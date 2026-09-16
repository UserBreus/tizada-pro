/**
 * MOTOR DE AYUDA GUIADA — el tutorial paso a paso, estilo tutorial de videojuego.
 *
 * Oscurece la pantalla, deja ILUMINADO el campo o botón exacto que hay que usar y muestra un
 * globo con la consigna. El paso avanza cuando el usuario HACE la acción de verdad (decisión del
 * usuario: se aprende haciendo), y siempre queda una salida por si algo se traba.
 *
 * El CONTENIDO ya no se escribe a mano: el usuario GRABA lo que hace y el sistema arma los
 * carteles con `diccionario.js`. Acá está sólo el mecanismo. Para que el motor pueda iluminar
 * un elemento, ese elemento tiene que estar marcado en el JSX con `data-tour="id"`.
 *
 * ── LO QUE MIRA EL MOTOR PARA AVANZAR (y por qué) ──────────────────────────────────────────────
 * Hay DOS mecanismos, y el orden importa:
 *   1. `hecho(E, E0)` — EL ESTADO REAL de la app (lo arma `App.jsx` en `ayudaEstado`). Si el paso
 *      lo declara, **es la única forma de avanzar**. Esto arregla dos agujeros de fondo:
 *        · tocar un botón NO es lo mismo que que la acción SALGA BIEN. Si el POST falla (ej. un
 *          nombre repetido devuelve 409) el estado no cambia y el tutorial ya no sigue contento;
 *        · los gestos del VISOR (elegir piezas, arrastrar) no se pueden detectar por clic en un
 *          ancla — antes esos pasos avanzaban SOLOS por tiempo, o sea que lo más difícil de la
 *          app era justo lo que la ayuda no verificaba.
 *      Además, si `hecho` ya da true al empezar el paso, el paso se SALTEA: no se pide lo hecho.
 *   2. DOM (clic en el ancla / campo que se vacía) — para los pasos que no declaran `hecho`.
 *      OJO: React limpia el `value` por asignación directa y el navegador NO emite `input` en ese
 *      caso → hay que MIRAR el valor (poll), no escuchar el evento (ver `vigilarVaciado`).
 *
 * NO toca los datos del usuario: la acción real siempre la hace la persona.
 */
