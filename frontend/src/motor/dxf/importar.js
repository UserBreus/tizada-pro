// IMPORTAR UN MOLDE EN DXF EN EL NAVEGADOR — PLAN_NAVEGADOR.md, etapa 1, punto 7.
//
// Traducción función por función de `importar_dxf.py`: el DXF de moldería (Optitex/AAMA o genérico)
// se convierte en un PDF con la MISMA estructura que un .ai (una capa OCG por talle + los contornos
// de cada pieza como trazos), para que el resto del sistema (detección, nombrado, motor) funcione
// igual. El contrato `verificar_navegador_dxf.py` exige el mismo `resumen`, la misma página, las
// mismas capas y el mismo content-stream, token por token, que el Python.
//
// 🔴 LO QUE HAY QUE COPIAR DE PYMUPDF, NO DE PDF «EN GENERAL» (igual que en `ficha/ficha.js`):
//   · cada punto pasa por `fz_transform_point` (float32) con la matriz inversa de la página
//     (1, 0, 0, -1, -0, alto32) y después por `JM_TUPLE` (`round(x, 5)`, y 0 si |x| < 1e-4);
//   · los números van con el `%g` de MuPDF (`fz_format_double`): el decimal más corto que vuelve
//     al mismo float de 32 bits, sin cero a la izquierda; se le pide a `newReal(v).toString()`;
//   · `Shape.draw_line` sólo escribe `m` cuando el punto anterior NO es exactamente el mismo;
//   · `finish(oc=...)` envuelve en `/OC /MCn BDC … EMC` (los nombres se dan por ORDEN DE USO, sólo
//     a los talles que dibujan algo), pinta `.16 .62 .42 RG S`, y cada `finish` va en su `q … Q`;
//   · el fondo blanco es `0 0 W H re h 1 1 1 rg f` con W y H en doble (no el MediaBox en float32).
//
// 🔴 LO QUE NO SE PUEDE COPIAR BIT A BIT (medido 2026-09-18 con 60 000 muestras, Python/UCRT contra
// Node/V8): `sin`/`cos`/`tan`/`atan`/`atan2`/`acos` difieren en el último bit en el 0,4-21 % de los
// casos y `x**2`/`x**3` (el `pow` de UCRT) en el 0,04-0,07 %. `math.hypot` SÍ se reproduce
// (`pyHypot`). Esos bits entran al ajuste de curvas (`_contorno_suave`) y a los arcos de ezdxf;
// después de `round(x, 5)` desaparecen salvo que un valor caiga justo en el borde del redondeo, o
// que un empate del `argmax` del error se decida distinto. El contrato lo mide y lo dice.
//
// ENTRADA: `dxfAPdf(mupdf, bytes)` → `{pdf: Uint8Array, resumen}`; `resumen` = `dxf_resumen`
// (`piezas`, `talles`, `nombres_detectados`, `nombres`, `indices`, `escala_pdf`).
import { pyRound, pyStrip, pyHypot, compararTuplas } from '../py.js'
import { leerDXF, plainMtext } from './leer.js'
import { makePath, virtualEntities } from './geometria.js'

export const CM = 28.3465          // puntos por cm
const _UNID_A_CM = new Map([[0, 0.1], [1, 2.54], [2, 30.48], [4, 0.1], [5, 1.0], [6, 100.0], [8, 0.00254]])

// Entidades que pueden formar el contorno cerrado de una pieza.
const _TIPOS_PIEZA = new Set(['LWPOLYLINE', 'POLYLINE', 'SPLINE', 'ELLIPSE', 'CIRCLE'])

function _pathASegs(p) {
  // Convierte un Path a segmentos (m/l/c/h) SIN perder curvas. CURVE3 se eleva a cúbica exacta.
  const segs = []
  let sx = p.start[0], sy = p.start[1]
  segs.push(['m', sx, sy])
  let cx = sx, cy = sy
  for (const cmd of p) {
    const ex = cmd.end[0], ey = cmd.end[1]
    if (cmd.type === 'MOVE_TO') { segs.push(['m', ex, ey]); sx = ex; sy = ey }
    else if (cmd.type === 'LINE_TO') segs.push(['l', ex, ey])
    else if (cmd.type === 'CURVE3_TO') {
      const qx = cmd.ctrl[0], qy = cmd.ctrl[1]
      const c1x = cx + 2.0 / 3.0 * (qx - cx), c1y = cy + 2.0 / 3.0 * (qy - cy)
      const c2x = ex + 2.0 / 3.0 * (qx - ex), c2y = ey + 2.0 / 3.0 * (qy - ey)
      segs.push(['c', c1x, c1y, c2x, c2y, ex, ey])
    } else if (cmd.type === 'CURVE4_TO') segs.push(['c', cmd.ctrl1[0], cmd.ctrl1[1], cmd.ctrl2[0], cmd.ctrl2[1], ex, ey])
    else segs.push(['l', ex, ey])
    cx = ex; cy = ey
  }
  return [segs, [sx, sy], [cx, cy]]
}

