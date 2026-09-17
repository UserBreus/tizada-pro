// LA TIZADA ENTERA, GENERADA EN ESTA COMPUTADORA — PLAN_NAVEGADOR.md, etapa 4 (camino B).
//
// Es `generar_multi` del servidor repartido en dos: el servidor VALIDA y TRADUCE el pedido
// (`POST /api/pedido/plan` → `_plan_del_pedido`: la traba antes de fabricar, las prendas, las telas,
// los giros, las tipografías, las mesas de trabajo) y esta computadora hace TODO lo pesado con el
// mismo motor que la etapa 3 (`obrero.worker.js`): cada pieza (base + estampado), el acomodo en la
// tela (`nesting/contorno.js`), la hoja con el sello (`hoja/componer.js`), el aplanado para el RIP
// (`rip/aplanar.js`), el perfil de salida y la ficha técnica (`ficha/ficha.js`). Al final manda el
// PAQUETE DEL PEDIDO (`POST /api/paquetes/pedido`) y el servidor lo guarda como un trabajo más: la
// pantalla del paso Tizada, las descargas y «Nuevo pedido» no distinguen quién lo generó.
//
// Si el pedido trae un molde que no es del camino B (o el servidor tiene esto apagado), devuelve
// `null` y la pantalla genera en el servidor como siempre.
import { motorDe, cerrarMotores } from '../arte/previa.js'
import { piezasDe } from '../arte/prendas.js'
import { traerConCache } from '../cache.js'
import { pyRound } from '../py.js'

const CM = 28.3465
const PIEZAS_RIB = new Set(['Cuello', 'TC', 'Tapacostura'])     // van a la tela RIB (motor_pedido)
const CFG_BASE = { ancho_cm: 180, altura_max_cm: 500, espaciado_cm: 0.5,
                   margenes_cm: { sup: 1, inf: 1, izq: 1, der: 1 }, resolucion_mm: 4, estrategias: ['bl', 'bandas'] }

let _config = null
export async function navegadorGeneraTizada(rutaApi = (x) => x) {
  if (_config === null) {
    try { const r = await fetch(rutaApi('/api/navegador/config')); _config = r.ok ? await r.json() : {} } catch { _config = {} }
  }
  return !!_config.tizada
}

/** `slug` de la tela como en `_nestear_y_componer`: alfanumérico o `_`, 48 caracteres, o «Tela». */
function slugTela(prefijo, tela) {
  let s = prefijo
  for (const ch of String(tela)) s += /[\p{L}\p{N}]/u.test(ch) ? ch : '_'
  return s.slice(0, 48) || 'Tela'
}

async function json(url, opts) {
  const r = await fetch(url, opts)
  const d = await r.json().catch(() => ({}))
  if (!r.ok) { const e = new Error(d.error || `${url}: ${r.status}`); e.datos = d; throw e }
  return d
}

/** `_fuentes_guia`: con qué tipografía sale cada campo (para la ficha). */
function fuentesGuia(pers, talle, fuentes, resolver) {
  const campos = {}
  for (const mapa of Object.values(pers || {})) {
    for (const [campo, pl] of Object.entries(mapa || {})) {
      if (!pl || typeof pl !== 'object') continue
      const p = ((pl.por_talle || {})[String(talle)]) || pl
      const f = String(p.fuente || '').trim()
      if (f && !(campo in campos)) campos[campo] = f
    }
  }
  const salida = []
  for (const campo of Object.keys(campos).sort()) {
    const pedida = campos[campo]
    const r = resolver(campo, pedida)
    salida.push({ campo, fuente: r.fuente, pedida, sustituida: r.sustituida })
  }
  return salida
}

/**
 * Genera el pedido acá. `cuerpo` = lo mismo que se manda a `/api/generar_multi`.
 * `avisar(texto)` recibe el avance. Devuelve `{id}` del trabajo guardado, o `null` si este pedido
 * lo tiene que generar el servidor.
 */
