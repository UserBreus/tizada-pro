# -*- coding: utf-8 -*-
"""
CONTRATO: LOS DIBUJOS DEL MOLDE A MEDIDA EN LA FICHA SALEN IGUALES EN EL NAVEGADOR —
`py verificar_ficha_a_medida_navegador.py`

Regla del usuario: «nada del uso depende del servidor; el servidor sólo guarda». La ficha técnica del
molde a medida lleva dibujos técnicos (plano con cotas, el borde en corte paso a paso, la esquina/punta
cortada y doblada, los pasos de «CÓMO SE TERMINA») que calcula `ficha_a_medida.dibujos_a_medida`
(Python). Su gemelo `frontend/src/motor/ficha/aMedidaDibujos.js` (`dibujosAMedida`) tiene que dar
EXACTAMENTE lo mismo: misma estructura `[{alto, ops}]`, mismas claves, mismos textos y los mismos
números (tolerancia 1e-6: los dos redondean a 2 decimales, así que en la práctica son iguales).

Combinaciones: forma (rectángulo, círculo, triángulo con las 4 puntas y una punta inválida) ×
terminación (dobladillo, overlock, sin) × medidas (grandes, chicas, con decimales, un triángulo tan
chico que los recortes se cruzan) × márgenes (parejo, cero, por lado, con lados en cero) × tiras (sin;
como las arma `servidor._tiras_de(…, para_ficha=True)`: marcadas, sin marcar, con y sin recorte, sin la
clave «recorte», sin «lados» → sin marcas, vacías) × borde (0 y 2 mm) × total de tiras (None o el del
servidor). Más casos sueltos: medida inconsistente con el total y textos de pasos que se parten.

Además se comprueba que el ancho de texto del JS sea el de `pymupdf.get_text_length` (con la rareza de
los bytes UTF-8) y que el contrato DETECTA una diferencia (se altera a propósito una copia de la salida).

⚠️ No toca nada del usuario: no importa `servidor` ni la base; sólo `ficha_a_medida` y `motor_pedido`.
"""
import copy
import functools
import itertools
import json
import math
import os
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import ficha_a_medida as FAM  # noqa: E402
import motor_pedido as MP  # noqa: E402

FRONT = os.path.join(AQUI, "frontend")
MODULO = "./src/motor/ficha/aMedidaDibujos.js"
TOL = 1e-6
FALLOS = []


def ok(cond, msg):
    print(("    ✓ " if cond else "    ✗ ") + msg)
    if not cond:
        FALLOS.append(msg)
    return cond


# ─── comparar dos salidas (Python ↔ JS) ─────────────────────────────────────────────────────────
def diferencias(a, b, ruta="", out=None, tope=8):
    """Las diferencias entre `a` y `b` (estructura, claves, textos, números con tolerancia)."""
    out = [] if out is None else out
    if len(out) >= tope:
        return out
    if isinstance(a, bool) or isinstance(b, bool):
        if not (isinstance(a, bool) and isinstance(b, bool) and a == b):
            out.append(f"{ruta}: {a!r} ≠ {b!r}")
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if not (abs(a - b) <= TOL):
            out.append(f"{ruta}: {a!r} ≠ {b!r}")
    elif isinstance(a, dict) and isinstance(b, dict):
        if sorted(a) != sorted(b):
            out.append(f"{ruta}: claves {sorted(a)} ≠ {sorted(b)}")
        else:
            for k in a:
                diferencias(a[k], b[k], f"{ruta}.{k}", out, tope)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{ruta}: largo {len(a)} ≠ {len(b)}")
        for i, (x, y) in enumerate(zip(a, b)):
            diferencias(x, y, f"{ruta}[{i}]", out, tope)
    elif a is None or b is None or isinstance(a, str) or isinstance(b, str):
        if a != b or type(a) is not type(b):
            out.append(f"{ruta}: {a!r} ≠ {b!r}")
    else:
        out.append(f"{ruta}: tipo {type(a).__name__} ≠ {type(b).__name__}")
    return out


