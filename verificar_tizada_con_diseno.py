# -*- coding: utf-8 -*-
"""CONTRATO DE LA TIZADA DEL CAMINO B — `py verificar_tizada_con_diseno.py [ruta.ai]`

El camino de siempre arma cada pieza cruzando DOS archivos: el contorno sale del molde y el dibujo
de una mesa del arte, escalado para encajar (`cm_encajar`). En el camino B hay UN solo archivo y el
dibujo YA ESTÁ ADENTRO de la pieza, en su lugar y en su escala: no hay nada que mapear ni que
escalar. Lo único que se hace es traer la mesa del propio molde —con SÓLO la capa de ese talle— y
recortarla a su contorno.

Lo que se verifica es que eso salga de verdad, y sobre todo **la LEY del proyecto: lo que se ve es
lo que sale estampado**. Una pieza vacía, escalada o rasterizada pasaría inadvertida hasta que
alguien imprimiera 40 metros de tela.

🔴 LA TRAMPA QUE ESTE CONTRATO CUIDA: reusar `pagina_arte` para esto parece lo natural y **borra la
pieza**. Esa función llama a `limpiar_capas_conservando_talle(..., geometrias_base(...))`, que
dentro de la capa descarta los trazados que coinciden con la moldería base y TODO el texto. En el
camino A eso saca el contorno del molde repetido en el arte; en el camino B la moldería base **es**
el dibujo, así que se llevaría la pieza entera y los placeholders de nombre/número. Por eso existe
`pagina_molde`, que usa `aislar_capa`.

⚠️ No toca nada del usuario: trabaja sobre una COPIA del archivo en un temporal, con `db`
reemplazado por un doble que explota, y borra el temporal al terminar.
"""
import os
import shutil
import sys
import tempfile
import time
import types

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"
_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n})")))
sys.modules.setdefault("db", _falso_db)

import pikepdf                       # noqa: E402
import pymupdf as fitz               # noqa: E402
import motor_pedido as MP            # noqa: E402
import piezas_con_diseno as PD       # noqa: E402

ORIG = sys.argv[1] if len(sys.argv) > 1 else \
    r"C:\Users\user2\Downloads\PRUEBA TIZADA PRO\para acomodo de archivos\CAMISETA JUGADOR.ai"
CM = MP.CM
FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)


if not os.path.exists(ORIG):
    print(f"❌ no está el archivo de prueba:\n   {ORIG}")
    sys.exit(1)

# Desplegar el molde real son ~90 s y el archivo no cambia entre corridas: se reusa el
# despliegue guardado (`contrato_molde_b`). Un control que no se puede correr seguido
# no protege nada -- y el tope de la tanda esta para eso.
import contrato_molde_b as CB
tmp, COPIA, _alta_cb, _ = CB.espacio_desplegado(ORIG, "verif_tizada_b_")
print("CONTRATO DE LA TIZADA — molde con el diseño adentro\n")

