// NESTING POR CONTORNO EN EL NAVEGADOR — PLAN_NAVEGADOR.md, etapa 4, punto 1.
//
// Traducción de `nesting_contorno.py` (`poligonos_contorno`, `_mascara_contorno`, `_angulos`,
// `_rotar`, `_elegir_posicion`, `_preparar`, `anidar_contorno`, `_anidar_estrategia`). La salida
// tiene que ser IDÉNTICA a la del servidor: mismas colocaciones (x, y, ángulo, orden de hojas y
// dentro de cada hoja), mismos empates. El contrato es `verificar_navegador_nesting.py`.
//
// 🔴 SIEMPRE LA MÁSCARA DEL CONTORNO. Python tiene dos caminos para la silueta: rasterizar el
// documento de la pieza (`_mascara(doc)`, el legado: `TIZADA_MASCARA_LEGACY=1` o piezas sin
// `base.cont`) y pintar el polígono del contorno (`_mascara_contorno`, lo que usa el camino B y el
// sello desde 2026-09-04). Acá existe SOLO el del contorno: en el navegador no se rasteriza nada
// (regla «siempre el vector original») y toda pieza llega con su `base` (`pieza/base.js`).
//
// QUÉ HACE DISTINTO PYTHON Y CÓMO SE COPIÓ (lo no obvio):
//   · La silueta la pinta Pillow 12.2 (`ImageDraw.polygon(fill=1, outline=1)` en modo "1"): con
//     `outline == fill` NO se traza el contorno, sólo el relleno (`ImageDraw.polygon`). El relleno
//     es `ImagingDrawPolygon` + `polygon_generic` (libImaging/Draw.c): vértices truncados a int
//     (`(int)xy`), aristas con pendiente en FLOAT de 32 bits, cruces por fila en float, corrección
//     de esquinas, `ROUND_UP`/`ROUND_DOWN` con `+ 0.5F`. Está portado línea por línea con
//     `Math.fround` donde C opera en `float`.
//   · `ndimage.binary_dilation(m, disco)`: OR del vecindario (disco simétrico, borde = 0).
//   · `ndimage.rotate(m, ang, reshape=True, order=0)` (sólo rotación «libre»): cos/sin en GRADOS
//     (cephes `cosdg`/`sindg`, portados: `Math.cos(rad)` difiere en el último bit para 19 de 360
//     grados enteros), forma de salida `int(ptp + 0.5)`, vecino más cercano con `floor(cc + 0.5)`
//     y borde constante (fuera de [0, len-1] → 0), en el mismo orden de suma que el C de scipy.
//   · `fftconvolve(...) < 0.5` es «ninguna celda se pisa»: acá se cuenta EXACTO con bits (una
//     palabra de 32 celdas por vez). Es la misma pregunta sin el error de la FFT. Y como
//     `_elegir_posicion` se queda con la PRIMERA posición válida en el orden (y+hh, x) (bl) o
//     ((y+hh)//25, x, y) (bandas), se recorre en ese orden y se corta al encontrarla.
//   · `sorted(..., reverse=True)` es estable: los empates conservan el orden de entrada. El
//     `sort` de JS también, con un comparador descendente.
//   · `int(...)` trunca hacia cero (`Math.trunc`); `//` con enteros no negativos = `Math.floor`.
//   · `math.cos/sin(math.radians(ang))` para el bbox (`bw`, `bh`): en múltiplos de 90° la UCRT
//     de Windows y V8 coinciden bit a bit; en otros ángulos pueden diferir en 1 ulp (medido:
//     19 de 360). Por eso el contrato compara `bw`/`bh` con tolerancia y todo lo demás exacto.
import { compararTuplas } from '../py.js'

export const CM = 28.3465
const SOBRE = 4              // submuestras por celda (`sobre=4` de `_mascara_contorno`)

/** Contadores para medir (bloques vs búsqueda completa), como `_DEBUG` en Python. */
export const DEBUG = {}

// ─────────────────────────────────────────────────────────────────────────────────────────────
// Máscaras: `{h, w, d: Uint8Array(h*w)}` (0/1), fila mayor, como un ndarray bool de numpy.
// ─────────────────────────────────────────────────────────────────────────────────────────────

function mascara(h, w) {
  return { h, w, d: new Uint8Array(h * w) }
}

function contar(m) {
  let n = 0
  const d = m.d
  for (let i = 0; i < d.length; i++) n += d[i]
  return n
}

/** `_disco(r)`: la bola de radio r en la grilla, `(x² + y²) <= r²`; null si r <= 0. */
export function disco(r) {
  if (r <= 0) return null
  const n = 2 * r + 1
  const m = mascara(n, n)
  for (let y = -r; y <= r; y++) for (let x = -r; x <= r; x++) if (x * x + y * y <= r * r) m.d[(y + r) * n + (x + r)] = 1
  return m
}

