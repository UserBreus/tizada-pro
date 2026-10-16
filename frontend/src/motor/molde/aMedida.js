// ── MOLDE A MEDIDA (MAPA 623) ────────────────────────────────────────────────────────────────
// Un molde de UNA pieza rectangular (banderas, banners): no se sube un archivo, se escribe la medida.
// Pedido del usuario 2026-10-06: «se elige la opción molde a medida, se pone el nombre de la única
// pieza y el margen del borde hacia adentro; en el pedido se escriben ancho y alto en metros y trae
// todo lo demás (etiqueta, grosor del molde, nesting…)».
//
// La decisión de fondo: el motor ENTERO (visor, tizada, etiqueta, borde, nesting, ficha, plantilla de
// Illustrator) trabaja con moldes de verdad —un archivo con piezas y talles—. En vez de enseñarle a
// cada parte qué es «una medida», acá se FABRICA ese molde: un PDF con el rectángulo, escrito por el
// mismo constructor que el DXF (`construirPdfPiezas`), una capa por talle, y el nombre de la pieza
// viaja como el de un DXF (`resumen.nombres`) para que el alta lo ponga sola. El talle se llama como
// la medida («1,50x0,90»): así la etiqueta de corte y la ficha dicen la medida sin tocar el motor.
import { construirPdfPiezas } from '../dxf/importar.js'
import { normForma, normOrientacion, margenUniforme, geoTriangulo, segsCirculo, segsPoligono, rectRecortado } from './formas.js'

/** «1,50» — metros con dos decimales y coma, como se escriben en el taller. */
export function metrosTexto(m) {
  const v = Math.round(Number(m) * 100) / 100
  return v.toFixed(2).replace('.', ',')
}

/** El nombre del TALLE de un molde a medida: «1,50x0,90» (ancho x alto, en metros). Sólo ASCII a
 *  propósito: viaja como nombre de capa del PDF y como clave del registro. */
export function talleDeMedida(anchoM, altoM) {
  return `${metrosTexto(anchoM)}x${metrosTexto(altoM)}`
}

/** Lee lo que escribió la persona: «1,5», «1.50», «150 cm» no; sólo metros con coma o punto. */
export function leerMetros(txt) {
  const s = String(txt == null ? '' : txt).trim().replace(',', '.')
  if (!/^\d+(\.\d+)?$/.test(s)) return null
  const v = Number(s)
  return v > 0 ? v : null
}

/** Topes de la medida: menos de 5 cm no es una pieza; más de 50 m no entra en ninguna mesa (el PDF
 *  topa ahí, `ALTO_MESA_MAX_CM`). */
export const MEDIDA_MIN_M = 0.05
export const MEDIDA_MAX_M = 50

/** ¿Es una medida que se puede fabricar? Devuelve el motivo para la pantalla, o null. */
export function problemaMedida(anchoM, altoM) {
  if (anchoM == null || altoM == null) return 'Escribí el ancho y el alto en metros (por ejemplo 1,50 y 0,90).'
  if (anchoM < MEDIDA_MIN_M || altoM < MEDIDA_MIN_M) return `La medida mínima es ${metrosTexto(MEDIDA_MIN_M)} m.`
  if (anchoM > MEDIDA_MAX_M || altoM > MEDIDA_MAX_M) return `La medida máxima es ${MEDIDA_MAX_M} m.`
  return null
}

/** El margen (dobladillo) en cm por borde. Acepta `{todos}` o `{arriba, abajo, izq, der}`; lo que
 *  falte vale `todos` (o 0). */
export function margenPorBorde(margen) {
  const m = margen || {}
  const t = Number(m.todos) || 0
  const v = (k) => (m[k] === '' || m[k] == null ? t : Math.max(0, Number(m[k]) || 0))
  return { arriba: v('arriba'), abajo: v('abajo'), izq: v('izq'), der: v('der') }
}

