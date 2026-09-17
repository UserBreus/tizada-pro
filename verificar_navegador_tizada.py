# -*- coding: utf-8 -*-
"""
CONTRATO: EL NAVEGADOR GENERA LA TIZADA ENTERA IGUAL QUE EL SERVIDOR — `py verificar_navegador_tizada.py [molde.ai]`

PLAN_NAVEGADOR.md, etapa 4 (el cierre). El MISMO pedido (un molde con el diseño adentro, prendas
de tres talles con nombre y número) se genera de las dos formas:
  · en el SERVIDOR: `_plan_del_pedido` + `generar_pedido_grupos` + aplanado para el RIP + perfil +
    ficha técnica, tal como lo hace `generar_multi`;
  · en el NAVEGADOR (Node, `frontend/src/motor/pruebas/tizada.mjs`): `pedido/generar.js` con un
    `fetch` que contesta con los mismos archivos (el plan, el desplegado, las tipografías, el
    perfil) y guarda el paquete que le mandaría al servidor.
Y se exige que las hojas sean la misma tizada: mismas páginas y medidas, mismo consumo, el
content-stream de cada página token por token (con los nombres de recursos normalizados), el mismo
perfil de salida, y el dibujo a 60 dpi con 0 píxeles distintos fuera de bordes; y que la ficha
técnica tenga el mismo texto y el mismo dibujo. Marcado CONTRATO_LENTO (renders grandes).

⚠️ No toca nada del usuario: el molde se COPIA a un temporal, `db` es un doble (nada de MSSQL) y el
catálogo es uno de mentira con ese molde solo.
"""
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import types

CONTRATO_LENTO = True
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
_TMP = tempfile.mkdtemp(prefix="verif_tizada_")
os.environ["TIZADA_DATOS"] = os.path.join(_TMP, "datos")
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"
os.environ["TIZADA_APLANADO_EN_PROCESO"] = "1"      # el aplanado acá mismo (sin procesos aparte)
for d in ("datos", "entrada", "trabajos"):
    os.makedirs(os.path.join(_TMP, d), exist_ok=True)

_DOCS = {}
_falso = types.ModuleType("db")
_falso.__getattr__ = lambda n: (lambda *a, **k: None)
_falso.get_doc = lambda c, default=None: _DOCS.get(c, default)
_falso.get_doc_ver = lambda c, default=None: (_DOCS.get(c, default), 0)
_falso.set_doc = lambda c, o, version_esperada=None: (_DOCS.__setitem__(c, o), 1)[-1]
_falso.guardar_catalogo = lambda cat, version_esperada=None: (_DOCS.__setitem__("catalogo", cat), 1)[-1]
_REG = {}
_falso.registro_rev = lambda pid: (1 if pid in _REG else None)
_falso.leer_registro = lambda pid: _REG.get(pid)
sys.modules["db"] = _falso
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")

import pikepdf                                 # noqa: E402
import pymupdf as fitz                         # noqa: E402
import registro as _LG                         # noqa: E402
_LG.usar_carpeta(os.path.join(_TMP, "logs"))
import servidor as S                           # noqa: E402
import motor_pedido as MP                      # noqa: E402
import piezas_con_diseno as PD                 # noqa: E402

S._USUARIOS_ON = False
NODE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "tizada.mjs")
PID = "prod_tizada_nav"
FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


def molde_por_defecto():
    c = [p for p in sorted(glob.glob(os.path.join(AQUI, "entrada", "*", "plantilla.ai")))
         if os.path.exists(os.path.join(os.path.dirname(p), "desplegado", "m1.pdf"))]
    return min(c, key=os.path.getsize) if c else None


