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

## 2. EL RECORRIDO DEL CLIENTE (lo que va a ver)

Todo esto pasa **desde el Pedido**, **no** desde Configuración:

1. **Sube el archivo** (`.ai` / `.pdf`: una capa por talle, el diseño ya adentro).
2. El sistema **detecta las piezas** y le muestra **sólo los contornos** (liviano).
3. **Nombra las piezas** — para que el sistema sepa qué es cada una.
4. **Elige la planilla** que va a usar ese molde.
5. **Marca dónde va la etiqueta** en cada pieza (sobre el contorno).
6. Listo: el molde queda usable en el pedido como cualquier otro.

**Lo que NO hace el cliente** (lo deja configurado el admin, una vez): grosor y color del **borde
de corte**, tamaño y tipografía de la **etiqueta**, separación y márgenes del **nesting**.

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

- [ ] ¿Un molde del camino B tiene **variables** (modelos), o va **entero** como los «Mis
      artículos» de hoy? (hoy un molde propio no tiene variables y el motor genera todas sus piezas)
- [ ] ¿Lleva **toggles** (manga corta/larga, capucha)? Si el diseño ya está adentro, cada opción
      tendría que venir dibujada en el archivo.
- [ ] ¿Cómo se asigna la **tela** por pieza en este camino?
- [ ] Las 9 mesas: ¿es **una pieza por mesa** siempre, o una mesa puede traer varias piezas?
      (se responde solo al correr la detección de E1 sobre el archivo real)

---

## 7. EL PLAN — entregas (cada una funciona sola)

> Regla del proyecto: **nada a medias.** Si una entrega no entra en una sesión, se parte en
> entregas que funcionen, nunca a medio hacer.

### [ ] E0 — Andamiaje (esta sesión)
- Rama `pruebas-tizada-con-diseno` + commit de partida (local, sin push).
- **Dos localhost a la vez:** segunda carpeta (`git worktree`) clavada en el commit de partida =
  **EL ACTUAL en 8050**; esta carpeta (la rama) = **LA PRUEBA en 8051**. Las dos ven los mismos
  moldes.
- Este archivo + su memoria persistente.

### [ ] E1 — Detectar las piezas del archivo nuevo (backend)
- Módulo nuevo `piezas_con_diseno.py`: **aislar la capa del talle** → ensamblado por solape
  (union-find sobre grilla) → **borde externo = trazado de la máscara**.
- Salida por pieza: contorno real, qué trozos la componen, bbox en mm.
- El molde queda registrado **igual que hoy** → todo lo que ya existe (nombrar, agrupar homólogas
  entre talles, visor) sigue andando sin cambios.
- **Contrato** `verificar_molde_con_diseno.py` contra `CAMISETA JUGADOR.ai`: cuántas piezas por
  talle, ninguna pieza partida en dos, ninguna pieza pegada a su vecina, y **los 20 talles
  separados** (el error que este archivo provoca si no se aísla la capa).

### [ ] E2 — El alta desde el Pedido
- Botón **«Subir molde con diseño»** en Pedido → Mis artículos (al lado del que ya existe).
- Marca `origen: "con_diseno"` en el producto.
- **Visor de contornos liviano**: endpoint que devuelve SÓLO los trazados de contorno (sin el
  diseño) → sobre eso el cliente **nombra las piezas**.
- **Elegir la planilla** en el mismo paso.
- Al terminar, el molde ya aparece para elegir en el pedido.

### [ ] E3 — El motor: la tizada desde el molde con diseño
- Variante de `_armar_base`: **sin arte y sin mapeo**. El contenido de la pieza es el del propio
  archivo, recortado a su contorno. Sin escalado ni `cm_encajar`: ya está en su lugar.
- Más el **borde de corte** (el que dejó el admin) y el **nombre/número** leídos del propio molde.
- Nesting y hojas: los de siempre.
- **Contrato**: la pieza generada tiene que ser idéntica al recorte del archivo original.

### [ ] E4 — La etiqueta: el cliente sólo marca dónde va
- Sobre el **contorno** (liviano), pieza por pieza.
- Reusa el sistema de posiciones que ya existe (`etiqueta.posiciones`) — ojo con la cascada de
  claves y con [[etiqueta-baseline-no-romper]].
- Tipografía, tamaño y contenido: del admin.

### [ ] E5 — La configuración del admin
- Borde de corte por defecto, etiqueta por defecto y nesting por defecto **para este camino**.
- Pantalla en Configuración (no la ve el cliente).

### [ ] E6 — Que todo lo demás siga igual
- Ficha técnica, trabas antes de fabricar, ayuda guiada, permisos.
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

- **2026-08-31** — Estudiado el proyecto `Prueba para tizada` y decidido el camino. Medido el
  archivo real `CAMISETA JUGADOR.ai` (§3): 123 MB, 9 mesas, 20 talles en capas, cada pieza es una
  máscara de recorte con su diseño adentro. Decidido: talles en capas, nombre/número siguen, la
  detección se porta a Python (un solo motor), la UI de edición sólo con contornos. Creada la rama
  y este archivo.
  ⚠️ Trampa de herramienta: escribir este archivo con un heredoc de bash falló
  (`unexpected EOF`); va con la herramienta de escritura, como manda [[escrituras-atomicas]].
