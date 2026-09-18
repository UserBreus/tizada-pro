// EL ARTE SEPARADO PREPARADO EN EL NAVEGADOR, LISTO PARA `POST /api/arte` — PLAN_NAVEGADOR.md,
// etapa 3, camino A. Hace en el navegador lo que `servidor._subir_arte_analizar` hacía en el
// servidor (detección de mesas, personalización, mapeo por nombre + mapeo fijo, recorte por
// variable, validación) y lo empaqueta en el ZIP que `servidor._subir_arte_paquete` recibe como
// `paquete` junto con el `.ai`. El servidor NO vuelve a abrir el arte para calcular: sólo
// comprueba el sha1 y el modo, y guarda.
//
// Formato EXACTO del zip (todo en la raíz, sin carpetas; ningún otro nombre se admite):
//   manifest.json   {"sha1": <sha1 del .ai completo>, "modo": "separado" | "clasico"}
//   det.json        lo que devuelve `detectarArte` (una entrada por mesa del arte)
//   auto.json       el mapeo por nombre {pieza: mesa}
//   pers.json       la personalización {mesa: {campo: placeholder}}
//   mapeo.json      el mapeo final {pieza: mesa} = auto + los del mapeo FIJO que no pisen mesas
//   pv.json         {variante_clave: {pieza: mesa}} el recorte del mapeo por variable
//   validacion.json `validarArteSeparado` si el alcance quedó completo; si no, el aviso de
//                   «faltan asignar»; para el modo clásico, `validarArte`
import { zipSync } from 'fflate'
import { sha1HexBytes } from '../sha1.js'
import { extraerPersonalizacion } from './personalizacion.js'
import { detectarArte, mapeoPorNombre, arteEsSeparado, validarArte, validarArteSeparado } from './mapeo.js'

const texto = (o) => new TextEncoder().encode(JSON.stringify(o))

/**
 * `prepararArte(mupdf, bytes, contexto)` → `{zip, sha1, modo, det, auto, pers, mapeo, pv, validacion}`.
 *
 * `bytes` = el .ai tal cual lo eligió la persona (Uint8Array). `contexto` = lo que devuelve
 * `GET /api/productos/<pid>/arte_contexto`: `{registro, fijo, alcance, variantes: {clave: [piezas]},
 * orden_var, fuentes: {catalogo, alias}}`, más:
 *   · `plantilla` (Uint8Array, opcional): los bytes de `plantilla.ai`, para decidir el modo como
 *     el servidor (`arte_es_separado`) y para validar un arte clásico. Sin ella el modo es el de
 *     `contexto.modo` o, por defecto, «separado» (lo único que hoy sube el camino A).
 *   · `ancho_thumb` (opcional, 240): el ancho de las miniaturas de `det.json`.
 */
export function prepararArte(mupdf, bytes, contexto) {
  const registro = contexto.registro || {}
  const fijo = contexto.fijo || {}
  const alcance = new Set(contexto.alcance || Object.keys(registro))
  const variantes = contexto.variantes || {}
  const ordenVar = contexto.orden_var || []
  const fuentes = contexto.fuentes || { catalogo: [], alias: {} }
  const sha1 = sha1HexBytes(bytes)
  let modo = contexto.modo || 'separado'
  if (contexto.plantilla) modo = arteEsSeparado(mupdf, bytes, contexto.plantilla) ? 'separado' : 'clasico'
  const det = detectarArte(mupdf, bytes, registro, contexto.ancho_thumb || 240)
  let auto = {}, pers = {}, mapeo = {}, pv = {}, validacion
  if (modo === 'separado') {
    auto = mapeoPorNombre(mupdf, bytes, registro)
    pers = extraerPersonalizacion(mupdf, bytes)
    // Los NOMBRES de la guía mandan: el mapeo fijo sólo rellena piezas sin nombre y nunca pisa
    // una mesa ya reclamada (misma regla que `_subir_arte_analizar`)
    mapeo = { ...auto }
    const usadas = new Set(Object.values(mapeo))
    for (const [pieza, mesa] of Object.entries(fijo)) {
      const m = Math.trunc(Number(mesa))
      if (!m || !(pieza in registro)) continue
      if (!(pieza in mapeo) && !usadas.has(m)) { mapeo[pieza] = m; usadas.add(m) }
    }
    for (const [clave, piezas] of Object.entries(variantes)) {
      if (!clave || !piezas || !piezas.length) continue
      const r = {}
      for (const p of piezas) if (p in mapeo) r[p] = mapeo[p]
      pv[clave] = r
    }
    const completo = [...alcance].every((p) => p in mapeo)
    if (completo) {
      validacion = validarArteSeparado(mupdf, bytes, registro, fuentes, mapeo, ordenVar, [...alcance])
    } else {
      const faltan = [...alcance].filter((p) => !(p in mapeo)).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0))
      validacion = { aprobado: false, modo: 'separado',
                     checks: [{ nombre: 'Mapeo de arte a piezas', ok: false, detalle: 'faltan asignar (sin nombre en la guía): ' + faltan.join(', ') }],
                     personalizacion: {}, faltan }
    }
  } else {
    if (!contexto.plantilla) throw new Error('para validar un arte clásico hace falta la plantilla (contexto.plantilla)')
    validacion = validarArte(mupdf, bytes, contexto.plantilla, fuentes)
    pers = validacion.personalizacion || {}
  }
  const entradas = {
    'manifest.json': [texto({ sha1, modo }), { level: 6 }],
    'det.json': [texto(det), { level: 6 }],
    'auto.json': [texto(auto), { level: 6 }],
    'pers.json': [texto(pers), { level: 6 }],
    'mapeo.json': [texto(mapeo), { level: 6 }],
    'pv.json': [texto(pv), { level: 6 }],
    'validacion.json': [texto(validacion), { level: 6 }],
  }
  return { zip: zipSync(entradas), sha1, modo, det, auto, pers, mapeo, pv, validacion }
}
