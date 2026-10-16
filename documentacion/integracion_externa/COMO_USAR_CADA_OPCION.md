# TIZADA PRO — Cómo usar cada opción desde el programa externo

Este archivo es para **quien programa el otro sistema** (el de ventas / pedidos) que le manda los pedidos
a TIZADA PRO. Dice, opción por opción, **para qué sirve**, **cuándo usarla** y **cómo mandarla** en el
`pedido.json`. El detalle técnico de cada campo está en `FORMATO_PEDIDO.md`; las rutas, en `API.md`.

> Regla de oro: **todo lo que se elige en la pantalla de TIZADA al armar un pedido a mano, el otro
> sistema lo manda como un dato del `pedido.json`.** Si el dato no viene, TIZADA usa lo que tiene
> configurado el molde.

---

## 0. El pedido en una mirada

```json
{
  "formato": "tizadapro.pedido/1",
  "referencia": "OV-2026-00123",
  "opciones": { ... },          // qué hacer si algo falla (sección 9)
  "mesas":    { "modo": "normal" },   // cómo se reparten las mesas (secciones 1 y 2)
  "disenos": [                   // los diseños del pedido y sus prendas (secciones 3 a 8)
    { "nombre": "JUGADOR", "moldes": [ { "variable": "v_…", "tela": "232", "arte": "artes/jugador.ai" } ] }
  ],
  "planilla": [                  // una fila por prenda (o por grupo de prendas iguales)
    { "diseno": "JUGADOR", "talle": "M", "nombre": "PÉREZ", "numero": "10", "cantidad": "1" }
  ]
}
```

| Lo que el cliente elige en el otro sistema | Dónde va en el `pedido.json` | Sección |
|---|---|---|
| Cuántas prendas iguales de una fila | `planilla[].cantidad` (modo `normal`) | 1 |
| Que cada fila salga en su propia mesa y se imprima N veces | `mesas.modo = "una_por_fila"` + `planilla[].cantidad` | 1 |
| Qué talles van juntos en una mesa | `mesas.modo = "por_talles"` + `mesas.grupos` | 2 |
| Todos en la misma mesa pero sin mezclar talles | `mesas.modo = "talles_separados"` (+ `grupos` opcional) | 2 |
| El largo máximo de cada mesa | `mesas.largo_max_m` (sin él, el del nesting del molde) | 2 |
| Que cada diseño vaya en sus propias mesas | `mesas.separar_disenos = true` (sin él, el mismo molde se mezcla) | 2 |
| Los diseños del pedido (jugador, golero…) | `disenos[]` + `planilla[].diseno` | 3 |
| La prenda / variable | `disenos[].moldes[].variable` | 3 |
| Talle, nombre, número, manga… | las columnas de `planilla[]` | 4 |
| La tela | `moldes[].tela` y `moldes[].telas_por_pieza` | 5 |
| Piezas que no se hacen | `moldes[].piezas_apagadas` | 6 |
| Escudo bordado, logo en TPU… | `moldes[].editables` | 7 |
| Banderas y piezas a medida | `moldes[].medida`, `forma`, `orientacion`, `terminacion`, `tiras` | 8 |
| La letra del nombre / número | `disenos[].tipografias`, `tipografia_por_campo` | 3 |
| Qué hacer si falta algo | `opciones` | 9 |

---

## 1. 🔢 LA COLUMNA CANTIDAD: DOS USOS DISTINTOS

La columna de **cantidad** de la planilla sirve para dos cosas **diferentes**, y cuál se usa lo decide
`mesas.modo`. Es lo más importante de entender de este archivo.

| | **Uso 1 — «cuántas prendas»** | **Uso 2 — «copias de la mesa»** |
|---|---|---|
| Cómo se pide | `"mesas": {"modo": "normal"}` (o no mandar `mesas`) | `"mesas": {"modo": "una_por_fila"}` |
| Qué significa `cantidad: 3` | **3 prendas iguales**: TIZADA repite la fila 3 veces | **La fila se arma UNA vez** en su propia mesa, y esa mesa se **imprime 3 veces** |
| Cómo se acomodan las piezas | **Todas las filas mezcladas** en las mesas de cada tela, para gastar la menor tela posible | **Cada fila sola en su mesa**, en el orden de la planilla |
| Cuántas mesas salen | Las que hagan falta según el largo máximo de mesa (pueden ser pocas y largas) | **Una por fila** (por tela) |
| Qué devuelve el resultado | Un PDF por mesa, sin datos de fila | Un PDF por mesa con **`fila`** (el número de fila) y **`copias`** (la cantidad) |
| El nombre del archivo | `REF__Mesa 1 - Tela.pdf` (las mesas se numeran por tela) | `REF__Mesa 3 - Tela - Fila 3 - x5.pdf` |
| ¿Quién «repite»? | TIZADA (ya vienen todas las piezas en el PDF) | **El que imprime**: manda la mesa a la impresora `copias` veces |
| Requisito | — | La planilla del molde **tiene que tener** columna de cantidad (si no: alarma `mesas-invalido`) |

