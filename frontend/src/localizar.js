/**
 * LOCALIZADOR DE CONTROLES — cómo el tutorial vuelve a encontrar lo que el usuario tocó.
 *
 * ── EL PROBLEMA ────────────────────────────────────────────────────────────────────────────────
 * El grabador necesita un identificador que sobreviva a recargar la página y a que otro lo
 * reproduzca en su máquina. `data-tour="…"` es el mejor: lo puso una persona y no cambia. Pero
 * en el sistema hay **477 controles y sólo 82 lo tienen**: pedirle a alguien que ponga las otras
 * 395 a mano antes de poder grabar un tutorial es no tenerlo.
 *
 * ── LA SOLUCIÓN ────────────────────────────────────────────────────────────────────────────────
 * Dos clases de identificador, y siempre se prefiere el primero:
 *
 *   1. `nav-pedidos`      el `data-tour` de toda la vida.
 *   2. `txt:guardar`      el TEXTO VISIBLE del control, normalizado. Lo que la persona lee es lo
 *                         que la persona toca, así que es lo más estable que hay sin tocar el JSX.
 *                         Se busca sólo entre controles VISIBLES y, si hay varios iguales, gana
 *                         el que esté más cerca de donde se grabó (ver `elegirEntre`).
 *
 * 🔴 NO se usan selectores de CSS ni caminos del DOM (`div > div:nth-child(3)`): con React se
 * rompen apenas alguien toca el layout, y el tutorial quedaría marcando el botón equivocado —
 * peor que no marcar nada.
 *
 * Lo que no tiene ni ancla ni texto (un ícono suelto en una fila de una lista) NO se puede grabar
 * y el grabador lo dice: es preferible a grabar un paso que después apunte a cualquier lado.
 */

/** Sin acentos, sin espacios de más y en minúscula: «Guardar cambios» y «guardar  cambios» son lo mismo. */
export function normalizar(s) {
  return String(s || '')
    .normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ')
    .trim().toLowerCase()
    .slice(0, 48);
}

/**
 * El rótulo de un campo: `<label for>`, el label que lo envuelve, o el texto justo arriba.
 *
 * 🔴 EL «?» DE AYUDA NO ES EL NOMBRE DE UN CAMPO. Los rótulos de esta app llevan al lado el botón
 * «?» del popover, y el texto de ese vecino terminaba siendo la identidad del campo: en el tutorial
 * «Cargar molde» del usuario hay dos pasos guardados como **`txt:?`** (2026-09-01). Cada texto
 * candidato tiene que parecer un NOMBRE (`esNombreDeControl`), y se le saca el «?» pegado.
 */
/** La primera línea de un texto (lo que se lee como nombre). */
function primeraLinea(s) {
  return String(s || '').split(/\r?\n/)[0];
}
function limpiarRotulo(s) {
  return String(s || '').replace(/\s*[?¿]\s*$/, '').replace(/^\s*[?¿]\s*/, '').trim();
}
function rotuloDe(el) {
  const sirve = (s) => { const x = limpiarRotulo(s); return esNombreDeControl(x) ? x : ''; };
  if (el.id) {
    const l = document.querySelector(`label[for="${CSS.escape ? CSS.escape(el.id) : el.id}"]`);
    const r0 = l && sirve(l.innerText);
    if (r0) return r0;
  }
  const env = el.closest('label');
  const r1 = env && sirve(env.innerText);
  if (r1) return r1;
  // el patrón más común de esta app: un rótulo suelto justo arriba del campo
  let p = el.previousElementSibling;
  for (let i = 0; i < 2 && p; i++, p = p.previousElementSibling) {
    const t = sirve(primeraLinea(p.innerText));
    if (t) return t;
  }
  // …y si no, SUBIENDO: el patrón habitual es <div><label>Contraseña</label><div><input/>…
  // Se sube poco (3 niveles) y se toman textos cortos: más arriba ya empiezan los títulos de
  // sección, que valdrían para varios campos y los harían indistinguibles entre sí.
  let cont = el.parentElement;
  for (let up = 0; up < 3 && cont; up++, cont = cont.parentElement) {
    const lab = cont.querySelector('label');
    const r2 = lab && !lab.contains(el) && sirve(lab.innerText);
    if (r2) return r2;
    const prev = cont.previousElementSibling;
    const t = prev && sirve(primeraLinea(prev.innerText));
    if (t) return t;
  }
  return '';
}

/** Lo que la persona LEE de un control: su texto, o lo que lo describe.
 *  🔴 Un CAMPO no tiene texto propio: su identidad es su rótulo o su ayuda de escritura. Sin
 *  esto los 88 campos del sistema no se podían grabar (se vio probando en la pantalla real). */
