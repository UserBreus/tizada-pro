# 🧰 MANUAL DE HERRAMIENTAS — TIZADA PRO

> **Qué es esto.** Una herramienta por entrada: **qué hace**, **dónde está**, **qué tiene que estar
> hecho antes**, **los pasos exactos para completarla**, **qué queda guardado** (endpoint + archivo)
> y **las trampas** de cada una.
>
> **Cuándo leerlo.** Cuando hay que *usar* o *tocar* una pantalla concreta. Es el complemento
> operativo de `MAPA_DEL_SISTEMA.md` (que explica la arquitectura, los invariantes y el porqué).
> Regla: si cambia una herramienta, se actualiza **su entrada acá** + la sección del MAPA + el
> changelog del MAPA, en la misma tanda.
>
> Las explicaciones de la **ayuda guiada in-app** viven en `frontend/src/diccionario.js` y cuentan la versión
> corta de varias de estas herramientas: si acá se cambian los pasos, hay que revisar si el guion
> de esa guía quedó mintiendo.

---

## 0. Vocabulario mínimo (sin esto, media doc se lee al revés)

| Palabra | Qué es | Dónde vive |
|---|---|---|
| **MOLDE / moldería / producto (`pid`)** | El archivo con TODAS las piezas de TODOS los talles | `entrada/<pid>/plantilla.ai` |
| **PIEZA** | Una parte del molde (Frente, Manga, Cuello…) | `registro_producto.json`, `piezas.json` |
| **VARIANTE** | **El TALLE** (XS…6XL, 1…16). El picker que dice «variantes» muestra TALLES | capas OCG del molde |
| **VARIABLE** | **La selección de piezas / modelo** (MP1-A, «con costadillo»). Es lo que se elige por fila | `prod["variantes"] = [{clave:"v_xxx", label, valores…}]` |
| **GRUPO** | Bolsa de piezas donde adentro viven las VARIABLES (ej. «Tipo de manga») | `prod["grupos"]` |
| **MODELO** | Un conjunto de VARIABLES con nombre | `prod["modelos"]` |
| **DISEÑO** | Un arte con nombre. «Principal» = el base | `entrada/<pid>/disenos/<slug>/arte.ai` |
| **MESA** | Una página del `arte.ai` = el diseño de una pieza | — |
| **MAPEO** | Qué mesa va en qué pieza, **por variable** | `mapeo_arte.json` |
| **TIZADA / HOJA** | El PDF final con las piezas acomodadas, una por tela | `trabajos/<tid>/HOJA_*.pdf` |

⚠️ **VARIABLE ≠ VARIANTE**: el código las cruza (el estado `verVariante` guarda la **VARIABLE**).
En el motor la variable viaja por su **clave `v_xxx`**, nunca por el label.

---

## 1. Las tres zonas y el orden de trabajo

```
CONFIGURACIÓN GENERAL          ┐  se hace UNA vez para todo el sistema
  Telas · Planillas · Reglas   │  (§4)
  Nesting · Fuentes · Perfil   ┘

MOLDERÍA (por molde)           ┐  se hace UNA vez por molde
  subir molde → nombrar        │  (§2 y §3)
  variantes → nombrar piezas   │
  → variables → plantilla      │
  → telas/borde/etiqueta       ┘

PEDIDO (todos los días)        ┐  diseño → moldes → arte → planilla → enviar
                               ┘  (§5)
```

**Orden mínimo para que un molde produzca** (checklist en §7):
1. Crear la moldería → 2. Subir el molde → 3. Que cada **talle** tenga su capa nombrada →
4. Que cada **pieza** tenga nombre → 5. Al menos una **variable** con piezas →
6. **Telas** asignadas → 7. **Planilla** de columnas elegida → 8. **Arte** cargado y mapeado.

---

## 2. Preparar la moldería (Configuración › Molderías › *abrir un molde* › **Moldería**)

### 2.1 Crear una moldería

- **Dónde:** Configuración → tarjeta **Moldería** → botón **Nueva Moldería**.
- **Pasos:** escribir el nombre (`molde-nombre`) → **Crear Molde** (`molde-crear-ok`).
- **Guarda:** `POST /api/productos/crear {nombre, propio?}` → entrada nueva en
  `datos/productos_catalogo.json`, y el molde queda **activo** (global y **de la sesión**).
- **Trampa:** con `propio:true` el endpoint es **idempotente** (mismo dueño + mismo nombre =
  devuelve el que ya existe con `{"reusado":true}`). Fue la respuesta a los «4 artículos iguales».
- **Verificar:** aparece la tarjeta en la grilla con los badges `Sin Molde` / `Sin Diseño`.

### 2.2 Subir (o re-subir) el molde

- **Dónde:** dentro del molde → ajuste **Moldería** → zona de subida (`molde-subir`) o
  **Re-subir Plantilla**. También hay una guía in-app: **«¿Cómo exportar el molde desde tu
  programa?»** (`AyudaExportMolde`: Illustrator, Corel, Optitex/Gerber…).
- **Formatos:** `.ai` · `.pdf` (Corel/Affinity) · `.dxf` (AAMA/Optitex, **BETA**). El **ARTE** en
  cambio sólo acepta `.ai`/`.pdf`.
- **Pasos:** elegir el archivo → esperar el procesado → el visor muestra las piezas numeradas.
- **Guarda:** `POST /api/plantilla` (multipart `archivo` + **`pid`**) →
  - `entrada/<pid>/plantilla.ai` (y `plantilla_fuente.dxf` si vino DXF),
  - `datos/productos/<pid>/registro_producto.json` (TODAS las piezas por talle),
  - `resumen_plantilla.json`, `piezas.json` (ids estables),
  - `correspondencia_piezas.json` si el DXF trajo la correspondencia exacta pieza↔talle.
- **Qué hace de más:** descarta versiones previas (`reset_versiones`), y si ya había piezas
  nombradas **saca una foto del talle guía** y las **transfiere por geometría** al archivo nuevo
  (`snapshot_nombres_guia` + `remapear_registro`, se acepta si cubre ≥50%). El resultado se informa
  como `nombres_conservados`.