/** 🔴 EL BORDE DE CORTE VA ADENTRO DE LA MEDIDA (decisión del usuario 2026-10-07: «si pongo 300 × 157,
 *  ¿por qué me pone 300,4 × 157,4?» → «Borde por dentro»). El motor deja alrededor de cada pieza la
 *  RESERVA del borde (`B`: el ancho del borde, o 2 mm si está apagado) y dibuja el borde ahí. Para que
 *  la bandera impresa mida EXACTO lo que se escribió, el rectángulo del molde se arma `reserva` más chico
 *  por lado: rectángulo + reserva = la medida. Default de un molde nuevo: 2 mm (`_BORDE_DEFAULT`). */
export const RESERVA_DEFECTO_MM = 2

/** El MARGEN medido desde el CONTORNO del molde (lo que dibujan el visor, la guía y la plantilla):
 *  el margen se escribe desde el borde FINAL de la bandera, y el contorno está `reserva` más adentro. */
export function margenSobreContorno(margen, reservaMm = RESERVA_DEFECTO_MM, forma = 'rectangulo', orientacion = 'abajo', anchoM = null, altoM = null, terminacion = 'dobladillo') {
  const m = margenPorBorde(margen)
  const f = normForma(forma)
  // el TRIÁNGULO (MAPA 645) no se achica: su contorno ES el total y el margen se mide desde ahí
  const r = f === 'triangulo' ? 0 : (Number(reservaMm) || 0) / 10
  const q = (v) => Math.max(0, Math.round((v - r) * 1000) / 1000)
  // LA COSTURA (MAPA 654): sólo con dobladillo — el margen ENTERO adentro de la guía (`segsCostura`)
  const conCostura = normTerminacion(terminacion) === 'dobladillo' && (m.arriba > 0 || m.abajo > 0 || m.izq > 0 || m.der > 0)
  if (f === 'rectangulo') {
    const o = { arriba: q(m.arriba), abajo: q(m.abajo), izq: q(m.izq), der: q(m.der) }
    if (conCostura) o.costura = { arriba: m.arriba, abajo: m.abajo, izq: m.izq, der: m.der }
    return o
  }
  // círculo y triángulo: margen PAREJO (el mayor), como lo arma `medidaPieza`; la forma viaja con él
  // para que cada guía (`segsDobladillo`, visores) dibuje la línea con la forma de la pieza
  const u = q(margenUniforme(m))
  const out = { arriba: u, abajo: u, izq: u, der: u, forma: f, orientacion: normOrientacion(orientacion) }
  // el triángulo recortado (MAPA 649): la guía se arma con la medida del DISEÑO, no desde la caja
  if (f === 'triangulo' && Number(anchoM) > 0 && Number(altoM) > 0) out.diseno = { w: Number(anchoM) * 100, h: Number(altoM) * 100 }
  if (f === 'triangulo') out.recorte = normTerminacion(terminacion) !== 'overlock'      // overlock: puntas enteras (MAPA 652)
  if (conCostura) { const cu = margenUniforme(m); out.costura = { arriba: cu, abajo: cu, izq: cu, der: cu } }
  return out
}

/**
 * 🔴 LA VERSIÓN DE LA GEOMETRÍA con la que se arma el archivo de cada forma (MAPA 651). El archivo del
 * molde de un pedido se arma UNA vez (al escribir la medida); si después cambia cómo se dibuja una
 * forma, la copia vieja quedaba con el contorno viejo y la guía (que se calcula con la geometría NUEVA)
 * no coincidía con él — visto 2026-10-09: un triángulo armado con el inglete (649) mostraba en
 * Illustrator la guía de la 650. La copia guarda con qué versión se armó (`a_medida.geo_v`) y el paso
 * Arte la vuelve a armar sola si quedó vieja. Subir este número cuando cambie el dibujo de una forma.
 */
export const GEO_VERSION = { rectangulo: 2, circulo: 1, triangulo: 3 }     // rectángulo 2: esquinas recortadas (MAPA 653)

/**
 * LA TERMINACIÓN DEL BORDE (MAPA 652, pedido del usuario 2026-10-09): se elige EN CADA PEDIDO.
 *  · `dobladillo`: el margen del molde (Ajustes › Margen), que se dobla por la guía (el triángulo con las
 *    puntas recortadas para que, doblado, no sobre nada);
 *  · `overlock`: la costura va en el borde, no se dobla: la forma tal cual, corrida la medida del overlock
 *    (`overlock_cm` del molde, 1 cm si no se puso);
 *  · `sin`: sin margen, la pieza es el diseño (las tiras van sólo en la ficha).
 * Gemelos: `_TERMINACIONES` / `_margen_de_terminacion` de servidor.py.
 */
