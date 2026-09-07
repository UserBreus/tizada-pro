/**
 * DE LA GRABACIÓN AL GUION — lo que el tutorial le va a mostrar a la persona.
 *
 * Vive aparte de `tutor.jsx` a propósito: ese archivo importa React y sólo corre en el navegador,
 * así que la lógica que arma el guion no se podía ejecutar ni verificar. Acá es JS puro y el
 * contrato la corre de verdad (`verificar_diccionario.mjs`).
 *
 * Hace dos cosas, y las dos al REPRODUCIR (no al grabar): así, mejorar una explicación o corregir
 * la secuencia arregla todos los tutoriales ya grabados, sin que nadie regrabe nada.
 *   1. le pone a cada paso las palabras del diccionario;
 *   2. COMPLETA las etapas que la grabación no tiene porque quien grabó ya las tenía hechas.
 *
 * 🔴 LO QUE NO HACE, Y ES A PROPÓSITO (decisión del usuario, 2026-08-28): **no repite nada por
 * su cuenta**. No cicla entre diseños, no arma «bloques por diseño», no tiene marcas «↻» ni
 * desvíos automáticos. Un tutorial muestra lo que se grabó, en el orden en que se grabó: si se
 * quiere uno para dos diseños, se graba haciendo dos diseños. Se probó lo contrario durante un día
 * entero y el resultado era imposible de predecir para quien lo seguía.
 */
// La extensión `.js` NO es opcional: este módulo lo importa también `node` (el contrato lo
// ejecuta de verdad), y node exige la extensión. Vite acepta las dos formas.
import { explicar, SECUENCIA, DICCIONARIO, AVISOS_CONOCIDOS, modalDeBoton } from './diccionario.js';
import { normalizar, esNombreDeControl, partirAncla } from './localizar.js';

/** Un paso armado desde una etapa de la SECUENCIA (uno que la grabación no tiene pero hace falta). */
function pasoDeEtapa(et) {
  const d = explicar(et.ancla, '');
  // `_agregado` = este paso no se grabó: lo completó el sistema. La vista real del editor lo
  // dibuja distinto (borde punteado) para que se sepa qué puso la persona y qué puso el sistema.
  const paso = { ancla: et.ancla, accion: 'click', texto: d.como, ir: { tab: 'pedidos', paso: et.paso },
                 _agregado: true,
                 hecho: (E) => { try { return !!et.listo(E); } catch { return false; } } };
  if (d.que) paso.nota = d.que;
  if (d.cuantos && typeof d.cuantos.mide === 'function') paso.cuantos = d.cuantos;
  return paso;
}

/**
 * CON VARIAS COSAS ENCIMA A LA VEZ, ¿QUÉ ATIENDE EL TUTORIAL? **La de adelante.**
 *
 * 🔴 Un modal tapa la carga que corre atrás: hasta que no se cierre, lo de atrás no se puede ni
 * ver ni tocar. Antes ganaba la carga y el tutorial pedía «esperá a que esto termine» señalando
 * algo escondido detrás de una ventana que la persona tenía que cerrar primero (reporte del
 * usuario 2026-08-31, con «Perfil de color del diseño» sobre «poniendo el diseño sobre el
 * molde»). Al cerrar el modal, si la carga sigue, se pasa solo a la espera.
 *
 *   modalTapando   hay un modal abierto que NO es el del paso actual
 *   hayCarga       el sistema está trabajando (una ventana de trabajo a la vista)
 *   cargaEsDelPaso el paso ES esperar esa carga (un «esperar aviso» del editor)
 */
export function queAtender({ modalTapando, modalDelPasoAbierto, hayCarga, cargaEsDelPaso }) {
  if (modalTapando) return 'modal';                    // lo de adelante, primero
  // 🔴 El modal de adelante ES donde hay que hacer el paso (su botón «Entendido», por ejemplo):
  // se atiende el paso. Antes ganaba la carga de atrás y el tutorial decía «esperá» con el botón
  // a la vista (reporte del usuario 2026-08-31, segunda vuelta).
  if (modalDelPasoAbierto) return 'paso';
  if (hayCarga && !cargaEsDelPaso) return 'carga';
  return 'paso';
}

