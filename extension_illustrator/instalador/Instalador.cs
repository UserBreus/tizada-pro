// USER PRO para Illustrator — INSTALADOR (Windows). Se compila con `extension_illustrator/construir.py`.
//
// Pensado para alguien que nunca usó una computadora: una ventana, pocas palabras, un botón por
// paso y nada técnico en pantalla. Diseño minimalista y moderno (2026-09-23): fondo oscuro, botones
// redondeados propios (`Boton`), y una tarjeta que dice QUÉ VERSIÓN HAY INSTALADA y CUÁL SE VA A
// INSTALAR (`TarjetaVersion`). No pide permisos de administrador: todo va a la carpeta y al registro
// del propio usuario.
//   · copia la extensión a %APPDATA%\Adobe\CEP\extensions\com.tizadapro.illustrator;
//   · habilita las extensiones sin firma de Adobe (PlayerDebugMode = 1, CSXS 9 a 16);
//   · se registra en «Aplicaciones instaladas» de Windows para poder quitarla (`/desinstalar`);
//   · al terminar avisa que el tutorial de cómo conectarla está DENTRO de Illustrator (el panel de
//     USER PRO se abre solo la primera vez).
// C# 5 (el compilador que trae Windows): nada de `$"…"`, `?.` ni `=>` en propiedades.
using System;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Text;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;
using System.Windows.Forms;
using Microsoft.Win32;