- **Trampas:**
  - Un `.ai` **ES** un PDF; que entre no garantiza que se lea todo: hace falta que el exportador
    conserve las **capas OCG** y el **texto vivo**. Affinity aplana la pila de apariencias → colores
    y bordes salen mal.
  - **Siempre mandar `pid` explícito.** Sin `pid` escribe en el molde **activo**, que no es
    necesariamente el que se está configurando.
  - DXF: no se corre `alta_plantilla` (Optitex no pone etiquetas «Talle-Pieza-#»); los talles vienen
    del DXF y las piezas se nombran en el visor. Con ≤25 nombres se auto-nombran.

### 2.3 Nombrar las variantes (talles) — `NombrarVariantes`

El talle de una pieza sale del **nombre de la capa**. Si el molde vino con `Layer 1`, `Capa 3` o con
**todo en una sola capa**, es inusable hasta resolver esto. Hay **dos modos** y el sistema **sugiere
uno** (`modo_sugerido`); se puede cambiar a mano con el selector **Por capa / Por piezas**.

#### Modo **POR CAPA** (el molde trae una capa por talle, sin nombre)
- **Pasos:** abrir el acordeón → revisar la **curva propuesta** (el sistema ordena las capas **por
  ÁREA**, verificado contra un molde real de 20 talles) → escribir/corregir el nombre de cada capa →
  **Aplicar**.
- **Guarda:** `POST /api/plantilla/variantes` → escribe una **versión nueva** del archivo
  (`plantilla.v<N>.ai` + puntero `plantilla.ver`) y **rehace el registro**. El archivo del usuario
  queda intacto.
- **Por qué renombra el archivo y no traduce al vuelo:** habría que traducir en CADA punto que
  compara capas por nombre — incluido `molde_real._candidatos_mesa` — y olvidarse de uno deja al
  motor **sin piezas al generar**.

#### Modo **POR PIEZAS** (todas las piezas en UNA capa)
- **Pasos:** activar el modo → **seleccionar piezas en el visor** (clic, o arrastrar un recuadro) →
  escribir el nombre de la variante en texto libre (`S`, `38`, `Talle único`, `Niño 4`) → repetir →
  **Aplicar al molde** (botón en la barra **sticky** de arriba).
- **Guardado automático del borrador:** cada cambio dispara
  `POST /api/plantilla/variantes_piezas_borrador` con 500 ms de respiro. Estado a la vista:
  *Guardando… / ✓ Guardado automático / ⚠ No se pudo guardar*.
- **Aplicar** (lo caro): `POST /api/plantilla/variantes_piezas {pid, asignaciones}` →
  **parte el PDF** en una capa OCG real por variante (verificado **pixel-idéntico** al original) y
  **rehace el registro**. Queda en `variantes_piezas.json` con dos campos: `asignaciones`
  (borrador) y `aplicadas` (lo que efectivamente se partió) — distintos ⇒ hay trabajo pendiente.
- **Trampas:**
  - La vista de este modo lee el **archivo ORIGINAL** (`candidatas=1`) para que los índices de pieza
    no se muevan → **el estado del molde NO se lee de esa detección**: `talles_reales`, `resuelto` y
    `guia` vienen del registro. Si no, un molde ya terminado se ve como recién subido.
  - El botón **{Variante} de guía** queda deshabilitado mientras dura este modo (cambiarla recargaría
    el visor con otros índices y rompería la asignación en curso).
  - Se trabaja sobre **una** mesa+capa (la que concentra más piezas). Un molde repartido en varias
    mesas no está contemplado.

### 2.4 Talle (variante) de guía

- **Dónde:** ajuste **Moldería** → botón **«{Variante} de Guía · Actual: …»** → modal.
- **Para qué:** es el talle de referencia — donde se **nombra** cada pieza y desde donde se propaga.
- **Guarda:** `POST /api/productos/variante_guia`. Si la guía guardada ya no existe entre las
  reales, el `GET /api/plantilla/deteccion` **la corrige solo** (sólo si estaba puesta; con
  `variante_guia = null` el sistema elige y no se toca).

### 2.5 Agrupar piezas homólogas — «La misma pieza en cada talle»

El **camino principal** para que una pieza sea "la misma" en todos los talles. Un solo gesto:
**seleccionar las que son la misma pieza + escribir qué es**.

- **Dónde:** ajuste **Moldería**, panel de agrupado. Al abrir la pestaña se **precarga** lo ya hecho
  (`GET /api/plantilla/emparejado` en silencio) y el panel cerrado muestra
  «✓ N piezas ya agrupadas (guardado)».
- **Vista preferida — TODAS las variantes juntas:** el visor muestra las piezas de **todos** los
  talles en un lienzo (`GET /api/plantilla/deteccion_todas`, cacheado en disco: 3 s la 1ª vez,
  **17 ms** después). Cada pieza lleva su **variante** encima y el nombre del grupo debajo, con el
  **color del grupo** (mismo color = misma pieza en todos los talles).
- **Pasos:** seleccionar en el visor las piezas homólogas (clic o recuadro) → escribir el nombre →
  **Confirmar**. Repetir. El sistema valida **antes** de guardar:
  - **2 piezas del mismo talle** → rojo, **bloquea**;
  - **falta la del talle guía** → **bloquea** (el nombre se guarda ahí);
  - **faltan talles** → naranja, **no bloquea** (queda la propuesta automática).
- **Guarda:** `POST /api/plantilla/grupo_pieza {pid, nombre, guia_idx, piezas:{talle:idx}, renombrar_de?, eliminar?}`
  → nombre en el talle guía + confirmaciones a mano en `emparejado_talles.json → manual`, y
  **re-arma el registro** (`_guardar_y_repropagar`). Nombre repetido → **409** (no se renumera por atrás).
- **Panel de progreso:** «N de TOTAL agrupadas · M confirmadas», barra de dos capas, filtro
  **Pendientes / Listas / Todas**, buscador con >8 grupos, miniatura de cada pieza, renombrar desde
  la fila y **«Confirmar todo» global** (UN solo `POST /api/plantilla/emparejado` sin `talle`).
- **Trampas:**
  - Molde **`anidado`** (talles dibujados uno encima del otro) → la vista junta **no se muestra**
    (sería ilegible): cae al flujo de a un talle y lo dice en una línea.
  - Rótulos: por debajo de 24 px de separación la pieza queda como un **punto**; el nombre de la
    variante va **una vez por bloque**. Aviso «N sin rótulo · acercá el zoom».
  - `colorGrupo` devuelve `hsl(...)`: **no** pegarle sufijo de alfa (`${col}55` es inválido) — usar
    `colorGrupoA(nombre, a)` o `fillOpacity`.

### 2.6 Ajuste avanzado (reacomodar / corregir por índice)

Escondido detrás de **«Ajuste avanzado ▸»** — el usuario lo rechazó por difícil, pero funciona y
está verificado.

1. **REACOMODAR:** seleccionar piezas y **arrastrarlas** hasta dejar ese talle dispuesto como el
   guía. Es **virtual**: sólo alimenta los rasgos del emparejado, **no mueve nada** del archivo ni
   de la tizada.
2. **CORREGIR:** para una pieza ya nombrada, decir a mano «en este talle es la #N». Una corrección
   manual **no se pisa nunca** con lo automático.
- **Guarda:** `GET/POST /api/plantilla/emparejado` → `emparejado_talles.json`
  `{"acomodo":{talle:{idx:[dx_mm,dy_mm]}}, "manual":{talle:{nombre:idx}}}` (offsets en **mm**).
- **Trampa:** guardar no alcanza — el emparejado se resuelve **al construir el registro**, por eso
  el POST guarda **y re-arma** el registro. Y las correcciones se guardan por `(talle, idx)`: si el
  molde se vuelve a **partir** por piezas, conviene rehacer el ajuste.

### 2.7 Acomodar piezas (posición en el visor)

- **Dónde:** ajuste **Moldería** → botón **Acomodar piezas** (queda en verde «Guardando pos.»).
- **Pasos:** arrastrar piezas en el visor. La posición **se guarda sola**.
- **Ojo:** en la vista de agrupar (`empVista === 'simple'`) el arrastre está **apagado** a propósito:
  ahí el gesto es sólo seleccionar.

---

## 3. Los 10 ajustes de la moldería (menú «Ajustes de la moldería»)

> Se entra desde Configuración → **Moldería** → clic en la tarjeta del molde. El menú lateral tiene
> un botón por herramienta; **⬅ Volver a ajustes** vuelve al menú.
> En **modo «mi molde»** (venido del pedido) se recorta **Variables** y «⬅ Molderías» se convierte
> en **«← Volver al pedido»**.

### 2.3 **Agregar una pieza** al molde ya cargado

- **Dónde:** dentro del molde → ajuste **Moldería** → bloque **«Agregar una pieza»**.
- **Dos caminos:** **⧉ Duplicar la elegida** (tocás la pieza en el visor) o **Subir un archivo**
  (`.ai`/`.pdf`, que tiene que traer la pieza **dibujada en todos los talles**, una forma por talle,
  del más chico al más grande — si no, se rechaza y te dice por qué).
- **Pasos:** elegir el camino → **tocar en el visor dónde va** (se ve la cruz y el contorno en
  tamaño real) → **«Listo, prepararla»** → repetir si querés más → **«Guardar»**.
- 🔴 **Nada se escribe hasta que tocás Guardar.** Las preparadas se ven en **ámbar** en el visor y
  se sacan con la ✕: hasta ahí el molde está intacto. Todas se guardan **juntas**.
- 🔴 **Lo guardado no se puede borrar.** Para sacar una pieza hay que **borrar el molde entero** y
  subirlo de nuevo. No hay «deshacer» (el modal te lo avisa antes de guardar).
- **Duplicar copia los vectores respetando los talles**: en cada talle se copia **esa misma pieza**
  (la homóloga del registro), no la que tenga el mismo número. El **nombre y el número NO se
  copian**: entra como pieza nueva. ⚠️ Si la pieza que duplicás **todavía no tiene nombre**, no hay
  correspondencia entre talles y se copia la del mismo número — conviene nombrarla antes.
- **Después de guardar:** la pieza queda **sin nombre** → nombrala en **Moldería · Nombrar piezas**,
  sumala al **grupo** y a las **variables** que la lleven, y dale **tela** y **arte** si el molde
  los usa (si no, la traba del pedido lo frena antes de fabricar).
- **La numeración no se mueve:** la pieza nueva es **la última** de cada talle.
- **Guarda:** `POST /api/plantilla/pieza_archivo` (sube el archivo, no toca el molde) y
  `POST /api/plantilla/pieza_agregar` (**es el Guardar**) → `entrada/<pid>/plantilla.v<N>.ai` +
  `plantilla.ver`; tu archivo original **no se toca**. Contrato: `verificar_agregar_pieza.py`.

### 3.1 Variables · Paso 1 — **Nombrar las piezas**

- **Para qué:** decirle al sistema cuál es el frente, la espalda, la manga. Es la base de TODO
  (mapeo del arte, telas, etiqueta, variables).
- **Pasos:**
  1. Seleccionar piezas en el visor: **clic** una, o **arrastrar un recuadro** desde un espacio
     vacío para varias.
  2. Escribir el nombre (`nombre-pieza-input`) — ej. «Frente».
  3. **Nombrar N piezas** (`nombre-pieza-ok`). Si se eligieron varias, se numeran solas
     (Frente 1, Frente 2…).
  4. Repetir hasta que no quede ninguna sin nombre (el contador dice «Nombradas X de Y»).
  5. **Guardar nombres** (`nombres-guardar`).
- **Extras:** **«Nombres puestos (N) — ver / editar»** abre el listado; entrar a un nombre activa el
  modo edición (tocar piezas las **suma o quita** de ese nombre) y se cierra con **Listo**.
- **Guarda:** `POST /api/plantilla/etiquetas` → **re-arma el registro** del molde.
- **Trampas:**
  - ⚠️ Ese endpoint re-arma el registro entero del molde activo: mandar **`pid`** siempre.
  - **La pantalla manda sólo las piezas del talle que se está mirando.** Desde 2026-07-28 el server
    lo traduce al talle GUÍA y **mergea** sobre lo que ya estaba nombrado (`_puente_idx` /
    `_asign_a_guia` / `_merge_asignaciones` en `servidor.py`): «no vino en el payload» significa **«no
    lo tocaste»**, no «borralo». Antes, nombrar desde un talle donde una pieza no aparecía la borraba
    del registro. **Quitar** un nombre sigue funcionando porque el front manda el idx **en blanco**;
    si algún día se cambia eso, se rompe la única forma de borrar.
  - Nombrar ya **no renumera** lo que escribiste: sólo se desambiguan los nombres repetidos, y con el
    primer número libre. Ver `bug-renumerado-nombres-piezas` en las memorias.
  - Contrato ejecutable: **`py verificar_piezas.py`** (raíz) — correrlo al tocar estas funciones.

### 3.2 Variables · Paso 2 — **Grupos y variables**

- **Modelo mental:** un **GRUPO** es la *pregunta* («Tipo de manga»); las **VARIABLES** de adentro
  son las *respuestas* («Manga corta», «Musculosa»). Una variable = **qué piezas** forman la prenda.
  **Las variables se arman A MANO** (la generación automática se eliminó el 2026-07-06).
- **Pasos:**
  1. Crear el grupo y ponerle nombre (`grupo-nombre`).
  2. **Elegir piezas del grupo** → tocar piezas en el visor → **Listo**. (Una pieza puede estar en
     varios grupos.)
  3. **Nueva variable:** escribir el nombre (`var-nombre`) → **+ Elegir piezas**
     (`var-elegir-piezas`) → tocar en el visor TODAS las piezas que lleva esa variable →
     **Listo** (`var-listo`).
  4. Repetir con las demás respuestas del grupo.
- **Detalle de una variable** (tocar su tarjeta): renombrar, **Cargar piezas**,
  **Guardar cambios**, y ver sus piezas **con todos los talles nesteados** (arrastrar una pieza
  acomoda las de todos los talles juntas; se guarda sola).
- **⛓ Piezas que van juntas (se declaran en el GRUPO):** detalle del grupo → **＋ Vincular piezas**
  → tocar 2 o más piezas que van SIEMPRE juntas (ej. manga corta + su vivo) → elegir el nombre
  común → **Crear vínculo**. Después, al armar cualquier variable de ese grupo, **elegir una trae
  la otra sola**. Si un toggle saca un miembro, se sacan **todos**.
- **Un nombre = un lugar:** si elegís «Cuello 9» y después «Cuello 10», queda **el último** (el
  anterior se saca solo, sin avisos). La única forma de que dos piezas del mismo nombre **convivan**
  es **vincularlas** en el grupo. Con el **recuadro** entra una por nombre y no se pisa lo que ya
  habías elegido. Si un molde viejo ya tenía dos, el detalle de la variable te lo **avisa**.
- **Guarda:** `POST /api/productos/variantes` (+ `/grupos`) → `prod["variantes"]` /
  `prod["grupos"]` en el catálogo. `juntas` viaja a la prenda como `juntas_piezas` y se filtra en
  `partes_de`.
- **Trampa:** una variable **sin piezas** no aparece en el pedido (la grilla filtra por
  `valores[].pieza_idx != null`).

### 3.3 Variables · Paso 3 — **Modelos**

- **Qué es:** un **modelo** agrupa varias **variables** bajo un nombre.
- **Pasos:** crear el modelo → ponerle nombre → tocar las variables que lo forman (quedan con ✓);
  el 👁 la muestra en el visor.
- **Guarda:** `POST /api/productos/modelos` → `prod["modelos"] = [{id, nombre, variantes:[clave…]}]`.

### 3.4 **Plantilla** (medidas del diseño + mapeo del arte)

Dos modos en la misma pantalla; se alterna con **«Mapear diseño al molde» ↔ «Ver medidas de las piezas»**.

**A) Medidas (cómo se escala el diseño sobre la pieza)**
1. **Dimensión de referencia:** *Alto manda* (default) o *Ancho manda*. El sistema calcula la otra
   para que **cubra todos los talles** sin huecos.
2. **Cómo se adapta el diseño:**
   - **Default** — un solo diseño cubre todos los talles (mesa **sin** `#`).
   - **Por rango** — elegir el rango (clic / **shift+clic**) y la **guía del rango**. En el arte, la
     mesa se llama `#XS-L Pieza`.
   - **Talle por talle** — un diseño por talle: mesa `#XS Pieza`.
3. **Descargar guía .ai** — el PDF/AI con las cajas de medida (sólo la variable en curso si hay una
   elegida). `GET /api/plantilla/pdf_guia`. Abre el **«Guardar como»** para elegir dónde dejarlo
   (como toda descarga de la app, ver `src/descargar.js`); cancelar no descarga.
- **Guarda:** `POST /api/productos/referencia_medida` y la config de medida por variante.
  Precedencia en el motor: **exacto > rango > default**; si algo no queda cubierto, avisa.

**B) Mapeo del arte al molde**
1. **«Qué va en cada capa del .ai»** (`diseno-capas`) — abre la guía con los nombres de capa que
   tiene que traer el arte (capas del sistema + las de personalización que salen de las **Reglas**).
   Cada nombre se copia con un clic.
2. **Mapear diseño al molde** (`diseno-mapear`) → el visor pasa a modo arte.
3. Emparejar cada **mesa** del arte con su **pieza**. Si en el `.ai` cada mesa tiene escrito el
   nombre de la pieza (capa «guías»), **el sistema lo hace solo**.
