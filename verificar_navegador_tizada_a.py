# -*- coding: utf-8 -*-
"""
CONTRATO: EL NAVEGADOR GENERA LA TIZADA DEL CAMINO A IGUAL QUE EL SERVIDOR — `py verificar_navegador_tizada_a.py`

PLAN_NAVEGADOR.md, pendiente 1b (el cierre del camino A). Un molde SIN diseño adentro (la plantilla
pelada, nombrada con el nombrado visual del usuario) con su ARTE SEPARADO (el diseño «jugador»,
con editables y nombre/número en curva), prendas de tres talles: el MISMO pedido se genera en el
servidor (`_plan_del_pedido` + `generar_pedido_grupos` + aplanado + perfil + ficha, como
`generar_multi`) y en el navegador (Node, `pruebas/tizada.mjs` → `pedido/generar.js` con la rama
del camino A: `molde_a_abrir` + `contexto_a` + `pieza_a`). Se exige lo mismo que en el camino B:
mismas hojas, mismo consumo, content-stream token por token, 0 píxeles distintos fuera de bordes,
misma ficha. Marcado CONTRATO_LENTO.

⚠️ No toca nada del usuario: todo se COPIA a un temporal y `db` es un doble.
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
import verificar_navegador_tizada as VT       # noqa: E402  (el entorno, los dobles y las comparaciones)

S, MP, fitz = VT.S, VT.MP, VT.fitz
ok, FALLOS, _TMP, NODE = VT.ok, VT.FALLOS, VT._TMP, VT.NODE
PID = "prod_tizada_a"
ORIGEN = os.path.join(AQUI, "entrada", "prod_20260820_095558_38bc")
DATOS_ORIGEN = os.path.join(AQUI, "datos", "productos", "prod_20260820_095558_38bc")
DISENO = "jugador"
# 🔴 UN SEGUNDO DISEÑO DEL MISMO MOLDE EN LA MISMA HOJA (reporte 2026-09-18: «en la tizada no mantiene
# el arte de cada molde; nombres y números sí»). La hoja compartía el dibujo del arte por «mesa N»
# sin mirar de qué arte era: las piezas del golero salían con el arte del jugador. Con los dos
# diseños acá, la comparación píxel a píxel contra el servidor lo agarra.
DISENO2 = "golero"


def main():
    print("\n1 · EL MOLDE SIN DISEÑO, SU ARTE Y EL PEDIDO")
    carpeta = os.path.join(_TMP, "entrada", PID)
    sub = S._diseno_sub(DISENO)
    os.makedirs(os.path.join(carpeta, sub))
    shutil.copy2(os.path.join(ORIGEN, "plantilla.ai"), os.path.join(carpeta, "plantilla.ai"))
    shutil.copy2(os.path.join(ORIGEN, "disenos", DISENO, "arte.ai"), os.path.join(carpeta, sub, "arte.ai"))
    pl = os.path.join(carpeta, "plantilla.ai")
    arte = os.path.join(carpeta, sub, "arte.ai")
    ddir = os.path.join(_TMP, "datos", "productos", PID)
    os.makedirs(os.path.join(ddir, sub), exist_ok=True)
    # el registro con el nombrado visual del usuario (piezas.json → talle guía M), como en pieza_a
    pz = json.load(open(os.path.join(DATOS_ORIGEN, "piezas.json"), encoding="utf-8"))
    emp = json.load(open(os.path.join(DATOS_ORIGEN, "emparejado_talles.json"), encoding="utf-8"))
    asign = [{"idx": int(p["ancla"]["idx"]), "nombre": p["clave"]} for p in pz["piezas"] if (p.get("ancla") or {}).get("talle") == "M"]
    alta = MP.alta_plantilla_manual(pl, asign, 1, "M", emparejado=emp)
    registro = alta["registro"]
    VT._REG[PID] = registro
    talles = sorted({t for v in registro.values() for t in v})
    mapeo = MP.mapeo_por_nombre(arte, registro)
    pers = MP.extraer_personalizacion(arte)
    json.dump({"mapeo": mapeo, "por_variable": {}}, open(os.path.join(ddir, sub, "mapeo_arte.json"), "w", encoding="utf-8"))
    json.dump(pers, open(os.path.join(ddir, sub, "registro_personalizacion.json"), "w", encoding="utf-8"))
    json.dump({"aprobado": True, "modo": "separado", "checks": [], "mapeo": mapeo, "personalizacion": pers},
              open(os.path.join(ddir, sub, "validacion_arte.json"), "w", encoding="utf-8"))
    sub2 = S._diseno_sub(DISENO2)
    os.makedirs(os.path.join(carpeta, sub2))
    arte2 = os.path.join(carpeta, sub2, "arte.ai")
    shutil.copy2(os.path.join(ORIGEN, "disenos", DISENO2, "arte.ai"), arte2)
    os.makedirs(os.path.join(ddir, sub2), exist_ok=True)
    mapeo2 = MP.mapeo_por_nombre(arte2, registro)
    pers2 = MP.extraer_personalizacion(arte2)
    json.dump({"mapeo": mapeo2, "por_variable": {}}, open(os.path.join(ddir, sub2, "mapeo_arte.json"), "w", encoding="utf-8"))
    json.dump(pers2, open(os.path.join(ddir, sub2, "registro_personalizacion.json"), "w", encoding="utf-8"))
    json.dump({"aprobado": True, "modo": "separado", "checks": [], "mapeo": mapeo2, "personalizacion": pers2},
              open(os.path.join(ddir, sub2, "validacion_arte.json"), "w", encoding="utf-8"))
    VT._DOCS["catalogo"] = {"activo": PID, "productos": [{
        "id": PID, "nombre": "Molde de prueba A", "planilla_template_id": "plan_default", "variante_guia": "M",
        "disenos": [{"id": DISENO, "nombre": "Jugador"}, {"id": DISENO2, "nombre": "Golero"}], "mapeo_arte": mapeo, "referencia_medida": "alto",
        "editables": {DISENO: {"*": {"escudo": {"transforms": {"M": {"dx": 0.06, "dy": -0.04, "rot": 12, "scale": 1.15}}}}}},
        "borde_corte": {"activo": True, "color": [0, 0, 0, 1], "mm": 2.0}}],
        "plantillas_planillas": [{"id": "plan_default", "nombre": "Estándar", "columnas": [
            {"id": "talle", "label": "Talle", "role": "talle"}, {"id": "nombre", "label": "Nombre", "role": "nombre"},
            {"id": "numero", "label": "Número", "role": "numero"}, {"id": "diseno", "label": "Diseño", "role": "diseno"}]}],
        "reglas_planilla": [], "telas": []}
    comunes = [t for t in ["S", "M", "L", "XL"] if t in talles] or talles[:3]
    elegidos = [comunes[0], comunes[len(comunes) // 2], comunes[-1]][:3]
    filas = [{"talle": t, "nombre": n, "numero": num, "diseno": "Jugador"} for t, (n, num) in zip(elegidos, [("PÉREZ", "10"), ("GÓMEZ", "7"), ("DÍAZ", "23")])]
    filas.append({"talle": elegidos[0], "nombre": "LÓPEZ", "numero": "1", "diseno": "Jugador"})
    # las del golero, en los mismos talles que el jugador: comparten mesas del molde y de nombre de arte
    filas.append({"talle": elegidos[1], "nombre": "NACHO", "numero": "12", "diseno": "Golero"})
    filas.append({"talle": elegidos[-1], "nombre": "RAMOS", "numero": "25", "diseno": "Golero"})
    cuerpo = {"molds": [PID], "prendas": filas, "default_diseno": DISENO,
              "moldes_por_diseno": {DISENO: [PID], DISENO2: [PID]},
              "planilla": {"columnas": [{"id": "talle", "label": "Talle"}, {"id": "nombre", "label": "Nombre"}, {"id": "numero", "label": "Número"},
                                        {"id": "diseno", "label": "Diseño"}],
                           "filas": filas}}
    ok(len(registro) >= 30 and len(mapeo) > 0, f"{len(registro)} piezas · mapeo por nombre de {len(mapeo)} · talles {elegidos} · {len(filas)} prendas")

    print("\n2 · EL SERVIDOR GENERA")
    with S.app.test_request_context("/api/pedido/plan", method="POST", json=cuerpo):
        plan = S._plan_del_pedido(cuerpo)
        plan_nav = S._plan_para_navegador(plan)
        cat = S._cargar_catalogo()
        _icc, _icc_nom, _icc_n = S._icc_para_salida([], cat, forzado=None)
    ok(plan_nav.get("todo_navegador") and not plan_nav.get("todo_camino_b"), "el plan dice que el navegador puede generarlo (camino A)")
    _dis_plan = sorted({str(md.get("diseno")) for md in plan_nav.get("moldes") or []})
    ok(_dis_plan == sorted([DISENO, DISENO2]), f"el pedido lleva los DOS diseños del mismo molde ({', '.join(_dis_plan)})")
    salida_py = os.path.join(_TMP, "trabajos", "py_a")
    os.makedirs(salida_py)
    t = time.time()
    res = MP.generar_pedido_grupos(plan["grupos"], S.FUENTES, salida_py, config_nesting=plan["cfg_nesting"],
                                   telas_cfg=plan["telas_cfg"], progreso=None, procesos=None)
    from aplanar_rip import aplanar_para_rip
    for h in res["hojas"]:
        aplanar_para_rip(os.path.join(salida_py, h["archivo"]))
        if _icc:
            S._embeber_perfil_pdf(os.path.join(salida_py, h["archivo"]), _icc, _icc_nom, _icc_n)
    t_py = time.time() - t
    ok(bool(res["hojas"]), f"{len(res['hojas'])} hoja(s) en {t_py:.1f} s: " + ", ".join(f"{h['archivo']} ({h['paginas']} pág, {h['consumo_cm']} cm)" for h in res["hojas"]))
    import ficha_tecnica as FT
    _guias = []
    for _sp in plan["_guias_ficha"]:
        with S.app.test_request_context("/", method="POST", json=cuerpo):
            g = S._molde_guia_ficha(PID, cat["productos"][0], registro, _sp.get("diseno") or "principal", _sp, reempl={})
        if g:
            _guias.append(g)
    FT.generar_ficha(salida_py, "Ficha técnica", "Molde de prueba A · " + time.strftime("%d/%m/%Y"), cuerpo["planilla"], _guias)
    ok(os.path.exists(os.path.join(salida_py, "FICHA_TECNICA.pdf")), f"ficha técnica del servidor ({len(_guias)} guía(s))")

    print("\n3 · EL NAVEGADOR GENERA LO MISMO")
    with S.app.test_request_context("/", method="GET"):
        motor = S.app.test_client().get(f"/api/productos/{PID}/motor_b").get_json()
    ok(motor.get("camino_a") and any(d["id"] == DISENO for d in motor.get("disenos") or []), "el motor del molde dice camino A y trae el diseño con su arte")
    fuentes = {}
    for ruta in glob.glob(os.path.join(S.FUENTES, "*")):
        if ruta.lower().endswith((".ttf", ".otf")):
            fuentes[os.path.basename(ruta)] = ruta
    perfil_path = None
    if _icc:
        perfil_path = os.path.join(_TMP, "perfil_a.icc")
        with open(perfil_path, "wb") as fh:
            fh.write(_icc)
    entorno = {"plan": plan_nav, "cuerpo": cuerpo, "motor_b": {PID: motor}, "desplegado": {},
               "plantilla": {PID: pl}, "artes": {f"{PID}|{DISENO}": arte, f"{PID}|{DISENO2}": arte2}, "objetos": {},
               "fuentes": fuentes, "perfil": perfil_path}
    ep = os.path.join(_TMP, "entorno_a.json")
    with open(ep, "w", encoding="utf-8") as fh:
        json.dump(entorno, fh, ensure_ascii=False)
    salida_js = os.path.join(_TMP, "trabajos", "nav_a")
    t = time.time()
    r = subprocess.run(["node", "--max-old-space-size=8192", NODE, ep, salida_js], capture_output=True, text=True, encoding="utf-8", timeout=3600)
    ok(r.returncode == 0, f"el motor del navegador terminó en {time.time() - t:.1f} s" + ("" if r.returncode == 0 else f": {r.stderr[-1500:]}"))
    if r.returncode != 0:
        return
    nav = json.load(open(os.path.join(salida_js, "resultado.json"), encoding="utf-8"))["resultado"]
    tiempos = json.load(open(os.path.join(salida_js, "tiempos.json"), encoding="utf-8"))
    print("    etapas: " + " · ".join(f"{s} s {t}" for s, t in tiempos["etapas"]))
    ok(len(nav["hojas"]) == len(res["hojas"]), f"las mismas hojas ({len(nav['hojas'])})")
    for hp, hn in zip(res["hojas"], nav["hojas"]):
        ok(hp["archivo"] == hn["archivo"] and hp["paginas"] == hn["paginas"] and hp["consumo_cm"] == hn["consumo_cm"]
           and hp["alturas_cm"] == hn["alturas_cm"] and hp["aprovechamiento"] == hn["aprovechamiento"],
           f"{hp['archivo']}: mismo nombre, páginas ({hp['paginas']}={hn['paginas']}), consumo ({hp['consumo_cm']}={hn['consumo_cm']}), alturas y aprovechamiento ({hp['aprovechamiento']}={hn['aprovechamiento']})")
        VT.comparar_hoja(os.path.join(salida_py, hp["archivo"]), os.path.join(salida_js, hn["archivo"]), hp["archivo"])
    ok(nav.get("validaciones") == res["validaciones"],
       f"las validaciones de la hoja dan igual en el navegador: {nav.get('validaciones')} vs servidor {res['validaciones']}")

    print("\n4 · LA FICHA TÉCNICA")
    fp, fn = os.path.join(salida_py, "FICHA_TECNICA.pdf"), os.path.join(salida_js, "FICHA_TECNICA.pdf")
    ok(os.path.exists(fn), "el navegador armó la ficha")
    if os.path.exists(fn):
        da, dbb = fitz.open(fp), fitz.open(fn)
        ok(da.page_count == dbb.page_count, f"mismas páginas ({da.page_count} = {dbb.page_count})")
        for i in range(min(da.page_count, dbb.page_count)):
            ta, tb = da[i].get_text(), dbb[i].get_text()
            ok(ta == tb, f"ficha pág {i + 1}: el mismo texto" if ta == tb else f"ficha pág {i + 1}: texto distinto: {next(((x, y) for x, y in zip(ta.splitlines(), tb.splitlines()) if x != y), '?')!r}")
            z = 100 / 72
            xa = da[i].get_pixmap(matrix=fitz.Matrix(z, z), alpha=False, colorspace=fitz.csRGB)
            xb = dbb[i].get_pixmap(matrix=fitz.Matrix(z, z), alpha=False, colorspace=fitz.csRGB)
            if (xa.width, xa.height) == (xb.width, xb.height):
                distintos, fuera = VT._distintos(xa.samples, xb.samples, xa.width, xa.height)
                ok(fuera == 0, f"ficha pág {i + 1}: dibujo a 100 dpi: {fuera} píxeles distintos que no son borde ({distintos} en total)")
            else:
                ok(False, f"ficha pág {i + 1}: dibujo de distinto tamaño")
    print(f"\n    tiempos: servidor {t_py:.1f} s · navegador {tiempos['segundos']:.1f} s (Node, un hilo)")


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
    print("✅ CONTRATO VERDE — el navegador genera la tizada del camino A igual que el servidor")
