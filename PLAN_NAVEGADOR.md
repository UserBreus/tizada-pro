# PLAN: LO PESADO SE HACE EN EL NAVEGADOR — el servidor sólo guarda y entrega

> Decisión del usuario (2026-09-17), textual: *«quiero que lo puedan usar cientos de personas a la
> vez, y el servidor no es fuerte, así que debemos hacer que no dependa del servidor»* → *«me tiro por
> que todo lo pesado lo use el navegador de la persona, que dependa de los componentes de la PC que
> lo levante; el servidor sirva para guardar y enviar las cosas; quien no tenga la potencia no podrá
> enviar»* → *«que cargar el molde haga toda la configuración y vaya armando un paquete; después de
> tener pronto le dan a un botón Guardar y envía el paquete: una lógica profesional»*.
> Descartado para siempre: la app de escritorio y máquinas ayudantes. Todo por el navegador en
> https://tizadapro.user.com.uy/ (VPS chico de Hostinger).
>
> Este documento es el plan **completo, de la etapa 0 a la última**, con la lógica y el código de
> cada paso. Se ejecuta en orden, sin saltear etapas, y **cada etapa termina publicada y
> verificada** antes de empezar la siguiente. Referencia en el MAPA: changelog 477.

---

## 0. LAS REGLAS QUE MANDAN EN TODO EL PLAN

1. **El servidor no parsea, no dibuja, no calcula.** Guarda archivos y datos, los entrega, cuida
   usuarios y permisos, lleva el registro. Nada más. Al final del plan, `servidor.py` no importa
   PyMuPDF ni pikepdf.
2. **La salida del navegador es IDÉNTICA a la de hoy.** El mismo molde con el mismo diseño y la
   misma planilla tiene que dar la misma tizada: mismo vector, mismos operadores PDF, mismos
   colores CMYK, mismas posiciones. Cada etapa se prueba comparando **byte a byte o número a
   número** contra lo que hoy produce el código Python, con los archivos reales del usuario. Si
   no da igual, la etapa no se publica.
3. **Se trabaja LOCAL y se guarda de una vez («paquete + Guardar»).** Mientras la persona
   configura, prueba, mira y acomoda, nada viaja. Al tocar **Guardar**, el navegador arma un
   paquete (archivos + configuración + huella) y lo manda entero; el servidor lo recibe completo o
   lo rechaza completo. Nunca a medias.
4. **Quien no tiene la potencia no envía.** Antes de un trabajo pesado el navegador mide la
   máquina y, si no alcanza, lo dice con claridad y no deja subir ni generar. Nada de degradar
   la calidad: la ley del vector original sigue (nunca rasterizar, nunca tocar el archivo).
5. **Las dos rutas conviven mientras se migra.** Cada etapa entra detrás de un interruptor
   (`navegador.<etapa>` en la configuración, por defecto apagado en el publicado hasta que la
   etapa esté verificada). El código Python del servidor queda como **verificador**: en el taller
   se corre en «modo comparación» (recalcula y compara con lo que mandó el navegador) hasta que la
   etapa se da por cerrada; recién entonces se borra del servidor.
6. **Nada a medias, nada roto.** Una etapa que no entra en una tanda se parte en entregas que
   funcionan solas; no se deja código muerto ni pantallas que «después se conectan».

---

## 1. QUÉ HACE HOY EL SERVIDOR Y A DÓNDE VA CADA COSA

