# -*- coding: utf-8 -*-
"""
CONTRATO: EL NAVEGADOR COMPONE LA HOJA (EL SELLO) IGUAL QUE EL SERVIDOR — `py verificar_navegador_hoja.py [N_prendas]`

CONTRATO_LENTO — corre el motor entero sobre un pedido de 7 prendas (2 páginas de mesa) y rasteriza a
60 dpi las cuatro hojas (dos de ellas de más de 5 m): ~100 s, de los que 90 son el render. Entra en la
tanda con `--todos`. Con `3` tarda ~50 s (una página).

PLAN_NAVEGADOR.md, etapa 4, punto 2. `frontend/src/motor/hoja/componer.js` hace en el navegador lo
que `hoja_pike.componer_hoja_sello` hace en el servidor: la hoja de una tela con el dibujo de cada
mesa desplegada UNA sola vez (Form XObject `/S0`…) y cada pieza como
`q <matriz> <recorte a la caja> <base_stream remapeado> <estampado> Q`.

Cómo se prueba, con datos REALES y sin inventar la entrada:
  1. se copia a un temporal el molde del camino B `entrada/prod_20260916_095236_ef99` (plantilla +
     marca + desplegado; `copy2` conserva la fecha, así el sello del desplegado sigue valiendo);
  2. se arma un pedido chico y se corre el motor de verdad (`motor_pedido.generar_pedido`) con
     `hoja_pike.componer_hoja_sello` INTERCEPTADO: lo que el motor le pasa (colocaciones, bases con
     su `base_stream`/`fuentes_xo`, estampados, cfg) se vuelca a JSON y después se llama al
     original, que escribe la hoja de Python;
  3. Node (`frontend/src/motor/pruebas/hoja.mjs`) compone la MISMA entrada;
  4. y además la misma entrada corrida 420 cm más abajo (una mesa de más de 5,08 m): el caso
     `/UserUnit 2`, que no sale de un pedido chico, y el perfil ICC como OutputIntent.
Se compara: cantidad de páginas, tamaños, `/UserUnit`, `OutputIntents`, los XObjects (uno por
página de mesa usada: BBox, Matrix, `/TizadaBase`, recursos y el contenido byte a byte), el
content-stream de cada página BYTE A BYTE (y, si difiere, instrucción por instrucción con los
nombres normalizados para decir dónde), consumo y alturas, y el render a 60 dpi de las dos hojas
con la regla estructural de `verificar_navegador_vista.py` (un píxel distinto sólo se acepta en un
borde o en la última fila/columna).

🔴 NO TOCA NADA DEL USUARIO NI LA BASE: `db` se reemplaza por un doble que revienta si alguien lo
llama, el molde se copia a un temporal, el registro se reconstruye de `piezas.json` (en disco) y
todo lo que se escribe va al temporal, que se borra.
"""
import glob
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
os.chdir(AQUI)

# ── la base, fuera de alcance (misma guarda que `verificar_sello.py`) ───────────────────────
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"
_doble = types.ModuleType("db")
_doble.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(AssertionError("LA PRUEBA TOCÓ MSSQL")))
sys.modules.setdefault("db", _doble)

import pikepdf                       # noqa: E402
import pymupdf as fitz               # noqa: E402
import motor_pedido as MP            # noqa: E402
import hoja_pike                     # noqa: E402
from verificar_navegador_vista import _distintos  # noqa: E402

NODE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "hoja.mjs")
PID = "prod_20260916_095236_ef99"
DATOS = os.environ.get("TIZADA_DATOS") or "datos"
ENTRADA = os.environ.get("TIZADA_ENTRADA") or "entrada"
FUENTES = os.path.join(AQUI, "catalogo_fuentes")
NOMBRES = ["MESSI", "DI MARIA", "ALVAREZ", "ENZO", "OTAMENDI", "ROMERO", "TAGLIAFICO"]
DPI = 60
CM = hoja_pike.CM


