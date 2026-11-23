// node frontend/src/motor/pruebas/arte_en_pc.mjs <base> <pid> <arteA.ai> <arteB.ai>
// EL ARTE DEL PEDIDO VIVE EN LA PC (MAPA 760-761) — lo corre `verificar_arte_en_pc.py` contra su servidor aislado.
//
// Dos pedidos (A y B) en la MISMA computadora, mismo molde y mismo diseño «JUGADOR», artes distintos; la carpeta del
// servidor tiene OTRO arte de «jugador» (el de B: el caso del cruce, MAPA 758). Cada pedido tiene que leer SU arte en
// todo: motor, detección, objetos agregados, versión nueva, plan del servidor (`artes_pc`) — y «Nuevo pedido» suelta
// sólo lo del otro. `arte/enPc.js` se usa TAL CUAL: sólo se cambian sus dos importaciones que tocan el navegador
// (IndexedDB y el hilo) por dobles en memoria.
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import crypto from 'node:crypto'
import { fileURLToPath, pathToFileURL } from 'node:url'
import * as mupdf from 'mupdf'
import { prepararArte } from '../arte/preparar.js'

const [, , BASE, PID, rutaA, rutaB] = process.argv
const AQUI = path.dirname(fileURLToPath(import.meta.url))
const MOTOR = path.resolve(AQUI, '..')
const u = (p) => pathToFileURL(path.join(MOTOR, p)).href

// ── enPc.js con sus dos dependencias del navegador cambiadas por dobles ──────────────────────────────────────
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'arte_en_pc_'))
fs.writeFileSync(path.join(tmp, 'cache.mjs'), `
export const DB = new Map()
const _s = (sello) => (sello || []).join(',')
export const claveDe = { arte: (pid, diseno, sello) => \`arte|\${pid}|\${diseno || 'principal'}|\${_s(sello)}\` }
export async function leerCache(k) { const b = DB.get(k); return b ? b.slice() : null }
export async function tieneCache(k) { return DB.has(k) }
export async function guardarCache(k, b) { DB.set(k, new Uint8Array(b).slice()) }
export async function clavesCache() { return [...DB.keys()] }
export async function borrarCache(ks) { for (const k of ks) DB.delete(k) }
`)
fs.writeFileSync(path.join(tmp, 'hilo.mjs'), `
import * as mupdf from ${JSON.stringify(pathToFileURL(fileURLToPath(import.meta.resolve('mupdf'))).href)}
import { aTextoJSON } from ${JSON.stringify(u('molde/caminoA.js'))}
export async function enHiloSuelto(tipo, { bytes, fn, args = {} }) {
  let r
  if (fn === 'arte_editables') r = (await import(${JSON.stringify(u('arte/editables.js'))})).extraerEditables(mupdf, bytes)
  else if (fn === 'arte_mapeo_variantes') r = (await import(${JSON.stringify(u('arte/mapeo.js'))})).mapeoVariantesArte(mupdf, bytes, args.registro || {}, args.orden || [])
  else if (fn === 'arte_perfil') r = (await import(${JSON.stringify(u('arte/perfil.js'))})).detectarPerfilIncrustado(mupdf, bytes)
  else throw new Error(tipo + ' ' + fn)
  return aTextoJSON(r)
}
`)
const fuente = fs.readFileSync(path.join(MOTOR, 'arte', 'enPc.js'), 'utf-8')
  .replace("'../cache.js'", "'./cache.mjs'").replace("'../hiloSuelto.js'", "'./hilo.mjs'")
  .replace("'../pieza/estampar.js'", JSON.stringify(u('pieza/estampar.js')))
  .replace("'./motorB.js'", JSON.stringify(u('arte/motorB.js')))
fs.writeFileSync(path.join(tmp, 'enPc.mjs'), fuente)
const E = await import(pathToFileURL(path.join(tmp, 'enPc.mjs')).href)
const { DB, claveDe } = await import(pathToFileURL(path.join(tmp, 'cache.mjs')).href)

const DIS = 'jugador'
const api = (p) => BASE + p
const j = async (p, o) => { const r = await fetch(api(p), o); const t = await r.text(); if (!r.ok) throw new Error(`${p} ${r.status} ${t.slice(0, 300)}`); return JSON.parse(t) }
const sha = (b) => crypto.createHash('sha1').update(b).digest('hex')
const res = { checks: [] }
const ok = (c, m) => { res.checks.push([!!c, m]); console.log((c ? '  ✓ ' : '  ✗ ') + m) }

