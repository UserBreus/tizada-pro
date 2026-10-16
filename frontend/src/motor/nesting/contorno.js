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
  // `libres[y]`: cuántas celdas libres le quedan a la fila y (MAPA 707): con eso la búsqueda descarta
  // de una las filas donde la pieza no puede entrar, sin probar x por x. `prof[x]`: la fila siguiente
  // a la última ocupada de la columna x (el frente de la hoja, para la estrategia «hueco», MAPA 714)
  return { h: altoC, w: anchoC, words, bits: new Uint32Array(altoC * words), libres: new Int32Array(altoC).fill(anchoC), prof: new Int32Array(anchoC) }
}

/** El perfil inferior de la máscara (gemelo de `_perfil_inferior`): `b[j]` = la fila siguiente a la
 * última ocupada de la columna j (0 si vacía) y `cols` = las columnas con algo. Una vez por máscara. */
function perfilInferior(m) {
  if (!m._pinf) {
    const b = new Int32Array(m.w), cols = []
    for (let x = 0; x < m.w; x++) {
      for (let y = m.h - 1; y >= 0; y--) if (m.d[y * m.w + x]) { b[x] = y + 1; break }
      if (b[x] > 0) cols.push(x)
    }
    m._pinf = { b, cols: Int32Array.from(cols) }
  }
  return m._pinf
}

function bitsEn(v) {
  v = v - ((v >>> 1) & 0x55555555)
  v = (v & 0x33333333) + ((v >>> 2) & 0x33333333)
  return (((v + (v >>> 4)) & 0x0f0f0f0f) * 0x01010101) >>> 24
}

/** Cuántas celdas ocupa la máscara en cada fila (se calcula una vez por máscara). */
function porFila(m) {
  if (!m._pf) {
    const pf = new Int32Array(m.h)
    for (let y = 0; y < m.h; y++) { let n = 0; const f = y * m.w; for (let x = 0; x < m.w; x++) if (m.d[f + x]) n++; pf[y] = n }
    m._pf = pf
  }
  return m._pf
}

/** DESCARTE EXACTO (MAPA 707): si alguna fila de la hoja tiene menos celdas libres que las que la
 * máscara ocupa en esa fila, la máscara no puede entrar en NINGÚN x de esa fila. Es una condición
 * necesaria: no cambia ningún resultado, sólo evita probar x por x donde no hay lugar. */
function puedeFila(G, yy, m) {
  const pf = porFila(m), L = G.libres
  for (let r = 0; r < m.h; r++) if (L[yy + r] < pf[r]) return false
  return true
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
  const gb = G.bits, W = G.words, L = G.libres
  for (let r = 0; r < m.h; r++) {
    const g = (yy + r) * W + wo, b = r * nw
    let nuevas = 0
    for (let j = 0; j < nw; j++) { const v = bits[b + j] & ~gb[g + j]; if (v) nuevas += bitsEn(v); gb[g + j] |= bits[b + j] }
    if (L) L[yy + r] -= nuevas
    if (G.tramo) G.tramo[yy + r] = -1          // sus tramos libres cambiaron (MAPA 719)
  }
  if (G.col) {                                 // y las columnas (MAPA 719)
    for (let r = 0; r < m.h; r++) {
      const yr = yy + r, w = yr >> 5, bit = 1 << (yr & 31)
      for (let c = 0; c < m.w; c++) if (m.d[r * m.w + c]) G.col[(xx + c) * G.hw + w] |= bit
    }
  }
}

/** LOS TRAMOS LIBRES de la fila `y` (MAPA 719): `[inicio, fin)` de cada tramo de celdas libres, en orden, y
 * el más largo en `G.tramo[y]`. Se recalcula sólo si la fila cambió (`estampar` la marca). */
function tramosDe(G, y) {
  if (!G.tramo) { G.tramo = new Int32Array(G.h).fill(-1); G.tramos = new Array(G.h) }
  if (G.tramo[y] < 0) {
    const out = [], W = G.w, f = y * G.words, gb = G.bits
    let ini = -1, mx = 0
    for (let x = 0; x <= W; x++) {
      const libre = x < W && !((gb[f + (x >> 5)] >>> (x & 31)) & 1)
      if (libre) { if (ini < 0) ini = x }
      else if (ini >= 0) { out.push(ini, x); if (x - ini > mx) mx = x - ini; ini = -1 }
    }
    G.tramos[y] = out
    G.tramo[y] = mx
  }
  return G.tramos[y]
}

/** De la máscara: el tramo ocupado más largo de cada fila (largo y dónde empieza) y la fila con el mayor. */
function tramosMascara(m) {
  if (!m._tm) {
    const len = new Int32Array(m.h), off = new Int32Array(m.h)
    let rMax = 0
    for (let y = 0; y < m.h; y++) {
      let ini = -1
      for (let x = 0; x <= m.w; x++) {
        const on = x < m.w && m.d[y * m.w + x]
        if (on) { if (ini < 0) ini = x }
        else if (ini >= 0) { if (x - ini > len[y]) { len[y] = x - ini; off[y] = ini } ini = -1 }
      }
      if (len[y] > len[rMax]) rMax = y
    }
    m._tm = { len, off, rMax }
  }
  return m._tm
}

/** LAS COLUMNAS DE LA HOJA (MAPA 719): la misma ocupación por columna (un bit por fila), para saber de una
 * vez cuál es la próxima celda ocupada debajo de una fila. Se arma la primera vez y `estampar` la mantiene. */
function columnasDe(G) {
  if (!G.col) {
    G.hw = (G.h + 31) >> 5
    G.col = new Uint32Array(G.w * G.hw)
    for (let y = 0; y < G.h; y++) {
      const f = y * G.words
      for (let x = 0; x < G.w; x++) if ((G.bits[f + (x >> 5)] >>> (x & 31)) & 1) G.col[x * G.hw + (y >> 5)] |= (1 << (y & 31))
    }
  }
  return G.col
}

/** La primera fila >= `y` ocupada en la columna `x`; si no hay ninguna hasta `lim`, devuelve `lim` (no hace
 * falta mirar más abajo: la búsqueda no pasa de ahí). */
function proximaOcupada(G, x, y, lim) {
  if (y >= lim) return lim
  const col = G.col, base = x * G.hw, wl = Math.min(G.hw - 1, lim >> 5)
  let w = y >> 5
  let b = col[base + w] & (~0 << (y & 31))
  while (!b) {
    if (++w > wl) return lim
    b = col[base + w]
  }
  const r = (w << 5) + (31 - Math.clz32(b & -b))
  return r < lim ? r : lim
}

/** La máscara entra en (y, x): ¿hasta qué fila sigue entrando si se la baja? Al bajar una fila sólo cambian
 * las celdas de su BORDE DE ABAJO, así que la primera que choca es la menor «próxima ocupada» de esas celdas. */
function bajaHasta(G, y, x, bi, yTope) {
  columnasDe(G)
  let fin = yTope
  for (let i = 0; i < bi.length; i += 2) {
    const r = bi[i]
    const t = proximaOcupada(G, x + bi[i + 1], y + r + 1, fin + r + 1) - r - 1
    if (t < fin) fin = t
  }
  return fin
}

/** El BORDE DE ABAJO de la máscara (MAPA 719): la celda más baja de cada tramo vertical, como pares [fila,
 * columna]. Si la máscara entra en (y-1, x), entra en (y, x) si y sólo si esas celdas están libres en (y, x). */
function bordeInferior(m) {
  if (!m._bi) {
    const out = []
    for (let r = 0; r < m.h; r++) for (let c = 0; c < m.w; c++) {
      if (m.d[r * m.w + c] && (r + 1 >= m.h || !m.d[(r + 1) * m.w + c])) out.push(r, c)
    }
    m._bi = Int32Array.from(out)
  }
  return m._bi
}

/** ¿Puede entrar la máscara en la fila `y`? Condición NECESARIA (exacta para descartar): cada fila de la
 * máscara necesita en su fila de la hoja un tramo libre al menos tan largo como su tramo ocupado más largo. */
function cabenTramos(G, y, m) {
  const { len } = tramosMascara(m)
  for (let r = 0; r < m.h; r++) {
    if (!len[r]) continue
    tramosDe(G, y + r)
    if (G.tramo[y + r] < len[r]) return false
  }
  return true
}

/** Los x de [desde, hasta] donde la máscara PUEDE entrar en la fila `yy` (MAPA 728), como pares [a, b]
 * crecientes: su tramo ocupado más largo (fila `rMax`) tiene que caer adentro de un tramo LIBRE de la fila
 * `yy + rMax` de la hoja; en cualquier otro x choca seguro. Condición necesaria: no cambia ningún resultado,
 * sólo evita probar x por x donde no hay lugar (igual que «contacto», MAPA 719). */
