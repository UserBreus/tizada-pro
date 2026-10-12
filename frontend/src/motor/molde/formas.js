// ── FORMAS DEL MOLDE A MEDIDA (MAPA 645) ─────────────────────────────────────────────────────────
// Pedido del usuario 2026-10-08: «lo mismo de los rectángulos, adaptalo para que se puedan hacer
// círculos y triángulos». La forma se elige EN CADA PEDIDO (`a_medida.forma` de la copia); el
// triángulo es isósceles con la punta hacia donde se elija (`orientacion`); el círculo es sólo
// círculo (un diámetro). Módulo sin dependencias: lo usan el molde (`aMedida.js`), las marcas
// (`tiras.js`), las guías de Illustrator/Corel/.ai y los visores. Gemelos en motor_pedido.py.
//
// La medida escrita es la del DISEÑO (como en el rectángulo): la pieza TOTAL es la forma corrida
// hacia afuera el margen, PAREJO en todo el borde (en estas formas no hay «arriba/abajo»: vale el
// mayor de los márgenes). En el triángulo eso es una homotecia desde el INCENTRO: cada lado se
// corre exactamente el margen, y la diagonal de una esquina a la de la guía pasa por el incentro.

export const FORMAS = ['rectangulo', 'circulo', 'triangulo']
export const ORIENTACIONES = ['abajo', 'arriba', 'izq', 'der']        // hacia dónde apunta la punta
export const NOMBRE_FORMA = { rectangulo: 'Rectángulo', circulo: 'Círculo', triangulo: 'Triángulo' }
export const NOMBRE_PUNTA = { abajo: 'punta abajo', arriba: 'punta arriba', izq: 'punta a la izquierda', der: 'punta a la derecha' }

export const normForma = (f) => (FORMAS.includes(f) ? f : 'rectangulo')
export const normOrientacion = (o) => (ORIENTACIONES.includes(o) ? o : 'abajo')

/** El margen PAREJO de una forma que no es rectángulo: el mayor de los cuatro (cm). Gemelo: `_margen_uniforme`. */
export function margenUniforme(m) {
  return Math.max(Number(m.arriba) || 0, Number(m.abajo) || 0, Number(m.izq) || 0, Number(m.der) || 0)
}

/** El triángulo isósceles que llena la caja `x0,y0 → x1,y1` (y hacia ARRIBA, como el PDF): `[baseA,
 *  baseB, punta]`. «abajo» = la base arriba y la punta abajo (el banderín). Gemelo: `_vertices_triangulo`. */
export function verticesTriangulo(x0, y0, x1, y1, orientacion) {
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2
  switch (normOrientacion(orientacion)) {
    case 'arriba': return [[x0, y0], [x1, y0], [cx, y1]]
    case 'izq': return [[x1, y1], [x1, y0], [x0, cy]]
    case 'der': return [[x0, y0], [x0, y1], [x1, cy]]
    default: return [[x1, y1], [x0, y1], [cx, y0]]            // abajo: base arriba, punta abajo
  }
}

/** El incentro y el radio inscripto de un triángulo. Gemelo: `_incentro`. */
export function incentro(p) {
  const [A, B, C] = p
  const d = (u, v) => Math.sqrt((u[0] - v[0]) * (u[0] - v[0]) + (u[1] - v[1]) * (u[1] - v[1]))   // sqrt, no hypot: igual al gemelo de Python
  const a = d(B, C), b = d(C, A), c = d(A, B)
  const per = a + b + c
  const ix = (a * A[0] + b * B[0] + c * C[0]) / per, iy = (a * A[1] + b * B[1] + c * C[1]) / per
  const area = Math.abs((B[0] - A[0]) * (C[1] - A[1]) - (C[0] - A[0]) * (B[1] - A[1])) / 2
  return { x: ix, y: iy, r: area / (per / 2) }
}

/** El triángulo con cada lado corrido `t` (positivo = afuera, negativo = adentro). Gemelo: `_triangulo_corrido`. */
export function trianguloCorrido(p, t) {
  const I = incentro(p)
  const k = (I.r + t) / I.r
  return p.map(([x, y]) => [I.x + (x - I.x) * k, I.y + (y - I.y) * k])
}

