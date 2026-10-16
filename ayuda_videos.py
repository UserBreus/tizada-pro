"""AYUDA EN VIDEO (MAPA 689) — los tutoriales viven en una carpeta de Google Drive y se ven en el
reproductor propio de la pantalla (`frontend/src/ayudaVideos.jsx`).

Pedido del usuario (2026-10-12): «quitá la ayuda paso a paso; guardá los videos tutoriales en esta
carpeta de Drive, tomalos y ponelos en nuestro propio reproductor, moderno, con velocidades, que
funcione rápido».

CÓMO FUNCIONA (sin cuentas ni claves: la carpeta es «cualquiera con el enlace puede ver»):
  · La LISTA sale de la vista pública de la carpeta (`embeddedfolderview`): id y nombre de cada
    archivo; una subcarpeta es una SECCIÓN (un nivel). Se guarda 5 minutos en memoria.
  · Cada VIDEO se baja UNA vez a `datos/cache_ayuda/` (por su id de Drive: si se sube una versión
    nueva, es otro archivo con otro id) y se sirve desde el disco del servidor con `Range` → el
    reproductor adelanta y atrasa al instante. Apenas se pide la lista, los que falten se bajan de
    fondo de a uno, así cuando alguien abre un video ya está.
  · Las MINIATURAS, lo mismo (`drive.google.com/thumbnail`).
Para cambiar de carpeta: `TIZADA_AYUDA_DRIVE` (el id de la carpeta).
"""
import os
import shutil
import subprocess
import re
import html
import json
import time
import threading
import urllib.request

from flask import Blueprint, jsonify, send_file, request

bp = Blueprint("ayuda_videos", __name__)

CARPETA = os.environ.get("TIZADA_AYUDA_DRIVE") or "1BD21AeE2iRhZoLAc9QxP218VaJMFvxTc"
_UA = "Mozilla/5.0 (TIZADA PRO ayuda)"
_EXT_VIDEO = (".mp4", ".m4v", ".webm", ".mov")
_EXT_IMG = (".jpg", ".jpeg", ".png", ".webp")
_LISTA_TTL = 300

_cache_dir = None
_lock = threading.Lock()
_lista = {"t": 0.0, "datos": None}
_bajando = {}          # id → {"pct": 0..100, "error": str|None}
_activos = set()       # ids que se están bajando AHORA (uno solo por id: si no, dos escriben el mismo .tmp)
_cola = []             # ids para bajar de fondo
_hilo = {"vivo": False}


def configurar(datos_dir):
    """La carpeta de caché (adentro de `datos/`: es lo único que el servidor publicado puede escribir)."""
    global _cache_dir
    _cache_dir = os.path.join(datos_dir, "cache_ayuda")
    os.makedirs(_cache_dir, exist_ok=True)


def _get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    return urllib.request.urlopen(req, timeout=timeout)


def _entradas(carpeta_id):
    """[(id, nombre, es_carpeta)] de la vista pública de una carpeta de Drive."""
    with _get(f"https://drive.google.com/embeddedfolderview?id={carpeta_id}#list", timeout=30) as r:
        txt = r.read().decode("utf-8", "replace")
    out = []
    for m in re.finditer(r'<div class="flip-entry" id="entry-([\w-]+)".*?<a href="([^"]+)".*?'
                         r'<div class="flip-entry-title">(.*?)</div>', txt, re.S):
        fid, href, nombre = m.group(1), m.group(2), html.unescape(m.group(3)).strip()
        out.append((fid, nombre, "/folders/" in href))
    return out


def _orden_natural(s):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", s)]


def _titulo(nombre):
    base = re.sub(r"\.(mp4|m4v|webm|mov)$", "", nombre, flags=re.I)
    return re.sub(r"^\d+\s*[-._)]\s*", "", base).strip() or base       # «01 - Pedido» → «Pedido» (el número sólo ordena)


def _ruta(fid, ext=".mp4"):
    return os.path.join(_cache_dir, re.sub(r"[^\w-]", "", fid) + ext)


