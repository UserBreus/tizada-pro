# -*- coding: utf-8 -*-
"""CONTRATO: CAMBIAR LA FORMA DE UNA PIEZA Y MOVERLA, SIN TOCAR NADA MÁS — `py verificar_editar_piezas.py`

MAPA 746. Pedido del usuario (2026-10-23): «elegir piezas y actualizarlas: cargar un archivo nuevo a un
molde, reubicar las piezas donde quiera y reemplazarlas». Decidió: se cambia la FORMA conservando todo
(nombre, variables, telas, etiqueta, arte); la forma viene de un archivo; la posición queda GUARDADA; en
todos los talles o en los que elija.

Lo que se prueba, sobre una COPIA de un molde real (el `db` es un doble: nada de MSSQL ni de `datos/`):
  1. MOVER una pieza en todos los talles: queda corrida lo pedido, ninguna otra cambia de número ni de
     lugar, el registro corre su caja y el ancla de su texto, y el archivo del usuario no se toca
     (se escribe `plantilla.v1.ai`).
  2. REEMPLAZAR la forma en DOS talles con un archivo que trae una forma por talle: cambia el tamaño en
     el registro de esos talles y en ninguno más; mismo número, mismo nombre.
  3. Lo que se rechaza: dos cambios a la misma pieza (409) y un archivo con menos formas que talles (422).
  4. PARIDAD: el motor del navegador (`editarPiezas.js`, Node) con las MISMAS ediciones deja las piezas
     exactamente donde las deja el gemelo de Python.
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys

os.environ["TIZADA_SOLO_NAVEGADOR"] = "0"          # el gemelo de Python (el del navegador va por Node, punto 4)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import verificar_navegador_tizada as VT           # noqa: E402  (entorno aislado + doble de la base)

S, MP, ok, FALLOS, _DOCS, _REG = VT.S, VT.MP, VT.ok, VT.FALLOS, VT._DOCS, VT._REG
import piezas_molde as PM                         # noqa: E402

ORIGEN = os.path.join(AQUI, "entrada", "prod_20260916_095236_ef99", "plantilla.ai")
PID = "prod_editar_piezas"
NODE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "editar_piezas.mjs")


def _sha(p):
    return hashlib.sha1(open(p, "rb").read()).hexdigest()


def _archivo_formas(destino, n, w0=10.0, h0=20.0):
    """Un PDF con `n` rectángulos de tamaño creciente (una forma por talle, del más chico al más grande)."""
    import pymupdf as fitz
    doc = fitz.open()
    pg = doc.new_page(width=2000, height=2000)
    for k in range(n):
        w, h = (w0 + k) * MP.CM, (h0 + k) * MP.CM
        x = 20 + k * 40
        pg.draw_rect(fitz.Rect(x, 20, x + w, 20 + h), color=(0, 0, 0), width=1)
    doc.save(destino)
    doc.close()


def main():
    print("CONTRATO — CAMBIAR LA FORMA Y MOVER PIEZAS SIN TOCAR NADA MÁS\n")
    if not os.path.exists(ORIGEN):
        print("    (no está el molde de referencia: no se puede correr)")
        return 0
    os.makedirs(os.path.join(S.ENTRADA, PID), exist_ok=True)
    base = os.path.join(S.ENTRADA, PID, "plantilla.ai")
    shutil.copy(ORIGEN, base)
    sha0 = _sha(base)
    doc = MP._abrir(base)
    try:
        talles = MP._talles_de_plantilla(doc)
    finally:
        doc.close()
    antes = PM.detectar_por_talle(base, 1, talles)
    guia = talles[0]
    # registro mínimo: dos piezas con nombre, con su caja y el ancla de su texto (como el del alta)
    reg = {}
    for nom, j in (("Pieza A", 2), ("Pieza B", 4)):
        reg[nom] = {t: {"mesa": 1, "pieza_idx": j, "w_cm": round(antes[t][j]["w"] / MP.CM, 1),
                        "h_cm": round(antes[t][j]["h"] / MP.CM, 1), "bbox_mu": antes[t][j]["bbox_mu"],
                        "ancla": {"x": 100.0, "y": 200.0, "angulo": 0.0, "size_pt": 8.0, "fuente": "Arial"}}
                    for t in talles}
    _REG[PID] = reg
    _DOCS["catalogo"] = {"activo": PID, "productos": [{"id": PID, "nombre": "Molde de prueba", "variante_guia": guia}]}
    cli = S.app.test_client()
    capturadas = []
    _orig_editar = PM.editar_piezas
    PM.editar_piezas = lambda pl, ed, mesa=1, destino=None: (capturadas.append(ed), _orig_editar(pl, ed, mesa=mesa, destino=destino))[1]

    print("1 · MOVER UNA PIEZA EN TODOS LOS TALLES")
    r = cli.post("/api/plantilla/piezas_cambiar", json={"pid": PID, "cambios": [{"tipo": "mover", "pieza_idx": 2, "dx": 50, "dy": 30}]})
    d = r.get_json() or {}
    ok(r.status_code == 200, f"guardado ({r.status_code} {d.get('error', '')})")
    ok(_sha(base) == sha0, "el archivo del usuario no se tocó")
    v1 = os.path.join(S.ENTRADA, PID, "plantilla.v1.ai")
    ok(os.path.exists(v1), "se escribió una versión nueva (plantilla.v1.ai)")
    desp = PM.detectar_por_talle(v1, 1, talles)
    dx, dy = 50 * MP.CM / 10, -30 * MP.CM / 10
    corridas = all(abs(desp[t][2]["bbox_raw"][0] - (antes[t][2]["bbox_raw"][0] + dx)) < 1
                   and abs(desp[t][2]["bbox_raw"][1] - (antes[t][2]["bbox_raw"][1] + dy)) < 1 for t in talles)
    ok(corridas, "la pieza 3 quedó corrida 50 mm a la derecha y 30 mm abajo, en todos los talles")
    quietas = all(len(desp[t]) == len(antes[t]) and all(
        all(abs(a - b) < 0.6 for a, b in zip(desp[t][i]["bbox_raw"], antes[t][i]["bbox_raw"]))
        for i in range(len(antes[t])) if i != 2) for t in talles)
    ok(quietas, f"ninguna otra pieza cambió de número ni de lugar ({sum(len(v) for v in antes.values())} piezas)")
    ra = _REG[PID]["Pieza A"][guia]
    ok(abs(ra["bbox_mu"][0] - (antes[guia][2]["bbox_mu"][0] + 50 * MP.CM / 10 * (antes[guia][2]["bbox_mu"][2] - antes[guia][2]["bbox_mu"][0]) / (antes[guia][2]["bbox_raw"][2] - antes[guia][2]["bbox_raw"][0]))) < 1,
       "el registro corrió su caja")
    ok(ra["ancla"]["x"] > 100.0 and ra["ancla"]["y"] > 200.0 and ra["pieza_idx"] == 2, "y el ancla de su texto; mismo número")

    print("\n2 · REEMPLAZAR LA FORMA EN DOS TALLES")
    arch = os.path.join(S.ENTRADA, PID, "forma_nueva.pdf")
    _archivo_formas(arch, 2)
    with open(arch, "rb") as fh:
        r = cli.post("/api/plantilla/pieza_archivo", data={"pid": PID, "archivo": (io.BytesIO(fh.read()), "forma.pdf")},
                     content_type="multipart/form-data")
    up = r.get_json() or {}
    ok(r.status_code == 200 and up.get("archivo"), f"archivo subido ({r.status_code} {up.get('error', '')})")
    dos = talles[:2]
    r = cli.post("/api/plantilla/piezas_cambiar", json={"pid": PID, "cambios": [
        {"tipo": "reemplazar", "pieza_idx": 4, "talles": dos, "archivo": up.get("archivo"), "dx": 0, "dy": 0}]})
    d = r.get_json() or {}
    ok(r.status_code == 200, f"guardado ({r.status_code} {d.get('error', '')})")
    rb = _REG[PID]["Pieza B"]
    ok(abs(rb[dos[0]]["w_cm"] - 10.0) < 0.3 and abs(rb[dos[1]]["w_cm"] - 11.0) < 0.3,
       f"los dos talles tienen la forma nueva ({rb[dos[0]]['w_cm']} y {rb[dos[1]]['w_cm']} cm de ancho)")
    otros = [t for t in talles if t not in dos]
    ok(all(rb[t]["w_cm"] == round(antes[t][4]["w"] / MP.CM, 1) for t in otros), "los demás talles quedaron como estaban")
    ok(all(rb[t]["pieza_idx"] == 4 for t in talles), "misma pieza: mismo número y mismo nombre en todos")
    v2 = os.path.join(S.ENTRADA, PID, "plantilla.v2.ai")
    desp2 = PM.detectar_por_talle(v2, 1, talles)
    ok(all(len(desp2[t]) == len(antes[t]) for t in talles), "ningún talle ganó ni perdió piezas")

    print("\n2b · AGREGAR UNA FORMA NUEVA EN DOS TALLES (y en ninguno más)")
    n_antes = {t: len(desp2[t]) for t in talles}
    reg_antes = json.dumps(_REG[PID], sort_keys=True)
    r = cli.post("/api/plantilla/piezas_cambiar", json={"pid": PID, "cambios": [
        {"tipo": "agregar", "archivo": up.get("archivo"), "talles": dos,
         "por_talle": {t: {"ref": 0, "dx": 300, "dy": 0} for t in dos}}]})
    d = r.get_json() or {}
    ok(r.status_code == 200 and d.get("nuevas") == 2, f"guardado ({r.status_code} {d.get('error', '')})")
    v3 = os.path.join(S.ENTRADA, PID, "plantilla.v3.ai")
    desp3 = PM.detectar_por_talle(v3, 1, talles) if os.path.exists(v3) else {t: [] for t in talles}
    ok(all(len(desp3[t]) == n_antes[t] + 1 for t in dos) and all(len(desp3[t]) == n_antes[t] for t in talles if t not in dos),
       "una pieza más en cada talle elegido; los demás talles, igual")
    ok(all(desp3[dos[k]] and abs((desp3[dos[k]][-1]["w"] / MP.CM) - (10.0 + k)) < 0.3 for k in range(2)),
       "cada talle recibió SU forma (la chica en el primero, la grande en el segundo)")
    ok(all(len(desp3[t]) >= len(desp2[t]) and all(all(abs(a - b) < 0.6 for a, b in zip(desp3[t][i]["bbox_raw"], desp2[t][i]["bbox_raw"]))
           for i in range(len(desp2[t]))) for t in talles), "ninguna pieza que ya estaba cambió de número ni de lugar")
    ok(json.dumps(_REG[PID], sort_keys=True) == reg_antes, "el registro no cambió: la forma nueva entra sin nombre")
    import pikepdf as _pk

    def _capas(p):
        with _pk.open(p) as _pdf:
            return [str(o.get("/Name")) for o in _pdf.Root.OCProperties.OCGs]
    ok(os.path.exists(v3) and _capas(v3) == _capas(base), "las capas del archivo quedaron iguales (mismas y en el mismo orden)")

    print("\n3 · LO QUE SE RECHAZA")
    r = cli.post("/api/plantilla/piezas_cambiar", json={"pid": PID, "cambios": [
        {"tipo": "mover", "pieza_idx": 1, "dx": 10}, {"tipo": "mover", "pieza_idx": 1, "dx": 20}]})
    ok(r.status_code == 409, f"dos cambios a la misma pieza → 409 ({r.status_code})")
    r = cli.post("/api/plantilla/piezas_cambiar", json={"pid": PID, "cambios": [
        {"tipo": "reemplazar", "pieza_idx": 4, "archivo": up.get("archivo")}]})
    ok(r.status_code == 422, f"menos formas que talles → 422 ({r.status_code})")

    print("\n4 · PARIDAD CON EL MOTOR DEL NAVEGADOR")
    PM.editar_piezas = _orig_editar
    ed = capturadas[0] if capturadas else []
    tmpj = os.path.join(VT._TMP, "ed.json")
    esperado = []
    json.dump({"ediciones": ed, "esperado": esperado, "mesa": 1}, open(tmpj, "w"))
    sal, res = os.path.join(VT._TMP, "js.ai"), os.path.join(VT._TMP, "js.json")
    p = subprocess.run(["node", NODE, base, tmpj, sal, res], capture_output=True, text=True, encoding="utf-8")
    js = json.load(open(res)) if os.path.exists(res) else {}
    dif = None
    if js.get("despues"):
        dif = sum(1 for t in talles for i, c in enumerate(desp[t])
                  if any(abs(a - b) > 0.05 for a, b in zip(c["bbox_raw"], js["despues"][t][i])))
    ok(dif == 0, f"mover: el navegador deja cada pieza donde la deja Python (distintas: {dif}; {(p.stderr or '')[:200]})")

    print()
    if FALLOS:
        print(f"❌ CONTRATO ROJO — {len(FALLOS)} falla(s)")
        return 1
    print("✅ CONTRATO VERDE — se cambia la forma y se mueve una pieza sin tocar nada más")
    return 0


if __name__ == "__main__":
    sys.exit(main())
