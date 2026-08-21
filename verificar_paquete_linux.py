"""
CONTRATO DEL PAQUETE QUE VIAJA A LINUX — `py verificar_paquete_linux.py`

El taller es **Windows** y el servidor publicado es **Linux**: el paquete cruza de un sistema
al otro y hay diferencias que no avisan, sólo rompen del otro lado.

  · Una ruta guardada con `\\` dentro del zip: Windows la abre bien y Linux crea **un archivo
    llamado «frontend\\dist\\index.html»** en vez de la carpeta. El sistema arranca sin pantalla.
  · Linux **distingue mayúsculas**: `import Db` funciona en Windows con `db.py` y allá no.
  · Dos archivos que sólo difieren en mayúsculas conviven en Linux y en Windows se pisan.
  · Las tipografías **cargadas a mano** en el taller: si no viajan, el servidor publicado estampa
    con el reemplazo temporal y **nadie se entera hasta ver la tela impresa**.

Audita el último paquete de `dist/`; si no hay ninguno, revisa el árbol de trabajo. No toca red.
"""
import fnmatch
import glob
import os
import re
import sys
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
FALLOS = []


def _falla(t):
    FALLOS.append(t)


# ── De dónde sacamos los archivos: el paquete real si existe, si no el árbol ─────────────
_zips = [p for p in glob.glob(os.path.join(AQUI, "dist", "*.zip")) if "COMPLETO" not in p]
if _zips:
    _z = max(_zips, key=os.path.getmtime)
    _zf = zipfile.ZipFile(_z)
    NOMBRES = _zf.namelist()
    def leer(n):
        return _zf.read(n).decode("utf-8", "replace")
    ORIGEN = f"paquete {os.path.basename(_z)}"
else:
    import empaquetar as EMP
    NOMBRES = []
    for f in sorted(os.listdir(AQUI)):
        if os.path.isfile(os.path.join(AQUI, f)) and not EMP._excluido(f) \
           and any(fnmatch.fnmatch(f, p) for p in EMP.INCLUIR_ARCHIVOS):
            NOMBRES.append(f)
    for carpeta in EMP.INCLUIR_CARPETAS:
        raiz = os.path.join(AQUI, *carpeta.split("/"))
        for dp, _d, fs in os.walk(raiz):
            for f in fs:
                rel = os.path.relpath(os.path.join(dp, f), AQUI).replace("\\", "/")
                if not EMP._excluido(rel):
                    NOMBRES.append(rel)
    def leer(n):
        with open(os.path.join(AQUI, *n.split("/")), encoding="utf-8", errors="replace") as fh:
            return fh.read()
    ORIGEN = "árbol de trabajo (no hay paquete en dist/)"

# ── 1. Separadores de ruta ──────────────────────────────────────────────────────────────
# Nota de la vez que se intentó falsear este caso para verlo fallar: NO se pudo. `zipfile` de
# Python normaliza `os.sep` a `/` al escribir, así que nuestro empaquetador **no puede** generar
# rutas con barra invertida. La comprobación queda igual: cuesta nada y cubre un paquete armado
# de otra forma (7-zip, a mano, otro script). Que no salte no significa que no sirva.
malas = [n for n in NOMBRES if "\\" in n]
if malas:
    _falla(f"{len(malas)} rutas guardadas con barra invertida (ej. {malas[0]!r}): en Linux se "
           f"crean como UN archivo con ese nombre, no como carpetas")

# ── 2. Rutas absolutas o que se escapan de la carpeta ───────────────────────────────────
raras = [n for n in NOMBRES if n.startswith("/") or n.startswith("..") or re.match(r"^[A-Za-z]:", n)]
if raras:
    _falla(f"{len(raras)} rutas absolutas o con '..' (ej. {raras[0]!r}): descomprimir escribiría "
           f"fuera de la carpeta del sistema")

# ── 3. Nombres que sólo difieren en mayúsculas ──────────────────────────────────────────
vistos = {}
for n in NOMBRES:
    vistos.setdefault(n.lower(), []).append(n)
choques = [v for v in vistos.values() if len(v) > 1]
if choques:
    _falla(f"archivos que sólo difieren en mayúsculas ({choques[0]}): en Windows se pisan entre sí")

# ── 4. Los `import` propios tienen que coincidir EXACTO con el nombre del archivo ────────
raiz_py = {n for n in NOMBRES if n.endswith(".py") and "/" not in n}
bajas = {n.lower(): n for n in raiz_py}
for n in sorted(raiz_py):
    for m in set(re.findall(r"^\s*(?:import|from)\s+([a-zA-Z_]\w*)", leer(n), re.M)):
        real = bajas.get(f"{m}.py".lower())
        if real and real != f"{m}.py":
            _falla(f"{n}: `import {m}` pero el archivo se llama `{real}` — en Linux no lo encuentra")

# ── 5. Las tipografías cargadas a mano viajan ───────────────────────────────────────────
# (si no, el servidor publicado estampa con el reemplazo temporal y sale mal impreso)
_dir_f = os.path.join(AQUI, "catalogo_fuentes")
if os.path.isdir(_dir_f):
    locales = {f for f in os.listdir(_dir_f)
               if f.startswith("subida_") and f.lower().endswith((".ttf", ".otf"))}
    en_paq = {os.path.basename(n) for n in NOMBRES if n.startswith("catalogo_fuentes/")}
    faltan = sorted(locales - en_paq)
    if faltan:
        _falla(f"{len(faltan)} tipografías cargadas en el taller NO viajan (ej. {faltan[0]}): "
               f"allá el diseño se estampa con el reemplazo temporal y sale mal impreso")

# ── 6. La pantalla compilada apunta a donde el servidor la sirve ────────────────────────
idx = [n for n in NOMBRES if n.endswith("frontend/dist/index.html")]
if not idx:
    _falla("el paquete no trae `frontend/dist/index.html`: el servidor quedaría sin pantalla")
else:
    html = leer(idx[0])
    src = re.findall(r'src="([^"]+\.js)"', html)
    if not src:
        _falla("el index.html compilado no referencia ningún .js")
    else:
        try:
            import json
            with open(os.path.join(AQUI, "datos", "publicacion.json"), encoding="utf-8") as fh:
                url = json.load(fh).get("url") or ""
            from urllib.parse import urlparse
            ruta = urlparse(url).path.strip("/")
            esperado = f"/{ruta}/assets/" if ruta else "/assets/"
            if not src[0].startswith(esperado):
                _falla(f"la pantalla está compilada para `{src[0]}` pero el destino "
                       f"({url}) la sirve en `{esperado}`: todos los archivos darían 404 "
                       f"(pantalla en blanco con el servidor sano)")
        except FileNotFoundError:
            pass          # sin destino configurado no hay contra qué comparar

print(f"revisado: {ORIGEN} — {len(NOMBRES)} archivos")
if FALLOS:
    print(f"\nx EL PAQUETE NO ESTÁ LISTO PARA LINUX ({len(FALLOS)}):\n")
    for f in FALLOS:
        print("    -", f)
    sys.exit(1)
print("OK paquete: rutas, mayúsculas, imports, tipografías cargadas y pantalla compilada "
      "para la dirección del destino")
