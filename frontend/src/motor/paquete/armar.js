// EL PAQUETE DEL MOLDE — lo que el navegador manda al servidor con «Guardar» (PLAN_NAVEGADOR.md §5).
//
// El navegador ya preparó el molde entero (`molde/desplegar.js`); el servidor NO vuelve a hacerlo:
// recibe el archivo original y este paquete, lo valida y lo guarda tal cual (ver
// `servidor._paquete_molde_aplicar`). Es un ZIP con una lista CERRADA de archivos:
//
//   manifest.json                     qué es, de qué archivo (SHA-1) y con qué reglas se armó
//   alta.json                         el resultado del alta (registro, visor, talles, resumen)
//   desplegado/m{mesa}.json           contornos, placeholders, línea de corte, etiqueta del archivo
//   desplegado/m{mesa}.pdf            una página por talle
//   desplegado/etiqueta_archivo.json  la decisión por familia
//
// Las versiones van en el manifiesto: si el servidor tiene otra regla (otra `_V_PAGINAS`, por
// ejemplo), rechaza el paquete en vez de guardar un desplegado viejo.

import { zipSync } from 'fflate'
import { aJSON } from '../molde/contornos.js'
import { aTextoJSON } from '../molde/caminoA.js'
import { sha1HexBytes } from '../sha1.js'
import { V_CONTORNOS, V_PAGINAS } from '../molde/desplegar.js'
import { V_ETQ } from '../molde/paginas.js'

export const FORMATO = 'tizada.molde_con_diseno'
export const VERSION_PAQUETE = 1

const texto = (o) => new TextEncoder().encode(JSON.stringify(o))

/**
 * `archivo` = los bytes del .ai tal cual los eligió la persona; `desplegado` = lo que devolvió
 * `desplegarMolde` (o `faseA`/`faseB` de `desplegar_paralelo.js`). Devuelve `{zip: Uint8Array, sha1}`.
 * `fase`: 'completo' (todo), 'contornos' (fase A: alta + contornos, sin páginas) o 'paginas'
 * (fase B: páginas, decisión de la etiqueta y JSON completos). `sha1` se puede pasar ya calculado.
 */
export function armarPaqueteMolde(archivo, desplegado, { motor = 'mupdf.js', fase = 'completo', sha1 = null } = {}) {
  sha1 = sha1 || sha1HexBytes(archivo)
  const entradas = {
    'manifest.json': [texto({ formato: FORMATO, version: VERSION_PAQUETE, fase, sha1, bytes: archivo ? archivo.length : null,
      v_contornos: V_CONTORNOS, v_paginas: V_PAGINAS, v_etq: V_ETQ, mesas: desplegado.mesas.size,
      talles: desplegado.talles, motor, armado: new Date().toISOString() }), { level: 6 }],
    'alta.json': [texto(aJSON(desplegado.alta)), { level: 6 }],
  }
  for (const [m, { json, pdf }] of desplegado.mesas) {
    entradas[`desplegado/m${m}.json`] = [texto(aJSON(json)), { level: 6 }]
    if (pdf && fase !== 'contornos') entradas[`desplegado/m${m}.pdf`] = [pdf, { level: 0 }]   // ya viene comprimido
  }
  if (desplegado.etiqueta && fase !== 'contornos') entradas['desplegado/etiqueta_archivo.json'] = [texto(aJSON(desplegado.etiqueta)), { level: 6 }]
  return { zip: zipSync(entradas), sha1 }
}

// ─── EL PAQUETE DEL MOLDE SIN DISEÑO (camino A) ──────────────────────────────────────────────
// Lo que el servidor valida en `_paquete_molde_aplicar` con `fase == "alta_a"` (PLAN_NAVEGADOR 1b):
//
//   manifest.json            {formato, version, fase: "alta_a", sha1, dxf: null | {resumen del DXF, indices}}
//   alta.json                lo que devolvió `altaPlantilla` (o `altaPlantillaManual` si el DXF trajo
//                            nombres): mesas, talles, registro, problemas, advertencias, piezas_detalle…
//   deteccion/auto.json      `detectarPiezas(molde)` (talle de referencia automático)
//   deteccion/<talle>.json   `detectarPiezas(molde, talle)` — el nombre del archivo se limpia como el
//                            servidor limpia el de su caché (`[^A-Za-z0-9_-]+` → «_»)
//   deteccion/todas.json     `detectarPiezasTodas(molde)` (el servidor le agrega `formato`)
//   plantilla_fuente.dxf     el DXF original, si el molde vino de uno
//
// El servidor escribe las detecciones en su caché con el mtime final del archivo y NO vuelve a
// leer el molde (`_escribir_deteccion_paquete`). Los JSON se escriben con `aTextoJSON`: llevan
// diccionarios con el nombre del talle de clave y JavaScript reordenaría los que parecen números.

export const FASE_ALTA_A = 'alta_a'
const textoPy = (o) => new TextEncoder().encode(aTextoJSON(o))
const limpiarNombre = (s) => s.replace(/[^A-Za-z0-9_-]+/g, '_')

/**
 * `archivo` = los bytes del .ai (o del PDF convertido del DXF); `preparado` = lo que devolvió
 * `prepararCaminoA` ({alta, deteccion: {auto, porTalle, todas}, dxf}). `dxfBytes` = el DXF
 * original, si lo hubo. Devuelve `{zip: Uint8Array, sha1}`.
 */
export function armarPaqueteCaminoA(archivo, preparado, { motor = 'mupdf.js', sha1 = null, dxfBytes = null } = {}) {
  sha1 = sha1 || sha1HexBytes(archivo)
  const { alta, deteccion = {}, dxf = null } = preparado
  const entradas = {
    'manifest.json': [texto({ formato: FORMATO, version: VERSION_PAQUETE, fase: FASE_ALTA_A, sha1,
      bytes: archivo ? archivo.length : null, mesas: alta.mesas, talles: alta.talles, motor,
      armado: new Date().toISOString(), dxf: dxf || null }), { level: 6 }],
    'alta.json': [textoPy(alta), { level: 6 }],
  }
  if (deteccion.auto) entradas['deteccion/auto.json'] = [textoPy(deteccion.auto), { level: 6 }]
  for (const [t, d] of deteccion.porTalle || []) {
    const nombre = limpiarNombre(t)
    // un talle que se llame «auto» o «todas» pisaría los archivos fijos: se deja afuera (el
    // servidor lo calcula cuando lo pidan)
    if (!d || !nombre || nombre === 'auto' || nombre === 'todas') continue
    entradas[`deteccion/${nombre}.json`] = [textoPy(d), { level: 6 }]
  }
  if (deteccion.todas) entradas['deteccion/todas.json'] = [textoPy(deteccion.todas), { level: 6 }]
  if (dxfBytes) entradas['plantilla_fuente.dxf'] = [dxfBytes, { level: 6 }]
  return { zip: zipSync(entradas), sha1 }
}
