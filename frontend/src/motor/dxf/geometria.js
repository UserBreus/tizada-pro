// LA GEOMETRÍA DE ezdxf QUE USA `importar_dxf.py`, OPERACIÓN POR OPERACIÓN — PLAN_NAVEGADOR.md,
// etapa 1, punto 7 (`dxf.js: importar_dxf`).
//
// `importar_dxf.py` no dibuja el DXF: le pide a ezdxf (`ezdxf.path.make_path`) que convierta cada
// entidad en un trazado de rectas y Bézier cúbicas, y lo que sale de ahí va DERECHO al PDF. Para que
// el navegador escriba los MISMOS números que el servidor hay que hacer las mismas cuentas en el mismo
// orden: ezdxf 1.4.4 corre con sus extensiones en C (`ezdxf.acc`: Vec3, Bezier4P, Basis, Matrix44),
// así que lo que está acá es la traducción de esos `.pyx`, no de la versión Python pura (que en algún
// caso opera distinto). Cada función lleva el nombre de la de ezdxf.
//
// Lo que importa y no se ve:
//   · `Vec3.isclose` compara COMPONENTE por componente con rel 1e-9 y abs 1e-12 (no la distancia);
//   · un arco (bulge) se convierte con `bulge_to_arc` (Lee Mac) → `ConstructionEllipse.from_arc`
//     (pasando por GRADOS y volviendo a radianes: ese ida y vuelta se reproduce, cambia bits) →
//     `cubic_bezier_arc_parameters` (cuartos de vuelta, tangente 4/3·tan(θ/4)) y se DA VUELTA si
//     el primer punto de control cayó en el vértice final;
//   · una SPLINE cúbica, no racional y sujeta («clamped») se descompone EXACTA en Bézier (NURBS Book
//     A5.6); cualquier otra se APROXIMA: puntos sobre la curva (parámetros por cuerda, subdivididos
//     3 veces) e interpolación cúbica con un sistema tridiagonal;
//   · el principio del trazado de una SPLINE es `spline.point(0)` evaluado con las funciones base:
//     puede caer a un bit del primer punto de control, y ese bit es el que se escribe;
//   · `Path.close()` y `is_closed` usan `isclose` del principio contra el final.
//
// Los vectores son arreglos [x, y, z]; una Bézier es [p0, p1, p2, p3].
import { pyRound, pySum } from '../py.js'

export const ABS_TOL = 1e-12
export const REL_TOL = 1e-9
export const TAU = 6.283185307179586
const X_AXIS = [1, 0, 0], Y_AXIS = [0, 1, 0], Z_AXIS = [0, 0, 1], NULLVEC = [0, 0, 0]

// ─── lo mismo que `ezdxf.acc.vector` (Cython) ────────────────────────────────────────────────
/** `isclose(a, b, rel_tol, abs_tol)` de vector.pyx ("tiene que coincidir con la de Python"). */
export function isclose(a, b, rel = REL_TOL, abs = ABS_TOL) {
  const diff = Math.abs(b - a)
  return diff <= Math.abs(rel * b) || diff <= Math.abs(rel * a) || diff <= abs
}
/** `math.isclose` de Python: rel 1e-9, abs 0 salvo que se pida. */
export function mathIsclose(a, b, rel = 1e-9, abs = 0.0) {
  if (a === b) return true
  const diff = Math.abs(b - a)
  return diff <= Math.abs(rel * b) || diff <= Math.abs(rel * a) || diff <= abs
}
export const Vec3 = (x = 0, y = 0, z = 0) => [x, y, z]
export const v3isclose = (a, b, rel = REL_TOL, abs = ABS_TOL) =>
  isclose(a[0], b[0], rel, abs) && isclose(a[1], b[1], rel, abs) && isclose(a[2], b[2], rel, abs)
export const v3add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]]
export const v3sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
export const v3mul = (a, f) => [a[0] * f, a[1] * f, a[2] * f]
export const v3cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
export const v3magnitude = (a) => Math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])
export const v3magnitudeSqr = (a) => a[0] * a[0] + a[1] * a[1] + a[2] * a[2]
export function v3normalize(a, length = 1.0) {
  const factor = length / v3magnitude(a)
  return [a[0] * factor, a[1] * factor, a[2] * factor]
}
export function v3dist(a, b) {
  const dx = a[0] - b[0], dy = a[1] - b[1], dz = a[2] - b[2]
  return Math.sqrt(dx * dx + dy * dy + dz * dz)
}
/** `Vec3.from_angle` / `Vec2.from_angle`: (cos·l, sin·l). */
export const fromAngle = (angle, length = 1.0) => [Math.cos(angle) * length, Math.sin(angle) * length, 0]
/** `(a % math.tau)` de Python (y `normalize_rad_angle` de C): siempre en [0, τ). */
export function pyModTau(a) {
  let r = a % TAU
  if (r < 0) r += TAU
  return r === 0 ? 0 : r
}
// `v2_dist` es el `hypot` de C (no el de Python): en JS queda `Math.hypot`. Ver la nota de
// `importar.js` sobre lo que difiere en el último bit entre libm de Windows y V8.
const v2dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1])
const v2angle = (p1, p2) => Math.atan2(p2[1] - p1[1], p2[0] - p1[0])

