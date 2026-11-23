// EL BUSCADOR DE MOLDES Y VARIABLES (paso Moldes del pedido y Configuración › Moldería).
//
// Reglas del usuario (2026-11-12, MAPA 815): se escribe el nombre de la VARIABLE o el del MOLDE.
//   · Coincide SÓLO lo que CONTIENE lo escrito tal cual, de corrido (sin tildes ni mayúsculas):
//     «cortada m» trae «Cortada M» y «Cortada manga larga»; NO trae «Camiseta cortada» porque tenga
//     una «m» en otro lado. Antes alcanzaba con que cada palabra estuviera en cualquier parte, y con
//     dos palabras aparecían cosas que no tenían nada que ver.
//   · El nombre EXACTO va primero, pero NO esconde a los demás que lo contienen («cortada» muestra
//     «Cortada» y después «Cortada M», «Recortada»…). Cuanto más se escribe, menos queda.
//   · Escribir el nombre de un molde muestra todas sus variables.
// Vive en un archivo aparte (antes en App.jsx) para que el contrato `verificar_buscador.mjs` pruebe
// estas reglas con los ejemplos del usuario sin levantar la pantalla.

/** Sin tildes, sin mayúsculas y con un solo espacio entre palabras. */
export const normBusq = (s) => (s || '').toString().normalize('NFD').replace(/[̀-ͯ]/g, '')
  .toLowerCase().replace(/\s+/g, ' ').trim();

/**
 * Qué tan bien coincide `texto` con lo escrito: 0 = no coincide.
 * 100 es EXACTO > 80 empieza igual > 60 lo escrito arranca una palabra > 40 está adentro de una palabra.
 */
export function puntajeBusqueda(q, texto) {
  const qq = normBusq(q), t = normBusq(texto);
  if (!qq) return 1;
  if (!t) return 0;
  if (t === qq) return 100;
  if (t.startsWith(qq)) return 80;
  if (t.includes(' ' + qq)) return 60;
  if (t.includes(qq)) return 40;
  return 0;
}

/**
 * Filtra y ordena `items` por `textosDe(item)` (varios textos: gana el mejor; a igual puntaje, el
 * primero de la lista — por eso el nombre de la variable va antes que el del molde).
 * Orden: mejor puntaje → el texto que coincidió (0 antes que 1) → el orden en que venían.
 * Sin nada escrito devuelve TODO, en su orden. Devuelve [{item, puntaje, cual}] — `cual` = el índice
 * del texto que coincidió.
 */
export function filtrarBusqueda(q, items, textosDe) {
  if (!normBusq(q)) return items.map((item) => ({ item, puntaje: 1, cual: -1 }));
  const out = [];
  items.forEach((item, orden) => {
    let mejor = 0, cual = -1;
    (textosDe(item) || []).forEach((tx, i) => { const p = puntajeBusqueda(q, tx); if (p > mejor) { mejor = p; cual = i; } });
    if (mejor > 0) out.push({ item, puntaje: mejor, cual, orden });
  });
  return out.sort((a, b) => b.puntaje - a.puntaje || a.cual - b.cual || a.orden - b.orden);
}

/**
 * CÓDIGOS DE VARIABLE REPETIDOS ENTRE MOLDES. Cada variable se reconoce en todo el sistema por su
 * código (`clave`), que tiene que ser único. Moldes viejos armados con «Aplicar configuración» antes
 * del 2026-09-21 pudieron quedar con los códigos del molde de origen. Devuelve
 * [{clave, variables: [{moldeId, moldeNombre, label}]}] sólo con los repetidos.
 */
export function clavesRepetidas(variables) {
  const porClave = new Map();
  for (const v of variables || []) {
    if (!v || !v.clave) continue;
    if (!porClave.has(v.clave)) porClave.set(v.clave, []);
    porClave.get(v.clave).push({ moldeId: v.moldeId, moldeNombre: v.moldeNombre, label: v.label });
  }
  return [...porClave].filter(([, l]) => new Set(l.map((x) => x.moldeId)).size > 1).map(([clave, l]) => ({ clave, variables: l }));
}
