// EL TEXTO, LAS CAPAS Y LOS PÍXELES DE UN ARTE, LEÍDOS COMO LOS LEE PyMuPDF — PLAN_NAVEGADOR.md,
// etapa 3, camino A (el arte SEPARADO).
//
// Todo lo que el servidor sabe de un arte separado (`motor_pedido.extraer_personalizacion`,
// `detectar_arte`, `mapeo_por_nombre`, `validar_arte*`) sale de cuatro lecturas de PyMuPDF:
// `page.get_text("dict")`, `layer_ui_configs()`/`set_layer_ui_config()`, `get_ocgs()` y
// `get_pixmap()`. mupdf.js trae el MISMO MuPDF, pero no la capa de PyMuPDF que arma los «spans»
// y corrige los recuadros de los glifos: eso se traduce acá, función por función
// (`JM_make_spanlist`, `JM_char_quad`, `JM_char_bbox`, `detect_super_script`), para que el
// navegador vea EXACTAMENTE los mismos números que el servidor. El contrato
// `verificar_navegador_arte.py` lo exige valor por valor.
//
// ⚠️ FLOAT32: MuPDF calcula en `float`. Donde PyMuPDF/C++ hace aritmética con esos valores
// (`JM_char_quad`), acá se pasa por `Math.fround` en el mismo orden.
//
// Lo que NO se puede leer desde mupdf.js y se asume constante (verificado en los artes reales):
//   · `char_flags` y `bidi` de cada carácter (PyMuPDF parte los spans también por ellos); en un
//     PDF `bidi` es siempre 0 y `char_flags` sólo cambia si el mismo texto se rellena Y se traza;
//   · el canal alfa del color (`argb >> 24`): PyMuPDF también parte por él;
//   · el ascender/descender de una fuente SIN /FontDescriptor (MuPDF los toma de la cara FreeType).
import { pyIsSpace, pyStrip } from '../py.js'

const f = Math.fround
export const FLT_EPSILON = 1.1920928955078125e-7

// ─── cadenas como Python ─────────────────────────────────────────────────────────────────────
/** `str.split()` de Python (sin argumento): por corridas de espacios de Python, sin vacíos. */
export function splitPy(s) {
  const out = []
  let cur = ''
  for (const ch of String(s)) {
    if (pyIsSpace(ch)) { if (cur) { out.push(cur); cur = '' } } else cur += ch
  }
  if (cur) out.push(cur)
  return out
}

/** `_norm_nombre` de motor_pedido: NFKD, sin marcas combinantes, minúsculas, guión → espacio. */
export function normNombre(s) {
  if (!s) return ''
  // `unicodedata.combining(c) != 0` ≈ la categoría Mn (para nombres de capa en español es lo mismo)
  const t = String(s).normalize('NFKD').replace(/\p{Mn}/gu, '')
  return splitPy(t.toLowerCase().replace(/-/g, ' ')).join(' ')
}

// los espacios de Python (`str.isspace`), como clase de expresión regular
export const WS_PY = '\\t\\n\\v\\f\\r\\x1c-\\x1f \\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000'
const RX_GENERICO = new RegExp('[' + WS_PY + ']+\\p{Nd}+[' + WS_PY + ']*$', 'u')

/** `_norm_generico`: además sin el número final («Frente 8» → «frente»). */
export function normGenerico(s) {
  return pyStrip(normNombre(s).replace(RX_GENERICO, ''))
}

/** `str.isdigit()` de Python sobre una palabra ya normalizada (NFKD): dígitos decimales. */
export const esDigitoPy = (w) => /^\p{Nd}+$/u.test(w)

/** `str.isalpha()` de Python. */
export const esLetraPy = (ch) => /^\p{L}$/u.test(ch)

/** `sorted(lista_de_textos)` de Python: por punto de código. */
export function ordenarPy(lista) {
  return [...lista].sort((a, b) => (a < b ? -1 : a > b ? 1 : 0))
}

/** `max(lista, key=len)` de Python: el PRIMERO de los más largos (largo en puntos de código). */
export function masLargaPy(lista) {
  let mejor = null, ml = -1
  for (const s of lista) { const l = Array.from(s).length; if (l > ml) { mejor = s; ml = l } }
  return mejor
}

