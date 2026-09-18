// LA FICHA TÉCNICA (A4) EN EL NAVEGADOR — PLAN_NAVEGADOR.md, etapa 4, punto 4.
//
// Traducción de `ficha_tecnica.py` (PyMuPDF) sobre mupdf.js: el PDF que sale junto con la tizada, con
// la TABLA DE TALLES (la planilla del pedido tal cual) arriba y, abajo, el MOLDE GUÍA (las piezas
// de la variable con el diseño adentro: el MISMO PDF de pieza que nestea la hoja), la tipografía con
// la que sale cada campo y lo que NO se sublima. El contrato `verificar_navegador_ficha.py` exige
// el mismo texto, el mismo content-stream y el mismo dibujo que el Python.
//
// 🔴 LO QUE HAY QUE COPIAR DE PYMUPDF, NO DE PDF «EN GENERAL». PyMuPDF no escribe operadores a
// mano: `insert_text` / `draw_rect` / `draw_line` / `show_pdf_page` / `insert_image` arman cadenas
// con reglas propias, y acá se arman LAS MISMAS:
//   · los números van con el `%g` de MuPDF (`fz_format_double`): el decimal MÁS CORTO que vuelve
//     al mismo float de 32 bits, sin cero a la izquierda («.1», «815.89», «1000000»). No es el
//     `toPrecision` de JS (ese busca el double): se le pide al propio mupdf (`newReal(v).toString()`
//     imprime con la misma rutina; verificado en 5800 valores, exacto con |v| < 1e7 — más que
//     suficiente para una hoja A4 de 842 pt);
//   · `draw_rect`/`draw_line` pasan los puntos por `fz_transform_point` (float32) y por `JM_TUPLE`
//     (`round(x, 5)`, y 0 si |x| < 1e-4); `insert_text` NO: `top = alto - y` en doble;
//   · `show_pdf_page` escribe DOS Form XObjects (la página fuente entera como `/fullpage` y uno
//     que la posiciona con `/BBox` = el rect de la fuente y `/Matrix` = `calc_matrix`) y en la
//     página ` q /fzFrmN Do Q `; la matriz se calcula con `fz_concat`/`fz_transform_rect` en float32
//     y después `JM_TUPLE`;
//   · el texto va en hexadecimal (`[<…>]TJ`) con el código Latin-1 de cada carácter y «b7» (·) para
//     todo lo que no entra en un byte («…», «→», emojis): así se ve en la ficha de hoy;
//   · `get_text_length` (el recorte a `max_w`) tiene una particularidad de PyMuPDF que hay que
//     reproducir: avanza `pos` con la cantidad de BYTES UTF-8 del carácter, sobre un índice de
//     CARACTERES, así que después de una «ñ» se saltea el carácter siguiente al medir. Sin
//     copiarlo, el recorte cae en otra letra.
//
// ⚠️ EL OBJETO QUE NO SE SUBLIMA VIENE COMO PDF. Python lo recibe como SVG (`get_svg_image`) y lo
// convierte con el lector de SVG de MuPDF; ese lector NO está compilado en mupdf.js («cannot find
// document handler for file type: image/svg+xml»). En el navegador el arte es un PDF, así que el
// objeto llega como `pdf` (bytes de un PDF de una página) y se incrusta igual que una pieza. Si sólo
// hay `svg`, se cae a la miniatura (`thumb`) como hace Python cuando la conversión falla.
//
// ENTRADA: `generarFicha(mupdf, {titulo, subtitulo, planilla, moldesGuia})`
//   planilla   = {columnas: [{id, label}], filas: [{colId: valor}]}
//   moldesGuia = [{nombre, diseno, variante, opciones,
//                  piezas:   [{nombre, tela, pdf: Uint8Array}],
//                  fuentes:  [{campo, fuente, pedida, sustituida}],
//                  procesos: [{nombre, proceso, pieza, sin_marca, pdf?: Uint8Array, svg?: b64,
//                              thumb?: b64|Uint8Array, medidas: [{talles, texto}], nota?}]}]
// Devuelve los bytes del PDF (Uint8Array).
import { pyRound, pyStrip } from '../py.js'
import { sha1HexBytes } from '../sha1.js'
import { dibujarMesa } from '../vista/dibujar.js'

// A4 en puntos (72 dpi). Retrato.
export const A4_W = 595.28
export const A4_H = 841.89
const MARGEN = 36                      // 0.5"
const GRIS = [0.45, 0.45, 0.45]
const NEGRO = [0.1, 0.1, 0.1]
const LINEA = [0.75, 0.75, 0.75]
const ACENTO = [0.0, 0.55, 0.62]
const ROJO = [0.72, 0.13, 0.13]        // falta un dato que alguien tiene que completar
const FONT = 'helv'
const FONT_B = 'hebo'

const f32 = Math.fround
// `page.mediabox_size.y`: PyMuPDF lee el MediaBox como float de 32 bits (841.89 → 841.8900146…)
const H32 = f32(A4_H)
// `~page.transformation_matrix` de una página A4 sin rotar: (1, 0, 0, -1, -0, H32) — la inversa la
// calcula `util_invert_matrix` en Python a partir de los float32 de `pdf_page_transform`.
const IPCTM = [1, 0, 0, -1, -0, H32]

// ─── lo que Python hace con los valores (str, truthiness, dict.get) ─────────────────────────
const verdad = (v) => !(v === null || v === undefined || v === false || v === 0 || v === '' ||
  (Array.isArray(v) && v.length === 0) || (v instanceof Uint8Array && v.length === 0) ||
  (typeof v === 'object' && !Array.isArray(v) && !(v instanceof Uint8Array) && Object.keys(v).length === 0))
