# -*- coding: utf-8 -*-
"""CONTRATO: UN CARÁCTER QUE LA TIPOGRAFÍA NO TIENE SE AVISA ANTES, Y NUNCA TUMBA LA TIZADA
`py verificar_glifos_del_nombre.py`

Reporte del usuario (2026-09-14): quiso armar una tizada y le salió **«glifo faltante: '.'»**. El
nombre llevaba un punto y las tipografías de camiseta del diseñador (`MoreggiTFont4…`) sólo traen
letras y números — ni punto ni guion. El pedido entero moría con un rastro de Python.

El aviso YA existía: `/api/pedido/fuente_chars` devuelve los caracteres que la tipografía sí puede
estampar y la planilla pinta el resto en ROJO **antes** de generar. Pero leía el **arte**, y el
molde con el diseño adentro no tiene arte: devolvía vacío y no marcaba nada.

REGLA DEL USUARIO (2026-09-14): *«si la fuente no tiene algunos caracteres que le ponga unos
genéricos solamente en ese carácter»*. El nombre sale COMPLETO: ese carácter lo dibuja la
tipografía predeterminada, al mismo tamaño, y el resto sigue siendo la del diseño.

Lo que se prueba:
  1. el carácter que la tipografía no tiene lo PRESTA la de respaldo, se dibuja y se ve del
     mismo tamaño;
  2. `fuente_chars` de un molde del camino B sale del MOLDE y marca el punto y el guion;
  3. el molde del camino A (con arte) sigue saliendo del arte;
  4. el préstamo se ANOTA (que salga no quiere decir que no haya que saberlo), la planilla lo
     avisa como ADVERTENCIA y, si no lo puede dibujar NADIE, el mensaje dice qué hacer.

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


def _fuente(nombre, respaldo=None):
    r = MP.resolver_fuente(nombre, os.path.join(_AQUI, "catalogo_fuentes"))
    if not r:
        return None
    with open(r, "rb") as fh:
        return FuenteCurvas(fh.read(), respaldo=respaldo)


def main():
    # ── 1. `faltantes()` ────────────────────────────────────────────────────────────────────
    print("1 · EL CARÁCTER QUE NO ESTÁ LO PRESTA LA PREDETERMINADA")
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
    anton = _fuente("Anton Regular")
    ok(anton is not None and anton.faltantes(".-/ 0123456789ABCÑ") == [],
       "la predeterminada («Anton Regular») los tiene todos")
    _nom = sin_punto[0] if sin_punto else None
    sola = _fuente(_nom) if _nom else None
    if sola is not None:
        ok(sola.faltantes("J. PEREZ") == ["."], f"SIN respaldo, «{_nom}» no podría estampar «J. PEREZ»")
    fc = _fuente(_nom, respaldo=anton) if _nom else None
    if fc is not None:
        ok(fc.prestados("J. PEREZ") == ["."], f"el punto lo presta la predeterminada → {fc.prestados('J. PEREZ')}")
        ok(fc.faltantes("J. PEREZ") == [], "🔴 …y por eso «J. PEREZ» YA NO falta: la tizada sale")
        ok(fc.prestados("PEREZ-GOMEZ") == ["-"] and fc.faltantes("PEREZ-GOMEZ") == [],
           "lo mismo con el guion")
        ok(fc.prestados("MESSI") == [], "un nombre que la tipografía del diseño cubre entero no presta nada")
        ok(fc.prestados("N.N.") == ["."], "el mismo carácter no se repite en la lista")
        ok(fc.faltantes(" ") == [] and fc.prestados(" ") == [],
           "el espacio nunca falta ni se presta (tiene avance aunque no tenga contorno)")
        ok("." in fc.sustituidos and len(fc.sustituidos) == len(set(fc.sustituidos)),
           f"queda anotado qué se prestó, sin repetir: {fc.sustituidos}")
        # SE DIBUJA DE VERDAD
        _con = len(fc.ops_texto("J. PEREZ", 100, 0, 0))
        _sin = len(fc.ops_texto("J PEREZ", 100, 0, 0))
        ok(_con > _sin, f"el punto se DIBUJA (con punto {_con} trazos · sin punto {_sin})")
        ok(fc.ancho_texto("J. PEREZ", 100) > fc.ancho_texto("J PEREZ", 100),
           "…y ocupa su lugar: el nombre con punto mide más de ancho")

        # …Y DEL TAMAÑO QUE CORRESPONDE. Sin escalar por la altura de mayúscula, un punto prestado
        # sale notoriamente más chico o más grande que el resto del nombre.
        def _alto(f, ch):
            _ops, _ = f._glifo(ch)
            ys = [p[1] for _v, args in _ops for p in (args or ()) if p]
            return (max(ys) - min(ys)) / f.upem if ys else 0
        _prest = _alto(fc, ".") / (_alto(fc, "M") or 1)
        _orig = _alto(anton, ".") / (_alto(anton, "M") or 1)
        ok(abs(_prest - _orig) < 0.25 * _orig,
           f"el carácter prestado se ve del mismo tamaño (punto sobre M: prestado {_prest:.3f} · original {_orig:.3f})")

    # ── 2. EL MOLDE CON DISEÑO ADENTRO ──────────────────────────────────────────────────────
    print("\n2 · 🔴 EL AVISO SALE DEL MOLDE CUANDO NO HAY ARTE (camino B)")
    fuente_chars_src = inspect.getsource(S.fuente_chars)
    ok("_es_camino_b(pid)" in fuente_chars_src and "personalizacion_con_diseno" in fuente_chars_src,
       "`fuente_chars` mira el molde cuando es del camino B (antes leía sólo `arte.ai`)")
    ok("por_talle" in fuente_chars_src,
       "…y junta también la tipografía de CADA TALLE (en el camino B cada talle trae la suya)")
    # 🔴 UN MOLDE QUE TRAIGA NOMBRE Y NÚMERO. Antes se tomaba el PRIMER molde del camino B del
    # catálogo, y el 2026-09-16 ése pasó a ser el «Buzo medio cierre», que no tiene marcas «00» ni
    # «NOMBRE» (medido con el código viejo y el nuevo: ninguna). Devolver 0 caracteres ahí es lo
    # CORRECTO, y el contrato quedaba rojo por elegir mal el caso, no por un error del sistema.
    import piezas_con_diseno as _PDg
    cb = []
    try:
        cat_prod = S._cargar_catalogo()
        for p in (cat_prod.get("productos") or []):
            pid = p.get("id")
            if pid and S._es_camino_b(pid):
                _pl = S._ruta_entrada("plantilla.ai", pid)
                if _PDg.desplegado_listo(_pl) and (_PDg.personalizacion_con_diseno(_pl, armar=False) or {}):
                    cb.append(pid)
    except Exception:
        pass
    if not cb:
        print("    ⚠️    no hay ningún molde del camino B cargado CON nombre/número: no se puede probar en vivo")
    else:
        pid = cb[0]
        with S.app.test_request_context(f"/api/pedido/fuente_chars?producto_id={pid}"):
            d = S.fuente_chars().get_json()
        chars = d.get("chars") or ""
        ok(d.get("ok") and bool(chars), f"devuelve los caracteres del molde «{pid}» ({len(chars)}) · fuentes {d.get('fuentes')}")
        ok(bool(d.get("fuentes")), "…y de qué tipografía salieron")
        if chars and sin_punto:
            ok("." not in chars, "🔴 el punto NO figura como soportado: la planilla lo marca y avisa")
        ok("A" in chars and "5" in chars, "las letras y los números sí figuran")

    # ── 3. EL CAMINO A NO CAMBIA ────────────────────────────────────────────────────────────
    print("\n3 · EL MOLDE CON ARTE SIGUE SALIENDO DEL ARTE")
    ok('extraer_personalizacion(_ruta_entrada("arte.ai", pid))' in fuente_chars_src,
       "el camino A sigue leyendo la personalización del arte")

    # ── 4. EL MENSAJE DE LA TIZADA ──────────────────────────────────────────────────────────
    print("\n4 · 🔴 EL PRÉSTAMO SE ANOTA, SE AVISA, Y LO IMPOSIBLE SE EXPLICA")
    # `generar_pieza` vive ADENTRO de `generar_pedido`: se lee el archivo, no el objeto.
    src = io.open(os.path.join(_AQUI, "motor_pedido.py"), encoding="utf-8").read()
    ok("respaldo=_resp" in src, "el motor arma cada tipografía CON una de respaldo")
    ok('resolver_fuente("Anton Regular", carpeta_fuentes)' in src, "…y el respaldo es la predeterminada del sistema")
    ok("fnom.prestados(texto)" in src and "[tipografía]" in src,
       "lo prestado queda ANOTADO en el registro (que salga no quiere decir que no haya que saberlo)")
    ok("fnom.faltantes(texto)" in src and "y la predeterminada" in src,
       "y si no lo puede dibujar NADIE, el mensaje lo dice (no «glifo faltante»)")
    # la planilla avisa, pero como ADVERTENCIA: la tizada sale igual
    app = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
    ok("Se estampan con la tipografía predeterminada" in app,
       "la planilla dice que esos caracteres salen con la predeterminada")
    ok("no los tiene la fuente cargada" not in app,
       "…y ya no dice «revisá la fuente», que sonaba a que no se podía fabricar")

    print()
    if FALLOS:
        print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
        for f in FALLOS:
            print("   ·", f)
        sys.exit(1)
    print("✅ CONTRATO VERDE — el carácter que falta lo presta la predeterminada y el nombre sale entero")


if __name__ == "__main__":
    main()
