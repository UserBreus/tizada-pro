# -*- coding: utf-8 -*-
"""
CONTRATO: EL NAVEGADOR CONVIERTE TEXTO A CURVAS IGUAL QUE EL SERVIDOR — `py verificar_navegador_curvas.py`

PLAN_NAVEGADOR.md, etapa 3, punto 2. `frontend/src/motor/texto/curvas.js` traduce `texto_curvas.py`
(`FuenteCurvas`: glifo → operadores de trazado PDF con opentype.js en vez de fontTools). Este contrato
corre las dos cosas sobre las MISMAS tipografías (todas las de `catalogo_fuentes/`, sólo lectura, con
Anton Regular de respaldo como en `motor_pedido`) y los mismos textos, tamaños, posición y ángulos, y
exige que den lo mismo:
  · `faltantes` y `prestados` de cada texto, `cap_ratio`, `size_para_alto`, `ancho_texto` (double exacto);
  · `ops_texto` (recto, con ángulo): la CADENA de operadores, byte a byte;
  · `ops_texto_curva` y `ops_texto_fiel` (arco): la cadena también, con UNA excepción documentada:
    el arco se ajusta con `numpy.polyfit` (SVD de LAPACK), que no se puede reproducir bit a bit en
    JavaScript (la versión JS resuelve los mismos mínimos cuadrados por QR: los coeficientes difieren
    ~1e-14 relativo, medido), y `math.atan2` de la CRT de Windows difiere de `Math.atan2` de V8 en el
    último bit para algunas tangentes. Eso mueve cada coordenada ~1e-13 pt y sólo se ve si el valor
    cae JUSTO en un borde de redondeo del `.2f` (…5 exacto). Con los datos de este contrato pasa
    seguido A PROPÓSITO (tamaño 37,5 sobre upem 1000 deja miles de coordenadas en …25/…75, y el
    texto recto exige que se redondeen IGUAL): en el arco se toleran esos casos comparando los
    números a 1 centésima (el último dígito impreso), se cuentan como «bordes» y si pasan de uno por
    mil el contrato se pone rojo (medido 2026-09-17: 627 sobre 1,9 millones de números). Cualquier
    otra diferencia en el arco —un operador distinto, un número corrido más de eso— es rotura.
  · un texto que la fuente NO puede dibujar (sin respaldo) tiene que fallar en las dos puntas.
No toca MSSQL ni el servidor. Sin argumentos usa el catálogo entero; con rutas, esas fuentes.
"""
import glob
import json
import math
import os
import subprocess
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
NODE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "curvas.mjs")
CATALOGO = os.path.join(AQUI, "catalogo_fuentes")
RESPALDO = os.path.join(CATALOGO, "Anton-Regular.ttf")

from texto_curvas import FuenteCurvas  # noqa: E402

TEXTOS = [
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "abcdefghijklmnopqrstuvwxyz",
    "0123456789",
    "J. PEREZ 10",                      # punto y espacio: lo que tumbaba la tizada (2026-09-14)
    "ÁÉÍÓÚ áéíóú ñÑ üÜ",                 # acentos: compuestos en las TrueType
    "MESSI\t10",                        # un espacio que no es «espacio» (isspace de Python)
    "Ω→★",                              # nadie lo tiene: faltantes hasta con respaldo
    "",
]
SIZES = [12, 37.5, "alto3mm"]           # alto3mm = size_para_alto(3 mm) de CADA fuente
POS = [10.123, 20.456]
ANGULOS = [0, 17.5, -90, 33.3]
# arco de prueba: los orígenes de 7 glifos sobre una parábola (como los que deja Illustrator)
CURVA = {
    "puntos": [[40.0 + 25 * k, 300.0 - 0.02 * (k - 3) ** 2 * 625 + 0.37 * k] for k in range(7)],
    "x0": 31.5, "x1": 204.25, "aligns": ["centro", "izquierda", "derecha"],
}
# dos renglones alineados a la izquierda, el segundo en arco
FIEL = {
    "texto": "GOLERO\n1",
    "glifos": [[20.0, 100.0, 20.0, 120.0], [45.0, 100.0, 20.0, 120.0], [70.0, 100.0, 20.0, 120.0],
               [20.0, 60.0, 20.0, 120.0], [60.0, 63.0, 20.0, 120.0], [100.0, 60.0, 20.0, 120.0]],
}
TOL_BORDE = 0.01 + 1e-9


def _intentar(f):
    try:
        return f()
    except Exception:
        return None


