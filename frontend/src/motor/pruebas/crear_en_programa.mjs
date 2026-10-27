// node frontend/src/motor/pruebas/crear_en_programa.mjs <estado.json> <carpeta> <direccion> <programa> <diseno> <salida.json>
// El código que se le entrega al otro sistema para mandar la plantilla a Illustrator / CorelDRAW
// (`documentacion/integracion_externa/codigo/crear_en_programa.js`), corrido de verdad contra un conector de
// prueba (`direccion`). `traer` lee los archivos que el contrato bajó de la API a `carpeta`. Lo usa
// `verificar_integracion_externa.py` (sección 10).
import fs from 'node:fs'
import path from 'node:path'
import { crearEnPrograma, buscarConector } from '../../../../documentacion/integracion_externa/codigo/crear_en_programa.js'

const [, , estJson, carpeta, direccion, programa, diseno, salida] = process.argv
const estado = JSON.parse(fs.readFileSync(estJson, 'utf8'))
const pasos = []
let out
try {
  const r = await crearEnPrograma({
    programa, estado, diseno, direccion,
    traer: async (a) => fs.readFileSync(path.join(carpeta, a.nombre), 'utf8'),
    alAvanzar: (t) => pasos.push(t),
  })
  out = { ...r, pasos }
} catch (e) {
  out = { ok: false, codigo: e.codigo || null, error: String(e.message || e), instalador: e.instalador || null, pasos }
}
// sin conector en esa dirección: lo tiene que decir con su código
out.sinConector = await buscarConector(programa, { direccion: 'http://127.0.0.1:9', esperaMs: 1500 })
fs.writeFileSync(salida, JSON.stringify(out))
