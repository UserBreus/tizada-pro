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
