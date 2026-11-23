# -*- coding: utf-8 -*-
"""
CONTRATO: EL ARTE DEL PEDIDO VIVE EN LA PC Y NO SE CRUZA ENTRE PERSONAS — `py verificar_arte_en_pc.py`

MAPA 758 (el bug: «a dos personas se les cruzaron los artes») → 760-761 (PLAN_ARTE_EN_LA_PC.md). El arte de un
pedido se guardaba en el servidor en una carpeta por molde + NOMBRE del diseño, la misma para todas las personas.
Ahora queda en la computadora de quien lo carga (`frontend/src/motor/arte/enPc.js`, IndexedDB por pedido) y el
plan recibe lo que calculó esa computadora (`artes_pc`).

Se arma un molde de prueba (la plantilla del molde de la camiseta, copiada) con OTRO arte de «jugador» en la carpeta
del servidor — el de la otra persona — y dos pedidos A y B con artes distintos. `pruebas/arte_en_pc.mjs` (Node, con
`enPc.js` tal cual y dobles de IndexedDB y del hilo) pide al servidor aislado lo mismo que la pantalla y exige que
cada pedido lea SU arte en el motor, la detección, los objetos agregados, la versión nueva y el plan; que el servidor
responda sin abrir su carpeta (`/api/arte/perfil?det=`, `/api/arte/deteccion?solo_molde=1`, `/api/arte/mapeo_fijo`);
y que «Nuevo pedido» suelte sólo lo del otro pedido.

⚠️ No toca nada del usuario: todo se COPIA a un temporal, `db` es un doble y el servidor corre en un puerto propio.
"""
import json
import os
import shutil
import subprocess
import sys
import threading

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import verificar_navegador_tizada as VT       # noqa: E402  (el entorno aislado: temporal + doble de `db`)

S, MP = VT.S, VT.MP
ok, FALLOS, _TMP = VT.ok, VT.FALLOS, VT._TMP
PID = "prod_arte_pc"
ORIGEN = os.path.join(AQUI, "entrada", "prod_20260820_095558_38bc")
DATOS_ORIGEN = os.path.join(AQUI, "datos", "productos", "prod_20260820_095558_38bc")
NODE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "arte_en_pc.mjs")
ARTE_A = os.path.join(ORIGEN, "disenos", "jugador", "arte.ai")
ARTE_B = os.path.join(ORIGEN, "disenos", "golero", "arte.ai")


