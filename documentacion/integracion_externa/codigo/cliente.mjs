// Cliente de ejemplo de la API de TIZADA PRO — Node 18+ (fetch y crypto nativos, sin dependencias).
// Para ARMAR el .zip del pedido hace falta una librería de zip (p. ej. `npm i jszip`); acá se recibe
// ya armado. Uso:
//
//   TIZADA_URL=https://tizada.ejemplo.com TIZADA_LLAVE=tzp_... node cliente.mjs revisar pedido.json
//   TIZADA_URL=... TIZADA_LLAVE=... node cliente.mjs mandar OV-2026-00123.zip
//   TIZADA_URL=... TIZADA_LLAVE=... node cliente.mjs estado OV-2026-00123
//   TIZADA_URL=... TIZADA_LLAVE=... node cliente.mjs bajar OV-2026-00123
//
// LA PLANTILLA para Illustrator / CorelDRAW (la parte de SU SERVIDOR; la de la página del diseñador, que la
// manda al programa, es `crear_en_programa.js`):
//   TIZADA_URL=... TIZADA_LLAVE=... node cliente.mjs plantilla pedir plantilla.json   (lo de POST /plantillas)
//   TIZADA_URL=... TIZADA_LLAVE=... node cliente.mjs plantilla esperar PL-0001       (hasta «listo»; muestra archivos y conectores)
//   TIZADA_URL=... TIZADA_LLAVE=... node cliente.mjs plantilla bajar PL-0001         (los .json de cada programa y la guía .ai)
//   TIZADA_URL=... TIZADA_LLAVE=... node cliente.mjs conectores                      (los instaladores)
//   TIZADA_URL=... TIZADA_LLAVE=... node cliente.mjs conector illustrator            (baja ese instalador)
import { createHash, createHmac, timingSafeEqual } from 'node:crypto'
import { readFile, writeFile, mkdir } from 'node:fs/promises'

const URL_API = (process.env.TIZADA_URL || 'http://127.0.0.1:8050').replace(/\/+$/, '') + '/api/externo/v1'
const LLAVE = process.env.TIZADA_LLAVE || ''

async function llamar (metodo, ruta, { cuerpo, tipo, crudo } = {}) {
  const r = await fetch(URL_API + ruta, { method: metodo, body: cuerpo, headers: { 'X-Api-Key': LLAVE, ...(tipo ? { 'Content-Type': tipo } : {}) } })
  return [r.status, crudo && r.ok ? Buffer.from(await r.arrayBuffer()) : await r.json().catch(() => ({}))]
}

/** Revisar sólo los DATOS (no guarda nada). */
export const revisar = (pedido) => llamar('POST', '/pedidos/validar', { cuerpo: JSON.stringify(pedido), tipo: 'application/json' })

/** Mandar el paquete .zip (Buffer). 202 = en cola · 422 = rechazado con alarmas. */
export function mandar (zip, nombre = 'pedido.zip') {
  const fd = new FormData()
  fd.append('paquete', new Blob([zip], { type: 'application/zip' }), nombre)
  return llamar('POST', '/pedidos', { cuerpo: fd })
}

export const estado = (ref) => llamar('GET', `/pedidos/${encodeURIComponent(ref)}`)

/** Bajar cada PDF del resultado y comprobar el sha256. */
export async function bajar (resultado, carpeta) {
  await mkdir(carpeta, { recursive: true })
  for (const a of resultado.archivos) {
    const [c, datos] = await llamar('GET', a.descarga.split('/api/externo/v1')[1], { crudo: true })
    const ok = c === 200 && createHash('sha256').update(datos).digest('hex') === a.sha256
    await writeFile(`${carpeta}/${a.nombre}`, datos)
    console.log(ok ? 'OK ' : 'MAL', a.tipo, a.nombre, a.enlace || '')
  }
}

/** El AVISO: ¿viene de TIZADA? (cuerpo = Buffer crudo, firma = encabezado X-Tizada-Firma) */
export function firmaValida (cuerpo, firma) {
  const clave = createHash('sha256').update(LLAVE, 'utf8').digest('hex')
  const esperada = Buffer.from(createHmac('sha256', clave).update(cuerpo).digest('hex'))
  const llego = Buffer.from(String(firma || ''))
  return LLAVE !== '' && esperada.length === llego.length && timingSafeEqual(esperada, llego)
}

