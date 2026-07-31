# PLAN — Versión publicada en internet + circuito de actualización (decidido 2026-07-22)

> Retomar con: **"seguimos con la publicación"**. Este archivo existe para NO re-investigar nada.
> Actualizalo al final de cada sesión (§7 Estado).

## 1. QUÉ PIDIÓ EL USUARIO (textual)

> «Quiero tener una opción que se pueda levantar desde internet, usarlo y guardar cosas, pero que
> las actualizaciones que yo haga se hagan desde otro apartado y después programar la actualización.»
>
> Y al preguntarle dónde debía correr: «que nosotros seguimos trabajando como hasta ahora y cuando
> tengamos mejoras habilitar la actualización y que se actualice lo que tenemos publicado en internet».

Respuestas a las preguntas de arranque:
- **Qué se actualiza:** LAS DOS COSAS → (a) versiones del programa (código) y (b) moldes / artes /
  configuración.
- **Quién entra:** SOLO el usuario y su gente (pocos, de confianza). **No** hay clientes externos
  todavía → **no** hace falta separación de datos por cliente (multi-tenant) en esta etapa.
- **Dónde corre:** no lo eligió; describió el flujo. **Decisión tomada acá: VPS Windows** (§3).

## 2. LOS DOS AMBIENTES

| | **TALLER (local)** | **PUBLICADO (internet)** |
|---|---|---|
| Qué es | La máquina del usuario, como hoy (`py servidor.py`) | El mismo programa en un servidor con dominio + HTTPS |
| Para qué | Trabajar, cargar moldes/artes, y donde nosotros programamos y probamos | Usarlo desde cualquier lado y **guardar el trabajo real** |
| Datos de setup (moldes, artes, config) | **Se editan acá** | Llegan **publicados** desde el taller |
| Datos de trabajo (pedidos, tizadas) | Los de prueba | **Los reales, viven acá** |

**REGLA DURA DE DIRECCIÓN DE DATOS:** el setup viaja **taller → publicado**, nunca al revés. Los
pedidos/tizadas hechos en publicado **se quedan ahí** y NO se pisan al publicar. Consecuencia a
resolver en la Etapa 3: en publicado, las pantallas de setup tienen que quedar **de sólo lectura**
(o avisar fuerte), porque un cambio hecho ahí lo borra la próxima publicación.

## 3.bis LA INFRAESTRUCTURA QUE YA TIENE EL USUARIO (relevado 2026-07-22)

El usuario ya tiene otro proyecto publicado: **`C:\Users\user2\Documents\tincho\stock`**
(«stock-wms», React+Vite, repo GitHub `UserBreus/stock-amazon`). Relevado sin tocar nada:

| Qué | Dato |
|---|---|
| Dominio | **`administracionuser.uy`** (y `www`) |
| Delante | **Cloudflare** (104.21.95.72 / 172.67.143.128) |
| Origen real | **EC2 de AWS `3.85.26.173`**, con **nginx 1.27.3** |
| Qué sirve hoy | el SPA `portal-crm-y-stock` en `/`, y la API SQL en el **puerto 5005** de la misma máquina (`/api/sql` → `http://3.85.26.173:5005/sql`, ver `vercel.json`) |
| Vercel | quedó el `.vercel/` y el `vercel.json` de cuando estaba ahí, pero **hoy el dominio lo sirve el EC2** (mismo HTML byte a byte) |
| Sistema | **Linux** (nginx; no es Windows) |

**Consecuencia:** se puede publicar TIZADA PRO en **el mismo dominio, en `/Tizadapro`**, agregando un
`location /Tizadapro/` en el nginx de ese EC2. ⚠️ Hoy `https://administracionuser.uy/Tizadapro`
devuelve 200 porque el SPA contesta **cualquier** ruta con su `index.html` → la regla nueva tiene que
ir **ANTES** del catch-all.