// ─── `str(pikepdf.String)` y `str(pikepdf.Name)` ───────────────────────────────────────────────
// Los lectores de personalización comparan el TEXTO de cada `Tj` tal como lo decodifica pikepdf
// (QPDF `getUTF8Value`): UTF-16 si hay BOM, si no PDFDocEncoding byte a byte. Con una fuente CID
// ese texto son ids de glifo y la clave que manda es la CAPA (`CLAVE_CAPA`), pero la clave por
// texto tiene que salir igual para que los desempates («contención», «un solo texto») coincidan.
const PDFDOC_ALTOS = [0xfffd, 0x2022, 0x2020, 0x2021, 0x2026, 0x2014, 0x2013, 0x0192, 0x2044, 0x2039, 0x203a,
  0x2212, 0x2030, 0x201e, 0x201c, 0x201d, 0x2018, 0x2019, 0x201a, 0x2122, 0xfb01, 0xfb02, 0x0141, 0x0152,
  0x0160, 0x0178, 0x017d, 0x0131, 0x0142, 0x0153, 0x0161, 0x017e, 0xfffd, 0x20ac]   // bytes 127..160
const PDFDOC_BAJOS = [0x02d8, 0x02c7, 0x02c6, 0x02d9, 0x02dd, 0x02db, 0x02da, 0x02dc]  // bytes 24..31

export function textoPikepdf(u8) {
  const n = u8.length
  if (n >= 2 && ((u8[0] === 0xfe && u8[1] === 0xff) || (u8[0] === 0xff && u8[1] === 0xfe))) {
    // QUtil::utf16_to_utf8
    const le = u8[0] === 0xff
    let out = '', cp = 0
    for (let i = 2; i + 1 < n; i += 2) {
      const msb = le ? i + 1 : i, lsb = le ? i : i + 1
      const bits = (u8[msb] << 8) + u8[lsb]
      if ((bits & 0xfc00) === 0xd800) { cp = 0x10000 + ((bits & 0x3ff) << 10); continue }
      if ((bits & 0xfc00) === 0xdc00) cp += bits & 0x3ff
      else cp = bits
      out += String.fromCodePoint(cp)
      cp = 0
    }
    return out
  }
  if (n >= 3 && u8[0] === 0xef && u8[1] === 0xbb && u8[2] === 0xbf) {
    return new TextDecoder('utf-8').decode(u8.subarray(3))
  }
  let out = ''
  for (let i = 0; i < n; i++) {
    const ch = u8[i]
    let cp = ch
    if (ch >= 127 && ch <= 160) cp = PDFDOC_ALTOS[ch - 127]
    else if (ch >= 24 && ch <= 31) cp = PDFDOC_BAJOS[ch - 24]
    else if (ch === 173) cp = 0xfffd
    out += String.fromCodePoint(cp)
  }
  return out
}

/** `str(pikepdf.Name)`: «/» + el nombre ya sin `#xx`, decodificado como UTF-8 (pybind11). */
export function nombrePikepdf(nLatin1) {
  const b = new Uint8Array(nLatin1.length)
  for (let i = 0; i < nLatin1.length; i++) b[i] = nLatin1.charCodeAt(i) & 255
  return '/' + new TextDecoder('utf-8').decode(b)
}

/** `str(operando)` de pikepdf para un operando de contenido.js. */
export function strOperando(v) {
  if (v === null) return 'null'
  if (v === true) return 'True'
  if (v === false) return 'False'
  if (Array.isArray(v)) return '[' + v.map(strOperando).join(' ') + ']'
  if (v.i !== undefined) return String(Number(v.i))
  if (v.r !== undefined) return v.r
  if (v.n !== undefined) return nombrePikepdf(v.n)
  if (v.s !== undefined) return textoPikepdf(v.s)
  return ''
}

export class NoEsNumero extends Error {}
/** `float(operando)` de pikepdf: sólo números; cualquier otra cosa lanza (como el ValueError). */
export function floatOperando(v) {
  if (v && v.i !== undefined) return Number(v.i)
  if (v && v.r !== undefined) return Number(v.r)
  throw new NoEsNumero()
}

