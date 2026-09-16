# -*- coding: utf-8 -*-
"""TIZADA PRO COMO APLICACIÓN DE WINDOWS.

Pedido del usuario (2026-09-16): «una copia del sistema pero instalable, que sea aplicación y
funcione como aplicación de Windows y no del navegador». Decisiones suyas: **el sistema completo
adentro de la PC** (no una ventana a un servidor) y **arranca vacía** (sin moldes ni diseños).

Qué hace este archivo, en orden:
  1. Una sola instancia: si la app ya está abierta, trae su ventana al frente y sale.
  2. Abre YA la ventana (motor de Edge, WebView2) con un cartel «Abriendo…»: nada de esperar a
     ciegas los segundos que tarda en cargar el motor.
  3. Busca el SQL Server de esta PC. El sistema lo necesita para guardar moldes y piezas: si no
     hay, la ventana lo explica y ofrece bajarlo, en vez de abrir un sistema que no guarda nada.
  4. La primera vez crea SU base (`TizadaPro_Escritorio`, nunca la del sistema del taller) y pide
     el usuario administrador en la misma ventana.
  5. Levanta el servidor de siempre (`servidor.arrancar()`) en un hilo, en 127.0.0.1 (nadie de la
     red entra), y cuando contesta muestra el sistema.
  6. Al cerrar la ventana se apaga todo: el Job de Windows se lleva los procesos de dibujo.

🔴 DATOS APARTE. Todo lo del usuario vive en `%LOCALAPPDATA%\\TIZADA PRO` (moldes, diseños,
tizadas, tipografías subidas, registro, estado de la ventana): desinstalar o actualizar el
programa no lo toca, y el sistema del taller (su carpeta y su base) tampoco.

⚠️ Lo que corre al importar este módulo tiene que ser LIVIANO: cada proceso de dibujo del pool
vuelve a ejecutar el programa desde arriba hasta `freeze_support()` (así arranca `spawn` en una
app congelada). Por eso todo el trabajo está adentro de funciones.
"""
import os
import sys

# En una app de ventana (sin consola) `sys.stdout` es None y más de una biblioteca escribe ahí sin
# preguntar. Va ANTES de `freeze_support`, que es donde los procesos de dibujo se desvían: ellos
# también lo necesitan.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import multiprocessing  # noqa: E402

NOMBRE = "TIZADA PRO"
BASE_DB = "TizadaPro_Escritorio"
PUERTO_PREFERIDO = 8765
_MUTEX = None


# ══ RUTAS ═══════════════════════════════════════════════════════════════════════════════════
def congelado():
    return bool(getattr(sys, "frozen", False))


def carpeta_programa():
    """Donde están el código y lo que viene con el programa (sólo lectura en la práctica)."""
    if congelado():
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def carpeta_datos():
    """Donde vive TODO lo del usuario. `TIZADA_ESCRITORIO_DATOS` la cambia (pruebas)."""
    d = os.environ.get("TIZADA_ESCRITORIO_DATOS")
    if not d:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        d = os.path.join(base, NOMBRE)
    os.makedirs(d, exist_ok=True)
    return d


def _log(msg):
    """Registro del lanzador: `logs/escritorio.log` en la carpeta de datos."""
    try:
        import time
        ruta = os.path.join(carpeta_datos(), "logs", "escritorio.log")
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "a", encoding="utf-8") as fh:
            fh.write(time.strftime("%d/%m/%Y %H:%M:%S ") + str(msg) + "\n")
    except Exception:
        pass


def _config():
    import json
    try:
        with open(os.path.join(carpeta_datos(), "config_escritorio.json"), encoding="utf-8") as fh:
            return json.load(fh) or {}
    except Exception:
        return {}


