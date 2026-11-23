// node frontend/src/motor/pruebas/corte_exportar.mjs <pedidos.json>
// Cada mesa de una hoja de corte en los cinco formatos (`corte/exportar.js`, lo mismo que el hilo
// `corte_exportar` de la pantalla). pedidos.json = [{pdf, pi, base}] → escribe base.dxf/.ai/.plt/.svg/.eps
// e imprime (última línea) [{piezas, letras}] por mesa. Lo usa `verificar_tizada_corte.py`.
import fs from 'node:fs'
import * as mupdf from 'mupdf'
import { exportarMesa } from '../corte/exportar.js'

const pedidos = JSON.parse(fs.readFileSync(process.argv[2], 'utf-8'))
const out = []
for (const p of pedidos) {
  const bytes = new Uint8Array(fs.readFileSync(p.pdf))
  let info = null
  for (const f of ['dxf', 'ai', 'plt', 'svg', 'eps']) {
    const r = exportarMesa(mupdf, bytes, p.pi, f, { titulo: 'mesa' })
    fs.writeFileSync(`${p.base}.${f}`, r.bytes)
    info = { piezas: r.piezas, letras: r.letras }
  }
  out.push(info)
}
console.log(JSON.stringify(out))