def _registro(pl):
    """El registro del molde SIN tocar la base: en el camino B lo arma `alta_molde_con_diseno`
    (correspondencia exacta por capas; es lo que hace el servidor al subirlo). Sobre la COPIA con el
    desplegado ya hecho no vuelve a desplegar nada. Los nombres quedan provisorios («Pieza N»): a la
    hoja no le cambian nada (el estampado sale del motor, igual para los dos lados)."""
    import piezas_con_diseno as PD
    cat = json.load(open(os.path.join(DATOS, "productos_catalogo.json"), encoding="utf-8"))
    prod = next((p for p in cat["productos"] if p["id"] == PID), None) or {}
    alta = PD.alta_molde_con_diseno(pl, paginas=False)
    if not alta.get("registro"):
        raise SystemExit("[i] el alta del camino B no registró piezas: " + "; ".join(alta.get("problemas") or []))
    return alta["registro"], alta["talles"], prod


def _volcar(colocaciones, cfg, signo, carpeta, nombre, perfil=None):
    """Lo que recibe `componer_hoja_sello`, como datos simples, en `<carpeta>/<nombre>.json`."""
    bases, ids, origenes = {}, {}, {}
    hojas = []
    for hoja in colocaciones:
        h = []
        for c in hoja or []:
            b = c["pieza"]["base"]
            k = ids.get(id(b))
            if k is None:
                k = f"b{len(ids)}"
                ids[id(b)] = k
                despl = b.get("despl")
                if not despl:
                    raise RuntimeError("esta prueba es del camino B: la base tiene que venir de un molde desplegado")
                fx = list((b.get("fuentes_xo") or {}).items())
                if len(fx) != 1:
                    raise RuntimeError(f"camino B: una fuente por base, vinieron {len(fx)}")
                oid = os.path.basename(despl[2])
                if oid not in origenes:
                    shutil.copy2(despl[2], os.path.join(carpeta, oid))
                    origenes[oid] = oid
                bases[k] = {"baseStream": b["base_stream"], "B": float(b["B"]), "W": float(b["W"]),
                            "Hp": float(b["Hp"]), "delMolde": True,
                            "fuentesXo": [[fx[0][0], {"origen": oid, "pagina": int(despl[1])}]]}
            h.append({"cx": float(c["cx"]), "cy": float(c["cy"]), "bw": float(c["bw"]), "bh": float(c["bh"]),
                      "ang": c["ang"], "estampado": c["pieza"].get("estampado") or "", "base": k})
        hojas.append(h)
    d = {"cfg": cfg, "hojas": hojas, "bases": bases, "origenes": origenes, "signo_rotacion": signo}
    if perfil:
        d["perfil"] = perfil
    ruta = os.path.join(carpeta, nombre + ".json")
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False)
    return ruta


def _perfil_icc():
    """Un perfil ICC real de la máquina (sólo para probar el OutputIntent), o None."""
    for pat in (os.path.join(AQUI, "perfiles_icc", "*.ic[cm]"),
                r"C:\Program Files (x86)\Common Files\Adobe\Color\Profiles\*.icc",
                r"C:\Windows\System32\spool\drivers\color\*.icm"):
        for f in sorted(glob.glob(pat)):
            try:
                if os.path.getsize(f) > 1000:
                    return f
            except OSError:
                pass
    return None


def _embeber_perfil(path, icc, nombre, n):
    """`servidor._embeber_perfil_pdf`, copiado: importar `servidor` levanta Flask entero."""
    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        st = pdf.make_stream(icc)
        st.N = n
        oi = pdf.make_indirect(pikepdf.Dictionary({
            "/Type": pikepdf.Name("/OutputIntent"), "/S": pikepdf.Name("/GTS_PDFX"),
            "/OutputConditionIdentifier": pikepdf.String(nombre), "/Info": pikepdf.String(nombre),
            "/DestOutputProfile": st}))
        pdf.Root.OutputIntents = pikepdf.Array([oi])
        pdf.save(path)


