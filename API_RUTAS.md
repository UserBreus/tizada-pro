# API — Rutas de TIZADA PRO

Backend Flask (`servidor.py`). **Base URL:** `http://localhost:8050` (puerto = env `PORT`, default 8050).
Total: **117 endpoints**. Generado automáticamente del código.

> Params: `q=` query string · `form=` multipart/form · `file=` archivo subido · `body{}` = JSON. Los `<...>` en el path son variables de ruta.

## API externa (WMS)
- `GET https://user.com.uy/api/external/telas` — registro de telas. Key en `config_externo.json` (`telas_api_key`, gitignoreado).

## Sistema

| Método | Ruta | Descripción | Params |
|---|---|---|---|
| GET | `/` |  | — |
| GET | `/admin` |  | — |
| GET | `/api/config` |  | — |
| POST | `/api/config` |  | body: asignacion, espaciado_mm, margen_mm, mesas, rotacion |
| GET | `/api/estado_general` |  | — |
| GET | `/api/salud` | Estado del servidor — LO MIRA EL ACTUALIZADOR para decidir si una publicación salió bien (si esto no responde `ok`, vuelve sola a la versión anterior). También  | — |
| GET | `/favicon.ico` |  | — |

## Fuentes / Catálogo

| Método | Ruta | Descripción | Params |
|---|---|---|---|
| POST | `/api/catalogo_grupos/agregar` |  | body: nombre |
| POST | `/api/catalogo_grupos/eliminar` |  | body: nombre |
| GET | `/api/catalogo_piezas` |  | — |
| POST | `/api/catalogo_piezas/agregar` |  | body: grupo, nombre |
| POST | `/api/catalogo_piezas/eliminar` |  | body: grupo, nombre |
| POST | `/api/fuente` |  | file: archivo |
| GET | `/api/fuente/archivo/<path:nombre>` | Sirve el .ttf/.otf del catálogo para que el navegador lo dibuje (@font-face) en las tarjetas del catálogo. Sin esto la vista previa mostraría una tipografía cua | — |
| DELETE | `/api/fuente/archivo/<path:nombre>` | Saca una tipografía del catálogo. Ojo: si algún arte la usa, ese arte va a quedar sin fuente (se avisa al validar) — por eso el front pide confirmación antes. | — |
| GET | `/api/fuente/glifos/<path:nombre>` | Qué caracteres TIENE y cuáles le FALTAN a una fuente del catálogo. 'Tiene' = el contorno se puede dibujar de verdad (estar en el cmap no alcanza: puede estar ma | — |
| GET | `/api/pedido/fuente_chars` | Caracteres que SOPORTA la tipografía de personalización del diseño (la que estampa nombre/número). La planilla los usa para pintar en ROJO lo que la fuente no t | q: producto_id |

## Nesting / Grupos de tizada

| Método | Ruta | Descripción | Params |
|---|---|---|---|
| GET | `/api/grupos_tizada` |  | — |
| POST | `/api/grupos_tizada/eliminar` |  | body: id |
| POST | `/api/grupos_tizada/guardar` |  | body: id, moldes, nombre |
| GET | `/api/nesting_presets` |  | — |
| POST | `/api/nesting_presets/eliminar` |  | body: id |
| POST | `/api/nesting_presets/guardar` |  | body: alto_max_cm, espaciado_mm, id, margen_mm, nombre, rotacion |
| POST | `/api/productos/grupo_tizada` | Grupo de tizada del molde: los moldes con el MISMO grupo comparten mesa de trabajo; grupos distintos se arman en tizadas separadas. | body: grupo_tizada, id, producto_id |
| POST | `/api/productos/nesting_preset` |  | body: id, nesting_preset_id, producto_id |

## Perfiles de color

| Método | Ruta | Descripción | Params |
|---|---|---|---|
| POST | `/api/color/convertir` | CMYK ↔ RGB a través del perfil ICC configurado (el mismo con el que se ve en Illustrator). Body: {cmyk:[[c,m,y,k],…]} (canales 0..1) → {rgb:[[r,g,b],…], hex:[…] | body: cmyk, rgb |
| GET | `/api/perfiles` |  | — |
| POST | `/api/perfiles/config` |  | body: cmyk, rgb |

## Generación / Tizadas / Trabajos

| Método | Ruta | Descripción | Params |
|---|---|---|---|
| POST | `/api/generar` |  | body: asignacion, editables, prendas, producto_id |
| POST | `/api/generar_multi` | Genera VARIOS moldes en UNA sola tizada: junta las piezas de todos por TELA. Body: {molds: [pid, ...], prendas: [...]}. | body: asignaciones, default_diseno, editables, molds, perfil_forzado, planilla, prendas, productos, tela_base, vars_por_diseno |
| GET | `/api/trabajo/<tid>` |  | — |
| GET | `/api/trabajos/<tid>/mesa/<archivo>` | Descarga UNA mesa (la página `pi` de la hoja) como PDF PROPIO, con el NOMBRE que se ve en la tizada. Así cada mesa baja SEPARADA aunque varias sean páginas del  | q: nombre, pi |
| GET | `/api/trabajos/<tid>/pagina_img/<archivo>` | Una página de un PDF del trabajo como PNG (para MOSTRARLO en el visor con el look del sistema: así el scroll es el de la app, no el del visor de PDF del navegad | q: pi, z |
| GET | `/api/trabajos/zip` | Arma un ZIP con los PDF de todas las mesas de los trabajos pedidos (ids separados por coma), una carpeta por molde. | q: ids |
| GET | `/trabajos/<tid>/<archivo>` |  | — |

## Actualización / Publicación (VPS)

| Método | Ruta | Descripción | Params |
|---|---|---|---|
| POST | `/api/actualizacion/aplicar` | Aplica la pendiente YA (el botón «actualizar ahora»). Contesta ANTES de apagarse. | — |
| POST | `/api/actualizacion/cancelar` |  | — |
| GET | `/api/actualizacion/estado` | Lo consulta la PANTALLA para mostrar la cuenta regresiva. Sin clave a propósito: no revela nada sensible (qué versión corre y cuánto falta para el corte) y lo n | — |
| POST | `/api/actualizacion/subir` | Recibe el paquete del taller. `X-Token-Act` (clave), `X-Version`, `X-Sha256` y `X-Cuando` (marca de tiempo; 0 = ya). El cuerpo es el .zip crudo. | — |
| POST | `/api/publicacion/cancelar` |  | — |
| GET | `/api/publicacion/estado` | Para la pantalla de Publicación: qué versión hay acá, qué versión hay publicada y si hay algo pendiente allá. Si el servidor publicado no contesta, se dice y li | — |
| POST | `/api/publicacion/publicar` | Arma el paquete y lo SUBE. `cuando` = 0 (ya) o marca de tiempo. Es lo que hace el botón. | body: cuando, url, version |

## Productos / Moldería

| Método | Ruta | Descripción | Params |
|---|---|---|---|
| GET | `/api/productos` |  | — |
| GET | `/api/productos/<pid>/descargar_plantilla` |  | — |
| GET | `/api/productos/<pid>/preview` | Miniatura VECTORIAL del molde (siluetas de las piezas) para las tarjetas del Pedido. Liviano: solo los contornos, sin imagen rasterizada. | — |
| POST | `/api/productos/activar` |  | body: id |
| POST | `/api/productos/config_columnas` |  | body: columnas, id, role |
| POST | `/api/productos/config_mapeo` |  | body: id, mapeo_columnas, planilla_template_id |
| POST | `/api/productos/crear` |  | body: nombre, propio |
| GET | `/api/productos/diagnostico` | Por qué CADA moldería se ve o no se ve, para el usuario que está logueado AHORA. Existe porque «no me aparece» no se puede diagnosticar a ciegas: el sistema pub | — |
| POST | `/api/productos/eliminar` |  | body: id |
| GET | `/api/productos/objetos_agregados` |  | q: diseno, pid |
| POST | `/api/productos/referencia_medida` | Guarda la dimensión de referencia del diseño ('alto' o 'ancho') del molde. | body: id, referencia |
| POST | `/api/productos/renombrar` |  | body: id, nombre |
| POST | `/api/productos/telas_asignadas` | Telas (ids del registro global) disponibles para ESTE molde. Cuerpo nuevo: {id, todas:[…], por_pieza:{pieza:[…]}}. Cuerpo viejo: {id, telas:[…]} (= `todas`). | body: id, max_var, por_pieza, telas, todas |
| POST | `/api/productos/terminologia` | Guarda los nombres configurables (variante/molde) de un producto. Solo afecta las etiquetas que ve el usuario; el funcionamiento es el mismo. | body: id, terminologia |

## Plantilla (molde)

| Método | Ruta | Descripción | Params |
|---|---|---|---|
| POST | `/api/plantilla` |  | file: archivo |
| GET | `/api/plantilla/deteccion` | Detecta las piezas de la moldería para el etiquetador visual. | q: candidatas, talle_ref, variante |
| GET | `/api/plantilla/deteccion_todas` | TODAS las piezas de TODAS las variantes en un solo lienzo, para AGRUPAR por selección. El gesto que pidió el usuario es el mismo del nombrado: ver todo junto, s | — |
| GET | `/api/plantilla/emparejado` | Estado del emparejado entre talles: guía, talles, qué pieza le tocó a cada nombre en cada talle, y el ajuste a mano guardado (acomodo + correcciones). | — |
| POST | `/api/plantilla/emparejado` | Guarda el ajuste a mano del emparejado y RE-PROPAGA el nombrado con él. Body: `{pid?, talle, acomodo?: {idx:[dx_mm,dy_mm]}, manual?: {nombre: idx|null}, reset?: | body: acomodo, manual, reset, talle |
| POST | `/api/plantilla/etiquetas` | Recibe los nombres puestos a mano en el talle que se está mirando y arma el registro propagándolos a todos los talles por posición. ⚠️ El registro se re-arma SI | body: asignaciones, mesa, talle_ref |
| POST | `/api/plantilla/grupo_pieza` | UN SOLO GESTO: «estas piezas son la misma y se llama Frente». Body: `{pid?, nombre, guia_idx, piezas?: {talle: idx|null}, renombrar_de?, eliminar?}`. En un solo | body: eliminar, guia_idx, nombre, piezas, renombrar_de |
| GET | `/api/plantilla/medidas_variantes` | Medidas reales (w_cm/h_cm) de CADA pieza en CADA variante, leídas del registro (sin re-detectar). Para la visual de referencia «piezas en fila por talle» que mu | — |
| GET | `/api/plantilla/nido` | Geometría NESTEADA de cada pieza nombrada en TODOS los talles (para acomodar en el visor). | — |
| GET | `/api/plantilla/pdf_guia` | PDF imprimible con el molde de guía + el recuadro de medida y el nombre de cada pieza, según el modo elegido en el visor (default / rango / talle). | q: capas, config, formato, guia, limpio, piezas, rango, talle |
| POST | `/api/plantilla/pieza_agregar` | Agrega una PIEZA NUEVA al molde, en el lugar del lienzo que se indique. Cuerpo: `{pid?, origen: "duplicar"|"archivo", pieza_idx?, dx, dy, nombre?}` · `duplicar` | body: dx, dy, origen, pieza_idx |
| POST | `/api/plantilla/pieza_archivo` | Guarda el archivo de la pieza que se va a agregar (paso previo a `pieza_agregar`). Va a un nombre fijo (`pieza_nueva.ai`) y NO toca el molde: recién `pieza_agre | file: archivo |
| POST | `/api/plantilla/pieza_deshacer` | Saca la ÚLTIMA pieza agregada: vuelve el molde a su versión anterior y el registro con él. El archivo se revierte moviendo el puntero de versión (el original nu | — |
| GET | `/api/plantilla/variantes` | Radiografía del molde para la herramienta de NOMBRAR VARIANTES: qué capas hay, cuáles son talles, y la curva propuesta (de menor a mayor por área). Acepta `?pid | — |
| POST | `/api/plantilla/variantes` | Aplica los nombres de variante (talle) a las capas del molde. Body: `{pid?, nombres: {capa_actual: nombre_nuevo}}`. Escribe una VERSIÓN nueva del molde (el arch | body: nombres |
| POST | `/api/plantilla/variantes_piezas` | Asigna las variantes SELECCIONANDO PIEZAS (molde con todo en una sola capa). Body: `{pid?, asignaciones: {pieza_idx: "nombre_variante"}}` con los índices de `/a | body: asignaciones |
| POST | `/api/plantilla/variantes_piezas_borrador` | Guarda el BORRADOR de la asignación pieza→variante, sin tocar el molde. Por qué existe aparte de `/api/plantilla/variantes_piezas`: aplicar PARTE el PDF y rehac | body: asignaciones |
| GET | `/api/plantillas_planillas` |  | — |
| POST | `/api/plantillas_planillas/eliminar` |  | body: id |
| POST | `/api/plantillas_planillas/guardar` |  | body: columnas, id, nombre, role |

## Variables / Modelos / Grupos

| Método | Ruta | Descripción | Params |
|---|---|---|---|
| POST | `/api/productos/conjuntos` | Guarda los CONJUNTOS "van juntas" (piezas de varias partes que forman una sola). Estructura: [{id, nombre, piezas:[idx]}]. Para la generación automática de vari | body: conjuntos, id |
| POST | `/api/productos/grupos` | Guarda los GRUPOS de piezas del molde: [{id, nombre, piezas:[idx]}]. La generación de variables corre dentro de cada grupo; las piezas pueden repetirse entre gr | body: grupos, id |
| POST | `/api/productos/modelos` | Guarda los MODELOS del molde y sus Variables. Estructura: [{id, nombre, variables:[{id, nombre, build:{clave→valor_id}}]}]. El nombre de modelo no se puede repe | body: id, modelos |
| POST | `/api/productos/variante_guia` | Guarda en la base la variante (talle) usada como guía del visor del molde. Al estar en el servidor, todos los usuarios ven la misma. | body: id, variante |
| POST | `/api/productos/variantes` | Guarda los TIPOS de pieza (variantes) y sus valores del molde. Estructura: [{clave, label, valores:[{id, label, pieza_idx?, pieza_id?}]}]. Es genérico (sirve pa | body: id, variantes |

## Etiqueta / Borde

| Método | Ruta | Descripción | Params |
|---|---|---|---|
| GET | `/api/productos/borde_corte` |  | q: pid |
| POST | `/api/productos/borde_corte` |  | body: activo, ancho_mm, color, pid |
| GET | `/api/productos/etiqueta` |  | q: pid |
| POST | `/api/productos/etiqueta` |  | body: activo, align, borde_activo, borde_color, borde_mm, color, mostrar, pid, piezas_off, posicion, posiciones, separador, size_mm, texto, zonas |

## Arte

| Método | Ruta | Descripción | Params |
|---|---|---|---|
| POST | `/api/arte` |  | form: diseno · file: archivo |
| GET | `/api/arte/asignar_estado` |  | q: job |
| POST | `/api/arte/asignar_todo` | Genera EN PARALELO (ProcessPool) el render de TODOS los talles de una variable → caché en disco. Devuelve un job_id; el progreso se consulta en /api/arte/asigna | body: diseno, mapeo, pid, talles, variante |
| GET | `/api/arte/deteccion` |  | q: diseno, variante |
| POST | `/api/arte/mapeo` |  | body: diseno, mapeo, variante |
| GET | `/api/arte/mesa_img` | UNA mesa del arte, para el visor. Ver `_urls_mesas`. **Sale VECTORIAL (SVG), siempre**: lo que se ve en pantalla tiene que ser el diseño de verdad, no una foto  | q: diseno, mesa |
| GET | `/api/arte/perfil` | Detecta el perfil incrustado del arte recién subido (o de ese diseño) y devuelve el aviso (sin perfil / distinto / ok). | q: diseno |
| POST | `/api/arte/preview_piezas` | PREVIEW REAL per-pieza (CACHEADO): sirve el render del motor por pieza desde `_piezas_base`. La 1ª vez por config arma y guarda; las siguientes son instantáneas | body: bg, diseno, editables, mapeo, pid, sin_prewarm, talle, variante |

## Editables / Objetos agregados

| Método | Ruta | Descripción | Params |
|---|---|---|---|
| POST | `/api/productos/editable_color` | Setea (o LIMPIA) el color override de un editable, POR VARIABLE, a NIVEL OBJETO (no por talle: el color es del objeto). Body: {pid?, diseno, nombre, variante, c | body: color, diseno, nombre, obj_id, pid, variante |
| POST | `/api/productos/editable_quitar` | SACA del arte un objeto que había agregado el usuario (contraparte de `colocar`): borra la capa `Editable <nombre>` y su contenido, escribiendo una versión nuev | body: capa, diseno, inyectadas, pid |
| GET | `/api/productos/editables` |  | q: diseno, pid, variante |
| POST | `/api/productos/editables` |  | body: diseno, nombre, pid, talles, transform, variante |
| GET | `/api/productos/editables_config` | Config de TAMAÑO de capas editables del molde (general, por nombre de capa). Devuelve la lista registrada + las VARIANTES del molde (para el selector emergente) | q: pid |
| POST | `/api/productos/editables_config` | Guarda la config de tamaño del molde. Body: {pid, config:[{capa, rangos:[{variantes:[...], apaisado:{ancho,alto}, vertical:{ancho,alto}}]}]}. Se guarda por nomb | body: config, pid |
| DELETE | `/api/productos/objeto_agregado/<oid>` |  | q: diseno, pid |
| POST | `/api/productos/objeto_agregado/<oid>/colocar` | COLOCA el objeto en el diseño: lo INYECTA en el arte como capa `Editable <nombre>` en la mesa de esa pieza — en TODOS los rangos que use (igual que el arte trae | body: diseno, fx, fy, pid, pieza |
| POST | `/api/productos/objeto_agregado/<oid>/duplicar` | Copia el objeto (archivo + entrada) para poder ponerlo en OTRA pieza. La copia nace SIN pieza (hay que colocarla) y conserva el transform del original como punt | body: diseno, pid |
| POST | `/api/productos/objeto_agregado/<oid>/pieza` | Asigna el objeto a una pieza, o lo DESASIGNA (`pieza` vacía): sigue en la barra, listo para colocarlo en otra. Un objeto vive en UNA sola pieza — para tenerlo e | body: diseno, pid, pieza |
| POST | `/api/productos/objeto_agregado/<oid>/transform` | Guarda el transform (mover/rotar/escalar/espejar) del objeto agregado, POR VARIABLE y talle. Estructura en el manifiesto: obj['transforms'][variante][talle] = { | body: diseno, pid, pieza, talles, transform, variante |
| POST | `/api/productos/objeto_agregar` |  | form: diseno, nombre, pid · file: archivo |

## Diseños

| Método | Ruta | Descripción | Params |
|---|---|---|---|
| GET | `/api/disenos` |  | q: molds |
| POST | `/api/disenos/eliminar` |  | body: id, pid |
| POST | `/api/disenos/guardar` |  | body: nombre, pid |

## Telas

| Método | Ruta | Descripción | Params |
|---|---|---|---|
| GET | `/api/telas` |  | — |
| POST | `/api/telas` | Ya NO crea telas (vienen de la API). Sólo administra los GRUPOS combinables. | body: grupos |
| POST | `/api/telas/ancho` | Guarda el ANCHO (cm) local de una tela de la API. Es lo único editable de nuestro lado. | body: ancho_cm, id |
| GET | `/api/telas/conexion` | Estado de la conexión con la API del sistema. NO devuelve la key (sólo si está o no). | — |
| POST | `/api/telas/refrescar` | Fuerza re-consulta a la API externa (botón «Actualizar telas del sistema»). | — |

## Planillas / Reglas

| Método | Ruta | Descripción | Params |
|---|---|---|---|
| POST | `/api/productos/asignar_planilla` |  | body: planilla_template_id, producto_id |
| GET | `/api/reglas_planilla` |  | — |
| POST | `/api/reglas_planilla/eliminar` |  | body: id |
| POST | `/api/reglas_planilla/guardar` |  | body: clave, comportamiento, id, nombre, opciones, tipo |
