# TIZADA PRO — referencia de la API para otro sistema

Todo lo que un sistema externo (ventas, ERP, tienda) necesita para mandarle pedidos a TIZADA PRO y
recibir lo que sale: **qué rutas hay, qué se manda, qué vuelve y qué archivos viajan**. El detalle
campo por campo del pedido está en [`FORMATO_PEDIDO.md`](FORMATO_PEDIDO.md); acá está la API entera.

- Base: `https://<servidor-de-TIZADA>/api/externo/v1` (en una PC de prueba: `http://127.0.0.1:8050/api/externo/v1`).
  Si TIZADA vive bajo un subcamino (`https://…/Tizadapro`), la base es `https://…/Tizadapro/api/externo/v1`.
- Todo en **UTF-8**. Las respuestas son **JSON** (salvo los PDF y las siluetas, ver abajo).
- Especificación para herramientas (Postman, Insomnia, generadores de cliente): [`openapi.yaml`](openapi.yaml).
- Respuestas **reales** de cada ruta: carpeta [`respuestas/`](respuestas/).

---

## 1. La llave

Cada pedido entra con una **llave** que se crea en TIZADA PRO: *Configuración › Integraciones › Crear
llave* (se muestra **una sola vez**; TIZADA guarda sólo su huella). Va en un encabezado:

```
X-Api-Key: tzp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

- Sin llave o con una inválida → `401 {"error": "falta la llave o no es válida (encabezado X-Api-Key)"}`.
- `/formato` y `/alarmas` no la piden (son documentación).
- La llave **sólo** abre `/api/externo/v1`. Para cortar el acceso: *Integraciones › Revocar*.
- La misma llave firma los avisos (ver §6): guardarla en el servidor del otro sistema, nunca en un navegador.

---

## 2. El recorrido

```
OTRO SISTEMA                                   TIZADA PRO
───────────                                    ──────────
1. GET  /variables, /moldes/{codigo}, /telas,     ← catálogo: qué se puede pedir
        /tipografias, /alarmas                       (guardarlo y refrescarlo cuando cambia `version`)
2. POST /pedidos/validar   (JSON o .zip)          ← revisa los DATOS sin guardar nada (200 / 422)
3. POST /pedidos           (.zip)                 ← 202 en cola · 422 rechazado
                                                     el robot de TIZADA lee el arte y arma la tizada
4. GET  /pedidos/{ref}     (cada 5-10 s)          ← en_cola → procesando (etapa, %) → listo / rechazado / error
   o el AVISO: TIZADA hace POST a tu URL           ← el mismo JSON, firmado
5. GET  /pedidos/{ref}/archivos/{nombre}          ← cada PDF (o desde Google Drive con `drive_id`)
```

---

## 3. Catálogo (lo que se puede pedir)

### `GET /variables` — lo que se elige

En TIZADA PRO **se elige la variable** («Cuello redondo», «cuello V»…), no el molde: una variable es
un conjunto de piezas de una prenda. Esta lista trae las variables de las prendas **listas** para pedir.

```json
{ "version": "…", "variables": [
  { "clave": "v_bu8p7gy", "nombre": "Cuello redondo",
    "molde": "prod_20260820_095558_38bc", "molde_nombre": "Camiseta de futbol",
    "piezas": ["Cuello", "Dorso", "Frente", "Manga corta derecha", "…"], "n_piezas": 7,
    "planilla": "plan_…", "foto": "/api/externo/v1/variables/v_bu8p7gy/foto" } ] }
