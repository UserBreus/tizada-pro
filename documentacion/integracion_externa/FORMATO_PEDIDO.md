# TIZADA PRO — pedidos que llegan de otro sistema

Este documento es para quien programa **el otro sistema** (ventas). Explica qué archivo hay que
mandar para que TIZADA PRO arme la tizada **sin que nadie toque la pantalla**, qué contesta y qué
alarmas existen para revisar el pedido antes de mandarlo.

Archivos de esta carpeta:

| Archivo | Qué es |
|---|---|
| `pedido_ejemplo.json` | Un `pedido.json` completo, revisado contra el catálogo real |
| `resultado_ejemplo.json` | Lo que devuelve TIZADA PRO cuando el pedido termina |
| `FORMATO_PEDIDO.md` | Este documento |

---

## 1. La idea, en una página

El pedido llega **igual que si se cargara a mano en TIZADA PRO**: primero el **diseño** (JUGADOR,
GOLERO…), después las **variables** que lleva ese diseño (en TIZADA no se elige el molde: se elige
la **variable** — «Cuello redondo», «Cuello V»… —, que es un conjunto de piezas de un molde), y
para cada una su **arte**, sus **telas** y lo que **no se sublima**. Después viene la **planilla**,
una fila por prenda.

```
PAQUETE (.zip)
├── pedido.json                  ← los datos (este documento)
├── artes/jugador_camiseta.ai    ← un arte por diseño y molde (.ai o .pdf)
├── artes/golero_camiseta.ai
└── tipografias/Anton-Regular.ttf  ← sólo las que TIZADA no tenga
```

Qué pasa con el paquete:

1. **Se revisan los datos** en el acto (sin abrir ningún archivo): molde, variable, telas, talles,
   opciones, columnas obligatorias. Si algo está mal, contesta `422` con la lista de **alarmas**
   y el pedido no entra.
2. Si pasa, contesta `202` y queda **en cola**.
3. El **robot** de TIZADA PRO lo toma: carga las tipografías, lee cada arte y lo guarda en su
   diseño y su molde, arma la tizada y guarda los PDF en **Google Drive**.
4. Queda un **JSON de resultado** con dónde quedó cada archivo y a qué pedido pertenece. Se puede
   consultar, y si se configuró una dirección de aviso, TIZADA PRO lo manda solo.

El pedido lleva una **`referencia`** (el número del pedido en el otro sistema) y un bloque libre
**`pedido_externo`**: TIZADA PRO lo guarda y lo devuelve **tal cual** en el resultado, para que el
otro sistema sepa de qué pedido son esos archivos.

---

## 2. La conexión

Todas las rutas están bajo **`/api/externo/v1`** y llevan el encabezado **`X-Api-Key: <llave>`**.
La llave se crea en TIZADA PRO: *Configuración › Integraciones › Crear llave* (se muestra una sola
vez).

| Para qué | Ruta |
|---|---|
| **Lo que se elige: las variables** (de cada prenda lista, con su molde detrás) | `GET /variables` |
| Silueta de las piezas de una variable | `GET /variables/{clave}/foto` |
| Lista de moldes | `GET /moldes` |
| Todo lo de un molde (talles, variables, piezas, planilla, opciones, telas) | `GET /moldes/{codigo}` |
| Foto del molde | `GET /moldes/{codigo}/foto` |
| Telas (id, nombre, ancho, si se puede usar) | `GET /telas` |
| Tipografías que TIZADA ya tiene | `GET /tipografias` |
| Perfiles de color que tiene | `GET /perfiles` |
| Catálogo de alarmas (sin llave) | `GET /alarmas` |
| Formato y ejemplos (sin llave) | `GET /formato` |
| **Revisar un pedido sin mandarlo** | `POST /pedidos/validar` |
| **Mandar un pedido** | `POST /pedidos` |
| Estado y resultado | `GET /pedidos/{referencia}` |
| Bajar un PDF del resultado (la copia del servidor; sirve aunque Drive no esté conectado) | `GET /pedidos/{referencia}/archivos/{nombre}` |
| Cancelar (si todavía no se generó) | `DELETE /pedidos/{referencia}` |

`GET /moldes` y `GET /variables` traen un campo `version`: cambia cada vez que cambia el catálogo.
Conviene guardar lo que publica cada molde y volver a pedirlo cuando la versión cambie.

