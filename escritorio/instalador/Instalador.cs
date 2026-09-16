// INSTALADOR DE TIZADA PRO (aplicación de escritorio).
//
// Se compila con el csc.exe que trae Windows (.NET Framework 4), sin herramientas de terceros: lo
// arma `CONSTRUIR-APLICACION.bat`. Lleva ADENTRO, como recursos:
//   · app.zip          → la carpeta del programa que armó PyInstaller;
//   · desinstalar.exe  → el desinstalador (se deja en la carpeta del programa);
//   · version.txt      → la versión que se muestra;
//   · logo.png         → el logo de la ventana.
//
// Decisiones:
//   · Instala PARA EL USUARIO, en %LOCALAPPDATA%\Programs\TIZADA PRO: no pide administrador.
//   · Los DATOS (moldes, diseños, tizadas) viven en %LOCALAPPDATA%\TIZADA PRO y NUNCA se tocan
//     acá: actualizar el programa es volver a correr este instalador.
//   · Avisa ANTES si falta algo que la app necesita (el motor de ventanas WebView2, SQL Server),
//     con el enlace para bajarlo. No lo instala solo: son instaladores de Microsoft que piden permisos.
// ⚠️ C# 5 (el compilador de .NET Framework): nada de $"", ?. ni => en propiedades.
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Win32;

namespace TizadaPro
{
    static class Programa
    {
        [DllImport("user32.dll")]
        static extern bool SetProcessDPIAware();

