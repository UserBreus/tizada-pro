// USER PRO para CorelDRAW — EL PUENTE entre el navegador y Corel (el equivalente de `puente.js` de
// Illustrator). Corre en segundo plano en la PC del taller, con un ícono junto al reloj.
//
// Escucha SOLO en 127.0.0.1:47851 (esta PC; nada de afuera llega). Mismo protocolo que el puente de
// Illustrator (47850), así la web usa el mismo código:
//   GET  /estado     → {app:'TIZADA PRO', programa:'corel', version, corel, corel_abierto, ultima, log, contacto, ahora, sistema}
//   POST /plantilla  → el plan (JSON) → {ok, mesas, metodo, ms, archivo, carpeta, textosFallidos} o 422 {ok:false, error}
// CORS con el origen que pregunta y `Access-Control-Allow-Private-Network` (Chrome lo pide para que
// una página de internet hable con 127.0.0.1). NO acepta cabeceras propias (regla del puente de
// Illustrator: una cabecera de más rompe el pedido previo de CORS).
//
// 🔴 SERVIDOR HTTP PROPIO SOBRE TcpListener (no HttpListener): HttpListener usa http.sys y en
// muchas PC pide permisos de administrador para escuchar; un socket en 127.0.0.1 no.
// C# 5 (el compilador de Windows): nada de `$"…"`, `?.` ni `=>` en propiedades.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace UserPro
{
    static class Puente
    {
        public const int PUERTO = 47851;
        const int TOPE_CUERPO = 80 * 1024 * 1024;
        static readonly object candado = new object();
        static readonly List<Dictionary<string, object>> log = new List<Dictionary<string, object>>();
        static Dictionary<string, object> ultima;
        static Dictionary<string, object> contacto;
        static NotifyIcon icono;
        static SynchronizationContext ui;

        static long Ahora() { return (long)(DateTime.UtcNow - new DateTime(1970, 1, 1)).TotalMilliseconds; }

        static void Anotar(string texto)
        {
            lock (candado)
            {
                Dictionary<string, object> e = new Dictionary<string, object>();
                e["t"] = Ahora(); e["texto"] = texto;
                log.Insert(0, e);
                if (log.Count > 30) log.RemoveRange(30, log.Count - 30);
            }
        }

        static JavaScriptSerializer Json()
        {
            JavaScriptSerializer j = new JavaScriptSerializer();
            j.MaxJsonLength = int.MaxValue;
            j.RecursionLimit = 256;
            return j;
        }

        // ── la RAM y el procesador de esta PC (lo muestra el Monitor de USER PRO) ─────────────────
        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
        class MEMORYSTATUSEX
        {
            public uint dwLength = (uint)Marshal.SizeOf(typeof(MEMORYSTATUSEX));
            public uint dwMemoryLoad; public ulong ullTotalPhys, ullAvailPhys, ullTotalPageFile, ullAvailPageFile, ullTotalVirtual, ullAvailVirtual, ullAvailExtendedVirtual;
        }
        [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        static extern bool GlobalMemoryStatusEx([In, Out] MEMORYSTATUSEX m);
        [DllImport("kernel32.dll")]
        static extern bool GetSystemTimes(out long idle, out long kernel, out long user);
        static long cpuOcupAnt = -1, cpuTotAnt = -1;

        static Dictionary<string, object> Sistema()
        {
            Dictionary<string, object> s = new Dictionary<string, object>();
            s["nucleos"] = Environment.ProcessorCount;
            try
            {
                long idle, kernel, user;
                if (GetSystemTimes(out idle, out kernel, out user))
                {
                    long total = kernel + user, ocup = total - idle;      // kernel incluye el ocioso
                    object pct = null;
                    if (cpuTotAnt > 0 && total > cpuTotAnt) pct = Math.Round(100.0 * (ocup - cpuOcupAnt) / (total - cpuTotAnt), 1);
                    cpuOcupAnt = ocup; cpuTotAnt = total;
                    s["cpu_pct"] = pct;
                }
            }
            catch { }
            try
            {
                MEMORYSTATUSEX m = new MEMORYSTATUSEX();
                if (GlobalMemoryStatusEx(m)) { s["ram_total_mb"] = (long)(m.ullTotalPhys / 1048576); s["ram_libre_mb"] = (long)(m.ullAvailPhys / 1048576); }
            }
            catch { }
            return s;
        }

        static Dictionary<string, object> Estado()
        {
            int mayor;
            string corel = ArmarCorel.Instalado(out mayor);
            Dictionary<string, object> d = new Dictionary<string, object>();
            d["app"] = "TIZADA PRO";
            d["programa"] = "corel";
            d["version"] = Version.Texto;
            d["corel"] = corel ?? "";
            d["corel_version"] = mayor;
            d["corel_abierto"] = Process.GetProcessesByName("CorelDRW").Length > 0;
            lock (candado)
            {
                d["ultima"] = ultima;
                d["log"] = log.ToArray();
                d["contacto"] = contacto;
            }
            d["ahora"] = Ahora();
            d["sistema"] = Sistema();
            return d;
        }

        // ── armar: de a una plantilla por vez (Corel arma un documento por vez) ─────────────────────
        static readonly object unaPorVez = new object();

        static Dictionary<string, object> Plantilla(string cuerpo)
        {
            object crudo;
            try { crudo = Json().DeserializeObject(cuerpo); }
            catch { throw new ArgumentException("el plan no es JSON"); }
            Plan plan = Plan.Sanear(crudo);
            lock (unaPorVez)
            {
                try { plan.GuardarEn = ArmarCorel.RutaParaGuardar(plan.Archivo); } catch { plan.GuardarEn = null; }
                Stopwatch sw = Stopwatch.StartNew();
                ResultadoArmado r;
                try { r = HiloCorel.Hacer(delegate () { return ArmarCorel.Armar(plan); }); }
                catch (Exception e)
                {
                    string msg = Mensaje(e);
                    Anotar("No se pudo armar «" + plan.Titulo + "»: " + msg);
                    throw new Exception(msg);
                }
                sw.Stop();
                Dictionary<string, object> res = new Dictionary<string, object>();
                res["ok"] = true;
                res["mesas"] = r.Mesas;
                res["metodo"] = r.Metodo;
                res["ms"] = sw.ElapsedMilliseconds;
                res["textosFallidos"] = r.TextosFallidos;
                res["espacioUnico"] = r.EspacioUnico;
                if (r.Guardado && plan.GuardarEn != null) { res["archivo"] = Path.GetFileName(plan.GuardarEn); res["carpeta"] = Path.GetDirectoryName(plan.GuardarEn); }
                lock (candado)
                {
                    ultima = new Dictionary<string, object>();
                    ultima["t"] = Ahora(); ultima["titulo"] = plan.Titulo; ultima["mesas"] = r.Mesas; ultima["ms"] = sw.ElapsedMilliseconds;
                }
                Anotar("Armada «" + plan.Titulo + "»: " + r.Mesas + " mesas en " + (sw.ElapsedMilliseconds / 1000.0).ToString("0.0") + " s");
                Avisar("Plantilla lista en Corel", plan.Titulo + ": " + r.Mesas + " mesa" + (r.Mesas == 1 ? "" : "s") + ".");
                return res;
            }
        }

        // El motivo en palabras (un error de COM trae un código; se traduce lo que se sabe)
        static string Mensaje(Exception e)
        {
            while (e is TargetInvocationException && e.InnerException != null) e = e.InnerException;
            COMException ce = e as COMException;
            if (ce != null)
            {
                uint h = (uint)ce.ErrorCode;
                if (h == 0x80010001 || h == 0x8001010A) return "CorelDRAW está ocupado (¿hay una ventana abierta en Corel?). Cerrala y probá de nuevo.";
                if (h == 0x80080005) return "no se pudo abrir CorelDRAW. Abrilo a mano y probá de nuevo.";
                return "CorelDRAW contestó un error (" + ce.ErrorCode.ToString("X8") + "): " + ce.Message;
            }
            return e.Message;
        }

        // ── HTTP mínimo ───────────────────────────────────────────────────────────────────────────
        public static bool Escuchar()
        {
            TcpListener srv = new TcpListener(IPAddress.Loopback, PUERTO);
            try { srv.Start(); }
            catch (SocketException) { return false; }       // ya hay otro puente escuchando
            Thread t = new Thread(delegate ()
            {
                while (true)
                {
                    TcpClient c;
                    try { c = srv.AcceptTcpClient(); } catch { break; }
                    ThreadPool.QueueUserWorkItem(delegate (object o) { Atender((TcpClient)o); }, c);
                }
            });
            t.IsBackground = true;
            t.Start();
            Anotar("Conectado: esperando plantillas de TIZADA PRO");
            return true;
        }

        static void Atender(TcpClient c)
        {
            using (c)
            {
                try
                {
                    c.ReceiveTimeout = 120000;
                    NetworkStream ns = c.GetStream();
                    // la cabecera, hasta la línea en blanco
                    MemoryStream cab = new MemoryStream();
                    int b, fin = 0;
                    while (fin < 4 && (b = ns.ReadByte()) >= 0)
                    {
                        cab.WriteByte((byte)b);
                        fin = (b == '\r' || b == '\n') ? fin + 1 : 0;
                        if (cab.Length > 65536) return;
                    }
                    string[] lineas = Encoding.ASCII.GetString(cab.ToArray()).Split(new[] { "\r\n" }, StringSplitOptions.None);
                    string[] pedido = lineas[0].Split(' ');
                    if (pedido.Length < 2) return;
                    string metodo = pedido[0].ToUpperInvariant();
                    string ruta = pedido[1].Split('?')[0];
                    Dictionary<string, string> h = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
                    for (int i = 1; i < lineas.Length; i++)
                    {
                        int dp = lineas[i].IndexOf(':');
                        if (dp > 0) h[lineas[i].Substring(0, dp).Trim()] = lineas[i].Substring(dp + 1).Trim();
                    }
                    string origen;
                    h.TryGetValue("Origin", out origen);
                    if (!string.IsNullOrEmpty(origen) && origen != "null")
                    {
                        lock (candado)
                        {
                            bool nuevo = contacto == null || (string)contacto["origen"] != origen;
                            contacto = new Dictionary<string, object>();
                            contacto["origen"] = origen; contacto["t"] = Ahora();
                            if (nuevo) Anotar("Conectado con USER PRO (" + origen.Replace("https://", "").Replace("http://", "") + ")");
                        }
                    }
                    if (metodo == "OPTIONS") { Responder(ns, origen, 204, null); return; }
                    if (metodo == "GET" && ruta == "/estado") { Responder(ns, origen, 200, Estado()); return; }
                    // «Exportar para TIZADA PRO» desde la BARRA DE COREL: el botón del complemento
                    // (`complemento/BotonTizada.cs`) lo pide acá y espera; los diálogos los muestra el conector
                    if (metodo == "POST" && ruta == "/exportar-corel")
                    {
                        string lt; long l = 0;
                        if (h.TryGetValue("Content-Length", out lt)) long.TryParse(lt, out l);
                        for (long i = 0; i < Math.Min(l, 65536); i++) { if (ns.ReadByte() < 0) break; }   // el cuerpo no se usa
                        ResultadoExportar rx = null;
                        // los diálogos («Guardar como», avisos) van en el hilo de la pantalla del conector
                        if (ui != null) ui.Send(delegate (object o) { rx = FlujoExportar.Correr(); }, null);
                        Dictionary<string, object> d = new Dictionary<string, object>();
                        if (rx == null) { d["ok"] = false; d["error"] = "el conector no pudo abrir la ventana"; }
                        else
                        {
                            d["ok"] = rx.Ok; d["cancelado"] = rx.Cancelado; d["error"] = rx.Error;
                            if (rx.Ok) { d["archivo"] = Path.GetFileName(rx.Ruta); d["carpeta"] = Path.GetDirectoryName(rx.Ruta); Avisar("Listo para subir a TIZADA PRO", Path.GetFileName(rx.Ruta)); }
                        }
                        Responder(ns, origen, 200, d);
                        return;
                    }
                    if (metodo == "POST" && ruta == "/plantilla")
                    {
                        string largoTxt;
                        long largo = 0;
                        if (h.TryGetValue("Content-Length", out largoTxt)) long.TryParse(largoTxt, out largo);
                        if (largo <= 0 || largo > TOPE_CUERPO) { Responder(ns, origen, 413, Error("el plan es demasiado grande")); return; }
                        byte[] cuerpo = new byte[largo];
                        int leido = 0;
                        while (leido < largo)
                        {
                            int n = ns.Read(cuerpo, leido, (int)Math.Min(1 << 20, largo - leido));
                            if (n <= 0) return;
                            leido += n;
                        }
                        try { Responder(ns, origen, 200, Plantilla(Encoding.UTF8.GetString(cuerpo))); }
                        catch (ArgumentException e) { Responder(ns, origen, 400, Error(e.Message)); }
                        catch (Exception e) { Responder(ns, origen, 422, Error(e.Message)); }
                        return;
                    }
                    Responder(ns, origen, 404, Error("no existe"));
                }
                catch { }
            }
        }

        static Dictionary<string, object> Error(string msg)
        {
            Dictionary<string, object> d = new Dictionary<string, object>();
            d["ok"] = false; d["error"] = msg;
            return d;
        }

        static void Responder(NetworkStream ns, string origen, int codigo, Dictionary<string, object> cuerpo)
        {
            byte[] datos = cuerpo == null ? new byte[0] : Encoding.UTF8.GetBytes(Json().Serialize(cuerpo));
            string estado = codigo == 200 ? "OK" : codigo == 204 ? "No Content" : codigo == 404 ? "Not Found" : "Error";
            StringBuilder sb = new StringBuilder();
            sb.Append("HTTP/1.1 ").Append(codigo).Append(' ').Append(estado).Append("\r\n");
            sb.Append("Content-Type: application/json; charset=utf-8\r\n");
            sb.Append("Access-Control-Allow-Origin: ").Append(string.IsNullOrEmpty(origen) ? "*" : origen).Append("\r\n");
            sb.Append("Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n");
            sb.Append("Access-Control-Allow-Headers: Content-Type\r\n");
            sb.Append("Access-Control-Allow-Private-Network: true\r\n");
            sb.Append("Vary: Origin\r\nCache-Control: no-store\r\nConnection: close\r\n");
            sb.Append("Content-Length: ").Append(datos.Length).Append("\r\n\r\n");
            byte[] cab = Encoding.ASCII.GetBytes(sb.ToString());
            ns.Write(cab, 0, cab.Length);
            if (datos.Length > 0) ns.Write(datos, 0, datos.Length);
            ns.Flush();
        }

        // ── el ícono junto al reloj ────────────────────────────────────────────────────────────────
        static void Avisar(string titulo, string texto)
        {
            if (ui == null || icono == null) return;
            ui.Post(delegate (object o) { try { icono.ShowBalloonTip(4000, titulo, texto, ToolTipIcon.Info); } catch { } }, null);
        }

        static string CarpetaPlantillas()
        {
            return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "USER PRO", "Plantillas");
        }

        /// El puente con su ícono (modo `/puente`). Una sola instancia por usuario.
        public static void Correr()
        {
            bool nuevo;
            using (Mutex m = new Mutex(true, @"Local\USERPRO-Corel-Puente", out nuevo))
            {
                if (!nuevo) return;                                  // ya corre otro
                HiloCorel.Iniciar();
                if (!Escuchar()) return;                             // el puerto ya lo tiene otro puente
                ui = new WindowsFormsSynchronizationContext();
                SynchronizationContext.SetSynchronizationContext(ui);
                icono = new NotifyIcon();
                try
                {
                    Stream ico = Assembly.GetExecutingAssembly().GetManifestResourceStream("icono.ico");
                    icono.Icon = ico != null ? new Icon(ico, 16, 16) : SystemIcons.Application;
                }
                catch { icono.Icon = SystemIcons.Application; }
                icono.Text = "USER PRO para CorelDRAW " + Version.Texto;
                ContextMenuStrip menu = new ContextMenuStrip();
                ToolStripMenuItem titulo = new ToolStripMenuItem("USER PRO para CorelDRAW " + Version.Texto);
                titulo.Enabled = false;
                menu.Items.Add(titulo);
                ToolStripMenuItem estado = new ToolStripMenuItem("…");
                estado.Enabled = false;
                menu.Items.Add(estado);
                menu.Items.Add(new ToolStripSeparator());
                menu.Items.Add("Abrir la carpeta de plantillas", null, delegate (object s, EventArgs e)
                {
                    try { Directory.CreateDirectory(CarpetaPlantillas()); Process.Start("explorer.exe", "\"" + CarpetaPlantillas() + "\""); } catch { }
                });
                // EL BOTÓN «Exportar para TIZADA PRO» pegado a la ventana de Corel (ver `BotonCorel`)
                BotonCorel botonCorel = new BotonCorel(delegate (string tit, string txt, bool error) { Avisar(tit, txt); });
                IntPtr _crear = botonCorel.Handle;                  // se crea ya, oculto: aparece solo con Corel abierto
                menu.Items.Add("Exportar para TIZADA PRO", null, delegate (object s, EventArgs e) { botonCorel.Exportar(); });
                ToolStripMenuItem verBoton = new ToolStripMenuItem("Mostrar el botón en CorelDRAW");
                verBoton.Checked = botonCorel.Activo;
                verBoton.Click += delegate (object s, EventArgs e) { verBoton.Checked = !verBoton.Checked; botonCorel.CambiarVisible(verBoton.Checked); };
                menu.Items.Add(verBoton);
                menu.Items.Add(new ToolStripSeparator());
                menu.Items.Add("Cerrar el puente", null, delegate (object s, EventArgs e) { icono.Visible = false; Application.Exit(); });
                menu.Opening += delegate (object s, System.ComponentModel.CancelEventArgs e)
                {
                    int mayor;
                    string corel = ArmarCorel.Instalado(out mayor);
                    Dictionary<string, object> c;
                    lock (candado) c = contacto;
                    estado.Text = (corel == null ? "No encontré CorelDRAW" : corel) +
                                  (c != null ? " · conectado con USER PRO" : " · esperando a USER PRO");
                };
                icono.ContextMenuStrip = menu;
                icono.Visible = true;
                Application.ApplicationExit += delegate (object s, EventArgs e) { try { icono.Visible = false; } catch { } };
                Application.Run();
            }
        }
    }
}
