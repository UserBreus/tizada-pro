// node frontend/src/motor/pruebas/contexto_a_repetido.mjs <fixture.json> <salida.json>
// El caso del reporte del 2026-09-18 («tarda en cargar un arte»): con el visor mostrando el arte
// de antes, se carga uno nuevo → el hilo de trabajo (`obrero.worker.js`, el MISMO del navegador, acá
// con worker_threads) vuelve a armar el contexto del arte con la misma clave. Las piezas que ya
// había armado nombraban documentos que ese re-armado destruye: si se reusaban, la pieza reventaba
// («cannot find page tree», «invalid page number») y la pantalla le tiraba todos los talles al
// servidor. Acá: pieza → contexto de nuevo → la misma pieza (y lo mismo con el molde).
// Usa el fixture de `verificar_navegador_pieza_a.py` (el primer caso).
import fs from 'node:fs'
import { Worker } from 'node:worker_threads'
import { crearPool } from '../pool.js'

const [, , fixture, salida] = process.argv
const F = JSON.parse(fs.readFileSync(fixture, 'utf-8'))
const caso = F.casos[0]
const crearObrero = () => {
  const w = new Worker(new URL('../obrero.worker.js', import.meta.url), { resourceLimits: { maxOldGenerationSizeMb: 4096 } })
  const o = { postMessage: (m, t) => w.postMessage(m, t), terminate: () => w.terminate(), onmessage: null, onerror: null }
  w.on('message', (m) => o.onmessage && o.onmessage({ data: m }))
  w.on('error', (e) => o.onerror && o.onerror(e))
  return o
}
const pool = crearPool(1, crearObrero)
const out = { pasos: [] }
const paso = async (nombre, fn) => {
  try { const v = await fn(); out.pasos.push({ nombre, ok: true }); return v } catch (e) { out.pasos.push({ nombre, ok: false, error: String(e && e.message || e) }); return null }
}
try {
  const archivos = {}
  for (const c of F.catalogo) if (c.archivo && c.ruta && fs.existsSync(c.ruta)) archivos[c.archivo] = new Uint8Array(fs.readFileSync(c.ruta))
  await pool.enviar('fuentes', { catalogo: F.catalogo, archivos, alias: F.alias || {} })
  const abrirMolde = () => pool.enviar('molde_a_abrir', { clave: 'molde', bytes: new Uint8Array(fs.readFileSync(F.plantilla)) })
  const contexto = () => pool.enviar('contexto_a', {
    clave: 'molde|diseno|previa', arte: new Uint8Array(fs.readFileSync(caso.arte)), registro: F.registro, ordenVar: F.orden_var || [],
    mapeoArte: caso.mapeo_arte, editablesCfg: caso.editables_cfg ?? null, editablesTamano: caso.editables_tamano ?? null,
    editablesColor: caso.editables_color ?? null, editablesMarca: caso.editables_marca ?? null,
    editablesSinMarca: caso.editables_sin_marca ?? null, marcasComoCruz: false, referencia: 'alto', borde: F.borde,
    objetos: [], conPersonalizacion: false,
  })
  // una pieza CON arte (la base nombra la mesa del arte) y sin objetos agregados de por medio
  const p = caso.piezas.find((x) => x.mesa_a) || caso.piezas[0]
  const pieza = () => pool.enviar('pieza_a', {
    molde: 'molde', arte: 'molde|diseno|previa', mesa: p.info.mesa, talle: p.talle, pieza: p.pieza, info: p.info,
    persona: p.persona, nro: p.nro, variante: p.variante ?? null, grupo: null, ph: {}, etiqueta: F.etiqueta,
    alias: F.alias || {}, salida: 'svg',
  }).then((r) => r.svg)
  await abrirMolde()
  await contexto()
  const svg1 = await paso('la pieza, la primera vez', pieza)
  await contexto()                                   // llega un arte nuevo: el contexto se rearma
  const svg2 = await paso('la misma pieza con el contexto rearmado', pieza)
  await abrirMolde()                                 // y si se vuelve a abrir el molde
  const svg3 = await paso('la misma pieza con el molde reabierto', pieza)
  out.pieza = `${p.pieza} · ${p.talle} · ${p.variante ?? 'sin variable'}`
  out.iguales = !!svg1 && svg1 === svg2 && svg1 === svg3
} finally {
  pool.cerrar()
}
fs.writeFileSync(salida, JSON.stringify(out))
