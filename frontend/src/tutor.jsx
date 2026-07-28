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
  // Dentro de un molde abierto: el menú de ajustes tiene un botón por pantalla.
  'ajuste:variables': { ancla: 'ajuste-variables', texto: 'Entrá a «Variables».', necesita: { ajuste: 'menu' } },
  'ajuste:telas':     { ancla: 'ajuste-telas',     texto: 'Entrá a «Telas asignadas».', necesita: { ajuste: 'menu' } },
  'ajuste:borde':     { ancla: 'ajuste-borde',     texto: 'Entrá a «Borde de corte».', necesita: { ajuste: 'menu' } },
  'ajuste:etiqueta':  { ancla: 'ajuste-etiqueta',  texto: 'Entrá a «Etiqueta».', necesita: { ajuste: 'menu' } },
  'ajuste:diseno':    { ancla: 'ajuste-diseno',    texto: 'Entrá a «Diseño».', necesita: { ajuste: 'menu' } },
  'ajuste:menu':      { ancla: 'ajuste-volver',    texto: 'Volvé al menú de ajustes tocando acá.' },
  'paso:moldes':      { ancla: 'pedido-volver-moldes', texto: 'Volvé al primer paso del pedido.' },
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

/** Globo con la consigna, ubicado donde entre (abajo del elemento, o arriba si no hay lugar). */
function Globo({ rect, paso, idx, total, onSiguiente, onAtras, onCerrar, esperando, puente }) {
  const ANCHO = 330;
  const vh = window.innerHeight, vw = window.innerWidth;
  let top, left, flecha = 'arriba';
  if (!rect) {                                  // sin elemento: centrado (mientras se busca)
    top = vh / 2 - 90; left = vw / 2 - ANCHO / 2; flecha = null;
  } else {
    const abajo = rect.y + rect.h + MARGEN + 14;
    const cabeAbajo = abajo + 190 < vh;
    top = cabeAbajo ? abajo : Math.max(12, rect.y - 190 - MARGEN);
    flecha = cabeAbajo ? 'arriba' : 'abajo';
    left = Math.min(Math.max(12, rect.x + rect.w / 2 - ANCHO / 2), vw - ANCHO - 12);
  }
  return (
    <div style={{ position: 'fixed', top, left, width: ANCHO, zIndex: 100002,
      background: 'linear-gradient(180deg, #0f1720, #0b1118)', border: '1px solid var(--accent)',
      borderRadius: 14, boxShadow: '0 18px 50px rgba(0,0,0,0.65), 0 0 0 1px rgba(0,216,245,0.25)', padding: 16 }}>
      {flecha && (
        <span style={{ position: 'absolute', left: '50%', marginLeft: -8, [flecha === 'arriba' ? 'top' : 'bottom']: -8,
          width: 14, height: 14, background: '#0f1720', borderLeft: '1px solid var(--accent)', borderTop: '1px solid var(--accent)',
          transform: flecha === 'arriba' ? 'rotate(45deg)' : 'rotate(225deg)' }} />
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 9 }}>
        <span style={{ fontSize: 10.5, fontWeight: 800, letterSpacing: 0.6, textTransform: 'uppercase', color: 'var(--accent)' }}>
          {puente ? 'Te llevo hasta ahí' : `Paso ${idx + 1} de ${total}`}
        </span>
        <button onClick={onCerrar} title="Salir de la ayuda"
          style={{ marginLeft: 'auto', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 15, lineHeight: 1 }}>✕</button>
      </div>
      <div style={{ fontSize: 14, color: '#fff', lineHeight: 1.45, fontWeight: 600 }}>{paso.texto}</div>
      {paso.nota && <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.4, marginTop: 7 }}>{paso.nota}</div>}
      {esperando && (
        <div style={{ fontSize: 11.5, color: 'var(--warning, #e0a020)', marginTop: 9 }}>
          Buscando ese lugar en pantalla…
        </div>
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 13 }}>
        {idx > 0 && (
          <button className="btn ghost" style={{ padding: '6px 12px', fontSize: 12 }} onClick={onAtras}>← Atrás</button>
        )}
        {/* Barrita de avance */}
        <div style={{ flex: 1, height: 4, borderRadius: 999, background: 'rgba(255,255,255,0.10)', overflow: 'hidden' }}>
          <div style={{ width: `${((idx + 1) / total) * 100}%`, height: '100%', background: 'var(--accent)' }} />
        </div>
        {!puente && (
          <button className="btn primary" style={{ padding: '6px 14px', fontSize: 12, fontWeight: 700 }} onClick={onSiguiente}>
            {idx + 1 === total ? 'Terminar' : 'Siguiente →'}
          </button>
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
  const avanzar = useCallback(() => {
    setIdx(i => {
      if (desde.current >= i) return i;          // ya se avanzó desde este paso
      desde.current = i;
      if (i + 1 >= guia.pasos.length) { setTimeout(onCerrar, 0); return i; }
      return i + 1;
    });
  }, [guia.pasos.length, onCerrar]);
  const retroceder = useCallback(() => { desde.current = -1; setIdx(i => Math.max(0, i - 1)); }, []);
  useEffect(() => { idxRef.current = idx; }, [idx]);
  const saltoRef = useRef(false);
  useEffect(() => { saltoRef.current = !!salto; }, [salto]);

  // Si el paso pide una pantalla y NO hay camino marcado (no está en RUTAS), se navega solo para no
  // dejar al usuario colgado. Cuando sí hay camino, lo hace él tocando los botones (`salto`).
  useEffect(() => { if (pasoGuion?.ir && !salto) ir(pasoGuion.ir); }, [idx, !!salto]);   // eslint-disable-line react-hooks/exhaustive-deps

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
    const dentro = (t) => t && t.closest && t.closest(`[data-tour="${paso.ancla}"]`);
    let temp = null;                                   // UN solo temporizador por paso
    // `avanzarDesde` sólo corre si seguimos parados en el mismo paso: así una acción vieja no
    // empuja pasos de más.
    // Si lo cumplido fue un PUENTE, no se avanza el guion: al cambiar de pantalla el puente
    // desaparece solo y el mismo paso queda listo para hacerse.
    const avanzarDesde = (i) => { if (idxRef.current === i && !saltoRef.current) avanzar(); };
    if (paso.accion === 'click') {
      const h = (e) => { if (dentro(e.target)) { clearTimeout(temp); temp = setTimeout(() => avanzarDesde(idx), 280); } };
      document.addEventListener('click', h, true);
      return () => { clearTimeout(temp); document.removeEventListener('click', h, true); };
    }
    // ESCRIBIR: se espera a que TERMINE de escribir (cada tecla reinicia la cuenta). Antes cada
    // tecla programaba su propio avance y una palabra de 10 letras saltaba 10 pasos de una.
    const h = (e) => {
      if (!dentro(e.target) || (e.target.value || '').trim().length < 2) return;
      clearTimeout(temp);
      temp = setTimeout(() => avanzarDesde(idx), 900);
    };
    document.addEventListener('input', h, true);
    // Si el guion lo permite, ENTER también cuenta como hecho (varios campos del sistema
    // confirman con Enter en vez de con el botón).
    const hk = (e) => { if (e.key === 'Enter' && dentro(e.target)) { clearTimeout(temp); temp = setTimeout(() => avanzarDesde(idx), 280); } };
    document.addEventListener('keydown', hk, true);
    return () => { clearTimeout(temp); document.removeEventListener('input', h, true); document.removeEventListener('keydown', hk, true); };
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
        onSiguiente={() => { desde.current = -1; avanzar(); }} onAtras={retroceder} onCerrar={onCerrar} />
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