export function etiquetaDe(el) {
  if (!el) return '';
  const t = (el.getAttribute && (el.getAttribute('aria-label') || el.getAttribute('title'))) || '';
  if (t.trim()) return t.trim();
  const tag = (el.tagName || '').toLowerCase();
  if (tag === 'input' || tag === 'select' || tag === 'textarea') {
    const ph = el.getAttribute('placeholder');
    if (ph && ph.trim()) return ph.trim();
    const r = rotuloDe(el);
    if (r) return r.split('\n')[0].trim();
    const nm = el.getAttribute('name');
    return nm ? nm.trim() : '';
  }
  const txt = (el.innerText || el.textContent || '').trim();
  if (txt) return txt.split('\n')[0].trim();
  const ph = el.getAttribute && el.getAttribute('placeholder');
  return ph && ph.trim() ? ph.trim() : '';
}

/** Lo que se puede tocar y tiene nombre propio. Va ARRIBA de todo lo que la usa: leerla antes
 *  de su declaración es ReferenceError (el candado `verificar_tdz.mjs` lo corta). */
const CONTROLES = 'button, [role="button"], a[href], input, select, textarea, label';

/**
 * EL CONTEXTO DE UN CONTROL: de qué FILA es. Sirve para distinguir homónimos — en la app hay 7
 * botones «Editar» y 13 «Eliminar…», y sin esto todos se guardaban igual y el tutorial marcaba el
 * primero de la lista en vez del que se tocó.
 *
 * Se sube por los ancestros buscando el primero que tenga texto propio distinto del control (una
 * fila, una tarjeta) y se usa su primera línea, que es como esa fila se llama en la pantalla.
 */
function contextoDe(el, etiquetaCtrl) {
  let n = el.parentElement;
  for (let i = 0; i < 6 && n; i++, n = n.parentElement) {
    // 🔴 El nombre de la fila es su texto SIN el de sus botones. Sin sacarlos, los 7 «Editar» de
    // las reglas daban todos el mismo contexto: «eliminar», que es el botón de al lado.
    let t = n.innerText || '';
    if (!t.trim()) continue;
    try {
      for (const c of n.querySelectorAll(CONTROLES)) {
        const tc = (c.innerText || '').trim();
        if (tc && tc.length < 40) t = t.split(tc).join('\n');
      }
    } catch { /* sin querySelectorAll (nodo raro): se usa el texto tal cual */ }
    const prim = t.split('\n').map((x) => x.trim()).filter(Boolean)
      .find((x) => normalizar(x) !== etiquetaCtrl && x.length > 1);
    if (prim) return normalizar(prim);
  }
  return '';
}

/** ¿Cuántos controles a la vista se llaman igual? (si hay más de uno, hace falta el contexto) */
function homonimos(etiqueta) {
  let n = 0;
  for (const el of document.querySelectorAll(CONTROLES)) {
    if (!visible(el)) continue;
    if (normalizar(etiquetaDe(el)) === etiqueta) n++;
    if (n > 1) break;
  }
  return n;
}

/**
 * ¿ESTO SE PUEDE GRABAR? — el mismo criterio para el grabador y para el «⏺ Agregar pasos» del
 * editor. Antes cada uno tenía el suyo y el editor terminaba anotando pasos que el grabador
 * descarta (se vio 2026-08-31: agregó un «tocá Configuración» de la barra lateral).
 *
 *   · la BARRA LATERAL: moverse entre secciones no es el trabajo que se enseña, y ensuciaba cada
 *     tutorial con un «tocá Pedidos» antes de lo importante (el motor igual lleva a la pantalla);
 *   · lo marcado `data-no-grabar` (el cartel del grabador) y el propio editor.
 */
export function sePuedeGrabar(el) {
  if (!el || !el.closest) return false;
  return !el.closest('aside.sidebar') && !el.closest('[data-no-grabar]')
    && !el.closest('[data-diseno-pasos]');
}

/**
 * PARTIR UN ANCLA `txt:<nombre>[@<fila>][#<sección>]` — el ÚNICO lugar donde se decide.
 *
 * 🔴 EL `#` DEL SEPARADOR CHOCA CON EL `#` DEL TEXTO. Un control puede llamarse «6XL · pieza #1 —
 * Espalda…», y partir por el PRIMER `#` daba como «sección» un pedazo del propio nombre
 * (`1 — espalda 16xl · pieza `). Con eso el paso no se podía encontrar nunca, ni caer a su sección,
 * ni reconocerse como parte del visor: era el cartel **«No encuentro ese lugar en pantalla»** que
 * reportó el usuario (paso 16/37 de «Cargar molde», 2026-09-01). La sección es lo que va después
 * del ÚLTIMO `#`: un `data-tour` no lleva `#` nunca.
 */
