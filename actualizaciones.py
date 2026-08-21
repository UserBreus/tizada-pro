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

# «Aplicación A MANO»: un `cuando` en el año 2100 (o más) significa que el paquete queda
# esperando y NADIE lo aplica solo — lo aplican en el servidor (parar → descomprimir
# `_actualizacion/pendiente.zip` sobre la carpeta → arrancar). Es una FECHA y no un flag
# a propósito: los servidores con receptor viejo solo comparan la hora, y a éstos la hora
# no les llega nunca — compatibilidad gratis, sin tocar el servidor de enfrente.
MANUAL = 4102444800.0            # 2100-01-01

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


def puede_instalarse_solo():
    """¿Este servidor puede aplicar una actualización SIN que nadie lo ayude? → (ok, detalle).

    En Windows sí: el ayudante se lanza `DETACHED` y la tarea programada no lo toca. En Linux
    depende del **`KillMode` del servicio**: el ayudante nace dentro del cgroup de la unidad, así
    que con el valor por defecto (`control-group`) el `systemctl stop` que él mismo pide lo mata
    a él también — servidor apagado, archivos a medio reemplazar y sin rollback (pasó el
    2026-08-21). Con `KillMode=process` systemd mata sólo el proceso principal y el ayudante
    sobrevive. Se PREGUNTA en vez de confiar: `systemctl show` es de sólo lectura y no pide sudo.
    Ante la duda (no se puede consultar) se contesta NO: mejor pedir que lo apliquen a mano que
    apagar un servidor de producción."""
    if os.name == "nt":
        return True, "windows"
    servicio = os.environ.get("TIZADA_SERVICIO") or "tizadapro"
    try:
        r = subprocess.run(["systemctl", "show", "-p", "KillMode", "--value", servicio],
                           capture_output=True, text=True, timeout=15)
        valor = (r.stdout or "").strip().lower()
    except Exception as e:
        return False, f"no se pudo consultar el servicio ({e})"
    if not valor:
        return False, f"el servicio «{servicio}» no contestó su KillMode"
    if valor != "process":
        return False, (f"KillMode={valor} en «{servicio}»: instalar solo apagaría el servidor. "
                       f"Falta el drop-in con KillMode=process (ver DESPLIEGUE.md §11.b)")
    return True, "KillMode=process"


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
    # `so` = dónde corre ESTE servidor. La pantalla del taller lo usa para avisar que en Linux
    # el modo automático depende de `KillMode=process` en el unit (ver DESPLIEGUE.md §11.b).
    _solo_ok, _solo_det = puede_instalarse_solo()
    out = {"version": version_actual, "so": ("windows" if os.name == "nt" else "linux"),
           # `puede_solo` = si este servidor sabe aplicar una actualización sin ayuda humana.
           # La pantalla del taller lo muestra ANTES de publicar, para no elegir a ciegas.
           "puede_solo": _solo_ok, "puede_solo_detalle": _solo_det,
           "pendiente": None, "ultima": _leer(ULTIMA),
           "en_curso": bool(_leer(EN_CURSO))}
    if p:
        faltan = int(p.get("cuando", 0) - time.time())
        out["pendiente"] = {"version": p.get("version"), "cuando": p.get("cuando"),
                            "segundos": max(0, faltan), "tamano": p.get("tamano"),
                            "manual": float(p.get("cuando") or 0) >= MANUAL,
                            "aparcada": bool(p.get("aparcada"))}
    return out


def guardar(datos, version, sha256, cuando):
    """Recibe el .zip: verifica la huella, que abra, que traiga lo imprescindible y que la versión
    coincida con la de adentro. Recién ahí lo deja pendiente. Devuelve (ok, mensaje)."""
    # ⚠️ TODO lo que escribe va PROTEGIDO. Antes, `makedirs`, el `open` del temporal, el
    # `os.replace` y el `_escribir` estaban FUERA del try: si el servidor no tenía permiso de
    # escritura en su carpeta, o el paquete anterior estaba tomado por otro proceso (en Windows
    # `os.replace` da WinError 5), la excepción subía sin atajar y el que publicaba veía un
    # **«HTTP Error 500»** pelado, sin ninguna pista de qué pasó. Le pasó al usuario.
    try:
        os.makedirs(CARPETA, exist_ok=True)
    except Exception as e:
        return False, f"no puedo crear la carpeta de actualizaciones ({CARPETA}): {e}"
    real = hashlib.sha256(datos).hexdigest()
    if sha256 and real != sha256:
        return False, "el paquete llegó cortado o alterado (la huella no coincide)"
    tmp = PAQUETE + ".tmp"
    try:
        with open(tmp, "wb") as fh:
            fh.write(datos)
    except Exception as e:
        return False, f"no puedo escribir el paquete en {CARPETA}: {e}"
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


def aparcar():
    """Deja la pendiente para aplicar A MANO (nadie la reintenta sola). El paquete no se toca."""
    p = _leer(PENDIENTE)
    if p and float(p.get("cuando", 0) or 0) < MANUAL:
        p["cuando"] = MANUAL
        p["aparcada"] = True
        _escribir(PENDIENTE, p)
        return True
    return False