4. **Guardar Mapeo de Arte** (`diseno-guardar`).
- **Guarda:** `POST /api/arte/mapeo` → `mapeo_arte.json` `{mapeo, por_variable:{v_xxx:{pieza:mesa}}}`
  + `prod["mapeo_arte"]` (fijo, semilla) + corre `validar_arte_separado` + **pre-warm** del preview.
- ⛔ **REGLA DURA:** el mapeo se maneja **POR VARIABLE**. El de la variable es **autoritativo**
  (quitar un diseño en una variable **no** se resucita desde la base); la base queda para datos
  viejos y como semilla.
- **Trampa de los VIVOS:** «Vivo espalda/frente/…» no tienen mesa propia → son **huérfanos** y se
  mapean **a mano**. **No hay auto-herencia** (decisión del usuario). Sin mapear salen **blancos**
  en Arte **y** en la tizada — consistente, no es un bug.

### 3.5 **Planilla** del molde

- **Para qué:** qué columnas se cargan cuando se pide **este** molde.
- **Pasos:** elegir la planilla de columnas (`mplanilla-elegir`) → (opcional) probar la vista →
  **Guardar configuración de este molde** (`mplanilla-guardar`).
- **Guarda:** `POST /api/productos/asignar_planilla` + `POST /api/productos/config_columnas`
  (`mapeo_columnas`: qué columnas usa realmente este molde).
- **Efecto:** en el pedido aparecen **sólo** las columnas que algún molde elegido usa. El match es
  **por `c.id`**, nunca por `c.role` (hay roles compartidos: «Talle» y «Talle short» son ambos
  `role: 'talle'`).
- **Trampa:** un molde **sin** `columnas` cae al fallback `nombre/numero/talle` en
  `_traducir_prendas`. Si el código asume columnas, rompe esos moldes.

### 3.4.b **Que una pieza NO lleve etiqueta**

- **Dónde:** Moldería → un molde → **Etiqueta**. Es la misma pantalla a la que entra el cliente
  desde el pedido con **«Ubicar etiqueta»**, así que sirve igual para los moldes con el diseño
  adentro.
- **Regla:** **todas las piezas llevan etiqueta.** Si alguna no tiene que llevarla (un vivo, una
  tira), se apaga. Dos formas, la que te quede cómoda:
  1. **En el visor** (`etq-apagar-modo`): tocá **«🚫 Elegir piezas SIN etiqueta»** y después tocá
     las piezas en el dibujo. Quedan **marcadas a rayas**. Tocalas de nuevo para que vuelvan a
     llevar. Al terminar, **«✓ Listo»** para volver a ubicar la etiqueta.
  2. **En la lista**, columna **¿LLEVA ETIQUETA?**: tocá **LLEVA** en su fila y queda en
     **SIN ETIQUETA**.
- **Guardar:** con el botón **«Guardar etiqueta»** de siempre.
- **Efecto:** esa pieza no lleva etiqueta en **ningún talle**, ni en el visor ni en la tizada. Se
  guarda por **nombre genérico**: apagar «Cuello» apaga todos los cuellos.
- **Se ve de un vistazo:** al lado del rótulo «Piezas» aparece «N sin etiqueta» en ámbar.
- **Guarda:** `etiqueta.piezas_off` del molde (`POST /api/productos/etiqueta`).
- ⚠️ En **Configuración → Molde con diseño** NO se elige: esa pantalla vale para todos los moldes
  con diseño y no sabe qué piezas tiene cada uno. Se elige molde por molde, acá.

### 3.5.b **Quién está editando qué** (aparece solo)

- **Qué es:** al abrir un molde en Configuración, una regla de nesting o una planilla, esa cosa
  queda **tomada a tu nombre**. Si otra persona la tiene abierta, ves un cartel ámbar
  («Fulano está editando esto ahora mismo», ancla `reserva-aviso`) y el botón de **guardar queda
  apagado**. Podés mirar todo igual.
- **Se libera sola** apenas la otra persona cierra la pantalla; y si se le colgó el navegador, a los
  90 segundos. **No hay que pedirle a nadie que la suelte.**
- **Nunca te deja sin trabajar:** si el servidor no contesta, o el sistema anda sin usuarios, no
  bloquea nada. Es una cortesía para no pisarse, no un permiso.
- **Guarda:** `POST /api/reserva/tomar` · `/soltar` · `GET /api/reservas`; se renueva con el
  latido que la pantalla ya hace.

### 3.6 **Nesting** del molde

- **Pasos:** elegir el preset en el desplegable (`nsel-elegir`). Abajo se ve el resumen
  (separación · margen · giro).
- **Guarda:** `POST /api/productos/nesting_preset`.
- **Grupo de tizada** (sólo lectura acá): dice con qué otros moldes comparte mesa. Se arma en
  **Configuración → Reglas de Nesting → Grupos** (`nsel-grupos`).

### 3.7 **Telas asignadas**

- **Para qué:** qué telas del registro global quedan disponibles **para este molde**, y cuál va en
  cada pieza.
- **Pasos:**
  1. Elegir la **variable** con la que trabajar (`telas-variable`) — el visor muestra sólo sus
     piezas (~9, no las ~135 del molde).
  2. **Tope de telas** (`telas-tope`): cuántas telas distintas puede combinar la prenda en un
     pedido (ej. 2). «Sin límite» disponible.
  3. **Mostrar telas asignadas** (`telas-mostrar`).
  4. Tocar en el visor las piezas que van a llevar la tela. **Si no se toca ninguna, la tela va a
     TODAS.**
  5. **Seleccionar tela** (`telas-seleccionar`) → buscar por nombre (`telas-modal-buscar`) → tocar
     las que se habilitan → **Asignar** (`telas-modal-asignar`).
- **Guarda:** `POST /api/productos/telas_asignadas` → `{todas:[ids], por_pieza:{pieza:[ids]}}`.
- **Default:** las piezas de `PIEZAS_RIB` (`Cuello`, `TC`, `Tapacostura`) van a **RIB**.

### 3.8 **Borde de corte**

- **Pasos:** prender el toggle (`borde-activo`) → grosor en **mm** (`borde-tamano`) → color CMYK
  (`borde-color`) → **Guardar borde** (`borde-guardar`).
- **Guarda:** `GET/POST /api/productos/borde_corte` → `prod["borde_corte"] = {activo, ancho_mm, color:[c,m,y,k]}`.
- **Ojo:** el color se muestra convertido por el **perfil ICC** real (`cmykHex` ↔
  `POST /api/color/convertir`), igual que Illustrator.

### 3.9 **Etiqueta** (el textito de corte sobre cada pieza)

- **Lo que dice**: `talle · nombre · #nro`, y el **nombre va GENERAL, sin el número** («Frente 9»
  se estampa «Frente») — las piezas iguales se distinguen por el `#nro`. Contrato:
  `verificar_etiqueta_nombre.py`.
- **Se trabaja POR PIEZA** (2026-08-18). La etiqueta **es de la pieza** y vale para todo el molde:
  donde la pongas en el «Frente 1», queda en el «Frente 1» de **todos los talles y todas las
  variables**. ⛔ **«Frente 1» y «Frente 2» son piezas DISTINTAS:** cada una lleva su etiqueta y
  mover una **no mueve** las otras. La lista agrupa por nombre y muestra **`n/m`** cuántas de las
  piezas de ese nombre ya tienen su lugar marcado.
- **Pasos:**
  1. **Elegir la pieza** en la lista de la derecha (`etq-piezas`): una entrada por pieza
     («Frente», «Cuello»…, ~9 — no una por talle). Cada fila muestra cuántos talles tiene, un
     **✓** si ya tiene su lugar marcado, y un **sí/no** para apagarle la etiqueta a esa pieza.
     También se puede elegir desde la **barra de capas** de la izquierda: desplegá un talle (▸) y
     tocá el **tik** de la pieza (ver 6.2) — el tik lleno es la que estás ubicando.
  2. El **visor** pasa a mostrar **esa pieza en todos sus talles**, una al lado de la otra, y se
     **centra y encuadra solo** en ella (si son varias, el encuadre las abarca a todas). Al entrar,
     la primera pieza de la lista queda elegida sola.
  3. **Dónde:** tocar sobre el **borde** de cualquiera de ellas el punto donde va. La posición se
     guarda **relativa al contorno**, así que cae en el mismo lugar en todos los talles; el texto
     se **apoya y se inclina según el borde** (text-on-path).
  4. **Mostrar etiqueta** on/off general (`etq-activo`).
  5. **Qué muestra** (`etq-mostrar`): talle · nombre de pieza · número de prenda (+ separador).
  6. **Alineación** del texto (izquierda/centro/derecha) — de la pieza elegida; sin ninguna, el
     default global.
  7. **Tamaño (mm)**, **color**, y **borde del texto (halo)** con su color y su tamaño.
  8. **Guardar etiqueta** (`etq-guardar`).
- **Guarda:** `GET/POST /api/productos/etiqueta` → `prod["etiqueta"]`. La clave de cada posición es
  el **nombre genérico** de la pieza («Frente»), sin namespace.
- **Molde ANIDADO** (talles dibujados uno encima del otro): la pantalla **sí** muestra todos los
  talles (arranca con sólo el de guía visible y el resto apagado en la barra de capas; el 👁 general
  los prende). Lo que no se dibuja son los rótulos por bloque, que ahí caerían todos en el mismo
  punto. Se configura igual — la posición es relativa al contorno.
- ⚠️ **Lo que ya estaba configurado por variable se MIGRA solo** al abrir la pantalla (y se guarda
  al Guardar). Si una pieza tenía la etiqueta en **lugares distintos según la variable**, sólo
  puede quedar uno: queda el de la primera variable y la pantalla **avisa cuáles** para revisarlas.
- ⛔ **NO ROMPER la baseline** del text-on-path (ver `etiqueta-baseline-no-romper`; respaldo
  `respaldo29626.rar`).

### 3.10 **Editable** (tamaño de los objetos editables)

- **Qué configura:** por **capa** «Editable …» y por **rango de variantes**, el **tamaño máximo**
  del objeto (caja apaisada/vertical) o **«mantener medida del diseño»**. Es general del molde:
  sirve para cualquier diseño que traiga esa capa.
- **Pasos:** **Registrar capa** → escribir el nombre exacto de la capa (ej. `Editable escudo`) →
  agregar rangos (qué variantes cubre cada uno) y sus medidas → guardar.
- **Guarda:** `GET/POST /api/productos/editables_config` → `prod["editables_config"]`.
- **Precedencia:** capa **no registrada** → el objeto **escala con el diseño**. Lo que el operario
  ajuste en **Pedidos → Arte → Editar diseño** **manda** sobre esto.

### 3.11 **Nombres** (terminología del molde)

- **Pasos:** escribir cómo se llama el talle en este molde (`term-variante`: «Talle», «Medida»…) y
  cómo se llama la prenda (`term-molde`) → **Guardar Nombres** (`term-guardar`).
- **Guarda:** `POST /api/productos/terminologia` → `prod["terminologia"]`.
- **Alcance:** cambia **los carteles** de toda la app, no el funcionamiento.

---

## 4. Configuración general del sistema (Configuración → tarjetas)

### 4.1 Molderías (catálogo)
Grilla de todos los moldes con su estado (`Molde OK` / `Sin Molde`, `Diseño OK` / `Sin Diseño`).
Clic = abrir y **activar**. Lápiz = renombrar (`POST /api/productos/renombrar`); tacho = eliminar
(`POST /api/productos/eliminar`, `prod_default` no se puede borrar).
⛔ **Nunca borrar un molde con `creado_por`**: es del usuario aunque el nombre parezca de prueba.

