# -*- coding: utf-8 -*-
"""CONTRATO DE «00» Y «NOMBRE» (camino B) — `py verificar_placeholders_con_diseno.py [ruta.ai]`

Regla del usuario (2026-09-04): el molde con diseño trae, dentro de cada talle, el texto «00» donde
va el número y «NOMBRE» donde va el nombre. El sistema los detecta POR TEXTO, los saca del dibujo y
estampa en su lugar el valor de las columnas `numero` y `nombre` de la planilla, con la fuente, el
tamaño y el color nativo del archivo, talle por talle. Ver `MOLDE_CON_DISENO.md` §3.b y el
changelog 387 del mapa.

Lo que cuida:
  1. 🔴 Se detectan los dos placeholders en cada talle, con su tamaño (distinto por talle) y su
     color nativo. Incluido el «00», que viene codificado con `/Differences` y PyMuPDF no ve.
  2. 🔴 La página desplegada del talle NO conserva «NOMBRE» ni «00» como texto (si quedaran, se
     imprimirían debajo del nombre estampado).
  3. `extraer_personalizacion` del molde da `pers` con `por_talle` para el motor.
  4. Una pieza generada con nombre y número los estampa (más trazados que sin ellos) y no deja
     los placeholders como texto.

⚠️ No toca nada del usuario: trabaja sobre una copia en un temporal.
"""
import os
import shutil
import sys
import time
import types

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"
_f = types.ModuleType("db")
_f.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(AssertionError("LA PRUEBA TOCÓ MSSQL")))
sys.modules.setdefault("db", _f)

import pikepdf                       # noqa: E402
import pymupdf as fitz               # noqa: E402
import motor_pedido as MP            # noqa: E402
import piezas_con_diseno as PD       # noqa: E402

ORIG = sys.argv[1] if len(sys.argv) > 1 else \
    r"C:\Users\user2\Downloads\PRUEBA TIZADA PRO\para acomodo de archivos\CAMISETA JUGADOR.ai"
FALLOS = []


def ok(cond, msg):
    print(("    OK    " if cond else "    ❌    ") + msg)
    if not cond:
        FALLOS.append(msg)


def textos_de(pg, fuentes):
    tf, out = None, []
    for inst in pikepdf.parse_content_stream(pg):
        o = str(inst.operator)
        if o == "Tf":
            tf = str(inst.operands[0])
        if o in ("Tj", "TJ", "'", '"'):
            dec = PD._decodificador(fuentes.get(tf)) if tf in fuentes else None
            out.append(PD._texto_mostrado(o, inst.operands, dec).strip().upper())
    return out


