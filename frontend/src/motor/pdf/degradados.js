// LOS DEGRADADOS, VECTORIALES TAMBIÉN EN PANTALLA — 2026-10-01 (MAPA 605).
//
// 🔴 POR QUÉ. El escritor SVG de MuPDF no sabe escribir un degradado: cada `sh` lo DIBUJA como una
// imagen PNG del tamaño de lo que recorta y la incrusta en el SVG. Con el arte «CAMISETA NEGRO 2»
// (11 degradados por mesa, recortados por piezas de 70 × 76 cm) dibujar UNA mesa para el visor
// tardaba 8,6 s y 11,9 s, y lo que se veía era un píxel — contra la LEY «siempre el vector».
//
// CÓMO. Antes de pasar la página por el escritor SVG, cada `sh` de un degradado lineal o radial se
// cambia por un RELLENO MARCADOR: un polígono que cubre lo que el degradado pinta, de un color
// reservado (`#5bc3NN`). MuPDF lo escribe como un `<path fill="#5bc3NN">` común (con su recorte,
// su transparencia y su lugar en el orden de dibujo), y después se cambia ese `fill` por
// `url(#…)` hacia un `linearGradient`/`radialGradient` propio. El marcador se pinta en el MISMO
// sistema de coordenadas del `sh`, así que el `<path>` queda en el espacio del degradado y sus
// `/Coords` se usan tal cual (`gradientUnits="userSpaceOnUse"`): no hay cuenta de matrices que
// pueda salir mal.
//
// LOS COLORES SON LOS DE MuPDF: el degradado se dibuja UNA vez en una tira angosta (con su espacio
// de color, su perfil ICC y su función) y de ahí salen las paradas, así que en pantalla se ve
// igual que cuando MuPDF pintaba la imagen (comparado contra el dibujo real de la mesa).
//
// LO QUE NO SE TOCA (queda como estaba, dibujado por MuPDF): mallas y degradados por función
// (tipos 1, 4-7), los que traen `/BBox`, los radiales raros (el círculo de arranque fuera del de
// llegada, o sin extender) y los patrones de degradado. Y si al final el SVG no trae los
// marcadores que se esperaban, se descarta todo y se dibuja por el camino viejo: nunca sale un
// dibujo equivocado, a lo sumo uno lento.
//
// El documento NO queda cambiado: cada contenido reemplazado se devuelve a su lugar (`deshacer`).
import { instrucciones, escribir } from './contenido.js'

// La tira de muestras: 1024 × 8. ⚠️ MEDIDO: con 1 píxel de alto MuPDF da los colores CORRIDOS
// (hasta 10 niveles contra el dibujo real de la mesa); con 8 de alto y leyendo la fila del medio
// coincide con el dibujo real a ±1 nivel. Y 256 muestras se quedaban cortas donde el color
// cambia rápido.
const MUESTRAS = 1024
const ALTO_TIRA = 8
const COLOR_BASE = 0x5bc300            // + el número del degradado (hasta 250 por dibujo)
const TOPE = 250
const PATH_BUILD = new Set(['m', 'l', 'c', 'v', 'y', 're', 'h'])
const TERMINADORES = new Set(['S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*', 'n'])
const SIN_COPIAR = new Set(['Length', 'Filter', 'DecodeParms'])

const nulo = (o) => !o || o.isNull()
const num = (v) => {
  if (v && typeof v === 'object' && (v.i !== undefined || v.r !== undefined)) return Number(v.i !== undefined ? v.i : v.r)
  throw new TypeError('no es un número')
}
const mmul = (a, b) => [a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3],
  a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
  a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5]]