/** `x or ""` */
const oVacio = (v) => (verdad(v) ? v : '')
/** `str(x)` (con `None` → "None", como un f-string de Python) */
const fstr = (v) => (v === null || v === undefined ? 'None' : String(v))
/** `"" if s is None else str(s)` */
const pyStr = (v) => (v === null || v === undefined ? '' : String(v))
/** `d.get(k, default)` con las claves de un JSON (siempre texto) */
const pyGet = (d, k, def) => (typeof k === 'string' && Object.prototype.hasOwnProperty.call(d, k) ? d[k] : def)
/** `str.capitalize()`: la primera en mayúscula, el resto en minúscula */
const capitalize = (s) => { const c = Array.from(s); return c.length ? c[0].toUpperCase() + c.slice(1).join('').toLowerCase() : '' }
/** `str.splitlines()` (sin los saltos; sin un último elemento vacío) */
function pySplitlines(s) {
  const partes = s.split(/\r\n|[\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029]/)
  if (partes.length && partes[partes.length - 1] === '') partes.pop()
  return partes
}

/** Nombre de la pieza SIN el número final: «Frente 1» → «Frente» (`_generico`). */
export function generico(nombre) {
  const s = pyStr(oVacio(nombre))
  return pyStrip(s.replace(/[\s\x1c-\x1f]+\p{Nd}+[\s\x1c-\x1f]*(?=\n?$)/u, '')) || s
}

// ─── la aritmética de MuPDF en float32 (fz_transform_point / fz_transform_rect / fz_concat) ──
function transformarPunto(x, y, m) {
  // fz_transform_point_xy: x' = x*a + y*c + e ; y' = x*b + y*d + f, cada operación en float
  const xf = f32(x), yf = f32(y)
  return [f32(f32(f32(xf * m[0]) + f32(yf * m[2])) + m[4]), f32(f32(f32(xf * m[1]) + f32(yf * m[3])) + m[5])]
}

function transformarRect(r, m) {
  // fz_transform_rect de MuPDF 1.26: con la matriz sin giro (b y c bajo FLT_EPSILON) da vuelta los
  // lados que la matriz invierte y transforma dos esquinas; si no, las cuatro y toma min/max.
  let [x0, y0, x1, y1] = r.map(f32)
  if (Math.abs(m[1]) < 1.1920929e-7 && Math.abs(m[2]) < 1.1920929e-7) {
    if (m[0] < 0) [x0, x1] = [x1, x0]
    if (m[3] < 0) [y0, y1] = [y1, y0]
    const s = transformarPunto(x0, y0, m), t = transformarPunto(x1, y1, m)
    return [s[0], s[1], t[0], t[1]]
  }
  const s = transformarPunto(x0, y0, m), t = transformarPunto(x0, y1, m)
  const u = transformarPunto(x1, y1, m), v = transformarPunto(x1, y0, m)
  return [Math.min(s[0], t[0], u[0], v[0]), Math.min(s[1], t[1], u[1], v[1]),
    Math.max(s[0], t[0], u[0], v[0]), Math.max(s[1], t[1], u[1], v[1])]
}

function concatMatriz(l, r) {
  // fz_concat (float32, de izquierda a derecha como lo evalúa C)
  l = l.map(f32); r = r.map(f32)
  return [
    f32(f32(l[0] * r[0]) + f32(l[1] * r[2])),
    f32(f32(l[0] * r[1]) + f32(l[1] * r[3])),
    f32(f32(l[2] * r[0]) + f32(l[3] * r[2])),
    f32(f32(l[2] * r[1]) + f32(l[3] * r[3])),
    f32(f32(f32(l[4] * r[0]) + f32(l[5] * r[2])) + r[4]),
    f32(f32(f32(l[4] * r[1]) + f32(l[5] * r[3])) + r[5]),
  ]
}

function invertirMatriz(m) {
  // `util_invert_matrix` de PyMuPDF: la matriz llega en float32, la cuenta se hace en doble y
  // cada componente se guarda en un campo float de C (se redondea al asignar).
  const [a, b, c, d, e, f] = m.map(f32)
  const det = a * d - b * c
  if (!(det < -2.220446049250313e-16 || det > 2.220446049250313e-16)) return null
  const rdet = 1 / det
  const da = f32(d * rdet), db = f32((-b) * rdet), dc = f32((-c) * rdet), dd = f32(a * rdet)
  const a2 = (-e) * da - f * dc
  const df = f32((-e) * db - f * dd)
  return [da, db, dc, dd, f32(a2), df]
}

/** `JM_TUPLE`: `round(x, 5) if abs(x) >= 1e-4 else 0` */
const jmTuple = (vals) => vals.map((x) => (Math.abs(x) >= 1e-4 ? pyRound(x, 5) : 0))

// ─── el contexto de UNA ficha: el documento, las dos tipografías y el formateador ───────────
// Los ascender/descender son los que `fz_font_ascender/descender` devuelven para las Base-14 de
// MuPDF (URW Nimbus Sans), en float32; mupdf.js no los expone y sólo importan para `lineheight`
// de un texto con más de una línea.
const FUENTES = {
  helv: { nombre: 'Helvetica', asc: f32(1.075), desc: f32(-0.299) },
  hebo: { nombre: 'Helvetica-Bold', asc: f32(1.07), desc: f32(-0.307) },
}

function crearCtx(mupdf) {
  const doc = new mupdf.PDFDocument()
  const fuentes = {}
  for (const [k, v] of Object.entries(FUENTES)) fuentes[k] = { ...v, font: new mupdf.Font(v.nombre), obj: null }
  // `_format_g` = el `%g` de MuPDF: se lo pide al propio mupdf, que imprime un real con esa rutina
  const g = (v) => { const o = doc.newReal(v); const s = o.toString(); try { o.destroy() } catch { /* nada */ } return s }
  return { mupdf, doc, fuentes, g, paginas: [] }
}

function cerrarCtx(ctx) {
  for (const f of Object.values(ctx.fuentes)) { try { f.font.destroy() } catch { /* nada */ } }
  try { ctx.doc.destroy() } catch { /* nada */ }
}

function nuevaPagina(ctx) {
  // una página en construcción: sus trozos de contenido (uno por cada llamada de PyMuPDF, en
  // orden), sus XObjects y las fuentes que usa; se materializa al final (el «Pág. x/y» va último)
  const pg = { trozos: [], xobjs: [], nFrm: 0, nImg: 0, fuentes: new Set() }
  ctx.paginas.push(pg)
  return pg
}

