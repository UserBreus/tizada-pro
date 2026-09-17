// node frontend/src/motor/pruebas/curvas.mjs <casos.json> <salida.json>
// Texto a curvas con el motor del navegador (`texto/curvas.js`, opentype.js) sobre los casos que
// arma `verificar_navegador_curvas.py`: por fuente, `faltantes`/`prestados` de cada texto, el ancho y
// los operadores de `opsTexto` por tamaño y ángulo, `opsTextoCurva` por alineación, `opsTextoFiel`
// y la lista de `sustituidos`. La SECUENCIA de llamadas es la misma que en el contrato (la caché y
// los sustituidos dependen del orden). Un error se anota como null (el Python hace lo mismo).
import fs from 'node:fs'
import { FuenteCurvas } from '../texto/curvas.js'

const [, , rutaCasos, salida] = process.argv
const casos = JSON.parse(fs.readFileSync(rutaCasos, 'utf8'))
const leer = (ruta) => new Uint8Array(fs.readFileSync(ruta))
const intentar = (f) => { try { return f() } catch (e) { return null } }

const resultado = {}
for (const fu of casos.fuentes) {
  const t0 = performance.now()
  let r
  try {
    const respaldo = fu.respaldo ? new FuenteCurvas(leer(fu.respaldo)) : null
    const fc = new FuenteCurvas(leer(fu.ruta), respaldo)
    const sizes = casos.sizes.map((s) => (s === 'alto3mm' ? fc.sizeParaAlto(3 * 2.83465) : s))
    r = { upem: fc.upem, cap_ratio: fc.capRatio, sizes, faltantes: {}, prestados: {}, ancho: {}, ops: {}, curva: {}, fiel: {}, sustituidos: null }
    for (const texto of casos.textos) {
      r.faltantes[texto] = fc.faltantes(texto)
      r.prestados[texto] = fc.prestados(texto)
      sizes.forEach((size, si) => {
        r.ancho[`${texto}|${si}`] = intentar(() => fc.anchoTexto(texto, size))
        for (const ang of casos.angulos) {
          r.ops[`${texto}|${si}|${ang}`] = intentar(() => fc.opsTexto(texto, size, casos.pos[0], casos.pos[1], ang))
        }
        for (const al of casos.curva.aligns) {
          r.curva[`${texto}|${si}|${al}`] = intentar(() => fc.opsTextoCurva(texto, size, casos.curva.puntos, casos.curva.x0, casos.curva.x1, al))
        }
        r.curva[`${texto}|${si}|2pts`] = intentar(() => fc.opsTextoCurva(texto, size, casos.curva.puntos.slice(0, 2)))
      })
    }
    sizes.forEach((size, si) => { r.fiel[String(si)] = intentar(() => fc.opsTextoFiel(casos.fiel.texto, size, casos.fiel.glifos)) })
    r.sustituidos = fc.sustituidos
  } catch (e) {
    r = { error: String(e && e.message || e) }
  }
  r.segundos = (performance.now() - t0) / 1000
  resultado[fu.nombre] = r
}
fs.writeFileSync(salida, JSON.stringify(resultado))
