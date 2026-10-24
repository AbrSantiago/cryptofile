"""CryptoFile — interfaz web (Streamlit).

Ejecutar localmente:   streamlit run app.py
"""

from __future__ import annotations

import hashlib
import html
import math

import streamlit as st

from cryptofile import core
from i18n import STRINGS, core_error

st.set_page_config(page_title="CryptoFile", page_icon="🔐", layout="wide",
                   initial_sidebar_state="collapsed")

# --------------------------------------------------------------------------- estado

ss = st.session_state
ss.setdefault("lang", "es")
ss.setdefault("result", None)   # dict con la salida de la última operación
ss.setdefault("status", None)   # (nivel, clave_i18n, kwargs) del último evento
ss.setdefault("file_id", None)


def t(key: str, **kwargs) -> str:
    text = STRINGS[ss.lang][key]
    return text.format(**kwargs) if kwargs else text


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}".replace(".0 ", " ")
        n /= 1024
    return f"{n} B"


def password_score(pw: str) -> int:
    """Estimación simple de fortaleza (0–4) para el medidor."""
    if not pw:
        return 0
    classes = sum([any(c.islower() for c in pw), any(c.isupper() for c in pw),
                   any(c.isdigit() for c in pw), any(not c.isalnum() for c in pw)])
    score = 1
    if len(pw) >= 8 and classes >= 2:
        score = 2
    if len(pw) >= 12 and classes >= 3:
        score = 3
    if len(pw) >= 16 and classes >= 3 or len(pw) >= 20:
        score = 4
    return score


# --------------------------------------------------------------------------- estilos

def inject_css() -> None:
    drop_title = html.escape(t("drop_title")).replace('"', "")
    drop_sub = html.escape(t("drop_sub")).replace('"', "")
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');