namespace UserPro
{
    static class Programa
    {
        [STAThread]
        static void Main(string[] args)
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            bool quitar = false;
            foreach (string a in args) if (a.Equals("/desinstalar", StringComparison.OrdinalIgnoreCase)) quitar = true;
            Application.Run(new Ventana(quitar));
        }
    }

    static class Estilo
    {
        public static readonly Color Fondo = Color.FromArgb(17, 20, 24);
        public static readonly Color Tarjeta = Color.FromArgb(26, 30, 36);
        public static readonly Color Borde = Color.FromArgb(48, 54, 63);
        public static readonly Color Texto = Color.FromArgb(240, 242, 245);
        public static readonly Color Suave = Color.FromArgb(150, 159, 172);
        public static readonly Color Cian = Color.FromArgb(0, 213, 255);
        public static readonly Color CianSobre = Color.FromArgb(90, 228, 255);
        public static readonly Color CianApretado = Color.FromArgb(0, 176, 212);
        public static readonly Color Verde = Color.FromArgb(52, 211, 153);

        public static GraphicsPath Redondo(RectangleF r, float radio)
        {
            float d = radio * 2;
            GraphicsPath p = new GraphicsPath();
            p.AddArc(r.X, r.Y, d, d, 180, 90);
            p.AddArc(r.Right - d, r.Y, d, d, 270, 90);
            p.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
            p.AddArc(r.X, r.Bottom - d, d, d, 90, 90);
            p.CloseFigure();
            return p;
        }
    }

    // Botón plano con esquinas redondeadas. «Principal» = celeste lleno (el que hay que tocar);
    // el otro, sólo el borde. Cambia al pasar el mouse y al apretar; con teclado, Enter/Espacio.
    class Boton : Control, IButtonControl
    {
        public bool Principal;
        bool sobre, apretado;
        DialogResult resultado = DialogResult.None;

        public Boton()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint |
                     ControlStyles.ResizeRedraw | ControlStyles.Selectable | ControlStyles.StandardClick, true);
            Cursor = Cursors.Hand;
            Font = new Font("Segoe UI Semibold", 12.5F);
            Size = new Size(190, 50);
            TabStop = true;
        }

        public DialogResult DialogResult { get { return resultado; } set { resultado = value; } }
        public void NotifyDefault(bool valor) { }
        public void PerformClick() { if (Enabled) OnClick(EventArgs.Empty); }

        protected override void OnMouseEnter(EventArgs e) { sobre = true; Invalidate(); base.OnMouseEnter(e); }
        protected override void OnMouseLeave(EventArgs e) { sobre = false; apretado = false; Invalidate(); base.OnMouseLeave(e); }
        protected override void OnMouseDown(MouseEventArgs e) { apretado = true; Focus(); Invalidate(); base.OnMouseDown(e); }
        protected override void OnMouseUp(MouseEventArgs e) { apretado = false; Invalidate(); base.OnMouseUp(e); }
        protected override void OnGotFocus(EventArgs e) { Invalidate(); base.OnGotFocus(e); }
        protected override void OnLostFocus(EventArgs e) { Invalidate(); base.OnLostFocus(e); }
        protected override void OnTextChanged(EventArgs e) { Invalidate(); base.OnTextChanged(e); }
        protected override void OnKeyDown(KeyEventArgs e)
        {
            if (e.KeyCode == Keys.Enter || e.KeyCode == Keys.Space) { PerformClick(); e.Handled = true; }
            base.OnKeyDown(e);
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            Graphics g = e.Graphics;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.Clear(Parent != null ? Parent.BackColor : Estilo.Fondo);
            RectangleF r = new RectangleF(1, 1, Width - 3, Height - 3);
            float radio = Math.Min(12F, Height / 2F - 1);
            using (GraphicsPath p = Estilo.Redondo(r, radio))
            {
                if (Principal)
                {
                    Color c = apretado ? Estilo.CianApretado : (sobre ? Estilo.CianSobre : Estilo.Cian);
                    using (SolidBrush b = new SolidBrush(c)) g.FillPath(b, p);
                }
                else
                {
                    if (sobre) using (SolidBrush b = new SolidBrush(Color.FromArgb(34, 39, 46))) g.FillPath(b, p);
                    using (Pen pen = new Pen(sobre ? Color.FromArgb(90, 100, 114) : Estilo.Borde, 1.5F)) g.DrawPath(pen, p);
                }
                if (Focused && !Principal)
                    using (Pen pf = new Pen(Estilo.Cian, 1.5F)) g.DrawPath(pf, p);
            }
            TextRenderer.DrawText(g, Text, Font, new Rectangle(0, 0, Width, Height),
                Principal ? Color.Black : Estilo.Texto,
                TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.SingleLine);
        }
    }

    // La tarjeta de versiones: «Instalada  1.4.0   →   Nueva  1.5.0».
    class TarjetaVersion : Control
    {
        public string Instalada = "—";
        public string Nueva = "—";
        public string TituloIzq = "Instalada";
        public string TituloDer = "Esta versión";
        public bool SoloUna;                           // «Instalada: 1.5.0» sola (al terminar)

        public TarjetaVersion()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint | ControlStyles.ResizeRedraw, true);
            Height = 78;
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            Graphics g = e.Graphics;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.TextRenderingHint = TextRenderingHint.ClearTypeGridFit;
            g.Clear(Parent != null ? Parent.BackColor : Estilo.Fondo);
            RectangleF r = new RectangleF(1, 1, Width - 3, Height - 3);
            using (GraphicsPath p = Estilo.Redondo(r, 12F))
            {
                using (SolidBrush b = new SolidBrush(Estilo.Tarjeta)) g.FillPath(b, p);
                using (Pen pen = new Pen(Estilo.Borde, 1F)) g.DrawPath(pen, p);
            }
            using (Font chica = new Font("Segoe UI", 9.5F))
            using (Font grande = new Font("Segoe UI Semibold", 17F))
            {
                int pad = 22;
                if (SoloUna)
                {
                    TextRenderer.DrawText(g, TituloIzq, chica, new Point(pad, 14), Estilo.Suave);
                    TextRenderer.DrawText(g, Nueva, grande, new Point(pad - 2, 32), Estilo.Verde);
                    return;
                }
                int mitad = Width / 2;
                TextRenderer.DrawText(g, TituloIzq, chica, new Point(pad, 14), Estilo.Suave);
                TextRenderer.DrawText(g, Instalada, grande, new Point(pad - 2, 32), Estilo.Texto);
                TextRenderer.DrawText(g, "→", grande, new Rectangle(mitad - 30, 24, 60, 40), Estilo.Suave,
                    TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter);
                TextRenderer.DrawText(g, TituloDer, chica, new Point(mitad + 40, 14), Estilo.Suave);
                TextRenderer.DrawText(g, Nueva, grande, new Point(mitad + 38, 32), Estilo.Cian);
            }
        }
    }

    class Ventana : Form
    {
        const string ID = "com.tizadapro.illustrator";
        const string CLAVE_DESINSTALAR = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\USERPRO-Illustrator";
        const string NOMBRE = "USER PRO para Illustrator";

        readonly Label titulo = new Label();
        readonly Label cuerpo = new Label();
        readonly TarjetaVersion tarjeta = new TarjetaVersion();
        readonly FlowLayoutPanel botones = new FlowLayoutPanel();
        readonly bool modoQuitar;

        static string Destino
        {
            get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Adobe", "CEP", "extensions", ID); }
        }
        static string CarpetaPrograma
        {
            get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "USER PRO", "Illustrator"); }
        }
        static string ExePrograma
        {
            get { return Path.Combine(CarpetaPrograma, "USER-PRO-Illustrator.exe"); }
        }

        // La versión que hay instalada ahora (la del manifiesto de la extensión), o null si no hay.
        static string VersionInstalada()
        {
            try
            {
                string m = Path.Combine(Destino, "CSXS", "manifest.xml");
                if (!File.Exists(m)) return null;
                Match x = Regex.Match(File.ReadAllText(m), "ExtensionBundleVersion=\"([^\"]+)\"");
                return x.Success ? x.Groups[1].Value : "?";
            }
            catch { return "?"; }
        }

        static int Comparar(string a, string b)
        {
            try
            {
                string[] x = a.Split('.'), y = b.Split('.');
                for (int i = 0; i < Math.Max(x.Length, y.Length); i++)
                {
                    int p = i < x.Length ? int.Parse(x[i]) : 0, q = i < y.Length ? int.Parse(y[i]) : 0;
                    if (p != q) return p.CompareTo(q);
                }
                return 0;
            }
            catch { return 0; }
        }

        [DllImport("dwmapi.dll")]
        static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int valor, int tam);

        protected override void OnHandleCreated(EventArgs e)
        {
            base.OnHandleCreated(e);
            // barra de título oscura (Windows 10 20H1 en adelante / 11): hace juego con la ventana
            try { int si = 1; if (DwmSetWindowAttribute(Handle, 20, ref si, 4) != 0) DwmSetWindowAttribute(Handle, 19, ref si, 4); }
            catch { }
        }

        public Ventana(bool quitar)
        {
            modoQuitar = quitar;
            AutoScaleDimensions = new SizeF(96F, 96F);
            AutoScaleMode = AutoScaleMode.Dpi;
            Text = NOMBRE + " " + Version.Texto;
            BackColor = Estilo.Fondo;
            ForeColor = Estilo.Texto;
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;
            ClientSize = new Size(640, 470);
            Font = new Font("Segoe UI", 11F);
            try
            {
                Stream ico = Assembly.GetExecutingAssembly().GetManifestResourceStream("icono.ico");
                if (ico != null) Icon = new Icon(ico);
            }
            catch { }

            TableLayoutPanel t = new TableLayoutPanel();
            t.Dock = DockStyle.Fill;
            t.Padding = new Padding(40, 30, 40, 30);
            t.ColumnCount = 1;
            t.RowCount = 5;
            t.RowStyles.Add(new RowStyle(SizeType.Absolute, 70F));
            t.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            t.RowStyles.Add(new RowStyle(SizeType.Percent, 100F));
            t.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            t.RowStyles.Add(new RowStyle(SizeType.AutoSize));

            PictureBox logo = new PictureBox();
            logo.Dock = DockStyle.Left;
            logo.Width = 250;
            logo.SizeMode = PictureBoxSizeMode.Zoom;
            try
            {
                Stream s = Assembly.GetExecutingAssembly().GetManifestResourceStream("isologo.png");
                if (s != null) logo.Image = Image.FromStream(s);
            }
            catch { }
            t.Controls.Add(logo, 0, 0);

            titulo.AutoSize = true;
            titulo.Font = new Font("Segoe UI Semibold", 20F);
            titulo.ForeColor = Estilo.Texto;
            titulo.Margin = new Padding(0, 22, 0, 6);
            titulo.MaximumSize = new Size(560, 0);
            t.Controls.Add(titulo, 0, 1);

            cuerpo.Dock = DockStyle.Fill;
            cuerpo.Font = new Font("Segoe UI", 12F);
            cuerpo.ForeColor = Estilo.Suave;
            cuerpo.Margin = new Padding(0, 0, 0, 8);
            t.Controls.Add(cuerpo, 0, 2);

            tarjeta.Dock = DockStyle.Fill;
            tarjeta.Margin = new Padding(0, 0, 0, 18);
            t.Controls.Add(tarjeta, 0, 3);

            botones.Dock = DockStyle.Fill;
            botones.AutoSize = true;
            botones.FlowDirection = FlowDirection.RightToLeft;
            botones.WrapContents = false;
            botones.Margin = new Padding(0);
            t.Controls.Add(botones, 0, 4);

            Controls.Add(t);

            if (modoQuitar) PaginaQuitar(); else PaginaBienvenida();
        }

        Boton NuevoBoton(string texto, bool principal, EventHandler alTocar)
        {
            Boton b = new Boton();
            b.Text = texto;
            b.Principal = principal;
            b.Margin = new Padding(12, 0, 0, 0);
            if (principal) b.Size = new Size(210, 50);
            b.Click += alTocar;
            return b;
        }

        // `principal` va a la derecha (el que se toca), el resto a su izquierda
        void Pagina(string tit, string texto, bool conTarjeta, Boton principal, params Boton[] otros)
        {
            titulo.Text = tit;
            cuerpo.Text = texto;
            tarjeta.Visible = conTarjeta;
            tarjeta.Invalidate();
            botones.Controls.Clear();
            if (principal != null) { botones.Controls.Add(principal); AcceptButton = principal; }
            foreach (Boton b in otros) botones.Controls.Add(b);
            if (principal != null) principal.Focus();
            Refresh();
        }

        void Salir(object s, EventArgs e) { Close(); }

        // ── instalar ───────────────────────────────────────────────────────────────────────────
        void PaginaBienvenida()
        {
            string antes = VersionInstalada();
            string nueva = Version.Texto;
            tarjeta.SoloUna = false;
            tarjeta.TituloIzq = "Versión instalada";
            tarjeta.TituloDer = "Versión a instalar";
            tarjeta.Instalada = antes ?? "ninguna";
            tarjeta.Nueva = nueva;

            string tit, texto, boton;
            if (antes == null)
            {
                tit = "Instalar USER PRO en Illustrator";
                texto = "Prepara Illustrator para recibir las plantillas de USER PRO. Tarda unos segundos.";
                boton = "Instalar";
            }
            else if (antes == "?" || Comparar(antes, nueva) < 0)
            {
                tit = "Hay una versión nueva";
                texto = "Se reemplaza la versión que tenés por la nueva. Tus archivos no se tocan.";
                boton = "Actualizar";
            }
            else if (Comparar(antes, nueva) == 0)
            {
                tit = "Ya tenés esta versión";
                texto = "Podés volver a instalarla si Illustrator no la muestra o algo no anda.";
                boton = "Reinstalar";
            }
            else
            {
                tit = "Tenés una versión más nueva";
                texto = "La instalada es más nueva que la de este instalador. Si instalás, vuelve a la anterior.";
                boton = "Instalar igual";
            }
            if (!HayIllustrator())
                texto += "\n\nNo encontré Illustrator en esta computadora: va a funcionar cuando esté instalado.";
            Pagina(tit, texto, true, NuevoBoton(boton, true, Instalar), NuevoBoton("Salir", false, Salir));
        }

        void Instalar(object s, EventArgs e)
        {
            if (Process.GetProcessesByName("Illustrator").Length > 0)
            {
                Pagina("Primero cerrá Illustrator",
                       "Illustrator está abierto. Guardá lo que estés haciendo, cerralo y tocá «Ya lo cerré».",
                       false, NuevoBoton("Ya lo cerré", true, Instalar), NuevoBoton("Salir", false, Salir));
                return;
            }
            Pagina("Instalando…", "Un momento, por favor.", false, null);
            Cursor = Cursors.WaitCursor;
            try
            {
                CopiarExtension();
                HabilitarExtensiones();
                RegistrarDesinstalador();
                Cursor = Cursors.Default;
                tarjeta.SoloUna = true;
                tarjeta.TituloIzq = "Versión instalada";
                tarjeta.Nueva = Version.Texto;
                Pagina("¡Listo!",
                       "Abrí Illustrator: se abre solo un cuadro de USER PRO con un tutorial que te explica, paso a paso, cómo conectarlo.",
                       true, NuevoBoton("Cerrar", true, Salir));
            }
            catch (Exception ex)
            {
                Cursor = Cursors.Default;
                Pagina("Algo no salió bien",
                       "Cerrá Illustrator si está abierto y probá de nuevo.\n\nDetalle (para quien te ayude): " + ex.Message,
                       false, NuevoBoton("Probar de nuevo", true, Instalar), NuevoBoton("Salir", false, Salir));
            }
        }

        static void CopiarExtension()
        {
            string dest = Destino;
            if (Directory.Exists(dest)) Directory.Delete(dest, true);     // la versión anterior, entera
            Directory.CreateDirectory(dest);
            string raiz = Path.GetFullPath(dest) + Path.DirectorySeparatorChar;
            using (Stream z = Assembly.GetExecutingAssembly().GetManifestResourceStream("extension.zip"))
            using (ZipArchive zip = new ZipArchive(z, ZipArchiveMode.Read))
            {
                foreach (ZipArchiveEntry en in zip.Entries)
                {
                    string ruta = Path.GetFullPath(Path.Combine(dest, en.FullName));
                    if (!ruta.StartsWith(raiz, StringComparison.OrdinalIgnoreCase)) continue;   // nada fuera de la carpeta
                    if (en.FullName.EndsWith("/")) { Directory.CreateDirectory(ruta); continue; }
                    Directory.CreateDirectory(Path.GetDirectoryName(ruta));
                    en.ExtractToFile(ruta, true);
                }
            }
        }

        // Illustrator sólo carga extensiones firmadas por Adobe salvo que esto esté prendido (una
        // clave del propio usuario, una por versión del motor de extensiones).
        static void HabilitarExtensiones()
        {
            for (int v = 9; v <= 16; v++)
            {
                using (RegistryKey k = Registry.CurrentUser.CreateSubKey(@"Software\Adobe\CSXS." + v))
                {
                    if (k != null) k.SetValue("PlayerDebugMode", "1", RegistryValueKind.String);
                }
            }
        }

        // Una copia de este mismo programa queda guardada para poder QUITAR la extensión desde
        // «Aplicaciones instaladas» de Windows.
        static void RegistrarDesinstalador()
        {
            Directory.CreateDirectory(CarpetaPrograma);
            string yo = Assembly.GetExecutingAssembly().Location;
            if (!string.Equals(Path.GetFullPath(yo), Path.GetFullPath(ExePrograma), StringComparison.OrdinalIgnoreCase))
                File.Copy(yo, ExePrograma, true);
            using (RegistryKey k = Registry.CurrentUser.CreateSubKey(CLAVE_DESINSTALAR))
            {
                if (k == null) return;
                k.SetValue("DisplayName", NOMBRE);
                k.SetValue("DisplayVersion", Version.Texto);
                k.SetValue("Publisher", "USER PRO");
                k.SetValue("DisplayIcon", ExePrograma + ",0");
                k.SetValue("InstallLocation", Destino);
                k.SetValue("UninstallString", "\"" + ExePrograma + "\" /desinstalar");
                k.SetValue("NoModify", 1, RegistryValueKind.DWord);
                k.SetValue("NoRepair", 1, RegistryValueKind.DWord);
                k.SetValue("EstimatedSize", 400, RegistryValueKind.DWord);
            }
        }

        static bool HayIllustrator()
        {
            try
            {
                string[] bases = { Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
                                   Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86) };
                foreach (string b in bases)
                {
                    string adobe = Path.Combine(b, "Adobe");
                    if (!Directory.Exists(adobe)) continue;
                    if (Directory.GetDirectories(adobe, "Adobe Illustrator*").Length > 0) return true;
                }
            }
            catch { }
            return false;
        }

        // ── quitar ─────────────────────────────────────────────────────────────────────────────
        bool borrarProgramaAlCerrar = false;

        protected override void OnFormClosed(FormClosedEventArgs e)
        {
            base.OnFormClosed(e);
            if (!borrarProgramaAlCerrar) return;
            try
            {
                ProcessStartInfo p = new ProcessStartInfo("cmd.exe",
                    "/c timeout /t 2 /nobreak >nul & rmdir /s /q \"" + CarpetaPrograma + "\"");
                p.CreateNoWindow = true;
                p.WindowStyle = ProcessWindowStyle.Hidden;
                p.UseShellExecute = false;
                Process.Start(p);
            }
            catch { }
        }

        void PaginaQuitar()
        {
            tarjeta.SoloUna = true;
            tarjeta.TituloIzq = "Versión instalada";
            tarjeta.Nueva = VersionInstalada() ?? "ninguna";
            Pagina("¿Quitar USER PRO de Illustrator?",
                   "Illustrator deja de recibir las plantillas de USER PRO. Tus archivos no se tocan.",
                   true, NuevoBoton("Quitar", true, Quitar), NuevoBoton("No, dejarlo", false, Salir));
        }

        void Quitar(object s, EventArgs e)
        {
            if (Process.GetProcessesByName("Illustrator").Length > 0)
            {
                Pagina("Primero cerrá Illustrator",
                       "Illustrator está abierto. Guardá lo que estés haciendo, cerralo y tocá «Ya lo cerré».",
                       false, NuevoBoton("Ya lo cerré", true, Quitar), NuevoBoton("Salir", false, Salir));
                return;
            }
            try
            {
                if (Directory.Exists(Destino)) Directory.Delete(Destino, true);
                Registry.CurrentUser.DeleteSubKeyTree(CLAVE_DESINSTALAR, false);
                // la copia de este programa no se puede borrar mientras corre: se borra un
                // instante DESPUÉS de cerrar esta ventana (ver `OnFormClosed`)
                borrarProgramaAlCerrar = true;
                Pagina("Listo", "Se quitó USER PRO de Illustrator.", false, NuevoBoton("Cerrar", true, Salir));
            }
            catch (Exception ex)
            {
                Pagina("Algo no salió bien", "No se pudo quitar.\n\nDetalle: " + ex.Message,
                       false, NuevoBoton("Probar de nuevo", true, Quitar), NuevoBoton("Salir", false, Salir));
            }
        }
    }
}
