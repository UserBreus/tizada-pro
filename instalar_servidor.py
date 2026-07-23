"""INSTALADOR PARA EL SERVIDOR. Se ejecuta EN EL SERVIDOR (no acá), con doble clic en INSTALAR.bat.

Hace TODO solo: Python, dependencias, Ghostscript, perfiles de color, la clave de sesión, el
arranque automático, el bloque de nginx y el chequeo final. Al terminar dice si quedó andando.

    py instalar_servidor.py              instala
    py instalar_servidor.py --simular    NO toca nada: dice paso por paso qué haría
    py instalar_servidor.py --sin-nginx  no toca la configuración de nginx (se hace a mano)

Pensado para que el usuario NO tenga que saber nada: cada paso avisa qué hace, y si algo falla
dice exactamente qué quedó a medias y cómo seguir. Nada de esto pisa `datos\\` ni `entrada\\`.
"""
import os, sys, re, shutil, socket, subprocess, secrets, time, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
SIMULAR = "--simular" in sys.argv
SIN_NGINX = "--sin-nginx" in sys.argv
PUERTO_PREF = 8050
RUTA_SUB = "/Tizadapro"
TAREA = "TIZADA PRO"

# Ghostscript oficial (Artifex). Solo se baja si NO está instalado.
GS_URL = ("https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/"
          "gs10012/gs10012w64.exe")
PY_URL = "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"

_pasos, _avisos = [], []


class _Tee:
    """Todo lo que sale por pantalla se guarda TAMBIÉN en instalacion_log.txt. La ventana se puede
    cerrar sin querer (le pasó al usuario: apretó una tecla y se cerró antes de leer nada); con el
    log siempre se puede saber después qué hizo y dónde se cortó."""

    def __init__(self, consola, archivo):
        self.consola, self.archivo = consola, archivo

    def write(self, txt):
        try:
            self.consola.write(txt)
        except Exception:
            pass                              # consola cp1252 rara: que NO tumbe la instalación
        try:
            self.archivo.write(txt); self.archivo.flush()
        except Exception:
            pass

    def flush(self):
        try:
            self.consola.flush()
        except Exception:
            pass


try:
    _log = open(os.path.join(AQUI, "instalacion_log.txt"), "w", encoding="utf-8", errors="replace")
    _log.write(f"INSTALACION DE TIZADA PRO — {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
               f"python: {sys.version}\ncarpeta: {AQUI}\n{'=' * 70}\n")
    sys.stdout = _Tee(sys.stdout, _log)
    sys.stderr = _Tee(sys.stderr, _log)
except Exception:
    pass


def paso(txt):
    print(f"\n>> {txt}")
    _pasos.append(txt)


def ok(txt):
    print(f"   OK  {txt}")


def aviso(txt):
    print(f"   [!] {txt}")
    _avisos.append(txt)