def _base(nombre):
    return os.path.splitext(nombre)[0].strip().lower()


def _imagenes(entradas):
    return {_base(n): i for i, n, c in entradas if not c and n.lower().endswith(_EXT_IMG)}


def _videos_de(entradas, minis):
    """[(id, nombre, id_miniatura|None)] de los archivos de una carpeta. La miniatura es una imagen con el
    MISMO nombre que el video («03 - Pedido con base.jpg»), en la subcarpeta «miniaturas» de la carpeta
    principal (así en Drive no parecen videos repetidos) o al lado del video. Hace falta porque la de Drive
    es el primer cuadro y nuestros videos arrancan en negro: salían todas iguales."""
    junto = _imagenes(entradas)
    return [(i, n, junto.get(_base(n)) or minis.get(_base(n)))
            for i, n, c in entradas if not c and n.lower().endswith(_EXT_VIDEO)]


def listar(forzar=False):
    """{carpeta, secciones: [{nombre, videos: [{id, titulo, archivo, mini, listo}]}]}."""
    with _lock:
        if not forzar and _lista["datos"] and time.time() - _lista["t"] < _LISTA_TTL:
            datos = _lista["datos"]
        else:
            datos = None
    if datos is None:
        secciones = []
        raiz = _entradas(CARPETA)
        minis = {}
        for fid, nombre, es_carpeta in raiz:
            if es_carpeta and nombre.strip().lower() == "miniaturas":
                minis = _imagenes(_entradas(fid))     # no es una sección: sólo las imágenes de los videos
        for fid, nombre, es_carpeta in raiz:
            if es_carpeta and nombre.strip().lower() != "miniaturas":
                vids = _videos_de(_entradas(fid), minis)
                if vids:
                    secciones.append({"nombre": nombre, "videos": sorted(vids, key=lambda x: _orden_natural(x[1]))})
        sueltos = _videos_de(raiz, minis)
        if sueltos:
            secciones.insert(0, {"nombre": "Tutoriales", "videos": sorted(sueltos, key=lambda x: _orden_natural(x[1]))})
        secciones.sort(key=lambda s: (s["nombre"] != "Tutoriales", _orden_natural(s["nombre"])))
        datos = {"carpeta": f"https://drive.google.com/drive/folders/{CARPETA}",
                 "secciones": [{"nombre": s["nombre"],
                                "videos": [{"id": i, "titulo": _titulo(n), "archivo": n, "mini": m}
                                           for i, n, m in s["videos"]]}
                               for s in secciones]}
        with _lock:
            _lista.update(t=time.time(), datos=datos)
        _podar(datos)
    # marca cuáles ya están en el disco y encola los que faltan (de fondo, de a uno)
    for s in datos["secciones"]:
        for v in s["videos"]:
            v["listo"] = os.path.exists(_ruta(v["id"]))
            if not v["listo"]:
                _encolar(v["id"])
    return datos


def _podar(datos):
    """Un video que se SACÓ de la carpeta de Drive se va también del caché del servidor (si no, sus 50 MB
    quedan para siempre y el que lo tenía abierto lo seguiría viendo). Sólo con una lista que trajo algo:
    una carpeta que vuelve vacía por un problema de Drive no tiene que borrar todo el caché."""
    vivos = {v[k] for s in datos["secciones"] for v in s["videos"] for k in ("id", "mini") if v.get(k)}
    if not vivos:
        return
    with _lock:
        ocupados = set(_activos) | set(_cola)
    for nombre in os.listdir(_cache_dir):
        fid = nombre.split(".", 1)[0]
        if fid in vivos or fid in ocupados:
            continue
        try:
            os.remove(os.path.join(_cache_dir, nombre))
            print(f"[ayuda] fuera del caché (ya no está en la carpeta): {nombre}", flush=True)
        except OSError:
            pass


def _encolar(fid):
    with _lock:
        if fid in _cola or fid in _activos or (_bajando.get(fid) or {}).get("error"):
            return
        _cola.append(fid)
        if _hilo["vivo"]:
            return
        _hilo["vivo"] = True
    threading.Thread(target=_trabajar, daemon=True, name="ayuda-videos").start()


