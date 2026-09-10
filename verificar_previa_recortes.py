# -*- coding: utf-8 -*-
"""
CONTRATO: EN LA VISTA PREVIA, CADA PIEZA SE RECORTA CON SU PROPIA SILUETA.
Se corre con `py verificar_previa_recortes.py`.

EL BUG (reporte del usuario 2026-09-10, con dos capturas: *«hay piezas que quedan cortadas y el
diseño del arte en piezas que no van»*, *«sigue pasando el mismo error de mierda»*).

La vista previa mete el dibujo de cada base en un `<symbol>` y lo repite con `<use>`. PyMuPDF
numera sus recortes desde cero en CADA documento (`id="cp0"`), así que a cada símbolo se le pone un
prefijo — hasta ahí, bien. El problema era **de dónde salía el número del prefijo**: de
`len(ids) + 1`, e `ids` **arranca de cero en cada página de la hoja**. Pero el contenido de los
símbolos se cachea ENTRE PÁGINAS (`simbolos`) con el prefijo ya escrito adentro.

Entonces, en la hoja 2, una base distinta recibe un prefijo que otra ya usó → **dos `clipPath` con
el mismo id**. En un navegador gana el primero: la pieza se recorta con la silueta de OTRA. En la
tizada del usuario, una tira salía con la loma de una manga adentro y media blanca.

🔴 **La familia del error es la peor: NO FALLA.** El PDF de la tizada sale bien —ahí el recorte es
de verdad—; lo que miente es **lo único que el usuario mira para aprobar el trabajo**.

⚠️ Y ojo con cómo se verifica: **PyMuPDF NO respeta los `clipPath` al dibujar un SVG** (comprobado:
un recorte a la mitad pinta el 100 %). Rasterizar la previa con PyMuPDF muestra rectángulos SIEMPRE,
tenga o no el bug — por eso acá se verifica la ESTRUCTURA del SVG (ids repetidos), que es exacta y
no depende de ningún dibujante. Para mirarlo con los ojos hay que abrirlo en un navegador.

No toca datos del usuario: arma sus propias bases de mentira.
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from hoja_pike import preview_svg                      # noqa: E402

FALLOS = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALLA ") + msg)
    if not cond:
        FALLOS.append(msg)


def ids_repetidos(svg):
    vistos, rep = set(), []
    for i in re.findall(r'<clipPath id="([^"]+)"', svg):
        (rep.append(i) if i in vistos else vistos.add(i))
    return rep


# Una base de mentira: lo mínimo que `preview_svg` le pide (medidas) — el dibujo se le pasa hecho
# por `crudos`, así no hace falta ningún PDF.
def base(nombre):
    return {"W": 100.0, "B": 0.0, "Hp": 200.0, "pieza": nombre}


def crudo(nombre):
    """Lo que devolvería PyMuPDF para esa base: un recorte con SU silueta. Los ids arrancan en
    «cp0» en todos, que es justamente por lo que hace falta el prefijo."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="200">'
            f'<defs><clipPath id="cp0"><path d="M0 0 L100 0 L50 200 Z" data-de="{nombre}"/></clipPath></defs>'
            f'<g clip-path="url(#cp0)"><rect width="100" height="200" fill="#f00"/></g></svg>')


def coloc(b, x, y):
    return {"pieza": {"base": b, "estampado": ""}, "cx": x, "cy": y, "ang": 0.0,
            "bw": 100.0, "bh": 200.0}


CFG = {"ancho_cm": 180.0, "margenes_cm": {"izq": 1.0, "der": 1.0, "sup": 1.0, "inf": 1.0}}

# ─────────────────────────────────────────────────────────────────
print("\n1 · 🔴 EL CASO DEL USUARIO: la misma base en DOS páginas de la hoja")
# Página 1: A y B.  Página 2: C y A otra vez.
# Con el número por página, en la 2 «C» agarraba el prefijo B1 y «A» venía cacheada con B1 → dos
# clipPath con el mismo id, y C terminaba recortada con la silueta de A.
A, B, C = base("Frente"), base("Espalda"), base("Tapa costura")
CRUDOS = {id(A): crudo("Frente"), id(B): crudo("Espalda"), id(C): crudo("TapaCostura")}
simbolos = {}
pag1 = preview_svg([coloc(A, 100, 200), coloc(B, 300, 200)], CFG, 900.0, simbolos, None, crudos=CRUDOS)
pag2 = preview_svg([coloc(C, 100, 200), coloc(A, 300, 200)], CFG, 900.0, simbolos, None, crudos=CRUDOS)