def cancelar():
    for f in (PENDIENTE, PAQUETE):
        try:
            os.remove(f)
        except OSError:
            pass


def limpiar_si_aplicada(version_actual):
    """Si lo pendiente ya ES la versión que está corriendo, lo aplicaron a mano y reiniciaron:
    se limpia solo. Sin esto, el paquete quedaría «esperando» para siempre en la pantalla."""
    p = _leer(PENDIENTE)
    if p and str(p.get("version") or "") == str(version_actual or ""):
        cancelar()


def aplicar(puerto, version_actual):
    """Lanza al ayudante SUELTO y devuelve. Quien llama debe apagar el servidor a continuación:
    el ayudante espera a que el puerto quede libre para empezar."""
    p = _leer(PENDIENTE)
    if not p or not os.path.exists(PAQUETE):
        return False, "no hay ninguna actualización pendiente"
    # 🔴 NO APAGAR UN SERVIDOR QUE NO VA A SABER VOLVER. Si el ayudante no sobreviviría al
    # `systemctl stop`, aplicar sola es garantizar la caída: se APARCA y queda para aplicar a
    # mano (el paquete está sano, no se pierde nada).
    _ok, _det = puede_instalarse_solo()
    if not _ok:
        p["cuando"] = MANUAL
        p["aparcada"] = True
        _escribir(PENDIENTE, p)
        _escribir(ULTIMA, {"ok": False, "version": p.get("version"), "cuando": time.time(),
                           "detalle": f"no se instaló sola para no dejar el servidor apagado "
                                      f"({_det}); el paquete quedó esperando para aplicarlo a mano"})
        return False, _det
    _escribir(EN_CURSO, {"desde": version_actual, "hacia": p.get("version"), "inicio": time.time()})
    exe = sys.executable or "py"
    cmd = [exe, os.path.join(AQUI, "actualizador.py"), AQUI, PAQUETE, str(puerto),
           str(p.get("version") or "")]
    # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP: el ayudante tiene que SOBREVIVIR a que el
    # servidor se apague. Si fuese hijo normal, se lo llevaría puesto y quedaría todo a medias.
    flags = 0x00000008 | 0x00000200 if os.name == "nt" else 0
    # 🔴 LINUX — LAS DOS MITADES, LAS DOS NECESARIAS (2026-08-21, se pagó en producción):
    #   (a) `start_new_session` = sesión propia (`setsid`): no le llegan las señales dirigidas al
    #       grupo del servidor.
    #   (b) `KillMode=process` en el unit (drop-in `tizadapro.service.d/kill.conf`, ver
    #       DESPLIEGUE.md §11.b): **de un cgroup NO SE SALE** — la sesión nueva no lo saca del
    #       cgroup del servicio, así que con el `KillMode` por defecto (`control-group`) el
    #       `systemctl stop` que el propio ayudante pide mata el grupo ENTERO, ayudante incluido.
    # Pasó en la primera publicación al VPS: el log del ayudante quedó en la primera línea y el
    # servicio se apagó sin versión nueva ni vieja (`Restart=always` no revive un stop deliberado).
    subprocess.Popen(cmd, cwd=AQUI, creationflags=flags, close_fds=True,
                     start_new_session=(os.name != "nt"),
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
                       "detalle": "la actualización quedó interrumpida; el paquete quedó "
                                  "APARCADO para aplicarlo a mano (no se reintenta solo)"})
    # 🔴 NO REINTENTAR SOLA. Si el intento anterior no terminó y la pendiente sigue
    # marcada para «ya», `vigilar()` la reaplica a los 5 s del arranque — y si lo que la
    # cortó sigue ahí (en Linux: el ayudante muere con el `systemctl stop` cuando al unit le
    # falta `KillMode=process`), el servidor se vuelve a apagar en cada arranque: BUCLE DE
    # CAÍDAS, con la máquina inalcanzable y sin pista de por qué. **Pasó de verdad**
    # (2026-08-21, primera actualización automática al VPS). Se APARCA con la fecha
    # centinela: el paquete queda entero para aplicarlo a mano, pero nadie lo intenta solo.
    p = _leer(PENDIENTE)
    if p and float(p.get("cuando", 0) or 0) < MANUAL:
        p["cuando"] = MANUAL
        p["aparcada"] = True
        _escribir(PENDIENTE, p)
    try:
        os.remove(EN_CURSO)
    except OSError:
        pass


def vigilar(puerto, version_actual, apagar):
    """Hilo que mira cada 20 s si llegó la hora de una actualización programada."""
    def _loop():
        while True:
            # cada 5 s (leer un json chico no cuesta nada) para que «en 15 segundos» signifique
            # eso de verdad y no «en 15 segundos más lo que tarde en darse cuenta»
            time.sleep(5)
            try:
                p = _leer(PENDIENTE)
                if p and float(p.get("cuando", 0)) < MANUAL and time.time() >= float(p.get("cuando", 0)):
                    ok, _ = aplicar(puerto, version_actual)
                    if ok:
                        time.sleep(2)          # que el ayudante levante antes de apagarnos
                        apagar()
                        return
            except Exception:
                pass
    threading.Thread(target=_loop, daemon=True).start()
