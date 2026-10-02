# «Foto» de cómo el motor de TIZADA PRO lee cada arte/molde REAL: se guarda en un JSON para
# comparar ANTES y DESPUÉS de adaptar los lectores a Corel. Con Illustrator tiene que dar IDÉNTICO.
# Solo lectura: usa las funciones «crudas» (sin memo en disco) y no escribe nada en entrada/.
import sys, json, glob, os, fitz
REPO = r"C:\Users\user2\Documents\tincho\codigos\TIZADA PRO"
sys.path.insert(0, REPO)
import motor_pedido as MP, piezas_con_diseno as PB

salida = sys.argv[1]
extra = sys.argv[2:]
artes = sorted(glob.glob(os.path.join(REPO, "entrada", "*", "arte.ai")) +
               glob.glob(os.path.join(REPO, "entrada", "*", "disenos", "*", "arte.ai")) +
               [os.path.join(REPO, "diseño plantilla 2.ai"), os.path.join(REPO, "scratchpad", "arte_concentrico.ai"),
                os.path.join(REPO, "scratchpad", "arte_prueba.ai")] + [e for e in extra if "arte" in os.path.basename(e)])
moldes = sorted(glob.glob(os.path.join(REPO, "entrada", "*", "plantilla.ai")) +
                [os.path.join(REPO, "scratchpad", "buzo", "plantilla.ai")] + [e for e in extra if "molde" in os.path.basename(e)])

def j(x):
    return json.loads(json.dumps(x, ensure_ascii=False, default=lambda o: sorted(o) if isinstance(o, set) else str(o)))

def prueba(fn):
    try:
        return j(fn())
    except Exception as e:
        return f"ERROR {type(e).__name__}: {e}"

foto = {}
for a in artes:
    if not os.path.exists(a):
        continue
    doc = fitz.open(a)
    foto["ARTE " + os.path.relpath(a, REPO)] = {
        "orden": prueba(lambda: MP._orden_capas_archivo(doc)),
        "fuentes": prueba(lambda: MP.fuentes_requeridas_arte(a)),
        "colores": prueba(lambda: MP._colores_personalizable(a)),
        "trazo": prueba(lambda: MP._trazo_personalizable(a)),
        "pasadas": prueba(lambda: MP._pasadas_personalizable(a)),
        "pers": prueba(lambda: MP._extraer_personalizacion_crudo(a)),
        "editables": prueba(lambda: MP._extraer_editables_crudo(a, con_thumb=False)),
    }
    print("arte", os.path.relpath(a, REPO), flush=True)
for m in moldes:
    if not os.path.exists(m):
        continue
    doc = fitz.open(m)
    foto["MOLDE " + os.path.relpath(m, REPO)] = {
        "orden": prueba(lambda: MP._orden_capas_archivo(doc)),
        "talles_A": prueba(lambda: MP._talles_de_plantilla(doc)),
        "talles_B": prueba(lambda: PB.talles_del_molde(doc)),
        "capas_con_dibujo": prueba(lambda: MP._capas_con_dibujo(doc)),
    }
    print("molde", os.path.relpath(m, REPO), flush=True)
with open(salida, "w", encoding="utf-8") as fh:
    json.dump(foto, fh, ensure_ascii=False, indent=1, sort_keys=True)
print("listo:", len(foto), "archivos ->", salida)
