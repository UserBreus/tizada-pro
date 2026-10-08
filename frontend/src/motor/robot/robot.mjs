// EL ROBOT DE INTEGRACIÓN — arma, sin persona, los pedidos que llegan de otro sistema (MAPA 606).
//
//   node frontend/src/motor/robot/robot.mjs            (lo arranca solo el servidor)
//
// 🔴 POR QUÉ UN PROCESO APARTE Y EN NODE. La regla del sistema es que el servidor web no calcula
// (MAPA 528): leer un arte y armar una tizada lo hace «la computadora de quien está conectado»,
// con el motor de `frontend/src/motor`. Un pedido que llega de otro sistema no tiene a nadie
// conectado, así que este proceso ES esa computadora: usa el mismo motor (el mismo que corren los
// contratos `pruebas/tizada.mjs`), entra al servidor por las rutas de siempre (`/api/arte`,
// `/api/pedido/plan`, `/api/paquetes/pedido`) y hace los pasos que haría una persona:
//   1. sube las tipografías que trajo el paquete;
//   2. lee cada arte, lo sube a su diseño y a su molde, y le cuenta al servidor lo que encontró
//      (el servidor decide las alarmas con las reglas);
//   3. arma la tizada y la guarda en el servidor, como «Generar»;
//   4. guarda los PDF en Google Drive (o en la carpeta del servidor si Drive no está configurado);
//   5. avisa que terminó: el servidor arma el JSON para el otro sistema.
// Un pedido por vez. Si este proceso se cae, el servidor lo vuelve a levantar y el pedido que
// quedó a medias vuelve a la cola.
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import { fileURLToPath } from 'node:url'
import { Worker as WorkerNode } from 'node:worker_threads'

const AQUI = path.dirname(fileURLToPath(import.meta.url))
const RAIZ = path.resolve(AQUI, '..', '..', '..', '..')              // la carpeta del proyecto
const BASE = (process.env.TIZADA_URL || 'http://127.0.0.1:8050').replace(/\/+$/, '')
const DATOS = process.env.TIZADA_DATOS || path.join(RAIZ, 'datos')
const UNA_VEZ = process.argv.includes('--una-vez')                   // procesa lo que haya y sale (pruebas)
const ESPERA_MS = 4000

function llave() {
  if (process.env.TIZADA_ROBOT_TOKEN) return process.env.TIZADA_ROBOT_TOKEN.trim()
  return fs.readFileSync(path.join(DATOS, 'externo', 'robot.token'), 'ascii').trim()
}
const TOKEN = llave()
const log = (...a) => console.log(`[robot ${new Date().toLocaleTimeString('es-UY')}]`, ...a)

// ── el motor espera un navegador: `Worker` y un `fetch` que conozca el servidor ──────────────
globalThis.Worker = class {
  constructor(url) {
    this.w = new WorkerNode(url)
    this.w.on('message', (m) => this.onmessage && this.onmessage({ data: m }))
    this.w.on('error', (e) => this.onerror && this.onerror(e))
  }
  postMessage(m, t) { this.w.postMessage(m, t) }
  terminate() { this.w.terminate() }
}
const fetchReal = globalThis.fetch
const rutaApi = (x) => BASE + x
let _calculos = null
// 🔴 EL SERVIDOR LE PIDE CÁLCULOS A QUIEN LO LLAMA (MAPA 528): cuando una ruta necesita leer algo
// de un archivo contesta 428 `{calcular}` y espera que «la computadora» lo haga y repita el
// pedido. En el navegador lo atiende `instalarCalculos`; acá, lo mismo con `resolverCalculo`.
globalThis.fetch = async (url, opts = {}) => {
  let u = String(url)
  if (u.startsWith('/')) u = BASE + u
  if (!u.startsWith(BASE + '/')) return fetchReal(url, opts)          // Google: sin la llave del robot
  const h = new Headers(opts.headers || {})
  h.set('X-Robot-Token', TOKEN)
  const veces = new Map()
  for (;;) {
    const r = await fetchReal(u, { ...opts, headers: h })
    if (r.status !== 428) return r
    let d = null
    try { d = await r.clone().json() } catch { d = null }
    if (!d || !d.calcular) return r
    const lista = Array.isArray(d.calculos) && d.calculos.length ? d.calculos : [d.calcular]
    if (!_calculos) _calculos = await import('../calculos.js')
    for (const pd of lista) {
      const n = (veces.get(pd.clave) || 0) + 1
      veces.set(pd.clave, n)
      if (n > 3) throw new Error(`el cálculo «${pd.fn}» no avanza (el servidor lo vuelve a pedir)`)
      await _calculos.resolverCalculo(pd, rutaApi)
    }
  }
}