// ─── texto: get_text_length + insert_text ───────────────────────────────────────────────────
// `fz_windows_1252_from_unicode`: ASCII y 160-255 tal cual, los 27 especiales de cp1252, y -1
// (→ «·», 0xB7) para todo lo demás. Es sólo para MEDIR: el estampado usa el código Latin-1.
const CP1252 = { 338: 140, 339: 156, 352: 138, 353: 154, 376: 159, 381: 142, 382: 158, 402: 131, 710: 136,
  732: 152, 8211: 150, 8212: 151, 8216: 145, 8217: 146, 8218: 130, 8220: 147, 8221: 148, 8222: 132,
  8224: 134, 8225: 135, 8226: 149, 8230: 133, 8240: 137, 8249: 139, 8250: 155, 8364: 128 }
const cp1252 = (u) => (u < 128 ? u : (u >= 160 && u < 256) ? u : (CP1252[u] ?? -1))

/** `fitz.get_text_length(text, fontname, fontsize)` con la Base-14 (`util_measure_string`). */
export function largoTexto(ctx, texto, fontname, size) {
  const font = ctx.fuentes[fontname].font
  const cs = Array.from(texto)
  let w = 0, pos = 0
  while (pos < cs.length) {
    const u = cs[pos].codePointAt(0)
    // `t, c = fz_chartorune(text[pos:]); pos += t`: t son BYTES UTF-8 sobre un índice de caracteres
    pos += u < 0x80 ? 1 : u < 0x800 ? 2 : u < 0x10000 ? 3 : 4
    let c = cp1252(u)
    if (c < 0) c = 0xB7
    w += font.advanceGlyph(font.encodeCharacter(c), 0)
  }
  return w * size
}

/** `getTJstr` para una fuente simple que no es Symbol/ZapfDingbats: un byte por carácter. */
function tjStr(t) {
  if (t.startsWith('[<') && t.endsWith('>]')) return t
  if (!t) return '[<>]'
  let o = ''
  for (const ch of t) { const c = ch.codePointAt(0); o += c < 256 ? c.toString(16).padStart(2, '0') : 'b7' }
  return '[<' + o + '>]'
}

/** `ColorCode(c, f)`: "r g b RG " / "r g b rg " (1 valor → G/g, 4 → K/k). */
function colorCode(ctx, c, f) {
  if (!verdad(c)) return ''
  if (typeof c === 'number') c = [c]
  const s = c.map((v) => ctx.g(v)).join(' ') + ' '
  if (c.length === 1) return s + (f === 'c' ? 'G ' : 'g ')
  if (c.length === 3) return s + (f === 'c' ? 'RG ' : 'rg ')
  return s + (f === 'c' ? 'K ' : 'k ')
}

/** `Page.insert_text((x, y), s, fontsize, fontname, color)` (sin giro, sin opacidad, sin capa). */
function insertarTexto(ctx, pg, x, y, buffer, size, fontname, color) {
  if (!verdad(buffer)) return 0
  const text = pySplitlines(String(buffer))
  if (!text.length) return 0
  const fd = ctx.fuentes[fontname]
  const lheight = (fd.asc - fd.desc <= 1) ? size * 1.2 : size * (fd.asc - fd.desc)
  const tab = text.map(tjStr)
  // con render_mode 0 y sin `fill`, PyMuPDF pone el mismo color de trazo y de relleno
  const colorStr = colorCode(ctx, color, 'c'), fillStr = colorCode(ctx, color, 'f')
  const top = H32 - y - 0.0            // height - point.y - self.y (cropbox en el origen)
  const left = x + 0.0
  let nres = `\nq\nBT\n1 0 0 1 ${ctx.g(left)} ${ctx.g(top)} Tm\n/${fontname} ${ctx.g(size)} Tf `
  if (color !== null && color !== undefined) nres += colorStr + fillStr
  nres += tab[0]
  let nlines = 1
  let space = top
  if (tab.length > 1) nres += `TJ\n0 -${ctx.g(lheight)} TD\n`
  else nres += 'TJ'
  for (let i = 1; i < tab.length; i++) {
    if (space < lheight) break
    if (i > 1) nres += '\nT* '
    nres += tab[i] + 'TJ'
    space -= lheight
    nlines++
  }
  nres += '\nET\nQ\n'
  pg.trozos.push(nres)
  pg.fuentes.add(fontname)
  return nlines
}

/** `_texto`: escribe recortando a `maxW` (letra a letra, midiendo como PyMuPDF). Devuelve el ancho. */
function texto(ctx, pg, x, y, s, size = 9, color = NEGRO, bold = false, maxW = null) {
  s = pyStr(s)
  const fn = bold ? FONT_B : FONT
  if (verdad(maxW)) {
    let cs = Array.from(s)
    while (cs.length && largoTexto(ctx, cs.join(''), fn, size) > maxW) cs = cs.slice(0, -1)
    s = cs.join('')
  }
  insertarTexto(ctx, pg, x, y, s, size, fn, color)
  return largoTexto(ctx, s, fn, size)
}

// ─── formas: Shape.draw_rect / draw_line + finish + commit ──────────────────────────────────
function terminar(ctx, drawCont, { width = 1, color = [0], fill = null, closePath = true, evenOdd = false }) {
  // `Shape.finish` (sin dashes, sin cap/join, sin opacidad, sin capa, sin morph)
  if (width === 0) color = null
  else if (color === null || color === undefined) width = 0
  const colorStr = colorCode(ctx, color, 'c'), fillStr = colorCode(ctx, fill, 'f')
  if (width !== 1 && width !== 0) drawCont += ctx.g(width) + ' w\n'
  if (closePath) drawCont += 'h\n'
  if (color !== null && color !== undefined) drawCont += colorStr
  if (fill !== null && fill !== undefined) {
    drawCont += fillStr
    if (color !== null && color !== undefined) drawCont += evenOdd ? 'B*\n' : 'B\n'
    else drawCont += evenOdd ? 'f*\n' : 'f\n'
  } else drawCont += 'S\n'
  return '\nq\n' + drawCont + 'Q\n'
}

