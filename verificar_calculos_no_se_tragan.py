"""Contrato: ningún `except Exception` de una RUTA se traga el pedido de cálculo al navegador (MAPA 721).

Con «El servidor no calcula» (MAPA 528) `_calcular` lanza `_FaltaCalculo` para que el navegador haga el
cálculo (428 / 200 marcado). Si una ruta lo envuelve en `try: … except Exception as e: return error`, el
pedido sale como error con el NOMBRE del cálculo («no se pudo leer el molde: analizar_variantes») y la
pantalla lo repite sin parar. Pasó en `/api/plantilla/variantes` al subir un molde desde Illustrator.

Lee servidor.py (sin ejecutar nada): arma qué funciones llaman —directo o a través de otras— a
`_calcular`/`_arte_calc`, y marca todo `except` amplio cuyo `try` llame a una de ellas y que no haga
`_relanzar_calculo(e)` ni `raise`. Las de la lista PERMITIDAS no son rutas del navegador (trabajadores de
proceso, precalentados, el camino que sólo corre con el servidor calculando): ahí tragarse el error es lo
buscado o el cálculo nunca se pide.
"""
import ast
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))

# función → por qué puede tragarse el error
PERMITIDAS = {
    "_deteccion_talle_worker": "trabajador de proceso (sin pedido del navegador): precalienta, best-effort",
    "_render_talle_worker": "trabajador de proceso: precalienta, best-effort",
    "_precalentar_nido": "precalentado en segundo plano, best-effort",
    "_subir_arte_analizar": "sólo corre con el servidor calculando (`_solo_navegador()` apagado)",
    "generar_multi": "la guía de la ficha del armado en el servidor: si falla, el pedido sigue sin ella",
    "correr": "hilo del armado en el servidor (sin pedido del navegador)",
}


def _llamadas(nodo):
    out = set()
    for x in ast.walk(nodo):
        if isinstance(x, ast.Call):
            f = x.func
            if isinstance(f, ast.Name):
                out.add(f.id)
            elif isinstance(f, ast.Attribute):
                out.add(f.attr)
    return out


def revisar(ruta):
    arbol = ast.parse(open(ruta, encoding="utf-8").read())
    funcs = {n.name: n for n in ast.walk(arbol) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    calculan = {"_calcular", "_arte_calc"}
    cambio = True
    while cambio:                                   # las que calculan a través de otras
        cambio = False
        for nom, fn in funcs.items():
            if nom not in calculan and _llamadas(fn) & calculan:
                calculan.add(nom)
                cambio = True
    malas = []
    for nom, fn in funcs.items():
        for tr in ast.walk(fn):
            if not isinstance(tr, ast.Try):
                continue
            usa = _llamadas(ast.Module(body=tr.body, type_ignores=[])) & calculan
            if not usa:
                continue
            for h in tr.handlers:
                t = h.type
                amplio = t is None or (isinstance(t, ast.Name) and t.id in ("Exception", "BaseException")) or \
                    (isinstance(t, ast.Tuple) and any(isinstance(e, ast.Name) and e.id == "Exception" for e in t.elts))
                if not amplio:
                    continue
                hm = ast.Module(body=h.body, type_ignores=[])
                if "_relanzar_calculo" in _llamadas(hm) or any(isinstance(x, ast.Raise) for x in ast.walk(hm)):
                    continue
                malas.append((h.lineno, nom, sorted(usa)))
    return malas


def main():
    malas = revisar(os.path.join(AQUI, "servidor.py"))
    fallas = [m for m in malas if m[1] not in PERMITIDAS]
    for ln, nom, usa in malas:
        marca = "  ·" if nom in PERMITIDAS else "  ✗"
        extra = f" — permitida: {PERMITIDAS[nom]}" if nom in PERMITIDAS else ""
        print(f"{marca} servidor.py:{ln} en {nom}() (el try llama {', '.join(usa)}){extra}")
    if fallas:
        print(f"\n❌ CONTRATO ROTO — {len(fallas)} except se tragan el pedido de cálculo al navegador: "
              "agregá `_relanzar_calculo(e)` al principio del except (MAPA 721)")
        return 1
    print("\n✅ CONTRATO VERDE — ninguna ruta se traga el pedido de cálculo al navegador")
    return 0


if __name__ == "__main__":
    sys.exit(main())