import React, { useState, useEffect, useLayoutEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { aGuion, pasoSuperado, explicarModal, queAtender } from './guion';
import { explicar, AVISOS_CONOCIDOS, fichaVentana, COLUMNAS_CONOCIDAS, explicarColumna } from './diccionario';
import { buscar, normalizar, identificar, etiquetaDe, rectDeAncla, esDelAncla, sePuedeGrabar, etiquetaColumna,
         elegidasEn, estaApagado, motivoApagado, anclaEfectiva, roleDeColumna, esCampo,
         gestoGenerico, esArrastre } from './localizar';
import { ubicarGlobo } from './tutor_pos';
import CursorGuia from './cursor';

const MARGEN = 8;          // aire entre el elemento iluminado y el recorte
const REINTENTO = 250;     // cada cuánto se busca el elemento que todavía no apareció
const LATIDO = 200;        // cada cuánto se revisa el ESTADO para ver si el paso ya se cumplió
const ESPERA_ESCAPE = 15000; // si `hecho` no se cumple en este rato, se ofrece seguir igual
const LS_PROGRESO = 'tizada_ayuda_progreso';   // {guiaId, idx} para poder retomar

/**
 * CÓMO SE LLEGA A CADA PANTALLA. La ayuda mira DÓNDE ESTÁ el usuario y, si no está donde el paso
 * necesita, no lo teletransporta: le va marcando los botones hasta llegar. Cada destino dice qué
 * botón tocar y, si a su vez necesita estar en otro lado, se encadena solo (`necesita`).
 */
const RUTAS = {
  'tab:pedidos':      { ancla: 'nav-pedidos',   texto: 'Primero vamos a Pedidos. Tocá acá.' },
  'tab:config':       { ancla: 'nav-config',    texto: 'Primero vamos a Configuración. Tocá acá.' },

  // ── Pantallas del panel de Configuración ─────────────────────────────────────────────────────
  'sub:dashboard':    { ancla: 'nav-config',    texto: 'Volvé al panel de Configuración tocando acá.' },
  'sub:productos':    { ancla: 'cfg-productos', texto: 'Entrá a «Moldería».', necesita: { tab: 'config', sub: 'dashboard' } },
  'sub:columnas':     { ancla: 'cfg-columnas',  texto: 'Entrá a «Planillas».', necesita: { tab: 'config', sub: 'dashboard' } },
  'sub:reglas':       { ancla: 'cfg-reglas',    texto: 'Entrá a «Reglas de planilla».', necesita: { tab: 'config', sub: 'dashboard' } },
  'sub:telas':        { ancla: 'cfg-telas',     texto: 'Entrá a «Telas».', necesita: { tab: 'config', sub: 'dashboard' } },
  'sub:nesting':      { ancla: 'cfg-nesting',   texto: 'Entrá a «Reglas de Nesting».', necesita: { tab: 'config', sub: 'dashboard' } },
  'sub:fuentes':      { ancla: 'cfg-fuentes',   texto: 'Entrá a «Catálogo de Fuentes».', necesita: { tab: 'config', sub: 'dashboard' } },
  'sub:perfil':       { ancla: 'cfg-perfil',    texto: 'Entrá a «Perfil de color».', necesita: { tab: 'config', sub: 'dashboard' } },
  'sub:usuarios':     { ancla: 'cfg-usuarios',  texto: 'Entrá a «Usuarios y permisos».', necesita: { tab: 'config', sub: 'dashboard' } },
  'sub:publicacion':  { ancla: 'cfg-publicacion', texto: 'Entrá a «Publicación».', necesita: { tab: 'config', sub: 'dashboard' } },

  // ⚠️ A los AJUSTES de una moldería no se entra directo: primero hay que ABRIR una moldería de la
  // grilla. Sin este paso, el tutorial marcaba un botón del menú lateral que todavía no existe.
  // 🔴 SE MARCA LA GRILLA ENTERA, NO UNA TARJETA. `molde-tarjeta` es SIEMPRE la primera de la
  // grilla: si el tutorial es de otra moldería, mandaba a abrir la equivocada y todos los pasos
  // siguientes terminaban configurando el molde que no era (auditoría de Configuración,
  // 2026-09-01). El paso que viene después ya dice cuál es —«Tocá "Camiseta de futbol"»—.
  // `elige`: esto NO lo puede hacer el sistema por vos —hay que decidir CUÁL moldería— así que
  // el globo no ofrece «Llevame igual» (no llevaría a ningún lado): ofrece saltear el paso.
  'molde:abierto':    { ancla: 'molde-grilla', elige: true, texto: 'Abrí la moldería con la que vas a trabajar: tocá su tarjeta.', necesita: { tab: 'config', sub: 'productos' } },
  // 🔴 Y EL CAMINO DE VUELTA. Si quedaste DENTRO de una moldería, un paso que necesita la grilla
  // (elegir otra, o la tarjeta de ésta) no se podía cumplir nunca: no había ruta y el tutorial se
  // quedaba en «No encuentro ese lugar» con la pantalla equivocada delante.
  'molde:grilla':     { ancla: 'molde-volver', texto: 'Volvé a la lista de molderías con «⬅ Molderías».', necesita: { tab: 'config', sub: 'productos' } },
  'ajuste:menu':      { ancla: 'ajuste-volver', texto: 'Volvé al menú de ajustes tocando acá.' },

  // ── EL PEDIDO ES UN WIZARD EN FILA: diseño → moldes → arte → planilla → resultados ──────────
  // ⚠️ EL CAMINO DEPENDE DE DÓNDE ESTÁS: para ADELANTE se usa el botón de avanzar de cada paso;
  // para ATRÁS, el botón de volver **de la pantalla en la que estás parado**, que NO es el mismo
  // en todas. Cuando esto no se contemplaba, desde la Planilla el tutorial marcaba «← Diseños»
  // (que sólo existe en el paso Arte), no encontraba nada, y a los 5 s el «seguir igual»
  // TELETRANSPORTABA al usuario fuera de su pedido. Por eso son funciones de `donde`.
  // El paso 1 (elegir el diseño) es el principio del wizard: desde `moldes` se vuelve con
  // «← Diseño»; desde más adelante hay que retroceder de a un paso.
  'paso:diseno': (d) => d.paso === 'moldes'
    ? { ancla: 'pedido-volver-diseno', texto: 'Volvé al diseño con «← Diseño».' }
    : { ancla: 'pedido-volver-diseno', texto: 'Volvé al diseño con «← Diseño».', necesita: { tab: 'pedidos', paso: 'moldes' } },
  'paso:moldes': (d) => d.paso === 'diseno'
    ? { ancla: 'pedido-ir-moldes', texto: 'Pasá a los moldes con «Elegir los moldes».' }
    : d.paso === 'arte'
    ? { ancla: 'pedido-volver-moldes', texto: 'Volvé a los moldes con «← Moldes».' }
    // desde planilla/resultados hay que retroceder de a un paso (cada pantalla tiene SU botón)
    : { ancla: 'pedido-volver-moldes', texto: 'Volvé a los moldes con «← Moldes».', necesita: { tab: 'pedidos', paso: 'arte' } },
  'paso:arte': (d) => d.paso === 'planilla'
    ? { ancla: 'planilla-volver-arte', texto: 'Volvé al arte con «← Arte».' }
    : d.paso === 'resultados'
      ? { ancla: 'planilla-volver-arte', texto: 'Volvé al arte con «← Arte».', necesita: { tab: 'pedidos', paso: 'planilla' } }
      : d.paso === 'diseno'
        ? { ancla: 'pedido-ir-moldes', texto: 'Pasá a los moldes con «Elegir los moldes».' }
        : { ancla: 'pedido-ir-arte', texto: 'Pasá al arte con «Cargar el arte».', necesita: { tab: 'pedidos', paso: 'moldes' } },
  'paso:planilla': (d) => d.paso === 'resultados'
    ? { ancla: 'resultados-volver-planilla', texto: 'Volvé a la planilla con «← Planilla».' }
    : { ancla: 'arte-siguiente', texto: 'Pasá a la planilla con «A la planilla».', necesita: { tab: 'pedidos', paso: 'arte' } },
  // A «resultados» NO se llega con un botón: se llega GENERANDO la tizada. Por eso no hay ruta:
  // la guía llega ahí sola, siguiendo el flujo (nunca hay que «volver» a resultados).

  // Los 10 ajustes de la moldería: un botón por pantalla, todos detrás de abrir la moldería.
  ...Object.fromEntries([
    ['molderia', 'Moldería'], ['variables', 'Variables'], ['diseno', 'Plantilla'],
    ['planilla', 'Planilla'], ['nestingsel', 'Nesting'], ['telas', 'Telas asignadas'],
    ['borde', 'Borde de corte'], ['etiqueta', 'Etiqueta'], ['editable', 'Editable'],
    ['terminologia', 'Nombres'],
  ].map(([id, nom]) => [`ajuste:${id}`, {
    ancla: `ajuste-${id}`, texto: `Entrá a «${nom}».`,
    necesita: { tab: 'config', sub: 'productos', molde: 'abierto', ajuste: 'menu' },
  }])),
};

/** La ruta puede depender de dónde está parado el usuario (los botones de volver no son iguales). */
const rutaDe = (clave, donde) => {
  const r = RUTAS[clave];
  return typeof r === 'function' ? r(donde || {}) : r;
};

/** Devuelve el paso-PUENTE que hay que hacer ahora para acercarse al destino, o null si ya llegó. */
/**
 * QUÉ PARTES DEL DESTINO IMPORTAN — según a qué SECCIÓN va el paso.
 *
 * 🔴 CADA PASO GUARDA LA PANTALLA ENTERA, incluida la del wizard del pedido (`paso`), aunque el
 * trabajo sea en Configuración: es el estado en el que quedó el pedido, no algo que el paso
 * necesite. Al tomarlo como destino, un tutorial de Configuración abría pidiendo **«Volvé al
 * diseño con "← Diseño"»** — un botón que ahí ni existe (reporte del usuario 2026-09-01, con
 * «Cargar molde» en 1/46). El `paso` del pedido sólo vale si el destino ES el pedido; y `sub`,
 * `molde` y `ajuste` sólo valen dentro de Configuración.
 */
function clavesDe(destino) {
  if (destino.tab === 'pedidos') return ['tab', 'paso'];
  if (destino.tab === 'config') return ['tab', 'sub', 'molde', 'ajuste'];
  return ['tab', 'sub', 'paso', 'molde', 'ajuste'];
}

function puente(destino, donde) {
  if (!destino) return null;
  // El ORDEN importa: primero la sección, después la pantalla, después abrir la moldería y recién
  // ahí su ajuste. Al revés, se marcaría un botón que todavía no está en pantalla.
  const claves = clavesDe(destino);
  for (const k of claves) {
    const q = destino[k];
    if (!q || donde[k] === q) continue;               // no pedido, o ya estamos
    const r = rutaDe(`${k}:${q}`, donde);
    if (!r) continue;                                  // sin ruta conocida: lo resuelve el propio guion
    const previo = r.necesita ? puente(r.necesita, donde) : null;   // ¿hace falta llegar a otro lado antes?
    if (previo) return previo;
    // 🔴 LA BARRA LATERAL NO SE MARCA (pedido del usuario). Cambiar de sección no es lo que el
    // tutorial enseña: el motor lleva solo y arranca directo en lo que importa. Los puentes de
    // ADENTRO de una pantalla («Entrá a Moldedería») sí se marcan, porque ésos SÍ son el trabajo.
    if (String(r.ancla || '').startsWith('nav-')) return { llevarSolo: { [k]: q } };
    return { ancla: r.ancla, texto: r.texto, accion: 'click', esPuente: true, elige: !!r.elige };
  }
  return null;
}

/**
 * ¿El paso sirve SÓLO para llevar al usuario a una pantalla? Se sabe solo: su ancla es exactamente
 * el botón que la tabla de RUTAS usa para llegar al destino que el paso pide. Si ya estamos ahí, el
 * paso no tiene nada que pedir — sería el absurdo de decir «tocá Pedidos» estando en Pedidos.
 */
function esPasoNav(p, donde) {
  if (!p || !p.ir || !p.ancla) return false;
  // ⚠️ Un paso 'ver' NUNCA es puro tránsito: TIENE ALGO QUE CONTAR. En los recorridos
  // explicativos el primer paso suele señalar el mismo botón por el que se entró («Entrá a Telas»
  // → «Acá se dice qué telas puede usar este molde»), y saltearlo se comía justo la explicación
  // más importante, la que dice de qué se trata la pantalla.
  if (p.accion === 'ver') return false;
  const utiles = clavesDe(p.ir);
  return Object.entries(p.ir).some(([k, v]) => utiles.includes(k)
    && (rutaDe(`${k}:${v}`, donde) || {}).ancla === p.ancla);
}

/** Texto que tiene ahora mismo el campo de ese ancla ('' si no hay campo). */
function valorDe(ancla) {
  // por `data-tour` o por texto: `buscar` resuelve las dos formas (antes sólo la primera, y los
  // campos sin marca quedaban afuera)
  const el = buscar(ancla);
  if (!el) return '';
  const campo = el.matches('input, textarea, select') ? el : el.querySelector('input, textarea, select');
  return campo ? (campo.value || '').trim() : '';
}

/**
 * Vigila que un campo pase de TENER TEXTO a QUEDAR VACÍO: así se sabe que la persona lo confirmó
 * (con Enter o con el botón), porque el sistema limpia el campo al aceptarlo.
 *
 * OJO — POR QUÉ ES UN POLL Y NO UN LISTENER: React limpia el `value` por asignación directa y el
 * navegador NO emite ningún evento `input` en ese caso. Escuchar el evento es esperar algo que no
 * ocurre jamás (y una prueba que lo dispare a mano da un falso OK). Hay que MIRAR el valor.
 */
function vigilarVaciado(anclas, alConfirmar) {
  let tenia = anclas.some(a => valorDe(a).length > 0);
  return setInterval(() => {
    const val = anclas.map(valorDe).find(v => v.length > 0) || '';
    if (val) { tenia = true; return; }
    if (tenia) { tenia = false; alConfirmar(); }
  }, 150);
}

/**
 * CUÁNTAS OPCIONES HAY PUESTAS AHORA en el paso «elegí N de esta lista» (null = no se puede medir).
 *
 * 🔴 SE MIDE LA PANTALLA, NO SE CUENTAN CLICS. Contando clics, dos toques en el AIRE de la lista
 * cumplían el paso, y tocar dos opciones YA elegidas —que las DESMARCA— lo cumplía dejando el
 * pedido con menos de lo que tenía: el tutorial daba por bien hecho justo lo contrario de lo que
 * pedía (verificado en pantalla, auditoría 2026-08-31). Es la misma regla que ya valía para
 * `cuantos`: lo que cuenta es el TOTAL que hay puesto.
 */
function elegidasDelPaso(paso) {
  if (!paso || (paso.cuantas || 1) <= 1 || !paso.ancla) return null;
  try { return elegidasEn(paso.ancla); } catch { return null; }
}

/** Evalúa `hecho` sin que un guion roto pueda tirar abajo la ayuda. */
function seCumplio(paso, E, E0) {
  if (!paso || typeof paso.hecho !== 'function' || !E || !E0) return false;
  try { return !!paso.hecho(E, E0); } catch { return false; }
}

/** Rectángulo del control del paso (por `data-tour` o por su texto), siguiéndolo si se mueve. */
function useAncla(ancla, activo) {
  const [rect, setRect] = useState(null);
  const elRef = useRef(null);
  useEffect(() => {
    if (!activo || !ancla) { setRect(null); elRef.current = null; return; }
    let vivo = true;
    const medir = () => {
      if (!vivo) return;
      // No es un `querySelector` a secas: el ancla puede ser un `txt:…` (un control sin
      // `data-tour`, que son la mayoría) y eso lo resuelve el localizador.
      const el = buscar(ancla);
      elRef.current = el || null;
      if (!el) { setRect(null); return; }
      // El recuadro lo decide SIEMPRE `rectDeAncla` (el mismo que usa el editor): una columna se
      // ilumina entera —título, todas las casillas y su desplegable—, un botón es su botón.
      const nuevo = rectDeAncla(ancla, el);
      // Sólo se avisa si de verdad SE MOVIÓ. Antes se creaba un objeto nuevo cada 250 ms, así que
      // todo el tutorial se re-dibujaba 4 veces por segundo sin motivo (y eso alimentaba el lazo
      // de medición del globo). Ahora, quieto el elemento, no hay re-render.
      setRect(prev => {
        if (!nuevo || !prev) return (nuevo === prev) ? prev : nuevo;
        const igual = Math.abs(prev.x - nuevo.x) < 0.5 && Math.abs(prev.y - nuevo.y) < 0.5
          && Math.abs(prev.w - nuevo.w) < 0.5 && Math.abs(prev.h - nuevo.h) < 0.5;
        return igual ? prev : nuevo;
      });
    };
    medir();
    // El elemento puede tardar (cambio de pantalla, carga de datos) → se reintenta.
    const t = setInterval(medir, REINTENTO);
    window.addEventListener('scroll', medir, true);
    window.addEventListener('resize', medir);
    return () => { vivo = false; clearInterval(t); window.removeEventListener('scroll', medir, true); window.removeEventListener('resize', medir); };
  }, [ancla, activo]);
  return [rect, elRef];
}

/**
 * Globo de la consigna. Hay tipos bien distintos a propósito:
 *   ACCIÓN  (cyan, «TENÉS QUE HACER ESTO»): el usuario tiene que tocar/escribir algo. No avanza
 *           solo: espera la acción de verdad.
 *   GESTO   (cyan, «HACELO EN EL MOLDE»): se trabaja en el visor. Avanza cuando el estado real
 *           dice que el gesto ocurrió — nunca por tiempo.
 *   INFO    (violeta, «PARA QUE SEPAS»): sólo explica para qué sirve ese espacio. Avanza solo
 *           después de un ratito, con una barra que muestra cuánto falta.
 * El PUENTE (ámbar) es una acción especial: llevar al usuario a la pantalla que corresponde.
 */
function Globo({ rect, paso, idx, total, onAtras, onCerrar, esperando, puente, progreso, trabado, onSeguirIgual, escape,
                pregunta, onResponder, llevan, onSaltear, onSiguiente, apagado }) {
  const ANCHO = 340;
  const [n, setN] = useState('');   // la respuesta a «¿cuántas?», mientras se tipea
  const esInfo = !puente && paso.accion === 'ver';
  const esGesto = !puente && paso.accion === 'gesto';
  const esEspera = paso.accion === 'espera';
  const col = (puente || esEspera) ? 'var(--warning, #e0a020)' : esInfo ? '#a78bfa' : 'var(--accent)';
  const fondo = (puente || esEspera) ? 'linear-gradient(180deg,#231a0d,#171208)'
    : esInfo ? 'linear-gradient(180deg,#171526,#100f1b)' : 'linear-gradient(180deg,#0b1c22,#081418)';
  const rotulo = esEspera ? (paso.esModal ? 'Primero este aviso' : 'Esperá un momento') : pregunta ? 'Una pregunta' : puente ? 'Te llevo hasta ahí' : esInfo ? 'Para que sepas' : esGesto ? 'Hacelo en el molde' : 'Hacé esto';
  const icono = esEspera ? (paso.esModal ? '!' : '⏳') : puente ? '➜' : esInfo ? 'i' : esGesto ? '✋' : '☝';
  const vh = window.innerHeight, vw = window.innerWidth;
  // ── DÓNDE VA EL GLOBO: NUNCA ENCIMA DE LO QUE HAY QUE TOCAR ─────────────────────────────────
  // Antes se asumía que el globo medía 200 px de alto. Con un texto largo (o con la nota y el
  // botón de escape) mide bastante más, y al no entrar abajo se lo mandaba arriba **tapando el
  // botón** que justamente había que tocar — sobre todo en la barra inferior del pedido, que es
  // donde viven «Cargar el arte», «A la planilla» y «Enviar». Ahora se MIDE el globo de verdad y,
  // si no entra ni arriba ni abajo, se pone AL COSTADO. La caja del ancla es zona prohibida.
  const cajaRef = useRef(null);
  const [tam, setTam] = useState({ w: ANCHO, h: 210 });
  useLayoutEffect(() => {
    const el = cajaRef.current; if (!el) return;
    // ⚠️ SE MIDE EL ALTO **NATURAL** (`scrollHeight`), NO EL RENDERIZADO — si no, LAZO INFINITO.
    // Cuando el globo no entra en ningún hueco se le pone un `maxHeight`. La app tiene
    // `* { box-sizing: border-box }` (index.css:44), así que con ese tope el alto RENDERIZADO pasa
    // a ser EXACTAMENTE el hueco → al medirlo, «ahora entra» → se le saca el tope → vuelve a no
    // entrar → se lo pone… y así para siempre: React corta con «Maximum update depth exceeded»
    // (error #185, lo vio el usuario en pantalla). `scrollHeight` es el alto del CONTENIDO y NO
    // cambia cuando lo capamos, así que la decisión de dónde ponerlo es estable.
    const h = el.scrollHeight + 3;          // + el borde (scrollHeight no lo incluye)
    const w = el.offsetWidth;
    // Devolver `prev` cuando no cambió nada evita re-renderizar de gusto (y es la segunda red).
    setTam(prev => (Math.abs(h - prev.h) > 2 || Math.abs(w - prev.w) > 2) ? { w, h } : prev);
    // Se mide sólo cuando cambia lo que ocupa lugar (el texto del paso, los avisos, la ventana):
    // sin lista de dependencias corría en CADA render, que es justo lo que alimentaba el lazo.
  }, [paso.texto, paso.nota, trabado, escape, esInfo, puente, vw, vh, !!pregunta, !!llevan,
      apagado && apagado.texto]);
  // La cuenta vive en `tutor_pos.js` (función pura) para poder probarla sin navegador: el chequeo
  // del build verifica que el globo NUNCA se solape con el elemento resaltado.
  const { top, left, flecha, maxAlto } = ubicarGlobo(rect, tam, vw, vh, MARGEN + 14, 12);
  return (
    <div ref={cajaRef} data-tutor-globo="1"
      style={{ position: 'fixed', top, left, width: ANCHO, zIndex: 100002, background: fondo,
      border: `1.5px solid ${col}`, borderRadius: 14, padding: 16,
      // Si no entraba en ningún hueco, se achica y scrollea adentro (nunca encima del control).
      ...(maxAlto ? { maxHeight: maxAlto, overflowY: 'auto' } : null),
      boxShadow: `0 18px 50px rgba(0,0,0,0.7), 0 0 0 1px ${col}44` }}>
      {flecha && rect && (() => {
        // La flecha apunta al CENTRO DEL ANCLA, no al centro del globo: cuando el globo se corre
        // para no salirse de la pantalla, si la flecha quedaba fija al 50% señalaba cualquier cosa.
        const cx = Math.min(Math.max(14, rect.x + rect.w / 2 - left), tam.w - 14);
        return (
          <span style={{ position: 'absolute', left: cx, marginLeft: -7, [flecha === 'arriba' ? 'top' : 'bottom']: -8,
            width: 14, height: 14, background: fondo.includes('231a') ? '#231a0d' : fondo.includes('1715') ? '#171526' : '#0b1c22',
            borderLeft: `1.5px solid ${col}`, borderTop: `1.5px solid ${col}`,
            transform: flecha === 'arriba' ? 'rotate(45deg)' : 'rotate(225deg)' }} />
        );
      })()}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <span style={{ width: 20, height: 20, borderRadius: '50%', background: col, color: '#04141a',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 900, flexShrink: 0 }}>{icono}</span>
        <span style={{ fontSize: 10.5, fontWeight: 800, letterSpacing: 0.7, textTransform: 'uppercase', color: col }}>{rotulo}</span>
        {/* 🔴 EL CONTADOR SE VE SIEMPRE, TAMBIÉN EN UN PUENTE. Sin él, mientras el tutorial te
            lleva de una pantalla a otra no se sabe en qué paso se está — y si el puente no se
            puede resolver (el botón está apagado), cada «Siguiente» se comía un paso REAL sin que
            se notara: en la prueba se comió los 7 de la planilla (auditoría 2026-08-31). */}
        <span style={{ marginLeft: 'auto', fontSize: 10.5, color: 'var(--text-muted)' }}>{`${idx + 1}/${total}`}</span>
        <button onClick={onCerrar} title="Salir de la ayuda"
          style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 15, lineHeight: 1 }}>✕</button>
      </div>
      <div style={{ fontSize: 14.5, color: '#fff', lineHeight: 1.45, fontWeight: 600 }}>{pregunta ? pregunta.pregunta : paso.texto}</div>
      {!pregunta && paso.nota && <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.4, marginTop: 7 }}>{paso.nota}</div>}
      {/* LA PREGUNTA: lo que el sistema no puede deducir se pide, no se adivina. */}
      {pregunta && (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 11 }}>
          <input type="number" min="1" max="99" value={n} autoFocus
            onChange={(e) => setN(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && Number(n) >= 1) onResponder(Math.min(99, Number(n))); }}
            style={{ width: 72, padding: '7px 9px', borderRadius: 8, fontSize: 15, fontWeight: 700,
              textAlign: 'center', border: '1px solid var(--border-light)',
              background: 'rgba(255,255,255,0.06)', color: '#fff' }} />
          <button type="button" disabled={!(Number(n) >= 1)}
            onClick={() => onResponder(Math.min(99, Number(n)))}
            style={{ padding: '7px 14px', borderRadius: 8, fontSize: 13, fontWeight: 700,
              cursor: Number(n) >= 1 ? 'pointer' : 'not-allowed', opacity: Number(n) >= 1 ? 1 : 0.45,
              border: '1px solid var(--accent)', background: 'rgba(0,216,245,0.14)', color: 'var(--accent)' }}>
            Seguir
          </button>
        </div>
      )}
      {/* EL CONTADOR: cuántas van de las que dijo. */}
      {!pregunta && llevan && llevan.total > 0 && (
        <div style={{ fontSize: 12.5, color: 'var(--accent)', fontWeight: 700, marginTop: 9 }}>
          {Math.min(llevan.hechas, llevan.total)} de {llevan.total}{llevan.unidad ? ' ' + llevan.unidad + (llevan.total === 1 ? '' : 's') : ''}
        </div>
      )}
      {/* Mientras el paso se prepara: NO se dice «buscando» ni «no encuentro» — el sistema sabe a
          dónde va y lo resuelve solo (ver el efecto que decide en el Tour). */}
      {esperando && !paso.esVentanaFalta && <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 9 }}>Preparando este paso…</div>}
      {paso.manual && !esperando && (
        // 🔴 ESTE PASO NO AVANZA SOLO, Y SE DICE. Una columna se carga fila por fila y un campo se
        // escribe: el primer clic no es «hecho». Lo termina la persona con «Siguiente →».
        <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 9 }}>
          {paso.manualPor === 'campo'
            ? 'Escribí lo que necesites. El tutorial te espera: cuando termines, tocá «Siguiente →».'
            : 'Cargá lo que necesites en esta columna y, cuando termines, tocá «Siguiente →».'}
        </div>
      )}
      {/* 🔴 EL BOTÓN ESTÁ APAGADO — Y SE DICE POR QUÉ. Antes el tutorial iluminaba un botón que no
          se puede tocar, decía «Tocá lo que está marcado» y encima el velo TAPABA el aviso de la
          pantalla que explica qué falta: no había forma de saber qué hacer (auditoría 2026-08-31,
          paso 5/23 de «Camiseta» con «Cargar el arte» apagado porque faltaban prendas). */}
      {apagado && !trabado && (
        <div style={{ marginTop: 10, padding: '9px 11px', borderRadius: 9, background: 'rgba(224,160,32,0.12)', border: '1px solid rgba(224,160,32,0.35)' }}>
          <div style={{ fontSize: 11.5, color: 'var(--warning, #e0a020)', fontWeight: 700, lineHeight: 1.4 }}>
            Ese botón todavía está apagado.
          </div>
          {!!apagado.texto && (
            <div style={{ fontSize: 11.5, color: 'var(--text-secondary)', lineHeight: 1.45, marginTop: 4 }}>
              {apagado.texto}
            </div>
          )}
          <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.4, marginTop: 4 }}>
            Resolvé eso y se prende solo; el tutorial sigue acá esperando.
          </div>
        </div>
      )}
      {/* 🔴 ACÁ IBA «No encuentro ese lugar en pantalla». SE FUE (pedido del usuario 2026-09-01):
          el tutorial está grabado, así que el sistema tiene que RESOLVER —llevar, esperar la
          ventana o pasar al siguiente— y no confesarle a la persona que se perdió. La decisión
          vive en el efecto de arriba; acá no queda ningún cartel de error. */}
      {/* ESCAPE de los pasos que esperan el ESTADO: si el sistema no llegó a registrarlo (o el
          usuario lo hizo por otro camino), no puede quedar preso del tutorial. */}
      {escape && !trabado && (
        <div style={{ marginTop: 10, padding: '9px 11px', borderRadius: 9, background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border-light)' }}>
          <div style={{ fontSize: 11.5, color: 'var(--text-muted)', lineHeight: 1.4 }}>
            ¿Ya lo hiciste y sigo esperando? Puede que lo hayas resuelto por otro lado.
          </div>
          <button className="btn ghost" style={{ marginTop: 7, padding: '5px 11px', fontSize: 11.5 }} onClick={onSeguirIgual}>Ya está, seguir →</button>
        </div>
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginTop: 13 }}>
        {idx > 0 && !puente && (
          <button className="btn ghost" style={{ padding: '5px 11px', fontSize: 11.5 }} onClick={onAtras}>← Atrás</button>
        )}
        {esInfo ? (
          <div style={{ flex: 1, height: 5, borderRadius: 999, background: 'rgba(255,255,255,0.10)', overflow: 'hidden' }}>
            <div style={{ width: `${Math.round(progreso * 100)}%`, height: '100%', background: col, transition: 'width .2s linear' }} />
          </div>
        ) : (
          <span style={{ flex: 1, fontSize: 11.5, color: apagado ? 'var(--warning, #e0a020)' : col, fontWeight: 700 }}>
            {apagado ? 'Todavía no se puede tocar'
              : esEspera ? (paso.esModal ? 'Cerralo y seguimos' : 'Esperando…')
              : esGesto ? 'Hacelo y sigo solo'
              // un campo (o una columna) no avanza solo: lo cierra la persona
              : paso.manual ? (paso.manualPor === 'campo' ? 'Escribí y tocá «Siguiente →»' : 'Cargalo y tocá «Siguiente →»')
              : paso.accion === 'input' ? 'Escribilo y seguimos' : 'Tocá lo que está marcado'}
          </span>
        )}
        {/* SIGUIENTE A MANO (pedido del usuario): pasar el paso sin hacer lo que pide.
            🔴 EN UN PUENTE NO SALTEA EL PASO: LLEVA. El puente no es un paso del tutorial, es el
            camino hasta él; su «Siguiente» salteaba el paso de DESTINO —en silencio, porque el
            puente seguía igual— y el tutorial terminaba con «¡Listo!» sin haber mostrado nada
            (auditoría 2026-08-31). Ahora lleva a la pantalla y el guion sigue donde iba. */}
        {onSaltear && !pregunta && !esEspera && (() => {
          // 🔴 UN PUENTE QUE EXIGE ELEGIR NO SE PUEDE «LLEVAR» SOLO (abrir una moldería es una
          // decisión de la persona): ahí el botón saltea el paso, en vez de no hacer nada — que
          // era quedarse trabado con un botón que parecía funcionar.
          const llevar = puente && !paso.elige;
          return (
            <button className="btn ghost"
              title={(llevar ? 'Ir a esa pantalla sin tocar el botón' : 'Pasar este paso sin hacerlo') + ' (o tocá Enter)'}
              style={{ padding: '5px 11px', fontSize: 11.5, flexShrink: 0 }}
              /* el MISMO camino que la tecla Enter: una sola decisión, en el Tour */
              onClick={onSiguiente}>{llevar ? 'Llevame igual →' : 'Siguiente →'}
              <span style={{ marginLeft: 6, fontSize: 9.5, opacity: 0.6, fontWeight: 700 }}>Enter</span>
            </button>
          );
        })()}
      </div>
    </div>
  );
}