/** `ndimage.binary_dilation(m, estructura)`: una celda se prende si alguna del vecindario lo está. */
export function dilatar(m, est) {
  const out = mascara(m.h, m.w)
  const r = (est.h - 1) >> 1
  // los desplazamientos del disco, una vez (es simétrico: da igual el sentido)
  const offs = []
  for (let y = 0; y < est.h; y++) for (let x = 0; x < est.w; x++) if (est.d[y * est.w + x]) offs.push([y - r, x - r])
  for (let y = 0; y < m.h; y++) {
    for (let x = 0; x < m.w; x++) {
      if (!m.d[y * m.w + x]) continue
      for (const [dy, dx] of offs) {
        const yy = y + dy, xx = x + dx
        if (yy >= 0 && yy < m.h && xx >= 0 && xx < m.w) out.d[yy * m.w + xx] = 1
      }
    }
  }
  return out
}

/** `np.pad(m, pad)`: ceros alrededor. */
function rellenar(m, pad) {
  const out = mascara(m.h + 2 * pad, m.w + 2 * pad)
  for (let y = 0; y < m.h; y++) out.d.set(m.d.subarray(y * m.w, (y + 1) * m.w), (y + pad) * out.w + pad)
  return out
}

/** `np.rot90(m, k)` (k = 1, 2, 3): en sentido antihorario, como numpy. */
function rot90(m, k) {
  const { h, w } = m
  if (k === 2) {
    const out = mascara(h, w)
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) out.d[y * w + x] = m.d[(h - 1 - y) * w + (w - 1 - x)]
    return out
  }
  const out = mascara(w, h)
  if (k === 1) {
    for (let i = 0; i < w; i++) for (let j = 0; j < h; j++) out.d[i * h + j] = m.d[j * w + (w - 1 - i)]
  } else {
    for (let i = 0; i < w; i++) for (let j = 0; j < h; j++) out.d[i * h + j] = m.d[(h - 1 - j) * w + i]
  }
  return out
}

// ── cephes `sindg`/`cosdg` (lo que usa `ndimage.rotate`: seno y coseno en GRADOS) ──────────────
const SINCOF = [1.58962301572218447952e-10, -2.50507477628503540135e-8, 2.75573136213856773549e-6,
  -1.98412698295895384658e-4, 8.33333333332211858862e-3, -1.66666666666666307295e-1]
const COSCOF = [1.13678171382044275096e-11, -2.08758833757683644217e-9, 2.75573155429816611547e-7,
  -2.48015872936186303776e-5, 1.38888888888806666760e-3, -4.16666666666666348141e-2, 4.99999999999999999978e-1]
const PI180 = 1.74532925199432957692e-2

function polevl(x, coef) {
  let ans = coef[0]
  for (let i = 1; i < coef.length; i++) ans = ans * x + coef[i]
  return ans
}

function _octante(x) {
  let y = Math.floor(x / 45.0)
  let z = Math.floor(y / 16)           // ldexp(y, -4), floor
  z = y - z * 16                        // y - 16 * floor(y/16)
  let j = z | 0
  if (j & 1) { j += 1; y += 1.0 }
  j = j & 7
  return [y, j]
}

export function sindg(x) {
  let sign = 1
  if (x < 0) { x = -x; sign = -1 }
  let [y, j] = _octante(x)
  if (j > 3) { sign = -sign; j -= 4 }
  let z = x - y * 45.0
  z *= PI180
  const zz = z * z
  let r
  if (j === 1 || j === 2) r = 1.0 - zz * polevl(zz, COSCOF)
  else r = z + z * (zz * polevl(zz, SINCOF))
  return sign < 0 ? -r : r
}

export function cosdg(x) {
  let sign = 1
  if (x < 0) x = -x
  let [y, j] = _octante(x)
  if (j > 3) { j -= 4; sign = -sign }
  if (j > 1) sign = -sign
  let z = x - y * 45.0
  z *= PI180
  const zz = z * z
  let r
  if (j === 1 || j === 2) r = z + z * (zz * polevl(zz, SINCOF))
  else r = 1.0 - zz * polevl(zz, COSCOF)
  return sign < 0 ? -r : r
}

// ── `x * y + z` con UN solo redondeo (el FMA de la CPU), exacto con BigInt ─────────────────────
// numpy hace el `@` de `ndimage.rotate` con OpenBLAS, y sus kernels usan FMA: `rot @ vector`
// (gemv) da `fma(m00, v0, fl(m01·v1))` y `rot @ matriz` (gemm) acumula al revés,
// `fma(m01, b1, fl(m00·b0))`. Medido 2026-09-17 sobre 2492 giros: cada fórmula acierta bit a
// bit el 100 %, y la suma en doble a secas sólo la mitad. Sin esto, en 2 de 116 máscaras de
// prueba una celda del borde de la pieza girada quedaba distinta (el `offset` caía a un ulp de
// un .5). Corre 4 veces por giro: no cuesta nada.
function _descomponer(x) {
  const dv = new DataView(new ArrayBuffer(8))
  dv.setFloat64(0, x)
  const hi = dv.getUint32(0), lo = dv.getUint32(4)
  const neg = hi >>> 31, expo = (hi >>> 20) & 0x7ff
  let mant = (BigInt(hi & 0xfffff) << 32n) | BigInt(lo)
  let e = -1074
  if (expo !== 0) { mant |= 1n << 52n; e = expo - 1075 }
  return [neg ? -mant : mant, e]
}

