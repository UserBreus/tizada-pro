# Radiografía de un PDF de arte: lo mismo que mira TIZADA PRO (OCG, /Order, marcadores BDC /OC,
# texto vivo por capa, fuentes, colores CMYK, recortes). Para comparar Corel contra Illustrator.
import sys, re, fitz, pikepdf

ruta = sys.argv[1]
doc = fitz.open(ruta)
print("PAGINAS:", doc.page_count, "| productor:", doc.metadata.get("producer"), "| creador:", doc.metadata.get("creator"))
print("OCGs:", {x: v["name"] for x, v in doc.get_ocgs().items()})
print("layer_ui_configs (orden de la barra):", [(c["text"], c.get("depth"), c.get("on")) for c in doc.layer_ui_configs()])
pdf = pikepdf.open(ruta)
ocp = pdf.Root.get("/OCProperties")
if ocp is not None:
    d = ocp.get("/D")
    print("/D /Order:", [str(o.get("/Name")) if isinstance(o, pikepdf.Dictionary) else ("[sub]" if isinstance(o, pikepdf.Array) else str(o)) for o in (d.get("/Order") or [])])
    print("/D /OFF:", [str(o.get("/Name")) for o in (d.get("/OFF") or [])], "| /Locked:", [str(o.get("/Name")) for o in (d.get("/Locked") or [])])
for i, page in enumerate(doc):
    p = pdf.pages[i]
    print(f"\n=== pagina {i+1}  {page.rect}  mediabox={list(p.MediaBox)}  trim={p.get('/TrimBox')}")
    raw = b"".join(page.read_contents() for _ in [0])
    bdc = re.findall(rb"/OC\s*/(\w+)\s*BDC", raw)
    print("  marcadores BDC /OC en el contenido:", [x.decode() for x in bdc][:20], "| total", len(bdc))
    xo = p.Resources.get("/XObject") or {}
    for k, v in xo.items():
        print("  XObject", k, v.get("/Subtype"), "OC:" , (v.get("/OC") or {}).get("/Name") if v.get("/OC") is not None else None)
    props = (p.Resources.get("/Properties") or {})
    print("  /Properties:", {str(k): str(v.get("/Name")) for k, v in props.items()})
    # texto vivo por capa (como _texto_mesa / personalización)
    for b in page.get_texttrace():
        print("  TEXTO", repr("".join(chr(c[0]) for c in b["chars"])), "fuente:", b["font"], "capa:", b.get("layer"), "color:", b.get("color"), "tipo:", b.get("type"), "ancho linea:", round(b.get("linewidth", 0), 2))
    for dr in page.get_drawings():
        print("  DIBUJO", dr["type"], "capa:", dr.get("layer"), "fill:", dr.get("fill"), "color:", dr.get("color"), "rect:", [round(x) for x in dr["rect"]])
    ops = set(re.findall(rb"\b(k|K|scn|SCN|cs|CS|sc|SC|rg|RG|g|G|W n|Do|sh)\b", raw))
    print("  operadores de color/recorte usados:", sorted(o.decode() for o in ops))
    for m in re.finditer(rb"([\d.]+ [\d.]+ [\d.]+ [\d.]+) (k|K)\b", raw):
        print("    cmyk", m.group(1).decode(), m.group(2).decode())
    cs = p.Resources.get("/ColorSpace") or {}
    print("  espacios de color:", {str(k): (str(v[0]) if isinstance(v, pikepdf.Array) else str(v)) for k, v in cs.items()})
    fonts = p.Resources.get("/Font") or {}
    print("  fuentes:", {str(k): (str(v.get("/BaseFont")), str(v.get("/Subtype"))) for k, v in fonts.items()})
oi = pdf.Root.get("/OutputIntents")
print("\nOutputIntents:", [str(o.get("/OutputConditionIdentifier")) for o in oi] if oi else None)