```

- Guardar la **`clave`**: es lo que va en el pedido.
- Dos variables con distinta `planilla` no se combinan en un mismo pedido.
- **Prenda A MEDIDA** (banderas, banners): un rectángulo de una sola pieza, sin talles. Trae el bloque
  `a_medida` con TODO lo que hace falta para pedirla completa:

  ```json
  "a_medida": {
    "pieza": "Bandera",
    "pide": "medida: {ancho_m, alto_m} = la del DISEÑO en metros (obligatoria) · tiras: {lleva, lados} (opcional)",
    "medida_minima_m": 0.05, "medida_maxima_m": 50,
    "medida_de_muestra_m": { "ancho_m": 1, "alto_m": 1 },
    "margen_cm": { "arriba": 3, "abajo": 3, "izq": 3, "der": 3 },
    "borde_corte_mm": 2,
    "total": "total = medida del diseño + el margen de cada lado (el borde de corte va ADENTRO del total)",
    "gira": true, "largo_maximo_cm": 2999.5,
    "telas": [ { "id": "44", "nombre": "Bandera (1,60)", "ancho_mesa_cm": 157, "entra_hasta_cm": 156.7 } ],
    "regla_entra": "entra si el lado del TOTAL que va atravesado ≤ entra_hasta_cm …",
    "tiras": { "lleva_por_defecto": false, "lados_por_defecto": { "arriba": 0, "abajo": 0, "izq": 0, "der": 0 },
               "grosor_mm": 1, "color_cmyk": [0, 0, 0, 1], "maximo_por_lado": 50, "regla": "…" } }
  ```

  El pedido manda la **medida del diseño** (`medida: {"ancho_m": 3, "alto_m": 1.5}`) y, si quiere,
  las **tiras** (`tiras: {"lleva": true, "lados": {"arriba": 5, "abajo": 5, "izq": 1, "der": 0}}`; cada
  número cuenta las 2 puntas). TIZADA le suma el margen (3,00 × 1,50 con 3 cm → **3,06 × 1,56**), el
  borde de corte va adentro, y las marcas de las tiras salen impresas del color y grosor del molde. La
  ficha técnica trae «MEDIDA Y TERMINACIÓN». Si el total no entra en la tela: `tela-no-entra` (con
  cuánto se pasa y lo máximo). Para saberlo ANTES de mandar: `POST /a_medida/calcular`.
- `version` cambia cuando cambia el catálogo: conviene guardar y refrescar sólo entonces.

### `GET /variables/{clave}/foto` — la silueta de sus piezas

Contornos **vectoriales** de las piezas de esa variable, para mostrarla en pantalla:

```json
{ "img_w": 5906.2, "img_h": 5304.7, "variable": "v_bu8p7gy", "molde": "prod_…",
  "piezas": [ { "idx": 3, "path_svg": "M 772.6 2229.0 L …", "px": 657.6, "py": 2229.0, "pw": 230.0, "ph": 35.0 } ] }