### Uso 1 — `normal`: la cantidad son PRENDAS

Es lo de siempre. Cada fila es una persona (o un grupo de prendas idénticas) y la cantidad dice cuántas
prendas iguales lleva.

```json
"mesas": { "modo": "normal" },
"planilla": [
  { "diseno": "JUGADOR", "talle": "M", "nombre": "PÉREZ",     "numero": "10", "cantidad": "1" },
  { "diseno": "JUGADOR", "talle": "L", "nombre": "RODRÍGUEZ", "numero": "7",  "cantidad": "2" },
  { "diseno": "JUGADOR", "talle": "S", "nombre": "",          "numero": "",   "cantidad": "15" }
]
```

Resultado: **18 camisetas** (1 + 2 + 15). TIZADA acomoda las piezas de las 18 juntas, mezcladas, en las
mesas de cada tela, buscando el menor consumo.

**Usarlo cuando:** es un pedido de equipo, de remeras con o sin nombre, de cualquier cosa donde lo que
importa es fabricar **todas las prendas** con el menor gasto de tela. **Es el uso normal: si no sabés
cuál elegir, es éste.**

### Uso 2 — `una_por_fila` («Copia»): la cantidad son COPIAS DE LA MESA

Cada fila se arma **sola**, en **su propia mesa** (una por tela), con sus piezas **una sola vez**. La
cantidad **no multiplica las piezas**: viaja como dato, para que quien imprime mande esa mesa a la
impresora N veces.

**Las copias se acomodan JUNTAS en una mesa del largo máximo** (el del nesting del molde, o
`mesas.largo_max_m`), con el mejor acomodo de siempre. Si la cantidad llena esa mesa más de una vez, sale
**un** archivo con la mesa llena que se imprime varias veces (MAPA 720): con 19 copias y lugar para 5 → un
archivo con **5** (`por_mesa: 5`) que se imprime **3** veces (`copias: 3`); las **4** que sobran van **junto con
todo lo demás del pedido** que no llena una mesa (MAPA 725), y esa mesa se imprime **1** vez.
Unidades de cada archivo = `por_mesa × copias` (5×3 + 4×1 = 19). Todas las mesas van **del ancho
imprimible de la tela** (`ancho_cm`), como siempre.

**Sólo la mesa LLENA va aparte; lo demás va junto (MAPA 725).** Las filas con la misma pieza (mismo molde y
mismo talle, aunque cambie el diseño o el texto) que alcanzan para llenar una mesa salen en mesas que **se
repiten**, con sus lugares repartidos en proporción. Ejemplo: JUGADOR 33 y GOLERO 34 con lugar para 8 → un
archivo con 4 + 4 que se imprime **8** veces. **Todo lo que no llena una mesa** —de cualquier fila y de
cualquier talle— se acomoda **junto**, como sin Copia, y esas mesas se imprimen 1 vez. Las mesas con varias
filas traen `"fila": null` y `"filas": [{"fila": 1, "por_mesa": 4}, {"fila": 2, "por_mesa": 4}]`. Separar
talles es `mesas.modo = "por_talles"`; separar diseños, `mesas.separar_disenos: true`.

```json
"mesas": { "modo": "una_por_fila" },
"planilla": [
  { "diseno": "BANDERA CLUB", "cantidad": "20" },
  { "diseno": "BANDERA SPONSOR", "cantidad": "5" }
]
```

Resultado: si las dos banderas son de **moldes distintos**, una mesa por fila; si son del **mismo molde**, mesas
mezcladas que se repiten (ver arriba). En el resultado, cada archivo de tizada trae:

```json
{ "tipo": "tizada", "nombre": "OV-2026-00123__Mesa 1 - Bandera (1,60) - Fila 1 - x20.pdf",
  "mesa": 1, "fila": 1, "copias": 10, "por_mesa": 2, "ancho_cm": 157.0, "largo_cm": [312.4], ... }
```

**Usarlo cuando:** lo mismo se fabrica **muchas veces igual** y conviene imprimir la mesa repetida en vez
de armar una tizada gigante: banderas o banderines iguales, prendas sin nombre ni número, muestras,
pedidos donde cada fila es un artículo distinto que se produce por separado. También cuando el taller
**necesita cada fila separada** (para cortar, controlar o entregar por separado).

**No usarlo cuando:** las prendas llevan nombre o número distintos (cada una es una fila de cantidad 1:
da lo mismo que `normal` pero con más mesas y más tela).

### Lo que conviene que haga el otro sistema

- **Guardar `fila`, `copias` y `por_mesa`** de cada archivo del resultado: se imprime `copias` veces
  esa mesa, y cada impresión trae `por_mesa` unidades. Para contar unidades: `por_mesa × copias`. Si la mesa
  mezcla filas del mismo molde, `fila` viene `null` y `filas` dice cuántas de cada una trae cada impresión.
- La **cantidad vacía vale 1** en los dos usos. Tiene que ser un entero de 1 en adelante (si no:
  alarma `cantidad-invalida`).
- `una_por_fila` y `por_talles` **no se combinan**: se elige un solo `modo`.
- Ofrecerle al usuario la elección con palabras simples, por ejemplo: «¿Cantidad de prendas
  (se mezclan para ahorrar tela)?» / «¿Cantidad de copias de esta mesa (cada fila aparte)?».

---

## 2. 🗂️ Talles por mesa (`por_talles`)

Para que ciertos talles salgan **juntos en una mesa y separados de los demás** (por ejemplo, para cortar o
entregar por talle). Las prendas cuentan igual que en `normal` (la cantidad son prendas).

```json
"mesas": { "modo": "por_talles", "grupos": [["S", "M"], ["L", "XL"]] }
```

- Cada lista es una mesa (o las mesas que haga falta, si no entra en una): S y M juntos, L y XL juntos.
- Los talles que no estén en ningún grupo van juntos **al final**.
- Los talles se escriben como los tiene el molde (`GET /variables` / `GET /moldes/{codigo}`); uno que no
  existe → alarma `mesas-invalido`.
- En el resultado cada archivo trae `"talles": ["S", "M"]` y el nombre lo dice: `REF__Mesa 1 - Tela - Talles S-M.pdf`.
- **Un talle por mesa:** un grupo por talle: `[["S"], ["M"], ["L"]]`.

### Talles separados en la MISMA mesa (`talles_separados`)

Para gastar **menos mesas sin mezclar talles**: cada talle se acomoda solo (con el mejor acomodo) y abajo
sigue el próximo, con una **línea punteada** entre talles impresa en el PDF. Si no entra en el largo máximo,
sigue en otra mesa.

```json
"mesas": { "modo": "talles_separados", "grupos": [["XS", "S"]] }
```

- `grupos` es **opcional**: los talles de un mismo grupo sí van mezclados entre sí (útil para talles con
  pocas prendas); los que no están en ningún grupo van **cada uno aparte**.
- En el resultado cada archivo trae `"talles": [...]` (los de esa mesa, en orden) y `"separados": true`.

### Separar diseños (`separar_disenos`)

Es el botón **«Separar»** de la planilla. Por defecto el **mismo molde se mezcla** aunque las piezas sean de
diseños distintos (se gasta menos tela). Con `true`, cada diseño va en **sus propias mesas** en cualquier
`modo`, y cada archivo trae `"diseno": "JUGADOR"`.

```json
"mesas": { "modo": "una_por_fila", "separar_disenos": true }
```

### El largo máximo de cada mesa (`largo_max_m`)

Es el botón **«Largo»** de la planilla. Sin él, cada mesa llega hasta el largo del **nesting** del molde
(`largo_mesa_cm` en `GET /variables`). Con él, ninguna mesa pasa de ese largo y lo que no entra sigue en
otra mesa. Vale con cualquier `modo` (también Copia y talles por mesa).

```json
"mesas": { "modo": "normal", "largo_max_m": 12.5 }
```