const mpt = (m, x, y) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]]
function inversa(m) {
  const det = m[0] * m[3] - m[1] * m[2]
  if (!Number.isFinite(det) || Math.abs(det) < 1e-12) return null
  return [m[3] / det, -m[1] / det, -m[2] / det, m[0] / det,
    (m[2] * m[5] - m[3] * m[4]) / det, (m[1] * m[4] - m[0] * m[5]) / det]
}
/** Un número como real de PDF / atributo SVG: sin exponente y sin ceros de más. */
function texto(x) {
  if (!Number.isFinite(x)) throw new RangeError('número no finito')
  let s = x.toFixed(6)
  if (s.includes('.')) s = s.replace(/0+$/, '').replace(/\.$/, '')
  return s === '-0' ? '0' : s
}
const real = (x) => ({ r: texto(x) })
const hex = (n) => '#' + n.toString(16).padStart(6, '0')
const numeros = (arr, n) => {
  if (nulo(arr) || !arr.isArray() || arr.length < n) return null
  const out = []
  for (let i = 0; i < n; i++) { const v = arr.get(i).asNumber(); if (!Number.isFinite(v)) return null; out.push(v) }
  return out
}

/**
 * Las paradas del degradado, con los colores que pinta MuPDF: el mismo sombreado (copiado a un
 * documento de una página de 256 × 1) estirado a lo largo de la tira. [[offset, '#rrggbb'], …].
 */
function paradas(mupdf, sombreado) {
  const tmp = new mupdf.PDFDocument()
  let page = null, pix = null
  try {
    const sh = tmp.graftObject(sombreado)
    sh.put('ShadingType', 2)
    sh.put('Coords', [0, 0, 1, 0])
    sh.put('Extend', [true, true])
    const res = tmp.newDictionary(), shs = tmp.newDictionary()
    shs.put('S0', sh)
    res.put('Shading', shs)
    tmp.insertPage(-1, tmp.addPage([0, 0, MUESTRAS, ALTO_TIRA], 0, res, `${MUESTRAS} 0 0 ${ALTO_TIRA} 0 0 cm /S0 sh`))
    page = tmp.loadPage(0)
    pix = page.toPixmap(mupdf.Matrix.identity, mupdf.ColorSpace.DeviceRGB, false, false)
    const px = pix.getPixels()
    const n = pix.getNumberOfComponents()
    if (pix.getWidth() !== MUESTRAS || pix.getHeight() !== ALTO_TIRA || n < 3) return null
    const fila = (ALTO_TIRA >> 1) * MUESTRAS * n            // la fila del medio (lejos de los bordes)
    const col = []
    for (let i = 0; i < MUESTRAS; i++) col.push([px[fila + i * n], px[fila + i * n + 1], px[fila + i * n + 2]])
    // De las 1024 muestras quedan sólo las paradas que hacen falta: se saltea toda muestra que la
    // recta entre sus vecinas ya da (a menos de medio nivel de color). Un degradado de dos colores
    // queda en 2 paradas; uno con curvas, en unas decenas.
    const dentro = (a, b) => {
      for (let k = a + 1; k < b; k++) {
        const f = (k - a) / (b - a)
        for (let c = 0; c < 3; c++) if (Math.abs(col[a][c] + (col[b][c] - col[a][c]) * f - col[k][c]) > 0.5) return false
      }
      return true
    }
    const out = []
    const poner = (i) => out.push([(i + 0.5) / MUESTRAS, hex((col[i][0] << 16) | (col[i][1] << 8) | col[i][2])])
    let a = 0
    poner(0)
    while (a < MUESTRAS - 1) {
      let b = a + 1
      while (b + 1 < MUESTRAS && dentro(a, b + 1)) b++
      poner(b)
      a = b
    }
    return out
  } catch {
    return null
  } finally {
    if (pix) { try { pix.destroy() } catch { /* nada */ } }
    if (page) { try { page.destroy() } catch { /* nada */ } }
    try { tmp.destroy() } catch { /* nada */ }
  }
}