**Las siluetas** (`/variables/{clave}/foto`, `/moldes/{codigo}/foto`) son los contornos vectoriales
de las piezas (`piezas[].path_svg` con su caja `px/py/pw/ph`). Si TIZADA todavía no la calculó
(nadie abrió esa prenda en TIZADA PRO), contesta `404` con `sin_calcular: true`: mostrar un ícono.

**Dos variables de distinta `planilla`** no se combinan en un mismo pedido (pasa lo mismo en TIZADA).

### Mandar el pedido

El paquete va como archivo de formulario (`paquete`) o como cuerpo crudo `application/zip`:

```bash
curl -X POST https://TU-SERVIDOR/api/externo/v1/pedidos -H "X-Api-Key: tzp_…" -F "paquete=@OV-2026-00123.zip"
```

Límites: hasta 600 MB y 400 archivos por paquete.

### Revisar sin mandar

`POST /pedidos/validar` acepta el mismo `.zip` **o sólo el JSON** (`Content-Type:
application/json`). No guarda nada. Sirve para revisar el pedido mientras se carga en el otro
sistema: contesta las mismas alarmas de la etapa «datos».

---

## 3. `pedido.json`, campo por campo

Ver `pedido_ejemplo.json`. Todo en UTF-8.

### Cabecera

| Campo | | Qué es |
|---|---|---|
| `formato` | obligatorio | Siempre `"tizadapro.pedido/1"` |
| `referencia` | obligatorio | El número del pedido en el otro sistema. Único. Letras, números, punto, guion y guion bajo; hasta 64. Es el nombre de la carpeta en Drive y el prefijo de cada archivo |
| `pedido_externo` | opcional | Objeto libre con lo que el otro sistema quiera (id, sucursal, fecha…). **Vuelve tal cual** en el resultado |
| `cliente` | opcional | Texto, para reconocerlo en la pantalla |
| `aviso_url` | opcional | Dónde avisar al terminar. Sólo vale si es del mismo sitio que la dirección configurada en Integraciones |
| `reemplazar` | opcional | `true` para rehacer un pedido que ya se generó con esa misma referencia |
| `opciones` | opcional | Ver abajo |
| `mesas` | opcional | Ver abajo |

### `disenos[]` — cada diseño con sus moldes

| Campo | | Qué es |
|---|---|---|
| `nombre` | obligatorio | Nombre del diseño (JUGADOR, GOLERO…). Único en el pedido. Es el valor que va en la columna «diseño» de la planilla |
| `arte` | opcional | Ruta, dentro del paquete, del arte **para todos los moldes de este diseño** que no traigan el suyo |
| `tipografias` | opcional | Rutas de las tipografías (.ttf/.otf) que usa el texto/número y TIZADA no tiene |
| `tipografia_por_campo` | opcional | Forzar una tipografía del catálogo para un campo: `{"numero": "Anton Regular"}` |
| `moldes[]` | obligatorio | Los moldes que usa este diseño (uno o varios) |

### `disenos[].moldes[]` — cada variable (prenda) del diseño

Cada entrada es **una variable elegida** para el diseño. Se identifica por la `variable` (lo que se
elige en TIZADA); el `molde` es opcional y sólo hace falta si se nombra la variable por un nombre
que existe en más de una prenda. **Una variable por prenda** en cada diseño.

