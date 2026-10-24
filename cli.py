"""CryptoFile por línea de comandos.

Ejemplos:
    python cli.py encrypt documento.pdf                 # genera documento.pdf.cryf
    python cli.py decrypt documento.pdf.cryf -o copia.pdf
    python cli.py sha256 documento.pdf copia.pdf        # compara hashes

La contraseña se pide por teclado sin mostrarse. Para usar el programa desde un
script se puede pasar por la entrada estándar con --password-stdin.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import os
import sys

from cryptofile import core


def _read_password(args: argparse.Namespace, confirm: bool) -> str:
    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\r\n")
    else:
        password = getpass.getpass("Contraseña: ")
        if confirm and getpass.getpass("Repetir contraseña: ") != password:
            raise SystemExit("Error: las contraseñas no coinciden.")
    if not password:
        raise SystemExit("Error: la contraseña no puede estar vacía.")
    return password


def _write_output(path: str, data: bytes, force: bool) -> None:
    if os.path.exists(path) and not force:
        raise SystemExit(f"Error: {path} ya existe. Usá -o para elegir otro nombre o --force para sobrescribir.")
    with open(path, "wb") as fh:
        fh.write(data)


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_encrypt(args: argparse.Namespace) -> int:
    with open(args.input, "rb") as fh:
        data = fh.read()
    password = _read_password(args, confirm=True)
    blob = core.encrypt(data, password, filename=args.input)
    out = args.output or args.input + core.EXTENSION
    _write_output(out, blob, args.force)
    print(f"Cifrado OK -> {out} ({len(blob)} bytes)")
    return 0


def cmd_decrypt(args: argparse.Namespace) -> int:
    with open(args.input, "rb") as fh:
        blob = fh.read()
    password = _read_password(args, confirm=False)
    try:
        result = core.decrypt(blob, password)
    except core.CryptoFileError as exc:
        # No se escribe ningún archivo de salida.
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    out = args.output or os.path.join(os.path.dirname(args.input), result.filename or
                                      core.default_decrypted_filename(args.input))
    _write_output(out, result.data, args.force)
    print(f"Descifrado OK -> {out} ({len(result.data)} bytes)")
    return 0


def cmd_sha256(args: argparse.Namespace) -> int:
    hashes = [(path, _sha256(path)) for path in args.files]
    for path, digest in hashes:
        print(f"{digest}  {path}")
    if len(hashes) > 1:
        same = len({d for _, d in hashes}) == 1
        print("Los hashes COINCIDEN." if same else "Los hashes NO coinciden.")
        return 0 if same else 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cryptofile",
        description="Cifra y descifra archivos con AES-256-GCM y una clave derivada con Argon2id.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name, func, help_text in (
        ("encrypt", cmd_encrypt, "cifrar un archivo"),
        ("decrypt", cmd_decrypt, "descifrar un archivo .cryf"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("input", help="archivo de entrada")
        p.add_argument("-o", "--output", help="archivo de salida")
        p.add_argument("-f", "--force", action="store_true", help="sobrescribir la salida si existe")
        p.add_argument("--password-stdin", action="store_true",
                       help="leer la contraseña de la entrada estándar (una línea)")
        p.set_defaults(func=func)

    p = sub.add_parser("sha256", help="calcular (y comparar) el SHA-256 de uno o más archivos")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_sha256)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"Error: no se encontró {exc.filename}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
