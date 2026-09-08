# -*- coding: utf-8 -*-
"""
CONTRATO: NINGÚN PDF QUEDA ABIERTO — se corre con `py verificar_cierre_pdfs.py`.

En Windows un archivo abierto **no se puede reemplazar ni borrar** (WinError 5). Ya pasó: 4 de 5
artes trabados y el «error al cargar una imagen» que no era de la imagen. Por eso `motor_pedido`
lleva un registro de lo que abre (`MP._abrir`) y el servidor lo cierra al terminar cada request.
Este contrato cubre los tres lugares donde ese registro NO alcanza:

  1. **Los workers del ProcessPool** — son procesos que viven todo lo que vive el servidor, con un
     solo hilo, y **no tienen `teardown_request`**: sin cerrar a mano, cada talle dejaba el molde y
     el arte abiertos para siempre (memoria que sólo sube + archivos trabados con el server ocioso).
  2. **Los hilos de fondo** (la precarga del lienzo al subir el molde) — van por `_en_hilo`, que
     cierra al terminar; y **no se solapan consigo mismas**: son ~12 s leyendo el molde entero.
  3. **Los caminos de EXCEPCIÓN** — `aplanar_rip` reintenta en serie sobre el MISMO archivo:
     si el intento anterior dejó handles abiertos y temporales tirados, el reintento se topa con
     la hoja tomada.

⚠️ No toca nada del usuario: todo pasa en un temporal, con un PDF que arma esta misma prueba.
⚠️ Todo corre bajo `if __name__ == "__main__"`: el aplanado en paralelo levanta un ProcessPool y
   `spawn` re-importa ESTE módulo en cada worker — sin la guarda, cada worker repite la prueba.
"""
import os
import sys
import tempfile
import threading
import time
import types