| Hoy (Python, servidor) | Módulo | Mañana | Etapa |
|---|---|---|---|
| Leer el molde del camino B: capas = talles, contornos por capa (`get_drawings`), marco, línea de corte | `piezas_con_diseno.py` (2,7k líneas), `molde_real.py` | Navegador (`motor/molde/desplegar.js`) | 1 |
| Páginas por talle (cortar el content-stream por capa, `cortar_capas.py`) | `piezas_con_diseno._paginas_de_talles`, `molde_real.limpiar_capas` | Navegador (`motor/molde/paginas.js`) | 1 |
| Placeholders NOMBRE/00 por talle, etiqueta que trae el archivo (familias), personalización | `piezas_con_diseno` (buscar_candidatos, decidir_familias) | Navegador (`motor/molde/placeholders.js`, `etiqueta_archivo.js`) | 1 |
| Alta del camino A (molde solo, `detectar_piezas`, emparejado de talles) y DXF (`importar_dxf.py`, ezdxf) | `motor_pedido.alta_plantilla*`, `importar_dxf.py` | Navegador (`motor/molde/camino_a.js`, DXF con `dxf-parser`) | 1b |
| Guardar el molde (registro, catálogo, base) | `servidor.py` + MSSQL | Servidor: **recibe el paquete** y guarda | 1 |
| Vistas del molde y de las mesas de una tizada (`mesa_img`, recortes, pre-dibujado, pool del visor) | `servidor.py` (`_dibujar_una_mesa`, `_predibujar_mesas`) | Navegador dibuja desde el vector (`motor/vista/`) | 2 |
| Leer el arte: personalización (fuentes, curvas, bordes), editables, mapeo por nombre, perfil ICC | `motor_pedido.extraer_personalizacion/extraer_editables` | Navegador (`motor/arte/`) | 3 |
| Fuentes → curvas (fontTools), catálogo de fuentes, alias/reemplazos | `texto_curvas.py`, `motor_pedido.resolver_fuente` | Navegador (`motor/texto/curvas.js` con opentype.js); catálogo de fuentes lo **sirve** el servidor | 3 |
| Pieza con diseño (`_armar_base`: contorno + diseño + borde + marcas) y preview del Arte por pieza | `motor_pedido.generar_pieza/_armar_base`, `_piezas_base` | Navegador (`motor/pieza/`) | 3 |
| Nesting (acomodar piezas en la tela, contornos, giros) | `nesting_contorno.py`, `motor_pedido` | Navegador (`motor/nesting/`) — mismo algoritmo, mismos números | 4 |
| Escribir la hoja (XObjects, /UserUnit, hoja compartida), estampado por prenda, borde de corte, etiqueta del sistema | `hoja_pike.py`, `motor_pedido.generar_pedido*` | Navegador (`motor/hoja/`) | 4 |
| Aplanar para el RIP (0 XObjects anidados, 1 perfil ICC, ExtGState, PDF 1.6) | `aplanar_rip.py` | Navegador (`motor/rip/aplanar.js`) | 4 |
| Ficha técnica A4, previa SVG, verificación de la hoja, ZIP | `ficha_tecnica.py`, `hoja_pike.preview_svg` | Navegador (`motor/ficha/`, `motor/previa/`) | 4 |
| Guardar el pedido (trabajos/<id>, descargas) | `servidor.py` | Servidor: **recibe el paquete del pedido** y lo entrega | 4 |
| Medir la potencia de la PC | — (no existe) | Navegador (`motor/capacidad.js`) | 5 |
| Pools de procesos, cupo, topes, plan B | `procesos.py`, `servidor.py` | **Se borran** | 6 |
| Usuarios, permisos, catálogo, planillas, telas (API externa), registro, actualizaciones | `servidor.py`, `db.py`, `api_usuarios.py`, `registro.py` | **Quedan en el servidor** tal cual | — |

Lo que queda en el servidor es liviano: JSON, archivos y la base. Con eso, cien personas a la
vez son cien navegadores trabajando y un servidor que copia archivos.

---

## 2. LA TECNOLOGÍA (qué se usa y por qué)

- **mupdf.js** (paquete npm `mupdf`, MuPDF compilado a WebAssembly por Artifex): es **el mismo
  motor** que PyMuPDF usa en el servidor. Lee y escribe PDF (objetos, streams, XObjects, capas
  OCG), recorre los trazados de una página con un `Device` propio (= `get_drawings`), extrae
  texto con fuentes y tamaños (= `get_text("dict")`), rasteriza (= `get_pixmap`). Pesa 10 MB
  (`mupdf-wasm.wasm`, se baja una vez y queda en caché). Corre en Node también → **los contratos
  se corren sin navegador**.
  - ⚠️ **Misma versión de MuPDF en los dos lados.** Hoy el servidor tiene PyMuPDF 1.26.7 y npm
    da mupdf 1.28.1. Para comparar resultados se fija mupdf.js a la misma serie que PyMuPDF (o
    se sube PyMuPDF), y esa pareja de versiones queda escrita en `verificar_navegador_versiones.py`.
  - ⚠️ **Licencia**: MuPDF es AGPL (igual que PyMuPDF, que ya se usa). Para un producto comercial
    cerrado hace falta la licencia comercial de Artifex. Decisión del usuario; el plan no la
    toma.
- **pikepdf → mupdf.js.** Todo lo que hoy se hace con pikepdf (content streams, XObjects,
  ExtGState, /UserUnit, OutputIntents) se hace con la API de objetos PDF de mupdf.js
  (`PDFDocument.newDictionary/addStream/addObject`, `PDFPage.getObject()`, parsing propio del
  content-stream). No hay pikepdf para WebAssembly: **todo lo que use pikepdf se reescribe**.
- **opentype.js** para fuentes → curvas (= fontTools `DecomposingRecordingPen`): TTF/OTF/CFF,
  glifos como paths cúbicos/cuadráticos. Se verifica glifo por glifo contra fontTools.
- **JavaScript moderno (ES2022) con módulos, sin TypeScript** (el frontend ya es JS + React +
  Vite). Cada módulo del motor es JS puro sin React, probado en Node.
- **Web Workers**: cada trabajo pesado corre en un worker (un hilo aparte): la pantalla nunca se
  congela y el trabajo se puede cancelar matando el worker. Un worker por trabajo
  (`motor/trabajo.worker.js`), con mensajes `{tipo, avance, listo, error}`.
- **IndexedDB** (con la librería `idb`) para el **espacio local**: el molde abierto, su
  desplegado, la configuración, el diseño, la tizada armada. Sobrevive a recargar la página.
  `localStorage` sólo para preferencias chicas.
