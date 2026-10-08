// MARCAS DE TIRAS de un molde a medida (MAPA 639). Módulo aparte y sin dependencias: lo usan el motor
// de piezas (`pieza/base.js` → `opsTiras`) y los visores de la pantalla.

/**
 * MARCAS DE TIRAS (molde a medida, MAPA 639 y 641): las líneas del borde de la pieza hasta la guía del diseño.
 * `W` × `H` con el origen abajo a la izquierda y la y hacia ARRIBA (como el PDF); `m` = el margen
 * `{arriba, abajo, izq, der}` en las mismas unidades; `lados` = cuántas marcas en cada lado CONTANDO LAS
 * DOS PUNTAS (0 = ese lado sin tiras; 1 = una en el medio). La de la esquina va en diagonal del vértice de
 * la pieza al de la guía y, si la piden los dos lados, va una sola. Primero las esquinas (abajo-izq,
 * abajo-der, arriba-der, arriba-izq), después lo de adentro de cada lado (izq, der, abajo, arriba).
 * Devuelve `[[x1, y1, x2, y2], …]`. Gemelo EXACTO: `_segmentos_tiras` de motor_pedido.py.
 */
export function segmentosTiras(W, H, m, lados) {
  const mi = Number(m.izq) || 0, md = Number(m.der) || 0, ma = Number(m.arriba) || 0, mb = Number(m.abajo) || 0
  const L = (lados && typeof lados === 'object') ? lados : {}
  const n = (k) => Math.max(0, Math.trunc(Number(L[k]) || 0))
  const nI = n('izq'), nD = n('der'), nA = n('arriba'), nB = n('abajo')
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
