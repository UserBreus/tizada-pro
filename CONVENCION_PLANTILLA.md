# Cómo armar la plantilla `.ai` para que el motor funcione

Esta es la **única** guía que necesitás para preparar tus archivos de Illustrator.
Si seguís estos nombres al pie de la letra, el motor reconoce todo solo.

> **Regla de oro nueva:** **una mesa de trabajo por pieza**, y **todos los talles
> viven como capas dentro de esa misma mesa**. Ya **no** se hace una mesa por
> talle ni se reparten los talles en mesas distintas.

---

## 1. Mesas de trabajo (artboards)

- **Una mesa de trabajo por pieza.** Si la prenda tiene Frente, Espalda, Cuello y
  Manga → son **4 mesas**, una por pieza. Nada más.
- **Todos los talles de esa pieza van en esa misma mesa**, superpuestos, cada uno
  en su propia capa (ver punto 2). No importa que se pisen entre sí: el motor los
  separa por capa.
- **Tamaño de la mesa:** ajustala a la pieza. El **alto** de la mesa = el alto de
  la pieza en el **talle más grande** (más un margencito). El **ancho crece y se
  achica en proporción** al alto: dejá que la pieza marque la proporción, no
  estires la mesa a lo ancho a mano.
  - *Por qué:* el motor recorta cada pieza por su contorno real, así que el tamaño
    exacto de la mesa no cambia el resultado del corte. Pero una mesa ajustada a la
    pieza da previews limpias, archivos más livianos y validaciones más confiables.
- **La plantilla (molde) y el arte deben tener EXACTAMENTE las mismas mesas:**
  misma cantidad, mismo orden y mismas medidas. El arte se dibuja *encima* de la
  misma estructura de mesas de la plantilla.

| Antes (lo que hay que dejar de hacer) | Ahora (lo correcto) |
|---|---|
| Mesa "talles XS–2XL", mesa "talles 3XL–4XL", mesa "14/16"… | Una mesa **Frente**, una **Espalda**, una **Cuello**… |
| Una pieza repartida en 3 mesas | Cada pieza en **una sola** mesa |
| 24 mesas | tantas mesas como piezas (ej. 4–9) |

---

## 2. Capas (layers) = talles

- **Una capa por talle.** El nombre de la capa es **exactamente** el código del talle.
- Los nombres de capa deben coincidir con los talles que después cargás en el pedido.

Talles soportados (usá los que necesites):

| Línea | Nombres de capa válidos |
|---|---|
| Unisex / hombre | `XS` `S` `M` `L` `XL` `2XL` `3XL` `4XL` `5XL` `6XL` |
| Mujer | `XSfem` `Sfem` `Mfem` `Lfem` `XLfem` `2XLfem` `3XLfem` `4XLfem` `5XLfem` `6XLfem` |
| Numérica | `2` `4` `6` `8` `10` `12` `14` `16` |

- **Capas reservadas del sistema** (no son talles, no las nombres como talle):
  `Fondo`, `Personalizable`, `Capa 1`.
- Dentro de la capa de cada talle va: **el contorno de la pieza en ese talle** +
  **la etiqueta de texto** (punto 3).
- El contorno es el trazado **cerrado de mayor área** de esa capa. Piquetes y
  líneas internas pueden estar; el motor toma el contorno externo.

---

## 3. Etiqueta de cada pieza (un texto por talle)

En la capa de **cada talle**, poné un texto con este formato **exacto**:

```
TALLE-Pieza-#
```

- **Empieza** con el código del talle + guión. Ej: `M-`
- **Sigue** el nombre de la pieza. Ej: `Frente`
- **Termina** con `-#` (dejalo literal con el numeral; el motor le pone el número
  real al generar: `-#01`, `-#02`, …).

Ejemplos válidos:

```
M-Frente-#        3XL-Espalda-#       XSfem-Cuello-#       16-Manga-#
```

Reglas importantes:

- El **nombre de la pieza** tiene que ser **igual en todos los talles** de esa mesa.
  Así el motor entiende que es **una sola pieza** (Frente en M, Frente en L, etc.).
- La **posición, el ángulo y el tamaño** de este texto definen **dónde y cómo sale
  la etiqueta de corte** impresa en la pieza final (queda dentro de la costura).
- Es texto normal de Illustrator (no hace falta convertirlo a curvas acá; el motor
  lo regenera en curvas en la salida).

---

## 4. Nombres de pieza estándar

Usá estos nombres para que el motor aplique tela y rotación correctas:

| Pieza | Tela | Rotación en el nesting | Personalizable |
|---|---|---|---|
| `Frente` | Principal | no rota | no |
| `Espalda` | Principal | no rota | **sí** (nombre + número) |
| `Cuello` | RIB | 90° | no |
| `Tapacostura` / `TC` | RIB | 90° | no |
| `Manga` | Principal | 90° | no |
| Otras (`Costadillo`, etc.) | Principal | 90° | no |

