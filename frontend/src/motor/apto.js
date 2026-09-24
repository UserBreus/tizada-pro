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

// ── REQUISITOS: MÍNIMO E IDEAL (pedido del usuario 2026-09-24: «en el pedido, un espacio que diga el
// requisito mínimo para que TIZADA funcione correcto y ágil, el ideal, lo que tiene la PC, si está
// apta o no, con una barra de si está más cerca del mínimo o del ideal, si supera el ideal o está
// por debajo del mínimo, y por cuánto»). El MÍNIMO es el mismo umbral de «apta» de `evaluarEquipo`
// (por debajo, el veredicto es «justa» o «no»: NO APTA — el servidor no hace el trabajo por ella).
// El IDEAL: el doble de núcleos y de memoria, y la potencia de una PC de escritorio actual (la
// de referencia, 12 hilos, da ~100 puntos).
export const REQUISITOS = {
  nucleos: { nombre: 'Núcleos del procesador', corto: 'núcleos', unidad: 'núcleos', minimo: 4, ideal: 8 },
  memoria: { nombre: 'Memoria RAM', corto: 'memoria RAM', unidad: 'GB', minimo: 8, ideal: 16 },
  potencia: { nombre: 'Potencia medida', corto: 'potencia', unidad: 'puntos', minimo: UMBRAL_PUNTOS * 2, ideal: 60 },
}

/**
 * Lo que tiene esta PC contra los requisitos. `v` = `evaluarEquipo()`; `ramExactaGb` = la RAM
 * exacta si se sabe (la da la extensión de Illustrator): el navegador la informa redondeada y con
 * tope en 8 GB, así que sin eso «8» quiere decir «8 o más».
 * → `{items: [{clave, nombre, unidad, tiene, minimo, ideal, pos, estado, texto, tope}], general: {estado, pos, texto}}`
 *   · `pos` 0..1 para la barra: el mínimo en la MITAD, el ideal al final;
 *   · `estado`: 'debajo' (no llega al mínimo) · 'entre' (entre mínimo e ideal) · 'ideal' (llega o pasa).
 */
export function compararRequisitos(v, ramExactaGb = null) {
  const num = (x) => Math.round(x * 10) / 10
  const fmt = (x) => String(num(x)).replace('.', ',')
  const medir = (clave, tiene, tope = false) => {
    const r = REQUISITOS[clave]
    if (tiene == null) return { clave, ...r, tiene: null, pos: 0, estado: 'debajo', texto: 'el navegador no lo informa', tope }
    const pos = tiene < r.minimo ? 0.5 * tiene / r.minimo
      : tiene < r.ideal ? 0.5 + 0.5 * (tiene - r.minimo) / (r.ideal - r.minimo) : 1
    let estado, texto
    if (tiene < r.minimo) { estado = 'debajo'; texto = `le faltan ${fmt(r.minimo - tiene)} ${r.unidad} para el mínimo` }
    else if (tiene < r.ideal) {
      estado = 'entre'
      texto = tope ? `cumple el mínimo · el navegador no deja saber si llega al ideal (${r.ideal} ${r.unidad})`
        : `cumple el mínimo · le faltan ${fmt(r.ideal - tiene)} ${r.unidad} para el ideal`
    } else { estado = 'ideal'; texto = tiene > r.ideal ? `supera el ideal por ${fmt(tiene - r.ideal)} ${r.unidad}` : 'llega justo al ideal' }
    return { clave, ...r, tiene, pos, estado, texto, tope }
  }
  const memTope = !ramExactaGb && v && v.memoriaGb >= 8
  const items = [
    medir('nucleos', v ? v.nucleos : null),
    medir('memoria', ramExactaGb || (v ? v.memoriaGb : null), memTope),
    medir('potencia', v ? v.puntos : null),
  ]
  const navOk = !(v && v.nivel === 'no' && /navegador/i.test(v.motivo || ''))
  const peor = items.reduce((a, b) => (b.pos < a.pos ? b : a))
  let estado, texto
  if (!navOk) { estado = 'debajo'; texto = 'Este navegador no puede: usá Chrome o Edge actualizados.' }
  else if (items.some((i) => i.estado === 'debajo')) {
    estado = 'debajo'
    texto = 'NO APTA: no llega al mínimo en ' + items.filter((i) => i.estado === 'debajo').map((i) => i.corto).join(', ') + '.'
  } else if (items.every((i) => i.estado === 'ideal')) { estado = 'ideal'; texto = 'APTA · llega al ideal: TIZADA anda rápido.' }
  else { estado = 'entre'; texto = 'APTA · cumple el mínimo: TIZADA funciona bien; con el ideal los moldes grandes van más rápido.' }
  return { items, navOk, general: { estado, pos: navOk ? peor.pos : 0, texto } }
}
