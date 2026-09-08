# 🧵 CAMINO B — MOLDE CON EL DISEÑO ADENTRO

> **ESTE ARCHIVO ES LA MEMORIA DE ESTA FEATURE.** Se lee ANTES de tocar nada de este camino y se
> actualiza DESPUÉS de cada entrega, en la misma tanda y en el mismo commit. Lo que no está escrito
> acá se pierde entre sesiones. Es el mismo hábito del `MAPA_DEL_SISTEMA.md`, pero acotado a esta
> feature para que no se diluya entre 3.900 líneas.
>
> **Rama:** `pruebas-tizada-con-diseno` (local, sin push).

---

## 1. QUÉ ES (en tres líneas)

Hoy el cliente carga **un molde** y **un arte** por separado, y el sistema los cruza (el mapeo dice
qué mesa del arte va en qué pieza). El **camino B** es la alternativa: el cliente sube **UN solo
archivo que ya trae el diseño estampado adentro de cada pieza**. No hay arte aparte ni mapeo.

Los dos caminos **conviven**: el A no se toca.

---

## 0.a ⚡ NOMBRAR PIEZAS Y LA ETIQUETA ABREN AL INSTANTE (2026-09-03)

Pedido del usuario, textual: *«debe de funcionar super flash, no puede tardar ni andar super lento
sin importar el diseño de cada molde… debe de funcionar solo con los bordes para detectar las
piezas al igual que la etiqueta y ahí ignorar lo pesado del diseño»*.

**Lo que costaba, medido:** armar el visor de UN talle = **52 s**, y los 52 son `get_drawings()`
leyendo los dibujos de las 9 mesas (1.516 items por mesa) para quedarse con 140 recortes. No es el
acomodo ni el tamaño de la respuesta (que ya era de 5 KB): es **abrir el archivo pesado**. Cambiar
de talle después costaba 0 s, porque los dibujos ya estaban en memoria de ese proceso.

**La salida:** el **alta** ya recorre las 9 mesas × 20 talles, así que arma ahí mismo el visor de
**todos** los talles —con los contornos que ya tiene en la mano, gratis— y lo guarda en
`datos/productos/<pid>/visor_contornos.json`. Después, nombrar piezas y ubicar la etiqueta **no
abren el PDF nunca más**.

| | antes | ahora |
|---|---|---|
| Abrir «nombrar piezas» | **46 s** | **0,002 s** |
| Peso de lo guardado | — | 103 KB los 20 talles (5,2 KB cada uno) |
| Lo que tarda el alta | 58 s | 58 s (no cambió: los contornos ya estaban leídos) |

🔴 **Rápido y equivocado sería peor que lento**: el contrato compara lo guardado contra lo que
saldría de leer el archivo, pieza por pieza y contorno por contorno
(`verificar_visor_rapido.py` §3). Y si el molde se re-sube por el camino de siempre, el visor
guardado se borra: si no, «nombrar piezas» mostraría las piezas del archivo anterior y —como ya no
se abre el PDF— nadie se enteraría.

---

## 0. ESTADO (2026-09-02) — **el camino funciona de punta a punta**

Subir → nombrar → ubicar la etiqueta → tela → planilla → **tizada**, probado en el navegador con
el archivo real de 123 MB. Lo que queda abierto, con su detalle más abajo:

| Pendiente | Dónde |
|---|---|
| 🔴 **Rendimiento**: una tizada de 1 prenda tarda ~21 min, y **19 son del aplanado para el RIP** | §7-E4 |
| **El nombre y el número** necesitan un archivo con las capas `nombre` y `00` para probarse | §3.b |
| El nesting mejor del proyecto de referencia (13 % menos de tela) | §5 |

---

## 2. EL RECORRIDO DEL CLIENTE (lo que va a ver) — reformulado 2026-09-03

Todo esto pasa **desde el Pedido**, **no** desde Configuración. Al empezar hay **dos botones**
(decisión del usuario, 2026-09-03) y **no son excluyentes**: un pedido puede llevar de los dos —
una camiseta con el diseño adentro y un short del catálogo con su arte van a la misma tizada.

| | |
|---|---|
| **Armar con base** | los pasos de siempre: diseño → prenda de la moldería → arte → planilla → tizada |
| **Cargar molde con diseño incluido** | lo de abajo |

1. **Suelta los archivos** — **varios de una vez** (la camiseta, el short…). El **nombre del molde
   sale del propio archivo**: no se escribe. Se suben de a uno, con el % real y después el reloj.
2. Con los archivos cargados aparecen como **botones**: se tocan **los que van juntos** y se
   escribe **el nombre del diseño una sola vez** para todos (así no quedan «JUGADOR» y «jugador»,
   que serían dos diseños).
3. Y de cada molde se dice **de qué columna de talle** toma sus medidas — lo que distingue una
   camiseta de un short cuando la planilla lleva «Talle» y «Talle short». 🔴 Sin esto el short
   tomaría el talle de la camiseta y saldría del tamaño equivocado, impreso y cortado.
   (Se guarda en `mapeo_columnas.talle` del molde, que es de donde el motor ya lo lee.)
4. **Nombra las piezas con LA HERRAMIENTA DE MOLDERÍA** (regla del usuario 2026-09-04:
   «exactamente la misma herramienta que nombrar pieza en configuración» — y, en la misma tanda:
   «pero **no debe entrar a ajustes reales: a ese espacio no puede tener acceso el cliente**»).
   «Nombrar las piezas» abre **esa misma pantalla dentro del pedido**: el lienzo de **los 20
   talles** (cada talle en una fila, las piezas en el orden del archivo), la columna de talles con
   ojito, selección por clic o recuadro, el campo «Frente, Espalda, Manga…» y ✓. En este camino no
   hace falta tocar la pieza del talle guía: la pieza *i* es la misma en todos los talles, así que
   cualquiera que toques la nombra en todos. Los provisorios «Pieza N» cuentan como «sin nombre»
   (0/9 nombradas). **«← Volver al pedido»** vuelve al paso Arte con los nombres frescos.
   🔴 **Lo que el cliente NO ve** (`_soloHerramienta`): el menú de ajustes, «volver a ajustes»,
   re-subir el molde, «nombrar talles», «agregar una pieza» y la ayuda de exportación. Nunca se
   cambia de pestaña: la pantalla se renderiza desde **Pedidos**.
5. Con todo nombrado, «Ubicar la etiqueta» abre **la herramienta de la pestaña Etiqueta**, también
   dentro del pedido: la lista de piezas (en el **orden del archivo**), el talle guía y los ojitos
   por talle, «Aplicar a todas», y el visor donde se toca el borde de cada pieza. La **forma** de
   la etiqueta (qué muestra, tamaño, color, borde) se ve pero no se edita: es la config viva del
   taller (`Configuración → Moldes con diseño`) y el servidor sólo toma las posiciones. «Guardar
   etiqueta» y «← Volver al pedido». Del panel puede cambiar además el **color del texto**, el
   **color del halo** y la **alineación** (lo demás se ve apagado: lo decide el taller).
   📐 **Cómo se ve el molde en el visor: TAL CUAL EL ARCHIVO.** Los talles vienen dibujados **uno
   encima del otro** (la gradación) y así se muestran — no se separan ni se acomodan: ya se
   distinguen por su capa (el ojito de la columna de talles). Dentro de cada mesa, cada pieza
   queda donde el archivo la puso. Lo único que se acomoda son las **mesas**, porque el PDF las
   guarda todas en (0,0) (medido): `acomodo_mesas` les da su lugar en filas, en el orden del
   archivo, **una sola vez para todos los talles** — si se calculara por talle, el molde se
   movería al cambiar de talle. Tocar una pieza (que es la pila de sus 20 talles) la nombra en
   todos.
6. Telas, planilla y tizada: **iguales que en el otro camino**.

**Lo que NO hace el cliente** — lo deja el taller **una vez** en `Configuración → Molde con
diseño` (es global: no hace falta tener ningún molde cargado):

| | |
|---|---|
| **Borde de corte** | grosor, de qué lado del contorno, **color**, y si se dibuja |
| **Etiqueta** | tamaño de letra, separador, qué muestra (talle · pieza · número), grosor del halo y si va. La **alineación**, el **color del texto** y el **color del halo** se fijan acá como punto de partida, pero **el cliente los puede cambiar en su molde** (`_ETQ_CLIENTE`) |
| **Planilla del pedido** | las columnas del Excel que se le ponen a TODO molde con diseño al subirlo (`config_con_diseno.planilla_template_id`) |
| **Nesting** | con qué regla (separación, margen, giro) se acomodan estas piezas |

Es **viva**: cambiarla afecta también a los moldes ya cargados (la pantalla lo avisa).

🔤 **La tipografía del «NOMBRE» y el «00»**: si la del archivo no está en el catálogo, el paso Arte
lo avisa igual que en el camino de siempre («Tipografía (1)» en amarillo) y desde ahí se puede
**cargarla** o **cambiarla por una nuestra**. Si no se hace nada, la prenda sale con la
predeterminada (Anton). Las fuentes que se piden salen de los placeholders del desplegado
(`fuentes_estado` tiene su ramal camino B: sin arte no había nada que mirar y no avisaba).

**Cómo se ve** (2026-09-03): las dos formas son **dos tarjetas mitad y mitad** que ocupan el
espacio libre —es LA decisión de esa pantalla— con un color sutil del sistema cada una (cian /
magenta) puesto en el borde y en un resplandor de fondo, no en un relleno plano.

🔴 **La espera de la subida es un CÍRCULO, no una barra** (`CargaCircular`). Mientras el archivo
viaja, el anillo marca el **porcentaje real**; cuando llega, el servidor **recién empieza a
leerlo** (con 100+ MB son minutos) y el anillo pasa a **girar**, con el reloj corriendo. Una barra
llena y quieta se lee como «colgado», y estimar lo que falta sería inventar: o es el número real,
o gira.
📌 **El CSS va en `frontend/src/index.css`.** `frontend/src/App.css` **no lo importa nadie** — se
comprobó: sus selectores no están en el bundle. Escribir ahí compila sin error y no aplica nada
(pasó, y costó un rato de búsqueda). Con 9 piezas alcanza, pero queda anotado.

---

## 3. EL ARCHIVO REAL (medido, no supuesto)

`C:\Users\user2\Downloads\PRUEBA TIZADA PRO\para acomodo de archivos\CAMISETA JUGADOR.ai`

| Dato | Valor |
|---|---|
| Tamaño | **123 MB** |
| Mesas (páginas) | **9** — una por PIEZA: 2384×2714, 2396×2456, 1880×1594, 1878×1594, 822×147, 820×147, 637×182, 118×1632, 118×1632 pt |
| Capas (OCG) | **20 = los TALLES**: `0 1 2 4 6 8 10 12 14 16` y `XS S M L XL 2XL 3XL 4XL 5XL 6XL` |
| Mesa 1, sola | 1.376 trazados · **140 máscaras de recorte** · 1.320 rellenos · 56 trazos · texto (60 `setFont`) |
| Estructura | **100 hijos directos de la raíz, todos máscaras de recorte** = 20 talles × ~5 objetos. Cada máscara **es** una pieza y su dibujo va adentro |

**Lecturas que salen de acá y mandan sobre el diseño de la solución:**

1. **La forma de la pieza es el trazado de su máscara de recorte.** No hay que inventar contornos.
2. **Los talles están apilados uno encima del otro** (gradación): si no se aísla la capa del talle
   ANTES de agrupar, el ensamblado por solape los funde a todos en una sola mancha. **Aislar la
   capa es obligatorio, no una optimización.**
3. **123 MB.** Es la prueba de por qué la UI tiene que trabajar con contornos y no con el dibujo:
   mandar esto al navegador es exactamente lo que hace lento el sistema.

