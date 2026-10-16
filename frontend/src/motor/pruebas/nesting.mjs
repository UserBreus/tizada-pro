// node frontend/src/motor/pruebas/nesting.mjs <fixture.json> <salida.json>
// El nesting por contorno del navegador (`motor/nesting/contorno.js`) sobre los escenarios del
// fixture (piezas con su `base` = contorno + geometría, y la `cfg` de la tela). Lo compara
// `verificar_navegador_nesting.py` contra `nesting_contorno.anidar_contorno`: mismas
// colocaciones (hoja, orden, x, y, ángulo), misma área y mismo consumo.
import fs from 'node:fs'
import { anidarContorno, anidarPorFila, DEBUG } from '../nesting/contorno.js'
import { abrirCarriles, crearEjecutor, hilosParaCarriles } from '../nesting/carriles.js'

const [, , entrada, salida] = process.argv
const fx = JSON.parse(fs.readFileSync(entrada, 'utf8'))
const out = []
// 🔴 CON LOS HILOS DE VERDAD (MAPA 728): el contrato compara el acomodo en varios hilos contra Python en uno;
// `TIZADA_NESTING_UN_HILO=1` lo corre acá mismo (para medir o comparar los dos caminos)
// (con los mismos canales que usa la hoja: los hilos se abren acá y el ejecutor les habla por sus puertos)
const carriles = process.env.TIZADA_NESTING_UN_HILO === '1' ? null : await abrirCarriles(await hilosParaCarriles())
const ejecutor = carriles ? crearEjecutor({ puertos: carriles.puertos }) : null
for (const esc of fx.escenarios) {
  const t0 = performance.now()
  // COPIA (MAPA 581/701): con `por_fila`, el acomodado por fila + las copias a lo ancho
  const { colocaciones, area, consumo, mesas = null } = (esc.cfg.por_fila || esc.cfg.por_talles_mesa || esc.cfg.separar_disenos) ? await anidarPorFila(esc.piezas, esc.cfg, ejecutor) : await anidarContorno(esc.piezas, esc.cfg, ejecutor)
  const segundos = (performance.now() - t0) / 1000
  // la máscara de cada pieza (alto, ancho, celdas ocupadas y una suma ponderada por posición):
  // el contrato la compara con `p["_mask"]` de Python, aparte de las colocaciones
  const mascaras = {}
  for (const p of esc.piezas) {
    const m = p._mask
    if (!m) { mascaras[p.idx] = null; continue }      // Copia mezclada (MAPA 717): la fila no se prepara
    let n = 0, h = 0
    for (let i = 0; i < m.d.length; i++) if (m.d[i]) { n++; h += i + 1 }
    mascaras[p.idx] = [m.h, m.w, n, h]
  }
  out.push({
    nombre: esc.nombre, segundos, area, consumo, debug: { ...DEBUG }, mascaras, mesas,
    hojas: colocaciones.map((h) => h.map((c) => ({ idx: c.pieza.idx, ang: c.ang, cx: c.cx, cy: c.cy, bw: c.bw, bh: c.bh }))),
  })
}
if (ejecutor) { ejecutor.cerrar(); carriles.cerrar() }
fs.writeFileSync(salida, JSON.stringify({ escenarios: out }))
