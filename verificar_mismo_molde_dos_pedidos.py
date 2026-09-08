"""
CONTRATO: **EL MISMO MOLDE EN DOS PEDIDOS NO SE PISA** — `py verificar_mismo_molde_dos_pedidos.py`.

🔴 LO QUE LO MOTIVÓ (pregunta del usuario 2026-09-08): «si subo 2 veces el mismo molde en 2 pedidos
diferentes, ¿no pueden colapsarse entre ellos?». Cada molde vive en su propia carpeta
(`entrada/<pid>`, con un id al azar), así que los archivos no chocan. Pero hay UNA cosa que las dos
subidas comparten a propósito: **la caché del desplegado, guardada bajo el sha1 del ARCHIVO** — es
lo que hace que la segunda subida del mismo molde tarde 1 s en vez de 25. Ahí sí se podían pisar:

  1. el temporal de escritura era `<clave>.tmp`, **uno solo para todos**: la subida que llegaba
     segunda hacía `rmtree` de ese temporal mientras la primera copiaba adentro → árbol a medias;
  2. `os.replace` de una CARPETA falla en Windows si el destino existe: la excepción se tragaba y
     quedaban ~128 MB de `.tmp` tirados para siempre;
  3. el barrido de las entradas viejas podía borrar justo la carpeta que otra subida estaba
     copiando.

Lo que se verifica, con DIEZ hilos guardando y leyendo la caché del mismo archivo a la vez:

  1. **Nadie se lleva media caché**: toda copia que se da por buena tiene TODOS los archivos, con
     los mismos tamaños que el original.
  2. **No queda basura**: ni un `.tmp-…` en pie al terminar.
  3. **Una sola entrada por archivo y versión**, y las versiones viejas del mismo archivo se van.
  4. **Una copia incompleta NO se usa**: si la caché está mutilada, se rehace el desplegado (se
     devuelve None) en vez de dar por bueno un molde al que le faltan mesas.
  5. **Dos moldes distintos con el MISMO archivo son independientes**: cada uno con su carpeta y su
     `pid`; tocar el desplegado de uno no cambia el del otro.
  6. **Pedir la ruta de un molde que ya no existe no lo resucita**: `_ruta_entrada`/`_ruta_datos`
     creaban su carpeta con sólo consultarla, y así aparecían carpetas huérfanas de moldes
     borrados (las que hubo que limpiar a mano el 2026-09-08).

⚠️ No toca nada del usuario: trabaja en un temporal propio, con archivos de mentira; `DATOS` apunta
ahí y el módulo `db` es un doble que explota si alguien intenta ir a MSSQL.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import types

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = os.path.dirname(os.path.abspath(__file__))
_TMP = tempfile.mkdtemp(prefix="verif_cache_despl_")
os.environ["TIZADA_DATOS"] = os.path.join(_TMP, "datos")
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_FUENTES"] = os.path.join(RAIZ, "catalogo_fuentes")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"

_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n}) — revisar el aislamiento")))
sys.modules["db"] = _falso_db

sys.path.insert(0, RAIZ)
import servidor as S            # noqa: E402
import piezas_con_diseno as PD  # noqa: E402

# LO QUE SE PRUEBA ACÁ ES LA CACHÉ, NO EL DESPLEGADO. `desplegado_listo` abre el .ai con MuPDF y
# compara el sello de cada mesa: para eso haría falta un molde de verdad (123 MB). Se reemplaza por
# «la carpeta tiene páginas», que es la condición que a la caché le importa.
PD.desplegado_listo = lambda p: (os.path.isdir(PD._carpeta_desplegado(p))
                                 and any(f.endswith(".pdf") for f in os.listdir(PD._carpeta_desplegado(p))))


def _listar_cache():
    """Lo que hay en la caché (vacío si ni siquiera existe la carpeta)."""
    try:
        return sorted(os.listdir(S._CACHE_DESPL))
    except FileNotFoundError:
        return []


FALLOS = []


def ok(cond, que):
    print(("  OK   " if cond else "  FALLA ") + que)
    if not cond:
        FALLOS.append(que)


# ── EL MOLDE DE MENTIRA ───────────────────────────────────────────────────────────────────────
# No hace falta un .ai de 123 MB: la caché copia una CARPETA de desplegado, sea de quien sea. Se
# arma una con el mismo peso relativo (varios archivos, uno grande) para que la copia tarde lo
# suficiente como para que los hilos se pisen de verdad.
def _molde_falso(dir_, nombre="plantilla.ai", mesas=3):
    os.makedirs(dir_, exist_ok=True)
    path = os.path.join(dir_, nombre)
    io.open(path, "wb").write(b"%PDF-1.6 molde de prueba\n" + b"x" * 4096)
    despl = PD._carpeta_desplegado(path)
    os.makedirs(despl, exist_ok=True)
    for m in range(1, mesas + 1):
        json.dump({"mesa": m, "contornos": [{"n": f"pieza {m}"}]},
                  io.open(os.path.join(despl, f"m{m}.json"), "w", encoding="utf-8"))
        io.open(os.path.join(despl, f"m{m}.pdf"), "wb").write(b"%PDF-1.6\n" + b"y" * (2 << 20))
    json.dump({"talles": ["S", "M"]}, io.open(os.path.join(despl, "manifest.json"), "w", encoding="utf-8"))
    return path


ORIGEN = _molde_falso(os.path.join(_TMP, "origen"))
ESPERADO = S._contenido_carpeta(PD._carpeta_desplegado(ORIGEN))
ALTA = {"talles": ["S", "M"], "mesas": 3}

print("[1] DIEZ subidas del MISMO archivo a la vez (5 guardan, 5 leen)")
tomados, errores = [], []


def _guardar():
    try:
        d = tempfile.mkdtemp(dir=_TMP)
        p = _molde_falso(d)
        S._cache_desplegado_guardar(p, ALTA)
    except Exception as e:
        errores.append(f"guardar: {e!r}")


def _tomar():
    try:
        d = tempfile.mkdtemp(dir=_TMP)
        p = _molde_falso(d, mesas=0)          # sin desplegado propio: o lo toma de la caché, o None
        r = S._cache_desplegado_tomar(p)
        if r is not None:
            tomados.append(S._contenido_carpeta(PD._carpeta_desplegado(p)))
    except Exception as e:
        errores.append(f"tomar: {e!r}")


_guardar()          # una primero, para que los lectores de la carrera tengan qué leer
hilos = [threading.Thread(target=_guardar if i % 2 == 0 else _tomar) for i in range(10)]
for h in hilos:
    h.start()
for h in hilos:
    h.join()

ok(not errores, f"nadie explota con las diez subidas a la vez ({errores[:2]})")
ok(bool(tomados), f"alguna subida alcanzó a usar la caché ({len(tomados)} de 5)")
ok(all(t == ESPERADO for t in tomados),
   f"🔴 toda copia que se dio por buena está COMPLETA ({sum(1 for t in tomados if t != ESPERADO)} a medias)")
_basura = [d for d in _listar_cache() if ".tmp" in d]
ok(not _basura, f"no queda ningún temporal tirado ({_basura})")
_entradas = _listar_cache()
ok(len(_entradas) == 1, f"una sola entrada para ese archivo ({_entradas})")

print("\n[2] LAS VERSIONES VIEJAS DEL MISMO ARCHIVO SE VAN (128 MB cada una)")
_clave = _entradas[0]
_vieja = os.path.join(S._CACHE_DESPL, _clave.rsplit("_", 1)[0] + "_v000")
shutil.copytree(os.path.join(S._CACHE_DESPL, _clave), _vieja)
shutil.rmtree(os.path.join(S._CACHE_DESPL, _clave))       # para que el guardado la vuelva a escribir
S._cache_desplegado_guardar(_molde_falso(tempfile.mkdtemp(dir=_TMP)), ALTA)
ok(not os.path.exists(_vieja), "la entrada del MISMO archivo con el desplegado viejo se borra")
ok(os.path.isdir(os.path.join(S._CACHE_DESPL, _clave)), "y la de la versión de hoy queda")

print("\n[3] UNA CACHÉ MUTILADA NO SE USA (se rehace el desplegado)")
os.remove(os.path.join(S._CACHE_DESPL, _clave, "desplegado", "m2.pdf"))
_p = _molde_falso(tempfile.mkdtemp(dir=_TMP), mesas=0)
_r = S._cache_desplegado_tomar(_p)
ok(_r is None, "con la caché incompleta devuelve None (no da por bueno un molde sin mesas)")
ok(not os.path.isdir(PD._carpeta_desplegado(_p)),
   "y no deja el desplegado a medias al lado del molde")

print("\n[4] DOS MOLDES CON EL MISMO ARCHIVO SON INDEPENDIENTES")
shutil.rmtree(S._CACHE_DESPL, ignore_errors=True)
_a = _molde_falso(os.path.join(_TMP, "pedido_a"))
_b = _molde_falso(os.path.join(_TMP, "pedido_b"))
S._cache_desplegado_guardar(_a, ALTA)
_ok_b = S._cache_desplegado_tomar(_b)
ok(PD._carpeta_desplegado(_a) != PD._carpeta_desplegado(_b),
   "cada molde tiene SU carpeta de desplegado, aunque el archivo sea el mismo")
io.open(os.path.join(PD._carpeta_desplegado(_a), "m1.pdf"), "wb").write(b"CAMBIADO")
ok(io.open(os.path.join(PD._carpeta_desplegado(_b), "m1.pdf"), "rb").read() != b"CAMBIADO",
   "🔴 tocar el desplegado de un pedido NO cambia el del otro")
_pids = {S.os.path.basename(os.path.dirname(_a)), S.os.path.basename(os.path.dirname(_b))}
ok(len(_pids) == 2, "y son dos moldes distintos, con su propia carpeta")

print("\n[5] PEDIR LA RUTA DE UN MOLDE QUE YA NO EXISTE NO LO RESUCITA")
# 🔴 Es lo que llenaba `entrada/` de carpetas vacías: `_ruta_entrada`/`_ruta_datos` hacían
# `makedirs` aunque sólo se estuviera preguntando si un archivo existe.
_muerto = "prod_20200101_000000_zzzz"
S._ruta_entrada("plantilla.ai", _muerto)
S._ruta_datos("piezas.json", _muerto)
S._ruta_entrada("arte.ai", _muerto, sub=os.path.join("disenos", "golero"))
ok(not os.path.isdir(os.path.join(S.ENTRADA, _muerto)),
   "consultar la ruta de un molde borrado NO le crea la carpeta en entrada/")
ok(not os.path.isdir(os.path.join(S.DATOS, "productos", _muerto)),
   "…ni en datos/productos/")
# …pero un molde que SÍ existe sigue armando sus subcarpetas: las necesita subir el arte de un diseño
_vivo = "prod_vivo_de_prueba"
os.makedirs(os.path.join(S.ENTRADA, _vivo), exist_ok=True)
_ra = S._ruta_entrada("arte.ai", _vivo, sub=os.path.join("disenos", "golero"), original=True)
ok(os.path.isdir(os.path.dirname(_ra)),
   "y un molde que existe sí arma la subcarpeta de su diseño (para poder subirle el arte)")

shutil.rmtree(_TMP, ignore_errors=True)
print("\n" + ("  OK: el mismo archivo en dos pedidos no se pisa"
             if not FALLOS else f"  {len(FALLOS)} FALLA(S): " + " · ".join(FALLOS)))
sys.exit(1 if FALLOS else 0)