export function partirAncla(ancla) {
  const a = String(ancla || '');
  if (!a.startsWith('txt:')) return { nombre: '', ctx: '', seccion: '' };
  const cuerpo = a.slice(4);
  const i = cuerpo.lastIndexOf('#');
  const seccion = i >= 0 ? cuerpo.slice(i + 1) : '';
  const conNombre = i >= 0 ? cuerpo.slice(0, i) : cuerpo;
  const j = conNombre.lastIndexOf('@');
  return { nombre: j >= 0 ? conNombre.slice(0, j) : conNombre,
           ctx: j >= 0 ? conNombre.slice(j + 1) : '',
           seccion };
}

/**
 * ¿ESTO PARECE EL NOMBRE DE UN CONTROL? Un botón se llama «Guardar», no «✓ 120», ni «?», ni
 * «6XL · pieza #1 — Espalda 1…». Se pide: corto y con letras de verdad. Lo usan el grabador (para
 * no guardar un ancla con un cartel inservible) y el guion (para no afinar los ya grabados).
 */
export function esNombreDeControl(txt) {
  const s = String(txt || '').trim();
  return s.length > 0 && s.length <= 40 && /[a-z]{2}/.test(normalizar(s));
}

/** El identificador con el que se guarda un control. `null` = no se puede volver a encontrar. */
export function identificar(el) {
  if (!el) return null;
  const conAncla = el.closest && el.closest('[data-tour]');
  // UNA COLUMNA DE LA PLANILLA ES SU PROPIO LUGAR. La única marca de la planilla está en la
  // <table>, así que sin esto tocar Talle, Nombre o Número grababa siempre el mismo paso y el
  // tutorial iluminaba la tabla entera. Gana la columna sólo si está MÁS ADENTRO que el
  // `data-tour` (si algún día una celda tuviera un control marcado, ese control gana).
  const conCol = el.closest && el.closest('[data-col]');
  if (conCol && (!conAncla || conAncla.contains(conCol))) {
    const c = conCol.getAttribute('data-col');
    if (c) return 'col:' + c;
  }
  // UNA PIEZA DEL VISOR es su propio lugar (el «espacio de trabajo visual»): sin esto, tocar una
  // pieza no se podía grabar — el SVG no tiene texto ni controles adentro.
  const conPieza = el.closest && el.closest('[data-pieza]');
  if (conPieza && (!conAncla || conAncla.contains(conPieza))) {
    const pz = conPieza.getAttribute('data-pieza');
    if (pz) return 'pieza:' + normalizar(pz);
  }
  // 🔴 LO QUE SE TOCÓ NO SIEMPRE ES EL CONTROL: el clic cae en el ícono (`<svg>`, `<path>`) o en
  // un `<span>` de adentro del botón, y esos no tienen nombre. Se sube al control que los
  // contiene; si no hay ninguno, se usa el elemento tal cual (un div clickeable con texto).
  const ctrl = (el.closest && el.closest(CONTROLES)) || el;
  const et = normalizar(etiquetaDe(ctrl));
  if (conAncla) {
    const a = conAncla.getAttribute('data-tour');
    // El `data-tour` puesto EN el control manda: lo eligió una persona.
    if (a && (conAncla === ctrl || conAncla === el || !et)) return a;
    // 🔴 UNA LISTA DE OPCIONES NO SE AFINA: quien grabó eligió «Cuello redondo», pero quien sigue
    // el tutorial elige la prenda que necesita. La marca `data-opciones` la pone la pantalla
    // (pedido del usuario 2026-08-31: «en el paso de elegir molde también es multiopción»).
    if (a && conAncla.hasAttribute && conAncla.hasAttribute('data-opciones')) return a;
    // 🔴 NI EN UN LIENZO DE TRABAJO (`data-lienzo`): el visor del molde no tiene «botones», tiene
    // PIEZAS (que se graban como `pieza:<nombre>` más arriba). Lo que quede suelto adentro es
    // ayuda de la pantalla, no un control: guardarlo daba pasos como «Tocá "Rueda: zoom · clic
    // der.: mover"» (tutorial «Cargar molde» del usuario, 2026-09-01).
    if (a && conAncla.hasAttribute && conAncla.hasAttribute('data-lienzo')) return a;
    // 🔴 Pero si la marca está en un CONTENEDOR (un panel, una lista), quedarse sólo con ella
    // pierde CUÁL botón se tocó: en el tutorial del usuario los pasos 21 y 22 eran los dos
    // «resultados-mesas» —dos botones distintos del mismo panel— y el tutorial marcaba el panel
    // entero sin poder esperar los dos. Se guardan los dos datos: el botón y su sección.
    // 🔴 …pero SÓLO si lo que se tocó tiene un NOMBRE de control. Lo que el navegador da como
    // «texto» puede ser un párrafo, un contador o un símbolo, y con eso el tutorial terminaba
    // diciendo «Tocá "✓ 120"» o «Tocá "6XL · pieza #1 — Espalda 1…"» (tutorial «Cargar molde» del
    // usuario, 2026-09-01). Sin nombre de verdad, vale la marca del contenedor: su explicación
    // está escrita a mano.
    if (a && esNombreDeControl(et)) return 'txt:' + et + '#' + a;
    if (a) return a;
  }
  if (!et) return null;
  // Si hay varios controles con ese mismo nombre, el ancla sola no alcanza: se guarda con el
  // contexto de su fila («editar@manga larga») para volver a encontrar EL QUE SE TOCÓ.
  if (homonimos(et) > 1) {
    const ctx = contextoDe(ctrl, et);
    if (ctx) return 'txt:' + et + '@' + ctx;
  }
  return 'txt:' + et;
}


