/**
 * DICCIONARIO DEL SISTEMA — qué es cada cosa, cómo se usa, y cuándo el tutorial la pide.
 *
 * Es de donde el sistema saca los CARTELES de los tutoriales. El usuario graba lo que hace
 * (`grabador` en App.jsx) y el sistema arma solo el texto de cada paso leyendo de acá.
 * Reemplaza a los guiones fijos de `guias.js`, que se escribían a mano tutorial por tutorial
 * (eliminados 2026-08-27 a pedido del usuario).
 *
 * ── UNA ENTRADA ────────────────────────────────────────────────────────────────────────────────
 *   clave    el `data-tour="…"` del elemento en App.jsx. Es lo que el grabador guarda.
 *   nombre   cómo se llama en pantalla (para listar los pasos del tutorial).
 *   que      PARA QUÉ ES. Sale como aclaración gris debajo del cartel.
 *   como     QUÉ HAY QUE HACER, en imperativo criollo. Es el cartel.
 *
 * 🔴 REGLA: cada botón, cada campo y cada espacio del sistema tiene que estar acá. Lo que falte
 * igual se puede grabar —el sistema cae al texto que el botón muestra en pantalla— pero el cartel
 * sale pobre. `verificar_diccionario.mjs` lista lo que falta.
 *
 * Los textos NO son inventados: los que ya existían salieron del video del usuario y de las
 * pantallas reales (venían de `guias.js`). Al corregir una pantalla, corregir también acá.
 *
 * ── PASOS INTELIGENTES (opcional, por elemento) ────────────────────────────────────────────────
 * El tutorial no repite a ciegas lo que se grabó: se adapta a la situación de quien lo sigue.
 *
 *   listo(E)   ESTE PASO YA NO HACE FALTA. `E` = estado real del sistema ahora.
 *              Si da true al empezar, el paso NO SE MUESTRA. Ej.: el tutorial se grabó cargando
 *              una fuente porque a quien grabó le faltaba; a quien ya la tiene, no se le pide.
 *              Si da false, además es lo que hace avanzar: el paso se cumple cuando pasa a true.
 *
 *   cuantos    LA ACCIÓN SE HACE VARIAS VECES. El tutorial PREGUNTA cuántas antes de empezar y no
 *              avanza hasta que se hicieron ésas. `{ pregunta, mide(E), unidad }`:
 *                pregunta  qué se le pregunta a la persona
 *                mide(E)   de dónde sale la cuenta (ej. cuántos diseños tiene el pedido)
 *                unidad    para el contador del globo («2 de 3 diseños»)
 *              🔴 Se cuenta el TOTAL: si dijo 2 y ya había 2 elegidos, el paso está cumplido
 *              al instante — lo YA PRESIONADO también se reconoce (pedido del usuario
 *              2026-08-28; la cuenta relativa pedía re-tocar botones que ya estaban tocados).
 *
 * 🔴 Sólo se pregunta lo que el sistema NO puede deducir (cuántas prendas lleva el pedido, por
 * ejemplo). Si falta el arte o si faltan telas lo sabe el sistema: eso no se pregunta, se mira.
 *
 * 🔴 NO HAY REGLAS DE «VARIOS DISEÑOS» (decisión del usuario, 2026-08-28). El tutorial no cicla ni
 * desvía por su cuenta: si se quiere uno para dos diseños, se graba haciendo dos diseños.
 *
 * El estado `E` lo arma App.jsx (`ayudaEstado`): E.nMoldes · E.pedido.{nDisenos, sinVariable,
 * artesTotal, artesCargadas, telasFaltan, nFilas, hayResultados, nEditables}. Si hace falta mirar
 * otra cosa, se agrega ahí.
 */
// Una sola forma de comparar nombres en todo el sistema de ayuda (sin acentos, sin espacios de
// más, en minúscula). `localizar.js` no importa este archivo, así que no hay ciclo.
import { normalizar, partirAncla } from './localizar.js';

/**
 * LOS AVISOS QUE EL SISTEMA TIENE — para que el editor de tutoriales los ofrezca al armar un paso
 * «esperar aviso», en vez de hacer tipear el título de memoria. Los títulos tienen que coincidir
 * LETRA POR LETRA con los de App.jsx (el contrato lo verifica: si alguien renombra un modal y no
 * toca esta lista, el build corta).
 */
export const AVISOS_CONOCIDOS = {
  // modales (los abre el sistema y esperan una respuesta)
  modales: [
    'Perfil de color del diseño',
    'Tipografía no encontrada',
    'Tus diseños tienen perfiles distintos',
    'Hay talles con piezas sin emparejar',
    'Revisá los valores del CSV',
    'Cargar por lote',
    'Faltan datos en la planilla',
    'Elegí la variable',
    'Elegí las variantes',
    'Seleccionar tela',
    'Telas a la vez',
    'Subir mi propio molde',
    'Registrar capa editable',
    'Cómo armar el .ai',
    // Las de CONFIGURACIÓN, que estaban hechas a mano y la ayuda no veía (2026-09-01)
    'Crear Nuevo Molde',
    'Piezas del grupo',
    'Vista previa del molde',
    'Confirmar Tizada de Sublimación',
  ],
  // cargas (aparecen solas y se van solas: se espera a que terminen)
  cargas: [
    'Se está procesando el archivo.',
    'Se está armando la tizada.',
    'Se está poniendo el diseño sobre el molde.',
  ],
};