async function api(ruta, opts = {}) {
  const r = await fetch(rutaApi(ruta), opts)
  const d = await r.json().catch(() => ({}))
  if (!r.ok) { const e = new Error(d.error || `${ruta}: ${r.status}`); e.status = r.status; e.datos = d; throw e }
  return d
}
const apiJson = (ruta, cuerpo) => api(ruta, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cuerpo || {}) })
async function archivoDelPedido(ref, ruta) {
  const r = await fetch(rutaApi(`/api/externo/robot/archivo/${encodeURIComponent(ref)}?ruta=${encodeURIComponent(ruta)}`))
  if (!r.ok) throw new Error(`no se pudo leer «${ruta}» del paquete (${r.status})`)
  return new Uint8Array(await r.arrayBuffer())
}

// ── el motor (se carga recién cuando hay trabajo) ───────────────────────────────────────────
let M = null
async function motor() {
  if (M) return M
  const [arte, fsub, fest, gen, mupdf, ed, pers] = await Promise.all([
    import('../prepararArte.js'), import('../arte/fuentesSubir.js'), import('../arte/fuentesEstado.js'),
    import('../pedido/generar.js'), import('mupdf'), import('../arte/editables.js'), import('../arte/personalizacion.js'),
  ])
  M = { ...arte, ...fsub, ...fest, ...gen, mupdf, extraerEditables: ed.extraerEditables, extraerPersonalizacion: pers.extraerPersonalizacion, CAMPO_ALIAS: pers.CAMPO_ALIAS }
  return M
}

// ══ GOOGLE DRIVE (cuenta de servicio, sin librerías: `crypto` firma y `fetch` sube) ════════════
const b64u = (x) => Buffer.from(x).toString('base64url')
/**
 * El permiso para Drive. `cred` = lo que da `/api/externo/robot/destino`:
 *   · `{oauth: {client_id, client_secret, refresh_token, token_uri}}` — la cuenta de una PERSONA
 *     (lo normal: los archivos quedan a su nombre y en su espacio);
 *   · `{cuenta}` — una cuenta de servicio (sólo sirve con unidades compartidas).
 */
async function tokenDrive(cred) {
  if (cred.oauth) {
    const o = cred.oauth
    const r = await fetchReal(o.token_uri || 'https://oauth2.googleapis.com/token', { method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ grant_type: 'refresh_token', refresh_token: o.refresh_token, client_id: o.client_id, client_secret: o.client_secret }) })
    const d = await r.json().catch(() => ({}))
    if (!r.ok || !d.access_token) {
      throw new Error(d.error === 'invalid_grant'
        ? 'Google ya no acepta el permiso de la cuenta (se revocó o venció): volvé a tocar «Conectar con Google» en Integraciones'
        : 'Google no aceptó el permiso de la cuenta: ' + (d.error_description || d.error || r.status))
    }
    return d.access_token
  }
  const cuenta = cred.cuenta || cred
  const ahora = Math.floor(Date.now() / 1000)
  const uri = cuenta.token_uri || 'https://oauth2.googleapis.com/token'
  const unsigned = b64u(JSON.stringify({ alg: 'RS256', typ: 'JWT' })) + '.' + b64u(JSON.stringify({
    iss: cuenta.client_email, scope: 'https://www.googleapis.com/auth/drive', aud: uri, iat: ahora, exp: ahora + 3300 }))
  const firma = crypto.createSign('RSA-SHA256').update(unsigned).sign(cuenta.private_key, 'base64url')
  const r = await fetchReal(uri, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer', assertion: unsigned + '.' + firma }) })
  const d = await r.json().catch(() => ({}))
  if (!r.ok || !d.access_token) throw new Error('Google no aceptó la cuenta de servicio: ' + (d.error_description || d.error || r.status))
  return d.access_token
}
// (`TIZADA_DRIVE_API` sólo lo usa el contrato, para hablarle a un Drive de mentira)
const G = (process.env.TIZADA_DRIVE_API || 'https://www.googleapis.com').replace(/\/+$/, '')
async function gJson(tok, url, opts = {}) {
  const r = await fetchReal(url, { ...opts, headers: { Authorization: 'Bearer ' + tok, ...(opts.headers || {}) } })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error('Google Drive: ' + ((d.error && d.error.message) || r.status))
  return d
}
const qEsc = (s) => String(s).replace(/\\/g, '\\\\').replace(/'/g, "\\'")
async function buscarEnCarpeta(tok, carpeta, nombre, soloCarpetas = false) {
  const q = `name = '${qEsc(nombre)}' and '${qEsc(carpeta)}' in parents and trashed = false` + (soloCarpetas ? " and mimeType = 'application/vnd.google-apps.folder'" : '')
  const d = await gJson(tok, `${G}/drive/v3/files?q=${encodeURIComponent(q)}&fields=files(id,name,webViewLink)&supportsAllDrives=true&includeItemsFromAllDrives=true&pageSize=5`)
  return (d.files || [])[0] || null
}
async function carpetaDrive(tok, padre, nombre) {
  const ya = await buscarEnCarpeta(tok, padre, nombre, true)
  if (ya) return ya
  return gJson(tok, `${G}/drive/v3/files?supportsAllDrives=true&fields=id,name,webViewLink`, { method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: nombre, mimeType: 'application/vnd.google-apps.folder', parents: [padre] }) })
}
/** Sube (o actualiza, si ya hay uno con ese nombre: el enlace no cambia) un archivo a la carpeta. */
async function subirADrive(tok, carpeta, nombre, bytes, mime) {
  const ya = await buscarEnCarpeta(tok, carpeta, nombre)
  const url = ya
    ? `${G}/upload/drive/v3/files/${ya.id}?uploadType=resumable&supportsAllDrives=true&fields=id,name,webViewLink`
    : `${G}/upload/drive/v3/files?uploadType=resumable&supportsAllDrives=true&fields=id,name,webViewLink`
  const ini = await fetchReal(url, { method: ya ? 'PATCH' : 'POST',
    headers: { Authorization: 'Bearer ' + tok, 'Content-Type': 'application/json; charset=UTF-8', 'X-Upload-Content-Type': mime, 'X-Upload-Content-Length': String(bytes.length) },
    body: JSON.stringify(ya ? {} : { name: nombre, parents: [carpeta] }) })
  if (!ini.ok) { const d = await ini.json().catch(() => ({})); throw new Error('Google Drive: ' + ((d.error && d.error.message) || ini.status)) }
  const sesion = ini.headers.get('location')
  const fin = await fetchReal(sesion, { method: 'PUT', headers: { 'Content-Type': mime, 'Content-Length': String(bytes.length) }, body: bytes })
  const d = await fin.json().catch(() => ({}))
  if (!fin.ok) throw new Error('Google Drive: ' + ((d.error && d.error.message) || fin.status))
  return d
}