> **Columnas «Botón de opciones»:** en la planilla del pedido **no son casillas** — sus opciones
> están siempre a la vista y se eligen con **UN clic** (con el teclado: Enter/Espacio pasa a la
> siguiente, o se escribe la primera letra). **Siempre hay una presionada**: sin elegir vale la
> **primera** de la lista, que es la que usa el motor — para cambiar el default, reordená las
> opciones. Supr no la vacía: la devuelve al default. El tipo y las opciones salen de la columna
> **o de su regla** (`_tipoCol`/`_opcionesCol` en el front, `_toggle_info` en el server).

### 4.2 **Planillas** (armar el juego de columnas)
- **Pasos:** **Nueva Planilla** (`col-nueva`) → nombre → agregar columnas y **ordenarlas
  arrastrando** → a cada columna asignarle una **Regla** (§4.3) → **Visualizar** para probar →
  **Guardar Planilla** (`col-guardar`).
- **Guarda:** `GET /api/plantillas_planillas` · `POST /api/plantillas_planillas/guardar` · `/eliminar`.
- Después se le asigna a cada molde desde su ajuste **Planilla** (§3.5).

### 4.3 **Reglas de planilla · Capas**
Define **campos reutilizables**: cómo se cargan y **qué hacen**.
- **Pasos:** **Nueva Regla** (`regla-nueva`) → nombre (`regla-nombre`) → **cómo se carga**
  (*Casilla* / *Desplegable* / *Botón de opciones*) → opciones si corresponde → **qué hace con ese
  dato** → **Guardar regla** (`regla-guardar`).
- **Comportamientos:**
  | valor | qué hace |
  |---|---|
  | `talle` | elige la **variante** del molde (las opciones salen solas del molde) |
  | `diseno` | elige cuál de los **diseños del pedido** lleva la fila (se llena solo) |
  | `nombre` | **se estampa como TEXTO** → necesita su **capa** en el diseño |
  | `numero` | **se estampa como NÚMERO** → necesita su **capa** en el diseño |
  | `manga` | **Toggle de pieza**: cambia QUÉ piezas entran. Pide una **palabra clave** (`manga`, `sisa`, `capucha`…) |
  | `none` | solo dato |
- **Panel «Capas que debe tener el archivo de diseño»:** lista las capas del sistema + una capa por
  cada campo que se estampa. Clic = copiar; **📋 Copiar todas las capas**. No es obligatorio: si el
  diseño no trae una capa, al subirlo el sistema **avisa** qué dato no se va a estampar.
- **Guarda:** `GET /api/reglas_planilla` · `POST /api/reglas_planilla/guardar` · `/eliminar`.

### 4.4 **Telas**
- Las telas **vienen del sistema de stock** (API externa) — acá **no se crean ni se borran**.
- **Pasos:** ver el chip de **conexión** (`telas-conexion`) → **↻ Actualizar telas del sistema**
  (`telas-actualizar`) → para cada tela, escribir el **ANCHO DE IMPRESIÓN (cm)**, que es el que usa
  la tizada (suele ser **menor** que la medida del rollo, por los orillos) → armar **grupos
  combinables** (tocar las telas que se pueden intercambiar) → **Guardar grupos**.
- **Guarda:** `GET /api/telas` · `POST /api/telas/refrescar` · `POST /api/telas/ancho` ·
  `POST /api/telas` (grupos) · `GET /api/telas/conexion`. La key vive en `config_externo.json`
  (gitignoreado) y **viaja con el paquete de publicación**, no se carga a mano.
- **Nota:** el **alto** de la hoja se configura en **Reglas de Nesting**, no acá.

### 4.5 **Reglas de Nesting** (+ grupos de tizada)
- **Preset:** **Nuevo Nesting** (`nesting-nuevo`) → nombre (`nesting-nombre`) → **separación entre
  piezas (mm)** (al menos 5) → **margen del borde de la tela (mm)** → **giro** (*no girar* / *90°* /
  *180°* / *libre*) → **Guardar nesting** (`nesting-guardar`).
  `GET /api/nesting_presets` · `POST /api/nesting_presets/guardar` · `/eliminar`.
  Menos separación = menos tela, pero menos aire para cortar.
- **Grupos de tizada:** pestaña **Grupos** → **Nuevo grupo** → nombre (ej. «Conjunto deportivo») →
  tocar los moldes que **comparten mesa** → guardar. `GET/POST /api/grupos_tizada*` +
  `POST /api/productos/grupo_tizada`. Un molde fuera de todo grupo se arma en su **propia tizada**.
- **Config global** (ancho/alto por defecto, etc.): `GET/POST /api/config`.

### 4.5b **Usuarios y permisos**
- **Dónde:** Configuración → *Usuarios y permisos*. Tres pestañas con **un buscador común**:
  **Usuarios**, **Roles** y **Acciones** (el catálogo que define el código).
- **El modelo, en una línea:** un usuario **no** tiene permisos sueltos → tiene **roles**, y cada rol
  trae un paquete de **acciones**. Todo se valida en el **servidor**.
- **Nuevo/editar usuario** (modal en 4 pasos): 1) quién es · 2) **contraseña** (puntos + **ojo** para
  verla; vacía = no se cambia) · 3) **roles** como tarjetas con su descripción y cuántas acciones
  traen · 4) **«con eso va a poder»**: el resumen real de lo habilitado, que se recalcula al marcar.
  Sin ningún rol, avisa que el usuario entra pero no hace nada. El interruptor **«Puede entrar»**
  desactiva el acceso sin borrar el historial.
- **Nuevo/editar rol:** datos + selector de acciones con **buscador**, contador `X de Y`,
  **Marcar todo / Ninguna** (sobre lo filtrado) y, por módulo, una **caja de tres estados** que marca
  o saca el bloque entero. El rol **de sistema** no se puede tocar (si le sacaran «gestionar
  usuarios», nadie podría devolvérselo).
- **Trampa:** para revisar esta pantalla sin credenciales está `scratchpad/srv_visor_usuarios.py`
  (8062, sólo lectura). El sandbox común (`srv_visor.py`) **no sirve**: sabotea `api_usuarios` y con
  eso desaparecen `/api/usuarios`, `/api/roles` y `/api/permisos`.

### 4.5c **Columna «Cantidad»** (una fila = varias prendas)
- **Qué hace:** repite la fila tantas veces como diga el número. `M · pepe · 12 · **5**` ⇒ la tizada
  arma **5 remeras M con «pepe» y «12»**. No se estampa: sólo multiplica.
- **Está en TODAS las planillas** (columna de sistema, `role: 'cantidad'`): no hay que crearla ni
  migrar nada, y **no se puede borrar**.
- **Cuándo se ve** — se configura en *Configuración → Planillas*, tocando la columna:
  · **«Sólo si el operario la pide»** (por defecto): en el paso Planilla hay un botón **Cantidad**
    que la muestra/oculta. · **«Siempre a la vista»**: la planilla la trae puesta.
  La **posición** se cambia arrastrando su letra, como cualquier columna.
- 🔴 **Oculta = no se aplica** (vale 1). El valor cargado no se borra: vuelve a valer al mostrarla.
- **Sin tope** (decisión del usuario): 250 son 250 prendas. Al lado de los botones se ve
  **«N fila(s) → M prendas»** cuando difieren — ése es el número que le importa al taller.
- **El botón** para prenderla está **arriba de la planilla** (grande, dice «Mostrar columna de
  cantidad»), no abajo con los otros.
- **Dónde vive:** `_con_cantidad` (servidor) garantiza la columna en las dos puntas y
  `_traducir_prendas` es quien **repite** la prenda. Contrato: `verificar_cantidad.py`.

### 4.5c-bis **Mover filas de lugar**
- Desde la **columna del número (#)**: se toca para elegir la fila (**shift** = un rango ·
  **ctrl/cmd** = de a una) y se **arrastra** para moverla. Se pueden mover **varias juntas**, y
  mantienen su orden.
- Mientras arrastrás, las filas **se corren solas** mostrando dónde va a caer el bloque.
- 🔴 **El número es la POSICIÓN, no la fila**: siempre queda 1, 2, 3… de arriba abajo, sin importar
  cuánto muevas.

### 4.5d **Cargar por lote** (cuántas de cada talle)
- **Botón «Cargar por lote»**, abajo de la planilla. Abre un modal con **todos los talles del
  molde**; se pone cuántas prendas lleva cada uno (− / número / +) y se crea **UNA FILA POR
  PRENDA**: `M = 5` ⇒ **5 filas de M**, cada una lista para su nombre y su número.
- 🔴 **No es lo mismo que la columna Cantidad**: esa hace *una fila = N prendas iguales*; el lote
  arma *N filas separadas* — que es lo que sirve cuando cada prenda lleva un nombre distinto.
- Si la planilla está **en blanco**, el lote la **reemplaza**; si ya tiene datos, **agrega al final**
  (el modal lo avisa antes de confirmar).

### 4.5e **Exportar / Importar la planilla (CSV para Excel)**
- **⬇ Exportar CSV** (al lado de Importar, abajo de la planilla) baja la planilla tal cual está:
  **sólo las columnas que se ven** — si la de Cantidad está oculta, no va en el archivo.
- El archivo se abre en **Excel** (separador `;` + BOM, así entra en columnas y con acentos), se
  completa afuera y se vuelve a subir con **⬆ Importar CSV**: los encabezados son los **labels** de
  las columnas, que es justo lo que el importador matchea.
- El importador **detecta solo el separador** (`,` `;` tab), así que si Excel lo guarda distinto
  entra igual. En talle/diseño/toggles sólo acepta valores válidos.

### 4.6 **Catálogo de Fuentes**
- **Pasos:** **Subir** (`fuentes-subir`) el `.ttf`/`.otf` → escribir un texto de prueba
  (`fuentes-probar`) para ver cómo queda **en todas las fuentes** sin generar una tizada.
- **Guarda:** `POST /api/fuente` → `catalogo_fuentes/`. Consultas: `GET /api/fuente/archivo/<n>`,
  `GET /api/fuente/glifos/<n>`, `DELETE /api/fuente/archivo/<n>`.
- **Por qué importa:** el nombre/número se estampa como **curvas vectoriales** (`FuenteCurvas`), no
  como fuente embebida. En el pedido, `GET /api/pedido/fuente_chars` avisa **qué caracteres NO
  tiene** la fuente elegida.

### 4.7 **Perfil de color (ICC)**
- Muestra los perfiles **instalados en la máquina**; el marcado es el default (por grupo).
- **Pasos:** tocar el perfil que se quiere por defecto (`perfil-card`).
- **Guarda:** `GET /api/perfiles` · `POST /api/perfiles/config`. Default:
  *U.S. Web Coated (SWOP) v2*.
- Al cargar un arte, el sistema **detecta el perfil incrustado** (`GET /api/arte/perfil`) y avisa;
  si hay perfiles distintos entre moldes, el pedido ofrece **unificar** (`perfil_forzado`).
- ⛔ **CMYK exacto**: nada de Ghostscript ni re-cuantizar (sublimación). Ver `aplanar_rip.py`.

### 4.8 **Usuarios y permisos**
- Usuarios, roles y permisos. `GET/POST/PUT/DELETE /api/usuarios`, `/api/roles`, `/api/permisos`;
  sesión: `POST /api/auth/login|logout|password`, `GET /api/auth/yo`.
- **Trampas conocidas:** `app.secret_key` es **aleatoria** si falta `TIZADA_SECRET` → **reiniciar el
  server invalida la sesión**; y `GET /api/productos` **oculta** los moldes con dueño a quien no
  está identificado. Por eso `App.jsx` re-pide el catálogo con `useEffect(…, [yo?.id])`.
- **Pendiente real:** hoy **ningún endpoint de configuración valida permisos** (ver
  `molde-propio-desde-pedido`, entrega 4).

### 4.9b **Molde con diseño** (la config de los moldes que traen el diseño adentro)

