# -*- coding: utf-8 -*-
"""
CONTRATO: EL NAVEGADOR APLANA LA HOJA PARA EL RIP IGUAL QUE EL SERVIDOR — `py verificar_navegador_aplanar.py [hoja.pdf ...]`

PLAN_NAVEGADOR.md, etapa 4, punto 3. `frontend/src/motor/rip/aplanar.js` hace en el navegador lo
que `aplanar_rip._aplanar_archivo` hace en el servidor: des-anida los Form XObjects, un solo perfil
ICC, estado gráfico declarado (`/GSflat`), sin capas OCG ni texto fantasma, PDF 1.6, CMYK intacto.
Acá se aplana LO MISMO de los dos lados, en los dos modos (UN NIVEL, el default, y TOTAL =
`TIZADA_APLANADO_TOTAL=1`), y se compara la ESTRUCTURA del resultado:
  · páginas, profundidad de XObjects (0 en total, 1 en un nivel), perfiles ICC (uno, mismos bytes),
    versión 1.6, `/GSflat`, ni OCG ni marcadores de capa, Creator/Producer;
  · el content-stream de la página (y el de cada XObject que queda, en orden de uso) instrucción por
    instrucción, con los nombres de recursos normalizados por orden de primer uso (los números de
    objeto y los nombres pueden cambiar; los operadores y los valores de color, no);
  · el diccionario de la página entero, resuelto hasta el fondo (streams por contenido, reales con
    tolerancia float32: mupdf guarda los reales de los objetos en float);
  · y el dibujo: las dos salidas a 100 dpi (o menos si la hoja es enorme) con PyMuPDF, con la misma
    regla estructural de `verificar_navegador_vista.py` (bordes y última fila/columna tolerados).

Entradas: un PDF ARMADO acá con todo lo que el aplanado tiene que tratar (tres niveles de Form
anidados, el mismo Form usado dos veces y también anidado, nombres de recursos que chocan, una capa
OCG con /OCProperties, dos ICCBased iguales, texto con fuente declarada / inexistente / sin glifos,
ExtGState con transparencia «opaca», Contents en arreglo), la FICHA técnica más reciente (PyMuPDF,
tres niveles), la HOJA más reciente (ya aplanada por el servidor: idempotencia y bases `TizadaBase`)
y esa misma HOJA re-anidada dos niveles adentro de una capa (contenido real, sin aplanar).

⚠️ No toca nada del usuario: copia cada entrada a un temporal; `aplanar_rip` no importa la base.
"""
import glob
import io

CONTRATO_LENTO = True   # hojas reales de 8 m aplanadas dos veces y dibujadas: minutos, no segundos
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time

import pikepdf
import pymupdf as fitz
from pikepdf import Name, parse_content_stream, unparse_content_stream

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import aplanar_rip as AR  # noqa: E402
from verificar_navegador_vista import _distintos  # noqa: E402

NODE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "aplanar.mjs")
_OPKIND = {"Do": "/XObject", "gs": "/ExtGState", "cs": "/ColorSpace", "CS": "/ColorSpace",
           "scn": "/ColorSpace", "SCN": "/ColorSpace", "sh": "/Shading", "Tf": "/Font",
           "BDC": "/Properties", "DP": "/Properties"}
FALLAS = []


def ok(cond, msg):
    print(("    ✓ " if cond else "    ✗ ") + msg)
    if not cond:
        FALLAS.append(msg)
    return cond


