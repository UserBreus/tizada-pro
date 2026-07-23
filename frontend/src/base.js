// ── DÓNDE VIVE LA APP ────────────────────────────────────────────────────────────────────────
// En el taller la app cuelga de la raíz del servidor (http://localhost:8050/). Publicada puede
// colgar de una SUB-RUTA del dominio del cliente (https://…/Tizadapro/). Todo el código llama a
// la API con rutas absolutas (`fetch('/api/…')`, 125 lugares): tal cual, desde una sub-ruta esas
// llamadas irían a la RAÍZ del dominio — o sea, al OTRO sistema que vive ahí — y fallarían todas.
//
// En vez de tocar 125 llamadas (y que la próxima que alguien escriba se olvide del prefijo), se
// envuelve `fetch` UNA vez: cualquier ruta de la app (`/api/…`, `/trabajos/…`) sale con el prefijo
// correcto. El prefijo lo pone Vite al compilar (`TIZADA_BASE`, ver vite.config.js).
//
// Este archivo se importa PRIMERO en main.jsx, antes que la app: cuando el primer componente
// haga un fetch, el envoltorio ya tiene que estar puesto.

// "/Tizadapro/" → "/Tizadapro"   ·   "/" → ""   (así se concatena sin barras dobles)
export const BASE = (import.meta.env.BASE_URL || '/').replace(/\/+$/, '')

// Rutas propias de la app que hay que prefijar. El resto (URLs completas, data:, blob:,
// y cualquier cosa de otro dominio) se deja intacta.
const PROPIAS = ['/api/', '/api?', '/trabajos/', '/logo.svg']

/** Ruta absoluta de la app, ya con el prefijo donde esté publicada. */
export function rutaApi(p) {
  const s = String(p || '')
  if (!BASE || !s.startsWith('/')) return s
  return PROPIAS.some(x => s.startsWith(x) || s === x.replace(/[/?]$/, '')) ? BASE + s : s
}

/** ¿La URL del navegador es la pantalla de administración (`…/admin`)? */
export function esRutaAdmin() {
  const p = window.location.pathname.replace(/\/+$/, '')
  return p === BASE + '/admin'
}

// Envoltorio de fetch (idempotente: si ya se instaló, no se vuelve a envolver).
if (BASE && !window.fetch.__tizadaBase) {
  const original = window.fetch.bind(window)
  const envuelto = (entrada, opciones) => {
    if (typeof entrada === 'string') return original(rutaApi(entrada), opciones)
    if (entrada instanceof Request && entrada.url.startsWith(window.location.origin)) {
      const ruta = entrada.url.slice(window.location.origin.length)
      const nueva = rutaApi(ruta)
      if (nueva !== ruta) return original(new Request(window.location.origin + nueva, entrada), opciones)
    }
    return original(entrada, opciones)
  }
  envuelto.__tizadaBase = true
  window.fetch = envuelto
}