```

Se dibuja con un `<svg viewBox="minX minY ancho alto">` y un `<path d="…">` por pieza (la caja de todas
sale de `px/py/pw/ph`). Si TIZADA todavía no la calculó (nadie abrió esa prenda en TIZADA PRO):
`404 {"error": "…", "sin_calcular": true}` → mostrar un ícono.

### `GET /moldes` y `GET /moldes/{codigo}` — la prenda entera

`/moldes` lista todas las prendas con `listo` (y `motivo` si no se puede pedir). `/moldes/{codigo}` trae
todo lo de una prenda:

| Campo | Para qué |
|---|---|
| `talles[]` | Los talles, en su orden. En la planilla van **tal cual** |
| `variables[]` | `clave`, `nombre`, `piezas` (genéricas) y `piezas_exactas` |
| `piezas[]` | Nombres genéricos (sin número): para `telas_por_pieza` y `piezas_apagadas` |
| `planilla.columnas[]` | `id`, `titulo`, `rol` (`cantidad`, `talle`, `nombre`, `numero`, `manga`, `diseno`, `dato`…), `obligatoria`, `opciones` |
| `planilla.columna_talle` | Qué columna de talle lee esta prenda (puede haber «Talle» y «Talle short»). **`null` = planilla SIN TALLES** (banderas, moldes de un solo tamaño): las filas van sin talle y TIZADA usa el único talle del molde |
| `planilla.con_talles` | `false` en una planilla sin talles (lo mismo que `columna_talle: null`) |
| `opciones_de_pieza` | Qué opciones de cada toggle (p. ej. manga) **tiene de verdad**, en general (`*`) y por variable |
| `telas.todas[]`, `telas.por_pieza{}` | Las telas que admite, en general y por pieza |
| `foto` | La silueta del molde entero (mismo formato que la de una variable) |

### `GET /telas`

```json
{ "telas": [ { "id": "232", "nombre": "Jacquard Charrúa (1,83)", "ancho_mesa_cm": 180.0, "usable": true, "de_baja": false } ] }
```

Las telas van **por `id`**. `usable: false` = no se puede elegir (de baja o sin medida).

### `GET /tipografias`

Las que TIZADA ya tiene (`{"tipografias": ["Anton Regular", …]}`). Sólo hace falta mandar el archivo
de una tipografía que **no** esté acá.

### `GET /alarmas` (sin llave) y `GET /formato` (sin llave)

- `/alarmas`: el catálogo completo de alarmas — `codigo`, `etapa`, `frena`, `que_significa`, `que_hacer`.
  Lista real en [`respuestas/GET_alarmas.json`](respuestas/GET_alarmas.json).
- `/formato`: los nombres de formato (`tizadapro.pedido/1`, `tizadapro.resultado/1`), los procesos de
  editable (`sublimado`, `tpu`, `bordado`, `dtf`), los límites y los dos ejemplos.

---

## 4. Mandar un pedido

### El paquete (`.zip`) — lo que se MANDA

```
OV-2026-00123.zip
├── pedido.json                    ← los datos (ver FORMATO_PEDIDO.md · ejemplo: pedido_ejemplo.json)
├── artes/jugador_camiseta.ai      ← los artes (.ai con «compatible con PDF» o .pdf)
├── artes/golero_camiseta.ai
└── tipografias/Anton-Regular.ttf  ← sólo las que TIZADA no tiene (.ttf / .otf)
```

- `pedido.json` en la raíz del zip. Los demás archivos, en las rutas que `pedido.json` nombra.
- Límites: **600 MB** y **400 archivos** por paquete.
- Esquema JSON del pedido: [`esquemas/pedido.schema.json`](esquemas/pedido.schema.json).

### `POST /a_medida/calcular` — molde a medida: las cuentas antes de mandar

Con la variable (o `molde`), la medida del diseño y, si las tiene, la `tela` y las `tiras`, TIZADA
contesta lo mismo que su pantalla. No guarda nada.

```json
POST { "variable": "v_cb7fd79", "ancho_m": 3, "alto_m": 1.5, "tela": "44",
       "tiras": { "arriba": 5, "abajo": 5, "izq": 1 } }
200 { "medida_diseno_cm": { "ancho": 300, "alto": 150 }, "total_cm": { "ancho": 306, "alto": 156 },
      "margen_cm": { … }, "borde_corte_mm": 2, "gira": true, "largo_maximo_cm": 2999.5,
      "telas": [ { "id": "44", "nombre": "Bandera (1,60)", "ancho_mesa_cm": 157, "entra_hasta_cm": 156.7,
                   "entra": true, "motivo": null } ],
      "entra_en_alguna": true,
      "tiras": { "lleva": true, "lados": { "arriba": 5, "abajo": 5, "izq": 1, "der": 0 }, "total_marcas": 11,
                 "grosor_mm": 1, "color_cmyk": [0, 0, 0, 1],
                 "por_lado": [ { "lado": "arriba", "marcas": 5, "largo_del_lado_cm": 306, "cada_cm": 76.5,
                                 "en_el_medio": false, "largo_marca_cm": 3 }, … ] },
      "ficha": [ { "etiqueta": "Total del arte (con el margen)", "valor": "306 × 156 cm" }, … ],
      "alarmas": [] }
