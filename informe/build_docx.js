// Genera informe.docx con el mismo contenido que informe.html.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
  HeadingLevel, AlignmentType, WidthType, ShadingType, BorderStyle, LevelFormat,
  Footer, PageNumber, TabStopType, LineRuleType,
} = require("docx");

const DIR = __dirname;
const INK = "141B24", MUTED = "5B6774", TEAL = "0E9E85", LINE = "D9DEE4", CODEBG = "F2F4F6";
const FONT = "Calibri", MONO = "Consolas";
const PAGE_W = 11906, MARGIN = 1020, CONTENT_W = PAGE_W - 2 * MARGIN; // A4, márgenes ~18 mm

// ---------- helpers de texto en línea: **negrita**, `código`, *itálica*
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const tok = m[0];
    if (tok.startsWith("**")) out.push(new TextRun({ text: tok.slice(2, -2), bold: true, ...base }));
    else if (tok.startsWith("`")) out.push(new TextRun({ text: tok.slice(1, -1), font: MONO, size: 17, shading: { type: ShadingType.CLEAR, fill: CODEBG, color: "auto" }, ...base }));
    else out.push(new TextRun({ text: tok.slice(1, -1), italics: true, ...base }));
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}

const P = (text, opts = {}) => new Paragraph({ children: runs(text, opts.run || {}), spacing: { after: 100 }, ...opts.para });
const H1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)] });
const H2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: runs(text) });
const bullet = (text) => new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: runs(text), spacing: { after: 40 } });
const numbered = (ref) => (text) => new Paragraph({ numbering: { reference: ref, level: 0 }, children: runs(text), spacing: { after: 40 } });

// bloque de código: una tabla de 1 celda sombreada, una línea por párrafo
function code(lines) {
  const children = lines.map((l) => {
    const isComment = l.trim().startsWith("#") || l.trim().startsWith("(código");
    const isPrompt = l.startsWith("$ ");
    const r = [];
    if (isPrompt) {
      r.push(new TextRun({ text: "$ ", font: MONO, size: 16, color: TEAL, bold: true }));
      const rest = l.slice(2);
      const hash = rest.indexOf("   #");
      if (hash >= 0) {
        r.push(new TextRun({ text: rest.slice(0, hash), font: MONO, size: 16 }));
        r.push(new TextRun({ text: rest.slice(hash), font: MONO, size: 16, color: "7A8794" }));
      } else r.push(new TextRun({ text: rest, font: MONO, size: 16 }));
    } else {
      const hash = l.indexOf("   #");
      if (!isComment && hash >= 0) {
        r.push(new TextRun({ text: l.slice(0, hash), font: MONO, size: 16 }));
        r.push(new TextRun({ text: l.slice(hash), font: MONO, size: 16, color: "7A8794" }));
      } else r.push(new TextRun({ text: l || " ", font: MONO, size: 16, color: isComment ? "7A8794" : INK }));
    }
    return new Paragraph({ children: r, spacing: { after: 0, line: 250 } });
  });
  const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  return [
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [CONTENT_W],
      rows: [new TableRow({ children: [new TableCell({
        width: { size: CONTENT_W, type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill: CODEBG, color: "auto" },
        borders: { top: none, bottom: none, right: none, left: { style: BorderStyle.SINGLE, size: 18, color: TEAL } },
        margins: { top: 100, bottom: 100, left: 180, right: 140 },
        children,
      })] })],
    }),
    new Paragraph({ spacing: { after: 80 }, children: [] }),
  ];
}

// tabla de datos con encabezado
function table(headers, rows, widths, monoCols = []) {
  const border = { style: BorderStyle.SINGLE, size: 4, color: LINE };
  const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  const borders = { top: none, left: none, right: none, bottom: border };
  const cell = (text, w, header, mono) => new TableCell({
    width: { size: w, type: WidthType.DXA }, borders,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    shading: header ? { type: ShadingType.CLEAR, fill: "F5F7F9", color: "auto" } : undefined,
    children: [new Paragraph({ spacing: { after: 0 }, children: header
      ? [new TextRun({ text: text.toUpperCase(), bold: true, size: 15, color: MUTED, characterSpacing: 10 })]
      : (mono ? [new TextRun({ text, font: MONO, size: 16 })] : runs(text, { size: 19 })) })],
  });
  return [
    new Table({
      width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
      columnWidths: widths,
      rows: [
        new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, widths[i], true)) }),
        ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, widths[i], false, monoCols.includes(i))) })),
      ],
    }),
    new Paragraph({ spacing: { after: 80 }, children: [] }),
  ];
}

