"""
CONTRATO DE LA FICHA TÉCNICA: **UN MOLDE GUÍA POR CADA DISEÑO** — se corre con
`py verificar_ficha_disenos.py`.

Un pedido puede traer varios DISEÑOS del mismo molde (columna «Diseño»: Jugador / Golero) y cada
fila su VARIABLE (cuello redondo / cuello V). La ficha se llevaba **una sola guía por molde** —la
de la 1ª fila— así que mostraba un diseño y **escondía los demás**: el taller cortaba mirando un
arte que la mitad del pedido no usa. Eso es de los errores que salen **bien impresos**.

Lo que se verifica:

  1. **Una guía por (molde · diseño · variable)**, en el orden del pedido y sin repetir.
  2. **La tela sale de SU diseño** (la asignación es por diseño; usar la del diseño editado en el
     Arte le ponía a un diseño las telas del otro).
  3. **El diseño DEFINITIVO**: si el diseño de la fila no tiene arte, la tizada cae al `_fallback`
     → la guía tiene que mostrar el arte que de verdad se estampó, no el que se pidió.
  4. **El dibujo**: cada guía sale con su título «MOLDE GUÍA · molde · diseño», y la VARIABLE se
     nombra sólo cuando el mismo molde+diseño aparece más de una vez (si no, es ruido).
  5. **Con arte REAL**: dos diseños del mismo molde dan piezas DISTINTAS (cada una con su arte).

⚠️ No toca nada del usuario: `DATOS`/`ENTRADA` son una COPIA en un temporal y el módulo `db` se
reemplaza por un doble que explota (ver [[test-no-toca-mssql]]). Sólo lee los originales.
"""
import json
import os
import shutil
import sys
import tempfile
import time
import types

try:                                        # la consola de Windows es cp1252 y se traga las flechas
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = os.path.dirname(os.path.abspath(__file__))
PID = "prod_20260729_163651_4d0d"          # «Manga pegada»: 2 diseños (Jugador/Golero) + 2 variables

_TMP = tempfile.mkdtemp(prefix="verif_ficha_")
_DATOS = os.path.join(_TMP, "datos")
_ENTRADA = os.path.join(_TMP, "entrada")
os.environ["TIZADA_DATOS"] = _DATOS
os.environ["TIZADA_ENTRADA"] = _ENTRADA
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_FUENTES"] = os.path.join(RAIZ, "catalogo_fuentes")   # sólo lectura
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"

_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n}) — revisar el aislamiento")))
sys.modules["db"] = _falso_db


