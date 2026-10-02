# -*- coding: utf-8 -*-
"""Cliente de ejemplo de la API de TIZADA PRO — Python 3.8+, SIN dependencias.

Hace el recorrido entero que tiene que hacer el otro sistema:
  1. arma el paquete .zip (pedido.json + los artes + las tipografías que nombra),
  2. lo REVISA con TIZADA (POST /pedidos/validar) y muestra las alarmas,
  3. lo MANDA (POST /pedidos),
  4. pregunta el estado hasta que termina (GET /pedidos/{ref}),
  5. baja cada PDF del resultado y comprueba su sha256.

    set TIZADA_URL=https://tizada.ejemplo.com      (o http://127.0.0.1:8050)
    set TIZADA_LLAVE=tzp_...
    python enviar_pedido.py carpeta_del_pedido/      (adentro: pedido.json + artes/ + tipografias/)
    python enviar_pedido.py carpeta_del_pedido/ --solo-revisar
"""
import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
import zipfile

URL = (os.environ.get("TIZADA_URL") or "http://127.0.0.1:8050").rstrip("/") + "/api/externo/v1"
LLAVE = os.environ.get("TIZADA_LLAVE") or ""
FINALES = ("listo", "rechazado", "error", "cancelado")


def llamar(metodo, ruta, cuerpo=None, tipo=None, crudo=False):
    """(código HTTP, JSON o bytes). Los 4xx también vuelven: traen las alarmas."""
    h = {"X-Api-Key": LLAVE}
    if tipo:
        h["Content-Type"] = tipo
    rq = urllib.request.Request(URL + ruta, data=cuerpo, method=metodo, headers=h)
    try:
        with urllib.request.urlopen(rq, timeout=600) as r:
            datos = r.read()
            return r.status, (datos if crudo else json.loads(datos or b"{}"))
    except urllib.error.HTTPError as e:
        datos = e.read()
        try:
            return e.code, json.loads(datos or b"{}")
        except ValueError:
            return e.code, {"error": datos[:300].decode("utf-8", "replace")}


def armar_zip(carpeta):
    """pedido.json + cada archivo que nombra (arte / tipografías), con la misma ruta adentro del zip."""
    pedido = json.load(open(os.path.join(carpeta, "pedido.json"), encoding="utf-8"))
    rutas = []
    for d in pedido.get("disenos", []):
        rutas += [d.get("arte")] + list(d.get("tipografias") or [])
        for m in d.get("moldes", []):
            rutas += [m.get("arte")] + list(m.get("tipografias") or [])
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pedido.json", json.dumps(pedido, ensure_ascii=False, indent=1))
        for r in sorted({x for x in rutas if x}):
            local = os.path.join(carpeta, *r.split("/"))
            if not os.path.isfile(local):
                sys.exit(f"falta el archivo «{r}» (el pedido lo nombra)")
            z.write(local, r)
    return pedido, bio.getvalue()


def multipart(campo, nombre, datos, tipo):
    borde = "----tizada" + uuid.uuid4().hex
    cuerpo = (f"--{borde}\r\nContent-Disposition: form-data; name=\"{campo}\"; filename=\"{nombre}\"\r\n"
              f"Content-Type: {tipo}\r\n\r\n").encode() + datos + f"\r\n--{borde}--\r\n".encode()
    return cuerpo, f"multipart/form-data; boundary={borde}"


def mostrar_alarmas(alarmas):
    for a in alarmas or []:
        donde = (a.get("donde") or {}).get("campo") or ""
        print(f"   {'FRENA' if a.get('frena') else 'aviso'}  {a.get('codigo'):28} {a.get('mensaje', '')}  {donde}")


def main():
    if len(sys.argv) < 2 or not LLAVE:
        sys.exit(__doc__)
    pedido, paquete = armar_zip(sys.argv[1])
    ref = pedido["referencia"]
    print(f"Paquete de «{ref}»: {len(paquete) // 1024} KB")

    c, d = llamar("POST", "/pedidos/validar", paquete, "application/zip")
    print(f"Revisión: {'la aceptaría' if d.get('aceptaria') else 'la rechazaría'} ({c})")
    mostrar_alarmas(d.get("alarmas"))
    if not d.get("aceptaria") or "--solo-revisar" in sys.argv:
        return

    cuerpo, tipo = multipart("paquete", f"{ref}.zip", paquete, "application/zip")
    c, d = llamar("POST", "/pedidos", cuerpo, tipo)
    print(f"Mandado: {c} {d.get('estado')}")
    mostrar_alarmas(d.get("alarmas"))
    if c != 202:
        return

    etapa = None
    while True:                                   # o esperar el aviso (ver recibir_aviso.py)
        c, est = llamar("GET", f"/pedidos/{ref}")
        if est.get("etapa") != etapa:
            etapa = est.get("etapa")
            print(f"   {est.get('estado'):11} {etapa or ''}")
        if est.get("estado") in FINALES:
            break
        time.sleep(5)
    mostrar_alarmas(est.get("alarmas"))
    res = est.get("resultado")
    if not res:
        return
    os.makedirs(ref, exist_ok=True)
    for a in res["archivos"]:
        c, datos = llamar("GET", a["descarga"].split("/api/externo/v1", 1)[1], crudo=True)
        ok = c == 200 and hashlib.sha256(datos).hexdigest() == a["sha256"]
        with open(os.path.join(ref, a["nombre"]), "wb") as fh:
            fh.write(datos)
        print(f"   {'OK ' if ok else 'MAL'} {a['tipo']:7} {a['nombre']}  ({a['bytes']} bytes)  drive: {a.get('enlace') or '—'}")
    print(f"Listo: los PDF quedaron en ./{ref}/ · pedido_externo devuelto: {json.dumps(res.get('pedido_externo'), ensure_ascii=False)}")


if __name__ == "__main__":
    main()