async function probarDrive() {
  let ok = false, detalle = ''
  try {
    const { drive } = await api('/api/externo/robot/destino')
    if (!drive) throw new Error('falta prender Drive, poner la carpeta o conectar la cuenta de Google')
    const tok = await tokenDrive(drive)
    const nombres = []
    // las dos carpetas (tizadas y fichas técnicas): en cada una, un archivo de prueba
    for (const id of [...new Set([drive.carpeta_tizadas || drive.carpeta_id, drive.carpeta_fichas].filter(Boolean))]) {
      const c = await gJson(tok, `${G}/drive/v3/files/${encodeURIComponent(id)}?fields=id,name,driveId,capabilities(canAddChildren)&supportsAllDrives=true`)
      if (c.capabilities && c.capabilities.canAddChildren === false) throw new Error(`la cuenta ve la carpeta «${c.name}» pero no puede escribir en ella`)
      await subirADrive(tok, id, 'TIZADA PRO - prueba de conexión.txt', Buffer.from('TIZADA PRO puede escribir en esta carpeta. ' + new Date().toISOString()), 'text/plain')
      nombres.push(`«${c.name}»`)
      if (drive.cuenta && !c.driveId) detalle = ' (ojo: no es una unidad compartida; una cuenta de servicio no tiene espacio propio)'
    }
    ok = true
    detalle = `se escribió un archivo de prueba en ${nombres.join(' y ')}` + detalle
  } catch (e) { detalle = String(e.message || e) }
  await apiJson('/api/externo/robot/drive_probado', { ok, detalle })
  log('prueba de Drive:', ok ? 'bien' : 'falló', '—', detalle)
}

// ══ UN PEDIDO ══════════════════════════════════════════════════════════════════════════════════
const sha256 = (b) => crypto.createHash('sha256').update(b).digest('hex')
class Rechazo extends Error { constructor(motivo, alarmas = []) { super(motivo); this.alarmas = alarmas } }

async function subirTipografias(m, ref, pid, rutas) {
  const invalidas = []
  for (const ruta of rutas || []) {
    try {
      const bytes = await archivoDelPedido(ref, ruta)
      const archivo = new File([bytes], path.basename(ruta))
      const an = await m.analizarFuente(archivo, { pid, destino: 'pedido', rutaApi })
      const fd = new FormData()
      fd.append('archivo', archivo, archivo.name)
      fd.append('destino', 'pedido')
      fd.append('pid', pid)
      m.adjuntarAnalisis(fd, an)
      const r = await fetch(rutaApi('/api/pedido/fuente_resolver'), { method: 'POST', body: fd })
      // 409 «ya existe» = esa misma fuente ya está cargada en el molde: sirve
      if (!r.ok && r.status !== 409) { const d = await r.json().catch(() => ({})); throw new Error(d.error || r.status) }
    } catch (e) {
      invalidas.push(`${path.basename(ruta)} (${String(e.message || e).slice(0, 120)})`)
    }
  }
  return invalidas
}

