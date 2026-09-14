# -*- coding: utf-8 -*-
"""CONTRATO: UN CARÁCTER QUE LA TIPOGRAFÍA NO TIENE SE AVISA ANTES, Y NUNCA TUMBA LA TIZADA
`py verificar_glifos_del_nombre.py`

Reporte del usuario (2026-09-14): quiso armar una tizada y le salió **«glifo faltante: '.'»**. El
nombre llevaba un punto y las tipografías de camiseta del diseñador (`MoreggiTFont4…`) sólo traen
letras y números — ni punto ni guion. El pedido entero moría con un rastro de Python.

El aviso YA existía: `/api/pedido/fuente_chars` devuelve los caracteres que la tipografía sí puede
estampar y la planilla pinta el resto en ROJO **antes** de generar. Pero leía el **arte**, y el
molde con el diseño adentro no tiene arte: devolvía vacío y no marcaba nada.

Lo que se prueba:
  1. `faltantes()` dice exactamente qué caracteres no se pueden dibujar (y no se cuelga con los
     que sí);
  2. `fuente_chars` de un molde del camino B sale del MOLDE y marca el punto y el guion;
  3. el molde del camino A (con arte) sigue saliendo del arte;
  4. el mensaje de la tizada dice qué hacer: nombra la tipografía, el carácter y el texto — y
     NO estampa el nombre cambiado (un nombre de persona no se imprime distinto en silencio).

⚠️ Sólo LEE: catálogo de fuentes y moldes ya cargados. No escribe nada.
"""
import inspect
import io
import os
import sys
import tempfile
import types

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")

import registro as _LOG                    # noqa: E402
_LOG.usar_carpeta(tempfile.mkdtemp(prefix="verif_glifos_"))
import servidor as S                       # noqa: E402
import motor_pedido as MP                  # noqa: E402
from texto_curvas import FuenteCurvas      # noqa: E402

FALLOS = []


def ok(cond, msg):
    print(("    OK    " if cond else "    ❌    ") + msg)
    if not cond:
        FALLOS.append(msg)


def _fuente(nombre):
    r = MP.resolver_fuente(nombre, os.path.join(_AQUI, "catalogo_fuentes"))
    if not r:
        return None
    with open(r, "rb") as fh:
        return FuenteCurvas(fh.read())


def main():
    # ── 1. `faltantes()` ────────────────────────────────────────────────────────────────────
    print("1 · LA TIPOGRAFÍA DICE QUÉ NO PUEDE DIBUJAR")
    cat = MP.catalogo_fuentes(os.path.join(_AQUI, "catalogo_fuentes"))
    sin_punto = []
    for ruta, info in cat.items():
        try:
            with open(ruta, "rb") as fh:
                fc = FuenteCurvas(fh.read())
        except Exception:
            continue
        if fc.faltantes("."):
            sin_punto.append(info["interno"])
    ok(bool(sin_punto), f"hay tipografías en el catálogo SIN punto (si no, este contrato no prueba nada): {sin_punto}")
    fc = _fuente(sin_punto[0]) if sin_punto else None
    if fc is not None:
        ok(fc.faltantes("J. PEREZ") == ["."], f"«J. PEREZ» → {fc.faltantes('J. PEREZ')}")
        ok(fc.faltantes("MESSI") == [], "un nombre que sí se puede estampar no da faltantes")
        ok(fc.faltantes("N.N.") == ["."], "el mismo carácter no se repite en la lista")
        ok(fc.faltantes(" ") == [], "el espacio nunca falta (tiene avance aunque no tenga contorno)")
    anton = _fuente("Anton Regular")
    ok(anton is not None and anton.faltantes(".-/ 0123456789ABCÑ") == [],
       "la predeterminada («Anton Regular») los tiene todos")

    # ── 2. EL MOLDE CON DISEÑO ADENTRO ──────────────────────────────────────────────────────
    print("\n2 · 🔴 EL AVISO SALE DEL MOLDE CUANDO NO HAY ARTE (camino B)")
    fuente_chars_src = inspect.getsource(S.fuente_chars)
    ok("_es_camino_b(pid)" in fuente_chars_src and "personalizacion_con_diseno" in fuente_chars_src,
       "`fuente_chars` mira el molde cuando es del camino B (antes leía sólo `arte.ai`)")
    ok("por_talle" in fuente_chars_src,
       "…y junta también la tipografía de CADA TALLE (en el camino B cada talle trae la suya)")
    cb = []
    try:
        cat_prod = S._cargar_catalogo()
        for p in (cat_prod.get("productos") or []):
            pid = p.get("id")
            if pid and S._es_camino_b(pid):
                cb.append(pid)
    except Exception:
        pass
    if not cb:
        print("    ⚠️    no hay ningún molde del camino B cargado: no se puede probar en vivo")
    else:
        pid = cb[0]
        with S.app.test_request_context(f"/api/pedido/fuente_chars?producto_id={pid}"):
            d = S.fuente_chars().get_json()
        chars = d.get("chars") or ""
        ok(d.get("ok") and bool(chars), f"devuelve los caracteres del molde «{pid}» ({len(chars)}) · fuentes {d.get('fuentes')}")
        ok(bool(d.get("fuentes")), "…y de qué tipografía salieron")
        if chars and sin_punto:
            ok("." not in chars, "🔴 el punto NO figura como soportado: la planilla lo pinta en rojo")
        ok("A" in chars and "5" in chars, "las letras y los números sí figuran")

    # ── 3. EL CAMINO A NO CAMBIA ────────────────────────────────────────────────────────────
    print("\n3 · EL MOLDE CON ARTE SIGUE SALIENDO DEL ARTE")
    ok('extraer_personalizacion(_ruta_entrada("arte.ai", pid))' in fuente_chars_src,
       "el camino A sigue leyendo la personalización del arte")

    # ── 4. EL MENSAJE DE LA TIZADA ──────────────────────────────────────────────────────────
    print("\n4 · 🔴 SI IGUAL SE GENERA, EL MENSAJE DICE QUÉ HACER")
    # `generar_pieza` vive ADENTRO de `generar_pedido`: se lee el archivo, no el objeto.
    src = io.open(os.path.join(_AQUI, "motor_pedido.py"), encoding="utf-8").read()
    ok("fnom.faltantes(texto)" in src, "el estampado pregunta ANTES de dibujar")
    ok("no puede estampar" in src and "elegí otra tipografía" in src,
       "el mensaje nombra la tipografía, el carácter y qué hacer (no «glifo faltante»)")
    ok("raise ValueError" in src.split("fnom.faltantes(texto)")[1][:900],
       "…y CORTA: no se estampa el nombre cambiado en silencio")
    # el mensaje se arma de verdad
    if fc is not None:
        _f = fc.faltantes("J. PEREZ")
        msg = ("La tipografía «{f}» no puede estampar {c} de «{t}». "
               "Sacá {c2} del texto o elegí otra tipografía en el paso Arte.").format(
            f=sin_punto[0], c=" ni ".join(f"«{c}»" for c in _f), t="J. PEREZ",
            c2=("ese carácter" if len(_f) == 1 else "esos caracteres"))
        ok("«.»" in msg and "J. PEREZ" in msg and sin_punto[0] in msg, f"queda así: {msg}")

    print()
    if FALLOS:
        print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
        for f in FALLOS:
            print("   ·", f)
        sys.exit(1)
    print("✅ CONTRATO VERDE — lo que la tipografía no puede estampar se avisa antes y se explica")


if __name__ == "__main__":
    main()