# ── comparación ──────────────────────────────────────────────────────────────────────────────
def _contenido(pg):
    c = pg.obj.get("/Contents")
    if c is None:
        return b""
    if isinstance(c, pikepdf.Array):
        return b"\n".join(s.read_bytes() for s in c)
    return c.read_bytes()


def _nums(arr):
    return [float(x) for x in arr] if arr is not None else None


def _cerca(a, b, tol=0.01):
    if a is None or b is None:
        return a is None and b is None
    return len(a) == len(b) and all(abs(x - y) <= tol for x, y in zip(a, b))


def _tokens(data):
    """Instrucciones de un content-stream con los nombres de XObject normalizados por orden de
    aparición: para decir DÓNDE difieren dos streams cuando los bytes no son iguales."""
    from pikepdf import parse_content_stream
    out, ren = [], {}
    for ops, op in parse_content_stream(pikepdf.Stream(pikepdf.new(), data)):
        vals = []
        for o in ops:
            if isinstance(o, pikepdf.Name) and str(op) == "Do":
                nm = str(o)
                vals.append(ren.setdefault(nm, f"/X{len(ren)}"))
            else:
                vals.append(str(o))
        out.append(" ".join(vals + [str(op)]))
    return out


def _recursos_resumen(res):
    """Las claves de cada tabla de recursos de un XObject (fuentes, colores, estados gráficos)."""
    out = {}
    for k in (res or {}).keys():
        v = res[k]
        try:
            out[str(k)] = sorted(str(x) for x in v.keys()) if isinstance(v, pikepdf.Dictionary) else "?"
        except Exception:
            out[str(k)] = "?"
    return out


