# TIZADA PRO — instrucciones del proyecto

## 0. QUÉ ES ESTE PROYECTO (no inferirlo de cómo se ejecuta)

**Proyecto GRANDE que va a ser una APP WEB usada por CLIENTES**, y se va a asociar a un sistema que
usa **MSSQL** (por eso la base es MSSQL — decidido, ver `PLAN_MSSQL.md`). Que hoy arranque con
`py servidor.py` en localhost es el **estado actual**, NO el objetivo ni el alcance.

⚠️ **NO inferir el alcance del proyecto de cómo corre hoy. Si el alcance importa para una decisión,
PREGUNTAR.** (Ya pasó: se asumió "app local de un solo usuario" mirando el localhost y se recomendó
SQLite sobre MSSQL — mal.)

## 1. EL MAPA ES OBLIGATORIO

**`MAPA_DEL_SISTEMA.md` (raíz del repo) es el cerebro del sistema.** Contiene: arquitectura, modelo de
datos, conceptos, pipeline, enlaces críticos "si tocás X revisá Y", invariantes, gotchas, endpoints y
el changelog con los pendientes.

- **LEERLO ANTES de tocar código.** No empieces a editar sin haberlo consultado. Muchos bugs de este
  repo ya están documentados ahí con su causa: leerlo primero ahorra re-investigar y evita repetir
  errores ya pagados.
- **ACTUALIZARLO DESPUÉS de cada cambio**, en la misma tanda (misma sesión, mismo commit): la sección
  que corresponda + el CHANGELOG del final. Si algo del mapa ya no es cierto, **corregilo**.
- Si el usuario pide una mejora que no se hace en el momento, **queda anotada en el changelog del mapa
  con un plan concreto** (qué tocar, en qué archivo, cómo verificarlo) + una memoria persistente que
  la referencie. El mapa es el respaldo entre sesiones: lo que no está escrito ahí, se pierde.
- Al terminar una investigación, escribí también **lo que salió mal y por qué** (diagnósticos errados,
  trampas de herramientas). Vale tanto como lo que salió bien: evita repetir el error.

## 2. REGLAS DURAS (no negociables)

- **CUANDO SE PIDE ALGO, VA COMPLETO Y COHERENTE EN TODO EL SISTEMA.** No alcanza con el lugar
  obvio: hay que **INVESTIGAR EL PROYECTO ENTERO** y aplicar la mejora en **todos** los apartados,
  campos, vistas, cachés y configuraciones que la hagan funcional y coherente. Antes de decir
  "listo": buscar TODAS las rutas que tocan esa feature (previews, cachés y sus CLAVES de
  invalidación, overlays, el motor, el guardado por rango/variante/talle) y verificarlas. Media
  feature aplicada en un solo lugar NO es una entrega.
- **Responder con el tiempo que haga falta, no rápido.** Investigar a fondo antes de tocar; usar
  el MAPA y las memorias (para eso existen). Una respuesta rápida y superficial es un error.

- **NADA A MEDIAS.** Si una feature entra, entra COMPLETA: backend + endpoints + **la pantalla para
  usarla y configurarla**. No entregar la mitad y dejar el resto "para después". Si no entra en una
  sesión, partirla en entregas que **funcionen** cada una — pero nunca a medio hacer.

- **NUNCA borrar ni sobrescribir datos del usuario** (`datos/`, `entrada/`, `catalogo_fuentes/`) al
  probar. Solo GET y generar. Para verificar algo destructivo, usar una copia propia y descartable.
- **Matar servers por PID específico. NUNCA mass-kill** (`taskkill //IM py.exe` está prohibido).
- **LEY: el arte se ve igual que la tizada.** Lo que se ve en el Arte es exactamente lo que sale
  estampado (vectorial, pixel-idéntico). Si un cambio rompe esa igualdad, está mal.
- **Colores CMYK EXACTOS**: nada de Ghostscript ni re-cuantizar (sublimación). Ver `aplanar_rip.py`.
- **Escalar con las piezas de la VARIABLE (~9), no del MOLDE (~135).**
- **PyMuPDF/pikepdf NO son thread-safe** → paralelizar con ProcessPool (procesos), nunca hilos.

## 3. CÓMO CORRER ESTO

- Frontend servido desde `dist` → **recompilar tras editar `src`**: `cd frontend && npm run build`.
- Server: `py servidor.py` (puerto 8050, env `PORT`). **No tiene auto-reload** por defecto (usa
  `make_server` para IPv4+IPv6; `TIZADA_RELOAD=1` lo activa) → **tras tocar Python hay que
  reiniciarlo** o se sigue atendiendo con el código viejo en memoria.
- Los tests pegan al server REAL (8050), no a un sandbox.

## 4. ESTILO

- El usuario habla español (rioplatense). Respondé en español.
- Comentarios de código en español, explicando **el porqué** (no el qué).
- Nada de diálogos nativos del navegador (`alert`/`confirm`): la UI usa sus propios modales y avisos.
- Verificá lo que afirmás. Si algo no se pudo verificar, **decilo**; no lo des por hecho.
