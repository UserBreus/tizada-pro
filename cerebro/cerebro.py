# -*- coding: utf-8 -*-
"""EL CEREBRO DE TIZADA PRO — no perder lo que ya se construyó y no romperlo sin darse cuenta.

No es una red neuronal que «aprende sola»: es una red de NEURONAS escrita a mano
(`cerebro/neuronas.json`), una por cada parte del sistema que ya funciona, conectadas por
SINAPSIS (qué parte depende de cuál). Funciona como un sistema nervioso:

  • MEMORIA   — cada neurona guarda qué hace, dónde vive, sus REGLAS y sus CICATRICES (las fallas
                que ya pasaron, para no repetirlas), y apunta al MAPA y a la memoria persistente.
  • DOLOR     — cada neurona tiene ANCLAS: nombres que tienen que seguir existiendo en el código.
                Si una desaparece, la función se perdió (o se renombró sin avisar) y `revisar` grita.
  • REFLEJO   — un hook de Claude Code corre `hook` después de CADA edición: mira qué se tocó,
                qué neuronas se activan (y sus vecinas) y le recuerda a Claude sus reglas y qué
                contratos correr, en el momento, antes de seguir.
  • CONCIENCIA — `diff` junta todo lo cambiado contra el último commit: qué partes se tocaron,
                cuáles vecinas pueden sentirlo y qué contratos verifican que nada se rompió.

Uso:
  py cerebro/cerebro.py revisar            ¿están vivas todas las neuronas? (anclas, contratos)
  py cerebro/cerebro.py diff               qué toca lo cambiado desde el último commit
  py cerebro/cerebro.py tocar <archivo>…   qué neuronas viven en esos archivos
  py cerebro/cerebro.py neurona <id>       todo lo que sabe una neurona
  py cerebro/cerebro.py hook               (lo llama Claude Code después de cada Edit/Write)
  py cerebro/cerebro.py inicio             (lo llama Claude Code al empezar la sesión)
"""
import fnmatch
import json
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEURONAS = os.path.join(RAIZ, "cerebro", "neuronas.json")

try:                                   # la consola de Windows no es UTF-8 por defecto
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _cargar():
    with open(NEURONAS, encoding="utf-8") as fh:
        return json.load(fh)


def _rel(ruta):
    """Ruta relativa a la raíz, con `/` (el hook manda absolutas y con `\\`)."""
    if not ruta:
        return ""
    r = os.path.abspath(ruta) if os.path.isabs(ruta) else os.path.abspath(os.path.join(RAIZ, ruta))
    try:
        r = os.path.relpath(r, RAIZ)
    except ValueError:                 # otra unidad de disco
        return ruta.replace("\\", "/")
    return r.replace("\\", "/")


_TEXTOS = {}


def _texto(rel):
    if rel not in _TEXTOS:
        try:
            with open(os.path.join(RAIZ, rel), encoding="utf-8", errors="replace") as fh:
                _TEXTOS[rel] = fh.read()
        except OSError:
            _TEXTOS[rel] = None
    return _TEXTOS[rel]


def _anclas_rotas(n):
    """Las anclas de la neurona que ya no están en el código (= la función se perdió)."""
    rotas = []
    for archivo, texto in n.get("anclas", []):
        t = _texto(archivo)
        if t is None:
            rotas.append(f"{archivo} (el archivo no existe)")
        elif texto not in t:
            rotas.append(f"{archivo}: «{texto}»")
    return rotas


def _contratos_faltantes(n):
    return [c for c in n.get("contratos", []) if not os.path.exists(os.path.join(RAIZ, c))]


def _por_id(cer):
    return {n["id"]: n for n in cer["neuronas"]}


def _activadas(cer, rel, fragmento=None):
    """Qué neuronas se activan al tocar `rel`. En los archivos COMPARTIDOS (App.jsx, servidor.py…)
    viven casi todas: ahí sólo cuenta si lo tocado nombra un ancla o palabras de la neurona — si no,
    cada edición despertaría a todo el cerebro y el aviso no serviría de nada."""
    compartido = rel in cer.get("compartidos", [])
    frag = fragmento or ""
    out = []
    for n in cer["neuronas"]:
        fuerza = 0
        if any(fnmatch.fnmatch(rel, g) for g in n.get("archivos", [])):
            fuerza += 3
        for archivo, texto in n.get("anclas", []):
            if archivo != rel:
                continue
            if not compartido:
                fuerza += 2
            elif frag and texto in frag:
                fuerza += 3
        if frag:
            hits = sum(1 for p in n.get("palabras", []) if p and p in frag)
            fuerza += hits if not compartido else (hits if hits >= 2 else 0)
        if fuerza >= 2 or (not compartido and fuerza >= 1):
            out.append((fuerza, n))
    out.sort(key=lambda x: -x[0])
    return [n for _, n in out]