---

## 3.b 📋 QUÉ TIENE QUE TRAER EL ARCHIVO (el requisito, para el manual)

| Qué | Cómo | Por qué |
|---|---|---|
| **Una capa por talle** | `0 1 2 4 …` / `XS S M …` | de ahí salen los talles; es el mismo formato de la plantilla de hoy |
| **Cada pieza dentro de su máscara de recorte** | como la exporta Illustrator | la máscara **es** el contorno de la pieza: no se reconstruye, se lee |
| **El texto «00» donde va el número y «NOMBRE» donde va el nombre** (2026-09-04) | como TEXTO, dentro de la pieza de cada talle, con su fuente, tamaño y color (y su apariencia: relleno, borde) | son los placeholders: se detectan **por texto** y se reemplazan por el valor de las columnas `numero` y `nombre` de la planilla, talle por talle, con la fuente y el color del archivo. Ya no importa la capa |
| ~~Una capa `nombre` y una capa `00`~~ | (criterio anterior, superado) | ~~son los placeholders que se reempla~~zan por el nombre y el número de cada prenda |

🔴 **Sin los textos «00» y «NOMBRE» la tizada SALE IGUAL, con el texto del diseño en todas las
prendas.** No hay error, no hay aviso. Por eso el requisito está escrito acá y lo cuida
`verificar_personalizacion_con_diseno.py`.
Cómo se leen (`piezas_con_diseno.quitar_placeholders`, en la etapa de páginas del desplegado): se
decodifica cada texto del content-stream con la codificación de su fuente —⚠️ el «00» del archivo
real viene como código 31 con `/Differences [31 /0]` y PyMuPDF no lo lee—; si dice «00» o
«NOMBRE» se guarda posición, tamaño, fuente, color nativo y pasadas de apariencia
(`m{mesa}.json["placeholders"]`) y **se saca del dibujo**. El motor (`generar_pieza`) usa el
placeholder **del talle** (`por_talle`): cada talle tiene el suyo a su tamaño. La fuente del
archivo tiene que estar en el catálogo (si no, Anton como siempre). El criterio anterior por
CAPAS (`_CAMPO_ALIAS`) queda sin uso en el camino B.

---

## 4. DECISIONES TOMADAS (con su porqué)

| Fecha | Decisión | Por qué |
|---|---|---|
| 2026-08-31 | **Los talles vienen EN CAPAS** (confirmado con el archivo: 20 capas) | Es el mismo formato que la plantilla de hoy → se reusa el modo «por capa» (`MAPA §10.c`) y todo el nombrado/agrupado existente |
| 2026-08-31 | **Nombre y número SIGUEN**, como hoy | El archivo trae texto adentro; `extraer_personalizacion` ya sabe leer esos placeholders, sólo que ahora se leen del MOLDE en vez del arte |
| 2026-08-31 | **La UI de edición usa SÓLO CONTORNOS** | Pedido explícito del usuario: «que no quede pesado el uso de molde… para lo de etiqueta y etc use solo los contornos». Con 123 MB no hay otra |
| 2026-08-31 | **El borde de corte se sigue tomando igual** | «que tome los bordes igual» — el borde no cambia de camino; lo que cambia es quién decide su medida (el admin) |
| 2026-08-31 | **La detección se porta a PYTHON**, no corre en el navegador | Ley del proyecto: *el arte se ve igual que la tizada*, **un solo motor**. La salida final la produce Python (CMYK exacto, aplanado RIP, UserUnit). Dos motores = dos resultados |
| 2026-08-31 | El camino B se marca con **`origen: "con_diseno"`** en el producto | Un flag explícito en el catálogo; nada de adivinar por la forma del archivo |

---

## 5. DE DÓNDE SE COPIA (el proyecto de referencia)

**`C:\Users\user2\Documents\tincho\codigos\Prueba para tizada`** — navegador puro (pdf.js, sin
servidor). **Ya hace lo que el usuario quiere**, así que es la referencia: lo que falte, se saca de
ahí. Su `README.md` está muy bien escrito y explica cada decisión.

| Lo que resuelve | Archivo | Cómo lo hace |
|---|---|---|
| **Juntar los trozos en una pieza** | `src/core/assembly.js` | Illustrator parte una pieza en muchos trozos (silueta, dibujo interno, logos, texto). Dibuja la silueta de cada trozo sobre una grilla común: los que pisan la misma celda **son la misma pieza** (union-find). En su archivo real: **179 trozos → 30 piezas**. El trozo que cubre toda la mancha es el **borde externo** y se usa su trazado vectorial exacto; si ninguno la cubre, se traza el contorno de la mancha |
| **La forma real de una pieza** | `src/core/shape.js` | Si la pieza tiene máscara de recorte, su forma **ES el trazado de la máscara**; lo de adentro nunca cuenta como objeto propio. Nunca un rectángulo |
| **Rasterizar la silueta para acomodar** | `src/core/shape.js` (`rasterize`) | Grilla de ocupación por columnas (`minRow`/`maxRow`), con dilatación para la separación |
| **Acomodar** | `src/core/nesting.js` | Por silueta real; la mesa se guarda como **los tramos ocupados de cada columna** (no un horizonte plano), así una pieza entra **debajo del saliente** de otra. Elige dónde **termina** la pieza, no dónde apoya. Prueba hasta 12 órdenes distintos con presupuesto de tiempo. Medido: 176,8 cm → **153,2 cm** (13 % menos de tela) |
| **Que no se cuelgue** | `src/core/heavy.js` + worker | El cálculo pesado va en un Web Worker con OffscreenCanvas; el dibujo se arma desprendido de la página y por tandas |
| **Diagnóstico desde la terminal** | `scripts/analyze.mjs`, `scripts/analyze-layers.mjs` | Dicen qué trae un archivo sin abrir el visor. **Ya me sirvieron para medir el archivo real** (§3) |

📌 **De paso, esto ataca un pendiente viejo:** [[tiras-no-detectadas]] («4 tiras que no se
detectan») quedó parado justo en el AGRUPAMIENTO de `extraer_piezas_mesa`. Este algoritmo es la
respuesta a ese problema.

⚠️ **Su nesting es MEJOR que el nuestro** (mide 13 % menos de tela) y engancha con otro pendiente:
[[nesting-aprovechamiento]]. **No entra en este camino** — se anota y se decide aparte, para no
mezclar dos cambios grandes en la misma entrega.

---

## 6. PREGUNTAS ABIERTAS (lo que falta decidir)

- [x] ~~¿Cómo se marca el nombre y el número?~~ **RESUELTO 2026-09-02 (decisión del usuario):
      LO TRAE EL ARCHIVO.** Ver el requisito en §3.b.

- [ ] ¿Un molde del camino B tiene **variables** (modelos), o va **entero** como los «Mis
      artículos» de hoy? (hoy un molde propio no tiene variables y el motor genera todas sus piezas)
- [ ] ¿Lleva **toggles** (manga corta/larga, capucha)? Si el diseño ya está adentro, cada opción
      tendría que venir dibujada en el archivo.
- [ ] ¿Cómo se asigna la **tela** por pieza en este camino?
- [x] ~~Las 9 mesas: ¿una pieza por mesa?~~ **SÍ**, en este archivo: 9 mesas = 9 piezas por talle
      (frente, espalda, dos mangas, dos tiras, cuello y dos vivos). Igual el detector **no lo
      asume**: agrupa por solape, así que una mesa con varias piezas daría varias.

---

## 7. EL PLAN — entregas (cada una funciona sola)

> Regla del proyecto: **nada a medias.** Si una entrega no entra en una sesión, se parte en
> entregas que funcionen, nunca a medio hacer.

### [x] E0 — Andamiaje — **HECHA 2026-08-31**
- Rama `pruebas-tizada-con-diseno` + **commit de partida `e6a505a`** (local, sin push).
- **Dos localhost a la vez** (verificado, los dos contestan):
  - **8050** — carpeta principal `TIZADA PRO`, la RAMA: **acá se desarrolla el camino B**. Es el
    puerto de siempre, con la tarea de arranque automático y los `.bat` que ya usás.
  - **8051** — `..\TIZADA PRO - ACTUAL`, un `git worktree` **congelado en `e6a505a`**: el sistema
    tal como quedó hoy, para comparar contra la prueba. Se levanta con `INICIAR-ACTUAL-8051.bat`.
  - Los dos miran **los mismos `datos/`, `entrada/` y la misma base**, así que ven los mismos
    moldes; los `trabajos/` van separados para no mezclar salidas.
  - `node_modules` va por **junction** al de la carpeta principal (no se duplican 61 MB); el
    `dist` es **copia propia** — si fuera enlace, recompilar el desarrollo cambiaría la copia
    congelada y dejaría de servir para comparar.
- Este archivo + la memoria persistente `molde-con-diseno` + el puntero en el MAPA (§0.b).

### [x] E1 — Detectar las piezas del archivo nuevo — **HECHA 2026-08-31**

Módulo **`piezas_con_diseno.py`** + contrato **`verificar_molde_con_diseno.py`** (verde contra el
archivo real).

**El hallazgo que simplificó todo: la forma de la pieza YA ESTÁ EN EL ARCHIVO.** Illustrator mete
el dibujo de cada pieza dentro de una **máscara de recorte** cuyo trazado es la silueta. No hay que
reconstruir ningún contorno: hay que *leerlo*. Y PyMuPDF lo entrega
(`page.get_drawings(extended=True)` devuelve los items `clip`). Por eso el algoritmo terminó siendo
más simple que el del proyecto de referencia:

1. Los recortes **de esa capa** (talle). Aislar por capa es **obligatorio**: los talles están
   apilados y sin aislar se funden en una mancha.
2. Descartar el **marco de la mesa** que agrega Illustrator al exportar.
3. **Agrupar por solape** (union-find). Como son un puñado de recortes por mesa y talle (3 a 7),
   alcanza con los bounding boxes: **no hace falta rasterizar nada**. De paso se traga los recortes
   anidados del dibujo interno sin mirar el nivel de anidamiento.
4. El contorno de la pieza es el recorte **de mayor área** del grupo, con su trazado vectorial
   exacto.

Si el archivo no trae recortes hay un **respaldo** que agrupa los trazados pintados por solape.
⚠️ Ese camino **no está verificado contra un archivo real** (no hay ninguno sin máscaras a mano) y
así está marcado en el código.

**Medido contra `CAMISETA JUGADOR.ai`:**

| | |
|---|---|
| Piezas de un talle | **9** (una por mesa) — lo que tiene el archivo |
| Lo que daría la detección de HOY | **619 «piezas»** para el mismo talle |
| Los 20 talles | separados y creciendo: 28×41 → 81×96 cm |
| El molde entero (9 mesas × 20 talles) | 180 piezas en **50 s** |

🔴 **Trampa que costó y quedó en el código:** para descartar el marco de la mesa, la regla «ocupa
más del 95 % del área» **se comía piezas reales** — la tira del talle 0 mide 28,7 cm en una mesa de
29,0 cm, y el frente 6XL ocupa el 97 % de la suya. Se compara contra el rectángulo de la página
**con tolerancia de 1 pt**, nunca por porcentaje.

### [x] E2 — El alta desde el Pedido — **HECHA** (2026-08-31 y 2026-09-02)
**Backend (listo y probado por HTTP con el archivo real):**
- `POST /api/plantilla` detecta el camino sobre el temporal, da de alta con
  `alta_molde_con_diseno`, marca en disco DESPUÉS del `os.replace` y escribe `origen: "con_diseno"`.
- **Visor de contornos liviano**: `/api/plantilla/deteccion` enruta a `detectar_para_visor` →
  **7 KB** con las 9 piezas de las 9 mesas (el archivo pesa 123 MB).
