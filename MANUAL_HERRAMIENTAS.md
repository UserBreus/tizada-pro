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
> Los guiones de la **ayuda guiada in-app** viven en `frontend/src/guias.js` y cuentan la versión
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

PEDIDO (todos los días)        ┐  diseño → variables → arte → planilla → enviar
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
- **⛓ Piezas que van juntas:** dentro de la variable → **＋ Vincular piezas** → tocar 2 o más piezas
  que van SIEMPRE juntas (ej. manga corta + su vivo) → elegir el nombre común → **Crear vínculo**.
  Si un toggle saca un miembro, se sacan **todos**.
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
   elegida). `GET /api/plantilla/pdf_guia`.
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

- **Se trabaja POR PIEZA** (2026-08-18). La etiqueta **es de la pieza** y vale para todo el molde:
  donde la pongas en el «Frente 1», queda en el «Frente 1» de **todos los talles y todas las
  variables**. ⛔ **«Frente 1» y «Frente 2» son piezas DISTINTAS:** cada una lleva su etiqueta y
  mover una **no mueve** las otras. La lista agrupa por nombre y muestra **`n/m`** cuántas de las
  piezas de ese nombre ya tienen su lugar marcado.
- **Pasos:**
  1. **Elegir la pieza** en la lista de la derecha (`etq-piezas`): una entrada por pieza
     («Frente», «Cuello»…, ~9 — no una por talle). Cada fila muestra cuántos talles tiene, un
     **✓** si ya tiene su lugar marcado, y un **sí/no** para apagarle la etiqueta a esa pieza.
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
- **Molde ANIDADO** (talles dibujados uno encima del otro): no existe la vista de todos los talles
  juntos, así que el visor muestra el talle en pantalla. Se configura igual — la posición es
  relativa al contorno.
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

Wizard `pedidoPaso`: **moldes → arte → planilla → (generar) → resultados**.

### 5.1 Paso «Diseños» — diseño(s) + variables

**El orden real es: primero se CREA EL DISEÑO y después se le eligen las VARIABLES.** No se elige un
molde: se eligen variables, que ya traen su molde detrás.

- **Pasos:**
  1. Escribir el nombre del diseño (`pedido-diseno-input`) — ej. «River titular» — y **Enter** o el
     botón **Diseño** (`pedido-diseno-agregar`). Un pedido puede llevar **varios**.
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
  4. **Ver telas de pieza** (`arte-telas`) → decir en qué tela va cada una. **Todas las piezas
     necesitan tela**: si falta alguna, no deja seguir.
  5. **A la planilla →** (`arte-siguiente`).
- **Guarda:** `POST /api/arte` (multipart `archivo` + `diseno` + `pid`) →
  `entrada/<pid>/disenos/<slug>/arte.ai` + `validacion_arte.json` + `mapeo_arte.json` +
  `registro_personalizacion.json`. Si el auto-mapeo cubre el alcance de las variables, **se aprueba
  solo**; si no, pide completar y dice qué falta. Un diseño no-principal además se registra con
  `POST /api/disenos/guardar` para que aparezca en la columna «Diseño».
  Después: `POST /api/arte/asignar_todo` (+ `GET /api/arte/asignar_estado`) y
  `POST /api/arte/preview_piezas` (render real cacheado en `piezas_cache/`).
- **Contador y bloqueos:** «X/Y con arte» + «⚠ Faltan N pieza(s) sin tela».
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
  6. **Agregar** N filas (`planilla-agregar`) o **⬆ Importar CSV** (`planilla-csv`).
  7. **Enviar →** (`planilla-enviar`).
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
  - **Descargar todo (N)**: baja **cada mesa por separado** (una página = un archivo), con su
    nombre. También hay ZIP (`GET /api/trabajos/zip`).
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
| Nombrar piezas | Variables paso 1 | clic = elegir · **recuadro** = varias |
| Elegir piezas de variable/grupo | Variables paso 2 | idem |
| Vincular «van juntas» | detalle de variable | clic sobre 2+ piezas |
| Telas por pieza | ajuste Telas | clic = pieza lleva esa tela |
| Etiqueta | ajuste Etiqueta | clic **sobre el borde** = posición |
| Mapeo del arte | Plantilla / paso Arte | arrastrar mesa → pieza |
| Acomodar / reacomodar | Moldería | arrastrar piezas |
| Asignar variantes por piezas | Moldería | clic / recuadro + nombre |

- **Navegación:** rueda = zoom, **clic derecho arrastrado** = mover. Botones **Ver todo** y **100%**.
- **Escala real fija (mm)**: el visor **no** se reescala por cantidad de piezas — como Illustrator.

### 6.2 **Ayuda guiada** (botón `nav-ayuda`, «Te guío paso a paso»)

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
- **27 guías** en 4 áreas (moldes · ajustes · pedido · configuración), en `guias.js`.
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

**Agregar/mover un control ⇒ tocar la ayuda.** El ancla es `data-tour="id"` en el JSX y ese `id` es
el `ancla` del guion. **Está verificado por `frontend/verificar_guias.mjs`, que corre en cada
`npm run build`** (`npm run guias` para correrlo suelto) y **corta el build** si:
- una guía pide un ancla que no existe en `App.jsx` (contempla las **dinámicas**
  `data-tour={'ajuste-' + item.id}` y las **condicionales**);
- un predicado `hecho`/`falta`/`listo` explota, o miente en los casos que importan (orden de las
  tareas, «no avanzar si el guardado falló», «no dar por hecho el gesto sin gesto»).

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

### 6.3 Modales y avisos
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
| El tutorial se queda congelado tras escribir | Ver §6.2: la detección es por **poll del valor**, no por evento |
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
