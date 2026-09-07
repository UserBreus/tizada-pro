# -*- coding: utf-8 -*-
"""
CONTRATO: EL REGISTRO DEL SISTEMA — `py verificar_registro.py`.

El caso (2026-09-01): una actualización al servidor publicado dijo «falló» y no había forma de
saber POR QUÉ desde ninguna pantalla — el motivo vivía en un archivo del VPS al que sólo se llega
por SSH. Pedido del usuario, en dos partes:

  1. «agregá logs a este sistema en la parte de configuración para poder ver las fallas y deje
     registrado el POR QUÉ»;
  2. «los logs deben ser sólo del sistema, o sea todo lo que abriría en un PowerShell; y lo que
     falle debe registrarse en algún ARCHIVO que no sea base de datos, con fecha y hora real».

Lo que este contrato protege:
  · el POR QUÉ de cada evento queda guardado (no sólo el título);
  · **el registro nunca rompe lo que estaba registrando** (un dato imposible de guardar no explota);
  · **no es la base de datos**: es un archivo de texto, y este contrato lo prueba con un doble de
    `db` que explota si alguien la toca ([[test-no-toca-mssql]]);
  · la CONSOLA queda guardada con **fecha y hora reales** en cada línea, sin dejar de salir por la
    ventana de siempre;
  · el registro **no se abre a internet**: pide sesión, o el token con el que el taller le habla al
    servidor publicado.

⚠️ No toca nada del usuario: todo pasa en una carpeta temporal que se borra al final.
"""
import io
import os
import sys
import time
import types
import shutil
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TMP = tempfile.mkdtemp(prefix="verif_registro_")
os.environ["TIZADA_DATOS"] = TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"
os.environ["TIZADA_TOKEN_ACT"] = "clave-de-prueba-1234"

_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError("LA PRUEBA INTENTO TOCAR MSSQL (db.%s) — revisar el aislamiento" % n)))
import copy as _cp                                                             # noqa: E402
_DOCS = {}
_falso_db.set_doc = lambda c, o: _DOCS.__setitem__(c, _cp.deepcopy(o))
_falso_db.get_doc = lambda c, default=None: _cp.deepcopy(_DOCS.get(c, default))
_falso_db.proyectar_catalogo = lambda cat: None
sys.modules["db"] = _falso_db
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registro as LOG                                                         # noqa: E402
LOG.usar_carpeta(os.path.join(TMP, "logs"))     # el registro de juguete, ANTES de importar servidor
import servidor as S                                                           # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


print("\n1 · CADA EVENTO GUARDA SU POR QUÉ (que es lo que se vino a buscar)")
LOG.limpiar()
LOG.error("actualizacion", "Falló la versión 1.0.32",
          "El ayudante seguía descomprimiendo cuando el servidor se apagó.",
          version="1.0.32", segundos=66)
LOG.aviso("pedido", "Una fila no se fabricó", "La fila 4 no tiene talle.")
LOG.info("sistema", "Arrancó", "Arranque normal.")
evs = LOG.leer(10)
ok(len(evs) == 3, "se guardaron los tres eventos")
ok(evs[0]["que"] == "Arrancó", "el más nuevo va primero")
falla = [e for e in evs if e["tipo"] == "error"][0]
ok("descomprimiendo" in falla["porque"], "🔴 el MOTIVO queda escrito, no sólo el título")
ok(falla["datos"]["version"] == "1.0.32" and falla["datos"]["segundos"] == 66,
   "los datos que hacen falta para entenderlo también")
ok(LOG.leer(10, tipo="error") and all(e["tipo"] == "error" for e in LOG.leer(10, tipo="error")),
   "el filtro por tipo deja sólo ese tipo")
ok([e["area"] for e in LOG.leer(10, area="pedido")] == ["pedido"], "y el filtro por área, igual")
r = LOG.resumen()
ok(r["total"] == 3 and r["errores"] == 1, "el resumen cuenta bien las fallas")


print("\n2 · EL REGISTRO NUNCA ROMPE LO QUE ESTABA REGISTRANDO")


