/**
 * GUION DE AYUDA — el CONTENIDO del tutorial, separado del motor (`tutor.jsx`).
 *
 * HAY UNA SOLA GUÍA, A PROPÓSITO (decisión del usuario, 2026-07-28): **armar una tizada**, que es
 * el trabajo de todos los días. Las otras 26 guías se sacaron: sumaban pantallas de configuración
 * que el operario no toca y hacían que la ayuda pareciera un manual en vez de un acompañamiento.
 *
 * Los pasos están calcados del video «Como cargar un pedido.mp4» que grabó el usuario: mismo
 * orden, mismos botones, mismas palabras que se ven en pantalla. Si el flujo del pedido cambia,
 * ESTE archivo es lo que hay que corregir (y el video, la referencia de qué es "lo correcto").
 *
 * ── UN PASO ────────────────────────────────────────────────────────────────────────────────────
 *   ancla    'id' del elemento a iluminar. En el JSX se marca con `data-tour="id"`.
 *            Si el elemento no está en pantalla todavía, el motor espera a que aparezca.
 *   texto    qué tiene que hacer el usuario, en criollo y en imperativo («Tocá acá…»).
 *   accion   cómo se pasa al paso siguiente:
 *              'click'  cuando toca el elemento         (lo más común)
 *              'input'  cuando escribe algo adentro
 *              'ver'    es sólo para mirar → avanza solo a los pocos segundos
 *              'gesto'  se trabaja EN EL VISOR (elegir piezas, arrastrar): NO avanza por tiempo,
 *                       avanza cuando `hecho` dice que el gesto ocurrió de verdad
 *   ir       (opcional) a qué pantalla hay que llevarlo antes del paso: {tab, sub, paso, ajuste}
 *   nota     (opcional) aclaración corta que va abajo del texto, en gris.
 *   tambien  (opcional) otras anclas que valen lo mismo (el campo que confirma con Enter vale
 *            igual que el botón que hace esa confirmación).
 *   hecho(E, E0)  (opcional) — EL PASO YA ESTÁ CUMPLIDO. `E` = estado real de la app AHORA,
 *            `E0` = el mismo estado en el momento en que arrancó el paso (para poder pedir
 *            «que AUMENTE», no «que sea mayor a cero»). Ver la forma de `E` abajo.
 *            ⚠️ Si un paso declara `hecho`, **ES LA ÚNICA forma de avanzar** (más el escape
 *            manual). Eso es a propósito: tocar un botón NO es lo mismo que que la acción SALGA
 *            BIEN — si el POST falla, el estado no cambia y el tutorial no avanza.
 *            Si `hecho` ya da true al empezar el paso, el paso se SALTEA (no se pide lo hecho).
 *
 * ── EL ESTADO `E` (lo arma `App.jsx`, buscar `ayudaEstado`) ────────────────────────────────────
 *   E.cargado (¿ya llegaron los datos?) · E.nMoldes · E.tab/sub/paso/ajuste
 *   E.pedido  {nDisenos, sinVariable, artesTotal, artesCargadas, telasFaltan, nFilas,
 *              hayResultados, editorAbierto, nEditables}
 *   Si hiciera falta mirar otra cosa (el molde, la configuración), se agrega ahí y se documenta acá.
 *
 * REGLA: el usuario trabaja sobre SUS datos reales (decisión del usuario), así que ningún paso
 * borra ni cambia nada por su cuenta: la acción siempre la hace la persona.
 */