// ─── `ezdxf.path.Path` (lo que usa importar_dxf) ────────────────────────────────────────────
export const MOVE_TO = 1, LINE_TO = 2, CURVE3_TO = 3, CURVE4_TO = 4
export class Path {
  constructor(start = NULLVEC) {
    this._vertices = [Vec3(...start)]
    this._commands = []
    this._startIndex = []
    this._hasSubPaths = false
  }
  get length() { return this._commands.length }
  get start() { return this._vertices[0] }
  set start(p) {
    if (this._commands.length) throw new Error('Requires an empty path.')
    this._vertices[0] = Vec3(...p)
  }
  get end() { return this._vertices[this._vertices.length - 1] }
  /** `is_closed`: el primer vértice `isclose` al último (rel 1e-9, abs 1e-12, por componente). */
  get isClosed() {
    const v = this._vertices
    return v.length > 1 ? v3isclose(v[0], v[v.length - 1]) : false
  }
  lineTo(p) { this._commands.push(LINE_TO); this._startIndex.push(this._vertices.length); this._vertices.push(Vec3(...p)) }
  moveTo(p) {
    if (!this._commands.length) { this._vertices[0] = Vec3(...p); return }
    this._hasSubPaths = true
    if (this._commands[this._commands.length - 1] === MOVE_TO) { this._commands.pop(); this._vertices.pop(); this._startIndex.pop() }
    this._commands.push(MOVE_TO); this._startIndex.push(this._vertices.length); this._vertices.push(Vec3(...p))
  }
  curve3To(end, ctrl) { this._commands.push(CURVE3_TO); this._startIndex.push(this._vertices.length); this._vertices.push(Vec3(...ctrl), Vec3(...end)) }
  curve4To(end, ctrl1, ctrl2) { this._commands.push(CURVE4_TO); this._startIndex.push(this._vertices.length); this._vertices.push(Vec3(...ctrl1), Vec3(...ctrl2), Vec3(...end)) }
  close() { if (!this.isClosed) this.lineTo(this.start) }
  /** Los elementos como los itera Python: {type, end, ctrl, ctrl1, ctrl2}. */
  * [Symbol.iterator]() {
    const v = this._vertices
    for (let i = 0; i < this._commands.length; i++) {
      const cmd = this._commands[i], k = this._startIndex[i]
      if (cmd === MOVE_TO) yield { type: 'MOVE_TO', end: v[k] }
      else if (cmd === LINE_TO) yield { type: 'LINE_TO', end: v[k] }
      else if (cmd === CURVE3_TO) yield { type: 'CURVE3_TO', ctrl: v[k], end: v[k + 1] }
      else yield { type: 'CURVE4_TO', ctrl1: v[k], ctrl2: v[k + 1], end: v[k + 2] }
    }
  }
  /** `to_wcs(ocs, elevation)`: cada vértice con z = elevación y pasado a WCS. */
  toWcs(ocs, elevation) {
    this._vertices = this._vertices.map((v) => ocs.toWcs([v[0], v[1], Number(elevation)]))
  }
}

// ─── OCS (el «arbitrary axis algorithm» de AutoCAD) ─────────────────────────────────────────
const _1_OVER_64 = 1.0 / 64.0
export class OCS {
  constructor(extrusion = Z_AXIS) {
    const Az = v3normalize(Vec3(...extrusion))
    this.transform = !v3isclose(Az, Z_AXIS)
    if (this.transform) {
      let Ax = (Math.abs(Az[0]) < _1_OVER_64 && Math.abs(Az[1]) < _1_OVER_64) ? v3cross(Y_AXIS, Az) : v3cross(Z_AXIS, Az)
      Ax = v3normalize(Ax)
      const Ay = v3normalize(v3cross(Az, Ax))
      this.matrix = Matrix44.ucs(Ax, Ay, Az)
    }
  }
  get uz() { return this.transform ? [this.matrix.m[8], this.matrix.m[9], this.matrix.m[10]] : Z_AXIS }
  toWcs(p) { return this.transform ? this.matrix.transformDirection(p) : Vec3(...p) }
  fromWcs(p) { return this.transform ? this.matrix.ucsDirectionFromWcs(p) : Vec3(...p) }
}

