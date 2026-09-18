# -*- coding: utf-8 -*-
"""
CONTRATO: EL NAVEGADOR LEE EL ARTE SEPARADO IGUAL QUE EL SERVIDOR — `py verificar_navegador_arte.py [arte.ai ...]`

PLAN_NAVEGADOR.md, etapa 3, camino A (el arte SEPARADO, una mesa de diseño por pieza).
`frontend/src/motor/arte/{texto,personalizacion,editables,mapeo,preparar}.js` traducen lo que
`motor_pedido` lee de un arte con PyMuPDF/pikepdf. Acá se corren las dos cosas sobre los MISMOS
archivos y se exige que den lo mismo, valor por valor (floats iguales, textos iguales):
  1. `extraer_personalizacion` (cx, baseline_y, size, fuente, ancho, color, colorn, trazo,
     pasadas, baseline_pts);
  2. `_extraer_editables_crudo(con_thumb=False)` (bbox_mu, mesa_rect, w_cm/h_cm y cada objeto con
     su `obj_id` = sha1(repr(firma)));
  3. `mapeo_por_nombre`, `mapeo_variantes_arte`, `fuentes_requeridas_arte`, `arte_es_separado`;
  4. `detectar_arte` (todo menos los bytes del PNG: se compara el tamaño en píxeles);
  5. `validar_arte_separado` (con el mapeo por nombre) y `validar_arte` (el modo clásico), con el
     catálogo de `catalogo_fuentes/`;
  6. el paquete de `prepararArte` (el ZIP que recibe `POST /api/arte`): nombres, sha1, modo y
     cada JSON contra lo que el servidor habría calculado con la regla de `_subir_arte_analizar`.

Tolerancias, todas por NO-DETERMINISMO de Python (no del navegador), y sólo cuando aparecen:
  · `detectar_arte.sugerencia`: `min(libres, key=_dist)` desempata por el orden de un `set`
    (cambia entre corridas: medido el 2026-09-18 con el arte «csac», `PYTHONHASHSEED=0..2` da
    «Manga larga derecha 2» en la mesa 5 y `=3` da «Manga larga izquierda 1» — misma distancia
    0,2277). Si difieren, se acepta cuando las dos piezas están a la MISMA distancia de la mesa.
  · `_capas_mesa` devuelve `list(set(...))` y las tintas salen de un `set`: el navegador usa el
    orden de aparición. Sólo cambiaría algo si dos capas nombraran piezas distintas (no pasa).

Sin argumentos usa los artes de `entrada/*/disenos/*/arte.ai` cuyo molde tenga
`datos/productos/<pid>/resumen_plantilla.json`. El REGISTRO del molde se arma desde ese resumen
(`piezas_detalle` → {pieza: {talle: {w_cm, h_cm, mesa}}}; en producción sale de `db.leer_registro`
y acá no hay base) y el orden de variantes es `resumen["talles"]` (orden de archivo).

⚠️ No toca nada del usuario: artes y plantilla se COPIAN a un temporal, `db` es un doble (nada
de MSSQL) y la personalización se lee con `_extraer_personalizacion_crudo` (sin memo en disco).
"""
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"
_falso = types.ModuleType("db")
_falso.__getattr__ = lambda n: (lambda *a, **k: None)
_falso.get_doc = lambda c, default=None: default
_falso.leer_registro = lambda pid: None
sys.modules["db"] = _falso

import motor_pedido as MP                      # noqa: E402

NODE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "arte.mjs")
FUENTES = os.environ.get("TIZADA_FUENTES") or os.path.join(AQUI, "catalogo_fuentes")


def _json(v):
    """Tuplas → listas, sets → listas ordenadas: lo mismo que se compara del lado de Node."""
    return json.loads(json.dumps(v, ensure_ascii=False, default=lambda o: sorted(o) if isinstance(o, set) else str(o)))


