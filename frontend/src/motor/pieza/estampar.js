// EL ESTAMPADO DE UNA PIEZA: nombre, número, talle y la etiqueta del sistema — PLAN_NAVEGADOR.md,
// etapa 3 (camino B). Traducción de la parte por prenda de `motor_pedido.generar_pieza`, de
// `_eops_borde` (texto sobre el borde), `_eops_zonas`/`_eops_tramo` (por zonas), `_ancla_etiqueta`
// y `_color_op`. Devuelve el bloque `q <clip> W n … Q` que va después de la base; el contrato lo
// compara letra por letra con el de Python.
//
// Las tipografías llegan ya abiertas (`texto/curvas.js`, la traducción de `FuenteCurvas`):
// `fuente(nombrePs, {sinAlias})` devuelve una con `opsTexto`, `anchoTexto`, `sizeParaAlto`,
// `faltantes` y `prestados`.
import { pyFixed, pyG, pyRound } from '../py.js'
import { normNombre, normGenerico } from '../nombres.js'
export { normNombre, normGenerico }
import { MM } from './base.js'

// ─── nombres ─────────────────────────────────────────────────────────────────────────────────
const RE_ETQ = /\s+\d+\s*$/
const CAMPO_ALIAS = { '00': 'numero', nro: 'numero', num: 'numero', jugador: 'nombre', apellido: 'nombre' }
export const PREFIJO_CAMPO_FUENTE = '@campo:'

/** `clave_fuente_campo`: la clave del reemplazo de UN campo (`@campo:numero`). */
export function claveFuenteCampo(campo) {
  const n = normNombre(campo)
  return PREFIJO_CAMPO_FUENTE + normNombre(CAMPO_ALIAS[n] || campo)
}

/** `fuente_de_campo`: `[nombre, elegidaPorCampo]`. */
export function fuenteDeCampo(campo, fuenteOriginal, alias) {
  const elegida = (alias || {})[claveFuenteCampo(campo)]
  if (elegida) return [elegida, true]
  return [fuenteOriginal, false]
}

/** `_color_op`: el color del placeholder en su espacio nativo (k/rg/g), o sRGB→CMYK. */
export function colorOp(pl) {
  const cn = pl.colorn
  if (cn) return cn[1].map((v) => pyG(Number(v))).join(' ') + ' ' + cn[0]
  const rgb = Number(pl.color || 0)
  const r = ((rgb >> 16) & 255) / 255, g = ((rgb >> 8) & 255) / 255, b = (rgb & 255) / 255
  const k = 1 - Math.max(r, g, b)
  let c = 0, m = 0, y = 0
  if (k < 1) { c = (1 - r - k) / (1 - k); m = (1 - g - k) / (1 - k); y = (1 - b - k) / (1 - k) }
  return `${pyFixed(c, 4)} ${pyFixed(m, 4)} ${pyFixed(y, 4)} ${pyFixed(k, 4)} k`
}

// ─── el contorno aplanado (compartido por el borde y las zonas) ──────────────────────────────
const hypot = Math.hypot

/** `bisect.bisect_right` sobre una lista ordenada de números. */
function bisectRight(a, x) {
  let lo = 0, hi = a.length
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (x < a[mid]) hi = mid
    else lo = mid + 1
  }
  return lo
}

/** Python `%` con signo del divisor. */
const pmod = (a, n) => ((a % n) + n) % n