// ─── Matrix44 (4×4 por filas, como matrix44.pyx) ────────────────────────────────────────────
export class Matrix44 {
  constructor(m) { this.m = m ? m.slice() : [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1] }
  static ucs(ux = X_AXIS, uy = Y_AXIS, uz = Z_AXIS, origin = NULLVEC) {
    const mat = new Matrix44()
    const m = mat.m
    m[0] = ux[0]; m[1] = ux[1]; m[2] = ux[2]
    m[4] = uy[0]; m[5] = uy[1]; m[6] = uy[2]
    m[8] = uz[0]; m[9] = uz[1]; m[10] = uz[2]
    m[12] = origin[0]; m[13] = origin[1]; m[14] = origin[2]
    return mat
  }
  static axisRotate(axis, angle) {
    const mat = new Matrix44(), m = mat.m
    const cosA = Math.cos(angle), sinA = Math.sin(angle), omc = 1.0 - cosA
    const [x, y, z] = v3normalize(Vec3(...axis))
    m[0] = x * x * omc + cosA; m[1] = y * x * omc + z * sinA; m[2] = x * z * omc - y * sinA
    m[4] = x * y * omc - z * sinA; m[5] = y * y * omc + cosA; m[6] = y * z * omc + x * sinA
    m[8] = x * z * omc + y * sinA; m[9] = y * z * omc - x * sinA; m[10] = z * z * omc + cosA
    return mat
  }
  /** `m *= other` (in place), fila por columna como lo escribe el pyx. */
  imul(other) {
    const m1 = this.m.slice(), m2 = other.m, r = this.m
    for (let i = 0; i < 4; i++) {
      for (let j = 0; j < 4; j++) {
        r[i * 4 + j] = m1[i * 4] * m2[j] + m1[i * 4 + 1] * m2[4 + j] + m1[i * 4 + 2] * m2[8 + j] + m1[i * 4 + 3] * m2[12 + j]
      }
    }
    return this
  }
  setRow(row, values) { for (let i = 0; i < Math.min(4, values.length); i++) this.m[row * 4 + i] = values[i] }
  transform(v) {
    const [x, y, z] = v, m = this.m
    return [x * m[0] + y * m[4] + z * m[8] + m[12], x * m[1] + y * m[5] + z * m[9] + m[13], x * m[2] + y * m[6] + z * m[10] + m[14]]
  }
  transformDirection(v) {
    const [x, y, z] = v, m = this.m
    return [x * m[0] + y * m[4] + z * m[8], x * m[1] + y * m[5] + z * m[9], x * m[2] + y * m[6] + z * m[10]]
  }
  ucsDirectionFromWcs(v) {
    const [x, y, z] = v, m = this.m
    return [x * m[0] + y * m[1] + z * m[2], x * m[4] + y * m[5] + z * m[6], x * m[8] + y * m[9] + z * m[10]]
  }
}

// ─── arcos y elipses → Bézier (bezier4p.pyx, ellipse.py, construct.pyx) ─────────────────────
const RAD_ABS_TOL = 1e-15
/** `arc_angle_span_rad` (construct.pyx). */
export function arcAngleSpanRad(start, end) {
  if (isclose(start, end, REL_TOL, RAD_ABS_TOL)) return 0.0
  start = pyModTau(start)
  if (isclose(start, pyModTau(end), REL_TOL, RAD_ABS_TOL)) return TAU
  if (!isclose(end, TAU, REL_TOL, RAD_ABS_TOL)) end = pyModTau(end)
  if (end < start) end += TAU
  return end - start
}

const TANGENT_FACTOR = 4.0 / 3.0
/** `cubic_bezier_arc_parameters` (bezier4p.pyx): cuartos de círculo unitario. */
export function cubicBezierArcParameters(startAngle, endAngle, segments = 1) {
  const delta = endAngle - startAngle
  if (!(delta > 0)) throw new Error('Delta angle from start- to end angle has to be > 0.')
  let arcCount = Math.ceil(delta / Math.PI * 2.0)
  if (segments > arcCount) arcCount = segments
  const segmentAngle = delta / arcCount
  const tangentLength = TANGENT_FACTOR * Math.tan(segmentAngle / 4.0)
  let angle = startAngle
  let endPoint = fromAngle(angle, 1.0)
  const out = []
  for (let i = 0; i < arcCount; i++) {
    const startPoint = endPoint
    angle += segmentAngle
    endPoint = fromAngle(angle, 1.0)
    const cp1 = [startPoint[0] - startPoint[1] * tangentLength, startPoint[1] + startPoint[0] * tangentLength, 0]
    const cp2 = [endPoint[0] + endPoint[1] * tangentLength, endPoint[1] - endPoint[0] * tangentLength, 0]
    out.push([startPoint, cp1, cp2, endPoint])
  }
  return out
}