**Dos decisiones que abre esto:**
1. **¿Dónde corre el proceso de TIZADA PRO?**
   - (a) **En el mismo EC2 Linux**: costo extra **cero**. Hay que instalar Python + Ghostscript
     (`apt install ghostscript`) y **copiar los `.icc` de Adobe** de la máquina del usuario al
     servidor. Riesgo: el COLOR. Es medible — Pillow/littleCMS, PyMuPDF, pikepdf y Ghostscript son
     los mismos en Linux, así que lo más probable es que dé idéntico, pero **hay que probarlo con el
     test de píxeles antes de dar nada por bueno**. Verificar también CPU/RAM de la instancia: el
     render usa varios procesos.
   - (b) **Una máquina Windows aparte** (EC2 Windows en la misma cuenta) y el nginx del EC2 actual
     hace de puerta (`proxy_pass`). Cero riesgo de color, ~USD 30–40/mes más.
   - **Recomendación: probar (a) primero** — el test de píxeles decide en una tarde y puede ahorrar
     una máquina entera. Si no da idéntico, (b).
2. **¿Sub-ruta o subdominio?**
   - **`/Tizadapro`** (lo que pidió): el frontend tiene **125 llamadas absolutas a `/api/…`** más
     `/trabajos/…`. Bajo una sub-ruta hay que compilar con `base: '/Tizadapro/'` y prefijar esas
     llamadas — **no son 125 ediciones**: alcanza un envoltorio de `fetch` de ~10 líneas al arranque
     que le pone el prefijo (`import.meta.env.BASE_URL`).
   - **`tizada.administracionuser.uy`**: **cero cambios de código**, solo DNS en Cloudflare.
   - Las dos sirven; la sub-ruta cuesta un rato de trabajo y un riesgo chico de rutas rotas.

## 3. DÓNDE CORRE — decisión inicial (antes de relevar lo de arriba): **VPS Windows** (~USD 25–40/mes)

> ⚠️ Esta sección quedó **condicionada por §3.bis**: el usuario ya tiene dominio + EC2 + nginx
> andando. La decisión pasa a ser «EC2 Linux existente (probando el color) vs máquina Windows
> aparte», no «qué VPS contrato».

**Por qué Windows y no Linux (más barato):** hoy el color depende de cosas instaladas en Windows y
la LEY del proyecto es que **el arte se ve igual que la tizada, con CMYK exacto**:
- **Perfiles ICC de Adobe** (`servidor.py:42-48`): se leen de `C:\Program Files (x86)\Common
  Files\Adobe\Color\Profiles\…`. En Linux hay que conseguirlos y meterlos a mano (y revisar la
  licencia de redistribución de Adobe).
- **Ghostscript** (`servidor.py:326`, `_gs_exe`): busca `gswin64c.exe` en `C:\Program Files\gs`.
- **MSSQL** (decidido, ver `PLAN_MSSQL.md`) es nativo en Windows.
- Son pocos usuarios de confianza → no se gana nada con contenedores todavía.

Linux queda como opción **para más adelante**, cuando entren clientes externos y haya que escalar;
recién ahí se paga el costo de reverificar el color pixel por pixel.

**Buena noticia (ya verificado en el código):** la app **no está clavada a esta máquina**.
`ENTRADA/FUENTES/TRABAJOS/DATOS` ya salen de variables de entorno (`servidor.py:17-20`), el secreto
de sesión también (`TIZADA_SECRET`, línea 30) y hay override para perfiles (`TIZADA_PERFILES`) y
Ghostscript (`TIZADA_GS`). Falta poco para que arranque en otro lado.

## 4. LAS ETAPAS (cada una funciona sola — nada a medias)

### Etapa 0 — Dejarlo listo para correr fuera de esta máquina ✅ **HECHA (2026-07-22)**
- **`TIZADA_MODO`** = `taller` (default, nada cambia para `py servidor.py`) o `publicado`.
  En publicado: `TIZADA_SECRET` **obligatorio** (si falta, NO arranca y explica cómo generarla),
  `SESSION_COOKIE_SECURE` prendida (`TIZADA_HTTPS=0` la apaga mientras no haya certificado) y
  **ProxyFix** para leer los `X-Forwarded-*` del proxy que termina el HTTPS.
- **Waitress** (WSGI de verdad) en modo publicado, `TIZADA_HILOS` (8 por defecto). Si no está
  instalado **corta con un mensaje**, no cae en silencio al servidor de desarrollo.
