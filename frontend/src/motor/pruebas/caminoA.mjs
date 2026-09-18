// node frontend/src/motor/pruebas/caminoA.mjs <molde.ai> <salida.json> [--manual manual.json] [--paquete salida.zip]
// El molde SIN diseño (camino A) leído por el motor del navegador: capas de la interfaz, talles,
// `alta_plantilla`, `detectar_piezas` (talle de referencia automático y por talle),
// `detectar_piezas_todas` y `alta_plantilla_manual`. Con `--paquete` arma además el ZIP `alta_a`
// que se manda al servidor. Lo compara `verificar_navegador_camino_a.py` contra `motor_pedido`.
//
// `manual.json` = {asignaciones, mesa, talle_ref, indices?, emparejado?, excluir_talles?}: los
// mismos argumentos con que el contrato llama al Python. Sin él, se nombran las primeras piezas
// del talle de referencia detectado y el resto queda con nombre provisorio; si al lado del molde
// hay un `correspondencia_piezas.json` (la del DXF), se usan sus nombres y su correspondencia.
import fs from 'node:fs'
import path from 'node:path'
import * as mupdf from 'mupdf'
import { MoldeA, capasUI, tallesDePlantilla, altaPlantilla, detectarPiezas, detectarPiezasTodas,
  altaPlantillaManual, prepararCaminoA, aTextoJSON } from '../molde/caminoA.js'
import { armarPaqueteCaminoA } from '../paquete/armar.js'

const args = process.argv.slice(2)
const entrada = args[0], salida = args[1]
const opcion = (nombre) => { const i = args.indexOf(nombre); return i >= 0 ? args[i + 1] : null }
const manualPath = opcion('--manual'), paquetePath = opcion('--paquete')

const t0 = performance.now()
const bytes = new Uint8Array(fs.readFileSync(entrada))
const doc = mupdf.Document.openDocument(bytes, 'application/pdf')
const molde = new MoldeA(mupdf, doc)

// cada paso por separado: si el servidor lanza, el navegador tiene que lanzar el MISMO texto
const intentar = (fn) => {
  try { return fn() } catch (e) { return { error: e.message } }
}

const out = {}
out.capas_ui = capasUI(doc).map((c) => c.text)
out.talles = tallesDePlantilla(molde)
out.alta = intentar(() => altaPlantilla(molde))
out.detectar = intentar(() => detectarPiezas(molde))
out.todas = intentar(() => detectarPiezasTodas(molde))
out.por_talle = new Map()
for (const t of out.detectar.error ? [] : out.detectar.talles) out.por_talle.set(t, intentar(() => detectarPiezas(molde, t)))

let manual = null
if (manualPath) {
  manual = JSON.parse(fs.readFileSync(manualPath, 'utf-8'))
} else if (!out.detectar.error) {
  const det = out.detectar
  const corr = path.join(path.dirname(entrada), 'correspondencia_piezas.json')
  let indices = null, asignaciones
  if (fs.existsSync(corr)) {
    indices = JSON.parse(fs.readFileSync(corr, 'utf-8'))
    asignaciones = (indices[det.talle_ref] || []).map((nombre, idx) => ({ idx, nombre }))
  } else {
    const nombres = ['Frente', 'Frente', 'Dorso', 'Manga corta derecha', 'Cuello']
    asignaciones = nombres.slice(0, det.piezas.length).map((nombre, idx) => ({ idx, nombre }))
  }
  manual = { asignaciones, mesa: det.mesa, talle_ref: det.talle_ref, indices, emparejado: null, excluir_talles: null }
}
out.manual = manual
  ? intentar(() => altaPlantillaManual(molde, manual.asignaciones, manual.mesa, manual.talle_ref,
    manual.indices || null, manual.emparejado || null, manual.excluir_talles || null))
  : null

if (paquetePath) {
  const preparado = prepararCaminoA(molde)
  const { zip, sha1 } = armarPaqueteCaminoA(bytes, preparado, { motor: 'mupdf.js (Node, contrato)' })
  fs.writeFileSync(paquetePath, zip)
  out.paquete = { sha1, bytes: zip.length, detecciones: [...preparado.deteccion.porTalle.keys()] }
}
out.segundos = (performance.now() - t0) / 1000
molde.destroy()
fs.writeFileSync(salida, aTextoJSON(out))