// dos columnas lado a lado (flujos / capturas)
function twoCols(left, right, bordered) {
  const w = Math.floor((CONTENT_W - 240) / 2);
  const line = { style: BorderStyle.SINGLE, size: 4, color: LINE };
  const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  const b = bordered ? { top: line, bottom: line, left: line, right: line } : { top: none, bottom: none, left: none, right: none };
  const gapB = { top: none, bottom: none, left: none, right: none };
  const mk = (children, width, borders) => new TableCell({
    width: { size: width, type: WidthType.DXA }, borders,
    margins: bordered ? { top: 120, bottom: 120, left: 160, right: 160 } : { top: 0, bottom: 0, left: 0, right: 0 },
    children,
  });
  return [
    new Table({
      width: { size: w * 2 + 240, type: WidthType.DXA },
      columnWidths: [w, 240, w],
      rows: [new TableRow({ cantSplit: true, children: [mk(left, w, b), mk([new Paragraph("")], 240, gapB), mk(right, w, b)] })],
    }),
    new Paragraph({ spacing: { after: 80 }, children: [] }),
  ];
}

function note(text) {
  const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  return [
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: [CONTENT_W],
      rows: [new TableRow({ children: [new TableCell({
        width: { size: CONTENT_W, type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill: "EEF8F6", color: "auto" },
        borders: { top: none, bottom: none, right: none, left: { style: BorderStyle.SINGLE, size: 18, color: TEAL } },
        margins: { top: 100, bottom: 100, left: 180, right: 140 },
        children: [new Paragraph({ spacing: { after: 0 }, children: runs(text) })],
      })] })],
    }),
    new Paragraph({ spacing: { after: 80 }, children: [] }),
  ];
}

function figure(file, caption, widthPx) {
  const buf = fs.readFileSync(path.join(DIR, file));
  // dimensiones del jpg (SOF0/SOF2)
  let i = 2, wImg = 0, hImg = 0;
  while (i < buf.length) {
    const marker = buf[i + 1], len = buf.readUInt16BE(i + 2);
    if (marker === 0xc0 || marker === 0xc2) { hImg = buf.readUInt16BE(i + 5); wImg = buf.readUInt16BE(i + 7); break; }
    i += 2 + len;
  }
  const h = Math.round(widthPx * hImg / wImg);
  return [
    new Paragraph({ spacing: { after: 60, line: 240, lineRule: LineRuleType.AUTO }, children: [new ImageRun({ type: "jpg", data: buf, transformation: { width: widthPx, height: h },
      altText: { title: caption, description: caption, name: file } })] }),
    new Paragraph({ spacing: { after: 0 }, children: [new TextRun({ text: caption, size: 16, color: MUTED })] }),
  ];
}

// ---------- contenido
const body = [];

body.push(new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: "SEGURIDAD INFORMÁTICA · UNQ · TRABAJO PRÁCTICO 2", bold: true, size: 16, color: TEAL, characterSpacing: 30 })] }));
body.push(new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun("CryptoFile: cifrado de archivos con AES-256")] }));
body.push(new Paragraph({
  spacing: { after: 240 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 18, color: INK, space: 6 } },
  tabStops: [{ type: TabStopType.RIGHT, position: CONTENT_W }],
  children: [new TextRun({ text: "Integrantes: ", color: MUTED, size: 18 }), new TextRun({ text: "[completar]", bold: true, size: 18 }),
    new TextRun({ text: "\tOctubre 2026", color: MUTED, size: 18 })],
}));

body.push(P("CryptoFile cifra cualquier archivo con **AES-256-GCM**. La clave se deriva de una contraseña con **Argon2id** y una sal aleatoria, y el resultado se descifra a un archivo idéntico byte a byte. Se usa desde la línea de comandos (`cli.py`) o desde una interfaz web hecha con Streamlit (`app.py`). Las dos usan el mismo núcleo criptográfico (`cryptofile/core.py`), que se apoya en la librería `cryptography` de Python. No se implementa AES desde cero.", { run: { size: 21, color: "33404D" } }));