/** El nombre de una columna de la planilla, tal como lo puso el molde («Talle», «Sisa»…). */
export function etiquetaColumna(id) {
  const el = document.querySelector(`[data-col="${CSS.escape ? CSS.escape(id) : id}"][data-col-label]`);
  return (el && el.getAttribute('data-col-label')) || id;
}

/**
 * EL RECUADRO DE UNA COLUMNA ENTERA: el encabezado más todas sus celdas. Iluminar sólo el
 * encabezado (o sólo una celda) no muestra de qué columna se habla.
 */
export function rectDeColumna(id) {
  const esc = CSS.escape ? CSS.escape(id) : id;
  // La columna es el encabezado + sus celdas + SU DESPLEGABLE si está abierto: la lista se monta
  // en el body (portal), y sin sumarla el hueco del tutorial la dejaba afuera, bajo el velo.
  const els = [...document.querySelectorAll(`[data-col="${esc}"], [data-col-lista="${esc}"]`)].filter(visible);
  if (!els.length) return null;
  let x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity;
  for (const el of els) {
    const r = el.getBoundingClientRect();
    x1 = Math.min(x1, r.left); y1 = Math.min(y1, r.top);
    x2 = Math.max(x2, r.right); y2 = Math.max(y2, r.bottom);
  }
  return { x: x1, y: y1, w: x2 - x1, h: y2 - y1 };
}

/**
 * EL MISMO TEXTO, CON OTRO NÚMERO ADENTRO. Un botón que dice «Copiar a 1» pasa a decir «Copiar a 3»
 * en cuanto se marcan tres moldes, y «Descargar todo (1)» cambia con la cantidad de mesas. El ancla
 * grabada guarda el texto de ESE día, así que al reproducir no se encontraba nada y el tutorial
 * quedaba en «No encuentro ese lugar» (auditoría 2026-08-31, tutorial «2 colores» del usuario).
 * Los números se vuelven comodín SÓLO como segundo intento: primero manda el texto exacto.
 */
export function sinNumeros(s) {
  return String(s || '').replace(/\d+([.,]\d+)?/g, '#');
}

/** La lista de opciones equivalentes a la que pertenece un control (o null). La marca la pone la
 *  pantalla con `data-opciones`. */
export function listaDeOpciones(el) {
  return (el && el.closest) ? el.closest('[data-opciones]') : null;
}

/**
 * CUÁNTAS OPCIONES ESTÁN ELEGIDAS AHORA en esa lista — se MIDE la pantalla, no se cuentan clics.
 *
 * 🔴 POR QUÉ: el paso «Elegí 2 de esta lista» contaba clics, así que dos clics en el AIRE lo daban
 * por cumplido, y tocar dos diseños YA elegidos (que los DESMARCA) lo hacía avanzar dejando el
 * pedido con menos diseños que antes (verificado en pantalla, auditoría 2026-08-31). Es la misma
 * lección de `cuantos`: lo que vale es el TOTAL que hay puesto, no los toques que hubo.
 *
 * Cada opción de esas listas lleva `data-elegida="1"|"0"`. `null` = esa lista no lo declara y no se
 * puede medir (ahí el motor cae a contar clics sobre opciones de verdad).
 */
export function elegidasEn(ancla) {
  const cont = buscar(ancla);
  if (!cont || !cont.querySelectorAll) return null;
  let marcables;
  try { marcables = [...cont.querySelectorAll('[data-elegida]')]; } catch { return null; }
  if (!marcables.length) return null;                    // esta lista no sabe decirlo
  return marcables.filter((el) => el.getAttribute('data-elegida') === '1' && visible(el)).length;
}

/**
 * ¿ESTO ES UN CAMPO DE ESCRITURA? Un campo no se «toca y listo»: se COMPLETA, y eso lo termina la
 * persona (pedido del usuario 2026-09-01). Sirve para el elemento tocado y para el del paso.
 * Los `select` NO cuentan: ahí se elige de una lista, no se escribe.
 */
