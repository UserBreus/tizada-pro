"""Arma el PAQUETE DE PUBLICACIÓN: un .zip con todo lo que el servidor necesita para correr, y
NADA de lo que no (datos del usuario, dependencias de node, respaldos, scratchpad).

    py empaquetar.py                 → dist/TIZADAPRO_<version>_<commit>.zip  (frontend en /Tizadapro)
    py empaquetar.py --base /         → frontend en la raíz (si se publica en un dominio propio)
    py empaquetar.py --sin-frontend   → no recompila (usa el frontend/dist que ya esté)

POR QUÉ ASÍ y no `git clone` en el servidor: compilar el frontend (`npm install` + `vite build`)
necesita Node y **más de 1 GB de RAM** — justo lo que al servidor chico le falta. Se compila acá,
que sobra, y allá se descomprime y listo. Es además exactamente lo que va a mandar el botón de
actualizar (Etapa 2 de PLAN_PUBLICACION.md).

Los DATOS (datos/, entrada/) NO van en el paquete: son del usuario, van una sola vez y aparte.
"""
import os, sys, json, subprocess, zipfile, fnmatch

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "dist")

# Lo que SÍ viaja. Todo lo demás queda afuera (lista blanca: si mañana alguien deja un .rar de
# 300 MB en la raíz, no se cuela solo).
INCLUIR_ARCHIVOS = ["*.py", "requirements.txt", "VERSION", "publicado.bat", "iniciar.bat",
                    "INSTALAR.bat", "DIAGNOSTICO.bat", "*.md", "logo.svg"]
INCLUIR_CARPETAS = ["frontend/dist", "db", "catalogo_fuentes"]
EXCLUIR = ["empaquetar.py", "migrar_ids.py", "catalogo_fuentes/subida_*", "**/__pycache__/**"]

# Con `--completo` (primera instalación) el paquete lleva ADEMÁS:
#  • los perfiles ICC de esta máquina → sin ellos el color del servidor sale distinto;
#  • datos/ y entrada/ → los moldes y artes que ya están cargados.
# Así el servidor queda andando con UN archivo, sin que nadie tenga que copiar nada más.
PERFILES_ORIGEN = [
    r"C:\Program Files (x86)\Common Files\Adobe\Color\Profiles\Recommended",
    r"C:\Program Files\Common Files\Adobe\Color\Profiles\Recommended",
]


def _excluido(rel):
    return any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(rel, p.replace("**/", "*"))
               for p in EXCLUIR) or "__pycache__" in rel


def compilar_frontend(base):
    script = "build:publicado" if base != "/" else "build"
    print(f"  compilando frontend ({'base ' + base}) …")
    r = subprocess.run(["npm", "run", script], cwd=os.path.join(AQUI, "frontend"),
                       shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:]); print(r.stderr[-2000:])
        raise SystemExit("[ERROR] falló la compilación del frontend")
    idx = os.path.join(AQUI, "frontend", "dist", "index.html")
    with open(idx, encoding="utf-8") as fh:
        html = fh.read()
    # Guarda dura: si el index no quedó apuntando al prefijo, el servidor publicado serviría una
    # app que pide sus assets a la raíz del dominio (o sea, al otro sistema). Mejor cortar acá.
    if base != "/" and f'src="{base}assets/' not in html:
        raise SystemExit(f"[ERROR] el frontend NO quedó compilado en '{base}' (revisá vite.config.js)")
    print("  frontend OK")


def config_publicacion():
    """Config del TALLER para publicar: `datos/publicacion.json` con la dirección del servidor y la
    CLAVE de actualización. La clave se genera acá UNA vez y viaja dentro del paquete de
    instalación → los dos lados quedan con la misma sin que el usuario copie ni pegue nada
    (pedido explícito: «no voy a hacer más eso de copiar y pegar»). Nunca va al repositorio."""
    import secrets
    ruta = os.path.join(AQUI, "datos", "publicacion.json")
    cfg = {}
    try:
        with open(ruta, encoding="utf-8") as fh:
            cfg = json.load(fh)
    except Exception:
        pass
    if not cfg.get("token"):
        cfg["token"] = secrets.token_hex(32)
    cfg.setdefault("url", "https://administracionuser.uy/Tizadapro")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=1)
    return cfg


def version():
    v = "0.0.0"
    try:
        with open(os.path.join(AQUI, "VERSION"), encoding="utf-8") as fh:
            v = fh.read().strip() or v
    except OSError:
        pass
    try:
        c = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=AQUI,
                           capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        c = ""
    return v, c


