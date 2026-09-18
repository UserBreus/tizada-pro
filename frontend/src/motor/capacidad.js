// ¿ESTA COMPUTADORA PUEDE? — PLAN_NAVEGADOR.md, etapa 5 («quien no tenga la potencia no podrá enviar»).
//
// Antes de cada trabajo pesado (preparar un molde, generar la tizada) se mide la máquina y se decide
// con números, no a ojo: los hilos que informa el navegador, la memoria que declara (Chrome/Edge),
// una RESERVA DE PRUEBA de memoria WebAssembly del tamaño que el trabajo va a pedir, y un benchmark
// corto que da «puntos de potencia». Si no alcanza, la pantalla lo dice con todas las letras y no
// deja seguir: NADA se degrada (regla del proyecto: nunca bajar la calidad).
//
// Lo medido (MAPA changelog 478/479): abrir un molde con diseño pide ~3,5 MB de memoria WebAssembly
// por MB de archivo, y por hilo (cada hilo abre el molde entero); la tizada pide lo mismo por mesa
// desplegada abierta más ~200 MB por hoja que se escribe. Los umbrales de abajo salen de ahí.

/** MB de memoria que necesita preparar un molde de `mb` MB con `hilos` hilos. */
export function memoriaParaMolde(mb, hilos) {
  return Math.ceil((3.5 * mb + 120) * Math.max(1, hilos))
}

/** MB de memoria que necesita generar un pedido con `mbMesas` MB de mesas desplegadas y `hojas` hojas. */
export function memoriaParaTizada(mbMesas, hojas = 1) {
  return Math.ceil(3.5 * mbMesas + 200 * Math.max(1, hojas) + 150)
}

/** Lo que el navegador dice de la máquina. `deviceMemory` sólo lo dan Chrome y Edge (tope 8). */
export function equipo() {
  const n = typeof navigator !== 'undefined' ? navigator : {}
  return {
    nucleos: n.hardwareConcurrency || null,
    memoriaGb: n.deviceMemory || null,
    hilos: typeof Worker !== 'undefined',
    wasm: typeof WebAssembly !== 'undefined',
    navegador: n.userAgent || '',
  }
}

/**
 * RESERVA DE PRUEBA: pide `mb` MB de memoria (en bloques) y los suelta. Si el navegador no los
 * da, el trabajo tampoco los va a tener. Devuelve `{ok, mb}` con lo que se pudo reservar.
 */
export function reservaDePrueba(mb) {
  const bloques = []
  const paso = 64
  let reservados = 0
  try {
    while (reservados < mb) {
      const b = new Uint8Array(paso * 1024 * 1024)
      b[0] = 1; b[b.length - 1] = 1          // tocar el bloque: que de verdad se asigne
      bloques.push(b)
      reservados += paso
    }
    return { ok: true, mb: reservados }
  } catch {
    return { ok: false, mb: reservados }
  } finally {
    bloques.length = 0
  }
}

/**
 * BENCHMARK de ~1 s: cuántos «puntos de potencia» tiene esta computadora. Es trabajo parecido al
 * del motor (recorrer números, tocar memoria, transformar arreglos), medido en operaciones por
 * milisegundo y normalizado para que la PC de desarrollo (12 hilos, 2026) dé ~100.
 */
export function puntosDePotencia(ms = 800) {
  const t0 = performance.now()
  let ops = 0
  const a = new Float64Array(1 << 16)
  for (let i = 0; i < a.length; i++) a[i] = Math.sin(i)
  while (performance.now() - t0 < ms) {
    let s = 0
    for (let i = 0; i < a.length; i++) { s += a[i] * a[(i * 7) & 0xffff]; a[i] = s * 1e-9 }
    ops += a.length
  }
  const porMs = ops / (performance.now() - t0)
  return Math.round(porMs / 900)             // ~90.000 ops/ms en la PC de referencia → 100 puntos
}

export const UMBRAL_PUNTOS = 12                    // por debajo, un molde de 100 MB tarda más de un minuto

/**
 * ¿Se puede hacer este trabajo acá? `trabajo` = {tipo: 'molde'|'tizada', mb, hilos?, hojas?}.
 * Devuelve `{puede, motivo, detalle}`; `motivo` ya está en palabras para la pantalla.
 */
export function puedeHacer(trabajo) {
  const eq = equipo()
  if (!eq.wasm || !eq.hilos) {
    return { puede: false, motivo: 'Este navegador no puede preparar moldes ni tizadas. Usá Chrome, Edge o Firefox actualizados.', detalle: eq }
  }
  const hilos = trabajo.hilos || Math.max(2, Math.min((eq.nucleos || 4) - 1, 8))
  const necesita = trabajo.tipo === 'molde' ? memoriaParaMolde(trabajo.mb, hilos) : memoriaParaTizada(trabajo.mb, trabajo.hojas || 1)
  if (eq.memoriaGb && eq.memoriaGb * 1024 * 0.6 < necesita) {
    return { puede: false, detalle: { ...eq, necesita },
             motivo: `Esta computadora no tiene la memoria para ${trabajo.tipo === 'molde' ? 'preparar este molde' : 'generar esta tizada'} de ${Math.round(trabajo.mb)} MB: hacen falta ${(necesita / 1024).toFixed(1)} GB libres y el navegador informa ${eq.memoriaGb} GB en total. Cerrá otras pestañas o programas, o usá una computadora con más memoria.` }
  }
  const reserva = reservaDePrueba(Math.min(necesita, 2048))
  if (!reserva.ok) {
    return { puede: false, detalle: { ...eq, necesita, reserva },
             motivo: `Esta computadora no pudo reservar la memoria que hace falta (${(necesita / 1024).toFixed(1)} GB; se consiguieron ${reserva.mb} MB). Cerrá otras pestañas o programas y volvé a intentarlo.` }
  }
  const puntos = puntosDePotencia()
  if (puntos < UMBRAL_PUNTOS) {
    return { puede: false, detalle: { ...eq, necesita, puntos },
             motivo: `Esta computadora es demasiado lenta para este trabajo (${puntos} puntos de potencia; hacen falta ${UMBRAL_PUNTOS}). Con esta máquina un molde con diseño tardaría más de un minuto: usá otra computadora.` }
  }
  return { puede: true, motivo: '', detalle: { ...eq, necesita, puntos, hilos } }
}