def _resumen_neurona(n, idx, corto=False):
    lin = [f"■ {n['nombre']} [{n['id']}]"]
    for r in n.get("reglas", []):
        lin.append(f"  · regla: {r}")
    cic = n.get("cicatrices", [])
    for c in (cic[:2] if corto else cic):
        lin.append(f"  · ya pasó: {c}")
    vec = [idx[c]["nombre"] for c in n.get("conexiones", []) if c in idx]
    if vec:
        lin.append(f"  · conectada con: {', '.join(vec)}")
    con = [c for c in n.get("contratos", []) if os.path.exists(os.path.join(RAIZ, c))]
    if con:
        lin.append(f"  · contratos: {' '.join(con)}")
    if n.get("mapa"):
        lin.append(f"  · MAPA: {', '.join(str(m) for m in n['mapa'])}")
    return "\n".join(lin)


# ── comandos ──────────────────────────────────────────────────────────────────────────────────

def revisar(silencioso=False):
    cer = _cargar()
    danadas, avisos = [], []
    for n in cer["neuronas"]:
        rotas = _anclas_rotas(n)
        if rotas:
            danadas.append((n, rotas))
        falt = _contratos_faltantes(n)
        if falt:
            avisos.append(f"{n['id']}: contrato inexistente {', '.join(falt)}")
        for c in n.get("conexiones", []):
            if c not in _por_id(cer):
                avisos.append(f"{n['id']}: conexión a una neurona que no existe «{c}»")
    if not silencioso:
        total = len(cer["neuronas"])
        print(f"CEREBRO: {total - len(danadas)} de {total} neuronas sanas.")
        for n, rotas in danadas:
            print(f"\n⚠ DAÑADA — {n['nombre']} [{n['id']}]: faltan en el código:")
            for r in rotas:
                print(f"    {r}")
            print("   → ¿se borró o renombró? Si fue a propósito, actualizar sus anclas en cerebro/neuronas.json.")
        for a in avisos:
            print(f"· {a}")
    return danadas, avisos


def _cambios_git():
    """{archivo: texto de lo cambiado} contra el último commit (incluye los nuevos sin commit)."""
    out = {}
    try:
        d = subprocess.run(["git", "diff", "HEAD", "--unified=0", "--no-color"], cwd=RAIZ,
                           capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    except Exception:
        d = ""
    actual = None
    for linea in d.splitlines():
        if linea.startswith("+++ b/"):
            actual = linea[6:]
            out.setdefault(actual, "")
        elif actual and (linea.startswith("+") or linea.startswith("-")) and not linea.startswith(("+++", "---")):
            out[actual] += linea[1:] + "\n"
    try:
        nuevos = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=RAIZ,
                                capture_output=True, text=True, encoding="utf-8").stdout.split()
    except Exception:
        nuevos = []
    for f in nuevos:
        out.setdefault(f, _texto(f) or "")
    return out


def diff():
    cer = _cargar()
    idx = _por_id(cer)
    cambios = _cambios_git()
    if not cambios:
        print("No hay cambios contra el último commit.")
    activ, vecinas = {}, set()
    for f, frag in cambios.items():
        # el propio cerebro y la documentación nombran TODO: no son código que se pueda romper
        if f.startswith("cerebro/") or f.endswith(".md"):
            continue
        for n in _activadas(cer, f, frag):
            activ.setdefault(n["id"], set()).add(f)
    for nid in activ:
        vecinas.update(c for c in idx[nid].get("conexiones", []) if c not in activ)
    print(f"Archivos cambiados: {len(cambios)}  ·  neuronas tocadas: {len(activ)}  ·  vecinas que pueden sentirlo: {len(vecinas)}\n")
    for nid, fs in activ.items():
        print(_resumen_neurona(idx[nid], idx))
        print(f"  · tocada en: {', '.join(sorted(fs))}\n")
    if vecinas:
        print("VECINAS (revisar que sigan andando): " + ", ".join(idx[v]["nombre"] for v in sorted(vecinas)))
    contratos = sorted({c for nid in list(activ) + list(vecinas) for c in idx[nid].get("contratos", [])
                        if os.path.exists(os.path.join(RAIZ, c))})
    if contratos:
        print("\nCONTRATOS que verifican lo tocado:")
        for c in contratos:
            print(f"  {'node' if c.endswith('.mjs') else 'py'} {c}")
    danadas, _ = revisar(silencioso=True)
    if danadas:
        print("\n⚠ NEURONAS DAÑADAS (se perdió algo que existía):")
        for n, rotas in danadas:
            print(f"  {n['nombre']}: {'; '.join(rotas)}")
    else:
        print("\nTodas las anclas siguen en el código.")
    print("\nAntes de decir «listo»: MAPA + memoria actualizados, build si tocaste frontend/src, reinicio si tocaste Python.")


