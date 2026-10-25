import hashlib
import os

import pytest

from cryptofile import core

# Parámetros livianos para que los tests corran rápido; el formato y el flujo
# son los mismos que con los parámetros por defecto.
FAST = core.KdfParams(time_cost=1, memory_kib=8 * 1024, parallelism=1)
PASSWORD = "correct horse battery staple"


@pytest.mark.parametrize("size", [0, 1, 15, 16, 17, 1024, 1_000_003])
def test_roundtrip_identico_byte_a_byte(size: int) -> None:
    data = os.urandom(size)
    blob = core.encrypt(data, PASSWORD, "archivo.bin", FAST)
    result = core.decrypt(blob, PASSWORD)
    assert result.data == data
    assert hashlib.sha256(result.data).digest() == hashlib.sha256(data).digest()
    assert result.filename == "archivo.bin"


def test_roundtrip_con_parametros_por_defecto() -> None:
    data = b"documento secreto"
    blob = core.encrypt(data, PASSWORD, "doc.txt")
    assert core.decrypt(blob, PASSWORD).data == data


def test_nombre_unicode_y_ruta() -> None:
    blob = core.encrypt(b"x", PASSWORD, "/tmp/carpeta/año ñandú.pdf", FAST)
    assert core.decrypt(blob, PASSWORD).filename == "año ñandú.pdf"


def test_sal_e_iv_distintos_en_cada_cifrado() -> None:
    a = core.encrypt(b"igual", PASSWORD, "a", FAST)
    b = core.encrypt(b"igual", PASSWORD, "a", FAST)
    ha, hb = core.Header.from_bytes(a), core.Header.from_bytes(b)
    assert ha.salt != hb.salt
    assert ha.nonce != hb.nonce
    assert a != b


def test_formato_contiene_lo_necesario_para_descifrar() -> None:
    blob = core.encrypt(b"hola", PASSWORD, "h.txt", FAST)
    h = core.Header.from_bytes(blob)
    assert blob[:4] == core.MAGIC
    assert len(h.salt) == core.SALT_LEN and len(h.nonce) == core.NONCE_LEN
    assert h.kdf == FAST
    # encabezado + (2 + len(nombre) + datos) + tag
    assert len(blob) == core.HEADER_LEN + 2 + len("h.txt") + 4 + core.TAG_LEN


def test_contraseña_incorrecta() -> None:
    blob = core.encrypt(b"secreto", PASSWORD, "s", FAST)
    with pytest.raises(core.AuthenticationError):
        core.decrypt(blob, "otra contraseña")


@pytest.mark.parametrize("region", ["kdf_params", "salt", "nonce", "ciphertext", "tag"])
def test_archivo_modificado(region: str) -> None:
    blob = bytearray(core.encrypt(b"contenido importante" * 50, PASSWORD, "c", FAST))
    # (posición, máscara XOR) a modificar en cada región del archivo
    cambios = {
        "kdf_params": (9, 0x03),  # último byte del time_cost: 1 -> 2, sigue siendo válido
        "salt": (15, 0x01),
        "nonce": (31, 0x01),
        "ciphertext": (core.HEADER_LEN + 10, 0x01),
        "tag": (len(blob) - 1, 0x01),
    }
    i, mascara = cambios[region]
    blob[i] ^= mascara
    with pytest.raises(core.AuthenticationError):
        core.decrypt(bytes(blob), PASSWORD)


def test_archivo_truncado() -> None:
    blob = core.encrypt(b"datos", PASSWORD, "d", FAST)
    with pytest.raises(core.CryptoFileError):
        core.decrypt(blob[:-1], PASSWORD)
    with pytest.raises(core.InvalidFormatError):
        core.decrypt(blob[:20], PASSWORD)


def test_archivo_que_no_es_de_cryptofile() -> None:
    with pytest.raises(core.InvalidFormatError):
        core.decrypt(b"%PDF-1.7" + b"\x00" * 100, PASSWORD)


def test_parametros_absurdos_en_encabezado_se_rechazan_antes_de_derivar() -> None:
    blob = bytearray(core.encrypt(b"x", PASSWORD, "x", FAST))
    blob[10:14] = (0xFFFFFFFF).to_bytes(4, "big")  # 4 TiB de memoria
    with pytest.raises(core.InvalidFormatError):
        core.decrypt(bytes(blob), PASSWORD)


def test_contraseña_vacia() -> None:
    with pytest.raises(ValueError):
        core.encrypt(b"x", "", "x", FAST)


@pytest.mark.parametrize("stored, expected", [
    ("../../evil.txt", "evil.txt"),
    ("..\\..\\Windows\\evil.dll", "evil.dll"),
    ("/etc/passwd", "passwd"),
    ("C:\\Users\\x\\a.pdf", "a.pdf"),
    ("C:evil.txt", "evil.txt"),
    ("..", ""),
    ("", ""),
])
def test_nombre_guardado_no_puede_escapar_de_la_carpeta(
        stored: str, expected: str, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arma un archivo "malicioso" a mano: el nombre se mete en el payload sin limpiar.
    def payload_malicioso(filename: str, data: bytes) -> bytes:
        name = stored.encode()
        return len(name).to_bytes(2, "big") + name + data

    with monkeypatch.context() as m:
        m.setattr(core, "_pack_payload", payload_malicioso)
        blob = core.encrypt(b"x", PASSWORD, "ignorado", FAST)
    assert core.decrypt(blob, PASSWORD).filename == expected