export const DICCIONARIO = {

  // ══ NAVEGACIÓN ══════════════════════════════════════════════════════════════════════════════
  'nav-pedidos': {
    nombre: 'Pedidos',
    que: 'La pantalla donde se arma un trabajo de punta a punta: diseño, prenda, arte, telas, planilla y las hojas para imprimir.',
    como: 'Entrá a Pedidos.',
  },
  'nav-config': {
    nombre: 'Configuración',
    que: 'El setup del sistema: moldes, planillas, telas, nesting, fuentes, usuarios. Se toca poco y no hace falta para trabajar.',
    como: 'Entrá a Configuración.',
  },
  'nav-ayuda': {
    nombre: 'Ayuda',
    que: 'Abre la lista de tutoriales y el botón para grabar uno nuevo.',
    como: 'Tocá Ayuda.',
  },

  // Identificado por su TEXTO: este botón no tiene `data-tour` (lo encontró la medición en la
  // pantalla real). Las claves `txt:…` valen igual que las anclas.
  'txt:ayuda': {
    nombre: 'Ayuda',
    que: 'Abre la lista de tutoriales grabados y el botón para grabar uno nuevo.',
    como: 'Tocá «Ayuda».',
  },

  // ══ CONFIGURACIÓN · las tarjetas del panel ══════════════════════════════════════════════════
  'cfg-productos': {
    nombre: 'Moldería',
    que: 'Acá viven TODOS los moldes del sistema. Cada tarjeta es una moldería.',
    como: 'Entrá a «Moldería».',
  },
  'cfg-columnas': {
    nombre: 'Planillas',
    que: 'Una planilla es el juego de columnas que se carga al hacer un pedido: talle, nombre, número, color…',
    como: 'Entrá a «Planillas».',
  },
  'cfg-reglas': {
    nombre: 'Reglas de planilla',
    que: 'Una regla define un campo reutilizable: cómo se carga (casilla, lista o botones) y qué hace con ese dato.',
    como: 'Entrá a «Reglas de planilla».',
  },
  'cfg-telas': {
    nombre: 'Telas',
    que: 'Las telas no se crean acá: vienen solas del sistema de stock. Lo único que se carga a mano es el ancho de impresión.',
    como: 'Entrá a «Telas».',
  },
  'cfg-nesting': {
    nombre: 'Reglas de Nesting',
    que: 'Acá se arman los acomodos: separación entre piezas, margen de la hoja y si se pueden girar.',
    como: 'Entrá a «Reglas de Nesting».',
  },
  'cfg-fuentes': {
    nombre: 'Catálogo de Fuentes',
    que: 'Acá se cargan las tipografías con las que se estampan los nombres y los números. El sistema las dibuja como curvas: sale igual aunque la máquina no tenga la fuente instalada.',
    como: 'Entrá a «Catálogo de Fuentes».',
  },
  'cfg-perfil': {
    nombre: 'Perfil de color',
    que: 'El perfil de color es la traducción entre lo que se ve en pantalla y lo que sale impreso.',
    como: 'Entrá a «Perfil de color».',
  },
  // El toggle de la pantalla de Perfil de color (familia dinámica `perfil-esp-<k>`).
  'perfil-esp-rgb': {
    nombre: 'RGB',
    que: 'El color como se ve en PANTALLA. Es el espacio de los monitores, no el de la impresión.',
    como: 'Tocá «RGB».',
  },
  'perfil-esp-cmyk': {
    nombre: 'CMYK / Impresión',
    que: 'El color como se IMPRIME: es el que manda para la sublimación. Acá se elige el perfil con el que el sistema traduce los colores del arte.',
    como: 'Tocá «CMYK / Impresión».',
  },
  'cfg-usuarios': {
    nombre: 'Usuarios y permisos',
    que: 'Acá se define quién usa el sistema y qué puede hacer cada uno.',
    como: 'Entrá a «Usuarios y permisos».',
  },
  'cfg-publicacion': {
    nombre: 'Publicación',
    que: 'Hay dos sistemas: éste, el del taller, y el que está publicado en internet. Acá se manda lo de esta máquina al de internet.',
    como: 'Entrá a «Publicación».',
  },

  // ══ PEDIDO · paso 1, el diseño ══════════════════════════════════════════════════════════════
  'pedido-diseno-lista': {
    // OPCIONES INTERCAMBIABLES: quien grabó eligió las suyas; quien sigue el tutorial elige las
    // que necesita. Lo que se repite es la CANTIDAD, no cuáles (ver `cuantas` en guion.js).
    opciones: true,
    nombre: 'Lista de diseños',
    que: 'El pedido arranca por el diseño (JUGADOR, GOLERO…). Podés tocar varios.',
    como: 'Elegí el diseño que lleva este trabajo.',
  },
  'pedido-diseno-input': {
    nombre: 'Escribir un diseño',
    que: 'Para cuando el diseño que necesitás no está en la lista de siempre.',
    como: 'Escribí el nombre del diseño.',
  },
  'pedido-diseno-agregar': {
    nombre: 'Agregar diseño',
    que: 'Suma a este pedido el diseño que escribiste.',
    como: 'Tocá «Agregar».',
  },
  'pedido-diseno-chips': {
    // OPCIONES INTERCAMBIABLES: quien grabó eligió las suyas; quien sigue el tutorial elige las
    // que necesita. Lo que se repite es la CANTIDAD, no cuáles (ver `cuantas` en guion.js).
    opciones: true,
    nombre: 'Diseños del pedido',
    que: 'Los diseños que ya cargaste. El número al lado dice cuántas prendas le asignaste.',
    como: 'Tocá el diseño sobre el que querés trabajar.',
  },
  'pedido-progreso': {
    nombre: 'Pasos del pedido',
    que: 'La barra de arriba: en qué paso estás y cuáles quedaron listos.',
    como: 'Mirá en qué paso del pedido estás.',
  },

  'pedido-ir-moldes': {
    nombre: 'Elegir los moldes',
    que: 'Cierra el paso del diseño y pasa al de la prenda. Si está apagado, todavía no elegiste ningún diseño.',
    como: 'Tocá «Elegir los moldes».',
  },
  'pedido-volver-diseno': {
    nombre: 'Volver al diseño',
    que: 'Vuelve al primer paso, para agregar o sacar diseños del pedido. No se pierde nada de lo cargado.',
    como: 'Tocá «← Diseño» para volver.',
  },

  // ══ PEDIDO · paso 2, la prenda ══════════════════════════════════════════════════════════════
  'pedido-tabs': {
    nombre: 'Catálogo / Mis artículos',
    que: 'Hay dos orígenes de moldes: el CATÁLOGO (los compartidos) y MIS ARTÍCULOS (los que subiste vos).',
    como: 'Elegí de dónde sale la prenda.',
  },
  'pedido-variables': {
    // OPCIONES INTERCAMBIABLES: quien grabó eligió las suyas; quien sigue el tutorial elige las
    // que necesita. Lo que se repite es la CANTIDAD, no cuáles (ver `cuantas` en guion.js).
    opciones: true,
    nombre: 'Prendas disponibles',
    que: 'Las prendas que puede llevar ese diseño. La elegida queda con un ✓.',
    como: 'Tocá la prenda que lleva ese diseño.',
    // Cada diseño necesita su prenda: el paso se cumple cuando no queda ninguno sin ella.
    listo: (E) => E.pedido.nDisenos > 0 && E.pedido.sinVariable === 0,
    // EL CICLO: la prenda se elige de a un diseño. Si el que está a la vista ya tiene la suya y
  },
  'pedido-subir-molde': {
    nombre: 'Subir un molde propio',
    que: 'Sube un molde sin pasar por la configuración del catálogo. Sólo hay que decirle qué es cada pieza.',
    como: 'Tocá para subir tu propio molde.',
  },
  'pedido-subir-con-diseno': {
    nombre: 'Molde con el diseño adentro',
    que: 'La otra forma de cargar: un solo archivo que ya trae el diseño estampado en cada pieza, sin arte aparte ni mapeo. Vale para este pedido y no queda guardado.',
    como: 'Tocá para subir el archivo que ya trae el diseño adentro.',
  },
  'pieza-b-lista': {
    nombre: 'Las piezas del molde',
    que: 'Las piezas que trae el archivo, con su miniatura y su medida. Las que todavía dicen «sin nombre» son las que falta identificar: el nombre es lo que hace que después funcionen la etiqueta, las telas y la manga corta o larga.',
    como: 'Tocá la pieza que querés nombrar.',
  },
  'etqb-piezas': {
    nombre: 'Ubicar la etiqueta',
    que: 'La segunda tarea, cuando ya están todas las piezas nombradas: marcar en qué parte del borde de cada pieza sale impresa la etiqueta de corte (el talle, el nombre y el número). El tamaño y la tipografía los deja configurados el taller.',
    como: 'Tocá para pasar a ubicar la etiqueta.',
  },
  'pedido-armar-base': {
    nombre: 'Armar con base',
    que: 'La forma de siempre: elegís el diseño, la prenda de la moldería y le cargás el arte aparte.',
    como: 'Tocá para armar el trabajo con la moldería del sistema.',
  },
  'pedido-armar-con-diseno': {
    nombre: 'Cargar molde con diseño incluido',
    que: 'La otra forma: subís los archivos que ya traen el diseño estampado en cada pieza. No hay arte aparte ni mapeo; sólo decís qué es cada pieza y dónde va la etiqueta.',
    como: 'Tocá para subir los moldes que ya traen el diseño.',
  },
  'cargar-b-zona': {
    nombre: 'Los archivos',
    que: 'Acá van los moldes que ya traen el diseño adentro. Podés soltar varios de una vez (la camiseta, el short…); el nombre de cada molde sale del propio archivo.',
    como: 'Tocá o soltá acá los archivos .ai o .pdf.',
  },
  'cargar-b-moldes': {
    nombre: 'Los moldes cargados',
    que: 'Los archivos que ya subiste. Se tocan los que van juntos en un mismo diseño para nombrarlos de una sola vez.',
    como: 'Tocá los moldes que llevan el mismo diseño.',
  },
  'cargar-b-diseno': {
    nombre: 'Nombre del diseño',
    que: 'Cómo se llama el diseño que llevan los moldes que elegiste (ej. JUGADOR). Es el mismo nombre que usa el resto del pedido para agrupar.',
    como: 'Escribí el nombre del diseño y apretá Enter.',
  },
  'etq-apagar-modo': {
    nombre: 'Elegir piezas sin etiqueta',
    que: 'Todas las piezas llevan etiqueta. Con este botón entrás a elegir cuáles NO: tocás las piezas en el visor y quedan marcadas a rayas. Tocándolas de nuevo vuelven a llevar. Se guarda con «Guardar etiqueta».',
    como: 'Tocá el botón y después las piezas que no llevan etiqueta.',
  },
  'reserva-aviso': {
    nombre: 'Lo está editando otra persona',
    que: 'Aparece cuando otra persona tiene abierto esto mismo. Podés mirarlo, pero el botón de guardar queda apagado hasta que termine, así no se pisan el trabajo. Se libera solo apenas cierra la pantalla.',
    como: 'Esperá a que termine, o avisale.',
  },
  'cargar-b-columna': {
    nombre: 'De qué talle toma las medidas',
    que: 'Cuando la planilla lleva más de una columna de talle (por ejemplo «Talle» y «Talle short»), acá se dice de cuál toma sus medidas este molde. Sin esto, un short tomaría el talle de la camiseta y saldría del tamaño equivocado.',
    como: 'Tocá la columna de talle que le corresponde a este molde.',
  },
  'molde-columna-talle': {
    nombre: 'De qué talle toma las medidas',
    que: 'Con más de una columna de talle en la planilla, cada molde toma el suyo de una: la camiseta de «Talle» y el short de «Talle short». Mientras no lo digas, la tarjeta lo marca en amarillo.',
    como: 'Tocá la columna de talle que le corresponde a este molde.',
  },
  'cargar-b-siguiente': {
    nombre: 'Nombrar las piezas',
    que: 'Pasa al visor para decir qué es cada pieza de los moldes que cargaste. Se habilita cuando todos tienen su diseño.',
    como: 'Tocá para pasar a nombrar las piezas.',
  },
  'cargar-b-volver': {
    nombre: 'Volver',
    que: 'Vuelve a elegir cómo armar el trabajo. Los moldes que ya subiste quedan cargados.',
    como: 'Tocá para volver.',
  },
  'pieza-b-nombrar': {
    nombre: 'Nombrar las piezas',
    que: 'Abre la Moldería de este molde con la herramienta de nombrar de Configuración: todos los talles a la vista, tocás las que son la misma pieza y escribís qué es. Con «← Volver al pedido» seguís acá.',
    como: 'Tocá el botón. En Moldería, tocá o encerrá con un recuadro las piezas y escribí el nombre.',
  },
  'volver-pedido-b': {
    nombre: 'Volver al pedido',
    que: 'Cierra la pantalla de configuración y vuelve al paso Arte del pedido con los nombres y la etiqueta ya guardados.',
    como: 'Tocá «← Volver al pedido».',
  },
  'pedido-volver-inicio': {
    nombre: 'Volver al inicio',
    que: 'Vuelve a la pantalla de las dos formas de armar el trabajo (con base, o cargando un molde con diseño). Lo que ya elegiste queda.',
    como: 'Tocá «← Inicio».',
  },
  'arteb-ojo-todos': {
    nombre: 'Mostrar u ocultar todos los talles',
    que: 'En «Nombrar piezas» del molde con diseño se ven todos los talles juntos, uno debajo del otro. Este ojo los muestra u oculta todos de una; el de cada talle, uno solo.',
    como: 'Tocá el ojo. Ocultar un talle no lo saca del molde: sólo deja de dibujarse mientras nombrás.',
  },
  'arte-volver-cargar-b': {
    nombre: 'Volver a cargar moldes',
    que: 'Vuelve a la pantalla donde se cargan los moldes con diseño, para agregar otro archivo o cambiar a qué diseño va cada uno. Los nombres de las piezas quedan.',
    como: 'Tocá «← Cargar moldes».',
  },
  'pedido-terminar': {
    nombre: 'Terminar el pedido',
    que: 'Cierra el pedido y borra el molde que subiste con el diseño adentro: se cargó sólo para este trabajo. Las tizadas que ya bajaste no se tocan.',
    como: 'Tocá para cerrar el pedido.',
  },
  'cfg-con-diseno': {
    nombre: 'Molde con diseño',
    que: 'La configuración de los moldes que ya traen el diseño adentro de cada pieza: el borde de corte, la etiqueta y cómo se acomodan en la tela. Se deja una vez y vale para todos, también para los que ya están cargados.',
    como: 'Tocá para configurar cómo salen esos moldes.',
  },
  'cfgb-borde-mm': {
    nombre: 'Grosor del borde de corte',
    que: 'El ancho, en milímetros, de la línea de corte que rodea cada pieza de estos moldes.',
    como: 'Escribí el grosor en milímetros.',
  },
  'cfgb-borde-alin': {
    nombre: 'Dónde va el borde',
    que: 'Si la línea de corte se dibuja por fuera del contorno de la pieza, centrada sobre él, o por dentro. Cambia cuánta tela queda alrededor.',
    como: 'Elegí dónde se dibuja el borde.',
  },
  'cfgb-etq-mm': {
    nombre: 'Tamaño de la etiqueta',
    que: 'La altura de la letra, en milímetros, del texto que se imprime al borde de cada pieza (talle, nombre y número).',
    como: 'Escribí el tamaño de letra en milímetros.',
  },
  'cfgb-solo-navegador': {
    nombre: 'El servidor no calcula',
    que: 'Si todo lo pesado (preparar moldes, analizar diseños, previas y tizadas) lo hace la computadora de cada persona, y el servidor sólo valida y guarda.',
    como: 'Tocá el interruptor y guardá. Si lo fija el entorno del servidor, acá no se puede cambiar.',
  },
  'cfgb-borde-on': {
    nombre: 'Dibujar el borde de corte',
    que: 'Si las piezas de estos moldes salen con la línea de corte alrededor o sin ella.',
    como: 'Tocá el interruptor.',
  },
  'cfgb-borde-color': {
    nombre: 'Color del borde de corte',
    que: 'El color CMYK de la línea de corte que rodea cada pieza.',
    como: 'Tocá la muestra y elegí el color.',
  },
  'cfgb-etq-on': {
    nombre: 'Poner etiqueta',
    que: 'Si las piezas llevan impreso el rótulo con el talle, el nombre de la pieza y el número de prenda.',
    como: 'Tocá el interruptor. Apagado, ninguna pieza de estos moldes lleva etiqueta.',
  },
  'cfgb-etq-mostrar': {
    nombre: 'Qué dice la etiqueta',
    que: 'Las tres partes del rótulo: el talle, el nombre de la pieza y el número de prenda. Se prenden y apagan por separado.',
    como: 'Tocá cada chip para incluirlo o sacarlo.',
  },
  'cfgb-etq-sep': {
    nombre: 'Separador de la etiqueta',
    que: 'El carácter que va entre el talle, el nombre de la pieza y el número de prenda del rótulo.',
    como: 'Escribí el separador (hasta 3 caracteres).',
  },
  'cfgb-etq-color': {
    nombre: 'Color del texto de la etiqueta',
    que: 'El color CMYK con el que se imprime el rótulo. El cliente lo puede cambiar en su molde.',
    como: 'Tocá la muestra y elegí el color.',
  },
  'cfgb-etq-halo-color': {
    nombre: 'Color del halo',
    que: 'El color del contorno que rodea al texto de la etiqueta y lo hace legible sobre un diseño con mucho dibujo. El cliente lo puede cambiar en su molde.',
    como: 'Tocá la muestra y elegí el color.',
  },
  'cfgb-etq-halo-on': {
    nombre: 'Dibujar el halo',
    que: 'Si el texto de la etiqueta lleva contorno alrededor o va limpio.',
    como: 'Tocá el interruptor.',
  },
  'cfgb-etq-align': {
    nombre: 'Alineación de la etiqueta',
    que: 'De qué lado del punto que marca el cliente se escribe el texto de la etiqueta: a la izquierda, centrado o a la derecha.',
    como: 'Elegí una de las tres. Vale para todos los moldes con diseño.',
  },
  'cfgb-etq-halo-mm': {
    nombre: 'Grosor del halo',
    que: 'El ancho, en milímetros, del contorno que rodea al texto de la etiqueta. El halo es lo que hace que se lea sobre un diseño oscuro o con mucho dibujo.',
    como: 'Escribí el grosor en milímetros. Con 0 (o apagando «Dibujar el halo») el texto va sin contorno.',
  },
  'cfgb-planilla': {
    nombre: 'Planilla de estos moldes',
    que: 'Las columnas del Excel (talle, nombre, número…) que se le ponen a todo molde con diseño al subirlo. El cliente no la elige: la deja el taller acá.',
    como: 'Elegí una de las planillas armadas en «Columnas de la planilla». Vale para los moldes que se suban de ahora en más.',
  },
  'cfgb-nesting': {
    nombre: 'Cómo se acomodan en la tela',
    que: 'Qué regla de nesting —separación entre piezas, margen y giros— se usa para acomodar estos moldes. Las reglas se crean en «Reglas de Nesting».',
    como: 'Elegí la regla de acomodo.',
  },
  'cfgb-guardar': {
    nombre: 'Guardar la configuración',
    que: 'Guarda estos valores para TODOS los moldes con diseño, incluidos los que ya están cargados: una tizada hecha antes del cambio y otra después salen distintas.',
    como: 'Tocá para guardar.',
  },

  'pedido-ir-arte': {
    nombre: 'Cargar el arte',
    que: 'Pasa al paso del arte. Si está apagado, falta elegir la prenda de algún diseño: te lo avisa al lado.',
    como: 'Tocá «Cargar el arte».',
  },
  'pedido-volver-moldes': {
    nombre: 'Volver a los moldes',
    que: 'Vuelve al paso de la prenda, para cambiar qué molde lleva cada diseño.',
    como: 'Tocá «← Moldes» para volver.',
  },

  // ══ PEDIDO · paso 3, el arte ════════════════════════════════════════════════════════════════
  'arte-variables': {
    nombre: 'Prendas del diseño',
    que: 'Las prendas (variables) de este diseño, cada una con su estado: si ya tiene el arte cargado o si le falta.',
    como: 'Tocá la prenda a la que le vas a cargar el arte.',
    // OPCIONES INTERCAMBIABLES: quien sigue el tutorial trabaja la que necesita, no la que se grabó.
    opciones: true,
  },
  'arte-cargar': {
    nombre: 'Cargar arte',
    que: 'El archivo del diseño (.ai o .pdf) que se estampa sobre las piezas.',
    como: 'Tocá «Cargar arte» y elegí el archivo del diseño.',
    // Si el arte de todas las prendas ya está cargado, no hay nada que pedir.
    listo: (E) => E.pedido.artesTotal > 0 && E.pedido.artesCargadas >= E.pedido.artesTotal,
  },
  'arte-telas': {
    nombre: 'Asignar telas',
    que: 'Hay que decir en qué tela va cada pieza; si falta alguna, el pedido no avanza.',
    como: 'Tocá «Asignar telas».',
    // Mientras queden piezas sin tela el pedido no puede seguir: el paso insiste hasta que no falte.
    listo: (E) => E.pedido.artesCargadas > 0 && E.pedido.telasFaltan === 0,
  },
  'arte-fuente': {
    nombre: 'Fuente del arte',
    que: 'Avisa si el arte usa una tipografía que el sistema no tiene cargada. Es el único requisito que no traba: podés seguir igual.',
    como: 'Revisá la tipografía del arte.',
    // 🔴 EL CASO QUE PIDIÓ EL USUARIO: el tutorial se pudo grabar cargando una fuente porque a
    // quien grabó le faltaba. A quien la tiene bien, este paso no se le muestra.
    listo: (E) => !E.pedido.fuentesFaltan,
  },
  'visor-molde': {
    // `lienzo`: acá se TRABAJA tocando piezas, no se aprieta un botón. El paso es el visor entero
    // y nunca se afina a lo que haya adentro (ver `data-lienzo` en App.jsx y `identificar`).
    lienzo: true,
    nombre: 'Visor del molde',
    que: 'El molde dibujado, pieza por pieza y talle por talle. Acá se tocan las piezas: para nombrarlas, para ponerles el diseño o para asignarles la tela. La primera vez tarda un poco: se hace una sola vez.',
    como: 'Trabajá en el visor: tocá las piezas que necesites.',
  },
  'editar-diseno': {
    nombre: 'Editar diseño',
    que: 'Para mover, agrandar o pintar algo del diseño: un escudo, un logo, un número. No es obligatorio.',
    como: 'Entrá a «Editar diseño».',
  },

  'arte-diseno-chips': {
    // OPCIONES INTERCAMBIABLES: quien grabó eligió las suyas; quien sigue el tutorial elige las
    // que necesita. Lo que se repite es la CANTIDAD, no cuáles (ver `cuantas` en guion.js).
    opciones: true,
    nombre: 'Diseños (paso Arte)',
    que: 'Los diseños del pedido, cada uno con su contador de artes cargados. Tocando uno, el paso Arte pasa a trabajar sobre ese diseño.',
    como: 'Tocá el diseño al que le vas a cargar el arte.',
  },

  // ══ MODALES (claves `modal:<título normalizado>`) ═══════════════════════════════════════════
  // Cuando un modal se abre en medio del tutorial, el motor FRENA y lo explica con esto. Un modal
  // sin entrada igual frena: el cartel se arma con su propio título (ver `explicarModal`).
  // `ventana: {contenido, botones, cuando, paso}` = con qué DIBUJARLA. El editor de tutoriales
  // muestra estas fichas como vista previa para poder elegirlas mirando, no leyendo el nombre.
  'modal:perfil de color del diseno': {
    nombre: 'Perfil de color del diseño',
    que: 'El sistema avisa qué perfil de color trae (o no trae) el arte y cuál le va a asignar. El perfil es la traducción entre el color del archivo y el color impreso.',
    como: 'Leé el aviso y tocá «Entendido» para seguir.',
    ventana: { contenido: 'El perfil que trae el arte y el que usa el sistema',
               botones: ['Entendido'], cuando: 'al cargar un diseño', paso: 'diseno' },
  },
  'modal:tipografia no encontrada': {
    nombre: 'Tipografía no encontrada',
    que: 'Al arte le falta una tipografía: si se sublima así, el nombre y el número salen con otra letra. Muestra qué fuente falta y en qué molde y diseño.',
    como: 'Cargá la tipografía que falta, o seguí igual si la letra de reemplazo te sirve.',
    ventana: { contenido: 'Las fuentes que faltan, con su molde y su diseño',
               botones: ['Cargar la tipografía', 'Seguir de todos modos'], cuando: 'al pasar de Arte a la planilla', paso: 'arte' },
  },
  'modal:tus disenos tienen perfiles distintos': {
    nombre: 'Tus diseños tienen perfiles distintos',
    que: 'Los diseños del pedido traen perfiles de color distintos y todos tienen que salir con el mismo, o los colores impresos no van a coincidir entre prendas.',
    como: 'Elegí a qué perfil unificar todo el pedido.',
    ventana: { contenido: 'La lista de perfiles, cada uno con su tira de colores',
               botones: [], cuando: 'al pasar de Arte a la planilla', paso: 'arte' },
  },
  'modal:hay talles con piezas sin emparejar': {
    nombre: 'Hay talles con piezas sin emparejar',
    que: 'Al molde recién subido le faltan piezas en algunos talles, o tiene piezas dibujadas que no se pudieron emparejar con las de los demás talles.',
    como: 'Cargalo sin esos talles, o cerrá y volvé a subir el archivo corregido.',
    ventana: { contenido: 'Los talles con lo que les falta o les sobra',
               botones: ['Cargar sin esos talles', 'Cerrar y subirlo de nuevo'], cuando: 'al subir un molde', paso: 'moldes' },
  },
  'modal:revisa los valores del csv': {
    nombre: 'Revisá los valores del CSV',
    que: 'El CSV que importaste trae valores que no existen en el molde (un talle, una variable o una opción que no está). Esas filas no se pueden fabricar así.',
    como: 'Corregí cada valor marcado en rojo, o dejalos afuera de la importación.',
    ventana: { contenido: 'Las filas con el valor inválido en rojo',
               botones: ['Cancelar', 'Importar las filas'], cuando: 'al importar un CSV', paso: 'planilla' },
  },
  'modal:faltan datos en la planilla': {
    nombre: 'Faltan datos en la planilla',
    que: 'Hay filas a las que les falta un dato obligatorio (el talle, el diseño…): así no se pueden fabricar. Se decide antes de armar la tizada, no después.',
    como: 'Elegí «Enviar igual» para fabricar sólo las filas completas, o «Cargar el dato» para volver a la planilla.',
    ventana: { contenido: 'Las filas incompletas y qué le falta a cada una',
               botones: ['Cargar el dato', 'Enviar igual'], cuando: 'al enviar el pedido con filas a medio llenar', paso: 'planilla' },
  },
  'modal:cargar por lote': {
    nombre: 'Cargar por lote',
    que: 'Crea de una todas las filas del pedido: se dice cuántas prendas lleva cada talle y el sistema arma una fila por prenda, lista para ponerle nombre y número.',
    como: 'Poné la cantidad de cada talle y creá las filas.',
    ventana: { contenido: 'Cada talle con un contador − N +',
               botones: ['Poner todo en 0', 'Cancelar', 'Crear las filas'], cuando: 'al cargar prendas en la planilla', paso: 'planilla' },
  },
  'modal:elegi la variable': {
    nombre: 'Elegí la variable',
    que: 'La variable de esa fila: qué piezas del molde se generan para esa prenda (con costadillo, sin costadillo, manga larga…).',
    como: 'Tocá la variable que lleva esa prenda.',
    ventana: { contenido: 'Tarjetas con el dibujo de las piezas de cada variable',
               botones: [], cuando: 'al tocar la variable de una fila', paso: 'planilla' },
  },
  'modal:elegi las variantes': {
    nombre: 'Elegí las variantes',
    que: 'El rango de talles al que se aplica lo que estás configurando. Los talles ya usados por otro rango aparecen tachados.',
    como: 'Tocá los talles del rango (con Shift elegís un tramo entero) y confirmá.',
    ventana: { contenido: 'Todos los talles como chips; los ya usados, tachados',
               botones: ['Limpiar', 'Todas (libres)', 'Listo'], cuando: 'al armar el rango de una capa editable', paso: 'config' },
  },
  'modal:seleccionar tela': {
    nombre: 'Seleccionar tela',
    que: 'El catálogo de telas para asignarle una a las piezas elegidas del molde (si no hay ninguna elegida, va a todas).',
    como: 'Buscá la tela y asignala a las piezas.',
    ventana: { contenido: 'Grilla de telas con su color y su ancho, y un buscador',
               botones: ['Asignar'], cuando: 'al asignar telas a las piezas', paso: 'config' },
  },
  'modal:telas a la vez': {
    nombre: 'Telas a la vez',
    que: 'El tope de telas distintas que puede combinar una prenda de esa variable dentro del pedido. En cero, sin límite.',
    como: 'Poné el número de telas y guardá.',
    ventana: { contenido: 'Un número grande con botones − y +',
               botones: ['Sin límite', 'Guardar'], cuando: 'al configurar las telas de una variable', paso: 'config' },
  },
  'modal:subir mi propio molde': {
    nombre: 'Subir mi propio molde',
    que: 'Sube un molde tuyo (.ai, .pdf o .dxf) sin pasar por el catálogo: queda en «Mis artículos» y se abre su configuración para dejarlo listo.',
    como: 'Ponele nombre, soltá el archivo y subilo.',
    ventana: { contenido: 'El nombre del molde y la zona para soltar el archivo',
               botones: ['Cancelar', 'Subir y configurar'], cuando: 'al subir un molde propio', paso: 'moldes' },
  },
  'modal:registrar capa editable': {
    nombre: 'Registrar capa editable',
    que: 'Da de alta una capa «Editable …» del arte: su nombre y con qué medida entra en cada rango de talles (apaisada, vertical o el tamaño original).',
    como: 'Ponele el nombre y la medida de cada rango, y guardá.',
    ventana: { contenido: 'El nombre de la capa y sus rangos con medidas en cm',
               botones: ['Eliminar', 'Cancelar', 'Guardar'], cuando: 'al configurar las capas editables', paso: 'config' },
  },
  'modal:como armar el .ai': {
    nombre: 'Cómo armar el .ai',
    que: 'La guía de qué va en cada capa del archivo de Illustrator: el diseño, las guías y una capa por cada texto que se personaliza.',
    como: 'Mirá qué capa lleva cada cosa; el nombre de cada una se copia de acá.',
    ventana: { contenido: 'Una ficha por capa, con su nombre copiable',
               botones: [], cuando: 'al preparar el .ai, desde Configuración', paso: 'config' },
  },
  // Las VENTANAS DE TRABAJO (las que aparecen y se van solas). No se responden: se esperan.
  'modal:se esta procesando el archivo.': {
    nombre: 'Se está procesando el archivo.',
    que: 'El sistema está leyendo el archivo que subiste y separando sus piezas. Tarda lo que tarda: se trabaja siempre sobre el vector original.',
    como: 'Esperá a que termine; no hay nada que tocar.',
    ventana: { contenido: 'El avance de la lectura del archivo', trabajo: true,
               botones: [], cuando: 'al subir un molde o un arte', paso: 'moldes' },
  },
  'modal:se esta armando la tizada.': {
    nombre: 'Se está armando la tizada.',
    que: 'El motor está acomodando las piezas sobre la tela y armando las mesas para imprimir. Es la parte más pesada del trabajo.',
    como: 'Esperá a que termine; no hay nada que tocar.',
    ventana: { contenido: 'El avance de la tizada, mesa por mesa', trabajo: true,
               botones: [], cuando: 'al fabricar el pedido', paso: 'planilla' },
  },
  'modal:se esta poniendo el diseno sobre el molde.': {
    nombre: 'Se está poniendo el diseño sobre el molde.',
    que: 'El sistema está recortando el diseño para cada pieza y cada talle. Aparece al entrar al paso Arte o al cambiar el mapeo.',
    como: 'Esperá a que termine; no hay nada que tocar.',
    ventana: { contenido: 'Variante y talle en curso, con el avance', trabajo: true,
               botones: [], cuando: 'al preparar el arte', paso: 'arte' },
  },

  // ══ EDITOR DEL DISEÑO ═══════════════════════════════════════════════════════════════════════
  'edit-objetos': {
    nombre: 'Objetos del diseño',
    que: 'La lista de objetos editables que trae el arte. Se elige uno, o varios con Ctrl+clic.',
    como: 'Elegí el objeto que querés tocar.',
  },
  'edit-alcance': {
    nombre: 'Alcance del cambio',
    que: 'Lo más importante del editor: si el cambio va a todo el rango de talles o sólo al que estás viendo.',
    como: 'Elegí a qué talles afecta el cambio.',
  },
  'edit-color': {
    nombre: 'Color del objeto',
    que: 'Cambia el color en CMYK, figura por figura. Si está apagado, ese objeto pinta desde adentro (es una imagen) y no se puede recolorear.',
    como: 'Cambiale el color al objeto.',
  },
  'edit-agregar': {
    nombre: 'Agregar objeto',
    que: 'Suma algo propio (PNG, SVG, PDF o AI) y lo coloca sobre una pieza. Queda como un editable más.',
    como: 'Tocá «Agregar objeto».',
  },
  // Las tres MARCAS DE PROCESO: el objeto no se sublima y en su lugar va una cruz de 3 cm, para
  // que en el taller sepan que ahí va otro proceso. (Familia dinámica `edit-marca-<k>`.)
  'edit-marca-tpu': {
    nombre: 'TPU',
    que: 'El objeto no se estampa: va en TPU (vinilo termoadhesivo). En la tizada queda una cruz de 3 cm marcando dónde va, y en la ficha técnica su material y su medida.',
    como: 'Tocá «TPU».',
  },
  'edit-marca-bordado': {
    nombre: 'Bordado',
    que: 'El objeto no se estampa: va bordado. En la tizada queda una cruz de 3 cm marcando dónde va, y en la ficha técnica su material y su medida.',
    como: 'Tocá «Bordado».',
  },
  'edit-marca-dtf': {
    nombre: 'DTF',
    que: 'El objeto no se estampa acá: va en DTF (transfer). En la tizada queda una cruz de 3 cm marcando dónde va, y en la ficha técnica su material y su medida.',
    como: 'Tocá «DTF».',
  },
  'edit-marca-visible': {
    nombre: 'Sin marca',
    que: 'Deja el lugar del objeto vacío en la tizada: ahí no se imprime nada. Si el objeto lleva TPU, Bordado o DTF, lo que se saca es la cruz de 3 cm; si no lleva ninguno, el objeto directamente no se imprime. Igual queda en la ficha técnica con su material y su medida.',
    como: 'Tocá «Sin marca».',
  },
  'edit-guardar': {
    nombre: 'Guardar del editor',
    que: 'Guarda las posiciones y los colores de los objetos, en el alcance de talles elegido.',
    como: 'Tocá «Guardar».',
  },
  'editable-registrar': {
    nombre: 'Registrar tamaño del editable',
    que: 'Dice qué tamaño tiene el objeto en cada rango de talles. Sin esto se agranda junto con el diseño: un escudo terminaría enorme en los talles grandes.',
    como: 'Registrá el tamaño del objeto.',
  },

  'arte-siguiente': {
    nombre: 'A la planilla',
    que: 'Cierra el paso del arte. Si falta alguna pieza sin tela el botón queda apagado y te dice cuántas son.',
    como: 'Cuando diga «Todas las piezas tienen tela», tocá «A la planilla».',
    // Mientras falten telas no se puede avanzar: el paso insiste hasta que no falte ninguna.
    listo: (E) => E.pedido.artesCargadas > 0 && E.pedido.telasFaltan === 0,
  },

  // ══ PEDIDO · paso 4, la planilla ════════════════════════════════════════════════════════════
  'planilla-tabla': {
    nombre: 'Planilla del pedido',
    que: 'Una fila = una prenda. Un clic elige la celda y escribís directo; en Talle y Diseño se abre la lista.',
    como: 'Cargá el talle, y el nombre y el número si la prenda los lleva.',
  },
  // ── EL ESPACIO DE TRABAJO VISUAL ─────────────────────────────────────────────────────────
  'molde-visor': {
    lienzo: true,
    nombre: 'La prenda armada',
    que: 'El dibujo de la prenda con todas sus piezas. Cada pieza se toca para trabajar sobre ella: ponerle el diseño, asignarle la tela o ver cómo va a salir.',
    como: 'Tocá la pieza sobre la que querés trabajar.',
  },
  // Una PIEZA suelta se identifica como `pieza:<su nombre>` y el cartel se arma con ese nombre
  // (son distintas en cada molde, así que no pueden estar listadas acá una por una).

  // ── LAS COLUMNAS DE LA PLANILLA (`col:<id>`) ──────────────────────────────────────────────
  // Son configurables por molde: acá están las conocidas; una columna propia del molde (una sisa,
  // una capucha) cae al fallback de `explicar`, que usa su LABEL.
  'col:talle': {
    nombre: 'Columna Talle',
    que: 'El talle de esa prenda. De acá sale qué molde se usa y de qué tamaño se corta.',
    como: 'Elegí el talle de la prenda en esta columna.',
  },
  'col:nombre': {
    nombre: 'Columna Nombre',
    que: 'El nombre que va estampado en la prenda. Sale con la tipografía, la curva y el borde del diseño.',
    como: 'Escribí el nombre de cada prenda en esta columna.',
  },
  'col:numero': {
    nombre: 'Columna Número',
    que: 'El número que va estampado. Igual que el nombre, respeta la letra y el borde del diseño.',
    como: 'Escribí el número de cada prenda en esta columna.',
  },
  'col:cantidad': {
    nombre: 'Columna Cantidad',
    que: 'Cuántas prendas iguales salen de esa fila. Con 5, esa fila sale 5 veces en la tizada, con el mismo talle, nombre y número.',
    como: 'Poné cuántas prendas iguales lleva esa fila.',
  },
  'col:diseno': {
    nombre: 'Columna Diseño',
    que: 'Con qué diseño se estampa esa prenda. Un pedido puede llevar varios diseños y esta columna decide el de cada fila.',
    como: 'Elegí el diseño de esa prenda.',
  },
  'col:manga': {
    nombre: 'Columna Manga',
    que: 'La opción de la prenda que cambia sus piezas: manga corta o larga. Un molde puede tener otras columnas así (sisa, capucha), con el nombre que les puso su dueño.',
    como: 'Elegí la opción de esa prenda.',
  },

  'planilla-agregar': {
    nombre: 'Agregar filas',
    que: 'Suma filas vacías al final de la planilla.',
    como: 'Poné cuántas filas y tocá «Agregar Fila».',
    // Una fila por prenda: cuántas van sólo lo sabe la persona.
    cuantos: { pregunta: '¿Cuántas prendas lleva este pedido?',
               mide: (E) => E.pedido.nFilas, unidad: 'fila' },
  },
  'planilla-cantidad': {
    nombre: 'Columna cantidad',
    que: 'Enciende la columna Cantidad: una fila con cantidad 5 sale 5 veces en la tizada, con el mismo talle, nombre y número. Oculta, cada fila vale 1.',
    como: 'Tocá «Columna cantidad».',
  },
  'planilla-lote': {
    nombre: 'Cargar por lote',
    que: 'Carga de una vez varias filas por talle, sin tipear una por una. Primero rellena las filas vacías que ya haya.',
    como: 'Tocá «Cargar por lote».',
  },
  'planilla-csv': {
    nombre: 'Importar CSV',
    que: 'Si el pedido ya te llegó en Excel, se importa en vez de tipearlo. Lo que no exista en el molde queda vacío: no inventa datos.',
    como: 'Tocá «Importar» y elegí el archivo.',
  },
  'planilla-exportar': {
    nombre: 'Exportar CSV',
    que: 'Baja la planilla como CSV, sólo con las columnas que están a la vista.',
    como: 'Tocá «Exportar».',
  },

  'planilla-enviar': {
    nombre: 'Enviar el pedido',
    que: 'Manda el pedido a fabricar y arma las tizadas. Si está apagado, arriba dice qué falta: filas, un valor inválido o el arte de algún molde.',
    como: 'Cuando la planilla esté completa, tocá «Enviar».',
  },
  'planilla-volver-arte': {
    nombre: 'Volver al arte',
    que: 'Vuelve al paso del arte, para cambiar el diseño o las telas. La planilla cargada queda como está.',
    como: 'Tocá «← Arte» para volver.',
  },

  // ══ PEDIDO · paso 5, los resultados ═════════════════════════════════════════════════════════
  'resultados-mesas': {
    nombre: 'Mesas de la tizada',
    que: 'Mientras se arma, va mostrando en qué va. Al terminar quedan las mesas listas para imprimir.',
    como: 'Esperá a que termine de armar la tizada.',
  },
  'resultados-hojas': {
    nombre: 'Hojas para imprimir',
    que: 'Cada hoja es una mesa de tela lista para el RIP.',
    como: 'Mirá las hojas que salieron.',
  },
  'tizada-cancelar': {
    nombre: 'Cancelar',
    que: 'Para la tizada que se está armando. Se frena al terminar el paso en curso, así no queda ningún archivo a medias, y se borra lo que alcanzó a generar.',
    como: 'Tocá «Cancelar» mientras se arma la tizada.',
  },
  'resultados-descargar': {
    nombre: 'Descargar todo',
    que: 'Baja cada mesa como un archivo aparte, con su nombre.',
    como: 'Tocá «Descargar todo».',
  },
  'resultados-ficha': {
    nombre: 'Ficha técnica',
    que: 'La hoja para el taller: la tabla de talles y el molde guía con la tela de cada pieza. También lista lo que no se sublima y en qué material va.',
    como: 'Abrí la «Ficha técnica».',
  },

  'resultados-volver-planilla': {
    nombre: 'Volver a la planilla',
    que: 'Vuelve a la planilla del pedido, con todo lo que habías cargado, para corregir y volver a generar.',
    como: 'Tocá «← Planilla» para volver.',
  },

  // ══ MOLDES ══════════════════════════════════════════════════════════════════════════════════
  'molde-nuevo': {
    nombre: 'Nueva Moldería',
    que: 'Crea una moldería vacía; después se le sube el archivo.',
    como: 'Tocá «Nueva Moldería».',
  },
  'molde-nombre': {
    nombre: 'Nombre del molde',
    que: 'Con este nombre lo va a ver el operario en el pedido.',
    como: 'Escribí el nombre del molde.',
  },
  'molde-crear-ok': {
    nombre: 'Crear el molde',
    que: 'Confirma la moldería nueva.',
    como: 'Confirmá para crearla.',
  },
  'molde-subir': {
    nombre: 'Subir archivo del molde',
    que: 'Sube o reemplaza el archivo del molde (.ai, .pdf o .dxf). Si lo volvés a subir, los nombres de pieza que ya pusiste se transfieren solos.',
    como: 'Subí el archivo del molde.',
  },
  'molde-como-exportar': {
    nombre: 'Cómo exportar el molde',
    que: 'La guía para el diseñador: cómo tiene que salir el archivo desde Illustrator, Corel u Optitex.',
    como: 'Abrí la ayuda de cómo exportar.',
  },
  'molde-cfg-abrir': {
    nombre: 'Guardar / usar configuración',
    que: 'Guarda cómo quedó configurado este molde (nombres de las piezas, grupos, variables, telas y talle de guía) para volver a aplicarlo cuando se suba el mismo archivo en otro pedido.',
    como: 'Abrí las configuraciones guardadas.',
  },
  'arte-fuente-campo': {
    nombre: 'Tipografía de cada campo',
    que: 'Cada texto que se personaliza —el nombre, el número, un número 2— puede llevar su propia tipografía, aunque en el diseño vengan con la misma. Primero elegís el campo y después la tipografía de la lista: sólo cambia ese campo. Tocar la original del diseño la devuelve.',
    como: 'Tocá el campo (Nombre, Número…) y después la tipografía que querés para él.',
  },
  'arte-fuente-copiar': {
    nombre: 'Usar la tipografía en otros moldes',
    que: 'La tipografía que elegís es de este molde en este diseño: cada uno tiene la suya. Con este botón la copiás a los otros moldes o diseños del pedido, todos de un toque o marcando cuáles, sin ir de molde en molde. Pisa lo que tuvieran elegido.',
    como: 'Tocá «Usar en otros moldes…» y marcá a cuáles va.',
  },
  'pieza-b-etiqueta-archivo': {
    nombre: 'La etiqueta que trae el diseño',
    que: 'El diseño trae textos con el talle. Los que se repiten igual en casi todas las piezas son la etiqueta de corte que puso el diseñador: se ocultan, y la tizada pone la del sistema, así la prenda no sale con dos. Los que están en una sola pieza (la talla tejida, por ejemplo) son parte del diseño y se dejan. Cada renglón es una familia de textos (misma fuente y tamaño) con un casillero: si el sistema se equivocó, lo cambiás vos y las piezas se rehacen.',
    como: 'Mirá cada renglón: marcado = se oculta, sin marcar = se deja. Cambiá el casillero si hace falta.',
  },
  'pieza-b-sugerida': {
    nombre: 'Ya configuraste este molde',
    que: 'Aviso de que hay una configuración tuya guardada que le calza a este molde: dice cuál es, cuántos nombres trae y en cuántas piezas está marcada la etiqueta. Aparece también cuando el archivo es otro pero el molde es el mismo con otro diseño adentro, porque el molde se reconoce por sus piezas.',
    como: 'Mirá el aviso de la configuración guardada.',
  },
  'pieza-b-sugerida-aplicar': {
    nombre: 'Aplicar la configuración guardada',
    que: 'Pone de una los nombres de las piezas y dónde va la etiqueta en cada una, tal como los habías dejado. No se aplica sola nunca: entra recién cuando tocás este botón. Si el molde todavía se está leyendo, queda esperando y entra sola en cuanto termina. Después conviene abrir «Nombrar piezas» y mirar si quedó bien.',
    como: 'Aplicá la configuración guardada.',
  },
  'pieza-b-configuracion': {
    nombre: 'Guardar configuración',
    que: 'Abre la configuración guardada de este molde: acá se guarda con un nombre cómo quedó (dónde va la etiqueta en cada pieza y el nombre de las piezas) y se vuelve a aplicar en otro pedido. El molde se reconoce por sus piezas, así que el mismo molde con otro diseño adentro también la encuentra. Son tuyas: cada uno ve las suyas.',
    como: 'Abrí la configuración del molde.',
  },
  'molde-cfg-sugerida': {
    nombre: 'Este molde ya lo configuraste',
    que: 'Aviso de que hay una configuración TUYA guardada que le calza a este molde: dice cuál es y cuánto trae (en cuántas piezas está marcada la etiqueta y cuántos nombres). Aparece también cuando el archivo es otro pero el molde es el mismo con otro diseño adentro, porque el molde se reconoce por sus piezas.',
    como: 'Mirá el aviso de la configuración guardada.',
  },
  'molde-cfg-sugerida-aplicar': {
    nombre: 'Aplicar la configuración que ya tenías',
    que: 'Pone de una los nombres de las piezas y dónde va la etiqueta en cada una, tal como los habías dejado. No se aplica sola nunca: entra recién cuando tocás este botón, y después conviene mirar el visor y corregir a mano lo que no haya quedado bien.',
    como: 'Aplicá la configuración guardada.',
  },
  'molde-cfg-nombre': {
    nombre: 'Nombre de la configuración',
    que: 'Con este nombre se va a reconocer después, en la lista. Conviene decir de qué molde es y qué variante («Camiseta jugador · cuello redondo»).',
    como: 'Escribí un nombre para reconocerla después.',
  },
  'molde-cfg-guardar': {
    nombre: 'Guardar esta',
    que: 'Guarda la configuración de este molde con ese nombre. Queda en la base, atada al archivo: el molde se puede borrar con el pedido y la configuración sigue.',
    como: 'Guardá la configuración de este molde.',
  },
  'molde-cfg-partes': {
    nombre: 'Aplicar además',
    que: 'La etiqueta y los nombres de las piezas se aplican siempre. Lo demás —grupos y variables, telas, planilla, talle de guía, borde y producción— es del pedido y entra sólo si lo tildás.',
    como: 'Tildá lo que además querés traer de esa configuración.',
  },
  'molde-cfg-aplicar': {
    nombre: 'Aplicar',
    que: 'Le pone a este molde el nombrado, los grupos, las variables y las telas de esa configuración. No se aplica sola: la elegís vos y después mirás en el visor si acomodó bien.',
    como: 'Aplicá esa configuración y fijate en el visor si acomodó bien.',
  },
  'molde-cfg-actualizar': {
    nombre: 'Actualizar esta configuración',
    que: 'Guarda cómo está el molde AHORA —los nombres de las piezas y dónde va la etiqueta en cada una— dentro de una configuración que ya tenías, en vez de crear otra. Es lo que conviene cuando corregís un detalle: si no, quedan tres o cuatro casi iguales y no se sabe cuál es la buena. Lo que tenía guardado antes se pierde, y se pregunta antes.',
    como: 'Guardá los cambios en la configuración que ya tenías.',
  },
  'molde-cfg-borrar': {
    nombre: 'Borrar configuración',
    que: 'Borra la configuración guardada. No toca ningún molde: es sólo la receta.',
    como: 'Borrá la configuración guardada.',
  },
  'molde-guia': {
    nombre: 'Talle de guía',
    que: 'El talle de referencia: sobre él se nombran las piezas y desde él se copian a los demás. Conviene uno del medio de la curva (M, 38…).',
    como: 'Elegí el talle de guía.',
  },
  // ══ VENTANAS DE CONFIGURACIÓN (estaban sin marcar: la ayuda no las reconocía) ════════════════
  'modal:crear nuevo molde': {
    nombre: 'Crear Nuevo Molde',
    que: 'Crea la moldería vacía: sólo se le pone el nombre. El archivo del molde se sube después, ya adentro.',
    como: 'Escribí el nombre y tocá «Crear Molde».',
    ventana: { contenido: 'El nombre de la moldería nueva',
               botones: ['Cancelar', 'Crear Molde'], cuando: 'al crear una moldería', paso: 'config' },
  },
  'modal:talle de guia': {
    nombre: 'Talle de Guía',
    que: 'El talle con el que se mira y se etiqueta el molde. Conviene uno del medio de la curva: sobre él se nombran las piezas y desde él se copian a los demás.',
    como: 'Elegí el talle con el que querés trabajar.',
    ventana: { contenido: 'Todos los talles del molde, para elegir uno',
               botones: [], cuando: 'al cambiar el talle de guía', paso: 'config' },
  },
  'modal:piezas del grupo': {
    nombre: 'Piezas del grupo',
    que: 'Las piezas que quedaron en ese grupo, para revisarlas o seguir asignando.',
    como: 'Revisá las piezas del grupo.',
    ventana: { contenido: 'La lista de piezas de ese grupo',
               botones: ['Asignar piezas'], cuando: 'al terminar de nombrar un grupo', paso: 'config' },
  },
  'modal:vista previa del molde': {
    nombre: 'Vista previa del molde',
    que: 'El molde en grande, para mirarlo de cerca antes de seguir.',
    como: 'Mirá el molde y cerrá la ventana cuando termines.',
    ventana: { contenido: 'El dibujo del molde a pantalla completa',
               botones: ['Cerrar'], cuando: 'al ampliar el molde', paso: 'config' },
  },
  'modal:confirmar tizada de sublimacion': {
    nombre: 'Confirmar Tizada de Sublimación',
    que: 'El último repaso antes de mandar a fabricar: qué se va a generar con lo cargado.',
    como: 'Revisá lo que dice y confirmá.',
    ventana: { contenido: 'El resumen de lo que se va a fabricar',
               botones: ['Cancelar', 'Confirmar'], cuando: 'antes de armar la tizada', paso: 'planilla' },
  },
  // La lista de talles de esa ventana: son intercambiables (cada uno elige el suyo).
  'molde-guia-talles': {
    opciones: true,
    nombre: 'Talles del molde',
    que: 'Todos los talles que trae el molde. El elegido es con el que vas a ver y etiquetar las piezas.',
    como: 'Elegí el talle de guía.',
  },

  // ══ REGISTRO DEL SISTEMA (Configuración) ════════════════════════════════════════════════════
  // Nació de una actualización que dijo «falló» sin decir por qué: el motivo estaba en un archivo
  // del servidor publicado, al que sólo se llega por SSH (pedido del usuario, 2026-09-01).
  'cfg-registro': {
    nombre: 'Registro del sistema',
    que: 'Todo lo que falla queda anotado con su motivo, y además está la consola entera del servidor (lo mismo que se ve en la ventana negra) con la fecha y la hora de cada línea. Sirve para saber qué pasó sin entrar al servidor. No guarda nada de tu trabajo.',
    como: 'Entrá a «Registro del sistema».',
  },
  'registro-donde': {
    opciones: true,
    nombre: 'De qué sistema',
    que: 'El registro de ESTA máquina o el del sistema publicado en internet. El del publicado es el que antes no se podía ver desde acá.',
    como: 'Elegí de qué sistema querés ver el registro.',
  },
  'registro-filtro': {
    opciones: true,
    nombre: 'Qué mostrar',
    que: 'Filtra lo anotado: todo, sólo las fallas, los avisos (algo que no salió como se esperaba pero no rompió nada) o los movimientos normales.',
    como: 'Elegí qué querés ver.',
  },
  'registro-evento': {
    nombre: 'Lo anotado',
    que: 'Cada línea dice QUÉ pasó y POR QUÉ, con la hora. Tocándola se abren los datos de esa vez (versión, archivo, cuánto tardó).',
    como: 'Tocá una línea para ver el detalle.',
  },
  'registro-consola': {
    nombre: 'Consola del servidor',
    que: 'Lo mismo que se ve en la ventana negra del servidor, línea por línea y con la fecha y la hora de cada una. Queda guardado en un archivo de texto, así que sigue estando después de cerrar la ventana — y también cuando el sistema corre sin ninguna ventana.',
    como: 'Mirá la consola del servidor.',
  },
  'registro-buscar': {
    nombre: 'Buscar en la consola',
    que: 'Deja sólo las líneas que dicen lo que escribas. Sirve para encontrar una falla puntual entre miles de líneas: el nombre de un archivo, una hora, la palabra «error».',
    como: 'Escribí qué buscar en la consola.',
  },
  'registro-cuantas': {
    nombre: 'Cuántas líneas',
    que: 'Cuántas líneas de las últimas se traen. Más líneas es ir más atrás en el tiempo; menos, que cargue más rápido.',
    como: 'Elegí cuántas líneas mostrar.',
  },
  'registro-ayudante': {
    nombre: 'Detalle de la última actualización',
    que: 'Lo que fue haciendo el ayudante paso por paso, con la hora de cada cosa: respaldar, descomprimir, levantar y comprobar. Si algo se cortó, acá se ve exactamente dónde.',
    como: 'Mirá el detalle de la última actualización.',
  },
  'registro-refrescar': {
    nombre: 'Actualizar',
    que: 'Vuelve a leer el registro. Sirve mientras algo está pasando (una actualización, por ejemplo).',
    como: 'Tocá «↻ Actualizar».',
  },
  'registro-limpiar': {
    nombre: 'Vaciar el registro',
    que: 'Borra lo anotado hasta ahora. Se usa después de resolver un problema, para que lo que aparezca de acá en más sea nuevo.',
    como: 'Tocá «Vaciar el registro».',
  },
  'registro-volver': {
    nombre: 'Volver a Configuración',
    que: 'Sale del registro y vuelve al panel de Configuración.',
    como: 'Tocá «⬅ Configuración».',
  },

  'ajuste-volver': {
    nombre: 'Volver',
    que: 'Sale de los ajustes del molde y vuelve a la lista.',
    como: 'Tocá «Volver».',
  },

  // ══ LOS 10 AJUSTES DE UNA MOLDERÍA ══════════════════════════════════════════════════════════
  // 🔴 FALTABAN TODOS (auditoría de Configuración, 2026-09-01). Se salvaban de casualidad, porque
  // el cartel caía al texto del botón; pero esos botones son ÍCONO + título, así que tocando el
  // ícono el tutorial decía «Tocá "Aa"» y, al arreglar eso, quedaba en «Tocá acá.». Son la puerta
  // de entrada a TODA la configuración de un molde: sin explicación no hay tutorial de config.
  // Los textos salen de la propia pantalla (el título y el renglón gris de cada tarjeta).
  'ajuste-molderia': {
    nombre: 'Moldería',
    que: 'El archivo del molde y el nombre de cada pieza. Es lo primero: sin las piezas nombradas, los demás ajustes quedan apagados.',
    como: 'Entrá a «Moldería».',
  },
  'ajuste-variables': {
    nombre: 'Variables',
    que: 'Los grupos de piezas y las variables de la prenda (cuello redondo, cuello V…). El talle va aparte.',
    como: 'Entrá a «Variables».',
  },
  'ajuste-etiqueta': {
    nombre: 'Etiqueta',
    que: 'La etiqueta que se estampa en cada pieza: qué dice, dónde va, en qué piezas, con qué color y tamaño.',
    como: 'Entrá a «Etiqueta».',
  },
  'ajuste-planilla': {
    nombre: 'Planilla',
    que: 'Qué columna de la planilla del pedido es el talle, cuál el nombre, cuál el número…',
    como: 'Entrá a «Planilla».',
  },
  'ajuste-nestingsel': {
    nombre: 'Nesting',
    que: 'Con qué acomodo se arma la tizada de este molde: separación entre piezas y si pueden girar.',
    como: 'Entrá a «Nesting».',
  },
  'ajuste-telas': {
    nombre: 'Telas asignadas',
    que: 'Qué telas del registro puede usar este molde. Las demás no aparecen al armar el pedido.',
    como: 'Entrá a «Telas asignadas».',
  },
  'ajuste-borde': {
    nombre: 'Borde de corte',
    que: 'Si las piezas llevan borde de corte, de qué color y de qué tamaño (en mm).',
    como: 'Entrá a «Borde de corte».',
  },
  'ajuste-diseno': {
    nombre: 'Plantilla',
    que: 'La medida de cada pieza y la carga del diseño que se estampa sobre ella.',
    como: 'Entrá a «Plantilla».',
  },
  'ajuste-editable': {
    nombre: 'Editable',
    que: 'Los objetos de la capa «Editable» del diseño: se pueden mover, rotar y escalar sin tocar el archivo.',
    como: 'Entrá a «Editable».',
  },
  'ajuste-terminologia': {
    nombre: 'Nombres',
    que: 'Cómo llama el sistema al talle y a la prenda en este molde. Sólo cambia los carteles.',
    como: 'Entrá a «Nombres».',
  },
  // La grilla de molderías, marcada ENTERA: el tutorial dice «abrí la que vas a usar» y la elige
  // quien lo sigue (marcar una tarjeta suelta mandaba a abrir la moldería equivocada).
  'molde-grilla': {
    nombre: 'Molderías',
    que: 'Cada tarjeta es una moldería del sistema, con su molde, su diseño y su planilla.',
    como: 'Abrí la moldería con la que vas a trabajar: tocá su tarjeta.',
  },
  'molde-volver': {
    nombre: 'Volver a las molderías',
    que: 'Sale de esta moldería y vuelve a la lista de todas.',
    como: 'Tocá «⬅ Molderías».',
  },

  // ══ MI MOLDE (desde el pedido) ══════════════════════════════════════════════════════════════
  'mimolde-crear': {
    nombre: 'Crear mi molde',
    que: 'Arranca un molde propio desde el pedido, sin pasar por Configuración.',
    como: 'Tocá para crear tu molde.',
  },
  'mimolde-nombre': {
    nombre: 'Nombre de mi molde',
    que: 'Cómo lo vas a reconocer en «Mis artículos».',
    como: 'Escribí el nombre.',
  },
  'mimolde-archivo': {
    nombre: 'Archivo de mi molde',
    que: 'El .ai, .pdf o .dxf con las piezas y los talles.',
    como: 'Elegí el archivo del molde.',
  },
  'mimolde-configurar': {
    nombre: 'Configurar mi molde',
    que: 'Abre lo mínimo para poder pedirlo: decirle qué es cada pieza.',
    como: 'Tocá «Configurar».',
  },

  // ══ PIEZAS, VARIABLES Y GRUPOS ══════════════════════════════════════════════════════════════
  'variantes-panel': {
    nombre: 'Talles del molde',
    que: 'Acá se definen los talles. Si el molde vino sin ellos, el panel se pone naranja: hasta resolverlo el molde no se puede usar.',
    como: 'Revisá los talles del molde.',
  },
  'variantes-modo': {
    nombre: 'Cómo vienen los talles',
    que: 'Dos casos: que cada talle venga en su propia capa, o que venga todo junto en una sola.',
    como: 'Elegí cómo vienen los talles en el archivo.',
  },
  'variantes-aplicar': {
    nombre: 'Aplicar los talles',
    que: 'Confirma el reparto de talles y lo guarda en el molde.',
    como: 'Tocá «Aplicar».',
  },
  'var-pasos': {
    nombre: 'Pasos de Variables',
    que: 'Son 2 pasos: 1) nombrar las piezas · 2) grupos y variables. En ese orden: sin nombres no se pueden armar variables.',
    como: 'Mirá en qué paso estás.',
  },
  'var-nombre': {
    nombre: 'Nombre de la variable',
    que: 'Una variable es una combinación de piezas: «manga corta», «musculosa», «con capucha».',
    como: 'Escribí el nombre de la variable.',
  },
  'var-elegir-piezas': {
    nombre: 'Piezas de la variable',
    que: 'Qué piezas entran en esa combinación. Se tocan sobre el visor.',
    como: 'Elegí las piezas que lleva.',
  },
  'var-listo': {
    nombre: 'Listo (variable)',
    que: 'Guarda la variable con las piezas elegidas.',
    como: 'Tocá «Listo».',
  },
  'grupo-nombre': {
    nombre: 'Nombre del grupo',
    que: 'Un grupo junta las variables que compiten entre sí (por ejemplo, los tipos de manga).',
    como: 'Escribí el nombre del grupo.',
  },
  'nombre-pieza-input': {
    nombre: 'Nombre de la pieza',
    que: 'Se eligen piezas en el visor y se les escribe qué son («Frente», «Manga»). Si elegís varias iguales, se numeran solas: Frente 1, Frente 2…',
    como: 'Escribí qué es esa pieza.',
  },
  'nombre-pieza-ok': {
    nombre: 'Confirmar el nombre',
    que: 'Le pone ese nombre a las piezas elegidas.',
    como: 'Confirmá el nombre.',
  },
  'nombres-guardar': {
    nombre: 'Guardar los nombres',
    que: 'Guarda el nombrado de piezas del molde.',
    como: 'Tocá «Guardar».',
  },
  'pieza-agregar': {
    nombre: 'Agregar pieza',
    que: 'Suma una pieza al molde. Ojo: agregar una pieza renumera a las demás, y el sistema rehace ese mapeo.',
    como: 'Tocá «Agregar una pieza».',
  },
  'agrupar-activar': {
    nombre: 'Agrupar piezas',
    que: 'Es decir cuál es la MISMA pieza en cada talle: el Frente de la S, el de la M, el de la L… Sin eso el sistema no sabe que son la misma y la tizada sale mal.',
    como: 'Tocá «Nombrar piezas».',
  },
  'agrupar-nombre': {
    nombre: 'Nombre del grupo de piezas',
    que: 'El nombre que van a compartir esa pieza en todos los talles.',
    como: 'Escribí el nombre.',
  },
  'agrupar-confirmar': {
    nombre: 'Confirmar el agrupado',
    que: 'Deja emparejada esa pieza entre todos los talles.',
    como: 'Confirmá el agrupado.',
  },
  'varpz-asignar': {
    nombre: 'Asignar piezas a la variable',
    que: 'Reparte a mano las piezas entre las variables, cuando el molde trae todo junto.',
    como: 'Asigná las piezas.',
  },
  'varpz-nombre': {
    nombre: 'Nombre (variable por piezas)',
    que: 'Cómo se va a llamar esa variable en el pedido.',
    como: 'Escribí el nombre.',
  },
  'varpz-aplicar': {
    nombre: 'Aplicar (variable por piezas)',
    que: 'Guarda el reparto de piezas.',
    como: 'Tocá «Aplicar».',
  },

  // ══ DISEÑO SOBRE EL MOLDE ═══════════════════════════════════════════════════════════════════
  'diseno-capas': {
    nombre: 'Capas que debe traer el arte',
    que: 'La lista de capas que tiene que traer el .ai del diseño. El diseñador las copia tal cual: los nombres tienen que coincidir.',
    como: 'Mirá las capas que necesita el arte.',
  },
  'diseno-mapear': {
    nombre: 'Mapear diseño al molde',
    que: 'Empareja cada mesa del arte con su pieza. Si en el .ai cada mesa dice el nombre de la pieza, el sistema lo hace solo. Se guarda por variable.',
    como: 'Tocá «Mapear diseño al molde».',
  },
  'diseno-guardar': {
    nombre: 'Guardar el mapeo',
    que: 'Guarda qué mesa del arte va en cada pieza.',
    como: 'Tocá «Guardar».',
  },

  // ══ ETIQUETA ════════════════════════════════════════════════════════════════════════════════
  'etq-activo': {
    nombre: 'Etiqueta encendida',
    que: 'La etiqueta es el textito que se imprime en cada pieza para saber, ya cortada, de qué prenda es. Se puede apagar entera, y también en las piezas donde molesta.',
    como: 'Prendé o apagá la etiqueta.',
  },
  'etq-mostrar': {
    nombre: 'Qué dice la etiqueta',
    que: 'El talle, el nombre de la pieza y el número de prenda.',
    como: 'Elegí qué muestra la etiqueta.',
  },
  'etq-piezas': {
    nombre: 'Piezas (etiqueta)',
    que: 'Tocá una pieza y el visor la muestra en todos sus talles: ahí marcás, sobre el borde, dónde va su etiqueta. La posición es de la PIEZA: donde la pongas en el Frente, queda en el Frente de todos los talles.',
    como: 'Elegí la pieza y marcá dónde va su etiqueta.',
  },
  'etq-guardar': {
    nombre: 'Guardar la etiqueta',
    que: 'Guarda la configuración y las posiciones de la etiqueta.',
    como: 'Tocá «Guardar».',
  },

  // ══ BORDE DE CORTE ══════════════════════════════════════════════════════════════════════════
  'borde-activo': {
    nombre: 'Borde de corte',
    que: 'La línea que se imprime alrededor de cada pieza para guiar el corte. Se imprime: por eso tiene color y grosor propios.',
    como: 'Prendé o apagá el borde de corte.',
  },
  'borde-color': {
    nombre: 'Color del borde',
    que: 'En CMYK, igual que el resto de la impresión.',
    como: 'Elegí el color del borde.',
  },
  'borde-tamano': {
    nombre: 'Grosor del borde',
    que: 'En milímetros. Si tu taller corta con plotter o a mano, esto es lo que sigue la tijera.',
    como: 'Poné el grosor del borde.',
  },
  'borde-guardar': {
    nombre: 'Guardar el borde',
    que: 'Guarda el borde de corte de este molde.',
    como: 'Tocá «Guardar».',
  },

  // ══ TELAS ═══════════════════════════════════════════════════════════════════════════════════
  'telas-conexion': {
    nombre: 'Conexión con el stock',
    que: 'Las telas vienen del sistema de stock; acá se revisa que la conexión ande.',
    como: 'Revisá la conexión con el stock.',
  },
  'telas-actualizar': {
    nombre: 'Actualizar telas',
    que: 'Vuelve a traer la lista de telas desde el sistema de stock.',
    como: 'Tocá «Actualizar».',
  },
  'telas-margen': {
    nombre: 'Margen de la mesa',
    que: 'La mesa de trabajo de cada tela es su medida menos este margen (3 cm si no lo cambiás). Vale para todas las telas que no tengan un valor puesto a mano: cambiarlo acá les cambia la mesa a todas ellas en el acto.',
    como: 'Escribí cuántos cm menos que la tela tiene la mesa.',
  },
  'telas-lista': {
    nombre: 'Lista de telas',
    que: 'Cada tela muestra su medida (dato del sistema de stock) y la MESA DE TRABAJO, que es la que usa la tizada para acomodar. La mesa sale sola: la medida menos el margen. Si una tela necesita otra, escribila a mano y esa manda («a mano»); con la × vuelve al automático. Si está mal, la tizada sale mal.',
    como: 'Revisá la mesa de cada tela.',
  },
  'telas-tope': {
    nombre: 'Tope de telas por prenda',
    que: 'Cuántas telas distintas puede combinar una misma prenda en un pedido. Ej.: 2 = el operario podrá usar hasta dos.',
    como: 'Poné el tope de telas.',
  },
  'telas-variable': {
    nombre: 'Variable (telas)',
    que: 'Se trabaja de a una variable: el visor muestra sólo sus piezas y no las del molde entero.',
    como: 'Elegí la variable.',
  },
  'telas-panel': {
    nombre: 'Asignar telas',
    que: 'Son tres pasos: 1) elegí la tela de la lista · 2) tocá las piezas en el molde · 3) «Asignar». Si no tocás ninguna pieza, la tela va a todas.',
    como: 'Asigná la tela a las piezas.',
  },
  'telas-seleccionar': {
    nombre: 'Elegir tela',
    que: 'La tela que vas a poner en las piezas que marques.',
    como: 'Elegí la tela.',
  },
  'telas-mostrar': {
    nombre: 'Telas sobre el molde',
    que: 'Se ve, sobre el molde, qué tela quedó en cada pieza. El cuello y las tapacosturas suelen ir en RIB.',
    como: 'Mirá qué tela quedó en cada pieza.',
  },
  'telas-modal-buscar': {
    nombre: 'Buscar tela',
    que: 'Filtra la lista de telas por nombre.',
    como: 'Buscá la tela.',
  },
  'telas-modal-asignar': {
    nombre: 'Confirmar la tela',
    que: 'Deja esa tela asignada a las piezas elegidas.',
    como: 'Tocá «Asignar».',
  },

  // ══ NESTING ═════════════════════════════════════════════════════════════════════════════════
  'nesting-nuevo': {
    nombre: 'Nuevo acomodo',
    que: 'Conviene tener dos o tres: «estándar», «apretado» para ahorrar tela y «sin giro» para telas con pelo o rayas. Girar una pieza en una tela con dirección la arruina.',
    como: 'Tocá para crear un acomodo.',
  },
  'nesting-nombre': {
    nombre: 'Nombre del acomodo',
    que: 'Con este nombre lo vas a elegir después en cada molde.',
    como: 'Escribí el nombre del acomodo.',
  },
  'nesting-alto': {
    nombre: 'Alto de la mesa',
    que: 'Hasta dónde puede crecer la hoja de tizada.',
    como: 'Poné el alto de la mesa.',
  },
  'nesting-guardar': {
    nombre: 'Guardar el acomodo',
    que: 'Guarda las reglas de nesting.',
    como: 'Tocá «Guardar».',
  },
  'nsel-elegir': {
    nombre: 'Acomodo del molde',
    que: 'Cuál de los acomodos usa este molde. Se arman en Configuración › Reglas de Nesting.',
    como: 'Elegí el acomodo.',
  },
  'nsel-grupos': {
    nombre: 'Grupos de tizada',
    que: 'Es cuando dos molderías se arman juntas en la misma mesa (camiseta + short). Un molde que no está en ningún grupo se arma en su propia tizada.',
    como: 'Armá los grupos de tizada.',
  },

  // ══ PLANILLAS Y REGLAS (configuración) ══════════════════════════════════════════════════════
  'col-nueva': {
    nombre: 'Nueva planilla',
    que: 'Se pueden tener varias: una para camisetas con nombre y número, otra para prendas lisas. Después cada molde elige cuál usa.',
    como: 'Tocá para crear una planilla.',
  },
  'col-guardar': {
    nombre: 'Guardar la planilla',
    que: 'Las columnas se ordenan arrastrando, y cada una usa una REGLA que dice qué se puede escribir.',
    como: 'Tocá «Guardar».',
  },
  'regla-nueva': {
    nombre: 'Nueva regla',
    que: 'Lo importante es «qué hace»: puede elegir el talle, elegir el diseño, ESTAMPARSE en la prenda, o cambiar qué piezas entran. Ej.: un toggle «capucha = sí» agrega las piezas de la capucha.',
    como: 'Tocá para crear una regla.',
  },
  'regla-nombre': {
    nombre: 'Nombre de la regla',
    que: 'Es el título de la columna que va a ver el operario.',
    como: 'Escribí el nombre de la regla.',
  },
  'regla-guardar': {
    nombre: 'Guardar la regla',
    que: 'Guarda el campo para poder usarlo en cualquier planilla.',
    como: 'Tocá «Guardar».',
  },
  'mplanilla-elegir': {
    nombre: 'Planilla del molde',
    que: 'Un molde que no lleva número no tiene por qué mostrar esa columna. En el pedido aparecen sólo las columnas que los moldes elegidos usan de verdad.',
    como: 'Elegí la planilla de este molde.',
  },
  'mplanilla-guardar': {
    nombre: 'Guardar la planilla del molde',
    que: 'Deja esa planilla asociada al molde.',
    como: 'Tocá «Guardar».',
  },

  // ══ FUENTES ═════════════════════════════════════════════════════════════════════════════════
  'fuentes-subir': {
    nombre: 'Subir fuente',
    que: 'Carga una tipografía para estampar nombres y números.',
    como: 'Subí el archivo de la fuente.',
  },
  'fuentes-probar': {
    nombre: 'Probar texto',
    que: 'Escribiendo acá se ve cómo queda ese texto en todas las fuentes cargadas, sin generar una tizada de prueba. También avisa si a la fuente le falta alguna letra.',
    como: 'Escribí un texto de prueba.',
  },

  // ══ USUARIOS ════════════════════════════════════════════════════════════════════════════════
  'usuarios-tabs': {
    nombre: 'Usuarios / Roles / Permisos',
    que: 'Son tres listas: los USUARIOS (las personas), los ROLES (paquetes de permisos) y los PERMISOS que existen. Conviene armar primero el rol y después las personas.',
    como: 'Elegí la lista que querés ver.',
  },
  'usuarios-nuevo': {
    nombre: 'Nuevo usuario',
    que: 'Da de alta a una persona y le asigna su rol.',
    como: 'Tocá para crear un usuario.',
  },
  'usuarios-roles': {
    nombre: 'Roles',
    que: 'Un rol es un paquete de permisos que después se le da a varias personas.',
    como: 'Entrá a los roles.',
  },
  'usuarios-ver-pass': {
    nombre: 'Ver la contraseña',
    que: 'Muestra u oculta lo que se está escribiendo en el campo de contraseña.',
    como: 'Tocá el ojo para ver la contraseña.',
  },
  'rol-permisos': {
    nombre: 'Permisos del rol',
    que: 'Qué puede hacer ese rol dentro del sistema.',
    como: 'Marcá los permisos del rol.',
  },

  // ══ PUBLICACIÓN ═════════════════════════════════════════════════════════════════════════════
  'pub-version': {
    nombre: 'Número de versión',
    que: 'La etiqueta con la que va a quedar la versión publicada. La escribe el usuario.',
    como: 'Escribí el número de versión.',
  },
  'pub-cuando': {
    nombre: 'Cuándo se instala',
    que: 'Ahora, en un rato, o un día y hora exactos. El corte dura alrededor de un minuto y, si algo falla, el servidor vuelve solo a la versión anterior. Los moldes y pedidos no viajan.',
    como: 'Elegí cuándo se instala.',
  },
  'pub-publicar': {
    nombre: 'Publicar',
    que: 'Arma el paquete y lo manda al servidor de internet.',
    como: 'Tocá «Publicar».',
  },

  // ══ TERMINOLOGÍA ════════════════════════════════════════════════════════════════════════════
  'term-molde': {
    nombre: 'Cómo se llama la prenda',
    que: 'Cambia cómo llama el sistema a la PRENDA en este molde. Sólo cambia los carteles, no el funcionamiento.',
    como: 'Escribí cómo querés que se llame.',
  },
  'term-variante': {
    nombre: 'Cómo se llama el talle',
    que: 'Cambia cómo llama el sistema al TALLE. Si en tu rubro se dice «medida», que lo diga.',
    como: 'Escribí cómo querés que se llame.',
  },
  'term-guardar': {
    nombre: 'Guardar los nombres',
    que: 'Guarda cómo se llaman las cosas en este molde.',
    como: 'Tocá «Guardar».',
  },
};