- **`GET /api/salud`** (sin sesión a propósito: tiene que contestar aunque la base esté caída):
  `{ok, fallas, modo, version, commit, uptime_s, chequeos:{ghostscript, perfiles_icc,
  datos_escribible, base, frontend}}`, HTTP **503** si algo crítico falla. **Es lo que va a mirar el
  actualizador de la Etapa 2** para decidir si vuelve atrás.
- Archivo **`VERSION`** (hoy `1.0.0`) + commit corto → lo que se compara taller vs publicado.
- **`publicado.bat`**: arranque del servidor de internet con las variables a completar.
  Para que arranque solo al prender la máquina (sin instalar nada), Programador de tareas:
  `schtasks /create /tn "TIZADA PRO" /tr "C:\ruta\publicado.bat" /sc onstart /ru SYSTEM /rl highest`
- **`requirements.txt`**: se le agregaron `pillow`, `ezdxf`, `pyodbc` y `waitress` — **el código ya
  los usaba pero no estaban en la lista**, así que una máquina limpia no levantaba.
- **VERIFICADO:** (a) modo publicado sin `TIZADA_SECRET` → se niega a arrancar con el mensaje;
  (b) con clave, waitress levanta en el puerto 8060 contra una **copia** de `datos/`+`entrada/` y
  `/api/salud` da `ok:true` con los 5 chequeos en verde (Ghostscript 10.01.2, 33 perfiles ICC,
  SWOP v2); (c) **la misma pieza renderizada apuntando a la copia vs a los datos reales da 0 px de
  diferencia** (`scratchpad/verif_pub_render.py`). Lo que **NO** se puede verificar todavía: que
  otra MÁQUINA dé igual — eso es la Etapa 1, con el VPS.

### Etapa 1.a — Que la app pueda vivir en `/Tizadapro` ✅ **HECHA (2026-07-22)**

El EC2 **es Windows** (lo confirmó el usuario) → TIZADA PRO corre ahí **nativo**, con los perfiles
ICC y Ghostscript instalados igual que en el taller. No hace falta otra máquina.

- **`frontend/vite.config.js`**: `base` configurable. **`npm run build`** → raíz (taller, como
  siempre); **`npm run build:publicado`** → `/Tizadapro/`.
  ⚠️ **Gotcha:** desde Git Bash, `TIZADA_BASE=/Tizadapro/ npm run build` **NO funciona** — MSYS
  convierte el valor a `/Program Files/Git/Tizadapro/`. Por eso el prefijo va dentro del script de
  `package.json` (`vite build --base=/Tizadapro/`), no por variable de entorno desde bash.
- **`frontend/src/base.js`** (nuevo, se importa PRIMERO en `main.jsx`): envuelve `fetch` una sola vez
  y le pone el prefijo a las rutas propias (`/api/…`, `/trabajos/…`, `/logo.svg`). Así las **125
  llamadas absolutas** siguen escritas igual y ninguna se olvida del prefijo. Exporta `rutaApi()`
  (para lo que NO pasa por fetch) y `esRutaAdmin()`.
- **`App.jsx`**: las 3 comparaciones `location.pathname === '/admin'` pasaron a `esRutaAdmin()`, y se
  prefijaron con `rutaApi()` las 11 URLs que no van por fetch (descargas `<a href>`, `<img src>`,
  `window.open`, el `@font-face` del CSS y los 3 `<img src="/logo.svg">`).
- **VERIFICADO de punta a punta** simulando el nginx (`scratchpad/proxy_subruta.py`, que hace lo
  mismo que el `location` de abajo): con el build publicado, `http://127.0.0.1:8070/Tizadapro/`
  **carga la app en el navegador, sin un solo error de consola**, y las **~20 llamadas salen todas
  con el prefijo** (`/Tizadapro/api/…` → 200), incluido `/Tizadapro/logo.svg`. Sin prefijo,
  `/api/salud` da 404 → **no pisa nada de lo que ya vive en la raíz del dominio**.

**El bloque para el nginx del EC2** (va ANTES del catch-all del sistema de stock):