- **Dónde:** Configuración → tarjeta **«Molde con diseño»** (`cfg-con-diseno`).
- **Qué se deja acá:** el **borde de corte** (grosor, si va por fuera/centro/dentro, si se dibuja),
  la **etiqueta** (tamaño de letra, separador, si muestra talle / nombre / número) y la **regla de
  nesting**. Es lo que el cliente NO configura cuando sube su molde desde el pedido.
- 🔴 **Es VIVA: vale para todos esos moldes, también para los que ya están cargados.** Una tizada
  hecha antes del cambio y otra después salen distintas. La pantalla lo avisa y dice a cuántos
  moldes alcanza.
- **Lo que NO se toca acá:** *dónde* va la etiqueta en cada pieza — eso lo marca el cliente en su
  pedido (§5.2.b), y guardar acá no se lo pisa.
- **Guarda:** `POST /api/config_con_diseno` → `cat["config_con_diseno"]`. Pide `config.editar`.
- **Dónde se aplica:** un único lugar lo resuelve (`_borde_de` / `_etiqueta_de` en `servidor.py`),
  y por ahí pasan el preview del Arte, la ficha y las llamadas al motor. Si se agrega otro lugar
  que lea el borde o la etiqueta, **tiene que pasar por ahí**.

### 4.9c **Guardar / usar la configuración de un molde** (etiqueta + nombres, para reusar)

- **Dónde:** desde el PEDIDO, en el panel del visor (donde están los talles y las herramientas):
  botón **«Guardar configuración»** (`pieza-b-configuracion`), al lado de «Nombrar piezas» y
  «Ubicar etiqueta». También desde el molde abierto → ajuste **Moldería** → tarjeta
  **«Configuración»** → **«Guardar / usar»** (`molde-cfg-abrir`). Es para el molde que trae el
  diseño adentro, que se sube **para un pedido y se borra con él**: sin esto, el trabajo de
  configurarlo se perdía.
- **Para qué:** no volver a marcar a mano **dónde va la etiqueta en cada pieza** ni a **nombrar las
  piezas** cada vez que se sube el mismo molde.

**Los pasos, la primera vez (guardar):**
1. Configurá el molde como siempre: nombrá las piezas y marcá la etiqueta pieza por pieza.
2. Abrí **«Guardar / usar»**, escribí un nombre que lo identifique («Camiseta jugador · cuello
   redondo») y tocá **Guardar esta**.

**Los pasos, la próxima vez (usar):**
1. Subí el molde en el pedido nuevo. Si el sistema lo reconoce, en la tarjeta «Configuración»
   aparece el aviso **«Este molde ya lo configuraste como «X»»** con **Aplicar** y **Ahora no**.
2. Tocá **Aplicar** (o abrí la configuración y elegí de la lista: cada tarjeta dice si es del
   **mismo archivo**, del **mismo molde**, **parecida** o **distinta**, y la que calza va
   resaltada en verde con su «Aplicar» lleno).
3. 🔴 **Miralo en el visor.** Entra siempre el nombrado y la etiqueta; el informe dice cuántas
   piezas quedaron con su lugar marcado y **qué no entró**. Lo que no haya quedado bien se corrige
   a mano, como siempre.
4. Lo que es decisión **del pedido** —grupos y variables, telas, planilla, talle de guía,
   producción— entra **sólo si lo tildás** en el modal. Y **queda guardado con la configuración**:
   lo que dejes encendido al guardarla (o al tocar «Actualizar») vuelve así la próxima vez, y cada
   receta muestra en su tarjeta lo que se lleva. Desde el aviso se aplica **lo que la receta
   tiene**, sin depender de lo que haya tildado en pantalla.

**Corregir una que ya tenías:** hacé el cambio en el molde (un nombre, dónde va una etiqueta) y en
la lista tocá **«Actualizar»** sobre esa configuración: guarda cómo está el molde ahora **dentro de
la misma**, en vez de dejarte cuatro casi iguales. Pregunta antes, porque lo anterior se pierde.

**Trampas:**
- ⏳ **Si acabás de subir el molde, esperá.** El molde se lee en segundo plano (más de un
  minuto en uno grande) y hasta que termina no tiene piezas. Podés apretar **Aplicar**
  igual: queda anotado y **entra solo** en cuanto el molde está. El aviso celeste te dice
  cuál quedó esperando.
- 🔴 **Son tuyas.** Cada usuario ve, aplica y borra **las suyas**. La de un compañero no aparece.
- 🔴 **Se reconoce el MOLDE, no el archivo.** El mismo molde con **otro diseño adentro** es otro
  archivo y se reconoce igual (por las medidas de sus piezas: la «huella»). Si cambiaste el molde
  de verdad —otra pieza, otra medida— va a decir «parecida» o «distinta»: ahí revisá con más ganas.
- **Nunca se aplica sola.** Ni el aviso ni la lista tocan nada hasta que apretás **Aplicar**.
- **Borrar una configuración no toca ningún molde**: es sólo la receta.
- **Guarda:** `POST /api/molde/config/guardar` · **usa:** `GET /api/molde/config/lista` +
  `POST /api/molde/config/aplicar` · **borra:** `DELETE /api/molde/config/<id>`.
  Vive en `dbo.config_molde`. Contrato: `verificar_config_guardada.py`.

### 4.9 **Publicación**
- Manda las mejoras de **esta máquina** al servidor publicado en internet. Los moldes, artes y
  pedidos **no viajan**.
- **Pasos:** ver las versiones (local vs remoto) → escribir el **número de versión** (se propone el
  siguiente) → elegir **cuándo**: *ahora / en X (seg-min-horas-días) / fecha y hora exactas* → leer
  el resumen («Se instala el jueves 12/8 a las 03:00 — en 4 h 12 min») → **Publicar**.
  **Cancelar** anula una actualización programada.
- **Guarda / dispara:** `GET /api/publicacion/estado` · `POST /api/publicacion/publicar {cuando, version}` ·
  `POST /api/publicacion/cancelar`. Del lado publicado: `/api/actualizacion/{estado,subir,aplicar,cancelar}`.
  Si algo falla, **el servidor vuelve solo** a la versión anterior. Plan completo en `PLAN_PUBLICACION.md`.
- **REGLA:** no bumpear el archivo `VERSION` por cada cambio — el número lo escribe el usuario acá.

---

## 5. El PEDIDO — armar una tizada (uso de todos los días)

Wizard `pedidoPaso`: **diseno → moldes → arte → planilla → (generar) → resultados** (5 pasos en la barra: Diseño · Moldes · Arte · Planilla · Tizadas).

🔴 **La barra de abajo es LA MISMA en los 5 pasos** (componente `BarraPaso`), siempre en este orden: **← volver · ↺ Nuevo pedido · lo propio del paso** … **progreso · el botón que avanza**. Ningún paso arma su barra por su cuenta.

**El PROGRESO del paso** (`ProgresoPaso`), **centrado** en la barra: cada requisito con su **marca** y su nombre **completo** («✓ Asignar arte · ✓ Asignar tela · ! Cargar fuente 2/3»). Verde = hecho · rojo con cruz = falta y **frena** · **amarillo con «!» = falta pero deja avanzar** (`aviso: true` en `pasoItems`; hoy sólo la tipografía). **Se toca y abre el detalle de ESE paso**: qué falta, con nombre y apellido («Falta el arte de «camiseta asque» en «JUGADOR»»). Qué mira cada paso — **Diseño**: haber elegido uno · **Moldes**: la prenda de cada diseño · **Arte**: el arte de cada molde+diseño, la tela de cada pieza y las fuentes · **Planilla**: filas, valores válidos y arte de todos los moldes · **Tizadas**: la generación terminada.

### 5.0 Paso 1 «Diseño» — elegir el o los diseños

**Acá no se ve ningún molde**: sólo los diseños, para tocarlos.

- Arriba, **centrado**, el campo para **escribir** un diseño que no esté en la lista (vale sólo
  para ese trabajo) y el botón **+ Diseño**.
- Debajo, la **lista de siempre** (`pedido-diseno-lista`), **de a 3 por línea**: JUGADOR · GOLERO ·
  CUERPO TECNICO · DISEÑO 1-5 · ALTERNATIVA · PRINCIPAL · LOCAL · VISITANTE. Se tocan (podés elegir
  varios); se vuelven a tocar para sacarlos. ⏳ La lista vive **en el código** (`DISENOS_PRESET` en
  `App.jsx`) hasta que se puedan crear desde Configuración.
- Los elegidos quedan en **«Este trabajo lleva»**, con su ✕.
- **«Elegir los moldes»** (`pedido-ir-moldes`) pasa al paso 2 — apagado hasta que elijas uno.

### 5.1 Paso 2 «Moldes» — las variables de cada diseño

**No se elige un molde: se eligen variables, que ya traen su molde detrás.** Se muestran **todas**,
para cualquier diseño.

- **Pasos:**
  1. **← Diseño** (`pedido-volver-diseno`) vuelve al paso 1 si hay que agregar o sacar alguno.
  2. Los chips (`pedido-diseno-chips`) muestran cada diseño con su color y **cuántas variables** le
     asignaste; tocar uno = trabajar sobre ese (**Todos** aplica a todos a la vez).
  3. Pestañas (`pedido-tabs`): **Catálogo** (variables de los moldes compartidos) o **Mis
     artículos** (los moldes propios).
  4. Tocar las **variables** que van en ese diseño (`pedido-variables`). Cada diseño necesita al
     menos una.
  5. **Cargar el arte →** (`pedido-ir-arte`).
- **Bloqueos:** el botón se apaga si algún diseño quedó sin variable — el cartel al lado dice cuál.
  Una variable con **otra planilla** aparece deshabilitada: no se puede combinar.
- **↺ Nuevo pedido** reinicia todo.

### 5.2 Subir **mi propio molde** desde el pedido

- **Dónde:** pestaña **Mis artículos** → tarjeta **+** o botón **Subir mi propio molde**
  (`pedido-subir-molde`).
- **Pasos:** nombre + archivo (`.ai`/`.pdf`/`.dxf`) → se crea el artículo
  (`POST /api/productos/crear {nombre, propio:true}`) → se sube el molde
  (`POST /api/plantilla` con **`pid`**) → entra a la config.
- **Configurar** (⚙ en la tarjeta) abre la **misma** pantalla de Config → Moldería por deep-link,
  en modo `modoMiMolde`: sin **Variables**, con **«Indicar qué es cada pieza →»** (el mismo editor
  de nombrado) y con **«← Volver al pedido»**. **No hay pantallas nuevas de config.**
- **Un molde propio no tiene variables** → en el pedido se elige **entero** y el motor genera
  **todas** sus piezas.

### 5.2.b Subir un **molde que YA TRAE EL DISEÑO ADENTRO** (camino B)

La otra forma de cargar: archivos con el diseño estampado en cada pieza. No llevan arte aparte
ni mapeo.

- **Dónde:** al entrar al pedido, botón **«Cargar molde con diseño incluido»**
  (`pedido-armar-con-diseno`). El otro botón, **«Armar con base»**, es el flujo de siempre — y **no
  son excluyentes**: un pedido puede llevar de los dos.
- **En el espacio de carga:**
  1. Soltá **varios archivos** de una vez (`cargar-b-zona`). El **nombre del molde sale del
     archivo**: no hay que escribirlo.
  2. Tocá los moldes **que van juntos** y escribí **el nombre del diseño** una sola vez
     (`cargar-b-diseno`).
  3. Si la planilla tiene más de una columna de talle («Talle», «Talle short»), **en la tarjeta de
     cada molde** hay dos pastillas: tocá la columna de la que toma su talle (`cargar-b-columna`).
     Es un toque, no hay que tildar el molde ni abrir nada. Mientras no lo digas, la tarjeta lo
     marca en ámbar («¿QUÉ TALLE?»), la barra de abajo lo avisa y **«Al arte» queda apagado**.
     🔴 Sin esto un short tomaría el talle de la camiseta y saldría del tamaño equivocado.
     · Para poner varios de una: tildalos y usá la tira «El talle lo toman de».
     · El mismo control está en la tarjeta de **Mis artículos** (`molde-columna-talle`), para los
       moldes que ya están en un diseño del pedido.
     · Con **una sola** columna de talle no aparece nada de esto.
  4. **Al arte** (`cargar-b-siguiente`) lleva al paso Arte: el visor, los talles y las
     herramientas. 🔴 **NO entra solo a nombrar** (cambió 2026-09-09): a cada herramienta se
     entra con su botón, así no perdés de vista el resto.