export function esCampo(el) {
  if (!el) return false;
  try {
    if (el.matches && el.matches('input, textarea')) return true;
    const c = el.closest && el.closest('input, textarea');
    if (c) return true;
    // `querySelectorAll` y no `querySelector`: es la que existe en todos lados (el DOM de juguete
    // del contrato implementa sólo ésa, y sin esto el caso «un div que envuelve al campo» no se
    // probaba de verdad)
    return !!(el.querySelectorAll && el.querySelectorAll('input, textarea').length);
  } catch { return false; }
}

/**
 * EL GESTO QUE SE MUESTRA ES **GENÉRICO**, SIEMPRE EL MISMO Y EN EL MISMO LUGAR.
 *
 * 🔴 No se reproduce el arrastre EXACTO de quien grabó (decisión del usuario, 2026-09-01: «que no
 * muestre el arrastrado real que hacemos cuando grabamos; debe ser un arrastrado genérico que
 * siempre se muestra en la misma parte del campo»). Y tiene razón: quien sigue el tutorial tiene
 * otro molde, otras piezas y otro zoom, así que calcar el recorrido de otra persona no enseña
 * nada — puede hasta marcar una zona que en su pantalla no significa nada. Lo que hay que mostrar
 * es EL GESTO: apretar, arrastrar y soltar para abarcar varias cosas de una.
 *
 * Es la misma regla que ya vale en todo el sistema: en una lista de opciones el paso es la LISTA
 * y no la tarjeta que se tocó; acá el paso es EL MOVIMIENTO, no el recorrido que se grabó.
 *
 * Una diagonal centrada, de arriba-izquierda a abajo-derecha, en proporciones del elemento: se ve
 * igual de clara en un visor grande que en uno chico.
 */
export const GESTO_GENERICO = { desde: { x: 0.22, y: 0.28 }, hasta: { x: 0.75, y: 0.78 } };

/** Los dos puntos de PANTALLA del gesto genérico sobre el elemento que hoy es el paso. */
export function gestoGenerico(el) {
  const d = puntoEnPantalla(el, GESTO_GENERICO.desde);
  const h = puntoEnPantalla(el, GESTO_GENERICO.hasta);
  return (d && h) ? { desde: d, hasta: h } : null;
}

/**
 * UN MOVIMIENTO, NO UN CLIC — reconocer un ARRASTRE al grabar.
 *
 * En el visor no todo se hace tocando: para elegir varias piezas de una se **arrastra un
 * recuadro** desde un espacio vacío. Ese gesto no se podía grabar (el grabador sólo anota clics) y
 * es justo el que más cuesta explicar con palabras (pedido del usuario 2026-09-01, con un video).
 *
 * Del gesto sólo importa QUE FUE un arrastre: el recorrido que se muestra después es el genérico
 * (ver `GESTO_GENERICO` arriba).
 */
/** El punto de PANTALLA de un `{x,y}` relativo, sobre el elemento que hoy representa ese ancla. */
export function puntoEnPantalla(el, rel) {
  if (!el || !rel || !el.getBoundingClientRect) return null;
  const r = el.getBoundingClientRect();
  if (!r.width && !r.height) return null;
  return { x: r.left + r.width * (Number(rel.x) || 0), y: r.top + r.height * (Number(rel.y) || 0) };
}

/** ¿Este movimiento es un ARRASTRE de verdad o el temblor de un clic? (en píxeles de pantalla) */
export function esArrastre(x0, y0, x1, y1) {
  return (Math.abs(x1 - x0) + Math.abs(y1 - y0)) >= 14;
}

/** ¿El control de este paso está APAGADO? (no se puede tocar aunque esté iluminado) */
export function estaApagado(el) {
  if (!el) return false;
  const c = (el.closest && el.closest('button, [role="button"], input, select, textarea')) || el;
  if (c.disabled) return true;
  return !!(c.getAttribute && c.getAttribute('aria-disabled') === 'true');
}

/**
 * POR QUÉ ESTÁ APAGADO — con las palabras que la propia pantalla ya usa.
 * 1) el `title` del control (lo escribió quien hizo la pantalla: «Faltan 3 pieza(s) sin tela»);
 * 2) el aviso de la barra del paso (`data-aviso-paso`), que es lo que la persona lee al lado.
 * Devuelve `{texto, el}`: `el` es el cartel a iluminar junto al botón, si lo hay.
 */
export function motivoApagado(el) {
  const c = (el && el.closest && el.closest('button, [role="button"], input, select, textarea')) || el;
  const t = c && c.getAttribute && (c.getAttribute('data-motivo') || c.getAttribute('title'));
  if (t && t.trim()) return { texto: t.trim(), el: null };
  let aviso = null;
  try { aviso = [...document.querySelectorAll('[data-aviso-paso]')].filter(visible)[0] || null; } catch { /* no-op */ }
  const txt = aviso && (aviso.innerText || '').trim();
  return txt ? { texto: txt, el: aviso } : null;
}