body.push(H1("1. Funcionamiento del código"));
body.push(H2("Estructura"));
body.push(...table(["Archivo", "Responsabilidad"], [
  ["cryptofile/core.py", "Formato del archivo cifrado, derivación de clave, `encrypt()` y `decrypt()`, errores (`AuthenticationError`, `InvalidFormatError`)."],
  ["cli.py", "Comandos `encrypt`, `decrypt` y `sha256`. Pide la contraseña sin mostrarla y nunca sobrescribe archivos sin `--force`."],
  ["app.py, i18n.py", "Interfaz web (Streamlit) en español e inglés. Procesa todo en memoria y ofrece el resultado como descarga."],
  ["tests/", "25 pruebas automáticas con `pytest`: ida y vuelta, contraseña incorrecta, archivo alterado, sal/IV distintos y formato."],
], [2700, CONTENT_W - 2700], [0]));

const enc = numbered("enc"), dec = numbered("dec");
body.push(...twoCols([
  new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: "Flujo de cifrado", bold: true })] }),
  enc("Leer el archivo y la contraseña."),
  enc("Generar con `os.urandom` (CSPRNG del sistema operativo) una **sal de 16 bytes** y un **nonce de 12 bytes**."),
  enc("Derivar la clave de 32 bytes: `Argon2id(contraseña, sal, t=3, m=64 MiB, p=4)`."),
  enc("Armar el encabezado de 43 bytes (magic, versión, parámetros de Argon2id, sal y nonce)."),
  enc("Cifrar `nombre original + contenido` con AES-256-GCM. El encabezado se pasa como dato asociado (AAD)."),
  enc("Escribir `encabezado ‖ texto cifrado ‖ tag (16 bytes)`."),
], [
  new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: "Flujo de descifrado", bold: true })] }),
  dec("Leer el encabezado y validarlo: magic, versión y parámetros dentro de rango."),
  dec("Re-derivar la clave con la contraseña ingresada y la sal y los parámetros guardados."),
  dec("Descifrar con AES-256-GCM, que verifica el tag sobre el encabezado y el texto cifrado."),
  dec("Si el tag no coincide, informar el error y **no escribir nada**."),
  dec("Si coincide, recuperar el nombre original y escribir el archivo descifrado."),
], true));

body.push(H1("2. Decisiones de diseño"));
body.push(H2("Modo de operación: AES-256-GCM"));
body.push(P("Elegimos GCM y no CBC+HMAC porque es un modo de **cifrado autenticado** (AEAD): en una sola operación, con una sola clave, da confidencialidad e integridad. Con CBC+HMAC hay que derivar dos claves, aplicar padding y respetar el orden encrypt-then-MAC con una comparación en tiempo constante. Cada uno de esos pasos es un punto donde se puede cometer un error. GCM no usa padding, así que el texto cifrado mide lo mismo que el original. El encabezado entra como AAD: no se cifra, pero queda autenticado, y alterar cualquier parámetro, la sal o el nonce invalida el tag. ECB queda descartado porque cifra igual los bloques iguales y deja ver patrones del archivo."));
body.push(H2("Derivación de la clave: Argon2id"));
body.push(P("La contraseña nunca se usa directo como clave: pasa por **Argon2id**, el ganador de la Password Hashing Competition y la opción recomendada por la RFC 9106 y por OWASP. Además de lento es *memory-hard*: cada intento obliga a reservar 64 MiB, y eso encarece mucho un ataque de fuerza bruta con GPU o ASIC frente a PBKDF2. Usamos la segunda configuración recomendada por la RFC 9106 (t=3, m=64 MiB, p=4). Tarda una fracción de segundo por operación y entra en la memoria de un servidor gratuito. La **sal** es aleatoria y distinta en cada cifrado: dos archivos con la misma contraseña quedan con claves diferentes y no sirven tablas precomputadas."));
body.push(P("Los parámetros se guardan en el encabezado, así se pueden endurecer en el futuro sin perder la capacidad de descifrar archivos viejos. Al leer un archivo se acotan (memoria ≤ 1 GiB, t ≤ 10, p ≤ 16), para que un archivo manipulado no fuerce a reservar recursos desmedidos antes de llegar a verificar el tag."));
body.push(H2("IV / nonce"));
body.push(P("El nonce de GCM es de 96 bits, el tamaño estándar, y se genera aleatoriamente en cada cifrado. En GCM es crítico no repetir nunca un par (clave, nonce). Acá además cada cifrado usa una clave distinta, porque la sal es nueva, así que una repetición es prácticamente imposible."));
body.push(H2("Formato del archivo cifrado (`.cryf`)"));
body.push(...table(["Bytes", "Campo", "Ejemplo real (documento_secreto.pdf.cryf)"], [
  ["0–3", "Magic `CRYF`", "43 52 59 46"],
  ["4", "Versión del formato", "01"],
  ["5", "KDF (1 = Argon2id)", "01"],
  ["6–9", "Iteraciones (t)", "00 00 00 03"],
  ["10–13", "Memoria en KiB (m)", "00 01 00 00  (65 536 KiB = 64 MiB)"],
  ["14", "Paralelismo (p)", "04"],
  ["15–30", "Sal (16 bytes)", "6c 13 4e 8b 56 c5 b6 f3 ef 4d 95 44 35 c2 0a 83"],
  ["31–42", "Nonce (12 bytes)", "98 78 ec ef cd e6 d9 50 37 bf 0e 96"],
  ["43–…", "Texto cifrado + tag", "1791 bytes = 2 + 21 (nombre) + 1752 (contenido) + 16 (tag)"],
], [1100, 2500, CONTENT_W - 3600], [2]));
body.push(P("El archivo trae todo lo necesario para descifrarlo salvo la contraseña. También cifra el **nombre original**, así el descifrado lo restaura y el nombre no queda expuesto. El costo total es de 43 + 2 + largo del nombre + 16 bytes."));
body.push(H2("Errores"));
body.push(P("GCM no puede distinguir una contraseña incorrecta de un archivo modificado: en los dos casos el tag no verifica. Por eso el programa informa un único error, “la contraseña es incorrecta o el archivo fue modificado”, y **no genera archivo de salida**. El descifrado se hace completo en memoria y solo se escribe si la verificación fue exitosa, así que nunca se entrega texto plano sin autenticar. Los archivos que no son de CryptoFile, o que están truncados o tienen parámetros fuera de rango, se rechazan con un mensaje específico antes de derivar la clave."));
body.push(...note("**Limitación conocida.** El archivo se procesa entero en memoria. Es la forma más simple de garantizar que no se escriba nada sin verificar, y alcanza para el uso previsto. La interfaz web acepta archivos de hasta 100 MB."));