export const TERMINACIONES = ['dobladillo', 'overlock', 'sin']
export const NOMBRE_TERMINACION = { dobladillo: 'Dobladillo', overlock: 'Overlock', sin: 'Sin margen' }
export const normTerminacion = (t) => (TERMINACIONES.includes(t) ? t : 'dobladillo')
export const OVERLOCK_DEFECTO_CM = 1
/** El margen que rige con una terminación: el del molde (dobladillo), el del overlock, o nada. En una copia
 *  del pedido el del dobladillo queda en `margen_dobladillo` (`margen` es el que rige). */
export function margenDeTerminacion(am, terminacion) {
  const t = normTerminacion(terminacion ?? (am && am.terminacion))
  if (t === 'sin') return { todos: 0 }
  if (t === 'overlock') {
    const v = Number(am && am.overlock_cm)
    return { todos: Number.isFinite(v) && v >= 0 ? v : OVERLOCK_DEFECTO_CM }
  }
  return (am && (am.margen_dobladillo || am.margen)) || { todos: 0 }
}
/**
 * ¿EL ARTE ES DE OTRA MEDIDA? (MAPA 658, pedido del usuario 2026-10-09 con captura: «las guías deben ser
 * idénticas en forma y tamaño; el arte no llegó a cubrirlo todo»). El arte se arma sobre la plantilla, y la
 * plantilla tiene la medida que había cuando se creó: si después se cambia la medida (3,00 × 1,50 → 1,45), la
 * mesa del arte (300 × 153,4) ya no es la pieza (300 × 148,5) y el diseño, escalado por una dimensión, deja tela
 * sin cubrir. `mesa` = la mesa del arte de la pieza ({w_cm, h_cm}); `molde` = el contorno de la pieza
 * ({w, h} en cm). Devuelve null si coinciden (± `tolCm`) o {arte: {w, h}, molde: {w, h}}.
 * Gemelo: `_arte_otra_medida` de servidor.py (la alarma `arte-otra-medida` de la API).
 */
export function arteDeOtraMedida(mesa, molde, tolCm = 0.5) {
  if (!mesa || !molde) return null
  const aw = Number(mesa.w_cm), ah = Number(mesa.h_cm), mw = Number(molde.w), mh = Number(molde.h)
  if (!(aw > 0 && ah > 0 && mw > 0 && mh > 0)) return null
  if (Math.abs(aw - mw) <= tolCm && Math.abs(ah - mh) <= tolCm) return null
  return { arte: { w: aw, h: ah }, molde: { w: mw, h: mh } }
}

export const versionGeo = (forma) => GEO_VERSION[normForma(forma)] || 1
/** ¿El archivo de esta copia se armó con una geometría vieja? (sin `geo_v` = la primera) */
export const geoVieja = (am) => !!am && !!am.de && (Number(am.geo_v) || 1) !== versionGeo(am.forma)

/** El rectángulo como segmentos «DXF» (cm, y hacia arriba), como los lee `construirPdfPiezas`. */
export function segsRectangulo(anchoCm, altoCm) {
  return [['m', 0, 0], ['l', anchoCm, 0], ['l', anchoCm, altoCm], ['l', 0, altoCm], ['h']]
}

/**
 * El PDF del molde a medida + su resumen (forma del resumen de un DXF: `nombres`, `talles`,
 * `indices`), listo para el alta del camino A. `mupdf` = el módulo ya cargado.
 */
