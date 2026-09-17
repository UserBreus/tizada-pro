# -*- coding: utf-8 -*-
"""
LABORATORIO «lo pesado en el navegador» — la REFERENCIA del servidor (PLAN_NAVEGADOR.md, etapa 0).

    py laboratorio_navegador.py <molde.ai> [<salida.json>]

Escribe, por mesa, lo que el servidor ve en el molde: cuántos dibujos da
`get_cdrawings(extended=True)`, el SHA-1 de los bytes del contenido y cuántas instrucciones tiene.
La página `frontend/laboratorio.html` abre el MISMO archivo en el navegador (mupdf.js, en un
worker), calcula lo mismo, mide tiempo y memoria y lo compara con esto.

La comparación completa, número a número, la hacen los contratos
`verificar_navegador_dibujos.py`, `verificar_navegador_contenido.py` y
`verificar_navegador_render.py` (en Node, que corre el mismo código que el navegador). El
laboratorio confirma que en un NAVEGADOR de verdad da lo mismo y cuánto tarda y pesa.
"""
import hashlib
import json
import os
import sys
import time

import pikepdf
import pymupdf as fitz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cortar_capas as CC  # noqa: E402


def referencia(path):
    doc = fitz.open(path)
    pdf = pikepdf.open(path)
    mesas = []
    for i in range(doc.page_count):
        t = time.time()
        n_dib = len(doc[i].get_cdrawings(extended=True))
        t_dib = time.time() - t
        pag = pdf.pages[i]
        crudo = CC.contenido_crudo(pag)
        corte = CC.cortar(pag)
        trozos = [x[1] for x in corte["trozos"]] if corte else [crudo]
        n_ins = sum(sum(1 for _ in CC.instrucciones(tr)) for tr in trozos)
        mesas.append({"mesa": i + 1, "dibujos": n_dib, "segundos_dibujos": round(t_dib, 3),
                      "bytes": len(crudo), "sha1": hashlib.sha1(crudo).hexdigest(), "instrucciones": n_ins})
    return {"archivo": os.path.basename(path), "bytes": os.path.getsize(path), "mesas": mesas,
            "pymupdf": fitz.__version__, "mupdf": fitz.VersionFitz}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    p = sys.argv[1]
    salida = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(p)[0] + ".referencia.json"
    ref = referencia(p)
    with open(salida + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(ref, fh, ensure_ascii=False)
    os.replace(salida + ".tmp", salida)
    print(f"{salida}: {len(ref['mesas'])} mesa(s)")