/** `ConstructionEllipse` (ellipse.py): centro, eje mayor, extrusión, relación, parámetros. */
export class ConstructionEllipse {
  constructor(center = NULLVEC, majorAxis = X_AXIS, extrusion = Z_AXIS, ratio = 1, startParam = 0, endParam = TAU, ccw = true) {
    this.center = Vec3(...center)
    this.majorAxis = Vec3(...majorAxis)
    if (v3isclose(this.majorAxis, NULLVEC)) throw new Error('Invalid major axis (null vector).')
    this.extrusion = Vec3(...extrusion)
    this.ratio = Number(ratio)
    this.startParam = Number(startParam)
    this.endParam = Number(endParam)
    if (!ccw) [this.startParam, this.endParam] = [this.endParam, this.startParam]
    // minor_axis = extrusion.cross(major_axis).normalize(major_axis.magnitude * ratio)
    this.minorAxis = v3normalize(v3cross(this.extrusion, this.majorAxis), v3magnitude(this.majorAxis) * this.ratio)
  }
  static fromArc(center = NULLVEC, radius = 1, extrusion = Z_AXIS, startAngle = 0, endAngle = 360, ccw = true) {
    radius = Math.abs(radius)
    const ocs = new OCS(extrusion)
    const c = ocs.toWcs(center)
    const majorAxis = ocs.toWcs([radius, 0, 0])
    // grados → radianes como `math.radians`: x·(π/180)
    return new ConstructionEllipse(c, majorAxis, extrusion, 1.0, startAngle * (Math.PI / 180.0), endAngle * (Math.PI / 180.0), !!ccw)
  }
  get paramSpan() { return arcAngleSpanRad(this.startParam, this.endParam) }
  /** `vertex(param, major, minor, center, ratio)`. */
  vertex(param) {
    const xAxis = v3normalize(this.majorAxis), yAxis = v3normalize(this.minorAxis)
    const radiusX = v3magnitude(this.majorAxis), radiusY = radiusX * this.ratio
    const x = v3mul(xAxis, Math.cos(param) * radiusX)
    const y = v3mul(yAxis, Math.sin(param) * radiusY)
    return v3add(v3add(this.center, x), y)
  }
  get startPoint() { return this.vertex(this.startParam) }
}

/** `cubic_bezier_from_ellipse` (bezier4p.pyx). */
export function cubicBezierFromEllipse(ellipse, segments = 1) {
  const paramSpan = ellipse.paramSpan
  if (Math.abs(paramSpan) < 1e-9) return []
  const startAngle = pyModTau(ellipse.startParam)
  let endAngle = startAngle + paramSpan
  while (startAngle > endAngle) endAngle += TAU
  const center = ellipse.center, xAxis = ellipse.majorAxis, yAxis = ellipse.minorAxis
  const out = []
  for (const cps of cubicBezierArcParameters(startAngle, endAngle, segments)) {
    const res = []
    for (const cp of cps) {
      const b = v3mul(xAxis, cp[0]), c = v3mul(yAxis, cp[1])
      res.push([center[0] + b[0] + c[0], center[1] + b[1] + c[1], center[2] + b[2] + c[2]])   // v3_add_3
    }
    out.push(res)
  }
  return out
}

/** `reverse_bezier_curves`: cada curva al revés y la lista al revés. */
export function reverseBezierCurves(curves) {
  return curves.map((c) => [c[3], c[2], c[1], c[0]]).reverse()
}

/** `add_bezier4p` (path/tools.py): conecta con una recta si hace falta y degrada a LINE_TO las
 * Bézier cuyos controles coinciden EXACTAMENTE (rel 1e-15, abs 0) con sus extremos. */
export function addBezier4p(path, curves) {
  curves = curves.slice()
  if (!curves.length) return
  const end = curves[curves.length - 1][3]
  if (v3isclose(path.end, end)) curves = reverseBezierCurves(curves)
  for (const [start, ctrl1, ctrl2, fin] of curves) {
    if (!v3isclose(start, path.end)) path.lineTo(start)
    if (v3isclose(start, ctrl1, 1e-15, 0.0) && v3isclose(fin, ctrl2, 1e-15, 0.0)) path.lineTo(fin)
    else path.curve4To(fin, ctrl1, ctrl2)
  }
}

/** `add_ellipse`. */
export function addEllipse(path, ellipse, segments = 1, reset = true) {
  if (Math.abs(ellipse.paramSpan) < 1e-9) return
  if (path.length === 0 && reset) path.start = ellipse.startPoint
  addBezier4p(path, cubicBezierFromEllipse(ellipse, segments))
}

// ─── bulge (bulge.py, con Vec2 en C) ────────────────────────────────────────────────────────
function signedBulgeRadius(start, end, bulge) {
  return v2dist(start, end) * (1.0 + (bulge * bulge)) / 4.0 / bulge
}
/** `bulge_to_arc(start, end, bulge)` → [centro, ángulo inicial, ángulo final, radio] (siempre CCW). */
export function bulgeToArc(start, end, bulge) {
  const r = signedBulgeRadius(start, end, bulge)
  const a = v2angle(start, end) + (Math.PI / 2 - Math.atan(bulge) * 2)
  const c = [start[0] + Math.cos(a) * r, start[1] + Math.sin(a) * r]       // polar(start, a, r)
  if (bulge < 0) return [c, v2angle(c, end), v2angle(c, start), Math.abs(r)]
  return [c, v2angle(c, start), v2angle(c, end), Math.abs(r)]
}

