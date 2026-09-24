// LOS CÁLCULOS QUE PIDE EL SERVIDOR, HECHOS EN ESTA COMPUTADORA — 2026-09-22.
//
// 🔴 POR QUÉ: «el servidor será sólo para sostener el sistema y la base; el resto lo debe hacer la
// PC del usuario». Las herramientas del molde (nombrar, emparejar talles, agrupar, variantes, el
// nido, la guía, agregar una pieza) tienen su lógica en el servidor —qué guardar, qué migrar— y
// unos pocos cálculos pesados sobre el ARCHIVO. Cuando una ruta necesita uno, contesta 428
// `{calcular: {clave, fn, args}}` (ver `servidor._calcular`); acá se hace con el mismo motor que
// prepara el molde al subirlo (`obrero.worker.js` → `molde_calculo` / `molde_editar`), se le deja
// el resultado al servidor (`/api/calculos`) y la MISMA petición se vuelve a mandar. Ninguna
// pantalla tiene que saberlo: se engancha una sola vez sobre `fetch` (`instalarCalculos`).
import { crearPool } from './pool.js'
import { traerConCache, claveDe, urlDe } from './cache.js'
import { registrarHilo } from './monitor.js'

// operaciones que REESCRIBEN el molde: devuelven el archivo nuevo además del resultado
const EDITAN = new Set(['agregar_pieza', 'renombrar_y_alta', 'separar_y_alta'])
const TOPE_ABIERTOS = 3

let _pool = null
const abiertos = []                 // claves de moldes abiertos en el hilo, del más viejo al más nuevo
const enCurso = new Map()           // clave del cálculo → promesa (dos pedidos iguales esperan al primero)
let _fetch = null

function pool() {
  if (!_pool) {
    _pool = crearPool(1, () => {
      const w = new Worker(new URL('./obrero.worker.js', import.meta.url), { type: 'module' })
      registrarHilo(w, 'molde')
      return w
    })
  }
  return _pool
}

async function bytesPlantilla(args, rutaApi) {
  // la MISMA clave que el motor y la descarga de fondo (`bajarMoldes.js`): el molde que ya está
  // guardado en esta PC no se vuelve a bajar para un cálculo
  const cual = args.archivo !== 'original' ? 'vigente' : 'original'
  return traerConCache(claveDe.plantilla(args.molde, args.sello, cual), rutaApi(urlDe.plantilla(args.molde, cual)))
}

async function abrirMolde(args, rutaApi) {
  const clave = `calc|${args.archivo}|${args.molde}|${(args.sello || []).join(',')}`
  if (abiertos.includes(clave)) return clave
  if (abiertos.length >= TOPE_ABIERTOS) {
    // se suelta todo lo abierto en el hilo (un molde pesa cientos de MB)
    try { await pool().enviar('cerrar_a', {}) } catch { /* nada */ }
    abiertos.length = 0
  }
  const b = (await bytesPlantilla(args, rutaApi)).slice()
  await pool().enviar('molde_a_abrir', { clave, bytes: b }, [b.buffer])
  abiertos.push(clave)
  return clave
}

async function dejar(rutaApi, clave, resultadoJson, archivo = null) {
  let r
  if (archivo) {
    const fd = new FormData()
    fd.append('clave', clave)
    fd.append('resultado_json', resultadoJson)
    fd.append('archivo', new Blob([archivo], { type: 'application/pdf' }), 'molde.pdf')
    r = await _fetch(rutaApi('/api/calculos'), { method: 'POST', body: fd })
  } else {
    r = await _fetch(rutaApi('/api/calculos'), {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ calculos: [{ clave, resultado_json: resultadoJson }] }),
    })
  }
  if (!r.ok) {
    let d = {}
    try { d = await r.json() } catch { /* nada */ }
    throw new Error(d.error || 'no se pudo entregar el cálculo al servidor')
  }
}

/**
 * Hace el cálculo `{clave, fn, args}` que pidió el servidor → `{txt, archivo}` (el resultado en
 * JSON y, en las operaciones que reescriben el molde, el archivo nuevo). No se lo deja a nadie.
 */