/** `page.draw_rect(Rect(x0, y0, x1, y1), color=, fill=, width=)` */
function dibujarRect(ctx, pg, r, opts = {}) {
  const [x0, y0, x1, y1] = r
  // `r.bl * self.ipctm` (float32) + [width, height] (doble) → JM_TUPLE → %g
  const bl = transformarPunto(x0, y1, IPCTM)
  const vals = jmTuple([bl[0], bl[1], Math.max(0, x1 - x0), Math.max(0, y1 - y0)])
  pg.trozos.push(terminar(ctx, vals.map((v) => ctx.g(v)).join(' ') + ' re\n', { closePath: true, ...opts }))
}

/** `page.draw_line(p1, p2, color=, width=)` */
function dibujarLinea(ctx, pg, p1, p2, color, width = 1) {
  const a = jmTuple(transformarPunto(p1[0], p1[1], IPCTM)), b = jmTuple(transformarPunto(p2[0], p2[1], IPCTM))
  const cont = `${a.map((v) => ctx.g(v)).join(' ')} m\n${b.map((v) => ctx.g(v)).join(' ')} l\n`
  pg.trozos.push(terminar(ctx, cont, { color, width, closePath: false }))
}

// ─── show_pdf_page: una página de otro PDF, incrustada vectorial ────────────────────────────
function leerCaja(obj) {
  // `pdf_to_rect`: cuatro reales, normalizados (x0 ≤ x1, y0 ≤ y1), en float32
  if (!obj || obj.isNull() || !obj.isArray() || obj.length < 4) return null
  const v = []
  for (let i = 0; i < 4; i++) v.push(f32(Number(obj.get(i).asNumber())))
  return [Math.min(v[0], v[2]), Math.min(v[1], v[3]), Math.max(v[0], v[2]), Math.max(v[1], v[3])]
}

function leerContenido(pageObj) {
  // `JM_read_contents`: los streams de la página, unidos con UN ESPACIO
  const cont = pageObj.get('Contents')
  if (!cont || cont.isNull()) return new Uint8Array(0)
  if (!cont.isArray()) return cont.readStream().asUint8Array().slice()
  const partes = []
  for (let i = 0; i < cont.length; i++) {
    const it = cont.get(i)
    if (it.isStream()) partes.push(it.readStream().asUint8Array().slice())
    else partes.push(new Uint8Array(0))
  }
  const out = new Uint8Array(partes.reduce((a, p) => a + p.length, 0) + Math.max(0, partes.length - 1))
  let k = 0
  partes.forEach((p, i) => { if (i) out[k++] = 32; out.set(p, k); k += p.length })
  return out
}

function calcMatriz(sr, tr) {
  // `show_pdf_page.calc_matrix(sr, tr, keep=True, rotate=0)` con las cuentas de PyMuPDF: los
  // Point se suman/dividen en doble, las matrices se concatenan con `fz_concat` (float32) y el
  // rect se transforma con `fz_transform_rect` (float32); al final `JM_TUPLE`.
  const smp = [(sr[0] + sr[2]) * 0.5, (sr[1] + sr[3]) * 0.5]
  const tmp = [(tr[0] + tr[2]) * 0.5, (tr[1] + tr[3]) * 0.5]
  // Matrix(0) = (round(cos 0, 8), round(sin 0, 8), -round(sin 0, 8), …) = (1, 0, -0, 1, 0, 0)
  let m = concatMatriz([1, 0, 0, 1, -smp[0], -smp[1]], [1, 0, -0, 1, 0, 0])
  const sr1 = transformarRect(sr, m)
  const ancho = (r) => Math.max(0, r[2] - r[0]), alto = (r) => Math.max(0, r[3] - r[1])
  let fw = ancho(tr) / ancho(sr1)
  let fh = alto(tr) / alto(sr1)
  fw = fh = Math.min(fw, fh)
  m = concatMatriz(m, [fw, 0, 0, fh, 0, 0])
  m = concatMatriz(m, [1, 0, 0, 1, tmp[0], tmp[1]])
  return jmTuple(m)
}

/** `page.show_pdf_page(rect, docsrc, pno, keep_proportion=True)` (`docsrc` = mupdf.PDFDocument). */
function mostrarPagina(ctx, pg, rect, srcDoc, pno = 0) {
  const [rx0, ry0, rx1, ry1] = rect
  if (rx0 >= rx1 || ry0 >= ry1) throw new Error('rect must be finite and not empty')
  const srcPage = srcDoc.loadPage(pno)
  try {
    const tar = transformarRect(rect, IPCTM)                 // el rect destino en coordenadas PDF
    const bounds = srcPage.getBounds()                        // src_page.rect
    const inv = invertirMatriz(srcPage.getTransform())        // ~src_page.transformation_matrix
    if (!inv) throw new Error('matrix not invertible')
    const srcRect = transformarRect(bounds, inv)
    if (srcRect[0] >= srcRect[2] || srcRect[1] >= srcRect[3]) throw new Error('clip must be finite and not empty')
    const matriz = calcMatriz(srcRect, tar)
    const doc = ctx.doc
    const srcObj = srcDoc.findPage(pno)
    // xobj1: la página fuente entera (`JM_xobject_from_page`): BBox = MediaBox, Matrix identidad,
    // los recursos de la página copiados y el contenido tal cual
    const mb = leerCaja(srcObj.getInheritable('MediaBox')) || bounds.map(f32)
    const d1 = doc.newDictionary()
    d1.put('Type', doc.newName('XObject'))
    d1.put('Subtype', doc.newName('Form'))
    const bb1 = doc.newArray(); for (const v of mb) bb1.push(doc.newReal(v)); d1.put('BBox', bb1)
    const m1 = doc.newArray(); for (const v of [1, 0, 0, 1, 0, 0]) m1.push(doc.newReal(v)); d1.put('Matrix', m1)
    const xo1 = doc.addStream(leerContenido(srcObj), d1)
    const res = srcObj.getInheritable('Resources')
    if (res && !res.isNull()) xo1.put('Resources', doc.graftObject(res))
    // xobj2: el que la posiciona (`_show_pdf_page`): BBox = el rect fuente, Matrix = la calculada
    const sub1 = doc.newDictionary(); sub1.put('fullpage', xo1)
    const sub = doc.newDictionary(); sub.put('XObject', sub1)
    const d2 = doc.newDictionary()
    d2.put('Type', doc.newName('XObject'))
    d2.put('Subtype', doc.newName('Form'))
    const bb2 = doc.newArray(); for (const v of srcRect) bb2.push(doc.newReal(v)); d2.put('BBox', bb2)
    const m2 = doc.newArray(); for (const v of matriz) m2.push(doc.newReal(v)); d2.put('Matrix', m2)
    d2.put('Resources', sub)
    const xo2 = doc.addStream('/fullpage Do', d2)
    const nombre = `fzFrm${pg.nFrm++}`
    pg.xobjs.push([nombre, xo2])
    pg.trozos.push(` q /${nombre} Do Q `)
  } finally {
    try { srcPage.destroy() } catch { /* nada */ }
  }
}