export function pdfMoldeAMedida(mupdf, { anchoM, altoM, pieza, reservaMm = 0, margen = null, forma = 'rectangulo', orientacion = 'abajo', terminacion = 'dobladillo' }) {
  const nombre = String(pieza || '').trim() || 'Pieza'
  const talle = talleDeMedida(anchoM, altoM)          // el talle dice la medida ESCRITA (la del diseño)
  // la pieza = la medida del diseño + el margen alrededor (`medidaPieza`); el borde de corte va adentro
  const f = normForma(forma)
  const { anchoCm, altoCm } = medidaPieza(anchoM, altoM, margen, f, orientacion, terminacion)
  const res = (Number(reservaMm) || 0) / 10
  let segs
  if (f === 'circulo') {
    // el contorno, la reserva más adentro: el borde (hacia afuera de él) termina justo en el total
    segs = segsCirculo(anchoCm / 2, anchoCm / 2, Math.max(0.5, anchoCm / 2 - res))
  } else if (f === 'triangulo') {
    // 🔴 el TRIÁNGULO es el total tal cual y el borde va por DENTRO (`_borde_de` → «dentro»), con las
    // PUNTAS RECORTADAS (MAPA 649-650): al doblar el margen por la guía se superpone pero no sobra nada
    segs = segsPoligono(geoTriangulo(Number(anchoM) * 100, Number(altoM) * 100, margenUniforme(margenPorBorde(margen)), orientacion,
      normTerminacion(terminacion) !== 'overlock').pol)
  } else {
    // el contorno, la reserva más adentro (el borde «fuera» termina en el total). Con DOBLADILLO, las
    // esquinas recortadas (MAPA 653): sin el cuadradito de cada esquina, del tamaño del margen — el borde
    // «fuera» del contorno recortado termina justo en la guía, así al doblar no sobra nada
    const m = margenPorBorde(margen)
    const Wc = Math.max(1, anchoCm - 2 * res), Hc = Math.max(1, altoCm - 2 * res)
    const corta = normTerminacion(terminacion) === 'dobladillo' && (m.izq > 0 || m.der > 0 || m.arriba > 0 || m.abajo > 0)
      && Wc > m.izq + m.der && Hc > m.arriba + m.abajo
    segs = corta ? segsPoligono(rectRecortado(0, 0, Wc, Hc, m.izq, m.der, m.arriba, m.abajo)) : segsRectangulo(Wc, Hc)
  }
  const piezas = [{ nombre, talles: new Map([[talle, segs]]) }]
  const r = construirPdfPiezas(mupdf, piezas, [talle], 1.0)
  return { pdf: r.pdf, resumen: { ...r.resumen, archivo: 'molde a medida', a_medida: true } }
}

/**
 * 🔴 LA MEDIDA QUE SE ESCRIBE ES LA DEL DISEÑO (2026-10-07, regla del usuario: «la medida que se ponga
 * será la del margen, guía de diseño, pero el archivo se creará con el espacio del margen: una bandera
 * de 3 × 1,50 con 1 cm de margen por lado sale de 3,02 × 1,52»). La PIEZA terminada = la medida + el
 * margen de cada lado; el borde de corte va adentro de ella (`RESERVA_DEFECTO_MM`). Gemelo: `_medida_pieza`.
 */
export function medidaPieza(anchoM, altoM, margen, forma = 'rectangulo', orientacion = 'abajo', terminacion = 'dobladillo') {
  const m = margenPorBorde(margen)
  const f = normForma(forma)
  // CÍRCULO y TRIÁNGULO (MAPA 645): el margen es PAREJO (el mayor) y la pieza es la forma corrida afuera
  if (f === 'circulo') {
    const D = Number(anchoM) * 100 + 2 * margenUniforme(m)
    return { anchoCm: D, altoCm: D }
  }
  if (f === 'triangulo') {
    // con las puntas recortadas (MAPA 649-650): la caja del contorno cortado
    const g = geoTriangulo(Number(anchoM) * 100, Number(altoM) * 100, margenUniforme(m), orientacion, normTerminacion(terminacion) !== 'overlock')
    return { anchoCm: g.W, altoCm: g.H }
  }
  return { anchoCm: Number(anchoM) * 100 + m.izq + m.der, altoCm: Number(altoM) * 100 + m.arriba + m.abajo }
}

// MARCAS DE TIRAS (MAPA 639): la geometría vive en `tiras.js` (la usa también el motor de piezas)
export { segmentosTiras } from './tiras.js'

/** La grilla del armado si el molde no dice otra cosa (`TIZADA_RES_MM`). */
export const RESOLUCION_DEFECTO_MM = 4

