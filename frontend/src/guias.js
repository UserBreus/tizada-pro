/**
 * GUIONES DE AYUDA — el CONTENIDO de los tutoriales, separado del motor (`tutor.jsx`).
 *
 * Cada guía es una tarea real del sistema, contada paso a paso. Se escriben acá, en texto plano,
 * para poder corregir o ampliar la ayuda SIN tocar el motor.
 *
 * Un paso:
 *   ancla    'id' del elemento a iluminar. En el JSX se marca con `data-tour="id"`.
 *            Si el elemento no está en pantalla todavía, el motor espera a que aparezca.
 *   texto    qué tiene que hacer el usuario, en criollo y en imperativo («Tocá acá…»).
 *   accion   cómo se pasa al paso siguiente:
 *              'click'  cuando toca el elemento         (lo más común)
 *              'input'  cuando escribe algo adentro
 *              'ver'    es sólo para mirar → avanza con «Siguiente»
 *              'espera' avanza solo cuando aparece el elemento del paso siguiente
 *   ir       (opcional) a qué pantalla hay que llevarlo antes del paso: {tab, sub, paso, ajuste}
 *   nota     (opcional) aclaración corta que va abajo del texto, en gris.
 *
 * REGLA: el usuario trabaja sobre SUS datos reales (decisión del usuario), así que ningún paso
 * borra ni cambia nada por su cuenta: la acción siempre la hace la persona.
 */

// ── ÁREA 1 · MOLDES: crear uno y dejarlo listo para usar ────────────────────────────────────────
const CREAR_MOLDE = {
  id: 'crear-molde',
  area: 'moldes',
  titulo: 'Crear un molde de cero',
  desc: 'Subir la moldería, ponerle nombre a las piezas y dejarla lista.',
  minutos: 5,
  pasos: [
    { ancla: 'nav-config', ir: { tab: 'config' }, accion: 'click',
      texto: 'Entrá a Configuración.' },
    { ancla: 'cfg-productos', ir: { tab: 'config', sub: 'dashboard' }, accion: 'click',
      texto: 'Abrí Molderías: acá viven todos los moldes.' },
    { ancla: 'molde-nuevo', accion: 'click',
      texto: 'Tocá «Nuevo molde».' },
    { ancla: 'molde-nombre', accion: 'input',
      texto: 'Escribí el nombre del molde. Ej: «Camiseta fútbol».',
      nota: 'Es el nombre con el que lo vas a elegir después en el pedido.' },
    { ancla: 'molde-crear-ok', accion: 'click',
      texto: 'Confirmá para crearlo.' },
    { ancla: 'molde-subir', accion: 'click',
      texto: 'Ahora subí el archivo de la moldería (.ai, .pdf o .dxf).',
      nota: 'Es el archivo con TODAS las piezas y todos los talles.' },
    { ancla: 'visor-molde', accion: 'ver',
      texto: 'Listo: acá ves tu moldería. Cada pieza tiene su número.',
      nota: 'Con la rueda del mouse hacés zoom y con el clic derecho la movés.' },
  ],
};

const NOMBRAR_PIEZAS = {
  id: 'nombrar-piezas',
  area: 'moldes',
  titulo: 'Ponerle nombre a las piezas',
  desc: 'Decirle al sistema cuál es el frente, la espalda, la manga…',
  minutos: 6,
  pasos: [
    { ancla: 'ajuste-variables', ir: { ajuste: 'variables' }, accion: 'click',
      texto: 'Entrá a «Variables»: ahí se nombran las piezas.' },
    { ancla: 'paso-nombrar', accion: 'click',
      texto: 'Tocá el paso «Nombrar».' },
    { ancla: 'visor-molde', accion: 'ver',
      texto: 'Tocá una pieza en el molde para elegirla. Podés tocar varias, o arrastrar un recuadro desde un espacio vacío para agarrar un grupo.',
      nota: 'La misma pieza aparece en cada talle: se nombran todas juntas.' },
    { ancla: 'nombre-pieza-input', accion: 'input',
      texto: 'Escribí el nombre de esa pieza. Ej: «Frente».' },
    { ancla: 'nombre-pieza-ok', accion: 'click',
      texto: 'Confirmá el nombre.',
      nota: 'Repetí lo mismo con el resto de las piezas hasta que no quede ninguna sin nombre.' },
  ],
};

