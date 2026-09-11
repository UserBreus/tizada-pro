# -*- coding: utf-8 -*-
"""
CONTRATO: SE OCULTA LA ETIQUETA QUE TRAE EL DISEÑO, Y SÓLO ESA.
Se corre con `py verificar_etiqueta_del_archivo.py [ruta al .ai]`.

EL CASO (pedido del usuario 2026-09-11): *«que el sistema lo detecte y tenga una manera de que
oculte automáticamente la etiqueta que viene en el diseño sin que nos afecte a otros textos que
vengan»*. Un molde con el diseño adentro puede traer la etiqueta de corte ya puesta: un texto chico
con el TALLE, pegado al borde de cada pieza. Si se deja, la prenda sale con DOS.

🔴 **EL TEXTO SOLO NO ALCANZA.** En el molde real (`CAMISETA JUGADOR.ai`) hay DOS textos que dicen
«M» en el mismo talle:
  · la etiqueta de corte → 5,3 mm, a 1,2 mm del borde de la pieza;
  · la TALLA TEJIDA      → 12 mm, en el CENTRO de la piecita «TALLE» (a 26 mm del borde).
La segunda es DISEÑO: es la etiqueta que se cose en la prenda. Borrarla la dejaría sin su talla, y
no fallaría nada — se descubre con la tela cortada. Por eso van TRES condiciones juntas, y la que
separa de verdad es **la distancia al borde**.

Lo que se verifica:
  1. La regla pura (`etiqueta_del_archivo`), caso por caso, sin abrir ningún archivo.
  2. 🔴 La talla tejida NO se toca, ni cuando dice exactamente el talle.
  3. Con el archivo REAL: se saca la etiqueta de las 9 mesas y se dejan el rótulo, la talla tejida
     y los placeholders «00»/«NOMBRE».
  4. La versión del caché subió (si no, un molde ya desplegado seguiría con su etiqueta adentro).

⚠️ No toca datos del usuario: lee el .ai en SOLO LECTURA.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

import piezas_con_diseno as PD                   # noqa: E402

CM = 28.3465
MM = CM / 10.0
FALLOS = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALLA ") + msg)
    if not cond:
        FALLOS.append(msg)


def pieza(x0_cm, y0_cm, x1_cm, y1_cm):
    return {"bbox_mu": (x0_cm * CM, y0_cm * CM, x1_cm * CM, y1_cm * CM)}


# ─────────────────────────────────────────────────────────────────
print("\n1 · LA REGLA, CASO POR CASO (pura, sin abrir nada)")
P = [pieza(0, 0, 50, 70)]                     # una pieza de 50 × 70 cm

ok(PD.etiqueta_del_archivo("M", "M", 25 * CM, 69.8 * CM, 5.3, P) is not None,
   "🔴 la etiqueta de corte: dice el talle, 5,3 mm, a 2 mm del borde inferior → SE SACA")
ok(PD.etiqueta_del_archivo("M", "M", 25 * CM, 70.1 * CM, 5.3, P) is not None,
   "y también si queda 1 mm POR FUERA del contorno — así está en las mangas del molde real")
ok(PD.etiqueta_del_archivo("6XL", "6XL", 0.15 * CM, 35 * CM, 5.3, P) is not None,
   "pegada al borde IZQUIERDO también (no sólo abajo)")

print("\n   lo que NO se toca:")
ok(PD.etiqueta_del_archivo("L", "M", 25 * CM, 69.8 * CM, 5.3, P) is None,
   "un texto que dice OTRO talle (el de otra capa) no se toca")
ok(PD.etiqueta_del_archivo("TALLE M", "M", 25 * CM, 69.8 * CM, 5.3, P) is None,
   "«TALLE M» tampoco: tiene que decir EXACTAMENTE el talle, no contenerlo")
ok(PD.etiqueta_del_archivo("M", "M", 25 * CM, 35 * CM, 5.3, P) is None,
   "🔴 un texto chico que dice el talle pero está en el MEDIO de la pieza: no es de corte")
ok(PD.etiqueta_del_archivo("M", "M", 25 * CM, 69.8 * CM, 12.0, P) is None,
   "🔴 uno pegado al borde pero GRANDE (12 mm): es diseño, no una marca de corte")
ok(PD.etiqueta_del_archivo("M", "M", 25 * CM, 69.8 * CM, 5.3, []) is None,
   "sin contornos no se saca nada (no se adivina)")
ok(PD.etiqueta_del_archivo("M", None, 25 * CM, 69.8 * CM, 5.3, P) is None,
   "sin talle tampoco")
ok(PD.etiqueta_del_archivo("M", "M", 200 * CM, 69.8 * CM, 5.3, P) is None,
   "y un texto lejos de toda pieza, tampoco")

print("\n2 · 🔴 LA TALLA TEJIDA NO SE TOCA (el caso que rompe la regla ingenua)")
# La piecita «TALLE» del molde real: 15,0 × 5,4 cm, con la talla en el centro.
TAG = [pieza(0, 0, 15.0, 5.4)]
ok(PD.etiqueta_del_archivo("M", "M", 7.8 * CM, 2.8 * CM, 12.0, TAG) is None,
   "🔴 la «M» de 12 mm en el centro de la piecita «TALLE» NO se saca — es la que se cose")
ok(PD.etiqueta_del_archivo("M", "M", 7.8 * CM, 2.8 * CM, 5.0, TAG) is None,
   "y aun si fuera chica, el centro está a 26 mm del borde: tampoco")
ok(PD.etiqueta_del_archivo("M", "M", 7.5 * CM, 5.3 * CM, 5.3, TAG) is not None,
   "pero una de corte pegada al borde de ESA misma piecita sí se saca")

print("\n3 · EL ARCHIVO REAL")
ARCH = (sys.argv[1] if len(sys.argv) > 1 else
        r"C:\Users\user2\Downloads\PRUEBA TIZADA PRO\para acomodo de archivos\CAMISETA JUGADOR.ai")
if not os.path.exists(ARCH):
    print(f"    (no está {os.path.basename(ARCH)}: se saltea)")
else:
    import pikepdf                               # noqa: E402
    import pymupdf as fitz                       # noqa: E402
    from pikepdf import parse_content_stream     # noqa: E402

    def textos(pdf, mesa):
        """Todo el texto de una mesa, con su capa, posición y alto. Usa el MISMO decodificador que
        el desplegado (PyMuPDF no ve el «00» de este archivo: ver `_PLACEHOLDERS`)."""
        page = pdf.pages[mesa - 1]
        fuentes = {str(k): v for k, v in ((page.obj.get("/Resources") or {}).get("/Font") or {}).items()}
        mb = [float(v) for v in (page.obj.get("/CropBox") or page.obj.get("/MediaBox"))]
        ctm, pila, capa, pila_capa = [1, 0, 0, 1, 0, 0], [], "", []
        tf, tfs, tm, tlm = None, 1.0, None, None
        out = []
        for inst in parse_content_stream(page):
            op, ops = str(inst.operator), inst.operands
            try:
                if op == "q":
                    pila.append((list(ctm), tf, tfs))
                elif op == "Q":
                    if pila:
                        ctm, tf, tfs = pila.pop(); ctm = list(ctm)
                elif op == "cm":
                    ctm = PD._mul([float(v) for v in ops], ctm)
                elif op in ("BDC", "BMC"):
                    pila_capa.append(capa)
                    if op == "BDC" and len(ops) == 2 and str(ops[0]) == "/OC":
                        try:
                            o = ops[1]
                            if isinstance(o, pikepdf.Name):
                                o = (page.obj.get("/Resources") or {}).get("/Properties", {})[str(o)]
                            capa = str(o.get("/Name")) if o.get("/Name") is not None else capa
                        except Exception:
                            pass
                elif op == "EMC":
                    if pila_capa:
                        capa = pila_capa.pop()
                elif op == "BT":
                    tm = tlm = [1, 0, 0, 1, 0, 0]
                elif op == "ET":
                    tm = tlm = None
                elif op == "Tf":
                    tf, tfs = str(ops[0]), float(ops[1])
                elif op == "Tm":
                    tm = tlm = [float(v) for v in ops]
                elif op in ("Td", "TD"):
                    tlm = PD._mul([1, 0, 0, 1, float(ops[0]), float(ops[1])], tlm or [1, 0, 0, 1, 0, 0])
                    tm = list(tlm)
                elif op in ("Tj", "TJ", "'", '"') and tm is not None:
                    f = fuentes.get(tf)
                    txt = PD._texto_mostrado(op, ops, PD._decodificador(f) if f is not None else None)
                    if not txt.strip():
                        continue
                    m = PD._mul(PD._mul([tfs, 0, 0, tfs, 0, 0], tm), ctm)
                    esc = (m[0] ** 2 + m[1] ** 2) ** 0.5
                    out.append((capa, txt.strip(), m[4] - mb[0], mb[3] - m[5], esc / MM))
            except Exception:
                continue
        return out

    doc = fitz.open(ARCH)
    pdf = pikepdf.open(ARCH)
    talles = PD.talles_del_molde(doc)
    TL = "M" if "M" in talles else talles[len(talles) // 2]
    mesas_con, dejados, sacados = set(), [], []
    for mesa in range(1, len(pdf.pages) + 1):
        conts = PD.piezas_de_mesa(doc, mesa, TL)
        for capa, txt, dx, dy, alto in textos(pdf, mesa):
            if capa != TL:
                continue
            if PD.etiqueta_del_archivo(txt, TL, dx, dy, alto, conts) is not None:
                mesas_con.add(mesa); sacados.append((mesa, txt, alto))
            else:
                dejados.append((mesa, txt, alto))
    print(f"    talle {TL}: se sacan {len(sacados)} textos en {len(mesas_con)} mesa(s); se dejan {len(dejados)}")
    # Las mesas que TRAEN una etiqueta chica con el talle: en todas ésas hay que encontrarla. No se
    # afirma «en las 9»: la mesa de la talla tejida (la piecita «TALLE») no trae etiqueta de corte,
    # su único texto con el talle es la talla de 12 mm que va cosida y NO se toca.
    candidatas = {m for m, t, a in sacados} | {m for m, t, a in dejados
                                               if t == TL and a <= PD._ETQ_ALTO_MAX_MM}
    ok(mesas_con == candidatas,
       f"🔴 se encuentra en TODAS las mesas que la traen: {len(mesas_con)} de {len(candidatas)} "
       f"(las que no: {sorted(set(range(1, len(pdf.pages) + 1)) - candidatas)} — la de la talla tejida)")
    ok(len(mesas_con) >= len(pdf.pages) - 1,
       f"y son casi todas las mesas del molde ({len(mesas_con)} de {len(pdf.pages)})")
    ok(all(t == TL for _m, t, _a in sacados),
       "y todo lo que se saca dice exactamente el talle")
    _tag = [(m, t, a) for m, t, a in dejados if t == TL]
    ok(any(a > 10 for _m, _t, a in _tag),
       f"🔴 la talla TEJIDA queda: dice «{TL}» pero mide {max([a for _m,_t,a in _tag] or [0]):.1f} mm y está en el centro")
    ok(any(t in ("ESPALDA", "FRENTE", "TALLE") for _m, t, _a in dejados),
       "los rótulos de la mesa (ESPALDA, FRENTE, TALLE…) quedan")
    ok(any(t in ("NOMBRE", "00") for _m, t, _a in dejados),
       "y los placeholders «NOMBRE»/«00» quedan para el camino que les corresponde")
    PD.olvidar(doc); doc.close(); pdf.close()

print("\n4 · LA VERSIÓN DEL CACHÉ SUBIÓ")
# Un molde ya desplegado tiene su PDF por talle escrito CON la etiqueta adentro. Sin subir la
# versión, se seguiría usando ese y el arreglo no llegaría nunca.
ok(PD._V_PAGINAS >= 4, f"`_V_PAGINAS` = {PD._V_PAGINAS} (≥ 4: rehace las páginas de los moldes viejos)")
_src = open(os.path.join(RAIZ, "piezas_con_diseno.py"), encoding="utf-8").read()
ok('"etiqueta_archivo": etq_archivo' in _src, "lo detectado se guarda en el `m{mesa}.json`")
ok("def piezas_con_etiqueta_propia" in _src, "y hay cómo contarlo para avisarlo en pantalla")
_app = open(os.path.join(RAIZ, "frontend", "src", "App.jsx"), encoding="utf-8").read()
ok("etiquetas_en_archivo" in _app, "🔴 la pantalla lo avisa (nunca se oculta en silencio)")

print()
if FALLOS:
    print(f"  {len(FALLOS)} FALLO(S)")
    sys.exit(1)
print("  OK: se oculta la etiqueta del diseño, y sólo esa")