function _aDouble(m, e) {
  if (m === 0n) return 0
  const neg = m < 0n
  if (neg) m = -m
  const bits = m.toString(2).length
  if (bits > 53) {                                   // al par más cercano, como la CPU
    const sh = BigInt(bits - 53)
    const q = m >> sh, r = m & ((1n << sh) - 1n), mitad = 1n << (sh - 1n)
    m = (r > mitad || (r === mitad && (q & 1n))) ? q + 1n : q
    e += bits - 53
  }
  const v = Number(m) * Math.pow(2, Math.max(e, -1000)) * Math.pow(2, e - Math.max(e, -1000))
  return neg ? -v : v
}

export function fma(x, y, z) {
  if (x === 0 || y === 0) return z
  if (z === 0) return x * y
  const [mx, ex] = _descomponer(x), [my, ey] = _descomponer(y), [mz, ez] = _descomponer(z)
  const ep = ex + ey, emin = Math.min(ep, ez)
  return _aDouble(((mx * my) << BigInt(ep - emin)) + (mz << BigInt(ez - emin)), emin)
}

/** `ndimage.rotate(m, ang, reshape=True, order=0)` para un ángulo que no es múltiplo de 90. */
function rotarLibre(m, ang) {
  const c = cosdg(ang), s = sindg(ang)
  const iy = m.h, ix = m.w
  // out_bounds = [[c, s], [-s, c]] @ [[0, 0, iy, iy], [0, ix, 0, ix]] (gemm); forma = int(ptp + 0.5)
  const b0 = [0, 0, iy, iy], b1 = [0, ix, 0, ix]
  const f0 = b0.map((v, j) => fma(s, b1[j], c * v))
  const f1 = b0.map((v, j) => fma(c, b1[j], -s * v))
  const oh = Math.trunc(Math.max(...f0) - Math.min(...f0) + 0.5)
  const ow = Math.trunc(Math.max(...f1) - Math.min(...f1) + 0.5)
  // out_center = rot @ ((forma - 1) / 2) (gemv); offset = in_center - out_center
  const a = (oh - 1) / 2, b = (ow - 1) / 2
  const off0 = (iy - 1) / 2 - fma(c, a, s * b)
  const off1 = (ix - 1) / 2 - fma(-s, a, c * b)
  const out = mascara(oh, ow)
  for (let oy = 0; oy < oh; oy++) {
    for (let ox = 0; ox < ow; ox++) {
      // el mismo orden de suma que NI_GeometricTransform: shift, + coord0*m0, + coord1*m1
      let cy = off0; cy += oy * c; cy += ox * s
      let cx = off1; cx += oy * -s; cx += ox * c
      // modo 'constant': fuera de [0, len-1] vale 0; adentro, el vecino más cercano
      if (cy < 0 || cy > iy - 1 || cx < 0 || cx > ix - 1) continue
      const ry = Math.floor(cy + 0.5), rx = Math.floor(cx + 0.5)
      out.d[oy * ow + ox] = m.d[ry * ix + rx]
    }
  }
  return out
}

/** `_rotar(mask, ang)`: en el MISMO sentido que `page.show_pdf_page(rotate=ang)`. */
export function rotar(m, ang) {
  ang = ((ang % 360) + 360) % 360
  if (ang === 0) return m
  if (ang % 90 === 0) return rot90(m, ang / 90)
  return rotarLibre(m, ang)
}

/** `_angulos(modo, paso_libre)`. */
export function angulos(modo, pasoLibre) {
  if (modo === 'ninguna' || modo === '0' || modo == null) return [0]
  if (modo === '90') return [0, 90, 180, 270]
  if (modo === '180') return [0, 180]
  if (modo === 'libre') {
    const paso = Math.max(1, Math.trunc(pasoLibre))
    const out = []
    for (let a = 0; a < 360; a += paso) out.push(a)
    return out
  }
  throw new Error(`Modo de rotación desconocido: ${JSON.stringify(modo)}`)
}

// ─────────────────────────────────────────────────────────────────────────────────────────────
// El contorno como polígonos y su máscara (`poligonos_contorno`, `_mascara_contorno`)
// ─────────────────────────────────────────────────────────────────────────────────────────────

/**
 * `poligonos_contorno(cont, S, x0, y0, B)`: polilíneas en coordenadas de PÁGINA (pt, y hacia
 * arriba), con la misma transformación que el clip y el borde: (vx·S + B − x0·S, vy·S + B − y0·S).
 * Las curvas se aplanan en 8 tramos.
 */