```nginx
location /Tizadapro/ {
    proxy_pass         http://127.0.0.1:8050/;   # la barra final SACA el prefijo
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;  # lo lee ProxyFix
    client_max_body_size 200m;                     # los .ai pesan
    proxy_read_timeout   600s;                     # generar una tizada tarda
    proxy_send_timeout   600s;
}
location = /Tizadapro { return 301 /Tizadapro/; }
```

### CÓMO SE LLEVA EL PROYECTO AL SERVIDOR (resuelto 2026-07-22)

**Con un paquete, no con `git clone`.** `py empaquetar.py` compila el frontend y arma
`dist/TIZADAPRO_<version>_<commit>.zip` — **1,2 MB, 38 archivos**: todo el código, el frontend ya
compilado para `/Tizadapro`, `db/schema.sql` y las 7 tipografías. **No** lleva `datos/`, `entrada/`,
`node_modules`, respaldos ni scratchpad (es lista blanca: nada se cuela solo).

**Por qué NO compilar en el servidor:** `npm install` + `vite build` necesita Node y **más de 1 GB
de RAM** — justo lo que a ese servidor le falta. Se compila acá, que sobra. Es además exactamente lo
que va a mandar el botón de actualizar (Etapa 2), así que el circuito es el mismo desde el día uno.

**PRIMERA INSTALACIÓN — el usuario NO tiene que saber nada** (pidió explícitamente «no quiero
hacer todo eso, no sé ni quiero aprenderlo ahora»):

1. Acá: **`py empaquetar.py --completo`** → `dist/TIZADAPRO_<v>_<commit>_COMPLETO.zip`
   (**25 MB, 162 archivos**): código + frontend compilado + **los perfiles ICC de esta máquina** +
   `datos/` + `entrada/` (sin el caché de render, que se regenera solo).
2. El usuario abre su **Escritorio remoto** (lo tiene en la barra de Windows), **arrastra el zip**
   y lo descomprime en, por ejemplo, `C:\tizada`.
3. **Clic derecho en `INSTALAR.bat` → «Ejecutar como administrador».** Y listo.

`instalar_servidor.py` hace **todo solo**: verifica/instala Python y las dependencias, instala
Ghostscript si falta (descarga oficial de Artifex), deja los perfiles ICC apuntados, **genera la
clave de sesión**, elige un puerto libre, escribe `config_publicado.bat`, crea la tarea de arranque
automático, levanta el servidor, **inserta el bloque en el nginx** (con respaldo previo, `nginx -t`
antes de recargar y **restauración automática si la config no valida**) y termina mostrando el
chequeo de salud. Modos: `--simular` (no toca nada, dice qué haría) y `--sin-nginx`.

**Verificado acá** (no en el servidor, que no tengo acceso): el paquete se descomprime y el
instalador corre de punta a punta en `--simular` desde el paquete extraído; y la inserción en nginx
probada contra un `nginx.conf` de ejemplo → **queda dentro del `server{}`, ANTES del catch-all, no
pisa la config existente, no duplica si se corre dos veces y devuelve None (no toca nada) si no
encuentra dónde**. Lo que **no** se pudo probar: la instalación real de Python/Ghostscript y el
`nginx -s reload` de verdad.

