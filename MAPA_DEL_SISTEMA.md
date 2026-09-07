# 🧠 MAPA DEL SISTEMA — TIZADA PRO

> **Cerebro de Claude.** Léelo ANTES de tocar código. Actualízalo DESPUÉS de cada cambio.
> Es el mapa holístico del sistema: cómo funciona, qué está enlazado con qué, y qué podés
> romper si tocás algo (con las alternativas). Complementa las memorias (`~/.claude/.../memory/*.md`),
> que son hechos por-feature; esto es la foto completa.
>
> **Regla de mantenimiento:** cada vez que cambies una pieza del sistema, volvé acá y actualizá
> la sección correspondiente + el CHANGELOG del final. Si algo de acá ya no es cierto, corregilo.
>
> 🧰 **`MANUAL_HERRAMIENTAS.md` (raíz del repo) es el complemento OPERATIVO de este mapa**: una
> entrada por herramienta/pantalla con *qué hace · dónde está · precondiciones · los pasos exactos
> para completarla · qué guarda (endpoint + archivo) · trampas*. Este mapa explica **cómo funciona y
> por qué**; el manual explica **cómo se usa y cómo se completa**. Si cambia una pantalla, se
> actualizan **los dos** en la misma tanda (y, si la pantalla tiene guía in-app, `frontend/src/guias.js`).

---

## ▶️ CASO 1 — SI VAS A EJECUTAR EL PROYECTO, HACÉ ESTO (en orden)

> El usuario quiere ver la app con SUS MOLDES REALES. El preview con launch.json usa un
> SANDBOX (datos de prueba) — NO le sirve al usuario para trabajar. Pasos verificados 2026-07-13:

1. **Liberar el puerto 8050** si hay un server previo:
   - Si fue un preview MCP: `preview_stop` con su serverId.
   - Si es un proceso suelto: `netstat -ano | grep ':8050' | grep LISTEN | awk '{print $5}'` → `taskkill //F //PID <pid>` (NUNCA mass-kill).
2. **Arrancar el server con DATOS REALES** (Bash, `run_in_background: true`):
   ```
   cd "/c/Users/user2/Documents/tincho/codigos/TIZADA PRO" && \
   TIZADA_DATOS="$PWD/datos" TIZADA_ENTRADA="$PWD/entrada" \
   TIZADA_TRABAJOS="$PWD/trabajos" TIZADA_FUENTES="$PWD/catalogo_fuentes" py servidor.py
   ```
3. **Verificar** que responde con el catálogo real: `curl -s http://localhost:8050/api/productos | head -c 600` → debe traer "Camiseta de Futbol"/"COMUNEITOR" (no "Molde 1" solo = sandbox).
4. **Abrir/recargar el navegador** en `http://localhost:8050` (tab del Browser pane con `navigate`; los screenshots pueden timeoutear — verificar con `get_page_text`).
5. Recordatorios: tras editar `frontend/src` → `cd frontend && npm run build`; tras editar `.py` → reiniciar el server. Con datos reales: **SOLO lectura y generar** (regla dura §0).

*(El sandbox `preview_start {name:"tizada"}` queda solo para chequeos de consola/carga sin tocar datos reales.)*

---

## 0. Cómo trabajo yo acá (entorno + reglas duras)

- **Plataforma:** Windows 11, PowerShell (primario) + Bash (POSIX). Rutas con `/`.
- **Frontend:** React (Vite) en `frontend/src/App.jsx`. Se sirve **desde `frontend/dist`** → tras editar `src` hay que `cd frontend && npm run build`. El server sirve el `dist` fresco (no hace falta reiniciarlo por cambios de front, sí por cambios de `.py`).
- **Server:** `py servidor.py`, puerto **8050** (env `PORT`). Flask `threaded=True` (un request lento NO bloquea otros).
- **launch.json** (`.claude/launch.json`) apunta a un **SANDBOX** (`.preview_sandbox/datos|entrada|trabajos`, 2 moldes viejos) para **proteger los datos reales** del preview tooling. Para probar con **datos reales** corro:
  ```
  TIZADA_DATOS="$PWD/datos" TIZADA_ENTRADA="$PWD/entrada" TIZADA_TRABAJOS="$PWD/trabajos" \
  TIZADA_FUENTES="$PWD/catalogo_fuentes" nohup py servidor.py > /tmp/srv8050.log 2>&1 &
  ```
- **REGLAS DURAS (no negociables):**
  1. **NUNCA** borrar/sobrescribir datos del usuario (`datos/`, `entrada/`) al probar. Solo **GET** y **generar** (a `trabajos/` o a un `tempfile.mkdtemp()`). Ver [[no-revertir-datos-usuario]].
  2. Matar servers por **PID específico**: `netstat -ano | grep ':8050' | grep LISTEN | awk '{print $5}'` → `taskkill //F //PID <pid>`. **NUNCA** mass-kill (`taskkill //IM py.exe` está prohibido y lo bloquea el sandbox).
  3. El **caché derivado** (`piezas_cache/`, `nido_cache.json`) SÍ se puede borrar (se regenera).
- **Cómo verifico cambios (mi caja de herramientas):**
  - Generar a un tmp + **renderizar el PDF/SVG a PNG con `fitz`** y mirarlo (`get_pixmap` / `fitz.open(stream=svg, filetype="svg")`).
  - Para refactors del **motor**: generar la MISMA tizada antes/después y **diff pixel a pixel** con numpy/PIL (`(A-C).max()==0`). Harness: `scratchpad/verif_tizada.py`.
  - Endpoints: `urllib.request` contra el server, o importar `servidor as S` en un script y llamar funciones directo (setear env ANTES del import).
  - El preview MCP (`preview_*`) usa el sandbox → sirve para chequear consola/carga, no para la Camiseta real.

---

## 0.b 🧵 CAMINO B — MOLDE CON EL DISEÑO ADENTRO (en curso, rama `pruebas-tizada-con-diseno`)

Se está construyendo un **segundo camino de alta**: el cliente sube **UN archivo que ya trae el
diseño estampado adentro de cada pieza** (sin arte aparte ni mapeo). Convive con el de hoy; el
camino A **no se toca**.

🧠 **Todo lo de ese camino —plan, decisiones, preguntas abiertas y bitácora— vive en
`MOLDE_CON_DISENO.md` (raíz del repo).** Leerlo antes de tocar nada de esa feature y actualizarlo
en la misma tanda. Acá sólo queda el puntero, para que no se dupliquen dos verdades.

Lo mínimo que hay que saber si se toca CUALQUIER otra cosa del sistema (2026-09-02):

| Qué | Dónde se decide | Por qué importa afuera de la feature |
|---|---|---|
| «¿este molde es del camino B?» | **la marca `molde.origen` en disco**, al lado de `plantilla.ai` (`piezas_con_diseno.es_camino_b`) | el nesting paraleliza con **procesos**: una global de módulo no cruzaría. Y entra en la clave de **todos** los cachés que dependen del archivo (`_DET_CACHE`, `_PZS_CACHE`, el caché de detección en disco): el alta detecta y marca DESPUÉS, así que misma ruta + mismo mtime da resultados distintos |
| el flag para las pantallas | `prod["origen"] == "con_diseno"` (lo devuelve `/api/productos`) | la marca de disco manda para el motor; ésta es para la UI |
| **`idx_mesa`** | `registro[pieza][talle]`, columna nueva en `dbo.pieza_talle` | `pieza_idx` = posición dentro del **TALLE** (identidad, §8.9) · `idx_mesa` = posición dentro de la **MESA** (lo que indexa `extraer_piezas_mesa`). En el camino A coinciden; con 9 mesas, no. Al leer de la base la clave se pone **sólo si no es NULL** |
| moldes **efímeros** | `prod["efimero"]` | se borran solos («Nuevo pedido», «Terminar pedido» y el barrido al arrancar). 🔴 Sólo por el flag y la fecha — ver §8 |
| **el molde desplegado** | `entrada/<pid>/desplegado/` (`m{mesa}.pdf` + `m{mesa}.json` + `personalizacion.json`), lo escribe el alta (`piezas_con_diseno.desplegar_molde`) | el archivo se lee **una vez**: el motor toma de ahí la página de cada (mesa, talle) ya aislada y podada, y los contornos. Validado por **sello** (tamaño + fecha del `plantilla.ai`): si no coincide se rehace solo. Se borra con la carpeta del molde y al re-subir uno del camino A. Changelog 384 |
| nombrar sus piezas | `POST /api/plantilla/pieza_renombrar` | las herramientas del camino A (`etiquetas`, `grupo_pieza`, `emparejado`) devuelven **409** sobre un molde B: re-armarían el registro asumiendo una sola mesa |

---

## 1. Qué es el sistema (en una frase)

App **local** que toma un **MOLDE** (Illustrator `.ai` / PDF / DXF) + un **ARTE** (el diseño) y produce **TIZADAS**: hojas PDF vectoriales con las piezas acomodadas para cortar e imprimir (sublimación). Todo en **medidas reales (cm)**.

---

## 2. Arquitectura (3 capas)

```
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND  frontend/src/App.jsx (8.8k líneas, SPA única)      │  React 19 + Vite
│   Panel de Pedidos (wizard) + Configuración del molde        │
└───────────────┬─────────────────────────────────────────────┘
                │ fetch /api/...
┌───────────────▼─────────────────────────────────────────────┐
│ SERVER  servidor.py (3.2k)  Flask, sirve dist + API + caché  │  import motor_pedido as MP
└───────────────┬─────────────────────────────────────────────┘
                │ MP.generar_pedido(...) etc.
┌───────────────▼─────────────────────────────────────────────┐
│ MOTOR  motor_pedido.py (3.1k) — orquesta la generación       │
│   ├─ molde_real.py (563)   parsing .ai/PDF + capas OCG       │
│   ├─ nesting_contorno.py (291)  acomodo (nesting) + compose  │
│   ├─ texto_curvas.py (225)  texto como CURVAS (FuenteCurvas) │
│   └─ importar_dxf.py (542)  molde desde DXF (AAMA/Optitex)   │
└─────────────────────────────────────────────────────────────┘
```
Librerías clave del motor: **pymupdf (fitz)** (render/SVG/pixmap), **pikepdf** (manipular content-streams, XObjects, OCG), **numpy/scipy** (máscaras del nesting).

---

## 3. Los archivos y qué hace cada uno

### `servidor.py` (Flask)
- Constantes de rutas: `ENTRADA`/`TRABAJOS`/`DATOS` (env `TIZADA_*` o defaults). `FUENTES` = `catalogo_fuentes`.
- Helpers de ruta: `_ruta_entrada(nombre, pid, sub)` → `ENTRADA/<pid>[/<sub>]/<nombre>` (acá viven `plantilla.ai`, `arte.ai`). `_ruta_datos(...)` → `DATOS/productos/<pid>[/<sub>]/...` (jsons por molde). `_diseno_sub(diseno)` → `None` (principal) o `disenos/<slug>`. `_slugify_diseno`.
- `_cargar(nombre, pid, sub)` lee un json de datos; `_cargar_catalogo()`/`_guardar_catalogo()` el catálogo global.
- `_get_active_producto_id()` = molde "activo" del catálogo (`cat["activo"]`).
- **Orquesta** la generación llamando a `MP.*`, mantiene cachés (`_NIDO_CACHE`, `piezas_cache/`), y traduce filas de pedido a prendas (`_traducir_prendas`).
- `app.run(..., threaded=True, use_reloader=True)` al final.

### `motor_pedido.py` (el corazón)
- **`generar_pedido(plantilla, arte, registro, pers, prendas, fuentes, salida, *, mapeo_arte, rotaciones, asignacion_tela, telas_cfg, solo_piezas, borde_corte, etiqueta, editables_cfg, editables_tamano)`** — el entry point. Ver §6.
- `_armar_base(pieza, talle, variante)` + `generar_pieza(...)` (split Fase 2, §6).
- `partes_de` / `piezas_de` (qué piezas entran por toggles + variable).
- `detectar_arte`, `detectar_piezas`, `mapeo_por_nombre`, `mapeo_variantes_arte`, `nido_piezas`, `medidas_diseno`, `extraer_editables`, `extraer_personalizacion`, `validar_arte_separado`.
- Etiqueta text-on-path: `_eops_borde`, `_eops_zonas`, `_eops_tramo` (ver [[etiqueta-baseline-no-romper]]).
- `_nestear_y_componer` (agrupa por tela + llama al nesting).
- Constantes: `CM = 28.3465` (pt/cm), `MM = CM/10`, `PIEZAS_RIB = {"Cuello","TC","Tapacostura"}` (van a tela RIB por default), `CAPAS_GUIA` (capas "guías" que se descartan), `CAPAS_NO_PERS`, `CAPAS_ARTE`.

### `molde_real.py` (parsing del molde + capas)
- `extraer_contorno_mesa(doc, mesa, talle)` / `extraer_piezas_mesa(doc, mesa, talle, ...)` → **contornos** de las piezas (segmentos, bbox_raw/bbox_mu, w/h, user_unit). Es de acá que sale la geometría real de cada pieza.
- Manipulación OCG (capas): `limpiar_capas`, `suprimir_capas`, `aislar_capa`, `sanear_oc`, `limpiar_capas_conservando_talle`, `geometrias_base`.
- `generar_pieza_real`, `extraer_ancla_etiqueta`, `estampar_etiqueta` (legacy/util).
- Fuentes: `fuentes_requeridas`, `validar_fuente_subida`, `chequear_catalogo`.

### `nesting_contorno.py` (acomodo)
- `anidar_contorno(piezas, cfg)` → coloca las piezas (rasteriza a máscara con `_mascara`, prueba estrategias `bl`/`bandas`, rota según `_angulos`). Devuelve colocaciones + área.
- `componer_pdf_contorno(colocaciones, cfg, path, etiquetas)` → arma el **HOJA_*.pdf** final.
- cfg default: `ancho_cm=180, altura_max_cm=500, espaciado_cm=0.5, márgenes, resolucion_mm=3, estrategias=["bl","bandas"]`.

### `texto_curvas.py` (`FuenteCurvas`)
- Renderiza texto como **curvas vectoriales** (no fuentes PDF embebidas). `ops_texto` (recto), `ops_texto_curva` (sobre un arco), `ops_texto_fiel` (fiel a puntos de baseline = curva+multilínea del placeholder original), `ancho_texto`.
- Se usa para nombre/número (personalización) y la etiqueta.

### `importar_dxf.py` (BETA)
- Importa el MOLDE desde `.dxf` (AAMA/Optitex) con `ezdxf`. Ver [[importar-molde-formatos]]. El ARTE sigue siendo solo `.ai`.

### `migrar_ids.py`
- Migración de identidad de piezas (`pieza_id` estable ↔ nombre). Ver [[identidad-pieza-id-nombre]].

### `frontend/src/App.jsx` (TODA la UI)
- SPA única. Dos grandes zonas: **Panel de Pedidos** (wizard `pedidoPaso`: `moldes → arte → planilla → generar → tizadas`) y **Configuración** del molde (tabs: `variables`, `diseno`, `etiqueta`, `planilla`, telas, editables…).
- Componente clave: **`MapeadorArteVisual`** (~599) = el visor del molde con su diseño (paso Arte + config).
- Estado clave: `verVariante` (variante activa), `mapeoValores` (pieza→mesa), `disenoActivo`, `arteIdx`, `editorTfs` (transforms de editables transitorias), `previewPiezas` (render real cacheado).

---

## 4. Modelo de datos (dónde vive cada cosa)

**En disco:**
```
datos/
  productos_catalogo.json         ← EL catálogo: {activo, productos:[{id,nombre,variantes,disenos,
                                       columnas,borde_corte,etiqueta,editables,editables_config,
                                       mapeo_arte(fijo),variante_guia,...}]}
  productos/<pid>/
    registro_producto.json        ← TODAS las piezas del molde: {nombre:{talle:{mesa,pieza_idx,ancla,bbox_mu,...}}}
    piezas.json                   ← identidad estable: [{id, clave, nombre_generico}]  (id NO varía por talle)
    correspondencia_piezas.json   ← correspondencia de índices entre talles (para el nido)
    nido_cache.json               ← geometría nesteada cacheada {clave, nido}
    piezas_cache/<variante>/<talle>/  ← NUEVO: render real por pieza (svg) + manifest.json (Fase 1)
    disenos/<slug>/               ← por diseño nombrado (el "principal" va en la raíz):
       mapeo_arte.json            ← {mapeo:{pieza:mesa} (base/compat), por_variable:{v_xxx:{pieza:mesa}}}
                                     ⚠️ REGLA 2026-07-13: el mapeo se maneja POR VARIABLE (ver §5)
       validacion_arte.json, registro_personalizacion.json
    config_produccion.json, resumen_plantilla.json
entrada/<pid>/
    plantilla.ai                  ← EL MOLDE (contornos por talle, capas OCG por talle)
    plantilla_fuente.dxf
    disenos/<slug>/arte.ai        ← EL ARTE (diseño) de ese diseño
trabajos/<tid>/                   ← salidas generadas: HOJA_*.pdf, prev_*.svg, pedido.json
```
- `_diseno_sub("principal")` → `None` → los archivos del diseño base viven en la RAÍZ del pid (no en `disenos/`).
- El **mapeo** vive en DOS lados: `mapeo_arte.json` (por diseño) y `prod["mapeo_arte"]` (fijo del molde, se reusa si un diseño nuevo no tiene mapeo).

---

## 5. Conceptos centrales (el vocabulario — clave para no romper)

- **MOLDE (producto/pid):** el conjunto completo de piezas (`plantilla.ai` + `registro_producto.json`). Tiene TODAS las piezas de TODOS los talles.
- **PIEZA:** una parte del molde (Frente, Espalda, Cuello, Manga…). Identidad triple (ojo, [[identidad-pieza-id-nombre]]):
  - `nombre` (ej. "Frente 18") — lo que se lee en el arte/planilla.
  - `pieza_id` — id ESTABLE (no varía por talle). En `piezas.json`.
  - `pieza_idx` — índice DENTRO de la mesa en UN talle (VARÍA por talle). No usar para identidad multi-talle.
  - `clave` — la clave de la pieza en el registro.
- ⚠️ **VARIABLE ≠ VARIANTE** (terminología del usuario — el código las CRUZA, cuidado):
  - **VARIABLE** = la **selección de piezas / modelo** (MP1-A, MP1-A1, "con costadillo") = *qué piezas* forman la prenda. Es lo que se elige por fila en la planilla y sobre lo que trabaja el editor. En el CÓDIGO se guarda en `prod["variantes"] = [{clave:"v_xxx", label:"MP1-A", valores:[{pieza_id,pieza_idx}], juntas, grupoId, orden}]` y el estado es `verVariante` (¡mal nombrado! guarda la VARIABLE). En el motor viaja por su **clave `v_xxx`** (NO el label); `_traducir_prendas` la resuelve a `variante_piezas`+`variante_clave`.
  - **VARIANTE** = el **TALLE** (1..16 numéricos; XS..6XL letra) = *el tamaño*. `variante_guia` (ej "M") = talle de referencia. El picker "Elegí las **variantes**" muestra TALLES; `verVarianteOperario(talle)` cambia el talle visto. El editable se puede editar para todas las variantes / un rango / una (scope de TALLES).
- **GRUPO:** grupo de piezas (`prod["grupos"]`, ej. "MP1-A2"). Adentro viven las VARIABLES. **CONJUNTO** (`prod["conjuntos"]`) = sub-armado con nombre (ej. "cuello polo V").
- **TOGGLE DE PIEZA** (generalización de manga corta/larga): `{clave, opcion, opciones}`. `partes_de` incluye/excluye piezas según mencionen la clave+opción. Ver [[toggle-de-pieza-generalizado]].
- **VAN JUNTAS:** vínculo atómico entre piezas (ej. vivo ↔ manga). Si el toggle saca un miembro, se sacan TODOS. Vive en el **GRUPO** (`prod["grupos"][].juntas`, desde 2026-08-21; `prod["variantes"][].juntas` sigue leyéndose por compat) → `juntas_piezas` en la prenda → filtrado en `partes_de` (~2289). Es además lo ÚNICO que habilita dos piezas con el mismo nombre en una variable (§10.c).
- **DISEÑO:** un arte con nombre (`arte.ai` en `disenos/<slug>/`). "Principal" = el base (raíz). Un molde tiene varios diseños. Ver [[multiples-disenos]].
- **MESA (del arte):** una página del `arte.ai` = el diseño de una pieza. El **MAPEO** dice qué mesa va en qué pieza (`{pieza: mesa}`).
- ⛔ **MAPEO POR VARIABLE (regla dura del usuario, 2026-07-13):** el mapeo se maneja **por VARIABLE**, nunca más por molde entero. `mapeo_arte.json = {mapeo: base, por_variable: {v_xxx: {pieza: mesa}}}`. El de la variable es **AUTORITATIVO** (quitar un diseño en una variable NO se resucita por la base); la base queda para datos viejos, filas sin variable y como semilla. Flujo: deteccion `?variante=` (devuelve `piezas_variable` = alcance), guardado con `variante` (validación acotada con `piezas_scope`), motor `mesa_arte(pieza, talle, variante)` resuelve por la `variante_clave` de cada fila, avisos de generación por variable. Al subir un arte, el auto-mapeo puebla `por_variable` con el recorte de cada variable y la completitud se mide contra la UNIÓN de las variables (`_alcance_variables`), no el molde.
- **BORDE DE CORTE:** trazo por molde (`prod["borde_corte"] = {activo,ancho_mm,color:[c,m,y,k]}`). Ver [[borde-corte-molde]].
- **ETIQUETA:** texto de corte (talle·pieza·#nro) sobre el borde, text-on-path. `prod["etiqueta"]`. Ver [[etiqueta-baseline-no-romper]], [[etiqueta-por-variable]].
- **OBJETOS EDITABLES:** capas OCG "Editable …" del arte que se mueven/rotan/escalan por talle. Posición guardada **POR VARIABLE** (desde 2026-07-10): `prod["editables"][diseno_slug][VARIABLE_clave][nombre]["transforms"][talle]` (`"*"` = base compartida legacy). **POR OBJETO** (desde 2026-07-22): una capa con VARIOS objetos anida `…[nombre]["objetos"][obj_id]["transforms"|"color"]` (cada trazado/XObject se edita solo); una capa de 1 objeto queda plana (compat). El motor recibe `editables_cfg = {variable:{IDENT:{talle:tf}}}` con IDENT = nombre de capa (1 objeto) o `"nombre<SEP>obj_id"` (multi). `dx/dy` = FRACCIONES del tamaño de la pieza. Tamaño en `prod["editables_config"]`. **COLOR** override (recoloreo CMYK, POR VARIABLE, a nivel objeto): `…["color"] = {"fill":[cmyk]|null,"stroke":[cmyk]|null}` → motor `editables_color`; sólo trazados con relleno/trazo directo (XObject/imagen NO). Ver §10.b y [[capa-editable]].
- **TELAS:** registro global (nombre+ancho) + grupos + telas por molde + tela por pieza en el pedido (una hoja por tela). Ver [[telas-registro-grupos-pedido]]. `PIEZAS_RIB` van a "RIB" por default.
- **VIVOS (huérfanos):** los "Vivo espalda/fente/derecho/izquierdo" NO tienen mesa propia en el arte → son piezas **huérfanas**. Se mapean **A MANO** (el usuario los arrastra a una mesa). **NO hay auto-herencia** (se sacó, decisión del usuario 2026-07-09). Sin mapear → salen blancos en Arte Y tizada (consistente).

---

## 6. El pipeline de generación de la tizada (`generar_pedido`)

Entra: `plantilla.ai`, `arte.ai`, `registro`, `pers` (placeholders de personalización), `prendas` (filas ya traducidas), config (mapeo, borde, etiqueta, editables, telas). Sale: `HOJA_*.pdf` por tela (o `piezas_por_tela` si `solo_piezas=True`).

**Pasos (motor_pedido.py ~2197–2832):**
1. Por cada **prenda** (fila del pedido) → `piezas_de(prenda)` = `partes_de` (toggles + van-juntas) ∩ `variante_piezas` (la variable). Decide QUÉ piezas.
2. Por cada **pieza** → `generar_pieza(pieza, talle, persona, nro, grupo, variante)`:
   - **`_armar_base(pieza, talle, variante)`** (CACHEADA por `(pieza,talle,variante)` en `_base_cache`): contorno real del molde (de `extraer_*_mesa`) + diseño de la mesa (`copy_foreign` del XObject del arte, VECTORIAL) escalado con `cm_encajar` (alto manda, centrado) recortado al contorno + borde de corte + objetos editables. Devuelve `out` (pikepdf), `page`, `cstream` (stream reusable), `base_stream`, geometría. **Sin nombre/número ni etiqueta.**
   - **Estampado por prenda** (encima de la base): personalización (nombre/número con `FuenteCurvas`, respeta curva/borde del placeholder; el borde se pinta DETRÁS y el relleno encima = neto de cómo Illustrator aplana la Apariencia "borde detrás", ver changelog 2026-07-16) + etiqueta (talle·pieza·#nro, text-on-path). Se reescribe `cstream` y se guardan los bytes.
3. Cada pieza va a `piezas_por_tela[TELA(pieza)]`.
4. **`_nestear_y_componer`** → `anidar_contorno` (acomoda) + `componer_pdf_contorno` (arma la hoja) → una `HOJA_<tela>.pdf` + `prev_*.svg` (con fondo blanco) por tela + consumo/aprovechamiento.

**Fase 2 (reuso):** la base se arma UNA vez por `(pieza,talle,variante)` y se reusa por prenda (solo cambia el texto). ⚠️ Verificado **pixel-idéntico** a la versión monolítica — cualquier cambio al split DEBE re-verificarse con diff pixel.

**Preview del Arte (Fase 1):** `_piezas_base` (servidor.py) corre `generar_pedido(solo_piezas=True)` con UNA prenda de muestra (nombre "NOMBRE", número "00") y **cachea el SVG por pieza en disco** (`piezas_cache/<variante>/<talle>/`, clave = mtimes + hashes de config, `_piezas_base_clave`). El visor del Arte muestra ESE svg → **Arte = tizada, un solo motor**. Ver [[arte-wysiwyg]].

---

## 7. 🔗 ENLACES CRÍTICOS — "si tocás X, revisá Y" (para no romper)

| Si tocás… | Revisá / puede romper… |
|---|---|
| **`generar_pieza` / `_armar_base` / el estampado** | La salida de la tizada. **Verificá diff pixel a pixel** (harness). El split base/overlay debe dar bytes de render idénticos. |
| **`_piezas_base` / `_piezas_base_clave`** | El preview del Arte. Si cambiás qué entra al render, **bumpeá la versión de la clave** (`"v2"→"v3"`) para invalidar cachés viejos, y borrá `piezas_cache/`. |
| **`partes_de` / `piezas_de` / toggles / van-juntas** | QUÉ piezas entran en la tizada. Un cambio acá puede hacer aparecer/desaparecer piezas (ej. el bug del vivo por van-juntas). |
| **`mapeo_arte` / `mapeo_por_nombre` / `mesa_arte`** | Qué diseño va en cada pieza. El mapeo es por **nombre genérico** (una mesa "Cuello" cubre "Cuello 1..N") y **POR VARIABLE** (regla 2026-07-13): tocá el nivel correcto — `por_variable[v_xxx]` es autoritativo; la base es semilla/compat. `mesa_arte(pieza, talle, variante)` en el motor; helpers `_mapeo_estructura`/`_mapeo_efectivo`/`_piezas_de_variable` en servidor.py. |
| **La variante (clave `v_xxx`)** | TODO lo per-variante. Pasar el **label** en vez de la **clave** NO filtra (bug clásico). El front manda `verVariante` (clave); el motor usa `variante_clave`/`variante_piezas`. |
| **`etiqueta` (config o `_eops_*`)** | El text-on-path. **NO ROMPER la baseline** ([[etiqueta-baseline-no-romper]]). Posiciones en cascada: `variante§nombre completo` > `variante§genérico` > `grupo§nombre` > `nombre` global > **otra variable** (último recurso, entrada 146). El motor y el preview del front tienen que resolver IGUAL: cuando el preview tenía más fallbacks, la etiqueta se veía bien en pantalla y salía en el lugar por defecto en la tizada. Contrato: `verificar_etiqueta_posicion.py`. |
| **`editables` (mover/persistir)** | `set_editable` guarda por `(pid, diseno_slug, IDENT, talle)` — IDENT = nombre de capa (1 objeto) o `"nombre<SEP>obj_id"` (capa multi-objeto, anida en `…[capa]["objetos"][obj_id]`, §10.b/§5). El front resuelve `pid` con `moldesDeDiseno(disenoActivo)[arteIdx] || productosCat.activo` (¡ojo con `_mid` undefined → guarda en el molde activo equivocado!). El motor: los objetos editados/recoloreados se sacan de la base **por objeto** (`suprimir_objetos`) + se redibujan (`pagina_arte_solo(obj_id=)`); el resto de la capa queda en el diseño. **Color override** (`set_editable_color`/`_editables_color`/`editables_color`) usa el MISMO camino "redibujar": un color-override suma el objeto a `_redibujar_nombres`. Recolorar SIEMPRE **antes** de aislar (§10.b). El color NO está en `_pvKeyCon` (memoria del front) → `guardarColorEditable` invalida `_pvCache` a mano; sí está en `_piezas_base_clave` v7 (disco). |
| **La FICHA TÉCNICA (`_guias_ficha` / `_molde_guia_ficha` / `ficha_tecnica.py`)** | Lo que ve el TALLER. Una guía por **(molde · diseño · variable)**: si tocás cómo se recolectan, revisá que sigan saliendo **después del `_fallback`** (el arte real) y con **la tela de SU diseño** (`_asig_de(dslug)` resuelta dentro del bucle, no en el hilo). Contrato: `verificar_ficha_disenos.py`. |
| **`columnas` del producto** | La Camiseta NO tiene columnas → `_traducir_prendas` cae al fallback `pr.get("nombre"/"numero"/"talle")`. Si asumís columnas, rompés esos moldes. |
| **El catálogo (`_guardar_catalogo`)** | Es global. Escribir desde un estado stale del front puede pisar `editables`/`mapeo_arte`/`variantes`. Los endpoints leen el catálogo FRESCO antes de modificar. |
| **Cualquier pantalla de CONFIGURACIÓN del molde** | ⛔ **TODO va por `pidCfg`/`prodCfg` (el molde ABIERTO), nunca por `activoProdDetalle` (el ACTIVO del server).** Leer de uno y escribir en el otro **copia la configuración de un molde adentro de otro** (pasó: entrada 122). `activoProdDetalle` sólo puede aparecer en el PEDIDO y en la grilla de molderías. Un grep de `activoProdDetalle` dentro del bloque de config tiene que dar **cero**. |
| **Un endpoint que recibe el molde en el campo `id`** | `_pid_de_request` **ignora `id` a propósito** (en varios endpoints es un preset/regla/grupo) → esos endpoints **no pasan por `_guardia_moldes`**. Hay que llamar **`_guard_id(cuerpo)`** (o `_guard_molde(pid)`) a mano. Lo mismo con los que reciben una LISTA de moldes (`generar_multi` → `molds`). |
| **`fetchProductos()` (se llama en ~28 lugares)** | Cada llamada crea un `productosCat` nuevo. Los efectos que **siembran buffers de edición** (variables, modelos, grupos, telas) tienen que estar clavados por **`pidCfg` + una GENERACIÓN**, no por el objeto ni por una firma del contenido: si no, re-siembran y **pisan lo que el usuario está editando sin guardar**. |
| **Puertos/servers** | El front nuevo contra un backend viejo (o al revés) = incoherencia. Reiniciá 8050 tras editar `.py`. Recompilá `dist` tras editar `src`. |

---

## 8. ⛔ INVARIANTES / NO ROMPER

- **LA PIEZA SE IDENTIFICA POR ID NUMÉRICO, NUNCA POR NOMBRE (regla dura del usuario, 2026-07-17).** El **nombre** se sigue usando para todo lo que se usa hoy (mostrar, agrupar, mapear, renombrar…), pero **identificar es SIEMPRE por id**. Nada se guarda con el nombre como clave. Formato: **número pelado y secuencial** (`1`, `2`, `3`…) — sin prefijo `pz_`, sin ceros a la izquierda, sin strings. Arranca en 1.
  - **Cada pieza NUEVA tiene su propio id.** Un id no se reusa ni se recicla: pieza nueva = id nuevo.
  - **Cada pieza se registra TAMBIÉN con un id dentro del MOLDE del que vino** → dos ids por pieza: el suyo (identidad) y el que ocupa dentro de su molde de origen.
  - **Motivo:** guardar por nombre hace colisionar a las piezas homónimas (dict por nombre → se pierde una), y de ahí salen los parches que rompen cosas: el renumerado al nombrar y el "un solo slot por nombre" de las variables (ver changelog 2026-07-17).
  - ⚠️ **CONTRADICCIÓN A RESOLVER en la Fase 3:** las fases 1-2 (backend) ya escribieron ids que NO cumplen la regla — `piezas.json` trae `{"id": "pz_0001", …}` (string con prefijo) + un campo **`clave` que ES el nombre** (la identidad por nombre sigue viva dentro del modelo que venía a reemplazarla). Decidir la migración con el usuario ANTES de tocar el frontend. Ver [[identidad-pieza-id-nombre]], [[bug-renumerado-nombres-piezas]].

1. **Arte = tizada, UN solo motor.** El visor del Arte muestra el render del motor cacheado; NO re-dibujar la pieza en JS (eso causaba el "tinte teal"). El re-dibujo JS quedó SOLO como placeholder mientras carga el caché.
2. **Salida de la tizada pixel-idéntica** ante refactors internos (Fase 2). Verificar siempre.
3. **Etiqueta baseline** ([[etiqueta-baseline-no-romper]]): el text-on-path sobre el borde quedó fino; respaldo `respaldo29626.rar`. No reintroducir los bugs listados ahí.
4. **Vivos = mapeo manual**, sin auto-herencia (decisión del usuario). Sin mapear = blanco consistente en Arte y tizada.
5. **Todo en tamaño real (cm).** Nada de miniaturas como fuente de verdad; el diseño VECTORIAL sigue vectorial (`as_form_xobject`, no rasterizar).
6. **No tocar datos del usuario al probar** (regla dura §0).
7. **LA SUBIDA DE UN MOLDE ES ATÓMICA.** El archivo entra a un temporal (**con extensión `.ai`**: PyMuPDF deduce el tipo por la extensión) y sólo reemplaza al molde bueno —`MP.cerrar_abiertos()` + `os.replace`— **si el alta pasó**. Lo mismo vale para `correspondencia_piezas.json`, que viaja en la misma transacción. Antes se guardaba encima y se procesaba después: al fallar, el molde quedaba con **archivo nuevo + registro viejo**, o sea las piezas apuntando a la geometría de otro archivo. En Windows `os.replace` da **WinError 5** si el PDF está abierto → hay que cerrar primero, y si aun así falla el molde viejo queda intacto.
8. **Config: se lee y se escribe SIEMPRE el mismo molde** (ver §7, fila de `pidCfg`).
9. **`pieza_idx` es una POSICIÓN DENTRO DE UN TALLE, no una identidad.** Nunca comparar ni guardar un `pieza_idx` sin saber **de qué talle es**: el que manda la pantalla es el del talle que se está mirando. Traducirlo contra otro talle se hace **por el registro** (`_puente_idx`, `_idx2id_de`), y para guardar identidad se usa el **`pieza_id`** de `piezas.json`. De acá salieron los bugs 3, 9 y 15.
10. **`piezas.json` es APPEND-ONLY.** Una pieza que sale del registro se marca `retirada: true`; **no se borra y su id no se recicla nunca** (`usados` cuenta también las retiradas). Si se borrara, al volver la pieza recibiría un id nuevo y las variables que la apuntaban quedarían colgadas. La resolución del id va en **dos pasadas** (toda la clave exacta primero, después el ancla): de a una clave, el resultado depende del orden del registro y dos claves pueden terminar con el MISMO id.
11. **No tocar datos del usuario incluye MSSQL, no sólo `datos/`** (ver §9).
13. **DE QUIÉN ES UN MOLDE — regla del usuario (2026-07-29):** lo que se carga en **CONFIGURACIÓN es
    del SISTEMA** (sin dueño personal: `creado_por = None`, aunque lo suba alguien con su sesión), lo
    ve y lo usa todo el taller. Lo que se sube en **PEDIDO → «Mis artículos» es de quien tiene la
    sesión** (`propio: true` + `creado_por`), **no lo ve nadie más y sólo lo toca su dueño** — ni
    siquiera un admin con `molde.editar` (`molde.ver_todos` da VER, no escribir). `alta_por` guarda
    quién lo dio de alta: es trazabilidad, **nunca** se usa para decidir quién ve qué. Y los «Mis
    artículos» **no se listan en Configuración**: usan las mismas herramientas pero se manejan aparte.
12. **AUTORÍA ≠ PRIVACIDAD ≠ PERMISO.** Tres cosas distintas, y confundirlas ya rompió el catálogo:
    **`creado_por`** dice quién dio de alta el molde (lo lleva todo lo creado con sesión);
    **`propio`** dice que es «Mi artículo» y sólo lo ve su dueño (`_es_privado`); el **permiso**
    (`molde.editar` / `molde.borrar`) dice quién puede TOCARLO. Corolario que hay que sostener:
    **ver un molde del catálogo no habilita a escribirlo** — si se arregla la visibilidad sin la
    guarda de permiso, cualquiera con sesión puede re-subir o borrar el molde compartido.

---

## 9. 🐛 TRAMPAS CONOCIDAS (gotchas que ya me mordieron)

- 🔴 **EL SISTEMA VIVO PUEDE IR ADELANTE DEL CLON: no subas un archivo suelto sin comparar.**
  Pasó dos veces el mismo día, en las dos direcciones: (1) el repo tenía `actualizador.py`
  Windows-only mientras el VPS corría el adaptado a systemd — publicar se lo habría pisado, y el
  daño recin aparece en la actualización SIGUIENTE; (2) al recuperar el VPS se le copió por `scp`
  un `actualizaciones.py` viejo sobre uno nuevo: el `servidor.py` nuevo llamaba a
  `limpiar_si_aplicada()`, que en el viejo no existía → `AttributeError` en el arranque y systemd
  reintentando cada 5 s (`activating (auto-restart)`). **Regla: antes de subir un archivo, mirar
  la versión del sistema VIVO (`/api/salud` → `version`) contra el `VERSION` local; si el vivo va
  adelante, el archivo bueno es el de allá y el arreglo se manda como PARCHE, no como archivo
  entero.** Y para el sistema completo, mandar el PAQUETE (coherente) en vez de archivos sueltos.
  (2026-08-21, entradas 249 y 253)
- 🔴 **`Restart=always` PELEA CONTRA EL ACTUALIZADOR.** El unit de systemd relanza el servidor **5 s
  después** de que el proceso se apaga. El ayudante de actualizaciones da por hecho que, una vez
  apagado, el programa se queda quieto (en Windows es así: la tarea es «al iniciar el sistema»); en
  Linux vuelve solo y se descomprime **por debajo de un servidor vivo**, que además sigue sirviendo
  el código viejo desde memoria. Por eso `actualizador.py` hace **`systemctl stop` ANTES** de esperar
  el apagado. Regla general: en Linux, apagar el proceso ≠ parar el servicio.
  (2026-08-04, entrada 146)
- 🔴 **EN LINUX, `localhost` NO ES `127.0.0.1`.** Ubuntu resuelve `localhost` a **`::1` (IPv6)**
  (`getent hosts localhost` lo dice), y un SQL Server en Docker publicado como `127.0.0.1:1433`
  escucha **sólo en IPv4** → `TIZADA_DB_SERVER=localhost,1433` no encuentra a nadie y muere con
  `HYT00 Login timeout expired` a los 10 s. El error NO dice «no hay ruta»: parece un problema de
  credenciales o de firewall y se busca donde no está. **En Linux poner siempre la IP literal:
  `TIZADA_DB_SERVER=127.0.0.1,1433`.** (Es el mismo fenómeno IPv6-antes-que-IPv4 que ya obligó al
  dual-stack de `servidor.py`, del otro lado del cable.) (2026-08-04, migración al VPS)
- 🔴 **LOS PERFILES ICC SE BUSCAN EN RUTAS DE WINDOWS: en Linux hay CERO y el color sale mal.**
  `PERFILES_DIRS` (`servidor.py`) lista carpetas de Adobe/Windows; en un servidor Linux ninguna
  existe, así que `/api/salud` marca `perfiles_icc: ok=false` («USWebCoatedSWOP.icc NO ESTÁ») y la
  conversión CMYK↔RGB se queda sin el perfil con el que se ve en Illustrator. **No hay paquete de
  Linux con el perfil de Adobe**: hay que copiar los `.icc/.icm` de la máquina del taller y apuntar
  **`TIZADA_PERFILES`** a esa carpeta. El chequeo tiene que quedar en `23 perfiles · CMYK por
  defecto: U.S. Web Coated (SWOP) v2`. (2026-08-04, migración al VPS)
- 🔴 **UNA PIEZA PUEDE DETECTARSE Y NO TENER GEOMETRÍA.** `_contorno_de` (`molde_real.py`) arma
  `segmentos` desde los `items` de PyMuPDF; si aparece un tipo que no maneja, la pieza sale con
  `segmentos == [("h",)]` — **bbox sí, puntos no** — y todo lo que dependa del contorno (el nido, y
  el CLIP con el que se arma la pieza) queda vacío **sin error**. Ya pasó con los cuadriláteros
  (`qu`): 2 tiras finas del molde real desaparecían del nido. Si se agrega soporte de formas,
  chequear `_bbox_segs` != None sobre TODOS los contornos, no que «se detecten». (2026-07-29)
- **Cruzar el nido con las variables va POR `pieza_id`, nunca por nombre.** El mapa id→clave de la
  detección está cacheado y no se vuelve a pedir: al renombrar una pieza quedaba viejo y la variable
  mostraba de menos. El nido trae el `pieza_id` de cada pieza (`_nido_con_ids`). (2026-07-29)
- 🔴 **EL NIDO ES GEOMETRÍA DEL REGISTRO, NO DE LAS VARIABLES.** `/api/plantilla/nido` sólo depende de
  la plantilla + el registro. Invalidarlo al guardar una VARIABLE es tirar algo caro que no cambió —
  y como el efecto que lo pide tiene que mirar `nidoData` para volver a pedirlo, invalidarlo de más
  hacía **desaparecer la vista de todos los talles hasta recargar la página**. Invalidar SÓLO cuando
  cambia el registro (subir molde, nombrar piezas, emparejado). Lo cuida el chequeo del build.
  (2026-07-29, regresión propia de la entrada 122)
- 🔴 **EL MOTOR ARMA LA PRENDA POR EL NOMBRE DE LAS PIEZAS.** `partes_de` (motor) mira los tokens del
  nombre: una pieza que menciona la CLAVE del toggle («manga») y **otra** opción de la que se eligió
  queda AFUERA. Consecuencias que no fallan —salen bien impresas— y por eso hay que validar antes
  (`_validar_pedido`): elegir «Larga» en un molde cuyas piezas dicen «Manga Corta …» deja la prenda
  **sin mangas**; y si las piezas dicen «Manga Derecha» a secas, el toggle **no cambia nada** (elegir
  Corta o Larga da la misma tizada). Al validar hay que usar **`tokens_pieza`/`opciones_soportadas`
  del motor**, no una normalización propia. (2026-07-29)
- 🔴 **«Principal» NO ES UNA TELA.** `TELA(p)` (motor) manda ahí cualquier pieza sin tela asignada —
  resto de antes del sistema de telas — y esa hoja sale con el ancho **por defecto (180 cm)**, no con
  el de ninguna tela real: aparece una hoja fantasma de pocos centímetros al lado de la buena. El
  pedido **no tiene tela base a propósito** (cada pieza debe tener la suya), así que cualquier pieza
  que se escape del panel de telas termina ahí. Ya pasó (trabajo 20260729-105151: `Cuello 12` y
  `Tapa costura`). Ahora `_validar_pedido` corta antes. ⚠️ El aviso «faltan N piezas sin tela» del
  paso Arte mira sólo las piezas **que se ven en el visor**: no es la lista completa. (2026-07-29)
- 🔴 **UN `dist` VIEJO SE DISFRAZA DE BUG.** El frontend se sirve COMPILADO (`frontend/dist`): editar
  `frontend/src` no cambia nada hasta correr `npm run build`. El síntoma es indistinguible de un bug
  de lógica — se toca el código, se prueba, «no anda», y se busca la falla donde no está. **Ya pasó
  (2026-07-29):** el arreglo del botón de un clic de la planilla estaba en `src` y el usuario seguía
  teniendo que hacer doble clic. **Cómo se confirma en 5 segundos:** buscar un texto literal de la UI
  DENTRO del bundle (`frontend/dist/assets/*.js`). ⚠️ Los nombres de variables/funciones y los
  comentarios NO sobreviven a la minificación: hay que buscar un **string que se vea en pantalla**.
  Ahora además lo avisa solo: `GET /api/salud` → chequeo **`frontend_compilado`** (mtime de `src` vs
  `dist`), no crítico, con el comando a correr en el detalle.
- **La CONFIGURACIÓN de una columna de planilla puede venir de la columna o de su REGLA.** Siempre
  resolver `c.tipo || regla?.tipo` y `c.opciones || regla?.opciones` (helpers `_tipoCol` /
  `_opcionesCol` en `App.jsx`, y `_toggle_info` en `servidor.py` ya lo hacía). Mirar sólo la columna
  dibujaba como **casilla de texto** una columna de BOTÓN definida por una regla, y usaba
  `corta/larga` en minúscula en vez de las opciones que puso el usuario. (2026-07-29)

- 🔴 **`TIZADA_DATOS` NO AÍSLA LA BASE.** La conexión MSSQL sale de `TIZADA_DB_SERVER`/`TIZADA_DB_NAME`
  (`db.py:17-20`), que **no tienen nada que ver con `DATOS`**: redirigir los archivos a un temporal da
  una sensación de aislamiento que no existe. **Ya pasó** (2026-07-28): `verificar_piezas.py` escribió
  el producto `prod_test` + 3 piezas en la base REAL del usuario. Y no es sólo `sync_piezas_molde`:
  **`_guardar_catalogo` reescribe las tablas normalizadas enteras** (`pieza`, `variable`,
  `variable_pieza`, `talle`, `diseno`) y lo llaman ~20 endpoints — y **hasta LEER el catálogo puede
  dispararlo** (`_cargar_catalogo` siembra con `set_doc`+`sync_productos` si no hay doc, y el backfill
  de `plantillas_planillas` llama a `_guardar_catalogo`). **Un test que importa `servidor` tiene que
  reemplazar el MÓDULO `db` entero en `sys.modules` ANTES del import** (servidor hace `import db` a
  nivel de módulo) por un doble que EXPLOTE: así queda cubierto también lo que se agregue mañana y
  falla ruidoso en vez de escribir en silencio. Monkeypatchear función por función no alcanza.
- **El editor dibuja con el SVG del ARTE CRUDO** (`extraer_editables`) → cualquier override (color)
  NO se ve en pantalla aunque la tizada sí lo aplique. Si se agrega un override que cambie el
  ASPECTO, hay que regenerar el svg en `get_editables` (`MP.svg_editable`) **y anular `thumb`**
  (la lista prefiere el PNG). (2026-07-22)
- **Modal montado dentro de una pantalla** → el estado se setea y **no se abre nada**. Pasó con
  `ColorPickerModal`, que vivía dentro de la tab `etiqueta` de Config: `setPicker` desde el editor de
  objetos no abría nada. Los modales globales (`picker`) van **una sola vez, al final del `return` de
  `App`**, nunca colgados de una rama condicional. (2026-07-22)
- **`_mid` undefined en el editor de editables** → guarda en el molde ACTIVO equivocado. Fix: fallback a `productosCat.activo` + guarda dura. (2026-07-09)
- **`_selT` filtrado contra `editableData.talles` vacío** → pierde el rango elegido → guarda talles `[]`. Fix: no filtrar si `talles` está vacío.
- **`_piezas_base` con `pers={}`** → el preview no mostraba textos. Fix: pasar `MP.extraer_personalizacion(arte)` + textos de muestra.
- **Molds SIN `columnas`** → el talle no llegaba a la fila mock (usaba default "M"). Fix: `fila["talle"]=talle` directo.
- **Variante por label vs clave** → `MP1-A` no matchea; `v_jl31t5b` sí.
- **Caché stale** → tras cambiar el motor, `piezas_cache/` viejo puede servir render viejo (la clave no incluye versión del motor). Borrar el caché tras cambios del motor.
- **Producto "activo" cambia** (`cat["activo"]`) → endpoints que usan `_get_active_producto_id()` (`/api/arte/deteccion`, `/api/arte/mapeo`, `get_editables`) dependen de él; `preview_piezas`/`generar` toman `pid` explícito. Inconsistencia latente: convendría que todos tomen pid explícito.
- **launch.json = sandbox** → el preview MCP no ve la Camiseta real; para probarla, server manual con env a datos reales.
- **Diseño sin `arte.ai`** (ej. "jugador") → fallback a otro diseño para lo principal; sus piezas huérfanas (vivos) salen sin nada.
- **Texto = curvas** → no se puede `grep` "NOMBRE"/"00" en el SVG (son `<path>`); verificar renderizando a PNG.
- **Parsear content streams: el color es ESTADO GRÁFICO** → cualquier lectura lineal de `k/rg/g/scn` sin trackear `q`/`Q` lee colores equivocados (Illustrator dibuja el halo en `q..Q` y el texto después del `Q`). Los parsers `_colores_personalizable`/`_trazo_personalizable` ya llevan stack — si se escribe otro parser, copiar ese patrón.
- **Arte por rango: la "mesa de la pieza" es POR TALLE** → cualquier código que asocie mesa↔pieza con el mapeo default solo (mesas del 1er rango) se pierde las mesas `#rango` (bug de editables sin pieza y del "primero muestra el 6XL"). Usar `mapeo_variantes_arte`/`mapeo_talles`.
- **Arte ≠ Planilla en el diseño** → el Arte edita `disenoActivo`, pero la tizada usa el diseño de la **columna "Diseño" de cada fila** de la planilla (feature multi-diseño). Si divergen — o la fila usa un diseño **sin arte** → **fallback silencioso** — la tizada NO usa lo que mapeaste. Síntoma: "mapeé pero salió en otro/un solo talle". Fix 2026-07-10 (ver changelog): la columna y el `default_diseno` arrancan con `disenoActivo`, y el fallback backend prefiere `default_diseno`.

---

## 10. Índice de endpoints (servidor.py) — los que más toco

- `GET /api/productos` · `GET /api/plantilla/deteccion[?talle_ref][&candidatas=1]` (→ `detectar_piezas`, piezas del molde; `candidatas=1` = molde ORIGINAL + capas que aún no son talle, para la herramienta de variantes por piezas) · `GET /api/plantilla/nido` (geometría nesteada).
- `GET /api/plantilla/deteccion_todas` (→ `detectar_piezas_todas`: TODAS las piezas de TODOS los talles en un lienzo + `formato`; es la vista del agrupado por selección — ver §10.c).
- `GET/POST /api/plantilla/variantes` (variantes POR CAPA) · `POST /api/plantilla/variantes_piezas` (variantes POR PIEZAS) — ver §10.c.
- `POST /api/plantilla/pieza_renombrar` (**CAMINO B**: le pone nombre a UNA pieza por `(mesa, t_idx)`; no re-arma el registro) · `POST /api/pedido/limpiar_efimeros` (borra los moldes efímeros del pedido) — ver §0.b.
- `POST /api/plantilla/grupo_pieza` (**agrupar piezas homólogas**: nombre + correspondencia entre talles en UN gesto) · `GET/POST /api/plantilla/emparejado` (el ajuste avanzado: acomodo virtual + corrección por índice) — ver §10.c.
- `GET /api/arte/deteccion?diseno=` (→ `detectar_arte`, mesas + mapeo) · `POST /api/arte/mapeo` (guarda `mapeo_arte.json` + `prod["mapeo_arte"]` fijo; corre `validar_arte_separado`; **pre-warm** de `_piezas_base` en background).
- `POST /api/arte/preview_piezas` (→ `_piezas_base`, render real cacheado por pieza).
- `GET/POST /api/productos/editables` (`get_editables`/`set_editable`) · `GET/POST /api/productos/editables_config` (tamaño).
- `GET/POST /api/productos/etiqueta*` · guía PDF (`pdf_guia`, param `piezas`=nombres de la variante).
- `POST /api/generar` (single) · `POST /api/generar_multi` (→ `generar_pedido_grupos`, multi-molde por tela). Salida a `TRABAJOS/<tid>/`. ⚠️ `generar_multi` recibe los moldes en la **lista `molds`** (que `_pid_de_request` no mira) → valida el DUEÑO **molde por molde** con un loop antes de armar nada (entrada 122).
- **FICHA TÉCNICA** (`ficha_tecnica.py`, sale junto con la tizada en `correr()` de `generar_multi`, best-effort): tabla de talles = la `planilla` que manda el front, y abajo **un molde guía por cada (molde · diseño · variable)** del pedido. Las guías se anotan en `_guias_ficha` **dentro del bucle `por_diseno`** —después del `_fallback` de arte y con `_asig_de(dslug)` ya resuelta— porque `_asig_de` es una clausura del molde en curso y en el hilo apuntaría al último. Tope `_MAX_GUIAS_FICHA` (16) con aviso. Contrato: `verificar_ficha_disenos.py` (entrada 145).
- `GET /api/productos` devuelve **`piezas_registradas`** (cuántas piezas tiene el registro, cacheado por mtime) además de `plantilla`: sirve para distinguir «molde cargado pero SIN piezas» de «molde OK». `plantilla` **no** se invirtió — un DXF entra a propósito con el registro vacío.

⚠️ **Coherencia molde-vs-variable (auditoría 2026-07-09, actualizada 2026-07-13):** el MAPEO ya es POR VARIABLE (regla dura, ver §5 y changelog 2026-07-13) — el conteo "faltan diseño" al guardar quedó acotado (`piezas_scope`). Gaps pendientes (menores): lista de mapeo en Config (`App.jsx` mapeador legacy con desplegables), `get_editables`/`get_etiqueta` devuelven `piezas: reg.keys()` (el front ya filtra los editables por variante). Global A PROPÓSITO: `detectar_arte` (las MESAS del arte son las mismas para todas), descargas de base, pantallas de Configuración.

---

## 10.b OBJETOS EDITABLES — cómo se manejan (verificado 2026-07-20; LA CAPA ES EL OBJETO 2026-07-22)

**UN SOLO ORIGEN REAL: el ARTE.** Un objeto editable vive en una capa OCG del .ai cuyo nombre empieza
con `editable` (ej. "Editable Escudo"). Las detecta `extraer_editables` →
`{mesa, capa, nombre, bbox_mu, mesa_rect, w_cm, h_cm, thumb, svg, objetos:[…]}`.

### REGLA (2026-07-22, decisión del usuario): **LA CAPA ES EL OBJETO EDITABLE**

**Todo lo que la capa «Editable …» tenga adentro se mueve / rota / escala / dimensiona JUNTO, como
una sola cosa. El COLOR sí es de cada figura por separado.**

**Por qué (investigado sobre el .ai REAL, no asumido):** el **agrupado de Illustrator NO viaja en el
archivo**. Verificado en `Diseño Short.ai`: dos elipses que en Illustrator están dentro de un
`<Grupo>` salen al content-stream **planas y consecutivas** (`q cm m c c c c f Q` ×2, mismo nivel),
sin `BDC /Figure`, sin XObject `/Group` y sin `q/Q` que las envuelva. Illustrator guarda el árbol de
grupos (y los nombres de objeto, y las **sub-capas**) en `PieceInfo→/Illustrator→/AIPrivateData*`,
que es **PGF comprimido con zstd** (`%AI24_ZStandard_Data`), formato propietario → no se puede leer de
forma confiable. **Sólo las capas de PRIMER NIVEL sobreviven como OCG.** Por eso la capa es la unidad
y no hay forma de distinguir "agrupado" de "no agrupado" dentro de una misma capa.
→ **Si el usuario quiere dos objetos que se muevan por separado, van en DOS capas «Editable …».**

**Figuras dentro de la capa (sólo para el COLOR).** `molde_real.objetos_de_capa(page, capa)` (núcleo
`_analizar_capa`) recorre el content-stream una vez con CTM+frame OCG y separa las figuras por
**firma de puntos de construcción** — relleno+trazo del MISMO trazado = una figura; figuras
CONCÉNTRICAS = figuras distintas. Cada una lleva `obj_id` (hash de la geometría, ESTABLE ante
reordenamiento), su bbox y su `fill` CMYK (lee `k` **y `scn` de 4 canales** — Illustrator pinta con
`scn` sobre un ColorSpace ICCBased CMYK: sin eso el color de la figura salía vacío).
- **Identidad (`IDENT`):** **transform/tamaño → el NOMBRE DE LA CAPA, siempre.**
  **color → `"nombre<SEP>obj_id"`** (`SEP`=U+001F; `motor_pedido.SEP`==`servidor._EDIT_SEP`);
  si la capa trae una sola figura, el color puede ir plano por nombre de capa (compat).
- **Storage:** `prod["editables"][diseno][variable][capa]["transforms"]` (de la CAPA) y
  `…[capa]["objetos"][obj_id]["color"]` (de cada figura). `_editables_cfg` aplana a
  `{variable:{capa:{talle:tf}}}` y `_editables_color` a `{variable:{IDENT:color}}`.
  **Compat:** si quedó config vieja por figura (`…["objetos"][oid]["transforms"]`) y la capa no tiene
  transform propio, `_tf_de_capa` adopta el de la primera figura con valor → lo ya movido no se pierde
  ni queda a medias. `set_editable` **ignora el `obj_id`** y guarda a nivel capa.
- **`get_editables` devuelve UN ítem por capa** (`nombre`=capa, bbox/`w_cm`/`h_cm` = **unión** de sus
  figuras) + `partes:[{obj_id, ident, label:"Escudo (i)", color, fill, recolorable, svg}]` cuando trae
  ≥2 figuras (vacío si trae una). `recolorable` de la capa = la capa o cualquiera de sus figuras.
- **Editor (front).** Clavea todo por `o.nombre` = **la capa** (`_objsUnicos`, `editableSel`,
  `editorTfs`, guardado). El panel COLOR muestra los chips de `o.partes` (miniatura SVG + punto con
  el color actual) para elegir **qué figura pintar**; guarda con `p.ident`. Estado `colorParte`
  (se resetea al cambiar de objeto). **NO reconstruir el IDENT en el front.**
- **Primitivas** (`molde_real.py`): **`aislar_capa_objetos(pdf,page,capa,colores={obj_id:(fill,stroke)})`**
  = aísla la capa ENTERA recoloreando figura por figura (lo que usa el motor cuando hay color por
  figura); `aislar_objeto` (UNA figura sola: validación/miniaturas), `suprimir_objetos`,
  `capa_admite_color_objeto`, `_reescribir_por_indice`.
  ⚠️ El recorrido por índice **sólo cataloga trazados/XObjects/shadings, no TEXTO** → sin colores por
  figura el motor sigue por `aislar_capa` (frame-based, camino verificado, respeta el texto).
- **Motor:** `pagina_arte_solo(mesa, capa, color=, obj_id=, colores=)`; `_edit_por_mesa` arma **una
  unidad por CAPA** (bbox unión + `objetos:[{obj_id,ident}]` para el color); `_colores_de(u,variante)`
  resuelve el color de cada figura (hereda el de capa si la figura no tiene); `pagina_arte_pieza` saca
  del diseño base la **capa ENTERA** cuando se redibuja (ya no parte capas a medias).
- **Verificado** (`scratchpad/verif_grupo.py`, arte sintético de 3 figuras + molde real, sólo lectura):
  redibujar la capa en identidad = **0 px** vs el diseño original; mover la capa → las 3 figuras se
  desplazan **lo mismo** (±0.5 px de centroide) y al escalar ×1.4 las 3 crecen ×1.96 en área;
  recolorear UNA figura **no toca** los píxeles de las otras (0 px); preview y HOJA coinciden dentro
  del ruido de rasterizado propio de la hoja (la misma diferencia existe SIN ninguna edición).
  Sobre el arte real (`Diseño Short.ai`, molde "Molde short"/diseño `erferg`): mesa 3 = 1 objeto de
  8.5×8.5 cm; mesa 4 = **1 objeto de 8.7×2.8 cm con 2 partes** (negra K100 y celeste C75).
- **LÍMITE:** si los N objetos están dentro de un **grupo/XObject** (un solo `Do`), se ven como 1
  objeto y no se pueden separar ni recolorear (viven adentro del XObject) — desagrupar en Illustrator.

Los objetos que **agrega el usuario** (PNG/SVG/PDF/AI desde "Editar diseño") NO son un sistema
paralelo: entran a una **sala de espera** y al COLOCARLOS se **INYECTAN en el arte como una capa
OCG más**, y desde ahí son editables del arte comunes (editor, visor, motor, tizada: sin código
especial). `objetos_agregados.py` los normaliza a **un PDF de 1 página + su tamaño en cm** (viven en
`datos/productos/<pid>/objetos_agregados/<sub>/` con `objetos_agregados.json`) y `inyectar_editable`
los escribe en el arte. Endpoints: `objeto_agregar`, `objetos_agregados`,
`objeto_agregado/<id>/{colocar,pieza,transform,duplicar}` (DELETE para borrar).

Los objetos que **agrega el usuario** (PNG/SVG/PDF/AI desde "Editar diseño") NO son un sistema
paralelo: entran a una **sala de espera** y al COLOCARLOS se **INYECTAN en el arte como una capa
OCG más**, y desde ahí son editables del arte comunes (editor, visor, motor, tizada: sin código
especial). `objetos_agregados.py` los normaliza a **un PDF de 1 página + su tamaño en cm** (viven en
`datos/productos/<pid>/objetos_agregados/<sub>/` con `objetos_agregados.json`) y `inyectar_editable`
los escribe en el arte. Endpoints: `objeto_agregar`, `objetos_agregados`,
`objeto_agregado/<id>/{colocar,pieza,transform,duplicar}` (DELETE para borrar).

**VERSIONES DEL ARTE (importante).** Inyectar **NO sobrescribe** el archivo que subió el usuario:
escribe `arte.v<N>.ai` al lado y un puntero `arte.ver` con la versión vigente. `_ruta_entrada(
"arte.ai")` devuelve **la vigente** para TODO el sistema (`original=True` fuerza el base, sólo lo
usa la subida, que además hace `reset_versiones`). Dos motivos, los dos reales: (a) el arte es un
archivo del usuario y el original queda intacto como respaldo; (b) en Windows `os.replace` falla con
**WinError 5** si cualquier proceso tiene el archivo abierto — crear un archivo nuevo no puede
fallar por eso. **Todas las mesas de un objeto se inyectan en UNA pasada = una sola versión.**

**QUITAR un objeto agregado.** `quitar_editable(arte, capa)` → escribe otra versión SIN esa capa
(saca el OCG de `/OCProperties` y borra los content streams que empiezan con `q /OC … BDC`, que son
exactamente los que escribió la inyección: no puede tocar contenido original). Endpoint
`POST /api/productos/editable_quitar`. **Sólo se pueden quitar las capas que agregó el usuario**, y
eso se decide comparando la versión vigente contra el arte ORIGINAL (`capas_agregadas`), no con un
registro aparte que se puede desincronizar. `/api/productos/editables` marca cada objeto con
`quitable`. Verificado: tras quitar, el arte queda **pixel-idéntico** al original.

**NOMBRE ÚNICO DE CAPA.** El nombre de la capa ES la identidad del editable en todo el sistema. Al
inyectar, si ya existe una con ese nombre se desambigua (`Editable Logo 2`); si no, quedan dos capas
indistinguibles y el bbox que se calcula es la UNIÓN de las dos (objeto gigante y no se lo puede
mover por separado).

**HANDLES DE PDF.** `motor_pedido` abre PDFs desde archivo con `_abrir`/`_abrir_pike`, que los
registran **por hilo** (`threading.local`), y `@app.teardown_request` llama `MP.cerrar_abiertos()` al
terminar cada request; los hilos de fondo (pre-warm) van envueltos en `_en_hilo`, que cierra al
terminar. Sin esto los documentos quedaban abiertos y **trababan el arte y la plantilla** (no se
podían reemplazar ni borrar): fue la causa real del "error al cargar una imagen" — 4 de 5 artes
estaban trabados. **El registro NO puede ser global**: el server atiende varios requests a la vez y
el teardown de uno cerraba los documentos de otro → `ValueError: document closed` en `detectar_arte`.

**DETECCIÓN DEL CONTENIDO DE UNA CAPA (gotcha caro).** `extraer_editables` ubicaba los objetos sólo
con `get_drawings()`, que **ve vectores y nada más**: una capa editable hecha con una IMAGEN (un PNG
agregado, un logo rasterizado del arte) o con TEXTO no tenía bbox y el objeto **no aparecía en
ninguna pantalla**. Se complementa con `pg.get_bboxlog(layers=True)`, que sí reporta `fill-image` /
`fill-text` con su capa. Verificado que los bboxes de los editables que ya funcionaban NO cambian.

**TAMAÑO DE UNA IMAGEN AGREGADA.** `normalizar_a_pdf` usa el **DPI real** del PNG/JPG si lo trae
(Pillow, `info["dpi"]`) y 96 dpi sólo como fallback: un PNG exportado a 300 dpi debe entrar con su
medida física, no 3 veces más grande.

**A QUÉ PIEZA PERTENECE.** Los del arte, por la mesa donde viven (`mesa2pieza`, vía el mapeo).
Los agregados, por la pieza que **elige el usuario clickeando sobre el diseño** (se guarda `pieza`).
Un objeto agregado vive en UNA sola pieza: para tenerlo en dos se **duplica** (la copia nace sin pieza).

**POSICIÓN (transform).** `{dx, dy, rot, scale, sx, sy}` — `dx/dy` en fracciones **del diseño**,
`rot` horario, `sx/sy` negativos = espejo. Se guarda **por diseño → variable → objeto → talle**:
los del arte en `prod["editables"]`, los agregados en su manifiesto. La posición base es el centro
del diseño; el tamaño sale de los cm reales del objeto contra el diseño colocado sobre la pieza.

**ALCANCE del ajuste (clave, y fuente de un bug real).** Al mover un objeto, el cambio se aplica a
**todos los talles donde SU PIEZA usa la misma mesa del arte** que el talle en vista — es decir,
donde se ve exactamente el mismo diseño (`tallesDeObjeto`). **NO** se usa el "grupo" del editor,
que se arma con la firma de TODAS las piezas: dos talles pueden mostrar el mismo diseño para esa
pieza y caer en grupos distintos (caso real: para 'Frente 1' la mesa 12 cubre 2XL,3XL,**4**,4XL,
5XL,**6**,6XL → 4 y 6 no se actualizaban). Con "Solo este talle" el cambio va únicamente a ése.

**CÓMO SE DIBUJAN (las 3 vistas deben coincidir — LEY arte = tizada).** El diseño se coloca sobre la
pieza escalando al **ALTO** y centrando el ancho (`cm_encajar`). Todos ubican el objeto como
fracciones de la **mesa del arte del talle que se está dibujando** (las mesas cambian de tamaño por
rango: en un arte real 1233x1842 el chico y 2352x2607 el grande — tomar una mesa fija produce
corrimiento):
- **Editor**: `marcoDeObjeto(o, p, aspMesa)` con `_aspMesaDe(p)` (usa `mapeo_talles`).
- **Visor del Arte**: el mismo `marcoDeObjeto` con la mesa de su `mappedMesa`. OJO: si existe el
  render del motor (`pv`) se muestra ESE y no se dibuja overlay.
- **Motor**: `pos_agregado_en_diseno(obj, cont, mesa_rect)` con `arte_rect(_mesa_a)` + `_matriz_editable`.
  Los del arte se aíslan de la capa y se redibujan con `cm_encajar`/`cm_tamano_editable`.

**TAMAÑO.** Config por molde `editables_config` (caja máx. por rango, apaisado/vertical, o
"mantener"). Los agregados hoy conservan su **tamaño real en cm** en todos los talles.

**CACHÉ.** El preview por pieza (`_piezas_base`) se cachea en disco; su clave
(`_piezas_base_clave`, **v7**) incluye plantilla, arte, mapeo, borde, etiqueta, editables_cfg,
editables_tamano, el manifiesto de objetos agregados, el registro **y el COLOR override de
editables** — sin esto, cambiar el color de un editable no regeneraba el render y "no se veía".

**COLOR override de un editable (CMYK, POR VARIABLE — HECHO 2026-07-22).** Un editable del arte se
puede **recolorear** sin tocar su forma ni el resto del diseño. Se guarda **por diseño → variable →
objeto** (a NIVEL OBJETO, no por talle: el color es del objeto), JUNTO a los transforms:
`prod["editables"][diseno][variable][nombre]["color"] = {"fill":[c,m,y,k]|null, "stroke":[c,m,y,k]|null}`
(null en un canal = no tocar ese relleno/trazo; `color` ausente = color original del diseño). CMYK
EXACTO, sin re-cuantizar (sublimación).
- **Primitiva** (`molde_real.recolorar_capa`): recorre el content-stream y DENTRO del frame OCG de la
  capa objetivo inyecta el color (`k`/`K`) antes de cada op de relleno/trazo, sin borrar estado (no
  desbalancea `q`/`Q` ni hereda colores a otras capas).
- ⚠️ **GOTCHA (orden):** `aislar_capa`/`_raspar_pintado` BORRAN los marcadores BDC/EMC → hay que
  **recolorar ANTES de aislar** (página fresca, marcadores presentes). El color inyectado sobrevive
  al aislado (se conserva el contenido de la capa objetivo). Lo respeta `pagina_arte_solo(mesa, capa,
  color=…)` en el motor, cacheado por `(mesa, capa, color)`.
- **Motor** (`generar_pedido(..., editables_color={variable:{objeto:{"fill":…,"stroke":…}}})`): un
  objeto con color en CUALQUIER variable entra a `_coloreados_nombres` → se SUMA a `_redibujar_nombres`
  → el diseño base lo EXCLUYE (`suprimir_capas`) y se **redibuja recoloreado** (mismo camino que los
  editados/con-tamaño). El color se resuelve por variable con `_color_de(nombre, variante)` (fallback
  `"*"`). Sin `editables_color` (o vacío) → comportamiento **idéntico** a antes (compat verificada 0 px).
- **Recoloreable o no** (`molde_real.capa_admite_color` / `motor.editables_recolorables`): sólo las
  capas con relleno/trazo DIRECTO. Si el objeto pinta vía **XObject (`Do`)** o imagen (ej. un objeto
  AGREGADO por el usuario), el color vive adentro y `recolorar_capa` no lo cambia → el editor muestra
  el control **deshabilitado** con una nota. `get_editables` devuelve `recolorable` y `color` por objeto.
- **Storage/endpoint:** `POST /api/productos/editable_color {pid?, diseno, nombre, variante, color}`
  (color `null` = LIMPIAR = volver al original). Helpers servidor: `_clamp_color`, `_editables_color`.
- **Preview = tizada:** `_piezas_base` pasa `editables_color=_editables_color(prod, diseno)` al motor
  igual que la tizada (verificado: mismo color en el escudo, dif ≤1 canal SVG-vs-PDF).
- **Editor (front):** panel COLUMNA "COLOR" del objeto seleccionado (1 solo) — swatch, presets CMYK,
  4 campos C/M/Y/K (0–100), "↺ Volver al color original". Guarda con `guardarColorEditable` (POST +
  invalida `_pvCache` — el color NO está en `_pvKeyCon` — + recarga editables + refresca el preview).

## 10.c NOMBRAR VARIANTES (talles) — DOS MODOS: por capa y por piezas

**El talle de una pieza sale del NOMBRE DE LA CAPA** (`_talles_de_plantilla`). Hay dos moldes rotos
distintos y la herramienta (`variantes_molde.py`, UI `NombrarVariantes` en Config → Moldería) tiene
**un modo para cada uno**; el modo se sugiere solo (`modo_sugerido` del `GET /api/plantilla/variantes`:
`piezas` si hay <2 capas candidatas o si ya existe una asignación guardada) y el usuario lo puede
cambiar a mano con el selector **Por capa / Por piezas**.

### Modo POR CAPA (el molde trae una capa por talle, sin nombrar)

Un molde exportado de
un CAD puede venir con capas `Layer 1`, `Capa 3`: el sistema detecta 20 "talles" con esos nombres y
**0 piezas**, y el molde es inusable. Se resuelve así:

- `analizar(plantilla)` → `{formato, capas[], sugerencia, total_talles}`. **`formato`**: `anidado`
  (los talles están dibujados UNO ENCIMA DEL OTRO — gradación de Optitex, el caso más común: no se
  pueden separar con el mouse, se nombran POR CAPA) o `extendido` (cada talle en su bloque). Se
  decide midiendo cuánto se solapan los bbox de dos talles.
- **La curva se propone ordenando por ÁREA** — verificado contra un molde real de 20 talles:
  reproduce el orden exacto. Por *ancho medio* NO sirve: `16` y `XS` empatan (1127.3 los dos, son
  dos curvas distintas que se tocan); por área se separan sin ambigüedad.
- `renombrar_capas(plantilla, mapa)` escribe una **VERSIÓN nueva** (`plantilla.v1.ai` + puntero
  `plantilla.ver`, la misma maquinaria que el arte): el archivo del usuario queda intacto.
- Endpoints `GET/POST /api/plantilla/variantes` (aceptan `pid`); el POST además **rehace el
  registro** leyendo la versión nueva. UI: componente `NombrarVariantes` en Config → Moldería.

**Por qué se renombra el archivo y no se traduce al vuelo:** se probó un alias `{capa: talle}`
aplicado en la lectura, y hay que traducir en CADA punto que compara capas por nombre — incluido
`molde_real._candidatos_mesa` (compara `d["layer"] == talle`), que de olvidarse deja al motor **sin
piezas al generar la tizada**. Renombrando, el resto del sistema no se entera de nada.

### Modo POR PIEZAS (el molde trae TODAS las piezas en UNA capa)

Caso real (`Molde short`): 36 piezas en «Capa 1». Ahí **no hay capas que nombrar**: el usuario
**selecciona piezas en el visor** (clic o recuadro) y les escribe el nombre de la variante en
**texto libre** (`S`, `38`, `Talle único`, `Niño 4`).

- **El archivo SE PARTE, no se anota.** `VM.separar_por_piezas(plantilla, {pieza_idx: variante})`
  escribe una **versión nueva** con **una capa (OCG) REAL por variante**. Guardar sólo "la pieza 3
  es del talle S" en el registro **no sirve**: el talle se resuelve por nombre de capa (mismo
  motivo que arriba) y el motor se quedaría sin piezas.
- **Cómo parte el content stream** (`_unidades_de_trazado`): se recorre instrucción por
  instrucción llevando la CTM, se agrupa en unidades `construcción… + operador de pintado`, cada
  unidad se empareja por **centro de bbox** con la pieza de `extraer_piezas_mesa` (en el molde real
  la distancia dio **0.00**) y se envuelve en su propio `/OC /MCx BDC … EMC`.
  - El `BDC` va **pegado al trazado** (después del `q … cm`, antes del `Q`) → nunca se cruza con el
    anidado `q/Q`, y el estado gráfico compartido (clip `W n`, ancho de línea, `/GS`) queda **fuera
    de toda capa**: apagar una variante no rompe el dibujo del resto.
  - Los trazados de **clip** (`W n`) NO se meten en ninguna capa. Las piezas **sin asignar** se
    re-marcan con la capa **original** (no se pierde nada del archivo).
  - Verificado: render del PDF partido **pixel-idéntico** al original (0 de 20.5M px).
- **Orden de la curva**: las capas nuevas se crean de **menor a mayor área** (mismo criterio ya
  verificado del modo por capa) → ese es el orden que después lee `_ordenar_por_archivo`.
- **El registro se rehace con `alta_plantilla_manual`** sobre el archivo partido: talle de
  referencia = la variante con más piezas, y las homólogas de los otros talles salen de
  `_emparejar_por_forma`. Si las piezas todavía no tienen nombre se usan **provisorios estables**
  (`Pieza 1`…) para que el registro exista y el molde se pueda seguir configurando; el editor de
  nombrado los reemplaza después. Los nombres que YA existían se recuperan **por `bbox_mu`** (la
  geometría no cambia al partir), así corregir la asignación no borra el nombrado.
- **Endpoints**: `POST /api/plantilla/variantes_piezas {pid?, asignaciones:{idx: nombre}}` y
  `GET /api/plantilla/deteccion?candidatas=1`. La asignación cruda queda en
  `datos/productos/<pid>/variantes_piezas.json` para poder reabrir y corregir.
- 🟢 **GUARDADO AUTOMÁTICO del borrador (2026-07-21)** — antes la asignación **sólo** se escribía
  dentro del POST caro: el usuario asignaba piezas, salía sin apretar «Aplicar» y **perdía todo**
  (y encima el botón le quedaba al final de una lista larga, así que no lo encontraba).
  - **`POST /api/plantilla/variantes_piezas_borrador {pid?, asignaciones}`** persiste **sólo** la
    asignación cruda (escribe un JSON, ~10 ms medidos): NO parte el PDF ni rehace el registro.
    El front lo dispara **en cada cambio** de `varPzAsig`, con 500 ms de respiro (debounce).
  - **`variantes_piezas.json` ahora tiene dos campos**: `asignaciones` = lo que el usuario viene
    armando (borrador) y **`aplicadas`** = copia de lo que EFECTIVAMENTE se partió. Distintos ⇒
    queda trabajo **pendiente de aplicar**. ⚠️ Los archivos **viejos** no tienen `aplicadas`: ahí
    lo guardado **es** lo aplicado (antes sólo se escribía al aplicar) — tanto el GET como el
    endpoint de borrador siembran `aplicadas` desde `asignaciones` en ese caso, si no un molde ya
    partido figuraría como pendiente para siempre.
  - `GET /api/plantilla/variantes` devuelve **`asignacion_piezas`** (borrador) y
    **`asignacion_piezas_aplicada`**; el front carga las dos (`varPzAsig` / `varPzAplicado`).
  - **UI**: barra **`position: sticky`** arriba del panel con el estado del guardado
    (`varPzEstado`: guardando / ✓ guardado / ⚠ error) y el botón **Aplicar al molde**, que ya no
    vive al final de la lista. Deshabilitado si no hay pendiente («Aplicado al molde ✓»).
    El acordeón de `NombrarVariantes` **se abre solo** si hay borrador sin aplicar (`pzPend`) y
    muestra el chip «guardado · falta aplicar» en el encabezado.
  - ⚠️ El autoguardado compara con `varPzUltimo` (ref, serialización con claves ordenadas) y se
    **resetea a `null` al cambiar de molde**: si no, el borrador del molde nuevo se compararía con
    el del anterior. Al CARGAR desde el server también se siembra esa ref, para que abrir la
    herramienta no dispare un POST inútil.
- ⚠️ **`candidatas=1` lee el molde ORIGINAL** (`_ruta_entrada(..., original=True)`) y acepta capas
  que todavía no son talle. Leer el original es lo que mantiene **estables los índices de pieza**:
  si leyera la versión ya partida, la segunda vez mostraría sólo las piezas de un talle y la
  asignación guardada no se podría corregir nunca. Y `POST` siempre parte **desde el original**
  (`OA.reset_versiones`), si no se acumularían capas de intentos anteriores.
- **UI**: el panel vive dentro de `NombrarVariantes` como `children` (necesita el visor, que vive en
  `App`). **Reusa el visor y el gesto del nombrado de piezas**: `startDrag` → `toggleSelNombrar`,
  marquee `iniciarRubber` → `addSelNombrar`, todo condicionado por el estado `varPzModo`
  (`varPzAsig`, `varPzInput`). Al activar el modo se recarga `etqData` con `candidatas=1`.
- **Límite conocido**: se trabaja sobre **una** mesa+capa (la que concentra más piezas). Un molde
  con el bloque repartido en varias mesas no está contemplado.

#### 🔴 EL ESTADO DEL MOLDE NO SE LEE DE LA DETECCIÓN QUE MUESTRA EL VISOR (2026-07-21)

La vista `candidatas=1` lee el **archivo original**, que **siempre** va a tener una sola capa
llamada «Capa 1» (partir escribe una versión nueva; el original no se toca nunca). De ahí salían
tres cosas que **no son del molde sino de esa vista**, y por eso un molde ya terminado se mostraba
como recién subido:

- `talle_ref = "Capa 1"` → el panel **«{Variante} de guía · Actual: Capa 1»** y el encabezado del
  visor **«Mesa: 1 · Capa: Capa 1»**.
- `sin_variantes = true` → el cartel naranja **«El molde se cargó, pero todavía no se puede usar…
  vino con todas las piezas en una sola capa»**.
- `talles = ["Capa 1"]` → el modal de talle de guía y todo lo que lista variantes.

**Y encima el modo se activaba solo**: `NombrarVariantes` hacía `onModo(true)` con sólo existir una
asignación guardada (`yaPorPiezas`) — o sea **siempre**, para todo molde definido por piezas —, y
`activarVarPz` recarga `etqData` con `candidatas=1`. Resultado: al abrir la Moldería de un molde
terminado el visor pasaba a la vista del archivo sin separar **con el panel plegado**, sin que el
usuario pidiera nada.

**Cómo quedó:**
- `GET /api/plantilla/deteccion` devuelve, además de la detección, el **estado del MOLDE**:
  **`talles_reales`** (los del registro, en orden de archivo, vía **`_talles_reales(pid)`** — sale
  de los JSON y no del PDF: `_talles_de_plantilla` hace un `get_drawings()` entero), **`resuelto`**
  (bool) y **`guia`** (la variante de guía que hay que mostrar). Si `resuelto`, se fuerzan
  `sin_variantes = False` y `falta_nombrar_variantes = False`.
- **Auto-corrección de los moldes ya guardados con la guía mal**: si `variante_guia` está puesta y
  ya no existe entre las reales, el propio GET la corrige (`_ajustar_variante_guia`) — se arregla
  sola al abrir el molde. ⚠️ **Sólo si está puesta**: con `variante_guia = None` («automática») el
  sistema elige solo, y escribirle una acá le cambiaría el talle de apertura a moldes que andan bien
  (`prod_default` es ese caso).
- `GET /api/plantilla/variantes` devuelve **`resuelto`**; el encabezado del acordeón usa
  `sin_talles && !resuelto` (`faltaNombrar` en `NombrarVariantes`), y cuando está resuelto muestra
  «✓ N variantes definidas: XS · S · M…».
- En `App.jsx`: **`tallesMolde`** (= `talles_reales` si vienen, si no `talles`) reemplazó a
  `etqData.talles` en **todo** lo que habla de las variantes del molde (rangos de medida, planilla,
  modal de guía, precarga del emparejado…). El botón de guía muestra `etqData.guia` y queda
  **deshabilitado mientras dura el modo por piezas** (cambiarla recargaría el visor con los índices
  de la versión partida y rompería la asignación en curso). El encabezado del visor dice qué está
  mostrando: «todas las piezas, sin separar» / «todas las variantes juntas» / «Talle: M».
- `onModo(true)` ahora sólo se dispara si **el acordeón está abierto** o si de verdad falta algo
  (`faltaNombrar || pzPend`).

### AGRUPAR PIEZAS HOMÓLOGAS — el camino principal (Config → Moldería, «La misma pieza en cada talle»)

El nombre de una pieza se pone UNA vez, en el talle guía, y se **propaga** al resto con
`_emparejar_por_forma` (posición relativa normalizada + log-aspecto + log-área, greedy global,
umbral 1.6). Si el molde no viene acomodado parecido entre talles, esa comparación **no tiene
señal** y el nombre cae en la pieza equivocada.

**El gesto que ve el usuario es UNO solo: «seleccioná las que son la misma pieza, escribí qué es».**
Con eso queda definido a la vez **cómo se llama** y **cuál es la misma pieza en cada talle** — no hay
«emparejar», ni offsets, ni índices. (El panel anterior, que pedía reacomodar y corregir por
número de pieza, fue **rechazado por el usuario por difícil**; sigue existiendo escondido como
«Ajuste avanzado ▸» — funciona y está verificado, no se borra.)

🟢 **TODAS LAS VARIANTES JUNTAS (2026-07-21) — el flujo principal de hoy.** El paso intermedio
(elegir un talle con chips, tocar una pieza, nombrarla, y después confirmar la homóloga talle por
talle) **también fue rechazado**: «no es intuitivo; es más fácil mostrar las piezas de TODOS los
talles y seleccionar las que son la misma y ponerle el nombre — es la misma función que nombrar».
Se hizo literal:

- **`MP.detectar_piezas_todas(path)`** (motor_pedido) — las piezas de **todos** los talles en UN
  lienzo, mismo sistema de coordenadas (mm) y **misma geometría** que la vista de a un talle: el
  armado del path salió a **`_item_visor(cont, idx, clip, cb, U, zoom)`**, compartido por las dos
  (si cada una lo armara por su cuenta, la misma pieza se vería distinta según desde dónde se mire).
  La mesa la elige **`_mesa_principal`** (la que más trazos de talle concentra — mismo criterio que
  `detectar_piezas`, si difirieran las dos vistas mirarían páginas distintas).
  Cada pieza trae **`talle`** + **`t_idx` = su índice DENTRO de ese talle, que ES el `pieza_idx` del
  registro**; `idx` es un correlativo global que sólo sirve como identidad en el visor.
- **`GET /api/plantilla/deteccion_todas`** (acepta `pid`). Devuelve además **`formato`**. Caché en
  disco `deteccion_cache/<mtime>_TODAS.json` (medido: 3.0 s la 1ª vez con 6 talles, **17 ms**
  después). ⚠️ El `formato` se mira **ANTES** de extraer: en un molde `anidado` esta vista no se usa
  y sacar las piezas de los 20 talles para tirarlas costaba segundos (`prod_default`: ahora **90 ms**).
- **Molde `anidado` → NO se muestra junto** (los talles están dibujados uno encima del otro: sería
  ilegible). El front cae al flujo de a un talle y **lo dice en una línea** (`empTodasMotivo`).
  Mismo camino si la vista junta cayera en **otra mesa** que el emparejado (los `pieza_idx` son
  relativos a la mesa: apuntarían a piezas que no son).
- **El backend NO cambió**: el gesto entero ya entraba por `POST /api/plantilla/grupo_pieza`
  (`nombre` + `guia_idx` + `piezas {talle: idx}`). Lo que cambió es que ahora el usuario los elige
  **todos de una** y quedan **confirmados a mano** (en `manual`) en el mismo POST.
- **UI** (`App.jsx`): estados `empTodas` / `empTodasData` / `empTodasMotivo`. **Reusa el visor**:
  `canvasLayout` toma `empTodasData` en lugar de `etqData` cuando el modo está activo (única línea
  que cambia la fuente), y la selección sigue siendo `selNombrar` + `toggleSelNombrar` +
  `iniciarRubber` (el marquee anda porque filtra por el atributo `data-piece`, que es el idx global).
  - El nombre de cada pieza **no puede salir de `etqNombres`** (es el de UN talle): se arma
    `empTodasInfo` = `{nom, fijo}` por `(talle|t_idx)` desde `empData.asignacion`/`manual`, **una vez
    por render**. Cada pieza muestra su **variante** encima del número y el nombre del grupo debajo,
    con el color del grupo (mismo color = misma pieza en todos los talles).
  - `crearGrupoTodas()` valida **antes** de guardar y lo dice en el panel: **2 piezas del mismo
    talle** (rojo, bloquea), **falta la pieza del talle guía** (bloquea: el nombre se guarda ahí),
    **faltan talles** (naranja, NO bloquea: ahí queda la propuesta del sistema).
  - `revisarPiezaEnTalle` en esta vista **no cambia de talle** (están todos): deja `empFijar` y el
    clic se resuelve por `(talle, t_idx)` con **`fijarPiezaTodas`** (usar `fijarPiezaEmp` acá
    guardaría el índice GLOBAL como si fuera el del talle → correspondencia rota).
  - `seleccionarGrupoTodas(nombre)` marca en el visor las N piezas de un grupo ya hecho.
  - Al cambiar de molde se limpian `empTodas/empTodasData/empTodasMotivo` (es geometría de ESE molde).

- 🟢 **RÓTULOS QUE NO SE PISAN (2026-07-21).** Cada pieza dibujaba su chapita (círculo con el número
  + la variante arriba + el nombre abajo) **en su centro**, siempre. En este molde las piezas de una
  misma fila están **encimadas**: los centros quedan a 115 mm, que a «Ver todo» son **14 px** — dos
  círculos de 22 px y dos textos uno sobre otro («2XL 2XL», «XL XL»). Medido sobre el molde real:
  **12 pares de círculos a menos de 24 px y 36 pares de textos a menos de 60 px**.
  - `canvasLayout` calcula **`sep`** = distancia de cada pieza al centro más cercano (unidades del
    viewBox). `sep × visorView.k` = **píxeles de pantalla disponibles**, que es lo único que decide
    si un rótulo se lee. Umbrales: **`LBL_MIN_PX = 24`** (el círculo mide 22) y **`TXT_MIN_PX = 60`**
    (los textos son mucho más anchos que el círculo).
  - Debajo de `LBL_MIN_PX` la pieza queda con un **punto** de su color de estado (sigue clicable, con
    su tooltip); entre `LBL_MIN_PX` y `TXT_MIN_PX` va el círculo con el número, sin textos. La pieza
    **elegida/resaltada muestra siempre todo** (`forzado`). Acercando el zoom vuelven solos.
  - El **nombre de la variante va UNA vez por bloque** (`canvasLayout.clusters`, bbox de las piezas
    de cada talle; en el modo «por piezas» el bloque se arma con lo que el usuario lleva asignado):
    36 rótulos de talle → **6**.
  - Aviso en la esquina del visor: «N sin rótulo · acercá el zoom» (`rotulosOcultos`), para que la
    falta de números no parezca un error del sistema.

### LA BARRA DE CAPAS (columna izquierda del visor) — estilo Illustrator

Vive **fuera** del visor, en su propia columna de **208 px** (`gridTemplateColumns` del
`workspace-container`), y aparece en dos pantallas: **Moldería → Nombrar piezas** (`empModo &&
empTodas`) y **Etiqueta** (`tabAjustesMolde === 'etiqueta'`). Fila por capa (= talle):

| tik | 👁 | nombre | ▸ |
|-----|----|--------|---|
| selección (**abre la fila**, pedido 2026-08-21) | ojito, con **arrastre en cadena** (`pintaOjo`: apretar y pasar por encima aplica el mismo modo) | doble click = **renombrar la capa** (`POST /api/plantilla/variantes_nombrar`) | despliega las piezas (**20×22 px**, al final de la fila) |

La fila de la capa **no lleva miniatura**; las de sus piezas (al desplegar ▸) sí, y su tik abre la
fila igual que el de la capa — los dos caen en la **misma columna**. Lo mismo en «Ver piezas».

- **Encabezado**: el **ojo GENERAL** (`toggleTodasCapas` — si hay alguna visible las apaga todas y
  limpia la selección, misma regla que el ojito de a una; si estaban todas apagadas, las prende) y
  el indicador de lo seleccionado (cantidad al nombrar; el nombre de la pieza en Etiqueta).
- **Miniaturas** (`MiniCapa`): el **mismo `path_svg` que dibuja el visor** — no hay un segundo
  dibujo que pueda diferir; cada una en su propio bbox (`miniPzVB`).
  🔴 **Son de UNA pieza, nunca de un grupo (2026-08-21).** La fila de la CAPA junta 34 piezas
  distintas: el dibujo combinado no identificaba nada, así que se sacó (con él se fue el memo
  `capasMini`, que existía sólo para eso). Mismo criterio en «Ver piezas»: la fila lleva miniatura
  **sólo si agrupa una única figura** («Tapa costura» = 1 pieza × 30 talles sí; «Cuello» = 11 formas
  distintas, no — dibujar la primera sería mentir).
- 🔴 **EL TIK (`TikSel`) NO TIENE ESTADO PROPIO.** Lee y escribe la selección **de la pantalla**:
  `selNombrar` (múltiple) al nombrar, y `etqPiezaSel` + `etqPzTocada` en Etiqueta (`capasSelModo`,
  `pzEstaSel`, `togglePzSel`). Con estado propio, el panel y el visor mostrarían cosas distintas.
  Estados: **lleno** (todo), **parcial** (algo), **vacío**.
- 🔴 **Qué selecciona cada cosa (2026-08-21, regla del usuario):** el tik de la **CAPA** = sus
  piezas de una (`toggleCapaSel`; en Etiqueta, donde la selección es de a UNA, queda **informativo**,
  sin click). **DENTRO de una capa, la selección es INDIVIDUAL**: tanto el tik como el NOMBRE de la
  pieza eligen **sólo ésa** (`togglePzSel`) — tocar «Frente 1» en el talle 0 no toca los frentes de
  los otros talles. **No hay** «seleccionar el grupo» desde la barra (el `toggleGrupoNombre` que lo
  hacía se eliminó): el **grupo** vive en la lista «Ver piezas» del panel, que trabaja por nombre.
  Todo es **toggle**: el mismo gesto pone y saca.
- En Etiqueta el tik **lleno** es la pieza **dueña** de la etiqueta (`etqPzTocada`) y las otras del
  mismo nombre quedan en **parcial** — se ve de un vistazo sobre cuál se está trabajando.
- La lista **«Ver piezas»** del panel derecho (nombrar) tiene el mismo trato: miniatura (si aplica) +
  tik que selecciona/quita el grupo por nombre genérico. Es la otra lista con ojitos del sistema y no
  puede comportarse distinto.

### 🔴 EL GESTO DE SELECCIÓN EN EL VISOR (Moldería → Nombrar piezas)

**CLICK = UNA pieza. ARRASTRE = muchas.** Regla del usuario (2026-08-21), y es la que manda:

- **Click sin arrastrar sobre una pieza** → se elige **sólo la de ADELANTE** (la capa más alta de
  la barra), **sin importar cuántas tenga debajo**. Lo mismo para el click corto que entra por el
  fondo (`iniciarRubber`): toma `bajo[0]`, no la pila.
- **Arrastrando con el botón izquierdo** (>3 px) se pintan varias y ahí sí **cada punto se lleva
  todo lo apilado** (`_piezasBajoPunto`, una vez por arrastre vía el set `tocadas`). El botón
  **derecho sigue moviendo el lienzo** — elección explícita del usuario al preguntarle.
- **Recuadro** (marquee) desde el fondo, y **agarre** (click quieto 350 ms) para mover la selección:
  sin cambios.
- ⚠️ El toggle del arrastre **exige `pintaSel.current.movio`** (el umbral de 3 px): si no, un
  temblor de 1 px convertía el click de una pieza en «las 30 apiladas» y el gesto nuevo no existía.
- **Por qué cambió**: la pila entera al primer click venía de que el clic caía en la pieza
  EQUIVOCADA (el z-order estaba invertido, ver abajo) y hacía falta agarrar todo para llegar a la
  que se quería. Con el apilado ya arreglado, el click preciso alcanza. (Historia: changelog 200 y
  198 documentan el gesto anterior — quedan como registro, no como la regla vigente.)

### 🔴 DOS PIEZAS CON EL MISMO NOMBRE EN UNA VARIABLE: SÓLO SI «VAN JUNTAS» (2026-08-21)

**Regla del usuario:** en una variable **no pueden convivir dos piezas que se llamen igual**
(mismo nombre GENÉRICO: «Cuello 9» y «Cuello 10»), **salvo** que estén declaradas como **«van
juntas»** (ej. manga + su vivo). Y eso se declara **antes**, al configurar el **GRUPO**.

- **El vínculo vive en el GRUPO** (`prod["grupos"][].juntas = [{id, nombre, piezas:[idx]}]`), no en
  la variante. Se declara una vez y **lo heredan todas las variables de ese grupo**: al elegir una
  de las piezas para una variable, **la compañera entra sola** (`togglePiezaEnTipo` /
  `agregarPiezasATipo` expanden por el vínculo).
- **Compat sin migración:** los moldes viejos guardaron el vínculo dentro de la variante
  (`prod["variantes"][].juntas`). Se leen **los dos lados** (`juntasDeVariable` en el front;
  grupo ∪ legacy en `_traducir_prendas`), y borrar uno lo saca de donde esté. Nada se migra a la
  fuerza — un molde ya configurado sigue andando igual.
- **Dónde está el botón**: en el **detalle del grupo** («⛓ Piezas que van juntas · ＋ Vincular
  piezas»), debajo de «Elegir piezas del grupo». En la **variable** quedó sólo la **lectura** («se
  definen en el grupo») para que se entienda por qué al tocar una pieza entran dos.
- 🔴 **EL NOMBRE ES UN LUGAR, NO UN ERROR (2026-08-21, corrección del mismo día).** Elegir otra
  pieza del mismo nombre **reemplaza** a la que estaba: sale «Cuello 9», entra «Cuello 10». **Uno
  u el otro, sin ningún cartel** — el primer intento tiraba un aviso rojo de rechazo y el usuario
  lo bajó enseguida: *«cuando selecciono una pieza no debe salir ese cartel; si selecciono un
  frente y después el otro, se deselecciona el anterior»*. Elegir el otro frente es **cambiar de
  frente**, no equivocarse.
  - Si la pieza que sale está en un vínculo, **sale el vínculo entero** (es atómico).
  - Con el **recuadro** entra **una por nombre** y **no se pisa** lo que el usuario ya había
    elegido (para cambiar de pieza se la toca: ahí sí reemplaza). Sin carteles.
  - `_desplazadasPorNombre` es quien decide qué sale; el toggle de siempre (tocar una elegida la
    saca) no cambió.
- Un molde configurado ANTES puede tener el choque ya guardado: el detalle de la variable lo
  **muestra** (aviso naranja con las piezas y la salida), no lo borra solo.
- ⚠️ **Ojo con la historia**: la «regla del slot» (un solo nombre genérico por variable) se había
  **eliminado** en 2026-07-28 por descartar piezas **en silencio** (ver el comentario en `App.jsx`
  y la memoria `bug-renumerado-nombres-piezas`). Lo que vuelve **no es aquella regla**: aquella era
  automática e invisible; ésta es **del usuario**, explícita, avisada y con una salida clara
  (vincular). El backend **no rechaza** nada: si rechazara, un molde viejo con el choque guardado
  no se podría ni abrir para arreglarlo.
- **Contrato**: `verificar_juntas_grupo.py` (raíz) — vínculo en el grupo, vínculo legacy en la
  variante, los dos a la vez, y que `POST /api/productos/grupos` conserve el campo.

### AGREGAR UNA PIEZA AL MOLDE — qué pasa con todo lo demás (estado a 2026-08-21)

`POST /api/plantilla/pieza_agregar` (Config → Moldería → «Agregar una pieza»): **⧉ duplicar la
elegida** o **subir un archivo**, marcar en el visor dónde va, **prepararla**, y **Guardar**.

🔴 **LAS TRES REGLAS DEL USUARIO (2026-08-21)** — mandan sobre cualquier diseño anterior:

1. **Nada se escribe hasta «Guardar».** Las piezas quedan **PREPARADAS** en la pantalla (`pzPend`,
   fantasma ámbar en el visor, ✕ para sacarlas): el molde no se toca. «Mientras no se guarda podés
   hacer lo que quieras». Todas las preparadas se guardan **juntas, en UNA sola versión**.
2. **Lo guardado NO se borra.** No hay «deshacer» (el endpoint `pieza_deshacer` **se eliminó**, y
   con él el contador `piezas_agregadas`): para sacar una pieza **se borra el molde entero** y se
   sube de nuevo. El modal de Guardar lo dice antes de escribir.
3. **Duplicar copia los VECTORES respetando los talles.** En cada talle se copia la geometría de la
   **HOMÓLOGA** (`_homologas`, que la resuelve por el REGISTRO), **no** la del mismo número — el
   número no se corresponde entre talles. **El nombre y el número NO se heredan**: entra como pieza
   nueva y sin nombre. Si la pieza a duplicar todavía **no tiene nombre** no hay correspondencia:
   se cae al mismo índice y **se avisa** (en el panel y en la respuesta).

- Se escribe una **VERSIÓN** (`plantilla.v<N>.ai` + `plantilla.ver`): **el archivo del usuario no
  se toca**.
- La pieza entra en **TODOS los talles**. Duplicando, cada talle copia **su** geometría (acompaña
  la progresión); por archivo se exige **una forma por talle** (menor→mayor área ↔ orden del
  molde) y si no, **422** con el motivo. Una pieza que existiera sólo en algunos talles deja el
  registro con un hueco y **la generación explota**.
- 🟢 **NO RENUMERA NADA.** La geometría se agrega **al final** del contenido de la capa
  (`page.contents_add`) y las piezas se leen en **orden de dibujo** → la nueva es **la última** de
  cada talle. Medido con `verificar_agregar_pieza.py` sobre el molde real: **0 de 2760** entradas
  cambian de índice (con el orden viejo por bbox eran 69 de 138). El remapeo del registro sigue
  corriendo igual, como red.
- Por eso **nada de lo configurado se desalinea**: registro, `piezas.json` (ids), variables
  (`pieza_idx` + `pieza_id`), grupos y sus `juntas` (índices), `emparejado_talles.json → manual`
  (índices), etiqueta / telas / arte / `acomodo_mm` (todos por NOMBRE) quedan como estaban.
  ⚠️ Esa tranquilidad **depende del orden de dibujo**: si alguna vez se vuelve a ordenar por
  posición, grupos, juntas y `manual` **sí** se corren y hoy **nadie los remapea** (sólo el
  registro). Es el primer lugar a mirar si aparece un nombrado corrido.
- La pieza nueva queda **SIN NOMBRE** a propósito: se nombra como cualquier otra. Después hay que
  **sumarla al grupo** y **a las variables** que la lleven (y darle **tela** y **arte** si el molde
  los usa, o la traba del pedido la va a frenar — que es lo que tiene que pasar).
- Se invalidan las cachés derivadas (`_invalidar_cache_molde`: detección, nido en memoria y disco,
  `piezas_cache`, toggles): el archivo vigente pasó a ser otro y ninguna se invalida sola.

#### ⚠️ LO QUE ESTA MANERA PUEDE ROMPER — auditoría 2026-08-21

Los 1, 2, 3 y 7 quedaron **CERRADOS** el mismo día con las reglas del usuario (ver arriba); los que
siguen abiertos están marcados. Se deja la lista entera: el motivo de cada arreglo importa tanto
como el arreglo.

1. ✅ **CERRADO — «Sacar la última pieza agregada» podía borrar una versión que NO era una pieza.**
   `get_productos` manda **`piezas_agregadas = OA._ver_actual(plantilla.ai)`** — o sea **el número de
   VERSIÓN**, no cuántas piezas se agregaron. Pero la plantilla la versionan **también**
   `variantes_molde.renombrar_capas` (nombrar los talles) y `separar_por_piezas` (partir el molde),
   con el mismo mecanismo. Un molde al que sólo se le nombraron los talles muestra «Sacar la última
   pieza agregada (1)», y tocarlo **borra el archivo vigente** (`os.remove`) y baja el puntero: el
   molde vuelve a «Capa 1» y **se queda sin talles**, con el registro apuntando a talles que ya no
   existen. Demostrado con `_ver_actual` sobre un temporal. Hoy **latente**: los 4 moldes del
   usuario están en `.ver = 0`. **Plan:** que el alta de pieza deje su marca (p. ej.
   `prod["piezas_agregadas"] = [{version, cuando}]`) y que el botón y `pieza_deshacer` miren ESO,
   no el contador de versiones; si la versión vigente no es de una pieza, 409 con el motivo.

2. ✅ **CERRADO — «Duplicar la elegida» copiaba por ÍNDICE en todos los talles.** `pieza_agregar` toma el `i`
   del talle guía y en cada talle copia `antes[t][i]`, o sea **asume que el índice es la misma
   pieza en todos los talles** — que es exactamente lo que NO siempre pasa (por eso existe el
   emparejado). Medido sobre los moldes reales: «Camiseta de futbol» **0 de 986** entradas con
   índice distinto al de la guía (ahí acierta), pero «camiseta asque» tiene **1**: «Frente 2» es
   `M#2` y `0#1` → duplicando ese frente, en el talle «0» se copiaría **otra pieza**, y sale así
   impreso. **Plan:** resolver la homóloga por el REGISTRO (`registro[nombre][talle].pieza_idx`)
   cuando la pieza tiene nombre, caer al índice sólo si no lo tiene, y avisarlo en el panel.

3. ✅ **CERRADO (ya no hay deshacer) — restauraba el registro de ANTES de agregar** (`.antes_pieza`), así que **se pierde
   todo el nombrado hecho entre agregar y deshacer** — y el flujo natural es agregar → nombrar →
   «no era» → deshacer. **Plan:** al deshacer, conservar lo nombrado que no sea de la pieza que se
   saca (fusionar por nombre), o avisar en el modal qué se va a perder.

4. 🟠 **ABIERTO — Archivo subido con contornos de más: «se usan los N más grandes», en silencio.** Guías,
   marcas o texto convertido a curvas pueden entrar como pieza. **Plan:** mostrar los contornos
   detectados con su medida y que el usuario confirme cuáles son.

5. 🟠 **ABIERTO — Una pieza por debajo del mínimo detectable** (`area_min_cm2=0.25`, `lado_min_cm=0.3`) se
   escribe en el molde pero **no se detecta**: queda una versión nueva y nada visible. **Plan:**
   medir el contorno antes de escribir y rechazar con el motivo.

6. 🟠 **ABIERTO — La copia es geométricamente IDÉNTICA a la original** → `_emparejar_por_forma` puede cruzar
   los nombres entre las dos si quedan cerca. Se salva nombrándolas con el gesto de agrupar (queda
   en `manual`, que manda sobre la heurística), pero conviene avisarlo.

7. ✅ **CERRADO — `resumen_plantilla.json` no se actualizaba**: ahora el alta le suma las piezas
   guardadas, así el conteo de la pantalla de estado deja de mentir.

8. 🟡 **ABIERTO — Multi-mesa**: `remapear_registro` aplica el mapa de un talle a TODAS las entradas de ese
   talle sin distinguir mesa. Hoy inocuo (el mapa es la identidad); volvería a importar si el orden
   dejara de ser el de dibujo.

9. 🟡 **MITIGADO — Disco**: cada **guardado** deja una copia completa del molde, pero ahora todas
   las piezas preparadas entran en **una sola** versión (antes era una por pieza).


### 🔴 ELEGIR LAS PIEZAS DE UNA VARIABLE VA SOBRE **UN** TALLE (2026-08-21)

`canvasLayout` usa el **lienzo junto** (`empTodasData`, todos los talles) cuando hay una variable
abierta… **salvo mientras se eligen las piezas** (`asignandoTipo`), que vuelve a **`etqData`** = el
talle **guía** o el que el usuario eligió con los chips «Resaltar talle».

**Por qué (bug real, reportado por el usuario):** las piezas del grupo se guardan con el
`pieza_idx` **del talle guía**, y `aisladoSet` filtra el lienzo por esos índices. En el lienzo
junto los índices son un correlativo **global**, así que esos números caen en el **bloque del
PRIMER talle** (el «0»): el usuario creía estar tocando la guía y estaba eligiendo sobre otro
talle. Peor: lo elegido se guardaba con `talle_origen` = el talle de `etqData`, o sea el índice de
un talle traducido contra **otro** — si el orden de piezas no coincide entre esos dos talles, la
variable quedaba con **piezas equivocadas**.

- El **encabezado del visor** sigue la misma condición (decía «todas las tallas juntas» mientras
  mostraba una sola: mentía).
- `asignandoTipo` va en las **dependencias del memo** — si no, el cambio de fuente no se recalcula.
- Al terminar («Listo») vuelve solo al lienzo junto para acomodar.
- ⚠️ No lo introdujo el z-order de la 258: el filtro es por índice, no por profundidad. Es un bug
  **viejo** que se hizo evidente ahora.
- **Verificado**: con la variable abierta y «Cargar piezas», el `d` del path de la pieza 7 en el
  DOM es **idéntico** al que devuelve `GET /api/plantilla/deteccion` para el talle guía (M) y
  **distinto** del bloque del talle «0» del lienzo junto; tocando el chip «XL» pasa a coincidir
  **exacto** con `?talle_ref=XL`; y al salir vuelven las 210 piezas (7 × 30) del lienzo junto.

### ACOMODAR UNA VARIABLE — mover VARIAS piezas juntas (Variables → variable abierta)

Con una variable abierta el visor muestra **sus piezas con todos los talles nesteados** y sirve
para **acomodarlas**. El modo es `modoAcomodoVar` (= variable abierta y **ninguna** herramienta de
asignación en curso: con una activa el clic es para asignar, no para mover).

🔴 **Acá el OBJETO que se mueve es el NOMBRE, no la pieza suelta**: «una pieza de la variable» son
sus ~30 talles, que se acomodan **juntos** y se guardan por nombre en **`acomodo_mm`**. Por eso
seleccionar una la selecciona **entera** (`toggleSelVarNombre` marca todos sus talles).

- **Click sin arrastrar** = selecciona/quita esa pieza (entera). Se resuelve en `endDrag` con
  `varAcomodo && !hasMoved`, porque el mousedown ya armó el arrastre.
- **Recuadro desde el fondo** = togglea las abarcadas, también por nombre entero (`iniciarRubber`
  con `modoAcomodoVar`; el marquee **expande cada idx a su nombre** antes de togglear).
- **Arrastrar una pieza QUE ESTÁ en la selección** = se mueven **todas las seleccionadas juntas**
  (`dragInfo.varNombres` con los N nombres; `inis` con los idx de todos sus talles).
- **Arrastrar una pieza que NO está en la selección** = se mueve **sólo ella** (lo de siempre); la
  selección **no se pierde** — un arrastre no debería borrar lo que el usuario venía marcando.
- **Una sola escritura por gesto**: al soltar, `guardarAcomodoVarMm` recibe **todos** los nombres
  movidos de una (todas las piezas de un nombre comparten el mismo offset, así que alcanza con
  leer el de la primera).
- La selección se **limpia al abrir y al cerrar** una variable (el mismo efecto que siembra
  `pzOffsets` desde `acomodo_mm`): si sobreviviera, la variable siguiente arrancaría con piezas
  marcadas que ni están en el visor.
- Reusa `selNombrar` a propósito: es la misma selección del resto del visor, con el mismo gesto —
  no hay un segundo estado que pueda desincronizarse.

- 🔴 **ORDEN DE APILADO DEL VISOR = LA BARRA DE CAPAS (2026-08-21).** La capa de más ARRIBA en la
  barra de talles es la que va más **ADELANTE**, igual que en Illustrator. En SVG no hay `z-index`:
  manda **lo último pintado**, así que el orden del DOM es el z-order — y el navegador entrega el
  clic al que está adelante. `canvasLayout` devuelve **DOS listas de las mismas piezas**:
  - **`layout`** = orden LÓGICO (adelante primero, el orden de `src.talles` = el de
    `_ordenar_por_archivo`, que sale de `doc.layer_ui_configs()` = el panel de capas del .ai).
    Lo consumen los **hit-tests por bbox** (`piezaBajoMouse`, el fallback de `_piezasBajoPunto`,
    `alinearSeleccion`…): toman el **primer** match, o sea la pieza de adelante.
  - **`dibujo`** = el mismo conjunto AL REVÉS por bloque de talle (`sort` estable: dentro de una
    capa el orden relativo del archivo no se toca). Es lo que se pinta — **los 4 `.map()` de render
    del visor usan `canvasLayout.dibujo`, nunca `layout`**; `MapeadorArteVisual` hace lo propio con
    `piezasZ` (los CARTELES se siguen ubicando con `piezas`, en orden lógico: el acomodo greedy
    depende del orden y no tiene por qué cambiar por esto).
  - **Dónde se nota**: molde **ANIDADO** (los 30 talles dibujados uno encima del otro, el caso de
    `prod_default` y de «Camiseta de futbol»). Antes el último talle de la lista tapaba a todos y
    se quedaba con cada clic; ahora el talle chico (arriba de la lista) está al frente.
  - ⚠️ Si algún día se agrega otro visor que dibuje piezas, tiene que salir de `dibujo`. Y si el
    orden lógico cambiara (p. ej. reordenar capas a mano), `layout` y `dibujo` se derivan los dos
    de `src.talles`: hay UN solo lugar que decide.
  - **Por qué esta salida y no otra**: mover la etiqueta al borde de cada pieza no alcanza (las
    piezas se solapan casi enteras, los bordes también se tocan) y esconder todo detrás del hover
    deja la pantalla muda. Ocultar **por falta de lugar real** es el criterio de los mapas: al zoom
    de «ver todo» se lee el bloque (la variante), al acercarse aparecen las piezas — y **la vista de
    UN talle no cambia en nada** (ahí siempre hay lugar).
  - Verificado renderizando el bloque **recortado literalmente de `App.jsx`** con `react-dom/server`
    (`scratchpad/armar_visor_test.py` + `scratchpad/verif_visor.mjs`, geometría real del molde):
    ver el CHANGELOG para los números.

- **Endpoint único: `POST /api/plantilla/grupo_pieza`**
  `{pid?, nombre, guia_idx, piezas?: {talle: idx|null}, renombrar_de?, eliminar?}`.
  - `nombre` + `guia_idx` → entra al **nombrado del talle guía** (la misma entrada de
    `alta_plantilla_manual`) → la heurística propaga el resto.
  - `piezas` → lo que el usuario **confirmó a mano**: se guarda en `emparejado_talles.json`
    → `manual` (el mecanismo que ya existía; `_aplicar_fijos` corre **después** de todo).
    Lo que NO confirma queda con la **propuesta** automática, y la UI los distingue.
  - `eliminar` deshace el grupo (le saca el nombre a la pieza guía **y** sus fijos).
  - **Nombre repetido → 409**, no se renumera por atrás: el usuario cree que puso «Frente» y
    el registro le dejaba «Frente 2» (colisión de nombres, ver `nombres_normalizados`).
  - ⚠️ La clave de `manual` es el nombre **FINAL** (el que va a quedar en el registro), no el
    tipeado: por eso `alta_plantilla_manual` delegó su renumerado en
    **`MP.nombres_normalizados(asignaciones)`**, que ahora se puede llamar aparte. Al
    agregar/quitar/renombrar un grupo, las claves de `manual` se **remapean** (viejo→nuevo) o
    la corrección a mano quedaría huérfana en silencio.
- **Backend compartido**: `_guardar_y_repropagar(pid, cfg, asign=)` — persiste el ajuste y
  **re-arma el registro** (+ `resumen_plantilla.json` + `piezas.json`). Lo usan el endpoint
  nuevo y el viejo `POST /api/plantilla/emparejado`; guardar sin re-armar no sirve (el
  emparejado se resuelve al CONSTRUIR el registro).
- **UI** (`App.jsx`, `empVista === 'simple'`, el mismo visor y la misma selección de siempre):
  chips de talle para elegir **qué muestra el visor** (la guía primero, con ★); en la guía va el
  input de nombre; en otro talle, seleccionar una pieza + desplegable «Esta pieza es…».
  Cada grupo se pinta con **su color** (`colorGrupo`, hash del nombre → mismo color en todos los
  talles) con el nombre encima y **✓ = confirmado por el usuario**. La lista de grupos muestra
  una fila de chips por talle: **★ guía · ✓ violeta = confirmado · gris = propuesto por el
  sistema · ! naranja = ninguna pieza le tocó**; tocar un chip abre ese talle esperando el clic
  (`revisarPiezaEnTalle` → `empFijar`). «Confirmar todo» fija la propuesta de todos los talles.
- **Por qué de a UN talle y no todos juntos**: el formato más común es **`anidado`** (los talles
  dibujados uno ENCIMA del otro, §10.c) → mostrarlos a la vez es un amasijo ilegible; y el visor
  renderiza la detección de **un** talle (`etqData`). Mostrar de a uno con las ya resueltas
  pintadas es lo único que se lee. El costo (no ver todos juntos) se compensa con la
  **pre-selección**: el sistema ya propone la homóloga en cada talle y el usuario sólo confirma.
- **Fix de paso**: el marquee (`iniciarRubber`) NO se disparaba en este panel — su condición sólo
  contemplaba la pestaña Variables. Ahora incluye `empModo`.
- 🟢 **LO YA HECHO SE VE SIN ENTRAR AL MODO (2026-07-21)** — los grupos **siempre** se guardaron en
  el momento (cada confirmación pega contra `POST /api/plantilla/grupo_pieza`), pero al volver a la
  Moldería el panel arrancaba plegado y **vacío**: el usuario creía que había perdido el trabajo.
  Ahora, al abrir la pestaña **Moldería** de un molde con >1 talle se **precarga**
  `GET /api/plantilla/emparejado` en silencio (`cargarEmparejado(true)`, sin `showError`) y el panel
  cerrado muestra **«✓ N piezas ya agrupadas (guardado)»** con los chips de cada nombre.
  Precargar `empData` con `empModo === false` es seguro: todo lo que lo consume en el visor está
  detrás de `if (empModo && empTalle)`.
- Los fetch de emparejado/grupo ahora mandan **`pid` explícito** (antes iban sin él y dependían del
  activo de la sesión).
- 🟢 **PANEL REDISEÑADO POR USABILIDAD (2026-07-21)** — con 36 piezas la lista era ilegible: una fila
  por grupo con los MISMOS chips de todos los talles + un «Confirmar todo» en cada una, nombres
  provisorios («Pieza 2, Pieza 3…») que no dicen nada, y **ningún número global**. Ahora:
  - **Encabezado de progreso** (`empStats`, se calcula una vez por render y lo comparten el panel
    abierto y el resumen plegado): «N de TOTAL piezas agrupadas · M confirmadas», barra de dos
    capas (agrupado en accent, confirmado en violeta) y **una** línea de estado que dice el
    **primer obstáculo real** (faltan por agrupar → sin correspondencia en algún talle → nombres
    provisorios → «ya podés seguir»). `TOTAL` = piezas del talle GUÍA (`empGuiaPzs`).
  - **«Confirmar todo» global**: UN solo `POST /api/plantilla/emparejado` **sin `talle`** con el
    diccionario `manual` COMPLETO (ese endpoint, sin `talle`, reemplaza `cfg["manual"]` entero) →
    una sola re-propagación del registro. Fila por fila eran N clics y N re-armados del registro.
    ⚠️ No mandar `acomodo` en ese POST: sin `talle`, un `acomodo` dict **reemplaza** el guardado.
  - **Miniatura de la pieza** en cada fila (`miniPieza`): el `path_svg` del talle guía recortado a
    su bbox. La geometría se pide una vez (`cargarPzsGuia`, misma detección que ya usa el visor,
    sale de `_talleDetCache`) al cargar el emparejado.
  - **Filas compactas y una sola abierta** (`empAbierto`): los chips por talle + «Confirmar esta
    pieza» + «Deshacer» viven en el detalle. Filtro **Pendientes / Listas / Todas** (arranca en
    pendientes; «pendiente» = le falta un talle, o no está confirmada, o el nombre es provisorio)
    y buscador si hay >8 grupos.
  - **Renombrar desde la fila** (`renombrarGrupo` → el mismo `grupo_pieza` con `guia_idx` +
    `renombrar_de`): ya no hay que ir a buscar la pieza en el visor. El **provisorio** (`Pieza N`,
    `esNombreProvisorio`) se muestra en itálica gris con «✎ poner nombre».
  - ⚠️ **`colorGrupo` devuelve `hsl(...)`, NO hex**: pegarle un sufijo de alfa (`${col}55`) da un
    color **inválido** (bug que ya existía en los chips del resumen). Para transparencia va
    `colorGrupoA(nombre, a)` (hsla) o `fillOpacity`.
  - Verificado con render real del bloque (`react-dom/server` sobre el JSX extraído de `App.jsx`)
    + prueba de API punta a punta contra el server real (crear/confirmar-todo/renombrar/borrar/
    salir y volver) con un molde de prueba descartable.

### Ajuste AVANZADO (reacomodar / corregir por índice) — escondido, no borrado

Dos salidas más, en el MISMO visor (botón «Ajuste avanzado ▸» dentro del panel):

1. **REACOMODAR.** El usuario selecciona piezas (clic, o recuadro con `iniciarRubber`) y las
   **arrastra** hasta dejar ese talle dispuesto como el guía. Es **virtual**: `_bboxes_acomodadas`
   corre la caja **sólo** para calcular los rasgos del emparejado. **NO mueve nada del archivo ni
   de la tizada** (la ley «el arte se ve igual que la tizada» queda intacta).
2. **CORREGIR.** Para una pieza ya nombrada se dice a mano «en este talle es la #N».
   `_aplicar_fijos` la mete **después** de todo (heurística *y* correspondencia del DXF), y le
   quita ese índice a quien lo tuviera. **Una corrección a mano no se pisa nunca con lo
   automático.** La pieza que perdió el índice queda «sin emparejar» y se corrige igual.

- **Persistencia**: `datos/productos/<pid>/emparejado_talles.json` =
  `{"acomodo": {talle: {idx: [dx_mm, dy_mm]}}, "manual": {talle: {nombre_pieza: idx}}}`.
  Los offsets van en **mm** (las coords del visor son mm: `detectar_piezas` dibuja a `zoom=1/MM`).
- **Guardar no alcanza**: el emparejado se resuelve **al construir el registro**, así que el POST
  guarda **y re-arma el registro** con `alta_plantilla_manual` releyendo los nombres del talle
  guía (`_guia_y_asignaciones`) — sin volver a pedirle nada al usuario.
- **Lo consumen los 3 caminos** que emparejan: `alta_plantilla_manual`, `nido_piezas` y
  `remapear_registro` (re-subida del molde). Todos reciben `emparejado=`; el servidor lo pasa
  desde `_emparejado_cfg(pid)` en **los 5 llamados** (subida de plantilla, `/api/plantilla/etiquetas`,
  `/api/plantilla/variantes_piezas`, el nido y el propio endpoint).
- **Endpoints**: `GET /api/plantilla/emparejado` (guía, talles, `nombres_guia`, `asignacion`
  `{talle:{nombre:idx}}`, `acomodo`, `manual`) y `POST /api/plantilla/emparejado`
  `{pid?, talle, acomodo?, manual?: {nombre: idx|null}, reset?: 'acomodo'|'manual'|'todo'}`.
- **CACHÉS que había que tocar** (media feature si no): `_nido_clave` sube a **v6** e incluye el
  mtime de `emparejado_talles.json`; y `_piezas_base_clave` sube a **v6** e incluye el mtime del
  **registro** — una pieza es un NOMBRE y qué geometría tiene ese nombre en cada talle sale del
  registro, así que re-emparejar (o re-nombrar) dejaba el render cacheado del Arte apuntando a la
  pieza vieja. Ese agujero ya existía para `/api/plantilla/etiquetas`.
- **UI**: `App.jsx`, estados `empModo/empVista/empData/empTalle/empFijar` (+ `empNombreInput`,
  `empGrupoSel` del modo agrupar). Reusa el visor entero: `startDrag`
  (arrastre en grupo con `dragInfo.inis`; clic sin movimiento = `toggleSelNombrar`; **en
  `empVista==='simple'` el arrastre está apagado**: ahí el gesto es sólo seleccionar),
  `iniciarRubber` y `pzOffsets`. ⚠️ `pzOffsets` se **borra en cada cambio de `etqData`**: el efecto que lo re-siembra
  desde `empData.acomodo` va declarado **después** de ese reset (los efectos corren en orden de
  declaración) — al revés, cada recarga perdería el reacomodo.
- **Límite conocido**: las correcciones se guardan por `(talle, idx)`. Si el molde se vuelve a
  **partir** por piezas (`variantes_piezas`) los índices pueden moverse; los que queden fuera de
  rango se ignoran, pero conviene rehacer el ajuste.

**MOLDE ACTIVO — ya no es global.** `_get_active_producto_id()` resuelve por orden: (1) `pid` de la
request, (2) el activo **de la sesión**, (3) el global del catálogo. Antes era sólo (3), un único
campo compartido: dos usuarios subiendo su molde a la vez **se pisaban los archivos**. Con esto
todos los endpoints que usaban el activo aceptan `?pid=` sin tocarlos uno por uno. `_pid_de_request`
acepta `pid`/`producto_id` y **no** `id` (en varios endpoints `id` es otra cosa).

## 10.d MI PROPIO MOLDE / "Mis artículos" (espacio del cliente dentro del pedido)

El cliente puede traer **su** molde y usarlo en el pedido sin pasar por el setup del catálogo.

- **Paso «Diseños» del pedido** (`App.jsx`, `pedidoPaso === 'moldes'`): dos pestañas
  (`pedidoTabMoldes`) — **Catálogo** (las VARIABLES de los moldes compartidos, `varsCatalogo`) y
  **Mis artículos** (los productos con `propio === true`, como tarjetas de MOLDE + tarjeta «+»).
  Botón **«Subir mi propio molde»** también en la barra inferior.
- **Alta**: modal → `POST /api/productos/crear {nombre, propio:true}` → `POST /api/plantilla`
  multipart con `archivo` + **`pid`** (nunca depende del molde activo) → entra a la config.
- 🔴 **`creado_por` = AUTORÍA · `propio` = PRIVACIDAD. NO son lo mismo** (2026-07-29). `propio` en
  `GET /api/productos` sale de la **marca `propio`** que dejó el alta, NUNCA del dueño: `creado_por`
  lo lleva **toda** moldería creada con sesión —incluidas las del catálogo, que se cargan desde
  Configuración—, así que mirarlo a él mandaba a "Mis artículos" (y **le escondía al resto de los
  usuarios**) los moldes que son de todos. Helper: **`_es_privado(prod)`** = `propio and creado_por`.
  Lo reportó el usuario: *«un molde que cargué desde configuración quedó como mi artículo cuando es
  para todos los usuarios que entren»*. El permiso `molde.ver_todos` lo dice con todas las letras:
  «ver también **los moldes propios** que subió cada usuario».
- **La config NO se duplica**: se entra a la MISMA pantalla de Config → Moldería por deep-link
  (`setActivoTab('config')` + `setAdminSubView('productos')` + `handleActivarProducto(pid)` +
  `setMolderiaAbierta(pid)`), con el estado **`modoMiMolde`** = pid. Ese modo: (a) saca **Variables**
  del menú de "Ajustes de la moldería" (quedan los otros 9), (b) cambia «⬅ Molderías» por
  **«← Volver al pedido»**, (c) en **Moldería** agrega **«Indicar qué es cada pieza →»**, que abre el
  MISMO editor de nombrado (que vive en `tabAjustesMolde === 'variables'` + `varStep === 'nombrar'`)
  con el selector de pasos 1/2/3 oculto. **Se reusa todo: no hay pantallas nuevas de config.**
- **Un molde propio NO tiene variables** (ese paso se le recorta) → en el pedido se elige **ENTERO**
  y el motor genera **todas** sus piezas (fila sin `__variante`, camino que ya existía).
  ⚠️ Por eso el paso **Arte** dejó de navegarse sólo por variable: `itemsArteDe(did)` devuelve
  `[…variables elegidas, …moldes elegidos sin variable]` y **`arteIdx` recorre ESA lista**
  (antes `disenoVars[did][arteIdx]` → un molde sin variable no tenía pantalla de arte).
  `toggleVarEnDiseno` **conserva** los moldes enteros al recalcular `disenoMoldes` (si no, tocar
  cualquier variable los borraba).
- **Botón de ayuda `Ayuda` (Config → Moldería, 2026-07-22):** el panel de Moldería mostraba
  **sólo herramientas**; toda explicación de texto vive detrás de un pequeño **«?»** al lado del
  título de su herramienta. Componente **reusable `<Ayuda ancho={N}>texto</Ayuda>`** (en `App.jsx`,
  arriba de `NombrarVariantes`): globo por **`createPortal` + `position:fixed`** (no lo recorta
  ningún contenedor con overflow, mismo criterio que el desplegable de `ComboCell`), se cierra al
  clic afuera / scroll / resize, `stopPropagation` en el click para no disparar el control de atrás.
  El header del acordeón de `NombrarVariantes` pasó de `<button>` a `<div role="button">` **sólo**
  para poder anidar el «?» (botón dentro de botón es HTML inválido). Los avisos de **estado/error**
  («El molde se cargó pero todavía no se puede usar», «N de M piezas agrupadas», «✓ Guardado
  automático», validaciones rojas/naranjas) **NO** se tocaron: son feedback, no explicación.

### 🔴 DOS TRAMPAS QUE YA COSTARON (2026-07-21) — leer antes de tocar este flujo

**1. La sesión se cae en cada reinicio del server y el front NO vuelve a pedir el catálogo.**
`app.secret_key` es **aleatoria** si no está `TIZADA_SECRET` (servidor.py:30) → reiniciar el server
invalida la cookie de sesión. Y `GET /api/productos` **oculta** los moldes con dueño a quien no
está identificado (`_puede_ver_molde`). El agujero: **`App` se monta ANTES del login** (la pantalla
de login se devuelve al final del render, con todos los hooks ya corridos), así que
`fetchProductos()` del `useEffect(…, [])` sale **sin sesión** y trae **un solo molde**; al loguearse
nadie lo volvía a pedir → `productosCat` quedaba trunco **para toda la sesión**: "Mis artículos"
vacío y la guarda del front («si ya existe un artículo con ese nombre, re-usalo») sin nada que
encontrar. Resultado real: **4 artículos «Molde short»** de una sola subida.
- **Arreglo (a)**: `useEffect(… , [yo?.id])` en `App.jsx` re-pide catálogo/estado/piezas al iniciar
  sesión.
- **Arreglo (b), el que no depende del navegador**: **`POST /api/productos/crear` es IDEMPOTENTE
  para `propio:true`** — mismo dueño + mismo nombre ⇒ devuelve el artículo que ya existe
  (`{"reusado": true}`) y lo activa, en vez de crear otro. Una guarda que vive sólo en el cliente
  no es una guarda.
- `crear_producto` ahora deja el molde nuevo activo **también en la SESIÓN** (`_activar_en_sesion`):
  `_get_active_producto_id` mira la sesión **antes** que el global, y quedaba apuntando al anterior.

**2. Todo guardado del flujo de configuración manda `pid` EXPLÍCITO — sin excepción.**
Los endpoints que no lo reciben escriben en el molde **activo**, y el activo NO es necesariamente el
que se está configurando: `handleActivarProducto(pid)` es **async y no se espera** al abrir la
moldería, y la sesión se resetea sola (punto 1). Con varios artículos del mismo nombre eso terminaba
guardando **el nombrado de piezas en el molde equivocado** (reproducido: `POST
/api/plantilla/etiquetas` sin `pid` **reemplaza el registro entero** del activo).
- En `App.jsx` hay **`pidCfg`** = `molderiaAbierta || modoMiMolde || productosCat.activo` (el molde
  que se está configurando, se setea **sincrónico**) y el helper **`qPid(sep)`** para las URLs de
  GET. Lo usan: `deteccion`, `deteccion_todas`, `etiquetas`, `nido`, `medidas_variantes`,
  `pdf_guia`, `variantes`, `variantes_piezas(_borrador)`, `emparejado`, `grupo_pieza`, `config`
  (GET y POST), `arte/mapeo`, `arte/deteccion`, `arte/perfil`, `arte/preview_piezas`,
  `arte/asignar_todo`, las **subidas** (`/api/plantilla` y `/api/arte`, `pid` en el FormData),
  `variante_guia` y la clave de `localStorage` del talle guía.
- **No alcanza con el endpoint obvio**: la clave de los cachés del front (`_talleDetCache`,
  `_pvCache`) también se arma con ese pid — si la URL y la clave no salen del mismo lugar, se
  muestra el render de otro molde.
- La tarjeta de «Mis artículos» muestra la **fecha de creación** cuando hay **dos artículos con el
  mismo nombre** (si no, son idénticas y no hay forma de saber en cuál se venía trabajando).

## 10.e AYUDA GUIADA — cómo decide avanzar (y por qué NO mira el DOM)

**Motor `frontend/src/tutor.jsx` · explicaciones `frontend/src/diccionario.js` · anclas `data-tour` en `App.jsx` · los tutoriales los GRABA el usuario (§11 changelog 317).**

- ⛔ **DOS COSAS DISTINTAS, Y NO SE MEZCLAN** (decisiones del usuario, entradas 118 y 121):
  - **UN solo PASO A PASO: «Armar una tizada»**, calcada del video `Como cargar un pedido.mp4` que
    grabó el usuario — ese video es la referencia de qué es "lo correcto". Pide acciones y las
    verifica contra el estado real.
  - **21 RECORRIDOS EXPLICATIVOS** («para qué sirve cada cosa») para el resto de las pantallas:
    llevan `explica: true`, **todos** sus pasos son `accion: 'ver'` y **ninguno** declara `hecho`.
    No le piden nada a la persona. El chequeo del build lo exige.
  El botón Ayuda abre el menú con esa separación a la vista, y permite **retomar** lo interrumpido.
- **El motor lee el ESTADO REAL.** `App.jsx` arma **`ayudaEstado`** (buscar ese nombre; está junto a
  `arteEnPedido`) con lo del PEDIDO que la app ya calcula para sus propios carteles: diseños,
  diseños sin prenda, artes cargadas, piezas sin tela, filas, si hay tizada lista.
- **Un paso avanza por `hecho(E, E0)` o por el DOM, nunca por los dos.** Si el paso declara `hecho`,
  ESO manda: `E` es el estado de ahora y `E0` la **foto al empezar el paso** (permite pedir «que
  AUMENTE» en vez de «que haya alguno»). Consecuencias buscadas:
  - un **POST que falla** (ej. `grupo_pieza` → **409** por nombre repetido) no mueve el estado ⇒ el
    tutorial **no avanza** (antes seguía contento con el clic);
  - los **gestos del visor** son `accion: 'gesto'` y **no avanzan por tiempo** (antes eran `'ver'`);
  - si `hecho` ya da true al entrar, el paso **se saltea**.
- **Redes de seguridad:** «Seguir igual» a los 5 s si el ancla no aparece; «Ya está, seguir» a los
  15 s si `hecho` no se cumple. Y globo **final** («¡Listo!» / «Esto ya estaba hecho») en vez de
  cerrarse de golpe. El progreso se guarda en `localStorage` (`tizada_ayuda_progreso`) → **retomar**.
- ⛔ **CONTRATO VERIFICADO EN EL BUILD:** `frontend/verificar_diccionario.mjs` corre en `npm run build`
  (y suelto con `npm run guias`) y **corta** si una guía apunta a un ancla inexistente o si un
  predicado explota/miente. **Contempla las anclas dinámicas** (`data-tour={'ajuste-' + item.id}`) y
  las condicionales: un chequeo ingenuo da **9 falsos positivos**.
- **Al agregar o mover un control de la UI**: poner/actualizar su `data-tour` y revisar el guion que
  lo usa. Antes esto se rompía **en silencio** (el usuario veía «No encuentro ese lugar» a los 5 s).
- ⛔ **EL PEDIDO ES UN WIZARD: el botón de VOLVER es de la PANTALLA, no del destino.** `RUTAS` tiene
  entradas **función de `donde`** (`rutaDe`): desde la planilla se vuelve con **`planilla-volver-arte`**
  («← Arte»), desde resultados con **`resultados-volver-planilla`**, y el retroceso encadena de a un
  paso. Una tabla fija marcaba «← Diseños» (que sólo existe en Arte) y terminaba **teletransportando**
  al usuario fuera de su pedido (entrada 117). A **`resultados` no hay ruta**: se llega generando.
- ⛔ **`requiere(E)` es obligatorio** en toda guía cuyo paso haga `ir` a un paso del pedido que no sea
  `moldes`: si no se cumple, la guía **no arranca** y explica qué falta, en vez de dejar al usuario en
  una pantalla vacía. Lo verifica `verificar_guias.mjs` y **corta el build**. (Hoy la única guía
  arranca en `moldes` y no lo necesita; la regla queda como guarda para la próxima que se sume.)
- ⛔ **EL RESALTE VA POR AFUERA DEL CONTROL, NUNCA POR ADENTRO.** Nada de sombras `inset` en el
  recorte: se dibujan DENTRO del hueco = **encima del botón** y lo dejan tapado con un velo (entrada
  119). Aro + resplandor externos, y listo.
- ⛔ **EL GLOBO NUNCA SE PONE ENCIMA DEL ELEMENTO RESALTADO.** La cuenta es una función pura en
  **`frontend/src/tutor_pos.js`** (`ubicarGlobo`) — se **mide** el globo (no se supone su alto) y se
  prueba DEBAJO → ARRIBA → AL COSTADO → achicarlo al hueco. El chequeo del build barre **8556
  combinaciones** de pantalla/botón/alto y exige 0 solapamientos.
- ⛔ **EL GLOBO SE MIDE POR `scrollHeight` (alto NATURAL), NUNCA POR EL ALTO RENDERIZADO.** Con
  `box-sizing: border-box` (regla global de la app) el `maxHeight` que se le pone cuando no entra
  hace que el alto renderizado SEA el hueco → medir eso hace que «ya entre» → se saca el tope →
  no entra → … **React #185, «Maximum update depth exceeded»** (entrada 120). El
  `useLayoutEffect` va **con lista de dependencias**, no en cada render.
- ⛔ **EL AVANCE POR CLIC VIVE EN UN REF, NO EN UNA VARIABLE DEL EFECTO.** El botón que se toca suele
  CAMBIAR DE PANTALLA (ej. «Cargar el arte») → aparece un puente → cambia `paso.ancla` → el efecto se
  re-monta y su cleanup **cancelaba el avance en camino**: el tutorial quedaba clavado pidiendo volver
  al paso anterior. Con el ref sobrevive; no puede pisar de más porque `avanzarDesde` sólo avanza si
  seguimos en el MISMO paso (entrada 118).

## 11. CHANGELOG (lo que voy tocando — mantener al día)

- **2026-09-07 (394) — SEGUNDOS, NO MINUTOS: la carga del molde con diseño 56 → ~8 s y la tizada de
  5 prendas 51 → ~15 s.** Pedido del usuario: «cargar `CAMISETA JUGADOR.ai` demora 1 minuto; buscá
  todos los caminos para que sean segundos y milisegundos; y la tizada de 5 tardó 45 s». Estudio
  completo (caminos, pros/contras, medidas) en `MOLDE_CON_DISENO.md` «SEGUNDOS, NO MINUTOS».
  **Medido antes** (servidor 8051, 2026-09-07 9:16): subida `POST /api/plantilla` 25 s (contornos
  de 9 mesas con 6 procesos: 16 s de pared, todo atado a la mesa 2) + páginas por talle 31 s en
  segundo plano; pedido de 5 prendas 51 s = motor 21 (hoja 6, previews 8, validar 6) + aplanado
  RIP 15 + perfil/verificación/ficha 15.
  **La carga** (`piezas_con_diseno.py`, `servidor.py`):
  · 🔴 **`get_cdrawings` en vez de `get_drawings`** (`_dibujos`): mismo resultado, crudo (tuplas).
    Medido: mesa 2 de 9,0 s a 2,2 s — **7 de los 9 s eran PyMuPDF envolviendo en `Point`/`Rect`
    los miles de puntos del DISEÑO**, que el alta no mira (sólo quiere los recortes del talle).
    `_rect_de` devuelve `fitz.Rect`; `_items_objetos` convierte SÓLO el trazado elegido de cada
    pieza (lo que espera `molde_real._contorno_de_drawing`). Verificado: 180/180 contornos
    (9 mesas × 20 talles) byte a byte iguales a los de `get_drawings`. `TIZADA_DIBUJOS_LEGACY=1`
    vuelve. Contornos de las 9 mesas: 39 → 12 s en serie; **16 → 5 s en paralelo**.
  · **Contornos por sello** (`desplegar_mesa`, `_json_vigente`): con `contornos=True` se rehacían
    SIEMPRE aunque `m{mesa}.json` fuera de ese archivo (el alta repetida costaba 16 s por nada).
  · **Caché por hash del archivo** (`servidor._cache_desplegado_tomar/_guardar`,
    `datos/desplegado_cache/<sha1>_v394/`): el mismo archivo subido otra vez (re-subir, otro
    molde con el mismo .ai) copia el desplegado COMPLETO (contornos + páginas) y el `alta`
    guardado; el sha1 de 123 MB cuesta 0,2 s. Se guarda cuando `_prewarm_desplegado` termina las
    páginas; quedan los últimos 6 archivos distintos (~120 MB cada uno). El sello sigue valiendo
    porque al temporal se le pone la fecha con la que se armó la caché (`os.utime`). ⚠️ Cambiar
    el formato del desplegado exige subir `_CACHE_DESPL_VERSION`.
  · **Procesos del alta = mesas** (`_procesos_alta`: núcleos − 1, tope 12; antes `procesos_render`
    = 6 → 9 mesas en dos tandas). `TIZADA_PROCESOS` manda.
  **La tizada** (`hoja_pike.py`, `aplanar_rip.py`, `motor_pedido.py`, `verificar_rip_compatible.py`,
  `servidor.py`):
  · **Bases marcadas `/TizadaBase`** (`xobject_base`): nacen de una página desplegada sin capas
    y con sus fuentes declaradas → el aplanado (`_aplanar_un_nivel`) no las re-parsea (sólo les
    saca `/OC`/`/Group`) y `validar_salida.caminar` no las chequea. Aplanado 15 → 4 s; validar
    6 → 0 s.
  · **Hoja intermedia sin comprimir** (`componer_hoja_pike`: `compress_streams=False`): el
    aplanado la vuelve a escribir igual. Escribir el PDF 6 → 0 s. ⚠️ Por eso
    `verificar_hoja_compartida.py` mide el peso DESPUÉS de aplanar.
  · **SVG de cada base cacheado en disco** (`svg_base_cacheado`, `desplegado/svg/<clave>.svg`).
    🔴 La clave NO puede llevar el nombre del XObject: `page.add_resource` lo genera AL AZAR y la
    caché no acertaba nunca (27 SVG nuevos por corrida). Previews 8 → 3 s.
  · **Flate nivel 1** (`pikepdf.settings.set_flate_compression_level`, en `aplanar_rip` y
    `piezas_con_diseno`; `TIZADA_FLATE=6` vuelve): guardar la hoja aplanada 6,9 → 1,7 s
    (18,0 → 20,4 MB). Sin pérdida: cambia cuánto se empaqueta, no un byte del contenido.
  · Servidor: sin arte no hay RGB que rastrear (`_pdf_tiene_rgb` se salta con moldes con diseño);
    `verificar_rip_compatible.verificar(path, balance=False)` no re-corre `validar_salida`
    (el CLI sí); cronómetro del pedido ENTERO en `correr()` (`[tiempos] pedido <tid>: motor · rip ·
    perfil · verificar · ficha · total`).
  **Medido después** (`medir_tizada_b.py 5`, mismo molde, en frío): 35 → **10 s** (motor 6:
  nesting 2, previews 3; aplanado 4) · hoja aplanada 20,4 MB. Carga (`medir_alta2.py`, 9
  procesos): alta completa 15,5 → **5,2 s**; con contornos ya hechos 18 → 3,1 s; páginas por talle
  en segundo plano 32,6 → 28,8 s. **Por HTTP contra el 8051** (`prueba_cache.py`, molde efímero
  propio): `POST /api/plantilla` 25 → **11,4 s** la primera vez (páginas listas a los 34 s, caché
  guardada 4 s después) y **1,0 s** la segunda vez con el mismo archivo, con el desplegado
  COMPLETO (páginas y placeholders incluidos). Cronómetro: `[tiempos] subida de <archivo>`.
  ⚠️ **Lo que salió mal**: un medidor sin `if __name__ == "__main__"` en Windows (spawn) se
  re-ejecuta entero en cada worker: la medición «con 6/9/12 procesos» corrió en SERIE, en loop
  y dejó 11 procesos huérfanos que inflaron TODAS las cifras (mesa 2: 15 s en vez de 8). Regla:
  todo script que llame a `desplegar_molde(procesos=n)` lleva el guardián, y antes de medir se
  listan los `python.exe` vivos con su línea de comando (`Get-CimInstance Win32_Process`).
  Contratos: `verificar_desplegado`, `verificar_hoja_compartida` (peso tras aplanar),
  `verificar_tizada_con_diseno`, `verificar_placeholders_con_diseno`, `verificar_molde_con_diseno`,
  `verificar_poda_camino_b`, `verificar_registro_idx_mesa`; comparación de contornos 180/180.
  · **Bug encontrado por el usuario al tizar (10:20): `'NoneType' object has no attribute 'get'`**
    en `texto_curvas._glifo`. La fuente que subió al catálogo («MoreggiTFont4-Camiseta.ttf») no
    trae tabla cmap unicode —sólo Mac Roman (1,0) y símbolo (3,0)— y `TTFont.getBestCmap()`
    devuelve None. `FuenteCurvas._cmap_de_respaldo` arma el mapa con lo que hay (símbolo =
    0xF000 + código; Mac Roman decodificado a unicode; nunca None: el servidor recorre
    `fc.cmap.keys()`). Y un ESPACIO sin glifo (fuentes decorativas con letras y números nada
    más) ya no tumba «MESSI 10»: avanza el glifo `space` si existe por nombre o un tercio del em.
  · 🔴 **Reporte del usuario (10:30): «hay piezas que se ven por fuera de lo que debería ser, el
    borde parece de más de 3 mm, y a la ficha le faltan las piezas».** Tres causas:
    (1) **El contorno era el recorte equivocado.** `_piezas_de_mesa_cruda` tomaba el recorte de
    MAYOR ÁREA del grupo, y en el archivo real ése es la LÍNEA DE CORTE dibujada: un clip con
    sólo trazos adentro, 0,5-1 mm más alto (camiseta, cuello recto, costadillo) y hasta 4 mm más
    ancho (cuello curvo, mesa 7) que la máscara del diseño. La pieza salía con una franja blanca
    entre el estampado y el borde de corte. Ahora el contorno es el recorte de mayor área ENTRE
    LOS QUE TIENEN RELLENOS adentro (`_rellenos_por_clip`, por el `level` de
    `get_drawings(extended=True)`); sin rellenos en ninguno, el mayor como antes. Cambian
    179/180 contornos del archivo real (misma cantidad de piezas). El desplegado lleva
    `v = _V_CONTORNOS` (2): un JSON con otra versión rehace los contornos y CONSERVA las páginas
    por talle (`_json_mismo_archivo` vs `_json_vigente`); `_CACHE_DESPL_VERSION` → `v394b`.
    (2) **La ficha sin molde guía**: `_molde_guia_ficha` devolvía None por no encontrar
    `arte.ai`; en el camino B el diseño está en el molde (`arte=None`, `mapeo=None`, `pers` del
    molde, mismo criterio que `_piezas_base`).
    (3) **`_desplegar_en_fondo`**: un molde ya cargado con desplegado no listo (regla vieja,
    carpeta borrada) lo rehace un hilo de fondo UNA vez por molde; antes los endpoints decían
    `preparando` y nadie lo armaba. Y la clave de la caché de SVG lleva la mesa (dos piezas de
    mesas distintas con el mismo contorno compartían el SVG).
  · 🔴🔴 **Segundo reporte (10:55): «sigue pasando, sólo en algunas piezas».** Las que seguían mal
    eran las RECTANGULARES (cuello recto, mesas 5/6): su contorno es un solo segmento `("re", x,
    y, ancho, alto)` y `generar_pedido.ops_cont` le sumaba el desplazamiento (`dx`, `dy`) a LOS
    CUATRO valores, ancho y alto incluidos. El clip del borde de corte salía 104 pt (3,7 cm) más
    angosto y 3 pt más alto que el diseño: la raya negra vertical DENTRO de la pieza, la franja
    blanca arriba y el estampado que «se pasaba» del borde por la derecha (leído en la hoja real:
    `9.921 9.921 600.112 141.981 re` con 600,112 = 704,976 − 104,864). El diseño en sí estaba
    bien porque su clip va sin desplazamiento (`cm` aparte). En el camino A nunca se vio: sus
    contornos son polilíneas/curvas. Los otros ocho manejos de `re` del motor y del nesting
    estaban bien (revisados uno por uno). Ahora `re` desplaza x e y y escala ancho y alto.
  · 🔴 **LA LÍNEA DE CORTE DEL ARCHIVO ES EL BORDE DE LA PIEZA (pedido del usuario, 11:20: «en vez
    de dibujar el borde por arriba, que los cambios los haga en el borde que viene»).** El
    archivo real trae, por pieza, la máscara del diseño Y una línea de corte dibujada (trazo de
    2 mm centrado en su propio trazado, 0,5-4 mm más grande que la máscara). Dibujar el borde
    nuestro encima daba dos bordes (1 mm negro de ellos + 3,5 mm nuestros). Ahora:
    (1) `_piezas_de_mesa_cruda`: si en el grupo hay un recorte SIN rellenos que envuelve al del
    diseño y tiene un trazo (adentro, o el dibujo siguiente con su misma caja —cuello curvo—),
    ESA es la pieza: su trazado es el contorno (`cont["linea_corte"] = True`). Sin línea, la
    máscara del diseño como antes. (2) Etapa de páginas, `quitar_linea_de_corte`: sigue la CTM
    del content-stream, arma la caja de cada trazado pintado sólo con trazo y, si coincide con
    `bbox_raw` del contorno (±1 pt), cambia el `S` por `n` (queda sin pintar) y guarda ancho y
    color EXACTOS (`m{mesa}.json["linea_corte"][talle][idx] = {w, color}`; `_leer_desplegado`
    lo mete en `cont["linea_corte"]`). (3) `_armar_base`: borde ACTIVO → el borde configurado
    (ancho, color, alineación) sobre ese trazado, único; borde APAGADO y la pieza trae línea →
    se traza tal cual venía (mismo ancho, color, centrada). Versiones: `_V_CONTORNOS = 3`,
    `_V_PAGINAS = 3` (las páginas viejas se rehacen: la línea hay que sacarla), caché `v394c`,
    `_piezas_base_clave` v16 lleva las versiones del desplegado. Contrato: `verificar_desplegado`
    §7 (y §1/§2: la página de control también pasa por `quitar_linea_de_corte`, como ya pasaba
    por `quitar_placeholders`; el conteo de píxeles distintos va con numpy — en Python puro
    tardaba 10 minutos y parecía colgado). Verificado en el archivo real: las 9 mesas × 20
    talles detectan su línea (w 5,669 pt, color k [0 0 0 1]) y la página desplegada queda sin
    ese trazo; con el borde apagado la base la traza tal cual (un solo `S` de 5,669 pt).
    **Segunda vuelta (12:10, «queda ese desfasaje» + subida de 30 s + nombrar lento):** (a) entre
    la máscara del diseño y la línea de corte hay 0,5-2 mm que en el archivo tapaba la mitad
    interior del trazo; con el borde «fuera» quedaba una franja blanca → `_armar_base` traza
    además esa mitad interior (ancho original, color del borde) DESPUÉS del diseño (`borde_post`);
    apagado, la línea original también va después del diseño (antes iba antes, y el diseño la
    tapaba a medias). (b) La subida de 30 s y el nombrar lento fueron CPU ajena: los contratos
    corriendo en la misma máquina (4 procesos + renders) justo cuando el usuario subía, más el
    `_desplegar_en_fondo` del molde viejo, más un SEGUNDO hilo de páginas para el molde nuevo
    (`_desplegar_en_fondo` no sabía del hilo de la subida): ahora `_prewarm_desplegado` se
    anota en `_DESPL_FONDO`, y `desplegar_mesa(contornos=False)` devuelve enseguida si las
    páginas ya están con su versión (antes reescribía las 20 páginas otra vez: 44 s). Regla
    para mí: no correr contratos pesados mientras el usuario prueba en el 8051. (c) Un pedido
    sobre un molde que ya no existe (re-subido como producto nuevo) cae en `pagina_arte(None)`
    con `TypeError` en vez de un aviso claro — pendiente.
  **Pendientes con plan** (ver el doc): responder la subida al instante y desplegar en segundo
  plano con avance en pantalla (front: estado «preparando el molde» en `subirPlantilla`);
  contornos desde el content-stream parseado (sin MuPDF; 1,2 s por mesa) con contrato contra
  `get_cdrawings`; páginas por talle sólo de los talles del pedido cuando la tizada llega antes
  que el segundo plano; previews después de marcar el trabajo listo; E6/E7 del changelog 393.
- **2026-09-04 (393) — LA HOJA COMPARTIDA: la tizada del camino B deja de ser lineal en prendas.**
  Pedido del usuario: «5 camisetas tardan 2:30; 100 tienen que tardar 2 minutos; buscá el mejor
  método». Plan aprobado en `~/.claude/plans/dapper-cuddling-dahl.md`; diseño en
  `MOLDE_CON_DISENO.md` «LA HOJA COMPARTIDA». Medido antes (5 prendas, en frío): motor 29 s +
  aplanado 26 s = **70 s** (en el servidor, con ICC y máquina cargada, 180 s). Cada prenda
  repetía TODO: serializar la pieza, copiar la mesa entera a la hoja (45 copias, 29 MB) y
  des-anidarla inline para el RIP (900.000 operadores).
  **Lo que cambia** (`hoja_pike.py` nuevo; `motor_pedido.py`, `nesting_contorno.py`,
  `aplanar_rip.py`, `servidor.py`):
  · **Base compartida**: `_armar_base` (camino B) deja en la base de dónde salió la mesa
    (`despl` = pdf desplegado + página) y el nombre del XObject; `generar_pieza` ya no serializa:
    devuelve `{base, estampado}` (el estampado = clip + nombre/número en curvas + etiqueta, lo
    que cambia por prenda). El documento por pieza sólo existe si alguien lo pide
    (`_DocPerezoso`: el Arte, el nesting de siempre, los contratos).
  · **`hoja_pike.componer_hoja_pike`**: la hoja se compone con pikepdf. Por base, UN Form XObject
    plano: la mesa desplegada metida INLINE (bytes tal cual, la receta de `_flatten`: `q [Matrix
    cm] [BBox re W n] <contenido> Q`) + clip + borde, con los recursos de la página (fuentes
    incluidas). Por colocación: `q <cm> /B_k Do Q` + `q <cm> <estampado> Q`. La `cm` reproduce a
    `show_pdf_page` (signo de giro +1, calibrado: con −1 las piezas libres giraban al revés).
  · **Máscaras por contorno** (`nesting_contorno._mascara_contorno`): el nesting ya no rasteriza
    el arte de cada pieza; pinta el polígono del contorno (+ borde) a 4× y reduce a celdas con el
    mismo criterio. `TIZADA_MASCARA_LEGACY=1` vuelve al raster.
  · **Aplanado de UN nivel** (`aplanar_rip._aplanar_un_nivel`, default): la página conserva sus
    `Do`; el interior de cada base se des-anida y sanea UNA vez (memo por objgen); ICC unificado
    por hash en todo el archivo (`_unificar_icc`); el **OutputIntent ya no se borra** y el
    servidor lo incrusta DESPUÉS del aplanado (antes lo ponía antes y el aplanado lo borraba: el
    archivo salía sin perfil). `TIZADA_APLANADO_TOTAL=1` = inline como siempre.
  · **Validar una vez**: `generar_pedido_grupos` reusa las validaciones de `_nestear_y_componer`
    (la segunda pasada costaba 26 s y reportaba un espaciado inventado).
  · **Preview liviano** (`hoja_pike.preview_svg`): `<symbol>` por base + `<use>` por colocación +
    el estampado convertido por PyMuPDF. Los ids de PyMuPDF (`cp0`…) se prefijan por símbolo: sin
    eso el recorte de una pieza se aplicaba a otra. ⚠️ MuPDF NO dibuja `<use>`/`<symbol>`: para
    verificar el SVG hay que mirarlo en un navegador (Chromium lo dibuja igual que la hoja).
  · **Compatibilidad RIP** (`verificar_rip_compatible.py`): PDF ≤ 1.6, sin capas, sin
    transparencia, profundidad 1, fuentes embebidas, colores CMYK/Gray/ICC-4/Separation, un ICC
    por perfil, OutputIntent GTS_PDFX N=4, streams balanceados, segundo lector (PyMuPDF). Corre al
    terminar cada tizada; si falla, aviso en `avisos_pedido`.
  · Bug adyacente: `servidor.py` `_cb = _combo_toggles(...)` pisaba el flag camino B → `_cbt`.
  · Las fuentes del diseño se CONSERVAN en las bases (antes `_barrer_fuentes` las borraba y el
    aplanado eliminaba los textos vivos: un rótulo del diseño se veía en el Arte y no salía en la
    hoja — 1836 píxeles de diferencia medidos en la hoja de siempre; la nueva da 0).
  · **Nesting a escala (E7)** (`nesting_contorno._anidar_estrategia`): a 100 prendas (900 piezas,
    72 geometrías) el nesting viejo no terminó en 25 min (una FFT por ángulo candidato y por
    hoja, 24 ángulos con rotación libre). Ahora: (1) **bloques de idénticas** — una geometría ya
    colocada busca primero, SIN FFT, el primer lugar libre de su fila, de la siguiente y de una
    más (barrido vectorizado con `sliding_window_view`, prueba local de solapamiento); (2) una
    repetida que no entra usa la FFT sólo con el ángulo de su anterior y sólo desde su hoja en
    adelante; (3) la primera de una geometría con rotación libre va de grueso a fino (múltiplos
    de 90° y después ±2 pasos alrededor del mejor: 8 FFT en vez de 24). Medido: 30 prendas 69 →
    14 s (FFT 2997 → 681, mismas 5 hojas); 100 prendas: más de 25 min → 38 s (1497 FFT).
    `TIZADA_NESTING_SIN_BLOQUES=1` vuelve al barrido completo. Contadores en `_DEBUG`.
  · 🔴 Trampa de `_DocPerezoso`: `if p["doc"]:` llamaba `__len__` → `real()` → serializaba la
    pieza (1,6 MB) para las 900 piezas sólo para cerrarlas: 170 de los 269 s a 100 prendas. Ahora
    `__bool__` es True sin armar nada. Un objeto perezoso que se usa como booleano tiene que
    decirlo explícitamente.
  · Preview: los estampados de TODA la hoja se convierten a SVG en UNA pasada (un documento con
    los 900, en coordenadas de página) en vez de una por prenda.
  **Medido (5 prendas, 3 talles, en frío)**: 70 s → **40 s** (motor 28: nesting 6, hoja 5,
  previews 13, validar 4; aplanado 11) · hoja 46 MB → 21 MB (18 aplanada) · previews 64 → 39 MB
  · con las MISMAS colocaciones la hoja nueva y la de siempre difieren en 0,1 % de píxeles (bordes
  de las piezas giradas, redondeo) · aplanar no cambia un píxel. Contratos nuevos:
  `verificar_hoja_compartida.py`, `verificar_rip_compatible.py`; medidor `medir_tizada_b.py`.
  **Medido (100 prendas, 8 talles, en frío)**: de **más de 40 min** (extrapolado; el nesting solo
  no terminó en 25) a **138 s = 1,4 s/prenda** (motor 91: nesting 37, hoja 14, previews 21,
  validar 16; aplanado 47) · hoja 51 MB (48 aplanada) · 15 hojas de 5 m · previews 264 MB en
  total (una por hoja).
  Lo que sigue (plan E6): bases y sus SVG pre-armados en el alta (por procesos; hoy 72 bases =
  ~14 s de armar documentos para el preview), la tizada entera en un proceso, memoria de tizada;
  y el aplanado/validación por hoja en paralelo (47 + 16 s a 100 prendas).
- **2026-09-04 (392) — EL SERVIDOR SE CONGELABA UN MINUTO: NADA CONSTRUYE EL DESPLEGADO EN UN
  HILO DEL REQUEST.** Reporte del usuario: «entro al molde con diseño y no me muestra las piezas,
  y ponerle nombre a una tarda más de un minuto». Medido en su sesión: `/api/productos` (3 KB)
  **9,4 s**, `emparejado` 3,1 s, `etiqueta` 3,7 s, `deteccion_todas` 2,9 s — y la pantalla pide
  varios por acción. La radiografía con **py-spy** del proceso del servidor mostró el hilo
  activo en `fuentes_estado → extraer_personalizacion → personalizacion_con_diseno →
  desplegar_mesa → pikepdf.save` **con el GIL**: el chequeo de tipografía del camino B (389),
  llamado apenas se entra al Arte —antes de que el hilo de fondo termine las páginas por
  talle— armaba las 9 mesas EN EL HILO DEL REQUEST y en serie, en paralelo con el hilo de fondo
  que hacía lo mismo por procesos. `pikepdf.save` no suelta el GIL, así que TODO el servidor
  esperaba: por eso el visor tardaba en mostrar las piezas y nombrar costaba un minuto.
  Arreglo, en tres capas:
  1. `fuentes_estado` (camino B) **nunca construye**: si `PD.desplegado_listo()` es falso responde
     `preparando: true` (sin fuentes) y el front re-pregunta cada 6 s hasta 2 min
     (`_reintentoFuentes`). Lee los placeholders con `personalizacion_con_diseno(armar=False)`.
  2. `personalizacion_con_diseno(armar=True)` y `ruta_desplegada(armar=True)` (lo que usa el
     motor) construyen **por procesos** (`desplegar_molde`, una sola pasada por todas las mesas),
     nunca en el hilo que llama.
  3. **Un candado por molde** (`_candado(path)` en `desplegar_molde`): el segundo que necesita
     las páginas ESPERA al que las está armando (el hilo de fondo de la subida) y al re-mirar las
     encuentra hechas. Se acabó el doble trabajo.
  4. La vista previa de piezas del Arte (`_piezas_base`) tampoco construye: si el molde no está
     listo responde `preparando` y el front vuelve a pedir (sin cachear el vacío).
  5. `_leer_desplegado` **no cachea una entrada sin páginas**: se guardaba en `_CONT_CACHE`
     mientras el hilo de fondo las armaba y, como el sello del archivo no cambia, el servidor
     decía «preparando» para siempre (el chequeo de tipografía re-preguntaba cada 7 s sin fin).
  Después del arreglo, en frío: `/api/productos` 0,09-0,2 s, `deteccion_todas` 0,08 s,
  `emparejado`/`etiqueta` 0,08 s; entrar a nombrar y ponerle nombre a una pieza: ~3-4 s de
  servidor en total (antes, más de un minuto). Regla nueva para el mapa (§6 gotchas): **pikepdf y PyMuPDF
  retienen el GIL — cualquier trabajo pesado con ellos va en un proceso, y nunca dentro de un
  request**.
- **2026-09-04 (391) — BUGS DEL PEDIDO CON MOLDE CON DISEÑO (la parte que toca configuración).**
  Pedido del usuario: «repará los bugs que se generan en el pedido de moldes cargados con diseño;
  hay varios que se bugean con la configuración». Se recorrió el flujo entero en el navegador
  (subir → nombrar → volver → etiqueta → color del cliente → volver → requisitos) y esto es lo
  que estaba roto y cómo quedó:
  1. **Pantalla EN BLANCO al salir de la herramienta por la barra.** Desde nombrar/etiqueta
     (`desdePedidoB` puesto), tocar «Pedidos» o «Configuración» en la barra dejaba todo vacío: el
     pedido se oculta con `!desdePedidoB` y el panel de Configuración también, y nadie limpiaba
     `desdePedidoB` salvo «← Volver al pedido». Ahora los dos botones llaman
     `cerrarHerramientaB()` (cierra el modo nombrar, limpia `desdePedidoB`/`pendienteNombrarB`/
     `empTodasData`, cierra la moldería y vacía `_talleDetCache`).
  2. **El conteo de etiquetas era del molde anterior.** `etiquetaConfig` es UN solo estado y la
     tarjeta del paso Arte sólo recargaba la detección: con dos moldes con diseño, «Etiqueta: N
     de 9 ubicadas» y el botón «Ubicar la etiqueta» mostraban lo del molde que se miró antes. El
     efecto de la tarjeta ahora trae `/api/productos/etiqueta` del molde elegido (fetch inline: la
     const `cargarEtiqueta` se define más abajo y sumaría un use-before-define al tope de
     `verificar_tdz.mjs`).
  3. **La tipografía faltante NO contaba en el requisito «Cargar fuente».** Dos causas:
     `cargarFuentesTodas` y `fuentesFaltantesItems` filtraban por `arteCargado[…]` (un molde con
     diseño no tiene arte cargado → nunca se consultaba), y el efecto que dispara el chequeo
     corría **antes de que llegara el catálogo** al recargar la página parado en el Arte (los
     moldes no se reconocían como camino B y el activo era `prod_default`). Ahora los moldes con
     diseño entran en las dos listas y el efecto depende también de `_idsCat`. Verificado:
     «Tipografía (1)», 0/3, y el detalle por molde con «se va a sublimar con Anton — podés
     avanzar igual».
  4. **«Falta el arte de «X»» para un molde con diseño.** El requisito «Asignar arte» ya sabía que
     en el camino B lo que falta es NOMBRAR (`_itemListo`), pero el texto decía «falta el arte».
     Ahora: «Faltan nombrar las piezas de «X» · diseño «Y» (N sin nombre)».
  5. **«Nombrar las piezas» abría la GRILLA de molderías del taller** («Molde 1», «Nueva
     Moldería», «Volver al Panel de Configuración» — captura del usuario). `abrirNombrarB` /
     `abrirEtiquetaB` ponían `adminSubView='productos'` y recién DESPUÉS de `await
     handleActivarProducto()` (activar + recargar catálogo + estado) abrían la moldería: mientras
     tanto se renderizaba la grilla, y si esa espera tardaba o fallaba el cliente quedaba ahí,
     dentro del taller. Ahora la moldería y la pestaña se abren ANTES del await (`pidCfg` toma
     `molderiaAbierta` explícito, no depende del activo del servidor), y además la rama de render
     tiene guardia: con `desdePedidoB` puesto **nunca** se muestra la grilla — si el molde todavía
     no está en el catálogo del navegador sale «Abriendo el molde…» con «← Volver al pedido».
     Verificado en la ruta del cliente sondeando el DOM cada 100 ms durante la apertura: la
     grilla no aparece ni un instante, ni para nombrar ni para la etiqueta.
  6. **El pedido listaba los efímeros de OTROS usuarios** (un admin ve los de todos por
     `molde.ver_todos`), y `irANombrarB` abría el primero sin nombrar aunque fuera ajeno.
     `_mios` filtra `!p.de_otro` (los dos sitios).
  7. **`limpiar_efimeros` («Nuevo pedido») borraba efímeros ajenos** — el pendiente del changelog
     387. Ahora ignora todo molde con `creado_por` distinto del usuario actual.
  8. **Carpetas huérfanas de 118 MB en `entrada/`** (la `prod_20260903_112000_55ad` y una de
     prueba de hoy): `_borrar_molde_entero` hacía `rmtree(ignore_errors=True)`, que en Windows
     falla EN SILENCIO si `plantilla.ai` está abierto un instante por el propio servidor (caché
     de documentos, una detección en curso, el hilo de páginas). Medido: minutos después el
     archivo se borraba sin problema — el bloqueo es transitorio. Ahora cierra los documentos
     abiertos (`MP.cerrar_abiertos()`), reintenta 5 veces, y si sigue trabado reintenta en un
     hilo hasta dos minutos; si aun así no puede, lo dice en el log con la carpeta.
  Verificado que NO eran bugs: el molde activo es POR SESIÓN (`session["pid_activo"]`, no se
  cruza entre usuarios); «Re-subir Plantilla» sigue en el DOM tras «Salir» pero con
  `display:none` (no se ve); «Cambiar» talle guía en la herramienta anda (guarda `variante_guia`,
  el lienzo sigue con las 180 piezas); ubicar + guardar la etiqueta y el color del cliente
  funcionan de punta a punta (el molde queda cian, el admin sigue con el suyo).
  ⚠️ Latente y preexistente (está en HEAD): `zdef` no está definido en el overlay de zonas
  (`editZonas` es `false` constante → código muerto). Cuenta en el tope de `verificar_tdz.mjs`:
  si alguien suma OTRO use-before-define, el build lo muestra a él aunque no tenga nada que ver.
- **2026-09-04 (390) — LA PANTALLA DEL TALLER, REHECHA; Y TRES COSAS DE LA ETIQUETA PASAN AL
  CLIENTE.** Pedido del usuario sobre la 389: «este campo hacerlo moderno, 100 % moderno, menos
  palabras y más iconos» + «el color del texto y del contorno que lo pueda modificar el cliente,
  igual que la alineación, en la etiqueta nomás».
  **La pantalla** (`Configuración → Molde con diseño`): era una lista de labels y campos; ahora
  son **tarjetas con icono** — Borde de corte · Etiqueta · Así sale · Planilla · Acomodo — con
  interruptor en la cabecera de cada una, números con la unidad **adentro** (sin label aparte),
  **segmented** para «fuera/centro/dentro» y para la alineación (◧ ◫ ◨), **chips** para qué
  muestra la etiqueta, y la **muestra de color como control** (el CMYK va en el `title`).
  «Guardar» y el aviso de «vale para N» suben a la cabecera. Y una tarjeta **«Así sale»**: la
  pieza dibujada en vivo con su borde, su etiqueta, su halo y su alineación — reemplaza tres
  párrafos por algo que se mira.
  🔴 Los controles son **componentes de módulo** (`CfgCard`, `CfgNum`, `CfgSeg`, `CfgColor`,
  `CfgChip`, `CfgSw`, `CfgPreview`), no helpers dentro del render: (1) definidos adentro, React
  los remonta en cada tecleo y el input **pierde el foco**; (2) `verificar_diccionario.mjs` sólo
  ve el ancla en el JSX (`data-tour="x"` / `ancla="x"`) — pasarla como argumento a un helper la
  dejaba invisible para el tutorial, que es justamente quien la necesita. 8 entradas nuevas en el
  diccionario; las tarjetas (contenedores) van sin ancla.
  **Los tres campos del cliente** (`_ETQ_CLIENTE = ("color", "borde_color", "align")`): el admin
  sigue fijando el punto de partida, y el molde manda **sólo si el cliente los tocó** —
  `_etiqueta_de` mira `prod["etiqueta"]` **crudo** (no el ya mezclado con los defaults: si no, el
  default del sistema ganaría siempre y lo del admin no se vería nunca). `set_etiqueta` los
  acepta en camino B junto con `posiciones`/`piezas_off`/`zonas`. En la pantalla del pedido se
  apaga **bloque por bloque** lo que decide el taller, no con un envolvente: la opacidad de un
  padre no se puede revertir en el hijo y `pointer-events: none` se hereda. Verificado por API:
  el cliente cambia color/halo/alineación y quedan; el `size_mm`, el `mostrar` y el `activo` que
  mande se **ignoran** y siguen los del taller.
- **2026-09-04 (389) — LA PANTALLA DEL TALLER, COMPLETA; Y LA TIPOGRAFÍA DEL «00»/«NOMBRE»
  AVISA.** Dos pedidos del usuario: (a) «no me agregaste un espacio para configurar desde admin
  ese tipo de cosas: qué plantilla le asignaremos, el color de etiqueta, color de borde, etc.,
  **sin tener el molde cargado**»; (b) «si la fuente del nombre y el 00 no la detecta, que
  funcione como la otra parte: que dé un aviso y puedas cargarla o cambiarla por una nuestra, y
  si no, que use la predeterminada».
  **(a)** La pantalla ya existía (`Configuración → Molde con diseño`, `adminSubView ===
  'con_diseno'`, es global: no necesita ningún molde cargado) pero estaba a medias: sólo grosor y
  alineación del borde, tamaño/separador/qué muestra de la etiqueta, y el nesting. Le faltaba
  **todo lo que el usuario nombró**. Ahora tiene: **color del borde de corte**; de la etiqueta,
  **alineación, color del texto, color del halo, grosor del halo** y el interruptor del halo; y
  la **planilla del pedido** — `config_con_diseno.planilla_template_id`, que `subir_plantilla`
  le aplica a TODO molde con diseño al confirmarse el camino (no en `crear_producto`: ahí
  todavía no se sabe si el archivo trae el diseño adentro). Los colores usan el mismo
  `ColorPickerModal` CMYK del resto. `_ETQ_FORMA` ya incluía `align`/`color`/`borde_*`, así que
  el motor los toma sin tocar nada más. Verificado: guardar y releer devuelve los valores, y un
  molde subido después queda con la planilla configurada.
  **(b)** `GET /api/pedido/fuentes_estado` miraba **el arte**, que en el camino B no existe → el
  paso Arte decía «Cargar fuente ✓» aunque la tipografía del archivo no estuviera en el catálogo,
  y la prenda salía con la de reemplazo **sin avisar**. Ahora, para un molde del camino B, las
  fuentes requeridas salen de los **placeholders del desplegado** (`extraer_personalizacion`,
  incluido el `por_talle`). Todo lo demás ya servía tal cual: el modal lista el catálogo para
  cambiarla, `POST /api/pedido/fuente_resolver` sube la del diseño o guarda el reemplazo **del
  pedido**, y el motor cae a Anton si no hay nada. Verificado en la pantalla con el archivo real:
  «Tipografía (1)» en amarillo, «No se encontraron las fuentes: MoreFont1-CL», elegir una del
  catálogo la saca de faltantes. Contrato: `verificar_placeholders_con_diseno.py` §5 (el
  reemplazo cambia lo estampado).
- **2026-09-04 (388) — LA HERRAMIENTA, SIN ENTRAR A CONFIGURACIÓN; Y LAS PIEZAS EN EL ORDEN DEL
  ARCHIVO.** Dos correcciones del usuario sobre la 387, con captura: (a) «¿te parece a vos que
  están así ordenadas las piezas? mirá el PDF»; (b) «que use la misma herramienta, pero **no debe
  entrar a ajustes reales: a ese espacio no puede tener acceso el cliente**».
  **(a) El acomodo del visor: NO SE ACOMODA NADA.** Aclaración del usuario en la misma tanda, con
  las dos capturas al lado: «que respete cómo viene en el archivo… **no hablo de las mesas sino de
  los objetos: que no separe los que están uno arriba del otro. Todos los frentes están juntos,
  que los deje así — ya están en diferente capa**». Los talles vienen dibujados **uno encima del
  otro** (la gradación anidada) y así tienen que verse; se distinguen por su CAPA (el ojito de la
  columna de talles), no por su posición. Lo ÚNICO que se acomoda son las **mesas**, y sólo porque
  el PDF las guarda todas en el mismo lugar (medido: las 9 páginas arrancan en (0,0)).
  Implementación: **`acomodo_mesas(por_mesa)`** calcula, con la unión de TODOS los talles, la caja
  de cada mesa y su lugar en filas tipo estante, en el orden del archivo, con el ancho de fila que
  deja el lienzo más parecido a 16:9. Se calcula **una sola vez** y se le pasa a todos los talles
  (`layout_visor(..., acomodo=)`): si se calculara por talle, el molde se movería al cambiar de
  talle. Dentro de la mesa, cada pieza queda donde el archivo la puso — el recorte que se le pasa a
  `_item_visor` es el de la MESA, no el de la pieza. `visor_junto` ya no acomoda nada: los talles
  comparten lienzo, sólo los concatena. Los dos devuelven **`formato: "anidado"`** y el front no
  dibuja el rótulo por talle (caerían los 20 en el mismo lugar); `canvasLayout.filas` se fue.
  Verificado en pantalla: se ve la gradación (espalda con sus 20 talles anidados, frente igual,
  mangas, tiras), 0 piezas que se pisen **dentro de un talle**, y tocar la pila nombra la pieza en
  los **20 talles** de una.
  ⚠️ Un molde subido ANTES de esto conserva su `visor_contornos.json` con el acomodo viejo (se ve
  chico y separado): se corrige al volver a subirlo. Los efímeros duran un pedido, así que se
  arregla solo.
  **(b) La herramienta sin Configuración.** `abrirNombrarB`/`abrirEtiquetaB` ya **no hacen
  `setActivoTab('config')`**: el espacio de trabajo del molde se renderiza desde la pestaña
  **Pedidos** (`{(activoTab === 'config' || desdePedidoB) && …}`, y el pedido se tapa con
  `activoTab === 'pedidos' && !desdePedidoB`). Con `_soloHerramienta` (= `!!desdePedidoB`) quedan
  fuera **todos** los accesos al espacio del taller: el menú de ajustes, «⬅ Volver a ajustes»,
  «Re-subir Plantilla», «Nombrar talles» (`NombrarVariantes`, que reescribe las capas del
  archivo), «Agregar una pieza» y la ayuda de exportación. Queda el visor, la herramienta, el
  talle de guía y «← Volver al pedido», con un subtítulo que dice qué se está haciendo. 🔴 No es
  sólo estética: el deep-link a `activoTab='config'` **renderizaba la pantalla de configuración a
  alguien sin `config.ver`** (el permiso gatea el botón del menú, no el render).
  **Y el orden en las listas de la etiqueta**: `et["piezas"]` y `_etq_piezas_del_molde` van sin
  ordenar para el camino B → «Espalda, Frente, Manga, Cuello, Costadillo, Tira» (archivo), no
  alfabético. Verificado en el navegador de punta a punta: nombrar 9 piezas, la lista de la
  etiqueta en orden, y ningún botón que lleve a los ajustes.
- **2026-09-04 (387) — CAMINO B: NOMBRAR Y ETIQUETA CON LAS PANTALLAS DE CONFIGURACIÓN, «00» /
  «NOMBRE» POR TEXTO, Y EL CUELGUE DEL SERVIDOR.** Tres pedidos del usuario: (1) «el nombrar
  piezas del molde con diseño tiene que ser exactamente la misma herramienta que usa Moldería»,
  (2) «lo mismo la etiqueta», (3) «el archivo trae el número como 00 y el nombre como NOMBRE: se
  detectan y se les pone el valor de la columna número y nombre; y las piezas en el orden del
  archivo». La versión propia del pedido de la 386 (lienzo junto, recuadro, homólogas) queda
  sin uso en el pedido; el lienzo junto (`visor_junto`) pasó a servir a Moldería.
  **(1) Nombrar = Moldería.** Desde el pedido, «Nombrar las piezas» (`abrirNombrarB`) activa el
  molde y abre Configuración → Moldería con el modo «nombrar» prendido (efecto
  `pendienteNombrarB`: `activarEmparejar` lee el molde ACTIVO, así que se prende recién cuando
  la pantalla está sobre ese molde), con **«← Volver al pedido»** (`desdePedidoB`,
  `volverAlPedidoB`: cierra, vuelve al paso Arte y recarga nombres y etiqueta). Para que esa
  herramienta funcione con el camino B: `GET /api/plantilla/emparejado` devuelve
  `_emparejado_camino_b` (guía, talles, `nombres_guia` por `pieza_idx` del guía —sin los
  provisorios «Pieza N», que para la pantalla son «sin nombre»—, `asignacion` completa y todo en
  `manual`: no hay pendientes), `POST grupo_pieza` en camino B es **renombrar** la pieza
  (`PD.renombrar` por mesa + idx_mesa; `eliminar` = volver a un provisorio libre), `POST
  emparejado` es no-op, y `deteccion_todas` devuelve `visor_junto` con **`t_idx` = pieza_idx**
  (el contrato del lienzo junto: «su índice dentro del talle»; el índice dentro de la mesa va en
  `idx_mesa`). En el front, `crearGrupoTodas` con `empData.origen === 'con_diseno'` nombra cada
  pieza seleccionada por su `t_idx` sin exigir la del guía (`sinGuia` no aplica), y `_postGrupo`
  vuelve a pedir el lienzo junto (trae los nombres del registro). Moldería esconde «Agregar una
  pieza» y «Acomodar piezas» para el camino B (no aplican).
  **(2) Etiqueta = la pestaña Etiqueta.** `abrirEtiquetaB` abre `tabAjustesMolde='etiqueta'`
  (+ `cargarEtiqueta(pid)`/`cargarBorde()`, lo que hace el menú). Para el camino B la sección de
  FORMA (mostrar, qué muestra, tamaño, color, borde) se ve pero no se edita —es la config viva
  del taller, `set_etiqueta` sólo toma posiciones— con una nota que lo dice. Las listas de piezas
  (`et["piezas"]`, `_etq_piezas_del_molde(ordenar=False)`) van en el **orden del archivo** para
  el camino B. 🔴 `abrirEtiquetaB`/`abrirNombrarB`/`volverAlPedidoB` limpian `empTodasData`: la
  pestaña filtra el lienzo junto POR NOMBRE y con el lienzo de antes de nombrar (nombres en
  blanco) el visor salía vacío — pasó. El panel del pedido quedó en dos botones + estado
  (`panelNombrarJSX`), sin el nombrado propio.
  **(3) «00» y «NOMBRE» por texto.** `piezas_con_diseno.quitar_placeholders` corre en la etapa de
  páginas del desplegado, sobre las instrucciones de cada talle: decodifica cada `Tj`/`TJ` con la
  codificación de la fuente (`_decodificador`: WinAnsi + `/Differences`; ToUnicode para Type0)
  —⚠️ el «00» de este archivo viene como `\x1f\x1f` con `/Differences [31 /0]` y PyMuPDF lo
  descarta como control—, y si dice «00»/«NOMBRE» guarda `cx`/`baseline_y` (dispositivo, como
  `bbox_mu`, con `marco`+`U` que ahora deja la etapa de contornos en el JSON), `size`, `fuente`,
  `ancho` (por `/Widths`), `colorn` y `pasadas` (relleno/trazo nativos en orden) y **saca el
  operador del dibujo**. Queda en `m{mesa}.json["placeholders"][talle][campo]`;
  `personalizacion_con_diseno` lo arma como `pers` con `por_talle` y `generar_pieza` toma el del
  talle (cada talle tiene su «00» a su tamaño). `extraer_personalizacion` para el camino B ya no
  mira capas. Verificado: mesa 1 talle M → nombre 200 pt, número 1150 pt, dos pasadas (negro,
  blanco); la pieza generada con «Jugador / 10» estampa JUGADOR y 10 en vector y no queda
  «NOMBRE» ni «00» como texto (`scratchpad/prueba_pers.py`, render `pieza_pers.png`).
  **EL CUELGUE (visto con py-spy).** Al abrir Moldería, el acordeón «Nombrar talles» pide
  `GET /api/plantilla/variantes` → `variantes_molde.analizar` → `get_drawings()` del molde
  ENTERO dentro del servidor, con el GIL: 4,5 GB, 690 s de CPU y el servidor sin aceptar
  conexiones (`curl` 000, `ERR_CONNECTION_REFUSED`) durante minutos. Pasó dos veces antes de
  encontrarlo. FIX: para el camino B el endpoint responde con los talles del registro sin abrir
  el archivo. **Regla:** en un molde de 123 MB, cualquier `get_drawings()` del archivo entero
  dentro de un request cuelga el servidor; se busca con `py-spy dump --pid` (ahora instalado).
  Quedan otros dos puntos que abren el archivo (`_falta_nombrar_variantes`, `agregar pieza`) que
  el camino B no toca. También: los `print` del servidor lanzado con `nohup` se perdían por el
  buffer (`PYTHONUNBUFFERED=1` al lanzar). Y **la 386 de ayer sí borró un efímero del usuario**:
  «Nuevo pedido» desde la sesión de prueba mandó a `limpiar_efimeros` los moldes del pedido
  anterior del navegador, y uno era el «CAMISETA JUGADOR» del taller (efímero, 24 h de vida;
  sin nombres puestos) — el endpoint no mira dueño. Anotado para el usuario.
- **2026-09-03 (386) — LA SUBIDA DEL CAMINO B RESPONDE EN 26 s (era 64), Y NOMBRAR / ETIQUETA COMO
  EN MOLDERÍA.** Reporte: «cargué el archivo y demoró 1 minuto en cargarlo y detectar las piezas»
  + «nombrar las piezas y la etiqueta debe ser tal cual la configuración: primero nombramos todas
  las piezas de todos los talles y después elegimos el talle guía y ahí colocamos la etiqueta».
  **(a) El minuto, medido mesa por mesa** (`scratchpad/medir_alta.py`): 12,5 s adivinando si el
  archivo trae diseño (`parece_molde_con_diseno`, `get_drawings` de dos mesas) ANTES del alta; 54 s
  de contornos (`get_drawings`, 10 s la mesa más pesada) y 107 s de páginas por talle (pikepdf,
  20 s la más pesada) — en paralelo, el tiempo es la mesa más pesada haciendo las dos cosas.
  **FIX:** el front manda `con_diseno=1` cuando el archivo entra por «Cargar molde con diseño
  incluido» y el servidor no adivina (el alta avisa igual si no hay piezas con máscara); y el
  desplegado quedó en **dos etapas** (`desplegar_mesa(contornos=, paginas=)`): la subida hace sólo
  los contornos (`alta_molde_con_diseno(..., paginas=False)`) y las páginas por talle las arma
  `_prewarm_desplegado` en un hilo después de responder (una mesa por proceso). El JSON lleva
  `paginas: true` sólo cuando el PDF está; `_leer_desplegado` devuelve `pdf: None` si no, y
  `ruta_desplegada` arma esa mesa en el momento si la tizada llega antes. Medido por HTTP: **26 s**
  la respuesta, las páginas listas 40 s después sin que nadie espere.
  **(b) Nombrar sobre TODOS los talles.** `GET /api/plantilla/deteccion_todas` para el camino B ya
  no da 409: devuelve `piezas_con_diseno.visor_junto(_visor_leer(pid, todo=True), registro)` — los
  20 visores por talle acomodados en una grilla casi cuadrada (5×4; apilados en una columna daban
  una tira de 1,5 × 26 m ilegible), con `talle`, `mesa`, `t_idx`, `pieza_idx`, `idx` global, `name`
  y `filas` (dónde va cada talle, para rotularlo). Front: estado `todasB` (lo carga
  `cargarMoldeOperario` junto con la detección), `canvasLayout` lo toma como fuente en el pedido
  mientras no se ubica la etiqueta (`_todasB_on`), la columna de talles pasa a **ojitos** (oculta /
  muestra, con ojo general `arteb-ojo-todos`), tocar una pieza elige sus **homólogas en todos los
  talles** (`_homologasB`: misma mesa + mismo índice — en el camino B la correspondencia es
  exacta), `MapeadorArteVisual` tiene **recuadro de selección** en modo nombrar
  (`iniciarRubberVisor` + `onRubberNombrar`; Shift+arrastre sigue siendo pan) y `data-idx` en cada
  pieza, el rótulo de cada pieza deja de ser rojo en ese modo, y `nombrarSeleccionB` renombra UNA
  vez por pieza aunque la selección la traiga 20 veces. ⚠️ `etqNombres` va vacío en ese modo: sus
  claves son idx del talle guía y en el lienzo junto pisarían las primeras 9 piezas.
  **(c) Etiqueta sobre el talle guía.** Con todo nombrado, «2 · Etiqueta» vuelve al visor de un
  talle; la columna dice «Talle guía» y el talle que se toca es sobre el que se ubica (la posición
  es relativa: vale para todos). Verificado en el navegador de punta a punta: ojo (180 → 171
  piezas), recuadro (2 elegidas en todos los talles), nombrar (20 «Espalda», una por talle, con un
  solo POST), cambiar guía a M y ubicar (1 de 9). **Lo que salió mal en la prueba:** un molde
  efímero de OTRO usuario en la lista daba 403 al renombrar (guarda de dueño, correcto) y una
  selección que quedó viva de un recuadro anterior se toggleó con los clicks siguientes — es el
  gesto de Illustrator, no un bug, pero hay que mirar el contador antes de nombrar.
- **2026-09-03 (385) — «VOLVER» EN TODO EL PEDIDO.** Pedido del usuario: poder navegar entre el
  inicio (las dos formas de armar el trabajo) y los pasos. Faltaban dos: la pantalla «Armar con
  base» no tenía forma de volver a la bifurcación (una vez elegida, no se podía pasar a cargar
  un molde con diseño sin reiniciar el pedido) → `BtnVolver` «← Inicio» (`setVistaDiseno(null)`,
  ancla `pedido-volver-inicio`); y en «Nombrar piezas» del camino B el volver decía «← Moldes»
  y mandaba al paso 2, que ese camino no usa → si el molde activo es del camino B (`_esB`) va
  «← Cargar moldes» (`setVistaDiseno('con_diseno')` + `setPedidoPaso('diseno')`, ancla
  `arte-volver-cargar-b`); en los demás sigue «← Moldes». Los otros pasos ya tenían el suyo en
  `BarraPaso`. Entradas nuevas en `diccionario.js`. Verificado en el navegador el «← Inicio»
  (ida y vuelta); el de «Cargar moldes» sólo por build (requiere subir el archivo de 123 MB).
- **2026-09-03 (384) — ⚡⚡ EL MOLDE DESPLEGADO: el archivo se lee UNA vez, al cargar (el pedido de
  5 prendas pasa de 15 min a 63 s).** Pedido del usuario: estudiar cómo `Prueba para tizada` carga
  el archivo y arma la tizada en segundos, y replicarlo o mejorarlo. **Lo que hace el otro:** parsea
  el PDF una sola vez a una escena en memoria (`sceneBuilder.js`), detecta y acomoda sobre eso en
  un worker, y exporta un PDF **plano** escribiendo cada trazado por colocación (`pdfExport.js`).
  **Lo que hacíamos nosotros, medido con cProfile sobre el pedido real (motor 356 s + RIP 542 s):**
  de los 356 s del motor, **328 eran RE-LEER EL ARCHIVO** por pedido — 119 s aislando el talle de
  cada (mesa, talle) (parsear de 398 mil a 1,2 millones de operadores por mesa, 3-13 s cada vez),
  109 s de `get_drawings` de las 9 mesas y 100 s de `extraer_personalizacion` (tres recorridos del
  archivo). De los 542 s del aplanado, **367 eran `unparse_content_stream` con TUPLAS**: acepta
  `(operandos, op)` y `ContentStreamInstruction`, pero con tuplas tarda **40×** (322 mil ops: 16,6
  s vs 0,4 s) y `aplanar_rip` armaba todo con tuplas; además cada nivel de anidado (página →
  envoltorio de `show_pdf_page` → pieza → mesa) re-parseaba lo que el de abajo acababa de escribir.
  **FIX (1) — el desplegado** (`piezas_con_diseno.py`, «EL MOLDE DESPLEGADO»): el alta deja en
  `entrada/<pid>/desplegado/` un `m{mesa}.pdf` con **una página por talle, ya aislada y podada**
  (byte a byte lo que hacía `aislar_capa(podar=True)` en cada tizada, verificado) y sólo con los
  recursos que usa (22 fuentes → 3-4), más `m{mesa}.json` con el **sello** del archivo (tamaño +
  fecha), el orden de los talles y los **contornos** de cada talle. `piezas_de_mesa` lee de ahí;
  `pagina_molde` del motor toma la página de ahí (`ruta_desplegada`, que la arma si falta o el
  sello cambió: un molde viejo se vuelve rápido la primera vez); `extraer_personalizacion` guarda
  su resultado en `desplegado/personalizacion.json` por sello y, sin capas de campo, devuelve `{}`
  sin recorrer nada. El alta va **una mesa por proceso** (`desplegar_molde`, ProcessPool; el
  servidor pasa `procesos_render()`, los scripts van en serie porque el spawn de Windows re-importa
  el módulo principal). En `molde_real`, `_raspar_pintado` quedó partido en `_mapa_oc` +
  `_bloques_oc` (árbol de bloques OC, una vez por mesa) + `_saltar_bloques` + `_raspar_instrucciones`,
  con **bytes idénticos** al código anterior en 6 casos (mesas 1/3/9, con y sin poda).
  **FIX (2) — el aplanado** (`aplanar_rip.py`): `_instr` (siempre `ContentStreamInstruction`, nunca
  tuplas), `_flatten` memoiza las **instrucciones** aplanadas por objeto y las devuelve (no
  reescribe los XObjects, que quedan huérfanos y se borran), `_procesar_contenido` recibe las
  instrucciones de la página en memoria (no re-parsea). **Pixel-idéntico** a la salida anterior en
  la hoja del camino B (46 MB, 1,6 millones de ops) y en una hoja real del camino A (molde + arte
  de producción, copiados a un temporal, registro leído de la base). Y **sin cambiar la política
  del archivo**: sigue saliendo totalmente plano, que es además lo que hace el proyecto de
  referencia — la «decisión de aplanar un solo nivel» de (383) ya no hace falta.
  **RESULTADO (pedido real de 5 prendas):** motor 356 → **24 s** · aplanado 542 → **36 s** ·
  personalización 100 → **0 s** · alta ~60 s en serie → **55-71 s con 6 procesos, desplegado
  incluido** (en serie serían minutos: 13-45 s por mesa) · subir + tizada + RIP = **115 s**; con
  el molde ya cargado, tizada + RIP = **63 s**. El desplegado ocupa **118 MB** por molde (9 mesas
  × 20 talles, 7,6 MB por mesa) y se borra con el molde (vive en su carpeta de `entrada/`) y al
  re-subir uno del camino A encima. Contrato nuevo: `verificar_desplegado.py` (bytes, píxeles,
  contornos, sello, alta en paralelo = en serie, recursos podados). Los demás contratos siguen
  verdes. **Lo que salió mal:** el primer perfil del alta en serie dio 403 s porque corrió junto a
  otras dos pruebas pesadas y antes de dos optimizaciones (juntar los nombres de recursos por regex
  sobre los bytes en vez de operando por operando: 9 s por mesa; y no recorrer 398 mil
  instrucciones por talle: 6 s por mesa) — medir con la máquina ocupada engaña. Y el servidor de
  prueba «8051» estaba en realidad escuchando en **8070** (`netstat` lo dice; `curl` a 8051 daba
  000): se mató por PID y se relanzó en 8051 con las variables del `.bat`.
- **2026-09-03 (383) — ⚡ LA TIZADA DEL CAMINO B ARRASTRABA LOS 20 TALLES EN CADA PIEZA (586 MB →
  46 MB).** Reporte del usuario: «va 6 minutos y paso por poco la mitad», contra el proyecto de
  referencia que «lo hace en segundos». **CAUSA, medida:** el content-stream de una mesa trae
  **398.653 operadores** (los 20 talles encimados) y, aislado un talle, **sólo 75 pintan**.
  `_raspar_pintado` convertía el pintado ajeno en `n` pero **dejaba los trazados escritos**, así
  que cada pieza copiaba los 398 mil (7,6 MB). **FIX:** `aislar_capa(..., podar=True)` —opt-in,
  sólo camino B— borra los operadores de construcción de trazado suprimidos y, además, los
  **bloques OC completos que quedan balanceados en `q/Q`** (los desbalanceados se podan operador a
  operador: si un bloque abre estado y no lo cierra, lo de después lo hereda y borrarlo cambiaría
  el dibujo — es el bug del editable que salía verde).
  Resultado: 398.347 → **20.186** operadores por pieza · pieza de 23,1 → **1,6 MB** · hoja de 1
  prenda 117 → **9 MB** · hoja de 5 prendas 586 → **46 MB** · el pedido pasó de no terminar en 18
  min a **11,5 min**. 🔴 Con **0 píxeles distintos** de 6.475.275 comparados
  (`verificar_poda_camino_b.py` §2). El camino A no cambia: sus contratos (`marcas_proceso`,
  `mesa_larga`, `referencia_medida`) siguen verdes.
  También: **`aplanar_rip._flatten` memoizado** — aplanaba el MISMO XObject una vez por colocación
  (45 veces en ese pedido), parseando y reescribiendo su stream cada vez.
  📌 **LO QUE QUEDA, y por qué el otro sistema tarda segundos:** de los 11,5 min, **402 s son el
  aplanado** y ya no hay basura que sacar (los 20.186 restantes son el trazado real: 16.505 curvas
  para 66 rellenos). La diferencia es estructural: `Prueba para tizada` parsea el PDF una vez y
  **escribe un PDF plano** emitiendo los paths (`pdfExport.js`); nosotros componemos con XObjects y
  los des-anidamos para el RIP, y eso mete el contenido inline una vez por colocación (~900.000
  operadores en la hoja). La salida sería **aplanar un solo nivel** (piezas como XObject de la
  página, 27 objetos y 45 `Do`), pero eso toca la política del archivo que va a la imprenta —
  `aplanar_rip.py` existe porque los XObjects anidados daban «error RIP» — así que **se decide con
  el usuario, no por cuenta propia**.
- **2026-09-03 (382) — LAS DOS FORMAS, MITAD Y MITAD · LA ESPERA ES UN CÍRCULO · Y UN MOLDE QUE
  YA NO ESTÁ SE SACA DEL PEDIDO.** Pedido del usuario, más un bug que él encontró usándolo.
  **(a)** Las dos formas de armar el pedido pasan a ser **dos tarjetas que ocupan el espacio libre,
  mitad y mitad**, con un color sutil del sistema cada una (cian / magenta) en el borde y en un
  resplandor de fondo — no en un relleno plano, que taparía el texto.
  **(b)** 🔴 **La espera de la subida es un CÍRCULO y no una barra** (`CargaCircular`): mientras el
  archivo viaja marca el **% real**; cuando llega, el servidor recién empieza a leerlo (minutos con
  100+ MB) y el anillo **gira** con el reloj corriendo. Una barra llena y quieta se lee como
  «colgado» y estimar el resto sería inventar: o es el número real, o gira.
  **(c)** 🔴 **BUG QUE ENCONTRÓ EL USUARIO: el pedido quedaba colgado en «Cargando el molde…».** El
  pedido vive en `localStorage` y los moldes del camino B son EFÍMEROS: al re-subir el archivo, el
  pid guardado dejó de existir y la pantalla esperaba para siempre mientras el servidor contestaba
  404 y 409, sin decir nada. Ahora un efecto **saca del pedido los moldes que ya no están en el
  catálogo** (de `disenoMoldes`, `disenoVars`, `moldesEfimeros` y `moldesBDiseno`) y lo avisa una
  vez; y el paso Arte, sin molde, **dice qué pasó y ofrece ir a elegir uno** en vez de «Cargando».
  Estaba anotado en el plan como «reconciliación al montar» y no se había hecho: la lección es que
  un estado guardado en el navegador que apunta a algo borrable **necesita** su reconciliación.
  📌 **`frontend/src/App.css` NO LO IMPORTA NADIE** (sólo `index.css`, desde `main.jsx`).
  Comprobado: sus selectores no están en el bundle. Escribir estilos ahí compila sin error y no
  aplica nada — pasó en esta tanda y costó un rato de búsqueda. **El CSS va en `index.css`.**
- **2026-09-03 (381) — EL PEDIDO ARRANCA CON DOS BOTONES, Y LA CARGA DEL CAMINO B ES SU PROPIO
  ESPACIO.** Pedido del usuario. Al entrar al pedido: **«Armar con base»** (los pasos de siempre) y
  **«Cargar molde con diseño incluido»**. **No son excluyentes**: un pedido puede llevar de los dos
  (una camiseta con el diseño adentro y un short del catálogo con su arte, en la misma tizada), así
  que la bifurcación es una VISTA del paso 1 (`vistaDiseno`) y no un paso nuevo — tocar las claves
  de `pedidoPaso` habría roto la persistencia del wizard, `pasoItems` y los tutoriales grabados.
  **El espacio de carga:** se sueltan **varios archivos** de una vez y **el nombre del molde sale
  del archivo** (no se escribe). Se suben de a uno —cada uno son 100+ MB y los procesa PyMuPDF:
  mandarlos juntos sólo haría que todos tarden más y que la barra no signifique nada—. Después
  aparecen como botones: se tocan los que van juntos y se escribe **el nombre del diseño una sola
  vez** (escribirlo por molde invita a «JUGADOR» y «jugador», que serían dos diseños).
  🔴 **Y de cada molde se elige DE QUÉ COLUMNA DE TALLE toma sus medidas** (`mapeo_columnas.talle`,
  vía `/api/productos/config_mapeo`). Es lo que distingue una camiseta de un short cuando la
  planilla lleva «Talle» y «Talle short» —la planilla real del usuario las tiene—: sin eso el short
  tomaría el talle de la camiseta y saldría del tamaño equivocado, impreso y cortado.
  **El nombrado pasa a ser el gesto de la pantalla de edición**: tocar las piezas en el visor (se
  suman) o en la lista, escribir UN nombre y nombrarlas todas; si son varias se numeran solas con
  la regla de siempre («Tira» → «Tira 1», «Tira 2»). El lote se manda **de a una y en orden**: cada
  renombrado reescribe el registro entero, así que dos a la vez se pisan y una se pierde.
  ⚠️ Falta el arrastre de recuadro de esa pantalla; el clic múltiple sí está.
- **2026-09-03 (380) — ⚡ CAMINO B: NOMBRAR PIEZAS ABRE AL INSTANTE (46 s → 0,002 s).** Pedido del
  usuario: esa pantalla tiene que andar «súper flash sin importar el diseño de cada molde»,
  trabajando **sólo con los bordes**. **Lo que costaba, medido:** armar el visor de UN talle = 52 s,
  y los 52 son `get_drawings()` leyendo los dibujos de las 9 mesas (1.516 items por mesa) para
  quedarse con 140 recortes — no era el tamaño de la respuesta, que ya eran 5 KB: era **abrir el
  archivo**. **La salida:** el ALTA ya recorre las 9 mesas × 20 talles, así que arma ahí mismo el
  visor de TODOS los talles (gratis: los contornos ya están leídos) y lo guarda en
  `visor_contornos.json` (103 KB los 20 talles). El visor lo sirve de ahí y **no abre el PDF nunca
  más**; el alta no tardó más por esto. `detectar_para_visor` quedó partida: `layout_visor` acomoda
  contornos YA LEÍDOS y la otra los lee del archivo.
  🔴 **Rápido y equivocado es peor que lento**: el contrato compara lo guardado contra lo que
  saldría del archivo, pieza por pieza y contorno por contorno. Y al re-subir por el camino A el
  visor guardado **se borra** — si no, mostraría las piezas del archivo anterior y, como ya no se
  abre el PDF, nadie se enteraría. Contrato: `verificar_visor_rapido.py`.
- **2026-09-02 (379) — CAMINO B, LO QUE FALTABA: LA ETIQUETA DESDE EL PEDIDO, LA PANTALLA DEL
  ADMIN Y «TERMINAR PEDIDO».** Con esto el camino B queda completo de punta a punta.
  **(a) La etiqueta la ubica el cliente**, en la 2ª solapa del panel del pedido, que se destraba
  con todo nombrado (sin nombre no hay qué escribir en ella). Toca el borde y el punto se apoya en
  el contorno. 🔴 **`_snapAContorno` pasó a vivir a nivel de módulo y la usan LAS DOS pantallas**
  (Configuración y el pedido): con una copia en cada una, la etiqueta caía distinto según dónde se
  la ubicara. Se manda **sólo `posiciones`** (el POST es *replace* y la forma es del admin), y se
  tira `_pvCache` o el paso Arte mostraría la etiqueta vieja.
  **(b) Pantalla «Molde con diseño»** en Configuración: borde, etiqueta y regla de nesting, con el
  aviso de que **alcanza a los moldes ya cargados** y a cuántos. Verificado: 3,5 mm en el molde con
  diseño y 2,0 en uno del camino A.
  **(c) «Terminar pedido»** en Resultados, sólo si el pedido tiene un molde con diseño. 🔴 Qué
  borrar **no sale sólo del estado del navegador**: se le suman los moldes del pedido marcados
  `efimero`, porque tras un F5 con el localStorage vacío ese estado no los tiene y el archivo de
  100+ MB se quedaría. Borrar de más no es riesgo: el servidor sólo toca los marcados.
  📌 El tope de `verificar_tdz.mjs` volvió a cortar el build: las funciones nuevas quedaban arriba
  de `showMsg`/`showError`. **Se mueven debajo de lo que usan; el tope no se sube nunca.**
- **2026-09-02 (378) — CAMINO B: EL PEDIDO COMPLETO, Y LA TRABA DE TELA QUE NO TRABABA.**
  Verificado desde la pantalla de punta a punta: subir → nombrar → tela → planilla → generar, y sale
  la hoja con su ficha. Los toggles salen gratis: la planilla mostró «Larga» **deshabilitado** con
  «el molde no contiene manga larga», deducido de los nombres que puso el cliente.
  🔴 **`_validar_pedido` no validaba nada sin variables**: recorría `variante_piezas`, que en un
  molde que va entero viene vacío → ninguna pieza se miraba y todas se habrían ido a la tela
  fantasma «Principal» de 180 cm, que es exactamente lo que esa traba existe para evitar. Ahora
  usa **`MP.partes_de_libre`**: `partes_de` sacado del motor a nivel de módulo (como ya estaba
  `tokens_pieza`, y por el mismo motivo — el servidor tiene que validar con LA MISMA regla con la
  que después se genera). Con los toggles aplicados, así que no reclama tela para una pieza que la
  fila no lleva.
  🔴 **RENDIMIENTO MEDIDO, pendiente serio**: una tizada de UNA prenda tardó **~21 min**, de los
  cuales el motor entero fueron **134 s** y el **aplanado para el RIP ~19 min** sobre una hoja de
  114 MB. El peso NO es basura: aislando una mesa da 7,6 MB y `remove_unreferenced_resources()` no
  baja nada — es el dibujo. Hay que perfilar `aplanar_rip.py` antes de tocarlo, y la salida nunca
  es rasterizar. Detalle en `MOLDE_CON_DISENO.md` §7-E4.
- **2026-09-02 (377) — CAMINO B, EL FRONT DEL PEDIDO: SUBIR Y NOMBRAR SIN SALIR DEL WIZARD.**
  Tarjeta «Molde con el diseño adentro» en Pedido → Mis artículos (el mismo modal sirve para las
  dos formas), con **espera honesta en dos tramos**: el % REAL de la subida por XHR —`fetch` no da
  progreso de subida y el archivo pesa >100 MB— y después «leyendo y detectando» con el reloj
  corriendo. Nunca un porcentaje inventado. El molde queda **elegido** y NO se sale del wizard
  (`subirMiMolde` termina en `abrirConfigMiMolde`, que te lleva a Configuración; ésta no).
  El **nombrado va en el paso Arte**, en el panel derecho: prop nueva `panelFijo` del visor, que en
  camino B reemplaza al panel de «Diseños» (estaría pidiendo un arte que el molde no lleva). La
  lista muestra la **miniatura del contorno** de cada pieza: con nueve «sin nombre» es lo único
  que deja saber cuál es cuál. El predicado `_itemListo(did, mid)` reemplaza a `arteCargado[...]`
  en los cuatro gates globales; 🔴 **no se reusa `arteCargado` para el camino B** — su cortocircuito
  en `cargarPreviewPiezas` es lo que impide pedir el dibujo pesado, y marcarlo dispararía
  `preview_piezas` sin arte, en loop.
  🔴 Después de renombrar hay que **volver a pedir la detección**: los nombres del panel salen de
  `nombres_existentes` (la detección), no del catálogo — sin eso el nombre se guardaba bien y la
  pantalla seguía diciendo «sin nombre», y el usuario lo escribía dos veces.
  📌 `verificar_tdz.mjs` (tope congelado de «usado antes de definirse») **cortó el build dos veces**:
  la función nueva quedaba arriba de `plantillaComun`, `toggleMoldeEnDiseno` y `showError`. Se
  MUEVE la función debajo de lo que usa; el tope no se sube nunca.
  Verificado en el navegador de punta a punta: subir → nombrar 9 → el gate a verde → las telas
  reconocen los 6 genéricos.
- **2026-09-02 (376) — CAMINO B, E5: UNA SOLA CONFIGURACIÓN PARA TODOS LOS MOLDES CON DISEÑO, Y
  VIVA.** El cliente que sube uno desde el pedido no configura borde, etiqueta ni nesting: lo deja
  el admin UNA vez en `cat["config_con_diseno"]` y vale para todos — **también para los ya
  cargados** (el molde APUNTA ahí, no se le copia nada: decisión del usuario). Patrón calcado de
  `nesting_presets`. **Punto único de resolución**: `_cfg_con_diseno` / `_borde_de` /
  `_etiqueta_de`, por donde ahora pasan los seis lugares que leían `prod.get("borde_corte")` a
  mano (clave del caché del preview, preview, `generar`, `generar_multi`, ficha y los GET del
  molde) — si uno leyera el del molde y otro el global, lo que se ve dejaría de ser lo que se
  estampa. 🔴 **Lo global es la FORMA de la etiqueta; el DÓNDE (`posiciones`) es del molde**, lo
  marca el cliente pieza por pieza: `set_etiqueta` es *replace*, así que en camino B conserva las
  posiciones y descarta el resto del cuerpo (si no, guardar una posición desde el pedido clavaba
  la forma en el molde y ese molde dejaba de seguir al admin, en silencio).
  🔴 **El valor RESUELTO entra en `_piezas_base_clave`**: es lo que hace que el cambio del admin se
  vea solo en el paso Arte. Sin eso salía bien en la tizada y viejo en la pantalla.
  `POST /api/productos/borde_corte` sobre un molde B → **409** (una pantalla que parece guardar y
  no cambia nada es peor que un error). Nuevos: `GET/POST /api/config_con_diseno` (el POST pide
  `config.editar` y devuelve a cuántos moldes alcanza). Contrato: `verificar_config_con_diseno.py`.
- **2026-09-02 (375) — CAMINO B, E4: LA TIZADA SALE DEL PROPIO MOLDE (sin arte y sin mapeo).**
  Verificado generando la hoja del archivo real **y mirándola**: 180 × 77 cm con las 9 piezas
  estampadas, su borde de corte y su etiqueta. `generar_pedido` acepta `arte=None` y la rama se
  elige por **la marca en disco** (no por «no vino arte»: así sobrevive al ProcessPool y no se
  adivina nada). La rama de `_armar_base` es el ramal del ARTE CLÁSICO con la página sacada del
  molde — misma traslación, mismo clip, misma escala —, salteando todo lo del arte separado
  (`cm_encajar`, editables, objetos agregados): la pieza ya está en su lugar y a tamaño real
  (medido: 48,7 × 73,8 cm contra 48,5 × 73,6 del registro; la diferencia es el borde).
  🔴 **`pagina_molde` nueva, NO reusar `pagina_arte`**: ése llama a
  `limpiar_capas_conservando_talle` + `geometrias_base`, que descarta los trazados que coinciden
  con la moldería base y TODO el texto de la capa — en el camino B la moldería base **es** el
  dibujo, así que borraría la pieza y los placeholders. Va `aislar_capa`, que conserva lo pintado
  del OCG del talle **con sus recortes** (que son la pieza). Destrabado además el servidor:
  `generar_multi` descartaba el molde **en silencio** (`continue` por no tener
  `validacion_arte.json`) y la tizada llegaba sin sus piezas; `_piezas_base` también, y ése no es
  opcional (si el preview no pasa por la misma rama del motor se rompe la LEY «arte = tizada»).
  Clave del caché del preview a **v15** con el camino B adentro.
  ⚠️ **Pendiente que destapó la prueba: el nombre/número NO se estampan.** El archivo real tiene
  20 capas y las 20 son TALLES: no hay capa `nombre`/`numero`, que es de donde
  `extraer_personalizacion` los saca, así que sale el «NOMBRE» dibujado en el diseño. (El
  auto-descubrimiento de capas se apagó para el camino B: si no, tomaría los 20 talles como campos
  y estamparía cualquier texto.) A decidir con el usuario — ver `MOLDE_CON_DISENO.md` §6.
- **2026-09-02 (374) — CAMINO B, E2+E3: EL ALTA EFÍMERA DESDE EL PEDIDO Y EL NOMBRADO.** Probado
  por HTTP con el archivo real (123 MB): alta en ~95 s, 9 piezas · 20/20 talles, visor de 7 KB,
  nombres que persisten y borrado que no deja nada. **Decisión del usuario: el molde del camino B
  es EFÍMERO** — se sube para ESE pedido y no queda guardado (`efimero: true` + `efimero_visto`;
  lo borra `POST /api/pedido/limpiar_efimeros` y, si quedó huérfano, `_barrer_efimeros` al
  arrancar). 🔴 El barrido borra **por el flag y por la fecha, nunca «los que sobran» ni por
  nombre** (§8 dice por qué: ya costó 3 moldes del usuario). Va DENTRO del catálogo a propósito:
  +20 puntos del camino caliente resuelven por catálogo y el primero que se olvidara daría un
  `prod = None` silencioso. **Nombrar en el camino B es RENOMBRAR**, no agrupar
  (`PD.renombrar` + `POST /api/plantilla/pieza_renombrar`): el registro ya está completo y los
  talles son capas de la misma mesa, así que `alta_plantilla_manual` —que asume UNA mesa y
  empareja por forma— lo destruiría; `etiquetas`, `grupo_pieza` y `emparejado` devuelven **409**
  sobre un molde B. Detalle completo en `MOLDE_CON_DISENO.md`.
- **2026-09-02 (373) — 🔴 TRES AGUJEROS QUE HABRÍAN APARECIDO RECIÉN AL GENERAR LA TIZADA.**
  (a) **`idx_mesa` no se persistía.** Desde que el registro vive **sólo en MSSQL** (sin espejo en
  disco), lo que no tiene columna no existe: `dbo.pieza_talle` no la tenía, así que el índice
  DENTRO de la mesa se evaporaba en el primer round-trip y `_armar_base` volvía a indexar por
  `pieza_idx` (el índice dentro del TALLE) → con 9 mesas de 1 pieza, `IndexError` o pieza
  equivocada. Columna nueva (`ALTER … NULL`, idempotente) + chequeo cacheado `COL_LENGTH` para que
  una base sin migrar **degrade** en vez de tumbar el camino A. 🔴 Al leer, la clave se escribe
  **sólo si no es NULL**: `info.get("idx_mesa", info["pieza_idx"])` cae al default sólo si la
  clave **falta**; un `None` haría `_pm[None]` → TypeError en TODOS los moldes del camino A.
  (b) **Dos cachés servían la detección vieja para siempre**: el alta detecta y marca DESPUÉS, así
  que misma ruta + mismo mtime da 9 piezas o 619 según la marca. `_DET_CACHE` ya lo tenía;
  `_PZS_CACHE` y el caché **en disco** (`{mtime}_dv2_…` → `dv3` + sufijo `_b`) no. Y el mtime es un
  entero de SEGUNDOS: dos subidas en el mismo segundo se servían la detección de la otra.
  (c) **El visor no precargaba los nombres puestos** (`nombres_existentes` vacío): filtraba
  `info["mesa"] == mesa` y en el camino B `mesa` es `None` — la misma guarda que ya tenía el filtro
  por variable diez líneas más abajo.
  📌 **Bug preexistente ENCONTRADO Y NO TOCADO:** en `/api/plantilla/etiquetas` (`servidor.py`) el
  `_guardar_registro` quedó **después de un `return`**, o sea inalcanzable: ese endpoint hoy **no
  persiste nada** (el nombrado real lo hace `grupo_pieza`). Moverlo resucita un camino de escritura
  viejo que nadie está probando → se decide aparte, no dentro de esta feature.
- **2026-08-31 (372) — CAMINO B, E1: LAS PIEZAS DE UN MOLDE CON EL DISEÑO ADENTRO.** Módulo
  `piezas_con_diseno.py` + contrato `verificar_molde_con_diseno.py`. **La detección de hoy no sirve
  para ese archivo**: `extraer_piezas_mesa` trata cada trazado como una pieza, así que una prenda
  con el diseño adentro da **619 «piezas»** en vez de 9 (medido con `CAMISETA JUGADOR.ai`). El
  hallazgo: **la forma de la pieza ya está en el archivo** — Illustrator la guarda como MÁSCARA DE
  RECORTE y PyMuPDF la entrega en `get_drawings(extended=True)`. Se leen los recortes de la capa del
  talle, se descarta el marco de la mesa, se agrupan por solape (union-find sobre bounding boxes:
  son 3 a 7 por mesa, no hace falta rasterizar) y el de mayor área es el contorno. Salida con la
  MISMA forma que `molde_real._contorno_de_drawing`, para que registro, nido, visor y motor no se
  enteren. 🔴 Trampa: descartar el marco «por área > 95 %» **se come piezas reales** (una tira de
  28,7 cm en una mesa de 29,0; un frente que ocupa el 97 %) → se compara contra el rectángulo de la
  página con 1 pt de tolerancia. **Todo el camino B está en `MOLDE_CON_DISENO.md`** (§0.b).
- **2026-08-31 (371) — 🔴 LA CAUSA REAL: EL FILTRO DE OBLIGATORIAS SE COMÍA LAS FILAS DE
  MUESTRA INTERNAS.** El usuario insistió («la ficha técnica es la ficha técnica») y tenía razón:
  la 370 tapaba una parte, pero el agujero de fondo estaba más abajo. `_traducir_prendas` **no la
  usa sólo el pedido**: el sistema arma **filas sintéticas** para DIBUJAR — el molde guía de la
  ficha (`_molde_guia_ficha`, ~6395), el preview de piezas del arte (~3847) y el visor (~6118). Esas
  filas traen lo mínimo (`talle`, `nombre`, `numero`, la variable) y **no tienen** las columnas que
  el usuario marcó obligatorias — si marchó «Diseño», el filtro nuevo las descartaba: sin prendas
  → sin piezas → **la ficha sin su molde guía**. FIX: `_traducir_prendas(..., exigir_obligatorias=True)`
  — el pedido real (~6586) lo deja en True; las tres muestras internas lo apagan.
  📌 LECCIÓN (la misma de la 370, un nivel más abajo): **antes de poner una regla de negocio
  dentro de una función, mirar QUIÉN MÁS la llama.** «Qué se fabrica» es una regla DEL PEDIDO; meterla
  en el traductor se la aplicó también a los dibujos internos, que no fabrican nada. Enumerar los
  llamadores (`grep -n "_traducir_prendas("`) habría evitado las dos entradas. CONTRATO §4b en
  `verificar_columnas_obligatorias.py` (verifica que la misma fila de muestra se descarte como
  pedido y salga como muestra, y que las tres llamadas internas estén apagadas).
  ✅ VERIFICADO CONTRA LOS DATOS REALES: la plantilla del usuario tiene marcadas «Talle», «Talle
  short» y «Diseño»; con el filtro puesto, la fila de muestra de la ficha daba **0 prendas en los
  dos moldes** («camiseta asque» y «Camiseta de futbol») y ahora da 1 en los dos.
  ⚠️ COLATERAL QUE ESTO DESTAPÓ: la muestra del arte (~3848) es la que dibuja el **preview de
  piezas** del paso Arte — también se quedaba sin prendas desde la 367. Y **tres verificadores
  estaban rotos en silencio** por lo mismo, porque copian los `datos` reales del usuario a un
  temporal y heredan sus obligatorias: `verificar_etiqueta_nombre.py`, `verificar_etiqueta_posicion.py`
  y la herramienta `medir_nesting.py` — sus filas también son muestras y ahora pasan
  `exigir_obligatorias=False`. 📌 Los contratos que copian datos reales cambian de resultado cuando
  cambia la CONFIGURACIÓN del usuario: **hay que correrlos todos, no sólo el de la feature tocada**.
- **2026-08-31 (370) — 🔴 LA FICHA PERDIÓ LOS MOLDES AL IGNORAR FILAS (efecto colateral de la
  369).** Reporte del usuario: «¿por qué ahora en la ficha técnica no se ve todo lo que se veía,
  información de los moldes y etc?». CAUSA: los **moldes guía** de la ficha se arman recorriendo
  LAS PRENDAS (`_guias_ficha`, dentro del bucle de `translated`). Al empezar a ignorar las filas
  incompletas, esas filas dejaron de generar prendas… y con ellas se fueron sus guías: la ficha
  perdió moldes, variables y combinaciones de toggles que antes mostraba. Las dos cosas conviven y
  no se contradicen: **la TABLA** de la ficha lista sólo lo que se fabricó (eso es lo que se pidió
  en la 369 — la ficha es la hoja con la que el taller controla lo que salió), pero **los MOLDES
  GUÍA son la referencia del trabajo** (qué prenda es, qué piezas lleva) y tienen que estar aunque
  alguna fila se haya ignorado. FIX: las guías se arman igual que antes con las prendas —para
  conservar su variable, sus toggles y su muestra de nombre/número— y después se COMPLETAN con los
  moldes del pedido (`molds` + `vars_por_diseno`): si un molde no quedó representado, se agrega su
  guía. No se duplica un molde que ya tiene guía para ese diseño. CONTRATO §5 en
  `verificar_columnas_obligatorias.py`.
  📌 LECCIÓN: filtrar la entrada de un pipeline afecta TODO lo que se derive de ella. Al sacar
  filas hay que preguntarse qué más se calculaba a partir de esas filas — acá, la ficha entera.
- **2026-08-31 (369) — UNA FILA VACÍA NO SE PREGUNTA, Y LO IGNORADO TAMPOCO VA A LA FICHA.** Dos
  correcciones del usuario sobre el cartel de la 367:
  **(a) «esas 3 que no tienen nada son ignorables por completo».** El cartel preguntaba por CADA
  fila incompleta, incluidas las que están en blanco —las que quedan de más al agregar filas—. Una
  fila vacía no es un olvido: sobra. Ahora sólo se pregunta por las **empezadas** a las que les
  falta un dato; las vacías se ignoran sin ruido. 📌 Ya existía `filaVacia()` en App.jsx con el
  criterio correcto (los BOTONES no cuentan: «Manga: corta» viene puesto solo, así que una fila en
  blanco los tiene igual) — escribí una copia sin verlo y el parser lo cantó («Identifier
  'filaVacia' has already been declared»): **antes de escribir un helper, buscar si ya está**.
  **(b) «si ignora una fila la ignora para la ficha técnica también».** La ficha es la hoja con la
  que el taller controla lo que salió: listar filas que no se imprimieron la vuelve mentirosa.
  Ahora lo que se manda como planilla de la ficha son las MISMAS filas que se fabrican.
  ⚠️ Para lograrlo, `generarMulti` **recibe** las filas útiles de quien la llama (`filasQueSalen()`)
  en vez de calcularlas: sus helpers se declaran más abajo y usarlos ahí adentro es leerlos antes
  de tiempo — lo cortó el candado de la 368 (2 casos nuevos). Es la forma correcta igual: la
  función recibe lo que necesita.
- **2026-08-31 (368) — 🔴 EL CANDADO DE PANTALLA NEGRA AHORA MIRA App.jsx (tope congelado).**
  Hoy volvió a pasar y en el peor archivo: un `useMemo` nuevo usaba `cantidadVisible`, declarado 20
  líneas más abajo → «No se pudo cargar la aplicación» (dos veces seguidas, porque la primera vez
  lo moví a un lugar que TAMPOCO alcanzaba: hay que quedar debajo de TODO lo que se use, incluido
  lo del array de dependencias, que se evalúa en el render). `verificar_tdz.mjs` no miraba App.jsx
  porque arrastra **321 casos previos**, casi todos inofensivos (handlers leídos dentro de
  callbacks, no en el render). Solución: **congelar la cuenta**. Uno nuevo corta el build; cuando
  se limpie alguno hay que BAJAR el tope. Probado en negativo: reporta «1 caso NUEVO (tope 321,
  ahora 322)». 📌 Y la lección de siempre, ahora con número: en App.jsx este error no es un aviso,
  es la app que no abre.
- **2026-08-31 (367) — SE PREGUNTA ANTES DE ARMAR LA TIZADA, NO SE AVISA DESPUÉS.** Pedido del
  usuario sobre la 365/366: «no sólo que no active el botón: al menos tiene que llenar una fila. Y
  si de 2 filas una está incompleta, que salga un cartel ANTES de armar la tizada — "falta el dato
  de tal, ¿querés avanzar ignorando esa fila o cargar el dato?" con dos opciones: **Enviar igual**
  (usa sólo las filas que cumplen) y **Cargar dato** (cierra y vuelve a la planilla). Y el cartel
  de después, quitalo». Hecho tal cual:
  · **el botón «Enviar» no se activa si NINGUNA fila está completa** (dice qué falta);
  · con filas a medio llenar, al tocar «Enviar» sale el modal **«Faltan datos en la planilla»**:
    lista qué le falta a cada fila (número de fila + columnas), dice con cuántas se armaría, y
    ofrece «Cargar el dato» (cierra, seguís en la planilla) o «Enviar igual (N filas)»;
  · **se eliminó el aviso posterior** («4 fila(s) sin completar…»): la decisión ya se tomó antes y
    repetirla después era ruido sobre algo resuelto.
  El front usa el MISMO criterio que el servidor (columnas `obligatoria` que este pedido usa de
  verdad, `colActiva`), así que lo que muestra el cartel es exactamente lo que el motor va a
  ignorar. El modal nuevo entró al diccionario con su ficha (17/17 ventanas dibujables) para que
  el tutorial lo entienda.
  ⚠️ NO VERIFICADO EN PANTALLA: el cartel en sí. Llegar a la planilla en el sandbox exige cargar un
  arte (escritura) y ahí es sólo lectura. Verificado: que la app carga, que compila con los seis
  contratos, y el comportamiento del servidor por contrato. **Falta probarlo con una planilla real
  a medio llenar.**
- **2026-08-31 (366) — 🔴 UNA COLUMNA OBLIGATORIA QUE EL MOLDE NO USA NO SE PIDE.** Pregunta del
  usuario sobre la 365, y era un agujero de verdad: «¿y si pongo "Talle short" obligatoria pero la
  variante que elijo no lleva esa columna y no aparece? ¿hay lógica que detecte que ahí no debe
  pedirla?». NO la había: esa columna no se muestra en la planilla de ese molde, así que estaría
  SIEMPRE vacía y **no se habría fabricado NINGUNA fila** (lo confirma la prueba en negativo: 0
  prendas). AHORA el servidor exige sólo las obligatorias que ESE MOLDE usa, con el mismo criterio
  que la pantalla aplica para mostrarlas (`colActiva`): las de rol mapeable
  (talle/nombre/numero/manga) valen si el molde las mapea **por id** —«Talle» y «Talle short» son
  las dos role `talle`, y cada molde mapea la suya—; las demás (Diseño, dato libre) van siempre. Si
  después de filtrar no queda ninguna, vale el talle de ese molde. La Ayuda de la pantalla lo dice:
  «Sólo se pide en los moldes que usan esta columna». CONTRATO §3 en
  `verificar_columnas_obligatorias.py`: con «Talle short» obligatoria, un molde que usa «Talle» SÍ
  fabrica (y sólo se le exige «Talle»); un molde que usa «Talle short» no fabrica la fila que la
  tiene vacía. Probado en negativo.
- **2026-08-31 (365) — COLUMNAS OBLIGATORIAS, CONFIGURABLES POR PLANILLA.** Pedido del usuario,
  mejorando la 364: «debe tener en configuración cuáles son las columnas que debe tener sí o sí
  cargadas para que aparezca en la tizada, porque puede ser 1 o varias; el molde de ahora debe ser
  talle y diseño; eso se ajusta en la edición y creación de las planillas». La regla fija «sin
  talle no se fabrica» pasa a ser **configurable**: cada columna de la plantilla puede marcarse
  `obligatoria`, y la fila a la que le falte ALGUNA no se fabrica. Si la plantilla no marca
  ninguna, sigue valiendo el TALLE —lo mínimo sin lo cual no se puede cortar— así que **ninguna
  planilla vieja cambia de comportamiento sin que nadie lo pida**.
  · **PANTALLA** (Configuración → Planillas → tocar la columna): interruptor «Obligatoria para
    fabricar», con su Ayuda y un aviso en vivo («Las filas con "Talle" vacía se van a ignorar al
    generar»). Sin esto la feature no existiría: no habría dónde decir «talle y diseño».
  · **SERVIDOR**: `_traducir_prendas` descarta la fila incompleta y guarda QUÉ columna faltó en
    cada una; el pedido avisa «N fila(s) sin completar — les falta: Diseño (2), Talle (1)», y si
    ninguna fila está completa se frena con 422 explicando qué columnas hacen falta y dónde se
    configuran.
  CONTRATO **`verificar_columnas_obligatorias.py`** (reemplaza al `verificar_fila_sin_talle.py` de
  la 364): sin configurar → vale el talle; con talle+diseño → sólo la fila completa, y se reporta
  qué faltó en cada una; una fila con sólo lo obligatorio se fabrica igual (nombre y número son
  opcionales). VERIFICADO EN LA PANTALLA REAL: el interruptor aparece en el panel de la columna y
  al encenderlo avisa qué filas se van a ignorar.
- **2026-08-31 (364) — 🔴🔴 UNA FILA SIN TALLE SE FABRICABA COMO TALLE «M».** Reporte del usuario:
  «en la planilla cargué 1 solo talle pero hay 4 filas más con el dato de la manga y el diseño, y
  me las creó del mismo talle; si no tiene el talle, ignorar». CAUSA, en `_traducir_prendas`:
  `"talle": pr.get(talle_col, "") or … or "M"` — la fila sin talle **no se descartaba, se
  rellenaba con «M»**. Las filas a medio llenar (con la manga y el diseño, que el sistema completa
  solo) salían fabricadas. 🔴 Es de la peor familia de errores del sistema: NO FALLA, sale bien
  impreso y de más (misma familia que [[traba-antes-de-fabricar]]). AHORA: la fila sin talle se
  IGNORA, y **se dice cuántas** (`avisos_pedido`: «N fila(s) sin talle — no se fabricaron»); si
  NINGUNA fila tiene talle, se frena con 422 y se explica. Callarlo sería casi tan malo: la
  persona cuenta las prendas de la tizada, no le cierran con la planilla y no sabe por qué.
  CONTRATO NUEVO **`verificar_fila_sin_talle.py`** con la planilla del reporte (1 fila con talle +
  4 a medio llenar → 1 prenda), probado en negativo. ⚠️ La primera prueba negativa NO falló: hay
  dos capas (el descarte y el `or "M"` que se sacó) y romper la segunda sola no cambia nada — hay
  que romper el descarte para ver el contrato en rojo.
  **Y el 404 de la consola** (`/api/productos/prod_default/preview`, en el server publicado): es
  el «Molde 1» que crea la instalación, sin archivo todavía. No rompía nada (la tarjeta cae a su
  ícono) pero ensuciaba la consola con rojo. Ahora ese caso devuelve **200 con la miniatura
  vacía** (`sin_molde: true`), igual que ya hacía el mismo endpoint cuando falta nombrar las
  variantes: un paso pendiente no es un error.
- **2026-08-31 (363) — 🔴 «⏺ AGREGAR PASOS» DEL EDITOR NO HACÍA NADA (otra víctima del borrado
  grande).** Reporte del usuario: «el grabar pasos en el editor no funciona». El botón prendía el
  modo y se pintaba en rojo, pero **el efecto que escucha los clics ya no existía**: se lo llevó
  por delante la limpieza de la lógica de 2 diseños (349), que cortó bloques del editor por sus
  comentarios de inicio y fin — la misma trampa que dejó sin declarar `carga`, `modalAb` y
  `ventanita` (351). Restaurado, y ahora identifica el paso con el MISMO localizador que el
  grabador (así una lista de opciones queda como lista) y guarda la ventana emergente donde cayó
  el clic. 🔴 DE PASO SE UNIFICÓ EL CRITERIO de qué NO se graba: **`sePuedeGrabar(el)`** en
  localizar.js (barra lateral, `data-no-grabar`, el propio editor) lo usan el grabador Y el editor
  — antes cada uno tenía el suyo y el editor anotaba pasos que el grabador descarta (se vio en la
  prueba: agregó un «tocá Configuración» de la barra). El candado del contrato se movió a
  `sePuedeGrabar` y ahora exige además que los DOS lo usen. VERIFICADO EN EL EDITOR REAL: con el
  modo prendido, tocar la barra lateral NO suma (22 → 22) y tocar un control del trabajo sí (22 →
  23, chip «Moldería»).
  ⚠️ El candado `verificar_tdz.mjs` volvió a atajar el restaurado: el efecto quedó ARRIBA de
  `dondeRef`/`selRef` y habría sido pantalla negra.
  📌 LECCIÓN (tercera vez): después de un borrado grande hay que **listar lo que quedó dentro del
  tramo** y probar cada función del editor a mano — los contratos no ejecutan React y estas cosas
  sólo se ven usando la pantalla.
- **2026-08-31 (362) — 🔴 EL GRABADOR SE COMÍA EL SEGUNDO CLIC DE UNA LISTA (bug MÍO, de la
  361).** Reporte del usuario tras subir la actualización: «grabé un tutorial y no me detectó los
  2 botones que presioné en diseño». CAUSA: el grabador descarta clics repetidos seguidos
  —`if (prev.ancla === ancla && prev.accion === accion) return;`, para no anotar dobles clics ni
  tipeo letra a letra—, y al marcar las listas con `data-opciones` **todos sus botones pasaron a
  dar el MISMO identificador** (es la lista, no el botón). Resultado: el segundo diseño se
  descartaba como «repetido» y el tutorial salía pidiendo uno solo. FIX: dentro de una lista de
  opciones, lo que se compara es **el BOTÓN tocado** (`ultCtrlGrab`), no el identificador: dos
  botones distintos son dos pasos; tocar dos veces el MISMO sigue siendo uno. Fuera de esas listas
  todo queda igual. VERIFICADO GRABANDO DE VERDAD (sandbox): tres diseños distintos → «1 paso, 2
  pasos, 3 pasos», y volver a tocar el mismo → sigue en 3.
  ⚠️ LO YA GRABADO NO SE PUEDE ARREGLAR SOLO: un tutorial grabado con el código de la 361 guardó
  UN solo clic donde hubo dos, y esa información no está en ninguna parte. Hay que regrabar ese
  tramo.
  📌 LECCIÓN: cambiar CÓMO se identifica un control toca también al GRABADOR, no sólo a la
  reproducción. La regla de «no repetir» daba por sentado que dos clics con el mismo identificador
  eran el mismo control — dejó de ser cierto el día que un identificador pasó a representar a toda
  una lista.
- **2026-08-31 (361) — LAS LISTAS DE OPCIONES SE MARCAN EN LA PANTALLA (`data-opciones`).**
  Pedido del usuario: «en el paso de elegir molde también es multiopción, hay más de un botón o
  tarjeta para elegir: no debe ir a uno directo». La regla de la 359 vivía sólo en `aGuion`, así
  que el GRABADOR seguía afinando dentro de esas listas y el paso quedaba atado a la tarjeta que
  se tocó («txt:camiseta de futbol · 7 pzas#pedido-variables»). AHORA la lista se marca en el JSX
  con **`data-opciones`** y el localizador NO afina ahí: el paso es la lista, aunque se haya
  grabado un solo clic («Tocá la prenda que lleva ese diseño», no «Tocá "Cuello redondo"»). Marcadas:
  los diseños del pedido, los chips de diseño (pedido y arte), las prendas y —nueva, no tenía
  marca— **la lista de prendas del paso Arte** (`arte-variables`, con su explicación).
  Y los tutoriales YA grabados se des-afinan al reproducirlos.
  **DOS COSAS MÁS que mostró el tutorial «2 colores» del usuario (36 pasos grabados):**
  (a) **pasos repetidos** — escribir en dos filas de la misma columna daba `col:nombre` ×2 y el
  tutorial repetía el cartel: dos clics seguidos EN EL MISMO LUGAR ya no son dos pasos (36 → 32).
  ⚠️ Ese descarte va DESPUÉS de contar las opciones (si no, se comía la cuenta del «elegí 2») y
  exige ancla de verdad (dos «esperar aviso» seguidos NO son un duplicado: son dos ventanas
  distintas) — las dos cosas las agarró el contrato.
  (b) **un cartel mostraba el ancla cruda** («Tocá «txt:camiseta de futbol · 7 pzas#pedido-…»»)
  cuando el paso venía afinado y sin etiqueta: `explicar()` ya no cae nunca al identificador, sólo
  a su parte legible.
  CONTRATOS: §10a suma «un solo clic en una lista tampoco ata el tutorial a esa tarjeta», «dos
  clics seguidos en la misma columna son UN paso» y «dos ventanas distintas seguidas siguen siendo
  dos pasos». VERIFICADO con los dos tutoriales reales del usuario.
  ⚠️ LO QUE NO SE PUDO ARREGLAR SOLO: en «2 colores» hay pasos `txt:cuello redondo` sin sección
  (grabados cuando la lista de prendas del Arte todavía no tenía marca). Al reproducir marcan esa
  tarjeta si está; si el molde es otro, no la encuentran y hay que seguir con «Siguiente →».
  Regrabar ese tramo los deja como «elegí la prenda».
- **2026-08-31 (360) — LA AYUDA NO SE GRABA A SÍ MISMA.** Pedido del usuario: «el botón de parar
  y guardar para terminar el tutorial no saldrá en el tutorial: eso es del grabador». El clic en
  «Parar y guardar» quedaba como un paso más (se veía en su tutorial «2 diseños», paso 4), así que
  el tutorial terminaba enseñando a tocar un botón del grabador que quien lo sigue nunca ve. FIX:
  el cartel de grabación lleva **`data-no-grabar`** y el grabador ignora todo lo que esté adentro
  de algo así (igual que ya ignoraba la barra lateral) — sirve para cualquier control del propio
  sistema de ayuda que se agregue después. Y los tutoriales YA grabados se limpian al
  reproducirlos: `aGuion` descarta los pasos de la ayuda (`txt:parar y guardar`, «Grabar un
  tutorial», el botón «Ayuda»…). CONTRATO en `verificar_guion.mjs`, probado con el caso real.
- **2026-08-31 (359) — 🔴 OPCIONES INTERCAMBIABLES: «elegí 2», no «tocá estos 2».** Pedido del
  usuario: «cuando tengo un modal con varias opciones —ejemplo, diseño— yo grabo el tutorial
  presionando 2 botones random, pero quien pide ayuda puede elegir otros 2». Su tutorial «2
  diseños» tenía grabados JUGADOR y GOLERO como dos pasos atados a ESOS botones: quien lo siguiera
  quedaba obligado a elegir los mismos. En una lista de opciones lo que importa es CUÁNTAS, no
  cuáles. FIX: (1) las listas de opciones equivalentes se DECLARAN en el diccionario con
  **`opciones: true`** (`pedido-diseno-lista`, `pedido-diseno-chips`, `pedido-variables`,
  `arte-diseno-chips`) — no se adivina, porque «Descargar sólo la hoja 1» y «Descargar la ficha
  técnica» son dos botones del mismo panel y NO son intercambiables (358); (2) `aGuion` junta los
  clics CONSECUTIVOS sobre la misma lista en UN paso con `cuantas: N`, que marca LA LISTA y dice
  «Elegí 2 de esta lista (las que necesites)»; (3) el motor cuenta los clics de adentro y avanza
  al llegar a N, sean los que sean, con el contador del globo («1 de 2»).
  ⚠️ TRES DETALLES QUE COSTARON: el ancla ya puede venir afinada (`txt:jugador#pedido-diseno-lista`,
  entrada 358), así que hay un helper único **`seccionDe(paso)`** y se compara SECCIÓN contra
  SECCIÓN — comparar el ancla cruda no juntaba nada; el completado de etapas también tiene que
  reconocer los pasos afinados (si no, agregaba de nuevo la etapa del diseño); y las anclas
  grabadas se registran por ancla Y por sección.
  CONTRATO §10a (dos clics en la lista = un paso «elegí 2» que marca la lista; y dos botones de
  acciones distintas NO se juntan). VERIFICADO EN VIVO con su tutorial «2 diseños»: el guion queda
  en 2 pasos («Elegí 2 de esta lista» + «Tocá "Elegir los moldes"»), y al tocar **GOLERO y DISEÑO
  1** —ninguno de los que él grabó— el tutorial pasó de 1/2 a 2/2. Con diseños ya elegidos, el
  paso se saltea solo (no repite lo hecho). ⚠️ NO VERIFICADO EN PANTALLA: el contador «0 de 2» del
  globo (el código está y el avance funciona, pero no llegué a verlo dibujado: el pedido de prueba
  ya tenía diseños y el paso se salteaba).
- **2026-08-31 (358) — 🔴 DOS BOTONES DE LA MISMA VENTANA SON DOS PASOS DISTINTOS.** Reporte del
  usuario: «si en un modal presiono 2 botones, el tutorial tiene que respetar eso y esperar a que
  presione los 2». EL CASO REAL, en su tutorial «Camiseta»: los pasos 21 y 22 eran los DOS
  `resultados-mesas` —«Descargar sólo la hoja 1» y «Descargar la ficha técnica completa»—. CAUSA:
  `identificar` prefería el `data-tour` del ANCESTRO y perdía CUÁL control se tocó; con la marca
  puesta en un PANEL, todos sus botones daban el mismo ancla → dos pasos idénticos, el tutorial
  marcando el panel entero («en vez de marcar el botón que le puse marca todo el modal») y sin
  forma de esperar los dos. FIX: formato de ancla nuevo **`txt:<nombre>#<sección>`** = ese control,
  dentro de esa sección marcada. Reglas: el `data-tour` puesto EN el control manda (lo eligió una
  persona); si está en un CONTENEDOR y el control tiene nombre propio, se guardan los dos; al
  reproducir se busca ese control dentro de esa sección y, si ya no está, **se cae a la sección**
  (mejor marcar la zona que nada). 🔴 Y LOS TUTORIALES YA GRABADOS SE ARREGLAN SOLOS: `aGuion`
  afina el ancla con la `etiqueta` que el grabador guardó en cada paso —sin regrabar— y reescribe
  el cartel para que nombre EL BOTÓN (si no, dos pasos distintos decían «Esperá a que termine de
  armar la tizada»); un cartel escrito a mano en el editor no se pisa (`_aMano`).
  ⚠️ DOS TRAMPAS DEL CAMINO: (a) afinar el ancla ANTES del completado de etapas le saca al paso su
  etapa y desordena todo el guion — lo agarró el contrato §1 y por eso el afinado va AL FINAL;
  (b) el paso del guion no llevaba la `etiqueta` del grabado, así que el afinado no hacía nada:
  ahora viaja como `_etq`. CONTRATO §10b con el caso del usuario (dos «resultados-mesas» dan
  anclas distintas, cada uno recuerda su sección, y un botón ya marcado a mano se queda con su
  marca); el helper `anclas()` de los contratos mide ahora `seccion || ancla`, que es la identidad
  semántica. VERIFICADO EN VIVO con su tutorial: los pasos finales son **«20/23 Tocá "Descargar
  todo (1)" · 21/23 Abrí la "Ficha técnica" · 22/23 Tocá "Descargar sólo la hoja 1" · 23/23 Tocá
  "Descargar la ficha técnica completa"»** — dos paradas distintas, cada una con su nombre.
- **2026-08-31 (357) — 🔴 EL MODAL DEL PASO GANA A LA CARGA + UN MODAL DE UN SOLO BOTÓN SE MARCA
  POR SU BOTÓN.** Segunda vuelta del reporte del usuario, con la misma captura: «esa ventana tiene
  un botón de Entendido pero la ayuda lee un modal que está por detrás… y dentro de ficha técnica,
  en vez de marcar el botón que le puse marca todo el modal; el modal sólo se marca si hay un
  montón de botones entre los que elegir, acá tengo uno solo».
  **(1) LO QUE FALTABA DE LA 355.** El arreglo anterior hacía ganar al modal sólo cuando era
  AJENO al paso. Pero acá el paso ES el «Entendido» de esa ventana: `bloqueoModal` daba null (bien:
  no hay que frenar, hay que hacerlo) y entonces, con una carga atrás, ganaba la CARGA → «Debés
  esperar a que esto termine» con el botón a la vista. `queAtender` recibe ahora
  **`modalDelPasoAbierto`**: si el modal de adelante es donde va el paso, se atiende EL PASO.
  **(2) UN SOLO BOTÓN, SE MARCA EL BOTÓN.** Cuando el tutorial frena por un modal ajeno contaba
  siempre la ventana entera. Ahora mira sus botones de acción (el aspa de cerrar no cuenta): con
  UNO SOLO ilumina ESE botón y el cartel dice «Tocá "Entendido"»; con VARIOS ilumina la ventana y
  explica, que es cuando de verdad hay que leer y elegir. ⚠️ El cálculo va SIN `useMemo`: el
  contenido de un modal cambia sin que cambie el objeto del modal, y un memo se quedaba con la
  cuenta vieja.
  CONTRATO: §11a de `verificar_guion.mjs` sube a 8 casos (incluidos los dos nuevos), probado en
  negativo. VERIFICADO EN VIVO con las dos superficies inyectadas sobre el tutorial corriendo:
  modal de UN botón → cartel «Tocá "Entendido"» e iluminado 112×51 px (**el botón**, no el modal de
  470×210); modal de DOS botones («Tipografía no encontrada») → cartel «Cargá la tipografía que
  falta, o seguí igual…» e iluminado 456×216 (**la ventana**). ⚠️ Nota de la prueba: agregarle un
  botón a un modal por DOM crudo no re-renderiza React, así que ese caso hay que probarlo con el
  modal ya nacido con sus dos botones — como pasa en la app de verdad.
- **2026-08-31 (356) — AUDITORÍA: QUE NADA QUEDE FUERA DEL TUTORIAL.** Pedido del usuario:
  «chequeá que no quede nada del tutorial por fuera: todo lo que se cree, todo mini botón, espacio
  de trabajo, visual, espacio de rellenar — todo lo manipulable tiene que ser grabable y los
  tutoriales entenderlo; del lado del cliente y de configuración, todo». Se midió en la app REAL
  (sandbox, 13 pantallas, **301 controles**: 115 con marca propia, 47 campos de escritura). Tres
  agujeros encontrados y cerrados:
  **(1) LO TOCADO NO SIEMPRE ES EL CONTROL.** El clic cae en el `<svg>`/`<path>` del ícono de un
  botón; ese nodo no tiene nombre y `identificar` devolvía `null` → ese paso NO SE PODÍA GRABAR.
  Ahora se sube al control que lo contiene.
  **(2) HOMÓNIMOS.** 7 botones «Editar», 13 «Eliminar esta fuente del catálogo», 7 «Eliminar»…
  todos daban el MISMO ancla, así que el tutorial marcaba el primero de la lista y no el que se
  tocó. Ahora el ancla lleva el contexto de su fila (`txt:editar@manga`) y al reproducir se busca
  entre los homónimos el de esa fila (si esa fila ya no está, cae al primero: mejor marcar algo
  parecido que nada). ⚠️ El contexto es el texto de la fila **sin el de sus botones**: la primera
  versión devolvía «eliminar» (el botón de al lado) para los 7 «Editar» — lo agarró la prueba en
  la app real, no el contrato.
  **(3) EL ESPACIO DE TRABAJO VISUAL.** El visor de piezas (un `<svg>` con 36 piezas clickeables,
  donde se mapea el diseño y se asignan las telas) no tenía NADA con qué identificarse. Ahora el
  lienzo lleva `data-tour="molde-visor"` (con su explicación) y cada pieza `data-pieza="<nombre>"`;
  el localizador entiende **`pieza:<nombre>`** igual que `col:<id>` → tocar una pieza graba ESA
  pieza («pieza:frente 1», «pieza:sisa izquierda») y el tutorial la ilumina a ella.
  Además: 3 botones de sólo ícono SIN nombre (renombrar moldería, borrar planilla y el `Switch`)
  ahora tienen `title` — sin nombre no se pueden grabar ni volver a encontrar.
  CONTRATOS: §4b en `verificar_localizar.mjs` (tocar el ícono cuenta como el botón; dos «Editar» de
  filas distintas dan anclas distintas y cada uno se reencuentra) y §8b en
  `verificar_diccionario.mjs` (**ningún botón de sólo ícono sin nombre**, hoy 0; probado en
  negativo). El DOM de juguete del contrato tuvo que crecer (selectores con coma, `innerText`,
  `parentElement`, `querySelectorAll` por elemento) para poder ejecutar esta lógica de verdad.
  📌 El candado `verificar_tdz.mjs` se ganó el sueldo en el camino: me atajó un `CONTROLES` usado
  antes de declararse, ANTES de compilar.
- **2026-08-31 (355) — 🔴 CON DOS VENTANAS ENCIMA, MANDA LA DE ADELANTE.** Reporte del usuario:
  «me hace esperar por una ventana emergente que se encuentra detrás de otra ventana emergente;
  reparalo para que marque la de atrás DESPUÉS de que se cierra la de adelante — en este caso se
  cierra al presionar "Entendido", que ya es un paso del tutorial». La captura: el modal «Perfil de
  color del diseño» ENCIMA de la carga «Se está poniendo el diseño sobre el molde», y el globo
  diciendo «Debés esperar a que esto termine» sobre algo tapado. CAUSA: la carga ganaba dos veces
  — `bloqueoModal` se anulaba con `if (!modalAb || carga) return null;` y en la cadena de `paso` la
  carga iba primera. FIX: la decisión pasa a una función pura **`queAtender({modalTapando,
  hayCarga, cargaEsDelPaso})`** en guion.js — *lo de adelante primero* — y la usan tanto el cartel
  como lo que se ilumina (antes eran dos cadenas separadas que podían discrepar). Al cerrarse el
  modal, si la carga sigue, el tutorial vuelve solo a la espera. CONTRATO §11a en
  `verificar_guion.mjs` (los 5 casos de la tabla), probado en negativo. VERIFICADO EN VIVO
  (sandbox, con el tutorial corriendo y las dos superficies inyectadas en el orden real): sólo la
  carga → «ESPERÁ UN MOMENTO»; con el modal encima → **«PRIMERO ESTE AVISO — Leé el aviso y tocá
  "Entendido" para seguir»** (la explicación real del modal, del diccionario); al cerrar el modal
  → vuelve a la espera de la carga; al terminar la carga → sigue el paso normal.
- **2026-08-31 (354) — EN LA PLANILLA EL PASO SE TERMINA A MANO.** Reporte del usuario, efecto
  colateral de la 353: «no me deja escribir ni elegir sobre un desplegable porque salta a la otra
  columna; sólo en la planilla el salto entre columna debe de ser manual». Con el clic cumpliendo
  el paso y cada COLUMNA siendo un paso (345), el primer toque en una celda saltaba a la columna
  siguiente antes de dejar cargar nada. La planilla no se toca: **se carga**, y un paso de columna
  abarca todas las filas. FIX: `aGuion` marca `manual: true` los pasos cuyo ancla es `col:<id>` o
  `planilla-tabla` (helper `esDeLaPlanilla`); el motor no los avanza por clic (sí por su regla
  `listo`, si la tienen, o con «Siguiente →») y el globo lo dice: «Cargá lo que necesites en esta
  columna y, cuando termines, tocá "Siguiente →"». Los botones de la planilla («Enviar el pedido»,
  «Agregar fila») NO son manuales: ésos sí avanzan al tocarlos. CONTRATO §11b en
  `verificar_guion.mjs` (columna y tabla manuales; el botón de enviar y un paso de otra pantalla,
  no), probado en negativo.
  🔴 DE PASO, OTRO CARTEL CON NOMBRE VIEJO, en un lugar que el candado de la 353 no miraba: los
  puentes de NAVEGACIÓN viven en las RUTAS de `tutor.jsx`, no en el diccionario, y uno decía
  «Volvé a la planilla con "← Atrás"» cuando el botón dice **«← Planilla»**. Corregido, y el
  candado ahora **revisa las dos fuentes** (84 nombres citados en total); probado en negativo.
  ⚠️ NO SE PUDO PROBAR EN LA PLANILLA REAL: llegar a ella exige cargar un arte, que es escritura, y
  el sandbox es de sólo lectura. Queda cubierto por los contratos (el guion marca `manual`, el
  motor tiene la guarda antes de enganchar el clic) pero **falta un ojo humano cargando una
  columna con el tutorial corriendo**.
- **2026-08-31 (353) — 🔴 EL PASO CON REGLA `listo` NO AVANZABA AL TOCARLO + LOS CARTELES
  NOMBRABAN BOTONES QUE YA NO EXISTEN.** Reporte del usuario sobre «Asignar telas»: «presionás el
  botón, abre una nueva barra donde están las telas, pero la ayuda no detecta eso y queda ahí
  siempre… todo lo que sea similar también, que muestre todo como es». DOS problemas distintos en
  la misma pantalla:
  **(1) EL CLIC NO CONTABA.** El avance por acción arrancaba con
  `if (fin || carga || bloqueoModal || esperaEstado) return;` — o sea que **con una regla `listo`
  del diccionario «mandaba el estado» y el clic ni se escuchaba**. La regla de `arte-telas` es *no
  falta ninguna tela*, algo que recién se cumple varias pantallas después: el tutorial quedaba
  pegado al botón mientras el panel de telas se abría atrás, sin explicar nada de lo que hay que
  hacer adentro. AHORA **tocar el control marcado cumple el paso, tenga o no regla**; el estado
  sigue sirviendo para SALTEAR lo ya hecho y para avanzar sin clic cuando se cumple por otro lado
  (se carga un archivo, se completa un campo). Lo que ya no hace es clavar un paso que la persona
  efectivamente hizo. (Complementa la 352: allá el clic no se detectaba por el tipo de ancla, acá
  ni se escuchaba por tener condición.)
  **(2) EL CARTEL NOMBRABA UN BOTÓN INEXISTENTE:** decía «Tocá "Ver telas de pieza"» y el botón
  dice **«Asignar telas»**. Se barrieron las 134 entradas comparando cada nombre citado entre
  comillas contra App.jsx: 5 estaban viejos — `arte-telas` («Ver telas de pieza» → «Asignar
  telas»), `planilla-cantidad` («Mostrar columna de cantidad» → «Columna cantidad»),
  `agrupar-activar` («Agrupar piezas» → «Nombrar piezas»), `pieza-agregar` («Agregar pieza» →
  «Agregar una pieza») y `resultados-volver-planilla` («← Atrás» → «← Planilla»).
  CONTRATOS: §9a nueva en `verificar_diccionario.mjs` — **todo nombre entre comillas de un cartel
  tiene que existir tal cual en App.jsx** (64 citados; los EJEMPLOS de datos como «con capucha» o
  «capucha = sí» van exentos por lista con su motivo, para que el candado no se vuelva ruido); y
  en `verificar_localizar.mjs`, que el avance por clic no vuelva a apagarse con `esperaEstado`.
  Los dos probados en negativo. VERIFICADO EN VIVO (sandbox 8060, tutorial real del usuario): el
  paso 10/24 muestra «Tocá "Asignar telas"», se toca el botón y **pasa a 11/24 explicando lo que
  se abrió** («Asigná la tela a las piezas: 1) elegí la tela de la lista…»).
- **2026-08-31 (352) — 🔴🔴 EL PASO NO AVANZABA AL TOCAR EL CONTROL MARCADO (bug viejo, de todos
  los pasos sin `data-tour`).** Reporte del usuario con la tarjeta «Cuello redondo»: «presionás y
  no salta al siguiente paso». CAUSA: el detector del clic era

      const dentro = (t) => anclas.some(a => t.closest(`[data-tour="${a}"]`));

  o sea **sólo entendía anclas con `data-tour`**. Pero la MAYORÍA de los controles no la tienen y
  se identifican por su texto (`txt:camiseta asque · 6 pzas`) —lo dice el propio comentario de
  `useAncla`—, así que para todos ésos el selector no matcheaba nada y el clic NO CONTABA NUNCA.
  Lo mismo con las columnas de la planilla (`col:<id>`, entrada 345). No se veía siempre porque
  muchos pasos avanzan por otro camino (cambian de pantalla, o su regla `listo` se cumple sola):
  quedaba clavado justo en los que se resuelven tocando y nada más — elegir la prenda de un molde,
  por ejemplo. FIX: **`esDelAncla(el, ancla)`** en `localizar.js`, el único lugar donde se decide
  si lo tocado es el control del paso, con las tres formas de ancla: `data-tour` (closest),
  `txt:` (el control tocado —o el que lo contiene— se llama así, o lo tocado está DENTRO del que
  resuelve `buscar`: un clic en el dibujito de la tarjeta cuenta como clic en la tarjeta) y `col:`
  (celda, encabezado o desplegable de esa columna). Mismo camino que `rectDeAncla`: un solo
  resolutor, para que ILUMINAR y DETECTAR no puedan discrepar. De paso, `valorDe()` (los pasos de
  «escribir») también usaba `querySelector('[data-tour=…]')` y dejaba afuera los campos sin marca:
  ahora usa `buscar`. CONTRATO `verificar_localizar.mjs` §4 con el caso exacto del reporte (botón
  con `title`, clic en un hijo, otro botón que no cuenta, celda de columna y celda de otra
  columna); probado en negativo. VERIFICADO sobre la tarjeta REAL en el sandbox: su ancla es
  `txt:camiseta asque · 6 pzas`, hay UN solo candidato en pantalla y es ella, y el clic en su hijo
  («Cuello redondo») cae adentro → cuenta.
- **2026-08-28 (351) — 🔴🔴 «modalAb is not defined»: BORRÉ DECLARACIONES AL SACAR LA LÓGICA DE 2
  DISEÑOS.** Reporte del usuario con la consola. Al cortar bloques enteros de `tutor.jsx` (entrada
  349) me llevé por delante **cuatro cosas que estaban en el medio y no eran del ciclo**:
  `const carga = useCargando(!fin)` y `const modalAb = useModalAbierto(!fin)` (quedaron dentro del
  tramo del desvío que borré) y el helper **`ventanita()`** que dibuja las ventanas emergentes
  (quedó dentro del tramo de la vista real). Compiló igual —Vite no valida símbolos— y reventó al
  abrir la ayuda: `ReferenceError: X is not defined`, que en React es la pantalla NEGRA. Las tres
  se restauraron. 🔴 EL CANDADO AHORA MIRA ESO: `verificar_tdz.mjs` suma la regla **`no-undef`**
  (con las globales de navegador y Node, en `eslint.tdz.config.mjs`) a la que ya tenía —«usado
  antes de declarar»—: las dos revientan React entero y ninguna la ve un contrato que no ejecuta
  el componente. Probado en negativo borrando `modalAb` a propósito: reporta las 3 líneas que lo
  usan y corta el build. DE PASO, el candado nuevo destapó **un cuarto problema que NO era de esta
  tanda**: el efecto que mide cuánto dura un cartel usaba `pregunta` y `llevan`, que son PROPS del
  Globo y no existen en el Tour — sólo se alcanzaba en pasos de tipo «ver»/«gesto», por eso nunca
  había explotado; ahora usa `preguntando` y `cuantas[idx]`, que son los reales. VERIFICADO EN
  VIVO (sandbox 8060): el tutorial arranca y muestra su cartel, el editor abre con sus 23 chips y
  24 huecos —sin marcas ni vista real—, el catálogo dibuja las 16 ventanas, el botón «Ayuda» del
  Panel de Producción abre el menú, y la consola no tiene un solo error.
  📌 LECCIÓN: **cortar por marcadores de texto («desde este comentario hasta aquel») se lleva lo
  que haya en el medio.** Cuando el borrado es grande, listar los símbolos que quedan dentro del
  tramo ANTES de cortar — o, más barato, correr el candado después de cada corte y no sólo al
  final.
- **2026-08-28 (350) — LA AYUDA ES PARA TODOS; GRABARLA, SÓLO EL ADMIN.** Pedido del usuario:
  «para los usuarios que no son admin y no tienen acceso a la barra, cambiá el botón de ayuda a
  otro lugar donde puedan acceder todos; pero los tutoriales los puede crear un admin nomás». El
  botón de Ayuda vivía SÓLO en la barra lateral, que existe únicamente en modo diseñador
  (`modoDisenador`, ruta `/admin`): el operario —el que más necesita el tutorial— no llegaba
  nunca. AHORA: (1) botón «Ayuda» en la barra superior del **Panel de Producción**, con el MISMO
  `data-tour="nav-ayuda"` (nunca están los dos a la vez, así que el localizador no se confunde y
  no hace falta otra entrada del diccionario). (2) Permiso nuevo **`ayuda.grabar`** (módulo
  config, `auth.py`): sin él, el menú de ayuda esconde «Grabar un tutorial», «Editar» y «Borrar»
  —y el cartel de «todavía no hay ninguno» dice que los graba el administrador—, pero **la
  seguridad NO es esconder el botón**: `_guard_grabar_tutorial()` en servidor.py rechaza el POST y
  el borrado (401 sin sesión, 403 sin permiso); VER y seguir tutoriales no pide nada. (3) 🔴 DOS
  ARREGLOS DE FONDO que hacían falta para que esto funcionara en una instalación YA HECHA:
  `bootstrap()` sólo corre al INSTALAR, así que un permiso agregado después no existía en la base
  y la función quedaba inaccesible para todos —ahora el server **sincroniza permisos y roles al
  arrancar** (idempotente, no borra ni pisa los roles del usuario)—; y `sincronizar_roles` no
  tocaba los roles ya creados, así que el rol **admin** (de sistema) nunca recibía los permisos
  nuevos: ahora se pone al día con todos (su pantalla no deja editarlo, así que no pisa nada
  elegido a mano). CONTRATO en `verificar_tutorial_ventana.py`: sin sesión→401, con
  `pedido.crear`→403, con `ayuda.grabar`→200, borrar sin permiso→403, y GET sin permiso→200.
  VERIFICADO en la base real (sólo lectura): `ayuda.grabar` sembrado (id 18) y asignado al rol
  admin.
- **2026-08-28 (349) — 🔴🔴 SE ELIMINÓ TODA LA LÓGICA AUTOMÁTICA DE «2 DISEÑOS».** Decisión del
  usuario: «lo que hacemos de 2 diseños eliminalo por completo; si se quiere para 2 diseños se
  debe de grabar para 2 diseños y listo». Se probó durante un día entero y el resultado era
  impredecible para quien seguía el tutorial. SE FUE: en `guion.js` —`vistaReal`,
  `bloquesPorDiseno`, `etapaIncompleta`, `conAntes`, `TRANSICIONES`, el bucle `{desde, etapa}`, las
  marcas `vuelta`/`vuelta2`/`mid`/`repite` y la condición `solo`— (314 → 163 líneas); en
  `diccionario.js` los tres desvíos `antes` y la pregunta «¿cuántos diseños vas a cargar?»; en
  `App.jsx` los campos `activoConVariable`/`activoArteCargado`/`activoTelasListas` que sólo
  alimentaban eso; en `tutor.jsx` el bucle al avanzar, los desvíos, el replay de las marcas, el
  salteo de pasos no pintados, y en el EDITOR las marcas «↻», el pintado, el modo «elegir pasos»,
  la vista real de 2 diseños y el selector «Sólo con 2+ diseños»; en `servidor.py` los campos
  `vuelta2`/`mid`/`repite`/`solo` del sanitizador y la excepción que dejaba guardar pasos sin
  ancla. QUEDA (y es lo que hace falta): las palabras del diccionario, el completado de etapas
  que la grabación no tiene, `pasoSuperado` (arrancar desde donde está la persona), las ventanas
  emergentes, el texto a mano y la pregunta «¿cuántas prendas?» de la planilla —que NO es del
  ciclo—. COMPATIBILIDAD: un tutorial viejo con marcas sigue sirviendo — `aGuion` las descarta y
  lo reproduce plano; el editor las saca al abrirlo y al guardar quedan limpias. CONTRATOS:
  `verificar_guion.mjs` perdió las secciones 7 (ciclo), 9 (bucle) y 12 (vista real) y ganó una
  §12 nueva que **prohíbe que la lógica vuelva** (ninguna de las 8 palabras clave puede reaparecer
  en `guion.js`, y un tutorial viejo con marcas tiene que reproducirse plano); el del diccionario
  perdió la validación de `antes` y el fixture MITAD; el del servidor exige que esos campos ya no
  se guarden. Todo probado en negativo. 📌 LECCIÓN: la inteligencia automática que ADIVINA lo que
  el usuario quiere repetir es peor que no tener nada — lo que se graba es lo que se muestra.
- **2026-08-28 (348) — 🔴🔴 PANTALLA NEGRA AL CARGAR EL ARTE CON LA AYUDA ABIERTA (bug MÍO,
  introducido hoy).** Reporte del usuario con la consola: `Uncaught ReferenceError: Cannot access
  'ge' before initialization`. CAUSA: en `tutor.jsx`, `const paso = (carga && !modalDelPaso) ? …`
  leía **`modalDelPaso`, que se declaraba 19 líneas más abajo**. Leer una `const` antes de su
  declaración no da `undefined`: tira ReferenceError (zona muerta temporal), y en React eso no es
  un aviso — se cae el árbol entero y la pantalla queda NEGRA. **POR QUÉ NO SALTÓ EN NINGUNA
  PRUEBA:** el `&&` corta. Sin ventana de carga a la vista, `modalDelPaso` no se evaluaba nunca;
  reventaba SÓLO con una carga en pantalla, o sea justo al cargar el arte — el momento exacto que
  esta misma tanda había agregado (el tutorial frena y explica la espera). Lo introduje al mover
  esa expresión y no lo vi porque probé el editor y el catálogo, nunca el flujo con una carga
  activa. FIX: `avisoAb` y `modalDelPaso` se declaran ANTES de `paso` (dependen sólo de `carga`,
  `modalAb` y `pasoGuion`, ya declarados arriba). Se ordenaron además `alternarPintado` y
  `ventanita` (tutor.jsx) y `TRANSICIONES` (guion.js), que hoy no rompían —se leen recién al tocar
  o al dibujar— pero son la misma bomba a un movimiento de distancia.
  CONTRATO NUEVO **`frontend/verificar_tdz.mjs`** (en el build): corre ESLint
  (`no-use-before-define`) sobre `tutor.jsx`, `guion.js`, `localizar.js` y `diccionario.js` y CORTA
  si algo se lee antes de declararse. Probado en negativo con el archivo real de esta mañana:
  reporta `tutor.jsx:536 — 'modalDelPaso' was used before it was defined` — o sea, el linter
  habría atajado la pantalla negra antes de que la viera el usuario. ⚠️ Usa
  `eslint.tdz.config.mjs` propio porque **`npm run lint` del proyecto HOY NO ARRANCA**
  (`reactHooks.configs.flat.recommended` es `undefined` con la versión instalada del plugin) —
  pendiente arreglarlo aparte; `App.jsx` queda fuera del candado por ahora (arrastra usos previos
  que taparían lo nuevo). VERIFICADO EN VIVO (sandbox 8060): con el tutorial corriendo se inyectó
  una ventana `data-cargando` real; la pantalla sigue viva y el tutorial muestra «Debés esperar a
  que esto termine» — sin ReferenceError en consola.
  📌 LECCIÓN: un cambio en el tutorial no está probado hasta correrlo **con una ventana de carga a
  la vista**; los contratos no ejecutan React y no ven este tipo de error, el linter sí.
- **2026-08-28 (347) — 🔴 UN SOLO RESOLUTOR DEL RECUADRO (el editor marcaba sólo el TÍTULO).**
  Reporte del usuario: «cuando te digo marcar toda la columna es el título y todas las casillas de
  todas las filas de esa columna». El Tour ya iluminaba la columna entera (346), pero el EDITOR
  tiene su propio resaltado y medía `buscar(ancla).getBoundingClientRect()` a secas → como
  `buscar('col:x')` devuelve el ENCABEZADO, marcaba sólo el título. Dos lugares dibujando lo mismo
  con reglas distintas: la misma clase de bug que ya se pagó en el motor con `_encaje()` (ver
  [[referencia-medida-alto-ancho]]). FIX: **`rectDeAncla(ancla, el)`** en `localizar.js` es el
  ÚNICO que decide el recuadro de un paso — columna entera (título + todas las casillas + su
  desplegable) para `col:`, el elemento para todo lo demás — y lo usan el Tour (`useAncla`) y el
  editor. CONTRATO (`verificar_localizar.mjs` §3): un paso de columna NO puede medir lo mismo que
  su encabezado solo, un paso normal sigue siendo su control, y **`tutor.jsx` tiene que llamar a
  `rectDeAncla` al menos dos veces** (si uno vuelve a medir por su cuenta, falla) — probado en
  negativo.
  ⚠️ **TRAMPA DE MEDICIÓN QUE COSTÓ UNA HORA (anotar y no repetir):** al verificar en el navegador
  embebido, `getBoundingClientRect()` de un elemento del PORTAL daba `x:223 w:868` (la tabla)
  mientras el elemento tenía `style.left:542.75px; width:162px` (la columna). El pane aplica un
  zoom propio, así que las coordenadas medidas NO son las que dibuja la página: parecía que el
  recuadro estaba congelado en la tabla y estuve buscando un bug que no existía (revisé closures,
  deps del efecto, doble montaje del portal, caché del bundle). Lo que destrabó el diagnóstico fue
  un `console.log` temporal dentro del efecto —mostró `col:nombre {x:547.75, w:152, h:202}`, o sea
  el cálculo SIEMPRE estuvo bien— y después comparar `style` crudo contra el rect medido.
  **Para verificar posiciones en ese navegador: leer `el.style` (lo que la app dibuja), no
  `getBoundingClientRect` (lo que el pane muestra).**
- **2026-08-28 (346) — LA COLUMNA SE ILUMINA CON SU DESPLEGABLE.** Reporte del usuario: «debe de
  seleccionar toda la columna y el desplegable también». La lista de opciones de una celda (Talle,
  Diseño…) NO vive dentro de la tabla: `ComboCell` la monta con `createPortal` en el body,
  `position: fixed`, z-index 3000. Como el recuadro de la columna se arma con los `[data-col]`, la
  lista quedaba afuera — y afuera del hueco está el velo del tutorial (z-index 100000), así que la
  lista se veía OSCURECIDA justo cuando hay que elegir en ella. (Tocarla siempre se pudo: el
  recorte es `pointerEvents:none` — el problema era de vista, no de clic.) FIX: `ComboCell` recibe
  `colId` y su portal se marca con **`data-col-lista`**; `rectDeColumna` suma
  `[data-col-lista="<id>"]` a `[data-col="<id>"]`. Como el recuadro se re-mide solo cada 250 ms, el
  hueco CRECE al abrirse la lista y se achica al cerrarla. CONTRATO (`verificar_localizar.mjs`):
  con la lista abierta el alto pasa de 50 a 130 sin mover el techo, la lista de una columna no
  agranda a las otras, y al cerrarse vuelve — probado en negativo; + candado en
  `verificar_diccionario.mjs` de que el portal siga marcando su columna (probado en negativo).
  ⚠️ LO QUE NO SE PUDO VERIFICAR EN VIVO Y POR QUÉ: abrir ese desplegable con eventos fabricados
  desde la consola NO funciona (React ignora los clics sintéticos para este flujo: probé
  click/dblclick, PointerEvent + MouseEvent completos y Enter; la celda nunca entró en edición), y
  el navegador de la sesión no compone frames (no hay screenshot ni clics reales). Se verificó lo
  que sí se puede: el `data-col` de encabezado y celdas en la planilla REAL (columna Nombre = 6
  celdas, 152 px dentro de una tabla de 858), el mecanismo completo en el contrato, y que
  `data-col-lista` llega al bundle compilado. Falta un ojo humano abriendo la lista con el tutorial
  corriendo.
- **2026-08-28 (345) — 🔴 UN PASO DE LA PLANILLA MARCA SU COLUMNA, NO LA TABLA ENTERA.** Reporte
  del usuario: «ese paso marcado en realidad debe de marcar la columna que estamos trabajando, no
  la planilla completa». CAUSA: `identificar()` sube al `[data-tour]` más cercano y la ÚNICA marca
  de la planilla está en la `<table data-tour="planilla-tabla">` → tocar Talle, Nombre o Número
  grababa **el mismo paso** (por eso el tutorial del usuario tiene cinco «Planilla del pedido»
  seguidos, indistinguibles) y al reproducir se iluminaba la tabla completa. FIX en cuatro puntas:
  (1) **App.jsx**: el `<th>` y el `<td>` de la planilla llevan `data-col={c.id}` +
  `data-col-label` + `data-col-role`. (2) **localizar.js**: `identificar` devuelve `col:<id>`
  cuando el `data-col` está MÁS ADENTRO que el `data-tour` (si una celda tuviera un control
  marcado, ese control gana); `buscar('col:x')` devuelve el encabezado (para el scroll) y la nueva
  **`rectDeColumna(id)`** une encabezado + celdas; + `etiquetaColumna(id)`. (3) **tutor.jsx**:
  `useAncla` ilumina con `rectDeColumna` cuando el ancla es `col:`. (4) **diccionario.js**: qué es
  cada columna (`col:talle|nombre|numero|cantidad|diseno|manga`); una columna propia del molde
  («Talle short», una sisa) cae al fallback con su LABEL. Además, **los pasos YA grabados no hay
  que regrabarlos**: en el detalle del paso hay un selector de columna que reescribe su ancla
  (`planilla-tabla` ↔ `col:<id>`), con las columnas leídas de la planilla en pantalla (son
  configurables por molde) o las conocidas (`COLUMNAS_CONOCIDAS`). CONTRATO NUEVO
  **`frontend/verificar_localizar.mjs`** (en el build): arma una planilla de juguete en memoria —
  no hay navegador — y exige que tres columnas den TRES pasos distintos, que un control marcado
  adentro de una celda le gane a la columna, y que el recuadro abarque del encabezado a la última
  celda con el ancho de ESA columna; probado en negativo (4 fallas). Candado extra en
  `verificar_diccionario.mjs`: las claves `col:` no son texto muerto pero su columna debe existir
  en App.jsx (agarró dos inventadas: `variable` y `tela` NO son columnas — la variable se elige por
  fila y la tela por pieza), y el `data-col` tiene que estar en el `<th>` **y** en el `<td>` (con
  uno solo el candado no detectaba nada: probado). VERIFICADO en la planilla real (sandbox 8060):
  la columna Nombre son 6 celdas y su recuadro mide 152 px dentro de una tabla de 858; el selector
  del editor trajo las columnas reales del molde (Talle, Talle short, Nombre, Número, Manga,
  Diseño) y cambiarlo convirtió el paso 18 de «Planilla del pedido» a «Columna Nombre».
  ⚠️ Trampa: `rectDeColumna` quedó sin cerrar la llave y lo agarró el contrato del guion (que
  importa `localizar.js`) ANTES de compilar — por eso los contratos van antes del build.
- **2026-08-28 (344) — LAS VENTANAS DEL CATÁLOGO SE DIBUJAN (no se nombran).** Pedido del
  usuario: «¿se puede hacer visual las ventanas emergentes a elegir? así sé cuáles son, porque no
  sé por nombre». RAÍZ: de las 16 ventanas de `AVISOS_CONOCIDOS`, **sólo 1 tenía ficha** en el
  diccionario — las otras 15 eran un título suelto, y por eso también el tutorial las explicaba
  con el texto genérico de `explicarModal` («Apareció X, leelo y respondé lo que pide») cuando se
  abrían solas. FIX en dos partes: (1) **las 16 fichas completas** en `diccionario.js`
  (`que`/`como` + el campo nuevo **`ventana: {contenido, botones, cuando, paso, trabajo}`**),
  relevadas del JSX real de App.jsx — los BOTONES son los textos exactos de cada modal; nueva
  `fichaVentana(titulo)` exportada. (2) el catálogo del editor (tutor.jsx `ventanita(titulo,
  activa, grande)`) dibuja **la ventana**: barra de título, lo que se ve adentro, dos renglones
  grises de cuerpo y **sus botones reales** (o la barra de progreso si es de trabajo), y debajo
  «Aparece al cargar un diseño» con el punto del color de su etapa (`COLOR_ETAPA[f.paso]`). En la
  línea de tiempo el chip sigue compacto (40 px). BENEFICIO EXTRA: como el cartel del tutorial sale
  del mismo diccionario, ahora esas 15 ventanas se explican de verdad al abrirse (verificado:
  «Tipografía no encontrada» → «Cargá la tipografía que falta, o seguí igual…»). CONTRATO §10 en
  `verificar_diccionario.mjs`: toda ventana de `AVISOS_CONOCIDOS` necesita `que`+`como`+
  `ventana.contenido`+`ventana.cuando`, un `paso` de la lista válida, y `trabajo` coherente con
  ser carga o no (16/16); probado en negativo. VERIFICADO en la UI real (sandbox 8060): las 16
  tarjetas con su contenido, botones y «Aparece …», y al elegir una queda en la posición exacta
  del «+» (la ventana «Tipografía no encontrada» quedó de paso 6).
- **2026-08-28 (343) — 🔴 LOS DESPLEGABLES SE ABRÍAN EN BLANCO (todos, desde siempre).** Reporte
  del usuario con la captura de una lista vacía con una sola línea azul: «repará todos los
  desplegables que al abrir se vean así». CAUSA: la lista que se abre al tocar un `<select>` la
  dibuja el **sistema operativo**, no la app. La página nunca declaró `color-scheme`, así que
  Windows la pintaba con el tema CLARO (fondo blanco) mientras las `option` heredaban el
  `color: var(--text-primary)` (casi blanco) de la regla `input, select` → **texto blanco sobre
  blanco**: la lista parecía vacía y sólo se leía la opción bajo el mouse (la resaltada azul del
  sistema). No era del editor de tutoriales: afectaba a los **14 desplegables** del sistema
  (unidades, fuente faltante, grupo de empaque, regla de columna, comportamiento, rotación…) desde
  siempre. FIX en `index.css`, global y de una sola vez: `:root { color-scheme: dark }` (el popup,
  los scrollbars y **todo** control nativo se dibujan oscuros — de paso arregla el calendario y el
  reloj de los `input type=date/time` y el `type=color`, que tenían el mismo problema) + `select
  option`/`select optgroup` con `background-color: var(--bg-dark)` y color propio, por si un
  navegador ignora lo primero. CONTRATO NUEVO **`frontend/verificar_estilo_ui.mjs`**, sumado a
  `npm run build` (y a `build:publicado` y `npm run diccionario`): vigila las reglas de CSS que al
  caerse rompen la pantalla EN SILENCIO — nada explota, algo se vuelve ilegible y nadie se entera
  hasta que llega una captura. Ignora lo comentado (una regla comentada NO cuenta como puesta) y
  se probó en negativo. VERIFICADO en el navegador (sandbox 8060): `color-scheme` computado
  `dark`, y las `option` del select del reporte (14 opciones) con fondo `rgb(12,12,14)` y texto
  `rgb(250,250,250)`.
- **2026-08-28 (342) — LAS VENTANAS SE PONEN EN LA LÍNEA DE TIEMPO (un «+» entre paso y paso).**
  Pedido del usuario con la captura de «Poniendo el diseño sobre el molde…»: «ese tipo de ventana
  debe de poder también poner en la línea de tiempo de paso para indicar que ahí aparecerá esa
  ventana y antes de seguir mostrará esa ventana». El paso «esperar aviso» YA existía (entrada
  334) pero estaba escondido: había que seleccionar un paso, tocar «+ ventana» y recién ahí
  elegirla de un desplegable. Ahora: (a) entre cada par de pasos —y en los dos extremos— hay un
  **«+»** que abre el CATÁLOGO de las 16 ventanas que el sistema conoce (`AVISOS_CONOCIDOS`),
  agrupadas en **«Mientras el sistema trabaja (esperar)»** (las 3 `data-cargando`) y **«Avisos que
  se responden»** (los 13 `data-modal`), cada una con su dibujo; se elige una y queda insertada EN
  ESE HUECO ya nombrada, con el título diciendo entre qué pasos va. (b) La ventana de TRABAJO se
  dibuja como lo que es —barra de progreso y SIN ✕ (no se cierra a mano)—; el dibujo lo hace un
  solo helper `ventanita()` que comparten el catálogo y la línea, así lo que elegís es igual a lo
  que queda puesto. (c) `aGuion` distingue trabajo de aviso: el cartel de una carga dice **esperar**
  («el sistema se pone a trabajar… esperá a que termine», nota «no hay nada que tocar») en vez del
  genérico «respondé lo que pide», que mandaba a buscar un botón inexistente; campo `esTrabajo`.
  CONTRATO en `verificar_guion.mjs` («la ventana de TRABAJO pide ESPERAR; la de aviso, responder»),
  probado en negativo. VERIFICADO EN LA UI REAL (sandbox 8060 sobre el tutorial «Camiseta» del
  usuario, 32 pasos): 33 huecos «+», catálogo con los 2 grupos y 16 ventanas, insertar deja la
  ventanita con barra de progreso y sin ✕ en la posición 4, el detalle queda con ella elegida, y la
  **vista real** la muestra en su lugar del tiempo («🗔 Se está poniendo el diseño sobre el molde.»
  entre «Elegir los moldes» y «Diseños del pedido»). ⚠️ Trampa de la verificación: el label «Así
  corre:» va en `text-transform: uppercase` → buscarlo por `innerText` exige comparar en MAYÚSCULAS
  (parecía que la vista real no se prendía y sí funcionaba).
- **2026-08-28 (341) — EL PASO QUE VIVE EN UNA VENTANA EMERGENTE MUESTRA SU VENTANA.** Pedido del
  usuario (captura del chip «Entendido»): «este paso se hace en una ventana emergente y no la veo a
  la ventana» — el clic grabado dentro del modal «Perfil de color del diseño» aparecía como un chip
  suelto, sin rastro de la ventana a la que pertenece. Nuevo campo del paso: **`ventana`** (el
  título del `[data-modal]` donde cayó el clic). (a) GRABADOR (App.jsx `pasosGrab` y la captura «⏺
  Agregar pasos» del editor): `el.closest('[data-modal]')` → `ventana: <título>`. (b) SERVER
  (`guardar_tutorial`): persiste `ventana` (80 chars). (c) EDITOR (tutor.jsx): el chip con
  `ventana` se dibuja como VENTANITA ámbar — mini barra de título con el nombre de la ventana y el
  botón adentro («Perfil de color del diseño › Entendido»); y en el detalle de cualquier paso de
  clic hay un selector «Sin ventana / en: …» (títulos de `AVISOS_CONOCIDOS.modales`) para asignarla
  A MANO a los tutoriales YA grabados sin el dato (el del usuario). (d) REPRODUCCIÓN (Tour): si al
  llegar al paso su ventana NO está abierta, el cartel explica «este paso va en la ventana “X”, que
  se abre sola en este punto… si no te salió, Siguiente →» (paso con `esVentanaFalta`; se suprime
  el «Buscando ese lugar…» que lo contradecía) en vez de buscar un botón que no existe; cuando la
  ventana aparece, el flujo normal la señala adentro (la exención de `bloqueoModal` ya cubría ese
  caso). (e) GUION (`aGuion`): copia `ventana` al paso. CONTRATOS: `verificar_guion.mjs` («el paso
  grabado dentro de una ventana conserva `ventana`», probado en negativo) y **nuevo
  `verificar_tutorial_ventana.py`** (backend con doble de `db`: POST/GET persisten
  ventana/texto/mid/repite, la basura se recorta; ⚠️ el catálogo ahora vive en la base → el doble
  necesita `get_doc`/`set_doc` EN MEMORIA + `proyectar_catalogo` no-op, y hay que sabotear
  `api_usuarios` en `sys.modules` para que no exija sesión — mismo patrón que
  `verificar_config_concurrente.py`/`srv_visor.py`). Al reiniciar quedó un server HUÉRFANO de la
  mañana sin puerto (el 8050 lo tenía el nuevo): matado por PID específico — verificar SIEMPRE
  quién tiene el puerto con `Get-NetTCPConnection` antes de asumir cuál corre.
- **2026-08-28 (340) — LA MARCA «↻»: rango DE MARCA A MARCA y selección EN LA LÍNEA REAL.**
  Correcciones del usuario sobre la 339: (a) los pasos elegibles van desde la marca ANTERIOR hasta
  ésta (lo previo pertenece a la vuelta de la otra marca); (b) la lista de píldoras se eliminó —
  al presionar la marca aparece el botón «Elegir pasos del siguiente diseño» y, habilitado, los
  pasos se seleccionan APRETANDO LOS CHIPS DE LA LÍNEA: los del rango quedan ofrecidos (contorno
  punteado violeta), el resto atenuado (35%) y sin efecto. «Todos»/«Ninguno» operan sobre el
  rango. Salir de la marca apaga el modo.
  🔴 **Casi-desastre evitado**: creí que un parche a medias había ensuciado tutor.jsx e intenté
  `git checkout --` — el clasificador lo bloqueó, y MENOS MAL: todo el trabajo del día está SIN
  COMMITEAR y eso lo borraba entero. El parche nunca se había ejecutado; el archivo estaba sano.
  **Lección: verificar el estado real ANTES de revertir, y nunca `git checkout --` sobre trabajo
  sin commitear.** Build y salud ok; sólo frontend.

- **2026-08-28 (339) — LA HERRAMIENTA DE LA MARCA «↻».** Pedido del usuario: al presionar la
  marca, una herramienta para SELECCIONAR los pasos que se vuelven a hacer en el siguiente diseño.
  El detalle de la marca ahora ES esa herramienta: la lista de los pasos ANTERIORES a la marca,
  cada uno como píldora con su tilde — se tocan para entrar/salir de la repetición — más los
  botones «Todos» / «Ninguno». Todo pasa por `alternarPintado(k, mid)`, el mismo camino que el
  pintado tocando los chips de la línea (las dos formas conviven). Sólo se listan los pasos de
  ANTES de la marca (lo de después no puede repetirse desde ahí). Build y salud ok; sólo frontend.

- **2026-08-28 (338) — 🔴 CADA MARCA «↻» ELIGE SUS PASOS, y quedan PINTADOS.** Pedido del
  usuario: al tocar una marca, poder marcar QUÉ pasos arrancan desde ahí; se repiten en el mismo
  orden y quedan pintados. Marcas: todas las que se quieran.
  **Modelo**: cada marca lleva identidad (`mid`); cada paso pintado guarda `repite: [mid,…]`
  (puede estar en varias marcas). El servidor persiste los dos campos.
  **Editor**: con una marca elegida, TOCAR un paso lo pinta/despinta para esa marca. Pintado =
  lavado violeta suave (+ insignia ↻) siempre visible; con su marca elegida, fuerte. El detalle de
  la marca dice cuántos pasos repite y cómo pintar. Las marcas nacen con `mid` (al materializar y
  al insertar con «+ ↻ marca»).
  **Reproducción** (Tour): al llegar a una marca con pasos pintados y trabajo pendiente, se salta
  al PRIMER pintado y los no pintados del medio se pasan de largo hasta volver a la marca
  (`replayRef`); otra marca en el medio del replay se ignora. Se repite mientras falte algún
  diseño — misma regla para N. **Sin pintar ninguno**: vuelve al principio y el salteo inteligente
  pide sólo lo necesario (el modo de la 337, que queda como automático).
  **Vista real**: la 2ª vuelta muestra EXACTAMENTE los pintados, en su orden.
  Contratos: servidor guarda `mid`/`repite`; la vista real repite exactamente los pintados
  (verificado ejecutando el guion). Server reiniciado y verificado; build y salud ok.

- **2026-08-28 (337) — 🔴 LA MARCA «↻» ES LIBRE: un ítem más de la línea, y su significado es
  «hasta acá».** Corrección del usuario sobre la 336: la marca tiene que poder acomodarse
  «libremente entre medio de cualquier paso», y lo que indica es que «hasta ahí pedirá todos los
  pasos anteriores que sean necesarios o que sean doble de hacer».
  **Modelo nuevo**: la marca es un PASO más (`accion:'vuelta'`, sin ancla — el servidor la acepta
  como al «esperar aviso»). En el editor es un chip violeta punteado que se arrastra como
  cualquier otro, a CUALQUIER lugar; se materializa sola al abrir un tutorial sin marcas (una por
  bloque, al final del bloque). La restricción «sólo dentro de su bloque» se eliminó.
  **Semántica en la reproducción** (Tour): al llegar a la marca, si a algún diseño le falta lo
  suyo en las etapas que la PRECEDEN (la marca las aprende al armar el guion), se **vuelve al
  principio** — y como lo ya hecho se saltea solo (superado/hecho/listo), se piden exactamente
  los pasos NECESARIOS. Si no falta nada, se pasa de largo. Misma regla para 2, 10 o 100 diseños.
  🔴 Con marcas a mano, el bucle automático por bloques NO corre (gobiernan ellas); sin marcas,
  el automático sigue (compat). La marca no navega ni arma puentes (no es un lugar de la pantalla).
  **Agilidad**: umbral del arrastre 6→3 px. La vista real muestra la repetición desde cada marca.
  Contratos: el servidor guarda `accion:'vuelta'` sin ancla y en su lugar; el guion aprende las
  etapas y apaga el bucle automático. Server reiniciado y verificado; build y salud ok.

- **2026-08-28 (336) — 🔴 EL MARCADOR «↻ DISEÑO 2» NO SE PODÍA MOVER: el drag nativo de HTML5
  se corta al re-dibujar.** Reporte del usuario: «te dije que tengo que poder mover dónde empieza
  el diseño 2». La causa NO era la lógica (vuelta2 andaba, contrato en verde): era el
  **`draggable` nativo** — cuando el elemento arrastrado se re-monta (y la línea se reacomoda EN
  VIVO, o sea siempre), el navegador CORTA el drag. El gesto moría al primer movimiento.
  **Arreglo**: todo el arrastre del editor pasó a **MOUSE** (mousedown/mousemove/mouseup +
  `elementsFromPoint` sobre `data-chip-idx`), que es inmune al re-render — el mismo mecanismo de
  las filas de la planilla, que ya está probado en pantalla. Umbral de 6 px: clic corto = elegir
  el paso; más que eso = arrastrar. El marcador sólo acepta caer dentro de su propio bloque.
  **Semántica confirmada para N diseños**: el bucle de reproducción salta a `bucle.desde` (la
  marca) MIENTRAS la etapa siga incompleta → con 2, 10 o 100 diseños, CADA vuelta siguiente
  arranca donde diga la marca. Es una sola regla, como pidió el usuario.
  🔴 **Lección para el mapa**: en esta app, drag & drop = SIEMPRE por mouse, nunca `draggable`
  nativo — dos veces ya (planilla 2026-08-27, editor hoy) el nativo murió por el re-render en vivo.
  Build en verde; sólo frontend, sin reinicio.

- **2026-08-28 (335) — EDITOR v3: una sola línea, el marcador «↻ diseño 2» movible y las
  VENTANITAS en su lugar.** Correcciones del usuario sobre la 334: la fila «CON 2+ DISEÑOS» se
  ELIMINÓ; en su lugar, **dentro de la línea única**, cada paso real del armado (moldes, arte)
  muestra un marcador violeta punteado «↻ diseño 2 arranca acá» en el punto donde el bloque se
  repite — y **se arrastra a otro paso del mismo bloque** para cambiar desde dónde arranca la
  segunda vuelta. Se guarda como **`vuelta2`** en el paso (servidor lo persiste; `aGuion` lo copia
  — 🔴 el contrato agarró que NO lo copiaba — y `bloquesPorDiseno()` lo respeta: `bucle.desde` =
  la marca). La vista real despliega la 2ª vuelta desde ahí.
  Los pasos de MODAL se dibujan como **VENTANITAS** ámbar (barra de título con puntitos y ✕)
  en su posición exacta de la línea — «ver los modales reales en sus respectivos pasos».
  La condición «sólo con 2+ / sólo con 1» volvió al detalle del paso (ya no la codifica la fila).
  Contratos: guion (vuelta2 mueve el `desde`), servidor (vuelta2 se guarda y no se inventa).
  Build en verde, server reiniciado y verificado, salud ok.

- **2026-08-28 (334) — EDITOR DE PASOS: la VISTA REAL y los AVISOS se ELIGEN (no se tipean).**
  Tres pedidos del usuario sobre la 333:
  · **«▶ Vista real (2 diseños)»**: una tira extra bajo las pistas que muestra **el orden del
  tiempo al reproducir con 2 diseños** — `vistaReal()` (guion.js) toma el guion completo (etapas
  agregadas, avisos convertidos) y despliega cada bloque por diseño dos veces con el marcador
  «↻ siguiente diseño» entre vueltas; lo agregado por el sistema va con borde punteado, la
  segunda vuelta con ②, los avisos con ⏳.
  · **AVISOS_CONOCIDOS** (diccionario.js): el sistema ya sabe qué modales y cargas existen — 13
  modales + 3 cargas — así que el paso «esperar aviso» se elige de un selector (con «Otro…»
  para escribir uno raro). 🔴 Contrato: cada título de la lista tiene que existir LETRA POR
  LETRA en App.jsx — si alguien renombra un modal sin tocar la lista, el build corta (un paso
  esperando un aviso renombrado esperaría para siempre).
  · El «esperar aviso» ahora también espera **CARGAS** (`data-cargando`): `avisoAb` = modal O
  carga; si la carga visible ES la que el paso espera, se muestra el cartel del paso (no el
  genérico), y el avance exige que se haya ido (ni modal ni carga).
  Contrato del guion §12 (vista real, ejecutada): marcador presente, aviso en las dos vueltas,
  cargar-arte dos veces, orden alrededor de SU marcador (ojo: moldes también bucla → hay varios
  marcadores), lo agregado marcado. Build en verde; sólo frontend.

- **2026-08-28 (333) — EDITOR DE PASOS: el sistema se ESCALA, no se tapa.** Pedido del usuario:
  al entrar al modo diseño, en vez de que la barra inferior se sobreponga, **todo el sistema se
  achica proporcionalmente** (`#root` con `transform: scale`, origen arriba-centro, transición
  suave) para que la línea de tiempo quede DEBAJO y se vea todo — como la vista previa de un
  editor de video. La escala se recalcula al cambiar el alto de la barra (aparece la fila 2+) y al
  redimensionar la ventana; al salir se restaura.
  🔴 Por qué funciona sin tocar nada más: los PORTALES (modales, la propia barra, el resaltado)
  viven en `<body>`, fuera de `#root`, así que no se escalan; y el resaltado se mide con
  `getBoundingClientRect` sobre lo ya dibujado → sus coordenadas coinciden con lo que se ve.
  Build en verde; sólo frontend. ⚠️ Sin probar en pantalla con sesión.

- **2026-08-28 (332) — EDITOR DE PASOS v2: dos PISTAS con colores y «Agregar pasos» tocando la
  app.** Pedidos del usuario sobre la 331: poder AGREGAR pasos desde el editor, una visual más
  intuitiva, y que la condición «2+ diseños» sea una FILA nueva con los casilleros marcados,
  dividida por colores.
  · **Dos pistas** como un editor de video: «SIEMPRE» (cian) y «CON 2+ DISEÑOS» (violeta), con
  rótulo propio a la izquierda. Cada columna es un lugar de la secuencia: la fila que no tiene el
  paso muestra su **casillero punteado** — arrastrar un chip a un casillero lo cambia de lugar
  y/o de fila, y **la fila ES la condición** (soltarlo en la violeta = `solo:{minDisenos:2}`;
  volverlo a la cian la borra). La fila 2+ aparece al marcar el primer paso o con «+ fila 2+
  diseños». Columna extra al final para soltar «al final»; número de orden bajo cada columna.
  · **«⏺ Agregar pasos»**: con el botón prendido (rojo, punto que late), cada control que se toca
  en la app se agrega como paso después del elegido (o al final) — la app responde normal, así se
  navega de verdad; identificado con el mismo `identificar` del grabador; doble clic = un paso; los
  toques a la propia barra no se graban (`[data-diseno-pasos]`).
  · El detalle del paso elegido (cartel, aviso, borrar) sigue arriba de la barra; la condición ya
  no es un select: es la fila.
  Build en verde; sólo frontend, sin reinicio. ⚠️ Arrastre y captura sin probar en pantalla (sin
  sesión); el usuario prueba en vivo.

- **2026-08-28 (331) — MODO DISEÑO DE PASOS: el editor de la grabación es VISUAL, estilo editor
  de video.** Pedido del usuario sobre la 330: «el acomodar la grabación debe ser visual… entrás
  a los pasos como lo harías real, y abajo muestra los pasos en el orden que están y los
  acomodás». El editor en modal de la 330 se REEMPLAZÓ (mismo componente `EditorTutorial`, otra
  forma): ahora, al tocar «Editar» en Ayuda, la app queda **usable de verdad** y abajo aparece una
  **LÍNEA DE TIEMPO** fija con los pasos como chips (numerados, coloreados por etapa:
  diseño/moldes/arte/planilla/resultados; ámbar para «esperar aviso»).
  · **Arrastrar un chip lo cambia de lugar**, reacomodándose EN VIVO (mismo gesto que las filas de
  la planilla, que el usuario ya aprobó).
  · **Tocar un chip** lo elige: la pantalla VA a donde ese paso vive (`ir(p.donde)`), su control se
  RESALTA con un borde (sin oscurecer nada — la app se sigue usando) y arriba de la barra aparece
  su detalle: cartel corregible, condición «sólo con 2+ diseños», borrar, «+ aviso».
  · Nada se guarda hasta «Guardar» (mismo POST de la 330; los campos ya estaban soportados).
  Build en verde, salud ok; sólo frontend, sin reinicio.
  ⚠️ Sin probar el arrastre en pantalla (necesita sesión y en el sandbox no se dibuja la barra
  lateral para abrir Ayuda). El usuario está probando en vivo.

- **2026-08-28 (330) — 🔴 TUTORIAL: el bug del ORDEN, el botón «Siguiente →» y el EDITOR de
  tutoriales.** El usuario reportó «está todo mal» con tres síntomas y pidió tres cosas.
  **(1) EL BUG DEL ORDEN** («me manda a hacer un paso después que era antes»): al completar
  etapas faltantes, un botón de TRANSICIÓN («A la planilla») sólo exigía lo anterior a SU etapa
  → la etapa de telas (que es del arte) se insertaba DESPUÉS del botón y su `ir` arrastraba de la
  planilla al arte. Arreglo: `AVANZA_A` en guion.js — una transición exige TODO lo anterior a su
  etapa DESTINO. Contrato §10: telas queda ANTES de «A la planilla».
  **(2) «SIGUIENTE →» en el globo**: pasar el paso sin hacer lo que pide, siempre disponible
  (salvo en preguntas y esperas). Va DIRECTO al paso siguiente, sin el bucle por diseño.
  De paso: el pie del globo en las esperas decía «Tocá lo que está marcado» (se veía en la
  captura del usuario) → ahora dice «Cerralo y seguimos» / «Esperando…».
  **(3) EL EDITOR DE TUTORIALES** (`EditorTutorial`, tutor.jsx; botón «Editar» en el menú de
  Ayuda): ver los pasos grabados y corregirlos — subir/bajar (cambiar de lugar), borrar, corregir
  el CARTEL a mano (`paso.texto`, le gana al diccionario), la CONDICIÓN («sólo con 2+ diseños» /
  «sólo con 1» → `paso.solo`) e insertar un paso «ESPERAR AVISO» (`accion:'modal'` + título →
  en la reproducción espera a que ese modal aparezca Y se cierre, iluminado y explicado;
  `modalPaso` en el Tour). La cantidad de diseños para `solo` toma el MAYOR entre lo elegido y lo
  respondido a «¿cuántos?» (la intención cuenta antes de tocar).
  **Servidor**: el sanitizador de `/api/tutoriales` guarda `texto`/`solo`/`modal` y acepta pasos
  sin ancla si son `modal`. Python → reiniciado y verificado por hora de arranque.
  **USADO EL SISTEMA DE VERDAD**: sandbox 8060 → elegí un diseño, fui a moldes, abrí el modal
  «Subir mi propio molde» y `[data-modal]` lo encontró con su título — la detección de modales
  confirmada en el DOM real. Los 25 modales del componente + 2 artesanales quedan cubiertos.
  **Verificado**: e2e endpoints (campos del editor sobreviven, condición rota no explota),
  contrato del guion §10/§11 en verde, build ok, salud ok.
  ⚠️ Sobre «di un paso que no me registró»: sin saber cuál fue no se puede arreglar a ciegas —
  ahora el EDITOR muestra exactamente qué se grabó, así que la próxima vez se ve ahí qué faltó
  (y el cartel «N sin grabar» durante la grabación avisa en el momento).

- **2026-08-28 (329) — 🔴 EL BUCLE POR DISEÑO: lo hecho antes de «siguiente» es el trabajo de UN
  diseño, y se repite para cada uno.** El usuario ofreció dos caminos (un editor de tutoriales o la
  inteligencia automática) y definió la semántica exacta: *«todo lo que se haga en cada paso antes
  de darle al botón siguiente —ese inferior que salta de diseño a arte, de arte a planilla— es el
  paso de un solo diseño. Si elige 2, saltará al segundo después de hacer todos los pasos, antes de
  presionar siguiente»*. Se implementó la automática.
  **Cómo**: `aGuion` marca el BLOQUE de cada etapa (los pasos seguidos de moldes/arte, con los
  botones de transición —`TRANSICIONES`— como frontera, fuera del bloque). El último paso lleva
  `bucle: {desde, etapa}`. En `avanzar()` (Tour): al salir de ese paso, si
  **`etapaIncompleta(etapa, E)`** (alguna regla `listo` de la SECUENCIA de esa etapa no se cumple)
  → **se vuelve al inicio del bloque** en vez de seguir, 🔴 rebobinando `desde.current` (sin eso
  los pasos repetidos no podrían avanzar: el guard anti-doble-avance los bloqueaba). El ciclo
  `antes` hace el resto: el diseño a la vista está completo → manda al chip del siguiente.
  Con 1 diseño la etapa cierra a la primera pasada → no hay vuelta: nada cambia.
  **Además**: las TELAS tienen ahora su propio ciclo (`arte-telas.antes` → chips del arte; faltaba)
  con el estado nuevo `activoTelasListas` (arte del diseño a la vista cargado y sin piezas sin
  tela, filtrando `telasFaltantesDet` por `disenoActivo`).
  **Contrato** (`verificar_guion.mjs` §9, ejecutado de verdad): el bloque del arte marca su bucle
  hacia `arte-cargar`, el «siguiente» queda fuera, moldes también bucla, `etapaIncompleta` da la
  vuelta con un solo arte cargado y cierra con los dos + telas completas. Build en verde; sólo
  frontend, sin reinicio.

- **2026-08-28 (328) — 🔴 Barrido de overlays: la carga «Poniendo el diseño sobre el molde…»
  y 2 modales artesanales quedaron marcados.** El usuario cazó al tutorial pasando por encima de
  ese panel (saltó al desvío «siguiente diseño» con la carga en pantalla): era una carga SIN
  `data-cargando` — sólo había marcado 2 de 3. Esta vez se barrió TODO `position:fixed; inset:0`
  de App.jsx: además de esa carga aparecieron **dos modales que no pasan por el componente Modal**
  («Elegí las variantes» y «Registrar capa editable») → marcados con `data-modal` a mano. Los dos
  que NO se marcan, a propósito: el catcher invisible de los popovers de Ayuda (transparente, no es
  un modal) y el editor de diseño a pantalla completa (es un espacio de trabajo con anclas adentro).
  El contrato ahora exige **3** superficies `data-cargando`. ⚠️ Trampa propia: el script de parche
  murió en el 2º reemplazo y el 1º quedó sin escribir (el write va al final) — verificar SIEMPRE
  re-escaneando, no por el OK del script.

- **2026-08-28 (327) — 🔴 EL TUTORIAL RESPETA TODOS LOS MODALES.** Reporte en pantalla: cargado
  el arte del primer diseño, el sistema abrió el aviso «Perfil de color del diseño» — y el
  tutorial le pasó por encima (saltó al desvío «tocá el SIGUIENTE diseño» con el modal abierto).
  Pedido textual: *«no puede avanzar a otros pasos si hay modales abiertos y debe explicar qué es
  ese modal»*.
  **La marca, en UN solo lugar**: el componente `Modal` (por el que pasan TODOS los modales del
  sistema) pone `data-modal={titulo}` en su caja → los presentes y los futuros quedan cubiertos
  sin tocar nada más.
  **El freno** (`useModalAbierto` + `bloqueoModal`, tutor.jsx): con un modal abierto que NO es del
  paso en curso, ningún camino avanza (estado, clic, nav, `ir`, salteo por `superado`, desvío,
  pregunta). El globo marca EL MODAL — rótulo «Primero este aviso» — y lo explica: con entrada
  del diccionario (**clave `modal:<título normalizado>`**, la primera es la del perfil de color) o,
  sin entrada, con su propio título («Apareció ‹X›. Leelo y respondé lo que pide» —
  `explicarModal`, guion.js). Cerrado el modal, retoma solo donde estaba.
  🔴 **Un paso cuyo control vive DENTRO del modal no se frena** (cargar por lote, asignar telas,
  un «Entendido» grabado): se detecta con `buscar(ancla)` ∈ modal — ése es justamente el paso a
  hacer. Sinergia: `elegirEntre` (localizar.js) ya prefería candidatos dentro de `[data-modal]`.
  **Contrato**: dos candados nuevos en `verificar_diccionario.mjs` (el Modal marca / el motor
  frena) + las claves `modal:` exentas del chequeo de sobrantes. Build en verde; sólo frontend.
  ⚠️ Cabo suelto conocido: un paso grabado apuntando adentro de un modal que al reproducir no se
  abre (ej. el «Entendido» de un aviso que al otro no le sale) queda esperando hasta el escape
  «Seguir igual». Si molesta en la práctica, el próximo paso es saltear solo los `txt:` no
  encontrados tras un tiempo.

- **2026-08-28 (326) — 🔴 «¿CUÁNTOS?» CUENTA EL TOTAL: lo ya presionado también se reconoce.**
  Reporte en pantalla del usuario: tenía **2 diseños ya marcados** (✓ JUGADOR, ✓ GOLERO),
  respondió «2» y el contador decía «0 de 2» — la cuenta era RELATIVA («N más desde que
  respondió», decisión mía del changelog 318) y encima **tocar un botón ya presionado lo
  desmarca**: no había forma de avanzar.
  **Regla corregida**: `hecho = mide(E) >= n` — contra el TOTAL del sistema. Si dijo 2 y ya hay 2
  elegidos, el paso se cumple al instante; el contador muestra el total real («2 de 2»). El
  contador del globo también pasó a absoluto.
  **Y `telas-panel` dejó de preguntar**: preguntaba algo que el sistema SÍ sabe (cuántas piezas
  quedan sin tela) con una cuenta en negativo que no funciona en absoluto — violaba la propia
  regla «sólo se pregunta lo que no se puede deducir». La etapa de telas ya se controla con el
  `listo` de `arte-telas`. Quedan 2 preguntas: diseños y filas de la planilla.
  Build en verde; sólo frontend, sin reinicio.

- **2026-08-28 (325) — TUTORIAL: respeta los carteles de CARGA y arranca DESDE DONDE ESTÁS.**
  Dos pedidos del usuario en la misma sesión de prueba.
  **(1) Los carteles de carga.** *«No mandará al siguiente paso: marcará el modal de carga y dirá
  que hay que esperar, y ahí salta al paso correcto.»* Mecanismo GENÉRICO: toda superficie de
  carga se marca con **`data-cargando="<texto>"`** (hoy: el overlay «Procesando…» de subir
  molde/arte y el panel «Armando la tizada») y el motor la vigila (`useCargando`, tutor.jsx).
  Mientras está visible: se marca EL CARTEL con globo ámbar ⏳ «Esperá un momento · Debés esperar
  a que esto termine» y **ningún camino avanza** (ni estado, ni clic, ni `esPasoNav`, ni el `ir`
  automático, ni la pregunta ¿cuántas?). Al desaparecer, la evaluación retoma sola y lo cumplido
  se saltea → cae en el paso correcto. **Un cartel nuevo = ponerle el atributo, nada más.**
  **(2) Arranca desde donde estás.** *«Si pongo el tutorial ya avanzado —ya elegí un diseño, ya
  estoy en el arte o en la planilla— debe reconocer dónde está y qué paso ya di, y mostrar desde
  ahí en adelante.»* Antes un paso de una etapa anterior sin condición propia (un clic grabado) se
  mostraba igual y su `ir` te ARRASTRABA de vuelta. Ahora — **`pasoSuperado(paso, E, donde)`** en
  guion.js: un paso queda atrás sólo si (a) su etapa es ANTERIOR a la pantalla en la que estás
  parado y (b) esa etapa está CUMPLIDA según el estado real (las reglas `listo` de la SECUENCIA).
  🔴 **La (b) es la red**: parado en la planilla con telas faltando, el paso del arte NO se
  saltea — el tutorial te lleva de vuelta a terminarlo. Un paso superado tampoco dispara su
  puente/`ir` ni su pregunta.
  **Contratos**: `verificar_diccionario.mjs` §8 (los 2 candados de la carga) y
  `verificar_guion.mjs` §8 (8 casos de `pasoSuperado`, ejecutados de verdad). Build en verde,
  salud ok; sólo frontend — sin reinicio.
  ⚠️ Sin probar en pantalla con sesión; el usuario está probando en vivo y reportando.

- **2026-08-28 (324) — 🔴 EL CICLO DENTRO DEL PASO: con varios diseños, el tutorial manda al
  siguiente.** Reporte del usuario probando en pantalla: grabó un tutorial subiendo UNA camiseta y
  lo reprodujo con 2 diseños. La pregunta «¿cuántos?» y el contador anduvieron, pero tras elegir
  la prenda del primer diseño *«ahí quedó y tenía que haber saltado otra vez a diseños para
  elegir el próximo»*. El paso esperaba (su `listo` mira `sinVariable === 0`, correcto) pero
  seguía iluminando las prendas, sin decir que primero había que tocar el chip del OTRO diseño.
  **La regla nueva — `antes` en el diccionario** (tercera del juego, junto a `listo` y `cuantos`):
  un paso que abarca varios diseños declara `{ ancla, cuando(E), texto }` — cuando el diseño a la
  vista ya quedó listo pero el paso no se cumple, el Tour marca el chip del siguiente (un DESVÍO,
  como el puente: no avanza nada; al tocar el chip `cuando` se apaga y la iluminación vuelve sola).
  Declarados: la PRENDA (`pedido-variables` → chips `pedido-diseno-chips`) y el ARTE
  (`arte-cargar` → chips `arte-diseno-chips`, ancla nueva — esos chips no tenían).
  **Estado nuevo en `ayudaEstado`**: `activoConVariable` y `activoArteCargado` (¿el diseño A LA
  VISTA ya tiene lo suyo?). 🔴 **Trampa que casi me como**: en el paso MOLDES el diseño «en
  armado» es **`asignDiseno`** (ahí va la prenda tocada), no `disenoActivo` (que es del paso Arte).
  Mirar el equivocado dejaba el desvío encendido aunque ya hubieras pasado al siguiente.
  **Contratos**: `verificar_diccionario.mjs` ejecuta cada `antes` contra tres fotos (vacío / a
  mitad / terminado) y exige que se encienda sólo a mitad de camino; `verificar_guion.mjs` §7
  reproduce el caso exacto del usuario (grabado con 1, reproducido con 2). Probado en negativo:
  borrando el ciclo del diccionario, los contratos lo agarran.
  El desvío NO dispara el avance por clic del DOM (guarda `esDesvio`); sólo Python no se tocó →
  sin reinicio, build en verde, salud ok.

- **2026-08-28 (323) — 🔴 «ANCHO MANDA» NO LLEGABA AL MOTOR: la tizada escalaba siempre por el
  alto.** Reportado por el usuario: *«cuando ponen en el molde ancho manda, en el pedido no respeta
  eso y usa el alto predeterminado»*. Confirmado: `referencia_medida` sólo se usaba para las
  medidas de la PLANTILLA y para la pantalla — **nunca llegaba a `generar_pedido`**, y `cm_encajar`
  tenía la escala por alto **fija**. O sea: el diseñador hacía el arte con una medida y el motor lo
  escalaba con otra.
  **El arreglo, en un solo lugar — `_encaje(aw, ah, pw, ph, referencia)`**: devuelve
  `(awf, ahf, offx, offy)`, o sea cuánto ocupa el DISEÑO sobre la pieza y cuánto se corre.
  Con «alto» da `ahf=1, offy=0` → **exactamente las cuentas de antes**; con «ancho» es el espejo.
  De ahí toman: `cm_encajar`, `cm_tamano_editable`, `_pos_en_pieza`, `pos_agregado_en_diseno`,
  `_centro_editable` y `_matriz_editable` (el mover ahora se mide contra `ahf*H`, no contra `H`).
  🔴 **Y la copia que tiene el SERVIDOR** (la que usa el editor) pasó a llamar a `MP._encaje`: si
  el editor y el motor calcularan distinto se rompería la ley «el arte se ve igual que la tizada».
  **La referencia viaja por los cuatro caminos**: preview del arte, molde guía de la ficha, el otro
  camino de generación y el pedido multi-molde (`md["referencia"]`, porque **cada molde puede tener
  la suya**). Y entra en la **clave del caché del visor (v14)**: sin eso, cambiar el ajuste servía
  el render viejo — la trampa de siempre.
  **Contrato nuevo `verificar_referencia_medida.py`**, con la NO-REGRESIÓN primero: con «alto» las
  cuentas dan **idénticas a las de antes** (los moldes que no usan «ancho manda» no cambian un
  píxel). Además: la escala es uniforme en los dos casos, un objeto centrado en el arte cae
  centrado en la pieza con cualquiera de las dos referencias, y **no queda ninguna escala por alto
  suelta** (las dos que hay están dentro del `if` de la referencia).
  ⚠️ **Lo que el contrato me corrigió a mí**: (1) mi primera prueba asumía que la dimensión que NO
  manda nunca se pasa de la pieza — falso: según la proporción del arte a veces sobra y **la
  recorta el contorno**, que es lo correcto; (2) me había **olvidado `cm_tamano_editable`**, que
  coloca los editables con tamaño configurado y también tenía la escala por alto fija — lo
  encontró el chequeo de «no queda ninguna suelta».
  No-regresión: medidas, marcas, cantidad, etiqueta y agregar-pieza siguen en verde.

- **2026-08-28 (322) — 🔴 LA PLANTILLA PEDÍA UNA MEDIDA CORTA: hasta 0,5 mm de tela SIN
  ESTAMPAR.** El usuario lo notó: *«hay algunos artes que no llegan a cubrir el ancho completo si
  pongo en default … me debería de dar un ancho que cubra todos los anchos»*. Tenía razón.
  **El cálculo estaba BIEN, el redondeo no.** `medidas_diseno` resuelve la proporción crítica
  correctamente (el motor escala igualando el ALTO de la pieza en cada talle, así que el diseño
  necesita ancho/alto >= el mayor w/h de todos los talles), pero cerraba con `round(x, 1)`, que
  **redondea para abajo**. Medido con el molde real del usuario: **11 de 34 piezas quedaban entre
  0,1 y 0,5 mm cortas** — esa franja sale sin estampar en el borde, y **sale bien impresa**: nadie
  se entera hasta que la prenda está cortada.
  **El arreglo — `_cm_arriba()`**: al milímetro y **siempre hacia arriba**. Sobrar no molesta: lo
  que sobra lo recorta el contorno de la pieza. La dimensión derivada se calcula sobre la base **ya
  redondeada**, así la proporción que ve el diseñador nunca queda por debajo de la necesaria.
  Aplicado a las dos referencias (alto y ancho) y también al modo **rango** de `_guia_capas_data`,
  que tenía el mismo `round`.
  **Medido después del arreglo, con el mismo molde: 34 de 34 cubren. 0 sin cubrir.**
  **Qué alto manda** (la otra pregunta del usuario): en `default`, el del **talle guía** del molde
  (`variante_guia`). La medida se da en esa escala para que el recuadro dibujado coincida con la
  pieza que se ve en el visor; el motor después escala a cada talle, y como la proporción es
  invariante a la escala, la cobertura vale para todos.
  **Contrato nuevo `verificar_medidas_diseno.py`**: la regla de oro (el ancho cubre todos los
  talles) con piezas que se ensanchan y que se angostan, el talle crítico correcto, las dos
  referencias, la base en la escala del talle guía, y que **nunca redondee para abajo**.
  **Probado en negativo**: se puso de vuelta el `round()` viejo y **el contrato lo agarra**.
  No-regresión: marcas, cantidad y etiqueta siguen en verde.

- **2026-08-27 (321) — 🔴 EL TUTORIAL COMPLETA SOLO LOS PASOS QUE LA GRABACIÓN NO TIENE.**
  Reporte del usuario, y era un agujero de fondo: *«cargué 2 diseños pero en el tutorial, como puse
  1 solo, obvio que no presioné en el diseño porque no era necesario; después en la ayuda no me
  mandó a eso. Leé los pasos coherentes y hacé que se pongan automático.»*
  **El problema**: una grabación sólo guarda lo que la persona **llegó a hacer**. Lo que ya tenía
  resuelto al grabar no queda grabado → el tutorial salía **con agujeros** y no llevaba a nadie a
  hacer algo imprescindible.
  **La solución — `SECUENCIA` en `diccionario.js`**: el orden real del trabajo escrito una vez
  (diseño → molde → arte → telas → planilla → enviar), cada etapa con su ancla y su `listo`. Al
  REPRODUCIR, `aGuion` mira hasta dónde llega la grabación y **mete las etapas anteriores que
  falten, justo antes del paso que las necesita**. Y como cada una trae su `listo`, **a quien ya la
  tenga resuelta no se le muestra**: se completa lo que falta, no se repite lo hecho.
  🔴 Se hace **al reproducir, no al grabar**: corregir la secuencia arregla **todos los tutoriales
  ya grabados**, sin regrabar nada. Misma propiedad que el diccionario.
  **`frontend/src/guion.js` (nuevo)**: `aGuion` salió de `tutor.jsx` a un módulo propio. `tutor.jsx`
  importa React y sólo corre en el navegador, así que la lógica que arma el guion **no se podía
  ejecutar ni verificar**. Ahora es JS puro. ⚠️ Sus imports llevan `.js` sí o sí: node lo exige.
  **Contrato nuevo `verificar_guion.mjs`** (corre en cada `npm run build`), y **ejecuta el código de
  verdad**. Cubre el caso del usuario tal cual: grabación con sólo el paso del molde → el guion
  agrega el del diseño **antes**; el paso agregado se saltea a quien ya tiene el diseño; no se
  duplica lo que la grabación ya trae; una grabación que arranca al final trae **toda la cadena**;
  y un tutorial de Configuración **no** se contamina con la secuencia del pedido.
  **Probado en negativo**: sacando una etapa de la SECUENCIA y dando vuelta el orden → **el
  contrato agarra los dos**.
  ⚠️ Sin probar en pantalla con sesión iniciada.

- **2026-08-27 (320) — LA BARRA LATERAL NO APARECE EN LOS TUTORIALES.** Pedido del usuario.
  Moverse entre secciones no es el trabajo que el tutorial enseña, y ensuciaba cada grabación con
  un «tocá Pedidos» antes de lo importante.
  **Son DOS candados y hacen falta los dos** — si se cae uno, la barra vuelve a salir por ese lado
  y nadie se entera hasta ver un tutorial que arranca mal:
  · **el GRABADOR** no anota los clics dentro de `aside.sidebar`;
  · **el MOTOR** ya no MARCA el botón de la barra cuando el paso está en otra sección: **cambia de
  pantalla solo** (`{ llevarSolo }` → `ir(destino)`) y el tutorial arranca directo en lo que
  importa. Mientras viaja, el paso no pide nada.
  🔴 **Los puentes de ADENTRO de una pantalla se siguen marcando** («Entrá a Moldedería»): ésos
  no son la barra y sí son parte del trabajo. La distinción es el prefijo `nav-` de la ruta.
  **Contrato**: `verificar_diccionario.mjs` verifica los dos candados, y se probó **en negativo**
  quitando cada uno: los agarra a los dos.
  ⚠️ **De paso se descubrió que un parche anterior NO se había aplicado**: el grabador seguía
  mirando sólo `[data-tour]` (o sea, 82 de 477 controles) porque el reemplazo había fallado en un
  lote y yo había seguido adelante. **Lección: cuando un parche por lotes falla a la mitad, revisar
  QUÉ quedó sin aplicar, no sólo re-correr lo que falló.** Ya está corregido: el grabador usa el
  localizador.
  ⚠️ Sin probar en pantalla con sesión: en el sandbox la barra lateral no se dibuja.

- **2026-08-27 (319) — EL TUTORIAL YA PUEDE APUNTAR A CUALQUIER CONTROL (no sólo a los 82 con
  ancla).** El usuario pidió arrancar con la cobertura completa. Medido primero:
  **477 controles, 395 sin `data-tour`, y 241 de ellos sin siquiera un texto** — poner 395 anclas a
  mano en JSX es lento y, sobre todo, riesgoso.
  **La solución — `frontend/src/localizar.js`**: dos clases de identificador, siempre se prefiere
  el primero. `nav-pedidos` (el `data-tour` de siempre) · **`txt:guardar`** (el TEXTO VISIBLE del
  control, normalizado). Lo que la persona lee es lo que la persona toca: es lo más estable que hay
  sin tocar el JSX. 🔴 **NO se usan selectores de CSS ni caminos del DOM** (`div > div:nth-child(3)`):
  con React se rompen apenas alguien toca el layout y el tutorial marcaría el botón equivocado, que
  es peor que no marcar nada.
  · Los CAMPOS no tienen texto propio → su identidad sale del `placeholder` o de su RÓTULO, buscado
  subiendo hasta 3 niveles. Sin eso los 88 campos del sistema no se podían grabar (**se descubrió
  probando en la pantalla real**, no leyendo código).
  · Al reproducir, un CAMPO le gana a su rótulo: los dos matchean «Usuario», pero lo que hay que
  iluminar es el campo.
  · Lo que no tiene ni ancla ni texto no se graba, **y el grabador lo dice** («3 sin grabar» en el
  cartel): mejor avisar que grabar un paso que después apunte a cualquier lado.
  **`srv_visor.py` (nuevo)** — sandbox de SÓLO LECTURA en el 8060: la UI real sin login (contesta
  404 en `/api/auth/yo`, que el front lee como «sin usuarios») y **con todo lo que no sea GET
  rechazado**. Es lo que permite medir sobre las pantallas de verdad sin la contraseña del usuario
  y sin poder tocarle nada. Verificado: entra sin login (200), auth/yo 404, POST → 405.
  **`verificar_cobertura_ayuda.mjs` (nuevo)** — genera un medidor para correr EN EL NAVEGADOR.
  Contar `<button>` en el código miente (un mismo botón se dibuja 12 veces, y muchos nunca están
  juntos en pantalla): lo único que vale es medir lo que se ve.
  **MEDIDO en la pantalla real (Pedidos)**: **17 controles visibles → 17 identificados, 17
  recuperados, 17 con explicación. 0 sin identificar, 0 sin explicar.**
  🔴 **Un punto ciego del contrato, encontrado por la medición**: hay anclas que se pasan **POR
  PROP** (`<BtnSiguiente ancla="pedido-ir-moldes">`) y mi regex sólo miraba `data-tour=`. Quedaban
  fuera **los 8 botones que mueven el pedido de un paso al otro** — los más importantes de
  cualquier tutorial. Ya había pasado con el verificador viejo (changelog 269). Corregido, y sus 8
  explicaciones escritas. **126/126.**
  El diccionario ahora acepta claves **`txt:…`** (controles sin ancla), que el contrato no cuenta
  como sobrantes.
  ⚠️ **Hasta dónde llegué**: en el sandbox **no se dibuja la barra lateral** (sin usuario no hay
  navegación), así que sólo pude medir el circuito del pedido. Las pantallas de Configuración hay
  que medirlas **con sesión iniciada en el 8050**, con el mismo medidor. El procedimiento queda
  escrito en `verificar_cobertura_ayuda.mjs`.

- **2026-08-27 (318) — PASOS INTELIGENTES: el tutorial se adapta a quien lo sigue.** Pedido del
  usuario, y su confirmación de qué tiene que lograr: *«sí tiene que llevarlo hasta terminar»* —
  el paso a paso guía **hasta que el pedido queda completo**, no repite lo que se grabó.
  Dos comportamientos, declarados **en el diccionario** (así valen para todos los tutoriales
  grabados, viejos y nuevos):
  · **`cuantos`** — donde una acción se hace varias veces, el globo **PREGUNTA** («¿Cuántos
  diseños vas a cargar?»), y no avanza hasta que se hicieron ésas, con contador («2 de 3
  diseños»). 🔴 **Se cuenta DESDE QUE SE RESPONDE**, no «llegar a N»: lo que la persona ya tenía
  cargado es asunto suyo. Por eso la foto del estado (`e0Ref`) se re-toma al responder.
  · **`listo(E)`** — el paso que **ya no hace falta no se muestra**. Es el caso que planteó el
  usuario: un tutorial grabado cargando una fuente (porque a quien grabó le faltaba) **no le pide
  eso a quien ya la tiene**. Puestas hoy: `arte-fuente`, `arte-cargar`, `arte-telas`,
  `pedido-variables`. Con `cuantos`: `pedido-diseno-lista`, `planilla-agregar`, `telas-panel`.
  🔴 **Sólo se pregunta lo que el sistema NO puede deducir.** Cuántos diseños lleva el trabajo lo
  sabe la persona; si falta el arte o si faltan telas lo sabe el sistema, y eso **no se pregunta:
  se mira**.
  **El motor casi no cambió**: ya tenía `hecho` y ya saltaba el paso cumplido. Lo que faltaba era
  que los pasos grabados declararan la condición. `aGuion` la engancha desde el diccionario.
  **App.jsx**: `ayudaEstado` suma `pedido.fuentesFaltan` — y 🔴 **hubo que MOVER el bloque
  entero** más abajo, porque `fuentesFaltantesItems` se calcula después: un `const` leído antes de
  su declaración deja **la pantalla en blanco**, que es un bug que este archivo ya nos regaló.
  **Contrato ampliado — y ahora EJECUTA las reglas**: `diccionario.js` es JS plano, así que
  `verificar_diccionario.mjs` lo **importa** y corre cada `listo`/`mide` contra dos fotos del
  estado (pedido vacío y pedido terminado). Verifica que no exploten, que devuelvan booleano/número,
  que **los campos que miran existan de verdad en `ayudaEstado`** (si no, la regla lee `undefined` y
  el paso se saltea o insiste **en silencio**) y avisa si una regla da lo mismo en los dos extremos.
  **Probado en negativo**: se rompió una regla a propósito de tres formas (campo inexistente,
  regla que explota, `cuantos` sin pregunta) y **el contrato agarró las tres**. Un contrato que
  nunca falla no sirve.
  ⚠️ **La trampa, otra vez**: `` dentro de una **plantilla de JS** es un **BACKSPACE**, no un
  límite de palabra — el chequeo acusaba a todos los campos de no existir. Ya había pasado
  (changelog 269) con Python. Ahora el regex se arma con comillas y concatenación, y queda avisado
  en el propio archivo.
  ⚠️ **Sin probar en pantalla** (no puedo iniciar sesión): la pregunta del globo y el contador se
  verificaron por código y contrato, no a mano.

- **2026-08-27 (317) — LOS TUTORIALES LOS GRABA EL USUARIO (los guiones fijos se eliminaron).**
  Pedido textual: *«existen unos tutoriales eliminálos … el usuario los creará. Habilitará un
  botón como de grabar, pero no graba un video: el sistema irá guardando todos los pasos que hace
  hasta que lo pare. Le pondrá un nombre, pero los carteles de ayuda los hará el sistema, así que
  cada botón, cada espacio y cada cosa del sistema debe tener una explicación de para qué es y
  cómo se usa»*.
  **Qué se fue**: `frontend/src/guias.js` (los guiones escritos a mano) y `verificar_guias.mjs`.
  **Qué se quedó**: el MOTOR (`tutor.jsx`) entero — iluminar el elemento, esperar la acción real,
  el puente entre pantallas, retomar lo que quedó a medias. Es lo que el usuario pidió conservar.
  **Lo nuevo**:
  · **`frontend/src/diccionario.js`** — la explicación de cada elemento (`nombre` · `que` = para
  qué es · `como` = qué hacer). **118 de 118 anclas cubiertas.** Los textos NO son inventados:
  salieron de los guiones viejos, que se habían escrito mirando las pantallas y el video del
  usuario.
  · **El grabador** (App.jsx): escucha `click` y `change` en **fase de captura sobre `document`**
  (si no, un botón que corta la propagación no se grabaría) y sube por el DOM hasta el `data-tour`
  más cercano. Guarda ancla + acción + etiqueta + **en qué pantalla estaba**. 🔴 El «dónde» sale
  de un **ref espejo**: un listener no puede leer el estado de React, quedaría congelado en el del
  primer render.
  · **Backend**: `GET/POST /api/tutoriales` y `POST /api/tutoriales/borrar`; se guardan en el
  catálogo (`tutoriales`) y son **compartidos** (un tutorial es para enseñarle a otro).
  · **UI**: botón grabar/parar en el menú de Ayuda, cartel fijo mientras graba (con el contador de
  pasos y un «Parar» a mano), y el modal del nombre.
  🔴 **La decisión de diseño que importa**: el cartel se arma **al REPRODUCIR**, no al grabar. Por
  eso mejorar una explicación del diccionario **mejora todos los tutoriales ya grabados**, sin que
  nadie tenga que regrabar nada.
  **Contrato nuevo `verificar_diccionario.mjs`** (corre en cada `npm run build` y **corta**): que
  ningún `data-tour` quede sin explicación, que no sobren entradas muertas, que cada una esté
  completa y que `explicar()` conserve su fallback. **118/118, 0 avisos.**
  **Verificado**: contrato en verde · build OK · circuito completo por los endpoints reales
  (`scratchpad/e2e_tutoriales.py`: guardar, listar, regrabar sin duplicar, borrar, y los cuatro
  rechazos — sin nombre, sin pasos, paso sin ancla, grabación desbocada) · la app levanta sin
  errores de consola · `/api/tutoriales` pasó a pedirse **al abrir la Ayuda** (al arrancar daba 401
  antes del login).
  ⚠️ **Falta probarlo EN PANTALLA con sesión**: no puedo loguearme, así que el grabador no se
  tocó a mano. Y **falta la ENTREGA 2**: hoy sólo 118 elementos tienen ancla, sobre **374 botones y
  88 campos**. Lo que no tiene ancla **no se graba**; lo que tiene ancla pero no explicación cae al
  texto del botón. Plan: ir pantalla por pantalla poniendo `data-tour` + su entrada, empezando por
  el circuito del pedido.

- **2026-08-27 (316) — VIGILANTE: sin ventanas que aparecen y se van, y vuelve en segundos.** Dos
  quejas del usuario: *«cuando estaba levantado el localhost me abría una ventana y desaparecía»* y
  *«se me volvió a cerrar»*.
  **(1) La ventana**: la tarea ejecutaba `cmd.exe` y, al correr con `InteractiveToken`, Windows le
  abría una consola. 🔴 **`<Hidden>true</Hidden>` NO tapa la consola** — sólo esconde la tarea de
  la lista del Programador. Ahora la acción es `wscript.exe //B //Nologo _vigilante.vbs`, y el
  vigilante lanza el `.bat` con `sh.Run(..., 0, True)`. Verificado: **ningún proceso de la cadena
  tiene ventana** (`python → py → cmd → wscript → svchost`).
  **(2) Los 2 minutos sin sistema**: la tarea sólo revisaba cada 2 min, así que una caída dejaba el
  sistema abajo hasta 2 minutos (pasó: murió 15:08:25, volvió 15:10). Ahora `_vigilante.vbs`
  **espera al servidor** y lo relevanta apenas termina. Medido: **4,7 s**. La repetición de la tarea
  bajó a 1 min y queda sólo como red por si el vigilante también muriera. Freno anti-bucle: 5
  arranques seguidos de menos de 20 s → se rinde y lo anota (si no, con el código roto quemaría la
  máquina).
  🔴 **Y se quitó algo peligroso que yo había puesto**: `_arrancar-oculto.bat` mataba lo que
  estuviera en el 8050 si `/api/salud` no contestaba **en 5 segundos**. Armando una tizada el
  servidor puede tardar más que eso → **el vigilante lo habría matado en plena producción**. Ahora
  no mata a nadie: si algo escucha el 8050, se respeta.
  **`logs/caidas.log`** anota ahora **cuánto duró** cada corrida: es lo que va a dejar ver el patrón
  de por qué se cierra (la caída de las 15:08 no dejó traceback y el servidor estaba ocioso —
  causa aún **sin identificar**).
  **`actualizador.py`**: en Windows `parar()` **pone la bandera `logs/apagado.flag` ANTES** del
  `schtasks /end` y `arrancar()` la saca. Sin eso el vigilante reviviría el servidor por debajo del
  ayudante y la actualización se aplicaría sobre un servidor vivo. Contrato de Linux sigue en verde.
  **Verificado**: sin ventanas · vuelve en 4,7 s · `CERRAR-SERVIDOR.bat` lo apaga y **sigue apagado
  100 s** pese a la tarea (y cierra también el vigilante) · `REINICIAR-SERVIDOR.bat` lo enciende y
  borra la bandera · `/api/salud` ok.

- **2026-08-27 (315) — 🔴 MIS REINICIOS NO REINICIABAN NADA: 2 h 30 de código Python que nunca
  corrió.** El usuario reportaba que «Sin marca» no guardaba. El código estaba bien: **el servidor
  que atendía era de las 12:00:05** y los arreglos eran de las 13:58 / 14:05 / 14:06.
  **La causa**: yo reiniciaba con `schtasks /end` + `schtasks /run`. El `/end` termina la TAREA pero
  **no siempre se lleva al proceso de Python** que cuelga de ella; y `_arrancar-oculto.bat` es
  idempotente a propósito (si el 8050 contesta, no hace nada) → el `/run` no arrancaba nada y el
  servidor VIEJO seguía atendiendo. Yo daba el reinicio por bueno porque **`/api/salud` contestaba
  200** — pero ese 200 lo contestaba el proceso viejo.
  **El daño**: el usuario probó contra el endpoint viejo, que al recibir un cuerpo **sin `marca`**
  (el que manda el botón «Sin marca») le **borraba la marca de proceso** recién puesta. De ahí
  «pongo sin marca, vuelvo y está como si nunca lo hubiese dicho»: era literalmente cierto.
  **El arreglo**: **`REINICIAR-SERVIDOR.bat`** — mata el proceso del puerto ANTES del `/run` y no
  deja la bandera de apagado (esa es de `CERRAR-SERVIDOR.bat`). Verificado: PID nuevo, arrancado
  14:29:12, posterior al `servidor.py` de 14:05:35.
  🔴 **REGLA: el reinicio se verifica por la HORA DE ARRANQUE del proceso, no porque `/api/salud`
  conteste.** `StartTime` del proceso del 8050 tiene que ser POSTERIOR al `LastWriteTime` de
  `servidor.py`. Y la regla general, que vale para todo el sistema: **«el servicio responde» no
  prueba que responda el código nuevo**. Cuando un arreglo «no funciona» y el código se ve bien, lo
  primero es confirmar **qué código está vivo** — antes de tocar una línea más.

- **2026-08-27 (314) — 🔴 QUÉ ES «SIN MARCA» (definición del usuario — la anterior era mía y
  estaba mal).** Sus palabras: *«en la tizada no saldrá ninguna marca ni el diseño, pero en el
  VISOR y en la FICHA TÉCNICA sí lo mostrará y dirá la información de qué va, en qué material y
  qué tamaño»*.
  | | tizada | visor | ficha técnica |
  |---|---|---|---|
  | **sin marca** | **nada**: ni cruz ni diseño | se ve entero | **se lista**: dibujo + material + tamaño |
  Lo que faltaba era **la ficha**: `_procesos_ficha` sólo listaba objetos con proceso, así que un
  «sin marca» **desaparecía del sistema entero** y nadie se enteraba de que ese objeto hay que
  hacerlo aparte. Ahora entra tenga proceso o no.
  **Sin material elegido la ficha lo PIDE, no lo inventa**: sale «Falta indicar en qué material se
  hace» en rojo y negrita. El objeto igual no se imprime, así que alguien tiene que decidirlo.
  El encabezado de la sección se adapta a los tres casos (todos con cruz / mezcla / todos sin
  marca) — verificado generando el PDF real y leyendo su texto.
  **Verificado**: contrato → **60 comprobaciones, 0 fallas**; ida y vuelta por endpoints → verde;
  PDF de ficha generado de verdad con los tres casos y leído con PyMuPDF.
  ⚠️ **Lección**: en dos vueltas seguidas me inventé la semántica de esta feature (primero
  «exige proceso», después «desaparece del todo») en vez de preguntar qué tenía que pasar en CADA
  superficie — tizada, visor y ficha son tres respuestas distintas y el usuario las tenía claras.
  Cuando una feature toca varias salidas, la pregunta es «¿qué pasa en cada una?», no «¿qué hace?».

- **2026-08-27 (313) — 🔴 «SIN MARCA» ES AUTÓNOMO (corrección de un error MÍO).** El usuario:
  «sigue estando ahí el maldito objeto … si presiono en sin marca es sin marca. vuelvo para atrás
  y está como si nunca lo hubiese dicho».
  **Qué había hecho mal**: le puse a «Sin marca» una condición que nadie pidió — *que el objeto
  tuviera antes TPU/Bordado/DTF*. El objeto que el usuario sólo quería hacer desaparecer no tenía
  proceso, así que el botón **rechazaba la orden y no guardaba nada**: de ahí «vuelvo para atrás y
  está como si nunca lo hubiese dicho». Encima el endpoint **borraba el flag al sacar el proceso**,
  lo que borraba la decisión sin avisar.
  **La regla ahora, en sus palabras**: **«Sin marca» = en la tizada NO queda NADA en ese lugar.**
  · con proceso → no va la cruz (el objeto ya no se sublimaba) · **sin proceso → el objeto
  simplemente no se imprime**. Las dos decisiones son INDEPENDIENTES: sacar el proceso ya no toca
  el flag.
  **Dónde se tocó**: `_editables_sin_marca` ya no exige `marca`; el endpoint desacopló los campos;
  el motor suma los «sin marca» a `_marcados_nombres` — 🔴 **sin eso el objeto se queda dentro del
  diseño base y se imprime igual, que era el síntoma** — y el dibujo resuelve las cuatro
  combinaciones con una sola regla (`if (_mk or _sin) and marcas_como_cruz`). La pantalla habilita
  el botón con cualquier objeto elegido.
  **Verificado**: contrato → **54 comprobaciones, 0 fallas** (con el caso «flag sin proceso» y el
  cerrojo de que salga del diseño base); ida y vuelta por los endpoints reales → todo verde,
  incluido «sin marca» sobre un objeto que **nunca** tuvo proceso.
  ⚠️ **Cómo se diagnosticó, que es lo que vale para la próxima**: el log del servidor mostraba
  los `POST /api/productos/editable_marca` **con 200**, o sea que la pantalla llamaba bien y el
  backend guardaba — el problema estaba en que el front **no llegaba a llamar** para esos objetos.
  Y `db.get_doc("catalogo")` mostró que el objeto de la queja no tenía ninguna marca guardada.
  Comparar «lo que se ve» con «lo que está guardado» y «lo que se pidió por HTTP» ubicó el error
  en tres pasos.

- **2026-08-27 (312) — 🔴 BUG REAL: las marcas de proceso NO se aplicaban y el objeto salía
  IMPRESO en la tizada.** Reportado por el usuario con su molde «Camiseta de futbol» / diseño
  «jugador»: asignó TPU y DTF y en la tizada aparecían los dos escudos dibujados, sin ninguna cruz.
  **La causa** (no era la feature nueva de «sin marca»; era de antes y salió a la luz recién ahora,
  porque hasta hoy **ningún arte cargado tenía capas «Editable …»** para probarlo de verdad):
  la config del editable se guarda **por variable** (`{v_bu8p7gy: {escudo: tpu}}`), pero la fila
  del pedido venía con **`variante_clave = None`**. El motor resolvía
  `_emarca.get(variante) or _emarca.get("*")` → los dos fallaban → `{}` → **ninguna marca**.
  Y como el objeto SÍ se saca del diseño base (eso mira todas las variables), se lo volvía a
  dibujar entero: exactamente el síntoma.
  **Diagnosticado con los datos reales del usuario** (sólo lectura): el catálogo tenía la marca
  bien guardada, los nombres del arte (`escudo`, `logo`, `Escudo_Mar_de_Fondo_Fútbol_Club_v2`)
  coincidían exactamente con las claves guardadas, y `trabajos/…/pedido.json` mostró el
  `variante_clave: None` de las 5 filas. Buscarlo en el nombre o en la cruz habría sido perder el
  tiempo: el problema estaba en la RESOLUCIÓN DE LA VARIABLE.
  **El arreglo — un único resolutor `_cfg_var(mapa, variante)`** que usan **las cuatro** config del
  editable (color, marca, sin_marca y transforms/posición; antes cada una lo resolvía a mano y
  todas tenían el mismo agujero). La regla es la misma que ya usaba la ETIQUETA para las filas sin
  variable: fila con variable → esa (o el `"*"` legacy) · fila sin variable y **UNA sola**
  configurada → esa, que es inequívoca · **varias y la fila sin elegir → NO se adivina**, y el
  pedido lo **avisa** (`avisos_pedido`). Elegir una al azar sacaría una prenda mal y bien impresa.
  **Verificado**: con el molde real, `escudo` ahora encuentra su `tpu` con `variante=None`;
  el caso ambiguo sigue devolviendo vacío. Contrato `verificar_marcas_proceso.py` → **51
  comprobaciones, 0 fallas**, e incluye un cerrojo: **el patrón `.get(variante) or` no puede
  aparecer fuera del resolutor** (si alguien lo reintroduce, vuelve el bug). `verificar_cantidad`
  y `verificar_etiqueta_nombre` siguen en verde.
  ⚠️ **Lo que sigue sin probarse**: la cruz DIBUJADA en una tizada real. Se verificó la
  resolución de la marca con los datos del usuario, no el PDF final.

- **2026-08-27 (311) — MARCAS DE PROCESO: la cruz se puede APAGAR («sin marca»).** Pedido del
  usuario: un objeto con TPU/Bordado/DTF puede dejar la cruz de 3 cm **o no dejar nada**.
  🔴 **Son DOS decisiones distintas y por eso van en dos campos**: `marca` (el objeto **no se
  sublima**) y `sin_marca` (**no queda nada en su lugar**). Mezclarlas en un solo valor obligaba a
  tocar todo el circuito de `MARCAS_PROCESO` y hubiera hecho que apagar la cruz volviera a imprimir
  el objeto — justo lo contrario de lo que se pide.
  **Dónde vive**: en el catálogo, junto a `marca`, dentro del mismo objeto (`sin_marca: true`);
  se lee con `_editables_sin_marca()` (espejo exacto de `_editables_marca`, con los tres formatos:
  plano viejo → «*», capa de 1 objeto, capa multi-objeto).
  **Motor**: `generar_pedido(..., editables_sin_marca=)` + `_sin_marca_de()`. El `continue` que saca
  el objeto del dibujo quedó **fuera** del `if` de la cruz: por eso apagar la marca **no** hace que
  el objeto se sublime. Viaja también por `generar_pedido_multi` (`md["editables_sin_marca"]`).
  **Pantalla**: botón **«Sin marca»** dentro del grupo «No se sublima» (con su Ayuda al lado, e
  ícono propio: la cruz tachada). Se habilita sólo si lo seleccionado ya tiene proceso, y se apaga
  tocándolo de nuevo. **No invalida el caché del visor a propósito**: el preview del arte muestra
  el objeto entero en los dos casos (`marcas_como_cruz=False`), así que rehacerlo sería trabajo al
  pedo — ojo, esto es lo contrario de asignar la marca, que **sí** lo invalida.
  **Ficha técnica**: el encabezado ya no afirma que siempre va una cruz (se adapta a todos/algunos/
  ninguno) y cada objeto sin marca dice **«SIN MARCA en la tela»**. Si no, el operario busca en la
  tela una cruz que nadie imprimió.
  **Verificado**: `verificar_marcas_proceso.py` ampliado (38 comprobaciones, 0 fallas) + prueba de
  ida y vuelta por los **endpoints reales** (`scratchpad/e2e_sin_marca.py`, catálogo en memoria y
  doble de `db` que explota): guarda, se lee, el flag no pisa el proceso ni al revés, y **sacar el
  proceso se lleva el flag** (un `sin_marca` huérfano se reactivaría solo al reasignar el proceso).
  ⚠️ **Falta la prueba EN PANTALLA**: ningún arte cargado tiene capas «Editable …», así que el
  botón no se pudo tocar de verdad (misma limitación que arrastran TPU/Bordado/DTF desde 2026-08-26).
  Sí verificado: compila, la app levanta sin errores de consola y los textos están en el build.
  ⚠️ **Trampa de herramienta**: la primera versión del contrato daba FALLA porque buscaba la
  palabra `continue` en el código y la encontraba **en un comentario mío**. Ahora busca la sentencia
  (`^\s*continue\s*$`) y compara su indentación con la del dibujo de la cruz.

- **2026-08-27 (310) — 🔴 «SE ME CAE SOLO»: el servidor del TALLER colgaba del programa que lo
  arrancaba. RESUELTO con la tarea de Windows.**
  **El síntoma**: el sistema se caía cada media hora y el `logs/servidor.log` **cortaba en seco, sin
  una sola línea de error**. No había evento en el Visor de eventos ni «Application Error» de Python.
  **La causa** (confirmada mirando la cadena de padres del proceso): un servidor lanzado desde una
  consola es HIJO de esa consola. Windows agrupa el árbol y, cuando el que lo lanzó se cierra, se
  lleva puesto TODO — con `TerminateProcess`, que no deja traza ni excepción. La cadena era
  `python → py → cmd → wscript → powershell → **claude.exe**`. O sea: **el sistema se apagaba
  cuando se cerraba la terminal desde la que yo lo arrancaba.** No era el código, ni SQL Server, ni
  la memoria. Buscarlo en el código era buscarlo donde no estaba.
  **El arreglo**: `INSTALAR-ARRANQUE-AUTOMATICO.bat` registra la tarea de Windows **«TIZADA PRO»**
  (`_instalar-tarea.ps1`) — la misma protección que `instalar_servidor.py` le ponía al servidor
  PUBLICADO y que al del taller nunca se le había puesto. Ahora la cadena termina en **svchost
  (Programador de tareas)**: el servidor no cuelga de nadie. La tarea además arranca al iniciar
  sesión, **se revisa cada 2 minutos** y lo levanta si se cayó, no tiene límite de tiempo (si no,
  Windows lo mata a los 3 días) y es oculta.
  **Piezas**: `_arrancar-oculto.bat` pasó a ser **idempotente** (si `/api/salud` contesta no hace
  nada → nunca dos servidores; si el puerto está tomado pero no contesta, lo saca); guarda el log
  anterior como `logs/servidor.anterior.log` (antes se pisaba en cada arranque y no se podía
  investigar la caída) y anota cada final en **`logs/caidas.log`**, que es lo que distingue «se
  cayó» de «lo apagaron». `CERRAR-SERVIDOR.bat` deja `logs/apagado.flag` para que el vigilante NO
  lo reviva (sin eso no habría forma de apagarlo); la bandera **caduca a los 15 minutos**, así que
  una bandera colgada no deja el sistema muerto. `INICIAR-SIN-VENTANA.vbs` ahora arranca **por la
  tarea** (`schtasks /run`) y sólo cae al arranque directo si la tarea no está.
  **Verificado de verdad**: matado a mano → **volvió solo en 48 s**; apagado con
  `CERRAR-SERVIDOR.bat` → siguió apagado 2:30 pese al vigilante; encendido de nuevo → arriba y con
  la bandera borrada; cadena de padres sin `claude.exe`; `/api/salud` ok, 0 fallas.
  🔴 **REGLA para mí: para reiniciar el server NUNCA más lanzar `py servidor.py` desde la
  terminal** — eso reintroduce el bug. Va **`schtasks /end /tn "TIZADA PRO"` y después
  `schtasks /run /tn "TIZADA PRO"`**, y verificar `/api/salud`.
  ⚠️ **Trampas de herramienta que costaron dos vueltas** (para no repetirlas):
  • Los `.bat` van en **ASCII puro y CRLF**. `cmd` los lee con la página de códigos OEM: los
  caracteres de caja y los acentos le parten la línea y termina ejecutando basura
  (`"pagado.flag)" no se reconoce como un comando`). Los `.bat` que funcionan en este repo son ASCII.
  • En Python, escribir la ruta `logspagado.flag` sin `r""` convierte `` en **BEL (0x07)**: la
  ruta queda rota y no se ve a simple vista. Y «arreglarlo» con `replace` por heredoc **vuelve a
  colapsar a BEL** — hubo que usar `bytes([92, 97])`.
  • En PowerShell 5.1, **`2>&1` sobre `schtasks`** convierte cada línea de error en excepción: con
  `ErrorActionPreference=Stop` el instalador moría en el `/delete`, que **falla a propósito** la
  primera vez.
  • `timeout /t` falla con «No es compatible la redirección de entradas» si la entrada no es una
  consola → `ping -n 4 127.0.0.1 >nul`.
  **Limitación honesta**: la tarea corre con `InteractiveToken` (como el usuario, sin guardar
  contraseña, para conservar sus permisos de Windows sobre MSSQL) → **arranca al iniciar sesión**,
  no con la máquina prendida sin nadie logueado. Para el taller es lo correcto.

- **2026-08-27 (309) — LINUX SE ACTUALIZA SOLO SIN PEDIR ROOT (modo «reinicio»); los dos modos
  conviven.** El usuario vio el cartel «este servidor no puede instalarse solo (KillMode=mixed…)» y
  pidió que el sistema lo resuelva: «que funcione y que convivan los dos».
  **La idea**: el problema era el `systemctl stop` que pedía el ayudante — el que lo mataba a él
  mismo. Pero el unit ya tiene **`Restart=always`**, así que no hace falta parar nada: se
  **descomprime con el servidor todavía vivo** (Python ya tiene sus módulos en memoria: reemplazar
  los `.py` no lo tumba) y, cuando el servidor se apaga solo —como venía haciendo—, **systemd lo
  levanta con la versión nueva**. Sin `systemctl stop`, el `KillMode` deja de importar y **no hace
  falta root ni el drop-in**.
  **Cómo se elige** (`actualizaciones.como_se_instala()`, reemplaza a `puede_instalarse_solo`, que
  queda como compatibilidad): `Restart=always|on-failure|on-abnormal` → **`reinicio`** ·
  `KillMode=process` → **`systemd`** (el clásico) · ninguno → **None**, y ahí sí queda para aplicar
  a mano. El modo viaja al ayudante como quinto argumento; sin él, `actualizador.py` asume el
  clásico (un ayudante lanzado por una versión vieja sigue funcionando). En `main()` la rama
  «reinicio» **no llama a `parar()`** y descomprime ANTES de esperar el apagado — al revés no
  serviría: systemd revivía el código viejo. Mantiene respaldo y vuelta atrás.
  **El estado que ve la pantalla** ahora informa `modo_instalacion`.
  **Contrato `verificar_actualizador_linux.py` ampliado**: exige que exista la rama «reinicio», que
  NO pare el servicio, que descomprima antes de esperar, que tenga rollback, que el modo clásico
  siga parando primero, y que la decisión mire `Restart` de verdad.
  **Verificado** simulando las cinco configuraciones posibles del unit: el **VPS de hoy**
  (`Restart=always`, `KillMode=mixed`) → **modo reinicio**, o sea que **ya puede actualizarse solo
  sin tocar nada**; con el drop-in → clásico; sin ninguno de los dos → a mano, diciendo qué falta.
  `DESPLIEGUE.md` §11.b actualizado: el drop-in pasó de obligatorio a opcional.

- **2026-08-27 (308) — Arrancar el sistema SIN VENTANA (`INICIAR-SIN-VENTANA.vbs`).** «Se me cerró la
  ventana» — y con razón: la consola negra **ERA** el servidor, así que cerrarla lo apagaba. Ahora hay
  tres piezas: **`INICIAR-SIN-VENTANA.vbs`** (doble clic → cierra lo que hubiera en el 8050, arranca
  el servidor **oculto**, espera hasta 20 s a que `/api/salud` conteste y avisa con un cartelito que
  se va solo; si no levanta, dice dónde mirar), **`_arrancar-oculto.bat`** (el arranque en sí, sin
  `pause`, con todo el registro a `logs\servidor.log`) y **`CERRAR-SERVIDOR.bat`** para apagarlo —
  hace falta justamente porque ya no hay ventana que cerrar. `iniciar.bat` queda como estaba, para
  cuando se quiere ver la consola.
  ⚠️ **Trampa**: la primera versión adivinaba el intérprete desde el VBS
  (`If Not fso.FileExists("C:\Windows\py.exe") Then py = "python"`) y terminó llamando al **alias
  de la Microsoft Store** → `logs\servidor.log`: «no se encontró Python». El arranque usa ahora el
  MISMO criterio que `iniciar.bat` (`where py` y si no `python`), en el .bat.
  **Verificado**: lanzado como lo va a hacer el usuario (doble clic en el .vbs) → `/api/salud`
  **200, ok: true, 0 fallas**, el registro escribiéndose en `logs\servidor.log` y **ninguna consola
  con ventana visible**. `logs/` agregado al `.gitignore`.

- **2026-08-26 (307) — ARTE POR RANGO: la ficha muestra la medida de CADA rango.** Corrección del
  usuario a la 306: su diseño tiene **un arte por rango**, y ahí cada mesa puede traer el objeto con
  otra medida — hay que mostrarlas **todas**, diciendo qué talles abarca cada una. La medida del
  **talle guía** es sólo para el modo *default* o para un arte *por talle* (una sola mesa).
  `_procesos_ficha` ahora recibe el **registro** y usa `MP.mapeo_variantes_arte` para invertir
  `{pieza: {talle: mesa}}` → `{mesa: [talles]}`; agrupa las mesas del objeto **por medida** y arma
  una línea por tramo, ordenando los talles como el molde (`_orden_var`) para poder decir «XS a S».
  Prioridad final: **tamaño configurado** > **rangos del arte** > **talle guía**.
  **Verificado** (contrato ampliado, 26 comprobaciones): con 3 mesas (XS-S · M-L · XL-2XL) sale
  **un solo renglón** con `XS a S → 6.5 cm`, `M a L → 7.5 cm`, `XL a 2XL → 8.5 cm`; con una sola
  mesa, `talle M → 7.5 cm`; y con tamaño configurado manda la config (`XS a M → 8.0`, `L a 2XL →
  10.0`). Server reiniciado tras tocar Python: `/api/salud` **ok: true, 0 fallas**.
- **2026-08-26 (306) — La ficha lista cada objeto UNA vez, con la medida que corresponde.** El
  usuario vio el mismo «escudo» **cuatro veces** (7,5 · 7,5 · 7,5 · 6,5 cm): `extraer_editables`
  devuelve el objeto **una vez por MESA del arte** —una por rango de talles— y la ficha los listaba
  todos. Ahora `_procesos_ficha` **agrupa por nombre** y resuelve las medidas así:
  · **con tamaño configurado por rangos** (`editables_config`) → **una línea por rango**, diciendo
    qué talles abarca: «XS a M · 8,0 × 8,0 cm» / «L a 2XL · 10,0 × 10,0 cm». Es la medida que la
    tizada va a respetar, así que es la que hay que mostrar.
  · **sin configurar** (default o talle por talle) → la medida que el objeto tiene **en el TALLE
    GUÍA**, y si el arte lo trae en varias medidas se aclara con una nota.
  El bloque de la ficha **crece** si el objeto tiene varios rangos (antes era de alto fijo).
  ⚠️ En `servidor.py` **`_norm_nombre` no existe suelto**: es `MP._norm_nombre` (se coló en la
  primera versión y habría explotado al generar la ficha).
  **Verificado** con una ficha REAL generada y leída de vuelta: «escudo» aparece **1 vez**, con sus
  dos rangos; el de una sola medida sale con «talle M» y su nota. Server reiniciado tras tocar
  Python — `/api/salud` **ok: true, 0 fallas** (regla del usuario).

- **2026-08-26 (305) — Marcas de proceso, segunda vuelta: cruz gruesa, letra adentro y la ficha
  muestra el objeto.** Correcciones del usuario sobre la 304:
  **(a) La cruz**, mucho más gruesa: `CRUZ_TRAZO_MM` **0,35 → 1,6 mm** (tiene que verse de lejos en
  la mesa), con puntas rectas (`0 J`).
  **(b) La letra va DENTRO de un cuadrante**, no al costado: se centra en el punto medio entre el
  cruce y la punta de los brazos de arriba-derecha (`CRUZ_LETRA_MM = 7`), así toda la marca entra en
  los 3 cm y el cruce —el punto exacto donde va el objeto— queda libre.
  **(c) La FICHA vuelve a mostrar el objeto en el molde**: `_molde_guia_ficha` genera con
  **`marcas_como_cruz=False`** — la cruz es para la TELA; en la ficha el molde tiene que verse con
  su diseño completo.
  **(d) La lista de abajo ya no muestra letras**: por cada objeto va **su DIBUJO** (el SVG del arte;
  si no se puede convertir, la miniatura PNG) en una caja de 54×48, y al lado el nombre, **«Se hace
  en: TPU/Bordado/DTF»**, la medida y sobre qué pieza. `_procesos_ficha` ahora devuelve `svg` y
  `thumb` en vez de la letra.
  **Verificado** (contrato, 22 comprobaciones en verde): trazo **1,6 mm**, y con una fuente real los
  **9 puntos** del trazado de la letra caen **dentro del cuadrante** y ninguno se sale de los 3 cm.
  ⚠️ Sigue sin poderse probar en pantalla (ningún arte cargado tiene capas «Editable …»).
  🔁 **Regla nueva del usuario**: «cada vez que toques python termina y inicia todo **pero el sistema
  debe de estar funcionando bien**» → tras esta tanda: server reiniciado y `/api/salud` con
  **ok: true, 0 fallas**, base respondiendo y frontend al día. Ver [[reiniciar-server-python]].

- **2026-08-26 (304) — MARCAS DE PROCESO: TPU · Bordado · DTF (lo que NO se sublima).** Pedido del
  usuario: en el editor, tres botones arriba; se eligen uno o varios objetos editables y se les
  asigna un proceso. Ese objeto **no se imprime**: en la tizada, en su lugar, va una **cruz de 3 cm**
  centrada donde estaba, y en la ficha técnica se lista qué hay que aplicar ahí.
  **Decisiones del usuario**: cruz de **3 cm punta a punta**, línea fina · **las tres en negro** con
  la **letra** al lado (T/B/D) en vez de tres colores (podían confundirse con el diseño) · se quita
  **tocando el mismo botón** otra vez · en la ficha van **dibujo/letra + nombre + medida + en qué
  pieza**.
  **Motor** (`motor_pedido.py`): `MARCAS_PROCESO`, `CRUZ_MM=30`, `_ops_cruz_proceso` (cruz negro puro
  `0 0 0 1 K` + la letra en curvas) y **`_centro_editable`**, que devuelve el mismo punto que usa
  `_matriz_editable` como pivote — así la cruz cae exactamente donde quedó el objeto, movido o no.
  `generar_pedido(..., editables_marca, marcas_como_cruz=True)`: el marcado entra en
  `_redibujar_nombres` (se saca del diseño base, como un recoloreado) y **no se vuelve a dibujar**.
  🔴 **`marcas_como_cruz=False` en el preview del arte**: es la **única excepción consciente** a la
  ley «el arte se ve igual que la tizada», y es a pedido del usuario — el diseñador tiene que seguir
  viendo el objeto entero. La marca **sí** entra en la clave del caché (`_piezas_base_clave` **v13**):
  aunque el dibujo no cambie, cambia lo que se saca del diseño base.
  **Servidor**: `_editables_marca` (espejo de `_editables_color`, lee los 3 formatos guardados),
  `POST /api/productos/editable_marca` (asigna/quita, por variable y por objeto),
  `GET /api/productos/editables_marcas`, y la marca viaja en los tres caminos de generación
  (preview, generar y `generar_multi`).
  **Front**: tres íconos nuevos (`tpu` plancha · `bordado` aguja · `dtf` película) y la barra
  **«No se sublima»** arriba del editor, que se enciende cuando TODOS los objetos elegidos tienen ese
  proceso; al asignar se invalida la caché del visor.
  **Ficha técnica**: `_procesos_ficha` + sección **«NO SE SUBLIMA · se aplica aparte»** debajo de las
  piezas de cada diseño, con la letra de la cruz, el nombre, el proceso, la medida y la pieza.
  **Contrato `verificar_marcas_proceso.py`** (18 comprobaciones, verde): la cruz mide **30,00 mm** en
  los dos brazos, es negro puro, la línea 0,35 mm, cada opción con su letra; una marca desconocida
  no dibuja nada; la marca se lee en los **tres formatos** (plano viejo → «*», capa de 1 objeto, y
  **por figura** en capas multi-objeto); y el centro sigue al objeto cuando se lo mueve.
  ⚠️ **Lo que NO se pudo probar en pantalla**: los tres botones. Ninguno de los artes cargados tiene
  capas «Editable …», así que el botón «Editar diseño» no aparece y el editor no se puede abrir en el
  sandbox. Falta probarlo con un arte que traiga editables.

- **2026-08-26 (303) — El REBOTE al soltar las filas.** «¿Por qué hace un efecto de retroceso cuando
  suelto si ya están acomodadas?» — dos causas, las dos del ciclo de React:
  1. En `onUp` se llamaba a `setFilasSel` **dentro del updater** de `setFilas`. Eso corre en plena
     fase de render y provoca un **render intermedio** con las filas todavía viejas y los
     desplazamientos ya en cero: por un instante se veían volver a su lugar original. Ahora el
     reordenamiento se calcula **antes** y los `setState` se aplican de una (`filas`, `filasSel`,
     `dragFilas`), sin nada anidado.
  2. Las `key` de las filas son el **índice**, así que al reordenar React **reutiliza el mismo
     `<tr>`** para otra fila: el navegador veía pasar su `translateY` de 99 px a 0 y lo **animaba**.
     Se agregó `soltandoFilas`: el frame en que se suelta va con `transition: 'none'` (60 ms) y
     después todo vuelve a la normalidad.
  **Verificado** midiendo **un frame después** de soltar (16 ms), que es donde se veía el rebote:
  las filas ya están en el orden final, **0 con `transform`** y **0 con transición activa** —
  todas en `transition: none`.

- **2026-08-26 (302) — Arrastre de filas: queda el PRIMER efecto (la fila real se mueve) + números en
  vivo.** Tercera vuelta sobre lo mismo, con la aclaración del usuario: *«cuando arrastrás no deja
  las filas como ocultas, arrastra las filas reales en tiempo real; ves cómo se va arrastrando la
  fila pero va cambiando su ítem»*. Se **eliminó el hueco punteado** (entradas 300-301) y volvió el
  efecto de la entrada 299: la fila **se ve y viaja** con el cursor (`translateY`, fondo de acento y
  sombra) y las demás se corren para dejarle lugar; **cero bordes punteados**. Se conserva lo único
  que se agregó después y sí quedó: **`numeroFila(i)`**, la numeración que se recalcula en vivo.
  Como las filas vuelven a moverse con `transform`, el destino se calcula otra vez con las
  posiciones **congeladas** del arranque (`tops`) — preguntarle al DOM daría la posición ya
  desplazada y el destino se perseguiría a sí mismo. Se sacaron el FLIP y `numerosDelHueco`, que
  eran del hueco.
  **Verificado en la UI**: arrastrando la 1ª al lugar 4 → la fila M queda **visible** (`oculta:
  false`) con `translateY(99px)` y su número ya dice **04**, mientras L/S/XL se corren `-33px` y
  pasan a **01/02/03** en vivo, XS queda en 05; **0 elementos punteados**; al soltar,
  `01:L 02:S 03:XL 04:M 05:XS`.
  📌 Historial de esta feature, para no volver a girar en círculos: **299** filas que se mueven →
  **300** hueco punteado (rechazado: «efecto horrible») → **301** hueco + FLIP + números →
  **302 (esto)** vuelta al 299 **con** los números. Lo que el usuario quiere es: **la fila real
  moviéndose y su número cambiando**.

- **2026-08-26 (301) — Arrastre de filas: números EN VIVO, el deslizamiento de vuelta y soltar la
  selección al tocar afuera.** Tres pedidos del usuario sobre la entrada 300.
  **(a) Números en vivo**: `numeroFila(i)` calcula el número que le VA A TOCAR a cada fila cuando se
  suelte, y el hueco muestra el suyo (`04` o `04-06` si viajan varias). Verificado: arrastrando la
  1ª al lugar 4, durante el gesto se ve `01:L · 02:S · 03:XL · [HUECO 04] · 05:XS` y al soltar queda
  exactamente así.
  **(b) Vuelve el movimiento**, pero sin el «va y viene»: el hueco se queda (entrada 300) y las filas
  **se deslizan** a su nuevo lugar con **FLIP** (`useLayoutEffect` mide dónde estaba cada fila, la
  devuelve con un `transform` y la suelta con transición de .18 s). ⚠️ `requestAnimationFrame` **no
  corre con la pestaña en segundo plano** — sin un `setTimeout` de respaldo, una fila podía quedarse
  desplazada para siempre. Verificado: **5 filas animándose** durante el gesto y **0 corridas** al
  terminar.
  **(c) Tocar en otro lado suelta la selección** (celda, fondo, lo que sea) salvo con shift/ctrl o
  sobre la propia columna del número (`data-numfila`). Verificado paso a paso: clic simple → 1 ·
  shift → 3 · tocar una celda → 0 · elegir otra → 1 · tocar el fondo → 0.
  🔴 **Dos bugs de carrera encontrados al verificar** (los dos por el orden de los eventos):
  1. El `onClick` del número se salteaba si `dragFilas` seguía activo — y el `mousedown` lo activa
     SIEMPRE. Ahora el clic se ignora sólo si hubo arrastre de verdad (`clickTrasDrag`).
  2. Los listeners del gesto se montaban en un `useEffect`, o sea **un render tarde**: un clic corto
     (soltar antes de ese render) no encontraba su `mouseup`, el gesto quedaba abierto y la tabla
     seguía «arrastrando» sin ningún botón apretado. Ahora se enganchan **dentro del propio
     `mousedown`** y se sueltan en el `mouseup`.
  🔧 **Y una lección de entorno**: el server 8050 se cayó cuatro veces. No era el código ni la base
  (SQL Server estuvo `RUNNING` y el log terminaba **sin una sola excepción**): **el entorno mata todo
  proceso que nace de un comando mío** al terminar ese comando — con `run_in_background`, con
  `Start-Process` y hasta creándolo por WMI. Lo que SÍ funciona: lanzarlo desde el **Programador de
  tareas** (`schtasks /create` + `/run`, y después `/delete` para no dejar nada puesto), que lo
  ejecuta el servicio de tareas, fuera de mi árbol. Verificado: sobrevive a varios comandos
  seguidos. Ver [[reiniciar-server-python]].

- **2026-08-26 (300) — El arrastre de filas ahora ABRE UN HUECO (y el toggle responde en el
  interruptor).** Dos correcciones del usuario sobre lo de la entrada 299.
  **(a) «El botón funciona sólo en las letras»**: el `Switch` de *Columna cantidad* traía su propio
  `onClick` y estaba dentro de una fila que también lo tenía → tocar el interruptor disparaba el
  toggle **dos veces** y volvía al estado anterior; tocando el texto, una sola vez. Ahora el switch
  va con `pointerEvents: none` y **el click lo maneja la fila entera**. Verificado: tocando el
  interruptor la columna aparece/desaparece, y tocando el texto también.
  **(b) «El efecto va y viene»**: la primera versión movía TODAS las filas con `translateY` — se veía
  como un baile. Se reemplazó por lo que pidió: **la fila sale de su lugar** (`display: none`) y en el
  destino aparece un **HUECO EN BLANCO** del alto de lo que se está moviendo (borde punteado en el
  acento), que se va corriendo con el cursor. **Ninguna fila se transforma**: cero movimiento
  lateral, sólo el espacio que se abre. Además el punto de inserción se calcula con las **posiciones
  del DOM de ahora** (filas visibles, sin las que viajan): como el hueco ocupa lugar, mover el cursor
  dentro del hueco no cambia nada — con las posiciones congeladas del arranque, parpadeaba.
  **Verificado**: (1) arrastrando 1 fila → durante el gesto `(fuera) · L · S · XL · XS · [HUECO]`,
  **0 filas con transform**, y al soltar `L S XL XS M`; (2) con **2 filas** elegidas por shift → las
  dos `(fuera)`, un hueco de **67 px** (2 × 33 + margen) arriba de todo, y al soltar `XS M L S XL`
  — juntas y en orden.

- **2026-08-26 (299) — Reordenar filas ARRASTRANDO desde la columna «#», con la animación en vivo.**
  Se toca el número para elegir una fila (**shift** = rango, **ctrl/cmd** = de a una) y se arrastra
  para moverla; mientras se arrastra, **las filas se corren en tiempo real** para abrir el hueco
  donde van a caer. El **número del ítem no viaja con la fila**: se pinta por posición (`i + 1`), así
  que siempre queda 1, 2, 3… de arriba abajo.
  **Cómo está hecho**: `filasSel` (Set de índices) + `dragFilas` = `{sel, destino, alto, tops}`.
  Las posiciones (`tops`) se capturan **al empezar** el gesto: el punto de inserción se calcula
  contra ellas y no contra el DOM, que en ese momento se está moviendo por la propia animación.
  `desplazoFila(i)` devuelve cuánto se corre cada fila —el bloque arrastrado hacia su destino, el
  resto abriendo el hueco— y eso va a un `translateY` con `transition` de .16 s **sólo mientras dura
  el arrastre**: al soltar, el array ya está reordenado y una transición ahí haría un salto. El
  gesto vive en el **documento** (mousemove/mouseup), así que sigue aunque el mouse se salga de la
  tabla; al terminar se limpia la selección de CELDAS (`plSel`), que apuntaba a los índices viejos.
  ⚠️ **Bug encontrado al verificarlo**: `empezarDragFilas` reseteaba la selección a la fila tocada, y
  como el **`mousedown` corre ANTES que el `click`**, el shift+click perdía lo elegido y se arrastraba
  una sola fila. Ahora el arranque **no toca la selección** (y con shift/ctrl ni siquiera arranca:
  eso es elegir, no arrastrar); la selección se actualiza al soltar, siguiendo al bloque movido.
  **Verificado en la UI** con 5 filas `M L S XL XS`: (1) arrastrando la 1ª a la 4ª posición →
  `L S XL M XS`, con `translateY(99px)` en la que viaja y `-33px` en las tres que se corren;
  (2) eligiendo dos con shift y llevándolas al final → **2 filas marcadas**, las dos con
  `translateY(99px)` y el resto `-66px`, resultado `S XL XS M L` — viajaron **juntas y en orden**;
  (3) en los dos casos los números quedaron **01…05**.
  ⚠️ Trampa de la verificación: entre el `mousedown` sintético y el primer `mousemove` hay que
  **esperar un tick** — el listener de documento lo monta un `useEffect`, que corre después del
  render; sin esa espera el movimiento se pierde y parece que la feature no anda.

- **2026-08-26 (298) — El lote aprovecha las filas vacías, y el filtro de los desplegables ordena por
  el principio de la palabra.** Dos pedidos del usuario.
  **(a) Cargar por lote** dejaba los renglones en blanco arriba y ponía lo suyo abajo. Ahora
  **rellena primero las filas vacías** que ya están —en su lugar, sin moverlas— y sólo agrega al
  final lo que no entró (`filaVacia` por fila; los toggles no cuentan como «cargado» porque nacen
  con una opción puesta). El modal lo dice antes de confirmar: «7 prendas · 5 en las 5 filas vacías
  · 2 al final». **Verificado**: planilla recién abierta (5 vacías) + `M=3`, `L=4` ⇒ **7 filas**
  `M M M L L L L`, **ninguna en blanco**.
  **(b) El filtro de los desplegables** usaba `includes` pelado: escribiendo **«L»** la lista abría
  con `XL`, `2XL`… y la **L** quedaba perdida en el medio. Ahora se ordena en tres tramos —
  **exacta → empieza con → contiene** — sin perder la búsqueda por dentro. **Verificado** con los 30
  talles del molde: «L» → `L · Lfem · XLfem · 2XLfem … XL · 2XL`; «S» → `S · Sfem · XSfem · XS`;
  y «fem» sigue encontrando las 10 (ninguna empieza así, caen en el tercer tramo).
  ℹ️ Nota de sesión: el server 8050 se había caído (el proceso de fondo terminó con código 127 por
  quedar lanzado desde `frontend/`); se relanzó **desde la raíz del repo** y quedó en verde
  (`ok: true`, base OK, 26 tablas). **Lanzar `py servidor.py` siempre desde la raíz.**

- **2026-08-26 (297) — Fuera el spinner de las casillas de número (en TODA la app).** El usuario
  mandó el recorte de las flechitas ▲▼ del navegador: un `input[type=number]` las dibuja de fábrica
  **con su propio fondo claro**, y dentro de una interfaz oscura se ve como un parche pegado. Se
  ocultan de una vez en `index.css` (`::-webkit-inner/outer-spin-button { appearance: none }` +
  `input[type=number] { appearance: textfield }` para Firefox), así que vale para los **13**
  `input[type=number]` del sistema, no sólo el de «Agregar filas»: la casilla queda con el fondo que
  le pone la app y el número centrado. Donde hace falta subir/bajar de a uno ya hay botones propios
  (los ± del «Cargar por lote», el menú de `NumeroConMenu`). **Verificado en la UI**: las dos reglas
  viajan en el CSS compilado y el `appearance` computado del input es `textfield`.

- **2026-08-26 (296) — La planilla, CENTRADA; y el modal del lote, POR GRUPOS.** Dos cosas que marcó
  el usuario mirando la pantalla.
  **(a) «La planilla sigue hacia un lado y queda feo»**: desde que la tabla mide `max-content`
  (entrada 293) quedaba pegada a la izquierda de una tarjeta que ocupaba todo el ancho, con medio
  panel vacío al lado. Ahora **la tarjeta acompaña al contenido** (`width: max-content`,
  `minWidth: min(100%, 780px)` para que el título no se apriete) y va **centrada**, igual que el
  marco de la tabla adentro. Medido a 1440 px: tarjeta de 918, con **233 px de aire a cada lado**, y
  la tabla con **54 a cada lado** dentro de la tarjeta. El aire quedó afuera y repartido, no adentro
  y de un solo lado.
  **(b) El modal «Cargar por lote» era una pared de 30 casilleros** con los nombres **cortados**
  («1..», «X.», «S.»): no se sabía cuál era cuál. Ahora se separa en **grupos** con encabezado y
  subtotal — `_grupoTalle` mira lo que queda DESPUÉS del talle en sí (`6XLfem` → sufijo «fem»), y los
  puramente numéricos van aparte; si un molde no usa sufijos queda **un solo grupo** y se ve como
  antes. Celdas de 178 px y el nombre **sin recorte** (`nowrap`, sin ellipsis); el modal pasó a
  760 px; los ± miden 26 y el número se pinta en el acento cuando hay carga.
  **Verificado** con el molde de 30 talles: **0 nombres cortados**, tres grupos —**NUMÉRICOS ·
  FEM · ADULTO**— y, cargando `10 = 2`, `Mfem = 3` y `M = 5`, cada encabezado muestra su subtotal
  («Numéricos 2 prendas · Fem 3 · Adulto 5») y el total dice **«Se van a cargar 10 fila(s)»**.

- **2026-08-26 (295) — El paso PLANILLA, reacomodado (barra de herramientas arriba).** El usuario
  mandó una captura: «que no se sienta como sistema trucho». Lo que estaba mal, punto por punto:
  el toggle de Cantidad era un **botón enorme** con un párrafo suelto al lado; las acciones vivían
  **abajo** de la tabla, todas del mismo peso visual y con **flechitas de texto** («⬆ ⬇») en lugar de
  íconos; el contador quedaba perdido a la derecha; y el título decía «3 ·» cuando la barra de pasos
  marca **4**.
  **Cómo quedó**: una **barra de herramientas ARRIBA de la tabla**, en una sola línea y agrupada por
  lo que hace cada cosa, con separadores finos entre grupos —
  **[+ Agregar fila |n|] [Cargar por lote]** │ **[Importar] [Exportar]** │ **[⏻ Columna cantidad + ?]**
  │ …y a la derecha las **pastillas** `N filas` / `M prendas` (la segunda sólo cuando difieren).
  Todos los controles miden **exactamente 36 px** de alto — con alturas distintas la fila se ve
  desprolija, que era buena parte de la sensación de «trucho». El toggle pasó a `Switch` + un «?»
  con el ejemplo (regla del proyecto: control corto, explicación en la ayuda de al lado), y los
  íconos son SVG del set (`plus`, `planilla`, `upload`, `download`).
  ⚠️ **Trampa al hacerlo**: al sacar el bloque de botones de abajo quedó un `</div>` de más y el
  build tiró «Expected ")" but found "{"» apuntando 40 líneas más abajo. Se ubicó comparando la
  estructura con `git show HEAD:frontend/src/App.jsx`. Y **medir con el tab en segundo plano da
  `window.innerWidth = 0`** (todo apilado y la card en 32 px): hay que fijar el viewport con
  `resize_window` antes de sacar conclusiones de una medición.
  **Verificado en la UI** (1440 px): los 5 controles en la **misma línea** (top 243) y **todos de
  36 px**, la barra por encima de la tabla, y la guía en verde.

- **2026-08-26 (294) — «CARGAR POR LOTE»: cuántas prendas de cada talle → una fila por prenda.** Un
  botón en la planilla abre un modal con **todos los talles del molde** (`estado.talles`), cada uno
  con − / número / +; al confirmar crea **UNA FILA POR PRENDA**: M = 5 ⇒ 5 filas de M, cada una lista
  para su nombre y su número.
  🔴 **No confundir con la columna Cantidad** (entrada 291): esa hace **1 fila = N prendas iguales**;
  el lote arma **N filas separadas**, que es lo que sirve cuando cada prenda lleva un nombre distinto.
  Detalle de comportamiento: si la planilla está **en blanco** (todas las celdas vacías; los toggles
  no cuentan, que nacen con un valor puesto) el lote la **reemplaza** — si no, **agrega al final**, y
  el modal lo dice antes de confirmar. El talle se escribe en la primera columna con `role: 'talle'`
  que esté visible; el resto de la fila sale de `_defaultRow()`.
  **Verificado en la UI** (sandbox 8060, molde de 30 talles): el modal lista los **30**; poniendo
  **M = 5** y **L = 2** el resumen dice «Se van a cargar 7 fila(s)» y quedan `M M M M M L L`
  (7 filas, reemplazando las vacías); con datos ya cargados, **S = 3** avisa «Se van a **agregar** 3
  fila(s) al final de las 7 que ya hay» y el resultado es `M M M M M L L S S S` (10).

- **2026-08-26 (293) — Columnas de la planilla con ANCHO INTELIGENTE.** Pedido del usuario: las
  numéricas **finas** (que entren 5 números) y que **crezcan si el texto las supera**; vacías, un
  ancho predeterminado. **El problema**: la tabla era `width: 100%` **sin anchos**, así que el
  navegador repartía el sobrante entre todas — una columna de números terminaba midiendo **219 px**.
  **Cómo se resolvió**: `ANCHO_COL` (memo) calcula el ancho de cada columna visible **midiendo el
  texto de verdad** con un canvas 2D y la MISMA tipografía de la celda (monoespaciada en los
  números, 600 en el nombre, que además va en mayúsculas) — contar caracteres erraba por el doble
  entre «MMMM» y «iiii». Se toma el máximo entre el **encabezado**, el **valor más largo** de las
  filas y, en los toggles, **la suma de sus opciones** (tienen que entrar aunque nadie las haya
  elegido); después se aplica el **piso** (numérica = 5 dígitos; desplegable 96; nombre 130; texto
  110 — eso es lo que se ve con la planilla vacía) y un techo de 280 px para que una sola columna no
  se coma la pantalla. Los anchos van en un **`<colgroup>`**.
  ⚠️ **Corrección en el mismo día**: la primera versión resolvía el sobrante con una **columna de
  relleno**, y el usuario la vio enseguida — quedaba «una columna vacía» con el fondo y las líneas
  de las filas hasta el borde. Se sacó: ahora la **tabla mide `max-content`** (termina donde
  terminan sus columnas) y el **marco** también (`max-content` + `maxWidth: 100%`), así a la derecha
  se ve el fondo del panel y nada más. Con la pantalla angosta el marco se limita al ancho
  disponible y la tabla **scrollea adentro**, como antes.
  **Verificado en la UI**: vacía → Número **76 px** y Cantidad 87 (el encabezado manda), Nombre 152;
  al importar «MAXIMILIANO DE LA CRUZ» y `99999999`, Nombre pasó a **192** y Número a **79**, y la
  columna sobrante se achicó sola (384 → 341). **Ningún texto queda cortado**: el ancho medido da
  191/192, 78/79 y 86/87 contra lo que cada celda necesita.

- **2026-08-26 (292) — El botón de Cantidad sube arriba de la planilla + EXPORTAR CSV.** Pedido del
  usuario: el botón de cantidad **arriba de la planilla**, más llamativo y que diga **«Mostrar
  columna de cantidad»**; y **al lado de Importar, un Exportar** que baje una planilla de Excel que
  después se pueda volver a subir por Importar, **con las columnas VISIBLES** (o sea: Cantidad se
  exporta sólo si se está viendo).
  **Botón**: salió de la barra de abajo y quedó **arriba de la tabla**, 44 px de alto, en el acento
  del sistema y encendido cuando está activo (fondo lleno + glow), con el texto completo —
  «Mostrar columna de cantidad» / «Ocultar columna de cantidad» — y al lado, en chico, un ejemplo de
  qué hace.
  **`exportarPlanillaCSV`**: encabezados = el **label** de cada columna (es lo que `importarCSVTexto`
  matchea) y **sólo las visibles** (`cols.filter(colActiva)`). Separador **`;`** y **BOM UTF-8**:
  Excel lo abre en columnas y con los acentos bien; y como `_parseCSV` **detecta solo el
  delimitador** (`,` / `;` / tab), si después se guarda con comas entra igual. Nombre del archivo:
  `planilla_<molde>.csv`.
  **Verificado en la UI, ciclo completo** (sandbox 8060): el botón está **arriba de la tabla**
  (`rect.top` menor que el de la tabla) y con el texto correcto en los dos estados; exportando **con**
  la columna a la vista el encabezado sale `Cantidad;Talle;Nombre;Número;Manga;Diseño`, y **sin**
  ella `Talle;Nombre;Número;Manga;Diseño` (0 rastros de «Cantidad»); y al **volver a importar** ese
  mismo archivo con `5` y `2`, la planilla quedó con las dos filas, sus cantidades, y el contador
  mostrando **«2 fila(s) → 7 prendas»** — que es la comprobación del cálculo del front que había
  quedado pendiente en la entrada 291.
  ℹ️ De paso, en el log del server se ve que el usuario ya usó la feature: `POST /api/generar_multi`
  y un `POST /api/plantillas_planillas/guardar` con el que dejó la columna Cantidad **primera** en su
  planilla — la posición sale del template, así que el sistema la respeta tal cual.

- **2026-08-26 (291) — COLUMNA «CANTIDAD»: una fila puede valer varias prendas.** Pedido del
  usuario: una columna que esté **en todas las planillas**, que el operario **prenda con un botón**
  (o se muestre siempre, según se configure), ubicable donde se quiera, y que **repita la fila**:
  «M · pepe · 12 · cantidad 5» ⇒ **5 remeras M con pepe y 12**.
  **Decisiones que tomó él**: **sin tope** (250 es 250); si la columna está **oculta NO se aplica**
  (vale 1, pero el valor queda guardado por si la vuelve a mostrar); en la **ficha técnica** va
  **una fila con su columna Cantidad**, no cinco renglones.
  **Backend** (`servidor.py`): `COL_CANTIDAD` + **`_con_cantidad(columnas)`** — garantiza la columna
  **sin migrar ninguna planilla**, y se aplica en las **dos puntas** (`GET /api/plantillas_planillas`
  y `_traducir_prendas`), que es lo que evita que la planilla que ve el usuario y la que lee el motor
  digan cosas distintas. `_cantidad_de_fila` (entero ≥ 1; vacío/basura/0/negativo → 1) y la fila se
  **repite en `_traducir_prendas`** con `copy.deepcopy` — ⚠️ sin la copia profunda las 5 prendas
  compartirían las mismas listas. Se repite **ahí y no en el motor** a propósito: de ese punto para
  abajo todo (nesting, numerado `#01…#05`, consumo de tela, ficha) ve prendas de verdad. La cantidad
  **no se estampa** (se excluye de la personalización, como el diseño).
  **Front**: `cols` inyecta la columna con la config del template; `colActiva` decide si se ve
  (`mostrar: 'siempre'` o el botón **Cantidad** del paso Planilla, estado `cantidadOn` que vive en el
  wizard y se apaga con «Nuevo pedido»); contador **«N fila(s) → M prendas»** cuando difieren; al
  enviar, si está oculta **se borra el valor del payload** (lo que no se ve no puede multiplicar); la
  ficha técnica la hereda porque ya se arma con `cols.filter(colActiva)`. En **Configuración →
  Planillas**, al tocar la columna aparece su panel propio: explica qué hace, deja elegir *«sólo si
  el operario la pide»* / *«siempre a la vista»*, y **no se puede borrar** (es del sistema); la
  posición se cambia arrastrando su letra, como cualquier otra.
  **Contrato nuevo `verificar_cantidad.py`** (21 comprobaciones, verde): 5 → 5 prendas con los mismos
  datos; sin clave/vacía/basura/0/negativa → 1; **250 → 250** (sin tope); no viaja en la
  personalización; las copias son **independientes** (tocar una no toca a las otras); 2+3+1 = 6 en
  orden; y `_con_cantidad` no duplica ni pisa lo configurado.
  **Verificado también en la UI** (sandbox 8060): la columna llega en `/api/plantillas_planillas`
  (`('Cantidad','cantidad','boton')`), y en el paso Planilla el botón **Cantidad** la hace aparecer
  y desaparecer del encabezado.
  ⚠️ **Lo que NO se pudo probar en vivo**: escribir un número en la celda y ver el contador
  «→ N prendas», porque en este entorno el panel del navegador no compone frames y `computer` no
  puede hacer clics por coordenadas (los eventos sintéticos no disparan la edición de la planilla,
  que usa foco real). La multiplicación en sí está verificada de punta a punta en el contrato.

- **2026-08-26 (290) — 🔴 La BASE CAÍDA se avisa; antes el sistema mentía por todos lados.** El
  usuario mostró la consola llena de rojos: `yo` en **500** y `activar`, `fuentes_estado`, `telas`,
  `editables` en **401**. **Causa raíz: NO era el código** — el servicio **SQL Server (SQLEXPRESS)
  se cayó** (`STOPPED`, código 1067; en el visor de eventos: «El servicio SQL Server (SQLEXPRESS) se
  terminó de manera inesperada», 26/8 10:31:45, 19 s después de arrancar la base). Sin base no hay
  login. **No se pudo levantar desde acá: arrancar un servicio pide administrador** (`Start-Service`
  y `net start` → «Acceso denegado»); lo tiene que hacer el usuario.
  🔧 **Lo que sí era del sistema y se arregló** (tres mentiras encadenadas):
  1. **`/api/auth/yo` devolvía un 500 crudo** (HTML de Flask). El front hacía `r.json()`, explotaba,
     caía en el `catch` **junto con el caso 404** y concluía **«esta instalación no tiene
     usuarios»**: entraba igual y después **todo** daba 401. Ahora contesta **503 + `base: false`**
     con el motivo. ⚠️ Ojo: `usuario_actual()` **corta antes de tocar la base si no hay sesión**, así
     que sin cookie contestaba 200 diciendo `base: true` con la base muerta → se agregó un
     `SELECT 1` explícito en ese caso.
  2. **`/api/salud` decía `ok: true` con la base muerta**: el chequeo `base` era `critico=False`,
     herencia de cuando la migración a MSSQL recién empezaba y el sistema corría con archivos. Hoy
     los usuarios y el registro de piezas viven en la base → ahora es **crítico si hay driver ODBC**
     (sin driver sigue sin ser falla). Efecto a tener en cuenta: el **actualizador** usa este `ok`
     como semáforo, así que una base caída puede hacerle revertir una publicación — es correcto, esa
     versión no es utilizable.
  3. **El front entraba igual**: nuevo estado `sinBase` y **`PantallaSinBase`** — se muestra ANTES
     del login (mostrar el login sería mentir: no hay contra qué validar la contraseña), con el
     motivo técnico y el paso concreto (Servicios → *SQL Server (SQLEXPRESS)* → Iniciar) y un botón
     **Reintentar**.
  **Verificado en el localhost real, con la base caída**: `/api/auth/yo` → **503** `base:false`;
  `/api/salud` → **503** `ok:false` con `base` y `esquema_base` en rojo; la app muestra la pantalla
  nueva y la consola quedó con **un solo error explicado** (el 503) en vez de siete crípticos.

- **2026-08-21 (289) — La guía .ai que se descarga sale con LAS capas que hacen falta y en el orden
  correcto.** Pedido del usuario: «que la plantilla que descargamos sea real de lo que necesitamos,
  por rango o default, las capas en el orden correspondiente y con los nombres que en realidad
  necesitamos; molde no es una capa que necesitemos, es **guía**; las guías siempre van **arriba del
  diseño**; y creá dos editables más: escudo y logo».
  🔴 **El bug de fondo**: `ai_guia_medidas` escribía primero `molde` y `guias` y **después** las
  capas del arte → en un `.ai` la capa escrita primero queda ABAJO, así que **el diseño tapaba la
  guía** y había que reordenar a mano en Illustrator.
  **Cómo quedó** (de abajo hacia arriba): **`diseño` · `Editable escudo` · `Editable logo` ·
  `Nombre` · `Número` · `guias`**. Ya **no existe la capa «molde»**: los contornos, los recuadros de
  medida, el título y los nombres de pieza van todos en **`guias`**, arriba de todo.
  ⚠️ **Los editables se llaman «Editable escudo» / «Editable logo», no «escudo editable»**: el
  sistema los reconoce por el **prefijo** del nombre de capa (`_es_capa_editable`), así que al revés
  no se detectarían. Constante `EDITABLES_GUIA` en `motor_pedido.py`; el endpoint acepta
  `?editables=[…]` para cambiarlas. El front (`capasArteNombres`) ya no manda `guias` ni `molde` —
  esas las arma el servidor— y el `diseño` se fuerza al fondo aunque venga en otro orden.
  **Verificado generando la guía REAL** (sandbox de sólo lectura, molde «Camiseta de futbol»):
  las 6 capas salen en ese orden exacto, **0 duplicadas**, ninguna se llama «molde»,
  `_es_capa_editable` dice **True** para las dos nuevas, el archivo abre y cierra bien
  (`%!PS-Adobe` … `%%EOF`) y las capas están balanceadas (6 begin / 6 end). **Por modo**: en
  *default* los rótulos salen `Cuello`; en *rango XS-L*, `#XS-L Cuello` — que es lo que después lee
  el auto-mapeo.

- **2026-08-21 (288) — «¿Por qué el Administrador no tiene contraseña?» — sí tiene; el modal lo
  explicaba mal.** El campo salía **vacío** al editar y se leía como «no tiene». La contraseña
  **no se puede mostrar**: se guarda hasheada (PBKDF2-SHA256 + salt por usuario, `auth.hashear`), y
  el hash es de una sola dirección — sirve para comprobar, no para recuperar. Comprobado en la base
  (sólo lectura): `admin` → `password_hash` 32 bytes + `password_salt` 32 bytes. **Arreglo en la
  UI**: al **editar**, el paso 2 ya no muestra un campo vacío sino el campo **con puntos** (`••••••••••••`), un candado y el pill **PROTEGIDA**, más un botón **«Cambiar»**. ⚠️ Los puntos son **relleno fijo de 12**: no salen de la contraseña real, así que no dejan adivinar su largo. Debajo, la explicación de por qué no se puede ver; recién ahí aparece el campo (con foco), y un **«Dejarla como está»** para volver
  atrás limpiando lo escrito. Al **crear** un usuario el campo va directo, como siempre. Verificado
  en la UI (sandbox 8062).

- **2026-08-21 (287) — «Usuarios y permisos» rehecha de cero + contraseña con ojo.** Pedido del
  usuario: rehacerla entera para que se entienda, **arreglar los modales de elegir permisos** (el del
  usuario y el del rol) y que la contraseña se escriba **con puntos y con un ojo para verla**.
  **Qué estaba mal**: los roles se elegían con chips que mostraban la **clave** (`operario`) y nada
  más —no había forma de saber qué habilitaba cada uno sin irse a otra pestaña—; al asignar roles
  **no se veía qué terminaba pudiendo hacer** el usuario; el selector de permisos del rol era una
  lista de checkboxes nativos chiquitos, **sin buscador, sin marcar un módulo entero y sin
  contador**; y la contraseña se escribía a ciegas.
  **Cómo quedó**: encabezado con ícono + subtítulo; pestañas **Usuarios / Roles / Acciones** con
  **buscador** que filtra las tres; usuarios como tarjetas (avatar, `@usuario`, pills VOS/INACTIVO,
  último acceso, **cuántas acciones tiene**, chips de rol con el **nombre legible**); roles con el
  desglose **por módulo** (`arte 2 · config 4 · molde 5…`) en vez de una tira de claves cortada en
  «+12»; y la pestaña Acciones muestra, por cada permiso, **qué roles lo tienen**.
  🔧 **Modal de USUARIO** en 4 pasos numerados: *quién es* · **contraseña** (`CampoPass`: puntos +
  ojo `eye`/`eyeOff`, `letterSpacing` para que los puntos respiren) · *roles como tarjetas* con
  descripción y nº de acciones · **«CON ESO VA A PODER»**, el resumen de permisos efectivos agrupado
  por módulo que se recalcula al marcar/desmarcar (y si no hay rol, avisa en amarillo que el usuario
  «puede entrar pero no hacer nada»). El «activo» pasó de checkbox nativo a `Switch`.
  🔧 **Modal de ROL**: selector con **buscador**, contador `X de Y`, botones **Marcar todo / Ninguna**
  (que respetan el filtro), y por módulo un encabezado con **`CajaCheck` de tres estados**
  (vacío/parcial/lleno) que marca o saca el bloque entero; cada acción es una fila grande con nombre,
  clave y descripción. El rol de **sistema** queda bloqueado con el motivo escrito.
  **Coherencia**: la pantalla de **login** usa el mismo `CampoPass` (o hay ojo en todos lados o en
  ninguno).
  **Verificado en la UI real** con los datos del usuario, en un sandbox nuevo
  (`scratchpad/srv_visor_usuarios.py`, puerto 8062: `api_usuarios` va ENTERO y se reemplaza
  `usuario_actual()` por un admin ficticio; `SIN_SESION=1` muestra el login; todo método ≠ GET →
  403): Usuarios 1 · Roles 3 · Acciones 17; el buscador del modal de rol deja sólo las 2 acciones que
  matchean «tizada»; el check del módulo ARTE lleva el contador de **5 → 7** y vuelve a 5;
  el ojo cambia `password → text` conservando el valor (en el modal **y** en el login, centrado
  dentro del campo); el resumen de permisos va **17 → aviso amarillo → 5** al cambiar los roles.
  Consola sin errores. ⚠️ Guardar no se pudo probar (el sandbox no escribe): los `fetch` de guardado
  quedaron **idénticos** a los que ya funcionaban.

- **2026-08-21 (286) — Un ícono propio para CADA ajuste del molde, ninguno parecido a otro.**
  El usuario lo pidió mirando la lista: había dibujos **prestados** de otras cosas y hasta
  **repetidos** — «Borde de corte» y «Editable» usaban el MISMO (`distribucion`), «Variables» el de
  columnas y «Telas» una hoja con líneas casi igual a la grilla de «Planilla». Ocho íconos nuevos en
  `Icon`: **`molderia`** (hoja con una pieza adentro = el archivo del molde), **`variables`** (un
  tronco que se abre en dos ramas), **`etiqueta`** (la etiqueta colgante; la «T» vuelve a ser sólo de
  Fuentes), **`nestingPiezas`** (piezas encastradas dentro de la tela), **`telaRollo`** (el rollo con
  la tela saliendo), **`bordeCorte`** (la pieza + la línea punteada por donde se corta),
  **`editable`** (las cuatro flechas de mover/transformar) y **`nombres`** («Aa»). Con `planilla`
  (grilla) y `plantilla` (camiseta) de la entrada 285, los **10 botones tienen dibujo propio**.
  **Coherencia fuera del menú** (mismo concepto = mismo ícono): las cards «Moldería», «Telas» y
  «Reglas de Nesting» del panel de Configuración y los dos «Asignar telas» del paso Arte. Quedaron
  como estaban los usos donde `productos` es un *placeholder* de imagen o la «Ficha técnica».
  **Verificado en la UI** (sandbox 8060 → /admin → Moldería → molde): los 10 `<svg>` de
  `ajuste-*` son distintos entre sí (0 duplicados, 0 vacíos) y el «Aa» de Nombres se pinta en el
  acento (14×14 px, `rgb(0,212,255)`).
- **2026-08-21 (285) — Íconos propios para «Planilla» y «Plantilla».** Los dos usaban íconos
  genéricos (`columnas` y `distribucion`, prestados de otras cosas) y no ayudaban a distinguirlos.
  Dos íconos nuevos en `Icon`: **`planilla`** = grilla de hoja de cálculo (encabezado + filas y
  columnas) y **`plantilla`** = **silueta de camiseta** con cuello redondo y mangas — la plantilla es
  la moldería de la prenda. Se usan en los botones de ajustes del molde y, por coherencia, la card
  **«Planillas»** del panel de Configuración pasó al mismo `planilla` (un ícono por concepto).
  Verificado en la UI (sandbox 8060 → /admin → Moldería → molde): los `<svg>` de `ajuste-planilla`,
  `ajuste-diseno` y `ajuste-etiqueta` son los tres distintos y son los nuevos.

- **2026-08-21 (284) — «Plantilla» y «Planilla» ya no van pegadas en los ajustes del molde.** Estaban
  una debajo de la otra y los nombres se diferencian en **una letra**: el usuario se equivocaba de
  botón. Se **intercambiaron** con «Etiqueta» — el menú queda: Moldería · Variables · **Etiqueta** ·
  Planilla · Nesting · Telas asignadas · Borde de corte · **Plantilla** · Editable · Nombres. Además
  «Etiqueta» cambió de ícono (`columnas` → `fuentes`) para no repetir el de Planilla justo al lado.
  Los `data-tour` (`ajuste-<id>`) no dependen del orden: la ayuda guiada sigue en verde. **Verificado
  en la UI** (sandbox 8060 → /admin → Moldería → «Camiseta de futbol»): las 10 anclas salen en el
  orden nuevo, con 5 posiciones entre Plantilla y Planilla.

- **2026-08-21 (283) — «Perfiles de color» rediseñada (referencia visual del usuario).** Mandó una
  captura del layout que quería: encabezado con la **rueda de color** + título grande + una línea de
  subtítulo, **toggle RGB | CMYK/Impresión** arriba y una **grilla de tarjetas simples** con un tick
  en la elegida — «así, pero con nuestros colores». Antes la pantalla apilaba **las dos listas**
  (CMYK arriba, RGB abajo) y había que scrollear para ver la segunda. Ahora `perfilEspacio`
  ('cmyk' por defecto — es el que manda para sublimar) decide cuál se muestra, y todo el acento sale
  de **`var(--accent)`** (el cian del sistema, `hsl(190,100%,50%)`), no del azul de la referencia.
  La tarjeta quedó: nombre centrado + tick circular a la derecha… y la **franja de colores reales
  del perfil** —que la referencia no tenía— se conservó como una **línea de 3 px abajo**: es
  información de color que ya estaba y sacarla sería perder referencia. Se mantuvo el ancla
  `perfil-card` de la ayuda guiada (+ `perfil-esp-rgb` / `perfil-esp-cmyk`).
  **Verificado en la UI real** (sandbox de sólo lectura en 8060, entrando por `/admin` →
  Configuración → Perfil de color): el toggle CMYK activo tiene borde `rgb(0,212,255)` = `--accent`
  y fondo cian al 8 %; 22 tarjetas CMYK con «U.S. Web Coated (SWOP) v2» marcada (borde accent, tick
  con ✓ y franja de 6 colores); al tocar **RGB** pasa a 11 tarjetas con «IEC 61966-2.1 … sRGB»
  marcada; grilla responsive (4 columnas a 1280 px, 3 a ~1024 como en la referencia); consola sin
  errores de JS. ⚠️ No pude adjuntar captura: en este entorno el panel del navegador no compone
  frames y `screenshot` da timeout — se verificó leyendo el DOM y los estilos computados.

- **2026-08-21 (282) — La ETIQUETA rotula el nombre GENERAL de la pieza, sin el número.** Pedido del
  usuario: «en la etiqueta de talle sólo debe aparecer el nombre general, sin el número al lado» —
  «Frente 9» se estampa **«Frente»**. Las piezas homónimas se siguen distinguiendo por el `#nro` que
  la etiqueta ya trae. **Motor** (`motor_pedido.py`): `_pieza_txt` = `_pieza_limpia` sin el número
  final (regex `_re_etq`, compilado al lado de `_norm_generico`); se usa en el texto de la etiqueta
  **única** y en el de las **zonas** (`_eops_zonas`). ⚠️ No sirve `_norm_generico` para esto: ésa
  normaliza a minúsculas para **comparar**, no para mostrar. La búsqueda de config (`piezas_off`,
  `zonas`, `posiciones`) sigue con `_pieza_limpia` — ya resuelven por genérico, no cambia nada.
  **Front** (LEY «el arte se ve igual que la tizada»): los **4** lugares que previsualizan el texto
  pasaron por el genérico — visor del pedido/mapeo (ya tenía `_genN`), lista de piezas de la config
  de Etiqueta, visor de la pantalla Etiqueta y etiqueta **por zonas**.
  **Contrato nuevo `verificar_etiqueta_nombre.py`**: corre el MOTOR REAL sobre el molde del usuario
  (copia en un temporal, `db` reemplazado por un doble que explota) y **espía `_eops_borde`**, que es
  quien recibe el texto que se dibuja. Verde con «Camiseta de futbol» (34 piezas, 28 numeradas): los
  28 textos salen `M-Cuello-#01`, `M-Frente-#01`, `M-Espalda-#01`… ninguno numerado; y los controles
  («pieza» apagado → `M-#01`; sólo «pieza» → `Cuello`, sin un solo dígito) siguen funcionando.
  ⚠️ **Lo que NO se pudo verificar en la UI**: la pantalla de Etiqueta vive en Configuración y el
  sandbox de sólo lectura no llega ahí (no hay sesión, no se dibuja el menú lateral) — el cambio del
  front quedó verificado por compilación y por usar el mismo `nombreGenerico` de siempre.
  🔧 **PENDIENTE encontrado de paso**: `verificar_etiqueta_posicion.py` **está roto desde la
  migración a MSSQL** — elige el molde buscando `datos/productos/<pid>/registro_producto.json`, que
  ya no existe (el registro vive en la base), así que siempre corta con «No hay ningún molde con
  plantilla + registro». Arreglo: copiarle el preámbulo de `verificar_etiqueta_nombre.py` (leer el
  registro con `db.leer_registro` ANTES de reemplazar el módulo y volcarlo al temporal).

- **2026-08-21 (281) — CORRECCIÓN: se nombra la VARIABLE, no el molde.** Yo había leído al revés el
  pedido de la entrada 280 y puse el molde. La regla es: **la VARIABLE que se está usando** —
  `«VARIABLE» · diseño «DISEÑO»`. `_arteLbl(did, item)` toma el **ítem del paso Arte** (el `label`
  de la variable; si el ítem es un molde entero —los moldes propios no tienen Variables— su label ya
  es el nombre del molde, así que la misma función sirve). La unidad de aviso pasó de (diseño,
  molde) a **ítem**: `itemsPedido` / `itemsSinArte`, las telas volvieron al detalle **por variable**
  (`telasFaltantesDet` = `[{did, it, n}]`, sin sumar por molde) y los faltantes de tipografía —que
  el server informa por (diseño, molde)— se **expanden** a las variables de ese molde. `irAlArte`
  ahora salta a la variable exacta (molde + clave) y el botón dice «Ir a esta variable».
  🔴 **FORMATO FINAL: `«MOLDE» · variable «VARIABLE» · diseño «DISEÑO»` — los tres, SIEMPRE.** Se
  probó primero la variable sola y después «el molde sólo si el nombre de la variable se repite»:
  las dos se descartaron. La misma variable la pueden usar **muchos** diseños (el usuario habló de
  100): lo que separa un caso de otro es el **diseño**, y el molde es el contexto — mostrarlo a
  veces sí y a veces no era demasiado sutil. Si el ítem es un molde ENTERO (sin Variables) se omite
  la parte de variable. **Verificado en la UI** (sandbox 8061, 2 moldes · 2 diseños · 3 variables):
  «Rebars-Regular» en *camiseta asque · variable Cuello redondo · diseño JUGADOR*, *Camiseta de
  futbol · variable Cuello redondo · diseño JUGADOR*, *Camiseta de futbol · variable cuello V ·
  diseño JUGADOR*; y «Falta el arte de «Camiseta de futbol» · variable «cuello V» · diseño
  «GOLERO»».
- **2026-08-21 (280) — Lo que falta dice DE QUÉ ARTE es (⚠️ corregido por la 281: va la VARIABLE).**
  Cada aviso de faltante tiene que identificar el arte: cuál y en qué **diseño**. Una sola función,
  `_arteLbl`, la usan **los tres requisitos** del paso Arte,
  el detalle del progreso, el `title` del botón **Enviar** y el error de `generarMulti`. Cambios de
  fondo: (1) **Tipografías de TODO el pedido, no sólo del arte en pantalla** — `fuentesEstado` es del
  arte que estás mirando, así que con dos moldes/diseños no se podía decir de cuál era el faltante
  (y de los otros te enterabas recién al llegar). Nuevo `fuentesPorArte` = `{ "<diseño>|<MOLDE>":
  [fuentes] }`, con `cargarFuentesDeArte(did, mid)` y `cargarFuentesTodas()` (GET en paralelo por
  cada arte cargado; se dispara al entrar al paso, al subir un arte y al resolver una fuente).
  `fuentesFaltantesItems` es la lista derivada que consumen el cartel, el modal y `pasoItems`, y es
  la que decide si sale el cartel al avanzar. (2) **Telas con detalle por molde**: `telasFaltantesDet`
  = `[{did, mid, n}]` — las variables del mismo molde se **suman** (el operario piensa en moldes);
  `telasFaltantesTotal` ahora se deriva de ahí. Antes decía «faltan 3 piezas sin tela» sin decir
  dónde. (3) El **arte faltante** en el paso Planilla y en `generarMulti` pasó de mirar
  `moldesSeleccionados` a mirar **(diseño, molde)**: el mismo molde en dos diseños ahora se
  distingue. (4) El cartel del paso Arte y el de avanzar listan **una línea por arte** y traen
  **«Ir a este arte»** / **«Resolver»**, que saltan al molde+diseño del problema (`irAlArte`).
  **Verificado en la UI real** (sandbox 8061 que finge un faltante, con 2 moldes y 2 diseños): el
  cartel lista los 3 artes por separado («Rebars-Regular» en *camiseta asque* · diseño *JUGADOR* /
  en *Camiseta de futbol* · diseño *JUGADOR* / … · diseño *GOLERO*), el detalle del progreso dice
  «Falta el arte de «Camiseta de futbol» · diseño «GOLERO»», y el effect no entra en bucle (10 GET
  en toda la sesión). ⚠️ No pude forzar el caso «piezas sin tela» en el sandbox (necesita POST): ese
  texto quedó verificado sólo por código.

- **2026-08-21 (279) — La TIPOGRAFÍA avisa, no traba: amarillo + «Seguir de todos modos».** Regla del
  usuario: de los tres requisitos del paso Arte, la fuente es el **único que no frena** (sin ella la
  tizada igual sale, sublimada con «Anton Regular»). Cambios: (1) `MarcaPaso` tiene un **tercer
  estado** — un ítem de `pasoItems` con `aviso: true` se pinta **AMARILLO con «!»** en vez de rojo
  con cruz, y el borde del conjunto sigue el mismo código (verde listo · amarillo avisa · rojo
  traba); helpers `_pasoTraba` / `_pasoAvisa` / `textoAvisoPaso`, que también cambian el texto sutil
  de arriba de la barra («Lo que está en amarillo no frena el pedido, pero te lo vamos a recordar
  antes de avanzar»). (2) El ítem `fuentes` lleva `aviso: true`, así que **el botón «A la planilla»
  queda habilitado** aunque falte la tipografía. (3) `irAPlanillaDesdeArte({forzarFuente})`: la traba
  vieja (abría el modal «Resolver fuente» y cortaba) pasó a ser un **cartel** —`fuenteAvanzar`— con
  el mismo texto que el aviso del paso y tres salidas: *Cancelar*, **«Seguir de todos modos»**
  (llama con `forzarFuente: true`) y *«Cargar la tipografía»* (abre el modal de siempre). (4) El
  cartel del paso Arte pasó de rojo a **amarillo** para no contradecir a su propia marca, y dice
  «se va a **sublimar**» (no «estampar»). **Verificado en la UI real** (sandbox de sólo lectura en
  8061 que miente un faltante `Rebars-Regular`): marca amarilla `rgba(245,158,11,.6)` sólo en
  «Cargar fuente», arte y tela en verde, botón `disabled = false`, el cartel aparece con los tres
  botones y «Seguir de todos modos» deja el wizard en `pedidoPaso = 'planilla'`.

- **2026-08-21 (278) — AUDITORÍA de «transacciones fantasma» en la base: NO hay. Se arregló otra cosa que sí estaba mal.** El usuario pidió revisar a fondo y reparar sólo si hacía falta. **Revisión del código**: TODO lo que toca MSSQL pasa por `db.cursor()` —un context manager con `commit` al salir bien, `rollback` si algo falla y `close()` en un `finally`— y no hay una sola conexión fuera del módulo (verificado con grep en todo el repo: sólo `instalar_servidor.py`, que también lo usa). No hay conexión global, ni caché de conexiones, ni transacciones que crucen requests. **Medición sobre la base REAL en tres escenarios**: (a) en reposo, (b) bajo carga —24 requests concurrentes que leen catálogo/estado/config— y (c) después de matar el server de golpe (`taskkill /F`) y reiniciarlo: **0 sesiones dormidas con transacción abierta y 0 peticiones bloqueadas** en los tres. **Lo que parece una fuga y no lo es**: `sys.dm_tran_active_transactions` muestra ~14 transacciones «abiertas hace 3 días», pero todas son **internas del motor** (`worktable`, `WorkFileGroup_fake_worktable`, `QDS nested transaction`) y **sin sesión asociada** (`session_id = NULL`) — existen con la app apagada. Y la sesión `sleeping` del server es el **pooling de ODBC** (pyodbc lo trae activado): la conexión vuelve al pool para reusarse, con **`open_transaction_count = 0`** y sin locks. 🔧 **Lo que SÍ se arregló** (real, aunque no era la fuga): en `db.cursor()` el `rollback` iba **sin proteger** — si la conexión ya se había caído (base reiniciada, red cortada), `rollback()` lanzaba **su propia** excepción y ésa **tapaba la original**, dejándote sin saber qué falló de verdad; ahora va en `try/except` y el error real llega arriba (el `close()` también). La transacción no quedaba abierta igual: al cerrar la conexión el motor descarta lo no confirmado. **Contrato nuevo `verificar_db_conexiones.py`**: corre contra la base real sin escribir nada — mide sesiones y fantasmas antes/después de 30 consultas, fuerza un error **en medio de una transacción** y comprueba que no queda nada abierto, y verifica que el error de SQL llegue tal cual a quien llamó.

- **2026-08-21 (277) — El cartel de «tipografía no encontrada» va ARRIBA y se va solo al resolverla.** Pedido del usuario: «ese cartel debe aparecer en la parte superior que tenemos vacía al pedo, y si ya seleccioné una fuente nueva debe desaparecer». **(1)** Salió del `aviso` del visor —donde tapaba el arte— y entró en la **fila de los diseños**, que deja todo ese ancho libre: caja compacta a la derecha (⚠ rojo + el texto + botón **«Resolver»** que abre el modal de tipografías). **(2)** 🔴 **No desaparecía**: `resolverFuente` llamaba a `cargarFuentesEstado()` **antes** de que React actualizara el estado, así que el server recalculaba los faltantes con el mapa de reemplazos **viejo** y el cartel seguía puesto (mismo error de tick que la 276, en el otro lado). FIX: `cargarFuentesEstado(reemplOverride)` toma el mapa **recién elegido**; se sacó además la llamada duplicada que quedaba con el mapa viejo (un viaje al server al pedo). **VERIFICADO**: build en verde y el cartel ya no existe en el visor. ⚠️ La posición final y el «desaparece» quedan al ojo del usuario: hace falta un arte con una fuente que falte, y el sandbox de solo lectura no deja cargarlo.

- **2026-08-21 (276) — Cambiar la tipografía se ve EN EL ACTO, esté o no la original.** Seguimiento de la 275: «capaz que leyó la fuente original, pero si después la quiere cambiar por una de nuestro catálogo lo puede hacer sin problema; debe cambiarse en tiempo real». **🔴 Un bug que introduje YO en la 275**: al mudar el reemplazo del molde al pedido, `resolverFuente` hacía `setFuentesReempl(...)` y **acto seguido** `cargarPreviewPiezas()` — que leía el estado **viejo** (React no lo actualiza en el mismo tick), así que el visor pedía el render **sin** la tipografía recién elegida y no cambiaba nada hasta el próximo render. FIX: `cargarPreviewPiezas(mapeoOverride, reemplOverride)` acepta el mapa **ya actualizado** y quien elige la fuente se lo pasa explícito. Además: **(a)** la clave del caché en memoria del front (`_pvKeyCon`) incluye ahora los reemplazos —sin eso, mismo mapeo + mismo talle devolvía el **hit anterior** y parecía que no pasaba nada—; **(b)** las **dos precargas** de talles (la de «Asignando…» y la de fondo) firman y mandan los mismos reemplazos, si no el talle vecino quedaba cacheado con la tipografía vieja; **(c)** el botón pasó a llamarse **«Tipografía»** (antes «Reemplazar fuente», que sonaba a que sólo servía cuando faltaba) y **ya estaba siempre disponible** — se puede cambiar aunque la original esté, que es la regla desde la 245. **VERIFICADO** con `verificar_fuentes_pedido.py` ampliado: la **clave del render cambia** con la tipografía elegida (y es estable con los mismos datos), o sea que el dibujo se rehace en vez de servirse del caché. ⚠️ Falta el ojo del usuario sobre el cambio en pantalla: el sandbox de solo lectura no deja cargar el arte.

- **2026-08-21 (275) — 🔴 «Le puse un arte con una tipografía que YA tenemos y no la usó, puso otra»: era un reemplazo VIEJO guardado en el molde.** Reporte del usuario. **DIAGNÓSTICO (medido, no supuesto)**: la tipografía del arte —`ClubAmerica2021-2022`— **sí estaba** en el catálogo (`subida_ClubAmerica2021-2022.ttf`) y el resolver la encontraba bien: `resolver_fuente` **sin alias** devolvía el archivo correcto. Lo que la pisaba era un **alias guardado en el molde**: `prod["fuentes_reemplazo"] = {'ClubAmerica2021-2022': 'Hawken Personal Use Only Regula'}`, de alguna prueba anterior — y por la regla de la 245 («la elección manda») ese alias ganaba **siempre**, aunque la fuente original estuviera. De ahí las dos cosas que vio: ni la original, ni la predeterminada, sino «una random». **LA REGLA NUEVA (del usuario)**: *«si le asigna una tipografía de las nuestras se asigna a ESE pedido; si empieza un pedido desde 0, esa tipografía que eligió ya se olvidó»*. Implementado: **(1)** el reemplazo **es del PEDIDO** — vive en el front (`fuentesReempl`, dentro del estado del pedido), **viaja en cada request** (`fuentes_reemplazo` en preview, generar, `fuentes_estado`) y `_fuentes_para(pid, reemplazos)` sólo arma alias con eso: **lo guardado en el catálogo ya no se lee** (queda como dato muerto; no se migra nada). **(2)** `POST /api/pedido/fuente_resolver` **dejó de persistir**: devuelve `{faltante, usar, quitar}` y el front lo guarda en el pedido (elegir la original devuelve `quitar` y se borra el reemplazo). **(3)** La **clave del caché** de piezas firma los reemplazos **del pedido** (si siguiera firmando los del molde, cambiar de fuente serviría el render viejo — el bug de la 243). **(4)** «Nuevo pedido» **olvida** el reemplazo y además **borra las tipografías subidas «sólo para este pedido»** (`POST /api/pedido/fuentes_pedido_limpiar`): antes quedaban en `datos/<pid>/fuentes` para siempre y el pedido siguiente las seguía encontrando — las del **catálogo** no se tocan. **(5)** El **cartel fijo** del paso Arte dice lo que pidió: «Tipografía no encontrada: X. Se va a estampar con «Anton Regular» (la predeterminada). Cargá la tipografía que usó el diseño, o elegí una de nuestro catálogo — si no, la tizada sale con la predeterminada». **VERIFICADO** con el contrato nuevo **`verificar_fuentes_pedido.py`**: las **13** tipografías del catálogo resuelven **exactamente a su propio archivo** (o sea, con la fuente instalada no hay «random»), el reemplazo del pedido manda y **sin él vuelve la original**, el molde que tiene el reemplazo viejo guardado (**«Camiseta de futbol»**) **ya no lo impone**, y la predeterminada existe. Server reiniciado y sano.

- **2026-08-21 (274) — El panel de TELAS, rehecho de cero + el progreso con ✓/✕ y texto completo.** Dos pedidos del usuario. **(A) TELAS** («muy básico y para nada intuitivo… remodelalo por completo desde 0, más aplicación y menos página web»): el panel dejó de ser un formulario de dos vistas con lista larga y buscador, y cuenta la historia como la piensa el operario — **1) esta prenda va en TAL tela · 2) salvo estas piezas, que van en tal otra**. Quedó: **cabecera** compacta; **estado** en una tarjeta (verde «Las N piezas tienen tela» / ámbar «Faltan N de M» **con los nombres**); **«La tela de esta prenda»** = una card grande con la muestra de color, el nombre y «N de M piezas», que se toca para cambiarla (la principal se deduce: la más usada); **«Piezas en otra tela»** = una card por excepción con su color, sus piezas y una ✕ para devolverlas a la principal; el gesto de excepción invertido a lo natural (**tocás las piezas en el visor → «Elegir tela»**, antes era al revés); y abajo **«⧉ Usar estas telas en otros moldes»**. **El selector salió a un MODAL**: las 34 telas en grilla de cards con su **muestra de color** (la misma del visor), el **ancho útil en cm** y buscador arriba — en la columna de 210 px era una tira ilegible. Un toque elige **y aplica**: no hay «guardar» aparte. **(B) PROGRESO**: marcas más grandes y modernas (SVG en badge circular), **✓ verde** cuando está y **✕ ROJA** cuando falta (era un «○» ámbar: lo que falta **frena** el pedido, no es una advertencia tibia), **nombres completos** («Asignar arte», «Asignar tela», «Cargar fuente» en vez de «Arte/Telas/Fuentes»), y **arriba, sutil y centrado**: «Tenés que completar todo lo de este paso para pasar al siguiente». **VERIFICADO en la UI**: el chip muestra «Asignar arte · Asignar tela · Cargar fuente 2/3» con la primera marca en **✕ #ef4444** y las otras en **✓ #10b981** (badges de 20 px), y el aviso arriba; el panel de telas abre en «La tela de esta prenda → Elegí la tela», y el selector lista **34 telas** con su color y «157 cm útiles». ⚠️ Falta el ojo del usuario sobre el flujo completo con arte cargado (el sandbox de solo lectura corta los POST).

- **2026-08-21 (273) — FALSA ALARMA: «El visor del arte no puede dibujar: falta plantilla/arte/registro» apenas entrar al paso Arte.** Reporte del usuario con captura. CAUSA: al entrar, el visor pide el render real de las piezas (`POST /api/arte/preview_piezas`); `_piezas_base` devuelve `None` si falta **plantilla, arte o registro** y el endpoint contestaba **409 con los tres juntos** en el mensaje. Como el arte de ese diseño **todavía no está cargado** —que es exactamente a lo que se viene a este paso—, el 409 era el estado NORMAL… y el front lo mostraba como **cartel rojo de error** apenas entrar. FIX: **(1)** el server dice **cuál** de los tres falta (`{"error": "todavía no cargaste el arte de este diseño", "falta": "arte"}`, o «este molde todavía no tiene plantilla cargada» / «el molde no tiene piezas registradas»); **(2)** el front **ni siquiera pide** el preview si ese `(diseño, molde)` no tiene arte cargado — sin pedido no hay 409 ni cartel; **(3)** si igual llega un 409 con `falta: 'arte'`, **no se avisa**: los otros dos sí, porque ésos sí son un problema. **VERIFICADO en la UI**: entrando al paso Arte con el arte sin cargar, **cero carteles** (antes salía siempre). Server reiniciado por PID y sano.

- **2026-08-21 (272) — Telas del pedido: se llama ASIGNAR, el default es «una tela para todas», y lo elegido se COPIA a los otros moldes.** Pedido del usuario: «la parte de ver telas en realidad es asignar telas; debe tener la opción por defecto de seleccionar a todas las piezas 1 tela, y opcional elegir tela para ciertas piezas; y debe tener la opción de clonar la selección para todos los moldes o elegir a qué moldes, sin la necesidad de navegar de molde en molde». **(1)** El botón del visor pasó de **«Ver telas de pieza» a «Asignar telas»** (y los avisos que mandaban ahí, con él). **(2) EL CAMINO POR DEFECTO ES UNA TELA PARA TODAS**: en el panel, un desplegable **«Una tela para todas»** que asigna esa tela a todas las piezas de la prenda de un saque; elegir pieza por pieza quedó como la excepción, detrás de **«Tela por pieza…»** (el modo de antes, intacto: elegir tela → tocar piezas → Asignar). **(3) COPIAR A OTROS MOLDES**: botón **«⧉ Copiar estas telas a…»** → modal con **todos los ítems (molde en diseño) del pedido**, con tildes, **«Todos los moldes del pedido»** de un toque, y marca cuáles ya tenían telas asignadas (avisa que se pisan). Copia el mapa `{pieza → tela}` a los ítems elegidos (`telaPorPieza[diseño|molde]`); las piezas que en el destino se llamen distinto no reciben nada y quedan como faltantes, que es lo correcto. **(4)** Elegir una tela **sin piezas a la vista** (prenda todavía armándose o sin arte) **avisa** en vez de no hacer nada: antes fallaba en silencio y parecía roto. **VERIFICADO en la UI**: el botón dice «Asignar telas»; el panel muestra «UNA TELA PARA TODAS» con el desplegable de las 35 telas del registro y el botón «Tela por pieza…»; el aviso de «todavía no se ven las piezas» sale al elegir una tela sin piezas. ⚠️ **NO verificado a mano**: la asignación efectiva y el modal de copiado — necesitan **arte cargado**, y el sandbox de solo lectura corta los POST. Queda al ojo del usuario.

- **2026-08-21 (271) — El progreso va CENTRADO, con el tick y el nombre corto de cada requisito + 🔴 FIX de un error MÍO que dejaba la pantalla en blanco.** **(1)** Pedido del usuario sobre la 270: «lo mismo pero centrado en la misma línea, y ahí mismo debe mostrar el tick y el paso reducido: decir qué le falta pero no un texto largo; al presionar te muestra más detallado, pero sólo de ese paso y no de todos». Ahora el progreso es una línea de chips **«○ Arte · ✓ Telas · ✓ Fuentes 2/3»** (cada requisito con su tick y su nombre CORTO, sin frases), **centrada respecto de la barra**: `BarraPaso` tiene una zona `centro` en `position: absolute; left: 50%` — centrarla con el flex la habría dejado bailando, porque lo que sobra entre los botones cambia de ancho en cada paso. El modal dice **de qué paso es** en el título («Paso 3 · Arte — qué falta») y muestra **sólo ese**. **(2) 🔴 EL ERROR (mío, lo vio el usuario en consola)**: `Uncaught ReferenceError: Cannot access 'iv' before initialization` al entrar al pedido. El memo `pasoItems` estaba declarado ~1000 líneas ANTES de `planillaInvalidos`, y **un `useMemo` se EJECUTA durante el render, en la línea donde está**: al llegar a la rama de la planilla tocaba un `const` que todavía estaba en la zona muerta (TDZ) y la pantalla quedaba en blanco. Se movió el memo **debajo** de `planillaInvalidos`, con el porqué escrito al lado. **LECCIÓN**: un `useMemo` no es «código que corre después» — corre ahí mismo; toda dependencia suya tiene que estar declarada **antes** de esa línea, y el build **no lo detecta** (compila perfecto). **VERIFICADO en la UI**: consola **sin el error**, el chip queda centrado (centro del botón = centro de la barra, 628 = 628), en Arte muestra «○ Arte · ✓ Telas · ✓ Fuentes 2/3» y el modal abre en «Paso 3 · Arte — qué falta» con «Falta el arte de «camiseta asque» en «JUGADOR»».

- **2026-08-21 (270) — Barra de PROGRESO por paso: qué está hecho, qué falta, y el detalle en un modal.** Pedido del usuario: «en ese espacio que haya una barra de progreso y le vaya tildando todo lo que ya va haciendo y lo que le falta dentro de cada paso —ejemplo en el paso arte: cargar el arte de todos los moldes y diseños, elegir tela, cargar fuente no encontrada—, y al presionar debe abrir un modal mostrándole más a detalle lo que le falta: cargar arte de molde tal en JUGADOR». Hecho: **`pasoItems`** (un memo) arma la lista de requisitos del paso en curso —`{label, hecho, faltan[], ok[]}`, cada pendiente **con nombre y apellido**— y de ahí comen **las dos** vistas (si fueran dos fuentes, una diría «todo listo» mientras la otra muestra pendientes). **En la barra**: `ProgresoPaso` en el hueco de la derecha — un tramo por requisito (pintado = cumplido), «N/M» y el **primer pendiente escrito**; se toca y abre el modal. **En el modal**: barra de avance, y por requisito ✓/○ con el detalle (lo que falta, o lo que ya está resuelto). **Qué mira cada paso** — *Diseño*: haber elegido uno · *Moldes*: diseño elegido + la prenda de cada diseño · *Arte*: arte de cada (molde, diseño) + la tela de cada pieza + las fuentes del arte · *Planilla*: filas cargadas + valores válidos + arte de todos los moldes · *Tizadas*: la generación terminada. **Los avisos sueltos de la barra se fueron adentro**: eran textos largos («⚠ Faltan 14 pieza(s) sin tela — asigná su tela en…») que empujaban el botón de avanzar. **VERIFICADO en la UI**: paso 1 «0/1 · Falta: elegir el diseño» → tocando JUGADOR pasa a «1/1 · Todo listo ✓»; paso 2 «1/2 · Falta: la prenda de cada diseño» y el modal muestra «✓ Elegir el diseño · «JUGADOR»» + «○ La prenda de cada diseño · «JUGADOR» no tiene ninguna prenda elegida»; paso Arte «2/3 · Falta: cargar el arte» con el detalle **«Falta el arte de «camiseta asque» en «JUGADOR»»** (el ejemplo textual del pedido) y las telas y fuentes en ✓.

- **2026-08-21 (269) — Paso 1 centrado (campo arriba, botones de a 3 abajo) y UNA sola barra inferior para los 5 pasos.** Pedido del usuario sobre la 268: «los botones a seleccionar quitalos de ahí y ponelos abajo del campo de escribir; el campo de escribir debe estar centrado, y los botones también, y que haya 3 por línea. Y estos botones y el de volver atrás que estén todos abajo de la pantalla y en los 5 pasos ubicados en el mismo lado: no puede variar el orden en ningún paso». **(1) Paso 1**: el campo para escribir quedó **arriba y centrado** (texto centrado incluido) y los **12 diseños abajo**, en una grilla de **3 columnas** centrada (`maxWidth 620`); los elegidos, en chips centrados debajo. **(2) UNA barra para todos**: componente **`BarraPaso`** + `BtnVolver` + `BtnSiguiente` — orden fijo **← volver · ↺ Nuevo pedido · acciones del paso … avisos · botón que avanza**. Los 5 pasos la usan (6 usos: el paso 5 tiene dos estados) y **no queda ninguna barra hecha a mano**: antes cada paso armaba la suya y el orden bailaba (en Moldes «Nuevo pedido» iba primero y no había «volver»; en Arte no había «Nuevo pedido»; en Tizadas los botones estaban **arriba**, en el encabezado). El «← Diseño» que estaba arriba en Moldes se fue a la barra. **(3)** `verificar_guias.mjs` aprendió a leer las anclas que se pasan **por prop** (`ancla="…"`), porque ahora el `data-tour` lo pone el componente: sin eso el build fallaba diciendo que faltaba `pedido-ir-moldes`. **VERIFICADO en la UI**: el input va antes que los botones y está centrado, la grilla mide `200px 200px 200px` (3 por línea), y las barras salen `[↺ Nuevo pedido … Elegir los moldes →]` en el paso 1 y `[← Diseño · ↺ Nuevo pedido · Subir mi propio molde … Cargar el arte →]` en el 2 — mismo orden, mismo lugar. Build con los chequeos de la ayuda en verde. ⚠️ Trampa: al escribir el regex del verificador desde Python, `` en una cadena normal se volvió un **backspace real** dentro del archivo (`/ancla=…/`) y el chequeo no matcheaba nada — se vio con `cat -A`.

- **2026-08-21 (268) — El pedido arranca eligiendo el DISEÑO (lista de botones), y los moldes pasan a ser el paso 2.** Pedido del usuario: «primer paso será elegir el diseño; ahí no verá moldes ni nada, sólo una lista de diseños preestablecidos para elegirlos como botón. Segundo paso, elegir el o los moldes de cada diseño como hace actualmente. Del 3º en adelante sigue como estaba». El wizard pasó de 4 a **5 pasos**: **1 Diseño · 2 Moldes · 3 Arte · 4 Planilla · 5 Tizadas**. **(1)** Paso nuevo `pedidoPaso = 'diseno'` (el inicial, también al que vuelve «Nuevo pedido»): los **12 diseños** de `DISENOS_PRESET` como botones que se tocan (JUGADOR, GOLERO, CUERPO TECNICO, DISEÑO 1-5, ALTERNATIVA, PRINCIPAL, LOCAL, VISITANTE), los elegidos abajo con su ✕, y **ningún molde a la vista**. ⏳ La lista está **en el código a propósito** (decisión del usuario: «de mientras crea en el código los siguientes… después vemos de que puedan crear en configuración y crearle una tabla»). El campo para **escribir** un diseño suelto quedó, abajo, para lo que no está en la lista («se usará sólo para ese trabajo»). **(2)** El paso `moldes` es el de siempre —la grilla de variables, sin filtrar por diseño (regla del usuario: «los moldes se muestran para todos los diseños»)— menos el input del nombre, que se fue al paso 1; arriba quedó «← Diseño» y los chips para elegir a cuál se le cargan los moldes. **(3)** El modelo de datos **no cambió**: `disenosPedido` / `disenoMoldes` / `disenoVars` son los mismos y el resto del pedido (arte, planilla, motor) no se entera. El id del diseño sale de **`_slugDiseno`**, el MISMO que usa el motor para agrupar las filas — un slug propio habría dejado filas sin diseño. **(4)** Ayuda guiada al día: ancla nueva `pedido-diseno-lista` + `pedido-ir-moldes` + `pedido-volver-diseno`, ruta `paso:diseno` en `tutor.jsx`, el tutorial «Armar una tizada» ahora empieza tocando el diseño de la lista, y **`verificar_guias.mjs` describe el flujo nuevo** (el arranque del wizard es `diseno`; la secuencia esperada arranca en `pedido-diseno-lista` → `pedido-ir-moldes`). **VERIFICADO en la UI real**: la barra muestra los 5 pasos; el paso 1 lista los 12 botones con «¿No está en la lista?» abajo y el botón «Elegir los moldes» apagado hasta tocar uno; tocando JUGADOR y GOLERO quedan los dos en «ESTE TRABAJO LLEVA» y el botón se habilita; en el paso 2 están «← Diseño», los dos chips y la grilla de moldes de siempre, y al tocar una prenda se le asignó al diseño activo (el chip pasó a «1» y el aviso quedó en «Falta elegir variable en «JUGADOR»»). Build con los chequeos de la ayuda en verde (79 anclas, 22 pasos en orden).

- **2026-08-21 (267) — Agregar piezas: BORRADOR hasta «Guardar», duplicado por vectores homólogos, y lo guardado no se borra.** Las tres reglas las puso el usuario sobre la auditoría de la 266: «lo subido nuevo no se guardará hasta que le den a guardar ni se nombre, y después de guardar ya no se puede borrar más; si no se guarda podés hacer lo que quieras. Lo de duplicar debe tomar los vectores, respetar los talles, pero el nombre ni el número no: eso se registra como nuevo. Y todo lo que ya esté guardado, o borrás el molde completo o no podés borrar piezas». Implementado: **(1) PREPARADAS**: el panel acumula las piezas (`pzPend`) con fantasma **ámbar** en el visor y ✕ para sacarlas; el molde **no se toca** hasta «Guardar», y todas entran en **UNA sola versión** (`agregar_pieza` acepta varias colocaciones por talle; `pieza_archivo` pasa a guardar con **nombre único** para que dos preparadas no se pisen). El modal de Guardar avisa que después **no se pueden borrar**. **(2) DUPLICAR POR HOMÓLOGA**: `_homologas` resuelve, por el REGISTRO, cuál es esa pieza en cada talle y copia **esa** geometría (antes copiaba la del mismo número: en un molde real «Frente 2» es la #2 en M y la #1 en el talle 0 → metía otra figura, y eso sale impreso); si la pieza no tiene nombre no hay correspondencia y se **avisa** en el panel y en la respuesta. El nombre y el número **no se heredan**. **(3) SIN DESHACER**: se eliminaron `pieza_deshacer` y el contador `piezas_agregadas` (que además contaba las versiones de «nombrar talles» y «partir por piezas» y podía borrarlas). De yapa: el alta ahora **actualiza `resumen_plantilla.json`** (riesgo 7) y el cartel del panel dice la verdad — «va a quedar como la última pieza, no le mueve el número a ninguna» (decía que corría el número a las de la derecha, que era del orden viejo por posición). **VERIFICADO**: `verificar_agregar_pieza.py` ampliado y en verde — duplicar toma la homóloga con un registro **desalineado a propósito** (`0#0 → 1#1`), 3 piezas preparadas dejan **1 sola versión** (138 → 141 contornos), y el **endpoint real** con 2 piezas en un POST deja 1 versión y en el 2º talle copia la **homóloga** (#2, ancho 609.4) y no la del mismo número (#0, ancho 496.1); además comprueba que `plantilla_pieza_deshacer` ya no existe. **Y en la UI real**: el botón de deshacer no está, «Duplicando Tapa costura — se copian sus vectores en cada talle; el nombre y el número NO se copian», el lugar se marca, el cartel dice «última pieza (35)», «Listo, prepararla» deja «1 pieza preparada · sin guardar» con su ✕ y el fantasma ámbar, y el modal de Guardar dice que no se podrá borrar. ⚠️ Trampa de la prueba: `app.test_request_context(json=…)` arma un **GET**, y `_pid_de_request` sólo mira el body en POST/PUT/… — sin `method="POST"` el endpoint contestaba «primero subí el molde».

- **2026-08-21 (266) — AUDITORÍA de «agregar una pieza»: 9 riesgos, 3 de ellos serios (anotados, no arreglados).** El usuario preguntó cómo funciona agregar una pieza y **qué bugs puede generar esa manera**. Primero se corrigió la doc, que estaba vieja: hoy la pieza se escribe **al final** del contenido de la capa y las piezas se leen en **orden de dibujo**, así que **no renumera nada** — medido con `verificar_agregar_pieza.py` sobre el molde real: **0 de 2760** entradas cambian de índice (con el orden por bbox eran 69 de 138; el mapa y el módulo seguían contando esa historia). Lo encontrado, con evidencia: **(1)** `piezas_agregadas` es el **número de versión**, no la cantidad de piezas, y la plantilla la versionan también `renombrar_capas` y `separar_por_piezas` → «Sacar la última pieza agregada» puede **borrar el renombrado de talles** y dejar el molde en «Capa 1» (demostrado con `_ver_actual`; hoy latente: los 4 moldes están en `.ver = 0`). **(2)** «Duplicar» copia `antes[t][i]` en cada talle, **asumiendo que el índice es la misma pieza en todos** — medido: «Camiseta de futbol» 0/986, pero «camiseta asque» tiene «Frente 2» como `M#2` y `0#1`, o sea que ahí duplicaría **otra pieza** en ese talle. **(3)** Deshacer restaura el registro de antes de agregar → **se pierde el nombrado hecho en el medio**. Y cinco más (contornos de más «los N más grandes» en silencio, pieza bajo el mínimo detectable, la copia idéntica que puede cruzar nombres en el emparejado, `resumen_plantilla.json` sin actualizar, multi-mesa, disco). Cada uno con su plan en §10.c («LO QUE ESTA MANERA PUEDE ROMPER»). Herramienta de la auditoría: `scratchpad/medir_duplicar.py` (sólo lectura, mide si el `pieza_idx` se corresponde entre talles en los moldes reales).

- **2026-08-21 (265) — BUG: al elegir las piezas de una variable, el visor mostraba el talle «0» y no el guía.** Reporte: «entro para seleccionar las piezas a una variable ya creada y no me sale en el visor la capa (talle) guía o el que tengo seleccionado; se ve el de más arriba, el 0». CAUSA: con una variable abierta el visor usa el **lienzo junto** (todos los talles), y `aisladoSet` lo filtra por los `pieza_idx` **del talle guía** — pero en ese lienzo los índices son un correlativo **global**, así que caen en el **bloque del primer talle**. O sea: mostraba las 11 piezas del grupo… **del talle «0»**. Y lo elegido se guardaba con `talle_origen` = el talle de `etqData` (M), es decir el índice de un talle traducido contra otro: si el orden de piezas difiere entre ellos, la variable quedaba con **piezas equivocadas** (bug de datos, no sólo visual). FIX: `_varAbierta` ahora excluye `asignandoTipo` → mientras se eligen piezas la fuente vuelve a **`etqData`** (el talle guía, o el que se elija con los chips), que es de donde salen esos índices; el **encabezado** usa la misma condición (decía «todas las tallas juntas» mostrando una sola) y `asignandoTipo` entró en las dependencias del memo. Al terminar, vuelve solo al lienzo junto para acomodar. ⚠️ **No lo introdujo el z-order de la 258** (el filtro es por índice, no por profundidad): es un bug viejo que recién ahora se reportó. **VERIFICADO en la UI real**: con «Cargar piezas» abierto, el `d` de la pieza 7 en el DOM es **idéntico** al de `GET /api/plantilla/deteccion` (talle guía **M**) y **distinto** del bloque del talle «0»; tocando el chip **XL** pasa a coincidir **exacto** con `?talle_ref=XL` y el encabezado dice «Talle: XL»; al salir vuelven las **210** piezas (7 × 30) del lienzo junto. Ver §10.c.

- **2026-08-21 (264) — Un nombre = un lugar: elegir el otro frente CAMBIA de frente (fuera el cartel).** Corrección de la 263 el mismo día. El aviso rojo («no puede ir en esta variable…») saltaba al tocar la segunda pieza del mismo nombre; el usuario lo bajó: «cuando selecciono una pieza no debe salir ese cartel; si selecciono un frente y después el otro, se deselecciona el anterior y se selecciona el nuevo. Uno u el otro». Ahora el nombre genérico funciona como un **lugar**: la pieza que entra **desplaza** a la que lo ocupaba (`_desplazadasPorNombre`), sin cartel ninguno. Si la desplazada está en un vínculo «van juntas», sale el **vínculo entero** (atómico). Las **vinculadas siguen conviviendo** aunque compartan nombre — para eso existe el vínculo. Con el **recuadro** entra **una por nombre** y **no se pisa** lo ya elegido (cambiar de pieza es tocarla). Se borraron `_choqueDeNombre` y `_avisoChoque` (el aviso naranja de choques ya guardados, para moldes viejos, queda). **VERIFICADO en la UI real** (grupo «Manga comun»): tocar «Cuello 9» → queda «Cuello 9»; tocar «Cuello 10» → queda **sólo «Cuello 10»** y **cero carteles**; con el vínculo «Frente 1 + Frente 2» creado en el grupo, tocar «Frente 1» mete **las dos** y tocar «Frente 2» **saca las dos**; el recuadro sobre las 11 piezas dejó **8** (una por nombre) respetando el «Cuello 10» ya elegido.

- **2026-08-21 (263) — «Van juntas» pasa al GRUPO, y dos piezas con el mismo nombre sólo entran juntas en una variable.** Pedido del usuario: «cuando estamos creando variables no se pueden poner 2 piezas con el mismo nombre a una misma variable a no ser que se indique que son 2 piezas que siempre van juntas; así que el botón de vincular piezas en vez de ir dentro de variable va donde configuramos el grupo, y cuando seleccionamos una de esas 2 piezas la otra se selecciona automático». Implementado tal cual: **(1)** el vínculo ahora vive en **`prod["grupos"][].juntas`** y el botón «⛓ ＋ Vincular piezas» está en el **detalle del grupo**, debajo de «Elegir piezas del grupo»; en la variable quedó la **lectura** («se definen en el grupo · Frente 1 + Frente 2 · al elegir una entra la otra sola»). **(2)** Todas las variables del grupo **heredan** el vínculo: elegir una pieza vinculada mete a las dos (`juntasDeVariable` = grupo ∪ legacy de la variante). **(3)** Regla nueva al armar la variable: si la pieza que entra se llama **igual** (nombre genérico) que una que ya está y **no** están vinculadas, **no entra y se avisa** con nombre, motivo y salida; el recuadro mete lo que puede y avisa por el resto. **(4)** Un molde configurado antes puede tener el choque ya guardado → el detalle de la variable lo **muestra** en un aviso naranja (no se toca solo). **(5)** Backend: `_traducir_prendas` arma `juntas_piezas` con las juntas del **grupo** de esa variable **más** las legacy de la variante — **compat sin migración forzada**. ⚠️ Esto **restaura una restricción que se había eliminado** en 2026-07-28 («la regla del slot»), pero **no es la misma**: aquella era automática, invisible y **descartaba piezas en silencio**; ésta la pide el usuario, es explícita, avisa, y el backend **no rechaza** nada (si rechazara, un molde viejo con el choque no se podría ni abrir para arreglarlo). **VERIFICADO**: contrato nuevo **`verificar_juntas_grupo.py`** (vínculo en el grupo → llega al motor · vínculo legacy en la variante → sigue llegando · los dos a la vez → se suman · sin vínculos → None · `POST /api/productos/grupos` conserva `juntas`), y **en la UI real** con el molde del usuario (grupo «Manga comun», 11 piezas): se creó el vínculo «Frente = Frente 1 + Frente 2» desde el grupo, en una variable nueva tocar «Frente 1» metió **las dos**, tocar «Cuello 9» y después «Cuello 10» dejó **una sola** con el aviso exacto, y el recuadro sobre las 11 piezas dejó **9** (afuera «Cuello 10» y «Cuello», los otros dos del mismo nombre). Server reiniciado por PID (17784 → nuevo) y sano.

- **2026-08-21 (262) — Acomodar una variable: mover VARIAS piezas juntas, con la misma selección del otro espacio.** Pedido: «en la parte de variable debo poder mover varias piezas a la vez usando la misma selección de arrastre que usamos en el otro espacio». Antes el visor de la variable abierta sólo dejaba arrastrar **una** pieza por vez (se movía con todos sus talles) — no había selección. Ahora (`modoAcomodoVar` = variable abierta y ninguna herramienta de asignación activa): **click** sobre una pieza la selecciona/quita **entera** (sus ~30 talles: acá el objeto es el NOMBRE, que es la unidad del `acomodo_mm`), **recuadro desde el fondo** togglea las abarcadas —expandiendo cada pieza a su nombre completo—, y **arrastrar una pieza que está en la selección mueve TODAS las seleccionadas juntas**; arrastrar una que NO está sigue moviendo sólo ésa **sin perder la selección**. Al soltar se guarda **UNA sola vez** con todos los nombres movidos (`guardarAcomodoVarMm` acepta el dict entero). Reusa `selNombrar` y `iniciarRubber` — el mismo gesto y el mismo estado que en Nombrar piezas, sin un segundo estado que pueda desincronizarse. La selección se limpia al abrir y al cerrar una variable (si no, la siguiente arrancaría con piezas marcadas que no están en el visor); lo seleccionado va en **cyan** por encima del coloreo de estado y el cursor pasa a mano. Texto de ayuda del panel actualizado. **VERIFICADO en la UI real** (variable «Cuello redondo», 7 piezas × 30 talles = 210 en el visor): click en «Frente 2» → 30 marcadas (la pieza entera); click en «Espalda 1» → 60; arrastre desde «Frente 2» → **las dos se movieron el mismo delta** y «Cuello 9» (no seleccionada) quedó quieta; **un solo POST** cuyo `acomodo_mm` trae «Frente 2» y «Espalda 1» actualizados junto a los acomodos previos; recuadro sobre todo el lienzo → toggle correcto (salieron las 2 marcadas, entraron las otras 5); y arrastrar una pieza NO seleccionada movió sólo a ella. ⚠️ Detalle de verificación: el toggle por click ocurre en el **mouseup** (`endDrag`, enganchado al `<svg>`), así que un `mouseup` sintético despachado en `window`/`document` **no** lo dispara — hay que despacharlo sobre el elemento del SVG. 📌 **Observado de paso (NO tocado)**: en esta vista los `<title>`/rótulos de las piezas que no son del talle guía dicen «Pieza #N (sin asignar)» porque `nombrePz` sale de `etqNombres` (que es de UN talle) y no de `p.name` — el dato correcto está en la pieza. Es cosmético pero confunde; arreglarlo es cambiar el fallback, con cuidado de no pintar como «ya nombradas» piezas con nombre provisorio.

- **2026-08-21 (261) — La barra de capas: el tik abre la fila, la flecha la cierra, y adentro de una capa la selección es INDIVIDUAL.** Dos pedidos. **(1)** «la flecha de expandir capa cambiala de lugar con el click de seleccionar»: la fila de la capa quedó **tik · 👁 · nombre · ▸**. Por coherencia de columnas, el tik también abre la fila de las **piezas** (tik · miniatura · nombre) y la de **«Ver piezas»** — los tres caen en la misma columna, que es lo que hace legible la selección de un vistazo. **(2)** «si selecciono la pieza Frente dentro del talle 0 se selecciona esa sola, no todos los frentes; la selección desde ahí es individual»: el **NOMBRE** de una pieza dentro de una capa dejó de elegir el grupo y ahora hace lo mismo que su tik (`togglePzSel`). Con eso `toggleGrupoNombre` quedó sin uso y **se eliminó**: el grupo (la misma pieza en todos los talles) se elige desde **«Ver piezas»**, que trabaja por nombre, y la capa entera desde su propio tik. Es la misma regla que ya rige en el visor desde la 260 — **tocar una cosa elige una cosa**. **VERIFICADO en la UI real** (molde del usuario, 30 capas × 34 piezas): orden de la fila de capa `TIK · OJO · nombre · FLECHA` y de la de pieza `TIK · MINI · nombre`; click en «Frente 1» del talle **0** → **1 seleccionada**, y en el visor es exactamente `0 / Frente 1` (antes 30, una por talle); el tik de la capa 0 sigue dando **34**; y el grupo «Frente» desde «Ver piezas» suma los **180** (6 frentes × 30 talles) — quitarlo devuelve la capa a 28/34 (parcial). ⚠️ Trampa de medición: leer `elemento.textContent` dentro del objeto que se serializa al final de una cadena de `setTimeout` devuelve el valor FINAL, no el del momento — capturar el string en una variable en cada paso.

- **2026-08-21 (260) — CLICK = una pieza · ARRASTRE = muchas + la barra de capas afinada.** Dos pedidos del usuario sobre lo de la 259. **(1) BARRA**: la fila de la CAPA **ya no muestra miniatura** («el que sostiene muchas piezas del mismo talle no muestra miniatura, sólo la capa de la pieza sola») — junta 34 figuras distintas y no identificaba nada; con ella se fue el memo `capasMini`, que existía sólo para eso. La **flecha** ▸/▾ pasó de 11×~14 px / fuente 9 a **20×22 px / fuente 15** (es el control que más se usa). Mismo criterio aplicado a «Ver piezas»: miniatura **sólo si la fila agrupa una única figura** (`_unaFigura`: «Tapa costura» = 1 pieza × 30 talles sí; «Cuello» = 11 formas distintas, no). **(2) GESTO DEL VISOR** (Moldería → Nombrar piezas): un **click sin arrastrar elige SÓLO la pieza de adelante**, sin importar cuántas tenga debajo — antes el apretón toggleaba **toda la pila** (`_piezasBajoPunto`), que en un molde anidado son 30 piezas de un saque. Eso venía de que el clic caía en la pieza equivocada (z-order invertido, arreglado en la 258): con el apilado bien, el click preciso alcanza. Varias piezas se eligen **arrastrando** y ahí sí cada punto se lleva **todo lo apilado** (respuesta explícita del usuario a la pregunta) con el **botón izquierdo**; el **derecho sigue moviendo el lienzo** (también elegido por él). ⚠️ El toggle del arrastre ahora exige `pintaSel.current.movio` (umbral de 3 px): sin eso, un temblor de 1 px devolvía el comportamiento viejo y el gesto nuevo no existía. También el click corto que entra por el fondo (`iniciarRubber`) toma `bajo[0]` en vez de la pila. **VERIFICADO en la UI real** (molde del usuario, 30 capas × 34 piezas, todos los ojitos abiertos): sobre un punto con **30 piezas apiladas**, el click dejó **1 seleccionada** y es la del talle **«0»** = la primera capa del panel, o sea la de adelante; el arrastre sobre ese mismo punto pasó a **29** (soltó la del click y se llevó el resto de la pila); flecha medida en 20×22 px y **0 miniaturas** en las filas de capa (34 al desplegar una); «Ver piezas» muestra los 8 grupos y sólo «Tapa costura» (30 = 1 × 30) lleva miniatura. Ver §10.c («EL GESTO DE SELECCIÓN EN EL VISOR»). Los changelog **198 y 200** describen el gesto anterior: quedan como historia, la regla vigente es ésta.

- **2026-08-21 (259) — La barra de capas, como el panel de capas de Illustrator: tik de selección, miniaturas y ojo general.** Pedido del usuario: «un tik estilo Illustrator que marca lo que está seleccionado y que sirva para seleccionar desde la capa; más grande; que muestre miniatura de las figuras; seleccionar y deseleccionar por grupo o unitaria; y un ojito general de mostrar/ocultar todo». Quedó (ver §10.c «LA BARRA DE CAPAS»): columna **128 → 208 px**; **encabezado** con el **ojo GENERAL** (`toggleTodasCapas`: si hay alguna capa visible las apaga TODAS —y limpia la selección, misma regla que el ojito de a una—, si estaban todas apagadas las prende) y el indicador de lo seleccionado (cantidad al nombrar, nombre de la pieza en Etiqueta); **miniatura** del contorno REAL por capa y por pieza (`MiniCapa`, memo `capasMini`: los contornos de una capa concatenados en UN solo path — cada `d` arranca con «M», así que son subtrazados válidos — con el bbox del bloque como viewBox; **es el mismo `path_svg` que dibuja el visor**, no un segundo dibujo que pueda diferir); y el **TIK** (`TikSel`) con tres estados (lleno / parcial / vacío) en cada fila. 🔴 **El tik NO tiene estado propio**: lee y escribe la selección de la pantalla (`selNombrar` al nombrar; `etqPiezaSel`+`etqPzTocada` en Etiqueta) — con estado propio, panel y visor mostrarían cosas distintas. **Qué selecciona cada cosa**: tik de la CAPA = sus piezas de una (informativo, sin click, en Etiqueta, donde la selección es de a UNA); NOMBRE de la pieza = el GRUPO (la misma pieza en todos los talles: nombre completo al nombrar, genérico en Etiqueta, que es lo que filtra ese visor); tik de la PIEZA = sólo ésa. Todo toggle. En Etiqueta el tik LLENO es la pieza dueña de la etiqueta (`etqPzTocada`) y las otras del grupo van en parcial. **Coherencia**: la lista «Ver piezas» del panel derecho (la otra lista con ojitos) recibió miniatura + tik de grupo por nombre genérico. **VERIFICADO en la UI real** con el molde del usuario (30 capas × 34 piezas = 1020) en los DOS modos: panel de 208 px con 30 miniaturas y 30 tiks; ojo general apaga (visor a 0 piezas) y prende (~470 ms); desplegar una capa da 34 miniaturas + 34 tiks unitarios; tik de capa → 34 seleccionadas y tik lleno; nombre «Frente 1» → 63 (34 + 29 frentes de las otras capas) con 29 capas en parcial y 1 llena; tik unitario «Cuello 2» → 62; volver a tocar «Frente 1» → 32; **el visor pintó exactamente esas 32** (panel y lienzo en sincronía); en Etiqueta, tik de «Espalda 3» → dueña en lleno, las otras 3 espaldas en parcial, encabezado «Espalda 3»; «Ver piezas» → «Cuello» (330 = 11 × 30). Consola sin errores de JS (sólo los 403 del propio sandbox de solo lectura). ⚠️ Trampa del entorno: con el panel del navegador oculto **`requestAnimationFrame` no corre** — medir con `setTimeout` (un rAF anidado dejó colgada la herramienta 30 s).

- **2026-08-21 (258) — El visor apila los talles como la BARRA DE CAPAS: el de más arriba, adelante.** Pedido del usuario con captura de la barra «TALLES»: «estas capas en el visor deben estar en este mismo orden; la de más arriba es la que va más hacia adelante». En SVG no hay `z-index` — manda lo último pintado — y el visor dibujaba `canvasLayout.layout` tal cual viene de `deteccion_todas` (talle por talle en el orden del panel), o sea **al revés**: el ÚLTIMO de la lista (6XL) quedaba al frente, tapando a los demás y quedándose con cada clic. En un molde ANIDADO (30 talles uno encima del otro) eso significa que el talle 0 —el de arriba de la barra, y el más chico, que queda dentro de todos— era inalcanzable. FIX en **un solo lugar**: `canvasLayout` devuelve ahora `layout` (orden LÓGICO, adelante primero → los hit-tests por bbox toman el primer match y aciertan) **y `dibujo`** (el mismo conjunto invertido por bloque de talle, `sort` estable: dentro de una capa el orden del archivo no se toca). Los **4** `.map()` de render del visor pasaron a `canvasLayout.dibujo` y `MapeadorArteVisual` dibuja con `piezasZ` (los carteles se siguen ubicando con `piezas`: el acomodo greedy depende del orden y no tenía por qué cambiar). El orden sale de `src.talles` = `_ordenar_por_archivo` = `doc.layer_ui_configs()` = el panel de capas del .ai — la misma fuente que ya ordenaba la barra, así que barra y visor no pueden divergir. **VERIFICADO en la UI real** (molde «Camiseta de futbol», 30 talles × 34 piezas, anidado, pantalla Etiqueta con la barra de capas y todos los ojitos abiertos; el visor mostraba las 330 piezas del nombre elegido —11 «Cuello» × 30 talles— porque esa pantalla filtra por la pieza que se está ubicando): el DOM se pinta `6XL → 5XL → … → 1 → 0` (el 0 último = al frente) y `document.elementsFromPoint` sobre un punto del talle 0 devuelve la pila `0, 1, 2, 4, 6, 8, 10, 12…` — exactamente el orden de la barra. ⚠️ La verificación se hizo con un **sandbox de SOLO LECTURA** en 8060 (`api_usuarios` saboteado → `/api/auth/yo` 404 → el front se saltea el login; `before_request` que corta todo método ≠ GET y `_guardar_catalogo` no-op) contra los datos reales: no se escribió un byte, y el proceso se mató por PID al terminar. Ver §10.c.

- **2026-08-21 (257) — Pedidos ya no ofrece moldes a medio configurar (el catálogo vive en la BASE y los archivos en DISCO: pueden no coincidir).** Reporte desde el VPS: aparecían moldes de una versión anterior que «no deberían mostrarse porque no están configurados». CAUSA ESTRUCTURAL: la lista de moldes y toda su config salen de `db.get_doc("catalogo")` (base), mientras que `plantilla.ai`/`arte.ai` viven en `entrada/<pid>/` (disco). Un servidor al que le restauraron la base pero no le copiaron las carpetas muestra moldes **que no existen**: el operario los elige, arma el pedido y recién ahí falla — y de paso son los 404 de `productos/<pid>/preview` («sin molde») y los 409 de `arte/preview_piezas` que se veían en la consola. FIX (front): `_moldeUsable(mid)` = tiene ARCHIVO de molde (`plantilla`) **y** al menos una pieza NOMBRADA (`piezas_nombradas`, que ya venían de `/api/productos`); filtra la grilla del catálogo y la pestaña «Mis artículos» (también su contador). **No se esconde en silencio**: si quedó alguno afuera, un aviso dice cuántos y por qué, y que se terminan en Configuración → Moldes. `variablesDisponibles` NO se filtra a propósito — lo usa `varByClave` para resolver lo que un pedido YA eligió; filtrar ahí dejaría filas huérfanas. VERIFICADO con el catálogo real del taller: los 2 moldes (19 y 34 piezas nombradas, con archivo) siguen visibles, 0 ocultos — el filtro sólo actúa donde falta algo. ⚠️ Recordatorio operativo que esto deja claro: **restaurar la base sin copiar `entrada/`+`datos/` deja el sistema incoherente**; van juntas (DESPLIEGUE.md §6).

- **2026-08-21 (256) — La actualización automática FUNCIONÓ (1.0.21), y los 500 del VPS son la BASE, no el código.** Con `KillMode=process` confirmado por el programador, el botón hizo todo solo: el VPS pasó de 1.0.20 a **1.0.21** y volvió sano (`ok:true`, `fallas:[]`) — primera actualización remota completa de punta a punta. Aparte, la consola del navegador muestra **500 en casi todo** (estado_general, catalogo_piezas, config, arte/preview_piezas) más 404/422 esperables por falta de moldes. Diagnóstico: **el chequeo `base` de `/api/salud` sólo pregunta si la base CONTESTA** (`SELECT 1`), así que una base sin las tablas nuevas da verde igual — el sistema arranca «sano» y revienta en cada pantalla. `db/schema.sql` viaja en el paquete pero **aplicarlo es un paso A MANO** (DESPLIEGUE.md §4) que nadie volvió a correr después de que el registro de piezas se mudó a MSSQL. FIX: chequeo nuevo **`esquema_base`** en `/api/salud` — saca las tablas esperadas del propio `schema.sql` (no se desactualiza) y lista las que faltan con el remedio. `critico=False` **a propósito**: el ayudante de actualizaciones usa el `ok` de esa pantalla como semáforo y una base a medias no debe disparar el rollback de una versión que está bien. Auditado para el usuario (preguntó expresamente que no borre nada): las **26 tablas** se crean con `IF OBJECT_ID(…) IS NULL`, los 2 `ALTER` están guardados por `COL_LENGTH` y son aditivos (ensanchar `pieza_talle.ancla`, agregar `producto.registro_rev` con default), y **no hay una sola sentencia `DROP`/`DELETE`/`TRUNCATE`** — re-aplicarlo es seguro. LECCIóN: un chequeo de salud que sólo verifica CONEXIÓN deja pasar el problema que importa; si el código espera un esquema, la salud tiene que mirar el esquema.

- **2026-08-21 (255) — El taller es WINDOWS y el destino LINUX: auditado el paquete que cruza, y un agujero SILENCIOSO tapado (las fuentes).** Se revisó el paquete real que manda el botón, mirado como lo abriría Linux. **Limpio** en lo estructural: 0 rutas con barra invertida, 0 rutas absolutas, 0 nombres que choquen al pasar a un sistema que distingue mayúsculas, y todos los `import` propios coinciden EXACTO con el nombre del archivo (en Windows `import Db` con `db.py` anda; en Linux no). Las 14 rutas `C:\` que quedan son de piezas que en Linux no se usan (`instalar_servidor.py`, herramientas de desarrollo) o están cubiertas por variable de entorno (`PERFILES_DIRS` → `TIZADA_PERFILES`, que el VPS tiene puesto: `/api/salud` reporta **23 perfiles, U.S. Web Coated (SWOP) v2** — la trampa §9 n°3 está resuelta allá). 🔴 **EL AGUJERO: las tipografías cargadas a mano NO viajaban.** `EXCLUIR` tenía `catalogo_fuentes/subida_*` (por «datos del usuario»), así que de las 13 fuentes del taller sólo iban las 7 de base: las 6 cargadas por el usuario — ClubAmerica, Adidas, Impact… — se quedaban acá. En el servidor publicado, un diseño que las use se estampa con el **reemplazo temporal (Anton)** y **nadie se entera hasta ver la tela impresa**: exactamente el peor error del sistema, el que sale bien impreso. Ahora viajan (son pocos KB); las que el cliente suba en el servidor no se tocan (`unzip -o` no borra lo que no está en el paquete). **Contrato nuevo `verificar_paquete_linux.py`**: audita el último zip de `dist/` (o el árbol) — separadores, rutas absolutas, choques de mayúsculas, `import` vs nombre real, que las fuentes cargadas estén, y que la pantalla compilada apunte a la dirección del destino configurado. **Visto fallar** con un paquete defectuoso: cazó la fuente faltante y la pantalla compilada para la sub-ruta. ⚠️ Dato del intento: la ruta con barra invertida **no se pudo falsear** — `zipfile` normaliza `os.sep` a `/` al escribir, o sea que nuestro empaquetador no puede generarla; la comprobación queda para paquetes armados de otra forma y así está anotada en el código. Pendiente menor: el VPS no tiene Ghostscript (`ok:false` a propósito) — sólo hace falta si un arte trae RGB.

- **2026-08-21 (254) — El sistema COMPRUEBA si puede instalarse solo, en vez de confiar en una config que no vemos.** Con `start_new_session` (253) y el drop-in `KillMode=process` puestos, el modo automático debería andar — pero «debería» no alcanza cuando equivocarse apaga un servidor de producción, y desde el taller **no hay forma de ver** el unit del VPS. Ahora se PREGUNTA: `puede_instalarse_solo()` (actualizaciones.py) corre `systemctl show -p KillMode --value <servicio>` — sólo lectura, no pide sudo — y devuelve (ok, detalle). En Windows siempre sí. **Ante la duda contesta NO** (no se pudo consultar / el servicio no contestó): mejor pedir que lo apliquen a mano que apagar producción. Se usa en tres lugares: (a) `aplicar()` se NIEGA a lanzar el ayudante si no sobreviviría — **aparca** la pendiente y escribe el porqué en `ultima.detalle`, en vez de apagar el servidor; (b) el endpoint `subir` aparca de entrada una actualización automática que ese servidor no podría aplicar y se lo dice **a quien publicó** (`aviso` en la respuesta): el paquete llega sano y queda esperando; (c) `estado()` informa `puede_solo`/`puede_solo_detalle` y la pantalla de Publicación lo muestra ANTES de elegir — verde «puede instalarse solo», ámbar con el motivo, o gris «todavía no sabe decirlo» para los servidores con versión anterior a esta comprobación. Verificado simulando los tres casos (`process` → sí; `control-group` → no, con el motivo; sin respuesta → no) y que `aplicar()` aparca en lugar de lanzar el ayudante. ⚠️ **Esta red de seguridad vive en el SERVIDOR: recién protege a partir de la versión que la trae.** El VPS corre hoy un `actualizaciones.py` híbrido (253) que no la tiene, así que **esta** actualización todavía depende de que el drop-in esté activo — se confirma en 10 segundos con `systemctl show -p KillMode tizadapro` (tiene que decir `process`) o se manda «a mano». De la siguiente en adelante, el peor caso posible es que el paquete se aparque solo. LECCIóN: cuando la seguridad depende de una config remota que no podemos ver, la salida no es documentarla mejor — es que el programa la consulte y se niegue a avanzar si no está.

- **2026-08-21 (253) — El VPS está RECUPERADO (1.0.20) y se incorpora su arreglo: el ayudante se lanza con SESIÓN PROPIA.** El programador aplicó a mano el paquete 1.0.20 (`unzip -o` + borrar `pendiente.*`/`en_curso.json` + `chown` + `systemctl start`) — verificado desde acá: `version: 1.0.20`, sin pendientes. Sus entradas 147/148 (renumeradas más abajo) traen dos cosas que HAY que tener en el repo o el próximo paquete se las pisa (el mismo accidente de la 249, tercera vez): (1) **`aplicar()` lanza el ayudante con `start_new_session=True` en Linux** — sesión propia, no le llegan las señales del grupo del servidor. Incorporado, con el porqué escrito al lado: es **la mitad** de la protección, porque **de un cgroup NO SE SALE** — la otra mitad es `KillMode=process` en el unit, que él instaló por **drop-in** (`tizadapro.service.d/kill.conf`, sin tocar el unit original: mejor que la versión que habíamos escrito, así que se adoptó su sección del §11.b entera). (2) Su **segundo incidente**, que vale como regla general y quedó en §9: al recuperar el VPS le copió por `scp` un `actualizaciones.py` VIEJO sobre el nuevo → el `servidor.py` 1.0.20 llamaba a `limpiar_si_aplicada()`, inexistente en el viejo → `AttributeError` en el arranque y systemd reintentando cada 5 s. **El sistema VIVO puede ir adelante del clon: antes de subir un archivo suelto, comparar `/api/salud → version` contra el `VERSION` local; si el vivo va adelante, el archivo bueno es el de allá y el arreglo va como PARCHE.** ⚠️ El `actualizaciones.py` que corre HOY en el VPS es un híbrido hecho a mano (su 1.0.16 + una `limpiar_si_aplicada` compatible): no tiene el aparcado de la 251 ni el campo `so`; el próximo paquete se lo reemplaza por el nuestro, que es superconjunto. **Contrato ampliado** (bloque 9): exige `start_new_session=` en `aplicar()` y que el porqué del `KillMode` esté en el código y en DESPLIEGUE.md. ⚠️ Se lo probó fallándolo y **la primera versión del bloque NO cazaba nada**: buscaba `start_new_session` a secas y el comentario que explica el porqué también la nombra — daba OK con el arreglo borrado. Ahora busca el ARGUMENTO (`start_new_session=`). Lección: un contrato que no se vio fallar no es un contrato. Además se lo endureció para que informe si falta `actualizaciones.py` en vez de morir con `ModuleNotFoundError`.

- **2026-08-21 (147 de la copia del servidor) — 🔴 LA PRIMERA ACTUALIZACIÓN REMOTA EN LINUX SE MATÓ A SÍ MISMA: el ayudante vive en el cgroup del servicio.** Se probó en producción el mecanismo de la entrada 146 (taller → VPS, paquete 1.0.20): el paquete llegó y verificó bien, el ayudante arrancó… y el log quedó **en la primera línea**, con el servicio apagado y sin volver. **Causa:** el ayudante lo lanza el propio servidor (`aplicar` en `actualizaciones.py`), así que nace **dentro del cgroup de `tizadapro.service`** — y `systemctl stop`, que el ayudante ejecuta primero (entrada 146), mata **al cgroup entero, ayudante incluido**. Como el stop fue «ordenado», systemd tampoco relanzó nada (`Restart=always` no aplica a un stop deliberado): quedó todo muerto. El truco de Windows (`DETACHED_PROCESS`) no dice nada sobre cgroups; el contrato tampoco lo podía cazar, porque verifica QUÉ comandos se mandan, no quién sobrevive a sus efectos. **Arreglo en dos mitades, las dos necesarias:** (1) `actualizaciones.aplicar` lanza el ayudante con **`start_new_session=True`** en Linux (sesión propia → no le llegan las señales del grupo del servidor); (2) el unit necesita **`KillMode=process`** — systemd mata sólo el proceso PRINCIPAL al hacer stop, no el resto del cgroup — agregado por drop-in (`tizadapro.service.d/kill.conf`, comando en `DESPLIEGUE.md` §11.b) para no tocar el unit original. Sin la (2), la (1) sola NO alcanza: la sesión nueva no saca al proceso del cgroup. **Recuperación de esa vez:** el paquete estaba sano en `_actualizacion/pendiente.zip` → se aplicó a mano (`unzip -o` + borrar `pendiente.*`/`en_curso.json` + `chown` + `systemctl start`); sin datos perdidos (el paquete no trae datos, y no llegó ni a descomprimir). **Contrato ampliado** (`verificar_actualizador_linux.py`, bloque 8): exige el `start_new_session` en `aplicar()` y que el porqué del `KillMode` esté documentado en el código y en `DESPLIEGUE.md`. ⚠️ **Archivos que hay que llevar a los DOS lados tras este cambio: `actualizaciones.py`** (al VPS para que el próximo lanzamiento del ayudante sea con sesión propia; al taller para que viaje en los paquetes futuros — `*.py` va en la lista blanca de `empaquetar.py`). ⚠️ **Lección para el mapa:** en Linux, «proceso suelto» no existe a nivel señales del servicio: lo que importa es el **cgroup**, y de un cgroup no se sale — se le dice a systemd que no lo mate entero.

- **2026-08-21 (148 de la copia del servidor) — 🔴 EL CLON LOCAL NO ES LA FUENTE DE VERDAD: el taller va ADELANTE.** Tras la recuperación de la entrada 147, el VPS entró en **loop de arranque** (`activating (auto-restart)`, systemd relanzando cada 5 s). Causa: el paquete 1.0.20 del taller dejó en el VPS su `actualizaciones.py` 1.0.20… y **se lo pisé por `scp` con el de este clon, que está en 1.0.16**. El `servidor.py` 1.0.20 llama a `limpiar_si_aplicada()` —función que en 1.0.16 no existe— y moría en el arranque con `AttributeError`. **Este repo local está en 1.0.16 (commit 730693a) y el taller publica 1.0.20**: cualquier archivo que se suba al servidor desde acá puede estar PISANDO código más nuevo. **Regla: antes de subir un archivo al VPS, comparar la versión del sistema vivo (`/api/salud` → `version`) con el `VERSION` local; si el vivo va adelante, el archivo bueno es el DEL TALLER y los arreglos se le mandan como PARCHE (diff), no como archivo entero.** Recuperación: se le agregó al `actualizaciones.py` del VPS una `limpiar_si_aplicada` compatible (si la pendiente ya es la versión que corre → `cancelar()` + borrar `en_curso`). Pendiente de fondo: que el taller aplique a SU `actualizaciones.py` el `start_new_session=True` de la entrada 147 — aunque con `KillMode=process` ya instalado en el unit, el ayudante sobrevive igual (el unit es la mitad que manda; el `start_new_session` es cinturón y tiradores). **Verificado al cierre:** `https://tizadapro.user.com.uy/api/salud` → `version: 1.0.20, ok: true, fallas: []`.

- **2026-08-21 (252) — Auditoría línea por línea de SU `servidor.py` contra el nuestro: no falta nada suyo, pero aparecieron dos features quitadas A MEDIAS.** Se compararon las **97 líneas** que tiene su copia y la nuestra no. Resultado por categoría: (a) su único arreglo propio — derivar la base del frontend de la URL — **ya estaba** (248, misma semántica); (b) su `app.secret_key` con fallback al azar: el nuestro es superconjunto (exige `TIZADA_SECRET` en publicado **y** persiste la del taller en `datos/.secret`); (c) todo el resto son versiones ANTERIORES de código que ya evolucionó — clave de caché `v7` (hoy v12), `FUENTES` pelado (hoy `_fuentes_para`), `registro_producto.json` en disco (hoy base-only), ids `pz_%04d` (hoy numéricos), y el **409 de «ya hay otra pieza llamada X»** que se sacó a propósito (los nombres repetidos están permitidos). **Conclusión: no hay nada suyo para traer.** Lo que SÍ destapó la comparación, y se limpió: (1) `subir_plantilla` seguía sacando la **foto de nombres** del molde viejo (`MP.snapshot_nombres_guia`, que **lee el molde anterior entero**) para un remapeo que ya no existe — se fue con la regla «re-subir = RESET total» (2026-08-18) —: trabajo pesado en CADA re-subida cuyo resultado se tiraba, con un comentario que prometía lo contrario («se transfieren solos»). Eliminado, con el porqué escrito en su lugar; `nombres_conservados` queda en la respuesta —siempre null— porque la pantalla ya lo contempla (`data.nombres_conservados ? … : []`) y es el enganche si alguna vez se vuelve. (2) `db.sync_piezas_molde` no la llama **nadie** desde que `guardar_registro` reconstruye `pieza`/`pieza_talle`/`variable_pieza` del molde entero (más completo: aquella sólo sincronizaba id y nombre): se le puso el aviso en el docstring para que no la reintroduzcan al ver la copia vieja del servidor, que sí la llama. LECCIóN: cuando se saca una feature, sacar también **lo que la alimentaba** — si no, queda pagando el costo sin dar el beneficio, y el comentario viejo se vuelve una mentira que el próximo lector cree. Contratos `verificar_piezas.py` y `verificar_actualizador_linux.py` en verde después de la limpieza.

- **2026-08-21 (251) — 🔴 PASÓ: la primera actualización AUTOMÁTICA al VPS dejó el servidor CAÍDO (502) — y habría entrado en BUCLE.** El usuario publicó en modo «ahora» (no «a mano»): el paquete llegó (1,59 MB, «instalando») y el servidor no volvió nunca — `/api/salud`, `/api/actualizacion/estado` y la raíz responden **502** (nginx sin nadie detrás). Es exactamente el riesgo anotado en la 250: el ayudante se lanza como HIJO del servidor (`aplicar()` → `subprocess.Popen`), o sea DENTRO del cgroup del servicio; con el `KillMode` por defecto (`control-group`) el `systemctl stop` que él mismo pide le manda SIGTERM **a él también** y muere antes de tocar un solo archivo. (Causa alternativa con el mismo síntoma: que la regla de sudoers no esté — ahí descomprime, no puede levantar nada y el rollback tampoco. Las distingue `_actualizacion/actualizador_log.txt`: si sólo tiene la línea «=== actualizando a X ===», murió en el stop.) Como el ayudante nunca llegó a respaldar ni descomprimir, **los archivos quedaron intactos en 1.0.16**: alcanza con arrancar el servicio. 🔴 **Y ahí estaba la segunda trampa, peor**: `recuperar_si_quedo_a_medias()` limpiaba `en_curso.json` pero **NO** `pendiente.json`, que seguía marcado para «ya» → al arrancar, `vigilar()` lo reaplicaba a los 5 s → el servidor se volvía a apagar **en cada arranque**: bucle de caídas sin ninguna pista. FIX: si había un intento en curso, la pendiente se **APARCA** (`cuando = MANUAL`, `aparcada: true`) — el paquete queda entero para aplicarlo a mano pero nadie lo reintenta solo, y `ultima.detalle` lo dice con esas palabras. Verificado en carpeta descartable: antes del fix la condición de `vigilar` daba True; después, False, y sigue disponible como pendiente manual. Además `/api/actualizacion/estado` ahora informa **`so`** (windows/linux) y la pantalla de Publicación **avisa en amarillo** al elegir un modo automático contra un servidor Linux («exige KillMode=process; si no, queda apagado»). ⚠️ Estos dos arreglos viajan en el paquete: en el servidor **recién rigen después** de aplicar esta versión — la recuperación de HOY es a mano (borrar `pendiente.json` antes de arrancar, o poner `KillMode=process` y dejar que termine). LECCIóN: un camino que NUNCA corrió en producción no es «automático», es un experimento; la primera vez va con red (modo «a mano»), y el botón peligroso tiene que decir por qué lo es EN la pantalla, no sólo en el chat.

- **2026-08-21 (250) — INCORPORADO del servidor: `DESPLIEGUE.md` §11.b (Linux/VPS), las 3 trampas de Linux (§9) y el changelog del 2026-08-04.** El programador pasó su `DESPLIEGUE.md` y su `MAPA_DEL_SISTEMA.md`: **su copia del MAPA es una RAMA distinta** — su changelog llega hasta la entrada 146 mientras el nuestro va por 249, y sus números 145/146 (2026-08-04, VPS Linux) **chocan** con los nuestros (2026-07-30, etiqueta y ficha técnica): son entradas distintas con el mismo número. Se incorporó lo que faltaba SIN pisar nada nuestro (comprobado: 0 líneas nuestras se perdían en `DESPLIEGUE.md`, y en el MAPA su única línea distinta de §7 era una versión VIEJA de la cascada de la etiqueta — se mantuvo la nuestra). Sus dos entradas van más abajo, renumeradas como «de la copia del servidor». **AÑADIDO POR NOSOTROS al §11.b: el requisito `KillMode=process`** — el ayudante se lanza como HIJO del servidor, o sea dentro del cgroup del servicio; con el `KillMode` por defecto (`control-group`) el `systemctl stop` que él mismo pide lo mata a él, dejando el servicio parado, los archivos a medio reemplazar y sin rollback. Esa rama **nunca corrió en producción** (ninguna actualización llegó nunca: 401 por falta de token), así que hasta confirmarlo con él la primera actualización va en modo «a mano» (247), que no usa el ayudante. **Contrato nuevo `verificar_actualizador_linux.py`** (que su entrada 146 menciona pero no existía acá): sin red ni servicios, sustituye `subprocess.run` por un espía y exige las dos ramas — es el guardián contra la regresión de la 249 (publicar desde un repo atrasado le devolvía la versión Windows-only).

- **2026-08-21 (249) — El servidor tenía código QUE EL REPO NO TENÍA: `actualizador.py` adaptado a Linux/systemd. Adoptado.** El programador mandó su `servidor.py` y su `actualizador.py`. Hallazgo: **su actualizador soporta Linux** (fechado 2026-08-04) y el nuestro era Windows-only — el repo estaba ATRASADO respecto del servidor. Su versión es un superconjunto limpio: `ES_WINDOWS = os.name == "nt"`, `SERVICIO = env TIZADA_SERVICIO or "tizadapro"`, `_systemctl(accion)` (prueba sin sudo y después con `sudo -n`, regla de sudoers acotada a start/stop/restart de esa unidad), `parar()` y `_plan_b()` por plataforma (Linux usa `restart`, que saca a la unidad de `failed`), y en `main()` un `parar()` INMEDIATO en Linux porque el unit tiene `Restart=always` (si no, el proceso vuelve a los 5 s y se descomprimiría por debajo de un servidor VIVO). Adoptada tal cual (verificado: compila, conserva la rama Windows — schtasks + arrancar.bat — y agrega la de Linux). ⚠️ **CASI LO PISAMOS**: `actualizador.py` viaja en el paquete (`INCLUIR_ARCHIVOS = ["*.py"…]`), así que publicar desde el repo le habría devuelto la versión Windows-only — y el daño aparecería recién en la actualización SIGUIENTE (la corriente ya tiene el código en memoria): servidor apagado, `schtasks` inexistente, sin arranque y **sin rollback** (el rollback también necesita poder arrancar). REGLA: antes de publicar, comparar contra lo que corre en el servidor; el repo puede estar atrás. Su `servidor.py` en cambio es la versión VIEJA (7078 líneas vs 8122): su único cambio propio era derivar la base del frontend de la URL (líneas 397/406-407) — lo mismo que se hizo hoy en la 248, con la misma semántica — y lo demás son versiones anteriores de código que ya evolucionó (clave de caché v7 vs v12, `FUENTES` pelado vs `_fuentes_para`, ids `pz_%04d`, etc.). **NO se pisó**: copiarlo habría borrado meses de trabajo. También comprobado que nuestro manejo de `TIZADA_SECRET` es superconjunto del suyo (mantiene la exigencia en publicado y además persiste la clave del taller en `datos/.secret`). ⚠️ PENDIENTE a confirmar con él antes de usar el modo AUTOMÁTICO: la rama Linux **nunca corrió en producción** (ninguna actualización llegó jamás: el token no está configurado → 401), y el ayudante se lanza como HIJO del servidor → queda en el cgroup del servicio; con el `KillMode` por defecto (`control-group`), `systemctl stop` le manda SIGTERM **también a él** y moriría a mitad del reemplazo. Preguntarle si el unit tiene `KillMode=process` (o lanzar el ayudante con `systemd-run --scope`). Mientras tanto, primera actualización en modo «a mano» (247), que no depende del ayudante. Nota: su docstring cita `DESPLIEGUE.md §11.b` (la regla de sudoers) — esa sección NO existe en nuestro DESPLIEGUE.md: la documentación del despliegue Linux vive sólo de su lado, conviene pedírsela.

- **2026-08-21 (248) — BUG ATAJADO: el paquete se compilaba SIEMPRE para `/Tizadapro/` → pantalla en blanco en el servidor nuevo.** `publicacion_publicar` corría `empaquetar.py` sin `--base`, y el default era `/Tizadapro/` (el servidor VIEJO vivía en un subdirectorio: `administracionuser.uy/Tizadapro`). El servidor nuevo (`tizadapro.user.com.uy`) sirve en la RAÍZ → al aplicar ese paquete el `index.html` habría pedido `/Tizadapro/assets/index-*.js` → 404 → pantalla en blanco, y con el sistema ya reiniciado (el peor momento para descubrirlo). FIX: la base sale de la URL del destino (`urlparse(cfg['url']).path` → `/` o `/<sub>/`) y se pasa con `--base`. Además `compilar_frontend` dejó de usar el script `build:publicado` (que tiene `--base=/Tizadapro/` HARDCODEADO en package.json y por eso ignoraba su propio argumento): ahora usa `npm run build -- --base=<base>` — npm agrega lo que va tras `--` al final del script, o sea a `vite build`. La guarda que verifica que el `index.html` quedó con el prefijo sigue en pie. VERIFICADO ejecutando `compilar_frontend` como lo hace el botón: base `/Tizadapro/` → `src="/Tizadapro/assets/…"`; base `/` → `src="/assets/…"` (idéntico a lo que sirve hoy el servidor nuevo); y el taller queda recompilado en `/`. ⚠️ También se corrigió `datos/publicacion.json`: apuntaba al servidor VIEJO — por eso «no llegaba nada». ⚠️ Ojo al publicar a un subdirectorio: `empaquetar.py` pisa `frontend/dist` (lo que sirve el taller) y lo recompila en `/` al final; si eso fallara, el taller queda pidiendo assets al prefijo y no abre. **AUDITORÍA LINUX** (el servidor nuevo corre en `/opt/tizadapro`): el núcleo es portable — `motor_pedido.py`, `piezas_molde.py` y `objetos_agregados.py` no tienen NADA de Windows, y en `servidor.py` el Job Object y demás están guardados por `os.name != "nt"` (early return). Windows-only de verdad: `actualizador.py` (schtasks + arrancar.bat), `instalar_servidor.py` y los `.bat` — por eso el modo «a mano» del 247 es la vía correcta ahí hasta adaptar el aplicador. Ver PLAN_PUBLICACION.md.

- **2026-08-21 (247) — Publicación: modo «a mano» (enviar la actualización SIN reinicio automático).** Contexto: el servidor nuevo (`tizadapro.user.com.uy`, receptor activo v1.0.16) corre en LINUX (`/opt/tizadapro`) y el aplicador automático (`actualizador.py`) es Windows-only (schtasks + arrancar.bat): el botón normal lo dejaría caído. Solución pedida: publicar el paquete y que el reinicio sea manual. Implementación — truco de compatibilidad: «a mano» = `cuando` en el año 2100 (`MANUAL = 4102444800` en actualizaciones.py), una FECHA y no un flag, así el receptor VIEJO del servidor lo entiende hoy mismo (guarda el paquete y su `vigilar` nunca llega a esa hora — cero cambios necesarios del otro lado). Piezas: (1) receptor: `estado()` marca `pendiente.manual`, `vigilar()` con guarda explícita `< MANUAL`, y `limpiar_si_aplicada(version)` al arrancar en modo publicado (si lo pendiente ya es la versión corriendo — lo aplicaron a mano y reiniciaron — se limpia solo; viaja EN este mismo paquete, así que rige desde la primera aplicación manual). (2) Pantalla Publicación: radio «a mano» + Ayuda (instrucciones: parar → descomprimir `_actualizacion/pendiente.zip` sobre la carpeta → arrancar), botón «Publicar (se aplica a mano)», la caja de pendiente distingue la manual (detecta también servidores viejos por `segundos > 10 años`). (3) La CINTA de cuenta regresiva NO aparece para una pendiente manual. VERIFICADO con test aislado del receptor: estado.manual=True, vigilar no dispara, una programada normal sí, y limpiar_si_aplicada limpia sólo con la versión ya corriendo. PENDIENTE: adaptar `actualizador.py` a Linux (relanzar vía systemctl/comando configurable) para recuperar el modo automático allá; preguntar al programador cómo corre el servicio. Ver PLAN_PUBLICACION.md.

- **2026-08-20 (246) — FIX LEY arte=tizada: el reemplazo de fuente NO llegaba a la TIZADA.** Reporte: «cambié la fuente y en la tizada no la usó». El camino real del pedido (`/api/generar` → `generar_multi` → `MP.generar_pedido_grupos(grupos, FUENTES, …)` línea ~6304) pasaba la carpeta `FUENTES` PELADA: sin las fuentes del pedido (`datos/<pid>/fuentes`) ni los reemplazos (`prod.fuentes_reemplazo`) — el visor usaba `_fuentes_para(pid)` y la tizada no. FIX en dos partes: (1) MOTOR: `generar_pedido_multi` y `generar_pedido_grupos` usan `md.get("fuentes") or carpeta_fuentes` por MOLDE (el alias es por molde: dos moldes pueden reemplazar la misma fuente distinto). (2) SERVIDOR: `molds_data` lleva `"fuentes": _fuentes_para(pid)` resuelto EN EL REQUEST — el hilo `correr()` no tiene sesión (`_get_active_producto_id()` ahí no sirve) y además así el trabajo firma la config del momento del click. Los otros caminos ya estaban bien (`generar` legacy ~5843 y ficha técnica ~5978 usan `_fuentes_para(pid)`). VERIFICADO con espía sobre `generar_pedido`: grupos y multi reciben el fx del molde ({carpetas, alias}) y sin `fuentes` cae al fallback común. ⚠️ Patrón a vigilar: cualquier config nueva POR MOLDE que afecte el estampado tiene que viajar DENTRO del dict del molde en `molds_data` (como borde_corte/etiqueta/editables) — un parámetro global de `generar_pedido_grupos` se queda corto y el visor y la tizada divergen. Ver [[arte-wysiwyg]] y la memoria fuentes-eleccion-manda.

- **2026-08-20 (245) — REGLA DEFINITIVA de fuentes (como Illustrator): la ELECCIÓN manda; toda fuente es reemplazable.** Supersede el criterio del 244 («la real le gana al alias» — duró horas). Regla del usuario: los textos de nombre/número son 100% manipulables — se puede cambiar la fuente AUNQUE esté instalada; sin cambio se respeta la original; con cambio se usa la nueva y NO vuelve sola a la original. Implementación: (1) motor `resolver_fuente`: el alias se aplica SIEMPRE primero (revertido el orden del 244). (2) `fuentes_estado`: `reemplazables` = TODAS las requeridas del arte (antes sólo las no-nativas) + mapa nuevo `originales` {fuente→interno nativo o null}; `faltantes` sigue = las que no estampan ni con reemplazo (cartel+traba). (3) VOLVER a la original, dos caminos que BORRAN el alias: elegirla en la lista (`fuente_resolver` compara la resolución nativa de `faltante` y `usar` — mismo archivo ⇒ pop, no guarda X→X) o CARGAR su archivo (tras `alta_fuente` se limpian los alias cuyo nombre original resuelve al archivo recién subido — eso es lo que el usuario esperaba ayer al subir la ClubAmerica; devuelve `alias_quitados`). (4) Front: fila «original del diseño» marcada vía `originales`; «en uso ✓» = reemplazo elegido o la original sin reemplazo. (5) Clave de caché v11→**v12** (tercera vez: cada cambio de SEMÁNTICA del resolver con los mismos insumos firmados exige bump — si no, el caché sirve renders con la regla vieja). (6) Reconciliación única con el server APAGADO (el candado del catálogo es in-process): borrado el alias ClubAmerica→CR Font del 38bc porque su subida de ayer, bajo la regla nueva, ES la elección de volver a la original. VERIFICADO: sin alias→ClubAmerica real; con alias→Impact aunque la real está; elegir-la-original→mismo archivo→alias borrado. Ver [[arte-wysiwyg]].

- **2026-08-20 (244) — FIX «cargué la fuente real y no funcionó»: el REEMPLAZO guardado le ganaba a la fuente REAL.** El usuario había elegido «CR Font 2025» como reemplazo de `ClubAmerica2021-2022`; después cargó la ClubAmerica real («Cargar y guardar» → `catalogo_fuentes/subida_ClubAmerica2021-2022.ttf`, interno «Club America 2021-2022 Regular», resuelve por nombre normalizado) — pero `resolver_fuente` aplicaba el ALIAS **antes** de buscar la original, así que seguía estampando CR Font para siempre. REGLA del usuario: el reemplazo es un fallback, no un candado — si la fuente real está (o entra después), se usa la real. FIX (motor_pedido.py `resolver_fuente` ~211): con alias presente, primero se intenta resolver el nombre ORIGINAL sin alias; sólo si no está se redirige al reemplazo. ⚠️ Clave de caché v10→**v11**: el fix cambia la SEMÁNTICA del resolver con los MISMOS insumos firmados (mismo alias, misma firma de archivos) — sin el bump, el caché habría seguido sirviendo los renders viejos con CR Font. Consistencia: `fuentes_estado` ya calculaba `reemplazables` sin alias → la fuente cargada sale sola de faltantes/reemplazables (cartel y traba se apagan). VERIFICADO con el estado real del molde 38bc: alias {ClubAmerica→CR Font} guardado y resolver devuelve `subida_ClubAmerica2021-2022.ttf` ✓. El alias queda guardado a propósito (si la fuente se borra del catálogo, vuelve el fallback). Ver [[arte-wysiwyg]].

- **2026-08-20 (243) — FIX «sigue sin mostrar la fuente que estoy eligiendo»: la clave del caché de piezas no incluía las FUENTES.** `_piezas_base_clave` (servidor.py ~3660) firmaba plantilla/arte/registro/mapeo/borde/etiqueta/editables… pero NO las fuentes: elegías un reemplazo (o cargabas la fuente real) y el server seguía sirviendo los SVG cacheados estampados con la fuente vieja — el render era correcto, el CACHÉ era el viejo. FIX: clave v9→**v10** con dos firmas nuevas: `_sha1_corto(prod.fuentes_reemplazo)` (cambiar el reemplazo regenera) y `_sha1_corto(_firma_fuentes())` (lista de (archivo, mtime) de los .ttf/.otf en `datos/productos/<pid>/fuentes` y `catalogo_fuentes/` — cargar/actualizar una fuente también regenera). VERIFICADO en sandbox con el molde real 38bc + arte refwerrf: reemplazo Bebas→preview (cache=False, ~3s), cambiar a Impact→preview REGENERA y el SVG de «Espalda 1» cambia — el diff muestra los contornos del «00» con los glifos de cada fuente. ⚠️ Trampa de la verificación: comparé primero el «Cuello» (una tira) y daba idéntico — el número no cae en esa pieza; comparar SIEMPRE una pieza donde el placeholder realmente caiga (Espalda/Frente). Y en el sandbox sin `mapeo_arte.json` el número se estampa fuera del lienzo (posición depende del mapeo): el raster se ve vacío aunque el vector esté — mirar el diff del SVG, no sólo el PNG. Ver [[arte-wysiwyg]], [[cache-preview-que-piezas]].

- **2026-08-20 (242) — Fuentes: el reemplazo se puede CAMBIAR + buscador + márgenes parejos.** (1) Reporte «quedó una predeterminada y no me deja cambiarla»: al guardar un reemplazo, la fuente dejaba de contar como `faltante` y la lista del modal quedaba DESHABILITADA. `fuentes_estado` ahora separa **`faltantes`** (sin resolver: cartel+traba) de **`reemplazables`** (las que no están nativas en el catálogo, tengan o no reemplazo): el modal habilita por reemplazables, el selector «Resolviendo» muestra `fuente → reemplazo actual`, y la fila en uso se marca «en uso como reemplazo ✓». Verificado en sandbox: reemplazo Bebas → cambiado a Impact ✓. (2) **Buscador** al lado del probador (dos inputs en fila; filtra por nombre). (3) Márgenes del modal simétricos (`maxWidth` al Modal, contenido al 100%). El early-return sin arte también manda `reemplazables`/catálogo completos.

- **2026-08-20 (241) — El modal de Fuentes muestra el catálogo COMO EN CONFIGURACIÓN + probador en vivo.** El catálogo de `fuentes_estado` ahora manda `{interno, archivo}` y cada fila del modal se dibuja con SU tipografía real (`@font-face` a `/api/fuente/archivo/<archivo>`, el mismo patrón de la pantalla de Configuración). Arriba de la lista, un campo de prueba: lo que se escribe se re-dibuja EN VIVO con cada fuente (vacío = «AaBbCc 0123456789»). Tocar una fila sigue siendo «usarla como reemplazo». Verificado el shape del endpoint en sandbox (interno+archivo); el dibujo en pantalla usa el patrón ya probado de Config (línea ~1571).

- **2026-08-20 (240) — El catálogo aparece en el modal de Fuentes + fallback TEMPORAL a Anton Regular.** (1) `fuentes_estado` devolvía `catalogo: []` en el early-return sin arte → el modal decía «el sistema no tiene fuentes»; ahora el catálogo va SIEMPRE (y abrir el modal refresca el estado). (2) Regla nueva del usuario: si la fuente del diseño NO se encuentra, el motor estampa TEMPORALMENTE con **Anton Regular** (el texto nunca desaparece ni revienta la generación con el RuntimeError viejo); en cuanto la fuente real entra al catálogo (o se elige reemplazo), el resolver la encuentra primero y Anton no se usa más. La DETECCIÓN de faltantes NO cambia (cartel+traba siguen; el cartel y el modal ahora avisan «mientras tanto se usa Anton Regular»). Verificado: `fuentes_estado` del diseño real `refwerrf` → faltantes=[ClubAmerica2021-2022] + catálogo de 12; resolver ClubAmerica=None / Anton=ruta ✓. ⚠️ El harness del sandbox copia la ESTRUCTURA de disenos/ pero no siempre los archivos (la carpeta copiada estaba vacía) — verificar el archivo antes de culpar al endpoint.

- **2026-08-20 (239) — El modal de Fuentes estaba ANIDADO dentro de otro Modal cerrado (por eso «no hacía nada») + el loop de 409 cortado + el molde real era OTRO.** (1) El ancla `{perfilUnificar && (` del 235 cayó DENTRO del `<Modal open={!!perfilUnificar}>` (era el children, no un wrapper): con perfiles cerrado, mi modal jamás se montaba — ni el fix de `open` alcanzaba. Reubicado al nivel raíz del tab pedidos. ⚠️ REGLA: tras insertar JSX por ancla, verificar EL ÁRBOL alrededor (sed ±10), no sólo que compile. (2) El loop de consola: 30 POSTs de prefetch a `preview_piezas` devolviendo 409 — ahora el 409 lleva DETALLE (`falta producto|registro (pid=…)` / `falta plantilla/arte/registro (pid, diseño)`), el front lo avisa UNA vez (`_pvErrAviso`) y el prefetch ABORTA al primer 409. (3) Contexto clave del diagnóstico: el usuario trabaja con `prod_20260820_095558_38bc` («Camiseta de futbol», creado HOY, 34 piezas, 3 diseños: csac/edwdwe/refwerrf) — no con el b30b de ayer; csac y refwerrf usan la fuente `ClubAmerica2021-2022` que SÍ FALTA en el catálogo (la detección nueva la encuentra: cartel+traba esperables ahí). (4) El harness del sandbox ahora SIEMBRA los registros reales (import del db real por ruta + `DB_SERVER` restaurado sólo para LEER; el fake sigue aislando escrituras). ⚠️ El catálogo del sandbox no trae `prod.disenos` (vive en la base real): el paso Arte completo no se reproduce ahí todavía.

- **2026-08-20 (238) — FIX: el modal de Fuentes no abría (faltaba `open`) + las fuentes REALES son las de la personalización.** (1) `Modal` exige la prop `open` — sin ella no renderiza NADA: «el botón no hace nada». ⚠️ REGLA: todo `<Modal>` nuevo lleva `open={...}`. (2) `fuentes_estado` usaba `fuentes_requeridas_arte` (capas Personalizable/Diseño) y se perdía justo las capas de CAMPO (Nombre/Número…) → ahora saca las fuentes de `extraer_personalizacion` (las que el motor estampa; fallback al método viejo). (3) Al resolver una fuente se tiran los previews y se repiden (los textos aparecen en la pieza al instante). **Verificado end-to-end en sandbox con `rangos 3.pdf`**: automapeo Espalda→mesa 5, render de la pieza con «NOMBRE» en arco (fuente Adidas), «00» y etiqueta — pixel-perfect. Dato: las fuentes del arte del usuario YA estaban en su catálogo (resolvían por nombre normalizado) — los textos no salían antes por el error `'pid' is not defined` (236) que abortaba la validación/mapeo, no por fuentes.

- **2026-08-20 (237) — Miniaturas sin placeholders + cartel de fuentes + botón «Reemplazar fuente» con el modal nuevo.** (1) Reporte: los textos «00»/«nombre» se veían en las tarjetas de la barra pero no en el molde. Las miniaturas de `detectar_arte` ahora ocultan TAMBIÉN las capas de personalización (todo lo que no es `CAPAS_GRAFICAS`: Nombre/Número/Palabra…) y la silueta `molde` — la tarjeta muestra lo que se IMPRIME. Verificado con diff de raster en la mesa 5 de `rangos 3.pdf`: 13.412 px de placeholders fuera. (2) Cartel ARRIBA del visor del Arte (prop `aviso` del mapeador): «No se encontraron las fuentes: X · Y». (3) Botón **«Reemplazar fuente»** junto a «Editar diseño» (se pinta ámbar con el conteo si hay faltantes) → modal «Fuentes»: lista de TODAS las del sistema (tocar una = usarla como reemplazo de la faltante elegida; selector si hay varias) + botón «Cargar fuente» → elegido el archivo aparecen **«Cargar y guardar»** (catálogo del sistema) y **«Cargar»** (sólo este pedido). La traba Arte→Planilla del 235 sigue. ⚠️ Verificado motor+build; el modal en pantalla queda al ojo del usuario (paso Arte con sesión).

- **2026-08-20 (236) — FIX del 235: `name 'pid' is not defined` al validar el arte.** Los dos `_fuentes_para(pid)` dentro de `_subir_arte_analizar` usaban una variable que ese scope no tiene → `_fuentes_para(None)` (resuelve el producto activo, igual que el resto de esa función). Verificado en sandbox subiendo `rangos 3.pdf`: valida sin error y responde con `rotulo`/`rango` por mesa. ⚠️ Recordatorio doble de hoy: el build NO valida identificadores — tras agregar código, grep de cada variable nueva en su scope. ⚠️ El producto ACTIVO es POR SESIÓN: curls sin cookie-jar activan en una sesión y suben en otra («primero registrá las piezas» engañoso) — para probar subidas usar `curl -c/-b` con el mismo jar.

- **2026-08-20 (235) — La tarjeta del diseño muestra el RÓTULO REAL del arte + FUENTES por pedido con traba y resolución.** (1) Reporte con captura: las tarjetas mostraban «Cuello 5 / Espalda 2» (la sugerencia por TAMAÑO) en vez de lo que dice el arte. `detectar_arte` ahora manda `rotulo` (la línea real: primero la que arranca con `#`, si no la de más letras — los placeholders 'n','o','m'… no cuentan) y la tarjeta lo muestra sin el prefijo # (el rango ya está en el desplegable). Verificado con `rangos 3.pdf`: rotulo «#4XL-6XL Manga Corta Derecha» vs sug vieja «sisa izquierda». (2) **Fuentes**: `catalogo_fuentes` acepta ruta|lista|{carpetas,alias} (las primeras carpetas PISAN); `resolver_fuente` respeta `alias` (reemplazos). `_fuentes_para(pid)` = [`datos/<pid>/fuentes`, catálogo global] + `prod.fuentes_reemplazo`; usado en TODOS los puntos que resolvían fuentes (2 validar de subida, validación cacheada, 2 generar de preview, generar real, fuente_chars). Endpoints nuevos: GET `/api/pedido/fuentes_estado` (requeridas/faltantes/catálogo/reemplazos del arte del diseño) y POST `/api/pedido/fuente_resolver` (multipart sube al `sistema` o sólo al `pedido` vía `alta_fuente`; JSON guarda reemplazo faltante→interno). FRONT: al entrar al Arte se chequea; **`irAPlanillaDesdeArte` se TRABA si hay faltantes** y abre el modal con las 3 salidas (subir y guardar en el sistema / subir sólo para este pedido / elegir una del catálogo). ⚠️ `fuentes_requeridas_arte` sólo cuenta capas Personalizable/Diseño — el texto de `guias` no exige fuente (correcto). ⚠️ El build NO valida identificadores: `pedidoProductoId` no existía y compiló igual — verificar variables nuevas con grep (era `pidCfg`).

- **2026-08-20 (234) — Sidebar afinada: 58px, iconos centrados (10px de aire por lado), menos margen contra el sistema (main padding-left 16px) y el logo SIN animación en la barra.** El icono quedaba descentrado (4/16) por el gap del flex con el span de texto oculto → `gap: 0` colapsada / `12px` abierta. El logo del login conserva su animación (sólo se quitó en la barra). Verificado en sandbox: 10/10 de margen por lado.

- **2026-08-20 (233) — La sidebar al expandirse EMPUJA el sistema (reflow proporcional).** Corrección de la 232 a pedido del usuario: fuera el margen negativo (overlay); al pasar el cursor, la barra crece 78→280 y el contenido se re-acomoda proporcionalmente (flex), todo sigue visible. Verificado en sandbox: main pasa a arrancar en x=280 con la barra abierta.

- **2026-08-20 (232) — Pedido como UN solo espacio + sidebar colapsada a iconos.** (1) El panel de Pedidos (admin) lleva la clase `pedido-unido`: los `.card` internos pierden borde/fondo/sombra/radio/padding (los recuadros parecían modales separados; ahora todo es un espacio continuo). (2) La sidebar (Pedidos/Configuración/Ayuda) queda de 78px mostrando SOLO los logos; con el cursor encima se expande a 280px POR ENCIMA del contenido (margin-right −202px = el layout no se re-acomoda) y aparecen los textos (`.sb-texto`, footer con opacidad). Verificado en sandbox: 78→280 al hover, textos ocultos/visibles, `main` clavado en x=78. ⚠️ El panel OPERARIO («/») es otro layout sin `.sidebar` — esto aplica al admin.

- **2026-08-20 (231) — La barra de Diseños del Arte (Pedidos) agrupa por el RANGO crudo de cada mesa.** Seguimiento de la 230: `nombre_detectado` es la PIEZA ya resuelta (el `#rango` se pierde en el match) → el agrupador del front nunca veía rangos. Ahora cada mesa lleva el campo `rango` (el prefijo `#…` leído del rótulo de texto o del nombre de capa, crudo) y `_rangoDe` del front lo usa primero (fallback: regex sobre el nombre). El paso Arte de Pedidos usa el mismo `MapeadorArteVisual`, así que los desplegables con el nombre del rango aparecen ahí. ⚠️ Requiere reinicio del server (motor) y que el mapeoData se re-pida (sin caché de mesas con el campo viejo… `arte_mesas` se re-arma por request).

- **2026-08-20 (230) — Arte: la detección de diseños matchea SIEMPRE por nombre GENÉRICO + barra de Diseños con desplegables por RANGO.** (1) `_match_piezas` (motor): fuera la precedencia del nombre exacto con número — «Espalda 2» en el rótulo/capa del arte cubre TODAS las espaldas (regla del usuario: el número de la pieza no importa). Los prefijos `#variante/#rango` siguen intactos (los resuelve `mapeo_variantes_arte` aparte, y `mapeo_por_nombre` ya les quitaba el `#` antes de matchear). Verificado unitario: «Espalda 2» → [Espalda 1, Espalda 2]; sin match → []. El click y el drag del front YA aplicaban por genérico (sin cambios). (2) Barra «Diseños» (`MapeadorArteVisual`): las mesas se agrupan por su RANGO (el prefijo `#…` del nombre detectado → botón desplegable CON EL NOMBRE del rango; sin prefijo → «General»); cada grupo se abre/cierra (`rangosCerrados`), un solo grupo = grilla plana como antes. La card de mesa quedó extraída en `_cardMesa` (mismo markup). ⚠️ Verificado el motor y el build; el desplegable en pantalla queda al ojo del usuario (su arte real con #rangos está tras el login).

- **2026-08-20 (229) — El cambio de borde/etiqueta se REFLEJA en el Arte + línea de referencia.** Reporte: cambió la alineación del borde y el Arte seguía mostrando el render viejo. La clave v9 del server ya incluye `borde_corte`, pero el FRONT no invalidaba: `guardarBorde` y `guardarEtiqueta` ahora hacen `_pvCache.current = {}` + `setPreviewPiezas({})` (⚠️ `{}` y no `null`: hay código que indexa el objeto) — al volver al Arte, los efectos repiden el render con la config nueva (patrón de la línea 7958, LEY arte=tizada). Además, la pieza SELECCIONADA en el Arte con render real ahora dibuja su contorno como **línea de referencia punteada finita** (trazo 1.6 dash 6-4) por ENCIMA del render: es la línea real de corte, para juzgar de qué lado cae el borde (afuera/centrado/adentro). Pendiente del ojo del usuario (sin sesión en la UI real para verificar en pantalla).

- **2026-08-20 (228) — Arte: el render real de la pieza quedaba DESFASADO del contorno (justo el ancho del borde).** Reporte con captura: al seleccionar una pieza en el paso Arte, el resaltado no coincidía con el dibujo. Causa: el preview WYSIWYG (`pv.svg`) es la PÁGINA del motor (pieza + margen del borde a cada lado, `r.width` de la page), pero el visor lo estiraba al bbox de la pieza pelada (`x={ox} width={p.pw}`) → la pieza dentro de la imagen quedaba corrida/achicada exactamente el margen. FIX en `MapeadorArteVisual`: el margen real se deriva de los datos del server (`(pv.w_cm − p.w_cm)/2` en px, ídem alto) y la imagen se ancla a `[ox−mx, oy−my, pw+2mx, ph+2my]` — sin suponer la regla del margen. ⚠️ Verificado por geometría (page-vs-bbox comprobado en el código del server: `"w": r.width` de la página); NO pude verlo en pantalla: la UI real pide login (sesión cortada por mis reinicios) y el sandbox no reproduce el estado (registro en la base real). Queda al ojo del usuario con Ctrl+F5.

- **2026-08-20 (227) — Borde de corte con ALINEACIÓN: Afuera / Centrado / Adentro.** Config nueva `borde_corte.alineacion` ('fuera' default = lo de siempre): **fuera** = trazo 2B clipado al exterior (par-impar); **centro** = trazo B sin clip (mitad y mitad); **dentro** = trazo 2B clipado al interior (`W n`) — en los tres `ancho_mm` es el ancho VISIBLE. El borde adentro/centrado se dibuja DESPUÉS del arte (si no, el diseño lo tapa); afuera mantiene el orden viejo. Motor (`_armar_base`), endpoint (`/api/productos/borde_corte` valida y persiste; default en molde sin tocar = fuera), UI (pestaña Borde: pastillas Afuera/Centrado/Adentro + «?»); el hash de `borde_corte` en las claves de caché ya cubre el campo nuevo. **Verificado a nivel de OPERADORES PDF**: los 3 streams rasterizados sobre un contorno cuadrado con línea en x=100 pintan exactamente 90→100 / 95→105 / 100→110 con ancho completo; endpoint round-trip + validación 400 en sandbox. ⚠️ Falta el ojo del usuario sobre una tizada real (el sandbox no tiene arte cargado para renderizar la pieza completa).

- **2026-08-20 (226) — Los rótulos de talle también respetan los ojitos.** Segunda parte de la 225: con talles ocultos por la barra de capas, las piezas desaparecían pero sus carteles («6XL · 34 pzas») quedaban FLOTANDO solos, «por fuera de los moldes» (captura del usuario). `_chipsSrc` ahora filtra `tallesOcultos`; combinado con el corte por anidado de la 225.

- **2026-08-20 (225) — Fuera la cascada de rótulos de talle en molde ANIDADO.** Reporte con captura («¿qué es eso?»): los carteles por bloque de talle («6XL · 34 pzas»…) caían todos casi en el mismo punto (30 bloques uno encima del otro) y formaban una cascada ilegible en la vista junta. FIX: si los dos primeros bloques se tapan más de la mitad (IoU sobre el menor > 0.5 = molde anidado), los rótulos de bloque NO se dibujan — los talles ya están en la barra de capas. En molde EXTENDIDO (bloques separados) siguen saliendo. Verificado en sandbox: 0 rótulos «pzas» con el molde real anidado.

- **2026-08-20 (224) — «Ver piezas» vuelve al PANEL (donde estaba), con filas IGUALES a las de talles.** Aclaración del usuario sobre la 222: quería que se VEA igual (fila con ojito), no que viva en la barra de capas. Quedó: botón «Ver piezas ▸» en el panel de nombrar → desplegable con una fila por nombre genérico, markup idéntico al de la barra (ojito 👁/◡ + cadena `pintaOjoPz` + nombre), max-height con scroll. La barra de capas volvió a ser solo de talles. Verificado en sandbox: barra sin sección Piezas, botón en el panel, cerrar el ojo de Frente 1020→990.

- **2026-08-20 (223) — 🔴🔴 EL MAPA SE TRUNCÓ A 0 BYTES y se reconstruyó.** Un `io.open(ruta,"w").write(...)` directo sobre este archivo: el `open("w")` TRUNCA al instante y el `.write()` explotó por surrogates (`\ud83d...` como texto en un heredoc de bash → Python lo parsea como surrogate inválido) → archivo vacío. **La MISMA secuencia que destruyó App.jsx el 2026-08-19.** Recuperación: base desde `git show HEAD:` (llegaba hasta la entrada 170 — TODO agosto estaba sin commitear), entradas 198-222 re-escritas verbatim desde el contexto de la sesión, y 171-197 como resumen reconstruido (abajo). **REGLA ABSOLUTA, sin excepciones ni para "un append chiquito": NINGÚN write programático va directo al archivo — SIEMPRE escribir a `.tmp` y `os.replace`; los emojis en scripts SIEMPRE `\U0001F441`, jamás `\ud83d\udc41`; y el MAPA se COMMITEA seguido (lo no commiteado hoy no existía en ningún lado).**

- **2026-08-20 (222) — «Ver piezas» = sección PIEZAS en la barra de capas (idéntica a los talles).** Tercera iteración del pedido: «fila» = la fila de la barra de capas. Fuera el botón y los chips del panel; la barra ahora tiene sección **Piezas** (arriba de Talles, sólo en nombrar): una fila por nombre GENÉRICO con el MISMO markup que las filas de talles — ojito 👁/◡ + nombre + arrastre en cadena sobre los ojos (`pintaOjoPz`). El filtro es `piezasOcultas` (ojo cerrado = ese nombre no se muestra); arranca con todos abiertos al entrar. Verificado en sandbox: headers Piezas/Talles, cerrar el ojo de «Frente» oculta sus 60 (2 frentes × 30 talles) y reabrirlo las devuelve.

- **2026-08-20 (221) — «Ver piezas»: chips idénticos a los botones de talles** (pastillas 4×10, 11.5/700, radio 999, wrap). Superada por la 222 (el usuario quería la BARRA, no chips).

- **2026-08-20 (220) — «Ver piezas»: botones por nombre GENÉRICO.** «Frente» agrupa Frente 1/2/3 (un botón por TIPO); el filtro matchea por `nombreGenerico`. Verificado: 3 Frentes → un chip; filtrar deja 90 de 1020.

- **2026-08-20 (219) — Nombrar: mover con la RUEDA + alinear a la MÁS GRANDE + «Ajuste avanzado» ELIMINADO (entra «Ver piezas»).** (1) Botón del medio (rueda apretada) sobre una pieza = mover la SELECCIÓN libremente por el visor, directo sin timer (`startDrag` botón 1, `noToggle`). (2) `alinearSeleccion`: la referencia es la pieza MÁS GRANDE de la selección (por área) — queda quieta y el resto se alinea a sus bordes/centros, como el objeto clave de Illustrator. (3) «Ajuste avanzado ▸» eliminado COMPLETO: la rama JSX entera y las funciones muertas `cambiarVistaEmp`/`aplicarEmparejado`/`soltarPiezaEmp`/`resetAcomodoEmp`; `empVista` fijo en 'simple'. ⚠️ NO se tocó el flujo de respaldo de a un talle (`!empTodas`, chips «Viendo» + fijarPiezaEmp/abrirTalleEmp/_postEmparejado): nombra cuando el lienzo junto no está (multi-mesa) — no era el Ajuste avanzado. Verificado en sandbox: alinear-izquierda deja la grande quieta y la chica clavada a su borde; la rueda mueve.

- **2026-08-20 (218) — Barra de alineación estilo Illustrator en Nombrar (6 modos).** Reemplaza «Centrar ↔/↕»: izquierda / centro horizontal / derecha / arriba / centro vertical / abajo, íconos como Illustrator (barra de referencia + dos bloques, SVG inline `currentColor`), tooltip + «?». `alinearSeleccion(modo)` sobre `pzOffsets` (visual). Verificado: 61 contornos al MISMO píxel. ⚠️ Para verificar alineación medir el `path` del contorno, no el `<g>` (el badge sobresale ~3px).

- **2026-08-20 (217) — Los «?» resaltan en cyan + fuera el acordeón «Nombrar talles» resuelto.** (1) `Ayuda` siempre con acento (borde+texto cyan, fondo suave). (2) `NombrarVariantes` no se muestra con talles resueltos (corregir nombres vive en la barra de capas, doble click); sigue cuando FALTA nombrar. ⚠️ El primer intento puso `return null` ANTES de dos `useEffect` → violación de reglas de hooks; va SIEMPRE después de todos los hooks.

- **2026-08-20 (216) — Label definitivo: «Aplicar a todas».** Criterio del usuario (ejemplo «Exportar»): el label debe ser un VERBO/expresión universal que ya traiga el significado (PowerPoint usa exactamente «Aplicar a todas»). Memoria `botones-texto-corto`: buscar SIEMPRE la palabra que la gente ya conoce de otras apps.

- **2026-08-20 (215) — «Todas juntas» (rechazada después).** Iteración intermedia del label.

- **2026-08-20 (214) — «Acomodar en todas las piezas del mismo nombre» (rechazada: muy larga).** Matiz de la regla: corto pero autoexplicativo; nada de jerga de instructor (Sincronizar/Vincular rechazadas).

- **2026-08-20 (213) — REGLA UI: botones con texto CORTO; la explicación profunda al «?».** Regla permanente (memoria `botones-texto-corto`). Barrido de 8 controles/encabezados: interruptor de etiqueta, Probar planilla, Usuarios y permisos, Moldería (grilla), tip de Shift en telas, Plantillas de Planilla, Reglas de planilla, Plantillas de nesting.

- **2026-08-20 (212) — Los textos explicativos de la UI pasaron a botones «?» (Ayuda).** 33 bloques convertidos (transformador sobre App.jsx): párrafos, cajitas con ícono y sub-labels → `<Ayuda ancho={330}>` junto a su espacio; encabezados «Título · explicación» conservan el título. NO convertidos: toasts, empty-states y ESTADO DINÁMICO (contadores) — feedback vivo queda visible. ⚠️ Lecciones: encabezados con «·» pierden el título si se convierte el div entero; contenido que arranca en `{` = estado dinámico; un `<Ayuda>` anidado rompe el reemplazo por rangos (quedó un `</Ayuda>` huérfano); compilar SIEMPRE tras un splice.

- **2026-08-20 (211) — Etiqueta con la BARRA DE CAPAS de talles (idéntica a Nombrar).** Fuera la tira de chips «Variante:»; Etiqueta usa el lienzo TODAS con la misma barra (ojito + cadena + doble click renombra) y arranca mostrando SÓLO la guía (`_etqCapasInit` oculta el resto una vez por entrada). `nombrePc` prioriza `p.name` (en TODAS el idx es global: `etqNombres[idx]` cruzaba nombres); activar Nombrar resetea `tallesOcultos`. ⚠️ El ojo cerrado es «◡» (no 👁).

- **2026-08-20 (210) — Etiqueta: la lista NO desaparece más + «Igualar» como MODO en tiempo real.** (1) El POST `/api/productos/etiqueta` devolvía la config SIN `piezas`/`piezas_gen` y el front la pisaba → lista vacía tras guardar. Fix doble: el POST devuelve la lista (como el GET) y el front hace merge defensivo. (2) El «= todas» de un disparo → INTERRUPTOR: activo, marcar posición o alineación se aplica a TODAS las del mismo nombre EN EL GESTO; apagado, cada pieza la suya. Se revirtió la sub-lista del 209. ⚠️ El reemplazo por índice de un map JSX corta en el PRIMER `})}`.

- **2026-08-20 (209) — Etiqueta: lista por pieza real (superada por la 210).**

- **2026-08-20 (208) — Etiqueta: botón «= todas» (superado por el interruptor de la 210).** POST directo con el objeto nuevo — no `guardarEtiqueta()` que leería estado viejo.

- **2026-08-20 (207) — Etiqueta: se trabaja SOLO sobre el talle GUÍA.** El visor de Etiqueta usa la detección de la guía; al entrar re-planta en la guía; aviso nuevo. La POSICIÓN no cambió (de la pieza, relativa al contorno, `t` 0..1). (La 211 después le sumó la barra de capas con el resto oculto.)

- **2026-08-20 (206) — Cartel honesto mientras se abre el lienzo de Nombrar.** `empTodasCargando` + overlay spinner «Abriendo los N talles…». ⚠️ NO existe `@keyframes spin` en el proyecto (varios spinners inline NO giran): el real es `perfilSpin` (index.css:208).

- **2026-08-20 (205) — Nombrar piezas RÁPIDO (guardar ~15-20s → ~3s · lienzo ~12s → ~1-4s) + tinte verde a las nombradas.** Medido con el archivo real (34 piezas × 30 talles): cada guardado re-parseaba TODO (detectar_piezas ~1,8s + extraer×30 ~12,7s + ~1000 INSERTs de a uno). Fixes: (1) caché en memoria de `extraer_piezas_mesa` por (archivo, mtime, mesa, talle) — shadow del import en motor_pedido, DEEPCOPY al devolver (los llamadores anotan sobre las piezas), cap 3 archivos → alta 12,7s→0,7s; (2) ídem `detectar_piezas` (`_DET_CACHE`, impl en `_detectar_piezas_impl`); (3) `_prewarm_deteccion_todas(pid)` en hilo daemon al final de `subir_plantilla`; (4) `db.guardar_registro`: pieza_talle EN LOTE (`fast_executemany`) → 0,1s, verificado en base descartable con NVARCHAR(MAX); (5) piezas con nombre de USUARIO en verde sutil `rgba(16,185,129,0.14)` (provisorias neutras). ⚠️ El caché devuelve COPIAS, nunca la referencia interna.

- **2026-08-20 (204) — Acomodar piezas en la VARIABLE abierta, GUARDADO.** Arrastrar mueve la pieza con TODOS sus talles juntos y al soltar queda en `variantes[].acomodo_mm = {nombre:{x,y}}` (mm del lienzo; clave separada del `acomodo` viejo del nido — otra escala). Al reabrir se re-aplica (efecto siembra `pzOffsets` y limpia al salir); «Ver variante» (`varianteFiltro`) también lo aplica — la regla «no se reacomoda NUNCA» sigue: el único acomodo es el del usuario. El renombre arrastra `acomodo_mm` y el `acomodo` legacy (`_migrar_nombres_pieza`). ⚠️ Dispatch sintético acá: apuntar al `path` (elementFromPoint a 0.3% devuelve overlays).

- **2026-08-20 (203) — Salir de Nombrar «para atrás» dejaba el visor con TODOS los talles.** «⬅ Volver a ajustes» sólo cambiaba pestaña: `empModo && empTodas` vivos. FIX: efecto sobre `tabAjustesMolde` — modo abierto y pestaña ≠ molderia → `activarEmparejar(false)` (restaura la guía). Verificado: 380 → 19.

- **2026-08-19 (202) — Selección por FORMA REAL + grupo desde el desplegable + el renombre ARRASTRA las configs.** (1) Hit-test por BBOX agarraba piezas vecinas (20 vs 13-14 reales) → `_piezasBajoPunto` usa `document.elementsFromPoint` (pila entera por TRAZADO, tapadas incluidas), bbox de fallback. (2) `seleccionarGrupoTodas` había quedado huérfana → click en pieza NOMBRADA del desplegable selecciona el grupo entero y precarga el input. (3) `_migrar_nombres_pieza(pid, ren)`: el renombre (explícito o el implícito del desambiguado) arrastra **etiqueta** (`prod.etiqueta.posiciones`), **telas por pieza** (`telas_cfg.por_pieza`) y **mapeo del arte** (fijo + `mapeo_arte.json` por diseño); si el nombre nuevo ya tenía config, ésa gana. Coherencia del resto: variables por pieza_id ✓, toggles por genérico ✓, cachés por registro_rev ✓. ⚠️ `/api/config` NO persiste `telas_cfg` (va por `/api/productos/telas_asignadas`).

- **2026-08-19 (201) — Recuadro de selección con toggle + FIX 547 (proyección por UPSERT).** (1) Gesto v7: desde el FONDO se dibuja el RECUADRO (marquee) y al soltar TODO lo abarcado se invierte según su estado; click corto en fondo togglea lo apilado bajo el punto. (2) Error 547 (`DELETE ... conflicted with FK pieza_talle.talle_id`): `_proyectar_un_producto` hacía DELETE+recrear de talles/variables/diseños EN CADA GUARDADO de config — con el registro en la base, `pieza_talle` referencia esos talles → 500; y recrear cambiaba ids dejando `mapeo_arte`/`editable`/`pedido_fila` colgados. **Reescrito a UPSERT por clave natural** (talle.nombre/variable.clave/diseno.nombre): ids estables; lo que la config ya no tiene se borra limpiando referencias (pedido_fila queda NULL); un talle con geometría NUNCA se borra por config. ⚠️ Dentro de `with cursor()` NO llamar `valor()` (abre OTRA conexión y espera los locks propios). Verificado en base descartable `TizadaVerif547`.

- **2026-08-19 (200) — Nombrar: gesto desde el fondo + nombres repetidos PERMITIDOS + 3 bugs.** (1) Gesto v6 (superado por v7). (2) Fuera el 409 «ya hay otra pieza llamada X» de `grupo_pieza` (la identidad es el ID; además rompía el nombrado en cadena); `nombres_normalizados` desambigua la clave interna (Frente→Frente 1/2) sin tocar únicos. (3) **El ancla no se escribía nunca** sin `variante_guia` → el renombrado implícito CAMBIABA el id (1→20). Fix en `_regenerar_piezas_index`: fallback a cualquier talle del registro con `pieza_idx`. (4) Tras nombrar, la vista de capas caía al talle suelto: `crearGrupoTodas` ahora recarga con `await cargarTodasVariantes(empData)`. (5) Rótulo NaN (`empTodasInfo` existe con data null; fallback `p.t_idx ?? p.idx`). (6) Ocultar capa (ojito) deselecciona sus piezas.

- **2026-08-19 (199) — Selección al nombrar = TOGGLE estilo Illustrator (v5).** Arrastrar invierte TODO lo que pasa bajo el cursor — apilado incluido — una vez por arrastre (set `tocadas`); sin modos; MOVER = quieto TOTAL 350 ms (agarre revierte el toggle del apretón, `noToggle`). Además ocultar capa deselecciona. ⚠️ El texto «Nombrar piezas» aparece en los carteles de TODAS las tarjetas bloqueadas — matchear `^Nombrar piezas$`. ⚠️ `cat >>` a un script DESPUÉS del print/os.replace no escribe nada.

- **2026-08-19 (198) — Deseleccionar, CUARTA iteración y la buena: el problema era el MOLDE ANIDADO (hit-testing).** v1 cruce imposible (la pieza arrastrada tapa); v2 timer; v3 patrón telas PERO por `data-piece` = la pieza DE ARRIBA — en molde anidado la seleccionada casi nunca es la top. FIX v4: deselección GEOMÉTRICA (`_seleccionadasBajo`). Verificado con el escenario real (34→31). ⚠️ Para gestos el target lo decide `elementFromPoint`; un dispatch dirigido valida código, no gestos.

- **2026-08-18/19 (171-197) — 🔧 RECONSTRUIDO (el detalle textual se perdió con el truncado; fuentes: memorias + resumen de sesión).** Lo que entró en ese rango: **etiqueta POR PIEZA** (lista de piezas a la derecha, visor con la pieza en todos sus talles, posición por pieza para todo el molde, claves por nombre completo, migración de claves viejas obligatoria); **variables SIN reacomodo automático** (regla 2026-08-18: mostrar tal cual el archivo; nada de grillas ni nido); **emparejado por SOLAPE, nunca por tamaño** (índice si igual conteo; IoU si no); **se cargan TODAS las piezas** (sin filtro de nombre ni tamaño mínimo — «no importa si miden menos de 1 cm»; nombres de objetos del archivo IGNORADOS, sólo el talle); **re-subir/borrar molde = RESET total** (registro, variables, emparejado; ids arrancan en 1); **aviso de talles incompletos** con «cargar sin esos talles» (`excluir_talles`, changelog 179); **ids NUMÉRICOS secuenciales por molde** + `piezas.json` (id/clave/nombre/numero/ancla; el id NO sigue al nombre — ancla por posición, no por geometría: las espejadas colisionan 94/137); **registro migrado a MSSQL base-only** (`_guardar_registro`/`_cargar` interceptados, `_REG_DB_CACHE` por `registro_rev`, sin espejo JSON; tablas producto/pieza UNIQUE(producto_id,id_en_molde)/pieza_talle CASCADE); **gate global** hasta nombrar piezas (todas las tarjetas deshabilitadas); **rediseño de Nombrar**: barra de capas de talles FUERA del visor (ojito + cadena + desplegable + doble click renombra), panel mínimo (input + ✓ + contador + alinear), sin colores de propuesta; **gestos v1-v3** del deseleccionar (el arco completo quedó en la 198); **App.jsx TRUNCADO y reconstruido** (2026-08-19: write sin tmp con surrogates — nació la regla del `.tmp` + `os.replace`); detección: las 4 tiras que no aparecían eran polilíneas ABIERTAS sin unir en el .ai (Ctrl+J del usuario las arregló — el PDF interno no las exportaba).

- **2026-08-04 (146 de la copia del servidor) — LAS ACTUALIZACIONES REMOTAS AHORA FUNCIONAN EN LINUX (systemd), no sólo en Windows.** El mecanismo de publicar (§entrada 145 y `PLAN_PUBLICACION.md`) estaba **entero atado a Windows** y en el VPS habría dejado el sistema caído: `actualizador.py` levantaba el servidor con `schtasks /run /tn "TIZADA PRO"` **sin condicionar por sistema operativo** (y `arrancar.bat` como plan B). En Linux eso no existe → el ayudante descomprimía bien y después **no sabía levantar nada**; y como el ROLLBACK también arranca por ahí, no volvía **ni la versión nueva ni la anterior**. Verificado que no había una sola aparición de `systemctl` en todo el repo. **Cambios en `actualizador.py`:** constantes `ES_WINDOWS` y **`SERVICIO`** (env `TIZADA_SERVICIO`, default `tizadapro`); `_systemctl(accion)` que prueba **primero sin sudo y después con `sudo -n`** (el sistema NO corre como root a propósito: usuario `tizada` sin shell) y **loguea si falla**, en vez de morir en silencio; `parar()` nuevo (schtasks `/end` en Windows, `systemctl stop` en Linux) reemplaza las **tres** llamadas sueltas a `schtasks`; `_lanzar_bat` pasa a `_plan_b`, que en Linux es `systemctl restart` — a propósito **restart y no start**, porque un `start` sobre una unidad en estado `failed` no siempre arranca. 🔴 **La trampa que no era obvia:** en Linux hay que **parar el SERVICIO antes de esperar el apagado**. El unit tiene `Restart=always`, así que el proceso que se apaga solo **vuelve en 5 s** y el ayudante terminaría descomprimiendo por debajo de un servidor vivo, que encima seguiría con el código viejo en memoria. En Windows no hace falta (la tarea es «al iniciar el sistema» y no relanza sola), así que ese camino **no se tocó**. 🔴 **Y un SEGUNDO bug que rompía igual, encontrado de paso:** `publicacion_publicar` corría `empaquetar.py` **sin argumentos**, y ese script compila la pantalla para la sub-ruta histórica `/Tizadapro/`. Publicando a un **subdominio** (el VPS nuevo) todos los assets daban **404**: pantalla en blanco **con el servidor sano**, que es lo peor de diagnosticar. Ahora el prefijo **se deduce de la URL de destino** (`urlparse(cfg["url"]).path`), así que no hay nada nuevo que configurar y el caso sub-ruta sigue idéntico. **Falta del lado del servidor (una vez):** una regla de sudoers acotada a `start`/`stop`/`restart` de esa única unidad — sin eso el rollback no puede levantar nada (comando en `DESPLIEGUE.md` §11.b). ⚠️ **Mientras `TIZADA_TOKEN_ACT` no esté configurado en el VPS, el endpoint responde 401 y el servidor está a salvo: ese 401 es la red de seguridad, no un problema.** **Contrato nuevo: `verificar_actualizador_linux.py`** (7 bloques, sin red ni servicios: sustituye `subprocess.run` por un espía). **Se lo vio fallar** reponiendo el `schtasks` incondicional en `parar()`: cazó la regresión en 4 aserciones, incluida la que exige que no quede ninguna llamada a `schtasks` fuera de una rama `ES_WINDOWS`.

- **2026-08-04 (145 de la copia del servidor) — EL SISTEMA CORRE EN UN VPS **LINUX**, en `https://tizadapro.user.com.uy`.** Hasta acá el despliegue era Windows Server (`DESPLIEGUE.md`, `INSTALAR.bat`, `publicado.bat`, tarea programada, IIS). Ahora hay un segundo destino real: **Ubuntu 24.04**, 4 núcleos / 16 GB, que ya hospedaba otros sistemas del usuario (Chatwoot y su Postgres, y un **SQL Server 2022 en Docker** publicado en `127.0.0.1:1433`). **Nada del código Python hubo que tocar** — corre igual — pero **todo el envoltorio de arranque es de Windows y no sirve**: en su lugar va un **servicio systemd** (`/etc/systemd/system/tizadapro.service`, `EnvironmentFile=/opt/tizadapro/tizada.env`, `Restart=always`, usuario **`tizada`** sin shell en vez de root) y **nginx** como proxy con certificado de Let's Encrypt. **Decisión: SUBDOMINIO, no sub-ruta** — con subdominio se usa el build por defecto (`npm run build`, base `/`) y el nginx es un `proxy_pass` y nada más; la sub-ruta obliga a `TIZADA_BASE=/Tizadapro/` al compilar y a reescribir rutas, que es de donde salen los assets que no cargan. **Tres cosas que mordieron, todas documentadas en §9 y acá:** (1) 🔴 **`localhost` en Ubuntu resuelve a `::1`** y el SQL de Docker escucha sólo IPv4 → `Login timeout expired`; se arregla con `TIZADA_DB_SERVER=127.0.0.1,1433` (la IP literal, nunca el nombre). (2) 🔴 **`PERFILES_DIRS` sólo tiene rutas de Windows** → 0 perfiles ICC y `/api/salud` en rojo; hubo que copiar los 23 `.icc/.icm` de Adobe del taller (`C:\Program Files (x86)\Common Files\Adobe\Color\Profiles\Recommended`, 6,8 MB comprimidos) a `/opt/tizadapro/perfiles_icc` y apuntar **`TIZADA_PERFILES`**. (3) `npm ci` falla por un conflicto de peers **del propio `package.json`** (`@eslint/js@^10` contra `eslint@^9`): se instala con `--legacy-peer-deps`; eslint no participa del build, así que el bundle sale idéntico. ⏳ **Queda pendiente arreglar ese conflicto en `frontend/package.json`** (bajar `@eslint/js` a `^9` y regenerar el lockfile), para no depender del flag. **Nginx, los tres valores que NO son adorno:** `client_max_body_size 512M` (los `.ai` y los moldes son grandes; sin esto los rechaza), `proxy_read_timeout/send_timeout 900s` (generar una tizada tarda minutos → si no, **504**) y `proxy_buffering off` (las descargas de PDF grandes, el mismo problema que ya dio `ERR_QUIC_PROTOCOL_ERROR` en la entrada 143). **`TIZADA_PROCESOS=3`** a propósito: cada proceso de render pesa ~200 MB y la máquina es compartida con los otros sistemas. **Verificado desde internet:** `GET https://tizadapro.user.com.uy/api/salud` → `"ok": true`, `"fallas": []`, `"modo": "publicado"` (waitress), base respondiendo y `frontend_compilado: al día`. `ghostscript` queda en `ok:false` **a propósito** (no crítico: sólo se usa si el arte trae RGB). ⚠️ **Y una advertencia operativa:** el VPS **NO tiene los datos** — `datos/`, `entrada/` y `catalogo_fuentes/` no viajan por git; hay que copiarlos aparte (§ `DESPLIEGUE.md` punto 6) o el sistema arranca sano pero **vacío**.

- **2026-07-31 (170) — 🔴 Los procesos de dibujo ya NO sobreviven al servidor (la máquina se iba poniendo lenta sin motivo aparente).** Reporte del usuario: *«¿por qué tarda 6 minutos algo que antes tardaba 3?»*. **La comparación etapa por etapa del MISMO pedido (38 prendas, mismas hojas) mostró TODO al doble** —armar la 1ª hoja 38 s→98 s, la 2ª 61 s→146 s, el RIP 112 s→237 s—, y que todo escale por igual no es una función rota: es la máquina a media velocidad. **Causa:** procesos huérfanos. Windows no mata a los hijos cuando muere el padre, así que **cada reinicio del servidor dejaba ~6 procesos de dibujo sueltos (~1 GB)**, y se acumulaban (llegó a 86 procesos / 4,8 GB, mitad de mis sandboxes de prueba y mitad de reinicios). Ya había pasado antes («2,87 GB de workers zombis»). **FIX definitivo:** `_atar_hijos_a_este_proceso()` en el arranque — un **Job Object de Windows con `KILL_ON_JOB_CLOSE`** al que se asigna el propio servidor; todo lo que cree lo hereda, así que al apagarlo (o matarlo) el sistema se lleva a sus hijos. Si no se puede, avisa por consola en vez de fallar callado. ⚠️ **Trampa de ctypes:** sin declarar `restype`/`argtypes` el HANDLE se trunca en 64 bits y **falla en silencio** — la primera versión "funcionaba" y el hijo sobrevivía igual; probado con un padre que se mata con `kill -9`. **REGLA: no correr cargas pesadas en la máquina del usuario mientras trabaja, y limpiar los procesos al terminar.**

- **2026-07-31 (169) — 🔴 REVERTIDO: la cola general de trabajo pesado (168.b) rompió la TIZADA.** Con la cola puesta, el usuario vio la ventana de «Armando la tizada» **clavada en "página 4 de 4 · 100%" a los 4:37**, con diseños simples, y mientras tanto el cartel «Dibujando el talle M». Se revirtió TODO eso en el acto: `_PIEZAS_BASE_LOCK` vuelve a ser `Lock` y a cubrir SOLO el armado de piezas del visor; `subir_arte`, `_deteccion_cache` y `arte_mesa_img` **ya no lo toman**; se quitó `_precalentar_pool()` (levantaba 6 procesos en cada subida, que competían con el ProcessPool que usa el aplanado para el RIP). **REGLA que queda: la generación de la tizada tiene que poder avanzar SIEMPRE; nunca se la puede dejar detrás de un lock que también usa el visor.** En su lugar, prioridad al revés y sin locks: mientras el trabajo está en `generando`/`en cola`, **el visor no pide dibujos** (`_tizadaEnCurso` corta los dos efectos de `cargarPreviewPiezas`; al terminar vuelven solos porque está en las dependencias). ⚠️ Además: mis propias verificaciones dejaron **86 procesos Python huérfanos (4,8 GB)** corriendo en la máquina del usuario — cada sandbox/medición crea su pool y no lo cierra. Eso solo ya explica que todo fuera más lento. **No correr cargas pesadas en la máquina del usuario mientras trabaja, y limpiar siempre los procesos al terminar.**

- **2026-07-31 (168) — Dos diseños pesados a la vez trababan todo + el reinicio deslogueaba (401).** ⚠️ **La parte (b) de esta entrada quedó REVERTIDA — ver (169).** Reporte del usuario: *«cuando cargo un segundo diseño pesado a otro diseño se tranca y no sube más, se congela el sistema»*, con `401 (UNAUTHORIZED)` en `api/telas` y `api/productos/activar`. **(a) Los 401 eran del reinicio del servidor:** `app.secret_key` se generaba AL AZAR en cada arranque, así que cualquier reinicio cerraba la sesión de todos (en pleno trabajo, sin explicación). Ahora, si no hay `TIZADA_SECRET`, la clave se guarda en `datos/.secret` (gitignoreado, no se publica) y sobrevive al reinicio — verificado recargando el módulo. En PUBLICADO sigue siendo obligatorio el env. **(b) El «se traba» NO era un deadlock sino SATURACIÓN, y encima un riesgo real:** subir un arte usa PyMuPDF **en el hilo del request** (`arte_es_separado`, `detectar_arte`, `mapeo_por_nombre`, `extraer_personalizacion`, `validar_arte_separado`) mientras otro hilo podía estar armando piezas — dos usos simultáneos de PyMuPDF en el mismo proceso, justo lo que la regla del proyecto prohíbe (no es thread-safe). REPRODUCIDO (`scratchpad/repro_dos_artes.py`: subir arte A + dibujar piezas + subir arte B en paralelo): nada se colgaba pero todo se peleaba la CPU — **subir pasaba de 7 s a 26,5 s**. FIX: `_PIEZAS_BASE_LOCK` pasa a `RLock` y lo toman TODAS las operaciones pesadas del proceso principal (subida, `detectar_arte`, `get_svg_image` de una mesa, armado de piezas) → hacen cola de a una. **MEDIDO después:** total 33,0 s → **26,5 s**, subir 26,5 s → **17,9 s**, dibujar piezas 30,4 s → 22,5 s, cero pedidos colgados. ⚠️ El lock NO alcanza al ProcessPool (cada worker es otro proceso: ahí el paralelismo es válido y necesario). **(c) «Las piezas solas tardan»:** medido, `_deteccion_base_cached` responde en **0,14 s** la primera vez y 0,00 s después — no era eso: era la competencia con el dibujado de los 20 talles, que se sacó en (167).

- **2026-07-31 (167) — 🔴 REGLA: siempre el VECTOR original + se dibuja sólo el talle que se mira.** Regla que fijó el usuario y que queda por encima de cualquier optimización: *«que no se puede cambiar el archivo real ni hacerlo pixel ni nada, siempre se trabajará con los vectores profesionales originales, y el único pixel si viene una imagen incrustada en el archivo»*. Está en `CLAUDE.md` como LEY. Si algo va lento, la salida es **hacer menos trabajo**, nunca bajar la calidad. **Cambio de estructura (idea del usuario):** al cargar el arte se dibujaba el render real de **los 20 talles** (`asignarTodasLasVariantes`) = 8 piezas × 20 = 160 recortes del vector → ~60 s antes de ver NADA. Ahora se dibuja **sólo el talle guía** (`/api/arte/asignar_todo` acepta `talles:[...]`) y **cada talle se dibuja cuando se lo toca** y queda en el caché (`verVarianteOperario` llama `asignarTodasLasVariantes(mapeo, pid, [talle])`, así el cambio de talle también muestra avance real en vez de un cartel mudo). **MEDIDO** (arte de 8,4 MB): 60-67 s → **17,8 s** el talle guía (y ~13 s en el flujo real, porque los procesos ya arrancaron durante la subida). **La TIZADA no se toca ni depende de esto:** `generar_pedido` arma cada pieza que necesita con `_armar_base` y su propio caché en memoria — `piezas_cache/` en disco es sólo del visor. Contra qué medir: `scratchpad/medir_asignar.py`. **Había DOS mecanismos de pre-dibujado y hubo que desactivar los dos:** el bloqueante (`asignarTodasLasVariantes`) y **`_prefetchTalles`**, que en segundo plano seguía pidiendo el render de TODOS los talles uno por uno (por eso la máquina seguía trabajando aunque el cartel dijera «listo»); ahora ese prefetch sólo trae la GEOMETRÍA de cada talle, que es barata. ⚠️ **Dos trampas al hacerlo:** (1) enganchar el dibujo del talle nuevo en `verVarianteOperario` hacía que el MISMO talle se generara dos veces a la vez (el job + `cargarPreviewPiezas`), pisándose los archivos y tardando el doble → el dibujo tiene UNA sola vía (`cargarPreviewPiezas`) y el aviso va aparte (`dibujandoTalle`, que aparece recién a los 0,9 s para no parpadear); (2) el contador de piezas de un job de UN talle miraba la carpeta de toda la variable y sumaba lo que hacían otras pasadas → apunta a la carpeta del talle.

- **2026-07-31 (166) — «Asignando el diseño a cada variante…» dejaba de moverse: ahora muestra lo que REALMENTE está pasando.** Reporte del usuario (con captura): el cartel quedaba en **«· 0/20» quieto un buen rato** — *«nada debe quedar congelado mientras está haciendo algo en segundo plano, debe mostrar en estas cosas realmente»*. **Por qué:** `hecho` sube de a un TALLE ENTERO y con un arte pesado el primero tarda ~26 s (medido: un talle solo son 13,5 s, y hay 6 corriendo a la vez peleando por CPU); antes de eso hay ~5 s levantando los procesos, porque `ProcessPoolExecutor` **no arranca ninguno hasta el primer trabajo**. Cambios: **(a)** el estado del job devuelve `piezas` = los `.svg` que los workers ya dejaron en `piezas_cache/<variable>/` **contados por FECHA** (`_contar_svgs(carpeta, desde)`) — por diferencia de totales no servía: re-dibujar un talle PISA los archivos que ya estaban y el contador quedaba clavado en 0 (me pasó, y parecía que la ruta estaba mal); **(b)** `fase` (`arrancando`/`dibujando`/`midiendo`) para poder decir qué se está haciendo cuando todavía no terminó nada; **(c)** el cartel muestra spinner + fase + piezas + **segundos que corren**, así siempre hay algo moviéndose; **(d)** `_precalentar_pool()` en `subir_arte`: los procesos levantan EN PARALELO al procesamiento del arte (~14 s), así cuando toca dibujar ya están; **(e)** `_get_render_pool` **descarta el pool si quedó roto** (`_broken`) y arma otro — si un worker moría de golpe, TODO render posterior fallaba con `BrokenProcessPool` hasta reiniciar el servidor. **MEDIDO** (arte de 8,4 MB, 20 talles): antes «0/20 · 0 piezas» durante 27 s y después saltos; ahora 11 → 38 → 64 → 72 → 106 → 240 piezas de forma continua, total 60-67 s. Harness: `scratchpad/medir_asignar.py` (⚠️ tiene que correr con la BASE VIVA: en el sandbox los workers re-importan `servidor` y el `db` falso no existe en el hijo → mueren).

- **2026-07-31 (165) — Artes PESADOS, la causa de fondo: el DIBUJO de las mesas ya no viaja dentro del JSON.** El usuario probó `Camiseta Golero 2.ai` (8,4 MB) y `Camiseta jugador.ai` y sufrió **1:13 min y 51 s**; la mejora (164) no alcanzaba. **Medido:** ese arte **no tiene ni una imagen embebida** — son **1098 KB de VECTOR PURO por mesa, 8,6 MB en total**, y la detección devolvía **11,66 MB de JSON** que el navegador tenía que parsear y rasterizar de una. La dedupe de (164) no podía hacer nada (nada se repite). **Solución:** cada mesa viaja como **URL** (`m.img` → `GET /api/arte/mesa_img?...&v=<firma>`) y el navegador la pide sólo cuando la muestra, en paralelo, cacheándola él (`Cache-Control: immutable`, y la firma del archivo va en la URL → subir otro arte cambia la URL sola y borra la caché en disco de la firma vieja). `detectar_arte(con_svg=False)` por defecto → **la detección pasó de 11,66 MB a 237 KB (0,02 s)** y la SUBIDA dejó de vectorizar. **SIGUE SIENDO VECTOR, no un raster:** se probó servir PNG (205 KB/mesa) y el usuario lo rechazó — *«no quiero PNG porque no es fiel»* — así que `mesa_img` devuelve SVG y el contrato verifica que es **byte por byte** el vector del arte. Tampoco hay miniatura de espera (la pidió sacar): se muestra el diseño de verdad o nada, con un **cartel de avance real**: «Cargando el diseño original… 0/25/38/50/75/88%» (efecto `cargaArte` en App.jsx, que precarga las URLs y cuenta las que llegan) y, en la subida, `XMLHttpRequest` con `upload.onprogress` → «Subiendo el diseño… N%» y después «Procesando el diseño…» (`fetch` no da progreso de subida; se cambió en `cargarDisenoWizard` y en `handleUploadFile`). **MEDIDO end-to-end en el navegador, subiendo el arte de 8,4 MB desde la UI:** detección 185 ms / 238 KB · las 8 mesas en vector completo 678 ms · el paso Arte dibuja en 683 ms. Lo que queda largo es la SUBIDA (~14 s), y ahí el grueso es `extraer_personalizacion` (4,2 s, tres pasadas por el content stream) — una vez por arte y con cartel. ⚠️ `open(...,"w")` en Windows convierte `\n`→`\r\n`: el SVG servido dejaba de ser byte-idéntico hasta poner `newline=""`. Contrato: `verificar_arte_liviano.py`. Ver [[arte-pesado-carga-rapida]].

- **2026-07-31 (164) — Artes PESADOS: el paso Arte pasa de 5-7 s a 0,05 s y el envío de 8,7 MB a 1,5 MB, sin tocar un píxel.** Pedido del usuario con sus archivos de `1 - Pruba tizada\Prueba 2` (3 artes de ~4,4 MB): *«que cargue rápido sin perder calidad ni fiabilidad, que sea el original pero que los maneje fluido»*. **Dónde estaba el tiempo** (perfilado): abrir 0,00 s · personalización 0,15 s · auto-mapeo 0,01 s · **`detectar_arte` 4,9-5,4 s**, y dentro de eso los pixmaps 0,19 s vs **`get_svg_image()` 4,70 s**. Del SVG de cada mesa (1094 KB), **1085 KB (99%) son una sola etiqueta `<image>`**: una imagen embebida de 6497×9897 px, 1 bit, 233 DPI — y **es la MISMA imagen repetida en 6 de las 8 mesas** (1,06 MB únicos, 6,4 MB enviados). Tres cambios: **(a) DEDUPLICACIÓN sin pérdida** (`motor_pedido._dedup_imagenes` + `_expandirSvg` en App.jsx): la imagen repetida viaja UNA vez en `det.svg_img` y en cada SVG queda el marcador `@@imgN@@`; el front la vuelve a pegar en 15 ms y el SVG queda **byte por byte igual** al original (verificado 8/8 mesas). gzip no puede hacer esto: su ventana es de 32 KB y las copias están a 1 MB una de otra. **(b) CACHÉ EN DISCO** de la detección (`servidor._deteccion_cache` → `.deteccion_cache.json` al lado del arte, 1,5 MB): la clave lleva ruta+mtime+tamaño del arte, las piezas del molde y `_DETECCION_CACHE_V`, así que se invalida sola; devuelve un dict fresco por llamada (el endpoint lo muta). `subir_arte` la deja caliente → cuando el usuario llega al paso Arte ya está. **(c) VECTORIZADO EN PARALELO** (`_svg_mesa_worker` + `_svgs_en_paralelo`) **sólo si el pool de render ya tiene procesos levantados**: medido 5,9 s → 1,7 s (3,4x, resultado idéntico), pero levantar los procesos cuesta 4,7 s y `ProcessPoolExecutor` los arranca recién con el primer trabajo — por eso NO alcanza con que el objeto exista (`_processes` vacío) o la primera detección saldría más lenta que antes. **MEDIDO end-to-end** en el navegador con el arte real: endpoint 7,08 s (frío) → 0,05 s; 1,53 MB en vez de 8,8 MB; el paso Arte del pedido dibuja las 8 mesas en 1,0 s. **LO QUE NO SE HIZO Y POR QUÉ:** re-muestrear las imágenes del SVG del visor (6497 px → 1625 px) daba 36% del peso, **pero la imagen es un tramado 1-bit (halftone)** y remuestrearla corre el patrón: 8,5% de píxeles visiblemente distintos ya a 600 px de ancho. Choca con «que sea el original» y con la ley *el arte se ve igual que la tizada* → descartado. **⚠️ TRAMPA AL VERIFICAR:** el rasterizador de SVG de PyMuPDF **ignora las etiquetas `<image>`** (borrarlas no cambia un píxel, y ese render difiere 59% de la página PDF real) → comparar SVG rasterizándolos con PyMuPDF da «idéntico» siempre, sin haber mirado nunca la imagen; hay que decodificar el `<image>` y compararlo con PIL. Contrato: `verificar_arte_liviano.py`. Ver [[arte-pesado-carga-rapida]].

- **2026-07-31 (163) — 🔴 El paso ARTE quedaba TRANCADO por un `viewBox` con `Infinity`.** Reporte del usuario: pedido nuevo → diseños → elegir moldes → «avancé al arte y quedó trancado», con este error repetido en la consola: `<svg> attribute viewBox: Expected number, "Infinity Infinit…"`. **Causa exacta:** en `MapeadorArteVisual` el encuadre se calculaba con `Math.min(...all.map(...))` — y **`Math.min()` SIN argumentos devuelve `Infinity`** (`Math.max()`, `-Infinity`). Cuando en ese instante no hay piezas que dibujar, el viewBox sale `"Infinity Infinity -Infinity -Infinity"`, el navegador **descarta el `<svg>` entero** y la pantalla queda en blanco, sin dibujo y sin explicación. Pasa de verdad: el visor filtra por la variable en vista y `vfArte` usa un **`show` VACÍO como piso** mientras la variable no resuelve (puesto a propósito para no caer a las ~135 piezas del molde), así que hay una ventana real con cero piezas. **Fix:** el encuadre se valida con `Number.isFinite` y cae a uno neutro (`-6 -6 112 112`) cuando no hay nada; el ancho/alto nunca bajan de 1; `_domVB()` (zoom/pan) también descarta un viewBox no numérico en vez de propagarlo a los encuadres siguientes; y si no hay piezas se muestra **«Preparando las piezas de esta prenda…»** dentro del visor en vez de un lienzo vacío. **VERIFICADO** con el cálculo aislado: sin piezas antes daba `"Infinity Infinity -Infinity -Infinity"` (inválido) y ahora `"-6 -6 112 112"` (válido); **con piezas el resultado es idéntico al de antes** (no cambia nada en el caso normal). Se revisaron los otros 6 usos de `Math.min/max(...spread)` del archivo: todos ya tenían su guarda. ⚠️ **Regla:** `Math.min/max` con spread sobre un array que puede venir vacío es un `Infinity` esperando; en un `viewBox` no degrada, **rompe la pantalla entera**.

- **2026-07-31 (162) — La ficha muestra el NOMBRE y el NÚMERO estampados, tal como salen del diseño.** Pedido del usuario. `_molde_guia_ficha` armaba su prenda de muestra con `nombre: ""` y `numero: ""`, así que el molde guía salía **sin personalización**: el taller no veía cómo queda el nombre y el número (tipografía, curva y borde del arte — ver [[personalizacion-curva-borde]]). Ahora `generar_multi` guarda en cada guía una **`muestra`** (`_muestra_de`: nombre, número y la personalización completa) tomada de la **primera fila del pedido que traiga alguno**, y la guía se genera con esos datos por el MISMO camino que la tizada. El rótulo aclara de quién es (**«ejemplo: PEREZ 10»**) para que no se lea como que todas las prendas llevan eso — los de cada una están en la tabla de arriba. **VERIFICADO** con el molde real: el Dorso de la guía sale con el **10 estampado con la tipografía del diseño** (antes salía liso) y el rótulo muestra el ejemplo; los contratos `verificar_ficha_piezas_pedido.py` y `verificar_ficha_disenos.py` siguen pasando. ⚠️ Si el arte no tiene capa para el nombre, ahí no aparece nada — es el mismo aviso de «capas faltantes» que ya da el sistema al subir el diseño, no un problema de la ficha.

- **2026-07-31 (161) — El halo de la etiqueta va DETRÁS DE TODO EL TEXTO, no por letra (en el visor).** Pedido del usuario después de (160): *«el grosor ya se muestra bien, pero debe quedar por detrás de todo el texto y no por letra»*. **El motor ya lo hacía bien** —traza el contorno de TODOS los glifos y recién después los rellena todos, así que el halo queda por debajo de la palabra entera; verificado dibujando el mismo texto en PDF (`halo3.png`: fill nonzero, even-odd y halo+fill, los tres impecables)—. El que fallaba era el **visor**: usaba un solo `<text>` con `paint-order: stroke`, y el navegador eso lo pinta **glifo por glifo** (halo de la M, relleno de la M, halo del guión…), así que el halo de cada letra se monta sobre el relleno de la anterior y se ven los contornos entre letras. **Fix:** el texto se dibuja en **dos capas** — un `<text>` sólo con el trazo (`fill:none`, `stroke-linejoin/linecap: round`) y encima otro sólo con el relleno (`stroke:none`) — en los tres caminos del visor (zonas, texto sobre el borde y texto recto). De paso, **el visor del paso Arte no dibujaba el halo** (la tizada sí): ahora también lo pinta, con el mismo criterio y en milímetros reales. **VERIFICADO**: el DOM del SVG muestra las dos capas con los estilos correctos, y en SVG el orden de documento define el pintado, así que el halo queda detrás. ⚠️ Al comparar «cómo se ve» entre motor y navegador, **`paint-order` NO es equivalente a trazar-todo-y-después-rellenar-todo**.

- **2026-07-31 (160) — El BORDE de la etiqueta se veía 3,4× más fino en la pantalla que en la tizada.** Reporte del usuario, después del arreglo del tamaño (159): *«en la tizada sale más grande el borde que en la configuración»*. **Causa:** el motor dibuja el trazo en **milímetros reales** (`borde_mm * MM`), pero el visor lo calculaba con una fórmula proporcional al tamaño de letra: `strokeWidth = fs * 0.07 * borde_mm`. Con la config del usuario (letra 3 mm, borde 3 mm) eso da **0,88 mm en pantalla contra 3 mm en la tizada — 3,4× más fino**. Y el error se movía con el tamaño de letra, así que nunca cerraba. **Fix:** `strokeWidth = borde_mm * pxmm` — la misma medida que el motor. **VERIFICADO** midiendo la etiqueta IMPRESA (aislada contra la misma pieza sin etiqueta, a 800 dpi): la letra mide **3,11 mm** de ancho —confirma la 159— y **cada milímetro de borde agrega ~0,5 mm** de mancha, o sea el trazo va en mm reales, centrado en el contorno y con el relleno encima. ⚠️ Para medir el halo hay que **bajar el umbral** de detección: el borde por defecto es `[0.01,0.01,0.01,0.05]` (casi blanco) y con umbral 30 no aparece. ⚠️ Y ojo con el eje: la etiqueta suele ir ROTADA sobre el borde de la pieza, así que el «alto» de la mancha es el LARGO del texto — el grosor se mide a lo ancho.

- **2026-07-30 (159) — EL TAMAÑO DE LA ETIQUETA SON MILÍMETROS DE LETRA (antes salía 28 % más chica).** El usuario: *«el tamaño es de la letra, no de un recuadro por fuera; si pongo 3 mm y tengo una “Mp”, la M tiene que medir 3 mm»*. Tenía razón y es medible: `size_mm` se pasaba **tal cual** como tamaño de fuente, y eso es el **em** — el cuerpo entero, con lugar reservado para ascendentes y descendentes. Con 3 mm configurados, la «M» de Arial Bold salía de **2,15 mm** (28 % menos), y el error **cambiaba según la tipografía** (Black Ops One 1,94 mm · Graduate 2,25 mm · la fuente subida del usuario 1,81 mm). **Fix:** `FuenteCurvas` expone **`cap_ratio`** (altura de mayúscula ÷ em, de `OS/2.sCapHeight`, y si la fuente no lo trae **se mide la «H» real**) y **`size_para_alto()`**; el motor convierte con eso en los dos caminos (etiqueta única y por zonas). Ahora una mayúscula mide EXACTAMENTE lo pedido y la «p» baja su cola por debajo, como corresponde. **El visor hace lo mismo** (`CAP_RATIO_ETQ = 0.716` en App.jsx, y el preview pasa a Arial): sin eso, el visor mostraría la etiqueta 28 % más chica que la tizada y se rompe la ley arte=tizada. **VERIFICADO**: contrato nuevo `verificar_etiqueta_tamano.py` (las 7 fuentes del catálogo dan mayúsculas de 3,00 mm; con «Mp» la M mide 3,00 y el conjunto 3,83 por la cola; 6 mm da exactamente el doble) **y medido sobre la pieza IMPRESA**, aislando la etiqueta contra la misma pieza generada sin ella: **1,40× más alta que antes = 1/0,716 exacto**. ⚠️ Al medir un glifo NO sirve `get_drawings()` (un glifo viene partido en varios paths): se mide restando dos renders.

- **2026-07-30 (158) — MEDIDO: cuánta tela se gana con cada giro y con más búsqueda (el usuario lo dejó PARA DESPUÉS).** Preguntó si la tizada aprovecha bien el espacio, «hay muchas piezas sin girar». **No se cambió nada**: se midió con sus piezas reales (36 piezas de 6 prendas de «Manga pegada», tela de 157 cm, separación 5 mm, margen 0) con la herramienta nueva **`medir_nesting.py`** (queda en el repo; `N_PRENDAS` y `GIRO` por variable de entorno). **Su preset está en giro `180`.** Resultados: sin girar **3,12 m / 78,1 %** · **180° (el suyo) 3,15 m / 77,3 %** · **90° 3,04 m / 80,0 %** · libre (15°) 3,04 m pero 6× más lento. O sea: **90° ahorra 3,5 % de tela y no cuesta tiempo**, y —contraintuitivo pero real— **«180» rinde PEOR que «ninguna»** (con bottom-left greedy, más ángulos no garantiza mejor resultado). Sobre el **pruning** (con >15 piezas `anidar_contorno` prueba 1 orden + `bl`): forzar las 8 combinaciones da **−1,2 % con giro 180 y 0 % con giro 90**, y la grilla fina de 2 mm otro −1,3 % a cambio de **30× el tiempo** (1,4 s → 47 s). **Conclusión: el algoritmo no deja tela sobre la mesa; lo que limita es la restricción de giro.** Pendiente cuando se retome: (a) decisión TEXTIL de si las telas admiten 90° (cambia hacia dónde estira la prenda y puede variar el color por la dirección de la fibra) — el campo ya existe en Reglas de Nesting; (b) si se quiere, un selector de «esfuerzo del acomodo» en el preset (rápido/máximo) que suba órdenes/estrategias/resolución para tizadas donde la tela sea cara y no importe esperar.

- **2026-07-30 (157) — LA FICHA MUESTRA LAS PIEZAS EXACTAS DEL PEDIDO (manga corta, larga, o las dos).** Pedido del usuario: *«si se eligió manga larga que muestre manga larga; si una fila es manga corta y otra larga del mismo diseño, que se muestren las 2»*. **El molde guía se armaba con una prenda de muestra SIN toggles** (`fila = {__variante, talle, nombre, numero}`), así que el motor resolvía con la opción por DEFECTO: un pedido entero de manga larga mostraba las mangas **cortas**. El taller corta mirando eso. **Fix:** `generar_multi` junta, por cada guía, **las combinaciones de toggle que aparecen en las filas** (`_combo_toggles` da la firma `clave=opción`, y se acumulan sin repetir); `_molde_guia_ficha` genera **una prenda por combinación** y **une** las piezas resultantes deduplicando por nombre (el Frente es el mismo con corta o larga: va una vez; las mangas son distintas: van las cuatro). El rótulo de la ficha ahora dice qué opciones incluye — «**Manga: corta + larga · 8 piezas**» — para que se entienda por qué están las de los dos tipos. **VERIFICADO con el molde real** (`verificar_ficha_piezas_pedido.py`): pedido de corta → 6 piezas con las 2 cortas y ninguna larga; pedido de larga → las 2 largas y ninguna corta; **pedido mezclado → 8 piezas con las 4 mangas, sin repetir el resto**; y el rótulo lo dice. **Visto fallar** con el comportamiento viejo (3 aserciones: el mezclado se quedaba en 6 piezas y sólo mangas cortas). Inspección visual de la ficha OK. ⚠️ Sirve para CUALQUIER toggle (sisa, capucha…), no sólo la manga: es el mismo mecanismo generalizado.

- **2026-07-30 (154) — 🔴 «Faltan N piezas sin tela» CON TODO ASIGNADO (y la planilla bloqueada): el contador anotaba piezas del ítem ANTERIOR.** Reportado como «vuelvo de la planilla y lo que asigné no queda». **Reproducido con el escenario real del usuario** —2 espacios (Jugador/Golero) × 2 moldes cada uno (Manga pegada + Short Basico), los 4 artes subidos de verdad— y el síntoma se ve clarísimo: las **4 combinaciones tenían su tela** (8+4+8+4 piezas) y aun así el pie decía «⚠ Faltan 4 pieza(s) sin tela»… y al pasear por los ítems el número **cambiaba a 8**. **Causa:** `piezasPorItem` se llenaba con `piezasArteGen`, que sale del VISOR. Al cambiar de prenda, el ítem (`_claveTela`) cambia al instante pero el dibujo llega después: en ese hueco se anotaban **las piezas del molde anterior** bajo la clave del nuevo (las 8 de la camiseta como si fueran del short). Esas piezas no existen en ese molde, así que **nunca** iban a tener tela → faltante fantasma, permanente y variable según por dónde navegaste. **Fix:** el registro sólo corre cuando el visor YA es el del ítem — nuevo estado **`etqPid`** (de qué molde es el `etqData` dibujado) + la variable en vista tiene que coincidir con la del ítem. **VERIFICADO:** con las 4 combinaciones asignadas, recorrer los ítems en cualquier orden (6 saltos) no genera ningún aviso, «A la planilla» queda habilitado, y **ir a la planilla y volver** conserva las 4 combinaciones sin avisos. ⚠️ **Lección de método:** en la primera pasada creí ver que asignar en un espacio escribía en otro — era un error de MI automatización (el botón «Ver telas de pieza» alterna: mi script lo cerraba en vez de abrirlo). Antes de acusar al sistema, verificar que el gesto simulado hizo lo que se cree.

- **2026-07-30 (156) — MESAS DE HASTA 50 METROS (`/UserUnit`), con el RIP del usuario verificado.** Tras la entrada 155 («el techo es 5,08 m»), el usuario preguntó si de verdad no se podían hacer mesas de 50 m. **Sí se puede**: PDF 1.6 tiene **`/UserUnit`** — el límite de 14400 unidades por lado no se mueve, pero cada unidad puede valer N puntos, así que la mesa crece sin romper el formato. **El riesgo era el RIP** (si lo ignora, imprime a 1/N de escala = rollo perdido), así que **primero se verificó**: se le entregó `PRUEBA-MESA-LARGA-10m.pdf` (10 m con `UserUnit=2`, con un rectángulo de 1 m y un cuadrado de 10 cm arriba de todo para no gastar tela) y **su RIP lo carga y lo reporta como 10 m**, igual que Illustrator. **Implementación:** `componer_pdf_contorno` calcula `uu = ceil(max(lado)/14400)`, dibuja TODO dividido por `uu` (posiciones, tamaños y cuerpo del texto) y escribe `/UserUnit` con pikepdf; con mesas normales `uu=1` y la salida es **idéntica** a la de siempre. Si pikepdf fallara, se avisa **fuerte** en el log («NO IMPRIMIR») en vez de dejar una hoja a 1/N de escala. Se sacó el recorte a 14400 de `_preparar` (el tope ahora lo pone la config) y `ALTO_MESA_MAX_CM` pasó de 508 a **5000 cm (50 m)**; el campo de Nesting acepta hasta 50 m y explica de dónde sale. **VERIFICADO** con `verificar_mesa_larga.py` (contrato nuevo): una mesa de 3 m sale sin `UserUnit` y con las medidas de siempre; una de 10 m usa `UserUnit=2`, ocupa 14060 unidades (dentro del límite), **mide 9,92 m de verdad**, sus piezas miden **40×30 cm reales** y la última está al final de la mesa; y **el aplanado para el RIP conserva el `/UserUnit`**. **Visto fallar**: desactivando la escritura de `/UserUnit`, el contrato tira 6 fallas (la mesa queda en 4,96 m y todo a media escala). ⚠️ **Trampa para la próxima vez:** **PyMuPDF YA aplica el UserUnit** al abrir (`page.rect` viene en puntos reales), pikepdf entrega el MediaBox crudo — multiplicar en los dos lados da el doble (pasó al escribir la prueba). ⚠️ Mesas muy largas: más tiempo de nesting y archivos más pesados; si aparece `std::bad_alloc`, bajar el alto o `TIZADA_PROCESOS`.

- **2026-07-30 (155) — «Puse 8 metros y me sigue haciendo mesas de 5»: el techo es del FORMATO PDF (5,08 m).** El preset guardaba los 800 cm sin chistar, pero `nesting_contorno._preparar` hace `min(alto_cm * CM, 14400)` y **14400 puntos = 200 pulgadas = 508 cm** es el tamaño de página más grande que admite un PDF. O sea: la pantalla prometía 8 m y el nesting cortaba en 5,08 — el usuario lo vio en las mesas. **No se puede subir sin salirse del PDF estándar** (`/UserUnit` lo permitiría, pero un RIP que no lo interprete imprime a otra escala: tela arruinada, y va contra la ley arte=tizada). **Fix — que la pantalla no mienta:** constante `ALTO_MESA_MAX_CM = 508` en `servidor.py`; se acota **al guardar** y también **al leer** (`_config_produccion`), así los presets ya guardados con 8 m muestran y aplican 5,08; el campo del formulario tiene `max=5.08` y explica el motivo. **VERIFICADO** sobre una copia: guardar 3,5 m llega a las 36 telas como 350 cm; pedir 8 m queda en 508; y un preset viejo con 800 cm se **lee** como 508 sin tener que re-guardarlo. Si una tizada no entra en 5,08 m, el sistema abre otra mesa — que es lo que ya hacía.

- **2026-07-30 (153) — El ALTO MÁXIMO DE LA MESA ya se puede configurar (existía, pero sin pantalla).** El usuario preguntó dónde se cambia. Vivía en el **preset de nesting** (`alto_max_cm`, lo lee `_config_produccion` y se lo pasa a **todas** las telas como `altura_max_cm`), pero **el formulario de Reglas de Nesting no tenía ese campo** —sólo Separación, Margen y Giro— así que nunca se escribía y el sistema usaba el **default de 500 cm**. Ahora: campo **«Alto máximo de cada mesa (metros)»** en el modal (se pide en metros, se guarda en cm), visible en la tarjeta del preset y en el resumen del molde (Ajustes → Nesting). El endpoint `POST /api/nesting_presets/guardar` lo persiste y lo **acota a 50–2000 cm** (por debajo no entra una prenda, por arriba ningún RIP lo procesa). **VERIFICADO** sobre una copia: guardar 3,5 m deja `altura_max_cm=350` en las 36 telas que ve el motor, y un valor absurdo (99999) se acota a 2000 en vez de romper la tizada.

- **2026-07-30 (152) — 🔴 «38 fila(s) sin variable elegida»: con DOS moldes en un espacio, el segundo se generaba ENTERO.** El usuario mostró el cartel amarillo de la tizada y preguntó por qué salía «si todo tenía arte». Dos cosas, las dos mías: **(a) el aviso estaba en la lista equivocada** — lo agregué en la entrada 146 dentro de `avisos`, que el front pinta bajo **«Algunas piezas salieron en blanco… no tienen diseño»**, así que se leía como un problema de ARTE cuando el arte estaba perfecto. Ahora va en **`avisos_pedido`**, un cartel aparte («Revisá esto del pedido»). **(b) El aviso destapó un bug de verdad:** cada fila de la planilla lleva **UNA sola** `__variante` —la primera del espacio (`varianteDeDiseno` devuelve `claves[0]`)—, así que si un espacio usa **dos moldes**, para el segundo esa clave no es suya, `_traducir_prendas` la descarta y la fila llega **sin variable**: el motor genera **TODAS las piezas de ese molde** (no las de la variable) y la etiqueta cae a la posición por defecto. **Fix:** el front manda `vars_por_diseno = {slug_espacio: {pid: clave}}` (la variable que ese espacio eligió PARA CADA molde) y `_traducir_prendas` acepta `var_por_diseno`: si la clave de la fila no es de este producto, usa la del mapa. La elección de la fila sigue mandando cuando SÍ es de ese molde. **VERIFICADO** (`scratchpad/probar_variable_por_molde.py`, sobre una copia): con una fila que trae `v_7bu24xr` (Manga pegada) y un espacio que también usa Short Basico → **antes** el Short quedaba en `variante_clave=None` (molde entero); **ahora** recupera `v_lo8q2c4` con sus **4 piezas** y su grupo; y una fila que elige «Cuello V» conserva su elección.

- **2026-07-30 (151) — «Después de cargar el arte lo asignado no queda en ningún lado»: SÍ quedaba, pero el panel no lo mostraba.** Reclamo del usuario. **Reproducido con arte real** (harness: una ruta `/sandbox/arte/<pid>/<diseño>` en el server de sandbox que devuelve un `.ai` ya cargado, y desde el navegador se lo mete en el `<input type=file>` con `DataTransfer` → corre `cargarDisenoWizard` de verdad). **Medido:** tras cargar el arte, `telaPorPieza` seguía **intacto** (8 piezas con su tela) — no se perdía nada. Lo que fallaba es la PANTALLA: el panel de telas se quedaba en la vista **«ASIGNAR TELA» (1) Elegí una tela · 2) Tocá las piezas · 3) Asignar**, que está en blanco por definición, porque `aplicarTela` limpiaba la selección pero **no salía del modo asignar**. Con el arte encima —que tarda, «Asignando el diseño a cada variante…»— el usuario volvía a un panel vacío y la conclusión razonable es «se perdió». **Fix:** al asignar una tela, y también al terminar de cargar un arte, el panel vuelve a **«Telas asignadas»** (`setTelaAsignMode(false)` + limpiar selección/buscador). **VERIFICADO:** asignar → el panel muestra «TELAS ASIGNADAS», la tela listada y **«✓ Todas las piezas tienen tela»**; cargar el arte encima → sigue mostrando lo mismo, las 8 piezas conservan su tela y «A la planilla» queda habilitado. ⚠️ **Lección:** en Pedidos, «no se guardó» y «no se ve» se sienten igual. Después de cualquier acción del operario, la pantalla tiene que **mostrar el resultado**, no volver a un formulario vacío.

- **2026-07-30 (150) — VOCABULARIO + el panel de telas dejó de cruzarse entre espacios.** ⚠️ **TÉRMINO QUE HAY QUE USAR (lo definió el usuario):** lo que se escribe en el **paso 1** («Jugador», «Golero») es un **ESPACIO DE TRABAJO AUTÓNOMO**, no «el diseño» del arte. Sus palabras: *«por cada uno que creemos crea un espacio de trabajo autónomo. Hasta la planilla — ahí indicamos qué espacio es cada uno. En el paso 1 y 2 son dos o más espacios únicos, y después planilla y tizada de cada espacio toma lo que necesita»*. En el código se llama `disenosPedido`/`disenoActivo` y su NOMBRE define además dónde vive su arte (`disenos/<slug>/arte.ai`); el `.ai` que se sube es **el ARTE de ese espacio**. Dos espacios pueden usar el mismo molde, la misma variable y hasta el mismo arte: **siguen siendo compartimentos separados**. **Bug arreglado en esa línea:** en el paso Arte, el panel de telas guardaba la **selección de piezas** (`telaSelPiezas`) y la tela elegida en estado GLOBAL → al pasar de un espacio a otro aparecían **las mismas piezas ya marcadas** que ahí nadie había tocado (y la siguiente asignación se las pintaba sin querer). Ahora un efecto suelta `telaSelPiezas`/`telaElegida`/`telaAsignMode`/`telaBuscarAsig`/`telaAviso` cada vez que cambia el espacio o la prenda dentro del espacio (el panel queda abierto: se asigna espacio por espacio sin reabrirlo). **VERIFICADO en el navegador:** con la MISMA variable en dos espacios, asignar Delta a todas las piezas en uno deja al otro en «⚠ Faltan 8 piezas sin tela» (no hereda), y la selección no viaja entre espacios.

- **2026-07-30 (149) — 🔴 «SIGUE TOMANDO DOBLE LA MISMA VARIANTE»: el modo «Todos» metía cada variable en TODOS los diseños.** Reclamo del usuario, textual: *«cada diseño es único, no importa si en el mismo pedido se elige 10 mil veces la misma variable; en cada diseño se maneja la variable propia de cada diseño, al sistema le importa un huevo si se eligió en otros diseños»*. **Causa:** el paso 1 tenía un chip **«Todos»** —y era el valor **por defecto** de `asignDiseno`— así que `toggleVarEnDiseno` hacía `targets = todos los diseños`: tocar una variable la agregaba a **cada diseño del pedido** (y si ya estaba en todos, la sacaba de todos). Resultado: la variable aparecía elegida en diseños donde nadie la puso, el paso Arte pedía su arte una vez por diseño y el pedido la fabricaba de más. Lo mismo en `toggleMoldeEnDiseno` (moldes propios). **Fix:** **se eliminó el modo «Todos»**. Siempre hay UN diseño destino (`disenoDestino()` = el chip encendido, o el primero si el elegido ya no existe) y elegir/soltar una variable o un molde toca **sólo ese diseño**; que otro diseño use la misma variable no marca nada acá. Las marcas de las tarjetas (catálogo y «Mis artículos») se calculan contra ese diseño, y las píldoras de colores debajo de cada tarjeta siguen mostrando **en qué diseños está** — que es la información útil, sin mezclar. Además `quitarDisenoPedido` ahora borra también **sus variables y sus telas** (antes quedaban colgadas aportando al pedido) y pasa el foco a otro diseño en vez de a «Todos». **VERIFICADO en el navegador** con los moldes reales: elegir «Cuello redondo» en *Titulares* deja `{titulares:[v_7bu24xr]}`; crear *Suplentes* y elegir **la misma** deja `{titulares:[v_7bu24xr], suplentes:[v_7bu24xr]}` (cada uno la suya); **quitarla de Suplentes no toca a Titulares**; agregar «Cuello V» a Titulares no toca a Suplentes; y en el paso Arte la misma variable en dos diseños da **un ítem por diseño** (`0/1` + `0/1` = `0/2 con arte`), no dos en el mismo.

- **2026-07-30 (148) — PEDIDOS SIN ARRASTRE: «Nuevo pedido» ahora limpia TODO, y el aviso de telas dejó de mentir.** Pedido del usuario: *«que cada vez que se presione nuevo pedido limpie la caché y no quede ni las telas asignadas ni los diseños ni nada»* + *«cuando entro a asignar una tela la asigno pero queda este mensaje bugiado cuando todas las piezas tienen»*. **(1) `_reiniciarPedido` limpiaba 13 estados y se dejaba el resto**, entre ellos **`telaBaseMolde` y `telaPorPieza`** — que además **se persisten en `localStorage` (`tizada_wizard`)**, así que las telas del pedido viejo volvían incluso recargando. Ahora borra: lo elegido (diseños/moldes/variables), **todas las telas** y el estado del panel, arte y visor (`arteCargado`, `mapeoData/Valores`, `etqData/etqNombres`, `verVariante`, perfiles, editor de editables), la **planilla** (5 filas vacías sembradas ahí mismo: el efecto de `filas` sólo corre cuando CAMBIA el molde activo), los resultados, las **tres cachés en memoria** (`_pvCache`, `_talleDetCache`, `_detArteCache`) y **el `tizada_wizard` del navegador**. **(2) El aviso «Faltan N piezas sin tela» quedaba pegado** porque `telasFaltantes` guardaba **el número** por `molde|variable` —sin el DISEÑO, siendo que la tela es por (diseño, molde) desde la entrada 142— y sólo se recalculaba al volver a ese ítem: dos diseños del mismo molde se pisaban la cuenta y una asignación posterior no la corregía. Ahora se guardan **las piezas** de cada ítem (`piezasPorItem`, clave `diseño|molde|variable`) y el total se **deriva** de las telas de ese momento → no puede quedar viejo. **(3) Se sacó el efecto** que, con la selección vacía, metía el molde ACTIVO del server en `moldesSeleccionados`: con «Nuevo pedido» + F5 reaparecía una prenda que nadie eligió (hoy la selección se DERIVA de las variables del paso 1). **(4)** `cargarMapeadorOperario`/`asignarTodasLasVariantes` al subir el arte ahora reciben el **pid del ítem** (mismo criterio que la entrada 147; con `pidCfg` podían trabajar sobre otro molde). **VERIFICADO en el navegador** con los moldes reales (copia en sandbox): armar pedido → asignar telas → el aviso desaparece al asignar; «Nuevo pedido» deja `telaPorPieza`, `disenosPedido`, `moldesSeleccionados` y `arteCargado` vacíos **y sigue vacío tras F5**; un 2º diseño con el MISMO molde **no hereda** las telas del primero. ⚠️ No se pudo probar a mano el aviso del pie con arte cargado en dos diseños (hay que subir dos `.ai` de verdad); lo que se verificó es el cálculo que lo alimenta.

- **2026-07-30 (147) — 🔴 «ELEGÍS EL MOLDE EN EL PEDIDO Y EL ARTE QUEDA VACÍO HASTA QUE RECARGÁS».** Reproducido en el navegador con los moldes reales (copia en un sandbox sin login, `scratchpad/sandbox_server.py`): el paso Arte se queda en **«Cargando el molde…»** para siempre. **Causa:** el efecto del paso Arte (`App.jsx`, «En el paso de DISEÑOS, el molde mostrado debe estar activo») hacía `if (id !== productosCat.activo) { handleActivarProducto(id); return; }` — o sea, **para pintar el molde esperaba a que el server lo marcara ACTIVO y a que volviera el catálogo**. Esa cadena tiene tres eslabones que pueden fallar o demorar (`POST /api/productos/activar` → `_guardar_catalogo` en MSSQL → `fetchProductos`); si se corta cualquiera, **no hay reintento** y la pantalla queda cargando. En el sandbox se ve con el activar devolviendo 500, y también con la base LENTA (cada request que lee el catálogo esperaba 10 s de timeout ODBC). Encaja con «ciertos moldes» + «recargando anda»: al recargar, el activo ya coincide y el efecto no pasa por ahí. **Fix (frontend):** el visor carga con el **`pid` EXPLÍCITO del ítem** (`cargarMoldeOperario(id)` / `cargarMapeadorOperario(id)`), que en el server **tiene prioridad sobre el activo** (`_get_active_producto_id`, punto 1) → ya no depende de la ida y vuelta; se sigue activando, pero **sin `return`** (la planilla y la config lo necesitan). Además se agregó **`_idsCat`** (firma estable de los ids del catálogo) a las dependencias: sin ninguna dep del catálogo, un efecto que corrió ANTES de que llegaran los productos **no se enteraba nunca** (`itemsArteDe` resuelve el molde por id); usar `productosCat.productos` directo hubiera disparado recargas en cada uno de los ~28 `fetchProductos()`. `cargarMoldeOperario` ahora también usa `_talleDetCache` (misma clave `pid|__guia__`), así el segundo pase no repite el GET. **VERIFICADO en el navegador**, con `activar` devolviendo 500 a propósito: el Arte **carga igual** y pide `deteccion?pid=<el molde del ítem>` (no el activo). Y **visto fallar**: con el `return` repuesto y recompilado, la misma secuencia queda en «Cargando el molde…». ⚠️ Para reproducir bugs de UI sin las credenciales del usuario: copia de `datos/`+`entrada/` a un temporal + `_USUARIOS_ON=False` + `/api/auth/yo` respondiendo 404 (el front sólo se saltea el login si ese fetch **falla**) + `db` que falla al instante (si no, 10 s por request).

- **2026-07-30 (146) — 🔴 LA ETIQUETA SE IBA AL LUGAR POR DEFECTO EN LA TIZADA (reportado: «en un molde funciona espectacular y en otro aparece en el espacio predeterminado»).** **Reproducido con el molde y el motor reales**: la misma pieza («Dorso» de *Manga pegada*) sale con la etiqueta sobre el borde configurado si la fila trae la variable, y **abajo al centro** (`etiqueta.posicion`, rx .5/ry .92) si no la trae. **Causa:** la posición se guarda con la clave **`variante§NombrePieza`** (`claveEtqPieza` en el front) y el motor la buscaba **sólo por la variante de la fila** — sin ninguna red debajo. Cuando la fila llega **sin variable**, ninguna clave matchea y cae al default. Y llega sin variable en dos casos reales: **(a)** el molde se pide entero (propios/sin variables elegidas); **(b)** `_traducir_prendas` **descarta** la clave si la variable no resuelve piezas (`valores` sin `pieza_id` NI `pieza_idx`) — medido en los datos del usuario: en «Molde 1» la variable `v_qess9lp` («yfg») **no llega al motor**, mientras que en «Manga pegada» y «Short Basico» las suyas sí. Ahí está el «en un molde sí y en otro no». Se ve bien en pantalla porque **el preview del front tenía más fallbacks que el motor** (`posPorPieza[variante§name] || [grupo§gen] || [gen] || [name]`). **Fix (motor, `generar_pieza`):** la resolución pasa a ser una cascada — `variante§nombre completo` → `variante§genérico` → `grupo§genérico` → `global` → **`otra variable§nombre completo` → `otra variable§genérico`** (último recurso, `setdefault` = gana la primera de la config, orden estable). Lo específico sigue mandando: cada variable usa la suya. **Aviso** nuevo en `generar_multi` (no traba): si hay posiciones por variable y filas sin variable, se dice que se usó la de la primera variable configurada. **VERIFICADO**: los renders de la pieza con variable / sin variable / con el label en vez de la clave quedan **pixel-idénticos** entre sí y **distintos** del default; con dos variables configuradas distinto, cada una conserva la suya. Contrato nuevo `verificar_etiqueta_posicion.py`, **visto fallar** (3 aserciones) con la cascada revertida. ⚠️ La etiqueta se estampa en `generar_pieza`, NO en `_armar_base` → **no hay que invalidar `piezas_cache`**. Ver [[etiqueta-por-variable]].

- **2026-07-30 (145) — FICHA TÉCNICA: UN MOLDE GUÍA POR CADA DISEÑO (antes mostraba uno solo y escondía el resto).** Pedido del usuario. La ficha se llevaba **una guía por MOLDE**, armada con la **1ª fila** del pedido (`_var_ficha[pid]`), así que un pedido con «Jugador» + «Golero» del mismo molde mostraba **un** arte y el taller cortaba mirando algo que la mitad del pedido no usa — otro de los errores que **salen bien impresos**. Ahora `/api/generar_multi` anota una guía por **(molde · diseño · variable)** en `_guias_ficha`, y lo hace **dentro del bucle `por_diseno`, después del `_fallback`**: si el diseño de la fila no tenía arte, la tizada usa el de otro y la ficha tiene que mostrar **el que de verdad se estampó**. Dentro de un diseño se anota una guía por VARIABLE distinta (cuello redondo ≠ cuello V: las piezas cambian), deduplicando `(pid, dslug, variante)` → filas repetidas no duplican guías. 🔴 **Bug de tela que venía de arrastre y se arregla acá:** la asignación pieza→tela salía de `_asig_de(default_diseno)` (el diseño editado en el Arte) para TODAS las guías — desde la entrada 142 la tela es **por diseño**, así que un diseño mostraba las telas del otro. Ahora cada guía guarda **`_asig_de(su dslug)`, calculada dentro del bucle**: `_asig_de` es una **clausura sobre el molde del ciclo** y para cuando corre el hilo de `correr()` ya apunta al último molde (llamarla ahí devuelve la asignación equivocada). **Tope:** `_MAX_GUIAS_FICHA = 16` — cada guía pasa por el motor, y molde × diseño × variable escala rápido; si recorta **lo dice** en `avisos` (nunca en silencio). **Dibujo** (`ficha_tecnica.py`): título «MOLDE GUÍA · molde · diseño» + línea gris con «Variable: X · N piezas» — la variable sólo se nombra cuando ese molde+diseño aparece más de una vez (si es la única, es ruido) — y **línea separadora** entre guías de una misma página. **VERIFICADO** con `verificar_ficha_disenos.py` (contrato nuevo): (1) el dibujo con 3 guías; (2) el pedido REAL por `app.test_client()` sobre una **copia** del molde «Manga pegada» → pide exactamente 3 guías (jugador·v_7bu24xr, golero·v_7bu24xr, golero·v_92ml8qi), sin repetir la fila 4, cada una con su asignación, y el `FICHA_TECNICA.pdf` que deja el trabajo trae los 3 títulos; (3) con **arte real**: los dos diseños dan las mismas 6 piezas pero **bytes distintos** (cada uno con su arte) — inspección visual de la ficha OK (Jugador blanco / Golero negro, uno debajo del otro). **Se lo vio FALLAR primero**: con el dedupe saboteado a `(pid,)` (el comportamiento viejo) el contrato tira 4 fallas. ⚠️ Trampas del camino: `/api/generar_multi` **exige sesión** (guarda global `_guardia_moldes`) → el contrato simula `_usuario_actual`; y el molde de prueba se **copia** sin `creado_por` (un molde con dueño lo corta la guarda). ⚠️ Y un pisón propio: el script que puso/sacó el sabotaje reescribió `servidor.py` con `newline=''` y **convirtió el archivo entero de CRLF a LF** — restaurado a mano; para editar Python desde un script hay que preservar los finales de línea. Ver [[ficha-tecnica]].

- **2026-07-29 (144) — 🔴 EL DISCO DEL SERVIDOR ESTABA LLENO: un solo problema disfrazado de tres.** `Local Disk (C:) — **0 bytes free of 39.9 GB**`. Explica de golpe los tres síntomas que se venían persiguiendo por separado: **(a)** publicar daba «HTTP Error 500» (no podía escribir el paquete); **(b)** los archivos se cortaban a mitad de descarga → `ERR_QUIC_PROTOCOL_ERROR` en el navegador; **(c)** generar la tizada tiraba **`std::bad_alloc`** — Windows amplía la memoria con el **archivo de paginación en C:**, y sin espacio no puede crecer, así que las reservas fallan. **Lección para el mapa: antes de perseguir tres bugs distintos, mirar el disco.** ⚠️ **Y una pista que se pasó por alto:** el diagnóstico previo culpó a HTTP/3 / al servidor de desarrollo, cuando el propio usuario había dicho que **otro sistema en la MISMA url funcionaba** — eso ya descartaba el dominio y apuntaba a la máquina. **Qué lo llena:** `trabajos/` guarda **todas** las tizadas generadas para siempre (medido acá: **1,7 GB en 215 carpetas**). **Cambios:** (1) **`LIBERAR-ESPACIO.bat`** — muestra el espacio y qué ocupa cada cosa, y borra sólo lo regenerable (tizadas más viejas que N días, `dist\*.zip`, `deteccion_cache`, `piezas_cache`); **no toca `datos/` ni `entrada/`**, pide confirmación y dice cuántos MB liberó. (2) `GET /api/salud` trae el chequeo **`disco`**: avisa por debajo de 3 GB y marca CRÍTICO por debajo de 1 GB, diciendo que publicar y generar van a fallar. (3) `actualizaciones.guardar` **protege todo lo que escribe** (`makedirs`, el temporal, `os.replace`, `_escribir` estaban fuera del `try`): sin eso, un disco lleno o un archivo tomado daban un **500 pelado** sin ninguna pista — ahora vuelve el motivo real.

- **2026-07-29 (143) — `ERR_QUIC_PROTOCOL_ERROR`: no es la app, y ahora la pantalla no queda en blanco.** El usuario reportó `GET …/assets/index-*.js net::ERR_QUIC_PROTOCOL_ERROR 200 (OK)` **en todos lados**. No es un error de la aplicación ni del archivo: es **transporte**. Chrome pide por **HTTP/3 (QUIC, sobre UDP)** y la transferencia se corta después de que el servidor ya respondió 200 — por eso el estado dice OK y aun así falla. Flask/Werkzeug **no habla HTTP/3**, así que lo anuncia algo delante (CDN tipo Cloudflare, o IIS/nginx con HTTP/3). Se identifica con `curl -sI <url>` mirando **`alt-svc: h3=…`** (quién lo ofrece), `cf-ray`/`server` (quién está adelante); se apaga en ese componente, no en el código. **Lo que sí se arregló acá:** cuando el bundle no bajaba, el usuario se quedaba con una **pantalla en blanco sin ninguna explicación** y sin saber que alcanzaba con recargar. `frontend/index.html` ahora trae un aviso propio — «No se pudo cargar la aplicación · el programa está bien, falló la descarga» + botón **Recargar** — que aparece **sólo** si a los 12 s el `#root` sigue vacío, o antes si un `<script>`/`<link>` dispara un `error` de carga (eso es concluyente y no espera). **Verificado en el navegador**: con la app cargada normalmente el aviso queda en `display:none` y `#root` tiene contenido (o sea, **no da falso positivo**, que sería peor que la pantalla blanca); forzándolo se ve el texto y el botón correctos. Los 12 s son holgados a propósito: una conexión lenta no tiene que disparar el cartel.

- **2026-07-29 (142) — LA TELA AHORA ES POR (DISEÑO, MOLDE), no por molde.** El usuario preguntó qué pasa si dos diseños del MISMO pedido usan el MISMO molde: ¿la tela queda separada o se pisa? **Se chequeó de punta a punta y se pisaba**, en los tres eslabones: el front guardaba `telaPorPieza[pid]` (sin lugar para el diseño), el payload armaba un solo `asignaciones[pid]`, y el server resolvía la asignación **antes** de partir las filas por diseño (`por_diseno` viene después) → los dos diseños salían cortados **en la misma tela**, y cambiarla en uno la cambiaba en el otro sin avisar. Otra vez el error que no falla y sale bien impreso. **Decisión del usuario:** cada diseño su tela. **Cambios:** front — `telaPorPieza` pasa a `{"<disenoId>|<pid>": {pieza: telaId}}` (por **id** de diseño, para que renombrarlo no pierda la asignación), con lectura compatible (`_telasDe` cae a la clave vieja para los pedidos a medio armar) y escritura siempre en la clave nueva; el payload manda `asignaciones = {pid: {slug_diseño: {pieza: tela}}}`, convirtiendo id → **slug del NOMBRE**, que es como el motor agrupa las filas (`_slugify_diseno`). Server — la asignación se arma en `_asig_de(dslug)` y se resuelve **dentro** del bucle `por_diseno`; **COMPAT**: el formato plano viejo se reconoce porque sus valores son textos y no diccionarios, y se aplica a todos los diseños como antes. La **traba** (`_validar_pedido`) acepta ahora una función `dslug → asignación` y valida cada fila con la tela de SU diseño — si no, una pieza sin tela en un solo diseño pasaba desapercibida. **Verificado:** con el formato nuevo, `remera-a` sale en Dry Basket y `remera-b` en Delta con el mismo molde; con el formato viejo los dos siguen dando lo mismo que antes.

- **2026-07-29 (141) — 🔴 «MI ARTÍCULO» SIN DUEÑO: el estado imposible que explicaba todo.** El usuario cerró el diagnóstico: el molde raro **lo había creado desde Mis artículos** y «quedó bugiado». El estado es `propio: true` + **`creado_por: null`**, y se comporta de las dos formas a la vez: **no** cuenta como privado (`_es_privado` = propio AND creado_por → False) así que **se cuela en Configuración**, y a la vez `get_productos` lo marca **`propio: true` para CUALQUIERA** (por la rama `not creado_por`) así que aparece en **«Mis artículos» de todos**. Encaja con los tres síntomas que reportó: «me dice sin dueño», «aparece en Configuración» y «lo creó desde Mis artículos». **Cómo se llega:** `_guardia_moldes` deja pasar con un usuario de mentira (`_u = True`) cuando la base parpadea —a propósito, «la seguridad no puede tumbar el sistema»— y acto seguido `_uid_actual()` devuelve None; el alta crea el artículo sin dueño. **Prevención:** `crear_producto` **rechaza** un `propio: true` sin dueño cuando el sistema de usuarios está activo («Se perdió tu sesión: volvé a entrar»). Sin sistema de usuarios sigue siendo legítimo (no hay a quién sellar) y no se toca. **Reparación automática** en `_cargar_catalogo`: si se sabe quién lo cargó (`alta_por`) **se le devuelve a esa persona**; si no se sabe, pasa a ser **del sistema** —lo único que se puede afirmar de algo sin dueño— y se avisa en el log, porque es un cambio visible. **Verificado** con los cuatro casos: el roto sin `alta_por` pasa al sistema y **deja de figurar como «mío» para terceros**; el roto con `alta_por` vuelve a su dueño y sale de Configuración; el sano y el del taller no se tocan. Contrato en `verificar_permisos_molde.py`, incluidas las aserciones que **prueban la hipótesis del síntoma** (el estado roto no es privado y sí se ve como propio de un tercero). ⚠️ **Aparte:** se agregó **`GET /api/productos/diagnostico`** (sólo lectura) — dice, molde por molde y para la sesión abierta, `personal`/`lo_ves`/`aparece_en_configuracion` y el motivo en castellano. Existe porque el sistema publicado corre en otra máquina y con otros usuarios: «no me aparece» no se puede diagnosticar a ciegas. ⚠️ **Y una aclaración que costó tiempo:** la base ES Microsoft SQL Server (`Microsoft SQL Server 2022, Express Edition`); **«Express» es una EDICIÓN de SQL Server**, mismo motor y mismo driver. `localhost\SQLEXPRESS` es sólo el valor por defecto de la máquina de desarrollo cuando no está `TIZADA_DB_SERVER`; en producción esa variable apunta al servidor real, y por eso **desde el entorno local no se ven los datos de producción**.

- **2026-07-29 (140) — 🔴 EL «MI ARTÍCULO» DE UN USUARIO SE COLABA EN CONFIGURACIÓN PARA OTRO ADMIN.** Reporte: *«le aparece en configuraciones un molde creado por el usuario admin que lo creó dentro de mis artículos»*. **Es la misma trampa que la entrada 136, por otra puerta:** `propio` significa **«es MÍO»** y lo calcula el server **según quién mira**. Un artículo de admin (`propio: true, creado_por: 1`) visto por **otro admin** llega con **`propio: false`** — y como los admin tienen `molde.ver_todos`, lo VEN. El filtro de la grilla de Configuración era `!p.propio`, así que ese artículo ajeno entraba al espacio del taller; lo mismo en el catálogo del pedido, donde `varsCatalogo` había quedado sin filtro (entrada 136). **Arreglo:** campo nuevo **`personal` = `_es_privado(p)`**, que **no depende del espectador** — es «esto es un artículo personal», sin importar de quién. La grilla de Configuración filtra por **`personal`**; el catálogo del pedido saca sólo los de OTRO (**`de_otro`**), conservando el arreglo de la 136 (el dueño sí ve sus propias variables); el aviso de «todavía no se puede pedir» también pasa a `personal`. **Verificado con los tres espectadores del caso real** — admin (dueño), felipe (otro admin) y un operario: felipe veía en Configuración `[Molde del taller, Artículo de admin]` y ahora ve `[Molde del taller]`; sus variables en el catálogo bajan de 2 a 1; admin no pierde nada (su artículo sigue en «Mis artículos» con sus variables usables); el operario ni lo ve. **Regresión en el build:** falla si la grilla de Configuración deja de filtrar por `personal` — **se lo vio fallar** reponiendo `!p.propio`. ⚠️ **Regla general (ya van tres veces):** `propio` y `de_otro` responden «¿es mío?» / «¿es de otro?»; para «¿esto es de alguien?» está **`personal`**. Nunca decidir en qué ESPACIO va una cosa con un campo que cambia según quién mira.

- **2026-07-29 (139) — «No lo deja borrar moldes, ¿por qué?»: el botón se escondía sin decir nada.** Al gatear las acciones por permiso (entrada 124) **escondí** el tacho cuando falta `molde.borrar`. Esconder no explica: el usuario ve que «no lo deja» y no tiene cómo saber por qué. Ahora el botón **se muestra APAGADO**, con el motivo en el tooltip y un aviso al tocarlo, señalando dónde se arregla (*Configuración › Usuarios y permisos*). El 403 del server también dice ahora el permiso que falta y dónde se da; y distingue el otro caso —artículo privado de otro— con su propio mensaje. **Las tres cosas que bloquean borrar, y sólo una es de permisos:** (a) **`prod_default` («Molde 1») no lo borra NADIE**, es el molde por defecto y está cortado en el front y sin tacho; (b) falta el permiso **`molde.borrar`**; (c) es un «Mi artículo» de otro usuario (pero esos ya ni se listan en Configuración, entrada 137). ⚠️ **Ojo con «tiene usuario admin»:** el permiso viene del **ROL**, y de los tres que trae el sistema sólo **Administrador** incluye `molde.borrar` — **Diseñador tiene `molde.crear` y `molde.editar` pero NO `molde.borrar`**, y Operario sólo `molde.ver`. Un usuario «administrador» que en realidad tenga el rol Diseñador crea y edita pero no borra: es el caso más probable. El rol Administrador es de sistema y sus permisos no se pueden cambiar; para que otro rol borre, hay que agregarle el permiso a ESE rol.

- **2026-07-29 (138) — MIGRACIÓN AUTOMÁTICA: las molderías de Configuración que quedaron con dueño pasan a ser del sistema.** El usuario necesitaba arreglar los datos **del sistema ya publicado en Amazon**, sin entrar al servidor a correr nada. Por eso la migración vive en **`_cargar_catalogo`** y no en un script aparte: se aplica sola en la primera lectura del catálogo después de desplegar. Qué hace: todo producto con `creado_por` y **sin** `propio` (o sea, cargado desde Configuración cuando el alta sellaba dueño siempre) pasa a `creado_por = None` y su dueño se conserva en **`alta_por`** — no se pierde el dato de quién lo cargó, deja de usarse como propiedad. **CORRE UNA SOLA VEZ Y QUEDA MARCADO** (`catalogo.migracion_dueno_config`). El usuario preguntó, con razón, si «en cada actualización se comparten los moldes» — **no**: sin la marca esto sería una REGLA PERMANENTE («todo lo que tenga dueño y no sea propio, liberalo») y cualquier cambio futuro que volviera a sellar `creado_por` en un molde compartido terminaría compartiendo moldes en el próximo despliegue. Con la marca no puede. Verificado: se agregó a mano un molde con dueño DESPUÉS de la migración y se simularon 3 despliegues más — **conserva su dueño, no se comparte**. (Además se comprobó que hoy `creado_por` tiene un solo escritor, `crear_producto`, y sólo lo sella para `propio: true`.) Deja una línea en el log con cuántas y cuáles. **Verificado sobre un catálogo simulado como el de producción** (una moldería de Configuración con dueño, un «Mi artículo» y una ya sin dueño): la primera se libera y pasa a verla todo el mundo, el «Mi artículo» **no se toca** y sigue privado, la tercera queda igual; correrlo de nuevo no cambia nada. En los datos locales no había ninguna para migrar, así que no escribió nada.

- **2026-07-29 (137) — LA REGLA DE PROPIEDAD, DICHA POR EL USUARIO.** Textual: *«todo lo que se hace dentro de configuración el dueño es el sistema; todo lo que se hace dentro de pedidos → mis artículos tiene su dueño y es quien tiene sesión iniciada, y lo que no es del sistema no lo puede ver nadie más que ese usuario. Es más, en configuración no debería aparecer, porque usa las mismas herramientas pero se maneja diferente»*. Corrige el modelo que yo había puesto en la entrada 124 (donde `creado_por` se sellaba SIEMPRE como autoría). Ahora: **`crear_producto` deja `creado_por = None` cuando el alta es de Configuración** (el molde es del taller, aunque lo cargue alguien logueado) y sólo lo sella para `propio: true`; **`alta_por`** guarda quién lo dio de alta — trazabilidad, nunca se usa para decidir visibilidad. **La grilla de Configuración ya no lista los «Mis artículos»** (`filter(p => !p.propio)`); se siguen configurando entrando desde su pestaña, con las mismas pantallas. 🔴 **Y un hueco que encontró la propia prueba al escribir la regla:** `_puede_editar_molde` dejaba que **cualquiera con `molde.editar` editara el «Mi artículo» de otro** — en la práctica lo tapaba la guarda de visibilidad, salvo para quien tuviera `molde.ver_todos` (un admin). Ahora **un molde privado lo toca SÓLO su dueño**: `molde.ver_todos` da VER (soporte/auditoría), no escribir. Matriz final verificada — molde de Configuración: felipe ve/no edita, admin ve/edita; «Mi artículo» de felipe: felipe ve/edita, admin ve/**no** edita. Contrato ampliado en `verificar_permisos_molde.py`. De paso se borró `_moldePropio`, que quedó sin uso tras la entrada 136.

- **2026-07-29 (136) — 🔴 EL DUEÑO DE UN MOLDE ERA EL ÚNICO QUE NO PODÍA USAR SU PROPIA VARIABLE.** Reporte del usuario, textual: *«felipe entró a configuración, cargó un molde, lo configuró y no le aparece la variable para usar; pero si entro del usuario admin sí me aparece»*. **Causa:** `propio` no es un dato del molde, **lo calcula el server según QUIÉN MIRA** — `bool(p.propio) and creado_por == vos` (§10.d). Para el DUEÑO da `true`, para cualquier otro `false`. Y el paso «Diseños» del pedido hacía `varsCatalogo = variablesDisponibles.filter(v => !_moldePropio(v.moldeId))` → **al dueño le sacaba justo sus variables**, mientras al resto se las mostraba. En «Mis artículos» tampoco aparecían: ahí el molde se elige **entero**, ignorando sus variables. Resultado exacto del reporte. **Reproducido** con un banco en Node: el dueño veía **0** variables y otro usuario **1**; con el arreglo, **1 y 1**. **Arreglo (una línea):** `varsCatalogo = variablesDisponibles` — en el Catálogo van **todas** las variables que se pueden usar. Un molde propio SIN variables no aporta ninguna, así que incluirlos no ensucia: sólo aparece lo que alguien configuró de verdad. Además, la tarjeta de «Mis artículos» ahora avisa «N variables → Catálogo» cuando el artículo tiene variables, para que se sepa dónde se eligen (ahí el molde se toma entero). **Regresión en el build:** `verificar_guias.mjs` falla si `varsCatalogo` vuelve a filtrar por `_moldePropio` — **se lo vio fallar** reponiendo el filtro. ⚠️ **Lección general:** un campo que el server calcula **por espectador** (`propio`, `de_otro`) no se puede usar como si fuera una propiedad del objeto; filtrar por él hace que cada usuario vea un sistema distinto.

- **2026-07-29 (135) — 🔴 LA 2ª PIEZA AGREGADA QUEDABA HUÉRFANA + por qué un molde «no se ve en Pedido».** **(1) El bug, mío:** `_ruta_entrada("plantilla.ai", pid)` devuelve la versión **VIGENTE**, y `pieza_agregar` le pasaba ESA a `agregar_pieza`, que versiona sobre lo que recibe. Resultado: la 2ª pieza generaba **`plantilla.v1.v1.ai`** + un puntero paralelo `plantilla.v1.ver`, mientras el puntero bueno (`plantilla.ver`) seguía en 1 → **el sistema seguía sirviendo el archivo con UNA sola pieza y la segunda quedaba invisible**. Se vio en el molde real del usuario (138 / 139 / 140 contornos en tres archivos, con el vigente en el de 139). Arreglo: se separan **`pl_base`** (`original=True`, sobre la que se versiona) y **`pl`** (la vigente, de la que se lee la geometría). **Regresión:** la prueba agrega **dos piezas seguidas** y exige contador de versiones en 2, **cero archivos huérfanos** (`.v1.v*` / `.v1.ver`) y el molde vigente con las dos piezas — se lo vio fallar con el código viejo. No hubo que reparar datos: el usuario ya había borrado ese molde, y su registro estaba vacío (no había nombrado nada). **(2) «Creé un molde desde Configuración y después no lo veo en Pedido».** No es un problema de usuario ni de permisos: **se verificó que el Pedido no filtra por dueño en ningún lado**. Es que **el Pedido es VARIABLE-FIRST** — se elige una VARIABLE, no un molde (`variablesDisponibles` exige `valores[].pieza_idx != null`), y un molde recién creado no tiene ninguna. El sistema no lo decía en ningún lado. Ahora el paso «Diseños» muestra un aviso listando las molderías que **todavía no se pueden pedir**, con el motivo («no tiene ninguna variable con piezas») y el camino exacto: *Configuración › Molderías › X › Variables → 1. Nombrar → 2. Grupos*. **(3)** Confirmado con el usuario: **duplicar una pieza y que quede sin nombre está bien** — se nombra después, como cualquier pieza sin nombrar.

- **2026-07-29 (134) — AGREGAR PIEZA ERA UN CAMINO DE IDA: ahora se puede DESHACER.** El usuario duplicó una pieza y reportó «quedó guardado y me movió todo el resto». **Se auditaron sus datos reales antes de tocar nada: el registro estaba INTACTO — 0 de 2740 entradas apuntando a otra pieza.** El remapeo hizo su trabajo; lo que se movió fue la NUMERACIÓN: la pieza cayó en el **número 102 de 139** (la marcó en el medio del molde, que va de x=14 a x=1584 cm) y **37 piezas** corrieron su número. Los nombres no se movieron. **El problema real era otro: no había vuelta atrás.** El archivo del molde se versiona (`plantilla.v<N>.ai`), pero el **registro se sobreescribía sin respaldo**, así que los `pieza_idx` de antes se perdían. Arreglos: (a) `pieza_agregar` **copia el registro a `.antes_pieza` antes de pisarlo**; (b) **`POST /api/plantilla/pieza_deshacer`** saca la última pieza agregada — mueve el puntero de versión a la anterior, borra el archivo nuevo y restaura el registro; si no hay respaldo (las altas hechas antes de esto, como la del usuario) **reconstruye el mapa inverso** comparando las dos versiones del molde, que es determinista: la pieza que sobra en la nueva dice en qué posición se insertó y todo lo que va de ahí en adelante vuelve un lugar atrás; (c) `get_productos` devuelve **`piezas_agregadas`** (= versiones del archivo) para que la pantalla pueda ofrecer el botón, con confirmación propia y aclarando que lo nombrado no se pierde. **Verificado en `verificar_agregar_pieza.py`**: tras agregar y deshacer, el registro vuelve **idéntico** al de antes (`reg_vuelta == reg`), sin avisos. ⚠️ **Lección:** el archivo estaba versionado pero el registro no — «reversible» hay que verificarlo sobre TODO lo que la operación escribe, no sólo sobre lo obvio.

- **2026-07-29 (133) — AGREGAR PIEZA: 14× más rápido, avisa qué número le toca, y el archivo tiene que traer TODOS los talles.** Tres cosas que marcó el usuario. **(1) LA DEMORA.** `_candidatos_mesa` llama a `page.get_drawings()` **una vez por talle**, y los 20 talles son CAPAS DE LA MISMA PÁGINA → se barría la página entera 20 veces, y el alta lo hacía DOS veces (antes y después). `PM.detectar_por_talle` ahora barre **una sola vez** y agrupa por capa: **0,9 s contra 12,2 s** (verificado que da EXACTAMENTE lo mismo que el camino lento — de ese orden sale el `pieza_idx`, así que la prueba lo compara). Y la segunda pasada **se eliminó**: como el orden es por `(x0, y0)`, la posición de la pieza nueva se **calcula** (`bbox_desplazado` + `indice_de_insercion` + `mapa_insercion`); la prueba verifica que el mapa calculado y el bbox predicho coincidan con los medidos. En total, de ~40 barridos a 1. **(2) LA NUMERACIÓN.** El usuario pidió que la pieza nueva tome «el siguiente número del último registrado, así no cambia el de otra». No se puede garantizar siempre: **el número ES la posición** (las piezas se ordenan por su X), así que ponerla en el medio corre a las que siguen. Pero **sí se puede decir antes**: el panel calcula en vivo «va a quedar como la **pieza N**» y, si corresponde, «y le corre el número a las **M** que están más a la derecha — si no querés que se muevan, marcala **a la derecha de todo**». Marcándola a la derecha de todo el usuario obtiene exactamente lo que pidió, y lo ve antes de confirmar. (El remapeo sigue: los NOMBRES nunca se mueven, cambie o no el número.) **(3) EL ARCHIVO TIENE QUE TRAER LA PIEZA EN TODOS LOS TALLES** — lo pidió él y tiene razón: una pieza de moldería cambia de forma con el talle, meter la misma forma en los 20 daría una pieza que no escala y saldría mal cortada en 19. Ahora `pieza_archivo` cuenta los contornos y avisa al subir (no se deja marcar el lugar para fallar recién al final), `pieza_agregar` rechaza con 422 explicando cuántos trajo y cuántos hacen falta, y el botón queda deshabilitado. Convención: **de menor a mayor área ↔ los talles en el orden del molde** (que va del más chico al más grande); si sobran contornos se usan los N más grandes. Al **duplicar** esto ya estaba bien: cada talle copia la geometría DE ESE talle.

- **2026-07-29 (132) — AGREGAR PIEZAS AL MOLDE: motor + endpoint (⏳ FALTA LA PANTALLA).** Pedido del usuario: «en Configuración → Moldería poder agregar piezas nuevas al molde indicando en qué lugar del lienzo, y poder mover las piezas para organizar». **Decisiones que él tomó** (AskUserQuestion): «espacio» = **lugar del lienzo**; **mover = SÓLO visual**, el archivo del molde no se toca; la pieza nueva sale de **un archivo que sube** o de **duplicar una que ya está**. **Relevamiento previo (hechos, no supuestos):** el molde real tiene **1 sola mesa** (una página) y los talles son **CAPAS OCG**, las 137 piezas conviven en la misma hoja repetidas en 20 capas; **nada en el sistema escribía geometría en el molde** hasta ahora; el `acomodo` de una variable es puramente visual y ni siquiera llega al motor. **Prueba decisiva (sobre una COPIA):** inyectando **operadores de trazado** dentro de la OCG del talle, la pieza **se detecta como una más** (138 → 139) y **no aparece ningún talle nuevo**. Se descartó el camino de `inyectar_editable` (el del arte) por dos motivos concretos: mete la geometría en un **XObject** —que `get_drawings()` ve como un objeto y no como pieza— y crea una capa `Editable …` que en la plantilla **se leería como un TALLE** (`_talles_de_plantilla` toma como talle toda capa que no esté en `CAPAS_SISTEMA`). 🔴 **La mina, medida:** el `pieza_idx` **no es un id, es la POSICIÓN** en el orden por bbox dentro de la capa, así que insertar una pieza corre a todas las que siguen — **1478 de 2760 entradas del registro** en el molde real. Por eso `remapear_registro` cruza la detección de ANTES con la de DESPUÉS **por bbox** (la geometría de las que ya estaban no cambia → el cruce es exacto, no heurístico) y reescribe los `pieza_idx`; lo que no se puede reubicar se deja como está y **se avisa**, nunca se mueve a ciegas. **Módulo nuevo `piezas_molde.py`** (`agregar_pieza`, `ops_de_segmentos`, `firma_contornos`, `mapa_idx`, `remapear_registro`, `contornos_de_pdf`, `detectar_por_talle`) + **`POST /api/plantilla/pieza_agregar`** (guardado con `molde.editar`). La pieza entra en **TODOS los talles** a propósito: si existiera sólo en algunos, el registro queda con un hueco y **la generación explota** (`registro[pieza][talle]`, sin guarda en el motor); al duplicar, en cada talle se copia **la geometría de ESE talle**, así la pieza nueva acompaña la progresión. Se escribe una **VERSIÓN** (`plantilla.v<N>.ai` + `plantilla.ver`, el mismo mecanismo del arte): el archivo del usuario no se toca. Y se limpian las cachés derivadas (`_invalidar_cache_molde`: detección, nido en memoria y en disco, `piezas_cache`, toggles) — ninguna se invalida sola, porque el archivo vigente pasa a ser otro. **PRUEBA:** `verificar_agregar_pieza.py` (raíz) corre sobre una **copia** del molde real: verifica el remapeo puro, que la pieza entre en los 20 talles, que no aparezcan talles nuevos, que el original quede intacto, que **ninguna** pieza quede apuntando a otro contorno tras remapear — y **cuenta cuántas quedarían mal sin el remapeo** (1478), o sea que la prueba prueba algo. **LA PANTALLA (misma tanda):** bloque **«Agregar una pieza»** en Configuración → Moldería, debajo de «Re-subir Plantilla». Dos caminos —**⧉ Duplicar la elegida** (usa la pieza tocada en el visor) y **Subir un archivo** (`POST /api/plantilla/pieza_archivo`, que sólo la guarda y la mide: si el alta falla, el molde queda como estaba)— y después **se toca en el visor dónde va**, con **cruz + contorno fantasma** del tamaño real antes de escribir nada. Al confirmar se recarga la detección, se tira el nido y se avisa que hay que nombrarla en Variables · Paso 1. 🔴 **UNIDADES, que es lo más fácil de romper:** el visor está dibujado a **px = mm** con la Y para ABAJO; el lienzo del PDF va en unidades crudas (CM/10 por mm) con la Y para ARRIBA. **Y las coords «crudas» de `molde_real` YA SON coordenadas PDF** (`cb.y1 - r.y1/U` = medidas desde el borde inferior): voltearlas otra vez en `ops_de_segmentos` ponía la pieza reflejada — se pedían 80 mm hacia abajo y daba **5297**. Lo cazó la prueba, que ahora mide dónde cayó: «colocada a 120 mm en X y 80 mm hacia abajo (se pidió 120 y 80)». ⏳ **PENDIENTE: el acomodo visual a nivel molde** (mover las piezas del molde entero y que la posición se guarde). Hoy «Acomodar piezas» mueve en el visor pero esa posición sólo se persiste por el camino del emparejado.

- **2026-07-29 (131) — FUERA el paso «3. Modelos» de Variables.** Pedido del usuario: no se usa. La pestaña Variables queda en **2 pasos: 1. Nombrar · 2. Grupos**. Se sacaron el bloque `varStep === 'combinar'` (76 líneas) y todo lo que sólo vivía para él: los estados `modelosEdit`/`modeloSel`/`varSel`/`modeloAbierto`/`nuevoModeloNombre`, las funciones `guardarVariablesModelos`/`guardarModelosCon`/`addModelo`/`renameModelo`/`delModelo`/`addVariable`/`renameVariable`/`delVariable`/`setBuild`, la siembra de esos buffers y la limpieza del `build` en `delTipo`. También el texto del menú de ajustes y los dos pasos del recorrido explicativo de Variables (el chequeo del build valida que las anclas sigan existiendo). ⚠️ **NO se tocó ni el endpoint `POST /api/productos/modelos` ni lo ya guardado en `prod.modelos`**: sacar una pantalla no es motivo para borrarle datos a nadie, y el motor nunca los usó (se comprobó: `modelos` sólo aparecía en el catálogo, en `get_productos` y en esa pantalla). Si más adelante se decide borrarlos de verdad, es una migración aparte y con el usuario.

- **2026-07-29 (130) — 🔴 RENOMBRAR UNA PIEZA LA HACÍA DESAPARECER DEL VISOR DEL ARTE (regresión mía) + selección múltiple en el nido.** **El bug, que es del append-only de la entrada 123:** `_regenerar_piezas_index` retiraba las entradas **por CLAVE**, así que al renombrar una pieza —que es exactamente lo que el ancla permite: **el id NO cambia**— quedaban DOS entradas con el **mismo id**, la viva con el nombre nuevo y una «retirada» con el viejo. Todo el que arma un `{id: clave}` recorriendo la lista se queda con **la última**, o sea el NOMBRE VIEJO; con eso las variables dejaban de matchear contra el visor y **las piezas renombradas desaparecían**. En el molde real eran **24 ids duplicados, todas mangas** (`piezas.json` con 172 entradas para 137 piezas). Lo reportó el usuario como «en el visor del arte no se me ven las mangas». **Arreglo en tres capas:** (a) sólo se retira lo que de verdad se fue — `p_prev["id"] not in _ids_vivos`; (b) `res["piezas_id"]` (detección) ya **no manda las retiradas**: son historial para no reciclar ids, no algo que el front tenga que filtrar; (c) los 3 `id2clave` del front ignoran `retirada` (un `piezas.json` viejo sigue trayéndolas). **Datos reparados**: se sacaron las 35 entradas retiradas que pisaban un id vivo (172 → 137), con respaldo `.bak_dupids`; verificado que las 2 variables resuelven **8/8 y 11/11** a piezas reales del registro. **Regresión:** `verificar_piezas.py` exige que no queden retiradas con id vivo ni ids repetidos — **se lo vio fallar** reponiendo el retirado por clave. **Y lo pedido:** en la moldería de una variable, **apretar el botón izquierdo en un espacio vacío arrastra un recuadro** que selecciona varias piezas (basta con tocarlas, no hace falta encerrarlas), las seleccionadas se marcan con un contorno punteado y **se mueven todas juntas** en un solo guardado (`guardarAcomodoPiezas`); agarrar una pieza que no está en la selección pasa a seleccionarla sólo a ella, y **un clic en el vacío deselecciona**. El paneo del visor sigue en el botón derecho, así que el izquierdo quedaba libre. Coordenadas vía `getScreenCTM()` — vale con cualquier zoom y paneo sin repetir la cuenta a mano.

- **2026-07-29 (129) — «Dice 8 piezas y veo 3»: DOS pérdidas silenciosas + el encuadre del visor.** **(1) 🔴 EL EXTRACTOR NO LEÍA LOS CUADRILÁTEROS.** `_contorno_de` (`molde_real.py`) recorre los `items` de PyMuPDF y sólo manejaba `l`, `c` y `re`: una pieza dibujada **sólo con quads (`qu`)** salía con `segmentos == [("h",)]`, o sea **sin un solo punto**. No fallaba — la pieza se DETECTABA (tiene bbox) y después `_bbox_segs` devolvía `None` y `nido_piezas` la salteaba con un `continue`. En el molde real eran 2 tiras finas, **«Cuello 4» y «Tapa costura»** (102 y 99 unidades de alto): el registro tenía 137 piezas y el nido 135. Ahora se emiten los 4 lados del quad; verificado sobre el molde del usuario: **0 contornos sin geometría** (antes 2) y las dos piezas recuperan su bbox. ⚠️ Esto no era sólo el visor: el contorno es lo que se usa como **clip** al armar la pieza, así que cualquier cosa dibujada con quads venía sin recorte útil. **Clave del nido a `v7`** — los nidos cacheados con `v6` se armaron sin esas piezas y su clave (mtimes de plantilla y registro) no cambia, así que no se invalidaban solos. **(2) EL CRUCE NIDO↔VARIABLE ERA POR NOMBRE.** El front cruzaba las piezas de la variable con las del nido usando el mapa id→clave que venía en la DETECCIÓN, que está cacheada y nadie vuelve a pedir: al renombrar una pieza el mapa quedaba viejo y **una variable de 8 piezas mostraba 3** (justo las que no habían cambiado de nombre). Ahora `/api/plantilla/nido` devuelve el **`pieza_id`** de cada pieza (`_nido_con_ids`, resuelto FUERA del caché del nido porque los ids cambian por su cuenta) y `nidoVarPiezas` cruza **id ↔ id**; el nombre queda sólo para mostrar, y los valores todavía sin id se suman por nombre. **(3) EL ENCUADRE.** El lienzo del nido lleva un margen enorme a propósito (para arrastrar una pieza lejos sin toparse con un borde invisible), pero «Ver todo» encuadraba **ese lienzo**, así que las piezas quedaban mínimas y corridas a un rincón — el usuario lo describió como «aparecen por cualquier lado». `nidoLayoutVar` ahora devuelve también la **`caja`** (dónde están realmente las piezas, ya con su `acomodo`) y `verTodoVisor` encuadra la caja, no el lienzo (`_encuadrarCaja`). Y el efecto de auto-encuadre sumó **`grupoAislado`, `varStep` y `nidoData`** a sus dependencias: al abrir una variable el svg pasa a usar el viewBox del nido, no `canvasLayout.vb`, así que antes no se re-encuadraba nada. Como la caja incluye el acomodo, **después de acomodar encuadra lo acomodado**. ⚠️ Se borró el `deteccion_cache` de ese molde (es caché derivada, se rehace sola) para forzar la re-detección con el extractor arreglado.

- **2026-07-29 (128) — LA VISTA DE TODOS LOS TALLES VUELVE A SER INSTANTÁNEA (regresión mía).** Reporte del usuario: *«si asigno una pieza a una variable debe mostrarse al toque; si entro a la variable debo ver todas las variantes de una»*. **Lo rompí yo en la entrada 122** arreglando el bug 10. Dos fallas encadenadas: **(1)** `guardarGruposCon` llamaba a `invalidarNido()`, pero **el nido es la GEOMETRÍA de las piezas del registro** — tocar qué piezas tiene una variable NO lo cambia, sólo cambia cuáles se muestran, y eso `nidoVarPiezas` ya lo recalcula solo con `variantesEdit`. **(2)** el `useEffect` que pide el nido **no tenía `nidoData` en sus dependencias**, así que al ponerlo en `null` nadie lo volvía a pedir: si ya estabas adentro de la variable no cambiaba ninguna otra dep. Resultado: guardabas y **la vista de todos los talles desaparecía hasta recargar la página**. Arreglo: sacar la invalidación de `guardarGruposCon` (queda sólo donde cambia el REGISTRO: subir molde, nombrar piezas, emparejado) y meter `nidoData`/`nidoLoading`/`nidoError` en las deps — no hace loop porque al terminar o hay datos o hay error. Además **`_nidoGen`**: una respuesta del nido que venía en camino cuando se invalidó se descarta en vez de pisar la nueva. **`nidoVarPiezas` ya no pierde piezas:** resolvía todo-o-nada (si UN valor resolvía por `pieza_id`, los que no resolvían **desaparecían**); ahora resuelve valor por valor con fallback al `label`. Y **`set_variantes` refresca el `label`** con el nombre de hoy: renombrar una pieza no reescribe las variables (se atan por `pieza_id`, que es lo correcto) pero la pantalla seguía mostrando el nombre viejo. **VERIFICADO sobre los datos reales del usuario, que renombró piezas mientras se trabajaba** (`Manga Derecha 5` → `Manga Corta Derecha 5`): los **17 valores** de sus 2 variables siguen resolviendo bien por `pieza_id` — la identidad estable (entrada 123) aguantó el renombrado. ⚠️ **Corrección a la entrada 127:** cuando se diagnosticó, ese molde no distinguía corta/larga; **ahora sí** (13 piezas «corta» + 11 «larga»), porque el usuario las renombró a las 11:17. **Regresión en el build:** `verificar_guias.mjs` ahora exige que el efecto del nido dependa de `nidoData` y que `guardarGruposCon` NO lo invalide; **se vio fallar a los dos** inyectando cada bug por separado.

- **2026-07-29 (127) — TRABA ANTES DE FABRICAR: la hoja fantasma «Principal» y la opción que el molde no tiene.** El usuario reportó dos cosas del mismo pedido, y las dos son del mismo tipo: **no fallaban, producían algo que PARECE correcto**. Diagnosticadas sobre el trabajo REAL `20260729-105151-9bb2`. **(1) HOJA FANTASMA.** Con una sola tela elegida salían DOS hojas: la buena (`Dry Basket 1,60`, 157 cm de ancho, 2 páginas) y una **`Principal` de 6,8 cm** con ancho 180 (el default del nesting, no el de ninguna tela real). Causa: `TELA(p)` en el motor devuelve `"Principal"` para cualquier pieza sin tela asignada — un resto de antes del sistema de telas. Y el pedido **no tiene tela base a propósito** («cada pieza debe tener SÍ O SÍ una tela»), pero el aviso de «faltan N piezas sin tela» sólo mira las piezas **que se ven en el visor**, así que las que quedan afuera se colaban sin tela y se iban a la hoja inventada. Simulado sobre el molde real: las que faltaban eran `Cuello 12` y `Tapa costura` — dos piezas chicas, consistente con esos 6,8 cm. **(2) OPCIÓN QUE EL MOLDE NO TIENE.** Dos filas en «Larga» sobre un molde cuyas **24 piezas de manga no dicen ni corta ni larga** (se llaman «Manga Derecha 5», «Manga izquierda 5»). `partes_de` decide por el NOMBRE: si las piezas dijeran «Manga Corta …», elegir «Larga» las saca a TODAS y **la prenda sale sin mangas, en silencio**; y como acá no dicen ninguna opción, elegir Corta o Larga da exactamente la misma tizada — la columna miente. **ARREGLO.** Helpers nuevos a nivel de módulo en `motor_pedido.py` (**`tokens_pieza`**, sacado de adentro de `generar_pedido`, y **`opciones_soportadas`**) para que la validación use LA MISMA normalización que el motor — si usara otra, diría que una opción existe y después el motor no encontraría piezas. En `servidor.py`: **`_toggles_de_template`** (extraído de `_traducir_prendas`, ahora compartido), **`_toggles_disponibles(prod, cat)`** → `{clave: {opciones, col, "*": {op:n}, "<v_xxx>": {op:n}}}`, expuesto en `GET /api/productos` como **`toggles_piezas`** (cacheado por mtime del registro + firma de plantilla/variables: es el endpoint más caliente), y **`_validar_pedido`**, que corre en `generar_multi` ANTES de fabricar y devuelve **422** diciendo **qué fila** corregir. ⚠️ **La primera versión de la traba era demasiado dura y se comía las 5 filas del pedido real** (deadlock: con ese molde no se podía generar nunca). Distinción final, en `_opcion_sin_piezas` / `_toggle_no_distingue`: **traba** sólo si el molde SÍ distingue las opciones y la elegida no tiene piezas (ahí se pierde una parte de la prenda); si **ninguna** opción se distingue, **avisa pero no traba** — lo que sale es correcto igual; y si el toggle no toca ninguna pieza de esa variable (una musculosa), no hay nada que decir. **FRONT:** en la planilla, la opción que el molde no tiene sale **tachada y apagada**, y al tocarla dice «El molde «X» no contiene manga larga» (o «no distingue manga: sus piezas se usan igual con cualquier opción»); las filas que la lleven cuentan como inválidas y **bloquean Enviar**, con el mismo criterio que el server. **PRUEBAS:** `verificar_traba_pedido.py` (raíz) — cubre las 5 formas del toggle (distingue / sólo una opción / genérico / la variable no lleva esa parte / acentos y mayúsculas) y las dos trabas. **Verificado replayando el trabajo real**: con las telas completas ya no traba (no hay deadlock) y con piezas sin tela corta nombrando `Cuello 12` y `Tapa costura`.

- **2026-07-29 (126) — LA COLUMNA DE BOTÓN SIEMPRE TIENE UNA OPCIÓN PRESIONADA.** Pedido del usuario: *«en esa opción de multi opción en forma de botón siempre debe de tener una presionada como predeterminada»*. Antes la celda podía quedar **sin ninguna marcada** (fila nueva, o tras Supr), y encima las dos capas de la misma celda no coincidían: la estática no marcaba ninguna y la de edición sí marcaba la primera. **La opción por defecto es la PRIMERA de la lista** — para cambiarla se reordenan las opciones en la regla/columna. Se eligió esa y no otra porque **es la que el servidor ya usaba al generar** (`armar_pedido`: `val or opciones[0]`), así que lo que se ve presionado es exactamente lo que sale en la tizada. Helpers nuevos en `App.jsx`: **`_botonDefault(c)`** y **`_valorBoton(c, v)`**; `_defaultRow` siembra el default en las columnas de botón, y `addPrenda`/`removeFila` (que armaban la fila vacía por su cuenta) pasan a usarlo. **Supr sobre una columna de botón la devuelve a su default**, no la vacía. `PlanillaTester` de Configuración, igual. ⚠️ **No se reescriben las filas ya guardadas** (las viejas con el valor en blanco se DIBUJAN con el default, que es lo que el motor usa igual): no hay que tocarle datos al usuario para arreglar una vista. **De paso, se alineó el servidor:** `_toggle_info` buscaba la regla **sólo por `reglaId`**, y la columna «Manga» de los datos reales NO tiene `reglaId` → caía al literal `"Corta, Larga"` e ignoraba las opciones configuradas en la regla; ahora busca por id **y por comportamiento**, igual que `_reglaDeCol` en el front (si no, la pantalla muestra unas opciones y el motor usa otras). **VERIFICADO sobre la configuración real del usuario**: la fila nueva sale `manga:"Corta"`, y en los 6 estados posibles (vacío, nulo, espacios, cada opción, después de Supr) hay **exactamente una** presionada.

- **2026-07-29 (125) — PLANILLA: la columna de BOTÓN se elige con UN clic (y dos causas, no una).** Pedido del usuario: *«las columnas que son multi opción tipo botón no se toman como el resto de las casillas… no debes de hacer doble click para la opción»*. **Causa 1 — el `dist` era viejo.** El código de un clic (`_colEsBoton`, botones en la capa estática, `_ciclarBoton` con Enter/Espacio, la letra que elige la opción) ya estaba en `frontend/src` pero **NO en el bundle compilado**: se confirmó buscando el literal `Elegir «` dentro de `frontend/dist/assets/*.js` (0 apariciones antes de recompilar, 1 después) mientras un texto vecino de la misma tabla sí estaba. Se recompiló. Para que esto no vuelva a disfrazarse de bug hay un chequeo nuevo en `GET /api/salud`: **`frontend_compilado`** compara el mtime más nuevo de `src` contra el de `dist` y avisa con el comando a correr; **verificado que muerde** (se creó un archivo en `src` → `ok:false`; se borró → vuelve a verde). **Causa 2 — la planilla del pedido leía la config de la columna a medias.** El tipo y las opciones pueden venir de la columna O de su **REGLA** (el preset de «Reglas de planilla»); `PlanillaTester`, las dos vistas previas de Configuración y el `_toggle_info` del servidor ya resolvían con las dos, pero **la planilla del PEDIDO miraba sólo la columna** → una columna de botón definida por una regla (las generalizadas: sisa, capucha…) se dibujaba como **casilla de texto** y había que hacer doble clic para escribir la opción a mano; la de «manga» zafaba de casualidad porque su rol tiene el toggle como default. Ahora todo pasa por los helpers **`_tipoCol` / `_opcionesCol`** (`App.jsx`), usados por `_colEsBoton`, `_opcionesBoton`, `_opcionesDeCol`, `_colEsTexto` y el render de la celda. **Verificado contra la configuración REAL del usuario** (7 reglas + las 6 columnas de «Planilla Estándar»): talle/nombre/número/diseño **no cambian**; «Manga» pasa a mostrar `Corta | Larga` —las opciones que él configuró— en vez del `corta | larga` hardcodeado; y una columna de botón definida sólo por su regla pasa de «casilla de texto, doble clic» a **botón de un clic**. El cambio de mayúsculas es seguro: `partes_de` (motor) y `manga_final` (servidor) comparan en minúscula, y el server ya usaba `"Corta, Larga"` como default.

- **2026-07-29 (124) — EL CATÁLOGO ES DE TODOS: `creado_por` era autoría y se estaba usando como candado.** Reporte del usuario: *«un molde que cargué desde configuración quedó como mi artículo cuando es para todos los usuarios que entren»*. **Causa:** `crear_producto` sellaba `creado_por = usuario actual` **siempre**, y tanto `_puede_ver_molde` como el `propio` de `GET /api/productos` tomaban ese campo como señal de PRIVACIDAD. El comentario del código decía que los moldes del catálogo «se crean sin sesión y quedan sin dueño» — **falso**: se crean desde Configuración, con sesión. Resultado: **toda moldería del catálogo quedaba invisible para el resto de los usuarios** y aparecía en la pestaña «Mis artículos» de su creador. Verificado sobre los datos reales: `Camisetas` (`creado_por: 1`, `propio: false`) la veía sólo el usuario 1. **Arreglo:** la privacidad la decide **`propio`** (lo pone sólo «Subir mi propio molde» del pedido) vía el helper nuevo **`_es_privado(prod)` = `propio and creado_por`**; `creado_por` queda como AUTORÍA y se sigue guardando siempre (lo necesita la regla de CLAUDE.md de no borrar nunca un molde con dueño). **No hizo falta migrar datos**: los campos ya decían lo correcto, lo que estaba mal era leerlos. 🔴 **Y la contracara, que es la mitad que se rompe si esto se arregla a medias:** el candado de hecho del catálogo ERA el dueño — al abrirlo, cualquiera con sesión podía renombrar, re-subir o **borrar** (con `rmtree`) el molde compartido. Por eso, en la misma tanda, **ver dejó de habilitar a escribir**: `_puede_editar_molde(prod, permiso)` + `_guard_molde(pid, permiso)` + `_guard_id(cuerpo, permiso='molde.editar')` — los 15 endpoints `id` heredan `molde.editar`, salvo `activar` (**`None`**: un Operario tiene que poder elegir un molde para trabajar) y `eliminar` (**`molde.borrar`**). Y en `_guardia_moldes` el permiso se exige **por MÉTODO** (POST/PUT/PATCH/DELETE con `pid`), porque son ~30 rutas y la que se olvide queda abierta; las de sólo lectura/generación van en `_API_LEE_CON_PID` (`arte/preview_piezas`, `generar`, `generar_multi`). **Su propio «Mi artículo» lo configura siempre su dueño, sin permisos** — para eso está esa pestaña, y el Operario justamente no tiene `molde.editar`. **Sin sistema de usuarios se puede todo** (`_USUARIOS_ON`), y además un molde privado ya no queda inaccesible cuando no hay nadie que pueda reclamarlo. **Alta:** crear en el CATÁLOGO pide `molde.crear`; subir «mi propio molde» no. La **unicidad del nombre** se partió en dos espacios: «Mi artículo» único **por dueño**, catálogo único **entre todos** (si fuera por dueño, dos personas dejarían dos «Camiseta» en la misma grilla). **UI:** `puedo(clave)` en `App.jsx` (pinta, no protege) esconde **Configuración** sin `config.ver`, **Nueva Moldería** sin `molde.crear` y el **tacho** sin `molde.borrar` — si no, el arreglo del server se vería como 403 en pantalla. **PRUEBAS:** `verificar_permisos_molde.py` (raíz), y se lo vio **fallar** en los dos frentes: contra la lógica vieja muerden las de visibilidad (el Operario y el Diseñador no veían el catálogo), y **contra el arreglo INGENUO** —visibilidad corregida pero sin permisos— muerden las de escritura (el Operario editaba el catálogo, el Diseñador lo borraba). ⚠️ Sin verificar contra la app real: pide login.

- **2026-07-28 (123) — AUDITORÍA DE «CREAR MOLDERÍA» (2ª mitad): los 18 bugs cerrados.** Cierra la entrada 122 con las tandas T3-T5 (bugs 1, 2, 3, 4, 5, 9, 15), todas revisadas por el agente corrector. **EL `pieza_idx` NO ES UNA IDENTIDAD, ES UNA POSICIÓN DENTRO DE UN TALLE** — ese es el nudo del que salían casi todos: *(bug 3)* el front mandaba el índice del talle **que se estaba mirando** y `set_variantes` lo traducía siempre contra la GUÍA → elegías piezas mirando L y se guardaban OTRAS; ahora cada valor viaja con su **`talle_origen`** y se resuelve contra ese talle (`_idx2id_de`), y sin él (datos viejos) cae a la guía = comportamiento anterior. *(bug 9)* la vista instantánea de variantes emparejaba las piezas del nido **por posición en la lista**; ahora va por `pieza_id` → clave → nombre, y si el talle en pantalla **no** es el que publica el nido no muestra nada (mejor vacío que la pieza equivocada). *(bugs 4 y 15)* se cayó la regla del **«un solo nombre por variable»**: era **inventada** — el corrector midió que todo el sistema indexa por nombre completo y que el mapeo del arte ya expande una mesa «Frente» a todas las piezas que matchean, o sea que dos Frentes en una variable **siempre funcionaron abajo**; lo único que lo impedía era un filtro que además **descartaba la pieza en silencio**. Queda `dedupePorPieza` (no repetir el mismo `pieza_idx`), y con el `_genDeValor` que se fue desapareció el bug del «slot que cambiaba según el talle en pantalla». **IDENTIDAD ESTABLE DE LA PIEZA (bug 2):** `piezas.json` v2 gana un **ancla `{talle, idx}`** y la resolución va **en DOS PASADAS** (primero TODA la clave exacta, después el ancla, después id nuevo). 🔴 Resolviendo de a una clave el resultado dependía del **orden del registro**: una pieza nueva que caía en la posición de otra se llevaba por ancla el id de una pieza **que seguía viva**, y después la viva recibía **el mismo id** por clave exacta → dos claves con un solo `pieza_id` → una variable resolvía la pieza equivocada (el corrector lo dedujo leyendo; el test lo reprodujo: `{'Manga 2': 'pz_0001', 'Frente Principal': 'pz_0001'}`). El archivo es **append-only**: la pieza que sale se marca `retirada: true`, no se borra —su id no se pierde ni se recicla— y no entra en `id2clave` ni en el sync a la base. ⚠️ **NO se ancla por geometría**: medido sobre los moldes reales, una firma por tamaño **colisiona en 94 de 137 piezas** (las espejadas —manga izq/der, sisas— miden exactamente lo mismo) y fusionaría piezas distintas, que es el peor error posible acá. **NOMBRAR YA NO PISA LO QUE ESCRIBISTE (bug 1):** `nombres_normalizados` renumeraba TODO el genérico 1..N por orden de índice; ahora lo que ya es único se respeta y sólo los repetidos reciben el primer número libre (idempotente). Efecto lateral bueno: `grupo_pieza` arrastra menos claves de `emparejado_talles["manual"]`. **GUARDAR NOMBRES DESDE OTRO TALLE YA NO BORRA (bug 5):** la pantalla manda **sólo las piezas del talle que se está mirando** y con eso se reconstruía el registro ENTERO → todo nombre cuya pieza no apareciera en ese talle se **perdía**. Ahora el registro se re-arma **siempre desde la GUÍA**: los índices se traducen con `_puente_idx`/`_asign_a_guia`, se **mergea** sobre lo ya nombrado (`_merge_asignaciones` — «no vino» pasó a significar «no lo tocaste», y quitar un nombre sigue siendo posible porque el front manda el idx en blanco) y lo que el registro todavía no conoce se lleva a la guía emparejando por forma. **PRUEBAS:** `verificar_piezas.py` (raíz) cubre nombres, identidad y el merge; **se lo vio FALLAR** con las implementaciones viejas (5 de 8 aserciones nuevas muerden; las otras 3 quedan como red de regresión, anotadas como tales en el archivo). ⚠️ **Diagnóstico errado que se descubrió así:** el bug 1 se había descrito con **dos síntomas de más** («le borra el número a un genérico de una sola pieza» — esa rama es **inalcanzable**, código muerto; «intercambia Frente 1 ↔ Frente 2» — sólo con textos repetidos). Un diagnóstico por lectura **no está confirmado hasta que un test lo ve fallar**. ⚠️ **Y la prueba escribió en la base REAL del usuario** (`prod_test` + 3 piezas; se borraron a mano, verificado que los 38 productos suyos quedaron intactos) — ver §9, trampa nueva.

- **2026-07-28 (122) — AUDITORÍA DE «CREAR MOLDERÍA»: 13 de 18 bugs arreglados (T0-T2 + subida atómica).** El usuario reportó que crear una moldería «está con muchas fallas»; la revisión encontró **18** y se trabajó con un **agente corrector** dedicado a que nada se rompa (él fijó el orden de tandas, los invariantes y revisó cada una). **PERMISOS (bug 7 + 3 huecos que encontró el corrector):** `_pid_de_request` ignora el campo `id` **a propósito**, así que 13 endpoints de molde (`eliminar` —que hace `rmtree`—, `renombrar`, `activar`, `terminologia`, `variantes`, `modelos`, `grupos`, `conjuntos`, `telas_asignadas`, `config_columnas`, `config_mapeo`, `variante_guia`, `referencia_medida`) **no pasaban por ninguna guarda de dueño**: cualquiera con sesión podía borrar el molde de otro. Helper nuevo **`_guard_id(cuerpo)`**, insertado antes de toda lectura/escritura. Además: `nesting_preset` y `grupo_tizada` tenían una puerta trasera (`producto_id or id`) y 🔴 **`generar_multi` no validaba nada** —los pids llegan en la LISTA `molds`, que `_pid_de_request` no mira— o sea que **generaba y devolvía la tizada de moldes ajenos, con su registro y su arte**: fuga de datos, no sólo escritura. **CONFIG LEÍA UN MOLDE Y ESCRIBÍA OTRO (bugs 13/14):** todo lo de configuración pasó a **`pidCfg`/`prodCfg`** (el molde ABIERTO) — 19 escrituras + 17 lecturas, incluido el `pid` que recibía `NombrarVariantes`, que **parte el PDF y rehace el registro** (podía partirle al usuario el molde equivocado). ⚠️ Arreglarlo a medias es PEOR que no tocarlo: el corrector cazó dos veces que dejé lectura y escritura de lados distintos. **LA UI DEJA DE MENTIR:** «Molde OK» salía con el registro vacío → ahora `get_productos` devuelve **`piezas_registradas`** (dato nuevo, sin invertir `plantilla`: el DXF entra a propósito con el registro vacío) y la tarjeta tiene 3 estados; los `problemas`/`advertencias` del alta **se muestran** (helper `avisarAltaMolde`, en las DOS pantallas que suben molde) y lo que decide si el alta falló son los **talles**, no las piezas (`piezas: []` es el caso NORMAL); el cartel de variables dice «no pude ubicar las piezas», no «no tienen nombre» (era una suposición). **EL NIDO SE REFRESCA** (`invalidarNido()`) al cambiar variables o el registro — antes había que recargar la página. **RE-SIEMBRA Y CARRERAS:** los buffers de edición se siembran **una vez por molde** (clave `pidCfg` + **generación**, no el objeto ni una firma del contenido) — antes cada uno de los ~28 `fetchProductos()` los pisaba en pleno uso; y `guardarGruposCon` descarta respuestas viejas con un contador de secuencia (dos gestos seguidos y la pieza recién tocada se «des-tocaba» sola). Ahora también **toma la respuesta del server**, que trae los `pieza_id` resueltos. **SUBIDA ATÓMICA (bug 6):** ver invariante §8.7. Verificado en Windows fuera de los datos del usuario: fitz **no** abriría un temporal `.tmp`, `os.replace` pisa bien, y con el PDF abierto da WinError 5 → la ruta de fallo existe y ahora conserva el molde viejo. **MENORES:** crear moldería ahora **la abre** (la zona de subida está adentro); nombre único **por dueño** (nunca global: dos usuarios pueden tener su «Camiseta»); se fueron los 7 `confirm`/`prompt` y 4 `alert()` nativos → modales propios (CLAUDE.md §4); conteo de piezas cacheado por mtime para no parsear el registro de cada molde en el endpoint más caliente. **PENDIENTE:** bugs 1, 2, 3, 4, 5, 9, 15 (marco de referencia del `pieza_idx` e identidad de pieza) — ver entrada siguiente cuando se cierren. ⚠️ **Nada de esto se pudo probar contra la app real: pide login y no se usan credenciales.** Compila, el server levanta sano y lo verificable sin API se verificó; el flujo lo tiene que abrir el usuario.

- **2026-07-28 (121) — RECORRIDOS EXPLICATIVOS: «para qué sirve cada cosa» en todas las demás pantallas.** Pedido del usuario: dejar el paso a paso SÓLO para armar la tizada y, en el resto, tutoriales que expliquen para qué sirve cada cosa. Se sumaron **21 recorridos** (22 guías en total, 99 pasos) agrupados en 3 áreas: **el molde y sus ajustes** (Moldería, Variables, Plantilla, Planilla, Nesting, Telas, Borde, Etiqueta, Editable, Nombres), **configuración del sistema** (Molderías, Planillas, Reglas·Capas, Telas, Nesting, Fuentes, Perfil de color, Usuarios, Publicación) y **dentro del pedido** (Editar diseño, Mis artículos). **Son OTRA COSA que un tutorial y el código lo hace explícito**: llevan `explica: true`, **todos** sus pasos son `accion: 'ver'` (globo violeta, avanza solo) y **ninguno** declara `hecho` — no le piden nada a la persona. El chequeo del build lo exige (se lo vio fallar al meterle un `click` a un recorrido). **El menú volvió**, pero separado con todas las letras: arriba **«Hacerlo paso a paso»** con la guía de la tizada destacada, abajo **«Para qué sirve cada cosa»** con las 3 áreas. **Motor:** (1) `RUTAS` recuperó las rutas de Configuración y sumó las de los 10 ajustes del molde; (2) **nueva llave `molde` en `donde`** — a un ajuste no se entra directo, primero hay que **abrir una moldería** de la grilla, así que se agregó el ancla `molde-tarjeta` (1ª tarjeta) y la ruta `molde:abierto`, y el orden de resolución pasó a ser `tab → sub → paso → molde → ajuste`; (3) **`esPasoNav` ya no saltea los pasos `'ver'`**: un paso informativo NUNCA es puro tránsito y saltearlo se comía justo la explicación de qué es esa pantalla (se perdía el 1/4 de cada recorrido); (4) el globo de cierre de un recorrido dice **«Eso es todo»** en vez de «esto ya estaba hecho» (que salía siempre, porque en un recorrido no hay interacción). **Chequeo nuevo:** todo destino `ir` tiene que tener ruta en el motor — se lo vio fallar con un `sub` inventado. **VERIFICADO en el navegador con el motor real**: desde Pedidos, abrir el recorrido «Telas asignadas» encadena los 4 puentes correctos (`nav-config → cfg-productos → molde-tarjeta → ajuste-telas`, cada uno con su texto) y después reproduce los 4 pasos explicativos **desde el 1/4** y cierra con «Eso es todo». 0 errores de consola.

- **2026-07-28 (120) — FIX: React #185 («Maximum update depth exceeded») al abrir la ayuda.** Lo trajo el arreglo anterior (119) y lo vio el usuario en pantalla. **Causa:** cuando el globo no entra en ningún hueco se le pone un **`maxHeight`**; la app tiene **`* { box-sizing: border-box }`** (`index.css:44`), así que con ese tope el alto **RENDERIZADO** pasa a ser EXACTAMENTE el hueco. Como el componente medía ese alto renderizado (`getBoundingClientRect().height`), a la vuelta siguiente «ya entraba» → se le sacaba el tope → crecía → no entraba → se lo ponía… **lazo infinito**. **Arreglo:** se mide el alto **NATURAL** del contenido con **`scrollHeight`**, que NO cambia cuando se lo capa → la decisión de dónde ubicarlo es estable. Además: `setTam` con forma funcional que devuelve `prev` si no cambió, y **lista de dependencias** en el `useLayoutEffect` (antes corría en CADA render, que era lo que alimentaba el lazo). De paso, `useAncla` dejó de crear un objeto nuevo cada 250 ms: ahora sólo avisa **si el elemento se movió de verdad** (antes el tutorial entero se re-dibujaba 4 veces por segundo sin motivo). **VERIFICADO:** primero se **REPRODUJO** el error en el navegador con un banco que copia la regla `box-sizing` de la app (sin esa regla NO se reproduce — mi primer intento falló justo por eso) y después, con el arreglo, el mismo caso da **0 errores** y el globo queda arriba, capado a 116 px, sin tapar el botón. **Regresión en el build:** el chequeo exige que la ubicación sea un **punto fijo** (realimentarla no la mueve) y que el código —no un comentario— siga midiendo por `scrollHeight`; se lo vio **fallar** al reponer la medición vieja. ⚠️ Ojo con los chequeos por `grep`: la primera versión daba OK porque la palabra `scrollHeight` seguía apareciendo **en un comentario**; ahora se filtran los comentarios antes de mirar.

- **2026-07-28 (119) — FIX: el resaltado TAPABA el botón en vez de resaltarlo.** Reportado por el usuario: «está bien cómo te guía pero los botones los oculta detrás del resaltado en vez de resaltar». **Dos causas, las dos de dibujo:** (1) el recorte tenía una sombra **`inset 0 0 22px rgba(0,216,245,0.30)`** — las sombras `inset` se dibujan **DENTRO** del hueco, o sea **encima del control**: en un botón de 43 px de alto un blur de 22 px desde los cuatro lados lo cubre entero con un velo celeste. Se sacó: **el resalte va SIEMPRE por afuera** (aro + resplandor). Queda como regla en el comentario del código. (2) el **globo se ubicaba suponiendo que medía 200 px de alto**; con texto largo, nota o el botón de escape mide más, no entraba abajo y se lo mandaba arriba **encima del botón** — justo en la barra inferior del pedido, donde viven «Cargar el arte», «A la planilla» y «Enviar». Ahora el globo **se mide de verdad** (`useLayoutEffect` + ref) y la ubicación salió a **`frontend/src/tutor_pos.js`** como **función pura** (`ubicarGlobo`) para poder probarla sin navegador: prueba DEBAJO → ARRIBA → **AL COSTADO** → y si no entra en ningún lado (pantalla baja + texto largo) **se achica al hueco más grande y scrollea adentro**, nunca se pone encima. La flecha ahora apunta al **centro del ancla** (antes iba fija al 50% del globo y, al correrse por el borde de pantalla, señalaba cualquier cosa). Además, mientras el elemento no aparece se oscurece **menos** (0.55 en vez de 0.88): tapar todo justo cuando algo no sale bien deja a la persona sin ver nada. **VERIFICADO con una barrida determinística en el chequeo del build: 8556 combinaciones** (4 resoluciones × 4 alturas de globo × el botón recorriendo toda la pantalla × 3 formas de botón) — **0 solapamientos y 0 globos fuera de pantalla**; con la lógica vieja puesta la misma barrida da **2021 casos tapados**. ⚠️ **NOTA DE MÉTODO:** las mediciones que hice en el navegador de pruebas salían «congeladas» porque el Browser pane estaba **en segundo plano y Chrome frena los timers** de las pestañas ocultas — no era un bug del motor. Por eso la verificación de geometría se hizo con una función pura en Node y no a ojo.

- **2026-07-28 (118) — UNA SOLA AYUDA: «Armar una tizada», calcada del video del usuario.** Decisión del usuario: «olvidate de todas las ayudas, quitalas todas y sólo dejá la de armado de tizada, y usá este video como guía para crear el paso a paso» (`Como cargar un pedido.mp4`, 2:48, grabado por él). **Se sacaron las 26 guías restantes** (moldes, ajustes, configuración): sumaban pantallas de setup que el operario no toca y hacían que la ayuda pareciera un manual. Queda **1 guía de 22 pasos**, escrita mirando el video cuadro por cuadro (`ffmpeg -vf fps=1/3` → 56 frames, leídos como imágenes): mismo orden, mismos botones y las mismas palabras que se ven en pantalla — *diseño → prenda → «Cargar el arte» → «Cargar arte» + espera del «Asignando el diseño a cada variante» → revisar/arrastrar mesas → «Editar diseño» (opcional) → «Ver telas de pieza» (1) elegí tela 2) tocá piezas 3) Asignar) → «A la planilla» → talle/nombre/número + fill-handle + CSV → «Enviar» → mesas con zoom/pan, «Descargar todo» y «Ficha técnica»*. **UI:** el botón Ayuda ya no abre un menú de áreas — abre una **tarjeta de arranque** (qué es, cuántos pasos, «Empezar») y ofrece **retomar** si quedó algo a medias. Se sacaron `AREAS`, `pendientes`, `estaLista`, `bloqueo`/`requiere` y el «Lo que te falta» (eran del menú multi-guía); `ayudaEstado` se recortó a lo del PEDIDO; `RUTAS` quedó sólo con `tab:pedidos` + los pasos del wizard. **🔴 BUG DEL MOTOR ENCONTRADO Y ARREGLADO (el que trababa al tocar «Cargar el arte»):** el avance por clic se programaba con un `setTimeout` guardado en una **variable del efecto**, y el cleanup lo cancelaba. Como el botón que se toca **cambia de pantalla**, aparece un puente → cambia `paso.ancla` → el efecto se re-monta → **se cancelaba el avance que estaba en camino** y el tutorial quedaba clavado mostrando «volvé al paso anterior». Ahora el temporizador vive en un **ref** que sobrevive al re-montaje (pisar de más es imposible: `avanzarDesde` sólo avanza si seguimos en el MISMO paso) y se limpia al cambiar de paso. **VERIFICADO en el navegador con el motor real** (banco que monta `tutor.jsx` tal cual, borrado después): un conductor automático jugó la guía COMPLETA como una persona — pasos **2→22 en orden y cierre**, incluidas las tres transiciones de pantalla que antes la trababan (moldes→arte, arte→planilla, planilla→resultados) y los pasos que esperan estado real (elegir prenda, arte procesado, todas las piezas con tela). **Chequeo (`verificar_guias.mjs`) actualizado**: anclas + estructura + `hecho` + **orden del video** (diseño antes que prenda, prenda antes que arte, arte antes que telas…). Se lo vio **fallar** con los bugs puestos: gesto sin `hecho()` y orden alterado (telas antes que el arte). Ancla nueva: `telas-panel`.

- **2026-07-28 (117) — FIX: la ayuda rompía el ARMADO DE TIZADA (los botones de VOLVER del wizard).** Reportado por el usuario: «el armado de tizada quedó bugiado, te estás confundiendo con los botones que son para volver a pasos anteriores». **Causa raíz: `RUTAS` sólo sabía ir para ADELANTE.** El único camino de vuelta era `'paso:moldes' → 'pedido-volver-moldes'` («← Diseños»), un botón que **existe SÓLO en el paso Arte**. Estando en la Planilla y pidiendo el paso Arte, `puente()` encadenaba `arte → necesita moldes → «← Diseños»` y marcaba un botón **que no está en esa pantalla** → «Buscando ese lugar…» → a los 5 s el «Seguir igual» llamaba a `ir()` y **teletransportaba** al usuario fuera de su pedido. Y las guías nuevas (117 era mío, entrada 116) empeoraban esto: **`resultados` hacía `ir` a un paso al que NO se llega con ningún botón** (se llega generando la tizada) → caía en el `ir()` a ciegas y dejaba al usuario en «No hay ninguna tizada en curso», que se lee como «perdí el pedido». **ARREGLO (3 partes):** (1) **las rutas del pedido ahora son función de DÓNDE ESTÁS** (`rutaDe(clave, donde)`): para atrás se usa el botón de volver **de la pantalla actual** — se agregaron las anclas que faltaban, `planilla-volver-arte` («← Arte») y `resultados-volver-planilla` («← Atrás»/«← Volver a la planilla»), y el retroceso encadena de a un paso (resultados→planilla→arte→moldes). (2) **`requiere(E)` en las guías**: una guía que lleva a un paso del pedido distinto de `moldes` tiene que declarar qué necesita; si no se cumple **NO arranca** y lo explica en el menú (candado + motivo), en vez de sacarte de tu pedido. Lo declaran `resultados`, `editar-diseno` y `planilla-pedido`. Vale también al **retomar**. (3) `esPasoNav` pasó a recibir `donde` (usaba la tabla vieja). **REGLA NUEVA EN EL CHEQUEO** (`verificar_guias.mjs`): todo paso con `ir.paso !== 'moldes'` obliga a `requiere()`, + se testea que las guardas digan NO con el pedido vacío y SÍ con el pedido completo. **Verificado**: primero el chequeo **falla** al sacarle el `requiere` a `resultados` (mensaje exacto del bug), y después el motor REAL en el navegador — parado en **planilla** pidiendo arte ilumina **`planilla-volver-arte`** (antes: `pedido-volver-moldes`, inexistente ahí) y **no navega solo** (`ir` no se llamó); parado en **resultados** pidiendo moldes ilumina **`resultados-volver-planilla`** (encadena bien); y «Descargar la tizada» sin tizada **no arranca**, muestra el aviso y **se queda en el menú**. **LECCIÓN: un wizard no se recorre con una tabla de rutas fija — el botón de volver es de la PANTALLA, no del destino.**

- **2026-07-28 (116) — LA AYUDA GUIADA AHORA MIRA EL ESTADO, NO EL DOM (+9 guías nuevas + contrato verificado en el build).** Auditoría de la ayuda: el motor estaba mejor construido que el contenido, y el contenido apuntaba al usuario que YA sabe. Cuatro arreglos, todos en la misma tanda. **(1) COBERTURA INVERTIDA.** Las 18 guías cubrían lo fácil; lo que de verdad traba a alguien nuevo NO tenía guía **ni una sola ancla**: nombrar variantes (sin eso el molde no se puede usar), agrupar piezas homólogas (rediseñada dos veces por rechazo del usuario), el editor de editables (la pantalla más compleja), talle de guía, modelos, mi propio molde, resultados/ficha, usuarios, publicación. Se sumaron **9 guías** (27 en total, 151 pasos) y **~25 anclas** nuevas en `App.jsx`. **(2) ENSEÑABAN LA PANTALLA, NO LA TAREA.** `nombrar-piezas` terminaba en «Guardar» cuando en multi-talle falta agrupar; `crear-molde` mandaba a Variables aunque el molde hubiera venido **sin talles** (ahí Variables no sirve: el visor está vacío) — corregido el ORDEN; el «repetí el mapeo por cada variable» dejó de ser nota al pie y es un paso. **(3) LA AYUDA NO SABÍA QUÉ TE FALTABA** aunque la app sí: se agregó **`ayudaEstado`** en `App.jsx` (§10.e) y el menú abre con **«Lo que te falta ahora»** + motivo concreto + **✓** en lo hecho + **retomar** lo interrumpido. **(4) CONFUNDÍA «TOCÓ» CON «LE SALIÓ»**: nuevo **`hecho(E, E0)`** — si un paso lo declara es la ÚNICA forma de avanzar, con la FOTO del estado al arrancar el paso. Un POST que falla (409) ya no hace avanzar el tutorial, y los gestos del visor pasaron a `accion:'gesto'` que **no avanza por tiempo** (antes eran `'ver'`: lo más difícil de la app era justo lo que la ayuda no verificaba). **CONTRATO EN EL BUILD**: `frontend/verificar_guias.mjs` (corre en `npm run build`) corta si una guía apunta a un ancla que no existe o si un predicado explota/miente; contempla anclas **dinámicas** (`'ajuste-' + item.id`) y **condicionales** — el chequeo ingenuo daba 9 falsos positivos. **VERIFICACIÓN, siguiendo la lección de (114):** primero se vieron los tests **FALLAR** con el bug puesto (ancla renombrada → detecta; orden equivocado nombrar-antes-que-talles → detecta; `hecho` sin la foto `E0` → detecta), y después pasar. Y el MOTOR REAL (no una réplica) se probó **en el navegador** con un banco que monta `tutor.jsx` tal cual: **A)** 6 s en un paso de gesto sin gesto → NO avanza (paso 3), al seleccionar piezas → avanza (paso 4); **B)** tocar «Nombrar» con el guardado fallado → NO avanza (queda en 5), con el guardado OK → avanza (6); **C)** el paso que sólo aplica a multi-talle se **saltea** solo en un molde de un talle y la guía cierra con el globo final. Banco borrado de `dist` después. **Bug de paso encontrado y arreglado:** el último paso de «Armar una tizada» apuntaba a `resultados-hojas`, ancla que vive en el bloque de resultados VIEJO (`trabajoEstado`, un solo molde) y no en el del wizard (`trabajosMulti`) → ese paso no encontraba nada nunca; ahora hay `resultados-mesas`/`-descargar`/`-ficha` en el bloque real. Docs: §10.e nueva acá + §6.2 reescrita en `MANUAL_HERRAMIENTAS.md`.

- **2026-07-28 (115) — MANUAL DE HERRAMIENTAS (`MANUAL_HERRAMIENTAS.md`, raíz del repo).** Faltaba el documento operativo: el MAPA cuenta *cómo funciona y por qué*, pero no *cómo se completa cada herramienta*. Se escribió recorriendo el sistema entero (los 121 endpoints de `servidor.py`, las ~90 anclas `data-tour` de `App.jsx`, `guias.js`, `tutor.jsx` y §10.b/c/d de este mapa) y quedó con **una entrada por herramienta**: qué hace · dónde está · qué tiene que estar hecho antes · **los pasos exactos** · qué guarda (endpoint + archivo en disco) · trampas. Cubre: preparar la moldería (crear · subir molde `.ai/.pdf/.dxf` · nombrar variantes **por capa** y **por piezas** con su autoguardado · talle guía · agrupar homólogas · ajuste avanzado · acomodar), los **10 ajustes del molde** (Variables 1-2-3, Plantilla/medidas+mapeo, Planilla, Nesting, Telas, Borde, Etiqueta, Editable, Nombres), la **configuración general** (Molderías, Planillas, Reglas·Capas con la tabla de comportamientos, Telas, Nesting+grupos de tizada, Fuentes, Perfil ICC, Usuarios, Publicación), el **pedido completo** (diseños→variables, mi propio molde, arte+mapeo+telas por pieza, «Editar diseño» con transform/color/objetos agregados, planilla estilo Sheets, enviar y resultados/ficha) y las transversales (visor, ayuda guiada, modales). Cierra con **checklist «este molde ya produce»**, tabla **herramienta→endpoint→archivo**, tabla de **cachés y cuándo se invalidan** (piezas_cache v7, nido v6, deteccion_cache, `_pvCache`) y **síntomas→causa**. Se agregó el puntero al manual en el encabezado de este mapa: **de acá en más se actualizan los dos juntos**.

- **2026-07-28 (114) — CAUSA RAÍZ de «los tutoriales están todos bugueados»: el motor esperaba un evento que React NUNCA emite.** El usuario reportó que escribe, el diseño **se agrega**, y la ayuda **queda congelada** en ese paso. La detección de «campo confirmado» estaba hecha escuchando el evento `input` para ver el vaciado — y **React limpia el `value` por asignación directa, sin emitir ningún evento**. O sea: el motor esperaba algo que no ocurre jamás → todo paso de escritura cuyo campo se limpia al confirmar (que son casi todos: diseño, nombrar pieza, nombre de grupo/variable, nesting, regla…) **quedaba trabado para siempre**. FIX: helper `valorDe(ancla)` + `vigilarVaciado(anclas, cb)` que **MIRA el valor cada 150 ms** (poll) en vez de escuchar; se usa tanto en el paso de escribir como en el paso siguiente que pide tocar el botón equivalente (`tambien`). También cuenta ahora **una sola letra** como escritura válida (antes exigía 2 → un talle «M» o un número dejaban el paso trabado) y `valorDe` reconoce `select` además de `input`/`textarea`. **MI ERROR, que hay que no repetir: la prueba anterior daba OK en verde porque la réplica limpiaba el campo con `dispatchEvent(new Event('input'))` — o sea, la prueba fabricaba justo el evento que en la app no existe.** Una prueba que no reproduce el mecanismo real no prueba nada: primero hay que ver la prueba FALLAR con el bug puesto. La nueva (`scratchpad/prueba_real.html`) limpia el campo como React —sin evento— y cubre 3 casos: Enter rápido, Enter tardío (con el tutorial ya en el paso del botón) y botón; **con el arreglo apagado se congela (`idx:1`) y con el arreglo sigue (`idx:2`)**, así que la prueba distingue de verdad. VERIFICADO en el navegador, servida desde `dist` y borrada después.

- **2026-07-28 (113) — EL ENTER ES DEL CAMPO, NO DEL TUTORIAL.** El usuario ya lo había dicho en (112) y yo lo entendí al revés: dejé el `keydown` escuchando la tecla y encima le sumé un salto de 2 pasos. **La regla es simple: con la ayuda abierta, el Enter tiene que hacer exactamente lo mismo que sin ella** (confirmar el campo: agregar el diseño, aplicar el nombre). Ahora `tutor.jsx` **no escucha `keydown` en ningún paso** (sólo queda el Escape para salir): el tutorial se entera por el **EFECTO** — el campo que confirma **se vacía**, y ese pasaje de «tenía texto» a «quedó en blanco» es la señal de que la acción se hizo. Vale en los dos tipos de paso: escribiendo (el paso se cierra) y en el paso siguiente que pide tocar el botón equivalente (declarado con `tambien: ['ancla-del-campo']` → se da por cumplido sin pedir el clic). **Detalle que costó una vuelta: `tenia` hay que inicializarlo LEYENDO el campo al montar el paso** (cuando ese paso empieza, la persona ya escribió en el paso anterior); arrancándolo en `false` el vaciado no se reconocía y el tutorial se quedaba esperando un clic innecesario. **VERIFICADO EN EL NAVEGADOR de verdad**, con una página que replica los handlers y el campo real (`scratchpad/prueba_enter.html`, servida desde `dist` y borrada después): con ENTER → el diseño se agrega **y** el tutorial sigue solo (`agregado:true, siguio:true`); tocando el BOTÓN → también agrega y avanza. Antes del arreglo la misma prueba daba `siguio:false`. **LECCIÓN: cuando el usuario dice que una tecla «sólo sirve para el tutorial», está diciendo que la ayuda le robó una función del sistema — no hay que envolver el robo, hay que devolver la tecla.**

- **2026-07-28 (112) — Ayuda guiada: dos absurdos que marcó el usuario.** (a) **«Tocá Pedidos» estando en Pedidos.** El primer paso de varias guías es de pura navegación, y se pedía igual aunque el usuario ya estuviera parado ahí. Ahora el motor lo detecta SOLO, sin tocar los guiones: `esPasoNav(p)` es cierto cuando el ancla del paso es exactamente el botón que la tabla `RUTAS` usa para llegar al destino que ese mismo paso pide (`RUTAS['tab:pedidos'].ancla === 'nav-pedidos'`); si además no hay puente activo (o sea: ya estamos en el destino), **el paso se da por cumplido y se saltea**. Comprobado sobre los 18 guiones: son 13 pasos (uno por guía, siempre el de entrada) y **ninguna guía se queda sin pasos propios**. (b) **El ENTER quedaba «sólo para el tutorial».** (Reescrito: el primer intento seguía escuchando la tecla y saltaba 2 pasos — mal, ver la entrada (113).) `frontend/src/tutor.jsx` + `guias.js`. VERIFICADO: compila, la app carga sin errores y el chequeo de anclas sigue en verde. **LECCIÓN: la ayuda no puede pedir lo que el sistema ya dio por hecho — antes de escribir un paso, preguntarse si el paso anterior no lo dejó cumplido.**

- **2026-07-28 (111) — Ayuda guiada: de 7 a 18 guías (las pantallas que faltaban), escritas desde el ESTUDIO.** Se completó lo que quedaba pendiente de (109): cada guion nuevo se escribió mirando `ESTUDIO_PANTALLAS.txt` (regenerado; **OJO: hay que correrlo con `PYTHONIOENCODING=utf-8`, si no la redirección a archivo muere con `UnicodeEncodeError` de cp1252**), no de memoria. **11 guías nuevas**: armar las variables del molde (grupos → variable → elegir piezas en el visor), Plantilla (medidas + mapeo del arte), Planilla del molde, Nesting del molde, Nombres propios, cargar la planilla del pedido (estilo Excel, fill-handle, CSV), y de Configuración: Planillas de columnas, Reglas de columna, Reglas de nesting, Fuentes y Perfil de color. **28 anclas nuevas** en App.jsx: las 7 tarjetas restantes del panel de Configuración (`cfg-columnas`, `cfg-reglas`, `cfg-nesting`, `cfg-fuentes`, `cfg-perfil`, `cfg-usuarios`, `cfg-publicacion`) y los controles de cada pantalla (`col-nueva/guardar`, `regla-nueva/nombre/guardar`, `nesting-nuevo/nombre/guardar`, `fuentes-subir/probar`, `perfil-card`, `nsel-elegir/grupos`, `diseno-mapear/capas/guardar`, `mplanilla-elegir/guardar`, `term-variante/molde/guardar`, `grupo-nombre`, `var-nombre/elegir-piezas/listo`, `planilla-agregar/csv`). La tabla `RUTAS` del motor creció con **11 destinos** (6 secciones de config + 5 pestañas de ajustes) y con los **pasos del pedido en fila** (`paso:arte` → `paso:planilla`), así que la ayuda ahora sabe llegar caminando a cualquier pantalla. **VERIFICADO con el chequeo automático: las 87 anclas usadas por guías y rutas existen en App.jsx (90 marcadas) — ningún paso queda sin resaltar**; compila y la app carga sin errores de consola. Quedan sin guía (a propósito, son de administrador): Usuarios, Publicación, Editable y el emparejado de talles de Moldería.

- **2026-07-28 (110) — FIX: la ayuda se trababa (o iba lentísima) dentro del PEDIDO.** El usuario reportó «al terminar de escribir o precionar en un boton dentro de pedido o no avanza mas o demora mucho». CAUSA: cuando el botón que hay que tocar **cambia de pantalla** (ej. «Cargar el arte» pasa de `paso:'moldes'` a `paso:'arte'`), el paso recién cumplido tenía `ir:{paso:'moldes'}` que ya no coincide con dónde quedó el usuario → **se activaba un puente de navegación** y el guard viejo (`if (!saltoRef.current) avanzar()`) leía ese puente al vencer el temporizador y **cancelaba el avance para siempre**: el tutorial pedía volver atrás a una pantalla que ya no correspondía. Fix: el estado de puente se captura **en el momento del evento** (`const eraPuente = saltoRef.current`), no al vencer el timer → `avanzarDesde(i, eraPuente)`; aplicado a los 4 disparadores (click, escritura, Enter, blur). Además se **aceleró** todo: click 280→**200 ms**, fin de escritura 900→**650 ms**, informativos 45 ms/caracter entre **2,6 y 9 s** (antes 55 ms, 3,5–11 s). Y se agregó una **red de seguridad**: si el elemento a marcar no aparece en **5 s** (típico: la guía necesita un molde abierto y no lo hay), el globo lo dice y ofrece **«Seguir igual →»** en vez de quedar en «Buscando ese lugar…» eternamente. `frontend/src/tutor.jsx`. VERIFICADO: compila y la app carga sin errores de consola.

- **2026-07-28 (109) — Ayuda guiada: ESTUDIO del sistema + sin botón «Siguiente» + dos tipos de globo.** El usuario marcó que el orden estaba mal (yo hice el motor antes de estudiar) y pidió: estudiar → guiones → tutoriales, sin «Siguiente», con detección real de cuándo se deja de escribir y **distinguiendo el cartel que EXPLICA un espacio del que INDICA una acción**. (1) **ESTUDIO**: nuevo `estudio_pantallas.py` (herramienta del repo) que recorre App.jsx y lista, por pantalla (paso del pedido / sección de config / pestaña de ajustes), **los elementos interactivos en orden de aparición** con su texto real y si ya tienen `data-tour`. Su salida queda en `ESTUDIO_PANTALLAS.txt` (307 líneas) y ES LA FUENTE para escribir guiones: se corre de nuevo cuando cambia la UI. **Los guiones se escriben desde ahí, no de memoria.** (2) **SE FUE EL BOTÓN «Siguiente»**: los pasos informativos (`accion:'ver'`) **avanzan solos**, con el tiempo calculado según el largo del texto (55 ms por caracter, entre 3,5 y 11 s) y una barra que se llena para que se vea cuánto falta; los pasos de acción esperan la acción de verdad. (3) **DOS GLOBOS distintos**: **ACCIÓN** (cyan, «Hacé esto», ícono ☝, dice si hay que tocar o escribir) vs **INFO** (violeta, «Para que sepas», ícono i, con la barrita de lectura); el **PUENTE** de navegación es ámbar («Te llevo hasta ahí»). (4) **FIN DE ESCRITURA**: ahora cuenta la pausa (900 ms sin teclear), **Enter** y también **salir del campo** (blur). VERIFICADO: compila y la app carga sin errores de consola. PENDIENTE: reescribir los guiones de las pantallas que faltan usando el inventario de `ESTUDIO_PANTALLAS.txt` (planilla, editables, nesting, columnas, usuarios, publicación, perfil, fuentes) y afinar las anclas para que marquen el campo exacto y no un contenedor.

- **2026-07-28 (108) — Ayuda guiada: paso a paso de verdad, resaltado fuerte y navegación INTELIGENTE.** Tres correcciones pedidas por el usuario tras probar: (a) **SALTABA PASOS AL ESCRIBIR**: cada tecla programaba su propio `setTimeout(avanzar)`, así que escribir «River» avanzaba 5 pasos de una (por eso «escribí el diseño y ya me saltó a elegir el molde»). Ahora hay **un solo temporizador por paso** (cada tecla lo reinicia: avanza 900 ms después de DEJAR de escribir) y `avanzarDesde(i)` sólo corre si seguimos en el mismo paso (`idxRef`) → un paso, una acción. Además **Enter cuenta como hecho** (varios campos del sistema confirman con Enter). (b) **RESALTADO más marcado**: fondo 0.72→**0.88**, borde 2→**4 px**, resplandor 26→**40 px** con spread, brillo interno, y un **halo que late** (`.tour-pulso`, keyframes en index.css porque una animación no se puede declarar inline en React). (c) **AYUDA INTELIGENTE**: el motor recibe DÓNDE está el usuario (`donde={{tab,sub,paso,ajuste}}` desde App) y, si el paso necesita otra pantalla, **ya no teletransporta**: calcula el camino con la tabla `RUTAS` y va marcando **un botón por vez** hasta llegar, encadenando lo que haga falta (`necesita`) — incluso hacia atrás (estando en Telas y pidiendo Variables, marca primero «Volver a ajustes»). El globo lo distingue («Te llevo hasta ahí», sin botón Siguiente) y cumplir un puente NO avanza el guion. Si un destino no tiene ruta conocida, se navega solo para no dejarlo colgado. Se agregó `ir` a 15 pasos para que cada uno sepa dónde debe hacerse. VERIFICADO: la función `puente()` probada con 5 escenarios reales (desde Pedidos, desde el dashboard, ya en destino, entre pestañas de ajustes, config→pedidos) dando el botón correcto en cada caso; chequeo automático de cobertura: las **49 anclas** usadas por guías y rutas existen en App.jsx; compila y la app carga sin errores.

- **2026-07-28 (107) — Ayuda guiada: guiones REALES (estudiando el sistema) + fix del salto de pasos.** El usuario probó la entrega 1 y marcó 3 fallas: el guion del pedido hacía «elegir el molde» sin diseño, no se resaltaba todo, y el tutorial **saltaba del paso 1 al 3**. (a) **FLUJO REAL del pedido** (leído en pantalla, no supuesto): primero se ESCRIBE EL DISEÑO (input «Escribí un diseño y Enter» + botón «+ Diseño»), aparecen los chips de diseños, se elige el activo, se eligen las **VARIABLES** que lo componen (NO «un molde»: las variables ya traen su molde detrás) y recién ahí se habilita **«Cargar el arte»** (bloqueado mientras algún diseño no tenga variable). En la planilla el botón final dice **«Enviar»**, no «Generar». El guion se reescribió con eso. (b) **SALTO DE PASOS**: el listener de avance se colgaba del elemento y se re-registraba al re-medirlo (cada 250 ms) → un mismo clic disparaba dos avances. Ahora se escucha en el **documento en fase de captura** preguntando si el target cae dentro del ancla (`closest`), y hay un guard `desde` que permite avanzar UNA sola vez por paso (se resetea al ir «Atrás» o con «Siguiente»). Ventaja extra: ya no hace falta que el elemento exista al montar el efecto. (c) **COBERTURA**: se marcaron todas las anclas faltantes (pedido: diseño/chips/pestañas/variables/subir molde/Enviar; variables: barra de 3 pasos, input y botón de nombrar, guardar nombres; borde: activo/tamaño/color/guardar; etiqueta: activo/qué muestra/guardar; config: tarjeta Telas, conexión y lista; resultados). **VERIFICADO con un chequeo automático: las 46 anclas usadas por las guías existen en App.jsx (54 marcadas en total) — ningún paso queda sin resaltar.** Compila y la app carga sin errores. Guías actualizadas: crear molde (con «cómo exportar» y el enlace a Variables), nombrar piezas (3 pasos reales) y armar una tizada (14 pasos con el flujo verdadero).

- **2026-07-28 (106) — AYUDA GUIADA paso a paso (entrega 1: el motor + primeras guías).** Pedido del usuario: un botón de ayuda que abra un menú de temas y después **guíe como el tutorial de un videojuego**, resaltando el campo real y diciendo qué hacer, para TODAS las herramientas. Decisiones suyas: (a) el paso avanza **cuando el usuario hace la acción de verdad** (igual queda «Siguiente» por si se traba); (b) trabaja **sobre sus datos reales**, acompañando el trabajo (no modo demo) → ningún paso toca datos por su cuenta; (c) hay que cubrir **todo** el sistema. ARQUITECTURA (2 archivos nuevos, App.jsx ya tiene 14k líneas): **`frontend/src/tutor.jsx`** = el MOTOR (recorte tipo spotlight con `box-shadow` gigante + `pointerEvents:none` para poder tocar de verdad el elemento; globo que se acomoda arriba/abajo; barra de avance; Escape para salir; `useAncla` reintenta cada 250 ms hasta que el elemento aparece —sirve para pantallas que tardan— y sigue scroll/resize; detección de `click`/`input` sobre el ancla; `ir(destino)` para navegar solo entre pantallas) y **`frontend/src/guias.js`** = el CONTENIDO (guiones en texto plano, para corregir la ayuda sin tocar el motor). Los elementos se marcan en el JSX con `data-tour="id"`. En App.jsx: import, estado `ayudaAbierta`, `irPantallaAyuda({tab,sub,paso,ajuste})`, botón **Ayuda** en el menú lateral y montaje de `<AyudaGuiada/>` (OJO: se importa como `AyudaGuiada` porque ya existía un componente `Ayuda`). HECHO: 7 guías (crear molde, nombrar piezas, telas del molde, etiqueta, borde, armar una tizada, telas del sistema) y **19 anclas** marcadas. VERIFICADO: compila y la app carga sin errores de consola. NO verificado a mano (el botón vive detrás del login). **FALTA (entregas siguientes):** guiones de las demás pantallas —variables, planilla, editables, terminología, nesting, columnas, usuarios, publicación, perfil de color, fuentes, productos— y marcar sus anclas. El motor tolera anclas faltantes: avisa «buscando ese lugar» y deja seguir con «Siguiente».

- **2026-07-28 (105) — CAUSA RAÍZ del servidor caído y los 3 arreglos.** El 502 NO fue por el código publicado: al apagarse para actualizar, el servidor hacía `os._exit(0)` **sin cerrar el `ProcessPoolExecutor` de render**. Esos workers heredan la salida del proceso (el `.bat` la redirige a un log), así que uno quedó vivo **manteniendo el log abierto** → la redirección del siguiente arranque fallaba («The process cannot access the file because it is being used by another process»), el `.bat` moría antes de escribir su primera línea y la tarea devolvía «error 1» SIN dejar rastro. Ni la versión nueva ni la restaurada podían levantar. Evidencia: en `servidor_log.txt` no hay ningún `---- arranque` posterior a la caída, y `cmd /c arrancar.bat` a mano imprimía ese error 3 veces (una por redirección). ARREGLOS: (1) `_apagarme()` termina los procesos del pool y lo cierra antes de salir (servidor.py); (2) el `.bat` que genera el instalador ya no puede morir por el log: prueba escribir y si no puede usa `arranque_%RANDOM%.txt` (instalar_servidor.py) — **VERIFICADO reproduciendo el fallo**: con el log bloqueado a propósito, el bat viejo no arrancaba y el nuevo arranca en un log alternativo; (3) `arrancar()` del ayudante ahora **comprueba la salud real** y, si la tarea no levantó nada (`schtasks /run` contesta 0 aunque no ejecute nada), lanza el `.bat` a mano y lo vuelve a verificar; si tampoco, lo deja escrito en el log (actualizador.py). PENDIENTE: el servidor publicado quedó en 1.0.9 con el `.bat` parcheado a mano (log `arranque_log.txt`, sin el fallback); conviene re-publicar para que tome estos fixes.

- **2026-07-27 (104) — INCIDENTE: el servidor PUBLICADO quedó caído (502) tras una actualización.** Diagnóstico desde el taller: `/Tizadapro/*` devuelve **502 en todo** (Cloudflare: «Host Error») → el proceso Python NO está escuchando en 127.0.0.1:8050. **NO es el código**: se probó `TIZADA_MODO=publicado TIZADA_SECRET=... py -c "import servidor"` y **arranca OK** (sin errores de import ni de sintaxis). Lo que falla es el RELANZAMIENTO post-actualización: `actualizador.py` apaga el server, descomprime y llama `arrancar()` = `schtasks /run /tn "TIZADA PRO"`, con `arrancar.bat` como respaldo; si la tarea no corre y el `.bat` no está, **nadie levanta el sistema y queda 502 para siempre**. Qué mirar EN EL SERVIDOR: `C:/TIZADAPRO/_actualizacion/actualizador_log.txt` (deja el paso exacto: respaldo, descomprimido, OK o falló) y `_actualizacion/ultima.json`. Para levantarlo: `schtasks /run /tn "TIZADA PRO"` o ejecutar `C:/TIZADAPRO/arrancar.bat`. **PENDIENTE (robustez, NO hecho):** `arrancar()` debería verificar que el server contestó de verdad y reintentar/avisar — hoy si `schtasks` devuelve 0 pero la tarea no levanta, el ayudante lo da por bueno. **OJO además:** el paquete incluye `publicado.bat` (plantilla con `TIZADA_SECRET=PONER_LA_CLAVE_ACA`) y ese nombre NO está en el `NO_TOCAR` del actualizador (que protege `config_publicado.bat` y `arrancar.bat`) → si el servidor arrancara con `publicado.bat`, la actualización se lo pisaría y perdería la clave. Verificar cuál usa.

- **2026-07-27 (104) — INCIDENTE: el servidor PUBLICADO quedó caído (502) tras una actualización.** Diagnóstico desde el taller: `/Tizadapro/*` devuelve **502 en todo** (Cloudflare: «Host Error») → el proceso Python NO está escuchando en 127.0.0.1:8050. **NO es el código**: se probó `TIZADA_MODO=publicado TIZADA_SECRET=... py -c "import servidor"` y **arranca OK** (sin errores de import ni de sintaxis). Lo que falla es el RELANZAMIENTO post-actualización: `actualizador.py` apaga el server, descomprime y llama `arrancar()` = `schtasks /run /tn "TIZADA PRO"`, con `arrancar.bat` como respaldo; si la tarea no corre y el `.bat` no está, **nadie levanta el sistema y queda 502 para siempre**. Qué mirar EN EL SERVIDOR: `C:/TIZADAPRO/_actualizacion/actualizador_log.txt` (deja el paso exacto: respaldo, descomprimido, OK o falló) y `_actualizacion/ultima.json`. Para levantarlo: `schtasks /run /tn "TIZADA PRO"` o ejecutar `C:/TIZADAPRO/arrancar.bat`. **PENDIENTE (robustez, NO hecho):** `arrancar()` debería verificar que el server contestó de verdad y reintentar/avisar — hoy si `schtasks` devuelve 0 pero la tarea no levanta, el ayudante lo da por bueno. **OJO además:** el paquete incluye `publicado.bat` (plantilla con `TIZADA_SECRET=PONER_LA_CLAVE_ACA`) y ese nombre NO está en el `NO_TOCAR` del actualizador (que protege `config_publicado.bat` y `arrancar.bat`) → si el servidor arrancara con `publicado.bat`, la actualización se lo pisaría y perdería la clave. Verificar cuál usa.

- **2026-07-24 (103) — El aviso del tope de telas sale SOBRE EL VISOR, no como cartel de error.** Pedido del usuario: el mensaje tiene que aparecer donde está mirando (el molde), no en el toast de la esquina. `MapeadorArteVisual` recibe un prop nuevo **`aviso`** y lo dibuja como overlay dentro del área del molde (arriba y centrado, fondo rojo oscuro translúcido, ícono `alert`, `pointerEvents:none` para no tapar clics, `zIndex 6`). En el pedido: `telaAviso` + `avisarEnVisor(msg)` (se borra solo a los 3,2s, con `clearTimeout` para que avisos seguidos no se pisen); `aplicarTela` usa `avisarEnVisor` en vez de `showError` al pasarse del tope, y el aviso se limpia al salir del modo telas. App.jsx: prop ~1919, overlay ~1990, estado ~2860, uso ~8735. VERIFICADO: compila. NO verificado a mano (el paso Arte está detrás del login).

- **2026-07-24 (102) — FIX: 401 de `/api/pedido/fuente_chars` al abrir el programa.** Se me había escapado ese fetch al gatear los de arranque (#73): su effect sólo miraba `pedidoPaso === 'planilla'`, y como el paso se restaura del wizard guardado, salía al MONTAR (antes del login) → 401 rojo en consola apenas abría la app. Fix: se agregó `!sesionLista` a la guarda (y a las deps), y el fetch ignora respuestas no-ok (`if (!r.ok) continue`) en vez de intentar parsearlas. **VERIFICADO EN EL NAVEGADOR** (esta vez sí se pudo abrir el preview): al cargar la app salen sólo 3 requests y las 3 dan 200 — `/api/salud`, `/api/auth/yo`, `/api/actualizacion/estado` — sin ningún 401 y sin errores de consola. App.jsx ~7537.

- **2026-07-24 (101) — CAUSA REAL del «no se puede guardar la etiqueta»: DOS funciones `_clamp_color` con el mismo nombre.** El mensaje de error mejorado en (100) destapó lo verdadero: `_clamp_color() takes 1 positional argument but 2 were given`. En servidor.py había **dos** definiciones: `def _clamp_color(c, fb)` (~2921, colores de la ETIQUETA con default) y, más abajo, `def _clamp_color(color)` (~3093, colores de EDITABLES). Python se queda con la ÚLTIMA del módulo → la de editables PISABA a la de etiqueta y **cualquier guardado de etiqueta tiraba 400**, sin importar los valores (el fix de (100) era necesario pero no alcanzaba). Fix: la de etiqueta pasó a llamarse **`_clamp_color_etq`** (+ comentario de advertencia) y se actualizaron sus 2 usos (`color`, `borde_color`); la de editables queda como estaba con su nombre. VERIFICADO ejecutando el bloque real del endpoint con AMBAS funciones cargadas (que era lo que reproducía la colisión): config normal, sin colores, colores inválidos y campos vacíos → todos OK con sus defaults. Server reiniciado (PID 26876). **LECCIÓN: al agregar helpers en servidor.py (7k+ líneas) verificar que el nombre no exista ya — una colisión así no da error al arrancar, rompe en runtime y en OTRA feature.** Ver [[etiqueta-baseline-no-romper]].

- **2026-07-24 (100) — FIX: no se podía guardar la ETIQUETA (400 «valores de etiqueta inválidos»).** `POST /api/productos/etiqueta` hacía `float(...)` DIRECTO sobre `size_mm`, `borde_mm`, `posicion.rx/ry`, `posiciones[].rx/ry/ang/t` y `zonas[].puntos`: si un input de la UI quedaba **vacío** mientras se editaba (o venía `None`, texto, o número con **coma**), `float('')` tira ValueError → toda la config se rechazaba con 400 y el usuario sólo veía «No se pudo guardar la etiqueta». Fix: helper `_num(v, default, lo, hi)` que convierte tolerante (acepta coma decimal, descarta NaN, cae al DEFAULT si no se puede) y clampea — un campo vacío ya no impide guardar. Además el `except` ahora dice qué falló y el **frontend muestra el motivo real** que manda el server (antes era un genérico y no se podía diagnosticar). VERIFICADO ejecutando el bloque real del endpoint con casos: vacíos → defaults (3.0/1.0/0.5/0.92), «3,5» → 3.5, None/'abc' → default, fuera de rango → clamp (999→40, -5→0); server reiniciado (PID 29180). NO verificado a mano (login).

- **2026-07-24 (99) — FIX: desapareció «Ver telas de pieza» del PEDIDO (efecto colateral de la disponibilidad por pieza).** El botón estaba condicionado a `_telasMol.length > 0`, o sea a la lista YA FILTRADA. Al introducir la disponibilidad por pieza (#82), si el molde tenía telas asignadas **sólo por pieza** (`por_pieza` con datos y `todas` vacío), `_idsDisp` sin selección devolvía `_todasIds` = [] → lista vacía → **el botón no se dibujaba**. REPRODUCIDO en simulación (ANTES: lista=0 → botón NO; AHORA: lista=1 → botón SÍ). Fix triple: (1) `_telasMoldeIds` = `todas` ∪ todas las de `por_pieza`, y sin piezas seleccionadas `_idsDisp` usa ESO (no sólo `todas`); (2) el **gate del botón** pasa a depender sólo de que haya telas en el sistema (`telasReg.telas.length > 0`) — antes también podía esconderse en pleno uso si la intersección de las piezas elegidas quedaba vacía; (3) `_telaActiva` (modo tela del visor: pintado + panel) igual, para que no se apague solo. App.jsx ~8685, ~8708, ~8906. VERIFICADO: compila + simulación del gate en los 4 escenarios (sólo-por-pieza, en «todas», selección sin telas en común, molde sin config). NO verificado a mano (login).

- **2026-07-24 (98) — «Telas a la vez»: el tope se edita en su PROPIO MODAL, con el número escrito y botón Guardar.** Los chips (97) y el campo suelto (96) no servían: el usuario quiere escribir el número y que tenga espacio propio. Ahora en la config de la variable hay una **fila-botón** («Telas a la vez · cuántas puede combinar la prenda en el pedido» + el valor actual a la derecha, o «Sin límite») que abre un **Modal** (`maxWidth 420`, centrado) con: input **grande** (76px de alto, 34px de fuente, autofocus, Enter guarda) entre botones **−/+**, una línea que traduce el valor («Hasta N telas distintas por prenda» / «Sin límite: puede usar todas las que tenga asignadas») y el pie con **«Sin límite»** y **«Guardar»**. Estados `telaTopeOpen`/`telaTopeVal`. El modelo (`telas_cfg.max_var`) y la validación en el ARTE no cambian. App.jsx: botón ~10330, modal ~10440. VERIFICADO: compila. NO verificado a mano (login).

- **2026-07-24 (97) — CORRECCIÓN del tope de telas: es un límite del PEDIDO, no de la config, y se elige con chips.** El usuario corrigió la semántica de (96): el tope NO limita cuántas telas se pueden dejar disponibles (ahí se asignan las que se quieran), sino **cuántas telas DISTINTAS puede combinar a la vez una prenda de esa variante EN EL PEDIDO** (cada pieza lleva una sola tela; el límite es sobre el conjunto). Cambios: (a) **UI**: el campo numérico (sin guardar, poco práctico) se reemplazó por **chips «Sin límite · 1 · 2 · 3 · 4 · 5 · 6»** que guardan al toque, bajo el título «Telas a la vez · cuántas puede combinar la prenda en el pedido»; (b) se **quitó el bloqueo en la config** (`excedeTope` y su aviso en el modal); (c) la validación pasó al **paso ARTE**: `aplicarTela` simula el mapa resultante y si las telas distintas de las piezas de la variable superan `max_var[clave]` corta con aviso («Esta prenda puede combinar hasta N telas a la vez»); el panel muestra el contador **N/T** (rojo al llegar). Modelo sin cambios (`telas_cfg.max_var`). VERIFICADO: compila; lógica probada con casos (1ª tela ok, 2ª ok, TERCERA bloquea, repetir una ya usada no suma, sin tope no corta). NO verificado a mano (login).

- **2026-07-24 (96) — ENTREGA 2/3: TOPE de telas por variable (límite de la CONFIG).** Decidido con el usuario: es «cuántas telas se pueden dejar disponibles para esa variable en la configuración», NO un límite del pedido. Modelo: `telas_cfg.max_var = {clave_variable: N}` (N>0; sin entrada = sin tope) — se guarda con el resto de la config de telas, **sin tocar el modelo de variables**, por el endpoint que ya existía (`POST /api/productos/telas_asignadas` ahora acepta `max_var` y CONSERVA lo que no venga en el cuerpo, vía `_prev`). `_telas_cfg_prod` normaliza y descarta valores no numéricos o <=0. UI (poco texto, junto al selector de Variable): campo **«Máximo de telas»** (vacío = sin tope, se guarda al salir del campo/Enter) + chip **«usa N / T»** que se pone rojo al llegar al tope. Bloqueo: en el modal, el botón Asignar se deshabilita y aparece «Máximo T · quedan X» si lo tildado superaría el tope (`excedeTope` = telas de la variable + las NUEVAS tildadas > T); `asignar()` también corta por las dudas. VERIFICADO: sintaxis OK, compila, server reiniciado (PID 29532) y probado `_telas_cfg_prod` con casos reales (molde viejo, tope válido, basura `'ocho'`/`-3` descartada, sin cfg) SIN tocar datos del usuario. NO verificado a mano (login). **Falta la entrega 3:** grupos combinables (mejor visual en Config › Telas + filtrado en el pedido; regla: tela sin grupo no combina con nada).

- **2026-07-24 (95) — Telas del molde: fuera los textos de relleno y los NOMBRES de piezas (ya se ven pintadas en el visor).** Eliminados: el párrafo «Definí qué telas están disponibles…», el instructivo «Tocá las piezas en el visor…», el renglón «Piezas de esta variable: …» y todo el bloque **«Piezas con telas propias»**. Donde antes se listaban nombres de piezas ahora va sólo la CANTIDAD: «3 piezas elegidas» (o «Ninguna → va a todas las piezas»), el chip de cada tela dice «N piezas» sin enumerarlas, y el subtítulo del modal también. Criterio del usuario: las piezas se ven pintadas en el visor, listar sus nombres es ruido. VERIFICADO: compila, 0 listados de nombres de piezas (`.join` sobre piezas). NO verificado a mano (login).

- **2026-07-24 (94) — Modal de telas: borde de color ABAJO, tarjetas más chicas y texto centrado.** El borde con el color de la tela pasó del lateral izquierdo al **borde inferior** (5px, degradado horizontal `col66 → col → col66` + glow). Tarjetas más compactas: grid `minmax(150px→116px, 1fr)`, gap 10→9, radio 12→11, nombre 15→13px, medida 12→11px, tilde 20→18px. Todo el contenido **centrado** (`alignItems:center` + `textAlign:center`) y el padding inferior deja aire para el borde (`10px 10px 14px`). App.jsx ~10455. VERIFICADO: compila. NO verificado a mano (login).

- **2026-07-24 (93) — Modal de telas: tarjetas NEGRAS con borde lateral de color + selección por RANGO con Shift.** Tarjeta rediseñada: fondo `#050709` (negra), **nombre grande** (15px/800, hasta 3 líneas) y **la medida debajo** (12px), con un **borde izquierdo de 5px con el color de la tela** en degradado (`col → col55`) y glow suave; al elegirla, borde+halo accent y ✓ arriba a la derecha. Grid `minmax(150px,1fr)`, sigue cuadrada (`aspectRatio 1/1`). **Shift+clic = rango:** el clic normal alterna y deja un ANCLA (`telaCfgAncla = {id, modo}`) con el estado en que quedó; el shift+clic aplica ESE modo a todo el tramo entre el ancla y la tocada, ambas incluidas, sobre la lista FILTRADA (respeta el buscador) → sirve igual para elegir en masa o para quitar en masa (si el ancla se había deseleccionado). `onMouseDown` con `preventDefault` cuando hay shift para que no seleccione texto; el ancla se limpia al abrir el modal. App.jsx ~10433. VERIFICADO: compila. NO verificado a mano: la pantalla exige login y el visor de archivos del navegador no ejecuta scripts (no se pudo capturar el mockup).

- **2026-07-24 (92) — Telas del molde: SE ELIMINA el modo intermedio; todo en un solo apartado.** El botón «Asignar» seguía en la vista principal (yo lo había reemplazado sólo dentro del modo asignar) y obligaba a entrar a otro modo para poder tocar las piezas — no era lo pedido. Se **eliminó el estado `telasCfgModo`** ('ver'/'asignar') y con él los botones «Asignar»/«← Volver». Ahora, al abrir «Mostrar telas asignadas», el panel es uno solo: **PASO 1** «Piezas elegidas» (se tocan/recuadran en el visor apenas se entra — la selección está activa siempre que el panel esté abierto, `telasPanelAbierto` reemplaza a la condición del modo en `startDrag`, `iniciarRubber` y el `onMouseDown` del contenedor) + botón **«Seleccionar tela»** (abre el modal de tarjetas); **PASO 2** «Asignadas»: buscador + lista de las telas ya asignadas, tocar una pinta sus piezas en el visor, ✕ para quitarla. El resaltado de piezas seleccionadas ya no depende del modo (`telasCfgPiezas.length > 0`). VERIFICADO: compila, 0 referencias a `telasCfgModo`/`modoA`. NO verificado a mano (login).

- **2026-07-24 (91) — Telas del molde: «Seleccionar tela» abre un MODAL de tarjetas (reemplaza el botón Asignar del panel).** Flujo nuevo en modo asignar: se eligen las PIEZAS en el visor (toque / recuadro / arrastre) → botón **«Seleccionar tela»** (dice a cuántas piezas va) → **Modal** (componente `Modal` del sistema, `maxWidth 860`) con **buscador arriba** y **todas las telas en tarjetas CUADRADAS** (`aspectRatio 1/1`, grid `auto-fill minmax(132px,1fr)`, el color de la tela de fondo, nombre + ancho abajo con degradado, ✓ al tildar); pie con el contador, «limpiar» y **«Asignar»**. Al asignar, `asignar()` guarda y vuelve a modo VER → **se ve lo asignado** (lo pedido). El subtítulo del modal avisa el destino («a 3 piezas: …» / «a TODAS las de la variable» / «a TODAS las del molde»). En modo asignar se ocultan la lista de telas del panel y su buscador (ahora viven en el modal); en modo VER queda igual (lista de asignadas + buscador + pintar al tocar). Estados nuevos `telaCfgModalOpen`/`telaCfgModalBuscar`. App.jsx: botón ~10339, modal ~10432. VERIFICADO: compila; `asignar()` vuelve a 'ver' (línea ~10273). NO verificado a mano (login).

- **2026-07-24 (90) — Telas del molde: selección múltiple con el RECUADRO del sistema (`iniciarRubber`), que es el gesto real de Variables.** Yo había inventado un pintado propio (mouseenter/mousemove) en vez de buscar el mecanismo existente — el usuario lo pidió 3 veces como «el de variables». **El sistema YA tiene selección múltiple por arrastre: `iniciarRubber`** (recuadro punteado, `rubber`), que se dispara desde el contenedor del visor con botón izquierdo **desde un espacio VACÍO** (`!e.target.closest('[data-piece]')`) y al soltar resuelve las piezas por intersección de `getBoundingClientRect` con `[data-piece]`. Lo dice el propio cartel de Variables: «tocá una pieza, o **arrastrá un recuadro** desde un espacio vacío para elegir varias». Enganchado para telas: `modoTelas` en `iniciarRubber` + en la condición del `onMouseDown` del contenedor (~12136) + `agregarPiezasATela(idxs)` (suma por CLAVE COMPLETA, sin duplicar). Se mantiene además el pintado al arrastrar POR ENCIMA de las piezas (onMouseMove del svg). App.jsx: `agregarPiezasATela` ~5607, `iniciarRubber` ~5613, contenedor ~12136. **LECCIÓN: antes de inventar un gesto, buscar si el visor ya lo tiene (`iniciarRubber`, `startDrag`, `addSelNombrar`).** VERIFICADO: compila. NO verificado a mano (login).

- **2026-07-24 (89) — Telas del molde: elegir PIEZA POR PIEZA (no todo el genérico) + el arrastre ahora sí funciona.** Dos bugs del (88): (1) **agrupaba**: yo usaba el nombre GENÉRICO (`_genTelaP` → «Frente») como clave, y `datos/productos/<pid>/piezas.json` muestra que cada pieza tiene su **clave única** (`{id:'pz_0020', nombre:'Frente', numero:1, clave:'Frente 1'}`) → tocar un frente marcaba TODOS los frentes. Ahora la config usa la **clave COMPLETA** (`_clavePiezaTela(idx)` = `etqNombres[idx]` tal cual, «Frente 1») en `startDrag`, `pintarTelaPieza`, el resaltado, el pintado de «ver tela», `piezasMolde` y `piezasDeVar`. (2) **el arrastre no tomaba**: `onMouseEnter` de cada pieza no llega de forma confiable con el botón apretado → el pintado se resuelve ahora en el `onMouseMove` del SVG buscando `e.target.closest('[data-piece]')` (el `<g>` de cada pieza ya traía `data-piece={p.idx}`); el `onMouseEnter` queda como respaldo. PUENTE con el pedido: el Arte maneja las piezas por genérico, así que al calcular disponibilidad usa `_extrasDeGen(gen)` = unión de las telas de TODAS las claves de ese genérico. `piezasArteGen` (validación del pedido) sigue en genérico a propósito: es el modelo del pedido/motor. VERIFICADO: compila. NO verificado a mano (login).

- **2026-07-24 (88) — Telas del molde: seleccionar piezas PINTANDO con el mouse (arrastre), no de a una.** El toque simple (87) no alcanzaba: se pidió el gesto de arrastrar con el botón izquierdo apretado sobre las piezas, y el MISMO gesto para desmarcar. Implementado con `pintaTela = useRef({on, modo})`: al apretar sobre una pieza se fija el modo según su estado (suelta → `add`, ya elegida → `del`), y `onMouseEnter` de cada pieza (`pintarTelaPieza`) aplica ese modo a todas las que se van tocando — idempotente, pasar dos veces por la misma no la alterna. Se corta en `endDrag` (mouseup/mouseleave del svg) y con un listener global de `mouseup` (por si se suelta fuera del visor). OJO: este gesto de pintar-arrastrando NO existía en el visor (nombrar/variables sólo hacen toggle en el mousedown) — se agregó acá; si se quiere en Variables/Nombrar hay que replicarlo igual. App.jsx: ref ~2905, `startDrag` caso telas ~4417, `pintarTelaPieza`+useEffect ~4525, `onMouseEnter` en la pieza ~12985. VERIFICADO: compila. NO verificado a mano (login).

- **2026-07-24 (87) — Telas del molde: las piezas se eligen TOCÁNDOLAS EN EL VISOR (no con chips).** El sistema ya tenía ese gesto (nombrar piezas, armar variables, conjuntos, grupos) y yo había puesto una lista de chips aparte — incoherente con el resto de la app (reclamo del usuario). Ahora, en la pestaña Telas + modo asignar, `startDrag(e, idx)` (el MISMO handler que usan Variables/Nombrar) suma/quita la pieza tocada en `telasCfgPiezas`, guardada por nombre GENÉRICO; las piezas seleccionadas se resaltan en cyan en el visor y el resto queda neutro (`_telaAsigPz`, primero en la cascada de `fillCol`). El panel dejó de listar chips: sólo muestra el resumen «N piezas: …» + «limpiar», y si no hay ninguna tocada avisa que la tela va a todas las de la variable. App.jsx: `startDrag` ~4404 (caso telas al principio), color ~12833, panel ~10292. NOTA para el futuro: **cualquier selección de piezas en Config va por el visor con `startDrag`, nunca con listas paralelas.** VERIFICADO: compila. NO verificado a mano (login).

- **2026-07-24 (86) — Telas del molde: el modo VER muestra SÓLO las asignadas y al tocar una se pinta en sus piezas.** Antes el panel listaba TODO el registro también en modo ver (telas sin asignar mezcladas con las asignadas → confuso; reclamo del usuario). Ahora: (a) modo **VER** = sólo las telas ASIGNADAS (las de la variable elegida, o las del molde con «Todo el molde»); el registro completo se ve únicamente en modo **ASIGNAR**, que es donde hay que poder sumar. (b) Al **tocar una tela** en la lista, sus piezas se pintan en el VISOR con el color de esa tela y el resto queda neutro (`telaCfgVerId`; se calcula por pieza con `todas ∪ por_pieza[genérico]` e inyecta `fillCol/badgeFill` al principio de la cascada de colores del visor, ~12833); la fila queda marcada con una barra del color y volver a tocarla apaga el resaltado. Se resetea al entrar a la pestaña, al cambiar de variable, al abrir/cerrar el panel y al entrar/salir de asignar. App.jsx: estado ~2850, `_base` ~10185, lista ~10311, visor ~12833. VERIFICADO: compila. NO verificado a mano (login).

- **2026-07-24 (85) — Telas del molde: al elegir una variable, el VISOR muestra SOLO esa variable con su acomodo.** Se engancha el mecanismo que ya usaban Etiqueta/Diseño: el chip de variable ahora hace `setVerVariante(clave)` → `varianteFiltro` reduce el visor a las piezas de esa variable y reproduce su ACOMODO del nido (si no hay nido, cae a la grilla compacta). Se agregó `'telas'` a la condición de `cargarNido` (~5000) para que el acomodo esté disponible en esta pestaña; al entrar a Telas se resetea a vista completa (`verVariante=null`). App.jsx ~4697 y ~10238. OJO al editar: el comentario explicativo va ANTES del `return (` del `.map`, no adentro — puesto como `{/* */}` dentro del return rompe el build («Expected ")" but found "key"»), pasó y se corrigió. VERIFICADO: compila. NO verificado a mano (login).

- **2026-07-24 (84) — FIX: el selector de VARIABLE de telas estaba escondido (no se veía).** En (83) lo puse DENTRO del modo asignar → había que entrar «Mostrar telas asignadas» → «Asignar» para verlo; en la pantalla de Telas asignadas no se veía ninguna variable (reclamo del usuario con captura). Ahora el bloque **Variable** va ARRIBA DE TODO, siempre visible, apenas se entra a la pestaña: chips «Todo el molde · N pzas» + una por variable con su cantidad, y debajo la lista de piezas de la variable elegida. Lo elegido ahí manda en todo lo de abajo: el contador del botón muestra las telas de esa variable, y en modo VER la lista se filtra a las telas disponibles en ella (en modo ASIGNAR se ve todo el registro, para poder sumar). Se eliminó el selector duplicado de adentro. Si el molde no tiene variables con piezas, sale un aviso ámbar explicando que se asigna sobre las piezas del molde y que se armen en Ajustes › Variables (antes no se mostraba NADA y parecía roto). App.jsx pestaña telas ~10213. VERIFICADO: compila. NO verificado a mano — la pantalla exige login y no tengo credenciales; el mockup estático del browser no permite screenshot. **Es la 3ª iteración de esta pantalla: si sigue sin verse, revisar `variantesEdit` (se llena en el effect de `activoProdDetalle`, ~4677) antes de tocar la UI.**

- **2026-07-24 (83) — Telas del molde: elegir POR VARIABLE (corrección de la entrega 1).** La pantalla listaba las piezas del MOLDE entero (~135) sueltas → iba contra el diseño VARIABLE-FIRST del sistema (ver [[mapeo-por-variable]]: se trabaja con las ~9 piezas de la variable). Ahora, en el modo asignar, primero se elige la **Variable** (chips con el nº de piezas de cada una, + «Todo el molde») y las piezas que se listan son SÓLO las de esa variable (`v.valores` con `pieza_idx`, nombre por `etqNombres`/registro con fallback al label, normalizado a genérico). El objetivo de la asignación queda: piezas tildadas → esas; ninguna tildada CON variable → todas las de la variable (se guarda como `por_pieza`); ninguna tildada SIN variable → `todas` (global). El botón lo dice: «Asignar N a 3 pieza(s)» / «a la variable (9 pzas)» / «a todas las piezas». App.jsx: estado `telasCfgVar` ~2848, lógica y UI en la pestaña telas ~10130-10250. VERIFICADO: compila, app sin errores de consola. NO verificado a mano (detrás del login). Sigue faltando: entrega 2 (**tope de telas por variable en la config**) y 3 (grupos combinables + filtrado en el pedido).

- **2026-07-24 (82) — TELAS POR PIEZA en la config del molde (Entrega 1 de 3).** Modelo nuevo `prod["telas_cfg"] = {"todas":[telaId…], "por_pieza":{"Frente":[telaId…]}}`: disponible en una pieza = `todas` ∪ `por_pieza[pieza]` (ej. 10 a todas + 2 extra en 3 piezas → esas 3 ofrecen 12 y el resto 10). Claves = nombre GENÉRICO de pieza (igual que la asignación del pedido). COMPAT: los moldes viejos con `telas_asignadas` (lista plana) se leen como `todas` (`_telas_cfg_prod`), y `telas_asignadas` se sigue guardando como la UNIÓN plana para no romper lo que ya la lee. Server: `POST /api/productos/telas_asignadas` acepta `{todas, por_pieza}` (y la forma vieja `{telas}`); `/api/productos` expone `telas_cfg`. Frontend Config › molde › Telas asignadas: botón **«Mostrar telas asignadas»** → panel con **buscador + botón Asignar**; en modo asignar se tildan telas y se eligen piezas (ninguna = TODAS) → «Asignar N a X piezas / a todas»; cada tela muestra dónde está disponible (chip «todas las piezas» / «N piezas: …») y se puede quitar; resumen de piezas con telas propias. COHERENCIA: el panel de telas del ARTE ahora ofrece sólo lo disponible para las piezas seleccionadas (INTERSECCIÓN, porque la tela se aplica a todas las tildadas; sin selección = las de `todas`); si el molde no tiene nada configurado, sigue ofreciendo todo el registro. VERIFICADO: sintaxis OK, compila, server reiniciado (PID 26756), app sin errores de consola. NO verificado a mano (la pantalla está detrás del login). **FALTAN las entregas 2 y 3 (decididas con el usuario):** (2) límite por variable = **tope de cuántas telas se pueden dejar disponibles para esa variable en la CONFIG** (no del pedido); (3) mejorar visualmente los grupos combinables en Config › Telas y **filtrar las telas del pedido según lo ya elegido**, con la regla: una tela SIN grupo no combina con nada (sólo aparece con las de su mismo grupo).

- **2026-07-24 (81) — FIX: «faltan piezas sin tela» aunque se asignaran TODAS (falso positivo del bloqueo #77).** Causa: la validación y el visor miraban listas DISTINTAS. El visor muestra/toca sólo las piezas de la VARIABLE en vista (`canvasLayout.layout` filtrado por `vfArte`) y con el nombre que se MUESTRA (`etqNombres` manda sobre el del registro); mi validación usaba `mapeoData.piezas` = TODAS las del molde (~135) con los nombres del registro → el operario asignaba las ~9 que veía y quedaban ~126 «faltando» para siempre (bloqueo imposible de destrabar). Fix: nuevo memo `piezasArteGen` = piezas VISIBLES del visor (mismo filtro y mismos nombres, con el mismo piso `show` vacío si la variable no resuelve), usado por el effect, por el aviso (`_sinTela`) y por «Asignar a todas» (`_todasGen`) → validar y asignar hablan EXACTAMENTE de lo mismo. Además el registro pasó de `telasFaltantes[pid]` a **`[pid|clave-de-variable]`** (un mismo molde puede entrar con 2 variables, cada una con sus piezas; antes se pisaban entre sí) y el total suma SÓLO los ítems que hoy están en el pedido → una variable quitada no deja bloqueo fantasma. App.jsx ~6711 (memo+effect+total) y ~8582 (panel). VERIFICADO: compila, sin refs colgadas, app sin errores de consola. NO verificado a mano (la pantalla está detrás del login).

- **2026-07-24 (80) — Config › Telas: se quitan los campos de conexión; queda sólo el cartel de estado.** Como la api-key ya viaja con el paquete (#79) y las telas llegan bien al publicado, la conexión no se configura más desde la app. UI: en lugar del bloque con URL + api-key + «Guardar conexión», ahora hay un chip «● Conectado al sistema de stock» (verde) / «● Sin conexión con el sistema de stock» (ámbar), alimentado por `GET /api/telas/conexion`. Se eliminaron `telaKeyInput`/`telaUrlInput`/`guardarTelaConexion` (front) y **el endpoint `POST /api/telas/conexion`** (server): sin pantalla que lo use, un POST que escribe la clave y la URL era superficie de ataque al pedo — justamente el que hubo que blindar con la allowlist en #70. El `GET` (informativo, sin exponer la key) y `_host_permitido` en el fetch saliente SIGUEN. La clave se cambia en `config_externo.json` / env `EXTERNAL_API_KEY` y se propaga publicando. VERIFICADO: sin refs colgadas, compila, sintaxis OK, server reiniciado (PID 26072), sólo queda el GET de conexión, app carga sin errores de consola.

- **2026-07-24 (79) — La api-key de telas VIAJA en el paquete + el error de telas ya no es «Unexpected token '<'».** Contexto: el fix del prefijo (#78) YA está publicado (v1.0.8, verificado: `/Tizadapro/Tizadapro/api/salud`→200 JSON) y aun así el publicado seguía mostrando el error de HTML → el HTML NO era del prefijo sino del **proxy de adelante** (502/504) al no poder alcanzar `user.com.uy` desde el servidor. Cambios: (1) `empaquetar.py` incluye `config_externo.json` en el paquete (mismo criterio que `token_actualizacion.txt`: el usuario no quiere pegar claves en cada ambiente) → el publicado queda configurado solo; sigue GITIGNOREADO (nunca al repo). VERIFICADO listando el zip: `config_externo.json` presente con la key. (2) Server: timeout del fetch externo 20s→**12s**, para contestar el error en JSON ANTES de que el proxy corte. (3) Frontend `_jsonTelas(res)`: si la respuesta no es JSON, muestra **el código HTTP real** («el servidor respondió 504 … sin JSON. Suele ser que no pudo alcanzar la API del sistema de stock») en vez del críptico Unexpected token; se usa en `refrescarTelas` y `guardarTelaConexion`. VERIFICADO: compila, sintaxis OK, server reiniciado (PID 24444), taller sin prefijo intacto. **Si tras publicar sigue fallando, el mensaje dirá el código → si es 502/504, el servidor de Amazon NO tiene salida a user.com.uy (firewall/Security Group) y hay que habilitarla.** Ver [[api-telas-externa]].

- **2026-07-24 (78) — FIX publicado: «Unexpected token '<', <!DOCTYPE» y el login que no tomaba la contraseña (acceso SIN nginx).** DIAGNÓSTICO (verificado contra el server publicado): la API del publicado responde bien CON prefijo (`/Tizadapro/api/auth/login` → JSON) y el bundle publicado es el nuevo y trae el prefijo compilado. El HTML aparece cuando se entra al servidor **sin pasar por nginx** (localhost:8050 o la IP en la propia máquina de Amazon): ahí nadie QUITA el `/Tizadapro` que pide el frontend, y Flask contestaba 404/405 en **HTML** → el `res.json()` del front tiraba «Unexpected token '<'». Mismo motivo para el login (la respuesta no era JSON). REPRODUCIDO en local: `/Tizadapro/api/salud` → 404 text/html. FIX: middleware WSGI `_QuitarPrefijo` (`app.wsgi_app`) que saca `_PREFIJO_APP` (env `TIZADA_PREFIJO`, default `Tizadapro`) y setea `SCRIPT_NAME` → la app anda IGUAL con y sin nginx. Va como middleware y NO como `before_request` porque Flask resuelve la ruta antes de los before_request. VERIFICADO tras el fix: con prefijo `/Tizadapro/api/salud`→200 JSON, `POST /Tizadapro/api/auth/login`→401 **JSON** («usuario o contraseña incorrectos»), `/Tizadapro/`→HTML del SPA, assets y logo 200; sin prefijo (taller) todo sigue 200. Server reiniciado (PID 14024).

- **2026-07-24 (77) — Arte: NO se avanza a la planilla si quedan piezas sin tela (obligatorio de verdad).** Antes el aviso (#75) no bloqueaba. Ahora: estado `telasFaltantes={pid:nº}`, un effect registra por molde cuántas piezas genéricas (`mapeoData.piezas`) siguen sin tela en `telaPorPieza[pid]`; `telasIncompletas` = suma>0 sobre los moldes del pedido. `irAPlanillaDesdeArte` corta con `showError` si faltan; el botón «A la planilla» queda deshabilitado + aviso rojo «⚠ Faltan N pieza(s) sin tela» en la barra inferior; el atajo Enter llama a la misma función (ya bloquea). App.jsx: estado ~2846, effect+deriv ~6708, función ~3723, botón ~8795. Robusto: `mapeoData.piezas` es molde-wide → «Asignar a todas» (misma fuente) SIEMPRE lo satisface, no hay dead-end. Conservador: puede pedir tela de genéricos que la variable del pedido no use (1 click con «a todas»). VERIFICADO: compila. NO verificado a mano (browser bloqueado). Solo frontend, sin reinicio.

- **2026-07-24 (76) — La tizada usa el ANCHO DE IMPRESIÓN y ahora lo muestra en el resumen.** (1) Verificado que el tamaño de hoja = ancho de impresión: `hoja.ancho_cm` = `cfg_t['ancho_cm']` = `telas_cfg[tela]['ancho_cm']` = `cat['telas'][].ancho_cm` = el ancho de impresión editable (NO la medida). Comprobado con datos reales del usuario: tela id 44 «Bandera» medida 160 → `ancho_cm`=157 en el catálogo → la hoja sale 157 cm. El motor (`_nestear_y_componer`) nunca usa `medida_cm` (es sólo informativa en la UI). (2) El visual de cada mesa ya mostraba `ancho × alto m` (App.jsx ~1864, usa `hoja.ancho_cm`); se AGREGÓ el ancho al RESUMEN de cada hoja (~9707): «<b>N cm de ancho</b> · P pág · L m de largo · X% eficiencia». VERIFICADO: compila; catálogo confirmado (telas_ancho con overrides 157/147/165…). Solo frontend, sin reinicio.

- **2026-07-24 (75) — Arte/telas: SIN tela base (cada pieza debe tener tela) + buscador en «Asignar tela».** (1) Se eliminó la tela BASE: `_telaDeGen(gen)` ya no cae a una base, devuelve `null` si la pieza no tiene tela asignada; `telaColorPieza` pasa `null` → esas piezas se ven SIN teñir (sin asignar). `_todasGen` (de `mapeoData.piezas`) permite «Asignar a todas» escribiendo override por pieza (ya no una base) y calcular `_sinTela`. La vista «Telas asignadas» muestra un aviso: rojo «⚠ Faltan N piezas sin tela» / verde «✓ Todas tienen tela». Se quitaron los tags «base» y `setTelaBaseMolde` del flujo (el payload ya no manda base para pedidos nuevos). (2) Buscador `telaBuscarAsig` en la vista Asignar: filtra `_telasMol` por nombre (útil con 35 telas). App.jsx ~8545 y panel ~8570-8620. VERIFICADO: compila. NO verificado a mano (browser bloqueado para localhost). NOTA: el aviso es no-bloqueante; si el usuario quiere BLOQUEAR la generación con piezas sin tela, es un paso extra a decidir.

- **2026-07-24 (74) — Telas: se separa MEDIDA (dato del sistema) de ANCHO DE IMPRESIÓN (editable, el que usa la tizada).** Antes había un solo `ancho_cm`. Ahora cada tela trae `medida_cm` = ancho parseado de la descripción de la API (informativo, no editable) y `ancho_cm` = ancho de IMPRESIÓN que usa la tizada (editable local en `cat['telas_ancho']`, default = la medida o 180). Server: `_fetch_telas_externas` agrega `medida_cm`; `_telas_merge` calcula ambos; `_config_produccion` sigue usando `ancho_cm` (impresión) → la tizada nestea con el ancho de impresión, no con el del rollo. Frontend Config › Telas: la lista ahora tiene cabecera (Tela · Medida · Ancho de impresión); Medida read-only, Ancho de impresión editable (onBlur→/api/telas/ancho). VERIFICADO: las 35 telas parsean medida (160/168/183…); compila; server reiniciado (PID 39928). Ver [[api-telas-externa]].

- **2026-07-24 (73) — FIX consola llena de 401 + crash al abrir sin sesión (secuela del #72).** Al exigir sesión en toda la API, los fetch de arranque (que salían ANTES del login) recibían 401: (a) varios guardaban el `{error}` como datos → `Uncaught TypeError: reading 'find'` (`productosCat.productos` undefined), y (b) la consola se llenaba de rojos. Fix doble: (1) `fetchEstado/fetchProductos/fetchConfig/fetchPlantillasPlanillas` ahora chequean `res.ok` (los demás ya lo hacían); (2) NUEVO `sesionLista = authListo && (yo?.id || !authOn)` — los fetch de arranque NO se disparan hasta que la sesión esté resuelta: effect principal (productos/estado/catálogo/config/plantillas/reglas/presets/grupos) + effect de `[activoTab]` + effect de `[productosCat.activo]` gateados por `sesionLista`; el effect de montaje quedó SOLO con el listener de teclado. En modo sin usuarios (`authOn=false`, taller sin base) también dispara. Al loguear, se re-pide todo (dep `yo?.id`). App.jsx ~3210/3540/3879/4116. VERIFICADO: compila; no verificable en browser (pane bloqueado para localhost) — el usuario debe recargar y ver la consola limpia pre-login.

- **2026-07-24 (72) — SEGURIDAD GLOBAL: TODA la API exige sesión iniciada (el login ya no es sólo una cortina del frontend).** Respuesta a «¿si alguien aprieta F12 sin loguearse puede acceder?»: el bundle JS siempre se descarga (normal, el frontend no es secreto), pero ANTES desde la consola/curl se podían llamar casi todos los endpoints sin sesión (`/api/productos` devolvía el catálogo, `/api/estado`, etc.). Ahora la guardia global `_guardia_moldes` (before_request) tiene 2 capas: (1) SESIÓN OBLIGATORIA para todo `/api/*` salvo `_API_SIN_SESION` = `/api/auth/*` (login), `/api/salud` (monitoreo/instalador/actualizador) y `/api/actualizacion/*` (token propio X-Token-Act); (2) la propiedad del molde (igual que antes). Si `_USUARIOS_ON` es False (taller sin base MSSQL) no se exige — el sistema sigue andando solo. Si la base parpadea en runtime, deja pasar (la seguridad no tumba el sistema). VERIFICADO sin sesión: productos/estado/telas→401; salud/actualizacion/auth-yo/frontend→200. NO verificado con login real (no tengo credenciales) — el guard usa el mismo `_usuario_actual()` de siempre, y el front ya re-pide el catálogo al iniciar sesión (comentario ~3202); OJO: los fetch de arranque pre-login ahora reciben 401 (antes datos) → si aparecen toasts de error sobre la pantalla de login, es cosmético y se ajusta en el front. El guard de telas (#71) queda redundante pero inofensivo.

- **2026-07-24 (71) — SEGURIDAD telas: los endpoints exigen SESIÓN (un externo ya no puede llevarse la info del WMS vía TIZADA).** Criterio del usuario: dentro de TIZADA las telas son para todos los usuarios; lo prohibido es que un sistema externo use la API/key para tomar esa info (incluye nombres, códigos y PRECIOS del stock). Nuevo `_guard_sesion_telas` aplicado a los 6 endpoints (`GET /api/telas`, `refrescar`, `ancho`, `GET/POST conexion`, `POST /api/telas` grupos): sin sesión → 401. Flag `_USUARIOS_ON` al registrar el blueprint: si el sistema de usuarios no está (taller sin base MSSQL) no se exige sesión — mismo criterio del server (la seguridad no lo tumba). VERIFICADO: sin sesión `/api/telas`→401 y `/api/telas/conexion`→401; `/api/salud`→200. Con sesión pasa (usa el mismo `_usuario_actual()` del resto). Completa el combo con la allowlist de hosts (#70). Pendiente lado WMS (usuario): key read-only + IP-allowlist.

- **2026-07-24 (70) — SEGURIDAD telas: la api-key sólo se envía a hosts permitidos (cierra un vector de robo).** El endpoint `POST /api/telas/conexion` (que introduje en #69) dejaba fijar una URL arbitraria → un atacante podía apuntar la URL a su server y con `refrescar` hacer que TIZADA le mandara la key real en el header. Fix: allowlist `_HOSTS_TELAS_OK` (user.com.uy, localhost) + `_host_permitido`: `set_telas_conexion` rechaza (400) URLs de otros hosts y `_fetch_telas_externas` NO manda la key si el host no está permitido. VERIFICADO: POST con url=evil.example.com → 400; GET /api/telas sigue dando 35. **PENDIENTE (no resuelto, requiere decisión):** (1) la API de TIZADA NO exige login del lado del server — el login es puerta del frontend; `_guardia_moldes` (único before_request) sólo chequea propiedad de molde, no autenticación → cualquiera que llegue a la URL llama los endpoints (verificado: `curl /api/telas` sin sesión devuelve datos). Endpoints de telas/conexión deberían exigir sesión admin. (2) Blast radius del WMS: la key debería ser READ-ONLY/scoped a telas y con IP-allowlist del lado del WMS, así un leak no permite descontar stock (`/api/articulos/descontar`). Ver [[api-telas-externa]] y [[molde-propio-desde-pedido]] (endpoints sin permisos).

- **2026-07-24 (69) — La api-key de telas se configura DESDE LA APP (no hay que tocar archivos en el server).** Nuevos endpoints `GET/POST /api/telas/conexion`: el POST escribe `config_externo.json` del lado del server (url/key; sólo pisa la key si mandan una nueva) e invalida el cache; el GET devuelve `{url, tiene_key, por_env}` SIN exponer la key. Frontend: sección «Conexión con el sistema de stock» en Config › Telas (chip Conectado/Falta clave, input URL + input password para la key + Guardar → reintenta refrescar). Resuelve «¿dónde pego la key en el publicado?»: se pega en la app. Si la key viene por env (`EXTERNAL_API_KEY`), el campo avisa que no la reemplaza. VERIFICADO: `GET /api/telas/conexion` → tiene_key true, compila, server reiniciado. Ver [[api-telas-externa]].

- **2026-07-24 (68) — TELAS ahora vienen de la API EXTERNA del WMS; local sólo el ANCHO.** El usuario dejó de crear telas de nuestro lado: se consumen de `GET user.com.uy/api/external/telas` (header `x-api-key`, key en `config_externo.json` GITIGNOREADO / env `EXTERNAL_API_KEY`). Server: `_fetch_telas_externas`+`_telas_efectivas` (cache mem TTL 300s + persiste en `cat['telas']` para offline/generación; UA `TIZADAPRO/1.0` por Cloudflare) + `_ancho_de_descripcion` (parsea el ancho del texto de la descripción). Endpoints: `GET /api/telas` (API+ancho), `POST /api/telas/refrescar`, `POST /api/telas/ancho` (guarda `cat['telas_ancho']={id:cm}`); `POST /api/telas` quedó SOLO para grupos. `_config_produccion` lee `cat['telas']` sin cambios → la tizada usa esos anchos. Frontend: Config › Telas = lista de la API (nombre read-only) + ancho editable (onBlur→/ancho) + «↻ Actualizar telas del sistema» + buscador; grupos siguen; `id` de tela = numérico API como string. VERIFICADO: `GET /api/telas` devuelve 35 telas reales con ancho parseado (160/150/168…), compila, server reiniciado. **Migración pendiente del usuario:** re-asignar telas a los moldes (los `telas_asignadas` viejos `tl_xxxx` no matchean los ids numéricos nuevos); los grupos viejos quedan stale. Ver [[api-telas-externa]].

- **2026-07-24 (67) — Ficha técnica: cada pieza dice EN QUÉ TELA va.** `generar_pedido(solo_piezas=True)` ya agrupa las piezas por tela (`ppt = {tela: piezas}`), pero `_molde_guia_ficha` lo llamaba SIN la asignación del pedido → grupo por defecto. Fix: se guarda `asig` (pieza→tela) y `_telas` (telas_cfg) en `_var_ficha[pid]` (servidor.py ~4372); `_molde_guia_ficha` los pasa a `generar_pedido` (`asignacion_tela`/`telas_cfg`) y guarda `pz['tela']` = el grupo real; y `ficha_tecnica.py _dibujar_piezas` dibuja «Tela: <nombre>» (acento) bajo el nombre de cada pieza (rótulo agrandado a 28pt, `h_cel=134`). VERIFICADO: sintaxis OK, server reiniciado (PID 26696, salud OK). NO verificado a mano (ficha detrás del login).

- **2026-07-24 (66) — Arte, panel de telas por pieza en 2 vistas (reemplaza el modal).** VISTA 1 «Telas asignadas»: sólo las telas EN USO en las piezas (`_telasEnUso` = base + overrides) + botón «Asignar tela» + ✕ (cerrar). VISTA 2 (al tocar «Asignar tela»): «← Volver» arriba, lista de las telas disponibles del molde (`_telasMol`) para ELEGIR una (resaltada, estado `telaElegida`), se tocan las piezas en el visor y el botón «Asignar» (habilitado al elegir tela) las asigna; limpia la selección para seguir asignando. Estados nuevos `telaAsignMode`/`telaElegida` (reemplazan `telaModalOpen`/`telaBusqueda`); se eliminó el modal «Asignar tela al pedido». `aplicarTela` ya no cierra modal. App.jsx ~8490-8560. VERIFICADO: compila. NO verificado a mano: Browser pane bloqueado por política para localhost.

- **2026-07-24 (65) — Arte: el selector de tela por pieza aparece SIEMPRE que haya telas en el registro.** El botón «Ver telas de pieza» (paso Arte) estaba gated por `_telasMol.length>0`, y `_telasMol` = registro filtrado por las telas ASIGNADAS al molde → si el molde no tenía telas asignadas (o `telasReg` no había cargado aún), el botón no aparecía. Fix: `_telasAsig` = asignadas; `_telasMol = _telasAsig.length ? _telasAsig : (telasReg.telas||[])` → con asignaciones usa esas (igual que antes), sin asignaciones ofrece TODO el registro global. App.jsx ~8482. NOTA: la causa exacta del reporte del usuario («no aparece pese a tener telas asignadas») no se pudo reproducir — sin sesión `/api/productos` sólo devuelve `prod_default` con `telas_asignadas=[]` (los moldes reales son por-sesión); el wiring de `MapeadorArteVisual` (acciones/panelTela/telaModo) está intacto. Si aún no aparece, revisar que el molde del pedido esté en `productosCat.productos` (moldes de sesión) y que `fetchTelas` haya cargado. VERIFICADO: compila.

- **2026-07-24 (64) — Planilla: tipear una letra sobre la celda seleccionada entra a editar y arranca con esa tecla (como Sheets).** En `onSelKey`, si se presiona un caracter imprimible (length 1, sin Ctrl/Cmd/Alt) sobre una celda NO-toggle: `setPlEdit({..., typed:true})` (congela el ancho al valor previo) + `updateFila` reemplaza el contenido con la tecla. El editor pone el cursor AL FINAL (no selecciona): nuevo prop `autoSel` en ComboCell — con doble-click/Enter `autoSel=true` (selecciona todo + muestra todas), con tipeo `autoSel=false` (cursor al final + FILTRA por lo tipeado). App.jsx `onSelKey` ~7310, ComboCell `autoEdit`/`autoSel` ~348. VERIFICADO: compila. NO verificado a mano: Browser pane bloqueado por política para localhost.

- **2026-07-24 (63) — ComboCell: navegar las opciones con ↑/↓ cuando el desplegable está abierto.** Nuevo estado `hi` (índice resaltado) + `hiRef`. Con la lista abierta, ↑/↓ mueven el resaltado (clamp, sin navegar entre celdas) y `scrollIntoView` lo mantiene a la vista; **Enter** elige la opción RESALTADA (Tab sigue confirmando el texto tipeado); el hover del mouse sincroniza el resaltado (`onMouseEnter→setHi`); al abrir se resalta la opción actual (o la 1ª), al escribir vuelve a 0. App.jsx ComboCell ~334-410. VERIFICADO: compila. NO verificado a mano: Browser pane bloqueado por política para localhost esta sesión.

- **2026-07-24 (62) — Planilla: la columna NO cambia de ancho al editar (fix definitivo).** El `size={1}` (61) no alcanzó: `type=number` ignora `size` y en general el control de edición podía diferir. Ahora el ancho lo define SIEMPRE una **capa estática** en flujo normal (`visibility:hidden` al editar → conserva el box y su aporte al ancho de columna), con el valor **CONGELADO** al entrar a editar (`plEdit.val`, vía `entrarEdicion`) para que tampoco crezca al escribir. El **editor** (input/ComboCell/toggle) va **superpuesto en `position:absolute; inset:0`** → NO aporta ancho a la tabla (auto-layout lo ignora). Al confirmar, la estática vuelve visible con el valor vivo (recién ahí la columna se ajusta al contenido nuevo, como Sheets). App.jsx: `entrarEdicion` ~7255; ComboCell root `width:100%` ~368; render de celda ~8188. VERIFICADO: compila. NO verificado a mano: el Browser pane quedó **bloqueado por política** para localhost esta sesión → mecanismo CSS garantizado (visibility:hidden conserva el ancho; absolute no aporta ancho).

- **2026-07-24 (61) — Planilla: al editar (doble-click/Enter) ya NO se ensancha la columna.** Causa: un `<input>` sin atributo `size` tiene ancho intrínseco de ~20 caracteres; con la tabla en layout automático, al pasar del `<div>` estático (angosto) al input, la columna se agrandaba para caber ese mínimo. Fix: `size={1}` + `minWidth:0` en el input de texto (~8215) y en el input del ComboCell (`cs` + `size=1`, ~356/369); el toggle en edición con `width:100%`+`minWidth:0` y botones `minWidth:0/overflow:hidden` (~8189). Así el control de edición no impone ancho y la columna la sigue definiendo el texto/encabezado. VERIFICADO: compila. NO verificado a mano: el Browser pane quedó bloqueado por política esta sesión (file:// timeout, http bloqueado) → el fix es CSS estándar para este síntoma.

- **2026-07-24 (60) — Ficha técnica: se quita la MEDIDA de las piezas del molde guía.** El rótulo de cada pieza ahora muestra sólo el nombre general (no «w×h cm»); se recuperó ese espacio para agrandar un poco la imagen (`h_card = h_cel - 18`, antes -26). `ficha_tecnica.py` `_dibujar_piezas`. OJO: es Python y el server NO tiene auto-reload + cachea el módulo → toma efecto al reiniciar `py servidor.py` o al publicar la nueva versión.

- **2026-07-24 (59) — Ficha técnica: la tabla refleja SOLO las columnas visibles del paso planilla.** Antes el payload de la ficha (`planilla` en `/api/generar_multi`) mandaba TODAS las columnas del template; ahora se filtra por `colActiva` → las columnas ocultas por molde en la planilla tampoco aparecen en la tabla de la ficha. App.jsx ~5611 (`.filter(c => colActiva(c))`). El server no cambió (usa la `planilla` que llega). VERIFICADO: compila; no verificable a mano (la ficha se genera detrás del login).

- **2026-07-24 (58) — Planilla estilo Google Sheets: SELECCIONAR ≠ EDITAR + arrastre sin secuencia en variantes/diseño.** (A) Nuevo estado `plEdit {r,c}` (celda en edición). En modo SELECCIÓN cada celda es un `<div>` ESTÁTICO focusable (sin cursor/desplegable): **1 click** selecciona, **arrastrar** selecciona rango, **Supr/Backspace** borra el contenido de TODO el rango (`_borrarRangoSel`), flechas/Tab mueven la selección (saltando columnas ocultas, `_colsVisibles`). **Doble-click** o **Enter** entra a EDICIÓN → recién ahí aparece el input o el desplegable (ComboCell con nuevo prop `autoEdit`: al montar enfoca y abre la lista). Dentro de edición: Enter confirma y baja, Tab al lado, Esc sale (`onEditKey`); al clickear otra celda o con blur, sale. `onSelKey`/`onEditKey`/`_focusCelda` reemplazan a `navKeyPlanilla` (eliminado). (B) El **fill-handle** en columnas de variante/diseño/desplegable/toggle ahora **sólo COPIA** el valor (sea número o letra), nunca hace secuencia numérica: `_colCopiaSolo(col)` + `_valFill(...,copiaSolo)`. Las de texto/número siguen continuando la progresión. App.jsx: ComboCell ~334; estado ~2794; helpers ~7250; render de celda ~8190. VERIFICADO: compila, sin errores de consola. NO verificado a mano (la planilla está detrás del login).

- **2026-07-24 (57) — Planilla, celdas desplegable (ComboCell): abrir con doble-click / Enter, y el clic en una opción ya no atraviesa.** (a) **Doble-click** sobre la casilla abre el desplegable (`onDoubleClick`→`abrir(true)`). (b) **Enter con la lista cerrada** la ABRE (no navega); con la lista abierta sigue confirmando/cerrando. (c) **Fix pass-through:** al elegir una opción se seleccionaba la celda de abajo — porque los eventos de un **portal de React burbujean por el árbol de componentes**, no por el DOM, así que el `onMouseDown` de la opción llegaba al `<td>` dueño y prendía `plSelDragRef`, y al cerrarse la lista el `mouseOver` sobre la celda expuesta extendía el rango. Se agregó `e.stopPropagation()` en la opción y en la flecha ▾. App.jsx ~334-402 (ComboCell). VERIFICADO: compila, sin errores de consola.

- **2026-07-24 (56) — Planilla: filas VACÍAS de verdad + se elimina «Cargar Ejemplo».** Corrección de la 55: (a) las 5 filas iniciales ahora salen con TODAS las celdas en blanco (antes precargaban talle/manga/diseño). (b) Se eliminó el botón **«Cargar Ejemplo»** y su función `loadExample` (lo que el usuario llamaba «pedido de prueba»). Para coherencia, TODAS las vías de fila nueva quedan vacías: `_defaultRow`, `addPrenda` («+»), y el fallback de `eliminarFila` al borrar la última. App.jsx ~3413/7118/7170/7335 y botón ~8289. VERIFICADO: compila, sin referencias a `loadExample`, sin errores de consola.

- **2026-07-24 (55) — Planilla del pedido: SIEMPRE arranca limpia con 5 filas, sin memoria.** El usuario pidió sacar la memoria de pedidos viejos y el pedido de prueba. Antes las filas se persistían en `localStorage['tizada_filas_<molde>']` y se restauraban al abrir → arrastraba datos viejos. Cambios (App.jsx ~3413): (1) el efecto de carga ya NO lee localStorage; inicializa `Array.from({length:5}, ()=>({...defaultRow}))` = **5 filas predeterminadas** (talle=1º disponible, manga=corta, diseño=el preparado en Arte, nombre/número vacíos). (2) Se ELIMINÓ el efecto que guardaba las filas en localStorage. (3) `filasInitRef` inicializa las filas UNA sola vez por molde activo (no en cada refresh de `productos`), así no se borra lo que el usuario carga en la sesión. (4) Efecto de montaje que **purga** todas las claves `tizada_filas_*` del navegador (limpia lo que hubiera quedado de versiones viejas). VERIFICADO: compila, sin errores de consola, `localStorage` sin claves `tizada_filas_` tras abrir. NOTA: dentro de la sesión las filas viven en el estado React (no se pierden al editar); no persisten entre recargas — es lo pedido.

- **2026-07-24 (54) — FIX: «Talle short» se mostraba aunque el molde use «Talle».** La regla de ocultar/mostrar columnas (entrada 53) matcheaba también por `c.role`, pero `mapeo_columnas` guarda **ids de columna**, no roles — y hay roles compartidos: **Talle** (id `talle`) y **Talle short** (id `talle_short`) son **ambas** `role: 'talle'`. Un molde que usa Talle mete `'talle'` en la unión → `colActiva(talle_short)` matcheaba por rol (`has('talle')`) y la prendía de más. **Fix:** `colActiva` ahora matchea **sólo por `c.id`**; las columnas NO mapeables (Diseño y dato libre, role ∉ {talle,nombre,numero,manga}) van siempre. Así, elegir Talle ya NO prende Talle short, y una columna de dato libre no se oculta por error. `COLS_MAPEABLES`+`colActiva` en App.jsx ~6537. VERIFICADO: compila, app sin errores de consola.

- **2026-07-24 (53) — Planilla: las columnas sin uso se OCULTAN (no se apagan) — regla de UNIÓN entre moldes.** El usuario aclaró la lógica: cada molde activa/desactiva columnas en su config de planilla; en el pedido una columna **se muestra si al menos UN molde elegido la usa** (unión) y **NO se muestra si ninguno la usa** (antes yo la dejaba gris/apagada — mal). Lo inteligente: con 2+ moldes, si uno solo necesita una columna, aparece. Cambio: la cabecera y las celdas devuelven **`null`** cuando `!colActiva(c)` (en vez del rayado gris). **Clave técnica:** NO se filtra el array `cols` (el fill/selección indexa por posición: `aplicarFill` usa `cols[c]`); se mantiene el índice `ci` sobre `cols` completo y sólo se omite el render de esa columna → alineación intacta y arrastre sin romperse. `colActiva`/`columnasActivasPlanilla` (unión de `mapeo_columnas` sobre `moldesUnion`) ya estaban. VERIFICADO: compila, app sin errores de consola. (El ocultado real por combinación de moldes necesita login+pedido para verlo a mano.)

- **2026-07-24 (52) — Planilla del pedido: más profesional + arrastre que no abre el desplegable + columnas apagadas según los moldes elegidos.** Tres pedidos del usuario. **(1) Arrastre vs desplegable:** `ComboCell` ya NO abre el desplegable al hacer foco/clic (era `onFocus→abrir(true)`); ahora se abre SÓLO con la flecha ▾, al ESCRIBIR, o con la tecla ↓. Así seleccionar una celda o agarrar el **tirador de relleno** (agrandado a 12×12, hitbox propio) para arrastrar ya no dispara el menú. **(2) Columnas apagadas:** una columna se «usa» si está en el `mapeo_columnas` de algún molde del pedido (`talle`→Molde 1, `talle_short`→Molde short; `nombre/numero/manga`→ambos; el `diseno` siempre activo). `columnasActivasPlanilla` (Set, `useMemo` sobre `moldesUnion`) + `colActiva(c)`; si no hay info, todas activas. La columna sin uso queda GRIS (opacidad 0.45, «· sin uso» en la cabecera) y sus celdas **apagadas** (rayado diagonal, no editables). **(3) Look pro:** cabecera con degradado + mayúsculas + tracking, `border-spacing:0`, zebra + hover de fila (`.planilla-tbl` en index.css), bordes finos. **VERIFICADO** con maqueta estática de los mismos estilos (`screenshot`): cabecera pro, «Talle short» apagada con rayado, zebra, tirador grande; `npm run build` OK; app sin errores. (El comportamiento del desplegable y el apagado real por molde necesitan login+pedido para verlo a mano.)

- **2026-07-24 (51) — Visor de la ficha: barra moderna con iconos, descarga por hoja EN cada hoja, miniatura legible, y se ocultó el «Descargar todo» de la tizada.** Pedidos del usuario. **(1)** El nombre de cada **miniatura** va ahora DEBAJO de la hoja (fuera de ella), legible, resaltado en acento si es la hoja visible. **(2)** Se quitaron los botones «Hoja N» de la barra superior; ahora cada **hoja grande** tiene un **ícono de descarga** flotante en su borde superior derecho que baja SÓLO esa hoja (`urlHoja(i)`). **(3)** Los botones «Descargar ficha» e «Imprimir» son **píldoras modernas** con **iconos SVG en línea** (descarga = flecha a bandeja, impresora), acento cyan el primario. **(4)** El botón global «Descargar todo (N)» de la TIZADA (arriba a la derecha del paso 5) **se oculta cuando `vistaFicha`** (confundía: la ficha tiene su propia descarga). **VERIFICADO** con una maqueta estática de los mismos estilos (`screenshot`): botones modernos, miniaturas con label abajo, ícono de descarga en la hoja; app sin errores de consola; `npm run build` OK.

- **2026-07-24 (50) — Visor de la ficha: scroll único robusto + MINIATURAS al costado para saltar de hoja.** El usuario seguía viendo 2 barras; y pidió miniaturas laterales. **Scroll:** el cálculo del alto ahora mide el ancestro que REALMENTE scrollea (`.main-content`, que es `height:100vh; overflow-y:auto; padding:40px`) y hace `alto = sc.clientHeight - (sc.scrollHeight - el.clientHeight)` → descuenta TODOS los paddings/cabeceras sin hardcodear; el visor llena exacto y la página deja de scrollear. (No verificable a ojo en este entorno: el preview de archivos externos da `innerHeight:0`; los números confirman `otros=242px`, en pantalla real 900px → visor 658px, overflow 0.) **Miniaturas:** `VisorFicha` pasó a DOS columnas dentro de una fila de alto fijo — izquierda las **miniaturas** (`imgPag(i, z=1)`, botón por hoja, resalta la actual) que al tocar hacen `scrollIntoView` de la página grande; derecha las páginas. Cada columna scrollea por su cuenta (estilo del sistema). Nuevo endpoint `pagina_img` sirve también las miniaturas (z chico). Al scrollear las páginas grandes, la miniatura de la hoja de arriba se resalta (`onScroll`). VERIFICADO: compila, app sin errores de consola.

- **2026-07-24 (49) — Visor de la ficha: UN solo scroll (el del PDF); la página no supera el alto de pantalla.** El usuario mostró que había DOS barras (la de la página + la del visor). `VisorFicha` ahora mide el tope de su contenedor (`getBoundingClientRect().top`) y le pone `height = innerHeight - top - 14` (recalcula en `resize`) → el visor termina justo en el borde inferior de la pantalla, así **no queda contenido debajo y la página no scrollea**; el único scroll es el de adentro del visor (con el estilo del sistema). VERIFICADO: compila, app sin errores de consola. (La vista de resultados en sí necesita login+tizada para verla a mano.)

- **2026-07-24 (48) — Visor de la ficha ADAPTADO al diseño del sistema (sin recuadros, colores y scroll de la app).** El usuario: «adaptalo al diseño del sistema, quitale los recuadros, el color como el sistema, y la barra de scrolear adaptada al sistema». El `<iframe>` traía el visor de PDF del navegador con SU barra (no se puede pintar). **Solución:** el `VisorFicha` ahora muestra las páginas como **imágenes** en un contenedor con `overflow-y:auto` → usa el **scroll del sistema** (cyan/magenta, `::-webkit-scrollbar` global + `.ficha-scroll{scrollbar-width:thin;scrollbar-color:cyan}` para Firefox). Nuevo endpoint **`GET /api/trabajos/<tid>/pagina_img/<archivo>?pi=&z=`** que renderiza una página como **PNG** (fitz `get_pixmap`). Botones con las clases del sistema (`btn ghost`, sin recuadro, acento en «Descargar todo»): **Descargar todo · 🖨 Imprimir · Hoja N**. Imprimir usa un `<iframe>` OCULTO con el PDF real (`contentWindow.print()`, fallback abrir aparte) → impresión nítida, visor lindo. **GOTCHA:** `servidor.py` NO importa `fitz` a nivel módulo → `import fitz` LOCAL en `pagina_img` y en el conteo de `ficha_paginas` (daba 500 «name 'fitz' is not defined»). **VERIFICADO:** el endpoint devuelve PNG 200 (17 KB); app sin errores de consola; `npm run build` OK; server sano.

- **2026-07-24 (47) — Ficha técnica: nombre general (sin número) + columna «#» de fila + PESTAÑA con visor de PDF (imprimir / descargar todo o por hoja).** Tres pedidos del usuario. **(1)** En cada tarjeta de pieza se muestra el **nombre general** (`ficha_tecnica._generico`: «Frente 1»→«Frente»), sin el número. **(2)** La tabla de talles tiene ahora una **primera columna «#»** (estilo columna de títulos, fondo gris) con el **número de cada fila**; `_dibujar_tabla` numera continuo entre páginas (`fila0`). **(3)** En resultados se **quitó el banner grande** de la ficha; ahora hay una **pestaña «Ficha técnica»** junto a la(s) de tela (`vistaFicha` en `App.jsx`) que muestra el **PDF embebido en el mismo espacio** (`VisorFicha`): `<iframe>` con el visor nativo (imprimir + descargar todo), + barra propia con «Descargar todo el PDF», «🖨 Imprimir» (`iframe.contentWindow.print()`, con fallback a abrir aparte) y, si hay >1 página, **«Hoja N ⬇» por hoja** (reusa el endpoint de mesas `/api/trabajos/<tid>/mesa/<archivo>?pi=<pág>`). Backend: `res['ficha_paginas']` (cuenta de páginas con fitz). **VERIFICADO:** ficha con nombres genéricos + columna # (inspección visual); descarga TODO (2 pág, 50 KB) y SÓLO la hoja 2 (`pi=1`, 1 pág, 19.8 KB) por el endpoint real; app carga sin errores de consola. `npm run build` OK; server sano.

- **2026-07-24 (46) — Ficha técnica: 5 piezas por línea + tarjeta con sombra por pieza (y confirmado que el borde de corte SÍ sale).** Pedido del usuario. `ficha_tecnica._dibujar_piezas`: `cols=3→5`, celdas más chicas (`h_cel=132`, fuentes 7.5/6.5), y cada pieza ahora va en su **TARJETA** (sombra gris apenas corrida atrás + fondo casi blanco + borde fino) para que cada espacio se distinga. **Borde de corte:** verificado que la ficha lo incluye porque `_molde_guia_ficha` pasa `borde_corte=prod['borde_corte']` al motor (mismo PDF que la tizada) — el Molde 1 de las demos no lo mostraba porque NO tiene borde configurado; el «Molde short» (2mm negro) sí lo trae. **VERIFICADO** (Molde short, 6 piezas): 5 por línea + la 6ª baja, cada una en su tarjeta con relieve, formas reales y diseño recortado adentro — inspección visual OK.

- **2026-07-24 (45) — Ficha técnica, 3 ajustes: sin talle, con nombre del diseño, y el diseño DENTRO de la silueta (mismo PDF que la tizada).** Pedido del usuario: el molde guía es sólo una guía → **no debe decir el talle**; debe decir el **diseño** (para distinguir si hay más de uno); y **el diseño tiene que quedar recortado dentro de la pieza, sin el rectángulo a la vista**. **Diagnóstico VERIFICADO del rectángulo:** el render de `_piezas_base` SÍ trae el clip (8 clipPath en el SVG), pero el conversor **SVG→PDF de fitz DESCARTA el recorte** (0 ops de clip en el PDF resultante) → el diseño salía como su rectángulo. **Fix:** `_molde_guia_ficha` ya NO usa el SVG; llama a `MP.generar_pedido(..., solo_piezas=True)` (el MISMO camino que la tizada) y se queda con el **PDF vectorial de cada pieza** (`pz['doc'].tobytes()`), con el recorte NATIVO. `ficha_tecnica._dibujar_piezas` incrusta ese PDF con `show_pdf_page` (sin caja/fondo detrás). El encabezado pasó a «MOLDE GUÍA · <molde> · <diseño>» (se quitó el talle; `mg['diseno']`). **VERIFICADO** (prod_default/dcvd/v_x3706kt): la ficha muestra las 5 piezas de la variable con su **forma real** (musculosa: escote + sisas) y el diseño **recortado dentro**, sin rectángulo — inspección visual OK. Server sano.

- **2026-07-24 (44) — FIX ficha técnica: el molde guía usa la VARIABLE del pedido (= lo que arma la tizada), no un genérico.** El usuario aclaró: «agarrás la variable que usamos para ese pedido, el talle de guía, y ponés eso con el diseño dentro de la máscara de recorte; usá lo mismo que tomás para armar la tizada». Antes `_molde_guia_ficha` llamaba a `_piezas_base` con **`variante="*"`** → mostraba TODO el molde con un mapeo genérico. Ahora: en `/api/generar_multi` se captura por pid la **variable del pedido** (`_var_ficha[pid] = {clave, piezas, diseno}` de la 1ª fila traducida con `variante_clave`) y se pasa a `_molde_guia_ficha`, que llama a `_piezas_base(pid, diseno_del_pedido, variante_clave, talle_guia, mapeo_POR_VARIABLE)` — el MISMO render que la tizada (arte=tizada, diseño recortado a la máscara de cada pieza). Sólo se muestran las piezas de esa variable (filtro por `variante_piezas`; y de hecho `_piezas_base` con la clave real ya devuelve sólo ese subconjunto). **VERIFICADO** con `prod_default`/diseño dcvd/variable `v_x3706kt`: la ficha muestra **sólo las 5 piezas de la variable** (Cuello 2, Espalda 3, Frente 1, Sisa Der/Izq) al talle guía (4XL), con sus **formas reales** y el diseño recortado — inspección visual OK. Server sano.

- **2026-07-24 (43) — HECHO: FICHA TÉCNICA (PDF A4) que sale JUNTO con la tizada.** Pedido del usuario: al armar la tizada, un PDF A4 (varias páginas si hace falta) con la **tabla de talles arriba** y el **molde guía abajo** (diseño + piezas nombradas), como plantilla técnica. **Decisiones del usuario:** la tabla = **la planilla del pedido tal cual** (sus columnas y filas); el molde guía = **un talle de referencia** (el `variante_guia`, o el del medio); se genera **siempre, junto con la tizada**. **Nuevo módulo `ficha_tecnica.py`** (dibuja con fitz, sin dependencias nuevas): encabezado + `_dibujar_tabla` (paginación de filas) + `_dibujar_piezas` (grilla 3-col; cada pieza = su SVG incrustado VECTORIAL vía `fitz.open('svg')→convert_to_pdf→show_pdf_page` + nombre + medida cm). **Backend** (`servidor.py`): `_molde_guia_ficha(pid,prod,reg,diseno)` arma las piezas del talle guía con el MISMO render que el visor/tizada (`_piezas_base`, arte=tizada; el SVG viene base64 → se decodifica); en `correr()` de `/api/generar_multi`, tras las hojas y **best-effort** (si falla, la tizada igual queda), arma `FICHA_TECNICA.pdf` y setea `res['ficha']`. El front manda `planilla:{columnas,filas}` en el body y muestra un **botón de descarga** en resultados (`/trabajos/<tid>/FICHA_TECNICA.pdf`, misma vía que las hojas). **VERIFICADO** con datos REALES (molde «Molde short»/diseño erferg, talle M, 6 piezas): la ficha sale A4 (595×842), 1 pág, con la tabla (columnas Talle/Nombre/Número + 3 filas) y el molde guía con las 6 piezas nombradas + medidas; **inspección visual** (`_ficha_demo.png`) OK. Server sano tras el reinicio; front compila. **v1:** el molde guía es UN talle de referencia (el usuario lo eligió); si se quisiera por-talle o un botón aparte, es extensible. Ver [[ficha-tecnica]].

- **2026-07-23 (42) — El NÚMERO DE VERSIÓN se escribe en la pantalla de Publicación (ya no en el archivo VERSION).** El usuario: «cada pedido que te haga no crees una nueva versión; la versión se la escribiré yo antes de actualizar». Ahora `PantallaPublicacion` tiene un **campo «NÚMERO DE VERSIÓN»** (viene con un sugerido = el actual +1 en el último tramo; editable) y `POST /api/publicacion/publicar` acepta `version`: la valida (`\d+(\.\d+){0,3}`), la ESCRIBE en el archivo `VERSION` **antes de empaquetar** e invalida `_version._v` (la caché). Si el número es inválido, **no toca nada** y avisa. VERIFICADO: número mal → 400 y VERSION intacto; `9.9.9` con URL falsa → VERSION=9.9.9 y el zip armado lleva `9.9.9` adentro; restaurado a 1.0.4 y la URL real intacta. **REGLA para el agente: no bumpear VERSION en cada cambio** — ver memoria [[no-tocar-version]]. El número es sólo etiqueta; el paquete lleva el código actual.

- **2026-07-23 (41) — FIX v1.0.4: el selector de color estaba DESFASADO (ponías verde y pintaba azul).** La **barra de tonos** del `ColorPickerModal` tenía el degradado CSS **al revés** (`#f00 #f0f #00f #0ff #0f0 #ff0 #f00` = rueda girando hacia atrás), pero `onHue` calcula el tono de arriba a abajo en el orden HSV normal (`h = clientY/alto * 360`). Consecuencia: la franja **verde** se veía en el 67% pero ahí el código leía **240° = azul** → «pongo verde y pinta azul». **Fix:** degradado en el orden correcto (`#f00 0% · #ff0 16.67% · #0f0 33.33% · #0ff 50% · #00f 66.67% · #f0f 83.33% · #f00 100%`), que coincide con `onHue` y con el marcador (`hsv.h/360`). **VERIFICADO** (JS en el navegador reproduciendo `onHue`): clic en la franja verde (33%) → 120° → RGB(0,255,0) = verde. El cuadro Saturación/Brillo y los campos ya estaban bien; era sólo la franja. (Nada que ver con la conversión ICC (21), que sigue OK.)

- **2026-07-23 (40) — v1.0.2 PUBLICADA POR EL BOTÓN (primera vez, la hizo el usuario) + v1.0.3: la actualización aparece SOLA, sin F5.** El usuario publicó la 1.0.2 (animación del logo: flota + giro con brillo cada 6 s, clase `logo-animado` en los 3 `<img>`) con el botón de Config→Publicación — **el circuito completo funcionó en producción** — pero reportó: «tuve que recargar la página para que se actualice». **Causa:** `AvisoActualizacion` consultaba cada **30 s fijos**; con una actualización inmediata el corte entero pasaba entre dos consultas y la pantalla quedaba con el frontend viejo hasta un F5. **Fix (v1.0.3):** ritmo adaptativo con `setTimeout` encadenado — 30 s de base, **10 s** si hay una programada, **2 s** cuando faltan ≤15 s, cuando `en_curso`, o **cuando el servidor no contesta** (= se está reiniciando; además muestra «Actualizando…»); al volver con OTRA versión → `location.reload()` a los pocos segundos. La cinta ahora también se monta en la **pantalla de login** (antes el early-return de `LoginScreen` la dejaba afuera y quien estaba ahí entraba con el frontend viejo). **VERIFICADO EN VIVO** (browser): página abierta con una marca en `window` → server abajo → server arriba con otra versión → **la página se recargó sola** (la marca desapareció) sin tocar nada. **OJO al publicar la 1.0.3:** las pantallas abiertas del publicado corren la 1.0.2 (poll de 30 s) → esa transición puede demorar hasta ~1 min en recargarse; desde la 1.0.3 en adelante, segundos.

- **2026-07-23 (39) — CARPETA DEFINITIVA `C:\TIZADAPRO`: el instalador se MUDA solo y libera todas las carpetas viejas.** El usuario intentó borrar la carpeta EN USO (Windows lo salvó) y pidió «una carpeta que se llame diferente y que al ejecutarla me deje borrar todas las demás». **Nuevo flujo en `instalar_servidor.py`:** constante `DESTINO=C:\TIZADAPRO`; si el instalador corre desde cualquier otra carpeta, `copiar_codigo`→DESTINO + **`migrar_datos`** (datos/, entrada/, trabajos/, perfiles_icc/ y `config_publicado.bat` con las claves, DESDE la carpeta del server VIVO detectado con `servidor_vivo()`) y se re-lanza allá (`--en-destino`). El puerto vuelve a ser SIEMPRE 8050 (nginx); el server viejo lo baja el `_liberar_puerto` del arranque nuevo. `arrancar()` ahora espera a que `/api/salud` conteste **desde la carpeta definitiva** (no alcanza con el puerto tomado: podía ser el viejo agonizando). `escribir_config` NO arrastra `TIZADA_DATOS/ENTRADA/TRABAJOS` si apuntan adentro de una instalación vieja (dejaría el sistema atado a la carpeta que se quiere borrar). Al final imprime **`carpetas_viejas()`**: la lista con nombre y apellido de lo que YA se puede borrar. **VERIFICADO** (`scratchpad/verif_mudanza.py`, reproduce el caso real: server 1.0.0 vivo en «TIZADA PRO - COPIAR AL SERVIDOR» + instalador nuevo descomprimido en cualquier lado): atiende 1.0.1 desde la DEFINITIVA, molde migrado, clave de sesión conservada (`SECRETO_VIEJO_123`), clave de actualización puesta y la carpeta vieja **borrable**. GOTCHA de la prueba: el primer armado copiaba 4 archivos sueltos → faltaba `servidor.py` en el destino y el server moría sin log; el fixture correcto es extraer el ZIP REAL entero. Escritorio: quedó UN solo zip, **`INSTALAR-TIZADAPRO.zip`** (se borraron los dos viejos que confundían).

- **2026-07-23 (38) — El instalador AHORA SE UBICA SOLO: mata el lío de carpetas duplicadas.** Diagnóstico del enredo del usuario (dos carpetas, no podía borrar una, `/admin` no mostraba nada): el instalador viejo elegía un puerto LIBRE → al correrlo en la carpeta equivocada, como el 8050 estaba tomado por el server bueno, **levantó un segundo server en el 8051 desde la carpeta mala** (por eso no se podía borrar) y **le robó la tarea de arranque**; nginx seguía en 8050 (viejo). **Fix en `instalar_servidor.py`:** `servidor_vivo()` busca un TIZADA PRO ya andando (escanea 8050-8059, `/api/salud`) y toma **su carpeta y su puerto** (el 8050=nginx manda); si el instalador se ejecutó en OTRA carpeta, **`copiar_codigo` mete la actualización en la carpeta viva y se re-lanza allá** (`--ya-en-sitio`), sin crear nada nuevo; **`cerrar_duplicados` baja los servers colados en otros puertos → la carpeta duplicada queda BORRABLE**; `crear_tarea` re-apunta la tarea a la carpeta buena. Se eliminó el `puerto += 1` (la causa). **`copiar_codigo` conserva `datos/`+`entrada/`+`config_publicado.bat`** (sólo copia el programa; ojo: `VERSION` no tiene extensión, se copia aparte). **La clave de actualización ahora viaja SIEMPRE en el paquete** (antes sólo en `--completo`) — clave porque el server publicado se instaló ANTES de que existiera y no la tenía. **VERIFICADO** (`scratchpad/verif_autoubicar.py`, reproduce el lío con DOS servers reales —buena 1.0.0 + colada 1.0.1— y corre el instalador desde una TERCERA carpeta): actualiza la BUENA a 1.0.1, le pone la clave y **el dato del usuario queda intacto**. Paquete nuevo en el Escritorio (`ACTUALIZAR SERVIDOR`, 1.3 MB).

- **2026-07-23 (37) — Publicación: se puede programar a CUALQUIER momento; y la barra muestra la VERSIÓN del sistema, no el molde activo.** Pedidos del usuario. **(1) Cuándo se instala:** antes eran dos opciones (03:00 o ahora). Ahora hay **tres formas**: atajos (`ahora · 15 seg · 30 seg · 1 min · 5 · 15 · 30 min · 1 h · 3 h · 10 h`), **«en X segundos/minutos/horas/días»** con el número a mano, y **día y hora exactos** (`el 25/7/2026 a las 8:00`). Debajo se lee siempre en castellano qué se eligió: «Se instala el jueves 24/7 a las 03:00 — en 4 h 12 min», y avisa si la fecha ya pasó. El backend no cambió (siempre recibió una marca de tiempo); sí se bajó el vigilante de **20 s a 5 s** para que «en 15 segundos» sea de verdad 15 segundos. **(2) Barra superior:** se sacó «Servidor Activo» + «Activo: Molde 1» y ahora dice **«TIZADA PRO 1.0.1»** (versión del servidor que te atiende, del `/api/salud`), con **«EN INTERNET»** debajo si estás en el publicado, y la revisión de git en el tooltip. Con dos ambientes, saber **qué versión tenés delante** importa más que qué molde está activo (que ya se ve en su pantalla). Verificado: compila, `/api/salud` da los datos y la app carga **sin errores de consola**; el aspecto exacto de la barra no se pudo mirar (hay login).

- **2026-07-23 (36) — RESPALDO: el proyecto ya está en GitHub.** Repositorio **privado** `https://github.com/UserBreus/tizada-pro.git` (lo creó el usuario; crear repos necesita permisos que el agente no tiene, subir sí —las credenciales de la máquina funcionan vía Git Credential Manager—). Subidos **162 commits y 66 archivos**: todo el historial, el código, el MAPA y los planes. **NO se subió nada privado** (verificado uno por uno): `datos/`, `entrada/`, `config_publicado.bat` (lleva la clave de sesión), `datos/publicacion.json` (lleva la clave de actualización) ni los logs — el `.gitignore` se amplió con `scratchpad/`, `dist/`, los generados del servidor y `perfiles_icc/`. **Motivo real, no teórico:** el 2026-07-23 desapareció de la carpeta `PROYECTO AVANZADO 1-0-0.rar` y **se pudo recuperar sólo porque estaba en el historial de git**; hasta hoy el proyecto vivía en UNA sola máquina.

- **2026-07-23 (35) — Etapa 2 COMPLETA: pantalla **Config → Publicación** + el botón verificado.** Nuevo componente **`PantallaPublicacion`**: compara **versión de acá vs publicada**, muestra si hay una actualización esperando (con los minutos que faltan) y el resultado de la última, deja elegir **«esta madrugada (03:00)» / «ahora mismo» / una hora a mano** y publica con un botón; también **cancela** una programada. Si el servidor publicado corre una versión vieja **sin el receptor**, en vez de un «404» pelado explica que falta una última instalación a mano (`sin_receptor` en `/api/publicacion/estado`). **DOS BUGS REALES encontrados al probar el botón:** (1) **Cloudflare devuelve 403 al `User-Agent` de Python** (`Python-urllib/3.x`, lo toma por bot) → **publicar habría fallado SIEMPRE** con un error incomprensible; verificado con `curl` que con cualquier otro agente da 200 → se manda `User-Agent: TIZADAPRO-publicador/1.0` en las tres llamadas. (2) **`sys` no estaba importado en `servidor.py`** y `publicacion_publicar` usa `sys.executable` → 502 al publicar. **VERIFICADO** (`scratchpad/verif_boton_publicar.py`, contra un servidor publicado de prueba en el 8062 y **con la clave real del taller**): el botón **arma el paquete (1,28 MB), lo sube y queda programado** (versión 1.0.1, faltan 30 min) y el botón de cancelar lo borra. Paquete final en el Escritorio: **1.0.1, 167 archivos**, con `actualizaciones.py`, `actualizador.py` y la clave adentro. **Falta sólo la ÚLTIMA instalación a mano** para que el servidor tenga el receptor.
- **2026-07-23 (34) — Etapa 2 (actualizaciones): MOTOR HECHO Y VERIFICADO DE PUNTA A PUNTA. Falta la PANTALLA.** Nuevos: **`actualizaciones.py`** (receptor: `token_ok` con `hmac.compare_digest`, `guardar` que verifica sha256 + que el zip abra + que traiga los archivos imprescindibles + lee la versión de adentro, `aplicar` que lanza al ayudante DESPRENDIDO —`DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP`, si fuera hijo se lo llevaría puesto el apagado—, `vigilar` que dispara a la hora, `recuperar_si_quedo_a_medias`) y **`actualizador.py`** (el ayudante: espera que se libere el puerto, **respalda sólo el código**, descomprime, arranca por la tarea —o por `arrancar.bat` si la tarea no está— y **exige `/api/salud` OK; si no, restaura y vuelve a la anterior**). Endpoints en el servidor: `GET /api/actualizacion/estado` (público, es el que alimenta la cuenta regresiva) y `subir`/`aplicar`/`cancelar` (con clave). En el TALLER: `GET /api/publicacion/estado` y `POST /api/publicacion/publicar` (arma el paquete con `empaquetar.py` y lo sube con `X-Token-Act`/`X-Sha256`/`X-Cuando`). **La clave viaja DENTRO del paquete de instalación** (`empaquetar.py --completo` la genera en `datos/publicacion.json` y la mete como `token_actualizacion.txt`; el instalador la deja en `config_publicado.bat`) → **cero copiar y pegar**, que era el pedido. Front: **`AvisoActualizacion`**, cinta fija arriba con el contador `mm:ss` (consulta cada 30 s, el reloj lo baja localmente), pasa a «Actualizando…» y **recarga sola** cuando el servidor vuelve con otra versión. **VERIFICADO de punta a punta** (`scratchpad/verif_actualizacion.py`, con un servidor publicado FALSO en otra carpeta, versión 1.0.0 → 1.0.1): la subida queda **pendiente con su cuenta regresiva** (3599 s); **sin clave → 401**; **paquete alterado → rechazado**; al aplicar, el ayudante respaldó, descomprimió y **el servidor volvió solo en ~20 s con 1.0.1 y salud OK**; `ultima.json` = «actualizado y verificado»; **el archivo de prueba en `datos/` quedó intacto**; la pendiente se limpió y quedó el respaldo. **BUG encontrado y arreglado en las pruebas:** `call config_publicado.bat` (sin ruta) **no encuentra el archivo** si el entorno tiene `NoDefaultCurrentDirectoryInExePath` → el servidor arrancaba **sin su configuración** (sin puerto ni clave). Ahora `call "%~dp0config_publicado.bat"`. **INCIDENTE (mío) en las pruebas:** por ese mismo bug, un servidor de prueba arrancó sin `PORT` → tomó el **8050** y su `_liberar_puerto` **mató el servidor local del usuario**, quedando servido desde una carpeta de prueba (salud en rojo). Detectado por `/api/salud` y **restaurado**; el local volvió a 1.0.1 con los 5 chequeos verdes. **Lección: los servidores de prueba SIEMPRE con `PORT` explícito y verificando que quedó tomado el puerto correcto.** **FALTA:** la pantalla Config → Publicación (botón, hora, estado) — los endpoints ya están, la UI no.
- **2026-07-23 (33) — «Unexpected token '<', "<!DOCTYPE"… is not valid JSON» = el servidor estaba CAÍDO. Ahora corre como SERVICIO de verdad.** El usuario mostró ese cartel rojo. **Diagnóstico desde afuera:** la raíz del dominio 200 (stock intacto) pero **`/Tizadapro/` daba 502** → nginx no encontraba a la app → **el proceso no estaba corriendo**. Con la app caída, nginx contesta su **página HTML de error** a TODAS las llamadas, el front hace `JSON.parse` de ese HTML y sale exactamente ese mensaje. **Causa: se cerró la ventana negra donde corría** — y encima se la había dado por cerrable en una respuesta anterior (error mío). **Causa RAÍZ real:** la tarea era `schtasks /sc onstart`, o sea **sólo arranca al prender el servidor**: si el proceso muere, nadie lo levanta. **Fix — la tarea pasa a definirse por XML** (`schtasks /create /xml`), que es la única forma de pedir las tres cosas que la convierten en un servicio: **`Hidden` + cuenta SYSTEM** (no hay ventana que cerrar), **`TimeTrigger` con `Repetition PT5M` + `MultipleInstancesPolicy=IgnoreNew`** (vigilancia: si se cayó vuelve en <5 min; si está andando no hace nada) y **`RestartOnFailure` + `ExecutionTimeLimit PT0S`** (si no, Windows lo mata a los 3 días). Además `arrancar()` ahora lo levanta **por la tarea** (`schtasks /run`), no como ventana suelta → desde el minuto cero queda igual que después de un reinicio; y `arrancar.bat` manda la salida a **`servidor_log.txt`** (corriendo sin ventana, es el único lugar donde mirar). Verificado: el XML **parsea** y contiene `Hidden`/`PT5M`/`IgnoreNew`/`BootTrigger`. **Pendiente del usuario:** correr el instalador una vez más (el servicio se crea ahí; hasta entonces el sistema sigue caído porque la tarea vieja sólo dispara al reiniciar).
- **2026-07-23 (32) — AUDITORÍA del SQL: qué toca el instalador y qué NO (el usuario avisó que ese SQL Server lo usan otros proyectos, entre ellos el de stock).** **Auditado con `grep`, no de palabra:** `db/schema.sql` tiene **0 sentencias destructivas** (los `ON DELETE CASCADE` que aparecen son definiciones de claves foráneas ENTRE NUESTRAS PROPIAS tablas, no borrados); las **únicas** dos veces que se sale de nuestra base es en `db.existe_base()`/`crear_base()`, que se conectan a `master` sólo para `SELECT DB_ID(?)` y, si no existe, `CREATE DATABASE [TizadaPro]`. Ningún `USE`, `DROP` ni `TRUNCATE` en todo el código. Las 26 tablas que crea el esquema son propias (`producto`, `pieza`, `usuario`, `rol`…). **SEGURO NUEVO en `preparar_base`:** si la base `TizadaPro` **ya existiera** y tuviera **tablas ajenas** (o sea, es de otro sistema), **corta sin escribir una sola línea** y explica que hay que usar otro nombre (`TIZADA_DB_NAME`). La lista de tablas propias sale de **leer `schema.sql`** (`_tablas_del_schema`), no está escrita a mano → si el esquema cambia, el seguro sigue siendo correcto. Probado: 26 tablas propias detectadas y tablas tipo `articulos`/`depositos`/`movimientos_stock` se marcarían como ajenas. Además el paso imprime, antes de tocar nada, que trabaja **sólo** sobre `TizadaPro` y que ninguna otra base se toca ni se lee.
- **2026-07-23 (31) — El servidor YA tiene SQL Server 2022 (instancia por defecto) + permiso para la cuenta del servicio.** El usuario avisó que **usa SQL Server 2022 para otras cosas** (captura de SSMS 20 + Configuration Manager) → la instancia es la **predeterminada** (`localhost`), no `SQLEXPRESS`; el `preparar_base` ya la prueba en 2º lugar. **Problema que se venía y se atajó antes de que muerda:** al instalar, todo corre como **Administrador** (que en SQL suele ser sysadmin) y anda; pero cuando el servidor se REINICIA, TIZADA PRO arranca como **`NT AUTHORITY\SYSTEM`** (tarea programada `/ru SYSTEM`) y esa cuenta normalmente **no tiene login en SQL** → «login failed» y **nadie podría iniciar sesión después de un reinicio**. **Fix `_permiso_al_servicio`:** crea el login de `NT AUTHORITY\SYSTEM` si falta y le da `db_owner` **SOLO sobre la base `TizadaPro`** — no toca ninguna otra base del servidor (ahí vive el sistema de stock del usuario); si falla, avisa con la explicación y sigue. **Verificado:** las 3 sentencias validadas con **`SET PARSEONLY ON`** contra un SQL Server 2022 real (**sin ejecutar nada**, para no tocar la base local del usuario). Paquete rearmado en el Escritorio.
- **2026-07-23 (30) — ✅ TIZADA PRO ESTÁ PUBLICADO Y ANDANDO EN INTERNET.** `https://administracionuser.uy/Tizadapro/` sirve la app (`<title>USER PRO · Motor de Sublimación</title>`, assets con el prefijo correcto) y `/Tizadapro/api/salud` responde **`ok:true`, modo `publicado`, 2 procesos de render**, con Ghostscript 10.01.2, **24 perfiles ICC (SWOP v2)**, datos escribibles y frontend OK. **El sistema de stock del usuario quedó intacto** (200, su `<title>` de siempre). El log de la corrida real confirmó que el `descargar()` de 3 caminos salvó a Ghostscript (**«descarga directa no anduvo … OK instalado»** — cayó al de PowerShell) y que nginx se configuró solo (`C:\nginx-1.27.3\conf\nginx.conf`, con respaldo `.antes-de-tizada`). **Servidor:** Windows Server 2022 (10.0.20348), **634 MB libres** (menos del 1 GB estimado) → con `TIZADA_PROCESOS=2` el pico calculado (~600 MB) queda **justo**; si se pone lento o falla al generar, bajar a 1. **LO QUE FALTABA para poder USARLO:** el chequeo `base` daba MAL (`28000`, login) → **sin base de usuarios no se puede iniciar sesión** (usuarios/roles es lo único que hoy vive en MSSQL; el resto son archivos). **Agregado al instalador el paso «Base de datos de usuarios»** (`preparar_base`): prueba varios SQL Server (`TIZADA_DB_SERVER`, `localhost\SQLEXPRESS`, `localhost`, `.\SQLEXPRESS`, `(local)`), **crea la base `TizadaPro`, aplica `db/schema.sql`, corre `auth.bootstrap()`** y **muestra el usuario `admin` con su contraseña generada** (una sola vez, y queda en `instalacion_log.txt`); anota `TIZADA_DB_SERVER` en `config_publicado.bat` para los próximos arranques. Todo idempotente; si no hay SQL Server avisa y el resto sigue andando. Paquete rearmado en el Escritorio.
- **2026-07-23 (29) — DOS BUGS REALES del instalador, encontrados con la corrida en el servidor del usuario.** El usuario mandó la captura de la ventana: el instalador **sí corrió elevado**, encontró Python e instaló las dependencias, y después falló. **(1) `CERTIFICATE_VERIFY_FAILED` al bajar Ghostscript:** un Windows Server recién hecho **no tiene los certificados raíz cacheados** (nunca navegó) → `urllib` no valida y la descarga muere. **Fix:** helper **`descargar(url, destino)`** con TRES caminos — `urllib` (con `certifi` si está) → **PowerShell `Invoke-WebRequest`** → **`curl.exe`**; los dos últimos usan el almacén de certificados de Windows, que sí sabe traerlos solo. Probado de verdad (bajó un archivo real). **(2) `PermissionError WinError 32` copiando los perfiles ICC:** `instalar_perfiles(AQUI)` copiaba `AQUI/perfiles_icc` **sobre sí misma** (el paquete ya los trae ahí) → «el proceso no puede acceder al archivo» y **se cayó toda la instalación**. **Fix:** si origen y destino son la misma carpeta, no se copia nada (ya están en su lugar). Probado reproduciendo el caso exacto del servidor (perfiles en el paquete + sin perfiles de Adobe instalados). **Además:** Ghostscript pasó a **NO bloqueante** — sólo se usa para unificar el modo de color cuando la hoja trae RGB; con arte CMYK (lo normal) la tizada sale igual. El instalador avisa y sigue, y `/api/salud` lo reporta sin marcar falla (`critico=False`). **Y `DIAGNOSTICO.bat`** (nuevo, batch puro — no necesita Python): mira Windows, memoria, Python, qué archivos hay, si el puerto 8050 escucha, la tarea programada, nginx y **pega el `instalacion_log.txt` entero**, guarda todo en `DIAGNOSTICO.txt` y **lo abre en el Bloc de notas** para copiar y pegar (el usuario no puede mandar imágenes). Paquete rearmado (163 archivos) y dejado en el Escritorio.
- **2026-07-23 (28) — El instalador se corta solo: ahora se AUTOELEVA, instala Python si falta y deja LOG.** El usuario probó y contó: «me abrió una ventana negra, me decía "presione [una tecla]" y se cerró». **Diagnóstico SIN pedirle nada** (esto es lo reutilizable): se chequeó el servidor **desde afuera** — `https://administracionuser.uy/` responde 200 (**su sistema de stock intacto**) y `https://administracionuser.uy/Tizadapro/api/salud` devuelve **el `index.html` del portal de stock**, no nuestro JSON → el `location` de nginx **no se creó** → la instalación **no llegó a correr**. Las dos causas posibles eran (a) el servidor no tiene Python (el `.bat` avisaba y salía) o (b) se hizo doble clic sin «ejecutar como administrador» (el script salía con ese mensaje); las dos terminan en el `pause` = «presione una tecla». **ARREGLADO las dos de raíz:** (1) `INSTALAR.bat` **se autoeleva** (`Start-Process -Verb RunAs`) → alcanza con doble clic, Windows pide confirmación; (2) si no hay Python, **lo descarga de python.org y lo instala en silencio** (`/quiet InstallAllUsers=1 PrependPath=1`) y sigue solo, y si no hay internet lo dice claro; (3) **`instalacion_log.txt`**: `instalar_servidor.py` duplica TODA su salida a un archivo (clase `_Tee`, tolerante a la consola cp1252) y cualquier excepción inesperada se imprime completa + `pause` → **la ventana ya no se cierra sin dejar rastro**. Verificado con `cmd /c INSTALAR.bat --simular`: encuentra Python, corre los pasos y escribe el log. Paquete rearmado y dejado en el **Escritorio del usuario** como `TIZADA PRO - COPIAR AL SERVIDOR.zip`.
- **2026-07-22 (27) — INSTALADOR AUTOMÁTICO (`INSTALAR.bat` + `instalar_servidor.py`) + paquete `--completo`.** El usuario fue claro: **«no quiero hacer todo eso, no sé ni quiero aprenderlo ahora, deberías de hacerlo vos»**. **LÍMITE REAL, dicho de frente:** no hay forma de que yo entre a ese servidor — se verificó que **no hay AWS CLI, ni credenciales `~/.aws`, ni Systems Manager, ni claves SSH**; lo único es un acceso de **Escritorio remoto** guardado (`Default.rdp` → `ec2-3-85-26-173.compute-1.amazonaws.com`) que pide contraseña, y yo **no manejo contraseñas ni puedo manejar una ventana de RDP** (los tools de navegador manejan páginas web, no el escritorio de Windows). Entonces se hizo lo único que sí resuelve el problema: **dejar su parte en 3 gestos** (arrastrar 1 archivo por el RDP que ya tiene en la barra, descomprimir, clic derecho → ejecutar como administrador). **`empaquetar.py --completo`** arma un zip de **25 MB / 162 archivos** con el código, el frontend compilado para `/Tizadapro`, **los perfiles ICC de esta máquina** (sin ellos el color del servidor sale distinto) y `datos/`+`entrada/` (sin `piezas_cache`, que se regenera). **`instalar_servidor.py`** hace todo solo: Python + dependencias, Ghostscript (descarga oficial de Artifex si falta), perfiles apuntados, **clave de sesión generada**, puerto libre, `config_publicado.bat`, tarea de arranque automático (`schtasks /sc onstart`), levanta el server, **inserta el bloque en el nginx** y muestra el chequeo de salud; modos `--simular` y `--sin-nginx`. **El nginx se toca con red:** respaldo previo (`.antes-de-tizada`), `nginx -t` y **si no valida se restaura el original**; busca el `server{}` en `nginx.conf` **y en sus `include`**; si no lo encuentra **no toca nada** y avisa. **VERIFICADO acá:** el instalador corre de punta a punta en `--simular` **desde el paquete ya extraído**, y la inserción en nginx probada contra un conf de ejemplo → queda **dentro del `server{}`, ANTES del catch-all**, no pisa lo existente, **no duplica** si se corre dos veces y devuelve None si no hay dónde. **Gotcha arreglado:** `empaquetar.py` compila el frontend con base `/Tizadapro/` y eso **pisaba `frontend/dist`** → el server local quedaba pidiendo sus archivos a `/Tizadapro/` y **la app del taller no abría**; ahora recompila el build del taller al terminar (pasó de verdad, se detectó y se corrigió). **Gotcha (ya conocido, volvió a morder):** un `→` en un `print()` **rompe** en la consola cp1252 de Windows — nada de flechas ni símbolos en los `print`. **NO verificado (imposible sin el servidor):** la instalación real de Python/Ghostscript y el `nginx -s reload` de verdad.
- **2026-07-22 (26) — Cómo se lleva al servidor (`empaquetar.py`) + CUÁNTA MEMORIA necesita (MEDIDO) + `TIZADA_PROCESOS`.** El usuario preguntó cómo subir el proyecto y avisó que **al servidor le queda 1 GB libre**. **MEDIDO** (`scratchpad/medir_memoria.py`, pico real por API de Windows, no estimación): Python + servidor importado **130 MB**; 1 talle **en frío** **170 MB**; **tizada completa** (con aplanado RIP) **194 MB**; el molde grande (19 pzs × 19 talles) **171 MB** → **el consumo NO depende de la cantidad de piezas**, un proceso de render ≈ **200 MB**. **El riesgo real era el paralelismo:** el pool usaba `min(núcleos, 6)` = **~1,2 GB solo en workers** → con 1 GB libre se quedaba sin memoria. **NUEVO `TIZADA_PROCESOS`** (`servidor.procesos_render()`, usado por `_get_render_pool`, y el pool de `aplanar_rip.py`): acota los procesos; sin la variable **todo sigue igual que siempre** (verificado: sin var → 6, `=2` → 2, `=0` → vuelve al automático). `/api/salud` informa `procesos_render`. Con `TIZADA_PROCESOS=2` el pico es ~600 MB → **entra en 1 GB para 1–3 personas**; si queda corto: `=1`, o subir la instancia un escalón, o una máquina aparte. **`empaquetar.py`** (nuevo): compila el frontend y arma `dist/TIZADAPRO_<v>_<commit>.zip` = **1,2 MB, 38 archivos** (código + frontend ya compilado para `/Tizadapro` + `db/schema.sql` + las 7 tipografías), con **lista blanca** (no se cuela un .rar de 300 MB) y una **guarda dura**: si el index no quedó apuntando al prefijo, corta. **No** compilar en el servidor: `npm install`+`vite build` pide **más de 1 GB de RAM**, justo lo que falta. Los datos (`datos/`, `entrada/`, ~60 MB) van **aparte y una sola vez** → actualizar no puede pisarlos. El repo **no tiene remoto** hoy; el `.gitignore` ya deja afuera datos/entrada/trabajos/node_modules/dist/respaldos (incluidos los 360 MB de `respaldo_moldes_*`). Guía completa en `PLAN_PUBLICACION.md` («CÓMO SE LLEVA EL PROYECTO AL SERVIDOR» y «CUÁNTA MEMORIA NECESITA»). El `dist` quedó recompilado al build del TALLER y el server del usuario (8050) OK.
- **2026-07-22 (25) — HECHA la Etapa 1.a: la app puede vivir en una SUB-RUTA (`/Tizadapro`) del dominio que el usuario ya tiene.** Ver `PLAN_PUBLICACION.md` §3.bis y §Etapa 1.a. **Infra relevada** (proyecto `C:\Users\user2\Documents\tincho\stock`, «stock-wms», repo `UserBreus/stock-amazon`): dominio **`administracionuser.uy`** → **Cloudflare** → **EC2 `3.85.26.173`** con **nginx 1.27.3**, que sirve el SPA del stock en `/` y su API SQL en el puerto 5005; quedó un `.vercel/` viejo pero **hoy el dominio lo sirve el EC2** (mismo HTML byte a byte). **El EC2 es WINDOWS** (lo confirmó el usuario) → TIZADA PRO corre ahí nativo, sin riesgo de color y sin máquina extra. **CAMBIOS:** `vite.config.js` con `base` configurable + script **`npm run build:publicado`** (`vite build --base=/Tizadapro/`); nuevo **`frontend/src/base.js`** (importado PRIMERO en `main.jsx`) que **envuelve `fetch` una sola vez** y prefija las rutas propias (`/api/…`, `/trabajos/…`, `/logo.svg`) → las **125 llamadas absolutas quedan escritas igual** y ninguna futura se olvida del prefijo; exporta `rutaApi()` y `esRutaAdmin()`. En `App.jsx`: las 3 `location.pathname === '/admin'` → `esRutaAdmin()`, y **11 URLs que NO pasan por fetch** prefijadas con `rutaApi()` (descargas `<a href>`, `<img src>`, `window.open`, el `@font-face` del CSS, los 3 `<img src="/logo.svg">`). **GOTCHA caro:** desde Git Bash `TIZADA_BASE=/Tizadapro/ npm run build` **no sirve** — MSYS convierte el valor a `/Program Files/Git/Tizadapro/` (salió en el index.html); por eso el prefijo va dentro del script de `package.json`. **VERIFICADO de punta a punta** con `scratchpad/proxy_subruta.py` (imita el `location` de nginx: `/Tizadapro/*` → `127.0.0.1:8060/*`) + el server en modo publicado: la app **carga en el navegador sin un solo error de consola** y las ~20 llamadas salen **todas con el prefijo** y en 200 (incluido `/Tizadapro/logo.svg`, que fue el único 404 de la primera pasada y se arregló); **sin** prefijo `/api/salud` da 404 → no pisa nada de lo que vive en la raíz del dominio. El `dist` quedó **recompilado al build del TALLER** (el de la sub-ruta es sólo para publicar) y el server del usuario en 8050 sigue OK. **NO hecho (depende del servidor, no tengo acceso):** instalar en el EC2 (Python, Ghostscript, **copiar los `.icc` de Adobe** o `TIZADA_PERFILES` — sin eso el color cambia), agregar el `location /Tizadapro/` al nginx (el bloque está escrito en el plan) y el backup diario. Ver [[publicacion-internet]].
- **2026-07-22 (24) — HECHA la Etapa 0 de la publicación: el programa ya corre fuera de esta máquina.** Ver `PLAN_PUBLICACION.md` §Etapa 0. **`TIZADA_MODO`** = `taller` (default — `py servidor.py` se comporta EXACTAMENTE igual que antes) o `publicado`. En publicado: **`TIZADA_SECRET` obligatorio** (si falta NO arranca y dice cómo generarla; antes se generaba al azar y cada reinicio deslogueaba a todos), `SESSION_COOKIE_SECURE` prendida (`TIZADA_HTTPS=0` para probar sin certificado), **ProxyFix** (`X-Forwarded-*` del proxy que termina el HTTPS) y **waitress** en vez de `make_server` con `TIZADA_HILOS` (8) — si waitress no está, **corta con mensaje** en vez de caer al servidor de desarrollo. Nuevo **`GET /api/salud`** (SIN sesión a propósito): `{ok, fallas, modo, version, commit, uptime_s, chequeos:{ghostscript, perfiles_icc, datos_escribible, base, frontend}}` y **503** si algo crítico falla → es el semáforo del actualizador de la Etapa 2 (y de paso dice al toque por qué una máquina nueva no genera igual: casi siempre Ghostscript o los perfiles ICC). Archivo **`VERSION`** (`1.0.0`) + commit corto = lo que se compara taller↔publicado. **`publicado.bat`** con las variables a completar + la línea de `schtasks` para que arranque solo. **`requirements.txt`**: se agregaron `pillow`, `ezdxf`, `pyodbc`, `waitress` — **el código ya los usaba y no estaban listados**, una máquina limpia no levantaba. **VERIFICADO:** (a) publicado sin `TIZADA_SECRET` → se niega a arrancar; (b) con clave, waitress levanta en 8060 contra una **COPIA** de `datos/`+`entrada/` (nunca se tocaron los reales) y `/api/salud` da `ok:true` con los 5 chequeos verdes (Ghostscript 10.01.2, 33 perfiles, SWOP v2); (c) **misma pieza renderizada contra la copia vs contra los datos reales = 0 px** (`scratchpad/verif_pub_render.py`); (d) el server del taller (8050) sigue igual, `/api/salud` `modo:"taller"`. **NO verificado (imposible acá):** que OTRA máquina dé el mismo píxel — eso es la Etapa 1, cuando exista el VPS. Ver [[publicacion-internet]].
- **2026-07-22 (23) — PLANIFICADO (nada codeado): versión PUBLICADA en internet + circuito de actualización → `PLAN_PUBLICACION.md`.** El usuario pidió «una opción que se pueda levantar desde internet, usarlo y guardar cosas, pero que las actualizaciones que yo haga se hagan desde otro apartado y después programar la actualización». Respondió: se actualizan **las dos cosas** (código Y moldes/artes), entran **sólo él y su gente** (no hay clientes externos todavía → sin multi-tenant), y el flujo es «seguimos trabajando como hasta ahora y cuando tengamos mejoras habilitar la actualización». **Decisión tomada por mí (él no eligió lugar): VPS Windows**, porque el color depende de cosas instaladas en Windows y la LEY es arte=tizada con CMYK exacto — perfiles ICC de Adobe (`servidor.py:42-48`), Ghostscript `gswin64c.exe` (`servidor.py:326`) y MSSQL nativo; Linux queda para cuando entren clientes externos y haya que reverificar el color. **Hallazgo útil:** la app **NO está clavada a esta máquina** — `ENTRADA/FUENTES/TRABAJOS/DATOS` ya salen de env (`servidor.py:17-20`), igual que `TIZADA_SECRET`, `TIZADA_PERFILES` y `TIZADA_GS`. **Etapas** (cada una usable sola): **0** sacar ataduras (cookies seguras con HTTPS, `TIZADA_SECRET` obligatorio —hoy si falta se genera al azar y cada reinicio desloguea a todos—, waitress en vez de `make_server`, servicio de Windows, nuevo **`GET /api/salud`**); **1** servidor publicado (VPS+dominio+HTTPS+**backup diario, que hoy no existe**) → con esto ya cumple lo primero que pidió; **2** pantalla **Config → Publicación** que publica la VERSIÓN con un botón (empaquetar → bajar → recompilar front → reiniciar → chequear `/api/salud` → **rollback solo si falla**) y permite **programarla** (ej. 3 AM, con aviso y bloqueo de generación ~2 min); **3** publicar MOLDES/ARTES (diff nuevo/modificado/igual, respaldo antes de pisar, y el setup en publicado pasa a SÓLO LECTURA porque los datos viajan **taller→publicado, nunca al revés**); **4** operación (mantenimiento, log de publicaciones, alertas, limpieza de cachés). **DEPENDENCIA:** la etapa 3 cambia mucho según `PLAN_MSSQL.md` — con archivos es copiar, con MSSQL es sincronizar dos bases → decidir el orden antes de codearla. **RIESGO principal:** mudar el color; antes de dar por buena la etapa 1 hay que generar la MISMA tizada acá y allá y compararlas píxel a píxel. **RECORDATORIO:** hoy **ningún endpoint valida permisos** — tolerable con gente de confianza, bloqueante antes de exponerlo a un cliente. Ver [[publicacion-internet]].

- **2026-07-22 (22) — Campos C/M/Y/K del selector: entran 4 dígitos, la coma se ve y NO tienen flechitas.** Pedido del usuario sobre la captura («0 · 94 · 94 · 41,» — el decimal quedaba cortado). Nuevo componente **`CampoNum`** (arriba de `ColorPickerModal`): `type="text"` + `inputMode="decimal"` → **sin spinners** (el `type=number` los traía), ancho 62 px y texto centrado (entra «100,0»), coma decimal aceptada y mostrada, y **mantiene el texto tal cual se tipea mientras está enfocado** — si se reformateara en cada tecla, escribir «41,» volvería a «41» y no se podría poner el decimal; al salir del campo se re-formatea desde el valor. Lo usan los 4 campos CMYK y también las filas H/S/B y R/G/B del selector (todo el selector pasó a ser sólo-escritura). **VERIFICADO** con `react-dom/server` sobre una copia literal del componente (`scratchpad/verif_campo_num.mjs`): sale `type="text"` (0 `type="number"`), valores `0 · 94 · 94,1 · 41,2` con la coma visible y 62 px cada uno. `npm run build` OK (frontend puro, sin reiniciar el server).
- **2026-07-22 (21) — FIX: el color de la pantalla no coincidía con Illustrator (no era redondeo: era la conversión CMYK→RGB sin perfil).** El usuario mandó las dos capturas: nuestro selector mostraba **#0bd913** (verde flúor) para CMYK 95/0/91/15 y el panel Color de Illustrator, **#009550**. **Causa:** todo el front pintaba los swatches con la fórmula ingenua `R=255·(1-C)·(1-K)`, que **ignora el perfil ICC**. Los números CMYK estaban bien (Illustrator mostraba 94,9/0/91,2/14,9 = lo mismo con su propio redondeo); lo falso era el color en pantalla. **Backend:** `_cms_tr(sentido)` (transformada ICC cacheada entre el perfil CMYK configurado —`_perfil_default_cfg`, default U.S. Web Coated (SWOP) v2— y sRGB) + **`POST /api/color/convertir`** (`{cmyk:[[c,m,y,k],…]}`→`{rgb,hex}` y `{rgb:[[r,g,b],…]}`→`{cmyk}`, en LOTE; sin perfil cae a la fórmula simple). **Intent PERCEPTUAL (0)** — se probaron los 4: el 0 (y el 2) dan **#009550 exacto**, el relativo (1) daba #00985a. **Frontend** (`App.jsx`): helper global `cmykHex(cmyk)` con **caché en memoria + pedido en lote (debounce 60 ms) + suscripción** (`useIcc()`, llamado en `App` y en `ColorPickerModal`) → devuelve el aproximado mientras no llegó la respuesta y re-renderiza con el real. Lo usan **todos** los swatches CMYK: el selector (muestra grande, HEX y R/G/B), el panel COLOR del editable + los chips de figura, y los de etiqueta/borde de corte. El cuadro de saturación/tono sigue siendo el espacio de SELECCIÓN (RGB puro: ahí se elige); lo que se ve abajo es cómo sale de verdad. Tipear un RGB/HEX ahora pide al perfil el CMYK que reproduce ese color (como Illustrator). Los campos C/M/Y/K pasaron a **1 decimal** (`step=0.1`): redondear a entero cambiaba el color al re-guardarlo. **VERIFICADO en vivo** (server reiniciado por PID 27976 → nuevo): `POST /api/color/convertir` con `[.95,0,.91,.15]` → **#009550** (idéntico a la captura de Illustrator); K100 → `#231f20` y C75 → `#00bdf2`, que son **exactamente** los colores con los que PyMuPDF dibuja el SVG del arte → el swatch de la app y el dibujo del objeto ahora coinciden. `npm run build` OK. **Ojo:** el ida-y-vuelta RGB→CMYK→RGB por ICC **no es estable** (#009550 → cmyk → #15904e), por eso el arrastre en el cuadro sigue usando la conversión simple: si no, el color se iría corriendo solo. **NO verificado:** la pantalla a mano (login).
- **2026-07-22 (20) — FIX: el color cambiado NO se veía en el editor (el dibujo salía del arte crudo).** El usuario, después de (19): «ahora abre el modal pero no se ve reflejado el cambio de color en los objetos». **Causa:** el editor dibuja cada objeto con `o.svg` (y la lista con `o.thumb`), que salen de `extraer_editables` = **el arte tal cual**, sin ningún override. El color se guardaba bien y la TIZADA lo aplicaba (verificado en (18)), pero la pantalla seguía mostrando el color original → parecía que no hacía nada. De hecho el catálogo del usuario YA tenía un rojo guardado (`fill [0, .924, .924, .067]`) de sus pruebas: se guardó siempre, nunca se vio. **Fix:** nueva **`motor_pedido.svg_editable(path_arte, mesa, capa, bbox_mu, colores=, obj_id=)`** — aísla la capa ENTERA (o una figura) y la exporta a SVG **recoloreada por figura** (usa `aislar_capa_objetos`/`aislar_objeto`); `_svg_objeto_aislado` quedó como alias. En `get_editables`, si alguna figura de la capa tiene color para ESA variable se regenera `o["svg"]` con los colores y se **descarta `o["thumb"]`** (la lista prefiere el PNG y mostraría el color viejo); cada chip de figura trae además su miniatura recoloreada. **VERIFICADO:** `svg_editable` sobre el arte real → la elipse chica pasa de `#00bdf2` a `#fff200` y la otra queda `#231f20` intacta; el endpoint en vivo (`GET /api/productos/editables?diseno=erferg`) ya devuelve el SVG con el rojo que el usuario tenía guardado (`#df362a`) y `thumb:null`. Server reiniciado por PID (28388 → nuevo). **NO verificado:** el click a mano en la app (login).
- **2026-07-22 (19) — FIX: el selector de color no abría desde NINGÚN lado que no fuera Config→Etiqueta (por eso «el color del editable no funciona para nada»).** El usuario: «al presionar sobre el espacio del color no abre nada, no cambia color nada». **Causa:** `<ColorPickerModal open={!!picker} …>` estaba montado **dentro de la rama `tabAjustesMolde === 'etiqueta'`** de Config (venía así del `commit 18db30d`, el que puso el selector tipo Illustrator en el editable). Desde el **editor de objetos** (Pedidos→Arte) el `setPicker({…})` seteaba el estado pero **el componente no existía en el árbol** → no se abría nada, y como el único camino para poner el color es el picker, **el color del editable nunca se pudo cambiar desde el editor**. No era ni el vector ni el motor: el backend/motor ya aplicaban bien el color (ver (18)). **Fix:** una **única instancia GLOBAL** del `ColorPickerModal` al final del `return` de `App` (junto a los toasts), y se sacó la de la tab etiqueta. **VERIFICADO end-to-end con el arte y el molde REALES, sin tocar nada en disco** (se pasó una COPIA en memoria de `prod` a `_piezas_base`, que es exactamente el camino que corre la app): guardar `…["Escudo"]["objetos"]["cb7935f5"]["color"]={"fill":[0,0,1,0]}` → la elipse chica pasa a **amarillo (11.834 px)** y **sólo cambia el escudo** (bbox del diff = 602,1482–880,1572, nada fuera); round-trip `servidor._editables_color` → IDENT `"Escudo␟cb7935f5"` = el que arma el motor. `npm run build` OK (frontend puro, no hizo falta reiniciar el server). **NO verificado:** el click a mano en la app (login).

- **2026-07-22 (18) — CAMBIO DE REGLA (decisión del usuario): LA CAPA «Editable …» ES EL OBJETO — todo lo de adentro se transforma JUNTO; el COLOR sigue siendo por figura.** Ver §10.b (reescrita). **Por qué:** el usuario pidió que las figuras **agrupadas en Illustrator** escalaran juntas y las no agrupadas no. **Se investigó el .ai REAL y NO SE PUEDE**: el agrupado no viaja en el archivo. En `Diseño Short.ai` las 2 elipses que en el panel de capas están dentro de un `<Grupo>` salen al content-stream **planas y consecutivas** (`q cm m c c c c f Q` ×2, mismo nivel, mismo `q` de la capa), **sin** `BDC /Figure`, **sin** XObject `/Group`, **sin** anidamiento extra; el `ExtGState` es `BM/Normal ca 1 CA 1 SMask/None` (no hay grupo de transparencia). El árbol de grupos, los **nombres de objeto** y las **sub-capas** viven en `PieceInfo→/Illustrator→/AIPrivateData*` = **PGF comprimido con zstd** (`%AI24_ZStandard_Data`, 778 KB en esa mesa), propietario de Adobe → no se puede leer confiable. `OCProperties/D/Order` es **plano**: sólo las capas de PRIMER NIVEL sobreviven como OCG (`Diseño`, `Editable Escudo`, `guias`). Se le ofrecieron 3 alternativas (agrupar en nuestra UI / convención en el nombre de capa / truco knockout-group) y **las rechazó las 3**: «que lo tome como está» → **la capa es la unidad**. Para separar objetos: **una capa «Editable …» por objeto**. **CAMBIOS.** `molde_real.py`: nueva **`aislar_capa_objetos(pdf,page,capa,colores)`** (aísla la capa ENTERA recoloreando figura por figura) y `_analizar_capa` ahora lee el fill también del operador **`scn` de 4 canales** (Illustrator pinta con `scn` sobre ICCBased CMYK, no con `k` → el color de la figura salía vacío; con el arte real ahora da negro K100 y cian C75). `motor_pedido.py`: `_edit_por_mesa` arma **una unidad por CAPA** (bbox/w_cm/h_cm = **unión**, + `objetos:[{obj_id,ident}]` sólo para el color); `_es_redibujado` también dispara si **cualquier figura** tiene color; nuevo `_colores_de(u,variante)`; `pagina_arte_solo(…, colores=)` (cache key ampliada); `pagina_arte_pieza` **saca la capa ENTERA** del diseño base (se eliminó la supresión parcial por objeto). `servidor.py`: `_tf_de_capa` (compat: adopta el transform de la 1ª figura si la config vieja quedó anidada), `_editables_cfg` aplana **por capa**, `set_editable` **ignora el obj_id** y guarda a nivel capa, `get_editables` devuelve **1 ítem por capa** + **`partes[]`** (obj_id/ident/label/color/fill/recolorable/svg) cuando hay ≥2 figuras. `App.jsx`: el panel COLOR muestra los **chips de figura** (miniatura SVG + punto del color actual) para elegir cuál pintar (estado `colorParte`, se resetea al cambiar de objeto); textos ajustados («N figuras — se mueven y escalan juntas, pero el color va de a una»). **VERIFICADO** (`scratchpad/verif_grupo.py`, arte sintético de 3 figuras + molde real `prod_default`, sólo lectura + tmp): redibujar la capa en identidad = **0 px** vs el diseño original; **mover** la capa → las 3 figuras se desplazan **lo mismo** (572/-319 px, ±0.5 de centroide) y **escalar ×1.4** → las 3 crecen ×1.96/1.97/1.95 en área (juntas y sin deformar); **recolorear UNA figura** → **0 px** cambiados en las otras dos, y la figura pasa de magenta a negro. Endpoint en vivo (server reiniciado por PID 26288): `GET /api/productos/editables?diseno=erferg` (molde «Molde short», el arte del usuario) devuelve **mesa 3 = 1 objeto 8.5×8.5 cm sin partes** y **mesa 4 = 1 objeto 8.7×2.8 cm con 2 partes** (`6e502de1` K100 / `cb7935f5` C75, las dos con SVG). **Y sobre la PIEZA REAL** (`_piezas_base`, «Frente izquierdo»/2XL, pintando cada figura de un color distinto para poder medirlas): mover → las dos se desplazan **(+147,−109) px exactos las dos**; escalar ×1.5 → las dos crecen ×2.26 en área; los dos colores se aplican **independientes**. **BUG encontrado y arreglado en el camino:** `_analizar_capa` no cataloga el **TEXTO** como pintado → el aislado por índice **dejaba colado el rótulo de «guías»** de otra capa (399 px arriba de la mesa) y, al revés, se habría comido el texto de una capa editable. Ahora cada op de texto (`Tj/TJ/'/"`) es una unidad más → `aislar_capa_objetos` vs `aislar_capa` sobre la mesa real da **0 px** de diferencia (antes 399). `npm run build` OK. **NO verificado:** la pantalla a mano (la app pide login y no se pasó); el preview-vs-HOJA se comparó por conteo de píxeles y **da la misma diferencia que SIN ninguna edición** (ruido de rasterizado de la hoja, no del cambio) — la igualdad estricta arte=tizada la cubre `verif_tizada.py` a nivel `_armar_base`. **Queda inerte** (no borrado) el storage viejo por figura `…[capa]["objetos"][oid]["transforms"]`: `_tf_de_capa` lo adopta si la capa no tiene transform propio.
- **2026-07-22 (17) — VERIFICADO: la UI del editor ya maneja los objetos POR SEPARADO (era el «FALTA» de (16)).** Ver §10.b («Editor (front) — VERIFICADO POR OBJETO»). El `commit 881a05d` dejó anotado que faltaba la UI porque «la identidad por nombre colisiona si una capa trae >1» — **eso ya no era cierto**: el backend bakea el `obj_id` DENTRO de `nombre` (`get_editables` devuelve el IDENT `"capa␟obj_id"` para las capas multi y el `label` amigable), así que el editor, que clavea todo por `o.nombre` (dedup `_objsUnicos`, `editableSel`, `editorTfs`, guardado y color), **ya trata cada objeto por separado sin colisión**; el único toque de front que hacía falta (mostrar `o.label` en la lista, el panel de tamaño y el título del color-picker) ya estaba en (16). **Lo que faltaba era la VERIFICACIÓN con un arte real de varios objetos** — (16) sólo pudo probar con el sintético y por lógica porque «ningún arte del catálogo tiene una capa multi-objeto en su versión vigente». El usuario dejó uno que SÍ: `C:/Users/user2/Documents/1 - Pruba tizada/Diseño Short.ai`, capa **«Editable Escudo»** con **1 objeto en la mesa 3 y 2 elipses en la mesa 4** (obj_id `6e502de1`/`cb7935f5`, los dos `recolorable=true`). **VERIFICADO end-to-end contra los HANDLERS REALES** (`get_editables`/`set_editable`/`set_editable_color`, con catálogo EN MEMORIA —no se tocó `catalogo.json`— y un pid temporal que se creó y BORRÓ; harness `scratchpad/verif_ui_obj.py`): (1) la mesa 4 se expande en **2 ítems con `obj_id`/`nombre` DISTINTOS + `recolorable`**, y la mesa 3 en **1 ítem con `obj_id=None`** (compat); (2) un transform (dx/dy/rot/scale) puesto en el objeto A **deja al B intacto** (`transforms[M]` de B = None) y queda anidado en `[Escudo][objetos][6e502de1]` (sólo esa key); (3) un color CMYK en A **no toca a B** (`color` de B = None); (4) limpiar el color de A con `null` lo vuelve al original **sin borrar su transform**. **COMPAT:** `scratchpad/verif_color.py` sigue dando **0 px** (`editables_color` vacío == baseline) y el color del escudo se ve igual en tizada(pdf) y preview(svg) (máx 1 canal). **Cambio de código:** un solo **comentario** en `App.jsx` (arriba de `_objsUnicos`) que documenta que `o.nombre` YA es la identidad por objeto y que **NO** hay que reconstruir el IDENT en el front (duplicaría el `obj_id`); ninguna lógica cambió. `npm run build` OK; NO se tocó Python → **no hizo falta reiniciar el server** (sirve `dist` estático). **NO verificado:** la pantalla a mano dentro de la app (hay login y no se pasó; el arte real habría que cargarlo como diseño de un molde por la UI). El comportamiento que ve la UI está probado por los handlers que ELLA llama.

- **2026-07-22 (16) — HECHO: EDITABLES POR OBJETO — una capa «Editable …» con VARIOS objetos se edita/recolorea/mueve por SEPARADO.** Ver §10.b («OBJETOS DENTRO DE UNA CAPA»). Antes toda la capa OCG se trataba como UN editable; ahora cada **trazado pintado de primer nivel** o cada **XObject `Do`** de la capa es un objeto editable **independiente** (mover/rotar/escalar/espejar/color por su cuenta). **DETECCIÓN** (`molde_real.py`): `_analizar_capa`/`objetos_de_capa(page, capa)` recorren el content-stream UNA vez llevando CTM (q/Q/cm) y frame OCG (BDC/EMC), agrupan **relleno+trazo del MISMO trazado** por **firma de puntos de construcción** (dos figuras CONCÉNTRICAS —radios distintos, mismo centro— NO se fusionan: cada una es su objeto) y devuelven `{obj_id, kind, bbox, fill, recolorable, i_paints}`. **`obj_id` = hash de la geometría** (estable ante reordenamiento del stream). `extraer_editables` agrega `objetos:[…]` por capa (bbox_mu por objeto vía cropbox+UserUnit, **verificado idéntico** al bbox de la capa entera en el caso de 1 objeto) — capa de 1 objeto sigue = 1 entrada (compat). **PRIMITIVAS nuevas** (`molde_real.py`): `aislar_objeto(pdf,page,capa,obj_id,cmyk_fill,cmyk_stroke)` (aísla+recolorea UN objeto, espejo de `aislar_capa`), `suprimir_objetos(pdf,page,capa,obj_ids,conservar_marcadores=)` (saca sólo esos objetos del diseño; `conservar_marcadores=True` mantiene los BDC/EMC para que una `suprimir_capas` posterior siga encontrando los frames de guías/pers — un raspado los consume, por eso el ORDEN importa), `capa_admite_color_objeto`, `_reescribir_por_indice`. **IDENTIDAD** (`IDENT`): capa de 1 objeto → nombre de capa (compat); multi → `"nombre<SEP>obj_id"` (`SEP`=U+001F, `motor.SEP`==`servidor._EDIT_SEP`). **MOTOR** (`motor_pedido.py`): `editables_cfg`/`editables_color` viajan PLANOS por IDENT; `_edit_por_mesa` se aplana a UNIDADES (una por objeto, con `obj_id`/`ident`/bbox/tamaño propios); `pagina_arte_solo(mesa,capa,color,obj_id=)` aísla por objeto (cacheado por `(mesa,capa,obj_id,color)`); `pagina_arte_pieza` saca del diseño base SÓLO los objetos redibujados de una capa multi (`suprimir_objetos(…,conservar_marcadores=True)` ANTES de `suprimir_capas`) — las capas de 1 objeto siguen el camino viejo entero (compat pixel). **STORAGE anidado** (§10.b/§5): `prod["editables"][diseno][variable][capa]["objetos"][obj_id]["transforms"|"color"]` (multi) / plano `…[capa]["transforms"|"color"]` (1 objeto); `_editables_cfg`/`_editables_color` lo aplanan a IDENT; `set_editable`/`set_editable_color` reciben el IDENT (o `obj_id`) y **anidan**. **`get_editables`** expande una capa multi en N ítems (`nombre`=IDENT, `label` amigable «capa (i)», `obj_id`, bbox/pos/w_cm/h_cm/recolorable/color por objeto). **EDITOR** (`App.jsx`): el editor ya indexaba por `o.nombre` → cada objeto aparece como su propia fila y se edita solo, sin más cambios; sólo se muestra `o.label` (la fila, el panel de tamaño y el título del color picker). **VERIFICADO PIXEL con el motor REAL** (harness `scratchpad/verif_obj.py`, arte SINTÉTICO de 3 objetos «Editable prueba» sobre el molde real `prod_default`, `Frente 1`/M→mesa 7, render): **(1) arte=BASE** — redibujar 1 objeto (o los 3) en identidad == diseño original = **0 px**; **(2) AISLAMIENTO** — mover/rotar A ⇒ **0 px** en los píxeles reales de B y C; recolorar B→negro ⇒ **0 px** en A y C (y B cambia de magenta a negro, 23256 px); **(3) COMPAT 1-objeto** — «Editable escudo» de `dcvd` (un polígono, TRUE 1-objeto) generado con el código NUEVO vs el BASELINE pre-cambio (`scratchpad/baseline/`), **sin editar Y con mover+color = 0/28.2M px**; **(4) MULTI-objeto REAL** — `freger/arte.v2.ai` «Editable logo moreggit» (2 XObjects) → detección **2 objetos**, equivalencia identidad = 0 px, y **SIN editar** NEW vs OLD = **0/22.9M px** (la regla es «sin ediciones = idéntico», no «1 objeto»); **(5) CONCÉNTRICAS** — 2 elipses mismo centro/radios distintos → **2 objetos** (no se fusionan), aislar/suprimir una deja la otra intacta. Server helpers round-trip verificados (`scratchpad/verif_server.py`). `npm run build` OK (`index-CHZ_Mg8s.js`, servido); server reiniciado por PID (23972 → **el actual**) y **dejado corriendo**; la app carga con **consola sin errores** (pantalla de login). **NO verificado / dudoso:** el editor a mano (hay login, no se pasó); ninguno de los artes REALES del catálogo tiene HOY una capa multi-objeto en su versión VIGENTE (los escudos son 1 polígono o 1 `Do`; el logo de `freger` multi vive en la versión v2, no en la vigente v4) → la expansión multi del **endpoint** `get_editables` en vivo se probó por lógica (unit test) y con el arte sintético, no con un producto del catálogo. **LÍMITE conocido (§10.b):** si «2 elipses» del usuario están dentro de un **grupo/XObject** (un solo `Do`), se ven como **1 objeto** y no se pueden separar ni recolorear (el color/forma vive adentro del XObject) — habría que desagrupar en Illustrator; el editor deshabilita el color en esos casos. arte=tizada por objeto: la pieza del preview (`solo_piezas`) ES el mismo `doc` que la tizada compone (misma `_armar_base`); comparando el preview contra la MISMA pieza embebida en la HOJA (cancelando la matriz del nesteo) dio 5.316/28.2M px, todo en un punto y por el desalineo **fraccional** de esa comparación de harness (el `doc` es idéntico por construcción). Harness obsoletos: `verif_tizada.py`/`verif_color.py` de sesiones previas (usar `verif_obj.py`/`verif_freger.py`).

- **2026-07-22 (15) — HECHO: COLOR override de un editable (recoloreo CMYK, POR VARIABLE) — motor + preview + storage + editor.** Ver §10.b («COLOR override…»), §5 (OBJETOS EDITABLES) y §7 (fila editables). Un editable del arte se puede **recolorear** sin tocar su forma ni el resto del diseño. **Storage** (`servidor.py`): color a nivel objeto en `prod["editables"][diseno][variable][nombre]["color"] = {"fill":[c,m,y,k]|null,"stroke":…}`; endpoint **`POST /api/productos/editable_color`** (color `null` = limpiar = volver al original); helpers `_clamp_color` (canales 0..1, exacto) y `_editables_color(prod,dslug)` → `{variable:{objeto:{fill,stroke}}}`; `get_editables` devuelve `color` + `recolorable` por objeto. **Motor** (`motor_pedido.py`): nuevo param `editables_color`; `_coloreados_nombres` se SUMA a `_redibujar_nombres` (un color-override entra por el camino "redibujar", el diseño base lo excluye y se redibuja recoloreado); `pagina_arte_solo(mesa,capa,color=…)` **recolorea ANTES de aislar** (gotcha §10.b: aislar borra los BDC/EMC que necesita `recolorar_capa`) y cachea por `(mesa,capa,color)`; `_color_de(nombre,variante)` resuelve por variable (fallback `"*"`). Detección de recoloreabilidad: `molde_real.capa_admite_color` + `motor.editables_recolorables` (sólo relleno/trazo directo; XObject/imagen NO). **Preview** (`_piezas_base` / `_piezas_base_clave` **v6→v7**): pasa `editables_color` al motor y lo mete en la clave de caché de disco (sin esto el color no invalidaba el render). **Editor** (`App.jsx`): panel "COLOR" del objeto seleccionado (swatch, presets CMYK, campos C/M/Y/K 0–100, "↺ Volver al color original"); no-recoloreables muestran el control deshabilitado con nota; `guardarColorEditable` (POST + invalida `_pvCache` —el color no está en `_pvKeyCon`— + recarga editables + refresca preview). Threading del color en `/api/generar` (single) y `/api/generar_multi` (vía `md["editables_color"]` → `generar_pedido_grupos`). **VERIFICADO PIXEL con el motor REAL** (harness `scratchpad/verif_color.py`, sobre una COPIA del arte real `dcvd` con «Editable escudo» —recoloreable por FILL— forzando `Frente 1`→mesa del escudo, talle M, render 300 DPI = 63.5M px): **(a) COMPAT** `editables_color` vacío vs baseline = **0 px** distintos; **(b) COLOR** escudo rojo **RGB[236,24,69] → magenta RGB[235,1,139]** = exactamente CMYK(0,1,0,0), footprint 313.022 px, el resto de la pieza intacto (los cambios son EXACTAMENTE el footprint del escudo, 0 px fuera); **(c) ARTE=TIZADA** color del escudo en tizada(pdf)=[235.4,0.8,138.7] vs preview(svg)=[235.4,0.8,139.7], **máx dif 1 canal** (redondeo SVG-vs-PDF, mismo doc). **Endpoints en vivo** (server real, molde de prueba `prod_default`): set color → GET lo trae → clear(null) → GET vuelve a null; `get_editables` da `recolorable:true`; `preview_piezas` con y sin color responde 200 (regenera, `cache=false`). Catálogo **sin color residual** (molde de prueba y del usuario limpios). `npm run build` OK (`index-CEccvi7_.js`, servido); server reiniciado por PID (13252 → **23972**) y **dejado corriendo**. **NO verificado / dudoso:** la UI del panel a mano — hay login y no se pasó (la app carga con **consola sin errores** en la pantalla de login); **XObjects**: `recolorar_capa` NO puede cambiar el color de un editable que pinta vía `Do` (ej. «Editable logo …» rasterizado, u objetos agregados) — se detecta y el editor lo deshabilita, no se intenta rasterizar/forzar (limitación conocida). El **stroke** override está soportado en backend/storage pero el panel del editor hoy sólo expone el **fill** (el caso del escudo); si un objeto define su color por trazo, habría que agregar el control de borde. El harness viejo `scratchpad/verif_tizada.py` apunta a un modelo por **sub-objeto** (`obj_id`/`fill`) que **no** coincide con el `extraer_editables` real (una entrada por capa) — quedó obsoleto; usar `verif_color.py`.

- **2026-07-22 (14) — HECHO: limpiar los textos del panel de Config → Moldería (sólo frontend).** Ver §10.d («Botón de ayuda `Ayuda`»). Pedido del usuario: «todos los textos de ahí eliminalos; que esas explicaciones estén dentro de un botón de ayuda o algo así en cada campo. Ahí sólo veremos herramientas». Se movieron **todos los párrafos de explicación** de `tabAjustesMolde === 'molderia'` (y de su hijo `NombrarVariantes`) detrás de un **«?»** al lado del título/control de cada herramienta, con un componente **reusable `Ayuda`** (nuevo, en `App.jsx` arriba de `NombrarVariantes`): globo por `createPortal`+`position:fixed` (no lo recorta ningún overflow), cierra al clic afuera/scroll/resize, `stopPropagation` para no accionar el control de atrás. **Textos movidos (verbatim, sin reescribir):** (1) intro «Carga y registra las piezas vectoriales del molde `.ai`.» → «?» en la fila de subir; (2) subtítulo del acordeón «Si el molde vino con las capas sin nombre…» → «?» junto al título (el header pasó de `<button>` a `<div role="button">` para poder anidar el botón); «El archivo original no se toca…» (POR CAPA y POR PIEZAS) y «Seleccioná en el visor las piezas de una variante…» → «?» junto al botón Aplicar / al contador; (3) panel «La misma pieza en cada talle»: la explicación **colapsada** y la **en-modo** (empTodas / por-talle) se unieron en UN «?» del título cuyo contenido cambia según el modo; «Clic para elegir una pieza…»/«Cada grupo se guarda al confirmarlo…»/«Estás viendo X: ¿alguna está mal?…» → «?» en las etiquetas Selección / Seleccionadas / Viendo; (4) cartel «Dos cosas para que tu molde sirva…» → «?» junto a «Indicar qué es cada pieza →»; (5) «Acá cargás y acomodás las piezas… andá a Variables» → «?». **NO se tocó** ningún aviso de **estado/error** (el cartel naranja «todavía no se puede usar», «N de M piezas agrupadas», «✓ Guardado automático», los rojos/naranjas de validación): son feedback. El botón «¿Cómo exportar el molde…?» (ya era un toggle de ayuda) quedó igual. **VERIFICADO:** `npm run build` OK (bundle nuevo servido); la app carga con la **consola sin errores** (pantalla de login); `grep` confirma que los 11 textos target quedan **sólo** dentro de `<Ayuda>` (ningún `<div>` de párrafo suelto sobrevive); **render `react-dom/server`** de una copia exacta del componente `Ayuda` → renderiza el botón «?» y **el texto queda oculto hasta el click** (no se llama `createPortal` con `pos=null`). **NO verificado:** la pantalla a mano — hay login y no se intentó pasarlo, así que no hay captura del panel abierto ni del globo desplegado. Puramente frontend: no cambió lógica, endpoints ni guardado.

- **2026-07-21 (13) — FIX de los tres problemas de Config → Moldería: guía «Capa 1», cartel naranja obsoleto y rótulos encimados.** Ver §10.c («EL ESTADO DEL MOLDE NO SE LEE DE LA DETECCIÓN QUE MUESTRA EL VISOR» + «RÓTULOS QUE NO SE PISAN»). **LOS TRES SALÍAN DE LA MISMA CAUSA, y no era la que parecía.** `_ajustar_variante_guia` **funcionaba bien** (verificado: partiendo un molde de 36 piezas en 6 variantes deja `variante_guia = XS`, una variante real) y el `variante_guia` guardado tampoco estaba mal. Lo que pasaba es que la pantalla mostraba **la detección `?candidatas=1`**, que lee el **archivo ORIGINAL** — donde siempre va a haber una sola capa «Capa 1», porque partir escribe una versión nueva y el original no se toca nunca. De ahí salían `talle_ref="Capa 1"` (el panel «Actual:» y el encabezado «Mesa: 1 · Capa: Capa 1»), `sin_variantes=true` (el cartel naranja, con el texto exacto que vio el usuario: «vino con todas las piezas en una sola capa») y las **36 piezas del bloque sin separar** (los rótulos encimados). **Y esa vista se activaba SOLA**: `NombrarVariantes` llamaba `onModo(true)` con sólo existir una asignación guardada (`yaPorPiezas`) — o sea siempre, para cualquier molde definido por piezas — y `activarVarPz` recarga `etqData` con `candidatas=1`; el acordeón, en cambio, arrancaba **plegado**. El usuario abría la Moldería y el visor ya estaba en una herramienta que él no pidió y que no veía. **Arreglos.** *Backend*: `GET /api/plantilla/deteccion` devuelve el estado del MOLDE aparte de la vista — **`talles_reales`** (nuevo `_talles_reales(pid)`, sale del registro + `resumen_plantilla.json`, **no** del PDF: `_talles_de_plantilla` hace un `get_drawings()` entero y esto se llama en cada detección), **`resuelto`** y **`guia`**; con `resuelto` se fuerzan `sin_variantes=False` y `falta_nombrar_variantes=False`. **Auto-corrección de los moldes que YA quedaron con la guía mal**: si `variante_guia` está puesta y ya no existe entre las reales, el propio GET la corrige — se arregla sola al abrir el molde, sin pedir nada. ⚠️ **Sólo si está puesta**: con `None` («automática») el sistema elige solo y escribirle una le cambiaría el talle de apertura a moldes sanos (`prod_default`). `GET /api/plantilla/variantes` devuelve **`resuelto`**. *Frontend*: `faltaNombrar = sin_talles && !resuelto` en el acordeón (+ resumen «✓ 6 variantes definidas: XS · S · M…»), el cartel naranja pide `!resuelto`, el botón de guía muestra `etqData.guia` y queda **deshabilitado mientras dura el modo por piezas** (cambiarla ahí recargaría el visor con los índices de la versión partida y rompería la asignación en curso), el encabezado del visor dice **qué** está mostrando («todas las piezas, sin separar» / «todas las variantes juntas» / «Talle: M»), **`tallesMolde`** reemplazó a `etqData.talles` en las 19 líneas que hablan de las variantes del molde, y `onModo(true)` sólo se dispara si el acordeón está **abierto** o falta algo de verdad. **Rótulos**: `canvasLayout` calcula **`sep`** (distancia al centro más cercano) → `sep × zoom` = píxeles de pantalla; con menos de **`LBL_MIN_PX`=24** queda un punto, con menos de **`TXT_MIN_PX`=60** el círculo sin textos, y la pieza elegida siempre completa; el **nombre de la variante va una vez por bloque** (`clusters`, y en el modo por piezas por variante asignada); aviso «N sin rótulo · acercá el zoom». **VERIFICADO con datos** sobre una **copia descartable** del molde del usuario (36 piezas → 6 variantes × 6, `formato=extendido`): (1) *guía* — sembrando a propósito `variante_guia="Capa 1"` en la base, un solo `GET /api/plantilla/deteccion?candidatas=1` la deja en **`XS`** en la base y devuelve `guia=XS`, `talles_reales=[XS,S,M,L,XL,2XL]`, y **los otros moldes no se tocan** (`prod_default` sigue en `None`, el del usuario en `M`); (2) *cartel* — en la MISMA vista `candidatas=1` (la que rompía) ahora `resuelto=true`, `sin_variantes=false`, `falta_nombrar_variantes=false`, y `GET /api/plantilla/variantes` da `sin_talles=false, resuelto=true`; (3) *rótulos* — **render real** del bloque **recortado literalmente de `App.jsx`** con `react-dom/server` (`scratchpad/armar_visor_test.py` genera el harness con el JSX y los umbrales del propio archivo; `scratchpad/verif_visor.mjs` mide sobre el SVG generado, con la geometría real que devuelve `deteccion_todas`): a «Ver todo» (k=0,124 px/mm) **ANTES 36 rótulos con 12 pares de círculos a <24 px (11,0 y 14,3 px: los «2XL 2XL») y 36 pares de textos a <60 px; AHORA 12 círculos + 24 puntos + 6 chips de variante y 0 pares encimados**; a 4× de zoom (k=0,5) vuelven **los 36, también con 0 encimados**; y la vista normal de **UN talle sigue igual** (6 piezas, **6 rótulos completos, 0 puntos, 0 encimados**) — o sea que el cambio sólo actúa donde había amontonamiento. Lo mismo en el modo «por piezas» (6 chips, 0 encimados). Molde de prueba **borrado**: `entrada/` y `datos/productos/` quedan con los **5 directorios del usuario**, catálogo con `prod_default` + `prod_20260721_143551_3261` y `activo` **restaurado** a ese mismo (borrar el de prueba lo había dejado en `prod_default`). `npm run build` OK (`index-xgpUceUC.js`, servido); server reiniciado por PID (19064 → **30080**) y **dejado corriendo**. **NO verificado:** la pantalla a mano — hay login y no se intentó pasarlo; el molde `prod_20260721_155921_d32c` que menciona el reporte **ya no existe en este entorno** (ni en el catálogo de la base ni en disco: quedan 5 directorios y 2 productos), así que se reprodujo todo sobre una copia con la MISMA forma (mismo archivo, mismas 36 piezas y las mismas 6 variantes que tenía guardadas el molde del usuario); y el molde del usuario **no se pudo consultar por API** (`GET` con su `pid` devuelve **403 «Ese molde es de otro usuario»** sin sesión iniciada), así que su auto-corrección de guía está probada sobre la copia, no sobre él.

- **2026-07-21 (12) — FIX de los dos bugs reportados: «una sola subida me creó 4 artículos» y «nombré las piezas y al volver no estaba nombrado».** Ver §10.d («DOS TRAMPAS QUE YA COSTARON»). **Causa del bug 1 (verificada con datos, no deducida):** la guarda que evitaba el duplicado vivía **sólo en el front** y trabajaba sobre un `productosCat` **trunco**. `app.secret_key` es aleatoria (no hay `TIZADA_SECRET`) → cada reinicio del server invalida la sesión; `GET /api/productos` oculta los moldes con dueño a quien no está identificado; y **`App` se monta antes del login**, así que el `fetchProductos()` del arranque salía sin sesión y devolvía **1 producto** — y **nadie lo volvía a pedir al loguearse** (`useEffect(…, [])`). Con la lista vacía de propios, «Mis artículos» se veía vacío (por eso el usuario volvía a subir) y la guarda no encontraba nada. Los 4 «Molde short» del catálogo tienen `propio=True` y `creado_por=1` → **los 4 salieron de `subirMiMolde`**, y sus horas (14:35, 14:53, 15:31, 15:59) caen **justo después de cada reinicio del server** de la sesión anterior; el `index.html` se sirve `no-store`, así que el navegador tenía la build **con** la guarda: la guarda corrió y falló. **Arreglo:** (a) `useEffect(…, [yo?.id])` que re-pide catálogo/estado/piezas al iniciar sesión; (b) **`POST /api/productos/crear` idempotente** para `propio:true` (mismo dueño + mismo nombre ⇒ devuelve el existente con `reusado:true` y lo activa) — una guarda de cliente no es una guarda; (c) `crear_producto` deja el activo **también en la sesión** (`_activar_en_sesion`), que `_get_active_producto_id` mira ANTES que el global. **Causa del bug 2:** `guardarEtiquetas` (y ~20 fetches más del flujo de config) iban **sin `pid`** → el server escribía en el molde **activo**, que no es necesariamente el que se está configurando (`handleActivarProducto` es async y no se espera; la sesión se resetea sola). **Reproducido con el server real:** el mismo `POST /api/plantilla/etiquetas` sin `pid` escribió en el molde ACTIVO (B) **reemplazándole el registro entero** mientras el molde que se estaba configurando (A) quedaba sin tocar. **Arreglo:** `pidCfg` (= `molderiaAbierta || modoMiMolde || activo`) + `qPid()` en TODO el flujo (detección, etiquetas, nido, medidas, pdf_guia, variantes, variantes_piezas y su borrador, emparejado, grupo_pieza, config GET/POST, arte: mapeo/detección/perfil/preview/asignar_todo, subidas de plantilla y arte con `pid` en el FormData, `variante_guia` y la clave de localStorage del talle guía) — y las **claves de caché del front** (`_talleDetCache`, `_pvCache`) salen del mismo pid que la URL. **De paso:** la tarjeta de «Mis artículos» muestra la **fecha** cuando hay dos artículos con el mismo nombre. **VERIFICADO por API contra el server real con DOS moldes de prueba propios** (36 piezas, copia descartable del molde del usuario): crear 3 veces «ZZ Prueba A» ⇒ **el mismo id las 3 veces** (`reusado:true`) y el catálogo pasa de 5 a 7 productos (2, no 4); con el **activo puesto en B** se configuró **A** (partir en 2 variantes, nombrar 3 piezas, agrupar una más) y el nombrado quedó **en A** (`ZZ Frente/ZZ Espalda/ZZ Manga/ZZ Cuello`) con **B intacto**; releer devuelve lo mismo; **reiniciar el server y releer: idéntico** (`nombres_existentes` = las 4 en A). Control explícito del bug viejo: el POST **sin** `pid` cayó en B. **Estado del molde del usuario:** su nombrado **NO se perdió** — está en `prod_20260721_155921_d32c` (Costadillo/Espalda/Frente izq. y der.); los otros tres «Molde short» tienen nombres provisorios («Pieza 1…6»), así que lo más probable es que haya abierto una tarjeta distinta (los 4 se ven iguales). Moldes de prueba **borrados**; catálogo final: los **mismos 5** productos y `activo` restaurado a `prod_20260721_155921_d32c`; los registros del usuario quedaron con su mtime original. `npm run build` OK (`index-CrQss3kg.js`, con `pid:Xe` en el POST de etiquetas y el efecto de re-carga por login); server reiniciado por PID (29836 → 33096 → el actual) y **dejado corriendo**. **NO verificado:** la UI a mano (hay login y no se intentó pasarlo; la app carga y la **consola queda sin un solo mensaje** en la pantalla de login); tampoco se pudo probar el escenario exacto **con sesión iniciada** (no hay contraseña) — la cadena está probada por código + por el comportamiento de `GET /api/productos` sin sesión (devuelve 1 de 5 productos).

- **2026-07-21 (11) — HECHO: agrupar piezas viendo TODAS LAS VARIANTES JUNTAS (el flujo de (8)/(10) se reemplaza).** Ver §10.c. El usuario **rechazó** el flujo de a un talle, textual: «el indicar la misma pieza en cada talle no es intuitivo. Es más fácil: mostrar las piezas de TODOS los talles y seleccionar las piezas y ponerle el nombre, así como se hace el nombrar — es la misma función. O sea decir: todo esto es Frente, esto es Espalda». Se hizo **literal**: el visor muestra las 36 piezas de las 6 variantes a la vez, el usuario las selecciona (clic o recuadro) y escribe «Frente» — un solo gesto define el **nombre** y la **correspondencia**. **Backend:** `MP.detectar_piezas_todas(path)` (piezas de todos los talles en un lienzo, con `talle` + `t_idx` = el `pieza_idx` del registro) + `_item_visor()` extraída de `detectar_piezas` (las DOS vistas arman el path con la misma función: si no, la misma pieza se vería distinta según de dónde se mire) + `_mesa_principal()`; endpoint `GET /api/plantilla/deteccion_todas` con caché en disco. **El endpoint de guardado NO cambió**: `POST /api/plantilla/grupo_pieza` ya aceptaba `nombre` + `guia_idx` + `piezas {talle: idx}` — lo que cambió es que ahora el usuario los elige todos de una y quedan **confirmados a mano** (en `manual`, que `_aplicar_fijos` respeta) en el mismo POST. **Frontend:** `canvasLayout` toma `empTodasData` en vez de `etqData` cuando el modo está activo (una línea) — **el visor, `selNombrar`, `toggleSelNombrar` e `iniciarRubber` se reusan tal cual**; `empTodasInfo` resuelve nombre/confirmado por `(talle|t_idx)` porque `etqNombres` es de UN talle; validaciones **antes** de guardar (2 piezas del mismo talle = rojo y bloquea, falta la del talle guía = bloquea, faltan talles = naranja y NO bloquea); `fijarPiezaTodas` para corregir sin cambiar de talle. **Molde `anidado` (talles dibujados uno encima del otro, p.ej. `prod_default`): NO se muestra junto** — se cae al flujo de a un talle y se explica en una línea; el `formato` se consulta **antes** de extraer (90 ms contra segundos). **«Ajuste avanzado ▸» intacto**, escondido. **VERIFICADO con datos**, contra el server real y sobre una **copia descartable** del molde del usuario (36 piezas, 6 variantes, `formato=extendido`): `deteccion_todas` devuelve **36 piezas / 6 talles × 6** (3,0 s la 1ª vez, **17 ms** cacheado); se crearon 3 grupos eligiendo a mano una pieza por talle y **cruzando a propósito XS** (Frente=XS#1, Espalda=XS#0, al revés de lo que propone la heurística) → `registro_producto.json` queda con **Frente = XS#1 47,0×52,7 · S#0 43,4×58,0 · M#0 45,2×60,5 · L#0 47,0×63,0 · XL#0 48,8×65,5 · 2XL#0 51,2×68,0 cm** y Espalda con el cruce inverso (XS#0 41,5×55,5); **las 18 entradas del registro coinciden con la geometría del visor** (w_cm/h_cm, tolerancia 0,15 cm); `emparejado_talles.json → manual` guarda los 5 talles; **reiniciando el server (salir y volver) queda idéntico**; nombre repetido → **409**; grupo **parcial** (sólo S y M) → 200, esos dos en `manual` y el resto con la propuesta. Molde de prueba **borrado**: `entrada/` y `datos/productos/` con los 7 directorios del usuario, catálogo restaurado y la BASE (fuente de verdad real del catálogo, no el JSON) **nunca se tocó**. `npm run build` OK; server reiniciado por PID y **dejado corriendo**. **NO verificado:** la pantalla a mano — hay login, no se intentó pasarlo; la consola del navegador queda **sin errores** en la pantalla de login y el **screenshot no funciona** en este entorno (timeout), así que no hay captura del panel nuevo. **Trampa que costó tiempo:** el catálogo de productos **ya no se lee de `datos/productos_catalogo.json`** sino de la base (`db.get_doc("catalogo")`) — agregar el molde de prueba al JSON no lo registra, y por eso su `variante_guia` no se aplicó (la guía cayó en la automática, `XS`). Para pruebas alcanza con los directorios + `?pid=`.

- **2026-07-21 (10) — HECHO: usabilidad del panel «La misma pieza en cada talle» («mejorá esto para que sea mejor»).** Ver §10.c. Lo que se veía en la pantalla del usuario: grupos llamados «Pieza 2/3/4…», «0/5 confirmadas» + un «Confirmar todo» **en cada fila** (36 piezas = 36 clics y 36 re-armados del registro), los **mismos chips de talle repetidos** en todas las filas ocupando la pantalla entera, **ningún número global** (¿cuánto falta? ¿ya puedo seguir?) y ninguna forma de saber **qué pieza es** cada fila. **Cambios (todos en `frontend/src/App.jsx`, `empVista==='simple'`):** (1) **encabezado de progreso** — «N de TOTAL piezas agrupadas · M confirmadas», barra de dos capas y una sola línea con el **primer obstáculo real**; los números salen de `empStats`, que también alimenta el resumen del panel **plegado** (antes decía sólo «✓ N piezas agrupadas», ahora dice de cuántas y qué falta). (2) **«Confirmar todo» global** — un único `POST /api/plantilla/emparejado` **sin `talle`** con el `manual` completo (ese modo del endpoint ya existía y reemplaza el diccionario entero) → **una** re-propagación en vez de N. (3) **Miniatura de la pieza** en cada fila (`miniPieza`, el `path_svg` del talle guía recortado a su bbox; geometría vía `cargarPzsGuia`, cacheada en `_talleDetCache`). (4) **Filas compactas**: los chips por talle y las acciones se abren **sólo en la fila que se mira** (`empAbierto`), con filtro **Pendientes/Listas/Todas** (arranca en pendientes) y buscador si hay >8 grupos. (5) **Renombrar desde la propia fila** (`renombrarGrupo`, mismo endpoint `grupo_pieza` con `guia_idx`+`renombrar_de`), con el provisorio (`Pieza N`) marcado en itálica y «✎ poner nombre». (6) Estado por fila legible: `✓ listo` / `falta en N` / `propuesta` (el críptico «0/5» ya no aparece). **Bug encontrado y arreglado de paso:** `colorGrupo` devuelve **`hsl(...)`, no hex** → el `${color}55` que ya usaba el resumen plegado era un color **inválido** (borde invisible); ahora hay `colorGrupoA()` (hsla) y la miniatura usa `fillOpacity`. **VERIFICADO:** `npm run build` OK (bundle nuevo servido: `index-BW23BhQR.js`); server reiniciado por PID (9376 → 34812); **render real del bloque nuevo** con `react-dom/server` sobre el JSX **extraído literalmente de `App.jsx`** (`scratchpad/armar_panel_test.py` + `render_panel.mjs`) → sale «5 de 6 piezas agrupadas · 1 confirmadas / Falta 1 pieza por agrupar / Pendientes 4 · Listas 1 · Todas 5», 4 miniaturas con su `viewBox`, 0 colores inválidos (ese render fue el que destapó el bug del `hsl`+alfa y los plurales «Faltan 1 piezas»); **prueba de API punta a punta** contra el server real con **molde de prueba propio** (`prueba_panel.py`, S/M/L × 4 piezas): crear 4 grupos → confirmar **todo de una pasada** (`manual` idéntico al enviado y `asignacion` **sin moverse**) → renombrar A→Frente (**la confirmación a mano sigue al nombre nuevo**) → salir y volver (idéntico) → deshacer «D» (se va con sus fijos, sin huérfanos). Molde de prueba **borrado** y catálogo **byte-idéntico** al de antes (incluido el `activo`). **NO verificado:** la pantalla a mano dentro de la app — hay login y no se intentó pasarlo; además el screenshot del navegador **no funciona** en este entorno (timeout), así que **no hay captura**; la consola queda sin errores en la pantalla de login.

- **2026-07-21 (9) — FIX: el trabajo de «asignar variantes por piezas» se PERDÍA al salir; ahora se guarda solo.** Reportado por el usuario: «cargás los talles y les asignás las piezas, si vuelvo atrás y vuelvo a entrar se pierde y no veo botón de guardar». Ver §10.c. **Causa exacta (verificada en el código):** `variantes_piezas.json` se escribía **únicamente dentro de `POST /api/plantilla/variantes_piezas`**, el endpoint caro que **parte el PDF** y rehace el registro. Todo lo que el usuario asignaba vivía sólo en el estado de React (`varPzAsig`); salir del panel = perder todo. El GET y la recarga del front **ya estaban bien** (`asignacion_piezas` → `varPzAsig` en `activarVarPz`): lo que faltaba era que hubiera algo guardado. Y el botón «Aplicar» estaba **al final** del panel, debajo de la lista de variantes (scroll) — por eso «no lo veo». **Arreglo:** endpoint nuevo **`POST /api/plantilla/variantes_piezas_borrador`** que persiste **sólo** la asignación cruda (medido: **0,01 s**, contra 0,28 s del aplicar en un molde de 36 piezas — en moldes grandes la diferencia es de segundos), disparado por el front **en cada cambio** con 500 ms de debounce; `variantes_piezas.json` gana el campo **`aplicadas`** (lo que realmente se partió) para poder distinguir «guardado» de «aplicado» — los archivos viejos, que no lo tienen, se siembran desde `asignaciones` para que un molde ya partido no figure como pendiente. UI: barra **sticky** arriba del panel con «✓ Guardado automático» y el botón **Aplicar al molde** (ya no al final de la lista), el acordeón **se abre solo** si hay borrador sin aplicar y el encabezado muestra el chip «guardado · falta aplicar». **Grupos de piezas homólogas:** el backend **ya guardaba** cada confirmación en el momento (verificado), pero al volver el panel arrancaba plegado y vacío → ahora se **precarga** `GET /api/plantilla/emparejado` al abrir Moldería y el panel cerrado muestra «✓ N piezas ya agrupadas (guardado)» con los chips; además los fetch de emparejado/grupo mandan `pid` explícito. **VERIFICADO por API sobre un molde de prueba propio** (copia de la plantilla del usuario, 36 piezas en «Capa 1»): asignar 10 piezas → borrador 200 en 0,01 s → **nuevo GET devuelve las 10 idénticas**; completar a 36 → GET devuelve 36 con `pendiente=True`; **aplicar** (0,28 s, 6 variantes / 6 piezas, sin problemas) → GET 36 asignadas = 36 aplicadas, `pendiente=False`; **corregir una pieza sin aplicar** → vuelve a `pendiente=True` con `borrador=2XL` vs `aplicada=XS`. Grupos: crear «ZZ Frente Test» → salir y volver → el nombre y la correspondencia en los 6 talles siguen; confirmar a mano un talle → `manual={"L":{"ZZ Frente Test":5}}` persistido. `npm run build` OK; server reiniciado por PID (36424 → 9376). Molde de prueba **borrado** (`entrada/` y `datos/productos/` quedan con los 5 directorios del usuario, catálogo con `prod_default` + `prod_20260721_143551_3261`, activo restaurado a ese mismo). **NO verificado:** la UI a mano dentro de la app (hay login y no se intentó pasarlo) — la consola del navegador queda **limpia** en la pantalla de login; y el comportamiento del sticky/indicador no se pudo ver renderizado.

- **2026-07-21 (8) — HECHO: AGRUPAR PIEZAS HOMÓLOGAS = el camino principal (el de (7) queda como «ajuste avanzado»).** Ver §10.c. El usuario **rechazó** el panel de (7): «el emparejar talles no es muy intuitivo, debe ser más fácil: seleccionando todas las piezas e indicar que son las mismas y así». Ahora el gesto es UNO: **tocá la pieza en el talle guía → escribí qué es → confirmá**, y con eso queda definido a la vez el **nombre** y la **correspondencia entre talles**. Nada de «emparejar», offsets ni «#7». Endpoint nuevo **`POST /api/plantilla/grupo_pieza`** `{nombre, guia_idx, piezas?:{talle:idx}, renombrar_de?, eliminar?}`: el nombre entra al nombrado de la guía (heurística propaga) y lo que el usuario confirma se guarda en el mecanismo que YA existía (`emparejado_talles.json → manual` + `_aplicar_fijos`) — **no se inventó otro almacenamiento**. **Ayuda, no imposición:** lo no confirmado queda como *propuesta* del sistema y la UI lo distingue (chip gris «propuesto» vs violeta «✓ confirmado» vs naranja «! ninguna pieza le tocó»); cada grupo se pinta con **su color** (mismo color en todos los talles) y el nombre encima de la pieza. Backend refactor: `_guardar_y_repropagar()` (compartido con el POST viejo) y **`MP.nombres_normalizados()`** extraída de `alta_plantilla_manual` — hacía falta porque la clave de `manual` es el nombre **FINAL** (el registro renumera genéricos duplicados) y una corrección guardada con el nombre tipeado quedaba huérfana; al crear/renombrar/deshacer un grupo las claves se **remapean**. Nombre repetido → **409** en vez de renumerar por atrás. **De a un talle a la vez y no todos juntos a propósito:** el formato `anidado` dibuja los talles UNO ENCIMA DEL OTRO y el visor renderiza la detección de UN talle — todos juntos es ilegible; se compensa con la pre-selección. **Fix de paso:** el marquee (`iniciarRubber`) nunca se disparaba en este panel (su condición sólo miraba la pestaña Variables) → ahora incluye `empModo`. **VERIFICADO con datos** (mismo molde de prueba propio de (7): 3 talles × 4 piezas casi idénticas, M acomodado al revés): nombrando sólo en la guía, la propuesta da **0/4 en M** (`A→0,B→2,C→1,D→3` vs. lo correcto `A→3,B→1,C→2,D→0`) y **4/4 en L** (control); **agrupando a mano las 4 en M: 4/4** en `registro_producto.json` (`A@M` queda en `pieza_idx=3, 7.4×7.4 cm` — la pieza correcta, contra 8.1×8.1 de la equivocada) y `emparejado_talles.json` guarda `{"M":{"A":3,"B":1,"C":2,"D":0}}`; **re-propagar no lo pisa** (sigue 4/4); L intacto en automático; nombre duplicado → 409; **renombrar** `A→Frente` arrastra la corrección (`Frente@M = 3`); **deshacer** un grupo lo saca del registro y se lleva sus fijos; `/api/plantilla/nido` 200. Moldes de prueba borrados (3), catálogo con `prod_default`, `prod_20260721_111945_7593` y `prod_20260721_130716_6eb6` (el que subió el usuario a las 13:07) intactos. **NO verificado:** la UI a mano dentro de la app (hay login y no se intentó pasarlo) — la consola del navegador queda limpia en la pantalla de login; no se generó una tizada (el molde de prueba no tiene arte); y el «activo» del catálogo se restauró a `prod_20260721_130716_6eb6` por deducción (crear un producto lo activa; era el último del usuario), no había registro del valor previo.

- **2026-07-21 (7) — HECHO: emparejar talles A MANO (seleccionar + reacomodar + corregir).** Ver §10.c. Pedido del usuario: «agregale una opción para seleccionar y reacomodar; para los moldes que no vienen uno sobre el otro el sistema no sabrá». Efectivamente: el nombre de pieza se propaga con `_emparejar_por_forma` comparando **cómo está acomodado cada talle**, y con un molde desprolijo esa comparación **no tiene señal**. Ahora hay dos salidas, las dos en el visor que ya existía: **(1) reacomodar** — seleccionar piezas (clic/recuadro) y arrastrarlas; el desplazamiento es **virtual** (`_bboxes_acomodadas` corre la caja **sólo** para los rasgos del emparejado, el archivo y la tizada no se tocan); **(2) corregir** — decir a mano qué pieza es cuál en ese talle (`_aplicar_fijos`, va **después** de la heurística y del DXF, y le saca el índice a quien lo tuviera). Persistencia en `emparejado_talles.json`; `GET/POST /api/plantilla/emparejado`. **Guardar no alcanzaba:** el emparejado se decide al CONSTRUIR el registro, así que el POST guarda y **re-arma el registro** (`_guia_y_asignaciones` + `alta_plantilla_manual`) — y los 3 caminos que emparejan (`alta_plantilla_manual`, `nido_piezas`, `remapear_registro`) reciben el ajuste en sus 5 llamados. **Dos cachés que había que tocar o quedaba media feature:** `_nido_clave` → v6 (mtime del ajuste) y **`_piezas_base_clave` → v6 con el mtime del REGISTRO** — no estaba, así que re-emparejar (o simplemente re-nombrar piezas, agujero que ya existía) dejaba el render cacheado del Arte apuntando a la pieza vieja. **VERIFICADO con datos, sobre un molde de prueba propio** (3 talles × 4 piezas casi idénticas —el aspecto/área no distinguen, manda la posición— con el talle **M acomodado al revés**): automático **0/4** en M (`A→0, B→2, C→1, D→3` cuando lo correcto es `A→3, B→1, C→2, D→0`) y **4/4** en el talle de control L; **tras reacomodar los 4 offsets: 4/4** sin ninguna corrección manual; **corrección manual** `A→3` deja `pieza_idx=3, w_cm=7.4` (la pieza correcta, contra 8.1 de la equivocada) y la manual **gana** sobre un acomodo que daba otra cosa (`A→0` forzado; `D` queda sin emparejar, no hay dos nombres en la misma pieza); quitar la corrección devuelve el automático. `/api/plantilla/nido` 200. Molde de prueba borrado; catálogo con `prod_default` + `prod_20260721_111945_7593` y activo restaurado. **De paso:** el arrastre del visor usaba `img_w` como ancho de viewBox — el viewBox se agranda para abarcar piezas que exceden la página, así que la pieza se corría **más/menos que el mouse**; ahora usa `vbW` (arregla también «Acomodar piezas»). **NO verificado:** la UI a mano dentro de la app (hay login y no se intentó pasarlo) — la consola del navegador queda limpia en la pantalla de login; y no se probó sobre un molde con arte (no se generó tizada).

- **2026-07-21 (6) — HECHO: asignar variantes SELECCIONANDO PIEZAS (2º modo de la herramienta).** Ver §10.c. Reportado por el usuario: «el asignar variante no está correcto, debe mostrar todas las piezas, se selecciona 1 o varias y se escribe el nombre». Su molde trae **36 piezas en una sola capa**: no hay capas que nombrar. **Lo que NO alcanzaba:** guardar la variante de cada pieza en el registro — el talle se resuelve por NOMBRE DE CAPA en todo el sistema (`molde_real._candidatos_mesa`), así que el motor se quedaría sin piezas. Por eso `variantes_molde.separar_por_piezas` **parte el content stream** y crea **una capa (OCG) real por variante** en una versión nueva del molde (el original intacto), y recién ahí se rehace el registro con `alta_plantilla_manual` + `_emparejar_por_forma` (nombres provisorios `Pieza N` si todavía no están nombradas; los ya existentes se recuperan por `bbox_mu`). Backend: `POST /api/plantilla/variantes_piezas`, `GET /api/plantilla/deteccion?candidatas=1` (lee el **original** → índices de pieza estables para poder corregir), `MP.detectar_piezas(capas_candidatas=)` + `_capas_con_dibujo`, flag `sin_variantes` en la detección. UI: selector **Por capa / Por piezas** dentro de `NombrarVariantes` (modo sugerido por el molde, cambiable a mano) y panel de asignación que **reusa el visor y el gesto del nombrado de piezas** (`varPzModo`/`varPzAsig`, `startDrag`+`iniciarRubber`). **Verificado por API sobre una COPIA del molde del usuario:** 36 piezas listadas → 6 variantes de 6 piezas → registro de 6 piezas × 6 talles, todos completos y con gradación monótona; **re-asignación** a 3 variantes de 12 (con acentos y espacios: `Niño 4`) volvió a leer las 36 y rehizo todo; `falta_nombrar_variantes` desapareció; `pdf_guia` (camino vectorial del motor) y `nido` responden 200; **render del PDF partido pixel-idéntico al original (0/20.5M px)**; `prod_default` sin cambios (20 capas, 19 piezas). Molde de prueba borrado y activo restaurado a `prod_20260721_111945_7593`. **NO verificado:** la UI a mano dentro de la app (hay login y no se intentó pasarlo) — la consola del navegador queda limpia en la pantalla de login; y no se generó una tizada real (el molde de prueba no tiene arte).

- **2026-07-21 (5) — FIX: un molde con TODO en una sola capa quedaba inusable y sin aviso.** Reportado por el usuario: sube el molde desde "Mis artículos", queda cargado y **no se muestra nada** (422 en `/api/plantilla/deteccion`). **Causa:** su molde trae las 36 piezas en una única capa llamada **«Capa 1»**, que está en `CAPAS_SISTEMA` → 0 talles → la detección falla. Y **la herramienta de nombrar variantes tampoco la ofrecía**, porque sólo listaba capas que YA contaban como talle: el molde no tenía forma de arreglarse nunca. Ahora `analizar` ofrece las capas **candidatas** (con molde dibujado, aunque el sistema todavía no las cuente como talle) y devuelve `sin_talles`/`una_sola_capa`; la herramienta **se abre sola y avisa en naranja** cuando no hay ningún talle; con un solo talle propone «Único» en vez de una letra del medio de la curva. **Verificado sobre una COPIA del molde del usuario: antes 422 y 0 piezas; después de nombrar la capa, 36 piezas.** **Agujero de seguridad encontrado en el camino:** la guardia de moldes ajenos no cubría las rutas con el id **en la URL** (`/api/productos/<pid>/preview`, `/descargar_plantilla`) porque sólo miraba query y body — `_pid_de_request` ahora lee primero el pid del path (403 verificado). **Gotcha de diagnóstico:** el id que mostraba la consola del navegador (`prod 2.1945 7593`) era el id real truncado por el visor, no un id mal formado; y un `curl` de bash con acentos rompe el JSON (el navegador manda UTF-8 bien) — no confundir eso con un bug del sistema.

- **2026-07-21 (4) — HECHO: «Mis artículos» + subir mi propio molde desde el pedido (UI).** Ver §10.d. Frontend (`App.jsx`): pestañas Catálogo/Mis artículos en el paso Diseños, botón + modal de subida (crear con `propio:true` → `POST /api/plantilla` con `pid`), y la config del molde propio **reusando** Config→Moldería en modo `modoMiMolde` (sin Variables, con «← Volver al pedido» y «Indicar qué es cada pieza →» que abre el editor de nombrado que ya existía). **Cambio de fondo que no era obvio:** el paso **Arte** navegaba sólo por VARIABLE (`disenoVars[did][arteIdx]`), así que un molde SIN variables —que es exactamente el caso del molde propio— no tenía pantalla de arte; ahora hay `itemsArteDe(did)` (variables + moldes enteros) y `arteIdx` recorre eso; los 8 lugares que resolvían el molde del paso Arte (`moldesDeDiseno(disenoActivo)[arteIdx]`) pasan por ahí. **BUG REAL ENCONTRADO en el backend:** `GET /api/productos` derivaba `propio` sólo del dueño (`creado_por`) y **sin sesión no hay dueño** → corriendo sin login "Mis artículos" quedaba SIEMPRE vacío (feature muerta); ahora, sólo cuando no hay usuario ni dueño, vale la marca `propio` que dejó el alta. **Verificado por API** (crear propio → subir plantilla con `pid` → `propio:true`, 20 talles / 19 piezas por `?pid=`, molde de prueba borrado y activo restaurado a `prod_default`) y `npm run build` OK; la consola del navegador queda limpia en la pantalla de login. **NO verificado:** la UI adentro de la app (hay login y no se intentó pasarlo) — falta la prueba a mano del flujo completo subir → nombrar variantes → nombrar piezas → generar la tizada de un molde propio.

- **2026-07-21 (3) — Nombrar variantes + el molde activo deja de ser global + BUG del talle «0».** (a) Herramienta `variantes_molde.py` + `GET/POST /api/plantilla/variantes` + UI `NombrarVariantes` (Config→Moldería): ver §10.c. Verificado end-to-end con un fixture real (el molde del usuario con las capas renombradas a `Layer N`): 20/20 nombradas, registro rehecho, piezas detectadas (19), original intacto. (b) **`_get_active_producto_id` ya no depende del activo global** (pid de la request → sesión → global); verificado que se puede subir una plantilla a un `pid` puntual **sin activarlo** y que el molde del otro usuario no se toca. (c) **BUG REAL ENCONTRADO Y ARREGLADO: el talle «0» se perdía.** `CAPAS_SISTEMA` incluye `"0"` (por la capa por defecto de AutoCAD en los DXF), así que a un molde con curva de niños (0,1,2,4…) se le borraba un talle entero: el molde del usuario tiene **20 capas de talle y su registro tenía 19**. Ahora se decide por CONTENIDO (si la capa "0" tiene tantas formas como los otros talles, es un talle) y la regla vive en un solo lugar: `_talles_con_molde` la reusa de `_talles_de_plantilla` — estaban duplicadas y por eso el talle aparecía en el alta y desaparecía en la detección. **Pendiente para el usuario:** su registro sigue con 19 talles hasta que se rehaga (re-subir el molde o re-guardar las etiquetas); su `deteccion_cache` también quedó viejo (no se tocó por ser dato suyo).

- **2026-07-21 — RESUELTO: "al cargar una imagen da error" (colocar objeto = 500). Causa real: archivos TRABADOS, no el código de inyección.** Síntoma: `POST /api/productos/objeto_agregado/<id>/colocar` devolvía 500 genérico. Traza real: `PermissionError [WinError 5]` al `os.replace` del temporal sobre `arte.ai`. **Diagnóstico (lo que costó):** primero se asumió que el server tenía el arte abierto y se cerraron `mesa_rect_arte` y `mapeo_variantes_arte` → **seguía fallando**. La prueba que lo destrabó fue empírica: intentar el `os.replace` **desde un proceso externo y con el server muerto** → seguía denegado ⇒ el lock **no era del server**. Sondeando todos los artes: **4 de 5 trabados** (`dcvd`, `hgvbn`, `t5y6rt`, `tht`; libre sólo `nhgnhg`), con 24 procesos python zombis de sesiones viejas y sus handles de PyMuPDF colgados. **NO era OneDrive ni la ACL** (el `replace` entre archivos nuevos en la misma carpeta funciona). **Arreglo en dos capas:** (1) **el arte se versiona** — `inyectar_editable` lee la versión vigente y escribe `arte.v<N+1>.ai` + puntero `arte.ver`, sin `os.replace`, así que ningún lock puede romper la edición y **el archivo original del usuario nunca se toca**; `_ruta_entrada("arte.ai")` resuelve la vigente para todo el sistema y la subida de arte (`original=True`) hace `reset_versiones`. (2) **fin de las fugas de handles** — `motor_pedido` abre con `_abrir`/`_abrir_pike` (registran el documento) y `@app.teardown_request` → `MP.cerrar_abiertos()`; 29 llamadas migradas en 16 funciones que abrían el arte/la plantilla y nunca cerraban. Verificado: tras un request el archivo queda **libre**. **Además:** el endpoint ahora inyecta **todas las mesas en una sola pasada** (una versión, una capa OCG compartida) y **devuelve el motivo real** del fallo en vez de "no se pudo inyectar" (el `print` al log estaba bufferizado y ocultaba la causa). **Gotcha para la próxima:** si algo "no se puede guardar" en Windows, probarlo **desde afuera del server** antes de tocar código — el lock puede ser de otro proceso.

- **2026-07-21 (2) — Lo que rompió el arreglo anterior y lo que faltaba de la feature.** Tres cosas salieron a la luz al probar la app de verdad: **(a) `ValueError: document closed` (500 en `/api/arte/deteccion`).** El registro de handles era **global** y el server es multi-thread: el `teardown` de un request cerraba los PDFs que otro request estaba usando. Ahora es **por hilo** (`threading.local`) y los hilos de fondo (pre-warm, generación) van envueltos en `_en_hilo`, que cierra al terminar. Verificado con 12 requests concurrentes: 0 errores, y el arte queda libre igual. **(b) No se podía SACAR un objeto ya inyectado** — los botones "Quitar de pieza"/"Borrar" apuntaban al manifiesto, del que el objeto sale al colocarse: quedaba pegado para siempre. Se agregó `quitar_editable` + `POST /api/productos/editable_quitar` + botón "Quitar del diseño" (sólo para capas agregadas por el usuario, decidido comparando contra el arte original). Verificado: el arte vuelve **pixel-idéntico** (0 px de diferencia en las 3 mesas). **(c) Un objeto PNG se inyectaba pero NO aparecía en ninguna pantalla**: `extraer_editables` medía las capas sólo con `get_drawings()` (vectores). Se complementó con `get_bboxlog(layers=True)` (imágenes y texto), comprobando que los bboxes de los editables que ya andaban no cambian. Además: **nombre de capa único** al inyectar (dos capas homónimas dan un bbox unión y no se pueden mover por separado) y **DPI real** de la imagen al calcular su medida. **Error mío en el camino:** intenté "reparar" nombres duplicados renombrando OCGs y renombré capas legítimas del arte del usuario —incluida `Guia`, que si se rompe **se imprime**—; el versionado permitió revertirlo sin daño. El arte trae entradas OCG repetidas de forma legítima: **no tocar los nombres de capas existentes.**

- **2026-07-17 — BUG ABIERTO: "nombro una pieza y quedan otras nombradas" (diagnosticado, NO resuelto).** Reporte del usuario. **NO se nombran solas: se RENUMERAN.** `_renumerar(obj, gen)` (`App.jsx`, ~3798) filtra **TODAS** las piezas cuyo `nombreGenerico` == `gen` y las reescribe `gen 1..N`. Lo llama `nombrarSeleccionadas` (~3770), `renombrarGrupoNombres` y `toggleNombreEnPieza`. Efecto: al nombrar una pieza "Manga", una que ya se llamaba "Manga 3" pasa a "Manga 1" sin que el usuario la toque. **NO es un descuido: es un PARCHE de un bug peor** (comentario en `renombrarGrupoNombres`): el registro se guarda como **dict POR NOMBRE** → dos piezas con el mismo nombre **colisionan y se PIERDE una**; por eso renumeran todo para forzar unicidad. **CAUSA RAÍZ = la identidad por nombre** → esto es exactamente el síntoma de [[identidad-pieza-id-nombre]] (id estable + nombre genérico separados; **fases 1-2 backend HECHAS, falta la FASE 3: frontend + renombrar-por-id**). Arreglar el renumerado sin hacer la fase 3 reintroduce la pérdida de piezas por colisión. **Respuestas a lo que preguntó el usuario:** (a) entre MOLDES distintos NO colisiona (`etqNombres` es del molde en edición); (b) a las piezas ya nombradas SÍ se les cambia el nombre (el número) — ése es el bug. **Ver también** el hermano de este problema: `dedupePorNombre` (~3740) + `_genDeValor`/`_slotDeValor` — regla deliberada "un solo SLOT por NOMBRE" en las VARIABLES; como `nombreGenerico` borra el número final, "Manga 1" y "Manga 2" caen en el mismo slot y queda solo la última → síntoma "no me deja elegir más de una pieza para la variable" (reportado 2026-07-16; para 2 piezas que van juntas el camino previsto es el vínculo `juntas`). Ambos salen del mismo nudo: **identidad por nombre**.

- **2026-07-16 — HECHO: PILA DE APARIENCIAS (el texto respeta las capas de la Apariencia + el color original va atrás).** `_pasadas_personalizable` (motor_pedido.py) devuelve la lista **ORDENADA** de pasadas de pintado por (mesa, texto): `[{"t":"f"|"S","color":(op,[vals]),"w":float}]`, con stack `q`/`Q`. `extraer_personalizacion` la expone como `pl["pasadas"]` (se mantienen `colorn`/`trazo` para compat) y el estampado (`generar_pieza`, ~2965) re-dibuja el texto **una vez por pasada, en orden** → el color original queda atrás y cada capa de la apariencia encima, como Illustrator. Si `pasadas` es None cae al camino viejo (`colorn`+`trazo`) → ningún arte cambia salvo donde la pila se lee. **DOS GOTCHAS que costaron caro (NO reintroducir):** (1) el texto llega **GLIFO A GLIFO** (`Tj` por letra) → la clave NO puede ser el último `Tj` (un "nombre" quedaba bajo la clave `"e"`); se acumula y, si el arte lo dibuja 2 veces, queda `"nombrenombre"` — `_match_texto` igual lo encuentra (matchea por contención, ya estaba previsto para eso). (2) **NO depender del `ET`**: hay artes donde el `BT..ET` **envuelve** a la capa (el bloque de texto empieza AFUERA del `BDC /OC`) y adentro sólo están `scn`+`Tj` → el `ET` nunca cae dentro y no se guardaba nada (así fallaba la mesa 29). Se acumula por CAPA y se vuelca al salir (`EMC`). **VERIFICADO** (`rangos 3.ai`): 12/12 campos leen la pila; cambian SOLO los 4 que estaban mal — mesas 15/28/29 Número y 29 Nombre pasan de negro (el original TAPADO) al AZUL de la apariencia; mesas 1 y 5 siguen `[relleno, BORDE, relleno]`; sin regresiones en los artes de `entrada/`. **FALTA:** comparar el render contra Illustrator (el harness `scratchpad/verif_orden.py` dibuja el texto RECTO y el placeholder va sobre CURVA → 17.8% de residuo sin explicar). NO toca la ETIQUETA (halo propio, `_et`).
- **2026-07-16 — APARIENCIA de Illustrator: ANÁLISIS (mi primer diagnóstico fue ERRADO, ver abajo).** Síntoma del usuario: "si el nombre/número viene con una Apariencia de Illustrator (la que se usa para poner el borde DETRÁS de las letras) no la respeta". **ESTRUCTURA REAL** del arte (`rangos 3.ai`, pág. 4, capa Nombre — verificado volcando el content stream): son **TRES pasadas**, no dos: (1) `BT scn(0,0,0,1) Tj×6 ET` = el texto con su color ORIGINAL; (2) `q CS/CS0 SCN(0,0,0,0) w 22.097` + `S`×6 = la APARIENCIA, exportada como **TRAZADOS** (contornos vectoriales, NO texto) y con **solo trazo** (`S`, sin fill); (3) `BT..ET` = el texto **otra vez, encima de todo** (sin `scn` propio → hereda el fill tras el `Q`). Ese sándwich relleno→trazo→relleno es como Illustrator aplana "borde detrás de las letras": el último relleno tapa la mitad interna del trazo. **NETO = borde SOLO por fuera, letra llena** — que es lo que el motor YA hacía (`motor_pedido.py:2973`: trazo detrás + relleno encima). **ERROR MÍO (revertido, commit b5ea482):** leí solo 2 pasadas (filtré los ops y no vi la 3ª ni que la apariencia son paths) y di vuelta el orden (trazo encima) "para respetar el arte" → eso comía las letras = lo contrario de lo que el usuario diseña. **PENDIENTE:** con este arte los dos rellenos son del MISMO color (negro), así que el orden no explica el síntoma → la causa está en otro lado. Sospecha viva: si la apariencia trae su propio relleno de OTRO color, `_colores_personalizable` toma el PRIMER fill de la capa (el ORIGINAL) y nunca el de la apariencia. **Trampa del harness `scratchpad/verif_orden.py`:** `set_layer_ui_config(n, action=1)` es TOGGLE, no ON (0=ON, 2=OFF) — con `1` se apaga la capa que se quiere aislar y la referencia sale BLANCA (dio un falso "4.39% vs 24.06%" que medía tinta contra una hoja vacía). Ver [[personalizacion-curva-borde]]; la ETIQUETA no pasa por este camino (halo propio, `_et`).
- **2026-07-13 — FIX: la tizada mostraba solo la 1ª mesa cuando se parte en varias.** Síntoma del usuario: "dice 2 pág pero muestra 1 y falta un diseño". No faltaba nada: cuando la tizada no entra en 1 mesa (nesting `altura_max_cm` ~500cm/5m) se parte en varias PÁGINAS = varias MESAS físicas de tela; el PDF tenía las 2 con TODOS los modelos (verificado renderizando ambas: 10 modelos golero+jugador repartidos), pero la TARJETA del visor (App.jsx ~5665) mostraba solo `previews[0]` (1ª página) con un badge "N pág" → parecía que faltaban los modelos de las otras mesas. FIX: la vista de mesas ahora hace `flatMap` sobre `previews` → UNA tarjeta por PÁGINA, cada una con su preview y su alto REAL (badge "Mesa 1/2"). El motor reporta `alturas_cm` (alto de cada página) desde `componer_pdf_contorno` (nesting_contorno.py ahora devuelve `(consumo, alturas_cm)`); verificado `[499.1, 421.0]`cm. Commit ec61fcc.
- **2026-07-13 — AUDITORÍA variable-vs-molde (3 agentes) — PRINCIPIO DURO DEL USUARIO.** Regla: el MOLDE solo sirve para cargar/guardar piezas + configurarlas en variables/grupos + renombrado masivo; TODO el resto del sistema debe escalar con las piezas de la **VARIABLE** (9), NUNCA con las del **MOLDE** (135). Auditoría exhaustiva (motor/servidor/frontend). Confirmado que el grueso YA está bien: el pipeline pesado (`generar_pieza`/`piezas_de` filtra por `variante_piezas`), el visor del Arte (`MapeadorArteVisual` filtra por `vf.show`) y el editor escalan con la variable. FIXES aplicados: **MOTOR** — `generar_pedido` recalculaba POR TALLE (×19 en asignar_todo) estructuras que dependen solo del ARTE: (a) `extraer_editables(con_thumb=False)` en el motor (NO generar thumb/svg con `get_pixmap`/`get_svg_image`+toggles — eso solo lo usa el visor); (b) `extraer_personalizacion` memoizada por (arte,mtime) — `_PERS_CACHE`; (c) `mapeo_variantes_arte` memoizada — `_MAPEO_VAR_CACHE`. `_piezas_base` 2.8s→~1.4s/talle. VERIFICADO pixel-idéntico (maxdiff 0). **SERVIDOR** — `/api/plantilla/deteccion` acepta `?variante=` → filtra a las piezas de la variable (138→9, 135KB→21KB, 6.4×); backward-compat (sin variante = molde completo para etiquetador/renombrado); caché full de disco intacto (filtro post-caché). **FRONTEND** — `vfArte` nunca cae a `null` si hay variable activa (antes dibujaba las 135); pieza pre-seleccionada = 1ª de la variable. Commit 7912af9. PENDIENTES MENORES (bajo ROI, documentados): el front pasar `?variante=` a deteccion (server ya acepta); lista de desplegables Config→Diseño muestra 135; editor de editables barre `mapeoData.piezas`. Ver [[perf-render-multiproceso]].
- **2026-07-13 — PERF 3: el cargado seguía en 1:22 → 22s. LA CAUSA PRINCIPAL era de RED, no de generación.** ⚡ **DUAL-STACK IPv6**: en Windows `localhost` resuelve a `::1` (IPv6) ANTES que `127.0.0.1`, y el server escuchaba SOLO IPv4 (`0.0.0.0`) → CADA request a `http://localhost` pagaba **~2s de retry** (con ~40 requests al asignar variantes = >1min de puro timeout de red). GOTCHA que me costó: mis mediciones con `urllib` TAMBIÉN estaban infladas 2s/req por esto → ocultaban que el server ya era rápido. FIX (servidor.py arranque): `make_server` en 2 threads escuchando IPv4 (`0.0.0.0`) e IPv6 (`::1`) → `localhost` instantáneo. Medido: **2.08s/req → 0.04s/req** (navegador: 2000ms→25ms). El reloader se pierde con make_server → `TIZADA_RELOAD=1` para volver a `app.run` con auto-reload en dev (solo IPv4). Otros 2 fixes de esta ronda: (a) **caché a disco de `detectar_piezas`** por (mtime plantilla, talle) — `_deteccion_base_cached`, pre-generado en el pool junto con los renders (antes 19× `plantilla/deteccion` = 19×2.3s de `get_drawings` de TODO el molde; la deteccion NO depende de variable/diseño); `deteccion_cache/<mtime>_<talle>.json` (derivado, borrable). (b) **`_editables_cfg` ignora overrides vacíos** (`{v:{}}` != `None` hacía cache MISS → el preview REGENERABA cada talle en FASE 2 en vez de leerlo del caché). RESULTADO end-to-end (caché frío, localhost): **1:22 → 22s** (asignar_todo paralelo 18s + loop preview/deteccion de caché 4s). Commit c50b92c. Ver [[perf-render-multiproceso]].
- **2026-07-13 — PERF 2: asignar variantes EN PARALELO (ProcessPool) — el cargado bajó ~4-8x.** El caché de contornos (perf 1) no alcanzó y el `sin_prewarm` EMPEORÓ la una-mesa (le quitó el paralelismo del pre-warm). Investigado con fuentes (doc oficial PyMuPDF/pikepdf): **PyMuPDF NO es thread-safe** (puede crashear Python), el `_PIEZAS_BASE_LOCK` global es lo que evita el crash → la solución es **MULTIPROCESO, no threads**. Implementado (servidor.py): `ProcessPoolExecutor` PERSISTENTE (`_get_render_pool`, `min(cpu,6)` workers); worker top-level `_render_talle_worker` (spawn-safe: solo tipos simples, no cruza objetos fitz/pikepdf, hereda env por spawn, protegido por el guard `if __name__=="__main__"`); endpoint `POST /api/arte/asignar_todo` genera TODOS los talles en paralelo → caché en disco; `GET /api/arte/asignar_estado?job=` da el progreso. Front `asignarTodasLasVariantes`: llama asignar_todo + polling del progreso, luego pide cada talle (sale del caché) para cargarlo a la memoria del navegador (`_pvCache`). MEDIDO en el server (Windows, 12 cores, caché frío): una-mesa 42s→17s, RANGO 102s→12s (rango ≤ una-mesa). Verificado: renders del pool con diseño real, pixel-idénticos. Notas: (a) la 1ª asignación tras iniciar el server paga el spawn del pool (~5s), las siguientes reusan; (b) con `use_reloader=True` el pool se recrea en cada reinicio de código (OK); (c) el pre-warm bg de 1 thread sigue para la navegación individual. Commit 80a5769.
- **2026-07-13 — PERF: cargar el diseño en cada variante tardaba 5x más por rango (2:27 vs 26s).** El usuario notó que un arte POR RANGO tardaba ~5x más que uno de una mesa con la MISMA cantidad de variantes. Diagnóstico (perfilado): NO era el rango — era `extraer_piezas_mesa(base_doc, mesa, talle)` (saca las 135 piezas de la mesa del molde, `get_drawings` caro) llamado una vez POR PIEZA generada (9+) con los MISMOS args → extraía las 135 N veces. FIX (motor_pedido.py `_armar_base`): caché `_piezas_mesa_cache` por `(mesa, talle)` → 1 extracción, las piezas toman su índice. `generar_pedido` 2.4s→1.4s; `_piezas_base` 7.7s→2.8s (rango)/1.8s (una-mesa); VERIFICADO pixel-idéntico (maxdiff 0). 2º factor: la ventana "Asignando…" (`asignarTodasLasVariantes`) recorre TODOS los talles fg, pero cada request disparaba ADEMÁS el pre-warm bg del server (redundante, competía por `_PIEZAS_BASE_LOCK` y serializaba); ahora manda `sin_prewarm:true` y `arte_preview_piezas` no lo dispara. RESULTADO (19 talles, caché frío): rango 145s→66s, una-mesa 83s→64s (rango ≈ una-mesa). Commit 930ffd7. Optimización futura posible: paralelizar la generación de talles (hoy el lock global serializa).
- **2026-07-13 — BARRIDO del proyecto (auditoría + fixes).** Pedido del usuario "chequeá qué no quedó arreglado y arreglalo". 2 auditorías (features incompletas + flujo mapeo variable/rango). Resultado: las features grandes que las memorias marcaban "a medias" (multiples-disenos, capa-editable, mapeo-por-variable) están COMPLETAS — memorias viejas. FIXES aplicados: (1) **la tizada usaba un diseño viejo/vacío de la planilla** (causa REAL del "por rango no sale nada"): `addPrenda`/`removeFila` (App.jsx) ponían `disenosPedido[0]` en la columna Diseño en vez de `disenoActivo`, y las filas de localStorage quedaban pegadas → generabas jyghj (arte VACÍO) en vez del preparado. Ahora filas nuevas usan el diseño activo, e `irAPlanillaDesdeArte` sincroniza (1 diseño → todas las filas lo usan; varios → respeta los válidos). Commit 2ea53f9. (2) **identidad-pieza Fase 3**: `plantilla_etiquetas` (servidor.py) reescribía el registro sin refrescar `piezas.json` → `_piezas_de_variable` caía al fallback por idx; ahora regenera igual que `subir_plantilla`. (3) **Arte≠tizada con mapeo efectivo vacío**: si `_mapeo_efectivo(variable)={}`, el preview pasaba `None` al motor → modo CLÁSICO (mesa del molde) → divergía de la tizada; ahora `arte_preview_piezas` pasa la MISMA estructura por-variable que `/api/generar*` (modo separado + #rango activos con mapeo vacío). Verificado 225px→0px. Pre-warm alineado a la estructura (comparte caché). Commit 2c4e488. NO-fix (by-design): en artes #rango, `_mapeo_var` (rótulos) pisa a `por_variable` — es NECESARIO para que el rango resuelva la mesa por talle; el "por_variable autoritativo" aplica a artes de una mesa. Código muerto de baja severidad (`/api/generar` single inalcanzable, `cargarEditables`/`editableDisenos` huérfanos) se deja (sin riesgo).
- **2026-07-13 — Ventana "Asignando el diseño a cada variante…" (modelo mental del usuario).** Acordado con el usuario: al CARGAR el arte, el diseño queda colocado en TODAS las piezas y TODOS los talles — una sola espera, VISIBLE (ventana modal con "Variante X · n/N" + barra de progreso), y después navegar es instantáneo desde memoria. Front: `asignarTodasLasVariantes(mapeo)` (App.jsx) — corre AWAITED tras subir el arte (`cargarDisenoWizard`), pide el preview fg de cada talle + su geometría y los guarda en `_pvCache`/`_talleDetCache`; `cargarMapeadorOperario`/`_aplicarDetArte` ahora DEVUELVEN el mapeo aplicado (para usarlo sin esperar el re-render del estado). El caché en disco del server se mantiene (hace que re-abrir el programa no re-genere; el usuario pidió "memoria por diseño/variante que se renueva al cambiar el diseño" — las claves por mtime+config ya dan exactamente esa semántica). Commit ea50a5c.
- **2026-07-13 — FUERA el "estado neutro" (se quedaba pegado → molde vacío).** El flag `talleCambiando` (contornos neutros durante el cambio de talle) podía quedar prendido (su limpieza dependía de que corriera `cargarPreviewPiezas` con guardas) → el visor mostraba SOLO contornos sin ningún diseño (captura del usuario). LECCIÓN: no ocultar contenido detrás de flags transitorios — el placeholder YA dibuja el diseño CORRECTO del talle vía `mapeo_talles`, así que ocultarlo no aportaba nada y sí podía romper. Se eliminó `talleCambiando` por completo (visor + editor); `mapeoCargando` queda SOLO para la primerísima visita a una variable. + Cambio de VARIABLE instantáneo al revisitar: `_detArteCache` (`pid|diseño|variable` → deteccion) aplicado sincrónico en `cargarMapeadorOperario` (`_aplicarDetArte`), refrescado en background, invalidado al subir arte, actualizado al guardar mapeo; la geometría del talle guía también cacheada (`_talleDetCache` clave `pid|__guia__`). Commit 6e9f621.
- **2026-07-13 — Precarga con PRIORIDAD (fix "ahora está peor") + crash de pieza sin diseño.** La 1ª versión de la precarga hacía que el click del usuario ESPERARA detrás de la cola del pre-warm (lock global `_PIEZAS_BASE_LOCK` sin prioridad). FIX: `_piezas_base(prioridad="fg"|"bg")` — los pedidos bg (pre-warm del server + prefetch del front, que ahora manda `bg:true`) ceden el paso mientras haya un fg esperando (`_PB_FG_ESPERANDO`); el usuario espera a lo sumo UNA generación en curso. El prefetch del front además precarga primero los talles VECINOS del actual. VERIFICADO: pedir un talle sin caché en medio de la precarga = 3-8s (1 generación), no la cola entera (60s+). + FIX motor (`generar_pieza`): pieza SIN diseño en la variable (blank) crasheaba con `UnboundLocalError: sp` — `clave_pers` caía a la mesa del MOLDE y podía chocar de casualidad con una mesa del ARTE (pers['1']) → intentaba estampar sin escala; ahora pieza sin diseño ⇒ `ph={}` (nada que estampar). Commits: fc71f8d (este), 227fef1 (precarga), 6a27d65 / tag `checkpoint-antes-precarga` (rollback).
- **2026-07-13 — PRECARGA TOTAL de talles en el navegador (cambio de variante instantáneo).** Pedido del usuario: "cuando cargue el arte ya quede puesto en cada variante y cambiar sea instantáneo y 100% bien". Front (App.jsx): `_pvCache` (renders reales por clave pid|diseño|variable|talle|mapeo|edits, tope 300) + `_talleDetCache` (geometría `/api/plantilla/deteccion` por pid|talle) + `_prefetchTalles` (tras el 1er preview, baja EN BACKGROUND los renders+geometría de todos los demás talles; token `_prefetchTok` aborta si cambia el contexto; NO precarga con `editorTfs` sin guardar). `verVarianteOperario`: si el talle destino está en memoria → `setEtqData`+`setPreviewPiezas` en el MISMO frame (swap instantáneo, sin neutro ni fetch); si no (1ª vez) → neutro breve como antes. `cargarPreviewPiezas`: cache-hit SINCRÓNICO antes del primer await (para que React lo batchee sin frame en blanco). Invalidación: subir arte nuevo limpia `_pvCache` (`cargarDisenoWizard`); mapeo/edits van en la clave. ⚠️ GIT: repo inicializado hoy — tag `checkpoint-antes-precarga` (6a27d65) = estado ANTERIOR a esta feature; para volver atrás: `git checkout checkpoint-antes-precarga -- frontend/src/App.jsx && cd frontend && npm run build`. El .gitignore EXCLUYE datos/ entrada/ trabajos/ (regla dura: datos del usuario nunca se versionan/revierten).
- **2026-07-13 — Cambio de TALLE sin estados sucios (2ª vuelta del flash).** El `mapeoCargando` solo cubría el cambio de VARIABLE; al cambiar de TALLE seguía el glitch (diseño del talle anterior → editables "flotando" sin fondo → recién ahí el real). FIX: estado `talleCambiando` — se prende al TOCAR un talle (`verVarianteOperario`, solo Pedidos→Arte y solo si el talle realmente cambia; se apaga si el fetch falla) y se apaga cuando LLEGA el preview del talle nuevo (`cargarPreviewPiezas` finally, con guard `_pvReq`). Mientras está prendido: `MapeadorArteVisual` (prop `cargando = mapeoCargando || talleCambiando`) y el editor de editables (fondo `_mesa.svg` + `_objsEd`) dibujan SOLO contornos neutros. Con el pre-warm de talles el neutro dura lo que tarda el caché (instantáneo). Frontend-only (dist).
- **2026-07-13 — Editor de editables POR GRUPO del arte + fin del flash al cambiar de variable.** (a) **Editor por rango/talle**: si el arte tiene mesas `#rango`/`#talle`, el editor de editables agrupa los talles por FIRMA (qué mesa usa cada pieza en ese talle → `mapeo_talles`): chips "Rango del arte" (XS–L / XL–3XL / 4XL–6XL / 1–16); elegir uno muestra SOLO los editables de ese grupo (`_objsEd`/`_objsUnicos` — antes salían Logo/Escudo repetidos ×4 en la lista), el alcance por defecto = los talles del grupo, y "Ver talle" navega dentro del grupo. Arte de una sola mesa → 1 grupo → picker de variantes normal (sin cambios). Guardar/Volver iteran los objetos ÚNICOS del grupo. (b) **Flash "otro diseño" al cambiar de VARIABLE**: mientras cargaba la deteccion de la variable nueva, el visor dibujaba con el `mapeoValores`/`mapeoData` de la ANTERIOR. FIX: estado `mapeoCargando` (set al entrar a `cargarMapeadorOperario`, clear en finally) → prop `cargando` de `MapeadorArteVisual`: no dibuja diseño/editables/preview con datos viejos (contornos neutros hasta tener el mapeo nuevo). Frontend-only (dist).
- **2026-07-13 — 3 FIXES para artes POR RANGO (#talle/#rango) + color de personalización.** (1) **Número BLANCO (bordes "no respetados")**: `_colores_personalizable`/`_trazo_personalizable` (motor) leían el color linealmente e IGNORABAN `q`/`Q` — Illustrator dibuja el halo dentro de `q..Q` y el texto tras el `Q` (estado restaurado) → en el frente el fill del "00" se leía CMYK blanco (el archivo pinta negro). FIX: stack q/Q en ambos parsers (el color/trazo es estado gráfico). VERIFICADO: `colorn` mesa 28 blanco→negro; render del frente talle 10 = "00" negro con borde blanco (igual a la espalda). Cache-key `v3`→`v4`. (2) **Editables "no editables" con rango**: los objetos viven en mesas por-talle (10/19/28) que no están en el mapeo default → `mesa2pieza` (get_editables) no les daba pieza → el editor no los listaba. FIX: `mesa2pieza` suma las mesas de `mapeo_variantes_arte` (setdefault). El motor ya aplicaba bien los transforms por `_mesa_a`. (3) **"Primero muestra el 6XL al navegar talles"**: el placeholder JS y el fondo del editor usaban `mapeoValores[pieza]` = mesa default = 1er rango del archivo (4XL-6XL). FIX: deteccion devuelve `mapeo_talles` ({pieza:{talle:mesa}}) y el front (MapeadorArteVisual + editor bg) resuelve la mesa del TALLE en vista; + PRE-WARM en background del resto de talles al pedir un preview (`_PREWARM_EN_CURSO` dedup) → navegar talles = caché de disco, instantáneo. VERIFICADO: talle 12 `cache:true` tras el warm. NOTA de datos: en el arte fbfdx el rango 4XL-6XL NO tiene capas Número/Nombre/Editable (mesas 1-9, gap de autoría del arte, no bug): esos talles salen sin número/editables hasta que el usuario las agregue al .ai.
- **2026-07-13 — FIX: en el visor del Arte las piezas de un toggle NO-default (mangas largas) salían con el diseño de OTRO rango.** Síntoma (arte `#rango` fbfdx, talle 10): todo verde (#1-16) menos las mangas LARGAS celestes (#4XL-6XL). CAUSA: `_piezas_base` generaba con UNA prenda de muestra y sin valor de manga → toggle default "corta" → `partes_de` excluía las mangas largas del render real → el visor caía al re-dibujo JS de placeholder, que usa el mapeo default plano (mesa 7/9) SIN resolver `#rango`. La TIZADA real siempre estuvo bien (el motor resuelve el rango). FIX (servidor.py `_piezas_base`): una fila de muestra EXTRA por cada opción restante de cada toggle (columnas role="manga" del template, opciones de la regla/columna) → el motor arma TODAS las piezas de la variable y el visor muestra siempre el render real (invariante Arte = tizada). Cache-key `v2`→`v3`. VERIFICADO: preview v_jl31t5b talle 10 ahora trae las 9 piezas y las mangas largas dan color EXACTO al de la mesa 30 (verde, dist 1) vs celeste (dist 184).
- **2026-07-13 — MAPEO POR VARIABLE (regla dura del usuario: "nunca más por molde").** El mapeo del arte pasa a manejarse POR VARIABLE en todo el flujo. (1) STORAGE: `mapeo_arte.json = {mapeo: base, por_variable: {v_xxx: {pieza: mesa}}}` (compat: datos viejos = solo base). (2) SERVIDOR: helpers `_piezas_de_variable` (resuelve por pieza_id estable, fallback idx@guía), `_alcance_variables` (unión), `_mapeo_estructura`, `_mapeo_efectivo` (el de la variable AUTORITATIVO, si no la base); `/api/arte/deteccion?variante=` devuelve el mapeo efectivo + `piezas_variable`; `/api/arte/mapeo` recibe `variante` (guarda en `por_variable`, base y `prod["mapeo_arte"]` fijo por MERGE semilla, validación acotada con `piezas_scope`, pre-warm con el mapeo efectivo de cada variable); subir arte puebla `por_variable` y mide completitud/faltan contra el ALCANCE de las variables (no las 135 piezas del molde); `/api/generar` y `/api/generar_multi` pasan la estructura completa y los avisos "sin diseño" se calculan con el mapeo efectivo de la variable de CADA fila. (3) MOTOR: `generar_pedido` acepta ambos formatos (plano compat / por variable), `mesa_arte(pieza, talle, variante)` resuelve por la `variante_clave` de la prenda (precedencia #talle > #rango > variable > base; sin base → unión de variables para filas sin variable); `validar_arte_separado(piezas_scope=)`. (4) FRONT: `persistirMapeo` manda `variante: verVariante`; `cargarMapeadorOperario`/`abrirMapeoOperario`/`cargarMapeoArte` piden deteccion con `variante` (el efecto del paso Arte re-corre al cambiar de variable → recarga SU mapeo). VERIFICADO: motor pixel-idéntico formato viejo vs nuevo (maxdiff 0); pv[vA] cambia solo vA (Frente 18 mesa 2→1: diff>0; vB intacta: 0); quitar pieza del pv NO se resucita por la base; endpoints en server copia 8060 (validación "8/9 — faltan Cuello 25" acotada a la variable, archivo con `por_variable`, otra variable no afectada); `generar_multi` end-to-end listo con aviso correcto por variable. Ver memoria [[mapeo-por-variable]].
- **2026-07-13 — Nueva sección "CASO 1: cómo ejecutar el proyecto"** al inicio del mapa (pedido del usuario): pasos verificados para levantar el localhost con los moldes REALES (liberar 8050 → server con env `TIZADA_*` reales en background → verificar `/api/productos` → abrir navegador). El sandbox del launch.json queda solo para chequeos sin datos reales.
- **2026-07-10 — FIX: arte con rótulos `#rango` no colocaba NINGÚN diseño.** Un arte "separado" con mesas rotuladas `#XS-L Frente`, `#4XL-6XL Frente`, etc. (una mesa por pieza por rango) no mapeaba nada: `mapeo_por_nombre` (el auto-mapeo que corre al SUBIR el arte y como fallback en la generación) exige que la línea ENTERA sea el nombre de pieza vía `_match_piezas`, y el prefijo `#<rango> ` rompía el match → devolvía **0 piezas** → mapeo vacío → (a) el visor no colocaba diseño (piezas en blanco) y (b) la generación se salteaba los rangos (el motor solo activa `mapeo_variantes_arte` `if mapeo_arte` NO está vacío, línea ~2703). FIX (motor_pedido.py `mapeo_por_nombre` ~2081): antes de matchear, se saca el prefijo con `re.sub(r"^\s*#\S+\s+", "", t)` ("#4XL-6XL Frente" → "Frente"). El `#` en sí lo sigue resolviendo `mapeo_variantes_arte` aparte (pieza→{talle:mesa}, precedencia exacta>rango>default). VERIFICADO con el archivo real del usuario (`rangos.ai`, 36 mesas, rangos `XS-L`/`XL-3XL`/`4XL-6XL`/`1-16`): auto-mapeo 0→**123** piezas; `mapeo_variantes_arte` correcto (Frente XS→mesa19, XL→mesa10, 4XL→mesa1, 1→mesa28). Los 12 no mapeados son piezas de OTRAS variables (costadillo) que no están en ese arte (normal). Como el mapeo ahora es no-vacío, el motor activa los rangos → visor y tizada colocan el diseño de cada rango por talle. El usuario debe RE-SUBIR el arte para que corra el auto-mapeo arreglado. Ver [[plantilla-diseno-por-variante]].
- **2026-07-10 — "Descargar guía" ahora baja un `.ai` NATIVO con CAPAS reales.** (Reemplaza el intento OCG, que Illustrator aplanaba a "Capa 1" — confirmado.) La guía se genera como `.ai` LEGACY (AI 8 / EPS con marcadores `%AI5_BeginLayer`/`Lb`/`Ln`/`LB`), que Illustrator SÍ abre con capas nativas (confirmado por el usuario). Motor: `ai_guia_medidas(...)` (nueva) + helpers `_ai_esc/_ai_path/_ai_text/_ai_layer/_segs_bbox`; comparte la geometría con el PDF vía `_guia_capas_data()` (extraída de `pdf_guia_medidas`, PDF verificado idéntico tras el refactor). Capas: `molde` (contornos + recuadro del diseño, trazo), `guias` (nombres de pieza como TEXTO VIVO), y `diseño` + columnas de texto/número (`capasArteNombres()` en el front) creadas VACÍAS. Coord AI = PostScript y-arriba (sin flip). **EMPAQUETADO COMPACTO**: el layout real del size-run es enorme (270"+); se reacomodan las piezas en grilla a 1:1 (shelf-packing por `_segs_bbox`). GUARD: si a 1:1 excede 16000pt (≈227", máximo de Illustrator) → error 422 "elegí una VARIABLE" (el molde completo de una camiseta = 138 piezas = 865", no entra; por variable ~9 piezas = 69×89" sí). Endpoint `/api/plantilla/pdf_guia?formato=ai` (mimetype `application/postscript`, filename `guia_<molde>.ai`); el PDF sigue para "Descargar base" (limpio). Front `descargarPdfGuia` ahora hace fetch+blob (para mostrar el error de tamaño como aviso, no JSON en pestaña) y el botón dice "Descargar guía .ai". VERIFICADO end-to-end: 200 application/postscript por variable, 422 molde completo; el usuario confirmó en Illustrator las 5 capas + contornos + nombres como texto vivo. LIMITACIÓN: modo 'talle' multipágina no soportado en .ai (usa un solo talle guía). Ver §"Cómo armar el .ai" (modal capas).
  - **DECISIÓN de formato (2026-07-10):** se evaluaron alternativas por pedidos del usuario (2023+, sin aviso de actualizar, mesas por pieza, espacio de trabajo grande). Matriz: **SVG** = moderno/limpio + grupos nombrados + texto vivo, pero UNA mesa; **PDF multipágina** = una mesa por pieza pero aplanado (sin estructura); **.ai legacy** = capas reales pero con aviso "actualizar" + espacio chico + una mesa; **.ai moderno** (tendría todo) = formato secreto de Adobe, NO generable. NO existe un formato generable con las 3 (mesas + estructura + moderno). El usuario **eligió .ai legacy (capas reales)** aceptando el aviso y el espacio chico. Pendiente OPCIONAL: intentar suavizar el aviso (versión en cabecera / texto) y el tamaño de mesa.
- **2026-07-10 — "Descargar guía": el PDF trae las CAPAS del arte pre-creadas (OCG). [SUPERSEDED por el .ai nativo de arriba]** El PDF de guía ahora crea capas OCG con los nombres del arte: `molde` (contornos+recuadro+título), `guias` (los NOMBRES de pieza), y una por cada capa del arte (`diseño` + columnas de texto/número de la planilla: nombre, número…). Las que tienen contenido lo llevan; las vacías (diseño, nombre, numero) se crean igual con un marcador mínimo invisible (un OCG sin contenido no aparece en Illustrator). Cambios: motor `pdf_guia_medidas(..., capas=None)` (crea OCGs con `doc.add_ocg`, asigna con `oc=` en `_segmentos_vector`/`draw_rect`/`insert_text`); endpoint lee `capas` (JSON array); front `capasArteNombres()` (misma lógica que el modal "Qué va en cada capa": diseño+guias+columnas nombre/numero) y `descargarPdfGuia` lo pasa. VERIFICADO a nivel PDF: `get_ocgs()` → molde/diseño/guias/nombre/numero; diferencial de render confirma contorno↔molde y nombres↔guias. **OJO** (nota vieja del código, línea ~1889, ahora matizada): puede que Illustrator APLANE los OCG al abrir el PDF → el usuario debe confirmar que aparecen como capas. Si no, habría que ir a un .ai con capas nativas (mucho más complejo). `capas=None` = comportamiento viejo (sin capas). El "Descargar Base" (limpio) no pasa capas.
- **2026-07-10 — Plantilla 'rango': guía SIEMPRE dentro del rango + se sacó "Cargar Arte".** (a) En "Cómo se adapta el diseño" → "Por rango", la GUÍA (base del cálculo + variante que se ve en el visor) ahora se mantiene SIEMPRE dentro del rango elegido: `toggleRango` y `cambiarConfigMedida('rango')` — si la guía actual (`etqData.talle_ref`, por defecto la `variante_guia` del molde, ej. M) queda FUERA del rango, se auto-elige la 1ª del rango por orden de archivo vía `verVarianteOperario(enOrden[0])`; si ya está dentro, no se toca. Así los cálculos (`cajaDe` usa `p.w_cm/h_cm` = la guía) y el visor (filtrado por `verVariante`) muestran las piezas de esa variante de la variable. `toggleRango` pasó de `setRangoMedida(prev=>…)` a estado directo para poder decidir la guía con el rango nuevo. VERIFICADO en navegador: rango {16} con guía previa 4 → detección `talle_ref=16`, chip "Guía del rango" = 16 resaltado. (b) Se ELIMINÓ el botón "Cargar Arte" de la pestaña Plantilla (Config→Moldería→Plantilla) y su `<input>` local (el del flujo Pedido→Arte, otro `<input ref={fileInputArteRef}>` ~4908, queda intacto). Frontend-only (solo Ctrl+F5).
- **2026-07-10 — "Descargar Base" (Config→Plantilla) por VARIABLE.** Antes bajaba el `.ai` crudo del molde COMPLETO. Ahora: si hay una VARIABLE elegida (`verVariante`) → baja SOLO sus piezas como PDF "base limpia" (contornos del molde, SIN recuadro del diseño, SIN nombre de mesa, SIN medidas); sin variable → el `.ai` completo (como antes). Cambios: motor `pdf_guia_medidas(..., limpio=False)` (nuevo flag: salta recuadro+nombre y no extiende el bbox con la caja del diseño; título "Base (contornos)"); endpoint `/api/plantilla/pdf_guia` lee `limpio` (filename `base_molde.pdf`); front `descargarBase()` (verVariante → `pdf_guia?piezas=…&limpio=1`, si no → `descargar_plantilla`); el botón pasó de `<a>` a `<button>` con label "Descargar base (variable)". Distinto de "Descargar guía (solo esta variable)" que SÍ trae recuadro+nombres (para mapear el arte). VERIFICADO: base limpia MP1-A = 10 trazos, 0 recuadros cyan, 1 texto (título), solo sus 9 piezas; guía normal = 9 recuadros+10 textos; compat sin `limpio` intacto. Requiere REINICIAR el server (cambio Python).
- **2026-07-10 — FIX: en Config→Etiqueta "volvía sola a la primera" variable.** Al cambiar de variable (tarjetas MP1-A…) en Config→Moldería→Etiqueta, saltaba de vuelta a la primera. CAUSA: el efecto del flujo Pedido→Arte (App.jsx ~3484) estaba guardado SOLO por `pedidoPaso!=='arte'`, pero al pasar a Configuración **`pedidoPaso` NO se resetea** (queda 'arte'); como el efecto tiene `verVariante` en sus deps y hace `setVerVariante(claveDelArte)`, cada click en Config lo pisaba con la variable del arte. Solo se dispara si venís del paso Arte (por eso costaba reproducir: entrando directo a `/admin`, `pedidoPaso` es 'moldes' y no corría). FIX: guardar el efecto también por `activoTab==='pedidos'` (`if (activoTab !== 'pedidos' || pedidoPaso !== 'arte') return;`) + `activoTab` en las deps. VERIFICADO en navegador (copia de datos, puerto 8060): con `pedidoPaso='arte'` reproducido el bounce, y tras el fix MP1-A1 y "con costadillo" quedan seleccionadas. Nota: otros efectos del arte (cargarPreviewPiezas, cargarEditablesPedido) también corren en Config con pedidoPaso='arte' pero son inofensivos ahí (no tocan `verVariante`).
- **2026-07-10 — Panel "Diseños" (Pedido→Arte): sin desplegable, thumbnails completos y auto-guardado.** (a) **Se quitó el `<select>`** de elegir pieza (redundante: se toca la pieza en el molde); queda una guía breve. (b) **Thumbnails con el editable**: la miniatura de cada mesa ahora es un `<svg>` = mesa (editables ocultos) + los objetos editables de esa mesa (`editablesRaw.filter(o=>o.mesa===m.mesa)`) superpuestos en su posición ORIGINAL (fracción `bbox_mu`/`mesa_rect`) → se ve el diseño COMPLETO. Si la mesa no tiene editables, cae al `<img>` de antes. Nuevo prop `editablesRaw={editableData?.objetos||[]}`. (c) **Auto-guardado del mapeo**: arrastrar/tocar/quitar un diseño persiste solo (`onMapeoChange={guardarMapeoAuto}` → `setMapeoValores` + `persistirMapeo(next,{silencioso})`); se **eliminó el botón "Guardar mapeo"**. `guardarMapeo` refactorizado sobre `persistirMapeo(valores,{silencioso})`. El componente usa `aplicarMapeo = onMapeoChange || setMapeoValores` (fallback sin auto-guardado). NO se tocó el mapeador legacy con desplegables (~línea 6360, otro panel).
- **2026-07-10 — Editor de editables: persistencia al reabrir, botones y deshacer/rehacer.** (a) **Re-entrar muestra lo editado**: `cargarEditablesPedido` ahora NO pisa `editorTfs` si se reabre el MISMO contexto (`editorCtx` = pid|diseño|variable) con ediciones en memoria; y el botón "Objetos editables" (App.jsx ~4867) pasa `verVariante` (antes iba sin variante → releía base '*' vacía → perdía lo editado). (b) **Botones nuevos**: "Volver al diseño principal" (todos los objetos → identidad en el alcance, deshacible), "Deshacer"/"Rehacer", "Cerrar" (era "Guardar como base" → ahora solo cierra) y "Guardar" (era "Listo" → ahora persiste TODOS los objetos por variable+alcance vía POST `/editables` y recién ahí cierra). (c) **Undo/redo + Ctrl+Z**: historial a nivel componente (`editorHist` ref = pila de snapshots de `editorTfs`, `histReset/histCommit/editorUndo/editorRedo`); commit al soltar el arrastre (`onUp`) y en "Volver"; keydown Ctrl+Z / Ctrl+Y|Ctrl+Shift+Z con el modal abierto. Ícono `reset` agregado a `Icon`. Frontend-only (dist). Nota: "Volver" resetea en memoria; si no se "Guarda", al cambiar de variable y volver se relee la base persistida.
- **2026-07-10 — Editable: MOVER en COORDENADAS DEL DISEÑO + fondo real + talle guía.** El objeto editable ES una capa del diseño → su espacio natural es el del DISEÑO. La BASE ya era design-relative (`fcx/fcy`) pero el MOVIMIENTO `dx/dy` se medía contra la PIEZA (mezcla de espacios). Ahora TODO es design-coord: (1) MOTOR `_matriz_editable` (motor_pedido.py ~1655) `tdx = dx * pos.get("awf",1.0) * W` (antes `dx*W`) = ancho del DISEÑO en la pieza; `_pos_en_pieza` (~1638) devuelve `awf`. `tdy=-dy*H` sin cambio (alto-diseño=H por cm_encajar). (2) EDITOR `centerOf` (App.jsx ~4982) `cx=imgX+(fcx+tf.dx)*imgW`, helper `_imgDim` (`imgW=aspecto*p.ph`, `imgX=p.px+(p.pw-imgW)/2`); `onMove` divide por `imgW/imgH`; `start` guarda `imgW/imgH`. (3) OVERLAY del arte (~768) `cx=imgX+(o.fcx+o.dx)*imgW`. (4) FONDO del editor (~5057): dibuja el SVG de la mesa mapeada (editables ocultos) recortado al contorno + objetos draggables encima. (5) TALLE GUÍA (~5041): chips `{_selT.length>1}` → `setEditableTalle(t)+verVarianteOperario(t)` (solo para ver). VERIFICADO: no-regresión identidad = **0 px**; move dx=0.15→269.36pt=0.15·awf·W (awf=1.162); **consistencia editor↔motor** ambos en la fracción `(1-awf)/2+(fcx+dx)·awf` (WYSIWYG). **CORRIGE** el entry de abajo "colocación EXACTA": `dx/dy` YA NO es fracción de la PIEZA sino del DISEÑO (`*imgW/*imgH`).
- **2026-07-10 — Editor de editables: colocación EXACTA (WYSIWYG).** El editor modal ubicaba el objeto con `o.pos` = `_pos_en_pieza` calculado en el talle GUÍA y en la pieza donde se REGISTRÓ el objeto (ej. "Frente 9") → corrido cuando la variable usa otra pieza ("Frente 18") o se ve otro talle (la fracción cambia por talle: escudo M=0.712, XL=0.696). FIX (App.jsx `centerOf` ~4977): usa la fracción del objeto DENTRO del diseño (`fcx/fcy` de `bbox_mu/mesa_rect`) mapeada con el encaje del diseño en la pieza ACTUAL (`imgW=aspecto*p.ph`, centrado), y `dx/dy` en fracción de la PIEZA (`*p.pw/*p.ph`), IGUAL que el motor `_matriz_editable` (`tdx=dx*W`). PROBADO en Python: `fcx`-center == `_pos_en_pieza` center EXACTO en M/1/XL. También corregido el overlay del arte (~768) para que `dx` use `p.pw` (no `imgW`). Confirmado además: re-editar una variable SÍ muestra lo guardado (`get_editables` devuelve el transform de esa variable; otra variable = vacío, no hereda). UNIDAD `dx/dy` = fracción de la PIEZA (no del diseño).
- **2026-07-10 — TERMINOLOGÍA: VARIABLE ≠ VARIANTE.** El usuario distingue: **VARIABLE** = la selección de piezas / modelo (MP1-A, con costadillo) = qué piezas; **VARIANTE** = el TALLE (M, 1-16) = el tamaño. OJO: el código está CRUZADO — `verVariante`/`prod["variantes"]` (v_xxx) guardan en realidad la VARIABLE; y "variante" como palabra también se usa para TALLE (`variante_guia`, `verVarianteOperario(talle)`, el picker "Elegí las variantes" muestra talles). Grupo = conjunto de piezas; Conjunto = sub-armado con nombre. (Ver §5, corregido.)
- **2026-07-10 — Posición del EDITABLE independiente POR VARIABLE.** Antes la posición se guardaba por (diseño,objeto,talle) → compartida entre todas las variables (mover el escudo en MP1-A lo movía en todas). Ahora se guarda por **(diseño, VARIABLE v_xxx, objeto, talle)**. Cambios: `editables_cfg` del motor pasa a `{variable:{objeto:{talle:tf}}}` (motor_pedido.py: `_editados_nombres` unión entre variables ~2354, `_armar_base` resuelve `_ecfg.get(variante) or _ecfg.get("*")` ~2586); `_editables_cfg` (servidor.py ~1502) produce ese formato + compat viejo→`"*"`; `set_editable`/`get_editables` con `variante`; front `guardarBase` manda `variante:verVariante`, `cargarEditablesPedido(...,verVariante)`, `cargarPreviewPiezas`/`_edoverride` envuelven `{[verVariante||'*']: editorTfs}`. Compat: formato viejo (sin nivel variable) → clave `"*"` (base compartida). VERIFICADO (motor + backend): escudo movido en v_jl31t5b (MP1-A) → dif>0; en v_emtd907 (MP1-A1) misma pieza Frente 18 → dif=0 (base, no afectado). Cache-key ya incluye variante+edit_cfg → editar una variable regenera (invalida las otras, inofensivo).
- **2026-07-10 — El preview del Arte sigue el TALLE que se ve (no siempre M).** `cargarPreviewPiezas` no mandaba talle → el preview se renderizaba SIEMPRE en el talle guía (M). Si editabas un editable en el rango 1–16 (el editor cambia el arte a talle 1 vía `verVarianteOperario`), el preview seguía en M → M ∉ 1–16 → la edición no se veía. Fix: `cargarPreviewPiezas` manda `talle: etqData?.talle_ref` (App.jsx:3533) + `etqData?.talle_ref` en las deps del efecto (3548). VERIFICADO: en talle 1 el escudo movido SE VE; en M (no editado) queda pixel-idéntico. UNIDADES del editable: `dx/dy` son FRACCIONES del tamaño de la pieza (App.jsx:4977/4981 `*p.pw` / `/p.pw`); el motor (`_matriz_editable`) interpreta igual → fidelidad editor↔motor OK (un dx grande = varios anchos de pieza = se va de la vista). SCOPING del editor de editables: piezas y objetos SÍ acotados a la variante (`verVariante`→`varianteFiltro`→`_piezasEd`, App.jsx:4958-4961); los TALLES son los 19 del molde (la variante no define rango); la POSICIÓN se guarda por (diseño,objeto,talle) → compartida entre variantes (si se quisiera por-variante, sería cambio mayor).
- **2026-07-10 — Editable movido se ve en el ARTE (preview) sin guardar como base.** La cadena editar→tizada YA estaba OK (el override per-pedido `_edoverride` llega a `generar_multi`), pero editar→arte estaba roto: el preview `_piezas_base` usaba `override=None` y el front no le mandaba `editorTfs`; y el visor tapa el overlay `editorTfs` cuando hay preview real (`!pv`) → el arte mostraba la posición BASE, no la edición. Fix: (1) `cargarPreviewPiezas` (App.jsx:3533) manda `editables: editorTfs` + `editorTfs` en las deps del efecto (3548); (2) `/api/arte/preview_piezas` lee `editables` (servidor.py:1276) y lo pasa a `_piezas_base(..., override)`; (3) `_piezas_base` (servidor.py:1177) usa `_editables_cfg(prod, diseno, override)`. La clave de caché ya hashea `edit_cfg` → un override distinto regenera solo. VERIFICADO: mover el escudo cambia el render del Frente (base vs override distinto, escudo reposicionado). Nota: el editor modal usa su propio `_matriz_editable` (JS); el arte-preview y la tizada usan el del motor (Python) → arte-preview = tizada garantizado; fidelidad editor-vs-motor es otra cuestión.
- **2026-07-10 — La tizada toma el diseño del ARTE.** Antes la planilla usaba `disenosPedido[0]` como diseño default de la columna y `default_diseno`, y `generar_multi` hacía fallback al 1º diseño con arte (`_con_arte[0]`) → la tizada podía usar un diseño distinto al que editaste en el Arte (síntoma: el mapeo manual "no salía" / salía en un solo talle). Fix (3 cambios coordinados): (1) App.jsx:1467 la columna "Diseño" arranca con el nombre de `disenoActivo`; (2) App.jsx:3367 `default_diseno = disenoActivo`; (3) servidor.py:2182 el fallback prefiere `default_diseno` (el del Arte) si tiene arte, si no el 1º con arte. VERIFICADO: fallback ahora resuelve a `vfvsfd` (antes `hjn`), y `vfvsfd` genera con diseño en M/L/XL. Ver [[generar-un-solo-talle-diseno]].
- **2026-07-09 — Arte = tizada (un solo sistema).** Fase 1: caché en disco del render del motor por pieza (`_piezas_base` + `piezas_cache/`), el visor del Arte lo muestra (se elimina el re-dibujo JS como fuente). Fase 2: `generar_pieza` partida en `_armar_base` (cacheada por pieza/talle/variante) + estampado por prenda; **verificado pixel-idéntico**. Ver [[arte-wysiwyg]].
- **2026-07-09 — Vivos = mapeo manual.** Se eliminó la auto-herencia de vivos huérfanos en `generar_pedido` (~2520). Sin mapear = blanco consistente Arte/tizada.
- **2026-07-09 — Preview con texto de muestra.** `_piezas_base` pasa `pers` real + nombre/número de muestra; cache-key v1→v2. Fix del talle en molds sin columnas.
- **2026-07-09 — Fix "Guardar como base" del editable.** `_mid` con fallback a `productosCat.activo`; `_selT` no pierde el rango; `guardarBase` con guarda dura. (Bug: guardaba en el molde equivocado con talles vacíos.)
- **2026-07-09 — Doble contorno del visor** sacado (con `pv`, pieza mapeada → strokeWidth 0).
- **2026-07-09 — Auditoría molde-vs-variable** (ver §10).

> _(Antes de esta fecha: ver git/memorias. Este archivo se creó el 2026-07-09 como cerebro consolidado.)_