/** ¿Se ve de verdad? Un control oculto no sirve para iluminar. */
function visible(el) {
  const r = el.getBoundingClientRect();
  if (!(r.width || r.height)) return false;
  const st = window.getComputedStyle(el);
  return st.visibility !== 'hidden' && st.display !== 'none' && Number(st.opacity) > 0.05;
}

/**
 * De varios candidatos con el mismo texto, el mejor: el que esté DENTRO de un diálogo abierto si
 * lo hay (lo de arriba es lo que la persona está mirando), y si no, el primero de la pantalla.
 */
function elegirEntre(cands) {
  if (cands.length <= 1) return cands[0] || null;
  // Un CAMPO le gana a su rótulo: los dos matchean con el mismo texto («Usuario»), pero lo que
  // la persona usa —y lo que hay que iluminar— es el campo, no la palabra de arriba.
  const reales = cands.filter((el) => (el.tagName || '').toLowerCase() !== 'label');
  const base = reales.length ? reales : cands;
  const enModal = base.filter((el) => el.closest('[role="dialog"], .modal, [data-modal]'));
  const lista = enModal.length ? enModal : base;
  return lista.slice().sort((a, b) => {
    const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
    return (ra.top - rb.top) || (ra.left - rb.left);
  })[0];
}

/**
 * ¿LO QUE SE TOCÓ ES EL CONTROL DE ESTE PASO? — el ÚNICO lugar donde se decide.
 *
 * 🔴 Antes esto vivía suelto en el motor y sólo miraba `data-tour`, así que un paso grabado sobre
 * un control SIN esa marca —la mayoría: se identifican por su texto, `txt:…`— no avanzaba nunca
 * al tocarlo (reporte del usuario 2026-08-31, con la tarjeta «Cuello redondo»). Las tres formas
 * de ancla se resuelven acá, con el mismo criterio que usa `buscar()` para encontrarlas.
 */
export function esDelAncla(el, ancla) {
  if (!el || !ancla || !el.closest) return false;
  // 🔴 LO QUE DESHACE NO CUMPLE EL PASO. La «✕» que QUITA un diseño vive dentro de la misma lista
  // marcada, así que tocarla contaba como «elegí una opción» y el tutorial avanzaba premiando lo
  // contrario de lo que pedía (auditoría 2026-08-31). Se marca con `data-no-avanza` en la pantalla.
  if (el.closest('[data-no-avanza]')) return false;
  const esc = (x) => (CSS.escape ? CSS.escape(x) : x);
  if (ancla.startsWith('col:')) {
    const id = esc(ancla.slice(4));
    return !!(el.closest(`[data-col="${id}"]`) || el.closest(`[data-col-lista="${id}"]`));
  }
  if (ancla.startsWith('pieza:')) {
    const pz = el.closest('[data-pieza]');
    return !!(pz && normalizar(pz.getAttribute('data-pieza')) === ancla.slice(6));
  }
  if (ancla.startsWith('txt:')) {
    const _p = partirAncla(ancla);
    const _sec = _p.seccion;
    // si el ancla trae sección, lo tocado tiene que estar ahí adentro
    if (_sec && !el.closest(`[data-tour="${esc(_sec)}"]`)) return false;
    const busco = _p.nombre, ctx = _p.ctx;
    // el control que se tocó (o el que lo contiene) se llama así… y, si el ancla trae contexto,
    // tiene que ser el de ESA fila (si no, tocar «Editar» de otra fila daría el paso por hecho)
    const ctrl = el.closest(CONTROLES);
    if (ctrl && normalizar(etiquetaDe(ctrl)) === busco
        && (!ctx || contextoDe(ctrl, busco).includes(ctx) || ctx.includes(contextoDe(ctrl, busco)))) return true;
    // …o lo tocado está DENTRO del control que el localizador resolvería para este paso (un
    // clic en el dibujito de una tarjeta cuenta como clic en la tarjeta)
    const res = buscar(ancla);
    return !!(res && res.contains && res.contains(el));
  }
  return !!el.closest(`[data-tour="${esc(ancla)}"]`);
}

/**
 * EL RECUADRO DE UN PASO — el ÚNICO lugar donde se decide qué se ilumina.
 * 🔴 Lo usan el tutorial Y el editor: cuando cada uno medía por su cuenta, el editor marcaba sólo
 * el TÍTULO de la columna y el tutorial la columna entera (reporte del usuario). Un paso de
 * columna es su título MÁS todas las casillas de todas las filas (más su desplegable abierto).
 */