:root{
  --page:#121822; --win:#05080f; --panel:#0a1018; --line:#151d29; --line-2:#1d2836;
  --teal:#19e6c1; --teal-dim:#0f8f7a; --teal-ghost:rgba(25,230,193,.08);
  --red:#ff3b5c; --amber:#ffb020;
  --text:#c9d4df; --muted:#4d5d6e; --faint:#2a3746;
  --mono:'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
html, body, .stApp{ background:var(--page) !important; }
.stApp{ background:radial-gradient(1200px 600px at 50% -10%, rgba(25,230,193,.06), transparent 60%), radial-gradient(900px 500px at 100% 110%, rgba(40,90,160,.07), transparent 60%), var(--page) !important; background-attachment:fixed !important; }
.stApp, .stApp *{ font-family:var(--mono) !important; }
.stApp [data-testid="stIconMaterial"]{ font-family:'Material Symbols Rounded' !important; }
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
footer, #MainMenu{ display:none !important; }
.block-container{ max-width:1180px !important; padding:2rem 1rem 2rem !important; }

/* ventana */
.st-key-window{
  background:var(--win); border:1px solid var(--line); border-radius:28px;
  box-shadow:0 0 0 1px rgba(25,230,193,.03), 0 40px 90px -30px rgba(0,0,0,.85); overflow:hidden; gap:0 !important;
}
.st-key-titlebar{ padding:14px 28px 12px 28px; border-bottom:1px solid var(--line); }
.cf-title{ display:flex; align-items:center; gap:14px; height:40px; }
.cf-dot{ width:18px; height:18px; border-radius:50%; display:inline-block; }
.cf-brand{ margin-left:22px; color:var(--teal); letter-spacing:.42em; font-weight:700; font-size:15px; }

/* selector de idioma */
.st-key-lang_wrap{ display:flex; align-items:flex-end; }
.st-key-lang_wrap [data-testid="stButtonGroup"]{ justify-content:flex-end; width:100%; display:flex; }
.st-key-lang_wrap button{
  background:transparent !important; border:1px solid var(--line-2) !important; color:var(--muted) !important;
  font-size:11px !important; letter-spacing:.2em; min-height:30px !important; padding:2px 12px !important;
}
.st-key-lang_wrap button[kind$="Active"], .st-key-lang_wrap button[aria-checked="true"]{
  color:var(--teal) !important; border-color:var(--teal-dim) !important; background:var(--teal-ghost) !important;
}

/* cuerpo */
.st-key-body{ gap:0 !important; }
.st-key-body > div[data-testid="stHorizontalBlock"]{ gap:0 !important; }
.st-key-left{ padding:48px 48px 40px 48px; }
.st-key-right{ padding:48px 28px; align-items:center; }
[data-testid="stColumn"]:has(.st-key-right){ border-left:1px solid var(--line); }


/* zona de carga */
[data-testid="stFileUploader"] label{ display:none !important; }
[data-testid="stFileUploaderDropzone"]{
  background:var(--win) !important; border:1.5px dashed #1f3140 !important; border-radius:16px !important;
  min-height:260px; display:flex !important; flex-direction:column; align-items:center; justify-content:center;
  cursor:pointer; transition:border-color .2s, background .2s; position:relative; padding:0 !important;
}
[data-testid="stFileUploaderDropzone"]:hover{ border-color:var(--teal-dim) !important; background:#071019 !important; }
[data-testid="stFileUploaderDropzone"] > *{ opacity:0 !important; position:absolute !important; inset:0; width:100% !important; height:100% !important; }
[data-testid="stFileUploaderDropzone"]::before{
  content:"DROP_TITLE"; color:#3e5568; letter-spacing:.32em; font-size:17px; padding-top:84px; pointer-events:none;
  text-align:center; width:100%; padding-left:.32em; box-sizing:border-box;
  background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='44' height='52' viewBox='0 0 44 52' fill='none' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M8 2h20l12 12v32a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4V6a4 4 0 0 1 4-4z' stroke='%232b4152' stroke-width='1.6' fill='%23070d14'/%3E%3Cpath d='M28 2v8a4 4 0 0 0 4 4h8' stroke='%232b4152' stroke-width='1.6'/%3E%3Cpath d='M22 40V24M15.5 30.5 22 24l6.5 6.5' stroke='%2319e6c1' stroke-width='1.8' opacity='.6'/%3E%3C/svg%3E") no-repeat center top;
}
[data-testid="stFileUploaderDropzone"]::after{
  content:"DROP_SUB"; color:#26394a; font-size:14px; margin-top:22px; pointer-events:none; text-align:center; width:100%;
}
[data-testid="stFileUploaderFile"], [data-testid="stFileUploaderPagination"],
[data-testid="stFileUploader"] section + div{ display:none !important; }

/* tarjeta del archivo */
.cf-file{
  display:flex; align-items:center; gap:22px; margin-top:18px; padding:18px 30px; border-radius:14px;
  background:#0c1a20; border:1.5px solid #12403a; color:#d5dee6; font-size:17px;
}
.cf-file .name{ flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.cf-file .size{ color:#2f4a55; font-size:15px; }
.cf-tag{ font-size:10px; letter-spacing:.18em; padding:3px 8px; border-radius:6px; border:1px solid var(--line-2); color:var(--muted); white-space:nowrap; }
.cf-tag.cryf{ color:var(--teal); border-color:var(--teal-dim); background:var(--teal-ghost); }

/* contraseña */
.cf-label{ color:#4c5c6b; letter-spacing:.32em; font-size:14px; margin:30px 0 10px; }
[data-testid="stTextInput"] label{ display:none !important; }
[data-testid="stTextInput"] [data-testid="stTextInputRootElement"]{
  background:#0b121b !important; border:1.5px solid var(--line-2) !important; border-radius:10px !important; height:64px !important;
}
[data-testid="stTextInput"] [data-testid="stTextInputRootElement"]:focus-within{ border-color:var(--teal-dim) !important; box-shadow:0 0 0 3px var(--teal-ghost); }
[data-testid="stTextInput"] > div{ height:auto !important; }
[data-testid="stTextInput"] input{ height:100% !important; color:#e6edf3 !important; font-size:20px !important; padding-left:24px !important; letter-spacing:.12em; caret-color:var(--teal); }
[data-testid="stTextInput"] input::placeholder{ color:#2c3a48 !important; letter-spacing:.04em; font-size:15px; }
[data-testid="stTextInput"] [data-baseweb="base-input"]{ background:transparent !important; height:60px !important; }
[data-testid="stTextInput"] button{ background:transparent !important; color:var(--muted) !important; }
[data-testid="InputInstructions"]{ color:var(--faint) !important; }
.cf-meter{ display:flex; gap:6px; margin-top:12px; }
.cf-meter span{ flex:1; height:4px; border-radius:3px; background:var(--line-2); transition:background .3s; }
.cf-meter-label{ text-align:right; font-size:10px; letter-spacing:.24em; margin-top:6px; height:14px; }

/* botones de acción */
.st-key-actions{ margin-top:10px; }
.st-key-actions [data-testid="stHorizontalBlock"]{ gap:16px !important; }
.st-key-actions button{
  width:100%; min-height:64px; border-radius:10px !important; background:#0b131c !important;
  border:1.5px solid #1a2a36 !important; color:var(--teal) !important; transition:all .2s;
}
.st-key-actions button p{ letter-spacing:.42em !important; font-size:20px !important; font-weight:500; }
.st-key-actions button:hover:not(:disabled){ background:var(--teal-ghost) !important; border-color:var(--teal) !important; box-shadow:0 0 24px -8px var(--teal); }
.st-key-actions button:disabled{ background:#070b11 !important; border-color:#0d141c !important; color:#141e28 !important; cursor:not-allowed; }
.st-key-actions button:disabled p{ color:#141e28 !important; }

/* resultado */
.st-key-result{
  margin-top:22px; padding:18px 22px; border:1px solid var(--line-2); border-radius:14px; background:var(--panel); gap:10px !important;
}
.cf-res-head{ margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; gap:12px; }
.cf-res-kind{ color:var(--muted); letter-spacing:.24em; font-size:11px; }
.cf-res-name{ color:#e6edf3; font-size:15px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.cf-hash{ color:var(--muted); font-size:11px; line-height:1.6; word-break:break-all; margin-bottom:16px; }
.cf-hash b{ color:var(--teal-dim); font-weight:500; }
.st-key-result [data-testid="stDownloadButton"] button{
  width:100%; background:var(--teal) !important; color:#03110e !important; border:none !important; border-radius:10px !important; min-height:48px;
}
.st-key-result [data-testid="stDownloadButton"] button p{ letter-spacing:.38em; font-weight:700; }
.st-key-result [data-testid="stDownloadButton"] button:hover{ filter:brightness(1.1); box-shadow:0 0 28px -6px var(--teal); }
.cf-note{ color:#d58a99; font-size:12px; margin-top:12px; letter-spacing:.04em; }

/* panel derecho */
.cf-side{ display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:560px; width:100%; }
.cf-radar{ width:250px; height:250px; }
.cf-radar .spin{ transform-origin:125px 125px; animation:cf-spin 18s linear infinite; }
.cf-radar .spin-rev{ transform-origin:125px 125px; animation:cf-spin 30s linear infinite reverse; }
.cf-radar .pulse{ transform-origin:125px 125px; animation:cf-pulse 2.4s ease-in-out infinite; }
.cf-radar.busy .spin{ animation-duration:2.5s; }
@keyframes cf-spin{ to{ transform:rotate(360deg); } }
@keyframes cf-pulse{ 0%,100%{ transform:scale(1); opacity:1 } 50%{ transform:scale(1.35); opacity:.55 } }
.cf-feats{ list-style:none; padding:0; margin:52px 0 0; text-align:left; color:#4e7f86; font-size:15px; letter-spacing:.14em; line-height:2.05; }
.cf-feats li::before{ content:"▸"; color:var(--teal); font-size:10px; margin-right:10px; position:relative; top:-2px; }
.cf-hdr{ margin-top:30px; width:100%; max-width:300px; border-top:1px dashed var(--line-2); padding-top:16px; font-size:11px; color:var(--muted); line-height:1.9; }
.cf-hdr .k{ color:#2f4352; letter-spacing:.2em; }
.cf-hdr .v{ color:#7da3a9; word-break:break-all; }
.cf-hdr .ttl{ color:#3e5568; letter-spacing:.3em; margin-bottom:6px; }

/* barra de estado */
.st-key-statusbar{ border-top:1px solid var(--line); padding:18px 40px 24px; }
.cf-status{ display:flex; align-items:center; gap:16px; letter-spacing:.3em; font-size:15px; color:#3e5568; }
.cf-status .cur{ width:12px; height:20px; background:var(--teal); animation:cf-blink 1.1s steps(1) infinite; flex:none; }
.cf-status.ok{ color:#4fae9c; } .cf-status.err{ color:var(--red); } .cf-status.err .cur{ background:var(--red); }
.cf-status.warn{ color:#9a7a3a; } .cf-status.warn .cur{ background:var(--amber); }
@keyframes cf-blink{ 50%{ opacity:0 } }
.cf-foot{ text-align:center; color:#334252; font-size:11px; letter-spacing:.06em; margin-top:14px; }
.cf-foot a{ color:#4d5d6e; }

/* Streamlit internos */
.st-key-window [data-testid="stMarkdownContainer"]{ margin-bottom:0 !important; }
.st-key-window [data-testid="stMarkdownContainer"] p{ margin:0; }
.st-key-left, .st-key-right, .st-key-titlebar, .st-key-statusbar{ gap:0 !important; }
.stElementContainer:has(> .stMarkdown style){ display:none; }
@media (max-width:640px){
  .st-key-left{ padding:28px 20px; }
  .st-key-right{ padding:36px 20px; }
  [data-testid="stColumn"]:has(.st-key-right){ border-left:none; border-top:1px solid var(--line); }
  .st-key-titlebar [data-testid="stHorizontalBlock"]{ flex-wrap:nowrap !important; }
  .st-key-titlebar [data-testid="stColumn"]{ min-width:0 !important; width:auto !important; flex:1 1 auto !important; }
  .cf-side{ min-height:0; }
  .cf-radar{ width:200px; height:200px; }
  .cf-feats{ margin-top:32px; }
  [data-testid="stFileUploaderDropzone"]{ min-height:210px; }
  [data-testid="stFileUploaderDropzone"]::before{ font-size:14px; letter-spacing:.22em; }
  .cf-file{ padding:14px 16px; gap:12px; font-size:14px; }
  .cf-status{ font-size:12px; letter-spacing:.18em; }
  .st-key-statusbar{ padding:14px 20px 18px; }
  .st-key-actions [data-testid="stHorizontalBlock"]{ flex-wrap:nowrap !important; gap:10px !important; }
  .st-key-actions [data-testid="stColumn"]{ min-width:0 !important; }
  .st-key-actions button p{ font-size:13px !important; letter-spacing:.16em !important; }
  .cf-file{ flex-wrap:wrap; row-gap:8px; }
  .cf-file .name{ flex:1 1 calc(100% - 40px); }
  .cf-file .cf-tag{ margin-left:30px; }
  .cf-file .size{ margin-left:auto; font-size:13px; }
  .st-key-titlebar{ padding:12px 18px; }
  .cf-brand{ margin-left:8px; letter-spacing:.3em; font-size:13px; }
  .cf-dot{ width:14px; height:14px; }
}</style>
""".replace("DROP_TITLE", drop_title).replace("DROP_SUB", drop_sub),
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- piezas HTML

def card_icon(encrypted: bool) -> str:
    """Ícono de documento con esquina doblada; con candado si el archivo está cifrado."""
    lines = ('<path d="M7 13h8M7 16.5h8M7 20h5" stroke="#19e6c1" stroke-width="1.3" opacity=".45"/>'
             if not encrypted else "")
    lock = ('<rect x="10.5" y="16" width="11" height="9" rx="2" fill="#0c1a20" stroke="#19e6c1" stroke-width="1.4"/>'
            '<path d="M13 16v-2.2a3 3 0 0 1 6 0V16" stroke="#19e6c1" stroke-width="1.4"/>'
            '<circle cx="16" cy="20.5" r="1.1" fill="#19e6c1"/>' if encrypted else "")
    return ('<svg width="24" height="28" viewBox="0 0 24 28" fill="none" stroke-linecap="round" '
            'stroke-linejoin="round" style="flex:none">'
            '<path d="M4.5 1.5h9.5l6 6v16a2 2 0 0 1-2 2H4.5a2 2 0 0 1-2-2v-20a2 2 0 0 1 2-2z" '
            'stroke="#19e6c1" stroke-width="1.4" fill="#0e2128"/>'
            '<path d="M14 1.5v4a2 2 0 0 0 2 2h4" stroke="#19e6c1" stroke-width="1.4"/>'
            f'{lines}{lock}</svg>')


def radar_svg(state: str) -> str:
    color = {"err": "#ff3b5c", "warn": "#ffb020"}.get(state, "#19e6c1")
    dots = [(0, 6, 1), (52, 4, .55), (102, 6, 1), (168, 6, 1), (196, 4, .55), (250, 4, .55), (290, 6, 1)]
    dot_svg = "".join(
        f'<circle cx="{125 + 104 * math.sin(math.radians(a)):.1f}" '
        f'cy="{125 - 104 * math.cos(math.radians(a)):.1f}" r="{r}" '
        f'fill="{color}" opacity="{o}"/>' for a, r, o in dots)
    busy = " busy" if state == "busy" else ""
    return f"""
<svg class="cf-radar{busy}" viewBox="0 0 250 250" xmlns="http://www.w3.org/2000/svg">
  <circle cx="125" cy="125" r="123" fill="#0b1820"/>
  <circle cx="125" cy="125" r="112" fill="#060c13"/>
  <g class="spin">
    <circle cx="125" cy="125" r="104" fill="none" stroke="{color}" stroke-width="1.3" stroke-dasharray="7 9" opacity=".75"/>
    {dot_svg}
  </g>
  <circle cx="125" cy="125" r="98" fill="none" stroke="#132230" stroke-width="1.5"/>
  <g class="spin-rev">
    <circle cx="125" cy="125" r="74" fill="none" stroke="#18293a" stroke-width="3"/>
    <path d="M125 51 A74 74 0 0 1 199 125" fill="none" stroke="{color}" stroke-width="3" opacity=".18"/>
  </g>
  <circle cx="125" cy="125" r="58" fill="none" stroke="#14222f" stroke-width="2"/>
  <circle cx="125" cy="125" r="32" fill="#08111a" stroke="#1d3446" stroke-width="3"/>
  <circle cx="125" cy="125" r="17" fill="none" stroke="{color}" stroke-width="1.6"/>
  <line x1="98" y1="125" x2="152" y2="125" stroke="#1d3446" stroke-width="2"/>
  <line x1="125" y1="98" x2="125" y2="152" stroke="#1d3446" stroke-width="2"/>
  <circle class="pulse" cx="125" cy="125" r="6" fill="{color}"/>
</svg>"""


def file_card(name: str, size: int, encrypted: bool) -> str:
    tag = (f'<span class="cf-tag cryf">{t("tag_cryf")}</span>' if encrypted
           else f'<span class="cf-tag">{t("tag_plain")}</span>')
    return (f'<div class="cf-file">{card_icon(encrypted)}'
            f'<span class="name">{html.escape(name)}</span>{tag}'
            f'<span class="size">{human_size(size)}</span></div>')


def meter(score: int) -> str:
    color = ["#1d2836", "#ff3b5c", "#ffb020", "#19e6c1", "#19e6c1"][score]
    bars = "".join(f'<span style="background:{color if i < score else "#1d2836"}"></span>' for i in range(4))
    return (f'<div class="cf-meter">{bars}</div>'
            f'<div class="cf-meter-label" style="color:{color}">{t("strength")[score]}</div>')


def header_info(h: core.Header) -> str:
    rows = [
        ("KDF", f"Argon2id · t={h.kdf.time_cost} · m={h.kdf.memory_kib // 1024} MiB · p={h.kdf.parallelism}"),
        ("SALT", h.salt.hex()),
        ("NONCE", h.nonce.hex()),
    ]
    body = "".join(f'<div><span class="k">{k}</span> <span class="v">{v}</span></div>' for k, v in rows)
    return f'<div class="cf-hdr"><div class="ttl">{t("header_title")}</div>{body}</div>'


def status_bar(level: str, text: str) -> str:
    return f'<div class="cf-status {level}"><span class="cur"></span><span>{html.escape(text)}</span></div>'


# --------------------------------------------------------------------------- acciones

def do_encrypt(data: bytes, name: str, password: str) -> None:
    blob = core.encrypt(data, password, filename=name)
    out = core.encrypted_filename(name)
    ss.result = {"kind": "enc", "name": out, "data": blob,
                 "sha": hashlib.sha256(data).hexdigest(), "header": core.Header.from_bytes(blob)}
    ss.status = ("ok", "status_enc_ok", {"name": out})


def do_decrypt(blob: bytes, name: str, password: str) -> None:
    try:
        res = core.decrypt(blob, password)
    except core.AuthenticationError:
        ss.result = None
        ss.status = ("err", "status_auth_err", {})
        return
    except core.InvalidFormatError as exc:
        ss.result = None
        ss.status = ("err", "status_format_err", {"msg": str(exc)})
        return
    out = res.filename or core.default_decrypted_filename(name)
    ss.result = {"kind": "dec", "name": out, "data": res.data,
                 "sha": hashlib.sha256(res.data).hexdigest()}
    ss.status = ("ok", "status_dec_ok", {})


# --------------------------------------------------------------------------- layout

inject_css()

with st.container(key="window"):
    # barra de título
    with st.container(key="titlebar"):
        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        c1.markdown(
            '<div class="cf-title"><span class="cf-dot" style="background:#ff3b5c"></span>'
            '<span class="cf-dot" style="background:#ffb020"></span>'
            '<span class="cf-dot" style="background:#19e6c1"></span>'
            '<span class="cf-brand">CRYPTOFILE</span></div>', unsafe_allow_html=True)
        with c2.container(key="lang_wrap"):
            lang = st.segmented_control("lang", ["ES", "EN"], default=ss.lang.upper(),
                                        label_visibility="collapsed", key="lang_sel")
            if lang and lang.lower() != ss.lang:
                ss.lang = lang.lower()
                st.rerun()

    with st.container(key="body"):
        left_col, right_col = st.columns([2.1, 1])

    left = left_col.container(key="left")
    right = right_col.container(key="right")

    with left:
        uploaded = st.file_uploader(t("drop_label"), type=None, accept_multiple_files=False,
                                    label_visibility="collapsed", key="uploader")

        file_bytes = uploaded.getvalue() if uploaded else None
        file_is_cryf = bool(file_bytes) and core.is_encrypted(file_bytes)
        current_id = uploaded.file_id if uploaded else None
        if current_id != ss.file_id:  # archivo nuevo: se descarta el resultado anterior
            ss.file_id, ss.result, ss.status = current_id, None, None

        if uploaded:
            st.markdown(file_card(uploaded.name, len(file_bytes), file_is_cryf), unsafe_allow_html=True)

        st.markdown(f'<div class="cf-label">{t("password")}</div>', unsafe_allow_html=True)
        password = st.text_input(t("password"), type="password", placeholder=t("password_ph"),
                                 label_visibility="collapsed", key="password")
        st.markdown(meter(password_score(password)), unsafe_allow_html=True)

        with st.container(key="actions"):
            b1, b2 = st.columns(2)
            enc_clicked = b1.button(t("encrypt"), disabled=not (uploaded and password), use_container_width=True)
            dec_clicked = b2.button(t("decrypt"), disabled=not (uploaded and password and file_is_cryf),
                                    use_container_width=True)

        if enc_clicked:
            with st.spinner(t("status_encrypting")):
                do_encrypt(file_bytes, uploaded.name, password)
        if dec_clicked:
            with st.spinner(t("status_decrypting")):
                do_decrypt(file_bytes, uploaded.name, password)

        r = ss.result
        if r:
            with st.container(key="result"):
                kind = t("res_encrypted") if r["kind"] == "enc" else t("res_decrypted")
                sha_label = t("sha_original") if r["kind"] == "enc" else t("sha_decrypted")
                st.markdown(
                    f'<div class="cf-res-head"><div style="min-width:0"><div class="cf-res-kind">{kind.upper()}</div>'
                    f'<div class="cf-res-name">{html.escape(r["name"])}</div></div>'
                    f'<div class="cf-res-kind">{human_size(len(r["data"]))}</div></div>'
                    f'<div class="cf-hash"><b>{sha_label}</b><br>{r["sha"]}</div>',
                    unsafe_allow_html=True)
                st.download_button(t("download"), data=r["data"], file_name=r["name"],
                                   mime="application/octet-stream", use_container_width=True,
                                   on_click="ignore", key="download")

    # estado general
    if ss.status:
        level, key, kw = ss.status
        if key == "status_format_err":
            kw = {"msg": core_error(kw["msg"], ss.lang)}
        status = (level, t(key, **kw))
    elif uploaded and not password:
        status = ("warn", t("status_need_pw"))
    elif uploaded:
        status = ("", t("status_file", size=human_size(len(file_bytes))))
    else:
        status = ("", t("status_ready"))

    with right:
        hdr = ""
        if ss.result and ss.result["kind"] == "enc":
            hdr = header_info(ss.result["header"])
        elif file_is_cryf:
            try:
                hdr = header_info(core.Header.from_bytes(file_bytes))
            except core.InvalidFormatError:
                hdr = ""
        st.markdown(
            f'<div class="cf-side">{radar_svg(status[0])}'
            f'<ul class="cf-feats"><li>{t("feat_aes")}</li><li>{t("feat_kdf")}</li><li>{t("feat_rand")}</li></ul>'
            f'{hdr}</div>', unsafe_allow_html=True)

    with st.container(key="statusbar"):
        st.markdown(status_bar(*status), unsafe_allow_html=True)

st.markdown(f'<div class="cf-foot">{t("footer_note")} · AES-256-GCM · Argon2id (RFC 9106)</div>',
            unsafe_allow_html=True)