/** La SECCIÓN de un paso: la lista o el panel al que pertenece. El ancla puede venir afinada
 *  («txt:jugador#pedido-diseno-lista» = ese botón, dentro de esa lista) y para saber DE QUÉ parte
 *  del sistema es el paso, lo que vale es la sección. */
function seccionDe(p) {
  if (!p) return '';
  if (p.seccion) return p.seccion;
  const a = String(p.ancla || '');
  // 🔴 por el ÚLTIMO `#`: el nombre de un control puede tener uno adentro («pieza #1»)
  return a.startsWith('txt:') ? (partirAncla(a).seccion || a) : a;
}

/** ¿El paso es de CARGAR LA PLANILLA? (una columna, o la tabla entera) Esos no se dan por hechos
 *  con un clic: se llenan fila por fila y los termina la persona. */
function esDeLaPlanilla(ancla) {
  const a = String(ancla || '');
  return a.startsWith('col:') || a === 'planilla-tabla';
}

/** QUÉ ES ESTE MODAL — para cuando uno se abre en medio del tutorial. Si el diccionario tiene
 *  su entrada (`modal:<título normalizado>`) se usa ésa; si no, el propio título del modal ya
 *  dice bastante y se arma un cartel honesto con él. */
export function explicarModal(titulo) {
  const d = DICCIONARIO['modal:' + normalizar(titulo || '')];
  if (d) return { texto: d.como, nota: d.que };
  return { texto: `Apareció «${titulo || 'un aviso del sistema'}». Leelo y respondé lo que pide.`,
           nota: 'El tutorial espera: cuando este cartel se cierre, seguimos donde estábamos.' };
}

/** El orden real de las etapas del pedido: es contra esto que se decide «anterior/posterior». */
const ORDEN_ETAPAS = ['diseno', 'moldes', 'arte', 'planilla', 'resultados'];

/** A qué etapa del pedido pertenece un paso: por su ancla (si está en la SECUENCIA) o por la
 *  pantalla que pide (`ir.paso`, que el grabador guarda con cada clic). */
function etapaDe(paso) {
  const et = SECUENCIA.find((e) => e.ancla === paso.ancla);
  if (et) return et.paso;
  // los pasos GRABADOS traen `donde`; los ya convertidos a guion traen `ir`. Vale cualquiera.
  const d = paso.ir || paso.donde;
  return (d && d.tab === 'pedidos' && d.paso) || null;
}

/**
 * ¿ESTE PASO YA QUEDÓ ATRÁS? — el tutorial arranca desde donde está parada la persona.
 *
 * True sólo si se dan las DOS cosas:
 *   1. el paso pertenece a una etapa ANTERIOR a la pantalla en la que está parada la persona
 *      (`donde.paso`), y
 *   2. esa etapa está CUMPLIDA según el estado real (todas sus reglas `listo` de la SECUENCIA).
 *
 * La segunda condición es la red: estar parado en la planilla NO prueba que las telas estén —
 * si la etapa quedó a medias, el paso NO se saltea y el tutorial lleva de vuelta a terminarla.
 */
export function pasoSuperado(paso, E, donde) {
  if (!paso || !E || !donde || donde.tab !== 'pedidos') return false;
  const est = etapaDe(paso);
  if (!est) return false;
  const iP = ORDEN_ETAPAS.indexOf(est);
  const iD = ORDEN_ETAPAS.indexOf(donde.paso);
  if (iP < 0 || iD < 0 || iP >= iD) return false;      // sólo etapas ANTERIORES a donde está
  const reglas = SECUENCIA.filter((e) => e.paso === est);
  if (!reglas.length) return true;                     // etapa sin regla: la posición alcanza
  try { return reglas.every((e) => !!e.listo(E)); } catch { return false; }
}