def correr_python(ruta, respaldo):
    """La MISMA secuencia de llamadas que `curvas.mjs` (la caché y `sustituidos` dependen del orden)."""
    resp = FuenteCurvas(open(respaldo, "rb").read()) if respaldo else None
    fc = FuenteCurvas(open(ruta, "rb").read(), respaldo=resp)
    sizes = [fc.size_para_alto(3 * 2.83465) if s == "alto3mm" else s for s in SIZES]
    r = {"upem": fc.upem, "cap_ratio": fc.cap_ratio, "sizes": sizes, "faltantes": {}, "prestados": {},
         "ancho": {}, "ops": {}, "curva": {}, "fiel": {}, "sustituidos": None}
    for texto in TEXTOS:
        r["faltantes"][texto] = fc.faltantes(texto)
        r["prestados"][texto] = fc.prestados(texto)
        for si, size in enumerate(sizes):
            r["ancho"][f"{texto}|{si}"] = _intentar(lambda: fc.ancho_texto(texto, size))
            for ang in ANGULOS:
                r["ops"][f"{texto}|{si}|{ang}"] = _intentar(lambda: fc.ops_texto(texto, size, POS[0], POS[1], ang))
            for al in CURVA["aligns"]:
                r["curva"][f"{texto}|{si}|{al}"] = _intentar(
                    lambda: fc.ops_texto_curva(texto, size, CURVA["puntos"], CURVA["x0"], CURVA["x1"], al))
            r["curva"][f"{texto}|{si}|2pts"] = _intentar(lambda: fc.ops_texto_curva(texto, size, CURVA["puntos"][:2]))
    for si, size in enumerate(sizes):
        r["fiel"][str(si)] = _intentar(lambda: fc.ops_texto_fiel(FIEL["texto"], size, FIEL["glifos"]))
    r["sustituidos"] = fc.sustituidos
    return r


def _tokens(s):
    return s.split()


def comparar_ops(a, b, tolerante):
    """None → (ok, bordes, detalle). Cadena igual = ok. Si `tolerante`, operadores iguales y números a
    ≤ 1 centésima cuentan como «borde de redondeo» (se devuelven contados)."""
    if a == b:
        return True, 0, None
    if a is None or b is None:
        return False, 0, f"uno falló y el otro no (py={'error' if a is None else 'ok'}, js={'error' if b is None else 'ok'})"
    ta, tb = _tokens(a), _tokens(b)
    if len(ta) != len(tb):
        return False, 0, f"largo {len(ta)} vs {len(tb)} tokens"
    bordes = 0
    for i, (x, y) in enumerate(zip(ta, tb)):
        if x == y:
            continue
        try:
            fx, fy = float(x), float(y)
        except ValueError:
            return False, bordes, f"token {i}: {x!r} vs {y!r}"
        if not tolerante or abs(fx - fy) > TOL_BORDE:
            return False, bordes, f"token {i}: {x} vs {y}"
        bordes += 1
    return True, bordes, None


def comparar(nombre, py, js):
    fallas, bordes, numeros = [], 0, 0
    if "error" in js:
        return [f"JS no pudo abrir la fuente: {js['error']}"], 0, 0
    if py["upem"] != js["upem"]:
        fallas.append(f"upem {py['upem']} vs {js['upem']}")
    if py["cap_ratio"] != js["cap_ratio"]:
        fallas.append(f"cap_ratio {py['cap_ratio']!r} vs {js['cap_ratio']!r}")
    if py["sizes"] != js["sizes"]:
        fallas.append(f"size_para_alto {py['sizes']!r} vs {js['sizes']!r}")
    for clave in ("faltantes", "prestados"):
        for texto, v in py[clave].items():
            if v != js[clave].get(texto):
                fallas.append(f"{clave}({texto!r}): {v} vs {js[clave].get(texto)}")
    for k, v in py["ancho"].items():
        if v != js["ancho"].get(k):
            fallas.append(f"ancho_texto[{k}]: {v!r} vs {js['ancho'].get(k)!r}")
    for k, v in py["ops"].items():
        ok, _, det = comparar_ops(v, js["ops"].get(k), tolerante=False)
        if not ok:
            fallas.append(f"ops_texto[{k}]: {det}")
    for grupo in ("curva", "fiel"):
        for k, v in py[grupo].items():
            tolerante = not k.endswith("|2pts")          # con 2 puntos no hay parábola: exacto
            ok, b, det = comparar_ops(v, js[grupo].get(k), tolerante)
            bordes += b
            numeros += len(_tokens(v)) if v else 0
            if not ok:
                fallas.append(f"ops_texto_{grupo}[{k}]: {det}")
    if py["sustituidos"] != js["sustituidos"]:
        fallas.append(f"sustituidos {py['sustituidos']} vs {js['sustituidos']}")
    return fallas, bordes, numeros


