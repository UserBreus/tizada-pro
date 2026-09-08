# -*- coding: utf-8 -*-
"""SANDBOX DE SÓLO LECTURA — la UI real, sin login, en el puerto 8060.

Sirve para MIRAR las pantallas de verdad (medir la cobertura de la ayuda, reproducir un bug de
interfaz) sin tener la contraseña del usuario y sin poder tocarle nada.

  py srv_visor.py          →  http://localhost:8060

🔴 DOS CANDADOS, y los dos importan:
  1. **Todo método que no sea GET se rechaza** antes de llegar a la vista. No hay POST, ni PUT, ni
     DELETE: es imposible escribir en la base o en los archivos del usuario aunque uno se equivoque.
  2. `/api/auth/yo` contesta **404**, que es lo que el frontend interpreta como «este sistema no
     tiene usuarios configurados» → entra directo, sin pantalla de login (ver `recargarYo` en
     App.jsx). No se toca la sesión ni las contraseñas de nadie.

Lee la base REAL (que es el punto: ver las pantallas con los datos de verdad). Por eso NO se usa
para probar nada que escriba: para eso van los contratos con el doble de `db`.
"""
import os
import sys

PUERTO = int(os.environ.get("PORT_VISOR", "8060"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import registro as LOG  # noqa: E402

# El sandbox lleva SU PROPIO registro: mirar las pantallas no puede ensuciar el registro del
# sistema de verdad (si no, mañana alguien investiga una falla que provocó una prueba).
LOG.usar_carpeta(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "sandbox"))

import servidor as S  # noqa: E402


@S.app.get("/api/_romper")
def _romper_a_proposito():
    """SÓLO EN EL SANDBOX: revienta a propósito, para comprobar que un error no previsto queda
    en el registro con su traceback (y no se pierde en la ventana del servidor)."""
    return {"nunca": 1 / 0}


@S.app.before_request
def _solo_lectura():
    """El candado. Va como `before_request` y no vista por vista: alcanza con que se escape UNA
    para que el sandbox deje de ser de sólo lectura."""
    from flask import request, jsonify
    if request.method != "GET":
        return jsonify({"error": "sandbox de SÓLO LECTURA: acá no se escribe nada"}), 405
    if request.path == "/api/auth/yo":
        # 404 = «no hay usuarios configurados» para el frontend → entra sin login
        return jsonify({"error": "sin usuarios (sandbox)"}), 404
    return None


if __name__ == "__main__":
    S._USUARIOS_ON = False
    # 🔴 Y el catálogo tampoco se escribe: los backfills que corren al LEERLO son escrituras, y
    # el `before_request` que rechaza lo que no sea GET no las ve (no son requests).
    S._CATALOGO_SOLO_LECTURA = True
    print("=" * 70)
    print(f"  SANDBOX DE SÓLO LECTURA  ·  http://localhost:{PUERTO}")
    print("  Entra sin login y NO puede escribir nada (todo lo que no sea GET se rechaza).")
    print("  El servidor de verdad sigue en el 8050, intacto.")
    print("=" * 70)
    # Los procesos de dibujo también hay que atarlos ACÁ: el sandbox usa el mismo motor y el mismo
    # ProcessPool que el servidor. Sin esto, cada vez que se cierra el sandbox quedaban hasta 6
    # procesos sueltos de ~200 MB (es exactamente lo que dejó la máquina a medio andar en su
    # momento: 86 procesos, 4,8 GB).
    S._atar_hijos_a_este_proceso()
    from werkzeug.serving import make_server
    make_server("127.0.0.1", PUERTO, S.app, threaded=True).serve_forever()