// ── ÁREA 2 · AJUSTES DEL MOLDE ──────────────────────────────────────────────────────────────────
const AJUSTE_TELAS = {
  id: 'ajuste-telas',
  area: 'ajustes',
  titulo: 'Telas del molde',
  desc: 'Elegir qué telas se van a poder usar en cada pieza.',
  minutos: 4,
  pasos: [
    { ancla: 'ajuste-telas', ir: { ajuste: 'telas' }, accion: 'click',
      texto: 'Entrá a «Telas asignadas».' },
    { ancla: 'telas-variable', accion: 'ver',
      texto: 'Primero elegí la variable con la que vas a trabajar. El molde de al lado te muestra sólo sus piezas.' },
    { ancla: 'telas-tope', accion: 'ver',
      texto: 'Acá definís cuántas telas distintas puede combinar la prenda en un pedido.',
      nota: 'Ej: 2 = el operario podrá usar hasta 2 telas en esa prenda.' },
    { ancla: 'telas-mostrar', accion: 'click',
      texto: 'Tocá «Mostrar telas asignadas».' },
    { ancla: 'visor-molde', accion: 'ver',
      texto: 'Tocá en el molde las piezas que van a llevar una tela. Si no tocás ninguna, la tela va a TODAS.' },
    { ancla: 'telas-seleccionar', accion: 'click',
      texto: 'Ahora tocá «Seleccionar tela».' },
    { ancla: 'telas-modal-buscar', accion: 'ver',
      texto: 'Buscá la tela por nombre y tocá las que quieras habilitar.' },
    { ancla: 'telas-modal-asignar', accion: 'click',
      texto: 'Tocá «Asignar» y listo.' },
  ],
};

const AJUSTE_ETIQUETA = {
  id: 'ajuste-etiqueta',
  area: 'ajustes',
  titulo: 'Etiqueta de las piezas',
  desc: 'Qué dice el textito de cada pieza y dónde va.',
  minutos: 4,
  pasos: [
    { ancla: 'ajuste-etiqueta', ir: { ajuste: 'etiqueta' }, accion: 'click',
      texto: 'Entrá a «Etiqueta».' },
    { ancla: 'etq-activo', accion: 'ver',
      texto: 'Con esto prendés o apagás la etiqueta en toda la moldería.' },
    { ancla: 'etq-mostrar', accion: 'ver',
      texto: 'Elegí qué tiene que decir: el talle, el nombre de la pieza, el número.' },
    { ancla: 'visor-molde', accion: 'ver',
      texto: 'Tocá sobre la pieza, en el visor, para mover la etiqueta al lugar que quieras.',
      nota: 'Se acomoda sobre el borde de la pieza.' },
    { ancla: 'etq-guardar', accion: 'click',
      texto: 'Guardá los cambios.' },
  ],
};

const AJUSTE_BORDE = {
  id: 'ajuste-borde',
  area: 'ajustes',
  titulo: 'Borde de corte',
  desc: 'La línea que rodea cada pieza para guiar el corte.',
  minutos: 2,
  pasos: [
    { ancla: 'ajuste-borde', ir: { ajuste: 'borde' }, accion: 'click',
      texto: 'Entrá a «Borde de corte».' },
    { ancla: 'borde-activo', accion: 'click',
      texto: 'Prendé el borde si este molde lo lleva.' },
    { ancla: 'borde-tamano', accion: 'ver',
      texto: 'Poné el grosor en milímetros.' },
    { ancla: 'borde-color', accion: 'ver',
      texto: 'Y elegí el color con el que se va a imprimir.' },
    { ancla: 'borde-guardar', accion: 'click',
      texto: 'Guardá.' },
  ],
};