// ─── `repr()` de Python (para `obj_id = sha1(repr(sig))`) ──────────────────────────────────────
function reprFloat(x) {
  if (Number.isNaN(x)) return 'nan'
  if (!Number.isFinite(x)) return x > 0 ? 'inf' : '-inf'
  if (Object.is(x, -0)) return '-0.0'
  let s = String(x)                       // la representación más corta que vuelve al mismo double
  let neg = false
  if (s[0] === '-') { neg = true; s = s.slice(1) }
  let mant = s, exp = 0
  const ei = s.indexOf('e')
  if (ei >= 0) { mant = s.slice(0, ei); exp = parseInt(s.slice(ei + 1), 10) }
  const [ip, fp = ''] = mant.split('.')
  const todos = ip + fp
  const sinCeros = todos.replace(/^0+/, '')
  if (!sinCeros) return (neg ? '-' : '') + '0.0'
  const decpt = ip.length + exp - (todos.length - sinCeros.length)   // dígitos antes del punto
  const digitos = sinCeros.replace(/0+$/, '')
  let txt
  if (decpt > -4 && decpt <= 16) {
    if (decpt <= 0) txt = '0.' + '0'.repeat(-decpt) + digitos
    else if (decpt >= digitos.length) txt = digitos + '0'.repeat(decpt - digitos.length) + '.0'
    else txt = digitos.slice(0, decpt) + '.' + digitos.slice(decpt)
  } else {
    const e = decpt - 1
    txt = digitos[0] + (digitos.length > 1 ? '.' + digitos.slice(1) : '') + 'e' + (e < 0 ? '-' : '+') + String(Math.abs(e)).padStart(2, '0')
  }
  return (neg ? '-' : '') + txt
}

const NO_IMPRIMIBLE = /[\p{Cc}\p{Cf}\p{Cs}\p{Co}\p{Cn}\p{Zl}\p{Zp}\p{Zs}]/u
export function reprStr(s) {
  const comilla = (s.includes("'") && !s.includes('"')) ? '"' : "'"
  let out = comilla
  for (const ch of s) {
    const cp = ch.codePointAt(0)
    if (ch === '\\') out += '\\\\'
    else if (ch === comilla) out += '\\' + ch
    else if (ch === '\n') out += '\\n'
    else if (ch === '\r') out += '\\r'
    else if (ch === '\t') out += '\\t'
    else if (ch !== ' ' && NO_IMPRIMIBLE.test(ch)) {
      out += cp < 0x100 ? '\\x' + cp.toString(16).padStart(2, '0')
        : cp < 0x10000 ? '\\u' + cp.toString(16).padStart(4, '0') : '\\U' + cp.toString(16).padStart(8, '0')
    } else out += ch
  }
  return out + comilla
}

/**
 * `repr(valor)`: números enteros de JS se toman como `int` de Python (para eso se marcan con
 * `{int: n}`), los demás `number` son `float`; los arreglos son TUPLAS (así están las firmas).
 */
export function reprPy(v) {
  if (v === null || v === undefined) return 'None'
  if (v === true) return 'True'
  if (v === false) return 'False'
  if (typeof v === 'number') return reprFloat(v)
  if (typeof v === 'string') return reprStr(v)
  if (Array.isArray(v)) return v.length === 1 ? '(' + reprPy(v[0]) + ',)' : '(' + v.map(reprPy).join(', ') + ')'
  if (v.int !== undefined) return String(v.int)
  if (v.lista !== undefined) return '[' + v.lista.map(reprPy).join(', ') + ']'
  return String(v)
}

// ─── rectángulos de MuPDF (fitz/geometry.c) ─────────────────────────────────────────────────
export const rectValido = (r) => r[0] <= r[2] && r[1] <= r[3]
export const rectVacio = (r) => r[0] >= r[2] || r[1] >= r[3]            // fz_is_empty_rect / Rect.is_empty
export const RECT_VACIO = [0, 0, -1, -1]                                 // FZ_EMPTY_RECT

export function unionRect(a, b) {
  if (!rectValido(b)) return a
  if (!rectValido(a)) return b
  return [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[2], b[2]), Math.max(a[3], b[3])]
}