# ─── el PDF armado acá ───────────────────────────────────────────────────────────────────────
def _icc_bytes():
    from PIL import ImageCms
    return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def armar_sintetico(path):
    pdf = pikepdf.new()
    icc = _icc_bytes()
    icc_a = pdf.make_stream(icc, N=3)            # dos streams distintos con los MISMOS bytes → uno solo
    icc_b = pdf.make_stream(icc, N=3)
    cs_pag = pikepdf.Array([Name.ICCBased, icc_a])
    cs_fx1 = pikepdf.Array([Name.ICCBased, icc_b])      # otro objeto con el mismo nombre → «CS0_fl1»
    cs_fx1a = pikepdf.Array([Name.ICCBased, icc_a])
    font = pdf.make_indirect(pikepdf.Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica))
    font2 = pdf.make_indirect(pikepdf.Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Courier))
    g0 = pdf.make_indirect(pikepdf.Dictionary(Type=Name.ExtGState, SMask=Name.None_, BM=Name.Normal, CA=1, ca=1, AIS=False))
    g1 = pdf.make_indirect(pikepdf.Dictionary(Type=Name.ExtGState, CA=0.5, BM=Name.Multiply))
    ocg = pdf.make_indirect(pikepdf.Dictionary(Type=Name.OCG, Name=pikepdf.String("Diseño")))
    im = pdf.make_stream(bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 0]), Type=Name.XObject, Subtype=Name.Image,
                         Width=2, Height=2, ColorSpace=Name.DeviceRGB, BitsPerComponent=8)
    fx1a = pdf.make_stream(
        b"/CS0 cs 0.2 0.4 0.6 sc 0 0 30 30 re f q 20 0 0 20 5 5 cm /Im0 Do Q 0.9 0.1 0.2 0.05 k 2 2 8 8 re f",
        Type=Name.XObject, Subtype=Name.Form, BBox=[0, 0, 30, 30],
        Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im0=im), ColorSpace=pikepdf.Dictionary(CS0=cs_fx1a)))
    fx1 = pdf.make_stream(
        b"/CS0 cs 0 0 1 sc 0 0 40 40 re f /G0 gs q 1 0 0 1 45 45 cm /Fx1a Do Q BT /F2 8 Tf 5 50 Td (in) Tj ET",
        Type=Name.XObject, Subtype=Name.Form, BBox=[0, 0, 100, 100], Matrix=[1, 0, 0, 1, 5, 5],
        Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Fx1a=fx1a), ColorSpace=pikepdf.Dictionary(CS0=cs_fx1),
                                     ExtGState=pikepdf.Dictionary(G0=g0), Font=pikepdf.Dictionary(F2=font2)))
    fx2 = pdf.make_stream(
        b"/OC /oc1 BDC 0 0 0 1 k 0 0 20 20 re f EMC /MP MP 1 0 0 0 K 2 w 0 0 m 20 20 l S",
        Type=Name.XObject, Subtype=Name.Form, BBox=[0, 0, 20, 20], Matrix=[1.5, 0, 0, 1.5, 300.123456, 200.5], OC=ocg,
        Group=pikepdf.Dictionary(S=Name.Transparency, CS=Name.DeviceCMYK),
        Resources=pikepdf.Dictionary(Properties=pikepdf.Dictionary(oc1=ocg)))
    c1 = pdf.make_stream(
        b"/OC /oc1 BDC q 1 0 0 1 20 20 cm /Fx1 Do Q EMC q 1 0 0 1 150 20 cm /Fx1 Do Q\n"
        b"/CS0 cs 1 0 0 sc 10 130 50 50 re f /CS1 cs 0 1 0 sc 70 130 50 50 re f 0 0 0 1 k 130 130 50 50 re f\n"
        b"0.9 0.1 0.2 0.05 k 190 130 50 50 re f /G0 gs /G1 gs 0.5 0.25 0 0 k 250 130 50 50 re f\n"
        b"BT /F1 12 Tf 10 250 Td (Hola) Tj ET BT /T1_0 12 Tf 10 270 Td (fantasma) Tj ET BT /F1 12 Tf ET")
    c2 = pdf.make_stream(b"q /Fx2 Do Q q 1 0 0 1 300 200 cm /Fx1a Do Q")
    page = pikepdf.Dictionary(
        Type=Name.Page, MediaBox=[0, 0, 400, 300], Contents=pikepdf.Array([c1, c2]),
        Resources=pikepdf.Dictionary(
            XObject=pikepdf.Dictionary(Fx1=fx1, Fx2=fx2, Fx1a=fx1a),
            ColorSpace=pikepdf.Dictionary(CS0=cs_pag, CS1=pikepdf.Array([Name.ICCBased, icc_b])),
            ExtGState=pikepdf.Dictionary(G0=g0, G1=g1),
            Font=pikepdf.Dictionary(F1=font, Fsin=font2),
            Properties=pikepdf.Dictionary(oc1=ocg)))
    pdf.pages.append(pikepdf.Page(page))
    pdf.Root.OCProperties = pikepdf.Dictionary(OCGs=pikepdf.Array([ocg]), D=pikepdf.Dictionary(ON=pikepdf.Array([ocg])))
    pdf.save(path)


