# TIZADA PRO — todo lo que necesitás para tomar el proyecto

Este documento es el punto de entrada para un programador que recibe el sistema. Está pensado
para que puedas **levantarlo, entenderlo y modificarlo sin romper nada**.

Orden de lectura sugerido:

1. Este archivo (arranque y mapa general).
2. **`CLAUDE.md`** — las reglas duras del proyecto. **No son sugerencias**: romper una de esas
   reglas arruina material impreso, que es plata y tela perdida.
3. **`MAPA_DEL_SISTEMA.md`** — el cerebro: arquitectura, modelo de datos, invariantes, trampas
   conocidas, endpoints y el registro de todos los cambios con su porqué.
4. **`MANUAL_HERRAMIENTAS.md`** — los pasos exactos de cada herramienta de la aplicación.

---

## 1. Qué es esto

Software de producción para un **taller de sublimación textil**. Toma:

- un **molde** (`.ai` de Illustrator, o `.pdf` de Corel, o `.dxf` de Optitex) con las piezas de
  la prenda en todos los talles,
- un **diseño/arte** (`.ai`) con el estampado de cada pieza,
- una **planilla del pedido** (quién, qué talle, qué nombre y número lleva),

y produce la **tizada**: uno o varios PDF con todas las piezas acomodadas sobre el ancho de la
tela, listos para mandar al RIP y estampar. Además saca una **ficha técnica** en A4 para el taller.

> ⚠️ **Es un sistema de producción real, en uso.** Lo que sale mal acá se imprime sobre tela y se
> tira. Antes de tocar el motor, leé los invariantes del `MAPA_DEL_SISTEMA.md`.

**Alcance**: hoy corre en `localhost` en el taller, pero el objetivo es una **app web para
clientes**, asociada a un sistema que usa **MSSQL**. No asumas "app local de un solo usuario":
si el alcance importa para una decisión, preguntá.

---

## 2. Requisitos

| Qué | Versión con la que corre hoy | Para qué |
|---|---|---|
| **Python** | 3.12 | todo el backend y el motor |
| **Node.js + npm** | 24 / 11 | compilar la pantalla (React + Vite) |
| **SQL Server** | — | base de datos (catálogo, usuarios, moldes) |
| **ODBC Driver for SQL Server** | 17 o 18 | lo usa `pyodbc` |
| **Ghostscript** | 10.x (opcional) | sólo para unificar RGB/CMYK mezclados |

Sistema operativo: se desarrolla y corre en **Windows**. Hay partes específicas de Windows
(el Job Object que ata los procesos hijos al servidor, en `servidor.py`).

---

## 3. Levantarlo por primera vez

```bash
git clone https://github.com/UserBreus/tizada-pro.git
cd tizada-pro
git checkout entrega-programadores
```

**Backend:**

```bash
py -m pip install -r requirements.txt
```

**Pantalla (frontend):**

```bash
cd frontend
npm install
npm run build
```

**Arrancar:**

```bash
py servidor.py
```

Abrí `http://localhost:8050`.

> **La pantalla se sirve desde `frontend/dist`, no desde `src`.** Si tocás `frontend/src/App.jsx`
> tenés que correr `npm run build` otra vez o no vas a ver el cambio.
>
> **El servidor no tiene recarga automática.** Si tocás un `.py`, reinicialo o vas a seguir
> ejecutando el código viejo en memoria. (`TIZADA_RELOAD=1` activa la recarga, pero ojo: reinicia
> el proceso ante cualquier cambio y puede cortar una tizada en curso.)

En VS Code hay tareas listas (`.vscode/tasks.json`): *Servidor TIZADA PRO (8050)* — que además
libera el puerto si quedó ocupado —, *Recompilar el front (dist)* y *Parar el servidor*.

---

## 4. Configuración

### Base de datos (MSSQL)

Por variables de entorno:

| Variable | Qué es |
|---|---|
| `TIZADA_DB_SERVER` | host\instancia |
| `TIZADA_DB_NAME` | nombre de la base |
| `TIZADA_DB_USER` / `TIZADA_DB_PASSWORD` | credenciales |
| `TIZADA_DB_DRIVER` | ej. `ODBC Driver 17 for SQL Server` |

La capa de acceso está en `db.py`. El plan y el modelo de datos están en `PLAN_MSSQL.md`.

### API externa de telas

