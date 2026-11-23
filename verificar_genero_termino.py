# -*- coding: utf-8 -*-
"""
CONTRATO: EL TÉRMINO DE LA VARIANTE SE DICE IGUAL EN LA PANTALLA Y EN EL SERVIDOR — `py verificar_genero_termino.py`

MAPA 776-780. El usuario elige cómo se llama la variante del molde («Talle», «Talla», «Color», «Imagen»…) y las
frases llevan su artículo y su plural: en la pantalla `generoTerm`/`pluralTerm` (frontend/src/App.jsx) y en los
errores del servidor `_genero_es`/`_plural_es` (servidor.py, gemelos). El inspector encontró que el gemelo corto
del servidor daba «imagenes», «3 mes», «la avión» mientras la pantalla decía bien. Este contrato corre los DOS con
las mismas palabras y exige el mismo resultado, más unos casos fijos que tienen que salir así.

⚠️ No toca nada del usuario: el servidor se importa con el entorno aislado de los otros contratos (doble de `db`).
"""
import json
import os
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import verificar_navegador_tizada as VT       # noqa: E402  (entorno aislado: temporal + doble de `db`)

S, ok, FALLOS = VT.S, VT.ok, VT.FALLOS
PALABRAS = ["Talle", "Talla", "Variante", "Color", "Imagen", "Edad", "Combinación", "Tema", "Mes", "Compás", "Lunes",
            "Versión", "Serie", "Tamaño", "Medida", "Pie", "Mano", "Foto", "Examen", "Joven", "Menú", "Avión", "Base",
            "Tesis", "Luz", "Modelo", "Opción"]
FIJOS = {"talle": ("el", "talles"), "talla": ("la", "tallas"), "color": ("el", "colores"), "imagen": ("la", "imágenes"),
         "edad": ("la", "edades"), "tema": ("el", "temas"), "mes": ("el", "meses"), "avión": ("el", "aviones"),
         "lunes": ("el", "lunes"), "opción": ("la", "opciones"), "menú": ("el", "menús")}


def main():
    app = open(os.path.join(AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
    i = app.index("const _FEMENINOS")
    j = app.index("function pluralTerm(")
    k = app.index("\n}\n", j) + 3
    # El tramo usa `PALABRAS_INGLES` y `ERRORES_NAVEGADOR` (el vocabulario y los errores de los mensajes del navegador, MAPA 818): se importa del
    # mismo archivo que la pantalla, si no el tramo suelto no corre.
    _err = pathlib.Path(AQUI, "frontend", "src", "erroresNavegador.js").as_uri()
    js = f"import {{ PALABRAS_INGLES, ERRORES_NAVEGADOR }} from '{_err}';\n" + app[i:k] + "\nconst r = {};\nfor (const w of %s) { const g = generoTerm(w); r[w.toLowerCase()] = [g.la, g.pl, g.los, g.todos, g.un, g.ninguno]; }\nconsole.log(JSON.stringify(r));\n" % json.dumps(PALABRAS)
    out = subprocess.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True, encoding="utf-8")
    ok(out.returncode == 0, f"la pantalla (`generoTerm` de App.jsx) corre aparte {out.stderr[-300:] if out.returncode else ''}")
    if out.returncode:
        return
    pantalla = json.loads(out.stdout.strip().splitlines()[-1])
    for w in PALABRAS:
        g = S._genero_es(w)
        srv = [g["la"], g["pl"], g["los"], g["todos"], g["un"], g["ninguno"]]
        ok(srv == pantalla[w.lower()], f"«{w}»: pantalla {pantalla[w.lower()]} = servidor {srv}")
    for w, (la, pl) in FIJOS.items():
        ok(pantalla[w][:2] == [la, pl], f"«{w}» → «{la} {w}», «{pl}» (sale {pantalla[w][:2]})")
    ok(S._cuantos(1, "fila") == "1 fila" and S._cuantos(3, "fila") == "3 filas" and S._cuantos(2, "acción") == "2 acciones",
       "`_cuantos`: «1 fila», «3 filas», «2 acciones»")
    # ninguna «(s)» ni «/s» en lo que lee la persona (avisos y errores del servidor)
    # (todos los .py del servidor: los errores de `api_usuarios.py` y la consola que se ve en «Registro del sistema»)
    malos = []
    for f in sorted(os.listdir(AQUI)):
        if not f.endswith(".py") or f.startswith("verificar_"):
            continue
        for n, l in enumerate(open(os.path.join(AQUI, f), encoding="utf-8", errors="replace").read().splitlines(), 1):
            if not l.strip().startswith("#") and re.search(r'f?"[^"\n]*\b[a-záéíóúñ]{3,}(\(s\)|\(es\)|/s|/es)\b[^"\n]*"', l):
                malos.append(f"{f}:{n} {l.strip()[:70]}")
    ok(not malos, f"el servidor no dice «(s)» ni «/s» en sus textos ({malos[:3]})")
    # «ningún» va delante del sustantivo; delante de «de los …» va el pronombre «ninguno» (inspector, MAPA 781)
    srv = open(os.path.join(AQUI, "servidor.py"), encoding="utf-8").read()
    ok("['ningun'].capitalize()} de" not in srv, "«Ninguno de los …», no «Ningún de los …»")


if __name__ == "__main__":
    import shutil
    try:
        main()
    finally:
        shutil.rmtree(VT._TMP, ignore_errors=True)
    if FALLOS:
        print(f"\n❌ CONTRATO ROJO — {len(FALLOS)} falla(s)")
        sys.exit(1)
    print("\n✅ CONTRATO VERDE — el término se dice igual en la pantalla y en el servidor")
