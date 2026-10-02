# Pasa un arte por las MISMAS funciones del motor de TIZADA PRO que leen el arte, para ver qué
# entiende de un PDF de Corel frente a uno de Illustrator. Solo lectura, sobre COPIAS en el scratchpad.
import sys, json, fitz
sys.path.insert(0, r"C:\Users\user2\Documents\tincho\codigos\TIZADA PRO")
import motor_pedido as MP

def corto(x, n=600):
    s = json.dumps(x, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + "…"

for ruta in sys.argv[1:]:
    print("\n##########", ruta)
    doc = fitz.open(ruta)
    print("orden de capas (barra):", MP._orden_capas_archivo(doc))
    print("texto de mesa por página:", [MP._texto_mesa(doc, i) if True else None for i in range(min(doc.page_count, 4))])
    for nombre, fn in [("fuentes", lambda: MP.fuentes_requeridas_arte(ruta)),
                       ("personalización", lambda: MP.extraer_personalizacion(ruta)),
                       ("colores pers.", lambda: MP._colores_personalizable(ruta)),
                       ("trazo pers.", lambda: MP._trazo_personalizable(ruta)),
                       ("pasadas pers.", lambda: MP._pasadas_personalizable(ruta)),
                       ("editables", lambda: MP.extraer_editables(ruta, con_thumb=False)),
                       ("recolorables", lambda: MP.editables_recolorables(ruta))]:
        try:
            print(f"{nombre}:", corto(fn()))
        except Exception as e:
            print(f"{nombre}: ERROR {type(e).__name__}: {e}")