const ARMAR_TIZADA = {
  id: 'hacer-pedido',
  titulo: 'Armar una tizada',
  desc: 'El camino completo: diseño, prenda, arte, telas, planilla y las hojas para imprimir.',
  minutos: 6,
  pasos: [
    // ── 1 · DISEÑOS ────────────────────────────────────────────────────────────────────────────
    { ancla: 'nav-pedidos', ir: { tab: 'pedidos', paso: 'moldes' }, accion: 'click',
      texto: 'Entrá a Pedidos.' },
    { ancla: 'pedido-diseno-input', ir: { tab: 'pedidos', paso: 'moldes' }, accion: 'input',
      texto: 'Empezá por el DISEÑO: escribí acá cómo se llama.',
      nota: 'Es el estampado de la prenda. Un pedido puede llevar varios diseños.' },
    { ancla: 'pedido-diseno-agregar', ir: { tab: 'pedidos', paso: 'moldes' }, accion: 'click',
      // Si ya lo confirmó con Enter en el campo, este paso está hecho: el motor lo saltea.
      tambien: ['pedido-diseno-input'],
      texto: 'Agregalo: tocá «+ Diseño» o apretá Enter en el campo.',
      hecho: (E, E0) => E.pedido.nDisenos > E0.pedido.nDisenos },
    { ancla: 'pedido-diseno-chips', ir: { tab: 'pedidos', paso: 'moldes' }, accion: 'ver',
      texto: 'Ahí queda tu diseño. Si cargás varios, tocá uno para trabajar sobre ese.',
      nota: 'El número al lado dice cuántas prendas le asignaste.' },
    { ancla: 'pedido-variables', ir: { tab: 'pedidos', paso: 'moldes' }, accion: 'gesto',
      texto: 'Ahora tocá la prenda que lleva ese diseño. Queda marcada con un ✓.',
      nota: 'En «Catálogo» están las compartidas; en «Mis artículos», los moldes que subiste vos.',
      hecho: (E) => E.pedido.nDisenos > 0 && E.pedido.sinVariable === 0 },
    { ancla: 'pedido-ir-arte', ir: { tab: 'pedidos', paso: 'moldes' }, accion: 'click',
      texto: 'Tocá «Cargar el arte».',
      nota: 'Si está apagado, es que falta elegir la prenda de algún diseño: te lo avisa al lado.' },

    // ── 2 · ARTE ───────────────────────────────────────────────────────────────────────────────
    { ancla: 'arte-cargar', accion: 'click',
      texto: 'Tocá «Cargar arte» y elegí el archivo del diseño (.ai o .pdf).',
      // No alcanza con abrir el explorador: el arte tiene que quedar procesado.
      hecho: (E, E0) => E.pedido.artesCargadas > E0.pedido.artesCargadas },
    { ancla: 'visor-molde', accion: 'ver',
      texto: 'El sistema le pone el diseño a cada talle. Esperá a que termine esa barra: se hace una sola vez.',
      nota: 'Después cambiar de talle es instantáneo.' },
    { ancla: 'visor-molde', accion: 'ver',
      texto: 'Fijate que cada pieza tenga su parte del diseño. Si alguna quedó vacía, arrastrale su diseño desde la lista de la derecha.',
      nota: 'También podés tocar la pieza en el molde y después su diseño. Se guarda solo.' },
    { ancla: 'editar-diseno', accion: 'ver',
      texto: 'Si necesitás mover, agrandar o pintar algo del diseño (un escudo, un logo), entrás por «Editar diseño».',
      nota: 'Ahí elegís si el cambio va a todo el rango de talles o sólo al que estás viendo. No es obligatorio.' },

    // ── 3 · TELAS ──────────────────────────────────────────────────────────────────────────────
    { ancla: 'arte-telas', accion: 'click',
      texto: 'Tocá «Ver telas de pieza»: hay que decir en qué tela va cada pieza.' },
    { ancla: 'telas-panel', accion: 'gesto',
      texto: 'Son tres pasos: 1) elegí la tela de la lista · 2) tocá las piezas en el molde · 3) «Asignar».',
      nota: 'Si no tocás ninguna pieza, el botón dice «Asignar a todas» y la tela va a todas.',
      hecho: (E) => E.pedido.telasFaltan === 0 },
    { ancla: 'arte-siguiente', accion: 'click',
      texto: 'Cuando diga «Todas las piezas tienen tela», tocá «A la planilla».',
      nota: 'Si falta alguna pieza sin tela, el botón queda apagado y te dice cuántas son.' },

    // ── 4 · PLANILLA ───────────────────────────────────────────────────────────────────────────
    { ancla: 'planilla-tabla', accion: 'ver',
      texto: 'Una fila = una prenda. Cargá el talle, y el nombre y el número si la prenda los lleva.',
      nota: 'Un clic elige la celda; escribís directo. En Talle y Diseño se abre la lista de opciones.' },
    { ancla: 'planilla-tabla', accion: 'ver',
      texto: 'Con el cuadradito de la esquina de la celda copiás hacia abajo arrastrando.',
      nota: 'En los números hace la secuencia (1, 2, 3…); en talle y diseño repite el mismo valor.' },
    { ancla: 'planilla-agregar', accion: 'ver',
      texto: 'Si te faltan filas, poné cuántas y tocá «Agregar Fila».' },
    { ancla: 'planilla-csv', accion: 'ver',
      texto: 'Si el pedido ya te llegó en Excel, lo podés importar como CSV en vez de tipearlo.',
      nota: 'Lo que no exista en el molde queda vacío: no inventa datos.' },
    { ancla: 'planilla-enviar', accion: 'click',
      texto: 'Cuando esté completa, tocá «Enviar».',
      nota: 'Si está apagado, arriba dice qué falta: filas, un valor inválido o el arte de algún molde.' },

    // ── 5 · TIZADAS ────────────────────────────────────────────────────────────────────────────
    { ancla: 'resultados-mesas', accion: 'ver',
      texto: 'Se está armando la tizada. No cierres la ventana: te va mostrando en qué va.',
      nota: 'Cuando termina, aparecen las mesas listas para imprimir.' },
    { ancla: 'resultados-mesas', accion: 'ver',
      texto: 'Acá tenés cada mesa. Rueda del mouse para acercar y clic DERECHO para moverte.',
      nota: 'Si el pedido usa más de una tela, arriba hay una pestaña por tela.' },
    { ancla: 'resultados-descargar', accion: 'ver',
      texto: 'Con «Descargar todo» bajás cada mesa como un archivo aparte, con su nombre.' },
    { ancla: 'resultados-ficha', accion: 'ver',
      texto: 'Y en «Ficha técnica» tenés la hoja para el taller: la tabla de talles y el molde guía con la tela de cada pieza.',
      nota: 'Se puede descargar o imprimir directo.' },
  ],
};