/** Lo que hace falta de un `/Shading` para escribirlo como gradiente SVG, o null si no se sabe. */
function leerDegradado(mupdf, sombreado) {
  const d = sombreado
  const tipoO = d.get('ShadingType')
  const tipo = nulo(tipoO) ? 0 : tipoO.asNumber()
  if (tipo !== 2 && tipo !== 3) return null
  if (!nulo(d.get('BBox')) || nulo(d.get('Function'))) return null
  const coords = numeros(d.get('Coords'), tipo === 2 ? 4 : 6)
  if (!coords) return null
  let ext = [false, false]
  const e = d.get('Extend')
  if (!nulo(e) && e.isArray() && e.length >= 2) ext = [!!e.get(0).asBoolean(), !!e.get(1).asBoolean()]
  if (tipo === 2) {
    const dx = coords[2] - coords[0], dy = coords[3] - coords[1]
    if (!(dx * dx + dy * dy > 0)) return null
  } else {
    // radial: sólo el caso que SVG dibuja igual — el círculo de arranque DENTRO del de llegada,
    // extendido hacia afuera (y hacia adentro, salvo que arranque en un punto)
    const [x0, y0, r0, x1, y1, r1] = coords
    if (!(r0 >= 0) || !(r1 > 0) || r0 >= r1) return null
    if (Math.hypot(x1 - x0, y1 - y0) + r0 > r1 * (1 + 1e-6)) return null
    if (!ext[1] || (!ext[0] && r0 > 0)) return null
  }
  const stops = paradas(mupdf, sombreado)
  if (!stops || stops.length < 1) return null
  return { tipo, coords, ext, stops, usos: 0 }
}

/** Las instrucciones del relleno marcador que reemplaza a un `sh`, [] si no pinta nada, null si no se puede. */
function marcador(g, ctm, region) {
  const im = inversa(ctm)
  if (!im || !region) return null
  const [x0, y0, x1, y1] = [region[0] - 1, region[1] - 1, region[2] + 1, region[3] + 1]
  const q = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]].map(([x, y]) => mpt(im, x, y))
  let poly = q
  if (g.tipo === 2) {
    // una banda a lo largo del eje: si el degradado NO se extiende de un lado, termina ahí
    const [ax, ay, bx, by] = g.coords
    const dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy
    const ts = q.map(([x, y]) => ((x - ax) * dx + (y - ay) * dy) / L2)
    const ss = q.map(([x, y]) => (-(x - ax) * dy + (y - ay) * dx) / L2)
    let t0 = Math.min(...ts), t1 = Math.max(...ts)
    const s0 = Math.min(...ss), s1 = Math.max(...ss)
    if (!g.ext[0]) t0 = Math.max(t0, 0)
    if (!g.ext[1]) t1 = Math.min(t1, 1)
    if (!(t0 < t1)) return []
    const P = (t, s) => [ax + t * dx - s * dy, ay + t * dy + s * dx]
    poly = [P(t0, s0), P(t1, s0), P(t1, s1), P(t0, s1)]
  }
  const c = g.color
  const out = [{ op: 'q', args: [] },
    { op: 'rg', args: [real(((c >> 16) & 255) / 255), real(((c >> 8) & 255) / 255), real((c & 255) / 255)] }]
  poly.forEach(([x, y], i) => out.push({ op: i ? 'l' : 'm', args: [real(x), real(y)] }))
  out.push({ op: 'h', args: [] }, { op: 'f', args: [] }, { op: 'Q', args: [] })
  return out
}

/**
 * Recorre un content-stream llevando la matriz y el recorte vigentes y cambia cada `sh` que se
 * sabe escribir por su marcador. → los bytes nuevos, o null si no cambió nada.
 * `region` = lo que se pinta cuando no hay ningún recorte abierto (la página o el `/BBox` del form).
 */
