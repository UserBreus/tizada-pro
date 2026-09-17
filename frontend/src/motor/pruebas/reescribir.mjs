// node frontend/src/motor/pruebas/reescribir.mjs <entrada.bin> <salida.bin>
// Lee un content-stream crudo, lo parte en instrucciones y lo vuelve a escribir con `escribir`.
// Lo usa `verificar_navegador_reescribir.py` para comparar byte a byte contra pikepdf.
import fs from 'node:fs'
import { instrucciones, escribir } from '../pdf/contenido.js'

const [, , entrada, salida] = process.argv
const datos = new Uint8Array(fs.readFileSync(entrada))
// el archivo trae varios trozos: [largo (8 bytes LE)][bytes]…, y la salida igual
const out = []
let p = 0
while (p < datos.length) {
  const largo = Number(new DataView(datos.buffer, datos.byteOffset + p, 8).getBigUint64(0, true))
  p += 8
  const trozo = datos.subarray(p, p + largo)
  p += largo
  const b = escribir(instrucciones(trozo))
  const cab = new Uint8Array(8)
  new DataView(cab.buffer).setBigUint64(0, BigInt(b.length), true)
  out.push(cab, b)
}
fs.writeFileSync(salida, Buffer.concat(out.map((x) => Buffer.from(x.buffer, x.byteOffset, x.byteLength))))