- Si manejás **manga corta y larga** en la misma plantilla, nombralas distinto:
  `Manga corta` y `Manga larga` (o incluí `(corta)` / `(larga)` en el nombre, por
  ejemplo `Manga Derecha (corta)`). El motor elige la que corresponde según la
  manga del pedido.
- Si una pieza no aparece en esta tabla, el motor la trata como **Principal, 90°**.
  Las reglas viven en `datos/config_producto.json` y se pueden ajustar ahí.

---

## 5. Personalización (nombre y número en la espalda)

Solo si la prenda lleva nombre/número:

- En la capa **`Personalizable`**, sobre la mesa de la pieza **`Espalda`**, poné dos
  textos placeholder:
  - `NOMBRE` → lo reemplaza el apellido del pedido.
  - `00` → lo reemplaza el número del pedido.
- El motor respeta **posición, tamaño y tipografía** de esos placeholders.
- La tipografía que uses ahí (y en las etiquetas) tiene que estar cargada en el
  **catálogo de tipografías** de la app, o el pedido no entra.

---

## 6. Checklist antes de subir

- [ ] Una mesa de trabajo por pieza (no por talle).
- [ ] Cada talle es una capa con el nombre exacto del talle (`M`, `3XL`, `16`, …).
- [ ] En cada capa de talle hay un texto `TALLE-Pieza-#` con el mismo nombre de
      pieza en todos los talles.
- [ ] El arte tiene **las mismas mesas** que la plantilla (cantidad, orden, medida).
- [ ] La capa `Personalizable` tiene `NOMBRE` y `00` sobre la Espalda (si aplica).
- [ ] Las tipografías de etiquetas y personalización están en el catálogo.

Cuando subís la plantilla, la app te muestra **pieza por pieza** qué detectó y, si
algo no cumple esta convención, **te dice exactamente qué corregir**.

> **¿No querés tocar Illustrator para poner las etiquetas?** Si la moldería no
> trae los textos `Talle-Pieza-#`, usá **«Etiquetar piezas visualmente»** en la
> app: te muestra la moldería, hacés clic en cada pieza (o arrastrás para agarrar
> varias), le ponés el nombre y listo. El nombre se propaga a **todos los talles**
> solo. Etiquetás cada pieza una vez, no talle por talle.

---

## 7. El arte: dos formas de trabajarlo

**Opción A — Arte sobre el molde (clásico).** El arte es **el mismo archivo del
molde con el diseño pintado encima**: mismas mesas, mismos talles. El sistema
recorta el diseño con el contorno del molde, en su lugar exacto.

**Opción B — Arte separado (una mesa por pieza).** Diseñás el arte **aparte**: una
mesa de trabajo por pieza, con **solo el diseño** (capa `diseño`; las guías van en
una capa `guias` que el sistema descarta). No necesitás talles ni contornos en el
arte.

- El **artboard de cada mesa = el área del diseño**: lo que llene el artboard
  llena la pieza (hacelo del tamaño/proporción de la pieza).
- **Para que el sistema reconozca solo qué diseño es cada pieza** (frente → Frente),
  escribí en cada mesa del arte el **nombre de la pieza como texto**, *igual* al
  que le pusiste en el molde (ej. `Frente`, `Espalda`, `Manga Corta Derecha`).
  - Poné ese texto en una capa llamada **`guias`** → el sistema lo lee para
    mapear pero **lo descarta al imprimir** (no sale en la prenda).
  - No importan mayúsculas ni guiones: `FRENTE`, `Frente` y `frente` valen igual.
  - Si **todas** las mesas tienen su nombre, al subir el arte queda **aprobado
    solo**, sin mapear a mano.
- Si **no** ponés los nombres, no pasa nada: subís el arte y tocás **«Mapear arte
  a piezas»** — ves una miniatura de cada mesa y elegís la pieza en un desplegable
  (con una sugerencia automática por proporción).
- El sistema **escala el diseño al ALTO** de la pieza en cada talle y el **ancho
  crece/se achica en la MISMA proporción** (no deforma): queda centrado a lo ancho
  y el contorno recorta lo que sobra. Una sola vez por pieza; sirve para todos los
  talles. *Tip:* hacé el artboard del arte con la **misma proporción** que la pieza
  para que el diseño la cubra justo (si es mucho más angosto, quedan bordes sin
  diseño; si es más ancho, se recorta a los costados).
- **El diseño va EN CURVAS (sin texto vivo).** Si el diseño tiene textos (una
  marca, un escudo con letras, etc.), convertilos a contornos en Illustrator
  (seleccionar → **Texto → Crear contornos**, `Ctrl+Shift+O`). El sistema entrega
  las hojas con cero fuentes, así que el texto vivo del diseño no sobreviviría.
  *Subir la fuente no alcanza* — hay que pasarlo a curvas.
- Para **nombre y número** (personalización), poné los placeholders `NOMBRE` y `00`
  en una capa `Personalizable` sobre la mesa del arte de la Espalda. Esa SÍ es la
  única tipografía que el sistema necesita en el catálogo (la re-dibuja con los
  datos del pedido).