- **fflate** para armar el ZIP del paquete y del pedido en el navegador.
- **File System Access API** (ya se usa en `src/descargar.js`): las descargas siguen eligiendo
  dónde guardar; los PDF los tiene el navegador, no hace falta bajarlos del servidor.
- **numpy** (una sola importación en `motor_pedido`) → JS puro (arrays). **ezdxf** → `dxf-parser`.
  **Pillow ImageCms** (sólo para mostrar los colores CMYK en pantalla con el perfil) → en el
  navegador se dibuja con la conversión de MuPDF (que ya aplica el perfil al rasterizar) — la
  salida impresa no cambia porque el perfil sólo se INCRUSTA, no se convierte.
- **Límites conocidos**: WebAssembly de 32 bits = **4 GB de memoria por pestaña** (el molde de
  123 MB pesa ~1 GB parseado en Python: entra, pero se mide en la etapa 0). Safari da menos
  memoria y no informa `deviceMemory`: la puerta de potencia (etapa 5) lo trata como «no sé» y
  mide de verdad.

---

## 3. ARQUITECTURA EN EL NAVEGADOR

```
frontend/src/
  motor/                       ← el motor, JS puro, sin React, probado en Node
    pdf/mupdf.js               ← carga mupdf.js una vez por worker; envoltorios (abrir, página,
                                  recorrer trazados, texto, escribir objetos, guardar)
    pdf/contenido.js           ← parser/escritor de content-streams (operadores, BDC/EMC de capas)
    molde/capas.js             ← talles = capas OCG (orden, nombres, «Editable …», guías)
    molde/contornos.js         ← _piezas_de_mesa_cruda: recortes por capa, marco, agrupar por
                                  solape, pintado por recorte, línea de corte, respaldo por trazados
    molde/orden.js             ← canonizar_orden (piezas en el orden del talle de referencia)
    molde/paginas.js           ← una página por talle (cortar_capas + limpiar_capas) → m{mesa}.pdf
    molde/placeholders.js      ← NOMBRE / 00 / talle por talle: fuente, tamaño, curva, borde
    molde/etiqueta_archivo.js  ← candidatos + decidir_familias (la etiqueta que trae el molde)
    molde/camino_a.js          ← detectar_piezas / alta_plantilla / emparejado (molde sin diseño)
    molde/dxf.js               ← importar_dxf (AAMA) con dxf-parser
    arte/personalizacion.js    ← extraer_personalizacion (capas Nombre/Número/talle, curvas, bordes)
    arte/editables.js          ← extraer_editables (capas «Editable …», pila de apariencias)
    arte/mapeo.js              ← mapeo por nombre de capa guía → pieza
    texto/fuentes.js           ← catálogo de fuentes (lo sirve el servidor), alias, reemplazos
    texto/curvas.js            ← FuenteCurvas con opentype.js; ops_texto_curva (arco)
    pieza/base.js              ← _armar_base: contorno + diseño + borde de corte + marcas de proceso
    pieza/estampar.js          ← nombre/número/talle por prenda sobre la base
    nesting/contorno.js        ← nesting_contorno (polígonos, giros, mesa por tela)
    nesting/grupos.js          ← generar_multi: una mesa por molde, grupos por columna de talle/tela
    hoja/componer.js           ← componer_hoja_pike / sello: XObjects, /UserUnit, hoja compartida
    rip/aplanar.js             ← aplanar_para_rip
    ficha/ficha.js             ← ficha técnica A4
    previa/svg.js              ← preview_svg (la vista previa vectorial, con recortes)
    vista/dibujar.js           ← rasterizar mesas/recortes para el visor (mupdf toPixmap → canvas)
    paquete/espacio.js         ← el espacio local (IndexedDB): molde, config, diseño, tizada
    paquete/armar.js           ← el ZIP del paquete (manifest + huella) para Guardar
    capacidad.js               ← medir la PC: núcleos, memoria, WebAssembly, benchmark
    trabajo.worker.js          ← el worker: recibe {tipo, datos}, corre el módulo, informa avance
  laboratorio/                 ← etapa 0 (se borra al terminar el plan)
```

**Reglas del motor JS:** cada módulo es una traducción **función por función** del Python, con
el mismo nombre (en español) y el mismo comentario del porqué; los números se calculan en el
mismo orden (los `float` de Python y los `number` de JS son el mismo IEEE-754: si se hacen las
mismas operaciones en el mismo orden, dan el mismo bit). Donde Python recorre un `dict`, el JS
recorre un `Map` en el mismo orden de inserción. Nada de «mejorar de paso»: primero idéntico,
después se mejora en los dos lados o en ninguno.

**El worker.** La pantalla manda `{tipo: "desplegar_molde", bytes, talles}` y recibe
`{avance: {hecho, total, texto}}` … `{listo: resultado}` o `{error: mensaje}`. Un worker por
trabajo; cancelar = `worker.terminate()`. Los bytes viajan transferidos (`postMessage(…,
[buffer])`), no copiados.

---