// ─── insert_image: la miniatura PNG (el respaldo cuando no hay vector) ──────────────────────
function calcMatrizImagen(width, height, trect, keep) {
  // `calc_image_matrix(w, h, clip, rotate=0, keep)`: los cocientes en doble sobre un rect float32;
  // la matriz final con `fz_concat`/`fz_scale`/`fz_translate` (float32)
  const trw = trect[2] - trect[0], trh = trect[3] - trect[1]
  let w = trw, h = trh, fw, fh
  if (keep) { const large = Math.max(width, height); fw = width / large; fh = height / large } else fw = fh = 1
  const small = Math.min(fw, fh)
  if (fw < 1) {
    if (trw / fw > trh / fh) { w = trh * small; h = trh } else { w = trw; h = trw / small }
  } else if (fw !== fh) {
    if (trw / fw > trh / fh) { w = trh / small; h = trh } else { w = trw; h = trw * small }
  } else { w = trw; h = trh }
  const tmp = [f32((trect[0] + trect[2]) / 2), f32((trect[1] + trect[3]) / 2)]
  let mat = [1, 0, 0, 1, -0.5, -0.5]
  mat = concatMatriz(mat, [1, 0, 0, 1, 0, 0])            // fz_rotate(0)
  mat = concatMatriz(mat, [w, 0, 0, h, 0, 0])            // fz_scale(w, h)
  mat = concatMatriz(mat, [1, 0, 0, 1, tmp[0], tmp[1]])  // fz_translate
  return mat
}

/** `page.insert_image(rect, stream=png, keep_proportion=True)` */
function insertarImagen(ctx, pg, rect, bytes, keep = true) {
  const [rx0, ry0, rx1, ry1] = rect
  if (rx0 >= rx1 || ry0 >= ry1) throw new Error('rect must be finite and not empty')
  const clip = transformarRect(rect, IPCTM)
  const img = new ctx.mupdf.Image(bytes)
  try {
    const w = img.getWidth(), h = img.getHeight()
    const ref = ctx.doc.addImage(img)
    const mat = calcMatrizImagen(w, h, clip, keep)
    const nombre = `fzImg${pg.nImg++}`
    pg.xobjs.push([nombre, ref])
    pg.trozos.push(`\nq\n${mat.map((v) => ctx.g(v)).join(' ')} cm\n/${nombre} Do\nQ\n`)
  } finally {
    try { img.destroy() } catch { /* nada */ }
  }
}

const aBytes = (v) => {
  if (v instanceof Uint8Array) return v
  if (typeof v === 'string') { const b = atob(v); const u = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u }
  return null
}

// ─── las partes de la ficha (mismos nombres que en Python) ─────────────────────────────────
function encabezado(ctx, pg, titulo, subtitulo, npag, total) {
  dibujarRect(ctx, pg, [0, 0, A4_W, 54], { fill: [0.97, 0.98, 0.98], color: null })
  texto(ctx, pg, MARGEN, 26, titulo, 15, NEGRO, true)
  if (verdad(subtitulo)) texto(ctx, pg, MARGEN, 44, subtitulo, 9, GRIS)
  texto(ctx, pg, A4_W - MARGEN - 60, 44, `Pág. ${npag}/${total}`, 8, GRIS)
  dibujarLinea(ctx, pg, [MARGEN, 54], [A4_W - MARGEN, 54], ACENTO, 1.4)
}

function seccion(ctx, pg, y, t) {
  texto(ctx, pg, MARGEN, y, t, 11, ACENTO, true)
  return y + 8
}

// ── TABLA DE TALLES (la planilla del pedido tal cual) ─────────────────────────────────────────
function dibujarTabla(ctx, pg, y, columnas, filas, yMax, fila0 = 0) {
  // Dibuja tantas filas como entren desde `y` hasta `yMax`; devuelve [yFinal, filasRestantes,
  // fila0Siguiente]. La 1ª columna es «#» con el NÚMERO DE FILA; `fila0` continúa la numeración.
  if (!columnas.length) return [y, [], fila0]
  const x0 = MARGEN, x1 = A4_W - MARGEN
  const W_NUM = 28                                   // ancho de la columna de números
  const wCol = (x1 - x0 - W_NUM) / columnas.length   // el resto se reparte entre las columnas reales
  const altoFila = 18
  const cx = (i) => (i === 0 ? x0 : x0 + W_NUM + (i - 1) * wCol)
  // cabecera (incluye el «#»)
  dibujarRect(ctx, pg, [x0, y, x1, y + altoFila], { fill: [0.13, 0.15, 0.17], color: null })
  texto(ctx, pg, x0 + 7, y + 12, '#', 8, [1, 1, 1], true)
  columnas.forEach((c, i) => {
    texto(ctx, pg, cx(i + 1) + 6, y + 12, pyStr(oVacio(c.label) || oVacio(c.id) || '').toUpperCase(),
      8, [1, 1, 1], true, wCol - 10)
  })
  y += altoFila
  let restantes = [], dibujadas = 0
  for (let r = 0; r < filas.length; r++) {
    const fila = filas[r]
    if (y + altoFila > yMax) { restantes = filas.slice(r); break }
    if (r % 2) dibujarRect(ctx, pg, [x0 + W_NUM, y, x1, y + altoFila], { fill: [0.96, 0.97, 0.98], color: null })
    // celda de número: fondo distinguido (como columna de títulos) + el número de fila
    dibujarRect(ctx, pg, [x0, y, x0 + W_NUM, y + altoFila], { fill: [0.90, 0.92, 0.94], color: null })
    texto(ctx, pg, x0 + 7, y + 12, String(fila0 + r + 1), 8, [0.25, 0.28, 0.32], true)
    columnas.forEach((c, i) => {
      const val = pyGet(fila, c.id, pyGet(fila, c.label, ''))
      texto(ctx, pg, cx(i + 1) + 6, y + 12, val, 8.5, NEGRO, false, wCol - 10)
    })
    y += altoFila
    dibujadas++
  }
  const top = y - altoFila * dibujadas - altoFila     // borde superior de la cabecera
  for (let i = 0; i < columnas.length + 2; i++) {     // líneas verticales (incluye la del «#»)
    const xx = i <= columnas.length ? cx(i) : x1
    dibujarLinea(ctx, pg, [xx, top], [xx, y], LINEA, 0.6)
  }
  dibujarRect(ctx, pg, [x0, top, x1, y], { color: LINEA, width: 0.8 })
  return [y, restantes, fila0 + dibujadas]
}