/* ═══════════════════════════════════════════════════════════════════════════════════════════════
 * RECORRIDOS EXPLICATIVOS — «para qué sirve cada cosa»
 *
 * OJO, NO SON TUTORIALES: acá NO se le pide a la persona que haga nada. Sólo se recorre la
 * pantalla contando para qué sirve cada control. Por eso TODOS los pasos son `accion: 'ver'`
 * (globo violeta «PARA QUE SEPAS», avanza solo) y ninguno declara `hecho`.
 *   · el ÚNICO paso a paso de verdad es «Armar una tizada» (arriba), que es el trabajo diario;
 *   · para llegar a la pantalla el motor sí marca los botones del camino (los puentes ámbar).
 * Si mañana uno de estos tiene que pedir una acción, se le cambia la `accion` y se le pone `hecho`.
 * ═══════════════════════════════════════════════════════════════════════════════════════════════ */

const R = (id, area, titulo, desc, minutos, pasos) => ({ id, area, titulo, desc, minutos, explica: true, pasos });

// ── ÁREA · LA MOLDERÍA Y SUS AJUSTES ───────────────────────────────────────────────────────────
const EX_MOLDERIA = R('ex-molderia', 'molde', 'Moldería', 'Dónde vive el molde y cómo se prepara.', 3, [
  { ancla: 'ajuste-molderia', ir: { tab: 'config', sub: 'productos', molde: 'abierto', ajuste: 'molderia' }, accion: 'ver',
    texto: 'Esta es la pantalla del MOLDE: el archivo con todas las piezas y todos los talles.',
    nota: 'Todo lo demás del sistema se apoya en lo que definas acá.' },
  { ancla: 'molde-subir', accion: 'ver',
    texto: 'Acá se sube o se reemplaza el archivo del molde (.ai, .pdf o .dxf).',
    nota: 'Si lo volvés a subir, los nombres de pieza que ya pusiste se transfieren solos.' },
  { ancla: 'molde-guia', accion: 'ver',
    texto: 'El TALLE DE GUÍA es el talle de referencia: sobre él se nombran las piezas y desde él se copian a los demás.',
    nota: 'Conviene uno del medio de la curva (M, 38…).' },
  { ancla: 'variantes-panel', accion: 'ver',
    texto: 'Acá se definen los TALLES. Si el molde vino sin ellos, este panel se pone naranja: hasta resolverlo el molde no se puede usar.',
    nota: 'Hay dos casos: que cada talle venga en su capa, o que venga todo junto en una sola.' },
  { ancla: 'agrupar-activar', accion: 'ver',
    texto: '«Agrupar piezas» es decir cuál es la MISMA pieza en cada talle: el Frente de la S, el de la M, el de la L…',
    nota: 'Sin eso el sistema no sabe que son la misma y la tizada sale mal.' },
  { ancla: 'visor-molde', accion: 'ver',
    texto: 'El visor muestra el molde en medidas reales. Rueda del mouse para acercar, clic derecho para moverte.',
    nota: 'Es el mismo visor de casi todas las pantallas: cambia lo que pasa al tocar una pieza.' },
]);