/**
 * ¿La pieza entra en la tela? (regla del usuario 2026-10-06: «si la medida supera el ancho de la tela
 * no se deja elegir ni pasar al paso siguiente»). La pieza ocupa la medida del diseño + el margen
 * (`medidaPieza`); el borde de corte va adentro. La mesa de la tela (`anchoCm`) y el largo máximo
 * (`largoMaxCm`) se achican por el margen del nesting a cada lado. Se puede girar 90° sólo si el nesting
 * de ese molde gira («90» o «libre»). Si no entra, el `motivo` dice cuánto se pasa y LO MÁXIMO que entra
 * (2026-10-07: «que le diga si se puede hacer o no, cuánto, y cuál es el máximo»). `bordeMm` queda por
 * compatibilidad (ya no suma). `resolucionMm` = la grilla del armado (MAPA 632-633).
 * Devuelve `{cabe, girada, motivo, excesoCm, maximoM, maximoLado}`.
 * Gemelo EXACTO (mismas cuentas, mismo texto): `_cabe_en_tela` de servidor.py.
 */
export function cabeEnTela({ anchoM, altoM, margen = null, bordeMm = 0, anchoCm, largoMaxCm, margenNestingMm = 0,
                            rotacion = 'ninguna', resolucionMm = RESOLUCION_DEFECTO_MM, forma = 'rectangulo', orientacion = 'abajo', terminacion = 'dobladillo' }) {
  const m = margenPorBorde(margen)
  const f = normForma(forma)
  const mx = m.izq + m.der, my = m.arriba + m.abajo
  // el TRIÁNGULO lleva el borde por dentro y el armado le deja la reserva alrededor (MAPA 645)
  const extra = f === 'triangulo' ? 2 * ((Number(bordeMm) > 0 ? Number(bordeMm) : 2) / 10) : 0
  const tot = medidaPieza(anchoM, altoM, margen, f, orientacion, terminacion)
  const w = tot.anchoCm + extra
  const h = tot.altoCm + extra
  // lo máximo de una forma: la medida del diseño más grande (cm enteros) con la que la pieza entra en
  // `limite` por ese eje (en el círculo, el diámetro)
  const maximoForma = (eje, limite) => {
    let d = Math.floor(limite)
    while (d >= MEDIDA_MIN_M * 100) {
      const a = (f === 'circulo' || eje === 'ancho') ? d / 100 : Number(anchoM)
      const b = (f === 'circulo' || eje === 'alto') ? d / 100 : Number(altoM)
      const t = medidaPieza(a, b, margen, f, orientacion, terminacion)
      if ((eje === 'ancho' ? t.anchoCm : t.altoCm) + extra <= limite + 1e-6) return d
      d -= 1
    }
    return 0
  }
  // El armado trabaja en una grilla de `res` mm (la separación entre piezas ya NO se come el borde de
  // la mesa, MAPA 633). Las cuentas van del lado seguro (una celda de más para la pieza, el redondeo
  // hacia abajo para la mesa), así lo que acá «entra» lo acepta siempre el armado real.
  const res = Number(resolucionMm) > 0 ? Number(resolucionMm) : RESOLUCION_DEFECTO_MM
  const mgMm = 2 * (Number(margenNestingMm) || 0)
  const lugar = (cm) => Math.floor((cm * 10 - mgMm) / res - 1e-6)                 // celdas libres para la pieza
  const celdas = (cm) => Math.floor(cm * 10 / res + 1e-6) + 1
  const hasta = (cm) => Math.max(0, Math.ceil(lugar(cm) * res - 1e-6) - 1) / 10      // lo más largo que entra, al mm
  const cabe = (a, b) => celdas(a) <= lugar(Number(anchoCm)) && celdas(b) <= lugar(Number(largoMaxCm))
  const util = hasta(Number(anchoCm)), largo = hasta(Number(largoMaxCm))
  const gira = rotacion === '90' || rotacion === 'libre'
  if (cabe(w, h)) return { cabe: true, girada: false, motivo: null, excesoCm: 0, maximoM: null, maximoLado: null }
  if (gira && cabe(h, w)) return { cabe: true, girada: true, motivo: null, excesoCm: 0, maximoM: null, maximoLado: null }
  const cm = (x) => (Math.round(x * 10) / 10).toString().replace('.', ',')
  const conM = (f === 'rectangulo' ? (mx || my) : margenUniforme(m) > 0) ? ' con el margen' : ''
  const tam = `La bandera${conM} mide ${cm(w)} × ${cm(h)} cm`
  let exceso, maxCm, lado, motivo
  if ((gira ? Math.min(w, h) : w) > util + 1e-6) {
    // no entra a lo ANCHO de la tela: se mide por el lado que iría atravesado (con giro, el más corto)
    const porAlto = gira && h < w
    exceso = (porAlto ? h : w) - util
    maxCm = f === 'rectangulo' ? Math.floor((util - (porAlto ? my : mx)) + 1e-6) : maximoForma(porAlto ? 'alto' : 'ancho', util)
    lado = f === 'circulo' ? 'diámetro' : (porAlto ? 'alto' : 'ancho')
    motivo = `${tam} y en esta tela entra hasta ${cm(util)} cm de ancho: se pasa ${cm(exceso)} cm${gira ? ' (ni girándola)' : ''}.`
  } else {
    // entra a lo ancho pero no en el LARGO de la mesa
    const derecha = w <= util + 1e-6
    exceso = (derecha ? h : w) - largo
    maxCm = f === 'rectangulo' ? Math.floor((largo - (derecha ? my : mx)) + 1e-6) : maximoForma(derecha ? 'alto' : 'ancho', largo)
    lado = f === 'circulo' ? 'diámetro' : (derecha ? 'alto' : 'ancho')
    motivo = `${tam} y en la mesa más larga entra hasta ${cm(largo)} cm: se pasa ${cm(exceso)} cm.`
  }
  const maximoM = maxCm >= MEDIDA_MIN_M * 100 ? maxCm / 100 : null
  motivo += maximoM
    ? ` En esta tela, lo máximo es ${metrosTexto(maximoM)} m de ${lado}${conM ? ' (sin contar el margen)' : ''}.`
    : ' Con este margen no entra ni la medida mínima.'
  return { cabe: false, girada: false, motivo, excesoCm: Math.round(exceso * 10) / 10, maximoM, maximoLado: lado }
}