// ── MOLDE GUÍA (piezas de la variable, con el diseño recortado — el MISMO PDF que la tizada) ───
function dibujarPiezas(ctx, pg, y, piezas, yMax, cols = 5) {
  // Grilla de `cols` columnas; cada pieza en su TARJETA (sombra + fondo claro + borde) y adentro
  // el PDF real de la pieza (recorte NATIVO). Devuelve [yFinal, restantes].
  const x0 = MARGEN
  const ancho = A4_W - 2 * MARGEN
  const wCel = ancho / cols
  const gap = 5                          // aire entre tarjetas
  const hCel = 134                       // alto de la celda (tarjeta + rótulo)
  const hCard = hCel - 28                // alto de la tarjeta (la imagen); el rótulo es nombre + tela
  let restantes = [], filaY = y, i = 0
  while (i < piezas.length) {
    if (filaY + hCel > yMax) { restantes = piezas.slice(i); break }
    for (let c = 0; c < cols; c++) {
      if (i >= piezas.length) break
      const pz = piezas[i]; i++
      const cx = x0 + c * wCel
      const card = [cx + gap, filaY + gap, cx + wCel - gap, filaY + gap + hCard]
      // SOMBRA suave: una tarjeta gris apenas corrida atrás
      dibujarRect(ctx, pg, [card[0] + 1.6, card[1] + 2.0, card[2] + 1.6, card[3] + 2.0], { color: null, fill: [0.86, 0.87, 0.88] })
      // TARJETA: fondo casi blanco + borde fino
      dibujarRect(ctx, pg, card, { color: [0.80, 0.82, 0.84], width: 0.8, fill: [0.985, 0.99, 0.995] })
      let src = null
      try {
        src = new ctx.mupdf.PDFDocument(pz.pdf)
        const p0 = src.loadPage(0)
        const r0 = p0.getBounds()
        p0.destroy()
        const pad = 7
        const cardW = Math.max(0, card[2] - card[0]), cardH = Math.max(0, card[3] - card[1])
        const dispoW = cardW - 2 * pad, dispoH = cardH - 2 * pad
        const r0w = Math.max(0, r0[2] - r0[0]), r0h = Math.max(0, r0[3] - r0[1])
        const esc = (r0w && r0h) ? Math.min(dispoW / r0w, dispoH / r0h) : 1
        const aw = r0w * esc, ah = r0h * esc
        const dst = [card[0] + (cardW - aw) / 2, card[1] + (cardH - ah) / 2,
          card[0] + (cardW + aw) / 2, card[1] + (cardH + ah) / 2]
        // la pieza como IMAGEN a 300 dpi del tamaño impreso (ver `ficha_tecnica.py`): el mismo
        // dibujo que hace PyMuPDF (`dibujarMesa` = `get_pixmap`, contrato de la vista)
        const anchoPx = Math.max(1, Math.round((dst[2] - dst[0]) * 300.0 / 72.0))
        const dib = dibujarMesa(ctx.mupdf, src, 0, { ancho: anchoPx })
        insertarImagen(ctx, pg, dst, dib.png, true)
      } catch {
        // como el Python: si el PDF de la pieza no se puede leer, la tarjeta queda vacía
      } finally {
        if (src) { try { src.destroy() } catch { /* nada */ } }
      }
      // Rótulo: NOMBRE general de la pieza (sin número) + en qué TELA va. La medida no se muestra.
      const nom = generico(oVacio(pz.nombre) || '—')
      texto(ctx, pg, cx + gap + 2, filaY + hCard + 12, nom, 7.5, NEGRO, true, wCel - 2 * gap - 2)
      const tela = pyStrip(pyStr(oVacio(pz.tela)))
      if (tela) texto(ctx, pg, cx + gap + 2, filaY + hCard + 22, 'Tela: ' + tela, 6.5, ACENTO, true, wCel - 2 * gap - 2)
    }
    filaY += hCel
  }
  return [filaY, restantes]
}

// Los campos salen del nombre de la CAPA del archivo («numero», «numero 2»), que casi nunca trae
// acentos: la ficha los muestra bien escritos.
const LABEL_CAMPO = { nombre: 'Nombre', numero: 'Número', 'numero 2': 'Número 2',
  numero2: 'Número 2', palabra: 'Palabra', apellido: 'Apellido' }

/**
 * Arma el PDF de la ficha. Ver el encabezado del archivo por la forma de la entrada.
 * `moldesGuia` = uno por DISEÑO del pedido (y por variable dentro del diseño).
 */
