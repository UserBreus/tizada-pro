# Cambios que tocan a su sistema

Una entrada por cada actualización de TIZADA PRO que se sube, **la más nueva arriba**. Cada una contesta lo
mismo, en este orden:

1. **¿Hay que cambiar algo en su sistema?** Sí o No.
2. **Cambió de nombre** — antes se llamaba así → ahora se llama así (rutas, campos del JSON, valores, nombres de archivo).
3. **Se sacó** — lo que deja de existir y qué usar en su lugar.
4. **Contesta distinto** — misma pregunta, otra respuesta (formato, textos de aviso, orden, cantidades).
5. **Nuevo y opcional** — lo que se puede empezar a mandar; si no lo mandan, todo sigue igual.

Si una actualización no trae nada para su sistema, igual tiene su entrada diciendo «No»: así saben que se revisó.

---

## 23/11/2026 · el talle de cada mesa también con `una_por_fila`

**¿Hay que cambiar algo en su sistema? Sólo si leen el nombre del archivo por posición.** El « - xN» sigue al final.

- **Contesta distinto (nombre del archivo):** con `mesas.modo: "una_por_fila"` el nombre de cada mesa ahora dice su
  talle, después de la fila: antes `REF__Mesa 3 - Tela - Fila 3 - x5.pdf` → ahora `REF__Mesa 3 - Tela - Fila 3 - Talle M - x5.pdf`
  (varios talles: `Talles S-M`). Si leen la fila o las copias con una expresión que espera `Fila N - xN` pegados,
  ajústenla; si sacan las copias del « - xN» final, no cambia nada.
- **Contesta distinto (JSON):** los `archivos[]` de esas mesas traen ahora `talles` (antes sólo con `por_talles`).
- Nada se sacó.

## 23/11/2026 · tizada para corte (`modo: "corte"`) y los formatos de corte

**¿Hay que cambiar algo en su sistema? No.** Todo lo nuevo es opcional: si no lo mandan, los pedidos siguen igual.

- **Nuevo y opcional:** `modo: "corte"` en la cabecera del pedido — la **tizada para corte**: sin arte, cada pieza
  en blanco con **sólo su línea de corte** (el molde, sin etiqueta), y **cada talle en su mesa** (salvo que `mesas` diga otra cosa). No
  lleva arte, tipografías ni editables (si vienen se ignoran con el aviso `corte-ignora-arte`); nombre y número no se
  exigen. Ver «Tizada para corte» en FORMATO_PEDIDO.md.
- **Nuevo y opcional:** `opciones.formatos` (`dxf`, `ai`, `plt`, `svg`, `eps`; sólo con `modo: "corte"`). Cada mesa vuelve además en esos formatos: en `archivos[]` con `tipo: "corte"` (nuevo)
  y `formato` (nuevo), con los mismos datos de la mesa que su PDF.
- **Nuevo y opcional:** `mesas.modo: "talle_por_mesa"` (cada talle en su propia mesa), también fuera del modo corte.
- **Alarmas nuevas:** `modo-invalido` y `formatos-invalidos` (frenan), `molde-no-corte` (frena: el molde a medida no
  entra en una tizada para corte), `corte-ignora-arte` y `formatos-sin-corte` (avisos).
- **Atención si validan `archivos[].tipo` contra una lista cerrada:** ahora puede venir `corte` (sólo si piden
  `modo: "corte"` con `formatos`).
- Nada cambió de nombre ni se sacó.

## 02/11/2026 · textos de aviso con singular y plural de verdad

**¿Hay que cambiar algo en su sistema? Sólo si comparan el TEXTO de los avisos.** Los códigos de alarma, los campos
y las etapas no cambiaron.

- **Contesta distinto (sólo la redacción):** los avisos del pedido ya no dicen «3 fila(s)», «2 pieza(s)», «1 prenda(s)»
  ni «N mesa(s)»: ahora «3 filas» / «1 fila», «2 piezas» / «1 pieza», con el verbo que corresponde («1 fila pedía…»,
  «2 filas pedían…», «1 pieza sin diseño saldrá…»). Lo mismo el rechazo por telas: «Hay 1 pieza sin tela asignada» /
  «Hay 3 piezas sin tela asignadas» (antes «pieza/s»). Si leen los avisos por su código (`alarmas[].codigo`), no les
  cambia nada.
- **Contesta distinto (nombre del archivo de la mesa, sólo con Copia):** cuando una mesa lleva algunas piezas de
  prendas cuyas otras piezas van en otra mesa, el nombre suma « - piezas sueltas de N prendas» antes de las copias:
  `REF__Mesa 2 - Tela - Fila 1 - piezas sueltas de 2 prendas - x1.pdf`. El « - xN» del final sigue estando siempre.
- Nada cambió de nombre ni se sacó.

## 30/10/2026 · un diseño no puede llevar dos prendas que lean la misma columna de talle

**¿Hay que cambiar algo en su sistema? Sólo si arman diseños así.** Regla nueva de TIZADA (igual en la pantalla):
en un mismo diseño, cada columna de talle va con UN solo molde. Una camiseta («Talle») y un short («Talle short»)
siguen yendo juntos; dos prendas que leen las dos «Talle» van en diseños distintos.

- **Contesta distinto:** un pedido con dos moldes que toman el talle de la misma columna dentro de un diseño ahora
  se rechaza con la alarma nueva **`misma-columna-de-talle`** (frena, etapa `datos`). Antes se aceptaba. Dos
  variables del MISMO molde en un diseño ya se rechazaban (`molde-repetido`): eso no cambió.
