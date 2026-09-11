// ── DESCARGAR ELIGIENDO DÓNDE ────────────────────────────────────────────────────────────────
// Pedido del usuario (2026-09-11): «cuando descargás el PDF, que te abra la carpeta de elegir dónde
// guardarlo». Un `<a download>` común deja al navegador guardar solo en "Descargas". Chrome y Edge
// tienen la File System Access API: la página abre el «Guardar como» NATIVO y escribe el archivo
// donde el usuario eligió. Para «Descargar todo» hay algo mejor que 30 diálogos: elegir UNA carpeta
// y guardar todas las mesas ahí.
//
// Reglas de este módulo:
//   · Si el navegador NO tiene la API (Firefox, Safari, celular), se cae al `<a download>` de
//     siempre: la descarga nunca deja de funcionar.
//   · Si el usuario CANCELA el diálogo, NO se descarga nada. Cancelar es cancelar — no «igual te lo
//     dejo en Descargas».
//   · El archivo se pide con `fetch` (misma origen → viaja la sesión) y se escribe tal cual llega:
//     ni un byte se toca.
//   · Ningún diálogo nativo (alert/confirm): los errores se avisan por `avisar`, que es el aviso
//     de la app (regla del proyecto).

const TIPOS = {
  pdf: { description: 'PDF', accept: { 'application/pdf': ['.pdf'] } },
  ai: { description: 'Illustrator', accept: { 'application/postscript': ['.ai'] } },
  csv: { description: 'CSV', accept: { 'text/csv': ['.csv'] } },
}

function tipoDe(nombre) {
  const ext = String(nombre || '').toLowerCase().split('.').pop()
  return TIPOS[ext] ? [TIPOS[ext]] : undefined
}

/** ¿Este navegador puede abrir el «Guardar como» nativo desde la página? */
export function puedeElegirDonde() {
  return typeof window !== 'undefined' && window.isSecureContext && typeof window.showSaveFilePicker === 'function'
}

/** ¿Y elegir una carpeta para guardar varios archivos de una? */
export function puedeElegirCarpeta() {
  return typeof window !== 'undefined' && window.isSecureContext && typeof window.showDirectoryPicker === 'function'
}

function esCancelacion(e) {
  return e && (e.name === 'AbortError' || e.code === 20)
}

/** Descarga de siempre: un `<a download>` efímero. Es el respaldo cuando no hay API. */
function descargaClasica(url, nombre) {
  const a = document.createElement('a')
  a.href = url
  a.download = nombre
  document.body.appendChild(a)
  a.click()
  a.remove()
}

async function traer(url) {
  const r = await fetch(url)
  if (!r.ok) {
    let detalle = ''
    try { detalle = (await r.json()).error || '' } catch { /* no era JSON */ }
    throw new Error(detalle || `no se pudo descargar (${r.status})`)
  }
  return await r.blob()
}

async function escribir(handle, blob) {
  const w = await handle.createWritable()
  try {
    await w.write(blob)
  } finally {
    await w.close()
  }
}

/**
 * Descarga UN archivo de la app abriendo el «Guardar como».
 * `url` = ruta de la app (ya con prefijo, ver base.js) o un `blob:`; `nombre` = nombre sugerido.
 * Devuelve true si se guardó, false si se canceló o se cayó al respaldo.
 */
export async function descargarArchivo(url, nombre, { avisar } = {}) {
  if (!puedeElegirDonde()) {
    descargaClasica(url, nombre)
    return false
  }
  let handle
  try {
    // el diálogo se abre PRIMERO, dentro del gesto del usuario: si se pidiera el archivo antes, el
    // navegador podría rechazar el diálogo por «no viene de un click»
    handle = await window.showSaveFilePicker({ suggestedName: nombre, types: tipoDe(nombre) })
  } catch (e) {
    if (esCancelacion(e)) return false           // canceló: no se guarda nada, en ningún lado
    descargaClasica(url, nombre)                 // la API existe pero falló: respaldo
    return false
  }
  try {
    const blob = url.startsWith('blob:') ? await (await fetch(url)).blob() : await traer(url)
    await escribir(handle, blob)
    return true
  } catch (e) {
    if (avisar) avisar(`No se pudo guardar «${nombre}»: ${e.message || e}`)
    return false
  }
}

/** Lo mismo, para un Blob ya armado en memoria (el CSV de la planilla, la guía .ai). */
export async function descargarBlob(blob, nombre, opciones) {
  const url = URL.createObjectURL(blob)
  try {
    return await descargarArchivo(url, nombre, opciones)
  } finally {
    // el <a download> del respaldo ya disparó la descarga; el objeto puede soltarse
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
}

/**
 * Descarga VARIOS archivos eligiendo UNA carpeta: `items` = [{url, nombre}]. Si el navegador no
 * puede elegir carpeta, cae a la descarga clásica de a uno (con una pausa, como siempre). Devuelve
 * cuántos se guardaron; -1 si el usuario canceló la carpeta.
 */
export async function descargarVarios(items, { avisar, progreso } = {}) {
  if (!items || !items.length) return 0
  if (!puedeElegirCarpeta()) {
    for (const it of items) {
      descargaClasica(it.url, it.nombre)
      await new Promise((r) => setTimeout(r, 500))
    }
    return items.length
  }
  let carpeta
  try {
    carpeta = await window.showDirectoryPicker({ mode: 'readwrite' })
  } catch (e) {
    if (esCancelacion(e)) return -1
    for (const it of items) {
      descargaClasica(it.url, it.nombre)
      await new Promise((r) => setTimeout(r, 500))
    }
    return items.length
  }
  let hechos = 0
  const fallas = []
  for (let i = 0; i < items.length; i++) {
    const it = items[i]
    try {
      if (progreso) progreso(i + 1, items.length, it.nombre)
      const blob = await traer(it.url)
      const fh = await carpeta.getFileHandle(it.nombre, { create: true })
      await escribir(fh, blob)
      hechos++
    } catch (e) {
      fallas.push(`${it.nombre}: ${e.message || e}`)
    }
  }
  if (fallas.length && avisar) avisar(`No se pudieron guardar ${fallas.length}: ${fallas.slice(0, 3).join(' · ')}`)
  return hechos
}
