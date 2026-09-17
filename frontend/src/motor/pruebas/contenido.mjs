// node frontend/src/motor/pruebas/contenido.mjs <molde.ai> <carpeta_salida>
// Por mesa: el SHA-1 de los bytes del contenido (como `cortar_capas.contenido_crudo`) y una línea
// JSON por instrucción (`c<mesa>.ndjson`), normalizada para compararla con pikepdf
// (`verificar_navegador_contenido.py`).
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import * as mupdf from 'mupdf'
import { instrucciones, contenidoCrudo } from '../pdf/contenido.js'

const hex = (u8) => Buffer.from(u8).toString('hex')
function norm(v) {
  if (v === null || v === true || v === false) return v
  if (Array.isArray(v)) return ['a', v.map(norm)]
  if (v.i !== undefined) return ['i', Number(v.i)]
  if (v.r !== undefined) return ['r', Number(v.r)]
  if (v.n !== undefined) return ['n', v.n]
  if (v.s !== undefined) return ['s', hex(v.s)]
  if (v.d !== undefined) return ['d', [...v.d.entries()].sort((a, b) => (a[0] < b[0] ? -1 : 1)).map(([k, x]) => [k, norm(x)])]
  if (v.op_suelto !== undefined) return ['op', v.op_suelto]
  return ['?', String(v)]
}

const [, , entrada, carpeta] = process.argv
fs.mkdirSync(carpeta, { recursive: true })
const doc = mupdf.Document.openDocument(fs.readFileSync(entrada), 'application/pdf')
const resumen = []
for (let i = 0; i < doc.countPages(); i++) {
  const page = doc.loadPage(i)
  const t = performance.now()
  const crudo = contenidoCrudo(page)
  const fd = fs.openSync(path.join(carpeta, `c${i + 1}.ndjson`), 'w')
  let buf = []
  let n = 0
  for (const ins of instrucciones(crudo)) {
    n++
    const o = ins.op === 'INLINE IMAGE'
      ? { op: ins.op, dict: norm({ d: ins.dict }), len: ins.datos.length }
      : { op: ins.op, args: ins.args.map(norm) }
    buf.push(JSON.stringify(o))
    if (buf.length >= 20000) { fs.writeSync(fd, buf.join('\n') + '\n'); buf = [] }
  }
  if (buf.length) fs.writeSync(fd, buf.join('\n') + '\n')
  fs.closeSync(fd)
  resumen.push({ mesa: i + 1, bytes: crudo.length, sha1: crypto.createHash('sha1').update(crudo).digest('hex'),
    instrucciones: n, segundos: (performance.now() - t) / 1000 })
  page.destroy()
}
fs.writeFileSync(path.join(carpeta, 'resumen.json'), JSON.stringify({ mesas: resumen, memoria_mb: process.memoryUsage().rss / 1048576 }))
