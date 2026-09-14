# -*- coding: utf-8 -*-
"""CONTRATO: UN MOLDE DE UNA SOLA MESA SE REPARTE POR TALLE — `py verificar_reparto_por_talle.py`

Llegó un molde armado al revés que los anteriores: en vez de 9 mesas de una pieza, **UNA mesa** de
4,63 m × 1,18 m con las 14 piezas adentro y 20 talles (2,35 M de instrucciones). El camino B
repartía el trabajo **por mesa**, así que ahí no repartía nada: 20 talles en fila en un solo
proceso, 197 s con el usuario esperando en el paso Arte. Ahora, cuando sobran procesos para las
mesas que hay, el trozo de trabajo pasa a ser **(mesa, unos talles)**.

Lo que se prueba:
  1. cómo se parte: el orden se respeta, no se pierde ni se repite un talle, y ningún proceso se
     lleva menos de `_TALLES_POR_PROCESO` (cada uno vuelve a parsear la mesa: con 11 procesos en
     vez de 6 el desplegado tardaba MÁS);
  2. 🔴 `buscar_candidatos_mesa` con un trozo encuentra lo mismo que con todos los talles — el
     bug real de esta tanda: al trozo se le pasaba como «orden» y no reconocía el índice del
     desplegado, devolvía cero candidatos y el molde quedaba SIN etiqueta detectada, en silencio;
  3. repartido == sin repartir: mismas páginas, mismo contenido en cada una, mismos placeholders,
     líneas de corte, etiqueta del archivo y hash de la decisión;
  4. un worker de mesa NO abre otro pool adentro (pools anidados).

⚠️ Trabaja sobre una COPIA temporal y con unos pocos talles para no tardar. No toca `datos/`.
"""
import json
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)

import pikepdf                       # noqa: E402
import pymupdf as fitz               # noqa: E402
import piezas_con_diseno as PD       # noqa: E402

ORIG = sys.argv[1] if len(sys.argv) > 1 else \
    r"C:\Users\user2\Downloads\drive-download-20260914T123733Z-1-001\MOLDES\CAMISETA JUGADOR.ai"
TALLES_PRUEBA = 6                    # con el tope de 3 por proceso, son 2 trozos
FALLOS = []


def ok(cond, msg):
    print(("    OK    " if cond else "    ❌    ") + msg)
    if not cond:
        FALLOS.append(msg)