const EX_VARIABLES = R('ex-variables', 'molde', 'Variables', 'Qué es una variable y para qué sirven los grupos.', 4, [
  { ancla: 'ajuste-variables', ir: { tab: 'config', sub: 'productos', molde: 'abierto', ajuste: 'variables' }, accion: 'ver',
    texto: 'Acá se le pone NOMBRE a cada pieza y se arman las VARIABLES del molde.',
    nota: 'Una variable es una combinación de piezas: «manga corta», «musculosa», «con capucha».' },
  { ancla: 'var-pasos', accion: 'ver',
    texto: 'Son 2 pasos: 1) Nombrar las piezas · 2) Grupos y variables.',
    nota: 'Van en ese orden: sin nombres no se pueden armar variables.' },
  { ancla: 'nombre-pieza-input', accion: 'ver',
    texto: 'Paso 1: se eligen piezas en el visor y se les escribe qué son («Frente», «Manga»).',
    nota: 'Si elegís varias iguales, se numeran solas: Frente 1, Frente 2…' },
  { ancla: 'var-pasos', accion: 'ver',
    texto: 'Paso 2: un GRUPO es la pregunta («Tipo de manga») y las VARIABLES son las respuestas («corta», «larga»).',
    nota: 'Cada variable guarda qué piezas lleva: eso es lo que se imprime cuando alguien la pide.' },
  { ancla: 'ajuste-variables', accion: 'ver',
    texto: 'Y «piezas que van juntas» es para las que nunca viajan solas: una manga y su vivo, por ejemplo.',
    nota: 'Si entra una, entra la otra.' },
]);

const EX_PLANTILLA = R('ex-plantilla', 'molde', 'Plantilla (medidas y arte)', 'Cómo se escala el diseño y cómo se empareja con las piezas.', 4, [
  { ancla: 'ajuste-diseno', ir: { tab: 'config', sub: 'productos', molde: 'abierto', ajuste: 'diseno' }, accion: 'ver',
    texto: 'Esta pantalla define DOS cosas: qué tamaño tiene el diseño sobre cada pieza, y qué parte del arte va en cada una.' },
  { ancla: 'ajuste-diseno', accion: 'ver',
    texto: 'La «dimensión de referencia» dice qué manda: el alto o el ancho. El sistema calcula la otra para que cubra todos los talles sin huecos.' },
  { ancla: 'ajuste-diseno', accion: 'ver',
    texto: 'Y «cómo se adapta»: un diseño para todos los talles, uno por rango, o uno por talle.',
    nota: 'Cuantos más diseños distintos, más trabajo para el diseñador — pero mejor calce.' },
  { ancla: 'diseno-capas', accion: 'ver',
    texto: 'Acá está la lista de capas que tiene que traer el archivo .ai del diseño.',
    nota: 'El diseñador las copia de acá tal cual: los nombres tienen que coincidir.' },
  { ancla: 'diseno-mapear', accion: 'ver',
    texto: '«Mapear diseño al molde» es emparejar cada mesa del arte con su pieza.',
    nota: 'Si en el .ai cada mesa dice el nombre de la pieza, el sistema lo hace solo. Se guarda por variable.' },
]);

const EX_PLANILLA_MOLDE = R('ex-planilla-molde', 'molde', 'Planilla del molde', 'Qué datos se piden cuando se pide este molde.', 2, [
  { ancla: 'ajuste-planilla', ir: { tab: 'config', sub: 'productos', molde: 'abierto', ajuste: 'planilla' }, accion: 'ver',
    texto: 'Acá se elige QUÉ COLUMNAS se cargan en el pedido cuando alguien pide este molde.',
    nota: 'Las planillas se arman en Configuración › Planillas; acá sólo se elige una.' },
  { ancla: 'mplanilla-elegir', accion: 'ver',
    texto: 'Un molde que no lleva número, por ejemplo, no tiene por qué mostrar esa columna.',
    nota: 'En el pedido aparecen sólo las columnas que los moldes elegidos usan de verdad.' },
]);