def _trabajar():
    while True:
        with _lock:
            if not _cola:
                _hilo["vivo"] = False
                return
            fid = _cola.pop(0)
        _bajar(fid)


def _bajar(fid):
    """Baja un video de Drive al disco (.tmp + os.replace: nunca queda uno a medias con el nombre bueno)."""
    dest = _ruta(fid)
    with _lock:
        if os.path.exists(dest) or fid in _activos:
            return
        _activos.add(fid)
        _bajando[fid] = {"pct": 0, "error": None}
    tmp = dest + ".tmp"
    try:
        url = f"https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t"
        with _get(url, timeout=120) as r, open(tmp, "wb") as fh:
            total = int(r.headers.get("Content-Length") or 0)
            tipo = r.headers.get("Content-Type") or ""
            if "text/html" in tipo:
                raise RuntimeError("Drive no entregó el video (¿la carpeta está compartida con «cualquiera con el enlace»?)")
            hecho = 0
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                fh.write(b)
                hecho += len(b)
                if total:
                    _bajando[fid]["pct"] = min(99, int(hecho * 100 / total))
        if os.path.getsize(tmp) < 1024:
            raise RuntimeError("el archivo bajado está vacío")
        os.replace(tmp, dest)
        _cuadro_del_video(fid)
        with _lock:
            _bajando.pop(fid, None)
    except Exception as e:
        try:
            os.remove(tmp)
        except OSError:
            pass
        with _lock:
            _bajando[fid] = {"pct": 0, "error": _en_castellano(e)}
    finally:
        with _lock:
            _activos.discard(fid)


def _en_castellano(e):
    """La pantalla sólo muestra castellano: los errores de urllib vienen en inglés («HTTP Error 404: Not Found»).
    El detalle técnico queda en la consola del servidor para quien lo investigue."""
    print(f"[ayuda] {type(e).__name__}: {e}", flush=True)
    if isinstance(e, RuntimeError):
        return str(e)[:200]                           # los nuestros ya están escritos en castellano
    cod = getattr(e, "code", None)
    if cod in (403, 404):
        return "Drive no encontró el video (¿lo borraron o la carpeta dejó de estar compartida?)"
    if cod:
        return f"Drive respondió con un error ({cod}). Probá de nuevo en un rato."
    if isinstance(e, (TimeoutError, OSError)):
        return "No se pudo conectar con Drive. Revisá la conexión a internet."
    return "No se pudo bajar el video de Drive."


@bp.get("/api/ayuda/videos")
def api_videos():
    """Los videos de la carpeta de Drive agrupados por sección (subcarpeta). `?recargar=1` relee Drive sin esperar los 5 min."""
    try:
        return jsonify(listar(forzar=request.args.get("recargar") == "1"))
    except Exception as e:
        return jsonify({"error": "No se pudo leer la carpeta de tutoriales de Drive: " + _en_castellano(e)}), 502


@bp.get("/api/ayuda/video/<fid>/estado")
def api_estado(fid):
    """¿Ya está bajado al servidor? {listo, pct}. Si no, lo pide a Drive adelante de la cola de fondo."""
    if os.path.exists(_ruta(fid)):
        return jsonify({"listo": True, "pct": 100})
    with _lock:
        b = dict(_bajando.get(fid) or {})
        activo = fid in _activos
    if b.get("error") and not activo:
        with _lock:
            _bajando.pop(fid, None)          # el próximo pedido lo vuelve a intentar
        return jsonify({"listo": False, "error": b["error"]}), 502
    if not activo:
        # lo pidió una persona: pasa adelante de la cola de fondo
        with _lock:
            if fid in _cola:
                _cola.remove(fid)
        threading.Thread(target=_bajar, args=(fid,), daemon=True).start()
    return jsonify({"listo": False, "pct": b.get("pct", 0)})


