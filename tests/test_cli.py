import io
import os

import pytest

import cli
from cryptofile import core

FAST = core.KdfParams(time_cost=1, memory_kib=8 * 1024, parallelism=1)


@pytest.fixture(autouse=True)
def fast_kdf(monkeypatch):
    original = core.encrypt
    monkeypatch.setattr(core, "encrypt", lambda d, p, filename="", params=None: original(d, p, filename, FAST))


def run(monkeypatch, argv, password):
    monkeypatch.setattr("sys.stdin", io.StringIO(password + "\n"))
    return cli.main([*argv, "--password-stdin"] if argv[0] != "sha256" else argv)


def test_cifrar_descifrar_y_comparar_hash(tmp_path, monkeypatch, capsys):
    original = tmp_path / "documento.pdf"
    original.write_bytes(os.urandom(5000))
    enc = tmp_path / "documento.pdf.cryf"
    dec = tmp_path / "descifrado.pdf"

    assert run(monkeypatch, ["encrypt", str(original)], "clave") == 0
    assert enc.exists()
    assert run(monkeypatch, ["decrypt", str(enc), "-o", str(dec)], "clave") == 0
    assert dec.read_bytes() == original.read_bytes()

    assert cli.main(["sha256", str(original), str(dec)]) == 0
    assert "COINCIDEN" in capsys.readouterr().out


def test_contraseña_incorrecta_no_genera_salida(tmp_path, monkeypatch, capsys):
    original = tmp_path / "a.txt"
    original.write_bytes(b"hola")
    run(monkeypatch, ["encrypt", str(original)], "buena")
    dec = tmp_path / "salida.txt"
    assert run(monkeypatch, ["decrypt", str(original) + ".cryf", "-o", str(dec)], "mala") == 1
    assert not dec.exists()
    assert "incorrecta" in capsys.readouterr().err


def test_archivo_modificado_no_genera_salida(tmp_path, monkeypatch):
    original = tmp_path / "a.txt"
    original.write_bytes(b"hola mundo")
    run(monkeypatch, ["encrypt", str(original)], "clave")
    enc = tmp_path / "a.txt.cryf"
    data = bytearray(enc.read_bytes())
    data[-5] ^= 0xFF
    enc.write_bytes(bytes(data))
    dec = tmp_path / "salida.txt"
    assert run(monkeypatch, ["decrypt", str(enc), "-o", str(dec)], "clave") == 1
    assert not dec.exists()


def test_no_sobrescribe_sin_force(tmp_path, monkeypatch):
    original = tmp_path / "a.txt"
    original.write_bytes(b"hola")
    run(monkeypatch, ["encrypt", str(original)], "clave")
    with pytest.raises(SystemExit):
        run(monkeypatch, ["decrypt", str(original) + ".cryf"], "clave")  # a.txt ya existe
    assert run(monkeypatch, ["decrypt", str(original) + ".cryf", "--force"], "clave") == 0
