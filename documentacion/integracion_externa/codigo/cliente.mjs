// Cliente de ejemplo de la API de TIZADA PRO — Node 18+ (fetch y crypto nativos, sin dependencias).
// Para ARMAR el .zip del pedido hace falta una librería de zip (p. ej. `npm i jszip`); acá se recibe
// ya armado. Uso:
//
//   TIZADA_URL=https://tizada.ejemplo.com TIZADA_LLAVE=tzp_... node cliente.mjs revisar pedido.json
//   TIZADA_URL=... TIZADA_LLAVE=... node cliente.mjs mandar OV-2026-00123.zip
//   TIZADA_URL=... TIZADA_LLAVE=... node cliente.mjs estado OV-2026-00123
//   TIZADA_URL=... TIZADA_LLAVE=... node cliente.mjs bajar OV-2026-00123
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

// ── desde la línea de comandos ──
const [, , que, arg] = process.argv
if (que) {
  if (!LLAVE) { console.error('falta TIZADA_LLAVE'); process.exit(1) }
  if (que === 'revisar') console.log(await revisar(JSON.parse(await readFile(arg, 'utf8'))))
  else if (que === 'mandar') console.log(await mandar(await readFile(arg), arg.split(/[\\/]/).pop()))
  else if (que === 'estado') console.log(JSON.stringify((await estado(arg))[1], null, 1))
  else if (que === 'bajar') {
    const [, est] = await estado(arg)
    if (est.estado !== 'listo') console.log('todavía no está listo:', est.estado, est.etapa || '')
    else await bajar(est.resultado, arg)
  }
}
