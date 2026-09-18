// LA VISTA PREVIA DE LAS PIEZAS, ARMADA EN ESTA COMPUTADORA — PLAN_NAVEGADOR.md, etapa 3 (camino B).
//
// Es lo que hacía `POST /api/arte/preview_piezas` → `_piezas_base` → `generar_pedido(solo_piezas)`
// → `get_svg_image` en el pool de render del servidor. Ahora: el servidor entrega el molde
// desplegado, el registro, los placeholders, el borde, la etiqueta y las tipografías
// (`/api/productos/<pid>/motor_b`, `/desplegado/<archivo>`, `/api/fuente/archivo/<archivo>`) y las
// prendas de muestra ya traducidas (`/prendas`); el hilo de trabajo arma cada pieza (base +
// estampado, `obrero.worker.js` → `pieza`) y la convierte a SVG. El resultado tiene la MISMA forma
// que la respuesta del servidor: `{piezas: {nombre: {svg, w_cm, h_cm}}, talle}`.
import { crearPool } from '../pool.js'
import { traerConCache, base64DeTexto } from '../cache.js'
import { piezasDe } from './prendas.js'
export { asegurarFuentes }
import { pyRound } from '../py.js'

const CM = 28.3465
const motores = new Map()          // pid → {info, pool, mesasAbiertas:Set, fuentesListas:bool}

async function json(url, opts) {
  const r = await fetch(url, opts)
  const d = await r.json().catch(() => ({}))
  if (!r.ok) { const e = new Error(d.error || `${url}: ${r.status}`); e.datos = d; throw e }
  return d
}

/** El motor de un molde: sus datos y su hilo. Se abre una vez por molde (y se rearma si cambió). */
export async function motorDe(pid, rutaApi, { reemplazos = null } = {}) {
  const q = reemplazos ? '?fuentes_reemplazo=' + encodeURIComponent(JSON.stringify(reemplazos)) : ''
  const info = await json(rutaApi(`/api/productos/${encodeURIComponent(pid)}/motor_b${q}`))
  if (!info.camino_b && !info.camino_a) return null
  const firma = JSON.stringify([(info.mesas || []).map((m) => m.sello), info.plantilla && info.plantilla.sello,
    (info.disenos || []).map((d) => [d.id, d.sello, d.mapeo, d.editables_cfg, d.editables_color, d.editables_marca, d.editables_sin_marca, d.objetos]),
    Object.keys(info.registro).length, info.borde, info.etiqueta, info.fuentes, info.editables_tamano])
  let m = motores.get(pid)
  if (m && m.firma !== firma) { try { m.pool.cerrar() } catch { /* nada */ } motores.delete(pid); m = null }
  if (!m) {
    m = { pid, info, firma, mesasAbiertas: new Set(), fuentesListas: false,
          pool: crearPool(1, () => new Worker(new URL('../obrero.worker.js', import.meta.url), { type: 'module' })) }
    motores.set(pid, m)
  } else {
    m.info = info
  }
  return m
}

async function asegurarMesa(m, rutaApi, mesa) {
  if (m.mesasAbiertas.has(mesa)) return
  const md = m.info.mesas.find((x) => x.mesa === mesa)
  if (!md || !md.paginas) throw new Error(`la mesa ${mesa} todavía no tiene sus páginas por talle`)
  const clave = `${m.pid}|m${mesa}.pdf|${(md.sello || []).join(',')}`
  const bytes = await traerConCache(clave, rutaApi(`/api/productos/${encodeURIComponent(m.pid)}/desplegado/m${mesa}.pdf`))
  await m.pool.enviar('mesa_abrir', { mesa, bytes }, [bytes.buffer])
  m.mesasAbiertas.add(mesa)
}

