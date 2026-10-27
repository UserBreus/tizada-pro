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
