// node frontend/src/motor/pruebas/fuentes_pc.mjs <carpeta_fuentes>
// MAPA 670: las tipografías de ESTA PC (`texto/fuentesPc.js`) con un navegador simulado: `queryLocalFonts`
// devuelve tipografías REALES de la carpeta (como las daría Chrome) y el permiso se puede dar o no.
// Imprime un JSON en la última línea; lo mira `verificar_fuente_ya_existe.py` §9.
import fs from 'node:fs'
import path from 'node:path'

const carpeta = process.argv[2]
const archivos = fs.readdirSync(carpeta).filter((a) => /\.(ttf|otf)$/i.test(a))
const { nombresFuente, nombreInternoMupdf } = await import('../texto/fuentes.js')
const instaladas = archivos.map((a) => {
  const b = new Uint8Array(fs.readFileSync(path.join(carpeta, a)))
  const n = nombresFuente(b)
  return { postscriptName: n.ps, fullName: n.completo, family: n.familia, style: n.estilo,
           blob: async () => ({ arrayBuffer: async () => b.slice().buffer }) }
})
let permiso = 'prompt', pedidas = 0
globalThis.window = { queryLocalFonts: async () => { pedidas++; if (permiso !== 'granted') throw new Error('sin permiso'); return instaladas } }
Object.defineProperty(globalThis, 'navigator', { value: { permissions: { query: async () => ({ state: permiso }) } }, configurable: true, writable: true })

const P = await import('../texto/fuentesPc.js')
const { resolverFuente } = await import('../texto/fuentes.js')
const out = {}
// el catálogo «subido» tiene Anton; el diseño pide Graduate (sólo en la PC) y Anton (subida)
const anton = archivos.find((a) => /^Anton/i.test(a))
const bA = new Uint8Array(fs.readFileSync(path.join(carpeta, anton)))
const subidas = [{ interno: nombreInternoMupdf(bA), archivo: anton, hash: 'x', ...(() => { const n = nombresFuente(bA); return { completo: n.completo, ps: n.ps } })() }]
const pers = { 1: { nombre: { fuente: 'Graduate-Regular' }, numero: { fuente: 'Anton-Regular' } } }

// 1) SIN permiso: nada cambia y NO se pregunta solo
out.sinPermiso = { lista: (await P.listarPc()).length, catalogo: (await P.catalogoConPc(subidas)).length, preguntas: pedidas }
// 2) con el permiso pedido desde un clic
permiso = 'granted'
out.conPermiso = { lista: (await P.listarPc({ pedir: true })).length }
const cat = await P.catalogoConPc(subidas)
out.conPermiso.catalogo = cat.length
out.conPermiso.antonGanaLaSubida = (resolverFuente('Anton-Regular', cat, {}) || {}).archivo === anton
const g = resolverFuente('Graduate-Regular', cat, {})
out.conPermiso.graduateDeLaPc = !!(g && g.pc)
const r = await P.fuentesConPc({ catalogo: subidas, alias: {} }, P.fuentesDePers(pers))
const e = r.catalogo.find((x) => x.pc)
const bG = new Uint8Array(fs.readFileSync(path.join(carpeta, archivos.find((a) => /^Graduate/i.test(a)))))
out.estampar = { suma: r.catalogo.length - subidas.length, interno: e && e.interno, internoEsperado: nombreInternoMupdf(bG),
                 bytesIguales: !!(e && r.pc.get(e.archivo) && r.pc.get(e.archivo).length === bG.length && r.pc.get(e.archivo).every((v, i) => v === bG[i])),
                 sinNecesidadNoSuma: (await P.fuentesConPc({ catalogo: subidas, alias: {} }, ['Anton-Regular'])).catalogo.length === subidas.length }
// 3) (MAPA 672) una COLECCIÓN de Windows (.ttc): se arma el archivo suelto de la cara pedida y el estampado lo lee
const ttc = 'C:/Windows/Fonts/cambria.ttc'
if (fs.existsSync(ttc)) {
  const { soloEsaCara, extensionDe } = P
  const { FuenteCurvas } = await import('../texto/curvas.js')
  const b = new Uint8Array(fs.readFileSync(ttc))
  const cara = soloEsaCara(b, 'CambriaMath')
  let glifos = 0
  try { glifos = new FuenteCurvas(cara).numGlyphs } catch { glifos = -1 }
  out.coleccion = { ps: nombresFuente(cara).ps, interno: nombreInternoMupdf(cara), ext: extensionDe(cara), glifos,
                    sueltaIgual: soloEsaCara(bA, 'Anton-Regular') === bA }
}
// 4) el permiso se pide al PRIMER CLIC de la página (y nunca sin un clic). Si ese intento falla por otra cosa
//    (la pestaña no estaba visible: medido en Chrome 2026-10-12) se vuelve a probar en el próximo clic; si la
//    persona cierra el cartel, no se insiste
{
  const unClic = async (oyentes) => { oyentes.slice().forEach((fn) => fn()); await new Promise((r) => setTimeout(r, 20)) }
  const armar = async (tag) => {
    const oyentes = []
    globalThis.document = { addEventListener: (t, fn) => oyentes.push(fn), removeEventListener: (t, fn) => { const i = oyentes.indexOf(fn); if (i >= 0) oyentes.splice(i, 1) } }
    const M = await import('../texto/fuentesPc.js?' + tag)   // otra copia del módulo: sin la lista ya leída
    return { oyentes, M }
  }
  let modo = 'oculta'
  permiso = 'prompt'
  globalThis.window.queryLocalFonts = async () => {
    pedidas++
    if (permiso === 'granted') return instaladas
    if (modo === 'oculta') { const e = new Error('Page needs to be visible.'); e.name = 'SecurityError'; throw e }
    if (modo === 'cierra') { const e = new Error('cerrado'); e.name = 'NotAllowedError'; throw e }
    permiso = 'granted'; return instaladas
  }
  const A = await armar('primer-clic')
  const antes = pedidas
  A.M.pedirAlPrimerClic()
  const sinClic = pedidas - antes
  await unClic(A.oyentes)
  const tras1 = { pedidas: pedidas - antes, oyentes: A.oyentes.length }
  modo = 'concede'
  await unClic(A.oyentes)
  out.primerClic = { sinClic, tras1, concedido: permiso === 'granted', quedanOyentes: A.oyentes.length, lista: (await A.M.listarPc()).length }
  permiso = 'prompt'; modo = 'cierra'
  const B = await armar('cierra')
  B.M.pedirAlPrimerClic()
  await unClic(B.oyentes)
  out.primerClic.cerroNoInsiste = B.oyentes.length === 0
}
console.log(JSON.stringify(out))
