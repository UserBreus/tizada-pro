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
      texto: 'Abrí «Molderías»: acá viven todos los moldes.' },
    { ancla: 'molde-nuevo', ir: { tab: 'config', sub: 'productos' }, accion: 'click',
      texto: 'Tocá «Nueva Moldería».' },
    { ancla: 'molde-nombre', accion: 'input',
      texto: 'Escribí el nombre del molde. Ej: «Camiseta fútbol».',
      nota: 'Es el nombre con el que lo vas a reconocer después en el pedido.' },
    { ancla: 'molde-crear-ok', accion: 'click',
      texto: 'Tocá «Crear Molde».' },
    { ancla: 'molde-subir', accion: 'click',
      texto: 'Ahora subí el archivo de la moldería (.ai, .pdf o .dxf).',
      nota: 'Es el archivo con TODAS las piezas y todos los talles.' },
    { ancla: 'molde-como-exportar', accion: 'ver',
      texto: 'Si no sabés cómo sacar ese archivo de tu programa, acá está explicado.',
      nota: 'Sirve para Illustrator, Corel y los de moldería (Optitex, Gerber…).' },
    { ancla: 'visor-molde', accion: 'ver',
      texto: 'Listo: acá ves tu moldería. Cada pieza tiene su número.',
      nota: 'Rueda del mouse para acercar, clic derecho para moverla.' },
    { ancla: 'ajuste-variables', accion: 'ver',
      texto: 'El molde ya está cargado. El paso que sigue es ponerle nombre a las piezas, en «Variables».',
      nota: 'Está en la guía «Ponerle nombre a las piezas».' },
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
    { ancla: 'var-pasos', ir: { ajuste: 'variables' }, accion: 'ver',
      texto: 'Variables tiene 3 pasos. Ahora vas por el primero: «1. Nombrar».',
      nota: 'Los otros dos (Grupos y Modelos) van después, con las piezas ya nombradas.' },
    { ancla: 'visor-molde', accion: 'ver',
      texto: 'Tocá una pieza en el molde para elegirla. Para varias, arrastrá un recuadro desde un espacio vacío.',
      nota: 'Si elegís varias iguales, el sistema las numera solo: Frente 1, Frente 2…' },
    { ancla: 'nombre-pieza-input', accion: 'input',
      texto: 'Escribí el nombre de esa pieza. Ej: «Frente».' },
    { ancla: 'nombre-pieza-ok', accion: 'click',
      texto: 'Tocá «Nombrar» para aplicarlo.',
      nota: 'Repetí con el resto hasta que no quede ninguna pieza sin nombre.' },
    { ancla: 'nombres-guardar', accion: 'click',
      texto: 'Al terminar, tocá «Guardar nombres».' },
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
    { ancla: 'telas-variable', ir: { ajuste: 'telas' }, accion: 'ver',
      texto: 'Primero elegí la variable con la que vas a trabajar. El molde de al lado te muestra sólo sus piezas.' },
    { ancla: 'telas-tope', ir: { ajuste: 'telas' }, accion: 'ver',
      texto: 'Acá definís cuántas telas distintas puede combinar la prenda en un pedido.',
      nota: 'Ej: 2 = el operario podrá usar hasta 2 telas en esa prenda.' },
    { ancla: 'telas-mostrar', ir: { ajuste: 'telas' }, accion: 'click',
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
    { ancla: 'etq-activo', ir: { ajuste: 'etiqueta' }, accion: 'ver',
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
    { ancla: 'borde-activo', ir: { ajuste: 'borde' }, accion: 'click',
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
  desc: 'El camino completo: diseño, variables, arte, planilla y enviar.',
  minutos: 8,
  // ORDEN REAL del sistema (verificado en pantalla): primero se CREA EL DISEÑO y recién después se
  // le eligen las VARIABLES que lo componen. No se «elige un molde»: se eligen variables, que ya
  // traen su molde detrás.
  pasos: [
    { ancla: 'nav-pedidos', ir: { tab: 'pedidos', paso: 'moldes' }, accion: 'click',
      texto: 'Entrá a Pedidos.' },
    { ancla: 'pedido-diseno-input', ir: { tab: 'pedidos', paso: 'moldes' }, accion: 'input',
      texto: 'Empezá por el DISEÑO: escribí acá cómo se llama.',
      nota: 'Es el estampado de la prenda. Ej: «River titular». Un pedido puede llevar varios.' },
    { ancla: 'pedido-diseno-agregar', ir: { tab: 'pedidos', paso: 'moldes' }, accion: 'click',
      texto: 'Agregalo con este botón (o con Enter).' },
    { ancla: 'pedido-diseno-chips', ir: { tab: 'pedidos', paso: 'moldes' }, accion: 'ver',
      texto: 'Ahí aparece tu diseño. Si cargás varios, tocá uno para trabajar sobre ese.',
      nota: 'El número al lado dice cuántas variables le asignaste.' },
    { ancla: 'pedido-tabs', ir: { tab: 'pedidos', paso: 'moldes' }, accion: 'ver',
      texto: 'Acá elegís de dónde salen las prendas: del «Catálogo» compartido o de «Mis artículos» (los que subiste vos).' },
    { ancla: 'pedido-variables', ir: { tab: 'pedidos', paso: 'moldes' }, accion: 'ver',
      texto: 'Ahora tocá las VARIABLES que van en ese diseño (por ejemplo: musculosa, manga corta).',
      nota: 'No se elige el molde: se eligen sus variables, que ya saben a qué molde pertenecen. Cada diseño necesita al menos una.' },
    { ancla: 'pedido-ir-arte', ir: { tab: 'pedidos', paso: 'moldes' }, accion: 'click',
      texto: 'Cuando cada diseño tenga su variable, tocá «Cargar el arte».',
      nota: 'Si está apagado, es que falta elegir variable en algún diseño: te lo avisa al lado.' },
    { ancla: 'arte-cargar', accion: 'click',
      texto: 'Subí el archivo del arte (.ai o .pdf) de esta variable.' },
    { ancla: 'visor-molde', accion: 'ver',
      texto: 'Revisá que cada pieza tenga su parte del diseño. Si algo no quedó bien, arrastrá el diseño hasta la pieza.',
      nota: 'Arriba podés cambiar de diseño y de variable: hay que cargar el arte de todas.' },
    { ancla: 'arte-telas', accion: 'click',
      texto: 'Tocá «Ver telas de pieza» para decir en qué tela va cada una.',
      nota: 'Todas las piezas necesitan tela: si falta alguna, no te deja seguir.' },
    { ancla: 'arte-siguiente', accion: 'click',
      texto: 'Con el arte y las telas listas, pasá a la planilla.' },
    { ancla: 'planilla-tabla', accion: 'ver',
      texto: 'Cargá una fila por prenda: talle, nombre, número… Funciona como una planilla de Excel.',
      nota: 'Tocás una celda y escribís. Con el cuadradito de la esquina copiás hacia abajo arrastrando.' },
    { ancla: 'planilla-enviar', accion: 'click',
      texto: 'Tocá «Enviar» y el sistema arma la tizada.',
      nota: 'Si está apagado, arriba te dice qué falta: filas, un valor inválido o el arte de algún molde.' },
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
    { ancla: 'cfg-telas', ir: { tab: 'config', sub: 'dashboard' }, accion: 'click',
      texto: 'Abrí «Telas».' },
    { ancla: 'telas-conexion', ir: { tab: 'config', sub: 'telas' }, accion: 'ver',
      texto: 'Las telas vienen solas del sistema de stock. Acá ves si la conexión está andando.' },
    { ancla: 'telas-actualizar', accion: 'click',
      texto: 'Si cargaste telas nuevas en el stock, tocá acá para traerlas.' },
    { ancla: 'telas-lista', accion: 'ver',
      texto: 'La medida la informa el stock; vos ponés el ANCHO DE IMPRESIÓN, que es el que usa la tizada.',
      nota: 'Suele ser menor que el rollo, por los orillos.' },
  ],
};


const VARIABLES_GRUPOS = {
  id: 'variables-grupos',
  area: 'moldes',
  titulo: 'Armar las variables del molde',
  desc: 'Decirle al sistema qué combinaciones de piezas se pueden pedir.',
  minutos: 7,
  pasos: [
    { ancla: 'ajuste-variables', ir: { ajuste: 'variables' }, accion: 'click',
      texto: 'Entrá a «Variables».' },
    { ancla: 'var-pasos', ir: { ajuste: 'variables' }, accion: 'ver',
      texto: 'Con las piezas ya nombradas, ahora vas por el paso «2. Grupos».',
      nota: 'Un GRUPO junta decisiones parecidas (ej: «Tipo de manga»). Adentro van las VARIABLES.' },
    { ancla: 'grupo-nombre', accion: 'input',
      texto: 'Ponele nombre al grupo. Ej: «Tipo de manga».',
      nota: 'Es la pregunta que se le hace a la prenda, no la respuesta.' },
    { ancla: 'var-nombre', accion: 'input',
      texto: 'Ahora la variable: escribí una de las respuestas posibles. Ej: «Manga corta».' },
    { ancla: 'var-elegir-piezas', accion: 'click',
      texto: 'Tocá «+ Elegir piezas».' },
    { ancla: 'visor-molde', accion: 'ver',
      texto: 'Tocá en el molde TODAS las piezas que lleva esa variable: frente, espalda, esa manga…',
      nota: 'Sólo esas piezas se van a imprimir cuando alguien pida esta variable.' },
    { ancla: 'var-listo', accion: 'click',
      texto: 'Tocá «Listo» para cerrar esa variable.',
      nota: 'Repetí con las demás respuestas del grupo (manga larga, musculosa…).' },
  ],
};

const AJUSTE_PLANTILLA = {
  id: 'ajuste-plantilla',
  area: 'ajustes',
  titulo: 'Plantilla: medidas y arte',
  desc: 'Decirle al sistema qué parte del arte va en cada pieza.',
  minutos: 5,
  pasos: [
    { ancla: 'ajuste-diseno', ir: { ajuste: 'diseno' }, accion: 'click',
      texto: 'Entrá a «Plantilla».' },
    { ancla: 'diseno-capas', ir: { ajuste: 'diseno' }, accion: 'click',
      texto: 'Antes que nada, mirá qué tiene que traer el archivo del arte.',
      nota: 'El .ai necesita una capa por cosa: el diseño, las guías con el nombre de cada pieza…' },
    { ancla: 'diseno-mapear', ir: { ajuste: 'diseno' }, accion: 'click',
      texto: 'Tocá «Mapear diseño al molde» para pasar del modo medidas al modo arte.' },
    { ancla: 'visor-molde', accion: 'ver',
      texto: 'Acá emparejás cada mesa del arte con su pieza del molde.',
      nota: 'Si en el .ai cada mesa tiene escrito el nombre de la pieza, el sistema lo hace solo.' },
    { ancla: 'diseno-guardar', accion: 'click',
      texto: 'Guardá el mapeo.',
      nota: 'Se guarda por variable: repetilo con cada una que tenga arte propio.' },
  ],
};

const AJUSTE_PLANILLA_MOLDE = {
  id: 'ajuste-planilla-molde',
  area: 'ajustes',
  titulo: 'Planilla del molde',
  desc: 'Qué columnas se cargan cuando se pide este molde.',
  minutos: 3,
  pasos: [
    { ancla: 'ajuste-planilla', ir: { ajuste: 'planilla' }, accion: 'click',
      texto: 'Entrá a «Planilla».' },
    { ancla: 'mplanilla-elegir', ir: { ajuste: 'planilla' }, accion: 'click',
      texto: 'Elegí la planilla de columnas que usa este molde.',
      nota: 'Las planillas se arman en Configuración › Planillas. Acá sólo se elige una.' },
    { ancla: 'mplanilla-guardar', accion: 'click',
      texto: 'Guardá la configuración de este molde.',
      nota: 'En el pedido van a aparecer sólo las columnas que este molde use de verdad.' },
  ],
};

const AJUSTE_NESTING = {
  id: 'ajuste-nesting',
  area: 'ajustes',
  titulo: 'Cómo se acomodan las piezas',
  desc: 'La separación y el giro con los que se arma la tizada.',
  minutos: 2,
  pasos: [
    { ancla: 'ajuste-nestingsel', ir: { ajuste: 'nestingsel' }, accion: 'click',
      texto: 'Entrá a «Nesting».' },
    { ancla: 'nsel-elegir', ir: { ajuste: 'nestingsel' }, accion: 'input',
      texto: 'Elegí con qué acomodo se van a tizar las piezas de este molde.',
      nota: 'Cada opción trae su separación entre piezas, su margen y si se permite girarlas.' },
    { ancla: 'nsel-grupos', accion: 'ver',
      texto: 'Si varias molderías se tizan juntas (ej: camiseta + short), eso se arma en «grupos de tizada».' },
  ],
};

const AJUSTE_NOMBRES = {
  id: 'ajuste-nombres',
  area: 'ajustes',
  titulo: 'Nombres propios del molde',
  desc: 'Cómo querés que el sistema llame al talle y a la prenda.',
  minutos: 2,
  pasos: [
    { ancla: 'ajuste-terminologia', ir: { ajuste: 'terminologia' }, accion: 'click',
      texto: 'Entrá a «Nombres».' },
    { ancla: 'term-variante', ir: { ajuste: 'terminologia' }, accion: 'input',
      texto: 'Escribí cómo llamás al talle en este molde. Ej: «Talle», «Medida».',
      nota: 'Es sólo el nombre que se muestra: cambia los carteles, no el funcionamiento.' },
    { ancla: 'term-molde', accion: 'input',
      texto: 'Y acá el nombre de la prenda, como lo vas a reconocer en el pedido.' },
    { ancla: 'term-guardar', accion: 'click',
      texto: 'Guardá los nombres.' },
  ],
};

const PLANILLA_PEDIDO = {
  id: 'planilla-pedido',
  area: 'pedido',
  titulo: 'Cargar la planilla',
  desc: 'Cargar las prendas del pedido como en una planilla de Excel.',
  minutos: 4,
  pasos: [
    { ancla: 'planilla-tabla', ir: { tab: 'pedidos', paso: 'planilla' }, accion: 'ver',
      texto: 'Una fila = una prenda. Un clic elige la celda; doble clic (o Enter) la abre para escribir.',
      nota: 'También podés empezar a escribir directo: la primera letra ya entra.' },
    { ancla: 'planilla-tabla', accion: 'ver',
      texto: 'Con el cuadradito de la esquina de la celda copiás hacia abajo o al costado arrastrando.',
      nota: 'En números hace la secuencia (1, 2, 3…); en talle y diseño copia el mismo valor.' },
    { ancla: 'planilla-agregar', accion: 'click',
      texto: 'Si te faltan filas, poné cuántas y tocá «Agregar».' },
    { ancla: 'planilla-csv', accion: 'ver',
      texto: 'Si el pedido ya te llegó en Excel, podés importarlo como CSV en vez de tipearlo.',
      nota: 'Los valores que no existan en el molde quedan vacíos, no inventa nada.' },
    { ancla: 'planilla-enviar', accion: 'click',
      texto: 'Cuando esté completa, tocá «Enviar».',
      nota: 'Si está apagado, arriba dice qué falta.' },
  ],
};

const CFG_COLUMNAS = {
  id: 'cfg-columnas',
  area: 'config',
  titulo: 'Armar una planilla de columnas',
  desc: 'Definir qué datos se le piden al operario en el pedido.',
  minutos: 5,
  pasos: [
    { ancla: 'nav-config', ir: { tab: 'config', sub: 'dashboard' }, accion: 'click',
      texto: 'Entrá a Configuración.' },
    { ancla: 'cfg-columnas', ir: { tab: 'config', sub: 'dashboard' }, accion: 'click',
      texto: 'Abrí «Planillas».',
      nota: 'Una planilla es el juego de columnas que se carga al hacer un pedido.' },
    { ancla: 'col-nueva', ir: { tab: 'config', sub: 'columnas' }, accion: 'click',
      texto: 'Tocá «Nueva Planilla».' },
    { ancla: 'col-guardar', accion: 'ver',
      texto: 'Agregá las columnas que necesites (talle, nombre, número, color…) y ordenálas arrastrando.',
      nota: 'Cada columna usa una REGLA, que dice si es texto libre, una lista de opciones o un toggle.' },
    { ancla: 'col-guardar', accion: 'click',
      texto: 'Guardá la planilla.',
      nota: 'Después se le asigna a cada molde desde su ajuste «Planilla».' },
  ],
};

const CFG_REGLAS = {
  id: 'cfg-reglas',
  area: 'config',
  titulo: 'Reglas de las columnas',
  desc: 'Qué se puede escribir en cada columna y qué efecto tiene.',
  minutos: 4,
  pasos: [
    { ancla: 'cfg-reglas', ir: { tab: 'config', sub: 'dashboard' }, accion: 'click',
      texto: 'Abrí «Reglas de planilla · Capas».' },
    { ancla: 'regla-nueva', ir: { tab: 'config', sub: 'reglas' }, accion: 'click',
      texto: 'Tocá «Nueva Regla».' },
    { ancla: 'regla-nombre', accion: 'input',
      texto: 'Ponele nombre. Ej: «Color», «Equipo», «Capucha».' },
    { ancla: 'regla-guardar', accion: 'ver',
      texto: 'Elegí el tipo: texto libre, lista de opciones o toggle (sí/no).',
      nota: 'El toggle puede CAMBIAR LAS PIEZAS: ej. «capucha = sí» agrega las piezas de la capucha.' },
    { ancla: 'regla-guardar', accion: 'click',
      texto: 'Guardá la regla.',
      nota: 'Ya la podés usar en cualquier columna de cualquier planilla.' },
  ],
};

const CFG_NESTING = {
  id: 'cfg-nesting',
  area: 'config',
  titulo: 'Reglas de nesting',
  desc: 'Cuánta separación deja la tizada y si puede girar las piezas.',
  minutos: 3,
  pasos: [
    { ancla: 'cfg-nesting', ir: { tab: 'config', sub: 'dashboard' }, accion: 'click',
      texto: 'Abrí «Reglas de Nesting».' },
    { ancla: 'nesting-nuevo', ir: { tab: 'config', sub: 'nesting' }, accion: 'click',
      texto: 'Tocá «Nuevo Nesting».' },
    { ancla: 'nesting-nombre', accion: 'input',
      texto: 'Ponele un nombre que se entienda. Ej: «Apretado», «Sin giro».' },
    { ancla: 'nesting-guardar', accion: 'ver',
      texto: 'Definí la separación entre piezas, el margen de la hoja y si se pueden girar.',
      nota: 'Menos separación = menos tela, pero deja menos aire para cortar.' },
    { ancla: 'nesting-guardar', accion: 'click',
      texto: 'Guardá.',
      nota: 'Después se le asigna a cada molde desde su ajuste «Nesting».' },
  ],
};

const CFG_FUENTES = {
  id: 'cfg-fuentes',
  area: 'config',
  titulo: 'Fuentes para estampar',
  desc: 'Subir las tipografías con las que salen los nombres y números.',
  minutos: 2,
  pasos: [
    { ancla: 'cfg-fuentes', ir: { tab: 'config', sub: 'dashboard' }, accion: 'click',
      texto: 'Abrí «Catálogo de Fuentes».' },
    { ancla: 'fuentes-subir', ir: { tab: 'config', sub: 'fuentes' }, accion: 'click',
      texto: 'Subí la tipografía (.ttf o .otf).',
      nota: 'Es el archivo de la fuente, el mismo que instalarías en la computadora.' },
    { ancla: 'fuentes-probar', accion: 'input',
      texto: 'Escribí un nombre o un número acá para ver cómo queda en todas las fuentes.',
      nota: 'Sirve para elegir sin tener que generar una tizada de prueba.' },
  ],
};

const CFG_PERFIL = {
  id: 'cfg-perfil',
  area: 'config',
  titulo: 'Perfil de color',
  desc: 'Con qué perfil CMYK sale la impresión.',
  minutos: 2,
  pasos: [
    { ancla: 'cfg-perfil', ir: { tab: 'config', sub: 'dashboard' }, accion: 'click',
      texto: 'Abrí «Perfil de color».' },
    { ancla: 'perfil-card', ir: { tab: 'config', sub: 'perfil' }, accion: 'ver',
      texto: 'Estos son los perfiles instalados en la máquina. El marcado es el que se usa por defecto.',
      nota: 'Si no sabés cuál poner, dejá el que viene: cambiarlo mueve los colores de todo lo que imprimas.' },
    { ancla: 'perfil-card', accion: 'ver',
      texto: 'Cuando cargás un arte que ya trae su propio perfil incrustado, el sistema te avisa y respeta ese.' },
  ],
};

export const GUIAS = [
  CREAR_MOLDE, NOMBRAR_PIEZAS, VARIABLES_GRUPOS,
  AJUSTE_PLANTILLA, AJUSTE_TELAS, AJUSTE_ETIQUETA, AJUSTE_BORDE, AJUSTE_PLANILLA_MOLDE, AJUSTE_NESTING, AJUSTE_NOMBRES,
  HACER_PEDIDO, PLANILLA_PEDIDO,
  CFG_TELAS, CFG_COLUMNAS, CFG_REGLAS, CFG_NESTING, CFG_FUENTES, CFG_PERFIL,
];

export const AREAS = [
  { id: 'moldes', titulo: 'Crear y preparar un molde', desc: 'Desde subir la moldería hasta dejarla lista', icono: 'productos' },
  { id: 'ajustes', titulo: 'Ajustes del molde', desc: 'Telas, etiqueta, borde y demás', icono: 'config' },
  { id: 'pedido', titulo: 'Armar una tizada', desc: 'El uso de todos los días', icono: 'pedidos' },
  { id: 'config', titulo: 'Configuración del sistema', desc: 'Telas, planillas, usuarios', icono: 'config' },
];

export const guiaPorId = (id) => GUIAS.find(g => g.id === id) || null;