async function indiceMesa(m, rutaApi, mesa) {
  m.indices = m.indices || new Map()
  if (!m.indices.has(mesa)) {
    const md = m.info.mesas.find((x) => x.mesa === mesa)
    const clave = `${m.pid}|m${mesa}.json|${(md.sello || []).join(',')}`
    const bytes = await traerConCache(clave, rutaApi(`/api/productos/${encodeURIComponent(m.pid)}/desplegado/m${mesa}.json`))
    m.indices.set(mesa, JSON.parse(new TextDecoder().decode(bytes)))
  }
  return m.indices.get(mesa)
}

async function asegurarFuentes(m, rutaApi) {
  if (m.fuentesListas) return
  const { catalogo, alias } = m.info.fuentes
  const archivos = {}
  await Promise.all(catalogo.map(async (f) => {
    const url = rutaApi(`/api/fuente/archivo/${encodeURIComponent(f.archivo)}` + (f.propia ? `?pid=${encodeURIComponent(m.pid)}` : ''))
    archivos[f.archivo] = await traerConCache(`fuente|${f.hash}|${f.archivo}`, url)
  }))
  await m.pool.enviar('fuentes', { catalogo, archivos, alias }, Object.values(archivos).map((b) => b.buffer))
  m.fuentesListas = true
}

/**
 * Las previas de todas las piezas de una variable en un talle (lo que la pantalla del Arte pide).
 * `prendas`: si no se pasan, se piden al servidor las de muestra (NOMBRE / 00 y una fila por
 * opción de cada toggle, como `_piezas_base`).
 */
export async function previasCaminoB({ pid, variante, talle, rutaApi, reemplazos = null, prendas = null, avisar = null }) {
  const m = await motorDe(pid, rutaApi, { reemplazos })
  if (!m) return null
  if (m.info.paginas_pendientes) return { piezas: {}, talle, preparando: true }
  if (!prendas) {
    const d = await json(rutaApi(`/api/productos/${encodeURIComponent(pid)}/prendas`), {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ muestra: { variante, talle } }),
    })
    prendas = d.prendas || []
  }
  if (!prendas.length) return { piezas: {}, talle }
  await asegurarFuentes(m, rutaApi)
  const { registro, pers, borde, etiqueta, fuentes } = m.info
  // una pieza por nombre (la primera prenda que la trae), como `unicas` en `_piezas_base`
  const pedidos = []
  const vistas = new Set()
  prendas.forEach((pr, i) => {
    for (const pieza of piezasDe(pr, registro)) {
      if (vistas.has(pieza)) continue
      vistas.add(pieza)
      pedidos.push({ pieza, prenda: pr, nro: i + 1 })
    }
  })
  const piezas = {}
  let hechas = 0
  for (const { pieza, prenda, nro } of pedidos) {
    const t = prenda.talle
    const info = (registro[pieza] || {})[t]
    if (!info) continue
    const mesa = info.mesa
    await asegurarMesa(m, rutaApi, mesa)
    const idx = await indiceMesa(m, rutaApi, mesa)
    const conts = idx.talles[t] || []
    const cont = conts[info.idx_mesa ?? info.pieza_idx]
    if (!cont) continue
    const pagina = (idx.orden || []).indexOf(t)
    const persona = prenda.personalizacion || { nombre: prenda.nombre || '', numero: prenda.numero || '' }
    const r = await m.pool.enviar('pieza', {
      mesa, pagina, cont, borde, etiqueta, ph: (pers || {})[String(mesa)] || {}, persona, talle: t, pieza, nro,
      variante: prenda.variante_clave || null, grupo: prenda._grupo || null, info, alias: fuentes.alias, salida: 'svg',
    })
    piezas[pieza] = { svg: base64DeTexto(r.svg), w_cm: pyRound(r.w / CM, 2), h_cm: pyRound(r.h / CM, 2) }
    hechas++
    if (avisar) avisar(hechas, pedidos.length, pieza)
  }
  return { piezas, talle, cache: false, navegador: true }
}

