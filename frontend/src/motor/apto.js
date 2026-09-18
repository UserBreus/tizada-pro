// ¿ESTA COMPUTADORA ESTÁ APTA? — el veredicto que la persona ve SIN tener que hacer nada.
//
// Pedido del usuario (2026-09-18): «que el usuario pueda ver si su PC está apta para usar el
// sistema correcto y rápido, sin necesidad de hacer un proceso». Se mide una vez por sesión, al
// entrar (menos de un segundo): núcleos, memoria que declara el navegador, WebAssembly e hilos, y
// el benchmark corto de `capacidad.js` («puntos de potencia»). De ahí sale:
//   · `apta`   — molde con diseño en pocos segundos y tizadas sin problema;
//   · `justa`  — funciona, pero los moldes grandes van a tardar más o pueden quedarse sin memoria;
//   · `no`     — no puede: navegador viejo, sin hilos, demasiado lenta o casi sin memoria.
// y «hasta qué molde» puede preparar con la memoria que tiene (la regla medida: ~3,5 MB de
// WebAssembly por MB de archivo, por hilo — ver `memoriaParaMolde`).
import { equipo, puntosDePotencia, UMBRAL_PUNTOS } from './capacidad.js'

let _cache = null

/** El veredicto (se calcula una vez y se guarda en la sesión). `forzar` lo vuelve a medir. */
export function evaluarEquipo(forzar = false) {
  if (_cache && !forzar) return _cache
  if (!forzar) {
    try {
      const g = sessionStorage.getItem('tizada_apto')
      if (g) { _cache = JSON.parse(g); return _cache }
    } catch { /* sin storage */ }
  }
  const eq = equipo()
  const hilos = Math.max(2, Math.min((eq.nucleos || 4) - 1, 8))
  let puntos
  try { puntos = (eq.wasm && eq.hilos) ? puntosDePotencia(500) : 0 } catch { puntos = 0 }
  // hasta qué tamaño de molde (MB) se puede preparar con la memoria declarada: el navegador deja
  // usar más o menos el 60 % de la memoria total, y cada hilo abre el molde entero
  const memMb = eq.memoriaGb ? eq.memoriaGb * 1024 : null
  const moldeMaxMb = memMb ? Math.max(0, Math.floor((memMb * 0.6 / hilos - 120) / 3.5)) : null
  let nivel, motivo
  if (!eq.wasm || !eq.hilos) {
    nivel = 'no'; motivo = 'Este navegador no puede preparar moldes ni tizadas. Usá Chrome, Edge o Firefox actualizados.'
  } else if (puntos < UMBRAL_PUNTOS || (eq.memoriaGb && eq.memoriaGb < 2)) {
    nivel = 'no'; motivo = puntos < UMBRAL_PUNTOS
      ? `Esta computadora es demasiado lenta (${puntos} puntos de potencia; hacen falta ${UMBRAL_PUNTOS}): un molde con diseño tardaría más de un minuto.`
      : `Esta computadora tiene muy poca memoria (${eq.memoriaGb} GB): no va a poder preparar moldes.`
  } else if (puntos < UMBRAL_PUNTOS * 2 || (eq.memoriaGb && eq.memoriaGb < 8) || (eq.nucleos && eq.nucleos < 4)) {
    nivel = 'justa'; motivo = `Funciona, pero los moldes grandes van a tardar más${moldeMaxMb ? ` (hasta ~${moldeMaxMb} MB por molde)` : ''}. Cerrá otras pestañas y programas mientras trabajás.`
  } else {
    nivel = 'apta'; motivo = `Esta computadora prepara moldes y tizadas en pocos segundos${moldeMaxMb ? ` (moldes de hasta ~${moldeMaxMb} MB)` : ''}.`
  }
  _cache = { nivel, motivo, puntos, hilos, moldeMaxMb, nucleos: eq.nucleos, memoriaGb: eq.memoriaGb, navegador: eq.navegador, medido: Date.now() }
  try { sessionStorage.setItem('tizada_apto', JSON.stringify(_cache)) } catch { /* sin storage */ }
  return _cache
}
