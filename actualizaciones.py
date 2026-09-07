"""RECEPTOR DE ACTUALIZACIONES (lado servidor publicado). Ver `PLAN_PUBLICACION.md` §Etapa 2.

El taller arma un paquete y lo SUBE por HTTPS a `/api/actualizacion/subir` con la clave. Acá se
guarda, se verifica y se anota para cuándo. A la hora indicada (o con «aplicar ya») se lanza
`actualizador.py`, que es un proceso APARTE: el programa no puede reemplazar sus propios archivos
mientras corre (Windows los tiene tomados), así que el ayudante espera a que se apague y trabaja.

Lo que NUNCA se toca: `datos/` y `entrada/`. El paquete ni siquiera los trae.
"""
import os, json, time, zipfile, hashlib, threading, subprocess, sys

# EL REGISTRO (pedido del usuario 2026-09-01): que cada paso de una actualización deje dicho qué
# pasó y POR QUÉ, para poder verlo desde la pantalla y no por SSH. Con guarda: si por lo que sea no
# está, el updater tiene que seguir funcionando igual.
try:
    import registro as LOG
except Exception:                                # pragma: no cover
    class LOG:                                   # noqa: N801 - reemplazo mudo
        @staticmethod
        def error(*a, **k): pass
        @staticmethod
        def aviso(*a, **k): pass
        @staticmethod
        def info(*a, **k): pass

AQUI = os.path.dirname(os.path.abspath(__file__))
CARPETA = os.path.join(AQUI, "_actualizacion")
PENDIENTE = os.path.join(CARPETA, "pendiente.json")
PAQUETE = os.path.join(CARPETA, "pendiente.zip")
ULTIMA = os.path.join(CARPETA, "ultima.json")
EN_CURSO = os.path.join(CARPETA, "en_curso.json")
# La SEÑAL del ayudante: «ya descomprimí, la versión nueva está en el disco». Hasta que
# aparece, el servidor no se apaga (ver `esperar_al_ayudante`).
LISTO = os.path.join(CARPETA, "listo.flag")
ESPERA_AYUDANTE = 240        # s como mucho: si algo se colgó, igual se sigue

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


# Cómo se aplica una actualización sin ayuda de nadie:
#   "windows"  → el ayudante va DETACHED y la tarea programada no lo toca.
#   "systemd"  → el de siempre en Linux: parar el servicio, descomprimir, arrancarlo. Necesita
#                `KillMode=process` (drop-in, root) o el `systemctl stop` mata al ayudante.
#   "reinicio" → SIN root: se descomprime con el servidor vivo y, cuando éste se apaga,
#                `Restart=always` lo revive con el código nuevo. Nunca se llama a `systemctl stop`,
#                así que el `KillMode` no importa. Es el que permite que el VPS se actualice solo
#                aunque nadie haya puesto el drop-in.
MODO_WINDOWS, MODO_SYSTEMD, MODO_REINICIO = "windows", "systemd", "reinicio"


def _prop_servicio(servicio, prop):
    """Una propiedad del unit, tal como la reporta systemd (sólo lectura, no pide sudo)."""
    r = subprocess.run(["systemctl", "show", "-p", prop, "--value", servicio],
                       capture_output=True, text=True, timeout=15)
    return (r.stdout or "").strip().lower()


def como_se_instala():
    """¿Cómo puede aplicarse una actualización acá? → (modo|None, detalle).

    En Windows, siempre. En Linux hay DOS caminos y se prefiere el que no necesita permisos:

      · **`Restart=always`** (o `on-failure`) → modo **«reinicio»**: se descomprime con el servidor
        todavía vivo y, cuando se apaga, systemd lo levanta solo con la versión nueva. No hace falta
        el drop-in ni root.
      · **`KillMode=process`** → modo **«systemd»**, el clásico: parar, descomprimir, arrancar.

    Si no se puede consultar el servicio, se contesta NO: mejor pedir que lo apliquen a mano que
    apagar un servidor de producción (pasó el 2026-08-21)."""
    if os.name == "nt":
        return MODO_WINDOWS, "windows"
    servicio = os.environ.get("TIZADA_SERVICIO") or "tizadapro"
    try:
        restart = _prop_servicio(servicio, "Restart")
        kill = _prop_servicio(servicio, "KillMode")
    except Exception as e:
        return None, f"no se pudo consultar el servicio ({e})"
    if restart in ("always", "on-failure", "on-abnormal"):
        return MODO_REINICIO, f"Restart={restart} (systemd lo vuelve a levantar solo)"
    if kill == "process":
        return MODO_SYSTEMD, "KillMode=process"
    if not (restart or kill):
        return None, f"el servicio «{servicio}» no contestó cómo está configurado"
    return None, (f"«{servicio}» no se puede actualizar solo: Restart={restart or '?'} y "
                  f"KillMode={kill or '?'}. Alcanza con cualquiera de las dos — `Restart=always` "
                  f"(recomendado) o `KillMode=process` (ver DESPLIEGUE.md §11.b)")