ok(not ids_repetidos(pag1), f"la página 1 no repite ids de recorte ({ids_repetidos(pag1)})")
ok(not ids_repetidos(pag2),
   f"🔴 la página 2 TAMPOCO — que es donde se rompía ({ids_repetidos(pag2)})")

# y cada recorte sigue siendo el de SU pieza
for pag, nombre, quien in ((pag2, "TapaCostura", "la tira"), (pag2, "Frente", "el frente")):
    m = re.search(rf'<clipPath id="([^"]+)">\s*<path[^>]*data-de="{nombre}"', pag)
    ok(bool(m), f"{quien} conserva su propio recorte en la página 2")

print("\n2 · EL PREFIJO ES DE LA BASE, NO DE SU LUGAR EN LA PÁGINA")
# La misma base tiene que usar el MISMO símbolo en todas las páginas: si cambiara de nombre entre
# páginas, el <use> de una apuntaría al símbolo de otra.
def sid_de(pag, nombre):
    m = re.search(rf'<symbol id="([^"]+)"[^>]*>(?:(?!</symbol>).)*?data-de="{nombre}"', pag, re.S)
    return m.group(1) if m else None


ok(sid_de(pag1, "Frente") == sid_de(pag2, "Frente"),
   f"«Frente» se llama igual en las dos páginas ({sid_de(pag1, 'Frente')})")
ok(sid_de(pag2, "TapaCostura") not in (sid_de(pag1, "Frente"), sid_de(pag1, "Espalda")),
   f"y la tira, que aparece recién en la página 2, NO reusa un nombre ya usado "
   f"({sid_de(pag2, 'TapaCostura')})")

print("\n3 · LO QUE NO SE ROMPE")
usos1 = set(re.findall(r'<use href="#([^"]+)"', pag1))
defs1 = set(re.findall(r'<symbol id="([^"]+)"', pag1))
ok(usos1 <= defs1, f"cada `use` de la página 1 apunta a un símbolo que está en esa página ({usos1 - defs1})")
usos2 = set(re.findall(r'<use href="#([^"]+)"', pag2))
defs2 = set(re.findall(r'<symbol id="([^"]+)"', pag2))
ok(usos2 <= defs2,
   f"🔴 y los de la página 2 también — el símbolo se re-emite en cada página ({usos2 - defs2})")
ok(pag2.count("<symbol") == 2, f"la página 2 trae sus dos símbolos ({pag2.count('<symbol')})")

print("\n4 · LAS PREVIAS QUE HAY EN `trabajos/` (informativo, no falla)")
# 🔴 ACÁ SE VIO EL BUG DE VERDAD, y por eso se mira: las previas del pedido del usuario
# (2026-09-10) traían hasta **15 ids de recorte repetidos**. Una previa generada ANTES del arreglo
# los sigue teniendo —el archivo ya está escrito—, así que esto NO puede hacer fallar el contrato:
# se informa, y se arregla volviendo a generar el pedido.
import glob                                                    # noqa: E402
previas = sorted(glob.glob(os.path.join(RAIZ, "trabajos", "*", "prev_*.svg")), key=os.path.getmtime)
if previas:
    con_lio = []
    for p in previas[-12:]:
        with open(p, encoding="utf-8") as fh:
            rep = ids_repetidos(fh.read())
        if rep:
            con_lio.append((os.path.basename(os.path.dirname(p)), os.path.basename(p), len(rep)))
    print(f"    miradas las {len(previas[-12:])} más nuevas")
    if con_lio:
        for t, f, n in con_lio[-4:]:
            print(f"      · {t}/{f}: {n} ids repetidos  ← generada ANTES del arreglo")
        print("      Volvé a generar el pedido y se van.")
    else:
        print("      ninguna repite ids: están todas bien")
else:
    print("    (no hay previas generadas: se saltea)")

print()
if FALLOS:
    print(f"  {len(FALLOS)} FALLO(S)")
    sys.exit(1)
print("  OK: en la previa, cada pieza se recorta con su propia silueta")
