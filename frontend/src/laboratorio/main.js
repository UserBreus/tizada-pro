// LABORATORIO «lo pesado en el navegador» (PLAN_NAVEGADOR.md, etapa 0). Abre un molde EN ESTA
// COMPUTADORA y compara con la referencia del servidor (`py laboratorio_navegador.py molde.ai`):
// por mesa, cuántos dibujos, los bytes del contenido (SHA-1) y cuántas instrucciones. Informa
// tiempo, memoria de WebAssembly y el equipo. Nada viaja al servidor.
const $ = (id) => document.getElementById(id)
const salida = $('salida')
let molde = null
let ref = null

function escribir(txt, clase) {
  salida.textContent = txt
  salida.className = clase || ''
}
function listo() { $('ir').disabled = !molde }
$('molde').onchange = (e) => { molde = e.target.files[0] || null; listo() }
$('ref').onchange = async (e) => {
  const f = e.target.files[0]
  ref = f ? JSON.parse(await f.text()) : null
}

const MB = (b) => (b / 1048576).toFixed(0) + ' MB'

function informe(nav, ref) {
  const l = []
  let fallas = 0
  l.push(`archivo: ${molde.name || ref?.archivo || ''} (${MB(nav.bytes)}) · total ${nav.segundos.toFixed(1)} s · memoria WebAssembly pico ${nav.memoria_wasm ? MB(nav.memoria_wasm) : '¿?'}`)
  l.push(`equipo: ${nav.nucleos ?? '¿?'} núcleos · ${nav.memoria_equipo_gb ?? '¿?'} GB (según el navegador) · ${nav.navegador}`)
  if (ref) l.push(`referencia del servidor: PyMuPDF ${ref.pymupdf} (MuPDF ${ref.mupdf})`)
  for (const m of nav.mesas) {
    const r = ref?.mesas?.[m.mesa - 1]
    let marca = ''
    if (r) {
      const ok = r.dibujos === m.dibujos && r.sha1 === m.sha1 && r.instrucciones === m.instrucciones
      if (!ok) fallas++
      marca = ok ? '✓ ' : '✗ '
    }
    l.push(`${marca}mesa ${m.mesa}: ${m.dibujos} dibujos en ${m.segundos_dibujos.toFixed(2)} s · ${MB(m.bytes)} de contenido, ${m.instrucciones} instrucciones en ${m.segundos_instrucciones.toFixed(2)} s` +
      (r && r.dibujos !== m.dibujos ? ` · servidor ${r.dibujos} dibujos` : '') +
      (r && r.sha1 !== m.sha1 ? ' · BYTES DISTINTOS' : '') +
      (r && r.instrucciones !== m.instrucciones ? ` · servidor ${r.instrucciones} instrucciones` : ''))
  }
  if (ref) l.unshift(fallas ? `✗ ${fallas} mesa(s) distintas del servidor` : '✓ IGUAL AL SERVIDOR en todas las mesas')
  return { texto: l.join('\n'), ok: !fallas }
}

async function correr() {
  $('ir').disabled = true
  escribir('Leyendo el archivo…', 'gris')
  const bytes = new Uint8Array(await molde.arrayBuffer())
  const worker = new Worker(new URL('./worker.js', import.meta.url), { type: 'module' })
  const t0 = performance.now()
  worker.onmessage = (ev) => {
    const d = ev.data
    if (d.avance) { escribir(`${((performance.now() - t0) / 1000).toFixed(1)} s · ${d.avance}`, 'gris'); return }
    if (d.error) { escribir('✗ ' + d.error, 'mal'); worker.terminate(); $('ir').disabled = false; return }
    const { texto, ok } = informe(d.listo, ref)
    escribir(texto, ref ? (ok ? 'ok' : 'mal') : '')
    window.__laboratorio = { resultado: d.listo, ok, texto }
    worker.terminate()
    $('ir').disabled = false
  }
  worker.onerror = (e) => { escribir('✗ el worker falló: ' + e.message, 'mal'); $('ir').disabled = false }
  worker.postMessage({ bytes }, [bytes.buffer])
}
$('ir').onclick = correr

// Modo automático: ?molde=<url>&ref=<url>
const q = new URLSearchParams(location.search)
if (q.get('molde')) {
  ;(async () => {
    escribir('Bajando los archivos de prueba…', 'gris')
    const r = await fetch(q.get('molde'))
    molde = new File([await r.blob()], decodeURIComponent(q.get('molde').split('/').pop()))
    if (q.get('ref')) ref = await (await fetch(q.get('ref'))).json()
    correr()
  })()
}

// ── LABORATORIO 2: la VISTA (PLAN_NAVEGADOR.md, etapa 2) ─────────────────────────────────────
// Dibuja una hoja de tizada acá mismo, con el mismo motor que usa la pantalla del paso Tizada, y
// muestra la huella del PNG: tiene que ser la misma que la del contrato en Node (y ese, píxel a
// píxel, la del servidor).
import { abrirVista } from '../motor/vista/vista.js'
import { sha1HexBytes } from '../motor/sha1.js'

let hoja = null
const $2 = (id) => document.getElementById(id)
$2('hoja').onchange = (e) => { hoja = e.target.files[0] || null; $2('dibujar').disabled = !hoja }
$2('dibujar').onclick = async () => {
  const s2 = $2('salida2'), lienzo = $2('lienzo')
  $2('dibujar').disabled = true
  s2.className = 'gris'
  s2.textContent = 'Abriendo la hoja…'
  lienzo.innerHTML = ''
  try {
    const bytes = new Uint8Array(await hoja.arrayBuffer())
    const t0 = performance.now()
    const v = await abrirVista('lab|' + hoja.name + '|' + bytes.length, async () => bytes.buffer)
    if (!v) throw new Error('este navegador no puede dibujar la vista')
    const l = [`hoja: ${hoja.name} (${(bytes.length / 1048576).toFixed(1)} MB) · abierta en ${((performance.now() - t0) / 1000).toFixed(1)} s`]
    const casos = [{ ancho: 1200, recorte: null }, { ancho: 800, recorte: [0, 0, 0.5, 0.5] }]
    const salida = []
    for (const c of casos) {
      const t = performance.now()
      const url = await v.dibujo(0, c.ancho, c.recorte)
      const seg = (performance.now() - t) / 1000
      const png = new Uint8Array(await (await fetch(url)).arrayBuffer())
      const img = new Image()
      img.src = url
      img.style.maxWidth = '380px'
      img.style.background = '#fff'
      lienzo.appendChild(img)
      const huella = sha1HexBytes(png)
      salida.push({ ancho: c.ancho, recorte: c.recorte, bytes: png.length, sha1: huella, segundos: seg })
      l.push(`${c.recorte ? 'recorte' : 'mesa entera'} a ${c.ancho} px: ${png.length} bytes de PNG · sha1 ${huella} · ${seg.toFixed(2)} s`)
    }
    window.__vista = { hoja: hoja.name, casos: salida }
    s2.textContent = l.join('\n')
    s2.className = 'ok'
  } catch (err) {
    s2.textContent = '✗ ' + (err.message || err)
    s2.className = 'mal'
  }
  $2('dibujar').disabled = false
}