export function poligonosContorno(cont, S, x0, y0, B) {
  const P = (vx, vy) => [vx * S + B - x0 * S, vy * S + B - y0 * S]
  const polis = []
  let pts = [], cur = null
  for (const sg of cont.segmentos || []) {
    const op = sg[0]
    if (op === 'm') {
      if (pts.length > 2) polis.push(pts)
      cur = P(sg[1], sg[2]); pts = [cur]
    } else if (op === 'l') {
      cur = P(sg[1], sg[2]); pts.push(cur)
    } else if (op === 'c') {
      const p0 = cur || P(sg[1], sg[2]), p1 = P(sg[1], sg[2]), p2 = P(sg[3], sg[4]), p3 = P(sg[5], sg[6])
      for (let k = 1; k <= 8; k++) {
        const u = k / 8.0, mu = 1 - u
        pts.push([mu * mu * mu * p0[0] + 3 * mu * mu * u * p1[0] + 3 * mu * u * u * p2[0] + u * u * u * p3[0],
                  mu * mu * mu * p0[1] + 3 * mu * mu * u * p1[1] + 3 * mu * u * u * p2[1] + u * u * u * p3[1]])
      }
      cur = p3
    } else if (op === 're') {
      const [X, Y, Wd, Ht] = [sg[1], sg[2], sg[3], sg[4]]
      if (pts.length > 2) polis.push(pts)
      pts = [P(X, Y), P(X + Wd, Y), P(X + Wd, Y + Ht), P(X, Y + Ht)]
      cur = pts[0]
    } else if (op === 'h') {
      if (pts.length > 2) polis.push(pts)
      pts = []
    }
  }
  if (pts.length > 2) polis.push(pts)
  return polis
}

// ── Pillow 12.2, libImaging/Draw.c: `ImagingDrawPolygon(fill=1)` + `polygon_generic` ──────────
const roundf = (x) => (x < 0 ? -Math.round(-x) : Math.round(x))                  // C roundf: mitad lejos de cero
const ROUND_UP = (f) => (f >= 0.0 ? Math.floor(Math.fround(f + 0.5)) : -Math.floor(Math.fround(Math.abs(f) + 0.5)))
const ROUND_DOWN = (f) => (f >= 0.0 ? Math.ceil(Math.fround(f - 0.5)) : -Math.ceil(Math.fround(Math.abs(f) - 0.5)))
// `(ymin - e.y0) * e.dx + e.x0` con `dx` float: producto y suma en precisión simple
const xEn = (e, y) => Math.fround(Math.fround((y - e.y0) * e.dx) + e.x0)

function addEdge(x0, y0, x1, y1) {
  const e = { x0, y0, xmin: x0 <= x1 ? x0 : x1, xmax: x0 <= x1 ? x1 : x0,
              ymin: y0 <= y1 ? y0 : y1, ymax: y0 <= y1 ? y1 : y0, d: 0, dx: 0 }
  if (y0 !== y1) {
    e.dx = Math.fround((x1 - x0) / (y1 - y0))          // ((float)(x1 - x0)) / (y1 - y0)
    e.d = y0 === e.ymin ? 1 : -1
  }
  return e
}

function hline8(img, x0, y0, x1) {
  if (y0 >= 0 && y0 < img.h) {
    if (x0 < 0) x0 = 0
    else if (x0 >= img.w) return
    if (x1 < 0) return
    else if (x1 >= img.w) x1 = img.w - 1
    if (x0 <= x1) img.d.fill(1, y0 * img.w + x0, y0 * img.w + x1 + 1)
  }
}

function polygonGeneric(img, e) {
  const n = e.length
  if (n <= 0) return
  let ymin = img.h - 1, ymax = 0
  const tabla = []
  for (let i = 0; i < n; i++) {
    if (ymin > e[i].ymin) ymin = e[i].ymin
    if (ymax < e[i].ymax) ymax = e[i].ymax
    if (e[i].ymin === e[i].ymax) { hline8(img, e[i].xmin, e[i].ymin, e[i].xmax); continue }
    tabla.push(e[i])
  }
  if (ymin < 0) ymin = 0
  if (ymax > img.h) ymax = img.h
  const xx = new Float32Array(tabla.length * 2)
  for (; ymin <= ymax; ymin++) {
    let j = 0
    for (let i = 0; i < tabla.length; i++) {
      const cur = tabla[i]
      if (ymin >= cur.ymin && ymin <= cur.ymax) {
        xx[j++] = xEn(cur, ymin)
        if (ymin === cur.ymax && ymin < ymax) {
          xx[j] = xx[j - 1]
          j++
        } else if ((ymin === cur.ymin || ymin === cur.ymax) && cur.dx !== 0) {
          for (let k = 0; k < i; k++) {
            const otro = tabla[k]
            if ((ymin !== otro.ymin && ymin !== otro.ymax) || otro.dx === 0) continue
            if (roundf(xx[j - 1]) === roundf(xEn(otro, ymin))) {
              const offset = ymin === cur.ymax ? -1 : 1
              const adj = xEn(cur, ymin + offset)
              if (ymin + offset >= otro.ymin && ymin + offset <= otro.ymax) {
                const adjOtro = xEn(otro, ymin + offset)
                if (xx[j - 1] > Math.fround(adj + 1) && xx[j - 1] > Math.fround(adjOtro + 1)) {
                  xx[j - 1] = Math.fround(roundf(Math.max(adj, adjOtro)) + 1)
                } else if (xx[j - 1] < Math.fround(adj - 1) && xx[j - 1] < Math.fround(adjOtro - 1)) {
                  xx[j - 1] = Math.fround(roundf(Math.min(adj, adjOtro)) - 1)
                }
                break
              }
            }
          }
        }
      }
    }
    xx.subarray(0, j).sort()
    for (let i = 1; i < j; i += 2) hline8(img, ROUND_UP(xx[i - 1]), ymin, ROUND_DOWN(xx[i]))
  }
}