422 { "alarmas": [ { "codigo": "medida-invalida", … } ] }      (o tiras-invalidas / tiras-sin-margen)
404 { "error": "esa variable o molde no existe" } · 422 { "error": "ese molde no es a medida" }
```

Si una tela no entra, su `motivo` dice cuánto se pasa y lo máximo («… se pasa 6,3 cm (ni girándola).
En esta tela, lo máximo es 1,50 m de alto (sin contar el margen).»).

### `POST /pedidos/validar` — revisar sin mandar

Acepta el `.zip` **o sólo el JSON** (`Content-Type: application/json`). No guarda nada. Revisa los
DATOS (variables, telas, talles, columnas, opciones); el arte se revisa recién al procesar.

```json
200 { "referencia": "OV-2026-00123", "aceptaria": true,  "alarmas": [], "nota": "…" }
422 { "referencia": "OV-2026-00123", "aceptaria": false, "alarmas": [ { "codigo": "variable-desconocida", "frena": true, … } ] }
```

La revisión va por etapas: si un diseño o una variable frena, la planilla todavía no se revisa.

### `POST /pedidos` — mandar

El `.zip` como **archivo de formulario** `paquete` (multipart) o como **cuerpo crudo** `application/zip`.

```bash
curl -X POST https://TIZADA/api/externo/v1/pedidos -H "X-Api-Key: tzp_…" -F "paquete=@OV-2026-00123.zip"
```

| HTTP | Cuerpo | Qué significa |
|---|---|---|
| `202` | `{"referencia", "aceptado": true, "estado": "en_cola", "alarmas": [avisos]}` | Entró y está en cola |
| `422` | `{"referencia", "aceptado": false, "estado": "rechazado", "alarmas": [...]}` | Rechazado por los datos: no entró |
| `415` | `{"error"}` | No vino un .zip (para revisar sólo el JSON está `/pedidos/validar`) |
| `401` | `{"error"}` | Falta la llave o no es válida |

La misma `referencia` otra vez: si ya está `listo`, se rechaza (`referencia-ya-generada`) salvo que el
pedido traiga `"reemplazar": true`.

---

## 5. Seguir el pedido y recibir lo que sale

### `GET /pedidos/{referencia}` — el estado (y el resultado)

```json
{ "referencia": "OV-2026-00123", "estado": "procesando",
  "etapa": "armando la tizada (52 %): Acomodando en la tela «Rib (1,00)» (33 piezas)…",
  "recibido": "2026-10-02T11:10:20", "actualizado": "…", "alarmas": [], "pedido_externo": { … } }