export async function generarPedidoEnNavegador(cuerpo, { rutaApi, avisar = null } = {}) {
  if (!(await navegadorGeneraTizada(rutaApi))) return null
  const t0 = performance.now()
  const decir = (t) => { if (avisar) avisar(t) }
  decir('Revisando el pedido…')
  const plan = await json(rutaApi('/api/pedido/plan'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cuerpo) })
  if (!plan.todo_camino_b) return null
  // el perfil de salida (OutputIntent), una vez
  let perfil = null
  if (plan.perfil) {
    const r = await fetch(rutaApi('/api/pedido/perfil_salida' + (cuerpo.perfil_forzado ? '?forzado=' + encodeURIComponent(cuerpo.perfil_forzado) : '')))
    if (r.ok) perfil = { icc: new Uint8Array(await r.arrayBuffer()), nombre: plan.perfil.nombre, n: plan.perfil.n }
  }
  const archivos = {}            // nombre → Uint8Array
  const hojas = []
  const validaciones = []
  let totalPiezas = 0
  const avisos = plan.avisos.slice(), avisosPedido = plan.avisos_pedido.slice()
  const guiasPiezas = new Map()  // (pid|diseno|clave) → {piezas:[{nombre,w_cm,h_cm,pdf,tela}], fuentes, pers, talle}
  for (let gi = 0; gi < plan.grupos.length; gi++) {
    const grupo = plan.grupos[gi]
    const porTela = new Map()
    const motoresGrupo = new Map()   // pid → motor (para que la hoja encuentre sus mesas abiertas)
    let hechas = 0
    const total = grupo.moldes.reduce((n, i) => n + plan.moldes[i].prendas.length, 0)
    for (const mi of grupo.moldes) {
      const md = plan.moldes[mi]
      const m = await motorDe(md.pid, rutaApi)
      if (!m) throw new Error(`«${md.nombre}» no es un molde con el diseño adentro`)
      if (m.info.paginas_pendientes) throw new Error(`«${md.nombre}» todavía se está terminando de preparar`)
      motoresGrupo.set(md.pid, m)
      // las tipografías de ESTE molde en ESTE diseño (los reemplazos son por par)
      await m.pool.enviar('fuentes', await bajarFuentes(md.fuentes, md.pid, rutaApi))
      m.fuentesListas = true
      const { registro, pers } = m.info
      const bases = new Map()        // (pieza|talle|variante) → base compartida (el MISMO objeto)
      for (let k = 0; k < md.prendas.length; k++) {
        const pr = md.prendas[k]
        const nro = k + 1
        for (const pieza of piezasDe(pr, registro)) {
          const t = pr.talle
          const info = (registro[pieza] || {})[t]
          if (!info) continue
          const mesa = info.mesa
          const claveMesa = `${md.pid}|${mesa}`
          await asegurarMesaAbierta(m, rutaApi, mesa, claveMesa)
          const idx = await indiceDeMesa(m, rutaApi, mesa)
          const cont = (idx.talles[t] || [])[info.idx_mesa ?? info.pieza_idx]
          if (!cont) continue
          const pagina = (idx.orden || []).indexOf(t)
          const persona = pr.personalizacion || { nombre: pr.nombre || '', numero: pr.numero || '' }
          const r = await m.pool.enviar('pieza', {
            mesa: claveMesa, pagina, cont, borde: md.borde_corte, etiqueta: md.etiqueta, ph: (md.pers || pers || {})[String(mesa)] || {},
            persona, talle: t, pieza, nro, variante: pr.variante_clave || null, grupo: pr._grupo || null, info,
            alias: md.fuentes.alias,
          })
          const bk = `${pieza}|${t}|${pr.variante_clave || ''}`
          if (!bases.has(bk)) {
            bases.set(bk, { baseStream: r.baseStream, B: r.B, W: r.W, Hp: r.Hp, S: r.S, x0: cont.bbox_raw[0], y0: cont.bbox_raw[1],
                            cont, fuentesXo: [['/A0', { origen: claveMesa, pagina }]], delMolde: true })
          }
          const rot = (md.rotaciones && md.rotaciones[pieza]) || 'ninguna'
          const tela = (md.asignacion_tela && md.asignacion_tela[pieza]) || (PIEZAS_RIB.has(pieza) ? 'RIB' : 'Principal')
          if (!porTela.has(tela)) porTela.set(tela, [])
          porTela.get(tela).push({ w: r.w, h: r.h, base: bases.get(bk), estampado: r.estampado, pieza, talle: t,
                                   variante: pr.variante_clave || null, etiqueta: String(nro).padStart(2, '0'),
                                   rotacion: rot, borde_cm: 0, _molde: md.pid, _mesa: mesa })
          totalPiezas++
        }
        hechas++
        decir(`Armando las piezas · ${hechas}/${total} prendas`)
      }
      // la guía de la ficha de este molde·diseño·variable: las piezas de muestra ya salen de acá
      for (const g of plan.guias.filter((x) => x.pid === md.pid && x.diseno === md.diseno)) {
        const kg = `${g.pid}|${g.diseno}|${g.clave || ''}`
        if (guiasPiezas.has(kg)) continue
        guiasPiezas.set(kg, { g, md, m })
      }
    }
    // una hoja por tela: TODAS las piezas de la tela juntas, sin importar el molde
    let ti = 0
    for (const [tela, piezas] of porTela) {
      ti++
      decir(`Acomodando en la tela «${tela}» (${piezas.length} piezas)…`)
      const cfg = { ...CFG_BASE, ...(plan.cfg_nesting || {}), ...((plan.telas_cfg || {})[tela] || {}) }
      // las mesas de origen tienen que estar abiertas en el MISMO hilo que compone la hoja
      const pids = [...new Set(piezas.map((p) => p._molde))]
      const mm = motoresGrupo.get(pids[0])
      for (const pid of pids.slice(1)) {
        const otro = motoresGrupo.get(pid)
        for (const mesa of new Set(piezas.filter((p) => p._molde === pid).map((p) => p._mesa))) {
          await copiarMesa(otro, mm, rutaApi, pid, mesa)
        }
      }
      const r = await mm.pool.enviar('hoja', { piezas, cfg, perfil, tela })
      const slug = slugTela(`g${gi}_`, tela)
      const archivo = `HOJA_${slug}.pdf`
      archivos[archivo] = r.pdf
      const denom = Number(cfg.ancho_cm) * Number(r.consumoCm)
      hojas.push({ tela, archivo, paginas: r.alturasCm.length, consumo_cm: pyRound(Number(r.consumoCm), 1),
                   alturas_cm: r.alturasCm, ancho_cm: pyRound(Number(cfg.ancho_cm), 1),
                   aprovechamiento: denom > 0 ? pyRound(100 * r.area / denom, 1) : 0.0, previews: [],
                   grupo: grupo.nombre, moldes: grupo.nombres })
      validaciones.push(...r.validaciones)
    }
  }
  // ── la ficha técnica ──
  let ficha = null
  const mm0 = [...guiasPiezas.values()][0]?.m || null
  try {
    if (!mm0) throw new Error('sin motor abierto')
    decir('Armando la ficha técnica…')
    const guias = []
    for (const { g, md, m } of guiasPiezas.values()) {
      const { registro, pers } = m.info
      const talles = [...new Set(Object.values(registro).flatMap((v) => Object.keys(v || {})))].sort()
      const guiaT = m.info.variante_guia
      const talle = talles.includes(guiaT) ? guiaT : talles[Math.floor(talles.length / 2)]
      const solo = new Set(g.piezas || [])
      const vistas = new Set()
      const piezas = []
      const combos = (g.combos && g.combos.length) ? g.combos : [[]]
      for (const toggles of combos) {
        const pr = { ...(md.prendas[0] || {}), talle, toggles, personalizacion: { ...(g.muestra || {}), talle } }
        if (!pr.personalizacion.nombre && !pr.personalizacion.numero) pr.personalizacion = { nombre: 'NOMBRE', numero: '00', talle }
        for (const pieza of piezasDe(pr, registro)) {
          if ((solo.size && !solo.has(pieza)) || vistas.has(pieza)) continue
          const info = (registro[pieza] || {})[talle]
          if (!info) continue
          const mesa = info.mesa
          const claveMesa = `${md.pid}|${mesa}`
          await asegurarMesaAbierta(m, rutaApi, mesa, claveMesa)
          const idx = await indiceDeMesa(m, rutaApi, mesa)
          const cont = (idx.talles[talle] || [])[info.idx_mesa ?? info.pieza_idx]
          if (!cont) continue
          const r = await m.pool.enviar('pieza', {
            mesa: claveMesa, pagina: (idx.orden || []).indexOf(talle), cont, borde: md.borde_corte, etiqueta: md.etiqueta,
            ph: (md.pers || pers || {})[String(mesa)] || {}, persona: pr.personalizacion, talle, pieza, nro: 1,
            variante: g.clave || null, grupo: null, info, alias: md.fuentes.alias, salida: 'pdf',
          })
          vistas.add(pieza)
          piezas.push({ nombre: pieza, w_cm: pyRound(r.w / CM, 1), h_cm: pyRound(r.h / CM, 1), pdf: r.pdf,
                        tela: (g.asig && g.asig[pieza]) || (PIEZAS_RIB.has(pieza) ? 'RIB' : 'Principal') })
        }
      }
      piezas.sort((a, b) => (String(a.nombre) < String(b.nombre) ? -1 : String(a.nombre) > String(b.nombre) ? 1 : 0))
      const ops = {}
      for (const c of combos) for (const t of (c || [])) {
        const k = String(t.clave || '').trim(), o = String(t.opcion || '').trim()
        if (k && o) { const K = k.charAt(0).toUpperCase() + k.slice(1).toLowerCase(); ops[K] = ops[K] || []; if (!ops[K].includes(o)) ops[K].push(o) }
      }
      const opciones = Object.entries(ops).map(([k, v]) => `${k}: ${v.join(' + ')}`).join(' · ') || null
      const vnom = (m.info.variantes || []).find((v) => v.clave === g.clave)
      guias.push({ nombre: g.molde || md.nombre, diseno: g.diseno_nombre || 'Principal', variante: vnom ? (vnom.label || vnom.nombre) : null,
                   opciones, ejemplo: null, piezas, fuentes: fuentesGuia(md.pers || pers, talle, md.fuentes, (campo, pedida) => ({ fuente: pedida, sustituida: false })),
                   procesos: [] })
    }
    const fecha = new Date()
    const dd = String(fecha.getDate()).padStart(2, '0'), mmx = String(fecha.getMonth() + 1).padStart(2, '0')
    const planilla = plan.planilla_ficha || { columnas: [], filas: plan.prendas }
    const pdfFicha = await mm0.pool.enviar('ficha', { titulo: 'Ficha técnica', subtitulo: `${plan.nombres.join(' + ')} · ${dd}/${mmx}/${fecha.getFullYear()}`, planilla, moldesGuia: guias })
    if (pdfFicha) { archivos['FICHA_TECNICA.pdf'] = pdfFicha; ficha = 'FICHA_TECNICA.pdf' }
  } catch (e) {
    avisos.push('La ficha técnica no se pudo armar en esta computadora: ' + (e.message || e))
  }
  // ── el paquete al servidor ──
  decir('Guardando el pedido en el servidor…')
  const resultado = { hojas, validaciones, duracion_s: pyRound((performance.now() - t0) / 1000, 1), piezas: totalPiezas,
                      avisos, avisos_pedido: avisosPedido, perfil_icc: perfil ? perfil.nombre : null, ficha }
  const fd = new FormData()
  fd.append('resultado', JSON.stringify(resultado))
  fd.append('prendas', JSON.stringify(plan.prendas))
  fd.append('nombres', JSON.stringify(plan.nombres))
  fd.append('pids', JSON.stringify(cuerpo.molds || cuerpo.productos || []))
  for (const [nombre, bytes] of Object.entries(archivos)) fd.append(nombre, new Blob([bytes], { type: 'application/pdf' }), nombre)
  const d = await json(rutaApi('/api/paquetes/pedido'), { method: 'POST', body: fd })
  return { id: d.id, resultado: d.resultado, segundos: (performance.now() - t0) / 1000 }
}

