// node frontend/src/motor/pruebas/a_medida.mjs <ancho_m> <alto_m> <pieza> <salida.pdf> <resumen.json>
// MOLDE A MEDIDA (MAPA 623): fabrica el PDF del rectángulo y corre el alta del camino A (la misma
// que corre el obrero en el navegador) para ver que la pieza queda nombrada, con su talle y su
// medida. Lo usa `verificar_molde_a_medida.py`.
import fs from 'node:fs'
import * as mupdf from 'mupdf'
import { pdfMoldeAMedida, cabeEnTela, talleDeMedida } from '../molde/aMedida.js'
import * as CA from '../molde/caminoA.js'

const [, , ancho, alto, pieza, salidaPdf, salidaJson] = process.argv
const anchoM = Number(ancho), altoM = Number(alto)
const r = pdfMoldeAMedida(mupdf, { anchoM, altoM, pieza })
fs.writeFileSync(salidaPdf, r.pdf)
const doc = mupdf.Document.openDocument(r.pdf, 'application/pdf')
const molde = new CA.MoldeA(mupdf, doc)
const prep = CA.prepararCaminoA(molde, { dxf: r.resumen, indices: r.resumen.indices })
const reg = {}
for (const [nom, porTalle] of prep.alta.registro) {
  reg[nom] = {}
  for (const [t, info] of porTalle) reg[nom][t] = { mesa: info.mesa, pieza_idx: info.pieza_idx, w_cm: info.w_cm, h_cm: info.h_cm }
}
fs.writeFileSync(salidaJson, JSON.stringify({
  talle: talleDeMedida(anchoM, altoM), resumen: r.resumen, registro: reg, talles: prep.alta.talles,
  problemas: prep.alta.problemas, dxf: prep.dxf,
  det_auto: prep.deteccion.auto ? { talles: prep.deteccion.auto.talles, piezas: prep.deteccion.auto.piezas.length } : null,
  cabe: [
    cabeEnTela({ anchoM: 3, altoM: 2, anchoCm: 157, largoMaxCm: 2000 }),
    cabeEnTela({ anchoM: 1.5, altoM: 3, anchoCm: 157, largoMaxCm: 2000, margenNestingMm: 10 }),
    cabeEnTela({ anchoM: 3, altoM: 1.5, anchoCm: 157, largoMaxCm: 2000, margenNestingMm: 10, rotacion: '90' }),
    cabeEnTela({ anchoM: 1.56, altoM: 1, anchoCm: 157, largoMaxCm: 2000, bordeMm: 1 }),
    cabeEnTela({ anchoM: 1, altoM: 25, anchoCm: 157, largoMaxCm: 2000 }),
  ],
}, null, 1))