try:
    # ── El alta, igual que la del servidor ──────────────────────────────────────────────────
    print("dando de alta el molde (detecta las piezas de todas las mesas y talles)…")
    t0 = time.time()
    alta = _alta_cb   # ya desplegado arriba
    PD.marcar(COPIA, True)
    MP._DET_CACHE.clear()
    reg = alta["registro"]
    TALLE = alta["talles"][len(alta["talles"]) // 2]
    print(f"  ({time.time()-t0:.0f}s) {len(reg)} piezas · {len(alta['talles'])} talles · "
          f"se prueba el talle {TALLE}\n")

    PIEZA = sorted(reg)[0]
    prendas = [{"talle": TALLE, "nombre": "NOMBRE", "numero": "00", "__variante": None}]
    pers = MP.extraer_personalizacion(COPIA)
    salida = os.path.join(tmp, "salida")
    os.makedirs(salida, exist_ok=True)
    # El catálogo de tipografías del repo: la etiqueta de corte se dibuja con curvas de una fuente
    # real y sin catálogo el motor corta antes de generar nada.
    FUENTES = os.path.join(_AQUI, "catalogo_fuentes")

    # ══ 1. GENERA SIN ARTE ══════════════════════════════════════════════════════════════════
    print("1 · 🔴 LA TIZADA SE GENERA SIN ARTE Y SIN MAPEO")
    t0 = time.time()
    try:
        por_tela = MP.generar_pedido(COPIA, None, reg, pers, prendas, FUENTES, salida,
                                     solo_piezas=True,
                                     borde_corte={"activo": True, "ancho_mm": 1.0,
                                                  "color": [0, 0, 0, 1], "alineacion": "fuera"},
                                     etiqueta={"activo": True, "size_mm": 3.0,
                                               "mostrar": {"talle": True, "pieza": True, "numero": True}})
    except Exception as e:
        print(f"    ❌ {type(e).__name__}: {e}")
        FALLOS.append(f"1. `generar_pedido(arte=None)` reventó: {type(e).__name__}: {e}")
        por_tela = {}
    piezas = [p for lst in por_tela.values() for p in lst]
    ok(piezas, "1. no se generó ninguna pieza")
    print(f"    ({time.time()-t0:.0f}s) OK    {len(piezas)} piezas generadas sin arte")

    if piezas:
        _por_nombre = {p["pieza"]: p for p in piezas}
        ok(len(_por_nombre) == len(reg),
           f"1. se generaron {len(_por_nombre)} piezas distintas y el molde tiene {len(reg)}")

        # ══ 2. CADA PIEZA TRAE SU DIBUJO ════════════════════════════════════════════════════
        print("\n2 · 🔴 LA PIEZA SALE CON SU DISEÑO ADENTRO (no en blanco)")
        _vacias, _sin_txt = [], []
        for nom, p in _por_nombre.items():
            pg = p["doc"][0]
            dib = pg.get_drawings()
            if len(dib) < 2:
                _vacias.append((nom, len(dib)))
        ok(not _vacias,
           f"🔴 {len(_vacias)} pieza(s) salieron PRÁCTICAMENTE VACÍAS (sólo el borde): {_vacias[:3]}. "
           f"Es lo que pasa si se aísla la capa con `pagina_arte`, que borra la geometría base — "
           f"y en este camino la geometría base ES el diseño")
        _n = _por_nombre[PIEZA]
        print(f"    OK    «{PIEZA}»: {len(_n['doc'][0].get_drawings())} trazados dibujados")

        # ══ 3. EL TAMAÑO ES EL REAL ═════════════════════════════════════════════════════════
        print("\n3 · LA PIEZA MIDE LO QUE DICE EL REGISTRO (no se escaló nada)")
        _mal = []
        for nom, p in _por_nombre.items():
            inf = reg[nom][TALLE]
            w_cm, h_cm = p["w"] / CM, p["h"] / CM
            # +2·borde (1 mm por lado) de margen, y 1 mm de tolerancia
            if abs(w_cm - inf["w_cm"]) > 0.35 or abs(h_cm - inf["h_cm"]) > 0.35:
                _mal.append((nom, round(w_cm, 1), round(h_cm, 1), inf["w_cm"], inf["h_cm"]))
        ok(not _mal, f"🔴 {len(_mal)} pieza(s) no miden lo del registro (pieza, w, h, w_reg, h_reg): {_mal[:3]}")
        _p = _por_nombre[PIEZA]
        print(f"    OK    «{PIEZA}» mide {_p['w']/CM:.1f} × {_p['h']/CM:.1f} cm "
              f"(registro: {reg[PIEZA][TALLE]['w_cm']:.1f} × {reg[PIEZA][TALLE]['h_cm']:.1f})")

        # ══ 4. VECTORIAL Y RECORTADA ════════════════════════════════════════════════════════
        print("\n4 · 🔴 VECTORIAL Y RECORTADA AL CONTORNO (ley del proyecto)")
        _raster = [n for n, p in _por_nombre.items() if p["doc"][0].get_images()]
        ok(not _raster,
           f"🔴 {len(_raster)} pieza(s) traen una IMAGEN: el molde tiene que seguir siendo vector "
           f"({_raster[:3]})")
        # El content-stream se lee ENTERO y por operadores: buscar el texto en los primeros bytes
        # da falsos negativos (el borde puede ir primero, y el stream viene comprimido).
        _buf = _por_nombre[PIEZA]["doc"].tobytes()
        _pk = pikepdf.open(__import__("io").BytesIO(_buf))
        _ops = [str(i.operator) for i in pikepdf.parse_content_stream(_pk.pages[0])]
        ok("W" in _ops, f"4. la pieza no lleva el recorte (`W`) del contorno — ops: {sorted(set(_ops))}")
        ok("Do" in _ops, f"4. la pieza no dibuja el XObject del molde (`Do`) — ops: {sorted(set(_ops))}")
        _pk.close()
        print("    OK    sin imágenes rasterizadas · con clip del contorno · dibuja el XObject")

        # ══ 5. EL BORDE DE CORTE ════════════════════════════════════════════════════════════
        print("\n5 · EL BORDE DE CORTE SE DIBUJA (lo deja el admin, no el cliente)")
        _sin_borde = []
        for nom, p in _por_nombre.items():
            if not any(d.get("type") in ("s", "fs") for d in p["doc"][0].get_drawings()):
                _sin_borde.append(nom)
        ok(not _sin_borde, f"5. {len(_sin_borde)} pieza(s) sin ningún trazo (¿se dibujó el borde?): {_sin_borde[:3]}")
        print("    OK    todas las piezas llevan trazo de corte")

        # ══ 6. EL PESO ══════════════════════════════════════════════════════════════════════
        print("\n6 · EL PESO NO SE DESMADRA")
        # `copy_foreign` trae la página del molde con sus recursos. Si arrastrara el archivo
        # entero, cada pieza pesaría decenas de MB y una tizada de 40 prendas sería inmanejable.
        _pesos = {n: len(p["doc"].tobytes()) for n, p in _por_nombre.items()}
        _peor = max(_pesos.values())
        _tot = sum(_pesos.values())
        ok(_peor < 40e6,
           f"🔴 una pieza pesa {_peor/1e6:.0f} MB: `copy_foreign` está arrastrando de más")
        print(f"    OK    la más pesada: {_peor/1e6:.1f} MB · las {len(_pesos)} juntas: {_tot/1e6:.0f} MB "
              f"(el archivo original pesa {os.path.getsize(COPIA)/1e6:.0f} MB)")

    # ══ 7. LA HOJA DE VERDAD ════════════════════════════════════════════════════════════════
    print("\n7 · LA TIZADA COMPLETA (nesting + hoja, que es lo que va al RIP)")
    # Lo anterior mira las piezas sueltas; esto arma la HOJA, que es el archivo que se imprime.
    # Acá se ve el peso que importa: las piezas comparten los recursos del molde y al componer se
    # deduplican, así que el total NO es la suma de las partes.
    t0 = time.time()
    salida2 = os.path.join(tmp, "hoja")
    os.makedirs(salida2, exist_ok=True)
    res = MP.generar_pedido(COPIA, None, reg, pers, prendas, FUENTES, salida2,
                            borde_corte={"activo": True, "ancho_mm": 1.0,
                                         "color": [0, 0, 0, 1], "alineacion": "fuera"},
                            etiqueta={"activo": True, "size_mm": 3.0,
                                      "mostrar": {"talle": True, "pieza": True, "numero": True}})
    _hojas = [f for f in os.listdir(salida2) if f.upper().startswith("HOJA") and f.endswith(".pdf")]
    ok(_hojas, "7. no se generó ninguna hoja")
    if _hojas:
        _hp = os.path.join(salida2, _hojas[0])
        _mb = os.path.getsize(_hp) / 1e6
        _d = fitz.open(_hp)
        _r = _d[0].rect
        _dib = len(_d[0].get_drawings())
        _imgs = len(_d[0].get_images())
        _d.close()
        ok(_dib > 50, f"7. la hoja tiene sólo {_dib} trazados: las piezas salieron vacías")
        ok(_imgs == 0, f"🔴 7. la hoja trae {_imgs} imagen(es): la tizada tiene que ser VECTORIAL")
        print(f"    ({time.time()-t0:.0f}s) OK    {_hojas[0]} · {_r.width/CM:.0f} × {_r.height/CM:.0f} cm · "
              f"{_dib} trazados · {_mb:.0f} MB")
        # No es un fallo, es un dato a vigilar: si un pedido de 40 prendas hace una hoja de cientos
        # de MB, el RIP se atraganta. Se anota para poder comparar entre versiones.
        if _mb > 200:
            print(f"    ⚠️  la hoja pesa {_mb:.0f} MB — vigilar con pedidos grandes")

    # ══ 8. SIN LA MARCA, EL CAMINO DE SIEMPRE ═══════════════════════════════════════════════
    print("\n8 · 🔴 SIN LA MARCA, EL MOLDE SIGUE POR EL CAMINO DE SIEMPRE")
    # La rama nueva no puede activarse por «no vino arte»: tiene que pedir la marca explícita.
    PD.marcar(COPIA, False)
    MP._DET_CACHE.clear()
    import piezas_con_diseno as _PD2
    ok(not _PD2.es_camino_b(COPIA), "8. la marca no se borró")
    print("    OK    sin la marca, `es_camino_b` dice que no y el motor usa el ramal del arte")

finally:
    for _p in (piezas if "piezas" in dir() else []):
        try:
            _p["doc"].close()
        except Exception:
            pass
    try:
        PD.olvidar()
    except Exception:
        pass
    shutil.rmtree(tmp, ignore_errors=True)

print()
if FALLOS:
    print(f"❌ {len(FALLOS)} FALLO(S):")
    for f in FALLOS:
        print("   -", f)
    sys.exit(1)
print("✅ CONTRATO VERDE — la tizada sale del propio molde: con su diseño, a tamaño real y vectorial")