function aplanar(cont, S, x0, y0, B) {
  const P = (vx, vy) => [vx * S + B - x0 * S, vy * S + B - y0 * S]
  const pts = []
  let cur = null, ini = null
  for (const s of cont.segmentos) {
    const op = s[0]
    if (op === 'm') { cur = P(s[1], s[2]); pts.push(cur); ini = cur }
    else if (op === 'l') { cur = P(s[1], s[2]); pts.push(cur) }
    else if (op === 'c') {
      const p0 = cur || P(s[1], s[2]), p1 = P(s[1], s[2]), p2 = P(s[3], s[4]), p3 = P(s[5], s[6])
      for (let k = 1; k <= 8; k++) {
        const u = k / 8.0, mu = 1 - u
        pts.push([mu * mu * mu * p0[0] + 3 * mu * mu * u * p1[0] + 3 * mu * u * u * p2[0] + u * u * u * p3[0],
                  mu * mu * mu * p0[1] + 3 * mu * mu * u * p1[1] + 3 * mu * u * u * p2[1] + u * u * u * p3[1]])
      }
      cur = p3
    } else if (op === 're') {
      const [X, Y, Wd, Ht] = s.slice(1, 5)
      const q = [P(X, Y), P(X + Wd, Y), P(X + Wd, Y + Ht), P(X, Y + Ht), P(X, Y)]
      pts.push(...q); cur = q[0]; ini = q[0]
    } else if (op === 'h') {
      if (ini && (cur[0] !== ini[0] || cur[1] !== ini[1])) pts.push(ini)
      cur = ini
    }
  }
  if (pts.length < 3) return null
  const cum = [0.0]
  for (let i = 1; i < pts.length; i++) cum.push(cum[cum.length - 1] + hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
  const total = cum[cum.length - 1]
  if (total <= 1) return null
  const at = (l) => {
    l = pmod(l, total)
    let i = bisectRight(cum, l)
    if (i <= 0) return pts[0]
    if (i >= pts.length) i = pts.length - 1
    const l0 = cum[i - 1], l1 = cum[i]
    const f = l1 > l0 ? (l - l0) / (l1 - l0) : 0.0
    return [pts[i - 1][0] + f * (pts[i][0] - pts[i - 1][0]), pts[i - 1][1] + f * (pts[i][1] - pts[i - 1][1])]
  }
  const dir = (l) => { const a = at(l - 1.0), b = at(l + 1.0); return Math.atan2(b[1] - a[1], b[0] - a[0]) }
  return { pts, cum, total, at, dir }
}

/** El tramo [a, b] con la baseline apoyada hacia adentro; devuelve `{lat, ldir, lt}` o null. */
function tramo(at, dir, a, b, cx, cy, size) {
  const segLen = b - a
  if (segLen <= 1) return null
  const nf = Math.max(8, Math.min(400, Math.trunc(segLen)))
  let segp = []
  for (let k = 0; k <= nf; k++) segp.push(at(a + segLen * k / nf))
  const md = at(a + segLen / 2), an = dir(a + segLen / 2)
  const up = [-Math.sin(an), Math.cos(an)]
  if ((up[0] * (cx - md[0]) + up[1] * (cy - md[1])) < 0) segp.reverse()
  const offIn = 0.18 * MM
  const n = segp.length, base = segp.slice()
  segp = []
  for (let i = 0; i < n; i++) {
    const a2 = base[Math.max(0, i - 1)], b2 = base[Math.min(n - 1, i + 1)]
    let tx = b2[0] - a2[0], ty = b2[1] - a2[1]
    const tl = hypot(tx, ty) || 1.0
    tx /= tl; ty /= tl
    segp.push([base[i][0] + (-ty) * offIn, base[i][1] + tx * offIn])
  }
  const lc = [0.0]
  for (let i = 1; i < segp.length; i++) lc.push(lc[lc.length - 1] + hypot(segp[i][0] - segp[i - 1][0], segp[i][1] - segp[i - 1][1]))
  const lt = lc[lc.length - 1]
  if (lt <= 1) return null
  const lat = (d) => {
    d = Math.max(0.0, Math.min(lt, d))
    let i = bisectRight(lc, d)
    if (i <= 0) return segp[0]
    if (i >= segp.length) i = segp.length - 1
    const d0 = lc[i - 1], d1 = lc[i]
    const f = d1 > d0 ? (d - d0) / (d1 - d0) : 0.0
    return [segp[i - 1][0] + f * (segp[i][0] - segp[i - 1][0]), segp[i - 1][1] + f * (segp[i][1] - segp[i - 1][1])]
  }
  const ldir = (d) => {
    const w = Math.max(1.5, size * 0.6)
    const p = lat(Math.max(0.0, d - w)), q = lat(Math.min(lt, d + w))
    return Math.atan2(q[1] - p[1], q[0] - p[0]) * 180 / Math.PI
  }
  return { lat, ldir, lt, segLen }
}

function glifoAGlifo(tr, texto, size, align, fetq) {
  const aw = fetq.anchoTexto(texto, size)
  const mg = Math.min(tr.segLen * 0.06, 2.5 * MM)
  let d
  if (align === 'izquierda') d = mg
  else if (align === 'derecha') d = Math.max(mg, tr.lt - mg - aw)
  else d = Math.max(0.0, tr.lt / 2 - aw / 2)
  const parts = []
  for (const ch of texto) {
    const cw = fetq.anchoTexto(ch, size)
    const p = tr.lat(d)
    parts.push(fetq.opsTexto(ch, size, p[0], p[1], tr.ldir(d)))
    d += cw
  }
  return parts.join('\n')
}

/** `_eops_borde`: el texto siguiendo el segmento del contorno que contiene la posición. */
export function eopsBorde(cont, S, x0, y0, B, rx, ry, t, texto, size, align, fetq) {
  const A = aplanar(cont, S, x0, y0, B)
  if (!A) return null
  const { pts, total, at, dir } = A
  let bestL
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1])
  const minx = Math.min(...xs), maxx = Math.max(...xs), miny = Math.min(...ys), maxy = Math.max(...ys)
  if (rx != null && ry != null && maxx > minx && maxy > miny) {
    const ax = minx + Number(rx) * (maxx - minx)
    const ay = maxy - Number(ry) * (maxy - miny)
    const ns = Math.max(80, Math.min(900, Math.trunc(total / 2)))
    bestL = 0.0
    let bestd = 1e18
    for (let i = 0; i <= ns; i++) {
      const L = total * i / ns, p = at(L)
      const d = (p[0] - ax) ** 2 + (p[1] - ay) ** 2
      if (d < bestd) { bestd = d; bestL = L }
    }
  } else {
    bestL = pmod((t || 0.0) * total, total)
  }
  const wd = Math.max(2.5, total / 160), st = Math.max(0.8, total / 600)
  const turn = (l) => Math.abs(pmod(dir(l + wd) - dir(l - wd) + Math.PI, 2 * Math.PI) - Math.PI)
  const walk = (sg) => {
    let d = st
    while (d < total * 0.48) {
      if (turn(bestL + sg * d) > 0.5) break
      d += st
    }
    return d
  }
  const a = bestL - walk(-1), b = bestL + walk(1)
  if (b - a <= 1) return null
  let cx = 0, cy = 0
  for (const p of pts) { cx += p[0]; cy += p[1] }
  cx /= pts.length; cy /= pts.length
  const tr = tramo(at, dir, a, b, cx, cy, size)
  if (!tr) return null
  return glifoAGlifo(tr, texto, size, align, fetq)
}

