// CONTENT-STREAMS: leer y escribir las instrucciones de dibujo de una página PDF.
//
// Es la traducción de lo que hoy hace pikepdf (`parse_content_stream` / `unparse_content_stream`)
// en el servidor. Todo el desplegado del camino B (quedarse con un talle, sacar NOMBRE/00, la
// etiqueta que trae el archivo) trabaja sobre esta lista de instrucciones, así que el navegador
// tiene que partir el stream EXACTAMENTE igual: mismos operadores, mismos operandos, mismos tipos
// (un `1` entero no es un `1.0` real: al volver a escribirlo cambia el byte). El contrato
// `verificar_navegador_contenido.py` lo compara contra pikepdf instrucción por instrucción.
//
// Instrucción: { op: 'cm', args: [ …operandos ] }, o para una imagen en línea
// { op: 'INLINE IMAGE', dict: {…}, datos: Uint8Array }.
// Operandos:
//   número entero → { i: '12' }     (el texto tal cual, para reescribirlo idéntico)
//   número real   → { r: '-2.5' }
//   nombre        → { n: 'MC0' }    (sin la barra, con los #xx ya decodificados, latin-1)
//   texto         → { s: Uint8Array }
//   arreglo       → [ … ]
//   diccionario   → { d: Map(nombre → valor) }
//   true/false/null → true / false / null

const ESPACIO = new Uint8Array(256)
for (const c of [0, 9, 10, 12, 13, 32]) ESPACIO[c] = 1
const DELIM = new Uint8Array(256)
for (const c of '()<>[]{}/%') DELIM[c.charCodeAt(0)] = 1

const esRegular = (c) => !ESPACIO[c] && !DELIM[c]
const HEX = (c) => (c >= 48 && c <= 57) ? c - 48 : (c >= 65 && c <= 70) ? c - 55 : (c >= 97 && c <= 102) ? c - 87 : -1
const latin1 = (b, i, j) => {
  let s = ''
  for (let k = i; k < j; k++) s += String.fromCharCode(b[k])
  return s
}
const RX_ENTERO = /^[+-]?\d+$/
const RX_REAL = /^[+-]?(\d+\.\d*|\.\d+|\d+)$/

