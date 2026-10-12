// MARCAS DE TIRAS de un molde a medida (MAPA 639, formas MAPA 645). Módulo chico: lo usan el motor de
// piezas (`pieza/base.js` → `opsTiras`) y los visores de la pantalla.
import { margenUniforme, geoTriangulo, solapaTri, normForma, normOrientacion } from './formas.js'

const medioTiras = (n, L) => {
  if (n === 1) return [L / 2]
  const out = []
  for (let k = 1; k <= n - 2; k++) out.push(L * k / (n - 1))
  return out
}

/** Las marcas de un CÍRCULO (`lados.alrededor`, parejas, empezando arriba) o de un TRIÁNGULO (`lados.base`
 *  y `lados.laterales`, contando las puntas). Gemelo EXACTO: `_segmentos_tiras_forma` de motor_pedido.py. */
function segmentosTirasForma(W, H, m, L, forma, orientacion, diseno, recorte = true) {
  const mm = margenUniforme(m)
  const n = (k, tope = 50) => Math.max(0, Math.min(tope, Math.trunc(Number(L[k]) || 0)))
  const s = []
  if (!(mm > 0)) return s
  if (forma === 'circulo') {
    const N = n('alrededor', 200)
    const cx = W / 2, cy = H / 2, R = Math.min(W, H) / 2
    if (!(R - mm > 0)) return s
    for (let k = 0; k < N; k++) {
      const th = Math.PI / 2 + 2 * Math.PI * k / N
      const c = Math.cos(th), si = Math.sin(th)
      s.push([cx + R * c, cy + R * si, cx + (R - mm) * c, cy + (R - mm) * si])
    }
    return s
  }
  // TRIÁNGULO EN INGLETE (MAPA 649): la geometría sale del DISEÑO (`diseno` = [w, h], mismas unidades);
  // las puntas no llevan marca (el corte llega a la punta de la guía: ya está marcada) pero CUENTAN para
  // repartir las del medio, que van de la solapa a la guía y se angostan con el recorte cerca de la punta
  if (!diseno) return s
  const g = geoTriangulo(Number(diseno[0]), Number(diseno[1]), mm, orientacion, recorte)
  if (!(g.W > 0 && g.H > 0)) return s
  const sx = W / g.W, sy = H / g.H
  const G = g.guia
  const nb = n('base'), nl = n('laterales')
  if (!recorte) {
    // OVERLOCK (MAPA 652): las puntas están enteras → una por punta, en diagonal (de la del total a la de la guía)
    const P = g.pol
    for (const [i, ok] of [[0, nb >= 2 || nl >= 2], [1, nb >= 2 || nl >= 2], [2, nl >= 2]]) {
      if (ok) s.push([P[i][0] * sx, P[i][1] * sy, G[i][0] * sx, G[i][1] * sy])
    }
  }
  for (const [i, c] of [[0, nb], [1, nl], [2, nl]]) {
    if (c <= 0) continue
    const px = G[i][0], py = G[i][1]
    // la solapa con sus recortes (`solapaTri`): a `d` de la punta tiene d / ca de ancho
    const { ux, uy, nx, ny, L: Lg, ca, cb, tt } = solapaTri(G, i, mm)
    for (const d of medioTiras(c, Lg)) {
      const an = recorte ? Math.min(tt, ca > 0 ? d / ca : Infinity, cb > 0 ? (Lg - d) / cb : Infinity) : mm
      if (!(an > 0)) continue
      const ex = px + ux * d, ey = py + uy * d
      s.push([(ex + nx * an) * sx, (ey + ny * an) * sy, ex * sx, ey * sy])
    }
  }
  return s
}