def _primera_diferencia(a, b, ruta=""):
    """La primera ruta donde `a` (servidor) y `b` (navegador) difieren; None si son iguales.
    Los números se comparan por valor exacto (816 == 816.0)."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if k not in b:
                return f"{ruta}/{k}: falta en el navegador"
            d = _primera_diferencia(a[k], b[k], f"{ruta}/{k}")
            if d:
                return d
        for k in b:
            if k not in a:
                return f"{ruta}/{k}: sobra en el navegador ({str(b[k])[:80]})"
        return None
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return f"{ruta}: {len(a)} ítems en el servidor, {len(b)} en el navegador"
        for i, (x, y) in enumerate(zip(a, b)):
            d = _primera_diferencia(x, y, f"{ruta}[{i}]")
            if d:
                return d
        return None
    if isinstance(a, bool) or isinstance(b, bool):
        return None if a == b else f"{ruta}: servidor {a!r} · navegador {b!r}"
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return None if a == b else f"{ruta}: servidor {a!r} · navegador {b!r}"
    if a == b:
        return None
    return f"{ruta}: servidor {str(a)[:120]!r} · navegador {str(b)[:120]!r}"


def _registro_desde_resumen(pid):
    ruta = os.path.join(AQUI, "datos", "productos", pid, "resumen_plantilla.json")
    if not os.path.exists(ruta):
        return None, None
    res = json.load(open(ruta, encoding="utf-8"))
    reg = {}
    for clave, d in (res.get("piezas_detalle") or {}).items():
        t = (d.get("talles") or ["ref"])[0]
        tm = d.get("talle_mayor_cm") or {}
        reg[clave] = {t: {"mesa": (d.get("mesas") or [1])[0], "pieza_idx": 0,
                          "w_cm": float(tm.get("w") or 0), "h_cm": float(tm.get("h") or 0)}}
    return reg, list(res.get("talles") or [])


def _catalogo():
    return [{**info, "ruta": ruta} for ruta, info in MP.catalogo_fuentes(FUENTES).items()]


def _sin_thumb(det):
    det = json.loads(json.dumps(det, ensure_ascii=False))
    for m in det.get("mesas") or []:
        m.pop("thumb", None)
    return det


def _sugerencias_equivalentes(det_py, det_js, reg):
    """La tolerancia del desempate de `min(libres, key=_dist)` (ver docstring)."""
    tam = {}
    for p in reg:
        v = max(reg[p].values(), key=lambda d: d["h_cm"])
        tam[p] = (float(v["w_cm"]), float(v["h_cm"]))
    for mp, mj in zip(det_py["mesas"], det_js["mesas"]):
        a, b = mp.get("sugerencia") or "", mj.get("sugerencia") or ""
        if a == b:
            continue
        if not a or not b or a not in tam or b not in tam:
            return False, f"mesa {mp['mesa']}: servidor {a!r} · navegador {b!r}"
        def _dist(p):
            pw, ph = tam[p]
            return abs(mp["w_cm"] - pw) / max(pw, 1) + abs(mp["h_cm"] - ph) / max(ph, 1)
        if _dist(a) != _dist(b):
            return False, f"mesa {mp['mesa']}: servidor {a!r} (dist {_dist(a):.4f}) · navegador {b!r} (dist {_dist(b):.4f})"
    return True, ""


def comparar(arte_orig, plantilla_orig, reg, orden, carpeta):
    arte = os.path.join(carpeta, "arte.ai")
    plantilla = os.path.join(carpeta, "plantilla.ai")
    shutil.copy(arte_orig, arte)
    if not os.path.exists(plantilla):
        shutil.copy(plantilla_orig, plantilla)
    cat = _catalogo()
    lineas, fallas = [], []

    # ── servidor ──
    t = time.time()
    py = {}
    py["personalizacion"] = MP._extraer_personalizacion_crudo(arte)
    py["editables"] = MP._extraer_editables_crudo(arte, con_thumb=False)
    py["mapeo_por_nombre"] = MP.mapeo_por_nombre(arte, reg)
    py["mapeo_variantes"] = MP.mapeo_variantes_arte(arte, reg, orden)
    py["fuentes_requeridas"] = MP.fuentes_requeridas_arte(arte)
    py["detectar"] = MP.detectar_arte(arte, reg)
    py["es_separado"] = MP.arte_es_separado(arte, plantilla)
    py["validar_separado"] = MP.validar_arte_separado(arte, reg, FUENTES, py["mapeo_por_nombre"], orden)
    py["validar_clasico"] = MP.validar_arte(arte, plantilla, FUENTES)
    # lo que `_subir_arte_analizar` haría con este arte (mapeo fijo vacío, alcance = el molde entero)
    alcance = set(reg.keys())
    mapeo_final = dict(py["mapeo_por_nombre"])
    if alcance <= set(mapeo_final):
        py["paquete_validacion"] = MP.validar_arte_separado(arte, reg, FUENTES, mapeo_final, orden, piezas_scope=alcance)
    else:
        faltan = sorted(alcance - set(mapeo_final))
        py["paquete_validacion"] = {"aprobado": False, "modo": "separado",
                                   "checks": [{"nombre": "Mapeo de arte a piezas", "ok": False,
                                               "detalle": "faltan asignar (sin nombre en la guía): " + ", ".join(faltan)}],
                                   "personalizacion": {}, "faltan": faltan}
    t_py = time.time() - t
    MP.cerrar_abiertos()

    # ── navegador ──
    fixture = {"registro": reg, "variantes_orden": orden, "catalogo": cat, "alias": {}, "plantilla": plantilla,
               "mapeo": py["mapeo_por_nombre"], "fijo": {}, "alcance": sorted(alcance), "variantes": {}}
    ruta_fx = os.path.join(carpeta, "fixture.json")
    json.dump(fixture, open(ruta_fx, "w", encoding="utf-8"), ensure_ascii=False)
    salida = os.path.join(carpeta, "nav.json")
    r = subprocess.run(["node", "--max-old-space-size=8192", NODE, arte, ruta_fx, salida],
                       capture_output=True, text=True, timeout=3600, cwd=os.path.join(AQUI, "frontend"))
    if r.returncode != 0:
        return False, f"  Node falló: {r.stderr[-1200:]}", t_py, 0.0
    nav = json.load(open(salida, encoding="utf-8"))

    def check(nombre, a, b):
        d = _primera_diferencia(_json(a), b)
        if d:
            fallas.append(nombre)
            lineas.append(f"  ✗ {nombre}: {d}")
        else:
            lineas.append(f"  ✓ {nombre}")

    check("personalizacion", py["personalizacion"], nav["personalizacion"])
    check("editables", py["editables"], nav["editables"])
    check("mapeo_por_nombre", py["mapeo_por_nombre"], nav["mapeo_por_nombre"])
    check("mapeo_variantes", py["mapeo_variantes"], nav["mapeo_variantes"])
    check("fuentes_requeridas", py["fuentes_requeridas"], nav["fuentes_requeridas"])
    check("es_separado", py["es_separado"], nav["es_separado"])
    # detectar: sin los bytes del PNG; la sugerencia con la tolerancia del desempate
    dp, dj = _sin_thumb(py["detectar"]), _sin_thumb(nav["detectar"])
    for m in dp["mesas"] + dj["mesas"]:
        m["_sug"] = m.pop("sugerencia", "")
    check("detectar (sin sugerencia ni PNG)", {**dp, "mesas": [{k: v for k, v in m.items() if k != "_sug"} for m in dp["mesas"]]},
          {**dj, "mesas": [{k: v for k, v in m.items() if k != "_sug"} for m in dj["mesas"]]})
    for m in dp["mesas"] + dj["mesas"]:
        m["sugerencia"] = m.pop("_sug")
    okS, txt = _sugerencias_equivalentes(dp, dj, reg)
    if okS:
        iguales = all(a.get("sugerencia") == b.get("sugerencia") for a, b in zip(dp["mesas"], dj["mesas"]))
        lineas.append("  ✓ detectar.sugerencia" + ("" if iguales else " (empate de distancia: desempate por `set` de Python)"))
    else:
        fallas.append("detectar.sugerencia"); lineas.append(f"  ✗ detectar.sugerencia: {txt}")
    if any(len(m.get("thumb") or "") == 0 for m in nav["detectar"]["mesas"]):
        fallas.append("detectar.thumb"); lineas.append("  ✗ detectar.thumb: alguna miniatura vino vacía")
    check("validar_arte_separado", py["validar_separado"], nav["validar_separado"])
    check("validar_arte (clásico)", py["validar_clasico"], nav["validar_clasico"])

    # ── el paquete de `prepararArte` ──
    pq = nav.get("paquete") or {}
    try:
        with zipfile.ZipFile(pq["zip"]) as z:
            nombres = set(z.namelist())
            esperados = {"manifest.json", "det.json", "auto.json", "pers.json", "mapeo.json", "pv.json", "validacion.json"}
            if nombres != esperados:
                fallas.append("paquete.nombres"); lineas.append(f"  ✗ paquete: archivos {sorted(nombres)}")
            else:
                lineas.append("  ✓ paquete: los 7 archivos, sin carpetas")
            zj = {n: json.loads(z.read(n).decode("utf-8")) for n in nombres if n.endswith(".json")}
        sha = hashlib.sha1(open(arte, "rb").read()).hexdigest()
        modo = "separado" if py["es_separado"] else "clasico"
        check("paquete.manifest", {"sha1": sha, "modo": modo}, zj["manifest.json"])
        check("paquete.det (sin PNG)", {**_sin_thumb(py["detectar"]), "mesas": [{k: v for k, v in m.items() if k != "sugerencia"} for m in _sin_thumb(py["detectar"])["mesas"]]},
              {**_sin_thumb(zj["det.json"]), "mesas": [{k: v for k, v in m.items() if k != "sugerencia"} for m in _sin_thumb(zj["det.json"])["mesas"]]})
        if modo == "separado":
            check("paquete.auto", py["mapeo_por_nombre"], zj["auto.json"])
            check("paquete.pers", py["personalizacion"], zj["pers.json"])
            check("paquete.mapeo (auto + fijo)", mapeo_final, zj["mapeo.json"])
            check("paquete.pv", {}, zj["pv.json"])
            vj = zj["validacion.json"]
            vp = py["paquete_validacion"]
            # la sugerencia no viaja en la validación; el resto, exacto
            check("paquete.validacion", vp, vj)
        else:
            check("paquete.validacion (clásico)", py["validar_clasico"], zj["validacion.json"])
    except Exception as e:
        fallas.append("paquete"); lineas.append(f"  ✗ paquete: {e}")

    tj = nav.get("tiempos") or {}
    lineas.insert(0, f"  servidor {t_py:.2f} s · navegador(Node) {nav.get('segundos', 0):.2f} s "
                     f"(personalización {tj.get('personalizacion', 0):.2f} · editables {tj.get('editables', 0):.2f} · "
                     f"detectar {tj.get('detectar', 0):.2f} · validar {tj.get('validar_separado', 0):.2f})")
    return not fallas, "\n".join(lineas), t_py, nav.get("segundos", 0)


def artes_por_defecto():
    out = []
    for p in sorted(glob.glob(os.path.join(AQUI, "entrada", "*", "disenos", "*", "arte.ai"))):
        pid = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(p))))
        if os.path.exists(os.path.join(AQUI, "datos", "productos", pid, "resumen_plantilla.json")) and \
                os.path.exists(os.path.join(AQUI, "entrada", pid, "plantilla.ai")):
            out.append(p)
    return out


if __name__ == "__main__":
    archivos = sys.argv[1:] or artes_por_defecto()
    if not archivos:
        print("no hay artes para comparar")
        sys.exit(2)
    todo_ok = True
    carpeta = tempfile.mkdtemp(prefix="verif_nav_arte_")
    try:
        for p in archivos:
            pid = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(p))))
            reg, orden = _registro_desde_resumen(pid)
            plantilla = os.path.join(AQUI, "entrada", pid, "plantilla.ai")
            print(f"· {os.path.relpath(p, AQUI)} ({os.path.getsize(p) / 1e6:.1f} MB, {len(reg or {})} piezas)")
            if not reg:
                print("  ✗ sin resumen_plantilla.json para armar el registro")
                todo_ok = False
                continue
            sub = os.path.join(carpeta, os.path.basename(os.path.dirname(p)))
            os.makedirs(sub, exist_ok=True)
            try:
                ok, txt, _, _ = comparar(p, plantilla, reg, orden, sub)
            except Exception as e:
                ok, txt = False, f"  ✗ excepción: {e!r}"
            print(txt)
            todo_ok = todo_ok and ok
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)
    print()
    print("✅ CONTRATO VERDE — el navegador lee el arte separado igual que el servidor" if todo_ok
          else "❌ CONTRATO ROTO — el navegador no lee el arte igual que el servidor")
    sys.exit(0 if todo_ok else 1)