/**
 * LA SECUENCIA DEL PEDIDO — qué va antes de qué.
 *
 * 🔴 POR QUÉ EXISTE (lo pidió el usuario y tenía razón): una grabación sólo tiene los pasos que
 * la persona LLEGÓ A HACER. Si al grabar ya tenía el diseño cargado, no tocó nada ahí → el
 * tutorial no tenía ese paso → al reproducirlo **no llevaba a nadie a elegir el diseño**, aunque
 * sea imprescindible para lo que viene después.
 *
 * Acá está escrito el orden real del trabajo. Al reproducir, el motor mira hasta dónde llega la
 * grabación y **completa solo** las etapas anteriores que falten. Y como cada etapa trae su
 * `listo`, a quien ya la tenga resuelta **no se le muestra**: se completa lo que falta, no se
 * repite lo hecho.
 *
 * Agregar una etapa nueva al pedido ⇒ agregarla acá, o los tutoriales van a saltearla.
 */
export const SECUENCIA = [
  { paso: 'diseno', ancla: 'pedido-diseno-lista',
    listo: (E) => E.pedido.nDisenos > 0 },
  { paso: 'moldes', ancla: 'pedido-variables',
    listo: (E) => E.pedido.nDisenos > 0 && E.pedido.sinVariable === 0 },
  { paso: 'arte', ancla: 'arte-cargar',
    listo: (E) => E.pedido.artesTotal > 0 && E.pedido.artesCargadas >= E.pedido.artesTotal },
  // Las telas viven dentro del paso del arte, pero son una etapa propia: sin ellas el pedido no
  // avanza, y es de lo que más se olvida la gente.
  { paso: 'arte', ancla: 'arte-telas', clave: 'telas',
    listo: (E) => E.pedido.artesCargadas > 0 && E.pedido.telasFaltan === 0 },
  { paso: 'planilla', ancla: 'planilla-tabla',
    listo: (E) => E.pedido.nFilas > 0 },
  { paso: 'resultados', ancla: 'planilla-enviar', clave: 'enviar',
    listo: (E) => E.pedido.hayResultados },
];

