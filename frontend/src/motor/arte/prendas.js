// QUÉ PIEZAS ENTRAN EN UNA PRENDA — traducción de `motor_pedido.tokens_pieza`, `partes_de_libre` y
// `piezas_de` (PLAN_NAVEGADOR.md, etapas 3 y 4). Las prendas llegan ya traducidas por el servidor
// (`/api/productos/<pid>/prendas` → `_traducir_prendas`: talle, personalización, toggles, variable);
// acá se decide, con la MISMA regla que el motor, qué piezas del registro lleva cada una.

/** `tokens_pieza`: tokens normalizados del nombre (minúsculas, sin acentos, sin paréntesis). */
export function tokensPieza(nombre) {
  const s = String(nombre).normalize('NFKD').replace(/[̀-ͯ]/g, '')
  return s.toLowerCase().replace(/\(/g, ' ').replace(/\)/g, ' ').split(/\s+/).filter(Boolean)
}

/** `partes_de_libre`: las piezas de la prenda según sus TOGGLES (manga corta/larga, sisa…). */
export function partesDeLibre(prenda, piezasNombres) {
  let toggles = prenda && typeof prenda === 'object' ? prenda.toggles : null
  if (!toggles || !toggles.length) {
    const mval = prenda && typeof prenda === 'object' ? prenda.manga : prenda
    if (mval) toggles = [{ clave: 'manga', opcion: mval, opciones: ['corta', 'larga'] }]
    else return piezasNombres.slice()
  }
  const norm = []
  for (const tg of toggles) {
    const clave = String(tg.clave || '').trim().toLowerCase()
    const opcion = String(tg.opcion || '').trim().toLowerCase()
    let opciones = (tg.opciones || []).map((o) => String(o).trim().toLowerCase()).filter(Boolean)
    if (opcion && !opciones.includes(opcion)) opciones = opciones.concat([opcion])
    if (!clave || !opcion) continue
    norm.push([clave, opcion.split(/\s+/), opciones.filter((o) => o !== opcion).map((o) => o.split(/\s+/))])
  }
  if (!norm.length) return piezasNombres.slice()
  let out = []
  for (const p of piezasNombres) {
    const tset = new Set(tokensPieza(p))
    let incluir = true
    for (const [clave, sel, otras] of norm) {
      if (!tset.has(clave)) continue
      if (sel.every((t) => tset.has(t))) continue
      if (otras.some((o) => o.every((t) => tset.has(t)))) { incluir = false; break }
    }
    if (incluir) out.push(p)
  }
  const juntas = prenda && typeof prenda === 'object' ? prenda.juntas_piezas : null
  if (juntas) {
    const names = new Set(piezasNombres)
    let outset = new Set(out)
    for (const grp of juntas) {
      const miembros = grp.filter((m) => names.has(m))
      if (miembros.length >= 2 && !miembros.every((m) => outset.has(m))) {
        out = out.filter((p) => !miembros.includes(p))
        outset = new Set(out)
      }
    }
  }
  return out
}

/** `sorted(registro.keys())` de Python (orden por código de carácter). */
export function nombresDelRegistro(registro) {
  return Object.keys(registro).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0))
}

/** `piezas_de`: los toggles INTERSECTADOS con la variable elegida (`variante_piezas`). */
export function piezasDe(prenda, registro) {
  const nombres = nombresDelRegistro(registro)
  const base = partesDeLibre(prenda, nombres)
  if (!prenda || typeof prenda !== 'object') return base
  let permit = null
  if (prenda.variante_piezas && prenda.variante_piezas.length) permit = new Set(prenda.variante_piezas)
  else if (prenda.variante_idx && prenda.variante_idx.length) {
    const idxANombre = {}
    for (const [nom, pt] of Object.entries(registro)) {
      for (const info of Object.values(pt || {})) if (info && info.pieza_idx != null) idxANombre[Number(info.pieza_idx)] = nom
    }
    permit = new Set(prenda.variante_idx.map((i) => idxANombre[Number(i)]).filter(Boolean))
  }
  if (!permit || !permit.size) return base
  return base.filter((p) => permit.has(p))
}
