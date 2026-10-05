// LA PLANTILLA DE UNA VARIABLE, SIN ABRIR EL MOLDE EN CONFIGURACIÓN (2026-10-05, «Crear plantilla»
// desde el paso Arte del pedido).
//
// La pestaña Plantilla de Moldería arma la guía, Illustrator y CorelDRAW con lo que tiene abierto
// la pantalla: la detección del talle guía (`etqData`), las variables del molde (`variantesEdit`) y
// el lienzo del visor (`canvasLayout`). Desde el pedido hay varias variables de varios moldes a la
// vez y ninguno está «abierto»: acá se calcula lo MISMO a partir de la detección de cada molde
// (`GET /api/plantilla/deteccion?pid=`) y de su variable del catálogo. Gemelos de App.jsx:
//   · `nombresDeVariable`   ↔ `nombresDeVariante`  (qué piezas pide la guía: `piezas=`)
//   · `posicionesDelVisor`  ↔ `canvasLayout` (cmPerUnit) + `varianteFiltro` + `_optsIllu._posVisor`
//   · `paramsPlantilla`     ↔ `_claveDatosIllu` / `descargarPdfGuia`
// Si cambia cómo el visor ubica una pieza o cómo se resuelve una variable, va en los dos lados.

/** `{id: clave}` de las piezas vivas del molde (identidad estable, talle-independiente). */
function idAClave(det) {
  const m = {}
  for (const p of (det && det.piezas_id) || []) if (p.id && p.clave && !p.retirada) m[p.id] = p.clave
  return m
}

/** Las claves (nombres estables) de las piezas de UNA variable. Sin variable → [] (= molde entero). */
export function nombresDeVariable(variable, det) {
  if (!variable) return []
  const id2clave = idAClave(det)
  const etq = (det && det.nombres_existentes) || {}
  return [...new Set((variable.valores || [])
    .map((v) => (id2clave[v.pieza_id] || etq[v.pieza_idx] || v.label || '').trim())
    .filter(Boolean))]
}

/**
 * Dónde dibuja el visor cada pieza (centro de su caja, en PUNTOS reales, «y» hacia abajo), por
 * nombre: lo que `planIllustrator` usa para armar cada mesa en el mismo lugar que se ve en
 * pantalla (`posiciones`). Con variable: sólo sus piezas y con su acomodo a mano (`acomodo_mm`).
 */
export function posicionesDelVisor(det, variable = null) {
  const piezas = (det && det.piezas) || []
  if (!piezas.length) return {}
  // cm por unidad del lienzo: el promedio de las piezas con medida (igual que `canvasLayout`)
  let suma = 0, n = 0
  for (const p of piezas) {
    if (p.pw > 2 && p.w_cm > 0) { suma += p.w_cm / p.pw; n++ }
    if (p.ph > 2 && p.h_cm > 0) { suma += p.h_cm / p.ph; n++ }
  }
  const cmU = n ? suma / n : 0
  if (!(cmU > 0)) return {}
  const etq = (det && det.nombres_existentes) || {}
  const nombreDe = (p) => (etq[p.idx] || p.name || '').trim()
  let visibles = piezas
  const pos = new Map()
  if (variable) {
    // `varianteFiltro`: por CLAVE estable si la variable la tiene; si no, también por pieza_idx
    const id2clave = idAClave(det)
    const nombres = new Set((variable.valores || [])
      .map((v) => (id2clave[v.pieza_id] || etq[v.pieza_idx] || v.label || '').trim()).filter(Boolean))
    const usaId = (variable.valores || []).some((v) => v.pieza_id && id2clave[v.pieza_id])
    const idxs = new Set((variable.valores || []).map((v) => v.pieza_idx))
    visibles = piezas.filter((p) => {
      const nm = nombreDe(p)
      if (nm && nombres.has(nm)) return true
      return !usaId && idxs.has(p.idx)
    })
    const ac = variable.acomodo_mm || {}
    for (const p of visibles) { const o = ac[nombreDe(p)]; if (o) pos.set(p.idx, { dx: o.x, dy: o.y }) }
  }
  const PT = 72 / 2.54
  const out = {}
  for (const p of visibles) {
    const nm = nombreDe(p)
    if (!nm) continue
    const o = pos.get(p.idx)
    ;(out[nm] = out[nm] || []).push({ x: (p.px + p.pw / 2 + (o ? o.dx : 0)) * cmU * PT, y: (p.py + p.ph / 2 + (o ? o.dy : 0)) * cmU * PT })
  }
  return out
}

/** Los talles del molde, en el orden del archivo (como `tallesMolde`). */
export const tallesDeDeteccion = (det) => ((det && det.talles_reales && det.talles_reales.length) ? det.talles_reales : ((det && det.talles) || []))

/**
 * La pedida de `GET /api/plantilla/pdf_guia` para una variable: `{pid, config, rango, guia, talles,
 * piezas, datos, formato, capas}` → query string. `talles` null = todos; `piezas` [] = molde entero.
 */
export function paramsPlantilla({ pid, config = 'default', rango = [], guia = null, talles = null, piezas = [], datos = true, formato = 'ai', capas = null }) {
  const q = new URLSearchParams({ config, formato })
  if (datos) q.set('datos', '1')
  if (pid) q.set('pid', pid)
  if (capas) q.set('capas', JSON.stringify(capas))
  if (config === 'rango' && rango && rango.length) q.set('rango', rango.join(','))
  if (talles) q.set('talles', talles.join(','))
  if (guia) q.set('guia', guia)
  if (piezas && piezas.length) q.set('piezas', JSON.stringify(piezas))
  return q.toString()
}