async function cargarArte(m, ref, dis, mol) {
  const informe = { pid: mol.pid, slug: dis.slug }
  try {
    informe.fuentes_invalidas = await subirTipografias(m, ref, mol.pid, mol.tipografias)
    const bytes = await archivoDelPedido(ref, mol.arte)
    const archivo = new File([bytes], path.basename(mol.arte))
    // lo que el arte trae para decidir alarmas: sus objetos editables y sus campos de nombre/número
    try { informe.editables = [...new Set(m.extraerEditables(m.mupdf, bytes.slice()).map((o) => o.capa))] } catch { informe.editables = [] }
    try {
      const pers = m.extraerPersonalizacion(m.mupdf, bytes.slice())
      informe.campos = [...new Set(Object.values(pers || {}).flatMap((x) => Object.keys(x || {})))].filter((c) => !c.startsWith('\u0000'))
    } catch { informe.campos = null }
    const prep = await m.prepararArteEnNavegador(archivo, { pid: mol.pid, diseno: dis.slug, rutaApi })
    if (!prep) throw new Error('el servidor tiene apagado «el arte lo lee la computadora»')
    informe.modo = prep.modo
    informe.validacion = prep.validacion
    const fd = new FormData()
    fd.append('archivo', archivo, archivo.name)
    fd.append('diseno', dis.slug)
    fd.append('pid', mol.pid)
    fd.append('paquete', new Blob([prep.zip], { type: 'application/zip' }), 'paquete.zip')
    const r = await fetch(rutaApi('/api/arte'), { method: 'POST', body: fd })
    const d = await r.json().catch(() => ({}))
    if (!r.ok) throw new Error(d.error || `subir el arte: ${r.status}`)
    // tipografías del nombre/número que no resuelven (ni en el catálogo ni en lo que vino)
    const reempl = {}
    // con los alias de capa («texto» = el campo nombre), como `clave_fuente_campo` del servidor
    for (const [campo, fuente] of Object.entries(dis.tipografia_por_campo || {})) {
      const c = String(campo).trim().toLowerCase()
      reempl['@campo:' + ((m.CAMPO_ALIAS || {})[c] || c)] = String(fuente)
    }
    try {
      const est = await m.fuentesEstadoLocal({ pid: mol.pid, diseno: dis.slug, reemplazos: reempl, rutaApi })
      informe.fuentes_faltan = est.faltantes || []
    } catch { informe.fuentes_faltan = [] }
  } catch (e) {
    informe.error = String(e.message || e).slice(0, 300)
  }
  return apiJson(`/api/externo/robot/arte/${encodeURIComponent(ref)}`, informe)
}

// ── MOLDE A MEDIDA (MAPA 623) ───────────────────────────────────────────────────────────────
// La COPIA a medida de un molde del catálogo: el servidor la da de alta (`/robot/a_medida`), acá se
// arma su archivo con el MISMO código que la pantalla (`molde/aMedida.js` + el alta del camino A) y
// se sube por `/api/plantilla`, como cualquier molde. `slug` = el diseño del pedido donde la copia
// toma el lugar del molde del catálogo (sin `slug`, es para una plantilla).
async function esperarTrabajo(resp) {
  if (!resp || !resp.job) return resp
  for (let espera = 250; ; espera = Math.min(1200, Math.round(espera * 1.5))) {
    await new Promise((r) => setTimeout(r, espera))
    const d = await api(`/api/trabajo/${resp.job}`)
    if (d.estado === 'listo') return d.resultado || {}
    if (d.estado === 'error') throw new Error(d.error || 'no se pudo leer el molde')
    if (d.estado === 'cancelado') throw new Error('la lectura del molde se canceló')
  }
}
async function armarCopiaAMedida(m, ref, plantilla, medida, slug = null) {
  const c = await apiJson(`/api/externo/robot/a_medida/${encodeURIComponent(ref)}`,
    { plantilla, ancho_m: medida.ancho_m, alto_m: medida.alto_m, slug })
  const [AM, CA, PQ] = await Promise.all([import('../molde/aMedida.js'), import('../molde/caminoA.js'), import('../paquete/armar.js')])
  // el borde de corte va ADENTRO de la medida: el rectángulo, la reserva más chico (como la pantalla)
  const { pdf, resumen } = AM.pdfMoldeAMedida(m.mupdf, { anchoM: c.ancho_m, altoM: c.alto_m, pieza: c.pieza,
    reservaMm: c.reserva_mm ?? AM.RESERVA_DEFECTO_MM, margen: c.margen || null })
  const doc = m.mupdf.Document.openDocument(pdf, 'application/pdf')
  let zip, sha1
  try {
    const prep = CA.prepararCaminoA(new CA.MoldeA(m.mupdf, doc), { dxf: resumen, indices: resumen.indices })
    sha1 = crypto.createHash('sha1').update(pdf).digest('hex')
    zip = PQ.armarPaqueteCaminoA(null, prep, { motor: 'mupdf.js', sha1 }).zip
  } finally {
    try { doc.destroy() } catch { /* nada */ }
  }
  const fd = new FormData()
  fd.append('archivo', new File([pdf], 'molde_a_medida.pdf', { type: 'application/pdf' }))
  fd.append('pid', c.pid)
  fd.append('con_diseno', '0')
  fd.append('solo_base', '1')
  fd.append('paquete', new Blob([zip], { type: 'application/zip' }), 'paquete.zip')
  const r = await fetch(rutaApi('/api/plantilla'), { method: 'POST', body: fd })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(d.error || `subir el molde a medida: ${r.status}`)
  await esperarTrabajo(d)
  const fin = await apiJson(`/api/externo/robot/a_medida/${encodeURIComponent(ref)}/listo`, { pid: c.pid })
  return { pid: c.pid, variable: fin.variable, acomodo: fin.acomodo, talle: c.talle }
}