/** Globo final: la guía terminó. Antes se cerraba de golpe y no quedaba claro si había terminado. */
function GloboFin({ guia, onCerrar, saltada, salteados = 0, noAplicaron = 0, onVerIgual }) {
  // 🔴 Si quedaron pasos sin hacer, el cartel NO se va solo: la persona tiene que poder leer
  // cuántos se salteó (antes decía «¡Listo!» y se cerraba a los 5 s, aunque no se hubiera hecho
  // nada — auditoría 2026-08-31).
  useEffect(() => {
    if (salteados > 0 || noAplicaron > 0) return undefined;
    const t = setTimeout(onCerrar, 5000);
    return () => clearTimeout(t);
  }, [onCerrar, salteados, noAplicaron]);
  return (
    <div style={{ position: 'fixed', left: '50%', bottom: 40, transform: 'translateX(-50%)', width: 380, zIndex: 100002,
      background: 'linear-gradient(180deg,#0d2119,#08150f)', border: '1.5px solid var(--success, #2ecc71)', borderRadius: 14, padding: 16,
      boxShadow: '0 18px 50px rgba(0,0,0,0.7)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
        <span style={{ width: 22, height: 22, borderRadius: '50%', background: 'var(--success, #2ecc71)', color: '#04141a',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 900 }}>✓</span>
        {/* Un RECORRIDO explicativo no «se hace»: se mira. Decirle «ya estaba hecho» (que es lo que
            salía, porque nunca hay interacción) no tiene ningún sentido ahí. */}
        <span style={{ fontSize: 14, fontWeight: 800, color: '#fff' }}>
          {guia.explica ? 'Eso es todo' : salteados > 0 ? 'Terminó, pero quedaron pasos sin hacer'
            : saltada ? 'Esto ya estaba hecho' : '¡Listo!'}
        </span>
        <button onClick={onCerrar} style={{ marginLeft: 'auto', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 15 }}>✕</button>
      </div>
      {/* Lo que NO estaba en la pantalla de quien lo siguió: se dice al final, en vez de frenarlo
          paso por paso con un cartel de error. */}
      {noAplicaron > 0 && (
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8, lineHeight: 1.45 }}>
          {noAplicaron === 1
            ? 'Un paso del tutorial no estaba en tu pantalla (tu molde o tu pedido son distintos) y se pasó solo.'
            : `${noAplicaron} pasos del tutorial no estaban en tu pantalla (tu molde o tu pedido son distintos) y se pasaron solos.`}
        </div>
      )}
      <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.45 }}>
        {guia.explica
          ? <>Eso es «{guia.titulo}». Podés volver a verlo cuando quieras desde Ayuda.</>
          : salteados > 0
            ? <>De «{guia.titulo}» te salteaste <b>{salteados}</b> de {guia.pasos.length} paso{guia.pasos.length === 1 ? '' : 's'}.
                Si algo quedó sin hacer, volvé a abrirlo desde Ayuda y seguí desde ahí.</>
            : saltada
              ? <>«{guia.titulo}» ya estaba resuelto en este molde, así que no había nada que pedirte.</>
              : <>Terminaste «{guia.titulo}».</>}
      </div>
      {/* 🔴 PEDIR AYUDA Y QUE NO TE MUESTREN NADA es la peor respuesta posible: si todo estaba
          hecho, el tutorial se salteaba entero y se cerraba. Acá se puede VER igual, de corrido,
          sin que pida hacer nada (auditoría 2026-08-31). */}
      {saltada && !guia.explica && onVerIgual && (
        <button className="btn ghost" style={{ marginTop: 11, padding: '6px 12px', fontSize: 12 }}
          onClick={onVerIgual}>Verlo igual, de principio a fin →</button>
      )}
    </div>
  );
}

/**
 * VIGÍA DE LOS CARTELES DE CARGA. Cualquier superficie marcada con `data-cargando="<texto>"`
 * (el overlay de «Procesando…», el panel «Armando la tizada») frena el tutorial: mientras esté
 * visible, no se avanza ni se marca nada — se marca EL CARTEL y se pide esperar. Al desaparecer,
 * la evaluación del paso retoma sola y, como lo ya cumplido se saltea, cae en el paso correcto.
 * (Pedido del usuario 2026-08-28: «debe respetar los modales de carga».)
 */
function useCargando(activo) {
  const [carga, setCarga] = useState(null);
  useEffect(() => {
    if (!activo) { setCarga(null); return undefined; }
    const mirar = () => {
      let el = null;
      for (const c of document.querySelectorAll('[data-cargando]')) {
        const r = c.getBoundingClientRect();
        if (r.width || r.height) { el = c; break; }
      }
      if (!el) { setCarga((prev) => (prev === null ? prev : null)); return; }
      const r = el.getBoundingClientRect();
      const nuevo = { x: r.left, y: r.top, w: r.width, h: r.height,
                      texto: el.getAttribute('data-cargando') || '' };
      // sólo se avisa si cambió de verdad: si no, todo el tutorial se re-dibuja 4 veces por segundo
      setCarga((prev) => (prev && Math.abs(prev.x - nuevo.x) < 0.5 && Math.abs(prev.y - nuevo.y) < 0.5
        && Math.abs(prev.w - nuevo.w) < 0.5 && Math.abs(prev.h - nuevo.h) < 0.5
        && prev.texto === nuevo.texto) ? prev : nuevo);
    };
    mirar();
    const t = setInterval(mirar, REINTENTO);
    return () => clearInterval(t);
  }, [activo]);
  return carga;
}

/**
 * VIGÍA DE MODALES. Todos los modales del sistema llevan `data-modal="<título>"` (lo pone el
 * componente Modal). Si uno se abre en medio del tutorial y NO es del paso en curso, el motor
 * FRENA: marca el modal, lo explica y espera a que se cierre. (Pedido del usuario 2026-08-28:
 * «no puede avanzar a otros pasos si hay modales abiertos, y debe explicar qué es ese modal».)
 */
function useModalAbierto(activo) {
  const [modal, setModal] = useState(null);
  useEffect(() => {
    if (!activo) { setModal(null); return undefined; }
    const mirar = () => {
      let el = null;
      for (const c of document.querySelectorAll('[data-modal]')) {
        const r = c.getBoundingClientRect();
        if (r.width || r.height) { el = c; break; }
      }
      if (!el) { setModal((prev) => (prev === null ? prev : null)); return; }
      const r = el.getBoundingClientRect();
      const nuevo = { el, x: r.left, y: r.top, w: r.width, h: r.height,
                      titulo: el.getAttribute('data-modal') || '' };
      setModal((prev) => (prev && prev.el === el && Math.abs(prev.x - nuevo.x) < 0.5
        && Math.abs(prev.y - nuevo.y) < 0.5 && Math.abs(prev.w - nuevo.w) < 0.5
        && Math.abs(prev.h - nuevo.h) < 0.5) ? prev : nuevo);
    };
    mirar();
    const t = setInterval(mirar, REINTENTO);
    return () => clearInterval(t);
  }, [activo]);
  return modal;
}

/** El tutorial en sí: recorte + globo + detección de la acción del usuario.
 *  `soloVer` = MIRARLO, sin hacer nada: no se saltea ningún paso (aunque ya esté hecho) y cada uno
 *  avanza solo después de leerse. Es la salida para cuando el tutorial se salteaba entero y la
 *  persona se quedaba sin ver nada. */
