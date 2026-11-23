// EL ARTE DEL PEDIDO VIVE EN ESTA PC — PLAN_ARTE_EN_LA_PC.md, entrega 1 (MAPA 760).
//
// 🔴 POR QUÉ: el arte de un pedido se guardaba en el servidor en una carpeta por molde + NOMBRE del diseño
// (`entrada/<pid>/disenos/jugador/arte.ai`), la MISMA para todas las personas: dos personas con el mismo molde y
// «JUGADOR» se pisaban, y al rehacer la tizada el motor bajaba el arte de la otra (MAPA 758). Acá queda guardado
// el de ESTE pedido, en IndexedDB, con clave POR PEDIDO: los bytes (vigente y original), su versión y lo que
// calculó el análisis del arte (detección, mapeo, mapeo por nombre, personalización, validación). Todo lo que lee
// el arte del pedido pasa por `aplicarArtesPc` (el sello del diseño pasa a ser `pc,<pedido>,<sha1>,<versión>`:
// la caché nunca lo baja del servidor, como el molde con diseño, MAPA 585) y el plan recibe estos datos
// (`datosPlanPc`) en vez de leerlos de la carpeta del servidor.
//
// Sin pedido fijado (el robot de la API, en Node) no hay nada acá y todo sigue como antes.
import { leerCache, tieneCache, guardarCache, clavesCache, borrarCache, claveDe } from '../cache.js'
import { enHiloSuelto } from '../hiloSuelto.js'
import { persConLimite } from '../pieza/estampar.js'
import { pedirMotorB } from './motorB.js'

let _pedido = null
/** El pedido en curso (`tizada_wizard.pedidoPc`). Sin él, nada se guarda ni se lee de la PC. */
export function fijarPedidoPc(id) { _pedido = id || null }

// las claves llevan `|pc,` (como el molde con diseño): la descarga de fondo de los moldes NO las borra
const kMeta = (pedido, pid, dis) => `artepc|${pid}|${dis}|pc,${pedido}`
const kOrig = (pedido, pid, dis, sha1) => `arte-original|${pid}|${dis}|pc,${pedido},${sha1}`
const selloPc = (m) => ['pc', m.pedido, m.sha1, m.version]
const dis0 = (d) => d || 'principal'

async function leerMeta(pid, diseno) {
  if (!_pedido || !pid) return null
  return leerMetaDe(_pedido, pid, dis0(diseno))
}
async function leerMetaDe(pedido, pid, dis) {
  const b = await leerCache(kMeta(pedido, pid, dis))
  if (!b) return null
  try { return JSON.parse(new TextDecoder().decode(b)) } catch { return null }
}
// 🔴 TODO LO QUE CAMBIA EL REGISTRO DEL ARTE VA EN FILA (MAPA 764): cada cambio lee el registro, espera y lo vuelve a
// escribir entero; dos a la vez (un mapeo a mano mientras se calcula el perfil, una versión nueva mientras se guarda
// un objeto) se pisaban, y en el peor caso la versión volvía atrás a una que ya se había borrado.
let _fila = Promise.resolve()
function enFila(fn) {
  const p = _fila.then(fn, fn)
  _fila = p.catch(() => {})
  return p
}
const escribirMeta = (m) => guardarCache(kMeta(m.pedido, m.pid, m.diseno), new TextEncoder().encode(JSON.stringify(m)))

/** ¿Este arte (molde, diseño) del pedido en curso está en la PC? → sus datos, o null. */
export const artePc = (pid, diseno) => leerMeta(pid, diseno)
/** …y con sus bytes (lo que de verdad usan el motor y la tizada). */
export async function arteEnPc(pid, diseno) {
  const m = await leerMeta(pid, diseno)
  return !!(m && await tieneCache(claveDe.arte(m.pid, m.diseno, selloPc(m))))
}

/**
 * Guarda el arte recién cargado. `datos` = lo que calculó el análisis (`prepararArteEnNavegador`):
 * `{det, auto, pers, mapeo, pv, validacion}`. Reemplaza al que hubiera (otro archivo = versión 0 otra vez).
 */