const IS_CLOSE_TOL = 1e-10
/** `add_2d_polyline(path, points[(x, y, bulge)], close, ocs, elevation, segments)`. */
export function add2dPolyline(path, points, close, ocs, elevation, segments = 1) {
  const bulgeTo = (p1, p2, bulge) => {
    if (v3isclose(p1, p2, IS_CLOSE_TOL, 0)) return
    const numBez = Math.ceil(segments / 3)
    let [center, startAngle, endAngle, radius] = bulgeToArc(p1, p2, bulge)
    startAngle = pyModTau(startAngle)
    endAngle = pyModTau(endAngle)
    if (startAngle > endAngle) endAngle += TAU
    // np.linspace(start, end, num_bez + 1): con num_bez = 1 son exactamente [start, end]
    const angles = numBez === 1 ? [startAngle, endAngle] : linspace(startAngle, endAngle, numBez + 1)
    let curves = []
    for (let i = 0; i < numBez; i++) {
      const ellipse = ConstructionEllipse.fromArc(center, radius, Z_AXIS, angles[i] * (180.0 / Math.PI), angles[i + 1] * (180.0 / Math.PI))
      curves.push(...cubicBezierFromEllipse(ellipse))
    }
    const cp0 = curves[0][0]
    if (v3isclose(cp0, p2, IS_CLOSE_TOL, 0)) curves = reverseBezierCurves(curves)
    addBezier4p(path, curves)
  }
  if (path.length) throw new Error('Requires an empty path.')
  let prevPoint = null, prevBulge = 0
  for (let [x, y, bulge] of points) {
    if (Math.abs(bulge) < 1e-6) bulge = 0
    const point = Vec3(x, y)
    if (prevPoint === null) { path.start = point; prevPoint = point; prevBulge = bulge; continue }
    if (prevBulge) bulgeTo(prevPoint, point, prevBulge)
    else path.lineTo(point)
    prevPoint = point; prevBulge = bulge
  }
  if (close && !v3isclose(path.start, path.end, IS_CLOSE_TOL, 0)) {
    if (prevBulge) bulgeTo(path.end, path.start, prevBulge)
    else path.lineTo(path.start)
  }
  if (ocs.transform || elevation) path.toWcs(ocs, elevation)
}
function linspace(a, b, n) {
  // np.linspace: start + i·step, y el último es EXACTAMENTE `stop`
  const step = (b - a) / (n - 1)
  const out = []
  for (let i = 0; i < n; i++) out.push(i === n - 1 ? b : a + i * step)
  return out
}

