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

/** El rótulo de un campo: `<label for>`, el label que lo envuelve, o el texto justo arriba. */
function rotuloDe(el) {
  if (el.id) {
    const l = document.querySelector(`label[for="${CSS.escape ? CSS.escape(el.id) : el.id}"]`);
    if (l && l.innerText.trim()) return l.innerText.trim();
  }
  const env = el.closest('label');
  if (env && env.innerText.trim()) return env.innerText.trim();
  // el patrón más común de esta app: un rótulo suelto justo arriba del campo
  let p = el.previousElementSibling;
  for (let i = 0; i < 2 && p; i++, p = p.previousElementSibling) {
    const t = (p.innerText || '').trim();
    if (t && t.length <= 40) return t;
  }
  // …y si no, SUBIENDO: el patrón habitual es <div><label>Contraseña</label><div><input/>…
  // Se sube poco (3 niveles) y se toman textos cortos: más arriba ya empiezan los títulos de
  // sección, que valdrían para varios campos y los harían indistinguibles entre sí.
  let cont = el.parentElement;
  for (let up = 0; up < 3 && cont; up++, cont = cont.parentElement) {
    const lab = cont.querySelector('label');
    if (lab && !lab.contains(el) && lab.innerText.trim()) return lab.innerText.trim();
    const prev = cont.previousElementSibling;
    const t = prev && (prev.innerText || '').trim();
    if (t && t.length <= 40) return t;
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
    // 🔴 Pero si la marca está en un CONTENEDOR (un panel, una lista), quedarse sólo con ella
    // pierde CUÁL botón se tocó: en el tutorial del usuario los pasos 21 y 22 eran los dos
    // «resultados-mesas» —dos botones distintos del mismo panel— y el tutorial marcaba el panel
    // entero sin poder esperar los dos. Se guardan los dos datos: el botón y su sección.
    if (a) return 'txt:' + et + '#' + a;
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
    const [_nom, _sec] = ancla.slice(4).split('#');
    // si el ancla trae sección, lo tocado tiene que estar ahí adentro
    if (_sec && !el.closest(`[data-tour="${esc(_sec)}"]`)) return false;
    const [busco, ctx] = _nom.split('@');
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
  const sinPrefijo = ancla.slice(4);
  const [conNombre, seccion] = sinPrefijo.split('#');
  const [busco, ctx] = conNombre.split('@');
  const zona = seccion
    ? document.querySelector(`[data-tour="${CSS.escape ? CSS.escape(seccion) : seccion}"]`)
    : null;
  const cands = [];
  for (const el of document.querySelectorAll(CONTROLES)) {
    if (!visible(el)) continue;
    if (zona && !zona.contains(el)) continue;      // sólo los de esa sección
    if (normalizar(etiquetaDe(el)) === busco) cands.push(el);
  }
  // ese botón ya no está (otra pantalla, otra lista): se marca la sección, que sigue existiendo
  if (!cands.length && zona) return visible(zona) ? zona : zona;
  if (ctx && cands.length > 1) {
    // el que está en ESA fila; si esa fila ya no está, se sigue con todos (mejor marcar algo
    // parecido que no marcar nada)
    const enSuFila = cands.filter((el) => contextoDe(el, busco).includes(ctx)
      || ctx.includes(contextoDe(el, busco)));
    if (enSuFila.length) return elegirEntre(enSuFila);
  }
  return elegirEntre(cands);
}

export default { normalizar, etiquetaDe, identificar, buscar, rectDeColumna, rectDeAncla,
                 esDelAncla, sePuedeGrabar, etiquetaColumna };
