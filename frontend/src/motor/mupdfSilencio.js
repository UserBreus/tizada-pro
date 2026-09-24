// LOS AVISOS DE MUPDF, SIN INUNDAR LA CONSOLA — 2026-09-23.
//
// Al leer un arte de Illustrator, mupdf avisa cosas de la ESTRUCTURA del archivo («invalid marked
// content and clip nesting», «non-page object in page tree», «Page tree load failed. Falling back
// to slow lookup»). No son errores: el archivo se lee bien igual. Pero mupdf los imprime UNO POR
// UNO y con un arte real salieron más de 9.000 (captura del usuario), cada uno con su pila en la
// consola: eso sí pone lenta la pantalla. No se van actualizando nada: vienen de los archivos.
//
// Emscripten toma su salida de `globalThis.$libmupdf_wasm_Module` (lo lee `mupdf.js` al cargarse),
// así que esto tiene que correr ANTES del `import('mupdf')` de cada hilo:
//   · las líneas «warning: …» se cuentan y no se imprimen;
//   · el resto (lo que mupdf marca como error) se imprime UNA vez cada mensaje distinto.
let _avisos = 0
const _vistos = new Set()

export function silenciarAvisosMupdf() {
  const g = globalThis
  const mod = (g.$libmupdf_wasm_Module = g.$libmupdf_wasm_Module || {})
  if (mod.__silencio) return
  mod.__silencio = true
  mod.printErr = (t) => {
    const s = String(t)
    if (/^\s*warning:/i.test(s)) { _avisos++; return }
    if (_vistos.has(s) || _vistos.size > 100) return
    _vistos.add(s)
    console.warn('[mupdf] ' + s)
  }
}

/** Cuántos avisos de mupdf se callaron en este hilo. */
export function avisosMupdfCallados() { return _avisos }