export function guardarArtePc(args) { return enFila(() => _guardarArtePc(args)) }
async function _guardarArtePc({ pid, diseno, nombre, bytes, sha1, datos }) {
  if (!_pedido || !pid || !bytes || !sha1) return null
  await soltarArtePc(pid, diseno)
  const m = { pedido: _pedido, pid, diseno: dis0(diseno), nombre: nombre || dis0(diseno), sha1, version: 0,
              bytes: bytes.byteLength, datos: datos || {}, calc: {} }
  await guardarCache(kOrig(m.pedido, pid, m.diseno, sha1), bytes)
  await guardarCache(claveDe.arte(pid, m.diseno, selloPc(m)), bytes)
  await escribirMeta(m)
  // que el navegador no lo borre por su cuenta si el disco se llena (best-effort: puede decir que no)
  try { if (navigator.storage && navigator.storage.persist) navigator.storage.persist() } catch { /* nada */ }
  return m
}

/** «Editar diseño» armó una versión nueva (el PDF editado): pasa a ser la vigente. El original no cambia. */
export function versionNuevaPc(pid, diseno, bytes) { return enFila(() => _versionNuevaPc(pid, diseno, bytes)) }
async function _versionNuevaPc(pid, diseno, bytes) {
  const m = await leerMeta(pid, diseno)
  if (!m || !bytes) return null
  const vieja = claveDe.arte(pid, m.diseno, selloPc(m))
  m.version += 1
  m.bytes = bytes.byteLength
  m.calc = {}                                     // lo calculado sobre el archivo viejo ya no vale
  await guardarCache(claveDe.arte(pid, m.diseno, selloPc(m)), bytes)
  await escribirMeta(m)
  await borrarCache([vieja])
  return m
}

/** Cambió lo que se guarda del arte sin cambiar el archivo (el mapeo a mano, la validación tras una fuente). */
export function actualizarDatosPc(pid, diseno, parche) { return enFila(() => _actualizarDatosPc(pid, diseno, parche)) }
async function _actualizarDatosPc(pid, diseno, parche) {
  const m = await leerMeta(pid, diseno)
  if (!m) return null
  m.datos = { ...m.datos, ...parche }
  await escribirMeta(m)
  return m
}

/** Los bytes del arte ORIGINAL (el que se cargó, sin las ediciones). */
export async function originalPc(pid, diseno) {
  const m = await leerMeta(pid, diseno)
  return m ? leerCache(kOrig(m.pedido, pid, m.diseno, m.sha1)) : null
}
/** Los bytes del arte VIGENTE (con las ediciones). */
export async function vigentePc(pid, diseno) {
  const m = await leerMeta(pid, diseno)
  return m ? leerCache(claveDe.arte(pid, m.diseno, selloPc(m))) : null
}

/** El mapeo que rige para una VARIABLE — gemelo de `_mapeo_efectivo` (servidor): el suyo si lo tiene, si no la base. */
export function mapeoEfectivo(base, pv, variante) {
  const v = String(variante || '').trim()
  return { ...((v && pv && v in pv) ? pv[v] : (base || {})) }
}

/**
 * Los datos de `/motor_b` con los artes de ESTE pedido que están en la PC: el sello, la versión y lo calculado
 * salen de acá (el servidor puede tener el arte de OTRA persona con el mismo nombre de diseño). Lo de configuración
 * del molde (editables, colores, marcas, objetos) sigue viniendo del servidor.
 */
export async function aplicarArtesPc(info, pid) {
  if (!_pedido || !info || !info.camino_a) return info
  const metas = await metasDe(pid)
  // 🔴 un diseño del servidor que NO está en esta PC (salvo el «principal», que es la config del molde) no es de este
  // pedido: es la carpeta compartida — antes de cargar el arte se veían las tipografías del arte de OTRA persona
  // (inspector, MAPA 770). Se saca; su config del molde sigue en `cfg_disenos`.
  const vivos = []
  for (const m of metas) if (await vivo(m)) vivos.push(m)        // sin sus bytes en la PC tampoco cuenta (se pide volver a cargarlo)
  const propios = new Set(vivos.map((m) => m.diseno))
  const disenos = (info.disenos || []).filter((d) => d.id === 'principal' || propios.has(d.id))
  if (!metas.length) return { ...info, disenos }
  for (const m of metas) {
    // 🔴 sin los bytes en la PC (el navegador liberó el disco) NO se marca: `traerConCache` bajaría el del servidor,
    // que puede ser el de otra persona. Queda como antes de esta entrega (lo que tenga el servidor).
    if (!(await vivo(m))) continue
    const i = disenos.findIndex((d) => d.id === m.diseno)
    // la config del diseño en el MOLDE (posiciones base, colores, marcas) la manda el servidor aunque no tenga el arte
    const srv = i >= 0 ? disenos[i] : { editables_cfg: {}, editables_color: {}, editables_marca: {}, editables_sin_marca: {},
                                        ...((info.cfg_disenos || {})[m.diseno] || {}) }
    const d = m.datos || {}
    const oa = oaDe(m)
    const local = { ...srv, id: m.diseno, nombre: m.nombre, sub: srv.sub || null, sello: selloPc(m), bytes: m.bytes,
                    version: m.version, version_srv: srv.version, mapeo: { mapeo: d.mapeo || {}, por_variable: d.pv || {} },
                    validacion: d.validacion || {}, pers: persConLimite(d.pers || {}, info.limite_texto), en_pc: true,
                    objetos: oa.objetos, inyectadas: oa.inyectadas.map((x) => x.capa) }
    if (i >= 0) disenos[i] = local; else disenos.push(local)
  }
  return { ...info, disenos }
}