async function hacer(pedido, rutaApi) {
  const { fn, args = {} } = pedido
  if (fn === 'visor_todos_b') {
    // el visor de un molde con el diseño adentro cargado antes de que el alta lo dejara hecho:
    // las piezas de todas las mesas (la fase A del alta, en varios hilos) → su visor
    const { abrirEnPool, faseA } = await import('./molde/desplegar_paralelo.js')
    const { hilosRecomendados } = await import('./prepararMolde.js')
    const { aTextoJSON } = await import('./molde/caminoA.js')
    const b = (await bytesPlantilla(args, rutaApi)).slice()
    const p2 = crearPool(hilosRecomendados(), () => new Worker(new URL('./obrero.worker.js', import.meta.url), { type: 'module' }), 'visor molde con diseño')
    try {
      const info = await abrirEnPool(p2, b)
      const A = await faseA(p2, info)
      return { txt: aTextoJSON(A.alta.visor || {}), archivo: null }
    } finally { p2.cerrar() }
  }
  if (args.arte) {
    // un cálculo sobre el ARTE de un diseño (su archivo vigente, identificado por su sello)
    // misma clave que el motor (`arte|…`): antes era `arte-calc|…` y el arte se bajaba dos veces
    const b = (await traerConCache(claveDe.arte(args.molde, args.arte, args.sello),
      rutaApi(urlDe.arte(args.molde, args.arte)))).slice()
    return { txt: await pool().enviar('arte_calculo', { bytes: b, fn, args }, [b.buffer]), archivo: null }
  }
  if (EDITAN.has(fn)) {
    const b = (await bytesPlantilla(args, rutaApi)).slice()
    const r = await pool().enviar('molde_editar', { bytes: b, fn, args }, [b.buffer])
    return { txt: r.resultado_json, archivo: r.bytes || null }
  }
  const k = await abrirMolde(args, rutaApi)
  return { txt: await pool().enviar('molde_calculo', { clave: k, fn, args }), archivo: null }
}

/** Hace el cálculo `{clave, fn, args}` que pidió el servidor y le deja el resultado. */
export async function resolverCalculo(pedido, rutaApi = (x) => x) {
  const { clave, fn } = pedido || {}
  if (!clave || !fn) throw new Error('pedido de cálculo inválido')
  if (enCurso.has(clave)) return enCurso.get(clave)
  const p = (async () => {
    const { txt, archivo } = await hacer(pedido, rutaApi)
    await dejar(rutaApi, clave, txt, archivo)
  })()
  enCurso.set(clave, p)
  try { return await p } finally { enCurso.delete(clave) }
}

// La MISMA petición con los resultados ADENTRO (`_calculos` en el cuerpo, que `servidor._calcular`
// lee antes que nada). Un GET pasa a POST sólo si la ruta lo pidió (`reenviar: 'post'`); un POST
// con cuerpo JSON los suma a su cuerpo. `null` si no se puede (otro tipo de cuerpo).
function conCalculos(input, init, reenviar, calculos) {
  if (typeof input !== 'string' && !(input instanceof URL)) return null
  const metodo = String((init && init.method) || 'GET').toUpperCase()
  const headers = new Headers((init && init.headers) || {})
  headers.set('Content-Type', 'application/json')
  if (metodo === 'GET') {
    if (reenviar !== 'post') return null
    return { ...(init || {}), method: 'POST', headers, body: JSON.stringify({ _calculos: calculos }) }
  }
  if (!init || typeof init.body !== 'string') return null
  let cuerpo
  try { cuerpo = JSON.parse(init.body) } catch { return null }
  if (!cuerpo || typeof cuerpo !== 'object' || Array.isArray(cuerpo)) return null
  return { ...init, headers, body: JSON.stringify({ ...cuerpo, _calculos: calculos }) }
}

/**
 * Engancha `fetch`: una respuesta 428 con `{calcular}` se resuelve acá y la petición se repite.
 * Si trae `calculos` (una lista: la ruta juntó TODOS los que le faltan), se hacen todos y viajan
 * DENTRO de la petición repetida (no quedan en la memoria del servidor, que tiene tope).
 *
 * 🔴 SIN TOPE DE VUELTAS (2026-09-23): había uno de 25 y la guía de un molde con muchos talles lo
 * pasaba («el servidor pidió demasiados cálculos seguidos»). Lo que corta ahora es que NO AVANCE:
 * el mismo cálculo pedido otra vez después de entregado (3 veces) es un bucle, no trabajo.
 */
export function instalarCalculos(rutaApi = (x) => x) {
  if (typeof window === 'undefined' || _fetch) return
  _fetch = window.fetch.bind(window)
  window.fetch = async (input, init) => {
    const veces = new Map()            // clave → cuántas veces la pidió el servidor
    const adentro = new Map()          // clave → {clave, resultado_json} que viajan en la petición
    let init2 = init
    for (;;) {
      const r = await _fetch(input, init2)
      if (r.status !== 428) return r
      let d = null
      try { d = await r.clone().json() } catch { d = null }
      if (!d || !d.calcular) return r
      const lista = Array.isArray(d.calculos) && d.calculos.length ? d.calculos : [d.calcular]
      for (const pd of lista) {
        const n = (veces.get(pd.clave) || 0) + 1
        veces.set(pd.clave, n)
        if (n > 3) throw new Error(`el cálculo «${pd.fn}» no avanza (el servidor lo vuelve a pedir)`)
      }
      if (lista.length > 1 && conCalculos(input, init, d.reenviar, []) !== null) {
        // de a uno (el hilo del molde es uno solo), y todos los resultados adentro de la petición
        for (const pd of lista) {
          if (adentro.has(pd.clave)) continue
          const { txt } = await hacer(pd, rutaApi)
          adentro.set(pd.clave, { clave: pd.clave, resultado_json: txt })
        }
        init2 = conCalculos(input, init, d.reenviar, [...adentro.values()])
      } else {
        for (const pd of lista) await resolverCalculo(pd, rutaApi)
      }
    }
  }
}