export function intersectRect(a, b) {
  // no colapsa: puede quedar «al revés» (ver dibujos.js)
  const r = [a[0], a[1], a[2], a[3]]
  if (r[0] < b[0]) r[0] = b[0]
  if (r[1] < b[1]) r[1] = b[1]
  if (r[2] > b[2]) r[2] = b[2]
  if (r[3] > b[3]) r[3] = b[3]
  return r
}

export function transformarPunto(x, y, m) {
  return [f(f(f(x * m[0]) + f(y * m[2])) + m[4]), f(f(f(x * m[1]) + f(y * m[3])) + m[5])]
}

/** `fz_transform_rect`, en float32 como MuPDF. */
export function transformarRect(r, m) {
  r = [r[0], r[1], r[2], r[3]]
  if (Math.abs(m[1]) < FLT_EPSILON && Math.abs(m[2]) < FLT_EPSILON) {
    if (m[0] < 0) { const t = r[0]; r[0] = r[2]; r[2] = t }
    if (m[3] < 0) { const t = r[1]; r[1] = r[3]; r[3] = t }
    const s = transformarPunto(r[0], r[1], m), t = transformarPunto(r[2], r[3], m)
    return [s[0], s[1], t[0], t[1]]
  }
  if (Math.abs(m[0]) < FLT_EPSILON && Math.abs(m[3]) < FLT_EPSILON) {
    if (m[1] < 0) { const t = r[0]; r[0] = r[2]; r[2] = t }
    if (m[2] < 0) { const t = r[1]; r[1] = r[3]; r[3] = t }
    const s = transformarPunto(r[0], r[1], m), t = transformarPunto(r[2], r[3], m)
    return [s[0], s[1], t[0], t[1]]
  }
  const invalido = r[0] > r[2] || r[1] > r[3]
  const s = transformarPunto(r[0], r[1], m), t = transformarPunto(r[0], r[3], m)
  const u = transformarPunto(r[2], r[3], m), v = transformarPunto(r[2], r[1], m)
  let out = [Math.min(s[0], t[0], u[0], v[0]), Math.min(s[1], t[1], u[1], v[1]),
             Math.max(s[0], t[0], u[0], v[0]), Math.max(s[1], t[1], u[1], v[1])]
  if (invalido) out = [out[2], out[3], out[0], out[1]]
  return out
}

const rectsSeSolapan = (a, b) => !(a[0] >= b[2] || a[1] >= b[3] || a[2] <= b[0] || a[3] <= b[1])   // JM_rects_overlap

// ─── el documento ───────────────────────────────────────────────────────────────────────────
/** `fitz.open(bytes)`: cada apertura es un documento NUEVO, con sus capas en el estado del archivo. */
export function abrir(mupdf, bytes) {
  return mupdf.Document.openDocument(bytes, 'application/pdf')
}

const nulo = (o) => !o || o.isNull()

/** `layer_ui_configs()`: [{number, text, on}] en el orden del /Order. */
export function capasUi(doc) {
  const out = []
  const n = doc.countLayers()
  for (let i = 0; i < n; i++) out.push({ number: i, text: doc.getLayerName(i), on: doc.isLayerVisible(i) })
  return out
}

/**
 * `set_layer_ui_config(number, action)`: 0 = mostrar (`pdf_select_layer_config_ui`), 1 = INVERTIR
 * (`pdf_toggle…`), 2 = ocultar (`pdf_deselect…`). ⚠️ El motor usa `action=1` como si fuera «ocultar»:
 * es un toggle, y una capa que ya viniera apagada en el archivo se ENCENDERÍA. Se copia tal cual.
 */
export function configurarCapa(doc, number, action) {
  if (action === 1) doc.setLayerVisible(number, !doc.isLayerVisible(number))
  else doc.setLayerVisible(number, action === 0)
}

/** `get_ocgs()`: los nombres de /OCProperties /OCGs (sin orden: se usa como conjunto). */
export function nombresOcgs(doc) {
  const out = []
  try {
    const ocgs = doc.getTrailer().get('Root').get('OCProperties').get('OCGs')
    if (nulo(ocgs) || !ocgs.isArray()) return out
    for (let i = 0; i < ocgs.length; i++) {
      const nm = ocgs.get(i).get('Name')
      out.push(nulo(nm) ? '' : nm.asString())
    }
  } catch { /* sin OCProperties */ }
  return out
}

