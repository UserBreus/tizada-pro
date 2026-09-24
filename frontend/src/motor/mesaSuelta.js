// UNA MESA SUELTA PARA DESCARGAR, ARMADA EN ESTA COMPUTADORA — 2026-09-22.
//
// 🔴 POR QUÉ: «el servidor será sólo para sostener el sistema y la base». Bajar una sola mesa de
// una hoja de varias páginas era `GET /api/trabajos/<tid>/mesa/<archivo>`: el servidor abría la
// hoja con pikepdf, copiaba la página a un PDF nuevo con el perfil de color y lo guardaba. Acá se
// hace lo mismo (`obrero.worker.js` → `pagina_pdf`) con la hoja que el navegador ya tiene (la
// guardó al generar el pedido o al mostrarlo) o que baja una vez como archivo estático.
import { bytesDeArchivo } from './vista/vista.js'
import { enHiloSuelto } from './hiloSuelto.js'

/** Devuelve una función que ARMA el PDF de la página `pi` de `archivo` (para `descargarArchivo`). */
export function mesaSuelta({ tid, archivo, pi, rutaApi }) {
  return async () => {
    const bytes = await bytesDeArchivo(`${tid}|${archivo}`, async () => {
      const r = await fetch(rutaApi(`/trabajos/${encodeURIComponent(tid)}/${encodeURIComponent(archivo)}`))
      if (!r.ok) throw new Error('no se pudo bajar la hoja')
      return r.arrayBuffer()
    })
    if (!bytes) throw new Error('no se pudo leer la hoja')
    const copia = bytes.slice()
    const pdf = await enHiloSuelto('pagina_pdf', { bytes: copia, pi }, [copia.buffer], 'descarga')
    return new Blob([pdf], { type: 'application/pdf' })
  }
}
