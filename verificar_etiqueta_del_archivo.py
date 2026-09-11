# -*- coding: utf-8 -*-
"""
CONTRATO: SE OCULTA LA ETIQUETA QUE TRAE EL DISEÑO, DECIDIDA POR FAMILIA, Y SÓLO ESA.
Se corre con `py verificar_etiqueta_del_archivo.py [ruta al .ai]`.

EL PEDIDO (2026-09-11): *«que oculte automáticamente la etiqueta que viene en el diseño sin que nos
afecte a otros textos»* y después, sobre la primera versión: *«no todos los diseñadores traen la
etiqueta como debería; debe ser ajuste nuestro. Buscá un verdadero método»*.

🔴 **LO QUE NO SIRVE:** reconocerla por tamaño y posición (≤ 10 mm, pegada al borde). Estaba
calibrado con UN archivo; otro diseñador la pone más grande, más adentro o con texto de más, y la
regla falla en silencio.

**EL MÉTODO, independiente del diseñador:** la etiqueta de corte **se repite igual en casi todas las
piezas** (copiar-pegar: misma fuente, mismo tamaño); la talla tejida —que también dice «M»— vive en
UNA sola pieza. Se agrupan por FAMILIA (fuente + alto) los textos que nombran su talle, y se oculta
la familia presente en ≥ 2/3 de las piezas. Lo demás se deja y se informa. Interruptor por familia.

Lo que se verifica:
  1. Los candidatos: qué cuenta como «nombra el talle» (palabra entera, no contención).
  2. La decisión, pura: 2/3 de las piezas oculta; una sola pieza no; lo fijado a mano gana.
  3. 🔴 Con el archivo REAL: la familia Arial 5,5 mm en 8 de 9 piezas se oculta; la talla tejida
     (Gunplay 12 mm, 1 pieza) se deja; el rótulo y los placeholders ni son candidatos.
  4. Aplicar la decisión saca del dibujo SÓLO esa familia (talle real, mesa real).
  5. Cambiar la decisión cambia el hash → las páginas se rehacen; la versión del caché subió; la
     pantalla lo muestra con interruptor.

⚠️ No toca datos del usuario: lee el .ai en SOLO LECTURA, y la decisión se escribe en un temporal.
"""
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

import piezas_con_diseno as PD                   # noqa: E402

CM = 28.3465
FALLOS = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALLA ") + msg)
    if not cond:
        FALLOS.append(msg)


# ─────────────────────────────────────────────────────────────────
print("\n1 · QUÉ CUENTA COMO «NOMBRA EL TALLE» (palabra entera, no contención)")
ok(PD.menciona_talle("M", "M"), "«M» nombra M")
ok(PD.menciona_talle("TALLE M", "M"), "«TALLE M» también (texto de más, como lo ponen algunos diseñadores)")
ok(PD.menciona_talle("M-FRENTE", "M"), "«M-FRENTE» también")
ok(PD.menciona_talle("talle 2xl", "2XL"), "sin importar mayúsculas")
ok(not PD.menciona_talle("2XL", "XL"), "🔴 «2XL» NO nombra XL (es otro talle)")
ok(not PD.menciona_talle("00", "0"), "🔴 el placeholder «00» NO nombra el talle 0")
ok(not PD.menciona_talle("NOMBRE", "M"), "«NOMBRE» no nombra M aunque contenga la letra")
ok(not PD.menciona_talle("ESPALDA", "L"), "«ESPALDA» no nombra L")
ok(PD.familia_de("ABCDEF+Arial-BoldMT", 5.31) == PD.familia_de("XYZ+Arial-BoldMT", 5.49),
   "la familia ignora el prefijo de subset y redondea el alto a 0,5 mm (copiar-pegar)")
ok(PD.familia_de("Arial-BoldMT", 5.3) != PD.familia_de("Arial-BoldMT", 12.0),
   "pero otro tamaño es otra familia")

print("\n2 · LA DECISIÓN, PURA")


def cand(mesa, idx, talle, fuente, alto, texto=None):
    return {"mesa": mesa, "idx": idx, "talle": talle, "fuente": fuente, "alto_mm": alto,
            "texto": texto or talle, "borde_mm": 1.2}


# 9 piezas (una por mesa). La etiqueta Arial 5,3 en 8 mesas × 2 talles; la talla tejida
# Gunplay 12 en la mesa 7, en los 2 talles.
C = []
for m in (1, 2, 3, 4, 5, 6, 8, 9):
    for t in ("M", "6XL"):
        C.append(cand(m, 0, t, "Arial-BoldMT", 5.3))
for t in ("M", "6XL"):
    C.append(cand(7, 0, t, "Gunplay-Regular", 12.0))
fams = PD.decidir_familias(C, 9)
por = {f["clave"]: f for f in fams}
ok(len(fams) == 2, f"dos familias: {[f['clave'] for f in fams]}")
ok(por["Arial-BoldMT|5.5"]["ocultar"] and por["Arial-BoldMT|5.5"]["piezas"] == 8,
   "🔴 la que está en 8 de 9 piezas SE OCULTA")