/** `_eops_zonas`: un texto por zona entre las esquinas elegidas. */
export function eopsZonas(cont, S, x0, y0, B, puntos, conts, size, alignDef, fetq, talle, pieza, nro, sep) {
  const A = aplanar(cont, S, x0, y0, B)
  if (!A) return null
  const { pts, total, at, dir } = A
  const h = Math.max(2.5, total / 160)
  const dirh = (l) => { const a = at(l - h), b = at(l + h); return Math.atan2(b[1] - a[1], b[0] - a[0]) }
  const N = Math.max(120, Math.min(700, pyRound(total)))
  const step = total / N
  const turn = (l) => {
    const d0 = dirh(l - step * 1.5), d1 = dirh(l + step * 1.5)
    return Math.abs(pmod(d1 - d0 + Math.PI, 2 * Math.PI) - Math.PI)
  }
  const tn = []
  for (let i = 0; i < N; i++) tn.push(turn(i * step))
  const thr = 0.5
  const cor = []
  let i = 0
  while (i < N) {
    if (tn[i] > thr) {
      let j = i, best = i
      while (j < N + 5 && tn[j % N] > thr * 0.5) {
        if (tn[j % N] > tn[best % N]) best = j
        j += 1
      }
      cor.push(pmod((best % N) * step, total)); i = j
    } else {
      i += 1
    }
  }
  cor.sort((p, q) => p - q)
  const corners = []
  for (const c of cor) {
    if (!corners.length || Math.min(Math.abs(c - corners[corners.length - 1]), total - Math.abs(c - corners[corners.length - 1])) > total / 40) corners.push(c)
  }
  if (corners.length > 1 && Math.min(Math.abs(corners[0] - corners[corners.length - 1]), total - Math.abs(corners[0] - corners[corners.length - 1])) < total / 40) corners.pop()
  const snap = (tf) => {
    const L = pmod(Number(tf), 1.0) * total
    if (!corners.length) return L
    let mejor = corners[0], md = Infinity
    for (const c of corners) {
      const d = Math.min(Math.abs(c - L), total - Math.abs(c - L))
      if (d < md) { md = d; mejor = c }        // `min(key=…)`: gana el primero en empate
    }
    return mejor
  }
  const P = puntos.map(snap)
  if (P.length < 2) return null
  let cx = 0, cy = 0
  for (const p of pts) { cx += p[0]; cy += p[1] }
  cx /= pts.length; cy /= pts.length
  const out = []
  for (let idx = 0; idx < P.length; idx++) {
    const a = P[idx]
    let b = P[(idx + 1) % P.length]
    if (b <= a) b += total
    const c = idx < conts.length ? (conts[idx] || {}) : {}
    const mos = c.mostrar || {}
    const partes = []
    if (mos.talle) partes.push(String(talle))
    if (mos.pieza) partes.push(pieza)
    if (mos.numero) partes.push('#' + String(nro).padStart(2, '0'))
    if (c.texto) partes.push(String(c.texto))
    const txt = partes.join(sep)
    if (!txt) continue
    const alg = c.align || alignDef || 'centro'
    const tr = tramo(at, dir, a, b, cx, cy, size)
    if (!tr) continue
    const ops = glifoAGlifo(tr, txt, size, alg, fetq)
    if (ops) out.push(ops)
  }
  return out.length ? out.join('\n') : null
}