/** Cuánto crece la caja de un triángulo de `ancho × alto` cuando cada lado se corre `t`: el factor de
 *  la homotecia (r + t) / r. Gemelo: `_factor_triangulo`. */
export function factorTriangulo(ancho, alto, orientacion, t) {
  const r = incentro(verticesTriangulo(0, 0, ancho, alto, orientacion)).r
  return r > 0 ? (r + t) / r : 1
}

/**
 * 🔺 EL TRIÁNGULO CON LAS PUNTAS RECORTADAS (MAPA 649-650, pedido del usuario 2026-10-09: «que si lo
 * doblan en la guía del dobladillo no quede sobrante hacia afuera» y después «que las puntas, cuando se
 * doble, se unan SUPERPONIÉNDOSE pero que no sobre, así como queda en el rectángulo»). El triángulo del
 * DISEÑO (`w` × `h`, la guía) con su margen `t` en solapas: cada lado lleva una solapa de `t` que,
 * doblada por la guía, cae adentro. En cada punta la solapa se corta por el REFLEJO DEL OTRO LADO (la
 * recta de la punta de la guía al vértice opuesto reflejado sobre ese lado): doblada, llega justo hasta
 * el otro lado de la guía — se SUPERPONE con la solapa vecina, pero no asoma. El corte llega a la punta
 * de la guía. Devuelve, con el origen en la esquina de la caja (y hacia ARRIBA): `pol` (9 puntos: punta,
 * solapa, solapa, punta…), `guia` (los 3 vértices del diseño) y la caja `W` × `H`. Gemelo EXACTO:
 * `_geo_triangulo` de motor_pedido.py.
 */
/** La SOLAPA del lado `i` (de G[i] a G[i+1]) de un triángulo con margen `t`: dirección `u`, normal hacia
 *  afuera `n`, largo `L`, cuánto se mete el recorte por cada unidad de alto en cada punta (`ca`, `cb`: la
 *  cotangente del ángulo del corte — el de la punta, o la mitad del hueco si la punta pasa de 120°, para
 *  que las solapas vecinas no se pisen en la tela) y el alto `tt` (= `t`, salvo un triángulo tan chico
 *  que los dos recortes se cruzan). Sin trigonometría: mismos números en los dos gemelos. Gemelo: `_solapa_tri`. */
export function solapaTri(G, i, t) {
  const a = G[i], b = G[(i + 1) % 3], c = G[(i + 2) % 3]
  const L = Math.sqrt((b[0] - a[0]) * (b[0] - a[0]) + (b[1] - a[1]) * (b[1] - a[1]))
  const ux = (b[0] - a[0]) / L, uy = (b[1] - a[1]) / L
  let nx = -uy, ny = ux
  if (nx * (c[0] - a[0]) + ny * (c[1] - a[1]) > 0) { nx = uy; ny = -ux }       // hacia AFUERA
  const hc = Math.abs(nx * (c[0] - a[0]) + ny * (c[1] - a[1]))
  const cot = (pv, lv) => (pv / lv >= -0.5 ? pv / hc : -(lv + pv) / hc)
  const pa = (c[0] - a[0]) * ux + (c[1] - a[1]) * uy
  const la = Math.sqrt((c[0] - a[0]) * (c[0] - a[0]) + (c[1] - a[1]) * (c[1] - a[1]))
  const pb = (c[0] - b[0]) * (-ux) + (c[1] - b[1]) * (-uy)
  const lb = Math.sqrt((c[0] - b[0]) * (c[0] - b[0]) + (c[1] - b[1]) * (c[1] - b[1]))
  const ca = cot(pa, la), cb = cot(pb, lb)
  const den = ca + cb
  const tt = (den > 0 && t * den > L) ? L / den : t
  return { ux, uy, nx, ny, L, ca, cb, tt }
}