function Tour({ guia, onCerrar, ir, donde, estado, desdePaso = 0, soloVer = false, onVerIgual }) {
  const [idx, setIdx] = useState(desdePaso);
  const [fin, setFin] = useState(null);            // null | {saltada:bool}
  // CUÁNTAS VECES. Lo que el sistema no puede deducir se pregunta: «¿cuántos diseños vas a
  // cargar?». Se guarda por paso; mientras no haya respuesta, el paso todavía no arrancó.
  const [cuantas, setCuantas] = useState({});      // {idx: n}
  // OPCIONES INTERCAMBIABLES: cuántas se tocaron ya en este paso ({idx: n}). El paso pide N de una
  // lista y no le importa CUÁLES (ver `cuantas` en guion.js).
  const [elegidas, setElegidas] = useState({});
  // 🔴 AVANCE EN CAMINO. El control de un paso casi siempre CAMBIA DE PANTALLA, y el `donde` que
  // el paso guarda es el de ANTES de tocarlo. Mientras el avance viaja (200 ms), el motor veía
  // «no estás donde este paso pide» y te DEVOLVÍA a la pantalla anterior: en Configuración,
  // entrar a «Moldería» te rebotaba al panel (verificado 2026-09-01). Con esto, nada navega ni
  // muestra puentes hasta que el paso termine de avanzar.
  const [avanzando, setAvanzando] = useState(false);
  const crudo = guia.pasos[idx];
  const preguntando = crudo?.cuantos && cuantas[idx] == null && !pasoSuperado(crudo, estado, donde || {}) ? crudo.cuantos : null;
  // Con la respuesta puesta, el paso se cumple cuando el TOTAL llega a esa cantidad.
  // 🔴 Es el TOTAL, no «N más desde que respondió»: lo YA PRESIONADO también se reconoce. Pasó en
  // pantalla (2026-08-28): con 2 diseños ya marcados y respuesta «2», la cuenta relativa decía
  // «0 de 2» y pedía tocar botones que ya estaban tocados — y tocarlos de nuevo los DESMARCABA.
  const pasoGuion = React.useMemo(() => {
    const n = cuantas[idx];
    if (!crudo || !crudo.cuantos || n == null) return crudo;
    const mide = crudo.cuantos.mide;
    const seguro = (E) => { try { return Number(mide(E)) || 0; } catch { return 0; } };
    return { ...crudo, hecho: (E) => seguro(E) >= n };
  }, [crudo, cuantas[idx]]);   // eslint-disable-line react-hooks/exhaustive-deps
  // ¿ESTE PASO YA QUEDÓ ATRÁS? La persona puede abrir el tutorial con el trabajo empezado (ya
  // eligió el diseño, ya está en la planilla): un paso de una etapa anterior YA CUMPLIDA se
  // saltea, y sobre todo NO se la arrastra de vuelta a esa pantalla (su `ir` no corre).
  // en modo MIRAR no se saltea nada: la idea es justamente ver todos los pasos
  const superado = !soloVer && !fin && pasoSuperado(pasoGuion, estado, donde || {});
  const omitir = superado;
  // AYUDA INTELIGENTE: si el usuario no está en la pantalla que el paso necesita, primero se le
  // marca el camino (un botón por vez) en vez de saltar solo. Cuando llega, sigue el guion.
  const salto0 = (!omitir && !avanzando && pasoGuion?.ir) ? puente(pasoGuion.ir, donde || {}) : null;
  // Un puente de BARRA LATERAL no se le muestra a nadie: se hace solo y el tutorial sigue con lo
  // suyo. `ir()` es la misma función que ya usaba el botón «seguir igual».
  useEffect(() => {
    if (salto0 && salto0.llevarSolo && ir) ir(salto0.llevarSolo);
  }, [salto0 && JSON.stringify(salto0.llevarSolo)]);   // eslint-disable-line react-hooks/exhaustive-deps
  // MIRAR: no se le pide a nadie que toque el botón del camino — se lleva solo y se sigue
  const salto = (soloVer || (salto0 && salto0.llevarSolo)) ? null : salto0;
  // Mientras el cambio de sección está en camino, el paso todavía no puede pedir nada.
  const enViaje = !!(salto0 && salto0.llevarSolo);
  // ¿HAY UNA VENTANA DE TRABAJO a la vista? (el sistema procesando algo) — el tutorial frena y
  // explica que hay que esperar en vez de pedir el paso siguiente.
  const carga = useCargando(!fin);
  // ¿HAY UN MODAL ABIERTO? Ninguna acción del guion puede pedirse por detrás de una ventana.
  const modalAb = useModalAbierto(!fin);
  const bloqueoModal = React.useMemo(() => {
    // ⚠️ NO se anula por la carga: un modal ENCIMA de una carga es lo primero que hay que
    // resolver (ver `queAtender`). Antes acá decía `|| carga` y la carga de atrás ganaba.
    if (!modalAb) return null;
    // el paso «esperar aviso» del editor: ese modal ES el paso, no un bloqueo
    if (pasoGuion?.accion === 'modalPaso'
        && (!pasoGuion.modal || normalizar(modalAb.titulo || '').includes(normalizar(pasoGuion.modal)))) return null;
    try {
      for (const a of [pasoGuion?.ancla, salto?.ancla]) {
        if (!a) continue;
        const e = buscar(a);
        if (e && modalAb.el.contains(e)) return null;   // el paso ES de este modal
      }
    } catch { /* si no se puede saber, mejor frenar */ }
    return modalAb;
  }, [modalAb, pasoGuion?.accion, pasoGuion?.ancla, pasoGuion?.modal, salto?.ancla]);
  // ⚠️ ESTE BLOQUE VA ANTES DE `paso`, Y NO ES COSMÉTICO: `paso` lee `modalDelPaso`, y leer una
  // `const` antes de su declaración es ReferenceError (zona muerta temporal) → se cae TODO React y
  // la pantalla queda NEGRA. No saltaba nunca porque el `&&` de `carga && !modalDelPaso` corta sin
  // carga a la vista: reventaba sólo al aparecer una ventana de trabajo (cargar el arte) con el
  // tutorial abierto — el momento exacto en que el tutorial tiene que frenar y explicar la espera.
  // el «esperar aviso» ilumina lo que espera cuando está a la vista — un MODAL o una CARGA
  // (el editor deja elegir cualquiera de los dos: los títulos salen de AVISOS_CONOCIDOS).
  const avisoAb = modalAb || (carga ? { x: carga.x, y: carga.y, w: carga.w, h: carga.h, titulo: carga.texto } : null);
  const modalDelPaso = (pasoGuion?.accion === 'modalPaso' && avisoAb
    && (!pasoGuion.modal || normalizar(avisoAb.titulo || '').includes(normalizar(pasoGuion.modal))))
    ? avisoAb : null;
  // QUÉ SE ATIENDE PRIMERO: lo de adelante (ver `queAtender` en guion.js).
  const atender = queAtender({ modalTapando: !!bloqueoModal,
                               // hay un modal abierto y NO bloquea = el paso se hace ahí adentro
                               modalDelPasoAbierto: !!(modalAb && !bloqueoModal),
                               hayCarga: !!carga, cargaEsDelPaso: !!modalDelPaso });
  // 🔴 ¿ESTE MODAL TIENE UN SOLO BOTÓN? Entonces no hay nada que elegir: se marca ESE BOTÓN y se
  // dice cómo se llama. La ventana entera se marca sólo cuando hay VARIOS botones —ahí sí hay que
  // leer y decidir— (pedido del usuario 2026-08-31: «acá tengo uno solo»).
  // ⚠️ SIN `useMemo` a propósito: el contenido de un modal cambia (aparece un segundo botón, se
  // habilita otro) sin que cambie el objeto del modal, y un memo se quedaba con la cuenta vieja.
  const botonUnico = (() => {
    if (atender !== 'modal' || !bloqueoModal || !bloqueoModal.el) return null;
    try {
      const bs = [...bloqueoModal.el.querySelectorAll('button, [role="button"], a[href]')]
        .filter((b) => {
          const r = b.getBoundingClientRect();
          if (!(r.width || r.height)) return false;
          const t = (b.innerText || '').trim();
          return t && t.length < 40 && !/^[×✕✖x]$/i.test(t);   // el aspa de cerrar no cuenta
        });
      return bs.length === 1 ? bs[0] : null;
    } catch { return null; }
  })();
  const paso = atender === 'modal'
    ? (botonUnico
        ? { accion: 'espera', esEspera: true, esModal: true, esBotonUnico: true,
            texto: `Tocá «${(botonUnico.innerText || '').trim().split('\n')[0]}».`,
            nota: explicarModal(bloqueoModal.titulo).nota }
        : { accion: 'espera', esEspera: true, esModal: true, ...explicarModal(bloqueoModal.titulo) })
    : atender === 'carga'
      ? { accion: 'espera', esEspera: true, texto: 'Debés esperar a que esto termine.',
          nota: carga.texto || undefined }
      : (salto || (pasoGuion && pasoGuion.accion === 'modalPaso'
          ? { accion: 'espera', esEspera: true, esModal: true, texto: pasoGuion.texto, nota: pasoGuion.nota }
          : (pasoGuion && pasoGuion.ventana
             && !(modalAb && normalizar(modalAb.titulo || '').includes(normalizar(pasoGuion.ventana))))
            // el paso vive en una ventana que AHORA no está: decirlo (y dejar pasar con Siguiente)
            ? { ...pasoGuion, esVentanaFalta: true,
                texto: `Este paso va en la ventana «${pasoGuion.ventana}», que se abre sola en este punto.`,
                nota: 'Cuando aparezca, seguimos ahí. Si a vos no te salió, tocá «Siguiente →» para pasarlo.' }
            : pasoGuion));
  const bloqueado = carga || bloqueoModal;
  const [rectAncla, elRef] = useAncla(bloqueado ? null : paso?.ancla, !fin);
  const rect = React.useMemo(
    () => (atender === 'modal'
      ? (botonUnico
          ? (() => { const r = botonUnico.getBoundingClientRect();
                     return { x: r.left, y: r.top, w: r.width, h: r.height }; })()
          : { x: bloqueoModal.x, y: bloqueoModal.y, w: bloqueoModal.w, h: bloqueoModal.h })
      : atender === 'carga' ? { x: carga.x, y: carga.y, w: carga.w, h: carga.h }
      : modalDelPaso ? { x: modalDelPaso.x, y: modalDelPaso.y, w: modalDelPaso.w, h: modalDelPaso.h }
      : rectAncla),
    [atender, botonUnico, bloqueoModal?.x, bloqueoModal?.y, bloqueoModal?.w, bloqueoModal?.h, carga?.x, carga?.y, carga?.w, carga?.h, modalDelPaso, rectAncla]);
  // ESTADO REAL: se guarda en un ref (cambia en cada render de App) + la FOTO del arranque del paso.
  const estadoRef = useRef(estado);
  estadoRef.current = estado;
  const e0Ref = useRef(estado);
  // Un paso avanza UNA sola vez. Sin esto, un mismo clic podía disparar dos avances (el listener se
  // re-registraba al re-medir el elemento) y el tutorial saltaba del paso 1 al 3.
  const desde = useRef(-1);
  const idxRef = useRef(desdePaso);  // el paso ACTUAL, para que una acción vieja no empuje de más
  const interaccion = useRef(false); // ¿el usuario llegó a hacer algo? (para el mensaje final)
  const tempRef = useRef(null);      // avance en camino tras un clic (sobrevive al re-montaje, ver abajo)
  const avanzar = useCallback((n = 1) => {
    setIdx(i => {
      if (desde.current >= i) return i;          // ya se avanzó desde este paso
      desde.current = i;
      if (i + n >= guia.pasos.length) { setTimeout(() => setFin({ saltada: !interaccion.current }), 0); return i; }
      return i + n;
    });
  }, [guia.pasos.length]);
  const retroceder = useCallback(() => { desde.current = -1; setIdx(i => Math.max(0, i - 1)); }, []);
  // SALTEAR A MANO (pedido del usuario): pasar el paso sin hacer lo que pide. Directo, sin el
  // bucle por diseño — si lo saltea es porque no lo quiere hacer ahora.
  const salteados = useRef(0);       // cuántos pasos se pasaron sin hacer (para el cartel final)
  // la acción de «Siguiente» SIEMPRE al día, para que la tecla no dispare una versión vieja
  const irAlSiguienteRef = useRef(() => {});
  const noAplicaron = useRef(0);     // cuántos no estaban en la pantalla de quien lo sigue
  const saltear = useCallback(() => {
    setIdx(i => {
      desde.current = i;
      salteados.current += 1;
      if (i + 1 >= guia.pasos.length) { setTimeout(() => setFin({ saltada: !interaccion.current }), 0); return i; }
      return i + 1;
    });
  }, [guia.pasos.length]);
  // Al cambiar de paso se descarta cualquier avance que hubiera quedado en camino del paso anterior.
  useEffect(() => { idxRef.current = idx; clearTimeout(tempRef.current); tempRef.current = null; setAvanzando(false); }, [idx]);
  // La FOTO del estado se saca al empezar cada paso: así un guion puede pedir «que AUMENTE» y no
  // «que sea mayor a cero» (si no, un molde con 3 piezas ya nombradas cumpliría el paso de entrada).
  // La foto se toma al entrar al paso y TAMBIÉN al responder «cuántas»: si no, se contarían
  // las que la persona ya tenía antes de que el tutorial le preguntara.
  useEffect(() => { e0Ref.current = estadoRef.current; }, [idx, !!salto, cuantas[idx] != null]);   // eslint-disable-line react-hooks/exhaustive-deps
  // Recordar dónde quedó, para poder retomar si sale y vuelve.
  useEffect(() => {
    if (fin) return;
    try { localStorage.setItem(LS_PROGRESO, JSON.stringify({ guiaId: guia.id, idx })); } catch { /* no-op */ }
  }, [guia.id, idx, fin]);
  useEffect(() => {
    if (!fin) return;
    try { localStorage.removeItem(LS_PROGRESO); } catch { /* no-op */ }
  }, [fin]);

  // PASOS INFORMATIVOS: avanzan SOLOS (el usuario no tiene que apretar nada). El tiempo sale del
  // largo del texto —lo que tarda en leerse— con un piso de ~2,6 s. `progreso` alimenta la barrita.
  const [progreso, setProgreso] = useState(0);
  // RED DE SEGURIDAD 1: si lo que hay que marcar no aparece en unos segundos (la pantalla necesita
  // algo previo, como tener un molde abierto), se ofrece seguir igual en vez de quedar esperando.
  const [trabado, setTrabado] = useState(false);
  // RED DE SEGURIDAD 2: un paso que espera el ESTADO y no se cumple nunca (lo hizo por otro camino,
  // o el dato no se refrescó) tampoco puede dejar preso al usuario.
  const [escape, setEscape] = useState(false);

  // ── AVANCE POR ESTADO REAL (el mecanismo principal) ──────────────────────────────────────────
  // Si el paso declara `hecho`, ESTO es lo único que lo avanza. Se revisa con un latido corto
  // porque el estado llega por fetch (no hay un evento del DOM que avise «el POST salió bien»).
  const esperaEstado = !soloVer && !salto && !enViaje && !carga && !bloqueoModal && !preguntando && typeof pasoGuion?.hecho === 'function';

  // 🔴 EL TUTORIAL NUNCA DICE «NO ENCUENTRO ESE LUGAR» (pedido del usuario 2026-09-01: «este tipo
  // de cartel no quiero más; si me está guiando y el tutorial está grabado en el sistema, debe
  // saber todo cómo va a salir»). Si el control del paso no está en pantalla, el motor RESUELVE:
  //   · si el paso vive en una VENTANA que todavía no se abrió → lo dice y espera (más arriba);
  //   · si pide otra PANTALLA → arma el puente y lleva (más arriba);
  //   · y si no hay nada que hacer, **pasa al siguiente solo**, sin cartel de error y sin pedirle
  //     nada a la persona. Al final se dice cuántos pasos no aplicaron.
  // Un paso DUDOSO (ancla que no es el nombre de nada, de un tutorial viejo) se resuelve más rápido.
  useEffect(() => {
    setTrabado(false);
    if (rect || fin || salto) return undefined;
    // con una ventana de trabajo a la vista no se cuenta el tiempo: la pantalla está por cambiar
    if (carga || bloqueoModal) return undefined;
    // el paso ESPERA algo (una ventana, o que el estado se cumpla): no se pasa de largo
    if (pasoGuion?.ventana || pasoGuion?.accion === 'modalPaso' || esperaEstado) return undefined;
    const ms = pasoGuion?.dudoso ? 1200 : 5000;
    const s = setTimeout(() => {
      if (idxRef.current !== idx) return;
      noAplicaron.current += 1;
      desde.current = -1;
      avanzar();
    }, ms);
    return () => clearTimeout(s);
  }, [idx, !!rect, !!salto, !!fin, !!carga, !!bloqueoModal, esperaEstado]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    setEscape(false);
    if (fin || !esperaEstado) return;
    // ¿Ya estaba hecho al entrar al paso? → no se pide lo que ya está hecho.
    if (seCumplio(pasoGuion, estadoRef.current, e0Ref.current)) { avanzar(); return; }
    const t = setInterval(() => {
      if (seCumplio(pasoGuion, estadoRef.current, e0Ref.current)) {
        clearInterval(t);
        if (idxRef.current === idx) { interaccion.current = true; avanzar(); }
      }
    }, LATIDO);
    const esc = setTimeout(() => setEscape(true), ESPERA_ESCAPE);
    return () => { clearInterval(t); clearTimeout(esc); };
  }, [idx, !!salto, esperaEstado, !!fin]);   // eslint-disable-line react-hooks/exhaustive-deps

  // ── «ELEGÍ N DE ESTA LISTA»: SE MIRA LO ELEGIDO, NO LOS TOQUES ───────────────────────────────
  // Mismo latido que el avance por estado: se cuenta cuántas opciones hay PUESTAS en la lista y se
  // avanza al llegar a N (el TOTAL, no «N más»: lo que ya estaba elegido también vale). Si al
  // entrar ya hay N o más, el paso se saltea — no se le pide a nadie que vuelva a elegir lo que ya
  // tiene, que era justamente lo que terminaba DESMARCÁNDOLO.
  useEffect(() => {
    if (fin || salto || enViaje || carga || bloqueoModal || preguntando) return undefined;
    const n = pasoGuion && (pasoGuion.cuantas || 1);
    if (!n || n <= 1) return undefined;
    const mirar = () => {
      const m = elegidasDelPaso(pasoGuion);
      if (m == null) return;                       // esta lista no se puede medir: manda el clic
      setElegidas((c) => (c[idx] === m ? c : { ...c, [idx]: m }));
      if (m >= n && idxRef.current === idx) { interaccion.current = true; avanzar(); }
    };
    mirar();
    const t = setInterval(mirar, LATIDO);
    return () => clearInterval(t);
  }, [idx, !!salto, enViaje, !!carga, !!bloqueoModal, !!preguntando, !!fin, pasoGuion]);   // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    setProgreso(0);
    if (fin || salto || !paso || preguntando) return;
    // 'gesto' NUNCA avanza por tiempo: el trabajo del visor se verifica o no se avanza. (Si un
    // guion se olvidó de ponerle `hecho`, cae al tiempo para no dejar el tutorial colgado.)
    // MIRAR: todos los pasos avanzan solos, como un recorrido explicativo
    const porTiempo = soloVer || paso.accion === 'ver' || (paso.accion === 'gesto' && !esperaEstado);
    if (!porTiempo || esperaEstado) return;
    const largo = (paso.texto || '').length + (paso.nota || '').length
      + (preguntando ? 90 : 0) + (cuantas[idx] != null ? 40 : 0);
    const ms = Math.min(9000, Math.max(2600, largo * 45));
    const t0 = Date.now();
    const tick = setInterval(() => {
      const p = Math.min(1, (Date.now() - t0) / ms);
      setProgreso(p);
      if (p >= 1) { clearInterval(tick); avanzar(); }
    }, 100);
    return () => clearInterval(tick);
  }, [idx, !!salto, esperaEstado, !!fin]);   // eslint-disable-line react-hooks/exhaustive-deps
  const saltoRef = useRef(false);
  useEffect(() => { saltoRef.current = !!salto; }, [salto]);

  // YA ESTÁS AHÍ: si el paso era sólo para llevarte a una pantalla y estás parado en ella, se da por
  // cumplido solo. (Antes el tutorial abría en Pedidos y el primer paso te pedía tocar «Pedidos».)
  useEffect(() => { if (!fin && !salto && !carga && !bloqueoModal && esPasoNav(pasoGuion, donde)) avanzar(); }, [idx, !!salto, !!fin, !!carga, !!bloqueoModal]);   // eslint-disable-line react-hooks/exhaustive-deps

  // «ESPERAR AVISO»: el paso se cumple cuando su modal APARECIÓ y después SE CERRÓ. Si al entrar
  // al paso el aviso ya no existe (a esta persona no le salió), el escape de los 15 s ofrece
  // seguir igual — no se puede adivinar un aviso que nunca vino.
  const vioModalRef = useRef(false);
  useEffect(() => { vioModalRef.current = false; }, [idx]);
  useEffect(() => {
    if (fin || pasoGuion?.accion !== 'modalPaso') return;
    if (modalDelPaso) { vioModalRef.current = true; return; }
    if (vioModalRef.current && !modalAb && !carga) { interaccion.current = true; avanzar(); }
  }, [idx, modalDelPaso, modalAb, !!carga, !!fin]);   // eslint-disable-line react-hooks/exhaustive-deps

  // ARRANCAR DESDE DONDE ESTÁ: el paso de una etapa anterior ya cumplida se saltea al entrar.
  // Varios seguidos encadenan solos (cada avance vuelve a evaluar el siguiente).
  useEffect(() => { if (!fin && !carga && !bloqueoModal && omitir) avanzar(); }, [idx, omitir, !!fin, !!carga, !!bloqueoModal]);   // eslint-disable-line react-hooks/exhaustive-deps

  // Si el paso pide una pantalla y NO hay camino marcado (no está en RUTAS), se navega solo para no
  // dejar al usuario colgado. Cuando sí hay camino, lo hace él tocando los botones (`salto`).
  useEffect(() => { if (!fin && pasoGuion?.ir && !salto && !avanzando && !carga && !bloqueoModal && !omitir) ir(pasoGuion.ir); }, [idx, !!salto, !!fin, !!carga, !!bloqueoModal, omitir, avanzando]);   // eslint-disable-line react-hooks/exhaustive-deps

  // FOCO: si el paso pide escribir y el foco quedó en la nada (el body), se lo damos al campo que
  // estamos marcando. Sin foco la persona igual «escribe» —el navegador manda las teclas al último
  // campo— pero el ENTER no llega al campo y no confirma nada. Nunca se le saca el foco a otro
  // campo: sólo se toma cuando no lo tiene nadie.
  useEffect(() => {
    if (fin || !paso || paso.accion !== 'input' || !rect) return;
    const el = elRef.current;
    if (!el) return;
    const campo = el.matches('input, textarea, select') ? el : el.querySelector('input, textarea, select');
    const act = document.activeElement;
    if (campo && (!act || act === document.body)) { try { campo.focus({ preventScroll: true }); } catch { /* no-op */ } }
  }, [idx, !!rect, !!fin]);   // eslint-disable-line react-hooks/exhaustive-deps

  // Traer el elemento a la vista.
  useEffect(() => {
    const el = elRef.current;
    if (!fin && el && rect && (rect.y < 0 || rect.y + rect.h > window.innerHeight)) {
      try { el.scrollIntoView({ block: 'center', behavior: 'smooth' }); } catch { /* no-op */ }
    }
  }, [rect?.y, idx, !!fin]);   // eslint-disable-line react-hooks/exhaustive-deps

  // AVANCE POR ACCIÓN EN EL DOM. Se escucha en el DOCUMENTO (fase de captura) y se pregunta si lo
  // que se tocó cae dentro del ancla: si el listener fuera al elemento y éste todavía no existe,
  // no se engancharía nunca.
  //
  // 🔴 TOCAR EL CONTROL MARCADO CUMPLE EL PASO, TENGA O NO REGLA `listo`. Antes, con `hecho`
  // definido «mandaba el estado» y el clic ni se escuchaba: el paso de «Asignar telas» —cuya
  // regla es *no falta ninguna tela*, que recién se cumple mucho después— dejaba al tutorial
  // pegado al botón mientras el panel de telas se abría atrás, sin explicar nada (reporte del
  // usuario 2026-08-31). El estado sigue sirviendo para SALTEAR lo ya hecho y para avanzar sin
  // clic cuando se cumple por otro lado; lo que ya no hace es clavar un paso que la persona hizo.
  useEffect(() => {
    if (fin || carga || bloqueoModal) return;
    if (!paso || paso.esDesvio || paso.esEspera) return; // ni el desvío ni la espera avanzan el paso
    // 🔴 LA PLANILLA SE TERMINA A MANO: tocar una celda NO cumple el paso de su columna (hay que
    // poder escribir y elegir en el desplegable sin que el tutorial se vaya a la columna
    // siguiente). Se avanza con «Siguiente →» — o solo, si el paso tiene una regla que se cumpla.
    if (paso.manual) return;
    if (paso.accion !== 'click' && paso.accion !== 'input') return;
    // El paso puede aceptar más de un lugar: `tambien` lista las otras anclas que valen igual (el
    // campo que confirma con Enter vale lo mismo que el botón que hace esa confirmación).
    const anclas = [paso.ancla, ...(paso.tambien || [])];
    // 🔴 `esDelAncla` y no un selector de `data-tour`: la mayoría de los controles no tienen esa
    // marca (se identifican por su texto) y el clic no contaba nunca — el paso quedaba clavado.
    const dentro = (t) => anclas.some((a) => esDelAncla(t, a));
    // ⚠️ EL TEMPORIZADOR VA EN UN REF, NO EN UNA VARIABLE DEL EFECTO. El botón que se toca suele
    // CAMBIAR DE PANTALLA (ej. «Cargar el arte» pasa de Diseños a Arte); eso hace aparecer un puente
    // → cambia `paso.ancla` → el efecto se vuelve a montar y su cleanup **cancelaba el avance que
    // estaba en camino**. Resultado: el tutorial se quedaba clavado mostrando «volvé al paso
    // anterior». Con el ref el avance sobrevive al re-montaje; pisar de más no puede, porque
    // `avanzarDesde` sólo avanza si seguimos en el MISMO paso.
    const temp = tempRef;
    // Avanza sólo si seguimos parados en el mismo paso (una acción vieja no empuja de más).
    // `eraPuente` se mira EN EL MOMENTO del evento, no después: si el botón que se tocó cambia de
    // pantalla, un instante más tarde el paso viejo «pide» la pantalla anterior y se encendería un
    // puente que bloqueaba el avance para siempre (el tutorial quedaba trabado al tocar, por
    // ejemplo, «Cargar el arte»).
    const avanzarDesde = (i, eraPuente) => { setAvanzando(false); if (idxRef.current === i && !eraPuente) { interaccion.current = true; avanzar(); } };
    // ── UN MOVIMIENTO SE CUMPLE MOVIENDO ────────────────────────────────────────────────────
    // El cursor guía lo muestra; el paso se da por hecho cuando la persona arrastra de verdad
    // dentro del mismo lugar (no alcanza con un clic: sería no haber hecho el gesto).
    if (paso.accion === 'arrastre') {
      let ini = null;
      const dn = (e) => { ini = (e.button === 0 && dentro(e.target)) ? { x: e.clientX, y: e.clientY } : null; };
      const up = (e) => {
        const d = ini; ini = null;
        if (!d || !esArrastre(d.x, d.y, e.clientX, e.clientY)) return;
        interaccion.current = true;
        clearTimeout(temp.current);
        temp.current = setTimeout(() => avanzarDesde(idx, saltoRef.current), 250);
      };
      document.addEventListener('mousedown', dn, true);
      document.addEventListener('mouseup', up, true);
      return () => {
        document.removeEventListener('mousedown', dn, true);
        document.removeEventListener('mouseup', up, true);
      };
    }
    if (paso.accion === 'click') {
      const h = (e) => {
        if (!dentro(e.target)) return;
        // 🔴 TOCAR UN CAMPO NO ES HABERLO COMPLETADO. Un campo se llena, y eso lo termina la
        // persona con «Siguiente →» (pedido del usuario 2026-09-01: «cuando son campos de escribir
        // no saltará automático»). El avance solo queda para botones y ventanas emergentes.
        if (esCampo(e.target)) return;
        const eraPuente = saltoRef.current;
        // ¿el paso pide VARIAS opciones de una lista? Se cuentan; recién con todas, avanza.
        if ((paso.cuantas || 1) > 1) {
          // 🔴 SI LA LISTA SE PUEDE MEDIR, EL CLIC NO CUENTA: manda lo que quedó ELEGIDO (lo
          // resuelve el latido de abajo). Sólo se cuentan clics cuando la lista no declara sus
          // opciones elegidas — y ahí, únicamente los que caen sobre una opción de verdad, no en
          // el aire del contenedor.
          if (elegidasDelPaso(paso) != null) return;
          if (!e.target.closest || !e.target.closest('button, [role="button"], a[href], input, select, label')) return;
          setElegidas((c) => {
            const n = (c[idx] || 0) + 1;
            if (n >= paso.cuantas) {
              clearTimeout(temp.current);
              temp.current = setTimeout(() => avanzarDesde(idx, eraPuente), 250);
            }
            return { ...c, [idx]: n };
          });
          return;
        }
        clearTimeout(temp.current);
        setAvanzando(true);          // el paso ya se hizo: nada de puentes ni navegación hasta que avance
        temp.current = setTimeout(() => avanzarDesde(idx, eraPuente), 200);
      };
      document.addEventListener('click', h, true);
      // Si el paso acepta que la acción se haga desde un campo (`tambien`) y ese campo se VACÍA, es
      // que ya se confirmó (con Enter o con el botón): el clic no hace falta y el paso está cumplido.
      const vig = (paso.tambien || []).length
        ? vigilarVaciado(paso.tambien, () => { clearTimeout(temp.current); avanzarDesde(idx, saltoRef.current); })
        : null;
      return () => { if (vig) clearInterval(vig); document.removeEventListener('click', h, true); };
    }
    // ESCRIBIR: se espera a que TERMINE de escribir (cada tecla reinicia la cuenta). Antes cada
    // tecla programaba su propio avance y una palabra de 10 letras saltaba 10 pasos de una.
    const h = (e) => {
      if (!dentro(e.target) || !(e.target.value || '').trim()) return;   // basta UNA letra: un talle es «M»
      const eraPuente = saltoRef.current;
      clearTimeout(temp.current);
      temp.current = setTimeout(() => avanzarDesde(idx, eraPuente), 650);   // dejó de escribir
    };
    document.addEventListener('input', h, true);
    // Y si confirma (Enter o botón) antes de esa pausa, el campo se vacía: también está hecho.
    const vig = vigilarVaciado(anclas, () => { clearTimeout(temp.current); avanzarDesde(idx, saltoRef.current); });
    // ⚠️ EL ENTER YA NO LLEGA ACÁ. Mientras el tutorial está abierto, la tecla es del TUTORIAL y
    // sólo acciona su «Siguiente →» (regla del usuario 2026-09-01; ver el listener de `keydown` más
    // abajo). Lo que sigue valiendo es el resto: si la persona confirma con el BOTÓN, el campo se
    // vacía —de tener texto a quedar en blanco— y ese vaciado es la señal de que la acción se hizo.
    // Salir del campo también es «ya terminé de escribir».
    const hb = (e) => { if (dentro(e.target) && (e.target.value || '').trim()) { clearTimeout(temp.current); avanzarDesde(idx, saltoRef.current); } };
    document.addEventListener('blur', hb, true);
    return () => { clearInterval(vig); document.removeEventListener('input', h, true); document.removeEventListener('blur', hb, true); };
  }, [idx, paso?.ancla, paso?.accion, avanzar, esperaEstado, !!fin, !!carga, !!bloqueoModal]);   // eslint-disable-line react-hooks/exhaustive-deps

  // Salir con Escape.
  useEffect(() => {
    const k = (e) => { if (e.key === 'Escape') onCerrar(); };
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [onCerrar]);

  // ── EL ENTER, MIENTRAS EL TUTORIAL ESTÁ ABIERTO, ES DEL TUTORIAL ────────────────────────────
  // 🔴 Regla del usuario (2026-09-01): «el enter cuando está activa la ayuda es exclusivamente
  // para el botón siguiente del tutorial y más nada». Va en CAPTURA y con `preventDefault` +
  // `stopPropagation`: si no, la app lo recibe igual y confirma un campo, manda un formulario o
  // dispara el botón que tenga el foco — que es justo lo que no se quiere.
  // Excepción: el campo del PROPIO globo (la pregunta «¿cuántas?»), que también es del tutorial.
  useEffect(() => {
    if (fin) return undefined;
    const k = (e) => {
      if (e.key !== 'Enter' || e.isComposing) return;
      try { if (e.target && e.target.closest && e.target.closest('[data-tutor-globo]')) return; }
      catch { /* nodo raro: se sigue con la regla general */ }
      e.preventDefault();
      e.stopPropagation();
      if (typeof e.stopImmediatePropagation === 'function') e.stopImmediatePropagation();
      irAlSiguienteRef.current();
    };
    window.addEventListener('keydown', k, true);
    return () => window.removeEventListener('keydown', k, true);
  }, [!!fin]);

  // 🔴 EL ENTER ES DEL TUTORIAL (regla del usuario 2026-09-01: «el enter cuando está activa la
  // ayuda es exclusivamente para el botón Siguiente del tutorial y nada más»). Antes era del CAMPO
  // —confirmaba lo que se estaba escribiendo, como sin tutorial—; ahora, con la ayuda abierta, la
  // tecla es del tutorial y no llega a la app. Botón y tecla hacen EXACTAMENTE lo mismo: una sola
  // función, para que no puedan discrepar.
  const hayQueSeguir = !preguntando && !(paso && paso.esEspera);
  const irAlSiguiente = () => {
    if (!hayQueSeguir) return;
    // en un puente que el sistema PUEDE resolver, lleva; en el resto, saltea el paso
    if (salto && !(paso && paso.elige) && pasoGuion?.ir) ir(pasoGuion.ir);
    else saltear();
  };

  irAlSiguienteRef.current = irAlSiguiente;

  if (fin) return createPortal(<GloboFin guia={guia} saltada={fin.saltada} salteados={salteados.current}
    noAplicaron={noAplicaron.current} onVerIgual={soloVer ? null : onVerIgual} onCerrar={onCerrar} />, document.body);
  if (!paso) return null;
  // ── LO QUE SE MUESTRA, YA MIRANDO LA PANTALLA ────────────────────────────────────────────────
  // Va acá (en el render) y no en un estado: se lee el DOM de AHORA sin forzar re-dibujos extra.
  //  · una COLUMNA se explica por su ROL, porque su id lo pone cada taller (el «Diseño» del
  //    usuario es `dise_o`) y con el id suelto el cartel salía «Tocá "▾"»;
  //  · si el paso terminó marcando una LISTA de opciones (ver `generalizar` en localizar.js), el
  //    cartel tiene que ser el de la lista y no el de la tarjeta que se grabó.
  const mostrar = (() => {
    if (!paso.ancla || paso._aMano || paso.esEspera) return paso;
    const a = String(paso.ancla);
    if (a.startsWith('col:')) {
      const id = a.slice(4);
      let d = null;
      try { d = explicarColumna(id, roleDeColumna(id), etiquetaColumna(id)); } catch { /* no-op */ }
      return d ? { ...paso, texto: d.como, nota: d.que || paso.nota } : paso;
    }
    let ef = a;
    try { ef = anclaEfectiva(a); } catch { /* no-op */ }
    if (ef === a) return paso;
    const d = explicar(ef, '');
    return (d && d.como) ? { ...paso, texto: d.como, nota: d.que || undefined } : paso;
  })();
  // ── EL GESTO QUE HAY QUE MOSTRAR ────────────────────────────────────────────────────────────
  // 🔴 SIEMPRE EL MISMO Y EN EL MISMO LUGAR (`gestoGenerico`), no el recorrido que hizo quien
  // grabó: esa persona tenía otro molde y otras piezas, así que calcar su arrastre no enseña nada
  // (decisión del usuario, 2026-09-01). Lo que se muestra es EL GESTO: apretar, arrastrar, soltar.
  const gesto = (!bloqueado && !salto && mostrar.accion === 'arrastre')
    ? gestoGenerico(elRef.current)
    : null;
  // ¿EL CONTROL DE ESTE PASO ESTÁ APAGADO? Entonces no se pide tocarlo: se dice qué falta para que
  // se prenda (y se ilumina también el aviso de la pantalla que lo explica).
  const apagado = (!bloqueado && !mostrar.esEspera && rect && estaApagado(elRef.current))
    ? (motivoApagado(elRef.current) || { texto: '' }) : null;
  // ¿Y ES UN CAMPO? Entonces el paso lo termina la persona: se lo avisa en el globo. (El guion ya
  // marca `manual` los pasos de escribir; esto agarra además los que se grabaron como un CLIC
  // sobre el campo, que son la mayoría.)
  const mostrarCampo = (!mostrar.manual && !mostrar.esEspera && !salto && esCampo(elRef.current))
    ? { ...mostrar, manual: true, manualPor: 'campo' } : mostrar;
  // 🔴 Y SI EL SISTEMA YA SABE QUE ESTE PASO NO SE PUEDE MOSTRAR, NO MUESTRA BASURA. Un paso viejo
  // guardado con un símbolo por nombre («👁», «?») no tiene cartel que valga: en vez de decir
  // «Tocá "👁"» y quedarse, se avisa que no aplica y se sigue (pedido del usuario 2026-09-01).
  const mostrarFinal = (mostrarCampo.dudoso && !rect && !salto)
    ? { ...mostrarCampo, texto: 'Este paso no está en tu pantalla, así que lo salteo.',
        nota: 'Puede que tu molde o tu pedido sean distintos de los que se grabaron.' }
    : mostrarCampo;
  // El hueco: el control… y, si está apagado, TAMBIÉN el aviso que dice qué falta — si no, el velo
  // tapa justo lo único que explica por qué no se puede seguir. Sólo si están cerca (misma barra):
  // unir dos cosas lejanas dejaría media pantalla sin velo y el resalte no señalaría nada.
  const rectAviso = (apagado && apagado.el && apagado.el.getBoundingClientRect)
    ? (() => { const q = apagado.el.getBoundingClientRect();
               return (q.width || q.height) ? { x: q.left, y: q.top, w: q.width, h: q.height } : null; })()
    : null;
  const base = (rect && rectAviso && Math.abs((rectAviso.y + rectAviso.h / 2) - (rect.y + rect.h / 2)) < 160)
    ? { x: Math.min(rect.x, rectAviso.x), y: Math.min(rect.y, rectAviso.y),
        w: Math.max(rect.x + rect.w, rectAviso.x + rectAviso.w) - Math.min(rect.x, rectAviso.x),
        h: Math.max(rect.y + rect.h, rectAviso.y + rectAviso.h) - Math.min(rect.y, rectAviso.y) }
    : rect;
  const r = base ? { x: base.x - MARGEN, y: base.y - MARGEN, w: base.w + MARGEN * 2, h: base.h + MARGEN * 2 } : null;
  return createPortal(
    <>
      {/* RECORTE: el `box-shadow` gigante oscurece TODO menos este rectángulo. `pointerEvents:none`
          es clave: deja que el usuario toque de verdad el elemento iluminado. */}
      {r ? (
        <>
          {/* EL HUECO TIENE QUE DEJAR VER EL BOTÓN — ES TODO EL PUNTO.
              El `box-shadow` de 9999px oscurece TODO menos este rectángulo, que queda transparente.
              ⚠️ NO PONER SOMBRAS `inset` ACÁ: se dibujan DENTRO del hueco, o sea ENCIMA del botón,
              y lo dejan tapado con un velo celeste — que es exactamente lo contrario de resaltarlo.
              El resalte va SIEMPRE por afuera: el aro + el resplandor. */}
          <div style={{ position: 'fixed', left: r.x, top: r.y, width: r.w, height: r.h, borderRadius: 12, zIndex: 100000,
            boxShadow: '0 0 0 9999px rgba(2,5,9,0.88), 0 0 0 3px var(--accent), 0 0 34px 6px rgba(0,216,245,0.6)',
            pointerEvents: 'none', transition: 'all .18s ease' }} />
          {/* Halo que late, para que salte a la vista dónde hay que tocar (también por afuera). */}
          <div className="tour-pulso" style={{ position: 'fixed', left: r.x - 6, top: r.y - 6, width: r.w + 12, height: r.h + 12,
            borderRadius: 16, border: '2px solid var(--accent)', zIndex: 100001, pointerEvents: 'none' }} />
        </>
      ) : (
        /* Todavía no se encontró el elemento: se oscurece MENOS. Tapar la pantalla entera mientras
           se busca deja a la persona sin ver nada justo cuando algo no está saliendo bien. */
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(2,5,9,0.55)', zIndex: 100000, pointerEvents: 'none' }} />
      )}
      {/* 🔴 EL CURSOR DEL SISTEMA: muestra el movimiento en bucle hasta que la persona lo hace.
          No toca nada — es un dibujo (ver cursor.jsx). */}
      {gesto && <CursorGuia desde={gesto.desde} hasta={gesto.hasta} />}
      <Globo rect={base} paso={mostrarFinal} apagado={apagado} idx={idx} total={guia.pasos.length} esperando={!rect} puente={!!salto}
        onAtras={retroceder} onCerrar={onCerrar} progreso={progreso} trabado={trabado} escape={escape && !trabado}
        pregunta={bloqueado ? null : preguntando}
        onResponder={(n) => setCuantas((c) => ({ ...c, [idx]: n }))}
        onSaltear={saltear}
        onSiguiente={irAlSiguiente}
        llevan={(paso?.cuantas || 1) > 1
          ? { hechas: elegidas[idx] || 0, total: paso.cuantas, unidad: '' }
          : cuantas[idx] != null && crudo?.cuantos
          ? { hechas: Math.max(0, (() => { try { return Number(crudo.cuantos.mide(estado)) || 0; } catch { return 0; } })()),
              total: cuantas[idx], unidad: crudo.cuantos.unidad || '' }
          : null}
        onSeguirIgual={() => { if (salto && pasoGuion?.ir) ir(pasoGuion.ir); else { desde.current = -1; avanzar(); } }} />
    </>,
    document.body
  );
}