function clasificarFalla(e) {
  const t = String((e && e.message) || e)
  if (/no entra en la hoja/i.test(t)) return ['pieza-no-entra', t]
  if (/no puede estampar/i.test(t)) return ['caracter-imposible', t]
  return [null, t]
}

async function guardarArchivos(ref, carpetaNombre, archivos) {
  // archivos = [{tipo, origen, nombre, bytes, mime}] → dónde quedó cada uno
  const { drive, local } = await api('/api/externo/robot/destino')
  const salida = [], destino = { tipo: 'local' }
  let driveError = null
  // SIEMPRE queda una copia en el servidor: si Drive falla, el pedido no se pierde
  const dir = path.join(local, ref)
  fs.mkdirSync(dir, { recursive: true })
  for (const a of archivos) {
    const tmp = path.join(dir, a.nombre + '.tmp')
    fs.writeFileSync(tmp, a.bytes)
    fs.renameSync(tmp, path.join(dir, a.nombre))
    salida.push({ tipo: a.tipo, origen: a.origen, nombre: a.nombre, bytes: a.bytes.length, sha256: sha256(a.bytes), ruta: path.join(dir, a.nombre),
      ...(a.pagina !== undefined ? { pagina: a.pagina, mesa: a.mesa, mesas_tela: a.mesas_tela } : {}) })
  }
  destino.carpeta = dir
  if (drive) {
    try {
      const tok = await tokenDrive(drive)
      // DOS CARPETAS (pedido del usuario 2026-10-02): las tizadas en la de pedidos, dentro de una
      // carpeta del pedido (`carpeta`, que puede traer niveles: «2026-10/OV-123»); la ficha técnica
      // suelta en la de fichas (su nombre ya lleva la referencia adelante)
      let c = { id: drive.carpeta_tizadas || drive.carpeta_id }
      for (const nivel of String(carpetaNombre).split('/').filter(Boolean)) c = await carpetaDrive(tok, c.id, nivel)
      const fichas = drive.carpeta_fichas || c.id
      for (let i = 0; i < archivos.length; i++) {
        const donde = archivos[i].tipo === 'ficha' ? fichas : c.id
        const d = await subirADrive(tok, donde, archivos[i].nombre, archivos[i].bytes, archivos[i].mime)
        salida[i].drive_id = d.id
        salida[i].enlace = d.webViewLink || `https://drive.google.com/file/d/${d.id}/view`
        salida[i].carpeta_id = donde
      }
      Object.assign(destino, { tipo: 'drive', carpeta_id: c.id, carpeta_enlace: c.webViewLink || `https://drive.google.com/drive/folders/${c.id}`, carpeta_nombre: carpetaNombre,
        carpeta_fichas_id: fichas, carpeta_fichas_enlace: `https://drive.google.com/drive/folders/${fichas}`, copia_local: dir })
      delete destino.carpeta
      destino._tok = tok
    } catch (e) { driveError = String(e.message || e) }
  }
  return { salida, destino, driveError }
}

