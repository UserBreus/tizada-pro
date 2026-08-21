"""EL AYUDANTE. Corre SUELTO (no es hijo del servidor) y hace el reemplazo con el programa apagado.

    py actualizador.py <carpeta_app> <paquete.zip> <puerto> <version>

Por qué existe: Windows bloquea los archivos de un programa mientras corre, así que TIZADA PRO no
puede pisarse a sí mismo. Este ayudante espera a que se apague, guarda una copia, descomprime la
versión nueva, la levanta y le pregunta si está bien. **Si no contesta, restaura la copia.**

NUNCA toca `datos/`, `entrada/` ni `config_publicado.bat`: el paquete no los trae y el respaldo
tampoco los incluye. Sólo se reemplaza el programa.
"""
import os, sys, json, time, socket, shutil, zipfile, subprocess, urllib.request

TAREA = "TIZADA PRO"
ESPERA_APAGADO = 90          # s a que el servidor libere el puerto
ESPERA_SALUD = 120           # s a que la versión nueva conteste que está bien

# CÓMO SE PRENDE Y SE APAGA EL SERVIDOR, según dónde corra: en Windows es una TAREA PROGRAMADA
# (`schtasks`), en Linux un SERVICIO de systemd. Sin esta distinción el ayudante descomprimía bien
# y después no sabía levantar NADA —`schtasks` no existe en Linux—, así que no volvían ni la versión
# nueva ni la anterior: el rollback también depende de poder arrancar. (2026-08-04)
ES_WINDOWS = os.name == "nt"
SERVICIO = os.environ.get("TIZADA_SERVICIO") or "tizadapro"   # nombre del unit de systemd


def log(carpeta, txt):
    linea = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {txt}"
    print(linea)
    try:
        with open(os.path.join(carpeta, "_actualizacion", "actualizador_log.txt"), "a",
                  encoding="utf-8") as fh:
            fh.write(linea + "\n")
    except Exception:
        pass


def puerto_libre(p):
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", int(p))); return True
        except OSError:
            return False


def esperar_libre(puerto, segundos):
    for _ in range(segundos):
        if puerto_libre(puerto):
            return True
        time.sleep(1)
    return False


def salud(puerto, segundos):
    """¿La versión que quedó levantada contesta que está sana? Es el semáforo de todo esto."""
    fin = time.time() + segundos
    while time.time() < fin:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/salud", timeout=10) as r:
                if json.loads(r.read()).get("ok"):
                    return True
        except Exception:
            pass
        time.sleep(3)
    return False


# Lo que se respalda y se reemplaza: SOLO el programa. Espejo de lo que trae el paquete.
CODIGO_ARCH = (".py", ".bat", ".md")
CODIGO_DIRS = ("frontend", "db", "catalogo_fuentes")
NO_TOCAR = {"config_publicado.bat", "arrancar.bat", "actualizador.py"}


def respaldar(app, destino):
    os.makedirs(destino, exist_ok=True)
    for f in os.listdir(app):
        ruta = os.path.join(app, f)
        if os.path.isfile(ruta) and f.endswith(CODIGO_ARCH) and f not in NO_TOCAR:
            shutil.copy2(ruta, os.path.join(destino, f))
    for d in CODIGO_DIRS:
        o = os.path.join(app, d)
        if os.path.isdir(o):
            shutil.copytree(o, os.path.join(destino, d), dirs_exist_ok=True)
    if os.path.exists(os.path.join(app, "VERSION")):
        shutil.copy2(os.path.join(app, "VERSION"), os.path.join(destino, "VERSION"))


def restaurar(respaldo, app):
    for f in os.listdir(respaldo):
        o, d = os.path.join(respaldo, f), os.path.join(app, f)
        if os.path.isdir(o):
            shutil.copytree(o, d, dirs_exist_ok=True)
        else:
            shutil.copy2(o, d)


def _systemctl(accion, app=None):
    """`systemctl <accion> <SERVICIO>` (Linux). True si el comando salió bien.

    Se prueba PRIMERO sin sudo (por si el ayudante corriera como root) y después con `sudo -n`: el
    sistema NO corre como root a propósito —usuario `tizada`, sin shell— y un usuario común no puede
    manejar un servicio. La regla de sudoers que lo habilita está acotada a estas tres acciones sobre
    ESTA unidad y se instala una sola vez (ver `DESPLIEGUE.md` §11.b).
    `-n` = que NO pregunte contraseña: acá no hay nadie para tipearla, así que es mejor fallar rápido
    y que quede en el log que falta la regla, antes que colgarse esperando una respuesta."""
    for cmd in (["systemctl", accion, SERVICIO], ["sudo", "-n", "systemctl", accion, SERVICIO]):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
        except (FileNotFoundError, OSError):
            continue
        if r.returncode == 0:
            return True
    log(app, f"systemctl {accion} {SERVICIO} FALLÓ (¿falta la regla de sudoers?)")
    return False


def parar(app=None):
    """Apaga el servidor por el mecanismo del sistema.

    🔴 EN LINUX ES IMPRESCINDIBLE, Y NO ALCANZA CON QUE EL PROCESO SE MUERA: el unit de systemd
    tiene `Restart=always`, así que el servidor que se apaga solo vuelve a los 5 segundos. Sin
    pararlo por systemd, el ayudante terminaría descomprimiendo por debajo de un servidor VIVO, que
    encima seguiría sirviendo el código viejo desde memoria. `systemctl stop` le dice a systemd que
    no lo relance hasta nueva orden."""
    if ES_WINDOWS:
        subprocess.run(["schtasks", "/end", "/tn", TAREA], capture_output=True)
        return True
    return _systemctl("stop", app)


