# SIRVE LOS ARCHIVOS DE PRUEBA (COPIAS) AL NAVEGADOR DEL SANDBOX, con CORS — `py servir_archivos.py <carpeta>`
# 🔴 Puerto 8093, NUNCA el 8071 (lo usa el NESTING DTF del usuario).
import http.server, sys, os
os.chdir(sys.argv[1])
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*"); super().end_headers()
http.server.ThreadingHTTPServer(("127.0.0.1", 8093), H).serve_forever()