def correr(cmd, **kw):
    if SIMULAR:
        print(f"   (simulado) {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
        return subprocess.CompletedProcess(cmd, 0, "", "")
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def es_admin():
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def descargar(url, destino):
    """Baja un archivo probando TRES caminos. El primero (urllib) falla en servidores Windows
    recién hechos con `CERTIFICATE_VERIFY_FAILED`: Python no encuentra los certificados raíz
    porque la máquina nunca navegó (pasó de verdad en el servidor del usuario). PowerShell y
    `curl.exe` usan el almacén de certificados de Windows, que sí los sabe traer solos."""
    try:
        import ssl
        ctx = None
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            pass
        with urllib.request.urlopen(url, timeout=120, context=ctx) as r, open(destino, "wb") as fh:
            shutil.copyfileobj(r, fh)
        if os.path.getsize(destino) > 1000:
            return True
    except Exception as e:
        print(f"   (descarga directa no anduvo: {str(e)[:90]})")
    r = correr(["powershell", "-NoProfile", "-Command",
                "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; "
                f"Invoke-WebRequest -Uri '{url}' -OutFile '{destino}' -UseBasicParsing"])
    if os.path.exists(destino) and os.path.getsize(destino) > 1000:
        return True
    print(f"   (PowerShell tampoco: {(r.stderr or '')[:90]})")
    correr(["curl.exe", "-L", "-s", "-o", destino, url])
    return os.path.exists(destino) and os.path.getsize(destino) > 1000


def puerto_libre(p):
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", p)); return True
        except OSError:
            return False


# ── 1. Python y dependencias ────────────────────────────────────────────────
def asegurar_python():
    paso("Python")
    if sys.version_info >= (3, 10):
        ok(f"Python {sys.version.split()[0]} (el que está corriendo esto)")
        return sys.executable
    aviso("Python viejo; se instala el 3.12")
    exe = os.path.join(os.environ.get("TEMP", AQUI), "python-instalador.exe")
    if not SIMULAR:
        urllib.request.urlretrieve(PY_URL, exe)
        correr([exe, "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_pip=1"])
    return "py"


def instalar_dependencias(py):
    paso("Dependencias de Python")
    req = os.path.join(AQUI, "requirements.txt")
    r = correr([py if py != "py" else "py", "-m", "pip", "install", "-r", req])
    if r.returncode == 0:
        ok("instaladas (flask, pymupdf, pikepdf, pillow, waitress…)")
    else:
        aviso(f"pip falló: {(r.stderr or '')[-300:]}")


# ── 2. Ghostscript ──────────────────────────────────────────────────────────
def asegurar_ghostscript():
    paso("Ghostscript (lo usa el aplanado para el RIP)")
    for base in (r"C:\Program Files\gs", r"C:\Program Files (x86)\gs"):
        if os.path.isdir(base):
            for v in sorted(os.listdir(base), reverse=True):
                exe = os.path.join(base, v, "bin", "gswin64c.exe")
                if os.path.exists(exe):
                    ok(f"ya estaba: {exe}")
                    return exe
    print("   no está; se descarga el oficial de Artifex…")
    exe = os.path.join(os.environ.get("TEMP", AQUI), "gs-instalador.exe")
    if SIMULAR:
        print(f"   (simulado) bajar {GS_URL} e instalar en silencio")
        return None
    try:
        if not descargar(GS_URL, exe):
            raise RuntimeError("no se pudo descargar por ningún camino")
        correr([exe, "/S"])
        time.sleep(5)
        for base in (r"C:\Program Files\gs", r"C:\Program Files (x86)\gs"):
            if not os.path.isdir(base):
                continue
            for v in sorted(os.listdir(base), reverse=True):
                c = os.path.join(base, v, "bin", "gswin64c.exe")
                if os.path.exists(c):
                    ok(f"instalado: {c}")
                    return c
        raise RuntimeError("se instaló pero no aparece el ejecutable")
    except Exception as e:
        # NO es bloqueante: Ghostscript sólo se usa para unificar el modo de color cuando la hoja
        # trae contenido RGB. Con arte CMYK (el caso normal) la tizada sale igual.
        aviso(f"Ghostscript quedó sin instalar ({str(e)[:100]}). El sistema FUNCIONA igual; "
              "sólo hace falta si algún arte viene en RGB. Se puede instalar después "
              "desde ghostscript.com y volver a correr este instalador.")
    return None


# ── 3. Perfiles de color ────────────────────────────────────────────────────
def instalar_perfiles(destino_app):
    paso("Perfiles de color ICC (SIN esto el color sale distinto)")
    origen = os.path.join(AQUI, "perfiles_icc")
    adobe = r"C:\Program Files (x86)\Common Files\Adobe\Color\Profiles\Recommended"
    if os.path.isdir(adobe) and any(f.lower().endswith((".icc", ".icm")) for f in os.listdir(adobe)):
        ok("el servidor ya tiene los perfiles de Adobe instalados")
        return None
    if not os.path.isdir(origen):
        aviso("el paquete no trae los perfiles y el servidor no los tiene. "
              "Copiá los .icc del taller y apuntá TIZADA_PERFILES a esa carpeta.")
        return None
    dest = os.path.join(destino_app, "perfiles_icc")
    # Los perfiles VIENEN en el paquete, así que origen y destino son la MISMA carpeta: copiar
    # un archivo sobre sí mismo revienta con WinError 32 ("lo está usando otro proceso") y
    # tumbaba toda la instalación. Ya están donde tienen que estar: sólo se apuntan.
    if os.path.abspath(origen) == os.path.abspath(dest):
        ok(f"{len(os.listdir(origen))} perfiles listos en {dest}")
        return dest
    if not SIMULAR:
        os.makedirs(dest, exist_ok=True)
        for f in os.listdir(origen):
            shutil.copy2(os.path.join(origen, f), os.path.join(dest, f))
    ok(f"{len(os.listdir(origen))} perfiles copiados a {dest}")
    return dest


# ── 4. Configuración del servicio ───────────────────────────────────────────
def escribir_config(puerto, perfiles, gs):
    paso("Configuración del servidor (clave de sesión, memoria, rutas)")
    clave = secrets.token_hex(32)
    cfg = os.path.join(AQUI, "config_publicado.bat")
    lineas = [
        "@echo off",
        "REM  Generado por el instalador. La CLAVE no se cambia: si cambia, se cierra la sesion de todos.",
        f"set TIZADA_MODO=publicado",
        f"set TIZADA_SECRET={clave}",
        f"set PORT={puerto}",
        "set HOST=127.0.0.1",
        "REM  cada proceso de render pesa ~200 MB: con ~1 GB libre, 2 es lo recomendado",
        "set TIZADA_PROCESOS=2",
    ]
    if perfiles:
        lineas.append(f"set TIZADA_PERFILES={perfiles}")
    if gs:
        lineas.append(f"set TIZADA_GS={gs}")
    # CLAVE DE ACTUALIZACIÓN: viene dentro del paquete (la generó el taller). Con esto los dos
    # lados quedan con la misma llave y las actualizaciones son un botón, sin copiar ni pegar nada.
    tok = os.path.join(AQUI, "token_actualizacion.txt")
    if os.path.exists(tok):
        try:
            with open(tok, encoding="ascii") as fh:
                lineas.append(f"set TIZADA_TOKEN_ACT={fh.read().strip()}")
            print("   clave de actualización tomada del paquete (no hay que copiar nada)")
        except Exception as e:
            aviso(f"no se pudo leer la clave de actualización: {e}")
    else:
        aviso("el paquete no trae la clave de actualización: este servidor NO va a poder "
              "recibir actualizaciones automáticas (rearmá el paquete con --completo).")
    if SIMULAR:
        print(f"   (simulado) escribir {cfg} con una clave nueva")
    else:
        with open(cfg, "w", encoding="ascii") as fh:
            fh.write("\n".join(lineas) + "\n")
        ok(f"{cfg} (clave nueva generada)")
    # arranque = config + servidor
    arranque = os.path.join(AQUI, "arrancar.bat")
    if SIMULAR:
        print(f"   (simulado) escribir {arranque}")
    else:
        with open(arranque, "w", encoding="ascii") as fh:
            # la salida va a un archivo: corriendo como servicio no hay ventana donde mirar
            # `call` CON RUTA COMPLETA: si el entorno tiene NoDefaultCurrentDirectoryInExePath,
            # `call config_publicado.bat` no encuentra el archivo y el servidor arranca SIN su
            # configuración (sin clave, sin puerto). Pasó en las pruebas.
            fh.write("@echo off\r\ncd /d \"%~dp0\"\r\ncall \"%~dp0config_publicado.bat\"\r\n"
                     "echo ---- arranque %date% %time% >> servidor_log.txt\r\n"
                     "where py >nul 2>nul && (py servidor.py >> servidor_log.txt 2>&1) "
                     "|| (python servidor.py >> servidor_log.txt 2>&1)\r\n")
        ok(arranque)
    return arranque


def _tablas_del_schema():
    """Nombres de las tablas que crea `db/schema.sql` (en minúsculas). Se leen del archivo, no se
    escriben a mano: si mañana el esquema cambia, el seguro sigue siendo correcto."""
    try:
        with open(os.path.join(AQUI, "db", "schema.sql"), encoding="utf-8") as fh:
            sql = fh.read()
    except OSError:
        return set()
    return {m.group(1).lower() for m in
            re.finditer(r"(?im)^\s*CREATE\s+TABLE\s+\[?(?:dbo\]?\.\[?)?([A-Za-z_][A-Za-z0-9_]*)", sql)}


def _permiso_al_servicio(_db):
    """Le da acceso a la base SOLO a la cuenta con la que arranca el servicio (`SYSTEM`).

    Al instalar, esto corre como Administrador —que en SQL suele ser sysadmin— y anda. Pero
    cuando el servidor se reinicia, TIZADA PRO arranca como **SYSTEM** por la tarea programada,
    y esa cuenta normalmente NO tiene permiso → «login failed» y no se podría iniciar sesión.
    Se crea el login y se le da acceso **únicamente a la base TizadaPro**: no toca ninguna otra
    base del servidor (el usuario usa ese SQL para otras cosas)."""
    cuenta = r"NT AUTHORITY\SYSTEM"
    try:
        with _db.cursor() as cur:
            cur.execute(
                "IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = ?) "
                f"CREATE LOGIN [{cuenta}] FROM WINDOWS;", cuenta)
            cur.execute(
                "IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = ?) "
                f"CREATE USER [{cuenta}] FOR LOGIN [{cuenta}];", cuenta)
            cur.execute(f"ALTER ROLE db_owner ADD MEMBER [{cuenta}];")
        ok(f"permiso dado a {cuenta} SOLO sobre la base TizadaPro "
           "(es la cuenta con la que arranca solo el sistema)")
    except Exception as e:
        aviso(f"no se pudo dar permiso a {cuenta} sobre TizadaPro ({str(e)[:120]}). "
              "Va a andar ahora, pero si se reinicia el servidor puede fallar el inicio de "
              "sesión: en ese caso hay que darle acceso a esa cuenta desde SQL Management Studio.")


def preparar_base(cfg_path):
    """Deja la base de USUARIOS lista (es lo único que hoy vive en MSSQL: usuarios, roles y
    permisos). Sin esto la pantalla de login no puede validar a nadie y no se entra al sistema.

    Busca un SQL Server que responda, crea la base `TizadaPro`, aplica el esquema y crea el
    usuario `admin` con una contraseña al azar que se MUESTRA una sola vez. Todo idempotente:
    si ya estaba, no rompe nada. Si no hay SQL Server, avisa y sigue (el resto del sistema anda)."""
    paso("Base de datos de usuarios")
    if SIMULAR:
        print("   (simulado) buscar SQL Server, crear la base TizadaPro y el usuario admin")
        return
    sys.path.insert(0, AQUI)
    try:
        import pyodbc
    except Exception:
        aviso("falta el driver de SQL Server (pyodbc). Sin base no se puede iniciar sesión.")
        return
    candidatos = [os.environ.get("TIZADA_DB_SERVER"), r"localhost\SQLEXPRESS", "localhost",
                  r".\SQLEXPRESS", "(local)", r"localhost\MSSQLSERVER"]
    servidor = None
    for s in [c for c in candidatos if c]:
        os.environ["TIZADA_DB_SERVER"] = s
        try:
            import db as _db
            import importlib
            importlib.reload(_db)
            _db.existe_base()
            servidor = s
            break
        except Exception as e:
            print(f"   {s}: no ({str(e)[:70]})")
    if not servidor:
        aviso("no encontré un SQL Server donde crear la base de usuarios. El sistema queda "
              "andando pero NO se puede iniciar sesión. Instalá SQL Server Express (gratis) y "
              "volvé a correr este instalador.")
        return
    ok(f"SQL Server encontrado en {servidor}")
    import db as _db
    import auth as _auth
    print(f"   se trabaja SOLO sobre la base '{_db.DB_NAME}'. Ninguna otra base de este "
          "servidor se toca (ni se lee).")
    try:
        nueva = _db.crear_base()
        ok(f"base {_db.DB_NAME} {'creada' if nueva else 'ya existía'}")
        # SEGURO: este SQL Server tiene otros sistemas del usuario (stock, entre otros). Si
        # apareciera una base con nuestro nombre pero con tablas AJENAS, no es la nuestra:
        # se corta sin escribir una sola línea, en vez de mezclar tablas en la base de otro.
        if not nueva:
            propias = _tablas_del_schema()
            ajenas = [t for t in _db.tablas() if t.lower() not in propias]
            if ajenas:
                aviso(f"la base '{_db.DB_NAME}' YA EXISTE y tiene tablas que NO son de TIZADA PRO "
                      f"({', '.join(ajenas[:6])}…). NO se tocó absolutamente nada. "
                      "Si es de otro sistema, hay que darle otro nombre a la nuestra "
                      "(variable TIZADA_DB_NAME).")
                return
        _db.aplicar_schema()
        ok(f"tablas al día ({len(_db.tablas())} tablas)")
        _permiso_al_servicio(_db)
        _np, _nr, pw = _auth.bootstrap()
        if pw:
            print("\n   " + "*" * 62)
            print("   *  USUARIO PARA ENTRAR AL SISTEMA — ANOTALO, SE MUESTRA UNA SOLA VEZ")
            print("   *")
            print("   *      usuario:    admin")
            print(f"   *      contraseña: {pw}")
            print("   *")
            print("   *  (también quedó en instalacion_log.txt, al lado de este instalador)")
            print("   " + "*" * 62 + "\n")
        else:
            ok("el usuario admin ya existía (se entra con la contraseña de siempre)")
    except Exception as e:
        aviso(f"no se pudo preparar la base: {str(e)[:200]}")
        return
    # dejar el servidor de base anotado en la config, para el próximo arranque
    try:
        with open(cfg_path, "a", encoding="ascii") as fh:
            fh.write(f"set TIZADA_DB_SERVER={servidor}\n")
        ok("servidor de base anotado en la configuración")
    except Exception:
        pass


# Tarea de Windows definida por XML (con `schtasks /create /sc onstart` no se pueden pedir estas
# tres cosas, que son las que hacen la diferencia entre "un programa abierto" y "un servicio"):
#   • SIN VENTANA (`Hidden` + cuenta SYSTEM) → nadie la puede cerrar sin querer. PASÓ: se cerró la
#     consola y el sistema quedó caído, dando 502 y "Unexpected token '<'" en la pantalla.
#   • VIGILANCIA cada 5 minutos (`Repetition` + `IgnoreNew`): si el programa se cayó, vuelve solo;
#     si está andando, no hace nada.
#   • REINTENTO ante fallo y sin límite de tiempo de ejecución (si no, Windows lo mata a los 3 días).
TAREA_XML = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>TIZADA PRO - servidor publicado</Description></RegistrationInfo>
  <Triggers>
    <BootTrigger><Enabled>true</Enabled></BootTrigger>
    <TimeTrigger>
      <StartBoundary>2020-01-01T00:00:00</StartBoundary><Enabled>true</Enabled>
      <Repetition><Interval>PT5M</Interval><StopAtDurationEnd>false</StopAtDurationEnd></Repetition>
    </TimeTrigger>
  </Triggers>
  <Principals><Principal id="Author">
    <UserId>S-1-5-18</UserId><RunLevel>HighestAvailable</RunLevel>
  </Principal></Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Hidden>true</Hidden><Enabled>true</Enabled>
    <RestartOnFailure><Interval>PT1M</Interval><Count>99</Count></RestartOnFailure>
  </Settings>
  <Actions Context="Author"><Exec>
    <Command>cmd.exe</Command>
    <Arguments>/c "{arranque}"</Arguments>
    <WorkingDirectory>{carpeta}</WorkingDirectory>
  </Exec></Actions>
</Task>
"""


def crear_tarea(arranque):
    paso("Servicio (que ande solo, sin ventana, y se levante si se cae)")
    xml = os.path.join(AQUI, "_tarea.xml")
    if SIMULAR:
        print("   (simulado) crear la tarea desde XML: sin ventana + vigilancia cada 5 min")
        return
    with open(xml, "w", encoding="utf-16") as fh:
        fh.write(TAREA_XML.format(arranque=arranque, carpeta=AQUI))
    correr(["schtasks", "/delete", "/tn", TAREA, "/f"])
    r = correr(["schtasks", "/create", "/tn", TAREA, "/xml", xml, "/f"])
    try:
        os.remove(xml)
    except OSError:
        pass
    if r.returncode == 0:
        ok("servicio creado: arranca con el servidor, SIN ventana, y si se cayera "
           "vuelve solo en menos de 5 minutos")
    else:
        aviso(f"no se pudo crear el servicio: {(r.stderr or r.stdout or '')[:200]}")


def arrancar(puerto):
    """Lo arranca COMO SERVICIO (por la tarea), no como una ventana suelta: así queda desde el
    minuto cero igual que después de un reinicio, y no hay ninguna consola que cerrar sin querer."""
    paso("Arrancando TIZADA PRO")
    if SIMULAR:
        print("   (simulado) schtasks /run")
        return
    if not puerto_libre(puerto):
        print("   ya había una instancia abierta: se cierra para dejar la del servicio")
        correr(["schtasks", "/end", "/tn", TAREA])
        for _ in range(10):
            if puerto_libre(puerto):
                break
            time.sleep(1)
    correr(["schtasks", "/run", "/tn", TAREA])
    for _ in range(60):
        time.sleep(1)
        if not puerto_libre(puerto):
            ok(f"escuchando en 127.0.0.1:{puerto} (sin ventana, como servicio)")
            return
    aviso("no llegó a levantar en 60 s. Mirá servidor_log.txt, al lado de este instalador.")


# ── 5. nginx ────────────────────────────────────────────────────────────────
BLOQUE = """
    # --- TIZADA PRO (agregado por el instalador) ---
    location {sub}/ {{
        proxy_pass         http://127.0.0.1:{puerto}/;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        client_max_body_size 200m;
        proxy_read_timeout   600s;
        proxy_send_timeout   600s;
    }}
    location = {sub} {{ return 301 {sub}/; }}
    # --- fin TIZADA PRO ---
"""


def ubicar_nginx():
    """Devuelve (exe, conf) del nginx que está corriendo, o (None, None)."""
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "(Get-Process nginx -ErrorAction SilentlyContinue | "
                        "Select-Object -First 1).Path"], capture_output=True, text=True)
    exe = (r.stdout or "").strip()
    cands = [exe] if exe else []
    cands += [r"C:\nginx\nginx.exe", r"C:\Program Files\nginx\nginx.exe"]
    for c in cands:
        if c and os.path.exists(c):
            conf = os.path.join(os.path.dirname(c), "conf", "nginx.conf")
            return c, (conf if os.path.exists(conf) else None)
    return None, None


def insertar_en_conf(texto, puerto):
    """Mete el bloque dentro del PRIMER `server {` que atienda el sitio. Devuelve el texto nuevo
    o None si no se pudo (mejor no tocar nada que romper el nginx del otro sistema)."""
    if "TIZADA PRO (agregado por el instalador)" in texto:
        return texto            # ya estaba: no duplicar
    m = re.search(r"\bserver\s*\{", texto)
    if not m:
        return None
    return texto[:m.end()] + BLOQUE.format(sub=RUTA_SUB, puerto=puerto) + texto[m.end():]


def _confs_candidatos(conf):
    """nginx.conf + los archivos que incluya (`include sites-enabled/*.conf`). El `server {` del
    sitio suele estar en el principal, pero si está en un incluido hay que encontrarlo igual."""
    import glob
    salida, base = [conf], os.path.dirname(conf)
    try:
        with open(conf, encoding="utf-8", errors="replace") as fh:
            texto = fh.read()
        for m in re.finditer(r"^\s*include\s+([^;]+);", texto, re.M):
            patron = m.group(1).strip().strip('"')
            if not os.path.isabs(patron):
                patron = os.path.join(base, patron.replace("/", os.sep))
            salida += [p for p in glob.glob(patron) if p.lower().endswith(".conf")]
    except OSError:
        pass
    return salida


def configurar_nginx(puerto):
    paso("nginx (para que se vea en el dominio, en " + RUTA_SUB + ")")
    exe, conf = ubicar_nginx()
    if not exe or not conf:
        aviso("no encontré nginx.conf. Agregá el bloque a mano (está en PLAN_PUBLICACION.md).")
        return
    # se elige el archivo donde REALMENTE está el sitio (el que tiene un `server {`)
    elegido, texto = None, ""
    for c in _confs_candidatos(conf):
        try:
            with open(c, encoding="utf-8", errors="replace") as fh:
                t = fh.read()
        except OSError:
            continue
        if re.search(r"\bserver\s*\{", t):
            elegido, texto = c, t
            if "location /" in t:      # el que sirve el sitio: mejor candidato todavía
                break
    if not elegido:
        aviso(f"no encontré ningún `server {{}}` en {conf} ni en sus includes: agregalo a mano.")
        return
    conf = elegido
    print(f"   archivo: {conf}")
    nuevo = insertar_en_conf(texto, puerto)
    if nuevo is None:
        aviso(f"no pude ubicar dónde insertar en {conf}: hacelo a mano.")
        return
    if nuevo == texto:
        ok("el bloque ya estaba puesto")
        return
    resp = conf + ".antes-de-tizada"
    if SIMULAR:
        print(f"   (simulado) respaldo {resp} + insertar bloque + nginx -t + reload")
        return
    shutil.copy2(conf, resp)                       # SIEMPRE respaldo antes de tocar
    with open(conf, "w", encoding="utf-8") as fh:
        fh.write(nuevo)
    r = correr([exe, "-t"], cwd=os.path.dirname(exe))
    if r.returncode != 0:
        shutil.copy2(resp, conf)                   # se rompió: se deja como estaba
        aviso(f"la config no valida; se restauró el original. Detalle: {(r.stderr or '')[:200]}")
        return
    correr([exe, "-s", "reload"], cwd=os.path.dirname(exe))
    ok(f"nginx configurado y recargado (respaldo en {resp})")


# ── 6. Chequeo final ────────────────────────────────────────────────────────
def chequear(puerto):
    paso("Chequeo final")
    if SIMULAR:
        print("   (simulado) GET /api/salud")
        return
    import json
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/salud", timeout=30) as r:
            d = json.loads(r.read())
    except Exception as e:
        aviso(f"no respondió el chequeo de salud: {str(e)[:150]}")
        return
    for nombre, c in (d.get("chequeos") or {}).items():
        print(f"   {'OK ' if c.get('ok') else 'MAL'} {nombre}: {c.get('detalle')}")
    if d.get("ok"):
        ok(f"TIZADA PRO {d.get('version')} andando (modo {d.get('modo')}, "
           f"{d.get('procesos_render')} procesos de render)")
    else:
        aviso(f"falla en: {', '.join(d.get('fallas') or [])}")


def main():
    print("=" * 70)
    print("  INSTALADOR DE TIZADA PRO EN EL SERVIDOR" + ("   [SIMULACIÓN]" if SIMULAR else ""))
    print("=" * 70)
    if os.name != "nt":
        raise SystemExit("Esto se corre en el SERVIDOR (Windows).")
    if not es_admin() and not SIMULAR:
        raise SystemExit("\n[!] Hacé clic DERECHO en INSTALAR.bat → 'Ejecutar como administrador'.\n"
                         "    Hace falta para nginx y para que arranque solo.")
    puerto = PUERTO_PREF
    while not puerto_libre(puerto) and puerto < PUERTO_PREF + 10:
        puerto += 1
    if puerto != PUERTO_PREF:
        aviso(f"el puerto {PUERTO_PREF} estaba ocupado; se usa el {puerto}")

    py = asegurar_python()
    instalar_dependencias(py)
    gs = asegurar_ghostscript()
    perfiles = instalar_perfiles(AQUI)
    arranque = escribir_config(puerto, perfiles, gs)
    preparar_base(os.path.join(AQUI, "config_publicado.bat"))   # antes de arrancar: el server la lee
    crear_tarea(arranque)
    arrancar(puerto)
    if not SIN_NGINX:
        configurar_nginx(puerto)
    chequear(puerto)

    print("\n" + "=" * 70)
    if _avisos:
        print("  TERMINÓ, PERO HAY COSAS PARA MIRAR:")
        for a in _avisos:
            print(f"   - {a}")
    else:
        print("  LISTO. No hubo ningún problema.")
    print(f"\n  Probalo en:  https://<tu-dominio>{RUTA_SUB}/")
    print(f"  Estado:      https://<tu-dominio>{RUTA_SUB}/api/salud")
    print("=" * 70)
    if not SIMULAR:
        input("\n  (Enter para cerrar)")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        # Cualquier error inesperado tiene que quedar A LA VISTA y en el log, no cerrar la ventana
        # en silencio: el usuario no tiene cómo saber qué pasó.
        import traceback
        print("\n" + "=" * 70)
        print("  SE CORTÓ POR UN ERROR INESPERADO:\n")
        traceback.print_exc()
        print("\n  Mandá el archivo instalacion_log.txt a quien te ayuda.")
        print("=" * 70)
        if "--simular" not in sys.argv:
            input("\n  (Enter para cerrar)")
