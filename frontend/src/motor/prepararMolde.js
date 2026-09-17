// PREPARAR EL MOLDE EN LA COMPUTADORA DE LA PERSONA (PLAN_NAVEGADOR.md, etapa 1).
//
// La pantalla llama a esto antes de subir un molde con diseño: el navegador lo prepara entero en
// un Worker (`trabajo.worker.js`) y devuelve el paquete que acompaña al archivo en la subida. El
// servidor lo guarda sin recalcular nada (`servidor._paquete_molde_aplicar`).

let _config = null

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
 * `archivo` = el File que eligió la persona. `onAvance({etapa, hecho, total, texto})`.
 * Devuelve `{zip: Uint8Array, sha1, resumen}` o tira un Error con un mensaje para la pantalla.
 * `senal` (AbortSignal, opcional) corta el trabajo.
 */
export function prepararMoldeEnNavegador(archivo, onAvance, senal = null) {
  return new Promise((resolve, reject) => {
    let worker
    try {
      worker = new Worker(new URL('./trabajo.worker.js', import.meta.url), { type: 'module' })
    } catch (e) {
      reject(new Error('Este navegador no puede preparar moldes (le falta soporte de Workers). Usá Chrome, Edge o Firefox actualizados.'))
      return
    }
    const terminar = () => { try { worker.terminate() } catch { /* nada */ } }
    if (senal) senal.addEventListener('abort', () => { terminar(); reject(new Error('Cancelado')) }, { once: true })
    worker.onmessage = (ev) => {
      const d = ev.data || {}
      if (d.avance) { if (onAvance) onAvance(d.avance); return }
      terminar()
      if (d.error) {
        const err = new Error(d.error)
        err.codigo = d.codigo
        reject(err)
        return
      }
      resolve(d.listo)
    }
    worker.onerror = (e) => {
      terminar()
      reject(new Error(`No se pudo preparar el molde en tu computadora: ${e.message || 'el proceso se cortó'}`))
    }
    worker.postMessage({ tipo: 'preparar_molde', archivo })
  })
}