Para **actualizar** (hasta que exista el botón): `py empaquetar.py`, copiar el zip, parar el
servicio, descomprimir encima, arrancar. `datos\` y `entrada\` **no se tocan** (el paquete no los
trae, así que no hay forma de pisarlos por accidente).

**Git** sigue siendo útil para el código (historial y, más adelante, el actualizador). Hoy el repo
**no tiene remoto**; si se quiere: crear uno **privado** en GitHub (la cuenta ya existe:
`UserBreus`) y `git remote add origin …`. El `.gitignore` ya deja afuera `datos/`, `entrada/`,
`trabajos/`, `node_modules`, `dist` y los respaldos (los 360 MB de `respaldo_moldes_*` incluidos).

### CUÁNTA MEMORIA NECESITA (medido 2026-07-22, no estimado)

Medido con `scratchpad/medir_memoria.py` (pico real del proceso, API de Windows):

| | RAM |
|---|---|
| Python + el servidor importado | **130 MB** |
| Generar **1 talle en frío** (6 piezas) | pico **170 MB** |
| Generar una **tizada completa** (1 hoja, con aplanado para el RIP) | pico **194 MB** |
| El molde grande (19 piezas × 19 talles), 1 talle | pico **171 MB** |

**El costo no depende de cuántas piezas tenga el molde** — depende de las librerías y del PDF que
esté abierto. Un proceso de render ≈ **200 MB**.

**El problema estaba en el paralelismo:** el pool usaba `min(núcleos, 6)` → **6 × 200 MB ≈ 1,2 GB**
solo para renderizar. Con 1 GB libre eso se queda sin memoria seguro.
→ **Nuevo `TIZADA_PROCESOS`** (`servidor.procesos_render()` y `aplanar_rip.py`): acota los procesos.
Sin la variable, todo sigue como siempre. `/api/salud` ahora informa `procesos_render`.

**Con `TIZADA_PROCESOS=2` y 1 GB libre:** ~200 MB el servidor + 2 × 200 MB los workers ≈ **600 MB
de pico**, con ~400 MB de aire. **Alcanza para 1–3 personas** usándolo (el trabajo pesado es de a
uno; lo que se paga es esperar un poco más al cargar todos los talles de una variable).
**Recomendado igual:** dejar el **archivo de paginación de Windows en automático** (colchón por si
un molde muy grande se pasa) y mirar `/api/salud` + el Administrador de tareas la primera semana.

**Si queda corto** (se pone lento o falla al generar), en orden de costo:
1. `TIZADA_PROCESOS=1` — gratis, más lento al cargar variantes.
2. Subir la instancia EC2 un escalón (ej. t3.small → t3.medium, ~USD 15–20/mes más). Es lo que yo
   haría si va a ser la herramienta de trabajo real.
3. Una instancia aparte solo para TIZADA PRO (deja el sistema de stock sin riesgo de quedarse sin
   memoria por culpa de una tizada).

### Etapa 1 — El servidor publicado (EN EL EC2 WINDOWS QUE YA EXISTE)

**Lo hace el usuario en su EC2** (no tengo acceso). Pasos:
1. **Python 3.12** + `py -m pip install -r requirements.txt` (ya incluye waitress/pillow/ezdxf/pyodbc).
2. **Ghostscript** (el mismo que en el taller: 10.01.2) — o dejarlo apuntado con `TIZADA_GS`.
3. **Perfiles ICC**: copiar los `.icc` del taller
   (`C:\Program Files (x86)\Common Files\Adobe\Color\Profiles\Recommended`) a la misma ruta del
   servidor, o a una carpeta propia y apuntarla con `TIZADA_PERFILES`. **Sin esto el color cambia.**
4. Copiar el proyecto, poner la clave en `publicado.bat` y dejarlo como tarea al inicio
   (`schtasks`, ver Etapa 0). Escucha en `127.0.0.1:8050`; a internet da la cara **nginx**.
5. Agregar al nginx el `location /Tizadapro/` de la Etapa 1.a y recargar (`nginx -s reload`).
6. **Backup diario** de `datos/`, `entrada/` y la base (hoy NO existe).
7. **Chequeo obligatorio antes de dar esto por bueno:** abrir `…/Tizadapro/api/salud` y que los 5
   chequeos den verde; después generar **la misma tizada** en el taller y en el servidor y
   compararlas **píxel a píxel** (harness `scratchpad/verif_pub_render.py` como base).
- **Backup diario automático** de `datos/`, `entrada/` y la base, con retención (esto es lo que hoy
  no existe y es lo primero que se extraña cuando algo se rompe).
- **Cómo se verifica:** entrar desde el celular con tu usuario, cargar un pedido y descargar la
  tizada; apagar y prender el servidor y ver que levanta solo.

### Etapa 2 — DISEÑO DETALLADO (acordado 2026-07-23)

Preguntas del usuario: *«¿cómo hacemos lo de las actualizaciones programadas? ¿cómo le avisa al
otro sistema que se va a actualizar y cómo le envía la actualización?»*

**El canal ya existe: el propio dominio.** El servidor publicado ya atiende en
`https://administracionuser.uy/Tizadapro/` con HTTPS. La actualización viaja por ahí — no hace
falta abrir puertos, ni FTP, ni entrar por Escritorio remoto.