def armar_hoja_anidada(hoja, path):
    """La hoja real, metida dos niveles adentro de una capa: contenido de verdad SIN aplanar."""
    src = pikepdf.open(hoja)
    out = pikepdf.new()
    pg = src.pages[0]
    inner = out.copy_foreign(pg.as_form_xobject())
    mb = [float(x) for x in pg.MediaBox]
    ocg = out.make_indirect(pikepdf.Dictionary(Type=Name.OCG, Name=pikepdf.String("molde")))
    outer = out.make_stream(b"q /Inner Do Q", Type=Name.XObject, Subtype=Name.Form, BBox=mb, Matrix=[1, 0, 0, 1, 0, 0],
                            OC=ocg, Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Inner=inner)))
    page = pikepdf.Dictionary(Type=Name.Page, MediaBox=mb, Contents=out.make_stream(b"/OC /oc1 BDC q /Outer Do Q EMC"),
                              Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Outer=outer),
                                                           Properties=pikepdf.Dictionary(oc1=ocg)))
    if "/UserUnit" in pg:
        page.UserUnit = pg.UserUnit
    out.pages.append(pikepdf.Page(page))
    out.Root.OCProperties = pikepdf.Dictionary(OCGs=pikepdf.Array([ocg]), D=pikepdf.Dictionary(ON=pikepdf.Array([ocg])))
    out.save(path)
    src.close()


# ─── lo que se mira de un PDF aplanado ───────────────────────────────────────────────────────
def _forms(res):
    xs = (res.get("/XObject") if res is not None else None) or {}
    return [(str(k), xs[k]) for k in xs.keys() if xs[k].get("/Subtype") == Name.Form]


def profundidad(res, nivel=0, vistos=None):
    vistos = vistos if vistos is not None else set()
    peor = nivel
    for _, xo in _forms(res):
        if xo.objgen in vistos:
            continue
        vistos.add(xo.objgen)
        peor = max(peor, profundidad(xo.get("/Resources"), nivel + 1, vistos))
    return peor


def perfiles_icc(pdf):
    """{objgen: bytes decodificados} de todos los ICCBased alcanzables desde las páginas."""
    out, vistos = {}, set()

    def _res(res):
        cs = (res.get("/ColorSpace") if res is not None else None) or {}
        for k in cs.keys():
            v = cs[k]
            if isinstance(v, pikepdf.Array) and len(v) > 1 and v[0] == Name.ICCBased:
                out[v[1].objgen] = v[1].read_bytes()
        for _, xo in _forms(res):
            if xo.objgen in vistos:
                continue
            vistos.add(xo.objgen)
            _res(xo.get("/Resources"))
    for pg in pdf.pages:
        _res(pg.get("/Resources"))
    return out