const vivo = (m) => tieneCache(claveDe.arte(m.pid, m.diseno, selloPc(m)))

async function metasDe(pid) {
  if (!_pedido) return []
  const claves = (await clavesCache()).filter((k) => k.startsWith(`artepc|${pid}|`) && k.endsWith(`|pc,${_pedido}`))
  const out = []
  for (const k of claves) {
    const b = await leerCache(k)
    try { if (b) out.push(JSON.parse(new TextDecoder().decode(b))) } catch { /* una meta rota no frena nada */ }
  }
  return out
}

// lo que el servidor pedía calcular sobre SU archivo (428 `_arte_calc`): acá, sobre el de la PC, una vez por versión
const CALC = { editables: 'arte_editables', perfil: 'arte_perfil', mapeo_talles: 'arte_mapeo_variantes' }
async function calcular(m, cual, args = null) {
  // con argumentos (el registro del molde) lo guardado vale para ESOS argumentos: si el molde cambió, se rehace
  const k = args ? `${cual}|${JSON.stringify(args)}` : cual
  if (m.calc && k in m.calc) return m.calc[k]
  const bytes = await leerCache(claveDe.arte(m.pid, m.diseno, selloPc(m)))
  if (!bytes) return null
  let r = null
  try { r = JSON.parse(await enHiloSuelto('arte_calculo', { bytes, fn: CALC[cual], args: args || {} }, [bytes.buffer], 'arte')) } catch { r = null }
  if (r && r.__error__) r = null
  // se anota en la fila y sobre el registro de AHORA: si mientras se calculaba cambió la versión, ya no vale
  await enFila(async () => {
    const cur = await leerMetaDe(m.pedido, m.pid, m.diseno)
    if (!cur || cur.sha1 !== m.sha1 || cur.version !== m.version) return
    cur.calc = { ...Object.fromEntries(Object.entries(cur.calc || {}).filter(([c]) => !c.startsWith(cual + '|'))), [k]: r }
    await escribirMeta(cur)
  })
  m.calc = { ...(m.calc || {}), [k]: r }
  return r
}

/**
 * Lo que devolvía `/api/arte/deteccion` para un arte del pedido que está en la PC: las mesas, el mapeo de la
 * variable (gemelo de `_mapeo_efectivo` + el automático por nombre si no hay nada asignado, MAPA 700) y el mapeo por
 * talle salen del arte de ACÁ; del servidor sólo lo del MOLDE (`?solo_molde=1`: registro, orden, mapeo fijo, piezas
 * de la variable). `null` si ese arte no está en la PC (entonces se pregunta como siempre).
 */
export async function deteccionPc({ pid, diseno, variante = '', rutaApi = (x) => x }) {
  const m = await leerMeta(pid, diseno)
  if (!m || !m.datos || !m.datos.det || !(await vivo(m))) return null
  const q = `solo_molde=1&diseno=${encodeURIComponent(m.diseno)}&variante=${encodeURIComponent(variante || '')}&pid=${encodeURIComponent(pid)}`
  const r = await fetch(rutaApi(`/api/arte/deteccion?${q}`))
  if (!r.ok) return null
  const molde = await r.json()
  const d = m.datos
  const det = JSON.parse(JSON.stringify(d.det))
  det.modo = 'separado'
  const base = d.mapeo || {}, pv = d.pv || {}, v = String(variante || '').trim()
  det.mapeo = mapeoEfectivo(base, pv, v)
  if (!Object.keys(det.mapeo).length && (!(v in pv) || (!Object.keys(base).length && !Object.values(pv).some((x) => x && Object.keys(x).length))))
    det.mapeo = { ...(d.auto || {}) }
  if (molde.piezas_variable) det.piezas_variable = molde.piezas_variable
  det.mapeo_fijo = molde.mapeo_fijo || {}
  det.validacion = d.validacion || null          // «Aprobado / Observado» del paso Arte: la de ESTE arte
  det.mapeo_talles = (await calcular(m, 'mapeo_talles', { registro: molde.registro || {}, orden: molde.orden || [] })) || {}
  // la firma de las mesas = el sello del arte en la PC: `localizarMesas` lo encuentra en la caché sin bajar nada
  det.firma_pc = selloPc(m).join(',')
  return det
}

