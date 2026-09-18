// node frontend/src/motor/pruebas/subida_a.mjs <molde.ai|molde.dxf> <archivo_a_subir.pdf> <paquete.zip> <resumen.json>
// Lo que `prepararMolde.js` hace en el navegador con un molde SIN diseño o un DXF (camino A), en
// Node: convertir el DXF (`dxf_convertir`), dar de alta (`alta_a`) y armar el paquete `alta_a`.
// Lo compara `verificar_navegador_subida_a.py` subiéndolo al servidor con una base de mentira.
import fs from 'node:fs'
import * as mupdf from 'mupdf'
import { dxfAPdf } from '../dxf/importar.js'
import { MoldeA, prepararCaminoA } from '../molde/caminoA.js'
import { armarPaqueteCaminoA } from '../paquete/armar.js'
import { sha1HexBytes } from '../sha1.js'

const [, , entrada, salidaArchivo, salidaZip, salidaJson] = process.argv
const t0 = performance.now()
let bytes = new Uint8Array(fs.readFileSync(entrada))
let dxf = null, dxfBytes = null
if (/\.dxf$/i.test(entrada)) {
  const r = dxfAPdf(mupdf, bytes)
  dxf = r.resumen
  dxfBytes = bytes
  bytes = new Uint8Array(r.pdf)
}
const sha1 = sha1HexBytes(bytes)
const doc = mupdf.Document.openDocument(bytes, 'application/pdf')
const molde = new MoldeA(mupdf, doc)
// el mismo armado que la tarea `alta_a` del hilo de trabajo (obrero.worker.js)
const indices = dxf && dxf.indices ? dxf.indices : null
const preparado = prepararCaminoA(molde, { indices, dxf: dxf ? { ...dxf, indices } : null })
const { zip } = armarPaqueteCaminoA(null, preparado, { motor: 'mupdf.js (Node, contrato)', sha1, dxfBytes })
molde.destroy()
fs.writeFileSync(salidaArchivo, bytes)
fs.writeFileSync(salidaZip, zip)
fs.writeFileSync(salidaJson, JSON.stringify({
  sha1, mesas: preparado.alta.mesas, talles: preparado.alta.talles, piezas: preparado.alta.registro.size,
  dxf: preparado.dxf || null, detecciones: [...preparado.deteccion.porTalle.keys()],
  segundos: (performance.now() - t0) / 1000,
}))