def _plan_b(app):
    """Segundo intento de arranque, para cuando el mecanismo normal dijo que sí pero el servidor no
    contesta. Windows: `arrancar.bat` a mano, sin la tarea. Linux: `restart`, que además saca a la
    unidad del estado `failed` (un `start` sobre una unidad fallida no siempre arranca)."""
    if not ES_WINDOWS:
        return _systemctl("restart", app)
    bat = os.path.join(app or os.getcwd(), "arrancar.bat")
    if not os.path.exists(bat):
        return False
    flags = 0x00000008 | 0x00000200
    subprocess.Popen(["cmd", "/c", bat], cwd=(app or os.getcwd()), creationflags=flags,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
    return True


def arrancar(app=None, puerto=None):
    """Levanta por el mecanismo del sistema (tarea de Windows / servicio systemd), igual que después
    de un reinicio, y COMPRUEBA que haya levantado de verdad.

    OJO: `schtasks /run` contesta 0 («intenté ejecutarla») aunque después no ejecute NADA — pasó en
    producción y el ayudante lo tomó por bueno: dio la actualización por exitosa con el servidor
    caído, y ni la versión nueva ni la anterior volvieron. Por eso, si el puerto no contesta, se
    reintenta con el plan B. Sin `puerto` no se puede verificar y se hace lo de antes."""
    if ES_WINDOWS:
        lanzado = subprocess.run(["schtasks", "/run", "/tn", TAREA],
                                 capture_output=True, text=True).returncode == 0
    else:
        lanzado = _systemctl("start", app)
    if puerto is None:
        if not lanzado:
            _plan_b(app)
        return True
    if salud(puerto, 45):
        return True
    log(app, "el servicio no levantó el servidor; se reintenta con el plan B")
    if _plan_b(app) and salud(puerto, 60):
        return True
    log(app, "NO se pudo levantar el servidor (ni por el servicio ni por el plan B)")
    return False


def resultado(carpeta, ok, version, detalle):
    d = os.path.join(carpeta, "_actualizacion")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "ultima.json"), "w", encoding="utf-8") as fh:
        json.dump({"ok": ok, "version": version, "cuando": time.time(), "detalle": detalle},
                  fh, ensure_ascii=False)
    for f in ("en_curso.json", "pendiente.json"):
        try:
            os.remove(os.path.join(d, f))
        except OSError:
            pass


def main():
    app, paquete, puerto, version = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    log(app, f"=== actualizando a {version} ===")

    # LINUX: hay que parar el SERVICIO ya, antes de esperar nada. Con `Restart=always` el proceso
    # que se apagó solo vuelve en 5 s, y descomprimiríamos por debajo de un servidor vivo. En Windows
    # la tarea es «al iniciar el sistema» y no relanza sola: ahí el apagado limpio que ya venía
    # funcionando alcanza, y no se toca.
    if not ES_WINDOWS:
        parar(app)
    if not esperar_libre(puerto, ESPERA_APAGADO):
        log(app, "el servidor no se apagó; se lo fuerza")
        parar(app)
        esperar_libre(puerto, 20)

    respaldo = os.path.join(app, "_actualizacion", "respaldo")
    shutil.rmtree(respaldo, ignore_errors=True)
    try:
        respaldar(app, respaldo)
        log(app, f"respaldo hecho en {respaldo}")
    except Exception as e:
        log(app, f"NO se pudo respaldar ({e}); se cancela para no arriesgar")
        arrancar(app, puerto)
        resultado(app, False, version, f"no se pudo respaldar: {e}")
        return

    try:
        with zipfile.ZipFile(paquete) as z:
            z.extractall(app)                  # el paquete NO trae datos/ ni entrada/
        log(app, "paquete descomprimido")
    except Exception as e:
        log(app, f"falló al descomprimir ({e}); se restaura")
        restaurar(respaldo, app)
        arrancar(app, puerto)
        resultado(app, False, version, f"no se pudo descomprimir: {e}")
        return

    arrancar(app, puerto)
    if salud(puerto, ESPERA_SALUD):
        log(app, f"OK: {version} andando")
        resultado(app, True, version, "actualizado y verificado")
        try:
            os.remove(paquete)
        except OSError:
            pass
        return

    # No contestó: se vuelve atrás. El sistema NUNCA queda caído por una actualización mala.
    log(app, "la versión nueva no contestó; VOLVIENDO A LA ANTERIOR")
    parar(app)
    esperar_libre(puerto, 30)
    restaurar(respaldo, app)
    arrancar(app, puerto)
    volvio = salud(puerto, 90)
    log(app, "restaurada la versión anterior" + ("" if volvio else " (¡tampoco contesta!)"))
    resultado(app, False, version,
              "la versión nueva no respondió; se restauró la anterior"
              + ("" if volvio else " — y la anterior TAMPOCO responde, revisar servidor_log.txt"))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            log(sys.argv[1], f"ERROR INESPERADO: {e}")
            resultado(sys.argv[1], False, sys.argv[4] if len(sys.argv) > 4 else "?", str(e))
            arrancar(sys.argv[1])
        except Exception:
            pass