export function geoTriangulo(w, h, t, orientacion, recorte = true) {
  const G = verticesTriangulo(0, 0, w, h, orientacion)
  let pol = []
  if (t > 0 && !recorte) {
    // OVERLOCK (MAPA 652): la costura va en el borde, no se dobla → el triángulo entero corrido el margen
    pol = trianguloCorrido(G, t)
  } else if (t > 0) {
    for (let i = 0; i < 3; i++) {
      const a = G[i], b = G[(i + 1) % 3]
      const { ux, uy, nx, ny, ca, cb, tt } = solapaTri(G, i, t)
      pol.push(a, [a[0] + tt * ca * ux + tt * nx, a[1] + tt * ca * uy + tt * ny],
                  [b[0] - tt * cb * ux + tt * nx, b[1] - tt * cb * uy + tt * ny])
    }
  } else {
    pol = G.slice()
  }
  const x0 = Math.min(...pol.map((p) => p[0])), y0 = Math.min(...pol.map((p) => p[1]))
  const x1 = Math.max(...pol.map((p) => p[0])), y1 = Math.max(...pol.map((p) => p[1]))
  const sh = (p) => [p[0] - x0, p[1] - y0]
  return { pol: pol.map(sh), guia: G.map(sh), W: x1 - x0, H: y1 - y0 }
}

/** `geoTriangulo` de `tri` = `{w, h, t}` (cm del diseño y margen) llevado a una caja (la del contorno de
 *  la pieza en un visor o una plantilla). `yAbajo`: la caja es de pantalla (y hacia abajo). */
export function trianguloEnCaja(tri, orientacion, x0, y0, x1, y1, yAbajo = false) {
  const g = geoTriangulo(tri.w, tri.h, tri.t, orientacion, tri.r !== false)
  const sx = g.W > 0 ? (x1 - x0) / g.W : 1, sy = g.H > 0 ? (y1 - y0) / g.H : 1
  const m = ([x, y]) => [x0 + x * sx, yAbajo ? y0 + (g.H - y) * sy : y0 + y * sy]
  return { pol: g.pol.map(m), guia: g.guia.map(m) }
}

/**
 * 🔲 EL RECTÁNGULO CON LAS ESQUINAS RECORTADAS (MAPA 653, pedido del usuario 2026-10-09: «en el rectángulo,
 * en la terminación dobladillo, debe tener el corte en las puntas como el triángulo»): la caja `x0,y0 →
 * x1,y1` sin el cuadradito de cada esquina (`mi`, `md` = margen izq/der, `ma`, `mb` = arriba/abajo, en
 * las unidades de la caja). Doblado por la guía, cada solapa llega justo a la otra: no sobra nada. Puntos
 * en orden; `yAbajo`: caja de pantalla (arriba = y chica).
 */
export function rectRecortado(x0, y0, x1, y1, mi, md, ma, mb, yAbajo = false) {
  const W = x1 - x0, H = y1 - y0
  const loc = [[mi, 0], [W - md, 0], [W - md, mb], [W, mb], [W, H - ma], [W - md, H - ma], [W - md, H], [mi, H], [mi, H - ma], [0, H - ma], [0, mb], [mi, mb]]
  const out = []
  for (const [x, y] of loc) {
    const p = [x0 + x, yAbajo ? y0 + (H - y) : y0 + y]
    const u = out[out.length - 1]
    if (!u || Math.abs(u[0] - p[0]) > 1e-9 || Math.abs(u[1] - p[1]) > 1e-9) out.push(p)
  }
  const a = out[0], z = out[out.length - 1]
  if (out.length > 1 && Math.abs(a[0] - z[0]) < 1e-9 && Math.abs(a[1] - z[1]) < 1e-9) out.pop()
  return out
}

/** El círculo como 4 curvas (segmentos «DXF»: cm, y hacia arriba), centro `cx, cy`, radio `r`. */
export function segsCirculo(cx, cy, r) {
  const k = 0.5522847498307936 * r
  return [['m', cx + r, cy],
    ['c', cx + r, cy + k, cx + k, cy + r, cx, cy + r],
    ['c', cx - k, cy + r, cx - r, cy + k, cx - r, cy],
    ['c', cx - r, cy - k, cx - k, cy - r, cx, cy - r],
    ['c', cx + k, cy - r, cx + r, cy - k, cx + r, cy],
    ['h']]
}