def normalizar(ops):
    """Las instrucciones con los nombres de recursos renombrados por orden de primer uso."""
    mapa, out = {}, []
    for inst in ops:
        k = _OPKIND.get(str(inst.operator))
        if k:
            operands = []
            for o in inst.operands:
                if isinstance(o, Name):
                    clave = (k, str(o))
                    if clave not in mapa:
                        mapa[clave] = Name(f"{k}{len(mapa)}")
                    o = mapa[clave]
                operands.append(o)
            inst = pikepdf.ContentStreamInstruction(operands, inst.operator)
        out.append(inst)
    return out


def comparar_contenido(a, b, etiqueta):
    """Instrucción por instrucción (normalizadas). Devuelve el primer desvío o None."""
    oa, ob = normalizar(list(parse_content_stream(a))), normalizar(list(parse_content_stream(b)))
    ua = [unparse_content_stream([x]) for x in oa]
    ub = [unparse_content_stream([x]) for x in ob]
    if ua == ub:
        return None, len(ua)
    i = next((j for j in range(min(len(ua), len(ub))) if ua[j] != ub[j]), min(len(ua), len(ub)))
    return (f"{etiqueta}: {len(ua)} vs {len(ub)} instrucciones; la primera distinta es la {i}: "
            f"servidor {ua[i] if i < len(ua) else '(fin)'!r} · navegador {ub[i] if i < len(ub) else '(fin)'!r}"), len(ua)


def _num(x):
    try:
        return float(x)
    except Exception:
        return None


def iguales(a, b, ruta, out, vistos):
    """Dos objetos de dos PDF distintos, resueltos hasta el fondo. Anota diferencias en `out`."""
    if len(out) >= 8:
        return
    if isinstance(a, pikepdf.Object) and isinstance(b, pikepdf.Object) and a.is_indirect and b.is_indirect:
        k = (a.objgen, b.objgen)
        if k in vistos:
            return
        vistos.add(k)
    if isinstance(a, pikepdf.Stream) or isinstance(b, pikepdf.Stream):
        if not (isinstance(a, pikepdf.Stream) and isinstance(b, pikepdf.Stream)):
            out.append(f"{ruta}: uno es stream y el otro no"); return
        da = {k: a.stream_dict[k] for k in a.stream_dict.keys() if k not in ("/Length", "/Filter", "/DecodeParms")}
        db = {k: b.stream_dict[k] for k in b.stream_dict.keys() if k not in ("/Length", "/Filter", "/DecodeParms")}
        if set(da) != set(db):
            out.append(f"{ruta}: claves del stream {sorted(set(da) ^ set(db))}"); return
        for k in da:
            iguales(da[k], db[k], f"{ruta}{k}", out, vistos)
        if a.read_bytes() != b.read_bytes():
            out.append(f"{ruta}: contenido del stream distinto ({len(a.read_bytes())} vs {len(b.read_bytes())} bytes)")
        return
    if isinstance(a, pikepdf.Dictionary) and isinstance(b, pikepdf.Dictionary):
        ka, kb = set(k for k in a.keys() if k != "/Parent"), set(k for k in b.keys() if k != "/Parent")
        if ka != kb:
            out.append(f"{ruta}: claves {sorted(ka ^ kb)}"); return
        for k in sorted(ka):
            iguales(a[k], b[k], f"{ruta}{k}", out, vistos)
        return
    if isinstance(a, pikepdf.Array) and isinstance(b, pikepdf.Array):
        if len(a) != len(b):
            out.append(f"{ruta}: arreglo de {len(a)} vs {len(b)}"); return
        for i in range(len(a)):
            iguales(a[i], b[i], f"{ruta}[{i}]", out, vistos)
        return
    na, nb = _num(a), _num(b)
    if na is not None and nb is not None and not isinstance(a, pikepdf.Name) and not isinstance(b, pikepdf.Name):
        # mupdf guarda los reales en float32: hasta ~7 cifras significativas
        if not math.isclose(na, nb, rel_tol=1e-6, abs_tol=1e-4):
            out.append(f"{ruta}: {a} vs {b}")
        return
    if str(a) != str(b):
        out.append(f"{ruta}: {a!r} vs {b!r}")


