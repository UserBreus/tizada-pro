"""ESTUDIO DEL SISTEMA — inventario real de cada pantalla, en orden de aparición.

Recorre App.jsx y, para cada bloque de pantalla (paso del pedido / sección de config / pestaña de
ajustes del molde), lista los ELEMENTOS INTERACTIVOS que el usuario ve: botones (con su texto),
campos (con su placeholder/label) y toggles. Sirve para escribir los guiones sobre lo que EXISTE
de verdad, en el orden en que aparece, y no de memoria.
"""
import io, re, sys

RUTA = r'C:\Users\user2\Documents\tincho\codigos\TIZADA PRO\frontend\src\App.jsx'
src = io.open(RUTA, encoding='utf-8').read()
lineas = src.splitlines()

# ── 1) Ubicar el comienzo de cada pantalla ────────────────────────────────────────────────────
MARCAS = []
for i, l in enumerate(lineas):
    for pat, tipo in (
        (r"pedidoPaso === '([a-z]+)'", 'PEDIDO'),
        (r"adminSubView === '([a-z_]+)'", 'CONFIG'),
        (r"tabAjustesMolde === '([a-z]+)'", 'AJUSTE'),
    ):
        m = re.search(pat, l)
        if m and ('&&' in l or '?' in l):
            MARCAS.append((i, tipo, m.group(1)))
MARCAS.sort()

def bloque(ini, fin):
    return '\n'.join(lineas[ini:fin])

def elementos(txt):
    """Elementos interactivos en ORDEN de aparición."""
    out = []
    # texto visible de un <button ...>TEXTO</button> (una línea o con el texto pegado)
    for m in re.finditer(r'<(button|input|textarea|select)\b([^>]*)>', txt):
        tag, attrs = m.group(1), m.group(2)
        tour = re.search(r'data-tour="([^"]+)"', attrs)
        ph = re.search(r'placeholder="([^"]{2,60})"', attrs)
        # texto del botón: lo que sigue hasta </button>
        etiqueta = ''
        if tag == 'button':
            resto = txt[m.end():m.end() + 400]
            t = re.sub(r'<[^>]+>', ' ', resto.split('</button>')[0])
            t = re.sub(r'\{[^{}]*\}', ' ', t)
            etiqueta = ' '.join(t.split())[:46]
        elif ph:
            etiqueta = f'[campo] {ph.group(1)}'
        else:
            etiqueta = f'[{tag}]'
        if not etiqueta.strip():
            continue
        out.append((etiqueta, tour.group(1) if tour else None))
    return out

# ── 2) Reportar ───────────────────────────────────────────────────────────────────────────────
filtro = sys.argv[1] if len(sys.argv) > 1 else None
for n, (ini, tipo, nombre) in enumerate(MARCAS):
    if filtro and filtro.lower() not in f'{tipo}:{nombre}'.lower():
        continue
    fin = MARCAS[n + 1][0] if n + 1 < len(MARCAS) else len(lineas)
    if fin - ini < 6:
        continue
    els = elementos(bloque(ini, fin))
    if not els:
        continue
    print(f'\n══ {tipo} · {nombre}   (linea {ini + 1}, {fin - ini} lineas)')
    vistos = set()
    for et, tour in els[:26]:
        if et in vistos:
            continue
        vistos.add(et)
        marca = f'  [{tour}]' if tour else '   -'
        print(f'   {marca:24} {et}')