function rangosX(G, yy, m, desde, hasta) {
  const { len, off, rMax } = tramosMascara(m)
  const L = len[rMax], o = off[rMax]
  if (!L) return [desde, hasta]
  const tr = tramosDe(G, yy + rMax), out = []
  for (let t = 0; t < tr.length; t += 2) {
    if (tr[t + 1] - tr[t] < L) continue
    const a = Math.max(desde, tr[t] - o), b = Math.min(hasta, tr[t + 1] - L - o)
    if (a <= b) out.push(a, b)
  }
  return out
}

/** El menor x en [desde, hasta] donde la máscara entra en la fila `yy` sin pisar nada, o -1. */
function primerLibre(G, yy, m, desde, hasta) {
  const r = rangosX(G, yy, m, desde, hasta)
  for (let t = 0; t < r.length; t += 2) for (let x = r[t]; x <= r[t + 1]; x++) if (!choca(G, yy, x, m)) return x
  return -1
}

/**
 * `fftconvolve(...) < 0.5` + `_elegir_posicion(valid, hh, estrategia)` en una sola pasada: la
 * primera posición válida en el orden que impone la estrategia. `[y, x, score]` o null.
 *   · bl:     lexsort((xs, ys + hh)) → menor y, después menor x;
 *   · bandas: lexsort((xs, (ys + hh) // 25)) → menor banda, menor x, y en empate el menor y
 *             (np.where devuelve fila mayor y lexsort es estable).
 */
/** `CONTACTO_PESO` (MAPA 719): cuánto vale cada celda de largo de más frente a una de borde que toca. Gemelo. */
const CONTACTO_PESO = 2

/** `_anillo` (MAPA 719) — gemelo EXACTO: las celdas vecinas de lado de la máscara (con margen de 1), como
 * pares [fila, columna] relativos al origen de la máscara (de -1 a h y de -1 a w). Una vez por máscara. */
function anillo(m) {
  if (!m._anillo) {
    const H = m.h + 2, W = m.w + 2
    const en = (y, x) => y >= 0 && y < m.h && x >= 0 && x < m.w && m.d[y * m.w + x]
    const out = []
    for (let r = 0; r < H; r++) for (let c = 0; c < W; c++) {
      const y = r - 1, x = c - 1
      if (en(y, x)) continue
      if (en(y - 1, x) || en(y + 1, x) || en(y, x - 1) || en(y, x + 1)) out.push(y, x)
    }
    m._anillo = Int32Array.from(out)
    // para el tope (MAPA 719): cuántas celdas del anillo hay por ENCIMA de cada fila relativa (`menos[i]` = las
    // de fila < i - 1) y cuántas caen en las columnas de los costados (las que pueden tocar pared)
    const menos = new Int32Array(m.h + 3)
    let costados = 0
    for (let i = 0; i < out.length; i += 2) {
      menos[out[i] + 2]++
      if (out[i + 1] === -1 || out[i + 1] === m.w) costados++
    }
    for (let i = 1; i < menos.length; i++) menos[i] += menos[i - 1]
    m._anilloMenos = menos
    m._anilloCostados = costados
  }
  return m._anillo
}

/** Cuántas celdas del anillo están ocupadas o son pared en (y, x) — gemelo de `_contacto`: arriba, izquierda
 * y derecha son pared; desde `ylim` para abajo, nada. null si no puede pasar de `necesita`. */
function contactoEn(G, ylim, y, x, cel, necesita) {
  const n = cel.length >> 1, W = G.w, words = G.words, bits = G.bits
  let c = 0
  for (let i = 0; i < n; i++) {
    const gy = y + cel[2 * i], gx = x + cel[2 * i + 1]
    if (gy < 0) c++
    else if (gy < ylim) {
      if (gx < 0 || gx >= W) c++
      else c += (bits[gy * words + (gx >> 5)] >>> (gx & 31)) & 1
    }
    if (c + (n - 1 - i) <= necesita) return null
  }
  return c
}

