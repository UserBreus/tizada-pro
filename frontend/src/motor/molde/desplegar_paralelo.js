// EL MOLDE DESPLEGADO CON VARIOS HILOS, EN DOS TIEMPOS (PLAN_NAVEGADOR.md, etapa 1 — velocidad).
//
// Lo mismo que `desplegar.js` (mismo resultado: lo verifica el contrato), repartido en un equipo
// de hilos (`pool.js`) y partido en dos tiempos, porque el usuario lo pidió así: «si un molde con
// diseño demora un minuto o más ya es muchísimo; debe ser muy pocos segundos».
//
//   FASE A — lo que hace falta para SEGUIR: las piezas de cada mesa (una mesa por hilo), el registro
//            y el visor. Con eso se guarda el molde y la persona ya puede nombrar las piezas.
//   FASE B — lo que usa la TIZADA: la etiqueta que trae el diseño y las páginas por talle (un talle
//            por hilo). Corre en segundo plano y se guarda cuando termina.

import { altaDesdeContornos } from './contornos.js'
import { decidirFamilias, familiasOcultas, hashOcultas, juntarTalle, V_ETQ } from './paginas.js'
import { V_CONTORNOS, V_PAGINAS } from './desplegar.js'

/** Abre el molde en todos los hilos. */
export async function abrirEnPool(pool, bytes) {
  const r = await pool.todos('abrir', () => ({ bytes }))
  return r[0]                                   // {mesas, talles}
}

/** FASE A. Devuelve `{talles, n, mesas: Map(mesa → {json}), geos, alta}`. */
export async function faseA(pool, info, { avisar = null } = {}) {
  const { talles } = info
  const n = info.mesas
  const mesas = new Map(), geos = new Map(), porMesa = new Map()
  let hechas = 0
  await Promise.all(Array.from({ length: n }, (_, k) => k + 1).map(async (m) => {
    const r = await pool.enviar('contornos', { mesa: m, talles })
    geos.set(m, r.geo)
    if (talles.length) {
      mesas.set(m, { json: { sello: null, orden: talles.slice(), talles: r.talles, v: V_CONTORNOS, paginas: false, marco: r.marco, U: r.U } })
      if (r.talles.size) porMesa.set(m, r.talles)
    }
    hechas++
    if (avisar) avisar('contornos', hechas, n, `mesa ${hechas} de ${n}`)
  }))
  // el registro necesita las mesas EN ORDEN (los Map se llenaron en el orden en que terminaron)
  const ordenar = (mapa) => new Map([...mapa].sort((a, b) => a[0] - b[0]))
  const pm = ordenar(porMesa)
  return { talles, n, mesas: ordenar(mesas), geos: ordenar(geos), alta: altaDesdeContornos(pm, ordenar(geos), talles, n) }
}

/**
 * FASE B (sobre el resultado de la fase A, que se completa acá mismo). Devuelve
 * `{talles, mesas: Map(mesa → {json, pdf}), etiqueta, alta}` — la forma de `desplegarMolde`.
 */
export async function faseB(pool, A, { avisar = null, manual = {} } = {}) {
  const { talles, n } = A
  if (!talles.length) return { talles, mesas: A.mesas, etiqueta: null, alta: A.alta }
  const total = n * talles.length
  let hechos = 0
  const aviso = (etapa, texto) => { if (avisar) avisar(etapa, hechos, total, texto) }

  // 1) cada mesa leída y cortada por talle (una mesa por hilo), y enseguida los candidatos a
  //    etiqueta de cada talle (un talle por hilo)
  const porMesa = new Map()                    // mesa → {R, porTalle}
  const candidatos = new Array(n)
  await Promise.all(Array.from({ length: n }, (_, k) => k + 1).map(async (m) => {
    const j = A.mesas.get(m).json
    const prep = await pool.enviar('preparar', { mesa: m, talles })
    porMesa.set(m, prep)
    const tareas = talles.map((t, i) => {
      if (!(j.talles.get(t) || []).length) { hechos++; return Promise.resolve([]) }
      return pool.enviar('talle', { bytes: prep.porTalle[i], R: prep.R, marco: j.marco, U: j.U, talle: t,
        contornos: j.talles.get(t), modo: 'candidatos' }).then((r) => {
        hechos++
        aviso('etiquetas', `Buscando la etiqueta del diseño · talle ${hechos} de ${total}`)
        for (const c of r.candidatos) c.mesa = m
        return r.candidatos
      })
    })
    candidatos[m - 1] = (await Promise.all(tareas)).flat()
  }))
  const cands = candidatos.flat()
  const totalPiezas = new Set()
  for (let m = 1; m <= n; m++) for (const lst of A.mesas.get(m).json.talles.values()) lst.forEach((_, i) => totalPiezas.add(`${m}|${i}`))
  const etiqueta = { sello: null, v: V_ETQ, piezas: totalPiezas.size, familias: decidirFamilias(cands, totalPiezas.size, manual), manual }
  const ocultar = familiasOcultas(etiqueta)
  const etq = hashOcultas(ocultar)

  // 2) las páginas: cada talle por su lado, y el PDF de la mesa cuando están todos sus talles
  hechos = 0
  const mesas = new Map()
  await Promise.all(Array.from({ length: n }, (_, k) => k + 1).map(async (m) => {
    const j = A.mesas.get(m).json
    const prep = porMesa.get(m)
    const res = await Promise.all(talles.map((t, i) => pool.enviar('talle', {
      bytes: prep.porTalle[i], R: prep.R, marco: j.marco, U: j.U, talle: t,
      contornos: j.talles.get(t) || [], modo: 'pagina', ocultar,
    }, [prep.porTalle[i].buffer]).then((r) => {
      hechos++
      aviso('paginas', `Separando los talles · ${hechos} de ${total}`)
      return r
    })))
    porMesa.delete(m)
    const placeholders = new Map(), lineas = new Map(), etqArchivo = new Map()
    res.forEach((r, i) => juntarTalle(r, talles[i], placeholders, lineas, etqArchivo))
    const contenidos = res.map((r) => r.contenido)
    const pdf = await pool.enviar('armar', { mesa: m, contenidos }, contenidos.map((c) => c.buffer))
    mesas.set(m, { pdf, json: { sello: null, orden: j.orden, talles: j.talles, paginas: true, v: V_CONTORNOS, vp: V_PAGINAS,
      marco: j.marco, U: j.U, placeholders, linea_corte: lineas, etiqueta_archivo: etqArchivo, etq } })
  }))
  return { talles, mesas: new Map([...mesas].sort((a, b) => a[0] - b[0])), etiqueta, alta: A.alta }
}