const EX_NESTING_MOLDE = R('ex-nesting-molde', 'molde', 'Nesting del molde', 'Con qué separación y giro se acomodan sus piezas.', 2, [
  { ancla: 'ajuste-nestingsel', ir: { tab: 'config', sub: 'productos', molde: 'abierto', ajuste: 'nestingsel' }, accion: 'ver',
    texto: 'El NESTING es cómo se acomodan las piezas en la tela: cuánta separación dejan y si se pueden girar.',
    nota: 'Menos separación = menos tela, pero deja menos aire para cortar.' },
  { ancla: 'nsel-elegir', accion: 'ver',
    texto: 'Acá se elige cuál de los acomodos usa este molde. Se arman en Configuración › Reglas de Nesting.' },
  { ancla: 'nsel-grupos', accion: 'ver',
    texto: 'Y un GRUPO DE TIZADA es cuando dos molderías se arman juntas en la misma mesa (camiseta + short).',
    nota: 'Un molde que no está en ningún grupo se arma en su propia tizada.' },
]);

const EX_TELAS_MOLDE = R('ex-telas-molde', 'molde', 'Telas asignadas', 'Qué telas puede usar este molde y en qué piezas.', 3, [
  { ancla: 'ajuste-telas', ir: { tab: 'config', sub: 'productos', molde: 'abierto', ajuste: 'telas' }, accion: 'ver',
    texto: 'Acá se dice QUÉ TELAS están disponibles para este molde, y en qué piezas.',
    nota: 'Es lo que después el operario puede elegir en el pedido: si no está acá, no aparece.' },
  { ancla: 'telas-variable', accion: 'ver',
    texto: 'Se trabaja de a una variable: el visor muestra sólo sus piezas y no las del molde entero.' },
  { ancla: 'telas-tope', accion: 'ver',
    texto: 'El TOPE dice cuántas telas distintas puede combinar una misma prenda en un pedido.',
    nota: 'Ej.: 2 = el operario podrá usar hasta dos telas en esa prenda.' },
  { ancla: 'telas-mostrar', accion: 'ver',
    texto: 'Y acá se ve, sobre el molde, qué tela quedó en cada pieza.',
    nota: 'El cuello y las tapacosturas suelen ir en RIB.' },
]);

const EX_BORDE = R('ex-borde', 'molde', 'Borde de corte', 'La línea que rodea cada pieza.', 2, [
  { ancla: 'ajuste-borde', ir: { tab: 'config', sub: 'productos', molde: 'abierto', ajuste: 'borde' }, accion: 'ver',
    texto: 'El BORDE DE CORTE es la línea que se imprime alrededor de cada pieza para guiar el corte.',
    nota: 'Se imprime: por eso tiene color y grosor propios.' },
  { ancla: 'borde-tamano', accion: 'ver',
    texto: 'El grosor va en milímetros; el color, en CMYK igual que el resto de la impresión.',
    nota: 'Si tu taller corta con plotter o a mano, esto es lo que sigue la tijera.' },
]);

const EX_ETIQUETA = R('ex-etiqueta', 'molde', 'Etiqueta', 'El textito que identifica cada pieza cortada.', 3, [
  { ancla: 'ajuste-etiqueta', ir: { tab: 'config', sub: 'productos', molde: 'abierto', ajuste: 'etiqueta' }, accion: 'ver',
    texto: 'La ETIQUETA es el textito que se imprime en cada pieza para saber, ya cortada, de qué prenda es.',
    nota: 'Sin eso, en una mesa con 60 piezas cortadas no se sabe qué va con qué.' },
  { ancla: 'etq-piezas', accion: 'ver',
    texto: 'A la derecha están las PIEZAS del molde. Tocá una y el visor te muestra esa pieza en todos sus talles: ahí marcás, sobre el borde, dónde va su etiqueta.',
    nota: 'La etiqueta es de la PIEZA: donde la pongas en el Frente, queda en el Frente de todos los talles. El ✓ te dice cuáles ya tienen su lugar marcado.' },
  { ancla: 'etq-mostrar', accion: 'ver',
    texto: 'Se elige qué dice: el talle, el nombre de la pieza y el número de prenda.' },
  { ancla: 'etq-activo', accion: 'ver',
    texto: 'Se puede apagar entera, y también apagarla en las piezas donde molesta.',
    nota: 'El texto se apoya sobre el borde de la pieza y se inclina siguiéndolo.' },
]);