/** `ImageDraw.polygon(pts, fill=1, outline=1)` en una imagen modo "1": sólo el relleno. */
export function pintarPoligono(img, pts) {
  const n = pts.length
  if (n < 2) return
  const xy = new Int32Array(2 * n)
  for (let i = 0; i < n; i++) { xy[2 * i] = Math.trunc(pts[i][0]); xy[2 * i + 1] = Math.trunc(pts[i][1]) }   // (int)xy
  const e = []
  let i
  for (i = 0; i < n - 1; i++) {
    const x0 = xy[i * 2], y0 = xy[i * 2 + 1], x1 = xy[i * 2 + 2], y1 = xy[i * 2 + 3]
    if (y0 === y1 && i !== 0 && y0 === xy[i * 2 - 1]) {
      const ult = e[e.length - 1]
      if (x1 > x0 && x0 > xy[i * 2 - 2]) { ult.xmax = x1; continue }
      else if (x1 < x0 && x0 < xy[i * 2 - 2]) { ult.xmin = x1; continue }
    }
    e.push(addEdge(x0, y0, x1, y1))
  }
  if (xy[i * 2] !== xy[0] || xy[i * 2 + 1] !== xy[1]) e.push(addEdge(xy[i * 2], xy[i * 2 + 1], xy[0], xy[1]))
  polygonGeneric(img, e)
}

/** `rell.reshape(H//sobre, sobre, W//sobre, sobre).any(axis=(1, 3))`, con ceros de relleno. */
function reducir(fino, sobre) {
  const H = Math.floor((fino.h + sobre - 1) / sobre) * sobre
  const W = Math.floor((fino.w + sobre - 1) / sobre) * sobre
  const h = H / sobre, w = W / sobre
  const m = mascara(h, w)
  let alguna = false
  for (let y = 0; y < fino.h; y++) {
    const fy = Math.floor(y / sobre)
    for (let x = 0; x < fino.w; x++) {
      if (fino.d[y * fino.w + x]) { m.d[fy * w + Math.floor(x / sobre)] = 1; alguna = true }
    }
  }
  if (!alguna) m.d.fill(1)
  return m
}

/**
 * `_mascara_contorno(b, cell_pt)`: la máscara de ocupación de una pieza a partir de su contorno
 * (la base del motor: `cont`, `S`, `x0`, `y0`, `B`, `W`, `Hp`). Se pinta el polígono a `SOBRE`×
 * la resolución, se dilata el borde de corte y se reduce a celdas con «alguna submuestra».
 */
export function mascaraContorno(b, cellPt, sobre = SOBRE) {
  const zoom = sobre / cellPt
  const Wp = Number(b.W) + 2 * Number(b.B), Hp = Number(b.Hp), B = Number(b.B)
  const wPx = Math.max(1, Math.ceil(Wp * zoom)), hPx = Math.max(1, Math.ceil(Hp * zoom))
  let fino = mascara(hPx, wPx)
  for (const poli of poligonosContorno(b.cont, b.S, b.x0, b.y0, B)) {
    const pts = poli.map(([x, y]) => [x * zoom, (Hp - y) * zoom])      // y hacia abajo, como el pixmap
    if (pts.length > 2) pintarPoligono(fino, pts)
  }
  const r = Math.trunc(Math.ceil(B * zoom))
  if (r > 0) fino = dilatar(fino, disco(r))                              // el borde de corte, por fuera
  return reducir(fino, sobre)
}

// ─────────────────────────────────────────────────────────────────────────────────────────────
// La hoja como bits (una palabra = 32 celdas) y la prueba de solapamiento exacta
// ─────────────────────────────────────────────────────────────────────────────────────────────

function hojaNueva(altoC, anchoC) {
  const words = (anchoC + 31) >> 5
  return { h: altoC, w: anchoC, words, bits: new Uint32Array(altoC * words) }
}

/** La máscara corrida `s` bits (0..31), por fila, para operar palabra contra palabra. */
function corrida(m, s) {
  const nw = (s + m.w + 31) >> 5
  const bits = new Uint32Array(m.h * nw)
  for (let y = 0; y < m.h; y++) {
    const fila = y * m.w, base = y * nw
    for (let x = 0; x < m.w; x++) {
      if (m.d[fila + x]) { const p = x + s; bits[base + (p >> 5)] |= (1 << (p & 31)) }
    }
  }
  return { bits, nw }
}

