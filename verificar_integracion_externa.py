# -*- coding: utf-8 -*-
"""
CONTRATO: UN PEDIDO QUE LLEGA DE OTRO SISTEMA SE HACE SOLO — `py verificar_integracion_externa.py`

MAPA 606. Recorre TODO el camino sin persona, contra un servidor de verdad (HTTP, en otro puerto)
y el robot de verdad (`frontend/src/motor/robot/robot.mjs`, Node):
  1. lo que TIZADA publica (moldes con talles, planilla, opciones y telas; el catálogo de alarmas);
  2. la llave: sin ella no se entra, y la del otro sistema no abre el resto de la API;
  3. la revisión de DATOS: cada error conocido vuelve con SU alarma (molde, talle, tela, opción…);
  4. un pedido bueno (dos diseños sobre el mismo molde, un objeto en TPU, manga corta y larga):
     el robot sube los artes, arma la tizada y deja los PDF + el JSON de resultado;
  5. que el JSON trae el pedido del otro sistema tal cual vino, cada archivo con su lugar, y que
     el aviso (webhook) llega firmado;
  6. Google Drive, contra un DOBLE del protocolo (token de cuenta de servicio, carpeta, subida por
     partes): prueba que el robot habla bien el protocolo, NO que Google lo acepte;
  7. un pedido con el arte mal (objeto editable que no existe, o piezas que quedarían en blanco)
     → rechazado, con su alarma, y sus diseños internos se van del molde;
  8. que los diseños que cargó la persona no se tocaron y que los del pedido no se mezclan con ellos.

⚠️ No toca nada del usuario: el molde y los artes se COPIAN a un temporal, `db` es un doble (nada
de MSSQL) y el servidor de la prueba escucha en un puerto propio.
"""
import hashlib
import hmac
import http.server
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile

CONTRATO_LENTO = True
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import verificar_navegador_tizada as VT       # noqa: E402  (el entorno aislado y los dobles de la base)

S, MP, fitz = VT.S, VT.MP, VT.fitz
ok, FALLOS, _TMP = VT.ok, VT.FALLOS, VT._TMP
import integracion_externa as IE              # noqa: E402

PID = "prod_externo_a"
ORIGEN = os.path.join(AQUI, "entrada", "prod_20260820_095558_38bc")
DATOS_ORIGEN = os.path.join(AQUI, "datos", "productos", "prod_20260820_095558_38bc")
ROBOT = os.path.join(AQUI, "frontend", "src", "motor", "robot", "robot.mjs")

ARTE_1, ARTE_2 = "jugador", "refwerrf"        # refwerrf trae «Editable escudo»
FUENTE = next(os.path.join(AQUI, "catalogo_fuentes", f) for f in sorted(os.listdir(os.path.join(AQUI, "catalogo_fuentes")))
              if f.lower().endswith((".ttf", ".otf")))
_PS_FUENTE = None          # su nombre PostScript (con el que la pide el pedido para cada campo); se llena abajo


def _puerto():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _http(metodo, url, llave=None, cuerpo=None, tipo=None):
    h = {}
    if llave:
        h["X-Api-Key"] = llave
    if tipo:
        h["Content-Type"] = tipo
    rq = urllib.request.Request(url, data=cuerpo, method=metodo, headers=h)
    try:
        with urllib.request.urlopen(rq, timeout=120) as r:
            t = r.read().decode("utf-8") or "{}"
            try:
                return r.status, json.loads(t)
            except ValueError:
                return r.status, {"html": t}          # (la página de vuelta de Google es HTML)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8") or "{}")
        except Exception:
            return e.code, {}


def _zip(pedido, archivos):
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_STORED) as z:
        z.writestr("pedido.json", json.dumps(pedido, ensure_ascii=False))
        for nombre, ruta in archivos.items():
            z.write(ruta, nombre)
    return bio.getvalue()


def _correr_robot(base, extra_env=None):
    # como lo arranca el servidor: con su dirección y la llave del robot en el ambiente
    env = dict(os.environ, TIZADA_URL=base, TIZADA_DATOS=S.DATOS, TIZADA_ROBOT_TOKEN=IE.robot_token(), **(extra_env or {}))
    r = subprocess.run(["node", ROBOT, "--una-vez"], cwd=AQUI, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900)
    return r


# ── un Google Drive de mentira: el protocolo que usa el robot, nada más ──────────────────────
class _DriveFalso(http.server.BaseHTTPRequestHandler):
    archivos, carpetas, tokens, sesiones, pedidos_token = {}, {}, [], {}, []

    def log_message(self, *a):
        pass

    def _json(self, obj, codigo=200, extra=None):
        b = json.dumps(obj).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(b)

    def _cuerpo(self):
        return self.rfile.read(int(self.headers.get("Content-Length") or 0))

    def do_GET(self):
        C = _DriveFalso
        if self.path.startswith("/drive/v3/files?"):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("q", [""])[0]
            nombre = q.split("name = '")[1].split("'")[0] if "name = '" in q else ""
            padre = q.split("' in parents")[0].split("'")[-1]
            hits = [{"id": i, "name": d["name"], "webViewLink": "https://drive.falso/" + i}
                    for i, d in {**C.archivos, **C.carpetas}.items() if d["name"] == nombre and d["padre"] == padre
                    and (("mimeType" not in q) or i in C.carpetas)]
            return self._json({"files": hits})
        if self.path.startswith("/drive/v3/about"):
            if self.headers.get("Authorization") != "Bearer tok-falso":
                return self._json({"error": {"message": "sin token"}}, 401)
            return self._json({"user": {"emailAddress": "dueno@prueba.com"}})
        if self.path.startswith("/drive/v3/files/"):
            fid = self.path.split("/drive/v3/files/")[1].split("?")[0]
            return self._json({"id": fid, "name": {"PED_1": "PEDIDOS", "FIC_1": "Fichas tecnicas"}.get(fid, "Tizadas"),
                               "capabilities": {"canAddChildren": True}})
        self._json({"error": {"message": "ruta no simulada"}}, 404)

    def do_POST(self):
        C = _DriveFalso
        cuerpo = self._cuerpo()
        if self.path == "/token":
            f = urllib.parse.parse_qs(cuerpo.decode())
            tipo = f.get("grant_type", [""])[0]
            C.pedidos_token.append(tipo)
            if tipo == "authorization_code":                 # «Conectar con Google»: el código por el permiso
                if f.get("code", [""])[0] != "codigo-falso" or f.get("client_secret", [""])[0] != "secreto-falso":
                    return self._json({"error": "invalid_grant"}, 400)
                return self._json({"access_token": "tok-falso", "refresh_token": "rt-falso", "expires_in": 3600, "scope": "drive"})
            if tipo == "refresh_token":                      # el robot, con el permiso guardado
                if f.get("refresh_token", [""])[0] != "rt-falso":
                    return self._json({"error": "invalid_grant"}, 400)
                return self._json({"access_token": "tok-falso", "expires_in": 3600})
            partes = (f.get("assertion", [""])[0]).split(".")
            C.tokens.append(partes)
            return self._json({"access_token": "tok-falso", "expires_in": 3600})
        if self.headers.get("Authorization") != "Bearer tok-falso":
            return self._json({"error": {"message": "sin token"}}, 401)
        if self.path.startswith("/drive/v3/files"):
            d = json.loads(cuerpo or b"{}")
            i = "c%d" % (len(C.carpetas) + 1)
            C.carpetas[i] = {"name": d.get("name"), "padre": (d.get("parents") or [""])[0]}
            return self._json({"id": i, "name": d.get("name"), "webViewLink": "https://drive.falso/" + i})
        if self.path.startswith("/upload/drive/v3/files"):
            d = json.loads(cuerpo or b"{}")
            s = "s%d" % (len(C.sesiones) + 1)
            C.sesiones[s] = {"name": d.get("name"), "padre": (d.get("parents") or [""])[0], "id": None}
            return self._json({}, 200, {"Location": f"http://127.0.0.1:{self.server.server_port}/sesion/{s}"})
        self._json({"error": {"message": "ruta no simulada"}}, 404)

    def do_PATCH(self):
        C = _DriveFalso
        self._cuerpo()
        fid = self.path.split("/upload/drive/v3/files/")[1].split("?")[0]
        s = "s%d" % (len(C.sesiones) + 1)
        C.sesiones[s] = {"id": fid}
        self._json({}, 200, {"Location": f"http://127.0.0.1:{self.server.server_port}/sesion/{s}"})

    def do_PUT(self):
        C = _DriveFalso
        datos = self._cuerpo()
        s = C.sesiones[self.path.split("/sesion/")[1]]
        fid = s.get("id") or "a%d" % (len(C.archivos) + 1)
        if s.get("id"):
            C.archivos[fid]["bytes"] = datos
        else:
            C.archivos[fid] = {"name": s["name"], "padre": s["padre"], "bytes": datos}
        self._json({"id": fid, "name": C.archivos[fid]["name"], "webViewLink": "https://drive.falso/" + fid})