async function procesar(ref, normal) {
  const m = await motor()
  const t0 = Date.now()
  const avance = (etapa) => apiJson(`/api/externo/robot/avance/${encodeURIComponent(ref)}`, { etapa }).catch(() => ({ seguir: true }))
  // 0 · MOLDE A MEDIDA (MAPA 623): primero la copia a la medida pedida; desde acá el diseño usa la copia
  for (const dis of normal.disenos) {
    for (const mol of dis.moldes) {
      if (!mol.medida) continue
      await avance(`armando «${mol.molde_nombre}» a ${mol.medida.ancho_m} × ${mol.medida.alto_m} m`)
      const c = await armarCopiaAMedida(m, ref, mol.plantilla || mol.pid, mol.medida, dis.slug)
      mol.plantilla = mol.plantilla || mol.pid
      mol.pid = c.pid
      mol.variable = c.variable && c.variable.clave
      log(ref, '· a medida', dis.nombre, '→', mol.molde_nombre, c.talle)
    }
  }
  // 1 y 2 · cada diseño, con cada uno de sus moldes: tipografías + arte
  let frena = false
  for (const dis of normal.disenos) {
    for (const mol of dis.moldes) {
      const st = await avance(`leyendo el arte de «${dis.nombre}» para «${mol.molde_nombre}»`)
      if (st.seguir === false) throw new Rechazo('cancelado')
      log(ref, '· arte', dis.nombre, '→', mol.molde_nombre)
      const r = await cargarArte(m, ref, dis, mol)
      for (const a of r.alarmas || []) log(ref, '   ', a.frena ? 'FRENA' : 'aviso', a.codigo, '—', a.mensaje)
      if (!r.seguir) frena = true
    }
  }
  if (frena) throw new Rechazo('el arte o las tipografías tienen alarmas que frenan el pedido')
  // 3 · la tizada (lo mismo que apretar «Generar»)
  const { cuerpo, opciones } = await api(`/api/externo/robot/cuerpo/${encodeURIComponent(ref)}`)
  await avance('revisando nombres y números')
  const achiques = []
  try {
    const med = await m.achiquesEnNavegador({ ...cuerpo, cantidad_copia: false }, { rutaApi })
    for (const [fila, campos] of Object.entries(med || {})) {
      for (const [campo, x] of Object.entries(campos || {})) {
        achiques.push({ fila: Number(fila), ilegible: x.k < 0.6,
          mensaje: `fila ${fila}: el ${campo} no entra en ${x.pieza} (talle ${x.talle}) y sale de ${Number(x.alto_cm).toFixed(1)} cm en vez de ${Number(x.alto0_cm).toFixed(1)} cm` })
      }
    }
  } catch (e) { log(ref, 'no se pudo medir si los textos entran:', e.message) }
  if (achiques.length && opciones.si_texto_no_entra === 'rechazar') {
    throw new Rechazo('hay nombres o números que no entran', achiques.map((x) => ({ codigo: x.ilegible ? 'texto-ilegible' : 'texto-se-achica', mensaje: x.mensaje, donde: { fila: x.fila } })))
  }
  // el plan, antes de armar nada: las piezas que SE FABRICAN y quedarían en blanco frenan acá
  let plan
  try { plan = await apiJson('/api/pedido/plan', cuerpo) } catch (e) {
    const det = e.datos && e.datos.detalle ? ' — ' + [].concat(e.datos.detalle).join('; ') : ''
    throw new Rechazo(e.message, [{ codigo: 'pedido-rechazado-por-reglas', mensaje: String(e.message) + det }])
  }
  if (opciones.si_piezas_en_blanco !== 'seguir' && (plan.avisos || []).length) {
    throw new Rechazo('hay piezas que saldrían en blanco', plan.avisos.map((t) => ({ codigo: 'piezas-en-blanco', mensaje: String(t) })))
  }
  await avance('armando la tizada')
  log(ref, '· armando la tizada')
  let r
  try {
    // el motor avisa con el formato interno de la pantalla (`nav|pct|texto`): al otro sistema le
    // llega en palabras, que es lo que muestra tal cual en su «en qué va»
    const enPalabras = (t) => {
      const mm = /^nav\|(\d+)\|(.*)$/s.exec(String(t))
      return mm ? `armando la tizada (${mm[1]} %): ${mm[2]}` : String(t)
    }
    r = await m.generarPedidoEnNavegador(cuerpo, { rutaApi, avisar: (t) => { avance(enPalabras(t)) } })
  } catch (e) {
    const [cod, txt] = clasificarFalla(e)
    if (cod) throw new Rechazo(txt, [{ codigo: cod, mensaje: txt }])
    if (e.status === 409 || e.status === 422 || e.status === 400) throw new Rechazo(txt, [{ codigo: 'tizada-fallo', mensaje: txt + (e.datos && e.datos.detalle ? ' — ' + [].concat(e.datos.detalle).join('; ') : '') }])
    throw e
  }
  if (!r) throw new Error('el servidor tiene apagado «la tizada la arma la computadora»')
  // 4 · los PDF, a Drive (y siempre una copia en el servidor)
  await avance('guardando los PDF')
  const archivos = []
  // 🔴 UNA MESA = UN ARCHIVO (MAPA 620, pedido del usuario: «cada mesa es un archivo, así como hace
  // al descargar»): cada página de la hoja de una tela sale como su propio PDF, con el MISMO nombre
  // que le pone «Descargar todo» de TIZADA («Mesa 1 - Bandera»…) y la misma copia de la página
  // (`pdf/mesaPorArchivo.js`). La ficha técnica va entera, como siempre.
  const MZ = await import('../pdf/mesaPorArchivo.js')
  const hojas = (r.resultado && r.resultado.hojas) || []
  const deHoja = new Set(hojas.map((h) => h.archivo))
  for (const mz of MZ.mesasEnOrden(hojas)) {
    const src = (r.archivos || {})[mz.hoja.archivo]
    if (!src) continue
    const pdf = MZ.paginaComoPdf(m.mupdf, new Uint8Array(src), mz.pi)
    archivos.push({ tipo: 'tizada', origen: mz.hoja.archivo, pagina: mz.pi, mesa: mz.numero, mesas_tela: mz.deLaTela,
      nombre: `${ref}__${MZ.nombreArchivoSeguro(mz.nombre)}.pdf`, bytes: Buffer.from(pdf), mime: 'application/pdf' })
  }
  for (const [nombre, bytes] of Object.entries(r.archivos || {})) {
    if (deHoja.has(nombre)) continue
    archivos.push({ tipo: /^FICHA/i.test(nombre) ? 'ficha' : 'tizada', origen: nombre, nombre: `${ref}__${nombre}`, bytes: Buffer.from(bytes), mime: 'application/pdf' })
  }
  const g = await guardarArchivos(ref, opciones.carpeta || ref, archivos)
  const tok = g.destino._tok
  delete g.destino._tok
  // 5 · terminado: el servidor arma el JSON para el otro sistema
  const fin = await apiJson(`/api/externo/robot/terminar/${encodeURIComponent(ref)}`, {
    tid: r.id, segundos: Math.round((Date.now() - t0) / 100) / 10, resultado: r.resultado,
    archivos: g.salida, destino: g.destino, drive_error: g.driveError, achiques })
  // el mismo JSON queda al lado de los PDF
  try {
    const bytes = Buffer.from(JSON.stringify(fin.resultado, null, 1))
    const nombre = `${ref}__resultado.json`
    if (g.destino.tipo === 'drive' && tok) await subirADrive(tok, g.destino.carpeta_id, nombre, bytes, 'application/json')
    const dir = g.destino.copia_local || g.destino.carpeta
    if (dir) fs.writeFileSync(path.join(dir, nombre), bytes)
  } catch (e) { log(ref, 'no se pudo dejar el resultado.json junto a los PDF:', e.message) }
  log(ref, '· listo en', ((Date.now() - t0) / 1000).toFixed(1), 's ·', g.destino.tipo, g.driveError ? '(Drive falló: ' + g.driveError + ')' : '')
}