```

| `estado` | Qué significa |
|---|---|
| `en_cola` | Esperando al robot |
| `procesando` | Haciéndose. `etapa` es texto para mostrar; si trae `(NN %)`, es el avance |
| `listo` | Terminó: viene **`resultado`** |
| `rechazado` | El arte, las tipografías o el plan tienen alarmas que frenan. No salió nada |
| `error` | Falla del sistema después de 3 intentos |
| `cancelado` | Lo canceló el otro sistema o una persona |

`404` si no existe esa referencia. Preguntar cada **5-10 s** mientras no sea final (o esperar el aviso).

### El resultado — lo que se RECIBE

Viene en `resultado` cuando `estado` es `listo` (ejemplo: [`resultado_ejemplo.json`](resultado_ejemplo.json),
esquema: [`esquemas/resultado.schema.json`](esquemas/resultado.schema.json)):

- `referencia`, `pedido_externo`, `cliente`: lo que mandó el otro sistema, **tal cual** → así se sabe
  de qué venta son los archivos.
- `archivos[]`: cada PDF — `tipo` (`tizada` o `ficha`), `nombre`, `bytes`, `sha256`, **`descarga`**
  (la ruta para bajarlo de TIZADA), y si se subió a Drive `drive_id`, `enlace`, `carpeta_id`. Cada
  tizada es UNA MESA y trae `tela`, `mesa` (su número dentro de la tela), `mesas_de_la_tela`, `mesas`
  (= 1), `ancho_cm`, `largo_cm` (`[su largo]`), `consumo_cm` (su largo), `aprovechamiento` (el de la
  tela entera), `moldes` y, si corresponde, `fila` y `copias` (una mesa por fila) o `talles` (talles por mesa).
- `destino`: `tipo` = `drive` (con `carpeta_id`, `carpeta_enlace`, `carpeta_fichas_id`…) o `local`
  (Drive no conectado o caído: los PDF quedaron en TIZADA y se bajan con `descarga`).
- `disenos[]`: por diseño y variable — `variable`, `variable_nombre`, la prenda, la tela y
  `no_sublimado` (qué objeto va en TPU/DTF/bordado).
- `resumen`, `alarmas` (avisos que quedaron), `tizada_id`, `generado`, `segundos`.

Hay **un PDF por mesa** (igual que «Descargar todo» de TIZADA: cada mesa es un archivo de una página,
lista para el RIP) y la **ficha técnica** (PDF A4). Los nombres llevan la referencia adelante y el
nombre de la mesa: `OV-2026-00123__Mesa 1 - Bandera (1,60).pdf`, `OV-2026-00123__Mesa 2 - Bandera (1,60).pdf`,
`OV-2026-00123__FICHA_TECNICA.pdf`. La numeración vuelve a 1 en cada tela.

### `GET /pedidos/{referencia}/archivos/{nombre}` — bajar un PDF

Devuelve el PDF (`application/pdf`); con `?descargar=1`, como adjunto. Sólo los archivos que nombra el
resultado (`404` si no). Es la ruta que viene en `archivos[].descarga`. Comprobar el `sha256`.

⚠️ La copia del servidor se borra a los **30 días** de terminado el pedido (quedan el estado y el
resultado; Drive no se toca): bajar los PDF apenas el pedido está `listo`, o usar los de Drive.

### `DELETE /pedidos/{referencia}` — cancelar

`200 {"referencia", "estado": "cancelado"}` · `409` si ya está `listo` · `404` si no existe.

---

## 6. El aviso (webhook) — lo que TIZADA MANDA al otro sistema

Si en *Integraciones › Aviso al otro sistema* hay una dirección (o el pedido trae `aviso_url` **del
mismo sitio**), cuando el pedido llega a `listo`, `rechazado` o `error` TIZADA hace:

```
POST <tu dirección>
Content-Type: application/json; charset=utf-8
X-Tizada-Referencia: OV-2026-00123
X-Tizada-Firma: 6f1c…(hex)

<el mismo JSON que GET /pedidos/{referencia}>
```

**Comprobar la firma** antes de creerle (si no coincide, ignorarlo):

```
firma = HMAC-SHA256( clave = sha256_hex(llave) , mensaje = cuerpo tal cual llegó ) → hexadecimal
```

```python
esperada = hmac.new(hashlib.sha256(LLAVE.encode()).hexdigest().encode(), cuerpo, hashlib.sha256).hexdigest()
valida = hmac.compare_digest(esperada, request.headers["X-Tizada-Firma"])
```

Contestar **`2xx`**. Si no, reintenta a los 5 s, 30 s y 2 min. Código listo para usar:
[`codigo/recibir_aviso.py`](codigo/recibir_aviso.py) y [`codigo/cliente.mjs`](codigo/cliente.mjs).

---

## 6.b Plantillas: la base para el diseñador (Illustrator, CorelDRAW y guía .ai)

Para que el diseñador arme el arte, TIZADA entrega **archivos**: la pantalla es de ustedes. Un
**archivo por diseño**, con todas sus prendas (variables), cada una en su bloque con su nombre arriba.

### `GET /conectores` y `GET /conectores/{clave}` — los instaladores

Los conectores se instalan **una vez** en la computadora donde se diseña (doble clic, «Instalar»).
Unen esa computadora con Illustrator o CorelDRAW para que la base se arme allá sola.

```json
{"conectores": [
  {"clave": "illustrator",     "programa": "Illustrator", "sistema": "Windows", "version": "1.26.0", "archivo": "Instalar-USER-PRO-Illustrator-1.26.0.exe", "descarga": "/api/externo/v1/conectores/illustrator"},
  {"clave": "illustrator-mac", "programa": "Illustrator", "sistema": "Mac",     "version": "1.26.0", "archivo": "USER-PRO-Illustrator-Mac-1.26.0.zip",      "descarga": "/api/externo/v1/conectores/illustrator-mac"},
  {"clave": "corel",           "programa": "CorelDRAW",   "sistema": "Windows", "version": "1.4.0",  "archivo": "Instalar-USER-PRO-Corel-1.4.0.exe",        "descarga": "/api/externo/v1/conectores/corel"}]}