def _guardar_config(cfg):
    import json
    ruta = os.path.join(carpeta_datos(), "config_escritorio.json")
    with open(ruta + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
    os.replace(ruta + ".tmp", ruta)


def preparar_entorno():
    """Carpetas de datos + variables que lee el servidor. Va ANTES de importar `db`/`servidor`:
    los dos leen el entorno al importarse, y los procesos de dibujo lo heredan tal cual."""
    datos = carpeta_datos()
    prog = carpeta_programa()
    rutas = {
        "TIZADA_DATOS": os.path.join(datos, "datos"),
        "TIZADA_ENTRADA": os.path.join(datos, "entrada"),
        "TIZADA_TRABAJOS": os.path.join(datos, "trabajos"),
        "TIZADA_FUENTES": os.path.join(datos, "catalogo_fuentes"),
        "TIZADA_LOGS": os.path.join(datos, "logs"),
    }
    for k, v in rutas.items():
        os.makedirs(v, exist_ok=True)
        os.environ[k] = v
    # Las tipografías del sistema (Anton, la predeterminada, y las de muestra) se copian UNA vez;
    # las que suba el usuario quedan en la misma carpeta y nunca se pisan.
    base_fuentes = os.path.join(prog, "catalogo_fuentes_base")
    if os.path.isdir(base_fuentes):
        import shutil
        for f in os.listdir(base_fuentes):
            dst = os.path.join(rutas["TIZADA_FUENTES"], f)
            if not os.path.exists(dst):
                try:
                    shutil.copy2(os.path.join(base_fuentes, f), dst)
                except OSError as e:
                    _log(f"no se pudo copiar la tipografía {f}: {e}")
    # Los perfiles de color: sin ellos el color sale distinto en una PC sin Adobe instalado.
    perfiles = os.path.join(prog, "perfiles_icc")
    if os.path.isdir(perfiles) and not os.environ.get("TIZADA_PERFILES"):
        os.environ["TIZADA_PERFILES"] = perfiles
    os.environ["HOST"] = "127.0.0.1"          # sólo esta PC: nadie de la red entra a la app
    # 🔴 SE FIJA, NO `setdefault`: si esta PC tuviera `TIZADA_DB_NAME` puesto para el sistema del
    # taller, la app escribiría en la base de verdad. Sólo manda su propia variable (pruebas).
    os.environ["TIZADA_DB_NAME"] = (os.environ.get("TIZADA_ESCRITORIO_DB")
                                    or _config().get("db_nombre") or BASE_DB)
    os.environ["TIZADA_ESCRITORIO"] = "1"
    os.environ.pop("TIZADA_RELOAD", None)
    os.environ.pop("MODO", None)              # modo taller: un solo usuario, sin actualizador
    return datos


# ══ UNA SOLA INSTANCIA ══════════════════════════════════════════════════════════════════════
def ya_abierta():
    """True si la app ya está corriendo (y en ese caso trae su ventana al frente)."""
    global _MUTEX
    if os.name != "nt":
        return False
    import ctypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW.restype = ctypes.c_void_p
    _MUTEX = k32.CreateMutexW(None, False, "Local\\TizadaProEscritorio")
    if ctypes.get_last_error() != 183:        # ERROR_ALREADY_EXISTS
        return False
    u32 = ctypes.WinDLL("user32", use_last_error=True)
    u32.FindWindowW.restype = ctypes.c_void_p
    hwnd = u32.FindWindowW(None, NOMBRE)
    if hwnd:
        u32.ShowWindow(ctypes.c_void_p(hwnd), 9)          # SW_RESTORE
        u32.SetForegroundWindow(ctypes.c_void_p(hwnd))
    return True


# ══ SQL SERVER ══════════════════════════════════════════════════════════════════════════════
def candidatos_sql():
    """Los SQL Server instalados en esta PC, según el registro de Windows (más los de siempre)."""
    vistos, out = set(), []

    def _add(s):
        if s and s.lower() not in vistos:
            vistos.add(s.lower())
            out.append(s)

    _add(os.environ.get("TIZADA_ESCRITORIO_DB_SERVER"))
    _add(_config().get("db_servidor"))
    try:
        import winreg
        for vista in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                   r"SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL",
                                   0, winreg.KEY_READ | vista)
            except OSError:
                continue
            i = 0
            while True:
                try:
                    nombre, _v, _t = winreg.EnumValue(k, i)
                except OSError:
                    break
                i += 1
                _add("localhost" if nombre.upper() == "MSSQLSERVER" else f"localhost\\{nombre}")
    except Exception:
        pass
    for s in (r"localhost\SQLEXPRESS", "localhost"):
        _add(s)
    return out