def correr_js(script, datos):
    """Corre `script` en Node con `datos` por ARCHIVO (la línea de comandos de Windows se queda corta,
    WinError 206) y devuelve lo que el script escribió en el archivo de salida."""
    with tempfile.TemporaryDirectory() as tmp:
        ent, sal = os.path.join(tmp, "entrada.json"), os.path.join(tmp, "salida.json")
        with open(ent, "w", encoding="utf-8") as fh:
            json.dump(datos, fh)
        js = ("import { readFileSync, writeFileSync } from 'node:fs'\n"
              f"const ENT = {json.dumps(ent)}, SAL = {json.dumps(sal)}\n" + script)
        r = subprocess.run(["node", "--input-type=module", "-e", js], cwd=FRONT, capture_output=True,
                           text=True, encoding="utf-8")
        if r.returncode != 0:
            raise RuntimeError(f"node falló ({r.returncode}):\n{r.stderr[-3000:]}")
        with open(sal, encoding="utf-8") as fh:
            return json.load(fh)


JS_DIBUJOS = f"""
import {{ dibujosAMedida }} from '{MODULO}'
const casos = JSON.parse(readFileSync(ENT, 'utf8'))
const out = casos.map((c) => {{
  try {{
    return {{ ok: dibujosAMedida(c.forma, c.orient, c.term, c.an, c.al, c.mg, c.W, c.H, c.tiras, c.borde, c.total) }}
  }} catch (e) {{
    return {{ error: String(e && e.stack || e) }}
  }}
}})
writeFileSync(SAL, JSON.stringify(out))
"""

JS_ANCHOS = f"""
import {{ anchoTexto }} from '{MODULO}'
const casos = JSON.parse(readFileSync(ENT, 'utf8'))
writeFileSync(SAL, JSON.stringify(casos.map(([s, z, b]) => anchoTexto(s, z, b))))
"""


# ─── las entradas: como las arma el servidor ─────────────────────────────────────────────────────
def medida_pieza(forma, orient, term, an, al, mg):
    """El total (cm) como `servidor._medida_pieza` con el margen que rige (no se importa el servidor)."""
    f = MP._norm_forma(forma)
    mu = MP._margen_uniforme(mg)
    if f == "circulo":
        return an + 2 * mu, an + 2 * mu
    if f == "triangulo":
        g = MP._geo_triangulo(an, al, mu, orient, term != "overlock")
        return g["W"], g["H"]
    return an + mg["izq"] + mg["der"], al + mg["arriba"] + mg["abajo"]


def tiras_de(forma, orient, term, an, al, mg, variante):
    """Un `tiras` con la forma de `servidor._tiras_de(prod, cat, para_ficha=True)`."""
    if variante is None:
        return None
    if variante == "vacio":
        return {}
    lados = {"arriba": 3, "abajo": 2, "izq": 1, "der": 4, "alrededor": 8, "base": 3, "laterales": 2}
    if variante == "pocas":
        lados = {"arriba": 1, "abajo": 0, "izq": 2, "der": 0, "alrededor": 1, "base": 1, "laterales": 1}
    sin_margen = not any(v > 0 for v in mg.values())
    t = {"lados": lados, "color": [0, 0, 0, 1], "grosor_mm": 1.0, "margen": dict(mg), "forma": forma,
         "orientacion": orient, "marcar": not sin_margen, "terminacion": term, "recorte": term != "overlock",
         "diseno_cm": [an, al]}
    if variante == "sin_marcar":
        t["marcar"] = False
    elif variante == "recorte_falso":
        t["recorte"] = False
    elif variante == "sin_clave_recorte":
        del t["recorte"]
    elif variante == "sin_lados":
        del t["lados"]
    return t