## 4. ARQUITECTURA EN EL SERVIDOR (cómo queda al final)

Endpoints que **quedan** (livianos): sesión/usuarios/permisos, catálogo (productos, planillas,
telas, diseños, fuentes del catálogo), **descargas de archivos** (molde, desplegado, arte,
tizadas), registro, actualizaciones, salud.

Endpoints **nuevos** (recibir paquetes):
- `POST /api/paquetes/molde` — ZIP con `manifest.json` (huella del .ai, versión del formato,
  talles, piezas, config), `plantilla.ai`, `desplegado/` (m{mesa}.json, m{mesa}.pdf,
  etiqueta_archivo.json, personalizacion.json), `registro_producto.json`, `visor.json`. El
  servidor: valida el manifest, comprueba la huella del .ai contra los bytes, escribe todo en
  una carpeta temporal y **la mueve de una vez** (`os.replace`); si algo falla no queda nada.
  Devuelve `{ok, pid, version}`.
- `POST /api/paquetes/pedido` — ZIP con `pedido.json`, las hojas PDF (ya aplanadas), la ficha,
  la previa SVG, la planilla. El servidor lo guarda en `trabajos/<id>/` y lo entrega como hoy.
- `GET /api/paquetes/molde/<pid>` — el paquete entero para abrirlo en otra PC (el navegador lo
  guarda en su espacio local).
- **Versiones y conflictos**: cada paquete lleva `basado_en` (la versión que la persona había
  bajado). Si en el servidor hay una versión más nueva, responde 409 con quién y cuándo, y la
  pantalla ofrece bajar la nueva o pisar (sólo con permiso `molde.editar`). Es la lógica de un
  programa profesional: se trabaja local, se sincroniza al guardar, y un choque se avisa.

Endpoints que **se borran** en la etapa 6 (hoy hacen trabajo pesado): `/api/generar`,
`/api/generar_multi`, `/api/arte/preview_piezas`, `/api/arte/asignar_todo`,
`/api/arte/asignar_estado`, `/api/arte/mesa_img`, `/api/arte/deteccion`,
`/api/plantilla/deteccion*`, `/api/productos/editables` (GET pesado), `/api/pedido/fuentes_estado`
(la parte que lee el arte), `/api/trabajos/<tid>/mesa_img/*`, el desplegado en segundo plano,
los pools (`_get_render_pool`, `_get_visor_pool`), `procesos.py` (cupo, topes), `aplanar_rip.py`,
`hoja_pike.py`, `motor_pedido.py`, `piezas_con_diseno.py`, `nesting_contorno.py`,
`texto_curvas.py`, `ficha_tecnica.py`, `molde_real.py`, `cortar_capas.py`, `importar_dxf.py`.
Hasta esa etapa **se conservan como verificadores** (`verificar_navegador_*.py` los usan para
producir la referencia).

---

## 5. LA LÓGICA «PAQUETE + GUARDAR» (transversal, se construye en la etapa 1 y se reusa en la 4)

1. **Abrir**: la persona elige el archivo del molde (o baja uno del servidor). Va al espacio local
   (IndexedDB, `espacio.abrirMolde(bytes)`) con una **huella** (SHA-1 de los bytes, igual que
   `_cache_desplegado` hoy).
2. **Preparar** (worker): desplegado completo con avance honesto («mesa 3 de 9 · talle M»). El
   resultado (JSON + PDFs por talle) queda en el espacio local, ligado a la huella.
3. **Configurar** (en la pantalla, sin servidor): nombrar piezas, columna de talle, etiqueta,
   telas, toggles, diseño, fuentes. Todo en el espacio local. Recargar la página no pierde nada.
4. **Guardar** (un botón): `armar.paqueteMolde(espacio)` → ZIP (fflate) con manifest → `POST
   /api/paquetes/molde`. Barra de subida real (bytes). Respuesta `ok` → el espacio local se marca
   «sincronizado con la versión N». Respuesta 409 → cartel de conflicto.
5. **Sin conexión / falla**: el paquete queda armado en el espacio local con estado «pendiente de
   enviar»; al volver la conexión se reintenta con un botón. Nada se pierde.
6. **Abrir en otra PC**: `GET /api/paquetes/molde/<pid>` → espacio local. La preparación NO se
   repite: el paquete ya trae el desplegado (es lo que hoy hace `_cache_desplegado_tomar`).

Lo mismo para el pedido: planilla + diseño + telas se configuran local; **Generar** arma la
tizada en la PC (etapa 4); **Guardar/Enviar** manda el paquete del pedido; **Descargar** guarda
los PDF desde el navegador directamente (ya están ahí).

---

## 6. LAS ETAPAS, PASO A PASO

### ETAPA 0 — Viabilidad: ¿el navegador ve el molde igual que el servidor? (1-2 semanas)

> ✅ **CERRADA 2026-09-17 — VIABLE** (MAPA changelog 478). Dibujos e instrucciones idénticos
> número a número en 5 moldes reales (hasta 117 MB, 6,3 M de instrucciones); render igual salvo
> bordes suavizados (WebAssembly vs nativo, comprobado que no es la versión); Chrome real con el
> de 117 MB: 19 s y 639 MB. Falta sólo que el usuario lo pruebe en Firefox y en su PC más floja.