/**
 * MARCAS DE TIRAS (molde a medida, MAPA 639 y 641): las líneas del borde de la pieza hasta la guía del diseño.
 * `W` × `H` con el origen abajo a la izquierda y la y hacia ARRIBA (como el PDF); `m` = el margen
 * `{arriba, abajo, izq, der}` en las mismas unidades; `lados` = cuántas marcas en cada lado CONTANDO LAS
 * DOS PUNTAS (0 = ese lado sin tiras; 1 = una en el medio). La de la esquina va en diagonal del vértice de
 * la pieza al de la guía y, si la piden los dos lados, va una sola. Primero las esquinas (abajo-izq,
 * abajo-der, arriba-der, arriba-izq), después lo de adentro de cada lado (izq, der, abajo, arriba).
 * Devuelve `[[x1, y1, x2, y2], …]`. Gemelo EXACTO: `_segmentos_tiras` de motor_pedido.py.
 */
export function segmentosTiras(W, H, m, lados, forma = 'rectangulo', orientacion = 'abajo', diseno = null, recorte = null) {
  const L = (lados && typeof lados === 'object') ? lados : {}
  // `recorte` sin decir: el triángulo recortado (dobladillo, MAPA 650) y el rectángulo entero (lo de antes)
  if (normForma(forma) !== 'rectangulo') return segmentosTirasForma(W, H, m, L, normForma(forma), normOrientacion(orientacion), diseno, recorte !== false)
  const mi = Number(m.izq) || 0, md = Number(m.der) || 0, ma = Number(m.arriba) || 0, mb = Number(m.abajo) || 0
  const n = (k) => Math.max(0, Math.trunc(Number(L[k]) || 0))
  const nI = n('izq'), nD = n('der'), nA = n('arriba'), nB = n('abajo')
  const medioR = (c, Lg) => (c === 1 ? [Lg / 2] : Array.from({ length: Math.max(0, c - 2) }, (_, i) => Lg * (i + 1) / (c - 1)))
  if (recorte === true) {
    // RECTÁNGULO CON LAS ESQUINAS RECORTADAS (MAPA 653): la esquina no lleva marca (el corte ya la marca)
    // pero cuenta; las del medio se reparten sobre la GUÍA (el borde terminado), de esquina a esquina
    const s = []
    const gx0 = mi, gy0 = mb, Lh = W - mi - md, Lv = H - ma - mb
    if (mi > 0) for (const y of medioR(nI, Lv)) s.push([0, gy0 + y, mi, gy0 + y])
    if (md > 0) for (const y of medioR(nD, Lv)) s.push([W, gy0 + y, W - md, gy0 + y])
    if (mb > 0) for (const x of medioR(nB, Lh)) s.push([gx0 + x, 0, gx0 + x, mb])
    if (ma > 0) for (const x of medioR(nA, Lh)) s.push([gx0 + x, H, gx0 + x, H - ma])
    return s
  }
  const pide = (c, mg) => c >= 2 && mg > 0          // con 2 o más, las puntas son del lado
  const s = []
  for (const [ok, sg] of [[pide(nI, mi) || pide(nB, mb), [0, 0, mi, mb]],
                          [pide(nD, md) || pide(nB, mb), [W, 0, W - md, mb]],
                          [pide(nD, md) || pide(nA, ma), [W, H, W - md, H - ma]],
                          [pide(nI, mi) || pide(nA, ma), [0, H, mi, H - ma]]]) {
    if (ok && (sg[0] !== sg[2] || sg[1] !== sg[3])) s.push(sg)
  }
  const medio = (c, Lg) => {
    if (c === 1) return [Lg / 2]
    const out = []
    for (let k = 1; k <= c - 2; k++) out.push(Lg * k / (c - 1))
    return out
  }
  if (mi > 0) for (const y of medio(nI, H)) s.push([0, y, mi, y])
  if (md > 0) for (const y of medio(nD, H)) s.push([W, y, W - md, y])
  if (mb > 0) for (const x of medio(nB, W)) s.push([x, 0, x, mb])
  if (ma > 0) for (const x of medio(nA, W)) s.push([x, H, x, H - ma])
  return s
}
