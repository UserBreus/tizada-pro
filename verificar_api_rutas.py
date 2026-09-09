# -*- coding: utf-8 -*-
"""CONTRATO DE `API_RUTAS.md` — `py verificar_api_rutas.py`

El documento dice «Generado automáticamente del código», y durante meses NO lo estuvo: el
generador no vivía en el repo. Al unir las dos ramas (2026-09-09) le faltaban **30 rutas** y le
sobraba una que ya no existía. Un índice de endpoints que miente por omisión es peor que no
tenerlo: se busca una ruta, no está, y se escribe otra igual con otro nombre.

Lo que se cuida:
  1. Toda ruta del código está en el documento.
  2. Toda fila del documento existe en el código.
  3. El total que declara el encabezado es el número de filas de verdad.

Si falla, se arregla solo: `py generar_api_rutas.py --escribir` (mirá antes el listado sin
`--escribir`, que no toca nada).

No abre la base ni toca datos: sólo lee `servidor.py`, `api_usuarios.py` y el .md.
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)

import generar_api_rutas as G   # noqa: E402

FALLOS = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALLA ") + msg)
    if not cond:
        FALLOS.append(msg)


print("CONTRATO DE API_RUTAS.md\n")
codigo = set(G.rutas_del_codigo())
lineas, donde, _sec = G.leer_doc()
doc = set(donde)

faltan = sorted(codigo - doc, key=lambda k: (k[1], k[0]))
sobran = sorted(doc - codigo, key=lambda k: (k[1], k[0]))
print(f"  rutas en el código: {len(codigo)} · filas en el documento: {len(doc)}")

ok(not faltan, "toda ruta del código figura en el documento"
   + ("" if not faltan else f" — faltan {len(faltan)}: "
      + ", ".join(f"{m} {r}" for m, r in faltan[:8]) + ("…" if len(faltan) > 8 else "")))
ok(not sobran, "toda fila del documento existe en el código"
   + ("" if not sobran else f" — sobran {len(sobran)}: "
      + ", ".join(f"{m} {r}" for m, r in sobran[:8]) + ("…" if len(sobran) > 8 else "")))

m = re.search(r"Total: \*\*(\d+) endpoints\*\*", "\n".join(lineas))
ok(bool(m) and int(m.group(1)) == len(doc),
   f"el total del encabezado coincide con las filas ({m and m.group(1)} vs {len(doc)})")

print()
if FALLOS:
    print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s). Se arregla con:")
    print("     py generar_api_rutas.py            (para ver qué cambiaría)")
    print("     py generar_api_rutas.py --escribir (para aplicarlo)")
    sys.exit(1)
print("✅ CONTRATO VERDE — el índice de endpoints dice la verdad")