def render(path, tope_px=3000):
    with fitz.open(path) as d:
        pg = d[0]
        r = pg.rect
        dpi = min(100.0, tope_px * 72.0 / max(r.width, r.height))
        dpi = int(dpi)
        pix = pg.get_pixmap(dpi=dpi, alpha=False)
        return pix.samples, pix.width, pix.height, dpi


def comparar_salidas(py, js, total):
    """Compara la hoja aplanada por el servidor (`py`) con la del navegador (`js`)."""
    A, B = pikepdf.open(py), pikepdf.open(js)
    try:
        ok(len(A.pages) == len(B.pages), f"páginas: {len(A.pages)} = {len(B.pages)}")
        ok(A.pdf_version == "1.6" and B.pdf_version == "1.6", f"versión 1.6 (cabecera): servidor {A.pdf_version} · navegador {B.pdf_version}")
        fa, fb = fitz.open(py).metadata["format"], fitz.open(js).metadata["format"]
        ok(fa == fb, f"versión que ve MuPDF: {fa} = {fb}")
        ia, ib = perfiles_icc(A), perfiles_icc(B)
        esperado = min(1, len(ia))
        ok(len(ia) == len(ib) and len(ia) <= 1 and sorted(ia.values()) == sorted(ib.values()),
           f"perfiles ICC alcanzables: {len(ia)} = {len(ib)} (esperado {esperado}), mismos bytes")
        ok("/OCProperties" not in A.Root and "/OCProperties" not in B.Root, "sin /OCProperties")
        for clave in ("/Creator", "/Producer", "/Author"):
            ok(str(A.docinfo.get(clave)) == str(B.docinfo.get(clave)) == "TIZADA PRO", f"docinfo {clave} = TIZADA PRO")
        tope = 0 if total else 1
        for i, (pa, pb) in enumerate(zip(A.pages, B.pages)):
            ra, rb = pa.get("/Resources"), pb.get("/Resources")
            da, db = profundidad(ra), profundidad(rb)
            ok(da == db <= tope, f"página {i + 1}: profundidad de Form XObjects {da} = {db} (≤ {tope})")
            ok(len(_forms(ra)) == len(_forms(rb)), f"página {i + 1}: {len(_forms(ra))} = {len(_forms(rb))} Form XObjects")
            ok("/Properties" not in ra and "/Properties" not in rb, f"página {i + 1}: sin /Properties")
            ok(all("/OC" not in xo for _, xo in _forms(ra)) and all("/OC" not in xo for _, xo in _forms(rb)), f"página {i + 1}: ningún XObject con /OC")
            ga, gb = ra.get("/ExtGState", {}).get("/GSflat"), rb.get("/ExtGState", {}).get("/GSflat")
            ok(ga is not None and gb is not None and {str(k): str(v) for k, v in ga.items()} == {str(k): str(v) for k, v in gb.items()},
               f"página {i + 1}: /GSflat {dict((str(k), str(v)) for k, v in (ga or {}).items())}")
            ops_a = list(parse_content_stream(pa))
            marcas = [str(o.operator) for o in ops_a if str(o.operator) in ("BDC", "BMC", "EMC", "MP", "DP")]
            marcas += [str(o.operator) for o in parse_content_stream(pb) if str(o.operator) in ("BDC", "BMC", "EMC", "MP", "DP")]
            ok(not marcas, f"página {i + 1}: sin marcadores de capa en el contenido")
            ok(str(ops_a[0].operator) == "gs" and str(ops_a[0].operands[0]) == "/GSflat", f"página {i + 1}: empieza con /GSflat gs")
            desvio, n = comparar_contenido(pa, pb, f"página {i + 1}")
            ok(desvio is None, desvio or f"página {i + 1}: {n} instrucciones iguales (nombres normalizados)")
            # los XObjects que quedan, en orden de primer uso
            usados_a = [str(o.operands[0]) for o in ops_a if str(o.operator) == "Do"]
            usados_b = [str(o.operands[0]) for o in parse_content_stream(pb) if str(o.operator) == "Do"]
            orden_a = list(dict.fromkeys(usados_a))
            orden_b = list(dict.fromkeys(usados_b))
            ok(len(orden_a) == len(orden_b), f"página {i + 1}: {len(orden_a)} = {len(orden_b)} XObjects usados")
            xa, xb = ra.get("/XObject", {}), rb.get("/XObject", {})
            malos, total_inst = [], 0
            for na_, nb_ in zip(orden_a, orden_b):
                oa, ob = xa.get(na_), xb.get(nb_)
                if oa is None or ob is None or oa.get("/Subtype") != Name.Form or ob.get("/Subtype") != Name.Form:
                    if (oa is None) != (ob is None) or (oa is not None and oa.get("/Subtype") != ob.get("/Subtype")):
                        malos.append(f"{na_}/{nb_}: uno es Form y el otro no")
                    continue
                d, n = comparar_contenido(oa, ob, f"XObject {na_} ↔ {nb_}")
                total_inst += n
                if d:
                    malos.append(d)
                if "/Group" in oa or "/Group" in ob:
                    malos.append(f"{na_}/{nb_}: conserva /Group")
            ok(not malos, malos[0] if malos else f"página {i + 1}: {len(orden_a)} XObjects con el mismo contenido ({total_inst} instrucciones)")
            dif = []
            iguales(pa.obj, pb.obj, f"página {i + 1}", dif, set())
            ok(not dif, f"página {i + 1}: diccionario entero igual (recursos resueltos hasta el fondo)" if not dif else f"página {i + 1}: {dif[0]}")
    finally:
        A.close(); B.close()
    sa, wa, ha, dpi = render(py)
    sb, wb, hb, _ = render(js)
    if ok((wa, ha) == (wb, hb), f"dibujo a {dpi:.0f} dpi: {wa}x{ha} = {wb}x{hb}"):
        distintos, fuera, peor = _distintos(sa, sb, wa, ha)
        ok(fuera == 0, f"dibujo: {distintos} valores distintos de {len(sa)}, {fuera} fuera de borde/última fila (peor salto {peor})")