/**
 * MENÚ DE TUTORIALES. Ya no hay guiones escritos a mano: lo que se lista es lo que el usuario
 * GRABÓ (decisión del usuario, 2026-08-27). Arriba, el botón de grabar; abajo, los grabados.
 */

/**
 * DE LA GRABACIÓN AL GUION. El grabador guarda lo mínimo que se puede volver a mostrar —qué
 * elemento se tocó y en qué pantalla— y ACÁ se arma el paso con las palabras del diccionario.
 * Se hace en la reproducción, no al grabar, para que al mejorar una explicación mejoren TODOS
 * los tutoriales ya grabados, sin regrabar nada.
 */

/**
 * MODO DISEÑO DE PASOS — editor visual de la grabación, estilo editor de video (v3).
 *
 * UNA sola línea de tiempo. Adentro:
 *   · los PASOS como chips (arrastrar = cambiar de lugar, en vivo; tocar = ir a su pantalla,
 *     resaltar su control y abrir su detalle);
 *   · los MODALES y ventanas emergentes como VENTANITAS ámbar en su lugar exacto.
 * «⏺ Agregar pasos» suma pasos tocando la app de verdad. El sistema se escala para que la barra
 * no tape nada. Nada se guarda hasta «Guardar».
 *
 * 🔴 NO HAY NADA DE «VARIOS DISEÑOS» (decisión del usuario, 2026-08-28): ni marcas de repetición,
 * ni vista de 2 diseños, ni condiciones por cantidad. Un tutorial es la lista de pasos que se
 * grabó; para dos diseños, se graba con dos diseños.
 */