export function rectDeAncla(ancla, el) {
  if (ancla && ancla.startsWith('col:')) {
    const r = rectDeColumna(ancla.slice(4));
    if (r) return r;
  }
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return (r.width || r.height) ? { x: r.left, y: r.top, w: r.width, h: r.height } : null;
}

/** Encuentra en pantalla el control que corresponde a un identificador. `null` si no está. */
export function buscar(ancla) {
  if (!ancla) return null;
  // `col:<id>` = una columna de la planilla; se devuelve su ENCABEZADO como elemento de
  // referencia (para el scroll), pero al iluminar se usa `rectDeColumna` (toda la columna).
  if (ancla.startsWith('col:')) {
    const id = ancla.slice(4);
    const els = [...document.querySelectorAll(`[data-col="${CSS.escape ? CSS.escape(id) : id}"]`)];
    return els.find((e) => e.tagName === 'TH' && visible(e)) || els.find(visible) || els[0] || null;
  }
  if (ancla.startsWith('pieza:')) {
    const pz = ancla.slice(6);
    return [...document.querySelectorAll('[data-pieza]')]
      .find((e) => normalizar(e.getAttribute('data-pieza')) === pz && visible(e)) || null;
  }
  if (!ancla.startsWith('txt:')) {
    const el = document.querySelector(`[data-tour="${CSS.escape ? CSS.escape(ancla) : ancla}"]`);
    return el && visible(el) ? el : (el || null);
  }
  // `txt:<nombre>@<fila>` — el contexto distingue entre homónimos (ver `identificar`)
  // `txt:<nombre>#<sección>` — el botón DENTRO de esa sección marcada
  const _pa = partirAncla(ancla);
  const seccion = _pa.seccion, busco = _pa.nombre, ctx = _pa.ctx;
  const zona = seccion
    ? document.querySelector(`[data-tour="${CSS.escape ? CSS.escape(seccion) : seccion}"]`)
    : null;
  const cands = [];
  for (const el of document.querySelectorAll(CONTROLES)) {
    if (!visible(el)) continue;
    if (zona && !zona.contains(el)) continue;      // sólo los de esa sección
    if (normalizar(etiquetaDe(el)) === busco) cands.push(el);
  }
  // ⚠️ SEGUNDO INTENTO, CON LOS NÚMEROS COMO COMODÍN: «Copiar a 1» hoy dice «Copiar a 3». Va
  // DESPUÉS del texto exacto, para no robarle el paso a un botón que se llama igual de verdad.
  if (!cands.length && /\d/.test(busco)) {
    const buscoN = sinNumeros(busco);
    for (const el of document.querySelectorAll(CONTROLES)) {
      if (!visible(el)) continue;
      if (zona && !zona.contains(el)) continue;
      if (sinNumeros(normalizar(etiquetaDe(el))) === buscoN) cands.push(el);
    }
  }
  // 🔴 LO QUE SE PUEDE GRABAR TIENE QUE PODER ENCONTRARSE. Media Configuración no se toca con
  // botones: las TARJETAS de moldería (y varias listas) son `<div>` clickeables. `identificar` las
  // graba —cae al elemento tal cual cuando no hay un control arriba— pero `buscar` sólo miraba
  // `CONTROLES`, así que al reproducir el tutorial decía «No encuentro ese lugar» con la tarjeta a
  // la vista (auditoría de Configuración, 2026-09-01). Se busca por TEXTO en todo lo demás y gana
  // el más CHICO: el nodo que se llama así y nada más, no el panel que lo contiene.
  if (!cands.length) {
    const otros = [];
    for (const el of document.querySelectorAll('div, li, tr, td, section, article, span')) {
      if (!visible(el)) continue;
      if (zona && !zona.contains(el)) continue;
      if (normalizar(etiquetaDe(el)) !== busco) continue;
      const r = el.getBoundingClientRect();
      otros.push({ el, area: r.width * r.height });
    }
    if (otros.length) {
      // 🔴 EL MÁS GRANDE, NO EL MÁS CHICO: el título de una tarjeta y la tarjeta entera se llaman
      // igual, y lo que la persona TOCA es la tarjeta. Con el título, el clic en cualquier otra
      // parte de la tarjeta no contaba como el paso y el tutorial quedaba pidiéndolo con la
      // moldería ya abierta (verificado 2026-09-01). Tope: nada que ocupe media pantalla —eso ya
      // no es «un lugar», es el panel que lo contiene—.
      let tope = Infinity;
      // ⚠️ `Number.isFinite`, no un try/catch: sin `innerWidth` la cuenta no explota, da **NaN**, y
      // con NaN toda comparación es false → se elegía el candidato más CHICO (el título de la
      // tarjeta) justo al revés de lo que se busca. Lo agarró el contrato.
      try {
        const t2 = window.innerWidth * window.innerHeight * 0.45;
        if (Number.isFinite(t2) && t2 > 0) tope = t2;
      } catch { /* sin ventana: sin tope */ }
      otros.sort((a, b) => b.area - a.area);
      const elegido = otros.find((x) => x.area <= tope) || otros[otros.length - 1];
      return generalizar(elegido.el, ancla);
    }
  }
  // ese botón ya no está (otra pantalla, otra lista): se marca la sección, que sigue existiendo
  if (!cands.length && zona) return visible(zona) ? zona : zona;
  if (ctx && cands.length > 1) {
    // el que está en ESA fila; si esa fila ya no está, se sigue con todos (mejor marcar algo
    // parecido que no marcar nada)
    const enSuFila = cands.filter((el) => contextoDe(el, busco).includes(ctx)
      || ctx.includes(contextoDe(el, busco)));
    if (enSuFila.length) return generalizar(elegirEntre(enSuFila), ancla);
  }
  return generalizar(elegirEntre(cands), ancla);
}

