// node frontend/src/motor/pruebas/contornos_capas.mjs <archivo.pdf> <resultado.json>
// FORMAS POR CAPA (MAPA 751): los contornos que lee la PC del archivo que sube el usuario (`contornosDePdf`)
// traen la CAPA de donde salieron, igual que el gemelo de Python (`piezas_molde.contornos_de_pdf`). Lo usa
// el contrato `verificar_formas_por_capa.py`. Sólo LEE el archivo.
import fs from 'node:fs'
import * as mupdf from 'mupdf'
import { contornosDePdf } from '../molde/herramientas.js'

const [, , entrada, salida] = process.argv
const conts = contornosDePdf(mupdf, new Uint8Array(fs.readFileSync(entrada)))
fs.writeFileSync(salida, JSON.stringify(conts.map((c) => ({ capa: c.capa, w: c.w, h: c.h, bbox_raw: c.bbox_raw }))))
