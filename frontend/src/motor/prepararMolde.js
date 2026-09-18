// PREPARAR EL MOLDE EN LA COMPUTADORA DE LA PERSONA, EN DOS TIEMPOS (PLAN_NAVEGADOR.md, etapa 1).
//
// La pantalla llama a esto antes de subir un molde con diseño. El trabajo lo hace un equipo de
// hilos del navegador (`pool.js` + `obrero.worker.js`) y sale en dos paquetes:
//   · FASE A (unos segundos): piezas, registro y visor. Se sube con el archivo y la persona sigue.
//   · FASE B (en segundo plano): la etiqueta que trae el diseño y las páginas por talle. Se sube
//     sola por `/api/plantilla/paginas` cuando termina.
// El servidor no calcula nada: valida y guarda (`servidor._paquete_molde_aplicar`).
//
// El molde SIN diseño adentro (camino A) y el DXF también se preparan acá (PLAN_NAVEGADOR 1b): un
// DXF se convierte primero a PDF (`dxf/importar.js`) y después se da de alta como un .ai; el alta
// (registro, detección por talle, lienzo de todas) viaja en UN paquete (`alta_a`) con el archivo.
// Para esos no hay fase B: `paginas` es `null` y `caminoA` es `true`.

import { crearPool } from './pool.js'
import { abrirEnPool, faseA, faseB, pareceConDiseno } from './molde/desplegar_paralelo.js'
import { puedeHacer } from './capacidad.js'

let _config = null
const MOTOR = 'mupdf.js · navegador'

/** ¿El servidor quiere que el navegador prepare los moldes? (`/api/navegador/config`) */
export async function navegadorPreparaMoldes() {
  if (_config === null) {
    try {
      const r = await fetch('/api/navegador/config')
      _config = r.ok ? await r.json() : { molde: false }
    } catch {
      _config = { molde: false }
    }
  }
  return !!_config.molde
}

/**
 * Cuántos hilos usar. Cada uno abre el molde entero (un molde de 117 MB pesa ~400 MB por hilo), así
 * que manda lo que tenga la computadora: los núcleos (menos uno, para que la pantalla siga fluida)
 * y la memoria que informa el navegador (Chrome y Edge la dicen, con tope 8 GB; Firefox no: se
 * asume 8 y, si igual no alcanza, el hilo que se queda sin memoria corta con un aviso claro).
 */
export function hilosRecomendados() {
  const nucleos = (typeof navigator !== 'undefined' && navigator.hardwareConcurrency) || 4
  const memoriaGb = (typeof navigator !== 'undefined' && navigator.deviceMemory) || 8
  return Math.max(2, Math.min(nucleos - 1, Math.floor(memoriaGb), 8))
}

function mensajeDeError(e) {
  const msg = String((e && e.message) || e)
  if (/memory|out of bounds|allocation|Array buffer|OOM|RangeError/i.test(msg)) {
    return 'Esta computadora no tiene memoria suficiente para preparar este molde. Cerrá otras pestañas o programas y volvé a intentarlo, o usá una computadora con más memoria.'
  }
  if (/Worker/i.test(msg) && /not|no /i.test(msg)) {
    return 'Este navegador no puede preparar moldes. Usá Chrome, Edge o Firefox actualizados.'
  }
  return `No se pudo preparar el molde en tu computadora: ${msg}`
}

const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('')

/**
 * `archivo` = el File elegido. `onA({texto})` y `onB({texto, hecho, total})` reciben el avance.
 * Devuelve (cuando termina la FASE A) `{zipA, sha1, resumen, paginas: Promise<zipB>, cancelar()}`.
 * Tira un Error con un mensaje para la pantalla si esta computadora no puede.
 *
 * `soloSiTraeDiseno`: las pantallas que aceptan CUALQUIER molde (Mis artículos, Configuración →
 * Moldería) no saben de antemano si el archivo trae el diseño adentro. Con esto se mira primero
 * (dos mesas, igual que el servidor) y, si es un molde pelado (camino A), se prepara COMO CAMINO A
 * acá mismo (`{caminoA: true, paginas: null}`). Un `.dxf` va siempre por el camino A (se convierte
 * primero). Así NINGUNA vía de subida deja un molde para que lo lea el servidor.
 *
 * Con `caminoA`, `archivo` es el archivo a SUBIR (para un DXF: el PDF ya convertido, con el DXF
 * original adentro del paquete) y `resumen.dxf` el resumen de la conversión.
 */