- `/api/productos` devuelve **`origen`** y **`efimero`** (sin eso el front no puede ramificar).
- **EL MOLDE ES EFÍMERO** (decisión del usuario, 2026-09-02): se sube para ESE pedido y no queda
  guardado. `POST /api/productos/crear` acepta `efimero: true` (+ hereda `planilla_template_id`
  del pedido), no lo reusa nunca y no le exige nombre único. Lo borra
  `POST /api/pedido/limpiar_efimeros` («Nuevo pedido» / «Terminar pedido») y, si quedó huérfano,
  `_barrer_efimeros` al arrancar el servidor.
- **Cimientos que faltaban** (ver bitácora): `idx_mesa` persistido en la base, la marca del camino
  B en las claves de `_PZS_CACHE` y del caché de detección en disco, el visor precargando los
  nombres ya puestos, y el pre-warm de `deteccion_todas` salteado.

**Front (hecho 2026-09-02, probado en el navegador):** tarjeta **«Molde con el diseño adentro»** en
Pedido → Mis artículos; el mismo modal de subida sirve para las dos formas (`subirMoldeConDiseno`
cambia texto, `accept` —sin `.dxf`— y a dónde va) con **espera honesta en dos tramos** (el % real
de la subida por XHR, y después «leyendo y detectando» con el reloj corriendo: nunca un porcentaje
inventado). Al terminar el molde queda **ya elegido** en el diseño activo, sin salir del wizard —
`subirMiMolde` termina en `abrirConfigMiMolde`, que te manda a Configuración; ésta no.
El molde se borra al **«Nuevo pedido»** (el modal avisa que se pierde el nombrado) y `moldesEfimeros`
viaja en `localStorage` con el resto del wizard, para que un F5 no deje 118 MB huérfanos.

### [x] E3 — Nombrar las piezas — **HECHA** (2026-09-02)

🔴 **En el camino B nombrar NO es agrupar: es RENOMBRAR.** El registro ya está completo desde el
alta y la correspondencia entre talles es exacta por construcción (son capas de la misma mesa).
Las herramientas del camino A (`/api/plantilla/etiquetas`, `grupo_pieza`, `emparejado`) re-arman
el registro con `alta_plantilla_manual`, que asume UNA sola mesa y empareja por forma: sobre un
molde B lo destruyen, o revientan con el `mesa=None` que devuelve su visor. Las tres devuelven
**409** ahora.

- `piezas_con_diseno.renombrar(reg, mesa, idx_mesa, nombre)` — función pura: ubica la pieza por el
  par `(mesa, idx_mesa)` (el único identificador que no depende del talle), aplica
  `MP.nombres_normalizados` para que dos piezas nunca queden con el mismo nombre (el registro es
  un dict POR NOMBRE: dos iguales pierden una en silencio) y conserva el orden de inserción.
- `POST /api/plantilla/pieza_renombrar {pid, mesa, t_idx, nombre}` — `mesa`/`t_idx` son los que el
  visor ya devuelve en cada pieza. Arrastra etiqueta/telas/mapeo con `_migrar_nombres_pieza`.

**Front (hecho 2026-09-02, probado en el navegador):** el nombrado vive **en el paso Arte**, en el
panel de la derecha (`panelNombrarJSX`, prop nueva `panelFijo` del visor: en el camino B ese panel
reemplaza al de «Diseños», que estaría pidiendo un arte que este molde no lleva). Lista con la
**miniatura del contorno** de cada pieza —con nueve «sin nombre» es lo único que deja saber cuál es
cuál—, su medida, chips con los nombres del catálogo del sistema, y un contador «Faltan N de 9».
El botón «Cargar arte» se esconde. Verificado de punta a punta: nombrar «Frente», «Espalda» y dos
«Manga Corta» dejó **«Manga Corta 1» y «Manga Corta 2»** (el desambiguado del camino A), el gate
«Asignar arte» pasó a verde con 9/9 y el panel de telas reconoció los 6 genéricos.
🔴 Después de renombrar hay que **volver a pedir la detección** (`cargarMoldeOperario`): los
nombres que muestra el panel salen de ahí (`nombres_existentes`), no del catálogo — sin eso el
nombre se guardaba bien y la pantalla seguía diciendo «sin nombre».

### [x] E4 — El motor: la tizada desde el molde con diseño — **HECHO** (2026-09-02)

