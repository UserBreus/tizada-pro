# -*- coding: utf-8 -*-
"""Migración: identidad de piezas por ID estable + NOMBRE genérico separados.

Hoy cada pieza se identifica por su CLAVE-string (nombre-con-número, ej.
"Manga Corta Derecha 3") en registro_producto.json, y las variables guardan
`pieza_idx` (que VARÍA por talle). Esto funde nombre+id y es frágil.

Esta migración NO toca el registro (la geometría sigue keyed por clave). Agrega,
por producto, un archivo `piezas.json` con la identidad estable:

    { "version": 1, "piezas": [
        {"id": "pz_0001", "nombre": "Cuello", "numero": null, "clave": "Cuello"},
        {"id": "pz_0085", "nombre": "Manga Corta Derecha", "numero": 3,
         "clave": "Manga Corta Derecha 3"} ] }

y reapunta las variables del catálogo a ese `id`:
  - variantes.valores[].pieza_id   (además del pieza_idx viejo, que se conserva)
  - grupos.piezas_id / conjuntos.piezas_id   (además de .piezas viejo)

Es RE-EJECUTABLE: si piezas.json ya existe, preserva los id↔clave existentes y
solo asigna id nuevos a claves nuevas (los id no se mueven al re-correr).
"""
import json, os, re, sys, shutil

RAIZ = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(RAIZ, "datos")
CAT = os.path.join(DATOS, "productos_catalogo.json")

_RE_NUM = re.compile(r"\s+(\d+)\s*$")


def _cargar(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _guardar(p, data):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def _split_nombre(clave):
    """'Manga Corta Derecha 3' -> ('Manga Corta Derecha', 3);  'Cuello' -> ('Cuello', None)."""
    m = _RE_NUM.search(clave)
    if m:
        return clave[:m.start()].rstrip(), int(m.group(1))
    return clave, None


def _piezas_para(pid, reg, guia, dry):
    """Construye/actualiza la lista de piezas (id estable) del producto."""
    ruta = os.path.join(DATOS, "productos", pid, "piezas.json")
    prev = _cargar(ruta, {"version": 1, "piezas": []})
    # id ya asignados por clave (preservar estabilidad)
    id_por_clave = {p["clave"]: p["id"] for p in prev.get("piezas", []) if p.get("clave")}
    usados = set(id_por_clave.values())

    def _nuevo_id():
        n = 1
        while True:
            cand = "pz_%04d" % n
            if cand not in usados:
                usados.add(cand)
                return cand
            n += 1

    piezas = []
    idx_guia_a_id = {}   # pieza_idx@guia -> id  (para migrar las variables)
    for clave in reg.keys():
        pid_pz = id_por_clave.get(clave) or _nuevo_id()
        nombre, numero = _split_nombre(clave)
        piezas.append({"id": pid_pz, "nombre": nombre, "numero": numero, "clave": clave})
        info = (reg[clave] or {}).get(guia)
        if isinstance(info, dict) and info.get("pieza_idx") is not None:
            idx_guia_a_id[int(info["pieza_idx"])] = pid_pz

    if not dry:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        _guardar(ruta, {"version": 1, "piezas": piezas})
    return piezas, idx_guia_a_id


def _migrar_valor_lista(idxs, idx_a_id):
    """Traduce una lista de pieza_idx@guia -> lista de id (descarta los que no resuelven)."""
    out, faltan = [], []
    for i in idxs:
        pid_pz = idx_a_id.get(int(i))
        if pid_pz:
            out.append(pid_pz)
        else:
            faltan.append(i)
    return out, faltan


def main():
    dry = "--apply" not in sys.argv
    cat = _cargar(CAT)
    if cat is None:
        print("no hay catálogo"); return
    if not dry:
        shutil.copy2(CAT, CAT + ".premigracion.bak")

    total_val = total_falta = 0
    for prod in cat.get("productos", []):
        pid = prod["id"]
        reg = _cargar(os.path.join(DATOS, "productos", pid, "registro_producto.json"))
        if not reg:
            print(f"- {prod.get('nombre')} ({pid}): sin registro, salteo")
            continue
        guia = prod.get("variante_guia")
        piezas, idx_a_id = _piezas_para(pid, reg, guia, dry)
        print(f"- {prod.get('nombre')} ({pid}): {len(piezas)} piezas -> id estable (guia={guia})")

        # variantes.valores[].pieza_idx -> pieza_id
        for v in prod.get("variantes", []) or []:
            for val in v.get("valores", []) or []:
                if val.get("pieza_idx") is None:
                    continue
                pz = idx_a_id.get(int(val["pieza_idx"]))
                if pz:
                    val["pieza_id"] = pz
                    total_val += 1
                else:
                    total_falta += 1
                    print(f"    ! variante {v.get('label')} valor idx={val.get('pieza_idx')} no resuelve a id")
        # grupos.piezas -> piezas_id ; conjuntos.piezas -> piezas_id
        for g in prod.get("grupos", []) or []:
            if isinstance(g.get("piezas"), list):
                ids, faltan = _migrar_valor_lista(g["piezas"], idx_a_id)
                g["piezas_id"] = ids
                if faltan:
                    print(f"    ! grupo {g.get('nombre')}: {len(faltan)} idx sin id")
        for c in prod.get("conjuntos", []) or []:
            if isinstance(c.get("piezas"), list):
                ids, faltan = _migrar_valor_lista(c["piezas"], idx_a_id)
                c["piezas_id"] = ids

    if not dry:
        _guardar(CAT, cat)
    print(f"\n{'APLICADO' if not dry else 'DRY-RUN (usar --apply para escribir)'}: "
          f"valores migrados={total_val}, sin resolver={total_falta}")


if __name__ == "__main__":
    main()