function _segsDe(e) {
  // Contorno CERRADO de una entidad como segmentos, FIEL al archivo: polilíneas punto a punto,
  // curvas reales (bulge/spline/elipse/círculo) como Bézier exactas vía make_path.
  if (!_TIPOS_PIEZA.has(e.type)) return null
  let p
  try { p = makePath(e) } catch { return null }
  if (!p || p.length < 2) return null
  const [segs, [sx, sy], [cx, cy]] = _pathASegs(p)
  const bb = _bboxSegs(segs)
  if (!bb) return null
  const diag = Math.max(bb[2] - bb[0], bb[3] - bb[1], 1e-9)
  const cerrado = p.isClosed || (Math.abs(sx - cx) + Math.abs(sy - cy)) < diag * 0.002
  if (!cerrado) return null
  segs.push(['h'])
  // Si vino como PURAS RECTAS (polilínea de puntos) → ajustar curvas Bézier. Si trae arcos, se dejan.
  if (!segs.some((s) => s[0] === 'c')) {
    const pts = segs.filter((s) => s[0] === 'm' || s[0] === 'l').map((s) => [s[1], s[2]])
    const suave = _contornoSuave(pts)
    if (suave) return suave
  }
  return segs
}

export function _bboxSegs(segs) {
  // Bounding box de los segmentos, con los puntos de control (la curva queda dentro de su casco).
  const xs = [], ys = []
  for (const s of segs) {
    if (s[0] === 'm' || s[0] === 'l') { xs.push(s[1]); ys.push(s[2]) }
    else if (s[0] === 'c') { xs.push(s[1], s[3], s[5]); ys.push(s[2], s[4], s[6]) }
  }
  if (!xs.length) return null
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]
}

function _escalaCm(doc, piezas) {
  // cm por unidad DXF: $INSUNITS si está (y no es 0); si no, por el tamaño de la pieza más grande.
  const u = doc.header.INSUNITS
  if (u) return _UNID_A_CM.has(Math.trunc(u)) ? _UNID_A_CM.get(Math.trunc(u)) : 1.0
  let maxd = 0.0
  for (const p of piezas) {
    for (const segs of p.talles.values()) {
      const bb = _bboxSegs(segs)
      if (bb) maxd = Math.max(maxd, bb[2] - bb[0], bb[3] - bb[1])
    }
  }
  return maxd < 300 ? 1.0 : 0.1
}

// ── stitching: unir LINEs sueltas en contornos ────────────────────────────────
function _stitch(lineas, tol = 0.05) {
  // Une LINE sueltas en CADENAS por extremos compartidos (cuantizados a `tol`); las devuelve por
  // área de bbox descendente (la mayor = el contorno de la pieza).
  const segs = []
  for (const l of lineas) {
    const a = [l.start[0], l.start[1]], b = [l.end[0], l.end[1]]
    if (Math.abs(a[0] - b[0]) > 1e-9 || Math.abs(a[1] - b[1]) > 1e-9) segs.push([a, b])
  }
  if (!segs.length) return []
  const q = 1.0 / tol
  const k = (p) => `${pyRound(p[0] * q)},${pyRound(p[1] * q)}`
  const adj = new Map()
  const meter = (key, i) => { if (!adj.has(key)) adj.set(key, []); adj.get(key).push(i) }
  segs.forEach(([a, b], i) => { meter(k(a), i); meter(k(b), i) })
  const usado = new Array(segs.length).fill(false)
  const cadenas = []
  for (let i0 = 0; i0 < segs.length; i0++) {
    if (usado[i0]) continue
    usado[i0] = true
    const [a, b] = segs[i0]
    const cad = [a, b]
    for (;;) {                                  // extender hacia adelante
      const fin = cad[cad.length - 1]
      let nxt = null
      for (const j of (adj.get(k(fin)) || [])) if (!usado[j]) { nxt = j; break }
      if (nxt === null) break
      usado[nxt] = true
      const [s, e] = segs[nxt]
      cad.push(k(s) === k(fin) ? e : s)
    }
    for (;;) {                                  // extender hacia atrás
      const ini = cad[0]
      let prv = null
      for (const j of (adj.get(k(ini)) || [])) if (!usado[j]) { prv = j; break }
      if (prv === null) break
      usado[prv] = true
      const [s, e] = segs[prv]
      cad.unshift(k(e) === k(ini) ? s : e)
    }
    cadenas.push(cad)
  }
  const area = (cad) => {
    const xs = cad.map((p) => p[0]), ys = cad.map((p) => p[1])
    return (Math.max(...xs) - Math.min(...xs)) * (Math.max(...ys) - Math.min(...ys))
  }
  // sort(key=area, reverse=True): estable, los empates conservan el orden original
  return cadenas.map((c, i) => [area(c), i, c]).sort((a, b) => (b[0] - a[0]) || (a[1] - b[1])).map((x) => x[2])
}

