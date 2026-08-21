"""
USER · Motor de Sublimación — servidor web local.
Correr:  python servidor.py   y abrir  http://localhost:8000
"""
import os, re, sys, json, time, threading, uuid, traceback
from collections import OrderedDict
from flask import Flask, request, jsonify, send_from_directory, send_file, session, has_request_context
from werkzeug.exceptions import HTTPException

import motor_pedido as MP
import piezas_molde as PM
import db

AQUI = os.path.dirname(os.path.abspath(__file__))
# Las carpetas de datos se pueden redirigir por variable de entorno. Sirve para
# correr una instancia de PRUEBA contra una copia aislada (sandbox) sin tocar
# jamás los datos reales del usuario. En uso normal quedan en su lugar de siempre.
ENTRADA = os.environ.get("TIZADA_ENTRADA") or os.path.join(AQUI, "entrada")
FUENTES = os.environ.get("TIZADA_FUENTES") or os.path.join(AQUI, "catalogo_fuentes")
TRABAJOS = os.environ.get("TIZADA_TRABAJOS") or os.path.join(AQUI, "trabajos")
DATOS = os.environ.get("TIZADA_DATOS") or os.path.join(AQUI, "datos")
for d in (ENTRADA, FUENTES, TRABAJOS, DATOS):
    os.makedirs(d, exist_ok=True)

app = Flask(__name__, static_folder="frontend/dist", static_url_path="")

# ── MODO: taller (la máquina del usuario, como siempre) o PUBLICADO (el servidor de
#    internet). Ver `PLAN_PUBLICACION.md`. El default es "taller": nada cambia para quien
#    corre `py servidor.py` como hasta hoy. ────────────────────────────────────────────
MODO = (os.environ.get("TIZADA_MODO") or "taller").strip().lower()
PUBLICADO = MODO == "publicado"
ARRANQUE = time.time()
_PUERTO = [int(os.environ.get("PORT") or 8050)]   # lo usa el actualizador para volver a chequear


def _version():
    """Versión del programa: el archivo VERSION + el commit corto si el repo está a mano.
    Es lo que compara el circuito de actualización (taller vs publicado)."""
    if getattr(_version, "_v", None):
        return _version._v
    v = "0.0.0"
    try:
        with open(os.path.join(AQUI, "VERSION"), encoding="utf-8") as fh:
            v = (fh.read().strip() or v)
    except OSError:
        pass
    commit = ""
    try:
        import subprocess
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=AQUI,
                                capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        pass
    _version._v = {"version": v, "commit": commit}
    return _version._v


# ── SESIÓN + API de usuarios/roles/permisos (base MSSQL, ver PLAN_MSSQL.md) ──
# La clave de sesión va por ENV. En TALLER, si falta, se genera una al azar: cada arranque
# invalida las sesiones (molesto pero seguro) en vez de usar una clave fija y conocida, que
# permitiría falsificar la cookie. En PUBLICADO eso NO sirve — cada reinicio (y toda
# actualización lo implica) desloguearía a todos → ahí `TIZADA_SECRET` es OBLIGATORIO.
_secret = os.environ.get("TIZADA_SECRET")
if PUBLICADO and not _secret:
    raise SystemExit(
        "\n[ERROR] Falta TIZADA_SECRET y el modo es 'publicado'.\n"
        "        Sin una clave fija, cada reinicio del servidor cierra la sesión de todos.\n"
        "        Generá una y dejala en la configuración del servicio, por ejemplo:\n"
        "        py -c \"import secrets;print(secrets.token_hex(32))\"\n")
if not _secret:
    # TALLER: una clave al azar por arranque dejaba al usuario DESLOGUEADO cada vez que se
    # reinicia el servidor (401 en medio del trabajo, sin entender por qué). Se guarda una en
    # `datos/` — que no se publica ni va al repo — y así reiniciar no molesta a nadie. Es la misma
    # idea de siempre: la clave nunca es fija en el código, sólo que ahora sobrevive al reinicio.
    _ruta_secret = os.path.join(DATOS, ".secret")
    try:
        with open(_ruta_secret, encoding="utf-8") as _f:
            _secret = (_f.read() or "").strip() or None
    except OSError:
        _secret = None
    if not _secret:
        _secret = __import__("secrets").token_hex(32)
        try:
            os.makedirs(DATOS, exist_ok=True)
            with open(_ruta_secret, "w", encoding="utf-8") as _f:
                _f.write(_secret)
        except OSError:
            pass          # sin poder guardarla se sigue con la de esta corrida (como antes)
app.secret_key = _secret
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
# HTTPS: la cookie de sesión sólo viaja por conexión segura. Se prende solo en publicado
# (en el taller es http://localhost y con SECURE el navegador NO guardaría la sesión).
# `TIZADA_HTTPS=0` lo apaga para probar el modo publicado sin certificado todavía.
if PUBLICADO and os.environ.get("TIZADA_HTTPS", "1") != "0":
    app.config.update(SESSION_COOKIE_SECURE=True)
# Detrás de un proxy inverso (el que termina el HTTPS) Flask ve http:// y la IP del proxy;
# ProxyFix le hace leer los X-Forwarded-* para que los redirects y la IP real sean correctos.
# ⚠️ SÓLO si hay un proxy delante: con HTTPS PROPIO (`TIZADA_TLS_CERT`, el caso «se entra por la
# IP») los `X-Forwarded-*` los manda el cliente y son mentira — confiar en ellos deja falsear la
# IP de origen y el esquema.
if PUBLICADO and not os.environ.get("TIZADA_TLS_CERT"):
    try:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    except Exception as _e:
        print(f"[publicado] ProxyFix no disponible: {_e}")
_USUARIOS_ON = False      # ¿está registrado el sistema de usuarios? (si no, no se puede exigir sesión)
try:
    from api_usuarios import bp as _bp_usuarios
    app.register_blueprint(_bp_usuarios)
    _USUARIOS_ON = True
except Exception as _e:   # sin base, el resto del sistema tiene que seguir andando
    print(f"[usuarios] API deshabilitada (¿base MSSQL sin levantar?): {_e}")
trabajos = {}

# ── Perfiles ICC (color management real) ─────────────────────────────────────
# Se leen los .icc/.icm REALES instalados en el sistema (Adobe + Windows). Los
# nombres NO se hardcodean: salen del tag 'desc' de cada perfil vía Pillow.
PERFILES_DIRS = [d for d in ([os.environ.get("TIZADA_PERFILES")] + [
    r"C:\Program Files (x86)\Common Files\Adobe\Color\Profiles\Recommended",
    r"C:\Program Files\Common Files\Adobe\Color\Profiles\Recommended",
    r"C:\Program Files (x86)\Common Files\Adobe\Color\Profiles",
    r"C:\Program Files\Common Files\Adobe\Color\Profiles",
    r"C:\Windows\System32\spool\drivers\color",
]) if d and os.path.isdir(d)]
PERFIL_DEFAULT_CMYK = "USWebCoatedSWOP.icc"   # U.S. Web Coated (SWOP) v2
PERFIL_DEFAULT_RGB = "sRGB Color Space Profile.icm"
_perfiles_cache = None


def _colores_perfil(prof, espacio):
    """Convierte los primarios (C,M,Y,R,G,B) a sRGB A TRAVÉS del perfil → swatch de
    colores REALES que produce ese perfil (sirve de referencia visual). Devuelve hex[]."""
    try:
        from PIL import Image, ImageCms
        srgb = ImageCms.createProfile("sRGB")
        if espacio == "CMYK":
            pts = [(255, 0, 0, 0), (0, 255, 0, 0), (0, 0, 255, 0), (0, 255, 255, 0), (255, 0, 255, 0), (255, 255, 0, 0)]
            im = Image.new("CMYK", (len(pts), 1)); im.putdata(pts)
            tr = ImageCms.buildTransform(prof, srgb, "CMYK", "RGB", renderingIntent=1)
        elif espacio == "RGB":
            pts = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255), (255, 255, 255)]
            im = Image.new("RGB", (len(pts), 1)); im.putdata(pts)
            tr = ImageCms.buildTransform(prof, srgb, "RGB", "RGB", renderingIntent=1)
        else:
            return []
        out = ImageCms.applyTransform(im, tr)
        return ["#%02x%02x%02x" % out.getpixel((i, 0))[:3] for i in range(len(pts))]
    except Exception:
        return []


# ── CMYK ↔ RGB por el PERFIL ICC configurado (para que la pantalla muestre el MISMO color
#    que Illustrator). La fórmula ingenua R=255(1-C)(1-K) da un verde fosforescente donde
#    Illustrator muestra un verde apagado: no es redondeo, es que esa fórmula ignora el perfil.
#    Intent PERCEPTUAL (0) — es el que reproduce EXACTO lo que muestra Illustrator (verificado:
#    CMYK 95/0/91/15 → #009550, idéntico al panel Color de Illustrator; con relativo daba #00985a).
_cms_cache = {}


def _cms_tr(sentido):
    """Transformada ICC cacheada entre el perfil CMYK configurado y sRGB.
    `sentido` = "cmyk2rgb" | "rgb2cmyk". None si no hay perfil/Pillow."""
    arch = (_perfil_default_cfg().get("cmyk") or PERFIL_DEFAULT_CMYK)
    key = (sentido, arch)
    if key in _cms_cache:
        return _cms_cache[key]
    tr = None
    try:
        from PIL import ImageCms
        p = _perfil_por_archivo(arch)
        if p:
            prof = ImageCms.ImageCmsProfile(p["ruta"])
            srgb = ImageCms.createProfile("sRGB")
            if sentido == "cmyk2rgb":
                tr = ImageCms.buildTransform(prof, srgb, "CMYK", "RGB", renderingIntent=0)
            else:
                tr = ImageCms.buildTransform(srgb, prof, "RGB", "CMYK", renderingIntent=0)
    except Exception:
        tr = None
    _cms_cache[key] = tr
    return tr


@app.post("/api/color/convertir")
def color_convertir():
    """CMYK ↔ RGB a través del perfil ICC configurado (el mismo con el que se ve en Illustrator).
    Body: {cmyk:[[c,m,y,k],…]} (canales 0..1) → {rgb:[[r,g,b],…], hex:[…]}
       o  {rgb:[[r,g,b],…]}   (0..255)       → {cmyk:[[c,m,y,k],…]} (0..1).
    Si no hay perfil disponible cae a la fórmula simple (mejor eso que romper la pantalla)."""
    from PIL import Image, ImageCms
    cuerpo = request.get_json(force=True) or {}
    def _f(v, lo, hi):
        try: return max(lo, min(hi, float(v)))
        except Exception: return lo
    if cuerpo.get("cmyk") is not None:
        ent = [[_f(x, 0, 1) for x in (c or [])][:4] for c in (cuerpo.get("cmyk") or [])]
        ent = [(c + [0, 0, 0, 0])[:4] for c in ent]
        tr = _cms_tr("cmyk2rgb")
        if not ent:
            return jsonify({"rgb": [], "hex": []})
        if tr is None:
            rgb = [[round(255*(1-c[0])*(1-c[3])), round(255*(1-c[1])*(1-c[3])), round(255*(1-c[2])*(1-c[3]))] for c in ent]
        else:
            im = Image.new("CMYK", (len(ent), 1))
            im.putdata([tuple(round(x*255) for x in c) for c in ent])
            out = ImageCms.applyTransform(im, tr)
            rgb = [list(out.getpixel((i, 0))[:3]) for i in range(len(ent))]
        return jsonify({"rgb": rgb, "hex": ["#%02x%02x%02x" % tuple(v) for v in rgb]})
    ent = [[int(_f(x, 0, 255)) for x in (c or [])][:3] for c in (cuerpo.get("rgb") or [])]
    ent = [(c + [0, 0, 0])[:3] for c in ent]
    if not ent:
        return jsonify({"cmyk": []})
    tr = _cms_tr("rgb2cmyk")
    if tr is None:
        out = []
        for r, g, b in ent:
            r, g, b = r/255., g/255., b/255.
            k = 1 - max(r, g, b)
            out.append([0, 0, 0, 1] if k >= 0.9999 else
                       [round((1-r-k)/(1-k), 4), round((1-g-k)/(1-k), 4), round((1-b-k)/(1-k), 4), round(k, 4)])
        return jsonify({"cmyk": out})
    im = Image.new("RGB", (len(ent), 1)); im.putdata([tuple(c) for c in ent])
    o = ImageCms.applyTransform(im, tr)
    return jsonify({"cmyk": [[round(v/255., 4) for v in o.getpixel((i, 0))[:4]] for i in range(len(ent))]})


@app.get("/api/salud")
def salud():
    """Estado del servidor — LO MIRA EL ACTUALIZADOR para decidir si una publicación salió bien
    (si esto no responde `ok`, vuelve sola a la versión anterior). También sirve para saber al toque
    por qué una máquina nueva no genera igual: casi siempre es Ghostscript o los perfiles ICC.
    NO pide sesión a propósito: tiene que contestar aunque la base de usuarios esté caída, y no
    expone nada sensible (versión, si encuentra las herramientas, y cuánto hace que arrancó)."""
    chequeos, fallas = {}, []

    def _chk(nombre, fn, critico=True):
        try:
            ok, det = fn()
        except Exception as e:
            ok, det = False, str(e)[:200]
        chequeos[nombre] = {"ok": bool(ok), "detalle": det}
        if not ok and critico:
            fallas.append(nombre)

    def _gs():
        exe = _gs_exe()
        return bool(exe), (exe or "no encontrado (se instala Ghostscript y/o se apunta TIZADA_GS)")

    def _icc():
        ps = _listar_perfiles()
        cfg = _perfil_default_cfg()
        hay = _perfil_por_archivo(cfg.get("cmyk"))
        return bool(hay), (f"{len(ps)} perfiles · CMYK por defecto: "
                           f"{hay['nombre'] if hay else (str(cfg.get('cmyk')) + ' NO ESTÁ')}")

    def _escribible():
        # Nombre ÚNICO por chequeo. Con uno fijo, dos consultas simultáneas se pisan el archivo y
        # en Windows la segunda muere con [WinError 32] «lo está usando otro proceso»: el chequeo
        # es CRÍTICO, así que `/api/salud` contestaba **503** por una colisión consigo mismo (6 de
        # 12 consultas a la vez, medido). Y no es cosmético: el ACTUALIZADOR mira este endpoint
        # para decidir si una publicación salió bien — dos chequeos que coincidieran podían
        # hacerle revertir sola una versión que estaba perfecta.
        p = os.path.join(DATOS, f".salud.{os.getpid()}.{threading.get_ident()}.tmp")
        try:
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("ok")
        finally:
            try:
                os.remove(p)
            except OSError:
                pass
        return True, DATOS

    def _base():
        # La base es opcional mientras la migración a MSSQL esté en curso (PLAN_MSSQL.md):
        # si no hay driver, no es una falla — el sistema sigue andando con los archivos.
        if not db.driver_disponible():
            return True, "sin driver ODBC (el sistema corre con archivos)"
        return bool(db.valor("SELECT 1")), "responde"

    # Ghostscript NO es crítico: sólo se usa para unificar el modo de color cuando la hoja trae
    # contenido RGB. Con arte CMYK (lo normal) la tizada sale igual sin él.
    _chk("ghostscript", _gs, critico=False)
    _chk("perfiles_icc", _icc)
    _chk("datos_escribible", _escribible)
    _chk("base", _base, critico=False)
    _chk("frontend", lambda: (os.path.exists(os.path.join(AQUI, "frontend", "dist", "index.html")),
                              "frontend/dist"), critico=True)

    def _disco():
        """Espacio libre. El disco lleno rompe de formas que NO parecen de disco: publicar da
        «HTTP Error 500», las descargas se cortan (ERR_QUIC_PROTOCOL_ERROR) y generar la tizada
        tira **std::bad_alloc** — Windows no puede agrandar el archivo de paginación y las
        reservas de memoria fallan. Ya pasó: 0 bytes libres de 39,9 GB en el servidor, y los tres
        síntomas se veían como tres problemas distintos. Por eso ahora se mira acá."""
        import shutil as _sh
        libre = _sh.disk_usage(AQUI).free / 2**30
        if libre < 1.0:
            return False, f"quedan {libre:.2f} GB libres — CRÍTICO: publicar y generar van a fallar"
        if libre < 3.0:
            return False, f"quedan {libre:.1f} GB libres — poco; conviene liberar (LIBERAR-ESPACIO.bat)"
        return True, f"{libre:.1f} GB libres"
    _chk("disco", _disco, critico=False)

    def _dist_al_dia():
        """¿La pantalla que se está sirviendo tiene los cambios del código?

        El frontend se sirve desde `dist`, o sea COMPILADO: editar `frontend/src` no cambia nada
        hasta que se corre `npm run build`. Sin este aviso el síntoma es indistinguible de un bug —
        se toca el código, se prueba, «no anda», y se busca la falla donde no está. Ya pasó: la
        planilla tenía el arreglo del botón de un clic en `src` y el usuario seguía teniendo que
        hacer doble clic, porque el `dist` era viejo (se confirmó buscando el texto del botón
        adentro del bundle: no estaba). No es crítico: la app anda, pero anda con código viejo."""
        src = os.path.join(AQUI, "frontend", "src")
        dist = os.path.join(AQUI, "frontend", "dist")
        if not os.path.isdir(src) or not os.path.isdir(dist):
            return True, "sin fuentes (paquete publicado)"
        def _ultimo(d):
            t = 0
            for raiz, _, archivos in os.walk(d):
                for a in archivos:
                    try:
                        t = max(t, os.path.getmtime(os.path.join(raiz, a)))
                    except OSError:
                        pass
            return t
        t_src, t_dist = _ultimo(src), _ultimo(dist)
        if t_src <= t_dist:
            return True, "compilado al día"
        _min = int((t_src - t_dist) / 60)
        return False, (f"frontend/src es {_min} min más nuevo que dist → la pantalla está "
                       f"corriendo código VIEJO. Corré: cd frontend && npm run build")
    _chk("frontend_compilado", _dist_al_dia, critico=False)
    v = _version()
    return jsonify({
        "ok": not fallas, "fallas": fallas, "modo": MODO,
        "version": v["version"], "commit": v["commit"],
        "uptime_s": round(time.time() - ARRANQUE, 1),
        # cada proceso de render pesa ~200 MB → sirve para entender un servidor lento o sin memoria
        "procesos_render": procesos_render(),
        "chequeos": chequeos,
    }), (200 if not fallas else 503)


# ── ACTUALIZACIONES (sólo tienen sentido en el servidor publicado) ───────────
# El taller sube el paquete acá y el servidor se actualiza solo a la hora indicada.
# Ver `actualizaciones.py`, `actualizador.py` y PLAN_PUBLICACION.md §Etapa 2.
import actualizaciones as ACT


def _apagarme():
    """Apaga este proceso para que el ayudante pueda reemplazar los archivos. La tarea de Windows
    lo vuelve a levantar (y el ayudante también lo arranca explícitamente)."""
    def _fin():
        time.sleep(1)
        # CERRAR LOS PROCESOS DE RENDER ANTES DE SALIR. Heredan la salida del servidor —el .bat de
        # arranque la manda a un archivo de log— así que si quedan vivos MANTIENEN ESE ARCHIVO
        # ABIERTO. El siguiente arranque no puede escribirlo, el .bat muere al instante y la tarea
        # devuelve error sin dejar rastro: el servidor publicado queda caído y ni la versión nueva
        # ni la anterior levantan. Pasó de verdad (2026-07-27, ver changelog).
        try:
            global _RENDER_POOL
            if _RENDER_POOL is not None:
                for _p in list(getattr(_RENDER_POOL, "_processes", {}).values()):
                    try:
                        _p.terminate()
                    except Exception:
                        pass
                _RENDER_POOL.shutdown(wait=False)
                _RENDER_POOL = None
        except Exception:
            pass
        os._exit(0)
    _en_hilo(_fin)


# ── PUBLICAR (lado TALLER): arma el paquete y se lo manda al servidor publicado ──
def _pub_cfg():
    import empaquetar as _EMP
    return _EMP.config_publicacion()


# Cloudflare (que está delante del servidor publicado) RECHAZA con 403 al `User-Agent` por defecto
# de Python (`Python-urllib/3.x`): lo toma por un bot. Verificado: con cualquier otro agente da 200.
# Sin esto, publicar fallaba siempre con un "403 Forbidden" imposible de entender.
_UA_PUB = "TIZADAPRO-publicador/1.0"


@app.get("/api/publicacion/estado")
def publicacion_estado():
    """Para la pantalla de Publicación: qué versión hay acá, qué versión hay publicada y si hay
    algo pendiente allá. Si el servidor publicado no contesta, se dice y listo."""
    cfg = _pub_cfg()
    out = {"local": _version(), "url": cfg.get("url"), "remoto": None, "error": None}
    try:
        import urllib.request
        _rq = urllib.request.Request(cfg["url"].rstrip("/") + "/api/actualizacion/estado",
                                     headers={"User-Agent": _UA_PUB})
        with urllib.request.urlopen(_rq, timeout=20) as r:
            out["remoto"] = json.loads(r.read())
    except Exception as e:
        # 404 = el servidor publicado corre una versión VIEJA, sin el receptor de actualizaciones:
        # no es un error de red, es que todavía le falta la instalación que lo incluye. Se distingue
        # para poder decírselo al usuario con esas palabras y no con un "404" pelado.
        out["sin_receptor"] = "404" in str(e)
        out["error"] = str(e)[:200]
    return jsonify(out)


@app.post("/api/publicacion/publicar")
def publicacion_publicar():
    """Arma el paquete y lo SUBE. `cuando` = 0 (ya) o marca de tiempo. Es lo que hace el botón."""
    cuerpo = request.get_json(force=True) or {}
    cfg = _pub_cfg()
    if cuerpo.get("url"):
        cfg["url"] = cuerpo["url"]
        with open(os.path.join(AQUI, "datos", "publicacion.json"), "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, ensure_ascii=False, indent=1)
    # El NÚMERO DE VERSIÓN lo decide el usuario desde la pantalla (no se toca solo). Se escribe en
    # el archivo VERSION ANTES de empaquetar, así el paquete lo lleva. Se acepta sólo `1.2.3`.
    nueva_v = str(cuerpo.get("version") or "").strip()
    if nueva_v:
        if not re.fullmatch(r"\d+(\.\d+){0,3}", nueva_v):
            return jsonify({"error": "la versión tiene que ser números y puntos, por ej. 1.0.5"}), 400
        with open(os.path.join(AQUI, "VERSION"), "w", encoding="ascii") as fh:
            fh.write(nueva_v + "\n")
        _version._v = None                     # invalidar la caché para que tome el número nuevo
    try:
        import subprocess as _sp, hashlib as _hl, urllib.request as _ur
        # 1) armar el paquete de ACTUALIZACIÓN (sin datos: nunca pisa moldes ni pedidos)
        r = _sp.run([sys.executable, os.path.join(AQUI, "empaquetar.py")],
                    cwd=AQUI, capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            return jsonify({"error": "no se pudo armar el paquete: " + (r.stdout or r.stderr)[-400:]}), 500
        import glob as _g
        v = _version()["version"]
        zips = [z for z in _g.glob(os.path.join(AQUI, "dist", "*.zip")) if "COMPLETO" not in z]
        if not zips:
            return jsonify({"error": "no apareció el paquete"}), 500
        paq = max(zips, key=os.path.getmtime)
        datos = open(paq, "rb").read()
        # 2) subirlo
        req = _ur.Request(cfg["url"].rstrip("/") + "/api/actualizacion/subir", data=datos,
                          method="POST", headers={
                              "Content-Type": "application/zip",
                              "User-Agent": _UA_PUB,
                              "X-Token-Act": cfg["token"],
                              "X-Version": v,
                              "X-Sha256": _hl.sha256(datos).hexdigest(),
                              "X-Cuando": str(float(cuerpo.get("cuando") or 0) or time.time())})
        with _ur.urlopen(req, timeout=300) as resp:
            return jsonify({"ok": True, "paquete": os.path.basename(paq),
                            "mb": round(len(datos) / 2**20, 2), **json.loads(resp.read())})
    except Exception as e:
        return jsonify({"error": str(e)[:300]}), 502


@app.post("/api/publicacion/cancelar")
def publicacion_cancelar():
    cfg = _pub_cfg()
    try:
        import urllib.request as _ur
        req = _ur.Request(cfg["url"].rstrip("/") + "/api/actualizacion/cancelar", data=b"{}",
                          method="POST", headers={"X-Token-Act": cfg["token"],
                                                  "User-Agent": _UA_PUB,
                                                  "Content-Type": "application/json"})
        with _ur.urlopen(req, timeout=60) as r:
            return jsonify(json.loads(r.read()))
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 502


@app.get("/api/actualizacion/estado")
def actualizacion_estado():
    """Lo consulta la PANTALLA para mostrar la cuenta regresiva. Sin clave a propósito: no revela
    nada sensible (qué versión corre y cuánto falta para el corte) y lo necesita cualquiera que
    esté trabajando para enterarse de que el sistema se va a reiniciar."""
    return jsonify(ACT.estado(_version()["version"]))


@app.post("/api/actualizacion/subir")
def actualizacion_subir():
    """Recibe el paquete del taller. `X-Token-Act` (clave), `X-Version`, `X-Sha256` y `X-Cuando`
    (marca de tiempo; 0 = ya). El cuerpo es el .zip crudo."""
    if not ACT.token_ok(request.headers.get("X-Token-Act")):
        return jsonify({"error": "no autorizado"}), 401
    datos = request.get_data()
    if not datos:
        return jsonify({"error": "no llegó ningún archivo"}), 400
    try:
        cuando = float(request.headers.get("X-Cuando") or 0)
    except ValueError:
        cuando = 0
    ok, det = ACT.guardar(datos, request.headers.get("X-Version") or "",
                          request.headers.get("X-Sha256") or "", cuando or time.time())
    if not ok:
        return jsonify({"error": det}), 400
    return jsonify({"ok": True, "version": det, "cuando": cuando or time.time()})


@app.post("/api/actualizacion/aplicar")
def actualizacion_aplicar():
    """Aplica la pendiente YA (el botón «actualizar ahora»). Contesta ANTES de apagarse."""
    if not ACT.token_ok(request.headers.get("X-Token-Act")):
        return jsonify({"error": "no autorizado"}), 401
    ok, det = ACT.aplicar(_PUERTO[0], _version()["version"])
    if not ok:
        return jsonify({"error": det}), 409
    _apagarme()
    return jsonify({"ok": True, "version": det})


@app.post("/api/actualizacion/cancelar")
def actualizacion_cancelar():
    if not ACT.token_ok(request.headers.get("X-Token-Act")):
        return jsonify({"error": "no autorizado"}), 401
    ACT.cancelar()
    return jsonify({"ok": True})


def _listar_perfiles():
    """Lista los perfiles ICC reales del sistema con su NOMBRE real (tag desc),
    espacio (RGB/CMYK) y un swatch de colores reales. Cacheado, dedup por nombre.
    Devuelve [{archivo, nombre, espacio, ruta, colores}]."""
    global _perfiles_cache
    if _perfiles_cache is not None:
        return _perfiles_cache
    out, vistos_arch, vistos_nombre = [], set(), set()
    try:
        from PIL import ImageCms
    except Exception:
        _perfiles_cache = []
        return _perfiles_cache
    for d in PERFILES_DIRS:
        for fn in sorted(os.listdir(d)):
            if not fn.lower().endswith((".icc", ".icm")) or fn.lower() in vistos_arch:
                continue
            ruta = os.path.join(d, fn)
            try:
                p = ImageCms.ImageCmsProfile(ruta)
                nombre = (ImageCms.getProfileName(p) or fn).strip()
                espacio = (getattr(p.profile, "xcolor_space", None) or "").strip().upper() or "?"
            except Exception:
                continue
            vistos_arch.add(fn.lower())
            if nombre.lower() in vistos_nombre:   # mismo nombre repetido (ej. HDTV) → uno solo
                continue
            vistos_nombre.add(nombre.lower())
            out.append({"archivo": fn, "nombre": nombre, "espacio": espacio, "ruta": ruta,
                        "colores": _colores_perfil(p, espacio)})
    _perfiles_cache = out
    return out


def _perfil_por_archivo(archivo):
    return next((p for p in _listar_perfiles() if p["archivo"].lower() == str(archivo or "").lower()), None)


def _perfil_default_cfg(cat=None):
    cat = cat or _cargar_catalogo()
    cfg = cat.get("perfil_cfg") or {}
    return {"cmyk": cfg.get("cmyk") or PERFIL_DEFAULT_CMYK,
            "rgb": cfg.get("rgb") or PERFIL_DEFAULT_RGB}


def _detectar_perfil_incrustado(pdf_path):
    """Detecta el perfil ICC incrustado en un .ai/PDF. Devuelve {tiene, nombre, espacio}.
    Busca OutputIntent → ICCBased → XMP → y, si no hay perfil, el modelo de color del
    encabezado AI (CMYK/RGB) para saber qué predeterminado corresponde."""
    nombre, espacio = None, None
    import tempfile
    def _desc_de_icc(data):
        try:
            from PIL import ImageCms
            import io
            return ImageCms.getProfileName(ImageCms.ImageCmsProfile(io.BytesIO(data))).strip()
        except Exception:
            return None
    try:
        import pikepdf
        pdf = pikepdf.open(pdf_path)
        try:
            ois = pdf.Root.get("/OutputIntents")
            if ois:
                for oi in ois:
                    dop = oi.get("/DestOutputProfile")
                    if dop is not None:
                        n = _desc_de_icc(bytes(dop.read_bytes()))
                        if n:
                            nombre = n; break
                    info = oi.get("/Info") or oi.get("/OutputConditionIdentifier")
                    if info and not nombre:
                        nombre = str(info)
            if not nombre:
                # ICCBased en cualquier recurso
                vis = set()
                def walk(obj, d=0):
                    nonlocal nombre, espacio
                    if d > 8 or nombre:
                        return
                    try:
                        if isinstance(obj, pikepdf.Array) and len(obj) >= 2 and str(obj[0]) == "/ICCBased":
                            n = _desc_de_icc(bytes(obj[1].read_bytes()))
                            if n:
                                nombre = n
                            nn = obj[1].get("/N")
                            espacio = {1: "GRAY", 3: "RGB", 4: "CMYK"}.get(int(nn)) if nn is not None else espacio
                    except Exception:
                        pass
                    try:
                        for k in (obj.keys() if hasattr(obj, "keys") else []):
                            walk(obj[k], d + 1)
                    except Exception:
                        pass
                for pg in pdf.pages:
                    walk(pg.obj)
        finally:
            pdf.close()
    except Exception:
        pass
    # Modelo de color del encabezado AI (para elegir el predeterminado correcto)
    if espacio is None:
        try:
            raw = open(pdf_path, "rb").read(60000)
            m = re.search(rb"AI9_ColorModel:\s*(\d+)", raw)
            if m:
                espacio = {0: "GRAY", 1: "RGB", 2: "CMYK"}.get(int(m.group(1)), "CMYK")
        except Exception:
            pass
    return {"tiene": bool(nombre), "nombre": nombre, "espacio": espacio or "CMYK"}


def _perfil_info(pdf_path, cat=None):
    """Compara el perfil incrustado contra el predeterminado y arma el aviso."""
    cat = cat or _cargar_catalogo()
    det = _detectar_perfil_incrustado(pdf_path)
    espacio = det["espacio"]
    defs = _perfil_default_cfg(cat)
    def_file = defs["rgb"] if espacio == "RGB" else defs["cmyk"]
    def_prof = _perfil_por_archivo(def_file)
    def_nombre = (def_prof or {}).get("nombre") or def_file
    if not det["tiene"]:
        return {"estado": "sin_perfil", "espacio": espacio, "incrustado": None,
                "predeterminado": def_nombre,
                "mensaje": f"Tu diseño viene SIN perfil de color. Se le asignará «{def_nombre}» ({espacio})."}
    if det["nombre"] == def_nombre:
        return {"estado": "ok", "espacio": espacio, "incrustado": det["nombre"],
                "predeterminado": def_nombre,
                "mensaje": f"Perfil correcto: «{det['nombre']}»."}
    return {"estado": "distinto", "espacio": espacio, "incrustado": det["nombre"],
            "predeterminado": def_nombre,
            "mensaje": f"El perfil del diseño es «{det['nombre']}», distinto del predeterminado. Se recomienda «{def_nombre}»."}


def _icc_para_salida(arts, cat=None, forzado=None):
    """Decide QUÉ perfil ICC embeber en la tizada. Si `forzado` (archivo) viene
    (el usuario unificó perfiles distintos), usa ese. Si no: el que vino incrustado
    en el arte, o el predeterminado del sistema si no traía. Devuelve
    (icc_bytes, nombre, n_componentes) o (None, None, None)."""
    cat = cat or _cargar_catalogo()
    # 1) El perfil ELEGIDO al unificar (paso 2) MANDA, sea RGB o CMYK. Se respeta su
    #    espacio: si elegís un perfil RGB, la salida sale en RGB (no se fuerza CMYK).
    if forzado:
        prof = _perfil_por_archivo(forzado)
        if prof:
            try:
                return open(prof["ruta"], "rb").read(), prof["nombre"], (4 if prof["espacio"] == "CMYK" else 3)
            except Exception:
                pass
    # 2) El perfil INCRUSTADO en el arte (respeta su espacio).
    espacio = None
    for a in (arts or []):
        if not a or not os.path.exists(a):
            continue
        det = _detectar_perfil_incrustado(a)
        espacio = det.get("espacio") or espacio
        if det.get("tiene") and det.get("nombre"):
            prof = next((p for p in _listar_perfiles() if p["nombre"] == det["nombre"]), None)
            if prof:
                try:
                    return open(prof["ruta"], "rb").read(), prof["nombre"], (4 if prof["espacio"] == "CMYK" else 3)
                except Exception:
                    pass
    # 3) Predeterminado del sistema, SEGÚN el espacio detectado (CMYK si no se sabe).
    defs = _perfil_default_cfg(cat)
    def_file = defs["rgb"] if espacio == "RGB" else defs["cmyk"]
    prof = _perfil_por_archivo(def_file)
    if prof:
        try:
            return open(prof["ruta"], "rb").read(), prof["nombre"], (4 if prof["espacio"] == "CMYK" else 3)
        except Exception:
            pass
    return None, None, None


def _gs_exe():
    """Ubica el ejecutable de Ghostscript (gswin64c). Cacheado en la variable."""
    if getattr(_gs_exe, "_path", "x") != "x":
        return _gs_exe._path
    cands = [os.environ.get("TIZADA_GS")]
    for base in (r"C:\Program Files\gs", r"C:\Program Files (x86)\gs"):
        if os.path.isdir(base):
            for v in sorted(os.listdir(base), reverse=True):
                for exe in ("gswin64c.exe", "gswin32c.exe", "gs.exe"):
                    cands.append(os.path.join(base, v, "bin", exe))
    _gs_exe._path = next((c for c in cands if c and os.path.exists(c)), None)
    return _gs_exe._path


def _pdf_tiene_rgb(pdf_path):
    """True si el PDF tiene algún contenido RGB (operadores rg/RG, DeviceRGB,
    CalRGB/Lab o ICCBased N=3), RECORRIENDO los Form XObjects (el motor pone cada
    pieza en un XObject, ahí viven los colores). Sirve para decidir si hace falta
    convertir a CMYK: si la tizada es TODA CMYK, NO se convierte (los valores CMYK
    quedan EXACTOS, el perfil solo se ASIGNA/tagea); solo se convierte si hay RGB."""
    try:
        import pikepdf
        from pikepdf import parse_content_stream
        pdf = pikepdf.open(pdf_path)
    except Exception:
        return True   # ante la duda, convertir (no romper el flujo viejo)

    def _cs_es_rgb(v):
        try:
            if isinstance(v, pikepdf.Array):
                base = str(v[0])
                if base in ("/CalRGB", "/Lab", "/DeviceRGB"):
                    return True
                if base == "/ICCBased" and int(v[1].get("/N", 0)) == 3:
                    return True
                if base in ("/Indexed", "/ICCBased", "/Separation", "/DeviceN") and len(v) > 1:
                    return _cs_es_rgb(v[1])   # base de Indexed / alternate
            elif str(v) in ("/DeviceRGB", "/CalRGB"):
                return True
        except Exception:
            pass
        return False

    def _rgb_en(obj, seen):
        # imagen con colorspace RGB directo (no está en /Resources)
        try:
            if str(obj.get("/Subtype", "")) == "/Image" and _cs_es_rgb(obj.get("/ColorSpace")):
                return True
        except Exception:
            pass
        try:
            cs = obj.get("/Resources", {}).get("/ColorSpace", {}) or {}
        except Exception:
            cs = {}
        for v in (cs.values() if cs else []):
            if _cs_es_rgb(v):
                return True
        try:
            for inst in parse_content_stream(obj):
                if str(inst.operator) in ("rg", "RG"):
                    return True
        except Exception:
            pass
        try:
            sub = obj.get("/Resources", {}).get("/XObject", {}) or {}
            for v in (sub.values() if sub else []):
                oid = id(v)
                if oid in seen:
                    continue
                seen.add(oid)
                if _rgb_en(v, seen):
                    return True
        except Exception:
            pass
        return False

    try:
        seen = set()
        return any(_rgb_en(pg, seen) for pg in pdf.pages)
    finally:
        pdf.close()


def _pdf_tiene_cmyk(pdf_path):
    """True si el PDF tiene algún contenido CMYK (k/K, DeviceCMYK, ICCBased N=4 o
    Separation/DeviceN), recorriendo Form XObjects e imágenes. Espejo de
    `_pdf_tiene_rgb`: sirve cuando el modo objetivo es RGB para decidir si hace falta
    convertir (solo si hay CMYK que no calza)."""
    try:
        import pikepdf
        from pikepdf import parse_content_stream
        pdf = pikepdf.open(pdf_path)
    except Exception:
        return False

    def _cs_es_cmyk(v):
        try:
            if isinstance(v, pikepdf.Array):
                base = str(v[0])
                if base in ("/Separation", "/DeviceN"):
                    return True
                if base == "/ICCBased" and int(v[1].get("/N", 0)) == 4:
                    return True
                if base in ("/Indexed",) and len(v) > 1:
                    return _cs_es_cmyk(v[1])
            elif str(v) == "/DeviceCMYK":
                return True
        except Exception:
            pass
        return False

    def _cmyk_en(obj, seen):
        try:
            if str(obj.get("/Subtype", "")) == "/Image" and _cs_es_cmyk(obj.get("/ColorSpace")):
                return True
        except Exception:
            pass
        try:
            cs = obj.get("/Resources", {}).get("/ColorSpace", {}) or {}
        except Exception:
            cs = {}
        for v in (cs.values() if cs else []):
            if _cs_es_cmyk(v):
                return True
        try:
            for inst in parse_content_stream(obj):
                if str(inst.operator) in ("k", "K"):
                    return True
        except Exception:
            pass
        try:
            sub = obj.get("/Resources", {}).get("/XObject", {}) or {}
            for v in (sub.values() if sub else []):
                oid = id(v)
                if oid in seen:
                    continue
                seen.add(oid)
                if _cmyk_en(v, seen):
                    return True
        except Exception:
            pass
        return False

    try:
        seen = set()
        return any(_cmyk_en(pg, seen) for pg in pdf.pages)
    finally:
        pdf.close()


def _unificar_modo_gs(pdf_path, espacio):
    """Convierte el PDF a UN SOLO modo de color (CMYK o RGB) con Ghostscript, así
    Illustrator/Acrobat no pide elegir modo. CMYK device pasa derecho; el RGB suelto
    (texto, contornos) se convierte. Devuelve True si convirtió."""
    gs = _gs_exe()
    if not gs or not os.path.exists(pdf_path):
        return False
    import subprocess
    rgb = (espacio == "RGB")
    out = pdf_path + ".cmyk.pdf"
    cmd = [gs, "-dBATCH", "-dNOPAUSE", "-dSAFER", "-sDEVICE=pdfwrite",
           "-dColorConversionStrategy=/" + ("RGB" if rgb else "CMYK"),
           "-dProcessColorModel=/" + ("DeviceRGB" if rgb else "DeviceCMYK"),
           "-dPreserveSeparation=true", "-dPreserveDeviceN=true",
           "-dAutoRotatePages=/None", "-dPassThroughJPEGImages=true",
           "-dDownsampleColorImages=false", "-dDownsampleGrayImages=false",
           "-dDownsampleMonoImages=false",
           f"-sOutputFile={out}", pdf_path]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0:
            os.replace(out, pdf_path)
            return True
        print(f"  [!]  gs no convirtió {pdf_path}: rc={r.returncode} {r.stderr[-200:]}")
    except Exception as e:
        print(f"  [!]  gs error en {pdf_path}: {e}")
    try:
        if os.path.exists(out):
            os.remove(out)
    except OSError:
        pass
    return False


def _embeber_perfil_pdf(pdf_path, icc_bytes, nombre, n):
    """Incrusta el perfil ICC como OutputIntent (PDF/X) — TAGEA el destino de color
    SIN convertir ni modificar los valores de color."""
    if not (icc_bytes and os.path.exists(pdf_path)):
        return False
    try:
        import pikepdf
        with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
            icc = pdf.make_stream(icc_bytes)
            icc.N = n
            oi = pdf.make_indirect(pikepdf.Dictionary({
                "/Type": pikepdf.Name("/OutputIntent"),
                "/S": pikepdf.Name("/GTS_PDFX"),
                "/OutputConditionIdentifier": pikepdf.String(nombre or "Custom"),
                "/Info": pikepdf.String(nombre or "Custom"),
                "/DestOutputProfile": icc,
            }))
            pdf.Root.OutputIntents = pikepdf.Array([oi])
            pdf.save(pdf_path)
        return True
    except Exception as e:
        print(f"  [!]  no se pudo embeber el perfil en {pdf_path}: {e}")
        return False


def _catalogo_desde_json():
    """Sólo para la PRIMERA carga: lee el productos_catalogo.json histórico (con backup y
    preservación de corruptos) para sembrar la base UNA vez. Después la base es la fuente."""
    ruta = os.path.join(DATOS, "productos_catalogo.json")
    cat = None
    for intento in (ruta, ruta + ".bak"):
        if os.path.exists(intento):
            try:
                with open(intento, encoding="utf-8") as f:
                    datos = json.load(f)
                if datos and datos.get("productos"):
                    cat = datos
                    break
            except Exception:
                cat = None
    if cat is None and os.path.exists(ruta) and os.path.getsize(ruta) > 0:
        try:
            import shutil
            shutil.copy2(ruta, ruta + ".corrupto")
            print(f"\n  [!]  {ruta} no se pudo leer. Copia preservada en {ruta}.corrupto\n")
        except Exception:
            pass
    return cat


def _cargar_catalogo():
    # FUENTE DE VERDAD: la base (MSSQL). Ya NO se lee del JSON en cada request.
    cat = None
    try:
        cat = db.get_doc("catalogo")
        if cat is None:
            # Primera vez: sembrar la base con el JSON histórico (o el default) y no volver a
            # depender del archivo. Esto NO es "migrar los datos de piezas": es traer la config
            # base (reglas de planilla, presets de nesting, plantillas) para no arrancar en cero.
            cat = _catalogo_desde_json()
            if cat:
                db.set_doc("catalogo", cat)
                db.sync_productos(cat)
    except Exception as e:
        # Si la base no está, se cae al JSON para no dejar el sistema muerto (y se avisa).
        print(f"[catalogo] sin base, uso JSON: {e}")
        cat = _catalogo_desde_json()
    if not cat:
        cat = {"activo": "prod_default", "productos": [{"id": "prod_default", "nombre": "Molde 1", "creado": time.time()}]}
    
    # Ensure plantillas_planillas is present
    if "plantillas_planillas" not in cat:
        cat["plantillas_planillas"] = [
            {
                "id": "plan_default",
                "nombre": "Planilla Estándar",
                "columnas": [
                    {"id": "talle", "label": "Talle", "role": "talle"},
                    {"id": "nombre", "label": "Nombre", "role": "nombre"},
                    {"id": "numero", "label": "Número", "role": "numero"},
                    {"id": "manga", "label": "Manga", "role": "manga"}
                ]
            }
        ]
        _guardar_catalogo(cat)

    # Biblioteca de REGLAS de planilla (campos reutilizables). Cada regla define
    # cómo se carga en la planilla (texto/desplegable/toggle), sus opciones y qué
    # hace (comportamiento). Las columnas de las planillas eligen una regla.
    if "reglas_planilla" not in cat:
        cat["reglas_planilla"] = [
            {"id": "regla_variante", "nombre": "Variante (talle/color/…)", "tipo": "desplegable", "opciones": "", "comportamiento": "talle"},
            {"id": "regla_nombre", "nombre": "Nombre", "tipo": "texto", "opciones": "", "comportamiento": "nombre"},
            {"id": "regla_numero", "nombre": "Número", "tipo": "texto", "opciones": "", "comportamiento": "numero"},
            {"id": "regla_manga", "nombre": "Manga", "tipo": "toggle", "opciones": "Corta, Larga", "comportamiento": "manga", "clave": "manga"},
            {"id": "regla_texto", "nombre": "Texto libre", "tipo": "texto", "opciones": "", "comportamiento": "none"},
        ]
        _guardar_catalogo(cat)

    # Migración aditiva: las reglas "toggle de pieza" (comportamiento "manga") ahora
    # llevan palabra CLAVE. A las viejas sin clave les ponemos su nombre en minúsculas.
    _mig_clave = False
    for r in cat.get("reglas_planilla", []):
        if r.get("comportamiento") == "manga" and not r.get("clave"):
            r["clave"] = (r.get("nombre") or "manga").strip().lower()
            _mig_clave = True
    if _mig_clave:
        _guardar_catalogo(cat)

    # Presets de NESTING (reglas de acomodo): espaciado, margen y giro. Cada molde
    # elige cuál usar (productos[*].nesting_preset_id). El primero es el estándar.
    if "nesting_presets" not in cat:
        cat["nesting_presets"] = [
            {"id": "nesting_default", "nombre": "Estándar", "espaciado_mm": 5, "margen_mm": 10, "rotacion": "ninguna"},
        ]
        _guardar_catalogo(cat)

    # Catálogo de piezas organizado por GRUPOS (editable y persistido). El grupo
    # que ya existía (catálogo plano) pasa a llamarse "Prenda Superior".
    if "catalogo_grupos" not in cat:
        base = cat.get("catalogo_piezas") or ["Frente", "Espalda", "Manga", "Cuello", "Costadillo", "TC"]
        cat["catalogo_grupos"] = [{"nombre": "Prenda Superior", "piezas": list(base)}]
        _guardar_catalogo(cat)

    # ── MIGRACIÓN: las molderías de CONFIGURACIÓN son del SISTEMA, no de quien las cargó ───────
    # Regla del usuario (2026-07-29): lo que se hace en Configuración es del taller y lo ve todo
    # el mundo; sólo los «Mis artículos» (`propio`) tienen dueño. Antes se sellaba `creado_por` en
    # TODA alta, así que las molderías cargadas desde Configuración con sesión quedaron con dueño
    # personal. Acá se las libera: el dueño pasa a `alta_por` (trazabilidad, no propiedad) y
    # `creado_por` queda vacío.
    # Va en la CARGA del catálogo —y no en un script aparte— justamente para que el sistema ya
    # publicado se arregle solo al desplegar, sin entrar al servidor a correr nada. Es idempotente:
    # después de la primera vez no encuentra ninguna y no escribe.
    # ⚠️ CORRE UNA SOLA VEZ EN LA VIDA DEL CATÁLOGO, y queda marcado. No es «en cada actualización
    # se comparten los moldes»: es un arreglo de los datos que dejó el modelo viejo. La marca no es
    # decorativa — sin ella, esto sería una regla PERMANENTE («todo lo que tenga dueño y no sea
    # propio, liberalo»), y cualquier cambio futuro que sellara `creado_por` en un molde compartido
    # terminaría compartiendo moldes de nuevo en el próximo despliegue. Con la marca, no puede.
    if not cat.get("migracion_dueno_config"):
        _mig_dueno = [p for p in cat.get("productos", [])
                      if p.get("creado_por") and not p.get("propio")]
        for p in _mig_dueno:
            p.setdefault("alta_por", p.get("creado_por"))
            p["creado_por"] = None
        if _mig_dueno:
            print(f"[migración] {len(_mig_dueno)} moldería/s de Configuración pasan a ser del sistema "
                  f"(las ve todo el mundo): {', '.join((p.get('nombre') or p['id']) for p in _mig_dueno)}")
        cat["migracion_dueno_config"] = True      # se marca SIEMPRE, haya encontrado o no
        _guardar_catalogo(cat)

    # ── REPARACIÓN: «Mi artículo» SIN DUEÑO ───────────────────────────────────────────────────
    # Estado imposible (ver `crear_producto`): se comporta como del sistema para la privacidad y
    # como propio para TODOS en el pedido. Se arregla dejándolo coherente:
    #   · si se sabe quién lo dio de alta (`alta_por`) → se le devuelve a esa persona;
    #   · si no se sabe → pasa a ser del sistema, que es lo único que se puede afirmar de algo
    #     sin dueño. Se avisa en el log: es un cambio visible y el usuario tiene que enterarse.
    # Sólo con sistema de usuarios: sin él, `propio` sin dueño es lo NORMAL (no hay a quién sellar).
    if _USUARIOS_ON:
        _rotos = [p for p in cat.get("productos", []) if p.get("propio") and not p.get("creado_por")]
        for p in _rotos:
            if p.get("alta_por"):
                p["creado_por"] = p["alta_por"]
                print(f"[reparación] «{p.get('nombre')}» era un artículo sin dueño → se le devuelve "
                      f"al usuario {p['alta_por']}")
            else:
                p["propio"] = False
                print(f"[reparación] «{p.get('nombre')}» estaba marcado como artículo personal pero "
                      f"SIN dueño y sin saber quién lo cargó → pasa a ser del sistema (lo ven todos)")
        if _rotos:
            _guardar_catalogo(cat)

    # Map existing products to the default template and set default mapeo_columnas if missing
    modificado = False
    for p in cat.get("productos", []):
        # El concepto "producto" deja de existir de cara al usuario: cada uno es
        # un molde. Migramos el nombre por defecto histórico.
        if p.get("nombre") in ("Producto por Defecto", "Producto por defecto"):
            p["nombre"] = "Molde 1"
            modificado = True
        if "planilla_template_id" not in p:
            p["planilla_template_id"] = "plan_default"
            modificado = True
        if "mapeo_columnas" not in p:
            p["mapeo_columnas"] = {
                "talle": "talle",
                "nombre": "nombre",
                "numero": "numero",
                "manga": "manga",
                "manga_corta_val": "corta",
                "manga_larga_val": "larga"
            }
            modificado = True
    if modificado:
        _guardar_catalogo(cat)
    return cat


_lock_catalogo = threading.Lock()


def _guardar_catalogo(cat):
    """Guarda el catálogo en la BASE (fuente de verdad) + sincroniza la identidad de los
    productos a la tabla `producto`. Además deja un espejo en JSON como respaldo (no se lee de
    ahí): si algún día se apaga la base, el archivo sigue teniendo el último estado bueno."""
    try:
        try:
            db.set_doc("catalogo", cat)
            db.proyectar_catalogo(cat)   # identidad + piezas/variables/talles/diseños NORMALIZADOS (por id)
        except Exception as e:
            print(f"[catalogo] no se pudo guardar en la base: {e}")
            raise
        _guardar_catalogo_json_espejo(cat)
    finally:
        # ⚠️ Acá NO se suelta el candado de edición, por más tentador que sea: `_cargar_catalogo`
        # puede guardar POR SU CUENTA (siembra el doc si no está, backfill de plantillas) y eso
        # dispararía la liberación en medio de la sección crítica de otro — el candado quedaría
        # suelto justo cuando hace falta. Lo suelta el `teardown_request`, o el llamador de
        # `_cargar_catalogo_para_editar` cuando corre fuera de un request. Lo detectó
        # `verificar_config_concurrente.py` (el primer intento fallaba exactamente por esto).
        pass


def _guardar_catalogo_json_espejo(cat):
    """Escritura ATÓMICA con backup: se escribe a un temporal, se respalda el
    archivo bueno anterior (.bak) y recién ahí se reemplaza. Así una escritura
    interrumpida o concurrente nunca deja el catálogo corrupto ni borra datos."""
    ruta = os.path.join(DATOS, "productos_catalogo.json")
    with _lock_catalogo:
        tmp = ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cat, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
            try:
                import shutil
                shutil.copy2(ruta, ruta + ".bak")
            except Exception:
                pass
        # os.replace puede fallar con [WinError 5] "Acceso denegado" cuando OneDrive,
        # el antivirus o el indexador de Windows tienen el archivo tomado un instante
        # (muy típico si el proyecto está en Documentos/OneDrive). Casi siempre es
        # transitorio → reintentamos unas veces; el .tmp y el .bak protegen los datos.
        ultimo = None
        for intento in range(8):
            try:
                os.replace(tmp, ruta)
                ultimo = None
                break
            except PermissionError as e:
                ultimo = e
                time.sleep(0.2 * (intento + 1))
        if ultimo is not None:
            # El espejo es SOLO respaldo (la base ya guardó): si Windows bloquea el archivo,
            # se avisa pero NO se rompe el guardado.
            print(f"[catalogo] no se pudo escribir el espejo JSON (la base ya guardó): {ultimo}")


# ── EDITAR EL CATÁLOGO SIN PISARSE ────────────────────────────────────────────────────────────
# El catálogo es UNO solo y global, y ~43 endpoints lo modifican con el mismo patrón:
#     cat = _cargar_catalogo()   →   prod["lo_mío"] = ...   →   _guardar_catalogo(cat)
# `_lock_catalogo` sólo hace ATÓMICA la escritura del espejo en disco: NO cubre esa secuencia. Con
# `threaded=True` dos requests se entrelazan (los dos leen lo mismo, cada uno cambia lo suyo) y el
# que guarda último escribe SU copia ENTERA del catálogo — el cambio del otro desaparece, sin un
# solo error en pantalla. Y como el catálogo es global, no es sólo el mismo molde: quien configura
# el molde X pisa la config del molde Y de otro. Repro: `scratchpad/repro_lost_update.py`.
# El candado abarca LEER→MODIFICAR→GUARDAR: se toma al pedir el catálogo «para editar» y se suelta
# solo al terminar el request (o al guardar, si no hay request), así ningún endpoint tiene que
# acordarse de liberarlo aunque corte antes por una validación o un molde de otro usuario.
# ⚠️ Serializa SÓLO a los que escriben configuración: leer el catálogo (`_cargar_catalogo`) y
# generar la tizada no pasan por acá — la tizada nunca puede quedar detrás de un lock (entrada 169).
_LOCK_CAT_EDICION = threading.RLock()
_edicion_cat = threading.local()


def _cargar_catalogo_para_editar():
    """Catálogo FRESCO para modificar y volver a guardar, con el candado de edición ya tomado."""
    _LOCK_CAT_EDICION.acquire()
    _edicion_cat.n = getattr(_edicion_cat, "n", 0) + 1
    try:
        return _cargar_catalogo()
    except Exception:
        _soltar_edicion_catalogo()   # si ni leerlo se pudo, no dejamos el candado tomado
        raise


def _soltar_edicion_catalogo():
    """Suelta el candado tantas veces como ESTE hilo lo haya tomado. Idempotente: se puede llamar
    siempre (en el teardown de cualquier request, aunque no haya tocado el catálogo)."""
    n = getattr(_edicion_cat, "n", 0)
    _edicion_cat.n = 0
    for _ in range(n):
        try:
            _LOCK_CAT_EDICION.release()
        except RuntimeError:
            break


# ── PROPIEDAD DE UN MOLDE (Mis artículos) ─────────────────────────────────────────────────────
# Un molde que sube un usuario desde el pedido es SUYO: sólo lo ve él. Los moldes del catálogo
# (los que arma la configuración, sin dueño) los ven todos. Sin esto "Mis artículos" sería privado
# sólo de apariencia: con saber el id, cualquiera lee o edita el molde de otro.

def _usuario_actual():
    """Usuario logueado, o None si no hay sesión/base. Nunca revienta: si la API de usuarios no
    está disponible, el sistema sigue funcionando en modo de un solo usuario (como antes)."""
    try:
        from api_usuarios import usuario_actual
        return usuario_actual()
    except Exception:
        return None


def _uid_actual():
    u = _usuario_actual()
    return (u or {}).get("id")


def _es_privado(prod):
    """¿Este molde es de UNA persona (su «Mi artículo») o del CATÁLOGO (de todos)?

    ⚠️ Lo decide **`propio`**, NO `creado_por`. `creado_por` es AUTORÍA: quién lo dio de alta. Toda
    moldería del catálogo la crea alguien —y ese alguien está logueado—, así que usar `creado_por`
    como señal de privacidad **escondía del resto del mundo los moldes que se cargan desde
    Configuración**, que son justamente los que tienen que ver todos (lo reportó el usuario).
    `propio` sólo lo pone «Subir mi propio molde» del pedido. Ver §10.d del mapa."""
    p = prod or {}
    return bool(p.get("propio")) and bool(p.get("creado_por"))


def _puede_ver_molde(prod, u=None):
    """¿Este usuario puede ver este molde? Catálogo = lo ve cualquiera. «Mi artículo» = sólo su
    dueño (o quien tenga `molde.ver_todos`, p. ej. un admin — el permiso dice literalmente
    «ver también los moldes propios que subió cada usuario»)."""
    if not _es_privado(prod):
        return True
    if not _USUARIOS_ON:
        # Taller sin sistema de usuarios: no hay a quién ocultarle nada, y esconder un molde que
        # NADIE puede reclamar lo dejaría inaccesible para siempre.
        return True
    dueno = (prod or {}).get("creado_por")
    if u is None:
        u = _usuario_actual()
    if not u:
        return False
    return u.get("id") == dueno or "molde.ver_todos" in (u.get("permisos") or [])


def _puede_editar_molde(prod, permiso, u=None):
    """Ver no alcanza para ESCRIBIR. Un molde del catálogo lo ve todo el mundo (un Operario lo
    necesita para trabajar) pero sólo lo toca quien tenga el permiso (`molde.editar` /
    `molde.borrar`). Su propio «Mi artículo» lo configura siempre, sin permisos: para eso está.

    Sin sesión (taller de un solo usuario) no hay a quién pedirle permiso → se permite, que es
    como funcionó siempre."""
    if not permiso:
        return True
    if u is None:
        u = _usuario_actual()
    if not u:
        return True
    if _es_privado(prod):
        # UN «Mi artículo» LO TOCA SÓLO SU DUEÑO. Ni siquiera con `molde.editar`: es de esa
        # persona, no del taller. `molde.ver_todos` da VER (soporte, auditoría), no escribir —
        # si no, un admin podía editarle el artículo privado a otro.
        return (prod or {}).get("creado_por") == u.get("id")
    return permiso in (u.get("permisos") or [])


def _guard_molde(pid, permiso=None):
    """Corta la request si el molde no es visible para este usuario, o si lo es pero le falta el
    permiso para tocarlo. Devuelve None si está permitido."""
    cat = _cargar_catalogo()
    prod = next((p for p in cat.get("productos", []) if p.get("id") == pid), None)
    if prod is None:
        return None                      # no existe: lo maneja cada endpoint como ya lo hacía
    _u = _usuario_actual()
    if not _puede_ver_molde(prod, _u):
        return jsonify({"error": "Ese molde es de otro usuario"}), 403
    if not _puede_editar_molde(prod, permiso, _u):
        if _es_privado(prod):
            return jsonify({"error": "Ese artículo es de otro usuario: sólo su dueño lo puede tocar."}), 403
        return jsonify({"error": f"Tu usuario no tiene el permiso «{permiso}». Esa moldería es del "
                                 f"catálogo (la comparten todos) y ese permiso se da por ROL en "
                                 f"Configuración › Usuarios y permisos."}), 403
    return None


def _guard_id(cuerpo, permiso="molde.editar"):
    """Guarda de DUEÑO + PERMISO para los endpoints que reciben el molde en el campo `id`.

    `_pid_de_request` ignora `id` A PROPÓSITO (en varios endpoints `id` es un preset, una regla o
    un grupo, y tomarlo como molde escribiría en el producto equivocado), así que estas rutas se
    saltaban `_guardia_moldes` por completo: cualquiera podía borrar, renombrar o activar el molde
    de otro usuario — y borrar hace `rmtree` de sus archivos. Por eso la guarda va acá, explícita,
    endpoint por endpoint. Devuelve None si está permitido, o la respuesta 403 si no.

    El permiso por defecto es `molde.editar` porque casi todas estas rutas ESCRIBEN; las que sólo
    usan el molde (activar) pasan `permiso=None` y las destructivas, `molde.borrar`.
    """
    pid = (cuerpo or {}).get("id")
    if not pid:
        return None                      # sin molde: lo maneja el endpoint como ya lo hacía
    return _guard_molde(str(pid), permiso)


def _pid_de_request():
    """`pid` explícito que venga en la request (query, form o JSON). Sólo se aceptan los nombres
    `pid`/`producto_id`: `id` NO, porque en varios endpoints significa otra cosa (un preset, un
    grupo) y tomarlo como molde llevaría a escribir en el producto equivocado."""
    if not has_request_context():
        return None
    try:
        # 1) el pid en la RUTA (`/api/productos/<pid>/preview`, `/descargar_plantilla`…). Iba
        #    primero porque si no, esas rutas se salteaban la guardia de moldes ajenos: el id no
        #    viaja ni en la query ni en el body.
        m = re.match(r"^/api/productos/(prod_[^/]+)/", request.path or "")
        if m:
            return m.group(1)
        v = request.args.get("pid") or request.args.get("producto_id")
        if not v and request.method in ("POST", "PUT", "PATCH", "DELETE"):
            d = request.get_json(silent=True)
            if isinstance(d, dict):
                v = d.get("pid") or d.get("producto_id")
            if not v:
                v = request.form.get("pid") or request.form.get("producto_id")
        v = str(v or "").strip()
        return v or None
    except Exception:
        return None


def _get_active_producto_id():
    """Con qué MOLDE trabaja esta llamada, por orden de prioridad:

    1. el `pid` explícito de la request — permite trabajar sobre un molde puntual sin "activarlo";
    2. el molde activo DE ESTA SESIÓN — cada usuario trabaja el suyo sin pisar al de al lado;
    3. el activo global del catálogo (compatibilidad con el modo de un solo usuario).

    El punto 3 solo era un campo ÚNICO y compartido: dos personas subiendo su molde a la vez se
    pisaban los archivos. Por eso 1 y 2 van primero.
    """
    pid = _pid_de_request()
    if pid:
        return pid
    cat = _cargar_catalogo()
    if has_request_context():
        try:
            s = session.get("pid_activo")
            # El molde de la sesión puede haber sido BORRADO (o ser de otro): si ya no está en el
            # catálogo se ignora, o todo el sistema queda trabajando contra un molde inexistente
            # (404 al activarlo, 409 al detectarlo) hasta cerrar sesión.
            if s and any(x.get("id") == s for x in cat.get("productos", [])):
                return s
            if s:
                session.pop("pid_activo", None)
        except Exception:
            pass
    return cat.get("activo", "prod_default")


def _slugify_diseno(s):
    """Nombre de diseño → slug. Vacío/'Principal' → 'principal' (el arte base)."""
    s = str(s or "").strip().lower()
    if not s or s in ("principal", "default"):
        return "principal"
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:48] or "principal"


def _diseno_sub(diseno):
    """Subcarpeta para un diseño nombrado. El diseño por defecto ('principal' o
    vacío) usa la carpeta raíz del producto → 100% compatible con lo de hoy."""
    slug = _slugify_diseno(diseno)
    return None if slug == "principal" else os.path.join("disenos", slug)


def _ruta_datos(nombre, pid=None, sub=None):
    pid = pid or _get_active_producto_id()
    pdir = os.path.join(DATOS, "productos", pid)
    if sub:
        pdir = os.path.join(pdir, sub)
    os.makedirs(pdir, exist_ok=True)
    return os.path.join(pdir, nombre)


def _ruta_entrada(nombre, pid=None, sub=None, original=False):
    """Ruta de un archivo de entrada. Para el ARTE devuelve la VERSIÓN VIGENTE (editar el diseño
    crea versiones nuevas y no toca el archivo que subió el usuario) — ver `objetos_agregados`.
    `original=True` fuerza el archivo base: sólo lo usa la subida del arte."""
    pid = pid or _get_active_producto_id()
    pdir = os.path.join(ENTRADA, pid)
    if sub:
        pdir = os.path.join(pdir, sub)
    os.makedirs(pdir, exist_ok=True)
    p = os.path.join(pdir, nombre)
    # Archivos VERSIONADOS: el arte (al inyectar objetos) y la plantilla (al nombrar variantes).
    # En los dos casos el original del usuario queda intacto y el sistema usa la versión vigente.
    if nombre in ("arte.ai", "plantilla.ai") and not original:
        return OA.ruta_vigente(p)
    return p


_DETECCION_CACHE_V = 2     # subir esto invalida TODAS las cachés (cambió el formato de `det`)


def _deteccion_cache(arte, reg):
    """`MP.detectar_arte` con caché en disco: es lo que hace lento el paso Arte.

    Con un arte pesado tarda ~5 s (el 95% es vectorizar cada mesa a SVG) y se vuelve a pedir
    ENTERO cada vez que se entra al paso Arte, siempre con el mismo archivo. La caché vive al
    lado del arte y se invalida sola: la clave lleva el archivo (ruta + fecha + tamaño) y los
    nombres de las piezas del molde, que son de donde salen las sugerencias.

    Devuelve un dict FRESCO en cada llamada (el que llama le agrega `modo`/`mapeo`), así que
    mutarlo no ensucia la caché."""
    import hashlib
    try:
        clave = hashlib.sha1(json.dumps([
            os.path.abspath(arte), int(os.path.getmtime(arte)), os.path.getsize(arte),
            sorted(reg.keys()), _DETECCION_CACHE_V,
        ]).encode("utf-8")).hexdigest()
    except Exception:
        return MP.detectar_arte(arte, reg)     # sin clave confiable, mejor no cachear
    ruta = os.path.join(os.path.dirname(arte), ".deteccion_cache.json")
    try:
        with open(ruta, encoding="utf-8") as f:
            g = json.load(f)
        if g.get("clave") == clave and isinstance(g.get("det"), dict):
            return g["det"]
    except Exception:
        pass
    det = MP.detectar_arte(arte, reg)
    try:
        tmp = ruta + ".tmp"                    # atómico: dos pestañas pueden pedirlo a la vez
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"clave": clave, "det": det}, f)
        os.replace(tmp, ruta)
    except Exception:
        pass
    return det


def _en_hilo(fn):
    """Corre `fn` en un hilo de fondo cerrando al final los PDFs que haya abierto. El
    `teardown_request` de Flask sólo alcanza a los hilos de request; sin esto un pre-warm dejaba
    el arte/la plantilla trabados (en Windows no se pueden reemplazar ni borrar)."""
    def _envuelto():
        try:
            fn()
        finally:
            try:
                MP.cerrar_abiertos()
            except Exception:
                pass
            # Un hilo de fondo no tiene `teardown_request`: si tocó el catálogo «para editar»,
            # acá es el único lugar donde se puede soltar el candado. Sin esto, un pre-warm que
            # falle a mitad dejaría colgada TODA la configuración del sistema.
            try:
                _soltar_edicion_catalogo()
            except Exception:
                pass
    threading.Thread(target=_envuelto, daemon=True).start()


# Rutas de API que funcionan SIN sesión: el login mismo, la salud (monitoreo/instalador) y la
# actualización taller→publicado (protegida por su propio token X-Token-Act, no por sesión).
_API_SIN_SESION = ("/api/auth/", "/api/salud", "/api/actualizacion/")

# POSTs que reciben un molde pero NO lo modifican: rendes y generación de tizada. No pueden pedir
# `molde.editar` — un Operario (sólo `molde.ver` + los de pedido) tiene que poder generar y ver el
# preview del catálogo. Todo lo demás que llegue por POST/PUT/PATCH/DELETE con `pid` SÍ escribe.
_API_LEE_CON_PID = ("/api/arte/preview_piezas", "/api/generar", "/api/generar_multi")

# PREFIJO de sub-ruta donde se publica la app (nginx hace `proxy_pass` y lo QUITA). Si alguien entra
# al servidor SIN pasar por nginx (localhost:8050 o la IP, típico al abrirlo en la propia máquina),
# el frontend —compilado con base `/Tizadapro/`— pide `/Tizadapro/api/…` y nadie saca el prefijo:
# Flask devolvía un 404/405 en HTML y el navegador tiraba «Unexpected token '<', "<!DOCTYPE"» (o sea,
# el login y las telas fallaban sin dar explicación). Se saca acá para que ande con y sin nginx.
#
# Va como MIDDLEWARE WSGI y no como `before_request` a propósito: Flask resuelve la ruta ANTES de los
# before_request, así que ahí ya sería tarde (el 404 estaría decidido).
_PREFIJO_APP = "/" + (os.environ.get("TIZADA_PREFIJO") or "Tizadapro").strip("/")


class _QuitarPrefijo:
    def __init__(self, app_wsgi, prefijo):
        self.app_wsgi, self.prefijo = app_wsgi, prefijo

    def __call__(self, environ, start_response):
        p = environ.get("PATH_INFO", "")
        if self.prefijo and (p == self.prefijo or p.startswith(self.prefijo + "/")):
            environ["PATH_INFO"] = p[len(self.prefijo):] or "/"
            # SCRIPT_NAME = dónde vive la app → url_for/redirects siguen apuntando bien.
            environ["SCRIPT_NAME"] = environ.get("SCRIPT_NAME", "") + self.prefijo
        return self.app_wsgi(environ, start_response)


app.wsgi_app = _QuitarPrefijo(app.wsgi_app, _PREFIJO_APP)


@app.before_request
def _guardia_moldes():
    """SEGURIDAD en dos capas, para TODA la API:

    1) SESIÓN OBLIGATORIA: el login del frontend es una cortina (ocultar ≠ proteger); sin esto,
       cualquiera con la URL (o F12/curl) llamaba los endpoints sin loguearse. Si el sistema de
       usuarios no está registrado (taller sin base MSSQL), no se puede exigir y se deja pasar.
    2) PROPIEDAD DEL MOLDE: corta cualquier request que trabaje sobre un molde de OTRO usuario.

    Va acá y no endpoint por endpoint a propósito: son ~30 rutas que reciben un molde y alcanza
    con que se olvide UNA para que el molde ajeno quede accesible. El molde se resuelve igual que
    en el resto del sistema (`pid` de la request → activo de la sesión)."""
    if not request.path.startswith("/api/") or any(request.path.startswith(p) for p in _API_SIN_SESION):
        return None
    if _USUARIOS_ON:
        try:
            _u = _usuario_actual()
        except Exception:
            _u = True              # la base parpadeó: la seguridad no puede tumbar el sistema
        if not _u:
            return jsonify({"error": "no hay sesión iniciada"}), 401
    try:
        pid = _pid_de_request()
        if not pid:
            return None            # sin molde explícito no hay nada que proteger acá
        # 3) ESCRIBIR EL CATÁLOGO PIDE PERMISO. Una moldería del catálogo la VE todo el mundo (un
        #    Operario la necesita para trabajar), pero tocarla es otra cosa. Antes lo que hacía de
        #    candado era el DUEÑO, y al arreglar «lo que subo desde Configuración es de todos» ese
        #    candado desaparecía: cualquiera con sesión podría re-subir el molde o renombrarle las
        #    piezas al catálogo compartido. Se mira el MÉTODO porque son ~30 rutas y la que se
        #    olvide queda abierta; las de sólo lectura/generación van en la lista de excepciones.
        _escribe = (request.method in ("POST", "PUT", "PATCH", "DELETE")
                    and request.path not in _API_LEE_CON_PID)
        return _guard_molde(pid, "molde.editar" if _escribe else None)
    except Exception:
        return None                # la seguridad no puede tumbar el sistema


@app.teardown_request
def _soltar_catalogo(_exc=None):
    """Suelta el candado de edición del catálogo pase lo que pase. Un endpoint puede cortar ANTES
    de guardar (validación, molde de otro usuario, excepción): sin esto el candado quedaría tomado
    y la siguiente edición de cualquiera se colgaría para siempre."""
    _soltar_edicion_catalogo()


@app.teardown_request
def _cerrar_pdfs(_exc=None):
    """Al terminar CADA request se cierran los PDFs que quedaron abiertos. Sin esto, en Windows el
    arte/la plantilla quedan trabados y no se pueden reemplazar ni borrar (WinError 5)."""
    try:
        MP.cerrar_abiertos()
    except Exception:
        pass


@app.errorhandler(Exception)
def _error_no_controlado(e):
    """Cualquier error no previsto vuelve como JSON legible (nunca una página
    HTML de stacktrace), y el detalle queda en la ventana del servidor. Los
    errores HTTP normales (404, etc.) se dejan pasar tal cual."""
    if isinstance(e, HTTPException):
        return e
    traceback.print_exc()
    return jsonify({"error": f"error interno del servidor: {e}"}), 500


@app.after_request
def _evitar_cache(response):
    # Excepción: lo que ya se marcó `immutable` (las mesas del arte) lleva la firma del archivo
    # en su propia URL — cachearlo es justamente lo que evita volver a bajar megabytes de dibujo.
    if "immutable" in (response.headers.get("Cache-Control") or ""):
        return response
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, public, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/favicon.ico")
def _favicon():
    return ("", 204)


_REG_DB_CACHE = {}   # pid -> (rev, registro): caché de lectura, validada contra registro_rev


def _reg_rev(pid):
    """Revisión del registro en la base — la señal de versión para TODAS las claves de caché
    (reemplaza al mtime del JSON: sin espejo no hay archivo que mirar). -1 si la base no
    responde: invalida siempre, y el error real lo da la lectura."""
    try:
        return db.registro_rev(pid) or 0
    except Exception:
        return -1


def _cargar(nombre, pid=None, sub=None):
    # REGISTRO DE PIEZAS: LA BASE ES LA ÚNICA FUENTE (2026-08-19, decisión del usuario: sin
    # espejo — «debe ser profesional»). Si la base no responde, la operación falla con error
    # claro: NUNCA se sigue en silencio con un archivo posiblemente viejo. Caché en memoria
    # validada por `registro_rev` (1 query barata); la escritura la invalida además localmente.
    if nombre == "registro_producto.json" and sub is None:
        _pid = pid or _get_active_producto_id()
        rev = db.registro_rev(_pid)          # si la base está caída, esto LEVANTA — a propósito
        if rev is None:
            return None                      # el molde no existe en la base → sin registro
        hit = _REG_DB_CACHE.get(_pid)
        if hit and hit[0] == rev:
            return hit[1]
        reg = db.leer_registro(_pid)
        _REG_DB_CACHE[_pid] = (rev, reg)
        return reg
    try:
        return json.load(open(_ruta_datos(nombre, pid, sub=sub), encoding="utf-8"))
    except Exception:
        return None


def _guardar_registro(pid, reg, reset=False):
    """EL único camino para escribir el registro: la BASE (pieza / pieza_talle), transaccional.
    Si la base falla, la operación FALLA — sin espejo, sin modo degradado. `piezas.json` se
    regenera como ÍNDICE derivado local (la identidad ya queda en la tabla `pieza`).
    `reset=True` = molde re-subido (ids desde 1)."""
    try:
        _regenerar_piezas_index(pid, reg=reg, reset=reset)
    except Exception as e:
        print(f"[registro] no se pudo refrescar piezas.json: {e}")
    piezas = (_cargar("piezas.json", pid) or {}).get("piezas") or []
    db.guardar_registro(pid, [x for x in piezas if not x.get("retirada")], reg)
    _REG_DB_CACHE.pop(pid, None)


# ── AJUSTE DEL EMPAREJADO ENTRE TALLES (ver §10.c del mapa) ───────────────────────────
# Cuando el molde NO trae las piezas dispuestas de forma parecida en cada talle, la
# heurística (`_emparejar_por_forma`) no tiene señal y propaga el nombre a la pieza
# equivocada. El usuario lo arregla a mano y eso vive acá:
#   {"acomodo": {talle: {idx: [dx_mm, dy_mm]}},   ← reacomodo VIRTUAL (solo para emparejar)
#    "manual":  {talle: {nombre_pieza: idx}}}     ← corrección directa, MANDA sobre todo
def _emparejado_cfg(pid=None):
    d = _cargar("emparejado_talles.json", pid) or {}
    return {"acomodo": d.get("acomodo") or {}, "manual": d.get("manual") or {}}


@app.get("/")
@app.get("/admin")
def inicio():
    # El index.html NO se cachea: así el navegador siempre carga la última build
    # (los assets llevan hash en el nombre, esos sí se pueden cachear).
    resp = send_from_directory("frontend/dist", "index.html")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.get("/api/estado_general")
def estado_general():
    reg = _cargar("registro_producto.json")
    val = _cargar("validacion_arte.json")
    # Talles en el orden del archivo (panel de capas), no alfabético. Primero se
    # juntan preservando la aparición y luego se ordenan según el .ai si existe.
    talles = []
    vistos = set()
    for p in (reg or {}).values():
        for t in p:
            if t not in vistos:
                vistos.add(t)
                talles.append(t)
    plantilla = _ruta_entrada("plantilla.ai")
    if talles and os.path.exists(plantilla):
        talles = MP.talles_orden_archivo(plantilla, talles)
    return jsonify({
        "plantilla": _cargar("resumen_plantilla.json"),
        "arte": val,
        "fuentes": list(MP.catalogo_fuentes(FUENTES).values()),
        "talles": talles,
        "listo_para_pedidos": bool(reg) and bool(val and val.get("aprobado")),
    })


def _descartar_tmp(ruta):
    """Borra el temporal de una subida que no llegó a buen puerto. Nunca toca el molde bueno."""
    try:
        if ruta and os.path.exists(ruta):
            os.remove(ruta)
    except Exception:
        pass


@app.post("/api/plantilla")
def subir_plantilla():
    f = request.files.get("archivo")
    if not f:
        return jsonify({"error": "falta el archivo"}), 400
    destino = _ruta_entrada("plantilla.ai", original=True)
    # ── SUBIDA ATÓMICA ───────────────────────────────────────────────────────────────────────
    # El archivo entra a un TEMPORAL y sólo reemplaza al molde bueno si se pudo procesar.
    # Antes se guardaba encima y recién después se procesaba: si el alta fallaba (422), el molde
    # quedaba con el ARCHIVO NUEVO y el REGISTRO VIEJO — o sea, las piezas registradas apuntando
    # a la geometría de otro archivo. Un molde así se ve bien y genera cualquier cosa.
    # ⚠️ El temporal CONSERVA la extensión `.ai`: PyMuPDF deduce el tipo de documento por la
    # extensión, y con un `.tmp` no lo abriría (y el alta fallaría por una razón inventada).
    tmp = os.path.join(os.path.dirname(destino), "plantilla.subiendo.ai")
    nombre = (f.filename or "").lower()
    # Si YA había un molde con piezas nombradas, sacar una FOTO de su talle guía antes
    # de pisarlo: si el archivo nuevo es el mismo molde (re-subida, p. ej. reimportar el
    # DXF con curvas), los nombres se transfieren solos y no se pierde el trabajo.
    snap_nombres = None
    try:
        if os.path.exists(destino):
            _reg_viejo = _cargar("registro_producto.json")
            if _reg_viejo:
                snap_nombres = MP.snapshot_nombres_guia(destino, _reg_viejo)
    except Exception:
        snap_nombres = None
    dxf_resumen = None
    _corresp_nueva = None          # correspondencia pieza↔talle del DXF (se escribe con el commit)
    if nombre.endswith(".dxf"):
        # Molde en DXF (AAMA/ASTM de Optitex, Gerber, Lectra…): se CONVIERTE a un PDF
        # con una capa por talle + los contornos de cada pieza, igual que un .ai.
        # Las curvas del archivo (bulge/spline/elipse) se conservan EXACTAS (Bézier).
        import importar_dxf, traceback as _tb
        # Guardar el DXF original SIEMPRE (antes de convertir): así, aunque la conversión
        # falle, queda el archivo para diagnosticar/reimportar y no se pierde.
        fuente = _ruta_entrada("plantilla_fuente.dxf")
        f.save(fuente)
        try:
            pdf_bytes, dxf_resumen = importar_dxf.dxf_a_pdf(fuente)
            with open(tmp, "wb") as g:
                g.write(pdf_bytes)
        except Exception as e:
            _tb.print_exc()
            _descartar_tmp(tmp)
            return jsonify({"error": f"no se pudo importar el DXF: {e}"}), 422
        # Correspondencia EXACTA pieza↔talle del DXF (Piece Name + Size): la usan el
        # nido y el registro para NO adivinar el emparejado entre talles.
        # Se GUARDA EN MEMORIA y se escribe recién con el `os.replace` de más abajo: forma parte
        # de la misma transacción que el archivo del molde (ver «EL REEMPLAZO, AL FINAL Y ATÓMICO»).
        try:
            _corresp_nueva = dxf_resumen.pop("indices", None)
        except Exception:
            _corresp_nueva = None
    else:
        # .ai / .pdf (Illustrator, Corel, InDesign…): PyMuPDF los lee directo.
        f.save(tmp)
    if dxf_resumen:
        # DXF: NO corremos alta_plantilla (busca etiquetas «Talle-Pieza-#» que Optitex no
        # pone → solo genera ruido y tarda). Los talles ya vienen del DXF; las piezas se
        # nombran en el visor. Resumen mínimo.
        alta = {"mesas": 1, "talles": dxf_resumen.get("talles", []), "piezas": [],
                "completos": [], "registro": {}, "problemas": [], "advertencias": [],
                "piezas_detalle": {}}
    else:
        try:
            alta = MP.alta_plantilla(tmp)          # se valida ANTES de pisar el molde bueno
        except Exception as e:
            _descartar_tmp(tmp)
            return jsonify({"error": f"no se pudo procesar la plantilla: {e}"}), 422
    # Si el DXF trajo NOMBRES de pieza, se aplican SOLOS (arma el registro con esos
    # nombres, emparejando por posición). SOLO para moldes chicos: con muchas piezas el
    # emparejado es carísimo (O(n²)×talles, +30s) → se saltea y se nombran en el visor/modelos.
    _nombres = [n for n in (dxf_resumen.get("nombres") or []) if str(n).strip()] if dxf_resumen else []
    if _nombres and len(_nombres) <= 25:
        try:
            det = MP.detectar_piezas(tmp)
            nombres = dxf_resumen["nombres"]
            asign = [{"idx": i, "nombre": nombres[i]}
                     for i in range(min(len(det["piezas"]), len(nombres))) if str(nombres[i]).strip()]
            manual = MP.alta_plantilla_manual(tmp, asign, det["mesa"], det["talle_ref"], indices=_corresp_nueva or _cargar("correspondencia_piezas.json") or None, emparejado=_emparejado_cfg()) if asign else None
            if manual and manual.get("registro"):
                alta = manual
                dxf_resumen["nombres_aplicados"] = sorted(manual["registro"].keys())
        except Exception:
            pass
    elif _nombres:
        # molde grande: no se auto-nombra ahora (se hace al organizar en Modelos)
        dxf_resumen["nombres_pendientes"] = len(_nombres)
    # ⛔ RE-SUBIR = EMPEZAR DE CERO (regla del usuario 2026-08-19). Antes acá se TRANSFERÍAN los
    # nombres del molde anterior emparejando geometría vieja→nueva; si el registro anterior estaba
    # cruzado, el cruce se heredaba para siempre. Ahora el archivo nuevo arranca limpio: sin
    # nombres heredados, ids desde 1, y las piezas se nombran en la carga (Agrupar piezas).
    nombres_conservados = None
    # ── EL REEMPLAZO, AL FINAL Y ATÓMICO ──────────────────────────────────────────────────────
    # Todo lo de arriba se hizo sobre el temporal. Si llegamos hasta acá, el archivo sirve.
    # ⚠️ En Windows `os.replace` falla con WinError 5 si algún proceso tiene el PDF abierto, así
    # que primero se cierran los documentos que dejó el procesado (§10.b del mapa).
    try:
        MP.cerrar_abiertos()
    except Exception:
        pass
    try:
        os.replace(tmp, destino)
    except Exception as e:
        _descartar_tmp(tmp)
        return jsonify({"error": f"no se pudo reemplazar el molde (¿está abierto en otro programa?): {e}"}), 422
    # Molde nuevo = se descartan las versiones del anterior (p. ej. el renombrado de variantes),
    # o quedaría vigente una versión que ya no corresponde a este archivo. Va DESPUÉS del
    # reemplazo: si la subida falla, el molde viejo y sus versiones quedan intactos.
    OA.reset_versiones(destino)
    # Correspondencia EXACTA pieza↔talle del DXF (Piece Name + Size): la usan el nido y el registro
    # para NO adivinar el emparejado entre talles. Va acá, con el molde ya reemplazado.
    if _corresp_nueva:
        try:
            json.dump(_corresp_nueva, open(_ruta_datos("correspondencia_piezas.json"), "w", encoding="utf-8"), ensure_ascii=False)
        except Exception:
            pass
    # RESET del molde re-subido: piezas (ids desde 1), emparejado manual y las VARIABLES/grupos
    # que apuntaban a las piezas del archivo anterior (quedarían colgadas de ids muertos).
    _pid_reset = _get_active_producto_id()
    try:
        os.remove(_ruta_datos("emparejado_talles.json", _pid_reset))
    except OSError:
        pass
    try:
        cat_r = _cargar_catalogo_para_editar()
        prod_r = next((x for x in cat_r["productos"] if x["id"] == _pid_reset), None)
        if prod_r is not None:
            for _k in ("variantes", "grupos", "conjuntos"):
                if prod_r.get(_k):
                    prod_r[_k] = []
            _guardar_catalogo(cat_r)
    except Exception as e:
        print(f"[subir_plantilla] no se pudieron resetear las variables: {e}")
    finally:
        _soltar_edicion_catalogo()
    try:
        db.borrar_piezas_molde(_pid_reset)   # la base también arranca de cero
    except Exception as e:
        print(f"[subir_plantilla] no se pudo resetear la base: {e}")
    _guardar_registro(_pid_reset, alta["registro"], reset=True)
    resumen = {"archivo": f.filename, "mesas": alta["mesas"], "piezas": alta["piezas"],
               "talles": alta["talles"],
               "completitud": f"{len(alta['completos'])}/{len(alta['talles'])} talles completos",
               "problemas": alta["problemas"],
               "advertencias": alta.get("advertencias", []),
               "piezas_detalle": alta.get("piezas_detalle", {}),
               "nombres_conservados": nombres_conservados,
               "dxf": dxf_resumen}
    json.dump(resumen, open(_ruta_datos("resumen_plantilla.json"), "w", encoding="utf-8"), ensure_ascii=False)
    # El lienzo de «Nombrar piezas» se arma YA, en segundo plano: cuando el usuario entre
    # está listo (el alta recién calentó el caché de extracción, así que cuesta poco).
    threading.Thread(target=_prewarm_deteccion_todas, args=(_pid_reset,), daemon=True).start()
    return jsonify(resumen)


def _deteccion_base_cached(pid, talle_ref, candidatas=False):
    """`candidatas=True` = universo de piezas de la herramienta «variantes POR PIEZAS»: se lee el
    molde ORIGINAL (no la versión ya partida en capas) y se aceptan capas que todavía no son
    talle. Leer el original es lo que hace que los índices de pieza NO cambien: si se leyera la
    versión partida, después de asignar una vez la herramienta mostraría sólo las piezas de un
    talle y no habría forma de corregir la asignación guardada."""
    """`MP.detectar_piezas` (lo CARO: get_drawings de TODO el molde, ~2.3s) CACHEADO a disco por
    (mtime plantilla, talle). NO depende de la variable ni del diseño → un solo cálculo por
    (molde, talle) sirve a todas. Antes se recalculaba en CADA `/api/plantilla/deteccion` (19×
    al asignar variantes = ~85s). El caché lo baja a 1× por talle (y el pool los pre-genera)."""
    pl = _ruta_entrada("plantilla.ai", pid, original=candidatas)
    try: mt = int(os.path.getmtime(pl))
    except OSError: mt = 0
    cdir = _ruta_datos("deteccion_cache", pid)
    # el flag entra en la CLAVE: la detección "con candidatas" da otras piezas que la normal y
    # servir una por la otra dejaría el visor mostrando cualquier cosa
    # `dv2`: el ORDEN de las piezas cambió (entrada 182, ya no se reordena por posición) sin
    # cambiar el mtime del archivo → un caché sin versión seguiría sirviendo los índices viejos.
    fp = os.path.join(cdir, re.sub(r"[^A-Za-z0-9_-]+", "_",
                                   f"{mt}_dv2_{talle_ref or 'auto'}{'_cand' if candidatas else ''}") + ".json")
    try:
        return json.load(open(fp, encoding="utf-8"))
    except Exception:
        pass
    res = MP.detectar_piezas(pl, talle_ref=talle_ref, capas_candidatas=candidatas)
    try:
        os.makedirs(cdir, exist_ok=True)
        json.dump(res, open(fp, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass
    return res


@app.get("/api/plantilla/deteccion")
def plantilla_deteccion():
    """Detecta las piezas de la moldería para el etiquetador visual."""
    pl = _ruta_entrada("plantilla.ai")
    if not os.path.exists(pl):
        return jsonify({"error": "primero subí la plantilla base"}), 409
    talle_ref = request.args.get("talle_ref")
    # `?candidatas=1` = herramienta de VARIANTES POR PIEZAS: si el molde no tiene ni un talle,
    # igual devolvé las piezas de la capa que las tenga (si no, no hay nada que seleccionar).
    _cand = str(request.args.get("candidatas") or "") in ("1", "true", "si", "sí")
    _pid_act = _get_active_producto_id()
    if not talle_ref:
        # Sin pedido explícito → usar la variante de guía guardada en la base
        # para este molde (compartida entre todos los usuarios). Así, elija quien
        # elija M, siempre se abre en M sin importar el navegador.
        prod = next((p for p in _cargar_catalogo()["productos"] if p["id"] == _pid_act), None)
        if prod and prod.get("variante_guia"):
            talle_ref = prod["variante_guia"]
    try:
        res = _deteccion_base_cached(_pid_act, talle_ref, _cand)
    except Exception:
        # La variante guardada puede ya no existir en la plantilla → reintentar
        # con la automática para no romper la carga.
        if talle_ref:
            try:
                res = _deteccion_base_cached(_pid_act, None, _cand)
            except Exception as e:
                if _falta_nombrar_variantes(_pid_act):
                    return jsonify(_deteccion_pendiente())
                return jsonify({"error": f"no se pudieron detectar las piezas: {e}"}), 422
        else:
            if _falta_nombrar_variantes(_pid_act):
                return jsonify(_deteccion_pendiente())
            return jsonify({"error": "no se pudieron detectar las piezas"}), 422
    try:
        # Cargar etiquetas existentes si las hay para precargarlas en el frontend
        reg = _cargar("registro_producto.json")
        nombres_existentes = {}
        if reg:
            talle_ref = res.get("talle_ref")
            mesa = res.get("mesa")
            for nombre_pieza, por_talle in reg.items():
                if talle_ref in por_talle:
                    info = por_talle[talle_ref]
                    if info.get("mesa") == mesa:
                        idx = info.get("pieza_idx")
                        if idx is not None:
                            nombres_existentes[idx] = nombre_pieza
        res["nombres_existentes"] = nombres_existentes
        # Dimensión de referencia (alto/ancho) y medidas recomendadas del diseño
        # por pieza, para que cubra todos los talles sin huecos.
        pid = _get_active_producto_id()
        prod = next((p for p in _cargar_catalogo()["productos"] if p["id"] == pid), None)
        ref = (prod or {}).get("referencia_medida") or "alto"
        res["referencia_medida"] = ref
        res["medidas_diseno"] = MP.medidas_diseno(reg, ref, talle_guia=res.get("talle_ref")) if reg else {}
        # Identidad ESTABLE de las piezas (id ↔ clave), para que el frontend resuelva las
        # variables por id y no por pieza_idx (que varía por talle → la pieza se caía al cambiar
        # de talle en el visor). Es talle-independiente; viene igual en cada detección.
        # SIN las retiradas: son el historial (para no reciclar ids) y no tienen que llegar al
        # front, que arma un `{id: clave}` recorriendo la lista — una retirada con el nombre viejo
        # pisaba a la viva y la pieza renombrada desaparecía del visor.
        res["piezas_id"] = [p for p in ((_cargar("piezas.json", pid) or {}).get("piezas") or [])
                            if not p.get("retirada")]
        # ACOTAR A LA VARIABLE: si el cliente (paso Arte) pasa `?variante=v_xxx`, se devuelven SOLO
        # las piezas de esa variable (no las ~135 del molde) → la respuesta baja ~15× (el visor usa
        # ~9). El caché en disco sigue siendo full (compartido); el filtro es post-caché, sobre un
        # objeto fresco (json.load). SIN `variante` → molde completo (etiquetador visual / renombrado).
        _var = request.args.get("variante")
        if _var and reg:
            _nombres = set(_piezas_de_variable(prod, _var, reg) or [])
            if _nombres:
                _tref, _mesa = res.get("talle_ref"), res.get("mesa")
                _idxs = {int((reg[_nm][_tref])["pieza_idx"]) for _nm in _nombres
                         if _tref in (reg.get(_nm) or {}) and reg[_nm][_tref].get("mesa") == _mesa
                         and reg[_nm][_tref].get("pieza_idx") is not None}
                res["piezas"] = [p for p in (res.get("piezas") or []) if p.get("idx") in _idxs]
                res["medidas_diseno"] = {k: v for k, v in (res.get("medidas_diseno") or {}).items() if k in _nombres}
        # ── ESTADO DEL MOLDE (no de esta vista) ────────────────────────────────
        # `talle_ref`/`talles` son de la detección que se está mostrando: con `candidatas=1` salen
        # del archivo ORIGINAL («Capa 1»). La pantalla necesita el estado del MOLDE: cuáles son sus
        # variantes de verdad, cuál es la de guía y si todavía falta algo. Sin esto, un molde ya
        # resuelto mostraba «Guía: Capa 1» y el cartel de «todavía no se puede usar».
        _reales = _talles_reales(pid)
        res["talles_reales"] = _reales
        res["resuelto"] = bool(_reales)
        if _reales:
            res["sin_variantes"] = False
            res["falta_nombrar_variantes"] = False
            # AUTO-CORRECCIÓN de los moldes que ya quedaron con la guía apuntando al nombre viejo
            # de la capa: se arregla sola al abrirlos, sin pedirle nada al usuario. Sólo si la
            # guía está PUESTA y ya no existe — sin guía ("automática") el sistema elige solo, y
            # escribirle una acá le cambiaría el talle con el que abre a moldes que andan bien.
            _g = (prod or {}).get("variante_guia")
            if _g and _g not in _reales and _ajustar_variante_guia(pid, _reales):
                prod = next((p for p in _cargar_catalogo()["productos"] if p["id"] == pid), None)
        # La guía que MUESTRA la pantalla: la guardada si sigue existiendo; si no, la de esta
        # detección (cuando es una variante de verdad) y, en última instancia, la primera real.
        _g2 = (prod or {}).get("variante_guia")
        _tr = res.get("talle_ref")
        res["guia"] = (_g2 if _g2 in _reales else None) or (_tr if _tr in _reales else None) \
            or (_reales[0] if _reales else _tr)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": f"no se pudieron detectar las piezas: {e}"}), 422


def _prewarm_deteccion_todas(pid):
    """Arma el caché del lienzo TODAS en segundo plano, apenas se sube el molde: para
    cuando el usuario entra a «Nombrar piezas» ya está listo (antes la primera entrada
    pagaba ~12 s de extracción en frío). Best-effort: si falla, el endpoint lo arma."""
    try:
        pl = _ruta_entrada("plantilla.ai", pid)
        mt = int(os.path.getmtime(pl))
        cdir = _ruta_datos("deteccion_cache", pid)
        fp = os.path.join(cdir, f"{mt}_dv2_TODAS.json")
        if os.path.exists(fp):
            return
        import variantes_molde as VM
        try:
            formato = VM.analizar(pl).get("formato") or "extendido"
        except Exception:
            formato = "extendido"
        res = MP.detectar_piezas_todas(pl)
        res["formato"] = formato
        os.makedirs(cdir, exist_ok=True)
        _tmp = fp + ".tmp"
        json.dump(res, open(_tmp, "w", encoding="utf-8"), ensure_ascii=False)
        os.replace(_tmp, fp)
    except Exception:
        pass


@app.get("/api/plantilla/deteccion_todas")
def plantilla_deteccion_todas():
    """TODAS las piezas de TODAS las variantes en un solo lienzo, para AGRUPAR por selección.

    El gesto que pidió el usuario es el mismo del nombrado: ver todo junto, seleccionar «esto,
    esto y esto son el Frente» y escribirlo. Para eso el visor necesita las piezas de todos los
    talles a la vez, cosa que `/api/plantilla/deteccion` (una capa) no puede dar.

    Devuelve además `formato` (`extendido` / `anidado`): en un molde ANIDADO los talles están
    dibujados uno encima del otro y esta vista es ilegible → el front cae al flujo de a un talle."""
    pid = _get_active_producto_id()
    pl = _ruta_entrada("plantilla.ai", pid)
    if not os.path.exists(pl):
        return jsonify({"error": "primero subí el molde"}), 409
    try:
        mt = int(os.path.getmtime(pl))
    except OSError:
        mt = 0
    # Es CARO (una extracción por talle: ~3 s con 6 talles) y la geometría no cambia si no
    # cambia el archivo → caché en disco con el mtime en la clave, igual que la detección normal.
    cdir = _ruta_datos("deteccion_cache", pid)
    fp = os.path.join(cdir, f"{mt}_dv2_TODAS.json")   # dv2 = orden nuevo (entrada 182)
    try:
        return jsonify(_todas_con_nombres(json.load(open(fp, encoding="utf-8")), pid))
    except Exception:
        pass
    # El FORMATO se mira PRIMERO (es barato): en un molde anidado esta vista no se va a usar, y
    # extraer las piezas de los 20 talles para tirarlas es regalar varios segundos por request.
    try:
        import variantes_molde as VM
        formato = VM.analizar(pl).get("formato") or "extendido"
    except Exception:
        formato = "extendido"
    if False:      # ⛔ ANTES se cortaba acá: con un molde ANIDADO se devolvía la lista VACÍA
        # porque "mostrar los talles juntos sería ilegible". Pero es lo que el molde ES: los talles
        # dibujados uno sobre otro, y así los quiere ver el usuario (regla 2026-08-18: mostrar tal
        # cual viene el archivo). Se devuelven las piezas igual; el `formato` sigue informándose por
        # si alguna pantalla quiere avisar.
        res = {"formato": "anidado", "piezas": [], "talles": []}
    else:
        try:
            res = MP.detectar_piezas_todas(pl)
        except Exception as e:
            return jsonify({"error": f"no se pudieron detectar las piezas: {e}"}), 422
        res["formato"] = formato
    try:
        os.makedirs(cdir, exist_ok=True)
        json.dump(res, open(fp, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass
    return jsonify(_todas_con_nombres(res, pid))


def _todas_con_nombres(res, pid):
    """Suma a cada pieza del lienzo TODAS su `name` según el registro. Va FUERA del caché (el
    caché guarda geometría pura): renombrar una pieza se refleja al instante sin invalidar. Sin
    esto, el filtro de una VARIABLE no encuentra sus piezas en este lienzo (matchea por nombre) y
    el visor cae a mostrar un solo talle — el bug de «no se me muestran todos los talles»."""
    try:
        reg = _cargar("registro_producto.json", pid) or {}
        idx2nom = {}
        for nom, por_t in reg.items():
            for t, inf in (por_t or {}).items():
                i = (inf or {}).get("pieza_idx")
                if i is not None:
                    idx2nom[(t, int(i))] = nom
        res = dict(res)
        res["piezas"] = [{**p, "name": idx2nom.get((p.get("talle"), p.get("t_idx")), p.get("name"))}
                         for p in (res.get("piezas") or [])]
    except Exception:
        pass
    return res


_NIDO_CACHE = {}   # clave (path, mtime, reg_mtime) → nido (geometría estable; recalcula si cambia el archivo/registro)

def _nido_clave():
    pl = _ruta_entrada("plantilla.ai")
    _pid_nc = _get_active_producto_id()
    cor_path = _ruta_datos("correspondencia_piezas.json")
    emp_path = _ruta_datos("emparejado_talles.json")
    try:
        # v7 (2026-07-29): el extractor de contornos aprendió a leer los CUADRILÁTEROS («qu»).
        # Los nidos cacheados con v6 se armaron sin las piezas dibujadas sólo con quads (tiras
        # finas: cuellos, tapacosturas) y su clave —mtimes de plantilla y registro— no cambió, así
        # que no se invalidaban solos. Subir la versión es lo que los rehace.
        return ["v8", pl, os.path.getmtime(pl),   # v8: orden de piezas del archivo (entrada 182)
                _reg_rev(_pid_nc),
                os.path.getmtime(cor_path) if os.path.exists(cor_path) else 0,
                os.path.getmtime(emp_path) if os.path.exists(emp_path) else 0]
    except OSError:
        return ["v8", pl, 0, 0, 0, 0]

def _nido_obtener():
    """Devuelve el nido (calculándolo si hace falta) con caché en memoria + DISCO
    (sobrevive reinicios del server: el cálculo recorre todos los talles y es lento)."""
    clave = _nido_clave()
    ck = tuple(clave)
    if ck in _NIDO_CACHE:
        return _NIDO_CACHE[ck]
    cache_path = _ruta_datos("nido_cache.json")
    try:                                          # ¿está en disco con la misma clave?
        d = json.load(open(cache_path, encoding="utf-8"))
        if d.get("clave") == clave and d.get("nido"):
            _NIDO_CACHE[ck] = d["nido"]
            return d["nido"]
    except Exception:
        pass
    reg = _cargar("registro_producto.json")
    if not reg:
        raise LookupError("primero nombrá las piezas (registro vacío)")
    talle_guia = None
    pid = _get_active_producto_id()
    prod = next((p for p in _cargar_catalogo()["productos"] if p["id"] == pid), None)
    if prod and prod.get("variante_guia"):
        talle_guia = prod["variante_guia"]
    nido = MP.nido_piezas(_ruta_entrada("plantilla.ai"), reg, talle_guia=talle_guia,
                          indices=_cargar("correspondencia_piezas.json") or None,
                          emparejado=_emparejado_cfg())
    _NIDO_CACHE[ck] = nido
    try:
        json.dump({"clave": clave, "nido": nido}, open(cache_path, "w", encoding="utf-8"))
    except Exception:
        pass
    return nido

def _nido_con_ids(nido, pid=None):
    """Le agrega a cada pieza del nido su **`pieza_id`** estable.

    Por qué: el front tenía que cruzar el nido con las variables POR NOMBRE, usando el mapa
    id→clave que venía en la detección. Ese mapa se queda viejo apenas se renombra una pieza (la
    detección está cacheada y nadie la vuelve a pedir), y entonces una variable de 8 piezas
    mostraba 3: las únicas cuyo nombre no había cambiado. Con el id adentro del nido el cruce es
    id↔id y no hay nombre que se pueda quedar viejo. El nombre queda sólo para mostrar."""
    if not isinstance(nido, dict) or not nido.get("piezas"):
        return nido
    try:
        _pz = _cargar("piezas.json", pid or _get_active_producto_id()) or {}
        clave2id = {p["clave"]: p["id"] for p in _pz.get("piezas", [])
                    if p.get("clave") and p.get("id") and not p.get("retirada")}
    except Exception:
        return nido
    if not clave2id:
        return nido
    return {**nido, "piezas": [{**p, "pieza_id": clave2id.get(p.get("nombre"))}
                               for p in nido["piezas"]]}


@app.get("/api/plantilla/nido")
def plantilla_nido():
    """Geometría NESTEADA de cada pieza nombrada en TODOS los talles (para acomodar en el visor)."""
    if not os.path.exists(_ruta_entrada("plantilla.ai")):
        return jsonify({"error": "primero subí la plantilla base"}), 409
    try:
        # Los ids se resuelven FUERA del caché del nido: el nido es geometría (caro, se cachea por
        # plantilla+registro) y los ids cambian por su cuenta al renombrar.
        return jsonify(_nido_con_ids(_nido_obtener()))
    except LookupError as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        return jsonify({"error": f"no se pudo armar el nido: {e}"}), 422


@app.get("/api/plantilla/medidas_variantes")
def plantilla_medidas_variantes():
    """Medidas reales (w_cm/h_cm) de CADA pieza en CADA variante, leídas del registro
    (sin re-detectar). Para la visual de referencia «piezas en fila por talle» que muestra
    cómo el diseño debe adaptarse a lo largo de los talles bajo cada modo de plantilla."""
    reg = _cargar("registro_producto.json")
    if not reg:
        return jsonify({"error": "primero registrá el molde"}), 409
    piezas = []
    for nombre, por_talle in reg.items():
        medidas = {t: {"w_cm": info.get("w_cm"), "h_cm": info.get("h_cm")}
                   for t, info in por_talle.items()
                   if info.get("w_cm") is not None and info.get("h_cm") is not None}
        if medidas:
            piezas.append({"nombre": nombre, "medidas": medidas})
    return jsonify({"talles": _orden_var(reg), "piezas": piezas})


@app.get("/api/plantilla/pdf_guia")
def plantilla_pdf_guia():
    """PDF imprimible con el molde de guía + el recuadro de medida y el nombre de cada
    pieza, según el modo elegido en el visor (default / rango / talle)."""
    pl = _ruta_entrada("plantilla.ai")
    if not os.path.exists(pl):
        return jsonify({"error": "primero subí la plantilla base"}), 409
    reg = _cargar("registro_producto.json") or {}
    config = request.args.get("config", "default")
    talle = request.args.get("talle") or None
    rango = [t for t in (request.args.get("rango", "").split(",")) if t]
    # Piezas a incluir (JSON array de claves de registro): solo las de la variante en curso.
    piezas_raw = request.args.get("piezas")
    try:
        piezas_incluir = set(json.loads(piezas_raw)) if piezas_raw else None
    except Exception:
        piezas_incluir = None
    pid = _get_active_producto_id()
    prod = next((p for p in _cargar_catalogo()["productos"] if p["id"] == pid), None)
    referencia = (prod or {}).get("referencia_medida") or "alto"
    titulo = (prod or {}).get("nombre") or "Molde"
    # En 'rango' la guía la elige el usuario DENTRO del rango; en el resto, la guía del molde.
    talle_guia = request.args.get("guia") or (prod or {}).get("variante_guia") or None
    limpio = request.args.get("limpio") in ("1", "true", "True")   # BASE: solo contornos, sin recuadro/nombre/medidas
    from flask import Response
    # GUÍA en .ai NATIVO (capas reales en Illustrator): `formato=ai`. Trae las capas del arte
    # (diseño, guias, número…) creadas. El PDF sigue disponible para "Descargar base" (limpio).
    if request.args.get("formato") == "ai":
        capas_raw = request.args.get("capas")
        try:
            capas = json.loads(capas_raw) if capas_raw else None
            if capas and not isinstance(capas, list):
                capas = None
        except Exception:
            capas = None
        try:
            ai = MP.ai_guia_medidas(pl, reg, config=config, rango=rango, referencia=referencia,
                                    titulo=titulo, talle_guia=talle_guia,
                                    piezas_incluir=piezas_incluir, capas=capas)
        except Exception as e:
            return jsonify({"error": f"no se pudo generar el .ai: {e}"}), 422
        _slug = "".join(ch if (ch.isalnum() or ch in "._-") else "_" for ch in (titulo or "guia")).strip("_") or "guia"
        return Response(ai, mimetype="application/postscript",
                        headers={"Content-Disposition": f'attachment; filename="guia_{_slug}.ai"'})
    try:
        pdf = MP.pdf_guia_medidas(pl, reg, config=config, talle=talle, rango=rango,
                                  referencia=referencia, titulo=titulo, talle_guia=talle_guia,
                                  piezas_incluir=piezas_incluir, limpio=limpio)
    except Exception as e:
        return jsonify({"error": f"no se pudo generar el PDF: {e}"}), 422
    fname = "base_molde.pdf" if limpio else "guia_medidas.pdf"
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})




def _ajustar_variante_guia(pid, talles):
    """La VARIANTE DE GUÍA tiene que ser una que exista. Al nombrar las variantes, la guía seguía
    apuntando al nombre viejo de la capa («Capa 1»), que ya no existe: la pantalla mostraba esa
    capa como guía y la detección trabajaba sobre una variante inexistente."""
    if not talles:
        return
    cat = _cargar_catalogo_para_editar()
    prod = next((x for x in cat.get("productos", []) if x.get("id") == pid), None)
    if prod is None:
        return
    if prod.get("variante_guia") in talles:
        return
    prod["variante_guia"] = talles[0]
    _guardar_catalogo(cat)
    return prod["variante_guia"]


def _talles_reales(pid=None):
    """Las variantes que el molde YA tiene RESUELTAS, en el orden del archivo.

    Existe porque el estado del molde NO se puede leer de la detección que el visor esté
    mostrando: la vista de «asignar variantes por piezas» (`?candidatas=1`) lee el archivo
    ORIGINAL, donde sigue habiendo una sola capa «Capa 1» para siempre. Tomando el talle de guía
    y el «falta nombrar variantes» de ahí, un molde ya terminado se mostraba como recién subido.

    Sale de los JSON (registro + resumen) y no del PDF a propósito: `_talles_de_plantilla` hace un
    `get_drawings()` de todo el molde (~segundos) y esto se consulta en cada detección."""
    reg = _cargar("registro_producto.json", pid) or {}
    del_reg = {t for v in reg.values() for t in (v or {}).keys() if t}
    if not del_reg:
        return []
    orden = (_cargar("resumen_plantilla.json", pid) or {}).get("talles") or []
    return [t for t in orden if t in del_reg] + sorted(del_reg - set(orden))


def _deteccion_pendiente():
    """Misma FORMA que una detección normal pero vacía: el front la consume sin casos especiales."""
    return {"mesa": None, "talle_ref": None, "talles": [], "unidad": "mm", "img_w": 0, "img_h": 0,
            "piezas": [], "falta_nombrar_variantes": True,
            "aviso": "Falta nombrar las variantes del molde: sin eso no se pueden "
                     "detectar las piezas."}


def _falta_nombrar_variantes(pid=None):
    """¿El molde todavía no tiene NINGÚN talle reconocido? Pasa cuando el archivo viene con las
    capas sin nombrar (o con todo en «Capa 1»). NO es un error: es un paso pendiente del alta, y
    tratarlo como error dejaba la pantalla vacía y la consola llena de 422 en rojo."""
    try:
        import fitz
        pl = _ruta_entrada("plantilla.ai", pid)
        if not os.path.exists(pl):
            return False
        d = fitz.open(pl)
        try:
            return not MP._talles_de_plantilla(d)
        finally:
            d.close()
    except Exception:
        return False


@app.get("/api/productos/<pid>/preview")
def producto_preview(pid):
    """Miniatura VECTORIAL del molde (siluetas de las piezas) para las tarjetas
    del Pedido. Liviano: solo los contornos, sin imagen rasterizada."""
    pl = _ruta_entrada("plantilla.ai", pid)
    if not os.path.exists(pl):
        return jsonify({"error": "sin molde"}), 404
    prod = next((p for p in _cargar_catalogo()["productos"] if p["id"] == pid), None)
    talle_ref = (prod or {}).get("variante_guia")
    try:
        res = MP.detectar_piezas(pl, talle_ref=talle_ref)
    except Exception:
        try:
            res = MP.detectar_piezas(pl, talle_ref=None)
        except Exception as e:
            # Molde recién subido al que le falta nombrar las variantes: es un PASO PENDIENTE, no
            # un error. Se devuelve 200 con la miniatura vacía y el estado, así la tarjeta se
            # dibuja "en preparación" en vez de tirar 422 en la consola.
            if _falta_nombrar_variantes(pid):
                return jsonify({"img_w": 0, "img_h": 0, "piezas": [],
                                "falta_nombrar_variantes": True})
            return jsonify({"error": str(e)}), 422
    return jsonify({"img_w": res.get("img_w"), "img_h": res.get("img_h"),
                    "piezas": [{"idx": p.get("idx"), "px": p.get("px"), "py": p.get("py"),
                                "pw": p.get("pw"), "ph": p.get("ph"), "path_svg": p.get("path_svg")}
                               for p in res.get("piezas", []) if p.get("path_svg")]})


def _puente_idx(reg, desde, hacia):
    """{pieza_idx en el talle `desde`: pieza_idx en el talle `hacia`}, sacado del registro."""
    puente = {}
    for _por_t in (reg or {}).values():
        _d = (_por_t or {}).get(desde) or {}
        _h = (_por_t or {}).get(hacia) or {}
        if _d.get("pieza_idx") is not None and _h.get("pieza_idx") is not None:
            puente[int(_d["pieza_idx"])] = int(_h["pieza_idx"])
    return puente


def _asign_a_guia(reg, asign, talle_visto, guia):
    """Traduce `[{idx,nombre}]` del talle QUE SE ESTABA MIRANDO a los índices del talle GUÍA.

    Devuelve `(traducidas, sin_traducir)`. `sin_traducir` son piezas que el usuario nombró en
    otro talle y que todavía no están en el registro: no hay puente posible, hay que emparejarlas
    por forma (lo hace el llamador con `alta_plantilla_manual`)."""
    if not talle_visto or not guia or talle_visto == guia:
        return list(asign or []), []
    puente = _puente_idx(reg, talle_visto, guia)
    trad, sin = [], []
    for a in (asign or []):
        _i = puente.get(int(a["idx"]))
        if _i is None:
            sin.append(a)
        else:
            trad.append({"idx": _i, "nombre": a.get("nombre")})
    return trad, sin


def _merge_asignaciones(base, encima):
    """`base` = lo YA nombrado en la guía; `encima` = lo que mandó la pantalla.

    Lo que NO vino en la pantalla **no se toca**; antes se borraba, y ese era el bug: la pantalla
    manda sólo las piezas del talle que se está mirando, así que nombrar desde un talle donde una
    pieza no aparece la BORRABA del registro. Quitar un nombre sigue siendo posible porque el
    front manda el idx con el nombre en blanco (eso sí pisa)."""
    m = {int(a["idx"]): (a.get("nombre") or "") for a in (base or [])}
    for a in (encima or []):
        m[int(a["idx"])] = (a.get("nombre") or "")
    return [{"idx": i, "nombre": n} for i, n in sorted(m.items()) if n.strip()]


@app.post("/api/plantilla/etiquetas")
def plantilla_etiquetas():
    """Recibe los nombres puestos a mano en el talle que se está mirando y arma el
    registro propagándolos a todos los talles por posición.

    ⚠️ El registro se re-arma SIEMPRE desde el talle GUÍA, con el nombrado de la guía mergeado
    (ver `_merge_asignaciones`). Tomar el talle visto como referencia hacía dos daños: cambiaba el
    marco en el que se resuelve el emparejado, y perdía todo nombre cuya pieza no existiera en ese
    talle."""
    cuerpo = request.get_json(force=True)
    asign = cuerpo.get("asignaciones", [])
    mesa, talle_ref = cuerpo.get("mesa"), cuerpo.get("talle_ref")
    pl = _ruta_entrada("plantilla.ai")
    if not os.path.exists(pl):
        return jsonify({"error": "primero subí la plantilla base"}), 409
    _indices = _cargar("correspondencia_piezas.json") or None
    _emp = _emparejado_cfg()
    _pid = _get_active_producto_id()
    _reg = _cargar("registro_producto.json", _pid) or {}
    _prod = next((p for p in _cargar_catalogo()["productos"] if p["id"] == _pid), None)
    _guia = (_prod or {}).get("variante_guia")
    if not _guia and _reg:
        # Sin guía elegida a mano la detección la resuelve sola; hay que abrir el PDF para saberla.
        try:
            _guia = _guia_y_asignaciones(_pid)[3]
        except Exception:
            _guia = None
    # El nombrado que YA existe en la guía, acotado a la MESA que mandó la pantalla: con otra mesa
    # los índices no son comparables y mezclarlos escribiría piezas equivocadas.
    _asign_base = [{"idx": int(_i["pieza_idx"]), "nombre": _nom}
                   for _nom, _por_t in _reg.items()
                   for _i in [(_por_t or {}).get(_guia) or {}]
                   if _i.get("pieza_idx") is not None and _i.get("mesa") == mesa]
    if _guia:
        _trad, _sin = _asign_a_guia(_reg, asign, talle_ref, _guia)
        if _sin:
            # Piezas nombradas en otro talle que el registro todavía no conoce: no hay puente, se
            # las empareja por forma desde el talle visto y se lee dónde caen en la guía.
            try:
                _n = MP.alta_plantilla_manual(pl, _sin, mesa, talle_ref, indices=_indices, emparejado=_emp)
                for _nom, _por_t in (_n.get("registro") or {}).items():
                    _g = (_por_t or {}).get(_guia) or {}
                    if _g.get("pieza_idx") is not None:
                        _trad.append({"idx": int(_g["pieza_idx"]), "nombre": _nom})
            except Exception as e:
                print(f"[etiquetas] no se pudieron llevar a la guía las piezas nuevas: {e}")
        asign, talle_ref = _merge_asignaciones(_asign_base, _trad), _guia
    # «Cargar sin esos talles»: el front reenvía la misma llamada con los talles que el usuario
    # decidió dejar afuera en la ventana de piezas faltantes (changelog 179).
    _excluir = (request.get_json(silent=True) or {}).get("excluir_talles") or []
    alta = MP.alta_plantilla_manual(pl, asign, mesa, talle_ref, indices=_indices, emparejado=_emp,
                                    excluir_talles=_excluir)
    if not alta["registro"]:
        return jsonify({"error": "; ".join(alta["problemas"]) or "no se registró ninguna pieza"}), 422
        _guardar_registro(_get_active_producto_id(), alta["registro"])
    resumen = {"archivo": (_cargar("resumen_plantilla.json") or {}).get("archivo", "plantilla.ai"),
               "mesas": alta["mesas"], "piezas": alta["piezas"], "talles": alta["talles"],
               "completitud": f"{len(alta['completos'])}/{len(alta['talles'])} talles completos",
               "problemas": alta["problemas"], "advertencias": alta["advertencias"],
               "piezas_detalle": alta["piezas_detalle"], "metodo": "etiquetado visual",
               # Para la ventana de «a estos talles les faltan estas piezas» (changelog 179).
               # No traba: el alta ya se hizo con lo que cada talle tiene; el usuario decide si
               # rehace la carga excluyendo los incompletos o si sube el archivo de nuevo.
               "faltantes_por_talle": alta.get("faltantes_por_talle") or {},
               "sobrantes_por_talle": alta.get("sobrantes_por_talle") or {},
               "excluidos": alta.get("excluidos") or []}
    json.dump(resumen, open(_ruta_datos("resumen_plantilla.json"), "w", encoding="utf-8"), ensure_ascii=False)
    return jsonify(resumen)


# ── EMPAREJADO ENTRE TALLES: reacomodar a mano + corregir la pieza homóloga ────────────
def _guia_y_asignaciones(pid=None):
    """(det, mesa, talle_guía, [{idx,nombre}], registro) del molde activo.

    Los nombres NO se vuelven a pedir: se releen del registro en el talle guía, que es
    exactamente la entrada de `alta_plantilla_manual`. Así re-propagar el nombrado con el
    ajuste nuevo es idempotente (misma guía, mismos nombres, otro emparejado)."""
    pid = pid or _get_active_producto_id()
    pl = _ruta_entrada("plantilla.ai", pid)
    prod = next((p for p in _cargar_catalogo()["productos"] if p["id"] == pid), None)
    det = MP.detectar_piezas(pl, talle_ref=(prod or {}).get("variante_guia") or None)
    mesa, guia = det["mesa"], det["talle_ref"]
    reg = _cargar("registro_producto.json", pid) or {}
    asign = []
    for nom, por_t in reg.items():
        inf = (por_t or {}).get(guia) or {}
        if inf.get("mesa") == mesa and inf.get("pieza_idx") is not None:
            asign.append({"idx": int(inf["pieza_idx"]), "nombre": nom})
    return pl, det, mesa, guia, asign, reg


def _asignacion_actual(reg, mesa):
    """{talle: {nombre_pieza: pieza_idx}} tal como quedó el registro — es lo que la UI
    muestra para poder decir «esta pieza en el talle X está mal, es la otra»."""
    out = {}
    for nom, por_t in (reg or {}).items():
        for t, inf in (por_t or {}).items():
            if (inf or {}).get("mesa") == mesa and inf.get("pieza_idx") is not None:
                out.setdefault(t, {})[nom] = int(inf["pieza_idx"])
    return out


def _guardar_y_repropagar(pid, cfg, asign=None):
    """Persiste el ajuste del emparejado y RE-ARMA el registro con él.

    Guardar sin re-armar no sirve: el emparejado se resuelve al CONSTRUIR el registro.
    `asign` = nombrado del talle guía a usar ([{idx,nombre}]); si no viene se relee del
    registro (re-propagar es idempotente). Devuelve la respuesta Flask ya lista."""
    json.dump(cfg, open(_ruta_datos("emparejado_talles.json", pid), "w", encoding="utf-8"),
              ensure_ascii=False)
    try:
        pl, det, mesa, guia, asign_reg, _reg = _guia_y_asignaciones(pid)
    except Exception as e:
        return jsonify({"error": f"no se pudo leer el molde: {e}"}), 422
    if asign is None:
        asign = asign_reg
    if not asign:
        # Sin nombres todavía no hay nada que propagar, pero el ajuste queda guardado
        # y se va a aplicar solo la primera vez que se nombren las piezas.
        return jsonify({"ok": True, "guia": guia, "talles": det.get("talles") or [],
                        "nombres_guia": {}, "asignacion": {},
                        "acomodo": cfg["acomodo"], "manual": cfg["manual"],
                        "aviso": "todavía no hay piezas nombradas: el ajuste queda guardado"})
    alta = MP.alta_plantilla_manual(pl, asign, mesa, guia,
                                    indices=_cargar("correspondencia_piezas.json", pid) or None,
                                    emparejado=cfg)
    if not alta.get("registro"):
        return jsonify({"error": "; ".join(alta.get("problemas") or []) or "no se registró ninguna pieza"}), 422
    _guardar_registro(pid, alta["registro"])
    _res = _cargar("resumen_plantilla.json", pid) or {}
    _res.update({"mesas": alta["mesas"], "piezas": alta["piezas"], "talles": alta["talles"],
                 "completitud": f"{len(alta['completos'])}/{len(alta['talles'])} talles completos",
                 "problemas": alta["problemas"], "advertencias": alta["advertencias"],
                 "piezas_detalle": alta["piezas_detalle"]})
    json.dump(_res, open(_ruta_datos("resumen_plantilla.json", pid), "w", encoding="utf-8"),
              ensure_ascii=False)
    return jsonify({"ok": True, "guia": guia, "talles": alta["talles"],
                    "nombres_guia": {str(i): n for i, n in
                                     MP.nombres_normalizados(asign).items()},
                    "asignacion": _asignacion_actual(alta["registro"], mesa),
                    "completitud": f"{len(alta['completos'])}/{len(alta['talles'])} talles completos",
                    "acomodo": cfg["acomodo"], "manual": cfg["manual"]})


@app.get("/api/plantilla/emparejado")
def plantilla_emparejado_get():
    """Estado del emparejado entre talles: guía, talles, qué pieza le tocó a cada nombre
    en cada talle, y el ajuste a mano guardado (acomodo + correcciones)."""
    pid = _get_active_producto_id()
    if not os.path.exists(_ruta_entrada("plantilla.ai", pid)):
        return jsonify({"error": "primero subí el molde"}), 409
    try:
        _pl, det, mesa, guia, asign, reg = _guia_y_asignaciones(pid)
    except Exception as e:
        return jsonify({"error": f"no se pudo leer el molde: {e}"}), 422
    cfg = _emparejado_cfg(pid)
    return jsonify({"guia": guia, "mesa": mesa, "talles": det.get("talles") or [],
                    "nombres_guia": {str(a["idx"]): a["nombre"] for a in asign},
                    "asignacion": _asignacion_actual(reg, mesa),
                    "acomodo": cfg["acomodo"], "manual": cfg["manual"]})


@app.post("/api/plantilla/emparejado")
def plantilla_emparejado_post():
    """Guarda el ajuste a mano del emparejado y RE-PROPAGA el nombrado con él.

    Body: `{pid?, talle, acomodo?: {idx:[dx_mm,dy_mm]}, manual?: {nombre: idx|null},
             reset?: 'acomodo'|'manual'|'todo'}`. Sin `talle` se aceptan los diccionarios
    completos `{talle: {...}}`. Guardar SIN re-armar el registro no serviría de nada: el
    emparejado se resuelve al construirlo, así que acá mismo se rehace."""
    cuerpo = request.get_json(force=True) or {}
    pid = _get_active_producto_id()
    if not os.path.exists(_ruta_entrada("plantilla.ai", pid)):
        return jsonify({"error": "primero subí el molde"}), 409
    cfg = _emparejado_cfg(pid)
    talle = cuerpo.get("talle")
    reset = cuerpo.get("reset")
    if reset in ("acomodo", "todo"):
        if talle:
            cfg["acomodo"].pop(talle, None)
        else:
            cfg["acomodo"] = {}
    if reset in ("manual", "todo"):
        if talle:
            cfg["manual"].pop(talle, None)
        else:
            cfg["manual"] = {}
    if talle:
        if "acomodo" in cuerpo:
            ac = {str(k): [float(v[0]), float(v[1])] for k, v in (cuerpo.get("acomodo") or {}).items()
                  if v and (abs(float(v[0])) > 0.01 or abs(float(v[1])) > 0.01)}
            if ac:
                cfg["acomodo"][talle] = ac
            else:
                cfg["acomodo"].pop(talle, None)
        for nom, idx in (cuerpo.get("manual") or {}).items():
            d = cfg["manual"].setdefault(talle, {})
            if idx is None:
                d.pop(nom, None)          # quitar la corrección → vuelve a mandar la heurística
            else:
                d[nom] = int(idx)
            if not d:
                cfg["manual"].pop(talle, None)
    else:
        if isinstance(cuerpo.get("acomodo"), dict):
            cfg["acomodo"] = cuerpo["acomodo"]
        if isinstance(cuerpo.get("manual"), dict):
            cfg["manual"] = cuerpo["manual"]

    return _guardar_y_repropagar(pid, cfg)


def _prod_de(pid):
    return next((p for p in _cargar_catalogo()["productos"] if p["id"] == pid), None)


@app.post("/api/plantilla/pieza_archivo")
def plantilla_pieza_archivo():
    """Guarda el archivo de la pieza que se va a agregar (paso previo a `pieza_agregar`).

    Va a un nombre fijo (`pieza_nueva.ai`) y NO toca el molde: recién `pieza_agregar` lo lee y
    escribe la geometría. Así, si el alta falla, el molde queda exactamente como estaba."""
    pid = _pid_de_request() or _get_active_producto_id()
    _no = _guard_molde(pid, "molde.editar")
    if _no: return _no
    f = request.files.get("archivo")
    if not f or not f.filename:
        return jsonify({"error": "no llegó ningún archivo"}), 400
    if not f.filename.lower().endswith((".ai", ".pdf")):
        return jsonify({"error": "la pieza tiene que ser .ai o .pdf"}), 400
    destino = _ruta_entrada("pieza_nueva.ai", pid, original=True)
    f.save(destino)
    try:
        conts = PM.contornos_de_pdf(destino)
    except Exception as e:
        return jsonify({"error": f"no se pudo leer el archivo: {e}"}), 422
    if not conts:
        return jsonify({"error": "el archivo no tiene ningún contorno dibujado"}), 422
    # Se avisa ACÁ si no trae todos los talles, para no dejar que marque el lugar y recién ahí fallar.
    _n_talles = 0
    try:
        pl = _ruta_entrada("plantilla.ai", pid)
        if os.path.exists(pl):
            d = MP._abrir(pl)
            try:
                _n_talles = len(MP._talles_de_plantilla(d))
            finally:
                d.close()
    except Exception:
        pass
    c = conts[0]
    return jsonify({"ok": True, "contornos": len(conts), "talles": _n_talles,
                    "completo": (not _n_talles) or len(conts) >= _n_talles,
                    "w_cm": round(c["w"] / MP.CM, 1), "h_cm": round(c["h"] / MP.CM, 1)})


def _invalidar_cache_molde(pid):
    """Tira TODO lo derivado del molde: cambió su geometría.

    Son cachés (se rehacen solas) pero ninguna se invalida por su cuenta acá: la de detección va
    por mtime del archivo —y el archivo nuevo es OTRO, el versionado—, y la del nido por una clave
    que mira la plantilla base. Si no se limpian, el visor sigue mostrando el molde de antes."""
    import shutil as _sh
    for sub in ("deteccion_cache", "piezas_cache"):
        try:
            _sh.rmtree(_ruta_datos(sub, pid), ignore_errors=True)
        except Exception:
            pass
    try:
        os.remove(_ruta_datos("nido_cache.json", pid))
    except OSError:
        pass
    _NIDO_CACHE.clear()
    _TOGGLES_CACHE.pop(pid, None)


@app.post("/api/plantilla/pieza_agregar")
def plantilla_pieza_agregar():
    """Agrega una PIEZA NUEVA al molde, en el lugar del lienzo que se indique.

    Cuerpo: `{pid?, origen: "duplicar"|"archivo", pieza_idx?, dx, dy, nombre?}`
      · `duplicar`: copia la pieza `pieza_idx` (índice en el talle GUÍA). En cada talle se copia la
        geometría DE ESE TALLE → la pieza nueva acompaña la progresión de talles como cualquier otra.
      · `archivo`: usa el contorno más grande del PDF/AI subido antes a `entrada/<pid>/pieza_nueva.ai`.
        Va IGUAL en todos los talles (un archivo suelto no tiene progresión).
    `dx`/`dy` = desplazamiento respecto de la pieza copiada, en MILÍMETROS.

    ⚠️ Entra en TODOS los talles a propósito: una pieza que exista sólo en algunos deja el registro
    con un hueco y **la generación explota** (`registro[pieza][talle]` no tiene guarda en el motor).
    ⚠️ Y después del alta se REMAPEA el registro: el `pieza_idx` es la posición en el orden por bbox,
    así que insertar una pieza corre a todas las que siguen (medido: 1478 de 2760 entradas)."""
    cuerpo = request.get_json(force=True) or {}
    pid = _pid_de_request() or _get_active_producto_id()
    _no = _guard_molde(pid, "molde.editar")
    if _no: return _no
    # 🔴 DOS RUTAS DISTINTAS, Y NO SE PUEDEN CONFUNDIR:
    #   · `pl_base` = `plantilla.ai` SIEMPRE (el original). Es sobre ÉL que se versiona.
    #   · `pl`      = la versión VIGENTE. Es de ella que se lee la geometría de ahora.
    # `_ruta_entrada` devuelve la VIGENTE, así que pasarle esa a `agregar_pieza` versionaba lo ya
    # versionado: la 2ª pieza generaba `plantilla.v1.v1.ai` + `plantilla.v1.ver`, y como el puntero
    # bueno (`plantilla.ver`) seguía en 1, **la 2ª pieza quedaba huérfana**: el sistema seguía
    # sirviendo el archivo con una sola. Pasó en el molde del usuario.
    pl_base = _ruta_entrada("plantilla.ai", pid, original=True)
    pl = OA.ruta_vigente(pl_base)
    if not os.path.exists(pl):
        return jsonify({"error": "primero subí el molde"}), 409
    reg = _cargar("registro_producto.json", pid) or {}
    try:
        doc = MP._abrir(pl)
        try:
            talles = MP._talles_de_plantilla(doc)
            det = MP.detectar_piezas(pl, talle_ref=(_prod_de(pid) or {}).get("variante_guia") or None)
        finally:
            doc.close()
        mesa, guia = det["mesa"], det["talle_ref"]
        if not talles:
            return jsonify({"error": "el molde no tiene talles"}), 422
        antes = PM.detectar_por_talle(pl, mesa, talles)
        firmas_antes = {t: PM.firma_contornos(cs) for t, cs in antes.items()}
        # ── UNIDADES ──────────────────────────────────────────────────────────────────────────
        # `dx`/`dy` llegan **como se ven en el visor**: milímetros, con la Y para ABAJO (es lo que
        # devuelve un clic sobre el svg, que está dibujado a px = mm). El lienzo del PDF va en
        # unidades crudas con la Y para ARRIBA → se escala (1 mm = CM/10 unidades) y se da vuelta
        # la Y. Verificado sobre el molde real: `CM` = 28.3465 unidades por cm y `user_unit` = 1.
        dx = float(cuerpo.get("dx") or 0) * (MP.CM / 10.0)
        dy = -float(cuerpo.get("dy") or 0) * (MP.CM / 10.0)
        origen = str(cuerpo.get("origen") or "duplicar")
        colocaciones = {}
        if origen == "duplicar":
            i = cuerpo.get("pieza_idx")
            if i is None:
                return jsonify({"error": "falta indicar qué pieza duplicar"}), 400
            i = int(i)
            # el idx viene del talle GUÍA; en cada talle se toma SU pieza del mismo índice
            for t in talles:
                cs = antes.get(t) or []
                if i < len(cs):
                    colocaciones[t] = {"segmentos": cs[i]["segmentos"], "dx": dx, "dy": dy}
            if guia not in colocaciones:
                return jsonify({"error": "esa pieza no existe en el talle guía"}), 422
        else:
            _f = _ruta_entrada("pieza_nueva.ai", pid)
            if not os.path.exists(_f):
                return jsonify({"error": "primero subí el archivo de la pieza"}), 409
            conts = PM.contornos_de_pdf(_f)
            # 🔴 EL ARCHIVO TIENE QUE TRAER LA PIEZA EN TODOS LOS TALLES. Una pieza de moldería
            # cambia de forma con el talle: meter la MISMA forma en los 20 sería una pieza que no
            # escala, y saldría mal cortada en todos menos uno. Y si entrara sólo en algunos, el
            # registro queda con un hueco y la generación explota. Por eso se rechaza.
            if len(conts) < len(talles):
                return jsonify({"error": f"el archivo trae {len(conts)} contorno/s y el molde tiene "
                                         f"{len(talles)} {('talles' if len(talles) != 1 else 'talle')}. "
                                         f"La pieza tiene que venir dibujada en todos los talles, una "
                                         f"forma por talle (del más chico al más grande).",
                                "contornos": len(conts), "talles": len(talles)}), 422
            # De menor a mayor área ↔ los talles en el orden del molde (que va del más chico al más
            # grande). Si sobran contornos se usan los N más grandes.
            _orden = sorted(conts[:len(talles)], key=lambda c: c["w"] * c["h"])
            _ref = (antes.get(guia) or [{}])[0].get("bbox_raw") if antes.get(guia) else None
            _base0 = _orden[0]["bbox_raw"]
            for _i, t in enumerate(talles):
                _c = _orden[_i]
                # cada talle conserva su posición RELATIVA dentro del archivo (si vienen anidados,
                # la pila queda como el usuario la dibujó); el conjunto se lleva al lugar marcado.
                _dx = dx - _base0[0] + (_ref[0] if _ref else 0)
                _dy = dy - _base0[1] + (_ref[1] if _ref else 0)
                colocaciones[t] = {"segmentos": _c["segmentos"], "dx": _dx, "dy": _dy}
        # ── DÓNDE VA A CAER EN LA NUMERACIÓN (antes de escribir) ──────────────────────────────
        # El orden de las piezas es por (x0, y0), así que la posición de la nueva se CALCULA: no
        # hace falta volver a detectar los 20 talles después de escribir (era la mitad del tiempo).
        _ks = {}
        for t, col in colocaciones.items():
            _bb = PM.bbox_desplazado(col["segmentos"], col["dx"], col["dy"], antes[t])
            _ks[t] = PM.indice_de_insercion(antes[t], _bb)
        destino, puestos = PM.agregar_pieza(pl_base, colocaciones, mesa=mesa)   # ← la BASE, no la vigente
        # ── REMAPEO: sin esto el registro apunta a la pieza vecina ─────────────────────────────
        mapas = {t: PM.mapa_insercion(len(antes[t]), _ks.get(t, len(antes[t]))) for t in talles}
        reg2, cambios, avisos = PM.remapear_registro(reg, mapas)
        if reg:
            # RESPALDO ANTES DE PISAR. El archivo del molde se versiona solo, pero el registro se
            # sobreescribe: sin esta copia, agregar una pieza era un camino de ida (no se podía
            # volver a los `pieza_idx` de antes). Es lo que hace posible «Deshacer».
            _rp = _ruta_datos("registro_producto.json", pid)
            try:
                import shutil as _sh
                _sh.copy(_rp, _rp + ".antes_pieza")
            except Exception as e:
                print(f"[pieza_agregar] no se pudo respaldar el registro: {e}")
            json.dump(reg2, open(_rp, "w", encoding="utf-8"), ensure_ascii=False)
            try:
                _regenerar_piezas_index(pid, reg=reg2)
            except Exception as e:
                print(f"[pieza_agregar] no se pudo refrescar piezas.json: {e}")
        _invalidar_cache_molde(pid)
        _nueva_idx = {t: [j for j in range(len(despues[t])) if j not in set(mapas[t].values())]
                      for t in talles}
        return jsonify({"ok": True, "talles": len(puestos), "version": os.path.basename(destino),
                        "piezas_remapeadas": cambios, "avisos": avisos[:10],
                        "pieza_idx_nueva": (_nueva_idx.get(guia) or [None])[0],
                        "sin_nombre": True})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"no se pudo agregar la pieza: {e}"}), 422


@app.post("/api/plantilla/pieza_deshacer")
def plantilla_pieza_deshacer():
    """Saca la ÚLTIMA pieza agregada: vuelve el molde a su versión anterior y el registro con él.

    El archivo se revierte moviendo el puntero de versión (el original nunca se tocó). El registro
    se restaura del respaldo `.antes_pieza`; si ese respaldo no está —altas hechas antes de que
    existiera— se **reconstruye** el mapa inverso comparando las dos versiones del molde, que es
    determinista: la pieza que sobra en la nueva dice en qué posición se insertó, y todo lo que va
    de ahí en adelante vuelve un lugar atrás."""
    pid = _pid_de_request() or _get_active_producto_id()
    _no = _guard_molde(pid, "molde.editar")
    if _no: return _no
    pl = _ruta_entrada("plantilla.ai", pid, original=True)
    n = OA._ver_actual(pl)
    if n <= 0:
        return jsonify({"error": "el molde no tiene ninguna pieza agregada para sacar"}), 409
    try:
        vig = OA.ruta_vigente(pl)
        prev = OA._ver_path(pl, n - 1) if n > 1 else pl
        if not os.path.exists(prev):
            return jsonify({"error": "no está la versión anterior del molde"}), 409
        _rp = _ruta_datos("registro_producto.json", pid)
        _bak = _rp + ".antes_pieza"
        if os.path.exists(_bak):
            import shutil as _sh
            _sh.copy(_bak, _rp)
            os.remove(_bak)
        else:
            # Sin respaldo: se reconstruye el inverso comparando las dos versiones.
            d = MP._abrir(prev)
            try:
                talles = MP._talles_de_plantilla(d)
                mesa = MP.detectar_piezas(prev, talle_ref=(_prod_de(pid) or {}).get("variante_guia") or None)["mesa"]
            finally:
                d.close()
            a = PM.detectar_por_talle(prev, mesa, talles)
            b = PM.detectar_por_talle(vig, mesa, talles)
            inv = {}
            for t in talles:
                fa = set(PM.firma_contornos(a[t]))
                k = next((i for i, c in enumerate(b[t])
                          if tuple(round(float(v), 1) for v in c["bbox_raw"]) not in fa), len(a[t]))
                # inverso de `mapa_insercion`: lo que estaba después de k vuelve un lugar atrás
                inv[t] = {j: (j if j < k else j - 1) for j in range(len(b[t])) if j != k}
            reg = _cargar("registro_producto.json", pid) or {}
            reg2, _c, _av = PM.remapear_registro(reg, inv)
            json.dump(reg2, open(_rp, "w", encoding="utf-8"), ensure_ascii=False)
        OA.fijar_version(pl, n - 1)
        try:
            os.remove(vig)
        except OSError:
            pass
        try:
            _regenerar_piezas_index(pid)
        except Exception as e:
            print(f"[pieza_deshacer] no se pudo refrescar piezas.json: {e}")
        _invalidar_cache_molde(pid)
        return jsonify({"ok": True, "version": n - 1})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"no se pudo deshacer: {e}"}), 422


def _migrar_nombres_pieza(pid, ren):
    """Un renombre de pieza (explicito, o el IMPLICITO del desambiguado «Frente»→«Frente 1» al
    aceptar nombres repetidos) ARRASTRA todas las configs que cuelgan del nombre: etiqueta
    (posiciones por pieza), telas por pieza y mapeo del arte (fijo del producto + por diseño).
    El emparejado manual ya migra en el caller. Sin esto la config quedaba huérfana bajo el
    nombre viejo y el molde «perdía» su etiqueta/tela/mapeo al renombrar."""
    if not ren:
        return

    def _mueve(d):
        if not isinstance(d, dict):
            return d, False
        out, tocado = {}, False
        for k, v in d.items():
            k2 = ren.get(k, k)
            if k2 != k:
                tocado = True
            if k2 not in out:          # si el nombre nuevo ya tenía algo propio, eso gana
                out[k2] = v
        return out, tocado

    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    cambio = False
    if prod:
        et = prod.get("etiqueta") or {}
        if isinstance(et.get("posiciones"), dict):
            et["posiciones"], _t = _mueve(et["posiciones"]); cambio = cambio or _t
        tc = prod.get("telas_cfg") or {}
        if isinstance(tc.get("por_pieza"), dict):
            tc["por_pieza"], _t = _mueve(tc["por_pieza"]); cambio = cambio or _t
        if isinstance(prod.get("mapeo_arte"), dict):
            prod["mapeo_arte"], _t = _mueve(prod["mapeo_arte"]); cambio = cambio or _t
        # acomodos de las variables (por nombre de pieza): el manual nuevo (mm) y el del nido viejo
        for _v in (prod.get("variantes") or []):
            for _k in ("acomodo_mm", "acomodo"):
                if isinstance(_v.get(_k), dict):
                    _v[_k], _t = _mueve(_v[_k]); cambio = cambio or _t
    if cambio:
        _guardar_catalogo(cat)
    # mapeo por diseño: un mapeo_arte.json por sub-carpeta del producto (+ el de la raíz)
    base = os.path.join(DATOS, "productos", pid)
    try:
        subs = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
    except OSError:
        subs = []
    for sub in subs + [None]:
        ruta = os.path.join(base, sub, "mapeo_arte.json") if sub else os.path.join(base, "mapeo_arte.json")
        if not os.path.exists(ruta):
            continue
        try:
            with open(ruta, encoding="utf-8") as f:
                mp = json.load(f)
        except Exception:
            continue
        tocado = False
        if isinstance(mp.get("mapeo"), dict):
            mp["mapeo"], _t = _mueve(mp["mapeo"]); tocado = tocado or _t
        if isinstance(mp.get("por_variable"), dict):
            for vk in list(mp["por_variable"].keys()):
                mp["por_variable"][vk], _t = _mueve(mp["por_variable"][vk]); tocado = tocado or _t
        if tocado:
            with open(ruta + ".tmp", "w", encoding="utf-8") as f:
                json.dump(mp, f, ensure_ascii=False)
            os.replace(ruta + ".tmp", ruta)


@app.post("/api/plantilla/grupo_pieza")
def plantilla_grupo_pieza():
    """UN SOLO GESTO: «estas piezas son la misma y se llama Frente».

    Body: `{pid?, nombre, guia_idx, piezas?: {talle: idx|null}, renombrar_de?, eliminar?}`.
    En un solo llamado queda definido lo que antes eran dos herramientas distintas:
      · el NOMBRE de la pieza (entra al nombrado del talle guía → registro), y
      · la CORRESPONDENCIA con los otros talles (`piezas`), que se guarda como corrección
        FIJA en `emparejado_talles.json["manual"]` → la heurística no la pisa nunca.
    Lo que el usuario NO confirma queda con la propuesta automática (se distingue en la UI).
    """
    cuerpo = request.get_json(force=True) or {}
    pid = _get_active_producto_id()
    if not os.path.exists(_ruta_entrada("plantilla.ai", pid)):
        return jsonify({"error": "primero subí el molde"}), 409
    try:
        _pl, _det, _mesa, guia, asign, _reg = _guia_y_asignaciones(pid)
    except Exception as e:
        return jsonify({"error": f"no se pudo leer el molde: {e}"}), 422
    cfg = _emparejado_cfg(pid)
    antes = MP.nombres_normalizados(asign)          # {idx: nombre} ANTES de tocar nada

    nombre = (cuerpo.get("nombre") or "").strip()
    eliminar = bool(cuerpo.get("eliminar"))
    if eliminar:
        if not nombre:
            return jsonify({"error": "falta el nombre del grupo a deshacer"}), 400
        asign = [a for a in asign if a["nombre"] != nombre]
    else:
        if not nombre:
            return jsonify({"error": "escribí qué es la pieza (Frente, Espalda, Manga…)"}), 400
        try:
            gi = int(cuerpo.get("guia_idx"))
        except (TypeError, ValueError):
            return jsonify({"error": f"elegí la pieza en {guia} (el talle guía)"}), 400
        viejo = (cuerpo.get("renombrar_de") or "").strip()
        # Los nombres REPETIDOS se aceptan (regla del usuario 2026-08-19: la identidad de la
        # pieza es su id, el nombre es sólo un rótulo — pueden llamarse igual las que sea).
        # La colisión en el registro (dict por nombre) la resuelve `nombres_normalizados`
        # dándole al repetido el primer número libre, sin tocar lo que ya estaba nombrado.
        # Antes acá había un 409 «usá otro nombre» que además rompía el nombrado en cadena
        # (dos piezas distintas nombradas «Frente» en un gesto: la 2ª quedaba bloqueada).
        asign = [a for a in asign if a["idx"] != gi and (not viejo or a["nombre"] != viejo)]
        asign.append({"idx": gi, "nombre": nombre})

    despues = MP.nombres_normalizados(asign)        # {idx: nombre} DESPUÉS
    # Las correcciones fijas se guardan por NOMBRE: si al agregar/quitar una pieza el registro
    # renumeró un genérico («Manga 2» → «Manga»), hay que arrastrar la clave o la corrección
    # queda huérfana y el emparejado a mano se pierde en silencio.
    ren = {antes[i]: despues[i] for i in antes if i in despues and antes[i] != despues[i]}
    if not eliminar and (cuerpo.get("renombrar_de") or "").strip():
        ren.setdefault((cuerpo.get("renombrar_de") or "").strip(), despues.get(int(cuerpo["guia_idx"]), nombre))
    vivos = set(despues.values())
    for t, d in list(cfg["manual"].items()):
        nd = {}
        for nom, idx in d.items():
            nom2 = ren.get(nom, nom)
            if nom2 in vivos:                        # el grupo deshecho se lleva sus fijos
                nd[nom2] = idx
        if nd:
            cfg["manual"][t] = nd
        else:
            cfg["manual"].pop(t, None)

    # El renombre arrastra las configs que cuelgan del nombre (etiqueta/telas/mapeo).
    _migrar_nombres_pieza(pid, ren)

    # Correspondencia confirmada A MANO en los otros talles (lo que manda sobre la heurística).
    nombre_final = despues.get(int(cuerpo.get("guia_idx"))) if not eliminar else None
    for t, idx in (cuerpo.get("piezas") or {}).items():
        if t == guia or not nombre_final:
            continue
        d = cfg["manual"].setdefault(t, {})
        if idx is None:
            d.pop(nombre_final, None)                # soltar → vuelve la propuesta automática
        else:
            d[nombre_final] = int(idx)
        if not d:
            cfg["manual"].pop(t, None)

    return _guardar_y_repropagar(pid, cfg, asign=asign)


@app.get("/api/plantilla/variantes")
def plantilla_variantes():
    """Radiografía del molde para la herramienta de NOMBRAR VARIANTES: qué capas hay, cuáles son
    talles, y la curva propuesta (de menor a mayor por área). Acepta `?pid=`."""
    import variantes_molde as VM
    pl = _ruta_entrada("plantilla.ai")
    if not os.path.exists(pl):
        return jsonify({"error": "primero subí el molde"}), 409
    try:
        info = VM.analizar(pl)
    except Exception as e:
        return jsonify({"error": f"no se pudo leer el molde: {e}"}), 422
    info["sugerencia_nombres"] = VM.curva_sugerida(info["sugerencia"])
    # los talles que YA están nombrados (el registro vigente), para saber si hace falta la herramienta
    reg = _cargar("registro_producto.json") or {}
    info["talles_registrados"] = sorted({t for v in reg.values() for t in (v or {}).keys()})
    # ¿El molde ya está RESUELTO? (tiene registro con variantes). El encabezado del acordeón se
    # calculaba con `sin_talles`, que mira el ARCHIVO: un molde ya terminado seguía anunciando
    # «⚠ Falta nombrar las variantes».
    info["resuelto"] = bool(info["talles_registrados"])
    # MODO de la herramienta (ver §10.c): con 2+ capas de talle candidatas se nombra POR CAPA; con
    # una sola capa que trae TODAS las piezas no hay capas que nombrar → hay que repartir POR
    # PIEZAS. Es una SUGERENCIA: el front deja cambiarlo a mano.
    prev = _cargar("variantes_piezas.json") or {}
    info["modo_sugerido"] = "piezas" if (prev or info.get("total_talles", 0) < 2) else "capas"
    info["asignacion_piezas"] = prev.get("asignaciones") or {}
    # Lo que se APLICÓ de verdad (se partió el archivo). Sin esto no se puede distinguir "lo que
    # el usuario viene armando" de "lo que ya está en el molde", y no hay forma de avisarle que le
    # queda trabajo sin aplicar. Los archivos VIEJOS no tienen `aplicadas`: ahí lo guardado ES lo
    # aplicado (antes sólo se escribía al aplicar), así que no queda nada pendiente.
    info["asignacion_piezas_aplicada"] = (prev.get("aplicadas") if "aplicadas" in prev
                                          else prev.get("asignaciones")) or {}
    info["variantes_piezas"] = prev.get("orden") or []
    return jsonify(info)


@app.post("/api/plantilla/variantes_piezas_borrador")
def plantilla_variantes_piezas_borrador():
    """Guarda el BORRADOR de la asignación pieza→variante, sin tocar el molde.

    Por qué existe aparte de `/api/plantilla/variantes_piezas`: aplicar PARTE el PDF y rehace el
    registro (segundos), así que no se puede hacer en cada clic. Pero el trabajo del usuario
    («estas 6 piezas son la M») se perdía entero si salía sin apretar Aplicar. Esto persiste la
    asignación cruda en cada cambio — barato, sólo escribe un JSON — y el partido queda para
    cuando el usuario termina.
    """
    cuerpo = request.get_json(force=True) or {}
    asign = cuerpo.get("asignaciones") or {}
    pid = _get_active_producto_id()
    prev = _cargar("variantes_piezas.json", pid) or {}
    # Archivo VIEJO (escrito sólo al aplicar): lo que tiene guardado ES lo aplicado. Hay que
    # sembrarlo ANTES de pisar `asignaciones` o el molde ya partido figuraría como pendiente.
    if "aplicadas" not in prev:
        prev["aplicadas"] = prev.get("asignaciones") or {}
    # `mesa`/`capa_origen`/`orden`/`aplicadas` son del último APLICADO: el borrador no los cambia.
    prev["asignaciones"] = {str(k): str(v) for k, v in asign.items() if str(v or "").strip()}
    prev["borrador_ts"] = time.time()
    os.makedirs(os.path.dirname(_ruta_datos("variantes_piezas.json", pid)), exist_ok=True)
    json.dump(prev, open(_ruta_datos("variantes_piezas.json", pid), "w", encoding="utf-8"),
              ensure_ascii=False)
    pendiente = prev["asignaciones"] != (prev.get("aplicadas") or {})
    return jsonify({"ok": True, "asignadas": len(prev["asignaciones"]), "pendiente": pendiente})


@app.post("/api/plantilla/variantes_piezas")
def plantilla_variantes_piezas():
    """Asigna las variantes SELECCIONANDO PIEZAS (molde con todo en una sola capa).

    Body: `{pid?, asignaciones: {pieza_idx: "nombre_variante"}}` con los índices de
    `/api/plantilla/deteccion?candidatas=1`.

    Parte la capa única en una capa (OCG) REAL por variante — escribiendo una VERSIÓN nueva, el
    archivo del usuario queda intacto — y rehace el registro. Sin partir el archivo el molde no
    serviría: todo el sistema resuelve el talle de una pieza por el NOMBRE DE LA CAPA.
    """
    import variantes_molde as VM
    from molde_real import extraer_piezas_mesa
    cuerpo = request.get_json(force=True) or {}
    asign = cuerpo.get("asignaciones") or {}
    pid = _get_active_producto_id()
    pl = _ruta_entrada("plantilla.ai", pid, original=True)
    if not os.path.exists(pl):
        return jsonify({"error": "primero subí el molde"}), 409

    # Los NOMBRES que ya tengan las piezas se recuperan por su bbox: la geometría no cambia al
    # partir el archivo, así que corregir la asignación no borra el nombrado hecho antes.
    def _k(b):
        return tuple(round(float(v), 1) for v in b)
    por_bbox = {}
    for _nom, _por_t in (_cargar("registro_producto.json", pid) or {}).items():
        for _inf in (_por_t or {}).values():
            if _inf.get("bbox_mu"):
                por_bbox.setdefault(_k(_inf["bbox_mu"]), _nom)

    # Siempre se parte desde el ORIGINAL: re-asignar tiene que dar el mismo resultado que la
    # primera vez (partir una versión ya partida acumularía capas viejas).
    OA.reset_versiones(pl)
    try:
        ruta, mesa, capa_origen, orden = VM.separar_por_piezas(pl, asign)
    except Exception as e:
        return jsonify({"error": str(e)}), 422

    resumen = {"variantes": orden, "mesa": mesa, "capa_origen": capa_origen}
    try:
        doc = MP._abrir(ruta)
        try:
            ref = max(orden, key=lambda t: len(extraer_piezas_mesa(doc, mesa, t)))
            piezas_ref = extraer_piezas_mesa(doc, mesa, ref)
        finally:
            doc.close()
        # Nombres PROVISORIOS estables si la pieza todavía no tiene nombre: el registro tiene que
        # existir igual para que el molde se pueda seguir configurando; el editor de nombrado
        # (paso siguiente del flujo) los reemplaza.
        asign_nombres = [{"idx": i, "nombre": por_bbox.get(_k(p["bbox_mu"]), f"Pieza {i + 1}")}
                         for i, p in enumerate(piezas_ref)]
        alta = MP.alta_plantilla_manual(ruta, asign_nombres, mesa, ref, emparejado=_emparejado_cfg(pid))
        if not alta.get("registro"):
            raise ValueError("; ".join(alta.get("problemas") or []) or "no se registró ninguna pieza")
        _guardar_registro(pid, alta["registro"])
        resumen.update({"talles": alta.get("talles") or [], "piezas": alta.get("piezas") or [],
                        "talle_ref": ref, "problemas": alta.get("problemas") or []})
        _ajustar_variante_guia(pid, alta.get("talles") or [])
        json.dump({"archivo": (_cargar("resumen_plantilla.json", pid) or {}).get("archivo", "plantilla.ai"),
                   "mesas": alta.get("mesas"), "piezas": alta.get("piezas"),
                   "talles": alta.get("talles"),
                   "completitud": f"{len(alta['completos'])}/{len(alta['talles'])} talles completos",
                   "problemas": alta.get("problemas") or [], "advertencias": alta.get("advertencias") or [],
                   "piezas_detalle": alta.get("piezas_detalle") or {},
                   "metodo": "variantes por piezas"},
                  open(_ruta_datos("resumen_plantilla.json", pid), "w", encoding="utf-8"),
                  ensure_ascii=False)
    except Exception as e:
        resumen["problemas"] = [f"las variantes quedaron asignadas, pero el registro no se pudo "
                                f"rehacer solo: {e}"]

    # La asignación CRUDA queda guardada para poder reabrir la herramienta y corregirla.
    # `aplicadas` = copia de lo que EFECTIVAMENTE se partió: es contra esto que se compara el
    # borrador para saber si al usuario le queda trabajo sin aplicar.
    _crudas = {str(k): str(v) for k, v in asign.items()}
    json.dump({"mesa": mesa, "capa_origen": capa_origen, "orden": orden,
               "asignaciones": _crudas, "aplicadas": dict(_crudas), "aplicado_ts": time.time()},
              open(_ruta_datos("variantes_piezas.json", pid), "w", encoding="utf-8"),
              ensure_ascii=False)
    return jsonify({"ok": True, **resumen})


@app.post("/api/plantilla/variantes")
def plantilla_variantes_nombrar():
    """Aplica los nombres de variante (talle) a las capas del molde.

    Body: `{pid?, nombres: {capa_actual: nombre_nuevo}}`. Escribe una VERSIÓN nueva del molde (el
    archivo original del usuario queda intacto) y RE-ARMA el registro con los nombres nuevos, para
    que el molde quede utilizable de una: sin esto quedaría renombrado pero sin piezas.
    """
    import variantes_molde as VM
    cuerpo = request.get_json(force=True) or {}
    nombres = cuerpo.get("nombres") or {}
    pid = _get_active_producto_id()
    pl = _ruta_entrada("plantilla.ai", pid, original=True)
    if not os.path.exists(pl):
        return jsonify({"error": "primero subí el molde"}), 409
    try:
        ruta, n = VM.renombrar_capas(pl, nombres)
    except Exception as e:
        return jsonify({"error": str(e)}), 422
    # el registro se rehace leyendo la versión nueva (ahí las capas ya se llaman como corresponde)
    resumen = {"renombradas": n}
    try:
        alta = MP.alta_plantilla(_ruta_entrada("plantilla.ai", pid))
        if alta.get("registro"):
            _guardar_registro(pid, alta["registro"])
        resumen.update({"talles": alta.get("talles") or [], "piezas": alta.get("piezas") or [],
                        "problemas": alta.get("problemas") or []})
        _ajustar_variante_guia(pid, alta.get("talles") or [])
    except Exception as e:
        resumen["problemas"] = [f"las variantes quedaron nombradas, pero el registro no se pudo "
                                f"rehacer solo: {e}"]
    return jsonify({"ok": True, **resumen})


# ── Mapeo POR VARIABLE (regla 2026-07-13) ─────────────────────────────────────
# El mapeo del arte (pieza→mesa) se maneja POR VARIABLE, nunca más por molde entero.
# `mapeo_arte.json` = {"mapeo": base_compat, "por_variable": {v_xxx: {pieza: mesa}}}.
# El de la variable es AUTORITATIVO (quitar un diseño en una variable no se resucita
# por la base); la base queda para datos viejos, filas sin variable y como semilla.

def _piezas_de_variable(prod, vcl, reg=None):
    """Nombres (claves del registro) de las piezas de una VARIABLE (clave v_xxx). Resuelve por
    pieza_id ESTABLE (piezas.json) con fallback pieza_idx@talle guía (datos viejos, espejo de
    _traducir_prendas). None si la variable no existe o no se puede resolver ninguna pieza."""
    v = next((x for x in ((prod or {}).get("variantes") or []) if x.get("clave") == vcl), None)
    if not v:
        return None
    _pid = (prod or {}).get("id")
    _pz = (_cargar("piezas.json", _pid) if _pid else None) or {}
    _id2clave = {p["id"]: p["clave"] for p in _pz.get("piezas", []) if p.get("id") and p.get("clave")}
    nombres = [_id2clave[x["pieza_id"]] for x in (v.get("valores") or []) if x.get("pieza_id") in _id2clave]
    if not nombres and reg:
        _guia = (prod or {}).get("variante_guia")
        _idx2nom = {}
        for _nm, _pt in reg.items():
            _info = (_pt or {}).get(_guia)
            if isinstance(_info, dict) and _info.get("pieza_idx") is not None:
                _idx2nom[int(_info["pieza_idx"])] = _nm
        nombres = [_idx2nom[int(x["pieza_idx"])] for x in (v.get("valores") or [])
                   if x.get("pieza_idx") is not None and int(x["pieza_idx"]) in _idx2nom]
    return nombres or None


def _toggles_de_template(cols_template, cat):
    """Los TOGGLES DE PIEZA de una planilla: `[{col, clave, opciones}]`.

    Un toggle es una columna con comportamiento `manga` (el rol se generalizó: puede ser sisa,
    capucha…). Aporta una palabra CLAVE y sus OPCIONES; el valor de la fila dice cuál se eligió.
    La regla se busca por `reglaId` **y, si la columna no lo tiene, por COMPORTAMIENTO** — igual que
    `_reglaDeCol` en el front. Buscándola sólo por id, una columna sin `reglaId` (así está la de
    «Manga» en los datos reales) caía al literal "Corta, Larga" e ignoraba las opciones que el
    usuario configuró: la pantalla mostraba unas y el motor usaba otras."""
    _by_id = {r.get("id"): r for r in cat.get("reglas_planilla", [])}
    _por_comp = {}
    for _r in cat.get("reglas_planilla", []):
        _por_comp.setdefault(_r.get("comportamiento"), _r)
    out = []
    for c in (cols_template or []):
        if c.get("role") != "manga":
            continue
        regla = _by_id.get(c.get("reglaId")) or _por_comp.get(c.get("role")) or {}
        clave = c.get("clave") or regla.get("clave") or regla.get("nombre") or c.get("label") or "manga"
        ops_str = c.get("opciones") or regla.get("opciones") or "Corta, Larga"
        out.append({"col": c, "clave": str(clave).strip(),
                    "opciones": [o.strip() for o in str(ops_str).split(",") if o.strip()]})
    return out


def _cols_template_de(prod, cat):
    _t = next((t for t in cat.get("plantillas_planillas", [])
               if t.get("id") == (prod or {}).get("planilla_template_id")), None)
    return (_t or {}).get("columnas", [])


def _toggles_disponibles(prod, cat, reg=None):
    """Qué opciones de cada toggle SOPORTA de verdad este molde, en total y por variable.

    `{clave_toggle: {"opciones": [...], "*": {op: n}, "<v_xxx>": {op: n}}}` — `n` = piezas que
    mencionan esa opción; la clave `__clave__` cuenta las que mencionan la palabra del toggle.

    Por qué existe: el motor arma la prenda por el NOMBRE de las piezas. Si se elige «Larga» y las
    piezas del molde dicen «Manga Corta …», el filtro las saca a TODAS y la prenda sale **sin
    mangas, en silencio**; y si dicen «Manga Derecha» a secas, elegir Corta o Larga da exactamente
    lo mismo. Con esto la pantalla puede no ofrecer lo que el molde no tiene, y `generar_multi`
    puede frenar antes de fabricar una tizada mal."""
    toggles = _toggles_de_template(_cols_template_de(prod, cat), cat)
    if not toggles:
        return {}
    reg = reg if reg is not None else (_cargar("registro_producto.json", (prod or {}).get("id")) or {})
    todas = list(reg.keys())
    por_var = {}
    for v in ((prod or {}).get("variantes") or []):
        _cl = v.get("clave")
        if _cl:
            por_var[_cl] = _piezas_de_variable(prod, _cl, reg) or []
    out = {}
    for tg in toggles:
        d = {"opciones": tg["opciones"], "col": (tg.get("col") or {}).get("id"),
             "*": MP.opciones_soportadas(todas, tg["clave"], tg["opciones"])}
        for _cl, _nombres in por_var.items():
            d[_cl] = MP.opciones_soportadas(_nombres, tg["clave"], tg["opciones"])
        # La clave se guarda en MINÚSCULA: es la palabra que se busca en el nombre de la pieza y
        # ahí ya se compara sin mayúsculas — que el índice dependa de cómo se escribió la regla
        # («Manga» vs «manga») es una fuente de bugs silenciosos para quien lo consuma.
        out[str(tg["clave"]).strip().lower()] = d
    return out


def _toggle_no_distingue(sop):
    """Hay piezas del toggle pero NINGUNA menciona ninguna opción (ej. «Manga Derecha» a secas).

    Elegir Corta o Larga da EXACTAMENTE la misma tizada: la columna no aplica a este molde. No es
    un error de producción —lo que sale está bien— así que **no traba**: se avisa, y el front no
    ofrece opciones que no significan nada. Trabar acá dejaría al usuario sin poder generar nunca
    con ese molde (pasó al escribir esto: la traba se comía las 5 filas del pedido)."""
    if not sop or not sop.get("__clave__"):
        return False
    return all(int(v) == 0 for k, v in sop.items() if k != "__clave__")


def _opcion_sin_piezas(sop, opcion):
    """¿Esta opción deja a la prenda SIN esa parte? `sop` = un `opciones_soportadas`.

    Sólo es verdad cuando el molde **sí distingue** las opciones y la elegida no tiene ninguna
    pieza: ahí el motor saca todas las piezas del toggle y la prenda sale sin mangas (o sin lo que
    sea) **en silencio**. Eso SÍ traba.

    Los otros dos casos no son un error de producción y devuelven False: que el toggle no toque
    ninguna pieza (`__clave__ == 0` — esa variable no lleva esa parte, ej. una musculosa) y que
    ninguna opción se distinga (ver `_toggle_no_distingue`)."""
    if not sop or not sop.get("__clave__") or _toggle_no_distingue(sop):
        return False
    return int(sop.get(str(opcion or "").strip().lower(), 0)) == 0


def _validar_pedido(pid, nombre_molde, prod, cat, translated, asig, reg):
    """Frena el pedido ANTES de generar. Devuelve `(mensaje, [detalle…])` o None.

    `asig` puede ser el mapa pieza→tela, o una FUNCIÓN `dslug → mapa`: la tela se elige por
    DISEÑO, así que cada fila se valida con la de SU diseño. Con un mapa suelto (o sin filas con
    diseño) se comporta como antes.

    Los dos errores que corta salen bien impresos y parecen correctos — por eso hay que avisar
    antes y decir en qué FILA está el problema:

    1. **Una opción de toggle que el molde no tiene.** Elegir «Larga» cuando las piezas dicen
       «Manga Corta …» las saca a TODAS: la prenda sale **sin mangas**. Y si las piezas dicen
       «Manga Derecha» a secas, elegir Corta o Larga da lo mismo: la columna miente.
    2. **Una pieza sin tela.** El motor la mandaba a una tela inventada, «Principal», con el ancho
       por defecto (180 cm) en vez del de la tela real → aparecía una hoja fantasma de unos pocos
       centímetros que no corresponde a ninguna tela del registro.
    """
    _sop = _toggles_disponibles(prod, cat, reg)
    _malas, _sin_tela = [], set()
    for _i, pr in enumerate(translated, start=1):
        _vcl = pr.get("variante_clave")
        for tg in (pr.get("toggles") or []):
            _d = _sop.get(str(tg.get("clave") or "").strip().lower()) or {}
            _s = _d.get(_vcl) if (_vcl and _vcl in _d) else _d.get("*")
            if _opcion_sin_piezas(_s, tg.get("opcion")):
                _otras = [o for o in (_d.get("opciones") or []) if not _opcion_sin_piezas(_s, o)]
                _malas.append(f"Fila {_i}: el molde «{nombre_molde}» no tiene piezas de "
                              f"{tg.get('clave')} {tg.get('opcion')}"
                              + (f" (sí tiene: {', '.join(_otras)})" if _otras else
                                 f" — ninguna de sus piezas de {tg.get('clave')} distingue esa opción"))
        _a = asig(pr.get("_diseno") or "principal") if callable(asig) else asig
        if _a:
            for _p in (pr.get("variante_piezas") or []):
                if not _a.get(str(_p)):
                    _sin_tela.add(str(_p))
    if _malas:
        return ("Hay filas que piden algo que este molde no tiene. Corregilas y volvé a enviar.",
                sorted(set(_malas))[:20])
    if _sin_tela:
        return (f"Hay {len(_sin_tela)} pieza/s sin tela asignada. Asignales una en el paso Arte "
                f"(si no, no se sabe en qué tela se cortan).", sorted(_sin_tela)[:20])
    return None


def _alcance_variables(prod, reg):
    """UNIÓN de las piezas de todas las variables del molde (el alcance que importa mapear).
    Si el molde no tiene variables (o ninguna resuelve), el molde entero."""
    todas = set()
    for _v in ((prod or {}).get("variantes") or []):
        _pzv = _piezas_de_variable(prod, _v.get("clave"), reg)
        if _pzv:
            todas |= set(_pzv)
    return todas or set((reg or {}).keys())


def _mapeo_estructura(pid=None, sub=None):
    """Lee mapeo_arte.json → (base {pieza:mesa}, por_variable {v_xxx:{pieza:mesa}}).
    Datos viejos (solo "mapeo") quedan como base compartida."""
    mp = _cargar("mapeo_arte.json", pid, sub=sub) or {}
    base = {k: int(v) for k, v in (mp.get("mapeo") or {}).items() if v}
    pv = {str(c): {k: int(v) for k, v in (m or {}).items() if v}
          for c, m in (mp.get("por_variable") or {}).items()}
    return base, pv


def _mapeo_efectivo(base, pv, variante):
    """Mapeo que rige para una VARIABLE: el suyo si lo tiene (AUTORITATIVO, aunque tenga
    menos piezas que la base), si no la base. Sin variable → base."""
    v = str(variante or "").strip()
    return dict(pv[v]) if v in pv else dict(base)


@app.post("/api/arte")
def subir_arte():
    f = request.files.get("archivo")
    if not f:
        return jsonify({"error": "falta el archivo"}), 400
    sub = _diseno_sub(request.form.get("diseno"))  # arte de un DISEÑO nombrado (o el por defecto)
    plantilla = _ruta_entrada("plantilla.ai")      # la plantilla y el registro del molde son COMPARTIDOS
    if not os.path.exists(plantilla):
        return jsonify({"error": "primero subí la plantilla base"}), 409
    destino = _ruta_entrada("arte.ai", sub=sub, original=True)
    f.save(destino)
    OA.reset_versiones(destino)   # arte nuevo = se descartan las ediciones (versiones) del anterior
    return _subir_arte_analizar(destino, plantilla, f, sub)


def _subir_arte_analizar(destino, plantilla, f, sub):
    try:
        if MP.arte_es_separado(destino, plantilla):
            reg = _cargar("registro_producto.json")
            if not reg:
                return jsonify({"error": "primero registrá las piezas del molde "
                                "(subí o etiquetá la plantilla)"}), 409
            det = _urls_mesas(_deteccion_cache(destino, reg), destino, request.form.get("diseno"))
            det.update({"modo": "separado", "archivo": f.filename})
            # Los NOMBRES de la capa "guías" MANDAN: cada mesa del arte que diga el
            # nombre de una pieza se asigna a esa pieza. El mapeo fijo guardado solo
            # rellena piezas SIN nombre detectado y NUNCA pisa una mesa ya reclamada
            # por un nombre (así un diseño rotulado "Frente" siempre va a la pieza Frente).
            auto = MP.mapeo_por_nombre(destino, reg)
            _cat = _cargar_catalogo()
            _prod = next((p for p in _cat["productos"] if p["id"] == _get_active_producto_id()), None)
            _fijo = {k: int(v) for k, v in ((_prod or {}).get("mapeo_arte") or {}).items() if v and k in reg}
            mapeo = dict(auto)
            usadas = set(mapeo.values())
            for pieza, mesa in _fijo.items():
                if pieza not in mapeo and mesa not in usadas:
                    mapeo[pieza] = mesa
                    usadas.add(mesa)
            # REGLA mapeo-por-variable: el mapeo se guarda POR VARIABLE (cada una recibe su
            # recorte del auto-mapeo) y la completitud/faltantes se miden contra el ALCANCE
            # de las variables (unión de sus piezas), no contra el molde entero.
            _alcance = _alcance_variables(_prod, reg)
            _pv_ini = {}
            for _v in ((_prod or {}).get("variantes") or []):
                _vcl = _v.get("clave")
                _pzv = _piezas_de_variable(_prod, _vcl, reg)
                if _vcl and _pzv:
                    _pv_ini[_vcl] = {p: mapeo[p] for p in _pzv if p in mapeo}
            if _alcance <= set(mapeo.keys()):            # quedó completo (en su alcance) → se aplica solo
                val = MP.validar_arte_separado(destino, reg, _fuentes_para(None), mapeo, _orden_var(reg), piezas_scope=_alcance)
                val["archivo"] = f.filename
                json.dump(val, open(_ruta_datos("validacion_arte.json", sub=sub), "w", encoding="utf-8"), ensure_ascii=False)
                json.dump(val.get("personalizacion", {}), open(_ruta_datos("registro_personalizacion.json", sub=sub), "w", encoding="utf-8"))
                json.dump({"mapeo": val["mapeo"], "por_variable": _pv_ini}, open(_ruta_datos("mapeo_arte.json", sub=sub), "w", encoding="utf-8"), ensure_ascii=False)
                det.update({"auto": True, "aprobado": val["aprobado"], "checks": val["checks"], "mapeo": val["mapeo"],
                            "por_nombre": sorted(auto.keys()), "por_mapeo_fijo": sorted(set(mapeo) - set(auto)),
                            "campos_personalizacion": sorted({c for m in val.get("personalizacion", {}).values() for c in m})})
                return jsonify(det)
            # Incompleto: hay piezas del alcance SIN nombre legible en la guía. Se prellena con lo
            # detectado por nombre (no se pisa con el mapeo fijo viejo) y se pide completar.
            faltan = sorted(_alcance - set(mapeo.keys()))
            json.dump({"aprobado": False, "modo": "separado", "archivo": f.filename,
                       "checks": [{"nombre": "Mapeo de arte a piezas", "ok": False,
                                   "detalle": "faltan asignar (sin nombre en la guía): " + ", ".join(faltan)}],
                       "personalizacion": {}},
                      open(_ruta_datos("validacion_arte.json", sub=sub), "w", encoding="utf-8"), ensure_ascii=False)
            json.dump({"mapeo": mapeo, "por_variable": _pv_ini}, open(_ruta_datos("mapeo_arte.json", sub=sub), "w", encoding="utf-8"), ensure_ascii=False)
            det.update({"auto": False, "mapeo": mapeo, "por_nombre": sorted(auto.keys()), "faltan": faltan})
            return jsonify(det)
        val = MP.validar_arte(destino, plantilla, _fuentes_para(None))
    except Exception as e:
        return jsonify({"error": f"no se pudo validar el arte: {e}"}), 422
    val["archivo"] = f.filename
    val["modo"] = "clasico"
    json.dump(val, open(_ruta_datos("validacion_arte.json", sub=sub), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(val["personalizacion"], open(_ruta_datos("registro_personalizacion.json", sub=sub), "w", encoding="utf-8"))
    return jsonify(val)


def _urls_mesas(det, arte, diseno):
    """Le pone a cada mesa la URL de su imagen (`m.img`), en vez de mandar el dibujo adentro.

    Antes cada mesa viajaba como SVG dentro del JSON: con un arte de vector pesado eso son
    1098 KB **por mesa** (11,6 MB en total) que el navegador tiene que parsear y rasterizar de
    una — el paso Arte tardaba casi un minuto. Ahora el navegador pide cada mesa por separado,
    sólo las que ve, en paralelo y con caché propia. La URL lleva la firma del archivo, así que
    se puede cachear para siempre y cambia sola cuando el usuario sube otro arte."""
    from urllib.parse import quote
    try:
        firma = f"{int(os.path.getmtime(arte))}-{os.path.getsize(arte)}"
    except OSError:
        return det
    qs = f"&diseno={quote(diseno)}" if diseno else ""
    pid = quote(_get_active_producto_id() or "")
    for m in det.get("mesas") or []:
        m["img"] = f"/api/arte/mesa_img?pid={pid}{qs}&mesa={m['mesa']}&v={firma}"
    return det


@app.get("/api/arte/mesa_img")
def arte_mesa_img():
    """UNA mesa del arte, para el visor. Ver `_urls_mesas`.

    **Sale VECTORIAL (SVG), siempre**: lo que se ve en pantalla tiene que ser el diseño de
    verdad, no una foto de él — al acercarse se sigue viendo nítido y es exactamente el mismo
    dibujo que va a la tizada (ley del sistema: el arte se ve igual que la tizada). Decisión
    explícita del usuario: prefiere esperar antes que ver una versión rasterizada. El `.ai`
    original ni se toca: la tizada lo lee entero, esto es sólo para mirar.

    Lo generado se guarda en disco junto al arte, y la respuesta se puede cachear para siempre
    porque la URL lleva la firma del archivo (`v`): subir otro arte cambia la URL sola."""
    sub = _diseno_sub(request.args.get("diseno"))
    arte = _ruta_entrada("arte.ai", sub=sub)
    if not os.path.exists(arte):
        return jsonify({"error": "no hay arte cargado"}), 404
    try:
        mesa = max(1, int(request.args.get("mesa") or 1))
    except ValueError:
        return jsonify({"error": "mesa inválida"}), 400
    firma = f"{int(os.path.getmtime(arte))}-{os.path.getsize(arte)}"
    cdir = os.path.join(os.path.dirname(arte), "mesas_cache")
    dest = os.path.join(cdir, f"{firma}_{mesa}.svg")
    if not os.path.exists(dest):
        try:
            os.makedirs(cdir, exist_ok=True)
            for viejo in os.listdir(cdir):          # el arte cambió: lo de la firma vieja no sirve
                if viejo == os.path.basename(dest):
                    continue
                if not viejo.startswith(firma + "_"):
                    try:
                        os.remove(os.path.join(cdir, viejo))
                    except OSError:
                        pass
            import pymupdf as fitz
            doc = fitz.open(arte)
            if mesa > len(doc):
                doc.close()
                return jsonify({"error": "esa mesa no existe"}), 404
            try:                                    # las guías y los editables no se imprimen
                for c in doc.layer_ui_configs():
                    if MP._es_capa_guia(c.get("text")) or MP._es_capa_editable(c.get("text")):
                        doc.set_layer_ui_config(c["number"], action=2)
            except Exception:
                pass
            pg = doc[mesa - 1]
            tmp = dest + ".tmp"                     # atómico: dos pestañas pueden pedir lo mismo
            # newline="": en Windows el modo texto convierte cada \n en \r\n y el archivo dejaría
            # de ser byte por byte el vector que produce el motor (además de pesar más).
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                f.write(pg.get_svg_image())
            os.replace(tmp, dest)
            doc.close()
        except Exception as e:
            return jsonify({"error": f"no se pudo dibujar la mesa: {e}"}), 500
    r = send_file(dest, mimetype="image/svg+xml", conditional=True)
    r.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return r


@app.get("/api/arte/deteccion")
def arte_deteccion():
    sub = _diseno_sub(request.args.get("diseno"))
    arte = _ruta_entrada("arte.ai", sub=sub)
    reg = _cargar("registro_producto.json")
    if not os.path.exists(arte):
        return jsonify({"error": "primero subí el arte"}), 409
    if not reg:
        return jsonify({"error": "primero registrá las piezas del molde"}), 409
    det = _urls_mesas(_deteccion_cache(arte, reg), arte, request.args.get("diseno"))
    det["modo"] = "separado"
    cat = _cargar_catalogo()
    prod = next((p for p in cat["productos"] if p["id"] == _get_active_producto_id()), None)
    # REGLA mapeo-por-variable: se devuelve el mapeo DE la variable pedida (`?variante=v_xxx`):
    # el suyo si lo tiene (autoritativo), si no la base. Si no hay nada guardado, auto-mapear
    # por nombre AHORA (incluye el match genérico: una mesa 'Cuello' cubre todas las 'Cuello N').
    variante = str(request.args.get("variante") or "").strip()
    base, pv = _mapeo_estructura(sub=sub)
    det["mapeo"] = _mapeo_efectivo(base, pv, variante)
    if not det["mapeo"] and variante not in pv:
        det["mapeo"] = MP.mapeo_por_nombre(arte, reg)
    if variante:
        _pzv = _piezas_de_variable(prod, variante, reg)
        if _pzv:
            det["piezas_variable"] = sorted(_pzv)   # alcance de ESTA variable (para conteos del front)
    # Mapeo POR TALLE (#talle/#rango en las mesas): {pieza: {talle: mesa}}. El front lo usa para
    # que el placeholder/editor muestren el diseño del TALLE que se ve (no el default del 1er
    # rango — bug "primero aparece el 6XL"). {} si el arte no usa rótulos #.
    try:
        det["mapeo_talles"] = MP.mapeo_variantes_arte(arte, reg, _orden_var(reg)) or {}
    except Exception:
        det["mapeo_talles"] = {}
    # Mapeo FIJO guardado en el molde (configurado una vez, se reusa para todos
    # los diseños de este molde). El front lo aplica si el archivo no tiene mapeo.
    det["mapeo_fijo"] = (prod or {}).get("mapeo_arte") or {}
    return jsonify(det)


@app.post("/api/arte/mapeo")
def arte_mapeo():
    cuerpo = request.get_json(force=True)
    sub = _diseno_sub(cuerpo.get("diseno"))
    mapeo = {k: int(v) for k, v in (cuerpo.get("mapeo") or {}).items() if v}
    # REGLA mapeo-por-variable: `variante` = clave v_xxx → el mapeo enviado ES el de esa
    # variable (autoritativo). La base solo se actualiza como semilla (merge, sin borrar
    # lo de otras variables). Sin `variante` (compat/datos viejos) → comportamiento base.
    variante = str(cuerpo.get("variante") or "").strip()
    arte = _ruta_entrada("arte.ai", sub=sub)
    reg = _cargar("registro_producto.json")
    if not os.path.exists(arte) or not reg:
        return jsonify({"error": "falta el arte o el registro del molde"}), 409
    # Lectura SIN candado: validar el arte es caro (abre el .ai, chequea fuentes) y tener tomado
    # el candado de edición durante todo eso dejaría esperando a cualquier otra pantalla de
    # configuración. El catálogo se vuelve a leer —ya bajo candado— recién para guardar.
    cat = _cargar_catalogo()
    prod = next((p for p in cat["productos"] if p["id"] == _get_active_producto_id()), None)
    _scope = _piezas_de_variable(prod, variante, reg) if variante else None
    val = MP.validar_arte_separado(arte, reg, _fuentes_para(_get_active_producto_id()), mapeo, _orden_var(reg), piezas_scope=_scope)
    val["archivo"] = (_cargar("validacion_arte.json", sub=sub) or {}).get("archivo", "arte.ai")
    json.dump(val, open(_ruta_datos("validacion_arte.json", sub=sub), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(val.get("personalizacion", {}), open(_ruta_datos("registro_personalizacion.json", sub=sub), "w", encoding="utf-8"))
    base, pv = _mapeo_estructura(sub=sub)
    if variante:
        pv[variante] = dict(mapeo)
        base = {**base, **mapeo}
    else:
        base = dict(mapeo)
    json.dump({"mapeo": base, "por_variable": pv}, open(_ruta_datos("mapeo_arte.json", sub=sub), "w", encoding="utf-8"), ensure_ascii=False)
    # Guardar el mapeo como FIJO del molde (semilla para próximos diseños con el mismo orden
    # de mesas). MERGE: guardar una variable no borra las piezas sembradas por otras.
    if prod is not None:
        # Sección crítica corta: se relee el catálogo FRESCO bajo candado y se toca sólo el mapeo
        # fijo. Si se guardara el `cat` leído antes de la validación, se perdería lo que hubiera
        # guardado otra pantalla mientras tanto (ver 171.A).
        cat = _cargar_catalogo_para_editar()
        prod = next((p for p in cat["productos"] if p["id"] == _get_active_producto_id()), prod)
        prod["mapeo_arte"] = {**{k: int(v) for k, v in (prod.get("mapeo_arte") or {}).items() if v},
                              **{k: int(v) for k, v in mapeo.items()}}
        _guardar_catalogo(cat)
        _soltar_edicion_catalogo()   # el pre-warm de abajo no necesita el candado
    val["campos_personalizacion"] = sorted({c for m in val.get("personalizacion", {}).values() for c in m})
    # Pre-warm en background: armar las piezas base de cada variable al talle guía con SU mapeo
    # efectivo → el visor del Arte las tiene instantáneas (no espera el 1er armado). Best-effort.
    try:
        _pw_pid = _get_active_producto_id()
        _pw_dis = cuerpo.get("diseno")
        _pw_guia = (prod or {}).get("variante_guia") or (sorted({t for v in reg.values() for t in v})[0] if reg else "M")
        _pw_vars = [v.get("clave") for v in ((prod or {}).get("variantes") or []) if v.get("clave")] or [""]
        def _prewarm():
            for _vcl in _pw_vars:
                # MISMA estructura que el preview interactivo (arte_preview_piezas) para compartir el
                # caché en disco: {"mapeo": base, "por_variable": {variable: su_mapeo_efectivo}}.
                _arg = {"mapeo": (base or _mapeo_efectivo(base, pv, _vcl)),
                        "por_variable": ({_vcl: _mapeo_efectivo(base, pv, _vcl)} if _vcl else {})}
                try: _piezas_base(_pw_pid, _pw_dis, _vcl, _pw_guia, _arg, prod, reg, prioridad="bg", cat=cat)
                except Exception: pass
        _en_hilo(_prewarm)
    except Exception:
        pass
    return jsonify(val)


# ── PIEZAS BASE: render REAL del motor por pieza, CACHEADO en disco ───────────
# Fuente ÚNICA compartida por el visor del Arte (y a futuro la tizada): cada pieza
# YA armada (contorno + diseño encajado + borde + etiqueta, en cm reales, sin nombre/número)
# se genera UNA vez con el MISMO motor de la tizada (`generar_pedido(solo_piezas=True)`) y se
# guarda en disco. Mientras la config no cambie, se REUSA (instantáneo) en vez de re-armar.
# ⚠️ NO convertir esto en una cola general de "todo lo pesado". Se probó (subir el arte, detectar
# mesas y dibujar una mesa tomando este mismo lock) para que dos artes pesados no se pelearan la
# CPU, y el resultado fue PEOR: la generación de la tizada quedó esperando detrás de pedidos del
# visor y el usuario vio la ventana de "Armando la tizada" clavada. La tizada tiene que poder
# avanzar SIEMPRE, sin depender de lo que esté mirando la pantalla. Este lock cubre sólo el armado
# de piezas del visor, como antes.
_PIEZAS_BASE_LOCK = threading.Lock()
_PREWARM_LOCK = threading.Lock()
_PREWARM_EN_CURSO = set()   # claves (pid,diseno,variante,mapeo) con pre-warm de talles en curso
# PRIORIDAD: lo que pide el USUARIO (primer plano) NUNCA espera detrás de la precarga.
# Los pedidos "bg" (pre-warm/prefetch) ceden el paso mientras haya un "fg" esperando el lock.
_PB_FG_LOCK = threading.Lock()
_PB_FG_ESPERANDO = 0

def _sha1_corto(obj):
    import hashlib
    try:
        s = json.dumps(obj, sort_keys=True, ensure_ascii=False)
    except Exception:
        s = str(obj)
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]

def _piezas_base_clave(pid, sub, prod, mapeo, edit_cfg, edit_tam, variante, talle, edit_color=None, cat=None):
    """Clave de invalidación (espejo de `_nido_clave`): si cambia el molde, el arte, el mapeo,
    el borde, la etiqueta o los editables → cambia la clave → se regenera esa base."""
    def _mt(p):
        try: return os.path.getmtime(p)
        except OSError: return 0
    # v5: la clave incluye los OBJETOS AGREGADOS (su lista y su posición). Sin esto, agregar o
    # mover un objeto NO invalidaba la caché → el visor del Arte seguía mostrando el render viejo,
    # sin el objeto (o con la posición anterior).
    # v6: entra el REGISTRO. Una pieza es un NOMBRE, y qué geometría tiene ese nombre en cada
    # talle sale del registro: re-emparejar (o re-nombrar) cambia la pieza sin tocar el archivo
    # → sin esto el visor del Arte seguía mostrando el render de la pieza vieja.
    # v7: entra el COLOR override de editables. Sin esto, cambiar el color de un editable NO
    # invalidaba la caché → el preview del Arte seguía mostrando el color viejo (LEY arte=tizada).
    # v8: entra QUÉ PIEZAS se dibujan, que hasta acá no estaba en ningún lado:
    #   (a) la COMPOSICIÓN de la variable (`variantes[].valores`) — `_traducir_prendas` saca de ahí
    #       las piezas de la prenda: agregar una pieza a la variable no cambiaba la clave y el
    #       visor seguía mostrando la prenda vieja mientras la TIZADA sí la incluía (la tizada no
    #       usa esta caché) → divergían, contra la ley «el arte se ve igual que la tizada»;
    #   (b) las COLUMNAS de la planilla y sus REGLAS — `_piezas_base` arma una fila de muestra por
    #       cada opción de toggle leyendo el template y las reglas, así que cambiar las opciones
    #       cambia las piezas del preview.
    # Sólo se hashea la variable EN CURSO: tocar otra variable no tiene por qué regenerar ésta.
    # Ver changelog 2026-08-18 (171.B).
    _vars = (prod or {}).get("variantes") or []
    _comp = [v for v in _vars if v.get("clave") == variante] if variante else _vars
    try:
        _tg = [_cols_template_de(prod, cat), (cat or {}).get("reglas_planilla") or []] if cat is not None else []
    except Exception:
        _tg = []
    # FIRMA DE FUENTES (2026-08-20): el render estampa nombre/número con las fuentes del
    # catálogo + las del pedido + los reemplazos elegidos. Sin esto en la clave, elegir un
    # reemplazo servía el SVG cacheado con la fuente vieja («sigue sin mostrar la fuente»).
    def _firma_fuentes():
        fs = []
        for c in (os.path.join(DATOS, "productos", pid, "fuentes"), FUENTES):
            try:
                for f in sorted(os.listdir(c)):
                    if f.lower().endswith((".ttf", ".otf")):
                        fs.append((f, int(os.path.getmtime(os.path.join(c, f)))))
            except OSError:
                pass
        return fs
    return ["v12", _mt(_ruta_entrada("plantilla.ai", pid)), _mt(_ruta_entrada("arte.ai", pid, sub=sub)),
            _sha1_corto((prod or {}).get("fuentes_reemplazo") or {}), _sha1_corto(_firma_fuentes()),
            _reg_rev(pid),   # versión del registro EN LA BASE (antes: mtime del espejo)
            _sha1_corto(mapeo or {}), _sha1_corto((prod or {}).get("borde_corte") or {}),
            _sha1_corto((prod or {}).get("etiqueta") or {}), _sha1_corto(edit_cfg or {}),
            _sha1_corto(edit_tam or {}), _sha1_corto(_oa_cargar(pid, sub) or {}),
            _sha1_corto(edit_color or {}),
            _sha1_corto(_comp or []), _sha1_corto(_tg),
            str(variante or ""), str(talle or "")]

def _piezas_base(pid, diseno, variante, talle, mapeo, prod, reg, override=None, prioridad="fg", cat=None):
    """Devuelve {piezas:{nombre:{svg,w_cm,h_cm}}, talle, cache:bool} — desde disco si la clave
    coincide, si no lo genera con el motor y lo guarda. None si faltan archivos.
    `override` = ajuste per-pedido de editables (mover sin guardar como base): entra al `edit_cfg`
    → como `edit_cfg` está en la clave de caché, un override distinto regenera solo.
    `prioridad`: "fg" = lo pidió el usuario (pasa primero); "bg" = pre-warm/prefetch (cede el
    paso: espera a que no haya ningún fg esperando antes de tomar el lock de generación)."""
    import base64, tempfile, shutil
    sub = _diseno_sub(diseno)
    pl = _ruta_entrada("plantilla.ai", pid)
    arte = _ruta_entrada("arte.ai", pid, sub=sub)
    if not (prod and os.path.exists(pl) and os.path.exists(arte) and reg):
        return None
    edit_cfg = _editables_cfg(prod, (diseno or "principal"), override)
    edit_tam = _editables_tamano(prod)
    edit_color = _editables_color(prod, (diseno or "principal"))
    # El catálogo entra a la CLAVE (las columnas/reglas de toggle deciden qué piezas se dibujan).
    # Lo pasan todos los llamadores porque ya lo tienen en la mano: cargarlo acá sería un viaje
    # de más a la base en el camino caliente (el hit de caché).
    cat = cat if cat is not None else _cargar_catalogo()
    clave = _piezas_base_clave(pid, sub, prod, mapeo, edit_cfg, edit_tam, variante, talle, edit_color, cat)
    vslug = re.sub(r"[^A-Za-z0-9_-]+", "_", str(variante or "todas"))[:40] or "todas"
    tslug = re.sub(r"[^A-Za-z0-9_-]+", "_", str(talle or "guia"))[:24] or "guia"
    cdir = _ruta_datos(os.path.join("piezas_cache", vslug, tslug), pid, sub=sub)
    manifest_path = os.path.join(cdir, "manifest.json")

    def _leer_cache():
        man = json.load(open(manifest_path, encoding="utf-8"))
        if man.get("clave") != clave:
            return None
        out = {}
        for nom, info in (man.get("piezas") or {}).items():
            svg = open(os.path.join(cdir, info["archivo"]), encoding="utf-8").read()
            out[nom] = {"svg": base64.b64encode(svg.encode("utf-8")).decode("ascii"),
                        "w_cm": info["w_cm"], "h_cm": info["h_cm"]}
        return {"piezas": out, "talle": talle, "cache": True}

    try:                                            # hit sin lock (lo común)
        r = _leer_cache()
        if r is not None:
            return r
    except Exception:
        pass
    global _PB_FG_ESPERANDO
    if prioridad == "bg":
        # La precarga CEDE EL PASO: si el usuario está esperando una generación, el bg no
        # compite por el lock (antes el click del usuario quedaba en cola detrás del warm).
        while True:
            with _PB_FG_LOCK:
                if _PB_FG_ESPERANDO == 0:
                    break
            time.sleep(0.05)
    else:
        with _PB_FG_LOCK:
            _PB_FG_ESPERANDO += 1
    with _PIEZAS_BASE_LOCK:                          # miss: generar (otro hilo pudo ganarnos)
        if prioridad != "bg":
            with _PB_FG_LOCK:
                _PB_FG_ESPERANDO -= 1
        try:
            r = _leer_cache()
            if r is not None:
                return r
        except Exception:
            pass
        # (el catálogo ya está resuelto arriba: es el MISMO que entró a la clave de caché — si se
        #  recargara acá, el render podría armarse con una config distinta de la que firmó la clave)
        # Talle DIRECTO (molds sin columnas caen al fallback de _traducir_prendas) + textos de
        # MUESTRA para que el preview MUESTRE dónde caen nombre/número (el pedido real los
        # reemplaza por prenda). Se setea tanto la clave directa como la columna por rol.
        fila = {"__variante": variante, "talle": talle, "nombre": "NOMBRE", "numero": "00"}
        for c in (prod.get("columnas") or []):
            _role = c.get("role"); _cid = c.get("id") or c.get("label")
            if _role == "talle": fila[_cid] = talle
            elif _role == "nombre": fila[_cid] = "NOMBRE"
            elif _role == "numero": fila[_cid] = "00"
        # TOGGLES: el preview debe cubrir TODAS las piezas de la variable, no solo las de la
        # opción default (una fila con manga "corta" excluye las mangas largas → el visor caía
        # al re-dibujo JS con el mapeo default, SIN resolver #rango: mangas de otro color).
        # Una fila de muestra extra por cada opción restante de cada toggle → el motor arma
        # todas las piezas y el visor muestra SIEMPRE el render real (Arte = tizada).
        filas = [dict(fila)]
        _tpl = next((t for t in cat.get("plantillas_planillas", []) if t.get("id") == prod.get("planilla_template_id")), None)
        _reglas = {r.get("id"): r for r in cat.get("reglas_planilla", [])}
        for c in ((_tpl or {}).get("columnas") or []):
            if c.get("role") != "manga":
                continue
            _rg = _reglas.get(c.get("reglaId")) or {}
            _ops = [o.strip() for o in str(c.get("opciones") or _rg.get("opciones") or "Corta, Larga").split(",") if o.strip()]
            _cid = c.get("id") or c.get("label")
            for _op in _ops[1:]:
                _f2 = dict(fila); _f2[_cid] = _op
                filas.append(_f2)
        prendas = _traducir_prendas(filas, prod, cat, reg=reg)
        if not prendas:
            return {"piezas": {}, "talle": talle, "cache": False}
        try: _pers = MP.extraer_personalizacion(arte)   # placeholders (dónde caen nombre/número)
        except Exception: _pers = {}
        tmp = tempfile.mkdtemp()
        try:
            ppt = MP.generar_pedido(pl, arte, reg, _pers, prendas, _fuentes_para(pid), tmp,
                                    mapeo_arte=(mapeo or None), solo_piezas=True,
                                    borde_corte=prod.get("borde_corte"), etiqueta=prod.get("etiqueta"),
                                    editables_cfg=edit_cfg, editables_tamano=edit_tam,
                                    editables_color=edit_color,   # color override (LEY arte=tizada)
                                    # el PREVIEW debe mostrar lo MISMO que la tizada (LEY arte=tizada):
                                    # sin esto los objetos agregados no aparecían en el paso Arte.
                                    objetos_agregados=_objetos_agregados_motor(pid, sub))
            os.makedirs(cdir, exist_ok=True)
            for f in os.listdir(cdir):              # limpiar svgs viejos de esta variante/talle
                if f.endswith(".svg"):
                    try: os.remove(os.path.join(cdir, f))
                    except OSError: pass
            out, piezas_man, idx = {}, {}, 0
            for _tela, piezas in (ppt or {}).items():
                for pz in piezas:
                    try:
                        svg = pz["doc"][0].get_svg_image()
                        w_cm = round(pz["w"] / MP.CM, 2); h_cm = round(pz["h"] / MP.CM, 2)
                        fn = f"p{idx:03d}.svg"; idx += 1
                        with open(os.path.join(cdir, fn), "w", encoding="utf-8") as fh:
                            fh.write(svg)
                        out[pz["pieza"]] = {"svg": base64.b64encode(svg.encode("utf-8")).decode("ascii"),
                                            "w_cm": w_cm, "h_cm": h_cm}
                        piezas_man[pz["pieza"]] = {"archivo": fn, "w_cm": w_cm, "h_cm": h_cm}
                    except Exception:
                        pass
                    finally:
                        try: pz["doc"].close()
                        except Exception: pass
            json.dump({"clave": clave, "piezas": piezas_man},
                      open(manifest_path, "w", encoding="utf-8"), ensure_ascii=False)
            return {"piezas": out, "talle": talle, "cache": False}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


@app.post("/api/arte/preview_piezas")
def arte_preview_piezas():
    """PREVIEW REAL per-pieza (CACHEADO): sirve el render del motor por pieza desde `_piezas_base`.
    La 1ª vez por config arma y guarda; las siguientes son instantáneas. Body: {pid?, diseno,
    variante(=clave v_xxx), mapeo:{pieza:mesa}, talle?}."""
    cuerpo = request.get_json(force=True) or {}
    diseno = cuerpo.get("diseno")
    variante = str(cuerpo.get("variante") or "").strip()
    mapeo = {k: int(v) for k, v in (cuerpo.get("mapeo") or {}).items() if v}
    override = cuerpo.get("editables") or None   # ajuste per-pedido de editables (mover sin "Guardar como base")
    pid = cuerpo.get("pid") or _get_active_producto_id()   # el front pasa el molde → no depende del "activo"
    cat = _cargar_catalogo()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    reg = _cargar("registro_producto.json", pid)
    if not prod or not reg:
        return jsonify({"error": "falta producto/registro"}), 409
    guia = prod.get("variante_guia") or (sorted({t for v in reg.values() for t in v})[0] if reg else "M")
    talle = str(cuerpo.get("talle") or guia)
    _es_bg = bool(cuerpo.get("bg"))   # prefetch del front → NUNCA compite con lo que pide el usuario
    # ARTE = TIZADA: el preview pasa la MISMA estructura por-variable que la tizada (base + por_variable
    # de disco), con el mapeo EN VIVO del front reemplazando el de la variable actual. Así el modo
    # SEPARADO y los rótulos #rango se activan aunque el mapeo de esta variable esté vacío — sin esto,
    # un mapeo vacío pasaba `None` al motor y caía a modo CLÁSICO (leía la mesa del molde) → el preview
    # divergía de la tizada. El motor resuelve por `variante_clave` igual que /api/generar*.
    _b, _ = _mapeo_estructura(pid, sub=_diseno_sub(diseno))
    _mapeo_arg = ({"mapeo": (_b or mapeo), "por_variable": ({variante: mapeo} if variante else {})}
                  if (_b or mapeo) else None)
    try:
        res = _piezas_base(pid, diseno, variante, talle, _mapeo_arg, prod, reg, override,
                           prioridad=("bg" if _es_bg else "fg"), cat=cat)
    except Exception as e:
        return jsonify({"error": f"no se pudo generar el preview: {e}"}), 422
    if res is None:
        return jsonify({"error": "falta plantilla/arte/registro"}), 409
    # PRE-WARM en background del RESTO de talles de esta variable (mismo mapeo, sin override):
    # una vez cargado el diseño, navegar entre talles es INSTANTÁNEO (todo queda en disco).
    # Se deduplica por clave para no lanzar la misma tanda dos veces. Se SALTA cuando el front
    # avisa `sin_prewarm` (la ventana "Asignando…" ya recorre TODOS los talles fg → el pre-warm
    # sería trabajo redundante compitiendo por el mismo lock y serializándolo todo).
    if override is None and not _es_bg and not cuerpo.get("sin_prewarm"):
        try:
            _otros = [t for t in _variantes_molde(pid) if str(t) != talle]
            _pwk = (pid, str(diseno or ""), variante, _sha1_corto(_mapeo_arg))
            with _PREWARM_LOCK:
                _lanzar = _pwk not in _PREWARM_EN_CURSO
                if _lanzar:
                    _PREWARM_EN_CURSO.add(_pwk)
            if _lanzar and _otros:
                def _pw_talles():
                    try:
                        for _t in _otros:
                            try: _piezas_base(pid, diseno, variante, str(_t), _mapeo_arg, prod, reg, prioridad="bg", cat=cat)
                            except Exception: pass
                    finally:
                        with _PREWARM_LOCK:
                            _PREWARM_EN_CURSO.discard(_pwk)
                _en_hilo(_pw_talles)
        except Exception:
            pass
    return jsonify(res)


# ── ASIGNAR TODAS LAS VARIANTES EN PARALELO (multiproceso) ───────────────────
# PyMuPDF NO es thread-safe (crashea) → se generan los talles en PROCESOS separados
# (recomendación verificada, doc oficial). Cada worker hace su pipeline completo (fitz +
# pikepdf + SVG) sin cruzar objetos, y escribe el render al caché en disco. El ProcessPool
# es PERSISTENTE (el spawn en Windows re-importa el módulo; crearlo una vez amortiza).
_RENDER_POOL = None
_RENDER_POOL_LOCK = threading.Lock()
_ASIGNAR_JOBS = {}          # job_id -> {"hecho": n, "total": N, "done": bool}

def procesos_render():
    """Cuántos procesos de render en paralelo. **CADA UNO PESA ~200 MB** (medido: 170 MB un talle
    en frío, 194 MB una tizada completa) → en un servidor con poca RAM hay que bajarlo o el sistema
    se queda sin memoria. `TIZADA_PROCESOS=2` es lo recomendado para ~1 GB libre.
    Sin la variable: el comportamiento de siempre (hasta 6, según los núcleos)."""
    try:
        n = int(os.environ.get("TIZADA_PROCESOS") or 0)
    except ValueError:
        n = 0
    return max(1, n) if n else min((os.cpu_count() or 4), 6)


def _get_render_pool():
    global _RENDER_POOL
    with _RENDER_POOL_LOCK:
        # Si un worker murió de golpe (se quedó sin memoria, lo mató el sistema), el pool queda
        # ROTO y todo lo que se le mande después falla con BrokenProcessPool — para siempre, hasta
        # reiniciar el servidor. Se descarta y se arma otro: es preferible perder unos segundos
        # levantándolo de nuevo a que el usuario no pueda volver a generar nada.
        if _RENDER_POOL is not None and getattr(_RENDER_POOL, "_broken", False):
            try:
                _RENDER_POOL.shutdown(wait=False)
            except Exception:
                pass
            _RENDER_POOL = None
        if _RENDER_POOL is None:
            from concurrent.futures import ProcessPoolExecutor
            _RENDER_POOL = ProcessPoolExecutor(max_workers=procesos_render())
    return _RENDER_POOL


def _render_talle_worker(args):
    """WORKER de proceso: genera UN talle → caché en disco. Recibe SOLO tipos simples
    (spawn-safe), no cruza objetos fitz/pikepdf entre procesos. El env TIZADA_* lo hereda
    del proceso padre (spawn hereda el entorno). Devuelve el talle (o None si falló)."""
    pid, diseno, variante, talle, mapeo_arg = args
    try:
        cat = _cargar_catalogo()
        prod = next((p for p in cat["productos"] if p["id"] == pid), None)
        reg = _cargar("registro_producto.json", pid)
        if prod and reg:
            _piezas_base(pid, diseno, variante, talle, mapeo_arg, prod, reg, cat=cat)
        return talle
    except Exception:
        return None

def _deteccion_talle_worker(args):
    """WORKER de proceso: pre-genera la DETECCIÓN de piezas de UN talle → caché en disco.
    Es lo caro del visor (get_drawings de todo el molde); en paralelo, no 19× secuencial."""
    pid, talle = args
    try:
        _deteccion_base_cached(pid, talle)
        return talle
    except Exception:
        return None

@app.post("/api/arte/asignar_todo")
def arte_asignar_todo():
    """Genera EN PARALELO (ProcessPool) el render de TODOS los talles de una variable → caché
    en disco. Devuelve un job_id; el progreso se consulta en /api/arte/asignar_estado. Después
    el front pide cada talle (sale del caché, instantáneo) para cargarlo a su memoria."""
    cuerpo = request.get_json(force=True) or {}
    diseno = cuerpo.get("diseno"); variante = str(cuerpo.get("variante") or "").strip()
    mapeo = {k: int(v) for k, v in (cuerpo.get("mapeo") or {}).items() if v}
    pid = cuerpo.get("pid") or _get_active_producto_id()
    prod = next((p for p in _cargar_catalogo()["productos"] if p["id"] == pid), None)
    reg = _cargar("registro_producto.json", pid)
    if not prod or not reg:
        return jsonify({"error": "falta producto/registro"}), 409
    _b, _ = _mapeo_estructura(pid, sub=_diseno_sub(diseno))
    _mapeo_arg = {"mapeo": (_b or mapeo), "por_variable": ({variante: mapeo} if variante else {})}
    # `talles` explícitos = dibujar SÓLO esos (por defecto, el molde entero). El visor pide primero
    # el talle guía y los demás recién cuando se los toca: con un arte pesado cada talle son ~8
    # recortes del vector, y hacer los 20 de una eran ~60 s de espera para ver algo.
    talles = [str(t) for t in (cuerpo.get("talles") or []) if str(t).strip()] or _variantes_molde(pid)
    job = uuid.uuid4().hex[:8]
    # PROGRESO DE VERDAD: los talles terminan de a uno y de golpe (el primero tarda lo que tarda
    # levantar los procesos + renderizar entero) → el cartel se quedaba clavado en «0/20» y parecía
    # colgado. Los workers van dejando cada pieza en disco (`piezas_cache/<variable>/<talle>/*.svg`),
    # así que se cuentan esos archivos: eso SÍ se mueve todo el tiempo y no es una estimación.
    _vslug = re.sub(r"[^A-Za-z0-9_-]+", "_", str(variante or "todas"))[:40] or "todas"
    _sub = os.path.join("piezas_cache", _vslug)
    if len(talles) == 1:   # con un solo talle se mira SU carpeta: si no, se cuentan las piezas
        _sub = os.path.join(_sub, re.sub(r"[^A-Za-z0-9_-]+", "_", str(talles[0]))[:24] or "guia")
    _dircache = _ruta_datos(_sub, pid, sub=_diseno_sub(diseno))
    _ASIGNAR_JOBS[job] = {"hecho": 0, "total": len(talles), "done": False,
                          "dir": _dircache, "desde": time.time() - 1, "fase": "arrancando"}
    if len(_ASIGNAR_JOBS) > 40:   # no acumular jobs viejos
        for k in [k for k, v in list(_ASIGNAR_JOBS.items()) if v.get("done")][:20]:
            _ASIGNAR_JOBS.pop(k, None)
    def _run():
        try:
            from concurrent.futures import as_completed
            pool = _get_render_pool()
            # RENDERS (por variable) + DETECCIONES (por molde, para el visor) — ambos en paralelo.
            futs = [pool.submit(_render_talle_worker, (pid, diseno, variante, str(t), _mapeo_arg)) for t in talles]
            det = [pool.submit(_deteccion_talle_worker, (pid, str(t))) for t in talles]
            _ASIGNAR_JOBS[job]["fase"] = "dibujando"
            for _f in as_completed(futs):
                _ASIGNAR_JOBS[job]["hecho"] += 1
            _ASIGNAR_JOBS[job]["fase"] = "midiendo"    # ya están los diseños; faltan las medidas
            for _f in as_completed(det):   # esperar también las detecciones (para que el front no las recalcule)
                pass
        except Exception as e:
            _ASIGNAR_JOBS[job]["error"] = str(e)
        finally:
            _ASIGNAR_JOBS[job]["done"] = True
    _en_hilo(_run)
    return jsonify({"job": job, "total": len(talles)})

def _contar_svgs(carpeta, desde=0):
    """Piezas dibujadas EN ESTA pasada: los `.svg` del caché de la variable escritos después de
    `desde`. Por fecha y no por diferencia de totales, porque re-dibujar un talle PISA los
    archivos que ya estaban (misma cantidad) y el contador se quedaba clavado en cero."""
    n = 0
    for raiz, _dirs, arch in os.walk(carpeta):
        for a in arch:
            if a.endswith(".svg"):
                try:
                    if os.path.getmtime(os.path.join(raiz, a)) >= desde:
                        n += 1
                except OSError:
                    pass
    return n


@app.get("/api/arte/asignar_estado")
def arte_asignar_estado():
    st = _ASIGNAR_JOBS.get(request.args.get("job"))
    if not st:
        return jsonify({"error": "job desconocido", "done": True})
    out = {k: v for k, v in st.items() if k not in ("dir", "desde")}
    if st.get("dir"):   # piezas ya dibujadas EN ESTA pasada: se mueve aunque ningún talle haya terminado
        out["piezas"] = _contar_svgs(st["dir"], st.get("desde") or 0)
    return jsonify(out)


# ── Diseños nombrados por molde ──────────────────────────────────────────────
# Un molde puede tener varios DISEÑOS (artes con nombre). "Principal" es el arte
# base del molde (carpeta raíz). Los demás viven en datos/entrada .../disenos/<slug>/.
@app.get("/api/disenos")
def listar_disenos():
    pids = [p for p in (request.args.get("molds", "").split(",")) if p] or [_get_active_producto_id()]
    cat = _cargar_catalogo()
    por_molde, nombres, seen = {}, [], set()
    for pid in pids:
        prod = next((p for p in cat["productos"] if p["id"] == pid), None)
        lst = [{"id": "principal", "nombre": "Principal"}]
        for d in ((prod or {}).get("disenos") or []):
            lst.append({"id": d["id"], "nombre": d["nombre"]})
        por_molde[pid] = lst
        for d in lst:
            if d["nombre"] not in seen:
                seen.add(d["nombre"]); nombres.append(d["nombre"])
    return jsonify({"por_molde": por_molde, "nombres": nombres})


@app.post("/api/disenos/guardar")
def guardar_diseno():
    cuerpo = request.get_json(force=True)
    pid = cuerpo.get("pid") or _get_active_producto_id()
    nombre = (cuerpo.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"error": "falta el nombre del diseño"}), 400
    slug = re.sub(r"[^a-z0-9]+", "-", nombre.lower()).strip("-")[:48] or "diseno"
    if slug in ("principal", "default"):
        return jsonify({"error": "'Principal' ya es el diseño base del molde"}), 400
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if prod is None:
        return jsonify({"error": "molde no encontrado"}), 404
    disenos = prod.setdefault("disenos", [])
    if not any(d["id"] == slug for d in disenos):
        disenos.append({"id": slug, "nombre": nombre})
        _guardar_catalogo(cat)
    return jsonify({"id": slug, "nombre": nombre})


@app.post("/api/disenos/eliminar")
def eliminar_diseno():
    import shutil
    cuerpo = request.get_json(force=True)
    pid = cuerpo.get("pid") or _get_active_producto_id()
    did = cuerpo.get("id")
    if not did or did in ("principal", "default"):
        return jsonify({"error": "no se puede borrar el diseño Principal"}), 400
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if prod is not None:
        prod["disenos"] = [d for d in (prod.get("disenos") or []) if d["id"] != did]
        _guardar_catalogo(cat)
    sub = _diseno_sub(did)
    if sub:
        for base in (os.path.join(DATOS, "productos", pid, sub), os.path.join(ENTRADA, pid, sub)):
            shutil.rmtree(base, ignore_errors=True)
    return jsonify({"ok": True})


# ── Borde de corte por molde ────────────────────────────────────────────────
_BORDE_DEFAULT = {"activo": True, "ancho_mm": 2.0, "color": [0, 0, 0, 0.85], "alineacion": "fuera"}


@app.get("/api/productos/borde_corte")
def get_borde_corte():
    pid = request.args.get("pid") or _get_active_producto_id()
    prod = next((p for p in _cargar_catalogo()["productos"] if p["id"] == pid), None)
    bc = dict(_BORDE_DEFAULT, **((prod or {}).get("borde_corte") or {}))
    return jsonify(bc)


@app.post("/api/productos/borde_corte")
def set_borde_corte():
    cuerpo = request.get_json(force=True)
    pid = cuerpo.get("pid") or _get_active_producto_id()
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if prod is None:
        return jsonify({"error": "molde no encontrado"}), 404
    try:
        color = [max(0.0, min(1.0, float(x))) for x in (cuerpo.get("color") or [0, 0, 0, 0.85])][:4]
        while len(color) < 4:
            color.append(0.0)
        _alin = cuerpo.get("alineacion") or "fuera"
        if _alin not in ("fuera", "centro", "dentro"):
            return jsonify({"error": "alineación de borde inválida"}), 400
        bc = {"activo": bool(cuerpo.get("activo", True)),
              "ancho_mm": max(0.2, min(20.0, float(cuerpo.get("ancho_mm", 2.0)))),
              "color": color,
              "alineacion": _alin}
    except (TypeError, ValueError):
        return jsonify({"error": "valores de borde inválidos"}), 400
    prod["borde_corte"] = bc
    _guardar_catalogo(cat)
    return jsonify(bc)


# ── Etiqueta de identificación por molde ────────────────────────────────────
_ETIQUETA_DEFAULT = {
    "activo": True,
    "mostrar": {"talle": True, "pieza": True, "numero": True},
    "separador": "-",
    "posicion": {"rx": 0.5, "ry": 0.92},
    "posiciones": {},
    "align": "centro",
    "size_mm": 3.0,
    "color": [0.15, 0.15, 0.15, 0.30],
    "borde_activo": True,
    "borde_color": [0.01, 0.01, 0.01, 0.05],
    "borde_mm": 1.0,
    "piezas_off": [],
    "zonas": {},
}


# OJO con el NOMBRE: más abajo hay otro `_clamp_color(color)` (colores de editables, 1 argumento)
# que PISABA a este —Python se queda con la última definición del módulo— y por eso guardar la
# etiqueta tiraba siempre «_clamp_color() takes 1 positional argument but 2 were given» (400).
def _clamp_color_etq(c, fb):
    """Color CMYK de la ETIQUETA con valor por defecto (`fb`) si viene vacío o inválido."""
    try:
        col = [max(0.0, min(1.0, float(x))) for x in (c or fb)][:4]
    except (TypeError, ValueError):
        col = list(fb)
    while len(col) < 4:
        col.append(0.0)
    return col


def _etq_mismo_lugar(a, b):
    """¿Dos posiciones de etiqueta caen en el mismo lugar? (para no reportar como conflicto lo
    que en realidad está igual configurado en dos variables)."""
    def _n(v, k, d=0.0):
        try:
            return round(float((v or {}).get(k, d) or 0.0), 4)
        except (TypeError, ValueError):
            return d
    return (all(_n(a, k) == _n(b, k) for k in ("rx", "ry", "ang", "t"))
            and (a or {}).get("align") == (b or {}).get("align"))


def _etq_posiciones_por_pieza(posiciones):
    """Pasa las posiciones de la etiqueta al modelo **POR PIEZA** (2026-08-18).

    Antes cada posición se guardaba con namespace: `v_xxx§Frente 8` (por variable, lo que armaba
    la pantalla vieja) o `g_xxx§Frente` (por grupo, legacy). Ahora **la posición es de la pieza** y
    vale para todo el molde, así que la clave es el **nombre COMPLETO de la pieza** («Frente 1»),
    sin namespace.

    ⛔ **Regla del usuario (2026-08-18): «Frente 1» y «Frente 2» son piezas DISTINTAS.** Poner la
    etiqueta del Frente 1 al costado NO mueve la de los otros frentes. Por eso la clave conserva el
    número y NO se colapsa al genérico. (El nombre completo ya es talle-independiente: en el
    registro una pieza es un nombre con sus talles adentro, así que la misma posición sirve para
    todos los talles — que es lo que se quiere.)

    Orden a propósito: **primero las que tienen namespace** (son las que el usuario configuró con
    la pantalla de variables) y después las globales viejas para las piezas que falten. Así el
    resultado coincide con lo que la tizada venía sacando, que es lo que el usuario tiene en la mano.

    Devuelve `(posiciones, conflictos)`. Si la MISMA pieza tenía posiciones DISTINTAS en dos
    variables sólo puede quedar una: gana la primera (orden estable) y la otra se informa — el
    usuario tiene que enterarse acá, no descubrirlo cuando salga la tizada.
    """
    con_ns = [(k, v) for k, v in (posiciones or {}).items() if "§" in k]
    sin_ns = [(k, v) for k, v in (posiciones or {}).items() if "§" not in k]
    out, por_clave, conflictos = {}, {}, []
    for k, v in con_ns + sin_ns:
        nombre = str(k.split("§", 1)[1] if "§" in k else k).strip()
        clave = MP._norm_nombre(nombre)      # POR PIEZA: el nombre completo, con su número
        if not clave:
            continue
        if clave in por_clave:
            if not _etq_mismo_lugar(por_clave[clave], v) and nombre not in conflictos:
                conflictos.append(nombre)   # esa pieza tenía DOS lugares distintos: queda el primero
            continue
        por_clave[clave] = v
        out[nombre] = v
    return out, conflictos


def _etq_piezas_del_molde(reg):
    """Las piezas del molde agrupadas por NOMBRE GENÉRICO — la lista del panel derecho.

    Una entrada por pieza («Frente», «Espalda», «Cuello»…, ~9) y adentro las piezas reales que la
    componen con su talle («Frente 8» del talle M…), que es lo que el visor tiene que dibujar
    cuando se la elige."""
    porgen = {}
    for nombre, por_talle in (reg or {}).items():
        gen = re.sub(r"\s+\d+\s*$", "", str(nombre)).strip() or str(nombre)
        clave = MP._norm_generico(gen)
        if not clave:
            continue
        d = porgen.setdefault(clave, {"nombre": gen, "piezas": [], "talles": []})
        d["piezas"].append(nombre)
        for t in (por_talle or {}):
            if t not in d["talles"]:
                d["talles"].append(t)
    for d in porgen.values():
        d["piezas"].sort()
        d["talles"].sort()
    return sorted(porgen.values(), key=lambda d: d["nombre"].lower())


@app.get("/api/productos/etiqueta")
def get_etiqueta():
    pid = request.args.get("pid") or _get_active_producto_id()
    prod = next((p for p in _cargar_catalogo()["productos"] if p["id"] == pid), None)
    et = {**_ETIQUETA_DEFAULT, **((prod or {}).get("etiqueta") or {})}
    et["mostrar"] = {**_ETIQUETA_DEFAULT["mostrar"], **(et.get("mostrar") or {})}
    et["posicion"] = {**_ETIQUETA_DEFAULT["posicion"], **(et.get("posicion") or {})}
    # La pantalla trabaja POR PIEZA: se devuelve ya migrado (en memoria; se persiste cuando el
    # usuario guarda). `migradas`/`conflictos` son para avisarle qué pasó con lo que ya tenía.
    _pos, _conf = _etq_posiciones_por_pieza(et.get("posiciones"))
    et["migradas"] = sum(1 for k in (et.get("posiciones") or {}) if "§" in k)
    et["conflictos"] = _conf
    et["posiciones"] = _pos
    # piezas del molde (para la lista de "en qué piezas")
    reg = _cargar("registro_producto.json", pid) or {}
    et["piezas"] = sorted(reg.keys())
    et["piezas_gen"] = _etq_piezas_del_molde(reg)
    return jsonify(et)


@app.post("/api/productos/etiqueta")
def set_etiqueta():
    cuerpo = request.get_json(force=True)
    pid = cuerpo.get("pid") or _get_active_producto_id()
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if prod is None:
        return jsonify({"error": "molde no encontrado"}), 404
    # Un campo numérico vacío o mal tipeado (el input de la UI puede quedar en "" mientras se edita,
    # o venir con coma) NO puede impedir guardar: se toma el valor por defecto en vez de tirar 400.
    def _num(v, d, lo=None, hi=None):
        try:
            x = float(str(v).replace(",", ".")) if isinstance(v, str) else float(v)
            if x != x:                      # NaN
                raise ValueError
        except (TypeError, ValueError):
            x = float(d)
        if lo is not None:
            x = max(lo, x)
        if hi is not None:
            x = min(hi, x)
        return x
    try:
        mos = cuerpo.get("mostrar") or {}
        pos = cuerpo.get("posicion") or {}
        et = {
            "activo": bool(cuerpo.get("activo", True)),
            "mostrar": {k: bool(mos.get(k, True)) for k in ("talle", "pieza", "numero")},
            "separador": (str(cuerpo.get("separador", "-")) or "-")[:3],
            "posicion": {"rx": _num(pos.get("rx"), 0.5, 0.0, 1.0),
                          "ry": _num(pos.get("ry"), 0.92, 0.0, 1.0)},
            "posiciones": {str(k): {"rx": _num(v.get("rx"), 0.5, 0.0, 1.0),
                                     "ry": _num(v.get("ry"), 0.92, 0.0, 1.0),
                                     "ang": _num(v.get("ang"), 0),
                                     **({"t": _num(v.get("t"), 0.0, 0.0, 1.0)} if v.get("t") is not None else {}),
                                     **({"align": str(v.get("align"))} if v.get("align") in ("izquierda", "centro", "derecha") else {})}
                            for k, v in (cuerpo.get("posiciones") or {}).items() if isinstance(v, dict)},
            "align": cuerpo.get("align") if cuerpo.get("align") in ("izquierda", "centro", "derecha") else "centro",
            "size_mm": _num(cuerpo.get("size_mm"), 3.0, 1.0, 40.0),
            "color": _clamp_color_etq(cuerpo.get("color"), [0.15, 0.15, 0.15, 0.30]),
            "borde_activo": bool(cuerpo.get("borde_activo", True)),
            "borde_color": _clamp_color_etq(cuerpo.get("borde_color"), [0.01, 0.01, 0.01, 0.05]),
            "borde_mm": _num(cuerpo.get("borde_mm"), 1.0, 0.0, 10.0),
            "piezas_off": [str(p) for p in (cuerpo.get("piezas_off") or [])],
            # ZONAS de texto por pieza (dividir el contorno en tramos eligiendo esquinas):
            # {nombre: {puntos:[t 0-1], cont:[{mostrar:{talle,pieza,numero}, texto, align}]}}
            "zonas": {str(k): {
                "puntos": [_num(t, 0.0, 0.0, 1.0) for t in (v.get("puntos") or []) if isinstance(t, (int, float))],
                "cont": [{
                    "mostrar": {kk: bool((c.get("mostrar") or {}).get(kk, False)) for kk in ("talle", "pieza", "numero")},
                    "texto": str(c.get("texto", ""))[:40],
                    "align": str(c.get("align")) if c.get("align") in ("izquierda", "centro", "derecha") else "centro",
                } for c in (v.get("cont") or []) if isinstance(c, dict)],
            } for k, v in (cuerpo.get("zonas") or {}).items() if isinstance(v, dict) and (v.get("puntos") or [])},
        }
    except (TypeError, ValueError) as _e:
        # Ya no debería pasar (todo lo numérico usa `_num`), pero si pasa se dice QUÉ falló.
        return jsonify({"error": f"valores de etiqueta inválidos: {_e}"}), 400
    # POR PIEZA (2026-08-18): la posición es de la pieza y vale para todo el molde. Si algo llega
    # con el namespace viejo (`variante§pieza`) se migra ACÁ, antes de guardar. Si quedara una
    # clave vieja, el motor le daría MÁS prioridad que a la nueva y la etiqueta saldría en el
    # lugar de antes aunque la pantalla mostrara el nuevo — el bug clásico de esta pantalla:
    # se ve bien y sale movida (ver changelog 146).
    et["posiciones"], _conf_mig = _etq_posiciones_por_pieza(et.get("posiciones"))
    prod["etiqueta"] = et
    _guardar_catalogo(cat)
    # La respuesta lleva TAMBIÉN la lista de piezas (como el GET): el front reemplaza su
    # config con esta respuesta, y sin `piezas`/`piezas_gen` la lista de la pantalla
    # DESAPARECÍA después de cada guardado (reporte del usuario 2026-08-20).
    _reg_et = _cargar("registro_producto.json", pid) or {}
    return jsonify({**et, "conflictos": _conf_mig,
                    "piezas": sorted(_reg_et.keys()),
                    "piezas_gen": _etq_piezas_del_molde(_reg_et)})


# ── Objetos editables (capa "Editable …" del arte) ───────────────────────────
def _pos_en_pieza(mesa_rect, bbox_mu, pieza_bbox):
    """Posición del objeto sobre su pieza en FRACCIONES (0..1 del bbox de la pieza), con el
    mismo encaje que el motor (cm_encajar): el arte se escala al ALTO de la pieza (manda el
    alto) y se centra a lo ancho. Devuelve {rx,ry,rw,rh} (esquina sup-izq + tamaño) o None."""
    try:
        ax0, ay0, aw, ah = mesa_rect
        ox0, oy0, ox1, oy1 = bbox_mu
        px0, py0, px1, py1 = pieza_bbox
        pw, ph = (px1 - px0), (py1 - py0)
        if aw <= 0 or ah <= 0 or pw <= 0 or ph <= 0:
            return None
        awf = (aw * (ph / ah)) / pw                       # ancho del arte como fracción del de la pieza
        rx = (1 - awf) / 2 + ((ox0 - ax0) / aw) * awf      # centrado a lo ancho
        ry = (oy0 - ay0) / ah                              # vertical: el arte llena el alto (y-abajo)
        return {"rx": round(rx, 4), "ry": round(ry, 4),
                "rw": round(((ox1 - ox0) / aw) * awf, 4), "rh": round((oy1 - oy0) / ah, 4)}
    except Exception:
        return None


# Separador del IDENT de un objeto editable: "nombre_capa<SEP>obj_id". Debe coincidir con `SEP` del
# motor. La config multi-objeto se GUARDA anidada (…[capa]["objetos"][obj_id]); al motor y al front
# viaja PLANA con el IDENT (el motor identifica cada objeto por su IDENT). Control-char (US): válido
# en JSON, no aparece en nombres de capa de Illustrator.
_EDIT_SEP = ""


def _ident_obj(nombre, obj_id):
    return f"{nombre}{_EDIT_SEP}{obj_id}" if obj_id else nombre


def _split_ident(ident):
    """IDENT → (nombre_capa, obj_id|None). rsplit por si el nombre de capa trajera el separador."""
    if _EDIT_SEP in str(ident):
        n, o = str(ident).rsplit(_EDIT_SEP, 1)
        return n, o
    return str(ident), None


def _tf_de_capa(entry):
    """Transform de UNA capa editable (la capa es el objeto: todo lo de adentro se mueve junto).
    Si la entrada trae la config VIEJA por figura (…["objetos"][oid]["transforms"]) y la capa no
    tiene transform propio, se adopta el de la primera figura que tenga uno → lo que el usuario
    ya había movido no se pierde ni queda a medias entre figuras."""
    entry = entry or {}
    tf = dict(entry.get("transforms") or {})
    if not tf:
        for sub in (entry.get("objetos") or {}).values():
            tf = dict((sub or {}).get("transforms") or {})
            if tf:
                break
    return tf


def _editables_cfg(prod, dslug, override=None):
    """Config de editables para el motor: BASE del catálogo POR VARIABLE + AJUSTE del pedido (override),
    mergeado por (variable, IDENT, talle). → {variable: {IDENT: {talle: tf}}}.
    El IDENT del TRANSFORM es SIEMPRE el nombre de la CAPA: la capa es UN objeto editable y todo lo
    que tenga adentro se transforma junto. Compat: config vieja guardada por figura
    (…[capa]["objetos"][obj_id]["transforms"]) → se toma como transform DE LA CAPA (la primera con
    valor), para no perder lo que el usuario ya había movido.
    Compat: formato VIEJO (base[objeto]={"transforms":...}, sin nivel variable) → clave "*"."""
    base = (((prod or {}).get("editables") or {}).get(dslug) or {})
    out = {}
    for var, objs in base.items():
        if isinstance(objs, dict) and "transforms" in objs:       # VIEJO: var es un OBJETO (capa)
            out.setdefault("*", {})[var] = dict(objs.get("transforms") or {})
        else:                                                     # NUEVO: var es una VARIABLE
            for capa, entry in (objs or {}).items():
                entry = entry or {}
                out.setdefault(var, {})[capa] = _tf_de_capa(entry)
    for var, objs in (override or {}).items():                    # override = {variable: {IDENT: {talle: tf}}}
        if not objs:
            continue                                              # override VACÍO → no cambia nada (no ensuciar
                                                                  # la clave de caché: {v:{}} != None hacía cache MISS)
        o = out.setdefault(var, {})
        for ident, tfs in (objs or {}).items():
            if not tfs:
                continue
            oo = o.setdefault(ident, {})
            for talle, tf in (tfs or {}).items():
                oo[talle] = _clamp_tf(tf)
    return out


def _clamp_color(color):
    """Sanea un color override CMYK de un editable. Devuelve {"fill":[c,m,y,k]|None,
    "stroke":[c,m,y,k]|None} o None si no hay NINGÚN canal (= sin override / volver al original).
    Cada canal en 0..1 (se guarda y se manda CMYK EXACTO, sin re-cuantizar — sublimación)."""
    if not color:
        return None
    def _cmyk(v):
        if not v:
            return None
        try:
            vals = [max(0.0, min(1.0, float(x))) for x in v][:4]
        except Exception:
            return None
        return vals if len(vals) == 4 else None
    f = _cmyk((color or {}).get("fill"))
    s = _cmyk((color or {}).get("stroke"))
    if f is None and s is None:
        return None
    return {"fill": f, "stroke": s}


def _editables_color(prod, dslug):
    """Color override de editables para el motor: {variable: {IDENT: {"fill":[cmyk]|None,
    "stroke":[cmyk]|None}}}. Espejo de `_editables_cfg` pero para el COLOR (a nivel objeto, no
    por talle). Compat: formato VIEJO (base[objeto]={"transforms":...}) → clave "*"."""
    base = (((prod or {}).get("editables") or {}).get(dslug) or {})
    out = {}
    for var, objs in base.items():
        if isinstance(objs, dict) and "transforms" in objs:       # VIEJO: var es un OBJETO (capa)
            c = _clamp_color(objs.get("color"))
            if c:
                out.setdefault("*", {})[var] = c
        else:                                                     # NUEVO: var es una VARIABLE
            for capa, entry in (objs or {}).items():
                entry = entry or {}
                if "objetos" in entry:                            # capa MULTI-objeto
                    for oid, sub in (entry.get("objetos") or {}).items():
                        c = _clamp_color((sub or {}).get("color"))
                        if c:
                            out.setdefault(var, {})[_ident_obj(capa, oid)] = c
                else:                                             # capa de 1 objeto (compat)
                    c = _clamp_color(entry.get("color"))
                    if c:
                        out.setdefault(var, {})[capa] = c
    return out


def _caja_cm(d):
    """{ancho, alto} → [ancho_cm, alto_cm] (0 = sin límite por ese lado)."""
    d = d or {}
    def _f(x):
        try:
            return max(0.0, float(x))
        except Exception:
            return 0.0
    return [_f(d.get("ancho")), _f(d.get("alto"))]


def _editables_tamano(prod):
    """Config de TAMAÑO por molde (general por nombre de capa) →
    {nombre_norm: {variante: {"apaisado":[ancho,alto], "vertical":[ancho,alto]}}}.
    Resuelve las variantes de cada rango a sus dos cajas (apaisado/vertical). Una variante
    fuera de todo rango → no aparece (el motor escala con el diseño)."""
    out = {}
    for key, cfg in ((prod or {}).get("editables_config") or {}).items():
        porvar = {}
        for r in (cfg or {}).get("rangos", []):
            if r.get("mantener"):
                box = {"mantener": True}                 # tamaño original del diseño (sin escalar)
            else:
                ap = _caja_cm(r.get("apaisado"))
                ve = _caja_cm(r.get("vertical"))
                if max(ap) <= 0 and max(ve) <= 0:
                    continue
                box = {"apaisado": ap, "vertical": ve}
            for v in (r.get("variantes") or []):
                porvar[str(v)] = box
        if porvar:
            out[key] = porvar
    return out


def _orden_var(reg):
    """Variantes (de un registro ya cargado) en orden de archivo de la plantilla activa.
    Para resolver rangos `#v1-v2` en la validación. Si no hay plantilla, orden alfabético."""
    vs = sorted({t for v in (reg or {}).values() for t in (v or {})})
    try:
        pl = _ruta_entrada("plantilla.ai")
        if os.path.exists(pl):
            return MP.talles_orden_archivo(pl, vs) or vs
    except Exception:
        pass
    return vs


def _variantes_molde(pid):
    """Variantes del molde (talles/tamaños/etc.) en orden de archivo."""
    reg = _cargar("registro_producto.json", pid) or {}
    variantes = sorted({t for v in reg.values() for t in (v or {}).keys()})
    try:
        pl = _ruta_entrada("plantilla.ai", pid)
        if os.path.exists(pl):
            variantes = MP.talles_orden_archivo(pl, variantes) or variantes
    except Exception:
        pass
    return variantes


def _clamp_tf(v):
    """Saneo de la transformación de un objeto editable (mover/rotar/escalar).
    `scale` = escala UNIFORME (legacy). `sx`/`sy` = ancho/alto por separado (enlace de
    proporción desactivado en el editor); si no vienen, valen `scale`."""
    v = v or {}
    # El SIGNO se conserva: negativo = ESPEJO (horizontal en sx, vertical en sy). Solo se
    # clampea la magnitud.
    def _cl(x):
        x = float(x)
        s = -1.0 if x < 0 else 1.0
        return s * max(0.05, min(20.0, abs(x)))
    sc = _cl(v.get("scale", 1.0) or 1.0)
    sx = _cl(v.get("sx") if v.get("sx") is not None else sc)
    sy = _cl(v.get("sy") if v.get("sy") is not None else sc)
    return {"dx": float(v.get("dx", 0.0) or 0.0), "dy": float(v.get("dy", 0.0) or 0.0),
            "rot": float(v.get("rot", 0.0) or 0.0), "scale": sc, "sx": sx, "sy": sy}


@app.get("/api/productos/editables")
def get_editables():
    pid = request.args.get("pid") or _get_active_producto_id()
    diseno = request.args.get("diseno") or "principal"
    sub = _diseno_sub(diseno)
    arte = _ruta_entrada("arte.ai", pid, sub=sub)
    objetos = []
    if os.path.exists(arte):
        try:
            objetos = MP.extraer_editables(arte)
        except Exception:
            objetos = []
    # mesa -> pieza (a qué pieza pertenece cada objeto, vía el mapeo del arte)
    mp = (_cargar("mapeo_arte.json", pid, sub=sub) or {}).get("mapeo", {})
    mesa2pieza = {int(v): k for k, v in mp.items() if v}
    reg = _cargar("registro_producto.json", pid) or {}
    talles = sorted({t for v in reg.values() for t in (v or {}).keys()})
    try:
        pl = _ruta_entrada("plantilla.ai", pid)
        if os.path.exists(pl):
            talles = MP.talles_orden_archivo(pl, talles) or talles
    except Exception:
        pass
    # ARTE POR RANGO (#talle/#rango): los objetos editables pueden vivir en mesas POR TALLE
    # (ej. "#1-16 Frente" = mesa 28), que NO figuran en el mapeo default (mesas del 1er rango).
    # Sin esta asociación quedaban sin pieza → el editor no los mostraba ("no se pueden editar").
    try:
        for _pz, _pt in (MP.mapeo_variantes_arte(arte, reg, talles) or {}).items():
            for _m in (_pt or {}).values():
                mesa2pieza.setdefault(int(_m), _pz)
    except Exception:
        pass
    prod = next((p for p in _cargar_catalogo()["productos"] if p["id"] == pid), None)
    # Config POR VARIABLE: los transforms de la variable pedida (v_xxx), con fallback a la base
    # compartida "*" (legacy). El editor edita una variable a la vez.
    variante = str(request.args.get("variante") or "*")
    _eds = (((prod or {}).get("editables") or {}).get(_slugify_diseno(diseno)) or {})
    cfg = _eds.get(variante) or _eds.get("*") or {}
    ref_talle = (prod or {}).get("variante_guia")
    # capas que agregó el usuario: son las únicas que se pueden volver a SACAR del arte. Se
    # calculan contra el arte ORIGINAL (no contra un registro, que puede desincronizarse).
    try:
        _inyectadas = OA.capas_agregadas(_ruta_entrada("arte.ai", pid, sub=sub, original=True))
    except Exception:
        _inyectadas = set()
    # ¿Cada capa admite cambio de COLOR? (relleno/trazo directo sí; XObject/imagen no, §10.b).
    try:
        _recol = MP.editables_recolorables(arte) if os.path.exists(arte) else {}
    except Exception:
        _recol = {}
    # UN ÍTEM POR CAPA: la capa "Editable …" ES el objeto editable — todo lo que tenga adentro se
    # mueve/rota/escala JUNTO (el agrupado de Illustrator no viaja en el .ai, así que la capa es la
    # unidad; ver §10.b). Su `bbox_mu`/`w_cm`/`h_cm` son los de la UNIÓN de sus figuras.
    # El COLOR sí es por FIGURA: van en `partes` [{obj_id, ident, label, color, recolorable, svg}]
    # y el editor deja elegir cuál pintar (cada una guarda con su IDENT "capa<SEP>obj_id").
    _expandido = []
    for o in objetos:
        pieza = mesa2pieza.get(o["mesa"], "")
        rp = reg.get(pieza) or {}
        pb = (rp.get(ref_talle) or next(iter(rp.values()), {})).get("bbox_mu")
        _obs = o.pop("objetos", None) or []                      # detalle interno → se reexpone como `partes`
        _entry = cfg.get(o["nombre"]) or {}
        _sub = _entry.get("objetos") or {}
        o["pieza"] = pieza
        o["label"] = o["nombre"]; o["obj_id"] = None
        o["quitable"] = o.get("capa") in _inyectadas
        o["transforms"] = _tf_de_capa(_entry)
        o["color"] = _entry.get("color")
        o["recolorable"] = bool(_recol.get(o.get("capa"), False)) or any(b.get("recolorable") for b in _obs)
        o["pos"] = _pos_en_pieza(o.get("mesa_rect"), o.get("bbox_mu"), pb)
        # COLOR de cada figura para ESTA variable (la de la capa vale de default para las que no
        # tengan el suyo) → {obj_id: (fill, stroke)}.
        _lay_c = _clamp_color(_entry.get("color"))
        _cols = {}
        for b in _obs:
            _c = _clamp_color((_sub.get(b["obj_id"]) or {}).get("color")) or _lay_c
            if _c:
                _cols[b["obj_id"]] = (_c.get("fill"), _c.get("stroke"))
        o["partes"] = [{
            "obj_id": b["obj_id"], "ident": _ident_obj(o["nombre"], b["obj_id"]),
            "label": f"{o['nombre']} ({i + 1})", "recolorable": bool(b.get("recolorable")),
            "color": (_sub.get(b["obj_id"]) or {}).get("color"), "fill": b.get("fill"),
            # miniatura de la figura CON su color (si tiene override); si no, la del arte
            "svg": (MP.svg_editable(arte, o["mesa"], o["capa"], b["bbox_mu"],
                                    colores=_cols, obj_id=b["obj_id"]) if _cols.get(b["obj_id"])
                    else b.get("svg")),
            "w_cm": b.get("w_cm"), "h_cm": b.get("h_cm"),
        } for i, b in enumerate(_obs)] if len(_obs) >= 2 else []
        # DIBUJO DEL OBJETO EN EL EDITOR: si alguna figura tiene color, se regenera el SVG de la
        # capa RECOLOREADO — el que trae `extraer_editables` es el del arte crudo y el cambio de
        # color no se veía en pantalla aunque la tizada sí lo tuviera (LEY arte=tizada). El `thumb`
        # (PNG del arte) se descarta: la lista lo prefiere al SVG y mostraría el color viejo.
        if _cols:
            _sv = MP.svg_editable(arte, o["mesa"], o["capa"], o["bbox_mu"], colores=_cols)
            if _sv:
                o["svg"] = _sv; o["thumb"] = None
        _expandido.append(o)
    objetos = _expandido
    # ── OBJETOS AGREGADOS: se devuelven con la MISMA FORMA que uno del arte ──────────────
    # (mesa_rect, bbox_mu, pos, w_cm/h_cm, svg base64, transforms). Así NINGUNA pantalla
    # necesita un caso especial: el editor, el overlay del Arte, el mapeador y el motor los
    # tratan igual que al escudo o al logo que ya vienen en el diseño. Antes se devolvían
    # incompletos y había que parchar vista por vista (y siempre faltaba alguna).
    #
    # Síntesis: el marco del objeto ES la pieza (mesa_rect con el aspecto de la pieza → awf=1)
    # y su bbox va CENTRADO con su medida real (w_cm/h_cm contra los cm de la pieza), que es
    # exactamente lo que calcula el motor (`_pos_agregado`).
    import base64 as _b64
    for _o in (_oa_cargar(pid, sub).get("objetos") or []):
        _pz = _o.get("pieza") or ""
        _svg = ""
        try:
            with open(os.path.join(OA.carpeta(DATOS, pid, sub), _o["archivo"]), "rb") as _fh:
                _svg = _b64.b64encode(OA.preview_svg(_fh.read()).encode("utf-8")).decode("ascii")
        except Exception:
            pass
        _tf = (_o.get("transforms") or {}).get(variante) or (_o.get("transforms") or {}).get("*") or {}
        objetos.append({
            "nombre": _o.get("nombre") or _o["id"], "capa": _o.get("nombre") or _o["id"],
            "pieza": _pz, "mesa": 0, "svg": _svg, "thumb": None,
            "w_cm": _o.get("w_cm"), "h_cm": _o.get("h_cm"),
            # El objeto se ubica DENTRO DEL DISEÑO (como cualquier editable del arte). NO se manda
            # `mesa_rect`: la mesa cambia por rango, así que la resuelve CADA VISTA con la del
            # talle que está mostrando (el editor con la suya, el visor del Arte con `mappedMesa`,
            # el motor con `arte_rect(_mesa_a)`). Mandar una mesa fija era la causa del corrimiento.
            "mesa_rect": None, "bbox_mu": None, "pos": None,
            "transforms": _tf, "agregado": True, "oid": _o["id"],
            # los agregados se componen como XObject (Do) → el color vive adentro, no recoloreable (§10.b)
            "color": None, "recolorable": False,
        })
    return jsonify({"objetos": objetos, "talles": talles, "piezas": sorted(reg.keys())})


@app.post("/api/productos/editables")
def set_editable():
    cuerpo = request.get_json(force=True)
    pid = cuerpo.get("pid") or _get_active_producto_id()
    diseno = cuerpo.get("diseno") or "principal"
    nombre = str(cuerpo.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"error": "falta nombre del objeto"}), 400
    # `talles` = alcance de VARIANTES/talles (una / rango / todas) ya resuelto por el front.
    talles = [str(t) for t in (cuerpo.get("talles") or []) if str(t)]
    # `variante` = la VARIABLE (v_xxx) sobre la que se edita → la posición se guarda POR VARIABLE.
    # "*" = compartida (sin variable, ej. front viejo).
    variante = str(cuerpo.get("variante") or "*").strip() or "*"
    tf = _clamp_tf(cuerpo.get("transform"))
    # El TRANSFORM es SIEMPRE de la CAPA: la capa "Editable …" es UN objeto y todo lo que tenga
    # adentro se mueve/rota/escala junto. Si viniera un IDENT por figura ("capa<SEP>obj_id", de un
    # front viejo) se le saca el obj_id y se guarda a nivel capa. El color sí es por figura.
    nombre, _oid_ignorado = _split_ident(nombre)
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if prod is None:
        return jsonify({"error": "molde no encontrado"}), 404
    eds = prod.setdefault("editables", {}).setdefault(_slugify_diseno(diseno), {}).setdefault(variante, {})
    obj = eds.setdefault(nombre, {"transforms": {}})
    obj.setdefault("transforms", {})
    for t in talles:
        obj["transforms"][t] = tf
    _guardar_catalogo(cat)
    return jsonify({"ok": True, "nombre": nombre, "transforms": obj["transforms"]})


@app.post("/api/productos/editable_color")
def set_editable_color():
    """Setea (o LIMPIA) el color override de un editable, POR VARIABLE, a NIVEL OBJETO (no por
    talle: el color es del objeto). Body: {pid?, diseno, nombre, variante, color}.
    `color` = {"fill":[c,m,y,k]|null, "stroke":[c,m,y,k]|null}; null/vacío = volver al color original.
    Se guarda junto a los transforms en prod["editables"][diseno][variable][nombre]["color"]."""
    cuerpo = request.get_json(force=True)
    pid = cuerpo.get("pid") or _get_active_producto_id()
    diseno = cuerpo.get("diseno") or "principal"
    nombre = str(cuerpo.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"error": "falta nombre del objeto"}), 400
    variante = str(cuerpo.get("variante") or "*").strip() or "*"
    color = _clamp_color(cuerpo.get("color"))
    capa_n, oid = _split_ident(nombre)
    oid = str(cuerpo.get("obj_id") or oid or "").strip() or None
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if prod is None:
        return jsonify({"error": "molde no encontrado"}), 404
    eds = prod.setdefault("editables", {}).setdefault(_slugify_diseno(diseno), {}).setdefault(variante, {})
    if oid:                                       # capa multi-objeto: color POR OBJETO (anidado)
        obj = eds.setdefault(capa_n, {}).setdefault("objetos", {}).setdefault(oid, {"transforms": {}})
    else:
        obj = eds.setdefault(nombre, {"transforms": {}})
    if color is None:
        obj.pop("color", None)                    # sin override = color original del diseño
    else:
        obj["color"] = color
    _guardar_catalogo(cat)
    return jsonify({"ok": True, "nombre": nombre, "color": obj.get("color")})


@app.get("/api/productos/editables_config")
def get_editables_config():
    """Config de TAMAÑO de capas editables del molde (general, por nombre de capa).
    Devuelve la lista registrada + las VARIANTES del molde (para el selector emergente)."""
    pid = request.args.get("pid") or _get_active_producto_id()
    prod = next((p for p in _cargar_catalogo()["productos"] if p["id"] == pid), None)
    cfg = ((prod or {}).get("editables_config") or {})
    items = []
    for key, c in cfg.items():
        items.append({"nombre": key, "capa": (c or {}).get("capa") or key,
                      "rangos": [{"variantes": list(r.get("variantes") or []),
                                  "mantener": bool(r.get("mantener")),
                                  "apaisado": r.get("apaisado") or {"ancho": "", "alto": ""},
                                  "vertical": r.get("vertical") or {"ancho": "", "alto": ""}}
                                 for r in ((c or {}).get("rangos") or [])]})
    return jsonify({"config": items, "variantes": _variantes_molde(pid)})


@app.post("/api/productos/editables_config")
def set_editables_config():
    """Guarda la config de tamaño del molde. Body:
    {pid, config:[{capa, rangos:[{variantes:[...], apaisado:{ancho,alto}, vertical:{ancho,alto}}]}]}.
    Se guarda por nombre de capa normalizado."""
    cuerpo = request.get_json(force=True)
    pid = cuerpo.get("pid") or _get_active_producto_id()
    items = cuerpo.get("config") or []
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if prod is None:
        return jsonify({"error": "molde no encontrado"}), 404
    validas = set(_variantes_molde(pid))

    def _caja(d):
        d = d or {}
        def _f(x):
            try:
                return round(max(0.0, float(x)), 3)
            except Exception:
                return 0.0
        return {"ancho": _f(d.get("ancho")), "alto": _f(d.get("alto"))}

    nuevo = {}
    for it in items:
        capa = str(it.get("capa") or "").strip()
        if not capa:
            continue
        key = MP._norm_nombre(MP._nombre_editable(capa))
        rangos = []
        for r in (it.get("rangos") or []):
            vs = [str(v) for v in (r.get("variantes") or []) if str(v) in validas]
            mantener = bool(r.get("mantener"))
            ap, ve = _caja(r.get("apaisado")), _caja(r.get("vertical"))
            if not vs or (not mantener and max(ap.values()) <= 0 and max(ve.values()) <= 0):
                continue
            rangos.append({"variantes": vs, "mantener": mantener, "apaisado": ap, "vertical": ve})
        nuevo[key] = {"capa": capa, "rangos": rangos}
    prod["editables_config"] = nuevo
    _guardar_catalogo(cat)
    return jsonify({"ok": True})


# ── OBJETOS AGREGADOS (PNG/SVG/PDF/AI que el usuario suma al editor) ──────────
# Cada objeto se normaliza a un PDF de 1 página + su tamaño en cm, y se guarda por producto+diseño.
# Aparece en el editor como un editable más y (etapa motor) se estampa en la tizada. El manifiesto
# vive en `objetos_agregados.json` del producto/diseño.
import objetos_agregados as OA


def _oa_manifest_path(pid, sub):
    return os.path.join(OA.carpeta(DATOS, pid, sub), "objetos_agregados.json")


def _oa_cargar(pid, sub):
    try:
        with open(_oa_manifest_path(pid, sub), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"objetos": []}


def _oa_guardar(pid, sub, data):
    with open(_oa_manifest_path(pid, sub), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _objetos_agregados_motor(pid, sub):
    """Para el motor: {dir, objetos:[...]} con los objetos agregados de este producto/diseño
    (id, archivo, pieza, w_cm, h_cm, transforms). None si no hay ninguno."""
    data = _oa_cargar(pid, sub)
    objs = data.get("objetos") or []
    if not objs:
        return None
    return {"dir": OA.carpeta(DATOS, pid, sub), "objetos": objs}


@app.post("/api/productos/objeto_agregar")
def objeto_agregar():
    f = request.files.get("archivo")
    if not f:
        return jsonify({"error": "falta el archivo"}), 400
    pid = request.form.get("pid") or _get_active_producto_id()
    sub = _diseno_sub(request.form.get("diseno"))
    nombre_vis = (request.form.get("nombre") or "").strip() or os.path.splitext(f.filename or "Objeto")[0]
    try:
        pdf_bytes, w_cm, h_cm, tipo = OA.normalizar_a_pdf(f.read(), f.filename or "")
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        return jsonify({"error": f"no se pudo leer el archivo: {e}"}), 422
    data = _oa_cargar(pid, sub)
    # id incremental estable dentro del producto/diseño
    oid = "oa_%d" % (1 + max([int(o["id"].split("_")[-1]) for o in data["objetos"] if o.get("id", "").startswith("oa_")] + [0]))
    carp = OA.carpeta(DATOS, pid, sub)
    with open(os.path.join(carp, oid + ".pdf"), "wb") as g:
        g.write(pdf_bytes)
    try:
        svg = OA.preview_svg(pdf_bytes)
    except Exception:
        svg = ""
    obj = {"id": oid, "nombre": nombre_vis, "archivo": oid + ".pdf",
           "w_cm": round(w_cm, 2), "h_cm": round(h_cm, 2), "tipo": tipo}
    data["objetos"].append(obj)
    _oa_guardar(pid, sub, data)
    return jsonify({"ok": True, "objeto": {**obj, "svg": svg}})


@app.get("/api/productos/objetos_agregados")
def objetos_agregados_listar():
    pid = request.args.get("pid") or _get_active_producto_id()
    sub = _diseno_sub(request.args.get("diseno"))
    data = _oa_cargar(pid, sub)
    carp = OA.carpeta(DATOS, pid, sub)
    salida = []
    for o in data.get("objetos", []):
        svg = ""
        try:
            with open(os.path.join(carp, o["archivo"]), "rb") as fh:
                svg = OA.preview_svg(fh.read())
        except Exception:
            pass
        salida.append({**o, "svg": svg})
    return jsonify({"ok": True, "objetos": salida})


@app.post("/api/productos/objeto_agregado/<oid>/transform")
def objeto_agregado_transform(oid):
    """Guarda el transform (mover/rotar/escalar/espejar) del objeto agregado, POR VARIABLE y talle.
    Estructura en el manifiesto: obj['transforms'][variante][talle] = {dx,dy,rot,scale,sx,sy}."""
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("pid") or _get_active_producto_id()
    sub = _diseno_sub(cuerpo.get("diseno"))
    variante = str(cuerpo.get("variante") or "*")
    talles = cuerpo.get("talles") or []
    tf = _clamp_tf(cuerpo.get("transform") or {})
    pieza = cuerpo.get("pieza")
    data = _oa_cargar(pid, sub)
    obj = next((o for o in data["objetos"] if o["id"] == oid), None)
    if not obj:
        return jsonify({"error": "no existe"}), 404
    tfs = obj.setdefault("transforms", {})
    porv = tfs.setdefault(variante, {})
    for t in (talles or ["*"]):
        porv[str(t)] = tf
    if pieza:
        obj["pieza"] = pieza          # a qué pieza quedó asignado el objeto
    _oa_guardar(pid, sub, data)
    return jsonify({"ok": True})


@app.post("/api/productos/objeto_agregado/<oid>/colocar")
def objeto_agregado_colocar(oid):
    """COLOCA el objeto en el diseño: lo INYECTA en el arte como capa `Editable <nombre>` en la
    mesa de esa pieza — en TODOS los rangos que use (igual que el arte trae el escudo repetido en
    la mesa de cada rango). Desde ahí es un editable del arte más: el editor, el visor y el motor
    lo tratan igual, sin código especial.

    Body: {pid, diseno, pieza, fx, fy} — `fx/fy` = punto clickeado en fracciones de la PIEZA
    (0..1, y hacia abajo), que se traduce a la posición equivalente dentro de cada mesa.
    """
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("pid") or _get_active_producto_id()
    diseno = cuerpo.get("diseno") or "principal"
    sub = _diseno_sub(diseno)
    pieza = str(cuerpo.get("pieza") or "")
    fx = float(cuerpo.get("fx", 0.5)); fy = float(cuerpo.get("fy", 0.5))
    arte = _ruta_entrada("arte.ai", pid, sub=sub)
    reg = _cargar("registro_producto.json", pid) or {}
    if not os.path.exists(arte) or pieza not in reg:
        return jsonify({"error": "falta el arte o la pieza"}), 409
    data = _oa_cargar(pid, sub)
    obj = next((o for o in data["objetos"] if o["id"] == oid), None)
    if not obj:
        return jsonify({"error": "no existe"}), 404

    # Mesas donde vive esa pieza: la del mapeo base + las de cada rango (arte por rango).
    mp = (_cargar("mapeo_arte.json", pid, sub=sub) or {}).get("mapeo", {})
    talles = sorted({t for v in reg.values() for t in (v or {}).keys()})
    # mesa -> talles de ESA mesa. Hace falta el talle para saber el ALTO de la pieza en ese rango:
    # el diseño se escala al alto de la pieza, así que el tamaño del objeto dentro de cada mesa
    # depende del rango. Usar un solo talle para todas daba el objeto de distinto tamaño por rango.
    mesa_talles = {}
    try:
        for _t, _m in ((MP.mapeo_variantes_arte(arte, reg, talles) or {}).get(pieza) or {}).items():
            mesa_talles.setdefault(int(_m), []).append(_t)
    except Exception:
        pass
    if mp.get(pieza):
        _mb = int(mp[pieza])
        # los talles que no tienen mesa propia caen a la del mapeo base
        _sin = [t for t in talles if t not in ((MP.mapeo_variantes_arte(arte, reg, talles) or {}).get(pieza) or {})]
        mesa_talles.setdefault(_mb, []).extend(_sin or [talles[0]] if talles else [])
    mesas = set(mesa_talles)
    if not mesas:
        return jsonify({"error": "esa pieza no tiene mesa de arte asignada"}), 409

    _errores = []
    ruta_obj = os.path.join(OA.carpeta(DATOS, pid, sub), obj["archivo"])
    with open(ruta_obj, "rb") as fh:
        pdf_obj = fh.read()
    ow, oh = float(obj.get("w_cm") or 0), float(obj.get("h_cm") or 0)
    colocaciones = []
    for mesa in sorted(mesas):
        try:
            _mr = MP.mesa_rect_arte(arte, mesa)
            if not _mr:
                continue
            ax0, ay0, aw, ah = _mr
            # ALTO de la pieza EN UN TALLE DE ESTA MESA: el diseño se escala al alto de la pieza,
            # así que este valor es el que hace que el objeto mida sus cm reales en ese rango.
            _tm = next((t for t in (mesa_talles.get(mesa) or []) if (reg.get(pieza) or {}).get(t)), None)
            _inf = ((reg.get(pieza) or {}).get(_tm) or next(iter((reg.get(pieza) or {}).values()), {})) or {}
            ph_cm = float(_inf.get("h_cm") or 0)
            if ph_cm <= 0:
                continue
            # tamaño del objeto DENTRO de la mesa, conservando su medida real
            bw = (ow / ((aw / ah) * ph_cm)) * aw if ow > 0 else aw * 0.3
            bh = (oh / ph_cm) * ah if oh > 0 else ah * 0.3
            # el click viene en fracción de la PIEZA; el diseño ocupa todo el alto y va centrado
            cx = ax0 + aw * 0.5 + (fx - 0.5) * aw
            cy_top = ay0 + ah * fy
            cy = (ay0 + ah) - cy_top + ay0          # y de página (hacia ARRIBA)
            colocaciones.append((mesa, (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)))
        except Exception as e:
            _errores.append(f"mesa {mesa}: {e}")
    if not colocaciones:
        # Se devuelve el motivo REAL (no un genérico): así el usuario ve qué pasó y no hay que
        # ir a buscarlo al log (que además puede estar bufferizado).
        return jsonify({"error": "No se pudo agregar al diseño. " + (" · ".join(_errores) or "sin detalle")}), 500
    # UNA sola pasada para todas las mesas → una sola versión nueva del arte
    try:
        capa, _nueva, _mesas_ok = OA.inyectar_editable(
            _ruta_entrada("arte.ai", pid, sub=sub, original=True),
            colocaciones, pdf_obj, obj.get("nombre") or oid)
    except Exception as e:
        return jsonify({"error": f"No se pudo agregar al diseño: {e}"}), 500
    capas = [{"mesa": m, "capa": capa} for m in _mesas_ok]
    # queda registrado que ESA capa la agregó el usuario: es la única que se puede volver a quitar
    # del arte (las que trae el .ai original no se tocan)
    data.setdefault("inyectadas", []).append(
        {"capa": capa, "nombre": obj.get("nombre"), "pieza": pieza, "mesas": _mesas_ok})
    # Ya vive DENTRO del arte: se saca del sistema paralelo (y su archivo suelto).
    data["objetos"] = [o for o in data["objetos"] if o["id"] != oid]
    _oa_guardar(pid, sub, data)
    try:
        os.remove(ruta_obj)
    except OSError:
        pass
    return jsonify({"ok": True, "capas": capas, "nombre": obj.get("nombre")})


@app.post("/api/productos/editable_quitar")
def editable_quitar():
    """SACA del arte un objeto que había agregado el usuario (contraparte de `colocar`): borra la
    capa `Editable <nombre>` y su contenido, escribiendo una versión nueva del arte.

    Sólo se pueden quitar las capas que agregó el usuario (registro `inyectadas`): las que trae el
    .ai original NO se tocan. Body: {pid, diseno, capa}."""
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("pid") or _get_active_producto_id()
    sub = _diseno_sub(cuerpo.get("diseno"))
    capa = str(cuerpo.get("capa") or "").strip()
    data = _oa_cargar(pid, sub)
    _base = _ruta_entrada("arte.ai", pid, sub=sub, original=True)
    if capa not in OA.capas_agregadas(_base):
        return jsonify({"error": "esa capa vino con el arte original: no se puede quitar desde acá"}), 409
    try:
        _, borrados = OA.quitar_editable(_base, capa)
    except Exception as e:
        return jsonify({"error": f"No se pudo quitar del diseño: {e}"}), 500
    data["inyectadas"] = [i for i in (data.get("inyectadas") or []) if i.get("capa") != capa]
    _oa_guardar(pid, sub, data)
    return jsonify({"ok": True, "capa": capa, "bloques": borrados})


@app.post("/api/productos/objeto_agregado/<oid>/pieza")
def objeto_agregado_pieza(oid):
    """Asigna el objeto a una pieza, o lo DESASIGNA (`pieza` vacía): sigue en la barra, listo
    para colocarlo en otra. Un objeto vive en UNA sola pieza — para tenerlo en dos, se duplica."""
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("pid") or _get_active_producto_id()
    sub = _diseno_sub(cuerpo.get("diseno"))
    data = _oa_cargar(pid, sub)
    obj = next((o for o in data["objetos"] if o["id"] == oid), None)
    if not obj:
        return jsonify({"error": "no existe"}), 404
    obj["pieza"] = str(cuerpo.get("pieza") or "")
    _oa_guardar(pid, sub, data)
    return jsonify({"ok": True, "pieza": obj["pieza"]})


@app.post("/api/productos/objeto_agregado/<oid>/duplicar")
def objeto_agregado_duplicar(oid):
    """Copia el objeto (archivo + entrada) para poder ponerlo en OTRA pieza. La copia nace SIN
    pieza (hay que colocarla) y conserva el transform del original como punto de partida."""
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("pid") or _get_active_producto_id()
    sub = _diseno_sub(cuerpo.get("diseno"))
    data = _oa_cargar(pid, sub)
    obj = next((o for o in data["objetos"] if o["id"] == oid), None)
    if not obj:
        return jsonify({"error": "no existe"}), 404
    carp = OA.carpeta(DATOS, pid, sub)
    nid = "oa_%d" % (1 + max([int(o["id"].split("_")[-1]) for o in data["objetos"] if o.get("id", "").startswith("oa_")] + [0]))
    try:
        import shutil
        shutil.copy2(os.path.join(carp, obj["archivo"]), os.path.join(carp, nid + ".pdf"))
    except Exception as e:
        return jsonify({"error": f"no se pudo duplicar: {e}"}), 500
    # nombre con sufijo para distinguirlo en la barra
    base = obj.get("nombre") or nid
    usados = {o.get("nombre") for o in data["objetos"]}
    nombre = base + " (copia)"
    k = 2
    while nombre in usados:
        nombre = f"{base} (copia {k})"; k += 1
    nuevo = {**obj, "id": nid, "archivo": nid + ".pdf", "nombre": nombre, "pieza": ""}
    data["objetos"].append(nuevo)
    _oa_guardar(pid, sub, data)
    svg = ""
    try:
        with open(os.path.join(carp, nuevo["archivo"]), "rb") as fh:
            svg = OA.preview_svg(fh.read())
    except Exception:
        pass
    return jsonify({"ok": True, "objeto": {**nuevo, "svg": svg}})


@app.delete("/api/productos/objeto_agregado/<oid>")
def objeto_agregado_borrar(oid):
    pid = request.args.get("pid") or _get_active_producto_id()
    sub = _diseno_sub(request.args.get("diseno"))
    data = _oa_cargar(pid, sub)
    obj = next((o for o in data["objetos"] if o["id"] == oid), None)
    if not obj:
        return jsonify({"error": "no existe"}), 404
    try:
        os.remove(os.path.join(OA.carpeta(DATOS, pid, sub), obj["archivo"]))
    except OSError:
        pass
    data["objetos"] = [o for o in data["objetos"] if o["id"] != oid]
    _oa_guardar(pid, sub, data)
    return jsonify({"ok": True})


# ── Perfiles ICC ─────────────────────────────────────────────────────────────
@app.get("/api/perfiles")
def listar_perfiles():
    perfiles = _listar_perfiles()
    defs = _perfil_default_cfg()
    return jsonify({
        "perfiles": perfiles,
        "cmyk": [p for p in perfiles if p["espacio"] == "CMYK"],
        "rgb": [p for p in perfiles if p["espacio"] == "RGB"],
        "otros": [p for p in perfiles if p["espacio"] not in ("CMYK", "RGB")],
        "config": defs,
        "hay_perfiles": bool(perfiles),
    })


@app.post("/api/perfiles/config")
def guardar_perfil_config():
    cuerpo = request.get_json(force=True)
    cat = _cargar_catalogo_para_editar()
    cfg = cat.get("perfil_cfg") or {}
    if cuerpo.get("cmyk"):
        cfg["cmyk"] = cuerpo["cmyk"]
    if cuerpo.get("rgb"):
        cfg["rgb"] = cuerpo["rgb"]
    cat["perfil_cfg"] = cfg
    _guardar_catalogo(cat)
    return jsonify({"ok": True, "config": _perfil_default_cfg(cat)})


@app.get("/api/arte/perfil")
def arte_perfil():
    """Detecta el perfil incrustado del arte recién subido (o de ese diseño) y
    devuelve el aviso (sin perfil / distinto / ok)."""
    sub = _diseno_sub(request.args.get("diseno"))
    arte = _ruta_entrada("arte.ai", sub=sub)
    if not os.path.exists(arte):
        return jsonify({"error": "no hay arte"}), 409
    return jsonify(_perfil_info(arte))


@app.post("/api/fuente")
def subir_fuente():
    f = request.files.get("archivo")
    if not f:
        return jsonify({"error": "falta el archivo"}), 400
    tmp = os.path.join(ENTRADA, "subida_" + f.filename)
    f.save(tmp)
    res = MP.alta_fuente(tmp, FUENTES)
    if not res["ok"]:
        return jsonify(res), 422
    # si había un arte validado con fuentes faltantes, revalidar (según el modo)
    prev = _cargar("validacion_arte.json") or {}
    if os.path.exists(_ruta_entrada("arte.ai")):
        if prev.get("modo") == "separado":
            reg = _cargar("registro_producto.json") or {}
            mp = (_cargar("mapeo_arte.json") or {}).get("mapeo", {})
            if reg and mp:
                val = MP.validar_arte_separado(_ruta_entrada("arte.ai"), reg, FUENTES,
                                               {k: int(v) for k, v in mp.items()}, _orden_var(reg))
                val["archivo"] = prev.get("archivo", "arte.ai")
                json.dump(val, open(_ruta_datos("validacion_arte.json"), "w", encoding="utf-8"), ensure_ascii=False)
        else:
            val = MP.validar_arte(_ruta_entrada("arte.ai"),
                                  _ruta_entrada("plantilla.ai"), FUENTES)
            val["archivo"] = prev.get("archivo", "arte.ai")
            json.dump(val, open(_ruta_datos("validacion_arte.json"), "w", encoding="utf-8"), ensure_ascii=False)
    res["catalogo"] = list(MP.catalogo_fuentes(FUENTES).values())
    return jsonify(res)


@app.get("/api/fuente/archivo/<path:nombre>")
def fuente_archivo(nombre):
    """Sirve el .ttf/.otf del catálogo para que el navegador lo dibuje (@font-face) en las
    tarjetas del catálogo. Sin esto la vista previa mostraría una tipografía cualquiera."""
    # Solo un archivo de fuente DENTRO del catálogo: basename corta cualquier "../" y después
    # se compara la ruta ya resuelta contra FUENTES (defensa por si el nombre trae symlinks).
    base = os.path.basename(nombre or "")
    if not base.lower().endswith((".ttf", ".otf")):
        return jsonify({"error": "no es una fuente"}), 400
    ruta = os.path.realpath(os.path.join(FUENTES, base))
    if os.path.dirname(ruta) != os.path.realpath(FUENTES) or not os.path.exists(ruta):
        return jsonify({"error": "no existe"}), 404
    return send_file(ruta, mimetype="font/ttf" if base.lower().endswith(".ttf") else "font/otf",
                     max_age=86400)   # el archivo no cambia (mismo nombre = misma fuente)


# Juegos de caracteres de REFERENCIA: lo que una fuente debería tener para este sistema
# (nombres y números de camiseta). Lo que falte de acá se marca como faltante.
_SETS_REF = [
    ("Mayúsculas", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    ("Minúsculas", "abcdefghijklmnopqrstuvwxyz"),
    ("Números", "0123456789"),
    ("Español", "ÁÉÍÓÚÜÑáéíóúüñ¿¡"),
    ("Signos", ".,;:!?'\"/%&()@#-+=*_"),
]


@app.get("/api/fuente/glifos/<path:nombre>")
def fuente_glifos(nombre):
    """Qué caracteres TIENE y cuáles le FALTAN a una fuente del catálogo.
    'Tiene' = el contorno se puede dibujar de verdad (estar en el cmap no alcanza: puede estar
    mapeado y tener los datos corruptos, como el '#' de la Hawken)."""
    base = os.path.basename(nombre or "")
    if not base.lower().endswith((".ttf", ".otf")):
        return jsonify({"error": "no es una fuente"}), 400
    ruta = os.path.realpath(os.path.join(FUENTES, base))
    if os.path.dirname(ruta) != os.path.realpath(FUENTES) or not os.path.exists(ruta):
        return jsonify({"error": "no existe"}), 404
    try:
        from texto_curvas import FuenteCurvas
        with open(ruta, "rb") as fh:
            fc = FuenteCurvas(fh.read())
    except Exception as e:
        return jsonify({"error": f"no se pudo leer la fuente: {e}"}), 422

    usados = set()
    grupos = []
    for titulo, chars in _SETS_REF:
        celdas = []
        for ch in chars:
            usados.add(ch)
            celdas.append({"ch": ch, "tiene": _dibuja(fc, ord(ch))})
        grupos.append({"titulo": titulo, "celdas": celdas,
                       "faltan": sum(1 for c in celdas if not c["tiene"])})
    # Todo lo demás que la fuente trae y no está en los juegos de referencia (bonus).
    otros = []
    for cp in sorted(fc.cmap.keys()):
        ch = chr(cp)
        if ch in usados or not ch.isprintable() or ch.isspace():
            continue
        if _dibuja(fc, cp):
            otros.append({"ch": ch, "tiene": True})
    if otros:
        grupos.append({"titulo": "Otros que trae", "celdas": otros, "faltan": 0})

    interno = (MP.catalogo_fuentes(FUENTES).get(ruta) or {}).get("interno", "")
    faltan_total = sum(g["faltan"] for g in grupos)
    return jsonify({"ok": True, "archivo": base, "interno": interno, "grupos": grupos,
                    "total_cmap": len(fc.cmap), "faltan": faltan_total})


@app.delete("/api/fuente/archivo/<path:nombre>")
def borrar_fuente(nombre):
    """Saca una tipografía del catálogo. Ojo: si algún arte la usa, ese arte va a quedar sin
    fuente (se avisa al validar) — por eso el front pide confirmación antes."""
    base = os.path.basename(nombre or "")
    if not base.lower().endswith((".ttf", ".otf")):
        return jsonify({"error": "no es una fuente"}), 400
    ruta = os.path.realpath(os.path.join(FUENTES, base))
    if os.path.dirname(ruta) != os.path.realpath(FUENTES) or not os.path.exists(ruta):
        return jsonify({"error": "no existe"}), 404
    try:
        os.remove(ruta)
    except Exception as e:
        return jsonify({"error": f"no se pudo eliminar: {e}"}), 500
    return jsonify({"ok": True, "catalogo": list(MP.catalogo_fuentes(FUENTES).values())})


def _config_default():
    # mesas de trabajo (telas): cada una con su ancho/alto. Las piezas se asignan
    # a una tela; cada tela arma su propia hoja.
    return {"mesas": [{"nombre": "Principal", "ancho_m": 1.8, "alto_max_m": 5.0},
                      {"nombre": "RIB", "ancho_m": 1.0, "alto_max_m": 5.0}],
            "asignacion": {}, "espaciado_mm": 5.0, "margen_mm": 10.0, "rotacion": "auto"}


@app.get("/api/config")
def get_config():
    conf = _cargar("config_produccion.json") or _config_default()
    conf.setdefault("asignacion", {})
    reg = _cargar("registro_producto.json") or {}
    conf["piezas"] = sorted(reg.keys())
    return jsonify(conf)


@app.post("/api/config")
def set_config():
    c = request.get_json(force=True) or {}
    rot = str(c.get("rotacion", "auto") or "auto")
    limpio = {"espaciado_mm": max(0.0, float(c.get("espaciado_mm", 5) or 0)),
              "margen_mm": max(0.0, float(c.get("margen_mm", 10) or 0)),
              "rotacion": rot if rot in ("auto", "ninguna", "90", "180", "libre") else "auto",
              "mesas": [], "asignacion": {}}
    for m in c.get("mesas", []):
        try:
            nom = str(m["nombre"]).strip()
            if not nom:
                continue
            limpio["mesas"].append({"nombre": nom,
                                    "ancho_m": round(float(m["ancho_m"]), 3),
                                    "alto_max_m": round(float(m["alto_max_m"]), 3)})
        except Exception:
            pass
    nombres = {m["nombre"] for m in limpio["mesas"]}
    limpio["asignacion"] = {str(p): str(t) for p, t in (c.get("asignacion") or {}).items()
                            if t and str(t) in nombres}
    json.dump(limpio, open(_ruta_datos("config_produccion.json"), "w", encoding="utf-8"), ensure_ascii=False)
    return jsonify(limpio)


# ═════════════════ TELAS (registro GLOBAL + grupos combinables) ═════════════════
# TELAS — YA NO se crean acá: vienen de la API EXTERNA del WMS (stock). De nuestro lado sólo se pone
# el ANCHO (cm) por tela (la API lo trae dentro del texto, inconsistente). El catálogo local guarda:
#   cat["telas_ancho"] = {str(id_api): ancho_cm}   ← lo ÚNICO que edita el usuario
#   cat["telas"]        = último fetch mergeado {id,nombre,ancho_cm,codigo,moneda,precio}  ← cache/offline
# `_config_produccion` lee cat["telas"] → la generación anda aun sin red. La api-key vive en
# config_externo.json (NO versionado) o en la env EXTERNAL_API_KEY. Los GRUPOS combinables siguen.
_TELAS_MEM = {"ts": 0.0, "data": None}     # cache en memoria del fetch (evita pegarle a la API en cada request)
_TELAS_TTL = 300                            # segundos
_UA_TELAS = "TIZADAPRO/1.0"                 # Cloudflare bloquea el UA por defecto de Python (ver _UA_PUB)


def _config_externo():
    """(url, key) de la API de telas. Prioridad: env EXTERNAL_TELAS_URL/EXTERNAL_API_KEY; si no,
    config_externo.json (no versionado). Nunca hardcodeado en el repo."""
    url = os.environ.get("EXTERNAL_TELAS_URL")
    key = os.environ.get("EXTERNAL_API_KEY")
    if not (url and key):
        try:
            cfg = json.load(open(os.path.join(AQUI, "config_externo.json"), encoding="utf-8"))
            url = url or cfg.get("telas_api_url")
            key = key or cfg.get("telas_api_key")
        except Exception:
            pass
    return (url or "https://user.com.uy/api/external/telas"), key


def _guard_sesion_telas():
    """SEGURIDAD: los datos de telas vienen del WMS (nombres, códigos, PRECIOS) → no se re-publican a
    quien no esté logueado. Devuelve una respuesta 401 si no hay sesión, o None si puede pasar.
    Dentro de TIZADA las telas son para TODOS los usuarios (cualquier sesión vale); esto sólo corta a
    los EXTERNOS sin login. Si el sistema de usuarios no está registrado (taller sin base), no se puede
    exigir sesión y se deja pasar — mismo criterio que el resto del server (la seguridad no lo tumba)."""
    if not _USUARIOS_ON:
        return None
    try:
        if _usuario_actual():
            return None
    except Exception:
        return None
    return jsonify({"error": "no hay sesión iniciada"}), 401


# HOSTS a los que se permite mandar la api-key. SEGURIDAD: aunque alguien logre cambiar la URL
# (endpoint de conexión), la key NUNCA se envía a un host fuera de esta lista → evita que un atacante
# apunte la URL a su servidor y capture la key en el header. Ampliá acá si cambia el dominio del WMS.
_HOSTS_TELAS_OK = {"user.com.uy", "www.user.com.uy", "localhost", "127.0.0.1"}


def _host_permitido(url):
    try:
        import urllib.parse
        return (urllib.parse.urlparse(str(url or "")).hostname or "").lower() in _HOSTS_TELAS_OK
    except Exception:
        return False


def _ancho_de_descripcion(desc):
    """Mejor esfuerzo: saca el ancho (cm) del texto ('(1,60)', '1,68 m', 'Parisien 1,60'…). None si no hay."""
    m = re.search(r'(\d+)[.,](\d{1,2})', str(desc or ""))
    if not m:
        return None
    try:
        val = float(m.group(1) + "." + m.group(2))
        return round(val * 100.0, 1) if val < 10 else round(val, 1)   # metros→cm (heurística)
    except Exception:
        return None


def _fetch_telas_externas():
    """GET a la API externa del WMS. Devuelve (telas|None, error|None). UA custom (Cloudflare)."""
    url, key = _config_externo()
    if not key:
        return None, "falta la api-key (config_externo.json o env EXTERNAL_API_KEY)"
    if not _host_permitido(url):     # SEGURIDAD: no mandar la key a un host desconocido
        return None, "host de la API no permitido (no se envía la clave)"
    try:
        import urllib.request
        rq = urllib.request.Request(url, headers={"x-api-key": key, "User-Agent": _UA_TELAS, "Accept": "application/json"})
        # Timeout CORTO a propósito: si el servidor no puede salir a internet, hay que contestar el
        # error (JSON) ANTES de que el proxy de adelante corte la espera y devuelva su 502/504 en
        # HTML — que en el navegador aparecía como «Unexpected token '<'» sin explicar nada.
        with urllib.request.urlopen(rq, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8"))
        arr = data.get("data") if isinstance(data, dict) else data
        telas = []
        for t in (arr or []):
            _desc = str(t.get("descripcion") or t.get("id") or "").strip()
            telas.append({"id": str(t.get("id")), "nombre": _desc,
                          "codigo": str(t.get("codigoArticulo") or ""), "moneda": t.get("moneda"), "precio": t.get("precioBase"),
                          "medida_cm": _ancho_de_descripcion(_desc)})   # ancho de la TELA que informa el sistema (de la descripción)
        return telas, None
    except Exception as e:
        return None, str(e)


def _telas_merge(cat, telas_api):
    """Dos anchos por tela:
      `medida_cm` = ancho de la TELA que informa el sistema (parseado de la descripción; informativo).
      `ancho_cm`  = ANCHO DE IMPRESIÓN que usa la TIZADA (editable local en cat['telas_ancho']).
    Default del ancho de impresión = la medida del sistema (o 180 si no se pudo leer), y el usuario lo
    ajusta a lo que realmente imprime (suele ser menor que el rollo por orillos/márgenes)."""
    anchos = cat.get("telas_ancho") or {}
    out = []
    for t in telas_api:
        med = t.get("medida_cm")
        if med is None:
            med = _ancho_de_descripcion(t.get("nombre"))
        ov = anchos.get(str(t["id"]))
        ancho = float(ov) if ov is not None else float(med if med is not None else 180.0)
        out.append({**t, "medida_cm": med, "ancho_cm": ancho})
    return out


def _telas_efectivas(cat, forzar=False):
    """Telas para usar = API + ancho local. Cache en memoria (TTL) + persistencia en cat['telas'] para
    que la generación (lee cat['telas']) y la UI anden aun sin red / sin re-fetch."""
    now = time.time()
    if forzar or _TELAS_MEM["data"] is None or (now - _TELAS_MEM["ts"] > _TELAS_TTL):
        telas_api, _err = _fetch_telas_externas()
        if telas_api is not None:
            _TELAS_MEM["data"] = telas_api
            _TELAS_MEM["ts"] = now
    telas_api = _TELAS_MEM["data"]
    if telas_api is None:                       # sin red y sin cache → lo último persistido en cat['telas']
        return list(cat.get("telas") or [])
    merged = _telas_merge(cat, telas_api)
    if merged != (cat.get("telas") or []):      # persistir sólo si cambió
        cat["telas"] = merged
        # Persistencia MÍNIMA y bajo candado: se recarga el catálogo fresco y se toca SÓLO
        # `telas`. Guardar el `cat` que trajo el llamador pisaría cualquier cambio de
        # configuración hecho mientras tanto — este `cat` se leyó ANTES de la consulta HTTP a la
        # API de telas, que puede tardar (y hasta agotar su timeout). Por eso tampoco se toma el
        # candado durante esa consulta: la sección crítica es sólo el guardado. Ver 171.A.
        with _LOCK_CAT_EDICION:
            _cat = _cargar_catalogo()
            _cat["telas"] = merged
            _guardar_catalogo(_cat)
    return merged


@app.get("/api/telas")
def get_telas():
    _g = _guard_sesion_telas()
    if _g:
        return _g
    cat = _cargar_catalogo()
    return jsonify({"telas": _telas_efectivas(cat), "grupos": cat.get("grupos_telas", [])})


@app.post("/api/telas/refrescar")
def refrescar_telas():
    """Fuerza re-consulta a la API externa (botón «Actualizar telas del sistema»)."""
    _g = _guard_sesion_telas()
    if _g:
        return _g
    cat = _cargar_catalogo()
    telas_api, err = _fetch_telas_externas()
    if telas_api is None:
        return jsonify({"error": f"No se pudo consultar la API de telas: {err}"}), 502
    _TELAS_MEM["data"] = telas_api
    _TELAS_MEM["ts"] = time.time()
    return jsonify({"telas": _telas_efectivas(cat, forzar=False), "grupos": cat.get("grupos_telas", []), "count": len(telas_api)})


@app.post("/api/telas/ancho")
def set_tela_ancho():
    """Guarda el ANCHO (cm) local de una tela de la API. Es lo único editable de nuestro lado."""
    _g = _guard_sesion_telas()
    if _g:
        return _g
    cuerpo = request.get_json(force=True) or {}
    tid = str(cuerpo.get("id") or "").strip()
    if not tid:
        return jsonify({"error": "falta id"}), 400
    ancho = max(1.0, float(cuerpo.get("ancho_cm", 180) or 180))
    cat = _cargar_catalogo_para_editar()
    anchos = cat.get("telas_ancho") or {}
    anchos[tid] = ancho
    cat["telas_ancho"] = anchos
    for t in (cat.get("telas") or []):          # reflejar en la tela cacheada
        if str(t.get("id")) == tid:
            t["ancho_cm"] = ancho
    _guardar_catalogo(cat)
    return jsonify({"ok": True, "id": tid, "ancho_cm": ancho})


@app.get("/api/telas/conexion")
def get_telas_conexion():
    """Estado de la conexión con la API del sistema. NO devuelve la key (sólo si está o no)."""
    _g = _guard_sesion_telas()
    if _g:
        return _g
    url, key = _config_externo()
    return jsonify({"url": url, "tiene_key": bool(key),
                    "por_env": bool(os.environ.get("EXTERNAL_API_KEY"))})


# NO hay endpoint para ESCRIBIR la conexión: la api-key se configura en `config_externo.json` (o en
# la env `EXTERNAL_API_KEY`) y viaja con el paquete de publicación (ver empaquetar.py). Se quitó a
# propósito — sin pantalla que lo use, un POST que escribe la clave y la URL es superficie de ataque
# al pedo (era el que había que blindar con la allowlist de hosts). El GET de arriba sólo informa.


@app.post("/api/telas")
def set_telas():
    """Ya NO crea telas (vienen de la API). Sólo administra los GRUPOS combinables."""
    _g = _guard_sesion_telas()
    if _g:
        return _g
    cuerpo = request.get_json(force=True) or {}
    cat = _cargar_catalogo_para_editar()
    if isinstance(cuerpo.get("grupos"), list):
        grupos = []
        for g in cuerpo["grupos"]:
            grupos.append({"id": g.get("id") or ("gt_" + uuid.uuid4().hex[:8]),
                           "nombre": str(g.get("nombre", "")).strip() or "Grupo",
                           "telas": [str(x) for x in (g.get("telas") or [])]})
        cat["grupos_telas"] = grupos
        _guardar_catalogo(cat)
    return jsonify({"telas": _telas_efectivas(cat), "grupos": cat.get("grupos_telas", [])})


# TELAS DISPONIBLES POR PIEZA (config del molde). Modelo:
#   prod["telas_cfg"] = {"todas": [telaId…],                 ← disponibles en TODAS las piezas
#                        "por_pieza": {"Frente": [telaId…]}} ← telas EXTRA sólo para esas piezas
# Disponible en una pieza = `todas` ∪ `por_pieza[pieza]`. Ej.: 10 telas a todas + 2 extra en 3 piezas
# → esas 3 piezas ofrecen 12 y el resto 10. Las claves son el nombre GENÉRICO de la pieza (sin el
# número final), igual que la asignación de tela del pedido.
# COMPAT: los moldes viejos tienen `telas_asignadas` (lista plana) → se lee como `todas`.
# `max_var` = {clave_variable: N} → TOPE de telas distintas que se pueden dejar disponibles para esa
# variable (límite de la CONFIG, no del pedido). Sin entrada = sin tope.
def _telas_cfg_prod(prod):
    """Config de telas del molde, normalizada. Nunca revienta con datos viejos."""
    tc = (prod or {}).get("telas_cfg")
    if isinstance(tc, dict):
        mv = {}
        for k, v in (tc.get("max_var") or {}).items():
            try:
                n = int(v)
            except (TypeError, ValueError):
                continue
            if n > 0:
                mv[str(k)] = n
        return {"todas": [str(x) for x in (tc.get("todas") or [])],
                "por_pieza": {str(k): [str(x) for x in (v or [])]
                              for k, v in (tc.get("por_pieza") or {}).items() if v},
                "max_var": mv}
    return {"todas": [str(x) for x in ((prod or {}).get("telas_asignadas") or [])], "por_pieza": {}, "max_var": {}}


@app.post("/api/productos/telas_asignadas")
def set_telas_asignadas():
    """Telas (ids del registro global) disponibles para ESTE molde.
    Cuerpo nuevo: {id, todas:[…], por_pieza:{pieza:[…]}}. Cuerpo viejo: {id, telas:[…]} (= `todas`)."""
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("id")
    _no = _guard_id(cuerpo)
    if _no: return _no          # molde de otro usuario
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if not prod:
        return jsonify({"error": "Producto no encontrado"}), 404
    _prev = _telas_cfg_prod(prod)          # lo que ya había (para no perder lo que no venga en el cuerpo)
    if "todas" in cuerpo or "por_pieza" in cuerpo:
        todas = [str(t) for t in (cuerpo.get("todas") or [])]
        _st = set(todas)
        por = {}
        for k, v in (cuerpo.get("por_pieza") or {}).items():
            # lo que ya está en `todas` no se repite como extra de la pieza
            ids = [str(t) for t in (v or []) if str(t) not in _st]
            if ids:
                por[str(k)] = ids
        prod["telas_cfg"] = {"todas": todas, "por_pieza": por, "max_var": _prev["max_var"]}
    elif "telas" in cuerpo:                        # forma vieja: una sola lista para todo el molde
        prod["telas_cfg"] = {"todas": [str(t) for t in (cuerpo.get("telas") or [])], "por_pieza": {}, "max_var": _prev["max_var"]}
    else:                                          # sólo vino el tope → se conserva el resto
        prod["telas_cfg"] = dict(_prev)
    # TOPE por variable (opcional en el cuerpo): {clave: N}. N<=0 o vacío = sin tope (se borra).
    if isinstance(cuerpo.get("max_var"), dict):
        mv = {}
        for k, v in cuerpo["max_var"].items():
            try:
                n = int(v)
            except (TypeError, ValueError):
                continue
            if n > 0:
                mv[str(k)] = n
        prod["telas_cfg"]["max_var"] = mv
    # `telas_asignadas` se mantiene como la UNIÓN plana: lo que ya lee el resto del sistema
    # (pedido/arte) sigue funcionando sin cambios mientras se migra.
    cfg = prod["telas_cfg"]
    prod["telas_asignadas"] = list(dict.fromkeys(cfg["todas"] + [t for ids in cfg["por_pieza"].values() for t in ids]))
    _guardar_catalogo(cat)
    return jsonify({"ok": True, "telas_cfg": cfg, "telas_asignadas": prod["telas_asignadas"]})


# ALTO MÁXIMO DE UNA MESA, EN CM.
# El PDF no admite páginas de más de 14400 unidades por lado (200 pulgadas = 508 cm), pero desde
# PDF 1.6 existe **/UserUnit**: cada unidad puede valer más de un punto, y así la mesa crece sin
# romper el formato. `componer_pdf_contorno` lo aplica solo cuando hace falta.
# ⚠️ Depende de que el RIP lo respete. **Verificado con el RIP del usuario (2026-07-30): carga una
# hoja de 10 m y la reporta como 10 m** (probado también en Illustrator). Si algún día se cambia de
# RIP, hay que repetir la prueba: si lo ignora, imprime a 1/UserUnit de escala.
ALTO_MESA_MAX_CM = 5000.0     # 50 m


def _config_produccion(pid=None):
    """Traduce la config a los parámetros del motor: (config_nesting global,
    rotaciones por pieza, telas_cfg por tela, asignación pieza→tela).
    TELAS: el registro es GLOBAL (catálogo `telas` = nombre + ancho). El ALTO de la
    hoja/tizada viene de la config de nesting (`alto_max_cm` del preset). La asignación
    pieza→tela ya NO vive en el config del molde: viene del PEDIDO (override por pieza)."""
    conf = _cargar("config_produccion.json", pid) or _config_default()
    espaciado_mm = conf.get("espaciado_mm", 5)
    margen_mm = conf.get("margen_mm", 10)
    rot = conf.get("rotacion", "auto")
    alto_max_cm = 500.0
    cat = _cargar_catalogo()
    prod = next((p for p in cat.get("productos", []) if p["id"] == (pid or _get_active_producto_id())), None)
    try:
        # Si el molde no tiene preset asignado, usa el DEFAULT (Estándar).
        _pid = (prod or {}).get("nesting_preset_id") or "nesting_default"
        preset = next((n for n in cat.get("nesting_presets", []) if n.get("id") == _pid), None)
        if preset:
            espaciado_mm = preset.get("espaciado_mm", espaciado_mm)
            margen_mm = preset.get("margen_mm", margen_mm)
            rot = preset.get("rotacion", rot)
            # Se acota también al LEER: los presets guardados antes de este tope pueden tener 8 m,
            # y el resumen de la pantalla mostraría un número que el nesting no respeta.
            alto_max_cm = min(ALTO_MESA_MAX_CM, float(preset.get("alto_max_cm", alto_max_cm) or alto_max_cm))
    except Exception:
        pass
    margen_cm = float(margen_mm) / 10.0
    base = {"espaciado_cm": float(espaciado_mm) / 10.0,
            "margenes_cm": {"sup": margen_cm, "inf": margen_cm,
                            "izq": margen_cm, "der": margen_cm}}
    # TELAS del registro GLOBAL (nombre + ancho); el alto de la hoja lo pone la tizada (nesting).
    telas_cfg = {}
    for t in (cat.get("telas") or []):
        nom = str(t.get("nombre", "")).strip()
        if nom:
            telas_cfg[nom] = {"ancho_cm": float(t.get("ancho_cm", 180) or 180), "altura_max_cm": alto_max_cm}
    # Defaults por compatibilidad con el fallback hardcodeado del motor (Principal/RIB).
    telas_cfg.setdefault("Principal", {"ancho_cm": 180.0, "altura_max_cm": alto_max_cm})
    telas_cfg.setdefault("RIB", {"ancho_cm": 100.0, "altura_max_cm": alto_max_cm})
    asignacion = {}   # la asignación pieza→tela viene del PEDIDO (ver _asignacion_tela_pedido)
    rotaciones = {}
    if rot and rot not in ("auto", ""):
        reg = _cargar("registro_producto.json", pid) or {}
        rotaciones = {p: rot for p in reg}
    return base, rotaciones, telas_cfg, asignacion


def _traducir_prendas(prendas, prod, cat, default_diseno="principal", reg=None, var_por_diseno=None):
    """Traduce las filas crudas de la planilla a las prendas que entiende el motor
    (talle/nombre/numero/manga + personalización por columna), según el template y
    el mapeo de columnas del molde. `default_diseno` = diseño de la fila cuando no
    hay columna "Diseño" (pedido de un solo diseño).

    `var_por_diseno` = {slug_del_espacio: clave_de_variable} **para ESTE molde**. La fila sólo
    puede traer UNA `__variante`, así que cuando un espacio del pedido usa dos moldes, la variable
    que viaja en la fila es la de uno solo: para el otro, la fila llegaba SIN variable y el motor
    generaba TODAS sus piezas (y la etiqueta caía a la posición por defecto). Con este mapa, cada
    molde recupera la variable que ese espacio eligió PARA ÉL en el paso 1."""
    mapeo_columnas = {"talle": "talle", "nombre": "nombre", "numero": "numero",
                      "manga": "manga", "manga_corta_val": "corta", "manga_larga_val": "larga"}
    if prod and "mapeo_columnas" in prod:
        mapeo_columnas.update(prod["mapeo_columnas"])
    _tpl = next((t for t in cat.get("plantillas_planillas", []) if t.get("id") == (prod or {}).get("planilla_template_id")), None)
    cols_template = (_tpl or {}).get("columnas", [])
    talle_col = mapeo_columnas.get("talle", "talle")
    nombre_col = mapeo_columnas.get("nombre", "nombre")
    numero_col = mapeo_columnas.get("numero", "numero")
    manga_col = mapeo_columnas.get("manga", "manga")
    larga_val = str(mapeo_columnas.get("manga_larga_val", "larga")).strip().lower()
    # TOGGLES DE PIEZA (generaliza la manga): TODAS las columnas con comportamiento
    # "manga" (role="manga"). Cada una aporta una palabra CLAVE (ej. 'manga', 'sisa') y
    # sus OPCIONES; el valor de la fila dice qué opción se eligió. Puede haber varias.
    toggle_cols = _toggles_de_template(cols_template, cat)
    # Columna que elige el DISEÑO de cada fila (comportamiento "diseno"). Si no
    # existe, todas las filas van al diseño "principal" (el arte base de hoy).
    diseno_col = next((c for c in cols_template if c.get("role") == "diseno"), None)
    # VARIABLES de configuración del molde (pestaña Variables).
    # Cada fila puede traer `__variante` = clave elegida → el motor genera SOLO esas piezas.
    # IDENTIDAD ESTABLE: `piezas.json` mapea el `pieza_id` (que NO varía por talle) a la CLAVE
    # de la pieza en el registro. La variable apunta al id → resolvemos a clave sin depender del
    # talle guía. `pieza_idx` queda como fallback para moldes aún no migrados.
    _pid = (prod or {}).get("id")
    _pz_idx = _cargar("piezas.json", _pid) if _pid else None
    _id2clave = {}
    if _pz_idx:
        for _p in _pz_idx.get("piezas", []):
            if _p.get("id") and _p.get("clave"):
                _id2clave[_p["id"]] = _p["clave"]
    variantes_prod = {}      # clave -> [pieza_idx]  (compat / fallback)
    variantes_piezas = {}    # clave -> [clave_pieza]  (ESTABLE, resuelto por pieza_id)
    variantes_grupo = {}     # clave -> grupoId (para acotar la config de etiqueta al grupo)
    variantes_juntas = {}    # clave -> [[clave_pieza,…], …]  vínculos "van juntas" (manga corta + su vivo)
    for _v in ((prod or {}).get("variantes") or []):
        _cl = _v.get("clave")
        if not _cl:
            continue
        variantes_grupo[_cl] = _v.get("grupoId")
        _idxs, _claves, _idx2cl_v = [], [], {}
        for x in (_v.get("valores") or []):
            _clp = _id2clave.get(x.get("pieza_id"))
            if _clp:
                _claves.append(_clp)
            if x.get("pieza_idx") is not None:
                _idxs.append(x["pieza_idx"])
                if _clp:
                    _idx2cl_v[int(x["pieza_idx"])] = _clp
        # Vínculos "van juntas" de ESTA variable → sets de CLAVES de registro (el motor los trata
        # como unidad frente al toggle: si saca la manga, saca también el vivo enlazado).
        _js = []
        for _b in (_v.get("juntas") or []):
            _nm = [_idx2cl_v[int(i)] for i in (_b.get("piezas") or []) if int(i) in _idx2cl_v]
            if len(_nm) >= 2:
                _js.append(_nm)
        if _js:
            variantes_juntas[_cl] = _js
        if _idxs:
            variantes_prod[_cl] = _idxs
        if _claves:
            variantes_piezas[_cl] = _claves
    # FALLBACK: pieza_idx → NOMBRE resuelto en el TALLE GUÍA (solo si la variable no tiene pieza_id).
    # El pieza_idx VARÍA por talle; la variable guarda los del talle guía → resolver con otro talle
    # da piezas equivocadas. Con pieza_id ya no hace falta, pero se conserva para datos viejos.
    _guia = (prod or {}).get("variante_guia")
    _idx2nom_guia = {}
    if reg and _guia:
        for _nm, _pt in reg.items():
            _info = (_pt or {}).get(_guia)
            if isinstance(_info, dict) and _info.get("pieza_idx") is not None:
                _idx2nom_guia[int(_info["pieza_idx"])] = _nm
    out = []
    for pr in prendas:
        manga_final = "larga" if str(pr.get(manga_col, "")).strip().lower() == larga_val else "corta"
        toggles = []
        for ti in toggle_cols:
            c = ti["col"]
            val = str(pr.get(c.get("id"), pr.get(c.get("label"), "")) or "").strip()
            opcion = val or (ti["opciones"][0] if ti["opciones"] else "")   # vacío → primera opción
            if opcion:
                toggles.append({"clave": ti["clave"], "opcion": opcion, "opciones": ti["opciones"]})
        translated_pr = {
            "talle": pr.get(talle_col, "") or pr.get("talle", "") or pr.get("Talle", "") or "M",
            "nombre": pr.get(nombre_col, "") or pr.get("nombre", "") or pr.get("Nombre", "") or "",
            "numero": pr.get(numero_col, "") or pr.get("numero", "") or pr.get("Número", "") or pr.get("Numero", "") or "",
            "manga": manga_final,
            "toggles": toggles,
        }
        dval = pr.get(diseno_col.get("id"), pr.get(diseno_col.get("label"), "")) if diseno_col else ""
        translated_pr["_diseno"] = _slugify_diseno(dval) if str(dval or "").strip() else _slugify_diseno(default_diseno)
        _vcl = str(pr.get("__variante", "") or "").strip()
        # ¿La variable que trae la fila es de ESTE molde? Si no lo es —porque el espacio usa varios
        # moldes y en la fila sólo entra una— se toma la que ese espacio eligió para este molde.
        if not (_vcl and (_vcl in variantes_prod or _vcl in variantes_piezas)):
            _vcl = str((var_por_diseno or {}).get(translated_pr["_diseno"], "") or "").strip()
        if _vcl and (_vcl in variantes_prod or _vcl in variantes_piezas):
            translated_pr["variante_clave"] = _vcl
            if _vcl in variantes_prod:
                translated_pr["variante_idx"] = variantes_prod[_vcl]
            # NOMBRES de las piezas: preferir el id ESTABLE (piezas.json); si no, el talle guía.
            if _vcl in variantes_piezas:
                translated_pr["variante_piezas"] = variantes_piezas[_vcl]
            elif _idx2nom_guia and _vcl in variantes_prod:
                translated_pr["variante_piezas"] = [_idx2nom_guia[int(i)] for i in variantes_prod[_vcl] if int(i) in _idx2nom_guia]
        if _vcl and variantes_grupo.get(_vcl):
            translated_pr["_grupo"] = variantes_grupo[_vcl]   # grupo → acota la posición de etiqueta
        if _vcl and variantes_juntas.get(_vcl):
            translated_pr["juntas_piezas"] = variantes_juntas[_vcl]   # vínculos "van juntas" → atómicos frente al toggle
        persona = {"nombre": translated_pr["nombre"], "numero": translated_pr["numero"]}
        for c in cols_template:
            if c.get("role") == "diseno":
                continue  # el diseño no es un dato a estampar
            cval = pr.get(c.get("id"), pr.get(c.get("label"), ""))
            if cval not in (None, ""):
                persona[c.get("label") or c.get("id")] = cval
        translated_pr["personalizacion"] = persona
        out.append(translated_pr)
    return out


@app.post("/api/generar")
def generar():
    cuerpo = request.get_json(force=True)
    prendas = cuerpo.get("prendas", [])
    if not prendas:
        return jsonify({"error": "el pedido no tiene prendas"}), 400
    # El molde a generar: el del body (multi-molde) o, si no viene, el activo.
    pid = cuerpo.get("producto_id") or _get_active_producto_id()
    reg = _cargar("registro_producto.json", pid)
    # Personalización FRESCA del arte (incluye trazo/borde + color exacto).
    try:
        pers = MP.extraer_personalizacion(_ruta_entrada("arte.ai", pid)) or {}
    except Exception:
        pers = _cargar("registro_personalizacion.json", pid) or {}
    val = _cargar("validacion_arte.json", pid)
    if not reg or not val or not val.get("aprobado"):
        return jsonify({"error": "falta plantilla registrada o arte aprobado"}), 409

    cat = _cargar_catalogo()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    translated_prendas = _traducir_prendas(prendas, prod, cat, reg=reg)

    mapeo = None
    if val.get("modo") == "separado":
        # REGLA mapeo-por-variable: se pasa la estructura completa; el motor resuelve el
        # mapeo de cada prenda por su `variante_clave` (base para filas sin variable).
        _b, _pv = _mapeo_estructura(pid)
        mapeo = ({"mapeo": _b, "por_variable": _pv} if (_b or _pv) else None)
    cfg_nesting, rotaciones, telas_cfg, asignacion = _config_produccion(pid)
    # Override pieza→tela desde el PEDIDO (selector de tela en el Arte). {pieza_nombre: tela_nombre}.
    _asig_ped = cuerpo.get("asignacion") or {}
    if isinstance(_asig_ped, dict) and _asig_ped:
        asignacion = {str(p): str(t) for p, t in _asig_ped.items() if t}
    tid = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    salida = os.path.join(TRABAJOS, tid)
    trabajos[tid] = {"estado": "en cola", "progreso": "", "resultado": None, "error": None,
                     "producto_id": pid, "producto_nombre": (prod or {}).get("nombre", "")}

    def correr():
        try:
            trabajos[tid]["estado"] = "generando"
            def prog(fase, a, b):
                trabajos[tid]["progreso"] = f"{fase}: {a}" + (f"/{b}" if b else "")
            res = MP.generar_pedido(_ruta_entrada("plantilla.ai", pid),
                                    _ruta_entrada("arte.ai", pid),
                                    reg, pers, translated_prendas, _fuentes_para(pid), salida, progreso=prog,
                                    mapeo_arte=mapeo, config_nesting=cfg_nesting,
                                     rotaciones=rotaciones, asignacion_tela=asignacion,
                                     telas_cfg=telas_cfg, borde_corte=(prod or {}).get("borde_corte"),
                                     etiqueta=(prod or {}).get("etiqueta"),
                                     editables_cfg=_editables_cfg(prod, "principal", (cuerpo.get("editables") or {}).get("principal")),
                                     editables_tamano=_editables_tamano(prod),
                                     editables_color=_editables_color(prod, "principal"),
                                     objetos_agregados=_objetos_agregados_motor(pid, _diseno_sub("principal")))
            res["id"] = tid
            res["producto_id"] = pid
            res["producto_nombre"] = (prod or {}).get("nombre", "")
            try:
                _icc, _icc_nom, _icc_n = _icc_para_salida([_ruta_entrada("arte.ai", pid)], cat)
                if _icc:
                    _esp = "RGB" if _icc_n == 3 else "CMYK"   # respeta el espacio del perfil
                    for h in res.get("hojas", []):
                        _p = os.path.join(salida, h["archivo"])
                        # Convertir SOLO si hay contenido en OTRO modo que el del perfil;
                        # si ya está todo en ese modo, los valores quedan EXACTOS.
                        _mixto = _pdf_tiene_rgb(_p) if _esp == "CMYK" else _pdf_tiene_cmyk(_p)
                        if _mixto:
                            _unificar_modo_gs(_p, _esp)
                        _embeber_perfil_pdf(_p, _icc, _icc_nom, _icc_n)
                    res["perfil_icc"] = _icc_nom
            except Exception as _e:
                print("  [!]  perfil ICC en salida:", _e)
            try:   # aplanar cada hoja para el RIP (ver generar_multi) — avisando hoja por hoja
                from aplanar_rip import aplanar_para_rip
                _hs = res.get("hojas", [])
                for _i, h in enumerate(_hs):
                    try:
                        prog("rip", f"{_i + 1}/{len(_hs)}", None)
                    except Exception:
                        pass
                    _tr = time.time()
                    aplanar_para_rip(os.path.join(salida, h["archivo"]))
                    print(f"  [tiempos] preparar {h['archivo']} para el RIP: "
                          f"{time.time() - _tr:.0f}s ({h.get('paginas')} páginas)", flush=True)
            except Exception as _ea:
                print("  [!] aplanar RIP:", _ea)
            json.dump({"prendas": prendas, "resultado": {k: v for k, v in res.items() if k != "hojas"} |
                       {"hojas": res["hojas"]}}, open(os.path.join(salida, "pedido.json"), "w", encoding="utf-8"),
                       ensure_ascii=False)
            trabajos[tid]["resultado"] = res
            trabajos[tid]["estado"] = "listo"
        except Exception as e:
            trabajos[tid]["estado"] = "error"
            trabajos[tid]["error"] = f"{e}"
            traceback.print_exc()

    _en_hilo(correr)
    return jsonify({"id": tid})


# Tope de moldes guía de la ficha. Cada uno pasa por el motor (render de sus piezas), así que un
# pedido con muchas combinaciones molde × diseño × variable haría una ficha eterna. Si se recorta,
# se avisa (nunca en silencio).
_MAX_GUIAS_FICHA = 16


def _muestra_de(prenda):
    """Nombre/número (y el resto de lo personalizable) de una fila del pedido, para que el molde
    guía de la ficha los muestre ESTAMPADOS como en la prenda y no en blanco."""
    return {"nombre": prenda.get("nombre") or "", "numero": prenda.get("numero") or "",
            "personalizacion": prenda.get("personalizacion") or {}}


def _combo_toggles(prenda):
    """Firma de la combinación de toggles de una fila («manga=larga», «sisa=con»…). Dos filas con
    la misma firma llevan LAS MISMAS piezas, así que a la ficha le alcanza con una."""
    return tuple(sorted((str(t.get("clave") or "").lower(), str(t.get("opcion") or "").lower())
                        for t in (prenda.get("toggles") or [])))


def _molde_guia_ficha(pid, prod, reg, diseno, var=None):
    """Molde guía para la ficha: las piezas de la VARIABLE del pedido, al talle guía, con el diseño
    RECORTADO dentro de la máscara — EXACTAMENTE el mismo PDF de pieza que la tizada nestea en la
    hoja (arte = tizada). Cada pieza vuelve como **PDF vectorial** (`pz['doc'].tobytes()`), NO como
    SVG: el conversor de SVG de fitz descarta el clip y el diseño saldría como rectángulo. Devuelve
    {nombre, diseno, piezas:[{nombre, w_cm, h_cm, pdf(bytes)}]} o None. Best-effort."""
    import tempfile as _tmp, shutil as _sh
    talles = sorted({t for v in reg.values() for t in (v or {}).keys()})
    if not talles:
        return None
    guia = (prod or {}).get("variante_guia")
    talle = guia if guia in talles else talles[len(talles) // 2]     # talle sólo para RENDERIZAR (no se muestra)
    variante = (var or {}).get("clave") or "*"
    if (var or {}).get("diseno"):
        diseno = var["diseno"]
    sub = _diseno_sub(diseno)
    pl = _ruta_entrada("plantilla.ai", pid)
    arte = _ruta_entrada("arte.ai", pid, sub=sub)
    if not os.path.exists(arte):
        diseno, sub = "principal", _diseno_sub("principal")
        arte = _ruta_entrada("arte.ai", pid, sub=sub)
    if not (os.path.exists(pl) and os.path.exists(arte)):
        return None
    # Mapeo POR VARIABLE (mismo criterio que la tizada).
    _b, _pv = _mapeo_estructura(pid, sub=sub)
    if not _b and not _pv:
        _b = {k: int(v) for k, v in (MP.mapeo_por_nombre(arte, reg) or {}).items() if v}
    mapeo = ({"mapeo": _b or {}, "por_variable": _pv} if (_b or _pv) else None)
    # Una prenda de muestra con la variable del pedido: el motor arma sus piezas igual que la tizada.
    fila = {"__variante": variante, "talle": talle, "nombre": "", "numero": ""}
    prendas = _traducir_prendas([fila], prod, cat=_cargar_catalogo(), reg=reg)
    if not prendas:
        return None
    # ── NOMBRE Y NÚMERO, TAL CUAL SALEN EN LA PRENDA ─────────────────────────────────────────
    # La muestra salía con nombre y número VACÍOS, así que el molde guía no mostraba cómo queda la
    # personalización (tipografía, curva y borde del diseño). Se toma la PRIMERA fila del pedido
    # que traiga alguno y se estampa igual que en la tizada: lo que el taller ve en la ficha es
    # exactamente lo que va a salir impreso.
    _mu = (var or {}).get("muestra") or {}
    if _mu.get("nombre") or _mu.get("numero"):
        prendas = [{**_p, "nombre": _mu.get("nombre") or "", "numero": _mu.get("numero") or "",
                    "personalizacion": _mu.get("personalizacion") or _p.get("personalizacion")}
                   for _p in prendas]
    # ── LAS PIEZAS EXACTAS DEL PEDIDO ─────────────────────────────────────────────────────────
    # Los TOGGLES (manga corta/larga, con/sin capucha…) cambian QUÉ PIEZAS lleva la prenda. La
    # muestra salía siempre con la opción por defecto, así que un pedido entero de manga larga
    # mostraba las mangas cortas. Ahora se genera UNA prenda por cada combinación que aparece en
    # las filas y se juntan las piezas: si el pedido tiene filas de manga corta Y de manga larga,
    # la ficha muestra las dos (que es lo que hay que cortar).
    _combos = (var or {}).get("combos") or []
    if _combos:
        prendas = [{**prendas[0], "toggles": list(_c)} for _c in _combos]
    try:
        pers = MP.extraer_personalizacion(arte)
    except Exception:
        pers = {}
    solo = set((var or {}).get("piezas") or [])
    tmp = _tmp.mkdtemp()
    piezas = []
    try:
        ppt = MP.generar_pedido(pl, arte, reg, pers, prendas, _fuentes_para(pid), tmp,
                                mapeo_arte=mapeo, solo_piezas=True,
                                asignacion_tela=(var or {}).get("asig"),
                                telas_cfg=(var or {}).get("telas"),
                                borde_corte=(prod or {}).get("borde_corte"),
                                etiqueta=(prod or {}).get("etiqueta"),
                                editables_cfg=_editables_cfg(prod, diseno or "principal"),
                                editables_tamano=_editables_tamano(prod),
                                editables_color=_editables_color(prod, diseno or "principal"),
                                objetos_agregados=_objetos_agregados_motor(pid, sub))
        _vistas = set()   # con varias combinaciones de toggle, las piezas comunes vienen repetidas
        for _tela, pzs in (ppt or {}).items():
            for pz in pzs:
                try:
                    nom = pz["pieza"]
                    if solo and nom not in solo:
                        continue
                    if nom in _vistas:      # el Frente es el mismo con manga corta o larga: va una vez
                        continue
                    _vistas.add(nom)
                    piezas.append({"nombre": nom, "w_cm": round(pz["w"] / MP.CM, 1),
                                   "h_cm": round(pz["h"] / MP.CM, 1), "pdf": pz["doc"].tobytes(),
                                   "tela": str(_tela) if _tela else ""})   # en qué tela va (grupo del motor)
                except Exception:
                    pass
                finally:
                    try: pz["doc"].close()
                    except Exception: pass
    except Exception:
        return None
    finally:
        _sh.rmtree(tmp, ignore_errors=True)
    if not piezas:
        return None
    piezas.sort(key=lambda p: str(p["nombre"]))
    # Nombre del diseño (para el encabezado): distingue si hay más de uno en el pedido.
    dnom = "Principal" if diseno in (None, "principal") else next(
        (d.get("nombre") for d in ((prod or {}).get("disenos") or []) if d.get("id") == diseno), diseno)
    # Nombre legible de la VARIABLE (la clave es un id tipo `v_x3706kt`): la ficha lo muestra cuando
    # un mismo diseño sale en más de una variable, que es cuando las piezas cambian.
    vnom = next((v.get("label") or v.get("nombre") for v in ((prod or {}).get("variantes") or [])
                 if v.get("clave") == (var or {}).get("clave")), None)
    # Qué opciones de toggle incluye esta guía («Manga: corta + larga»), para que se entienda por
    # qué están las piezas de las dos.
    _ops = {}
    for _c in _combos:
        for _t in (_c or []):
            _k = str(_t.get("clave") or "").strip()
            _o = str(_t.get("opcion") or "").strip()
            if _k and _o:
                _ops.setdefault(_k.capitalize(), [])
                if _o not in _ops[_k.capitalize()]:
                    _ops[_k.capitalize()].append(_o)
    opciones = " · ".join(f"{k}: {' + '.join(v)}" for k, v in _ops.items()) or None
    # De quién es el nombre/número que se ve estampado (es UNA fila del pedido, no todas).
    _ej = " ".join(x for x in (_mu.get("nombre"), _mu.get("numero")) if x).strip() or None
    return {"nombre": (prod or {}).get("nombre", pid), "diseno": dnom, "variante": vnom,
            "opciones": opciones, "ejemplo": _ej, "piezas": piezas}


@app.post("/api/generar_multi")
def generar_multi():
    """Genera VARIOS moldes en UNA sola tizada: junta las piezas de todos por TELA.
    Body: {molds: [pid, ...], prendas: [...]}."""
    cuerpo = request.get_json(force=True)
    prendas = cuerpo.get("prendas", [])
    pids = cuerpo.get("molds") or cuerpo.get("productos") or []
    default_diseno = cuerpo.get("default_diseno") or "principal"  # diseño de la fila si no hay columna
    planilla_ficha = cuerpo.get("planilla") or None              # {columnas, filas} para la FICHA TÉCNICA
    perfil_forzado = cuerpo.get("perfil_forzado")  # archivo ICC para unificar perfiles distintos (o None)
    _ed_override = cuerpo.get("editables") or {}  # ajuste por pedido de objetos editables: {diseno_slug: {nombre: {talle: tf}}}
    if not prendas:
        return jsonify({"error": "el pedido no tiene prendas"}), 400
    if not pids:
        return jsonify({"error": "no hay moldes elegidos"}), 400
    # GUARDA DE DUEÑO, MOLDE POR MOLDE. Los pids llegan en una LISTA (`molds`), que
    # `_pid_de_request` no mira (sólo `pid`/`producto_id`/la ruta) → esta ruta no pasaba por
    # ninguna guarda y generaba —y devolvía— la tizada de moldes ajenos, con su registro y su
    # arte. No es sólo escritura: es fuga de datos.
    for _p in pids:
        _no = _guard_molde(str(_p))
        if _no:
            return _no
    cat = _cargar_catalogo()
    grupos_cfg = cat.get("grupos_tizada", [])
    def _grupo_de(_pid):
        for g in grupos_cfg:
            if _pid in (g.get("moldes") or []):
                return g
        return None
    molds_data, nombres, avisos = [], [], []
    # DOS canales de aviso, porque el front los muestra distinto y con títulos distintos:
    #   `avisos`        → piezas que salieron EN BLANCO (sin diseño): «agregá su mesa en el arte».
    #   `avisos_pedido` → cosas del PEDIDO (variable sin elegir, etiqueta al lugar por defecto…),
    #                     que no tienen nada que ver con el arte.
    avisos_pedido = []
    # FICHA TÉCNICA: un molde guía POR CADA DISEÑO del pedido (y por cada variable dentro del
    # diseño), en el orden en que aparecen. Antes era uno solo por molde — el de la 1ª fila — así
    # que un pedido con «Jugador» + «Golero» mostraba un solo diseño y escondía el otro.
    _guias_ficha, _guias_vistas = [], set()
    for pid in pids:
        reg = _cargar("registro_producto.json", pid)
        prod = next((p for p in cat["productos"] if p["id"] == pid), None)
        nombre = (prod or {}).get("nombre", pid)
        if not reg:
            return jsonify({"error": f"falta el molde «{nombre}»"}), 409
        _cfg_n, rot, _telas, asig = _config_produccion(pid)
        # Tela del PEDIDO: una tela BASE para todo el molde + overrides por pieza.
        #   tela_base:   {pid: tela_nombre}
        #   asignaciones:{pid: {pieza_nombre: tela_nombre}}
        _base = (cuerpo.get("tela_base") or {}).get(pid)
        _ovr_all = (cuerpo.get("asignaciones") or {}).get(pid) or {}
        # ── LA TELA ES POR DISEÑO ─────────────────────────────────────────────────────────────
        # `asignaciones[pid]` ahora es `{slug_diseño: {pieza: tela}}`. Dos diseños que usan el
        # MISMO molde pueden ir en telas distintas: antes había una sola asignación por molde, así
        # que cambiarla en un diseño se la cambiaba al otro y los dos salían cortados igual.
        # COMPAT: el formato viejo era plano (`{pieza: tela}`) — se reconoce porque sus valores son
        # textos y no diccionarios, y se aplica a todos los diseños como antes.
        _por_dis = bool(_ovr_all) and all(isinstance(v, dict) for v in _ovr_all.values())
        _asig_cfg = asig                                  # la del molde (config), como base
        _gen = lambda s: re.sub(r"\s+\d+\s*$", "", str(s)).strip().lower()

        def _asig_de(dslug):
            """Asignación pieza→tela para UN diseño de este molde."""
            _ovr = (_ovr_all.get(dslug) or {}) if _por_dis else _ovr_all
            if not (_base or _ovr):
                return _asig_cfg
            _a = {}
            if _base:
                for _p in reg.keys():
                    _a[str(_p)] = str(_base)
            # Los overrides vienen por nombre GENÉRICO ("Cuello") → se aplican a TODAS las piezas
            # de ese genérico ("Cuello 25", "Cuello 12", …).
            for _p, _t in (_ovr.items() if isinstance(_ovr, dict) else []):
                if not _t:
                    continue
                _pg = _gen(_p)
                _match = [full for full in reg if _gen(full) == _pg]
                for full in (_match or [_p]):
                    _a[str(full)] = str(_t)
            return _a
        gconf = _grupo_de(pid)
        # Filas traducidas (cada una con su _diseno). Se separan por diseño: cada
        # subgrupo se genera con el ARTE de ese diseño (carpeta del molde para
        # 'principal', o disenos/<slug>/ para los demás).
        # La variable que ese ESPACIO eligió para ESTE molde (paso 1 del pedido): rescata las filas
        # cuya `__variante` es de otro molde del mismo espacio (ver `_traducir_prendas`).
        _vpd = {str(_sl): (_m or {}).get(pid) for _sl, _m in (cuerpo.get("vars_por_diseno") or {}).items()
                if isinstance(_m, dict)}
        translated = _traducir_prendas(prendas, prod, cat, default_diseno, reg=reg, var_por_diseno=_vpd)
        # AVISO (no traba): la posición de la etiqueta se guarda POR VARIABLE. Una fila que llega
        # sin variable —molde pedido entero, o variable cuyos valores no resuelven piezas— usa la
        # posición de la primera variable configurada (antes se iba al lugar por defecto, ver
        # `verificar_etiqueta_posicion.py`). Si dos variables la tienen en lugares distintos, esa
        # elección puede no ser la que se quería: se dice, no se frena.
        _etq_pos = ((prod or {}).get("etiqueta") or {}).get("posiciones") or {}
        if any("§" in str(_k) for _k in _etq_pos):
            _sin_var = sum(1 for _t in translated if not _t.get("variante_clave"))
            if _sin_var:
                # Va en `avisos_pedido`, NO en `avisos`: ese otro es «piezas que salieron en blanco»
                # (sin diseño) y el front lo muestra bajo ese título — mezclarlos hacía leer «no
                # tienen gráfica» cuando el arte estaba perfecto.
                avisos_pedido.append(f"«{nombre}»: {_sin_var} fila(s) quedaron sin variable elegida, así que "
                                     f"se generaron TODAS las piezas del molde y la etiqueta fue a la posición "
                                     f"de la primera variable configurada. Revisá que cada espacio tenga su "
                                     f"variable para este molde.")
        # ── TRABA ANTES DE FABRICAR ──────────────────────────────────────────────────────────
        # Una tizada mal sale igual de bien impresa que una bien: los dos errores de acá abajo NO
        # fallan, producen algo que PARECE correcto. Por eso se frena antes y se dice qué fila.
        _err = _validar_pedido(pid, nombre, prod, cat, translated, _asig_de, reg)
        if _err:
            return jsonify({"error": _err[0], "detalle": _err[1]}), 422
        por_diseno = OrderedDict()
        for pr in translated:
            por_diseno.setdefault(pr.get("_diseno") or "principal", []).append(pr)
        # Diseños de ESTE molde que tienen arte cargado (validacion existe). Si una fila trae un
        # diseño SIN arte (ej. un diseño viejo del desplegable), se usa el arte de uno que SÍ →
        # la prenda NO se descarta (antes se salteaba en silencio → la tizada quedaba con 1 talle).
        _con_arte = [d["id"] for d in ([{"id": "principal"}] + list((prod or {}).get("disenos") or []))
                     if _cargar("validacion_arte.json", pid, sub=_diseno_sub(d["id"]))]
        # El fallback es el diseño que se EDITÓ en el Arte (`default_diseno`) si tiene arte; así la
        # tizada usa lo que preparaste, no un diseño cualquiera. Si ese no tiene arte, el 1º que sí.
        _dd = _slugify_diseno(default_diseno)
        _fallback = _dd if _dd in _con_arte else (_con_arte[0] if _con_arte else None)
        for dslug, subset in por_diseno.items():
            sub = _diseno_sub(dslug)
            val = _cargar("validacion_arte.json", pid, sub=sub)
            if not val and _fallback and _fallback != dslug:
                # ese diseño no tiene arte → usar el arte de un diseño que SÍ (no descartar la prenda)
                dslug = _fallback
                sub = _diseno_sub(dslug)
                val = _cargar("validacion_arte.json", pid, sub=sub)
            dnom = "Principal" if dslug == "principal" else next((d["nombre"] for d in ((prod or {}).get("disenos") or []) if d["id"] == dslug), dslug)
            if not val:
                # ningún diseño del molde tiene arte cargado → no hay nada que aplicar.
                continue
            if not val.get("aprobado"):
                # El diseño EXISTE pero no está 100% mapeado. Se genera IGUAL: las piezas SIN
                # diseño salen en blanco (con su borde de corte + etiqueta). Solo se AVISA cuáles.
                # REGLA mapeo-por-variable: la cobertura se mide con el mapeo EFECTIVO de la
                # VARIABLE de cada fila (el suyo si lo tiene; si no la base/auto por nombre).
                _b0, _pv0 = _mapeo_estructura(pid, sub=sub)
                if not _b0 and not _pv0:
                    _b0 = MP.mapeo_por_nombre(_ruta_entrada("arte.ai", pid, sub=sub), reg) or {}
                # Solo importan las piezas que REALMENTE se generan (las de las VARIABLES de estas
                # filas), NO todo el molde. Una pieza sin diseño que no esté en ninguna variable
                # (ej. los Vivos, si la variable no los usa) NO se avisa.
                # Se prefieren las CLAVES estables (`variante_piezas`, resueltas por pieza_id); el
                # mapa idx→nombre por talle queda como fallback para variables sin pieza_id.
                _idx2nom = {}
                for _nm, _pt in reg.items():
                    for _info in (_pt or {}).values():
                        if isinstance(_info, dict) and _info.get("pieza_idx") is not None:
                            _idx2nom.setdefault(int(_info["pieza_idx"]), _nm); break
                _faltan_set = set()
                for _pr in subset:
                    _vp = _pr.get("variante_piezas")
                    _vi = _pr.get("variante_idx")
                    if _vp:
                        _usa = set(_vp)
                    elif _vi:
                        _usa = {_idx2nom[int(_i)] for _i in _vi if int(_i) in _idx2nom}
                    else:
                        _usa = set(reg.keys())
                    _eff = _mapeo_efectivo(_b0, _pv0, _pr.get("variante_clave"))
                    _faltan_set |= (_usa - set(_eff.keys()))
                _faltan = sorted(_faltan_set)
                if _faltan:
                    _lista = ", ".join(_faltan[:6]) + ("…" if len(_faltan) > 6 else "")
                    avisos.append(f"«{nombre}» · diseño «{dnom}»: {len(_faltan)} pieza(s) sin diseño saldrán en blanco ({_lista}).")
                # (no se saltea: sigue y genera con lo que haya mapeado)
            # Re-extraer la personalización FRESCA del arte (trazo/borde + color exacto)
            # para no depender del registro guardado al subir (que puede ser viejo).
            _artp = _ruta_entrada("arte.ai", pid, sub=sub)
            try:
                pers = MP.extraer_personalizacion(_artp)
            except Exception:
                pers = _cargar("registro_personalizacion.json", pid, sub=sub) or {}
            mapeo = None
            if val.get("modo") == "separado":
                # REGLA mapeo-por-variable: estructura completa al motor (cada prenda resuelve
                # por su `variante_clave`). Sin nada guardado → auto por nombre como base.
                _b, _pv = _mapeo_estructura(pid, sub=sub)
                if not _b and not _pv:
                    _b = {k: int(v) for k, v in (MP.mapeo_por_nombre(_ruta_entrada("arte.ai", pid, sub=sub), reg) or {}).items() if v}
                mapeo = ({"mapeo": _b, "por_variable": _pv} if (_b or _pv) else None)
            # ── FICHA: el molde guía de ESTE diseño ──────────────────────────────────────────
            # Se anota acá (y no arriba con la 1ª fila) porque recién ahora `dslug` es el diseño
            # DEFINITIVO: si el elegido no tenía arte, más arriba cayó al `_fallback` — la ficha
            # tiene que mostrar el arte que de verdad se estampó. Dentro del diseño se anota una
            # guía por VARIABLE distinta: las piezas cambian (cuello redondo ≠ cuello V), así que
            # una sola guía mentiría sobre la mitad del pedido.
            # La asignación de telas se calcula ACÁ, no en `correr()`: `_asig_de` es una clausura
            # sobre el molde del ciclo y para cuando corre el hilo ya apunta al último molde.
            _asig_d = _asig_de(dslug)
            for _prg in subset:
                _vc = str(_prg.get("variante_clave") or "")
                _kg = (pid, dslug, _vc)
                if _kg in _guias_vistas:
                    # Ya hay guía para este combo: sólo se le suma la COMBINACIÓN DE TOGGLES de
                    # esta fila, si es nueva (manga corta y manga larga son piezas distintas y las
                    # dos tienen que salir en la ficha).
                    _g0 = next((g for g in _guias_ficha if (g["pid"], g["diseno"], g["clave"] or "") == _kg), None)
                    if _g0 is not None:
                        _cb = _combo_toggles(_prg)
                        if _cb not in _g0["_combos_vistos"]:
                            _g0["_combos_vistos"].add(_cb)
                            _g0["combos"].append(_prg.get("toggles") or [])
                        # Si la guía todavía no tiene un nombre/número de ejemplo, se toma de esta
                        # fila: la ficha muestra la personalización tal como sale estampada.
                        if not (_g0["muestra"].get("nombre") or _g0["muestra"].get("numero")):
                            _g0["muestra"] = _muestra_de(_prg)
                    continue
                _guias_vistas.add(_kg)
                _guias_ficha.append({"pid": pid, "molde": nombre, "diseno": dslug, "diseno_nombre": dnom,
                                     "clave": _vc or None, "piezas": _prg.get("variante_piezas"),
                                     "asig": _asig_d, "telas": _telas,
                                     # QUÉ PIEZAS lleva de verdad: una entrada por combinación de
                                     # toggles usada en el pedido (manga corta / manga larga / …).
                                     "combos": [_prg.get("toggles") or []],
                                     "_combos_vistos": {_combo_toggles(_prg)},
                                     # Nombre y número de ejemplo (de una fila real del pedido) para
                                     # que el molde guía los muestre estampados como en la prenda.
                                     "muestra": _muestra_de(_prg)})
            molds_data.append({
                "plantilla": _ruta_entrada("plantilla.ai", pid),
                "arte": _ruta_entrada("arte.ai", pid, sub=sub),
                "fuentes": _fuentes_para(pid),   # carpetas + reemplazos DE ESTE molde (arte=tizada)
                "registro": reg, "pers": pers, "prendas": subset,
                "mapeo_arte": mapeo, "rotaciones": rot, "asignacion_tela": _asig_de(dslug),
                "borde_corte": (prod or {}).get("borde_corte"),
                "etiqueta": (prod or {}).get("etiqueta"),
                "editables_cfg": _editables_cfg(prod, dslug, (_ed_override.get(dslug) if isinstance(_ed_override, dict) else None)),
                "editables_tamano": _editables_tamano(prod),
                "editables_color": _editables_color(prod, dslug),
                "objetos_agregados": _objetos_agregados_motor(pid, sub),   # objetos que sumó el usuario (PNG/SVG/PDF/AI)
                "_cfg_n": _cfg_n, "_telas": _telas, "_nombre": nombre,
                # Clave del grupo: el id del grupo configurado, o "solo" el molde si no
                # está en ningún grupo. Las piezas de distintos diseños del MISMO grupo
                # se mezclan en la misma mesa (el diseño solo cambia el arte estampado).
                "_gkey": (gconf or {}).get("id") or ("__solo_" + pid),
                "_gnombre": (gconf or {}).get("nombre") or nombre})
        if nombre not in nombres:
            nombres.append(nombre)
    if not molds_data:
        return jsonify({"error": "ninguna fila tiene un diseño con arte aprobado"}), 409
    # Nesting y telas: del primer molde (espaciado/margen son a nivel de hoja; el
    # giro y la tela de cada pieza ya van por-molde).
    cfg_nesting = molds_data[0]["_cfg_n"]
    telas_cfg = molds_data[0]["_telas"]
    # Agrupar por GRUPO DE TIZADA (config en Reglas de Nesting): mismo grupo =
    # comparten mesa; sin grupo o grupos distintos = tizadas separadas.
    grupos_map = OrderedDict()
    for md in molds_data:
        grupos_map.setdefault(md["_gkey"], []).append(md)
    grupos = [{"nombre": lst[0]["_gnombre"], "nombres": list(dict.fromkeys(m["_nombre"] for m in lst)), "moldes": lst}
              for g, lst in grupos_map.items()]
    tid = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    salida = os.path.join(TRABAJOS, tid)
    trabajos[tid] = {"estado": "en cola", "progreso": "", "resultado": None, "error": None,
                     "producto_id": ",".join(pids), "producto_nombre": " + ".join(nombres)}

    def correr():
        try:
            trabajos[tid]["estado"] = "generando"
            def prog(fase, a, b):
                trabajos[tid]["progreso"] = f"{fase}: {a}" + (f"/{b}" if b else "")
            res = MP.generar_pedido_grupos(grupos, FUENTES, salida,
                                           config_nesting=cfg_nesting, telas_cfg=telas_cfg, progreso=prog)
            res["id"] = tid
            res["moldes"] = nombres
            res["avisos"] = avisos   # combos (molde,diseño) que no se generaron por mapeo sin aprobar
            res["avisos_pedido"] = avisos_pedido   # cosas del pedido (no del arte) — ver arriba
            # Embeber el perfil ICC en cada hoja: el que vino en el arte, o el
            # predeterminado del sistema si el arte no traía. Tagea (OutputIntent),
            # NO convierte los colores.
            try:
                arts = list({m.get("arte") for g in grupos for m in g.get("moldes", []) if m.get("arte")})
                _icc, _icc_nom, _icc_n = _icc_para_salida(arts, cat, forzado=perfil_forzado)
                if _icc:
                    _esp = "RGB" if _icc_n == 3 else "CMYK"   # modo del perfil ELEGIDO (respeta RGB/CMYK)
                    for h in res.get("hojas", []):
                        try:
                            _p = os.path.join(salida, h["archivo"])
                            # Se convierte SOLO si la hoja tiene contenido en OTRO modo que
                            # el del perfil elegido (RGB en salida CMYK, o CMYK en salida
                            # RGB). Si ya está todo en ese modo, NO se toca: los valores
                            # quedan EXACTOS y solo se ASIGNA el perfil (OutputIntent).
                            _mixto = _pdf_tiene_rgb(_p) if _esp == "CMYK" else _pdf_tiene_cmyk(_p)
                            if _mixto:
                                prog("perfil", "unificando color " + h["archivo"], None)
                                _unificar_modo_gs(_p, _esp)       # a un solo modo (sin diálogo de Illustrator)
                            _embeber_perfil_pdf(_p, _icc, _icc_nom, _icc_n)  # perfil incrustado (OutputIntent)
                        except Exception as _eh:
                            print("[!] perfil/color en hoja:", repr(_eh))
                    res["perfil_icc"] = _icc_nom
            except Exception as _e:
                print("  [!]  perfil ICC en salida:", _e)
            # APLANAR cada hoja para el RIP: la deja como el PDF de Illustrator (des-anida las piezas,
            # 1 solo perfil ICC, estado gráfico declarado, PDF 1.6) preservando el CMYK EXACTO. Sin
            # esto, los XObjects anidados + perfiles repetidos daban "error RIP". Best-effort.
            try:
                from aplanar_rip import aplanar_para_rip
                # AVISAR hoja por hoja: es lo que MÁS tarda de todo el pedido (minutos con hojas
                # grandes) y la pantalla se quedaba en «vistas previas 100%» sin decir nada más
                # durante ese rato → parecía colgada aunque estuviera trabajando.
                _hs = res.get("hojas", [])
                for _i, h in enumerate(_hs):
                    try:
                        prog("rip", f"{_i + 1}/{len(_hs)}", None)
                    except Exception:
                        pass
                    _tr = time.time()
                    aplanar_para_rip(os.path.join(salida, h["archivo"]))
                    print(f"  [tiempos] preparar {h['archivo']} para el RIP: "
                          f"{time.time() - _tr:.0f}s ({h.get('paginas')} páginas)", flush=True)
            except Exception as _ea:
                print("  [!] aplanar RIP:", _ea)
            # FICHA TÉCNICA (A4): la planilla del pedido arriba y, abajo, UN MOLDE GUÍA POR CADA
            # DISEÑO del pedido (diseño estampado + piezas nombradas + su tela). Sale JUNTO con la
            # tizada. Best-effort: si falla, la tizada igual queda.
            try:
                import ficha_tecnica as _FT
                _guias = []
                # Las guías se anotaron molde por molde, ya con el diseño y la variable REALES.
                # Si no quedó ninguna (pedido viejo o sin arte por diseño), se cae al de siempre:
                # una guía por molde con el diseño que se editó en el Arte.
                _specs = _guias_ficha or [{"pid": _p, "diseno": _slugify_diseno(default_diseno)} for _p in pids]
                if len(_specs) > _MAX_GUIAS_FICHA:
                    # Cada guía renderiza las piezas con el motor: con muchas combinaciones la ficha
                    # tardaría más que la tizada. Se recorta, pero se DICE (mismo `avisos` que ya
                    # viaja en `res`, por referencia).
                    avisos.append(f"Ficha técnica: el pedido tiene {len(_specs)} combinaciones de molde · diseño · "
                                  f"variable; se muestran los primeros {_MAX_GUIAS_FICHA} moldes guía.")
                    _specs = _specs[:_MAX_GUIAS_FICHA]
                _pr_cache = {}
                for _sp in _specs:
                    _pf = _sp["pid"]
                    if _pf not in _pr_cache:
                        _pr_cache[_pf] = (next((p for p in cat["productos"] if p["id"] == _pf), None),
                                          _cargar("registro_producto.json", _pf))
                    _prodf, _regf = _pr_cache[_pf]
                    if _prodf and _regf:
                        prog("ficha", (_sp.get("molde") or (_prodf or {}).get("nombre", _pf))
                             + (f" · {_sp['diseno_nombre']}" if _sp.get("diseno_nombre") else ""), None)
                        g = _molde_guia_ficha(_pf, _prodf, _regf, _sp.get("diseno") or default_diseno, _sp)
                        if g:
                            _guias.append(g)
                _pl = planilla_ficha or {"columnas": [], "filas": prendas}
                _FT.generar_ficha(salida,
                                  "Ficha técnica", " + ".join(nombres) + " · " + time.strftime("%d/%m/%Y"),
                                  _pl, _guias)
                _fp = os.path.join(salida, "FICHA_TECNICA.pdf")
                if os.path.exists(_fp):
                    res["ficha"] = "FICHA_TECNICA.pdf"
                    try:
                        import fitz as _fz
                        _fd = _fz.open(_fp); res["ficha_paginas"] = _fd.page_count; _fd.close()
                    except Exception:
                        res["ficha_paginas"] = 1
            except Exception as _ef:
                print("  [!] ficha técnica:", repr(_ef))
            json.dump({"prendas": prendas, "moldes": nombres,
                       "resultado": {k: v for k, v in res.items() if k != "hojas"} | {"hojas": res["hojas"]}},
                      open(os.path.join(salida, "pedido.json"), "w", encoding="utf-8"), ensure_ascii=False)
            trabajos[tid]["resultado"] = res
            trabajos[tid]["estado"] = "listo"
        except Exception as e:
            trabajos[tid]["estado"] = "error"
            trabajos[tid]["error"] = f"{e}"
            traceback.print_exc()

    _en_hilo(correr)
    return jsonify({"id": tid})


@app.get("/api/trabajo/<tid>")
def estado_trabajo(tid):
    t = trabajos.get(tid)
    if not t:
        return jsonify({"error": "trabajo inexistente"}), 404
    return jsonify(t)


def _dibuja(fc, cp):
    """¿El glifo de este code point se puede dibujar? (cmap OK pero datos rotos = False)"""
    try:
        fc._glifo(chr(cp))
        return True
    except Exception:
        return False


def _fuentes_para(pid):
    """Fuentes visibles para ESTE molde/pedido: primero las suyas (`datos/<pid>/fuentes`,
    las subidas «solo para este pedido»), después el catálogo del sistema; más los
    reemplazos elegidos (fuente faltante → interno del catálogo)."""
    pid = pid or _get_active_producto_id()
    d = os.path.join(DATOS, "productos", pid, "fuentes")
    try:
        prod = next((p for p in _cargar_catalogo()["productos"] if p["id"] == pid), None)
    except Exception:
        prod = None
    return {"carpetas": [d, FUENTES], "alias": dict((prod or {}).get("fuentes_reemplazo") or {})}


@app.get("/api/pedido/fuentes_estado")
def fuentes_estado():
    """Fuentes que pide el arte del diseño vs las que el sistema puede resolver (catálogo +
    las de este pedido + reemplazos). El paso Arte se traba si hay faltantes."""
    pid = request.args.get("pid") or _get_active_producto_id()
    sub = _diseno_sub(request.args.get("diseno"))
    arte = _ruta_entrada("arte.ai", pid, sub=sub)
    _catalogo = sorted(({"interno": i["interno"], "archivo": i["archivo"]}
                        for i in MP.catalogo_fuentes(FUENTES).values()), key=lambda x: x["interno"].lower())
    if not os.path.exists(arte):
        return jsonify({"ok": True, "requeridas": [], "faltantes": [], "reemplazables": [],
                        "originales": {}, "catalogo": _catalogo, "reemplazos": {}})
    try:
        # Las fuentes que el MOTOR necesita para estampar: las de la personalización
        # (capas Nombre/Número/Palabra…). `fuentes_requeridas_arte` mira Personalizable/
        # Diseño y se perdía justo éstas (bug 2026-08-20: la fuente del nombre no saltaba).
        pers = MP.extraer_personalizacion(arte) or {}
        req = sorted({c.get("fuente") for m in pers.values() for c in (m or {}).values() if c.get("fuente")})
        if not req:
            req = sorted((MP.fuentes_requeridas_arte(arte) or {}).keys())
    except Exception as e:
        return jsonify({"ok": False, "error": f"no se pudo leer el arte: {e}"}), 422
    fx = _fuentes_para(pid)
    # REGLA (como Illustrator): TODA fuente del arte es reemplazable, esté instalada o no
    # (los textos de nombre/número son 100% manipulables). <faltantes> = las que no se
    # pueden estampar ni con el reemplazo (cartel + traba). <originales> = con qué interno
    # del catálogo resuelve cada una SIN alias (el front marca «original del diseño»).
    fx0 = {"carpetas": fx.get("carpetas") or [], "alias": {}}
    _cat_fx = {r: i.get("interno") for r, i in MP.catalogo_fuentes(fx0).items()}
    originales = {}
    for f in req:
        _r = MP.resolver_fuente(f, fx0)
        originales[f] = _cat_fx.get(_r) if _r else None
    faltantes = sorted(f for f in req if not MP.resolver_fuente(f, fx))
    return jsonify({"ok": True, "requeridas": req, "faltantes": faltantes,
                    "reemplazables": req, "originales": originales,
                    "catalogo": _catalogo, "reemplazos": fx.get("alias") or {}})


@app.post("/api/pedido/fuente_resolver")
def fuente_resolver():
    """Resuelve una fuente NO reconocida del arte: subiéndola (destino `sistema` = catálogo
    global, `pedido` = sólo este molde) o eligiendo un reemplazo del catálogo
    (`{faltante, usar}` → se guarda en `prod.fuentes_reemplazo`)."""
    pid = request.form.get("pid") or (request.get_json(silent=True) or {}).get("pid") or _get_active_producto_id()
    f = request.files.get("archivo")
    if f:
        destino = (request.form.get("destino") or "pedido").strip()
        carpeta = FUENTES if destino == "sistema" else os.path.join(DATOS, "productos", pid, "fuentes")
        os.makedirs(carpeta, exist_ok=True)
        tmp = os.path.join(carpeta, "subida_" + os.path.basename(f.filename))
        f.save(tmp)
        res = MP.alta_fuente(tmp, carpeta)
        if not res.get("ok"):
            _descartar_tmp(tmp)
            return jsonify(res), 422
        # Cargar el archivo de una fuente que tenía reemplazo ES elegir volver a ella
        # (regla Illustrator: la elección manda; esta subida es la elección más explícita).
        # Se limpian los alias cuyo nombre ORIGINAL resuelve ahora al archivo recién subido.
        quitados = []
        try:
            fx0 = {"carpetas": [os.path.join(DATOS, "productos", pid, "fuentes"), FUENTES], "alias": {}}
            cat = _cargar_catalogo_para_editar()
            prod = next((p for p in cat["productos"] if p["id"] == pid), None)
            rr = dict((prod or {}).get("fuentes_reemplazo") or {})
            for k in list(rr):
                _r = MP.resolver_fuente(k, fx0)
                if _r and os.path.normcase(os.path.abspath(_r)) == os.path.normcase(os.path.abspath(tmp)):
                    rr.pop(k); quitados.append(k)
            if quitados and prod is not None:
                prod["fuentes_reemplazo"] = rr
            _guardar_catalogo(cat)
        except Exception:
            pass
        return jsonify({"ok": True, "destino": destino, "interno": res.get("interno"),
                        "alias_quitados": quitados})
    cuerpo = request.get_json(force=True) or {}
    faltante = (cuerpo.get("faltante") or "").strip()
    usar = (cuerpo.get("usar") or "").strip()
    if not faltante or not usar:
        return jsonify({"error": "falta indicar la fuente faltante y cuál usar"}), 400
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if prod is None:
        return jsonify({"error": "molde no encontrado"}), 404
    rr = dict(prod.get("fuentes_reemplazo") or {})
    # Elegir la fuente ORIGINAL del texto = volver a ella: se borra el alias en vez de
    # guardar un X→X (así <reemplazos> refleja sólo los cambios reales del usuario).
    fx0 = {"carpetas": [os.path.join(DATOS, "productos", pid, "fuentes"), FUENTES], "alias": {}}
    _ro = MP.resolver_fuente(faltante, fx0)
    _ru = MP.resolver_fuente(usar, fx0)
    if _ro and _ru and os.path.normcase(os.path.abspath(_ro)) == os.path.normcase(os.path.abspath(_ru)):
        rr.pop(faltante, None)
    else:
        rr[faltante] = usar
    prod["fuentes_reemplazo"] = rr
    _guardar_catalogo(cat)
    return jsonify({"ok": True, "reemplazos": rr})


@app.get("/api/pedido/fuente_chars")
def fuente_chars():
    """Caracteres que SOPORTA la tipografía de personalización del diseño (la que estampa
    nombre/número). La planilla los usa para pintar en ROJO lo que la fuente no tiene.
    Devuelve la INTERSECCIÓN de los cmap de todas las fuentes de personalización del arte."""
    pid = request.args.get("producto_id") or _get_active_producto_id()
    try:
        pers = MP.extraer_personalizacion(_ruta_entrada("arte.ai", pid)) or {}
    except Exception:
        return jsonify({"ok": False, "chars": "", "fuentes": [], "faltantes": []})
    fuentes = sorted({c.get("fuente") for m in pers.values() for c in (m or {}).values() if c.get("fuente")})
    sets, ok_f, falta_f = [], [], []
    for f in fuentes:
        ruta = MP.resolver_fuente(f, _fuentes_para(pid))
        if not ruta:
            falta_f.append(f); continue
        try:
            from texto_curvas import FuenteCurvas
            with open(ruta, "rb") as fh:
                fc = FuenteCurvas(fh.read())
            # Estar en el cmap NO alcanza: un glifo puede estar mapeado y tener los datos
            # corruptos (revienta recién al estamparlo). Se acepta el carácter solo si el
            # contorno se puede DIBUJAR de verdad → la planilla lo pinta en rojo antes de
            # generar, en vez de fallar la tizada.
            sets.append({chr(cp) for cp in fc.cmap.keys() if _dibuja(fc, cp)})
            ok_f.append(f)
        except Exception:
            falta_f.append(f)
    if not sets:
        return jsonify({"ok": False, "chars": "", "fuentes": fuentes, "faltantes": falta_f})
    inter = set.intersection(*sets) if len(sets) > 1 else sets[0]
    chars = "".join(sorted(c for c in inter if c.isprintable()))
    return jsonify({"ok": True, "chars": chars, "fuentes": ok_f, "faltantes": falta_f})


@app.get("/trabajos/<tid>/<archivo>")
def descargar(tid, archivo):
    return send_from_directory(os.path.join(TRABAJOS, tid), archivo)


@app.get("/api/trabajos/<tid>/pagina_img/<archivo>")
def pagina_img(tid, archivo):
    """Una página de un PDF del trabajo como PNG (para MOSTRARLO en el visor con el look del sistema:
    así el scroll es el de la app, no el del visor de PDF del navegador). `pi`=página, `z`=zoom."""
    import io as _io
    import fitz
    try:
        pi = int(request.args.get("pi", 0))
    except Exception:
        pi = 0
    try:
        z = max(1.0, min(3.0, float(request.args.get("z", 2))))
    except Exception:
        z = 2.0
    ruta = os.path.join(TRABAJOS, tid, archivo)
    if not os.path.exists(ruta):
        return jsonify({"error": "no existe"}), 404
    try:
        d = fitz.open(ruta)
        if pi < 0 or pi >= d.page_count:
            pi = 0
        pix = d[pi].get_pixmap(matrix=fitz.Matrix(z, z), alpha=False)
        png = pix.tobytes("png")
        d.close()
        return send_file(_io.BytesIO(png), mimetype="image/png")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/trabajos/<tid>/mesa/<archivo>")
def descargar_mesa(tid, archivo):
    """Descarga UNA mesa (la página `pi` de la hoja) como PDF PROPIO, con el NOMBRE que se ve en la
    tizada. Así cada mesa baja SEPARADA aunque varias sean páginas del mismo PDF (misma tela). La
    página ya viene aplanada (RIP-safe) desde la generación; se copia tal cual a un PDF de 1 página."""
    import io as _io
    import pikepdf
    try:
        pi = int(request.args.get("pi", 0))
    except Exception:
        pi = 0
    nombre = request.args.get("nombre") or "mesa"
    fn = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", nombre).strip() or "mesa"
    ruta = os.path.join(TRABAJOS, tid, archivo)
    if not os.path.exists(ruta):
        return jsonify({"error": "la mesa no existe"}), 404
    try:
        src = pikepdf.open(ruta)
        n = len(src.pages)
        if pi < 0 or pi >= n:
            pi = 0
        if n == 1:                    # hoja de 1 sola página → el archivo TAL CUAL (RIP-safe garantizado)
            src.close()
            return send_file(ruta, mimetype="application/pdf", as_attachment=True, download_name=fn + ".pdf")
        dst = pikepdf.new()
        dst.pages.append(src.pages[pi])   # copia la página (ya aplanada) a su propio PDF
        try:
            dst.docinfo["/Creator"] = "TIZADA PRO"
            dst.docinfo["/Producer"] = "TIZADA PRO"
        except Exception:
            pass
        buf = _io.BytesIO()
        dst.save(buf, force_version="1.6")
        dst.close(); src.close()
        buf.seek(0)
        return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=fn + ".pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/trabajos/zip")
def descargar_zip():
    """Arma un ZIP con los PDF de todas las mesas de los trabajos pedidos
    (ids separados por coma), una carpeta por molde."""
    import io
    import zipfile
    ids = [t for t in request.args.get("ids", "").split(",") if t]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for tid in ids:
            t = trabajos.get(tid) or {}
            hojas = ((t.get("resultado") or {}).get("hojas")) or []
            nombre = t.get("producto_nombre") or tid
            slug = "".join(c if c.isalnum() else "_" for c in nombre)[:30] or "molde"
            carpeta = os.path.join(TRABAJOS, tid)
            for h in hojas:
                arch = h.get("archivo")
                ruta = os.path.join(carpeta, arch) if arch else None
                if ruta and os.path.exists(ruta):
                    zf.write(ruta, f"{slug}/{arch}")
    buf.seek(0)
    return send_file(buf, mimetype="application/zip", as_attachment=True, download_name="tizadas.zip")


# ════════════════ PRODUCT CATALOG ENDPOINTS (CRM) ════════════════
_PZ_COUNT = {}   # ruta -> (mtime, cantidad)


_TOGGLES_CACHE = {}


def _toggles_disponibles_cached(prod, cat):
    """`_toggles_disponibles` cacheado por mtime del registro + firma de la config que lo afecta.

    `GET /api/productos` es el endpoint más caliente de la app; esto abre el registro, `piezas.json`
    y recorre los nombres de ~135 piezas por variable. La firma incluye la plantilla y las variables
    porque cambiarlas cambia el resultado sin tocar el registro."""
    pid = (prod or {}).get("id")
    if not pid:
        return {}
    try:
        mt = _reg_rev(pid)
    except OSError:
        return {}
    # La firma va por CONTENIDO, no por cantidad: `_toggles_disponibles` depende de QUÉ piezas
    # tiene cada variable (`_piezas_de_variable`) y de las OPCIONES de cada regla. Contando
    # `len(variantes)` y `len(reglas_planilla)` se escapaban los dos cambios más comunes —
    # editar las piezas de una variable, o pasar «Corta, Larga» a «Corta, Larga, 3/4»— y la
    # pantalla seguía ofreciendo las opciones viejas hasta reiniciar el servidor (que corre
    # como servicio: días). Ver changelog 2026-08-18 (171.C).
    firma = (mt, prod.get("planilla_template_id"),
             _sha1_corto(prod.get("variantes") or []),
             _sha1_corto(cat.get("reglas_planilla") or []),
             _sha1_corto(_cols_template_de(prod, cat) or []))
    hit = _TOGGLES_CACHE.get(pid)
    if hit and hit[0] == firma:
        return hit[1]
    try:
        val = _toggles_disponibles(prod, cat)
    except Exception as e:
        print(f"[toggles] no se pudo calcular para {pid}: {e}")
        val = {}
    _TOGGLES_CACHE[pid] = (firma, val)
    return val


def _contar_piezas_registro(reg_path):
    """Cuántas piezas tiene registradas un molde, CACHEADO por mtime.

    `GET /api/productos` es el endpoint más caliente de la app (el front lo llama en ~28 lugares)
    y abrir + parsear el registro de cada molde en cada llamada es caro: son ~135 piezas por
    molde. El registro cambia poco, así que alcanza con mirar la fecha del archivo."""
    try:
        mt = os.path.getmtime(reg_path)
    except OSError:
        return 0
    hit = _PZ_COUNT.get(reg_path)
    if hit and hit[0] == mt:
        return hit[1]
    try:
        n = len(json.load(open(reg_path, encoding="utf-8")) or {})
    except Exception:
        n = 0
    _PZ_COUNT[reg_path] = (mt, n)
    return n


@app.get("/api/productos")
def get_productos():
    cat = _cargar_catalogo()
    res_prods = []
    templates = cat.get("plantillas_planillas", [])
    _u = _usuario_actual()

    for p in cat["productos"]:
        if not _puede_ver_molde(p, _u):
            continue                     # molde de otro usuario: no existe para éste
        pid = p["id"]
        reg_path = os.path.join(DATOS, "productos", pid, "registro_producto.json")
        # `plantilla` = HAY ARCHIVO DE MOLDE subido. Antes miraba la existencia de
        # `registro_producto.json` — y con el flujo nuevo eso rompía TODO el visor: la subida
        # deja el registro vacío (se nombra después) y el registro vive en la BASE (sin espejo),
        # así que el archivo no existe nunca más → `plantilla: False` → el front ni pedía la
        # detección y el molde recién subido se veía VACÍO «sin ninguna explicación» (reportado).
        # Se mira el archivo del molde directo (sin `_ruta_entrada`, que hace makedirs en un GET).
        has_plantilla = os.path.exists(os.path.join(ENTRADA, pid, "plantilla.ai"))
        # CUÁNTAS PIEZAS TIENE REGISTRADAS (de la base) — para distinguir «molde subido pero sin
        # nombrar» de «molde OK». Un DXF/AI entra a propósito con el registro vacío.
        try:
            _reg_conteo = (_cargar("registro_producto.json", pid) or {}) if has_plantilla else {}
        except Exception:
            _reg_conteo = {}   # base caída: el conteo es informativo, no puede tumbar /api/productos
        n_piezas = len(_reg_conteo)
        # NOMBRADAS POR EL USUARIO (sin las provisorias «Pieza N» / «Pieza extra N»): el gate del
        # front — hasta que no haya al menos una, los demás ajustes del molde quedan DESACTIVADOS
        # (regla del usuario 2026-08-19: sin nombrar no se avanza a nada).
        n_nombradas = sum(1 for _k in _reg_conteo if not re.match(r"^Pieza( extra)? \d+'*$", _k))
        val_path = os.path.join(DATOS, "productos", pid, "validacion_arte.json")
        has_arte = False
        if os.path.exists(val_path):
            try:
                has_arte = json.load(open(val_path, encoding="utf-8")).get("aprobado", False)
            except Exception:
                pass
        
        # Resolve columns from template if assigned
        cols = None
        tid = p.get("planilla_template_id")
        if tid:
            template = next((t for t in templates if t["id"] == tid), None)
            if template:
                cols = template.get("columnas")
        if not cols:
            cols = p.get("columnas", [
                {"id": "talle", "label": "Talle", "role": "talle"},
                {"id": "nombre", "label": "Nombre", "role": "nombre"},
                {"id": "numero", "label": "Número", "role": "numero"},
                {"id": "manga", "label": "Manga", "role": "manga"}
            ])
        
        res_prods.append({
            "id": pid,
            "nombre": p["nombre"],
            "creado": p.get("creado", 0),
            # `propio` = va a la pestaña "Mis artículos" del pedido. Lo decide la marca **`propio`**
            # del alta, NO el dueño: `creado_por` es autoría y lo lleva TODA moldería creada con
            # sesión, incluidas las del catálogo — mirarlo a él mandaba a "Mis artículos" (y le
            # escondía al resto) los moldes cargados desde Configuración, que son de todos.
            "propio": bool(p.get("propio")) and (not _u or not p.get("creado_por")
                                                 or p.get("creado_por") == _u.get("id")),
            # Un molde de OTRO que igual se ve: sólo pasa con el permiso `molde.ver_todos`.
            "de_otro": _es_privado(p) and bool(_u) and p.get("creado_por") != _u.get("id"),
            # 🔴 «ES DE ALGUIEN» — NO depende de quién mira. `propio` y `de_otro` sí (uno es «es
            # MÍO» y el otro «es de OTRO»), así que ninguno de los dos sirve para preguntar «¿esto
            # es un artículo personal?». Sin este campo, el artículo privado de admin le llegaba a
            # otro admin con `propio: false` y se le colaba en Configuración como si fuera del
            # catálogo compartido. Para «¿va en el espacio del taller?» se usa ESTE.
            "personal": _es_privado(p),
            "plantilla": has_plantilla,
            "piezas_nombradas": n_nombradas,
            "piezas_registradas": n_piezas,
            # Cuántas piezas se le agregaron al molde (= versiones del archivo). Con esto la pantalla
            # puede ofrecer «Deshacer»: sin el dato, agregar una pieza parecía un camino de ida.
            "piezas_agregadas": OA._ver_actual(os.path.join(ENTRADA, pid, "plantilla.ai")),
            # Qué opciones de cada toggle (manga/sisa/…) tiene REALMENTE este molde, y por variable:
            # la planilla no puede ofrecer «Larga» si ninguna pieza dice «larga» (ver §9 del mapa).
            "toggles_piezas": _toggles_disponibles_cached(p, cat),
            "arte": has_arte,
            "planilla_template_id": tid or "plan_default",
            "nesting_preset_id": p.get("nesting_preset_id") or "nesting_default",
            "grupo_tizada": p.get("grupo_tizada") or "General",
            "columnas": cols,
            "mapeo_columnas": p.get("mapeo_columnas", {
                "talle": "talle",
                "nombre": "nombre",
                "numero": "numero",
                "manga": "manga",
                "manga_corta_val": "corta",
                "manga_larga_val": "larga"
            }),
            # Terminología configurable: cómo se llaman, de cara al usuario, los
            # conceptos del sistema. El funcionamiento NO cambia, solo las etiquetas.
            "terminologia": {**{"variante": "Talle", "molde": "Molde"},
                             **(p.get("terminologia") or {})},
            # Variante (talle) elegida como guía del visor. Persistida en la base
            # → todos los usuarios ven la misma.
            "variante_guia": p.get("variante_guia"),
            # Dimensión de referencia del diseño: 'alto' o 'ancho'.
            "referencia_medida": p.get("referencia_medida") or "alto",
            # Arquitectura Modelos/Variables (genérica). `variantes` = los TIPOS de
            # pieza y sus valores (Frente→[Manga pegada, Ranglan…]); `modelos` = los
            # modelos del molde, cada uno con sus Variables (combinaciones). El TALLE
            # queda aparte (columnas/variante_guia), esto no lo toca.
            "variantes": p.get("variantes") or [],
            "modelos": p.get("modelos") or [],
            # `conjuntos` = piezas que "van juntas" (una pieza de varias partes, p.ej.
            # cuello de 3 piezas). Para la generación automática de variables.
            "conjuntos": p.get("conjuntos") or [],
            # `grupos` = grupos de piezas elegidos por el usuario; la generación de
            # variables corre DENTRO de cada grupo (una pieza puede estar en varios).
            "grupos": p.get("grupos") or [],
            # Telas (ids del registro global) asignadas a este molde → habilitan el
            # selector de tela por pieza en el pedido.
            "telas_asignadas": p.get("telas_asignadas") or [],
            # Disponibilidad de telas POR PIEZA: {"todas":[…], "por_pieza":{pieza:[…]}}.
            # Se deriva de `telas_asignadas` en los moldes viejos (ver `_telas_cfg_prod`).
            "telas_cfg": _telas_cfg_prod(p),
        })
    return jsonify({
        "activo": cat["activo"],
        "productos": res_prods
    })


@app.get("/api/productos/diagnostico")
def productos_diagnostico():
    """Por qué CADA moldería se ve o no se ve, para el usuario que está logueado AHORA.

    Existe porque «no me aparece» no se puede diagnosticar a ciegas: el sistema publicado corre en
    otra máquina y con otros usuarios. Se abre en el navegador con la sesión de la persona que
    tiene el problema y dice, molde por molde, qué guarda lo está tapando. Es de SÓLO LECTURA."""
    u = _usuario_actual()
    cat = _cargar_catalogo()
    out = []
    for p in cat.get("productos", []):
        _ver = _puede_ver_molde(p, u)
        _priv = _es_privado(p)
        _prop = bool(p.get("propio")) and (not u or not p.get("creado_por")
                                           or p.get("creado_por") == u.get("id"))
        _deotro = _priv and bool(u) and p.get("creado_por") != u.get("id")
        if not _ver:
            motivo = ("Es el «Mi artículo» de otro usuario y te falta el permiso «molde.ver_todos»."
                      if _priv else "No deberías ver esto: revisar `_puede_ver_molde`.")
        elif _priv:
            motivo = ("Es TU «Mi artículo»: va en Pedido → Mis artículos, NO en Configuración."
                      if _prop else
                      "Es el «Mi artículo» de OTRO: lo ves por «molde.ver_todos», pero no va ni en "
                      "Configuración ni en tu catálogo.")
        else:
            motivo = "Del sistema: se ve en Configuración y su variable en el catálogo del pedido."
        out.append({
            "id": p.get("id"), "nombre": p.get("nombre"),
            "creado_por": p.get("creado_por"), "alta_por": p.get("alta_por"),
            "propio_guardado": p.get("propio"),
            "personal": _priv, "propio": _prop, "de_otro": _deotro,
            "lo_ves": _ver,
            "aparece_en_configuracion": _ver and not _priv,
            "aparece_en_mis_articulos": _ver and _prop,
            "variables_con_piezas": sum(1 for v in (p.get("variantes") or [])
                                        if any(x.get("pieza_idx") is not None for x in (v.get("valores") or []))),
            "motivo": motivo,
        })
    return jsonify({
        "usuario": ({"id": u.get("id"), "usuario": u.get("usuario"), "roles": u.get("roles"),
                     "permisos": sorted(u.get("permisos") or [])} if u else None),
        "usuarios_activados": _USUARIOS_ON,
        "moldes": out,
        "leeme": ("`aparece_en_configuracion` = lo ves en Configuración › Molderías. "
                  "Si un molde SIN dueño (`creado_por: null`) no te aparece, el problema NO es de "
                  "propiedad: mirá `lo_ves` y `motivo`."),
    })


def _activar_en_sesion(pid):
    """Deja `pid` como molde activo DE ESTA SESIÓN (el global lo escribe cada llamador)."""
    try:
        session["pid_activo"] = pid
        session.permanent = True
    except Exception:
        pass


@app.post("/api/productos/crear")
def crear_producto():
    cuerpo = request.get_json(force=True) or {}
    nombre = cuerpo.get("nombre", "").strip()
    if not nombre:
        return jsonify({"error": "Falta el nombre del producto"}), 400
    
    cat = _cargar_catalogo_para_editar()
    propio = bool(cuerpo.get("propio"))

    # 🔴 UN «MI ARTÍCULO» SIN DUEÑO ES UN ESTADO IMPOSIBLE — no se crea.
    # `propio: true` + `creado_por: null` es contradictorio y se comporta pésimo: `_es_privado` da
    # False (no cuenta como privado → se cuela en Configuración) pero `get_productos` lo marca
    # `propio: true` para CUALQUIERA (la rama `not creado_por`) → aparece en «Mis artículos» de
    # todos. Se llega ahí si la base parpadea justo en el alta: `_guardia_moldes` deja pasar con un
    # usuario de mentira (`_u = True`) y después `_uid_actual()` devuelve None.
    # Sin sistema de usuarios (taller de una persona) sí es legítimo: no hay a quién sellar.
    if propio and _USUARIOS_ON and not _uid_actual():
        return jsonify({"error": "Se perdió tu sesión: volvé a entrar y subilo de nuevo. "
                                 "Un artículo tuyo necesita saber de quién es."}), 401

    # Dar de alta en el CATÁLOGO (el que ven todos) pide `molde.crear`. Subir «mi propio molde»
    # desde el pedido NO: para eso está esa pestaña, y el Operario justamente no tiene ese permiso.
    if not propio:
        _u = _usuario_actual()
        if _u and "molde.crear" not in (_u.get("permisos") or []):
            return jsonify({"error": "No tenés permiso para crear molderías del catálogo "
                                     "(molde.crear)."}), 403

    # IDEMPOTENTE para "Mis artículos": subir DE NUEVO el mismo molde (mismo dueño, mismo nombre)
    # RE-USA el artículo que ya existe en vez de crear otro. La guarda equivalente vivía sólo en el
    # front y se caía sola: si el catálogo del navegador se había pedido sin sesión, la lista venía
    # sin los moldes propios (el server los oculta a quien no está identificado) y cada intento
    # creaba un artículo nuevo — así aparecieron cuatro «Molde short» iguales.
    if propio:
        dueno = _uid_actual()
        ya = next((p for p in cat["productos"]
                   if p.get("propio")
                   and (p.get("nombre") or "").strip().lower() == nombre.lower()
                   and p.get("creado_por") == dueno), None)
        if ya:
            cat["activo"] = ya["id"]
            _guardar_catalogo(cat)
            _activar_en_sesion(ya["id"])
            return jsonify({"id": ya["id"], "nombre": ya["nombre"], "reusado": True})

    # NOMBRE ÚNICO, **EN EL ESPACIO QUE CORRESPONDA**. Dos molderías con el mismo nombre quedan
    # como dos tarjetas idénticas y no hay forma de saber en cuál estabas trabajando (ya pasó:
    # cuatro «Molde short»). Pero el espacio no es el mismo para las dos clases de molde:
    #   · «Mi artículo» → único **por dueño** (dos usuarios pueden tener cada uno su «Camiseta»).
    #   · Catálogo      → único **entre todos**, sin mirar quién lo creó: lo comparten todos, y si
    #     la unicidad fuera por dueño dos personas podrían dejar dos «Camiseta» en la misma grilla.
    _dueno_nuevo = _uid_actual()
    _mismo_nombre = lambda p: (p.get("nombre") or "").strip().lower() == nombre.lower()
    if propio:
        _choque = next((p for p in cat["productos"] if _mismo_nombre(p)
                        and _es_privado(p) and p.get("creado_por") == _dueno_nuevo), None)
    else:
        _choque = next((p for p in cat["productos"] if _mismo_nombre(p)
                        and not _es_privado(p)), None)
    if _choque:
        _mio = " tenés" if (propio and _dueno_nuevo) else " existe"
        return jsonify({"error": f"Ya{_mio} una moldería que se llama «{nombre}». "
                                 f"Ponele otro nombre o entrá a la que ya existe."}), 409

    pid = "prod_" + time.strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:4]

    os.makedirs(os.path.join(DATOS, "productos", pid), exist_ok=True)
    os.makedirs(os.path.join(ENTRADA, pid), exist_ok=True)
    
    conf_base = _config_default()
    json.dump(conf_base, open(os.path.join(DATOS, "productos", pid, "config_produccion.json"), "w", encoding="utf-8"), ensure_ascii=False)
    
    cat["productos"].append({
        "id": pid,
        "nombre": nombre,
        "creado": time.time(),
        # ── DE QUIÉN ES ESTE MOLDE (regla del usuario, 2026-07-29) ────────────────────────────
        # · Lo que se hace en **CONFIGURACIÓN** es del **SISTEMA**: no tiene dueño personal
        #   (`creado_por = None`) y lo ve y usa todo el mundo. Aunque lo haya cargado un usuario
        #   con su sesión, no es suyo: es del taller.
        # · Lo que se hace en **PEDIDO → «Mis artículos»** (`propio: true`) es de **quien tiene la
        #   sesión iniciada**, y no lo ve nadie más.
        # `alta_por` guarda igual QUIÉN lo dio de alta: es trazabilidad, no propiedad — nunca se
        # usa para decidir quién ve qué (para eso está `_es_privado`).
        "creado_por": (_uid_actual() if propio else None),
        "alta_por": _uid_actual(),
        "propio": propio,
        "planilla_template_id": "plan_default",
        "mapeo_columnas": {
            "talle": "talle",
            "nombre": "nombre",
            "numero": "numero",
            "manga": "manga",
            "manga_corta_val": "corta",
            "manga_larga_val": "larga"
        }
    })
    cat["activo"] = pid
    _guardar_catalogo(cat)
    # El activo va TAMBIÉN a la sesión: `_get_active_producto_id` mira la sesión ANTES que el
    # global, así que dejarla apuntando al molde anterior mandaba los guardados que no llevan
    # `pid` al molde equivocado.
    _activar_en_sesion(pid)
    return jsonify({"id": pid, "nombre": nombre})


@app.post("/api/productos/activar")
def activar_producto():
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("id")
    # Activar NO es editar: un Operario (que sólo tiene `molde.ver`) necesita poder elegir un molde
    # del catálogo para trabajar. Alcanza con que lo pueda VER.
    _no = _guard_id(cuerpo, permiso=None)
    if _no: return _no          # molde de otro usuario
    cat = _cargar_catalogo_para_editar()
    exists = any(p["id"] == pid for p in cat["productos"])
    if not exists:
        return jsonify({"error": "Producto inexistente"}), 404
    # El activo se recuerda POR SESIÓN (cada usuario el suyo). Se sigue escribiendo el global
    # para no romper el modo de un solo usuario ni los procesos que corren fuera de un request.
    try:
        session["pid_activo"] = pid
        session.permanent = True
    except Exception:
        pass
    cat["activo"] = pid
    _guardar_catalogo(cat)
    return jsonify({"ok": True, "activo": pid})


def _limpiar_activo_si_borrado(cat, pid):
    """Tras borrar un molde, el 'activo' no puede seguir apuntando a él."""
    try:
        if session.get("pid_activo") == pid:
            session.pop("pid_activo", None)
    except Exception:
        pass
    if cat.get("activo") == pid:
        otros = [p["id"] for p in cat.get("productos", []) if p.get("id") != pid]
        cat["activo"] = otros[0] if otros else "prod_default"


@app.post("/api/productos/eliminar")
def eliminar_producto():
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("id")
    # Borrar hace `rmtree` de los archivos del molde: va con su propio permiso, no con `molde.editar`.
    _no = _guard_id(cuerpo, permiso="molde.borrar")
    if _no: return _no          # molde de otro usuario / sin permiso
    # (2026-08-19: `prod_default` DEJÓ de ser imborrable — era el molde semilla de la época sin
    #  base; hoy todo molde nace de una subida y el usuario puede borrar todos.)
    
    cat = _cargar_catalogo_para_editar()
    p_index = -1
    for i, p in enumerate(cat["productos"]):
        if p["id"] == pid:
            p_index = i
            break
            
    if p_index == -1:
        return jsonify({"error": "Producto inexistente"}), 404
        
    cat["productos"].pop(p_index)
    # el activo (global Y el de la sesión) no puede quedar apuntando al molde borrado
    _limpiar_activo_si_borrado(cat, pid)
    _guardar_catalogo(cat)
    
    import shutil
    try:
        shutil.rmtree(os.path.join(DATOS, "productos", pid), ignore_errors=True)
        shutil.rmtree(os.path.join(ENTRADA, pid), ignore_errors=True)
    except Exception:
        pass
    # BORRAR MOLDE = BORRAR TODO, también en la base (piezas, geometría, variables, talles).
    try:
        db.borrar_piezas_molde(pid)
    except Exception as e:
        print(f"[eliminar_producto] no se pudo borrar en la base: {e}")
    _REG_DB_CACHE.pop(pid, None)
        
    return jsonify({"ok": True})


@app.post("/api/productos/renombrar")
def renombrar_producto():
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("id")
    _no = _guard_id(cuerpo)
    if _no: return _no          # molde de otro usuario
    nombre = cuerpo.get("nombre", "").strip()
    if not nombre:
        return jsonify({"error": "Nombre vacío"}), 400
        
    cat = _cargar_catalogo_para_editar()
    encontrado = False
    for p in cat["productos"]:
        if p["id"] == pid:
            p["nombre"] = nombre
            encontrado = True
            break
            
    if not encontrado:
        return jsonify({"error": "Producto no encontrado"}), 404
        
    _guardar_catalogo(cat)
    return jsonify({"ok": True})


@app.post("/api/productos/config_columnas")
def config_columnas_producto():
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("id")
    _no = _guard_id(cuerpo)
    if _no: return _no          # molde de otro usuario
    columnas = cuerpo.get("columnas", [])
    
    if not any(c.get("role") == "talle" for c in columnas):
        return jsonify({"error": "Debe haber al menos una columna con el rol 'Talle'"}), 400
        
    cat = _cargar_catalogo_para_editar()
    encontrado = False
    for p in cat["productos"]:
        if p["id"] == pid:
            p["columnas"] = columnas
            encontrado = True
            break
            
    if not encontrado:
        return jsonify({"error": "Producto no encontrado"}), 404
        
    _guardar_catalogo(cat)
    return jsonify({"ok": True})


@app.post("/api/productos/terminologia")
def config_terminologia():
    """Guarda los nombres configurables (variante/molde) de un producto. Solo
    afecta las etiquetas que ve el usuario; el funcionamiento es el mismo."""
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("id")
    _no = _guard_id(cuerpo)
    if _no: return _no          # molde de otro usuario
    term = cuerpo.get("terminologia") or {}
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if not prod:
        return jsonify({"error": "Producto no encontrado"}), 404
    actual = prod.get("terminologia") or {}
    for clave in ("variante", "molde"):
        val = str(term.get(clave, "")).strip()
        if val:
            actual[clave] = val
    prod["terminologia"] = actual
    _guardar_catalogo(cat)
    return jsonify({"ok": True, "terminologia": actual})


@app.post("/api/productos/variante_guia")
def set_variante_guia():
    """Guarda en la base la variante (talle) usada como guía del visor del molde.
    Al estar en el servidor, todos los usuarios ven la misma."""
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("id")
    _no = _guard_id(cuerpo)
    if _no: return _no          # molde de otro usuario
    variante = str(cuerpo.get("variante", "")).strip()
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if not prod:
        return jsonify({"error": "Producto no encontrado"}), 404
    prod["variante_guia"] = variante
    _guardar_catalogo(cat)
    return jsonify({"ok": True, "variante_guia": variante})


def _grupo_por_nombre(grupos, nombre, crear=False):
    g = next((x for x in grupos if x.get("nombre", "").lower() == nombre.lower()), None)
    if g is None and crear:
        g = {"nombre": nombre, "piezas": []}
        grupos.append(g)
    return g


@app.post("/api/productos/referencia_medida")
def set_referencia_medida():
    """Guarda la dimensión de referencia del diseño ('alto' o 'ancho') del molde."""
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("id")
    _no = _guard_id(cuerpo)
    if _no: return _no          # molde de otro usuario
    ref = "ancho" if str(cuerpo.get("referencia", "")).lower().startswith("anch") else "alto"
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if not prod:
        return jsonify({"error": "Producto no encontrado"}), 404
    prod["referencia_medida"] = ref
    _guardar_catalogo(cat)
    return jsonify({"ok": True, "referencia_medida": ref})


_RE_PZ_NUM = re.compile(r"\s+(\d+)\s*$")


def _regenerar_piezas_index(pid, reg=None, guia=None, reset=False):
    """Genera/actualiza `piezas.json` del producto: identidad ESTABLE de cada pieza
    (`id` opaco + `nombre` genérico + `numero`), con la `clave` del registro como puente
    a la geometría. Preserva los id↔clave ya asignados (los id no se mueven al re-correr).
    Devuelve (id2clave, clave2id, idx_guia2id)."""
    if reg is None:
        reg = _cargar("registro_producto.json", pid) or {}
    if guia is None:
        cat = _cargar_catalogo()
        prod = next((p for p in cat["productos"] if p["id"] == pid), None)
        guia = (prod or {}).get("variante_guia")
    # `reset=True` = MOLDE RE-SUBIDO: todo lo registrado se borra y los ids arrancan en 1
    # (regla del usuario 2026-08-19: «si borramos ese molde o resubimos, todo lo que se había
    # registrado se borra»). El append-only de los ids vale DENTRO de la vida de una subida.
    prev = ({"version": 1, "piezas": []} if reset
            else (_cargar("piezas.json", pid) or {"version": 1, "piezas": []}))
    _prev_pz = prev.get("piezas", [])
    id_por_clave = {p["clave"]: p["id"] for p in _prev_pz if p.get("clave")}
    # ── EL ID NO PUEDE SEGUIR AL NOMBRE ────────────────────────────────────────────────────────
    # `clave` ES el nombre de la pieza, y el sistema lo reescribe solo (el renumerado de
    # `nombres_normalizados`). Anclado sólo a la clave, al renombrarse una pieza su id se mudaba
    # con el nombre — o se emitía uno nuevo y las variables que apuntaban al viejo quedaban
    # colgadas. Se agrega un ANCLA: en qué talle y con qué índice estaba la pieza la última vez.
    # ⚠️ NO se ancla por geometría: medido sobre los moldes reales, una firma por TAMAÑO colisiona
    #    en 94 de 137 piezas (las espejadas —manga derecha/izquierda, sisas— miden exactamente lo
    #    mismo) y fusionaría piezas distintas, que es el peor error posible acá.
    ancla_por_id = {p["id"]: p.get("ancla") for p in _prev_pz if p.get("ancla")}
    # `usados` cuenta TODAS las entradas, incluidas las retiradas: un id no se recicla nunca.
    usados = {p["id"] for p in _prev_pz if p.get("id")} | set(id_por_clave.values())

    _tomados = set()

    def _por_ancla(clave):
        """Id de una pieza que se RENOMBRÓ: se la reconoce por dónde estaba (talle + índice).
        Se traduce contra el registro actual, así que sirve aunque haya cambiado el talle guía."""
        for _id, anc in ancla_por_id.items():
            if not isinstance(anc, dict):
                continue
            _t, _i = anc.get("talle"), anc.get("idx")
            if _t is None or _i is None:
                continue
            _inf = (reg.get(clave) or {}).get(_t) or {}
            if _inf.get("pieza_idx") is not None and int(_inf["pieza_idx"]) == int(_i):
                # sólo si ese id no lo reclamó ya otra clave de esta misma pasada
                if _id not in _tomados:
                    return _id
        return None

    def _nuevo_id():
        # ID NUMÉRICO secuencial por molde (regla del usuario 2026-08-19: «cada molde subido
        # guardará cada pieza con un número secuencial» — 1, 2, 3… sin prefijo ni ceros).
        # Los ids viejos "pz_0001" pueden convivir en moldes ya cargados; los nuevos son enteros.
        _nums = [p for p in usados if isinstance(p, int)]
        _id = (max(_nums) + 1) if _nums else 1
        usados.add(_id)
        return _id

    # ── DOS PASADAS, y en este orden ───────────────────────────────────────────────────────────
    # La clave exacta es la señal MÁS FUERTE, así que se resuelve toda primero. Resolviendo de a
    # una clave (clave→ancla→nuevo) el resultado dependía del ORDEN del registro: una pieza NUEVA
    # que caía en la posición de otra se llevaba por ANCLA el id de una pieza que seguía viva, y
    # después la viva volvía a recibir el mismo id por clave exacta → dos claves con el mismo
    # pieza_id → `id2clave` se quedaba con la última y una variable resolvía la pieza equivocada.
    _asignado = {}
    for clave in reg.keys():
        _id = id_por_clave.get(clave)
        if _id and _id not in _tomados:
            _asignado[clave] = _id
            _tomados.add(_id)
    for clave in reg.keys():                      # recién ahora, sobre lo que quedó libre
        if clave in _asignado:
            continue
        _id = _por_ancla(clave)
        if _id:
            _asignado[clave] = _id
            _tomados.add(_id)

    piezas, id2clave, clave2id, idx_guia2id = [], {}, {}, {}
    for clave in reg.keys():
        _id = _asignado.get(clave) or _nuevo_id()
        _tomados.add(_id)
        m = _RE_PZ_NUM.search(clave)
        nombre = clave[:m.start()].rstrip() if m else clave
        numero = int(m.group(1)) if m else None
        info = (reg[clave] or {}).get(guia)
        # El ancla se re-escribe con la posición ACTUAL en el talle guía. Si el molde no tiene
        # `variante_guia` configurada (o el registro no cubre ese talle), sirve CUALQUIER talle
        # del registro: sin este fallback el ancla no se escribía nunca y un renombrado implícito
        # («Frente»→«Frente 1» al aceptar un nombre repetido) le cambiaba el id a la pieza.
        anc = None
        if isinstance(info, dict) and info.get("pieza_idx") is not None and guia:
            anc = {"talle": guia, "idx": int(info["pieza_idx"])}
        else:
            for _t, _inf in (reg[clave] or {}).items():
                if isinstance(_inf, dict) and _inf.get("pieza_idx") is not None:
                    anc = {"talle": _t, "idx": int(_inf["pieza_idx"])}
                    break
        anc = anc or ancla_por_id.get(_id)
        piezas.append({"id": _id, "nombre": nombre, "numero": numero, "clave": clave,
                       **({"ancla": anc} if anc else {})})
        id2clave[_id] = clave
        clave2id[clave] = _id
        if isinstance(info, dict) and info.get("pieza_idx") is not None:
            idx_guia2id[int(info["pieza_idx"])] = _id
    # ── APPEND-ONLY: las piezas que ya no están en el registro se MARCAN, no se borran ─────────
    # Si se borraran, su id se perdería y al volver la pieza (un renombrado en dos pasos, o
    # re-subir el molde) recibiría uno nuevo: las variables que la apuntaban quedarían colgadas.
    # Las retiradas no entran en `id2clave` (nadie las resuelve) pero conservan su ancla para
    # poder recuperarlas, y su id sigue ocupado para que nunca se recicle.
    # 🔴 SÓLO se retira lo que de verdad SE FUE. Si el id sigue vivo, la pieza no desapareció:
    # se RENOMBRÓ (justamente lo que el ancla permite). Retirando por CLAVE a secas quedaban dos
    # entradas con el MISMO id —la viva con el nombre nuevo y una «retirada» con el viejo— y
    # cualquier `{id: clave}` armado recorriendo la lista se quedaba con la última: el NOMBRE
    # VIEJO. Con eso, las variables dejaban de matchear y **las piezas renombradas desaparecían
    # del visor del Arte** (pasó con 24 mangas del molde real).
    _vivas = set(clave2id.keys())
    _ids_vivos = set(clave2id.values())
    for p_prev in _prev_pz:
        if p_prev.get("clave") and p_prev["clave"] not in _vivas and p_prev.get("id") not in _ids_vivos:
            piezas.append({**p_prev, "retirada": True})
    ruta = _ruta_datos("piezas.json", pid)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump({"version": 2, "piezas": piezas}, f, ensure_ascii=False, indent=2)
    # A LA BASE: las piezas del molde se guardan acá mismo — este punto corre al CARGAR el molde
    # (subir_plantilla) y al re-etiquetar. Así cada pieza tiene su id en la tabla `pieza` y su
    # pertenencia al molde desde que el molde entra, sin esperar a las variables.
    try:
        # (el espejo a la tabla `pieza` va por db.guardar_registro — un solo camino escribe;
        #  el sync viejo por legacy_id chocaba con UNIQUE(producto_id, id_en_molde))
        pass
    except Exception as e:
        print(f"[piezas] no se pudieron sincronizar a la base: {e}")
    return id2clave, clave2id, idx_guia2id


@app.post("/api/productos/variantes")
def set_variantes():
    """Guarda los TIPOS de pieza (variantes) y sus valores del molde. Estructura:
    [{clave, label, valores:[{id, label, pieza_idx?, pieza_id?}]}]. Es genérico (sirve
    para cualquier producto). NO toca los talles. Cada valor recibe su `pieza_id` ESTABLE
    (resuelto del pieza_idx@talle-guía vía piezas.json) para no depender del talle guía."""
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("id")
    _no = _guard_id(cuerpo)
    if _no: return _no          # molde de otro usuario
    variantes = cuerpo.get("variantes")
    if not isinstance(variantes, list):
        return jsonify({"error": "Faltan las variantes"}), 400
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if not prod:
        return jsonify({"error": "Producto no encontrado"}), 404
    # ── IDENTIDAD ESTABLE: cada valor (pieza_idx @ SU talle) → pieza_id ──────────────────────
    # ⚠️ El `pieza_idx` que manda el front es el índice DENTRO DEL TALLE QUE SE ESTABA MIRANDO
    # (`talle_origen`), no del talle guía. Traducirlo siempre contra la guía —que es lo que se
    # hacía— guardaba OTRAS piezas cuando el usuario elegía mirando otro talle. Ahora cada valor
    # se resuelve con su propio talle; sin `talle_origen` (datos viejos) se cae a la guía, que es
    # el comportamiento anterior.
    try:
        _guia = prod.get("variante_guia")
        _reg = _cargar("registro_producto.json", pid) or {}
        _, _clave2id, _idx2id_guia = _regenerar_piezas_index(pid, reg=_reg, guia=_guia)
        _id2clave_now = {v: k for k, v in _clave2id.items()}     # id → nombre de HOY (para el label)
        _cache_talle = {}                       # talle -> {pieza_idx: pieza_id}

        def _idx2id_de(talle):
            """{pieza_idx: pieza_id} para UN talle cualquiera, sacado del registro."""
            if talle in _cache_talle:
                return _cache_talle[talle]
            m = {}
            for _clave, _por_t in _reg.items():
                _inf = (_por_t or {}).get(talle) or {}
                if _inf.get("pieza_idx") is not None and _clave in _clave2id:
                    m[int(_inf["pieza_idx"])] = _clave2id[_clave]
            _cache_talle[talle] = m
            return m

        for _v in variantes:
            for _val in (_v.get("valores") or []):
                if _val.get("pieza_idx") is not None:
                    _t = _val.get("talle_origen")
                    _mapa = _idx2id_de(_t) if _t else _idx2id_guia
                    _pid_pieza = _mapa.get(int(_val["pieza_idx"]))
                    if _pid_pieza:
                        _val["pieza_id"] = _pid_pieza
                # El `label` es sólo para MOSTRAR y quedaba viejo al renombrar la pieza (la variable
                # se ata por `pieza_id`, que es lo correcto, pero la pantalla seguía diciendo el
                # nombre anterior). Se refresca con el nombre de HOY cada vez que se guarda.
                _cl_hoy = _id2clave_now.get(_val.get("pieza_id"))
                if _cl_hoy:
                    _val["label"] = _cl_hoy
    except Exception:
        pass  # si algo falla, se guarda igual con pieza_idx (fallback por talle guía)
    prod["variantes"] = variantes
    _guardar_catalogo(cat)
    return jsonify({"ok": True, "variantes": variantes})


@app.post("/api/productos/modelos")
def set_modelos():
    """Guarda los MODELOS del molde y sus Variables. Estructura:
    [{id, nombre, variables:[{id, nombre, build:{clave→valor_id}}]}]. El nombre de
    modelo no se puede repetir (se valida acá)."""
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("id")
    _no = _guard_id(cuerpo)
    if _no: return _no          # molde de otro usuario
    modelos = cuerpo.get("modelos")
    if not isinstance(modelos, list):
        return jsonify({"error": "Faltan los modelos"}), 400
    vistos = set()
    for m in modelos:
        nom = str(m.get("nombre", "")).strip().lower()
        if nom and nom in vistos:
            return jsonify({"error": f"El nombre de modelo «{m.get('nombre')}» está repetido"}), 400
        if nom:
            vistos.add(nom)
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if not prod:
        return jsonify({"error": "Producto no encontrado"}), 404
    prod["modelos"] = modelos
    _guardar_catalogo(cat)
    return jsonify({"ok": True, "modelos": modelos})


@app.post("/api/productos/grupos")
def set_grupos():
    """Guarda los GRUPOS de piezas del molde: [{id, nombre, piezas:[idx]}]. La
    generación de variables corre dentro de cada grupo; las piezas pueden repetirse
    entre grupos."""
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("id")
    _no = _guard_id(cuerpo)
    if _no: return _no          # molde de otro usuario
    grupos = cuerpo.get("grupos")
    if not isinstance(grupos, list):
        return jsonify({"error": "Faltan los grupos"}), 400
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if not prod:
        return jsonify({"error": "Producto no encontrado"}), 404
    prod["grupos"] = grupos
    _guardar_catalogo(cat)
    return jsonify({"ok": True, "grupos": grupos})


@app.post("/api/productos/conjuntos")
def set_conjuntos():
    """Guarda los CONJUNTOS "van juntas" (piezas de varias partes que forman una sola).
    Estructura: [{id, nombre, piezas:[idx]}]. Para la generación automática de variables."""
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("id")
    _no = _guard_id(cuerpo)
    if _no: return _no          # molde de otro usuario
    conjuntos = cuerpo.get("conjuntos")
    if not isinstance(conjuntos, list):
        return jsonify({"error": "Faltan los conjuntos"}), 400
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if not prod:
        return jsonify({"error": "Producto no encontrado"}), 404
    prod["conjuntos"] = conjuntos
    _guardar_catalogo(cat)
    return jsonify({"ok": True, "conjuntos": conjuntos})


@app.get("/api/catalogo_piezas")
def get_catalogo_piezas():
    cat = _cargar_catalogo_para_editar()
    grupos = cat.setdefault("catalogo_grupos", [])
    sup = _grupo_por_nombre(grupos, "Prenda Superior", crear=True)
    # Sumar a "Prenda Superior" las piezas ya registradas en el molde del
    # producto activo (los nombres reales que vienen del .ai).
    reg = _cargar("registro_producto.json") or {}
    existentes = {p.lower() for g in grupos for p in g.get("piezas", [])}
    cambiado = False
    for nombre in reg.keys():
        if nombre and nombre.lower() not in existentes:
            sup["piezas"].append(nombre)
            existentes.add(nombre.lower())
            cambiado = True
    if cambiado:
        _guardar_catalogo(cat)
    return jsonify(grupos)


@app.post("/api/catalogo_piezas/agregar")
def agregar_pieza_catalogo():
    cuerpo = request.get_json(force=True) or {}
    nombre = str(cuerpo.get("nombre", "")).strip()
    grupo = str(cuerpo.get("grupo", "")).strip() or "Prenda Superior"
    if not nombre:
        return jsonify({"error": "El nombre de la pieza no puede estar vacío"}), 400
    cat = _cargar_catalogo_para_editar()
    grupos = cat.setdefault("catalogo_grupos", [])
    g = _grupo_por_nombre(grupos, grupo, crear=True)
    if not any(p.lower() == nombre.lower() for p in g["piezas"]):
        g["piezas"].append(nombre)
        _guardar_catalogo(cat)
    return jsonify({"ok": True, "catalogo_grupos": grupos})


@app.post("/api/catalogo_piezas/eliminar")
def eliminar_pieza_catalogo():
    cuerpo = request.get_json(force=True) or {}
    nombre = str(cuerpo.get("nombre", "")).strip()
    grupo = str(cuerpo.get("grupo", "")).strip()
    cat = _cargar_catalogo_para_editar()
    for g in cat.get("catalogo_grupos", []):
        if not grupo or g.get("nombre", "").lower() == grupo.lower():
            g["piezas"] = [p for p in g.get("piezas", []) if p.lower() != nombre.lower()]
    _guardar_catalogo(cat)
    return jsonify({"ok": True, "catalogo_grupos": cat.get("catalogo_grupos", [])})


@app.post("/api/catalogo_grupos/agregar")
def agregar_grupo_catalogo():
    cuerpo = request.get_json(force=True) or {}
    nombre = str(cuerpo.get("nombre", "")).strip()
    if not nombre:
        return jsonify({"error": "El nombre del grupo no puede estar vacío"}), 400
    cat = _cargar_catalogo_para_editar()
    grupos = cat.setdefault("catalogo_grupos", [])
    if not any(g.get("nombre", "").lower() == nombre.lower() for g in grupos):
        grupos.append({"nombre": nombre, "piezas": []})
        _guardar_catalogo(cat)
    return jsonify({"ok": True, "catalogo_grupos": grupos})


@app.post("/api/catalogo_grupos/eliminar")
def eliminar_grupo_catalogo():
    cuerpo = request.get_json(force=True) or {}
    nombre = str(cuerpo.get("nombre", "")).strip()
    if nombre.lower() == "prenda superior":
        return jsonify({"error": "No se puede eliminar el grupo base 'Prenda Superior'"}), 400
    cat = _cargar_catalogo_para_editar()
    cat["catalogo_grupos"] = [g for g in cat.get("catalogo_grupos", []) if g.get("nombre", "").lower() != nombre.lower()]
    _guardar_catalogo(cat)
    return jsonify({"ok": True, "catalogo_grupos": cat["catalogo_grupos"]})


@app.post("/api/productos/config_mapeo")
def config_mapeo():
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("id")
    _no = _guard_id(cuerpo)
    if _no: return _no          # molde de otro usuario
    tid = cuerpo.get("planilla_template_id")
    mapeo = cuerpo.get("mapeo_columnas")
    
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if not prod:
        return jsonify({"error": "Producto no encontrado"}), 404
        
    if tid:
        prod["planilla_template_id"] = tid
    if mapeo is not None:
        prod["mapeo_columnas"] = mapeo
        
    _guardar_catalogo(cat)
    return jsonify({"ok": True})


@app.get("/api/productos/<pid>/descargar_plantilla")
def descargar_plantilla_producto(pid):
    pdir = os.path.join(ENTRADA, pid)
    ruta_plantilla = os.path.join(pdir, "plantilla.ai")
    if not os.path.exists(ruta_plantilla):
        return jsonify({"error": "El producto no tiene una plantilla base subida"}), 404
    return send_from_directory(pdir, "plantilla.ai", as_attachment=True, download_name="plantilla.ai")


# ════════════════ SPREADSHEET TEMPLATES ENDPOINTS (CRM) ════════════════
@app.get("/api/plantillas_planillas")
def get_plantillas_planillas():
    cat = _cargar_catalogo()
    # Already initialized in _cargar_catalogo()
    return jsonify(cat.get("plantillas_planillas", []))


@app.post("/api/plantillas_planillas/guardar")
def guardar_plantilla_planilla():
    cuerpo = request.get_json(force=True) or {}
    tid = cuerpo.get("id")
    nombre = cuerpo.get("nombre", "").strip()
    columnas = cuerpo.get("columnas", [])
    
    if not nombre:
        return jsonify({"error": "El nombre de la planilla no puede estar vacío"}), 400
    if not any(c.get("role") == "talle" for c in columnas):
        return jsonify({"error": "Debe haber al menos una columna con el rol 'Talle'"}), 400
        
    cat = _cargar_catalogo_para_editar()
    if "plantillas_planillas" not in cat:
        cat["plantillas_planillas"] = []
        
    if not tid:
        # Create a new template ID
        tid = "plan_" + time.strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:4]
        cat["plantillas_planillas"].append({
            "id": tid,
            "nombre": nombre,
            "columnas": columnas
        })
    else:
        encontrado = False
        for p in cat["plantillas_planillas"]:
            if p["id"] == tid:
                p["nombre"] = nombre
                p["columnas"] = columnas
                encontrado = True
                break
        if not encontrado:
            cat["plantillas_planillas"].append({
                "id": tid,
                "nombre": nombre,
                "columnas": columnas
            })
            
    _guardar_catalogo(cat)
    return jsonify({"ok": True, "id": tid, "nombre": nombre, "columnas": columnas})


@app.post("/api/plantillas_planillas/eliminar")
def eliminar_plantilla_planilla():
    cuerpo = request.get_json(force=True) or {}
    tid = cuerpo.get("id")
    if tid == "plan_default":
        return jsonify({"error": "No se puede eliminar la planilla por defecto"}), 400
        
    cat = _cargar_catalogo_para_editar()
    templates = cat.get("plantillas_planillas", [])
    p_index = -1
    for i, t in enumerate(templates):
        if t["id"] == tid:
            p_index = i
            break
    if p_index == -1:
        return jsonify({"error": "Plantilla no encontrada"}), 404
        
    templates.pop(p_index)
    
    # Reset any products pointing to deleted template
    for p in cat["productos"]:
        if p.get("planilla_template_id") == tid:
            p["planilla_template_id"] = "plan_default"
            
    _guardar_catalogo(cat)
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────────────────────
# Biblioteca de REGLAS de planilla (campos reutilizables)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/reglas_planilla")
def get_reglas_planilla():
    cat = _cargar_catalogo()
    return jsonify(cat.get("reglas_planilla", []))


@app.post("/api/reglas_planilla/guardar")
def guardar_regla_planilla():
    cuerpo = request.get_json(force=True) or {}
    rid = cuerpo.get("id")
    nombre = (cuerpo.get("nombre") or "").strip()
    tipo = cuerpo.get("tipo") or "texto"
    opciones = cuerpo.get("opciones") or ""
    comportamiento = cuerpo.get("comportamiento") or "none"
    clave = (cuerpo.get("clave") or "").strip()

    if not nombre:
        return jsonify({"error": "El nombre de la regla no puede estar vacío"}), 400
    if tipo not in ("texto", "desplegable", "toggle"):
        return jsonify({"error": "Tipo inválido"}), 400
    # Toggle de pieza (como Manga) → necesita la palabra clave que agrupa las piezas.
    if comportamiento == "manga" and not clave:
        return jsonify({"error": "Escribí la palabra clave (ej. «manga», «sisa») para el toggle de pieza"}), 400

    cat = _cargar_catalogo_para_editar()
    reglas = cat.setdefault("reglas_planilla", [])
    regla = {"nombre": nombre, "tipo": tipo, "opciones": opciones, "comportamiento": comportamiento, "clave": clave}

    if not rid:
        rid = "regla_" + uuid.uuid4().hex[:8]
        regla["id"] = rid
        reglas.append(regla)
    else:
        encontrada = False
        for r in reglas:
            if r.get("id") == rid:
                r.update(regla)
                encontrada = True
                break
        if not encontrada:
            regla["id"] = rid
            reglas.append(regla)

    _guardar_catalogo(cat)
    return jsonify({"ok": True, "id": rid})


@app.post("/api/reglas_planilla/eliminar")
def eliminar_regla_planilla():
    cuerpo = request.get_json(force=True) or {}
    rid = cuerpo.get("id")
    cat = _cargar_catalogo_para_editar()
    reglas = cat.get("reglas_planilla", [])
    idx = next((i for i, r in enumerate(reglas) if r.get("id") == rid), -1)
    if idx == -1:
        return jsonify({"error": "Regla no encontrada"}), 404
    reglas.pop(idx)
    _guardar_catalogo(cat)
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────────────────────
# Presets de NESTING (reglas de acomodo reutilizables). Cada molde elige cuál usa.
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/nesting_presets")
def get_nesting_presets():
    cat = _cargar_catalogo()
    return jsonify(cat.get("nesting_presets", []))


@app.post("/api/nesting_presets/guardar")
def guardar_nesting_preset():
    cuerpo = request.get_json(force=True) or {}
    nid = cuerpo.get("id")
    nombre = (cuerpo.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"error": "El nombre del nesting no puede estar vacío"}), 400
    try:
        espaciado = float(cuerpo.get("espaciado_mm", 5))
        margen = float(cuerpo.get("margen_mm", 10))
    except (TypeError, ValueError):
        return jsonify({"error": "Espaciado y margen deben ser números"}), 400
    # ALTO MÁXIMO DE LA MESA (cm): hasta dónde puede crecer una hoja antes de abrir otra.
    # ⚠️ EL TECHO ES DEL FORMATO PDF, no nuestro: una página no puede pasar de **14400 puntos =
    # 200 pulgadas = 508 cm**. `nesting_contorno._preparar` ya hace `min(alto*CM, 14400)`, así que
    # pedir 8 m daba mesas de 5,08 igual — la pantalla mentía. Se acota acá para que lo guardado
    # sea lo que de verdad va a pasar.
    try:
        alto_max = float(str(cuerpo.get("alto_max_cm", 500)).replace(",", ".") or 500)
    except (TypeError, ValueError):
        alto_max = 500.0
    alto_max = max(50.0, min(ALTO_MESA_MAX_CM, alto_max))
    rotacion = cuerpo.get("rotacion") or "auto"
    cat = _cargar_catalogo_para_editar()
    presets = cat.setdefault("nesting_presets", [])
    preset = {"nombre": nombre, "espaciado_mm": espaciado, "margen_mm": margen,
              "rotacion": rotacion, "alto_max_cm": alto_max}
    if not nid:
        nid = "nesting_" + uuid.uuid4().hex[:8]
        preset["id"] = nid
        presets.append(preset)
    else:
        encontrado = False
        for p in presets:
            if p.get("id") == nid:
                p.update(preset); encontrado = True; break
        if not encontrado:
            preset["id"] = nid
            presets.append(preset)
    _guardar_catalogo(cat)
    return jsonify({"ok": True, "id": nid})


@app.post("/api/nesting_presets/eliminar")
def eliminar_nesting_preset():
    cuerpo = request.get_json(force=True) or {}
    nid = cuerpo.get("id")
    if nid == "nesting_default":
        return jsonify({"error": "No se puede eliminar el nesting por defecto"}), 400
    cat = _cargar_catalogo_para_editar()
    presets = cat.get("nesting_presets", [])
    idx = next((i for i, p in enumerate(presets) if p.get("id") == nid), -1)
    if idx == -1:
        return jsonify({"error": "Nesting no encontrado"}), 404
    presets.pop(idx)
    for p in cat.get("productos", []):     # los moldes que lo usaban vuelven al estándar
        if p.get("nesting_preset_id") == nid:
            p["nesting_preset_id"] = "nesting_default"
    _guardar_catalogo(cat)
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────────────────────
# Grupos de TIZADA: conjuntos de moldes que se arman JUNTOS en la misma mesa.
# Un molde pertenece a lo sumo a un grupo; los que no están en ninguno van solos.
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/grupos_tizada")
def get_grupos_tizada():
    cat = _cargar_catalogo()
    return jsonify(cat.get("grupos_tizada", []))


@app.post("/api/grupos_tizada/guardar")
def guardar_grupo_tizada():
    cuerpo = request.get_json(force=True) or {}
    gid = cuerpo.get("id")
    nombre = (cuerpo.get("nombre") or "").strip()
    moldes = [m for m in (cuerpo.get("moldes") or []) if m]
    if not nombre:
        return jsonify({"error": "El grupo necesita un nombre"}), 400
    cat = _cargar_catalogo_para_editar()
    grupos = cat.setdefault("grupos_tizada", [])
    grupo = {"nombre": nombre, "moldes": moldes}
    if not gid:
        gid = "gt_" + uuid.uuid4().hex[:8]
        grupo["id"] = gid
        grupos.append(grupo)
    else:
        enc = False
        for g in grupos:
            if g.get("id") == gid:
                g.update(grupo); enc = True; break
        if not enc:
            grupo["id"] = gid; grupos.append(grupo)
    # Un molde solo puede estar en UN grupo: sacarlo de los demás.
    for g in grupos:
        if g.get("id") != gid:
            g["moldes"] = [m for m in (g.get("moldes") or []) if m not in moldes]
    _guardar_catalogo(cat)
    return jsonify({"ok": True, "id": gid})


@app.post("/api/grupos_tizada/eliminar")
def eliminar_grupo_tizada():
    cuerpo = request.get_json(force=True) or {}
    gid = cuerpo.get("id")
    cat = _cargar_catalogo_para_editar()
    grupos = cat.get("grupos_tizada", [])
    idx = next((i for i, g in enumerate(grupos) if g.get("id") == gid), -1)
    if idx == -1:
        return jsonify({"error": "Grupo no encontrado"}), 404
    grupos.pop(idx)
    _guardar_catalogo(cat)
    return jsonify({"ok": True})


@app.post("/api/productos/nesting_preset")
def asignar_nesting_a_producto():
    cuerpo = request.get_json(force=True) or {}
    # `producto_id` lo cubre `_pid_de_request`; el fallback a `id` NO pasaba por ninguna guarda
    # (era una puerta trasera para escribir en el molde de otro).
    pid = cuerpo.get("producto_id") or cuerpo.get("id")
    _no = _guard_molde(str(pid)) if pid else None
    if _no: return _no
    nid = cuerpo.get("nesting_preset_id")
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if prod is None:
        return jsonify({"error": "Molde no encontrado"}), 404
    prod["nesting_preset_id"] = nid
    _guardar_catalogo(cat)
    return jsonify({"ok": True})


@app.post("/api/productos/grupo_tizada")
def asignar_grupo_tizada():
    """Grupo de tizada del molde: los moldes con el MISMO grupo comparten mesa de
    trabajo; grupos distintos se arman en tizadas separadas."""
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("producto_id") or cuerpo.get("id")   # el fallback a `id` no tenía guarda
    _no = _guard_molde(str(pid)) if pid else None
    if _no: return _no
    grupo = (cuerpo.get("grupo_tizada") or "General").strip() or "General"
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if prod is None:
        return jsonify({"error": "Molde no encontrado"}), 404
    prod["grupo_tizada"] = grupo
    _guardar_catalogo(cat)
    return jsonify({"ok": True})


@app.post("/api/productos/asignar_planilla")
def asignar_planilla_a_producto():
    cuerpo = request.get_json(force=True) or {}
    pid = cuerpo.get("producto_id")
    tid = cuerpo.get("planilla_template_id")
    
    cat = _cargar_catalogo_para_editar()
    prod = next((p for p in cat["productos"] if p["id"] == pid), None)
    if not prod:
        return jsonify({"error": "Producto no encontrado"}), 404
        
    prod["planilla_template_id"] = tid
    _guardar_catalogo(cat)
    return jsonify({"ok": True})


def _liberar_puerto(port):
    """En Windows, cierra cualquier servidor anterior que esté escuchando en
    `port` para que este (el código nuevo) pueda tomarlo. Así, con solo abrir
    iniciar.bat siempre queda corriendo la última versión, sin depender del
    idioma de Windows ni de matar el proceso a mano."""
    if os.name != "nt":
        return
    try:
        import subprocess
        # netstat + taskkill: siempre disponibles, sin depender de PowerShell ni
        # del idioma de Windows (no parseamos el estado "LISTENING/ESCUCHANDO";
        # identificamos al servidor por su dirección LOCAL terminada en :PORT).
        salida = subprocess.run(["netstat", "-ano", "-p", "tcp"],
                                capture_output=True, text=True, timeout=10).stdout
        suf = ":" + str(int(port))
        pids = set()
        for linea in salida.splitlines():
            parts = linea.split()
            if len(parts) >= 5 and parts[0].upper() == "TCP" and parts[1].endswith(suf):
                pid = parts[-1]
                if pid.isdigit() and pid != "0":
                    pids.add(pid)
        for pid in pids:
            subprocess.run(["taskkill", "/F", "/T", "/PID", pid],
                           capture_output=True, timeout=10)
        if pids:
            time.sleep(0.7)  # darle tiempo al SO a liberar el socket
    except Exception:
        pass


_JOB_WIN = None      # handle del Job de Windows: mientras viva, los hijos viven; al morir, mueren


def _atar_hijos_a_este_proceso():
    """Que los procesos de dibujo NO sobrevivan al servidor.

    Windows no mata a los hijos cuando muere el padre: al reiniciar el servidor quedaban 6
    procesos de dibujo sueltos ocupando ~1 GB, y se iban acumulando con cada reinicio hasta
    dejar la máquina a medio andar (pasó: 86 procesos, 4,8 GB, y todo tardaba el doble).
    La forma que da Windows para esto es un JOB OBJECT con `KILL_ON_JOB_CLOSE`: se mete a
    ESTE proceso adentro y **todos los que cree lo heredan**, así que cuando el servidor se
    apaga —o lo matan— el sistema se lleva a sus hijos con él.

    Si algo falla (Windows viejo, permisos), se sigue como siempre: no rompe nada."""
    global _JOB_WIN
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        class _LIMITES(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
                        ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
                        ("LimitFlags", wintypes.DWORD),
                        ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t),
                        ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.POINTER(ctypes.c_ulong)),
                        ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class _IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in
                        ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                         "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        class _EXT(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", _LIMITES), ("IoInfo", _IO),
                        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        # Declarar los tipos es OBLIGATORIO: sin esto ctypes asume enteros de 32 bits y en
        # Windows de 64 el HANDLE se trunca → todo falla en silencio (comprobado: el hijo
        # sobrevivía igual). Con los tipos puestos, el hijo muere con el padre.
        k32.CreateJobObjectW.restype = wintypes.HANDLE
        k32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
        k32.SetInformationJobObject.restype = wintypes.BOOL
        k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                wintypes.LPVOID, wintypes.DWORD]
        k32.AssignProcessToJobObject.restype = wintypes.BOOL
        k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        job = k32.CreateJobObjectW(None, None)
        if not job:
            return False
        info = _EXT()
        info.BasicLimitInformation.LimitFlags = 0x2000        # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
            return False
        if not k32.AssignProcessToJobObject(job, k32.GetCurrentProcess()):
            return False
        _JOB_WIN = job       # ¡NO cerrar este handle! Cerrarlo mataría a todo el grupo.
        return True
    except Exception:
        return False


if __name__ == "__main__":
    # Puerto y host configurables por variable de entorno (sin tocar el código).
    #   PORT=8001 py servidor.py     → cambia el puerto si el 8050 está ocupado
    host = os.environ.get("HOST", "0.0.0.0")
    try:
        port = int(os.environ.get("PORT", "8050"))
    except ValueError:
        port = 8050
    debug = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")
    # El reloader corre en un proceso hijo (WERKZEUG_RUN_MAIN=true). Solo el
    # proceso inicial libera el puerto e imprime; el hijo no.
    es_reload = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    # Los procesos de dibujo tienen que morirse CON el servidor (si no, cada reinicio deja
    # ~1 GB de procesos sueltos y la máquina se va poniendo lenta sin que se note por qué).
    _atado = _atar_hijos_a_este_proceso()
    if not es_reload:
        _liberar_puerto(port)
        print("\n  USER · Motor de Sublimación")
        print(f"  Abrí el navegador en:  http://localhost:{port}\n")
        if not _atado and os.name == "nt":
            print("  [!] No se pudo atar los procesos de dibujo a este servidor: si lo reiniciás,\n"
                  "      puede que queden procesos sueltos ocupando memoria.\n")
    # Precalentar el nido (todos los talles nesteados) en segundo plano: si no está
    # cacheado en disco, el primer cálculo tarda varios segundos — mejor hacerlo ya.
    def _precalentar_nido():
        try:
            if os.path.exists(_ruta_entrada("plantilla.ai")):
                _nido_obtener()
        except Exception:
            pass
    _en_hilo(_precalentar_nido)
    # ⚡ DUAL-STACK IPv4 + IPv6 — CRÍTICO para la velocidad. En Windows "localhost" resuelve a
    # ::1 (IPv6) ANTES que a 127.0.0.1: si el server solo escucha IPv4, CADA request a
    # http://localhost paga ~2s de retry (con ~40 requests al asignar variantes = >1 minuto de
    # puro timeout). Escuchando también en ::1, "localhost" responde al instante. Medido:
    # localhost 2.08s/req → 0.02s/req. (El reloader se pierde con make_server → TIZADA_RELOAD=1
    # para volver a app.run con auto-reload en desarrollo, escuchando solo IPv4.)
    _PUERTO[0] = port
    if PUBLICADO:
        # Si una actualización quedó a mitad de camino (corte de luz), dejar constancia; y poner a
        # vigilar la hora de la que esté programada.
        ACT.recuperar_si_quedo_a_medias()
        ACT.limpiar_si_aplicada(_version()["version"])   # aplicada a mano → ya no está pendiente
        ACT.vigilar(port, _version()["version"], _apagarme)
        # SERVIDOR DE PRODUCCIÓN. `make_server`/`app.run` son de DESARROLLO: un solo hilo por
        # conexión, sin límite de cola y sin protección ante clientes lentos. Si el de producción
        # no está instalado NO se cae a los de desarrollo en silencio: se avisa y se corta (mejor
        # no arrancar que arrancar mal).
        _hilos = int(os.environ.get("TIZADA_HILOS", "8"))
        _cert, _key = os.environ.get("TIZADA_TLS_CERT"), os.environ.get("TIZADA_TLS_KEY")
        if _cert and _key:
            # ── HTTPS PROPIO (sin proxy delante) ──────────────────────────────────────────────
            # Es el caso «se entra por la IP, sin dominio»: no hay nginx ni Cloudflare que termine
            # el TLS, así que lo termina el servidor. Waitress NO habla TLS; cheroot (el server de
            # CherryPy, WSGI, sin nada compilado) sí.
            if not (os.path.exists(_cert) and os.path.exists(_key)):
                raise SystemExit(f"\n[ERROR] No encuentro el certificado:\n          {_cert}\n"
                                 f"          {_key}\n        Generalo con GENERAR-CERTIFICADO.bat\n")
            try:
                from cheroot.wsgi import Server as _ChServer
                from cheroot.ssl.builtin import BuiltinSSLAdapter
            except ImportError:
                raise SystemExit(
                    "\n[ERROR] Modo 'publicado' con HTTPS y sin cheroot instalado.\n"
                    "        Instalalo con:  py -m pip install cheroot\n")
            print(f"  modo PUBLICADO · HTTPS propio (cheroot) · {_hilos} hilos · puerto {port}")
            _srv = _ChServer((host, port), app, numthreads=_hilos, server_name="TIZADA PRO")
            _srv.ssl_adapter = BuiltinSSLAdapter(_cert, _key)
            try:
                _srv.start()
            except KeyboardInterrupt:
                _srv.stop()
        else:
            try:
                from waitress import serve as _waitress
            except ImportError:
                raise SystemExit(
                    "\n[ERROR] Modo 'publicado' sin waitress instalado.\n"
                    "        Instalalo con:  py -m pip install waitress\n")
            print(f"  modo PUBLICADO · waitress · {_hilos} hilos · puerto {port}")
            _waitress(app, host=host, port=port, threads=_hilos, ident="TIZADA PRO")
    elif os.environ.get("TIZADA_RELOAD") == "1":
        app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=True)
    else:
        from werkzeug.serving import make_server
        def _serve(h, principal=False):
            try:
                make_server(h, port, app, threaded=True).serve_forever()
            except Exception as e:
                if principal: raise
                print(f"  (aviso: no se pudo escuchar en [{h}]: {e})")
        threading.Thread(target=lambda: _serve("::1"), daemon=True).start()   # IPv6 (localhost→::1)
        _serve(host, principal=True)                                          # IPv4 (bloquea)
