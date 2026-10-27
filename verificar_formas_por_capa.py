"""CONTRATO — la forma de cada talle sale de la CAPA con su nombre (MAPA 751).

El usuario subió una forma nueva para «Cambiar pieza» y en el talle L quedó la forma de OTRO talle: las formas
del archivo se repartían por TAMAÑO (de la más chica a la más grande) y no por la capa en la que venían. Ahora
cada contorno trae su capa y cada talle toma la forma de la capa que se llama como él.

Arma un PDF propio (en una carpeta temporal; no toca nada del usuario) con tres capas «S», «M», «L» donde la
forma de la L es MÁS CHICA que la de la M —por tamaño se cruzarían— y una capa «guías» con una marca grande.
Verifica:
  1. Python (`contornos_de_pdf`) y la PC (`contornosDePdf`, Node) leen la MISMA capa para cada contorno.
  2. `formas_por_talle` le da a cada talle la forma de SU capa (no la del tamaño), en todos los talles y
     en algunos elegidos.
  3. Si falta la capa de un talle, lo dice (`faltan`).
  4. Un archivo SIN capas sigue repartiéndose por tamaño, como antes.
"""
import json
import os
import subprocess
import sys
import tempfile

import pikepdf
from pikepdf import Array, Dictionary, Name, Stream

import piezas_molde as PM

AQUI = os.path.dirname(os.path.abspath(__file__))


def _pdf(path, capas):
    """`capas` = [(nombre | None, [(x, y, w, h), …])] → un PDF de una página con cada grupo en su capa."""
    pdf = pikepdf.new()
    ocgs, props, partes = [], Dictionary(), []
    for i, (nom, rects) in enumerate(capas):
        ops = "\n".join(f"{x} {y} m {x + w} {y} l {x + w} {y + h} l {x + w * 0.5} {y + h * 1.2} l {x} {y + h} l h S"
                        for x, y, w, h in rects)
        if nom is None:
            partes.append(f"q 0 0 0 RG 1 w\n{ops}\nQ")
            continue
        o = pdf.make_indirect(Dictionary(Type=Name.OCG, Name=pikepdf.String(nom)))
        ocgs.append(o)
        props[f"/OC{i}"] = o
        partes.append(f"/OC /OC{i} BDC q 0 0 0 RG 1 w\n{ops}\nQ EMC")
    res = Dictionary(Properties=props) if ocgs else Dictionary()
    pagina = Dictionary(Type=Name.Page, MediaBox=Array([0, 0, 1800, 900]), Resources=res,
                        Contents=Stream(pdf, "\n".join(partes).encode()))
    pdf.pages.append(pikepdf.Page(pagina))
    if ocgs:
        pdf.Root.OCProperties = Dictionary(OCGs=Array(ocgs), D=Dictionary(Order=Array(ocgs)))
    pdf.save(path)


def _node(path, tmp):
    out = os.path.join(tmp, "js.json")
    subprocess.run(["node", os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "contornos_capas.mjs"), path, out],
                   check=True, cwd=os.path.join(AQUI, "frontend"))
    with open(out, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    fallas = []
    def ok(cond, txt):
        print(("  OK    " if cond else "  FALLA ") + txt)
        if not cond:
            fallas.append(txt)

    with tempfile.TemporaryDirectory() as tmp:
        # la L más CHICA que la M: por tamaño, M y L se cruzan
        con = os.path.join(tmp, "con_capas.pdf")
        _pdf(con, [("S", [(50, 50, 200, 300)]), ("M", [(500, 50, 300, 400)]),
                   ("L", [(1000, 50, 250, 350), (1100, 100, 20, 20)]),        # + una marca chica adentro de la L
                   ("guías", [(10, 10, 1700, 800)])])
        py = PM.contornos_de_pdf(con)
        js = _node(con, tmp)
        firma = lambda cs: sorted((c.get("capa"), round(c["w"], 1), round(c["h"], 1)) for c in cs)
        ok(firma(py) == firma(js), "Python y la PC leen la misma capa para cada contorno")
        ok({c.get("capa") for c in py} == {"S", "M", "L", "guías"}, "cada contorno trae su capa")

        talles = ["S", "M", "L"]
        asig, modo, faltan = PM.formas_por_talle(py, talles, talles)
        ok(modo == "capas" and not faltan, "con capas se reparte POR CAPA")
        ok(all(asig[t].get("capa") == t for t in talles), "cada talle toma la forma de SU capa (la L no se cruza con la M)")
        ok(round(asig["L"]["w"]) == 250, "la L toma su pieza (la más grande de su capa), no la marca chica")
        asig2, _, _ = PM.formas_por_talle(py, talles, ["L"])
        ok(list(asig2) == ["L"] and asig2["L"].get("capa") == "L", "eligiendo sólo la L, va la de la capa L")

        falta = os.path.join(tmp, "falta.pdf")
        _pdf(falta, [("S", [(50, 50, 200, 300)]), ("M", [(500, 50, 300, 400)])])
        _, modo3, faltan3 = PM.formas_por_talle(PM.contornos_de_pdf(falta), talles, talles)
        ok(modo3 == "capas" and faltan3 == ["L"], "si falta la capa de un talle, lo dice")

        sin = os.path.join(tmp, "sin_capas.pdf")
        _pdf(sin, [(None, [(50, 50, 300, 400), (500, 50, 200, 300), (1000, 50, 250, 350)])])
        asig4, modo4, faltan4 = PM.formas_por_talle(PM.contornos_de_pdf(sin), talles, talles)
        ok(modo4 == "tamaño" and not faltan4 and [round(asig4[t]["w"]) for t in talles] == [200, 250, 300],
           "sin capas sigue repartiendo por tamaño, como antes")

    print("\n" + ("TODO OK" if not fallas else f"{len(fallas)} FALLA/S"))
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