def tocar(archivos):
    cer = _cargar()
    idx = _por_id(cer)
    for a in archivos:
        rel = _rel(a)
        ns = _activadas(cer, rel)
        print(f"── {rel}: {len(ns)} neurona(s)" + (" (archivo compartido: sólo las que nombra lo tocado; usá `diff`)" if rel in cer.get("compartidos", []) else ""))
        for n in ns:
            print(_resumen_neurona(n, idx, corto=True))


def neurona(nid):
    cer = _cargar()
    idx = _por_id(cer)
    n = idx.get(nid)
    if not n:
        print("No existe. Neuronas: " + ", ".join(sorted(idx)))
        return
    print(f"{n['nombre']} [{n['id']}]\n{n.get('que', '')}\n")
    print(_resumen_neurona(n, idx))
    rotas = _anclas_rotas(n)
    print("\nAnclas: " + ("⚠ " + "; ".join(rotas) if rotas else "todas en el código"))
    if n.get("memoria"):
        print(f"Memoria: {n['memoria']}")


def hook():
    """PostToolUse (Edit|Write): el REFLEJO. Lee lo que Claude acaba de tocar y le devuelve las
    reglas de las neuronas activadas; si un ancla desapareció, lo dice fuerte. Sin nada que decir,
    no dice nada (un aviso en cada edición termina siendo ruido que nadie lee)."""
    try:
        datos = json.load(sys.stdin)
    except Exception:
        return
    ti = datos.get("tool_input") or {}
    ruta = ti.get("file_path") or (datos.get("tool_response") or {}).get("filePath") or ""
    rel = _rel(ruta)
    # el propio cerebro y los .md (MAPA, manual) nombran TODO: avisar ahí sería ruido en cada anotación
    if not rel or rel.startswith("..") or rel.startswith("cerebro/") or rel.endswith(".md"):
        return
    frag = "\n".join(str(ti.get(k) or "") for k in ("old_string", "new_string", "content"))
    for e in ti.get("edits") or []:
        frag += "\n" + str(e.get("old_string") or "") + "\n" + str(e.get("new_string") or "")
    cer = _cargar()
    idx = _por_id(cer)
    ns = _activadas(cer, rel, frag)[:5]
    # DOLOR: ¿esta edición borró el ancla de alguna neurona que vive en este archivo?
    rotas = []
    for n in cer["neuronas"]:
        for archivo, texto in n.get("anclas", []):
            if archivo == rel and texto not in (_texto(rel) or ""):
                rotas.append(f"{n['nombre']}: «{texto}»")
    if not ns and not rotas:
        return
    partes = ["CEREBRO TIZADA PRO — lo que tocaste en " + rel + ":"]
    if rotas:
        partes.append("⚠ DAÑO: esta edición hizo desaparecer anclas de funciones que ya existían → "
                      + "; ".join(rotas) + ". Si no fue a propósito, se ROMPIÓ algo: revertilo. "
                      "Si fue a propósito, actualizá cerebro/neuronas.json.")
    for n in ns:
        partes.append(_resumen_neurona(n, idx, corto=True))
    partes.append("Antes de cerrar: `py cerebro/cerebro.py diff` (vecinas + contratos).")
    texto = "\n".join(partes)
    if len(texto) > 3500:
        texto = texto[:3500] + "\n…(más en `py cerebro/cerebro.py diff`)"
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": texto}},
                     ensure_ascii=True))


def inicio():
    """SessionStart: una línea de salud + las dañadas, para empezar sabiendo cómo está el cerebro."""
    cer = _cargar()
    danadas, _ = revisar(silencioso=True)
    total = len(cer["neuronas"])
    lin = [f"CEREBRO TIZADA PRO: {total - len(danadas)}/{total} neuronas sanas "
           "(cerebro/neuronas.json). Leyes: " + " | ".join(cer.get("leyes", [])[:4]),
           "Usar `py cerebro/cerebro.py diff` antes de decir «listo»; `neurona <id>` para ver una parte."]
    for n, rotas in danadas:
        lin.append(f"⚠ DAÑADA {n['nombre']}: {'; '.join(rotas)}")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n".join(lin)}},
                     ensure_ascii=True))


if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else "revisar"
    if cmd == "revisar":
        danadas, _ = revisar()
        sys.exit(1 if danadas else 0)
    elif cmd == "diff":
        diff()
    elif cmd == "tocar":
        tocar(args[1:])
    elif cmd == "neurona":
        neurona(args[1] if len(args) > 1 else "")
    elif cmd == "hook":
        hook()
    elif cmd == "inicio":
        inicio()
    else:
        print(__doc__)