- En metros, de 0,10 a 50. Otra cosa → `largo-mesa-invalido`.
- Una pieza más larga que ese largo no se puede armar: un molde a medida lo avisa al validar (`tela-no-entra`);
  `POST /a_medida/calcular` acepta el mismo `largo_max_m` para saberlo antes.

---

## 3. 🎨 Diseños, prendas y arte

- **`disenos[]`**: cada diseño del pedido (JUGADOR, GOLERO, VISITANTE…). El `nombre` es el que va en la
  columna `diseno` de cada fila. Con **un solo diseño**, las filas pueden no llevar `diseno`.
- **`disenos[].moldes[]`**: las prendas de ese diseño. Cada una se identifica por su **`variable`** (la
  clave `v_…` de `GET /variables`). **Una variable por prenda** en cada diseño.
- **`arte`**: el archivo del diseño (.ai / .pdf). Va en el molde, o una vez en el diseño para todas sus
  prendas. Se arma sobre la plantilla que da TIZADA (`POST /plantillas`).
- **Tipografías:** mandar el archivo (`disenos[].tipografias`) **sólo** si el nombre/número usa una letra
  que TIZADA no tiene (`GET /tipografias`). Para forzar una del catálogo: `"tipografia_por_campo":
  {"numero": "Anton Regular"}` (en el diseño, o en el molde para ése solo). Para cambiar una tipografía
  del arte por otra del catálogo: `moldes[].reemplazos`.

### Lo mismo que hace el operario en el paso Arte (MAPA 712)

| En la pantalla | En el pedido |
|---|---|
| «Editar diseño»: mover, rotar, escalar o espejar un objeto | `moldes[].ajustes = {"escudo": {"dx": 0.05, "rot": 15, "scale": 1.2}}` (+ `talles` opcional) |
| Cambiarle el color a un objeto | `moldes[].colores = {"escudo": {"fill": [0, 1, 1, 0]}}` (CMYK 0 a 1) |
| Arrastrar una mesa del arte a una pieza | `moldes[].mapeo_arte = {"Frente": 1}` (número o rótulo de la mesa) |
| «Sin marca» en algo que se sublimaría | `editables = {"sponsor": "no_imprimir"}` |
| Repo: tocar qué piezas hace la fila | `planilla[].piezas = {"v_redondo": ["Cuello"]}` |
| Elegir el perfil de color | `opciones.perfil_color` (de `GET /perfiles`) |

---

## 4. 📋 Las columnas de la planilla

Las claves de cada fila son las **columnas de la planilla del molde** (`GET /moldes/{codigo}` →
`planilla.columnas`). **Cualquier otra clave se ignora** con el aviso `columna-desconocida` (no frena el pedido,
pero ese dato no se usa). Todo como texto:
los números con cero adelante entre comillas (`"07"`).

| Columna | Qué poner |
|---|---|
| `diseno` | El `nombre` de un diseño del pedido |
| la de **talle** | El talle tal cual lo tiene el molde (`M`, `2XL`, `10`). **Cada molde lee su columna de talle** (camiseta en «talle», short en «talle short»). Si la planilla es **sin talles**, no va |
| la de **nombre** / **número** | Lo que se estampa. Vacío = esa prenda sale sin nombre / número |
| las de **opciones** (p. ej. `manga`) | Una de sus opciones (`"Corta"`), o varias con ` + ` (`"Corta + Larga"`). El molde tiene que tener esa opción |
| la de **cantidad** | Ver sección 1 |

Una fila con un dato obligatorio vacío (p. ej. sin talle) → alarma `columna-obligatoria-vacia`.

---

## 5. 🧵 La tela

- **`tela`** (obligatorio): el **id** de la tela principal, para todas las piezas de la prenda.
- **`telas_por_pieza`** (opcional): las excepciones, por el nombre **genérico** de la pieza (sin número):
  `{"Cuello": "486", "Tapa costura": "486"}`.
- Si una pieza **no entra** en el ancho de la tela, el pedido se frena con `tela-no-entra` (dice cuánto se
  pasa y lo máximo que entra).

---

## 6. ✂️ Piezas que no se hacen (`piezas_apagadas`)

Para fabricar la prenda **sin** algunas piezas en **todo** el pedido (por ejemplo, sin tapa costura):

```json
"piezas_apagadas": ["Tapa costura"]
```

Vale para el diseño y la prenda donde se pone. No se pueden apagar todas (`todas-las-piezas-apagadas`).

