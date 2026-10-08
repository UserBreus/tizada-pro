// «CREAR PLANTILLA» DE LOS DISEÑOS DE UN PEDIDO — el cálculo, sin pantalla (MAPA 617-619).
//
// Lo usan DOS lados con las mismas cuentas:
//   · la ventana «Crear plantilla» del paso Arte (`CrearPlantillaModal`, App.jsx): pide los datos
//     con el `fetch` del navegador y arma la guía .ai en un hilo;
//   · el ROBOT de la integración (`robot/robot.mjs`, MAPA 619): el OTRO SISTEMA pide la plantilla
//     por la API y el robot deja los archivos para bajar (el plan para el conector de Illustrator,
//     el de CorelDRAW y la guía .ai, uno por diseño).
// Un ARCHIVO POR DISEÑO (MAPA 618): cada variable se arma como en la pestaña Plantilla de Moldería
// (`planIllustrator`, con SU acomodo y sus talles) y `empacarSecciones` + `unirPlanes` las juntan.
//
// `motorPlantilla(o)`:
//   · `dets`        — {pid: detección del molde} (`GET /api/plantilla/deteccion?pid=`);
//   · `config`      — 'default' | 'rango' | 'talle';
//   · `tallesSel`   — (talle por talle) los talles elegidos, o null = todos;
//   · `listaRangos` — (por rango) [{talles, guia}] — la lista o el rango elegido;
//   · `capas`       — las capas del arte a crear vacías (['diseño', 'Nombre', 'Número'…]);
//   · `traer(qs)`   — la promesa de `GET /api/plantilla/pdf_guia?<qs>` (cada lado con su fetch).
// Un diseño (`dis`) = `{nombre, vars: [{key, pid, clave, label, molde, variable, acomodo}]}`.
import { nombresDeVariable, posicionesDelVisor, paramsPlantilla, tallesDeDeteccion } from './plantillaVariable.js'
import { planIllustrator, repartirEnArchivos, empacarSecciones, unirPlanes, PORCENTAJES } from './illustrator.js'
import { corelDesdePlan } from './corel.js'