// ─── B-spline (bspline.py + bspline.pyx) ────────────────────────────────────────────────────
function bisectRight(a, x, lo, hi) {
  while (lo < hi) {
    const mid = Math.floor((lo + hi) / 2)
    if (x < a[mid]) hi = mid
    else lo = mid + 1
  }
  return lo
}
class Basis {
  constructor(knots, order, count, weights) {
    if (order < 2 || order >= 12) throw new Error('invalid order')
    if (count < 2) throw new Error('invalid count')
    this.order = order; this.count = count
    this.knotCount = order + count
    this.weights = weights && weights.length ? weights.map(Number) : []
    if (this.weights.length !== 0 && this.weights.length !== count) throw new Error('invalid weight count')
    this.knots = knots.map(Number)
    if (this.knots.length !== this.knotCount) throw new Error('invalid knot count')
    this.maxT = this.knots[this.knotCount - 1]
  }
  get degree() { return this.order - 1 }
  get isRational() { return this.weights.length > 0 }
  findSpan(u) {
    const knots = this.knots, count = this.count, p = this.order - 1
    if (u >= knots[count]) return count - 1
    if (knots[p] === 0.0) return bisectRight(knots, u, p, count) - 1
    let span = 0
    while (knots[span] <= u && span < count) span += 1
    return span - 1
  }
  basisFuncs(span, u) {
    // NURBS Book A2.2, con los mismos arreglos que el pyx
    const order = this.order, knots = this.knots
    const N = new Array(order).fill(0.0), left = new Array(order).fill(0.0), right = new Array(order).fill(0.0)
    N[0] = 1.0
    for (let j = 1; j < order; j++) {
      let i1 = span + 1 - j
      if (i1 < 0) i1 = 0
      left[j] = u - knots[i1]
      right[j] = knots[span + j] - u
      let saved = 0.0
      for (let r = 0; r < j; r++) {
        const tempR = right[r + 1], tempL = left[j - r]
        const temp = N[r] / (tempR + tempL)
        N[r] = saved + tempR * temp
        saved = tempL * temp
      }
      N[j] = saved
    }
    const result = N.slice(0, order)
    return this.isRational ? this.spanWeighting(result, span) : result
  }
  spanWeighting(nbasis, span) {
    const ws = this.weights.slice(Math.max(0, span - this.order + 1), span + 1)
    const products = []
    for (let i = 0; i < Math.min(nbasis.length, ws.length); i++) products.push(nbasis[i] * ws[i])
    if (products.length !== nbasis.length) return nbasis
    const s = pySum(products, () => false)
    if (s !== 0) return products.map((p) => p / s)
    return nbasis
  }
}
export class BSpline {
  constructor(controlPoints, order = 4, knots = null, weights = null) {
    this._controlPoints = controlPoints.map((p) => Vec3(...p))
    const count = this._controlPoints.length
    order = Math.trunc(order)
    if (order > count) throw new Error(`got ${count} control points, need ${order} or more for order of ${order}`)
    if (knots === null) knots = openUniformKnotVector(count, order, true)
    else {
      knots = knots.slice()
      if (knots.length !== count + order) throw new Error(`${count + order} knot values required, got ${knots.length}.`)
      if (knots[0] !== 0.0) knots = normalizeKnots(knots)
    }
    this._basis = new Basis(knots, order, count, weights)
    this._clamped = new Set(knots.slice(0, order)).size === 1 && new Set(knots.slice(-order)).size === 1
  }
  get controlPoints() { return this._controlPoints }
  get count() { return this._controlPoints.length }
  get maxT() { return this._basis.maxT }
  get order() { return this._basis.order }
  get degree() { return this._basis.degree }
  get isRational() { return this._basis.isRational }
  get isClamped() { return this._clamped }
  knots() { return this._basis.knots.slice() }
  /** `Evaluator.point(u)` (A3.1). */
  point(u) {
    const basis = this._basis
    if (isclose(u, basis.maxT, REL_TOL, ABS_TOL)) u = basis.maxT
    const p = basis.order - 1
    const span = basis.findSpan(u)
    const N = basis.basisFuncs(span, u)
    const sum = [0, 0, 0]
    for (let i = 0; i <= p; i++) {
      const factor = N[i], cp = this._controlPoints[span - p + i]
      sum[0] += cp[0] * factor; sum[1] += cp[1] * factor; sum[2] += cp[2] * factor
    }
    return sum
  }
  points(ts) { return ts.map((t) => this.point(t)) }
  /** `bezier_decomposition` (NURBS Book A5.6): sólo no racional y sujeta. */
  bezierDecomposition() {
    if (this._basis.isRational) throw new Error('Rational B-splines not supported.')
    if (!this.isClamped) throw new Error('Clamped B-Spline required.')
    const n = this.count - 1, p = this.degree
    const knots = this._basis.knots, controlPoints = this._controlPoints
    const alphas = new Array(knots.length).fill(0.0)
    const m = n + p + 1
    let a = p, b = p + 1
    let bezierPoints = controlPoints.slice(0, p + 1)
    const out = []
    while (b < m) {
      const nextBezierPoints = new Array(p + 1).fill(NULLVEC)
      const i = b
      while (b < m && mathIsclose(knots[b + 1], knots[b])) b += 1
      const mult = b - i + 1
      if (mult < p) {
        const numer = knots[b] - knots[a]
        for (let j = p; j > mult; j--) alphas[j - mult - 1] = numer / (knots[a + j] - knots[a])
        const r = p - mult
        for (let j = 1; j <= r; j++) {
          const save = r - j, s = mult + j
          for (let k = p; k >= s; k--) {
            const alpha = alphas[k - s]
            bezierPoints[k] = v3add(v3mul(bezierPoints[k], alpha), v3mul(bezierPoints[k - 1], 1.0 - alpha))
          }
          if (b < m) nextBezierPoints[save] = bezierPoints[p]
        }
      }
      out.push(bezierPoints.slice())
      if (b < m) {
        for (let k = p - mult; k <= p; k++) nextBezierPoints[k] = controlPoints[b - p + k]
        a = b; b += 1
        bezierPoints = nextBezierPoints
      }
    }
    return out
  }
  /** `approximation_params(level)`: parámetros por cuerda de los puntos de control, subdivididos. */
  approximationParams(level = 3) {
    let params = distanceTVector(this._controlPoints)
    if (!params.length) return params
    if (this.maxT !== 1.0) { const maxT = this.maxT; params = params.map((p) => p * maxT) }
    for (let i = 0; i < level - 1; i++) params = subdivideParams(params)
    return params
  }
  /** `cubic_bezier_approximation(level)`: puntos sobre la curva + interpolación cúbica. */
  cubicBezierApproximation(level = 3) {
    const points = this.points(this.approximationParams(level))
    return cubicBezierInterpolation(points)
  }
}
function normalizeKnots(knots) {
  const minVal = knots[0], maxVal = knots[knots.length - 1] - minVal
  return knots.map((v) => (v - minVal) / maxVal)
}
function openUniformKnotVector(count, order, normalize = false) {
  const k = []
  for (let i = 0; i < order; i++) k.push(0.0)
  for (let i = 1; i <= count - order; i++) k.push(i)
  for (let i = 0; i < order; i++) k.push(count - order + 1)
  return normalize ? normalizeKnots(k.map(Number)) : k.map(Number)
}
function subdivideParams(p) {
  const out = []
  for (let i = 0; i < p.length - 1; i++) { out.push(p[i]); out.push((p[i] + p[i + 1]) / 2.0) }
  out.push(p[p.length - 1])
  return out
}
function distanceTVector(points) {
  const distances = []
  for (let i = 1; i < points.length; i++) distances.push(v3dist(points[i - 1], points[i]))
  const total = pySum(distances, () => false)
  if (Math.abs(total) <= 1e-12) return []
  const params = [0.0]
  let s = 0.0
  for (const d of distances.slice(0, -1)) { s += d; params.push(s / total) }
  params.push(1.0)
  return params
}
/** `cubic_bezier_interpolation(points)` (bezier_interpolation.py) con el solver tridiagonal. */
export function cubicBezierInterpolation(points) {
  const pnts = points.map((p) => Vec3(...p))
  if (pnts.length < 3) return []
  const num = pnts.length - 1
  const b = new Array(num).fill(4.0), a = new Array(num).fill(1.0), c = new Array(num).fill(1.0)
  b[0] = 2.0; b[num - 1] = 7.0; a[num - 1] = 2.0
  const pv = [v3add(pnts[0], v3mul(pnts[1], 2.0))]
  for (let i = 1; i < num - 1; i++) pv.push(v3mul(v3add(v3mul(pnts[i], 2.0), pnts[i + 1]), 2.0))
  pv.push(v3add(v3mul(pnts[num - 1], 8.0), pnts[num]))
  // tridiagonal_matrix_solver: una columna por coordenada
  const cols = [0, 1, 2].map((k) => solveTridiagonal(a, b, c, pv.map((v) => v[k])))
  const cp1 = []
  for (let i = 0; i < num; i++) cp1.push([cols[0][i], cols[1][i], cols[2][i]])
  const cp2 = []
  for (let i = 1; i < num; i++) cp2.push(v3sub(v3mul(pnts[i], 2.0), cp1[i]))
  cp2.push(v3mul(v3add(cp1[num - 1], pnts[num]), 1.0 / 2.0))
  const out = []
  for (let i = 0; i < num; i++) out.push([pnts[i], cp1[i], cp2[i], pnts[i + 1]])
  return out
}
function solveTridiagonal(a, b, c, r) {
  const n = a.length
  const u = new Array(n).fill(0.0), gam = new Array(n).fill(0.0)
  let bet = b[0]
  u[0] = r[0] / bet
  for (let j = 1; j < n; j++) {
    gam[j] = c[j - 1] / bet
    bet = b[j] - a[j] * gam[j]
    u[j] = (r[j] - a[j] * u[j - 1]) / bet
  }
  for (let j = n - 2; j >= 0; j--) u[j] -= gam[j + 1] * u[j + 1]
  return u
}
/** `add_spline(path, spline, level=4, reset=True)`. */
export function addSpline(path, spline, level = 4, reset = true) {
  if (path.length === 0 && reset) path.start = spline.point(0)
  let curves
  if (spline.degree === 3 && !spline.isRational && spline.isClamped) curves = spline.bezierDecomposition()
  else curves = spline.cubicBezierApproximation(level)
  addBezier4p(path, curves)
}
/** `round_knots(knots, tolerance)`: `round(k, -int(log10(tol)))`. */
export function roundKnots(knots, tolerance) {
  let nd
  try { nd = -Math.trunc(Math.log10(tolerance)) } catch { return knots }
  if (!Number.isFinite(nd) || nd <= 0) return knots
  return knots.map((k) => pyRound(k, nd))
}