export function generarFicha(mupdf, { titulo, subtitulo, planilla, moldesGuia }) {
  const ctx = crearCtx(mupdf)
  try {
    const columnas = (planilla || {}).columnas || []
    const filas = (planilla || {}).filas || []

    // 1) TABLA (arriba). Puede ocupar más de una página si hay muchas filas (la numeración sigue).
    let pg = nuevaPagina(ctx)
    let y = seccion(ctx, pg, 78, 'TABLA DE TALLES')
    y += 6
    let restan, f0
    ;[y, restan, f0] = dibujarTabla(ctx, pg, y, columnas, filas, A4_H - MARGEN)
    while (restan.length) {
      pg = nuevaPagina(ctx)
      y = seccion(ctx, pg, 78, 'TABLA DE TALLES (continuación)')
      y += 6
      ;[y, restan, f0] = dibujarTabla(ctx, pg, y, columnas, restan, A4_H - MARGEN, f0)
    }

    // 2) MOLDE GUÍA — UNO POR CADA DISEÑO del pedido. El encabezado dice el DISEÑO, NO el talle.
    let guias = [...(moldesGuia || [])]
    // NUNCA EL MISMO MOLDE DOS VECES: se descarta una guía sólo si es COPIA EXACTA de otra (mismo
    // molde, misma variable, mismas piezas y los mismos bytes de dibujo).
    const vistas = new Set(), unicas = []
    const enc = new TextEncoder()
    for (const mg of guias) {
      const partes = []
      for (const p of (mg.piezas || [])) { partes.push(enc.encode(pyStr(oVacio(p.nombre)))); partes.push(aBytes(p.pdf) || new Uint8Array(0)) }
      const todo = new Uint8Array(partes.reduce((a, x) => a + x.length, 0))
      let k = 0
      for (const x of partes) { todo.set(x, k); k += x.length }
      const clave = JSON.stringify([pyStr(oVacio(mg.nombre)), pyStr(oVacio(mg.variante)), pyStr(oVacio(mg.opciones)), sha1HexBytes(todo)])
      if (vistas.has(clave)) continue
      vistas.add(clave)
      unicas.push(mg)
    }
    guias = unicas
    // La VARIABLE sólo se nombra cuando el MISMO molde+diseño sale en más de una.
    const rep = new Map()
    const claveRep = (mg) => JSON.stringify([mg.nombre ?? null, mg.diseno ?? null])
    for (const mg of guias) rep.set(claveRep(mg), (rep.get(claveRep(mg)) || 0) + 1)
    guias.forEach((mg, iMg) => {
      const piezas = mg.piezas || []
      const tituloMg = `MOLDE GUÍA · ${'nombre' in mg ? fstr(mg.nombre) : ''}` + (verdad(mg.diseno) ? `  ·  ${fstr(mg.diseno)}` : '')
      // Línea gris de abajo: la variable (si distingue), QUÉ OPCIONES lleva y cuántas piezas son.
      const varn = pyStrip(pyStr(oVacio(mg.variante)))
      const detalle = []
      if (varn && (rep.get(claveRep(mg)) || 0) > 1) detalle.push('Variable: ' + varn)
      if (pyStrip(pyStr(oVacio(mg.opciones)))) detalle.push(pyStrip(String(mg.opciones)))
      detalle.push(`${piezas.length} pieza` + (piezas.length !== 1 ? 's' : ''))
      const detalleTxt = detalle.join('  ·  ')
      if (y + 210 > A4_H - MARGEN) {          // no entra ni el título + una fila → página nueva
        pg = nuevaPagina(ctx); y = 78
      } else {
        y += 24
        if (iMg) {                            // separador: dónde termina un diseño y empieza otro
          const pageY = y - 12
          dibujarLinea(ctx, pg, [MARGEN, pageY], [A4_W - MARGEN, pageY], LINEA, 0.6)
        }
      }
      y = seccion(ctx, pg, y, tituloMg)
      y += 11
      texto(ctx, pg, MARGEN, y, detalleTxt, 8, GRIS, false, A4_W - 2 * MARGEN)
      y += 9
      // CON QUÉ TIPOGRAFÍA SALE ESTAMPADO cada campo, en su propia línea, partida si no entra.
      const fts = mg.fuentes || []
      if (fts.length) {
        const partes = fts.map((f) => {
          const campo = pyStr(oVacio(f.campo))
          const label = LABEL_CAMPO[pyStrip(campo).toLowerCase()] ?? capitalize(campo)
          return label + ': ' + pyStr(oVacio(f.fuente)) + (verdad(f.sustituida) ? ` (falta «${fstr(f.pedida)}», se sustituyó)` : '')
        })
        const anchoT = A4_W - 2 * MARGEN
        let lin = 'Tipografía  ·  ', acum = []
        for (const pt of partes) {
          const intento = (pyStrip(lin) !== 'Tipografía  ·' && acum.length) ? (lin + '   ' + pt) : (lin + pt)
          if (largoTexto(ctx, intento, FONT, 8) > anchoT && acum.length) {
            texto(ctx, pg, MARGEN, y, lin, 8, GRIS, false, anchoT)
            y += 9
            lin = '        ' + pt; acum = [pt]
          } else {
            lin = intento; acum = [...acum, pt]
          }
        }
        texto(ctx, pg, MARGEN, y, lin, 8, GRIS, false, anchoT)
        y += 9
      }
      let rest
      ;[y, rest] = dibujarPiezas(ctx, pg, y, piezas, A4_H - MARGEN)
      while (rest.length) {
        pg = nuevaPagina(ctx); y = 78
        y = seccion(ctx, pg, y, tituloMg + ' (continuación)')
        y += 10
        ;[y, rest] = dibujarPiezas(ctx, pg, y, rest, A4_H - MARGEN)
      }

      // ── LO QUE NO SE SUBLIMA ────────────────────────────────────────────────────────────
      // Los objetos marcados como TPU / Bordado / DTF: en la tela sale sólo una cruz de 3 cm, así
      // que el taller necesita saber acá qué va en ese lugar y sobre qué pieza.
      const procesos = mg.procesos || []
      if (procesos.length) {
        const ALTO_PR = 58                    // alto MÍNIMO: el dibujo + los datos al lado
        if (y + 34 + ALTO_PR > A4_H - MARGEN) { pg = nuevaPagina(ctx); y = 78 } else y += 16
        y = seccion(ctx, pg, y, 'NO SE SUBLIMA · se aplica aparte')
        y += 10
        // El texto se adapta: decir «va una cruz» cuando el usuario la deshabilitó mandaría a buscar
        // en la tela una marca que no existe.
        const con = procesos.filter((p) => !verdad(p.sin_marca))
        const sin = procesos.filter((p) => verdad(p.sin_marca))
        let cab
        if (con.length && sin.length) {
          cab = 'En la tela va una cruz de 3 cm marcando el centro, salvo en los que dicen ' +
                'SIN MARCA: en ese lugar la tela sale limpia, sin marca ni diseño.'
        } else if (sin.length) {
          cab = 'En la tela NO queda nada en su lugar (ni marca ni diseño): se ubican con ' +
                'el molde guía de abajo.'
        } else {
          cab = 'En la tela, en el lugar de cada uno, va una cruz de 3 cm marcando el centro:'
        }
        texto(ctx, pg, MARGEN, y, cab, 8, GRIS, false, A4_W - 2 * MARGEN)
        y += 14
        for (const pr of procesos) {
          if (y + ALTO_PR > A4_H - MARGEN) { pg = nuevaPagina(ctx); y = 78 }
          const caja = [MARGEN, y, MARGEN + 54, y + 48]
          // FONDO GRIS MEDIO detrás del objeto: un TPU/bordado/DTF blanco sobre la hoja blanca no se
          // veía; en gris medio se ve tanto un objeto blanco como uno oscuro.
          dibujarRect(ctx, pg, caja, { color: LINEA, width: 0.6, fill: [0.58, 0.60, 0.63] })
          const cajaInt = [caja[0] + 3, caja[1] + 3, caja[2] - 3, caja[3] - 3]
          // EL OBJETO, DIBUJADO: primero el vector (el PDF del objeto; ver el encabezado por el SVG)
          // y, si no se puede, la miniatura PNG.
          let dib = false
          const pdfObj = aBytes(pr.pdf)
          if (pdfObj && pdfObj.length) {
            let sd = null
            try {
              sd = new ctx.mupdf.PDFDocument(pdfObj)
              mostrarPagina(ctx, pg, cajaInt, sd, 0)
              dib = true
            } catch { dib = false } finally { if (sd) { try { sd.destroy() } catch { /* nada */ } } }
          }
          if (!dib && verdad(pr.thumb)) {
            try { insertarImagen(ctx, pg, cajaInt, aBytes(pr.thumb), true); dib = true } catch { /* sin vista */ }
          }
          if (!dib) texto(ctx, pg, caja[0] + 8, caja[1] + 27, '(sin vista)', 7, GRIS)
          // …y al lado, QUÉ es y EN QUÉ MATERIAL se hace.
          const x = caja[2] + 12
          texto(ctx, pg, x, y + 13, pyStr(oVacio(pr.nombre)), 10, NEGRO, true, A4_W - MARGEN - x)
          // El MATERIAL. Si nadie lo eligió se dice así, sin inventarlo.
          const mat = pyStrip(pyStr(oVacio(pr.proceso)))
          let proc = mat ? ('Se hace en: ' + mat) : 'Falta indicar en qué material se hace'
          if (verdad(pr.sin_marca)) proc += '   ·   SIN MARCA en la tela'
          texto(ctx, pg, x, y + 27, proc, 9, mat ? NEGRO : ROJO, !mat, A4_W - MARGEN - x)
          // MEDIDAS: una línea por rango («XS a M → 8 × 8 cm»); las arma el servidor.
          let yy = y + 40
          for (const md of (pr.medidas || [])) {
            const t = [pyStr(oVacio(md.talles)), pyStr(oVacio(md.texto))].filter((s) => s).join('  ·  ')
            if (t) { texto(ctx, pg, x, yy, t, 8, GRIS, false, A4_W - MARGEN - x); yy += 11 }
          }
          if (verdad(pr.pieza)) { texto(ctx, pg, x, yy, 'va en ' + String(pr.pieza), 8, GRIS, false, A4_W - MARGEN - x); yy += 11 }
          if (verdad(pr.nota)) { texto(ctx, pg, x, yy, String(pr.nota), 7, GRIS, false, A4_W - MARGEN - x); yy += 10 }
          y += Math.max(ALTO_PR, (yy - y) + 10)   // el bloque crece si hay varios rangos
        }
      }
    })

    // El «Pág. x/y» recién se sabe al final: segunda pasada, como en Python (queda ARRIBA de todo).
    const total = ctx.paginas.length
    ctx.paginas.forEach((p, i) => encabezado(ctx, p, titulo, subtitulo, i + 1, total))

    // Materializar: una página A4 por cada una, con SUS recursos y su contenido (los trozos de
    // PyMuPDF, que son streams sueltos, van seguidos en uno: cada uno es un `q … Q` cerrado).
    const doc = ctx.doc
    for (const p of ctx.paginas) {
      const res = doc.newDictionary()
      if (p.fuentes.size) {
        const fd = doc.newDictionary()
        for (const fn of ['helv', 'hebo']) {
          if (!p.fuentes.has(fn)) continue
          const f = ctx.fuentes[fn]
          if (!f.obj) f.obj = doc.addSimpleFont(f.font, 'Latin')
          fd.put(fn, f.obj)
        }
        res.put('Font', fd)
      }
      if (p.xobjs.length) {
        const xd = doc.newDictionary()
        for (const [n, o] of p.xobjs) xd.put(n, o)
        res.put('XObject', xd)
      }
      const contenido = enc.encode(p.trozos.join(''))
      const page = doc.addPage([0, 0, A4_W, A4_H], 0, res, contenido)
      doc.insertPage(doc.countPages(), page)
    }
    // `doc.save(garbage=3, deflate=True)`
    return doc.saveToBuffer('garbage=3,compress').asUint8Array().slice()
  } finally {
    cerrarCtx(ctx)
  }
}
