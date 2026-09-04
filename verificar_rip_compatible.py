# -*- coding: utf-8 -*-
"""CONTRATO DE COMPATIBILIDAD CON EL RIP — `py verificar_rip_compatible.py HOJA.pdf [--muestra]`

Lo que va a la imprenta tiene que ser un PDF que CUALQUIER RIP desde 2020 lea sin sorpresas y que
imprima los colores tal cual (pedido del usuario 2026-09-04): estructura «PDF/X-1a-like».

Lo que se verifica sobre la hoja FINAL (ya aplanada):
  1. PDF 1.6 o anterior.
  2. Sin capas: ni /OCProperties en el catálogo ni /OC en los XObjects.
  3. Sin transparencia: ningún /Group /S /Transparency, ningún /SMask en ExtGState o imágenes,
     ningún ExtGState con CA/ca < 1 o BM distinto de Normal.
  4. XObjects de UN solo nivel: ningún Form XObject de la página referencia otro Form.
  5. Toda fuente tiene su archivo embebido (FontFile/FontFile2/FontFile3) — o no hay fuentes.
  6. Espacios de color: sólo DeviceCMYK, DeviceGray, ICCBased de 4 canales, Separation/DeviceN
     (sin RGB, sin Lab/CalRGB) — el CMYK exacto es ley del proyecto.
  7. Un solo perfil ICC por contenido (sin copias repetidas).
  8. OutputIntent /GTS_PDFX con /DestOutputProfile de 4 canales (el perfil de salida incrustado).
  9. Content-streams balanceados (q/Q, BT/ET) — reusa `motor_pedido.validar_salida`.
 10. Se abre y se dibuja con PyMuPDF sin errores (segundo lector, independiente de pikepdf).

`--muestra` deja `HOJA_muestra_rip.pdf` al lado, para llevar a una imprenta real.
Sale 0 si pasa; 1 con la lista de lo que falla. Se puede llamar desde el servidor al terminar
cada tizada (`verificar(path) -> (ok, fallas)`).
"""
import hashlib
import os
import sys

import pikepdf
from pikepdf import Name


def _walk_xobjects(res, vistos, nivel=0):
    """Recorre los Form XObjects de unos recursos: yield (xobj, nivel)."""
    try:
        xs = res.get("/XObject") if res is not None else None
    except Exception:
        xs = None
    if not xs:
        return
    for k in [str(x) for x in xs.keys()]:
        xo = xs[k]
        try:
            og = xo.objgen
        except Exception:
            og = None
        if og in vistos:
            continue
        vistos.add(og)
        yield xo, nivel
        if xo.get("/Subtype") == Name("/Form"):
            yield from _walk_xobjects(xo.get("/Resources"), vistos, nivel + 1)