| Campo | | Qué es |
|---|---|---|
| `variable` | obligatorio* | La **clave** (`v_…`, de `GET /variables`) o el nombre de la variable. *Se puede omitir sólo si se manda `molde` y ese molde tiene una sola variable |
| `molde` | opcional | El código del molde (`prod_…`). Sólo si la `variable` va por nombre y ese nombre está en varias prendas |
| `arte` | uno de los dos | Ruta del arte de **este** molde. Si no viene, se usa el `arte` del diseño |
| `tela` | obligatorio | El **id** de la tela principal (el del sistema de telas). Vale para todas las piezas |
| `telas_por_pieza` | opcional | Las excepciones: `{"Cuello": "486"}`. La pieza va por su nombre **genérico** (sin número) |
| `piezas_apagadas` | opcional | Piezas que **no** se hacen en este pedido: `["Tapa costura"]` |
| `medida` | sólo prendas **a medida** | `{"ancho_m": 1.5, "alto_m": 0.9}` — la medida del **diseño** en metros (de 0,05 a 50); TIZADA le suma el margen (`a_medida.margen_cm`) y ése es el **total** que se imprime. La variable lo dice en `GET /variables` (`a_medida`). La fila de la planilla **no lleva talle** para esa prenda. Sin medida: `medida-falta`; si el total no entra en la tela: `tela-no-entra` (dice cuánto se pasa y lo máximo) |
| `forma` | opcional · sólo **a medida** | `rectangulo` (si no viene), `circulo` o `triangulo` (con o sin tilde). En el **círculo** la medida es el diámetro: `"medida": {"diametro_m": 1.2}` (o `ancho_m`). En el **triángulo** (isósceles) `ancho_m`/`alto_m` son su caja y va con `orientacion`. En las dos, el margen es parejo (el mayor de `margen_cm`); el triángulo sale con las **puntas recortadas** (doblado por la guía las solapas se superponen sin sobrar; la punta no lleva marca de tira). Error: `forma-invalida` |
| `terminacion` | opcional · sólo **a medida** | Cómo se termina el borde: `dobladillo` (el margen del molde, doblado; el triángulo con las puntas recortadas), `overlock` (la forma tal cual con `a_medida.overlock_cm` parejo; el triángulo con las puntas enteras) o `sin` (sin margen; las tiras van sólo en la ficha). Si no viene, `a_medida.terminacion_por_defecto`. También dentro de `medida`. Error: `terminacion-invalida` |
| `orientacion` | opcional · sólo **triángulo** | Hacia dónde va la **punta**: `abajo` (si no viene: el banderín), `arriba`, `izq`/`izquierda`, `der`/`derecha`. También puede ir dentro de `medida` |
| `tiras` | opcional · sólo **a medida** | Las marcas para coser las tiras: `{"lleva": true, "lados": {"arriba": 5, "abajo": 5, "izq": 1, "der": 0}}`. Cada número **cuenta las 2 puntas** (5 = una en cada esquina + 3 en el medio, a distancias iguales; 1 = una en el medio; 0 = ese lado sin tiras). También vale `true`/`false` (las del molde / no lleva) o los lados sueltos `{"arriba": 5}`. Sin `tiras`: las del molde. Grosor: el del molde. Color: siempre **negras con contorno blanco** (no se elige). **Triángulo:** `{"base": 5, "laterales": 4}` (cada lateral, contando sus puntas). **Círculo:** `{"alrededor": 12}` (parejas por todo el borde, la primera arriba; hasta 200). Con `"marcar": false` no se imprimen en la tizada pero salen en la ficha técnica (sin `marcar`: lo del molde). Errores: `tiras-invalidas`, `tiras-sin-margen` |
| `editables` | opcional | Qué lleva cada objeto editable del arte. Ver abajo |
| `tipografias` | opcional | Como en el diseño, pero sólo para este molde |
| `tipografia_por_campo` | opcional | Como en el diseño, pero sólo para **este molde** (pisa la del diseño): `{"numero": "Anton Regular"}`. Una que no está en el catálogo (ni vino en `tipografias`) → `tipografia-desconocida` |
| `reemplazos` | opcional | Reemplazar una tipografía **del arte** por otra **del catálogo**: `{"FuenteDelArte": "Anton Regular"}` (como «Tipografía» del paso Arte). Destino desconocido → `tipografia-desconocida` |
| `ajustes` | opcional | **Mover, rotar, escalar o espejar** un objeto editable (el «Editar diseño» de la pantalla): `{"escudo": {"dx": 0.05, "dy": -0.02, "rot": 15, "scale": 1.2, "talles": ["M", "L"]}}`. `dx`/`dy` = fracción del ancho/alto del diseño (+dx derecha, +dy abajo); `rot` en grados; `scale` (o `sx`/`sy` por separado; negativo = espejo); `talles` opcional (sin `talles`: todos). Error: `ajuste-invalido`; objeto que el arte no tiene: `editable-desconocido` |
| `colores` | opcional | El **color CMYK** (0 a 1) de un objeto editable: `{"escudo": {"fill": [0, 1, 1, 0], "stroke": [0, 0, 0, 1]}}`. Error: `color-invalido` |
| `mapeo_arte` | opcional | Qué **mesa del arte** va en cada pieza, a mano (cuando la guía no trae el nombre de la pieza): `{"Frente": 1, "Espalda": "ESPALDA"}` — el número de la mesa o el rótulo escrito en ella. Manda sobre lo automático. Errores: `mapeo-arte-invalido`, `mapeo-arte-mesa` |

#### `editables` — lo que no se sublima

El nombre del objeto es el de la capa del arte **sin** la palabra «Editable»
(«Editable escudo» → `escudo`).

```json
"editables": {
  "escudo": "sublimado",
  "logo": "tpu",
  "sponsor": { "proceso": "bordado", "cruz": false }
}
```