Las telas **no se crean en el sistema**: vienen de una API externa. La clave va en
`config_externo.json` (no versionado) o en la variable `EXTERNAL_API_KEY`. Nunca en el código.

### Otras variables útiles

| Variable | Para qué |
|---|---|
| `PORT` / `HOST` | dónde escucha (por defecto 8050 / 0.0.0.0) |
| `TIZADA_DATOS`, `TIZADA_ENTRADA`, `TIZADA_TRABAJOS`, `TIZADA_FUENTES` | mover las carpetas de trabajo (los tests las usan para aislarse) |
| `TIZADA_PROCESOS` | cuántos procesos de render en paralelo. **Cada uno pesa ~200 MB**: bajalo a 2 en un servidor chico |
| `TIZADA_SECRET` | clave de sesión. **Obligatoria en modo publicado** |
| `TIZADA_MODO` | `taller` (default) o `publicado` |
| `TIZADA_RELOAD` | `1` activa la recarga automática al editar Python |

---

## 5. Qué hay en el repo y qué no

**No se versiona** (y no está en la rama de entrega): `datos/` (la base en JSON y las cachés),
`entrada/` (los moldes y diseños del cliente), `trabajos/` (las tizadas generadas),
`certificados/`, `config_externo.json` (claves). Para trabajar en serio vas a necesitar que te
pasen un molde y un diseño de ejemplo.

**Módulos del backend** (los que importan):

| Archivo | Qué hace |
|---|---|
| `servidor.py` | servidor web y todos los endpoints. Es grande: usá la lista de endpoints del MAPA |
| `motor_pedido.py` | **el motor**: arma cada pieza, la estampa y produce la tizada |
| `molde_real.py` | lee el `.ai` del molde: contornos por capa y por talle |
| `nesting_contorno.py` | acomoda las piezas sobre la tela (true-shape) y compone el PDF de la hoja |
| `aplanar_rip.py` | deja la hoja como la deja Illustrator para que el RIP no falle. **Sin Ghostscript**: preserva el CMYK exacto |
| `texto_curvas.py` | convierte el texto a curvas (contornos vectoriales reales) |
| `ficha_tecnica.py` | el PDF A4 que acompaña a la tizada |
| `piezas_molde.py` | agregar piezas nuevas al molde |
| `objetos_agregados.py` | objetos que el usuario agrega al diseño (versiona el arte) |
| `importar_dxf.py` | importar moldes `.dxf` (AAMA / Optitex) |
| `db.py`, `auth.py`, `api_usuarios.py` | base de datos, usuarios, roles y permisos |
| `variantes_molde.py` | nombrar los talles de un molde |
| `actualizaciones.py`, `actualizador.py`, `empaquetar.py` | publicar versiones al servidor remoto |

**La pantalla** es un solo archivo: `frontend/src/App.jsx` (~15.600 líneas, React). Es grande:
buscá por el texto que ves en pantalla para ubicarte rápido.

---

## 6. Cómo se usa (el flujo que hay que respetar)

El pedido tiene 4 pasos, y ese orden es el que espera el usuario:

1. **Diseños** — se crean los "espacios" de trabajo y se les asignan uno o más moldes.
   Cada espacio es **autónomo**: sus telas, sus diseños y sus variables no se mezclan con los otros.
2. **Arte** — se carga el diseño y se ve cómo queda sobre cada pieza del molde.
3. **Planilla** — la lista de prendas: talle, nombre, número, diseño, tela.
4. **Tizadas** — se genera. Sale el PDF por tela + la ficha técnica.

**Conceptos que se confunden y conviene tener claros desde el día uno:**

- **VARIABLE** = qué piezas lleva la prenda (por ejemplo "con costadillo"). En el código aparece
  como `variante` / `v_xxx`, que es confuso: leé la nota de terminología en el MAPA.
- **VARIANTE** = el talle.
- **ESPACIO** ≠ **DISEÑO**: el "espacio" es la primera opción del paso 1; el "diseño" es el `.ai`
  del arte.

---

## 7. Reglas que no se negocian

Están completas en `CLAUDE.md`. Las que más caro se pagan:

- **Siempre el vector original.** Nunca rasterizar ni modificar el archivo del usuario. El único
  píxel admitido es una imagen que ya venga incrustada en su `.ai`. Si algo va lento, se hace
  **menos trabajo**, nunca menos calidad.
