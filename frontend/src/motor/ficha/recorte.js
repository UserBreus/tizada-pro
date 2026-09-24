// CADA PIEZA DE LA GUÍA LLEVA SÓLO SU PARTE DEL ARCHIVO — 2026-09-22.
//
// 🔴 POR QUÉ: la guía de la ficha pega el diseño ORIGINAL (vector, sin dibujar nada), pero cada pieza
// nombraba la mesa ENTERA del talle recortada a su contorno. Armar la ficha era instantáneo, pero
// quien la MIRA (la vista de la ficha, Acrobat, Chrome) tiene que leer la mesa completa por cada
// tarjeta: las hojas del molde guía no terminaban de aparecer (captura del usuario, «Hoja 2» y
// «Hoja 3» en blanco). Acá, para cada pieza, se arma una copia del XObject con SÓLO las
// instrucciones que caen dentro de lo que la pieza muestra: el mismo vector, en el mismo orden, sin
// lo que el recorte iba a tapar igual.
//
// QUÉ SE PUEDE SACAR SIN CAMBIAR NADA DE LO QUE SE VE:
//   · un bloque `q … Q` entero que no pinta nada dentro del rectángulo: todo su estado (color,
//     grosor, recortes, texto) vuelve atrás en el `Q`, así que lo que sigue no se entera;
//   · un trazado pintado (`m/l/c/re … f|S|B…`) que cae entero fuera del rectángulo.
// QUÉ SE DEJA SIEMPRE (por las dudas, aunque pese):
//   · los operadores de estado sueltos (cm, colores, gs, marcas de contenido…);
//   · los recortes (`W n`): cambian lo que se ve después;
//   · el texto vivo (`BT … ET`), los sombreados (`sh`) y lo que no se sabe medir;
//   · un bloque con marcas de contenido desparejas (`BDC` sin su `EMC` adentro).
// El rectángulo de cada pieza sale de la PROPIA página de la pieza (su recorte `W n` antes del
// `Do`), llevado al espacio del XObject con la inversa de `Matrix × CTM`. Nada se inventa.
import { instrucciones, escribir } from '../pdf/contenido.js'

const INF = [-Infinity, -Infinity, Infinity, Infinity]
const num = (v) => (v && v.i !== undefined ? Number(v.i) : v && v.r !== undefined ? Number(v.r) : NaN)
// a y después b (como `pdf-op-run.c`): `cm` hace CTM = M × CTM
const mul = (a, b) => [a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3], a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
  a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5]]
function invertir(m) {
  const det = m[0] * m[3] - m[1] * m[2]
  if (!det) return null
  const a = m[3] / det, b = -m[1] / det, c = -m[2] / det, d = m[0] / det
  return [a, b, c, d, -(m[4] * a + m[5] * c), -(m[4] * b + m[5] * d)]
}
function cajaPor(r, m) {
  if (!r) return null
  if (r[0] === -Infinity) return INF
  const xs = [], ys = []
  for (const [x, y] of [[r[0], r[1]], [r[2], r[1]], [r[2], r[3]], [r[0], r[3]]]) { xs.push(m[0] * x + m[2] * y + m[4]); ys.push(m[1] * x + m[3] * y + m[5]) }
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]
}
const unir = (a, b) => (!a ? b : !b ? a : [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[2], b[2]), Math.max(a[3], b[3])])
const cortar = (a, b) => (!a ? b : !b ? a : [Math.max(a[0], b[0]), Math.max(a[1], b[1]), Math.min(a[2], b[2]), Math.min(a[3], b[3])])
const toca = (a, r) => !!a && a[0] <= r[2] && a[2] >= r[0] && a[1] <= r[3] && a[3] >= r[1]

const PATH = new Set(['m', 'l', 'c', 'v', 'y', 're', 'h'])
const PINTA = new Set(['f', 'F', 'f*', 'S', 's', 'B', 'B*', 'b', 'b*', 'n'])

function leerArreglo(o) {
  if (!o || o.isNull() || !o.isArray()) return null
  const v = []
  for (let i = 0; i < o.length; i++) v.push(Number(o.get(i).asNumber()))
  return v
}

/** La caja (en su propio espacio × su Matrix) de cada XObject que nombra un contenido. */
function cajasXObjects(recursos) {
  const cache = new Map()
  return (nombre) => {
    if (cache.has(nombre)) return cache.get(nombre)
    let r = INF
    try {
      const xd = recursos && !recursos.isNull() ? recursos.get('XObject') : null
      const x = xd && !xd.isNull() ? xd.get(nombre) : null
      if (x && !x.isNull()) {
        const st = x.get('Subtype')
        const sub = st && !st.isNull() ? st.asName() : ''
        if (sub === 'Image') r = [0, 0, 1, 1]
        else if (sub === 'Form') {
          const bb = leerArreglo(x.get('BBox'))
          const mt = leerArreglo(x.get('Matrix'))
          if (bb && bb.length === 4) r = cajaPor([Math.min(bb[0], bb[2]), Math.min(bb[1], bb[3]), Math.max(bb[0], bb[2]), Math.max(bb[1], bb[3])], mt && mt.length === 6 ? mt : [1, 0, 0, 1, 0, 0])
        }
      }
    } catch { r = INF }
    cache.set(nombre, r)
    return r
  }
}