body.push(H1("3. Prueba"));
body.push(P("Ciclo completo con un PDF, comparando el SHA-256 del original con el del descifrado. También se prueba una contraseña incorrecta y un archivo con un solo bit modificado:"));
body.push(...code([
  "$ python cli.py encrypt documento_secreto.pdf",
  "Cifrado OK -> documento_secreto.pdf.cryf (1834 bytes)",
  "$ python cli.py decrypt documento_secreto.pdf.cryf -o documento_descifrado.pdf",
  "Descifrado OK -> documento_descifrado.pdf (1752 bytes)",
  "$ python cli.py sha256 documento_secreto.pdf documento_descifrado.pdf",
  "bb53f8ed9094d50ccf0f5314fff8ef5e05d58ef6a4c7bff0fa75d5665359516c  documento_secreto.pdf",
  "bb53f8ed9094d50ccf0f5314fff8ef5e05d58ef6a4c7bff0fa75d5665359516c  documento_descifrado.pdf",
  "Los hashes COINCIDEN.",
  "$ python cli.py decrypt documento_secreto.pdf.cryf -o x.pdf   # contraseña incorrecta",
  "Error: No se pudo descifrar: la contraseña es incorrecta o el archivo fue modificado.",
  "(código de salida 1 — x.pdf no se creó)",
  "$ python cli.py decrypt alterado.cryf -o y.pdf   # 1 bit modificado en el byte 100",
  "Error: No se pudo descifrar: la contraseña es incorrecta o el archivo fue modificado.",
  "(código de salida 1 — y.pdf no se creó)",
]));
body.push(new Paragraph({ spacing: { after: 100 }, children: [
  ...runs("Los **hashes SHA-256 coinciden**: el archivo descifrado es idéntico al original. Las pruebas automáticas (`python -m pytest`, "),
  new TextRun({ text: "25 passed", bold: true, color: TEAL }),
  new TextRun(") verifican además:"),
] }));
body.push(bullet("ida y vuelta byte a byte con archivos de 0, 1, 15, 16, 17, 1024 y ~1 MB;"));
body.push(bullet("que dos cifrados del mismo archivo con la misma contraseña usen sal y nonce distintos;"));
body.push(bullet("que la modificación de cualquier región (parámetros, sal, nonce, texto cifrado o tag) se detecte;"));
body.push(bullet("que la CLI no cree el archivo de salida ante contraseña incorrecta o archivo alterado."));
body.push(new Paragraph({ spacing: { after: 80 }, children: [] }));
const imgW = Math.floor(((CONTENT_W - 240) / 2) / 15); // DXA -> px (1 px = 15 DXA)
body.push(...twoCols(
  figure("captura_cifrado.jpg", "Interfaz web después de cifrar: SHA-256 del original y parámetros del encabezado.", imgW),
  figure("captura_error.jpg", "Descifrado con contraseña incorrecta: se informa el error y no se ofrece salida.", imgW),
  false));

