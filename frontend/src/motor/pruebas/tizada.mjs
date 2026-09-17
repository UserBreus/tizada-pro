// node frontend/src/motor/pruebas/tizada.mjs <entorno.json> <salida_dir>
// Genera un pedido ENTERO con el motor del navegador (`pedido/generar.js`) SIN servidor: el
// `fetch` se reemplaza por uno que contesta con archivos (el plan que armó Python, el desplegado
// del molde, las tipografías, el perfil) y que guarda el paquete del pedido en `salida_dir`.
// Lo compara `verificar_navegador_tizada.py` contra `generar_multi` del servidor.
//
// entorno.json = { plan: {...} (lo que da `_plan_para_navegador`), cuerpo: {...},
//                  motor_b: { pid: {...} }, desplegado: { pid: carpeta },
//                  fuentes: { archivo: ruta }, perfil: ruta|null }
import fs from 'node:fs'
import path from 'node:path'
import { Worker as WorkerNode } from 'node:worker_threads'

const [, , entornoPath, salidaDir] = process.argv
const E = JSON.parse(fs.readFileSync(entornoPath, 'utf-8'))
fs.mkdirSync(salidaDir, { recursive: true })

// ── Worker del navegador → worker_threads ───────────────────────────────────────────────────
globalThis.Worker = class {
  constructor(url) {
    this.w = new WorkerNode(url)
    this.w.on('message', (m) => this.onmessage && this.onmessage({ data: m }))
    this.w.on('error', (e) => this.onerror && this.onerror(e))
  }
  postMessage(m, t) { this.w.postMessage(m, t) }
  terminate() { this.w.terminate() }
}

// ── fetch → archivos ────────────────────────────────────────────────────────────────────────
const resp = (cuerpo, tipo = 'application/json', status = 200) => new Response(
  tipo === 'application/json' ? JSON.stringify(cuerpo) : cuerpo, { status, headers: { 'Content-Type': tipo } })
const dec = (s) => decodeURIComponent(s)
globalThis.fetch = async (url, opts = {}) => {
  const u = String(url)
  let m
  if (u.startsWith('/api/navegador/config')) return resp({ molde: true, vista: true, tizada: true, arte: true })
  if (u.startsWith('/api/pedido/plan')) return resp(E.plan)
  if (u.startsWith('/api/pedido/perfil_salida')) {
    if (!E.perfil) return resp({ error: 'sin perfil' }, 'application/json', 404)
    return resp(fs.readFileSync(E.perfil), 'application/vnd.iccprofile')
  }
  if ((m = u.match(/^\/api\/productos\/([^/]+)\/motor_b/))) return resp(E.motor_b[dec(m[1])])
  if ((m = u.match(/^\/api\/productos\/([^/]+)\/desplegado\/([^/?]+)/))) {
    return resp(fs.readFileSync(path.join(E.desplegado[dec(m[1])], dec(m[2]))), 'application/octet-stream')
  }
  if ((m = u.match(/^\/api\/fuente\/archivo\/([^/?]+)/))) {
    const ruta = E.fuentes[dec(m[1])]
    if (!ruta) return resp({ error: 'no existe' }, 'application/json', 404)
    return resp(fs.readFileSync(ruta), 'font/ttf')
  }
  if (u.startsWith('/api/paquetes/pedido')) {
    const fd = opts.body
    const resultado = JSON.parse(fd.get('resultado'))
    for (const [nombre, v] of fd.entries()) {
      if (v instanceof Blob) fs.writeFileSync(path.join(salidaDir, nombre), new Uint8Array(await v.arrayBuffer()))
    }
    fs.writeFileSync(path.join(salidaDir, 'resultado.json'), JSON.stringify({ resultado, prendas: JSON.parse(fd.get('prendas')), nombres: JSON.parse(fd.get('nombres')) }))
    return resp({ id: 'nav', resultado })
  }
  return resp({ error: 'ruta no simulada: ' + u }, 'application/json', 404)
}

const { generarPedidoEnNavegador } = await import('../pedido/generar.js')
const t0 = performance.now()
const etapas = []
const r = await generarPedidoEnNavegador(E.cuerpo, { rutaApi: (x) => x, avisar: (t) => etapas.push([((performance.now() - t0) / 1000).toFixed(1), t]) })
fs.writeFileSync(path.join(salidaDir, 'tiempos.json'), JSON.stringify({ segundos: (performance.now() - t0) / 1000, etapas, id: r && r.id }))
console.log(JSON.stringify({ id: r && r.id, segundos: (performance.now() - t0) / 1000 }))
process.exit(0)
