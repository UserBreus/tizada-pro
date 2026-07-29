/**
 * MOTOR DE AYUDA GUIADA — el tutorial paso a paso, estilo tutorial de videojuego.
 *
 * Oscurece la pantalla, deja ILUMINADO el campo o botón exacto que hay que usar y muestra un
 * globo con la consigna. El paso avanza cuando el usuario HACE la acción de verdad (decisión del
 * usuario: se aprende haciendo), y siempre queda una salida por si algo se traba.
 *
 * Todo el contenido vive en `guias.js`: acá está sólo el mecanismo. Para que el motor pueda
 * iluminar un elemento, ese elemento tiene que estar marcado en el JSX con `data-tour="id"`.
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
import { guiaPorId, GUIA_PRINCIPAL, RECORRIDOS, AREAS, bloqueo } from './guias';
import { ubicarGlobo } from './tutor_pos';

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
  'molde:abierto':    { ancla: 'molde-tarjeta', texto: 'Abrí una moldería: tocá una de las tarjetas.', necesita: { tab: 'config', sub: 'productos' } },
  'ajuste:menu':      { ancla: 'ajuste-volver', texto: 'Volvé al menú de ajustes tocando acá.' },

  // ── EL PEDIDO ES UN WIZARD EN FILA: moldes → arte → planilla → resultados ────────────────────
  // ⚠️ EL CAMINO DEPENDE DE DÓNDE ESTÁS: para ADELANTE se usa el botón de avanzar de cada paso;
  // para ATRÁS, el botón de volver **de la pantalla en la que estás parado**, que NO es el mismo
  // en todas. Cuando esto no se contemplaba, desde la Planilla el tutorial marcaba «← Diseños»
  // (que sólo existe en el paso Arte), no encontraba nada, y a los 5 s el «seguir igual»
  // TELETRANSPORTABA al usuario fuera de su pedido. Por eso son funciones de `donde`.
  'paso:moldes': (d) => d.paso === 'arte'
    ? { ancla: 'pedido-volver-moldes', texto: 'Volvé a los diseños con «← Diseños».' }
    // desde planilla/resultados hay que retroceder de a un paso (cada pantalla tiene SU botón)
    : { ancla: 'pedido-volver-moldes', texto: 'Volvé a los diseños con «← Diseños».', necesita: { tab: 'pedidos', paso: 'arte' } },
  'paso:arte': (d) => d.paso === 'planilla'
    ? { ancla: 'planilla-volver-arte', texto: 'Volvé al arte con «← Arte».' }
    : d.paso === 'resultados'
      ? { ancla: 'planilla-volver-arte', texto: 'Volvé al arte con «← Arte».', necesita: { tab: 'pedidos', paso: 'planilla' } }
      : { ancla: 'pedido-ir-arte', texto: 'Pasá al arte con «Cargar el arte».', necesita: { tab: 'pedidos', paso: 'moldes' } },
  'paso:planilla': (d) => d.paso === 'resultados'
    ? { ancla: 'resultados-volver-planilla', texto: 'Volvé a la planilla con «← Atrás».' }
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
function puente(destino, donde) {
  if (!destino) return null;
  // El ORDEN importa: primero la sección, después la pantalla, después abrir la moldería y recién
  // ahí su ajuste. Al revés, se marcaría un botón que todavía no está en pantalla.
  const claves = ['tab', 'sub', 'paso', 'molde', 'ajuste'];
  for (const k of claves) {
    const q = destino[k];
    if (!q || donde[k] === q) continue;               // no pedido, o ya estamos
    const r = rutaDe(`${k}:${q}`, donde);
    if (!r) continue;                                  // sin ruta conocida: lo resuelve el propio guion
    const previo = r.necesita ? puente(r.necesita, donde) : null;   // ¿hace falta llegar a otro lado antes?
    return previo || { ancla: r.ancla, texto: r.texto, accion: 'click', esPuente: true };
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
  return Object.entries(p.ir).some(([k, v]) => (rutaDe(`${k}:${v}`, donde) || {}).ancla === p.ancla);
}

/** Texto que tiene ahora mismo el campo marcado con ese `data-tour` ('' si no hay campo). */
function valorDe(ancla) {
  const el = document.querySelector(`[data-tour="${ancla}"]`);
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

/** Evalúa `hecho` sin que un guion roto pueda tirar abajo la ayuda. */
function seCumplio(paso, E, E0) {
  if (!paso || typeof paso.hecho !== 'function' || !E || !E0) return false;
  try { return !!paso.hecho(E, E0); } catch { return false; }
}

/** Rectángulo del elemento marcado con `data-tour`, siguiéndolo si la página se mueve. */
function useAncla(ancla, activo) {
  const [rect, setRect] = useState(null);
  const elRef = useRef(null);
  useEffect(() => {
    if (!activo || !ancla) { setRect(null); elRef.current = null; return; }
    let vivo = true;
    const medir = () => {
      if (!vivo) return;
      const el = document.querySelector(`[data-tour="${ancla}"]`);
      elRef.current = el || null;
      if (!el) { setRect(null); return; }
      const r = el.getBoundingClientRect();
      // Elemento presente pero sin tamaño (oculto) → se trata como si no estuviera.
      const nuevo = (r.width || r.height) ? { x: r.left, y: r.top, w: r.width, h: r.height } : null;
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
function Globo({ rect, paso, idx, total, onAtras, onCerrar, esperando, puente, progreso, trabado, onSeguirIgual, escape }) {
  const ANCHO = 340;
  const esInfo = !puente && paso.accion === 'ver';
  const esGesto = !puente && paso.accion === 'gesto';
  const col = puente ? 'var(--warning, #e0a020)' : esInfo ? '#a78bfa' : 'var(--accent)';
  const fondo = puente ? 'linear-gradient(180deg,#231a0d,#171208)'
    : esInfo ? 'linear-gradient(180deg,#171526,#100f1b)' : 'linear-gradient(180deg,#0b1c22,#081418)';
  const rotulo = puente ? 'Te llevo hasta ahí' : esInfo ? 'Para que sepas' : esGesto ? 'Hacelo en el molde' : 'Hacé esto';
  const icono = puente ? '➜' : esInfo ? 'i' : esGesto ? '✋' : '☝';
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
  }, [paso.texto, paso.nota, trabado, escape, esInfo, puente, vw, vh]);
  // La cuenta vive en `tutor_pos.js` (función pura) para poder probarla sin navegador: el chequeo
  // del build verifica que el globo NUNCA se solape con el elemento resaltado.
  const { top, left, flecha, maxAlto } = ubicarGlobo(rect, tam, vw, vh, MARGEN + 14, 12);
  return (
    <div ref={cajaRef} style={{ position: 'fixed', top, left, width: ANCHO, zIndex: 100002, background: fondo,
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
        <span style={{ marginLeft: 'auto', fontSize: 10.5, color: 'var(--text-muted)' }}>{puente ? '' : `${idx + 1}/${total}`}</span>
        <button onClick={onCerrar} title="Salir de la ayuda"
          style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 15, lineHeight: 1 }}>✕</button>
      </div>
      <div style={{ fontSize: 14.5, color: '#fff', lineHeight: 1.45, fontWeight: 600 }}>{paso.texto}</div>
      {paso.nota && <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.4, marginTop: 7 }}>{paso.nota}</div>}
      {esperando && !trabado && <div style={{ fontSize: 11.5, color: 'var(--warning, #e0a020)', marginTop: 9 }}>Buscando ese lugar en pantalla…</div>}
      {trabado && (
        <div style={{ marginTop: 10, padding: '9px 11px', borderRadius: 9, background: 'rgba(224,160,32,0.12)', border: '1px solid rgba(224,160,32,0.35)' }}>
          <div style={{ fontSize: 11.5, color: 'var(--warning, #e0a020)', lineHeight: 1.4 }}>
            No encuentro ese lugar en pantalla. Puede que falte abrir algo antes.
          </div>
          <button className="btn ghost" style={{ marginTop: 7, padding: '5px 11px', fontSize: 11.5 }} onClick={onSeguirIgual}>Seguir igual →</button>
        </div>
      )}
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
          <span style={{ flex: 1, fontSize: 11.5, color: col, fontWeight: 700 }}>
            {esGesto ? 'Hacelo y sigo solo' : paso.accion === 'input' ? 'Escribilo y seguimos' : 'Tocá lo que está marcado'}
          </span>
        )}
      </div>
    </div>
  );
}