class _Imposible(object):
    def __repr__(self):
        return "<no se puede guardar>"


ok(LOG.error("x", "con un dato raro adentro", "porque sí", cosa=_Imposible()) is not None,
   "🔴 un dato que no se puede guardar NO tumba el registro (se guarda como texto)")
_guardado = LOG.CARPETA
LOG.usar_carpeta(os.path.join(TMP, "no", "se", "puede", "\0"))   # una ruta imposible
ok(LOG.error("x", "sin poder escribir", "y sigue") is None,
   "🔴 si ni siquiera se puede escribir, devuelve None en vez de explotar")
LOG.usar_carpeta(_guardado)


print("\n3 · ES UN ARCHIVO DE TEXTO, NO LA BASE DE DATOS")
ok(os.path.exists(LOG.ARCHIVO), "los eventos viven en un archivo (%s)" % os.path.basename(LOG.ARCHIVO))
ok(LOG.ARCHIVO.endswith(".jsonl") and LOG.CONSOLA.endswith(".log"),
   "texto plano: se abre con cualquier cosa, sin la base de por medio")
ok(not _DOCS, "🔴 nada de esto pasó por la base (el doble de `db` no recibió una sola llamada)")
_datos_texto = io.open(LOG.ARCHIVO, encoding="utf-8").read()
ok("password" not in _datos_texto.lower() and "molde" not in _datos_texto.lower(),
   "no se guardó nada del trabajo del usuario")


print("\n4 · LA CONSOLA QUEDA GUARDADA CON FECHA Y HORA REALES")
# ⚠️ TRAMPA: `import servidor` ya enganchó el espejo, así que los `print` de ESTE contrato también
# van al archivo. Por eso todo lo que se cuenta acá lleva una marca propia — medir «cuántas líneas
# hay» daba un número que cambiaba solo (pasó al escribirlo, y parecía un bug del espejo).
M = "ZZ-PRUEBA"
LOG.limpiar_consola()
_real = io.StringIO()
_esp = LOG._Espejo(_real)
_esp.write(M + " hola desde el servidor\n")
_esp.write(M + " una linea ")
_esp.write("partida en dos\n")
mias = lambda: [l for l in LOG.leer_consola(500) if M in l]
lineas = mias()
ok(_real.getvalue() == M + " hola desde el servidor\n" + M + " una linea partida en dos\n",
   "🔴 lo que se imprime SIGUE saliendo por la ventana de siempre (el espejo no se lo queda)")