function _cadASegs(cad) {
  // Cadena de puntos → segmentos (m/l/h), TAL CUAL. Cierra el contorno.
  if (!cad || cad.length < 3) return null
  const segs = [['m', cad[0][0], cad[0][1]]]
  for (const p of cad.slice(1)) segs.push(['l', p[0], p[1]])
  segs.push(['h'])
  return segs
}

// ── ajuste de curvas Bézier (Schneider) sobre los puntos del contorno ─────────
// Mismas operaciones y en el mismo orden que el Python: `**` es `Math.pow` (el `pow` de C), `hypot`
// es el de CPython (`pyHypot`).
const _fcs = (a, b) => [a[0] - b[0], a[1] - b[1]]
const _fca = (a, b) => [a[0] + b[0], a[1] + b[1]]
const _fck = (a, s) => [a[0] * s, a[1] * s]
const _fcd = (a, b) => a[0] * b[0] + a[1] * b[1]
const _fcl = (a) => pyHypot(a[0], a[1])
function _fcn(a) { const l = _fcl(a) || 1e-12; return [a[0] / l, a[1] / l] }
function _fcq(bz, t) {
  const mt = 1 - t
  return [bz[0][0] * Math.pow(mt, 3) + 3 * bz[1][0] * mt * mt * t + 3 * bz[2][0] * mt * t * t + bz[3][0] * Math.pow(t, 3),
    bz[0][1] * Math.pow(mt, 3) + 3 * bz[1][1] * mt * mt * t + 3 * bz[2][1] * mt * t * t + bz[3][1] * Math.pow(t, 3)]
}
function _fcChord(pts) {
  const u = [0.0]
  for (let i = 1; i < pts.length; i++) u.push(u[u.length - 1] + _fcl(_fcs(pts[i], pts[i - 1])))
  const tot = u[u.length - 1] || 1e-12
  return u.map((x) => x / tot)
}
function _fcGen(pts, u, lT, rT) {
  const A = []
  for (let i = 0; i < pts.length; i++) A.push([_fck(lT, 3 * Math.pow(1 - u[i], 2) * u[i]), _fck(rT, 3 * (1 - u[i]) * Math.pow(u[i], 2))])
  const C = [[0.0, 0.0], [0.0, 0.0]], X = [0.0, 0.0]
  const p0 = pts[0], pn = pts[pts.length - 1]
  for (let i = 0; i < pts.length; i++) {
    const [a0, a1] = A[i]
    C[0][0] += _fcd(a0, a0); C[0][1] += _fcd(a0, a1); C[1][0] += _fcd(a0, a1); C[1][1] += _fcd(a1, a1)
    const t = u[i], mt = 1 - t, b0 = Math.pow(mt, 3), b1 = 3 * mt * mt * t, b2 = 3 * mt * t * t, b3 = Math.pow(t, 3)
    const base = [p0[0] * (b0 + b1) + pn[0] * (b2 + b3), p0[1] * (b0 + b1) + pn[1] * (b2 + b3)]
    const tmp = _fcs(pts[i], base); X[0] += _fcd(a0, tmp); X[1] += _fcd(a1, tmp)
  }
  const detC = C[0][0] * C[1][1] - C[1][0] * C[0][1], seg = _fcl(_fcs(pn, p0))
  let al, ar
  if (Math.abs(detC) < 1e-12) al = ar = seg / 3.0
  else { al = (X[0] * C[1][1] - X[1] * C[0][1]) / detC; ar = (C[0][0] * X[1] - C[1][0] * X[0]) / detC }
  if (al < 1e-6 * seg || ar < 1e-6 * seg) al = ar = seg / 3.0
  return [p0, _fca(p0, _fck(lT, al)), _fca(pn, _fck(rT, ar)), pn]
}
function _fcErr(pts, bz, u) {
  let md = 0.0, sp = Math.floor(pts.length / 2)
  for (let i = 1; i < pts.length - 1; i++) {
    const q = _fcq(bz, u[i]), d = _fcs(q, pts[i]), dd = d[0] * d[0] + d[1] * d[1]
    if (dd > md) { md = dd; sp = i }
  }
  return [md, sp]
}
function _fcReparam(bz, pts, u) {
  const q1 = [0, 1, 2].map((i) => _fck(_fcs(bz[i + 1], bz[i]), 3))
  const q2 = [0, 1].map((i) => _fck(_fcs(q1[i + 1], q1[i]), 2))
  const out = []
  for (let i = 0; i < u.length; i++) {
    const t = u[i], mt = 1 - t
    const qq = _fcq(bz, t), d = _fcs(qq, pts[i])
    const d1 = [q1[0][0] * mt * mt + 2 * q1[1][0] * mt * t + q1[2][0] * t * t, q1[0][1] * mt * mt + 2 * q1[1][1] * mt * t + q1[2][1] * t * t]
    const d2 = [q2[0][0] * mt + q2[1][0] * t, q2[0][1] * mt + q2[1][1] * t]
    const num = d[0] * d1[0] + d[1] * d1[1]
    const den = Math.pow(d1[0], 2) + Math.pow(d1[1], 2) + d[0] * d2[0] + d[1] * d2[1]
    out.push(Math.abs(den) < 1e-12 ? t : t - num / den)
  }
  return out
}
function _fcFit(pts, lT, rT, err, depth = 0) {
  if (pts.length === 2) {
    const d = _fcl(_fcs(pts[1], pts[0])) / 3.0
    return [[pts[0], _fca(pts[0], _fck(lT, d)), _fca(pts[1], _fck(rT, d)), pts[1]]]
  }
  let u = _fcChord(pts), bz = _fcGen(pts, u, lT, rT)
  let [e, sp] = _fcErr(pts, bz, u)
  if (e < err) return [bz]
  if (depth < 24 && e < err * 16) {
    for (let k = 0; k < 6; k++) {
      u = _fcReparam(bz, pts, u); bz = _fcGen(pts, u, lT, rT); [e, sp] = _fcErr(pts, bz, u)
      if (e < err) return [bz]
    }
  }
  sp = Math.max(1, Math.min(pts.length - 2, sp))
  const cT = _fcn(_fcs(pts[sp - 1], pts[sp + 1]))
  return _fcFit(pts.slice(0, sp + 1), lT, cT, err, depth + 1).concat(_fcFit(pts.slice(sp), [-cT[0], -cT[1]], rT, err, depth + 1))
}