class _Avisos(http.server.BaseHTTPRequestHandler):
    recibidos = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        b = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        _Avisos.recibidos.append({"firma": self.headers.get("X-Tizada-Firma"), "ref": self.headers.get("X-Tizada-Referencia"), "cuerpo": b})
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()


def _servir(clase):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), clase)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _un_solo_robot():
    """MAPA 698: en el publicado cada actualización dejaba vivo al robot del servidor viejo (con su código) y ése
    tomaba pedidos: el de la 1.0.49 no arma la copia a medida → «la pieza de 103,6 × 103,6 cm» pida lo que pida."""
    print("\n0 · UN SOLO ROBOT: EL QUE LANZÓ ESTE SERVIDOR (MAPA 698)")
    antes = IE._ROBOT.get("proc")
    try:
        IE._ROBOT["proc"] = object()          # «este servidor lanzó su robot»
        with S.app.test_request_context("/api/externo/robot/tomar", method="POST"):
            r = IE.robot_tomar()
            ok((r.get_json() or {}).get("salir") is True and (r.get_json() or {}).get("tarea") is None,
               "un robot SIN el turno (uno viejo, de otro arranque) no recibe trabajo y se le dice que se cierre")
        with S.app.test_request_context("/api/externo/robot/tomar", method="POST", headers={"X-Robot-Turno": "otro-turno"}):
            ok(not IE._robot_de_este_turno(), "con el turno de OTRO arranque, tampoco")
        with S.app.test_request_context("/api/externo/robot/tomar", method="POST", headers={"X-Robot-Turno": IE._TURNO_ROBOT}):
            ok(IE._robot_de_este_turno(), "el robot de ESTE arranque, sí")
        IE._ROBOT["proc"] = None              # sin robot propio (las pruebas lo corren a mano): vale cualquiera
        with S.app.test_request_context("/api/externo/robot/tomar", method="POST"):
            ok(IE._robot_de_este_turno(), "sin robot propio del servidor, cualquiera con la llave (así corre esta prueba)")
    finally:
        IE._ROBOT["proc"] = antes
    src = open(os.path.join(AQUI, "integracion_externa.py"), encoding="utf-8").read()
    rob = open(ROBOT, encoding="utf-8").read()
    _arr = src[src.index("def arrancar_robot("):src.index("RUTAS_DE_PANTALLA = {")]
    ok("_cerrar_robots_viejos(guion)" in _arr and _arr.index("_cerrar_robots_viejos(guion)") < _arr.index("subprocess.Popen(")
       and "TIZADA_ROBOT_TURNO=_TURNO_ROBOT" in _arr,
       "al arrancar se cierran los robots que quedaron (de a uno, por su comando exacto) y el nuevo lleva el turno")
    ok("h.set('X-Robot-Turno', process.env.TIZADA_ROBOT_TURNO)" in rob and "if (t.salir) {" in rob and "process.exit(0)" in rob,
       "el robot manda su turno y se cierra si el servidor le dice «salir»")
    ok(IE._cerrar_robots_viejos(ROBOT) == [] if os.name == "nt" else True,
       "en Windows no se busca nada (el Job del servidor se lleva a sus hijos)")