def total_servidor(forma, orient, W, H, t):
    if not t:
        return None
    if "lados" not in t:
        return 0
    return len(MP._segmentos_tiras(W, H, t["margen"], t["lados"], forma, orient, t.get("diseno_cm"), t.get("recorte", True)))


FORMAS = [("rectangulo", "abajo"), ("rectangulo", "xx"), ("circulo", "abajo"),
          ("triangulo", "abajo"), ("triangulo", "arriba"), ("triangulo", "izq"), ("triangulo", "der"),
          ("triangulo", "otra"), ("hexagono", "abajo")]
TERMS = ["dobladillo", "overlock", "sin"]
MEDIDAS = [(100.0, 70.0), (35.5, 120.3), (12.0, 8.0), (250.0, 33.3), (5.0, 4.0)]
MARGENES = [{"arriba": 2.0, "abajo": 2.0, "izq": 2.0, "der": 2.0},
            {"arriba": 0.0, "abajo": 0.0, "izq": 0.0, "der": 0.0},
            {"arriba": 1.0, "abajo": 2.0, "izq": 3.0, "der": 4.5},
            {"arriba": 0.0, "abajo": 2.5, "izq": 0.0, "der": 1.0},
            {"arriba": 3.0, "abajo": 3.0, "izq": 3.0, "der": 3.0}]
TIRAS = [None, "marcadas", "sin_marcar", "recorte_falso", "sin_clave_recorte", "pocas", "sin_lados", "vacio"]


def armar_casos():
    casos = []
    for i, ((forma, orient), term, (an, al), mg, tv) in enumerate(itertools.product(FORMAS, TERMS, MEDIDAS, MARGENES, TIRAS)):
        mg_rige = {k: 0.0 for k in mg} if term == "sin" else mg
        W, H = medida_pieza(forma, orient, term, an, al, mg_rige)
        t = tiras_de(MP._norm_forma(forma), MP._norm_orientacion(orient), term, an, al, mg_rige, tv)
        borde = 2.0 if i % 2 else 0.0
        # el total: la mitad de las veces el del servidor, la otra mitad None (= cuenta las marcas)
        total = total_servidor(MP._norm_forma(forma), MP._norm_orientacion(orient), W, H, t) if i % 3 else None
        # el servidor pasa `{}` como margen con «sin»; la función lo vuelve cero por su cuenta
        casos.append({"forma": forma, "orient": orient, "term": term, "an": an, "al": al,
                      "mg": {} if term == "sin" and i % 2 else mg_rige, "W": W, "H": H, "tiras": t,
                      "borde": borde, "total": total})
    # sueltos: el total no coincide con la medida (el plano escala igual), bordes con decimales,
    # una terminación desconocida, márgenes que no entran (costura que no cabe) y números enteros
    casos += [
        {"forma": "rectangulo", "orient": "abajo", "term": "dobladillo", "an": 80, "al": 60,
         "mg": {"arriba": 2, "abajo": 2, "izq": 2, "der": 2}, "W": 84, "H": 64, "tiras": None, "borde": 1.5, "total": None},
        {"forma": "rectangulo", "orient": "abajo", "term": "dobladillo", "an": 3.0, "al": 2.0,
         "mg": {"arriba": 2.0, "abajo": 2.0, "izq": 2.0, "der": 2.0}, "W": 7.0, "H": 6.0, "tiras": None, "borde": 0.0, "total": None},
        {"forma": "circulo", "orient": "abajo", "term": "dobladillo", "an": 3.0, "al": 3.0,
         "mg": {"arriba": 2.0, "abajo": 2.0, "izq": 2.0, "der": 2.0}, "W": 7.0, "H": 7.0, "tiras": None, "borde": 0.25, "total": None},
        {"forma": "triangulo", "orient": "der", "term": "dobladillo", "an": 2.0, "al": 30.0,
         "mg": {"arriba": 4.0, "abajo": 0.0, "izq": 0.0, "der": 0.0}, "W": 9.0, "H": 40.0, "tiras": None, "borde": 0.0, "total": 7},
        {"forma": "rectangulo", "orient": "abajo", "term": "raro", "an": 50.0, "al": 50.0,
         "mg": {"arriba": 1.0, "abajo": 1.0, "izq": 1.0, "der": 1.0}, "W": 52.0, "H": 52.0, "tiras": None, "borde": 0.0, "total": None},
        {"forma": "triangulo", "orient": "arriba", "term": None, "an": 50.0, "al": 40.0,
         "mg": {"arriba": 1.0, "abajo": 1.0, "izq": 1.0, "der": 1.0}, "W": 55.0, "H": 45.0, "tiras": None, "borde": 0.0, "total": None},
        {"forma": "rectangulo", "orient": "abajo", "term": "dobladillo", "an": 1234.56, "al": 0.35,
         "mg": {"arriba": 0.05, "abajo": 0.15, "izq": 0.25, "der": 0.35}, "W": 1235.16, "H": 0.55, "tiras": None, "borde": 0.05, "total": None},
    ]
    return casos


