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

/** El rectángulo como segmentos «DXF» (cm, y hacia arriba), como los lee `construirPdfPiezas`. */
export function segsRectangulo(anchoCm, altoCm) {
  return [['m', 0, 0], ['l', anchoCm, 0], ['l', anchoCm, altoCm], ['l', 0, altoCm], ['h']]
}

/**
 * El PDF del molde a medida + su resumen (forma del resumen de un DXF: `nombres`, `talles`,
 * `indices`), listo para el alta del camino A. `mupdf` = el módulo ya cargado.
 */
export function pdfMoldeAMedida(mupdf, { anchoM, altoM, pieza }) {
  const nombre = String(pieza || '').trim() || 'Pieza'
  const talle = talleDeMedida(anchoM, altoM)
  const piezas = [{ nombre, talles: new Map([[talle, segsRectangulo(anchoM * 100, altoM * 100)]]) }]
  const r = construirPdfPiezas(mupdf, piezas, [talle], 1.0)
  return { pdf: r.pdf, resumen: { ...r.resumen, archivo: 'molde a medida', a_medida: true } }
}

/**
 * ¿La pieza entra en la tela? (regla del usuario 2026-10-06: «si la medida supera el ancho de la
 * tela no se deja elegir ni pasar al paso siguiente»). La mesa de la tela (`anchoCm`, lo que nestea
 * la tizada: tela − margen de la tela) y el largo máximo (`largoMaxCm`, del preset de nesting) se
 * achican por el margen del nesting a cada lado; la pieza crece por el borde de corte. Se puede girar
 * 90° sólo si el nesting de ese molde gira (`rotacion` «90» o «libre»).
 * Devuelve `{cabe, girada, motivo}`.
 */
export function cabeEnTela({ anchoM, altoM, bordeMm = 0, anchoCm, largoMaxCm, margenNestingMm = 0, rotacion = 'ninguna' }) {
  const b = 2 * (Number(bordeMm) || 0) / 10
  const w = anchoM * 100 + b
  const h = altoM * 100 + b
  const mg = 2 * (Number(margenNestingMm) || 0) / 10
  const util = Number(anchoCm) - mg
  const largo = Number(largoMaxCm) - mg
  const gira = rotacion === '90' || rotacion === 'libre'
  if (w <= util + 1e-6 && h <= largo + 1e-6) return { cabe: true, girada: false, motivo: null }
  if (gira && h <= util + 1e-6 && w <= largo + 1e-6) return { cabe: true, girada: true, motivo: null }
  const cm = (x) => (Math.round(x * 10) / 10).toString().replace('.', ',')
  let motivo
  if (Math.min(w, gira ? h : w) > util + 1e-6) {
    motivo = `La pieza mide ${cm(w)} cm de ancho${b ? ' con el borde de corte' : ''} y en esta tela entran ${cm(util)} cm`
      + (gira ? ' (ni girándola)' : '') + '.'
  } else {
    motivo = `La pieza mide ${cm(h)} cm de largo${b ? ' con el borde de corte' : ''} y la mesa más larga es de ${cm(largo)} cm.`
  }
  return { cabe: false, girada: false, motivo }
}