- **Lo que se ve en el Arte es exactamente lo que se imprime.** Si un cambio rompe esa igualdad,
  está mal.
- **Colores CMYK exactos**: nada de Ghostscript ni de re-cuantizar en el camino de la tizada.
- **PyMuPDF y pikepdf no son thread-safe**: para paralelizar se usan **procesos**, nunca hilos.
- **Nunca borrar ni sobrescribir datos del usuario** al probar (`datos/`, `entrada/`,
  `catalogo_fuentes/`). Para probar algo destructivo, copia aparte.
- **La generación de la tizada tiene que poder avanzar siempre.** No la pongas detrás de un lock
  que también use la pantalla (se probó y dejó la generación clavada).

---

## 8. Cómo verificar que no rompiste nada

Hay contratos ejecutables en la raíz. Cada uno levanta el sistema **aislado** (copia de los datos
en un temporal) y verifica un comportamiento con archivos reales:

```bash
py verificar_piezas.py             # identidad y nombres de piezas
py verificar_ficha_disenos.py      # la ficha trae un molde guía por diseño
py verificar_ficha_piezas_pedido.py# la ficha muestra las piezas que se pidieron
py verificar_etiqueta_posicion.py  # la etiqueta cae donde se configuró
py verificar_etiqueta_tamano.py    # el tamaño en mm es el de la letra
py verificar_mesa_larga.py         # hojas de más de 5 m (UserUnit)
py verificar_arte_liviano.py       # el arte pesado no viaja dentro del JSON
py verificar_agregar_pieza.py      # agregar una pieza renumera bien las demás
py verificar_traba_pedido.py       # el pedido se frena si falta tela o una opción
py verificar_permisos_molde.py     # autoría / privacidad / permisos
py medir_nesting.py                # cuánto aprovecha la tela el nesting
```

**Al terminar de trabajar, revisá que no queden procesos sueltos**: cada proceso de render pesa
~200 MB y si se acumulan la máquina se pone lenta sin que se note por qué.

---

## 9. Trampas que ya costaron caro

Están todas documentadas en el MAPA, pero estas te van a ahorrar horas:

- **El rasterizador de SVG de PyMuPDF ignora las etiquetas `<image>`.** Comparar dos SVG
  rasterizándolos con PyMuPDF da "idéntico" siempre, aunque las imágenes sean distintas.
- **`open(..., "w")` en Windows convierte `\n` en `\r\n`.** Si escribís un SVG o un `.py` así,
  deja de ser byte a byte lo que generaste. Usá `newline=""`.
- **`ctypes` sin declarar `restype`/`argtypes` trunca los HANDLE en 64 bits** y falla en silencio.
- **El PDF topa en 5,08 m** de alto. Para hojas más largas se usa `/UserUnit` (PyMuPDF ya lo
  aplica al leer; pikepdf no).
- **Un test no puede "aislarse" sólo con `TIZADA_DATOS`**: la base sale de `TIZADA_DB_*`. Para
  aislar de verdad hay que reemplazar el módulo `db` en `sys.modules` antes de importar `servidor`.

---

## 10. Pendientes principales

1. **Rendimiento de la tizada.** Un pedido de 38 prendas tarda ~3 minutos. Más de la mitad se va
   en **volver a preparar cada hoja para el RIP** (`aplanar_rip.py`): se arma el PDF de una forma
   y después se reescribe entero a otra. La mejora de fondo es **generar la hoja ya en ese formato**.
   Además, la tizada **rehace las piezas que el paso Arte ya dibujó**: hoy no comparten el
   resultado guardado.
2. **Aprovechamiento del nesting.** Medido: girar 90° ahorra un 3,5% de tela y el preset actual
   rinde peor que no girar. Herramienta: `medir_nesting.py`.
3. **Permisos.** Hoy los endpoints no validan permisos de molde de forma pareja.
4. **Migración a MSSQL.** Ver `PLAN_MSSQL.md`: todavía hay datos en JSON sueltos.

---

## 11. Una costumbre del proyecto

`MAPA_DEL_SISTEMA.md` **se actualiza junto con el código, en el mismo commit**: la sección que
corresponda y el changelog del final, incluyendo **lo que salió mal y por qué**. Ese archivo es lo
que hace que alguien pueda retomar el proyecto sin volver a pagar los errores ya pagados. Mantenelo.