// ─── make_path por tipo de entidad (path/converter.py) ──────────────────────────────────────
/** `ezdxf.path.make_path(entidad)` para los tipos que forman piezas; null si el tipo no va. */
export function makePath(e) {
  const t = e.type
  if (t === 'LWPOLYLINE') {
    const path = new Path()
    add2dPolyline(path, e.points.map((p) => [p.x, p.y, p.b]), (e.flags & 1) !== 0, new OCS(e.extrusion), e.elevation, 1)
    return path
  }
  if (t === 'POLYLINE') {
    // is_polygon_mesh (16) / is_poly_face_mesh (64) → TypeError en ezdxf → importar_dxf lo descarta
    if (e.flags & 16 || e.flags & 64) throw new TypeError('Unsupported DXF type PolyMesh or PolyFaceMesh')
    const path = new Path()
    if (!e.vertices.length) return path
    if (e.flags & 8) {                        // is_3d_polyline → from_vertices(points, is_closed)
      return fromVertices(e.vertices.map((v) => [v.x, v.y, v.z]), (e.flags & 1) !== 0)
    }
    const points = e.vertices.map((v) => [v.x, v.y, v.bulge])
    const elevation = e.elevation !== undefined ? e.elevation[2] : e.vertices[0].z
    add2dPolyline(path, points, (e.flags & 1) !== 0, new OCS(e.extrusion), elevation, 1)
    return path
  }
  if (t === 'SPLINE') {
    const path = new Path()
    addSpline(path, splineConstructionTool(e), 4, true)
    return path
  }
  if (t === 'ELLIPSE') {
    const path = new Path()
    addEllipse(path, new ConstructionEllipse(e.center, e.majorAxis, e.extrusion, e.ratio, e.startParam, e.endParam), 1, true)
    return path
  }
  if (t === 'CIRCLE') {
    const path = new Path()
    const radius = Math.abs(e.radius)
    if (radius > 1e-12) addEllipse(path, ConstructionEllipse.fromArc(e.center, radius, e.extrusion), 1, true)
    return path
  }
  return null
}
function fromVertices(vertices, close = false) {
  const vs = vertices.map((v) => Vec3(...v))
  if (!vs.length) return new Path()
  const path = new Path(vs[0])
  for (const v of vs.slice(1)) path.lineTo(v)
  if (close) path.close()
  return path
}
/** `Spline.construction_tool()`: sólo con puntos de control (los de sólo «fit points» no). */
export function splineConstructionTool(e) {
  if (!e.controlPoints.length) throw new Error('SPLINE sin puntos de control (sólo fit points): no soportado en el navegador')
  const weights = e.weights.length ? e.weights : null
  const knots = e.knots.length ? roundKnots(e.knots, e.knotTolerance) : null
  return new BSpline(e.controlPoints, e.degree + 1, knots, weights)
}