def aplanar_servidor(entrada, salida, total):
    shutil.copyfile(entrada, salida)
    viejo = os.environ.pop("TIZADA_APLANADO_TOTAL", None)
    if total:
        os.environ["TIZADA_APLANADO_TOTAL"] = "1"
    t = time.time()
    try:
        AR._aplanar_archivo(salida)
    finally:
        os.environ.pop("TIZADA_APLANADO_TOTAL", None)
        if viejo is not None:
            os.environ["TIZADA_APLANADO_TOTAL"] = viejo
    return time.time() - t


def aplanar_navegador(entrada, salida, total):
    cmd = ["node", "--max-old-space-size=8192", NODE, entrada, salida] + (["total"] if total else [])
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=3600)
    if r.returncode != 0:
        raise RuntimeError(f"Node falló: {r.stderr[-800:]}")
    return json.loads(r.stdout.strip().splitlines()[-1])["segundos"]


def correr(nombre, entrada, tmp, modos=(False, True)):
    for total in modos:
        modo = "TOTAL (todo inline)" if total else "UN NIVEL (default)"
        print(f"  · {nombre} — {modo}")
        py = os.path.join(tmp, f"{nombre}_{int(total)}_py.pdf")
        js = os.path.join(tmp, f"{nombre}_{int(total)}_js.pdf")
        try:
            t_py = aplanar_servidor(entrada, py, total)
        except Exception as e:
            ok(False, f"el servidor no pudo aplanar: {type(e).__name__}: {e}"); continue
        try:
            t_js = aplanar_navegador(entrada, js, total)
        except Exception as e:
            ok(False, f"el navegador no pudo aplanar: {e}"); continue
        print(f"    servidor {t_py:.2f} s ({os.path.getsize(py) / 1e6:.2f} MB) · navegador {t_js:.2f} s ({os.path.getsize(js) / 1e6:.2f} MB)")
        comparar_salidas(py, js, total)