function elegirPosicion(G, ylim, m, estrategia, hueco = null, tope = Infinity) {
  const hh = m.h, ww = m.w
  const yMax = ylim - hh, xMax = G.w - ww
  if (yMax < 0 || xMax < 0) return null
  // 🔴 CORTE EXACTO (MAPA 715): `tope` = el fondo del mejor lugar ya encontrado con otro giro. Con «bl» y
  // «hueco» gana el fondo más alto, así que este giro sólo puede ganar en una fila con `y + hh <= tope`
  // (en empate de fondo decide lo que sigue en la tupla): más abajo no hace falta buscar. Lo revisado
  // queda en la memoria de la búsqueda igual que siempre (la hoja sólo se llena). Mismo resultado que
  // revisar todo: con giro libre (24 giros) los giros de 15°, más altos, se descartaban recorriendo
  // toda la franja de abajo de la mesa (593 banderines: 20 s en el navegador).
  const yHasta = Math.min(yMax, tope - hh)
  if (estrategia === 'contacto') {
    // 🔴 EL MAYOR CONTACTO (MAPA 719) — gemelo de `_elegir_posicion` «contacto»: donde más borde toca menos
    // CONTACTO_PESO por celda que alarga; empate, el fondo más alto y más a la izquierda. EXACTO y rápido:
    // · se retoma donde quedó (lo de antes de la primera posición válida no vuelve a servir: la hoja se llena);
    // · una fila deja de revisarse cuando ni tocando con todo el anillo podría ganar (el largo sólo crece);
    // · `tope` = el mejor valor de los giros ya probados: menos que eso no puede ganar (igual sí: decide el fondo).
    const { sky } = hueco
    const cel = anillo(m), total = cel.length >> 1
    const re = G._reC || (G._reC = new Map())
    const ini = re.get(m) || [0, 0]
    let mejor = null, primero = null, y = ini[0]
    const menos = m._anilloMenos, costados = m._anilloCostados
    // sólo donde la pieza queda APOYADA arriba (gemelo de Python): válida acá y no en la fila de arriba.
    // `hasta[x]` = la última fila del tramo en que la máscara ENTRA bajando por la columna x desde el último
    // lugar apoyado: se calcula de una vez con las columnas de la hoja (`bajaHasta`), sin probar fila por fila
    const hasta = new Int32Array(G.w).fill(-2)
    const bi = bordeInferior(m)
    // FILAS QUE YA NO SIRVEN (exacto: la hoja sólo se llena): una fila donde esta máscara no entró en ningún
    // x no vuelve a servir nunca; se saltan de a muchas con un «siguiente» compartido (union-find)
    const sk = G._skC || (G._skC = new Map())
    let sig = sk.get(m)
    if (!sig) { sig = new Int32Array(G.h + 2); for (let i = 0; i < sig.length; i++) sig[i] = i; sk.set(m, sig) }
    const prox = (v) => { let r = v; while (sig[r] !== r) r = sig[r]; while (sig[v] !== r) { const n = sig[v]; sig[v] = r; v = n } return r }
    for (y = prox(y); y <= yMax; y = prox(y + 1)) {
      const dfondo = Math.max(0, y + hh - sky) * CONTACTO_PESO
      // lo MÁS que puede tocar: las celdas del anillo que quedan arriba de `sky` (de ahí para abajo la hoja
      // está vacía) + las de los costados (pared). Sólo baja al bajar la fila → cortar es exacto.
      const k = Math.min(Math.max(sky - y, -1), hh + 1)
      const cota = Math.min(total, menos[k + 1] + costados)
      if (mejor !== null && cota - dfondo <= mejor[0]) break
      if (cota - dfondo < tope) break
      if ((G.libres && !puedeFila(G, y, m)) || !cabenTramos(G, y, m)) { sig[y] = y + 1; continue }
      let hubo = false
      // sólo los x donde el tramo más largo de la máscara cae adentro de un tramo libre (los demás chocan)
      const { len, off, rMax } = tramosMascara(m)
      const tr = tramosDe(G, y + rMax), L = len[rMax], o = off[rMax]
      const x0 = y === ini[0] ? ini[1] : 0
      for (let t = 0; t < tr.length; t += 2) {
        if (tr[t + 1] - tr[t] < L) continue
        const desde = Math.max(x0, tr[t] - o), hastaX = Math.min(xMax, tr[t + 1] - L - o)
        for (let x = desde; x <= hastaX; x++) {
          if (hasta[x] >= y) {                     // entra, pero también entraba una fila más arriba
            if (primero === null) primero = [y, x]
            hubo = true
            continue
          }
          if (choca(G, y, x, m)) continue
          hubo = true
          // entra y la fila de arriba no: APOYADA. Hasta dónde puede bajar sin chocar (de una vez)
          if (primero === null) primero = [y, x]
          hasta[x] = bajaHasta(G, y, x, bi, yMax)
          const necesita = Math.max(mejor === null ? -Infinity : mejor[0] + dfondo, tope - 1 + dfondo)
          const c = contactoEn(G, ylim, y, x, cel, necesita)
          if (c === null) continue
          const val = c - dfondo
          if (mejor === null || val > mejor[0]) mejor = [val, y, x]
        }
      }
      if (!hubo) sig[y] = y + 1
    }
    if (primero !== null) re.set(m, primero)
    else if (y > ini[0]) re.set(m, [y, 0])
    if (mejor === null) return null
    return [mejor[1], mejor[2], [-mejor[0], mejor[1] + hh, mejor[2]]]
  }
  if (estrategia === 'hueco') {
    // 🔴 EL MENOR HUECO (MAPA 714) — gemelo de `_elegir_posicion` «hueco»: la fila de «bl» (lo más
    // arriba posible) y, entre los lugares de esa fila, el que menos hueco deja atrapado (lo que avanza
    // el frente `G.prof` columna por columna). Se retoma como «bl» (exacto: la hoja sólo se llena).
    const re = G._reH || (G._reH = new Map())
    const ini = re.get(m) || [0, 0]
    const { b, cols, dy, dx } = hueco
    const prof = G.prof
    for (let y = ini[0]; y <= yHasta; y++) {
      if (G.libres && !puedeFila(G, y, m)) continue
      let x = primerLibre(G, y, m, y === ini[0] ? ini[1] : 0, xMax)
      if (x < 0) continue
      re.set(m, [y, x])
      let mejorX = -1, mejorInc = Infinity
      const yb = y + dy
      const rg = rangosX(G, y, m, x, xMax)
      for (let t = 0; t < rg.length; t += 2) for (x = rg[t]; x <= rg[t + 1]; x++) {
        if (choca(G, y, x, m)) continue
        let inc = 0
        const base = x + dx
        for (let k = 0; k < cols.length; k++) {
          const j = cols[k], d = yb + b[j] - prof[base + j]
          if (d > 0) inc += d
          if (inc >= mejorInc) break
        }
        if (inc < mejorInc) { mejorInc = inc; mejorX = x }
      }
      return [y, mejorX, [y + hh, mejorInc, mejorX]]
    }
    if (yHasta + 1 > ini[0]) re.set(m, [yHasta + 1, 0])
    return null
  }
  if (estrategia === 'bl') {
    // 🔴 SE RETOMA DONDE QUEDÓ (MAPA 708): la hoja sólo se LLENA, así que un lugar donde esta máscara
    // no entraba no vuelve a servir nunca. Cada máscara recuerda el primer lugar que todavía puede
    // servir (el último que devolvió, o el fin de lo que ya revisó) y la próxima búsqueda arranca de
    // ahí. Es EXACTO: da lo mismo que revisar todo desde arriba, sin repetir el trabajo.
    const re = G._re || (G._re = new Map())
    const ini = re.get(m) || [0, 0]
    for (let y = ini[0]; y <= yHasta; y++) {
      if (G.libres && !puedeFila(G, y, m)) continue
      const x = primerLibre(G, y, m, y === ini[0] ? ini[1] : 0, xMax)
      if (x >= 0) { re.set(m, [y, x]); return [y, x, [y + hh, x]] }
    }
    if (yHasta + 1 > ini[0]) re.set(m, [yHasta + 1, 0])
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
      if (G.libres && !puedeFila(G, y, m)) continue
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

/** ¿Dos máscaras iguales celda por celda? */
function mascarasIguales(a, b) {
  if (a.h !== b.h || a.w !== b.w) return false
  const da = a.d, db = b.d
  for (let i = 0; i < da.length; i++) if (da[i] !== db[i]) return false
  return true
}

/** `_preparar(piezas, cfg)`: parámetros de grilla + máscaras base (una por geometría). */
export function preparar(piezas, cfg) {
  const cellPt = (cfg.resolucion_mm ?? 2) / 10 * CM
  const m = cfg.margenes_cm
  const espC = Math.max(1, Math.ceil(cfg.espaciado_cm * CM / cellPt))
  // 🔴 LA SEPARACIÓN ES ENTRE PIEZAS, NO CONTRA EL BORDE DE LA MESA (MAPA 633): la grilla se agranda
  // `espC` de cada lado para que el aire de cada pieza pueda colgar afuera, y `colocar` corre las posiciones
  // `espC` al devolverlas: la PIEZA nunca sale de la mesa y el borde lo decide sólo el margen. Antes una
  // bandera de 156 cm no entraba en una mesa de 157. Gemelo: `_preparar` de nesting_contorno.py.
  const anchoC = Math.trunc((cfg.ancho_cm - m.izq - m.der) * CM / cellPt) + 2 * espC
  const altoC = Math.trunc((cfg.altura_max_cm * CM - (m.sup + m.inf) * CM) / cellPt) + 2 * espC
  const paso = cfg.paso_libre_grados ?? 15
  const geo = new Map()
  // 🔴 el tamaño de la mesa va en la clave (MAPA 703): los giros guardados son los que ENTRAN en esta mesa
  const cacheKey = (p) => JSON.stringify([cellPt, espC, paso, p.rotacion, p.borde_cm ?? 0, altoC, anchoC])
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
      // 🔴 un giro que da la MISMA silueta que otro ya anotado no se vuelve a probar (MAPA 708): se
      // acomoda igual y en empate ya ganaba el primero → resultado idéntico, hasta 24 búsquedas menos
      if (candidatos.some((c) => mascarasIguales(c.mrTest, mrTest) && mascarasIguales(c.mrCol, mrCol))) continue
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

// ─────────────────────────────────────────────────────────────────────────────────────────────
// 🔴 EL OPTIMIZADOR (MAPA 728) — gemelo EXACTO de `anidar_contorno` (nesting_contorno.py)
//
// El acomodo de siempre es CODICIOSO: pone cada pieza, en el orden dado, donde mejor queda AHORA. Con un
// orden fijo (las grandes primero) las chicas quedan para el final y se apilan al pie (los cuellos de 20
// camisetas: 14 en filas al final de la última mesa). La tizada mejor sale de OTRO orden — piezas chicas
// intercaladas que caen en los huecos entre las grandes — y ese orden no se adivina: se BUSCA. Por eso:
//   1. la búsqueda de siempre (órdenes × criterios × giros, `candidatosBusqueda`) da el punto de partida;
//   2. CARRILES independientes (uno por hilo de la PC) buscan cada uno con su semilla: el carril 0 es lo de
//      siempre, el 1 mejora el orden de la búsqueda, los demás arrancan de órdenes mezclados; cada intento
//      cambia el orden (dos piezas de lugar, una adelante…) o el criterio, y queda si usa menos tela;
//   3. cada carril termina PULIDO: la última mesa se re-acomoda sola (MAPA 726) y cada pieza sube al lugar
//      libre más alto que tenga (`compactarHoja`): nunca alarga;
//   4. gana el carril de menos tela (empate: el de número más bajo).
// Todo REPETIBLE: semillas fijas y la misma cuenta en los dos motores; el resultado no depende de cuántos
// hilos tenga la PC (los carriles son siempre los mismos, sólo cambia cuántos corren a la vez). El carril 0
// es exactamente lo de antes + compactar, así que nunca da peor que antes. Nada de formas ni reglas fijas:
// todo sale de las máscaras.
// ─────────────────────────────────────────────────────────────────────────────────────────────
export const CARRILES = 16
const CARRILES_HASTA = 120            // piezas: con más, sin carriles (MAPA 732)
const PRESUPUESTO_CARRIL = 800          // colocaciones de pieza por carril: intentos = esto / piezas (2 a 40)
const COMPACTAR_HASTA = 120             // piezas por mesa: con más, la grilla tarda minutos (Copia de 593 banderines: 190 por mesa); queda el contorno (MAPA 732)

/** Cuántos carriles y cuántos intentos por carril (`cfg.optimizar` = `{carriles, intentos}` o `false`). */
export function parametrosOptimizar(n, cfg) {
  const o = cfg ? cfg.optimizar : undefined
  // 🔴 CON MÁS DE 120 PIEZAS, SIN CARRILES (MAPA 732): la Copia de 593 banderines tardaba minutos; ahí rinde
  // la búsqueda de siempre + el contorno real, como antes
  if (o === false || n < 3 || (n > CARRILES_HASTA && !(o && o.carriles))) return { carriles: 1, intentos: 0 }
  const ent = (v, min) => Number.isInteger(v) && v >= min
  const carriles = o && ent(o.carriles, 1) ? o.carriles : CARRILES
  const intentos = o && ent(o.intentos, 0) ? o.intentos : Math.min(40, Math.max(2, Math.floor(PRESUPUESTO_CARRIL / n)))
  return { carriles, intentos }
}

/** El largo de una mesa (pt): hasta donde llega su pieza más baja. */
const altoHoja = (h) => { let m = -Infinity; for (const c of h) { const v = c.cy + c.bh / 2; if (v > m) m = v } return m }
/** El consumo de tela: la suma del largo de cada mesa (en el orden de las mesas, como `sum` de Python). */
export function consumoDe(colocaciones) { let s = 0; for (const h of colocaciones) if (h.length) s += altoHoja(h); return s }

/** Los criterios de colocación que compiten (los mismos en la búsqueda y en los carriles). */
function criterios(piezas, cfg) {
  let estrategias = [...(cfg.estrategias ?? ['bl', 'bandas'])]
  if (piezas.length > 12) estrategias = ['bl']
  // 🔴 el menor hueco compite siempre (MAPA 714, ver Python): gana sólo si deja la mesa más corta
  if (!estrategias.includes('hueco')) estrategias.push('hueco')
  // 🔴 y el mayor contacto (MAPA 719): usa la forma para encastrar; hasta 200 piezas (ver Python)
  if (!estrategias.includes('contacto') && piezas.length <= 200) estrategias.push('contacto')
  return estrategias
}

/** 🔴 GIRAR NO SIEMPRE ACORTA (MAPA 579): si alguna pieza puede ir de costado, también sólo con 0° y 180°. */
function variantesGiro(piezas) {
  const v = [null]
  if (piezas.some((p) => p._candidatos_angulo.some((c) => c.ang % 180 !== 0))) v.push(new Set([0, 180]))
  return v
}

/** Los puntos de partida de la búsqueda, EN ORDEN (giros × órdenes × criterios): gana el primero de menos tela. */
function candidatosBusqueda(piezas, cfg) {
  const idx = piezas.map((_, i) => i)
  const A = idx.map((i) => contar(piezas[i]._mask))
  const Hh = idx.map((i) => piezas[i]._mask.h)
  const Ww = idx.map((i) => piezas[i]._mask.w)
  let base
  // los ÓRDENES (MAPA 708): hasta 200 piezas, los cuatro; con más, por área
  if (piezas.length > 200) base = [ordenDesc(idx, (i) => A[i])]
  else base = [ordenDesc(idx, (i) => A[i]), ordenDesc(idx, (i) => Hh[i]), ordenDesc(idx, (i) => Ww[i]),
               ordenDesc(idx, (i) => Math.max(Hh[i], Ww[i]))]
  const ordenes = [], vistos = new Set()
  for (const o of base) {
    const k = o.join(',')
    if (!vistos.has(k)) { vistos.add(k); ordenes.push(o) }
  }
  const out = []
  for (const soloAng of variantesGiro(piezas)) for (const orden of ordenes) for (const est of criterios(piezas, cfg)) out.push({ orden, est, soloAng })
  return out
}

/** La búsqueda de siempre (MAPA 708 + 714 + 719), en un solo hilo: el mejor de `candidatosBusqueda`. */
function anidarBusqueda(piezas, cfg) {
  if (!piezas || !piezas.length) return { colocaciones: [], area: 0.0, consumo: 0, orden: [], est: 'bl', soloAng: null }
  const prep = preparar(piezas, cfg)
  let mejor = null
  for (const c of candidatosBusqueda(piezas, cfg)) {
    const { colocaciones, area } = anidarEstrategia(piezas, cfg, c.est, c.orden, prep, c.soloAng)
    const consumo = consumoDe(colocaciones)
    if (mejor === null || consumo < mejor.consumo) mejor = { consumo, colocaciones, area, ...c }
  }
  return mejor
}

/**
 * COMPACTAR una mesa (MAPA 728): cada pieza, de la que llega más abajo a la que llega más arriba, prueba
 * subir al lugar libre más alto que tenga (con cualquiera de los giros que permite su regla), con las
 * demás quietas; si lo hay, se muda. Se repite hasta que ninguna se mueve. Como cada mudanza deja la pieza
 * más arriba, la mesa nunca se alarga, y el lugar que deja puede servirle a otra. Gemelo: `_compactar_hoja`.
 */
function compactarHoja(hoja, prep) {
  const { cellPt, anchoC, altoC, espC } = prep
  const h = hoja.map((c) => {
    const k = c.pieza._candidatos_angulo.find((t) => t.ang === c.ang)
    return { c, k, x: Math.floor(c.cx / cellPt + espC - k.mrTest.w / 2 + 0.5), y: Math.floor(c.cy / cellPt + espC - k.mrTest.h / 2 + 0.5) }
  })
  // 🔴 COMO MUCHO 2 PASADAS (MAPA 732): sin tope, una Copia de 593 banderines (116 piezas por mesa) pasaba
  // minutos acá y el pedido quedaba trabado en «Buscando el mejor acomodo»; lo fino lo termina el contorno real
  let cambio = true, pasadas = 0
  while (cambio && pasadas++ < 2) {
    cambio = false
    const orden = h.map((_, i) => i).sort((a, b) => (h[b].y + h[b].k.mrTest.h) - (h[a].y + h[a].k.mrTest.h) || b - a)
    for (const i of orden) {
      const e = h[i]
      const fondo0 = e.y + e.k.mrTest.h
      const G = hojaNueva(altoC, anchoC)
      let sky = 0
      for (let j = 0; j < h.length; j++) {
        if (j === i) continue
        const o = h[j], mt = o.k.mrTest, mc = o.k.mrCol
        estampar(G, o.y + Math.floor((mt.h - mc.h) / 2), o.x + Math.floor((mt.w - mc.w) / 2), mc)
        if (o.y + mt.h > sky) sky = o.y + mt.h
      }
      const ylim = Math.min(altoC, Math.max(sky, fondo0))
      let mejor = null
      for (const k of e.c.pieza._candidatos_angulo) {
        const r = elegirPosicion(G, ylim, k.mrTest, 'bl', null, mejor ? mejor.score[0] : Infinity)
        if (r === null) continue
        if (mejor === null || compararTuplas(r[2], mejor.score) < 0) mejor = { y: r[0], x: r[1], score: r[2], k }
      }
      if (mejor && mejor.y + mejor.k.mrTest.h < fondo0) {
        const ww = mejor.k.mrTest.w, hh = mejor.k.mrTest.h
        const [bw, bh] = bboxGirado(e.c.pieza, mejor.k.ang)
        h[i] = { c: { ...e.c, ang: mejor.k.ang, cx: (mejor.x - espC + ww / 2) * cellPt, cy: (mejor.y - espC + hh / 2) * cellPt, bw, bh },
                 k: mejor.k, x: mejor.x, y: mejor.y }
        cambio = true
      }
    }
  }
  return h.map((e) => e.c)
}

// ─────────────────────────────────────────────────────────────────────────────────────────────
// 🔴 COMPACTAR CON EL CONTORNO REAL (MAPA 731) — gemelo EXACTO de `_compactar_vector` (nesting_contorno.py)
//
// El acomodo trabaja sobre una grilla de 4 mm: cada pieza queda un poco más grande que su contorno y el aire
// entre piezas se redondea para arriba (pedido: 5 mm de espaciado + los dos bordes de corte = 11 mm; medido
// en la tizada del usuario: 16,8 mm de mediana). Al final, cada pieza se DESLIZA con su contorno de verdad
// (los polígonos de `poligonosContorno`, girados igual que la hoja) hacia arriba y hacia la izquierda hasta
// quedar EXACTAMENTE a la distancia pedida de sus vecinas (+ 0,3 mm de holgura). Sólo traslada: no cambia giros
// ni qué pieza va en qué mesa, y nunca alarga. Medido: 20 camisetas 15,06 → 14,85 m; 689 banderines 35,29 →
// 34,42 m. La cuenta: el primer contacto al deslizar es siempre un vértice de una pieza contra un borde de la
// otra (en los dos sentidos); para cada par se calcula dónde entra el vértice en la «cápsula» del borde (el
// segmento engordado la distancia pedida): recta contra dos círculos y una franja, todo cerrado (sin iterar).
// ─────────────────────────────────────────────────────────────────────────────────────────────
const HOLGURA_VECTOR_MM = 0.3
const PASADAS_VECTOR = 6

/** Dónde la recta (x = v si `eje` es 0; y = v si es 1) queda a distancia <= R del segmento ab → [lo, hi] o null. */
function capsula(v, ax, ay, bx, by, R, eje) {
  if (eje === 1) { let t = ax; ax = ay; ay = t; t = bx; bx = by; by = t }
  let lo = Infinity, hi = -Infinity
  let d = v - ax
  if (d <= R && d >= -R) { const h = Math.sqrt(R * R - d * d); if (ay - h < lo) lo = ay - h; if (ay + h > hi) hi = ay + h }
  d = v - bx
  if (d <= R && d >= -R) { const h = Math.sqrt(R * R - d * d); if (by - h < lo) lo = by - h; if (by + h > hi) hi = by + h }
  const sx = bx - ax, sy = by - ay, L = Math.sqrt(sx * sx + sy * sy)
  if (L > 0) {
    const nx = -sy / L, ny = sx / L, dx = sx / L, dy = sy / L
    let a0 = -Infinity, a1 = Infinity
    const c1 = nx * (v - ax)
    if (Math.abs(ny) > 1e-12) {
      let u = ay + (-R - c1) / ny, w = ay + (R - c1) / ny
      if (u > w) { const t = u; u = w; w = t }
      if (u > a0) a0 = u
      if (w < a1) a1 = w
    } else if (Math.abs(c1) > R) a1 = -Infinity
    const c2 = dx * (v - ax)
    if (Math.abs(dy) > 1e-12) {
      let u = ay + (0 - c2) / dy, w = ay + (L - c2) / dy
      if (u > w) { const t = u; u = w; w = t }
      if (u > a0) a0 = u
      if (w < a1) a1 = w
    } else if (c2 < 0 || c2 > L) a1 = -Infinity
    if (a0 <= a1) { if (a0 < lo) lo = a0; if (a1 > hi) hi = a1 }
  }
  return lo <= hi ? [lo, hi] : null
}

/** COMPACTAR UNA MESA CON EL CONTORNO REAL (ver arriba). → la mesa con las piezas deslizadas. */
export function compactarVector(hoja, cfg) {
  if (!hoja.length) return hoja
  const esp = Number(cfg.espaciado_cm ?? 0.5) * CM, holg = HOLGURA_VECTOR_MM / 10 * CM
  const P = hoja.map((c) => {
    const b = c.pieza.base, B = Number(b.B) || 0
    return { c: { ...c }, loc: poligonosContorno(b.cont, b.S, b.x0, b.y0, B), Wp: Number(b.W) + 2 * B, Hp: Number(b.Hp), B, W: null, bb: null }
  })
  // el polígono en la mesa: el mismo giro que la hoja (`matrizColocacion`: antihorario en el PDF, centro de la caja)
  const ubicar = (e) => {
    const co = cosdg(e.c.ang), si = sindg(e.c.ang), cx = e.c.cx, cy = e.c.cy, w2 = e.Wp / 2, h2 = e.Hp / 2
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity
    e.W = e.loc.map((pl) => {
      const out = new Float64Array(pl.length * 2)
      for (let k = 0; k < pl.length; k++) {
        const u = pl[k][0] - w2, v = pl[k][1] - h2
        const X = cx + u * co - v * si, Y = cy - (u * si + v * co)
        out[2 * k] = X; out[2 * k + 1] = Y
        if (X < x0) x0 = X
        if (X > x1) x1 = X
        if (Y < y0) y0 = Y
        if (Y > y1) y1 = Y
      }
      return out
    })
    e.bb = [x0, y0, x1, y1]
  }
  for (const e of P) ubicar(e)
  let Bmax = 0
  for (const e of P) if (e.B > Bmax) Bmax = e.B
  const Rmax = esp + 2 * Bmax + holg
  // vértices de A que avanzan (−t en el eje) contra los bordes de B: el t del primer contacto (o t si no hay)
  const contra = (A, Bw, R, eje, t, signo) => {
    const o = eje, q = 1 - eje                   // o = coordenada de la recta, q = la que avanza
    for (const ra of A) for (let k = 0; k < ra.length; k += 2) {
      const v = ra[k + o], pos = ra[k + q]
      for (const rb of Bw) {
        const n = rb.length >> 1
        for (let s = 0; s < n; s++) {
          const s2 = (s + 1) % n
          const ax = rb[2 * s], ay = rb[2 * s + 1], bx = rb[2 * s2], by = rb[2 * s2 + 1]
          const ea = eje === 0 ? ax : ay, eb = eje === 0 ? bx : by
          if (v < (ea < eb ? ea : eb) - R || v > (ea < eb ? eb : ea) + R) continue
          const iv = capsula(v, ax, ay, bx, by, R, eje)
          if (iv === null) continue
          if (signo > 0) {                          // A avanza hacia valores menores
            if (iv[1] <= pos + 1e-9) { const d = pos - iv[1]; if (d < t) t = d } else if (iv[0] < pos) return 0
          } else {                                  // A (los vértices de la otra pieza) avanza hacia mayores
            if (iv[0] >= pos - 1e-9) { const d = iv[0] - pos; if (d < t) t = d } else if (iv[1] > pos) return 0
          }
          if (t <= 0) return 0
        }
      }
    }
    return t
  }
  // cuánto se puede mover la pieza i: eje 0 = hacia arriba, eje 1 = hacia la izquierda
  const deslizar = (i, eje) => {
    const e = P[i], bi = e.bb
    // el tope: la caja de la pieza no sale de la mesa (los márgenes ya están afuera de cx/cy)
    let t = eje === 0 ? e.c.cy - e.c.bh / 2 : e.c.cx - e.c.bw / 2
    if (t <= 1e-9) return 0
    const lo = eje === 0 ? 0 : 1, hi = eje === 0 ? 2 : 3, a0 = eje === 0 ? 1 : 0, a1 = eje === 0 ? 3 : 2
    const cands = []
    for (let j = 0; j < P.length; j++) {
      if (j === i) continue
      const bj = P[j].bb
      if (bj[lo] > bi[hi] + Rmax || bj[hi] < bi[lo] - Rmax || bj[a0] >= bi[a1]) continue
      cands.push(j)
    }
    // de la más cercana a la más lejana: en cuanto una ya no alcanza, las que siguen tampoco
    cands.sort((x, y) => P[y].bb[a1] - P[x].bb[a1] || x - y)
    for (const j of cands) {
      const ej = P[j]
      const R = esp + e.B + ej.B + holg
      if (ej.bb[a1] < bi[a0] - t - R) break
      t = contra(e.W, ej.W, R, eje, t, 1)
      if (t <= 0) return 0
      t = contra(ej.W, e.W, R, eje, t, -1)
      if (t <= 0) return 0
    }
    return t
  }
  for (let ps = 0; ps < PASADAS_VECTOR; ps++) {
    let movio = false
    for (const eje of [0, 1, 0]) {
      const k = eje === 0 ? 1 : 0
      const orden = P.map((_, i) => i).sort((x, y) => P[x].bb[k] - P[y].bb[k] || x - y)
      for (const i of orden) {
        const t = deslizar(i, eje)
        if (t > 1e-6) {
          if (eje === 0) P[i].c.cy -= t
          else P[i].c.cx -= t
          ubicar(P[i])
          movio = true
        }
      }
    }
    if (!movio) break
  }
  return P.map((e) => e.c)
}

/** El final de cada carril: la última mesa sola (MAPA 726) y compactar cada mesa. Nunca alarga. */
function pulir(cfg, colocaciones, prep) {
  let col = colocaciones
  const llenas = []
  col.forEach((h, i) => { if (h.length) llenas.push(i) })
  if (llenas.length >= 2) {
    // 🔴 LA ÚLTIMA MESA SE VUELVE A ACOMODAR SOLA (MAPA 726): sus piezas son las que quedaron al final; con la
    // búsqueda completa entre ellas suelen ocupar menos. Sólo si queda en UNA mesa y más corta.
    const ult = llenas[llenas.length - 1]
    const h2 = anidarBusqueda(col[ult].map((c) => c.pieza), cfg).colocaciones.filter((h) => h.length)
    if (h2.length === 1 && altoHoja(h2[0]) < altoHoja(col[ult]) - 1e-6) { col = col.slice(); col[ult] = h2[0] }
  }
  return col.map((h) => (h.length && h.length <= COMPACTAR_HASTA ? compactarHoja(h, prep) : h))
}

/**
 * UN CARRIL del optimizador (MAPA 728) — gemelo EXACTO de `_carril`. `inicio` = el mejor punto de la
 * búsqueda (`{orden, est, soloAng}`). Carril 0: ese mismo acomodo, pulido (lo de antes). Carril 1: busca
 * desde ahí. Los demás: desde un orden MEZCLADO (el área de cada pieza con ruido, por la semilla del carril).
 * Cada intento: un orden nuevo mezclado (1 de 4) o el mejor con 1 a 3 cambios (dos piezas de lugar o una
 * movida), a veces otro criterio; queda si usa menos tela (o igual y deja menos pieza en la última mesa).
 * → `{colocaciones, consumo}`.
 */
export function carril(piezas, cfg, k, inicio) {
  const prep = preparar(piezas, cfg)
  const n = piezas.length
  const saIni = inicio.soloAng ? new Set(inicio.soloAng) : null
  if (k === 0) {
    const { colocaciones } = anidarEstrategia(piezas, cfg, inicio.est, inicio.orden, prep, saIni)
    const col = pulir(cfg, colocaciones, prep)
    return { colocaciones: col, consumo: consumoDe(col) }
  }
  const { intentos } = parametrosOptimizar(n, cfg)
  const A = piezas.map((p) => contar(p._mask))
  const ests = criterios(piezas, cfg), vars = variantesGiro(piezas)
  let st = k * 7919 + 17                            // la semilla del carril: fija, el resultado se repite
  const u = () => { st = (Math.imul(st, 1103515245) + 12345) & 0x7fffffff; return st / 2147483648 }
  const mezclado = () => {
    const r = 0.2 + 0.6 * u()
    const clave = A.map((a) => a * (1 + r * (u() - 0.5)))
    return ordenDesc(piezas.map((_, i) => i), (i) => clave[i])
  }
  const areaUlt = (col) => {
    const ll = col.filter((h) => h.length)
    if (ll.length < 2) return 0
    let s = 0
    for (const c of ll[ll.length - 1]) s += contar(c.pieza._mask)
    return s
  }
  let mejor = null
  const probar = (orden, est, sa) => {
    const { colocaciones } = anidarEstrategia(piezas, cfg, est, orden, prep, sa)
    const c = consumoDe(colocaciones), a = areaUlt(colocaciones)
    if (mejor === null || c < mejor.c - 1e-9 || (Math.abs(c - mejor.c) <= 1e-9 && a <= mejor.a)) mejor = { c, a, colocaciones, orden, est, sa }
  }
  if (k === 1) probar(inicio.orden, inicio.est, saIni)
  else probar(mezclado(), ests[k % ests.length], vars[k % vars.length])
  for (let t = 0; t < intentos; t++) {
    let o, est = mejor.est
    if (u() < 0.25) {
      o = mezclado()
      est = ests[Math.floor(u() * ests.length)]
    } else {
      o = mejor.orden.slice()
      const m = 1 + Math.floor(u() * 3)
      for (let q = 0; q < m; q++) {
        const i = Math.floor(u() * n), j = Math.floor(u() * n)
        if (u() < 0.5) { const x = o[i]; o[i] = o[j]; o[j] = x } else { const [x] = o.splice(i, 1); o.splice(j, 0, x) }
      }
      if (u() < 0.15) est = ests[Math.floor(u() * ests.length)]
    }
    probar(o, est, mejor.sa)
  }
  const col = pulir(cfg, mejor.colocaciones, prep)
  return { colocaciones: col, consumo: consumoDe(col) }
}

/** Para mandar un punto de partida a otro hilo (el Set de giros viaja como lista). */
const inicioSerial = (c) => ({ orden: c.orden, est: c.est, soloAng: c.soloAng ? [...c.soloAng] : null })

/**
 * `anidar_contorno` (MAPA 708 + 714 + 719 + 726 + 728): LA TIZADA MÁS EFICIENTE → `{colocaciones, area,
 * consumo}`. `colocaciones` = mesas, cada una `[{pieza, ang, cx, cy, bw, bh}, ...]`. Con `ejecutor`
 * (`nesting/carriles.js`) la búsqueda y los carriles corren en varios hilos; sin él, acá mismo y en orden:
 * el resultado es EL MISMO (gemelo EXACTO de `anidar_contorno` de Python).
 */
export async function anidarContorno(piezas, cfg, ejecutor = null) {
  if (!piezas || !piezas.length) return { colocaciones: [], area: 0.0 }
  const prep = preparar(piezas, cfg)
  let celdas = 0
  for (const p of piezas) celdas += contar(p._mask)
  const kk = prep.cellPt / CM
  const area = celdas * (kk * kk)
  const { carriles } = parametrosOptimizar(piezas.length, cfg)
  let inicio
  if (ejecutor) {
    const cands = candidatosBusqueda(piezas, cfg)
    const rs = await ejecutor(piezas, cfg, cands.map((c) => ({ tipo: 'estrategia', ...inicioSerial(c) })))
    let b = 0
    for (let i = 1; i < rs.length; i++) if (rs[i].consumo < rs[b].consumo) b = i
    inicio = cands[b]
  } else inicio = anidarBusqueda(piezas, cfg)
  const tareas = []
  for (let k = 0; k < carriles; k++) tareas.push({ tipo: 'carril', k, inicio: inicioSerial(inicio) })
  let res
  if (ejecutor && carriles > 1) {
    res = (await ejecutor(piezas, cfg, tareas)).map((r) => ({
      consumo: r.consumo, colocaciones: r.hojas.map((h) => h.map((c) => ({ pieza: piezas[c.i], ang: c.ang, cx: c.cx, cy: c.cy, bw: c.bw, bh: c.bh }))) }))
  } else res = tareas.map((t) => carril(piezas, cfg, t.k, t.inicio))
  let b = 0
  for (let i = 1; i < res.length; i++) if (res[i].consumo < res[b].consumo) b = i
  // 🔴 y al final, con el CONTORNO REAL (MAPA 731): cada pieza a la distancia exacta de sus vecinas
  const colocaciones = res[b].colocaciones.map((h) => (h.length ? compactarVector(h, cfg) : h))
  return { colocaciones, area, consumo: consumoDe(colocaciones) }
}

/** Lo que hace un hilo de carriles con una tarea (`nesting/carril.worker.js`). → algo que se puede mandar. */
export function tareaCarril(piezas, cfg, t) {
  if (t.tipo === 'estrategia') {
    const prep = preparar(piezas, cfg)
    const { colocaciones } = anidarEstrategia(piezas, cfg, t.est, t.orden, prep, t.soloAng ? new Set(t.soloAng) : null)
    return { consumo: consumoDe(colocaciones) }
  }
  const pos = new Map(piezas.map((p, i) => [p, i]))
  const r = carril(piezas, cfg, t.k, t.inicio)
  return { consumo: r.consumo, hojas: r.colocaciones.map((h) => h.map((c) => ({ i: pos.get(c.pieza), ang: c.ang, cx: c.cx, cy: c.cy, bw: c.bw, bh: c.bh }))) }
}

// cada copia sabe su número y qué pieza de la fila es (`_copia_i`, `_pieza_i`): la Copia mezclada (MAPA 717)
const copiasDe = (fila, k) => { const out = []; for (let i = 0; i < k; i++) fila.forEach((p, j) => out.push({ ...p, _copia_i: i, _pieza_i: j })); return out }

/** El área de las piezas de una hoja (cm²), con la misma cuenta que el acomodo — gemelo de `_area_hoja`. */
function areaHoja(hoja, cellPt) {
  let n = 0
  for (const c of hoja) n += contar(c.pieza._mask)
  const k = cellPt / CM
  return n * (k * k)
}

/**
 * COPIA: LA MESA LLENA QUE SE REPITE (MAPA 720) — gemelo EXACTO de `repartir_copias` (nesting_contorno.py),
 * ver ahí el porqué. Las copias que llenan una mesa del largo máximo, acomodadas como siempre; la primera
 * mesa (con sus copias completas) se imprime `copias // n` veces y el resto va en su mesa.
 * → `[[colocaciones, {copias, por_mesa}, area]]` o null.
 */
export async function repartirCopias(fila, copias, cfg, hoja1 = null, area1 = null, ejecutor = null) {
  if (!fila || !fila.length || copias < 2) return null
  const { cellPt, anchoC, altoC } = preparar(fila, cfg)
  let celdas = 0
  for (const p of fila) celdas += contar(p._mask)
  celdas = celdas || 1
  const k = Math.min(copias, Math.floor((altoC * anchoC) / celdas) + 1)
  const hojas = (await anidarContorno(copiasDe(fila, k), cfg, ejecutor)).colocaciones.filter((h) => h.length)
  if (!hojas.length) return null
  if (hojas.length === 1 && k === copias) return [[hojas[0], { copias: 1, por_mesa: copias }, areaHoja(hojas[0], cellPt)]]
  const per = fila.length
  const cuenta = new Map()
  for (const c of hojas[0]) { const ci = c.pieza._copia_i ?? 0; cuenta.set(ci, (cuenta.get(ci) || 0) + 1) }
  const enteras = [...cuenta.entries()].filter(([, v]) => v === per).map(([ci]) => ci).sort((a, b) => a - b)
  const n = enteras.length
  if (n === 0) return null
  const nuevo = new Map(enteras.map((ci, i) => [ci, i]))
  // la mesa llena con sus copias numeradas 0…n-1 (la Copia mezclada reparte esos lugares, MAPA 717)
  const lleno = hojas[0].filter((c) => nuevo.has(c.pieza._copia_i ?? 0))
    .map((c) => ({ ...c, pieza: { ...c.pieza, _copia_i: nuevo.get(c.pieza._copia_i ?? 0) } }))
  const llenas = Math.floor(copias / n), resto = copias % n
  const res = [[lleno, { copias: llenas, por_mesa: n }, areaHoja(lleno, cellPt)]]
  if (resto) {
    for (const h of (await anidarContorno(copiasDe(fila, resto), cfg, ejecutor)).colocaciones) {
      if (h.length) res.push([h, { copias: 1, por_mesa: Math.max(1, Math.floor(h.length / per)) }, areaHoja(h, cellPt)])
    }
  }
  return res
}

// LA BANDA ENTRE TALLES SEPARADOS (MAPA 711): rótulo 7 mm + 3 mm + línea 1,2 mm + 3 mm + rótulo, además
// del espaciado. Gemelo: `SEP_BANDA_MM` (nesting_contorno.py).
const SEP_BANDA_MM = 2 * (7.0 + 3.0) + 1.2

/** `_firma_geo` (MAPA 717) — gemelo EXACTO: la geometría con la que se arma la máscara; null = no se mezcla. */
function firmaGeo(p) {
  const b = p.base && typeof p.base === 'object' ? p.base : null
  const c = b ? b.cont : null
  if (!c || typeof c !== 'object' || !c.segmentos || !c.segmentos.length) return null
  return JSON.stringify([Number(p.w), Number(p.h), String(p.rotacion || ''), Number(p.borde_cm || 0),
    ['S', 'x0', 'y0', 'B', 'W', 'Hp'].map((k) => Number(b[k] || 0)),
    c.segmentos.map((s) => s.map((x) => (typeof x === 'string' ? x : Number(x))))])
}

/** `_patron` (MAPA 717) — gemelo EXACTO: cuántas de cada fila en una mesa de `n` lugares, en proporción. */
function patronCopia(resto, n) {
  const tot = resto.reduce((a, b) => a + b, 0)
  const p = resto.map((r) => Math.floor(n * r / tot))
  let falta = n - p.reduce((a, b) => a + b, 0)
  const orden = resto.map((_, i) => i).sort((a, b) => ((n * resto[b]) % tot) - ((n * resto[a]) % tot) || a - b)
  for (const i of orden) {
    if (falta <= 0) break
    if (p[i] < resto[i]) { p[i]++; falta-- }
  }
  return p
}

/** `_info_copia` (MAPA 717) — gemelo EXACTO. */
function infoCopia(filas, cuenta, copias) {
  const nro = (i) => (filas[i][0] >= 0 ? filas[i][0] + 1 : null)
  const fs = [...cuenta.keys()].sort((a, b) => a - b)
  const nMesa = fs.reduce((t, i) => t + cuenta.get(i).size, 0)
  if (fs.length === 1) return { fila: nro(fs[0]), copias, por_mesa: nMesa }
  return { fila: null, filas: fs.map((i) => ({ fila: nro(i), por_mesa: cuenta.get(i).size })), copias, por_mesa: nMesa }
}

/** `_copia_llenas` (MAPA 720 + 725) — gemelo EXACTO, ver nesting_contorno.py. → `[mesas, sobra]`. */
async function copiaLlenas(filas, cfg, ejecutor = null) {
  let resto = filas.map((f) => f[2])
  const total = resto.reduce((a, b) => a + b, 0)
  if (total < 2) return [[], resto]
  // si todas juntas no ocupan ni MEDIA mesa (por la CAJA de cada pieza), no llenan una (ver Python)
  const m = cfg.margenes_cm
  const supMesa = (Number(cfg.ancho_cm) - m.izq - m.der) * (Number(cfg.altura_max_cm || 500) - m.sup - m.inf) * CM * CM
  let caja = 0
  for (const p of filas[0][1]) caja += Number(p.w) * Number(p.h)
  if (2 * total * caja <= supMesa) return [[], resto]
  const rep = await repartirCopias(filas[0][1], total, cfg, null, null, ejecutor)
  if (!rep || (rep.length === 1 && rep[0][1].copias === 1 && rep[0][1].por_mesa === total)) return [[], resto]
  const n = rep[0][1].por_mesa                   // `repartirCopias` pone primero la mesa llena (n <= total)
  const lleno = rep[0][0], aLleno = rep[0][2]
  const res = []
  while (resto.reduce((a, b) => a + b, 0) >= n) {
    const p = patronCopia(resto, n)
    let k = Infinity
    for (let i = 0; i < p.length; i++) if (p[i] > 0) k = Math.min(k, Math.floor(resto[i] / p[i]))
    const filaDeCopia = []
    for (let i = 0; i < p.length; i++) for (let v = 0; v < p[i]; v++) filaDeCopia.push(i)
    const out = [], cuenta = new Map()
    for (const c of lleno) {
      const ci = c.pieza._copia_i ?? 0
      const fi = filaDeCopia[ci]
      out.push({ ...c, pieza: { ...filas[fi][1][c.pieza._pieza_i ?? 0] } })
      if (!cuenta.has(fi)) cuenta.set(fi, new Set())
      cuenta.get(fi).add(ci)
    }
    res.push([out, infoCopia(filas, cuenta, k), aLleno])
    resto = resto.map((r, i) => r - k * p[i])
  }
  return [res, resto]
}

/** `_copia_por_filas` (MAPA 725) — gemelo EXACTO: las mesas llenas que se repiten aparte; TODO lo demás JUNTO
 * (talles mezclados; un pozo por diseño sólo con «Separar»). → `{colocaciones, area, consumo, mesas}`. */
async function copiaPorFilas(piezas, cfg, sepDis, nombreDis, ejecutor = null) {
  const grupos = new Map()
  for (const p of piezas) {
    const k = Number.isInteger(p._fila) ? p._fila : -1
    if (!grupos.has(k)) grupos.set(k, [])
    grupos.get(k).push(p)
  }
  const familias = []
  for (const k of [...grupos.keys()].sort((a, b) => a - b)) {
    const g = grupos.get(k)
    const dk = sepDis ? String(g[0]._diseno || '') : ''
    const fg = g.map(firmaGeo)
    if (k >= 0 && !fg.includes(null)) {
      const firma = JSON.stringify(fg)
      const fam = familias.find((f) => f.firma === firma && f.dis === dk)
      if (fam) { fam.filas.push(k); continue }
      familias.push({ firma, dis: dk, filas: [k] })
    } else familias.push({ firma: null, dis: dk, filas: [k] })
  }
  const colocaciones = [], mesas = []
  let area = 0, consumo = 0
  const altoDe = (h) => { let mx = -Infinity; for (const c of h) mx = Math.max(mx, c.cy + c.bh / 2); return mx }
  const sobraDe = new Map(), disDe = new Map()   // fila → copias que no llenan una mesa · fila → su pozo
  for (const fam of familias) {
    const filas = fam.filas.map((k) => [k, grupos.get(k), k >= 0 ? Math.max(1, Math.trunc(Number(grupos.get(k)[0]._copias) || 1)) : 1])
    const [llenas, sobra] = fam.filas[0] >= 0 ? await copiaLlenas(filas, cfg, ejecutor) : [[], filas.map((f) => f[2])]
    const dis = sepDis ? { diseno: nombreDis.get(fam.dis) } : {}
    for (const [h, info, a] of llenas) {
      colocaciones.push(h); mesas.push({ ...info, ...dis })
      area += a
      consumo += altoDe(h)
    }
    filas.forEach(([k], i) => { sobraDe.set(k, sobra[i]); disDe.set(k, fam.dis) })
  }
  // el pozo en el ORDEN DE LAS FILAS (ver Python); uno por diseño con «Separar»
  const pozo = new Map(), ordenPozo = []
  for (const k of [...grupos.keys()].sort((a, b) => a - b)) {
    const dk = disDe.get(k) ?? ''
    if (!pozo.has(dk)) { pozo.set(dk, []); ordenPozo.push(dk) }
    for (let inst = 0; inst < (sobraDe.get(k) || 0); inst++) grupos.get(k).forEach((p, j) => pozo.get(dk).push({ ...p, _copia_i: inst, _pieza_i: j }))
  }
  for (const dk of ordenPozo) {
    const pz = pozo.get(dk)
    if (!pz.length) continue
    const r = await anidarContorno(pz, cfg, ejecutor)
    const { cellPt } = preparar(pz, cfg)
    const dis = sepDis ? { diseno: nombreDis.get(dk) } : {}
    for (const h of r.colocaciones) {
      if (!h.length) continue
      const cuenta = new Map()
      for (const c of h) {
        const f = Number.isInteger(c.pieza._fila) ? c.pieza._fila : -1
        if (!cuenta.has(f)) cuenta.set(f, new Set())
        cuenta.get(f).add(c.pieza._copia_i ?? 0)
      }
      const fs = [...cuenta.keys()].sort((a, b) => a - b)
      const nro = (f) => (f >= 0 ? f + 1 : null)
      const nMesa = fs.reduce((t, f) => t + cuenta.get(f).size, 0)
      const info = fs.length === 1 ? { fila: nro(fs[0]), copias: 1, por_mesa: nMesa }
        : { fila: null, filas: fs.map((f) => ({ fila: nro(f), por_mesa: cuenta.get(f).size })), copias: 1, por_mesa: nMesa }
      colocaciones.push(h); mesas.push({ ...info, ...dis })
      area += areaHoja(h, cellPt)
      consumo += altoDe(h)
    }
  }
  return { colocaciones, area, consumo, mesas }
}

/**
 * `anidar_por_fila` — COPIA (MAPA 581/720/725: `copiaPorFilas`), TALLES POR MESA (593/710) y
 * SEPARAR DISEÑOS (717). Gemelo EXACTO de nesting_contorno.py.
 */
export async function anidarPorFila(piezas, cfg, ejecutor = null) {
  const porFila = !!(cfg && cfg.por_fila)
  const porTalles = !porFila && !!(cfg && cfg.por_talles_mesa)
  const sepDis = !!(cfg && cfg.separar_disenos)
  if (!porFila && !porTalles && !sepDis) return { ...(await anidarContorno(piezas, cfg, ejecutor)), mesas: null }
  const RESTO = 1e9                                   // los talles sin grupo: juntos y AL FINAL
  const DIS = 1e10                                    // el diseño va primero en la clave (separar diseños)
  const ordenDis = new Map(), nombreDis = new Map()
  for (const p of piezas) {
    const d = String(p._diseno || '')
    if (!ordenDis.has(d)) { ordenDis.set(d, ordenDis.size); nombreDis.set(d, String(p._diseno_nombre || p._diseno || '') || null) }
  }
  if (porFila) return copiaPorFilas(piezas, cfg, sepDis, nombreDis, ejecutor)
  const grupos = new Map()
  for (const p of piezas) {
    let k
    if (porTalles) k = Number.isInteger(p._grupo_mesa) && p._grupo_mesa >= 1 ? p._grupo_mesa : RESTO
    else k = 0
    if (sepDis) k = ordenDis.get(String(p._diseno || '')) * DIS + k
    if (!grupos.has(k)) grupos.set(k, [])
    grupos.get(k).push(p)
  }
  const colocaciones = [], mesas = []
  let area = 0, consumo = 0
  const altoDe = (h) => { let mx = -Infinity; for (const c of h) mx = Math.max(mx, c.cy + c.bh / 2); return mx }
  // TALLES SEPARADOS EN LA MISMA MESA (MAPA 710): cada grupo solo y los bloques apilados con una línea
  // punteada entre medio (ver `anidar_por_fila` de Python)
  const separados = porTalles && cfg.talles_mesa_modo === 'separados'
  const bloques = []
  const disDe = (g) => (sepDis ? nombreDis.get(String(g[0]._diseno || '')) : null)
  const claves = [...grupos.keys()].sort((a, b) => a - b)
  for (const k of claves) {
    const g = grupos.get(k)
    const r = await anidarContorno(g, cfg, ejecutor)
    // los talles de la mesa, en el orden en que llegan las piezas (el de la planilla)
    const tl = porTalles ? [...new Set(g.filter((x) => x.talle != null && x.talle !== '').map((x) => String(x.talle)))] : null
    const noVacias = r.colocaciones.filter((h) => h.length)
    const dx = sepDis ? { diseno: disDe(g) } : {}
    for (const h of noVacias) {
      if (separados) { bloques.push([h, [...tl], disDe(g)]); continue }
      colocaciones.push(h)
      if (porTalles) {
        const gk = sepDis ? k % DIS : k
        mesas.push({ grupo: gk !== RESTO ? gk : null, talles: [...tl], ...dx })
      } else mesas.push({ ...dx })
    }
    area += r.area
    if (!separados) consumo += r.consumo || 0
  }
  if (separados) {
    const m = cfg.margenes_cm
    const altoMax = (Number(cfg.altura_max_cm || 500) - m.sup - m.inf) * CM
    const esp = Number(cfg.espaciado_cm ?? 0.5) * CM
    const banda = SEP_BANDA_MM * CM / 10
    let actual = null, previos = []
    for (const [h, tl, dis] of bloques) {
      const hh = altoDe(h)
      // entre bloque y bloque: el espaciado + la banda de la línea con sus rótulos (MAPA 711); separando
      // diseños, otro diseño arranca otra mesa (MAPA 717)
      if (actual === null || (actual.h.length && actual.y + banda + hh > altoMax + 1e-6) || actual.dis !== dis) {
        if (actual !== null) consumo += actual.y - esp
        actual = { h: [], y: 0.0, talles: [], cortes: [], dis }
        colocaciones.push(actual.h)
        mesas.push(actual)
      } else if (actual.h.length) {
        actual.cortes.push({ y: actual.y - esp / 2 + banda / 2, arriba: [...previos], abajo: [...tl] })
        actual.y += banda
      }
      for (const c of h) actual.h.push({ ...c, cy: c.cy + actual.y })
      for (const t of tl) if (!actual.talles.includes(t)) actual.talles.push(t)
      actual.y += hh + esp
      previos = tl
    }
    if (actual !== null) consumo += actual.y - esp
    for (let i = 0; i < mesas.length; i++) {
      mesas[i] = { grupo: null, talles: mesas[i].talles, separados: true, cortes: mesas[i].cortes, ...(sepDis ? { diseno: mesas[i].dis } : {}) }
    }
  }
  return { colocaciones, area, consumo, mesas }
}

function bboxGirado(p, ang) {
  const th = ang * (Math.PI / 180)                      // math.radians
  return [Math.abs(p.w * Math.cos(th)) + Math.abs(p.h * Math.sin(th)),
          Math.abs(p.w * Math.sin(th)) + Math.abs(p.h * Math.cos(th))]
}

/** `_anidar_estrategia(piezas, cfg, estrategia, orden, prep, soloAng)` → `{colocaciones, area}`.
 * `soloAng` (Set o null): sólo esos ángulos (si a una pieza no le queda ninguno, los suyos). */
export function anidarEstrategia(piezas, cfg, estrategia, orden, prep, soloAng = null) {
  const { cellPt, anchoC, altoC, espC, paso } = prep
  const candsDe = (p) => {
    const c = p._candidatos_angulo
    if (!soloAng) return c
    const f = c.filter((k) => soloAng.has(k.ang))
    return f.length ? f : c
  }
  const hojasG = [], hojasSky = [], colocaciones = []
  const nuevaHoja = () => {
    hojasG.push(hojaNueva(altoC, anchoC)); hojasSky.push(0); colocaciones.push([])
    return hojasG.length - 1
  }
  nuevaHoja()
  let areaC2 = 0
  Object.assign(DEBUG, { bloque: 0, fft: 0, sin_geo: 0, sin_ultimo: 0, sin_lugar: 0 })

  const colocar = (h, p, ang, y, x, mrCol, mrTest) => {
    const hh = mrTest.h, ww = mrTest.w
    const dy = Math.floor((hh - mrCol.h) / 2), dx = Math.floor((ww - mrCol.w) / 2)
    estampar(hojasG[h], y + dy, x + dx, mrCol)
    const { b, cols } = perfilInferior(mrCol), prof = hojasG[h].prof
    for (let k = 0; k < cols.length; k++) { const j = cols[k], v = y + dy + b[j]; if (v > prof[x + dx + j]) prof[x + dx + j] = v }
    hojasSky[h] = Math.max(hojasSky[h], y + hh)
    const [bw, bh] = bboxGirado(p, ang)
    colocaciones[h].push({ pieza: p, ang, cx: (x - espC + ww / 2) * cellPt, cy: (y - espC + hh / 2) * cellPt, bw, bh })   // la grilla empieza `espC` antes de la mesa
    areaC2 += contar(p._mask)
  }

  for (const i of orden) {
    const p = piezas[i]
    const candidatosPorAngulo = candsDe(p)
    // con el largo de mesa del pedido (MAPA 716) esto pasa cuando el largo elegido es más corto que la pieza
    if (!candidatosPorAngulo.length) throw new Error(`«${p.pieza || p.etiqueta}» (talle ${p.talle || '-'}) no entra en una mesa de ` +
      `${Number(cfg.ancho_cm)} cm de ancho × ${Number(cfg.altura_max_cm) / 100} m de largo con el giro que tiene permitido: ` +
      'hace falta una tela más ancha o un largo de mesa mayor.')
    let colocada = false
    DEBUG.fft++
    // 🔴 LOS GIROS QUE PERMITE SU REGLA, EN TODAS LAS POSICIONES (MAPA 708): ni el giro ni el lugar
    // de la pieza anterior igual. Gana el lugar más abajo y más a la izquierda; cada pieza con SU mejor
    // giro. Giro LIBRE: en dos pasos (múltiplos de 90° y después los vecinos del mejor), ver Python.
    let fases = [candidatosPorAngulo]
    if (p.rotacion === 'libre' && candidatosPorAngulo.length > 8) {
      const grueso = candidatosPorAngulo.filter((c) => c.ang % 90 === 0)
      fases = [grueso.length ? grueso : candidatosPorAngulo.slice(0, 4), null]     // null = los vecinos del mejor
    }
    for (let hIdx = 0; hIdx < hojasG.length; hIdx++) {
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
          let hueco = null
          if (estrategia === 'hueco') {
            const { b, cols } = perfilInferior(mrCol)
            hueco = { b, cols, dy: Math.floor((hh - mrCol.h) / 2), dx: Math.floor((mrTest.w - mrCol.w) / 2) }
          } else if (estrategia === 'contacto') hueco = { sky }
          // el corte exacto (MAPA 715): con «bl» y «hueco» el fondo es lo primero que decide; con «contacto»
          // (MAPA 719) el valor (score[0] = -valor): pasa como el mínimo que tiene que alcanzar
          const tope = mejor === null || estrategia === 'bandas' ? (estrategia === 'contacto' ? -Infinity : Infinity)
            : estrategia === 'contacto' ? -mejor.score[0] : mejor.score[0]
          const r = elegirPosicion(G, ylim, mrTest, estrategia, hueco, tope)
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