// ── EL CAMINO A: el molde pelado + el arte separado ──────────────────────────────────────────
/** La plantilla (molde sin diseño) abierta en el hilo del motor `m`, con la clave `pid`. */
export async function asegurarMoldeA(m, rutaApi, pid, sello, hilo = null) {
  const h = hilo || m
  h.moldesA = h.moldesA || new Set()
  if (h.moldesA.has(pid)) return
  const bytes = await traerConCache(`plantilla|${pid}|${(sello || []).join(',')}`, rutaApi(`/api/productos/${encodeURIComponent(pid)}/descargar_plantilla`))
  await h.pool.enviar('molde_a_abrir', { clave: pid, bytes }, [bytes.buffer])
  h.moldesA.add(pid)
}

/** El diseño `id` del motor del camino A (`principal` si no se dice). */
export function disenoDe(m, id) {
  const d = (m.info.disenos || []).find((x) => x.id === (id || 'principal'))
  return d || null
}

/**
 * El contexto del arte separado en el hilo `h` (por defecto el del motor): baja el arte y los
 * objetos agregados (cacheados por su sello) y arma el contexto (`contexto_a`). `cfg` = lo que
 * cambia entre la vista previa y la tizada: `mapeoArte`, `editablesCfg/Tamano/Color/Marca/SinMarca`,
 * `marcasComoCruz`, `borde`, `referencia`. Devuelve `{clave, pers}`.
 */
export async function asegurarContextoA(m, rutaApi, diseno, cfg, { hilo = null, clave = null, conPersonalizacion = false } = {}) {
  const h = hilo || m
  const d = disenoDe(m, diseno)
  if (!d) throw new Error('este diseño no tiene el arte cargado')
  const k = clave || `${m.pid}|${d.id}|${(d.sello || []).join(',')}`
  const firma = JSON.stringify([k, cfg, conPersonalizacion])
  h.contextosA = h.contextosA || new Map()
  if (h.contextosA.get(k) && h.contextosA.get(k).firma === firma) return { clave: k, pers: h.contextosA.get(k).pers }
  const arte = await traerConCache(`arte|${m.pid}|${d.id}|${(d.sello || []).join(',')}`,
    rutaApi(`/api/productos/${encodeURIComponent(m.pid)}/arte_archivo` + (d.id !== 'principal' ? `?diseno=${encodeURIComponent(d.id)}` : '')))
  const objetos = []
  for (const o of (d.objetos || [])) {
    if (!o.archivo) continue
    const bytes = await traerConCache(`oa|${m.pid}|${d.id}|${o.id}|${o.archivo}`,
      rutaApi(`/api/productos/${encodeURIComponent(m.pid)}/objeto_agregado/${encodeURIComponent(o.id)}` + (d.id !== 'principal' ? `?diseno=${encodeURIComponent(d.id)}` : '')))
    objetos.push({ ...o, bytes: bytes.slice() })
  }
  const r = await h.pool.enviar('contexto_a', {
    clave: k, arte: arte.slice(), registro: m.info.registro, ordenVar: m.info.orden_var || [],
    mapeoArte: cfg.mapeoArte, editablesCfg: cfg.editablesCfg ?? null, editablesTamano: cfg.editablesTamano ?? null,
    editablesColor: cfg.editablesColor ?? null, editablesMarca: cfg.editablesMarca ?? null, editablesSinMarca: cfg.editablesSinMarca ?? null,
    marcasComoCruz: cfg.marcasComoCruz !== false, referencia: cfg.referencia || m.info.referencia_medida || 'alto',
    borde: cfg.borde === undefined ? m.info.borde : cfg.borde, objetos, conPersonalizacion,
  }, [...objetos.map((o) => o.bytes.buffer)])
  h.contextosA.set(k, { firma, pers: r.pers })
  return { clave: k, pers: r.pers }
}

/**
 * Las previas de las piezas de una variable en un talle, para un molde SIN diseño adentro con
 * su arte separado (camino A): lo que `POST /api/arte/preview_piezas` → `_piezas_base` hacía en
 * el servidor. `mapeo` = el mapeo {pieza: mesa} que la pantalla está mostrando; `editables` = el
 * ajuste del pedido (`{variable: {IDENT: {talle: tf}}}`, lo que se movió sin guardar).
 */
