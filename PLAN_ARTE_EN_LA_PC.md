# EL ARTE DEL PEDIDO VIVE EN LA PC (plan, 2026-11-02)

Pedido del usuario (2026-10-30 / 11-02): «a dos personas se les cruzaron los artes… cada computadora es su PC, el
arte no debería ir a ningún lado más que quedarse en esa computadora». Eligió **«todo a la PC, por entregas»**
(y no la carpeta por pedido en el servidor). Ver MAPA 758 (el bug) y 760 (este plan).

## Por qué se cruzan hoy

El arte de un pedido (camino A: molde base + arte separado) se sube con `POST /api/arte` y queda en el servidor en
`entrada/<pid>/disenos/<slug del NOMBRE del diseño>/arte.ai` (+ `datos/productos/<pid>/disenos/<slug>/`:
validación, mapeo, personalización, objetos agregados; versiones `arte.vN.ai`). Esa carpeta es la MISMA para todos:
dos personas con el mismo molde y «JUGADOR» se pisan. Al rehacer la tizada, el motor del navegador baja el arte por
`/arte_archivo` con el sello (tamaño + fecha) del archivo que hay AHORA en el servidor → el de la otra persona. Lo mismo
con lo que el servidor lee de esa carpeta para armar el plan (validación, personalización, mapeo).

## Lo que ya hace la PC (inventario 2026-11-02)

Analizar el arte al cargarlo (`prepararArteEnNavegador` → zip con `det`, `auto`, `pers`, `mapeo`, `pv`, `validacion`),
dibujar las mesas, validar el mapeo, revalidar al cargar una fuente, el perfil de color, las previas, la lista de
editables, «Editar diseño» (arma el PDF editado) y la tizada. El servidor: guarda el archivo y lo devuelve
(`/arte_archivo`), guarda lo que calculó el navegador y lo devuelve (`/motor_b` → `info.disenos`, `/api/arte/deteccion`,
`/editables_datos`), escribe las versiones editadas (`_arte_version_nueva`), guarda los objetos agregados, y arma el
plan (`_plan_del_pedido`) leyendo `validacion_arte.json` / personalización / mapeo de esa carpeta. Cuenta además las
páginas y `arte_es_separado` al subir.

## Qué NO se muda

- **El robot / la API externa** (`integracion_externa.py`, `robot/robot.mjs`): corre en el servidor (Node, sin
  IndexedDB) y ya usa carpetas propias por pedido (`x-<huella>-<nombre>`, `externo: ref`): sigue igual.
- **La tizada terminada** (el paquete del pedido): cada una tiene su id; no se cruza.

## Las entregas (cada una funciona sola)

### Entrega 1 — «Lo leo de MI PC» (arregla el cruce) — ✅ HECHA 2026-11-02 (MAPA 760)
- `motor/arte/enPc.js`: el arte del pedido en IndexedDB, con clave POR PEDIDO (`pedidoId` nuevo en cada «Nuevo
  pedido», guardado en `tizada_wizard`) + molde + diseño: bytes, sha1, versión y los datos del análisis (det, mapeo,
  pv, pers, validación). `navigator.storage.persist()`. Se borra con «Nuevo pedido» / «Terminar pedido».
- Al cargar el arte se guarda ahí (además de subirlo: en esta entrega el servidor todavía lo recibe, para que todo lo
  que lo usa siga andando).
- `motorDe` (previa.js): los diseños con copia en la PC usan sello `["pc", sha1, versión]` y sus datos (mapeo,
  validación, pers) de la PC; los bytes van a la caché con esa clave → `traerConCache` nunca los baja del servidor
  (como el molde con diseño, MAPA 585). Todo lo que lee el arte (previas, editables, mesas, tizada, ficha) pasa por ahí.
- «Editar diseño»: el PDF editado que arma el navegador se guarda TAMBIÉN como nueva versión en la PC.
- El plan: el cuerpo lleva `artes_pc` ({diseño: {pid: {validacion, pers, mapeo, por_variable, perfil}}}) y
  `_plan_del_pedido` los usa ANTES que los archivos del servidor (con arte = lo que diga la PC).
- Lo que todavía puede cruzarse en esta entrega (se cierra en la 2): los objetos agregados y el mapeo fijo que se
  guarda en el catálogo.

### Entrega 2 — «No lo subo más» — ✅ HECHA 2026-11-02 (MAPA 761)
- `cargarDisenoWizard` deja de subir el arte (el servidor ya no lo necesita para el pedido de una persona).
- Lo que hoy pide al servidor y necesita el archivo pasa a la PC: detección (`/api/arte/deteccion` → det local),
  guardar el mapeo a mano, validación tras cargar una fuente, perfil de color, objetos agregados (PDFs + lista en la
  PC), versiones del «Editar diseño».
- Páginas/`arte_es_separado` que cuenta el servidor al subir: salen del análisis del navegador.

### Entrega 3 — «Limpieza» — ✅ HECHA 2026-11-02 (MAPA 761)
- Sacar del servidor lo que ya no corre para los pedidos de personas (dejando lo del robot/API), los contratos al día
  (`verificar_navegador_arte.py`, `verificar_navegador_camino_a.py`, `verificar_navegador_tizada_a.py`), MAPA y cerebro.
- Los artes viejos que quedaron en `entrada/<pid>/disenos/` son DATOS DEL USUARIO: no se borran sin preguntar.

## Estado (2026-11-02)
- Entrega 1: HECHA (MAPA 760).
- Entrega 2: HECHA (MAPA 761): no se sube; objetos agregados, versiones, mapeo a mano y revalidación en la PC;
  `POST /api/arte/mapeo_fijo` para la semilla del molde; `/motor_b` manda `cfg_disenos`.
- Entrega 3: HECHA (MAPA 761): contrato `verificar_arte_en_pc.py` VERDE. No se borró ninguna ruta del servidor (las usan
  el robot, Configuración y el respaldo sin navegador). Los artes viejos de `entrada/<pid>/disenos/` NO se tocaron:
  son datos del usuario (decide él).
- Falta: recorrerlo en la PANTALLA (el navegador del panel estaba oculto cuando se hizo).

## Cómo se verifica cada entrega
Sandbox aislado (`scratchpad/arch/sandbox_todo.py`) con DOS sesiones (dos perfiles de navegador o dos pestañas con
`pedidoId` distinto): mismo molde + «JUGADOR», artes distintos; A genera, B carga el suyo, A vuelve atrás y regenera →
A sale con SU arte. Más el recorrido de siempre del Pedido (MAPA 754-756).
