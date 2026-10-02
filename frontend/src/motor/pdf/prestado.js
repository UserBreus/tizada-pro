// LO QUE MuPDF LE PRESTA A UN DISPOSITIVO NO SE LIBERA — 2026-10-01.
//
// 🔴 POR QUÉ: mupdf.js 1.26.4 avisa de un sombreado o de una imagen con `new Shade(puntero)` /
// `new Image(puntero)` SIN pedir su propia referencia (para trazados, textos y colores sí hace
// `_wasm_keep_…`). El envoltorio queda anotado para liberarse cuando el recolector de basura lo
// junte, y entonces suelta una referencia que nunca tuvo: el sombreado/la imagen se libera
// mientras el documento lo sigue usando, o dos veces. Lo que se ve es un error suelto, mucho
// después y en cualquier lado: «RuntimeError: null function or function signature mismatch»
// (en `fz_drop_colorspace` / `fz_drop_icc_link`) o memoria rota en el hilo del motor.
// Medido con el arte «CAMISETA NEGRO 2» (33 degradados con perfil ICC en una mesa): armar los
// editables y forzar el recolector reventaba SIEMPRE; con esto, nunca.
//
// Basta con que el dispositivo DEFINA el aviso (aunque no use el argumento): mupdf.js crea el
// envoltorio igual. Por eso todo dispositivo propio con `fillShade`, `fillImage`,
// `fillImageMask` o `clipImageMask` tiene que pasar su argumento por `devolver` (usarlo antes).
//
// ⚠️ Al actualizar mupdf.js: si esos cuatro avisos pasan a hacer `_wasm_keep_…`, esto deja de
// hacer falta (y dejaría una referencia sin soltar por objeto: sacarlo).

/** Desanota el envoltorio prestado: el recolector ya no va a liberar lo que no es suyo. */
export function devolver(obj) {
  try {
    if (!obj || !obj.pointer) return
    const reg = obj.constructor && obj.constructor._finalizer
    if (reg) reg.unregister(obj)
    obj.pointer = 0
  } catch { /* nada: en el peor caso queda como antes */ }
}