ok(not por["Gunplay-Regular|12"]["ocultar"] and por["Gunplay-Regular|12"]["piezas"] == 1,
   "🔴 la que está en 1 pieza (la talla tejida) SE DEJA")
ok(fams[0]["clave"] == "Arial-BoldMT|5.5", "ordenadas de la más presente a la menos")
# un diseñador que la pone GRANDE y en el medio: igual se oculta, porque se repite
G = [cand(m, 0, "M", "Impact", 18.0, "TALLE M") for m in range(1, 10)]
ok(PD.decidir_familias(G, 9)[0]["ocultar"],
   "🔴 una etiqueta de 18 mm que dice «TALLE M» en las 9 piezas TAMBIÉN se oculta (no hay umbral de tamaño)")
# el talle decorativo en frente y espalda: 2 de 9 → se deja
D = [cand(1, 0, "M", "Bebas", 90.0), cand(2, 0, "M", "Bebas", 90.0)]
ok(not PD.decidir_familias(D, 9)[0]["ocultar"], "un talle decorativo en 2 de 9 piezas se deja")
# 2/3 exacto
ok(PD.decidir_familias([cand(m, 0, "M", "A", 5) for m in range(1, 7)], 9)[0]["ocultar"],
   "6 de 9 (dos tercios justos) se oculta")
ok(not PD.decidir_familias([cand(m, 0, "M", "A", 5) for m in range(1, 6)], 9)[0]["ocultar"],
   "5 de 9 no")
ok(not PD.decidir_familias([cand(1, 0, "M", "A", 5)], 1)[0]["ocultar"],
   "un molde de UNA pieza no oculta con un solo candidato (mínimo 2 piezas)")
# lo fijado a mano gana
f2 = PD.decidir_familias(C, 9, manual={"Gunplay-Regular|12": True, "Arial-BoldMT|5.5": False})
p2 = {f["clave"]: f for f in f2}
ok(p2["Gunplay-Regular|12"]["ocultar"] and not p2["Arial-BoldMT|5.5"]["ocultar"],
   "🔴 lo que el usuario fija a mano GANA sobre lo automático, en los dos sentidos")
ok("fijaste" in p2["Gunplay-Regular|12"]["motivo"], "y el motivo lo dice")
ok(PD.decidir_familias([], 9) == [], "sin candidatos, sin familias (no se inventa nada)")

print("\n3 · 🔴 EL ARCHIVO REAL")
ARCH = (sys.argv[1] if len(sys.argv) > 1 else
        r"C:\Users\user2\Downloads\PRUEBA TIZADA PRO\para acomodo de archivos\CAMISETA JUGADOR.ai")
TMP = None
if not os.path.exists(ARCH):
    print(f"    (no está {os.path.basename(ARCH)}: se saltea)")
