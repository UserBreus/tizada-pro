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
// El molde SIN diseño adentro (camino A) va igual (PLAN_NAVEGADOR 1b): la plantilla pelada y el
// arte separado se bajan una vez, el contexto del arte se arma en el hilo (`contexto_a`) y cada
// pieza sale de `pieza_a` (`pieza/caminoA.js`); la hoja se compone en el hilo del PRIMER molde
// del grupo, adonde van todas las bases. Si el servidor tiene esto apagado, o un molde del
// camino A no tiene el arte de su diseño, devuelve `null` y la pantalla genera en el servidor.
import { motorDe, cerrarMotores, asegurarMoldeA, asegurarContextoA, disenoDe } from '../arte/previa.js'
import { piezasDe } from '../arte/prendas.js'
import { traerConCache, claveDe, urlDe } from '../cache.js'
import { pyRound } from '../py.js'
import { puedeHacer } from '../capacidad.js'
import { resolverFuente } from '../texto/fuentes.js'
import { claveFuenteCampo } from '../pieza/estampar.js'

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
  // 🔴 EL % REAL (pedido del usuario 2026-09-22: «la barra queda en 15 % trancada»). La barra de
  // la pantalla sólo entendía el formato del servidor («fase: n/N») y estos textos la dejaban en 15.
  // Ahora cada aviso lleva el porcentaje de lo HECHO: revisar 0-4 · cada grupo (su parte según sus
  // prendas): piezas 55 % + hojas 45 % · ficha 92-96 · guardar 96-99. Sólo se cuenta: no agrega trabajo.
  let pctActual = 0
  const decir = (t, pct = null) => {
    if (pct !== null) pctActual = Math.max(pctActual, Math.min(99, Math.round(pct)))
    if (avisar) avisar(`nav|${pctActual}|${t}`)
  }
  decir('Revisando el pedido…', 1)
  // CUÁNTO TARDA CADA ETAPA (2026-09-22): viaja en `resultado.tiempos` y queda en el pedido guardado,
  // para saber DÓNDE se va el tiempo sin adivinar. Sólo mide: no cambia nada.
  const _tiempos = { plan: 0, piezas: 0, hojas: [], ficha: 0, guardar: 0 }
  const _tPlan0 = performance.now()
  const plan = await json(rutaApi('/api/pedido/plan'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cuerpo) })
  if (!plan.todo_camino_b && !plan.todo_navegador) return null
  _tiempos.plan = (performance.now() - _tPlan0) / 1000
  // LA PUERTA (etapa 5): la memoria que piden las mesas desplegadas (camino B) o la plantilla y el
  // arte (camino A) de todos los moldes del pedido
  {
    let mb = 0
    for (const md of plan.moldes) {
      const m = await motorDe(md.pid, rutaApi)
      if (m && m.info.mesas) for (const x of m.info.mesas) mb += (x.bytes || 0) / 1048576
      if (m && m.info.camino_a) {
        mb += ((m.info.plantilla || {}).bytes || 0) / 1048576
        const d = disenoDe(m, md.diseno)
        if (!d) return null                       // sin arte para ese diseño: lo decide el servidor
        mb += ((d.sello || [])[0] || 0) / 1048576
      }
    }
    const puerta = puedeHacer({ tipo: 'tizada', mb, hojas: Math.max(1, plan.grupos.length) })
    if (!puerta.puede) { const e = new Error(puerta.motivo); e.capacidad = true; throw e }
  }
  // el perfil de salida (OutputIntent), una vez
  let perfil = null
  if (plan.perfil) {
    // el perfil que eligió el plan (el que trae el arte, o el que se unificó a mano)
    const _pfArch = cuerpo.perfil_forzado || plan.perfil.archivo || ''
    const r = await fetch(rutaApi('/api/pedido/perfil_salida' + (_pfArch ? '?forzado=' + encodeURIComponent(_pfArch) : '')))
    if (r.ok) perfil = { icc: new Uint8Array(await r.arrayBuffer()), nombre: plan.perfil.nombre, n: plan.perfil.n }
  }
  const archivos = {}            // nombre → Uint8Array
  const hojas = []
  const validaciones = []
  let totalPiezas = 0
  const avisos = plan.avisos.slice(), avisosPedido = plan.avisos_pedido.slice()
  const _rip = []                 // la revisión para el RIP de cada hoja (la hace el hilo de la hoja)
  const guiasPiezas = new Map()  // (pid|diseno|clave) → {piezas:[{nombre,w_cm,h_cm,pdf,tela}], fuentes, pers, talle}
  // la parte de la barra de cada grupo: según cuántas prendas lleva (de 4 % a 92 %)
  const _prGrupo = plan.grupos.map((g) => g.moldes.reduce((n, i) => n + plan.moldes[i].prendas.length, 0))
  const _prTotal = Math.max(1, _prGrupo.reduce((a, b) => a + b, 0))
  let _inicioGrupo = 4
  // ── la guía de la ficha técnica, EN PARALELO CON LAS HOJAS ──
  // 🔴 2026-09-22 («la ficha no puede tardar más de 1 s aunque tenga 60 hojas»): cada molde tiene
  // su hilo, y mientras la hoja larga se arma en el hilo del 1º molde los demás quedaban parados.
  // Las piezas de la guía se piden apenas el grupo tiene sus piezas, así se dibujan mientras se
  // acomoda y se arma la hoja; cuando la hoja termina, la ficha sólo pone la tabla y las imágenes.
  const _guiasProm = []           // una promesa por guía, en el orden de `guiasPiezas`
  let _tGuia = 0
  const armarGuia = async ({ g, md, m, info: infoM, claveArte }) => {
    const _t0 = performance.now()
    try {
      const { registro, pers } = infoM || m.info
      const talles = [...new Set(Object.values(registro).flatMap((v) => Object.keys(v || {})))].sort()
      const guiaT = (infoM || m.info).variante_guia
      const talle = talles.includes(guiaT) ? guiaT : talles[Math.floor(talles.length / 2)]
      const solo = new Set(g.piezas || [])
      const vistas = new Set()
      const piezas = []
      const combos = (g.combos && g.combos.length) ? g.combos : [[]]
      const lote = []               // [{camino, datos, pieza, tela}] → UNA tarea al hilo del molde
      for (const toggles of combos) {
        // `_molde_guia_ficha`: la guía muestra el diseño como se ve desde el inicio, «NOMBRE» y «00»
        // (regla del usuario 2026-09-16); los nombres y números de cada prenda están en la tabla
        const pr = { ...(md.prendas[0] || {}), talle, toggles, nombre: 'NOMBRE', numero: '00', personalizacion: { nombre: 'NOMBRE', numero: '00', talle } }
        for (const pieza of piezasDe(pr, registro)) {
          if ((solo.size && !solo.has(pieza)) || vistas.has(pieza)) continue
          const info = (registro[pieza] || {})[talle]
          if (!info) continue
          const mesa = info.mesa
          vistas.add(pieza)
          const tela = (g.asig && g.asig[pieza]) || (PIEZAS_RIB.has(pieza) ? 'RIB' : 'Principal')
          if (claveArte) {
            // camino A: la pieza de muestra sale del mismo contexto del arte que la tizada
            lote.push({ pieza, tela, camino: 'a', datos: {
              molde: md.pid, arte: claveArte, mesa, talle, pieza, info, persona: pr.personalizacion, nro: 1,
              variante: g.clave || null, grupo: null, ph: md.pers || pers || {}, etiqueta: md.etiqueta, alias: md.fuentes.alias,
            } })
          } else {
            const claveMesa = `${md.pid}|${mesa}`
            await asegurarMesaAbierta(m, rutaApi, mesa, claveMesa)
            const idx = await indiceDeMesa(m, rutaApi, mesa)
            const cont = (idx.talles[talle] || [])[info.idx_mesa ?? info.pieza_idx]
            if (!cont) continue
            lote.push({ pieza, tela, camino: 'b', datos: {
              mesa: claveMesa, pagina: (idx.orden || []).indexOf(talle), cont, borde: md.borde_corte, etiqueta: md.etiqueta,
              ph: (md.pers || pers || {})[String(mesa)] || {}, persona: pr.personalizacion, talle, pieza, nro: 1,
              variante: g.clave || null, grupo: null, info, alias: md.fuentes.alias,
            } })
          }
        }
      }
      // 🔴 LA GUÍA NO SE DIBUJA: ES EL ARCHIVO (2026-09-22, «ya tenemos el diseño, usá eso; no más
      // de 1 s»). Antes: un PDF por pieza con la mesa ENTERA adentro, que la ficha reabría y
      // rasterizaba (~35 s). Ahora el hilo del molde arma UN PDF con una página por pieza que
      // nombra la mesa del talle guía (o el arte) copiada UNA vez, y la ficha lo pega vectorial.
      // Una pieza que falla deja su tarjeta vacía y avisa: la ficha sale igual.
      const rg = lote.length ? await m.pool.enviar('guia_pdf', { piezas: lote.map((x) => ({ camino: x.camino, datos: x.datos })) }) : { pdf: null, piezas: [] }
      lote.forEach((x, i) => {
        const q = rg.piezas[i] || { error: 'sin respuesta' }
        if (q.error) {
          avisos.push(`Ficha técnica: la pieza «${x.pieza}» no se pudo armar (${q.error})`)
          piezas.push({ nombre: x.pieza, tela: x.tela })
        } else {
          piezas.push({ nombre: x.pieza, tela: x.tela, pagina: q.pagina, w_pt: q.w, h_pt: q.h,
                        w_cm: pyRound(q.wr / CM, 1), h_cm: pyRound(q.hr / CM, 1) })
        }
      })
      piezas.sort((a, b) => (String(a.nombre) < String(b.nombre) ? -1 : String(a.nombre) > String(b.nombre) ? 1 : 0))
      const ops = {}
      for (const c of combos) for (const t of (c || [])) {
        const k = String(t.clave || '').trim(), o = String(t.opcion || '').trim()
        if (k && o) { const K = k.charAt(0).toUpperCase() + k.slice(1).toLowerCase(); ops[K] = ops[K] || []; if (!ops[K].includes(o)) ops[K].push(o) }
      }
      const opciones = Object.entries(ops).map(([k, v]) => `${k}: ${v.join(' + ')}`).join(' · ') || null
      const vnom = ((infoM || m.info).variantes || []).find((v) => v.clave === g.clave)
      // `_fuentes_guia`: la que SALIÓ estampada (la elección del pedido manda; sin la fuente en el
      // catálogo, Anton Regular «se sustituyó»)
      const resolverGuia = (campo, pedida) => {
        const alias = md.fuentes.alias || {}
        const porCampo = alias[claveFuenteCampo(campo)]
        const fc = porCampo || pedida
        let e = resolverFuente(fc, md.fuentes.catalogo || [], porCampo ? {} : alias)
        const sustituida = !e
        if (sustituida) e = resolverFuente('Anton Regular', md.fuentes.catalogo || [], alias)
        return { fuente: (e && e.interno) || (sustituida ? 'Anton Regular' : pedida), sustituida }
      }
      // LO QUE NO SE SUBLIMA (TPU/Bordado/DTF): el servidor dice QUÉ y DÓNDE (mesa, capa, recuadro);
      // el DIBUJO del objeto se aísla acá del arte, en vector (antes era una miniatura del servidor)
      const procesos = []
      const dArte = claveArte ? ((infoM || m.info).disenos || []).find((x) => x.id === (md.diseno || 'principal')) : null
      let arteBytes = null
      for (const pr of (g.procesos || [])) {
        const p2 = { ...pr }
        if (!p2.pdf && dArte && pr.mesa && pr.capa && pr.bbox_mu) {
          try {
            if (!arteBytes) {
              arteBytes = await traerConCache(`arte|${md.pid}|${dArte.id}|${(dArte.sello || []).join(',')}`,
                rutaApi(`/api/productos/${encodeURIComponent(md.pid)}/arte_archivo` + (dArte.id !== 'principal' ? `?diseno=${encodeURIComponent(dArte.id)}` : '')))
            }
            const b = arteBytes.slice()
            p2.pdf = await m.pool.enviar('arte_objeto_pdf', { bytes: b, mesa: pr.mesa, capa: pr.capa, bbox: pr.bbox_mu }, [b.buffer])
          } catch { /* sin el dibujo: la ficha dice «(sin vista)» */ }
        }
        procesos.push(p2)
      }
      return { nombre: g.molde || md.nombre, diseno: g.diseno_nombre || 'Principal', variante: vnom ? (vnom.label || vnom.nombre) : null,
                   opciones, ejemplo: null, piezas, pdf_guia: rg.pdf, fuentes: fuentesGuia(md.pers || pers, talle, md.fuentes, resolverGuia),
                   procesos }   // TPU/Bordado/DTF y «sin marca»: el servidor dice cuáles, el dibujo es de acá

    } finally {
      _tGuia += (performance.now() - _t0) / 1000
    }
  }
  decir('Revisando el pedido…', 4)
  for (let gi = 0; gi < plan.grupos.length; gi++) {
    // la guía del grupo anterior usa contextos del arte que el grupo siguiente puede reabrir:
    // se espera a que termine antes de tocarlos (lo normal es un solo grupo)
    if (_guiasProm.length) await Promise.allSettled(_guiasProm)
    const grupo = plan.grupos[gi]
    const _parte = 88 * (_prGrupo[gi] / _prTotal), _ini = _inicioGrupo
    _inicioGrupo += _parte
    const _pctPiezas = (h, tot) => _ini + _parte * 0.55 * (tot ? h / tot : 1)
    const porTela = new Map()
    const motoresGrupo = new Map()   // pid → motor (para que la hoja encuentre sus mesas abiertas)
    let hechas = 0
    const total = grupo.moldes.reduce((n, i) => n + plan.moldes[i].prendas.length, 0)
    // el hilo del PRIMER molde del grupo compone la hoja: ahí van las bases del camino A y se
    // copian las mesas de los otros moldes del camino B
    const mmG = await motorDe(plan.moldes[grupo.moldes[0]].pid, rutaApi)
    if (!mmG) throw new Error(`«${plan.moldes[grupo.moldes[0]].nombre}» no se puede generar en esta computadora`)
    // 🔴 CADA MOLDE EN SU HILO, A LA VEZ (2026-09-22, «sigue demorando»). Antes los moldes del grupo
    // se armaban de a uno aunque cada molde del camino B tiene su propio hilo: mientras uno armaba una
    // pieza los demás esperaban. Ahora los del camino B trabajan en paralelo (los del A comparten el
    // hilo del grupo y siguen en fila) y lo que arma cada uno se junta DESPUÉS, en el orden de
    // siempre (molde por molde): mismas hojas, mismo acomodo.
    const _tPiezas0 = performance.now()
    const _motores = await Promise.all(grupo.moldes.map((mi) => motorDe(plan.moldes[mi].pid, rutaApi)))
    const _procA = async (md, m) => {
      const items = [], guias = []
        // ── CAMINO A: molde pelado + arte separado, en el hilo del grupo ──
      await mmG.pool.enviar('fuentes', await bajarFuentes(md.fuentes, md.pid, rutaApi))
      await asegurarMoldeA(m, rutaApi, md.pid, (m.info.plantilla || {}).sello, mmG)
      const { clave } = await asegurarContextoA(m, rutaApi, md.diseno, {
        mapeoArte: md.mapeo_arte || null, editablesCfg: md.editables_cfg, editablesTamano: md.editables_tamano,
        editablesColor: md.editables_color, editablesMarca: md.editables_marca, editablesSinMarca: md.editables_sin_marca,
        marcasComoCruz: true, borde: md.borde_corte, referencia: md.referencia,
      }, { hilo: mmG })
      const { registro } = m.info
      for (let k = 0; k < md.prendas.length; k++) {
        const pr = md.prendas[k]
        const nro = k + 1
        for (const pieza of piezasDe(pr, registro)) {
        const t = pr.talle
        const info = (registro[pieza] || {})[t]
        if (!info) continue
        const persona = pr.personalizacion || { nombre: pr.nombre || '', numero: pr.numero || '' }
        const r = await mmG.pool.enviar('pieza_a', {
          molde: md.pid, arte: clave, mesa: info.mesa, talle: t, pieza, info, persona, nro,
          variante: pr.variante_clave || null, grupo: pr._grupo || null, ph: md.pers || {}, etiqueta: md.etiqueta, alias: md.fuentes.alias,
        })
        const rot = (md.rotaciones && md.rotaciones[pieza]) || 'ninguna'
        const tela = (md.asignacion_tela && md.asignacion_tela[pieza]) || (PIEZAS_RIB.has(pieza) ? 'RIB' : 'Principal')
        items.push([tela, { w: r.w, h: r.h, base: { id: r.baseId }, estampado: r.estampado, pieza, talle: t,
                                 variante: pr.variante_clave || null, etiqueta: String(nro).padStart(2, '0'),
                                 rotacion: rot, borde_cm: 0, _molde: md.pid, _mesa: null }])
        totalPiezas++
        }
        hechas++
        decir(`Armando las piezas · ${hechas}/${total} prendas`, _pctPiezas(hechas, total))
      }
      const guiasMd = plan.guias.filter((x) => x.pid === md.pid && x.diseno === md.diseno)
      if (guiasMd.length) {
        // la guía de la ficha se dibuja con `marcas_como_cruz=False` (`_molde_guia_ficha`): ahí el
        // objeto se tiene que seguir viendo en su lugar, la cruz es para la tela → otro contexto
        const { clave: claveFicha } = await asegurarContextoA(m, rutaApi, md.diseno, {
        mapeoArte: md.mapeo_arte || null, editablesCfg: md.editables_cfg, editablesTamano: md.editables_tamano,
        editablesColor: md.editables_color, editablesMarca: md.editables_marca, editablesSinMarca: md.editables_sin_marca,
        marcasComoCruz: false, borde: md.borde_corte, referencia: md.referencia,
        }, { hilo: mmG, clave: `${clave}|ficha` })
        for (const g of guiasMd) guias.push([`${g.pid}|${g.diseno}|${g.clave || ''}`, { g, md, m: mmG, info: m.info, claveArte: claveFicha }])
      }
            return { items, guias, motor: mmG }
    }
    const _procB = async (md, m) => {
      const items = [], guias = []
      if (m.info.paginas_pendientes) throw new Error(`«${md.nombre}» todavía se está terminando de preparar`)
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
          items.push([tela, { w: r.w, h: r.h, base: bases.get(bk), estampado: r.estampado, pieza, talle: t,
                                   variante: pr.variante_clave || null, etiqueta: String(nro).padStart(2, '0'),
                                   rotacion: rot, borde_cm: 0, _molde: md.pid, _mesa: mesa }])
          totalPiezas++
        }
        hechas++
        decir(`Armando las piezas · ${hechas}/${total} prendas`, _pctPiezas(hechas, total))
      }
      // la guía de la ficha de este molde·diseño·variable: las piezas de muestra ya salen de acá
      for (const g of plan.guias.filter((x) => x.pid === md.pid && x.diseno === md.diseno)) {
        guias.push([`${g.pid}|${g.diseno}|${g.clave || ''}`, { g, md, m, info: m.info }])
      }
      return { items, guias, motor: m }
    }
    let _filaA = Promise.resolve()
    const _tareasMoldes = grupo.moldes.map((mi, k) => {
      const md = plan.moldes[mi]
      const m = _motores[k]
      if (!m) throw new Error(`«${md.nombre}» no se puede generar en esta computadora`)
      if (m.info.camino_a) { _filaA = _filaA.then(() => _procA(md, m)); return _filaA }
      return _procB(md, m)
    })
    const _res = await Promise.all(_tareasMoldes)
    grupo.moldes.forEach((mi, k) => {
      const md = plan.moldes[mi]
      motoresGrupo.set(md.pid, _res[k].motor)
      for (const [tela, e] of _res[k].items) { if (!porTela.has(tela)) porTela.set(tela, []); porTela.get(tela).push(e) }
      for (const [kg, v] of _res[k].guias) {
        if (guiasPiezas.has(kg)) continue
        guiasPiezas.set(kg, v)
        const pr = armarGuia(v)
        pr.catch(() => {})       // el error se lee al armar la ficha (va a los avisos)
        _guiasProm.push(pr)
      }
    })
    _tiempos.piezas += (performance.now() - _tPiezas0) / 1000
    // una hoja por tela: TODAS las piezas de la tela juntas, sin importar el molde
    const _nTelas = Math.max(1, porTela.size)
    let _telaK = 0
    for (const [tela, piezas] of porTela) {
      const _iniT = _ini + _parte * (0.55 + 0.45 * (_telaK / _nTelas)), _parteT = _parte * 0.45 / _nTelas
      _telaK++
      decir(`Acomodando en la tela «${tela}» (${piezas.length} piezas)…`, _iniT)
      const cfg = { ...CFG_BASE, ...(plan.cfg_nesting || {}), ...((plan.telas_cfg || {})[tela] || {}) }
      // las mesas de origen tienen que estar abiertas en el MISMO hilo que compone la hoja
      const _tHoja0 = performance.now()
      const pids = [...new Set(piezas.map((p) => p._molde))]
      const mm = mmG
      for (const pid of pids) {
        const otro = motoresGrupo.get(pid)
        if (!otro || otro === mm) continue
        for (const mesa of new Set(piezas.filter((p) => p._molde === pid && p._mesa !== null).map((p) => p._mesa))) {
          await copiarMesa(otro, mm, rutaApi, pid, mesa)
        }
      }
      const r = await mm.pool.enviar('hoja', { piezas, cfg, perfil, tela }, undefined,
        (f, txt) => decir(`${txt || 'Armando la hoja'} · tela «${tela}»…`, _iniT + _parteT * f))
      const slug = slugTela(`g${gi}_`, tela)
      const archivo = `HOJA_${slug}.pdf`
      archivos[archivo] = r.pdf
      const denom = Number(cfg.ancho_cm) * Number(r.consumoCm)
      hojas.push({ tela, archivo, paginas: r.alturasCm.length, consumo_cm: pyRound(Number(r.consumoCm), 1),
                   alturas_cm: r.alturasCm, ancho_cm: pyRound(Number(cfg.ancho_cm), 1),
                   aprovechamiento: denom > 0 ? pyRound(100 * r.area / denom, 1) : 0.0, previews: [],
                   grupo: grupo.nombre, moldes: grupo.nombres })
      validaciones.push(...r.validaciones)
      _rip.push({ archivo, ok: !!(r.rip && r.rip.ok), fallas: (r.rip && r.rip.fallas) || [] })
      _tiempos.hojas.push({ tela, piezas: piezas.length, total: pyRound((performance.now() - _tHoja0) / 1000, 1), ...(r.tiempos || {}) })
    }
  }
  // ── la ficha técnica ──
  let ficha = null, _fichaPaginas = null
  const _tFicha0 = performance.now()
  const mm0 = [...guiasPiezas.values()][0]?.m || null
  try {
    if (!mm0) throw new Error('sin motor abierto')
    decir('Armando la ficha técnica…', 92)
    const guias = await Promise.all(_guiasProm)
    const fecha = new Date()
    const dd = String(fecha.getDate()).padStart(2, '0'), mmx = String(fecha.getMonth() + 1).padStart(2, '0')
    const planilla = plan.planilla_ficha || { columnas: [], filas: plan.prendas }
    const rf = await mm0.pool.enviar('ficha', { titulo: 'Ficha técnica', subtitulo: `${plan.nombres.join(' + ')} · ${dd}/${mmx}/${fecha.getFullYear()}`, planilla, moldesGuia: guias })
    if (rf && rf.pdf) { archivos['FICHA_TECNICA.pdf'] = rf.pdf; ficha = 'FICHA_TECNICA.pdf'; _fichaPaginas = rf.paginas || 1 }
  } catch (e) {
    avisos.push('La ficha técnica no se pudo armar en esta computadora: ' + (e.message || e))
  }
  _tiempos.ficha = (performance.now() - _tFicha0) / 1000
  _tiempos.guia = _tGuia          // lo que tardó dibujar la guía (en paralelo con las hojas)
  // ── el paquete al servidor ──
  decir('Guardando el pedido en el servidor…', 96)
  const _r1 = (x) => pyRound(x, 1)
  const resultado = { hojas, validaciones, duracion_s: pyRound((performance.now() - t0) / 1000, 1), piezas: totalPiezas,
                      avisos, avisos_pedido: avisosPedido, perfil_icc: perfil ? perfil.nombre : null, ficha,
                      ficha_paginas: _fichaPaginas, rip: { hojas: _rip },
                      tiempos: { plan: _r1(_tiempos.plan), piezas: _r1(_tiempos.piezas), hojas: _tiempos.hojas, ficha: _r1(_tiempos.ficha), guia: _r1(_tiempos.guia || 0) } }
  const fd = new FormData()
  fd.append('resultado', JSON.stringify(resultado))
  fd.append('prendas', JSON.stringify(plan.prendas))
  fd.append('nombres', JSON.stringify(plan.nombres))
  fd.append('pids', JSON.stringify(cuerpo.molds || cuerpo.productos || []))
  for (const [nombre, bytes] of Object.entries(archivos)) fd.append(nombre, new Blob([bytes], { type: 'application/pdf' }), nombre)
  const d = await json(rutaApi('/api/paquetes/pedido'), { method: 'POST', body: fd })
  // `archivos`: la pantalla los usa para precalentar el visor sin volver a bajarlos (`precalentarVista`)
  return { id: d.id, resultado: d.resultado, segundos: (performance.now() - t0) / 1000, archivos }
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
  const bytes = await traerConCache(claveDe.mesaPdf(m.pid, mesa, md.sello), rutaApi(urlDe.mesa(m.pid, mesa, 'pdf')))
  await m.pool.enviar('mesa_abrir', { mesa: clave, bytes }, [bytes.buffer])
  m.mesasAbiertas.add(clave)
}

async function indiceDeMesa(m, rutaApi, mesa) {
  m.indices = m.indices || new Map()
  if (!m.indices.has(mesa)) {
    const md = m.info.mesas.find((x) => x.mesa === mesa)
    const bytes = await traerConCache(claveDe.mesaJson(m.pid, mesa, md.sello), rutaApi(urlDe.mesa(m.pid, mesa, 'json')))
    m.indices.set(mesa, JSON.parse(new TextDecoder().decode(bytes)))
  }
  return m.indices.get(mesa)
}

/** Dos moldes en la misma tela: las mesas del segundo se abren también en el hilo del primero. */
async function copiarMesa(desde, hasta, rutaApi, pid, mesa) {
  const clave = `${pid}|${mesa}`
  if (hasta.mesasAbiertas.has(clave)) return
  const md = desde.info.mesas.find((x) => x.mesa === mesa)
  const bytes = await traerConCache(claveDe.mesaPdf(pid, mesa, md.sello), rutaApi(urlDe.mesa(pid, mesa, 'pdf')))
  await hasta.pool.enviar('mesa_abrir', { mesa: clave, bytes }, [bytes.buffer])
  hasta.mesasAbiertas.add(clave)
}

export { cerrarMotores }