async function bajarFuentes(fuentes, pid, rutaApi) {
  const archivos = {}
  await Promise.all((fuentes.catalogo || []).map(async (f) => {
    const url = rutaApi(`/api/fuente/archivo/${encodeURIComponent(f.archivo)}` + (f.propia ? `?pid=${encodeURIComponent(pid)}` : ''))
    archivos[f.archivo] = await traerConCache(`fuente|${f.hash}|${f.archivo}`, url)
  }))
  return { catalogo: fuentes.catalogo, archivos, alias: fuentes.alias || {} }
}

async function asegurarMesaAbierta(m, rutaApi, mesa, clave) {
  if (m.mesasAbiertas.has(clave)) return
  const md = m.info.mesas.find((x) => x.mesa === mesa)
  if (!md || !md.paginas) throw new Error(`la mesa ${mesa} todavía no tiene sus páginas por talle`)
  const bytes = await traerConCache(`${m.pid}|m${mesa}.pdf|${(md.sello || []).join(',')}`,
    rutaApi(`/api/productos/${encodeURIComponent(m.pid)}/desplegado/m${mesa}.pdf`))
  await m.pool.enviar('mesa_abrir', { mesa: clave, bytes }, [bytes.buffer])
  m.mesasAbiertas.add(clave)
}