def buscar_sql():
    """(servidor, None) del primero que contesta, o (None, detalle) si no hay ninguno."""
    import pyodbc
    try:
        cands = [d for d in pyodbc.drivers() if "SQL Server" in d]
    except Exception as e:
        return None, f"no se pudo leer los drivers de base de datos: {e}"
    if not cands:
        return None, "esta PC no tiene ningún driver de SQL Server"
    nuevos = sorted([d for d in cands if "ODBC Driver" in d],
                    key=lambda d: int("".join(c for c in d if c.isdigit()) or 0), reverse=True)
    driver = nuevos[0] if nuevos else "SQL Server"
    probados = []
    for srv in candidatos_sql():
        try:
            cn = pyodbc.connect(f"DRIVER={{{driver}}};SERVER={srv};DATABASE=master;"
                                "Trusted_Connection=yes;TrustServerCertificate=yes;", timeout=4)
            cn.close()
            return srv, None
        except Exception as e:
            probados.append(f"{srv}: {str(e)[:120]}")
    return None, "; ".join(probados) or "no hay SQL Server instalado"


def preparar_base(servidor_sql):
    """Crea la base propia de la app (si falta) y aplica el esquema. Devuelve True si ya hay
    usuarios (se puede entrar) o False si hay que crear el administrador.

    🔴 SÓLO SE TOCA LA BASE DE LA APP. Si ya existe una con ese nombre y tiene tablas que no son de
    TIZADA PRO, no se toca nada: es de otro sistema (el mismo seguro del instalador del servidor)."""
    os.environ["TIZADA_DB_SERVER"] = servidor_sql
    import re
    import db
    import auth
    db.DB_SERVER = servidor_sql
    nueva = db.crear_base()
    if not nueva:
        with open(os.path.join(carpeta_programa(), "db", "schema.sql"), encoding="utf-8") as fh:
            propias = {m.group(1).lower() for m in re.finditer(
                r"(?im)^\s*CREATE\s+TABLE\s+\[?(?:dbo\]?\.\[?)?([A-Za-z_][A-Za-z0-9_]*)", fh.read())}
        ajenas = [t for t in db.tablas() if t.lower() not in propias]
        if ajenas:
            raise RuntimeError(f"la base «{db.DB_NAME}» ya existe y es de otro sistema "
                               f"(tiene {', '.join(ajenas[:5])}). No se tocó nada.")
    db.aplicar_schema()
    auth.sincronizar_permisos()
    auth.sincronizar_roles()
    cfg = _config()
    cfg.update({"db_servidor": servidor_sql, "db_nombre": db.DB_NAME})
    _guardar_config(cfg)
    return (db.valor("SELECT COUNT(*) FROM usuario") or 0) > 0


def crear_admin(usuario, nombre, clave):
    import auth
    import db
    if (db.valor("SELECT COUNT(*) FROM usuario") or 0) > 0:
        raise ValueError("ya hay un administrador creado")
    auth.crear_usuario(usuario, nombre or usuario, clave, roles=["admin"])


# ══ SERVIDOR ════════════════════════════════════════════════════════════════════════════════
def _responde(puerto):
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/salud", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def _libre(puerto):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", puerto))
        return True
    except OSError:
        return False
    finally:
        s.close()


