"""ARTE = TIZADA: compara la apariencia REAL del arte (capa Nombre aislada) contra lo que
dibuja el motor, en los DOS ordenes (trazo-encima vs trazo-detras). SOLO LECTURA del arte."""
import sys, fitz
sys.path.insert(0, r"C:\Users\user2\Documents\tincho\codigos\TIZADA PRO")
import motor_pedido as MP
from texto_curvas import FuenteCurvas

SC = r"C:\Users\user2\AppData\Local\Temp\claude\C--Users-user2-Documents-tincho-codigos-TIZADA-PRO\70858909-5b85-41a3-9977-c1b3747e19a2\scratchpad"
ARTE = r"C:\Users\user2\Downloads\rangos 3.ai"
PAG, MESA, CAMPO, TEXTO = 4, "5", "Nombre", "nombre"
DPI = 220

pers = MP.extraer_personalizacion(ARTE)
pl = pers[MESA][CAMPO]
print(f"{CAMPO!r}: size={pl['size']} relleno={pl['colorn']} trazo={pl['trazo']}")

# ── 1) ARTE: solo la capa Nombre visible -> su apariencia sola
doc = fitz.open(ARTE)
for c in doc.layer_ui_configs():
    # PyMuPDF: 0=ON, 1=TOGGLE, 2=OFF (usar 1 para "encender" ALTERNA y apaga lo ya visible)
    doc.set_layer_ui_config(c["number"], action=(0 if MP._norm_nombre(c["text"]) == "nombre" else 2))
page = doc[PAG]
H = page.rect.height
clip = fitz.Rect(pl["cx"] - pl["ancho"] / 2 - 40, pl["baseline_y"] - pl["size"] - 40,
                 pl["cx"] + pl["ancho"] / 2 + 40, pl["baseline_y"] + 40)
m = fitz.Matrix(DPI / 72, DPI / 72)
pa = page.get_pixmap(matrix=m, clip=clip, colorspace=fitz.csRGB, alpha=False)
pa.save(SC + r"\A_arte.png")
print("arte aislado:", pa.width, "x", pa.height)

# ── 2) MOTOR: mismas ops, mismo lugar, los dos ordenes
ruta_f = MP.resolver_fuente(pl["fuente"], r"C:\Users\user2\Documents\tincho\codigos\TIZADA PRO\catalogo_fuentes")
fc = FuenteCurvas(open(ruta_f, "rb").read())
ty = H - pl["baseline_y"]                      # fitz (y abajo) -> PDF (y arriba)
ops = fc.ops_texto(TEXTO, pl["size"], pl["cx"] - fc.ancho_texto(TEXTO, pl["size"]) / 2, ty)
_scol = " ".join(f"{v:g}" for v in pl["trazo"][1]) + " " + pl["trazo"][0].upper()
b_fill = f"q {MP._color_op(pl)}\n{ops}\nf\nQ\n"
b_stroke = f"q {_scol}\n{pl['trazo'][2]:.3f} w 1 j 1 J\n{ops}\nS\nQ\n"

res = {}
for nom, cont in {"ENCIMA": b_fill + b_stroke, "DETRAS": b_stroke + b_fill}.items():
    d2 = fitz.open()
    p2 = d2.new_page(width=page.rect.width, height=H)
    p2.draw_rect(p2.rect, color=None, fill=(1, 1, 1))
    xr = p2.get_contents()[0]
    d2.update_stream(xr, d2.xref_stream(xr) + cont.encode())
    px = d2[0].get_pixmap(matrix=m, clip=clip, colorspace=fitz.csRGB, alpha=False)
    px.save(SC + rf"\B_{nom}.png")
    a, b = pa.samples, px.samples
    dif = sum(1 for i in range(0, min(len(a), len(b)), 3) if abs(a[i] - b[i]) > 40)
    tot = len(a) // 3
    res[nom] = dif
    print(f"  trazo {nom}: {dif}/{tot} px distintos del arte ({100.0*dif/tot:.2f}%)")

g = min(res, key=res.get)
print(f"\nSE PARECE AL ARTE: trazo {g}  (el otro tiene {res[max(res, key=res.get)] - res[g]} px mas de diferencia)")
doc.close()