def main():
    _un_solo_robot()
    print("\n1 · EL MOLDE DE PRUEBA (copia), SU CATÁLOGO Y EL SERVIDOR")
    carpeta = os.path.join(_TMP, "entrada", PID)
    os.makedirs(carpeta)
    shutil.copy2(os.path.join(ORIGEN, "plantilla.ai"), os.path.join(carpeta, "plantilla.ai"))
    pl = os.path.join(carpeta, "plantilla.ai")
    os.makedirs(os.path.join(_TMP, "datos", "productos", PID), exist_ok=True)
    pz = json.load(open(os.path.join(DATOS_ORIGEN, "piezas.json"), encoding="utf-8"))
    emp = json.load(open(os.path.join(DATOS_ORIGEN, "emparejado_talles.json"), encoding="utf-8"))
    asign = [{"idx": int(p["ancla"]["idx"]), "nombre": p["clave"]} for p in pz["piezas"] if (p.get("ancla") or {}).get("talle") == "M"]
    registro = MP.alta_plantilla_manual(pl, asign, 1, "M", emparejado=emp)["registro"]
    VT._REG[PID] = registro
    talles = S._talles_de_registro(registro)
    # un diseño «de la persona», ya cargado a mano: el pedido externo no lo puede tocar
    VT._DOCS["catalogo"] = {"activo": PID, "productos": [{
        "id": PID, "nombre": "Camiseta de prueba", "planilla_template_id": "plan_x", "variante_guia": "M",
        "disenos": [{"id": "de-la-persona", "nombre": "De la persona"}], "referencia_medida": "alto",
        "mapeo_columnas": {"talle": "talle", "nombre": "nombre", "numero": "numero", "manga": "manga"},
        "telas_cfg": {"todas": ["44"], "por_pieza": {"Cuello": ["77"]}, "max_var": {}},
        "borde_corte": {"activo": True, "color": [0, 0, 0, 1], "mm": 2.0}}],
        "plantillas_planillas": [{"id": "plan_x", "nombre": "Estándar", "columnas": [
            {"id": "cantidad", "label": "Cantidad", "role": "cantidad", "tipo": "numero"},
            {"id": "talle", "label": "Talle", "role": "talle", "obligatoria": True},
            {"id": "nombre", "label": "Nombre", "role": "nombre"}, {"id": "numero", "label": "Número", "role": "numero"},
            {"id": "manga", "label": "Manga", "role": "manga"},
            {"id": "dis", "label": "Diseño", "role": "diseno"}]}],
        "reglas_planilla": [{"id": "regla_manga", "nombre": "Manga", "tipo": "toggle", "opciones": "Corta, Larga", "comportamiento": "manga", "clave": "manga"}],
        "telas": [{"id": "44", "nombre": "Bandera (1,60)", "ancho_cm": 157.0, "medida_cm": 160.0, "activa": True, "usable": True},
                  {"id": "77", "nombre": "Rib (1,00)", "ancho_cm": 97.0, "medida_cm": 100.0, "activa": True, "usable": True},
                  {"id": "9", "nombre": "Vieja", "ancho_cm": None, "medida_cm": None, "activa": False, "usable": False},
                  {"id": "55", "nombre": "Otra (1,50)", "ancho_cm": 147.0, "medida_cm": 150.0, "activa": True, "usable": True}]}
    from werkzeug.serving import make_server
    puerto = _puerto()
    srv = make_server("127.0.0.1", puerto, S.app, threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{puerto}"
    api = base + "/api/externo/v1"
    ok(len(registro) >= 30 and "M" in talles, f"molde con {len(registro)} piezas, talles {talles[:6]}… · servidor en {base}")

    print("\n2 · LA LLAVE")
    cli = S.app.test_client()
    r = cli.post("/api/integracion/llaves/crear", json={"nombre": "Sistema de ventas (prueba)"}).get_json()
    llave = r.get("llave") or ""
    ok(llave.startswith("tzp_") and len(llave) > 30, "la pantalla crea una llave y la muestra una sola vez")
    cfg = json.load(open(os.path.join(S.DATOS, "externo", "config.json"), encoding="utf-8"))
    ok(llave not in json.dumps(cfg), "en el disco queda sólo la huella de la llave, no la llave")
    c, _ = _http("GET", api + "/moldes")
    ok(c == 401, f"sin llave no se entra ({c})")
    c, _ = _http("GET", api + "/moldes", llave="tzp_inventada")
    ok(c == 401, f"con una llave inventada tampoco ({c})")
    c, d = _http("GET", api + "/alarmas")
    ok(c == 200 and len(d.get("alarmas") or []) == len(IE.ALARMAS) and all(a.get("que_hacer") for a in d["alarmas"]),
       f"el catálogo de alarmas es público: {len(d.get('alarmas') or [])} alarmas con qué significan y qué hacer")
    c, _ = _http("POST", base + "/api/externo/robot/tomar", llave=llave, cuerpo=b"{}", tipo="application/json")
    ok(c == 401, f"la llave del otro sistema no sirve para hacerse pasar por el robot ({c})")

    print("\n3 · LO QUE TIZADA PUBLICA")
    c, d = _http("GET", api + "/moldes", llave=llave)
    ok(c == 200 and any(m["codigo"] == PID and m["listo"] for m in d.get("moldes") or []), "la lista de moldes trae el molde, marcado listo")
    c, d = _http("GET", f"{api}/moldes/{PID}", llave=llave)
    m = d.get("molde") or {}
    ok(c == 200 and m.get("talles") == talles, "el molde publica sus talles, en su orden")
    cols = {x["id"]: x for x in (m.get("planilla") or {}).get("columnas") or []}
    ok(cols.get("manga", {}).get("opciones") == ["Corta", "Larga"] and cols.get("talle", {}).get("obligatoria"),
       "publica la planilla: columnas, cuál es obligatoria y las opciones de cada una")
    ok("Cuello" in (m.get("piezas") or []) and (m.get("opciones_de_pieza") or {}).get("manga", {}).get("tiene", {}).get("*") == ["Corta", "Larga"],
       "publica sus piezas (por nombre genérico) y qué opciones de manga tiene de verdad")
    ok([t["id"] for t in (m.get("telas") or {}).get("todas") or []] == ["44"] and "Cuello" in (m.get("telas") or {}).get("por_pieza", {}),
       "publica las telas que admite, en general y por pieza")
    c, d = _http("GET", api + "/telas", llave=llave)
    ok(c == 200 and any(t["id"] == "9" and not t["usable"] for t in d.get("telas") or []), "la lista de telas dice cuáles no se pueden usar")

    print("\n4 · LA REVISIÓN DE DATOS: CADA ERROR CON SU ALARMA")
    def pedido(**cambios):
        p = {"formato": IE.FORMATO, "referencia": "OV-1", "pedido_externo": {"numero": 123, "sucursal": "Centro"},
             "cliente": "Club de prueba",
             "disenos": [{"nombre": "JUGADOR", "arte": "artes/jugador.ai",
                          "moldes": [{"molde": PID, "tela": "44", "telas_por_pieza": {"Cuello": "77"}}]}],
             "planilla": [{"talle": "M", "nombre": "PÉREZ", "numero": "10", "manga": "Corta", "cantidad": 1}]}
        p.update(cambios)
        return p

    def codigos(p):
        c, d = _http("POST", api + "/pedidos/validar", llave=llave, cuerpo=json.dumps(p).encode(), tipo="application/json")
        return c, [a["codigo"] for a in d.get("alarmas") or [] if a.get("frena")], d

    c, cods, d = codigos(pedido())
    ok(c == 200 and not cods and d.get("aceptaria"), f"un pedido bien armado pasa la revisión de datos ({c}, {cods})")
    casos = [
        ("formato-desconocido", pedido(formato="otro/9")),
        ("referencia-invalida", pedido(referencia="OV 1/2")),
        ("molde-desconocido", pedido(disenos=[{"nombre": "J", "arte": "a.ai", "moldes": [{"molde": "prod_no_existe", "tela": "44"}]}])),
        ("tela-desconocida", pedido(disenos=[{"nombre": "J", "arte": "a.ai", "moldes": [{"molde": PID, "tela": "999"}]}])),
        ("tela-no-usable", pedido(disenos=[{"nombre": "J", "arte": "a.ai", "moldes": [{"molde": PID, "tela": "9"}]}])),
        ("tela-no-permitida", pedido(disenos=[{"nombre": "J", "arte": "a.ai", "moldes": [{"molde": PID, "tela": "55"}]}])),
        ("tela-falta", pedido(disenos=[{"nombre": "J", "arte": "a.ai", "moldes": [{"molde": PID}]}])),
        ("pieza-desconocida", pedido(disenos=[{"nombre": "J", "arte": "a.ai", "moldes": [{"molde": PID, "tela": "44", "telas_por_pieza": {"Capucha": "44"}}]}])),
        ("editable-proceso-invalido", pedido(disenos=[{"nombre": "J", "arte": "a.ai", "moldes": [{"molde": PID, "tela": "44", "editables": {"escudo": "pintado"}}]}])),
        ("arte-falta", pedido(disenos=[{"nombre": "J", "moldes": [{"molde": PID, "tela": "44"}]}])),
        ("diseno-repetido", pedido(disenos=[{"nombre": "J", "arte": "a.ai", "moldes": [{"molde": PID, "tela": "44"}]}, {"nombre": "j", "arte": "a.ai", "moldes": [{"molde": PID, "tela": "44"}]}])),
        ("talle-inexistente", pedido(planilla=[{"talle": "XXXXL", "nombre": "A", "numero": "1"}])),
        ("opcion-inexistente", pedido(planilla=[{"talle": "M", "manga": "Tres cuartos"}])),
        ("cantidad-invalida", pedido(planilla=[{"talle": "M", "cantidad": 0}])),
        ("columna-obligatoria-vacia", pedido(planilla=[{"nombre": "SIN TALLE"}])),
        ("fila-diseno-desconocido", pedido(planilla=[{"talle": "M", "diseno": "ARQUERO"}])),
        ("planilla-vacia", pedido(planilla=[])),
        ("mesas-invalido", pedido(mesas={"modo": "por_talles", "grupos": [["M", "ZZ"]]})),
        # MAPA 712: lo que la pantalla deja hacer en el pedido, también por la API
        ("ajuste-invalido", pedido(disenos=[{"nombre": "J", "arte": "a.ai", "moldes": [{"molde": PID, "tela": "44", "ajustes": {"escudo": {"dx": "mucho"}}}]}])),
        ("color-invalido", pedido(disenos=[{"nombre": "J", "arte": "a.ai", "moldes": [{"molde": PID, "tela": "44", "colores": {"escudo": {"fill": [2, 0, 0, 0]}}}]}])),
        ("mapeo-arte-invalido", pedido(disenos=[{"nombre": "J", "arte": "a.ai", "moldes": [{"molde": PID, "tela": "44", "mapeo_arte": {"Capucha": 1}}]}])),
        ("tipografia-desconocida", pedido(disenos=[{"nombre": "J", "arte": "a.ai", "moldes": [{"molde": PID, "tela": "44", "reemplazos": {"Vieja": "NoExisteEstaFuente123"}}]}])),
        ("perfil-desconocido", pedido(opciones={"perfil_color": "NoExiste.icc"})),
        ("repo-invalido", pedido(planilla=[{"talle": "M", "piezas": {PID: ["Capucha"]}}])),
        # MAPA 716: el largo de mesa del pedido (el botón «Largo» de la planilla)
        ("largo-mesa-invalido", pedido(mesas={"modo": "normal", "largo_max_m": 80})),
        ("largo-mesa-invalido", pedido(mesas={"modo": "normal", "largo_max_m": "mucho"})),
        # MAPA 717: «Separar diseños» es true o false
        ("mesas-invalido", pedido(mesas={"modo": "normal", "separar_disenos": "si"})),
    ]
    for cod, p in casos:
        c, cods, _ = codigos(p)
        ok(c == 422 and cod in cods, f"{cod} ({c}: {', '.join(cods) or 'sin alarmas'})")
    # MAPA 712: un pedido con TODO lo nuevo bien armado pasa (ajustes, colores, mapeo a mano, «no imprimir», Repo)
    c, cods, d = codigos(pedido(disenos=[{"nombre": "JUGADOR", "arte": "artes/jugador.ai", "moldes": [{
        "molde": PID, "tela": "44", "editables": {"escudo": "no_imprimir"},
        "ajustes": {"escudo": {"dx": 0.1, "dy": -0.05, "rot": 15, "scale": 1.2, "talles": ["M"]}},
        "colores": {"escudo": {"fill": [0, 0.5, 1, 0]}}, "mapeo_arte": {"Cuello": 1}}]}],
        planilla=[{"talle": "M", "nombre": "A", "numero": "1", "piezas": {PID: ["Cuello"]}}]))
    ok(c == 200 and not cods and d.get("aceptaria"), f"un pedido con ajustes, colores, mapeo a mano, «no imprimir» y Repo pasa ({c}, {cods})")
    # …y se traduce a lo MISMO que manda la pantalla (Repo con la copia a medida, ajustes, colores, tipografías)
    _cu = IE.cuerpo_de({"disenos": [{"slug": "x-j", "nombre": "J", "tipografia_por_campo": {"nombre": "Fuente A"},
                                     "moldes": [{"pid": "COPIA", "plantilla": "ORIG", "variable": "v1",
                                                 "ajustes_ident": {"Escudo": {"M": {"dx": 0.1}}},
                                                 "colores_ident": {"Escudo": {"fill": [0, 0, 0, 1], "stroke": None}},
                                                 "tipografia_por_campo": {"nombre": "Fuente B"}, "reemplazos": {"Vieja": "Nueva"}}]}],
                        "filas": [{"talle": "M", "__repo_ext": {"ORIG": ["Cuello"]}, "__diseno": "J"}],
                        "mesas": {"modo": "normal"}, "opciones": {}, "columnas": []})
    _rr = (_cu.get("fuentes_reemplazo_por") or {}).get("x-j|COPIA") or {}
    ok(_cu["prendas"][0].get("__repo") == {"COPIA": ["Cuello"]} and "__repo_ext" not in _cu["prendas"][0]
       and _cu.get("editables") == {"x-j": {"*": {"Escudo": {"M": {"dx": 0.1}}}, "v1": {"Escudo": {"M": {"dx": 0.1}}}}}
       and (_cu.get("editables_color") or {}).get("x-j", {}).get("*", {}).get("Escudo", {}).get("fill") == [0, 0, 0, 1]
       and _rr.get("Vieja") == "Nueva" and "Fuente B" in _rr.values() and "Fuente A" not in _rr.values(),
       "se traduce como la pantalla: Repo al molde que se usa (la copia a medida), ajustes y colores por diseño y variable, "
       "la tipografía del MOLDE pisa la del diseño y los reemplazos llegan")
    # MAPA 716: el largo de mesa pasa la revisión y llega al cuerpo como lo manda la pantalla
    c, cods, d = codigos(pedido(mesas={"modo": "normal", "largo_max_m": 12.5}))
    _cu2 = IE.cuerpo_de({"disenos": [{"slug": "x-j", "nombre": "J", "moldes": [{"pid": "P", "plantilla": "P", "variable": "v1"}]}],
                         "filas": [{"talle": "M", "__diseno": "J"}], "mesas": {"modo": "normal", "largo_cm": 1250.0},
                         "opciones": {}, "columnas": []})
    _cu3 = IE.cuerpo_de({"disenos": [{"slug": "x-j", "nombre": "J", "moldes": [{"pid": "P", "plantilla": "P", "variable": "v1"}]}],
                         "filas": [{"talle": "M", "__diseno": "J"}], "mesas": {"modo": "una_por_fila", "separar_disenos": True},
                         "opciones": {}, "columnas": []})
    ok(_cu3.get("separar_disenos") is True and "separar_disenos" not in _cu2,
       "`mesas.separar_disenos` llega al cuerpo como el botón «Separar» (y sin él no viaja: el mismo molde se mezcla)")
    ok(c == 200 and not cods and _cu2.get("largo_mesa_cm") == 1250.0,
       f"`mesas.largo_max_m` 12,5 pasa y llega como `largo_mesa_cm` 1250 ({c}, {cods}, {_cu2.get('largo_mesa_cm')})")
    c, d = _http("POST", api + "/pedidos", llave=llave, cuerpo=b"esto no es un zip", tipo="application/zip")
    ok(c == 422 and d["alarmas"][0]["codigo"] == "paquete-ilegible", "un paquete que no es .zip: paquete-ilegible")
    c, d = _http("POST", api + "/pedidos", llave=llave, cuerpo=_zip(pedido(), {}), tipo="application/zip")
    ok(c == 422 and any(a["codigo"] == "archivo-falta" for a in d["alarmas"]), "nombra un arte que no vino en el paquete: archivo-falta")

    print("\n5 · UN PEDIDO BUENO, DE PUNTA A PUNTA (el robot)")
    avisos = _servir(_Avisos)
    cli.post("/api/integracion/config", json={"aviso_url": f"http://127.0.0.1:{avisos.server_port}/aviso"})
    global _PS_FUENTE
    with open(FUENTE, "rb") as _fh:
        _PS_FUENTE = S.MP.nombres_fuente(_fh.read())["ps"]
    arte1 = os.path.join(ORIGEN, "disenos", ARTE_1, "arte.ai")
    arte2 = os.path.join(ORIGEN, "disenos", ARTE_2, "arte.ai")
    bueno = pedido(referencia="OV-2026-00123",
                   # 🔴 (MAPA 670) la tipografía del paquete se pide PARA CADA CAMPO: el arte «jugador» es el REAL del molde
                   # del usuario y cambia (el del 2026-10-12 pide «AIKFotboll130years», que no está en ningún catálogo);
                   # así el contrato no depende de qué fuente traiga ese arte y prueba que la del paquete se USA
                   disenos=[{"nombre": "JUGADOR", "tipografias": ["tipografias/" + os.path.basename(FUENTE)],
                             "tipografia_por_campo": {"nombre": _PS_FUENTE, "numero": _PS_FUENTE},
                             "moldes": [{"molde": PID, "tela": "44", "telas_por_pieza": {"Cuello": "77"}, "arte": "artes/jugador.ai"}]},
                            {"nombre": "GOLERO", "arte": "artes/golero.ai",
                             "moldes": [{"molde": PID, "tela": "44", "telas_por_pieza": {"Cuello": "77"}, "editables": {"escudo": "tpu"},
                                         # MAPA 712: el ajuste y el color del escudo, como «Editar diseño» de la pantalla
                                         "ajustes": {"escudo": {"dx": 0.05, "rot": 10, "scale": 0.9}},
                                         "colores": {"escudo": {"fill": [0, 0, 0, 1]}}}]}],
                   planilla=[{"diseno": "JUGADOR", "talle": "M", "nombre": "PÉREZ", "numero": "10", "manga": "Corta", "cantidad": 1},
                             # MAPA 712: REPO — esta fila sólo hace el cuello
                             {"diseno": "JUGADOR", "talle": "M", "nombre": "REPO", "numero": "5", "manga": "Corta", "piezas": {PID: ["Cuello"]}},
                             {"diseno": "JUGADOR", "talle": talles[-1], "nombre": "GÓMEZ", "numero": "7", "manga": "Larga", "cantidad": 2},
                             {"diseno": "GOLERO", "talle": "M", "nombre": "RAMOS", "numero": "1", "manga": "Larga"}],
                   opciones={"si_falta_tipografia": "predeterminada", "si_piezas_en_blanco": "seguir"},
                   # MAPA 716: mesas de 1,5 m como máximo (el botón «Largo» de la planilla)
                   mesas={"modo": "normal", "largo_max_m": 1.5, "separar_disenos": True})
    paquete = _zip(bueno, {"artes/jugador.ai": arte1, "artes/golero.ai": arte2, "tipografias/" + os.path.basename(FUENTE): FUENTE})
    c, d = _http("POST", api + "/pedidos", llave=llave, cuerpo=paquete, tipo="application/zip")
    ok(c == 202 and d.get("aceptado") and d.get("estado") == "en_cola", f"el paquete se acepta y queda en cola ({c}: {[a['codigo'] for a in d.get('alarmas') or []]})")
    c, d = _http("POST", api + "/pedidos", llave=llave, cuerpo=paquete, tipo="application/zip")
    ok(c == 422 and d["alarmas"][0]["codigo"] == "referencia-en-proceso", "mandarlo otra vez mientras está en marcha: referencia-en-proceso")
    t = time.time()
    r = _correr_robot(base)
    seg = time.time() - t
    # MAPA 712: el robot resolvió el ajuste y el color con el nombre REAL del objeto del arte, en todos los talles
    _nj = json.load(open(os.path.join(IE._dir_pedido("OV-2026-00123"), "normal.json"), encoding="utf-8"))
    _gol = next(m for dd in _nj["disenos"] if dd["nombre"] == "GOLERO" for m in dd["moldes"])
    _cu712 = IE.cuerpo_de(_nj)
    _rep = [pr.get("__repo") for pr in _cu712["prendas"] if pr.get("__repo")]
    ok(bool(_gol.get("ajustes_ident")) and all(len(v) == len(talles) for v in _gol["ajustes_ident"].values())
       and bool(_gol.get("colores_ident")) and (_cu712.get("editables") or {}) and (_cu712.get("editables_color") or {})
       and _rep == [{PID: sorted(p for p in registro if p.split()[0] == "Cuello") or ["Cuello"]}] or _rep and list(_rep[0].values())[0],
       f"el robot resolvió ajuste y color del escudo ({list((_gol.get('ajustes_ident') or {}).keys())}) y el Repo de la fila viaja ({_rep})")
    c, est = _http("GET", api + "/pedidos/OV-2026-00123", llave=llave)
    if est.get("estado") != "listo":
        print("    --- salida del robot ---\n" + (r.stdout or "")[-3000:] + "\n" + (r.stderr or "")[-3000:])
    ok(est.get("estado") == "listo", f"el robot lo terminó solo en {seg:.0f} s (estado: {est.get('estado')} · {est.get('etapa')})")
    res = est.get("resultado") or {}
    ok(res.get("formato") == IE.FORMATO_RESULTADO and res.get("referencia") == "OV-2026-00123"
       and res.get("pedido_externo") == {"numero": 123, "sucursal": "Centro"},
       "el resultado trae la referencia y los datos del pedido del otro sistema TAL CUAL vinieron")
    ok(os.path.exists(os.path.join(S.DATOS, "productos", PID, "fuentes", os.path.basename(FUENTE)))
       and not any(a["codigo"].startswith("tipografia-") for a in res.get("alarmas") or []),
       "la tipografía que vino en el paquete quedó cargada para ese molde (sin tocar el catálogo del sistema)")
    arch = res.get("archivos") or []
    tiz = [a for a in arch if a.get("tipo") == "tizada"]
    ok(len(tiz) >= 2 and any(a.get("tipo") == "ficha" for a in arch),
       f"{len(tiz)} tizada(s) + la ficha técnica: " + ", ".join(f"{a['nombre']} ({a.get('tela')}, {a.get('mesas')} mesa/s)" for a in tiz))
    ok({a.get("tela") for a in tiz} == {"Bandera (1,60)", "Rib (1,00)"}, "una tizada por tela: la principal y la del cuello")
    _largos = [float(x) for a in tiz for x in (a.get("largo_cm") or [])]
    ok(_largos and max(_largos) <= 150.5 and len(tiz) > 2,
       f"`largo_max_m` 1,5: ninguna mesa pasa de 150 cm y lo que no entra sigue en otra ({len(tiz)} mesas: {_largos})")
    _dis = {a.get("diseno") for a in tiz}
    ok(_dis == {"JUGADOR", "GOLERO"},
       f"`separar_disenos`: cada mesa es de UN diseño y lo dice (MAPA 717): {sorted(str(x) for x in _dis)}")
    # el otro sistema no ve rutas del disco del servidor; cada archivo trae su `descarga`
    txt_res = json.dumps(res, ensure_ascii=False)
    ok("ruta" not in {k for a in arch for k in a} and "copia_local" not in txt_res and "carpeta" not in (res.get("destino") or {})
       and S.DATOS.replace("\\", "\\\\") not in txt_res and all(a.get("descarga") for a in arch),
       "el resultado no muestra rutas del servidor y cada archivo trae su dirección de descarga")
    _a0 = arch[0] if arch else {}
    try:
        with urllib.request.urlopen(urllib.request.Request(base + _a0.get("descarga", "/x"), headers={"X-Api-Key": llave}), timeout=60) as _r:
            _bytes = _r.read()
        ok(hashlib.sha256(_bytes).hexdigest() == _a0.get("sha256"), f"«descarga» baja el archivo exacto ({len(_bytes)} bytes, sha256 igual)")
    except Exception as _e:
        ok(False, f"«descarga» baja el archivo exacto ({_e})")
    bien = True
    for a in arch:
        ruta = os.path.join(S.DATOS, "externo", "salida", "OV-2026-00123", a.get("nombre") or "")
        if not (ruta and os.path.exists(ruta)):
            bien = False
            continue
        datos = open(ruta, "rb").read()
        if hashlib.sha256(datos).hexdigest() != a.get("sha256") or len(datos) != a.get("bytes"):
            bien = False
        with fitz.open(ruta) as doc:
            if len(doc) < 1 or (a.get("tipo") == "tizada" and len(doc) != a.get("mesas")):
                bien = False
    ok(bien, "cada archivo del resultado existe, es un PDF que abre, y su tamaño, su sha256 y sus mesas coinciden")
    ok(any(a["codigo"] == "drive-sin-configurar" and not a["frena"] for a in res.get("alarmas") or []),
       "sin Drive configurado avisa (no frena) y deja los PDF en el servidor")
    gol = next((x for x in res.get("disenos") or [] if x["nombre"] == "GOLERO"), {})
    ok(((gol.get("moldes") or [{}])[0].get("no_sublimado") or {}) == {"escudo": "tpu"},
       "el resultado dice qué objeto no se sublima: escudo → TPU")
    tid = res.get("tizada_id")
    pj = json.load(open(os.path.join(S.TRABAJOS, tid, "pedido.json"), encoding="utf-8")) if tid else {}
    ok(bool(tid) and len(pj.get("prendas") or []) >= 3, f"la tizada quedó guardada en el servidor como cualquier otra (trabajo {tid})")
    cat = S._cargar_catalogo(fresco=True)
    dis = cat["productos"][0]["disenos"]
    ok(any(x["id"] == "de-la-persona" for x in dis) and sum(1 for x in dis if x.get("externo") == "OV-2026-00123") == 2,
       "el diseño de la persona sigue intacto y los dos del pedido quedaron aparte, marcados con su referencia")
    with S.app.test_request_context():
        lst = cli.get(f"/api/disenos?molds={PID}").get_json()["por_molde"][PID]
    ok([x["id"] for x in lst] == ["principal", "de-la-persona"], "en la pantalla, la lista de diseños del molde no muestra los del pedido externo")
    for _ in range(40):
        if _Avisos.recibidos:
            break
        time.sleep(0.25)
    av = _Avisos.recibidos[-1] if _Avisos.recibidos else {}
    huella = hashlib.sha256(llave.encode()).hexdigest()
    ok(bool(av) and av.get("ref") == "OV-2026-00123"
       and hmac.compare_digest(av.get("firma") or "", hmac.new(huella.encode(), av["cuerpo"], hashlib.sha256).hexdigest())
       and json.loads(av["cuerpo"]).get("estado") == "listo",
       "el aviso llegó a la dirección configurada, con el resultado adentro y firmado con la llave")
    c, d = _http("POST", api + "/pedidos", llave=llave, cuerpo=paquete, tipo="application/zip")
    ok(c == 422 and d["alarmas"][0]["codigo"] == "referencia-ya-generada", "una tizada hecha no se pisa: referencia-ya-generada")

    print("\n6 · GOOGLE DRIVE (contra un doble del protocolo)")
    drive = _servir(_DriveFalso)
    gbase = f"http://127.0.0.1:{drive.server_port}"
    clave = subprocess.run(["node", "-e", "const c=require('crypto');const {privateKey}=c.generateKeyPairSync('rsa',{modulusLength:2048});"
                            "process.stdout.write(privateKey.export({type:'pkcs8',format:'pem'}))"], capture_output=True, text=True).stdout
    cuenta = {"type": "service_account", "project_id": "prueba", "private_key_id": "k1", "private_key": clave,
              "client_email": "robot@prueba.iam.gserviceaccount.com", "token_uri": gbase + "/token"}
    r = cli.post("/api/integracion/drive_cuenta", data={"archivo": (io.BytesIO(json.dumps(cuenta).encode()), "cuenta.json")},
                 content_type="multipart/form-data")
    ok(r.status_code == 200 and r.get_json().get("cuenta") == cuenta["client_email"], "la pantalla recibe el archivo de la cuenta de servicio")
    r = cli.post("/api/integracion/drive_cuenta", data={"archivo": (io.BytesIO(b'{"type":"otra cosa"}'), "x.json")}, content_type="multipart/form-data")
    ok(r.status_code == 422, "un archivo que no es una cuenta de servicio se rechaza")
    cli.post("/api/integracion/config", json={"drive_activo": True, "drive_carpeta": "https://drive.google.com/drive/folders/RAIZ_123?usp=sharing", "probar_drive": True})
    e = cli.get("/api/integracion/estado").get_json()
    ok(e["drive"]["carpeta_id"] == "RAIZ_123" and e["drive"]["cuenta"] == cuenta["client_email"] and "private_key" not in json.dumps(e),
       "de un enlace de carpeta se queda con su id, y la pantalla nunca recibe la llave privada")
    r = _correr_robot(base, {"TIZADA_DRIVE_API": gbase})
    e = cli.get("/api/integracion/estado").get_json()
    ok((e["drive"].get("prueba") or {}).get("ok"), f"«Probar conexión»: el robot escribe un archivo de prueba ({(e['drive'].get('prueba') or {}).get('detalle')})")
    bueno2 = dict(bueno, referencia="OV-2026-00124", pedido_externo={"numero": 124})
    c, d = _http("POST", api + "/pedidos", llave=llave, cuerpo=_zip(bueno2, {"artes/jugador.ai": arte1, "artes/golero.ai": arte2, "tipografias/" + os.path.basename(FUENTE): FUENTE}), tipo="application/zip")
    r = _correr_robot(base, {"TIZADA_DRIVE_API": gbase})
    c, est = _http("GET", api + "/pedidos/OV-2026-00124", llave=llave)
    res2 = est.get("resultado") or {}
    if est.get("estado") != "listo":
        print("    --- salida del robot ---\n" + (r.stdout or "")[-3000:] + "\n" + (r.stderr or "")[-3000:])
    ok(est.get("estado") == "listo" and (res2.get("destino") or {}).get("tipo") == "drive",
       f"con Drive prendido el pedido termina con destino «drive» ({est.get('estado')} · {(res2.get('destino') or {}).get('tipo')})")
    carp = [c_ for c_ in _DriveFalso.carpetas.values() if c_["name"] == "OV-2026-00124" and c_["padre"] == "RAIZ_123"]
    subidos = {a["name"]: a for a in _DriveFalso.archivos.values()}
    iguales = all(a.get("drive_id") and a.get("enlace") and a["nombre"] in subidos
                  and hashlib.sha256(subidos[a["nombre"]]["bytes"]).hexdigest() == a["sha256"] for a in res2.get("archivos") or [])
    ok(len(carp) == 1 and iguales and (res2.get("archivos") or []),
       "se creó la carpeta del pedido dentro de la configurada y cada PDF subió entero (mismo sha256), con su id y su enlace")
    ok("OV-2026-00124__resultado.json" in subidos and json.loads(subidos["OV-2026-00124__resultado.json"]["bytes"]).get("referencia") == "OV-2026-00124",
       "el JSON de resultado queda en la misma carpeta, junto a los PDF")
    ok(not any(a["codigo"].startswith("drive-") for a in res2.get("alarmas") or []), "y ya no hay alarmas de Drive")
    tk = _DriveFalso.tokens[-1] if _DriveFalso.tokens else []
    import base64
    claim = json.loads(base64.urlsafe_b64decode(tk[1] + "==")) if len(tk) == 3 else {}
    ok(claim.get("iss") == cuenta["client_email"] and "drive" in str(claim.get("scope")), "el pedido de token va firmado a nombre de la cuenta de servicio")

    print("\n6b · GOOGLE DRIVE CON LA CUENTA DE UNA PERSONA (OAuth) Y DOS CARPETAS")
    # el caso real (2026-10-02): breusplanilla@gmail.com es una cuenta PERSONAL y la carpeta está en su
    # «Mi unidad»: una cuenta de servicio no puede guardar ahí. Se conecta la cuenta de la persona.
    os.environ["TIZADA_DRIVE_API"] = gbase           # (el servidor de la prueba pregunta el correo al Drive de mentira)
    cliente = {"web": {"client_id": "cli-falso.apps.googleusercontent.com", "client_secret": "secreto-falso",
                       "auth_uri": gbase + "/auth", "token_uri": gbase + "/token", "redirect_uris": []}}
    r = cli.post("/api/integracion/drive_cuenta", data={"archivo": (io.BytesIO(json.dumps(cliente).encode()), "client_secret.json")},
                 content_type="multipart/form-data")
    e = cli.get("/api/integracion/estado").get_json()
    ok(r.status_code == 200 and e["drive"]["cliente"] and not e["drive"]["conectada"] and "secreto-falso" not in json.dumps(e),
       "la pantalla recibe el «ID de cliente» de Google, no muestra el secreto y pide conectar")
    vuelta = base + "/api/integracion/drive/vuelta"
    r = cli.post("/api/integracion/drive/conectar", json={"vuelta": vuelta, "volver": base + "/admin"}).get_json()
    q = urllib.parse.parse_qs(urllib.parse.urlparse(r.get("url") or "").query)
    ok((r.get("url") or "").startswith(gbase + "/auth?") and q.get("redirect_uri") == [vuelta] and q.get("access_type") == ["offline"]
       and "drive" in (q.get("scope") or [""])[0] and q.get("state"),
       "«Conectar con Google» arma el pedido de permiso: vuelve a TIZADA, pide permiso permanente y sólo Drive")
    c, _ = _http("GET", f"{vuelta}?code=codigo-falso&state=inventado")
    ok(c == 400, f"una vuelta con un `state` que no pidió TIZADA se rechaza ({c})")
    c, _ = _http("GET", f"{vuelta}?code=codigo-falso&state={q['state'][0]}")      # sin sesión: como el navegador al volver
    e = cli.get("/api/integracion/estado").get_json()
    tok = json.load(open(os.path.join(S.DATOS, "externo", "drive_oauth_token.json"), encoding="utf-8"))
    ok(c == 200 and e["drive"]["conectada"] == "dueno@prueba.com" and tok.get("refresh_token") == "rt-falso" and "rt-falso" not in json.dumps(e),
       "al volver de Google queda conectada la cuenta (dueno@prueba.com) con su permiso guardado, que la pantalla no ve")
    c, _ = _http("GET", f"{vuelta}?code=codigo-falso&state={q['state'][0]}")
    ok(c == 400, "el mismo `state` no sirve dos veces")
    cli.post("/api/integracion/config", json={"drive_activo": True, "drive_carpeta_tizadas": "https://drive.google.com/drive/folders/PED_1",
                                              "drive_carpeta_fichas": "FIC_1", "probar_drive": True})
    _DriveFalso.pedidos_token.clear()
    r = _correr_robot(base, {"TIZADA_DRIVE_API": gbase})
    e = cli.get("/api/integracion/estado").get_json()
    pr = e["drive"].get("prueba") or {}
    ok(pr.get("ok") and "PEDIDOS" in pr.get("detalle", "") and "Fichas tecnicas" in pr.get("detalle", "")
       and "refresh_token" in _DriveFalso.pedidos_token,
       f"«Probar» escribe en las DOS carpetas con el permiso de la cuenta ({pr.get('detalle')})")
    bueno3 = dict(bueno, referencia="OV-2026-00125", pedido_externo={"numero": 125})
    c, d = _http("POST", api + "/pedidos", llave=llave, cuerpo=_zip(bueno3, {"artes/jugador.ai": arte1, "artes/golero.ai": arte2, "tipografias/" + os.path.basename(FUENTE): FUENTE}), tipo="application/zip")
    r = _correr_robot(base, {"TIZADA_DRIVE_API": gbase})
    c, est = _http("GET", api + "/pedidos/OV-2026-00125", llave=llave)
    res3 = est.get("resultado") or {}
    if est.get("estado") != "listo":
        print("    --- salida del robot ---\n" + (r.stdout or "")[-3000:] + "\n" + (r.stderr or "")[-3000:])
    sub = [i for i, c_ in _DriveFalso.carpetas.items() if c_["name"] == "OV-2026-00125" and c_["padre"] == "PED_1"]
    por_nombre = {a["name"]: a for a in _DriveFalso.archivos.values()}
    hojas = [a for a in res3.get("archivos") or [] if a.get("tipo") == "tizada"]
    ficha = [a for a in res3.get("archivos") or [] if a.get("tipo") == "ficha"]
    ok(est.get("estado") == "listo" and len(sub) == 1 and hojas and ficha
       and all(por_nombre.get(a["nombre"], {}).get("padre") == sub[0] and a.get("carpeta_id") == sub[0] for a in hojas)
       and all(por_nombre.get(a["nombre"], {}).get("padre") == "FIC_1" and a.get("carpeta_id") == "FIC_1" for a in ficha),
       f"las tizadas van a PEDIDOS/OV-2026-00125 y la ficha técnica a Fichas tecnicas ({len(hojas)} hoja(s), {len(ficha)} ficha)")
    ok((res3.get("destino") or {}).get("carpeta_fichas_id") == "FIC_1" and por_nombre.get("OV-2026-00125__resultado.json", {}).get("padre") == sub[0],
       "el resultado dice las dos carpetas y su JSON queda junto a las tizadas")
    cli.post("/api/integracion/drive/desconectar")
    ok(not cli.get("/api/integracion/estado").get_json()["drive"]["conectada"], "«Desconectar» olvida el permiso de la cuenta")

    print("\n7 · UN PEDIDO CON EL ARTE MAL: SE RECHAZA Y NO DEJA NADA")
    malo = dict(bueno, referencia="OV-MALO", disenos=[{"nombre": "JUGADOR", "arte": "artes/jugador.ai",
                "moldes": [{"molde": PID, "tela": "44", "telas_por_pieza": {"Cuello": "77"}, "editables": {"parche inventado": "bordado"}}]}],
                planilla=[{"diseno": "JUGADOR", "talle": "M", "nombre": "X", "numero": "1", "manga": "Corta"}])
    c, d = _http("POST", api + "/pedidos", llave=llave, cuerpo=_zip(malo, {"artes/jugador.ai": arte1}), tipo="application/zip")
    ok(c == 202, "los datos están bien, así que entra (el arte se mira después)")
    # el mismo pedido bueno pero SIN pedir «seguir»: el arte no cubre todas las piezas que se fabrican
    blanco = dict(bueno, referencia="OV-BLANCO", opciones={})
    c, d = _http("POST", api + "/pedidos", llave=llave, cuerpo=_zip(blanco, {"artes/jugador.ai": arte1, "artes/golero.ai": arte2, "tipografias/" + os.path.basename(FUENTE): FUENTE}), tipo="application/zip")
    r = _correr_robot(base, {"TIZADA_DRIVE_API": gbase})
    c, estb = _http("GET", api + "/pedidos/OV-BLANCO", llave=llave)
    codsb = [a["codigo"] for a in estb.get("alarmas") or [] if a.get("frena")]
    ok(estb.get("estado") == "rechazado" and codsb and set(codsb) == {"piezas-en-blanco"} and not estb.get("resultado"),
       f"por defecto, piezas que se fabrican y el arte no cubre FRENAN antes de armar nada ({estb.get('estado')}: {sorted(set(codsb))})")
    c, est = _http("GET", api + "/pedidos/OV-MALO", llave=llave)
    cods = [a["codigo"] for a in est.get("alarmas") or [] if a.get("frena")]
    ok(est.get("estado") == "rechazado" and "editable-desconocido" in cods and "resultado" not in est,
       f"queda rechazado con su alarma y sin resultado ({est.get('estado')}: {cods})")
    cat = S._cargar_catalogo(fresco=True)
    ok(not any(x.get("externo") == "OV-MALO" for x in cat["productos"][0]["disenos"])
       and not os.path.exists(os.path.join(S.ENTRADA, PID, "disenos", IE._slug_interno("OV-MALO", "JUGADOR"))),
       "sus diseños internos se fueron del molde y del disco")
    ok(any(x["id"] == "de-la-persona" for x in cat["productos"][0]["disenos"]), "el diseño de la persona sigue ahí")
    e = cli.get("/api/integracion/estado").get_json()
    ok({p["referencia"]: p["estado"] for p in e["pedidos"]} == {"OV-2026-00123": "listo", "OV-2026-00124": "listo", "OV-2026-00125": "listo", "OV-MALO": "rechazado", "OV-BLANCO": "rechazado"}
       and len(e.get("rechazos") or []) >= 4,
       f"la pantalla lista los cinco pedidos con su estado y el historial de rechazos ({len(e.get('rechazos') or [])})")

    print("\n9 · SE ELIGEN VARIABLES (como en el pedido de TIZADA), no moldes")
    # dos variables del molde de prueba + una prenda incompleta con una variable que se llama igual
    import copy
    cat0 = copy.deepcopy(VT._DOCS["catalogo"])
    guia = {}
    for _nm, _pt in VT._REG[PID].items():
        _inf = (_pt or {}).get("M")
        if isinstance(_inf, dict) and _inf.get("pieza_idx") is not None:
            guia[_nm] = int(_inf["pieza_idx"])
    _nms = sorted(guia)
    prod0 = VT._DOCS["catalogo"]["productos"][0]
    prod0["variantes"] = [{"clave": "v_redondo", "label": "Cuello redondo", "valores": [{"pieza_idx": guia[n]} for n in _nms[: len(_nms) // 2]]},
                          {"clave": "v_cuellov", "label": "Cuello V", "valores": [{"pieza_idx": guia[n]} for n in _nms[len(_nms) // 2:]]}]
    VT._DOCS["catalogo"]["productos"].append({"id": "prod_otra_prenda", "nombre": "Otra prenda", "planilla_template_id": "plan_x",
                                              "variantes": [{"clave": "v_otra", "label": "Cuello V", "valores": [{"pieza_idx": 0}]}]})
    try:
        c, d = _http("GET", api + "/variables", llave=llave)
        vs = {v["clave"]: v for v in d.get("variables") or []}
        ok(c == 200 and set(vs) == {"v_redondo", "v_cuellov"} and vs["v_redondo"]["molde"] == PID and vs["v_redondo"]["n_piezas"] == len(_nms) // 2,
           f"/variables lista las variables de las prendas listas, con su prenda detrás ({sorted(vs)}; la prenda incompleta no)")
        c, _ = _http("GET", api + "/variables")
        ok(c == 401, f"/variables pide la llave ({c})")
        # acá TIZADA todavía no calculó la silueta del molde (nadie lo abrió en un navegador): el
        # servidor se la pediría a quien llama, y el otro sistema no puede calcular → 404 con motivo
        # esto ES el modo «el servidor no calcula» (el de verdad, siempre prendido): el corredor de
        # contratos lo apaga por defecto para probar la referencia en Python, acá se prende (MAPA 624)
        _solo0 = os.environ.get("TIZADA_SOLO_NAVEGADOR")
        os.environ["TIZADA_SOLO_NAVEGADOR"] = "1"
        try:
            c, f = _http("GET", api + "/variables/v_redondo/foto", llave=llave)
            c2, f2 = _http("GET", f"{api}/moldes/{PID}/foto", llave=llave)
        finally:
            if _solo0 is None:
                os.environ.pop("TIZADA_SOLO_NAVEGADOR", None)
            else:
                os.environ["TIZADA_SOLO_NAVEGADOR"] = _solo0
        ok(c == 404 and f.get("sin_calcular") and c2 == 404 and f2.get("sin_calcular"),
           f"sin silueta calculada: 404 con el motivo, nunca un pedido de cálculo al otro sistema ({c}/{c2})")
        # con la silueta ya calculada (la de siempre, con `idx` por pieza) la variable trae SÓLO las suyas
        _prev = S.app.view_functions["producto_preview"]
        S.app.view_functions["producto_preview"] = lambda pid: S.jsonify({"img_w": 100, "img_h": 100, "piezas": [
            {"idx": i, "path_svg": "M 0 0 L 1 1 Z", "px": 0, "py": 0, "pw": 1, "ph": 1} for i in sorted(guia.values())]})
        try:
            c, f = _http("GET", api + "/variables/v_redondo/foto", llave=llave)
        finally:
            S.app.view_functions["producto_preview"] = _prev
        idx_r = {guia[n] for n in _nms[: len(_nms) // 2]}
        ok(c == 200 and {p["idx"] for p in f.get("piezas") or []} == idx_r,
           f"la silueta de una variable trae SÓLO sus piezas ({len(f.get('piezas') or [])} de {len(guia)})")
        c, _ = _http("GET", api + "/variables/v_no_existe/foto", llave=llave)
        ok(c == 404, f"una variable que no existe: 404 ({c})")
        def _dis(*moldes):
            return pedido(disenos=[{"nombre": "JUGADOR", "arte": "artes/jugador.ai", "moldes": list(moldes)}])
        c, cods, r = codigos(_dis({"variable": "v_redondo", "tela": "44"}))
        ok(c == 200 and not cods and r.get("aceptaria"), f"un pedido con SÓLO la variable (sin molde) se acepta ({cods})")
        c, cods, r = codigos(_dis({"variable": "Cuello redondo", "tela": "44"}))
        ok(not cods and r.get("aceptaria"), f"también por el NOMBRE si una sola prenda lo tiene ({cods})")
        c, cods, r = codigos(_dis({"variable": "Cuello V", "tela": "44"}))
        ok("variable-ambigua" in cods, f"un nombre que está en dos prendas pide la clave ({cods})")
        c, cods, r = codigos(_dis({"variable": "v_redondo", "tela": "44"}, {"variable": "v_cuellov", "tela": "44"}))
        ok("molde-repetido" in cods, f"dos variables de la misma prenda en un diseño: frena ({cods})")
        c, cods, r = codigos(_dis({"variable": "v_no_existe", "tela": "44"}))
        ok("variable-desconocida" in cods, f"una variable que no existe: variable-desconocida ({cods})")

        # ── 10 · «CREAR EN ILLUSTRATOR / CORELDRAW» DESDE EL OTRO SISTEMA + LOS CONECTORES (2026-10-27) ──
        # El usuario preguntó si la API entregada sirve para el botón de mandar a crear la plantilla en
        # Illustrator o Corel y si deja bajar la extensión: se recorre de punta a punta, como lo haría el otro sistema.
        print("\n10 · PLANTILLA PARA ILLUSTRATOR / CORELDRAW + LOS CONECTORES (la extensión)")
        def _bajar(ruta):
            rq = urllib.request.Request(base + ruta, headers={"X-Api-Key": llave})
            try:
                with urllib.request.urlopen(rq, timeout=120) as rr:
                    return rr.status, rr.read(), rr.headers.get("Content-Disposition") or ""
            except urllib.error.HTTPError as e:
                return e.code, b"", ""
        c, d = _http("POST", api + "/plantillas", llave=llave, tipo="application/json", cuerpo=json.dumps({
            "referencia": "PL-PRUEBA", "disenos": [{"nombre": "JUGADOR", "variables": ["v_redondo"]}],
            "talles": {"modo": "todos"}, "escala": 100}).encode())
        ok(c == 202, f"POST /plantillas la pone en cola ({c} {d.get('alarmas') or ''})")
        c, _ = _http("POST", api + "/plantillas", tipo="application/json", cuerpo=b"{}")
        ok(c == 401, f"/plantillas pide la llave ({c})")
        rr = _correr_robot(base)
        c, est = _http("GET", api + "/plantillas/PL-PRUEBA", llave=llave)
        tipos = {a.get("tipo"): a for a in est.get("archivos") or []}
        ok(c == 200 and est.get("estado") == "listo" and {"illustrator", "corel", "guia"} <= set(tipos),
           f"el robot la arma: archivos de Illustrator, CorelDRAW y la guía .ai ({est.get('estado')}, {sorted(tipos)}"
           f"{'' if est.get('estado') == 'listo' else ' · ' + (rr.stdout or '')[-400:] + (rr.stderr or '')[-400:]})")
        _dir_pl = os.path.join(_TMP, "plantilla_bajada")
        os.makedirs(_dir_pl, exist_ok=True)
        for tp in ("illustrator", "corel"):
            a = tipos.get(tp) or {}
            c, cuerpo, _ = _bajar(a.get("descarga") or "/x")
            try:
                plan = json.loads(cuerpo.decode("utf-8"))
            except Exception:
                plan = None
            ok(c == 200 and isinstance(plan, dict) and hashlib.sha256(cuerpo).hexdigest() == a.get("sha256"),
               f"el archivo de {tp} se baja entero (el JSON que va tal cual a POST http://127.0.0.1:{47850 if tp == 'illustrator' else 47851}/plantilla) ({c})")
            if c == 200:
                with open(os.path.join(_dir_pl, a["nombre"]), "wb") as fh:
                    fh.write(cuerpo)
        _vc = {x["clave"]: x["version"] for x in (_http("GET", api + "/conectores", llave=llave)[1].get("conectores") or [])}
        _ce = est.get("conectores") or {}
        ok(all((_ce.get(p) or {}).get("version") == _vc.get(p) and (_ce.get(p) or {}).get("crear", "").startswith("http://127.0.0.1:")
               and (_ce.get(p) or {}).get("tipo_archivo") == p for p in ("illustrator", "corel")),
           f"TIZADA dice CÓMO se crea: a dónde va cada archivo y qué versión de conector corresponde ({ {p: (_ce.get(p) or {}).get('version') for p in _ce} })")

        # EL CÓDIGO QUE SE LE ENTREGA (`codigo/crear_en_programa.js`) corrido de verdad contra un conector DE PRUEBA
        # (otro puerto: nunca el Illustrator o el Corel de esta computadora). Tiene que llegarle el plan TAL CUAL.
        class _ConectorFalso(http.server.BaseHTTPRequestHandler):
            recibidos, previos, programa = [], [], "illustrator"
            def log_message(self, *a):
                pass
            def _resp(self, codigo, obj):
                b = json.dumps(obj).encode()
                self.send_response(codigo)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)
            def do_OPTIONS(self):
                type(self).previos.append(self.path)
                self._resp(204, {})
            def do_GET(self):
                if self.path.startswith("/estado"):
                    d = {"app": "TIZADA PRO", "version": "0.0.1"}
                    if type(self).programa == "corel":
                        d["programa"] = "corel"
                    return self._resp(200, d)
                self._resp(404, {"ok": False, "error": "no existe"})
            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                cuerpo = self.rfile.read(n)
                type(self).recibidos.append((self.path, self.headers.get("Content-Type"), cuerpo))
                self._resp(200, {"ok": True, "mesas": 7, "archivo": f"prueba_{len(type(self).recibidos)}.ai"})
        _est_json = os.path.join(_TMP, "estado_plantilla.json")
        with open(_est_json, "w", encoding="utf-8") as fh:
            json.dump(est, fh)
        for tp in ("illustrator", "corel"):
            _ConectorFalso.recibidos, _ConectorFalso.previos, _ConectorFalso.programa = [], [], tp
            _pc = _puerto()
            _sv = http.server.ThreadingHTTPServer(("127.0.0.1", _pc), _ConectorFalso)
            threading.Thread(target=_sv.serve_forever, daemon=True).start()
            _sal = os.path.join(_TMP, f"crear_{tp}.json")
            try:
                _rn = subprocess.run(["node", os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "crear_en_programa.mjs"),
                                      _est_json, _dir_pl, f"http://127.0.0.1:{_pc}", tp, "JUGADOR", _sal],
                                     cwd=AQUI, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
            finally:
                _sv.shutdown()
            try:
                res = json.load(open(_sal, encoding="utf-8"))
            except Exception:
                res = {"error": (_rn.stderr or "")[-500:]}
            _esperados = sorted((x for x in est["archivos"] if x["tipo"] == tp and x["diseno"] == "JUGADOR"),
                                key=lambda x: int(str(x.get("parte") or "1").split()[0]))
            _bytes_esp = [open(os.path.join(_dir_pl, x["nombre"]), "rb").read() for x in _esperados]
            ok(res.get("ok") and [r_[2] for r_ in _ConectorFalso.recibidos] == _bytes_esp
               and all(r_[0] == "/plantilla" and r_[1] == "application/json" for r_ in _ConectorFalso.recibidos),
               f"crear_en_programa.js le manda al conector de {tp} el plan de TIZADA TAL CUAL, en orden "
               f"({len(_ConectorFalso.recibidos)} archivo/s, {res.get('mesas')} mesas{'' if res.get('ok') else ' · ' + str(res.get('error'))})")
            ok(any("versión nueva del conector" in x for x in res.get("avisos") or []),
               f"avisa que hay una versión nueva del conector, como el botón de TIZADA ({res.get('avisos')})")
            ok(res.get("sinConector") is None, "sin conector en esa computadora, `buscarConector` da null")
        c, cuerpo, _ = _bajar((tipos.get("guia") or {}).get("descarga") or "/x")
        ok(c == 200 and cuerpo[:4] in (b"%PDF", b"%!PS"), f"la guía .ai se baja y es un archivo de Illustrator ({c}, {cuerpo[:12]!r})")
        ok(all(k in (est.get("como_usar") or {}) for k in ("illustrator", "corel", "guia", "conectores")),
           "la respuesta dice cómo usar cada archivo y dónde están los conectores")

        c, d = _http("GET", api + "/conectores", llave=llave)
        cons = {x["clave"]: x for x in d.get("conectores") or []}
        ok(c == 200 and {"illustrator", "illustrator-mac", "corel"} <= set(cons),
           f"GET /conectores lista los instaladores: Illustrator (Windows y Mac) y CorelDRAW ({sorted(cons)})")
        c, _ = _http("GET", api + "/conectores")
        ok(c == 401, f"/conectores pide la llave ({c})")
        for k, firma, que in (("illustrator", b"MZ", "un .exe de Windows"), ("corel", b"MZ", "un .exe de Windows"),
                              ("illustrator-mac", b"PK", "un .zip con la extensión")):
            c, cuerpo, disp = _bajar((cons.get(k) or {}).get("descarga") or "/x")
            ok(c == 200 and cuerpo[:2] == firma and (cons.get(k) or {}).get("archivo", "") in disp,
               f"el conector «{k}» se baja ({que}, {len(cuerpo) // 1024} KB, {(cons.get(k) or {}).get('archivo')})")
        if cons.get("illustrator-mac"):
            c, cuerpo, _ = _bajar(cons["illustrator-mac"]["descarga"])
            with zipfile.ZipFile(io.BytesIO(cuerpo)) as z:
                nombres = z.namelist()
            ok(any(n.endswith("CSXS/manifest.xml") for n in nombres) and any(n.endswith("INSTALAR-MAC.command") for n in nombres),
               "el .zip de Mac trae la extensión (manifiesto) y su instalador")
        c, _ = _http("GET", api + "/conectores/no-existe", llave=llave)
        ok(c == 404, f"un conector que no existe: 404 ({c})")
    finally:
        VT._DOCS["catalogo"] = cat0

    # para mirarlos a mano: `py verificar_integracion_externa.py --guardar <carpeta>`
    if "--guardar" in sys.argv:
        dst = sys.argv[sys.argv.index("--guardar") + 1]
        shutil.copytree(os.path.join(S.DATOS, "externo", "salida"), dst, dirs_exist_ok=True)
        shutil.copy2(os.path.join(S.DATOS, "externo", "pedidos", "OV-2026-00123", "resultado.json"), os.path.join(dst, "resultado_OV-2026-00123.json"))
        shutil.copy2(os.path.join(S.DATOS, "externo", "pedidos", "OV-2026-00123", "paquete.zip"), os.path.join(dst, "paquete_OV-2026-00123.zip"))
        shutil.copytree(os.path.join(S.DATOS, "externo"), os.path.join(dst, "externo"), dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("paquete.zip", "archivos", "salida", "robot.token", "drive_cuenta.json"))
        print("  (salida copiada a", dst + ")")
    srv.shutdown()

    print()
    if FALLOS:
        print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
        for f in FALLOS:
            print("   ·", f)
        sys.exit(1)
    print("✅ CONTRATO VERDE — un pedido de otro sistema se hace solo, de punta a punta")


if __name__ == "__main__":
    import urllib.parse      # noqa: F401  (lo usa el Drive de mentira)
    try:
        main()
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