def main(argv):
    rutas = [os.path.abspath(a) for a in argv] or sorted(glob.glob(os.path.join(CATALOGO, "*.ttf")) +
                                                          glob.glob(os.path.join(CATALOGO, "*.otf")))
    if not rutas:
        print("❌ CONTRATO ROTO — no hay tipografías en catalogo_fuentes/")
        return 2
    fuentes = []
    for ruta in rutas:
        es_respaldo = os.path.normcase(ruta) == os.path.normcase(RESPALDO)
        fuentes.append({"nombre": os.path.basename(ruta), "ruta": ruta,
                        "respaldo": None if es_respaldo or not os.path.exists(RESPALDO) else RESPALDO})
    casos = {"fuentes": fuentes, "textos": TEXTOS, "sizes": SIZES, "pos": POS, "angulos": ANGULOS, "curva": CURVA, "fiel": FIEL}
    with tempfile.TemporaryDirectory(prefix="curvas_") as tmp:
        ruta_casos = os.path.join(tmp, "casos.json")
        ruta_salida = os.path.join(tmp, "salida.json")
        with open(ruta_casos, "w", encoding="utf-8") as fh:
            json.dump(casos, fh, ensure_ascii=False)
        t0 = time.time()
        p = subprocess.run(["node", NODE, ruta_casos, ruta_salida], capture_output=True, text=True, encoding="utf-8", cwd=AQUI)
        if p.returncode != 0:
            print(p.stdout); print(p.stderr)
            print("❌ CONTRATO ROTO — el motor del navegador no corrió")
            return 1
        t_node = time.time() - t0
        with open(ruta_salida, encoding="utf-8") as fh:
            salida = json.load(fh)
    rotas, total_bordes, total_numeros = 0, 0, 0
    for fu in fuentes:
        t0 = time.time()
        try:
            py = correr_python(fu["ruta"], fu["respaldo"])
        except Exception as e:
            js = salida.get(fu["nombre"], {})
            if "error" in js:
                print(f"  ✓ {fu['nombre']}: las dos puntas rechazan la fuente ({e})")
                continue
            print(f"  ✗ {fu['nombre']}: Python revienta ({e}) y el navegador no")
            rotas += 1
            continue
        t_py = time.time() - t0
        js = salida.get(fu["nombre"], {"error": "sin resultado"})
        fallas, bordes, numeros = comparar(fu["nombre"], py, js)
        total_bordes += bordes; total_numeros += numeros
        n_ops = sum(1 for v in py["ops"].values() if v is not None)
        n_arco = sum(1 for v in py["curva"].values() if v) + sum(1 for v in py["fiel"].values() if v)
        if not n_ops or not n_arco:                  # las dos puntas fallando igual NO es una prueba
            fallas.append(f"nada que comparar: {n_ops} textos rectos y {n_arco} en arco salieron del Python")
        extra = f", {bordes} bordes de redondeo" if bordes else ""
        if fallas:
            rotas += 1
            print(f"  ✗ {fu['nombre']} ({n_ops} rectos, {n_arco} en arco, py {t_py:.1f}s, js {js.get('segundos', 0):.1f}s{extra})")
            for f in fallas[:6]:
                print(f"      · {f}")
            if len(fallas) > 6:
                print(f"      · … y {len(fallas) - 6} más")
        else:
            print(f"  ✓ {fu['nombre']} ({n_ops} rectos, {n_arco} en arco, py {t_py:.1f}s, js {js.get('segundos', 0):.1f}s{extra})")
    if total_numeros and total_bordes > total_numeros / 1000:
        rotas += 1
        print(f"  ✗ demasiados bordes de redondeo en el arco: {total_bordes} de {total_numeros} números")
    if rotas:
        print(f"❌ CONTRATO ROTO — {rotas} de {len(fuentes)} tipografías no dan lo mismo en el navegador")
        return 1
    print(f"✅ CONTRATO VERDE — {len(fuentes)} tipografías, mismos operadores en el navegador y el servidor "
          f"({total_bordes} bordes de redondeo en el arco sobre {total_numeros} números; node {t_node:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