def main():
    base = "/Tizadapro/"
    if "--base" in sys.argv:
        base = sys.argv[sys.argv.index("--base") + 1]
        if not base.endswith("/"):
            base += "/"
    if "--sin-frontend" not in sys.argv:
        compilar_frontend(base)

    completo = "--completo" in sys.argv
    v, commit = version()
    os.makedirs(SALIDA, exist_ok=True)
    destino = os.path.join(SALIDA, f"TIZADAPRO_{v}{('_' + commit) if commit else ''}"
                                   f"{'_COMPLETO' if completo else ''}.zip")

    n = 0
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        # La CLAVE de actualización viaja SIEMPRE (también en el paquete de actualización): así el
        # servidor y el taller quedan con la misma sin que nadie tipee nada. En especial, el primer
        # servidor se instaló ANTES de que existiera la clave y no la tiene: este paquete se la lleva.
        z.writestr("token_actualizacion.txt", config_publicacion()["token"]); n += 1
        print("  + clave de actualizacion")
        # CONEXIÓN CON EL SISTEMA DE STOCK (api-key de telas). Viaja con el paquete —mismo criterio
        # que la clave de actualización— para que el servidor publicado quede configurado solo, sin
        # tener que pegar la clave a mano en cada ambiente (pedido explícito del usuario).
        # NUNCA va al repositorio (config_externo.json está en .gitignore).
        _cfg_ext = os.path.join(AQUI, "config_externo.json")
        if os.path.isfile(_cfg_ext):
            z.write(_cfg_ext, "config_externo.json"); n += 1
            print("  + conexion con el sistema de stock (api-key)")
        else:
            print("  [!] sin config_externo.json: el publicado va a pedir la api-key de telas a mano")
        if completo:
            # perfiles ICC (van a `perfiles_icc/`, el instalador los deja apuntados)
            perf = next((d for d in PERFILES_ORIGEN if os.path.isdir(d)), None)
            if perf:
                for f in sorted(os.listdir(perf)):
                    if f.lower().endswith((".icc", ".icm")):
                        z.write(os.path.join(perf, f), f"perfiles_icc/{f}"); n += 1
                print(f"  + perfiles ICC de {perf}")
            else:
                print("  [!] no encontré los perfiles de Adobe: el color del servidor puede variar")
            # 2) datos y entrada (moldes y artes YA cargados)
            for carpeta in ("datos", "entrada"):
                raiz = os.path.join(AQUI, carpeta)
                if not os.path.isdir(raiz):
                    continue
                for dirpath, _d, files in os.walk(raiz):
                    # el caché de render NO viaja: se regenera solo y son cientos de MB
                    if "piezas_cache" in dirpath.replace("\\", "/"):
                        continue
                    for f in files:
                        ruta = os.path.join(dirpath, f)
                        z.write(ruta, os.path.relpath(ruta, AQUI).replace("\\", "/")); n += 1
                print(f"  + {carpeta}/")
        for f in sorted(os.listdir(AQUI)):
            if os.path.isfile(os.path.join(AQUI, f)) and not _excluido(f) \
               and any(fnmatch.fnmatch(f, p) for p in INCLUIR_ARCHIVOS):
                z.write(os.path.join(AQUI, f), f); n += 1
        for carpeta in INCLUIR_CARPETAS:
            raiz = os.path.join(AQUI, *carpeta.split("/"))
            if not os.path.isdir(raiz):
                raise SystemExit(f"[ERROR] falta {carpeta} (¿compilaste el frontend?)")
            for dirpath, _dirs, files in os.walk(raiz):
                for f in files:
                    ruta = os.path.join(dirpath, f)
                    rel = os.path.relpath(ruta, AQUI).replace("\\", "/")
                    if not _excluido(rel):
                        z.write(ruta, rel); n += 1

    # DEJAR EL TALLER COMO ESTABA: compilar para `/Tizadapro` pisa `frontend/dist`, que es lo que
    # sirve el servidor local → si no se recompila, la app de esta máquina queda pidiendo sus
    # archivos a `/Tizadapro/…` y no abre más. (Pasó al armar el primer paquete.)
    if "--sin-frontend" not in sys.argv and base != "/":
        print("\n  dejando el frontend del taller como estaba…")
        subprocess.run(["npm", "run", "build"], cwd=os.path.join(AQUI, "frontend"),
                       shell=True, capture_output=True, text=True)

    mb = os.path.getsize(destino) / 2**20
    print(f"\n  PAQUETE LISTO: {destino}")
    print(f"  {n} archivos · {mb:.1f} MB · versión {v} {commit} · frontend en '{base}'")
    if completo:
        print("\n  Este paquete trae TODO (código + perfiles de color + datos + entrada).")
        print("  En el servidor: descomprimir y clic DERECHO en INSTALAR.bat,")
        print("  'Ejecutar como administrador'. El instalador hace el resto.")
    else:
        print("\n  Paquete de ACTUALIZACIÓN (sin datos): descomprimir encima de la instalación.")
        print("  `datos\\` y `entrada\\` no se tocan.")


if __name__ == "__main__":
    main()