**La tizada sale.** Verificado generando la hoja completa del archivo real y **mirándola**:
`HOJA_Principal.pdf` de 180 × 77 cm con las 9 piezas estampadas (patrón, escudo, logos), su borde
de corte y su etiqueta («XS · Espalda · #01»). Contrato: `verificar_tizada_con_diseno.py`.

- `generar_pedido(plantilla, arte=None, …)`. La rama se elige por **la marca en disco**, nunca por
  «no vino arte»: sobrevive al ProcessPool del nesting y no adivina nada del archivo.
- **`pagina_molde(mesa, talle)`** — la mesa del propio molde con sólo la capa del talle
  (`aislar_capa` + `sanear_oc`). 🔴 **NO se puede reusar `pagina_arte`**: ése llama a
  `limpiar_capas_conservando_talle(..., geometrias_base(...))`, que descarta los trazados que
  coinciden con la moldería base **y todo el texto** — y acá la moldería base ES el dibujo, así
  que borraría la pieza entera. Medido sobre la mesa 1: de 140 recortes / 1320 rellenos (las 20
  capas encimadas) quedan 7 / 66 y los textos del talle.
- La rama de `_armar_base` es, paso por paso, **el ramal del arte clásico** con la página sacada
  del molde: misma traslación, mismo clip, misma escala. Se saltea todo lo del arte separado
  (`mesa_arte`, `cm_encajar`, editables, objetos agregados): la pieza ya está en su lugar y a
  tamaño real. Verificado: 48,7 × 73,8 cm contra 48,5 × 73,6 del registro (la diferencia es el
  borde de corte).
- Servidor destrabado: `generar_multi` (antes descartaba el molde **en silencio** por no tener
  `validacion_arte.json` → la tizada llegaba sin sus piezas), `generar`, `estado_general` y
  **`_piezas_base`** — este último no es opcional: si el preview no pasa por la misma rama del
  motor se rompe la LEY «el arte se ve igual que la tizada». La clave del caché sube a `v15` con
  el camino B adentro.

**El nombre y el número: LOS TRAE EL ARCHIVO** (decisión del usuario, 2026-09-02, ver el requisito
en §3.b). El archivo con el que se probó tiene 20 capas y las 20 son talles, así que la tizada
salió con el «NOMBRE» dibujado en el diseño: no hay de dónde sacar el placeholder. La convención
queda: capas `nombre` y `00` (pueden ser subcapas y estar dentro de la máscara). El rótulo `00` se
traduce solo al campo `numero`, porque el estampado busca `persona[campo]` por el nombre de la
capa. ⚠️ **Falta probarlo contra un archivo que las traiga** — cuando exista, correr
`verificar_tizada_con_diseno.py` y mirar que salgan estampados.

## ⚡⚡⚡⚡ SEGUNDOS, NO MINUTOS (2026-09-07) — la carga y la tizada de 5, con todos los caminos

**El pedido**: «cargar `CAMISETA JUGADOR.ai` demora 1 minuto; buscá todos los caminos posibles
para que demore segundos y milisegundos; y la tizada de 5 camisetas tardó 45 s». Changelog 394.

### Dónde se iba el minuto de la carga (medido en el 8051, 2026-09-07 a la mañana)

| tramo | s | causa |
|---|---|---|
| `POST /api/plantilla` (lo que el usuario espera) | **25** | contornos de 9 mesas con 6 procesos: 16 s de pared |
| · de esos, la mesa 2 sola (`get_drawings`) | 8,4 (15 con la máquina cargada) | 5.796 trazados, la mayoría del DISEÑO |
| · registro + visor + guardar + copiar | ~3 | |
| páginas por talle (segundo plano) | 31 | `_raspar_instrucciones` × 20 talles × 9 mesas |
| sha1 del archivo (123 MB) | 0,2 | lo que cuesta reconocerlo |

Los 16 s no eran «muchas mesas»: eran **una** (la más pesada) y PyMuPDF haciendo un trabajo que
no hacía falta. `get_drawings` devuelve cada punto como `fitz.Point` y cada rectángulo como
`fitz.Rect`; con 400.000 operadores de diseño por mesa eso son millones de objetos Python para
quedarse con 140 recortes. `get_cdrawings` (la misma función, cruda) tarda 2,2 s en la misma
mesa. Los 7 s de diferencia eran envoltorios.

### Los caminos de la carga (todos), con lo que dan y lo que cuestan

| # | camino | qué da | contras | estado |
|---|---|---|---|---|
| 1 | **`get_cdrawings`** y convertir sólo el trazado elegido | contornos 16 → 5 s (9 procesos); 180/180 iguales | ninguno (switch `TIZADA_DIBUJOS_LEGACY=1`) | **hecho** |
| 2 | **caché por hash del archivo** (`datos/desplegado_cache/<sha1>/`) | el mismo archivo otra vez: sin desplegar nada, ni contornos ni páginas | 120 MB por archivo (se guardan 6); hay que subir `_CACHE_DESPL_VERSION` si cambia el formato | **hecho** |
| 3 | contornos por sello no se rehacen; un proceso por mesa (núcleos − 1) | el re-alta 18 → 3 s; las 9 mesas a la vez | 9 × ~200 MB de RAM durante 5 s | **hecho** |
| 4 | responder la subida **al instante** y desplegar en segundo plano con avance en pantalla | subida percibida ~1 s; «nombrar piezas» espera lo que falte (5 s) con cartel honesto | front: estado «preparando el molde» + polling en `subirPlantilla`; el registro/visor llegan después | pendiente (plan: `POST` devuelve `preparando: true`, `_prewarm` arma alta+registro, `GET /api/plantilla/estado`) |
| 5 | contornos desde el **content-stream parseado** (pikepdf, sin MuPDF) | parsear la mesa 2 cuesta 1,8 s y ya se hace para las páginas: contornos «gratis» | reimplementar CTM (`q/Q/cm`), rutas y `W n` por capa: es el intérprete de MuPDF en chico; contrato obligatorio contra `get_cdrawings` | pendiente, sólo si el 5 s molesta |
| 6 | páginas por talle **sólo de los talles del pedido** cuando la tizada llega antes que el segundo plano | el motor no espera 30 s si el usuario tiza enseguida | dos formatos de `m{mesa}.pdf` (parcial/total) y sello por talle | pendiente |
| 7 | flate nivel 1 al escribir el desplegado | páginas 32,6 → 28,8 s | +10 % de disco | **hecho** |
| 8 | la transferencia de 123 MB | en local es 1 s; en la app web será EL cuello (depende de la conexión) | no se resuelve en el servidor: subida directa al almacenamiento + alta asincrónica (camino 4) | anotado |

No hay camino a «milisegundos» para la PRIMERA carga de un archivo de 123 MB: hay que leerlo por
lo menos una vez. Milisegundos es lo que cuesta la segunda (camino 2: reconocerlo son 0,2 s).

**Medido por HTTP contra el 8051 después de todo esto** (`prueba_cache.py`, molde efímero propio):
`POST /api/plantilla` **25 → 11,4 s** la primera vez que se ve el archivo (contornos 5 s + 123 MB
por la red local + registro/visor/DB + arrancar 9 procesos); páginas por talle listas a los 34 s
y la caché guardada 4 s después; **1,0 s** la segunda subida del mismo archivo, ya con las páginas
y los placeholders (la tizada no tiene que esperar nada). El servidor imprime
`[tiempos] subida de <archivo>: N s`.

### Dónde se iban los 45-51 s de la tizada de 5 (y qué quedó)

| etapa | antes | después | cómo |
|---|---|---|---|
| armar bases | 1 | 1 | ya estaba (hoja compartida) |
| nesting | 1-2 | 2 | — (E7: memoria de tizada) |
| escribir la hoja | 6 | 0 | intermedia sin comprimir (`compress_streams=False`): la aplana el RIP igual |
| previews | 8 | 3 | SVG de cada base cacheado en disco; 🔴 la clave llevaba el nombre AL AZAR del XObject y no acertaba nunca |
| validar | 5-6 | 0 | las bases `/TizadaBase` no se re-parsean |
| aplanado RIP | 15 | 4 | bases no se re-parsean + flate nivel 1 (guardar 6,9 → 1,7 s) |
| perfil ICC (rastrear RGB + incrustar) | ~5 | ~1 | sin arte no hay RGB que buscar |
| verificación RIP | ~6 | ~1 | sin re-correr `validar_salida` (el CLI sí lo hace) |
| ficha técnica | ? | medido ahora | cronómetro del pedido entero: `[tiempos] pedido <tid>` |
| **total** | **51 (motor 21 + rip 15 + post 15)** | **~15** | |

Lo que queda por sacar (con plan): previews 3 s = leer 27 SVG (39 MB) + escribir el archivo
→ armarlos DESPUÉS de marcar el trabajo listo (el usuario abre la preview unos segundos más
tarde; `trabajos[tid]["preview"] = "armando"`); la tizada entera en un proceso (E6) para que el
servidor no se bloquee mientras tanto; memoria de tizada (E7).

### El borde de corte: cómo se dibuja y de dónde sale (2026-09-07, tarde)

El archivo real trae, por pieza, DOS cosas: la máscara de recorte del diseño y una **línea de
corte dibujada** (un trazo de 2 mm, negro CMYK, centrado en su propio trazado, que es 0,5 a 4 mm
más grande que la máscara). Hasta hoy el sistema tomaba un recorte como contorno y dibujaba SU
borde encima → dos bordes (1 mm negro de ellos + 3,5 mm nuestros), «el borde parece de más de
3 mm». Decisión del usuario: **«que los cambios los haga en el borde que viene»**.

Regla:
1. **Contorno de la pieza = su línea de corte** (el recorte sin rellenos que envuelve a la
   máscara y tiene un trazo). Es lo que se nestea, lo que recorta el diseño y por donde va el
   borde. Si el archivo no trae línea, el contorno es la máscara del diseño.
2. **La línea se saca del dibujo** al desplegar (`quitar_linea_de_corte`: el `S` pasa a `n`) y
   se guarda su ancho y color exactos en `m{mesa}.json["linea_corte"]`.
3. **La base la vuelve a trazar UNA sola vez**: con el borde configurado (ancho, color y de qué
   lado: «fuera» = hacia afuera; «centro» = mitad y mitad; «dentro» = todo sobre el diseño), o,
   con el borde APAGADO, tal cual venía en el archivo (después del diseño, donde estaba).
4. **Sin franja blanca.** Entre la máscara del diseño y la línea de corte el diseñador dejó
   0,5-2 mm que en el archivo tapaba la mitad interior de su trazo. Con «fuera», la base traza
   también esa mitad interior (ancho de la línea original, color del borde): el borde arranca
   donde arrancaba el del archivo y sigue hacia afuera con el ancho configurado. Reporte del
   usuario 12:10 («queda ese desfasaje»); antes de esto la franja se veía blanca.

**Lo que se aprendió**
· 🔴 En Windows un script que use `ProcessPoolExecutor` sin `if __name__ == "__main__"` se
  re-ejecuta entero en cada worker: la primera medición «con 6/9/12 procesos» corrió en serie, en
  loop, y dejó 11 procesos huérfanos que inflaron todas las cifras (mesa 2: 15 s en vez de 8).
  Antes de medir: listar los `python.exe` vivos con su línea de comando.
· `get_drawings` vs `get_cdrawings`: cuando lo caro es el diseño y lo que se busca son los
  recortes, la conversión a objetos es el costo, no MuPDF.
· Una clave de caché no puede llevar nada que se genere al azar (`add_resource` sin nombre).
· `pikepdf.settings.set_flate_compression_level(1)`: 4× más rápido al guardar, sin pérdida.

## ⚡⚡⚡ LA HOJA COMPARTIDA (2026-09-04) — la tizada deja de ser lineal en prendas

**El problema.** 5 prendas = 180 s en el servidor (70 s en frío). Cada prenda repetía TODO el
trabajo: la pieza se serializaba y reabría (`out.save` + `fitz.open`), la hoja llevaba **una copia
entera de la mesa por colocación** (45 copias, 29 MB) y el aplanado para el RIP las des-anidaba
inline (900.000 operadores, 87 s). A 100 prendas eran más de 40 minutos y 580 MB.

**La idea (del usuario): «primero se acomoda el contorno y después se le pone el diseño adentro,
guardando información».** Se separa lo invariante de lo que cambia por prenda:

| | qué es | cuántas veces |
|---|---|---|
| **Base** | pieza de un (pieza, talle): la página desplegada metida adentro por concatenación de bytes + clip al contorno + borde de corte. UN Form XObject plano. | una por base (9 × talles usados) |
| **Colocación** | `q <cm> /B_k Do Q` + `q <cm> <estampado> Q` — el estampado son los trazos por prenda (nombre/número en curvas, etiqueta) | una por prenda |
| **Máscara del nesting** | el polígono del contorno pintado a 4× (+ borde), sin dibujar el arte | una por geometría |
| **Aplanado RIP** | un nivel: la página conserva sus `Do`; el interior de cada base se sanea una vez | una por base |
| **Preview** | `<symbol>` por base + `<use>` por colocación | una por base |

Archivos: `hoja_pike.py` (compositor, preview), `motor_pedido.py` (`_armar_base` deja `despl`/`nom`,
`generar_pieza` devuelve `{base, estampado}`, `_DocPerezoso`, `_nestear_y_componer` elige compositor),
`nesting_contorno.py` (`_mascara_contorno`, `poligonos_contorno`), `aplanar_rip.py`
(`_aplanar_un_nivel`, `_unificar_icc`, OutputIntent conservado), `servidor.py` (ICC después del
aplanado, verificación RIP al final, `_cbt`). Switches: `TIZADA_HOJA_LEGACY`, `TIZADA_MASCARA_LEGACY`,
`TIZADA_APLANADO_TOTAL`.

**Lo que va al RIP** (decisión del usuario 2026-09-04: «que lo lea cualquier RIP desde 2020 y el
perfil y el CMYK estén incrustados de verdad»): estructura PDF/X-1a-like — PDF 1.6, sin capas, sin
transparencia, XObjects de UN nivel, fuentes embebidas o en curvas, sólo CMYK/Gray/ICC-4, un ICC
por perfil, OutputIntent GTS_PDFX. `verificar_rip_compatible.py` lo chequea al terminar cada tizada
(aviso en pantalla si algo falla). El «error RIP» que originó `aplanar_rip` era con TRES niveles
anidados + capas; eso ya no existe por construcción. Pendiente: probar una hoja en una imprenta real
(`py verificar_rip_compatible.py HOJA.pdf --muestra` deja `HOJA_muestra_rip.pdf`).

**Medido (5 prendas, 3 talles, en frío)**: 70 s → 40 s; hoja 46 → 21 MB; previews 64 → 39 MB;
mismas colocaciones → 0,1 % de píxeles distintos (bordes de piezas giradas, redondeo de la `cm`);
aplanar no cambia un píxel. Y de paso se cerró una grieta de la ley «se ve = sale»: `_barrer_fuentes`
borraba las fuentes de la hoja y el aplanado eliminaba los textos vivos del diseño (1836 píxeles
distintos entre antes y después de aplanar la hoja de siempre; la nueva da 0, porque las bases
conservan sus fuentes embebidas).

**Lo que se aprendió**
· **MuPDF no dibuja `<symbol>`/`<use>`**: para verificar el preview hay que mirarlo en un navegador.
· Los ids de PyMuPDF en SVG (`cp0`, …) chocan entre documentos: prefijarlos por símbolo.
· `copy_foreign` exige objetos INDIRECTOS: `src.make_indirect(res)` antes de copiar.
· El signo del giro de `show_pdf_page` es +1 en PDF (y-up) y −1 en SVG (y-down): calibrado con el
  render, no asumido (con el signo al revés: 1,6 millones de píxeles distintos).
· 6 decimales también en la traslación de la `cm`; con 3, las piezas giradas caían medio punto corridas.
· Un contrato pesado que «se cuelga» puede ser el lanzador `py.exe` (0 % CPU) esperando a su hijo
  `python.exe` (100 %): mirar el hijo antes de matar nada. Y las cadenas de contratos matadas dejan
  huérfanos que ensucian toda medición: `wmic process where "commandline like '%verificar%'"`.
· 🔴 Matar procesos por «la línea de comando contiene X» desde un shell cuya propia línea de
  comando contiene X **mata al shell** (varias mediciones «fallaron» con exit 1 y sin traza por
  eso). Matar por PID, nunca por patrón; y nunca desde el mismo comando que lanza lo nuevo.
· Un objeto perezoso usado como booleano (`if p["doc"]:`) tiene que definir `__bool__`: si no,
  Python cae a `__len__` y materializa lo que quería evitar (170 s a 100 prendas).

Lo que sigue (plan E6/E7): bases pre-armadas en el alta (por procesos), la tizada entera en un
proceso, y el nesting a 300+ prendas (convolución incremental, bloques de idénticas, memoria de
tizada).

## ⚡⚡ EL MOLDE DESPLEGADO (2026-09-03) — el archivo se lee UNA vez, al cargar

**Pedido del usuario:** estudiar a fondo cómo `Prueba para tizada` maneja el archivo al cargarlo,
cómo hace para ser veloz y cómo arma la tizada en segundos; replicarlo o mejorarlo.

**Lo que hace el proyecto de referencia** (leído entero: `main.js`, `sceneBuilder.js`,
`assembly.js`, `nesting.js`, `pdfExport.js`, `heavy.worker.js`):
1. **Parsea el PDF una sola vez** con pdf.js a una *escena* en memoria: cada trazado con su matriz
   ya aplicada, las máscaras como contenedores, las capas por OCG (`sceneBuilder.js`). Todo lo
   demás —detectar objetos, acomodar, exportar— trabaja sobre esa escena y **no vuelve a abrir el
   archivo**.
2. Lo pesado (detectar por grilla, acomodar por silueta) corre en un **worker** con OffscreenCanvas.
3. La tizada en pantalla son **referencias** al dibujo original (`<use>`), no copias.
4. Exporta escribiendo un PDF **plano**: emite los trazados de cada pieza por colocación
   (`pdfExport.js` → `pathToPdfOps`), sin XObjects. ⚠️ Pierde cosas que acá son ley: pdf.js
   convierte a **RGB** (no CMYK exacto), aproxima degradados y patrones a un gris, ignora SMask.

**Lo que hacíamos nosotros, medido con cProfile sobre el pedido real de 5 prendas** (motor 356 s +
aplanado 542 s = 15 min):

| Dónde se iba | s | qué era |
|---|---|---|
| aislar el talle de cada (mesa, talle) | 119 | parsear de 398 mil a 1,2 millones de operadores por mesa, **una vez por talle, en cada tizada** |
| `get_drawings` de las 9 mesas | 109 | los mismos contornos que el alta ya había leído |
| `extraer_personalizacion` | 100 | tres recorridos del archivo entero, para no encontrar campos |
| `unparse_content_stream` en el aplanado | 367 | 🔴 acepta tuplas `(operandos, op)` y `ContentStreamInstruction`; con tuplas tarda **40×** (322 mil ops: 16,6 s vs 0,4 s) y todo se armaba con tuplas |
| re-parsear en cada nivel de anidado | 85 | página → envoltorio de `show_pdf_page` → pieza → mesa: cada nivel volvía a parsear lo que el de abajo acababa de escribir |

Es decir: **328 de los 356 s del motor eran re-leer el archivo por pedido**, cosa que depende sólo
del archivo y no del pedido. Ésa es la idea del otro proyecto, y acá se guardó **en disco**.

**Lo que se hizo:**
- **El desplegado** (`piezas_con_diseno.py`, sección «EL MOLDE DESPLEGADO»). El alta deja en
  `entrada/<pid>/desplegado/`:
  - `m{mesa}.pdf` — **una página por talle**, con sólo ese talle, aislado y podado: **byte a byte**
    lo que `aislar_capa(podar=True)` producía en cada tizada (mismo código, corrido una vez), y
    sólo con los recursos que el contenido nombra (de 22 fuentes a 3 o 4).
  - `m{mesa}.json` — el **sello** del archivo (tamaño + fecha), el orden de los talles (= el de las
    páginas) y los **contornos** de cada talle, tal como los da `piezas_de_mesa`.
  - `personalizacion.json` — lo que calcula `extraer_personalizacion`, por sello. Y sin capas de
    campo (`nombre`/`00`) devuelve `{}` sin recorrer nada.
  `piezas_de_mesa` lee del JSON; `pagina_molde` del motor toma la página del PDF
  (`ruta_desplegada`); si el desplegado falta o el sello no coincide, **se arma en el momento** y
  sigue — un molde viejo se vuelve rápido la primera vez que se usa. Se borra con la carpeta del
  molde y al re-subir uno del camino A encima.
  🔴 **Son DOS ETAPAS** (2026-09-03, segunda tanda): la subida hace sólo los **contornos**
  (`paginas=False`; 54 s en serie, 10 s la mesa más pesada) y responde; las **páginas por talle**
  (107 s en serie, 20 s la más pesada) las arma `servidor._prewarm_desplegado` en un hilo, una
  mesa por proceso, cuando el archivo ya está en su lugar. El JSON lleva `paginas: true` sólo
  cuando el PDF está; si la tizada llega antes, `ruta_desplegada` arma esa mesa sola. Y el front
  manda `con_diseno=1`: el servidor deja de adivinar el camino (12,5 s). Medido por HTTP: la
  subida responde en **26 s** (era 64) y las páginas quedan 40 s después.
- **El alta, una mesa por proceso** (`desplegar_molde`, ProcessPool). Cada proceso lee los
  contornos de su mesa (`get_drawings`, como siempre) y parsea el content-stream **una vez** para
  filtrar los 20 talles (`molde_real._mapa_oc` + `_bloques_oc`, el árbol de bloques OC, +
  `_saltar_bloques` + `_raspar_instrucciones` — `_raspar_pintado` partido en piezas, con bytes
  idénticos al código anterior). El servidor pasa `procesos_render()`; los scripts van en serie.
- **El aplanado** (`aplanar_rip.py`): `_instr` (siempre instrucciones, nunca tuplas), `_flatten`
  memoiza las instrucciones ya aplanadas por objeto y las devuelve al nivel de arriba, y
  `_procesar_contenido` las recibe en memoria. **Pixel-idéntico** a la salida anterior en la hoja
  del camino B y en una hoja real del camino A. Sigue saliendo **totalmente plano**, como siempre
  y como el proyecto de referencia: la «decisión de aplanar un solo nivel» de más abajo **ya no
  hace falta**.

**Resultado (el mismo pedido de 5 prendas, 27 piezas distintas):**

| | antes | ahora |
|---|---|---|
| Motor (piezas + nesting + hoja) | 356 s | **24 s** (las 27 piezas se arman en 1 s) |
| Aplanado para el RIP | 542 s | **36 s** (hoja 46 → 28,7 MB, igual que antes) |
| `extraer_personalizacion` | 100 s | **0 s** |
| Alta (subir el molde) | ~60 s en serie | **55-71 s con 6 procesos**, desplegado incluido (en serie: 13-45 s por mesa) |
| **Subir + tizada + RIP** | no terminaba / 15 min | **115 s** |
| **Tizada + RIP con el molde cargado** | 15 min | **63 s** |
| Camino A, aplanar una hoja real | 10,6 s | **0,8 s** |

Costo: el desplegado ocupa **118 MB** por molde (9 mesas × 20 talles, 7,6 MB por mesa).
Contrato: `verificar_desplegado.py`. 🔴 Lo que NO se replicó del otro proyecto, a propósito:
convertir a RGB, aproximar degradados, rasterizar para acomodar. Acá el vector es exacto y CMYK
(leyes del proyecto); lo que se copió es **leer una vez** y **escribir plano**.

**Lo que queda para ir más abajo** (no hecho, medido): del motor, `validar_salida` recorre la hoja
(9 s) y `_barrer_fuentes` la reabre y reescribe; del aplanado, el `save` de 28 MB son 9 s y la
pasada de `_procesar_contenido` sobre 1,6 millones de instrucciones en Python otros ~10. Se puede
seguir, pero ya no es «re-leer el archivo»: es el trabajo real de escribir una hoja de 45 piezas
con un patrón de 16.505 curvas cada una.

---

## ⚡ EL PESO Y EL TIEMPO (2026-09-03) — la causa encontrada, y lo que falta *(superado por la sección de arriba)*

**Reporte del usuario:** «arme una tizada con un molde con diseño incluido, va 6 minutos y paso por
poco la mitad del proceso… y este sistema `Prueba para tizada` lo hace en segundos».

**La causa, medida:** el content-stream de una mesa trae **398.653 operadores** —los 20 talles
encimados— y, aislado un talle, **sólo 75 pintan**. El aislado convertía el pintado de los otros
talles en «no pintar» pero **dejaba los trazados escritos**, así que cada pieza de la tizada
arrastraba los 398 mil (7,6 MB). Una hoja de 5 prendas dio **586 MB** y el aplanado para el RIP
seguía sin terminar a los 20 minutos.

**Lo que se hizo** (`aislar_capa(..., podar=True)`, sólo camino B):

| | antes | ahora |
|---|---|---|
| Operadores por pieza | 398.347 | **20.186** (−94,9 %) |
| La pieza más pesada | 23,1 MB | **1,6 MB** |
| Hoja de 1 prenda | 117 MB | **9 MB** |
| Hoja de 5 prendas | 586 MB | **46 MB** |
| Pedido de 5 prendas | no terminaba en 18 min | **11,5 min** |

🔴 Y **no cambia un pixel**: el contrato compara el render de la página podada contra la sin podar
—6.475.275 píxeles— y da **0 distintos** (`verificar_poda_camino_b.py`). Se borran sólo los
operadores de construcción de trazado y los bloques OC **balanceados en `q/Q`**; nunca el estado
gráfico, que sí se hereda. Es *opt-in*: el camino A no cambió (sus contratos siguen verdes).
También se memoizó `_flatten` en `aplanar_rip.py`: aplanaba **el mismo XObject una vez por
colocación** (45 veces en ese pedido).

**Lo que quedó, y por qué el otro sistema tarda segundos.** De los 11,5 min, **402 s son el
aplanado para el RIP** y 288 s armar las piezas. Ya no hay basura que sacar: los 20.186 operadores
que quedan son **el trazado real del diseño** (16.505 curvas para 66 rellenos). La diferencia con
`Prueba para tizada` es estructural: él **parsea el PDF una vez y escribe un PDF plano** emitiendo
los paths de cada pieza (`pdfExport.js` → `pathToPdfOps`); nosotros componemos con XObjects y
después los **des-anidamos** para el RIP, y ese des-anidado mete el contenido *inline* una vez por
colocación (45 × 20.000 ≈ 900.000 operadores en el stream de la hoja).
📌 **La salida está identificada pero es DECISIÓN DEL USUARIO**: aplanar **un solo nivel** —dejar
las piezas como XObject de la página, aplanando sólo lo de adentro— daría 27 objetos y 45 `Do`,
sin anidamiento profundo y con el stream de la hoja chico. Toca la política del archivo que va a
la imprenta (`aplanar_rip.py` existe porque los XObjects anidados daban «error RIP»), así que **no
se cambia sin decidirlo con él**.

---

🔴 **EL PESO Y EL TIEMPO — MEDIDO DE PUNTA A PUNTA (registro de la medición vieja).**
Una tizada de **UNA prenda** (9 piezas, talle 1) desde la pantalla tardó **~21 minutos**:

| Fase | Tiempo |
|---|---|
| El motor entero (armar las 9 piezas, acomodar, escribir el PDF y las vistas previas) | **134 s** |
| **Aplanar la hoja para el RIP** (`aplanar_rip.py`) | **~19 min** ← el 90 % |

La hoja pesa **114 MB** y el archivo original 123. Y **ese peso no es basura**: se midió aislando
una mesa (7,6 MB) y `remove_unreferenced_resources()` no baja **nada** (0 %) — lo que pesa es el
dibujo, que en este archivo es un patrón vectorial densísimo. Cada pieza trae su mesa, y son 9
mesas distintas, así que compartir el XObject entre piezas de la misma mesa (la salida que se
había pensado) **acá no ayuda**.
Lo que hay que atacar es el **aplanado**, que es donde se van los 19 minutos, y es código del
camino A (des-anida los XObjects para que el RIP resuelva el color). **Sin medirlo no se toca**:
primero perfilarlo sobre esta hoja y ver si el costo está en el parseo del content-stream, en la
escritura o en el des-anidado. ⚠️ **La salida NUNCA es rasterizar ni bajar la calidad** (ley del
proyecto): si hay que elegir, se tarda con un cartel honesto — que es lo que hace hoy.

### [x] E5 — La configuración estable del admin (VIVA) — **HECHA** (2026-09-02)

**Cómo quedó:** `cat["config_con_diseno"]` (borde + forma de la etiqueta + regla de nesting) y **un
solo lugar donde se resuelve**: `_cfg_con_diseno` / `_borde_de` / `_etiqueta_de`. Por ahí pasan
ahora los seis puntos que antes leían `prod.get("borde_corte")` a mano: la clave del caché del
preview, el preview, `generar`, `generar_multi`, la ficha y los GET del molde. El nesting se
resuelve en `_config_produccion`, que ya era el único lugar que elegía el preset.
Endpoints `GET/POST /api/config_con_diseno` (el POST pide `config.editar` y devuelve **a cuántos
moldes alcanza**). `POST /api/productos/borde_corte` sobre un molde B devuelve **409**: si dejara
guardar, la pantalla parecería guardar y el motor seguiría leyendo el global.
🔴 Lo global es la **forma**; el **dónde** (`posiciones`) es del molde y lo marca el cliente — el
POST de la etiqueta conserva las posiciones aunque el cuerpo traiga otra cosa, porque ese endpoint
es *replace* y guardar una posición desde el pedido habría clavado la forma en el molde.
🔴 Que el valor **resuelto** entre en `_piezas_base_clave` es lo que hace que el cambio del admin
se vea solo en el paso Arte; si no, saldría bien en la tizada y viejo en la pantalla.
Contrato: `verificar_config_con_diseno.py`.

**La pantalla (hecha 2026-09-02, probada):** tarjeta **«Molde con diseño»** en Configuración, con
el borde (grosor, dónde va, si se dibuja), la etiqueta (tamaño de letra, separador, qué muestra) y
la regla de nesting. Arriba, el aviso de que **lo que se cambia vale para todos, también para los
ya cargados**, y a cuántos alcanza — porque no es lo que uno espera de una pantalla de config.
Verificado end-to-end: se cambió el borde a 3,5 mm y el molde con diseño pasó a leer 3,5 mientras
que un molde del camino A siguió en 2,0.

*(lo que sigue es el plan original de esta entrega)*
- Borde de corte, etiqueta y nesting por defecto **para este camino**, en el catálogo
  (`cat["config_con_diseno"]`), con el patrón de `nesting_presets`.
- **Viva** (decisión del usuario, 2026-09-02): el admin la cambia y **afecta a todos** los moldes
  con diseño, también a los ya cargados. Nada de copiar la config al molde en el alta.
- Lo GLOBAL es la **forma** de la etiqueta (tamaño, tipografía, color, qué muestra); lo del molde
  es el **dónde** (`posiciones`), que lo pone el cliente y muere con el pedido.
- Un único punto de resolución (`_borde_de` / `_etiqueta_de`) que lean los 8 lugares que hoy leen
  `prod.get(...)` directo — incluida **la clave del caché del preview**, o el cambio no se ve.
- Pantalla en Configuración (no la ve el cliente).

### [x] E6 — La etiqueta: el cliente sólo marca dónde va — **HECHO** (2026-09-02)

Segunda solapa del panel del pedido («1 · Piezas» / «2 · Etiqueta»), que **se destraba con todo
nombrado**: sin nombre no hay qué escribir en la etiqueta. El cliente toca el borde de la pieza y
el punto se **apoya en el contorno** (punto más cercano + ángulo de la tangente, con la normal
hacia adentro para que el texto entre en la pieza). El panel lleva la cuenta («1 de 9 ubicadas»),
marca con un punto verde dónde quedó cada una y deja sacarla; las que no se tocan salen abajo y
centradas.

🔴 **La función del snap vive a nivel de módulo (`_snapAContorno`) y la usan LAS DOS pantallas** —
Configuración y el pedido. Con una copia en cada una, la etiqueta habría caído distinto según
dónde se la ubicara.
🔴 Se manda **sólo `posiciones`**: la forma es del admin y el POST de la etiqueta es *replace*.
Verificado: tras guardar desde el pedido, `size_mm` seguía siendo el del admin y `forma_global`
`true`. Y se tira el caché del preview, o el paso Arte mostraría la etiqueta en el lugar viejo.
⚠️ La cascada de posiciones del motor no se tocó ([[etiqueta-baseline-no-romper]]): estas claves
son el **nombre completo de la pieza**, que es el nivel que ya manda (§10.c del MAPA).

### [~] E7 — Que todo lo demás siga igual — **la traba de tela, HECHA** (2026-09-02)

**Pedido completo verificado desde la pantalla**: subir → nombrar 9 piezas → asignar la tela →
cargar una fila → generar. Sale la hoja (1,60 × 0,48 m) con su ficha técnica. Y **los toggles
funcionan solos**: la planilla mostró «Larga» deshabilitado con el aviso *«El molde "Camiseta
jugador" no contiene manga larga»*, deducido de los nombres que puso el cliente.

- 🔴 **La traba «pieza sin tela»** recorría `variante_piezas`, que en un molde sin variables viene
  vacío: no validaba **nada** y todas las piezas se habrían ido a la tela fantasma «Principal» de
  180 cm — justo lo que esa traba existe para evitar. Ahora, sin variable, las piezas de la fila
  se calculan con **`MP.partes_de_libre`**, que es `partes_de` sacado del motor a nivel de módulo
  (como ya estaba `tokens_pieza`, y por el mismo motivo: si el servidor validara con una regla
  propia, diría una cosa y el motor haría otra). Se aplican los toggles, así que **no** se reclama
  tela para la manga larga en un pedido de manga corta. Contrato: `verificar_traba_pedido.py` §3.

**«Terminar pedido»** (2026-09-02): botón propio en Resultados, que aparece **sólo si el pedido
tiene un molde con diseño**. Cierra el pedido y lo borra. 🔴 La lista de qué borrar **no sale sólo
de `moldesEfimeros`** (lo que subió esa pantalla): se le suman los moldes del pedido que el
catálogo marca `efimero`, porque si se recargó la página con el localStorage vacío ese estado no
los tiene y el archivo de 100+ MB se quedaría hasta que lo junte el barrido. Borrar de más no es
riesgo: el servidor sólo toca los que llevan la marca.
Verificado de punta a punta: el modal avisa qué molde se pierde y con él los nombres; al confirmar,
no queda nada (ni datos, ni base) **y las tizadas generadas siguen ahí**.
- Ficha técnica, trabas antes de fabricar, ayuda guiada, permisos.
- 🔴 **La traba «pieza sin tela»**: `_validar_pedido` itera `variante_piezas`, que en el camino B
  viene vacío (el molde va entero, sin variables) → ninguna pieza se valida y todas caerían a la
  tela fantasma «Principal» de 180 cm, que es lo que esa traba existe para evitar. Hay que validar
  sobre las piezas que REALMENTE entran en la fila (`partes_de`, con los toggles ya aplicados).
- **Talles y toggles NO necesitan trabajo**: `piezas_de` sin variable devuelve `partes_de`, o sea
  todas las piezas filtradas por los toggles, que se resuelven por los tokens del NOMBRE de cada
  pieza. Por eso el nombrado es lo que los habilita (una pieza «Manga 1» hace que elegir Corta o
  Larga dé lo mismo) y conviene avisarlo al nombrar, no al generar.
- Contratos verdes y el MAPA actualizado.

---

## 8. DÓNDE ESTÁ CADA COSA (los archivos que toca este camino)

| Qué | Dónde |
|---|---|
| Detección nueva | `piezas_con_diseno.py` |
| **El molde desplegado** (una página por talle + contornos, escrito al cargar) | `piezas_con_diseno.py` («EL MOLDE DESPLEGADO»: `desplegar_molde`, `desplegar_mesa`, `ruta_desplegada`, `personalizacion_guardada`) → `entrada/<pid>/desplegado/` |
| Parsing del molde y capas OCG | `molde_real.py` (`extraer_piezas_mesa`, `aislar_capa`, `_mapa_oc`/`_bloques_oc`/`_saltar_bloques`/`_raspar_instrucciones`) |
| Aplanado para el RIP (instrucciones, nunca tuplas; memo por objeto) | `aplanar_rip.py` (`_instr`, `_flatten`, `_procesar_contenido`) |
| Armado de la pieza y estampado | `motor_pedido.py` (`_armar_base`, `generar_pieza`) |
| Acomodo y hoja final | `nesting_contorno.py` |
| Alta del molde propio | `servidor.py` (`/api/productos/crear`, `/api/plantilla`) + `App.jsx` (`modoMiMolde`) |
| Nombrado de piezas y agrupado entre talles | `App.jsx` (`NombrarVariantes`) + `MAPA §10.c` |
| Etiqueta | `motor_pedido.py` (`_eops_*`) + `prod["etiqueta"]` |
| Referencia del algoritmo | `…\Prueba para tizada\src\core\{assembly,shape,nesting}.js` |
| Archivo de prueba | `…\Downloads\PRUEBA TIZADA PRO\para acomodo de archivos\CAMISETA JUGADOR.ai` |

---

## 9. CÓMO PROBARLO

```bash
py verificar_molde_con_diseno.py
```

El desplegado (bytes idénticos al aislado de siempre, píxeles, contornos, sello, alta en paralelo;
tarda unos minutos):

```bash
py verificar_desplegado.py
```

La tizada de punta a punta (alta + motor + hoja) y la poda:

```bash
py verificar_tizada_con_diseno.py
```

```bash
py verificar_poda_camino_b.py
```

```bash
cd frontend && npm run build
```

Y **reiniciar el server** (si no, sigue corriendo el Python viejo en memoria):

```bash
REINICIAR-SERVIDOR.bat
```

⚠️ Comprobar el reinicio por **hora de arranque del proceso**, no por `/api/salud`
(ver [[reiniciar-server-python]]).

Para mirar qué trae un archivo sin abrir nada, desde el proyecto de referencia:

```bash
node scripts/analyze-layers.mjs "ruta/al/archivo.ai"
```

---

## 10. BITÁCORA (una línea por sesión — qué se hizo, qué falló, qué se aprendió)

- **2026-09-07 (segundos, no minutos)** — Ver changelog 394 del mapa y la sección «SEGUNDOS, NO
  MINUTOS». Carga: `get_cdrawings` (7 de los 9 s de la mesa 2 eran envoltorios `Point`/`Rect`
  del diseño), contornos por sello, caché por hash del archivo, un proceso por mesa; tizada:
  bases `/TizadaBase` sin re-parsear, hoja intermedia sin comprimir, SVG de base cacheado con
  clave estable, flate nivel 1, servidor sin rastreo RGB ni re-validación. Lo que salió mal: el
  primer medidor sin `__main__` corrió en serie y dejó huérfanos (cifras infladas ×2); la caché de
  SVG no acertaba por el nombre al azar del XObject; un `os.replace` del worker choca con quien
  tenga el JSON abierto (Windows) y el pool «fallaba» en silencio a serie → `_reemplazar` con
  reintento. Después, con la primera tizada del usuario: la fuente Moreggi sin cmap unicode
  (`_cmap_de_respaldo`), y **el contorno era la línea de corte dibujada y no la máscara del
  diseño** (0,5-4 mm de más: franja blanca entre estampado y borde) → el recorte con rellenos
  adentro manda (`_rellenos_por_clip`), desplegado con versión de contornos, ficha con molde
  guía en el camino B, `_desplegar_en_fondo` para moldes ya cargados. Y el que de verdad
  explicaba la foto del usuario: `ops_cont` le sumaba el desplazamiento al ANCHO y ALTO de un
  segmento `re` (piezas rectangulares): el clip del borde salía 3,7 cm más angosto. Lección:
  cuando «sólo pasa en algunas piezas», leer el content-stream de la base de UNA de esas
  piezas (los números cantan: 600,112 = 704,976 − 104,864) antes de tocar la detección.
  Al final, la decisión de fondo: **la línea de corte del archivo es el borde** (sección «El
  borde de corte: cómo se dibuja y de dónde sale»): contorno = esa línea, se saca del dibujo
  al desplegar y la base la traza una sola vez con la configuración (o tal cual, apagada).
  Verificado en las 180 piezas del archivo real (9 mesas × 20 talles): línea detectada, estilo
  guardado (2 mm, K=1) y ninguna queda dibujada en las páginas.
  **Y «Armar con base» (camino A) a la misma velocidad** (pedido de las 14:00): la clave de la
  caché de previews llevaba una tupla (bug mío del mediodía) y nada acertaba → 5 s por talle;
  arreglado (string), sin conversiones duplicadas y en paralelo: 1,3 s un talle nuevo, 0,1 s en
  caché. La tizada del camino A usa la misma preview por símbolos que el camino B, con caché de
  SVG al lado del arte (`svg_cache/`) y bases en paralelo: 15 → 10 s la primera vez, 2,3 s
  después. Ver changelog 394 del mapa.
- **2026-09-04 quinquies (la hoja compartida)** — Ver changelog 393 del mapa y la sección «LA HOJA
  COMPARTIDA». Plan aprobado por el usuario (bases compartidas, aplanado de un nivel, PDF/X-1a-like,
  preview con símbolos, escala a 300+). Entregadas E0-E5 en una tanda; medido 5 prendas 70 → 40 s
  en frío. Lo que salió mal en el camino: el ancla del parche del motor era ambigua (el ramal del
  arte clásico tiene las mismas líneas); `copy_foreign` con un dict directo; el signo del giro al
  revés; MuPDF sin `<use>` (la comparación automática del SVG daba basura y el navegador lo dibuja
  bien); y cuatro contratos huérfanos comiendo CPU que hacían parecer lento todo.
- **2026-09-04 quater (el servidor congelado un minuto)** — Ver changelog 392 del mapa. Lo que
  se aprendió:
  · 🔴 **pikepdf y PyMuPDF retienen el GIL.** Cualquier trabajo pesado con ellos dentro de un
    hilo del servidor (un request, o un `threading.Thread` «de fondo») congela TODOS los
    requests. Va en un proceso (`ProcessPoolExecutor`) o no va. El hilo de fondo sólo debe
    ESPERAR procesos.
  · **«Si falta, lo armo acá» es una trampa dentro de un request**: parece cómodo y es lo que
    congeló todo. Un request responde «preparando» y el front re-pregunta; construye sólo el
    que tiene que construir (el hilo de fondo por procesos, o el motor de la tizada).
  · **Un candado por recurso** cuando dos caminos pueden construir lo mismo: el segundo espera y
    encuentra hecho. Sin eso hubo doble trabajo y un `m1.json.tmp → m1.json` con «Acceso
    denegado» (dos escritores).
  · **Un caché de «todavía no está» es un caché que miente**: si la clave no cambia cuando la
    cosa aparece, el caché lo esconde para siempre. No cachear la ausencia.
  · **py-spy es la herramienta**: `py-spy dump --pid <servidor>` mostró el hilo culpable en un
    segundo, cuando el log no decía nada.
- **2026-09-04 ter (los bugs del pedido con la configuración)** — Ver changelog 391 del mapa. Lo
  que se aprendió:
  · **Todo estado que «tapa» una pantalla necesita TODAS sus salidas.** `desdePedidoB` oculta el
    pedido y el panel de configuración a la vez; con una sola salida («← Volver al pedido»), la
    barra dejaba la app en blanco. Al agregar un modo así, listar cada botón que cambia de
    pantalla y hacer que lo cierre.
  · **Un estado único por pantalla (`etiquetaConfig`) se desactualiza al cambiar de molde**: lo
    que lo lea tiene que recargarlo al elegir otro molde, o muestra lo del anterior.
  · **Los filtros «por arte cargado» excluyen al camino B sin querer** (`arteCargado[…]`): cada
    vez que algo se filtre así, preguntarse qué pasa con un molde que trae el diseño adentro.
  · **Un efecto que corre al montar puede correr ANTES de que llegue el catálogo**: si decide
    algo según `productosCat`, tiene que depender de él (`_idsCat`).
  · **Nunca dejar una pantalla intermedia visible detrás de un `await`.** Abrir la moldería
    DESPUÉS de esperar al servidor mostraba la grilla del taller mientras tanto; si la espera
    fallaba, el cliente quedaba adentro de Configuración. Primero el estado que define la
    pantalla, después la espera — y una guardia en el render por si igual falta algo.
  · **«Los míos» no es «los que veo»**: un admin ve los efímeros de todos; el pedido tiene que
    filtrar por dueño (`de_otro`) o abre y nombra moldes ajenos.
- **2026-09-04 bis (la herramienta sin Configuración, y el orden del archivo)** — Ver changelog
  388 del mapa. Lo que se aprendió:
  · **«La misma herramienta» y «que no entre a los ajustes» son compatibles**: se renderiza la
    MISMA pantalla desde la pestaña Pedidos y se apaga todo lo que es del taller
    (`_soloHerramienta`). El deep-link anterior encima le mostraba Configuración a alguien sin
    permiso `config.ver` — el permiso gatea el botón del menú, no el render.
  · 🔴 **«Que respete cómo viene» era literal: NO ACOMODAR.** Dos intentos fallidos antes de
    entenderlo —grilla compacta por talle, después una fila por talle— y los dos partían de la
    misma idea equivocada: que había que *acomodar* las piezas. No. Los talles vienen encimados
    (la gradación) y así se muestran; se distinguen por la CAPA. Lo único que se acomoda son las
    mesas, y sólo porque el PDF las guarda todas en (0,0). **Cuando el usuario dice «tal cual el
    archivo», la respuesta correcta suele ser sacar código, no agregar otro acomodo.**
  · **El acomodo de las mesas se calcula una vez con todos los talles**: por talle, el molde se
    movería al cambiar de talle en el visor.
- **2026-09-04 (las pantallas de configuración, «00»/«NOMBRE» por texto, y el cuelgue)** — Ver
  changelog 387 del mapa. Lo que se aprendió:
  · **«La misma herramienta» quiere decir la misma pantalla, no una parecida.** La versión propia
    del pedido (386) se reemplazó por abrir Moldería y la pestaña Etiqueta con «← Volver al
    pedido». Lo que hubo que hacer fue que los endpoints de esa herramienta entendieran el
    camino B (`emparejado`, `grupo_pieza`, `variantes`, `deteccion_todas`), no copiar la UI.
  · **El «00» no se ve con PyMuPDF.** Viene como código 31 con `/Differences [31 /0]`; hay que
    decodificar el content-stream con la codificación de la fuente. Se detecta por texto, en la
    etapa de páginas, y se saca del dibujo ahí mismo.
  · **Un `get_drawings()` del archivo entero dentro de un request cuelga el servidor** (GIL,
    4,5 GB, minutos): `py-spy dump` lo mostró en `/api/plantilla/variantes`. Antes de dar por
    «colgado» un servidor, mirar la pila.
  · **`nohup` sin `PYTHONUNBUFFERED=1` se come los prints** hasta que el proceso muere: los
    «[camino B] …» del log no aparecían.
  · ⚠️ **«Nuevo pedido» desde otra sesión borra los efímeros del pedido que había en ESE
    navegador**, sean de quien sean (`limpiar_efimeros` no mira dueño). Se llevó el efímero del
    taller de ayer. Pendiente: filtrar por dueño en ese endpoint.
- **2026-09-03 (segunda tanda: la subida en 26 s, y nombrar / etiqueta como en Moldería)** — Ver
  changelog 386 del mapa. Lo que se aprendió:
  · **No adivinar lo que el usuario ya dijo.** 12,5 s de cada subida eran mirar dos mesas para
    saber si el archivo traía diseño… cuando el archivo entraba por el botón «molde con diseño».
  · **Separar lo que la respuesta necesita de lo que necesita el motor.** Las páginas por talle
    (107 s en serie) no las mira nadie hasta la tizada: van en segundo plano. El desplegado quedó
    en dos etapas con un flag en el JSON, y el motor arma la mesa si llega antes.
  · **El lienzo de todos los talles se acomoda en grilla**, no en columna: 20 talles apilados eran
    una tira de 26 m y al «ver todo» no se veía nada.
  · **Probar en el navegador con la sesión correcta.** El primer renombrado dio 403: la lista
    mostraba un molde efímero de otro usuario (el del taller) y la guarda de dueño hizo lo suyo.
- **2026-09-03 (el molde desplegado: de 15 min a 63 s)** — Se estudió `Prueba para tizada` entero y
  se replicó su idea central —**leer el archivo una vez y escribir plano**— guardándola en disco
  (`desplegado/`), sin copiar lo que rompería las leyes del proyecto (RGB, degradados
  aproximados, rasterizar). Lo que se aprendió:
  · **Perfilar antes de tocar.** La intuición decía «el aplanado es lento porque des-anida 900 mil
    operadores»; cProfile dijo que **367 de 542 s eran `unparse_content_stream` con tuplas** (40×
    más lento que con instrucciones) y que el motor gastaba 328 de 356 s **re-leyendo el archivo**
    por pedido. Ninguna de las dos se veía leyendo el código.
  · **Medir con la máquina ocupada engaña.** El alta en serie dio 403 s corriendo junto a otras dos
    pruebas pesadas; sola y optimizada, la mesa 1 tarda 13 s.
  · **«Bytes idénticos» es el contrato correcto para un refactor de content-stream**: partir
    `_raspar_pintado` en cuatro funciones se verificó comparando la salida del módulo viejo (de
    git) contra el nuevo, con y sin poda, en tres mesas. Para el aplanado, que cambia nombres de
    recursos, el contrato es **pixel-idéntico** (camino B y camino A).
  · ⚠️ El servidor de prueba «8051» escuchaba en **8070**: `curl` a 8051 daba 000 y `netstat -ano`
    lo mostró. Comprobar el puerto con `netstat`, no con lo que dijo la sesión anterior.
  · ⚠️ `py -` con heredoc funciona; `python -` no (no está en el PATH: abre la tienda de Windows).
- **2026-09-02 (cierre: E5 pantalla, E6 y «Terminar pedido»)** — El camino queda **completo de
  punta a punta**, probado en el navegador: subir → nombrar 9 piezas → ubicar la etiqueta → tela →
  planilla → generar → cerrar. Lo que se aprendió en esta última tanda:
  · **Una regla, un solo lugar.** El snap de la etiqueta al contorno se movió a nivel de módulo
    (`_snapAContorno`) porque ahora lo usan dos pantallas; con una copia en cada una, la etiqueta
    caía distinto según dónde se la ubicara. Mismo criterio que ya se había aplicado a
    `partes_de_libre` en el motor.
  · **Lo que se manda importa tanto como lo que se guarda.** El POST de la etiqueta es *replace*:
    mandar el objeto entero desde el pedido habría clavado la forma en el molde y ese molde habría
    dejado de seguir al admin **en silencio**. Se manda sólo `posiciones`.
  · **No confiar en el estado del navegador para borrar.** «Terminar pedido» calcula qué borrar
    sumando los moldes del pedido marcados `efimero`, no sólo los que registró esa pantalla: tras
    un F5 con el localStorage vacío, el archivo de 100+ MB se habría quedado.
  · ⚠️ `verificar_tdz.mjs` cortó el build **tres veces** en la sesión, siempre por lo mismo:
    funciones nuevas escritas arriba de `showError`/`showMsg`/`plantillaComun`. **Se mueven debajo
    de lo que usan; el tope no se sube.** Conviene escribirlas directamente al lado de `showWarn`.
  · ⚠️ Y dos veces más la trampa de los **heredocs de bash**: JSX con comillas y `<>` no sobrevive.
    Los archivos se escriben con la herramienta de escritura ([[escrituras-atomicas]]).

- **2026-09-02 (E2 y E3, backend)** — El alta desde el pedido y el nombrado, probados **por HTTP
  con el archivo real de 123 MB**: alta completa en ~95 s (subida incluida), 9 piezas · 20/20
  talles, visor de 7 KB, nombrado que persiste, y el borrado del efímero que no deja nada
  (ni archivo, ni datos, ni filas en la base).

  **Lo que estaba roto y no se veía** (los tres habrían aparecido recién al generar la tizada):
  1. 🔴 **`idx_mesa` no se persistía.** El registro ya no tiene espejo en disco: vive **sólo** en
     MSSQL, y `dbo.pieza_talle` no tenía columna para él. Se evaporaba en el primer round-trip y
     `_armar_base` volvía a indexar por `pieza_idx` → con 9 mesas de 1 pieza, `IndexError` o la
     pieza equivocada. Se agregó la columna (`ALTER … NULL`, idempotente) y un chequeo cacheado
     `COL_LENGTH` para que una base sin migrar **degrade** en vez de reventar el camino A.
     🔴 Al LEER, la clave se pone **sólo si no es NULL**: el motor hace
     `info.get("idx_mesa", info["pieza_idx"])` y `.get` cae al default sólo si la clave **falta** —
     un `None` haría `_pm[None]` (TypeError) en **todos** los moldes del camino A.
  2. 🔴 **Dos cachés servían la detección vieja para siempre.** El alta DETECTA y marca DESPUÉS,
     así que la misma ruta con el mismo mtime da 9 piezas o 619 según esté marcada. `_DET_CACHE`
     ya lo contemplaba; `_PZS_CACHE` (contornos, en memoria) y el caché de detección **en disco**
     (`{mtime}_dv2_…`, ahora `dv3` + sufijo) no. Y el mtime es un entero de **segundos**: dos
     subidas en el mismo segundo servían lo del otro.
  3. **El visor no precargaba los nombres ya puestos** (`nombres_existentes` salía vacío): filtraba
     `info["mesa"] == mesa` y en el camino B `mesa` es `None`. Es la misma guarda que ya se le
     había puesto al filtro por variable, un poco más arriba, en la sesión anterior.

  **Lo que se aprendió (y cambia el diseño):** en el camino B **nombrar no es agrupar**. Todo el
  nombrado de hoy re-arma el registro para emparejar los talles por forma; acá los talles son
  capas de la misma mesa y ya están pareados desde el alta, así que re-armarlo sólo puede
  romperlo. Nombrar quedó en cambiar la clave de un dict, con las tres herramientas del camino A
  devolviendo 409 sobre un molde B.

  **Dos cosas que encontramos de paso y NO se tocaron** (son del camino A; anotarlas es la
  entrega): (a) en `/api/plantilla/etiquetas` el `_guardar_registro` quedó **después de un
  `return`**, o sea inalcanzable — ese endpoint hoy no persiste nada; moverlo resucitaría un
  camino de escritura viejo que nadie prueba, así que se decide aparte; (b) el pre-warm de
  `detectar_piezas_todas` corre PyMuPDF **en un hilo** sobre el molde recién subido (no es
  thread-safe) — para el camino B se saltea, para el A sigue igual.

  ⚠️ **Trampas de herramienta de esta sesión:** el `py` de Windows **no ve el `/tmp` de Git Bash**
  (`/tmp/x.json` lo busca en `C:\tmp\`), así que pasar archivos de bash a Python por ahí falla en
  silencio; y `curl ... | tail` desde una tarea en background no muestra nada hasta que el proceso
  termina (buffering), lo que parece que se colgó cuando en realidad está trabajando.

  🔧 **El entorno de prueba (8051) ahora tiene su PROPIA base** (`TizadaProCaminoB`, creada en esta
  sesión con su admin propio). Antes compartía la del taller: cada molde de prueba aparecía en el
  catálogo de verdad — exactamente el riesgo que el `.bat` ya advertía. Los `datos/` ya estaban
  separados; ahora la base también.

- **2026-08-31 (E1)** — Detección hecha y verde contra el archivo real. Lo que se aprendió: **la
  máscara de recorte ES la pieza**, así que no hubo que portar el rasterizado del proyecto de
  referencia — con agrupar los recortes por solape alcanza. Lo que falló: la regla del 95 % de área
  para descartar el marco de la mesa **se comía piezas reales**; se cambió por comparar contra el
  rectángulo de la página con 1 pt de tolerancia.
  ⚠️ Trampa de herramienta, dos veces en la misma sesión: los parches con **heredoc de bash** le
  comieron los escapes a un `print` y dejaron el contrato sin compilar, y después un script de
  parche perdió los guiones largos al leerse. **Los archivos se escriben con la herramienta de
  escritura y se editan con reemplazo exacto**, no con heredocs ([[escrituras-atomicas]]).

- **2026-08-31** — Estudiado el proyecto `Prueba para tizada` y decidido el camino. Medido el
  archivo real `CAMISETA JUGADOR.ai` (§3): 123 MB, 9 mesas, 20 talles en capas, cada pieza es una
  máscara de recorte con su diseño adentro. Decidido: talles en capas, nombre/número siguen, la
  detección se porta a Python (un solo motor), la UI de edición sólo con contornos. Creada la rama
  y este archivo.
  ⚠️ Trampa de herramienta: escribir este archivo con un heredoc de bash falló
  (`unexpected EOF`); va con la herramienta de escritura, como manda [[escrituras-atomicas]].

## UN PEDIDO CON VARIOS MOLDES: cada uno va SÓLO en su diseño

En el paso 1 del pedido cada **espacio de diseño** («Camiseta», «Campera») elige SU molde. El
servidor no lo puede adivinar mirando la planilla: la columna «Diseño» dice de qué espacio es cada
FILA, no qué molde le toca. Por eso el front manda el reparto:

```
moldes_por_diseno = { "camiseta": ["prod_…d413"], "campera": ["prod_…14c3"] }
```

`/api/generar_multi` lo aplica **antes** del fallback de arte: si un diseño declara sus moldes y
este no está, sus filas son de otra prenda del pedido y no se generan con este molde.

🔴 **Por qué importa más acá que en el camino A.** En el camino A, un molde sin `arte.ai` para ese
diseño se salteaba solo (no había nada que estampar). Acá el diseño viene DENTRO del molde: no hay
arte que falte, así que **nada frenaba la copia de más**. Un pedido de 2 moldes × 2 diseños salía
con 4 hojas (dos de ellas la misma tizada, una con la tela de verdad y otra con la tela por defecto,
porque el diseño de más no tenía asignación) y con la ficha mostrando dos veces el mismo molde.

Respaldo: si el `moldes_por_diseno` no viene (una pantalla que quedó abierta con el front viejo), se
deduce de `vars_por_diseno`. Si no viene ninguno de los dos **no se filtra**: es preferible generar
de más —se ve— a dejar prendas sin tizada —no se ve—.

Contrato: `verificar_pedido_por_diseno.py`.

## LA FICHA DICE CON QUÉ TIPOGRAFÍA SALE

El molde guía de la ficha muestra, en una línea gris, la fuente REAL de cada campo:

```
Tipografía  ·  Nombre: Anton Regular (falta «MoreFont1-CL», se sustituyó)   Número: …
```

Se resuelve igual que en la tizada (`_fuentes_guia` → `MP.resolver_fuente`): el nombre PostScript
que pide el archivo, con el **reemplazo del pedido** aplicado, y si no está en el catálogo,
`Anton Regular` (regla del 2026-08-20) **dicho a la vista** — el taller no puede adivinar mirando el
dibujo que esa no es la tipografía que se pidió.

⚠️ `_molde_guia_ficha` corre en el hilo que genera el pedido: ahí NO hay `request`, así que los
reemplazos hay que **pasárselos** (`reempl=`). Cuando no se hacía, el molde guía se dibujaba con una
tipografía y la tela salía con otra.

## LA CACHÉ DEL DESPLEGADO ES POR ARCHIVO, NO POR MOLDE

`datos/desplegado_cache/<sha1 del archivo>_<versión>/` guarda el desplegado completo + el `alta`.
Es lo que hace que **subir el mismo molde por segunda vez tarde 1 s en vez de 25**: el sello del
desplegado es `[tamaño, mtime]`, así que al copiarlo se le devuelve al archivo la fecha que tenía
cuando se armó y todo coincide.

Que sea **por archivo** significa que **dos pedidos distintos con el mismo molde comparten esa
carpeta**. Cada uno tiene su `pid`, su `entrada/<pid>` y su propio `desplegado/` al lado del molde
— lo único común es esta caché, y es de sólo lectura una vez escrita. Reglas para no pisarse:

- **Un candado (`_CACHE_DESPL_LOCK`) para leer, reemplazar y barrer.** Nunca las tres a la vez.
- **Temporal con nombre único** (`<clave>.tmp-<8 hex>`), borrado siempre en el `finally`. Con un
  nombre fijo, dos subidas simultáneas se copiaban una adentro de la otra.
- **`os.replace` sobre una carpeta que existe FALLA en Windows**: si otro pedido llegó primero, su
  copia vale igual (mismo sha1) y la nuestra se descarta.
- **Inventario (`contenido.json`)**: al usar la caché se comprueba que la copia tenga todos los
  archivos, con sus tamaños. Media caché es peor que ninguna: el molde saldría sin mesas y eso
  **sale bien impreso**.

Contrato: `verificar_mismo_molde_dos_pedidos.py`.

⚠️ **Consultar la ruta de un molde no lo crea.** `_ruta_datos`/`_ruta_entrada` hacían `makedirs`
siempre —hasta para preguntar si un archivo existía— y una consulta sobre un molde borrado le
resucitaba la carpeta vacía. Ahora sólo crean carpetas de un molde que ya está en disco.

## CUÁNDO SE VA UN MOLDE EFÍMERO

Un molde del camino B se sube **para un pedido** y no queda guardado. Se va por tres caminos, y los
tres tienen que existir porque cada uno cubre lo que el otro no:

1. **«Nuevo pedido» / «Terminar pedido»** manda sus pids a `/api/pedido/limpiar_efimeros`. La lista
   sale de `efimerosDelPedido()`: lo que subió esta pantalla (`moldesEfimeros`, guardado en el
   navegador) **más** los moldes del pedido que el catálogo marca `efimero` — tanto los de
   `moldesSeleccionados` como **los que entraron por el diseño** (`disenoMoldes`), que es como entra
   un molde del camino B.
2. **El barrido de abandonados**, para el que cerró la pestaña: se lleva los `efimero: true` que
   nadie tocó en `TIZADA_EFIMERO_TTL_H` horas (24 por defecto). Corre al arrancar el servidor **y
   cada hora**.
3. Nunca por nombre, nunca «los que sobran»: se borra por el flag y por la fecha (ya se perdieron 3
   moldes del usuario por confundir eso).

⚠️ **Ver un molde en la lista NO es usarlo.** `_tocar_efimero` refresca `efimero_visto` en la
guardia de requests, pero los endpoints de vidriera (la miniatura de la grilla, la descarga del
archivo) están excluidos (`_API_NO_USA_EL_MOLDE`). Sin esa exclusión, tener la pantalla de moldes
abierta mantenía vivos para siempre los efímeros de pedidos ya terminados — que es exactamente lo
que reportó el usuario el 2026-09-08.

⚠️ Si el servidor **ignora** un pid (no es efímero, es de otro usuario, o hay una tizada suya
generando), el front **no lo borra de su lista**: queda anotado y el próximo «Nuevo pedido» lo
vuelve a pedir. Olvidarlo era dejarlo en el servidor para siempre.

## GUARDAR LA CONFIGURACIÓN DE UN MOLDE Y VOLVER A USARLA

El molde con el diseño adentro se sube **para un pedido** y se borra con él — y con él se iría todo
el trabajo de configurarlo. Por eso esa configuración se puede **guardar con un nombre** y volver a
aplicarla cuando se sube el mismo archivo en otro pedido (Moldería → tarjeta «Configuración»).

- Vive en la base (`dbo.config_molde`), **atada al sha1 del ARCHIVO**, no al molde: el molde
  desaparece con el pedido, la configuración no.
- Guarda el **nombrado de las piezas** —por `(mesa, idx_mesa)`, la identidad que no depende del
  talle— más grupos, variables, conjuntos, telas, etiqueta, borde, planilla, talle de guía,
  referencia de medida, editables y la config de producción.
- 🔴 **Al aplicarla entran SIEMPRE la ETIQUETA y los NOMBRES, y nada más** (regla del usuario): el
  «dónde va la etiqueta» se marca pieza por pieza, es lo que más cuesta y cuelga del nombre de la
  pieza. Lo que es decisión DEL PEDIDO —grupos y variables, telas, planilla, talle de guía, borde y
  producción— entra sólo si se tilda en el modal.
- **No se aplica sola.** La lista muestra el estado de cada una (`mismo archivo` / `parecida` /
  `distinta`) y el usuario elige; al aplicarla se informa qué entró y qué no, y se ve en el visor.
- 🔴 **Los grupos y las variables se reubican por NOMBRE de pieza.** Sus `pieza_idx` son la posición
  dentro del talle EN EL MOLDE DE ORIGEN: si en el nuevo las piezas quedaron en otro orden,
  aplicarlos tal cual armaría los grupos con las piezas equivocadas — y eso sale bien impreso.

Contrato: `verificar_config_guardada.py`.