/** Un polígono como segmentos «DXF». */
export function segsPoligono(pts) {
  return [['m', pts[0][0], pts[0][1]], ...pts.slice(1).map(([x, y]) => ['l', x, y]), ['h']]
}

/**
 * LA GUÍA DEL DISEÑO de una forma dentro de la caja de su CONTORNO (para visores y plantillas): la forma
 * corrida hacia adentro `m` (en las mismas unidades que la caja). `yAbajo`: la caja viene en
 * coordenadas de pantalla (y hacia abajo). Devuelve `{tipo: 'circulo', cx, cy, r}` o
 * `{tipo: 'poligono', pts}` (o null si no queda nada).
 */
export function guiaForma(forma, orientacion, x0, y0, x1, y1, m, yAbajo = false, tri = null) {
  const f = normForma(forma)
  // el triángulo recortado (MAPA 649): la guía sale del diseño (`tri` = {w, h, t}), no de la caja
  if (f === 'triangulo' && tri) return { tipo: 'poligono', pts: trianguloEnCaja(tri, orientacion, x0, y0, x1, y1, yAbajo).guia }
  if (f === 'circulo') {
    const r = Math.min(x1 - x0, y1 - y0) / 2 - m
    return r > 0 ? { tipo: 'circulo', cx: (x0 + x1) / 2, cy: (y0 + y1) / 2, r } : null
  }
  if (f === 'triangulo') {
    const o = normOrientacion(orientacion)
    // en pantalla «arriba» es y chico: se arma en y-arriba y se espeja
    const pts = verticesTriangulo(x0, y0, x1, y1, yAbajo ? ({ arriba: 'abajo', abajo: 'arriba' }[o] || o) : o)
    const I = incentro(pts)
    if (!(I.r - m > 0)) return null
    return { tipo: 'poligono', pts: trianguloCorrido(pts, -m) }
  }
  const p = { tipo: 'poligono', pts: [[x0 + m, y0 + m], [x1 - m, y0 + m], [x1 - m, y1 - m], [x0 + m, y1 - m]] }
  return (x1 - x0 > 2 * m && y1 - y0 > 2 * m) ? p : null
}

/** El contorno de una forma que llena la caja (para dibujarlo): mismo formato que `guiaForma`. */
export function contornoForma(forma, orientacion, x0, y0, x1, y1, yAbajo = false, tri = null, corte = null) {
  if (normForma(forma) === 'triangulo' && tri) return { tipo: 'poligono', pts: trianguloEnCaja(tri, orientacion, x0, y0, x1, y1, yAbajo).pol }
  // el rectángulo con dobladillo: las esquinas recortadas (`corte` = {izq, der, arriba, abajo} en las unidades de la caja)
  if (normForma(forma) === 'rectangulo' && corte && (x1 - x0) > (corte.izq || 0) + (corte.der || 0) && (y1 - y0) > (corte.arriba || 0) + (corte.abajo || 0)) {
    return { tipo: 'poligono', pts: rectRecortado(x0, y0, x1, y1, corte.izq || 0, corte.der || 0, corte.arriba || 0, corte.abajo || 0, yAbajo) }
  }
  return guiaForma(forma, orientacion, x0, y0, x1, y1, 0, yAbajo) ||
    { tipo: 'poligono', pts: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]] }
}

/** Un `guiaForma`/`contornoForma` como `d` de un <path> de SVG. */
export function pathForma(g) {
  if (!g) return ''
  if (g.tipo === 'circulo') {
    const { cx, cy, r } = g
    return `M${cx - r} ${cy}A${r} ${r} 0 1 0 ${cx + r} ${cy}A${r} ${r} 0 1 0 ${cx - r} ${cy}Z`
  }
  return 'M' + g.pts.map(([x, y]) => `${x} ${y}`).join('L') + 'Z'
}

/** Un `guiaForma` como segmentos «DXF» (para las plantillas, que trabajan con segmentos). */
export function segsForma(g) {
  if (!g) return null
  return g.tipo === 'circulo' ? segsCirculo(g.cx, g.cy, g.r) : segsPoligono(g.pts)
}