def main():
    print("CONTRATO · dibujos del molde a medida (Python ↔ navegador)")

    # 1 · el ancho del texto: el de PyMuPDF, con la rareza de los bytes UTF-8 (después de una «ó» se
    # saltea la letra siguiente al medir)
    print("\n  1 · ancho del texto = pymupdf.get_text_length")
    textos = ["PLANO DE LA PIEZA", "Guía del diseño = doblez", "CÓMO SE TERMINA", "Ø 12,5 diseño (guía)",
              "ñandú · «comillas» — raya … € œ", "emoji 🙂 y más", "Tira (marca de borde a guía)",
              "abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789 ¡!¿?()[]{}<>@#$%&*+-=/\\|^~`'\"",
              "".join(chr(c) for c in range(32, 127)), "".join(chr(c) for c in range(160, 256)),
              "\u0080\u0081\u009f ‚ƒ„†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›žŸ", ""]
    pares = [(s, z, b) for s in textos for z in (7, 7.5, 8, 8.5, 9.5) for b in (False, True)]
    anchos_js = correr_js(JS_ANCHOS, pares)
    malos = [(s, z, b, FAM._ancho_texto(s, z, b), w) for (s, z, b), w in zip(pares, anchos_js)
             if FAM._ancho_texto(s, z, b) != w]
    ok(not malos, f"{len(pares)} textos miden EXACTAMENTE lo mismo que PyMuPDF"
       + (f" — primero distinto: {malos[0]}" if malos else ""))

    # 2 · los dibujos, caso por caso. El ancho del texto (PyMuPDF crea la fuente en CADA medición: el 85 % del
    # tiempo) se memoriza SÓLO para esta corrida: es una función pura, da el mismo número; el paso 1 ya
    # comparó la medición real contra el navegador. Sin esto el contrato tarda 2 minutos en vez de 20 s.
    FAM._ancho_texto = functools.lru_cache(maxsize=None)(FAM._ancho_texto)
    casos = armar_casos()
    print(f"\n  2 · dibujos_a_medida ↔ dibujosAMedida en {len(casos)} combinaciones")
    py_out = []
    for c in casos:
        try:
            py_out.append({"ok": FAM.dibujos_a_medida(c["forma"], c["orient"], c["term"], c["an"], c["al"], c["mg"],
                                                      c["W"], c["H"], tiras=c["tiras"], borde_mm=c["borde"],
                                                      total_tiras=c["total"])})
        except Exception as e:
            py_out.append({"error": f"{type(e).__name__}: {e}"})
    # Python → JSON → Python: las tuplas pasan a listas (lo mismo que ve el navegador)
    py_out = json.loads(json.dumps(py_out))
    js_out = []
    LOTE = 400
    for k in range(0, len(casos), LOTE):
        js_out += correr_js(JS_DIBUJOS, casos[k:k + LOTE])
    ok(len(js_out) == len(casos), f"el navegador devolvió {len(js_out)} de {len(casos)} salidas")
    errores_py = sum(1 for o in py_out if "error" in o)
    ok(errores_py == 0, f"Python no falla en ningún caso ({errores_py} con error)")
    distintos = 0
    for c, a, b in zip(casos, py_out, js_out):
        d = diferencias(a, b)
        if d:
            distintos += 1
            if distintos <= 5:
                print(f"      ≠ {json.dumps({k: c[k] for k in ('forma', 'orient', 'term', 'an', 'al', 'mg', 'tiras', 'borde', 'total')}, ensure_ascii=False)[:400]}")
                for x in d:
                    print(f"          {x[:300]}")
    ok(distintos == 0, f"las {len(casos)} salidas son IGUALES (estructura, claves, textos, números ±{TOL})"
       + (f" — {distintos} distintas" if distintos else ""))

    # que el contrato mire lo que dice que mira: hay de todo en las salidas
    textos_vistos = {op["s"] for o in py_out if "ok" in o for bl in o["ok"] for op in bl["ops"] if op["k"] == "t"}
    for t in ("PLANO DE LA PIEZA", "EL DOBLADILLO · el borde de costado", "EL OVERLOCK · el borde de costado",
              "SIN MARGEN · el borde de costado", "LA TERMINACIÓN · el borde de costado", "La esquina de cerca",
              "La punta de cerca", "El borde de cerca", "Tira (marca de borde a guía)", "Tira (no va marcada)",
              "CÓMO SE TERMINA"):
        ok(t in textos_vistos, f"las combinaciones cubren «{t}»")
    n_tiras = sum(1 for o in py_out if "ok" in o for op in o["ok"][0]["ops"] if op["k"] == "l" and op["w"] == 1.2)
    ok(n_tiras > 100, f"hay marcas de tiras dibujadas en el plano ({n_tiras})")
    n_lineas_pasos = max((sum(1 for op in o["ok"][2]["ops"] if op["k"] == "t") for o in py_out if "ok" in o), default=0)
    ok(n_lineas_pasos >= 8, f"hay pasos que se parten en varios renglones (máx. {n_lineas_pasos} textos en un bloque)")

    # 3 · el contrato DETECTA una diferencia: se altera a propósito una copia (un número, un texto, una clave)
    print("\n  3 · el contrato detecta una diferencia")
    base = next(o for o in py_out if "ok" in o)
    for nombre, cambiar in (("un número corrido 0,01", lambda o: o["ok"][0]["ops"][2]["p"][0].__setitem__(0, o["ok"][0]["ops"][2]["p"][0][0] + 0.01)),
                            ("un texto distinto", lambda o: o["ok"][2]["ops"][0].__setitem__("s", "COMO SE TERMINA")),
                            ("un alto distinto", lambda o: o["ok"][1].__setitem__("alto", o["ok"][1]["alto"] + 1e-3)),
                            ("una op de más", lambda o: o["ok"][1]["ops"].append(o["ok"][1]["ops"][0])),
                            ("una negrita apagada", lambda o: o["ok"][0]["ops"][0].__setitem__("b", False)),
                            ("un relleno que falta", lambda o: o["ok"][0]["ops"][2].__setitem__("f", None))):
        mal = copy.deepcopy(base)
        cambiar(mal)
        ok(bool(diferencias(base, mal)), f"detecta {nombre}")

    print()
    if FALLOS:
        print(f"✗ CONTRATO ROJO — {len(FALLOS)} falla(s):")
        for f in FALLOS:
            print(f"   · {f}")
        sys.exit(1)
    print(f"✓ CONTRATO VERDE — los dibujos del molde a medida salen iguales en el navegador ({len(casos)} combinaciones)")


if __name__ == "__main__":
    main()
