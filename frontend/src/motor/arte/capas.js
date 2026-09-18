// LAS CAPAS DEL ARTE QUE NO SE IMPRIMEN — `motor_pedido._es_capa_guia` / `_es_capa_editable`.
//
// «guías» es texto para el sistema (qué pieza es cada mesa, rangos) y nunca se ve ni se estampa;
// «Editable …» es un objeto que el usuario mueve/escala y lo dibuja el motor aparte, con su
// transform. Las dos se apagan para mirar la mesa (`/api/arte/mesa_img`) y para armar la pieza.
import { normCapa } from '../molde/talle.js'

export const esCapaGuia = (nombre) => ['guias', 'guia', 'guides'].includes(normCapa(nombre || ''))
export const esCapaEditable = (nombre) => normCapa(nombre || '').startsWith('editable')

/** Apaga en `doc` (PDFDocument de mupdf.js) las capas guía y editables. Devuelve sus nombres. */
export function apagarCapasNoImpresas(doc) {
  const apagadas = []
  try {
    for (let i = 0; i < doc.countLayers(); i++) {
      const n = doc.getLayerName(i) || ''
      if (esCapaGuia(n) || esCapaEditable(n)) { doc.setLayerVisible(i, false); apagadas.push(n) }
    }
  } catch { /* un arte sin capas */ }
  return apagadas
}
