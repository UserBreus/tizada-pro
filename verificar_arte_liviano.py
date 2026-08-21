"""CONTRATO: un arte pesado se carga rápido, sin importar cuántas imágenes o vectores tenga.

El usuario probó dos artes reales y sufrió 51 s y 1:13 min. Medido, el problema era el SVG de
las mesas viajando dentro del JSON: en `Camiseta Golero 2.ai` son **1098 KB por mesa, 8,6 MB en
total, VECTOR PURO** (ese arte no tiene ni una imagen embebida) — el navegador tenía que parsear
ese JSON y rasterizar cientos de miles de trazos de una.

Lo que se afirma y se prueba acá, con sus archivos (`1 - Pruba tizada\\Prueba 2`):

  1) La detección ya NO lleva el dibujo adentro: cada mesa viaja como URL (`m.img`) y el
     navegador pide sólo las que muestra. El JSON pasa de megabytes a unos pocos KB.
  2) Subir el arte deja de vectorizar: es lo que se llevaba casi todo el tiempo del servidor.
  3) `/api/arte/mesa_img` devuelve la mesa dibujada a la resolución que se pide, la cachea en
     disco, y la respuesta se puede cachear para siempre (la URL lleva la firma del archivo).
  4) Cambiar el arte cambia la URL de las mesas (nadie ve el arte viejo) y limpia la caché.
  5) La TIZADA sigue leyendo el `.ai` original: el archivo del usuario no se toca.

⚠️ NO comparar SVG rasterizándolos con PyMuPDF: su rasterizador de SVG **ignora las etiquetas
`<image>`** (comprobado: borrarlas no cambia un píxel, y ese render difiere 59% de la página PDF
real). Daría «idéntico» siempre, sin haber mirado nunca la imagen.

No toca datos del usuario: copia aislada de `datos/`+`entrada/` y un `db` que explota.
Uso:  py verificar_arte_liviano.py [nombre del arte]
"""
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import types
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAIZ = os.path.dirname(os.path.abspath(__file__))
ARTES = r"C:\Users\user2\Documents\1 - Pruba tizada\Prueba 2"
PID = "prod_20260729_163651_4d0d"
VAR = "v_7bu24xr"
PUERTO = 8074
ARCHIVO = sys.argv[1] if len(sys.argv) > 1 else "Camiseta Golero 2.ai"
FALLAS = []


def check(ok, msg):
    print(("   OK    " if ok else "   FALLA ") + msg)
    if not ok:
        FALLAS.append(msg)


def _preparar():
    t = tempfile.mkdtemp(prefix="verif_liviano_")
    os.environ.update({"TIZADA_DATOS": os.path.join(t, "datos"), "TIZADA_ENTRADA": os.path.join(t, "entrada"),
                       "TIZADA_TRABAJOS": os.path.join(t, "trabajos"),
                       "TIZADA_FUENTES": os.path.join(RAIZ, "catalogo_fuentes"),
                       "TIZADA_DB_SERVER": r"localhost\NO_EXISTE", "PORT": str(PUERTO)})
    f = types.ModuleType("db")
    f.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(AssertionError("MSSQL")))
    # la "base" del registro, simulada (el server ya no lee el JSON: fuente única 2026-08-19)
    import json as _rj
    _RM, _RR = {}, {}
    def _rl(pid):
        if pid not in _RM:
            try:
                _RM[pid] = _rj.load(open(os.path.join(os.environ["TIZADA_DATOS"], "productos", pid,
                                                      "registro_producto.json"), encoding="utf-8"))
                _RR[pid] = 1
            except Exception:
                return None
        return _RM.get(pid)
    f.leer_registro = _rl
    f.registro_rev = lambda pid: (_RR.get(pid, 1) if _rl(pid) is not None else None)
    f.guardar_registro = lambda pid, piezas, reg: (_RM.__setitem__(pid, reg), _RR.__setitem__(pid, _RR.get(pid, 1) + 1), 1)[-1]
    f.borrar_piezas_molde = lambda pid: (_RM.pop(pid, None), _RR.pop(pid, None), 0)[-1]
    sys.modules["db"] = f
    os.makedirs(os.path.join(t, "datos", "productos"), exist_ok=True)
    for n in os.listdir(os.path.join(RAIZ, "datos")):
        if os.path.isfile(os.path.join(RAIZ, "datos", n)):
            shutil.copy2(os.path.join(RAIZ, "datos", n), os.path.join(t, "datos", n))
    shutil.copytree(os.path.join(RAIZ, "datos", "productos", PID), os.path.join(t, "datos", "productos", PID))
    shutil.copytree(os.path.join(RAIZ, "entrada", PID), os.path.join(t, "entrada", PID))
    return t


BASE = f"http://127.0.0.1:{PUERTO}"


def get(url):
    t0 = time.time()
    with urllib.request.urlopen(BASE + url, timeout=900) as r:
        return time.time() - t0, r.read(), dict(r.headers)