| Valor | Qué hace |
|---|---|
| `"sublimado"` | Sale impreso con el diseño (es lo que pasa si no se nombra) |
| `"tpu"`, `"bordado"`, `"dtf"` | **No se imprime**: en su lugar va una cruz de posición, y la ficha técnica dice qué aplicar y dónde |
| `{"proceso": "…", "cruz": false}` | Igual, pero **sin** la cruz en la tela (queda sólo en la ficha) |
| `"no_imprimir"` | No sale **ni el objeto ni una cruz** (el «Sin marca» de la pantalla sobre algo que se sublimaría) |

### `planilla[]` — una fila por prenda

Las claves son los **ids de columna** de la planilla del molde (`GET /moldes/{codigo}` →
`planilla.columnas`). Todo como texto; los números con cero adelante entre comillas (`"07"`).

| Clave | Qué es |
|---|---|
| `diseno` | El `nombre` de uno de los diseños. Obligatoria si el pedido trae más de uno |
| la columna de talle | El talle **tal cual lo tiene el molde** (`M`, `2XL`, `10`). Cada molde lee **su** columna de talle (`planilla.columna_talle`). Si es `null` la planilla es **sin talles**: la fila no lleva talle |
| las de rol `nombre` / `numero` | Lo que se estampa |
| las de opciones (p. ej. `manga`) | Una de sus `opciones`, y el molde tiene que **tener** esa opción (`opciones_de_pieza`). Varias a la vez: `"Corta + Larga"` |
| `piezas` (Repo) | Opcional: **qué piezas hace esta fila** (reposición), por variable o molde: `{"v_redondo": ["Cuello", "Manga 1"]}` (un nombre genérico = todas las suyas). Sin `piezas`: todas. Errores: `repo-invalido`, `repo-no-admitido` |
| la de rol `cantidad` | Entero de 1 en adelante. Vacía = 1. **Tiene dos usos según `mesas.modo`**: prendas iguales (`normal`) o copias de la mesa (`una_por_fila`) — ver [`COMO_USAR_CADA_OPCION.md`](COMO_USAR_CADA_OPCION.md) §1 |

### `opciones`

| Campo | Valores | Por defecto |
|---|---|---|
| `si_falta_tipografia` | `"rechazar"` · `"predeterminada"` (estampa con la tipografía predeterminada y avisa) | `rechazar` |
| `si_texto_no_entra` | `"achicar"` (avisa) · `"rechazar"` | `achicar` |
| `si_piezas_en_blanco` | `"rechazar"` · `"seguir"` (salen sin diseño y avisa) | `rechazar` |
| `perfil_color` | El perfil a forzar: el archivo o el nombre de uno de `GET /perfiles`. Uno que no existe → `perfil-desconocido` | el del sistema |
| `carpeta` | Subcarpeta de Drive donde guardar (`"2026-10/OV-2026-00123"`) | la referencia |

### `mesas`

| `modo` | Qué hace |
|---|---|
| `"normal"` | Lo de siempre (por defecto) |
| `"una_por_fila"` | Una mesa por fila; la cantidad pasa a ser copias. Las copias se acomodan en una mesa del largo máximo (el del nesting o `largo_max_m`); si alcanzan para llenarla, sale UN archivo con la mesa llena que se imprime `copias` veces (19 con lugar para 5 → 5×3). Todo lo que no llena una mesa, de cualquier fila y talle, se acomoda JUNTO como en `normal` y se imprime 1 vez (MAPA 725). Cada archivo trae `por_mesa` unidades. Todas las mesas, del ancho imprimible de la tela |
| `"por_talles"` | Los talles de cada grupo comparten mesa: `"grupos": [["S","M"],["L","XL"]]` |
| `"talles_separados"` | Todos en la misma mesa sin mezclar talles: cada talle acomodado solo y apilado debajo del anterior, con una línea punteada entre talles; `grupos` opcional (esos sí van mezclados). Resultado: `"separados": true` |

| Otro campo de `mesas` | Qué hace |
|---|---|
| `"separar_disenos"` | Opcional, `true`/`false` (por defecto `false`). Sin él, las piezas del **mismo molde se mezclan** aunque sean de diseños distintos (también con `una_por_fila`: mesas mezcladas que se repiten, con `filas` en el resultado). Con `true`, cada diseño va en sus propias mesas en cualquier `modo` y cada archivo trae su `diseno`. Otro tipo → `mesas-invalido` (el botón «Separar» de la planilla, MAPA 717) |
| `"largo_max_m"` | Opcional. El **largo máximo de cada mesa** de este pedido, en metros (`12.5`; de 0,10 a 50). Sin él rige el del nesting del molde (`largo_mesa_cm` de `GET /variables` y del molde). Con él ninguna mesa lo pasa: lo que no entra sigue en otra mesa. Vale con cualquier `modo`. Un molde a medida se revisa contra este largo (`tela-no-entra`). Mal → `largo-mesa-invalido` (el botón «Largo» de la planilla, MAPA 716) |

