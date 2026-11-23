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

// 🔴 LA IMAGEN DE `fillImage` NO ES PRESTADA: SE SUELTA (2026-11-11, MAPA 814). Medido con el arte
// «base nfl mujer y diablos.ai» (una imagen de 8965 × 6827 px, 120 MB): con `devolver`, cada recorrida
// de una página con un dispositivo propio dejaba la imagen tomada PARA SIEMPRE (≈350 MB que no vuelven
// ni al cerrar el documento ni cuando el navegador limpia) → mapeo + editables + mapeo por nombre
// = 1 GB perdido de los 2 GB del hilo, y la vista previa y la tizada se quedaban sin memoria. El
// envoltorio que llega a `fillImage` trae SU referencia: con `destroy()` en el aviso la memoria vuelve
// al cerrar el documento (10 ciclos: estable) y la página se dibuja idéntica (misma suma de píxeles).
// Los SOMBREADOS siguen por `devolver` (ahí soltar de más rompía, ver arriba) y las máscaras de imagen
// también: no se midieron, y perder una máscara chica es mejor que soltar algo que no es nuestro.

/** Suelta la imagen que el motor le pasó a `fillImage` (usarla ANTES: después ya no sirve). */
export function soltarImagen(obj) {
  try { if (obj && obj.pointer) obj.destroy() } catch { /* nada: en el peor caso queda como antes */ }
}

/** Desanota el envoltorio prestado: el recolector ya no va a liberar lo que no es suyo. */
export function devolver(obj) {
  try {
    if (!obj || !obj.pointer) return
    const reg = obj.constructor && obj.constructor._finalizer
    if (reg) reg.unregister(obj)
    obj.pointer = 0
  } catch { /* nada: en el peor caso queda como antes */ }
}