```

CorelDRAW necesita la versión **2022 o más nueva**. Para saber si el conector ya está en esa
computadora, desde su navegador: `GET http://127.0.0.1:47850/estado` (Illustrator) o
`GET http://127.0.0.1:47851/estado` (CorelDRAW): contesta si está, y si no, no hay conexión.

### `POST /plantillas` — pedir la base (JSON)

```json
{
  "referencia": "PL-0001",
  "disenos": [
    {"nombre": "JUGADOR", "variables": ["v_redondo", "v_cuellov"]},
    {"nombre": "GOLERO",  "variables": [{"variable": "v_redondo", "molde": "prod_..."}]}
  ],
  "talles": {"modo": "todos"},
  "escala": 100
}
```

| Campo | Qué es |
|---|---|
| `referencia` | La de ustedes (letras, números, `.`, `-`, `_`; hasta 64). Pedirla de nuevo con la misma la rehace. |
| `disenos[].nombre` | Nombre del diseño: sale UN archivo por diseño, con ese nombre. |
| `disenos[].variables` | Las prendas, como en `GET /variables` (clave o nombre; con `molde` si el nombre está en varias). Una prenda **a medida** va como objeto con su medida: `{"variable": "v_…", "medida": {"ancho_m": 1.5, "alto_m": 0.9}}`. |
| `talles.modo` | `todos` = un diseño para todos los talles · `rango` = uno por grupo de talles · `por_talle` = cada talle a su medida real. |
| `talles.rangos` | (`rango`) `[{"talles": ["XS","S","M"], "guia": "S"}]` — la guía es el talle con el que se calcula la medida. |
| `talles.talles` | (`por_talle`) los talles que van; sin este campo, todos. |
| `escala` | Tamaño en **Illustrator**: 100 (real), 90 … 10. CorelDRAW es siempre a tamaño real. |

Contesta en el acto `202` (en cola) o `422` con alarmas (`variable-desconocida`, `talles-invalidos`,
`escala-invalida`, `plantilla-sin-variables`, `medida-falta`, `medida-invalida`…). La arma el robot en segundos.

### `GET /plantillas/{referencia}` — el estado y los archivos

```json
{"referencia": "PL-0001", "estado": "listo", "etapa": "terminado", "alarmas": [],
 "archivos": [
   {"diseno": "JUGADOR", "tipo": "illustrator", "nombre": "JUGADOR - Illustrator.json", "bytes": 377250, "sha256": "…", "descarga": "/api/externo/v1/plantillas/PL-0001/archivos/JUGADOR%20-%20Illustrator.json"},
   {"diseno": "JUGADOR", "tipo": "corel",       "nombre": "JUGADOR - CorelDRAW.json",  "bytes": 311548, "sha256": "…", "descarga": "…"},
   {"diseno": "JUGADOR", "tipo": "guia",        "nombre": "guia_JUGADOR.ai",           "bytes": 47035,  "sha256": "…", "descarga": "…"}],
 "como_usar": {"illustrator": "…", "corel": "…", "guia": "…", "conectores": "…"}}
```

Estados: `en_cola` → `procesando` → `listo` (o `rechazado` / `error`). Si un diseño no entra en un
archivo de Illustrator a esa escala, sale en varios (`"parte": "1 de 2"`). Avisos que pueden venir:
`plantilla-mesas-chocan` (dos piezas distintas con el mismo nombre de mesa en un archivo: al subir el
arte se usaría la primera para las dos) y `plantilla-aviso` (por ejemplo, una guía .ai que no entra
en Illustrator: los otros archivos salen igual).

