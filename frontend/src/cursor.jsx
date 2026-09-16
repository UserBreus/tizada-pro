/**
 * EL CURSOR DEL SISTEMA — el orbe que MUESTRA el movimiento.
 *
 * ── POR QUÉ EXISTE ─────────────────────────────────────────────────────────────────────────────
 * Hay cosas que no se explican con palabras ni iluminando un botón: en el visor, para elegir
 * varias piezas de una se **arrastra un recuadro** desde un espacio vacío. Decirlo por escrito no
 * alcanza — hay que verlo. El usuario lo pidió con un video: «podemos hacer que cree como un
 * cursor del sistema para que en ayuda podamos grabar algunos movimientos como este ejemplo»
 * (2026-09-01).
 *
 * ── ES UN CURSOR, PERO NO **EL** CURSOR ────────────────────────────────────────────────────────
 * 🔴 Tiene que LEERSE como un puntero (si no, no se entiende que muestra un movimiento del mouse),
 * y a la vez no confundirse con el de la máquina. Dos intentos hicieron falta:
 *   1. la flechita blanca de siempre = EXACTAMENTE la de Windows: dos flechas iguales en pantalla
 *      y no se sabía cuál era la de uno;
 *   2. un orbe (un punto con anillo): inconfundible, sí, pero ya no se leía como un cursor
 *      («no me gusta ese punto, debe de ser un cursor, con forma de cursor pero moderno»).
 * Lo que quedó: **la silueta de un puntero**, con las esquinas redondeadas y pintada con el cian de
 * la app (borde oscuro y glow para que se despegue del fondo). Forma conocida, identidad propia.
 *
 * Este cursor NO toca nada: es un dibujo. La acción real siempre la hace la persona (misma regla
 * que el resto de la ayuda). Sólo muestra, en bucle, el gesto que hay que hacer.
 *
 * ── CÓMO SE MUEVE ──────────────────────────────────────────────────────────────────────────────
 * Un ciclo dura `MS_CICLO` y tiene cuatro tiempos, para que se lea como una mano de verdad:
 *   1. aparece en el punto de inicio (en el aire, anillo ancho);
 *   2. APRIETA: el anillo se cierra sobre el núcleo y sale un pulso;
 *   3. se DESLIZA hasta el final, dejando la estela y dibujando el recuadro;
 *   4. SUELTA (otro pulso), queda un instante y el ciclo vuelve a empezar.
 *
 * 🔴 Se dibuja con `requestAnimationFrame` y atributos del SVG, sin re-renderizar React en cada
 * cuadro: el tutorial ya vive encima de una app pesada (el visor tiene cientos de piezas) y un
 * `setState` por cuadro le robaría fluidez justo a la pantalla que se está enseñando.
 */
import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

const MS_CICLO = 2800;        // lo que dura el gesto completo, de punta a punta
const T_APRIETA = 0.16;       // hasta acá está por bajar
const T_ARRASTRA = 0.74;      // hasta acá se desliza
const T_SUELTA = 0.88;        // después queda quieto un instante y vuelve a empezar

/** Suaviza el movimiento: arranca despacio y frena despacio (una mano no va a velocidad constante). */
function suave(t) {
  return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
}