ok(len(lineas) == 2, "y quedó guardado, una línea por línea (un print partido no se parte)")
import re                                                                      # noqa: E402
ok(all(re.match(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2} ", l) for l in lineas),
   "🔴 cada línea empieza con la FECHA y la HORA reales")
ok(lineas[0].endswith("hola desde el servidor"), "y sigue el texto tal cual salió")
ok(LOG.leer_consola(500, buscar="partida en dos") == [lineas[1]],
   "buscar deja sólo las que dicen eso")
ok(LOG.leer_consola(1) == LOG.leer_consola(500)[-1:], "el límite trae las ÚLTIMAS, no las primeras")
_esp.write(M + " y esto no cerró la línea todavía")
ok(len(mias()) == 2, "lo que quedó a medias espera al salto (no se corta al azar)")


print("\n5 · LA VENTANA PUEDE FALLAR Y EL SERVIDOR SIGUE")


class _VentanaRota(object):
    def write(self, t):
        raise IOError("la ventana se cerró")

    def flush(self):
        raise IOError("idem")


_esp2 = LOG._Espejo(_VentanaRota())
try:
    _esp2.write("algo que igual hay que guardar\n")
    _esp2.flush()
    ok(True, "🔴 escribir con la ventana rota no lanza (pasó de verdad al correr sin consola)")
except Exception as e:
    ok(False, "escribir con la ventana rota explotó: %s" % e)
ok(any("igual hay que guardar" in l for l in LOG.leer_consola(50)),
   "…y la línea igual quedó guardada en el archivo")


print("\n6 · SE ROTA SOLO Y NO LLENA EL DISCO")
ok(LOG.MAX_BYTES <= 4 * 1024 * 1024 and LOG.MAX_CONSOLA <= 8 * 1024 * 1024,
   "hay un tope de tamaño para los dos archivos")
LOG.limpiar_consola()
_guarda = LOG.MAX_CONSOLA
# Se fuerza UNA rotación, no varias: son DOS archivos (el actual y el anterior), así que rotar
# muchas veces seguidas pisa el anterior — con el tope de verdad eso son megas de historia.
LOG.MAX_CONSOLA = 10 ** 9
for i in range(20):
    _esp.write("%s relleno numero %d\n" % (M, i))
LOG.MAX_CONSOLA = 100                                     # ahora lo escrito ya pasa el tope
_esp.write("%s la de despues de rotar\n" % M)
# ⚠️ Se mide TODO antes de informar nada: cada `print` de este contrato también va al archivo
# (el espejo está puesto), y con el tope en 100 un solo `OK` lo rotaba de nuevo y borraba la
# prueba. Pasó, y parecía que la rotación perdía historia.
_hay_vieja = os.path.exists(LOG.CONSOLA_VIEJA)
_liviano = os.path.getsize(LOG.CONSOLA) < 200
_m = mias()
LOG.MAX_CONSOLA = _guarda
_i_vieja = [i for i, l in enumerate(_m) if "numero 0" in l]
_i_nueva = [i for i, l in enumerate(_m) if "despues de rotar" in l]
ok(_hay_vieja, "al pasarse de tamaño, lo viejo se mueve al archivo anterior")
ok(_liviano, "y el actual arranca liviano")
ok(bool(_i_vieja) and bool(_i_nueva),
   "🔴 rotar NO esconde lo de antes: se leen los dos archivos")
ok(bool(_i_vieja) and bool(_i_nueva) and _i_vieja[0] < _i_nueva[0],
   "…y en orden: la más vieja arriba y la más nueva abajo, como en la ventana")


print("\n7 · EL REGISTRO NO SE ABRE A INTERNET")
S._USUARIOS_ON = True                                     # como en un sistema con usuarios de verdad
cli = S.app.test_client()
for ruta in ("/api/registro", "/api/consola"):
    ok(cli.get(ruta).status_code == 401, "%s sin sesión: 401" % ruta)
    ok(cli.get(ruta, headers={"X-Token-Act": "otra-clave"}).status_code == 401,
       "%s con una clave inventada: 401" % ruta)
    r = cli.get(ruta, headers={"X-Token-Act": "clave-de-prueba-1234"})
    ok(r.status_code == 200,
       "🔴 %s con el token del taller: entra (así el taller ve el registro del publicado)" % ruta)
ok(cli.get("/api/registro/limpiar", headers={"X-Token-Act": "clave-de-prueba-1234"}).status_code
   in (401, 404, 405),
   "🔴 el token deja LEER, no vaciar: el permiso es sólo para las dos rutas de lectura")
d = cli.get("/api/consola?limite=3", headers={"X-Token-Act": "clave-de-prueba-1234"}).get_json()
ok(isinstance(d.get("lineas"), list), "y contesta las líneas de la consola")

# El propio servidor tiene que estar espejando: si no, en el VPS no se guarda nada.
src = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "servidor.py"),
              encoding="utf-8").read()
ok("LOG.espejar_consola()" in src, "🔴 el servidor engancha el espejo al arrancar")
ok(src.find("LOG.espejar_consola()") < src.find("@app.get(\"/api/registro\")"),
   "…y lo hace temprano (lo que se imprima antes se pierde)")
ok("LOG.error(\"servidor\"" in src, "🔴 un error no previsto del servidor queda registrado")

shutil.rmtree(TMP, ignore_errors=True)
print()
if FALLOS:
    print("  %d FALLO(S) — el registro no está cumpliendo su parte:" % len(FALLOS))
    for f in FALLOS:
        print("   · " + f)
    sys.exit(1)
print("  OK: lo que falla queda anotado con su motivo, la consola entera queda guardada con")
print("      fecha y hora, y nada de eso pasa por la base ni se abre a internet.")