def main():
    if not os.path.exists(ORIG):
        print(f"❌ no está el archivo de prueba:\n   {ORIG}")
        sys.exit(1)
    # Desplegar el molde real son ~90 s y el archivo no cambia entre corridas: se reusa el
    # despliegue guardado (`contrato_molde_b`). Un control que no se puede correr seguido
    # no protege nada -- y el tope de la tanda esta para eso.
    import contrato_molde_b as CB
    tmp, C, _alta_cb, _ = CB.espacio_desplegado(ORIG, "verif_ph_")
    print("CONTRATO DE «00» Y «NOMBRE» — el molde con diseño estampa nombre y número por texto\n")
    try:
        d = fitz.open(C)
        talles = PD.talles_del_molde(d)
        d.close()
        MESA = 1
        TA, TB = talles[len(talles) // 2], talles[-1]

        # ══ 1. LOS PLACEHOLDERS, POR TALLE ══════════════════════════════════════════════════════
        print("1 · 🔴 SE DETECTAN «00» Y «NOMBRE» EN CADA TALLE, CON SU TAMAÑO Y SU COLOR")
        t0 = time.time()
        PD.desplegar_mesa(C, MESA, talles)
        import json
        j = json.load(open(os.path.join(tmp, PD.DESPLEGADO, f"m{MESA}.json"), encoding="utf-8"))
        ph = j.get("placeholders") or {}
        print(f"          mesa {MESA} desplegada en {time.time()-t0:.0f}s · talles con placeholders: {len(ph)}/{len(talles)}")
        ok(len(ph) == len(talles), "los dos placeholders aparecen en TODOS los talles de la mesa")
        for tl in (TA, TB):
            p = ph.get(tl) or {}
            ok("nombre" in p and "numero" in p, f"talle {tl}: trae «nombre» y «numero»")
            if "nombre" in p and "numero" in p:
                print(f"          {tl}: nombre {p['nombre']['size']} pt · número {p['numero']['size']} pt · fuente {p['nombre']['fuente']} · colorn {p['nombre']['colorn']} · pasadas {len(p['nombre']['pasadas'])}")
                ok(p["numero"]["size"] > p["nombre"]["size"] > 0, f"talle {tl}: el número es más grande que el nombre (tamaños leídos del archivo)")
                ok(p["nombre"]["colorn"] and p["nombre"]["colorn"][0] in ("k", "rg", "g"), f"talle {tl}: color NATIVO (operador {p['nombre']['colorn'] and p['nombre']['colorn'][0]})")
        if TA in ph and TB in ph and "numero" in ph[TA] and "numero" in ph[TB]:
            ok(ph[TA]["numero"]["size"] != ph[TB]["numero"]["size"], f"el tamaño es POR TALLE ({TA}: {ph[TA]['numero']['size']} · {TB}: {ph[TB]['numero']['size']})")

        # ══ 2. NO QUEDAN COMO TEXTO EN LA PÁGINA DESPLEGADA ═════════════════════════════════════
        print("\n2 · 🔴 LA PÁGINA DESPLEGADA NO CONSERVA «NOMBRE» NI «00»")
        pdf = pikepdf.open(os.path.join(tmp, PD.DESPLEGADO, f"m{MESA}.pdf"))
        pg = pdf.pages[talles.index(TA)]
        fuentes = {str(k): v for k, v in (pg.Resources.get("/Font") or {}).items()}
        tx = textos_de(pg, fuentes)
        pdf.close()
        print(f"          textos que quedan en el talle {TA}: {tx}")
        ok("NOMBRE" not in tx and "00" not in tx, "ni «NOMBRE» ni «00» siguen en el dibujo")
        # …y lo mismo aislando el talle en el ORIGINAL: ahí sí tienen que estar (es lo que se sacó)
        src = pikepdf.open(C)
        import molde_real as MR
        pg0 = src.pages[MESA - 1]
        MR.aislar_capa(src, pg0, TA, podar=True)
        f0 = {str(k): v for k, v in (pg0.Resources.get("/Font") or {}).items()}
        tx0 = textos_de(pg0, f0)
        src.close()
        ok("NOMBRE" in tx0 and "00" in tx0, f"en el archivo original sí están (control: {sorted(set(tx0))})")

        # ══ 3. `pers` PARA EL MOTOR ═════════════════════════════════════════════════════════════
        print("\n3 · `extraer_personalizacion` ARMA LOS PLACEHOLDERS POR TALLE")
        alta = _alta_cb   # ya desplegado arriba
        PD.marcar(C, True)
        MP._DET_CACHE.clear()
        pers = MP.extraer_personalizacion(C)
        m1 = pers.get(str(MESA)) or {}
        ok("nombre" in m1 and "numero" in m1, f"pers[{MESA}] trae nombre y numero (mesas con placeholders: {sorted(pers)})")
        ok(TA in (m1.get("numero") or {}).get("por_talle", {}), f"y el número tiene su versión del talle {TA} (`por_talle`)")

        # ══ 4. LA PIEZA ESTAMPA NOMBRE Y NÚMERO ═════════════════════════════════════════════════
        print("\n4 · LA PIEZA GENERADA ESTAMPA «Jugador» Y «10» EN VECTOR, SIN DEJAR LOS PLACEHOLDERS")
        reg = alta["registro"]
        FUENTES = os.path.join(_AQUI, "catalogo_fuentes")
        kw = dict(borde_corte={"activo": True, "ancho_mm": 1.0, "color": [0, 0, 0, 1], "alineacion": "fuera"},
                  etiqueta={"activo": True, "size_mm": 3.0, "mostrar": {"talle": True, "pieza": True, "numero": True}})
        prendas = [{"talle": TA, "nombre": "Jugador", "numero": "10", "__variante": None}]
        out1 = os.path.join(tmp, "out1"); os.makedirs(out1)
        out2 = os.path.join(tmp, "out2"); os.makedirs(out2)
        con = MP.generar_pedido(C, None, reg, pers, prendas, FUENTES, out1, solo_piezas=True, **kw)
        sin = MP.generar_pedido(C, None, reg, {}, prendas, FUENTES, out2, solo_piezas=True, **kw)
        pz_con = next(p for lst in con.values() for p in lst if p["pieza"] == "Pieza 1")
        pz_sin = next(p for lst in sin.values() for p in lst if p["pieza"] == "Pieza 1")
        pg_con = pz_con["doc"][0]
        tx_pieza = [s["text"].strip().upper() for b in pg_con.get_text("dict")["blocks"] if b.get("type") == 0
                    for l in b["lines"] for s in l["spans"] if s["text"].strip()]
        n_con, n_sin = len(pg_con.get_drawings()), len(pz_sin["doc"][0].get_drawings())
        print(f"          trazados con personalización: {n_con} · sin: {n_sin} · textos que quedan: {tx_pieza}")
        ok("NOMBRE" not in tx_pieza and "00" not in tx_pieza, "la pieza no trae «NOMBRE» ni «00» como texto")
        ok(n_con > n_sin, "el nombre y el número se estamparon (hay trazados de más, en vector)")
        # ══ 5. LA FUENTE DEL ARCHIVO SE PUEDE CAMBIAR POR UNA NUESTRA ═══════════════════════════
        # Regla del usuario (2026-09-04): si la tipografía del «NOMBRE»/«00» no está, el sistema
        # avisa y deja cargarla o cambiarla por una del catálogo; si no se hace nada, sale con la
        # predeterminada. El aviso es `/api/pedido/fuentes_estado` (ramal camino B); acá se
        # verifica la otra mitad: que el reemplazo ELEGIDO llegue al estampado.
        print("\n5 · LA TIPOGRAFÍA DEL ARCHIVO SE PUEDE REEMPLAZAR POR UNA DEL CATÁLOGO")
        _fuente_arch = (m1.get("nombre") or {}).get("fuente")
        _cat = MP.catalogo_fuentes(FUENTES)
        _internos = sorted({i.get("interno") for i in _cat.values() if i.get("interno")})
        ok(bool(_fuente_arch), f"el placeholder dice con qué tipografía viene el archivo ({_fuente_arch})")
        ok(not MP.resolver_fuente(_fuente_arch, FUENTES),
           f"«{_fuente_arch}» NO está en el catálogo → tiene que avisar (si estuviera, este contrato no prueba nada)")

        # ⚠️ NO alcanza con contar trazados: `get_drawings` agrupa por operación de pintado, no por
        # glifo, y dos tipografías distintas dan el MISMO número (76 y 76, visto). Lo que las
        # distingue es la GEOMETRÍA: la suma de las cajas de los trazados.
        def _geo(fuentes, sub):
            out = os.path.join(tmp, sub)
            os.makedirs(out, exist_ok=True)
            r = MP.generar_pedido(C, None, reg, pers, prendas, fuentes, out, solo_piezas=True, **kw)
            pz = next(p for lst in r.values() for p in lst if p["pieza"] == "Pieza 1")
            g = round(sum(abs(x["rect"].width * x["rect"].height) for x in pz["doc"][0].get_drawings()), 1)
            for lst in r.values():
                for p in lst:
                    try:
                        p["doc"].close()
                    except Exception:
                        pass
            return g
        _otras = [i for i in _internos if "anton" not in i.lower()]
        if _otras:
            _g_def = _geo(FUENTES, "out_def")                     # sin la fuente y sin reemplazo
            _g_anton = _geo({"carpetas": [FUENTES], "alias": {_fuente_arch: "Anton Regular"}}, "out_anton")
            _g_otra = _geo({"carpetas": [FUENTES], "alias": {_fuente_arch: _otras[0]}}, "out_otra")
            print(f"          sin reemplazo: {_g_def} · forzando Anton: {_g_anton} · con «{_otras[0]}»: {_g_otra}")
            ok(_g_def == _g_anton,
               "sin cargar ni cambiar nada, se estampa con la PREDETERMINADA (idéntico a forzar Anton)")
            ok(_g_otra != _g_def,
               f"y eligiendo «{_otras[0]}» el estampado CAMBIA: el reemplazo del pedido manda")
        for lst in list(con.values()) + list(sin.values()):
            for p in lst:
                try:
                    p["doc"].close()
                except Exception:
                    pass
        MP.cerrar_abiertos()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FALLOS:
        print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
        for f in FALLOS:
            print("   ·", f)
        sys.exit(1)
    print("✅ CONTRATO VERDE — «00» y «NOMBRE» se leen por texto, se sacan del diseño y se estampan por talle")


if __name__ == "__main__":
    main()
