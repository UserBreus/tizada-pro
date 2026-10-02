// USER PRO para CorelDRAW — el BOTÓN «Exportar para TIZADA PRO» pegado a la ventana de Corel.
//
// 🔴 POR QUÉ UN BOTÓN DEL CONECTOR Y NO UNO DE LA BARRA DE CORE (probado el 2026-09-30 en la 2026):
// Corel no deja registrar macros ni botones desde afuera (el VBE no se expone por COM, `RunMacro` no
// encuentra proyectos nuevos sin reiniciar Corel, y según el foro de Corel el truco de VBA de agregar
// botones a la barra dejó de andar en la 2022); un add-on propio va en Program Files y pide
// administrador. Este botón lo dibuja el conector (que ya corre en segundo plano): es una ventanita
// HIJA de la ventana de Corel —queda encima de Corel y debajo de los demás programas—, sigue a Corel
// cuando se mueve, se esconde si Corel se minimiza o se cierra, y se puede correr arrastrando la
// manija de la izquierda (el lugar se recuerda). Sirve igual de la 2022 a la 2026.
// C# 5 (el compilador de Windows): nada de `$"…"`, `?.` ni `=>` en propiedades.
using System;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Win32;

namespace UserPro
{
    class BotonCorel : Form
    {
        [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
        [DllImport("user32.dll")] static extern bool IsIconic(IntPtr h);
        [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
        [DllImport("user32.dll", EntryPoint = "SetWindowLongPtr")] static extern IntPtr SetWindowLongPtr64(IntPtr h, int i, IntPtr v);
        [StructLayout(LayoutKind.Sequential)] struct RECT { public int Left, Top, Right, Bottom; }
        const int GWLP_HWNDPARENT = -8;
        const string CLAVE = @"Software\USER PRO\Corel";

        readonly Boton boton = new Boton();
        readonly Panel manija = new Panel();
        readonly System.Windows.Forms.Timer reloj = new System.Windows.Forms.Timer();
        readonly Action<string, string, bool> avisar;
        IntPtr dueno = IntPtr.Zero;
        int margenDer = 90, margenAbajo = 80;           // lugar respecto de la esquina de abajo a la derecha de Corel
        bool arrastrando; Point desde; int derDesde, abajoDesde;
        bool ocupado;
        public bool Activo = true;
        int miradoComplemento; bool hayComplemento;                      // lo apaga el menú del ícono («Mostrar el botón en Corel»)

        public BotonCorel(Action<string, string, bool> avisar)
        {
            this.avisar = avisar;
            FormBorderStyle = FormBorderStyle.None;
            ShowInTaskbar = false;
            StartPosition = FormStartPosition.Manual;
            BackColor = Estilo.Fondo;
            AutoScaleMode = AutoScaleMode.Dpi;
            Size = new Size(262, 46);
            try
            {
                using (RegistryKey k = Registry.CurrentUser.OpenSubKey(CLAVE))
                {
                    if (k != null)
                    {
                        margenDer = Convert.ToInt32(k.GetValue("BotonDer", margenDer));
                        margenAbajo = Convert.ToInt32(k.GetValue("BotonAbajo", margenAbajo));
                        Activo = Convert.ToInt32(k.GetValue("BotonVisible", 1)) != 0;
                    }
                }
            }
            catch { }

            manija.Dock = DockStyle.Left;
            manija.Width = 16;
            manija.Cursor = Cursors.SizeAll;
            manija.BackColor = Estilo.Fondo;
            manija.Paint += delegate (object s, PaintEventArgs e)
            {
                using (SolidBrush b = new SolidBrush(Estilo.Suave))
                    for (int y = 13; y <= 29; y += 5) { e.Graphics.FillEllipse(b, 5, y, 3, 3); e.Graphics.FillEllipse(b, 9, y, 3, 3); }
            };
            manija.MouseDown += delegate (object s, MouseEventArgs e) { arrastrando = true; desde = Cursor.Position; derDesde = margenDer; abajoDesde = margenAbajo; };
            manija.MouseMove += delegate (object s, MouseEventArgs e)
            {
                if (!arrastrando) return;
                margenDer = Math.Max(0, derDesde - (Cursor.Position.X - desde.X));
                margenAbajo = Math.Max(0, abajoDesde - (Cursor.Position.Y - desde.Y));
                Ubicar();
            };
            manija.MouseUp += delegate (object s, MouseEventArgs e) { arrastrando = false; Guardar(); };

            boton.Principal = true;
            boton.Text = "Exportar para TIZADA PRO";
            boton.Font = new Font("Segoe UI Semibold", 10.5F);
            boton.Dock = DockStyle.Fill;
            boton.Click += delegate (object s, EventArgs e) { Exportar(); };
            ToolTip tt = new ToolTip();
            tt.SetToolTip(boton, "Guarda el PDF que se sube a TIZADA PRO, con todos los ajustes que necesita el sistema.");
            tt.SetToolTip(manija, "Arrastrá para correr el botón.");
            Controls.Add(boton);
            Controls.Add(manija);

            reloj.Interval = 400;
            reloj.Tick += delegate (object s, EventArgs e) { Seguir(); };
            reloj.Start();
        }

        // Sin tomar el foco (Corel sigue siendo la ventana activa) y sin aparecer en Alt+Tab
        protected override bool ShowWithoutActivation { get { return true; } }
        protected override CreateParams CreateParams
        {
            get
            {
                CreateParams cp = base.CreateParams;
                cp.ExStyle |= 0x08000000 /*WS_EX_NOACTIVATE*/ | 0x00000080 /*WS_EX_TOOLWINDOW*/;
                return cp;
            }
        }

        protected override void OnHandleCreated(EventArgs e)
        {
            base.OnHandleCreated(e);
            using (GraphicsPath p = Estilo.Redondo(new RectangleF(0, 0, Width, Height), 12F)) Region = new Region(p);
        }

        void Guardar()
        {
            try
            {
                using (RegistryKey k = Registry.CurrentUser.CreateSubKey(CLAVE))
                {
                    if (k == null) return;
                    k.SetValue("BotonDer", margenDer, RegistryValueKind.DWord);
                    k.SetValue("BotonAbajo", margenAbajo, RegistryValueKind.DWord);
                    k.SetValue("BotonVisible", Activo ? 1 : 0, RegistryValueKind.DWord);
                }
            }
            catch { }
        }

        public void CambiarVisible(bool si) { Activo = si; Guardar(); Seguir(); }

        static IntPtr VentanaCorel()
        {
            foreach (Process p in Process.GetProcessesByName("CorelDRW"))
            {
                try { if (p.MainWindowHandle != IntPtr.Zero) return p.MainWindowHandle; } catch { }
            }
            return IntPtr.Zero;
        }

        void Ubicar()
        {
            RECT r;
            if (dueno == IntPtr.Zero || !GetWindowRect(dueno, out r)) return;
            int x = Math.Max(r.Left, r.Right - Width - margenDer);
            int y = Math.Max(r.Top, r.Bottom - Height - margenAbajo);
            if (Left != x || Top != y) Location = new Point(x, y);
        }

        void Seguir()
        {
            // con el complemento en Corel (la barra «TIZADA PRO»), este botón sobra: se mira cada 10 s
            if (Environment.TickCount - miradoComplemento > 10000 || miradoComplemento == 0)
            {
                miradoComplemento = Environment.TickCount;
                hayComplemento = FlujoExportar.HayComplemento();
            }
            IntPtr h = Activo && !hayComplemento ? VentanaCorel() : IntPtr.Zero;
            if (h == IntPtr.Zero || IsIconic(h) || !IsWindowVisible(h)) { if (Visible) Hide(); return; }
            if (h != dueno)
            {
                dueno = h;
                // HIJA de la ventana de Corel: queda siempre encima de Corel (y sólo de Corel)
                SetWindowLongPtr64(Handle, GWLP_HWNDPARENT, h);
            }
            if (!arrastrando) Ubicar();
            if (!Visible) Show();
        }

        void Listo()
        {
            ocupado = false;
            boton.Text = "Exportar para TIZADA PRO";
            boton.Enabled = true;
        }

        // El mismo flujo que el botón de la barra de Corel (`FlujoExportar`): revisa, PREGUNTA DÓNDE
        // GUARDAR y exporta.
        public void Exportar()
        {
            if (ocupado) return;
            ocupado = true;
            boton.Text = "Exportando…";
            boton.Enabled = false;
            try
            {
                ResultadoExportar r = FlujoExportar.Correr();
                if (r.Ok) avisar("Listo para subir a TIZADA PRO", System.IO.Path.GetFileName(r.Ruta), false);
            }
            finally { Listo(); }
        }
    }
}
