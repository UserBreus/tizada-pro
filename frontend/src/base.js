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

// 🔴 EL MOLDE ACTIVO ES DE CADA PESTAÑA (MAPA 819). Dos pestañas del mismo navegador comparten la sesión del
// servidor: lo que activaba una le cambiaba el molde a la otra, que pedía la configuración del molde ajeno y lo
// volvía a activar (8 `activar` seguidos, «Molde activado ✓» en una pestaña quieta). Cada pestaña recuerda el
// suyo (sessionStorage = de la pestaña, sobrevive al F5) y lo manda en cada pedido a la API (`X-Tizada-Molde`);
// el servidor avisa cuando un pedido de ESTA pestaña activó otro (`X-Tizada-Molde-Activado`).
const CLAVE_MOLDE = 'tizada_molde_pestana'
let moldePestana = null
try { moldePestana = sessionStorage.getItem(CLAVE_MOLDE) || null } catch { /* sin sessionStorage: sólo en memoria */ }
/** El molde activo de ESTA pestaña (null = todavía ninguno: manda el de la sesión). */
export function moldeDePestana() { return moldePestana }
/** Lo que el servidor dice que es el activo de esta pestaña (`/api/productos` → `activo`, o un activar). */
export function ponerMoldeDePestana(pid) {
  moldePestana = pid ? String(pid) : null
  try { if (moldePestana) sessionStorage.setItem(CLAVE_MOLDE, moldePestana); else sessionStorage.removeItem(CLAVE_MOLDE) } catch { /* nada */ }
}
const esPropia = (ruta) => typeof ruta === 'string' && ruta.startsWith('/api/')

// Envoltorio de fetch (idempotente: si ya se instaló, no se vuelve a envolver): el prefijo de la publicación
// (si hay) y el molde de la pestaña.
if (!window.fetch.__tizadaBase) {
  const original = window.fetch.bind(window)
  const conMolde = (opciones) => {
    if (!moldePestana) return opciones
    const h = new Headers((opciones && opciones.headers) || undefined)
    if (!h.has('X-Tizada-Molde')) h.set('X-Tizada-Molde', moldePestana)
    return { ...(opciones || {}), headers: h }
  }
  const leerAviso = (r) => {
    try { const a = r && r.headers && r.headers.get('X-Tizada-Molde-Activado'); if (a) ponerMoldeDePestana(a) } catch { /* nada */ }
    return r
  }
  const envuelto = (entrada, opciones) => {
    if (typeof entrada === 'string') {
      if (!esPropia(entrada)) return original(rutaApi(entrada), opciones)
      return original(rutaApi(entrada), conMolde(opciones)).then(leerAviso)
    }
    if (BASE && entrada instanceof Request && entrada.url.startsWith(window.location.origin)) {
      const ruta = entrada.url.slice(window.location.origin.length)
      const nueva = rutaApi(ruta)
      if (nueva !== ruta) return original(new Request(window.location.origin + nueva, entrada), opciones)
    }
    return original(entrada, opciones)
  }
  envuelto.__tizadaBase = true
  window.fetch = envuelto
}