/** `molde_real._nombres_oc(operando, page)`: el/los nombre(s) de capa de un `BDC /OC`. */
export function nombresOc(page, operando) {
  try {
    let obj = null
    if (operando && operando.n !== undefined) {
      const props = page.getObject().get('Resources').get('Properties')
      if (nulo(props)) return []
      obj = props.get(operando.n)
      if (nulo(obj)) return []
    } else return []
    const tipo = obj.get('Type')
    if (nulo(tipo) || !tipo.isName()) return []
    if (tipo.asName() === 'OCG') {
      const nm = obj.get('Name')
      return nulo(nm) ? [] : [nm.asString()]
    }
    if (tipo.asName() === 'OCMD') {
      const ocgs = obj.get('OCGs')
      if (nulo(ocgs)) return []
      if (ocgs.isArray()) {
        const out = []
        for (let i = 0; i < ocgs.length; i++) {
          const nm = ocgs.get(i).get('Name')
          if (nulo(nm)) return []
          out.push(nm.asString())
        }
        return out
      }
      const nm = ocgs.get('Name')
      return nulo(nm) ? [] : [nm.asString()]
    }
  } catch { /* como el except de Python */ }
  return []
}

// ─── `page.get_text("dict")` ─────────────────────────────────────────────────────────────────
const OPCIONES_STEXT = 'preserve-ligatures,preserve-whitespace,preserve-images,use-cid-for-unknown-unicode'   // TEXTFLAGS_DICT (el recorte a la página viene activo por defecto)
const MAX_ASC = 8, MAX_DESC = -2                                        // FZ_MAX_TRUSTWORTHY_ASCENT/DESCENT

function nombreFuenteMuPDF(bf) {
  // `fz_font.name` tiene 32 bytes: fz_strlcpy corta a 31 (en UTF-8)
  const b = new TextEncoder().encode(bf)
  return b.length <= 31 ? bf : new TextDecoder('utf-8').decode(b.subarray(0, 31))
}

function metricasDescriptor(desc) {
  // pdf_load_font_descriptor: /Ascent y /Descent (float32) → font->ascender/descender
  if (nulo(desc)) return null
  const a = desc.get('Ascent'), d = desc.get('Descent')
  if (nulo(a) || !a.isNumber() || nulo(d) || !d.isNumber()) return null   // sin dato → lo pone la cara (no se puede leer acá)
  let ascent = f(a.asNumber()), descent = f(d.asNumber())
  if (descent > 0) descent = -descent
  if (ascent <= 0 || ascent > MAX_ASC * 1000 || descent < MAX_DESC * 1000) return { asc: 0.800000011920929, dsc: -0.20000000298023224 }
  return { asc: f(ascent / 1000), dsc: f(descent / 1000) }
}

/** ascender/descender por nombre de fuente (como los ve `fz_font_name`), de los recursos de la página. */
function metricasFuentes(page) {
  const out = new Map()
  const vistos = new Set()
  const registrar = (fd) => {
    try {
      const bf = fd.get('BaseFont')
      if (nulo(bf) || !bf.isName()) return
      const clave = nombreFuenteMuPDF(bf.asName())
      if (out.has(clave)) return
      let desc = fd.get('FontDescriptor')
      if (nulo(desc)) {
        const dfs = fd.get('DescendantFonts')
        if (!nulo(dfs) && dfs.isArray() && dfs.length) desc = dfs.get(0).get('FontDescriptor')
      }
      out.set(clave, metricasDescriptor(desc))
    } catch { /* fuente rara: sin métricas */ }
  }
  const recorrer = (res, prof) => {
    if (nulo(res) || prof > 8) return
    const fonts = res.get('Font')
    if (!nulo(fonts) && fonts.isDictionary()) fonts.forEach((v) => registrar(v))
    const xo = res.get('XObject')
    if (!nulo(xo) && xo.isDictionary()) {
      xo.forEach((x) => {
        try {
          if (x.isIndirect()) { const k = x.asIndirect(); if (vistos.has(k)) return; vistos.add(k) }
          const st = x.get('Subtype')
          if (!nulo(st) && st.isName() && st.asName() === 'Form') recorrer(x.get('Resources'), prof + 1)
        } catch { /* nada */ }
      })
    }
  }
  try { recorrer(page.getObject().get('Resources'), 0) } catch { /* sin recursos */ }
  return out
}

