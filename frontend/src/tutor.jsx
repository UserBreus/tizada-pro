/**
 * MOTOR DE AYUDA GUIADA — el tutorial paso a paso, estilo tutorial de videojuego.
 *
 * Oscurece la pantalla, deja ILUMINADO el campo o botón exacto que hay que usar y muestra un
 * globo con la consigna. El paso avanza cuando el usuario HACE la acción de verdad (decisión del
 * usuario: se aprende haciendo), y siempre queda un «Siguiente» por si algo se traba.
 *
 * Todo el contenido vive en `guias.js`: acá está sólo el mecanismo. Para que el motor pueda
 * iluminar un elemento, ese elemento tiene que estar marcado en el JSX con `data-tour="id"`.
 *
 * NO toca los datos del usuario: la acción real siempre la hace la persona.
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { GUIAS, AREAS, guiaPorId } from './guias';

const MARGEN = 8;          // aire entre el elemento iluminado y el recorte
const REINTENTO = 250;     // cada cuánto se busca el elemento que todavía no apareció

/**
 * CÓMO SE LLEGA A CADA PANTALLA. La ayuda mira DÓNDE ESTÁ el usuario y, si no está donde el paso
 * necesita, no lo teletransporta: le va marcando los botones hasta llegar. Cada destino dice qué
 * botón tocar y, si a su vez necesita estar en otro lado, se encadena solo (`necesita`).
 */
const RUTAS = {
  'tab:pedidos':      { ancla: 'nav-pedidos',   texto: 'Primero vamos a Pedidos. Tocá acá.' },
  'tab:config':       { ancla: 'nav-config',    texto: 'Primero vamos a Configuración. Tocá acá.' },
  'sub:productos':    { ancla: 'cfg-productos', texto: 'Ahora entrá a «Molderías».', necesita: { tab: 'config', sub: 'dashboard' } },
  'sub:telas':        { ancla: 'cfg-telas',     texto: 'Ahora entrá a «Telas».',     necesita: { tab: 'config', sub: 'dashboard' } },
  'sub:dashboard':    { ancla: 'nav-config',    texto: 'Volvé al panel de Configuración tocando acá.' },
  'sub:columnas':     { ancla: 'cfg-columnas',  texto: 'Ahora entrá a «Planillas».',   necesita: { tab: 'config', sub: 'dashboard' } },
  'sub:reglas':       { ancla: 'cfg-reglas',    texto: 'Ahora entrá a «Reglas de planilla».', necesita: { tab: 'config', sub: 'dashboard' } },
  'sub:nesting':      { ancla: 'cfg-nesting',   texto: 'Ahora entrá a «Reglas de Nesting».', necesita: { tab: 'config', sub: 'dashboard' } },
  'sub:fuentes':      { ancla: 'cfg-fuentes',   texto: 'Ahora entrá a «Catálogo de Fuentes».', necesita: { tab: 'config', sub: 'dashboard' } },
  'sub:perfil':       { ancla: 'cfg-perfil',    texto: 'Ahora entrá a «Perfil de color».', necesita: { tab: 'config', sub: 'dashboard' } },
  'sub:usuarios':     { ancla: 'cfg-usuarios',  texto: 'Ahora entrá a «Usuarios y permisos».', necesita: { tab: 'config', sub: 'dashboard' } },
  // Dentro de un molde abierto: el menú de ajustes tiene un botón por pantalla.
  'ajuste:variables': { ancla: 'ajuste-variables', texto: 'Entrá a «Variables».', necesita: { ajuste: 'menu' } },
  'ajuste:telas':     { ancla: 'ajuste-telas',     texto: 'Entrá a «Telas asignadas».', necesita: { ajuste: 'menu' } },
  'ajuste:borde':     { ancla: 'ajuste-borde',     texto: 'Entrá a «Borde de corte».', necesita: { ajuste: 'menu' } },
  'ajuste:etiqueta':  { ancla: 'ajuste-etiqueta',  texto: 'Entrá a «Etiqueta».', necesita: { ajuste: 'menu' } },
  'ajuste:diseno':    { ancla: 'ajuste-diseno',    texto: 'Entrá a «Diseño».', necesita: { ajuste: 'menu' } },
  'ajuste:planilla':  { ancla: 'ajuste-planilla',  texto: 'Entrá a «Planilla».', necesita: { ajuste: 'menu' } },
  'ajuste:terminologia': { ancla: 'ajuste-terminologia', texto: 'Entrá a «Nombres».', necesita: { ajuste: 'menu' } },
  'ajuste:nestingsel': { ancla: 'ajuste-nestingsel', texto: 'Entrá a «Nesting».', necesita: { ajuste: 'menu' } },
  'ajuste:molderia':  { ancla: 'ajuste-molderia',  texto: 'Entrá a «Moldería».', necesita: { ajuste: 'menu' } },
  'ajuste:editable':  { ancla: 'ajuste-editable',  texto: 'Entrá a «Editable».', necesita: { ajuste: 'menu' } },
  'ajuste:menu':      { ancla: 'ajuste-volver',    texto: 'Volvé al menú de ajustes tocando acá.' },
  'paso:moldes':      { ancla: 'pedido-volver-moldes', texto: 'Volvé al primer paso del pedido.' },
  // Los pasos del pedido son en fila: para llegar a la planilla hay que pasar por el arte.
  'paso:arte':        { ancla: 'pedido-ir-arte',   texto: 'Pasá al arte con «Cargar el arte».', necesita: { tab: 'pedidos', paso: 'moldes' } },
  'paso:planilla':    { ancla: 'arte-siguiente',   texto: 'Pasá a la planilla con «A la planilla».', necesita: { tab: 'pedidos', paso: 'arte' } },
};