try {
  const ctx = await j(`/api/productos/${PID}/arte_contexto`)
  const plantilla = ctx.plantilla_sello ? new Uint8Array(await (await fetch(api(`/api/productos/${PID}/descargar_plantilla?cual=vigente`))).arrayBuffer()) : null
  const prep = (b) => prepararArte(mupdf, b.slice(), { ...ctx, diseno: DIS, plantilla, manual: null })
  const A = new Uint8Array(fs.readFileSync(rutaA)), B = new Uint8Array(fs.readFileSync(rutaB))
  const pA = prep(A), pB = prep(B)
  const datos = (p, nom) => ({ det: p.det, auto: p.auto, pers: p.pers, mapeo: p.mapeo, pv: p.pv, validacion: { ...p.validacion, archivo: nom, modo: p.modo } })
  // la carpeta del servidor tiene el arte de B (el caso del cruce) y el servidor YA NO LO ENTREGA (MAPA 771): ni el
  // archivo, ni el diseño en /motor_b, ni sus objetos, ni su detección
  ok(pA.sha1 !== pB.sha1, 'dos artes distintos')
  const rSrv = await fetch(api(`/api/productos/${PID}/arte_archivo?diseno=${DIS}`))
  ok(rSrv.status === 404, `el servidor no entrega el arte de la carpeta compartida (arte_archivo → ${rSrv.status})`)
  const mbSrv = await j(`/api/productos/${PID}/motor_b`)
  ok(!(mbSrv.disenos || []).some((d) => d.id === DIS) && (mbSrv.cfg_disenos || {})[DIS], '/motor_b no lista el diseño de la carpeta compartida (su config sí)')
  ok(!(mbSrv.disenos || []).some((d) => d.id === 'x-prueba-jugador'), '/motor_b no lista el `x-…` de un pedido del otro sistema')
  const rX = await fetch(api(`/api/productos/${PID}/arte_archivo?diseno=x-prueba-jugador`))
  ok(rX.status === 404, `el arte del \`x-…\` no se entrega a una persona (${rX.status})`)
  const rDet = await fetch(api(`/api/arte/deteccion?diseno=${DIS}&pid=${PID}`))
  ok(rDet.status === 409, `la detección completa de la carpeta compartida tampoco (${rDet.status})`)
  // y /motor_b se puede revalidar: si no cambió, 304 sin cuerpo (se pide en cada talle que se dibuja)
  const r1 = await fetch(api(`/api/productos/${PID}/motor_b`)), et = r1.headers.get('etag'); const b1 = await r1.json()
  const r2 = await fetch(api(`/api/productos/${PID}/motor_b`), { headers: { 'If-None-Match': et || '' } })
  let dif = ''
  if (r2.status === 200) { const b2 = await r2.json(); dif = Object.keys(b1).filter((k) => JSON.stringify(b1[k]) !== JSON.stringify(b2[k])).join(',') }
  ok(et && r2.status === 304, `/motor_b revalidable: ETag y 304 si no cambió (${r2.status}${dif ? ' · cambia: ' + dif : ''}${et ? '' : ' · sin ETag'})`)
  E.fijarPedidoPc('A'); await E.guardarArtePc({ pid: PID, diseno: DIS, nombre: 'JUGADOR', bytes: A, sha1: pA.sha1, datos: datos(pA, 'a.ai') })
  E.fijarPedidoPc('B'); await E.guardarArtePc({ pid: PID, diseno: DIS, nombre: 'JUGADOR', bytes: B, sha1: pB.sha1, datos: datos(pB, 'b.ai') })
  const objPdf = A.slice(0, 1024)          // el contenido del objeto no importa acá: se guarda y se copia tal cual
  const planes = {}
  for (const [ped, p, otro] of [['A', pA, pB], ['B', pB, pA]]) {
    console.log(`pedido ${ped}:`)
    E.fijarPedidoPc(ped)
    const mb = await j(`/api/productos/${PID}/motor_b`)
    ok(mb.cfg_disenos && mb.cfg_disenos[DIS] && 'editables_cfg' in mb.cfg_disenos[DIS], '/motor_b manda la config de cada diseño (cfg_disenos)')
    const d = (await E.aplicarArtesPc(mb, PID)).disenos.find((x) => x.id === DIS)
    ok(d && d.en_pc && d.sello.join(',') === ['pc', ped, p.sha1, 0].join(','), `motor: sello de SU arte (${d && d.sello.join(',').slice(0, 24)}…)`)
    ok(sha(DB.get(claveDe.arte(PID, DIS, d.sello))) === p.sha1, 'motor: los bytes que lee son los de SU arte')
    ok(JSON.stringify(d.mapeo.mapeo) === JSON.stringify(p.mapeo) && d.validacion.modo === p.modo, 'motor: su mapeo y su validación')
    const det = await E.deteccionPc({ pid: PID, diseno: DIS, variante: '', rutaApi: api })
    ok(det && det.mesas.length === p.det.mesas.length && det.firma_pc === d.sello.join(',') && det.validacion,
       `detección: SUS ${det && det.mesas.length} mesas, firma = sello en la PC`)
    if (p.det.mesas[0].thumb !== otro.det.mesas[0].thumb) ok(det.mesas[0].thumb === p.det.mesas[0].thumb, 'detección: no es la del otro pedido')
    // objetos agregados
    const o1 = await E.objetoAgregarPc(PID, DIS, { pdf: objPdf, nombre: `escudo ${ped}`, w_cm: 5.123, h_cm: 4 })
    ok(o1.id === 'oa_1' && o1.archivo === `pc,${ped},oa_1.pdf` && o1.w_cm === 5.12, `objeto agregado ${o1.id} (${o1.archivo})`)
    await E.objetoTransformPc(PID, DIS, o1.id, { variante: 'v1', talles: ['M'], transform: { dx: 1, scale: 50, sx: -0.01 }, pieza: 'Frente' })
    const o2 = await E.objetoDuplicarPc(PID, DIS, o1.id)
    ok(o2.id === 'oa_2' && o2.nombre === `escudo ${ped} (copia)` && o2.pieza === '' && o2.transforms.v1.M.scale === 20 && o2.transforms.v1.M.sx === -0.05,
       'duplicar: sin pieza, transform acotado como `_clamp_tf`')
    await E.objetoColocadoPc(PID, DIS, o1.id, { capa: 'Editable escudo', pieza: 'Frente', mesas: [1] })
    const d2 = (await E.aplicarArtesPc(await j(`/api/productos/${PID}/motor_b`), PID)).disenos.find((x) => x.id === DIS)
    ok(d2.objetos.length === 1 && d2.objetos[0].id === 'oa_2' && d2.inyectadas.includes('Editable escudo')
       && DB.has(`oa|${PID}|${DIS}|oa_2|pc,${ped},oa_2.pdf`) && !DB.has(`oa|${PID}|${DIS}|oa_1|pc,${ped},oa_1.pdf`),
       'colocar: el objeto pasa al arte y queda anotada su capa')
    ok((await E.objetoAgregarPc(PID, DIS, { pdf: objPdf, nombre: 'x', w_cm: 1, h_cm: 1 })).id === 'oa_3', 'el número de objeto no se reusa')
    await E.objetoBorrarPc(PID, DIS, 'oa_3')
    // versión nueva («Editar diseño») y original
    await E.versionNuevaPc(PID, DIS, A.slice())
    const m1 = await E.artePc(PID, DIS)
    ok(m1.version === 1 && !DB.has(claveDe.arte(PID, DIS, ['pc', ped, p.sha1, 0])) && sha(await E.originalPc(PID, DIS)) === p.sha1,
       'versión nueva: la vigente sube, la vieja se suelta, el original queda')
    planes[ped] = await E.datosPlanPc([PID], api)
    const x = (planes[ped][DIS] || {})[PID]
    ok(x && JSON.stringify(x.pers) === JSON.stringify(p.pers) && x.perfil && 'tiene' in x.perfil && x.objetos.length === 1, 'plan: su personalización, perfil y objetos')
    ok(x && x.mapeo_variantes && typeof x.mapeo_variantes === 'object', 'plan: su mapeo por talle (la ficha no lo pide sobre la carpeta del servidor)')
  }
  // el plan del SERVIDOR con lo que manda cada PC (la carpeta tiene el arte de B)
  const reg = (await j(`/api/productos/${PID}/motor_b`)).registro
  const talle = Object.keys(Object.values(reg)[0]).sort()[0]
  const fuenteDe = (p) => Object.values(Object.values(p.pers || {})[0] || {})[0]?.fuente
  for (const [ped, p, otro] of [['A', pA, pB], ['B', pB, pA]]) {
    const c ={ molds: [PID], default_diseno: DIS, moldes_por_diseno: { [DIS]: [PID] }, artes_pc: planes[ped],
                prendas: [{ talle, nombre: 'PEREZ', numero: '10', diseno: 'JUGADOR' }] }
    const r = await fetch(api('/api/pedido/plan'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(c) })
    const t = await r.text()
    const mol = r.ok ? (JSON.parse(t).moldes || [])[0] : null
    ok(r.ok && mol && mol.mapeo_arte, `plan ${ped} del servidor: ${r.status}${r.ok ? '' : ' · ' + t.slice(0, 200)}`)
    if (mol) {
      // (sin el catálogo de tipografías del molde: ahí están las de los dos artes)
      const { fuentes, ...resto } = mol, s = JSON.stringify(resto)
      ok(s.includes(`"${fuenteDe(p)}"`) && (fuenteDe(p) === fuenteDe(otro) || !s.includes(`"${fuenteDe(otro)}"`)),
         `plan ${ped}: la personalización de SU arte (${fuenteDe(p)})`)
    }
  }
  // un pedido de la PC SIN el arte de ese diseño: el plan no usa el de la carpeta (es el de otra persona, MAPA 770)
  {
    const c = { molds: [PID], default_diseno: DIS, moldes_por_diseno: { [DIS]: [PID] }, artes_pc: {},
                prendas: [{ talle, nombre: 'PEREZ', numero: '10', diseno: 'JUGADOR' }] }
    const r = await fetch(api('/api/pedido/plan'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(c) })
    const t = await r.text()
    const mol = r.ok ? (JSON.parse(t).moldes || [])[0] : null
    ok(!r.ok || !mol || !mol.mapeo_arte, `plan sin el arte en la PC: no toma el de la carpeta del servidor ni el \`x-…\` de otro pedido (${r.status}${r.ok ? '' : ' ' + t.slice(0, 120)})`)
    ok(!t.includes('x-prueba-jugador'), 'el plan ni nombra el `x-…` de otro pedido (ni para calcularlo)')
  }
  // el perfil: el servidor compara lo que leyó la PC, sin abrir su archivo
  const pf = await j(`/api/arte/perfil?diseno=${DIS}&pid=${PID}&det=${encodeURIComponent(JSON.stringify({ tiene: true, nombre: 'Perfil de prueba', espacio: 'CMYK' }))}`)
  ok(pf.estado === 'distinto' && pf.incrustado === 'Perfil de prueba', '/api/arte/perfil?det= compara lo que leyó la PC')
  // el mapeo FIJO del molde (config del molde): merge
  const fijo = async () => (await j(`/api/arte/deteccion?solo_molde=1&diseno=${DIS}&pid=${PID}`)).mapeo_fijo || {}
  const antes = await fijo()
  const pieza = Object.keys(reg)[0]
  await j('/api/arte/mapeo_fijo', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pid: PID, mapeo: { [pieza]: 2 } }) })
  const despues = await fijo()
  ok(despues[pieza] === 2 && Object.keys(despues).length >= Object.keys(antes).length, '/api/arte/mapeo_fijo suma al mapeo fijo del molde')
  // sin los bytes en la PC, el arte NO se marca (si no, se bajaría el del servidor)
  E.fijarPedidoPc('B')
  const mB = await E.artePc(PID, DIS)
  const kB = claveDe.arte(PID, DIS, ['pc', 'B', mB.sha1, mB.version]), bB = DB.get(kB)
  DB.delete(kB)
  const dSin = (await E.aplicarArtesPc(await j(`/api/productos/${PID}/motor_b`), PID)).disenos.find((x) => x.id === DIS)
  ok(!dSin && !(await E.deteccionPc({ pid: PID, diseno: DIS, rutaApi: api })), 'sin los bytes en la PC no se marca «en la PC» ni queda el de la carpeta del servidor')
  // un diseño que NO está en la PC tampoco viene de la carpeta del servidor (MAPA 770): antes de cargar el arte se
  // veían las tipografías del arte de otra persona
  E.fijarPedidoPc('C')
  const dC = (await E.aplicarArtesPc(await j(`/api/productos/${PID}/motor_b`), PID)).disenos.find((x) => x.id === DIS)
  ok(!dC, 'pedido sin arte cargado: el diseño de la carpeta del servidor NO aparece')
  DB.set(kB, bB)
  // «Nuevo pedido» en A: se van los artes (y objetos) de B; los de A quedan; nada de otros módulos
  DB.set('plantilla-vigente|otro|pc,abc,1', new Uint8Array(1))
  // con OTRA pestaña abierta (su pedido en el conjunto, MAPA 762) no se toca nada de ella
  const antesDeSoltar = DB.size
  E.fijarPedidoPc('A'); await E.soltarArtesPc(new Set(['A', 'B']))
  ok(DB.size === antesDeSoltar, 'soltarArtesPc con el pedido de otra pestaña: no borra nada de ella')
  E.fijarPedidoPc('A'); await E.soltarArtesPc('A')
  const ks = [...DB.keys()]
  ok(ks.every((k) => !k.includes('pc,B')) && ks.some((k) => k.startsWith('oa|') && k.includes('|pc,A,')) && ks.includes('plantilla-vigente|otro|pc,abc,1'),
     'soltarArtesPc: se va lo del otro pedido (artes y objetos), queda lo de A y lo de los moldes')
} catch (e) {
  ok(false, 'error: ' + (e && e.stack || e))
} finally {
  fs.rmSync(tmp, { recursive: true, force: true })
}
const mal = res.checks.filter((c) => !c[0]).length
console.log(mal ? `✗ ${mal} falla(s)` : '✓ todo bien')
process.exit(mal ? 1 : 0)
