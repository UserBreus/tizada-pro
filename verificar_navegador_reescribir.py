# -*- coding: utf-8 -*-
"""
CONTRATO: EL NAVEGADOR REESCRIBE LAS INSTRUCCIONES CON LOS MISMOS BYTES QUE PIKEPDF — `py verificar_navegador_reescribir.py [molde.ai ...]`

PLAN_NAVEGADOR.md, etapa 1. Las páginas por talle del desplegado se escriben con
`pikepdf.unparse_content_stream`; en el navegador, con `escribir` de
`frontend/src/motor/pdf/contenido.js`. Si los bytes son los mismos, la página del navegador es la
del servidor. Se prueba sobre cada trozo de capa (`cortar_capas`) de los moldes reales y sobre un
caso armado con los tokens raros (textos con controles y paréntesis, nombres con #xx, reales
«.5»/«4.», enteros «-0»/«+3», diccionarios, arreglos vacíos).
"""
import glob
import os
import struct
import subprocess
import sys
import tempfile

import pikepdf

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import cortar_capas as CC  # noqa: E402

NODE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "reescribir.mjs")
RAROS = (b"q 1 0 0 1 -2.5 .5 cm /OC /MC0 BDC (a\\(b\\)\n\\101\\351\x01) Tj <48 65> Tj [(x) -120 (y)] TJ "
         b"/F1 12 Tf /N#20a#2Fb gs << /MCID 3 /A [1 2 ] >> BDC EMC 0 Tr 1.000 -0 +3 4. -.25 re Q "
         b"(\x80\x81\x82\x83abc) Tj (\x07) Tj [] TJ (a\\\\b\tc\x7f\x9f\xa0) Tj true false null d0")


def comparar_trozos(trozos):
    tmp = tempfile.mkdtemp(prefix="verif_reesc_")
    ent, sal = os.path.join(tmp, "e.bin"), os.path.join(tmp, "s.bin")
    with open(ent, "wb") as fh:
        for t in trozos:
            fh.write(struct.pack("<Q", len(t)))
            fh.write(t)
    r = subprocess.run(["node", "--max-old-space-size=8192", NODE, ent, sal], capture_output=True, text=True, timeout=3600)
    if r.returncode != 0:
        return None, f"Node falló: {r.stderr[-600:]}"
    data = open(sal, "rb").read()
    p, malos, ejemplo = 0, 0, None
    for i, t in enumerate(trozos):
        (n,) = struct.unpack_from("<Q", data, p)
        p += 8
        js = data[p:p + n]
        p += n
        py = pikepdf.unparse_content_stream(CC.instrucciones(t))
        if js != py:
            malos += 1
            if ejemplo is None:
                k = next((j for j in range(min(len(js), len(py))) if js[j] != py[j]), min(len(js), len(py)))
                ejemplo = f"trozo {i}, byte {k}: servidor {py[max(0, k - 40):k + 40]!r} · navegador {js[max(0, k - 40):k + 40]!r}"
    os.remove(ent)
    os.remove(sal)
    return malos, ejemplo


def moldes_por_defecto():
    out = [p for p in sorted(glob.glob(os.path.join(AQUI, "entrada", "*", "plantilla.ai")))
           if os.path.isdir(os.path.join(os.path.dirname(p), "desplegado"))]
    return out + sorted(glob.glob(os.path.join(AQUI, "laboratorio", "*.ai")))


if __name__ == "__main__":
    ok_todo = True
    malos, ej = comparar_trozos([RAROS])
    print(f"· tokens raros: {'✓ mismos bytes' if malos == 0 else '✗ ' + str(ej)}")
    ok_todo = ok_todo and malos == 0
    for path in (sys.argv[1:] or moldes_por_defecto()):
        pdf = pikepdf.open(path)
        trozos = []
        for pag in pdf.pages:
            corte = CC.cortar(pag)
            trozos += [x[1] for x in corte["trozos"]] if corte else [CC.contenido_crudo(pag)]
        malos, ej = comparar_trozos(trozos)
        ok = malos == 0
        print(f"· {os.path.basename(path)}: {len(trozos)} trozos · " + ("✓ mismos bytes" if ok else f"✗ {malos} distintos · {ej}"))
        ok_todo = ok_todo and ok
        pdf.close()
    print()
    print("✅ CONTRATO VERDE — el navegador reescribe con los mismos bytes que pikepdf" if ok_todo
          else "❌ CONTRATO ROTO — los bytes difieren")
    sys.exit(0 if ok_todo else 1)