/** Lo que sabe el sistema de un elemento. Si no está en el diccionario, se arma con lo que el
 *  propio botón muestra en pantalla: peor cartel, pero el tutorial igual se puede grabar. */
/** Las columnas de la planilla que el sistema sabe explicar (las de un molde propio no están). */
export const COLUMNAS_CONOCIDAS = Object.keys(DICCIONARIO)
  .filter((k) => k.startsWith('col:'))
  .map((k) => ({ id: k.slice(4), nombre: DICCIONARIO[k].nombre || k.slice(4) }));

export function explicar(ancla, etiqueta) {
  const d = DICCIONARIO[ancla];
  if (d) return d;
  // 🔴 UN CARTEL NUNCA MUESTRA UN ANCLA. Sin entrada ni etiqueta se caía al identificador crudo y
  // el tutorial decía «Tocá «txt:camiseta de futbol · 7 pzas#pedido-variables»» (se vio en el
  // tutorial «2 colores»). Del ancla sólo se rescata la parte legible: el nombre del control.
  const legible = String(ancla || '').startsWith('txt:')
    ? partirAncla(ancla).nombre
    : '';
  const nom = (etiqueta || legible || '').trim();
  return { nombre: nom, que: '', como: nom ? `Tocá «${nom}».` : 'Tocá acá.' };
}