function _contornoSuave(cad, tol = 0.04, cornerAng = 32.0) {
  // Cadena de puntos → segs (m/l/c/h) con Bézier ajustadas, esquinas y piquetes preservados.
  try {
    const P = []
    for (const p0 of cad) {
      const p = [Number(p0[0]), Number(p0[1])]
      if (!P.length || Math.abs(p[0] - P[P.length - 1][0]) > 1e-7 || Math.abs(p[1] - P[P.length - 1][1]) > 1e-7) P.push(p)
    }
    if (P.length >= 2 && Math.abs(P[0][0] - P[P.length - 1][0]) < 1e-7 && Math.abs(P[0][1] - P[P.length - 1][1]) < 1e-7) P.pop()
    const n = P.length
    if (n < 4) return _cadASegs(cad)
    const turn = (i) => {
      const a = P[(i - 1 + n) % n], b = P[i], c = P[(i + 1) % n]
      const v1 = _fcs(b, a), v2 = _fcs(c, b), l1 = _fcl(v1) || 1e-9, l2 = _fcl(v2) || 1e-9
      return Math.acos(Math.max(-1.0, Math.min(1.0, _fcd(v1, v2) / (l1 * l2)))) * (180.0 / Math.PI)
    }
    const corners = []
    for (let i = 0; i < n; i++) if (turn(i) > cornerAng) corners.push(i)
    const err = tol * tol
    if (!corners.length) {
      const seq = P.concat([P[0]])
      const lT = _fcn(_fcs(seq[1], seq[0])), rT = _fcn(_fcs(seq[seq.length - 2], seq[seq.length - 1]))
      const bezs = _fcFit(seq, lT, rT, err)
      const segs = [['m', bezs[0][0][0], bezs[0][0][1]]]
      for (const b of bezs) segs.push(['c', b[1][0], b[1][1], b[2][0], b[2][1], b[3][0], b[3][1]])
      segs.push(['h'])
      return segs
    }
    const segs = [['m', P[corners[0]][0], P[corners[0]][1]]]
    const mn = corners.length
    for (let ci = 0; ci < mn; ci++) {
      const i0 = corners[ci], i1 = corners[(ci + 1) % mn]
      const run = []
      let i = i0
      for (;;) { run.push(P[i]); if (i === i1) break; i = (i + 1) % n }
      if (run.length === 2) segs.push(['l', run[1][0], run[1][1]])
      else if (run.length > 2) {
        const lT = _fcn(_fcs(run[1], run[0])), rT = _fcn(_fcs(run[run.length - 2], run[run.length - 1]))
        for (const b of _fcFit(run, lT, rT, err)) segs.push(['c', b[1][0], b[1][1], b[2][0], b[2][1], b[3][0], b[3][1]])
      }
    }
    segs.push(['h'])
    return segs
  } catch {
    return _cadASegs(cad)
  }
}