- **También** se puede subir de a uno desde la pestaña **Mis artículos** → tarjeta **«Molde con el
  diseño adentro»** (`pedido-subir-con-diseno`).
- **Qué tiene que traer el archivo** (`.ai`/`.pdf`, sin DXF): una **capa por talle**, cada pieza
  dentro de su **máscara de recorte**, y —si la prenda lleva nombre y número— una capa **`nombre`**
  y otra **`00`** con los textos de muestra (pueden ser subcapas y estar dentro de la máscara).
  🔴 **Sin esas dos capas la tizada sale igual**, con el texto del diseño en todas las prendas.
- **Pasos:** nombre + archivo → se sube (con el % real y después el reloj mientras el servidor lo
  lee: un archivo de 100+ MB tarda un par de minutos) → el molde **queda elegido** en el diseño
  activo, **sin salir del pedido**.
- **Después, en el paso Arte**, el panel de la derecha tiene **tres botones y nada más**
  («Nombrar piezas», «Ubicar etiqueta», «Guardar configuración» — §4.9c) y, abajo, la lista de
  piezas con lo que le falta a cada una. Las dos tareas **también son pasos de la barra de abajo**:
  **«Nombrar piezas»** traba hasta que estén todas, y **«Ubicar etiqueta»** avisa en amarillo pero
  **no traba** (una pieza sin marcar sale con la etiqueta centrada abajo, no sin etiqueta).
  Qué hace cada una:
  1. **Piezas** — **el mismo gesto que en la moldería** (§3.1): tocá las piezas **en el visor** (se
     van sumando) o en la lista, escribí **un** nombre y tocá «Nombrar N». Si elegiste varias se
     numeran solas («Tira» → «Tira 1», «Tira 2»). El visor abre al instante y muestra **sólo
     contornos**. *(De ese gesto falta el arrastre de recuadro; el clic múltiple sí está.)*
     🔴 **El nombre es lo que hace funcionar todo lo demás**: la etiqueta, las telas (se asignan por
     nombre) y la manga corta/larga — el motor arma la prenda mirando los tokens del NOMBRE, así
     que una pieza llamada «Manga 1» hace que elegir corta o larga dé la misma tizada.
  2. **Etiqueta** — se destraba con todas nombradas: tocá el borde de la pieza donde quieras que
     salga impresa. Las que no toques salen abajo y centradas.
- **El molde es de ESE pedido y no queda guardado.** Se borra con **«Terminar pedido»** o
  «Nuevo pedido» (el aviso dice qué se pierde), y si quedó colgado lo junta el servidor solo.
  Las tizadas ya generadas **no se tocan**.
- **Lo que NO configura el cliente:** el borde de corte, el tamaño/tipografía de la etiqueta y el
  nesting. Eso lo deja el taller una vez en **Configuración → Molde con diseño** (§4.9b).

### 5.3 Paso «Arte» — cargar el diseño y mapearlo

Se navega **por variable** (cada tarjeta de arriba es una variable elegida, o un molde entero si es
propio); el ✓ verde marca las que ya tienen arte.

- **Pasos:**
  1. **Cargar arte** (`arte-cargar`) — `.ai` o `.pdf` **de esta variable**.
  2. Al terminar la subida, el sistema **asigna el diseño a todas las variantes** en una sola
     espera visible (con barra de progreso) → después navegar entre talles es instantáneo.
  3. Revisar en el visor que **cada pieza tenga su parte del diseño**. Si algo no quedó bien,
     **arrastrar el diseño hasta la pieza**. Arriba se cambia de diseño y de variable: **hay que
     cargar el arte de todas**.
  4. **Asignar telas** (`arte-telas`) → en qué tela va cada pieza. **Todas necesitan tela**: si
     falta alguna, no deja seguir.
     - **Lo normal: una sola tela.** La card **«La tela de esta prenda»** → se toca, se elige del
       selector (grilla con la muestra de color y el ancho útil) y queda en **todas** las piezas.
     - **Si alguna va en otra:** **«+ Otra tela para algunas piezas»** → **tocás esas piezas en el
       visor** y después **«Elegir tela»**. Quedan listadas como *excepciones*, con su color y una
       ✕ para devolverlas a la tela principal.
     - **No repetir el trabajo:** **«⧉ Copiar estas telas a…»** copia lo elegido a los otros moldes
       del pedido — *Todos los moldes* de un toque, o marcando cuáles. Avisa si el destino ya tenía
       telas (se pisan). Las piezas que allá se llamen distinto quedan sin tela y te lo marca.
  5. **Tipografía** (`arte-fuente`) → si el arte pide una que el sistema no tiene, sale un cartel
     **AMARILLO** arriba: *«Tipografía no encontrada: X. Se va a sublimar con «Anton Regular»…»*.
     🔸 **Es el único requisito del paso que NO traba** (2026-08-21): se puede avanzar igual.
     Al tocar **A la planilla** aparece el cartel con tres salidas: *Cancelar*, **«Seguir de todos
     modos»** y *«Cargar la tipografía»* (el modal de siempre: subirla al sistema o sólo a este
     pedido, o elegir un reemplazo del catálogo). El cartel de arriba **desaparece solo** cuando la
     tipografía queda resuelta, y el visor se re-dibuja **al instante** con la elegida.
  6. **A la planilla →** (`arte-siguiente`).
- **Guarda:** `POST /api/arte` (multipart `archivo` + `diseno` + `pid`) →
  `entrada/<pid>/disenos/<slug>/arte.ai` + `validacion_arte.json` + `mapeo_arte.json` +
  `registro_personalizacion.json`. Si el auto-mapeo cubre el alcance de las variables, **se aprueba
  solo**; si no, pide completar y dice qué falta. Un diseño no-principal además se registra con
  `POST /api/disenos/guardar` para que aparezca en la columna «Diseño».
  Después: `POST /api/arte/asignar_todo` (+ `GET /api/arte/asignar_estado`) y
  `POST /api/arte/preview_piezas` (render real cacheado en `piezas_cache/`).
- **Contador y bloqueos:** el progreso del paso y su detalle. Código de colores: **✓ verde** hecho ·
  **✕ rojo** falta y **frena** (arte, telas) · **! amarillo** falta pero **deja avanzar** (hoy, sólo
  la tipografía). El texto de arriba de la barra cambia según haya rojo o sólo amarillo.
- **Todo lo que falta se nombra igual** (`_arteLbl`): **«MOLDE» · variable «VARIABLE» · diseño
  «DISEÑO»** — los tres, siempre (la misma variable la usan muchos diseños; lo que distingue es el
  diseño). Si el ítem es un molde entero (sin Variables) se omite la parte de variable.
  Vale para el arte, las telas y la tipografía: en la barrita, en
  el detalle, en el `title` de **Enviar** y en el error de generar. Las tipografías se chequean en
  **todos** los artes del pedido, no sólo en el que estás mirando.
- **LEY: el arte se ve igual que la tizada.** Lo que muestra el visor **es** el render del motor
  cacheado — no se re-dibuja en JS (el re-dibujo quedó sólo como placeholder mientras carga).

### 5.4 **Editar diseño** (objetos editables) — botón magenta en el paso Arte

Sirve para **mover, rotar, escalar, espejar y recolorear** lo que el arte trae en capas
`Editable …`, y para **agregar objetos propios**.

- ⛔ **LA CAPA ES EL OBJETO:** todo lo que la capa «Editable …» tenga adentro se mueve/rota/escala
  **junto**. El **color sí** es de cada figura por separado. (El agrupado de Illustrator **no viaja**
  en el `.ai`.) Si se quieren dos objetos independientes → **dos capas** «Editable …».
- **Pasos (mover/escalar):**
  1. Elegir el objeto en la barra lateral.
  2. Elegir el **alcance**: por defecto **todo el rango** de talles que muestran el mismo diseño;
     con **«Solo este talle»** el cambio va únicamente al talle en vista.
  3. Arrastrar en el lienzo / usar los handles (rotar, escalar; con el enlace apagado, ancho y alto
     libres; `sx`/`sy` negativos = **espejo**).
  4. **Guardar**. También hay **↶ Deshacer / ↷ Rehacer**.
- **Color:** con **un** objeto seleccionado, la columna **COLOR** muestra los chips de sus figuras
  (`o.partes`) → elegir la figura → swatch/presets/campos **C M Y K (0–100)** → **↺ Volver al color
  original**.
  - Sólo se puede recolorear lo que pinta con **relleno/trazo directo**. Si el objeto pinta vía
    **XObject/imagen** el control aparece **deshabilitado** con su nota.
- **Agregar un objeto propio:** subir PNG/SVG/PDF/AI → queda en una **sala de espera** → **Colocar**
  (se elige la pieza clickeando el diseño) → desde ahí es un editable más. También:
  **Quitar de pieza**, **Duplicar** (la copia nace sin pieza) y **quitar del arte**.
- **Guarda:**
  - transform: `POST /api/productos/editables` (`set_editable`) →
    `prod["editables"][diseno][variable][capa]["transforms"][talle]` — `dx/dy` en **fracciones** del
    diseño, `rot` horario.
  - color: `POST /api/productos/editable_color` → `…[capa]["objetos"][obj_id]["color"]`
    (`null` = limpiar).
  - agregados: `POST /api/productos/objeto_agregar`, `…/objeto_agregado/<oid>/{colocar,pieza,transform,duplicar}`,
    `DELETE …/<oid>`, y `POST /api/productos/editable_quitar` para sacar la capa del arte.
- **Versiones del arte:** colocar un objeto **NO sobrescribe** el archivo del usuario: escribe
  `arte.v<N>.ai` + puntero `arte.ver`. (a) el original queda de respaldo; (b) en Windows `os.replace`
  falla con **WinError 5** si algún proceso tiene el archivo abierto. Todas las mesas se inyectan en
  **una sola pasada** = una sola versión. Sólo se pueden **quitar** las capas que agregó el usuario
  (se compara la versión vigente contra el original).
- **Trampas:**
  - `_mid` undefined → guarda en el **molde activo equivocado** (hay fallback a `productosCat.activo`).
  - El editor dibuja con el **SVG del arte crudo**: un override de color **no se ve** ahí aunque la
    tizada sí lo aplique (por eso se regenera el svg y se anula el `thumb`).
  - El color **no** está en `_pvKeyCon` → `guardarColorEditable` invalida `_pvCache` a mano.

### 5.5 Paso «Planilla» — cargar las prendas

Funciona **como una planilla de Excel** (`planilla-tabla`).

- **Pasos:**
  1. Una **fila = una prenda**. Un clic elige la celda; **doble clic** (o **Enter**) la abre para
     escribir; también se puede **empezar a escribir directo**.
  2. **Fill handle**: con el cuadradito de la esquina se copia hacia abajo o al costado arrastrando.
     En números hace **secuencia** (1, 2, 3…); en talle y diseño **copia** el mismo valor.
  3. Columnas con opciones = desplegables **escribibles** (`ComboCell`).
  4. **Variable por fila**: la celda de variable abre un picker con **preview de las piezas** de
     cada variable → define **qué piezas se generan** en esa fila.
  5. **Diseño por fila**: la columna «Diseño» elige cuál de los diseños del pedido lleva la fila.
     Sólo ofrece los diseños que **existen en el talle de esa fila**: si un diseño no tiene ese
     talle en ninguno de los moldes del pedido, no aparece en la lista de esa fila (las demás filas
     lo siguen ofreciendo). Si la fila todavía no tiene talle, se ofrecen todos.
  6. **Agregar** N filas (`planilla-agregar`) o **⬆ Importar CSV** (`planilla-csv`).
  7. **Enviar →** (`planilla-enviar`).
