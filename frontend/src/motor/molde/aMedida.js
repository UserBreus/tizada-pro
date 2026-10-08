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
export function margenSobreContorno(margen, reservaMm = RESERVA_DEFECTO_MM) {
  const m = margenPorBorde(margen)
  const r = (Number(reservaMm) || 0) / 10
  const q = (v) => Math.max(0, Math.round((v - r) * 1000) / 1000)
  return { arriba: q(m.arriba), abajo: q(m.abajo), izq: q(m.izq), der: q(m.der) }
}

/** El rectángulo como segmentos «DXF» (cm, y hacia arriba), como los lee `construirPdfPiezas`. */
export function segsRectangulo(anchoCm, altoCm) {
  return [['m', 0, 0], ['l', anchoCm, 0], ['l', anchoCm, altoCm], ['l', 0, altoCm], ['h']]
}

/**
 * El PDF del molde a medida + su resumen (forma del resumen de un DXF: `nombres`, `talles`,
 * `indices`), listo para el alta del camino A. `mupdf` = el módulo ya cargado.
 */
export function pdfMoldeAMedida(mupdf, { anchoM, altoM, pieza, reservaMm = 0, margen = null }) {
  const nombre = String(pieza || '').trim() || 'Pieza'
  const talle = talleDeMedida(anchoM, altoM)          // el talle dice la medida ESCRITA (la del diseño)
  // la pieza = la medida del diseño + el margen alrededor (`medidaPieza`); el borde de corte va adentro
  const { anchoCm, altoCm } = medidaPieza(anchoM, altoM, margen)
  const rr = 2 * (Number(reservaMm) || 0) / 10
  const piezas = [{ nombre, talles: new Map([[talle, segsRectangulo(Math.max(1, anchoCm - rr), Math.max(1, altoCm - rr))]]) }]
  const r = construirPdfPiezas(mupdf, piezas, [talle], 1.0)
  return { pdf: r.pdf, resumen: { ...r.resumen, archivo: 'molde a medida', a_medida: true } }
}

/**
 * 🔴 LA MEDIDA QUE SE ESCRIBE ES LA DEL DISEÑO (2026-10-07, regla del usuario: «la medida que se ponga
 * será la del margen, guía de diseño, pero el archivo se creará con el espacio del margen: una bandera
 * de 3 × 1,50 con 1 cm de margen por lado sale de 3,02 × 1,52»). La PIEZA terminada = la medida + el
 * margen de cada lado; el borde de corte va adentro de ella (`RESERVA_DEFECTO_MM`). Gemelo: `_medida_pieza`.
 */
export function medidaPieza(anchoM, altoM, margen) {
  const m = margenPorBorde(margen)
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
                            rotacion = 'ninguna', resolucionMm = RESOLUCION_DEFECTO_MM }) {
  const m = margenPorBorde(margen)
  const mx = m.izq + m.der, my = m.arriba + m.abajo
  const w = Number(anchoM) * 100 + mx
  const h = Number(altoM) * 100 + my
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
  const conM = (mx || my) ? ' con el margen' : ''
  const tam = `La bandera${conM} mide ${cm(w)} × ${cm(h)} cm`
  let exceso, maxCm, lado, motivo
  if ((gira ? Math.min(w, h) : w) > util + 1e-6) {
    // no entra a lo ANCHO de la tela: se mide por el lado que iría atravesado (con giro, el más corto)
    const porAlto = gira && h < w
    exceso = (porAlto ? h : w) - util
    maxCm = Math.floor((util - (porAlto ? my : mx)) + 1e-6)
    lado = porAlto ? 'alto' : 'ancho'
    motivo = `${tam} y en esta tela entra hasta ${cm(util)} cm de ancho: se pasa ${cm(exceso)} cm${gira ? ' (ni girándola)' : ''}.`
  } else {
    // entra a lo ancho pero no en el LARGO de la mesa
    const derecha = w <= util + 1e-6
    exceso = (derecha ? h : w) - largo
    maxCm = Math.floor((largo - (derecha ? my : mx)) + 1e-6)
    lado = derecha ? 'alto' : 'ancho'
    motivo = `${tam} y en la mesa más larga entra hasta ${cm(largo)} cm: se pasa ${cm(exceso)} cm.`
  }
  const maximoM = maxCm >= MEDIDA_MIN_M * 100 ? maxCm / 100 : null
  motivo += maximoM
    ? ` En esta tela, lo máximo es ${metrosTexto(maximoM)} m de ${lado}${conM ? ' (sin contar el margen)' : ''}.`
    : ' Con este margen no entra ni la medida mínima.'
  return { cabe: false, girada: false, motivo, excesoCm: Math.round(exceso * 10) / 10, maximoM, maximoLado: lado }
}