function marcarStream(bytes, res, region, ctx) {
  const shs = nulo(res) ? null : res.get('Shading')
  if (nulo(shs)) return null
  let ctm = [1, 0, 0, 1, 0, 0], recorte = null
  const pila = []
  let pts = [], clip = false
  const out = []
  let cambios = 0
  for (const ins of instrucciones(bytes)) {
    const op = ins.op
    if (op === 'q') pila.push([ctm, recorte])
    else if (op === 'Q') { if (pila.length) [ctm, recorte] = pila.pop() } else if (op === 'cm') {
      try { const v = ins.args.map(num); if (v.length >= 6) ctm = mmul(v, ctm) } catch { /* una matriz rara: queda la anterior */ }
    } else if (PATH_BUILD.has(op)) {
      let f
      try { f = ins.args.map(num) } catch { f = [] }
      if (op === 're' && f.length === 4) {
        const [x, y, w, h] = f
        for (const [px, py] of [[x, y], [x + w, y], [x, y + h], [x + w, y + h]]) pts.push(mpt(ctm, px, py))
      } else {
        for (let k = 0; k < f.length - 1; k += 2) pts.push(mpt(ctm, f[k], f[k + 1]))
      }
    } else if (op === 'W' || op === 'W*') clip = true
    else if (TERMINADORES.has(op)) {
      if (clip && pts.length) {
        const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1])
        const b = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]
        recorte = recorte === null ? b : [Math.max(recorte[0], b[0]), Math.max(recorte[1], b[1]),
          Math.min(recorte[2], b[2]), Math.min(recorte[3], b[3])]
      }
      pts = []; clip = false
    } else if (op === 'sh' && ins.args.length === 1 && ins.args[0] && ins.args[0].n !== undefined) {
      const zona = recorte === null ? region : recorte
      const g = (zona && zona[0] < zona[2] && zona[1] < zona[3]) ? ctx.degradado(shs, ins.args[0].n) : null
      let m = null
      if (g) { try { m = marcador(g, ctm, zona) } catch { m = null } }
      if (m) {
        if (m.length) g.usos += 1
        out.push(...m)
        cambios += 1
        continue
      }
    }
    out.push(ins)
  }
  return cambios ? escribir(out) : null
}

const caja = (o) => {
  const v = numeros(o, 4)
  return v ? [Math.min(v[0], v[2]), Math.min(v[1], v[3]), Math.max(v[0], v[2]), Math.max(v[1], v[3])] : null
}

/**
 * Deja la página `pagina` de `doc` lista para el escritor SVG (sus `sh` cambiados por marcadores,
 * también dentro de sus Form XObjects) → `{ aplicar(svg), deshacer() }`, o null si no tiene
 * degradados que se sepan escribir (no se tocó nada).
 *   · `deshacer()` devuelve el documento a como estaba: llamarlo SIEMPRE después de dibujar.
 *   · `aplicar(svg)` → el SVG con los gradientes, o null si hay que dibujar por el camino viejo.
 */
