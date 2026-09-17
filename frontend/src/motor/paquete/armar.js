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