async function indiceDeMesa(m, rutaApi, mesa) {
  m.indices = m.indices || new Map()
  if (!m.indices.has(mesa)) {
    const md = m.info.mesas.find((x) => x.mesa === mesa)
    const bytes = await traerConCache(`${m.pid}|m${mesa}.json|${(md.sello || []).join(',')}`,
      rutaApi(`/api/productos/${encodeURIComponent(m.pid)}/desplegado/m${mesa}.json`))
    m.indices.set(mesa, JSON.parse(new TextDecoder().decode(bytes)))
  }
  return m.indices.get(mesa)
}

/** Dos moldes en la misma tela: las mesas del segundo se abren también en el hilo del primero. */
async function copiarMesa(desde, hasta, rutaApi, pid, mesa) {
  const clave = `${pid}|${mesa}`
  if (hasta.mesasAbiertas.has(clave)) return
  const md = desde.info.mesas.find((x) => x.mesa === mesa)
  const bytes = await traerConCache(`${pid}|m${mesa}.pdf|${(md.sello || []).join(',')}`,
    rutaApi(`/api/productos/${encodeURIComponent(pid)}/desplegado/m${mesa}.pdf`))
  await hasta.pool.enviar('mesa_abrir', { mesa: clave, bytes }, [bytes.buffer])
  hasta.mesasAbiertas.add(clave)
}

export { cerrarMotores }