export function marcarDegradados(mupdf, doc, pagina) {
  const pdf = doc.asPDF ? doc.asPDF() : null
  if (!pdf) return null
  const pageObj = pdf.findPage(pagina)
  const lista = []                    // los degradados, por orden de aparición
  const porClave = new Map()
  const formas = new Map()            // nº de objeto del Form original → su copia marcada (o null)
  const deshacer = []
  const ctx = {
    degradado(shs, nombre) {
      const ref = shs.get(nombre)
      if (nulo(ref)) return null
      const clave = ref.isIndirect() ? `o${ref.asIndirect()}` : null
      if (clave !== null && porClave.has(clave)) return porClave.get(clave)
      let g = null
      if (lista.length < TOPE) {
        try { g = leerDegradado(mupdf, ref) } catch { g = null }
        if (g) { g.color = COLOR_BASE + lista.length; lista.push(g) }
      }
      if (clave !== null) porClave.set(clave, g)
      return g
    },
  }
  // los Form XObjects (el diseño de una pieza viaja adentro de uno), primero los de más adentro
  const recorrer = (res, prof) => {
    if (nulo(res) || prof > 8) return
    const xos = res.get('XObject')
    if (nulo(xos) || !xos.isDictionary()) return
    const entradas = []
    xos.forEach((v, k) => entradas.push([String(k), v]))
    for (const [nombre, ref] of entradas) {
      try {
        if (!ref.isIndirect() || !ref.isStream()) continue
        const st = ref.get('Subtype')
        if (nulo(st) || !st.isName() || st.asName() !== 'Form') continue
        const n = ref.asIndirect()
        if (!formas.has(n)) {
          formas.set(n, null)                                      // (corta los ciclos)
          const sub = nulo(ref.get('Resources')) ? res : ref.get('Resources')
          recorrer(sub, prof + 1)
          const nuevo = marcarStream(ref.readStream().asUint8Array().slice(), sub, caja(ref.get('BBox')), ctx)
          if (nuevo) {
            const d = pdf.newDictionary()
            ref.forEach((v, k) => { if (!SIN_COPIAR.has(String(k))) d.put(String(k), v) })
            formas.set(n, pdf.addStream(nuevo, d))
          }
        }
        const copia = formas.get(n)
        if (copia) {
          xos.put(nombre, copia)
          deshacer.push(() => xos.put(nombre, ref))
        }
      } catch { /* un XObject raro: queda como está (lo dibuja MuPDF) */ }
    }
  }
  const volver = () => { while (deshacer.length) { try { deshacer.pop()() } catch { /* nada */ } } }
  try {
    const res = pageObj.getInheritable ? pageObj.getInheritable('Resources') : pageObj.get('Resources')
    recorrer(res, 0)
    const cont = pageObj.get('Contents')
    if (!nulo(cont)) {
      let bytes
      if (cont.isArray()) {
        const partes = []
        for (let i = 0; i < cont.length; i++) partes.push(cont.get(i).readStream().asUint8Array().slice())
        bytes = new Uint8Array(partes.reduce((s, p) => s + p.length + 1, 0))
        let k = 0
        for (const p of partes) { bytes.set(p, k); k += p.length; bytes[k++] = 10 }
      } else bytes = cont.readStream().asUint8Array().slice()
      const mb = caja(pageObj.getInheritable ? pageObj.getInheritable('MediaBox') : pageObj.get('MediaBox'))
      const nuevo = marcarStream(bytes, res, mb, ctx)
      if (nuevo) {
        pageObj.put('Contents', pdf.addStream(nuevo, pdf.newDictionary()))
        deshacer.push(() => pageObj.put('Contents', cont))
      }
    }
  } catch {
    volver()
    return null
  }
  const usados = lista.filter((g) => g.usos > 0)
  if (!deshacer.length) return null
  return {
    deshacer: volver,
    aplicar(svg) {
      let defs = ''
      for (const g of lista) {
        const marca = `fill="${hex(g.color)}"`
        const hay = svg.split(marca).length - 1
        // más marcadores que `sh` reemplazados = el dibujo ya traía ese color: no se puede saber
        // cuál es cuál → camino viejo. (Menos está bien: MuPDF no escribe lo que no pinta.)
        if (hay > g.usos) return null
        if (!hay) continue
        const id = `tzdg_${g.color - COLOR_BASE}`
        const stops = g.stops.map(([o, c]) => `<stop offset="${texto(o)}" stop-color="${c}"/>`).join('')
        if (g.tipo === 2) {
          const [x1, y1, x2, y2] = g.coords.map(texto)
          defs += `<linearGradient id="${id}" gradientUnits="userSpaceOnUse" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}">${stops}</linearGradient>\n`
        } else {
          const [fx, fy, fr, cx, cy, r] = g.coords.map(texto)
          defs += `<radialGradient id="${id}" gradientUnits="userSpaceOnUse" cx="${cx}" cy="${cy}" r="${r}" fx="${fx}" fy="${fy}" fr="${fr}">${stops}</radialGradient>\n`
        }
        svg = svg.split(marca).join(`fill="url(#${id})"`)
      }
      if (!defs) return usados.length ? null : svg
      const i = svg.indexOf('<svg')
      const j = i < 0 ? -1 : svg.indexOf('>', i)
      if (j < 0) return null
      return svg.slice(0, j + 1) + '\n<defs>\n' + defs + '</defs>' + svg.slice(j + 1)
    },
  }
}
