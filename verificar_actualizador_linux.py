"""
CONTRATO DEL ACTUALIZADOR EN LINUX — se corre con `py verificar_actualizador_linux.py`.

Existe por una regresión que YA pasó y que no da la cara enseguida: el repo se quedó con la
versión Windows-only de `actualizador.py` mientras el servidor corría una adaptada a systemd, y
como ese archivo **viaja dentro del paquete de actualización**, publicar desde el repo se la
habría pisado. El daño no aparece en esa actualización —la que está corriendo ya tiene su código
en memoria— sino en la SIGUIENTE: `schtasks` no existe en Linux, así que el ayudante descomprime
y después no sabe levantar nada; y como el ROLLBACK también arranca por ahí, no vuelve ni la
versión nueva ni la anterior. Servidor caído, sin vuelta atrás.

Este contrato exige que convivan las DOS ramas. No toca la red ni servicios: reemplaza
`subprocess.run` por un espía y mira qué comandos se habrían ejecutado.
"""
import importlib.util
import inspect
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
FALLOS = []


def _falla(txt):
    FALLOS.append(txt)


class _Espia:
    """Sustituto de `subprocess`: anota los comandos en vez de ejecutarlos."""

    def __init__(self, exito=True):
        self.cmds = []
        self.exito = exito

    def run(self, cmd, *a, **k):
        self.cmds.append(list(cmd))

        class _R:
            returncode = 0 if self.exito else 1
            stdout = stderr = ""
        return _R()

    def Popen(self, cmd, *a, **k):        # el plan B de Windows lanza así
        self.cmds.append(list(cmd))
        return None

    DEVNULL = -3