body.push(H1("Anexo: ejecución"));
body.push(H2("Requisitos"));
body.push(P("uv (recomendado) o Python 3.11 o superior con pip. Dependencias (`requirements.txt`): `cryptography ≥ 44`, que incluye Argon2id, y `streamlit`, solo para la interfaz web."));
body.push(H2("Instalación"));
body.push(P("Con **uv** no hace falta instalar nada a mano: `uv run` lee `pyproject.toml` y `uv.lock`, y crea el entorno virtual con las versiones exactas la primera vez:"));
body.push(...code(["uv run streamlit run app.py", "uv run cli.py encrypt documento.pdf", "uv run pytest"]));
body.push(P("Alternativa con pip:"));
body.push(...code([
  "# Windows (PowerShell)", "python -m venv .venv", ".venv\\Scripts\\activate", "pip install -r requirements.txt", "",
  "# Linux / macOS", "python3 -m venv .venv", "source .venv/bin/activate", "pip install -r requirements.txt",
]));
body.push(H2("Línea de comandos"));
body.push(...code([
  "# Cifrar (pide la contraseña dos veces, sin mostrarla) → genera documento.pdf.cryf",
  "python cli.py encrypt documento.pdf", "",
  "# Descifrar → restaura el nombre original, o el indicado con -o",
  "python cli.py decrypt documento.pdf.cryf -o documento_descifrado.pdf", "",
  "# Comparar hashes", "python cli.py sha256 documento.pdf documento_descifrado.pdf", "",
  "# Ayuda", "python cli.py --help",
]));
body.push(H2("Interfaz web"));
body.push(...code(["streamlit run app.py   # abre http://localhost:8501"]));
body.push(P("Arrastrar un archivo a la zona de carga, escribir la contraseña (Enter para aplicarla) y presionar **CIFRAR** o **DESCIFRAR**. El botón de descifrar solo se habilita si el archivo tiene el formato de CryptoFile. El resultado se baja con **DESCARGAR**, junto con su SHA-256. El selector ES/EN cambia el idioma."));
body.push(H2("Pruebas automáticas"));
body.push(...code(["pip install -r requirements-dev.txt", "python -m pytest"]));

// ---------- documento
const numCfg = (ref, fmt, text) => ({ reference: ref, levels: [{ level: 0, format: fmt, text, alignment: AlignmentType.LEFT,
  style: { paragraph: { indent: { left: 360, hanging: 280 } } } }] });

const doc = new Document({
  creator: "Grupo TP2",
  title: "TP2 — Criptografía — Informe",
  styles: {
    default: { document: { run: { font: FONT, size: 20, color: INK }, paragraph: { spacing: { line: 276, lineRule: LineRuleType.AUTO } } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", next: "Normal", run: { font: FONT, size: 40, bold: true, color: INK }, paragraph: { spacing: { after: 120 } } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 27, bold: true, color: INK },
        paragraph: { spacing: { before: 320, after: 140 }, keepNext: true, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: INK, space: 3 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 22, bold: true, color: INK }, paragraph: { spacing: { before: 200, after: 80 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [
    numCfg("bullets", LevelFormat.BULLET, "•"),
    numCfg("enc", LevelFormat.DECIMAL, "%1."),
    numCfg("dec", LevelFormat.DECIMAL, "%1."),
  ] },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [
      new TextRun({ text: "TP2 · Criptografía · página ", size: 16, color: MUTED }),
      new TextRun({ children: [PageNumber.CURRENT], size: 16, color: MUTED }),
    ] })] }) },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(path.join(DIR, "informe.docx"), buf);
  console.log("informe.docx generado");
});