- **Con VARIOS moldes en el pedido:** la columna «Talle» ofrece la **unión** de los talles de
  todos los moldes cargados, sin repetidos y respetando el orden de cada molde (antes mostraba los
  de uno solo y no se podía cargar una prenda del otro). Cada molde publica sus talles en
  `GET /api/productos` (campo `talles`); el front los une en `tallesDelPedido`.
- **Con DOS columnas de talle** («Talle» y «Talle short»): cada columna ofrece **sólo los talles de
  los moldes que la leen** — la del short no ofrece los de la camiseta. De qué columna toma el
  talle cada molde se dice **en su tarjeta**, en el espacio de carga o en Mis artículos (§5.2.b).
  🔴 Si una columna trae un talle que **ningún** molde del pedido tiene ahí, el pedido **no se
  fabrica**: el botón Enviar se apaga con el motivo, y si se pega a la API directo el servidor
  responde 409 diciendo qué columna mirar. (Que a UN molde le falte un talle que otro sí tiene no
  frena nada: es la regla de siempre.)
- **Importar CSV:** los valores que **no existan** en el molde quedan **vacíos** — no inventa nada.
  Hay un panel para omitir/corregir filas antes de importar.
- **Bloqueos del botón Enviar** (el cartel de al lado dice cuál):
  - no hay filas;
  - hay **valores inválidos** (fuera de las opciones) — dice en qué columnas;
  - falta el **arte** de algún molde del pedido.
- **Trampa grande:** el Arte edita `disenoActivo`, pero la tizada usa el diseño **de la columna de
  cada fila**. Si divergen —o la fila usa un diseño **sin arte**— hay **fallback silencioso** y la
  tizada no usa lo que mapeaste. Síntoma: «mapeé pero salió en otro / en un solo talle».

### 5.6 Enviar y resultados

- **Qué dispara:** `POST /api/generar_multi {molds, prendas, default_diseno, planilla, tela_base,
  asignaciones, perfil_forzado, editables}` (o `POST /api/generar` para uno solo).
  Progreso con `GET /api/trabajo/<tid>`.
- **Qué hace el motor** (resumen; detalle en `MAPA_DEL_SISTEMA.md` §6):
  1. por prenda → `piezas_de` (toggles + van-juntas ∩ piezas de la variable);
  2. por pieza → `_armar_base` (contorno + diseño vectorial recortado + borde + editables,
     **cacheada**) + estampado por prenda (nombre/número en curvas + etiqueta);
  3. las piezas se agrupan **por TELA**;
  4. `anidar_contorno` + `componer_pdf_contorno` → **una `HOJA_<tela>.pdf` por tela** + `prev_*.svg`
     + consumo/aprovechamiento. Salida en `trabajos/<tid>/`.
- **Pantalla de resultados:**
  - **Pestañas** por tela + pestaña **Ficha técnica** (PDF A4: la tabla de talles arriba y, abajo,
    **un molde guía POR CADA DISEÑO del pedido** — con su arte estampado, cada pieza nombrada y en
    qué tela va). Si un mismo diseño se pidió en **más de una variable**, sale una guía por cada
    una y el rótulo la nombra («Variable: Cuello V»). Se lee de arriba abajo: la fila N de la tabla
    dice su diseño, y ese diseño tiene su molde guía más abajo.
  - **Espacio infinito de mesas** (`MesasInfinito`): zoom con la rueda, **pan con clic derecho**,
    cada mesa se puede **renombrar** y se descarga con ese nombre.
  - **Descargar una mesa** (el botón de la mesa): abre el **«Guardar como»** del sistema con el
    nombre de la mesa ya puesto, y guarda donde elijas. **Cancelar no descarga nada.** Mismo
    comportamiento en la ficha técnica (completa o una hoja), la guía .ai y el CSV de la planilla.
    Vive en `src/descargar.js` (File System Access API; en Firefox/Safari/celular cae a la descarga
    de siempre). Contrato: `frontend/verificar_descarga_elegir_carpeta.mjs` (corre en el build).
  - **Descargar todo (N)**: pide **una carpeta** y guarda ahí **cada mesa por separado** (una
    página = un archivo), con su nombre. Sin la API del navegador, baja de a una como antes.
    También hay ZIP (`GET /api/trabajos/zip`). Cada archivo lleva el perfil ICC declarado
    (`OutputIntent`) y los valores CMYK intactos, se baje una, varias o todas.
  - **Aviso naranja**: «Algunas piezas salieron en blanco» — la tizada **sí** se generó; esas piezas
    no tienen diseño (van con su borde y etiqueta). Lista cuáles y por qué.
- **Aplanado para el RIP:** la hoja se aplana como Illustrator (0 XObjects anidados, 1 perfil ICC,
  PDF 1.6) **sin Ghostscript**, para preservar el CMYK exacto (`aplanar_rip.py`).

---

## 6. Herramientas transversales

### 6.1 El **visor del molde** (`visor-molde`)
Es el mismo componente en casi todas las pantallas; lo que **cambia es el modo**:

| Modo | Se activa en | Gesto |
|---|---|---|
| Nombrar piezas | Variables paso 1 | **clic = UNA pieza** (la de adelante, aunque haya otras debajo) · **arrastrar** = varias, apiladas incluidas · **recuadro** desde el fondo = varias |
| Elegir piezas de variable/grupo | Variables paso 2 | idem |
| Vincular «van juntas» | detalle del **GRUPO** | clic sobre 2+ piezas del grupo |
| Telas por pieza | ajuste Telas | clic = pieza lleva esa tela |
| Etiqueta | ajuste Etiqueta | clic **sobre el borde** = posición |
| Mapeo del arte | Plantilla / paso Arte | arrastrar mesa → pieza |
| Acomodar / reacomodar | Moldería | arrastrar piezas |
| Acomodar una VARIABLE | Variables → variable abierta | clic = elegir la pieza **entera** (todos sus talles) · **recuadro** = varias · arrastrar una **marcada** = se mueven **todas juntas** · arrastrar una suelta = sólo ésa |
| Asignar variantes por piezas | Moldería | clic / recuadro + nombre |

- **Navegación:** rueda = zoom, **clic derecho arrastrado** = mover. Botones **Ver todo** y **100%**.
- **Elegir piezas (2026-08-21):** un **clic** elige **una sola** — la de la capa de más arriba, sin
  importar cuántas haya debajo. Para elegir **varias**, **arrastrá** con el botón izquierdo (ahí sí
  se lleva todo lo que esté apilado bajo el cursor) o hacé un **recuadro** desde el fondo. El mismo
  gesto pone y saca. Mantener el clic **quieto** sobre una elegida (medio segundo) pasa a **mover**.
- **Escala real fija (mm)**: el visor **no** se reescala por cantidad de piezas — como Illustrator.

### 6.2 **La barra de capas** (columna izquierda del visor — estilo Illustrator)

Aparece en **Moldería → Nombrar piezas** y en **ajuste Etiqueta**. Es la lista de los talles del
molde, con el mismo lenguaje que el panel de capas de Illustrator:

| Control | Qué hace |
|---|---|
| **👁 general** (arriba de todo) | muestra u **oculta TODAS** las capas de una. Al ocultar, suelta la selección |
| **👁 de la fila** | muestra/oculta esa capa. **Se puede arrastrar**: apretar y pasar por encima aplica lo mismo a las que toque |
| **miniatura** | el contorno real de **la pieza** — el mismo dibujo del visor. La fila del **talle** no lleva (junta muchas piezas distintas): se ven al desplegar |
| **nombre** | **doble click = renombrar la capa**. En una fila de PIEZA, un click elige **esa pieza sola** (la de ese talle) |
| **tik** (cuadradito, **al principio de la fila**) | **lleno** = todo seleccionado · **medio** = una parte · **vacío** = nada. Click = seleccionar/quitar. En la fila de la capa, sus piezas de una; en la de una pieza, **sólo ésa** |
| **▸ / ▾** (**al final de la fila**) | despliega las piezas de esa capa (es grande a propósito: es lo que más se toca) |

- **El orden manda**: la capa de más arriba es la que va **más adelante** en el visor (y la que se
  lleva el clic cuando las piezas están encimadas). Ese orden sale del archivo `.ai`.
- En **Etiqueta** la selección es de a una: el tik **lleno** marca la pieza cuya etiqueta se está
  ubicando y las otras del mismo nombre quedan a medio marcar. El tik de la capa ahí sólo informa.
- **Adentro de una capa la selección es INDIVIDUAL**: tocar «Frente 1» en el talle 0 elige esa sola,
  no los frentes de los demás talles. Para elegir **la misma pieza en todos los talles** está la
  lista **«Ver piezas»** del panel de nombrar (funciona igual, con tik, pero por **nombre**); para
  **toda una capa**, su propio tik.

### 6.3 **Ayuda guiada** (botón `nav-ayuda`, «Te guío paso a paso»)

- **Hay dos cosas distintas y el menú las separa:**
  - **«Hacerlo paso a paso» → «Armar una tizada»** (22 pasos): el único tutorial de verdad, calcado
    del video `Como cargar un pedido.mp4` que grabó el usuario. Pide acciones y las verifica.
  - **«Para qué sirve cada cosa» → 21 recorridos** en 3 áreas (el molde y sus ajustes ·
    configuración del sistema · dentro del pedido): **sólo explican**, no piden hacer nada. Todos
    sus pasos son informativos (`accion: 'ver'`) y el chequeo del build lo exige.
- El menú ofrece además **retomar** lo que quedó a medias.
- Oscurece la pantalla, **ilumina el control exacto** y muestra un globo con la consigna. El paso
  avanza cuando la persona **hace la acción de verdad**; **Escape** sale.
- Si el usuario no está en la pantalla que el paso necesita, **no lo teletransporta**: le va marcando
  los botones hasta llegar (tabla `RUTAS` en `tutor.jsx`, se encadena sola).
- ⚠️ **El pedido es un wizard y el botón de VOLVER es de la pantalla, no del destino**: desde la
  Planilla se vuelve con **«← Arte»**, desde Resultados con **«← Atrás»**. Por eso las rutas del
  pedido son **función de dónde estás**. A **Resultados no se llega con ningún botón** (se llega
  generando): las guías que lo necesitan lo declaran con **`requiere(E)`** y **no arrancan** si no
  hay tizada — muestran un candado y el motivo. Sin eso, la ayuda sacaba a la persona de su pedido.
- 🔴 **Los tutoriales ya NO se escriben: los GRABA el usuario** (2026-08-27). Botón «Grabar un tutorial» en Ayuda → hace el trabajo → «Parar» → le pone un nombre. El sistema no graba video: anota **qué elemento tocó y en qué pantalla**, y los carteles los escribe él con `frontend/src/diccionario.js`. Se guardan en el catálogo (`tutoriales`) y son compartidos. Endpoints: `GET/POST /api/tutoriales` y `POST /api/tutoriales/borrar`.
- **NO toca datos del usuario**: la acción la hace siempre la persona.

**Cómo avanza un paso** — hay dos mecanismos y el orden importa:

| | Cuándo | Qué mira |
|---|---|---|
| **`hecho(E, E0)`** | si el paso lo declara, **es la única forma de avanzar** | el **estado real** de la app: `E` ahora, `E0` = foto al empezar el paso |
| DOM | el resto de los pasos | clic dentro del ancla, o el campo que **se vacía** al confirmar |