def comparar(py_path, js_path, etiqueta):
    """Compara las dos hojas. Devuelve (ok, líneas)."""
    lineas, fallas = [], []
    with pikepdf.open(py_path) as A, pikepdf.open(js_path) as B:
        if len(A.pages) != len(B.pages):
            fallas.append(f"cantidad de páginas: servidor {len(A.pages)} · navegador {len(B.pages)}")
        oa, ob = A.Root.get("/OutputIntents"), B.Root.get("/OutputIntents")
        if (oa is None) != (ob is None):
            fallas.append(f"OutputIntents: servidor {'sí' if oa is not None else 'no'} · navegador {'sí' if ob is not None else 'no'}")
        elif oa is not None:
            a0, b0 = oa[0], ob[0]
            for k in ("/S", "/OutputConditionIdentifier", "/Info"):
                if str(a0.get(k)) != str(b0.get(k)):
                    fallas.append(f"OutputIntent {k}: {a0.get(k)} vs {b0.get(k)}")
            pa, pb = a0.get("/DestOutputProfile"), b0.get("/DestOutputProfile")
            if pa.read_bytes() != pb.read_bytes() or int(pa.get("/N")) != int(pb.get("/N")):
                fallas.append("OutputIntent: el perfil ICC incrustado no es el mismo")
            lineas.append(f"  ✓ OutputIntent {a0.get('/S')} «{a0.get('/Info')}» con el mismo ICC ({len(pa.read_bytes())} bytes, N={int(pa.get('/N'))})")
        xo_a, xo_b = {}, {}
        for i, (pa, pb) in enumerate(zip(A.pages, B.pages), 1):
            ma, mb = _nums(pa.obj.get("/MediaBox")), _nums(pb.obj.get("/MediaBox"))
            if not _cerca(ma, mb):
                fallas.append(f"pág {i}: MediaBox {ma} vs {mb}")
            ua, ub = pa.obj.get("/UserUnit"), pb.obj.get("/UserUnit")
            if (None if ua is None else int(ua)) != (None if ub is None else int(ub)):
                fallas.append(f"pág {i}: /UserUnit {ua} vs {ub}")
            ra = (pa.obj.get("/Resources") or {}).get("/XObject") or {}
            rb = (pb.obj.get("/Resources") or {}).get("/XObject") or {}
            if sorted(str(k) for k in ra.keys()) != sorted(str(k) for k in rb.keys()):
                fallas.append(f"pág {i}: nombres de XObject {sorted(str(k) for k in ra.keys())} vs {sorted(str(k) for k in rb.keys())}")
            for k in ra.keys():
                xo_a.setdefault(str(k), ra[k])
            for k in rb.keys():
                xo_b.setdefault(str(k), rb[k])
            ca, cb = _contenido(pa), _contenido(pb)
            if ca == cb:
                _uu = int(ua) if ua is not None else 1
                lineas.append(f"  ✓ pág {i}: {ma[2] * _uu / CM:.1f} × {ma[3] * _uu / CM:.1f} cm reales "
                              f"(MediaBox {ma[2]:.2f} × {ma[3]:.2f} pt, UserUnit {_uu}) · "
                              f"content-stream IDÉNTICO ({len(ca):,} bytes) · {len(ra)} dibujo(s)")
            else:
                ta, tb = _tokens(ca), _tokens(cb)
                j = next((j for j in range(min(len(ta), len(tb))) if ta[j] != tb[j]), min(len(ta), len(tb)))
                fallas.append(f"pág {i}: content-stream distinto ({len(ca)} vs {len(cb)} bytes; {len(ta)} vs {len(tb)} instrucciones) "
                              f"— instrucción {j}: servidor {ta[j] if j < len(ta) else '∅'!r} · navegador {tb[j] if j < len(tb) else '∅'!r}")
        if len(xo_a) != len(xo_b):
            fallas.append(f"dibujos distintos en la hoja: servidor {len(xo_a)} · navegador {len(xo_b)}")
        for nm in sorted(set(xo_a) & set(xo_b)):
            a, b = xo_a[nm], xo_b[nm]
            probs = []
            if str(a.get("/Subtype")) != "/Form" or str(b.get("/Subtype")) != "/Form":
                probs.append("Subtype")
            if not _cerca(_nums(a.get("/BBox")), _nums(b.get("/BBox"))):
                probs.append(f"BBox {_nums(a.get('/BBox'))} vs {_nums(b.get('/BBox'))}")
            if not _cerca(_nums(a.get("/Matrix")), _nums(b.get("/Matrix")), 1e-6):
                probs.append(f"Matrix {a.get('/Matrix')} vs {b.get('/Matrix')}")
            if bool(a.get("/TizadaBase", False)) != bool(b.get("/TizadaBase", False)):
                probs.append(f"TizadaBase {a.get('/TizadaBase')} vs {b.get('/TizadaBase')}")
            for k in ("/OC", "/Group"):
                if k in a or k in b:
                    probs.append(f"{k} presente")
            if _recursos_resumen(a.get("/Resources")) != _recursos_resumen(b.get("/Resources")):
                probs.append(f"recursos {_recursos_resumen(a.get('/Resources'))} vs {_recursos_resumen(b.get('/Resources'))}")
            da, db = a.read_bytes(), b.read_bytes()
            if da != db:
                k0 = next((k for k in range(min(len(da), len(db))) if da[k] != db[k]), min(len(da), len(db)))
                probs.append(f"contenido distinto ({len(da)} vs {len(db)} bytes; byte {k0}: {da[max(0, k0 - 30):k0 + 30]!r} vs {db[max(0, k0 - 30):k0 + 30]!r})")
            if probs:
                fallas.append(f"dibujo {nm}: " + "; ".join(probs))
            else:
                lineas.append(f"  ✓ dibujo {nm}: mismo BBox, Matrix, TizadaBase, recursos y contenido ({len(da):,} bytes)")
    # ── píxeles: las dos hojas con el mismo MuPDF ────────────────────────────────────────────
    with fitz.open(py_path) as da_, fitz.open(js_path) as db_:
        for i in range(min(da_.page_count, db_.page_count)):
            t = time.time()
            pa = da_[i].get_pixmap(dpi=DPI, alpha=False)
            pb = db_[i].get_pixmap(dpi=DPI, alpha=False)
            if (pa.width, pa.height) != (pb.width, pb.height):
                fallas.append(f"pág {i + 1}: render {pa.width}x{pa.height} vs {pb.width}x{pb.height}")
                continue
            distintos, fuera, peor = _distintos(pa.samples, pb.samples, pa.width, pa.height)
            if fuera:
                fallas.append(f"pág {i + 1}: {fuera} píxel(es) distintos que NO son borde (peor salto {peor})")
            else:
                lineas.append(f"  ✓ pág {i + 1}: render {pa.width}x{pa.height} a {DPI} dpi · {distintos} valores distintos "
                              f"de {len(pa.samples):,}{' (todos de borde/última fila)' if distintos else ''} · {time.time() - t:.1f} s")
    for f in fallas:
        lineas.append(f"  ✗ {f}")
    return not fallas, "\n".join(lineas)