**Qué se construye (ya empezado, sin commitear):**
- `laboratorio_navegador.py`: escribe `<molde>.dibujos_ref.json` con lo que PyMuPDF ve
  (`get_cdrawings(extended=True)`): por mesa, cada recorte/relleno/trazo con su capa, nivel y
  rectángulo.
- `frontend/laboratorio.html` + `src/laboratorio/{main.js, worker.js}`: abre el molde con
  mupdf.js en un worker, recorre cada mesa con un `Device` propio (beginLayer/endLayer = capa;
  clipPath/popClip/beginGroup/endGroup = nivel; `path.getBounds(stroke, ctm)` = rectángulo) y
  compara con la referencia: mismas capas, mismos recortes por capa (cantidad, orden, posición
  a 0,05 pt), mismas cantidades de rellenos y trazos; informa tiempo y memoria.
- Vite: segunda entrada `laboratorio.html`; `worker.format = 'es'`; `build.target = 'esnext'`
  (mupdf.js usa `await` a nivel de módulo).
- Segunda prueba del laboratorio: **rasterizar** una mesa a 72 dpi con mupdf.js y con PyMuPDF
  y comparar píxel a píxel (misma versión de MuPDF ⇒ 0 píxeles distintos).
- Tercera prueba: **texto**: los placeholders (NOMBRE/00) con su fuente y tamaño por talle,
  contra `extraer_placeholders` de Python.

**Con qué archivos:** los del usuario, los pesados: CAMISETA JUGADOR/LIBERO (los del 16/09), el
molde de 123 MB, el de una sola mesa con 20 talles, más 3 artes del camino A. Se copian a
`laboratorio/` (gitignoreado).

**Se mide:** tiempo por mesa en Chrome, Edge y Firefox (y Safari si hay Mac), memoria pico del
worker, y si el .ai de 123 MB abre. Se anota todo en el MAPA.

**Criterio para seguir:** contornos idénticos en TODOS los archivos + render píxel-idéntico +
placeholders iguales + el archivo más pesado entra en memoria en Chrome/Edge/Firefox. Si algo no
da, se investiga (versión de MuPDF, orden de capas) hasta que dé o se declara inviable **por
escrito** con la causa. No se pasa a la etapa 1 con «casi».

**Publicación:** el laboratorio queda en `/laboratorio.html` (sólo con sesión de administrador)
para repetir la prueba con archivos nuevos.

### ETAPA 1 — El molde se prepara en el navegador y se guarda como paquete (4-6 semanas)

> ⏩ **EN CURSO 2026-09-17** (MAPA changelog 479). HECHO: pasos 1-6 y 8-9 para el molde CON
> diseño (camino B), idénticos al servidor, en dos tiempos y con varios hilos (la persona sigue a
> los 3,5-5,4 s). FALTA: paso 7 (camino A y DXF), no re-subir un archivo que el servidor ya tiene
> (misma SHA-1), y el modo comparación `TIZADA_NAVEGADOR_COMPARAR`. 🔴 Falta también que
> «Subir mi propio molde» (Mis artículos) prepare en el navegador: hoy manda el archivo sin
> paquete y lo prepara el servidor (MAPA 482); para eso hay que detectar en el navegador si el
> molde trae el diseño adentro, porque esa pantalla también acepta camino A y DXF.
> MEDIDO (MAPA 480): 10 personas guardando a la vez el molde de 117 MB = 5,7 s y 166 MB en un
> servidor de 3 núcleos. Lo caro es internet: ~250 MB por molde (archivo + páginas).

**Lógica (traducción de `piezas_con_diseno.py`, función por función):**
1. `capas.js`: `talles_del_molde` — las capas OCG del documento en el orden de `/OCProperties
   /D /Order`; nombres tal cual (regla: del archivo sólo el TALLE; «Editable …», «guías» se
   apartan); talle de referencia.
2. `contornos.js`: `_piezas_de_mesa_cruda` — recorrer la mesa con el Device: recortes de la
   capa del talle (`type clip`, `layer`), descartar degenerados y el **marco de la mesa** (igual
   al rectángulo de la página con 1 pt de tolerancia: NUNCA por porcentaje), agrupar por solape
   (`_se_pisan` contra el más chico > 0,5), elegir el recorte con diseño adentro
   (`_pintado_por_clip`, por nivel), la **línea de corte** (el recorte envolvente sin relleno con
   trazo), `_respaldo_por_trazados` si no hay recortes; contorno serializado en coordenadas
   crudas del lienzo (`_contorno_de_drawing`: y arriba, `U` del /UserUnit, cropbox), con
   `w_cm/h_cm`, área y `pieza_idx`.
3. `orden.js`: `canonizar_orden` — las piezas de cada talle en el orden del talle de referencia
   (centroide + forma + solape), para que la pieza *i* sea la misma en todos los talles.