/**
 * El contenido de un XObject como ÁRBOL de bloques con la caja de lo que pinta cada cosa (en el
 * espacio del contenido). Se arma UNA vez por XObject y sirve para todas las piezas que lo nombran.
 */
export function arbolDeContenido(bytes, recursos) {
  const inst = [...instrucciones(bytes)]
  const cajaXO = cajasXObjects(recursos)
  let i = 0
  // un bloque: `items` = {ins} (estado, va siempre) | {ins[], caja, clip} (trazado) | {bloque}
  // el bloque hijo arranca con el estado del padre (CTM, grosor, pico) y lo suelta en su `Q`
  function bloque(ctm0, abre, lw0 = 1, miter0 = 10) {
    const b = { abre, items: [], cierra: null, caja: null, mc: 0 }
    let ctm = ctm0, lw = lw0, miter = miter0
    let path = [], pb = null, clip = false
    const pt = (x, y) => { const X = ctm[0] * x + ctm[2] * y + ctm[4], Y = ctm[1] * x + ctm[3] * y + ctm[5]; pb = unir(pb, [X, Y, X, Y]) }
    const pinta = (caja) => { b.caja = unir(b.caja, caja) }
    while (i < inst.length) {
      const ins = inst[i++]
      const op = ins.op
      if (op === 'q') {
        const h = bloque(ctm, ins, lw, miter)
        b.items.push({ bloque: h })
        if (h.caja) pinta(h.caja)
        continue
      }
      if (op === 'Q') {
        if (abre) { b.cierra = ins; break }
        b.items.push({ ins })                          // un `Q` de más en la raíz: se deja tal cual
        continue
      }
      if (PATH.has(op)) {
        path.push(ins)
        const a = ins.args
        if (op === 're') { const [x, y, w, h] = a.map(num); pt(x, y); pt(x + w, y + h); pt(x + w, y); pt(x, y + h) }
        else if (op === 'm' || op === 'l') pt(num(a[0]), num(a[1]))
        else if (op === 'c') { pt(num(a[0]), num(a[1])); pt(num(a[2]), num(a[3])); pt(num(a[4]), num(a[5])) }
        else if (op === 'v' || op === 'y') { pt(num(a[0]), num(a[1])); pt(num(a[2]), num(a[3])) }
        continue
      }
      if (op === 'W' || op === 'W*') { path.push(ins); clip = true; continue }
      if (PINTA.has(op)) {
        path.push(ins)
        let caja = null
        if (op !== 'n') {
          // el grosor del trazo (con el pico de las esquinas) agranda la caja; de más, nunca de menos
          const esc = Math.max(Math.hypot(ctm[0], ctm[1]), Math.hypot(ctm[2], ctm[3]))
          const g = /^(S|s|B|B\*|b|b\*)$/.test(op) ? lw * esc * Math.max(1, miter) : 0
          caja = pb ? [pb[0] - g, pb[1] - g, pb[2] + g, pb[3] + g] : INF
          if (caja.some((v) => Number.isNaN(v))) caja = INF
          pinta(caja)
        }
        b.items.push({ ins: path, caja, clip })
        path = []; pb = null; clip = false
        continue
      }
      if (path.length) { b.items.push({ ins: path, caja: null, clip: true }); path = []; pb = null; clip = false }   // trazado sin pintar: se deja
      if (op === 'cm') { ctm = mul(ins.args.map(num), ctm); b.items.push({ ins }); continue }
      if (op === 'w') { lw = num(ins.args[0]) || 0; b.items.push({ ins }); continue }
      if (op === 'M') { miter = num(ins.args[0]) || 10; b.items.push({ ins }); continue }
      if (op === 'BDC' || op === 'BMC') { b.mc++; b.items.push({ ins }); continue }
      if (op === 'EMC') { b.mc--; b.items.push({ ins }); continue }
      if (op === 'BT') {
        // texto vivo: se deja entero (el texto no se sabe medir sin la fuente)
        const t = [ins]
        while (i < inst.length) { const x = inst[i++]; t.push(x); if (x.op === 'ET') break }
        b.items.push({ ins: t, caja: INF, clip: false })
        pinta(INF)
        continue
      }
      if (op === 'Do') {
        const nom = ins.args[0] && ins.args[0].n
        const caja = cajaPor(nom ? cajaXO(nom) : INF, ctm) || INF
        b.items.push({ ins: [ins], caja, clip: false })
        pinta(caja)
        continue
      }
      if (op === 'INLINE IMAGE') {
        const caja = cajaPor([0, 0, 1, 1], ctm)
        b.items.push({ ins: [ins], caja, clip: false })
        pinta(caja)
        continue
      }
      if (op === 'sh') { b.items.push({ ins: [ins], caja: INF, clip: false }); pinta(INF); continue }
      b.items.push({ ins })                              // estado: colores, gs, d, j, J, ri, i…
    }
    if (path.length) b.items.push({ ins: path, caja: null, clip: true })
    // marcas de contenido desparejas adentro: sacarlo rompería el par → va siempre
    if (b.mc !== 0) b.caja = INF
    return b
  }
  return bloque([1, 0, 0, 1, 0, 0], null)
}