/** Un lector de tokens sobre los bytes de un content-stream. */
function lector(b) {
  let p = 0
  const n = b.length

  function saltarEspacios() {
    while (p < n) {
      const c = b[p]
      if (ESPACIO[c]) { p++; continue }
      if (c === 37) {                                  // % comentario hasta fin de línea
        while (p < n && b[p] !== 10 && b[p] !== 13) p++
        continue
      }
      break
    }
  }

  function textoLiteral() {
    // p apunta después de '('
    const out = []
    let prof = 1
    while (p < n) {
      let c = b[p++]
      if (c === 92) {                                  // barra invertida
        if (p >= n) break
        c = b[p++]
        if (c === 110) out.push(10)
        else if (c === 114) out.push(13)
        else if (c === 116) out.push(9)
        else if (c === 98) out.push(8)
        else if (c === 102) out.push(12)
        else if (c === 13) { if (b[p] === 10) p++ }   // continuación de línea
        else if (c === 10) { /* continuación */ }
        else if (c >= 48 && c <= 55) {
          let v = c - 48
          for (let k = 0; k < 2 && p < n && b[p] >= 48 && b[p] <= 55; k++) v = v * 8 + (b[p++] - 48)
          out.push(v & 255)
        } else out.push(c)
        continue
      }
      if (c === 40) prof++
      else if (c === 41) { prof--; if (prof === 0) break }
      out.push(c)
    }
    return { s: Uint8Array.from(out) }
  }

  function textoHex() {
    // p apunta después de '<'
    const out = []
    let alto = -1
    while (p < n) {
      const c = b[p++]
      if (c === 62) break
      const h = HEX(c)
      if (h < 0) continue
      if (alto < 0) alto = h
      else { out.push(alto * 16 + h); alto = -1 }
    }
    if (alto >= 0) out.push(alto * 16)
    return { s: Uint8Array.from(out) }
  }

  function nombre() {
    // p apunta después de '/'
    let s = ''
    while (p < n && esRegular(b[p])) {
      const c = b[p]
      if (c === 35 && p + 2 < n + 0 && HEX(b[p + 1]) >= 0 && HEX(b[p + 2]) >= 0) {
        s += String.fromCharCode(HEX(b[p + 1]) * 16 + HEX(b[p + 2]))
        p += 3
        continue
      }
      s += String.fromCharCode(c)
      p++
    }
    return { n: s }
  }

  /** El próximo token: {t:'valor', v} | {t:'op', v:'cm'} | {t:'abre['} … | null al final. */
  function token() {
    saltarEspacios()
    if (p >= n) return null
    const c = b[p]
    if (c === 40) { p++; return { t: 'valor', v: textoLiteral() } }
    if (c === 60) {
      if (b[p + 1] === 60) { p += 2; return { t: '<<' } }
      p++
      return { t: 'valor', v: textoHex() }
    }
    if (c === 62 && b[p + 1] === 62) { p += 2; return { t: '>>' } }
    if (c === 91) { p++; return { t: '[' } }
    if (c === 93) { p++; return { t: ']' } }
    if (c === 47) { p++; return { t: 'valor', v: nombre() } }
    if (c === 123 || c === 125 || c === 41 || c === 62) { p++; return { t: 'raro', v: String.fromCharCode(c) } }
    const i = p
    while (p < n && esRegular(b[p])) p++
    const s = latin1(b, i, p)
    if (s === 'true') return { t: 'valor', v: true }
    if (s === 'false') return { t: 'valor', v: false }
    if (s === 'null') return { t: 'valor', v: null }
    if (RX_ENTERO.test(s)) return { t: 'valor', v: { i: s } }
    if (RX_REAL.test(s)) return { t: 'valor', v: { r: s } }
    return { t: 'op', v: s }
  }

  function valorCompuesto(tk) {
    if (tk.t === 'valor') return tk.v
    if (tk.t === '[') {
      const arr = []
      for (;;) {
        const x = token()
        if (x === null || x.t === ']') return arr
        if (x.t === 'op') { arr.push({ op_suelto: x.v }); continue }
        arr.push(valorCompuesto(x))
      }
    }
    if (tk.t === '<<') {
      const d = new Map()
      for (;;) {
        const k = token()
        if (k === null || k.t === '>>') return { d }
        const v = token()
        if (v === null || v.t === '>>') { if (k.t === 'valor' && k.v && k.v.n !== undefined) d.set(k.v.n, null); return { d } }
        if (k.t === 'valor' && k.v && k.v.n !== undefined) d.set(k.v.n, valorCompuesto(v))
      }
    }
    return undefined
  }

  function imagenEnLinea() {
    // después de BI: pares clave/valor hasta ID, un espacio, los datos hasta «EI» entre espacios
    const d = new Map()
    for (;;) {
      const k = token()
      if (k === null) return null
      if (k.t === 'op' && k.v === 'ID') break
      const v = token()
      if (k.t === 'valor' && k.v && k.v.n !== undefined) d.set(k.v.n, valorCompuesto(v))
    }
    if (ESPACIO[b[p]]) p++
    const ini = p
    while (p < n) {
      if (b[p] === 69 && b[p + 1] === 73 && ESPACIO[b[p - 1]] && (p + 2 >= n || ESPACIO[b[p + 2]] || DELIM[b[p + 2]])) break
      p++
    }
    let fin = p
    if (fin > ini && ESPACIO[b[fin - 1]]) fin--
    const datos = b.subarray(ini, fin)
    p += 2
    return { op: 'INLINE IMAGE', dict: d, datos }
  }

  return { token, valorCompuesto, imagenEnLinea, pos: () => p }
}

/** Las instrucciones de un content-stream (bytes ya descomprimidos). */
export function* instrucciones(bytes) {
  const L = lector(bytes)
  let args = []
  for (;;) {
    const tk = L.token()
    if (tk === null) return                              // operandos sin operador al final: se descartan (como pikepdf)
    if (tk.t === 'op') {
      if (tk.v === 'BI') {
        const im = L.imagenEnLinea()
        if (im) yield im
        args = []
        continue
      }
      yield { op: tk.v, args }
      args = []
      continue
    }
    if (tk.t === 'raro' || tk.t === ']' || tk.t === '>>') continue
    args.push(L.valorCompuesto(tk))
  }
}

/** Los bytes del contenido de una página de mupdf.js (varios streams se unen con '\n', como
 *  `cortar_capas.contenido_crudo`). */
export function contenidoCrudo(page) {
  const obj = page.getObject()
  const c = obj.get('Contents')
  if (!c || c.isNull()) return new Uint8Array(0)
  if (c.isArray()) {
    const partes = []
    for (let i = 0; i < c.length; i++) partes.push(c.get(i).readStream().asUint8Array())
    const total = partes.reduce((a, x) => a + x.length, 0) + Math.max(0, partes.length - 1)
    const out = new Uint8Array(total)
    let pos = 0
    partes.forEach((x, k) => { if (k) out[pos++] = 10; out.set(x, pos); pos += x.length })
    return out
  }
  return c.readStream().asUint8Array()
}