4. `paginas.js`: `_paginas_de_talles` — para cada talle, una página con SOLO su capa: ubicar por
   bytes dónde empieza y termina cada `BDC /OC /nombre … EMC` (`cortar_capas`), parsear sólo ese
   trozo (`contenido.js`), aplicar `limpiar_capas_conservando_talle` (se conservan marcadores,
   recursos usados, `sanear_oc`), escribir `m{mesa}.pdf` con mupdf.js (una página por talle, el
   mismo `/Resources` podado, `/UserUnit`). **Operador por operador igual** al de hoy: se
   verifica con `verificar_navegador_paginas.py` (desempaqueta los content-streams de los dos
   lados y los compara).
5. `placeholders.js`: NOMBRE / 00 / talle por talle: texto con fuente y tamaño
   (`toStructuredText`), la curva (`baseline_pts`), el borde (re-match), el color; se sacan del
   diseño (`ocultar`).
6. `etiqueta_archivo.js`: `buscar_candidatos_mesa` + `decidir_familias` (fuente + alto; la que
   está en ≥ 2/3 de las piezas se oculta; lo fijado a mano manda).
7. `camino_a.js` (1b): `detectar_piezas`, `alta_plantilla`, `alta_plantilla_manual`, emparejado
   por centroide/forma/solape; `dxf.js`: `importar_dxf` (AAMA/Optitex) con `dxf-parser`.
8. `espacio.js` + `armar.js` + `POST /api/paquetes/molde` (§5). En el servidor: `paquetes.py`
   (validar manifest, huella, mover atómico, versión/409) y en modo comparación (taller,
   `TIZADA_NAVEGADOR_COMPARAR=1`) recalcula con Python y compara; una diferencia va al registro
   y corta la subida.
9. Pantalla: el paso «Subir molde» pasa a «Abrir molde» (local) → «Preparando en tu computadora»
   (avance real por mesa/talle, cancelable) → configuración (la de hoy, leyendo del espacio local)
   → **Guardar** (barra de subida) → «Guardado, versión N». Sin cambios de aspecto: cambia de
   dónde salen los datos. El `_desplegar_en_fondo` del servidor deja de dispararse cuando
   `navegador.molde` está prendido.

**Contratos:** `verificar_navegador_contornos.py` (m{mesa}.json idéntico: mismas piezas, mismos
segmentos a 1e-6), `verificar_navegador_paginas.py` (content-streams iguales), 
`verificar_navegador_placeholders.py`, `verificar_navegador_etiqueta.py`, `verificar_paquete_molde.py`
(atómico: un ZIP roto no deja nada; 409 con versión vieja; huella falsa rechazada). Los JS se
corren en **Node** (`node motor/pruebas/*.mjs`) desde `correr_contratos.py`.

**Publicación:** interruptor `navegador.molde` (Configuración → Sistema). Primero apagado en el
publicado y prendido en el taller; después de una semana de comparación sin diferencias, se
prende en el publicado. El desplegado del servidor deja de correr para las subidas nuevas.

### ETAPA 2 — El visor dibuja en el navegador (2-3 semanas)

- `vista/dibujar.js`: rasterizar una mesa o un recorte con mupdf.js (`toPixmap` a la escala
  pedida, en un worker, a un `OffscreenCanvas` → `ImageBitmap`), con caché en IndexedDB por
  (huella, mesa, escala, recorte). Reemplaza `mesa_img`, los escalones 800/1600 de recortes y el
  pre-dibujado del servidor. La grilla del paso Tizada y el zoom fluido (changelogs 468-470)
  pasan a pedirle al worker, no al servidor.
- El visor del molde (contornos, nombrar piezas, etiqueta) ya dibuja vector en el navegador:
  pasa a leer del espacio local.
- **Contrato:** `verificar_navegador_vista.py`: el mismo recorte a 800 px en mupdf.js y en
  PyMuPDF → 0 píxeles distintos (misma versión). 
- **Publicación:** `navegador.vista`. El pool del visor del servidor se apaga con el interruptor.

### ETAPA 3 — El arte en el navegador (6-8 semanas)

1. `texto/fuentes.js`: el catálogo de fuentes lo sigue sirviendo el servidor
   (`/api/fuentes/catalogo`, ya existe) — el navegador baja el archivo de la tipografía una vez
   (caché); alias, reemplazos por pedido y por campo (`@campo:`), «la elección manda».
2. `texto/curvas.js`: `FuenteCurvas` con opentype.js: glifo → path (cúbicas; las cuadráticas
   TrueType se elevan a cúbicas **exactamente como fontTools**), avance, kerning, `ops_texto_curva`
   (arco) — contrato glifo por glifo contra fontTools.
3. `arte/personalizacion.js`: `extraer_personalizacion` (capas Nombre/Número/campos, fuente CID
   por capa, curva, borde, color, pila de apariencias); `arte/editables.js`: `extraer_editables`
   (capas «Editable …» como objetos: mover/rotar/escalar, marcas TPU/Bordado/DTF, `sin_marca`);
   `arte/mapeo.js`: mapeo por nombre de capa guía → pieza, por variable.