const EX_EDITABLE = R('ex-editable', 'molde', 'Editable (tamaño)', 'Que el escudo mida lo mismo en todos los talles.', 2, [
  { ancla: 'ajuste-editable', ir: { tab: 'config', sub: 'productos', molde: 'abierto', ajuste: 'editable' }, accion: 'ver',
    texto: 'Un OBJETO EDITABLE es algo del diseño que se puede mover o cambiar aparte: un escudo, un logo, un número.',
    nota: 'El diseñador los deja en una capa del .ai que se llama «Editable …».' },
  { ancla: 'editable-registrar', accion: 'ver',
    texto: 'Acá se dice qué tamaño tiene que tener en cada rango de talles.',
    nota: 'Si no se registra, se agranda junto con el diseño: un escudo terminaría enorme en los talles grandes.' },
]);

const EX_NOMBRES = R('ex-nombres', 'molde', 'Nombres', 'Cómo llama el sistema al talle y a la prenda.', 1, [
  { ancla: 'ajuste-terminologia', ir: { tab: 'config', sub: 'productos', molde: 'abierto', ajuste: 'terminologia' }, accion: 'ver',
    texto: 'Acá se cambia cómo llama el sistema al TALLE y a la PRENDA en este molde.',
    nota: 'Sólo cambia los carteles, no el funcionamiento: si en tu rubro se dice «medida», que lo diga.' },
]);

// ── ÁREA · CONFIGURACIÓN DEL SISTEMA ───────────────────────────────────────────────────────────
const EX_MOLDERIAS = R('ex-molderias', 'config', 'Molderías', 'El catálogo de moldes del sistema.', 2, [
  { ancla: 'cfg-productos', ir: { tab: 'config', sub: 'dashboard' }, accion: 'ver',
    texto: 'Acá viven TODOS los moldes del sistema. Cada tarjeta es una moldería.' },
  { ancla: 'molde-nuevo', ir: { tab: 'config', sub: 'productos' }, accion: 'ver',
    texto: 'Con «Nueva Moldería» se crea una vacía y después se le sube el archivo.' },
  { ancla: 'molde-tarjeta', accion: 'ver',
    texto: 'Cada tarjeta avisa si ya tiene molde y diseño cargados. Tocándola se entra a sus ajustes.',
    nota: 'Ahí adentro están las 10 pantallas de configuración de ese molde.' },
]);

const EX_PLANILLAS = R('ex-planillas', 'config', 'Planillas', 'Qué datos se le piden al operario.', 3, [
  { ancla: 'cfg-columnas', ir: { tab: 'config', sub: 'dashboard' }, accion: 'ver',
    texto: 'Una PLANILLA es el juego de columnas que se carga al hacer un pedido: talle, nombre, número, color…' },
  { ancla: 'col-nueva', ir: { tab: 'config', sub: 'columnas' }, accion: 'ver',
    texto: 'Se pueden tener varias: una para camisetas con nombre y número, otra para prendas lisas.',
    nota: 'Después, cada molde elige cuál usa.' },
  { ancla: 'col-guardar', accion: 'ver',
    texto: 'Las columnas se ordenan arrastrando, y cada una usa una REGLA que dice qué se puede escribir.' },
]);

const EX_REGLAS = R('ex-reglas', 'config', 'Reglas de planilla y capas', 'Qué se puede escribir en cada columna y qué efecto tiene.', 3, [
  { ancla: 'cfg-reglas', ir: { tab: 'config', sub: 'dashboard' }, accion: 'ver',
    texto: 'Una REGLA define un campo reutilizable: cómo se carga (casilla, lista o botones) y qué hace con ese dato.' },
  { ancla: 'regla-nueva', ir: { tab: 'config', sub: 'reglas' }, accion: 'ver',
    texto: 'Lo importante es «qué hace»: puede elegir el talle, elegir el diseño, ESTAMPARSE en la prenda, o cambiar qué piezas entran.',
    nota: 'Ej.: un toggle «capucha = sí» agrega las piezas de la capucha.' },
  { ancla: 'cfg-reglas', accion: 'ver',
    texto: 'Y cada campo que se estampa necesita SU CAPA en el archivo del diseño: abajo está la lista con los nombres exactos.',
    nota: 'Se copian de acá y se le pasan al diseñador.' },
]);