/**
 * EL GIRO DE UN MOLDE A MEDIDA (MAPA 696): una bandera es una pieza plana, sin sentido de tela que la obligue a ir
 * derecha → SIEMPRE puede girar 90°, sea cual sea la regla de acomodo del molde («libre» queda libre). Antes salía
 * de esa regla: en el servidor publicado la Bandera tenía «Estándar» (no gira) y una de 3 × 1,50 «no entraba» en la
 * tela de 1,60 mientras en el taller (regla «Productos simples», giro libre) sí. Gemelo: `_rotacion_a_medida`.
 */
export const rotacionAMedida = (rot) => (rot === 'libre' || rot === '90' ? rot : '90')

/**
 * ¿La COPIA a medida del pedido entra en una tela de `anchoCm`? La decide ESTA computadora (MAPA 692: el
 * servidor sólo guarda; ya no frena el plan). `am` = lo que publica el servidor del molde (`_a_medida_publico`:
 * medida, forma, punta, terminación, margen, borde y el acomodo). Mide la MISMA pieza que el visor
 * (`estadoMedida`): forma, punta, terminación y el margen que RIGE con ella (MAPA 691).
 */
export function amEnTela(am, anchoCm, largoPedidoCm = null) {
  const n = (am && am.nesting) || {}
  const te = normTerminacion(am && am.terminacion)
  return cabeEnTela({ anchoM: am.ancho_m, altoM: am.alto_m, margen: margenDeTerminacion(am, te), bordeMm: am.borde_mm, anchoCm,
    // el largo de mesa del PEDIDO manda sobre el del nesting (MAPA 716)
    largoMaxCm: largoPedidoCm || n.alto_max_cm, margenNestingMm: n.margen_mm, rotacion: rotacionAMedida(n.rotacion), resolucionMm: n.resolucion_mm,
    forma: normForma(am.forma), orientacion: normOrientacion(am.orientacion), terminacion: te })
}