@bp.get("/api/ayuda/video/<fid>")
def api_video(fid):
    """El .mp4 desde el caché del servidor, con Range (para adelantar sin bajarlo entero). 409 si todavía no bajó."""
    ruta = _ruta(fid)
    if not os.path.exists(ruta):
        return jsonify({"error": "todavía no está listo"}), 409
    # `conditional=True` → Range: el reproductor salta a cualquier punto sin bajar todo
    r = send_file(ruta, mimetype="video/mp4", conditional=True, max_age=86400)
    r.headers["Cache-Control"] = "private, max-age=86400, immutable"
    return r


def _cuadro_del_video(fid):
    """Con ffmpeg en el servidor (opcional: el publicado puede no tenerlo), un cuadro de adentro del video
    —al 30 %, ya con la pantalla armada— como miniatura. Sin ffmpeg no pasa nada: queda la de Drive."""
    ff, fp = shutil.which("ffmpeg"), shutil.which("ffprobe")
    dest = _ruta(fid, ".cuadro.jpg")
    if not ff or not fp or os.path.exists(dest):
        return
    try:
        dur = float(subprocess.run([fp, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    _ruta(fid)], capture_output=True, text=True, timeout=30).stdout.strip() or 0)
        tmp = dest + ".tmp.jpg"
        subprocess.run([ff, "-v", "error", "-y", "-ss", f"{max(1.0, dur * 0.3):.2f}", "-i", _ruta(fid),
                        "-frames:v", "1", "-vf", "scale=640:-2", "-q:v", "4", tmp],
                       capture_output=True, timeout=60, check=True)
        if os.path.getsize(tmp) > 1024:
            os.replace(tmp, dest)
    except Exception as e:
        print(f"[ayuda] miniatura de {fid}: {type(e).__name__}: {e}", flush=True)


def _bajar_a(url, dest):
    with _get(url, timeout=30) as r:
        if "image" not in (r.headers.get("Content-Type") or ""):
            raise RuntimeError("no es una imagen")
        datos = r.read()
    with open(dest + ".tmp", "wb") as fh:
        fh.write(datos)
    os.replace(dest + ".tmp", dest)


def _mini_de(fid):
    for s in (_lista["datos"] or {}).get("secciones", []):
        for v in s["videos"]:
            if v["id"] == fid:
                return v.get("mini")
    return None


def _servir_imagen(ruta, fija):
    with open(ruta, "rb") as fh:
        cab = fh.read(12)
    tipo = "image/png" if cab.startswith(b"\x89PNG") else "image/webp" if cab[8:12] == b"WEBP" else "image/jpeg"
    r = send_file(ruta, mimetype=tipo, conditional=True, max_age=86400)
    # la de Drive es provisoria (puede llegar la del video o una subida a mano): que el navegador la pida de nuevo
    r.headers["Cache-Control"] = "private, max-age=86400, immutable" if fija else "private, max-age=600"
    return r


@bp.get("/api/ayuda/miniatura/<fid>")
def api_miniatura(fid):
    """La miniatura del video: la imagen con su mismo nombre en la carpeta › un cuadro de adentro del video
    (si el servidor tiene ffmpeg) › la que arma Drive. Cacheadas en el servidor."""
    mini = _mini_de(fid)
    if mini:
        ruta = _ruta(mini, ".mini")              # por el id de la IMAGEN: si la cambian en Drive, cambia
        try:
            if not os.path.exists(ruta):
                _bajar_a(f"https://drive.usercontent.google.com/download?id={mini}&export=download&confirm=t", ruta)
            return _servir_imagen(ruta, True)
        except Exception as e:
            print(f"[ayuda] miniatura subida {mini}: {type(e).__name__}: {e}", flush=True)
    if os.path.exists(_ruta(fid)):
        _cuadro_del_video(fid)
    if os.path.exists(_ruta(fid, ".cuadro.jpg")):
        return _servir_imagen(_ruta(fid, ".cuadro.jpg"), True)
    ruta = _ruta(fid, ".jpg")
    if not os.path.exists(ruta):
        try:
            _bajar_a(f"https://drive.google.com/thumbnail?id={fid}&sz=w640", ruta)
        except Exception:
            return ("", 404)
    return _servir_imagen(ruta, False)