/** Devuelve el paso-PUENTE que hay que hacer ahora para acercarse al destino, o null si ya llegó. */
function puente(destino, donde) {
  if (!destino) return null;
  const claves = ['tab', 'sub', 'paso', 'ajuste'];
  for (const k of claves) {
    const q = destino[k];
    if (!q || donde[k] === q) continue;               // no pedido, o ya estamos
    const r = RUTAS[`${k}:${q}`];
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
function esPasoNav(p) {
  if (!p || !p.ir || !p.ancla) return false;
  return Object.entries(p.ir).some(([k, v]) => (RUTAS[`${k}:${v}`] || {}).ancla === p.ancla);
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
      setRect(r.width || r.height ? { x: r.left, y: r.top, w: r.width, h: r.height } : null);
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
 * Globo de la consigna. Hay DOS tipos, bien distintos a propósito:
 *   ACCIÓN  (cyan, «TENÉS QUE HACER ESTO»): el usuario tiene que tocar/escribir algo. No avanza
 *           solo: espera la acción de verdad. No hay botón «Siguiente».
 *   INFO    (violeta, «PARA QUE SEPAS»): sólo explica para qué sirve ese espacio. Avanza solo
 *           después de un ratito, con una barra que muestra cuánto falta.
 * El PUENTE (ámbar) es una acción especial: llevar al usuario a la pantalla que corresponde.
 */
function Globo({ rect, paso, idx, total, onAtras, onCerrar, esperando, puente, progreso, trabado, onSeguirIgual }) {
  const ANCHO = 340;
  const esInfo = !puente && paso.accion === 'ver';
  const col = puente ? 'var(--warning, #e0a020)' : esInfo ? '#a78bfa' : 'var(--accent)';
  const fondo = puente ? 'linear-gradient(180deg,#231a0d,#171208)'
    : esInfo ? 'linear-gradient(180deg,#171526,#100f1b)' : 'linear-gradient(180deg,#0b1c22,#081418)';
  const rotulo = puente ? 'Te llevo hasta ahí' : esInfo ? 'Para que sepas' : 'Hacé esto';
  const icono = puente ? '➜' : esInfo ? 'i' : '☝';
  const vh = window.innerHeight, vw = window.innerWidth;
  let top, left, flecha = 'arriba';
  if (!rect) { top = vh / 2 - 90; left = vw / 2 - ANCHO / 2; flecha = null; }
  else {
    const abajo = rect.y + rect.h + MARGEN + 14;
    const cabe = abajo + 200 < vh;
    top = cabe ? abajo : Math.max(12, rect.y - 200 - MARGEN);
    flecha = cabe ? 'arriba' : 'abajo';
    left = Math.min(Math.max(12, rect.x + rect.w / 2 - ANCHO / 2), vw - ANCHO - 12);
  }
  return (
    <div style={{ position: 'fixed', top, left, width: ANCHO, zIndex: 100002, background: fondo,
      border: `1.5px solid ${col}`, borderRadius: 14, padding: 16,
      boxShadow: `0 18px 50px rgba(0,0,0,0.7), 0 0 0 1px ${col}44` }}>
      {flecha && (
        <span style={{ position: 'absolute', left: '50%', marginLeft: -8, [flecha === 'arriba' ? 'top' : 'bottom']: -8,
          width: 14, height: 14, background: fondo.includes('231a') ? '#231a0d' : fondo.includes('1715') ? '#171526' : '#0b1c22',
          borderLeft: `1.5px solid ${col}`, borderTop: `1.5px solid ${col}`,
          transform: flecha === 'arriba' ? 'rotate(45deg)' : 'rotate(225deg)' }} />
      )}
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
      {/* INFO: barra que se llena sola (no hay que apretar nada). ACCIÓN: recordatorio de qué se espera. */}
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
            {paso.accion === 'input' ? 'Escribilo y seguimos' : 'Tocá lo que está marcado'}
          </span>
        )}
      </div>
    </div>
  );
}

/** El tutorial en sí: recorte + globo + detección de la acción del usuario. */
function Tour({ guia, onCerrar, ir, donde }) {
  const [idx, setIdx] = useState(0);
  const pasoGuion = guia.pasos[idx];
  // AYUDA INTELIGENTE: si el usuario no está en la pantalla que el paso necesita, primero se le
  // marca el camino (un botón por vez) en vez de saltar solo. Cuando llega, sigue el guion.
  const salto = pasoGuion?.ir ? puente(pasoGuion.ir, donde || {}) : null;
  const paso = salto || pasoGuion;
  const [rect, elRef] = useAncla(paso?.ancla, true);
  // Un paso avanza UNA sola vez. Sin esto, un mismo clic podía disparar dos avances (el listener se
  // re-registraba al re-medir el elemento) y el tutorial saltaba del paso 1 al 3.
  const desde = useRef(-1);
  const idxRef = useRef(0);          // el paso ACTUAL, para que una acción vieja no empuje de más
  const avanzar = useCallback((n = 1) => {
    setIdx(i => {
      if (desde.current >= i) return i;          // ya se avanzó desde este paso
      desde.current = i;
      if (i + n >= guia.pasos.length) { setTimeout(onCerrar, 0); return i; }
      return i + n;
    });
  }, [guia.pasos.length, onCerrar]);
  const retroceder = useCallback(() => { desde.current = -1; setIdx(i => Math.max(0, i - 1)); }, []);
  useEffect(() => { idxRef.current = idx; }, [idx]);

  // PASOS INFORMATIVOS: avanzan SOLOS (el usuario no tiene que apretar nada). El tiempo sale del
  // largo del texto —lo que tarda en leerse— con un piso de 3,5 s. `progreso` alimenta la barrita.
  const [progreso, setProgreso] = useState(0);
  // RED DE SEGURIDAD: si lo que hay que marcar no aparece en unos segundos (la pantalla necesita
  // algo previo, como tener un molde abierto), se ofrece seguir igual en vez de quedar esperando.
  const [trabado, setTrabado] = useState(false);
  useEffect(() => {
    setTrabado(false);
    if (rect) return;
    const t = setTimeout(() => setTrabado(true), 5000);
    return () => clearTimeout(t);
  }, [idx, !!rect, !!salto]);
  useEffect(() => {
    setProgreso(0);
    if (salto || !paso || paso.accion !== 'ver') return;
    const largo = (paso.texto || '').length + (paso.nota || '').length;
    const ms = Math.min(9000, Math.max(2600, largo * 45));
    const t0 = Date.now();
    const tick = setInterval(() => {
      const p = Math.min(1, (Date.now() - t0) / ms);
      setProgreso(p);
      if (p >= 1) { clearInterval(tick); avanzar(); }
    }, 100);
    return () => clearInterval(tick);
  }, [idx, !!salto]);   // eslint-disable-line react-hooks/exhaustive-deps
  const saltoRef = useRef(false);
  useEffect(() => { saltoRef.current = !!salto; }, [salto]);

  // YA ESTÁS AHÍ: si el paso era sólo para llevarte a una pantalla y estás parado en ella, se da por
  // cumplido solo. (Antes el tutorial abría en Pedidos y el primer paso te pedía tocar «Pedidos».)
  useEffect(() => { if (!salto && esPasoNav(pasoGuion)) avanzar(); }, [idx, !!salto]);   // eslint-disable-line react-hooks/exhaustive-deps

  // Si el paso pide una pantalla y NO hay camino marcado (no está en RUTAS), se navega solo para no
  // dejar al usuario colgado. Cuando sí hay camino, lo hace él tocando los botones (`salto`).
  useEffect(() => { if (pasoGuion?.ir && !salto) ir(pasoGuion.ir); }, [idx, !!salto]);   // eslint-disable-line react-hooks/exhaustive-deps

  // FOCO: si el paso pide escribir y el foco quedó en la nada (el body), se lo damos al campo que
  // estamos marcando. Sin foco la persona igual «escribe» —el navegador manda las teclas al último
  // campo— pero el ENTER no llega al campo y no confirma nada. Nunca se le saca el foco a otro
  // campo: sólo se toma cuando no lo tiene nadie.
  useEffect(() => {
    if (!paso || paso.accion !== 'input' || !rect) return;
    const el = elRef.current;
    if (!el) return;
    const campo = el.matches('input, textarea, select') ? el : el.querySelector('input, textarea, select');
    const act = document.activeElement;
    if (campo && (!act || act === document.body)) { try { campo.focus({ preventScroll: true }); } catch { /* no-op */ } }
  }, [idx, !!rect]);   // eslint-disable-line react-hooks/exhaustive-deps

  // Traer el elemento a la vista.
  useEffect(() => {
    const el = elRef.current;
    if (el && rect && (rect.y < 0 || rect.y + rect.h > window.innerHeight)) {
      try { el.scrollIntoView({ block: 'center', behavior: 'smooth' }); } catch { /* no-op */ }
    }
  }, [rect?.y, idx]);   // eslint-disable-line react-hooks/exhaustive-deps

  // AVANCE POR ACCIÓN REAL. Se escucha en el DOCUMENTO (fase de captura) y se pregunta si lo que
  // se tocó cae dentro del ancla. Antes el listener iba pegado al elemento: si todavía no existía
  // (pantalla que tarda) no se enganchaba nunca, y al re-medirlo se registraba de más → saltos.
  useEffect(() => {
    if (!paso || (paso.accion !== 'click' && paso.accion !== 'input')) return;
    // El paso puede aceptar más de un lugar: `tambien` lista las otras anclas que valen igual (el
    // campo que confirma con Enter vale lo mismo que el botón que hace esa confirmación).
    const anclas = [paso.ancla, ...(paso.tambien || [])];
    const dentro = (t) => t && t.closest && anclas.some(a => t.closest(`[data-tour="${a}"]`));
    let temp = null;                                   // UN solo temporizador por paso
    // Avanza sólo si seguimos parados en el mismo paso (una acción vieja no empuja de más).
    // `eraPuente` se mira EN EL MOMENTO del evento, no después: si el botón que se tocó cambia de
    // pantalla, un instante más tarde el paso viejo «pide» la pantalla anterior y se encendería un
    // puente que bloqueaba el avance para siempre (el tutorial quedaba trabado al tocar, por
    // ejemplo, «Cargar el arte»).
    const avanzarDesde = (i, eraPuente) => { if (idxRef.current === i && !eraPuente) avanzar(); };
    if (paso.accion === 'click') {
      const h = (e) => {
        if (!dentro(e.target)) return;
        const eraPuente = saltoRef.current;
        clearTimeout(temp);
        temp = setTimeout(() => avanzarDesde(idx, eraPuente), 200);
      };
      document.addEventListener('click', h, true);
      // Si el paso acepta que la acción se haga desde un campo (`tambien`) y ese campo se VACÍA, es
      // que ya se confirmó (con Enter o con el botón): el clic no hace falta y el paso está cumplido.
      const vig = (paso.tambien || []).length
        ? vigilarVaciado(paso.tambien, () => { clearTimeout(temp); avanzarDesde(idx, saltoRef.current); })
        : null;
      return () => { clearTimeout(temp); if (vig) clearInterval(vig); document.removeEventListener('click', h, true); };
    }
    // ESCRIBIR: se espera a que TERMINE de escribir (cada tecla reinicia la cuenta). Antes cada
    // tecla programaba su propio avance y una palabra de 10 letras saltaba 10 pasos de una.
    const h = (e) => {
      if (!dentro(e.target) || !(e.target.value || '').trim()) return;   // basta UNA letra: un talle es «M»
      const eraPuente = saltoRef.current;
      clearTimeout(temp);
      temp = setTimeout(() => avanzarDesde(idx, eraPuente), 650);   // dejó de escribir
    };
    document.addEventListener('input', h, true);
    // Y si confirma (Enter o botón) antes de esa pausa, el campo se vacía: también está hecho.
    const vig = vigilarVaciado(anclas, () => { clearTimeout(temp); avanzarDesde(idx, saltoRef.current); });
    // Si el guion lo permite, ENTER también cuenta como hecho (varios campos del sistema
    // confirman con Enter en vez de con el botón).
    // EL ENTER ES DEL CAMPO, NO DEL TUTORIAL. Acá no se escucha la tecla: cuando la persona aprieta
    // Enter está CONFIRMANDO el campo (agrega el diseño, aplica el nombre) y eso tiene que pasar
    // igual que sin tutorial. El tutorial se entera por el EFECTO: el campo que confirma se vacía,
    // y ese vaciado —de tener texto a quedar en blanco— es la señal de que la acción se hizo.
    // Salir del campo también es «ya terminé de escribir».
    const hb = (e) => { if (dentro(e.target) && (e.target.value || '').trim()) { clearTimeout(temp); avanzarDesde(idx, saltoRef.current); } };
    document.addEventListener('blur', hb, true);
    return () => { clearTimeout(temp); clearInterval(vig); document.removeEventListener('input', h, true); document.removeEventListener('blur', hb, true); };
  }, [idx, paso?.ancla, paso?.accion, avanzar]);   // eslint-disable-line react-hooks/exhaustive-deps

  // Salir con Escape.
  useEffect(() => {
    const k = (e) => { if (e.key === 'Escape') onCerrar(); };
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [onCerrar]);

  if (!paso) return null;
  const r = rect ? { x: rect.x - MARGEN, y: rect.y - MARGEN, w: rect.w + MARGEN * 2, h: rect.h + MARGEN * 2 } : null;
  return createPortal(
    <>
      {/* RECORTE: el `box-shadow` gigante oscurece TODO menos este rectángulo. `pointerEvents:none`
          es clave: deja que el usuario toque de verdad el elemento iluminado. */}
      {r ? (
        <>
          {/* Fondo MUY oscuro + el hueco iluminado con borde grueso y resplandor. */}
          <div style={{ position: 'fixed', left: r.x, top: r.y, width: r.w, height: r.h, borderRadius: 12, zIndex: 100000,
            boxShadow: '0 0 0 9999px rgba(2,5,9,0.88), 0 0 0 4px var(--accent), 0 0 40px 6px rgba(0,216,245,0.75), inset 0 0 22px rgba(0,216,245,0.30)',
            pointerEvents: 'none', transition: 'all .18s ease' }} />
          {/* Halo que late, para que salte a la vista dónde hay que tocar. */}
          <div className="tour-pulso" style={{ position: 'fixed', left: r.x - 6, top: r.y - 6, width: r.w + 12, height: r.h + 12,
            borderRadius: 16, border: '2px solid var(--accent)', zIndex: 100001, pointerEvents: 'none' }} />
        </>
      ) : (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(2,5,9,0.88)', zIndex: 100000, pointerEvents: 'none' }} />
      )}
      <Globo rect={rect} paso={paso} idx={idx} total={guia.pasos.length} esperando={!rect} puente={!!salto}
        onAtras={retroceder} onCerrar={onCerrar} progreso={progreso} trabado={trabado}
        onSeguirIgual={() => { if (salto && pasoGuion?.ir) ir(pasoGuion.ir); else { desde.current = -1; avanzar(); } }} />
    </>,
    document.body
  );
}

/** Modal con las guías disponibles, agrupadas por área. */
function Menu({ onElegir, onCerrar }) {
  const [area, setArea] = useState(null);
  const lista = area ? GUIAS.filter(g => g.area === area) : [];
  return createPortal(
    <div onMouseDown={(e) => { if (e.target === e.currentTarget) onCerrar(); }}
      style={{ position: 'fixed', inset: 0, zIndex: 100001, background: 'rgba(0,0,0,0.62)', backdropFilter: 'blur(5px)',
        display: 'flex', alignItems: 'flex-start', justifyContent: 'center', padding: '8vh 20px 24px', overflowY: 'auto' }}>
      <div style={{ width: 620, maxWidth: '100%', background: '#0f1216', border: '1px solid var(--border-light)', borderRadius: 16, padding: 22 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
          {area && <button className="btn ghost" style={{ padding: '4px 10px', fontSize: 12 }} onClick={() => setArea(null)}>←</button>}
          <h3 style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>{area ? (AREAS.find(a => a.id === area) || {}).titulo : '¿Con qué te ayudo?'}</h3>
          <button onClick={onCerrar} style={{ marginLeft: 'auto', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 17 }}>✕</button>
        </div>
        <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', margin: '0 0 16px' }}>
          {area ? 'Elegí la tarea y te voy marcando en pantalla qué tocar.' : 'Elegí el tema. Después te guío paso a paso sobre tu propio trabajo.'}
        </p>
        <div style={{ display: 'grid', gap: 9 }}>
          {!area && AREAS.map(a => {
            const n = GUIAS.filter(g => g.area === a.id).length;
            if (!n) return null;
            return (
              <button key={a.id} onClick={() => setArea(a.id)}
                style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '13px 15px', borderRadius: 12, cursor: 'pointer', textAlign: 'left',
                  border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.03)', color: '#fff' }}>
                <span style={{ flex: 1 }}>
                  <span style={{ display: 'block', fontSize: 14, fontWeight: 700 }}>{a.titulo}</span>
                  <span style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{a.desc}</span>
                </span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{n} guía{n > 1 ? 's' : ''}</span>
                <span style={{ color: 'var(--accent)', fontSize: 16 }}>›</span>
              </button>
            );
          })}
          {area && lista.map(g => (
            <button key={g.id} onClick={() => onElegir(g.id)}
              style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '13px 15px', borderRadius: 12, cursor: 'pointer', textAlign: 'left',
                border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.03)', color: '#fff' }}>
              <span style={{ flex: 1 }}>
                <span style={{ display: 'block', fontSize: 14, fontWeight: 700 }}>{g.titulo}</span>
                <span style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{g.desc}</span>
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{g.pasos.length} pasos · {g.minutos}′</span>
              <span style={{ color: 'var(--accent)', fontSize: 16 }}>›</span>
            </button>
          ))}
        </div>
      </div>
    </div>,
    document.body
  );
}

/**
 * Punto de entrada. Se monta UNA vez en la app.
 *   abierto / setAbierto  el modal de «¿con qué te ayudo?»
 *   ir(destino)           lleva a la pantalla que pide el paso ({tab, sub, paso, ajuste})
 */
export function Ayuda({ abierto, setAbierto, ir, donde }) {
  const [guiaId, setGuiaId] = useState(null);
  const guia = guiaPorId(guiaId);
  return (
    <>
      {abierto && !guia && <Menu onCerrar={() => setAbierto(false)} onElegir={(id) => { setGuiaId(id); setAbierto(false); }} />}
      {guia && <Tour guia={guia} ir={ir} donde={donde} onCerrar={() => setGuiaId(null)} />}
    </>
  );
}

export default Ayuda;