/**
 * LA EXPLICACIÓN DE UNA COLUMNA DE LA PLANILLA — por su ROL, no por su id.
 *
 * 🔴 POR QUÉ: las columnas las arma cada taller, así que el ID cambia («Diseño» es `dise_o` en la
 * planilla del usuario, y hay dos columnas de talle: `talle` y `talle_short`). El diccionario las
 * tenía indexadas por id, así que la explicación existía y NO SE USABA: el cartel caía a la
 * etiqueta de lo que se tocó y salía **«Tocá "▾"»** — el símbolo del desplegable (auditoría
 * 2026-08-31, los dos tutoriales reales). El ROL sí es estable: es el que usa el motor.
 */
export function explicarColumna(id, role, label) {
  const propia = DICCIONARIO['col:' + id];
  if (propia) return propia;
  const porRol = role && DICCIONARIO['col:' + role];
  // el nombre que se muestra es SIEMPRE el de la pantalla («Talle short», no «Talle»)
  if (porRol) return { ...porRol, nombre: label || porRol.nombre };
  const nom = label || id;
  return { nombre: nom, que: 'Una columna de la planilla de este pedido.',
           como: `Cargá lo que va en la columna «${nom}».` };
}

/**
 * ¿ESTE BOTÓN ES DE UNA VENTANA QUE PUEDE NO APARECER? Devuelve el título de esa ventana.
 *
 * 🔴 EL CASO REAL: el tutorial «Camiseta» tiene un paso «Tocá "Entendido"» que es el botón del
 * aviso «Perfil de color del diseño». A quien sigue el tutorial puede no salirle ese aviso: el
 * paso quedaba 5 s en «No encuentro ese lugar en pantalla» y había que seguir a mano. Con esto el
 * motor sabe que el paso VIVE EN esa ventana y lo dice (los grabados desde 2026-08-31 ya guardan
 * `ventana`; esto arregla los anteriores, al reproducir).
 */