/** Globo final: la guía terminó. Antes se cerraba de golpe y no quedaba claro si había terminado. */
function GloboFin({ guia, onCerrar, saltada }) {
  useEffect(() => { const t = setTimeout(onCerrar, 5000); return () => clearTimeout(t); }, [onCerrar]);
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
          {guia.explica ? 'Eso es todo' : saltada ? 'Esto ya estaba hecho' : '¡Listo!'}
        </span>
        <button onClick={onCerrar} style={{ marginLeft: 'auto', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 15 }}>✕</button>
      </div>
      <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.45 }}>
        {guia.explica
          ? <>Eso es «{guia.titulo}». Podés volver a verlo cuando quieras desde Ayuda.</>
          : saltada
            ? <>«{guia.titulo}» ya estaba resuelto en este molde, así que no había nada que pedirte.</>
            : <>Terminaste «{guia.titulo}».</>}
      </div>
    </div>
  );
}

/** El tutorial en sí: recorte + globo + detección de la acción del usuario. */
function Tour({ guia, onCerrar, ir, donde, estado, desdePaso = 0 }) {
  const [idx, setIdx] = useState(desdePaso);
  const [fin, setFin] = useState(null);            // null | {saltada:bool}
  const pasoGuion = guia.pasos[idx];
  // AYUDA INTELIGENTE: si el usuario no está en la pantalla que el paso necesita, primero se le
  // marca el camino (un botón por vez) en vez de saltar solo. Cuando llega, sigue el guion.
  const salto = pasoGuion?.ir ? puente(pasoGuion.ir, donde || {}) : null;
  const paso = salto || pasoGuion;
  const [rect, elRef] = useAncla(paso?.ancla, !fin);
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
  // Al cambiar de paso se descarta cualquier avance que hubiera quedado en camino del paso anterior.
  useEffect(() => { idxRef.current = idx; clearTimeout(tempRef.current); tempRef.current = null; }, [idx]);
  // La FOTO del estado se saca al empezar cada paso: así un guion puede pedir «que AUMENTE» y no
  // «que sea mayor a cero» (si no, un molde con 3 piezas ya nombradas cumpliría el paso de entrada).
  useEffect(() => { e0Ref.current = estadoRef.current; }, [idx, !!salto]);
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
  useEffect(() => {
    setTrabado(false);
    if (rect || fin) return;
    const t = setTimeout(() => setTrabado(true), 5000);
    return () => clearTimeout(t);
  }, [idx, !!rect, !!salto, !!fin]);

  // ── AVANCE POR ESTADO REAL (el mecanismo principal) ──────────────────────────────────────────
  // Si el paso declara `hecho`, ESTO es lo único que lo avanza. Se revisa con un latido corto
  // porque el estado llega por fetch (no hay un evento del DOM que avise «el POST salió bien»).
  const esperaEstado = !salto && typeof pasoGuion?.hecho === 'function';
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

  useEffect(() => {
    setProgreso(0);
    if (fin || salto || !paso) return;
    // 'gesto' NUNCA avanza por tiempo: el trabajo del visor se verifica o no se avanza. (Si un
    // guion se olvidó de ponerle `hecho`, cae al tiempo para no dejar el tutorial colgado.)
    const porTiempo = paso.accion === 'ver' || (paso.accion === 'gesto' && !esperaEstado);
    if (!porTiempo || esperaEstado) return;
    const largo = (paso.texto || '').length + (paso.nota || '').length;
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
  useEffect(() => { if (!fin && !salto && esPasoNav(pasoGuion, donde)) avanzar(); }, [idx, !!salto, !!fin]);   // eslint-disable-line react-hooks/exhaustive-deps

  // Si el paso pide una pantalla y NO hay camino marcado (no está en RUTAS), se navega solo para no
  // dejar al usuario colgado. Cuando sí hay camino, lo hace él tocando los botones (`salto`).
  useEffect(() => { if (!fin && pasoGuion?.ir && !salto) ir(pasoGuion.ir); }, [idx, !!salto, !!fin]);   // eslint-disable-line react-hooks/exhaustive-deps

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

  // AVANCE POR ACCIÓN EN EL DOM. Es el camino de los pasos que NO declaran `hecho` (los que sólo
  // llevan de un lado a otro, o donde no hay un estado que mirar). Se escucha en el DOCUMENTO (fase
  // de captura) y se pregunta si lo que se tocó cae dentro del ancla: si el listener fuera al
  // elemento y éste todavía no existe, no se engancharía nunca.
  useEffect(() => {
    if (fin || esperaEstado) return;                    // con `hecho`, manda el estado
    if (!paso || (paso.accion !== 'click' && paso.accion !== 'input')) return;
    // El paso puede aceptar más de un lugar: `tambien` lista las otras anclas que valen igual (el
    // campo que confirma con Enter vale lo mismo que el botón que hace esa confirmación).
    const anclas = [paso.ancla, ...(paso.tambien || [])];
    const dentro = (t) => t && t.closest && anclas.some(a => t.closest(`[data-tour="${a}"]`));
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
    const avanzarDesde = (i, eraPuente) => { if (idxRef.current === i && !eraPuente) { interaccion.current = true; avanzar(); } };
    if (paso.accion === 'click') {
      const h = (e) => {
        if (!dentro(e.target)) return;
        const eraPuente = saltoRef.current;
        clearTimeout(temp.current);
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
    // EL ENTER ES DEL CAMPO, NO DEL TUTORIAL. Acá no se escucha la tecla: cuando la persona aprieta
    // Enter está CONFIRMANDO el campo (agrega el diseño, aplica el nombre) y eso tiene que pasar
    // igual que sin tutorial. El tutorial se entera por el EFECTO: el campo que confirma se vacía,
    // y ese vaciado —de tener texto a quedar en blanco— es la señal de que la acción se hizo.
    // Salir del campo también es «ya terminé de escribir».
    const hb = (e) => { if (dentro(e.target) && (e.target.value || '').trim()) { clearTimeout(temp.current); avanzarDesde(idx, saltoRef.current); } };
    document.addEventListener('blur', hb, true);
    return () => { clearInterval(vig); document.removeEventListener('input', h, true); document.removeEventListener('blur', hb, true); };
  }, [idx, paso?.ancla, paso?.accion, avanzar, esperaEstado, !!fin]);   // eslint-disable-line react-hooks/exhaustive-deps

  // Salir con Escape.
  useEffect(() => {
    const k = (e) => { if (e.key === 'Escape') onCerrar(); };
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [onCerrar]);

  if (fin) return createPortal(<GloboFin guia={guia} saltada={fin.saltada} onCerrar={onCerrar} />, document.body);
  if (!paso) return null;
  const r = rect ? { x: rect.x - MARGEN, y: rect.y - MARGEN, w: rect.w + MARGEN * 2, h: rect.h + MARGEN * 2 } : null;
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
      <Globo rect={rect} paso={paso} idx={idx} total={guia.pasos.length} esperando={!rect} puente={!!salto}
        onAtras={retroceder} onCerrar={onCerrar} progreso={progreso} trabado={trabado} escape={escape && !trabado}
        onSeguirIgual={() => { if (salto && pasoGuion?.ir) ir(pasoGuion.ir); else { desde.current = -1; avanzar(); } }} />
    </>,
    document.body
  );
}


/**
 * MENÚ DE LA AYUDA. Dos cosas bien separadas, a propósito:
 *   · ARRIBA, el único PASO A PASO: «Armar una tizada», el trabajo de todos los días.
 *   · ABAJO, los RECORRIDOS explicativos («para qué sirve cada cosa»), agrupados por área.
 * La diferencia se dice con todas las letras: uno te hace hacer, los otros sólo te cuentan.
 */
function Menu({ onElegir, onCerrar, estado, retomar, onRetomar, onOlvidar }) {
  const [area, setArea] = useState(null);
  const [trabada, setTrabada] = useState(null);   // {id, motivo} — recorrido que todavía no se puede
  const lista = area ? RECORRIDOS.filter(g => g.area === area) : [];
  const card = {
    display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', borderRadius: 12,
    cursor: 'pointer', textAlign: 'left', border: '1px solid var(--border-light)',
    background: 'rgba(255,255,255,0.03)', color: '#fff', width: '100%',
  };
  const elegir = (g) => {
    const b = bloqueo(g, estado);
    if (b) { setTrabada({ id: g.id, motivo: b }); return; }
    onElegir(g.id);
  };
  const Nota = ({ id }) => (trabada && trabada.id === id) ? (
    <div style={{ fontSize: 11.5, color: 'var(--warning, #e0a020)', lineHeight: 1.45,
      padding: '8px 11px', borderRadius: 9, background: 'rgba(224,160,32,0.10)',
      border: '1px solid rgba(224,160,32,0.32)' }}>{trabada.motivo}</div>
  ) : null;
  const rotulo = { fontSize: 11, fontWeight: 800, letterSpacing: 0.6, textTransform: 'uppercase',
    color: 'var(--text-muted)', margin: '0 0 8px' };

  return createPortal(
    <div onMouseDown={(e) => { if (e.target === e.currentTarget) onCerrar(); }}
      style={{ position: 'fixed', inset: 0, zIndex: 100001, background: 'rgba(0,0,0,0.62)', backdropFilter: 'blur(5px)',
        display: 'flex', alignItems: 'flex-start', justifyContent: 'center', padding: '8vh 20px 24px', overflowY: 'auto' }}>
      <div style={{ width: 560, maxWidth: '100%', background: '#0f1216', border: '1px solid var(--border-light)', borderRadius: 16, padding: 22 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          {area && <button className="btn ghost" style={{ padding: '4px 10px', fontSize: 12 }} onClick={() => { setArea(null); setTrabada(null); }}>←</button>}
          <h3 style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>
            {area ? (AREAS.find(a => a.id === area) || {}).titulo : '¿Con qué te ayudo?'}
          </h3>
          <button onClick={onCerrar} style={{ marginLeft: 'auto', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 17 }}>✕</button>
        </div>

        {area ? (
          /* ── Recorridos del área elegida ── */
          <div style={{ display: 'grid', gap: 9 }}>
            <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', margin: '0 0 4px' }}>
              Te muestro cada cosa y te cuento para qué sirve. No hay que hacer nada.
            </p>
            {lista.map(g => {
              const b = bloqueo(g, estado);
              return (
                <React.Fragment key={g.id}>
                  <button onClick={() => elegir(g)} title={b || ''} style={{ ...card, opacity: b ? 0.62 : 1 }}>
                    <span style={{ flex: 1 }}>
                      <span style={{ display: 'block', fontSize: 14, fontWeight: 700 }}>{g.titulo}</span>
                      <span style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{g.desc}</span>
                    </span>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{g.pasos.length} pantallas</span>
                    <span style={{ color: b ? 'var(--text-muted)' : 'var(--accent)', fontSize: 16 }}>{b ? '🔒' : '›'}</span>
                  </button>
                  <Nota id={g.id} />
                </React.Fragment>
              );
            })}
          </div>
        ) : (<>
          {/* ── Retomar lo que quedó a medias ── */}
          {retomar && (<>
            <div style={{ ...card, borderColor: 'var(--accent)', background: 'rgba(0,216,245,0.07)', marginBottom: 16, cursor: 'default' }}>
              <span style={{ flex: 1 }}>
                <span style={{ display: 'block', fontSize: 13.5, fontWeight: 700 }}>Seguir donde quedaste</span>
                <span style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                  {retomar.guia.titulo} · paso {retomar.idx + 1} de {retomar.guia.pasos.length}
                </span>
              </span>
              <button className="btn ghost" style={{ padding: '5px 10px', fontSize: 11.5 }} onClick={onOlvidar}>Descartar</button>
              <button className="btn primary" style={{ padding: '6px 13px', fontSize: 12 }}
                onClick={() => { const b = bloqueo(retomar.guia, estado); if (b) setTrabada({ id: retomar.guia.id, motivo: b }); else onRetomar(); }}>Seguir →</button>
            </div>
            <Nota id={retomar.guia.id} />
          </>)}

          {/* ── EL paso a paso ── */}
          <div style={rotulo}>Hacerlo paso a paso</div>
          <button onClick={() => onElegir(GUIA_PRINCIPAL.id)}
            style={{ ...card, borderColor: 'var(--accent)', background: 'rgba(0,216,245,0.07)', padding: '14px 16px', marginBottom: 20 }}>
            <span style={{ flex: 1 }}>
              <span style={{ display: 'block', fontSize: 15.5, fontWeight: 800 }}>{GUIA_PRINCIPAL.titulo}</span>
              <span style={{ display: 'block', fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 3, lineHeight: 1.4 }}>{GUIA_PRINCIPAL.desc}</span>
              <span style={{ display: 'block', fontSize: 11.5, color: 'var(--text-muted)', marginTop: 5 }}>
                {GUIA_PRINCIPAL.pasos.length} pasos · unos {GUIA_PRINCIPAL.minutos} min · te voy marcando qué tocar
              </span>
            </span>
            <span style={{ color: 'var(--accent)', fontSize: 18 }}>›</span>
          </button>

          {/* ── Los recorridos explicativos ── */}
          <div style={rotulo}>Para qué sirve cada cosa</div>
          <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', margin: '0 0 10px', lineHeight: 1.45 }}>
            Recorridos cortos: te muestro la pantalla y te explico qué hace cada control. No hay que hacer nada.
          </p>
          <div style={{ display: 'grid', gap: 9 }}>
            {AREAS.map(a => {
              const n = RECORRIDOS.filter(g => g.area === a.id).length;
              if (!n) return null;
              return (
                <button key={a.id} onClick={() => setArea(a.id)} style={card}>
                  <span style={{ flex: 1 }}>
                    <span style={{ display: 'block', fontSize: 14, fontWeight: 700 }}>{a.titulo}</span>
                    <span style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{a.desc}</span>
                  </span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{n}</span>
                  <span style={{ color: 'var(--accent)', fontSize: 16 }}>›</span>
                </button>
              );
            })}
          </div>
        </>)}

        <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 18, lineHeight: 1.5 }}>
          Trabajás sobre tus datos reales: la ayuda no toca ni borra nada, las acciones las hacés vos.
          Podés salir cuando quieras con <b>Escape</b>.
        </div>
      </div>
    </div>,
    document.body
  );
}

/**
 * Punto de entrada. Se monta UNA vez en la app.
 *   abierto / setAbierto  el menú de ayuda
 *   ir(destino)           lleva a la pantalla que pide el paso ({tab, sub, paso, molde, ajuste})
 *   donde                 en qué pantalla está parado el usuario
 *   estado                el ESTADO REAL del sistema (`ayudaEstado` en App.jsx) — ver guias.js
 */
export function Ayuda({ abierto, setAbierto, ir, donde, estado }) {
  const [guiaId, setGuiaId] = useState(null);
  const [desdePaso, setDesdePaso] = useState(0);
  const guia = guiaPorId(guiaId);
  // Lo que quedó a medias en una sesión anterior (o al cerrar con la ✕).
  const [retomar, setRetomar] = useState(null);
  useEffect(() => {
    if (!abierto) return;
    try {
      const g = JSON.parse(localStorage.getItem(LS_PROGRESO) || 'null');
      const gu = g && guiaPorId(g.guiaId);
      setRetomar(gu && g.idx > 0 ? { guia: gu, idx: Math.min(g.idx, gu.pasos.length - 1) } : null);
    } catch { setRetomar(null); }
  }, [abierto]);
  const olvidar = () => { try { localStorage.removeItem(LS_PROGRESO); } catch { /* no-op */ } setRetomar(null); };
  return (
    <>
      {abierto && !guia && (
        <Menu estado={estado} retomar={retomar}
          onCerrar={() => setAbierto(false)}
          onElegir={(id) => { olvidar(); setDesdePaso(0); setGuiaId(id); setAbierto(false); }}
          onRetomar={() => { setDesdePaso(retomar.idx); setGuiaId(retomar.guia.id); setAbierto(false); }}
          onOlvidar={olvidar} />
      )}
      {guia && <Tour guia={guia} ir={ir} donde={donde} estado={estado} desdePaso={desdePaso}
        onCerrar={() => setGuiaId(null)} />}
    </>
  );
}

export default Ayuda;