        // `/prueba:<carpeta>` instala SIN ventana en esa carpeta, sin accesos directos ni registro
        // de Windows, y termina con código 0 (bien) o 1 (mal). Sirve para verificar el instalador
        // sin instalar nada de verdad en la PC donde se arma.
        [STAThread]
        static int Main(string[] args)
        {
            foreach (string a in args)
            {
                if (a.StartsWith("/prueba:", StringComparison.OrdinalIgnoreCase))
                {
                    try { Ventana.Trabajo(a.Substring(8).Trim('"'), false, true, null, null); return 0; }
                    catch (Exception e) { Console.Error.WriteLine(e.Message); return 1; }
                }
            }
            try { SetProcessDPIAware(); } catch { }
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new Ventana());
            return 0;
        }
    }

    static class Comun
    {
        public const string Nombre = "TIZADA PRO";
        public const string ClaveDesinstalar = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\TizadaPro";

        public static string CarpetaPrograma
        {
            get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", Nombre); }
        }

        public static string CarpetaDatos
        {
            get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), Nombre); }
        }

        public static string AccesoMenu
        {
            get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs), Nombre + ".lnk"); }
        }

        public static string AccesoEscritorio
        {
            get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), Nombre + ".lnk"); }
        }

        public static string Recurso(string nombre)
        {
            using (Stream s = Assembly.GetExecutingAssembly().GetManifestResourceStream(nombre))
            {
                if (s == null) return "";
                using (StreamReader r = new StreamReader(s)) return r.ReadToEnd().Trim();
            }
        }

        // ¿Está el motor de ventanas (WebView2)? Windows 11 lo trae; en Windows 10 casi siempre.
        public static bool HayWebView2()
        {
            string guid = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}";
            string[] rutas = {
                @"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\" + guid,
                @"SOFTWARE\Microsoft\EdgeUpdate\Clients\" + guid };
            foreach (string r in rutas)
            {
                if (VersionValida(Registry.LocalMachine, r)) return true;
                if (VersionValida(Registry.CurrentUser, r)) return true;
            }
            return false;
        }

        static bool VersionValida(RegistryKey raiz, string ruta)
        {
            try
            {
                using (RegistryKey k = raiz.OpenSubKey(ruta))
                {
                    if (k == null) return false;
                    string pv = Convert.ToString(k.GetValue("pv"));
                    return !string.IsNullOrEmpty(pv) && pv != "0.0.0.0";
                }
            }
            catch { return false; }
        }

        // ¿Hay algún SQL Server instalado? (la app lo necesita para guardar moldes y piezas)
        public static bool HaySqlServer()
        {
            foreach (RegistryView vista in new[] { RegistryView.Registry64, RegistryView.Registry32 })
            {
                try
                {
                    using (RegistryKey hklm = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, vista))
                    using (RegistryKey k = hklm.OpenSubKey(@"SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL"))
                    {
                        if (k != null && k.GetValueNames().Length > 0) return true;
                    }
                }
                catch { }
            }
            return false;
        }

        // Cierra la app si está abierta (primero amable, después a la fuerza). True si quedó cerrada.
        public static bool CerrarApp()
        {
            Process[] ps = Process.GetProcessesByName(Nombre);
            foreach (Process p in ps)
            {
                try { p.CloseMainWindow(); } catch { }
            }
            DateTime hasta = DateTime.Now.AddSeconds(10);
            while (DateTime.Now < hasta && Process.GetProcessesByName(Nombre).Length > 0) Thread.Sleep(300);
            foreach (Process p in Process.GetProcessesByName(Nombre))
            {
                try { p.Kill(); p.WaitForExit(5000); } catch { }
            }
            return Process.GetProcessesByName(Nombre).Length == 0;
        }

        public static void CrearAcceso(string lnk, string destino, string carpeta)
        {
            Type t = Type.GetTypeFromProgID("WScript.Shell");
            object shell = Activator.CreateInstance(t);
            object acceso = t.InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, shell, new object[] { lnk });
            Type ta = acceso.GetType();
            ta.InvokeMember("TargetPath", BindingFlags.SetProperty, null, acceso, new object[] { destino });
            ta.InvokeMember("WorkingDirectory", BindingFlags.SetProperty, null, acceso, new object[] { carpeta });
            ta.InvokeMember("IconLocation", BindingFlags.SetProperty, null, acceso, new object[] { destino + ",0" });
            ta.InvokeMember("Description", BindingFlags.SetProperty, null, acceso, new object[] { "TIZADA PRO · Motor de sublimación" });
            ta.InvokeMember("Save", BindingFlags.InvokeMethod, null, acceso, null);
            Marshal.FinalReleaseComObject(acceso);
            Marshal.FinalReleaseComObject(shell);
        }
    }

    class Ventana : Form
    {
        readonly string version = Comun.Recurso("version.txt");
        Label lblEstado;
        ProgressBar barra;
        Button btnInstalar, btnAbrir, btnCerrar;
        CheckBox chkEscritorio;

        public Ventana()
        {
            Text = "Instalar " + Comun.Nombre;
            ClientSize = new Size(600, 470);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Color.White;
            Font = new Font("Segoe UI", 10f);
            try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch { }

            PictureBox logo = new PictureBox();
            logo.SizeMode = PictureBoxSizeMode.Zoom;
            logo.SetBounds(28, 24, 76, 76);
            try { logo.Image = Image.FromStream(Assembly.GetExecutingAssembly().GetManifestResourceStream("logo.png")); } catch { }
            Controls.Add(logo);

            Label titulo = new Label();
            titulo.Text = Comun.Nombre;
            titulo.Font = new Font("Segoe UI Semibold", 20f);
            titulo.SetBounds(120, 26, 440, 42);
            Controls.Add(titulo);

            Label sub = new Label();
            sub.Text = "Versión " + version + " · aplicación para Windows";
            sub.ForeColor = Color.DimGray;
            sub.SetBounds(122, 68, 440, 24);
            Controls.Add(sub);

            Label texto = new Label();
            texto.Text = "Se instala para tu usuario (no pide permisos de administrador) en:\n" + Comun.CarpetaPrograma +
                         "\n\nTus moldes, diseños y tizadas se guardan aparte, en:\n" + Comun.CarpetaDatos +
                         "\nActualizar o desinstalar el programa no los toca.";
            texto.SetBounds(28, 116, 548, 118);
            Controls.Add(texto);

            int y = 238;
            y = AgregarChequeo(y, Comun.HayWebView2(), "Motor de ventanas de Windows (WebView2)",
                               "Falta: sin él la app no se puede ver.", "https://go.microsoft.com/fwlink/p/?LinkId=2124703");
            y = AgregarChequeo(y, Comun.HaySqlServer(), "SQL Server (base de datos)",
                               "Falta: instalalo antes de usar la app (es gratis, versión Express).",
                               "https://www.microsoft.com/es-es/sql-server/sql-server-downloads");

            chkEscritorio = new CheckBox();
            chkEscritorio.Text = "Crear un acceso directo en el escritorio";
            chkEscritorio.Checked = true;
            chkEscritorio.SetBounds(28, y + 6, 540, 26);
            Controls.Add(chkEscritorio);

            barra = new ProgressBar();
            barra.SetBounds(28, 356, 544, 18);
            barra.Visible = false;
            Controls.Add(barra);

            lblEstado = new Label();
            lblEstado.ForeColor = Color.DimGray;
            lblEstado.SetBounds(28, 380, 544, 24);
            Controls.Add(lblEstado);

            btnInstalar = Boton("Instalar", 432, true);
            btnInstalar.Click += delegate { Instalar(); };
            btnAbrir = Boton("Abrir TIZADA PRO", 392, true);
            btnAbrir.Width = 180;
            btnAbrir.Visible = false;
            btnAbrir.Click += delegate
            {
                try { Process.Start(Path.Combine(Comun.CarpetaPrograma, Comun.Nombre + ".exe")); } catch { }
                Close();
            };
            btnCerrar = Boton("Cancelar", 292, false);
            btnCerrar.Click += delegate { Close(); };
        }

        Button Boton(string texto, int x, bool principal)
        {
            Button b = new Button();
            b.Text = texto;
            b.SetBounds(x, 416, 140, 38);
            b.FlatStyle = FlatStyle.Flat;
            if (principal)
            {
                b.BackColor = Color.FromArgb(0, 159, 227);
                b.ForeColor = Color.White;
                b.FlatAppearance.BorderSize = 0;
            }
            Controls.Add(b);
            return b;
        }

        int AgregarChequeo(int y, bool ok, string que, string falta, string enlace)
        {
            Label l = new Label();
            l.Text = (ok ? "✔  " : "⚠  ") + que + (ok ? "" : " — " + falta);
            l.ForeColor = ok ? Color.SeaGreen : Color.FromArgb(200, 110, 0);
            l.SetBounds(28, y, 548, 24);
            Controls.Add(l);
            y += 24;
            if (!ok)
            {
                LinkLabel ln = new LinkLabel();
                ln.Text = "Bajarlo de Microsoft";
                ln.SetBounds(50, y, 300, 22);
                ln.LinkClicked += delegate { try { Process.Start(enlace); } catch { } };
                Controls.Add(ln);
                y += 24;
            }
            return y + 4;
        }

        void Estado(string t)
        {
            if (InvokeRequired) { BeginInvoke(new Action<string>(Estado), t); return; }
            lblEstado.Text = t;
        }

        void Avance(int pct)
        {
            if (InvokeRequired) { BeginInvoke(new Action<int>(Avance), pct); return; }
            barra.Value = Math.Max(0, Math.Min(100, pct));
        }

        void Instalar()
        {
            btnInstalar.Enabled = false;
            btnCerrar.Enabled = false;
            chkEscritorio.Enabled = false;
            barra.Visible = true;
            bool escritorio = chkEscritorio.Checked;
            Thread hilo = new Thread(delegate ()
            {
                string error = null;
                try { Trabajo(Comun.CarpetaPrograma, escritorio, false, Estado, Avance); }
                catch (Exception e) { error = e.Message; }
                BeginInvoke(new Action(delegate
                {
                    btnCerrar.Enabled = true;
                    btnCerrar.Text = "Cerrar";
                    if (error != null)
                    {
                        Estado("No se pudo instalar: " + error);
                        btnInstalar.Enabled = true;
                        btnInstalar.Text = "Reintentar";
                    }
                    else
                    {
                        Estado("Listo. TIZADA PRO quedó instalado.");
                        btnInstalar.Visible = false;
                        btnAbrir.Visible = true;
                        btnCerrar.Left = 252;
                    }
                }));
            });
            hilo.IsBackground = true;
            hilo.Start();
        }

        public static void Trabajo(string dir, bool escritorio, bool prueba, Action<string> Estado, Action<int> Avance)
        {
            if (Estado == null) Estado = delegate (string x) { };
            if (Avance == null) Avance = delegate (int x) { };
            string version = Comun.Recurso("version.txt");
            if (!prueba && Process.GetProcessesByName(Comun.Nombre).Length > 0)
            {
                Estado("Cerrando TIZADA PRO, que estaba abierto…");
                if (!Comun.CerrarApp()) throw new Exception("TIZADA PRO sigue abierto. Cerralo y volvé a intentar.");
            }

            // La versión anterior del PROGRAMA se borra entera (los datos están en otra carpeta).
            Estado("Preparando la carpeta…");
            if (Directory.Exists(dir))
            {
                for (int i = 0; ; i++)
                {
                    try { Directory.Delete(dir, true); break; }
                    catch (Exception)
                    {
                        if (i >= 10) throw new Exception("no se pudo reemplazar la versión anterior (¿hay algún archivo abierto?)");
                        Thread.Sleep(700);
                    }
                }
            }
            Directory.CreateDirectory(dir);

            Estado("Copiando el programa…");
            using (Stream s = Assembly.GetExecutingAssembly().GetManifestResourceStream("app.zip"))
            using (ZipArchive zip = new ZipArchive(s, ZipArchiveMode.Read))
            {
                long total = 0, hecho = 0;
                foreach (ZipArchiveEntry e in zip.Entries) total += e.Length;
                byte[] buf = new byte[1 << 16];
                foreach (ZipArchiveEntry e in zip.Entries)
                {
                    string destino = Path.GetFullPath(Path.Combine(dir, e.FullName));
                    if (!destino.StartsWith(dir, StringComparison.OrdinalIgnoreCase)) continue;   // nada fuera de la carpeta
                    if (e.FullName.EndsWith("/")) { Directory.CreateDirectory(destino); continue; }
                    Directory.CreateDirectory(Path.GetDirectoryName(destino));
                    using (Stream src = e.Open())
                    using (FileStream dst = new FileStream(destino, FileMode.Create, FileAccess.Write))
                    {
                        int n;
                        while ((n = src.Read(buf, 0, buf.Length)) > 0)
                        {
                            dst.Write(buf, 0, n);
                            hecho += n;
                        }
                    }
                    if (total > 0) Avance((int)(hecho * 95 / total));
                }
            }

            Estado("Creando los accesos directos…");
            string exe = Path.Combine(dir, Comun.Nombre + ".exe");
            using (Stream s = Assembly.GetExecutingAssembly().GetManifestResourceStream("desinstalar.exe"))
            using (FileStream f = new FileStream(Path.Combine(dir, "Desinstalar TIZADA PRO.exe"), FileMode.Create))
            {
                s.CopyTo(f);
            }
            if (prueba) { Avance(100); return; }
            Comun.CrearAcceso(Comun.AccesoMenu, exe, dir);
            if (escritorio) Comun.CrearAcceso(Comun.AccesoEscritorio, exe, dir);
            else if (File.Exists(Comun.AccesoEscritorio)) File.Delete(Comun.AccesoEscritorio);

            // «Agregar o quitar programas» de Windows.
            long kb = 0;
            foreach (string f in Directory.GetFiles(dir, "*", SearchOption.AllDirectories)) kb += new FileInfo(f).Length / 1024;
            using (RegistryKey k = Registry.CurrentUser.CreateSubKey(Comun.ClaveDesinstalar))
            {
                k.SetValue("DisplayName", Comun.Nombre);
                k.SetValue("DisplayVersion", version);
                k.SetValue("Publisher", "TIZADA PRO");
                k.SetValue("DisplayIcon", exe);
                k.SetValue("InstallLocation", dir);
                k.SetValue("UninstallString", "\"" + Path.Combine(dir, "Desinstalar TIZADA PRO.exe") + "\"");
                k.SetValue("NoModify", 1, RegistryValueKind.DWord);
                k.SetValue("NoRepair", 1, RegistryValueKind.DWord);
                k.SetValue("EstimatedSize", (int)Math.Min(int.MaxValue, kb), RegistryValueKind.DWord);
            }
            Avance(100);
        }
    }
}