// ─── INSERT.virtual_entities: el bloque transformado (insert.py + explode.py) ────────────────
/** `Insert.matrix44()`: escala·rotación en el OCS del INSERT, más la traslación (con el punto base). */
export function insertMatrix44(ins, block) {
  const sx = ins.xscale, sy = ins.yscale, sz = ins.zscale
  const ocs = new OCS(ins.extrusion)
  const extrusion = ocs.uz
  const ux = ocs.toWcs(X_AXIS), uy = ocs.toWcs(Y_AXIS)
  const m = Matrix44.ucs(v3mul(ux, sx), v3mul(uy, sy), v3mul(extrusion, sz))
  const angle = ins.rotation * (Math.PI / 180.0)
  if (angle) m.imul(Matrix44.axisRotate(extrusion, angle))
  let insert = ocs.toWcs(ins.insert)
  if (block) insert = v3sub(insert, m.transformDirection(block.basePoint))
  m.setRow(3, insert)
  return m
}
/** `transform_extrusion(extrusion, m)` → [nueva extrusión, ¿escala uniforme en el plano?]. */
function transformExtrusion(extrusion, m) {
  const ocs = new OCS(extrusion)
  const xAxis = m.transformDirection(ocs.toWcs(X_AXIS)), yAxis = m.transformDirection(ocs.toWcs(Y_AXIS))
  const isUniform = mathIsclose(v3magnitudeSqr(xAxis), v3magnitudeSqr(yAxis), 1e-9, 1e-9)
  return [v3normalize(v3cross(xAxis, yAxis)), isUniform]
}
class OCSTransform {
  constructor(extrusion, m) {
    this.m = m
    const [nueva, uniforme] = transformExtrusion(extrusion, m)
    this.oldOcs = new OCS(extrusion); this.newOcs = new OCS(nueva); this.scaleUniform = uniforme
  }
  get newExtrusion() { return this.newOcs.uz }
  transformVertex(v) { return this.newOcs.fromWcs(this.m.transform(this.oldOcs.toWcs(v))) }
  transformLength(v) { return v3magnitude(this.m.transformDirection(this.oldOcs.toWcs(v))) }
}
/**
 * `Insert.virtual_entities()`: copias transformadas de las entidades del bloque. Se traducen las que
 * pueden formar pieza o texto: LWPOLYLINE, CIRCLE, SPLINE, LINE. Un ELLIPSE o POLYLINE adentro de
 * un bloque (raro en moldería) no se transforma acá → se omite y se avisa por `omitidas`.
 */
export function virtualEntities(ins, blocks, omitidas) {
  const block = blocks.get(ins.name)
  if (!block) throw new Error(`Required block definition for "${ins.name}" does not exist.`)
  const m = insertMatrix44(ins, block)
  const out = []
  for (const e of block.entities) {
    if (e.type === 'ATTDEF') continue
    const t = e.type
    if (t === 'LWPOLYLINE') {
      const ocs = new OCSTransform(e.extrusion, m)
      const hasArc = e.points.some((p) => p.b !== 0)
      if (!ocs.scaleUniform && hasArc) { omitidas?.push(`${t} con arcos y escala no uniforme`); continue }
      const vs = e.points.map((p) => ocs.transformVertex([p.x, p.y, e.elevation]))
      const c = { ...e, points: e.points.map((p, i) => ({ x: vs[i][0], y: vs[i][1], s: p.s, e: p.e, b: p.b })) }
      if (vs.length) c.elevation = vs[0][2]
      c.extrusion = ocs.newExtrusion
      out.push(c)
    } else if (t === 'CIRCLE') {
      const ocs = new OCSTransform(e.extrusion, m)
      if (!ocs.scaleUniform) { omitidas?.push(`${t} con escala no uniforme`); continue }
      out.push({ ...e, extrusion: ocs.newExtrusion, center: ocs.transformVertex(e.center), radius: ocs.transformLength([e.radius, 0, 0]) })
    } else if (t === 'SPLINE') {
      out.push({ ...e, controlPoints: e.controlPoints.map((p) => m.transform(p)), fitPoints: e.fitPoints.map((p) => m.transform(p)) })
    } else if (t === 'LINE') {
      out.push({ ...e, start: m.transform(e.start), end: m.transform(e.end) })
    } else if (t === 'INSERT') {
      // ezdxf devuelve el INSERT anidado como INSERT (transformado): `_segs_de` lo ignora, así que
      // no aporta contornos. Se omite sin aviso, que es lo que hace Python.
      continue
    } else {
      omitidas?.push(`${t} dentro de un bloque`)
    }
  }
  return out
}