def desplegar(copia_de, talles, procesos):
    """Despliega una copia y devuelve (índice, contenido de cada página, MB)."""
    tmp = tempfile.mkdtemp(prefix="verif_reparto_")
    C = os.path.join(tmp, "plantilla.ai")
    shutil.copy2(copia_de, C)
    try:
        PD.desplegar_molde(C, talles, procesos=procesos)
        dd = os.path.join(tmp, "desplegado")
        with open(os.path.join(dd, "m1.json"), encoding="utf-8") as fh:
            idx = json.load(fh)
        with pikepdf.open(os.path.join(dd, "m1.pdf")) as pdf:
            paginas = [bytes(pikepdf.unparse_content_stream(list(pikepdf.parse_content_stream(p))))
                       for p in pdf.pages]
        mb = os.path.getsize(os.path.join(dd, "m1.pdf")) / 1e6
        return idx, paginas, mb
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    if not os.path.exists(ORIG):
        print(f"❌ no está el archivo de prueba (un molde de UNA mesa con el diseño adentro):\n   {ORIG}")
        sys.exit(1)

    # ── 1. CÓMO SE PARTE ────────────────────────────────────────────────────────────────────
    print("1 · EL REPARTO: se respeta el orden y nadie se lleva menos de lo que paga el parseo")
    for n_t, procs in ((20, 6), (20, 11), (20, 4), (7, 11), (2, 11), (1, 8)):
        talles = [f"T{i}" for i in range(n_t)]
        tr = PD._trozos_de_talles(talles, procs)
        juntos = [t for x in tr for t in x]
        ok(juntos == talles, f"{n_t} talles en {procs} procesos: no se pierde ni se desordena nada ({[len(x) for x in tr]})")
        if len(tr) > 1:
            ok(min(len(x) for x in tr) >= PD._TALLES_POR_PROCESO or n_t < PD._TALLES_POR_PROCESO * 2,
               f"   …y ningún proceso se lleva menos de {PD._TALLES_POR_PROCESO} talles")
    ok(len(PD._trozos_de_talles([f"T{i}" for i in range(20)], 11)) <= 20 // PD._TALLES_POR_PROCESO,
       "🔴 con 11 procesos y 20 talles NO se abren 11 trozos (medido: tardaba más que con 6)")

    print(f"\ncopiando el archivo ({os.path.getsize(ORIG)/1e6:.0f} MB)…")
    d = fitz.open(ORIG)
    todos = PD.talles_del_molde(d)
    n_mesas = d.page_count
    d.close()
    ok(n_mesas == 1, f"el archivo de prueba es de UNA mesa (tiene {n_mesas})")
    talles = todos[:TALLES_PRUEBA]

    # ── 2. EL TROZO ENCUENTRA LO MISMO QUE LA CORRIDA ENTERA ────────────────────────────────
    print("\n2 · 🔴 UN TROZO DE TALLES ENCUENTRA LAS MISMAS ETIQUETAS QUE LA CORRIDA ENTERA")
    tmp = tempfile.mkdtemp(prefix="verif_cands_")
    try:
        C = os.path.join(tmp, "plantilla.ai")
        shutil.copy2(ORIG, C)
        PD.desplegar_molde(C, talles, procesos=None, contornos=True, paginas=False)
        _m, enteros = PD.buscar_candidatos_mesa(C, 1, list(talles))
        por_trozo = []
        for tr in PD._trozos_de_talles(talles, 2):
            _m, cs = PD.buscar_candidatos_mesa(C, 1, list(tr), list(talles))
            por_trozo.extend(cs)
        clave = (lambda c: (c.get("talle"), c.get("idx"), c.get("texto"), round(float(c.get("alto_mm") or 0), 2)))
        ok(len(enteros) > 0, f"la corrida entera encuentra candidatos ({len(enteros)})")
        ok(sorted(map(clave, enteros)) == sorted(map(clave, por_trozo)),
           f"los trozos encuentran exactamente los mismos ({len(por_trozo)} vs {len(enteros)})")
        # …y sin pasarle el orden del molde, el trozo NO reconoce el índice: ésa fue la falla
        _m, sin_orden = PD.buscar_candidatos_mesa(C, 1, list(talles[:2]))
        ok(sin_orden == [], "sin el orden del molde, un trozo devuelve vacío (por eso hay que pasárselo)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ── 3. REPARTIDO == SIN REPARTIR ────────────────────────────────────────────────────────
    print(f"\n3 · 🔴 REPARTIDO DA LO MISMO QUE SIN REPARTIR ({len(talles)} talles)")
    iS, pS, mS = desplegar(ORIG, talles, None)
    iP, pP, mP = desplegar(ORIG, talles, 6)
    ok(len(pS) == len(talles) and len(pP) == len(pS), f"una página por talle en los dos ({len(pS)} y {len(pP)})")
    ok(pS == pP, "el contenido de cada página es IDÉNTICO")
    for k in ("placeholders", "linea_corte", "etiqueta_archivo", "etq", "orden", "vp", "talles"):
        ok(iS.get(k) == iP.get(k), f"«{k}» igual")
    ok(abs(mP - mS) < max(1.0, 0.05 * mS), f"el PDF no engorda al pegar los trozos ({mS:.1f} MB vs {mP:.1f} MB)")

    # ── 4. NADA DE POOLS ANIDADOS ───────────────────────────────────────────────────────────
    print("\n4 · UN WORKER DE MESA NO ABRE OTRO POOL ADENTRO")
    llamado = []
    orig = PD._POOL_FACTORY
    PD._POOL_FACTORY = lambda max_workers: llamado.append(max_workers)
    try:
        PD._armar_paginas("x.ai", 1, list(talles), {}, [0, 0, 1, 1], 1.0, set(), "x.pdf", None, None)
    except Exception:
        pass                       # va a fallar al abrir «x.ai»: lo que importa es que no hubo pool
    finally:
        PD._POOL_FACTORY = orig
    ok(not llamado, f"sin `procesos` no se abre ningún pool (se abrieron {llamado})")

    print()
    if FALLOS:
        print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
        for f in FALLOS:
            print("   ·", f)
        sys.exit(1)
    print("✅ CONTRATO VERDE — el molde de una mesa se reparte por talle y da exactamente lo mismo")


if __name__ == "__main__":
    main()
