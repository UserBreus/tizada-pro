# -*- coding: utf-8 -*-
"""Recibir el AVISO de TIZADA PRO (webhook) y comprobar la firma — Python 3.8+, SIN dependencias.

TIZADA hace POST a la dirección configurada en *Integraciones › Aviso al otro sistema* cuando un
pedido llega a listo / rechazado / error. El cuerpo es el MISMO JSON que GET /pedidos/{ref}.

    X-Tizada-Firma = HMAC-SHA256( clave = sha256_hex(llave), mensaje = cuerpo crudo ) en hexadecimal

    set TIZADA_LLAVE=tzp_...
    python recibir_aviso.py            → escucha en http://0.0.0.0:8090/aviso
"""
import hashlib
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

LLAVE = os.environ.get("TIZADA_LLAVE") or ""
PUERTO = int(os.environ.get("PUERTO") or 8090)


def firma_valida(cuerpo: bytes, firma: str) -> bool:
    clave = hashlib.sha256(LLAVE.encode("utf-8")).hexdigest().encode("ascii")
    esperada = hmac.new(clave, cuerpo, hashlib.sha256).hexdigest()
    return bool(LLAVE) and hmac.compare_digest(esperada, firma or "")


class Aviso(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/aviso":
            self.send_response(404); self.end_headers(); return
        cuerpo = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if not firma_valida(cuerpo, self.headers.get("X-Tizada-Firma")):
            # no viene de TIZADA (o la llave no es la misma): se ignora
            self.send_response(401); self.end_headers(); return
        est = json.loads(cuerpo.decode("utf-8"))
        res = est.get("resultado") or {}
        print(f"Pedido {est['referencia']}: {est['estado']} · venta {json.dumps(est.get('pedido_externo'), ensure_ascii=False)}")
        for a in res.get("archivos") or []:
            print(f"   {a['tipo']:7} {a['nombre']}  sha256 {a['sha256'][:12]}…  drive {a.get('enlace') or '—'}  descarga {a['descarga']}")
        for a in est.get("alarmas") or []:
            print(f"   {'FRENA' if a.get('frena') else 'aviso'} {a['codigo']}: {a.get('mensaje', '')}")
        # ACÁ: guardar en la venta los archivos (drive_id / enlace / sha256) y marcarla como lista.
        # Contestar rápido con 2xx: si no, TIZADA reintenta a los 5 s, 30 s y 2 min.
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')


if __name__ == "__main__":
    if not LLAVE:
        raise SystemExit("falta TIZADA_LLAVE")
    print(f"Esperando avisos de TIZADA PRO en http://0.0.0.0:{PUERTO}/aviso")
    HTTPServer(("0.0.0.0", PUERTO), Aviso).serve_forever()
