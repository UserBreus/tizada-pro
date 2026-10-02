// USER PRO para CorelDRAW — INSTALADOR (Windows) y arranque del PUENTE. Se compila con
// `extension_corel/construir.py`. Es UN solo programa con tres modos:
//   · sin argumentos → la ventana de instalar (la del instalador de Illustrator, adaptada);
//   · `/puente`      → el puente en segundo plano, con su ícono junto al reloj (`Puente.Correr`);
//   · `/desinstalar` → la ventana de quitar (la llama «Aplicaciones instaladas» de Windows).
// No pide permisos de administrador: todo va a la carpeta y al registro del propio usuario.
//   · se copia a %LOCALAPPDATA%\USER PRO\Corel\USER-PRO-Corel.exe;
//   · arranca solo al prender la PC (HKCU\...\Run «USERPRO-Corel» → `/puente`);
//   · se registra en «Aplicaciones instaladas» para poder quitarlo;
//   · deja el puente corriendo al terminar (no hay que reiniciar nada).
// Las piezas de la ventana (Estilo, Boton, TarjetaVersion) son las del instalador de Illustrator.
// C# 5 (el compilador que trae Windows): nada de `$"…"`, `?.` ni `=>` en propiedades.
using System;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Text;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
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
            bool quitar = false, puente = false;
            foreach (string a in args)
            {
                if (a.Equals("/desinstalar", StringComparison.OrdinalIgnoreCase)) quitar = true;
                if (a.Equals("/puente", StringComparison.OrdinalIgnoreCase)) puente = true;
                // el complemento de Corel (la barra «TIZADA PRO»): estos dos modos corren ELEVADOS
                if (a.Equals("/complemento", StringComparison.OrdinalIgnoreCase)) { Environment.Exit(Complemento.InstalarAca()); return; }
                if (a.Equals("/quitar-complemento", StringComparison.OrdinalIgnoreCase)) { Environment.Exit(Complemento.QuitarAca()); return; }
            }
            if (puente) { Puente.Correr(); return; }
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
        const string CLAVE_DESINSTALAR = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\USERPRO-Corel";
        const string CLAVE_ARRANQUE = @"Software\Microsoft\Windows\CurrentVersion\Run";
        const string VALOR_ARRANQUE = "USERPRO-Corel";
        const string NOMBRE = "USER PRO para CorelDRAW";

        readonly Label titulo = new Label();
        readonly Label cuerpo = new Label();
        readonly TarjetaVersion tarjeta = new TarjetaVersion();
        readonly FlowLayoutPanel botones = new FlowLayoutPanel();
        readonly bool modoQuitar;

        static string CarpetaPrograma
        {
            get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "USER PRO", "Corel"); }
        }
        static string ExePrograma
        {
            get { return Path.Combine(CarpetaPrograma, "USER-PRO-Corel.exe"); }
        }

        // La versión instalada (la que anotó el instalador en «Aplicaciones instaladas»), o null.
        static string VersionInstalada()
        {
            try
            {
                using (RegistryKey k = Registry.CurrentUser.OpenSubKey(CLAVE_DESINSTALAR))
                {
                    if (k == null || !File.Exists(ExePrograma)) return null;
                    return (k.GetValue("DisplayVersion") as string) ?? "?";
                }
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
                tit = "Instalar USER PRO en CorelDRAW";
                texto = "Conecta CorelDRAW con USER PRO para crear las plantillas directo en Corel. Tarda unos segundos.";
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
                texto = "Podés volver a instalarla si USER PRO no encuentra a Corel o algo no anda.";
                boton = "Reinstalar";
            }
            else
            {
                tit = "Tenés una versión más nueva";
                texto = "La instalada es más nueva que la de este instalador. Si instalás, vuelve a la anterior.";
                boton = "Instalar igual";
            }
            int mayor;
            string corel = ArmarCorel.Instalado(out mayor);
            if (corel == null) texto += "\n\nNo encontré CorelDRAW en esta computadora: va a funcionar cuando esté instalado (2022 o más nuevo).";
            else if (mayor < 24) texto += "\n\nEsta computadora tiene " + corel + ": hace falta CorelDRAW 2022 o más nuevo.";
            Pagina(tit, texto, true, NuevoBoton(boton, true, Instalar), NuevoBoton("Salir", false, Salir));
        }

        // Cierra el puente que esté corriendo desde la carpeta del programa, proceso por proceso por
        // su PID (nunca «matar todos los que se llamen así»).
        static void CerrarPuente()
        {
            string yo = Path.GetFullPath(ExePrograma);
            int propio = Process.GetCurrentProcess().Id;
            foreach (Process p in Process.GetProcessesByName(Path.GetFileNameWithoutExtension(ExePrograma)))
            {
                try
                {
                    if (p.Id == propio) continue;
                    if (!string.Equals(Path.GetFullPath(p.MainModule.FileName), yo, StringComparison.OrdinalIgnoreCase)) continue;
                    p.Kill();
                    p.WaitForExit(5000);
                }
                catch { }
            }
        }

        void Instalar(object s, EventArgs e)
        {
            Pagina("Instalando…", "Un momento, por favor.", false, null);
            Cursor = Cursors.WaitCursor;
            try
            {
                CerrarPuente();
                Directory.CreateDirectory(CarpetaPrograma);
                string yo = Assembly.GetExecutingAssembly().Location;
                if (!string.Equals(Path.GetFullPath(yo), Path.GetFullPath(ExePrograma), StringComparison.OrdinalIgnoreCase))
                    File.Copy(yo, ExePrograma, true);
                using (RegistryKey k = Registry.CurrentUser.CreateSubKey(CLAVE_ARRANQUE))
                {
                    if (k != null) k.SetValue(VALOR_ARRANQUE, "\"" + ExePrograma + "\" /puente");
                }
                RegistrarDesinstalador();
                Process.Start(ExePrograma, "/puente");
                // el BOTÓN DENTRO DE CORELDRAW (la barra «TIZADA PRO»): va en la carpeta de programas de
                // Corel, así que Windows pide permiso de administrador UNA vez (ver `Complemento`)
                Pagina("Un permiso más", "Para poner el botón «Exportar para TIZADA PRO» dentro de CorelDRAW, Windows te va a pedir permiso. Tocá «Sí».", false, null);
                string sinBoton = Complemento.PedirPermisoY("/complemento");
                Cursor = Cursors.Default;
                tarjeta.SoloUna = true;
                tarjeta.TituloIzq = "Versión instalada";
                tarjeta.Nueva = Version.Texto;
                Pagina("¡Listo!",
                       "Quedó un ícono de USER PRO junto al reloj: arranca solo cada vez que prendés la computadora.\n\n" +
                       (sinBoton == null
                         ? "Cerrá CorelDRAW y volvé a abrirlo: arriba aparece la barra «TIZADA PRO» con el botón «Exportar para TIZADA PRO».\n\n"
                         : "El botón no quedó dentro de CorelDRAW (" + sinBoton + "): mientras tanto aparece pegado a la ventana de Corel. Para agregarlo, volvé a abrir este instalador.\n\n") +
                       "En USER PRO, entrá al molde → Plantilla → «Conectar CorelDRAW».",
                       true, NuevoBoton("Cerrar", true, Salir));
            }
            catch (Exception ex)
            {
                Cursor = Cursors.Default;
                Pagina("Algo no salió bien",
                       "Probá de nuevo.\n\nDetalle (para quien te ayude): " + ex.Message,
                       false, NuevoBoton("Probar de nuevo", true, Instalar), NuevoBoton("Salir", false, Salir));
            }
        }

        static void RegistrarDesinstalador()
        {
            using (RegistryKey k = Registry.CurrentUser.CreateSubKey(CLAVE_DESINSTALAR))
            {
                if (k == null) return;
                k.SetValue("DisplayName", NOMBRE);
                k.SetValue("DisplayVersion", Version.Texto);
                k.SetValue("Publisher", "USER PRO");
                k.SetValue("DisplayIcon", ExePrograma + ",0");
                k.SetValue("InstallLocation", CarpetaPrograma);
                k.SetValue("UninstallString", "\"" + ExePrograma + "\" /desinstalar");
                k.SetValue("NoModify", 1, RegistryValueKind.DWord);
                k.SetValue("NoRepair", 1, RegistryValueKind.DWord);
                k.SetValue("EstimatedSize", 400, RegistryValueKind.DWord);
            }
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
            Pagina("¿Quitar USER PRO de CorelDRAW?",
                   "USER PRO deja de poder crear plantillas en Corel. Tus archivos no se tocan.",
                   true, NuevoBoton("Quitar", true, Quitar), NuevoBoton("No, dejarlo", false, Salir));
        }

        void Quitar(object s, EventArgs e)
        {
            try
            {
                CerrarPuente();
                // el botón de adentro de Corel (pide permiso de administrador, igual que al ponerlo)
                if (Complemento.Instalado()) Complemento.PedirPermisoY("/quitar-complemento");
                using (RegistryKey k = Registry.CurrentUser.OpenSubKey(CLAVE_ARRANQUE, true))
                {
                    if (k != null) k.DeleteValue(VALOR_ARRANQUE, false);
                }
                Registry.CurrentUser.DeleteSubKeyTree(CLAVE_DESINSTALAR, false);
                // la copia de este programa no se puede borrar mientras corre: se borra un instante
                // DESPUÉS de cerrar esta ventana (ver `OnFormClosed`)
                borrarProgramaAlCerrar = true;
                Pagina("Listo", "Se quitó USER PRO de CorelDRAW.", false, NuevoBoton("Cerrar", true, Salir));
            }
            catch (Exception ex)
            {
                Pagina("Algo no salió bien", "No se pudo quitar.\n\nDetalle: " + ex.Message,
                       false, NuevoBoton("Probar de nuevo", true, Quitar), NuevoBoton("Salir", false, Salir));
            }
        }
    }
}