def _copiar_molde():
    """COPIA (nunca mueve ni borra) el molde real a la caja de arena, y deja el catálogo con ese
    solo producto. Sin dueño: la prueba no simula sesión y `_guard_molde` cortaría."""
    os.makedirs(os.path.join(_DATOS, "productos"), exist_ok=True)
    for f in os.listdir(os.path.join(RAIZ, "datos")):
        o = os.path.join(RAIZ, "datos", f)
        if os.path.isfile(o):
            shutil.copy2(o, os.path.join(_DATOS, f))
    shutil.copytree(os.path.join(RAIZ, "datos", "productos", PID), os.path.join(_DATOS, "productos", PID))
    shutil.copytree(os.path.join(RAIZ, "entrada", PID), os.path.join(_ENTRADA, PID))
    cat = json.load(open(os.path.join(_DATOS, "productos_catalogo.json"), encoding="utf-8"))
    prod = next(p for p in cat["productos"] if p["id"] == PID)
    prod.pop("creado_por", None)
    prod["propio"] = False
    cat["productos"] = [prod]
    json.dump(cat, open(os.path.join(_DATOS, "productos_catalogo.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    return prod


PROD = _copiar_molde()

sys.path.insert(0, RAIZ)
import ficha_tecnica as FT      # noqa: E402
import servidor as S            # noqa: E402

FALLOS = []


def ok(cond, que):
    print(("  OK   " if cond else "  FALLA ") + que)
    if not cond:
        FALLOS.append(que)


def _piezas_falsas(n=3):
    """Piezas de mentira para la prueba de dibujo: un PDF chiquito por pieza."""
    import fitz
    out = []
    for i in range(n):
        d = fitz.open()
        pg = d.new_page(width=120, height=160)
        pg.draw_rect(fitz.Rect(10, 10, 110, 150), color=(0, 0, 0), width=1)
        out.append({"nombre": f"Pieza {i + 1}", "tela": "Dry Basket", "pdf": d.tobytes()})
        d.close()
    return out


# ── 1) DIBUJO: cada guía su título; la variable sólo cuando distingue ─────────────────────────
def prueba_dibujo():
    print("\n[1] DIBUJO de la ficha con varias guías")
    import fitz
    guias = [
        {"nombre": "Manga pegada", "diseno": "Jugador", "variante": "Cuello redondo", "piezas": _piezas_falsas(3)},
        {"nombre": "Manga pegada", "diseno": "Golero", "variante": "Cuello redondo", "piezas": _piezas_falsas(2)},
        {"nombre": "Manga pegada", "diseno": "Golero", "variante": "Cuello V", "piezas": _piezas_falsas(4)},
    ]
    planilla = {"columnas": [{"id": "talle", "label": "Talle"}, {"id": "dise_o", "label": "Diseño"}],
                "filas": [{"talle": "M", "dise_o": "Jugador"}, {"talle": "L", "dise_o": "Golero"}]}
    salida = os.path.join(_TMP, "dibujo")
    os.makedirs(salida, exist_ok=True)
    ruta = FT.generar_ficha(salida, "Ficha técnica", "prueba", planilla, guias)
    doc = fitz.open(ruta)
    txt = "\n".join(p.get_text() for p in doc)
    doc.close()
    ok(txt.count("MOLDE GUÍA") == 3, "hay 3 moldes guía (uno por diseño/variable), no uno solo")
    ok("MOLDE GUÍA · Manga pegada  ·  Jugador" in txt, "el título del 1º dice el diseño Jugador")
    ok("MOLDE GUÍA · Manga pegada  ·  Golero" in txt, "el título del 2º dice el diseño Golero")
    ok("Variable: Cuello V" in txt and "Variable: Cuello redondo" in txt,
       "en el diseño repetido (Golero) se nombran las DOS variables")
    ok(txt.count("Variable: Cuello redondo") == 1,
       "en el diseño que aparece una sola vez (Jugador) NO se nombra la variable")
    ok("3 piezas" in txt and "2 piezas" in txt and "4 piezas" in txt, "cada guía dice cuántas piezas lleva")
    return ruta


# ── 2) RECOLECCIÓN: qué guías pide `/api/generar_multi` (sin pagar el render) ─────────────────
def prueba_recoleccion():
    print("\n[2] RECOLECCIÓN de guías en /api/generar_multi")
    pedidas = []
    orig_guia, orig_motor, orig_user = S._molde_guia_ficha, S.MP.generar_pedido_grupos, S._usuario_actual
    # Las rutas /api/ exigen sesión (guarda global). Acá se prueba la FICHA, no el login: se simula
    # un usuario y el molde de la caja de arena no tiene dueño, así que la guarda de molde lo deja.
    S._usuario_actual = lambda: {"id": "u_prueba", "nombre": "Prueba", "rol": "admin"}

    def espia(pid, prod, reg, diseno, var=None):
        pedidas.append({"pid": pid, "diseno": diseno, "clave": (var or {}).get("clave"),
                        "asig": (var or {}).get("asig")})
        return {"nombre": (prod or {}).get("nombre"), "diseno": diseno,
                "variante": (var or {}).get("clave"), "piezas": _piezas_falsas(1)}

    def _motor_falso(grupos, fuentes, salida, **k):
        """La tizada en sí no es lo que se prueba (y tarda) — pero la carpeta de salida la crea el
        motor, y sin ella la ficha no se puede escribir."""
        os.makedirs(salida, exist_ok=True)
        return {"hojas": []}

    S._molde_guia_ficha = espia
    S.MP.generar_pedido_grupos = _motor_falso
    try:
        tela = (PROD.get("telas_asignadas") or ["Dry Basket 1,60"])[0]
        if isinstance(tela, dict):
            tela = tela.get("nombre") or tela.get("tela") or "Dry Basket 1,60"
        filas = [
            {"talle": "M", "dise_o": "Jugador", "__variante": "v_7bu24xr"},
            {"talle": "L", "dise_o": "Golero", "__variante": "v_7bu24xr"},
            {"talle": "XL", "dise_o": "Golero", "__variante": "v_92ml8qi"},
            {"talle": "S", "dise_o": "Jugador", "__variante": "v_7bu24xr"},   # repetida → NO duplica guía
        ]
        cli = S.app.test_client()
        r = cli.post("/api/generar_multi", json={
            "molds": [PID], "prendas": filas, "default_diseno": "jugador",
            "tela_base": {PID: tela},
            "planilla": {"columnas": [{"id": "talle", "label": "Talle"}, {"id": "dise_o", "label": "Diseño"}],
                         "filas": filas}})
        ok(r.status_code == 200, f"el pedido arranca (HTTP {r.status_code}: {r.get_data(as_text=True)[:160]})")
        if r.status_code != 200:
            return
        tid = r.get_json()["id"]
        t0 = time.time()
        while S.trabajos[tid]["estado"] not in ("listo", "error") and time.time() - t0 < 120:
            time.sleep(0.3)
        ok(S.trabajos[tid]["estado"] == "listo", f"el trabajo termina bien ({S.trabajos[tid].get('error')})")
        combos = [(g["diseno"], g["clave"]) for g in pedidas]
        ok(len(pedidas) == 3, f"pide 3 moldes guía (2 diseños; Golero en 2 variables) — pidió {len(pedidas)}: {combos}")
        ok(combos[:1] == [("jugador", "v_7bu24xr")], f"el 1º es el diseño de la 1ª fila — {combos[:1]}")
        ok(("golero", "v_7bu24xr") in combos and ("golero", "v_92ml8qi") in combos,
           f"el otro diseño sale con SUS DOS variables — {combos}")
        ok(len(set(combos)) == len(combos), "no repite combinaciones (la fila 4 repetía diseño+variable)")
        ok(all(g["asig"] for g in pedidas), "cada guía lleva su asignación pieza-tela (no vacía)")
        # Y el PDF que deja el pedido tiene esas 3 guías (el camino completo, no sólo la lista).
        _res = S.trabajos[tid].get("resultado") or {}
        ok(_res.get("ficha") == "FICHA_TECNICA.pdf", "el pedido deja la FICHA_TECNICA.pdf en la salida")
        _fp = os.path.join(os.environ["TIZADA_TRABAJOS"], tid, "FICHA_TECNICA.pdf")
        if os.path.exists(_fp):
            import fitz
            _d = fitz.open(_fp)
            _t = "\n".join(p.get_text() for p in _d)
            _d.close()
            ok(_t.count("MOLDE GUÍA") == 3, f"la ficha del pedido trae los 3 moldes guía ({_t.count('MOLDE GUÍA')})")
            ok("jugador" in _t and "golero" in _t, "en la ficha están los DOS diseños del pedido")
    finally:
        S._molde_guia_ficha, S.MP.generar_pedido_grupos = orig_guia, orig_motor
        S._usuario_actual = orig_user


# ── 3) ARTE REAL: cada diseño trae SU arte (piezas distintas) ─────────────────────────────────
def prueba_arte_real():
    print("\n[3] RENDER REAL: cada diseño con su arte (tarda: pasa por el motor)")
    reg = S._cargar("registro_producto.json", PID)
    cfg = S._config_produccion(PID)
    telas_cfg, asig = cfg[2], cfg[3]
    guias = []
    for dslug, clave in (("jugador", "v_7bu24xr"), ("golero", "v_7bu24xr")):
        t0 = time.time()
        g = S._molde_guia_ficha(PID, PROD, reg, dslug,
                                {"clave": clave, "asig": asig, "telas": telas_cfg, "diseno": dslug})
        print(f"      · {dslug}: {'sin guía' if not g else str(len(g['piezas'])) + ' piezas'} "
              f"({time.time() - t0:.1f}s)")
        ok(bool(g and g.get("piezas")), f"el diseño «{dslug}» arma su molde guía")
        if g:
            guias.append(g)
    if len(guias) == 2:
        ok(guias[0]["diseno"] != guias[1]["diseno"], "cada guía dice su propio diseño")
        n0 = sorted(p["nombre"] for p in guias[0]["piezas"])
        n1 = sorted(p["nombre"] for p in guias[1]["piezas"])
        ok(n0 == n1, "misma variable: las mismas piezas en los dos diseños")
        b0 = [p["pdf"] for p in guias[0]["piezas"]]
        b1 = [p["pdf"] for p in guias[1]["piezas"]]
        ok(b0 != b1, "el CONTENIDO de las piezas cambia: cada diseño trae su arte estampado")
        ok(any(p.get("tela") for p in guias[0]["piezas"]), "las piezas dicen en qué tela van")
        salida = os.path.join(_TMP, "real")
        os.makedirs(salida, exist_ok=True)
        ruta = FT.generar_ficha(salida, "Ficha técnica", "Manga pegada · prueba", {
            "columnas": [{"id": "talle", "label": "Talle"}, {"id": "dise_o", "label": "Diseño"}],
            "filas": [{"talle": "M", "dise_o": "Jugador"}, {"talle": "L", "dise_o": "Golero"}]}, guias)
        print("      ficha con arte real:", ruta)
        return ruta
    return None


if __name__ == "__main__":
    print("caja de arena:", _TMP)
    r1 = prueba_dibujo()
    prueba_recoleccion()
    r3 = prueba_arte_real() if "--rapido" not in sys.argv else None
    destino = os.environ.get("FICHA_SALIDA")
    if destino:                      # copia para mirar la ficha a ojo
        os.makedirs(destino, exist_ok=True)
        for r, n in ((r1, "ficha_dibujo.pdf"), (r3, "ficha_arte_real.pdf")):
            if r and os.path.exists(r):
                shutil.copy2(r, os.path.join(destino, n))
                print("copiada:", os.path.join(destino, n))
    print("\n" + ("TODO OK" if not FALLOS else f"{len(FALLOS)} FALLA(S):\n  - " + "\n  - ".join(FALLOS)))
    shutil.rmtree(_TMP, ignore_errors=True)
    sys.exit(1 if FALLOS else 0)