/**
 * 🔴 EN UNA LISTA DE OPCIONES, EL PASO ES LA LISTA — también para los YA GRABADOS.
 *
 * Un tutorial viejo puede tener el paso atado a UNA tarjeta («Cuello redondo»), grabado cuando esa
 * lista todavía no tenía su marca `data-opciones`. Quien lo sigue trabaja con OTRO molde: esa
 * tarjeta no existe y el tutorial se queda en «No encuentro ese lugar» (auditoría 2026-08-31). Si
 * lo que se resolvió cae dentro de una lista de opciones, se marca LA LISTA: cualquiera de sus
 * opciones cumple el paso. Se arregla al REPRODUCIR, sin regrabar nada.
 */
function generalizar(el, ancla) {
  const lista = listaDeOpciones(el);
  if (!lista || !lista.getAttribute) return el;
  const a = lista.getAttribute('data-tour');
  if (!a || a === ancla) return el;
  return lista;
}

/**
 * EL ANCLA QUE DE VERDAD SE VA A USAR. Si el paso terminó marcando una lista de opciones (ver
 * `generalizar`), el cartel tiene que ser el DE LA LISTA y no el de la tarjeta que se grabó: si
 * no, se ilumina «elegí la que necesites» y el texto sigue diciendo «Tocá "Cuello redondo"».
 */
export function anclaEfectiva(ancla) {
  if (!ancla || !String(ancla).startsWith('txt:')) return ancla;
  // 🔴 SI LA SECCIÓN **ES** EL CONTROL, EL PASO ES LA SECCIÓN. El afinado por etiqueta
  // («txt:<lo que decía el botón>#<su data-tour>») existe para los PANELES con varios botones
  // adentro. Aplicado a un control que ya tiene su propia marca, sólo empeora el cartel: el botón
  // «Nombres» se toca en su ícono y el tutorial terminaba diciendo **«Tocá "Aa"»** en vez de
  // «Entrá a "Nombres"» (auditoría de Configuración, 2026-09-01). Se decide acá, mirando la
  // pantalla, porque es lo único que sabe si eso es un botón o un panel.
  const parte = [null, partirAncla(ancla).seccion];
  if (parte[1]) {
    const esc = CSS.escape ? CSS.escape(parte[1]) : parte[1];
    const z = document.querySelector(`[data-tour="${esc}"]`);
    if (z) {
      let dentro;
      try { dentro = z.querySelectorAll(CONTROLES).length; } catch { dentro = 0; }
      const esControl = (z.matches && z.matches(CONTROLES)) || dentro <= 1;
      if (esControl) return parte[1];
    }
  }
  const el = buscar(ancla);
  const a = el && el.getAttribute && el.getAttribute('data-opciones') != null
    ? el.getAttribute('data-tour') : null;
  return a || ancla;
}

/** El ROL de una columna de la planilla («talle», «nombre», «diseno»…). Las columnas son
 *  configurables por planilla, así que su ID cambia de taller en taller (el «Diseño» del usuario
 *  se llama `dise_o`) pero el ROL es el mismo siempre: es por ahí que hay que explicarlas. */
export function roleDeColumna(id) {
  const el = document.querySelector(`[data-col="${CSS.escape ? CSS.escape(id) : id}"][data-col-role]`);
  return (el && el.getAttribute('data-col-role')) || '';
}

export default { normalizar, etiquetaDe, identificar, buscar, rectDeColumna, rectDeAncla,
                 esDelAncla, sePuedeGrabar, etiquetaColumna, elegidasEn, estaApagado,
                 motivoApagado, anclaEfectiva, roleDeColumna, sinNumeros, listaDeOpciones,
                 esCampo, esNombreDeControl, gestoGenerico, GESTO_GENERICO };