/** `JM_char_quad`: el recuadro del glifo, recalculado cuando ascender−descender < 1. */
function quadDeChar(ch, linea, metr) {
  if (linea.wmode) return ch.quad
  const m = metr.get(ch.font.getName()) || { asc: 0.800000011920929, dsc: -0.20000000298023224 }
  let asc = m.asc, dsc = m.dsc
  const fsize = ch.size
  let ascDsc = f(f(asc - dsc) + FLT_EPSILON)
  if (ascDsc >= 1) return ch.quad
  if (asc < 1e-3) { dsc = -0.10000000149011612; asc = 0.8999999761581421; ascDsc = 1.0 }
  if (ascDsc < 1) { dsc = f(dsc / ascDsc); asc = f(asc / ascDsc) }
  ascDsc = f(asc - dsc)
  asc = f(f(asc * fsize) / ascDsc)
  dsc = f(f(dsc * fsize) / ascDsc)
  const c = linea.dir[0], s = linea.dir[1]
  const trm1 = [c, -s, s, c, 0, 0], trm2 = [c, s, -s, c, 0, 0]
  if (c === -1) { trm1[3] = 1; trm2[3] = 1 }
  const ox = ch.origin[0], oy = ch.origin[1]
  const xlate1 = [1, 0, 0, 1, -ox, -oy], xlate2 = [1, 0, 0, 1, ox, oy]
  const tq = (q, M) => {
    const out = []
    for (let i = 0; i < 8; i += 2) { const p = transformarPunto(q[i], q[i + 1], M); out.push(p[0], p[1]) }
    return out
  }
  let q = tq(tq(ch.quad, xlate1), trm1)             // [ulx, uly, urx, ury, llx, lly, lrx, lry]
  if (c === 1 && q[1] > 0) { q[1] = asc; q[3] = asc; q[5] = dsc; q[7] = dsc } else { q[1] = -asc; q[3] = -asc; q[5] = -dsc; q[7] = -dsc }
  if (q[4] < 0) { q[4] = 0; q[0] = 0 }
  const cwidth = f(q[6] - q[4])
  if (cwidth < FLT_EPSILON) {
    const glyph = ch.font.encodeCharacter(ch.c.codePointAt(0))
    if (glyph) {
      const fwidth = ch.font.advanceGlyph(glyph, linea.wmode)
      q[6] = f(q[4] + f(fwidth * fsize)); q[2] = q[6]
    }
  }
  q = tq(tq(q, trm2), xlate2)
  return q
}

function bboxDeChar(ch, linea, metr) {
  const q = quadDeChar(ch, linea, metr)
  const r = [Math.min(q[0], q[2], q[4], q[6]), Math.min(q[1], q[3], q[5], q[7]),
             Math.max(q[0], q[2], q[4], q[6]), Math.max(q[1], q[3], q[5], q[7])]
  if (!linea.wmode) return r
  if (r[3] < r[1] + ch.size) r[1] = r[3] - ch.size
  return r
}

/** `JM_font_name`: sin el prefijo de subconjunto «ABCDEF+». */
function nombreFuente(nombre) {
  const s = nombre.indexOf('+')
  return (s === -1 || s !== 6) ? nombre : nombre.slice(7)
}

const rgbEntero = (color) => (Math.round(color[0] * 255) << 16) | (Math.round(color[1] * 255) << 8) | Math.round(color[2] * 255)

/**
 * Los bloques de texto de `page.get_text("dict")` (sólo `type == 0`): [{lines: [{bbox, spans:
 * [{text, origin, bbox, size, font, color, flags}]}]}]. `font` viene como lo da PyMuPDF (sin
 * prefijo de subconjunto); `color` es el sRGB entero.
 */
