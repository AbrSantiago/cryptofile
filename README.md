# CryptoFile — TP2 Seguridad Informática (UNQ)

Cifra y descifra archivos con **AES-256-GCM**. La clave se deriva de la contraseña con **Argon2id**
(t=3, m=64 MiB, p=4) y una sal aleatoria de 16 bytes. Se usa por línea de comandos o con una
interfaz web en Streamlit.

**Demo online:** <https://cryptofile.streamlit.app/>

## Integrantes

| Integrante | GitHub |
|---|---|
| Abregú, Santiago | [@AbrSantiago](https://github.com/AbrSantiago) |
| Futryk, Fabricio | [@ffutryk](https://github.com/ffutryk) |
| Viazzo, Lucía | [@luciaviazzo](https://github.com/luciaviazzo) |

## Estructura

```
cryptofile/core.py   núcleo criptográfico y formato .cryf
cli.py               línea de comandos (encrypt / decrypt / sha256)
app.py, i18n.py      interfaz web (Streamlit, ES/EN)
tests/               pruebas automáticas (pytest)
informe/             informe (HTML fuente + PDF)
```

## Con uv (recomendado)

uv lee `pyproject.toml`/`uv.lock`, baja Python 3.12 si hace falta y crea el `.venv` solo.

```bash
uv run streamlit run app.py                                         # interfaz web -> http://localhost:8501
uv run cli.py encrypt documento.pdf                                 # -> documento.pdf.cryf
uv run cli.py decrypt documento.pdf.cryf -o documento_descifrado.pdf
uv run cli.py sha256 documento.pdf documento_descifrado.pdf         # compara hashes
uv run pytest                                                       # tests
```

## Con pip

Requiere Python 3.11 o superior.

```powershell
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
streamlit run app.py
python cli.py encrypt documento.pdf
python -m pytest
```

`requirements.txt` se mantiene para quien no use uv; las dependencias son las mismas que en `pyproject.toml`.

## Deploy en Streamlit Community Cloud

La app está publicada en **<https://cryptofile.streamlit.app/>** y se redeploya sola con cada push a la rama
configurada.

Para repetir el deploy:

1. Tener el proyecto en un repositorio de GitHub sobre el que tengas permisos de **administrador**. Si el repo
   es de otra persona, hacé un fork; después, para traer los cambios nuevos, usá **Sync fork** en GitHub.
2. En <https://share.streamlit.io> → **Create app** → elegir el repo, la rama y `app.py` como *main file*.
3. En **Advanced settings**, elegir Python 3.12 (o 3.11+). Las dependencias se instalan desde `uv.lock`/`requirements.txt`.
4. **Deploy**. La configuración visual y el límite de subida (100 MB) están en `.streamlit/config.toml`.