// ══ LA PLANTILLA QUE PIDE EL OTRO SISTEMA (MAPA 619) ═══════════════════════════════════════════
// La base para el diseñador de unos diseños (cada uno con sus variables), con el MISMO cálculo de
// la ventana «Crear plantilla» de TIZADA (`molde/plantillaPedido.js`). Por diseño deja tres cosas
// para bajar: lo que se le manda al conector de Illustrator (uno o más archivos), lo de CorelDRAW y
// la guía .ai. No toca ningún molde: sólo lee la detección y la geometría por las rutas de siempre.
const nombreSeguro = (t) => String(t).replace(/[\\/:*?"<>|\u0000-\u001f]+/g, '_').replace(/\s+/g, ' ').trim().slice(0, 150) || 'plantilla'
async function procesarPlantilla(ref, normal) {
  const P = await import('../molde/plantillaPedido.js')
  const H = await import('../molde/herramientas.js')
  // MOLDE A MEDIDA (MAPA 623): la plantilla se arma sobre una copia a la medida pedida
  for (const dis of normal.disenos) {
    for (const it of dis.vars) {
      if (!it.medida) continue
      const c = await armarCopiaAMedida(await motor(), ref, it.pid, it.medida)
      Object.assign(it, { pid: c.pid, clave: c.variable.clave, variable: c.variable, acomodo: c.acomodo || {} })
      log(ref, '· plantilla a medida', dis.nombre, '→', it.molde, c.talle)
    }
  }
  const dets = {}
  for (const dis of normal.disenos) {
    for (const it of dis.vars) {
      if (!dets[it.pid]) dets[it.pid] = await api(`/api/plantilla/deteccion?pid=${encodeURIComponent(it.pid)}`)
    }
  }
  const cache = new Map()
  const traer = (qs) => { if (!cache.has(qs)) cache.set(qs, api('/api/plantilla/pdf_guia?' + qs)); return cache.get(qs) }
  const listaRangos = normal.config === 'rango' ? (normal.rangos || []) : []
  const mp = P.motorPlantilla({ dets, config: normal.config, tallesSel: normal.talles_sel || null, listaRangos, capas: normal.capas, traer })
  const talles = []
  for (const d of Object.values(dets)) for (const x of (d.talles_reales && d.talles_reales.length ? d.talles_reales : d.talles || [])) if (!talles.includes(x)) talles.push(x)
  const tEtq = P.etiquetaTalles({ config: normal.config, rangos: listaRangos, tallesSel: normal.talles_sel || null, talles })
  const archivos = [], avisos = []
  const subir = async (nombre, bytes, extra) => {
    const r = await fetch(rutaApi(`/api/externo/robot/plantilla/${encodeURIComponent(ref)}/archivo?nombre=${encodeURIComponent(nombre)}`),
      { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: bytes })
    if (!r.ok) throw new Error(`no se pudo guardar «${nombre}» (${r.status})`)
    archivos.push({ nombre, ...extra })
  }
  const choques = await mp.choquesDe(normal.disenos)
  for (const dis of normal.disenos) {
    log(ref, '· plantilla', dis.nombre)
    // ILLUSTRATOR: uno por diseño si entra a la escala pedida; si no, los que hagan falta
    const il = await mp.planesIllustrator(dis, normal.escala, tEtq)
    for (const a of il.avisos) if (!avisos.includes(a)) avisos.push(a)
    for (let i = 0; i < il.planes.length; i++) {
      const parte = il.planes.length > 1 ? `${i + 1} de ${il.planes.length}` : null
      await subir(nombreSeguro(`${dis.nombre} - Illustrator${parte ? ' ' + parte : ''}`) + '.json',
        Buffer.from(JSON.stringify(il.planes[i])), { diseno: dis.nombre, tipo: 'illustrator', ...(parte ? { parte } : {}) })
    }
    // CORELDRAW: siempre a tamaño real, uno por diseño
    const co = await mp.planCorel(dis, tEtq)
    for (const a of co.avisos) if (!avisos.includes(a)) avisos.push(a)
    if (co.plan) await subir(nombreSeguro(`${dis.nombre} - CorelDRAW`) + '.json', Buffer.from(JSON.stringify(co.plan)), { diseno: dis.nombre, tipo: 'corel' })
    // LA GUÍA .ai (una por diseño, y por rango)
    // (una guía que no entra en Illustrator no tumba la plantilla: queda como aviso)
    const gs = await mp.guiasDe(dis, async (capas_data, opciones) => H.aiGuiaMedidas(capas_data, opciones))
    for (const t of gs.fallas) if (!avisos.includes(t)) avisos.push(t)
    for (const gu of gs.archivos) {
      await subir(nombreSeguro(gu.nombre.replace(/\.ai$/i, '')) + '.ai', Buffer.from(gu.bytes), { diseno: dis.nombre, tipo: 'guia' })
    }
  }
  await apiJson(`/api/externo/robot/plantilla/${encodeURIComponent(ref)}/terminar`, { archivos, avisos, choques })
  log(ref, '· plantilla lista:', archivos.length, 'archivos')
}

async function vuelta() {
  const t = await apiJson('/api/externo/robot/tomar', {})
  if (t.tarea === 'probar_drive') { await probarDrive(); return true }
  if (t.tarea === 'plantilla') {
    const ref = t.referencia
    log(ref, 'plantilla tomada')
    try {
      await procesarPlantilla(ref, t.normal)
    } catch (e) {
      // un dato que no sirve (409/422/400 del servidor) no se arregla reintentando
      const rechazo = e && (e.status === 400 || e.status === 409 || e.status === 422)
      log(ref, 'LA PLANTILLA FALLÓ:', e.message)
      if (!rechazo) console.error(e)
      await apiJson(`/api/externo/robot/plantilla/${encodeURIComponent(ref)}/fallo`, { rechazo, motivo: String((e && e.message) || e).slice(0, 300) }).catch(() => {})
    }
    return true
  }
  if (t.tarea !== 'pedido') return false
  const ref = t.referencia
  log(ref, 'tomado')
  try {
    await procesar(ref, t.normal)
  } catch (e) {
    const rechazo = e instanceof Rechazo
    log(ref, rechazo ? 'RECHAZADO:' : 'FALLÓ:', e.message)
    if (!rechazo) console.error(e)
    await apiJson(`/api/externo/robot/fallo/${encodeURIComponent(ref)}`, { rechazo, motivo: String(e.message || e).slice(0, 300), alarmas: e.alarmas || [] }).catch(() => {})
  } finally {
    try { M && M.cerrarMotores && M.cerrarMotores() } catch { /* nada */ }
  }
  return true
}

log('arrancó · servidor', BASE)
for (;;) {
  let hubo = false
  try { hubo = await vuelta() } catch (e) { log('no se pudo hablar con el servidor:', e.message) }
  if (UNA_VEZ && !hubo) break
  if (!hubo) await new Promise((ok) => setTimeout(ok, ESPERA_MS))
}
process.exit(0)