def _cargar(es_windows, servicio="tizadapro", exito=True):
    """Carga `actualizador.py` FRESCO, forzando la plataforma y espiando los comandos."""
    os.environ["TIZADA_SERVICIO"] = servicio
    spec = importlib.util.spec_from_file_location("_act_verif", os.path.join(AQUI, "actualizador.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.ES_WINDOWS = es_windows
    espia = _Espia(exito)
    m.subprocess = espia
    return m, espia


def _cmds_txt(espia):
    return [" ".join(str(x) for x in c) for c in espia.cmds]


# ── 1. Las dos ramas existen ────────────────────────────────────────────────────────────
m, _ = _cargar(True)
for f in ("ES_WINDOWS", "SERVICIO", "_systemctl", "parar", "arrancar", "_plan_b"):
    if not hasattr(m, f):
        _falla(f"falta `{f}` en actualizador.py (¿se pisó con la versión vieja de Windows?)")

if FALLOS:
    # Sin esas piezas no tiene sentido seguir: los bloques que vienen las usan y el contrato
    # moriría con un traceback en vez de decir qué pasa. Se informa y se corta acá.
    print(f"\nx EL ACTUALIZADOR PERDIÓ EL SOPORTE DE LINUX ({len(FALLOS)}):\n")
    for f in FALLOS:
        print("    -", f)
    print("\n    Publicar así le devuelve al servidor Linux la versión Windows-only:")
    print("    la actualización SIGUIENTE lo deja apagado y sin rollback.")
    sys.exit(1)

# ── 2. El nombre del servicio sale del entorno ──────────────────────────────────────────
m, _ = _cargar(False, servicio="otro_nombre")
if getattr(m, "SERVICIO", None) != "otro_nombre":
    _falla("SERVICIO no respeta la variable TIZADA_SERVICIO")

# ── 3. LINUX: parar = `systemctl stop`, nunca schtasks ──────────────────────────────────
m, e = _cargar(False)
m.parar("/tmp/app")
cmds = _cmds_txt(e)
if not any("systemctl stop tizadapro" in c for c in cmds):
    _falla(f"en Linux `parar()` no hace systemctl stop (ejecutó: {cmds})")
if any("schtasks" in c for c in cmds):
    _falla("en Linux `parar()` llama a schtasks, que NO existe en Linux")

# ── 4. LINUX: si falla sin sudo, se reintenta con `sudo -n` (el sistema no corre como root) ──
m, e = _cargar(False, exito=False)
m.parar("/tmp/app")
cmds = _cmds_txt(e)
if not any(c.startswith("sudo -n systemctl stop") for c in cmds):
    _falla(f"en Linux no se reintenta con `sudo -n` (ejecutó: {cmds})")

# ── 5. LINUX: arrancar = `systemctl start`; el plan B es `restart` ──────────────────────
m, e = _cargar(False)
m.arrancar("/tmp/app")                     # sin puerto: no consulta salud (no toca la red)
if not any("systemctl start tizadapro" in c for c in _cmds_txt(e)):
    _falla(f"en Linux `arrancar()` no hace systemctl start (ejecutó: {_cmds_txt(e)})")

m, e = _cargar(False)
m._plan_b("/tmp/app")
if not any("systemctl restart tizadapro" in c for c in _cmds_txt(e)):
    # restart y no start a propósito: un `start` sobre una unidad en `failed` no siempre arranca
    _falla(f"en Linux el plan B no es systemctl restart (ejecutó: {_cmds_txt(e)})")

# ── 6. WINDOWS intacto: la tarea programada sigue siendo el camino ──────────────────────
m, e = _cargar(True)
m.parar("/tmp/app")
if not any("schtasks /end" in c for c in _cmds_txt(e)):
    _falla("en Windows `parar()` ya no usa la tarea programada (se rompió el taller)")

m, e = _cargar(True)
m.arrancar("/tmp/app")
if not any("schtasks /run" in c for c in _cmds_txt(e)):
    _falla("en Windows `arrancar()` ya no usa la tarea programada")

# ── 7. Ninguna llamada a schtasks fuera de una rama por plataforma ──────────────────────
# (fue exactamente así como se coló la versión Windows-only: llamadas sueltas, sin condicionar)
fuente = open(os.path.join(AQUI, "actualizador.py"), encoding="utf-8").read()
for fn in ("main", "arrancar", "_plan_b", "parar"):
    try:
        cuerpo = inspect.getsource(getattr(m, fn))
    except Exception:
        continue
    if "schtasks" in cuerpo and "ES_WINDOWS" not in cuerpo:
        _falla(f"`{fn}()` llama a schtasks sin preguntar por la plataforma")

# ── 8. En Linux hay que PARAR EL SERVICIO antes de esperar el apagado ───────────────────
# El unit tiene `Restart=always`: el proceso que se apaga solo vuelve en 5 s y descomprimiríamos
# por debajo de un servidor vivo (que además sigue sirviendo el código viejo desde memoria).
main_src = inspect.getsource(m.main)
i_parar = main_src.find("parar(app)")
i_esperar = main_src.find("esperar_libre(")
if i_parar < 0 or i_esperar < 0 or i_parar > i_esperar:
    _falla("`main()` no para el servicio ANTES de esperar el apagado (Restart=always lo revive)")

# ── 9. Las DOS mitades de la supervivencia del ayudante en Linux ────────────────────────
# (a) `aplicar()` lo lanza con sesión propia; (b) el unit lleva `KillMode=process`. La (a) sola
# NO alcanza — de un cgroup no se sale — y por eso el porqué tiene que estar escrito donde se
# lee: en el código y en la guía de despliegue. Sin esto se perdió el VPS una vez.
_ruta_act = os.path.join(AQUI, "actualizaciones.py")
if not os.path.exists(_ruta_act):
    # Sin el archivo no hay nada que exigir, pero callarlo sería peor: el contrato diría «OK»
    # sobre un sistema al que le falta la mitad del mecanismo.
    _falla("falta `actualizaciones.py` al lado de este contrato (¿carpeta incompleta?)")
else:
    _spec_act = importlib.util.spec_from_file_location("_act_mod_verif", _ruta_act)
    _ACT = importlib.util.module_from_spec(_spec_act)
    _spec_act.loader.exec_module(_ACT)
    # OJO: se busca el ARGUMENTO (`start_new_session=`), no la palabra suelta — el comentario que
    # explica el porqué también la nombra, y buscarla a secas daba OK con el arreglo ya borrado.
    if "start_new_session=" not in inspect.getsource(_ACT.aplicar):
        _falla("`actualizaciones.aplicar()` no lanza el ayudante con sesión propia "
               "(`start_new_session`): en Linux se lo lleva puesto la señal del servidor")
if os.path.exists(_ruta_act) and "KillMode" not in open(_ruta_act, encoding="utf-8").read():
    _falla("`actualizaciones.py` no explica que hace falta `KillMode=process`: el próximo que "
           "toque `aplicar()` no tiene cómo saber que la sesión propia es sólo la mitad")
_desp = os.path.join(AQUI, "DESPLIEGUE.md")
if os.path.exists(_desp) and "KillMode=process" not in open(_desp, encoding="utf-8").read():
    _falla("DESPLIEGUE.md no documenta el drop-in con `KillMode=process` (§11.b)")

if FALLOS:
    print(f"\nx EL ACTUALIZADOR NO CUMPLE EL CONTRATO DE LINUX ({len(FALLOS)}):\n")
    for f in FALLOS:
        print("    -", f)
    sys.exit(1)
print("OK actualizador: convive Windows (tarea programada) con Linux (systemd + sudo -n), "
      "y en Linux para el servicio antes de tocar los archivos")
