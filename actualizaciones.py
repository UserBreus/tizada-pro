"""RECEPTOR DE ACTUALIZACIONES (lado servidor publicado). Ver `PLAN_PUBLICACION.md` §Etapa 2.

El taller arma un paquete y lo SUBE por HTTPS a `/api/actualizacion/subir` con la clave. Acá se
guarda, se verifica y se anota para cuándo. A la hora indicada (o con «aplicar ya») se lanza
`actualizador.py`, que es un proceso APARTE: el programa no puede reemplazar sus propios archivos
mientras corre (Windows los tiene tomados), así que el ayudante espera a que se apague y trabaja.

Lo que NUNCA se toca: `datos/` y `entrada/`. El paquete ni siquiera los trae.
"""
import os, json, time, zipfile, hashlib, threading, subprocess, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
CARPETA = os.path.join(AQUI, "_actualizacion")
PENDIENTE = os.path.join(CARPETA, "pendiente.json")
PAQUETE = os.path.join(CARPETA, "pendiente.zip")
ULTIMA = os.path.join(CARPETA, "ultima.json")
EN_CURSO = os.path.join(CARPETA, "en_curso.json")

# Archivos que el paquete DEBE traer para ser creíble. Si no están, no es una actualización de
# TIZADA PRO (o llegó cortada) y se rechaza antes de tocar nada.
IMPRESCINDIBLES = ["servidor.py", "motor_pedido.py", "VERSION", "frontend/dist/index.html"]


def _leer(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def _escribir(path, obj):
    os.makedirs(CARPETA, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path)                      # atómico: nunca queda un json a medio escribir


def token_ok(recibido):
    """La clave del header contra la del servidor. Comparación en tiempo constante (no se filtra
    cuántos caracteres coinciden). Sin clave configurada, NADIE puede actualizar."""
    esperado = os.environ.get("TIZADA_TOKEN_ACT") or ""
    if not esperado or not recibido:
        return False
    import hmac
    return hmac.compare_digest(str(recibido), esperado)


def estado(version_actual):
    """Lo que ve la pantalla: qué versión corre, si hay una pendiente y cuánto falta."""
    p = _leer(PENDIENTE)
    out = {"version": version_actual, "pendiente": None, "ultima": _leer(ULTIMA),
           "en_curso": bool(_leer(EN_CURSO))}
    if p:
        faltan = int(p.get("cuando", 0) - time.time())
        out["pendiente"] = {"version": p.get("version"), "cuando": p.get("cuando"),
                            "segundos": max(0, faltan), "tamano": p.get("tamano")}
    return out


def guardar(datos, version, sha256, cuando):
    """Recibe el .zip: verifica la huella, que abra, que traiga lo imprescindible y que la versión
    coincida con la de adentro. Recién ahí lo deja pendiente. Devuelve (ok, mensaje)."""
    os.makedirs(CARPETA, exist_ok=True)
    real = hashlib.sha256(datos).hexdigest()
    if sha256 and real != sha256:
        return False, "el paquete llegó cortado o alterado (la huella no coincide)"
    tmp = PAQUETE + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(datos)
    try:
        with zipfile.ZipFile(tmp) as z:
            if z.testzip() is not None:
                raise ValueError("el zip está dañado")
            nombres = set(z.namelist())
            faltan = [f for f in IMPRESCINDIBLES if f not in nombres]
            if faltan:
                raise ValueError(f"no parece un paquete de TIZADA PRO (falta {faltan[0]})")
            ver_zip = z.read("VERSION").decode("utf-8").strip()
    except Exception as e:
        os.remove(tmp)
        return False, str(e)
    os.replace(tmp, PAQUETE)
    _escribir(PENDIENTE, {"version": ver_zip or version, "sha256": real, "cuando": float(cuando),
                          "subido": time.time(), "tamano": len(datos)})
    return True, ver_zip


def cancelar():
    for f in (PENDIENTE, PAQUETE):
        try:
            os.remove(f)
        except OSError:
            pass


def aplicar(puerto, version_actual):
    """Lanza al ayudante SUELTO y devuelve. Quien llama debe apagar el servidor a continuación:
    el ayudante espera a que el puerto quede libre para empezar."""
    p = _leer(PENDIENTE)
    if not p or not os.path.exists(PAQUETE):
        return False, "no hay ninguna actualización pendiente"
    _escribir(EN_CURSO, {"desde": version_actual, "hacia": p.get("version"), "inicio": time.time()})
    exe = sys.executable or "py"
    cmd = [exe, os.path.join(AQUI, "actualizador.py"), AQUI, PAQUETE, str(puerto),
           str(p.get("version") or "")]
    # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP: el ayudante tiene que SOBREVIVIR a que el
    # servidor se apague. Si fuese hijo normal, se lo llevaría puesto y quedaría todo a medias.
    flags = 0x00000008 | 0x00000200 if os.name == "nt" else 0
    subprocess.Popen(cmd, cwd=AQUI, creationflags=flags, close_fds=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True, p.get("version")


def recuperar_si_quedo_a_medias():
    """Si el servidor arranca y había una actualización EN CURSO, quedó a mitad de camino (corte de
    luz, reinicio). El respaldo lo restaura el propio ayudante; acá sólo se deja constancia para
    que se vea en pantalla y no quede la marca puesta para siempre."""
    m = _leer(EN_CURSO)
    if not m:
        return
    _escribir(ULTIMA, {"ok": False, "version": m.get("hacia"), "cuando": time.time(),
                       "detalle": "la actualización quedó interrumpida (¿corte o reinicio?); "
                                  "el sistema volvió a la versión anterior"})
    try:
        os.remove(EN_CURSO)
    except OSError:
        pass


def vigilar(puerto, version_actual, apagar):
    """Hilo que mira cada 20 s si llegó la hora de una actualización programada."""
    def _loop():
        while True:
            time.sleep(20)
            try:
                p = _leer(PENDIENTE)
                if p and time.time() >= float(p.get("cuando", 0)):
                    ok, _ = aplicar(puerto, version_actual)
                    if ok:
                        time.sleep(2)          # que el ayudante levante antes de apagarnos
                        apagar()
                        return
            except Exception:
                pass
    threading.Thread(target=_loop, daemon=True).start()
