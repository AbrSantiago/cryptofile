"""Núcleo criptográfico de CryptoFile.

Cifra y descifra archivos con AES-256-GCM. La clave de 256 bits se deriva de la
contraseña del usuario con Argon2id y una sal aleatoria de 16 bytes.

Formato del archivo cifrado (.cryf), todos los enteros en big-endian:

    offset  tamaño  campo
    0       4       magic  b"CRYF"
    4       1       versión del formato (1)
    5       1       id de KDF (1 = Argon2id)
    6       4       iteraciones de Argon2id (time cost)
    10      4       memoria de Argon2id en KiB
    14      1       paralelismo (lanes) de Argon2id
    15      16      sal
    31      12      nonce (IV) de AES-GCM
    43      ...     texto cifrado + tag de autenticación de 16 bytes

Los 43 bytes del encabezado se pasan a AES-GCM como "datos asociados" (AAD):
no se cifran, pero sí se autentican, así que modificar cualquier parámetro del
encabezado hace fallar el descifrado igual que modificar el texto cifrado.

Lo que se cifra no es solo el contenido del archivo: se antepone el nombre
original (2 bytes de largo + nombre en UTF-8), para que el descifrado devuelva
el archivo con su nombre y para que el nombre no quede expuesto en claro.
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

MAGIC = b"CRYF"
VERSION = 1
KDF_ARGON2ID = 1

SALT_LEN = 16
NONCE_LEN = 12
TAG_LEN = 16
KEY_LEN = 32  # 256 bits -> AES-256

# Parámetros por defecto: segunda recomendación de la RFC 9106 (sección 4)
# para entornos con memoria limitada: t=3, m=64 MiB, p=4.
DEFAULT_TIME_COST = 3
DEFAULT_MEMORY_KIB = 64 * 1024
DEFAULT_PARALLELISM = 4

# Límites al leer un encabezado: evitan que un archivo manipulado obligue a
# reservar memoria o tiempo de CPU desmedidos antes de poder detectar el cambio.
MAX_TIME_COST = 10
MAX_MEMORY_KIB = 1024 * 1024  # 1 GiB
MAX_PARALLELISM = 16

EXTENSION = ".cryf"

_HEADER_FMT = ">4sBBIIB"
_PARAMS_LEN = struct.calcsize(_HEADER_FMT)  # 15
HEADER_LEN = _PARAMS_LEN + SALT_LEN + NONCE_LEN  # 43
MIN_FILE_LEN = HEADER_LEN + TAG_LEN


class CryptoFileError(Exception):
    """Error base de CryptoFile."""


class InvalidFormatError(CryptoFileError):
    """El archivo no tiene el formato de CryptoFile, o está truncado."""


class AuthenticationError(CryptoFileError):
    """Contraseña incorrecta o archivo modificado (GCM no distingue entre ambos)."""


@dataclass(frozen=True)
class KdfParams:
    time_cost: int = DEFAULT_TIME_COST
    memory_kib: int = DEFAULT_MEMORY_KIB
    parallelism: int = DEFAULT_PARALLELISM


@dataclass(frozen=True)
class Header:
    version: int
    kdf_id: int
    kdf: KdfParams
    salt: bytes
    nonce: bytes

    def to_bytes(self) -> bytes:
        return (
            struct.pack(
                _HEADER_FMT,
                MAGIC,
                self.version,
                self.kdf_id,
                self.kdf.time_cost,
                self.kdf.memory_kib,
                self.kdf.parallelism,
            )
            + self.salt
            + self.nonce
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> Header:
        if len(data) < MIN_FILE_LEN:
            raise InvalidFormatError("El archivo es demasiado corto para ser un archivo cifrado.")
        magic, version, kdf_id, t, m, p = struct.unpack(_HEADER_FMT, data[:_PARAMS_LEN])
        if magic != MAGIC:
            raise InvalidFormatError("El archivo no fue cifrado con CryptoFile.")
        if version != VERSION:
            raise InvalidFormatError(f"Versión de formato no soportada: {version}.")
        if kdf_id != KDF_ARGON2ID:
            raise InvalidFormatError(f"Función de derivación de clave desconocida: {kdf_id}.")
        if not (1 <= t <= MAX_TIME_COST and 1 <= p <= MAX_PARALLELISM
                and 8 * p <= m <= MAX_MEMORY_KIB):
            raise InvalidFormatError("Parámetros de Argon2id fuera de rango.")
        salt = data[_PARAMS_LEN:_PARAMS_LEN + SALT_LEN]
        nonce = data[_PARAMS_LEN + SALT_LEN:HEADER_LEN]
        return cls(version, kdf_id, KdfParams(t, m, p), salt, nonce)


@dataclass(frozen=True)
class DecryptedFile:
    filename: str
    data: bytes


def derive_key(password: str, salt: bytes, params: KdfParams) -> bytes:
    """Deriva una clave de 256 bits a partir de la contraseña con Argon2id."""
    if not password:
        raise ValueError("La contraseña no puede estar vacía.")
    kdf = Argon2id(
        salt=salt,
        length=KEY_LEN,
        iterations=params.time_cost,
        lanes=params.parallelism,
        memory_cost=params.memory_kib,
    )
    return kdf.derive(password.encode("utf-8"))


def _pack_payload(filename: str, data: bytes) -> bytes:
    name = os.path.basename(filename).encode("utf-8")[:0xFFFF]
    return struct.pack(">H", len(name)) + name + data


def _safe_filename(name: str) -> str:
    """Deja solo el nombre del archivo, sin ninguna ruta.

    El nombre viene de adentro del archivo cifrado; si alguien armara un .cryf con
    un nombre como "../../algo" o "C:\\algo", al descifrar se podría escribir fuera
    de la carpeta elegida. Se aceptan "/" y "\\" como separadores, sin importar el
    sistema operativo, y se descartan los nombres vacíos, "." y "..".
    """
    name = name.replace("\\", "/").replace("\x00", "")
    name = name.rsplit("/", 1)[-1].strip()
    if len(name) >= 2 and name[1] == ":":  # "C:algo" en Windows es relativo a la unidad C
        name = name[2:]
    return "" if name in ("", ".", "..") else name


def _unpack_payload(payload: bytes) -> DecryptedFile:
    (name_len,) = struct.unpack(">H", payload[:2])
    name = payload[2:2 + name_len].decode("utf-8", errors="replace")
    return DecryptedFile(filename=_safe_filename(name), data=payload[2 + name_len:])


def encrypt(data: bytes, password: str, filename: str = "", params: KdfParams | None = None) -> bytes:
    """Cifra `data` y devuelve el archivo cifrado completo (encabezado + cifrado + tag).

    Cada llamada genera una sal y un nonce nuevos con el CSPRNG del sistema
    (os.urandom), por lo que cifrar dos veces lo mismo da resultados distintos.
    """
    params = params or KdfParams()
    header = Header(
        version=VERSION,
        kdf_id=KDF_ARGON2ID,
        kdf=params,
        salt=os.urandom(SALT_LEN),
        nonce=os.urandom(NONCE_LEN),
    )
    header_bytes = header.to_bytes()
    key = derive_key(password, header.salt, params)
    ciphertext = AESGCM(key).encrypt(header.nonce, _pack_payload(filename, data), header_bytes)
    return header_bytes + ciphertext


def decrypt(blob: bytes, password: str) -> DecryptedFile:
    """Descifra un archivo producido por `encrypt`.

    Si la contraseña es incorrecta o cualquier byte (encabezado, cifrado o tag)
    fue alterado, lanza AuthenticationError y no devuelve ningún dato.
    """
    header = Header.from_bytes(blob)
    header_bytes = blob[:HEADER_LEN]
    key = derive_key(password, header.salt, header.kdf)
    try:
        payload = AESGCM(key).decrypt(header.nonce, blob[HEADER_LEN:], header_bytes)
    except InvalidTag:
        raise AuthenticationError(
            "No se pudo descifrar: la contraseña es incorrecta o el archivo fue modificado."
        ) from None
    return _unpack_payload(payload)


def is_encrypted(blob: bytes) -> bool:
    """Indica si `blob` parece un archivo de CryptoFile (solo mira el magic)."""
    return blob[:4] == MAGIC


def encrypted_filename(original: str) -> str:
    return os.path.basename(original) + EXTENSION


def default_decrypted_filename(encrypted_name: str) -> str:
    base = os.path.basename(encrypted_name)
    return base[: -len(EXTENSION)] if base.endswith(EXTENSION) else base + ".dec"