/** Las instrucciones del árbol que pintan dentro de `rect` (espacio del contenido), en su orden. */
export function recortarArbol(raiz, rect) {
  const out = []
  const emitir = (b) => {
    for (const it of b.items) {
      if (it.bloque) {
        if (toca(it.bloque.caja, rect)) { out.push(it.bloque.abre); emitir(it.bloque); if (it.bloque.cierra) out.push(it.bloque.cierra) }
        continue
      }
      if (!Array.isArray(it.ins)) { out.push(it.ins); continue }
      // trazado: el recorte va siempre; lo pintado, sólo si toca (si además recorta, va igual)
      if (it.clip || !it.caja || toca(it.caja, rect)) { for (const x of it.ins) out.push(x) }
    }
  }
  emitir(raiz)
  return escribir(out)
}

/**
 * Para cada XObject que nombra la página de una pieza (`contenido`, sus bytes), el rectángulo que
 * esa página MUESTRA de él, en el espacio de su contenido: el recorte vigente en el `Do` llevado
 * atrás por `Matrix × CTM`. `matrizDe(nombre)` = la /Matrix del XObject. Sin recorte → null (todo).
 */
export function rectsPorXObject(contenido, matrizDe, pagina) {
  const res = new Map()
  let gs = { ctm: [1, 0, 0, 1, 0, 0], clip: pagina ? pagina.slice() : null }
  const pila = []
  let pb = null, clipP = false
  const pt = (x, y) => { const m = gs.ctm; const X = m[0] * x + m[2] * y + m[4], Y = m[1] * x + m[3] * y + m[5]; pb = unir(pb, [X, Y, X, Y]) }
  for (const ins of instrucciones(contenido)) {
    const op = ins.op, a = ins.args
    if (op === 'q') { pila.push(gs); gs = { ...gs, clip: gs.clip ? gs.clip.slice() : null }; continue }
    if (op === 'Q') { gs = pila.pop() || gs; continue }
    if (op === 'cm') { gs.ctm = mul(a.map(num), gs.ctm); continue }
    if (op === 're') { const [x, y, w, h] = a.map(num); pt(x, y); pt(x + w, y + h); continue }
    if (op === 'm' || op === 'l') { pt(num(a[0]), num(a[1])); continue }
    if (op === 'c') { pt(num(a[0]), num(a[1])); pt(num(a[2]), num(a[3])); pt(num(a[4]), num(a[5])); continue }
    if (op === 'v' || op === 'y') { pt(num(a[0]), num(a[1])); pt(num(a[2]), num(a[3])); continue }
    if (op === 'W' || op === 'W*') { clipP = true; continue }
    if (PINTA.has(op)) { if (clipP && pb) gs.clip = cortar(gs.clip, pb); clipP = false; pb = null; continue }
    if (op === 'Do') {
      const nom = a[0] && a[0].n
      if (!nom) continue
      const total = mul(matrizDe(nom) || [1, 0, 0, 1, 0, 0], gs.ctm)
      const inv = invertir(total)
      const r = (gs.clip && inv) ? cajaPor(gs.clip, inv) : INF
      res.set(nom, unir(res.get(nom) || null, r))
    }
  }
  return res
}

/**
 * La página de UNA pieza con sus XObjects reducidos: para cada `[nombre, xo]` de `xs`, un XObject
 * nuevo con los mismos BBox / Matrix / Resources / Group y SÓLO el contenido que la pieza muestra.
 * `arboles` (Map xo → árbol) se comparte entre las piezas: el archivo se lee una vez.
 */
export function xobjectsDePieza(out, contenido, xs, caja, arboles) {
  const porNombre = new Map(xs)
  const matrizDe = (n) => { const x = porNombre.get(n); return x ? leerArreglo(x.get('Matrix')) : null }
  const rects = rectsPorXObject(contenido, matrizDe, caja)
  return xs.map(([nom, xo]) => {
    const r = rects.get(nom)
    if (!r || r[0] === -Infinity) return [nom, xo]         // no se sabe qué muestra: va entero
    let arbol = arboles.get(xo)
    if (!arbol) { arbol = arbolDeContenido(xo.readStream().asUint8Array(), xo.get('Resources')); arboles.set(xo, arbol) }
    // un pelo de margen (0,5 % del lado) para que lo que roza el borde no quede afuera por redondeo
    const mx = (r[2] - r[0]) * 0.005 + 0.5, my = (r[3] - r[1]) * 0.005 + 0.5
    const bytes = recortarArbol(arbol, [r[0] - mx, r[1] - my, r[2] + mx, r[3] + my])
    const d = out.newDictionary()
    d.put('Type', out.newName('XObject'))
    d.put('Subtype', out.newName('Form'))
    for (const k of ['BBox', 'Matrix', 'Resources', 'Group']) { const v = xo.get(k); if (v && !v.isNull()) d.put(k, v) }
    return [nom, out.addStream(bytes, d)]
  })
}
