# -*- coding: utf-8 -*-
"""
CONTRATO: LA TIZADA PARA CORTE (MAPA 816) — `py verificar_tizada_corte.py`

Pedido del usuario 2026-11-23: un tercer camino en el pedido, «Tizada para corte»: lo mismo que «Armar con
base» pero SIN el arte; sale la línea de corte de cada pieza; cada talle en su mesa de entrada; y al descargar
se elige el formato de la máquina (DXF 2000, Illustrator 3, PLT, SVG, EPS o el PDF).

De punta a punta, con el molde real del camino A (COPIADO a un temporal; `db` es un doble):
  1 · el PLAN del servidor con `corte`: sin arte, sin nombre ni número (aunque la planilla los marque
      obligatorios), la línea de corte prendida aunque el molde la tenga apagada, sin perfil de color,
      «cada talle en su mesa» (`talles_mesa_modo: cada_uno`), y frena el molde a medida y el que trae el
      diseño adentro (422); `generar_multi` dice que no (409: la arma la computadora);
  2 · el MOTOR DEL NAVEGADOR (Node, `pruebas/tizada.mjs` → `pedido/generar.js`, rama `md.corte`) arma la
      tizada: una mesa por talle, cada pieza con su línea de corte y su etiqueta, sin imágenes;
  3 · cada mesa en los CINCO formatos (`corte/exportar.js`): el DXF lo abre y lo audita un lector
      independiente (ezdxf) sin errores, con una línea de corte por pieza y del tamaño de la mesa; el SVG
      tiene sus dos capas; AI 3, EPS y PLT con su encabezado y la misma cantidad de contornos.
⚠️ No toca nada del usuario. Marcado CONTRATO_LENTO.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import time

CONTRATO_LENTO = True
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
os.environ["TIZADA_SOLO_NAVEGADOR"] = "1"
import verificar_navegador_tizada as VT       # noqa: E402  (el entorno temporal y el doble de la base)

S, MP, fitz = VT.S, VT.MP, VT.fitz
ok, FALLOS, _TMP, NODE = VT.ok, VT.FALLOS, VT._TMP, VT.NODE
PID = "prod_corte"
PID_AM = "prod_corte_a_medida"
PID_B = "prod_corte_con_diseno"
ORIGEN = os.path.join(AQUI, "entrada", "prod_20260820_095558_38bc")
DATOS_ORIGEN = os.path.join(AQUI, "datos", "productos", "prod_20260820_095558_38bc")
EXPORTAR = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "corte_exportar.mjs")


def main():
    print("\n1 · EL MOLDE BASE (SIN ARTE) Y EL PEDIDO")
    carpeta = os.path.join(_TMP, "entrada", PID)
    os.makedirs(carpeta)
    shutil.copy2(os.path.join(ORIGEN, "plantilla.ai"), os.path.join(carpeta, "plantilla.ai"))
    pl = os.path.join(carpeta, "plantilla.ai")
    pz = json.load(open(os.path.join(DATOS_ORIGEN, "piezas.json"), encoding="utf-8"))
    emp = json.load(open(os.path.join(DATOS_ORIGEN, "emparejado_talles.json"), encoding="utf-8"))
    asign = [{"idx": int(p["ancla"]["idx"]), "nombre": p["clave"]} for p in pz["piezas"] if (p.get("ancla") or {}).get("talle") == "M"]
    registro = MP.alta_plantilla_manual(pl, asign, 1, "M", emparejado=emp)["registro"]
    for p in (PID, PID_AM, PID_B):
        VT._REG[p] = registro
    # el molde que trae el diseño adentro: la marca del alta al lado de su archivo
    for p in (PID_AM, PID_B):
        os.makedirs(os.path.join(_TMP, "entrada", p))
        shutil.copy2(pl, os.path.join(_TMP, "entrada", p, "plantilla.ai"))
    import piezas_con_diseno as PD
    open(PD._ruta_marca(os.path.join(_TMP, "entrada", PID_B, "plantilla.ai")), "w").write("con_diseno")
    talles = sorted({t for v in registro.values() for t in v})
    VT._DOCS["catalogo"] = {"activo": PID, "productos": [
        {"id": PID, "nombre": "Molde de prueba de corte", "planilla_template_id": "plan_corte", "variante_guia": "M",
         "referencia_medida": "alto",
         # 🔴 la línea de corte APAGADA en el molde: en la tizada para corte igual tiene que salir
         "borde_corte": {"activo": False, "ancho_mm": 1.5, "color": [0, 1, 1, 0], "alineacion": "fuera"}},
        {"id": PID_AM, "nombre": "Bandera a medida", "planilla_template_id": "plan_corte",
         "a_medida": {"pieza": "Bandera", "ancho_m": 1, "alto_m": 1}},
        {"id": PID_B, "nombre": "Camiseta con diseño", "planilla_template_id": "plan_corte", "origen": "con_diseno"}],
        "plantillas_planillas": [{"id": "plan_corte", "nombre": "Corte", "columnas": [
            {"id": "talle", "label": "Talle", "role": "talle", "obligatoria": True},
            # nombre y número OBLIGATORIOS en la planilla: en la tizada para corte no se exigen
            {"id": "nombre", "label": "Nombre", "role": "nombre", "obligatoria": True},
            {"id": "numero", "label": "Número", "role": "numero", "obligatoria": True}]}],
        "reglas_planilla": [], "telas": []}
    comunes = [t for t in ["S", "M", "L", "XL"] if t in talles] or talles[:3]
    elegidos = [comunes[0], comunes[len(comunes) // 2], comunes[-1]][:3]
    # filas SIN nombre ni número, dos del primer talle
    filas = [{"talle": t} for t in elegidos] + [{"talle": elegidos[0]}]
    cuerpo = {"molds": [PID], "prendas": filas, "default_diseno": "principal", "corte": True,
              "talles_mesa_modo": "cada_uno",
              "planilla": {"columnas": [{"id": "talle", "label": "Talle", "role": "talle"}], "filas": filas}}
    ok(len(registro) >= 30, f"{len(registro)} piezas en el registro · talles del pedido {elegidos} · {len(filas)} prendas sin nombre ni número")

    print("\n2 · EL PLAN DEL SERVIDOR")
    with S.app.test_request_context("/api/pedido/plan", method="POST", json=cuerpo):
        plan = S._plan_del_pedido(cuerpo)
        plan_nav = S._plan_para_navegador(plan)
    md = (plan_nav.get("moldes") or [{}])[0]
    ok(plan_nav.get("corte") is True and md.get("corte") is True, "el plan dice «corte» (el pedido y el molde)")
    ok(md.get("camino_b") is False and not md.get("clasico") and not md.get("mapeo_arte"), "el molde no pasa por camino B ni por el arte")
    ok(plan_nav.get("todo_navegador") is True, "el navegador lo puede armar")
    ok(not md.get("pers"), "sin nombre ni número para estampar")
    ok((md.get("etiqueta") or {}).get("activo") is False, "sin etiqueta: sólo el molde (regla del usuario 2026-11-23)")
    ok(len(md.get("prendas") or []) == len(filas), f"las {len(filas)} filas sin nombre ni número entran (la planilla los marca obligatorios)")
    ok((md.get("borde_corte") or {}).get("activo") is True, "la línea de corte prendida aunque el molde la tenga apagada")
    ok(plan_nav.get("perfil") is not None, "con su perfil de color, como toda hoja (si no, la revisión del RIP avisa que falta)")
    ok(plan_nav["cfg_nesting"].get("por_talles_mesa") is True and plan_nav["cfg_nesting"].get("talles_mesa_modo") != "separados",
       "«cada talle en su mesa»: mesas por talle (no apiladas en la misma)")
    _g = {}
    for pr in md.get("prendas") or []:
        _g.setdefault(pr.get("_grupo_mesa"), set()).add(pr.get("talle"))
    ok(len(_g) == len(elegidos) and all(len(v) == 1 for v in _g.values()) and None not in _g,
       f"cada talle con su grupo de mesa: {sorted((k, sorted(v)) for k, v in _g.items())}")
    for p, que in ((PID_AM, "a medida"), (PID_B, "con el diseño adentro")):
        c2 = dict(cuerpo, molds=[p])
        try:
            with S.app.test_request_context("/api/pedido/plan", method="POST", json=c2):
                S._plan_del_pedido(c2)
            ok(False, f"el molde {que} tenía que frenarse")
        except S._PlanInvalido as e:
            _d = e.resp.get_json() if hasattr(e.resp, "get_json") else {}
            ok(e.code == 422 and "corte" in str(_d.get("error", "")), f"el molde {que} se frena (422): «{_d.get('error')}» — {_d.get('detalle')}")
    with S.app.test_client() as cl:
        r = cl.post("/api/generar_multi", json=cuerpo)
    ok(r.status_code == 409, f"generar_multi no la arma en el servidor ({r.status_code}: {(r.get_json() or {}).get('error')})")

    print("\n3 · EL MOTOR DEL NAVEGADOR LA ARMA")
    with S.app.test_request_context("/", method="GET"):
        motor = S.app.test_client().get(f"/api/productos/{PID}/motor_b").get_json()
    fuentes = {os.path.basename(r): r for r in glob.glob(os.path.join(S.FUENTES, "*")) if r.lower().endswith((".ttf", ".otf"))}
    with S.app.test_request_context("/"):
        _icc, _n, _k = S._icc_para_salida([], S._cargar_catalogo(), forzado=None)
    perfil_path = None
    if _icc:
        perfil_path = os.path.join(_TMP, "perfil_corte.icc")
        open(perfil_path, "wb").write(_icc)
    entorno = {"plan": plan_nav, "cuerpo": cuerpo, "motor_b": {PID: motor}, "desplegado": {},
               "plantilla": {PID: pl}, "artes": {}, "objetos": {}, "fuentes": fuentes, "perfil": perfil_path}
    ep = os.path.join(_TMP, "entorno_corte.json")
    json.dump(entorno, open(ep, "w", encoding="utf-8"), ensure_ascii=False)
    salida = os.path.join(_TMP, "trabajos", "corte")
    t = time.time()
    r = subprocess.run(["node", "--max-old-space-size=8192", NODE, ep, salida], capture_output=True, text=True, encoding="utf-8", timeout=3600)
    ok(r.returncode == 0, f"el motor terminó en {time.time() - t:.1f} s" + ("" if r.returncode == 0 else f": {r.stderr[-1500:]}"))
    if r.returncode != 0:
        return
    nav = json.load(open(os.path.join(salida, "resultado.json"), encoding="utf-8"))["resultado"]
    ok(nav.get("corte") is True, "el resultado dice «corte» (la pantalla ofrece los formatos)")
    _rip = [f for h in ((nav.get("rip") or {}).get("hojas") or []) for f in (h.get("fallas") or [])]
    ok(not _rip, f"la revisión del RIP no avisa nada ({_rip})")
    hojas = nav.get("hojas") or []
    mesas = [(h, i) for h in hojas for i in range(h.get("paginas") or 1)]
    tm = [m for h in hojas for m in (h.get("mesas") or [])]
    ok(len(mesas) >= len(elegidos) and len(tm) == len(mesas) and all(len(m.get("talles") or []) == 1 for m in tm),
       f"{len(mesas)} mesa(s), cada una de UN talle: {[m.get('talles') for m in tm]}")
    ok(sorted({t for m in tm for t in (m.get("talles") or [])}) == sorted(elegidos), "están todos los talles del pedido")
    total = 0
    for h in hojas:
        d = fitz.open(os.path.join(salida, h["archivo"]))
        imgs = sum(len(pg.get_images()) for pg in d)
        ok(imgs == 0, f"{h['archivo']}: sin imágenes ({imgs})")
        d.close()
    total_piezas = int(nav.get("piezas") or 0)

    print("\n4 · CADA MESA EN LOS CINCO FORMATOS")
    import ezdxf
    from ezdxf import bbox as _bbox
    sal = os.path.join(_TMP, "exportes")
    os.makedirs(sal)
    pedidos = [{"pdf": os.path.join(salida, h["archivo"]), "pi": i, "base": os.path.join(sal, f"{h['archivo'][:-4]}_{i}")} for h, i in mesas]
    pj = os.path.join(_TMP, "exportar.json")
    json.dump(pedidos, open(pj, "w", encoding="utf-8"))
    r = subprocess.run(["node", EXPORTAR, pj], capture_output=True, text=True, encoding="utf-8", timeout=1800)
    ok(r.returncode == 0, "los cinco formatos de cada mesa" + ("" if r.returncode == 0 else f": {r.stderr[-1500:]}"))
    if r.returncode != 0:
        return
    info = json.loads(r.stdout.strip().splitlines()[-1])
    for p, inf in zip(pedidos, info):
        nom = os.path.basename(p["base"])
        doc = ezdxf.readfile(p["base"] + ".dxf")
        a = doc.audit()
        ok(doc.dxfversion == "AC1015" and not a.errors, f"{nom}.dxf: DXF 2000 sin errores para ezdxf ({len(a.errors)} errores, {len(a.fixes)} arreglos)")
        msp = doc.modelspace()
        cortes = list(msp.query('*[layer=="Corte"]'))
        etq = list(msp.query('*[layer=="Etiqueta"]'))
        total += len(cortes)
        ok(len(cortes) == inf["piezas"] and len(etq) == 0 and inf["letras"] == 0,
           f"{nom}.dxf: {len(cortes)} líneas de corte (una por pieza) y NINGUNA etiqueta (sólo el molde: {len(etq)} en el DXF, {inf['letras']} letras en la hoja)")
        bb = _bbox.extents(cortes)
        pg = fitz.open(p["pdf"])[p["pi"]]
        w_mm, h_mm = pg.rect.width * 25.4 / 72, pg.rect.height * 25.4 / 72
        ok(bb.extmin.x >= -0.01 and bb.extmin.y >= -0.01 and bb.extmax.x <= w_mm + 0.01 and bb.extmax.y <= h_mm + 0.01,
           f"{nom}.dxf: todo adentro de la mesa ({bb.extmax.x:.1f} × {bb.extmax.y:.1f} mm de {w_mm:.1f} × {h_mm:.1f} mm)")
        svg = open(p["base"] + ".svg", encoding="utf-8").read()
        ok('id="Corte"' in svg and 'id="Etiqueta"' not in svg and f'width="{w_mm:.4f}mm"' in svg, f"{nom}.svg: sólo la capa de corte, en mm")
        ai = open(p["base"] + ".ai", encoding="latin-1").read()
        ok(ai.startswith("%!PS-Adobe-2.0 EPSF-1.2\n%%Creator:Adobe Illustrator(TM) 3.2") and ai.count("\ns\n") + ai.count("\nS\n") == inf["piezas"],
           f"{nom}.ai: Illustrator 3 con {inf['piezas']} contornos de corte")
        eps = open(p["base"] + ".eps", encoding="latin-1").read()
        ok(eps.startswith("%!PS-Adobe-3.0 EPSF-3.0") and eps.count("stroke\n") == inf["piezas"], f"{nom}.eps: EPS con {inf['piezas']} contornos")
        plt = open(p["base"] + ".plt", encoding="latin-1").read()
        ok(plt.startswith("IN;") and "SP2" not in plt and plt.count("PD") == inf["piezas"], f"{nom}.plt: HPGL con {inf['piezas']} contornos, una sola pluma")
    ok(total == total_piezas, f"entre todas las mesas, una línea de corte por pieza de la tizada ({total} = {total_piezas})")


if __name__ == "__main__":
    if not os.path.exists(os.path.join(ORIGEN, "plantilla.ai")) or not os.path.exists(os.path.join(DATOS_ORIGEN, "piezas.json")):
        print("  (no está el molde real del camino A con su nombrado: se saltea)")
        sys.exit(0)
    try:
        main()
    finally:
        try:
            MP.cerrar_abiertos()
        except Exception:
            pass
        if os.environ.get("TIZADA_MANTENER_TMP"):
            print("    (temporal conservado: " + _TMP + ")")
        else:
            shutil.rmtree(_TMP, ignore_errors=True)
    print()
    if FALLOS:
        print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
        for f in FALLOS:
            print("   · " + f)
        sys.exit(1)
    print("✅ CONTRATO VERDE — la tizada para corte sale sin arte, un talle por mesa, y en los cinco formatos")
