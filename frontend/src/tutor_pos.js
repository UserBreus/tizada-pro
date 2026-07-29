/**
 * DÓNDE SE PONE EL GLOBO DE LA AYUDA — función pura, aparte del motor para poder TESTEARLA.
 *
 * La regla es una sola y no se negocia: **el globo NUNCA puede taparle a la persona el control que
 * le estamos pidiendo que toque.** Si lo tapa, la ayuda deja de ayudar.
 *
 * Antes esto se resolvía suponiendo que el globo medía 200 px de alto. Con un texto largo (o con la
 * nota, o con el botón de escape) mide bastante más: no entraba abajo, se lo mandaba arriba y
 * terminaba **encima del botón** — justo en la barra inferior del pedido, que es donde viven
 * «Cargar el arte», «A la planilla» y «Enviar».
 *
 * Orden de preferencia: DEBAJO (lo natural: leo y después toco) → ARRIBA → AL COSTADO → y si la
 * pantalla es tan chica que no hay lugar en ningún lado, el lado con más aire, pegado al borde.
 */

/**
 * @param {{x,y,w,h}|null} rect  caja del elemento a resaltar (null = todavía no se encontró)
 * @param {{w,h}} tam            tamaño REAL del globo (medido, no supuesto)
 * @param {number} vw, vh        tamaño de la ventana
 * @param {number} aire          separación mínima entre el globo y el elemento
 * @param {number} borde         margen mínimo contra el borde de la pantalla
 * @returns {{top, left, flecha: 'arriba'|'abajo'|null}}
 */
export function ubicarGlobo(rect, tam, vw, vh, aire = 22, borde = 12) {
  if (!rect) return { top: Math.max(borde, vh / 2 - tam.h / 2), left: Math.max(borde, vw / 2 - tam.w / 2), flecha: null };

  const libreAbajo = vh - (rect.y + rect.h) - aire - borde;
  const libreArriba = rect.y - aire - borde;
  const libreDer = vw - (rect.x + rect.w) - aire - borde;
  const libreIzq = rect.x - aire - borde;

  let top, left, flecha = null, maxAlto = null;
  if (tam.h <= libreAbajo) {
    top = rect.y + rect.h + aire; left = rect.x + rect.w / 2 - tam.w / 2; flecha = 'arriba';
  } else if (tam.h <= libreArriba) {
    top = rect.y - aire - tam.h; left = rect.x + rect.w / 2 - tam.w / 2; flecha = 'abajo';
  } else if (tam.w <= libreDer || tam.w <= libreIzq) {
    left = (tam.w <= libreDer) ? rect.x + rect.w + aire : rect.x - aire - tam.w;
    top = rect.y + rect.h / 2 - tam.h / 2;
  } else {
    // NO ENTRA EN NINGÚN LADO (pantalla baja + texto largo). Antes acá se lo ponía igual y
    // terminaba ENCIMA del botón. Ahora se elige el hueco más grande y **se achica el globo** a
    // ese hueco (adentro scrollea): más vale leer de a poco que no ver lo que hay que tocar.
    const arriba = libreArriba >= libreAbajo;
    maxAlto = Math.max(80, arriba ? libreArriba : libreAbajo);
    top = arriba ? rect.y - aire - maxAlto : rect.y + rect.h + aire;
    left = rect.x + rect.w / 2 - tam.w / 2;
    flecha = arriba ? 'abajo' : 'arriba';
  }
  const alto = maxAlto || tam.h;
  // Que no se salga de la pantalla (el clamp va DESPUÉS de elegir el lado: si no, el clamp podría
  // empujarlo justo encima del elemento).
  left = Math.min(Math.max(borde, left), Math.max(borde, vw - tam.w - borde));
  top = Math.min(Math.max(borde, top), Math.max(borde, vh - alto - borde));
  return { top, left, flecha, maxAlto };
}

/** ¿Se pisan dos cajas? (lo que NUNCA tiene que pasar entre el globo y el elemento resaltado) */
export const seSolapan = (a, b) =>
  !(a.x + a.w <= b.x || b.x + b.w <= a.x || a.y + a.h <= b.y || b.y + b.h <= a.y);