def _distintos(py, js, W, H):
    distintos = fuera = 0
    for k in range(min(len(py), len(js))):
        a, b = py[k], js[k]
        if a == b:
            continue
        distintos += 1
        d = abs(a - b)
        px, py_ = (k // 3) % W, (k // 3) // W
        if px >= W - 1 or py_ >= H - 1:
            continue
        canal = k % 3
        vals = [py[(y * W + x) * 3 + canal] for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                for x, y in [(px + dx, py_ + dy)] if 0 <= x < W and 0 <= y < H]
        if vals and (max(vals) - min(vals)) >= d:
            continue
        fuera += 1
    return distintos, fuera


_RE_RES = re.compile(rb"/(S|A|GS|Fm|Im|F|Cs)([A-Za-z0-9_-]+)\b")


def _normalizar(stream):
    """Los nombres de recursos, por orden de primer uso; los números tal cual (son texto nuestro)."""
    vistos = {}
    def _r(m):
        k = m.group(0)
        if k not in vistos:
            vistos[k] = b"/" + m.group(1) + str(len(vistos)).encode()
        return vistos[k]
    return _RE_RES.sub(_r, stream)


def comparar_hoja(py_path, js_path, etiqueta):
    with pikepdf.open(py_path) as A, pikepdf.open(js_path) as B:
        ok(len(A.pages) == len(B.pages), f"{etiqueta}: mismas páginas ({len(A.pages)} = {len(B.pages)})")
        oa, ob = A.Root.get("/OutputIntents"), B.Root.get("/OutputIntents")
        ok((oa is None) == (ob is None), f"{etiqueta}: perfil de salida declarado en los dos ({'sí' if oa is not None else 'no'})")
        if oa is not None and ob is not None:
            ok(bytes(oa[0].DestOutputProfile.read_bytes()) == bytes(ob[0].DestOutputProfile.read_bytes()),
               f"{etiqueta}: el mismo perfil ICC ({len(oa[0].DestOutputProfile.read_bytes())} bytes)")
        for i in range(min(len(A.pages), len(B.pages))):
            pa, pb = A.pages[i], B.pages[i]
            ma, mb = [float(x) for x in pa.MediaBox], [float(x) for x in pb.MediaBox]
            ok(all(abs(x - y) < 0.05 for x, y in zip(ma, mb)) and str(pa.get("/UserUnit")) == str(pb.get("/UserUnit")),
               f"{etiqueta} pág {i + 1}: mismo tamaño ({ma[2]:.1f}×{ma[3]:.1f} pt, UserUnit {pa.get('/UserUnit')})")
            ca = _normalizar(b"".join(pikepdf.unparse_content_stream(pikepdf.parse_content_stream(pa)).split()))
            cb = _normalizar(b"".join(pikepdf.unparse_content_stream(pikepdf.parse_content_stream(pb)).split()))
            ok(ca == cb, f"{etiqueta} pág {i + 1}: el mismo content-stream ({len(ca)} bytes)" if ca == cb
               else f"{etiqueta} pág {i + 1}: content-stream distinto (servidor {len(ca)} bytes, navegador {len(cb)}; 1ª diferencia en {next((k for k, (x, y) in enumerate(zip(ca, cb)) if x != y), min(len(ca), len(cb)))})")
    da, db = fitz.open(py_path), fitz.open(js_path)
    for i in range(min(da.page_count, db.page_count)):
        z = 60 / 72
        xa = da[i].get_pixmap(matrix=fitz.Matrix(z, z), alpha=False, colorspace=fitz.csRGB)
        xb = db[i].get_pixmap(matrix=fitz.Matrix(z, z), alpha=False, colorspace=fitz.csRGB)
        if (xa.width, xa.height) != (xb.width, xb.height):
            ok(False, f"{etiqueta} pág {i + 1}: dibujo de distinto tamaño")
            continue
        distintos, fuera = _distintos(xa.samples, xb.samples, xa.width, xa.height)
        ok(fuera == 0, f"{etiqueta} pág {i + 1}: dibujo a 60 dpi {xa.width}x{xa.height}: {fuera} píxeles distintos que no son borde ({distintos} en total)")


def main(orig):
    print("\n1 · EL MOLDE Y EL PEDIDO")
    carpeta = os.path.join(_TMP, "entrada", PID)
    os.makedirs(carpeta)
    shutil.copy2(orig, os.path.join(carpeta, "plantilla.ai"))
    shutil.copytree(os.path.join(os.path.dirname(orig), "desplegado"), os.path.join(carpeta, "desplegado"))
    for extra in ("molde.origen", "plantilla.ver"):
        if os.path.exists(os.path.join(os.path.dirname(orig), extra)):
            shutil.copy2(os.path.join(os.path.dirname(orig), extra), os.path.join(carpeta, extra))
    pl = os.path.join(carpeta, "plantilla.ai")
    os.makedirs(os.path.join(_TMP, "datos", "productos", PID), exist_ok=True)
    alta = PD.alta_molde_con_diseno(pl, procesos=None, paginas=False)
    registro, talles = alta["registro"], list(alta["talles"])
    _REG[PID] = registro                       # el registro vive en la base (el doble)
    comunes = [t for t in talles if all(t in v for v in registro.values())]
    elegidos = [comunes[0], comunes[len(comunes) // 2], comunes[-1]][:3]
    _DOCS["catalogo"] = {"activo": PID, "productos": [{"id": PID, "nombre": "Molde de prueba", "origen": "con_diseno",
                                                        "planilla_template_id": "plan_default"}],
                         "plantillas_planillas": [{"id": "plan_default", "nombre": "Estándar", "columnas": [
                             {"id": "talle", "label": "Talle", "role": "talle"}, {"id": "nombre", "label": "Nombre", "role": "nombre"},
                             {"id": "numero", "label": "Número", "role": "numero"}]}],
                         "reglas_planilla": [], "telas": []}
    filas = [{"talle": t, "nombre": n, "numero": num} for t, (n, num) in zip(elegidos, [("PÉREZ", "10"), ("GÓMEZ", "7"), ("DÍAZ", "23")])]
    filas.append({"talle": elegidos[0], "nombre": "LÓPEZ", "numero": "1"})
    cuerpo = {"molds": [PID], "prendas": filas, "default_diseno": "principal",
              "planilla": {"columnas": [{"id": "talle", "label": "Talle"}, {"id": "nombre", "label": "Nombre"}, {"id": "numero", "label": "Número"}],
                           "filas": filas}}
    ok(len(registro) > 0, f"{len(registro)} piezas · talles {elegidos} · {len(filas)} prendas")

    print("\n2 · EL SERVIDOR GENERA")
    with S.app.test_request_context("/api/pedido/plan", method="POST", json=cuerpo):
        plan = S._plan_del_pedido(cuerpo)
        plan_nav = S._plan_para_navegador(plan)
        cat = S._cargar_catalogo()
        _icc, _icc_nom, _icc_n = S._icc_para_salida([], cat, forzado=None)
    salida_py = os.path.join(_TMP, "trabajos", "py")
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
    # la ficha del servidor, con la misma guía que usaría `generar_multi`
    import ficha_tecnica as FT
    _guias = []
    for _sp in plan["_guias_ficha"]:
        with S.app.test_request_context("/", method="POST", json=cuerpo):
            g = S._molde_guia_ficha(PID, cat["productos"][0], registro, _sp.get("diseno") or "principal", _sp, reempl={})
        if g:
            _guias.append(g)
    FT.generar_ficha(salida_py, "Ficha técnica", "Molde de prueba · " + time.strftime("%d/%m/%Y"), cuerpo["planilla"], _guias)
    ok(os.path.exists(os.path.join(salida_py, "FICHA_TECNICA.pdf")), f"ficha técnica del servidor ({len(_guias)} guía(s))")

    print("\n3 · EL NAVEGADOR GENERA LO MISMO")
    with S.app.test_request_context("/", method="GET"):
        motor_b = S.app.test_client().get(f"/api/productos/{PID}/motor_b").get_json()
    fuentes = {}
    for ruta in glob.glob(os.path.join(S.FUENTES, "*")):
        if ruta.lower().endswith((".ttf", ".otf")):
            fuentes[os.path.basename(ruta)] = ruta
    perfil_path = None
    if _icc:
        perfil_path = os.path.join(_TMP, "perfil.icc")
        with open(perfil_path, "wb") as fh:
            fh.write(_icc)
    entorno = {"plan": plan_nav, "cuerpo": cuerpo, "motor_b": {PID: motor_b},
               "desplegado": {PID: os.path.join(carpeta, "desplegado")}, "fuentes": fuentes, "perfil": perfil_path}
    ep = os.path.join(_TMP, "entorno.json")
    with open(ep, "w", encoding="utf-8") as fh:
        json.dump(entorno, fh, ensure_ascii=False)
    salida_js = os.path.join(_TMP, "trabajos", "nav")
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
        comparar_hoja(os.path.join(salida_py, hp["archivo"]), os.path.join(salida_js, hn["archivo"]), hp["archivo"])
    ok(nav.get("validaciones") == res["validaciones"],
       f"las validaciones de la hoja (texto en curvas, cero fuentes) dan bien en el navegador: {nav.get('validaciones')} vs servidor {res['validaciones']}")

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
                distintos, fuera = _distintos(xa.samples, xb.samples, xa.width, xa.height)
                ok(fuera == 0, f"ficha pág {i + 1}: dibujo a 100 dpi: {fuera} píxeles distintos que no son borde ({distintos} en total)")
            else:
                ok(False, f"ficha pág {i + 1}: dibujo de distinto tamaño")
    print(f"\n    tiempos: servidor {t_py:.1f} s · navegador {tiempos['segundos']:.1f} s (Node, un hilo)")


if __name__ == "__main__":
    orig = sys.argv[1] if len(sys.argv) > 1 else molde_por_defecto()
    if not orig:
        print("  (no hay un molde del camino B con desplegado: se saltea)")
        sys.exit(0)
    try:
        main(orig)
    finally:
        try:
            MP.cerrar_abiertos()
        except Exception:
            pass
        shutil.rmtree(_TMP, ignore_errors=True)
    print()
    if FALLOS:
        print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
        for f in FALLOS:
            print("   · " + f)
        sys.exit(1)
    print("✅ CONTRATO VERDE — el navegador genera la tizada entera igual que el servidor")