// ── LA PLANTILLA (Illustrator / CorelDRAW / guía .ai) ──
/** Pedirla (202 = en cola · 422 = rechazada con alarmas). `pedido` = {referencia, disenos, talles, escala}. */
export const pedirPlantilla = (pedido) => llamar('POST', '/plantillas', { cuerpo: JSON.stringify(pedido), tipo: 'application/json' })
export const estadoPlantilla = (ref) => llamar('GET', `/plantillas/${encodeURIComponent(ref)}`)

/** Espera a que el robot la arme (segundos). → el estado «listo» (con `archivos` y `conectores`). */
export async function esperarPlantilla (ref, { cadaMs = 2000, topeMs = 10 * 60 * 1000 } = {}) {
  const fin = Date.now() + topeMs
  for (;;) {
    const [c, est] = await estadoPlantilla(ref)
    if (c !== 200) throw new Error(`TIZADA contestó ${c}: ${est.error || ''}`)
    if (est.estado === 'listo') return est
    if (est.estado === 'rechazado' || est.estado === 'error') throw Object.assign(new Error(`plantilla ${est.estado}`), { alarmas: est.alarmas })
    if (Date.now() > fin) throw new Error('la plantilla tardó demasiado')
    await new Promise((r) => setTimeout(r, cadaMs))
  }
}

/** El contenido de UN archivo de la plantilla (Buffer), comprobado contra su sha256. Es lo que su página le
 *  da a `crear_en_programa.js` (su servidor hace de puente: la llave nunca va al navegador). */
export async function archivoPlantilla (archivo) {
  const [c, datos] = await llamar('GET', archivo.descarga.split('/api/externo/v1')[1], { crudo: true })
  if (c !== 200) throw new Error(`no se pudo bajar «${archivo.nombre}» (${c})`)
  if (createHash('sha256').update(datos).digest('hex') !== archivo.sha256) throw new Error(`«${archivo.nombre}» llegó incompleto`)
  return datos
}

export const conectores = () => llamar('GET', '/conectores')
export const conector = (clave) => llamar('GET', `/conectores/${encodeURIComponent(clave)}`, { crudo: true })

// ── desde la línea de comandos ──
const [, , que, arg, arg2] = process.argv
if (que) {
  if (!LLAVE) { console.error('falta TIZADA_LLAVE'); process.exit(1) }
  if (que === 'revisar') console.log(await revisar(JSON.parse(await readFile(arg, 'utf8'))))
  else if (que === 'mandar') console.log(await mandar(await readFile(arg), arg.split(/[\\/]/).pop()))
  else if (que === 'estado') console.log(JSON.stringify((await estado(arg))[1], null, 1))
  else if (que === 'bajar') {
    const [, est] = await estado(arg)
    if (est.estado !== 'listo') console.log('todavía no está listo:', est.estado, est.etapa || '')
    else await bajar(est.resultado, arg)
  } else if (que === 'plantilla' && arg === 'pedir') console.log(await pedirPlantilla(JSON.parse(await readFile(arg2, 'utf8'))))
  else if (que === 'plantilla' && arg === 'esperar') {
    const est = await esperarPlantilla(arg2)
    for (const a of est.archivos) console.log(a.tipo.padEnd(12), a.diseno, a.parte || '', '·', a.nombre)
    console.log('conectores:', JSON.stringify(est.conectores, null, 1))
  } else if (que === 'plantilla' && arg === 'bajar') {
    const est = await esperarPlantilla(arg2)
    await mkdir(arg2, { recursive: true })
    for (const a of est.archivos) { await writeFile(`${arg2}/${a.nombre}`, await archivoPlantilla(a)); console.log('OK ', a.tipo, a.nombre) }
  } else if (que === 'conectores') console.log(JSON.stringify((await conectores())[1], null, 1))
  else if (que === 'conector') {
    const [, lista] = await conectores()
    const c = (lista.conectores || []).find((x) => x.clave === arg)
    if (!c) { console.error('no existe ese conector:', arg); process.exit(1) }
    const [st, datos] = await conector(arg)
    if (st !== 200) { console.error('TIZADA contestó', st); process.exit(1) }
    await writeFile(c.archivo, datos)
    console.log('OK', c.archivo, datos.length, 'bytes')
  }
}
