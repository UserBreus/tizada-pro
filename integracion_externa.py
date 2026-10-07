# -*- coding: utf-8 -*-
"""
PEDIDOS QUE LLEGAN DE OTRO SISTEMA — sin que una persona toque la pantalla (MAPA 606).

Otro sistema (ventas) manda un PAQUETE (.zip con `pedido.json` + los artes + las tipografías) y
TIZADA PRO hace todos los pasos que hoy hace una persona: carga cada diseño con su molde y su
arte, las telas, las tipografías, lo que no se sublima (TPU/Bordado/DTF), la planilla; arma la
tizada, guarda los PDF en Google Drive y deja un JSON con dónde quedó cada cosa.

CÓMO ESTÁ PARTIDO (y por qué):
  · ESTE MÓDULO vive dentro del servidor web: recibe, REVISA LOS DATOS (todo lo que se puede decir
    sin abrir un archivo), guarda el paquete, lleva el estado y arma el JSON final. No calcula.
  · EL ROBOT (`robot/robot.mjs`, un proceso APARTE en Node) hace lo pesado con el MISMO motor que
    usa el navegador: lee el arte, lo sube por las rutas de siempre (`/api/arte`), arma la tizada
    (`generarPedidoEnNavegador`) y sube los PDF a Drive. La regla «el proceso web no calcula»
    (MAPA 528) se mantiene: el robot es, para el servidor, una computadora más.
  · NADA DEL USUARIO SE PISA: cada diseño que llega se guarda con un nombre interno propio del
    pedido (`x-<huella>-<nombre>`, marcado `externo`), nunca sobre un diseño cargado a mano.

RUTAS:
  /api/externo/v1/…      el otro sistema, con `X-Api-Key`
  /api/externo/robot/…   el robot, con `X-Robot-Token` (sale de `datos/externo/robot.token`)
  /api/integracion/…     la pantalla Configuración › Integraciones (sesión + `config.editar`)

EL FORMATO del paquete y de la respuesta está explicado en
`documentacion/integracion_externa/FORMATO_PEDIDO.md` (y un ejemplo al lado).
"""
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import shutil
import threading
import time
import urllib.parse
import urllib.request
import zipfile

from flask import Blueprint, g, has_request_context, jsonify, request, send_file

FORMATO = "tizadapro.pedido/1"
FORMATO_RESULTADO = "tizadapro.resultado/1"
PROCESOS = ("sublimado", "tpu", "bordado", "dtf")       # lo que puede llevar un objeto editable
EXT_ARTE = (".ai", ".pdf")
EXT_FUENTE = (".ttf", ".otf")
MAX_ZIP_MB = 600                  # el paquete entero
MAX_ARCHIVOS = 400
ESPERA_ROBOT_S = 20 * 60          # un pedido «procesando» sin noticias del robot vuelve a la cola

bp = Blueprint("externo", __name__)
S = None                          # el módulo `servidor` (lo pone `iniciar`): rutas, catálogo, reglas
_LOCK = threading.RLock()         # un solo proceso web: alcanza con un candado en memoria


def iniciar(servidor):
    """Lo llama `servidor.py` al registrar el blueprint: le pasa el módulo para usar SUS reglas
    (las mismas de la pantalla) en vez de copiarlas."""
    global S
    S = servidor


# ══ ARCHIVOS DE ESTE MÓDULO (todo bajo `datos/externo/`) ═══════════════════════════════════════
def _raiz():
    # (`TIZADA_EXTERNO` sólo para mirar la pantalla con datos de muestra, sin tocar los de verdad)
    return os.environ.get("TIZADA_EXTERNO") or os.path.join(S.DATOS, "externo")


def _dir_pedido(ref):
    return os.path.join(_raiz(), "pedidos", ref)