function EditorTutorial({ t, ir, donde, onCerrar, onGuardar, onProbar }) {
  const [nombre, setNombre] = useState(t.nombre || '');
  const [pasos, setPasos] = useState(() => {
    // Los tutoriales viejos pueden traer marcas de repetición y campos del ciclo: se DESCARTAN
    // acá (la lógica ya no existe) para que al guardar queden limpios.
    return (t.pasos || [])
      .filter((p) => (p.accion || '') !== 'vuelta')
      .map(({ mid, repite, vuelta2, solo, ...p }) => ({ ...p }));
  });
  const [sel, setSel] = useState(null);
  const [huecoVentana, setHuecoVentana] = useState(null);  // en qué hueco de la línea se inserta una ventana
  const [capturando, setCapturando] = useState(false);
  const arrastro = useRef(null);                 // { tipo: 'paso', i }
  const omitirClick = useRef(false);             // el clic que cierra un arrastre no es un paso
  const [guardando, setGuardando] = useState(false);
  const [marca, setMarca] = useState(null);
  const dondeRef = useRef(donde);
  useEffect(() => { dondeRef.current = donde; }, [donde]);
  const selRef = useRef(sel);
  useEffect(() => { selRef.current = sel; }, [sel]);

  // ── resaltar en pantalla el control del paso elegido ──────────────────────────────────────
  useEffect(() => {
    const p = sel != null ? pasos[sel] : null;
    if (!p || !p.ancla) { setMarca(null); return undefined; }
    const mirar = () => {
      // MISMO resolutor que el tutorial: si acá se midiera el elemento a secas, un paso de
      // columna marcaría sólo su título y el editor mostraría algo distinto de lo que se ve al
      // reproducir (ya pasó).
      const r = rectDeAncla(p.ancla, buscar(p.ancla));
      if (!r) { setMarca((m) => (m === null ? m : null)); return; }
      setMarca((m) => (m && Math.abs(m.x - r.x) < 0.5 && Math.abs(m.y - r.y) < 0.5
        && Math.abs(m.w - r.w) < 0.5 && Math.abs(m.h - r.h) < 0.5) ? m : r);
    };
    mirar();
    const t2 = setInterval(mirar, 250);
    return () => clearInterval(t2);
  }, [sel, pasos]);

  // ── «⏺ AGREGAR PASOS»: se toca la app de verdad y cada control se suma como paso ──────────
  // Escucha en el DOCUMENTO y en fase de CAPTURA: así el paso se anota aunque el control haga
  // otra cosa con el clic (cambiar de pantalla, abrir un modal). Lo del propio editor y lo que
  // esté marcado `data-no-grabar` no cuenta: son controles de la ayuda, no del trabajo.
  useEffect(() => {
    if (!capturando) return undefined;
    const alTocar = (e) => {
      const el = e.target;
      if (!el || !el.closest) return;
      if (omitirClick.current) { omitirClick.current = false; return; }   // venía de un arrastre
      if (!sePuedeGrabar(el)) return;   // mismo criterio que el grabador (barra lateral, ayuda)
      const ancla = identificar(el);
      if (!ancla) return;                       // sin nombre no se puede volver a encontrar
      const enV = el.closest('[data-modal]');
      const nuevo = { ancla, accion: 'click', etiqueta: etiquetaDe(el).slice(0, 120),
                      donde: { ...(dondeRef.current || {}) },
                      ...(enV ? { ventana: (enV.getAttribute('data-modal') || '').slice(0, 80) } : {}) };
      setPasos((ps) => {
        const m = ps.slice();
        const at = selRef.current == null ? m.length : selRef.current + 1;
        m.splice(at, 0, nuevo);
        return m;
      });
      // el paso nuevo queda elegido, así el siguiente se agrega DESPUÉS de éste
      setSel((k) => (k == null ? null : k + 1));
    };
    // …y los MOVIMIENTOS (arrastres), igual que el grabador: mismo criterio, mismos datos.
    let ini = null;
    const alBajar2 = (e) => { ini = (e.button === 0) ? { x: e.clientX, y: e.clientY, el: e.target } : null; };
    const alSoltar = (e) => {
      const d = ini; ini = null;
      if (!d || !esArrastre(d.x, d.y, e.clientX, e.clientY)) return;
      if (!sePuedeGrabar(d.el)) return;
      const ancla = identificar(d.el);
      if (!ancla) return;
      omitirClick.current = true;
      // del gesto sólo se guarda QUE FUE un arrastre: el recorrido que se muestra es el genérico
      const nuevo = { ancla, accion: 'arrastre',
                      etiqueta: etiquetaDe(d.el).slice(0, 120), donde: { ...(dondeRef.current || {}) } };
      setPasos((ps) => { const m = ps.slice();
        const at = selRef.current == null ? m.length : selRef.current + 1;
        m.splice(at, 0, nuevo); return m; });
      setSel((k) => (k == null ? null : k + 1));
    };
    document.addEventListener('click', alTocar, true);
    document.addEventListener('mousedown', alBajar2, true);
    document.addEventListener('mouseup', alSoltar, true);
    return () => {
      document.removeEventListener('click', alTocar, true);
      document.removeEventListener('mousedown', alBajar2, true);
      document.removeEventListener('mouseup', alSoltar, true);
    };
  }, [capturando]);

  const elegir = (i) => {
    if (sel === i) { setSel(null); return; }
    setSel(i);
    // tocar un paso lleva a SU pantalla: el editor muestra dónde ocurre, no sólo su nombre
    const p = pasos[i];
    if (p && p.donde && Object.keys(p.donde).length && ir) { try { ir(p.donde); } catch { /* no-op */ } }
  };
  const cambiar = (i, campo, val) => setPasos((ps) => ps.map((p, k) => (k === i ? { ...p, [campo]: val } : p)));
  const borrar = (i) => { setSel(null); setPasos((ps) => ps.filter((_, k) => k !== i)); };
  const insertarAviso = (i) => setPasos((ps) => {
    const m = ps.slice(); m.splice(i + 1, 0, { accion: 'modal', modal: '', donde: ps[i]?.donde || {} }); return m;
  });
  // ¿Es una ventana de TRABAJO (el sistema procesando) o un aviso que se responde? Se dibujan
  // distinto y se explican distinto: la de trabajo no se toca, se espera.
  // insertar en el HUECO `h` (0 = antes del primer paso) la ventana ya elegida del catálogo
  const ponerVentana = (h, titulo) => {
    setPasos((ps) => { const m = ps.slice();
      m.splice(h, 0, { accion: 'modal', modal: titulo, donde: (ps[h - 1] || ps[h] || {}).donde || {} });
      return m; });
    setHuecoVentana(null);
    setSel(h);
  };

  // ── ARRASTRE POR MOUSE: un PASO se reordena; la MARCA «↻ diseño 2» elige desde dónde se
  // repite el bloque para CADA diseño que siga (2, 10 o 100: la regla es la misma).
  // 🔴 Mouse y no `draggable` nativo: el drag de HTML5 SE CORTA cuando el elemento arrastrado se
  // re-dibuja, y acá la línea se reacomoda EN VIVO — el gesto moría al primer movimiento (reporte
  // del usuario). Las filas de la planilla usan mouse por esta misma razón.
  const alBajar = (e, tipo, dato) => {
    if (e.button !== 0) return;
    e.preventDefault();
    const d = { tipo, ...dato, x0: e.clientX, y0: e.clientY, movio: false };
    arrastro.current = d;
    const onMove = (ev) => {
      if (arrastro.current !== d) return;
      if (!d.movio && Math.abs(ev.clientX - d.x0) + Math.abs(ev.clientY - d.y0) < 3) return;
      d.movio = true;
      const el = (document.elementsFromPoint(ev.clientX, ev.clientY) || [])
        .find((x) => x.hasAttribute && x.hasAttribute('data-chip-idx'));
      if (!el) return;
      const j = Number(el.getAttribute('data-chip-idx'));
      if (Number.isNaN(j)) return;
      if (d.tipo === 'paso') {
        if (d.i === j) return;
        setPasos((ps) => { const m = ps.slice(); const [x] = m.splice(d.i, 1); m.splice(j, 0, x); return m; });
        setSel((s2) => (s2 === d.i ? j : s2));
        d.i = j;
        return;
      }
      // (las marcas «↻» ya viajan como pasos: este camino quedó sin uso y se conserva por si
      // un tutorial viejo trae la marca embebida)
      return;
    };
    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      const fue = arrastro.current;
      arrastro.current = null;
      // clic corto sobre un paso (sin arrastre) = elegirlo
      if (fue === d && d.tipo === 'paso' && !d.movio) elegir(d.i);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  };

  const COLOR_ETAPA = { diseno: '#22d3ee', moldes: '#a78bfa', arte: '#fb923c',
                        planilla: '#34d399', resultados: '#f472b6' };
  const nombreDe = (p) => {
    if ((p.accion || '') === 'modal') return p.modal || 'Ventana del sistema';
    const d = explicar(p.ancla, p.etiqueta);
    const nom = d.nombre || p.etiqueta || p.ancla;
    // un MOVIMIENTO se lee distinto de un clic: en la línea de tiempo tiene que notarse
    return (p.accion || '') === 'arrastre' ? `✋ Arrastrar en ${nom}` : nom;
  };
  const AMBAR = 'var(--warning, #e0a020)';
  const inputCss = { padding: '6px 9px', borderRadius: 7, fontSize: 12, border: '1px solid var(--border-light)',
    background: 'rgba(255,255,255,0.05)', color: '#fff' };
  // LAS COLUMNAS DE LA PLANILLA son configurables por molde: si hay una planilla a la vista se
  // leen de ahí (con el nombre que les puso su dueño); si no, las que el sistema sabe explicar.
  const columnasPlanilla = React.useMemo(() => {
    const enPantalla = [...document.querySelectorAll('th[data-col]')]
      .map((e) => ({ id: e.getAttribute('data-col'), nombre: e.getAttribute('data-col-label') || e.getAttribute('data-col') }))
      .filter((c) => c.id);
    if (enPantalla.length) return enPantalla;
    return COLUMNAS_CONOCIDAS;
  }, [donde]);
  const pSel = sel != null ? pasos[sel] : null;
  const altoBarra = 168;

  // 🔴 EL SISTEMA SE ESCALA, NO SE TAPA: #root se achica proporcionalmente para que la línea de
  // tiempo quede DEBAJO de la app (los portales viven en <body> y no se escalan; el resaltado se
  // mide sobre lo ya dibujado, así que sus coordenadas siguen coincidiendo).
  useEffect(() => {
    const raiz = document.getElementById('root');
    if (!raiz) return undefined;
    const aplicar = () => {
      const esc = Math.max(0.5, (window.innerHeight - altoBarra) / window.innerHeight);
      raiz.style.transform = `scale(${esc})`;
      raiz.style.transformOrigin = 'top center';
      raiz.style.transition = 'transform .25s ease';
    };
    aplicar();
    window.addEventListener('resize', aplicar);
    return () => {
      window.removeEventListener('resize', aplicar);
      raiz.style.transform = ''; raiz.style.transformOrigin = ''; raiz.style.transition = '';
    };
  }, [altoBarra]);

  // DIBUJO DE UNA VENTANA — el mismo para el chip de la línea y para el catálogo, así lo que
  // elegís es igual a lo que queda puesto. `grande` = la vista previa del catálogo (se ve lo que
  // la ventana tiene adentro y sus botones); chica = el chip de la línea, que sólo tiene 40 px.
  const ventanita = (titulo, activa, grande) => {
    const f = fichaVentana(titulo);
    const trabaja = f.trabajo;
    return (
      <div style={{ borderRadius: 8, overflow: 'hidden', boxSizing: 'border-box',
        height: grande ? 'auto' : 40,
        border: `1.5px solid ${activa ? AMBAR : 'rgba(224,160,32,0.5)'}`,
        boxShadow: activa ? `0 0 12px ${AMBAR}55` : 'none', background: 'rgba(224,160,32,0.08)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 3, height: grande ? 15 : 12,
          padding: '0 6px', background: 'rgba(224,160,32,0.22)' }}>
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: AMBAR }} />
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: `${AMBAR}88` }} />
          {!trabaja && <span style={{ marginLeft: 'auto', fontSize: 8, color: AMBAR, fontWeight: 800 }}>✕</span>}
        </div>
        <div style={{ padding: grande ? '6px 9px 0' : (trabaja ? '2px 8px 0' : '3px 8px'),
          fontSize: grande ? 11.5 : 10.5, fontWeight: 800, color: '#fff', lineHeight: 1.25,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: grande ? 'normal' : 'nowrap' }}>
          {f.nombre || 'Elegí qué ventana…'}
        </div>
        {grande && !!f.contenido && (
          // lo que se ve ADENTRO, con dos renglones grises que hacen de cuerpo de la ventana
          <div style={{ padding: '4px 9px 0' }}>
            <div style={{ fontSize: 10, color: 'var(--text-secondary)', lineHeight: 1.3 }}>{f.contenido}</div>
            <div style={{ marginTop: 4, height: 3, borderRadius: 999, width: '88%', background: 'rgba(255,255,255,0.09)' }} />
            <div style={{ marginTop: 3, height: 3, borderRadius: 999, width: '64%', background: 'rgba(255,255,255,0.07)' }} />
          </div>
        )}
        {trabaja ? (
          <div style={{ margin: grande ? '7px 9px 9px' : '3px 8px 0', height: 4, borderRadius: 999,
            overflow: 'hidden', background: 'rgba(255,255,255,0.10)' }}>
            <div style={{ width: '62%', height: '100%', borderRadius: 999, background: 'var(--accent, #22b8cf)' }} />
          </div>
        ) : grande && (
          // LOS BOTONES REALES de esa ventana: es lo que más la hace reconocible
          <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end', flexWrap: 'wrap',
            padding: '7px 9px 8px' }}>
            {(f.botones.length ? f.botones : ['Cerrar']).map((b, k) => (
              <span key={b + k} style={{ fontSize: 9, fontWeight: 700, padding: '2.5px 7px', borderRadius: 5,
                border: `1px solid ${k === f.botones.length - 1 ? 'rgba(224,160,32,0.6)' : 'rgba(255,255,255,0.16)'}`,
                background: k === f.botones.length - 1 ? 'rgba(224,160,32,0.2)' : 'transparent',
                color: k === f.botones.length - 1 ? '#ffd98a' : 'var(--text-secondary)' }}>{b}</span>
            ))}
          </div>
        )}
      </div>
    );
  };

  // ── un CHIP de paso; los modales van como VENTANITA ámbar ─────────────────────────────────
  const chip = (p, i) => {
    const esVentana = (p.accion || '') === 'modal';
    const col = esVentana ? AMBAR : (COLOR_ETAPA[(p.donde || {}).paso] || '#9ca3af');
    // PINTADO: el paso pertenece al conjunto de alguna marca «↻» (lavado violeta suave); si la
    // marca elegida es la suya, fuerte — así se ve qué repite cada marca.
    return (
      <div key={'p' + i} data-chip-idx={i}
        onMouseDown={(e) => alBajar(e, 'paso', { i })}
        title={nombreDe(p)}
        style={{ display: 'flex', flexDirection: 'column', gap: 0, width: 158, flexShrink: 0,
          cursor: 'grab', userSelect: 'none', borderRadius: 10 }}>
        {p.ventana && !esVentana ? (
          // EL PASO VIVE EN UNA VENTANA: se dibuja la ventana, con el botón adentro
          <div style={{ borderRadius: 8, overflow: 'hidden', height: 40, boxSizing: 'border-box',
            border: `1.5px solid ${sel === i ? AMBAR : 'rgba(224,160,32,0.45)'}`,
            boxShadow: sel === i ? `0 0 12px ${AMBAR}55` : 'none', background: 'rgba(224,160,32,0.06)',
            }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, height: 13,
              padding: '0 6px', background: 'rgba(224,160,32,0.2)' }}>
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: AMBAR, flexShrink: 0 }} />
              <span style={{ fontSize: 7.5, color: AMBAR, fontWeight: 800, overflow: 'hidden',
                textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.ventana}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '3px 8px' }}>
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: col, flexShrink: 0 }} />
              <span style={{ fontSize: 10.5, fontWeight: 700, color: '#fff', overflow: 'hidden',
                textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{nombreDe(p)}</span>
            </div>
          </div>
        ) : esVentana ? (
          // LA VENTANITA: se ve como lo que es — una ventana emergente del sistema en su lugar.
          // La de TRABAJO lleva su barra de progreso y no lleva ✕ (no se cierra a mano).
          ventanita(p.modal, sel === i)
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, height: 40, padding: '0 10px',
            borderRadius: 9, fontSize: 11.5, fontWeight: 700, boxSizing: 'border-box',
            border: `1.5px solid ${sel === i ? col : 'rgba(255,255,255,0.13)'}`,
            background: sel === i ? `${col}2b` : 'rgba(255,255,255,0.05)',
            color: sel === i ? '#fff' : 'var(--text-secondary)',
            boxShadow: sel === i ? `0 0 12px ${col}44` : 'none', transition: 'border .15s, background .15s' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: col, flexShrink: 0 }} />
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{nombreDe(p)}</span>
          </div>
        )}
        <div style={{ fontSize: 9.5, fontWeight: 800, color: 'var(--text-muted)', textAlign: 'center', height: 14 }}>{i + 1}</div>
      </div>
    );
  };

  // EL HUECO entre dos pasos: un «+» finito para meter ahí una ventana del sistema.
  const hueco = (h) => (
    <button key={'h' + h} type="button" onClick={() => setHuecoVentana(huecoVentana === h ? null : h)}
      title="Poner acá una ventana del sistema (aparece en este punto del tutorial)"
      style={{ flexShrink: 0, width: 16, height: 40, marginTop: 0, padding: 0, cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: 6,
        border: huecoVentana === h ? `1.5px dashed ${AMBAR}` : '1.5px dashed transparent',
        background: huecoVentana === h ? 'rgba(224,160,32,0.12)' : 'transparent',
        color: huecoVentana === h ? AMBAR : 'var(--text-muted)', fontSize: 13, fontWeight: 800,
        opacity: huecoVentana === h ? 1 : 0.45, transition: 'opacity .15s' }}
      onMouseEnter={(e) => { e.currentTarget.style.opacity = 1; }}
      onMouseLeave={(e) => { if (huecoVentana !== h) e.currentTarget.style.opacity = 0.45; }}>+</button>
  );

  // 🔴 UN MOVIMIENTO SE REVISA VIÉNDOLO. Al elegir un paso de arrastre en la línea de tiempo, el
  // editor muestra el MISMO cursor que va a ver quien siga el tutorial: así se comprueba que el
  // gesto quedó bien grabado sin tener que reproducir todo el tutorial.
  const gestoSel = (() => {
    if (!pSel || (pSel.accion || '') !== 'arrastre') return null;
    return gestoGenerico(buscar(pSel.ancla));
  })();

  return createPortal(
    <div data-diseno-pasos="1">
      {gestoSel && <CursorGuia desde={gestoSel.desde} hasta={gestoSel.hasta} />}
      {marca && (
        <div style={{ position: 'fixed', left: marca.x - 5, top: marca.y - 5, width: marca.w + 10,
          height: marca.h + 10, border: '2px solid var(--accent)', borderRadius: 10,
          boxShadow: '0 0 0 3px rgba(0,216,245,0.25), 0 0 18px rgba(0,216,245,0.35)',
          pointerEvents: 'none', zIndex: 100001, transition: 'all .15s' }} />
      )}

      {pSel && (
        <div style={{ position: 'fixed', left: '50%', transform: 'translateX(-50%)', bottom: altoBarra + 10,
          zIndex: 100003, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
          maxWidth: 'min(900px, 94vw)', padding: '10px 14px', borderRadius: 12,
          background: '#14181d', border: '1px solid var(--border-light)',
          boxShadow: '0 14px 40px rgba(0,0,0,0.6)' }}>
          <span style={{ fontSize: 12.5, fontWeight: 800, flexShrink: 0 }}>{sel + 1} · {nombreDe(pSel)}</span>
          {(pSel.accion || '') === 'modal' ? (
            <>
              <select value={[...AVISOS_CONOCIDOS.modales, ...AVISOS_CONOCIDOS.cargas].includes(pSel.modal) ? pSel.modal : '__otro'}
                onChange={(e) => cambiar(sel, 'modal', e.target.value === '__otro' ? '' : e.target.value)}
                style={{ ...inputCss, cursor: 'pointer', maxWidth: 280 }}>
                <optgroup label="Ventanas del sistema">
                  {AVISOS_CONOCIDOS.modales.map((m) => <option key={m} value={m}>{m}</option>)}
                </optgroup>
                <optgroup label="Cargas (esperar a que terminen)">
                  {AVISOS_CONOCIDOS.cargas.map((m) => <option key={m} value={m}>{m}</option>)}
                </optgroup>
                <option value="__otro">Otra (escribirla)…</option>
              </select>
              {![...AVISOS_CONOCIDOS.modales, ...AVISOS_CONOCIDOS.cargas].includes(pSel.modal) && (
                <input value={pSel.modal || ''} onChange={(e) => cambiar(sel, 'modal', e.target.value)}
                  placeholder="Título de la ventana a esperar"
                  style={{ ...inputCss, flex: 1, minWidth: 160 }} />
              )}
            </>
          ) : (
            <>
            <input value={pSel.texto || ''} onChange={(e) => cambiar(sel, 'texto', e.target.value || undefined)}
              placeholder={explicar(pSel.ancla, pSel.etiqueta).como}
              title="El cartel de este paso. Vacío = el que escribe el sistema."
              style={{ ...inputCss, flex: 1, minWidth: 200 }} />
            {/* ¿ES UN PASO DE LA PLANILLA? Entonces elige SU COLUMNA. Los grabados desde ahora
                la traen solas; a los viejos —que apuntaban a la tabla entera— se les pone acá. */}
            {(pSel.ancla === 'planilla-tabla' || (pSel.ancla || '').startsWith('col:')) && (
              <select value={(pSel.ancla || '').startsWith('col:') ? pSel.ancla.slice(4) : ''}
                onChange={(e) => cambiar(sel, 'ancla', e.target.value ? 'col:' + e.target.value : 'planilla-tabla')}
                title="Qué columna de la planilla marca este paso (si no, se ilumina la tabla entera)"
                style={{ ...inputCss, cursor: 'pointer', maxWidth: 200 }}>
                <option value="">Toda la planilla</option>
                {columnasPlanilla.map((c) => <option key={c.id} value={c.id}>Columna: {c.nombre}</option>)}
              </select>
            )}
            {/* ¿Este paso vive dentro de una ventana emergente? (los grabados desde ahora lo
                traen solos; a los viejos se les asigna acá) */}
            <select value={AVISOS_CONOCIDOS.modales.includes(pSel.ventana) ? pSel.ventana : (pSel.ventana ? '__otra' : '')}
              onChange={(e) => cambiar(sel, 'ventana', e.target.value === '' ? undefined : e.target.value === '__otra' ? pSel.ventana : e.target.value)}
              title="Si este paso se hace dentro de una ventana emergente, decí cuál: se muestra y se explica"
              style={{ ...inputCss, cursor: 'pointer', maxWidth: 210 }}>
              <option value="">Sin ventana</option>
              {AVISOS_CONOCIDOS.modales.map((m) => <option key={m} value={m}>en: {m}</option>)}
              {pSel.ventana && !AVISOS_CONOCIDOS.modales.includes(pSel.ventana) && (
                <option value="__otra">en: {pSel.ventana}</option>
              )}
            </select>
            </>
          )}
          <button className="btn ghost" title="Insertar después una ventana del sistema a esperar"
            style={{ padding: '5px 10px', fontSize: 11.5 }} onClick={() => insertarAviso(sel)}>+ ventana</button>
          <button className="btn ghost" title="Borrar este paso"
            style={{ padding: '5px 10px', fontSize: 11.5, color: 'var(--error, #e0503a)' }}
            onClick={() => borrar(sel)}>Borrar</button>
        </div>
      )}

      <div style={{ position: 'fixed', left: 0, right: 0, bottom: 0, zIndex: 100002,
        background: 'rgba(9,12,16,0.97)', borderTop: '1px solid var(--border-light)',
        backdropFilter: 'blur(8px)', padding: '10px 16px 12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
          <span style={{ fontSize: 11, fontWeight: 800, letterSpacing: '.06em', textTransform: 'uppercase',
            color: 'var(--accent)', flexShrink: 0 }}>Diseño de pasos</span>
          <input value={nombre} onChange={(e) => setNombre(e.target.value)}
            style={{ ...inputCss, width: 220, fontWeight: 700 }} />
          <button type="button" onClick={() => setCapturando((c) => !c)}
            title="Con esto prendido, cada control que toques en la pantalla se agrega como paso (después del elegido)"
            style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '6px 12px', borderRadius: 9,
              fontSize: 12, fontWeight: 700, cursor: 'pointer',
              border: `1px solid ${capturando ? 'var(--error, #e0503a)' : 'var(--border-light)'}`,
              background: capturando ? 'rgba(224,80,58,0.14)' : 'transparent',
              color: capturando ? 'var(--error, #e0503a)' : 'var(--text-secondary)' }}>
            <span className={capturando ? 'grabando-punto' : ''} style={{ width: 9, height: 9,
              borderRadius: '50%', background: capturando ? 'var(--error, #e0503a)' : 'var(--text-muted)' }} />
            {capturando ? 'Grabando… tocá la app' : '⏺ Agregar pasos'}
          </button>
          {/* PROBARLO: el editor mostraba los pasos GRABADOS, pero lo que la gente ve es el GUION
              (el sistema completa etapas y junta repetidos). Sin poder correrlo, se editaba a
              ciegas y recién se veía el resultado después de guardar. */}
          <button type="button" onClick={() => onProbar && onProbar({ ...t, nombre: nombre.trim() || t.nombre, pasos })}
            title="Cerrar el editor y correr el tutorial tal como está (no se guarda nada)"
            style={{ padding: '6px 12px', borderRadius: 9, fontSize: 12, fontWeight: 700, cursor: 'pointer',
              border: '1px solid var(--accent)', background: 'rgba(0,216,245,0.12)', color: 'var(--accent)' }}>
            ▶ Probar
          </button>
          <span style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
            arrastrá los pasos para acomodarlos · tocá uno para ir a su pantalla y editarlo
            {(() => {
              // cuántos pasos AGREGA el sistema (etapas que la grabación no tiene) y cuántos junta
              let g = null;
              try { g = aGuion({ ...t, pasos }); } catch { /* no-op */ }
              if (!g) return null;
              const d = g.pasos.length - pasos.length;
              if (!d) return null;
              return d > 0
                ? ` · el sistema agrega ${d} paso(s) que faltaban: se ven ${g.pasos.length}`
                : ` · el sistema junta ${-d} paso(s) repetidos: se ven ${g.pasos.length}`;
            })()}
          </span>
          <span style={{ marginLeft: 'auto', display: 'flex', gap: 8, flexShrink: 0 }}>
            <button className="btn ghost" style={{ padding: '6px 12px', fontSize: 12.5 }} onClick={onCerrar}>Cancelar</button>
            <button className="btn primary" disabled={guardando || !nombre.trim()} style={{ padding: '6px 14px', fontSize: 12.5 }}
              onClick={async () => { setGuardando(true); try { await onGuardar({ ...t, nombre: nombre.trim(), pasos }); } finally { setGuardando(false); } }}>
              {guardando ? 'Guardando…' : 'Guardar'}
            </button>
          </span>
        </div>

        {/* LA LÍNEA DE TIEMPO: los pasos y las ventanas emergentes, en su orden.
            Entre paso y paso hay un «+» que abre el catálogo de ventanas del sistema. */}
        <div style={{ display: 'flex', gap: 7, overflowX: 'auto', paddingBottom: 4, alignItems: 'flex-start' }}>
          {pasos.map((p, i) => [hueco(i), chip(p, i)])}
          {!!pasos.length && hueco(pasos.length)}
          {!pasos.length && (
            <span style={{ fontSize: 12, color: 'var(--text-muted)', alignSelf: 'center' }}>
              Sin pasos: prendé «⏺ Agregar pasos» y tocá la app para armarlos.
            </span>
          )}
        </div>

        {huecoVentana != null && (
          // EL CATÁLOGO: las ventanas que el sistema YA CONOCE, para poner en ese punto de la
          // línea. Se elige una y queda puesta ahí (indica que en ese momento va a aparecer).
          <div style={{ marginTop: 9, padding: '10px 12px', borderRadius: 11,
            border: `1px solid ${AMBAR}55`, background: 'rgba(224,160,32,0.06)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 800, color: AMBAR }}>
                ¿Qué ventana aparece {huecoVentana === 0 ? 'antes del paso 1' : `entre el paso ${huecoVentana} y el ${huecoVentana + 1}`}?
              </span>
              <span style={{ fontSize: 11.5, color: 'var(--text-secondary)' }}>
                El tutorial la va a mostrar y esperar ahí antes de seguir.
              </span>
              <button className="btn ghost" style={{ marginLeft: 'auto', padding: '2px 9px', fontSize: 11 }}
                onClick={() => setHuecoVentana(null)}>Cancelar</button>
            </div>
            {[['Mientras el sistema trabaja (esperar)', AVISOS_CONOCIDOS.cargas],
              ['Avisos que se responden', AVISOS_CONOCIDOS.modales]].map(([tit, lista]) => (
              <div key={tit} style={{ marginBottom: 7 }}>
                <div style={{ fontSize: 9.5, fontWeight: 800, letterSpacing: '.05em', textTransform: 'uppercase',
                  color: 'var(--text-muted)', marginBottom: 5 }}>{tit}</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {(lista || []).map((m) => {
                    const f = fichaVentana(m);
                    const cEt = COLOR_ETAPA[f.paso] || 'var(--text-muted)';
                    return (
                      <div key={m} onClick={() => ponerVentana(huecoVentana, m)}
                        title={f.que || `Poner «${m}» en este punto`}
                        style={{ width: 208, cursor: 'pointer' }}>
                        {ventanita(m, false, true)}
                        {!!f.cuando && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 4, paddingLeft: 2 }}>
                            <span style={{ width: 6, height: 6, borderRadius: '50%', background: cEt, flexShrink: 0 }} />
                            <span style={{ fontSize: 9.5, color: 'var(--text-muted)', overflow: 'hidden',
                              textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Aparece {f.cuando}</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}

      </div>
    </div>, document.body);
}

function Menu({ onElegir, onCerrar, tutoriales, grabando, onGrabar, onParar, onBorrar, onEditar, retomar, onRetomar, onOlvidar, puedeGrabar = true }) {
  const [borrando, setBorrando] = useState(null);   // id que pide confirmación
  const card = {
    display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', borderRadius: 12,
    cursor: 'pointer', textAlign: 'left', border: '1px solid var(--border-light)',
    background: 'rgba(255,255,255,0.03)', color: '#fff', width: '100%',
  };
  const rotulo = { fontSize: 11, fontWeight: 800, letterSpacing: 0.6, textTransform: 'uppercase',
    color: 'var(--text-muted)', margin: '0 0 8px' };

  return createPortal(
    <div onMouseDown={(e) => { if (e.target === e.currentTarget) onCerrar(); }}
      style={{ position: 'fixed', inset: 0, zIndex: 100001, background: 'rgba(0,0,0,0.62)', backdropFilter: 'blur(5px)',
        display: 'flex', alignItems: 'flex-start', justifyContent: 'center', padding: '8vh 20px 24px', overflowY: 'auto' }}>
      <div style={{ width: 560, maxWidth: '100%', background: '#0f1216', border: '1px solid var(--border-light)', borderRadius: 16, padding: 22 }}>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <h3 style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>Tutoriales</h3>
          <button className="btn ghost" style={{ marginLeft: 'auto', padding: '6px 12px', fontSize: 13 }}
            onClick={onCerrar}>Cerrar</button>
        </div>

        {/* GRABAR: el tutorial lo hace el usuario haciendo el trabajo, no escribiéndolo.
            Sólo para quien tiene `ayuda.grabar` (el admin): seguir los tutoriales lo puede hacer
            cualquiera, grabarlos no. */}
        {puedeGrabar && (
        <button type="button" onClick={grabando ? onParar : onGrabar}
          style={{ ...card, marginBottom: 16, borderColor: grabando ? 'var(--error, #e0503a)' : 'var(--accent)',
            background: grabando ? 'rgba(224,80,58,0.12)' : 'rgba(0,216,245,0.10)' }}>
          <span style={{ width: 13, height: 13, borderRadius: grabando ? 3 : '50%', flexShrink: 0,
            background: grabando ? 'var(--error, #e0503a)' : 'var(--accent)' }} />
          <span style={{ flex: 1 }}>
            <span style={{ display: 'block', fontWeight: 700, fontSize: 14.5 }}>
              {grabando ? 'Parar y guardar el tutorial' : 'Grabar un tutorial'}
            </span>
            <span style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
              {grabando ? 'Se está anotando cada paso que hacés.'
                        : 'Hacé el trabajo una vez y el sistema anota los pasos. No graba video.'}
            </span>
          </span>
        </button>
        )}

        {retomar && (
          <div style={{ marginBottom: 16 }}>
            <p style={rotulo}>Quedó a medias</p>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" style={{ ...card, flex: 1 }} onClick={onRetomar}>
                <span style={{ flex: 1 }}>Seguir «{retomar.guia.titulo}» desde el paso {retomar.idx + 1}</span>
              </button>
              <button className="btn ghost" style={{ padding: '6px 12px', fontSize: 12 }} onClick={onOlvidar}>Empezar de cero</button>
            </div>
          </div>
        )}

        <p style={rotulo}>{tutoriales.length ? 'Grabados' : ''}</p>
        {!tutoriales.length && (
          <div style={{ fontSize: 13.5, color: 'var(--text-muted)', lineHeight: 1.55,
            padding: '16px 16px', borderRadius: 12, border: '1px dashed var(--border-light)' }}>
            {puedeGrabar
              ? <>Todavía no hay ningún tutorial. Tocá <b>«Grabar un tutorial»</b>, hacé el trabajo como
                  lo hacés siempre y, al terminar, ponele un nombre. El sistema escribe solo las
                  explicaciones de cada paso.</>
              : <>Todavía no hay ningún tutorial. Los graba el administrador del sistema: pedile que
                  grabe el trabajo que necesitás aprender y va a aparecer acá.</>}
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {tutoriales.map((t) => (
            <div key={t.id} style={{ display: 'flex', gap: 8, alignItems: 'stretch' }}>
              <button type="button" style={{ ...card, flex: 1 }} onClick={() => onElegir(t.id)}>
                <span style={{ flex: 1 }}>
                  <span style={{ display: 'block', fontWeight: 700, fontSize: 14.5 }}>{t.nombre}</span>
                  {/* Los pasos que se van a VER, no los que se grabaron: el sistema completa las
                      etapas que faltan y junta las repetidas, así que el número era otro (decía
                      «22 pasos» y el tutorial mostraba 23). */}
                  <span style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                    {(() => {
                      let n = (t.pasos || []).length;
                      try { n = (aGuion(t) || {}).pasos.length; } catch { /* el grabado, como antes */ }
                      return `${n} paso${n === 1 ? '' : 's'}`;
                    })()}
                    {t.desc ? ' · ' + t.desc : ''}
                  </span>
                </span>
              </button>
              {puedeGrabar && (<>
              <button className="btn ghost" title="Ver y modificar los pasos grabados"
                style={{ padding: '0 12px', fontSize: 12, color: 'var(--text-muted)' }}
                onClick={() => onEditar(t)}>Editar</button>
              <button className="btn ghost" title="Borrar este tutorial"
                style={{ padding: '0 12px', fontSize: 12, color: borrando === t.id ? 'var(--error, #e0503a)' : 'var(--text-muted)' }}
                onClick={() => { if (borrando === t.id) { onBorrar(t.id); setBorrando(null); } else setBorrando(t.id); }}>
                {borrando === t.id ? '¿Seguro?' : 'Borrar'}
              </button>
              </>)}
            </div>
          ))}
        </div>
      </div>
    </div>, document.body);
}

/**
 * Punto de entrada. Se monta UNA vez en la app.
 *   abierto / setAbierto  el menú de tutoriales
 *   ir(destino)           lleva a la pantalla que pide el paso ({tab, sub, paso, molde, ajuste})
 *   donde                 en qué pantalla está parado el usuario
 *   estado                el ESTADO REAL del sistema (`ayudaEstado` en App.jsx)
 *   tutoriales            los grabados por el usuario (los trae App.jsx de /api/tutoriales)
 *   grabando · onGrabar · onParar · onBorrar   el grabador, que vive en App.jsx
 */
export function Ayuda({ abierto, setAbierto, ir, donde, estado, tutoriales = [],
                        grabando = false, onGrabar, onParar, onBorrar, onGuardarEdicion,
                        puedeGrabar = true }) {
  const [guiaId, setGuiaId] = useState(null);
  const [editando, setEditando] = useState(null);   // el tutorial abierto en el EDITOR
  const [desdePaso, setDesdePaso] = useState(0);
  const [soloVer, setSoloVer] = useState(false);    // «verlo igual»: mirarlo entero, sin hacer nada
  const [prueba, setPrueba] = useState(null);       // tutorial del editor corriendo SIN guardar
  const porId = (id) => aGuion((tutoriales || []).find((t) => t.id === id));
  const guia = prueba ? aGuion(prueba) : porId(guiaId);
  // Lo que quedó a medias en una sesión anterior (o al cerrar con la ✕).
  const [retomar, setRetomar] = useState(null);
  useEffect(() => {
    if (!abierto) return;
    try {
      const g = JSON.parse(localStorage.getItem(LS_PROGRESO) || 'null');
      const gu = g && porId(g.guiaId);
      setRetomar(gu && g.idx > 0 ? { guia: gu, idx: Math.min(g.idx, gu.pasos.length - 1) } : null);
    } catch { setRetomar(null); }
  }, [abierto, tutoriales]);
  const olvidar = () => { try { localStorage.removeItem(LS_PROGRESO); } catch { /* no-op */ } setRetomar(null); };
  return (
    <>
      {editando && (
        <EditorTutorial t={editando} ir={ir} donde={donde} onCerrar={() => setEditando(null)}
          onProbar={(tt) => { setEditando(null); setSoloVer(false); setDesdePaso(0); setPrueba(tt); }}
          onGuardar={async (tt) => {
            const ok2 = onGuardarEdicion ? await onGuardarEdicion(tt) : false;
            if (ok2 !== false) setEditando(null);
          }} />
      )}
      {abierto && !guia && !editando && (
        <Menu tutoriales={tutoriales} retomar={retomar}
          grabando={grabando}
          puedeGrabar={puedeGrabar}
          onGrabar={() => { setAbierto(false); onGrabar && onGrabar(); }}
          onParar={() => { setAbierto(false); onParar && onParar(); }}
          onBorrar={(id) => onBorrar && onBorrar(id)}
          onEditar={(t) => setEditando(t)}
          onCerrar={() => setAbierto(false)}
          onElegir={(id) => { olvidar(); setDesdePaso(0); setSoloVer(false); setGuiaId(id); setAbierto(false); }}
          onRetomar={() => { setDesdePaso(retomar.idx); setSoloVer(false); setGuiaId(retomar.guia.id); setAbierto(false); }}
          onOlvidar={olvidar} />
      )}
      {/* `key`: al pedir «verlo igual» el tutorial se vuelve a montar desde cero, en modo mirar */}
      {guia && <Tour key={(prueba ? 'prueba:' : '') + (guiaId || '') + (soloVer ? ':ver' : '')}
        guia={guia} ir={ir} donde={donde} estado={estado}
        desdePaso={soloVer ? 0 : desdePaso} soloVer={soloVer}
        onVerIgual={() => setSoloVer(true)}
        onCerrar={() => { setSoloVer(false); setGuiaId(null);
          // al terminar la PRUEBA se vuelve al editor con lo que se estaba armando (nada se perdió)
          if (prueba) { const t2 = prueba; setPrueba(null); setEditando(t2); } }} />}
    </>
  );
}

export default Ayuda;