export function aGuion(t) {
  if (!t) return null;
  // Los tutoriales grabados ANTES del 2026-08-28 pueden traer marcas de repetición («↻ acá
  // arranca el siguiente diseño») y campos del ciclo. Esa lógica se eliminó: las marcas se
  // DESCARTAN —no marcaban un lugar de la pantalla, eran un punto de repetición— y el resto de
  // los pasos se reproduce plano, en su orden. Así un tutorial viejo sigue sirviendo.
  // 🔴 LO QUE ES DEL SISTEMA DE AYUDA NO ES UN PASO DEL TRABAJO. Un tutorial grabado antes puede
  // traer el «Parar y guardar» del grabador (o el botón «Ayuda» con el que se abrió el menú): se
  // descartan al reproducir, sin tener que regrabar.
  const DE_LA_AYUDA = new Set(['txt:parar y guardar', 'txt:grabar un tutorial', 'txt:ayuda',
                               'nav-ayuda', 'txt:cerrar el tutorial', 'txt:siguiente']);
  const pasos = (t.pasos || [])
    .filter((p) => (p.accion || '') !== 'vuelta')
    .filter((p) => !DE_LA_AYUDA.has(String(p.ancla || '').toLowerCase()))
    .map((p) => {
    // Paso «ESPERAR AVISO» del editor: no marca un control — espera a que el modal indicado
    // aparezca y se cierre. El Tour lo trata como una espera con explicación.
    if ((p.accion || '') === 'modal') {
      // Una ventana de TRABAJO no se responde: se espera. Decir «respondé lo que pide» sobre
      // «Se está armando la tizada» manda al usuario a buscar un botón que no existe.
      const _trabaja = (AVISOS_CONOCIDOS.cargas || []).includes(p.modal);
      const pm = { accion: 'modalPaso', modal: p.modal || '', esTrabajo: _trabaja || undefined,
        texto: p.texto || (_trabaja
          ? ('Acá el sistema se pone a trabajar y aparece el cartel «' + p.modal + '». Esperá a que termine.')
          : ('Ahora aparece «' + (p.modal || 'un aviso') + '». Leelo y respondé lo que pide.')),
        nota: _trabaja
          ? 'No hay nada que tocar: cuando termine, el tutorial sigue solo.'
          : 'El tutorial sigue solo cuando ese aviso se cierre.' };
      if (p.donde && Object.keys(p.donde).length) pm.ir = p.donde;
      return pm;
    }
    const d = explicar(p.ancla, p.etiqueta);
    // `p.texto` = cartel corregido a mano en el EDITOR: le gana al del diccionario.
    const paso = { ancla: p.ancla, accion: p.accion || 'click', texto: p.texto || d.como };
    // el NOMBRE de lo que se tocó al grabar: hace falta al final, para afinar un ancla que quedó
    // en un contenedor y saber QUÉ botón de ahí adentro era
    if (p.etiqueta) paso._etq = p.etiqueta;
    if (p.texto) paso._aMano = true;   // cartel escrito en el editor: no se toca
    // 🔴 LA PLANILLA NO SE TOCA: SE CARGA. Un paso de columna abarca TODAS las filas, así que no
    // puede darse por hecho con el primer clic — hacerlo saltaba a la columna siguiente antes de
    // dejar escribir o elegir en el desplegable (reporte del usuario 2026-08-31). Estos pasos se
    // terminan a mano, con «Siguiente →».
    // 🔴 UN PASO QUE NO SE PUEDE MOSTRAR NO PUEDE FRENAR EL TUTORIAL. Un tutorial viejo puede traer
    // un ancla que no es el nombre de nada («txt:?», «txt:👁»): se grabó cuando el sistema leía mal
    // el rótulo de un campo. Ya no se generan más, pero los guardados quedan — y con ellos el
    // tutorial se comía 5 segundos en «No encuentro ese lugar» antes de dejar seguir. Marcado así,
    // si no aparece en pantalla se pasa de largo solo.
    const _a = String(p.ancla || '');
    if (_a.startsWith('txt:') && !esNombreDeControl(partirAncla(_a).nombre)) paso.dudoso = true;
    if (esDeLaPlanilla(p.ancla)) { paso.manual = true; paso.manualPor = 'planilla'; }
    // 🔴 UN CAMPO DE ESCRITURA TAMPOCO SE DA POR HECHO SOLO (pedido del usuario 2026-09-01):
    // «cuando son campos de escribir no saltará automático, debe presionar Siguiente así puede
    // escribir». El avance solo queda para lo que NO hay que completar: los botones y las ventanas
    // emergentes. Si no, el tutorial se iba al paso siguiente apenas se tocaba el campo —o a mitad
    // de una palabra— y no dejaba cargar nada.
    else if ((p.accion || '') === 'input') { paso.manual = true; paso.manualPor = 'campo'; }
    // 🔴 UN MOVIMIENTO (arrastre): viaja con sus dos puntos, en porcentajes del elemento, y el
    // motor lo MUESTRA con el cursor guía. El cartel lo dice con todas las letras: hay gestos que
    // no se explican con palabras (pedido del usuario 2026-09-01, con el video del recuadro).
    // 🔴 EL RECORRIDO NO SE GUARDA NI SE COPIA: el cursor muestra un gesto GENÉRICO, siempre en el
    // mismo lugar del elemento (decisión del usuario, 2026-09-01 — quien sigue el tutorial tiene
    // otro molde y otras piezas, así que calcar el arrastre de quien grabó no enseña nada). Del
    // paso sólo importa QUE ES un movimiento. Esto además hace andar los que se grabaron cuando el
    // servidor todavía descartaba los puntos.
    if ((p.accion || '') === 'arrastre') {
      paso.accion = 'arrastre';
      if (!p.texto) {
        paso.texto = 'Arrastrá como te muestra el cursor: apretá y, sin soltar, llevalo hasta el otro punto.';
        paso.nota = (d.que ? d.que + ' ' : '')
          + 'Con el recuadro elegís varias cosas de una vez, sin tocarlas una por una.';
      }
    }
    if (p.ventana) paso.ventana = p.ventana;   // el paso vive dentro de esta ventana
    // 🔴 UN PASO QUE ES EL BOTÓN DE UN AVISO (tutoriales grabados ANTES de que se guardara la
    // ventana). «Tocá "Entendido"» es el botón del aviso «Perfil de color del diseño»: a quien
    // sigue el tutorial puede no salirle, y el paso se quedaba 5 s en «No encuentro ese lugar»
    // (auditoría 2026-08-31). Si el diccionario sabe de qué ventana es ese botón, se dice.
    // (vale también con el ancla afinada —«txt:crear molde#molde-crear-ok»—: lo que dice en qué
    //  ventana vive el paso es el NOMBRE del botón, no la forma del ancla)
    if (!paso.ventana && String(p.ancla || '').startsWith('txt:')) {
      const v = modalDeBoton(p.etiqueta || partirAncla(p.ancla).nombre);
      if (v) paso.ventana = v;
    }
    if (d.que) paso.nota = d.que;
    if (p.donde && Object.keys(p.donde).length) paso.ir = p.donde;
    // PASOS INTELIGENTES (ver diccionario.js). `listo` sirve para las dos cosas a la vez: si ya da
    // true al empezar, el motor SALTEA el paso; si no, es lo que lo hace avanzar cuando se cumple
    // de verdad. Así un tutorial grabado cargando una fuente no le pide eso a quien ya la tiene.
    if (typeof d.listo === 'function') paso.hecho = (E) => d.listo(E);
    // `cuantos` no se resuelve acá: lo pregunta el Tour en el momento, porque la respuesta depende
    // del trabajo que tenga entre manos quien está siguiendo el tutorial.
    if (d.cuantos && typeof d.cuantos.mide === 'function') paso.cuantos = d.cuantos;
    return paso;
  });

  // 🔴 COMPLETAR LO QUE LA GRABACIÓN NO TIENE. Una grabación sólo guarda lo que la persona
  // LLEGÓ A HACER: si al grabar ya tenía el diseño cargado, no tocó nada ahí y el tutorial no
  // llevaba a nadie a elegirlo, aunque sin eso no se puede seguir. Acá se meten las etapas
  // anteriores que falten, ANTES del primer paso que las necesita. Cada una trae su `listo`, así
  // que a quien ya la tenga resuelta NO se le muestra: se completa lo que falta, no se repite lo
  // hecho. (Pedido del usuario: «leé los pasos coherentes y hacé que se pongan automático».)
  const orden = SECUENCIA.map((e) => e.clave || e.paso);
  // 🔴 también por SECCIÓN: un paso afinado («txt:jugador#pedido-diseno-lista») ES el paso de
  // esa etapa; sin esto el completado la agregaba de nuevo y el diseño aparecía dos veces.
  const anclasGrabadas = new Set(pasos.flatMap((p) => [p.ancla, seccionDe(p)]));
  // 🔴 LAS COLUMNAS **SON** LA PLANILLA. Un tutorial que graba «Talle», «Nombre», «Número»… ya
  // enseña a cargar la planilla: agregarle además el paso de la tabla entera (que es la etapa de
  // la SECUENCIA) repetía lo mismo al final, después de las columnas — pasaba en los DOS
  // tutoriales reales del usuario (auditoría 2026-08-31).
  if (pasos.some((p) => String(p.ancla || '').startsWith('col:'))) anclasGrabadas.add('planilla-tabla');
  const yaEsta = (et) => anclasGrabadas.has(et.ancla);
  const completos = [];
  const puestas = new Set();
  // 🔴 Un botón de TRANSICIÓN exige TODO lo anterior a su etapa DESTINO. Sin esto, «A la
  // planilla» sólo pedía lo anterior al arte: la etapa de telas (que es del arte) se insertaba
  // DESPUÉS del botón y su `ir` arrastraba de la planilla al arte — «me manda a hacer un paso
  // después que era antes» (reporte del usuario, 2026-08-28).
  const AVANZA_A = { 'pedido-ir-moldes': 'moldes', 'pedido-ir-arte': 'arte',
                     'arte-siguiente': 'planilla', 'planilla-enviar': 'resultados' };
  const hastaDe = (p) => {
    const et2 = SECUENCIA.find((e) => e.ancla === p.ancla);
    if (et2) return orden.indexOf(et2.clave || et2.paso);
    const destino = AVANZA_A[p.ancla];
    if (destino) {
      const k = SECUENCIA.findIndex((e) => e.paso === destino);
      return k < 0 ? orden.length : k;
    }
    return orden.indexOf((p.ir && p.ir.paso) || '');
  };
  for (const p of pasos) {
    const et = SECUENCIA.find((e) => e.ancla === p.ancla);
    const hasta = hastaDe(p);
    if (hasta > 0) {
      for (let k = 0; k < hasta; k++) {
        const prev = SECUENCIA[k];
        const cl = prev.clave || prev.paso;
        if (puestas.has(cl) || yaEsta(prev)) continue;
        puestas.add(cl);
        completos.push(pasoDeEtapa(prev));
      }
    }
    if (et) puestas.add(et.clave || et.paso);
    completos.push(p);
  }

  // 🔴 EL BOTÓN, NO EL PANEL (tutoriales ya grabados). Si un paso quedó anclado a un CONTENEDOR
  // (`resultados-mesas`) pero el grabador guardó la ETIQUETA del botón que se tocó, se afina el
  // ancla a «ese botón dentro de esa sección». Así los dos pasos «resultados-mesas» del tutorial
  // del usuario —«Descargar sólo la hoja 1» y «Descargar la ficha técnica»— vuelven a ser dos
  // pasos distintos, sin regrabar nada. Va AL FINAL: antes del completado, cambiar el ancla le
  // sacaba al paso su etapa y se desordenaba todo (lo agarró el contrato §1).
  // Si ese botón ya no está, `buscar` cae a la sección: nunca se queda sin marcar.
  for (const p of completos) {
    if (p._agregado || !p.ancla || p.ancla.includes(':')) continue;
    // 🔴 EN UNA LISTA DE OPCIONES NO SE AFINA NUNCA: aunque quien grabó haya tocado UNA sola
    // tarjeta («Cuello redondo»), el paso es «elegí la que necesites», no «tocá ésa» (pedido del
    // usuario 2026-08-31: «en el paso de elegir molde también es multiopción; no debe ir a uno
    // directo»). El cartel genérico del diccionario ya dice lo correcto.
    if ((explicar(p.ancla, '') || {}).opciones) continue;
    const etq = normalizar(p._etq || '');
    if (!etq) continue;
    // 🔴 NO SE AFINA CON CUALQUIER TEXTO. El afinado sirve para decir CUÁL botón de un panel se
    // tocó; pero lo que el grabador guardó puede ser un párrafo, un contador o un símbolo, y ahí el
    // cartel resultante es inservible. En el tutorial «Cargar molde» del usuario salían cosas como
    // «Tocá "✓ 120"» (la cuenta de piezas seleccionadas), «Tocá "?"», «Tocá "👁"» y hasta
    // «Tocá "6XL · pieza #1 — Espalda 1…"» (el contenido entero del visor). En todos esos casos es
    // mejor el cartel de la sección, que está escrito a mano en el diccionario.
    // Se exige: nombre corto y con letras de verdad (un botón se llama «Guardar», no «✓ 120»).
    if (etq.length > 40 || !/[a-z]{2}/.test(etq)) continue;
    const propio = normalizar(explicar(p.ancla, '').nombre || '');
    if (etq === propio) continue;              // la etiqueta ES la del elemento marcado
    p.seccion = p.ancla;                       // por si hace falta saber de dónde salió
    p.ancla = 'txt:' + etq + '#' + p.ancla;
    // …y el cartel nombra EL BOTÓN, no la sección: si no, dos pasos distintos decían lo mismo
    // («Esperá a que termine de armar la tizada» para dos botones de descarga distintos).
    if (!p._aMano) p.texto = 'Tocá «' + (p._etq || '').trim() + '».';
  }

  // 🔴 OPCIONES INTERCAMBIABLES (pedido del usuario 2026-08-31). Varios clics seguidos sobre la
  // MISMA lista de opciones no son «tocá éste y después éste»: son «elegí N». Quien grabó eligió
  // JUGADOR y GOLERO; quien sigue el tutorial puede necesitar otros dos. Se juntan en un paso con
  // la CANTIDAD, y el motor cuenta los que se toquen, sean cuales sean.
  // 🔴 TUTORIALES GRABADOS ANTES: si un paso quedó atado a UNA opción de una lista
  // («txt:jugador#pedido-diseno-chips»), se le saca la puntería: en una lista de opciones el paso
  // es LA LISTA. El grabador nuevo ya no las afina (`data-opciones`), pero lo guardado sigue ahí.
  for (const p of completos) {
    const a = String(p.ancla || '');
    if (!a.startsWith('txt:') || !a.includes('#')) continue;
    const sec = partirAncla(a).seccion;
    // 🔴 DOS MOTIVOS PARA VOLVER A LA SECCIÓN: que sea una lista de opciones (no se apunta a una
    // tarjeta) o que lo guardado NO SEA UN NOMBRE de control. Lo segundo es lo que salvaba al
    // tutorial «Cargar molde» del usuario, lleno de pasos «Tocá "✓ 120"» y «Tocá "👁"».
    const _nom = partirAncla(a).nombre;
    const _d = explicar(sec, '') || {};
    if (!_d.opciones && !_d.lienzo && esNombreDeControl(_nom)) continue;
    p.ancla = sec;
    delete p.seccion;
    if (!p._aMano) {
      const d3 = explicar(sec, '');
      p.texto = d3.como || p.texto;
      if (d3.que) p.nota = d3.que;
    }
  }

  const juntados = [];
  for (const p of completos) {
    const ult = juntados[juntados.length - 1];
    // la SECCIÓN del paso: la que puso el afinado, o la que ya trae el ancla («txt:jugador#lista»
    // — el grabador nuevo la guarda así desde el vamos)
    const base = seccionDe(p);
    const esOpcion = !p._agregado && !!(explicar(base, '') || {}).opciones;
    if (ult && esOpcion && seccionDe(ult) === base && (ult.cuantas || ult._opcion)) {
      ult.cuantas = (ult.cuantas || 1) + 1;
      ult.ancla = base;                                   // se marca LA LISTA, no un botón suelto
      delete ult.seccion;
      const d2 = explicar(base, '');
      ult.texto = `Elegí ${ult.cuantas} de esta lista (las que necesites).`;
      if (d2.que) ult.nota = d2.que;
      continue;
    }
    if (esOpcion) { p._opcion = true; }
    // 🔴 DOS CLICS SEGUIDOS EN EL MISMO LUGAR NO SON DOS PASOS: se escribe en dos filas de la
    // misma columna, se toca dos veces la misma tarjeta. El tutorial repetía el mismo cartel dos
    // veces seguidas (se vio en «2 colores»: `col:nombre` ×2, `col:numero` ×2). Va DESPUÉS de la
    // rama de opciones —si no, se comía la cuenta— y exige ancla de verdad: dos «esperar aviso»
    // seguidos no son un duplicado, son dos ventanas distintas.
    // 🔴 …PERO UN CLIC Y UN MOVIMIENTO EN EL MISMO LUGAR NO SON EL MISMO PASO. En el visor se toca
    // una pieza y DESPUÉS se arrastra un recuadro: dos anclas iguales, dos cosas distintas. Al no
    // mirar la acción, el arrastre se descartaba como «repetido» y el gesto no llegaba nunca al
    // tutorial — «funciona cuando estás grabando pero no cuando estás siguiendo el tutorial»
    // (reporte del usuario 2026-09-01).
    const _mismaAccion = (ult && (ult.accion || 'click')) === (p.accion || 'click');
    if (ult && p.ancla && ult.ancla === p.ancla && _mismaAccion && !p._agregado && !ult._agregado
        && !p.cuantas && !ult.cuantas) {
      continue;
    }
    juntados.push(p);
  }
  completos.length = 0;
  completos.push(...juntados);

  // 🔴 «¿NO ES EL MISMO PASO DE RECIÉN?» — SE DICE CUÁL VUELTA ES. Un tutorial grabado con dos
  // diseños tiene DOS veces «Tocá el diseño…» y DOS veces «Tocá la prenda…», con carteles
  // idénticos: quien lo sigue no sabe si está repitiendo o si el tutorial se colgó (auditoría
  // 2026-08-31, tutorial «2 colores»). ⚠️ Esto NO es lógica de repetición —eso está prohibido y
  // sigue estándolo—: es sólo rotular pasos que YA se grabaron, tal como se grabaron.
  const cuantasVeces = {};
  for (const p of completos) if (p.ancla) cuantasVeces[p.ancla] = (cuantasVeces[p.ancla] || 0) + 1;
  const vaPor = {};
  for (const p of completos) {
    if (!p.ancla || cuantasVeces[p.ancla] < 2 || p._agregado) continue;
    vaPor[p.ancla] = (vaPor[p.ancla] || 0) + 1;
    const rotulo = `(Vez ${vaPor[p.ancla]} de ${cuantasVeces[p.ancla]} que el tutorial pasa por acá.)`;
    p.nota = p.nota ? `${p.nota} ${rotulo}` : rotulo;
  }

  // 🔴 UN PASO GRABADO TAMBIÉN TIENE SU REGLA. Hasta acá, «no se pide lo que ya está hecho» valía
  // sólo para los pasos que AGREGA el sistema: los grabados no heredaban el `listo` de la
  // SECUENCIA aunque fueran exactamente la misma etapa. Por eso «Elegí el diseño» se le pedía a
  // quien ya tenía los diseños cargados… y ahí tocar los que ya estaban elegidos los DESMARCABA
  // (auditoría 2026-08-31, verificado en pantalla). Va AL FINAL, cuando el ancla ya es la
  // definitiva (afinada o des-afinada), así que también repone la regla que el des-afinado de las
  // listas de opciones se llevaba puesta.
  //
  // ⚠️ SALVO los pasos «elegí N de esta lista»: ésos no se miden con el `listo` de la etapa (que
  // pregunta si hay AL MENOS UNO), sino contando cuántas opciones hay puestas — eso lo resuelve el
  // motor mirando la pantalla.
  for (const p of completos) {
    if (p.hecho || p.cuantas || p._agregado) continue;
    const et = SECUENCIA.find((e) => e.ancla === p.ancla || e.ancla === seccionDe(p));
    if (!et) continue;
    p.hecho = (E) => { try { return !!et.listo(E); } catch { return false; } };
  }

  return { id: t.id, titulo: t.nombre, desc: t.desc || '', pasos: completos,
           minutos: Math.max(1, Math.round(completos.length / 4)) };
}