/**
 * LA GUÍA DEL MARGEN (dobladillo) de un molde a medida como segmentos «DXF», dentro de la caja `b`
 * (`[x0, y0, x1, y1]`, y hacia ARRIBA) del contorno de la pieza. `dobladillo` = `margenSobreContorno`
 * (`{arriba, abajo, izq, der}` en cm + `forma`/`orientacion`); `k` = unidades por cm de la caja. El
 * rectángulo corre cada lado lo suyo; el círculo y el triángulo, el margen PAREJO. Una sola función
 * para la guía .ai, el PDF de medidas y el camino de Illustrator/Corel: la misma línea en todas.
 */
export function segsDobladillo(b, dobladillo, k) {
  if (!b || !dobladillo) return null
  const f = normForma(dobladillo.forma)
  if (f !== 'rectangulo') {
    const m = margenUniforme(dobladillo) * k
    if (!(m > 0)) return null
    // el triángulo recortado: la guía sale del diseño (`dobladillo.diseno`, cm), llevada a la caja
    const d = dobladillo.diseno
    const tri = (f === 'triangulo' && d) ? { w: Number(d.w), h: Number(d.h), t: margenUniforme(dobladillo), r: dobladillo.recorte !== false } : null
    return segsForma(guiaForma(f, dobladillo.orientacion, b[0], b[1], b[2], b[3], m, false, tri))
  }
  const iz = (Number(dobladillo.izq) || 0) * k, de = (Number(dobladillo.der) || 0) * k
  const ab = (Number(dobladillo.abajo) || 0) * k, ar = (Number(dobladillo.arriba) || 0) * k
  if (!(iz > 0 || de > 0 || ab > 0 || ar > 0)) return null
  const x0 = b[0] + iz, x1 = b[2] - de, y0 = b[1] + ab, y1 = b[3] - ar
  return (x1 > x0 && y1 > y0) ? segsPoligono([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]) : null
}

/**
 * 🧵 LA COSTURA (MAPA 654, pedido del usuario 2026-10-09: «una guía nueva, punteada, interna a la guía del
 * arte, donde va la costura, a la misma distancia que la otra guía — sólo en dobladillo — para que cuando
 * suban el arte sepan si la costura pasa por arriba o no»). Doblado el margen por la guía, el borde de la
 * tela cae el margen ADENTRO: ahí se cose. Es la guía del diseño corrida hacia adentro `dobladillo.costura`
 * (cm, el margen entero; sólo viene con dobladillo). Segmentos «DXF» en la caja `b` (y hacia ARRIBA), o null.
 */
export function segsCostura(b, dobladillo, k) {
  if (!b || !dobladillo || !dobladillo.costura) return null
  const c = dobladillo.costura
  const f = normForma(dobladillo.forma)
  if (f !== 'rectangulo') {
    const u = margenUniforme(dobladillo), cu = margenUniforme(c)
    if (!(cu > 0)) return null
    const d = dobladillo.diseno
    const tri = (f === 'triangulo' && d) ? { w: Number(d.w), h: Number(d.h), t: u, r: dobladillo.recorte !== false } : null
    const g = guiaForma(f, dobladillo.orientacion, b[0], b[1], b[2], b[3], u * k, false, tri)
    if (!g) return null
    if (g.tipo === 'circulo') return g.r - cu * k > 0 ? segsCirculo(g.cx, g.cy, g.r - cu * k) : null
    return incentro(g.pts).r - cu * k > 0 ? segsPoligono(trianguloCorrido(g.pts, -cu * k)) : null
  }
  const iz = ((Number(dobladillo.izq) || 0) + (Number(c.izq) || 0)) * k, de = ((Number(dobladillo.der) || 0) + (Number(c.der) || 0)) * k
  const ab = ((Number(dobladillo.abajo) || 0) + (Number(c.abajo) || 0)) * k, ar = ((Number(dobladillo.arriba) || 0) + (Number(c.arriba) || 0)) * k
  const x0 = b[0] + iz, x1 = b[2] - de, y0 = b[1] + ab, y1 = b[3] - ar
  return (x1 > x0 && y1 > y0) ? segsPoligono([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]) : null
}

