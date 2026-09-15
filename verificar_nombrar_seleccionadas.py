# -*- coding: utf-8 -*-
"""CONTRATO: NOMBRAR PIEZAS TOCA SÓLO LO SELECCIONADO — `py verificar_nombrar_seleccionadas.py`

Regla del usuario (2026-09-15), textual: *«si yo selecciono una, o 5 o 10 piezas nombrara esas»*.

Lo que estaba mal: el paso «Nombrar» renumeraba TODO el nombre genérico 1..N en cada gesto. Con
dos piezas parecidas —dos mangas, dos costadillos— pasaba esto: nombraba una «Manga»; al nombrar
la otra, también «Manga», la PRIMERA (no seleccionada) se convertía sola en «Manga 1». Desde la
pantalla se veía como que el sistema «renombraba la pieza equivocada».

Este contrato NO lee el código buscando palabras: **saca la función real de `App.jsx` y la
EJECUTA** con node sobre escenarios concretos. Si alguien vuelve a renumerar de más, falla.
"""
import io
import json
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(AQUI, "frontend", "src", "App.jsx")

CASOS = [
    # (titulo, nombres_previos, generico, idxs_tocados, esperado)
    ("la primera pieza se llama como se escribió",
     {}, "Manga", [3], {"3": "Manga"}),
    ("nombrar la SEGUNDA no le cambia el nombre a la primera",
     {"3": "Manga"}, "Manga", [7], {"3": "Manga", "7": "Manga 1"}),
    ("nombrar 3 juntas: las tres quedan, y lo de antes intacto",
     {"3": "Manga"}, "Manga", [7, 9, 11],
     {"3": "Manga", "7": "Manga 1", "9": "Manga 2", "11": "Manga 3"}),
    ("otro nombre genérico no se toca",
     {"1": "Frente", "3": "Manga"}, "Manga", [7],
     {"1": "Frente", "3": "Manga", "7": "Manga 1"}),
    ("quitarle el nombre a una NO renumera a las demás",
     {"3": "Manga", "7": "Manga 1", "9": "Manga 2"}, "Manga", [7],
     {"3": "Manga", "7": "", "9": "Manga 2"}),
    ("un número libre del medio se reusa, sin tocar a nadie",
     {"3": "Manga", "9": "Manga 2"}, "Manga", [7],
     {"3": "Manga", "7": "Manga 1", "9": "Manga 2"}),
]


def _sacar_funcion():
    """El texto de `_numerarTocadas` tal como está en App.jsx (sin copiarlo acá: si el contrato
    tuviera su propia copia, verificaría su copia y no lo que corre en la pantalla)."""
    src = io.open(APP, encoding="utf-8").read()
    if "_renumerar(" in src:
        return None, ("`_renumerar` volvió a App.jsx: esa función renumeraba TODO el genérico "
                      "y le cambiaba el nombre a piezas que el usuario no había seleccionado")
    m = re.search(r"\n  const _numerarTocadas = \(obj, gen, idxs\) => \{.*?\n  \};", src, re.S)
    if not m:
        return None, "no encontré `_numerarTocadas` en App.jsx (¿la renombraron?)"
    gen = re.search(r"\n  const nombreGenerico = .*?;", src, re.S)
    if not gen:
        return None, "no encontré `nombreGenerico` en App.jsx"
    return (gen.group(0) + m.group(0)), None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("CONTRATO — NOMBRAR PIEZAS TOCA SÓLO LO SELECCIONADO")
    fn, err = _sacar_funcion()
    if err:
        print("    ❌   ", err)
        print("❌ CONTRATO ROTO")
        return 1
    js = (fn.replace("\n  const ", "\nconst ")
          + "\nconst casos = " + json.dumps([[c[1], c[2], c[3]] for c in CASOS], ensure_ascii=False)
          + ";\nconsole.log(JSON.stringify(casos.map(([obj, gen, idxs]) => "
            "{ const o = { ...obj }; idxs.forEach(i => { o[i] = (o[String(i)] && "
            "nombreGenerico(o[String(i)]) === gen) ? '' : gen; }); "
            "return _numerarTocadas(o, gen, idxs); })));")
    try:
        r = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=60,
                           encoding="utf-8", errors="replace")
    except FileNotFoundError:
        print("    ❌    no está node en el PATH: sin él no se puede ejecutar la función real")
        print("❌ CONTRATO ROTO")
        return 1
    if r.returncode != 0:
        print("    ❌    node no pudo ejecutar la función:", (r.stderr or "").strip()[:300])
        print("❌ CONTRATO ROTO")
        return 1
    salidas = json.loads(r.stdout)
    fallas = 0
    for (titulo, previos, gen, idxs, esperado), obtenido in zip(CASOS, salidas):
        # el escenario «quitar» deja "" y JS no lo serializa distinto: se compara tal cual
        ok = {k: v for k, v in obtenido.items()} == esperado
        print(("    ✅    " if ok else "    ❌    ") + titulo)
        if not ok:
            fallas += 1
            print(f"            antes={previos}  tocadas={idxs}")
            print(f"            esperado={esperado}")
            print(f"            quedó   ={obtenido}")
    print("✅ CONTRATO VERDE — se nombra lo seleccionado y nada más" if not fallas
          else f"❌ CONTRATO ROTO — {fallas} caso(s)")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
