# TIZADA PRO — poner el sistema en un servidor nuevo

Guía para instalar el sistema desde cero en un **Windows Server**. Pensada para que la siga
alguien que no conoce el proyecto.

> **El código está en el repositorio. Los SECRETOS y los DATOS no**, y no tienen que estarlo.
> Están listados en el punto 5: se pasan por otro medio.

---

## 1. Qué necesita la máquina

| Cosa | Versión | Para qué | Cómo se consigue |
|---|---|---|---|
| **Windows** | 10 / Server 2019+ | — | — |
| **Python** | 3.12+ | el sistema corre en Python | python.org (marcar *Add to PATH*) |
| **Node.js** | 20+ | compilar la pantalla | nodejs.org |
| **SQL Server** | 2019+ (sirve **Express**, es gratis) | la base | microsoft.com/sql-server |
| **ODBC Driver for SQL Server** | 17 o 18 | conectar Python con la base | «Microsoft ODBC Driver for SQL Server» |
| Ghostscript | cualquiera | **opcional** | sólo se usa si el arte trae contenido RGB |

> La pantalla se sirve **compilada**: Node hace falta para *construirla*, no para que el sistema
> funcione. Si preferís, se compila en otra máquina y se copia la carpeta `frontend/dist`.

---

## 2. Traer el código

```bash
git clone https://github.com/UserBreus/tizada-pro.git C:\TIZADAPRO
cd C:\TIZADAPRO
```

## 3. Instalar las dependencias

```bash
py -m pip install -r requirements.txt
```

```bash
cd frontend && npm install && npm run build && cd ..
```

`npm run build` deja la pantalla en `frontend/dist`. **Hay que rehacerlo cada vez que cambie el
código de `frontend/src`**, o el servidor sigue sirviendo la versión anterior (`/api/salud` avisa
si quedó vieja).

## 4. La base de datos

1. Crear una base llamada **`TizadaPro`** (o el nombre que quieras, va en `TIZADA_DB_NAME`).
2. Aplicar el esquema — es **idempotente**, crea sólo lo que falta:

```bash
py -c "import db; db.aplicar_schema(); print('esquema aplicado')"
```

3. Comprobar que conecta:

```bash
py -c "import db; print(db.valor('SELECT @@VERSION'))"
```

Por defecto usa `localhost\SQLEXPRESS` con autenticación de Windows. Para otro servidor o usuario,
ver las variables del punto 5.

## 5. 🔑 Lo que NO está en el repositorio y hay que pasar aparte

Nada de esto se versiona a propósito. Pasalo por un canal seguro (gestor de contraseñas, no por
chat ni por mail).

| Qué | Dónde va | Si falta |
|---|---|---|
| **Credenciales de SQL Server** | `TIZADA_DB_SERVER`, `TIZADA_DB_NAME`, y `TIZADA_DB_USER`/`TIZADA_DB_PASSWORD` si no se usa autenticación de Windows | el sistema no arranca |
| **`config_externo.json`** | raíz del proyecto — api-key de la API de **telas** (WMS) | no se pueden listar las telas |
| **`datos/publicacion.json`** | url + token del servidor publicado, para el botón «Publicar» | no se puede publicar desde el taller |
| **`secret.txt`** | raíz — clave de sesión. **`publicado.bat` la genera solo la primera vez**; si querés conservar las sesiones abiertas del servidor viejo, copiá la de allá | se cierran todas las sesiones |
| **Acceso al repositorio** | GitHub → *Settings → Collaborators* | no puede clonar |

**Variables de entorno** (se ponen en `publicado.bat`, ya está preparado):

| Variable | Para qué | Por defecto |
|---|---|---|
| `TIZADA_MODO` | `publicado` = servidor real (waitress). Sin esto usa el servidor de **desarrollo**, que corta las descargas grandes | `taller` |
| `TIZADA_SECRET` | clave de sesión | la genera `publicado.bat` |
| `PORT` / `HOST` | puerto y escucha | `8050` / `127.0.0.1` |
| `TIZADA_DB_SERVER` / `TIZADA_DB_NAME` | la base | `localhost\SQLEXPRESS` / `TizadaPro` |
| `TIZADA_DB_USER` / `TIZADA_DB_PASSWORD` | si no es autenticación de Windows | — |
| `TIZADA_DATOS` / `TIZADA_ENTRADA` / `TIZADA_TRABAJOS` | carpetas de datos (conviene otro disco, por el backup) | dentro del proyecto |
| `TIZADA_PROCESOS` | procesos de render. **Cada uno pesa ~200 MB** | hasta 6 |
| `TIZADA_HILOS` | hilos de waitress | 8 |

## 6. Los datos del sistema anterior

El repositorio trae el **programa**, no el contenido. Del servidor viejo hay que copiar:

| Carpeta | Qué tiene |
|---|---|
| `datos/` | catálogo, registros de piezas, configuración de cada molde |
| `entrada/` | los archivos de los moldes y los artes (`.ai`) |
| `catalogo_fuentes/` | las tipografías cargadas |

Y **la base de datos**: backup y restore de `TizadaPro`, o exportarla e importarla.

`trabajos/` **no hace falta copiarla**: son tizadas ya generadas.

## 7. Arrancar

Doble clic en **`publicado.bat`**, o:

```bash
cd C:\TIZADAPRO && publicado.bat
```

Tiene que decir `modo PUBLICADO · waitress`. Si dice otra cosa, está en modo desarrollo y las
descargas grandes se van a cortar.

Para que arranque solo al prender la máquina: Programador de tareas → nueva tarea → *Al iniciar el
sistema* → acción: `C:\TIZADAPRO\publicado.bat`, marcando **«Ejecutar aunque el usuario no haya
iniciado sesión»**.

## 8. HTTPS y el proxy de adelante

El sistema escucha en `127.0.0.1:8050` **a propósito**: el que da la cara a internet es un proxy
(IIS, nginx o el que uses) que pone el certificado y reenvía a ese puerto. El sistema ya viene
preparado para vivir bajo un subcamino (`https://…/Tizadapro`).

Si la pantalla queda en blanco o los archivos se cortan, revisar **en este orden**: que esté en
modo `publicado`, y que el disco tenga espacio (ver punto 10).

## 9. Comprobar que quedó bien

Abrir `https://…/api/salud`. Tiene que decir `"ok": true` y `"fallas": []`. Ahí se ve, uno por uno:
la base, el disco, los perfiles de color, y si la pantalla está compilada al día.

## 10. Mantenimiento

**El disco lleno rompe todo y de formas que no parecen de disco**: al publicar da «HTTP Error 500»,
las descargas se cortan en el navegador y generar la tizada falla con `std::bad_alloc` (Windows no
puede agrandar el archivo de paginación). `trabajos/` crece sin límite: guarda **todas** las tizadas
generadas.

Correr **`LIBERAR-ESPACIO.bat`** cada tanto. Borra sólo lo que se puede volver a generar y **nunca
toca `datos/` ni `entrada/`**.

## 11. Para entender el sistema

- **`MAPA_DEL_SISTEMA.md`** — el cerebro: arquitectura, modelo de datos, invariantes, trampas
  conocidas y el changelog. **Leerlo antes de tocar código.**
- **`MANUAL_HERRAMIENTAS.md`** — qué hace cada herramienta y los pasos para usarla.
- **`CLAUDE.md`** — las reglas del proyecto.
- `verificar_*.py` en la raíz — contratos ejecutables. Correrlos después de tocar lo que cubren.