def subir(path, diseno):
    lim = "----x"
    c = io.BytesIO()
    for k, v in (("diseno", diseno), ("pid", PID)):
        c.write(f"--{lim}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    c.write(f"--{lim}\r\nContent-Disposition: form-data; name=\"archivo\"; "
            f"filename=\"{os.path.basename(path)}\"\r\nContent-Type: application/octet-stream\r\n\r\n".encode())
    c.write(open(path, "rb").read())
    c.write(f"\r\n--{lim}--\r\n".encode())
    req = urllib.request.Request(BASE + "/api/arte", data=c.getvalue(),
                                 headers={"Content-Type": f"multipart/form-data; boundary={lim}"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        return time.time() - t0, r.read()


if __name__ == "__main__":       # sin esto, cada worker del ProcessPool re-ejecuta TODO el script
    _T = _preparar()
    sys.path.insert(0, RAIZ)
    import servidor as S  # noqa: E402

    S._USUARIOS_ON = False
    threading.Thread(target=lambda: S.app.run(host="127.0.0.1", port=PUERTO, threaded=True,
                                              use_reloader=False), daemon=True).start()
    for _ in range(80):
        try:
            urllib.request.urlopen(BASE + "/api/salud", timeout=2).read()
            break
        except Exception:
            time.sleep(0.3)
    try:
        arte = os.path.join(ARTES, ARCHIVO)
        huella = os.path.getmtime(arte), os.path.getsize(arte)
        print(f"\n=== «{ARCHIVO}» · {os.path.getsize(arte)/2**20:.1f} MB ===")

        print("\n=== 1) SUBIR el arte (ya no vectoriza las mesas) ===")
        t_sub, _d = subir(arte, "perfil")
        print(f"   POST /api/arte ............................ {t_sub:6.2f}s")
        # Se paga UNA vez por arte. De esto, ~4 s son leer la personalización (nombre/número),
        # que es otra historia; vectorizar las mesas —lo que se llevaba ~8 s— ya no está acá.
        check(t_sub < 12.0, f"subir el arte tarda menos de 12 s ({t_sub:.2f}s)")

        print("\n=== 2) ABRIR el paso Arte: el dibujo NO viaja en el JSON ===")
        t_det, d, _h = get(f"/api/arte/deteccion?diseno=perfil&pid={PID}&variante={VAR}")
        det = json.loads(d)
        mesas = det.get("mesas") or []
        print(f"   GET /api/arte/deteccion ................... {t_det:6.2f}s   ({len(d)/1024:.0f} KB, "
              f"{len(mesas)} mesas)")
        check(len(d) < 700 * 1024, f"la detección pesa menos de 700 KB ({len(d)/1024:.0f} KB)")
        check(t_det < 2.0, f"la detección responde en menos de 2 s ({t_det:.2f}s)")
        check(all(not m.get("svg") for m in mesas), "ninguna mesa manda el dibujo adentro del JSON")
        check(all(m.get("img") for m in mesas), "cada mesa trae su URL (`img`)")

        print("\n=== 3) CADA MESA se pide aparte, y es el VECTOR de verdad ===")
        u = mesas[0]["img"]
        t, dd, h = get(u)
        print(f"   mesa 1 (vector) ........................... {t:6.2f}s   ({len(dd)/1024:5.0f} KB, "
              f"{h.get('Content-Type')})")
        check((h.get("Content-Type") or "").startswith("image/svg+xml"),
              "la mesa se sirve VECTORIAL (no una foto)")
        check("immutable" in (h.get("Cache-Control") or ""),
              "el navegador la puede cachear para siempre (la URL lleva la firma del arte)")
        # FIDELIDAD: tiene que ser EXACTAMENTE el vector que sale del arte, sin simplificar nada.
        import pymupdf as fitz  # noqa: E402
        import motor_pedido as MP  # noqa: E402
        _d = fitz.open(arte)
        try:
            for c in _d.layer_ui_configs():
                if MP._es_capa_guia(c.get("text")) or MP._es_capa_editable(c.get("text")):
                    _d.set_layer_ui_config(c["number"], action=2)
        except Exception:
            pass
        crudo = _d[0].get_svg_image()
        _d.close()
        servido = dd.decode("utf-8")
        check(servido == crudo, "lo que se muestra es el vector del arte, byte por byte")
        check(servido.count("<path") == crudo.count("<path"),
              f"están todos los trazos ({crudo.count('<path')})")
        t2, _dd, _h = get(u)
        print(f"   la misma otra vez (cacheada en disco) ..... {t2:6.2f}s")
        check(t2 < 0.5, f"pedirla de nuevo es instantáneo ({t2:.2f}s)")
        _tot = t_sub + t_det + sum(get(m["img"])[0] for m in mesas)
        print(f"\n   TOTAL subir + abrir + traer las {len(mesas)} mesas en vector: {_tot:5.2f}s")

        print("\n=== 4) SI CAMBIA EL ARTE, cambia la URL (nadie ve el arte viejo) ===")
        antes = mesas[0]["img"]
        t_sub2, _d = subir(os.path.join(ARTES, "Short.ai"), "perfil")
        _t, d2, _h = get(f"/api/arte/deteccion?diseno=perfil&pid={PID}&variante={VAR}")
        m2 = (json.loads(d2).get("mesas") or [{}])[0]
        check(m2.get("img") and m2["img"] != antes, "al subir otro arte, la URL de la mesa cambia")
        cdir = os.path.join(os.environ["TIZADA_ENTRADA"], PID, "disenos", "perfil", "mesas_cache")
        get(m2["img"] + "&px=700")
        quedan = os.listdir(cdir) if os.path.isdir(cdir) else []
        check(all(not q.startswith(antes.split("v=")[1].split("&")[0]) for q in quedan),
              f"la caché en disco del arte viejo se borró (quedan {len(quedan)} archivos, todos nuevos)")

        print("\n=== 5) EL ARTE ORIGINAL NO SE TOCA (la tizada lo usa entero) ===")
        check((os.path.getmtime(arte), os.path.getsize(arte)) == huella, "el .ai del usuario quedó intacto")
    finally:
        sys.stdout.flush()
        shutil.rmtree(_T, ignore_errors=True)

    print("\n" + ("TODO OK" if not FALLAS else f"{len(FALLAS)} FALLA(S):\n  - " + "\n  - ".join(FALLAS)))
    os._exit(1 if FALLAS else 0)