def _node(entrada_json, salida_pdf):
    r = subprocess.run(["node", NODE, entrada_json, salida_pdf], capture_output=True, text=True,
                       encoding="utf-8", timeout=1800)
    if r.returncode != 0:
        raise RuntimeError(f"Node falló: {r.stderr[-1500:]}")
    return json.loads(r.stdout.strip().splitlines()[-1])


def main():
    # 7 prendas: con el buzo (7 piezas, ~80 cm por prenda) dan DOS páginas de mesa, así se prueba
    # que cada página lleve su propia tabla de recursos y sólo los dibujos que usa.
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 7
    origen = os.path.join(ENTRADA, PID)
    if not os.path.exists(os.path.join(origen, "desplegado", "m1.pdf")):
        print(f"  (no está el molde desplegado {origen}: se saltea)")
        return 0
    tmp = tempfile.mkdtemp(prefix="verif_hoja_")
    ok_todo = True
    try:
        # 1. el molde, copiado (fecha incluida: el sello del desplegado la compara)
        molde = os.path.join(tmp, "molde")
        shutil.copytree(origen, molde, copy_function=shutil.copy2)
        pl = os.path.join(molde, "plantilla.ai")
        reg, talles, prod = _registro(pl)
        print(f"molde {PID} · {len(reg)} piezas · {len(talles)} talles · {n} prendas")
        MP._DET_CACHE.clear()
        pers = MP.extraer_personalizacion(pl)
        ts = talles[len(talles) // 2 - 1: len(talles) // 2 + 2] or talles
        prendas = [{"talle": ts[i % len(ts)], "nombre": NOMBRES[i % len(NOMBRES)],
                    "numero": str((i * 7) % 99 + 1), "__variante": None} for i in range(n)]
        # borde y etiqueta explícitos, como `medir_tizada_b`: así el estampado por prenda no es vacío
        kw = dict(borde_corte=prod.get("borde_corte") or {"activo": True, "ancho_mm": 2.0, "color": [0, 0, 0, 0.85], "alineacion": "fuera"},
                  etiqueta=prod.get("etiqueta") or {"activo": True, "size_mm": 3.0, "mostrar": {"talle": True, "pieza": True, "numero": True},
                                                    "posiciones": {}, "align": "centro"},
                  rotaciones={p: ("libre" if i % 3 == 0 else "180" if i % 3 == 1 else "90") for i, p in enumerate(reg)},
                  config_nesting={"ancho_cm": 180, "altura_max_cm": 500, "espaciado_cm": 0.5,
                                  "margenes_cm": {"sup": 1, "inf": 1, "izq": 1, "der": 1}})
        # 2. el motor de verdad, con el compositor interceptado
        capturas = []
        original = hoja_pike.componer_hoja_sello

        def _espia(colocaciones, cfg, path_salida, signo_rotacion=1, progreso=None):
            r = original(colocaciones, cfg, path_salida, signo_rotacion, progreso)
            capturas.append((colocaciones, cfg, path_salida, signo_rotacion, r))
            return r
        hoja_pike.componer_hoja_sello = _espia
        sal = os.path.join(tmp, "salida")
        try:
            t0 = time.time()
            res = MP.generar_pedido(pl, None, reg, pers, prendas, FUENTES, sal, **kw)
            t_motor = time.time() - t0
        finally:
            hoja_pike.componer_hoja_sello = original
        if not capturas:
            print("  ✗ el motor no pasó por `componer_hoja_sello` (¿el molde no es del camino B?)")
            return 1
        print(f"motor: {t_motor:.1f} s · {len(res['hojas'])} hoja(s) · {len(capturas)} llamada(s) al sello")

        for k, (coloc, cfg, path_py, signo, (consumo_py, alturas_py)) in enumerate(capturas):
            n_col = sum(len(h) for h in coloc)
            angs = sorted({c["ang"] for h in coloc for c in h})
            print(f"· {os.path.basename(path_py)}: {n_col} colocaciones en {sum(1 for h in coloc if h)} página(s) · giros {angs}")
            ent = _volcar(coloc, cfg, signo, tmp, f"hoja{k}")
            js = os.path.join(tmp, f"hoja{k}_js.pdf")
            info = _node(ent, js)
            altos_py = [round(a / CM, 1) for a in hoja_pike.altos_de_hojas(coloc, cfg)]
            if info["alturas_cm"] != alturas_py or altos_py != alturas_py or abs(info["consumo_cm"] - consumo_py) > 1e-9:
                print(f"  ✗ alturas/consumo: servidor {alturas_py} / {consumo_py!r} (altos_de_hojas {altos_py}) · "
                      f"navegador {info['alturas_cm']} / {info['consumo_cm']!r}")
                ok_todo = False
            else:
                print(f"  ✓ alturas {alturas_py} cm · consumo {consumo_py:.2f} cm iguales · navegador {info['segundos']:.2f} s")
            ok, txt = comparar(path_py, js, f"hoja{k}")
            print(txt)
            ok_todo = ok_todo and ok

            # 4. LA MESA LARGA (/UserUnit) y el perfil: la misma entrada, 420 cm más abajo. El
            #    compositor es una función pura de (colocaciones, cfg): se lo llama directo.
            if k == 0:
                bajo = [[dict(c, cy=c["cy"] + 420 * CM) for c in h] for h in coloc]
                path_py2 = os.path.join(tmp, "larga_py.pdf")
                original(bajo, cfg, path_py2, signo, None)
                perfil = None
                icc = _perfil_icc()
                if icc:
                    with open(icc, "rb") as fh:
                        icc_bytes = fh.read()
                    nom = os.path.splitext(os.path.basename(icc))[0]
                    _embeber_perfil(path_py2, icc_bytes, nom, 4)
                    perfil = {"icc": icc, "nombre": nom, "n": 4}
                ent2 = _volcar(bajo, cfg, signo, tmp, "larga", perfil=perfil)
                js2 = os.path.join(tmp, "larga_js.pdf")
                info2 = _node(ent2, js2)
                with pikepdf.open(path_py2) as p2:
                    uus = [int(pg.obj.get("/UserUnit") or 1) for pg in p2.pages]
                print(f"· mesa larga (misma tizada 420 cm más abajo): /UserUnit {uus} · "
                      f"{'con' if perfil else 'sin'} perfil ICC · navegador {info2['segundos']:.2f} s")
                if max(uus) < 2:
                    print("  ✗ la mesa larga no pasó de 5,08 m: la prueba del /UserUnit no probó nada")
                    ok_todo = False
                ok2, txt2 = comparar(path_py2, js2, "larga")
                print(txt2)
                ok_todo = ok_todo and ok2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print()
    print("✅ CONTRATO VERDE — el navegador compone la hoja (el sello) igual que el servidor" if ok_todo
          else "❌ CONTRATO ROTO — la hoja del navegador difiere")
    return 0 if ok_todo else 1


if __name__ == "__main__":
    sys.exit(main())