export async function previasCaminoA({ pid, diseno = null, variante, talle, rutaApi, reemplazos = null, mapeo = null, editables = null, prendas = null, avisar = null }) {
  const m = await motorDe(pid, rutaApi, { reemplazos })
  if (!m || !m.info.camino_a) return null
  const d = disenoDe(m, diseno)
  if (!d) return null
  if (!prendas) {
    const r = await json(rutaApi(`/api/productos/${encodeURIComponent(pid)}/prendas`), {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ muestra: { variante, talle } }),
    })
    prendas = r.prendas || []
  }
  if (!prendas.length) return { piezas: {}, talle }
  await asegurarFuentes(m, rutaApi)
  await asegurarMoldeA(m, rutaApi, pid, (m.info.plantilla || {}).sello)
  // el ajuste de editables del pedido, mergeado por el servidor con la base (`_editables_cfg`)
  let editablesCfg = d.editables_cfg, editablesColor = d.editables_color, editablesTamano = m.info.editables_tamano
  if (editables && Object.values(editables).some((v) => v && Object.keys(v).length)) {
    const e = await json(rutaApi(`/api/productos/${encodeURIComponent(pid)}/editables_cfg`), {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ diseno: d.id, editables }),
    })
    editablesCfg = e.editables_cfg; editablesColor = e.editables_color; editablesTamano = e.editables_tamano
  }
  // sin un mapeo dado por la pantalla, el guardado del diseño (base + por variable, como el motor)
  const mapeoArte = (mapeo && Object.keys(mapeo).length) ? mapeo : (d.mapeo && Object.keys(d.mapeo.mapeo || {}).length ? d.mapeo : null)
  if (!mapeoArte) return { piezas: {}, talle, navegador: true, sin_mapeo: true }
  const { clave, pers } = await asegurarContextoA(m, rutaApi, d.id, {
    mapeoArte, editablesCfg, editablesTamano, editablesColor, editablesMarca: d.editables_marca,
    editablesSinMarca: d.editables_sin_marca, marcasComoCruz: false, borde: m.info.borde, referencia: m.info.referencia_medida,
  }, { clave: `${pid}|${d.id}|previa`, conPersonalizacion: true })
  const { registro, etiqueta, fuentes } = m.info
  const pedidos = []
  const vistas = new Set()
  prendas.forEach((pr, i) => {
    for (const pieza of piezasDe(pr, registro)) {
      if (vistas.has(pieza)) continue
      vistas.add(pieza)
      pedidos.push({ pieza, prenda: pr, nro: i + 1 })
    }
  })
  const piezas = {}
  let hechas = 0
  for (const { pieza, prenda, nro } of pedidos) {
    const t = prenda.talle
    const info = (registro[pieza] || {})[t]
    if (!info) continue
    const persona = prenda.personalizacion || { nombre: prenda.nombre || '', numero: prenda.numero || '' }
    const r = await m.pool.enviar('pieza_a', {
      molde: pid, arte: clave, mesa: info.mesa, talle: t, pieza, info, persona, nro,
      variante: prenda.variante_clave || null, grupo: prenda._grupo || null, ph: pers || {}, etiqueta, alias: fuentes.alias, salida: 'svg',
    })
    piezas[pieza] = { svg: base64DeTexto(r.svg), w_cm: pyRound(r.w / CM, 2), h_cm: pyRound(r.h / CM, 2) }
    hechas++
    if (avisar) avisar(hechas, pedidos.length, pieza)
  }
  return { piezas, talle, cache: false, navegador: true }
}

/** Cierra los motores abiertos (al salir del pedido). */
export function cerrarMotores() {
  for (const m of motores.values()) { try { m.pool.cerrar() } catch { /* nada */ } }
  motores.clear()
}