def verificar(path):
    fallas = []
    def mal(cond, msg):
        if not cond:
            fallas.append(msg)
    pdf = pikepdf.open(path)
    try:
        # 1
        mal(str(pdf.pdf_version) <= "1.6", f"versión PDF {pdf.pdf_version} (> 1.6)")
        # 2 capas
        mal("/OCProperties" not in pdf.Root, "el catálogo tiene /OCProperties (capas)")
        # 8 OutputIntent
        oi = pdf.Root.get("/OutputIntents")
        _ok_oi = False
        if oi is not None and len(oi):
            o = oi[0]
            dp = o.get("/DestOutputProfile")
            _ok_oi = (o.get("/S") == Name("/GTS_PDFX") and dp is not None and int(dp.get("/N", 0)) == 4)
        mal(_ok_oi, "sin OutputIntent /GTS_PDFX con perfil CMYK (/DestOutputProfile N=4)")
        vistos = set()
        icc_hashes = {}
        fuentes_sin_archivo = []
        cs_malos = []
        for pg in pdf.pages:
            contenedores = [(pg.obj, -1)]
            for xo, nivel in _walk_xobjects(pg.get("/Resources"), vistos):
                if xo.get("/Subtype") == Name("/Form"):
                    contenedores.append((xo, nivel))
                    # 4 un nivel
                    mal(nivel == 0, f"XObject anidado a profundidad {nivel + 1}")
                    # 2 y 3
                    mal("/OC" not in xo, "un XObject lleva /OC (capa)")
                    g = xo.get("/Group")
                    mal(not (g is not None and g.get("/S") == Name("/Transparency")), "un XObject tiene /Group /Transparency")
                else:
                    mal("/SMask" not in xo, "una imagen lleva /SMask (transparencia)")
                    cs = xo.get("/ColorSpace")
                    if cs is not None and not _cs_ok(cs, icc_hashes):
                        cs_malos.append(str(cs)[:40])
            for cont, _ in contenedores:
                res = cont.get("/Resources")
                if res is None:
                    continue
                g = cont.get("/Group")
                mal(not (g is not None and g.get("/S") == Name("/Transparency")), "la página tiene /Group /Transparency")
                # 3 ExtGState
                for k, gs in list((res.get("/ExtGState") or {}).items()):
                    try:
                        if "/SMask" in gs and gs["/SMask"] != Name("/None"):
                            fallas.append(f"ExtGState {k} con SMask")
                        if "/CA" in gs and float(gs["/CA"]) < 1 or "/ca" in gs and float(gs["/ca"]) < 1:
                            fallas.append(f"ExtGState {k} con opacidad < 1")
                        if "/BM" in gs and gs["/BM"] not in (Name("/Normal"), Name("/Compatible")):
                            fallas.append(f"ExtGState {k} con modo de fusión {gs['/BM']}")
                    except Exception:
                        pass
                # 5 fuentes
                for k, f in list((res.get("/Font") or {}).items()):
                    if not _fuente_embebida(f):
                        fuentes_sin_archivo.append(str(f.get("/BaseFont", k)))
                # 6/7 colorspaces
                for k, cs in list((res.get("/ColorSpace") or {}).items()):
                    if not _cs_ok(cs, icc_hashes):
                        cs_malos.append(f"{k}={str(cs)[:40]}")
        mal(not fuentes_sin_archivo, f"fuentes sin archivo embebido: {sorted(set(fuentes_sin_archivo))[:5]}")
        mal(not cs_malos, f"espacios de color fuera de CMYK/Gray/ICC-4/Separation: {cs_malos[:5]}")
        _dup = [h for h, ogs in icc_hashes.items() if len(ogs) > 1]
        mal(not _dup, f"{len(_dup)} perfil(es) ICC repetidos ({sum(len(icc_hashes[h]) for h in _dup)} copias)")
    finally:
        pdf.close()
    # 9 balanceados
    try:
        import motor_pedido as MP
        v = MP.validar_salida(os.path.dirname(path), [{"tela": "hoja", "archivo": os.path.basename(path)}], {})
        for x in v:
            if x.get("ok") is False and "balance" in x.get("nombre", "").lower():
                fallas.append(x.get("nombre"))
    except Exception as e:
        fallas.append(f"no se pudo validar el balance de los streams: {e}")
    # 10 segundo lector
    try:
        import pymupdf as fitz
        d = fitz.open(path)
        for pg in d:
            pg.get_pixmap(dpi=8)
        d.close()
    except Exception as e:
        fallas.append(f"PyMuPDF no pudo dibujar la hoja: {e}")
    return (not fallas), fallas


def _fuente_embebida(f):
    try:
        if f.get("/Subtype") == Name("/Type0"):
            f = f["/DescendantFonts"][0]
        fd = f.get("/FontDescriptor")
        if fd is None:
            return f.get("/Subtype") == Name("/Type3")
        return any(k in fd for k in ("/FontFile", "/FontFile2", "/FontFile3"))
    except Exception:
        return False


def _cs_ok(cs, icc_hashes):
    try:
        if isinstance(cs, pikepdf.Name):
            return str(cs) in ("/DeviceCMYK", "/DeviceGray", "/Pattern")
        if isinstance(cs, pikepdf.Array) and len(cs):
            fam = str(cs[0])
            if fam == "/ICCBased":
                st = cs[1]
                if int(st.get("/N", 0)) != 4:
                    return False
                h = hashlib.sha1(bytes(st.read_raw_bytes())).hexdigest()
                icc_hashes.setdefault(h, set()).add(st.objgen)
                return True
            if fam in ("/Separation", "/DeviceN"):
                return _cs_ok(cs[2], icc_hashes)
            if fam == "/Indexed":
                return _cs_ok(cs[1], icc_hashes)
            if fam == "/Pattern":
                return True
            return fam in ("/DeviceCMYK", "/DeviceGray")
    except Exception:
        return False
    return False


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__); sys.exit(2)
    path = args[0]
    ok, fallas = verificar(path)
    print(f"CONTRATO DE COMPATIBILIDAD RIP — {os.path.basename(path)} ({os.path.getsize(path)/1e6:.1f} MB)")
    for f in fallas:
        print("    ❌   ", f)
    if "--muestra" in sys.argv:
        import shutil
        dst = os.path.join(os.path.dirname(path), "HOJA_muestra_rip.pdf")
        shutil.copy2(path, dst)
        print("    muestra para la imprenta:", dst)
    print("✅ CONTRATO VERDE — PDF/X-1a-like: lo lee cualquier RIP y el color va incrustado" if ok
          else f"❌ CONTRATO ROTO — {len(fallas)} falla(s)")
    sys.exit(0 if ok else 1)
