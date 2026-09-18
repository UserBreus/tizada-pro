# -*- coding: utf-8 -*-
"""
CONTRATO: EL NAVEGADOR LEE EL MOLDE SIN DISEÑO (camino A) IGUAL QUE EL SERVIDOR — `py verificar_navegador_camino_a.py [molde.ai ...]`

PLAN_NAVEGADOR.md, etapa 1, paso 7. `frontend/src/motor/molde/caminoA.js` traduce lo que hoy hace
`motor_pedido.py` con un molde pelado: los talles (`_talles_de_plantilla`, el orden del panel de
capas), `alta_plantilla` (etiquetas «TALLE-Pieza-#», ancla con ángulo, Manga corta/larga, problemas
y advertencias), `detectar_piezas` (talle de referencia automático o capa «referencia», visor en mm),
`detectar_piezas_todas` (todas las variantes en un lienzo) y `alta_plantilla_manual` (nombres
normalizados, emparejado exacto del DXF / por índice / por solape / por forma, fijos y acomodo a mano,
segunda pasada «Pieza extra N», faltantes y sobrantes). Este contrato corre las dos cosas sobre los
MISMOS archivos y exige que den lo mismo: cada número el MISMO double, cada texto igual, cada lista
en el mismo orden y cada diccionario con las MISMAS claves EN EL MISMO ORDEN.

Archivos: los moldes del camino A de `entrada/` (los que no tienen `desplegado/` ni `molde.origen`)
copiados a un temporal —con `correspondencia_piezas.json` y `emparejado_talles.json` de
`datos/productos/<pid>/` si existen—, más dos moldes SINTÉTICOS que se generan acá con PyMuPDF para
ejercitar lo que los reales no traen: etiquetas de texto (rotadas, repetidas, mal escritas, sin
contorno), la capa «Referencia», la capa «0» (basura de CAD vs. talle legítimo), capas de sistema,
talles con distinta cantidad de piezas (solape, forma, segunda pasada), acomodo y fijos a mano.

Lo que NO se puede reproducir y se tolera, acotado:
  · `math.log` y `math.atan2` de CPython (libm de MSVC) y los de V8 difieren en el último bit en un
    2 % / 17 % de los valores (medido con 40 000 al azar). El ángulo del ancla se redondea a 1
    decimal y el logaritmo sólo entra en el costo del emparejado por forma (que se ordena y se
    compara con un umbral): un bit cambia el resultado nada más que en un empate exacto entre dos
    pares distintos. El contrato compara los RESULTADOS (registro, elección) exactos: si un empate
    así apareciera en un molde real, se vería acá como diferencia y se decidiría a mano.
  · La cola de `_ordenar_por_archivo` (capas con dibujo que no figuran en `/Order`) itera un `set`
    de Python: su orden cambia de un proceso a otro. No pasa con archivos de Illustrator ni de
    `importar_dxf.py` (todas las capas van en `/Order`); los sintéticos tampoco lo provocan.

⚠️ No toca nada del usuario: los moldes se COPIAN a un temporal, `db` es un doble, no hay servidor.
"""
import glob
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
# el servidor se importa sólo para validar el paquete (`_paquete_molde_aplicar`): sus datos van a un
# temporal y la base es un doble, como en `verificar_paquete_molde.py`
_TMP_SRV = tempfile.mkdtemp(prefix="verif_camino_a_srv_")
os.environ["TIZADA_DATOS"] = _TMP_SRV
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP_SRV, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP_SRV, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"
_falso = types.ModuleType("db")
_falso.__getattr__ = lambda n: (lambda *a, **k: None)
sys.modules["db"] = _falso
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")

import pymupdf as fitz                        # noqa: E402
import motor_pedido as MP                     # noqa: E402

_SRV = None


def servidor():
    """`servidor.py` importado una vez, con el registro en un temporal (ver `registro-del-sistema`)."""
    global _SRV
    if _SRV is None:
        import registro as _LG
        _LG.usar_carpeta(tempfile.mkdtemp(prefix="verif_camino_a_logs_"))
        import servidor as S
        _SRV = S
    return _SRV

NODE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "caminoA.mjs")