export default function CursorGuia({ desde, hasta, recuadro = true }) {
  const orbe = useRef(null);      // el grupo que se mueve (anillo + núcleo)
  const anillo = useRef(null);
  const pulso = useRef(null);     // el aro que se expande al apretar y al soltar
  const estela = useRef(null);
  const caja = useRef(null);

  useEffect(() => {
    if (!desde || !hasta) return undefined;
    let vivo = true;
    let t0 = null;
    const cuadro = (ahora) => {
      if (!vivo) return;
      if (t0 == null) t0 = ahora;
      const t = ((ahora - t0) % MS_CICLO) / MS_CICLO;

      let px = desde.x, py = desde.y, apretado = false, avance = 0;
      if (t >= T_APRIETA && t < T_ARRASTRA) {
        avance = suave((t - T_APRIETA) / (T_ARRASTRA - T_APRIETA));
        px = desde.x + (hasta.x - desde.x) * avance;
        py = desde.y + (hasta.y - desde.y) * avance;
        apretado = true;
      } else if (t >= T_ARRASTRA) {
        px = hasta.x; py = hasta.y; avance = 1;
        apretado = t < T_SUELTA;
      }

      if (orbe.current) {
        // el puntero se hunde un poco al apretar: el mismo gesto que hace una mano de verdad
        orbe.current.setAttribute('transform', `translate(${px} ${py}) scale(${apretado ? 0.86 : 1})`);
        orbe.current.style.opacity = t < 0.03 ? '0' : '1';
      }
      // el halo se CIERRA y se enciende cuando aprieta: es la señal de «botón apretado»
      if (anillo.current) {
        anillo.current.setAttribute('r', apretado ? 11 : 15);
        anillo.current.style.opacity = apretado ? '1' : '0.55';
      }
      // el PULSO: un aro que se abre justo al apretar y justo al soltar
      if (pulso.current) {
        const dAp = Math.abs(t - T_APRIETA), dSu = Math.abs(t - T_SUELTA);
        const cerca = Math.min(dAp, dSu);
        const k = cerca < 0.09 ? 1 - cerca / 0.09 : 0;      // 1 en el golpe, 0 lejos
        pulso.current.setAttribute('transform', `translate(${px} ${py})`);
        pulso.current.setAttribute('r', 10 + (1 - k) * 22);
        pulso.current.style.opacity = String(k * 0.55);
      }
      // la ESTELA: por dónde viene, para que se entienda la dirección del gesto
      if (estela.current) {
        if (apretado || avance === 1) {
          estela.current.setAttribute('x1', desde.x); estela.current.setAttribute('y1', desde.y);
          estela.current.setAttribute('x2', px); estela.current.setAttribute('y2', py);
          estela.current.style.opacity = '0.55';
        } else {
          estela.current.style.opacity = '0';
        }
      }
      if (caja.current) {
        if (recuadro && (apretado || avance === 1)) {
          caja.current.setAttribute('x', Math.min(desde.x, px));
          caja.current.setAttribute('y', Math.min(desde.y, py));
          caja.current.setAttribute('width', Math.abs(px - desde.x));
          caja.current.setAttribute('height', Math.abs(py - desde.y));
          caja.current.style.opacity = '1';
        } else {
          caja.current.style.opacity = '0';
        }
      }
      requestAnimationFrame(cuadro);
    };
    const id = requestAnimationFrame(cuadro);
    return () => { vivo = false; cancelAnimationFrame(id); };
  }, [desde && desde.x, desde && desde.y, hasta && hasta.x, hasta && hasta.y, recuadro]);

  if (!desde || !hasta) return null;
  // UN SOLO SVG a pantalla completa: así la estela y el recuadro se dibujan en las mismas
  // coordenadas que el orbe. `pointerEvents: none` en todo — es un DIBUJO, lo que se toca es la app.
  return createPortal(
    <svg width="100%" height="100%" style={{ position: 'fixed', inset: 0, zIndex: 100004,
      pointerEvents: 'none', overflow: 'visible' }}>
      <defs>
        {/* el relleno del puntero: claro en la punta, cian de la app en el cuerpo */}
        <linearGradient id="tp-nucleo" x1="0" y1="0" x2="0.7" y2="1">
          <stop offset="0%" stopColor="#eafcff" />
          <stop offset="45%" stopColor="var(--accent, #00d8f5)" />
          <stop offset="100%" stopColor="#0aa8c2" />
        </linearGradient>
        <filter id="tp-glow" x="-120%" y="-120%" width="340%" height="340%">
          <feGaussianBlur stdDeviation="4" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      {/* el recuadro que va quedando (lo mismo que hace la app de verdad) */}
      <rect ref={caja} x="0" y="0" width="0" height="0" rx="3" fill="rgba(0,216,245,0.10)"
        stroke="var(--accent, #00d8f5)" strokeWidth="1.5" strokeDasharray="6 4" style={{ opacity: 0 }} />
      {/* la estela: de dónde salió el gesto */}
      <line ref={estela} x1="0" y1="0" x2="0" y2="0" stroke="var(--accent, #00d8f5)"
        strokeWidth="2.5" strokeLinecap="round" strokeDasharray="2 7" style={{ opacity: 0 }} />
      {/* el pulso del clic */}
      <circle ref={pulso} cx="0" cy="0" r="10" fill="none" stroke="var(--accent, #00d8f5)"
        strokeWidth="2" style={{ opacity: 0 }} />
      {/* EL PUNTERO. La punta está en (0,0) del grupo, así que cae EXACTO en el punto del gesto.
          Las esquinas se redondean con `strokeLinejoin: round` + un trazo grueso del mismo color
          del borde: se ve moderno y no hace falta un path lleno de curvas. */}
      <g ref={orbe} filter="url(#tp-glow)">
        {/* el halo de fondo: lo despega de cualquier pantalla, clara u oscura */}
        <circle ref={anillo} cx="7" cy="9" r="15" fill="rgba(0,216,245,0.10)"
          stroke="rgba(0,216,245,0.35)" strokeWidth="1" />
        <path d="M0 0 L0 20 L5.4 15.2 L8.8 23.2 L12.6 21.6 L9.2 13.8 L16.4 13.2 Z"
          fill="url(#tp-nucleo)" stroke="#04141a" strokeWidth="2.2" strokeLinejoin="round" />
        {/* un brillo en el filo, que es lo que lo hace ver «de vidrio» y no plano */}
        <path d="M1.6 2.6 L1.6 15.4 L5.9 11.6" fill="none" stroke="rgba(255,255,255,0.75)"
          strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
      </g>
    </svg>,
    document.body,
  );
}
