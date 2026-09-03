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
4. **Nombra las piezas** con **el gesto de la pantalla de edición**: toca las piezas en el visor
   (se suman) o en la lista, escribe **un** nombre y las nombra todas — si son varias se numeran
   solas («Tira» → «Tira 1», «Tira 2»). El visor abre **al instante** (§0.a) y muestra **sólo
   contornos**: ni un trazo del diseño.
5. **Marca dónde va la etiqueta** en cada pieza (mismo visor, mismos contornos).
6. Telas, planilla y tizada: **iguales que en el otro camino**.

**Lo que NO hace el cliente** (lo deja configurado el admin, una vez): grosor y color del **borde
de corte**, tamaño y tipografía de la **etiqueta**, separación y márgenes del **nesting**.

⚠️ Del gesto de edición falta el **arrastre de recuadro** para seleccionar varias de un tirón; el
clic múltiple sí está.

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
| **Una capa `nombre` y una capa `00`** | pueden ser **subcapas**, y pueden estar **dentro de la máscara de recorte** | son los placeholders que se reemplazan por el nombre y el número de cada prenda |

🔴 **Sin las capas `nombre` y `00` la tizada SALE IGUAL, con el texto del diseño en todas las
prendas.** No hay error, no hay aviso: 40 camisetas con el mismo «NOMBRE». Por eso el requisito
está escrito acá y lo cuida `verificar_personalizacion_con_diseno.py`.
El rótulo `00` se traduce solo al campo `numero` (`_CAMPO_ALIAS` en `motor_pedido.py`): el
estampado busca `persona[campo]` **por el nombre de la capa**, y la prenda trae `nombre` y
`numero` — una capa rotulada `00` apuntaría a un campo que no existe. También se aceptan `nro`,
`num`, `jugador` y `apellido`. ⚠️ `0` **no** es alias de nada: en estos moldes es un TALLE.

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

🔴 **EL PESO Y EL TIEMPO — MEDIDO DE PUNTA A PUNTA, ES EL PENDIENTE MÁS SERIO DE ESTE CAMINO.**
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
| Detección nueva | `piezas_con_diseno.py` *(a crear, E1)* |
| Parsing del molde y capas OCG | `molde_real.py` (`extraer_piezas_mesa`, `aislar_capa`) |
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