/** El perfil de color que TRAE el arte de la PC (`{tiene, nombre, espacio}`), o null si no está acá. */
export async function perfilPc(pid, diseno) {
  const m = await leerMeta(pid, diseno)
  return m ? calcular(m, 'perfil') : null
}

// ── OBJETOS AGREGADOS («Editar diseño → Agregar objeto») ─────────────────────────────────────────────────────────
// Lo que el servidor guardaba en `objetos_agregados.json` + un PDF por objeto, en la carpeta compartida del diseño:
// acá van con el arte del pedido. `archivo` lleva el pedido (`pc,<pedido>,<id>.pdf`) para que la clave de la caché
// que arman el motor y el editor (`oa|pid|dis|id|archivo`) tenga `|pc,` y nunca se pida al servidor.
const oaDe = (m) => ({ objetos: [], inyectadas: [], n: 0, ...((m.datos || {}).oa || {}) })
const kObj = (m, o) => `oa|${m.pid}|${m.diseno}|${o.id}|${o.archivo}`
// el número nunca se repite (el servidor reusaba el de un objeto ya colocado: acá la clave de la caché lo lleva)
const idNuevo = (oa) => { oa.n = Math.max(oa.n || 0, ...oa.objetos.map((o) => Number(String(o.id).split('_').pop()) || 0)) + 1; return `oa_${oa.n}` }
function cambiarOa(pid, diseno, fn) { return enFila(() => _cambiarOa(pid, diseno, fn)) }
async function _cambiarOa(pid, diseno, fn) {
  const m = await leerMeta(pid, diseno)
  if (!m) throw new Error('el diseño no está en esta computadora')
  const oa = oaDe(m)
  const r = await fn(oa, m)
  m.datos = { ...m.datos, oa }
  await escribirMeta(m)
  return r
}
/** Guarda un objeto ya normalizado (PDF de una página + su medida). Devuelve el objeto como lo daba el servidor. */
export function objetoAgregarPc(pid, diseno, { pdf, nombre, w_cm, h_cm, tipo }) {
  return cambiarOa(pid, diseno, async (oa, m) => {
    const id = idNuevo(oa)
    const obj = { id, nombre: String(nombre || '').trim() || 'Objeto', archivo: `pc,${m.pedido},${id}.pdf`,
                  w_cm: Math.round(Number(w_cm || 0) * 100) / 100, h_cm: Math.round(Number(h_cm || 0) * 100) / 100,
                  tipo: tipo === 'imagen' ? 'imagen' : 'vector' }
    await guardarCache(kObj(m, obj), pdf)
    oa.objetos.push(obj)
    return obj
  })
}
/** Cambia un objeto (`fn(obj)`): su transform por variable/talle o la pieza. */
export function objetoCambiarPc(pid, diseno, oid, fn) {
  return cambiarOa(pid, diseno, async (oa) => {
    const o = oa.objetos.find((x) => x.id === oid)
    if (!o) throw new Error('el objeto ya no está')
    fn(o)
    return o
  })
}
/** Gemelo de `_clamp_tf` (servidor): el signo es ESPEJO, sólo se acota la magnitud de la escala. */
function clampTf(v) {
  v = v || {}
  const cl = (x) => { x = Number(x); const s = x < 0 ? -1 : 1; return s * Math.max(0.05, Math.min(20, Math.abs(x))) }
  const sc = cl(v.scale || 1)
  return { dx: Number(v.dx || 0), dy: Number(v.dy || 0), rot: Number(v.rot || 0), scale: sc,
           sx: cl(v.sx != null ? v.sx : sc), sy: cl(v.sy != null ? v.sy : sc) }
}
/** Lo que hacía `/objeto_agregado/<id>/transform`: el transform POR VARIABLE y talle (+ la pieza). */
export function objetoTransformPc(pid, diseno, oid, { variante = '*', talles = [], transform, pieza }) {
  return objetoCambiarPc(pid, diseno, oid, (o) => {
    const porv = ((o.transforms = o.transforms || {})[String(variante || '*')] = o.transforms[String(variante || '*')] || {})
    for (const t of (talles && talles.length ? talles : ['*'])) porv[String(t)] = clampTf(transform)
    if (pieza) o.pieza = pieza
  })
}
/** Los bytes (PDF) de un objeto. */
export async function objetoBytesPc(pid, diseno, oid) {
  const m = await leerMeta(pid, diseno)
  const o = m && oaDe(m).objetos.find((x) => x.id === oid)
  return o ? leerCache(kObj(m, o)) : null
}
/** DUPLICAR: copia (archivo + entrada) sin pieza, con el transform del original; el nombre como el servidor. */
export function objetoDuplicarPc(pid, diseno, oid) {
  return cambiarOa(pid, diseno, async (oa, m) => {
    const o = oa.objetos.find((x) => x.id === oid)
    if (!o) throw new Error('el objeto ya no está')
    const bytes = await leerCache(kObj(m, o))
    if (!bytes) throw new Error('el archivo del objeto no está en esta computadora')
    const id = idNuevo(oa)
    const usados = new Set(oa.objetos.map((x) => x.nombre))
    const base = o.nombre || id
    let nombre = `${base} (copia)`, k = 2
    while (usados.has(nombre)) nombre = `${base} (copia ${k++})`
    const nuevo = { ...JSON.parse(JSON.stringify(o)), id, archivo: `pc,${m.pedido},${id}.pdf`, nombre, pieza: '' }
    await guardarCache(kObj(m, nuevo), bytes)
    oa.objetos.push(nuevo)
    return nuevo
  })
}
/** BORRAR el objeto (y su archivo). */
export function objetoBorrarPc(pid, diseno, oid) {
  return cambiarOa(pid, diseno, async (oa, m) => {
    const o = oa.objetos.find((x) => x.id === oid)
    if (o) await borrarCache([kObj(m, o)])
    oa.objetos = oa.objetos.filter((x) => x.id !== oid)
  })
}
/** COLOCADO: ya vive DENTRO del arte como capa «Editable …» → sale de la lista y queda anotado que esa capa la
 *  agregó el usuario (la única que se puede quitar). */