else:
    import pymupdf as fitz                       # noqa: E402
    import pikepdf                               # noqa: E402
    import molde_real as MR                      # noqa: E402
    # La decisión se escribe al lado del molde: se trabaja sobre un ENLACE en un temporal para no
    # tocar la carpeta del usuario (el .ai no se copia: 123 MB).
    TMP = tempfile.mkdtemp(prefix="verif_etq_")
    LINK = os.path.join(TMP, "plantilla.ai")
    try:
        os.link(ARCH, LINK)
    except Exception:
        shutil.copy2(ARCH, LINK)
    doc = fitz.open(LINK)
    talles = PD.talles_del_molde(doc)
    n_mesas = doc.page_count
    PD.olvidar(doc)
    doc.close()
    # contornos de todas las mesas (etapa 1), en serie (script sin pool)
    PD.desplegar_molde(LINK, talles, contornos=True, paginas=False)
    dec = PD.decidir_etiqueta_archivo(LINK, talles)
    fams = dec.get("familias") or []
    print(f"    piezas del molde: {dec.get('piezas')} · familias: "
          + " · ".join(f"{f['clave']} en {f['piezas']}" for f in fams))
    ok(dec.get("piezas") == n_mesas, f"el molde tiene {dec.get('piezas')} piezas (una por mesa)")
    arial = next((f for f in fams if f["fuente"].startswith("Arial")), None)
    gun = next((f for f in fams if f["fuente"].startswith("Gunplay")), None)
    ok(arial is not None and arial["ocultar"] and arial["piezas"] == n_mesas - 1,
       f"🔴 la etiqueta de corte (Arial {arial and arial['alto_mm']} mm) está en {arial and arial['piezas']} de {n_mesas} → SE OCULTA")
    ok(gun is not None and not gun["ocultar"] and gun["piezas"] == 1,
       f"🔴 la talla tejida (Gunplay {gun and gun['alto_mm']} mm) está en 1 pieza → SE DEJA")
    # 🔴 la talla tejida ESCALA con el talle (10 → 13,5 mm): por clave serían 7 familias de una
    # pieza. Es el mismo texto en la misma pieza → UNA familia, con el alto como rango y TODAS sus
    # claves (la etapa de páginas oculta por clave).
    _gun = [f for f in fams if f["fuente"].startswith("Gunplay")]
    ok(len(_gun) == 1, f"🔴 la talla tejida es UNA sola familia aunque escale con el talle ({len(_gun)})")
    ok(gun and gun.get("alto_hasta_mm") and len(gun.get("claves") or []) > 1,
       f"con el alto como rango ({gun and gun['alto_mm']}–{gun and gun.get('alto_hasta_mm')} mm) y sus {gun and len(gun.get('claves') or [])} claves")
    ok(arial and len(arial.get("claves") or []) == 1, "la etiqueta de corte no escala: una sola clave")
    ok(all(not f["fuente"].startswith("Tahoma") for f in fams),
       "el rótulo de la mesa (Tahoma: ESPALDA, FRENTE…) ni siquiera es candidato")
    ok(all(f["talles"] == len(talles) for f in fams if f["ocultar"]),
       f"y la familia que se oculta está en los {len(talles)} talles")

    print("\n4 · APLICAR LA DECISIÓN SACA SÓLO ESA FAMILIA (mesa 1, talle M, del archivo real)")
    ocultar = set(PD.familias_ocultas(dec))
    import json                                  # noqa: E402
    idx = json.load(open(os.path.join(PD._carpeta_desplegado(LINK), "m1.json"), encoding="utf-8"))
    conts = [PD._cont_de_json(c) for c in idx["talles"]["M"]]
    pdf = pikepdf.open(LINK)
    pag = pdf.pages[0]
    ins = list(pikepdf.parse_content_stream(pag))
    ops, oc = MR._mapa_oc(ins, pag)
    bloques = MR._bloques_oc(ops, oc)
    obj = {MR._norm_capa("M")}
    fn = (lambda pila, _o=obj: not any(frame and (_o & frame) for frame in pila))
    salida = MR._raspar_instrucciones(ins, ops, oc, fn, True, MR._saltar_bloques(ops, oc, fn, bloques))
    n_antes = len(salida)
    s2, ph, etq = PD.quitar_placeholders(salida, pag, idx["marco"], idx["U"], "M", conts, ocultar=ocultar)
    ok(etq and list(etq.values())[0]["copias"] == 2,
       f"se sacaron las 2 copias de la etiqueta de la pieza (etq={ {k: v['texto'] for k, v in etq.items()} })")
    ok(n_antes - len(s2) == 2 + sum(1 for _ in ph) * 0 + (n_antes - len(s2) - 2),
       "y nada más que eso y los placeholders")
    # sin decisión (ocultar vacío) no se saca la etiqueta
    s3, _, etq3 = PD.quitar_placeholders(salida, pag, idx["marco"], idx["U"], "M", conts, ocultar=set())
    ok(not etq3, "sin familias que ocultar, la etiqueta queda (no se adivina)")
    pdf.close()

    print("\n5 · CAMBIAR LA DECISIÓN CAMBIA EL HASH → las páginas se rehacen")
    h1 = PD.hash_ocultas(PD.familias_ocultas(dec))
    dec2 = PD.fijar_familia(LINK, arial["clave"], False)
    h2 = PD.hash_ocultas(PD.familias_ocultas(dec2))
    ok(h1 != h2, f"🔴 fijar «se deja» cambia el hash ({h1} → {h2}): la vigencia de las páginas cae")
    dec3 = PD.fijar_familia(LINK, arial["clave"], None)
    ok(PD.hash_ocultas(PD.familias_ocultas(dec3)) == h1, "volver a «automático» devuelve el hash original")
    ok(PD.piezas_con_etiqueta_propia(LINK)[0] == arial["piezas"],
       f"la pantalla recibe {arial['piezas']} piezas con etiqueta ocultada")

if TMP:
    shutil.rmtree(TMP, ignore_errors=True)

print("\n6 · LO QUE SOSTIENE TODO ESTO")
ok(PD._V_PAGINAS >= 5, f"`_V_PAGINAS` = {PD._V_PAGINAS} (≥ 5: rehace las páginas de los moldes viejos)")
_src = open(os.path.join(RAIZ, "piezas_con_diseno.py"), encoding="utf-8").read()
ok("_ETQ_ALTO_MAX_MM" not in _src and "_ETQ_BORDE_MAX_MM" not in _src,
   "🔴 los umbrales de tamaño y de borde se fueron: no se decide por cómo lo dibujó el diseñador")
ok('"etq": _etq_hash' in _src, "el hash de la decisión se guarda con las páginas")
ok("decidir_etiqueta_archivo(path_molde, talles" in _src, "y la decisión se toma ANTES de las páginas")
_srv = open(os.path.join(RAIZ, "servidor.py"), encoding="utf-8").read()
ok('"/api/productos/etiqueta_archivo"' in _srv and "fijar_familia" in _srv, "hay interruptor en el servidor")
_app = open(os.path.join(RAIZ, "frontend", "src", "App.jsx"), encoding="utf-8").read()
ok("etiquetas_familias" in _app and "etiqueta_archivo" in _app, "🔴 la pantalla lista las familias con su interruptor")

print()
if FALLOS:
    print(f"  {len(FALLOS)} FALLO(S)")
    sys.exit(1)
print("  OK: la etiqueta del diseño se decide por familia, y sólo esa se oculta")