export function modalDeBoton(etiqueta) {
  // se compara con la MISMA normalización que usa el localizador (una sola forma de comparar
  // nombres en todo el sistema de ayuda): sin acentos, sin espacios de más, en minúscula
  const e = normalizar(etiqueta);
  if (!e) return '';
  for (const [k, d] of Object.entries(DICCIONARIO)) {
    if (!k.startsWith('modal:') || !d.ventana) continue;
    if ((d.ventana.botones || []).some((b) => normalizar(b) === e)) return d.nombre || '';
  }
  return '';
}

export default DICCIONARIO;

/**
 * LA FICHA DE UNA VENTANA EMERGENTE — con qué DIBUJARLA (y qué explicar de ella).
 * El editor de tutoriales muestra estas fichas como vista previa: el usuario elige la ventana
 * MIRÁNDOLA, no leyendo un nombre que no le dice nada.
 */
export function fichaVentana(titulo) {
  const t = String(titulo || '');
  const clave = 'modal:' + t.normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ').trim().toLowerCase().slice(0, 48);
  const d = DICCIONARIO[clave] || {};
  const v = d.ventana || {};
  return {
    nombre: d.nombre || t,
    que: d.que || '',
    como: d.como || '',
    contenido: v.contenido || '',
    botones: Array.isArray(v.botones) ? v.botones : [],
    cuando: v.cuando || '',
    paso: v.paso || '',
    trabajo: !!v.trabajo || (AVISOS_CONOCIDOS.cargas || []).includes(t),
  };
}