export function objetoColocadoPc(pid, diseno, oid, { capa, pieza, mesas }) {
  return cambiarOa(pid, diseno, async (oa, m) => {
    const o = oa.objetos.find((x) => x.id === oid)
    oa.inyectadas.push({ capa, nombre: o ? o.nombre : capa, pieza: String(pieza || ''), mesas: (mesas || []).map(Number) })
    if (o) await borrarCache([kObj(m, o)])
    oa.objetos = oa.objetos.filter((x) => x.id !== oid)
    return o
  })
}
/** Se quitó del arte una capa que había agregado el usuario. */
export function capaQuitadaPc(pid, diseno, capa) {
  return cambiarOa(pid, diseno, async (oa) => { oa.inyectadas = oa.inyectadas.filter((x) => x.capa !== capa) })
}

/** Nombre de diseño → slug: gemelo EXACTO de `_slugify_diseno` (servidor), con el que el plan arma las filas. */
export function slugDiseno(s) {
  const t = String(s || '').trim().toLowerCase()
  if (!t || t === 'principal' || t === 'default') return 'principal'
  return t.replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 48) || 'principal'
}

/**
 * 🔴 EL MAPEO QUE SE VE (MAPA 804): sin nada asignado, el paso Arte muestra el mapeo fijo del molde o, si no hay, las
 * SUGERENCIAS de la detección (`_aplicarDetArte` en App.jsx) — la Bandera a medida se veía «Frente ✓» — pero eso no
 * se guardaba y al plan iba `auto: {}` → `mapeo_arte: null`, la pieza en blanco y la tizada no salía. Lo mismo que se
 * ve va como `auto` (el servidor lo usa sólo cuando no hay mapeo propio, igual que la pantalla).
 */