- Nada cambió de nombre ni se sacó.

## 27/10/2026 · crear la plantilla en Illustrator / CorelDRAW desde su sistema

**¿Hay que cambiar algo en su sistema? No.** Todo lo de antes sigue igual.

- **Contesta distinto (se suma un campo):** `GET /plantillas/{referencia}` en estado `listo` trae además
  `conectores`: para `illustrator` y `corel`, a dónde mandar cada archivo (`crear`), cómo saber si el conector
  está (`estado`), qué archivos le tocan (`tipo_archivo`), la `version` del conector que corresponde y su
  `instalador`. Si ignoran campos que no conocen, no les cambia nada.
- **Nuevo y opcional:** `codigo/crear_en_programa.js` — para su página, en la computadora del diseñador: hace lo
  mismo que el botón «Crear en Illustrator / CorelDRAW» de TIZADA (busca el conector, avisa si hay que
  actualizarlo, manda cada archivo en orden, junta el resultado). `codigo/cliente.mjs` suma `pedirPlantilla`,
  `esperarPlantilla`, `archivoPlantilla`, `conectores` y `conector` para su servidor.

## 26/10/2026 · cambiar piezas del molde (agregar formas, formas reales)

**¿Hay que cambiar algo en su sistema? No.** Sigue siendo una herramienta de Configuración › Moldería (ahora
también agrega formas nuevas a un molde). Nada de la API cambió de nombre ni contesta distinto. Un molde al
que le agregan formas sigue publicando las mismas variables; las formas nuevas entran sin nombre y no forman
parte de ninguna variable hasta que alguien las configure en TIZADA.

## 23/10/2026 · cambiar piezas del molde

**¿Hay que cambiar algo en su sistema? No.** Es una herramienta de Configuración › Moldería (cambiar la forma
de una pieza o moverla). Nada de la API cambió de nombre ni contesta distinto; un molde editado sigue
publicando las mismas variables, con las mismas piezas.

## 23/10/2026 · moldes archivados

**¿Hay que cambiar algo en su sistema? No es obligatorio**, pero conviene manejar la alarma nueva.

En TIZADA ahora se puede **archivar** un molde: ni el molde ni sus variables se usan en pedidos hasta que
lo vuelvan a habilitar.

- **Cambió de nombre:** nada.
- **Se sacó:** nada.
- **Contesta distinto:**
  - `GET /moldes` y `GET /variables` **no listan** un molde archivado ni sus variables (la `version` del
    catálogo cambia al archivar o habilitar: re-sincronizar como siempre).
  - `GET /moldes/{codigo}`, sus fotos y `POST /a_medida/calcular` de un molde archivado → **404**
    («ese molde está archivado»).
  - Un pedido o una plantilla que pida una variable o un molde archivado vuelve **rechazado con la
    alarma `molde-archivado`** (antes, ese caso no existía).
- **Nuevo y opcional:** la alarma **`molde-archivado`** (etapa `datos`, frena). Está en `GET /alarmas`.
  Qué hacer: sacar esa prenda de lo que se ofrece al vendedor, o pedir que la vuelvan a habilitar.

## 21/10/2026 · requisitos de la PC

**¿Hay que cambiar algo en su sistema? No.** Cambió sólo la pantalla de TIZADA (el aviso «Requisitos · apta / NO apta» se mide mejor). Nada de la API.

## 21/10/2026 · TIZADA PRO `c4de207`

**¿Hay que cambiar algo en su sistema? No.**

- **Cambió de nombre:** nada. Ninguna ruta de `/api/externo/v1`, ningún campo de `pedido.json` ni de la
  respuesta, ningún nombre de archivo.
- **Se sacó:** nada.
- **Contesta distinto:**
  - **El acomodo de las piezas.** Cuando un pedido trae piezas iguales (por ejemplo, muchas banderas iguales),
    TIZADA calcula con todas juntas el dibujo que se repite a lo largo de la mesa y lo usa si gasta menos tela.
    El mismo pedido puede dar **mesas más cortas, menos mesas o las piezas en otro lugar** que antes de esta
    actualización (102 banderas: de 25,67 m a 23,45 m). Los PDF se llaman igual («Mesa 1 - …») y el resultado
    tiene la misma forma; sólo cambia el dibujo de adentro y, si hay menos mesas, la cantidad de archivos.
    Si su sistema guarda el largo o la cantidad de mesas de un pedido viejo para compararlo, va a ver la diferencia.
  - **Aviso de pieza que no entra en la tela:** las medidas del texto ahora van con coma decimal, como en la
    pantalla (antes `… 157.5 cm de ancho × 1.5 m de largo …`, ahora `… 157,5 cm de ancho × 1,5 m de largo …`).
    Es un texto para personas: si su sistema lo lee buscando un número, que acepte la coma.
- **Nuevo y opcional:** nada en la API.

## 16/10/2026

**¿Hay que cambiar algo en su sistema? No.** Todo lo nuevo es opcional y un pedido armado como antes se sigue
aceptando igual. El detalle está en [`novedades_2026-10-16.html`](novedades_2026-10-16.html)
([PDF](TIZADA_PRO_Novedades_integracion_2026-10-16.pdf)): `ajustes`, `colores`, `mapeo_arte`, `reemplazos`,
`tipografia_por_campo`, `no_imprimir`, `planilla[].piezas`, `opciones.perfil_color`, `mesas.largo_max_m`,
`mesas.separar_disenos`, `mesas.modo: "talles_separados"` y `GET /a_medida/calcular?largo_max_m=`.