function corridas(m) {
  if (!m._c) m._c = new Array(32).fill(null)
  return m._c
}

function corridaDe(m, s) {
  const c = corridas(m)
  return c[s] || (c[s] = corrida(m, s))
}

/** `(G[yy:yy+hh, xx:xx+ww] & m).any()`: ¿alguna celda ocupada bajo la máscara? (sin chequear bordes) */
function choca(G, yy, xx, m) {
  const s = xx & 31, wo = xx >> 5
  const { bits, nw } = corridaDe(m, s)
  const gb = G.bits, W = G.words
  for (let r = 0; r < m.h; r++) {
    const g = (yy + r) * W + wo, b = r * nw
    for (let j = 0; j < nw; j++) if (gb[g + j] & bits[b + j]) return true
  }
  return false
}

/** `G[...] |= m` en (yy, xx). */
function estampar(G, yy, xx, m) {
  const s = xx & 31, wo = xx >> 5
  const { bits, nw } = corridaDe(m, s)
  const gb = G.bits, W = G.words
  for (let r = 0; r < m.h; r++) {
    const g = (yy + r) * W + wo, b = r * nw
    for (let j = 0; j < nw; j++) gb[g + j] |= bits[b + j]
  }
}

/** El menor x en [desde, hasta] donde la máscara entra en la fila `yy` sin pisar nada, o -1. */
function primerLibre(G, yy, m, desde, hasta) {
  for (let x = desde; x <= hasta; x++) if (!choca(G, yy, x, m)) return x
  return -1
}

/**
 * `fftconvolve(...) < 0.5` + `_elegir_posicion(valid, hh, estrategia)` en una sola pasada: la
 * primera posición válida en el orden que impone la estrategia. `[y, x, score]` o null.
 *   · bl:     lexsort((xs, ys + hh)) → menor y, después menor x;
 *   · bandas: lexsort((xs, (ys + hh) // 25)) → menor banda, menor x, y en empate el menor y
 *             (np.where devuelve fila mayor y lexsort es estable).
 */
function elegirPosicion(G, ylim, m, estrategia) {
  const hh = m.h, ww = m.w
  const yMax = ylim - hh, xMax = G.w - ww
  if (yMax < 0 || xMax < 0) return null
  if (estrategia === 'bl') {
    for (let y = 0; y <= yMax; y++) {
      const x = primerLibre(G, y, m, 0, xMax)
      if (x >= 0) return [y, x, [y + hh, x]]
    }
    return null
  }
  if (estrategia === 'bandas') {
    const Q = 25
    let banda = -1, mejorX = -1, mejorY = -1
    for (let y = 0; y <= yMax; y++) {
      const b = Math.floor((y + hh) / Q)
      if (b !== banda) {
        if (mejorX >= 0) break
        banda = b
      }
      if (mejorX === 0) continue                     // nada mejora a x = 0 dentro de la banda
      const x = primerLibre(G, y, m, 0, mejorX >= 0 ? mejorX - 1 : xMax)
      if (x >= 0) { mejorX = x; mejorY = y }
    }
    if (mejorX < 0) return null
    return [mejorY, mejorX, [Math.floor((mejorY + hh) / Q), mejorX]]
  }
  throw new Error(`Estrategia desconocida: ${JSON.stringify(estrategia)}`)
}

// ─────────────────────────────────────────────────────────────────────────────────────────────
// `_preparar`, `anidar_contorno`, `_anidar_estrategia`
// ─────────────────────────────────────────────────────────────────────────────────────────────

const claveGeo = (p, cellPt, espC, paso) => JSON.stringify([
  p._molde ?? null, p.pieza ?? null, p.talle ?? null, p.variante ?? null, p.rotacion,
  p.borde_cm ?? 0, cellPt, espC, paso])