**La llave, SIN que el usuario copie ni pegue nada** (pedido explícito 2026-07-23: *«las
actualizaciones no voy a hacer más eso de copiar y pegar, debe de ser más directo»*): el token lo
genera **el TALLER** al armar el paquete (`empaquetar.py`), lo guarda en su config local
(`datos/publicacion.json`, fuera de git) y lo **mete dentro del zip**; el instalador lo lee de ahí y
lo deja en `config_publicado.bat`. Como el paquete lo lleva el propio usuario, **los dos lados
quedan con la misma llave sin que nadie tipee nada**. Se reusa siempre el mismo (si ya existe, no se
regenera: si no, cada paquete rompería el anterior). Va en el header `X-Token-Act`, nunca en la URL.
Sin token, el servidor **rechaza** cualquier paquete: es lo único que separa «actualizar el sistema»
de «cualquiera sube lo que quiera».

**La dirección** del servidor también queda guardada en esa config
(`https://administracionuser.uy/Tizadapro`), editable desde la pantalla. Resultado: **después de
esta instalación, actualizar es UN BOTÓN en el taller. Nunca más Escritorio remoto ni copiar
archivos.**

**Los 4 endpoints nuevos (en el servidor publicado):**

| Endpoint | Qué hace |
|---|---|
| `GET /api/actualizacion/estado` | versión que corre, si hay una pendiente, para cuándo, y el resultado de la última |
| `POST /api/actualizacion/subir` | recibe el `.zip` (token + `sha256` + `cuando`). Lo guarda en `_actualizacion/pendiente.zip`, **verifica el hash y que el zip abra**, y anota la hora. NO instala nada todavía |
| `POST /api/actualizacion/aplicar` | fuerza la instalación ya (el botón «actualizar ahora») |
| `POST /api/actualizacion/cancelar` | borra la pendiente |

**Cómo se avisa (las dos cosas que pediste):**
1. **Al servidor:** el propio `POST …/subir` ES el aviso. Queda anotado «hay una actualización para
   las 03:00» y `GET …/estado` lo devuelve.
2. **A quien esté usando el sistema:** el front pregunta el estado cada pocos minutos y muestra una
   **cinta arriba**: *«El sistema se actualiza a las 03:00 — vas a ver un corte de ~1 minuto»*, que
   pasa a *«Actualizando…»* y después *«Listo, versión nueva»* (recarga sola). Cinco minutos antes,
   bloquea que se empiece una tizada nueva; **las que ya están corriendo se esperan** (no se corta
   un trabajo a la mitad).