> ⚠️ **Hoy no se puede hacer por fila** (la «Repo» de la pantalla: que **una** fila haga sólo algunas
> piezas, para reponer). Por la API, cada fila hace todas las piezas que no estén apagadas.

---

## 7. 🏷️ Lo que no se sublima (`editables`)

Para cada objeto editable del arte (capa «Editable escudo» → `escudo`):

| Valor | Qué pasa |
|---|---|
| `"sublimado"` (o no nombrarlo) | Sale impreso con el diseño |
| `"tpu"`, `"bordado"`, `"dtf"` | **No se imprime**: va una cruz de posición en la tela y la ficha técnica dice qué aplicar y dónde |
| `{"proceso": "bordado", "cruz": false}` | Igual, pero **sin** la cruz en la tela (sólo en la ficha) |

> La posición y el tamaño del objeto son los del arte: por la API no se mueven ni se agrandan.

---

## 8. 📐 Banderas y piezas a medida

Sólo para las prendas que `GET /variables` marca como `a_medida`. La fila de la planilla **no lleva
talle** para esas prendas.

| Campo | Qué poner |
|---|---|
| `medida` | `{"ancho_m": 3, "alto_m": 1.5}` — la medida del **DISEÑO** en metros. TIZADA le suma el margen de la terminación y ése es el total que se imprime. Círculo: `{"diametro_m": 1.2}` |
| `forma` | `rectangulo` (si no viene), `circulo` o `triangulo` |
| `orientacion` | Sólo triángulo: hacia dónde va la **punta**: `abajo` (banderín), `arriba`, `izq`, `der` |
| `terminacion` | `dobladillo` (se dobla el margen), `overlock` (borde con overlock) o `sin` (sin margen) |
| `tiras` | Las marcas para coser tiras: `{"lleva": true, "lados": {"arriba": 5, "abajo": 5}}` (cada número cuenta las 2 puntas). Triángulo: `{"base": 5, "laterales": 4}`; círculo: `{"alrededor": 12}`. Con `"marcar": false` no se imprimen pero salen en la ficha |

- **La bandera siempre puede girar 90°** para entrar en la tela (una de 3 × 1,50 entra en la tela de 1,60
  girada).
- **Antes de mandar:** `POST /a_medida/calcular` devuelve el total, en qué telas entra y las tiras como van a salir.
  Conviene usarlo para mostrarle al cliente si la medida entra **antes** de confirmar.
- El arte se arma sobre la plantilla de **esa medida** (`POST /plantillas` con la `medida`). Un arte de
  otra medida avisa `arte-otra-medida`.

---

## 9. ⚙️ Qué hacer si algo falla (`opciones`)

| Opción | Valores | Por defecto | Consejo |
|---|---|---|---|
| `si_falta_tipografia` | `rechazar` · `predeterminada` | `rechazar` | `rechazar`: mejor frenar que estampar con otra letra |
| `si_texto_no_entra` | `achicar` · `rechazar` | `achicar` | `achicar` avisa (`texto-se-achica`) y sigue |
| `si_piezas_en_blanco` | `rechazar` · `seguir` | `rechazar` | `rechazar`: una pieza sin diseño casi siempre es un arte incompleto |
| `perfil_color` | archivo .icc | el del sistema | Sólo si el taller pide uno especial |
| `carpeta` | `"2026-10/OV-123"` | la referencia | La subcarpeta de Drive donde quedan los PDF |

---

## 10. ✅ Antes de mandar un pedido

1. ¿Cada fila tiene su `diseno` (si hay más de uno) y su talle (si la planilla tiene talles)?
2. ¿La **cantidad** significa prendas (`normal`) o copias de la mesa (`una_por_fila`)? ¿Se eligió el `modo`
   que corresponde?
3. ¿Cada prenda tiene su `tela`? ¿Las banderas, su `medida`, y entra en la tela (`POST /a_medida/calcular`)?
4. ¿El arte está hecho sobre la plantilla de esa variable (y de esa medida, si es a medida)?
5. Probar con **`POST /pedidos/validar`**: dice todas las alarmas **sin generar nada**.
6. Al recibir el resultado: guardar `fila`/`copias`/`por_mesa` (modo `una_por_fila`) o `talles` (`por_talles` / `talles_separados`) de
   cada archivo, y bajar los PDF antes de 30 días (verificando `sha256`).