const EX_TELAS = R('ex-telas', 'config', 'Telas', 'De dónde salen y por qué hay que poner el ancho.', 3, [
  { ancla: 'cfg-telas', ir: { tab: 'config', sub: 'dashboard' }, accion: 'ver',
    texto: 'Las telas NO se crean acá: vienen solas del sistema de stock.' },
  { ancla: 'telas-lista', ir: { tab: 'config', sub: 'telas' }, accion: 'ver',
    texto: 'Lo único que se carga a mano es el ANCHO DE IMPRESIÓN, que es el que usa la tizada para acomodar.',
    nota: 'Suele ser menor que la medida del rollo, por los orillos. Si está mal, la tizada sale mal.' },
  { ancla: 'telas-lista', accion: 'ver',
    texto: 'Y los GRUPOS COMBINABLES dicen qué telas se pueden cambiar entre sí en un pedido.' },
]);

const EX_NESTING = R('ex-nesting', 'config', 'Reglas de nesting', 'Cuánta tela se gasta y cómo se corta.', 3, [
  { ancla: 'cfg-nesting', ir: { tab: 'config', sub: 'dashboard' }, accion: 'ver',
    texto: 'Acá se arman los ACOMODOS: separación entre piezas, margen de la hoja y si se pueden girar.' },
  { ancla: 'nesting-nuevo', ir: { tab: 'config', sub: 'nesting' }, accion: 'ver',
    texto: 'Conviene tener dos o tres: «estándar», «apretado» para ahorrar tela y «sin giro» para telas con pelo o rayas.',
    nota: 'Girar una pieza en una tela con dirección la arruina.' },
  { ancla: 'nesting-nuevo', accion: 'ver',
    texto: 'En la otra pestaña están los GRUPOS DE TIZADA: qué molderías se arman juntas en la misma mesa.' },
]);

const EX_FUENTES = R('ex-fuentes', 'config', 'Fuentes', 'Con qué tipografía salen los nombres y números.', 2, [
  { ancla: 'cfg-fuentes', ir: { tab: 'config', sub: 'dashboard' }, accion: 'ver',
    texto: 'Acá se cargan las tipografías con las que se estampan los nombres y los números.',
    nota: 'El sistema las dibuja como curvas: sale igual aunque la máquina no tenga la fuente instalada.' },
  { ancla: 'fuentes-probar', ir: { tab: 'config', sub: 'fuentes' }, accion: 'ver',
    texto: 'Escribiendo acá se ve cómo queda ese texto en todas las fuentes cargadas.',
    nota: 'Sirve para elegir sin generar una tizada de prueba. También avisa si a la fuente le falta alguna letra.' },
]);

const EX_PERFIL = R('ex-perfil', 'config', 'Perfil de color', 'Por qué los colores salen como salen.', 2, [
  { ancla: 'cfg-perfil', ir: { tab: 'config', sub: 'dashboard' }, accion: 'ver',
    texto: 'El PERFIL DE COLOR es la traducción entre lo que se ve en pantalla y lo que sale impreso.' },
  { ancla: 'perfil-card', ir: { tab: 'config', sub: 'perfil' }, accion: 'ver',
    texto: 'Estos son los perfiles instalados en esta máquina; el marcado es el que se usa por defecto.',
    nota: 'Si no sabés cuál poner, dejá el que viene: cambiarlo mueve los colores de TODO lo que imprimas.' },
]);

const EX_USUARIOS = R('ex-usuarios', 'config', 'Usuarios y permisos', 'Quién entra y qué puede hacer.', 2, [
  { ancla: 'cfg-usuarios', ir: { tab: 'config', sub: 'dashboard' }, accion: 'ver',
    texto: 'Acá se define quién usa el sistema y qué puede hacer cada uno.' },
  { ancla: 'usuarios-tabs', ir: { tab: 'config', sub: 'usuarios' }, accion: 'ver',
    texto: 'Son tres listas: los USUARIOS (las personas), los ROLES (paquetes de permisos) y los PERMISOS que existen.',
    nota: 'Conviene armar primero el rol y después las personas.' },
]);

const EX_PUBLICACION = R('ex-publicacion', 'config', 'Publicación', 'Cómo viajan las mejoras al sistema de internet.', 2, [
  { ancla: 'cfg-publicacion', ir: { tab: 'config', sub: 'dashboard' }, accion: 'ver',
    texto: 'Hay dos sistemas: éste, el del taller, y el que está publicado en internet. Acá se manda lo de esta máquina al de internet.' },
  { ancla: 'pub-cuando', ir: { tab: 'config', sub: 'publicacion' }, accion: 'ver',
    texto: 'Se elige cuándo se instala: ahora, en un rato, o un día y hora exactos.',
    nota: 'El corte dura alrededor de un minuto y, si algo falla, el servidor vuelve solo a la versión anterior. Los moldes y pedidos no viajan.' },
]);

