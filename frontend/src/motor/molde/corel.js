// LA PLANTILLA ARMADA DIRECTO EN CORELDRAW — 2026-09-30 (MAPA 598, COREL_REFERENCIA.md §7).
//
// Pedido del usuario: «que desde TIZADA PRO podamos crear la base así como lo hace directamente en
// Illustrator». El programa `USER PRO para CorelDRAW` (`extension_corel/`, se instala una vez)
// escucha en esta misma PC (`127.0.0.1:47851`) con el MISMO protocolo que la extensión de Illustrator
// (`/estado`, `/plantilla`) y dibuja en Corel por COM. Nada pasa por el servidor.
//
// 🔴 EL MISMO PLAN QUE ILLUSTRATOR, PASADO A PÁGINAS. `planIllustrator` decide todo (qué mesas, qué
// nombre lleva cada una —el que lee el motor—, las capas, el contorno y el fondo). En Corel cada
// mesa de trabajo es una PÁGINA (y así la lee el motor: mesa = página del PDF), pero con la VISTA DE
// VARIAS PÁGINAS en acomodo libre (Corel 2021+) todas se ven en UN espacio de trabajo, cada una en el
// lugar de su pieza en el molde, como las mesas de Illustrator (`cx`/`cy`). Por eso acá se arma a tamaño
// real y sin tope de lienzo (`sinTope`: una página llega a 45 m) y cada contorno, texto y fondo va a
// la página de SU mesa (el campo `mesa` que marca `planIllustrator`), con las coordenadas corridas a
// la esquina de la página. Lo que en Illustrator va FUERA de las mesas (el título «TALLE S», el
// recuadro de cada talle, el cartel de escala) no tiene lugar en Corel: cada página ya lleva el
// nombre de su mesa («#S Frente»).
import { planIllustrator } from './illustrator.js'

export const PUERTO_COREL = 47851
const BASE = `http://127.0.0.1:${PUERTO_COREL}`

/** La versión del programa que corresponde a ESTE sistema → `{version, instalador}`. Una vez por página. */
let _versionServidor = null
export function versionCorelDelServidor(rutaApi = (x) => x) {
  if (!_versionServidor) {
    _versionServidor = fetch(rutaApi('/api/corel/version')).then((r) => (r.ok ? r.json() : {})).catch(() => ({}))
  }
  return _versionServidor
}

/**
 * ¿Hay un puente de USER PRO para CorelDRAW corriendo en esta PC? → su estado
 * (`{version, corel, corel_abierto, …}`) o `null`. La primera vez Chrome pregunta «permitir» y la
 * pregunta queda esperando al usuario: por eso la espera por defecto es LARGA.
 */
export async function buscarCorel(esperaMs = 60000) {
  const ctl = typeof AbortController !== 'undefined' ? new AbortController() : null
  const t = ctl ? setTimeout(() => ctl.abort(), esperaMs) : null
  try {
    const r = await fetch(`${BASE}/estado`, { signal: ctl ? ctl.signal : undefined, cache: 'no-store' })
    if (!r.ok) return null
    const d = await r.json().catch(() => null)
    return d && d.app === 'TIZADA PRO' && d.programa === 'corel' ? d : null
  } catch {
    return null
  } finally {
    if (t) clearTimeout(t)
  }
}

/** Le pasa el plan al puente. Devuelve `{ok, mesas, archivo, carpeta}` o tira el error que contestó. */
export async function enviarACorel(plan) {
  // sin cabeceras propias: una de más rompe el pedido previo de CORS (misma regla que Illustrator)
  const r = await fetch(`${BASE}/plantilla`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(plan),
  })
  const d = await r.json().catch(() => ({}))
  if (!r.ok || !d.ok) throw new Error(d.error || `CorelDRAW contestó ${r.status}`)
  return d
}

/**
 * El plan para Corel: `planIllustrator` a tamaño real y sin tope de lienzo, repartido en PÁGINAS.
 * Coordenadas de cada página en puntos, origen arriba a la izquierda, «y» hacia abajo (el puente
 * las pasa a las de Corel). → `{plan, avisos, nMesas}`.
 */
export function planCorel(capasData, opts = {}) {
  const { plan: pi, avisos, nMesas } = planIllustrator(capasData, { ...opts, escala: 1, sinTope: true })
  return { plan: corelDesdePlan(pi), avisos, nMesas }
}

/**
 * Un plan de Illustrator (a tamaño real) pasado a PÁGINAS de Corel. Sirve también para el plan
 * UNIDO de un diseño (varias variables en un archivo, `unirPlanes`, MAPA 618): cada mesa es una
 * página y su lugar en el espacio de trabajo es el del plan. Lo que está fuera de toda mesa (los
 * títulos de talle y de variable) no va: en Corel sólo existen las páginas.
 */
export function corelDesdePlan(pi) {
  const paginas = pi.mesas.map((m, i) => {
    const [x0, y0, x1, y1] = m.rect
    const f = (pi.fondos || []).find((x) => x.mesa === i)
    return {
      nombre: m.nombre,
      w: x1 - x0,
      h: y1 - y0,
      // DÓNDE va la página en el espacio de trabajo (su CENTRO, en el mismo lienzo que Illustrator):
      // el puente prende la vista de varias páginas con acomodo libre y la ubica ahí, así todas las
      // mesas se ven juntas y acomodadas como en el molde (pedido del usuario 2026-09-30)
      cx: (x0 + x1) / 2,
      cy: (y0 + y1) / 2,
      fondo: f ? { capa: f.capa, color: f.color } : null,
      caminos: (pi.caminos || []).filter((k) => k.mesa === i).map((k) => ({
        capa: k.capa, ancho: k.ancho, color: k.color, ...(k.punteado ? { punteado: k.punteado } : {}),
        sub: k.sub.map((sp) => ({ c: sp.c, p: sp.p.map((q) => [q[0] - x0, q[1] - y0, q[2] - x0, q[3] - y0, q[4] - x0, q[5] - y0]) })),
      })),
      textos: (pi.textos || []).filter((t) => t.mesa === i).map((t) => ({
        capa: t.capa, t: t.t, x: t.x - x0, y: t.y - y0, tam: t.tam, vector: !!t.vector,
      })),
    }
  })
  const plan = {
    version: 1,
    programa: 'corel',
    titulo: pi.titulo,
    archivo: pi.archivo,
    capas: pi.capas,
    activa: pi.activa,
    paginas,
  }
  return plan
}
