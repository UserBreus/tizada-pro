// GUARDAR UN PDF DEL MOTOR SOLTANDO SU MEMORIA EN EL ACTO (MAPA 811).
//
// `doc.saveToBuffer()` de mupdf.js devuelve un `Buffer` que vive en la memoria del motor (el heap
// del wasm, con tope de 2 GB por hilo) y que sólo se libera cuando el navegador decide limpiar
// objetos de JavaScript (FinalizationRegistry). El navegador no ve esa memoria —para él el `Buffer`
// es un objeto chiquito— así que no apura la limpieza: con un arte de 239 MB que trae una imagen de
// 120 MB (8965 × 6827 px, «base nfl mujer y diablos.ai»), cada pieza o hoja guardada dejaba ~240 MB
// colgados y a la 5ª el hilo se quedaba sin memoria («realloc (163443015 bytes) failed»): la
// tizada fallaba en la PC, caía al servidor y el servidor no calcula → «la tizada la genera tu
// computadora: recargá la página». Medido sobre una copia: soltándolo acá la memoria queda plana.
//
// Los bytes que devuelve son EXACTAMENTE los de `saveToBuffer(opciones).asUint8Array().slice()`:
// sólo cambia cuándo se devuelve la memoria.

/** `doc.saveToBuffer(opciones)` → `Uint8Array` propio, soltando el buffer del motor en el acto. */
export function guardarPdf(doc, opciones = '') {
  const b = doc.saveToBuffer(opciones)
  try {
    return b.asUint8Array().slice()
  } finally {
    try { b.destroy() } catch { /* ya liberado */ }
  }
}