// ── ÁREA 3 · PEDIDO (el uso de todos los días) ─────────────────────────────────────────────────
const HACER_PEDIDO = {
  id: 'hacer-pedido',
  area: 'pedido',
  titulo: 'Armar una tizada',
  desc: 'El camino completo: molde, arte, planilla y generar.',
  minutos: 8,
  pasos: [
    { ancla: 'nav-pedidos', ir: { tab: 'pedidos', paso: 'moldes' }, accion: 'click',
      texto: 'Entrá a Pedidos.' },
    { ancla: 'pedido-moldes', accion: 'ver',
      texto: 'Elegí el molde (o los moldes) que vas a usar en esta tizada.',
      nota: 'Podés combinar varios en la misma tizada.' },
    { ancla: 'pedido-ir-arte', accion: 'click',
      texto: 'Seguí al paso del arte.' },
    { ancla: 'arte-cargar', accion: 'click',
      texto: 'Subí el arte (el diseño) de esta prenda.' },
    { ancla: 'arte-telas', accion: 'click',
      texto: 'Tocá «Ver telas de pieza» para decir en qué tela va cada pieza.',
      nota: 'Todas las piezas necesitan una tela para poder seguir.' },
    { ancla: 'arte-siguiente', accion: 'click',
      texto: 'Cuando esté todo, pasá a la planilla.' },
    { ancla: 'planilla-tabla', accion: 'ver',
      texto: 'Cargá una fila por prenda: talle, nombre, número… Se usa como una planilla de Excel.',
      nota: 'Tocás una celda y escribís. Arrastrando el cuadradito de la esquina copiás hacia abajo.' },
    { ancla: 'planilla-generar', accion: 'click',
      texto: 'Generá la tizada.' },
    { ancla: 'resultados-hojas', accion: 'ver',
      texto: '¡Listo! Acá tenés las hojas para imprimir y la ficha técnica.' },
  ],
};

// ── ÁREA 4 · CONFIGURACIÓN GENERAL ─────────────────────────────────────────────────────────────
const CFG_TELAS = {
  id: 'cfg-telas',
  area: 'config',
  titulo: 'Telas del sistema',
  desc: 'De dónde salen las telas y cómo se pone el ancho de impresión.',
  minutos: 3,
  pasos: [
    { ancla: 'nav-config', ir: { tab: 'config', sub: 'dashboard' }, accion: 'click',
      texto: 'Entrá a Configuración.' },
    { ancla: 'cfg-telas', accion: 'click',
      texto: 'Abrí «Telas».' },
    { ancla: 'telas-conexion', accion: 'ver',
      texto: 'Las telas vienen solas del sistema de stock. Acá ves si la conexión está andando.' },
    { ancla: 'telas-actualizar', accion: 'click',
      texto: 'Si cargaste telas nuevas en el stock, tocá acá para traerlas.' },
    { ancla: 'telas-lista', accion: 'ver',
      texto: 'La medida la informa el stock; vos ponés el ANCHO DE IMPRESIÓN, que es el que usa la tizada.',
      nota: 'Suele ser menor que el rollo, por los orillos.' },
  ],
};

export const GUIAS = [CREAR_MOLDE, NOMBRAR_PIEZAS, AJUSTE_TELAS, AJUSTE_ETIQUETA, AJUSTE_BORDE, HACER_PEDIDO, CFG_TELAS];

export const AREAS = [
  { id: 'moldes', titulo: 'Crear y preparar un molde', desc: 'Desde subir la moldería hasta dejarla lista', icono: 'productos' },
  { id: 'ajustes', titulo: 'Ajustes del molde', desc: 'Telas, etiqueta, borde y demás', icono: 'config' },
  { id: 'pedido', titulo: 'Armar una tizada', desc: 'El uso de todos los días', icono: 'pedidos' },
  { id: 'config', titulo: 'Configuración del sistema', desc: 'Telas, planillas, usuarios', icono: 'config' },
];

export const guiaPorId = (id) => GUIAS.find(g => g.id === id) || null;