def elegir_puerto():
    """El de siempre si está libre (así la ventana recuerda lo que el usuario dejó: el navegador
    guarda por dirección). Si lo ocupa OTRO programa no se lo mata: se usa el siguiente libre."""
    pref = int(_config().get("puerto") or PUERTO_PREFERIDO)
    for p in [pref] + list(range(PUERTO_PREFERIDO, PUERTO_PREFERIDO + 40)):
        if _libre(p):
            if p != pref:
                cfg = _config()
                cfg["puerto"] = p
                _guardar_config(cfg)
            return p
    raise RuntimeError("no hay ningún puerto libre para el servidor interno")


def _sin_ventanas_de_consola():
    """El servidor llama a programas de consola (netstat, taskkill, git, Ghostscript). Desde una
    app de ventana cada uno abriría una consola negra un instante: se las pide ocultas."""
    if os.name != "nt":
        return
    import subprocess
    _orig = subprocess.Popen.__init__
    if getattr(_orig, "_tizada", False):
        return

    def _init(self, *args, **kw):
        kw["creationflags"] = kw.get("creationflags", 0) | 0x08000000     # CREATE_NO_WINDOW
        _orig(self, *args, **kw)

    _init._tizada = True
    subprocess.Popen.__init__ = _init


def levantar_servidor(puerto):
    """Importa el servidor (lo pesado: unos segundos) y lo deja atendiendo en un hilo."""
    import threading
    os.environ["PORT"] = str(puerto)
    _sin_ventanas_de_consola()
    if not congelado():
        sys.path.insert(0, carpeta_programa())
    import registro
    registro.usar_carpeta(os.environ["TIZADA_LOGS"])
    import servidor

    def _correr():
        try:
            servidor.arrancar()
        except BaseException as e:           # noqa: BLE001 — se registra y la ventana lo muestra
            _log(f"el servidor se detuvo: {type(e).__name__}: {e}")

    threading.Thread(target=_correr, daemon=True, name="servidor").start()


# ══ PANTALLAS PROPIAS (antes de que el sistema esté) ════════════════════════════════════════
_CSS = """
*{box-sizing:border-box}html,body{margin:0;height:100%;background:#07090f;color:#e8ecf3;
font-family:'Segoe UI',system-ui,sans-serif}
.c{height:100%;display:flex;align-items:center;justify-content:center;padding:24px}
.t{width:min(520px,100%);background:#10131c;border:1px solid #232838;border-radius:18px;padding:30px 32px;
box-shadow:0 20px 60px rgba(0,0,0,.5)}
h1{margin:0 0 6px;font-size:22px}h1 b{color:#00f3ff}p{color:#9aa3b5;font-size:14px;line-height:1.55;margin:8px 0}
.g{width:26px;height:26px;border-radius:50%;border:3px solid #2a3042;border-top-color:#00f3ff;
animation:s .9s linear infinite;display:inline-block;vertical-align:middle;margin-right:12px}
@keyframes s{to{transform:rotate(360deg)}}
label{display:block;font-size:12px;color:#9aa3b5;margin:14px 0 5px;font-weight:600}
input{width:100%;padding:11px 12px;border-radius:10px;border:1px solid #2a3042;background:#0b0e16;color:#fff;font-size:14px}
input:focus{outline:none;border-color:#00f3ff}
button{margin-top:20px;padding:11px 20px;border-radius:10px;border:0;background:#00f3ff;color:#06121a;
font-weight:800;font-size:14px;cursor:pointer}button.s{background:transparent;color:#9aa3b5;border:1px solid #2a3042;margin-left:8px}
.e{color:#ff6b81;font-size:13px;min-height:18px;margin-top:10px}.d{font-size:12px;color:#6b7386;word-break:break-word}
"""


def _pagina(cuerpo):
    return f"<!doctype html><html lang='es'><head><meta charset='utf-8'><style>{_CSS}</style></head><body>" \
           f"<div class='c'><div class='t'>{cuerpo}</div></div></body></html>"


def pagina_cargando(texto="Abriendo el sistema…"):
    return _pagina(f"<h1><span class='g'></span><b>TIZADA PRO</b></h1><p id='m'>{texto}</p>")