# ── comparación exacta (números, textos, orden de listas y de claves) ────────────────────────
def _normal(v):
    if isinstance(v, (list, tuple)):
        return [_normal(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _normal(x) for k, x in v.items()}
    if isinstance(v, set):
        return sorted(_normal(x) for x in v)
    if isinstance(v, bool) or v is None or isinstance(v, str):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    return v


def diferencias(a, b, ruta="", out=None, tope=10):
    if out is None:
        out = []
    if len(out) >= tope:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        if list(a.keys()) != list(b.keys()):
            if set(a) != set(b):
                out.append(f"{ruta}: claves distintas {sorted(set(a) ^ set(b))[:6]}")
            else:
                out.append(f"{ruta}: mismas claves en OTRO orden: servidor {list(a)[:6]} · navegador {list(b)[:6]}")
            return out
        for k in a:
            diferencias(a[k], b[k], f"{ruta}.{k}", out, tope)
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{ruta}: largo {len(a)} vs {len(b)}")
            return out
        for i, (x, y) in enumerate(zip(a, b)):
            diferencias(x, y, f"{ruta}[{i}]", out, tope)
        return out
    if type(a) is not type(b) and not (isinstance(a, float) and isinstance(b, float)):
        out.append(f"{ruta}: tipo {type(a).__name__} vs {type(b).__name__} ({str(a)[:60]!s} · {str(b)[:60]!s})")
        return out
    if a != b:
        out.append(f"{ruta}: servidor {str(a)[:120]!s} · navegador {str(b)[:120]!s}")
    return out


def _intentar(fn):
    try:
        return fn()
    except Exception as e:
        return {"error": str(e)}


# ── los moldes sintéticos ────────────────────────────────────────────────────────────────────
def _poli(page, pts, oc, fill=None, ancho=1.0):
    page.draw_polyline([fitz.Point(*p) for p in pts], color=(0, 0, 0), fill=fill, closePath=True,
                       width=ancho, oc=oc)


def _pieza(page, x, y, w, h, oc, forma="poli", fill=None):
    """Una «pieza» de w×h puntos con la esquina superior izquierda en (x, y)."""
    if forma == "rect":
        page.draw_rect(fitz.Rect(x, y, x + w, y + h), color=(0, 0, 0), fill=fill, oc=oc)
    elif forma == "curva":
        sh = page.new_shape()
        sh.draw_bezier((x, y), (x + w, y), (x + w, y + h), (x, y + h))
        sh.draw_line((x, y + h), (x, y))
        sh.finish(color=(0, 0, 0), fill=fill, closePath=True, oc=oc)
        sh.commit()
    else:
        _poli(page, [(x, y), (x + w, y + h * 0.1), (x + w * 0.9, y + h), (x + w * 0.2, y + h * 0.9)], oc, fill=fill)


def sintetico_etiquetas(carpeta):
    """Convención «una mesa por pieza, talles en capas» con etiquetas de texto — y sus errores."""
    doc = fitz.open()
    M, L = doc.add_ocg("M"), doc.add_ocg("L")
    fondo = doc.add_ocg("Fondo")                  # capa de sistema: nunca es un talle
    cero = doc.add_ocg("0")                       # con tantas formas como los talles → SÍ es un talle
    for _ in range(5):
        doc.new_page(width=2000, height=2000)
    p = doc
    # mesa 1: Frente (M y L), Fondo con un rectángulo, «0» con una forma
    _pieza(p[0], 100, 200, 500, 1500, M, "curva", fill=(1, 0, 0))
    p[0].insert_text((120, 150), "M-Frente-#", fontsize=20, fontname="helv", oc=M)
    _pieza(p[0], 700, 200, 600, 1700, L)
    p[0].insert_text((720, 150), "L-Frente-#", fontsize=22, fontname="helv", oc=L)
    p[0].draw_rect(fitz.Rect(0, 0, 2000, 60), color=(0, 0, 1), oc=fondo)
    _pieza(p[0], 1400, 300, 300, 300, cero, "rect")
    # mesa 2: Manga sin (corta)/(larga) en la etiqueta → lo decide el alto (< 45 cm = corta)
    _pieza(p[1], 100, 200, 500, 600, M, "rect")
    p[1].insert_text((80, 900), "M-Manga-#", fontsize=18, fontname="helv", rotate=90, oc=M)
    _pieza(p[1], 800, 200, 600, 1400, L)
    p[1].insert_text((820, 150), "L-Manga-#", fontsize=18, fontname="helv", oc=L)
    _pieza(p[1], 1500, 300, 300, 300, cero, "rect")
    # mesa 3: Espalda en M; L tiene molde pero NO etiqueta (problema)
    _pieza(p[2], 100, 200, 800, 1200, M, fill=(0, 1, 0))
    p[2].insert_text((120, 150), "M-Espalda-#", fontsize=20, fontname="helv", oc=M)
    _pieza(p[2], 1000, 200, 800, 1300, L)
    _pieza(p[2], 1500, 1600, 300, 300, cero, "rect")
    # mesa 4: Frente repetido en M (advertencia + «repartida en las mesas»); L mal escrita
    _pieza(p[3], 100, 200, 500, 1400, M)
    p[3].insert_text((120, 150), "M-Frente-#", fontsize=20, fontname="helv", oc=M)
    _pieza(p[3], 700, 200, 600, 1500, L)
    p[3].insert_text((720, 150), "L_Frente#", fontsize=20, fontname="helv", oc=L)
    # mesa 5: M no nombra la pieza; L tiene etiqueta pero ningún trazado (no se puede leer el contorno)
    _pieza(p[4], 100, 200, 500, 1400, M)
    p[4].insert_text((120, 150), "M--#", fontsize=20, fontname="helv", oc=M)
    p[4].insert_text((720, 150), "L-Cuello-#", fontsize=20, fontname="helv", oc=L)
    ruta = os.path.join(carpeta, "plantilla.ai")
    doc.save(ruta)
    doc.close()
    return ruta


def sintetico_referencia(carpeta):
    """Un bloque de piezas por talle, capa «Referencia», «0» con basura, talles con más piezas."""
    doc = fitz.open()
    ref = doc.add_ocg("Referencia")
    cero = doc.add_ocg("0")
    capa1 = doc.add_ocg("Capa 1")
    S, M, L, XL, XXL = (doc.add_ocg(n) for n in ("S", "M", "L", "XL", "2XL"))
    page = doc.new_page(width=3000, height=3000)
    # tres piezas anidadas (mismo origen, escala por talle): referencia = M
    def bloque(oc, esc, x0=100, y0=100, extra=0, dx=0):
        _pieza(page, x0 + dx, y0, 500 * esc, 900 * esc, oc)                      # Frente
        _pieza(page, x0 + dx + 700, y0, 520 * esc, 880 * esc, oc, "curva")       # Espalda
        _pieza(page, x0 + dx + 1400, y0, 300 * esc, 400 * esc, oc, "rect")       # Manga
        if extra >= 1:
            _pieza(page, x0 + dx + 1400, y0 + 600, 200 * esc, 150 * esc, oc, "rect")   # una pieza de más
        if extra >= 2:
            _pieza(page, x0 + dx + 1800, y0 + 600, 150 * esc, 250 * esc, oc)          # y otra
    bloque(ref, 1.0)
    bloque(S, 0.9)
    bloque(M, 1.0)
    bloque(L, 1.1, dx=1500, y0=1500)              # lado a lado (sin solape) → por forma, con acomodo a mano
    bloque(XL, 1.2, extra=1)                      # una pieza más → solape + sobrante → segunda pasada
    bloque(XXL, 1.3, extra=2)                     # dos más → la segunda pasada empareja por forma
    _pieza(page, 2500, 2500, 100, 100, cero, "rect")            # «0» con UNA forma: basura de CAD
    page.draw_rect(fitz.Rect(0, 0, 3000, 40), color=(0, 0, 1), oc=capa1)
    page.draw_line((0, 2990), (3000, 2990), color=(0, 0, 1))    # sin capa: se ignora
    ruta = os.path.join(carpeta, "plantilla.ai")
    doc.save(ruta)
    doc.close()
    emparejado = {"acomodo": {"L": {"0": [-500 / MP.MM, -500 / MP.MM]}},
                  "manual": {"M": {"Frente": 1}, "S": {"Nombre ajeno": 2}}}
    json.dump(emparejado, open(os.path.join(carpeta, "emparejado_talles.json"), "w", encoding="utf-8"))
    return ruta


# ── el contrato por molde ────────────────────────────────────────────────────────────────────
def argumentos_manual(copia, det):
    """Los argumentos de `alta_plantilla_manual`, los mismos para el servidor y el navegador."""
    carpeta = os.path.dirname(copia)
    corr = os.path.join(carpeta, "correspondencia_piezas.json")
    emp = os.path.join(carpeta, "emparejado_talles.json")
    indices = json.load(open(corr, encoding="utf-8")) if os.path.exists(corr) else None
    if indices:
        asign = [{"idx": i, "nombre": n} for i, n in enumerate(indices.get(det["talle_ref"], []))]
    else:
        nombres = ["Frente", "Frente", "Dorso", "Manga corta derecha", "Cuello"]
        asign = [{"idx": i, "nombre": n} for i, n in enumerate(nombres[:len(det["piezas"])])]
    talles = det["talles"]
    return {"asignaciones": asign, "mesa": det["mesa"], "talle_ref": det["talle_ref"], "indices": indices,
            "emparejado": json.load(open(emp, encoding="utf-8")) if os.path.exists(emp) else None,
            # un talle afuera, para ejercitar `excluidos` y los faltantes (nunca el de referencia)
            "excluir_talles": [t for t in talles if t != det["talle_ref"]][-1:] or None}


def correr_python(copia):
    doc = fitz.open(copia)
    res = {"capas_ui": [c.get("text") for c in doc.layer_ui_configs()],
           "talles": MP._talles_de_plantilla(doc)}
    doc.close()
    res["alta"] = _intentar(lambda: MP.alta_plantilla(copia))
    res["detectar"] = _intentar(lambda: MP.detectar_piezas(copia))
    res["todas"] = _intentar(lambda: MP.detectar_piezas_todas(copia))
    res["por_talle"] = {}
    if "error" not in res["detectar"]:
        for t in res["detectar"]["talles"]:
            res["por_talle"][t] = _intentar(lambda: MP.detectar_piezas(copia, talle_ref=t))
    manual = None
    if "error" not in res["detectar"]:
        manual = argumentos_manual(copia, res["detectar"])
        res["manual"] = _intentar(lambda: MP.alta_plantilla_manual(
            copia, manual["asignaciones"], manual["mesa"], manual["talle_ref"], indices=manual["indices"],
            emparejado=manual["emparejado"], excluir_talles=manual["excluir_talles"]))
    else:
        res["manual"] = None
    return res, manual


def comparar(path, extras=()):
    tmp = tempfile.mkdtemp(prefix="verif_camino_a_")
    try:
        copia = os.path.join(tmp, "plantilla.ai")
        shutil.copy2(path, copia)
        for e in extras:
            if e and os.path.exists(e):
                shutil.copy2(e, os.path.join(tmp, os.path.basename(e)))
        t = time.time()
        py, manual = correr_python(copia)
        t_py = time.time() - t
        zip_paq = os.path.join(tmp, "paquete.zip")
        cmd = ["node", NODE, copia, os.path.join(tmp, "nav.json"), "--paquete", zip_paq]
        if manual is not None:
            with open(os.path.join(tmp, "manual.json"), "w", encoding="utf-8") as g:
                json.dump(manual, g, ensure_ascii=False)
            cmd += ["--manual", os.path.join(tmp, "manual.json")]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=1800)
        if r.returncode != 0:
            return False, f"  Node falló: {r.stderr[-900:]}"
        nav = json.load(open(os.path.join(tmp, "nav.json"), encoding="utf-8"))
        lineas = [f"  servidor {t_py:.1f} s · navegador(Node) {nav['segundos']:.1f} s"]
        d = []
        for clave in ("capas_ui", "talles", "alta", "detectar", "todas", "por_talle", "manual"):
            d += diferencias(_normal(py.get(clave)), _normal(nav.get(clave)), clave)
        # el paquete `alta_a`: el servidor lo valida contra el archivo y devuelve lo que guardaría
        try:
            fase, alta_paq = servidor()._paquete_molde_aplicar(copia, zip_paq, fases=("alta_a",))
        except Exception as e:
            d.append(f"paquete: el servidor lo rechazó: {e}")
        else:
            det_paq = alta_paq.pop("_deteccion", {}) or {}
            alta_paq.pop("_dxf", None)
            alta_paq.pop("_dxf_bytes", None)
            d += diferencias(_normal(py["alta"]), _normal(alta_paq), "paquete.alta")
            esperado = {"auto": py["detectar"], "todas": py["todas"]}
            for t, v in py["por_talle"].items():
                esperado[t] = v
            esperado = {k: v for k, v in esperado.items() if "error" not in v}
            d += diferencias(sorted(esperado), sorted(det_paq), "paquete.deteccion (archivos)")
            for k in sorted(esperado):
                if k in det_paq:
                    d += diferencias(_normal(esperado[k]), _normal(det_paq[k]), f"paquete.deteccion/{k}")
        if d:
            lineas.append(f"  ✗ {len(d)} diferencia(s) (se muestran las primeras):")
            lineas += [f"      {x}" for x in d[:12]]
            return False, "\n".join(lineas)
        alta, det, todas, man = py["alta"], py["detectar"], py["todas"], py["manual"]
        resumen = [f"{len(py['talles'])} talles"]
        resumen.append(f"alta: {len(alta['registro'])} piezas, {len(alta['problemas'])} problemas, "
                       f"{len(alta['advertencias'])} advertencias" if "error" not in alta else f"alta: «{alta['error']}»")
        resumen.append(f"detectar: mesa {det['mesa']}, ref «{det['talle_ref']}», {len(det['piezas'])} piezas"
                       if "error" not in det else f"detectar: «{det['error']}»")
        resumen.append(f"todas: {len(todas['piezas'])} piezas" if "error" not in todas else f"todas: «{todas['error']}»")
        if man is not None:
            resumen.append(f"manual: {len(man['registro'])} piezas, {sum(len(v) for v in man['registro'].values())} por talle, "
                           f"{len(man.get('faltantes_por_talle') or {})} talles incompletos, "
                           f"{len(man.get('sobrantes_por_talle') or {})} con sobrantes, excluidos {man.get('excluidos')}"
                           if "error" not in man else f"manual: «{man['error']}»")
        resumen.append(f"paquete alta_a de {os.path.getsize(zip_paq) / 1024:.0f} KB con "
                       f"{len(nav['paquete']['detecciones'])} detecciones por talle, aceptado por el servidor")
        lineas.append("  ✓ idéntico: " + " · ".join(resumen))
        return True, "\n".join(lineas)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def moldes_por_defecto():
    """Los moldes del camino A de `entrada/`: sin `desplegado/` ni `molde.origen`, con sus datos."""
    out = []
    for p in sorted(glob.glob(os.path.join(AQUI, "entrada", "*", "plantilla.ai"))):
        carpeta = os.path.dirname(p)
        if os.path.isdir(os.path.join(carpeta, "desplegado")) or os.path.exists(os.path.join(carpeta, "molde.origen")):
            continue
        pid = os.path.basename(carpeta)
        datos = os.path.join(AQUI, "datos", "productos", pid)
        out.append((p, [os.path.join(datos, "correspondencia_piezas.json"), os.path.join(datos, "emparejado_talles.json")]))
    return out