### `GET /plantillas/{referencia}/archivos/{nombre}` — bajar un archivo (`?descargar=1` para guardarlo)

### Qué hacer con cada archivo

| Tipo | Qué es | Cómo se usa |
|---|---|---|
| `illustrator` | Lo que arma la base en Illustrator: una mesa por pieza con su nombre, las capas (diseño, Editable…, Texto, Número, guias) y el contorno de cada pieza. | Desde la **computadora del diseñador** (su navegador), con el conector instalado e Illustrator abierto: `POST http://127.0.0.1:47850/plantilla` con el contenido del archivo tal cual (`Content-Type: application/json`). Contesta `{"ok": true, "mesas": N, "archivo": "…"}` y guarda el .ai en *Documentos › USER PRO › Plantillas*. |
| `corel` | Lo mismo para CorelDRAW (una página por mesa, a tamaño real). | `POST http://127.0.0.1:47851/plantilla` con el contenido del archivo. Si CorelDRAW está cerrado, se abre solo. |
| `guia` | Una guía .ai que se abre en cualquier Illustrator, sin conector. | Bajarla y abrirla. |

El `POST` al conector lo hace **la página del sistema de ustedes** en la computadora del diseñador:
el conector escucha sólo en esa computadora (`127.0.0.1`) y acepta pedidos de cualquier página.
Ejemplo (navegador):

```js
const plan = await (await fetch('/su-servidor/plantilla/PL-0001/JUGADOR - Illustrator.json')).text()
const r = await fetch('http://127.0.0.1:47850/plantilla', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: plan })
const d = await r.json()   // {ok: true, mesas: 15, archivo: "JUGADOR.ai"}
```

Después el diseñador arma el arte sobre esa base y el arte va en el pedido (`POST /pedidos`).

---

## 7. Errores y alarmas

- Errores de la API: `{"error": "texto"}` con `400` (referencia inválida), `401`, `404`, `409`, `415`.
- Problemas del pedido: **alarmas** `{codigo, frena, etapa, mensaje, donde: {campo, fila}}`.
  `frena: true` rechaza; `false` es un aviso. `donde.campo` dice dónde está (`disenos[1].moldes[0].tela`,
  `planilla[2].talle`). Las etapas: `datos` (en el acto), `arte` y `tizada` (llegan por el estado o el aviso).
- Catálogo completo: `GET /alarmas` · cómo evitarlas antes de mandar: [`FORMATO_PEDIDO.md` §6](FORMATO_PEDIDO.md).

---

## 8. Archivos de esta carpeta

| Archivo | Qué es |
|---|---|
| `LEEME.md` | Por dónde empezar |
| `API.md` | Este documento |
| `FORMATO_PEDIDO.md` | `pedido.json` campo por campo, el arte, las alarmas |
| `openapi.yaml` | La API para Postman / Insomnia / generar un cliente |
| `esquemas/pedido.schema.json` | JSON Schema del pedido (para validar en el otro sistema) |
| `esquemas/resultado.schema.json` | JSON Schema de `GET /pedidos/{ref}` y del aviso |
| `pedido_ejemplo.json` | Un pedido completo (revisado contra el catálogo real: pasa) |
| `resultado_ejemplo.json` | Lo que vuelve cuando está listo (= el cuerpo del aviso) |
| `respuestas/*.json` | La respuesta REAL de cada ruta (HTTP + cuerpo) |
| `codigo/enviar_pedido.py` | Armar el .zip, revisar, mandar, esperar y bajar los PDF (Python, sin dependencias) |
| `codigo/recibir_aviso.py` | Recibir el aviso y comprobar la firma (Python, sin dependencias) |
| `codigo/cliente.mjs` | Lo mismo en Node 18+ (revisar, mandar, estado, bajar, firma) |

Y un sistema de ejemplo que hace TODO esto con pantalla: el **sistema de ventas de prueba**
(repositorio aparte), que arma pedidos como en TIZADA, los manda, recibe el aviso, muestra los PDF y
comprueba en Drive que cada archivo sea el del resultado.