def pagina_sin_sql(detalle):
    import html
    return _pagina(
        "<h1>Falta <b>SQL Server</b></h1>"
        "<p>TIZADA PRO guarda los moldes, las piezas y los usuarios en una base de datos SQL Server, "
        "y en esta PC no encontré ninguno funcionando.</p>"
        "<p><b>Qué hacer:</b> instalá <b>SQL Server Express</b> (es gratis): en el instalador elegí "
        "«Básica» y aceptá todo lo que propone. Cuando termine, tocá «Reintentar».</p>"
        "<button onclick=\"pywebview.api.abrir('https://www.microsoft.com/es-es/sql-server/sql-server-downloads')\">"
        "Bajar SQL Server Express</button>"
        "<button class='s' onclick='pywebview.api.reintentar()'>Reintentar</button>"
        f"<p class='d'>Detalle: {html.escape(detalle or '')}</p>")


def pagina_error(titulo, detalle):
    import html
    return _pagina(
        f"<h1>{html.escape(titulo)}</h1>"
        f"<p class='d'>{html.escape(detalle or '')}</p>"
        f"<p>El detalle completo está en <b>{html.escape(os.path.join(carpeta_datos(), 'logs'))}</b>.</p>"
        "<button onclick='pywebview.api.reintentar()'>Reintentar</button>")


def pagina_primer_usuario():
    return _pagina(
        "<h1>Bienvenido a <b>TIZADA PRO</b></h1>"
        "<p>Es la primera vez que se abre en esta PC. Creá el usuario <b>administrador</b>: con él "
        "vas a entrar y, después, podés crear los usuarios de los demás desde Configuración.</p>"
        "<label>Usuario</label><input id='u' value='admin' autocomplete='off'>"
        "<label>Nombre</label><input id='n' placeholder='Tu nombre'>"
        "<label>Contraseña</label><input id='p1' type='password'>"
        "<label>Repetí la contraseña</label><input id='p2' type='password'>"
        "<div class='e' id='e'></div>"
        "<button id='b' onclick='crear()'>Crear y entrar</button>"
        "<script>"
        "async function crear(){const u=document.getElementById('u').value.trim(),n=document.getElementById('n').value.trim(),"
        "a=document.getElementById('p1').value,b=document.getElementById('p2').value,e=document.getElementById('e');"
        "if(!u){e.textContent='Falta el usuario.';return}if(a.length<6){e.textContent='La contraseña tiene que tener 6 caracteres o más.';return}"
        "if(a!==b){e.textContent='Las dos contraseñas no coinciden.';return}"
        "document.getElementById('b').disabled=true;e.textContent='';"
        "const r=await pywebview.api.crear_admin(u,n,a);if(r!=='ok'){e.textContent=r;document.getElementById('b').disabled=false}}"
        "document.addEventListener('keydown',ev=>{if(ev.key==='Enter')crear()});"
        "</script>")


# ══ LA VENTANA ══════════════════════════════════════════════════════════════════════════════
class Api:
    """Lo que las pantallas propias le pueden pedir a Python (`pywebview.api.*`)."""

    # `_ventana` con guion bajo: pywebview expone al JS todo atributo público del objeto, y
    # recorrer la ventana entera para eso cuelga el arranque.
    def __init__(self):
        self._ventana = None

    def abrir(self, url):
        if str(url).startswith("https://"):
            os.startfile(url)                 # noqa: S606 — sólo enlaces fijos de estas pantallas

    def reintentar(self):
        import threading
        threading.Thread(target=arranque, args=(self,), daemon=True).start()

    def crear_admin(self, usuario, nombre, clave):
        try:
            crear_admin(str(usuario).strip(), str(nombre).strip(), str(clave))
        except Exception as e:
            return f"No se pudo crear el usuario: {e}"
        import threading
        threading.Thread(target=_mostrar_sistema, args=(self,), daemon=True).start()
        return "ok"