if __name__ == "__main__":
    ok_todo = True
    casos = [(p, []) for p in sys.argv[1:]] or moldes_por_defecto()
    sint = tempfile.mkdtemp(prefix="verif_camino_a_sint_")
    try:
        for nombre, gen in (("sintético: etiquetas de texto", sintetico_etiquetas),
                            ("sintético: capa Referencia y talles desparejos", sintetico_referencia)):
            carpeta = os.path.join(sint, nombre.split(":")[0] + str(len(os.listdir(sint))))
            os.makedirs(carpeta)
            ruta = gen(carpeta)
            casos.append((ruta, [os.path.join(carpeta, "emparejado_talles.json")], nombre))
        for caso in casos:
            p, extras = caso[0], caso[1]
            etiqueta = caso[2] if len(caso) > 2 else os.path.basename(os.path.dirname(p))
            print(f"· {etiqueta} ({os.path.getsize(p) / 1e6:.1f} MB)")
            ok, txt = comparar(p, extras)
            print(txt)
            ok_todo = ok_todo and ok
    finally:
        shutil.rmtree(sint, ignore_errors=True)
        shutil.rmtree(_TMP_SRV, ignore_errors=True)
    print()
    print("✅ CONTRATO VERDE — el navegador lee el molde sin diseño (camino A) igual que el servidor" if ok_todo
          else "❌ CONTRATO ROTO — el navegador y el servidor no leen igual el molde sin diseño (camino A)")
    sys.exit(0 if ok_todo else 1)