def puede_instalarse_solo():
    """Compatibilidad: (ok, detalle). El modo lo decide `como_se_instala()`."""
    modo, detalle = como_se_instala()
    return (modo is not None), detalle


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
    # `so` = dónde corre ESTE servidor. En Linux hay DOS caminos para actualizarse solo y basta con
    # uno: `Restart=always` (modo «reinicio», sin root) o `KillMode=process` (modo clásico).
    _modo, _solo_det = como_se_instala()
    _solo_ok = _modo is not None
    out = {"version": version_actual, "so": ("windows" if os.name == "nt" else "linux"),
           # `puede_solo` = si este servidor sabe aplicar una actualización sin ayuda humana.
           # La pantalla del taller lo muestra ANTES de publicar, para no elegir a ciegas.
           "puede_solo": _solo_ok, "puede_solo_detalle": _solo_det, "modo_instalacion": _modo,
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
    LOG.info("actualizacion", f"Llegó el paquete de la versión {ver_zip or version}",
             f"{len(datos)} bytes, firma verificada. "
             + ("Queda para aplicar A MANO." if float(cuando) >= MANUAL
                else f"Se aplica {'ya' if float(cuando) <= time.time() else 'a la hora pedida'}."),
             version=ver_zip or version, bytes=len(datos))
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
    _modo, _det = como_se_instala()
    _ok = _modo is not None
    if not _ok:
        p["cuando"] = MANUAL
        p["aparcada"] = True
        _escribir(PENDIENTE, p)
        _escribir(ULTIMA, {"ok": False, "version": p.get("version"), "cuando": time.time(),
                           "detalle": f"no se instaló sola para no dejar el servidor apagado "
                                      f"({_det}); el paquete quedó esperando para aplicarlo a mano"})
        LOG.aviso("actualizacion", f"La versión {p.get('version')} NO se instaló sola",
                  f"Este servidor no puede hacerlo sin ayuda: {_det}. El paquete quedó sano y "
                  f"esperando para aplicarlo a mano — no se apagó nada.",
                  version=p.get("version"))
        return False, _det
    # ⚠️ Una señal de una actualización anterior haría que el servidor se apague AL INSTANTE,
    # creyendo que la versión nueva ya está en el disco. Se limpia antes de empezar.
    try:
        os.remove(LISTO)
    except OSError:
        pass
    _escribir(EN_CURSO, {"desde": version_actual, "hacia": p.get("version"), "inicio": time.time()})
    exe = sys.executable or "py"
    cmd = [exe, os.path.join(AQUI, "actualizador.py"), AQUI, PAQUETE, str(puerto),
           str(p.get("version") or ""), _modo]
    # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP: el ayudante tiene que SOBREVIVIR a que el
    # servidor se apague. Si fuese hijo normal, se lo llevaría puesto y quedaría todo a medias.
    # 🔴 WINDOWS — Y ESO NO ALCANZABA: el servidor se mete a sí mismo en un JOB OBJECT con
    # `KILL_ON_JOB_CLOSE` (para que los procesos de dibujo no queden sueltos al reiniciar) y los
    # hijos HEREDAN el Job aunque nazcan «detached». Cuando el servidor hacía `os._exit(0)` para
    # dejarse reemplazar, Windows mataba el Job entero y con él al ayudante, en el peor momento:
    # a mitad de descomprimir. CREATE_BREAKAWAY_FROM_JOB lo saca del Job (el Job lo permite desde
    # que lleva BREAKAWAY_OK, ver `servidor._atar_hijos_a_este_proceso`).
    flags = (0x00000008 | 0x00000200 | 0x01000000) if os.name == "nt" else 0
    # 🔴 LINUX — LAS DOS MITADES, LAS DOS NECESARIAS (2026-08-21, se pagó en producción):
    #   (a) `start_new_session` = sesión propia (`setsid`): no le llegan las señales dirigidas al
    #       grupo del servidor.
    #   (b) `KillMode=process` en el unit (drop-in `tizadapro.service.d/kill.conf`, ver
    #       DESPLIEGUE.md §11.b): **de un cgroup NO SE SALE** — la sesión nueva no lo saca del
    #       cgroup del servicio, así que con el `KillMode` por defecto (`control-group`) el
    #       `systemctl stop` que el propio ayudante pide mata el grupo ENTERO, ayudante incluido.
    # Pasó en la primera publicación al VPS: el log del ayudante quedó en la primera línea y el
    # servicio se apagó sin versión nueva ni vieja (`Restart=always` no revive un stop deliberado).
    def _lanzar(_flags):
        return subprocess.Popen(cmd, cwd=AQUI, creationflags=_flags, close_fds=True,
                                start_new_session=(os.name != "nt"),
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        _lanzar(flags)
    except OSError as e:
        # Si este proceso vive dentro de un Job que NO permite salirse (lo lanzó otra cosa: una
        # tarea con su propio Job, un IDE), `CreateProcess` contesta «acceso denegado». Se
        # reintenta sin pedir la salida: la actualización arranca igual, pero si el servidor se
        # apaga el ayudante puede irse con él — por eso queda avisado en el registro.
        LOG.aviso("actualizacion", "El ayudante no pudo salirse del grupo de procesos del servidor",
                  f"{type(e).__name__}: {e}. Se lanzó igual. Si la actualización queda a medias, "
                  "es por acá: este servidor corre dentro de un grupo que no deja salir a nadie.")
        _lanzar(flags & ~0x01000000)
    LOG.info("actualizacion", f"Empezó la instalación de la versión {p.get('version')}",
             f"Modo «{_modo}» ({_det}). El servidor espera a que el ayudante avise que la versión "
             f"nueva ya está en el disco, y recién ahí se apaga.",
             version=p.get("version"), modo=_modo, desde=version_actual)
    return True, p.get("version")


def recuperar_si_quedo_a_medias():
    """Si el servidor arranca y había una actualización EN CURSO, quedó a mitad de camino (corte de
    luz, reinicio). El respaldo lo restaura el propio ayudante; acá sólo se deja constancia para
    que se vea en pantalla y no quede la marca puesta para siempre."""
    m = _leer(EN_CURSO)
    if not m:
        return
    # 🔴 UN ARRANQUE EN EL MEDIO NO ES UN FRACASO. En el modo «reinicio» el servidor se apaga y
    # `Restart=always` lo levanta enseguida MIENTRAS el ayudante todavía trabaja: ese arranque
    # declaraba fallida una actualización que estaba saliendo bien, la aparcaba y dejaba la versión
    # vieja corriendo (pasó con la 1.0.32, 2026-09-01). Si el ayudante empezó recién, se lo deja
    # terminar: él escribe el resultado y borra esta marca. Recién si pasó el plazo se da por
    # interrumpida — ahí sí no hay nadie del otro lado.
    try:
        _edad = time.time() - float(m.get("inicio") or 0)
    except (TypeError, ValueError):
        _edad = 1e9
    if 0 <= _edad < ESPERA_AYUDANTE:
        return
    _escribir(ULTIMA, {"ok": False, "version": m.get("hacia"), "cuando": time.time(),
                       "detalle": "la actualización quedó interrumpida; el paquete quedó "
                                  "APARCADO para aplicarlo a mano (no se reintenta solo)"})
    LOG.error("actualizacion", f"La versión {m.get('hacia')} quedó a medias",
              f"El servidor arrancó y encontró una actualización marcada como «en curso» desde "
              f"hace {int(_edad)} s, sin noticias del ayudante. Se dio por interrumpida y el "
              f"paquete se APARCÓ (no se reintenta solo, para no entrar en un bucle de caídas). "
              f"El detalle de dónde se cortó está en _actualizacion/actualizador_log.txt.",
              version=m.get("hacia"), desde=m.get("desde"), segundos=int(_edad))
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


def esperar_al_ayudante():
    """🔴 NO APAGARSE HASTA QUE LA VERSIÓN NUEVA ESTÉ EN EL DISCO.

    Antes se esperaban **2 segundos** y listo, dando por hecho que el ayudante ya había hecho su
    trabajo. No alcanza: respaldar la carpeta y descomprimir tarda más. Con `Restart=always`,
    systemd levantaba el servidor VIEJO en el medio, ese arranque veía la actualización «en curso»
    y la declaraba interrumpida — versión sin aplicar y paquete aparcado (pasó con la 1.0.32,
    2026-09-01: el fallo quedó marcado 14 segundos después de publicar).

    Ahora se espera el `listo.flag` que el ayudante deja al terminar de descomprimir. Con tope, por
    si el ayudante muriera: pasado ese tiempo se sigue igual y la red de abajo
    (`recuperar_si_quedo_a_medias`) se encarga."""
    t0 = time.time()
    while time.time() - t0 < ESPERA_AYUDANTE:
        if os.path.exists(LISTO):
            time.sleep(1)                      # que termine de cerrar el archivo
            return True
        time.sleep(0.5)
    return False


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
                        esperar_al_ayudante()
                        apagar()
                        return
            except Exception:
                pass
    threading.Thread(target=_loop, daemon=True).start()