def entradas_por_defecto():
    """De `trabajos/` (sólo se leen): la FICHA más reciente, la HOJA más reciente y la HOJA más chica
    de los últimos pedidos (para el modo TOTAL y la re-anidada, que multiplican el contenido)."""
    ficha = hoja = None
    chicas = []
    for d in sorted(glob.glob(os.path.join(AQUI, "trabajos", "*")), key=os.path.getmtime, reverse=True)[:12]:
        if ficha is None and os.path.exists(os.path.join(d, "FICHA_TECNICA.pdf")):
            ficha = os.path.join(d, "FICHA_TECNICA.pdf")
        h = sorted(glob.glob(os.path.join(d, "HOJA_*.pdf")), key=os.path.getsize)
        if hoja is None and h:
            hoja = h[-1]                     # la más grande del pedido más reciente: el camino real
        chicas += h
    chica = min(chicas, key=os.path.getsize) if chicas else None
    return ficha, hoja, chica


if __name__ == "__main__":
    tmp = tempfile.mkdtemp(prefix="verif_aplanar_")
    try:
        sint = os.path.join(tmp, "sintetico.pdf")
        armar_sintetico(sint)
        print("· PDF armado acá (3 niveles, OCG, 2 ICC iguales, texto fantasma, ExtGState opaco, Contents en arreglo)")
        correr("sintetico", sint, tmp)
        if sys.argv[1:]:
            for p in sys.argv[1:]:
                print(f"· {os.path.basename(p)} ({os.path.getsize(p) / 1e6:.1f} MB)")
                correr(os.path.splitext(os.path.basename(p))[0], p, tmp)
        else:
            ficha, hoja, chica = entradas_por_defecto()
            if ficha:
                print(f"· {os.path.relpath(ficha, AQUI)} ({os.path.getsize(ficha) / 1e6:.1f} MB, PyMuPDF, XObjects anidados)")
                correr("ficha", ficha, tmp)
            if hoja:
                # 🔴 SÓLO UN NIVEL (el camino real del servidor). En TOTAL cada `Do` de una base se
                # inlinea una vez por colocación: con esta hoja de 8 MB el servidor tarda 2,5 min y
                # deja 144 MB, y compararlos en Python se comió 21 GB de memoria (2026-09-17).
                print(f"· {os.path.relpath(hoja, AQUI)} ({os.path.getsize(hoja) / 1e6:.1f} MB, ya aplanada por el servidor: idempotencia)")
                correr("hoja", hoja, tmp, modos=(False,))
            if chica and chica != hoja:
                print(f"· {os.path.relpath(chica, AQUI)} ({os.path.getsize(chica) / 1e6:.1f} MB, la hoja más chica de los últimos pedidos)")
                correr("hoja_chica", chica, tmp)
            if chica:
                anid = os.path.join(tmp, "hoja_anidada.pdf")
                armar_hoja_anidada(chica, anid)
                print(f"· esa hoja chica re-anidada dos niveles adentro de una capa OCG ({os.path.getsize(anid) / 1e6:.1f} MB): contenido real sin aplanar")
                correr("hoja_anidada", anid, tmp)
            if not ficha and not hoja:
                print("  (no hay hojas ni fichas en trabajos/: sólo el PDF armado acá)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print()
    if FALLAS:
        print(f"❌ CONTRATO ROTO — {len(FALLAS)} falla(s); la primera: {FALLAS[0]}")
        sys.exit(1)
    print("✅ CONTRATO VERDE — el navegador aplana la hoja para el RIP igual que el servidor")
    sys.exit(0)