---

## 4. El arte

- **.ai** guardado con «Crear archivo compatible con PDF», o **.pdf** de Illustrator / CorelDRAW.
- **Una mesa de trabajo por pieza**, armado sobre la base que da TIZADA PRO para ese molde.
- Capas: `diseño` (el dibujo, **sin texto vivo**: convertido a curvas), `guias` (el nombre de la
  pieza de cada mesa; `#talle` o `#rango` para mesas por talle), `Texto` (también puede llamarse `Nombre`) y `Número` (los textos
  que se reemplazan en cada prenda), y una capa `Editable <nombre>` por cada objeto editable.
- Una tipografía sólo hace falta mandarla si el texto/número usa una que TIZADA no tiene
  (`GET /tipografias`).

---

## 5. Qué contesta

### Al mandar (`POST /pedidos`)

```json
{ "referencia": "OV-2026-00123", "aceptado": true, "estado": "en_cola", "alarmas": [] }
```

- `202` = entró y está en cola. Las `alarmas` que vengan acá son avisos.
- `422` = **rechazado**: `aceptado: false` y la lista de alarmas que frenan.
- `401` = falta la llave o no es válida.

### Al consultar (`GET /pedidos/{referencia}`)

`estado` puede ser:

| Estado | Qué significa |
|---|---|
| `en_cola` | Esperando al robot |
| `procesando` | El robot lo está haciendo (`etapa` dice en qué va) |
| `listo` | Terminó. Viene `resultado` |
| `rechazado` | El arte, las tipografías o el plan tienen alarmas que frenan. No salió nada |
| `error` | Falla del sistema después de 3 intentos. Se puede reintentar desde la pantalla |
| `cancelado` | Lo canceló el otro sistema o una persona |

### El resultado (ver `resultado_ejemplo.json`)

| Campo | Qué es |
|---|---|
| `referencia`, `pedido_externo`, `cliente` | Lo que mandó el otro sistema, tal cual |
| `tizada_id` | El número de la tizada dentro de TIZADA PRO |
| `destino` | `tipo` = `drive` (con `carpeta_id` y `carpeta_enlace`) o `local` (Drive sin configurar o caído: se bajan con `descarga`). Nunca trae rutas del disco del servidor |
| `archivos[]` | Cada PDF: `tipo` (`tizada` o `ficha`), `nombre`, `bytes`, `sha256`, `descarga` (la ruta para bajarlo de TIZADA, haya Drive o no), y si se subió a Drive `drive_id`, `enlace`, `carpeta_id`. Las tizadas traen además `tela`, `mesas`, `ancho_cm`, `largo_cm` (uno por mesa), `consumo_cm`, `aprovechamiento` y `moldes`; con `una_por_fila`, `fila`, `copias` y `por_mesa` (y `filas` si la mesa mezcla varias filas del mismo molde); con `separar_disenos`, `diseno` |
| `resumen` | Prendas, piezas, telas usadas y perfil de color |
| `disenos[]` | Por diseño y variable: la `variable` (clave) y su `variable_nombre`, la prenda (`molde`, `nombre`), la tela y qué quedó **sin sublimar** (`no_sublimado`) |
| `alarmas[]` | Los avisos que quedaron |

Hay **un PDF por mesa** (como «Descargar todo» de TIZADA) más la **ficha técnica**. Los nombres llevan la
referencia adelante y el nombre de la mesa: `OV-2026-00123__Mesa 1 - Bandera (1,60).pdf`. El mismo JSON de resultado queda en la
carpeta de Drive como `OV-2026-00123__resultado.json`.

### El aviso (webhook)

Si en *Integraciones* se configuró una dirección de aviso, cuando el pedido llega a `listo`,
`rechazado` o `error` TIZADA PRO hace un `POST` con el mismo JSON de `GET /pedidos/{referencia}`.

- Encabezados: `X-Tizada-Referencia` y `X-Tizada-Firma`.
- La firma es `HMAC-SHA256(cuerpo, sha256_hex(llave))` en hexadecimal: sirve para comprobar que
  el aviso viene de TIZADA PRO.