**Cómo se aplica, sin que se pueda romper.** El programa **no puede reemplazarse a sí mismo mientras
corre** (Windows tiene los archivos tomados). Entonces lanza un ayudante suelto, `actualizador.py`,
y se apaga:
1. espera a que el puerto quede libre (o lo fuerza a los 60 s);
2. **respalda** la instalación actual en `_actualizacion/respaldo_<version>/` (código solamente:
   `datos\` y `entrada\` **no se tocan nunca** — el paquete ni siquiera los trae);
3. descomprime el paquete nuevo encima;
4. arranca el servidor y espera hasta 90 s a que `/api/salud` diga `ok`;
5. **si no responde o falla: restaura el respaldo, arranca la versión vieja** y deja el motivo
   anotado. El sistema **nunca** queda caído por una actualización mala.

**Programar la hora.** La hora elegida se guarda en `_actualizacion/pendiente.json`. Un hilo del
servidor la mira cada minuto y dispara solo. Si el servidor estaba apagado a esa hora, la aplica al
arrancar. Default sugerido: **03:00** (nadie trabajando).

**En el taller:** pantalla **Config → Publicación** con: versión de acá vs la publicada, los cambios
desde la última, el campo del token (se pega una vez), y **«Publicar»** con dos opciones —
*ahora* o *a las 03:00*. Por debajo: `empaquetar.py` arma el zip y se sube por HTTPS.

**Lo que NO hace (a propósito):** no toca `datos/` ni `entrada/` (eso es la Etapa 3), no toca nada
del sistema de stock, y no se puede disparar sin token.

### Etapa 2 — Publicar VERSIÓN (el código) desde la app
- Pantalla nueva **Config → Publicación**: qué versión corre en internet, qué versión hay en el
  taller, la lista de cambios, y el botón **Publicar**.
- Detrás: se empaqueta la versión (git tag), un servicio en el servidor la baja, instala
  dependencias, recompila el frontend, reinicia y chequea `/api/salud`. **Si falla, vuelve sola a la
  versión anterior** (rollback) y avisa.
- **Programar la actualización:** publicar ahora o dejarla agendada (ej. 3 AM), con aviso en
  pantalla a quien esté trabajando y bloqueo de generación durante los ~2 minutos que dura.
- **Cómo se verifica:** publicar un cambio de prueba, verlo en internet, y forzar una versión rota a
  propósito para comprobar que vuelve sola a la anterior.

### Etapa 3 — Publicar MOLDES / ARTES / CONFIG
- Misma pantalla, otra solapa: lista de moldes y diseños con su estado (**nuevo / modificado /
  igual**), tildás lo que querés y **Publicar seleccionados**.
- Sube los `.json` de `datos/` y los `.ai` de `entrada/` del molde elegido; **antes de pisar nada
  hace un respaldo** en el servidor y se puede deshacer.
- Las pantallas de setup en publicado pasan a sólo lectura (ver la regla de §2).
- ⚠️ **Depende de `PLAN_MSSQL.md`:** hoy los datos son archivos sueltos y publicar es copiar
  archivos (fácil). Con MSSQL adentro pasa a ser sincronizar filas entre dos bases (bastante más
  trabajo). **Conviene hacer esta etapa DESPUÉS de decidir si MSSQL entra antes o después** — si
  entra antes, esta etapa se diseña directamente contra la base y no se tira nada a la basura.
- **Cómo se verifica:** cambiar el nombre de una pieza en el taller, publicar sólo ese molde, y ver
  el cambio en internet **sin** que se toque ningún pedido ya cargado ahí.

### Etapa 4 — Operación
- Aviso de mantenimiento, registro de quién publicó qué y cuándo, alerta si el servidor se cae,
  limpieza automática de `piezas_cache` y `trabajos` viejos.

## 5. ORDEN SUGERIDO Y TAMAÑO

| Etapa | Tamaño aprox. | Deja algo usable |
|---|---|---|
| 0 — correr fuera de acá | chica | sí (corre en cualquier máquina) |
| 1 — servidor publicado | media (incluye trámites: VPS, dominio) | **sí: ya lo usás desde internet** |
| 2 — publicar versión | media | sí (actualizás con un botón) |
| 3 — publicar moldes/artes | media-grande (mirar MSSQL antes) | sí |
| 4 — operación | chica | sí |

Con la Etapa 1 ya tenés lo que pediste primero («levantarlo desde internet, usarlo y guardar»); las
actualizaciones se hacen a mano hasta que entre la Etapa 2.

## 6. RIESGOS / COSAS A NO OLVIDAR

- **El color es lo más frágil de mudar.** Antes de dar por buena la Etapa 1: generar la MISMA tizada
  en el taller y en el servidor y compararlas píxel a píxel (harness tipo `scratchpad/verif_tizada.py`).
- **`TIZADA_SECRET` fijo** en publicado o cada reinicio desloguea a todos.
- **Nunca publicar sobre datos sin respaldo previo** (regla dura del proyecto: no se pisan datos del
  usuario).
- Hoy **ningún endpoint valida permisos** (ver `molde-propio-desde-pedido`, entrega 4 pendiente).
  Con pocos usuarios de confianza es tolerable, pero **antes de que entre un cliente externo hay que
  cerrarlo**.
- El servidor no tiene auto-reload: toda subida implica reiniciar el proceso (por eso el rollback).

## 6.bis CAMINO ALTERNATIVO ELEGIDO POR EL USUARIO (2026-07-30): **desde su propia conexión, con IP fija**

En vez del EC2, el usuario decidió publicarlo **desde la PC del taller**, aprovechando que su
internet tiene **IP fija**. Decisiones suyas: **sin dominio** (se entra por la IP) · puerto público
**8443** · la IP local se fija con **reserva en el router**.

**Lo que quedó hecho y verificado (2026-07-30):**

| Pieza | Qué es |
|---|---|
| `PUBLICAR-EN-INTERNET.bat` | Arranca en modo `publicado`. Genera y guarda la clave de sesión la 1ª vez (`config_publicado.env`, gitignoreado — sin clave fija cada reinicio desloguea a todos). Toma el certificado si existe. |
| `GENERAR-CERTIFICADO.bat [IP]` | Certificado autofirmado (10 años) con **openssl, el que viene con Git** — no hace falta instalar nada. SAN: `localhost`, `127.0.0.1`, `192.168.0.120` y la IP pública si se le pasa. |
| `servidor.py` (`__main__`) | Si están `TIZADA_TLS_CERT`/`TIZADA_TLS_KEY`, el **TLS lo termina el propio servidor con cheroot** (waitress NO habla TLS). Sin ellos, waitress como antes. |
| `servidor.py` (arranque) | **ProxyFix ya NO se aplica cuando hay TLS propio**: sin un proxy delante, los `X-Forwarded-*` los manda el cliente y son falsificables (dejaba mentir la IP de origen y el esquema). |

**Verificado:** `https://localhost:8443/api/salud` y `https://192.168.0.120:8443/api/salud` responden
`ok=True`; la app carga por HTTPS; `/api/productos` sigue exigiendo sesión (401); un `http://` contra
el puerto seguro se rechaza. Certificado con los SAN correctos (`openssl x509 -ext subjectAltName`).

**Lo que le queda al usuario (no lo puedo hacer yo: son cambios de seguridad del sistema y del router):**
1. Abrir el **8443** en el Firewall de Windows (PowerShell **como administrador**).
2. En el router: **reenviar 8443 → 192.168.0.120:8443** y **reservar** esa IP para la MAC de la PC
   (hoy es DHCP: si cambia, el reenvío deja de funcionar).
3. Regenerar el certificado con su IP pública: `GENERAR-CERTIFICADO.bat <IP-PUBLICA>`.

⚠️ **NO correr los dos servidores a la vez** (el de siempre en 8050 y el publicado en 8443): son dos
procesos escribiendo los MISMOS `datos/`. El lock del catálogo es por proceso, no entre procesos.
⚠️ Y esto **no** son los dos ambientes de §2: es el MISMO sistema abierto a internet. Lo que toque
alguien de afuera en las pantallas de setup, se lo toca al taller.
⚠️ Al quedar expuesto a internet van a llegar **escaneos automáticos** al login: contraseñas largas
en todos los usuarios. La base MSSQL **no** se expone (sólo el 8443).

## 7. ESTADO

- **2026-07-30:** el usuario eligió publicar **desde su propia conexión con IP fija** (ver §6.bis),
  no el EC2. Hecho y verificado el lado del programa (modo publicado + HTTPS propio con cheroot +
  certificado autofirmado); falta lo que depende de él: firewall, router y la IP pública en el
  certificado.
- **2026-07-22:** plan escrito y decidido el VPS Windows.
- **2026-07-23:** **Etapa 2 COMPLETA** (motor + pantalla, verificados de punta a punta). Falta la
  ÚLTIMA instalación a mano en el servidor, la que lleva el receptor. Después: un botón.
- **2026-07-22:** **Etapa 1.a HECHA** — la app ya puede vivir en `/Tizadapro` (build con base,
  envoltorio de `fetch`, URLs sueltas prefijadas), verificada en el navegador contra un proxy que
  imita el nginx. Falta lo que depende del servidor (Etapa 1: instalar en el EC2 Windows y agregar
  el `location` al nginx) — **eso lo tiene que hacer el usuario, no tengo acceso**.
- **2026-07-22:** **Etapa 0 HECHA y verificada** (ver el detalle arriba). El programa ya corre en
  modo `publicado` con waitress, se niega a arrancar mal configurado y tiene `/api/salud`.
  **Próximo paso: Etapa 1** — necesita que el usuario contrate el VPS y el dominio; el trabajo de
  código que queda de nuestro lado antes de eso es cero (lo siguiente es instalar y configurar).
  Si se prefiere adelantar código, se puede arrancar la **Etapa 2** (pantalla de publicación +
  actualizador) apuntando primero contra el servidor de prueba local en el puerto 8060.
