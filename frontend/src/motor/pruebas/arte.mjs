// node frontend/src/motor/pruebas/arte.mjs <arte.ai> <registro.json> <salida.json> [variantes_orden.json]
// El arte SEPARADO (camino A) leído por el motor del navegador: personalización, editables,
// mapeo por nombre, mapeo por variante, detección, validación y el paquete para `POST /api/arte`.
// Lo compara `verificar_navegador_arte.py` contra motor_pedido.
//
// `registro.json` puede ser el registro pelado {pieza: {talle: {w_cm, h_cm, …}}} o un FIXTURE
// {registro, variantes_orden, catalogo, alias, plantilla, mapeo, piezas_scope, fijo, alcance,
// variantes}: con la plantilla se corre también `arteEsSeparado`/`validarArte` y con el catálogo
// las validaciones. `variantes_orden.json` (opcional) manda sobre el del fixture.
import fs from 'node:fs'
import * as mupdf from 'mupdf'
import { extraerPersonalizacion } from '../arte/personalizacion.js'
import { extraerEditables } from '../arte/editables.js'
import { mapeoPorNombre, mapeoVariantesArte, arteEsSeparado, detectarArte, validarArte, validarArteSeparado,
         fuentesRequeridasArte } from '../arte/mapeo.js'
import { prepararArte } from '../arte/preparar.js'

const [, , rutaArte, rutaRegistro, salida, rutaOrden] = process.argv
const t0 = performance.now()
const bytes = new Uint8Array(fs.readFileSync(rutaArte))
let F = JSON.parse(fs.readFileSync(rutaRegistro, 'utf-8'))
if (!F.registro) F = { registro: F }
const registro = F.registro
const orden = rutaOrden ? JSON.parse(fs.readFileSync(rutaOrden, 'utf-8')) : (F.variantes_orden || [])
const fuentes = { catalogo: F.catalogo || [], alias: F.alias || {} }
const plantilla = F.plantilla ? new Uint8Array(fs.readFileSync(F.plantilla)) : null
const estricto = !!process.env.ARTE_ESTRICTO

const out = {}
const medir = (nombre, fn) => { const t = performance.now(); out[nombre] = fn(); out.tiempos = out.tiempos || {}; out.tiempos[nombre] = (performance.now() - t) / 1000 }
medir('personalizacion', () => extraerPersonalizacion(mupdf, bytes))
medir('editables', () => extraerEditables(mupdf, bytes, { estricto }))
medir('mapeo_por_nombre', () => mapeoPorNombre(mupdf, bytes, registro))
medir('mapeo_variantes', () => mapeoVariantesArte(mupdf, bytes, registro, orden))
medir('fuentes_requeridas', () => fuentesRequeridasArte(mupdf, bytes))
medir('detectar', () => detectarArte(mupdf, bytes, registro, F.ancho_thumb || 240))
if (plantilla) medir('es_separado', () => arteEsSeparado(mupdf, bytes, plantilla))
if (F.mapeo) medir('validar_separado', () => validarArteSeparado(mupdf, bytes, registro, fuentes, F.mapeo, orden, F.piezas_scope ?? null))
if (plantilla) medir('validar_clasico', () => validarArte(mupdf, bytes, plantilla, fuentes))
if (F.contexto !== false) {
  medir('paquete', () => {
    const r = prepararArte(mupdf, bytes, { registro, fijo: F.fijo || {}, alcance: F.alcance || Object.keys(registro),
      variantes: F.variantes || {}, orden_var: orden, fuentes, plantilla, ancho_thumb: F.ancho_thumb || 240 })
    const zipPath = salida + '.paquete.zip'
    fs.writeFileSync(zipPath, r.zip)
    return { zip: zipPath, sha1: r.sha1, modo: r.modo, mapeo: r.mapeo, pv: r.pv, auto: r.auto, validacion: r.validacion }
  })
}
out.segundos = (performance.now() - t0) / 1000
fs.writeFileSync(salida, JSON.stringify(out))