_TMP = tempfile.mkdtemp(prefix="verif_pdfs_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = "localhost\\NO_EXISTE_ES_UNA_PRUEBA"

_falso = types.ModuleType("db")
_falso.__getattr__ = lambda n: (lambda *a, **k: None)
_falso.get_doc = lambda c, default=None: default
sys.modules["db"] = _falso

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# El registro de la prueba va aparte (ver [[registro-del-sistema]]).
import tempfile as _tmp_log, registro as _LOG_PRUEBA   # noqa: E402
_LOG_PRUEBA.usar_carpeta(_tmp_log.mkdtemp(prefix="verif_logs_"))

import pymupdf as fitz          # noqa: E402
import motor_pedido as MP       # noqa: E402
import aplanar_rip as AR        # noqa: E402
import servidor as S            # noqa: E402

FALLOS = []
MOLDE = None


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


def _pdf(nombre, paginas=1):
    """Un PDF de verdad, chiquito, en el temporal de la prueba."""
    ruta = os.path.join(_TMP, nombre)
    d = fitz.open()
    for _ in range(paginas):
        pg = d.new_page(width=200, height=200)
        pg.draw_rect(fitz.Rect(10, 10, 100, 100))
    d.save(ruta)
    d.close()
    return ruta


def _se_puede_reemplazar(ruta):
    """La prueba de fuego en Windows: si el archivo quedó abierto, esto tira WinError 5."""
    copia = ruta + ".prueba"
    try:
        with open(ruta, "rb") as orig, open(copia, "wb") as f:
            f.write(orig.read())
        os.replace(copia, ruta)
        return True
    except OSError:
        try:
            os.remove(copia)
        except OSError:
            pass
        return False


def _explota(*a, **k):
    """Lo que hacía el motor de verdad: abre el molde por el registro y no lo cierra."""
    MP._abrir(MOLDE)
    raise RuntimeError("falla a propósito, con el molde abierto")


class _DocQueExplota:
    """Un documento que revienta al leerle las capas, para ver si igual lo cierran."""

    def __init__(self, real):
        self._real = real
        self.cerrado = False

    def layer_ui_configs(self):
        raise RuntimeError("arte ilegible")

    def close(self):
        self.cerrado = True
        self._real.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
        return False


def main():
    global MOLDE
    sys.stdout.reconfigure(encoding="utf-8")
    MOLDE = _pdf("molde.pdf", paginas=2)

    print("1) Los workers del pool cierran lo que abren, TAMBIÉN si el trabajo falla")
    _cat = {"productos": [{"id": "pid_prueba", "nombre": "Prueba"}]}
    S._cargar_catalogo = lambda *a, **k: _cat
    S._cargar = lambda *a, **k: {"Pieza 1": {"M": {}}}
    S._piezas_base = _explota
    MP.cerrar_abiertos()
    r = S._render_talle_worker(("pid_prueba", "d", "v", "M", {}))
    ok(r is None, "un talle que falla devuelve None (el pool sigue vivo)")
    ok(MP._pendientes() == [], "el worker de RENDER no deja PDFs abiertos aunque el talle falle")

    S._deteccion_base_cached = _explota
    MP.cerrar_abiertos()
    S._deteccion_talle_worker(("pid_prueba", "M"))
    ok(MP._pendientes() == [], "el worker de DETECCIÓN tampoco")
    MP.cerrar_abiertos()
    ok(_se_puede_reemplazar(MOLDE), "y el molde se puede reemplazar después (nada quedó trabado)")

    print("\n2) La precarga del lienzo: cierra al terminar y no se solapa consigo misma")
    veces = {"n": 0}
    arranco, seguir = threading.Event(), threading.Event()

    def _detectar_lento(pl):
        veces["n"] += 1
        MP._abrir(pl)                      # abre y no cierra: lo tiene que cerrar `_en_hilo`
        arranco.set()
        seguir.wait(20)
        return {"mesas": [], "piezas": []}

    MP.detectar_piezas_todas = _detectar_lento
    S._ruta_entrada = lambda nombre, pid=None: MOLDE
    S._ruta_datos = lambda nombre, pid=None: os.path.join(_TMP, nombre)
    S._en_hilo(lambda: S._prewarm_deteccion_todas("pid_prueba"))
    ok(arranco.wait(20), "la precarga arranca en segundo plano")
    S._en_hilo(lambda: S._prewarm_deteccion_todas("pid_prueba"))   # la segunda NO tiene que entrar
    time.sleep(0.5)
    ok(veces["n"] == 1,
       f"subir el molde dos veces no lanza dos extracciones (entró {veces['n']} vez/veces)")
    seguir.set()
    for _ in range(100):
        if _se_puede_reemplazar(MOLDE):
            break
        time.sleep(0.1)
    ok(_se_puede_reemplazar(MOLDE), "al terminar la precarga el molde YA no está trabado")

    print("\n3) El aplanado para el RIP no deja temporales ni handles cuando falla")
    roto = os.path.join(_TMP, "roto.pdf")
    with open(roto, "wb") as f:
        f.write(b"%PDF-1.6\nesto no es un PDF de verdad\n")
    os.environ["TIZADA_APLANADO_PARALELO"] = "1"
    res = AR.aplanar_para_rip(roto)
    os.environ.pop("TIZADA_APLANADO_PARALELO", None)
    sobras = [n for n in os.listdir(_TMP) if ".__p" in n]
    ok(res is False, "un PDF ilegible no se da por aplanado")
    ok(not sobras, f"no quedan temporales del aplanado en paralelo (quedaron: {sobras})")
    ok(_se_puede_reemplazar(roto), "la hoja se puede reemplazar después de fallar el aplanado")

    print("\n4) Una hoja de verdad sigue aplanándose igual (control)")
    hoja = _pdf("hoja.pdf", paginas=3)
    os.environ["TIZADA_APLANADO_PARALELO"] = "1"
    ok(AR.aplanar_para_rip(hoja) is True, "el aplanado en paralelo funciona con varias páginas")
    os.environ.pop("TIZADA_APLANADO_PARALELO", None)
    ok(not [n for n in os.listdir(_TMP) if ".__p" in n],
       "y tampoco deja temporales cuando sale bien")
    with fitz.open(hoja) as _h:
        ok(_h.page_count == 3, "la hoja aplanada conserva sus 3 páginas (no se perdió contenido)")
    ok(_se_puede_reemplazar(hoja), "la hoja aplanada no queda abierta")

    print("\n5) La lectura de la personalización cierra el arte aunque el arte esté roto")
    abiertos = []
    open_real = fitz.open

    def _open_trucado(*a, **k):
        d = _DocQueExplota(open_real(*a, **k))
        abiertos.append(d)
        return d

    MP.fitz.open = _open_trucado
    try:
        MP.extraer_personalizacion(MOLDE)
    except Exception:
        pass
    finally:
        MP.fitz.open = open_real
    ok(bool(abiertos) and all(d.cerrado for d in abiertos),
       "si leer las capas explota, el arte se cierra igual")

    print()
    if FALLOS:
        print(f"FALLARON {len(FALLOS)}:")
        for f in FALLOS:
            print("  -", f)
        sys.exit(1)
    print("TODO OK: nada queda abierto, ni cuando falla")


if __name__ == "__main__":
    main()