`hecho` arregla dos agujeros de fondo:
- **tocar un botón ≠ que la acción salga bien**: si el POST falla (ej. nombre repetido → **409**) el
  estado no cambia y el tutorial **no** avanza;
- los **gestos del visor** (elegir piezas, arrastrar) no se detectan por clic → antes esos pasos
  avanzaban **solos por tiempo**. Ahora son `accion: 'gesto'` y **no avanzan por tiempo**.

Si `hecho` ya da true al empezar el paso, **el paso se saltea** (no se pide lo ya hecho). Dos redes
de seguridad: «Seguir igual» si el ancla no aparece en 5 s, y «Ya está, seguir» si `hecho` no se
cumple en 15 s.

🔴 **Un control nuevo ⇒ su ancla Y su explicación.** El ancla es `data-tour="id"` en el JSX;
la explicación, una entrada con ese mismo id en `frontend/src/diccionario.js` (`nombre` · `que` =
para qué es · `como` = qué hay que hacer). Sin ancla el paso **no se puede grabar**; sin
explicación el cartel sale pobre.
**Lo verifica `frontend/verificar_diccionario.mjs`, que corre en cada `npm run build`**
(`npm run diccionario` para correrlo suelto) y **corta el build** si:
- algún `data-tour` de `App.jsx` no tiene entrada en el diccionario;
- sobra una entrada cuyo ancla ya no existe (texto muerto);
- una entrada está incompleta, o `explicar()` perdió su fallback.

**Cómo se dibuja el resaltado** (regla dura): el hueco deja ver el control **tal cual**; el resalte
(aro + resplandor) va **siempre por afuera**. Nada de sombras `inset`: se dibujan adentro del hueco y
**tapan el botón**. Y el globo **nunca** se pone encima del control: se mide y se ubica debajo →
arriba → al costado → o se achica al hueco (`frontend/src/tutor_pos.js`, verificado en el build con
8556 combinaciones de pantalla y posición).

**Trampas históricas (no reintroducir):**
- React limpia el `value` **por asignación directa, sin emitir evento** → detectar «campo
  confirmado» escuchando `input` **no funciona jamás**. Se resuelve con `valorDe(ancla)` +
  `vigilarVaciado()` que **mira el valor cada 150 ms**. Una prueba que fabrica el evento que la app
  no emite **no prueba nada**.
- El Enter **es del campo, no del tutorial**: con la ayuda abierta tiene que hacer exactamente lo
  mismo que sin ella. El tutorial se entera por el **efecto** (el campo se vacía).

### 6.4 Modales y avisos
- Nada de `alert`/`confirm` del navegador: la UI usa su componente **`Modal`** y sus propios avisos.
- **Los editores van en modal aparte**, nunca inline dentro de la lista.
- ⚠️ Un modal montado **dentro** de una pantalla no se abre desde otra: los modales globales
  (ej. `ColorPickerModal` / `picker`) van **una sola vez, al final del `return` de `App`**.

---

## 7. Checklist — «este molde ya produce»

```
[ ] La moldería existe y tiene nombre                         Config › Molderías
[ ] El molde está subido (badge «Molde OK»)                   ajuste Moldería
[ ] Cada TALLE tiene su capa nombrada (o el molde ya está     ajuste Moldería › NombrarVariantes
    partido por piezas y dice «Aplicado al molde ✓»)
[ ] Hay talle de GUÍA correcto                                ajuste Moldería
[ ] Cada PIEZA tiene nombre (contador «N de N»)               Variables › 1. Nombrar
[ ] Las piezas homólogas están agrupadas (sin naranjas)       ajuste Moldería › agrupar
[ ] Hay al menos UNA variable con piezas                      Variables › 2. Grupos
[ ] Telas asignadas (ninguna pieza sin tela)                  ajuste Telas
[ ] Planilla de columnas elegida                              ajuste Planilla
[ ] Nesting elegido (y grupo de tizada si comparte mesa)      ajuste Nesting
[ ] Borde / Etiqueta configurados si el molde los lleva       ajustes Borde y Etiqueta
[ ] Arte cargado y mapeo GUARDADO por cada variable           Pedido › Arte  (o Plantilla)
[ ] Prueba: una fila en la planilla → Enviar → hoja OK
```

---

## 8. Qué toca cada herramienta (referencia rápida)

| Herramienta | Endpoint principal | Archivo que queda |
|---|---|---|
| Crear/renombrar/borrar molde | `POST /api/productos/{crear,renombrar,eliminar,activar}` | `datos/productos_catalogo.json` |
| Subir molde | `POST /api/plantilla` | `entrada/<pid>/plantilla.ai`, `registro_producto.json`, `piezas.json`, `resumen_plantilla.json` |
| Nombrar variantes (capa) | `GET/POST /api/plantilla/variantes` | `plantilla.v<N>.ai` + `plantilla.ver` |
| Nombrar variantes (piezas) | `POST /api/plantilla/variantes_piezas[_borrador]` | `variantes_piezas.json` |
| Nombrar piezas | `POST /api/plantilla/etiquetas` | `registro_producto.json` (**lo reemplaza**) |
| Agrupar homólogas | `POST /api/plantilla/grupo_pieza` · `GET/POST /api/plantilla/emparejado` | `emparejado_talles.json` |
| Variables / grupos / modelos | `POST /api/productos/{variantes,grupos,modelos,conjuntos}` | catálogo |
| Medidas del diseño | `POST /api/productos/referencia_medida` · `GET /api/plantilla/medidas_variantes` | catálogo |
| Guía .ai | `GET /api/plantilla/pdf_guia` | descarga |
| Subir arte | `POST /api/arte` | `disenos/<slug>/arte.ai`, `validacion_arte.json`, `mapeo_arte.json` |
| Mapeo del arte | `POST /api/arte/mapeo` | `mapeo_arte.json` (`por_variable`) + `prod["mapeo_arte"]` |
| Preview real por pieza | `POST /api/arte/preview_piezas` | `piezas_cache/<variante>/<talle>/` |
| Editables (mover) | `GET/POST /api/productos/editables` | `prod["editables"]` |
| Editables (color) | `POST /api/productos/editable_color` | `…["objetos"][obj_id]["color"]` |
| Editables (tamaño) | `GET/POST /api/productos/editables_config` | `prod["editables_config"]` |
| Objetos agregados | `POST /api/productos/objeto_agregar` + `objeto_agregado/<oid>/*` | `objetos_agregados/` + `arte.v<N>.ai` |
| Borde de corte | `GET/POST /api/productos/borde_corte` | `prod["borde_corte"]` |
| Etiqueta | `GET/POST /api/productos/etiqueta` | `prod["etiqueta"]` |
| Telas del molde | `POST /api/productos/telas_asignadas` | catálogo |
| Telas del sistema | `GET /api/telas` · `POST /api/telas{,/refrescar,/ancho}` | registro de telas |
| Planillas | `GET/POST /api/plantillas_planillas*` · `POST /api/productos/asignar_planilla` | catálogo |
| Reglas | `GET/POST /api/reglas_planilla*` | catálogo |
| Nesting | `GET/POST /api/nesting_presets*` · `POST /api/productos/nesting_preset` | catálogo |
| Grupos de tizada | `GET/POST /api/grupos_tizada*` · `POST /api/productos/grupo_tizada` | catálogo |
| Fuentes | `POST /api/fuente` · `GET /api/fuente/glifos/<n>` | `catalogo_fuentes/` |
| Perfil ICC | `GET /api/perfiles` · `POST /api/perfiles/config` | config |
| Generar | `POST /api/generar` · `POST /api/generar_multi` · `GET /api/trabajo/<tid>` | `trabajos/<tid>/HOJA_*.pdf`, `prev_*.svg`, ficha |
| Publicación | `GET /api/publicacion/estado` · `POST /api/publicacion/{publicar,cancelar}` | paquete |

---

## 9. Cachés: cuándo se invalidan (media feature si se olvidan)

| Caché | Dónde | Se invalida con |
|---|---|---|
| `piezas_cache/` (preview real del Arte) | disco, por `(variante, talle)` | `_piezas_base_clave` **v7**: plantilla, arte, mapeo, borde, etiqueta, editables (tf **y color**), tamaño, objetos agregados, **registro**. Al cambiar el motor **hay que borrarlo a mano** (la clave no incluye versión del motor) |
| `nido_cache.json` | por molde | `_nido_clave` **v6** (incluye mtime de `emparejado_talles.json`) |
| `deteccion_cache/` | por `(mtime plantilla, talle[, _cand])` | cambia el archivo del molde |
| `_pvCache` / `_talleDetCache` (front) | memoria del navegador | su clave se arma con **el mismo pid** que la URL; el color se invalida **a mano** |
| `_base_cache` (motor) | proceso | por `(pieza, talle, variable)` dentro de una generación |

**Si se toca `generar_pieza` / `_armar_base` / el estampado → verificar con diff pixel a pixel**
(harness `scratchpad/verif_tizada.py`). La salida tiene que ser **pixel-idéntica** ante refactors.

---

## 10. Síntomas frecuentes → qué mirar

| Síntoma | Causa típica |
|---|---|
| «Mapeé el arte pero salió otro / un solo talle» | La fila usa **otro diseño** (columna «Diseño») o un diseño **sin arte** → fallback silencioso |
| Piezas en blanco en la tizada | Esa pieza no tiene mesa mapeada (típico: los **Vivos**, que van a mano) |
| El molde «no se puede usar» / visor vacío | Faltan nombrar las **variantes** (capas) o el molde vino todo en una capa |
| Guardé el nombrado y se perdió / fue a otro molde | El endpoint fue **sin `pid`** → escribió en el molde **activo** |
| Cambié algo y el Arte muestra lo viejo | `piezas_cache/` stale → falta la clave o hay que borrarlo |
| El filtro por variable no filtra nada | Se pasó el **label** en vez de la **clave `v_xxx`** |
| Un objeto editable «gigante» que no se puede mover solo | Dos capas con el **mismo nombre** → el bbox es la unión. Renombrar una |
| No puedo recolorear un editable | Pinta vía **XObject/imagen**: el color vive adentro (control deshabilitado a propósito) |
| El tutorial se queda congelado tras escribir | Ver §6.3: la detección es por **poll del valor**, no por evento |
| «Mis artículos» vacío | El catálogo se pidió **sin sesión** (server reiniciado) → re-pedir con `[yo?.id]` |
| El talle no llega a la fila | Molde **sin `columnas`** → fallback `nombre/numero/talle` |

---

## 11. Cómo correr y verificar (para trabajar sobre esto)

- **Frontend:** se sirve desde `frontend/dist` → tras editar `src`: `cd frontend && npm run build`.
- **Server:** `py servidor.py`, puerto **8050** (env `PORT`). **Sin auto-reload** → tras tocar
  `.py` hay que **reiniciarlo** (matar por **PID específico**, nunca mass-kill).
- **Datos reales** (los del usuario) vs **sandbox** (`.claude/launch.json`, 2 moldes viejos): para
  ver los moldes reales hay que arrancar el server con `TIZADA_DATOS/TIZADA_ENTRADA/TIZADA_TRABAJOS/
  TIZADA_FUENTES` apuntando a las carpetas del repo.
- ⛔ **Con datos reales: sólo lectura y generar.** Nunca borrar ni sobrescribir `datos/`, `entrada/`,
  `catalogo_fuentes/`. Nunca borrar un molde con `creado_por`.
- **Verificación visual:** renderizar el PDF/SVG a PNG con `fitz` y mirarlo. Los textos son
  **curvas**: no se pueden `grep`ear, hay que rasterizar.

---

*Documento vivo. Si una herramienta cambia y esta entrada queda mintiendo, corregirla acá + en
`MAPA_DEL_SISTEMA.md` (sección + CHANGELOG), en la misma tanda.*