// `s[5:].strip()` / `.lstrip("@").strip()` con los espacios de Python
const _despues = (s, n) => pyStrip(Array.from(s).slice(n).join(''))
const _sinArroba = (s) => pyStrip(s.replace(/^@+/, ''))

function _parseOptitexLineas(msp) {
  // Optitex/AAMA con el contorno EXPLOTADO en LINEs: Size:/Piece Name: en textos + LINEs que se
  // UNEN en el contorno de cada pieza.
  const reg = new Map(), orden = []
  let curSize = null, curPiece = null, lineas = [], vio = false
  const flush = () => {
    if (curSize && curPiece && lineas.length) {
      const cad = _stitch(lineas)
      if (cad.length) {
        const segs = _contornoSuave(cad[0])
        if (segs && _bboxSegs(segs)) {
          const bb = _bboxSegs(segs)
          if ((bb[2] - bb[0]) > 0.3 && (bb[3] - bb[1]) > 0.3) {
            if (!orden.includes(curSize)) orden.push(curSize)
            if (!reg.has(curPiece)) reg.set(curPiece, new Map())
            reg.get(curPiece).set(curSize, segs)
          }
        }
      }
    }
    lineas = []
  }
  for (const e of msp) {
    if (e.type === 'TEXT') {
      const s = pyStrip(String(e.text)), low = s.toLowerCase()
      if (low.startsWith('size:')) { flush(); curSize = _despues(s, 5); vio = true }
      else if (low.startsWith('piece name:')) { curPiece = _sinArroba(_despues(s, 11)); vio = true }
    } else if (e.type === 'LINE') lineas.push(e)
  }
  flush()
  if (!vio || !reg.size) return null
  const piezas = [...reg].map(([nombre, talles]) => ({ nombre, talles }))
  return [piezas, orden]
}

// ── 1) Optitex/AAMA por textos Size:/Piece Name: ──────────────────────────────
function _parseOptitex(msp) {
  let curSize = null, curPiece = null
  const reg = new Map(), ordenTalles = []
  let vioTextos = false
  for (const e of msp) {
    if (e.type === 'TEXT') {
      const s = pyStrip(String(e.text))
      if (s.toLowerCase().startsWith('size:')) { curSize = _despues(s, 5); vioTextos = true }
      else if (s.toLowerCase().startsWith('piece name:')) { curPiece = _sinArroba(_despues(s, 11)); vioTextos = true }
      continue
    }
    const segs = _segsDe(e)
    if (segs === null || !curPiece || !curSize) continue
    if (!ordenTalles.includes(curSize)) ordenTalles.push(curSize)
    if (!reg.has(curPiece)) reg.set(curPiece, new Map())
    reg.get(curPiece).set(curSize, segs)
  }
  if (!vioTextos || !reg.size) return null
  const piezas = [...reg].map(([nombre, talles]) => ({ nombre, talles }))
  return [piezas, ordenTalles]
}