export async function prepararEnDosTiempos(archivo, { onA = null, onB = null, soloSiTraeDiseno = false } = {}) {
  let pool = null
  let cerrado = false
  const cerrar = () => { if (!cerrado && pool) { cerrado = true; pool.cerrar() } }
  try {
    // LA PUERTA (etapa 5): si esta computadora no tiene la memoria o la potencia, se dice y NO se
    // manda al servidor (regla del usuario: «quien no tenga la potencia no podrá enviar»).
    const puerta = puedeHacer({ tipo: 'molde', mb: archivo.size / 1048576, hilos: hilosRecomendados() })
    if (!puerta.puede) { const e = new Error(puerta.motivo); e.capacidad = true; throw e }
    onA && onA({ texto: 'Abriendo el archivo en tu computadora…' })
    let bytes = new Uint8Array(await archivo.arrayBuffer())
    const esDxf = /\.dxf$/i.test(archivo.name || '')
    let dxf = null, dxfBytes = null, archivoSubir = archivo
    if (esDxf) {
      // el DXF se convierte a PDF en UN hilo; el PDF resultante es lo que se sube (con el DXF adentro)
      onA && onA({ texto: 'Convirtiendo el DXF en tu computadora…' })
      const uno = crearPool(1, () => new Worker(new URL('./obrero.worker.js', import.meta.url), { type: 'module' }))
      try {
        const r = await uno.enviar('dxf_convertir', { bytes: bytes.slice() })
        dxf = r.resumen
        dxfBytes = bytes
        bytes = new Uint8Array(r.pdf)
        archivoSubir = new File([bytes], (archivo.name || 'molde').replace(/\.dxf$/i, '') + '.pdf', { type: 'application/pdf' })
      } finally {
        uno.cerrar()
      }
    }
    const sha1 = hex(await crypto.subtle.digest('SHA-1', bytes))
    const caminoA = esDxf || soloSiTraeDiseno
    // el camino A lee el molde en UN hilo (el alta es secuencial); el B abre el archivo en todos
    pool = crearPool(caminoA && esDxf ? 1 : hilosRecomendados(), () => new Worker(new URL('./obrero.worker.js', import.meta.url), { type: 'module' }))
    const info = await abrirEnPool(pool, bytes)
    if (caminoA) {
      let esA = esDxf
      if (!esA) {
        onA && onA({ texto: 'Mirando si trae el diseño adentro…' })
        esA = !(await pareceConDiseno(pool)).si
      }
      if (esA) {
        onA && onA({ texto: 'Detectando las piezas y los talles…' })
        const indices = dxf && dxf.indices ? dxf.indices : null
        const dxfMan = dxf ? { ...dxf } : null
        if (dxfMan) delete dxfMan.indices
        const r = await pool.enviar('alta_a', { sha1, motor: MOTOR, dxf: dxfMan ? { ...dxfMan, indices } : null, dxfBytes, indices },
          dxfBytes ? [dxfBytes.buffer] : [])
        cerrar()
        return { zipA: r.zip, sha1, paginas: null, caminoA: true, cancelar: () => {}, archivo: archivoSubir,
                 resumen: { ...r.resumen, dxf: r.resumen.dxf || dxf } }
      }
    }
    const A = await faseA(pool, info, {
      avisar: (_etapa, hecho, total) => onA && onA({ texto: `Detectando las piezas · mesa ${hecho} de ${total}` }),
    })
    onA && onA({ texto: 'Listo para guardar…' })
    const pA = await pool.enviar('paquete', { archivo: null, desplegado: A, fase: 'contornos', sha1, motor: MOTOR })
    const paginas = (async () => {
      try {
        const B = await faseB(pool, A, { avisar: (_e, hecho, total, texto) => onB && onB({ texto, hecho, total }) })
        onB && onB({ texto: 'Armando el paquete de las páginas…', hecho: 1, total: 1 })
        const pdfs = [...B.mesas.values()].map((x) => x.pdf.buffer)
        const pB = await pool.enviar('paquete', { archivo: null, desplegado: B, fase: 'paginas', sha1, motor: MOTOR }, pdfs)
        return pB.zip
      } catch (e) {
        throw new Error(cerrado ? 'Cancelado' : mensajeDeError(e))
      } finally {
        cerrar()
      }
    })()
    paginas.catch(() => {})            // el que llama se engancha después: que no quede «sin atender»
    return {
      zipA: pA.zip, sha1, paginas, cancelar: cerrar,
      resumen: { mesas: A.alta.mesas, talles: A.alta.talles, piezas: A.alta.registro.size },
    }
  } catch (e) {
    cerrar()
    if (e && e.capacidad) throw e
    throw new Error(mensajeDeError(e))
  }
}

/** Sube la FASE B. `onPct(0..100)`. Devuelve la respuesta del servidor o tira el error. */
export function subirPaginas(rutaApi, pid, zipB, onPct = null) {
  return new Promise((resolve, reject) => {
    const fd = new FormData()
    fd.append('pid', pid)
    fd.append('paquete', new Blob([zipB], { type: 'application/zip' }), 'paginas.zip')
    const xhr = new XMLHttpRequest()
    xhr.open('POST', rutaApi('/api/plantilla/paginas'))
    xhr.upload.onprogress = (e) => { if (e.lengthComputable && onPct) onPct(Math.round(e.loaded * 100 / e.total)) }
    xhr.onload = () => {
      let j = {}
      try { j = JSON.parse(xhr.responseText || '{}') } catch { /* nada */ }
      xhr.status >= 200 && xhr.status < 300 ? resolve(j) : reject(new Error(j.error || 'No se pudieron guardar las páginas del molde'))
    }
    xhr.onerror = () => reject(new Error('Se cortó la conexión con el servidor al guardar las páginas'))
    xhr.send(fd)
  })
}
