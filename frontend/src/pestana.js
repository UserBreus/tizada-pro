// CADA PESTAÑA, SU PEDIDO (MAPA 762).
//
// 🔴 POR QUÉ: el avance del pedido se guardaba en UNA sola clave del navegador (`tizada_wizard`), la misma para
// todas las pestañas: con dos pestañas abiertas en la misma computadora, la última que guardaba pisaba a la otra y,
// como el arte del pedido vive en la PC por número de pedido (`arte/enPc.js`, MAPA 760), las dos terminaban con el
// mismo pedido y el mismo arte. Ahora cada pestaña tiene su número (`sessionStorage`: sobrevive al F5 y es de esa
// pestaña) y su avance va en `tizada_wizard|<número>`.
//
// Para saber qué pestañas siguen ABIERTAS se usa un candado del navegador (Web Locks) por pestaña: el navegador lo
// suelta solo al cerrarla, recargarla o si se cae — no depende de relojes (una pestaña escondida casi no corre).
//   · F5: mismo número (el candado de la página anterior ya se soltó) → mismo pedido.
//   · «Duplicar pestaña» copia el sessionStorage: el candado de la original sigue tomado → número nuevo, pedido vacío
//     (NO adopta ningún pedido de otra pestaña cerrada: lo vio el inspector, MAPA 764).
//   · Pestaña nueva (o volver a abrir el navegador): se queda con el ÚLTIMO pedido guardado que no esté abierto en
//     otra pestaña; si todos están abiertos, empieza uno vacío. Se adopta de a una pestaña por vez.
//   · El avance de una pestaña cerrada hace más de 7 días se olvida (si no, sus artes quedaban en la PC para siempre).
// Sin candados (navegador viejo o página sin https): cada pestaña nueva arranca vacía salvo el pedido guardado con
// la clave de antes; el F5 sigue igual.
const CLAVE = 'tizada_wizard'
const SES = 'tizada_pestana'
const candado = (id) => `tizada_pestana|${id}`
const nuevoId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
let _id = null

const leer = (k) => { try { return JSON.parse(localStorage.getItem(k)) } catch { return null } }

/** El número de esta pestaña y lo que hay que hacer para que el avance guardado sea el suyo. Se llama UNA vez,
 *  antes de dibujar la app (`main.jsx`). */
export async function prepararPestana() {
  const locks = typeof navigator !== 'undefined' && navigator.locks
  let id = null
  try { id = sessionStorage.getItem(SES) } catch { id = null }
  let tomados = new Set()
  if (locks) {
    try { tomados = new Set(((await locks.query()).held || []).map((l) => l.name)) } catch { tomados = new Set() }
  }
  let duplicada = false
  if (id && locks && tomados.has(candado(id))) {
    // ¿es el F5 (la página anterior todavía soltando) o una pestaña duplicada? Se espera un poco a que se suelte.
    let libre = false
    for (let i = 0; i < 8 && !libre; i++) {
      await new Promise((r) => setTimeout(r, 150))
      try { libre = !((await locks.query()).held || []).some((l) => l.name === candado(id)) } catch { libre = true }
    }
    if (!libre) { id = null; duplicada = true }    // la otra pestaña sigue abierta: ésta es una copia → pedido VACÍO
  }
  if (!id) {
    id = nuevoId()
    // pestaña NUEVA (no duplicada): el último pedido guardado que no esté abierto en otra pestaña (o el de la clave
    // de antes). De a UNA pestaña por vez (candado `tizada_adoptar`): dos pestañas abiertas juntas no se quedan con
    // el mismo pedido.
    const adoptar = async () => {
      let vivos = tomados
      if (locks) { try { vivos = new Set(((await locks.query()).held || []).map((l) => l.name)) } catch { /* los de antes */ } }
      const huerfanos = []
      try {
        for (const k of Object.keys(localStorage)) {
          if (k !== CLAVE && !k.startsWith(CLAVE + '|')) continue
          const dueno = k === CLAVE ? null : k.slice(CLAVE.length + 1)
          if (dueno && (!locks || vivos.has(candado(dueno)))) continue   // abierto en otra pestaña (o no se puede saber)
          const w = leer(k)
          if (w) huerfanos.push({ k, w })
        }
        huerfanos.sort((a, b) => (b.w.guardado || 0) - (a.w.guardado || 0))
        if (!duplicada && huerfanos.length) {
          localStorage.setItem(`${CLAVE}|${id}`, JSON.stringify(huerfanos[0].w))
          localStorage.removeItem(huerfanos[0].k)
          huerfanos.shift()
        }
        // los avances de pestañas cerradas hace más de una semana se olvidan (si no, sus artes quedaban para siempre)
        const viejo = Date.now() - 7 * 24 * 3600 * 1000
        for (const h of huerfanos) if ((h.w.guardado || 0) < viejo) localStorage.removeItem(h.k)
      } catch { /* sin storage: arranca vacío */ }
    }
    if (locks) { try { await locks.request('tizada_adoptar', adoptar) } catch { await adoptar() } } else await adoptar()
  }
  try { sessionStorage.setItem(SES, id) } catch { /* sin storage: el F5 empieza de cero */ }
  // el candado queda tomado mientras la pestaña viva (la promesa no termina nunca)
  if (locks) { try { locks.request(candado(id), () => new Promise(() => {})) } catch { /* sin candado */ } }
  _id = id
}

/** La clave donde ESTA pestaña guarda su pedido. */
export const claveWizard = () => (_id ? `${CLAVE}|${_id}` : CLAVE)

/** Las tizadas (`jobId`) que tienen anotadas las OTRAS pestañas: «Nuevo pedido» acá no se las puede llevar (MAPA 787). */
export function tizadasDeOtrasPestanas() {
  const out = new Set()
  try {
    const mia = claveWizard()
    for (const k of Object.keys(localStorage)) {
      if (k === mia || (k !== CLAVE && !k.startsWith(CLAVE + '|'))) continue
      const w = leer(k)
      for (const t of (w && w.trabajosMulti) || []) if (t && t.jobId) out.add(String(t.jobId))
    }
  } catch { /* sin storage */ }
  return out
}

/** Los números de pedido (`pedidoPc`) guardados por TODAS las pestañas: sus artes no se pueden borrar. */
export function pedidosGuardados() {
  const out = new Set()
  try {
    for (const k of Object.keys(localStorage)) {
      if (k !== CLAVE && !k.startsWith(CLAVE + '|')) continue
      const w = leer(k)
      if (w && w.pedidoPc) out.add(w.pedidoPc)
    }
  } catch { /* sin storage */ }
  return out
}