// ── 2) genérico: contornos por posición, talle del layer ──────────────────────
function _solapan(a, b) {
  const [ax0, ay0, ax1, ay1] = a, [bx0, by0, bx1, by1] = b
  const ix0 = Math.max(ax0, bx0), iy0 = Math.max(ay0, by0), ix1 = Math.min(ax1, bx1), iy1 = Math.min(ay1, by1)
  if (ix1 <= ix0 || iy1 <= iy0) return false
  const inter = (ix1 - ix0) * (iy1 - iy0)
  const menor = Math.min((ax1 - ax0) * (ay1 - ay0), (bx1 - bx0) * (by1 - by0)) || 1
  return inter / menor > 0.55
}

function _textoCercano(textos, bb) {
  const [x0, y0, x1, y1] = bb, mx = (x1 - x0) * 0.15 + 1, my = (y1 - y0) * 0.15 + 1
  const cand = textos.filter((t) => x0 - mx <= t[1] && t[1] <= x1 + mx && y0 - my <= t[2] && t[2] <= y1 + my)
  if (!cand.length) return ''
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2
  const d = (t) => Math.pow(t[1] - cx, 2) + Math.pow(t[2] - cy, 2)
  return cand.map((t, i) => [d(t), i, t]).sort((a, b) => (a[0] - b[0]) || (a[1] - b[1]))[0][2][0]
}

const _area = (c) => (c.bb[2] - c.bb[0]) * (c.bb[3] - c.bb[1])
function _parseGenerico(doc) {
  const msp = doc.modelspace
  const contornos = []
  for (const e of msp) {
    const segs = _segsDe(e)
    if (segs) contornos.push({ segs, layer: e.layer || '0', bb: _bboxSegs(segs) })
  }
  for (const ins of msp.filter((e) => e.type === 'INSERT')) {
    try {
      for (const e of virtualEntities(ins, doc.blocks, doc.omitidas)) {
        const segs = _segsDe(e)
        if (segs) contornos.push({ segs, layer: e.layer || '0', bb: _bboxSegs(segs) })
      }
    } catch { /* como Python: un bloque roto no frena el resto */ }
  }
  if (!contornos.length) return null
  const textos = []
  for (const e of msp) {
    if (e.type !== 'TEXT' && e.type !== 'MTEXT') continue
    try {
      const s = e.type === 'MTEXT' ? plainMtext(e.text) : e.text
      const p = e.insert
      if (s && pyStrip(String(s))) textos.push([pyStrip(String(s)), Number(p[0]), Number(p[1])])
    } catch { /* nada */ }
  }
  const grupos = []
  // sorted(key=-area): estable
  const ordenados = contornos.map((c, i) => [-_area(c), i, c]).sort((a, b) => (a[0] - b[0]) || (a[1] - b[1])).map((x) => x[2])
  for (const c of ordenados) {
    let puesto = false
    for (const g of grupos) if (_solapan(g[0].bb, c.bb)) { g.push(c); puesto = true; break }
    if (!puesto) grupos.push([c])
  }
  const piezas = [], orden = []
  for (const g0 of grupos) {
    const g = g0.map((c, i) => [_area(c), i, c]).sort((a, b) => (a[0] - b[0]) || (a[1] - b[1])).map((x) => x[2])
    const nombre = _textoCercano(textos, g[g.length - 1].bb)
    const tal = new Map()
    g.forEach((c, i) => {
      const lay = pyStrip(String(c.layer || ''))
      const t = (lay && lay !== '0' && Array.from(lay).length <= 6) ? lay : `T${i + 1}`
      if (!orden.includes(t)) orden.push(t)
      tal.set(t, c.segs)
    })
    piezas.push({ nombre, talles: tal })
  }
  return [piezas, orden]
}