async function autoDe(m, pid, rutaApi) {
  const d = m.datos || {}
  if (d.auto && Object.keys(d.auto).length) return d.auto
  // el mismo orden que la pantalla: el automático por nombre → el mapeo FIJO del molde → las sugerencias de la detección
  try {
    const q = `solo_molde=1&diseno=${encodeURIComponent(m.diseno)}&pid=${encodeURIComponent(pid)}`
    const r = await fetch(rutaApi(`/api/arte/deteccion?${q}`))
    const fijo = r.ok ? ((await r.json()) || {}).mapeo_fijo : null
    if (fijo && Object.keys(fijo).length) return { ...fijo }
  } catch { /* sin el molde: las sugerencias */ }
  const sug = {}
  for (const me of (d.det || {}).mesas || []) if (me && me.sugerencia) sug[me.sugerencia] = me.mesa
  return sug
}

/**
 * Lo que el plan del pedido necesita de cada arte en la PC → `{<slug del NOMBRE del diseño>: {<pid>: {...}}}` (va en
 * el cuerpo como `artes_pc`; el servidor lo usa ANTES que su carpeta). El editable y el perfil se calculan sobre el
 * archivo de la PC la primera vez y quedan guardados con él.
 */
export async function datosPlanPc(pids, rutaApi = (x) => x) {
  const out = {}
  if (!_pedido) return out
  for (const pid of pids || []) {
    const metas = await metasDe(pid)
    // el mapeo POR TALLE (la ficha dice en qué talles va cada objeto) necesita el registro y el orden del molde
    let molde = null
    if (metas.length) {
      try { molde = await pedirMotorB(rutaApi(`/api/productos/${encodeURIComponent(pid)}/motor_b`)) } catch { molde = null }   // MAPA 771
    }
    for (const m of metas) {
      if (!(await vivo(m))) continue                // mismo criterio que `aplicarArtesPc`
      const d = m.datos || {}
      const slug = slugDiseno(m.nombre)
      ;(out[slug] = out[slug] || {})[pid] = {
        validacion: d.validacion || {}, pers: d.pers || {}, mapeo: d.mapeo || {}, por_variable: d.pv || {},
        auto: await autoDe(m, pid, rutaApi), editables: await calcular(m, 'editables'), perfil: await calcular(m, 'perfil'),
        objetos: oaDe(m).objetos,
        mapeo_variantes: molde && molde.registro
          ? await calcular(m, 'mapeo_talles', { registro: molde.registro, orden: molde.orden_var || [] }) : null,
      }
    }
  }
  return out
}

/** Borra lo guardado de un arte del pedido en curso (otro archivo para ese diseño, o se quitó). */
export async function soltarArtePc(pid, diseno) {
  if (!_pedido) return
  const dis = dis0(diseno)
  const claves = (await clavesCache()).filter((k) => k.endsWith(`|pc,${_pedido}`) && k.startsWith(`artepc|${pid}|${dis}|`)
    || (k.startsWith(`arte|${pid}|${dis}|pc,${_pedido},`)) || (k.startsWith(`arte-original|${pid}|${dis}|pc,${_pedido},`))
    || (k.startsWith(`oa|${pid}|${dis}|`) && k.includes(`|pc,${_pedido},`)))
  await borrarCache(claves)
}

/** Borra los artes de los pedidos que NO están en `salvo` (un número o un conjunto: el pedido nuevo + los que tienen
 *  abiertos OTRAS pestañas, MAPA 762) — «Nuevo pedido», «Terminar pedido». */
export async function soltarArtesPc(salvo = null) {
  const quedan = salvo instanceof Set ? salvo : new Set([salvo])
  const de = (k) => {
    const m = /^(?:artepc|arte|arte-original)\|[^|]+\|[^|]+\|pc,([^,|]+)/.exec(k) || /^oa\|[^|]+\|[^|]+\|[^|]+\|pc,([^,|]+),/.exec(k)
    return m ? m[1] : null
  }
  // sólo las claves de ESTE módulo: las de los moldes con diseño (`plantilla-…|pc,`, `<pid>|mN.pdf|pc,`) no se tocan
  const claves = (await clavesCache()).filter((k) => /^(?:artepc|arte-original)\|/.test(k) || /^arte\|[^|]+\|[^|]+\|pc,/.test(k)
    || /^oa\|[^|]+\|[^|]+\|[^|]+\|pc,/.test(k))
  await borrarCache(claves.filter((k) => { const p = de(k); return p && !quedan.has(p) }))
}