- Hay que contestar `2xx`. Si no, reintenta a los 5 s, 30 s y 2 min.

---

## 6. Las alarmas

Cada alarma tiene esta forma:

```json
{ "codigo": "talle-inexistente", "frena": true, "etapa": "datos",
  "mensaje": "fila 3: «Camiseta de futbol» no tiene el talle «XXL» (tiene: XS, S, M, L, XL, 2XL…)",
  "donde": { "fila": 3, "campo": "planilla[2].talle" } }
```

- **`frena: true`** = el pedido se rechaza. **`false`** = aviso, sigue.
- **`etapa`**: `datos` (al recibir, se contesta en el acto) · `arte` (al leer el arte, segundos
  después) · `tizada` (al armarla).

**La lista completa y siempre al día está en `GET /api/externo/v1/alarmas`** (no pide llave), con
qué significa cada una y qué hacer. Las de la etapa `datos` se pueden evitar antes de mandar con
lo que publica cada molde:

| Para no caer en… | Revisar contra… |
|---|---|
| `molde-desconocido`, `molde-no-disponible`, `molde-archivado` | `GET /moldes` → `listo` (un archivado ya no aparece: re-sincronizar) |
| `variable-falta`, `variable-desconocida`, `variable-ambigua` | `GET /variables` (mandar la clave `v_…`) |
| `talle-inexistente` | `talles[]` del molde |
| `talle-sin-columna` | `planilla.con_talles` (un molde con varios talles no puede ir con una planilla sin talles: lo arregla quien administra TIZADA) |
| `medida-falta`, `medida-invalida` | `a_medida` de la variable: mandar `medida: {ancho_m, alto_m}` (la del diseño) en metros; en el círculo, `diametro_m` |
| `forma-invalida` | `a_medida.formas` y `a_medida.orientaciones_triangulo` |
| `terminacion-invalida` | `a_medida.terminaciones`: `dobladillo`, `overlock` o `sin` |
| `arte-otra-medida` | el arte de un molde a medida tiene que salir de la plantilla de ESA medida (`POST /plantillas` con la `medida` del pedido): si se cambió la medida, su mesa ya no es la pieza y el diseño no la cubre |
| `tela-no-entra` | `a_medida.telas[].entra_hasta_cm` y `largo_maximo_cm`: el total (medida + margen) tiene que entrar; o preguntar antes a `POST /a_medida/calcular` |
| `tiras-invalidas`, `tiras-sin-margen` | `a_medida.tiras` (lados `arriba`/`abajo`/`izq`/`der`, enteros 0-50; triángulo `base`/`laterales`; círculo `alrededor` 0-200) y `a_medida.margen_cm` (sin margen en un lado, ese lado no lleva tiras) |
| `opcion-inexistente` | `planilla.columnas[].opciones` |
| `opcion-sin-piezas` | `opciones_de_pieza.<clave>.tiene` (por variable) |
| `columna-obligatoria-vacia` | `planilla.columnas[].obligatoria` |
| `tela-desconocida`, `tela-no-usable` | `GET /telas` → `usable` |
| `tela-no-permitida` | `telas.todas` y `telas.por_pieza` del molde |
| `pieza-desconocida` | `piezas[]` del molde |
| `tipografia-falta` | `GET /tipografias` |

Las de la etapa `arte` dependen del archivo (piezas sin mesa, texto sin convertir a curvas, un
objeto editable que el pedido nombra y el arte no tiene): sólo se saben cuando el robot lo abre, y
llegan por el estado del pedido o por el aviso.

---

## 7. Lista de control

- [ ] El artículo del otro sistema guarda la **clave de la variable** de TIZADA PRO (`v_…`, de `GET /variables`).
- [ ] Cada diseño trae sus variables (una por prenda) y su arte (en el diseño o en cada variable).
- [ ] Las telas van por **id**, las piezas por **nombre genérico**, los talles **tal cual** el molde.
- [ ] `referencia` única y sin espacios.
- [ ] `pedido_externo` con lo necesario para reconocer el pedido cuando vuelva.
- [ ] `POST /pedidos/validar` antes de `POST /pedidos`.
- [ ] El otro sistema guarda, de cada archivo del resultado, `sha256`, `descarga` y (si hay Drive) `drive_id` y `enlace`.
- [ ] El aviso se comprueba con la firma (`X-Tizada-Firma`) antes de creerle.

La API entera (todas las rutas, el aviso, errores) está en [`API.md`](API.md).