def _leer_json(ruta, defecto=None):
    try:
        with open(ruta, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return defecto


def _escribir_json(ruta, obj):
    """`.tmp` + `os.replace`: nunca un archivo a medias (ver memoria «escrituras atómicas»)."""
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    tmp = f"{ruta}.{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, ruta)


def _ahora():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


# ── configuración: llaves, Drive, robot ────────────────────────────────────────────────────
def _cfg():
    c = _leer_json(os.path.join(_raiz(), "config.json"), None) or {}
    c.setdefault("llaves", [])
    c.setdefault("drive", {"activo": False, "carpeta_id": ""})
    c.setdefault("robot", {"activo": True})
    c.setdefault("aviso_url", "")
    c.setdefault("dias_guardado", 30)
    return c


def _cfg_guardar(c):
    _escribir_json(os.path.join(_raiz(), "config.json"), c)


def _huella(texto):
    return hashlib.sha256(str(texto).encode("utf-8")).hexdigest()


def robot_token():
    """La llave del robot: un secreto al azar en `datos/externo/robot.token`. El robot corre en
    esta misma máquina y lo lee de ahí (o de la variable `TIZADA_ROBOT_TOKEN` que le pasa el
    servidor al arrancarlo). No viaja por ninguna ruta."""
    ruta = os.path.join(_raiz(), "robot.token")
    with _LOCK:
        try:
            t = open(ruta, encoding="ascii").read().strip()
            if len(t) >= 32:
                return t
        except Exception:
            pass
        t = secrets.token_urlsafe(48)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        tmp = ruta + ".tmp"
        with open(tmp, "w", encoding="ascii") as fh:
            fh.write(t)
        os.replace(tmp, ruta)
        return t


def _es_robot():
    t = request.headers.get("X-Robot-Token") or ""
    return bool(t) and hmac.compare_digest(t, robot_token())


def _llave_de_request():
    """La llave (`X-Api-Key`) con la que llama el otro sistema, o None. Se guarda sólo su huella."""
    k = (request.headers.get("X-Api-Key") or "").strip()
    if not k:
        return None
    h = _huella(k)
    for ll in _cfg()["llaves"]:
        if ll.get("activa", True) and hmac.compare_digest(str(ll.get("huella") or ""), h):
            return ll
    return None


_PERMISOS_ROBOT = None


def usuario_de_request():
    """Para `servidor._usuario_actual`: quién es el que llama cuando NO es una persona.

    · el ROBOT entra a las rutas de siempre (subir el arte, pedir el plan, guardar la tizada) como
      un usuario propio con todos los permisos de trabajo;
    · el OTRO SISTEMA sólo existe dentro de `/api/externo/v1/` y no tiene ningún permiso: las
      reglas del pedido se corren con él para que los moldes privados de un usuario no se le abran.
    Devuelve None para todo lo demás (sigue la sesión normal)."""
    global _PERMISOS_ROBOT
    if S is None or not has_request_context():
        return None
    memo = getattr(g, "_usuario_externo", False)
    if memo is not False:
        return memo
    u = None
    try:
        if request.headers.get("X-Robot-Token") and _es_robot():
            if _PERMISOS_ROBOT is None:
                import auth
                _PERMISOS_ROBOT = [p[0] for p in auth.PERMISOS if not p[0].startswith("usuario.")]
            u = {"id": None, "usuario": "robot", "nombre": "Robot de integración", "roles": ["robot"],
                 "permisos": list(_PERMISOS_ROBOT), "robot": True}
        elif request.path.startswith("/api/externo/v1/"):
            ll = _llave_de_request()
            if ll:
                u = {"id": None, "usuario": "externo:" + str(ll.get("id")), "nombre": ll.get("nombre") or "Sistema externo",
                     "roles": ["externo"], "permisos": [], "externo": True}
    except Exception:
        u = None
    g._usuario_externo = u
    return u


@bp.before_request
def _puerta():
    """Cada tramo con su llave. (`/api/externo/` está fuera de la guardia de sesión del servidor.)"""
    p = request.path
    if p.startswith("/api/externo/robot/"):
        if not _es_robot():
            return jsonify({"error": "llave de robot inválida"}), 401
        return None
    if p.startswith("/api/externo/v1/"):
        if p.endswith("/v1/formato") or p.endswith("/v1/alarmas"):
            return None                              # documentación: no revela nada del taller
        ll = _llave_de_request()
        if not ll:
            return jsonify({"error": "falta la llave o no es válida (encabezado X-Api-Key)"}), 401
        g._llave = ll
        return None
    if p == "/api/integracion/drive/vuelta":
        return None                                  # la valida su `state` (ver `adm_drive_vuelta`)
    if p.startswith("/api/integracion/"):
        return S._guard_permiso("config.editar")     # la sesión ya la pidió la guardia del servidor
    return None


# ══ LAS ALARMAS: el catálogo completo (se publica en /api/externo/v1/alarmas) ══════════════════
# etapa: «datos» = se detecta al recibir el paquete, sin abrir ningún archivo (contesta en el acto)
#        «arte»  = al leer el arte y las tipografías (lo hace el robot, segundos después)
#        «tizada»= al armar la tizada
# frena: True = el pedido se RECHAZA y no sale nada · False = aviso, el pedido sigue
ALARMAS = {
    # ── el paquete ──
    "paquete-ilegible":        ("datos", True,  "El paquete no es un .zip válido o está dañado.", "Volver a armar el .zip."),
    "paquete-muy-grande":      ("datos", True,  "El paquete supera el tamaño o la cantidad de archivos permitidos.", f"Hasta {MAX_ZIP_MB} MB y {MAX_ARCHIVOS} archivos."),
    "paquete-sin-pedido":      ("datos", True,  "El paquete no trae `pedido.json` en la raíz.", "Agregar pedido.json."),
    "pedido-json-invalido":    ("datos", True,  "`pedido.json` no es un JSON válido.", "Revisar comas, comillas y que esté en UTF-8."),
    "formato-desconocido":     ("datos", True,  "El campo `formato` no es el que este sistema entiende.", f"Usar \"{FORMATO}\"."),
    "campo-falta":             ("datos", True,  "Falta un campo obligatorio.", "Ver el campo indicado en `donde`."),
    "campo-tipo":              ("datos", True,  "Un campo vino con un tipo que no corresponde (texto, lista, objeto…).", "Ver el campo indicado."),
    "referencia-invalida":     ("datos", True,  "La referencia sólo puede tener letras, números, punto, guion y guion bajo (hasta 64).", "Cambiar la referencia."),
    "referencia-en-proceso":   ("datos", True,  "Ya hay un pedido con esa referencia que se está procesando.", "Esperar a que termine o cancelarlo."),
    "referencia-ya-generada":  ("datos", True,  "Ese pedido ya se generó. No se pisa una tizada hecha.", "Mandar con `reemplazar: true` o con otra referencia."),
    "archivo-falta":           ("datos", True,  "El pedido nombra un archivo que no vino en el paquete.", "Agregar el archivo o corregir la ruta."),
    "archivo-ruta-invalida":   ("datos", True,  "Una ruta de archivo sale de la carpeta del paquete.", "Usar rutas relativas simples (artes/jugador.ai)."),
    "arte-formato":            ("datos", True,  "El arte tiene que ser .ai (con PDF compatible) o .pdf.", "Guardar el arte en uno de esos formatos."),
    "tipografia-formato":      ("datos", True,  "La tipografía tiene que ser .ttf u .otf.", "Mandar el archivo de la fuente en uno de esos formatos."),
    # ── diseños y moldes ──
    "disenos-vacio":           ("datos", True,  "El pedido no trae ningún diseño.", "Mandar al menos un diseño con su molde."),
    "diseno-repetido":         ("datos", True,  "Dos diseños tienen el mismo nombre.", "El nombre de cada diseño es único dentro del pedido."),
    "diseno-sin-moldes":       ("datos", True,  "Un diseño no dice qué molde usa.", "Cada diseño lleva al menos un molde."),
    "molde-desconocido":       ("datos", True,  "El código de molde no existe en TIZADA PRO.", "Elegirlo de la lista que publica /moldes."),
    "molde-no-disponible":     ("datos", True,  "El molde existe pero no está listo para pedidos externos (es propio de un usuario, temporal, trae el diseño adentro o no tiene sus piezas nombradas).", "Usar un molde del catálogo marcado `listo`."),
    "molde-repetido":          ("datos", True,  "El mismo molde aparece dos veces en un diseño (dos variables de la misma prenda).", "Una variable por prenda en cada diseño."),
    "variable-ambigua":        ("datos", True,  "Ese nombre de variable existe en más de una prenda y el pedido no dice cuál.", "Mandar la `variable` por su clave (`v_…`) o agregar `molde`."),
    "arte-falta":              ("datos", True,  "Un molde de un diseño no tiene arte (ni propio ni el del diseño).", "Indicar `arte` en el diseño o en el molde."),
    "variable-falta":          ("datos", True,  "El molde tiene varias variables y el pedido no dice cuál.", "Indicar `variable` (nombre o clave)."),
    "variable-desconocida":    ("datos", True,  "La variable indicada no existe (o no en ese molde).", "Usar una de las que publica /variables."),
    "planillas-distintas":     ("datos", True,  "Los moldes del pedido usan planillas distintas.", "Todos los moldes de un pedido comparten la misma planilla; si no, van en pedidos separados."),
    "sin-columna-diseno":      ("datos", True,  "El pedido trae más de un diseño para un molde y su planilla no tiene columna de diseño.", "Un diseño por pedido, o usar una planilla con columna «Diseño»."),
    # ── telas ──
    "tela-falta":              ("datos", True,  "Un molde no dice en qué tela se corta.", "Indicar `tela` (el id del sistema de telas)."),
    "tela-desconocida":        ("datos", True,  "El id de tela no existe en el registro de telas.", "Usar un id de los que publica /telas."),
    "tela-no-usable":          ("datos", True,  "La tela está dada de baja o no tiene medida.", "Elegir otra tela."),
    "tela-no-permitida":       ("datos", True,  "El molde no admite esa tela (o no para esa pieza).", "Usar una de las telas que publica el molde."),
    "pieza-desconocida":       ("datos", True,  "Se nombró una pieza que el molde no tiene.", "Usar el nombre genérico de la pieza, sin número («Manga», no «Manga 2»)."),
    "pieza-sin-tela":          ("datos", True,  "Hay piezas que quedarían sin tela.", "Indicar la tela principal o la de esas piezas."),
    "todas-las-piezas-apagadas": ("datos", True, "Se apagaron todas las piezas de un molde: no saldría nada.", "Dejar al menos una pieza prendida."),
    # ── objetos editables ──
    "editable-proceso-invalido": ("datos", True, "El proceso de un objeto editable no es válido.", "Usar: " + ", ".join(PROCESOS) + "."),
    "editable-desconocido":    ("arte",  True,  "El pedido nombra un objeto editable que el arte no tiene.", "El nombre es el de la capa sin la palabra «Editable» («Editable escudo» → escudo)."),
    "editable-sin-declarar":   ("arte",  False, "El arte trae un objeto editable que el pedido no menciona: sale sublimado.", "Declararlo en `editables` si lleva otro proceso."),
    # ── planilla ──
    "planilla-vacia":          ("datos", True,  "La planilla no trae filas.", "Una fila por prenda."),
    "columna-desconocida":     ("datos", False, "La fila trae una columna que la planilla del molde no tiene: se ignora.", "Usar los ids de columna que publica el molde."),
    "columna-obligatoria-vacia": ("datos", True, "A una fila le falta un dato obligatorio para fabricar.", "Completar la columna indicada."),
    "fila-diseno-desconocido": ("datos", True,  "Una fila pide un diseño que el pedido no trae.", "El valor tiene que ser el `nombre` de uno de los diseños."),
    "talle-inexistente":       ("datos", True,  "Una fila pide un talle que el molde no tiene.", "Usar los talles que publica el molde, tal cual."),
    "medida-falta":            ("datos", True,  "El molde es A MEDIDA (un rectángulo) y no trae su medida.", "Mandar `medida: {ancho_m, alto_m}` (metros) en ese molde."),
    "medida-invalida":         ("datos", True,  "La medida tiene que ser metros, de 0,05 a 50.", "Mandar números con punto: `{\"ancho_m\": 1.5, \"alto_m\": 0.9}`."),
    "tela-no-entra":           ("datos", True,  "La pieza a medida no entra en la tela elegida (su ancho imprimible o el largo máximo de la mesa).", "Elegir una tela más ancha o una medida menor."),
    "talle-sin-columna":       ("datos", True,"La planilla del molde no tiene columna de talle, pero el molde tiene varios talles: no se sabe de cuál es cada fila.", "Avisar al que administra TIZADA: ese molde necesita una planilla con columna de talle."),
    "opcion-inexistente":      ("datos", True,  "Una fila trae un valor que no está entre las opciones de esa columna.", "Usar una de las opciones publicadas."),
    "opcion-sin-piezas":       ("datos", True,  "Una fila pide una opción (p. ej. manga larga) que el molde no tiene.", "Elegir una opción que el molde sí tenga."),
    "cantidad-invalida":       ("datos", True,  "La cantidad tiene que ser un número entero de 1 en adelante.", "Corregir la cantidad."),
    "mesas-invalido":          ("datos", True,  "La forma de repartir las mesas no se entiende o nombra un talle que no existe.", "Ver `mesas` en el formato."),
    "pedido-rechazado-por-reglas": ("datos", True, "Las reglas del pedido (las mismas de la pantalla) lo rechazaron.", "Leer el mensaje: dice qué fila o qué pieza."),
    "aviso-url-no-permitida":  ("datos", False, "La dirección de aviso del pedido no es del mismo sitio que la configurada: se usa la configurada.", "Configurarla en Integraciones."),
    # ── arte ──
    "arte-ilegible":           ("arte",  True,  "El arte no se pudo abrir (dañado, o un .ai guardado sin «Crear archivo compatible con PDF»).", "Volver a guardarlo."),
    "arte-sin-mesas-de-pieza": ("arte",  True,  "El arte no trae una mesa por pieza con su nombre en la capa de guías (es otro tipo de archivo).", "Armar el arte desde la base que da TIZADA PRO para ese molde."),
    "arte-pieza-sin-mesa":     ("arte",  False, "Hay piezas del molde que el arte no cubre. Si alguna de ellas se fabrica en este pedido, frena como `piezas-en-blanco`.", "Agregar la mesa de esas piezas con su nombre en la capa «guias»."),
    "arte-mesa-vacia":         ("arte",  True,  "Una mesa asignada a una pieza SIN nombre en la guía no tiene diseño (las mesas con el nombre de su pieza no se revisan: manda el nombre, sea del color que sea).", "Revisar esa mesa del arte o escribirle el nombre de la pieza en la capa «guias»."),
    "arte-texto-vivo":         ("arte",  True,  "El diseño trae texto sin convertir a curvas.", "Illustrator: Texto → Crear contornos · Corel: Objeto → Convertir en curvas."),
    "arte-variante-sin-cubrir": ("arte", False, "Con mesas por talle (#talle/#rango), algún talle queda sin diseño en una pieza.", "Agregar la mesa de ese talle o una mesa sin #."),
    "arte-campo-sin-capa":     ("arte",  False, "La planilla trae texto o número y el arte no tiene esa capa: no se estampa.", "Agregar la capa «Texto» (o «Nombre») / «Número» al arte."),
    "arte-observado":          ("arte",  False, "La revisión del arte dejó una observación.", "Leer el mensaje."),
    # ── tipografías ──
    "tipografia-falta":        ("arte",  True,  "El texto o el número usa una tipografía que no está en el catálogo ni vino en el paquete.", "Mandarla en `tipografias`, o pedir `si_falta_tipografia: \"predeterminada\"`."),
    "tipografia-reemplazada":  ("arte",  False, "Faltaba una tipografía y se usó la predeterminada, como pidió el pedido.", "—"),
    "tipografia-invalida":     ("arte",  True,  "Un archivo de tipografía no se pudo leer.", "Mandar otro archivo de esa fuente."),
    # ── tizada ──
    "texto-se-achica":         ("tizada", False, "Un texto o número no entra en la pieza y sale más chico.", "Acortar el texto o cambiar el margen en el molde."),
    "texto-ilegible":          ("tizada", False, "Un texto o número sale tan chico que puede no leerse.", "Acortar el texto."),
    "piezas-en-blanco":        ("tizada", True,  "Hay piezas de las que se fabrican que el arte no cubre: saldrían en blanco.", "Agregar su mesa al arte, apagarlas en `piezas_apagadas`, o pedir `si_piezas_en_blanco: \"seguir\"`."),
    "aviso-del-pedido":        ("tizada", False, "El plan del pedido dejó un aviso.", "Leer el mensaje."),
    "caracter-imposible":      ("tizada", True,  "Un carácter del texto no se puede estampar con ninguna tipografía.", "Sacar ese carácter."),
    "pieza-no-entra":          ("tizada", True,  "Una pieza no entra en el ancho de la tela con ninguna rotación.", "Usar una tela más ancha."),
    "tizada-fallo":            ("tizada", True,  "La tizada no se pudo armar.", "Leer el mensaje; si es una falla del sistema, se puede reintentar."),
    # ── salida ──
    "drive-sin-configurar":    ("tizada", False, "Google Drive no está configurado: los PDF quedaron guardados en el servidor.", "Configurar Drive en Integraciones y reintentar la subida."),
    "drive-fallo":             ("tizada", False, "No se pudo subir a Google Drive: los PDF quedaron guardados en el servidor.", "Revisar la cuenta de servicio y la carpeta; reintentar."),
    # ── plantillas (la base para el diseñador, MAPA 619) ──
    "plantilla-sin-variables": ("datos", True,  "Un diseño de la plantilla no trae variables.", "Mandar al menos una variable por diseño."),
    "talles-invalidos":        ("datos", True,  "El modo de talles no se entiende o nombra un talle que ninguna variable tiene.", "Usar `todos`, `rango` (con `rangos`) o `por_talle` (con `talles`) y los talles que publica cada molde."),
    "escala-invalida":         ("datos", True,  "La escala de Illustrator tiene que ser 100, 90, 80… o 10.", "Mandar uno de esos números (100 = tamaño real)."),
    "plantilla-mesas-chocan":  ("plantilla", False, "En el archivo de un diseño hay dos piezas distintas con el mismo nombre de mesa: al subir el arte se usaría la primera para las dos.", "Si llevan diseños distintos, pedir esas variables en diseños separados."),
    "plantilla-aviso":         ("plantilla", False, "Aviso al armar la plantilla.", "Leer el mensaje."),
    "plantilla-fallo":         ("plantilla", True,  "La plantilla no se pudo armar.", "Leer el mensaje; si es una falla del sistema, volver a pedirla."),
}


def alarma(codigo, mensaje=None, **donde):
    etapa, frena, texto, _que = ALARMAS[codigo]
    a = {"codigo": codigo, "frena": frena, "etapa": etapa, "mensaje": mensaje or texto}
    d = {k: v for k, v in donde.items() if v is not None and v != ""}
    if d:
        a["donde"] = d
    return a


def _frenan(alarmas):
    return [a for a in alarmas if a.get("frena")]


# ══ LO QUE TIZADA PUBLICA (para que el otro sistema elija y revise ANTES de mandar) ════════════
_gen = lambda s: re.sub(r"\s+\d+\s*$", "", str(s)).strip()            # «Manga 2» → «Manga»
_norm = lambda s: re.sub(r"\s+", " ", str(s or "")).strip().lower()


def _telas_por_id(cat):
    return {str(t.get("id")): t for t in (cat.get("telas") or [])}


def _plantilla_de(prod, cat):
    return next((t for t in cat.get("plantillas_planillas", [])
                 if t.get("id") == (prod or {}).get("planilla_template_id")), None)


def _opciones_de_columna(col, cat):
    """Las opciones fijas de una columna (toggle o desplegable con lista), o None si es libre."""
    regla = next((r for r in cat.get("reglas_planilla", []) if r.get("id") == col.get("reglaId")), None)
    if regla is None and col.get("role") == "manga":
        regla = next((r for r in cat.get("reglas_planilla", []) if r.get("comportamiento") == "manga"), None)
    crudo = col.get("opciones") or (regla or {}).get("opciones") or ("Corta, Larga" if col.get("role") == "manga" else "")
    ops = [o.strip() for o in str(crudo).split(",") if o.strip()]
    return ops or None


def _molde_listo(prod, reg):
    """¿Sirve para un pedido externo? Sólo moldes del catálogo, con sus piezas nombradas y con el
    arte aparte (camino A). Devuelve (bool, motivo)."""
    if not prod:
        return False, "no existe"
    if prod.get("efimero"):
        return False, "es un molde temporal de un pedido"
    if S._es_privado(prod):
        return False, "es un molde propio de un usuario"
    if not reg:
        return False, "no tiene sus piezas nombradas"
    try:
        if S._es_camino_b(prod["id"]):
            return False, "trae el diseño adentro del molde (todavía no se admite por esta vía)"
    except Exception:
        pass
    return True, ""


def _medida_del_pedido(m, prod, cat, tela_p, tpp, telas, cm, nom, A):
    """La MEDIDA de un molde a medida en el pedido (`medida: {ancho_m, alto_m}`, o los dos campos
    sueltos): que esté, que sea válida y que la pieza entre en sus telas (regla del usuario
    2026-10-06). Devuelve `{ancho_m, alto_m}` o None (con la alarma puesta)."""
    md = m.get("medida") if isinstance(m.get("medida"), dict) else {"ancho_m": m.get("ancho_m"), "alto_m": m.get("alto_m")}
    if md.get("ancho_m") in (None, "") or md.get("alto_m") in (None, ""):
        A.append(alarma("medida-falta", f"«{prod.get('nombre')}» en «{nom}»", campo=cm + ".medida"))
        return None
    an, al = S._metros(md.get("ancho_m")), S._metros(md.get("alto_m"))
    if an is None or al is None:
        A.append(alarma("medida-invalida", f"«{md.get('ancho_m')} × {md.get('alto_m')}» en «{prod.get('nombre')}»", campo=cm + ".medida"))
        return None
    pub = S._a_medida_publico(prod, cat) or {}
    n = pub.get("nesting") or {}
    por_nombre = {str(t.get("nombre")): t for t in telas.values()}
    for t in [tela_p] + [por_nombre.get(x) for x in (tpp or {}).values()]:
        if not t:
            continue
        ok, mot = S._cabe_en_tela(an, al, pub.get("borde_mm") or 0, t.get("ancho_cm") or 180, n.get("alto_max_cm") or 500,
                                  n.get("margen_mm") or 0, n.get("rotacion") or "auto")
        if not ok:
            A.append(alarma("tela-no-entra", f"«{prod.get('nombre')}» de {S._talle_de_medida(an, al)} m en «{t.get('nombre')}»: {mot}",
                            campo=cm + ".tela"))
            return None
    return {"ancho_m": an, "alto_m": al}


def _a_medida_publico_ext(prod):
    """Lo que el otro sistema tiene que saber de un molde A MEDIDA (MAPA 623), o None."""
    am = (prod or {}).get("a_medida")
    if not isinstance(am, dict) or am.get("de"):
        return None
    mg = am.get("margen") or {}
    t = float(mg.get("todos") or 0)
    return {"pieza": am.get("pieza"), "pide": "medida: {ancho_m, alto_m} en metros",
            "margen_cm": {k: float(mg[k]) if mg.get(k) not in (None, "") else t for k in ("arriba", "abajo", "izq", "der")}}


def _columna_talle_que_lee(prod, cols):
    """El id de la columna de la planilla de la que este molde lee el talle, o None si no lee
    ninguna (PLANILLA SIN TALLES, MAPA 622). Mismo criterio que `_traducir_prendas`: la que el molde
    mapea; si mapea una que la planilla no tiene, la primera de talle (`_hay_fallback`)."""
    ct = [c for c in (cols or []) if c.get("role") == "talle"]
    if not ct:
        return None
    mc = (prod or {}).get("mapeo_columnas") or {}
    quiere = mc.get("talle") if "talle" in mc else "talle"
    if not quiere:
        return None                       # el molde la tiene apagada
    return quiere if quiere in {str(c.get("id")) for c in ct} else str(ct[0].get("id"))


def molde_publico(prod, cat, detalle=True):
    """Todo lo que el otro sistema necesita de un molde para armar (y revisar) un pedido."""
    pid = prod["id"]
    try:
        reg = S._cargar("registro_producto.json", pid) or {}
    except Exception:
        reg = {}
    listo, motivo = _molde_listo(prod, reg)
    out = {"codigo": pid, "nombre": prod.get("nombre") or pid, "listo": listo}
    if not listo:
        out["motivo"] = motivo
    if not detalle or not listo:
        return out
    tpl = _plantilla_de(prod, cat) or {}
    mc = prod.get("mapeo_columnas") or {}
    cols = []
    for c in (tpl.get("columnas") or []):
        if c.get("role") == "cantidad" and c.get("mostrar") == "no":
            continue                   # esta planilla no tiene Cantidad (2026-10-06): no se publica
        col = {"id": c.get("id"), "titulo": c.get("label"), "rol": c.get("role") or "dato",
               "obligatoria": bool(c.get("obligatoria"))}
        ops = _opciones_de_columna(c, cat)
        if c.get("role") == "talle":
            col["lee_este_molde"] = (c.get("id") == (mc.get("talle") or "talle"))
        elif c.get("role") == "diseno":
            col["opciones"] = "los nombres de los diseños del pedido"
        elif ops:
            col["opciones"] = ops
        cols.append(col)
    variables = []
    for v in (prod.get("variantes") or []):
        cl = v.get("clave")
        if not cl:
            continue
        pz = sorted(S._piezas_de_variable(prod, cl, reg) or [])
        variables.append({"clave": cl, "nombre": v.get("label") or cl, "piezas": sorted({_gen(p) for p in pz}),
                          "piezas_exactas": pz})
    tcfg = S._telas_cfg_prod(prod) if hasattr(S, "_telas_cfg_prod") else (prod.get("telas_cfg") or {})
    tid = _telas_por_id(cat)
    def _tela(i):
        t = tid.get(str(i)) or {}
        return {"id": str(i), "nombre": t.get("nombre"), "ancho_mesa_cm": t.get("ancho_cm"), "usable": bool(t.get("usable"))}
    try:
        tog = S._toggles_disponibles(prod, cat, reg) or {}
    except Exception:
        tog = {}
    opciones = {}
    for clave, d in tog.items():
        _tiene = lambda sop: [o for o in d.get("opciones", []) if int((sop or {}).get(str(o).strip().lower(), 0) or 0) > 0]
        opciones[clave] = {"columna": d.get("col"), "opciones": d.get("opciones", []),
                           "distingue": not S._toggle_no_distingue(d.get("*")),
                           "tiene": {"*": _tiene(d.get("*")), **{k: _tiene(v) for k, v in d.items()
                                                                 if isinstance(v, dict) and k.startswith("v_")}}}
    out.update({
        "talles": S._talles_de_registro(reg, pid),
        "piezas": sorted({_gen(p) for p in reg.keys()}),
        "variables": variables,
        # `columna_talle: null` = la planilla NO lleva talle (MAPA 622): las filas van sin talle
        "planilla": {"id": tpl.get("id"), "nombre": tpl.get("nombre"), "columnas": cols,
                     "columna_talle": _columna_talle_que_lee(prod, tpl.get("columnas") or []),
                     "con_talles": _columna_talle_que_lee(prod, tpl.get("columnas") or []) is not None},
        "opciones_de_pieza": opciones,
        "a_medida": _a_medida_publico_ext(prod),
        "telas": {"todas": [_tela(i) for i in (tcfg.get("todas") or [])],
                  "por_pieza": {k: [_tela(i) for i in v] for k, v in (tcfg.get("por_pieza") or {}).items()}},
        "foto": f"/api/externo/v1/moldes/{pid}/foto",
    })
    return out


def _version_catalogo():
    """Sube cada vez que cambia el catálogo: el otro sistema la guarda y sabe cuándo refrescar."""
    try:
        return S._catalogo_rev()
    except Exception:
        return None


# ══ REVISAR EL PEDIDO (etapa «datos»: sin abrir ningún archivo) ════════════════════════════════
_RX_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def _slug_interno(ref, nombre):
    """El nombre con el que se guarda el diseño en el molde: propio del pedido, para no pisar jamás
    un diseño cargado a mano. Ya viene en la forma que deja `_slugify_diseno` (no lo cambia)."""
    base = re.sub(r"[^a-z0-9]+", "-", _norm(nombre)).strip("-")[:28] or "diseno"
    return f"x-{_huella(ref)[:8]}-{base}"


def _ruta_segura(nombre):
    n = str(nombre or "").replace("\\", "/").strip()
    if not n or n.startswith("/") or re.match(r"^[A-Za-z]:", n) or any(p in ("", ".", "..") for p in n.split("/")):
        return None
    return n


def revisar_datos(pedido, archivos, estado_previo=None):
    """Todo lo que se puede decir del pedido SIN abrir un archivo. `archivos` = los nombres que
    vinieron en el paquete. Devuelve `(alarmas, normal)`; `normal` (None si algo frena antes) es el
    pedido ya traducido a lo que usa la pantalla: códigos internos, nombres de tela, variables."""
    A = []
    if not isinstance(pedido, dict):
        return [alarma("campo-tipo", "pedido.json tiene que ser un objeto { … }")], None
    if pedido.get("formato") != FORMATO:
        A.append(alarma("formato-desconocido", f"formato «{pedido.get('formato')}»; se esperaba «{FORMATO}»", campo="formato"))
    ref = pedido.get("referencia")
    if not isinstance(ref, str) or not ref.strip():
        A.append(alarma("campo-falta", "falta `referencia` (el número del pedido en el otro sistema)", campo="referencia"))
        ref = None
    elif not _RX_REF.match(ref.strip()):
        A.append(alarma("referencia-invalida", campo="referencia"))
        ref = None
    else:
        ref = ref.strip()
        ep = estado_previo if estado_previo is not None else leer_estado(ref)
        if ep:
            if ep.get("estado") in ("en_cola", "procesando"):
                A.append(alarma("referencia-en-proceso", campo="referencia"))
            elif ep.get("estado") == "listo" and not pedido.get("reemplazar"):
                A.append(alarma("referencia-ya-generada", campo="referencia"))
    for k, tipo in (("pedido_externo", dict), ("opciones", dict), ("mesas", dict), ("cliente", str)):
        if pedido.get(k) is not None and not isinstance(pedido.get(k), tipo):
            A.append(alarma("campo-tipo", f"`{k}` vino con un tipo que no corresponde", campo=k))
    disenos = pedido.get("disenos")
    if not isinstance(disenos, list) or not disenos:
        A.append(alarma("disenos-vacio", campo="disenos"))
        return A, None
    filas = pedido.get("planilla")
    if not isinstance(filas, list) or not filas:
        A.append(alarma("planilla-vacia", campo="planilla"))
        filas = []
    if _frenan(A) and ref is None:
        return A, None

    cat = S._cargar_catalogo()
    prods = {p["id"]: p for p in cat.get("productos", [])}
    telas = _telas_por_id(cat)
    nombres_zip = {str(n).replace("\\", "/") for n in (archivos or [])}
    sin_may = {n.lower(): n for n in nombres_zip}
    opc = pedido.get("opciones") if isinstance(pedido.get("opciones"), dict) else {}

    def _archivo(valor, campo, exts, cod_formato):
        if valor is None:
            return None
        r = _ruta_segura(valor)
        if r is None:
            A.append(alarma("archivo-ruta-invalida", f"ruta «{valor}»", campo=campo))
            return None
        real = r if r in nombres_zip else sin_may.get(r.lower())
        if real is None:
            A.append(alarma("archivo-falta", f"«{r}» no vino en el paquete", campo=campo))
            return None
        if not real.lower().endswith(exts):
            A.append(alarma(cod_formato, f"«{r}»", campo=campo))
            return None
        return real

    def _tela(valor, campo, prod, pieza=None):
        """id de tela → su ficha, o None (con la alarma puesta)."""
        t = telas.get(str(valor).strip()) if valor is not None else None
        if t is None:
            A.append(alarma("tela-desconocida", f"tela «{valor}»", campo=campo))
            return None
        if not t.get("usable"):
            A.append(alarma("tela-no-usable", f"la tela «{t.get('nombre')}» (id {t.get('id')}) no se puede usar", campo=campo))
            return None
        tcfg = S._telas_cfg_prod(prod)
        permitidas = {str(x) for x in (tcfg.get("todas") or [])}
        if pieza:
            permitidas |= {str(x) for k, v in (tcfg.get("por_pieza") or {}).items() if _norm(k) == _norm(pieza) for x in v}
        if (tcfg.get("todas") or tcfg.get("por_pieza")) and str(t.get("id")) not in permitidas:
            A.append(alarma("tela-no-permitida", f"«{prod.get('nombre')}» no admite la tela «{t.get('nombre')}» (id {t.get('id')})"
                            + (f" en «{pieza}»" if pieza else ""), campo=campo))
            return None
        return t

    norm_d, vistos, tpl_ids = [], set(), set()
    for i, d in enumerate(disenos):
        cd = f"disenos[{i}]"
        if not isinstance(d, dict):
            A.append(alarma("campo-tipo", f"`{cd}` tiene que ser un objeto", campo=cd)); continue
        nom = str(d.get("nombre") or "").strip()
        if not nom:
            A.append(alarma("campo-falta", f"`{cd}.nombre`", campo=cd + ".nombre")); continue
        if _norm(nom) in vistos:
            A.append(alarma("diseno-repetido", f"«{nom}»", campo=cd + ".nombre")); continue
        vistos.add(_norm(nom))
        arte_d = _archivo(d.get("arte"), cd + ".arte", EXT_ARTE, "arte-formato")
        fuentes_d = [x for x in (_archivo(f, f"{cd}.tipografias[{j}]", EXT_FUENTE, "tipografia-formato")
                                 for j, f in enumerate(d.get("tipografias") or [])) if x]
        moldes = d.get("moldes")
        if not isinstance(moldes, list) or not moldes:
            A.append(alarma("diseno-sin-moldes", f"«{nom}»", campo=cd + ".moldes")); continue
        nd = {"nombre": nom, "slug": _slug_interno(ref or "sin-ref", nom), "moldes": [],
              "tipografias": fuentes_d,
              "tipografia_por_campo": d.get("tipografia_por_campo") if isinstance(d.get("tipografia_por_campo"), dict) else {}}
        pids_d = set()
        for j, m in enumerate(moldes):
            cm = f"{cd}.moldes[{j}]"
            if isinstance(m, str):
                m = {"molde": m}
            if not isinstance(m, dict):
                A.append(alarma("campo-tipo", f"`{cm}`", campo=cm)); continue
            pid = str(m.get("molde") or "").strip()
            if not pid and str(m.get("variable") or "").strip():
                # EN TIZADA SE ELIGE LA VARIABLE, no el molde: el molde es sólo su contenedor. Se
                # busca por clave (única) y, si viene el nombre, sólo vale si una sola prenda lo tiene.
                pid, amb = _molde_de_variable(str(m.get("variable")).strip(), prods)
                if amb:
                    A.append(alarma("variable-ambigua", f"«{m.get('variable')}» está en: " + ", ".join(amb), campo=cm + ".variable")); continue
                if not pid:
                    A.append(alarma("variable-desconocida", f"«{m.get('variable')}»", campo=cm + ".variable")); continue
            prod = prods.get(pid)
            if not prod:
                A.append(alarma("molde-desconocido", f"«{pid}»" if pid else "falta `variable` (o `molde`)", campo=cm + ".molde")); continue
            if pid in pids_d:
                A.append(alarma("molde-repetido", f"«{prod.get('nombre')}» en «{nom}»", campo=cm + ".molde")); continue
            pids_d.add(pid)
            try:
                reg = S._cargar("registro_producto.json", pid) or {}
            except Exception:
                reg = {}
            listo, motivo = _molde_listo(prod, reg)
            if not listo:
                A.append(alarma("molde-no-disponible", f"«{prod.get('nombre')}»: {motivo}", campo=cm + ".molde")); continue
            tpl_ids.add(prod.get("planilla_template_id"))
            # la variable (por clave o por nombre)
            variantes = [v for v in (prod.get("variantes") or []) if v.get("clave")]
            vq = str(m.get("variable") or "").strip()
            vcl = None
            if vq:
                v = next((v for v in variantes if v["clave"] == vq or _norm(v.get("label")) == _norm(vq)), None)
                if v is None:
                    A.append(alarma("variable-desconocida", f"«{vq}» en «{prod.get('nombre')}» (tiene: "
                                    + ", ".join(str(v.get("label")) for v in variantes) + ")", campo=cm + ".variable"))
                else:
                    vcl = v["clave"]
            elif len(variantes) == 1:
                vcl = variantes[0]["clave"]
            elif len(variantes) > 1:
                A.append(alarma("variable-falta", f"«{prod.get('nombre')}» tiene: " + ", ".join(str(v.get("label")) for v in variantes),
                                campo=cm + ".variable"))
            piezas_var = sorted(S._piezas_de_variable(prod, vcl, reg) or []) if vcl else sorted(reg.keys())
            genericos = {_norm(_gen(p)): _gen(p) for p in (piezas_var or reg.keys())}
            todos_gen = {_norm(_gen(p)): _gen(p) for p in reg.keys()}
            # telas: la principal + las excepciones por pieza (nombre genérico)
            tela_p = None
            if m.get("tela") in (None, ""):
                A.append(alarma("tela-falta", f"«{prod.get('nombre')}» en «{nom}»", campo=cm + ".tela"))
            else:
                tela_p = _tela(m.get("tela"), cm + ".tela", prod)
            tpp = {}
            for pz, tv in (m.get("telas_por_pieza") or {}).items() if isinstance(m.get("telas_por_pieza"), dict) else []:
                g_ = todos_gen.get(_norm(_gen(pz)))
                if g_ is None:
                    A.append(alarma("pieza-desconocida", f"«{pz}» no es una pieza de «{prod.get('nombre')}»", campo=f"{cm}.telas_por_pieza.{pz}")); continue
                t = _tela(tv, f"{cm}.telas_por_pieza.{pz}", prod, pieza=g_)
                if t:
                    tpp[g_] = t["nombre"]
            fuera = []
            for pz in (m.get("piezas_apagadas") or []) if isinstance(m.get("piezas_apagadas"), list) else []:
                g_ = todos_gen.get(_norm(_gen(pz)))
                if g_ is None:
                    A.append(alarma("pieza-desconocida", f"«{pz}» no es una pieza de «{prod.get('nombre')}»", campo=f"{cm}.piezas_apagadas")); continue
                fuera.append(g_)
            if genericos and all(k in {_norm(x) for x in fuera} for k in genericos):
                A.append(alarma("todas-las-piezas-apagadas", f"«{prod.get('nombre')}» en «{nom}»", campo=cm + ".piezas_apagadas"))
            # lo que no se sublima: {objeto: proceso} o {objeto: {proceso, cruz}}
            marcas, sin_marca, declarados = {}, {}, []
            for obj, val in (m.get("editables") or {}).items() if isinstance(m.get("editables"), dict) else []:
                proc = val.get("proceso") if isinstance(val, dict) else val
                proc = str(proc or "").strip().lower()
                if proc not in PROCESOS:
                    A.append(alarma("editable-proceso-invalido", f"«{obj}»: «{proc}»", campo=f"{cm}.editables.{obj}")); continue
                declarados.append(str(obj))
                if proc != "sublimado":
                    marcas[str(obj)] = proc
                    if isinstance(val, dict) and val.get("cruz") is False:
                        sin_marca[str(obj)] = True
            # MOLDE A MEDIDA (MAPA 623): un rectángulo de una pieza; la medida viene en el pedido
            medida = None
            if isinstance(prod.get("a_medida"), dict):
                medida = _medida_del_pedido(m, prod, cat, tela_p, tpp, telas, cm, nom, A)
            arte = _archivo(m.get("arte"), cm + ".arte", EXT_ARTE, "arte-formato") if m.get("arte") else arte_d
            if not arte and not (m.get("arte") or d.get("arte")):
                A.append(alarma("arte-falta", f"«{prod.get('nombre')}» en «{nom}»", campo=cm + ".arte"))
            nd["moldes"].append({"pid": pid, "molde_nombre": prod.get("nombre"), "variable": vcl,
                                 "variable_nombre": next((str(v.get("label") or vcl) for v in variantes if v["clave"] == vcl), None) if vcl else None,
                                 "tela": (tela_p or {}).get("nombre"), "tela_id": (tela_p or {}).get("id"),
                                 "telas_por_pieza": tpp, "piezas_fuera": fuera, "marcas": marcas,
                                 **({"medida": medida} if medida else {}),
                                 "sin_marca": sin_marca, "editables_declarados": declarados, "arte": arte,
                                 "tipografias": fuentes_d + [x for x in (_archivo(f, f"{cm}.tipografias[{k}]", EXT_FUENTE, "tipografia-formato")
                                                                         for k, f in enumerate(m.get("tipografias") or [])) if x]})
        norm_d.append(nd)

    if len(tpl_ids) > 1:
        A.append(alarma("planillas-distintas", campo="disenos"))
    if _frenan(A):
        return A, None

    # ── la planilla, contra las columnas y los talles de los moldes ──
    pid0 = norm_d[0]["moldes"][0]["pid"]
    prod0 = prods[pid0]
    tpl = _plantilla_de(prod0, cat) or {}
    # una Cantidad «no va» (2026-10-06) es como si la planilla no la tuviera: mandarla da
    # `columna-desconocida`, igual que cualquier columna que no existe
    cols = [c for c in (tpl.get("columnas") or []) if not (c.get("role") == "cantidad" and c.get("mostrar") == "no")]
    por_id = {str(c.get("id")): c for c in cols}
    por_titulo = {_norm(c.get("label")): c for c in cols}
    # «Nombre» ↔ «Texto» (2026-10-06): la columna del campo que se estampa pasó a rotularse «Texto»;
    # una fila que la manda con el título viejo «Nombre» (o al revés) sigue entrando en esa columna
    _col_txt = next((c for c in cols if c.get("role") == "nombre"), None)
    if _col_txt is not None:
        for _t in ("nombre", "texto"):
            por_titulo.setdefault(_norm(_t), _col_txt)
    col_dis = next((c for c in cols if c.get("role") == "diseno"), None)
    col_cant = next((c for c in cols if c.get("role") == "cantidad"), None)
    dis_por_nombre = {_norm(d["nombre"]): d for d in norm_d}
    if len(norm_d) > 1 and col_dis is None:
        A.append(alarma("sin-columna-diseno", campo="planilla"))
    talles_de, col_talle_de = {}, {}
    for d in norm_d:
        for m in d["moldes"]:
            p = prods[m["pid"]]
            reg = S._cargar("registro_producto.json", m["pid"]) or {}
            talles_de[m["pid"]] = {str(t).strip().lower(): t for t in S._talles_de_registro(reg, m["pid"])}
            # (un molde A MEDIDA nunca lee talle: el suyo es la medida, MAPA 623)
            col_talle_de[m["pid"]] = None if isinstance(p.get("a_medida"), dict) else _columna_talle_que_lee(p, cols)
    try:
        toggles = S._toggles_de_template(cols, cat)
    except Exception:
        toggles = []
    filas_n = []
    for n, f in enumerate(filas, 1):
        cf = f"planilla[{n - 1}]"
        if not isinstance(f, dict):
            A.append(alarma("campo-tipo", f"la fila {n} tiene que ser un objeto", fila=n, campo=cf)); continue
        fila, dnom = {}, None
        for k, v in f.items():
            kk = str(k)
            if kk in ("diseno", "diseño") and kk not in por_id:
                dnom = str(v or "").strip(); continue
            c = por_id.get(kk) or por_titulo.get(_norm(kk))
            if c is None:
                A.append(alarma("columna-desconocida", f"fila {n}: «{kk}»", fila=n, campo=f"{cf}.{kk}")); continue
            if c.get("role") == "diseno":
                dnom = str(v or "").strip(); continue
            fila[str(c.get("id"))] = "" if v is None else str(v).strip()
        # el diseño de la fila
        if dnom:
            d = dis_por_nombre.get(_norm(dnom))
            if d is None:
                A.append(alarma("fila-diseno-desconocido", f"fila {n}: «{dnom}»", fila=n, campo=cf + ".diseno")); continue
        elif len(norm_d) == 1:
            d = norm_d[0]
        else:
            A.append(alarma("columna-obligatoria-vacia", f"fila {n}: falta el diseño (el pedido trae varios)", fila=n, campo=cf + ".diseno")); continue
        if col_dis is not None:
            fila[str(col_dis.get("id"))] = d["slug"]
        # la cantidad
        if col_cant is not None and fila.get(str(col_cant.get("id")), "") != "":
            cv = fila[str(col_cant.get("id"))]
            if not re.match(r"^\d+$", cv) or int(cv) < 1:
                A.append(alarma("cantidad-invalida", f"fila {n}: «{cv}»", fila=n, campo=f"{cf}.{col_cant.get('id')}")); continue
        # obligatorias (las columnas de talle son un grupo: cada molde mira la suya)
        for c in cols:
            if c.get("obligatoria") and c.get("role") not in ("talle", "diseno") and not fila.get(str(c.get("id")), ""):
                A.append(alarma("columna-obligatoria-vacia", f"fila {n}: falta «{c.get('label')}»", fila=n, campo=f"{cf}.{c.get('id')}"))
        # el talle, molde por molde del diseño de la fila
        algun = False
        for m in d["moldes"]:
            ct = col_talle_de[m["pid"]]
            if ct is None:
                # PLANILLA SIN TALLES (MAPA 622): la fila no lleva talle; el molde pone el suyo si
                # tiene uno solo. Con varios no hay de dónde sacarlo.
                if len(talles_de[m["pid"]]) <= 1:
                    algun = True
                else:
                    A.append(alarma("talle-sin-columna", f"fila {n}: «{m['molde_nombre']}» tiene "
                                    f"{len(talles_de[m['pid']])} talles y su planilla no tiene columna de talle",
                                    fila=n, campo=cf))
                continue
            tv = fila.get(ct, "")
            if not tv:
                continue
            if tv.lower() not in talles_de[m["pid"]]:
                A.append(alarma("talle-inexistente", f"fila {n}: «{m['molde_nombre']}» no tiene el talle «{tv}» (tiene: "
                                + ", ".join(talles_de[m["pid"]].values()) + ")", fila=n, campo=f"{cf}.{ct}"))
            else:
                fila[ct] = talles_de[m["pid"]][tv.lower()]
                algun = True
        if not algun and not any(a.get("codigo") in ("talle-inexistente", "talle-sin-columna") and (a.get("donde") or {}).get("fila") == n for a in A):
            A.append(alarma("columna-obligatoria-vacia", f"fila {n}: falta el talle", fila=n, campo=cf))
        # las opciones de las columnas con lista
        for c in cols:
            cid = str(c.get("id"))
            if c.get("role") in ("talle", "diseno", "cantidad") or not fila.get(cid, ""):
                continue
            ops = _opciones_de_columna(c, cat)
            if not ops:
                continue
            partes = [x.strip() for x in fila[cid].split("+")] if c.get("role") == "manga" else [fila[cid]]
            ok = []
            for p_ in partes:
                hit = next((o for o in ops if _norm(o) == _norm(p_)), None)
                if hit is None:
                    A.append(alarma("opcion-inexistente", f"fila {n}: «{c.get('label')}» = «{p_}» (opciones: " + ", ".join(ops) + ")",
                                    fila=n, campo=f"{cf}.{cid}"))
                else:
                    ok.append(hit)
            if len(ok) == len(partes):
                fila[cid] = " + ".join(ok)
        # la variable de la fila: la del primer molde de su diseño (cada molde resuelve la suya)
        v0 = next((m["variable"] for m in d["moldes"] if m.get("variable")), None)
        if v0:
            fila["__variante"] = v0
        fila["__nfila"] = n
        fila["__diseno"] = d["nombre"]
        filas_n.append(fila)
    # cómo se reparten las mesas
    mesas = pedido.get("mesas") if isinstance(pedido.get("mesas"), dict) else {}
    modo = str(mesas.get("modo") or "normal").strip().lower()
    talles_mesa = {}
    if modo not in ("normal", "una_por_fila", "por_talles"):
        A.append(alarma("mesas-invalido", f"modo «{modo}»", campo="mesas.modo"))
    elif modo == "por_talles":
        todos = {t for d_ in talles_de.values() for t in d_}
        for gi, grupo in enumerate(mesas.get("grupos") or [], 1):
            for t in (grupo if isinstance(grupo, list) else []):
                if str(t).strip().lower() not in todos:
                    A.append(alarma("mesas-invalido", f"el talle «{t}» no es de ningún molde del pedido", campo="mesas.grupos"))
                talles_mesa[str(t).strip().lower()] = gi
        if not talles_mesa:
            A.append(alarma("mesas-invalido", "`por_talles` necesita `grupos`", campo="mesas.grupos"))
    if modo == "una_por_fila" and col_cant is None:
        A.append(alarma("mesas-invalido", "«una_por_fila» necesita que la planilla tenga columna de cantidad", campo="mesas.modo"))
    for k, permitidos in (("si_falta_tipografia", ("rechazar", "predeterminada")), ("si_texto_no_entra", ("achicar", "rechazar")),
                          ("si_piezas_en_blanco", ("rechazar", "seguir"))):
        if opc.get(k) is not None and opc.get(k) not in permitidos:
            A.append(alarma("campo-tipo", f"`opciones.{k}` admite: " + ", ".join(permitidos), campo="opciones." + k))
    normal = {
        "referencia": ref, "disenos": norm_d, "filas": filas_n,
        "columnas": [{"id": c.get("id"), "label": c.get("label"), "role": c.get("role") or "none"} for c in cols],
        "mesas": {"modo": modo, "talles_mesa": talles_mesa},
        "opciones": {"si_falta_tipografia": opc.get("si_falta_tipografia") or "rechazar",
                     "si_texto_no_entra": opc.get("si_texto_no_entra") or "achicar",
                     "si_piezas_en_blanco": opc.get("si_piezas_en_blanco") or "rechazar",
                     "perfil_color": opc.get("perfil_color") or None,
                     "carpeta": _ruta_segura(opc.get("carpeta") or "") or None},
    }
    if _frenan(A):
        return A, None
    # ── las reglas de la pantalla (la traba antes de fabricar, telas de baja, talles cruzados) ──
    A.extend(_reglas_de_la_pantalla(cuerpo_de(normal)))
    return A, (None if _frenan(A) else normal)


def cuerpo_de(normal):
    """El pedido externo traducido al MISMO cuerpo que arma la pantalla al apretar «Generar»
    (`cuerpoDelPedido` de App.jsx): a partir de acá todo el sistema lo trata igual."""
    molds, mpd, vpd = [], {}, {}
    tela_p, asig, fuera, marcas, sin_marca, reempl = {}, {}, {}, {}, {}, {}
    for d in normal["disenos"]:
        sl = d["slug"]
        for m in d["moldes"]:
            pid = m["pid"]
            if pid not in molds:
                molds.append(pid)
            mpd.setdefault(sl, []).append(pid)
            if m.get("variable"):
                vpd.setdefault(sl, {})[pid] = m["variable"]
            if m.get("tela"):
                tela_p.setdefault(pid, {})[sl] = m["tela"]
            if m.get("telas_por_pieza"):
                asig.setdefault(pid, {})[sl] = dict(m["telas_por_pieza"])
            if m.get("piezas_fuera"):
                fuera.setdefault(pid, {})[sl] = list(m["piezas_fuera"])
            # las marcas valen para cualquier variable del molde en este pedido («*») y, por si la
            # fila trae su variable, también con esa clave
            for destino, origen in ((marcas, m.get("marcas_ident") or m.get("marcas") or {}),
                                    (sin_marca, m.get("sin_marca_ident") or m.get("sin_marca") or {})):
                if origen:
                    por_var = destino.setdefault(pid, {}).setdefault(sl, {})
                    por_var["*"] = dict(origen)
                    if m.get("variable"):
                        por_var[m["variable"]] = dict(origen)
            r = {}
            for campo, fuente in (d.get("tipografia_por_campo") or {}).items():
                r[S.MP.clave_fuente_campo(campo)] = str(fuente)   # con los alias: «texto» = el campo nombre
            r.update(m.get("reemplazos") or {})
            if r:
                reempl[f"{sl}|{pid}"] = r
    prendas, filas_ficha = [], []
    for f in normal["filas"]:
        prendas.append({k: v for k, v in f.items() if k != "__diseno"})
        ff = {k: v for k, v in f.items() if not k.startswith("__")}
        filas_ficha.append(ff)
    modo = normal["mesas"]["modo"]
    cuerpo = {
        "molds": molds, "moldes_por_diseno": mpd, "vars_por_diseno": vpd, "prendas": prendas,
        "default_diseno": normal["disenos"][0]["slug"],
        "tela_principal": tela_p, "asignaciones": asig, "piezas_fuera": fuera,
        "marcas_pedido": marcas, "sin_marca_pedido": sin_marca,
        "cantidad_copia": modo == "una_por_fila",
        "planilla": {"columnas": normal["columnas"], "filas": filas_ficha},
        "fuentes_reemplazo_por": reempl,
    }
    if modo == "por_talles" and normal["mesas"].get("talles_mesa"):
        cuerpo["talles_mesa"] = normal["mesas"]["talles_mesa"]
    if normal["opciones"].get("perfil_color"):
        cuerpo["perfil_forzado"] = normal["opciones"]["perfil_color"]
    # en la ficha el diseño va con su nombre, no con el código interno
    nombres = {d["slug"]: d["nombre"] for d in normal["disenos"]}
    for ff in filas_ficha:
        for k, v in list(ff.items()):
            if v in nombres:
                ff[k] = nombres[v]
    return cuerpo


def _reglas_de_la_pantalla(cuerpo):
    """Corre `servidor._plan_del_pedido` sólo por sus TRABAS (toggle que el molde no tiene, pieza
    sin tela, talles cruzados, tela de baja…). Todavía no hay arte cargado, así que el final
    esperado es «ninguna fila tiene un diseño con arte»: eso acá significa que los datos pasaron."""
    try:
        S._plan_del_pedido(cuerpo)
        return []
    except S._PlanInvalido as e:
        r = e.resp[0] if isinstance(e.resp, tuple) else e.resp
        try:
            d = r.get_json() or {}
        except Exception:
            d = {}
        err = str(d.get("error") or "")
        det = d.get("detalle")
        if "arte aprobado" in err:
            return []
        txt = err + (" — " + ("; ".join(det) if isinstance(det, list) else str(det)) if det else "")
        if "no tiene piezas" in txt or "piden algo que este molde no tiene" in txt:
            return [alarma("opcion-sin-piezas", txt)]
        if "sin tela" in txt:
            return [alarma("pieza-sin-tela", txt)]
        if "no se puede usar" in txt and "tela" in txt.lower():
            return [alarma("tela-no-usable", txt)]
        if "talle" in txt.lower() and "columna" in txt.lower():
            return [alarma("talle-inexistente", txt)]
        if "TODAS sus piezas" in txt:
            return [alarma("todas-las-piezas-apagadas", txt)]
        if "ninguna fila está completa" in txt:
            return [alarma("columna-obligatoria-vacia", txt)]
        return [alarma("pedido-rechazado-por-reglas", txt)]
    except Exception as e:                       # una regla que revienta no puede aceptar el pedido
        return [alarma("pedido-rechazado-por-reglas", f"no se pudo revisar el pedido: {e}")]


# ══ EL PAQUETE Y EL ESTADO DE CADA PEDIDO ══════════════════════════════════════════════════════
def leer_estado(ref):
    return _leer_json(os.path.join(_dir_pedido(ref), "estado.json"), None)


def _guardar_estado(ref, est):
    est["actualizado"] = _ahora()
    _escribir_json(os.path.join(_dir_pedido(ref), "estado.json"), est)


def _abrir_paquete(datos):
    """(pedido, nombres, zip) o levanta ValueError(codigo_de_alarma, mensaje)."""
    if len(datos) > MAX_ZIP_MB * 1024 * 1024:
        raise ValueError("paquete-muy-grande")
    try:
        z = zipfile.ZipFile(io.BytesIO(datos))
        infos = [i for i in z.infolist() if not i.is_dir()]
    except Exception:
        raise ValueError("paquete-ilegible")
    if len(infos) > MAX_ARCHIVOS or sum(i.file_size for i in infos) > MAX_ZIP_MB * 1024 * 1024 * 3:
        raise ValueError("paquete-muy-grande")
    nombres = [i.filename.replace("\\", "/") for i in infos]
    if "pedido.json" not in nombres:
        raise ValueError("paquete-sin-pedido")
    try:
        pedido = json.loads(z.read("pedido.json").decode("utf-8-sig"))
    except Exception:
        raise ValueError("pedido-json-invalido")
    return pedido, [n for n in nombres if n != "pedido.json"], z


def _paquete_de_request():
    """El .zip puede venir como archivo de formulario (`paquete`) o como cuerpo crudo. Un cuerpo
    JSON pelado también vale (para `/validar`, sin archivos)."""
    f = request.files.get("paquete")
    if f is not None:
        return f.read(), None
    ct = (request.content_type or "").lower()
    if "json" in ct:
        try:
            return None, request.get_json(force=True)
        except Exception:
            return None, ValueError("pedido-json-invalido")
    return request.get_data(), None


def _respuesta_alarmas(ref, alarmas, aceptado, codigo_http):
    return jsonify({"referencia": ref, "aceptado": aceptado,
                    "estado": "en_cola" if aceptado else "rechazado",
                    "alarmas": alarmas}), codigo_http


# ══ /api/externo/v1 — lo que llama el otro sistema ═════════════════════════════════════════════
@bp.get("/api/externo/v1/formato")
def v1_formato():
    base = os.path.join(S.AQUI, "documentacion", "integracion_externa")
    return jsonify({"formato": FORMATO, "formato_resultado": FORMATO_RESULTADO,
                    "ejemplo": _leer_json(os.path.join(base, "pedido_ejemplo.json"), {}),
                    "ejemplo_resultado": _leer_json(os.path.join(base, "resultado_ejemplo.json"), {}),
                    "procesos_de_editable": list(PROCESOS),
                    "limites": {"paquete_mb": MAX_ZIP_MB, "archivos": MAX_ARCHIVOS}})


@bp.get("/api/externo/v1/alarmas")
def v1_alarmas():
    return jsonify({"alarmas": [{"codigo": k, "etapa": v[0], "frena": v[1], "que_significa": v[2], "que_hacer": v[3]}
                                for k, v in ALARMAS.items()],
                    "etapas": {"datos": "al recibir el paquete, sin abrir archivos: se contesta en el acto",
                               "arte": "al leer el arte y las tipografías (segundos después)",
                               "tizada": "al armar la tizada y guardar los PDF",
                               "plantilla": "al armar la plantilla (la base para el diseñador): la arma el robot"}})


@bp.get("/api/externo/v1/moldes")
def v1_moldes():
    cat = S._cargar_catalogo()
    return jsonify({"version": _version_catalogo(),
                    "moldes": [molde_publico(p, cat, detalle=False) for p in cat.get("productos", [])
                               if not p.get("efimero") and not S._es_privado(p)]})


def _molde_de_variable(q, prods):
    """(pid, []) de la prenda que tiene esa variable; (None, [nombres]) si el NOMBRE está en varias."""
    por_clave, por_nombre = [], []
    for p in prods.values():
        if p.get("efimero") or S._es_privado(p):
            continue
        for v in p.get("variantes") or []:
            if v.get("clave") == q:
                por_clave.append(p)
            elif _norm(v.get("label")) == _norm(q):
                por_nombre.append(p)
    if por_clave:
        return por_clave[0]["id"], []
    if len(por_nombre) == 1:
        return por_nombre[0]["id"], []
    if len(por_nombre) > 1:
        return None, [str(p.get("nombre") or p["id"]) for p in por_nombre]
    return None, []


def variables_publicas(cat):
    """TODAS las variables que se pueden pedir: de cada molde LISTO, las que tienen piezas. Es lo que
    el operario elige en el pedido de TIZADA (el molde queda detrás, como dato)."""
    out = []
    for prod in cat.get("productos", []):
        if prod.get("efimero") or S._es_privado(prod):
            continue
        try:
            reg = S._cargar("registro_producto.json", prod["id"]) or {}
        except Exception:
            reg = {}
        if not _molde_listo(prod, reg)[0]:
            continue
        for v in prod.get("variantes") or []:
            cl = v.get("clave")
            pz = (S._piezas_de_variable(prod, cl, reg) or []) if cl else []
            if not pz:
                continue
            out.append({"clave": cl, "nombre": v.get("label") or cl, "molde": prod["id"], "molde_nombre": prod.get("nombre") or prod["id"],
                        "piezas": sorted({_gen(x) for x in pz}), "n_piezas": len(pz), "planilla": prod.get("planilla_template_id"),
                        "foto": f"/api/externo/v1/variables/{cl}/foto",
                        # MOLDE A MEDIDA (MAPA 623): el pedido tiene que traer la medida
                        **({"a_medida": _a_medida_publico_ext(prod)} if _a_medida_publico_ext(prod) else {})})
    return out


@bp.get("/api/externo/v1/variables")
def v1_variables():
    cat = S._cargar_catalogo()
    return jsonify({"version": _version_catalogo(), "variables": variables_publicas(cat),
                    "nota": "en TIZADA PRO se elige la VARIABLE; el molde va de la mano (campo `molde`). "
                            "Dos variables de distinta `planilla` no se combinan en un pedido."})


@bp.get("/api/externo/v1/variables/<clave>/foto")
def v1_variable_foto(clave):
    """La silueta de las piezas de UNA variable: la del molde filtrada por sus `pieza_idx` (igual que
    `VariantePreviewSVG` en el pedido de TIZADA). Vectorial: contornos, nada de imagen."""
    cat = S._cargar_catalogo()
    prods = {p["id"]: p for p in cat.get("productos", [])}
    pid, _amb = _molde_de_variable(clave, prods)
    prod = prods.get(pid) if pid else None
    v = next((x for x in ((prod or {}).get("variantes") or []) if x.get("clave") == clave), None)
    if not prod or not v or "producto_preview" not in S.app.view_functions:
        return jsonify({"error": "esa variable no existe"}), 404
    foto, resp = _silueta(pid)
    if foto is None:
        return resp
    idx = {int(x["pieza_idx"]) for x in (v.get("valores") or []) if x.get("pieza_idx") is not None}
    return jsonify({**foto, "piezas": [p for p in (foto.get("piezas") or []) if p.get("idx") in idx],
                    "variable": clave, "molde": pid})


@bp.get("/api/externo/v1/moldes/<pid>")
def v1_molde(pid):
    cat = S._cargar_catalogo()
    prod = next((p for p in cat.get("productos", []) if p.get("id") == pid), None)
    if prod is None or prod.get("efimero") or S._es_privado(prod):
        return jsonify({"error": "ese molde no existe"}), 404
    return jsonify({"version": _version_catalogo(), "molde": molde_publico(prod, cat)})


@bp.get("/api/externo/v1/moldes/<pid>/foto")
def v1_molde_foto(pid):
    cat = S._cargar_catalogo()
    prod = next((p for p in cat.get("productos", []) if p.get("id") == pid), None)
    if prod is None or prod.get("efimero") or S._es_privado(prod):
        return jsonify({"error": "ese molde no existe"}), 404
    if "producto_preview" not in S.app.view_functions:
        return jsonify({"error": "sin foto"}), 404
    return _silueta(pid)[1]


_SIN_SILUETA = ("la silueta de esta prenda todavía no está calculada: se arma la primera vez que alguien "
                "la abre en TIZADA PRO (el otro sistema no puede calcularla)")


def _silueta(pid):
    """(dict|None, respuesta) con la silueta del molde. Si TIZADA todavía no la calculó, el servidor
    le pediría el cálculo a quien llama (428 `{calcular}`), y el otro sistema NO es un navegador de
    TIZADA: no puede hacerlo. Se contesta 404 con el motivo, y la pantalla de afuera pone un ícono."""
    try:
        r = S.app.view_functions["producto_preview"](pid)
    except Exception as e:
        if type(e).__name__ == "_FaltaCalculo":
            return None, (jsonify({"error": _SIN_SILUETA, "sin_calcular": True}), 404)
        raise
    resp = r[0] if isinstance(r, tuple) else r
    return (resp.get_json(silent=True) if hasattr(resp, "get_json") else None), r


@bp.get("/api/externo/v1/telas")
def v1_telas():
    cat = S._cargar_catalogo()
    return jsonify({"telas": [{"id": str(t.get("id")), "nombre": t.get("nombre"), "ancho_mesa_cm": t.get("ancho_cm"),
                               "usable": bool(t.get("usable")), "de_baja": not t.get("activa", True)}
                              for t in (cat.get("telas") or [])]})


@bp.get("/api/externo/v1/tipografias")
def v1_tipografias():
    try:
        fu = {"carpetas": [S.FUENTES], "alias": {}}
        lst = sorted({str(i.get("interno") or i.get("completo") or "") for i in S.MP.catalogo_fuentes(fu).values()} - {""})
    except Exception:
        lst = []
    return jsonify({"tipografias": lst,
                    "nota": "si el arte usa una que no está acá, mandar el archivo en `tipografias`"})


@bp.post("/api/externo/v1/pedidos/validar")
def v1_validar():
    """Revisa el pedido SIN guardarlo ni ponerlo en cola. Acepta el .zip o sólo el JSON (en ese
    caso no se controla que los archivos nombrados existan)."""
    datos, pedido = _paquete_de_request()
    nombres = None
    if isinstance(pedido, ValueError):
        return _respuesta_alarmas(None, [alarma(str(pedido))], False, 422)
    if pedido is None:
        try:
            pedido, nombres, _z = _abrir_paquete(datos)
        except ValueError as e:
            return _respuesta_alarmas(None, [alarma(str(e))], False, 422)
    al, normal = revisar_datos(pedido, nombres if nombres is not None else _nombres_del_json(pedido))
    ref = pedido.get("referencia") if isinstance(pedido, dict) else None
    return jsonify({"referencia": ref, "aceptaria": normal is not None, "alarmas": al,
                    "nota": "sólo se revisaron los DATOS; el arte y las tipografías se revisan al procesar"}), (200 if normal is not None else 422)


def _nombres_del_json(pedido):
    """Para validar sólo el JSON: se da por bueno que los archivos que nombra van a venir."""
    out = []
    for d in (pedido.get("disenos") or []) if isinstance(pedido, dict) else []:
        if isinstance(d, dict):
            out += [d.get("arte")] + list(d.get("tipografias") or [])
            for m in (d.get("moldes") or []):
                if isinstance(m, dict):
                    out += [m.get("arte")] + list(m.get("tipografias") or [])
    return [str(x) for x in out if x]


@bp.post("/api/externo/v1/pedidos")
def v1_recibir():
    datos, pedido = _paquete_de_request()
    if pedido is not None or not datos:
        return jsonify({"error": "el pedido se manda como paquete .zip (pedido.json + artes + tipografías); "
                                 "para revisar sólo el JSON está /pedidos/validar"}), 415
    try:
        pedido, nombres, z = _abrir_paquete(datos)
    except ValueError as e:
        _anotar_rechazo(None, [alarma(str(e))])
        return _respuesta_alarmas(None, [alarma(str(e))], False, 422)
    with _LOCK:
        al, normal = revisar_datos(pedido, nombres)
        ref = normal["referencia"] if normal else (pedido.get("referencia") if isinstance(pedido, dict) else None)
        if normal is None:
            _anotar_rechazo(ref, al)
            return _respuesta_alarmas(ref, al, False, 422)
        # el paquete se guarda entero: el .zip tal cual llegó + sus archivos sueltos para el robot
        carpeta = _dir_pedido(ref)
        previo = leer_estado(ref)
        if previo:
            _limpiar_disenos(previo)                 # los diseños internos de la tanda anterior
            shutil.rmtree(os.path.join(carpeta, "archivos"), ignore_errors=True)
        os.makedirs(os.path.join(carpeta, "archivos"), exist_ok=True)
        with open(os.path.join(carpeta, "paquete.zip.tmp"), "wb") as fh:
            fh.write(datos)
        os.replace(os.path.join(carpeta, "paquete.zip.tmp"), os.path.join(carpeta, "paquete.zip"))
        for n in nombres:
            r = _ruta_segura(n)
            if r is None:
                continue
            dst = os.path.join(carpeta, "archivos", *r.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst + ".tmp", "wb") as fh:
                fh.write(z.read(n))
            os.replace(dst + ".tmp", dst)
        _escribir_json(os.path.join(carpeta, "pedido.json"), pedido)
        _escribir_json(os.path.join(carpeta, "normal.json"), normal)
        try:
            os.remove(os.path.join(carpeta, "resultado.json"))
        except OSError:
            pass
        ll = getattr(g, "_llave", None) or {}
        _guardar_estado(ref, {"referencia": ref, "estado": "en_cola", "etapa": "esperando al robot",
                              "recibido": _ahora(), "intentos": 0, "alarmas": al,
                              "llave": ll.get("id"), "integracion": ll.get("nombre"),
                              "cliente": pedido.get("cliente"), "aviso_url": _aviso_url(pedido, al),
                              "pedido_externo": pedido.get("pedido_externo")})
    return _respuesta_alarmas(ref, al, True, 202)


def _anotar_rechazo(ref, al):
    """Lo rechazado también queda a la vista en la pantalla (sin guardar el paquete)."""
    try:
        lst = _leer_json(os.path.join(_raiz(), "rechazos.json"), []) or []
        lst.insert(0, {"cuando": _ahora(), "referencia": ref, "alarmas": al[:12],
                       "integracion": (getattr(g, "_llave", None) or {}).get("nombre")})
        _escribir_json(os.path.join(_raiz(), "rechazos.json"), lst[:60])
    except Exception:
        pass


def _aviso_url(pedido, alarmas):
    """A dónde se avisa cuando termina. La del pedido sólo vale si es del MISMO sitio que la
    configurada: una llave robada no puede hacer que el servidor llame a cualquier dirección."""
    base = (_cfg().get("aviso_url") or "").strip()
    del_pedido = str((pedido or {}).get("aviso_url") or "").strip()
    if not del_pedido:
        return base
    try:
        a, b = urllib.parse.urlparse(del_pedido), urllib.parse.urlparse(base)
        if base and a.scheme in ("http", "https") and a.netloc and a.netloc == b.netloc:
            return del_pedido
    except Exception:
        pass
    alarmas.append(alarma("aviso-url-no-permitida", campo="aviso_url"))
    return base


def resultado_publico(res, ref):
    """Lo que ve el otro sistema del resultado: SIN las rutas del disco del servidor (`ruta`,
    `destino.carpeta`, `destino.copia_local` — no le sirven y muestran cómo está armado el servidor)
    y CON la dirección para bajar cada archivo de TIZADA (`descarga`), haya Drive o no."""
    if not res:
        return res
    r = dict(res)
    r["destino"] = {k: v for k, v in (res.get("destino") or {}).items() if k not in ("carpeta", "copia_local")}
    r["archivos"] = [{**{k: v for k, v in a.items() if k != "ruta"},
                      "descarga": f"/api/externo/v1/pedidos/{ref}/archivos/{urllib.parse.quote(str(a.get('nombre') or ''))}"}
                     for a in (res.get("archivos") or [])]
    return r


def estado_publico(ref):
    est = leer_estado(ref)
    if not est:
        return None
    out = {k: est.get(k) for k in ("referencia", "estado", "etapa", "recibido", "actualizado", "alarmas", "pedido_externo")}
    res = _leer_json(os.path.join(_dir_pedido(ref), "resultado.json"), None)
    if res:
        out["resultado"] = resultado_publico(res, ref)
    return out


@bp.get("/api/externo/v1/pedidos/<ref>")
def v1_estado(ref):
    if not _RX_REF.match(ref):
        return jsonify({"error": "referencia inválida"}), 400
    e = estado_publico(ref)
    return (jsonify(e), 200) if e else (jsonify({"error": "no hay ningún pedido con esa referencia"}), 404)


@bp.get("/api/externo/v1/pedidos/<ref>/archivos/<nombre>")
def v1_archivo(ref, nombre):
    """Un PDF del resultado, bajado de TIZADA PRO (la copia que siempre queda en el servidor). Sirve
    aunque Drive no esté conectado. Sólo los archivos que el resultado nombra, y sólo de la carpeta
    de salida de ESE pedido."""
    if not _RX_REF.match(ref):
        return jsonify({"error": "referencia inválida"}), 400
    res = _leer_json(os.path.join(_dir_pedido(ref), "resultado.json"), None) or {}
    a = next((x for x in res.get("archivos") or [] if x.get("nombre") == nombre), None)
    base = os.path.realpath(os.path.join(_raiz(), "salida", ref))
    ruta = os.path.realpath(os.path.join(base, nombre)) if a else ""
    if not a or not ruta.startswith(base + os.sep) or not os.path.isfile(ruta):
        return jsonify({"error": "ese archivo no es de este pedido o ya no está en el servidor"}), 404
    return send_file(ruta, mimetype="application/pdf" if nombre.lower().endswith(".pdf") else None,
                     as_attachment=request.args.get("descargar") == "1", download_name=nombre)


@bp.delete("/api/externo/v1/pedidos/<ref>")
def v1_cancelar(ref):
    if not _RX_REF.match(ref):
        return jsonify({"error": "referencia inválida"}), 400
    with _LOCK:
        est = leer_estado(ref)
        if not est:
            return jsonify({"error": "no hay ningún pedido con esa referencia"}), 404
        if est.get("estado") == "listo":
            return jsonify({"error": "ese pedido ya se generó"}), 409
        est["estado"], est["etapa"] = "cancelado", "cancelado por el otro sistema"
        _guardar_estado(ref, est)
        _limpiar_disenos(est)
    return jsonify({"referencia": ref, "estado": "cancelado"})


# ══ LOS DISEÑOS INTERNOS (uno por diseño y molde del pedido, marcados `externo`) ═══════════════
def _asegurar_disenos(ref, normal):
    """Da de alta en cada molde el diseño interno del pedido. Sólo AGREGA entradas marcadas
    `externo`; nunca toca un diseño cargado a mano."""
    cat = S._cargar_catalogo_para_editar()
    cambio = False
    for d in normal["disenos"]:
        for m in d["moldes"]:
            prod = next((p for p in cat["productos"] if p["id"] == m["pid"]), None)
            if prod is None:
                continue
            lst = prod.setdefault("disenos", [])
            if not any(x.get("id") == d["slug"] for x in lst):
                lst.append({"id": d["slug"], "nombre": d["nombre"], "externo": ref})
                cambio = True
    if cambio:
        S._guardar_catalogo(cat)


def _borrar_copias_a_medida(ref):
    """MOLDE A MEDIDA (MAPA 623): las copias a medida que hizo el robot para `ref` (un pedido o una
    plantilla) se borran apenas no hacen falta — los PDF ya quedaron guardados. Sólo las efímeras,
    marcadas con ESTA referencia y que salieron de una plantilla: nunca un molde del catálogo."""
    _es_copia = lambda p: (p.get("efimero") is True and p.get("externo") == ref
                           and isinstance(p.get("a_medida"), dict) and p["a_medida"].get("de"))
    copias = []
    try:
        cat = S._cargar_catalogo_para_editar()
        copias = [p["id"] for p in cat.get("productos", []) if _es_copia(p)]
        if copias:
            cat["productos"] = [p for p in cat["productos"] if not _es_copia(p)]
            S._guardar_catalogo(cat)
    finally:
        S._soltar_edicion_catalogo()
    for _pid in copias:
        try:
            S._borrar_archivos_y_base(_pid, efimero=True)
        except Exception as e:
            print(f"[externo] no se pudo borrar la copia a medida {_pid}: {e}", flush=True)


def _limpiar_disenos(est):
    """Saca del catálogo y del disco los diseños internos de ESTE pedido — sólo los que llevan su
    marca `externo` con esta misma referencia (nunca por nombre, nunca «los que sobran»)."""
    ref = est.get("referencia")
    normal = _leer_json(os.path.join(_dir_pedido(ref), "normal.json"), None) or {}
    try:
        cat = S._cargar_catalogo_para_editar()
        cambio = False
        for d in normal.get("disenos", []):
            for m in d.get("moldes", []):
                prod = next((p for p in cat["productos"] if p["id"] == m["pid"]), None)
                if prod is None:
                    continue
                antes = prod.get("disenos") or []
                queda = [x for x in antes if not (x.get("id") == d["slug"] and x.get("externo") == ref)]
                if len(queda) != len(antes):
                    prod["disenos"] = queda
                    for tabla in ("editables",):
                        if isinstance(prod.get(tabla), dict):
                            prod[tabla].pop(d["slug"], None)
                    cambio = True
                    for base in (os.path.join(S.DATOS, "productos", m["pid"], "disenos", d["slug"]),
                                 os.path.join(S.ENTRADA, m["pid"], "disenos", d["slug"])):
                        shutil.rmtree(base, ignore_errors=True)
        if cambio:
            S._guardar_catalogo(cat)
        _borrar_copias_a_medida(ref)
    except Exception as e:
        print(f"[externo] no se pudieron limpiar los diseños de {ref}: {e}", flush=True)


# ══ /api/externo/robot — la conversación con el robot ══════════════════════════════════════════
def _pedidos():
    base = os.path.join(_raiz(), "pedidos")
    try:
        refs = [r for r in os.listdir(base) if os.path.isdir(os.path.join(base, r))]
    except OSError:
        refs = []
    out = []
    for r in refs:
        e = leer_estado(r)
        if e:
            out.append(e)
    return out


@bp.post("/api/externo/robot/tomar")
def robot_tomar():
    """El robot pide trabajo: el pedido más viejo en cola (o una prueba de Drive pendiente)."""
    with _LOCK:
        c = _cfg()
        _latido("esperando")
        try:
            purgar()
        except Exception as e:
            print(f"[externo] la limpieza de pedidos viejos falló: {e}", flush=True)
        if not c["robot"].get("activo", True):
            return jsonify({"tarea": None, "pausa": True})
        if c.get("probar_drive"):
            c.pop("probar_drive", None)
            _cfg_guardar(c)
            return jsonify({"tarea": "probar_drive"})
        # las PLANTILLAS primero (MAPA 619): se arman en segundos y un pedido puede llevar minutos
        tp = _tomar_plantilla()
        if tp:
            _latido("trabajando", tp["referencia"])
            return jsonify(tp)
        ahora = time.time()
        cola = []
        for e in _pedidos():
            if e.get("estado") == "en_cola":
                cola.append(e)
            elif e.get("estado") == "procesando":
                # el robot se cayó a mitad de camino: vuelve a la cola (hasta 3 intentos)
                try:
                    visto = time.mktime(time.strptime(e.get("actualizado"), "%Y-%m-%dT%H:%M:%S"))
                except Exception:
                    visto = 0
                if ahora - visto > ESPERA_ROBOT_S:
                    cola.append(e)
        if not cola:
            return jsonify({"tarea": None})
        cola.sort(key=lambda e: e.get("recibido") or "")
        est = cola[0]
        ref = est["referencia"]
        if int(est.get("intentos") or 0) >= 3:
            est["estado"], est["etapa"] = "error", "se intentó 3 veces y no se pudo terminar"
            _guardar_estado(ref, est)
            _avisar(ref)
            return jsonify({"tarea": None})
        normal = _leer_json(os.path.join(_dir_pedido(ref), "normal.json"), None)
        if not normal:
            est["estado"], est["etapa"] = "error", "el paquete guardado no se puede leer"
            _guardar_estado(ref, est)
            return jsonify({"tarea": None})
        _asegurar_disenos(ref, normal)
        est["estado"], est["etapa"] = "procesando", "leyendo el arte"
        est["intentos"] = int(est.get("intentos") or 0) + 1
        est["alarmas"] = [a for a in est.get("alarmas", []) if a.get("etapa") == "datos"]
        _guardar_estado(ref, est)
        _latido("trabajando", ref)
        return jsonify({"tarea": "pedido", "referencia": ref, "normal": normal})


def _latido(que, ref=None):
    try:
        _escribir_json(os.path.join(_raiz(), "robot_latido.json"), {"cuando": time.time(), "que": que, "referencia": ref})
    except Exception:
        pass


@bp.get("/api/externo/robot/archivo/<ref>")
def robot_archivo(ref):
    r = _ruta_segura(request.args.get("ruta") or "")
    if not _RX_REF.match(ref) or r is None:
        return jsonify({"error": "ruta inválida"}), 400
    ruta = os.path.join(_dir_pedido(ref), "archivos", *r.split("/"))
    if not os.path.isfile(ruta):
        return jsonify({"error": "no existe"}), 404
    return send_file(ruta, as_attachment=False)


@bp.post("/api/externo/robot/avance/<ref>")
def robot_avance(ref):
    d = request.get_json(force=True) or {}
    with _LOCK:
        est = leer_estado(ref)
        if not est:
            return jsonify({"error": "no existe"}), 404
        if est.get("estado") == "cancelado":
            return jsonify({"seguir": False})
        if d.get("etapa"):
            est["etapa"] = str(d["etapa"])[:200]
        _guardar_estado(ref, est)
        _latido("trabajando", ref)
    return jsonify({"seguir": True})


def _nombre_editable(capa):
    try:
        return S.MP._nombre_editable(capa)
    except Exception:
        return str(capa)


@bp.post("/api/externo/robot/arte/<ref>")
def robot_arte(ref):
    """El robot cuenta lo que leyó de UN arte (un diseño en un molde) y acá se decide con las
    reglas: qué frena, qué es aviso, y cómo se llaman de verdad los objetos editables."""
    d = request.get_json(force=True) or {}
    with _LOCK:
        est = leer_estado(ref)
        normal = _leer_json(os.path.join(_dir_pedido(ref), "normal.json"), None)
        if not est or not normal:
            return jsonify({"error": "no existe"}), 404
        dis = next((x for x in normal["disenos"] if x["slug"] == d.get("slug")), None)
        mol = next((m for m in (dis or {}).get("moldes", []) if m["pid"] == d.get("pid")), None)
        if not mol:
            return jsonify({"error": "ese diseño o molde no es de este pedido"}), 400
        A = []
        quien = f"«{dis['nombre']}» en «{mol['molde_nombre']}»"
        donde = {"diseno": dis["nombre"], "molde": mol["pid"]}
        if d.get("error"):
            A.append(alarma("arte-ilegible", f"{quien}: {d['error']}", **donde))
        if d.get("modo") and d.get("modo") != "separado":
            A.append(alarma("arte-sin-mesas-de-pieza", quien, **donde))
        # los «checks» de la revisión del arte (los mismos textos que ve la pantalla)
        for ch in ((d.get("validacion") or {}).get("checks") or []):
            if ch.get("ok"):
                continue
            nom, det = str(ch.get("nombre") or ""), str(ch.get("detalle") or "")
            txt = f"{quien}: {nom} — {det}"
            if "pieza tiene un arte" in nom or "Mapeo de arte" in nom:
                cod = "arte-pieza-sin-mesa"
            elif "variantes tienen" in nom:
                cod = "arte-variante-sin-cubrir"
            elif "mesas asignadas" in nom or "Mesas de arte" in nom:
                cod = "arte-mesa-vacia"
            elif "texto vivo" in nom:
                cod = "arte-texto-vivo"
            elif "Tipograf" in nom:
                continue                                   # se decide abajo, con lo que vino en el paquete
            else:
                cod = "arte-observado"
            A.append(alarma(cod, txt, **donde))
        # tipografías del nombre/número que no resuelven
        for f in (d.get("fuentes_faltan") or []):
            if normal["opciones"].get("si_falta_tipografia") == "predeterminada":
                A.append(alarma("tipografia-reemplazada", f"{quien}: faltaba «{f}»", **donde))
            else:
                A.append(alarma("tipografia-falta", f"{quien}: «{f}»", **donde))
        for f in (d.get("fuentes_invalidas") or []):
            A.append(alarma("tipografia-invalida", f"{quien}: «{f}»", **donde))
        # los objetos editables: el pedido los nombra como la capa sin «Editable»
        capas = [str(c) for c in (d.get("editables") or [])]
        por_nombre = {}
        for c in capas:
            por_nombre.setdefault(_norm(_nombre_editable(c)), _nombre_editable(c))
            por_nombre.setdefault(_norm(c), _nombre_editable(c))
        marcas, sin_marca = {}, {}
        for obj in mol.get("editables_declarados") or []:
            real = por_nombre.get(_norm(obj)) or por_nombre.get(_norm(_nombre_editable(obj)))
            if real is None:
                A.append(alarma("editable-desconocido", f"{quien}: «{obj}» (el arte tiene: "
                                + (", ".join(sorted(set(por_nombre.values()))) or "ninguno") + ")", **donde))
                continue
            if obj in (mol.get("marcas") or {}):
                marcas[real] = mol["marcas"][obj]
            if obj in (mol.get("sin_marca") or {}):
                sin_marca[real] = True
        dichos = {_norm(o) for o in (mol.get("editables_declarados") or [])} | {_norm(_nombre_editable(o)) for o in (mol.get("editables_declarados") or [])}
        for real in sorted(set(por_nombre.values())):
            if _norm(real) not in dichos:
                A.append(alarma("editable-sin-declarar", f"{quien}: «{real}»", **donde))
        # nombre / número cargados en la planilla sin capa en el arte
        campos = {_norm(c) for c in (d.get("campos") or [])}
        if d.get("campos") is not None:
            prod = next((p for p in S._cargar_catalogo().get("productos", []) if p["id"] == mol["pid"]), {}) or {}
            mc = prod.get("mapeo_columnas") or {}
            for campo, col in (("nombre", mc.get("nombre") or "nombre"), ("numero", mc.get("numero") or "numero")):
                usa = any(str(f.get(col) or "").strip() for f in normal["filas"] if f.get("__diseno") == dis["nombre"])
                if usa and campo not in campos:
                    A.append(alarma("arte-campo-sin-capa", f"{quien}: la planilla trae «{'texto' if campo == 'nombre' else campo}» y el arte no tiene esa capa", **donde))
        mol["marcas_ident"], mol["sin_marca_ident"] = marcas, sin_marca
        _escribir_json(os.path.join(_dir_pedido(ref), "normal.json"), normal)
        est["alarmas"] = [a for a in est.get("alarmas", [])
                          if not (a.get("etapa") == "arte" and (a.get("donde") or {}).get("diseno") == dis["nombre"]
                                  and (a.get("donde") or {}).get("molde") == mol["pid"])] + A
        _guardar_estado(ref, est)
    return jsonify({"alarmas": A, "seguir": not _frenan(A)})


@bp.post("/api/externo/robot/a_medida/<ref>")
def robot_a_medida(ref):
    """MOLDE A MEDIDA (MAPA 623): el robot pide la COPIA a medida de un molde del catálogo (para un
    pedido o una plantilla). Con `slug`, la copia toma el lugar de la plantilla en ese diseño del
    pedido (así `cuerpo_de` y el arte la usan). El archivo lo sube el robot por `/api/plantilla`."""
    d = request.get_json(force=True) or {}
    tpl = str(d.get("plantilla") or "").strip()
    an, al = S._metros(d.get("ancho_m")), S._metros(d.get("alto_m"))
    if not tpl or an is None or al is None:
        return jsonify({"error": "falta la plantilla o la medida"}), 400
    pid, err = S._copia_a_medida(tpl, an, al, externo=ref)
    if err:
        return jsonify({"error": err}), 400
    slug = d.get("slug")
    if slug:
        with _LOCK:
            normal = _leer_json(os.path.join(_dir_pedido(ref), "normal.json"), None)
            dis = next((x for x in (normal or {}).get("disenos", []) if x.get("slug") == slug), None)
            mol = next((m for m in (dis or {}).get("moldes", []) if (m.get("plantilla") or m.get("pid")) == tpl), None)
            if not mol:
                return jsonify({"error": "ese molde no es de este pedido"}), 400
            mol["plantilla"] = tpl
            mol["pid"] = pid
            mol["variable"] = S._clave_var_a_medida(pid)
            _escribir_json(os.path.join(_dir_pedido(ref), "normal.json"), normal)
            _asegurar_disenos(ref, normal)
    cat = S._cargar_catalogo()
    prod = next((p for p in cat.get("productos", []) if p.get("id") == pid), {}) or {}
    am = prod.get("a_medida") or {}
    return jsonify({"pid": pid, "variable": am.get("variable"), "pieza": am.get("pieza"),
                    "talle": S._talle_de_medida(an, al), "ancho_m": an, "alto_m": al})


@bp.post("/api/externo/robot/a_medida/<ref>/listo")
def robot_a_medida_listo(ref):
    """Después de subir el archivo de la copia: su variable (creada por el alta) y el margen."""
    d = request.get_json(force=True) or {}
    pid = str(d.get("pid") or "")
    cat = S._cargar_catalogo()
    prod = next((p for p in cat.get("productos", []) if p.get("id") == pid), None)
    if not prod or (prod.get("externo") != ref) or not isinstance(prod.get("a_medida"), dict):
        return jsonify({"error": "esa copia no es de este pedido"}), 400
    var = next((v for v in (prod.get("variantes") or []) if v.get("clave") == prod["a_medida"].get("variable")), None)
    if not var:
        return jsonify({"error": "la copia a medida quedó sin variable (¿falló el alta?)"}), 409
    return jsonify({"variable": var, "acomodo": prod.get("acomodo_illustrator") or {}})


@bp.get("/api/externo/robot/cuerpo/<ref>")
def robot_cuerpo(ref):
    normal = _leer_json(os.path.join(_dir_pedido(ref), "normal.json"), None)
    if not normal:
        return jsonify({"error": "no existe"}), 404
    return jsonify({"cuerpo": cuerpo_de(normal), "opciones": normal["opciones"]})


@bp.get("/api/externo/robot/destino")
def robot_destino():
    """Dónde se guardan los PDF. La llave de la cuenta de servicio sólo sale por acá, hacia el
    robot (misma máquina), nunca hacia la pantalla ni hacia el otro sistema."""
    c = _cfg()
    drive = None
    cred = _credencial_drive()
    tiz, fic = _carpetas_drive(c)
    if c["drive"].get("activo") and tiz and cred:
        drive = {"carpeta_tizadas": tiz, "carpeta_fichas": fic or tiz, "carpeta_id": tiz, **cred}
    return jsonify({"drive": drive, "local": os.path.join(_raiz(), "salida")})


def _carpetas_drive(c):
    """(carpeta de las tizadas, carpeta de las fichas). `carpeta_id` es la de antes (una sola)."""
    d = c.get("drive") or {}
    tiz = d.get("carpeta_tizadas") or d.get("carpeta_id") or ""
    return tiz, (d.get("carpeta_fichas") or tiz)


def _credencial_drive():
    """Con qué se entra a Drive. 🔴 PRIMERO la cuenta de una PERSONA (OAuth, `drive_oauth_*.json`):
    los archivos quedan a su nombre y usan SU espacio. Una cuenta de servicio no tiene espacio propio
    y Google no la deja guardar en el «Mi unidad» de una cuenta personal (sólo en unidades
    compartidas) — es el caso de breusplanilla@gmail.com (2026-10-02)."""
    cli = _leer_json(os.path.join(_raiz(), "drive_oauth_cliente.json"), None)
    tok = _leer_json(os.path.join(_raiz(), "drive_oauth_token.json"), None)
    if cli and tok and tok.get("refresh_token"):
        return {"oauth": {"client_id": cli["client_id"], "client_secret": cli["client_secret"],
                          "token_uri": cli.get("token_uri") or "https://oauth2.googleapis.com/token",
                          "refresh_token": tok["refresh_token"]}}
    cuenta = _leer_json(os.path.join(_raiz(), "drive_cuenta.json"), None)
    if cuenta:
        return {"cuenta": cuenta}
    return None


@bp.post("/api/externo/robot/drive_probado")
def robot_drive_probado():
    d = request.get_json(force=True) or {}
    with _LOCK:
        c = _cfg()
        c["drive"]["prueba"] = {"cuando": _ahora(), "ok": bool(d.get("ok")), "detalle": str(d.get("detalle") or "")[:400]}
        _cfg_guardar(c)
    return jsonify({"ok": True})


def _clasificar_avisos(resultado, opciones):
    A = []
    for t in (resultado or {}).get("avisos") or []:
        a = alarma("piezas-en-blanco", str(t))
        a["frena"] = False            # si llegó hasta acá es porque el pedido pidió «seguir»
        A.append(a)
    for t in (resultado or {}).get("avisos_pedido") or []:
        A.append(alarma("aviso-del-pedido", str(t)))
    return A


@bp.post("/api/externo/robot/terminar/<ref>")
def robot_terminar(ref):
    """La tizada quedó hecha y guardada: se arma el JSON para el otro sistema."""
    d = request.get_json(force=True) or {}
    with _LOCK:
        est = leer_estado(ref)
        normal = _leer_json(os.path.join(_dir_pedido(ref), "normal.json"), None)
        pedido = _leer_json(os.path.join(_dir_pedido(ref), "pedido.json"), None) or {}
        if not est or not normal:
            return jsonify({"error": "no existe"}), 404
        if est.get("estado") == "cancelado":
            return jsonify({"ok": False, "cancelado": True})
        res = d.get("resultado") or {}
        A = [a for a in est.get("alarmas", []) if a.get("etapa") != "tizada"]
        A += _clasificar_avisos(res, normal["opciones"])
        for x in (d.get("achiques") or []):
            a = alarma("texto-ilegible" if x.get("ilegible") else "texto-se-achica", str(x.get("mensaje") or ""), fila=x.get("fila"))
            A.append(a)
        if d.get("drive_error"):
            A.append(alarma("drive-fallo", str(d["drive_error"])[:400]))
        elif (d.get("destino") or {}).get("tipo") != "drive":
            A.append(alarma("drive-sin-configurar"))
        hojas = {h.get("archivo"): h for h in (res.get("hojas") or [])}
        archivos = []
        for a in (d.get("archivos") or []):
            h = hojas.get(a.get("origen")) or {}
            item = {"tipo": a.get("tipo"), "nombre": a.get("nombre"), "bytes": a.get("bytes"), "sha256": a.get("sha256")}
            if a.get("tipo") == "tizada" and a.get("pagina") is not None:
                # 🔴 UNA MESA = UN ARCHIVO (MAPA 620): los MISMOS campos de antes (así no se le rompe
                # nada al otro sistema), ahora de ESTA mesa: `mesas` = 1, `largo_cm` = [su largo],
                # `consumo_cm` = su largo; `aprovechamiento` sigue siendo el de la tela entera.
                # Nuevos: `mesa` (su número dentro de la tela) y `mesas_de_la_tela`; y, si la hoja
                # los dice, la `fila` y las `copias` (Copia) o los `talles` (Talles por mesa).
                pi = int(a.get("pagina") or 0)
                alt = h.get("alturas_cm") or []
                largo = alt[pi] if pi < len(alt) else h.get("consumo_cm")
                ms = h.get("mesas") or []
                mf = ms[pi] if pi < len(ms) else None
                item.update({"tela": h.get("tela"), "mesa": a.get("mesa"), "mesas_de_la_tela": a.get("mesas_tela"), "mesas": 1,
                             "ancho_cm": h.get("ancho_cm"), "largo_cm": [largo] if largo is not None else None, "consumo_cm": largo,
                             "aprovechamiento": h.get("aprovechamiento"), "moldes": h.get("moldes")})
                if isinstance(mf, dict):
                    for k in ("fila", "copias", "talles"):
                        if mf.get(k) is not None:
                            item[k] = mf[k]
            elif a.get("tipo") == "tizada":
                item.update({"tela": h.get("tela"), "mesas": h.get("paginas"), "ancho_cm": h.get("ancho_cm"),
                             "largo_cm": h.get("alturas_cm"), "consumo_cm": h.get("consumo_cm"),
                             "aprovechamiento": h.get("aprovechamiento"), "moldes": h.get("moldes")})
            for k in ("drive_id", "enlace", "carpeta_id", "ruta"):
                if a.get(k):
                    item[k] = a[k]
            archivos.append(item)
        resultado = {
            "formato": FORMATO_RESULTADO,
            "referencia": ref,
            "pedido_externo": pedido.get("pedido_externo"),
            "cliente": pedido.get("cliente"),
            "estado": "listo",
            "generado": _ahora(),
            "segundos": d.get("segundos"),
            "tizada_id": d.get("tid"),
            "destino": d.get("destino") or {"tipo": "local"},
            "archivos": archivos,
            "resumen": {"prendas": len(normal["filas"]), "piezas": res.get("piezas"),
                        "telas": sorted({h.get("tela") for h in (res.get("hojas") or []) if h.get("tela")}),
                        "perfil_color": res.get("perfil_icc")},
            "disenos": [{"nombre": x["nombre"],
                         "moldes": [{"molde": m["pid"], "nombre": m["molde_nombre"], "variable": m.get("variable"),
                                     "variable_nombre": m.get("variable_nombre"),
                                     "tela": m.get("tela"), "tela_id": m.get("tela_id"),
                                     "no_sublimado": m.get("marcas_ident") or {}} for m in x["moldes"]]}
                        for x in normal["disenos"]],
            "alarmas": A,
        }
        _escribir_json(os.path.join(_dir_pedido(ref), "resultado.json"), resultado)
        est.update({"estado": "listo", "etapa": "terminado", "alarmas": A, "tid": d.get("tid"), "terminado": _ahora()})
        _guardar_estado(ref, est)
        _latido("esperando")
    _avisar(ref)
    _borrar_copias_a_medida(ref)          # los PDF ya están: la copia a medida sobra (MAPA 623)
    return jsonify({"ok": True, "resultado": resultado_publico(resultado, ref)})


@bp.post("/api/externo/robot/fallo/<ref>")
def robot_fallo(ref):
    """No se pudo: `rechazo` = es por algo del pedido (alarmas que frenan, no se reintenta);
    si no, es una falla del sistema y vuelve a la cola (hasta 3 veces)."""
    d = request.get_json(force=True) or {}
    with _LOCK:
        est = leer_estado(ref)
        if not est:
            return jsonify({"error": "no existe"}), 404
        if est.get("estado") == "cancelado":
            return jsonify({"ok": True})
        A = est.get("alarmas", [])
        for a in (d.get("alarmas") or []):
            if a.get("codigo") in ALARMAS:
                A.append(alarma(a["codigo"], a.get("mensaje"), **(a.get("donde") or {})))
        est["alarmas"] = A
        if d.get("rechazo"):
            est["estado"], est["etapa"] = "rechazado", str(d.get("motivo") or "hay alarmas que frenan el pedido")[:300]
            normal = _leer_json(os.path.join(_dir_pedido(ref), "normal.json"), None)
            if normal:
                _limpiar_disenos(est)
        elif int(est.get("intentos") or 0) >= 3:
            est["estado"], est["etapa"] = "error", str(d.get("motivo") or "falla del sistema")[:300]
            est["alarmas"] = A + [alarma("tizada-fallo", str(d.get("motivo") or "")[:400])]
        else:
            est["estado"], est["etapa"] = "en_cola", "se va a reintentar: " + str(d.get("motivo") or "")[:200]
        _guardar_estado(ref, est)
        _latido("esperando")
        final = est["estado"] in ("rechazado", "error")
    if final:
        _avisar(ref)
    return jsonify({"ok": True, "estado": est["estado"]})


# ── el aviso al otro sistema (webhook) ─────────────────────────────────────────────────────
def _avisar(ref):
    """Manda el estado final (con el JSON de resultado) a la dirección de aviso, en un hilo y con
    reintentos. Va firmado: `X-Tizada-Firma` = HMAC-SHA256 del cuerpo con la huella de la llave."""
    est = leer_estado(ref) or {}
    url = (est.get("aviso_url") or "").strip()
    if not url:
        return
    cuerpo = json.dumps(estado_publico(ref), ensure_ascii=False).encode("utf-8")
    ll = next((x for x in _cfg()["llaves"] if x.get("id") == est.get("llave")), None) or {}
    firma = hmac.new(str(ll.get("huella") or "").encode("ascii"), cuerpo, hashlib.sha256).hexdigest()

    def _mandar():
        ultimo = ""
        for espera in (0, 5, 30, 120):
            time.sleep(espera)
            try:
                rq = urllib.request.Request(url, data=cuerpo, method="POST", headers={
                    "Content-Type": "application/json; charset=utf-8", "User-Agent": "TIZADAPRO/1.0",
                    "X-Tizada-Referencia": ref, "X-Tizada-Firma": firma})
                with urllib.request.urlopen(rq, timeout=15) as r:
                    if 200 <= r.status < 300:
                        ultimo = "entregado"
                        break
                    ultimo = f"respondió {r.status}"
            except Exception as e:
                ultimo = str(e)[:200]
        with _LOCK:
            e2 = leer_estado(ref)
            if e2:
                e2["aviso"] = {"cuando": _ahora(), "resultado": ultimo}
                _escribir_json(os.path.join(_dir_pedido(ref), "estado.json"), e2)

    threading.Thread(target=_mandar, daemon=True, name=f"aviso-{ref}").start()


# ══ PLANTILLAS Y CONECTORES PARA EL OTRO SISTEMA (MAPA 619) ════════════════════════════════════
# Pedido del usuario (2026-10-05): «desde el sistema externo deben de poder usar el botón de
# plantilla para descargar la extensión y crear las bases en Corel o Illustrator… a ellos no les
# viaja la visual de TIZADA, pero podrán tener los archivos a descargar y lo necesario para crear
# en Illustrator o Corel el archivo base».
#   · CONECTORES: los instaladores de Illustrator (Windows y Mac) y de CorelDRAW, para bajar.
#   · PLANTILLAS: el otro sistema pide la base de unos diseños (cada uno con sus variables) y, como
#     un pedido, la arma el ROBOT con el mismo cálculo de la ventana «Crear plantilla» de TIZADA
#     (`motor/molde/plantillaPedido.js`). Quedan, por diseño, tres archivos para bajar:
#       - «<diseño> - Illustrator.json»: lo que se le manda al conector de Illustrator (POST a
#         http://127.0.0.1:47850/plantilla desde la computadora del diseñador) y arma la base allá;
#       - «<diseño> - CorelDRAW.json»: lo mismo para CorelDRAW (POST a http://127.0.0.1:47851/plantilla);
#       - «guia_<diseño>.ai»: la guía, que se abre en cualquier Illustrator sin conector.
# Nada de esto toca un molde ni un diseño: la plantilla sólo LEE.
MODOS_TALLES = ("todos", "rango", "por_talle")
CONFIG_DE_MODO = {"todos": "default", "rango": "rango", "por_talle": "talle"}
ESCALAS = (100, 90, 80, 70, 60, 50, 40, 30, 20, 10)
CONECTOR_LOCAL = {"illustrator": "http://127.0.0.1:47850/plantilla", "corel": "http://127.0.0.1:47851/plantilla"}


def _dir_plantilla(ref):
    return os.path.join(_raiz(), "plantillas", ref)


def leer_plantilla(ref):
    return _leer_json(os.path.join(_dir_plantilla(ref), "estado.json"), None)


def _guardar_plantilla(ref, est):
    est["actualizado"] = _ahora()
    _escribir_json(os.path.join(_dir_plantilla(ref), "estado.json"), est)


def _plantillas():
    base = os.path.join(_raiz(), "plantillas")
    try:
        refs = [r for r in os.listdir(base) if os.path.isdir(os.path.join(base, r))]
    except OSError:
        refs = []
    return [e for e in (leer_plantilla(r) for r in refs) if e]


def _capas_arte(pids, cat):
    """Las capas del arte que la base trae vacías, EN ORDEN: «diseño» y una por cada columna de
    nombre/número de la planilla de esos moldes (lo mismo que `capasArteNombres` de la pantalla)."""
    out, vistos = ["diseño"], {"diseño", "guias", "molde"}
    reglas = cat.get("reglas_planilla") or []
    prods = {p["id"]: p for p in cat.get("productos", [])}
    for pid in pids:
        tpl = _plantilla_de(prods.get(pid), cat) or {}
        for c in tpl.get("columnas") or []:
            reg = next((r for r in reglas if r.get("id") == c.get("reglaId")), None) \
                or next((r for r in reglas if r.get("comportamiento") == (c.get("role") or "none")), None)
            comp = (reg or {}).get("comportamiento") or c.get("role")
            if comp not in ("nombre", "numero"):
                continue
            nom = str((reg or {}).get("nombre") or c.get("label") or "").strip()
            if nom and nom.lower() not in vistos:
                vistos.add(nom.lower())
                out.append(nom)
    return out


def revisar_plantilla(body):
    """Revisa el pedido de plantilla SIN abrir nada. → (alarmas, normal|None). `normal` es lo que
    usa el robot: cada diseño con sus variables ya resueltas (molde, variable del catálogo, acomodo)."""
    A = []
    if not isinstance(body, dict):
        return [alarma("pedido-json-invalido")], None
    ref = str(body.get("referencia") or "").strip()
    if not ref:
        A.append(alarma("campo-falta", campo="referencia"))
    elif not _RX_REF.match(ref):
        A.append(alarma("referencia-invalida", campo="referencia"))
    cat = S._cargar_catalogo()
    prods = {p["id"]: p for p in cat.get("productos", [])}
    disenos = body.get("disenos")
    if not isinstance(disenos, list) or not disenos:
        A.append(alarma("disenos-vacio", campo="disenos"))
        disenos = []
    norm_d, nombres, pids = [], set(), []
    for i, d in enumerate(disenos):
        donde = f"disenos[{i}]"
        if not isinstance(d, dict):
            A.append(alarma("campo-tipo", "cada diseño es un objeto {nombre, variables}", campo=donde))
            continue
        nom = str(d.get("nombre") or "").strip()
        if not nom:
            A.append(alarma("campo-falta", campo=donde + ".nombre"))
            continue
        if _norm(nom) in nombres:
            A.append(alarma("diseno-repetido", f"«{nom}»", campo=donde + ".nombre"))
            continue
        nombres.add(_norm(nom))
        vs = d.get("variables")
        if not isinstance(vs, list) or not vs:
            A.append(alarma("plantilla-sin-variables", f"«{nom}»", campo=donde + ".variables"))
            continue
        vars_ = []
        for j, v in enumerate(vs):
            dv = f"{donde}.variables[{j}]"
            q = v.get("variable") if isinstance(v, dict) else v
            mol = v.get("molde") if isinstance(v, dict) else None
            q = str(q or "").strip()
            if not q:
                A.append(alarma("campo-falta", campo=dv))
                continue
            if mol:
                prod = prods.get(str(mol))
                var = next((x for x in ((prod or {}).get("variantes") or []) if x.get("clave") == q or _norm(x.get("label")) == _norm(q)), None)
                pid = prod["id"] if prod and var else None
                amb = []
            else:
                pid, amb = _molde_de_variable(q, prods)
                var = next((x for x in ((prods.get(pid) or {}).get("variantes") or []) if x.get("clave") == q or _norm(x.get("label")) == _norm(q)), None) if pid else None
            if amb:
                A.append(alarma("variable-ambigua", f"«{q}» está en: " + ", ".join(amb), campo=dv))
                continue
            if not pid or not var:
                A.append(alarma("variable-desconocida", f"«{q}»", campo=dv))
                continue
            prod = prods[pid]
            try:
                reg = S._cargar("registro_producto.json", pid) or {}
            except Exception:
                reg = {}
            listo, motivo = _molde_listo(prod, reg)
            if not listo:
                A.append(alarma("molde-no-disponible", f"«{prod.get('nombre') or pid}»: {motivo}", campo=dv))
                continue
            key = f"{nom}|{pid}|{var.get('clave')}"
            # MOLDE A MEDIDA (MAPA 623): la plantilla se arma a la medida que viene en la variable
            medida_v = None
            if isinstance(prod.get("a_medida"), dict):
                md = v.get("medida") if isinstance(v, dict) and isinstance(v.get("medida"), dict) else (v if isinstance(v, dict) else {})
                an, al = S._metros(md.get("ancho_m")), S._metros(md.get("alto_m"))
                if md.get("ancho_m") in (None, "") or md.get("alto_m") in (None, ""):
                    A.append(alarma("medida-falta", f"«{prod.get('nombre')}» en «{nom}»", campo=dv + ".medida"))
                    continue
                if an is None or al is None:
                    A.append(alarma("medida-invalida", f"«{md.get('ancho_m')} × {md.get('alto_m')}»", campo=dv + ".medida"))
                    continue
                medida_v = {"ancho_m": an, "alto_m": al}
                key += "|" + S._talle_de_medida(an, al)
            if any(x["key"] == key for x in vars_):
                continue                                     # la misma variable dos veces: una
            vars_.append({"key": key, "pid": pid, "clave": var.get("clave"), "label": var.get("label") or var.get("clave"),
                          "molde": prod.get("nombre") or pid, "variable": var, "acomodo": prod.get("acomodo_illustrator") or {},
                          "talles": S._talles_de_registro(reg, pid),
                          **({"medida": medida_v, "dobladillo": (_a_medida_publico_ext(prod) or {}).get("margen_cm")} if medida_v else {})})
            if pid not in pids:
                pids.append(pid)
        if vars_:
            norm_d.append({"nombre": nom, "vars": vars_})
    # cómo se adapta a los talles (los tres modos de la ventana)
    t = body.get("talles") if isinstance(body.get("talles"), dict) else {}
    modo = str(t.get("modo") or "todos").strip().lower()
    todos = {str(x).lower(): x for d in norm_d for it in d["vars"] for x in it["talles"]}
    talles_sel, rangos = None, []
    if modo not in MODOS_TALLES:
        A.append(alarma("talles-invalidos", f"modo «{modo}»: usar " + ", ".join(MODOS_TALLES), campo="talles.modo"))
    elif modo == "por_talle" and t.get("talles") is not None:
        lst = t.get("talles") if isinstance(t.get("talles"), list) else []
        talles_sel = []
        for x in lst:
            real = todos.get(str(x).strip().lower())
            if real is None:
                A.append(alarma("talles-invalidos", f"el talle «{x}» no es de ninguna variable pedida", campo="talles.talles"))
            elif real not in talles_sel:
                talles_sel.append(real)
        if not lst:
            A.append(alarma("talles-invalidos", "`talles` vacío: mandar al menos uno, o no mandarlo (= todos)", campo="talles.talles"))
    elif modo == "rango":
        for k, rg in enumerate(t.get("rangos") or []):
            lst = (rg or {}).get("talles") if isinstance(rg, dict) else rg
            reales = []
            for x in (lst if isinstance(lst, list) else []):
                real = todos.get(str(x).strip().lower())
                if real is None:
                    A.append(alarma("talles-invalidos", f"el talle «{x}» no es de ninguna variable pedida", campo=f"talles.rangos[{k}]"))
                elif real not in reales:
                    reales.append(real)
            if not reales:
                continue
            guia = (rg or {}).get("guia") if isinstance(rg, dict) else None
            guia = todos.get(str(guia or "").strip().lower())
            rangos.append({"talles": reales, "guia": guia if guia in reales else reales[0]})
        if not rangos:
            A.append(alarma("talles-invalidos", "«rango» necesita `rangos`: [{\"talles\": [\"XS\", \"M\"], \"guia\": \"S\"}]", campo="talles.rangos"))
    try:
        escala = int(body.get("escala") or 100)
    except Exception:
        escala = 0
    if escala not in ESCALAS:
        A.append(alarma("escala-invalida", campo="escala"))
    if _frenan(A) or not norm_d:
        if not _frenan(A):
            A.append(alarma("disenos-vacio", campo="disenos"))
        return A, None
    # el orden de los talles en un rango: el del primer molde que los tiene (como la pantalla)
    orden = []
    for d in norm_d:
        for it in d["vars"]:
            for x in it["talles"]:
                if x not in orden:
                    orden.append(x)
    for rg in rangos:
        rg["talles"] = [x for x in orden if x in rg["talles"]]
    if talles_sel:
        talles_sel = [x for x in orden if x in talles_sel]
    return A, {"referencia": ref, "disenos": norm_d, "config": CONFIG_DE_MODO[modo], "talles_sel": talles_sel,
               "rangos": rangos, "escala": escala, "capas": _capas_arte(pids, cat)}


def _archivo_plantilla_publico(ref, a):
    return {**a, "descarga": f"/api/externo/v1/plantillas/{ref}/archivos/{urllib.parse.quote(str(a.get('nombre') or ''))}"}


def plantilla_publica(ref):
    est = leer_plantilla(ref)
    if not est:
        return None
    out = {k: est.get(k) for k in ("referencia", "estado", "etapa", "recibido", "actualizado", "alarmas")}
    if est.get("estado") == "listo":
        out["archivos"] = [_archivo_plantilla_publico(ref, a) for a in (est.get("archivos") or [])]
        out["como_usar"] = {
            "illustrator": "Con el conector de Illustrator instalado e Illustrator abierto, desde la computadora del diseñador: "
                           "POST del contenido del archivo «… - Illustrator.json» (tal cual, Content-Type: application/json) a "
                           + CONECTOR_LOCAL["illustrator"] + ". Arma las mesas, capas y contornos y guarda el .ai en "
                           "Documentos › USER PRO › Plantillas. Si hay varios archivos de Illustrator para un diseño, se manda cada uno.",
            "corel": "Con el conector de CorelDRAW instalado (CorelDRAW 2022 o más nuevo): POST del contenido de «… - CorelDRAW.json» a "
                     + CONECTOR_LOCAL["corel"] + ". Si CorelDRAW está cerrado, se abre solo.",
            "guia": "«guia_….ai» se abre en cualquier Illustrator, sin conector.",
            "conectores": "Los instaladores, en /api/externo/v1/conectores. Para saber si el conector está: GET "
                          "http://127.0.0.1:47850/estado (Illustrator) o http://127.0.0.1:47851/estado (CorelDRAW) desde esa computadora.",
        }
    return out


@bp.post("/api/externo/v1/plantillas")
def v1_plantilla_pedir():
    """Pide la base (Illustrator, CorelDRAW y guía .ai) de unos diseños: contesta en el acto si los
    datos sirven y la arma el robot (segundos). El resultado se consulta en GET /plantillas/<ref>."""
    try:
        body = request.get_json(force=True)
    except Exception:
        body = None
    with _LOCK:
        al, normal = revisar_plantilla(body)
        ref = normal["referencia"] if normal else (str((body or {}).get("referencia") or "") or None if isinstance(body, dict) else None)
        if normal is None:
            return jsonify({"referencia": ref, "aceptado": False, "estado": "rechazado", "alarmas": al}), 422
        previo = leer_plantilla(ref)
        if previo and previo.get("estado") in ("en_cola", "procesando"):
            al.append(alarma("referencia-en-proceso", campo="referencia"))
            return jsonify({"referencia": ref, "aceptado": False, "estado": "rechazado", "alarmas": al}), 409
        carpeta = _dir_plantilla(ref)
        shutil.rmtree(os.path.join(carpeta, "salida"), ignore_errors=True)      # una plantilla se rehace entera
        _escribir_json(os.path.join(carpeta, "normal.json"), normal)
        ll = getattr(g, "_llave", None) or {}
        _guardar_plantilla(ref, {"referencia": ref, "estado": "en_cola", "etapa": "esperando al robot", "recibido": _ahora(),
                                 "intentos": 0, "alarmas": al, "llave": ll.get("id"), "integracion": ll.get("nombre")})
    return jsonify({"referencia": ref, "aceptado": True, "estado": "en_cola", "alarmas": al}), 202


@bp.get("/api/externo/v1/plantillas/<ref>")
def v1_plantilla_estado(ref):
    if not _RX_REF.match(ref):
        return jsonify({"error": "referencia inválida"}), 400
    e = plantilla_publica(ref)
    return (jsonify(e), 200) if e else (jsonify({"error": "no hay ninguna plantilla con esa referencia"}), 404)


def _tipo_mime(nombre):
    n = nombre.lower()
    return "application/json" if n.endswith(".json") else ("application/postscript" if n.endswith(".ai") else "application/octet-stream")


@bp.get("/api/externo/v1/plantillas/<ref>/archivos/<nombre>")
def v1_plantilla_archivo(ref, nombre):
    """Un archivo de la plantilla. Sólo los que nombra su estado, y sólo de SU carpeta."""
    if not _RX_REF.match(ref):
        return jsonify({"error": "referencia inválida"}), 400
    est = leer_plantilla(ref) or {}
    a = next((x for x in est.get("archivos") or [] if x.get("nombre") == nombre), None)
    base = os.path.realpath(os.path.join(_dir_plantilla(ref), "salida"))
    ruta = os.path.realpath(os.path.join(base, nombre)) if a else ""
    if not a or not ruta.startswith(base + os.sep) or not os.path.isfile(ruta):
        return jsonify({"error": "ese archivo no es de esta plantilla o ya no está en el servidor"}), 404
    return send_file(ruta, mimetype=_tipo_mime(nombre), as_attachment=request.args.get("descargar") == "1", download_name=nombre)


# ── los conectores (los instaladores) ─────────────────────────────────────────────────────────
def _conectores():
    """{clave: (ruta, nombre de archivo, versión, para qué)} de los instaladores que tiene ESTE
    servidor. Salen de los mismos lugares que la pantalla del taller (`_illustrator_version`,
    `_corel_version`); en el publicado viajan en el paquete pero la pantalla no los ofrece
    (decisión del 2026-09-24: «se le pasa a cada usuario manual»): sólo los da esta API."""
    out = {}
    try:
        base, v, exe = S._illustrator_version()
        if exe:
            out["illustrator"] = (os.path.join(base, exe), exe, v, "Windows")
        if v and os.path.isdir(os.path.join(base, "com.tizadapro.illustrator")):
            out["illustrator-mac"] = (None, f"USER-PRO-Illustrator-Mac-{v}.zip", v, "Mac")
    except Exception:
        pass
    try:
        base, v, exe = S._corel_version()
        if exe:
            out["corel"] = (os.path.join(base, exe), exe, v, "Windows")
    except Exception:
        pass
    return out


@bp.get("/api/externo/v1/conectores")
def v1_conectores():
    c = _conectores()
    prog = {"illustrator": "Illustrator", "illustrator-mac": "Illustrator", "corel": "CorelDRAW"}
    return jsonify({"conectores": [{"clave": k, "programa": prog[k], "sistema": x[3], "version": x[2], "archivo": x[1],
                                    "descarga": f"/api/externo/v1/conectores/{k}"} for k, x in c.items()],
                    "nota": "Se instalan UNA vez en la computadora donde se diseña (doble clic, «Instalar»). "
                            "CorelDRAW necesita la versión 2022 o más nueva (sólo Windows). Para saber si ya está: "
                            "GET http://127.0.0.1:47850/estado (Illustrator) o http://127.0.0.1:47851/estado (CorelDRAW) desde esa computadora."})


@bp.get("/api/externo/v1/conectores/<clave>")
def v1_conector(clave):
    c = _conectores().get(clave)
    if not c:
        return jsonify({"error": "este servidor no tiene ese conector"}), 404
    ruta, nombre, _v, _s = c
    if ruta:
        return send_file(ruta, as_attachment=True, download_name=nombre, max_age=0)
    # Mac: la extensión con su instalador, armada en el momento (la misma que arma el taller)
    from flask import Response
    datos, nom = S._zip_extension_illustrator()
    if datos is None:
        return jsonify({"error": "este servidor no tiene ese conector"}), 404
    return Response(datos, mimetype="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{nom}"', "Cache-Control": "no-store"})


# ── el robot y las plantillas ─────────────────────────────────────────────────────────────────
def _tomar_plantilla():
    """La plantilla más vieja en cola (o una que quedó a medias), para el robot. None si no hay."""
    ahora = time.time()
    cola = []
    for e in _plantillas():
        if e.get("estado") == "en_cola":
            cola.append(e)
        elif e.get("estado") == "procesando":
            try:
                visto = time.mktime(time.strptime(e.get("actualizado"), "%Y-%m-%dT%H:%M:%S"))
            except Exception:
                visto = 0
            if ahora - visto > ESPERA_ROBOT_S:
                cola.append(e)
    cola.sort(key=lambda e: e.get("recibido") or "")
    for est in cola:
        ref = est["referencia"]
        if int(est.get("intentos") or 0) >= 3:
            est["estado"], est["etapa"] = "error", "se intentó 3 veces y no se pudo armar"
            _guardar_plantilla(ref, est)
            continue
        normal = _leer_json(os.path.join(_dir_plantilla(ref), "normal.json"), None)
        if not normal:
            est["estado"], est["etapa"] = "error", "el pedido guardado no se puede leer"
            _guardar_plantilla(ref, est)
            continue
        est["estado"], est["etapa"] = "procesando", "armando la plantilla"
        est["intentos"] = int(est.get("intentos") or 0) + 1
        _guardar_plantilla(ref, est)
        return {"tarea": "plantilla", "referencia": ref, "normal": normal}
    return None


_RX_NOMBRE_ARCHIVO = re.compile(r"^[^\\/:*?\"<>|\x00-\x1f]{1,180}\.(json|ai)$")


@bp.post("/api/externo/robot/plantilla/<ref>/archivo")
def robot_plantilla_archivo(ref):
    """El robot deja UN archivo de la plantilla (cuerpo crudo) en su carpeta de salida."""
    nombre = str(request.args.get("nombre") or "")
    if not _RX_REF.match(ref) or not _RX_NOMBRE_ARCHIVO.match(nombre) or nombre.strip() != nombre:
        return jsonify({"error": "nombre inválido"}), 400
    est = leer_plantilla(ref)
    if not est or est.get("estado") != "procesando":
        return jsonify({"error": "esa plantilla no se está armando"}), 409
    base = os.path.join(_dir_plantilla(ref), "salida")
    os.makedirs(base, exist_ok=True)
    ruta = os.path.join(base, nombre)
    with open(ruta + ".tmp", "wb") as fh:
        fh.write(request.get_data())
    os.replace(ruta + ".tmp", ruta)
    return jsonify({"ok": True, "bytes": os.path.getsize(ruta)})


@bp.post("/api/externo/robot/plantilla/<ref>/terminar")
def robot_plantilla_terminar(ref):
    """Quedó armada: se anotan los archivos (sólo los que están en su carpeta) y los avisos."""
    d = request.get_json(force=True) or {}
    with _LOCK:
        est = leer_plantilla(ref)
        if not est:
            return jsonify({"error": "no existe"}), 404
        base = os.path.join(_dir_plantilla(ref), "salida")
        archivos = []
        for a in d.get("archivos") or []:
            nom = str(a.get("nombre") or "")
            ruta = os.path.join(base, nom)
            if not _RX_NOMBRE_ARCHIVO.match(nom) or not os.path.isfile(ruta):
                continue
            with open(ruta, "rb") as fh:
                sha = hashlib.sha256(fh.read()).hexdigest()
            archivos.append({"diseno": str(a.get("diseno") or ""), "tipo": a.get("tipo") if a.get("tipo") in ("illustrator", "corel", "guia") else "otro",
                             "nombre": nom, "bytes": os.path.getsize(ruta), "sha256": sha,
                             **({"parte": a["parte"]} if a.get("parte") else {})})
        A = [x for x in est.get("alarmas", []) if x.get("etapa") == "datos"]
        for c in d.get("choques") or []:
            A.append(alarma("plantilla-mesas-chocan", f"En «{c.get('diseno')}», la mesa «{c.get('mesa')}»: "
                            + " · ".join(str(x) for x in (c.get("piezas") or [])) + ".", diseno=c.get("diseno")))
        for t in d.get("avisos") or []:
            A.append(alarma("plantilla-aviso", str(t)[:400]))
        est.update({"estado": "listo", "etapa": "terminado", "archivos": archivos, "alarmas": A, "terminado": _ahora()})
        _guardar_plantilla(ref, est)
    _borrar_copias_a_medida(ref)          # la copia a medida ya no hace falta (MAPA 623)
    return jsonify({"ok": True})


@bp.post("/api/externo/robot/plantilla/<ref>/fallo")
def robot_plantilla_fallo(ref):
    """No se pudo: `rechazo` = por algo de lo pedido (no se reintenta); si no, vuelve a la cola."""
    d = request.get_json(force=True) or {}
    with _LOCK:
        est = leer_plantilla(ref)
        if not est:
            return jsonify({"error": "no existe"}), 404
        motivo = str(d.get("motivo") or "falla del sistema")[:300]
        if d.get("rechazo") or int(est.get("intentos") or 0) >= 3:
            est["estado"], est["etapa"] = ("rechazado" if d.get("rechazo") else "error"), motivo
            est["alarmas"] = est.get("alarmas", []) + [alarma("plantilla-fallo", motivo)]
        else:
            est["estado"], est["etapa"] = "en_cola", "se va a reintentar: " + motivo[:200]
        _guardar_plantilla(ref, est)
    _borrar_copias_a_medida(ref)          # el reintento arma otra copia (MAPA 623)
    return jsonify({"ok": True, "estado": est["estado"]})


def _purgar_plantillas(dias):
    """Las plantillas terminadas hace más de `dias`: se borran sus archivos (queda el estado)."""
    n = 0
    for est in _plantillas():
        if est.get("estado") not in ("listo", "rechazado", "error") or est.get("purgado"):
            continue
        try:
            visto = time.mktime(time.strptime(est.get("actualizado"), "%Y-%m-%dT%H:%M:%S"))
        except Exception:
            continue
        if time.time() - visto < dias * 86400:
            continue
        shutil.rmtree(os.path.join(_dir_plantilla(est["referencia"]), "salida"), ignore_errors=True)
        est["purgado"] = _ahora()
        est["archivos"] = []
        _escribir_json(os.path.join(_dir_plantilla(est["referencia"]), "estado.json"), est)
        n += 1
    return n


# ══ /api/integracion — la pantalla Configuración › Integraciones ═══════════════════════════════
def _robot_estado():
    lat = _leer_json(os.path.join(_raiz(), "robot_latido.json"), None) or {}
    hace = time.time() - float(lat.get("cuando") or 0)
    return {"vivo": hace < 60, "hace_s": int(hace) if lat else None, "que": lat.get("que"), "referencia": lat.get("referencia"),
            "motivo": _ROBOT.get("motivo") or ""}


@bp.get("/api/integracion/estado")
def adm_estado():
    c = _cfg()
    cuenta = _leer_json(os.path.join(_raiz(), "drive_cuenta.json"), None) or {}
    peds = sorted(_pedidos(), key=lambda e: e.get("recibido") or "", reverse=True)[:200]
    return jsonify({
        "llaves": [{k: ll.get(k) for k in ("id", "nombre", "creada", "activa", "pista")} for ll in c["llaves"]],
        "drive": {"activo": bool(c["drive"].get("activo")), "carpeta_id": c["drive"].get("carpeta_id") or "",
                  "carpeta_tizadas": _carpetas_drive(c)[0], "carpeta_fichas": _carpetas_drive(c)[1],
                  "cuenta": cuenta.get("client_email") or "", "prueba": c["drive"].get("prueba"),
                  "cliente": bool(_leer_json(os.path.join(_raiz(), "drive_oauth_cliente.json"), None)),
                  "conectada": (_leer_json(os.path.join(_raiz(), "drive_oauth_token.json"), None) or {}).get("email") or "",
                  "vuelta": _vuelta_de_request()},
        "robot": {"activo": bool(c["robot"].get("activo", True)), **_robot_estado()},
        "aviso_url": c.get("aviso_url") or "",
        "pedidos": [{k: e.get(k) for k in ("referencia", "estado", "etapa", "recibido", "actualizado", "cliente",
                                           "integracion", "intentos", "tid", "aviso")}
                    | {"alarmas": len(e.get("alarmas") or []), "frenan": len(_frenan(e.get("alarmas") or []))} for e in peds],
        "rechazos": _leer_json(os.path.join(_raiz(), "rechazos.json"), []) or [],
    })


@bp.get("/api/integracion/pedidos/<ref>")
def adm_pedido(ref):
    if not _RX_REF.match(ref):
        return jsonify({"error": "referencia inválida"}), 400
    est = leer_estado(ref)
    if not est:
        return jsonify({"error": "no existe"}), 404
    return jsonify({"estado": est, "pedido": _leer_json(os.path.join(_dir_pedido(ref), "pedido.json"), None),
                    "resultado": _leer_json(os.path.join(_dir_pedido(ref), "resultado.json"), None)})


@bp.post("/api/integracion/llaves/crear")
def adm_llave_crear():
    nombre = str((request.get_json(force=True) or {}).get("nombre") or "").strip()[:60]
    if not nombre:
        return jsonify({"error": "poné un nombre para reconocer la llave (p. ej. «Sistema de ventas»)"}), 400
    llave = "tzp_" + secrets.token_urlsafe(32)
    with _LOCK:
        c = _cfg()
        c["llaves"].append({"id": secrets.token_hex(4), "nombre": nombre, "huella": _huella(llave),
                            "pista": llave[:8] + "…", "creada": _ahora(), "activa": True})
        _cfg_guardar(c)
    # la llave se muestra UNA vez: sólo queda guardada su huella
    return jsonify({"ok": True, "llave": llave})


@bp.post("/api/integracion/llaves/revocar")
def adm_llave_revocar():
    lid = str((request.get_json(force=True) or {}).get("id") or "")
    with _LOCK:
        c = _cfg()
        for ll in c["llaves"]:
            if ll.get("id") == lid:
                ll["activa"] = False
        _cfg_guardar(c)
    return jsonify({"ok": True})


@bp.post("/api/integracion/config")
def adm_config():
    d = request.get_json(force=True) or {}
    with _LOCK:
        c = _cfg()
        if "aviso_url" in d:
            u = str(d.get("aviso_url") or "").strip()
            if u and urllib.parse.urlparse(u).scheme not in ("http", "https"):
                return jsonify({"error": "la dirección de aviso tiene que empezar con http:// o https://"}), 400
            c["aviso_url"] = u
        if "drive_activo" in d:
            c["drive"]["activo"] = bool(d.get("drive_activo"))
        # se acepta el enlace entero de la carpeta: se queda con su id
        def _id(v):
            m = re.search(r"/folders/([A-Za-z0-9_-]+)", v)
            return m.group(1) if m else v
        if "drive_carpeta" in d:
            c["drive"]["carpeta_id"] = _id(str(d.get("drive_carpeta") or "").strip())
        if "drive_carpeta_tizadas" in d:
            c["drive"]["carpeta_tizadas"] = _id(str(d.get("drive_carpeta_tizadas") or "").strip())
        if "drive_carpeta_fichas" in d:
            c["drive"]["carpeta_fichas"] = _id(str(d.get("drive_carpeta_fichas") or "").strip())
        if "robot_activo" in d:
            c["robot"]["activo"] = bool(d.get("robot_activo"))
        if d.get("probar_drive"):
            c["probar_drive"] = True
            c["drive"].pop("prueba", None)
        _cfg_guardar(c)
    return jsonify({"ok": True})


@bp.post("/api/integracion/drive_cuenta")
def adm_drive_cuenta():
    """El archivo .json de la cuenta de servicio de Google (lo carga la persona; no se muestra más)."""
    f = request.files.get("archivo")
    if f is None:
        return jsonify({"error": "falta el archivo"}), 400
    try:
        cuenta = json.loads(f.read().decode("utf-8-sig"))
    except Exception:
        cuenta = {}
    if not isinstance(cuenta, dict):
        cuenta = {}
    # el «ID de cliente OAuth» que se baja de Google Cloud (tipo «Aplicación web» o «de escritorio»)
    _cli = cuenta.get("web") or cuenta.get("installed")
    if isinstance(_cli, dict) and _cli.get("client_id") and _cli.get("client_secret"):
        _escribir_json(os.path.join(_raiz(), "drive_oauth_cliente.json"),
                       {"tipo": "web" if cuenta.get("web") else "escritorio", "client_id": _cli["client_id"],
                        "client_secret": _cli["client_secret"],
                        "auth_uri": _cli.get("auth_uri") or "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": _cli.get("token_uri") or "https://oauth2.googleapis.com/token",
                        "redirect_uris": _cli.get("redirect_uris") or []})
        try:
            os.remove(os.path.join(_raiz(), "drive_oauth_token.json"))     # otro cliente: hay que reconectar
        except OSError:
            pass
        return jsonify({"ok": True, "cliente": True})
    if not (cuenta.get("type") == "service_account" and cuenta.get("private_key") and cuenta.get("client_email")):
        return jsonify({"error": "ese archivo no es de Google: tiene que ser el «ID de cliente OAuth» (.json) o la llave "
                                 "de una cuenta de servicio (.json)"}), 422
    _escribir_json(os.path.join(_raiz(), "drive_cuenta.json"),
                   {k: cuenta.get(k) for k in ("type", "project_id", "private_key_id", "private_key", "client_email", "token_uri")})
    return jsonify({"ok": True, "cuenta": cuenta.get("client_email")})


# ── CONECTAR CON GOOGLE (OAuth de la persona dueña de la carpeta) ───────────────────────────
# La persona toca «Conectar con Google», Google le pregunta si deja que TIZADA PRO use su Drive y
# vuelve acá con un código; el servidor lo cambia por un permiso que no vence (`refresh_token`) y lo
# guarda. Nadie copia ni pega ninguna clave. `state` ata la vuelta a quien tocó el botón: la vuelta
# no pide sesión (si la página se abrió con 127.0.0.1 y Google vuelve a localhost, la cookie no viaja).
_ESTADOS_OAUTH = {}
_SCOPE_DRIVE = "https://www.googleapis.com/auth/drive"


def _vuelta_de_request():
    """La dirección de vuelta que hay que registrar en Google: la de ESTE servidor, como lo ve el navegador."""
    if not has_request_context():
        return ""
    base = (request.headers.get("X-Tizada-Origen") or "").strip() or request.host_url.rstrip("/")
    return base + "/api/integracion/drive/vuelta"


@bp.post("/api/integracion/drive/conectar")
def adm_drive_conectar():
    cli = _leer_json(os.path.join(_raiz(), "drive_oauth_cliente.json"), None)
    if not cli:
        return jsonify({"error": "primero cargá el archivo del «ID de cliente OAuth» de Google"}), 409
    d = request.get_json(silent=True) or {}
    vuelta = str(d.get("vuelta") or "").strip() or _vuelta_de_request()
    u = urllib.parse.urlparse(vuelta)
    if u.scheme not in ("http", "https") or not u.netloc or not u.path.endswith("/api/integracion/drive/vuelta"):
        return jsonify({"error": "dirección de vuelta inválida"}), 400
    estado = secrets.token_urlsafe(24)
    ahora = time.time()
    for k in [k for k, v in _ESTADOS_OAUTH.items() if ahora - v["t"] > 900]:
        _ESTADOS_OAUTH.pop(k, None)
    volver = str(d.get("volver") or "/admin")[:300]
    if not volver.startswith("/") and not volver.startswith(u.scheme + "://" + u.netloc):
        volver = "/admin"
    _ESTADOS_OAUTH[estado] = {"t": ahora, "vuelta": vuelta, "volver": volver}
    url = cli["auth_uri"] + "?" + urllib.parse.urlencode({
        "client_id": cli["client_id"], "redirect_uri": vuelta, "response_type": "code", "scope": _SCOPE_DRIVE,
        "access_type": "offline", "prompt": "consent", "include_granted_scopes": "true", "state": estado})
    return jsonify({"url": url, "vuelta": vuelta})


def _post_form(url, datos):
    import urllib.error
    rq = urllib.request.Request(url, data=urllib.parse.urlencode(datos).encode(), method="POST",
                                headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(rq, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            return {"error": f"Google respondió {e.code}"}
    except Exception as e:
        return {"error": str(e)[:200]}


def _pagina_vuelta(ok, texto, volver="/admin"):
    import html as _h
    color = "#2ecc71" if ok else "#e0503a"
    marca = "&#10003;" if ok else "&#10007;"
    pagina = ("<!doctype html><meta charset='utf-8'><title>TIZADA PRO</title>"
              "<body style='background:#000;color:#eee;font:15px system-ui;display:flex;align-items:center;"
              "justify-content:center;height:100vh;margin:0'><div style='max-width:520px;text-align:center'>"
              f"<div style='font-size:42px;color:{color}'>{marca}</div><p>{texto}</p>"
              f"<p><a style='color:#00d8f5' href='{_h.escape(volver, quote=True)}'>Volver a TIZADA PRO</a></p></div>")
    return pagina, (200 if ok else 400), {"Content-Type": "text/html; charset=utf-8"}


@bp.get("/api/integracion/drive/vuelta")
def adm_drive_vuelta():
    import html as _h
    est = _ESTADOS_OAUTH.pop(request.args.get("state") or "", None)
    if not est or time.time() - est["t"] > 900:
        return _pagina_vuelta(False, "Esta conexión venció o no se pidió desde TIZADA PRO. "
                                     "Volvé a tocar «Conectar con Google».")
    volver = est.get("volver") or "/admin"
    if request.args.get("error"):
        return _pagina_vuelta(False, "Google no dio el permiso (" + _h.escape(request.args.get("error")) + ").", volver)
    cli = _leer_json(os.path.join(_raiz(), "drive_oauth_cliente.json"), None) or {}
    r = _post_form(cli.get("token_uri") or "https://oauth2.googleapis.com/token", {
        "code": request.args.get("code") or "", "client_id": cli.get("client_id"),
        "client_secret": cli.get("client_secret"), "redirect_uri": est["vuelta"], "grant_type": "authorization_code"})
    if not r.get("refresh_token"):
        return _pagina_vuelta(False, "Google no entregó el permiso permanente: "
                              + _h.escape(str(r.get("error_description") or r.get("error") or r)[:200]), volver)
    email = ""
    try:
        api = (os.environ.get("TIZADA_DRIVE_API") or "https://www.googleapis.com").rstrip("/")
        rq = urllib.request.Request(api + "/drive/v3/about?fields=user(emailAddress)",
                                    headers={"Authorization": "Bearer " + str(r.get("access_token") or "")})
        with urllib.request.urlopen(rq, timeout=20) as rr:
            email = ((json.loads(rr.read().decode("utf-8")) or {}).get("user") or {}).get("emailAddress") or ""
    except Exception:
        pass
    _escribir_json(os.path.join(_raiz(), "drive_oauth_token.json"),
                   {"refresh_token": r["refresh_token"], "email": email, "cuando": _ahora(), "scope": r.get("scope")})
    with _LOCK:
        c = _cfg()
        c["drive"]["activo"] = True
        c["probar_drive"] = True
        c["drive"].pop("prueba", None)
        _cfg_guardar(c)
    return _pagina_vuelta(True, "Listo: TIZADA PRO guarda las tizadas en el Drive de <b>"
                          + _h.escape(email or "tu cuenta") + "</b>. Se está probando la conexión: el resultado "
                          "aparece en Configuración &rsaquo; Integraciones.", volver)


@bp.post("/api/integracion/drive/desconectar")
def adm_drive_desconectar():
    try:
        os.remove(os.path.join(_raiz(), "drive_oauth_token.json"))
    except OSError:
        pass
    return jsonify({"ok": True})


@bp.post("/api/integracion/pedidos/<ref>/reintentar")
def adm_reintentar(ref):
    with _LOCK:
        est = leer_estado(ref)
        if not est:
            return jsonify({"error": "no existe"}), 404
        if est.get("estado") in ("en_cola", "procesando"):
            return jsonify({"error": "ese pedido ya está en marcha"}), 409
        est.update({"estado": "en_cola", "etapa": "esperando al robot", "intentos": 0,
                    "alarmas": [a for a in est.get("alarmas", []) if a.get("etapa") == "datos"]})
        _guardar_estado(ref, est)
    return jsonify({"ok": True})


@bp.post("/api/integracion/pedidos/<ref>/cancelar")
def adm_cancelar(ref):
    with _LOCK:
        est = leer_estado(ref)
        if not est:
            return jsonify({"error": "no existe"}), 404
        if est.get("estado") == "listo":
            return jsonify({"error": "ese pedido ya se generó"}), 409
        est["estado"], est["etapa"] = "cancelado", "cancelado desde la pantalla"
        _guardar_estado(ref, est)
        _limpiar_disenos(est)
    return jsonify({"ok": True})


# ══ LIMPIEZA Y ARRANQUE DEL ROBOT ══════════════════════════════════════════════════════════════
_ULTIMA_PURGA = [0.0]


def purgar(forzar=False):
    """Pasados `dias_guardado` días de terminado (listo, rechazado o cancelado): se sacan del molde
    los diseños internos de ese pedido y se borran su paquete y la copia local de los PDF. Quedan
    `estado.json` y `resultado.json` (el historial). Corre como mucho una vez por hora."""
    if not forzar and time.time() - _ULTIMA_PURGA[0] < 3600:
        return 0
    _ULTIMA_PURGA[0] = time.time()
    dias = max(1, int(_cfg().get("dias_guardado") or 30))
    n = 0
    for est in _pedidos():
        if est.get("estado") not in ("listo", "rechazado", "cancelado", "error") or est.get("purgado"):
            continue
        try:
            visto = time.mktime(time.strptime(est.get("actualizado"), "%Y-%m-%dT%H:%M:%S"))
        except Exception:
            continue
        if time.time() - visto < dias * 86400:
            continue
        ref = est["referencia"]
        _limpiar_disenos(est)
        for sub in ("archivos", "paquete.zip"):
            p = os.path.join(_dir_pedido(ref), sub)
            shutil.rmtree(p, ignore_errors=True) if os.path.isdir(p) else (os.path.exists(p) and os.remove(p))
        shutil.rmtree(os.path.join(_raiz(), "salida", ref), ignore_errors=True)
        est["purgado"] = _ahora()
        _escribir_json(os.path.join(_dir_pedido(ref), "estado.json"), est)      # sin tocar `actualizado`
        n += 1
    try:
        n += _purgar_plantillas(dias)
    except Exception as e:
        print(f"[externo] la limpieza de plantillas viejas falló: {e}", flush=True)
    return n


_ROBOT = {"proc": None, "motivo": ""}


def arrancar_robot(url, extra_env=None):
    """Mantiene vivo el robot (`node frontend/src/motor/robot/robot.mjs`) mientras viva el servidor:
    lo arranca y, si se cae, lo vuelve a levantar (con esperas cada vez más largas). Es un PROCESO
    aparte a propósito: lo pesado no corre adentro del servidor web. Su salida va a
    `logs/robot.log`. Sin Node instalado no arranca y la pantalla lo dice."""
    import subprocess
    guion = os.path.join(S.AQUI, "frontend", "src", "motor", "robot", "robot.mjs")
    node = shutil.which("node")
    if not node or not os.path.exists(guion):
        _ROBOT["motivo"] = "no está instalado Node.js en esta máquina" if not node else "falta el programa del robot"
        print(f"[externo] el robot no arranca: {_ROBOT['motivo']}", flush=True)
        return
    token = robot_token()

    def _vigilar():
        espera = 2
        while True:
            try:
                os.makedirs(os.path.join(S.AQUI, "logs"), exist_ok=True)
                salida = open(os.path.join(S.AQUI, "logs", "robot.log"), "ab")
                env = dict(os.environ, TIZADA_URL=url, TIZADA_ROBOT_TOKEN=token, TIZADA_DATOS=S.DATOS, **(extra_env or {}))
                t0 = time.time()
                p = subprocess.Popen([node, guion], cwd=S.AQUI, env=env, stdout=salida, stderr=subprocess.STDOUT,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                _ROBOT["proc"], _ROBOT["motivo"] = p, ""
                p.wait()
                salida.close()
                _ROBOT["motivo"] = f"se cerró (código {p.returncode}); se vuelve a levantar"
                espera = 2 if time.time() - t0 > 120 else min(espera * 2, 120)
            except Exception as e:
                _ROBOT["motivo"] = f"no se pudo arrancar: {e}"
                espera = min(espera * 2, 120)
            time.sleep(espera)

    threading.Thread(target=_vigilar, daemon=True, name="robot-integracion").start()
    import atexit
    atexit.register(lambda: _ROBOT["proc"] and _ROBOT["proc"].poll() is None and _ROBOT["proc"].terminate())


# Las rutas de esta pantalla que ESCRIBEN, con el permiso que piden (las suma `servidor.py` a su
# tabla `_API_SIN_MOLDE`: ninguna trabaja sobre «el molde activo»).
RUTAS_DE_PANTALLA = {
    "/api/integracion/llaves/crear": "config.editar",
    "/api/integracion/llaves/revocar": "config.editar",
    "/api/integracion/config": "config.editar",
    "/api/integracion/drive_cuenta": "config.editar",
    "/api/integracion/drive/conectar": "config.editar",
    "/api/integracion/drive/desconectar": "config.editar",
    "/api/integracion/pedidos/<ref>/reintentar": "config.editar",
    "/api/integracion/pedidos/<ref>/cancelar": "config.editar",
}
