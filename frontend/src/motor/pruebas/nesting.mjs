// node frontend/src/motor/pruebas/nesting.mjs <fixture.json> <salida.json>
// El nesting por contorno del navegador (`motor/nesting/contorno.js`) sobre los escenarios del
// fixture (piezas con su `base` = contorno + geometría, y la `cfg` de la tela). Lo compara
// `verificar_navegador_nesting.py` contra `nesting_contorno.anidar_contorno`: mismas
// colocaciones (hoja, orden, x, y, ángulo), misma área y mismo consumo.
import fs from 'node:fs'
import { anidarContorno, DEBUG } from '../nesting/contorno.js'

const [, , entrada, salida] = process.argv
const fx = JSON.parse(fs.readFileSync(entrada, 'utf8'))
const out = []
for (const esc of fx.escenarios) {
  const t0 = performance.now()
  const { colocaciones, area, consumo } = anidarContorno(esc.piezas, esc.cfg)
  const segundos = (performance.now() - t0) / 1000
  // la máscara de cada pieza (alto, ancho, celdas ocupadas y una suma ponderada por posición):
  // el contrato la compara con `p["_mask"]` de Python, aparte de las colocaciones
  const mascaras = {}
  for (const p of esc.piezas) {
    const m = p._mask
    let n = 0, h = 0
    for (let i = 0; i < m.d.length; i++) if (m.d[i]) { n++; h += i + 1 }
    mascaras[p.idx] = [m.h, m.w, n, h]
  }
  out.push({
    nombre: esc.nombre, segundos, area, consumo, debug: { ...DEBUG }, mascaras,
    hojas: colocaciones.map((h) => h.map((c) => ({ idx: c.pieza.idx, ang: c.ang, cx: c.cx, cy: c.cy, bw: c.bw, bh: c.bh }))),
  })
}
fs.writeFileSync(salida, JSON.stringify({ escenarios: out }))