export function textoDict(page) {
  const tp = page.getBounds()
  const metr = metricasFuentes(page)
  const st = page.toStructuredText(OPCIONES_STEXT)
  const bloques = []
  let bloque = null, linea = null
  try {
    st.walk({
      beginTextBlock(bbox) {
        bloque = rectVacio(intersectRect(tp, bbox)) ? null : { type: 0, lines: [] }
        if (bloque) bloques.push(bloque)
      },
      beginLine(bbox, wmode, dir) {
        if (!bloque) return
        linea = { wmode, dir, chars: [], primero: null }
      },
      onChar(c, origin, font, size, quad, color) {
        if (!linea) return
        if (!linea.primero) linea.primero = origin
        linea.chars.push({ c, origin, font, size, quad, color })
      },
      endLine() {
        if (!linea) return
        const spans = []
        let lineRect = RECT_VACIO
        let span = null, viejo = null
        const volcar = () => {
          if (!span) return
          spans.push({ text: span.text, origin: span.origin, bbox: span.rect, size: span.size, font: span.font, color: span.color, flags: span.flags })
          lineRect = unionRect(lineRect, span.rect)
          span = null
        }
        for (const ch of linea.chars) {
          const r = bboxDeChar(ch, linea, metr)
          if (!rectsSeSolapan(tp, r)) continue
          let flags = 0
          if (linea.wmode === 0 && linea.dir[0] === 1 && linea.dir[1] === 0) {
            flags += ch.origin[1] < f(linea.primero[1] - f(ch.size * 0.10000000149011612)) ? 1 : 0
          }
          flags += (ch.font.isItalic() ? 2 : 0) + (ch.font.isSerif() ? 4 : 0) + (ch.font.isMono() ? 8 : 0) + (ch.font.isBold() ? 16 : 0)
          const fuente = nombreFuente(ch.font.getName())
          const argb = rgbEntero(ch.color)
          if (!viejo || ch.size !== viejo.size || flags !== viejo.flags || argb !== viejo.argb || fuente !== viejo.fuente) {
            volcar()
            span = { size: ch.size, flags, font: fuente, color: argb & 0xffffff, origin: [ch.origin[0], ch.origin[1]], rect: r, text: '' }
            viejo = { size: ch.size, flags, argb, fuente }
          }
          span.rect = unionRect(span.rect, r)
          span.text += ch.c
        }
        volcar()
        bloque.lines.push({ bbox: lineRect, spans })
        linea = null
      },
    })
  } finally {
    st.destroy()
  }
  return bloques
}

// ─── `get_pixmap` ───────────────────────────────────────────────────────────────────────────
/** `page.get_pixmap(matrix=Matrix(zoom, zoom), alpha=…)`: por lista de dibujo, como PyMuPDF. */
export function pixmapMesa(mupdf, page, zoom, alpha = false) {
  const dl = page.toDisplayList(true)
  try {
    return dl.toPixmap(mupdf.Matrix.scale(zoom, zoom), mupdf.ColorSpace.DeviceRGB, alpha)
  } finally {
    dl.destroy()
  }
}

/** `a.std(axis=(0, 1)).mean()` sobre los 3 primeros canales (población, como numpy). */
export function desvioMedio(pix) {
  const w = pix.getWidth(), h = pix.getHeight(), n = pix.getNumberOfComponents(), stride = pix.getStride()
  const px = pix.getPixels()
  const total = w * h
  if (!total) return NaN
  let suma = 0
  for (let c = 0; c < 3; c++) {
    let s = 0
    for (let y = 0; y < h; y++) { const fila = y * stride; for (let x = 0; x < w; x++) s += px[fila + x * n + c] }
    const media = s / total
    let s2 = 0
    for (let y = 0; y < h; y++) { const fila = y * stride; for (let x = 0; x < w; x++) { const d = px[fila + x * n + c] - media; s2 += d * d } }
    suma += Math.sqrt(s2 / total)
  }
  return suma / 3
}

/** `_mesa_tiene_diseno(doc, mesa)`: la mesa dibujada a 0,04 tiene variación (std media ≥ 8). */
export function mesaTieneDiseno(mupdf, page) {
  const pix = pixmapMesa(mupdf, page, 0.04, false)
  try { return desvioMedio(pix) >= 8 } finally { pix.destroy() }
}

export function base64De(u8) {
  if (typeof Buffer !== 'undefined') return Buffer.from(u8.buffer, u8.byteOffset, u8.byteLength).toString('base64')
  let s = ''
  for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000))
  return btoa(s)
}