/** `_ancla_etiqueta`: el ancla en una posición relativa del bbox de la pieza (coords MuPDF). */
export function anclaEtiqueta(cont, posicion, sizePt) {
  const [x0, y0, x1, y1] = cont.bbox_mu
  const pos = posicion || {}
  const r = (k, d) => {
    const v = Number(pos[k] ?? d)
    return Number.isFinite(v) ? Math.max(0.0, Math.min(1.0, v)) : d
  }
  const rx = r('rx', 0.5), ry = r('ry', 0.92)
  return { x: pyRound(x0 + rx * (x1 - x0), 1), y: pyRound(y0 + ry * (y1 - y0), 1),
           angulo: 0.0, size_pt: pyRound(sizePt, 2), fuente: 'Arial-BoldMT', h: 'centro' }
}

const colorCmyk = (vals, op) => vals.slice(0, 4).map((v) => pyG(Number(v))).join(' ') + ' ' + op

/**
 * El estampado de UNA prenda sobre UNA pieza. Devuelve el bloque de operadores.
 *   · `base`     — lo que devuelve `armarBase`;
 *   · `ph`       — los placeholders de la mesa (`pers[str(mesa)]`: `{campo: {..., por_talle}}`);
 *   · `persona`  — `{nombre, numero, talle, …}` de la prenda (la personalización de la fila);
 *   · `talle`, `pieza`, `nro`, `variante`, `grupo`;
 *   · `etiqueta` — la config de la etiqueta del sistema (`_etiqueta_de`);
 *   · `fuente(nombrePs, {sinAlias})` — abre una tipografía (o tira);
 *   · `alias`    — los reemplazos del pedido (`carpeta_fuentes.alias`);
 *   · `info`     — la entrada del registro de la pieza en ese talle (`ancla`, `pieza_idx`).
 * `avisos` (opcional) junta los caracteres prestados por tipografía, como el registro del server.
 */