4. `pieza/base.js`: `_armar_base` (contorno + diseño recortado + borde de corte con su color
   CMYK y tamaño + marcas de proceso) y `pieza/estampar.js` (nombre/número/talle sobre la
   base, `_encaje` alto/ancho, `_cm_arriba`), con la caché por (pieza, talle, variable, clave v14).
5. El paso Arte del pedido: las previas por pieza (`preview_piezas`, `asignar_todo`) se generan
   en el worker y se muestran como hoy (SVG vectorial); el editor de editables lee del espacio
   local; «Editar diseño» instantáneo porque no hay viaje.
6. **Contratos:** `verificar_navegador_curvas.py` (fontTools vs opentype.js, todos los glifos de
   las 7 tipografías del catálogo + las del usuario: mismos puntos a 1e-4), 
   `verificar_navegador_personalizacion.py`, `verificar_navegador_editables.py`,
   `verificar_navegador_base.py` (la base de cada pieza: PDF byte a byte tras normalizar ids de
   objetos; si no, operador por operador + render píxel-idéntico).
7. **Publicación:** `navegador.arte`.

### ETAPA 4 — La tizada entera en el navegador (8-12 semanas)

1. `nesting/contorno.js`: `poligonos_contorno`, `anidar_contorno` (mismos giros, mismo orden de
   prueba, mismos empates) y `nesting/grupos.js` (`generar_multi`: una mesa por molde, grupos por
   tela y por columna de talle, filas sin talle → traba, toggles, variables por fila). Contrato:
   **mismas posiciones** (x, y, ángulo) para el mismo pedido.
2. `hoja/componer.js`: `componer_hoja_pike`/`componer_hoja_sello`: XObjects por base, matriz de
   colocación, hoja compartida, mesas de más de 5,08 m con `/UserUnit` en TODOS lados, borde de
   corte, etiqueta del sistema (text-on-path sobre el borde: baseline protegida), OutputIntent.
3. `rip/aplanar.js`: `aplanar_para_rip` (0 XObjects anidados, 1 perfil ICC, ExtGState, PDF 1.6,
   CMYK intacto). Contrato: la hoja aplanada del navegador vs la de Python: mismos operadores,
   mismos colores (`verificar_color_nativo_cid`, `verificar_hoja_compartida` traducidos).
4. `ficha/ficha.js` (A4 con la planilla y el molde guía), `previa/svg.js` (`preview_svg`, con
   recortes, best-effort), verificación de la hoja, ZIP.
5. Pantalla: **Generar** corre en el worker con avance real por etapa (armar piezas → acomodar →
   escribir → aplanar → ficha), cancelable; el resultado queda en el espacio local; **Descargar**
   guarda directo desde el navegador; **Enviar** manda el paquete del pedido
   (`POST /api/paquetes/pedido`) para que quede en el servidor (historial, otra PC, el taller).
6. **Contratos:** `verificar_navegador_tizada.py`: los pedidos de referencia del repo
   (`scratchpad/verif_tizada.py` ya compara pixel-idéntico) generados en Node y en Python: hoja
   aplanada píxel-idéntica a 150 dpi y operadores iguales; ficha igual; ZIP con los mismos
   archivos.
7. **Publicación:** `navegador.tizada`. Con esto el servidor ya no genera nada.

### ETAPA 5 — «Quien no tenga la potencia no podrá enviar» (1-2 semanas)

- `capacidad.js`: al abrir la app y antes de cada trabajo pesado: `navigator.hardwareConcurrency`,
  `navigator.deviceMemory` (Chrome/Edge), una **reserva de prueba** de memoria WebAssembly (pedir
  el bloque que el trabajo va a necesitar, según el tamaño del archivo: la etapa 0 da la regla
  MB de archivo → MB de memoria), y un **benchmark de 2 segundos** (recorrer un PDF de prueba
  que viene con la app) que da «puntos de potencia».
- Umbrales calibrados con lo medido en las etapas 0 y 4 (tabla en el MAPA: archivo de N MB
  necesita M MB y P puntos). Si no alcanza: cartel claro («Esta computadora no tiene la memoria
  para preparar este molde de 120 MB: hacen falta 3 GB libres…») y los botones Preparar/Generar
  quedan apagados con el «?» que explica. Nada se degrada.
- Modo honesto de espera: barra con etapa y porcentaje reales, tiempo transcurrido, botón
  cancelar; si la pestaña se cierra, el trabajo queda en el espacio local para retomar.
- **Contrato:** `verificar_navegador_capacidad.mjs` (Node con memoria limitada simula una PC
  chica → la puerta cierra; con memoria de sobra → abre).

### ETAPA 6 — Apagar lo pesado del servidor (1-2 semanas)

- Borrar endpoints, pools, `procesos.py`, los módulos del motor y sus contratos de servidor
  (§4). `servidor.py` queda sin PyMuPDF ni pikepdf; `requirements.txt` sin ellos. El paquete de
  publicación baja de tamaño; `/api/salud` deja de informar procesos.
