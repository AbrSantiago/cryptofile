"""Textos de la interfaz en español e inglés."""

STRINGS = {
    "es": {
        "drop_title": "SOLTÁ TU ARCHIVO ACÁ",
        "drop_sub": "o hacé clic para buscarlo",
        "drop_label": "Archivo",
        "password": "CONTRASEÑA",
        "password_ph": "Ingresá la contraseña",
        "password_hint": "Enter para aplicar",
        "encrypt": "CIFRAR",
        "decrypt": "DESCIFRAR",
        "download": "DESCARGAR",
        "tag_plain": "SIN CIFRAR",
        "tag_cryf": "CIFRADO · CRYPTOFILE",
        "strength": ["", "DÉBIL", "ACEPTABLE", "BUENA", "FUERTE"],
        "feat_aes": "AES-256-GCM",
        "feat_kdf": "Argon2id KDF",
        "feat_rand": "IV/sal aleatorios",
        "header_title": "ENCABEZADO",
        "sha_original": "SHA-256 del original",
        "sha_decrypted": "SHA-256 del descifrado",
        "res_encrypted": "Archivo cifrado",
        "res_decrypted": "Archivo descifrado",
        "status_ready": "SISTEMA LISTO — ESPERANDO ENTRADA",
        "status_file": "ARCHIVO CARGADO — {size}",
        "status_need_pw": "ARCHIVO CARGADO — INGRESÁ UNA CONTRASEÑA",
        "status_encrypting": "DERIVANDO CLAVE Y CIFRANDO…",
        "status_decrypting": "DERIVANDO CLAVE Y DESCIFRANDO…",
        "status_enc_ok": "CIFRADO OK — {name} LISTO PARA DESCARGAR",
        "status_dec_ok": "DESCIFRADO OK — INTEGRIDAD VERIFICADA",
        "status_auth_err": "ERROR — CONTRASEÑA INCORRECTA O ARCHIVO MODIFICADO. NO SE GENERÓ SALIDA",
        "status_format_err": "ERROR — {msg}",
        "not_cryf": "El archivo no fue cifrado con CryptoFile: solo se puede cifrar.",
        "footer_note": "El archivo se procesa en memoria y no se guarda en el servidor.",
    },
    "en": {
        "drop_title": "DROP YOUR FILE HERE",
        "drop_sub": "or click to browse",
        "drop_label": "File",
        "password": "PASSWORD",
        "password_ph": "Enter password",
        "password_hint": "Press Enter to apply",
        "encrypt": "ENCRYPT",
        "decrypt": "DECRYPT",
        "download": "DOWNLOAD",
        "tag_plain": "PLAINTEXT",
        "tag_cryf": "ENCRYPTED · CRYPTOFILE",
        "strength": ["", "WEAK", "FAIR", "GOOD", "STRONG"],
        "feat_aes": "AES-256-GCM",
        "feat_kdf": "Argon2id KDF",
        "feat_rand": "Random IV/salt",
        "header_title": "HEADER",
        "sha_original": "Original SHA-256",
        "sha_decrypted": "Decrypted SHA-256",
        "res_encrypted": "Encrypted file",
        "res_decrypted": "Decrypted file",
        "status_ready": "SYSTEM READY — AWAITING INPUT",
        "status_file": "FILE LOADED — {size}",
        "status_need_pw": "FILE LOADED — ENTER A PASSWORD",
        "status_encrypting": "DERIVING KEY AND ENCRYPTING…",
        "status_decrypting": "DERIVING KEY AND DECRYPTING…",
        "status_enc_ok": "ENCRYPTED — {name} READY TO DOWNLOAD",
        "status_dec_ok": "DECRYPTED — INTEGRITY VERIFIED",
        "status_auth_err": "ERROR — WRONG PASSWORD OR TAMPERED FILE. NO OUTPUT WRITTEN",
        "status_format_err": "ERROR — {msg}",
        "not_cryf": "This file was not encrypted with CryptoFile: it can only be encrypted.",
        "footer_note": "Files are processed in memory and never stored on the server.",
    },
}

# Mensajes de error del núcleo (en español) traducidos para la interfaz en inglés.
CORE_ERRORS_EN = {
    "El archivo es demasiado corto para ser un archivo cifrado.": "FILE TOO SHORT TO BE ENCRYPTED",
    "El archivo no fue cifrado con CryptoFile.": "NOT A CRYPTOFILE FILE",
    "Parámetros de Argon2id fuera de rango.": "ARGON2ID PARAMETERS OUT OF RANGE",
}


def core_error(msg: str, lang: str) -> str:
    if lang == "en":
        return CORE_ERRORS_EN.get(msg, "INVALID FILE FORMAT")
    return msg.rstrip(".").upper()