/** `_preparar(piezas, cfg)`: parámetros de grilla + máscaras base (una por geometría). */
export function preparar(piezas, cfg) {
  const cellPt = (cfg.resolucion_mm ?? 2) / 10 * CM
  const m = cfg.margenes_cm
  const anchoC = Math.trunc((cfg.ancho_cm - m.izq - m.der) * CM / cellPt)
  const altoC = Math.trunc((cfg.altura_max_cm * CM - (m.sup + m.inf) * CM) / cellPt)
  const espC = Math.max(1, Math.ceil(cfg.espaciado_cm * CM / cellPt))
  const paso = cfg.paso_libre_grados ?? 15
  const geo = new Map()
  const cacheKey = (p) => JSON.stringify([cellPt, espC, paso, p.rotacion, p.borde_cm ?? 0])
  for (const p of piezas) {
    const ck = cacheKey(p)
    if (p._cache_key === ck) continue
    const gk = claveGeo(p, cellPt, espC, paso)
    p._geo_key = gk
    const hit = geo.get(gk)
    if (hit) {
      p._mask = hit._mask; p._borde_c = hit._borde_c; p._cell_pt = hit._cell_pt
      p._candidatos_angulo = hit._candidatos_angulo; p._cache_key = ck
      continue
    }
    const b = p.base
    if (!b || b.cont == null) throw new Error(`La pieza ${p.etiqueta} no trae su contorno (base.cont): el navegador no rasteriza`)
    p._mask = mascaraContorno(b, cellPt)
    p._borde_c = Math.ceil((p.borde_cm ?? 0) * CM / cellPt)
    p._cell_pt = cellPt
    const candidatos = []
    for (const ang of angulos(p.rotacion, paso)) {
      const mr = rotar(p._mask, ang)
      const pad = p._borde_c + espC
      const mrP = rellenar(mr, pad)
      const mrCol = p._borde_c ? dilatar(mrP, disco(p._borde_c)) : mrP
      const d = disco(espC)
      const mrTest = d ? dilatar(mrCol, d) : mrCol
      if (mrTest.h > altoC || mrTest.w > anchoC) continue
      candidatos.push({ ang, mrCol, mrTest })
    }
    p._candidatos_angulo = candidatos
    p._cache_key = ck
    geo.set(gk, { _mask: p._mask, _borde_c: p._borde_c, _cell_pt: p._cell_pt, _candidatos_angulo: candidatos })
  }
  return { cellPt, anchoC, altoC, espC, paso }
}

/** `sorted(idx, key=..., reverse=True)`: descendente y ESTABLE (los empates, en orden de entrada). */
const ordenDesc = (idx, clave) => idx.slice().sort((a, b) => clave(b) - clave(a))

/**
 * `anidar_contorno(piezas, cfg)`: prueba varios órdenes × estrategias y devuelve
 * `{colocaciones, area}` del layout de MENOR consumo de tela. `colocaciones` = hojas, cada una
 * `[{pieza, ang, cx, cy, bw, bh}, ...]`.
 */
export function anidarContorno(piezas, cfg) {
  if (!piezas || !piezas.length) return { colocaciones: [], area: 0.0 }
  const prep = preparar(piezas, cfg)
  const idx = piezas.map((_, i) => i)
  const A = idx.map((i) => contar(piezas[i]._mask))
  const Hh = idx.map((i) => piezas[i]._mask.h)
  const Ww = idx.map((i) => piezas[i]._mask.w)
  let candidatos
  if (piezas.length > 15) candidatos = [ordenDesc(idx, (i) => A[i])]
  else if (piezas.length > 8) candidatos = [ordenDesc(idx, (i) => A[i]), ordenDesc(idx, (i) => Math.max(Hh[i], Ww[i]))]
  else candidatos = [ordenDesc(idx, (i) => A[i]), ordenDesc(idx, (i) => Hh[i]), ordenDesc(idx, (i) => Ww[i]),
                     ordenDesc(idx, (i) => Math.max(Hh[i], Ww[i]))]
  const ordenes = [], vistos = new Set()
  for (const o of candidatos) {
    const k = o.join(',')
    if (!vistos.has(k)) { vistos.add(k); ordenes.push(o) }
  }
  let estrategias = cfg.estrategias ?? ['bl', 'bandas']
  if (piezas.length > 12) estrategias = ['bl']
  let mejor = null
  for (const orden of ordenes) {
    for (const est of estrategias) {
      const { colocaciones, area } = anidarEstrategia(piezas, cfg, est, orden, prep)
      let consumo = 0
      for (const h of colocaciones) {
        if (!h.length) continue
        let mx = -Infinity
        for (const c of h) { const v = c.cy + c.bh / 2; if (v > mx) mx = v }
        consumo += mx
      }
      if (mejor === null || consumo < mejor.consumo) mejor = { consumo, colocaciones, area }
    }
  }
  return { colocaciones: mejor.colocaciones, area: mejor.area, consumo: mejor.consumo }
}

function bboxGirado(p, ang) {
  const th = ang * (Math.PI / 180)                      // math.radians
  return [Math.abs(p.w * Math.cos(th)) + Math.abs(p.h * Math.sin(th)),
          Math.abs(p.w * Math.sin(th)) + Math.abs(p.h * Math.cos(th))]
}

