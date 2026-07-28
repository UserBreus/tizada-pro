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
function Globo({ rect, paso, idx, total, onSiguiente, onAtras, onCerrar, esperando }) {
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
          Paso {idx + 1} de {total}
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
        <button className="btn primary" style={{ padding: '6px 14px', fontSize: 12, fontWeight: 700 }} onClick={onSiguiente}>
          {idx + 1 === total ? 'Terminar' : 'Siguiente →'}
        </button>
      </div>
    </div>
  );
}

/** El tutorial en sí: recorte + globo + detección de la acción del usuario. */
function Tour({ guia, onCerrar, ir }) {
  const [idx, setIdx] = useState(0);
  const paso = guia.pasos[idx];
  const [rect, elRef] = useAncla(paso?.ancla, true);
  const avanzar = useCallback(() => {
    setIdx(i => (i + 1 >= guia.pasos.length ? (onCerrar(), i) : i + 1));
  }, [guia.pasos.length, onCerrar]);

  // Llevar al usuario a la pantalla del paso (si el guion lo pide).
  useEffect(() => { if (paso?.ir) ir(paso.ir); }, [idx]);   // eslint-disable-line react-hooks/exhaustive-deps

  // Traer el elemento a la vista.
  useEffect(() => {
    const el = elRef.current;
    if (el && rect && (rect.y < 0 || rect.y + rect.h > window.innerHeight)) {
      try { el.scrollIntoView({ block: 'center', behavior: 'smooth' }); } catch { /* no-op */ }
    }
  }, [rect?.y, idx]);   // eslint-disable-line react-hooks/exhaustive-deps

  // AVANCE POR ACCIÓN REAL: se escucha sobre el elemento marcado.
  useEffect(() => {
    const el = elRef.current;
    if (!el || !paso) return;
    if (paso.accion === 'click') {
      const h = () => setTimeout(avanzar, 220);       // deja que la pantalla reaccione primero
      el.addEventListener('click', h);
      return () => el.removeEventListener('click', h);
    }
    if (paso.accion === 'input') {
      const h = (e) => { if ((e.target.value || '').trim().length >= 2) setTimeout(avanzar, 500); };
      el.addEventListener('input', h);
      // el ancla puede ser el contenedor: también se escucha en el input de adentro
      const inner = el.querySelector('input, textarea');
      if (inner) inner.addEventListener('input', h);
      return () => { el.removeEventListener('input', h); if (inner) inner.removeEventListener('input', h); };
    }
  }, [idx, rect, avanzar]);   // eslint-disable-line react-hooks/exhaustive-deps

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
        <div style={{ position: 'fixed', left: r.x, top: r.y, width: r.w, height: r.h, borderRadius: 10, zIndex: 100000,
          boxShadow: '0 0 0 9999px rgba(3,7,12,0.72), 0 0 0 2px var(--accent), 0 0 26px rgba(0,216,245,0.55)',
          pointerEvents: 'none', transition: 'all .18s ease' }} />
      ) : (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(3,7,12,0.72)', zIndex: 100000, pointerEvents: 'none' }} />
      )}
      <Globo rect={rect} paso={paso} idx={idx} total={guia.pasos.length} esperando={!rect}
        onSiguiente={avanzar} onAtras={() => setIdx(i => Math.max(0, i - 1))} onCerrar={onCerrar} />
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
export function Ayuda({ abierto, setAbierto, ir }) {
  const [guiaId, setGuiaId] = useState(null);
  const guia = guiaPorId(guiaId);
  return (
    <>
      {abierto && !guia && <Menu onCerrar={() => setAbierto(false)} onElegir={(id) => { setGuiaId(id); setAbierto(false); }} />}
      {guia && <Tour guia={guia} ir={ir} onCerrar={() => setGuiaId(null)} />}
    </>
  );
}

export default Ayuda;