// ── construir el PDF a TAMAÑO REAL 1:1 y TAL CUAL VIENE (coords originales del DXF) ──
const f32 = Math.fround
function _construirPdf(mupdf, piezas, ordenTalles, escalaCm) {
  const S = CM * escalaCm
  const MARG = 4 * CM
  let minX = 1e18, minY = 1e18, maxX = -1e18, maxY = -1e18
  for (const p of piezas) {
    for (const segs of p.talles.values()) {
      const bb = _bboxSegs(segs)
      if (bb) { minX = Math.min(minX, bb[0]); minY = Math.min(minY, bb[1]); maxX = Math.max(maxX, bb[2]); maxY = Math.max(maxY, bb[3]) }
    }
  }
  const PW = MARG * 2 + (maxX - minX) * S
  const PH = MARG * 2 + (maxY - minY) * S

  const doc = new mupdf.PDFDocument()
  try {
    // `_format_g` = el `%g` de MuPDF: se lo pide al propio mupdf
    const g = (v) => { const o = doc.newReal(v); const s = o.toString(); try { o.destroy() } catch { /* nada */ } return s }
    // `page.mediabox_size.y` es float32 (el MediaBox vive en floats); `~page.transformation_matrix`
    // = (1, 0, 0, -1, -0, H32). `Point * Matrix` es `fz_transform_point` en float32, y después
    // `JM_TUPLE`: round(x, 5), o 0 si |x| < 1e-4.
    const H32 = f32(PH)
    const jm = (x) => (Math.abs(x) >= 1e-4 ? pyRound(x, 5) : 0)
    const pt = (x, y) => {
      const xf = f32(x), yf = f32(y)
      const xp = f32(f32(f32(xf * 1) + f32(yf * 0)) + -0)
      const yp = f32(f32(f32(xf * 0) + f32(yf * -1)) + H32)
      return [jm(xp), jm(yp)]
    }
    const P = (x, y) => [MARG + (x - minX) * S, PH - MARG - (y - minY) * S]   // DXF (y arriba) → página

    // fondo blanco: `page.draw_rect(Rect(0, 0, PW, PH), color=None, fill=(1, 1, 1))`
    const bl = pt(0, PH)
    let contenido = `\nq\n${g(bl[0])} ${g(bl[1])} ${g(jm(PW))} ${g(jm(PH))} re\nh\n1 1 1 rg f\nQ\n`

    const ocgs = new Map()           // talle → objeto OCG (todos, en orden, como `add_ocg`)
    const props = new Map()          // talle → nombre /MCn (sólo los que dibujan, por orden de uso)
    const verde = `${g(0.16)} ${g(0.62)} ${g(0.42)} RG `
    for (const t of ordenTalles) {
      const ocg = doc.newDictionary()
      ocg.put('Type', doc.newName('OCG'))
      ocg.put('Name', doc.newString(String(t)))
      const intent = doc.newArray(); intent.push(doc.newName('View')); ocg.put('Intent', intent)
      const ci = doc.newDictionary(); ci.put('Creator', doc.newString('TIZADA PRO')); ci.put('Subtype', doc.newName('Artwork'))
      const usage = doc.newDictionary(); usage.put('CreatorInfo', ci); ocg.put('Usage', usage)
      ocgs.set(t, doc.addObject(ocg))
    }
    for (const t of ordenTalles) {
      for (const p of piezas) {
        const segs = p.talles.get(t)
        if (!segs) continue
        // Shape: `draw_line` escribe `m` sólo si el último punto no es EXACTAMENTE el mismo
        let cur = null, ini = null, last = null, dibujo = false, drawCont = ''
        const linea = (p1, p2) => {
          if (!(last && last[0] === p1[0] && last[1] === p1[1])) { const a = pt(p1[0], p1[1]); drawCont += `${g(a[0])} ${g(a[1])} m\n` }
          const b = pt(p2[0], p2[1]); drawCont += `${g(b[0])} ${g(b[1])} l\n`
          last = p2
        }
        const bezier = (p1, p2, p3, p4) => {
          if (!(last && last[0] === p1[0] && last[1] === p1[1])) { const a = pt(p1[0], p1[1]); drawCont += `${g(a[0])} ${g(a[1])} m\n` }
          const b = pt(p2[0], p2[1]), c = pt(p3[0], p3[1]), d = pt(p4[0], p4[1])
          drawCont += `${g(b[0])} ${g(b[1])} ${g(c[0])} ${g(c[1])} ${g(d[0])} ${g(d[1])} c\n`
          last = p4
        }
        for (const s of segs) {
          const op = s[0]
          if (op === 'm') { cur = ini = P(s[1], s[2]) }
          else if (op === 'l' && cur !== null) { const nxt = P(s[1], s[2]); linea(cur, nxt); cur = nxt; dibujo = true }
          else if (op === 'c' && cur !== null) { const c1 = P(s[1], s[2]), c2 = P(s[3], s[4]), fin = P(s[5], s[6]); bezier(cur, c1, c2, fin); cur = fin; dibujo = true }
          else if (op === 'h' && cur !== null && ini !== null) {
            if (Math.abs(cur[0] - ini[0]) > 1e-6 || Math.abs(cur[1] - ini[1]) > 1e-6) linea(cur, ini)
            cur = ini; dibujo = true
          }
        }
        if (dibujo) {
          // finish(color=verde, width=1.0, closePath=False, oc=oc)
          if (!props.has(t)) props.set(t, `MC${props.size}`)
          contenido += `\nq\n/OC /${props.get(t)} BDC\n${drawCont}${verde}S\nEMC\nQ\n`
        }
      }
    }

    // la página: /Resources /Properties → los OCG usados; /OCProperties en el catálogo
    const res = doc.newDictionary()
    if (props.size) {
      const pd = doc.newDictionary()
      for (const [t, nombre] of props) pd.put(nombre, ocgs.get(t))
      res.put('Properties', pd)
    }
    const page = doc.addPage([0, 0, PW, PH], 0, res, new TextEncoder().encode(contenido))
    doc.insertPage(doc.countPages(), page)
    if (ocgs.size) {
      const lista = () => { const a = doc.newArray(); for (const o of ocgs.values()) a.push(o); return a }
      const d = doc.newDictionary()
      d.put('ON', lista()); d.put('OFF', doc.newArray()); d.put('Order', lista()); d.put('RBGroups', doc.newArray())
      const ocp = doc.newDictionary()
      ocp.put('OCGs', lista()); ocp.put('D', d)
      doc.getTrailer().get('Root').put('OCProperties', ocp)
    }

    // nombres en el orden que numera detectar_piezas (bbox x0,y0 en coords de página)
    const _key = (p) => {
      const allb = [...p.talles.values()].map((segs) => _bboxSegs(segs)).filter((b) => b)
      const x0 = Math.min(...allb.map((b) => b[0])), y1 = Math.max(...allb.map((b) => b[3]))
      return [pyRound(MARG + (x0 - minX) * S, 1), pyRound(PH - MARG - (y1 - minY) * S, 1)]
    }
    const nombres = piezas.map((p, i) => [_key(p), i, p]).sort((a, b) => compararTuplas(a[0], b[0]) || (a[1] - b[1])).map((x) => x[2].nombre)

    // CORRESPONDENCIA EXACTA por talle: indices[talle][i] = nombre DXF de la pieza i (mismo filtro
    // de tamaño y mismo orden que `extraer_piezas_mesa`)
    const indices = {}
    for (const t of ordenTalles) {
      const entradas = []
      for (const p of piezas) {
        const segs = p.talles.get(t)
        if (!segs) continue
        const bb = _bboxSegs(segs)
        if (!bb) continue
        const x0 = MARG + (bb[0] - minX) * S
        const y0 = PH - MARG - (bb[3] - minY) * S
        const wCm = (bb[2] - bb[0]) * S / CM
        const hCm = (bb[3] - bb[1]) * S / CM
        if (wCm * hCm < 10.0 || Math.min(wCm, hCm) < 1.0) continue
        entradas.push([[pyRound(x0, 1), pyRound(y0, 1)], p.nombre || ''])
      }
      indices[t] = entradas.map((e, i) => [e, i]).sort((a, b) => compararTuplas(a[0][0], b[0][0]) || (a[1] - b[1])).map((x) => x[0][1])
    }

    const out = doc.saveToBuffer('garbage=3,compress').asUint8Array().slice()
    const resumen = {
      piezas: piezas.length, talles: ordenTalles.slice(),
      nombres_detectados: nombres.filter((n) => n), nombres,
      indices, escala_pdf: 1.0,
    }
    return { pdf: out, resumen }
  } finally {
    try { doc.destroy() } catch { /* nada */ }
  }
}

/**
 * Lee un DXF de moldería y devuelve `{pdf, resumen, omitidas}` — PDF con capa por talle.
 * `omitidas` lista lo que ezdxf hubiera transformado dentro de un bloque y acá no (raro).
 */
export function dxfAPdf(mupdf, bytes) {
  const doc = leerDXF(bytes)
  doc.omitidas = []
  const msp = doc.modelspace
  const parsed = _parseOptitex(msp) || _parseOptitexLineas(msp) || _parseGenerico(doc)
  if (!parsed) throw new Error('El DXF no trae contornos de piezas reconocibles.')
  const [piezas, ordenTalles] = parsed
  const escala = _escalaCm(doc, piezas)
  const r = _construirPdf(mupdf, piezas, ordenTalles, escala)
  r.omitidas = doc.omitidas
  return r
}