export function motorPlantilla({ dets, config = 'default', tallesSel = null, listaRangos = [], capas = null, traer }) {
  // LO QUE SE PIDE PARA UNA VARIABLE: una pedida, o una por rango. Cada molde usa SUS talles (el
  // rango «XS–M» de un molde que no tiene XS sale «S–M»: es el nombre de mesa que su arte va a leer).
  const pedidasDe = (it) => {
    const det = dets[it.pid]
    const tItem = tallesDeDeteccion(det)
    const piezas = nombresDeVariable(it.variable, det)
    if (config === 'rango') {
      if (!listaRangos.length) return [{ qs: paramsPlantilla({ pid: it.pid, config, guia: det.talle_ref, piezas }), rango: [] }]
      return listaRangos.map((rg) => {
        const t = tItem.filter((x) => rg.talles.includes(x))
        if (!t.length) return null
        const guia = t.includes(rg.guia) ? rg.guia : t[0]
        return { qs: paramsPlantilla({ pid: it.pid, config, rango: t, guia, piezas }), rango: t, guia, rg }
      }).filter(Boolean)
    }
    if (config === 'talle') {
      const t = tallesSel ? tItem.filter((x) => tallesSel.includes(x)) : null
      if (t && !t.length) return []
      return [{ qs: paramsPlantilla({ pid: it.pid, config, talles: t, guia: det.talle_ref, piezas }), talles: t }]
    }
    return [{ qs: paramsPlantilla({ pid: it.pid, config, guia: det.talle_ref, piezas }) }]
  }
  // los datos de una variable (varios rangos → un bloque por rango, como `_datosIllu`)
  const datosDe = async (it) => {
    const ps = pedidasDe(it)
    if (!ps.length) return null
    const ds = await Promise.all(ps.map((p) => traer(p.qs)))
    if (ds.length === 1) return ds[0]
    return { ...ds[0], capas_data: ds.map((d, i) => (d.capas_data && d.capas_data[0] ? { ...d.capas_data[0], rango: ps[i].rango } : null)).filter(Boolean) }
  }
  const optsDe = (it, d) => {
    const det = dets[it.pid]
    return { config: d.config, rango: d.rango || [], titulo: d.titulo || 'Molde', capas, editables: null,
      referencia: d.referencia || 'alto', posiciones: posicionesDelVisor(det, it.variable), talleVisor: det.talle_ref || null,
      acomodoGuia: (it.acomodo || {})[it.clave || '_molde'] || null,
      dobladillo: it.dobladillo || null }   // MOLDE A MEDIDA (MAPA 623): el margen punteado
  }
  // el nombre de cada bloque en el archivo del diseño
  const tituloDe = (it) => (it.clave ? `${it.label} · ${it.molde}` : it.molde)
  // LAS SECCIONES DE UN DISEÑO para Illustrator: cada variable como en la pestaña (repartida si
  // sola no entra) → `[{it, titulo, medida, r}]` (`r` = el plan armado; con `soloMedir`, sólo medida)
  const seccionesDe = async (dis, porc, soloMedir) => {
    const out = []
    for (const it of dis.vars) {
      const d = await datosDe(it)
      if (!d) continue
      const opts = optsDe(it, d)
      const trozos = repartirEnArchivos(d.capas_data, opts, porc)
      trozos.forEach((cd, i) => {
        const titulo = tituloDe(it) + (trozos.length > 1 ? ` (${i + 1} de ${trozos.length})` : '')
        if (soloMedir) {
          const m = planIllustrator(cd, { ...opts, escala: 100 / porc, soloMedir: true })
          out.push({ it, titulo, medida: { W: m.W, H: m.H, nMesas: m.nMesas } })
        } else {
          const r = planIllustrator(cd, { ...opts, archivo: titulo, escala: 100 / porc })
          out.push({ it, titulo, r, medida: { W: r.plan.ancho, H: r.plan.alto, nMesas: r.nMesas } })
        }
      })
    }
    return out
  }
  // cuántos archivos de Illustrator salen con estos diseños a esta escala
  const archivosA = async (disSel, porc) => {
    let n = 0
    for (const dis of disSel) n += empacarSecciones((await seccionesDe(dis, porc, true)).map((x) => x.medida), { escala: 100 / porc }).length
    return n
  }
  // LA ESCALA RECOMENDADA: la más grande a la que CADA diseño entra en UN archivo (null = ni al 10 %)
  const recomendada = async (disSel, sigue = () => true) => {
    for (const p of PORCENTAJES) {
      if (!sigue()) return null
      let entra = true
      for (const dis of disSel) {
        if (empacarSecciones((await seccionesDe(dis, p, true)).map((x) => x.medida), { escala: 100 / p }).length > 1) { entra = false; break }
      }
      if (entra) return p
    }
    return null
  }
  // MESAS QUE CHOCAN en el archivo de un diseño: el mismo nombre de mesa («Frente») para piezas
  // DISTINTAS de variables distintas (Frente 2 de una, Frente 1 de otra, o el Frente de otro molde).
  // Al subir el arte el sistema usa la primera de cada nombre: se avisa ANTES de crear.
  const choquesDe = async (disSel) => {
    const out = []
    for (const dis of disSel) {
      if (dis.vars.length < 2) continue
      const porMesa = new Map()
      for (const it of dis.vars) {
        const d = await datosDe(it)
        const items = (d && d.capas_data && d.capas_data[0] && d.capas_data[0].items) || []
        for (const x of items) {
          if (!x.nombre) continue
          const gen = String(x.nombre).replace(/\s+\d+\s*$/, '').trim() || String(x.nombre)
          const m = porMesa.get(gen) || new Map()
          const id = it.pid + '|' + x.nombre
          const e = m.get(id) || { txt: `${x.nombre} (${it.clave ? it.label : it.molde})`, vars: new Set() }
          e.vars.add(it.key)
          m.set(id, e)
          porMesa.set(gen, m)
        }
      }
      for (const [gen, m] of porMesa) {
        const vars = new Set([...m.values()].flatMap((e) => [...e.vars]))
        if (m.size > 1 && vars.size > 1) out.push({ diseno: dis.nombre, mesa: gen, piezas: [...m.values()].map((e) => e.txt) })
      }
    }
    return out
  }
  // ILLUSTRATOR: los planes (lo que se le manda al conector) de UN diseño a esta escala; uno si
  // entra, los que hagan falta si no. `tEtq` = los talles para el nombre del archivo.
  const planesIllustrator = async (dis, porc, tEtq = null) => {
    const secs = await seccionesDe(dis, porc, false)
    const avisos = []
    for (const x of secs) for (const a of x.r.avisos) if (!avisos.includes(a)) avisos.push(a)
    if (!secs.length) return { planes: [], avisos }
    const archivos = empacarSecciones(secs.map((x) => x.medida), { escala: 100 / porc })
    const planes = archivos.map((a, i) => {
      const nombre = [dis.nombre, tEtq && tEtq.length ? tEtq.join(' ') : null, porc < 100 ? `al ${porc}%` : null,
        archivos.length > 1 ? `${i + 1} de ${archivos.length}` : null].filter(Boolean).join(' - ')
      return unirPlanes(a.secciones.map((p) => ({ plan: secs[p.i].r.plan, titulo: secs[p.i].titulo, x: p.x, y: p.y })),
        { archivo: nombre, titulo: dis.nombre, escala: 100 / porc })
    })
    return { planes, avisos }
  }
  // CORELDRAW: el plan de UN diseño (a tamaño real, cada variable entera, una debajo de la otra)
  const planCorel = async (dis, tEtq = null) => {
    const secs = [], avisos = []
    for (const it of dis.vars) {
      const d = await datosDe(it)
      if (!d) continue
      const r = planIllustrator(d.capas_data, { ...optsDe(it, d), escala: 1, sinTope: true })
      for (const a of r.avisos) if (!avisos.includes(a)) avisos.push(a)
      secs.push({ titulo: tituloDe(it), r, medida: { W: r.plan.ancho, H: r.plan.alto, nMesas: r.nMesas } })
    }
    if (!secs.length) return { plan: null, avisos }
    const [arch] = empacarSecciones(secs.map((x) => x.medida), { escala: 1, sinTope: true })
    const nombre = [dis.nombre, tEtq && tEtq.length ? tEtq.join(' ') : null].filter(Boolean).join(' - ')
    const plan = corelDesdePlan(unirPlanes(arch.secciones.map((p) => ({ plan: secs[p.i].r.plan, titulo: secs[p.i].titulo, x: p.x, y: p.y })),
      { archivo: nombre, titulo: dis.nombre, escala: 1 }))
    return { plan, avisos }
  }
  // LA GUÍA .ai de UN diseño (y una por rango): las piezas de todas sus variables juntas, en filas
  // (`aiGuiaMedidas` las acomoda solas). La misma pieza del mismo molde va una vez. En rango, el
  // nombre de cada mesa lleva el rango de SU molde (`#S-M Frente`), igual que en Illustrator.
  // `armar(capas_data, opciones)` → bytes (el navegador lo hace en un hilo; el robot, directo).
  // → `{archivos: [{nombre, bytes}], fallas: [texto]}`: una guía que no se puede armar (la guía
  // es UNA mesa a tamaño real: con muchas piezas no entra en Illustrator) no tumba las otras.
  const guiasDe = async (dis, armar) => {
    const out = [], fallas = []
    for (const rg of (config === 'rango' && listaRangos.length ? listaRangos : [null])) {
      const items = [], vistos = new Set()
      let d0 = null
      for (const it of dis.vars) {
        const det = dets[it.pid]
        const piezas = nombresDeVariable(it.variable, det)
        let qs, prefijo = ''
        if (rg) {
          const t = tallesDeDeteccion(det).filter((x) => rg.talles.includes(x))
          if (!t.length) continue
          qs = paramsPlantilla({ pid: it.pid, config, rango: t, guia: t.includes(rg.guia) ? rg.guia : t[0], piezas, capas })
          prefijo = `#${t[0]}-${t[t.length - 1]} `
        } else {
          // los MISMOS parámetros que `descargarPdfGuia` (el talle guía del molde)
          qs = paramsPlantilla({ pid: it.pid, config, piezas, capas })
        }
        const d = await traer(qs)
        const cd0 = d.capas_data && d.capas_data[0]
        if (!cd0) continue
        if (!d0) d0 = cd0
        for (const x of cd0.items || []) {
          const k = it.pid + '|' + (x.nombre || '#' + items.length)
          if (vistos.has(k)) continue
          vistos.add(k)
          // MOLDE A MEDIDA: cada pieza lleva el margen (dobladillo) de SU molde: la guía .ai lo dibuja
          const x2 = it.dobladillo ? { ...x, dobladillo: it.dobladillo } : x
          items.push(x2.nombre && prefijo ? { ...x2, nombre: prefijo + x2.nombre } : x2)
        }
      }
      if (!d0 || !items.length) continue
      const base = [dis.nombre, rg ? `${rg.talles[0]}-${rg.talles[rg.talles.length - 1]}` : null].filter(Boolean).join(' ')
      try {
        const bytes = await armar([{ ...d0, items }], { config: 'default', rango: [], titulo: dis.nombre, capas, editables: null })
        const slug = String(base).replace(/[^A-Za-z0-9._-]/g, '_').replace(/_+/g, '_').replace(/^_+|_+$/g, '') || 'guia'
        out.push({ nombre: `guia_${slug}.ai`, bytes })
      } catch (e) {
        fallas.push(`La guía .ai de «${base}» no se pudo armar: ${(e && e.message) || e}`)
      }
    }
    return { archivos: out, fallas }
  }
  return { pedidasDe, datosDe, optsDe, tituloDe, seccionesDe, archivosA, recomendada, choquesDe, planesIllustrator, planCorel, guiasDe }
}

/** Los talles en el NOMBRE del archivo (como la pestaña): los rangos agregados, o los talles si no son todos. */
export function etiquetaTalles({ config, rangos = [], tallesSel = null, talles = [] }) {
  if (config === 'rango' && rangos.length) return rangos.map((rg) => `${rg.talles[0]}-${rg.talles[rg.talles.length - 1]}`)
  if (config === 'talle' && tallesSel && tallesSel.length < talles.length) return tallesSel
  return null
}
