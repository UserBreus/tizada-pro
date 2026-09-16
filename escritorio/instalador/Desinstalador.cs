// DESINSTALADOR DE TIZADA PRO. Lo deja el instalador en la carpeta del programa y lo lanza
// «Agregar o quitar programas» de Windows.
//
// 🔴 LOS DATOS SE CONSERVAN SI NO SE PIDE LO CONTRARIO. Moldes, diseños y tizadas viven en
// %LOCALAPPDATA%\TIZADA PRO: sólo se borran si el usuario tilda la casilla (que arranca SIN tildar).
// La base `TizadaPro_Escritorio` de SQL Server no se toca nunca desde acá.
// ⚠️ C# 5 (el compilador de .NET Framework): nada de $"", ?. ni => en propiedades.
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Win32;

namespace TizadaPro
{
    static class Desinstalar
    {
        const string Nombre = "TIZADA PRO";
        const string ClaveDesinstalar = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\TizadaPro";

        [DllImport("user32.dll")]
        static extern bool SetProcessDPIAware();

        [STAThread]
        static void Main()
        {
            try { SetProcessDPIAware(); } catch { }
            Application.EnableVisualStyles();
            string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string programa = Path.Combine(local, "Programs", Nombre);
            string datos = Path.Combine(local, Nombre);

            Form f = new Form();
            f.Text = "Desinstalar " + Nombre;
            f.ClientSize = new Size(520, 250);
            f.FormBorderStyle = FormBorderStyle.FixedDialog;
            f.MaximizeBox = false;
            f.StartPosition = FormStartPosition.CenterScreen;
            f.BackColor = Color.White;
            f.Font = new Font("Segoe UI", 10f);

            Label l = new Label();
            l.Text = "Se va a quitar TIZADA PRO de esta PC.\n\nTus moldes, diseños y tizadas quedan guardados en:\n" + datos +
                     "\n(si lo volvés a instalar, aparecen de nuevo)";
            l.SetBounds(24, 18, 480, 110);
            f.Controls.Add(l);

            CheckBox chk = new CheckBox();
            chk.Text = "Borrar también mis datos (no se puede deshacer)";
            chk.ForeColor = Color.FromArgb(190, 40, 40);
            chk.SetBounds(24, 136, 480, 26);
            f.Controls.Add(chk);

            Button ok = new Button();
            ok.Text = "Desinstalar";
            ok.SetBounds(372, 196, 128, 38);
            ok.DialogResult = DialogResult.OK;
            f.Controls.Add(ok);
            Button no = new Button();
            no.Text = "Cancelar";
            no.SetBounds(236, 196, 128, 38);
            no.DialogResult = DialogResult.Cancel;
            f.Controls.Add(no);
            f.AcceptButton = no;
            f.CancelButton = no;
            if (f.ShowDialog() != DialogResult.OK) return;
            bool borrarDatos = chk.Checked;

            // cerrar la app si está abierta
            foreach (Process p in Process.GetProcessesByName(Nombre)) { try { p.CloseMainWindow(); } catch { } }
            DateTime hasta = DateTime.Now.AddSeconds(10);
            while (DateTime.Now < hasta && Process.GetProcessesByName(Nombre).Length > 0) Thread.Sleep(300);
            foreach (Process p in Process.GetProcessesByName(Nombre)) { try { p.Kill(); p.WaitForExit(5000); } catch { } }

            foreach (string lnk in new[] {
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs), Nombre + ".lnk"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), Nombre + ".lnk") })
            {
                try { if (File.Exists(lnk)) File.Delete(lnk); } catch { }
            }
            try { Registry.CurrentUser.DeleteSubKeyTree(ClaveDesinstalar, false); } catch { }
            if (borrarDatos)
            {
                try { if (Directory.Exists(datos)) Directory.Delete(datos, true); }
                catch (Exception e) { MessageBox.Show("No se pudieron borrar todos los datos: " + e.Message, Nombre); }
            }

            // Este mismo archivo está adentro de la carpeta del programa: la borra una consola oculta
            // un instante después de que este proceso termina.
            // El aviso va ANTES: mientras está en pantalla este proceso sigue vivo y su archivo no se
            // puede borrar.
            MessageBox.Show("TIZADA PRO se desinstaló.", Nombre);
            ProcessStartInfo psi = new ProcessStartInfo("cmd.exe",
                "/c ping 127.0.0.1 -n 3 > nul & rmdir /s /q \"" + programa + "\"");
            psi.CreateNoWindow = true;
            psi.UseShellExecute = false;
            psi.WindowStyle = ProcessWindowStyle.Hidden;
            try { Process.Start(psi); } catch { }
        }
    }
}