/**
 * Un camino (segmentos «DXF») convertido en RAYAS: tramos sueltos de `on` de largo cada `on + off` (en las
 * unidades de los segmentos). Las curvas se aplanan en tramos cortos. Sirve para que una línea punteada
 * entre a Illustrator y Corel como GUÍA de verdad (MAPA 656): una guía no puede tener rayas, pero varias
 * guías cortas en fila sí se ven punteadas — y una guía va siempre ENCIMA (el arte punteado quedaba
 * tapado por el fondo de la mesa, como pasó con el dobladillo en la 629).
 */
export function segsRayas(segs, on, off) {
  if (!segs || !(on > 0)) return null
  // 1) el camino como polilíneas (una por sub-camino)
  const lineas = []
  let cur = null, ini = null
  for (const s of segs) {
    if (s[0] === 'm') { cur = [[s[1], s[2]]]; ini = cur[0]; lineas.push(cur) }
    else if (s[0] === 'l' && cur) cur.push([s[1], s[2]])
    else if (s[0] === 'c' && cur) {
      const [x0, y0] = cur[cur.length - 1]
      for (let i = 1; i <= 24; i++) {
        const t = i / 24, u = 1 - t
        cur.push([u * u * u * x0 + 3 * u * u * t * s[1] + 3 * u * t * t * s[3] + t * t * t * s[5],
                  u * u * u * y0 + 3 * u * u * t * s[2] + 3 * u * t * t * s[4] + t * t * t * s[6]])
      }
    } else if (s[0] === 'h' && cur && ini) cur.push([ini[0], ini[1]])
  }
  // 2) las rayas: se camina cada polilínea y se corta en tramos de `on`, salteando `off`
  const out = []
  for (const L of lineas) {
    let pos = 0, dentro = true, resto = on, raya = [L[0]]
    for (let i = 1; i < L.length; i++) {
      let [ax, ay] = L[i - 1]
      const [bx, by] = L[i]
      let seg = Math.hypot(bx - ax, by - ay)
      while (seg > 1e-9) {
        const paso = Math.min(seg, resto)
        const f = paso / seg
        const px = ax + (bx - ax) * f, py = ay + (by - ay) * f
        if (dentro) raya.push([px, py])
        seg -= paso; resto -= paso; ax = px; ay = py; pos += paso
        if (resto <= 1e-9) {
          if (dentro && raya.length > 1) out.push(['m', raya[0][0], raya[0][1]], ...raya.slice(1).map(([x, y]) => ['l', x, y]))
          dentro = !dentro
          resto = dentro ? on : off
          raya = [[ax, ay]]
        }
      }
    }
    if (dentro && raya.length > 1) out.push(['m', raya[0][0], raya[0][1]], ...raya.slice(1).map(([x, y]) => ['l', x, y]))
  }
  return out.length ? out : null
}

/** La costura como `d` de un <path> de SVG en una caja de PANTALLA (y hacia abajo): la misma línea que
 *  `segsCostura`, para los visores. */
export function pathCostura(dobladillo, x0, y0, w, h, k) {
  const s = segsCostura([x0, y0, x0 + w, y0 + h], dobladillo, k)
  if (!s) return ''
  const fy = (y) => y0 + h - (y - y0)              // y hacia arriba → pantalla
  let d = ''
  for (const sg of s) {
    if (sg[0] === 'm') d += `M${sg[1]} ${fy(sg[2])}`
    else if (sg[0] === 'l') d += `L${sg[1]} ${fy(sg[2])}`
    else if (sg[0] === 'c') d += `C${sg[1]} ${fy(sg[2])} ${sg[3]} ${fy(sg[4])} ${sg[5]} ${fy(sg[6])}`
    else if (sg[0] === 'h') d += 'Z'
  }
  return d
}

/** La caja (x0, y0, x1, y1) de un `guiaForma`. */
export function cajaForma(g) {
  if (!g) return null
  if (g.tipo === 'circulo') return [g.cx - g.r, g.cy - g.r, g.cx + g.r, g.cy + g.r]
  const xs = g.pts.map((p) => p[0]), ys = g.pts.map((p) => p[1])
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]
}