_ESTADO = {"puerto": None, "servidor_arriba": False}


def _mostrar_sistema(api):
    """Levanta el servidor (una sola vez) y, cuando contesta, carga el sistema en la ventana."""
    import time
    v = api._ventana
    if not _ESTADO["servidor_arriba"]:
        v.load_html(pagina_cargando("Preparando el motor de dibujo…"))
        _ESTADO["puerto"] = elegir_puerto()
        levantar_servidor(_ESTADO["puerto"])
        _ESTADO["servidor_arriba"] = True
    t0 = time.time()
    while not _responde(_ESTADO["puerto"]):
        if time.time() - t0 > 180:
            v.load_html(pagina_error("El sistema no arrancó",
                                     "El servidor interno no contestó en 3 minutos."))
            return
        time.sleep(0.4)
    _log(f"sistema listo en el puerto {_ESTADO['puerto']} ({time.time() - t0:.1f} s)")
    v.load_url(f"http://127.0.0.1:{_ESTADO['puerto']}/")
    if os.environ.get("TIZADA_ESCRITORIO_DIAG") == "1":
        _diagnostico(v)


def _diagnostico(v):
    """Para las pruebas: qué puede hacer la página dentro de la ventana (queda en el registro)."""
    import time
    time.sleep(6)
    try:
        r = v.evaluate_js(
            "JSON.stringify({guardarComo: typeof window.showSaveFilePicker, carpeta: typeof window.showDirectoryPicker,"
            " seguro: window.isSecureContext, ls: (()=>{try{localStorage.setItem('_d','1');return localStorage.getItem('_d')==='1'}catch(e){return false}})(),"
            " url: location.href, titulo: document.title})")
        _log(f"diagnóstico de la ventana: {r}")
    except Exception as e:
        _log(f"diagnóstico de la ventana falló: {e}")


def arranque(api):
    """Todo lo que pasa entre abrir la ventana y mostrar el sistema (corre en un hilo)."""
    v = api._ventana
    try:
        if _ESTADO["servidor_arriba"]:
            _mostrar_sistema(api)
            return
        v.load_html(pagina_cargando("Buscando la base de datos…"))
        srv, detalle = buscar_sql()
        if not srv:
            _log(f"sin SQL Server: {detalle}")
            v.load_html(pagina_sin_sql(detalle))
            return
        _log(f"SQL Server: {srv} · base {os.environ.get('TIZADA_DB_NAME')}")
        v.load_html(pagina_cargando("Preparando la base de datos…"))
        hay_usuarios = preparar_base(srv)
        if not hay_usuarios:
            v.load_html(pagina_primer_usuario())
            return
        _mostrar_sistema(api)
    except Exception as e:
        import traceback
        _log("error al arrancar:\n" + traceback.format_exc())
        v.load_html(pagina_error("No se pudo abrir el sistema", f"{type(e).__name__}: {e}"))


def main():
    if ya_abierta():
        return
    preparar_entorno()
    _log(f"abriendo {NOMBRE} · programa {carpeta_programa()} · datos {carpeta_datos()}")
    import webview
    webview.settings["ALLOW_DOWNLOADS"] = True                   # el «Descargar» de siempre
    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
    api = Api()
    api._ventana = webview.create_window(
        NOMBRE, html=pagina_cargando(), js_api=api, maximized=True,
        width=1440, height=900, min_size=(1024, 640), background_color="#07090f", text_select=True)
    api._ventana.events.closed += lambda: os._exit(0)            # el Job de Windows se lleva el resto
    # `private_mode=False` + `storage_path`: sin esto la ventana olvida TODO al cerrarse (el paso
    # del pedido, los nombres de las mesas, la sesión).
    webview.start(arranque, (api,), gui="edgechromium", private_mode=False,
                  storage_path=os.path.join(carpeta_datos(), "ventana"))
    os._exit(0)


if __name__ == "__main__":
    multiprocessing.freeze_support()          # los procesos de dibujo se desvían acá
    main()