def main():
    print("\n1 · EL MOLDE, CON EL ARTE DE «OTRA PERSONA» EN LA CARPETA DEL SERVIDOR")
    for r in (ARTE_A, ARTE_B, os.path.join(ORIGEN, "plantilla.ai")):
        if not os.path.exists(r):
            ok(False, f"falta el archivo de prueba {r}")
            return
    carpeta = os.path.join(_TMP, "entrada", PID)
    sub = S._diseno_sub("jugador")
    os.makedirs(os.path.join(carpeta, sub))
    shutil.copy2(os.path.join(ORIGEN, "plantilla.ai"), os.path.join(carpeta, "plantilla.ai"))
    shutil.copy2(ARTE_B, os.path.join(carpeta, sub, "arte.ai"))          # el de B: el caso del cruce (MAPA 758)
    pl = os.path.join(carpeta, "plantilla.ai")
    pz = json.load(open(os.path.join(DATOS_ORIGEN, "piezas.json"), encoding="utf-8"))
    emp = json.load(open(os.path.join(DATOS_ORIGEN, "emparejado_talles.json"), encoding="utf-8"))
    asign = [{"idx": int(p["ancla"]["idx"]), "nombre": p["clave"]} for p in pz["piezas"] if (p.get("ancla") or {}).get("talle") == "M"]
    registro = MP.alta_plantilla_manual(pl, asign, 1, "M", emparejado=emp)["registro"]
    VT._REG[PID] = registro
    ddir = os.path.join(_TMP, "datos", "productos", PID, sub)
    os.makedirs(ddir, exist_ok=True)
    arte_srv = os.path.join(carpeta, sub, "arte.ai")
    mapeo = MP.mapeo_por_nombre(arte_srv, registro)
    pers = MP.extraer_personalizacion(arte_srv)
    json.dump({"mapeo": mapeo, "por_variable": {}}, open(os.path.join(ddir, "mapeo_arte.json"), "w", encoding="utf-8"))
    json.dump(pers, open(os.path.join(ddir, "registro_personalizacion.json"), "w", encoding="utf-8"))
    json.dump({"aprobado": True, "modo": "separado", "checks": [], "mapeo": mapeo, "personalizacion": pers},
              open(os.path.join(ddir, "validacion_arte.json"), "w", encoding="utf-8"))
    VT._DOCS["catalogo"] = {"activo": PID, "productos": [{
        "id": PID, "nombre": "Molde de prueba (arte en la PC)", "planilla_template_id": "plan_default", "variante_guia": "M",
        "disenos": [{"id": "jugador", "nombre": "JUGADOR"}], "mapeo_arte": {}, "referencia_medida": "alto"}],
        "plantillas_planillas": [{"id": "plan_default", "nombre": "Estándar", "columnas": [
            {"id": "talle", "label": "Talle", "role": "talle"}, {"id": "nombre", "label": "Nombre", "role": "nombre"},
            {"id": "numero", "label": "Número", "role": "numero"}, {"id": "diseno", "label": "Diseño", "role": "diseno"}]}],
        "reglas_planilla": [], "telas": []}
    # + un pedido del OTRO SISTEMA con el mismo nombre de diseño («JUGADOR», carpeta `x-…`, MAPA 606): es de ese
    # pedido; ninguna persona lo puede usar ni recibir (MAPA 773)
    sub_x = S._diseno_sub("x-prueba-jugador")
    os.makedirs(os.path.join(carpeta, sub_x))
    shutil.copy2(ARTE_B, os.path.join(carpeta, sub_x, "arte.ai"))
    dx = os.path.join(_TMP, "datos", "productos", PID, sub_x)
    os.makedirs(dx, exist_ok=True)
    for _n in ("mapeo_arte.json", "registro_personalizacion.json", "validacion_arte.json"):
        shutil.copy2(os.path.join(ddir, _n), os.path.join(dx, _n))
    VT._DOCS["catalogo"]["productos"][0]["disenos"].append({"id": "x-prueba-jugador", "nombre": "JUGADOR", "externo": "prueba"})
    ok(len(registro) > 10, f"molde con {len(registro)} piezas; en la carpeta del servidor, el arte de B (y un `x-…` del otro sistema)")

    print("\n2 · DOS PEDIDOS EN LA PC (Node, `enPc.js` tal cual) CONTRA EL SERVIDOR AISLADO")
    from werkzeug.serving import make_server
    srv = make_server("127.0.0.1", 0, S.app, threaded=True)
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    try:
        base = f"http://127.0.0.1:{srv.server_port}"
        r = subprocess.run(["node", "--max-old-space-size=4096", NODE, base, PID, ARTE_A, ARTE_B],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
                           cwd=os.path.join(AQUI, "frontend"))
        for linea in (r.stdout or "").splitlines():
            if linea.startswith("  ✓ ") or linea.startswith("  ✗ ") or linea.startswith("pedido "):
                print(linea)
        if r.returncode != 0:
            print((r.stderr or "")[-2000:])
        ok(r.returncode == 0, "el pedido A lee SU arte y el B el suyo, en todo (ver arriba)")
    finally:
        srv.shutdown()


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
    if FALLOS:
        print(f"\n❌ CONTRATO ROJO — {len(FALLOS)} falla(s)")
        sys.exit(1)
    print("\n✅ CONTRATO VERDE — el arte de cada pedido queda en su computadora y no se cruza")