// ── ÁREA · DENTRO DEL PEDIDO ───────────────────────────────────────────────────────────────────
const EX_EDITAR_DISENO = R('ex-editar-diseno', 'pedido', 'Editar diseño', 'Mover, agrandar o pintar algo del arte.', 3, [
  { ancla: 'editar-diseno', ir: { tab: 'pedidos', paso: 'arte' }, accion: 'ver',
    texto: 'Con «Editar diseño» se acomoda lo que el arte trae como editable: un escudo, un logo, un objeto suelto.',
    nota: 'No cambia el archivo del diseñador: se guarda una versión aparte.' },
  { ancla: 'edit-alcance', accion: 'ver',
    texto: 'Lo más importante es el ALCANCE: si el cambio va a todo el rango de talles o sólo al que estás viendo.' },
  { ancla: 'edit-color', accion: 'ver',
    texto: 'También se le puede cambiar el color en CMYK, figura por figura.',
    nota: 'Si el control está apagado, ese objeto pinta desde adentro (una imagen) y no se puede recolorear.' },
  { ancla: 'edit-agregar', accion: 'ver',
    texto: 'Y con «Agregar objeto» se suma algo propio (PNG, SVG, PDF o AI) y se coloca sobre una pieza.' },
]);
// Es adentro de un pedido en curso: sin arte cargado no hay nada que mostrar (ver `bloqueo`).
EX_EDITAR_DISENO.requiere = (E) => E.pedido.artesCargadas > 0 ? null
  : 'Es dentro de un pedido con el arte ya cargado: hacé primero «Armar una tizada».';

const EX_MI_MOLDE = R('ex-mi-molde', 'pedido', 'Mis artículos', 'Traer un molde propio al pedido.', 2, [
  { ancla: 'pedido-tabs', ir: { tab: 'pedidos', paso: 'moldes' }, accion: 'ver',
    texto: 'En el pedido hay dos orígenes: el CATÁLOGO (los moldes compartidos) y MIS ARTÍCULOS (los que subiste vos).' },
  { ancla: 'pedido-subir-molde', accion: 'ver',
    texto: 'Con esto se sube un molde propio sin pasar por la configuración del catálogo.',
    nota: 'Sólo hay que decirle qué es cada pieza; después ya se puede pedir.' },
  { ancla: 'pedido-tabs', accion: 'ver',
    texto: 'Un artículo propio se elige ENTERO: no tiene variables, se generan todas sus piezas.' },
]);

export const RECORRIDOS = [
  EX_MOLDERIA, EX_VARIABLES, EX_PLANTILLA, EX_PLANILLA_MOLDE, EX_NESTING_MOLDE, EX_TELAS_MOLDE,
  EX_BORDE, EX_ETIQUETA, EX_EDITABLE, EX_NOMBRES,
  EX_MOLDERIAS, EX_PLANILLAS, EX_REGLAS, EX_TELAS, EX_NESTING, EX_FUENTES, EX_PERFIL,
  EX_USUARIOS, EX_PUBLICACION,
  EX_EDITAR_DISENO, EX_MI_MOLDE,
];

export const AREAS = [
  { id: 'molde', titulo: 'El molde y sus ajustes', desc: 'Moldería, variables, telas, etiqueta…' },
  { id: 'config', titulo: 'Configuración del sistema', desc: 'Planillas, reglas, telas, nesting, usuarios…' },
  { id: 'pedido', titulo: 'Dentro del pedido', desc: 'Editar el diseño, mis artículos' },
];

// El paso a paso primero; después los recorridos explicativos.
export const GUIAS = [ARMAR_TIZADA, ...RECORRIDOS];

export const guiaPorId = (id) => GUIAS.find(g => g.id === id) || null;

/** La única guía PASO A PASO: la que ofrece el botón de Ayuda como acción principal. */
export const GUIA_PRINCIPAL = ARMAR_TIZADA;

/**
 * ¿Falta algo para poder arrancar? Devuelve el texto a mostrar, o null.
 * Impide que un recorrido del PEDIDO saque al usuario de su pedido para dejarlo en una pantalla
 * vacía (ver la regla de `requiere` arriba).
 */
export function bloqueo(g, E) {
  if (!E || E.cargado === false || typeof g.requiere !== 'function') return null;
  try { return g.requiere(E) || null; } catch { return null; }
}