/** `_anidar_estrategia(piezas, cfg, estrategia, orden, prep)` → `{colocaciones, area}`. */
export function anidarEstrategia(piezas, cfg, estrategia, orden, prep) {
  const { cellPt, anchoC, altoC, paso } = prep
  const hojasG = [], hojasSky = [], colocaciones = []
  const nuevaHoja = () => {
    hojasG.push(hojaNueva(altoC, anchoC)); hojasSky.push(0); colocaciones.push([])
    return hojasG.length - 1
  }
  nuevaHoja()
  let areaC2 = 0
  // BLOQUES DE PIEZAS IDÉNTICAS (plan E7): una geometría ya colocada busca primero, sin barrer la
  // hoja, al lado de la última igual (misma fila a la derecha, la fila siguiente, una más); si no
  // entra, la búsqueda completa sólo con el ángulo de su anterior y desde su hoja en adelante.
  const bloques = !(cfg._sin_bloques)
  const ultimo = new Map()            // geo_key → {h, ang, y, x, mrCol, mrTest}
  Object.assign(DEBUG, { bloque: 0, fft: 0, sin_geo: 0, sin_ultimo: 0, sin_lugar: 0 })

  const cabe = (G, yy, xx, m) => {
    if (yy < 0 || xx < 0 || yy + m.h > altoC || xx + m.w > anchoC) return false
    return !choca(G, yy, xx, m)
  }
  const xEnFila = (G, yy, m, desde) => {
    if (yy < 0 || yy + m.h > altoC || m.w > anchoC) return -1
    return primerLibre(G, yy, m, desde, anchoC - m.w)
  }
  const colocar = (h, p, ang, y, x, mrCol, mrTest) => {
    const hh = mrTest.h, ww = mrTest.w
    const dy = Math.floor((hh - mrCol.h) / 2), dx = Math.floor((ww - mrCol.w) / 2)
    estampar(hojasG[h], y + dy, x + dx, mrCol)
    hojasSky[h] = Math.max(hojasSky[h], y + hh)
    if (p._geo_key != null) ultimo.set(p._geo_key, { h, ang, y, x, mrCol, mrTest })
    const [bw, bh] = bboxGirado(p, ang)
    colocaciones[h].push({ pieza: p, ang, cx: (x + ww / 2) * cellPt, cy: (y + hh / 2) * cellPt, bw, bh })
    areaC2 += contar(p._mask)
  }

  for (const i of orden) {
    const p = piezas[i]
    const candidatosPorAngulo = p._candidatos_angulo
    if (!candidatosPorAngulo.length) throw new Error(`La pieza ${p.etiqueta} no entra en la hoja con ninguna rotación permitida.`)
    let colocada = false
    const u = bloques ? (ultimo.get(p._geo_key) ?? null) : null
    if (u !== null) {
      const G = hojasG[u.h], mt = u.mrTest
      const hh = mt.h, ww = mt.w
      let pos = null
      for (const [yy, desde] of [[u.y, u.x + ww], [u.y + hh, 0], [u.y + 2 * hh, 0]]) {
        const xx = xEnFila(G, yy, mt, desde)
        if (xx >= 0) { pos = [yy, xx]; break }
      }
      if (pos && cabe(G, pos[0], pos[1], mt)) {
        colocar(u.h, p, u.ang, pos[0], pos[1], u.mrCol, mt)
        colocada = true
        DEBUG.bloque++
      }
      if (!colocada) DEBUG.sin_lugar++
    } else if (p._geo_key == null) DEBUG.sin_geo++
    else DEBUG.sin_ultimo++
    if (colocada) continue
    DEBUG.fft++
    let fases
    if (u) {
      const mismo = candidatosPorAngulo.filter((c) => c.ang === u.ang)
      fases = [mismo.length ? mismo : candidatosPorAngulo]
    } else if (p.rotacion === 'libre' && candidatosPorAngulo.length > 8) {
      const grueso = candidatosPorAngulo.filter((c) => c.ang % 90 === 0)
      fases = [grueso.length ? grueso : candidatosPorAngulo.slice(0, 4), null]     // null = los vecinos del mejor
    } else fases = [candidatosPorAngulo]
    for (let hIdx = u ? u.h : 0; hIdx < hojasG.length; hIdx++) {
      const G = hojasG[hIdx], sky = hojasSky[hIdx]
      let mejor = null
      for (let cands of fases) {
        if (cands === null) {
          if (mejor === null) continue
          const vistos = new Set(fases[0].map((c) => c.ang))
          const ang0 = mejor.ang
          const tope = 2 * Math.max(1, Math.trunc(paso))
          cands = candidatosPorAngulo.filter((c) => !vistos.has(c.ang) &&
            Math.min(Math.abs(c.ang - ang0), 360 - Math.abs(c.ang - ang0)) <= tope)
        }
        for (const { ang, mrCol, mrTest } of cands) {
          const hh = mrTest.h
          const ylim = Math.min(altoC, sky + hh)
          if (ylim < hh) continue
          const r = elegirPosicion(G, ylim, mrTest, estrategia)
          if (r === null) continue
          const [y, x, score] = r
          if (mejor === null || compararTuplas(score, mejor.score) < 0) mejor = { score, ang, mrCol, mrTest, y, x }
        }
      }
      if (mejor) {
        colocar(hIdx, p, mejor.ang, mejor.y, mejor.x, mejor.mrCol, mejor.mrTest)
        colocada = true
        break
      }
    }
    if (!colocada) {
      const h = nuevaHoja()
      // hoja vacía: el ángulo de menor altura (el primero en empate) y colocar en el origen
      let c = candidatosPorAngulo[0]
      for (const k of candidatosPorAngulo) if (k.mrTest.h < c.mrTest.h) c = k
      colocar(h, p, c.ang, 0, 0, c.mrCol, c.mrTest)
    }
  }
  const k = cellPt / CM
  return { colocaciones, area: areaC2 * (k * k) }
}