export function estamparPieza({ base, ph, persona, talle, pieza, nro, variante = null, grupo = null,
                                etiqueta = null, fuente, alias = {}, info = {}, avisos = null,
                                separado = false, arteRect = null }) {
  const { clip, cont, x0, y0, x0m, y0m, Hp, S, B, bcActivo, W, H } = base
  const bloques = []
  const personaN = {}
  for (const [k, v] of Object.entries(persona || {})) personaN[normNombre(k)] = v
  if (ph && Object.keys(ph).length && Object.keys(personaN).length) {     // `if ph and persona_n`
    // ARTE SEPARADO (camino A): el placeholder vive en la mesa del arte y se escala con el diseño
    // (`sp = H / ha`, alto manda); `arteRect` = `arte_rect(_mesa_a)` = [x0, y0, ancho, alto].
    // Una pieza SIN mesa de arte (`mapeo_arte and not _mesa_a`) llega con `ph = {}` y sin
    // `arteRect`: nada que estampar, como en el Python (`ph = {}` antes de este bucle).
    let sp = 1.0, awArte = 0.0, ha = 1.0
    if (separado) {
      if (!arteRect) throw new Error('arte separado: falta `arteRect` (la mesa del arte de esta pieza)')
      const wa = Number(arteRect[2]); ha = Number(arteRect[3])
      sp = H / ha
      awArte = wa * sp
    }
    // `_T`: un punto del arte → coordenadas de la pieza (la misma transformación que el texto plano)
    const T = separado ? (px, py) => [B + (W - awArte) / 2 + px * sp, B + H - py * sp]
                       : (px, py) => [px - x0m + B, Hp - (py - y0m + B)]
    for (const [campo, pl0] of Object.entries(ph)) {
      const pl = ((pl0.por_talle || {})[String(talle)]) || pl0
      let texto = String(personaN[normNombre(campo)] ?? '').trim()
      if (normNombre(campo) !== 'talle') texto = texto.toUpperCase()
      if (texto === '') continue
      let fnom, fnomNombre
      try {
        const [nom, porCampo] = fuenteDeCampo(campo, pl.fuente, alias)
        fnomNombre = nom
        fnom = fuente(nom, { sinAlias: porCampo })
      } catch {
        continue                        // tipografía no disponible → no se estampa ESE campo
      }
      const size = separado ? pl.size * sp : pl.size
      // ¿el placeholder ORIGINAL va sobre una CURVA o tiene VARIAS LÍNEAS? Sus glifos trazan la
      // línea base: con arco (y varía) o salto de línea se reproduce fiel; si no, texto plano.
      const bp = pl.baseline_pts || []
      const size0 = pl.size
      let fiel = false
      if (bp.length >= 3) {
        const xs = bp.map((p) => p[0]), ys = bp.map((p) => p[1])
        const xr = Math.max(...xs) - Math.min(...xs)
        const curva = xr > 0 && (Math.max(...ys) - Math.min(...ys)) > 0.03 * xr
        let multi = false
        for (let i = 1; i < bp.length; i++) {
          if (Math.abs(bp[i][1] - bp[i - 1][1]) > 0.6 * size0 || (bp[i][0] - bp[i - 1][0]) < -0.4 * size0) { multi = true; break }
        }
        fiel = curva || multi
      }
      const fps = fnomNombre || pl.fuente || '?'
      if (avisos) {
        const prest = fnom.prestados(texto).filter((c) => !(avisos[fps] || new Set()).has(c))
        if (prest.length) { avisos[fps] = avisos[fps] || new Set(); prest.forEach((c) => avisos[fps].add(c)) }
      }
      const falta = fnom.faltantes(texto)
      if (falta.length) {
        const c = falta.map((x) => `«${x}»`).join(' ni ')
        throw new Error(`La tipografía «${fps}» no puede estampar ${c} de «${texto}», y la predeterminada tampoco. Sacá ${falta.length === 1 ? 'ese carácter' : 'esos caracteres'} del texto.`)
      }
      let ops
      if (fiel) {
        // (x, y, x0, x1) del arte → coords de la pieza (posición + bordes del renglón)
        const glifos = bp.map(([px, py, ex0, ex1]) => [...T(px, py), T(ex0, py)[0], T(ex1, py)[0]])
        ops = fnom.opsTextoFiel(texto, size, glifos)
      } else {
        // texto plano centrado en el placeholder (en el camino B `baseline_pts` siempre está vacío)
        let cxFinal, ty
        if (separado) {
          cxFinal = B + (W - awArte) / 2 + pl.cx * sp
          ty = B + (1 - pl.baseline_y / ha) * H
        } else {
          cxFinal = pl.cx - x0m + B
          ty = Hp - (pl.baseline_y - y0m + B)
        }
        ops = fnom.opsTexto(texto, size, cxFinal - fnom.anchoTexto(texto, size) / 2, ty)
      }
      const pas = pl.pasadas
      if (pas && pas.length) {
        for (const p of pas) {
          const c = p.color
          const vals = c[1].map((v) => pyG(Number(v))).join(' ')
          if (p.t === 'f') bloques.push(`q ${vals} ${c[0]}\n${ops}\nf\nQ\n`)
          else {
            const w = Number(p.w) * (separado ? sp : 1.0)          // a la escala del texto
            bloques.push(`q ${vals} ${String(c[0]).toUpperCase()}\n${pyFixed(w, 3)} w 1 j 1 J\n${ops}\nS\nQ\n`)
          }
        }
        continue
      }
      const tz = pl.trazo
      if (tz) {
        const sw = Number(tz[2]) * (separado ? sp : 1.0)
        const scol = tz[1].map((v) => pyG(Number(v))).join(' ') + ' ' + String(tz[0]).toUpperCase()
        bloques.push(`q ${scol}\n${pyFixed(sw, 3)} w 1 j 1 J\n${ops}\nS\nQ\n`)
        bloques.push(`q ${colorOp(pl)}\n${ops}\nf\nQ\n`)
      } else {
        bloques.push(`q ${colorOp(pl)}\n${ops}\nf\nQ\n`)
      }
    }
  }

  // ── la etiqueta del sistema ──
  const et = etiqueta || {}
  const piezaLimpia = pieza.replace(' (corta)', '').replace(' (larga)', '')
  const piezaTxt = piezaLimpia.replace(RE_ETQ, '').trim() || piezaLimpia
  const etOff = new Set((et.piezas_off || []).map(normGenerico))
  const etOn = (et.activo ?? true) && !etOff.has(normGenerico(piezaLimpia))
  const zonasN = {}
  for (const [k, v] of Object.entries(et.zonas || {})) zonasN[normGenerico(k)] = v
  const zna = zonasN[normGenerico(piezaLimpia)]
  const usaZonas = !!(etOn && zna && (zna.puntos || []).length >= 2)
  if (usaZonas) {
    let zeops
    try {
      const fetq = fuente('Arial-BoldMT')
      const esize = fetq.sizeParaAlto(Number(et.size_mm || 3.0) * MM)
      zeops = eopsZonas(cont, S, x0, y0, B, zna.puntos, zna.cont || [], esize, et.align || 'centro', fetq,
                        talle, piezaTxt, nro, et.separador === undefined ? '-' : (et.separador || '-'))
    } catch { zeops = null }
    if (zeops) {
      if (et.borde_activo ?? true) {
        const bcol = colorCmyk(et.borde_color || [0.01, 0.01, 0.01, 0.05], 'K')
        const bw = Number(et.borde_mm || 1.0) * MM
        bloques.push(`q 1 J 1 j ${pyFixed(bw, 2)} w ${bcol}\n${zeops}\nS\nQ\n`)
      }
      bloques.push(`q ${colorCmyk(et.color || [0.15, 0.15, 0.15, 0.30], 'k')}\n${zeops}\nf\nQ\n`)
    }
  }
  if (etOn && !usaZonas) {
    const mos = et.mostrar || { talle: true, pieza: true, numero: true }
    const partes = []
    if (mos.talle ?? true) partes.push(String(talle))
    if (mos.pieza ?? true) partes.push(piezaTxt)
    if (mos.numero ?? true) partes.push('#' + String(nro).padStart(2, '0'))
    const etTxt = partes.join(et.separador === undefined ? '-' : (et.separador || '-'))
    if (etTxt) {
      let fmet
      try { fmet = fuente('Arial-BoldMT') } catch { fmet = null }
      let esize = Number(et.size_mm || 3.0) * MM
      esize = fmet ? fmet.sizeParaAlto(esize) : esize / 0.72
      const posGlob = {}, posGrp = {}, posVar = {}, posVarGen = {}, posOtra = {}, posOtraGen = {}, posGlobPz = {}
      const setdefault = (o, k, v) => { if (!(k in o)) o[k] = v }
      for (const [k, v] of Object.entries(et.posiciones || {})) {
        if (k.includes('§')) {
          const i = k.indexOf('§')
          const g = k.slice(0, i), n = k.slice(i + 1)
          if (variante && g === variante) { posVar[normNombre(n)] = v; setdefault(posVarGen, normGenerico(n), v) }
          else if (grupo && g === grupo) posGrp[normGenerico(n)] = v
          else { setdefault(posOtra, normNombre(n), v); setdefault(posOtraGen, normGenerico(n), v) }
        } else {
          posGlobPz[normNombre(k)] = v
          setdefault(posGlob, normGenerico(k), v)
        }
      }
      const kn = normGenerico(piezaLimpia), knc = normNombre(piezaLimpia)
      const posi = posGlobPz[knc] || posVar[knc] || posVarGen[kn] || posGrp[kn] || posGlob[kn] || posOtra[knc] || posOtraGen[kn] || null
      let eops = null
      if (posi && posi.t != null) {
        const alg = posi.align || et.align || 'centro'
        try {
          const fetq = fuente('Arial-BoldMT')
          eops = eopsBorde(cont, S, x0, y0, B, posi.rx ?? null, posi.ry ?? null, Number(posi.t), etTxt, esize, alg, fetq, bcActivo)
        } catch { eops = null }
      }
      if (eops == null) {
        let a, ang
        if (posi) { a = anclaEtiqueta(cont, posi, esize); ang = -Number(posi.ang || 0) }
        else if (et.posicion || ('pieza_idx' in info)) { a = anclaEtiqueta(cont, et.posicion || {}, esize); ang = 0.0 }
        else { a = { ...info.ancla }; esize = a.size_pt; ang = a.angulo || 0 }
        const align = (posi || {}).align || et.align || a.h || 'centro'
        const fetq = fuente(a.fuente || 'Arial-BoldMT')
        const aw = fetq.anchoTexto(etTxt, esize)
        const ca = Math.cos(ang * Math.PI / 180), sa = Math.sin(ang * Math.PI / 180)
        const shift = align === 'centro' ? aw / 2 : (align === 'derecha' ? aw : 0)
        const px = a.x - x0m + B
        const py = Hp - (a.y - y0m + B)
        eops = fetq.opsTexto(etTxt, esize, px - shift * ca, py - shift * sa, ang)
      }
      if (et.borde_activo ?? true) {
        const bcol = colorCmyk(et.borde_color || [0.01, 0.01, 0.01, 0.05], 'K')
        const bw = Number(et.borde_mm || 1.0) * MM
        bloques.push(`q 1 J 1 j ${pyFixed(bw, 2)} w ${bcol}\n${eops}\nS\nQ\n`)
      }
      bloques.push(`q ${colorCmyk(et.color || [0.15, 0.15, 0.15, 0.30], 'k')}\n${eops}\nf\nQ\n`)
    }
  }
  return `q\n${clip}\nW n\n` + bloques.join('') + 'Q\n'
}
