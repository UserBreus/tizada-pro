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