- Los contratos `verificar_navegador_*` pasan a comparar contra **salidas de referencia
  guardadas** (`referencias/` con los PDF de Python de la última versión), porque ya no hay
  Python que las genere.
- Publicar. Medir con `/api/salud` y el registro: el servidor sólo copia archivos.

---

## 7. VERIFICACIÓN (cómo se prueba cada cosa, siempre igual)

- **Un contrato por función traducida**, en `verificar_navegador_<tema>.py`: corre el Python de
  hoy y el JS (en Node, `node frontend/src/motor/pruebas/<tema>.mjs archivo.ai`) sobre los mismos
  archivos y compara. Se integra a `correr_contratos.py`. Ninguna etapa se publica con un
  contrato rojo.
- **Archivos de referencia**: los del usuario (camino B pesados, camino A con artes, DXF), en
  `laboratorio/` (gitignoreado, con un `LEEME` de qué es cada uno).
- **Píxeles**: renders con la misma versión de MuPDF ⇒ 0 píxeles distintos. Si hay que comparar
  algo visual, es en un navegador (nunca con el rasterizador de SVG de PyMuPDF, que ignora los
  clips: [[render-no-prueba-nada]]).
- **Modo comparación en el taller** (etapas 1-4): el servidor recalcula lo que mandó el navegador
  y anota cualquier diferencia en el registro del sistema. Una semana sin diferencias con uso
  real = la etapa se prende en el publicado.

---

## 8. RIESGOS Y DECISIONES ABIERTAS

| Riesgo | Cómo se trata |
|---|---|
| Licencia AGPL de MuPDF para un producto cerrado | Decisión del usuario antes de la etapa 1 (comercial de Artifex o aceptar AGPL). |
| Versiones distintas de MuPDF (PyMuPDF vs mupdf.js) dan renders distintos | Fijar la misma serie en los dos lados; contrato de versiones. |
| El molde de 123 MB no entra en los 4 GB de WebAssembly | Se mide en la etapa 0; si no entra, se parte por mesa (cada mesa es una página: abrir y cerrar) y se mide de nuevo. |
| fontTools y opentype.js no dan los mismos puntos (CFF, cuadráticas) | Contrato glifo por glifo; si hace falta, se porta la parte de fontTools que se usa (es Python puro). |
| Nesting no determinista al traducir (orden de diccionarios, empates) | `Map` con orden de inserción, comparación de posiciones en el contrato. |
| Safari (memoria, `deviceMemory`) | La puerta de potencia mide de verdad; Safari puede quedar «no soportado» para archivos grandes. |
| Alguien sube un paquete armado a mano | El servidor valida manifest + huella + estructura; el modo comparación lo detecta en el taller; los permisos siguen mandando. |
| Mientras dura el plan, el VPS sigue siendo el que trabaja | Queda la red de seguridad de hoy (cupo, sin plan B, topes) y el plan más grande de Hostinger es la única forma de que muchas personas entren **ya**. |

---

## 9. CRONOGRAMA Y LO QUE HACE FALTA DEL USUARIO

| Etapa | Duración estimada | Al terminar, el servidor deja de… |
|---|---|---|
| 0 Viabilidad | 1-2 semanas | (decide todo) |
| 1 Molde en el navegador + paquete | 4-6 semanas | preparar moldes |
| 2 Visor en el navegador | 2-3 semanas | dibujar mesas y recortes |
| 3 Arte en el navegador | 6-8 semanas | leer artes y armar previas |
| 4 Tizada en el navegador | 8-12 semanas | generar tizadas |
| 5 Puerta de potencia | 1-2 semanas | — |
| 6 Apagar lo pesado | 1-2 semanas | tener PyMuPDF y pikepdf |

Total: **6 a 8 meses** de trabajo continuo, publicando cada etapa.

**Del usuario hace falta:** (1) los archivos pesados de referencia (las dos camisetas del 16/09, el
molde de 123 MB, el de una mesa con 20 talles, 3 artes del camino A) en una carpeta; (2) la
decisión sobre la licencia de MuPDF; (3) el plan de Hostinger mientras tanto; (4) probar cada
etapa en su máquina cuando se publique y decir «esto no es igual» si algo cambia.

---

## 10. CÓMO SE EMPIEZA (etapa 0, primer día)

1. Commitear el laboratorio (ya escrito): `laboratorio_navegador.py`, `frontend/laboratorio.html`,
   `frontend/src/laboratorio/`, Vite con `worker.format='es'` y `build.target='esnext'`, `mupdf`
   fijado a la serie de PyMuPDF.
2. Correr con el molde chico del repo (ef99): contornos idénticos o no, y por qué.
3. Correr con los pesados del usuario en Chrome, Edge y Firefox: tabla de tiempos y memoria en
   el MAPA (changelog nuevo por cada medición).
4. Agregar el render píxel-idéntico y los placeholders.
5. Decidir por escrito: **viable / no viable**, y sólo entonces la etapa 1.
