// USER PRO para CorelDRAW — EL FLUJO de «Exportar para TIZADA PRO», el mismo desde los tres lugares:
// el botón de la barra de Corel (complemento → `/exportar-corel`), el botón pegado a Corel (si el
// complemento no está) y el menú del ícono junto al reloj.
//   1. revisa el documento abierto (`ExportarCorel.Analizar`, no lo toca) y, si hay algo para avisar,
//      pregunta si exporta igual;
//   2. PREGUNTA DÓNDE GUARDAR (pedido del usuario 2026-09-30): la ventana «Guardar como» de Windows,
//      encima de Corel, abierta en la carpeta del .cdr y con el nombre «<nombre> - para TIZADA.pdf»;
//   3. publica el PDF con los ajustes fijos (`ExportarCorel.Exportar`) y abre la carpeta con el PDF.
// Corre en el hilo de la pantalla del conector (los diálogos); lo de Corel va por `HiloCorel`.
// C# 5 (el compilador de Windows): nada de `$"…"`, `?.` ni `=>` en propiedades.
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace UserPro
{
    class ResultadoExportar { public bool Ok, Cancelado; public string Ruta, Error; }

    // Una ventana de otro programa (Corel) como dueña de nuestros diálogos: así salen ENCIMA de Corel
    class VentanaAjena : IWin32Window
    {
        readonly IntPtr h;
        public VentanaAjena(IntPtr h) { this.h = h; }
        public IntPtr Handle { get { return h; } }
    }

    static class FlujoExportar
    {
        [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
        static bool corriendo;

        public static IntPtr VentanaCorel()
        {
            foreach (Process p in Process.GetProcessesByName("CorelDRW"))
            {
                try { if (p.MainWindowHandle != IntPtr.Zero) return p.MainWindowHandle; } catch { }
            }
            return IntPtr.Zero;
        }

        /// ¿El complemento (la barra «TIZADA PRO» dentro de Corel) está en el Corel que corre ahora?
        public static bool HayComplemento()
        {
            foreach (Process p in Process.GetProcessesByName("CorelDRW"))
            {
                try
                {
                    string dir = Path.GetDirectoryName(p.MainModule.FileName);              // …\Programs64
                    if (File.Exists(Path.Combine(dir, "Addons", "TizadaPro", "CorelDrw.addon"))) return true;
                }
                catch { }
            }
            return false;
        }

        static string Motivo(Exception e)
        {
            while (e.InnerException != null && e is System.Reflection.TargetInvocationException) e = e.InnerException;
            COMException ce = e as COMException;
            if (ce != null && ((uint)ce.ErrorCode == 0x80010001 || (uint)ce.ErrorCode == 0x8001010A))
                return "CorelDRAW está ocupado (¿hay una ventana abierta en Corel?). Cerrala y probá de nuevo.";
            return e.Message;
        }

        /// Todo el flujo. Llamar desde el hilo de la pantalla del conector.
        public static ResultadoExportar Correr()
        {
            ResultadoExportar r = new ResultadoExportar();
            if (corriendo) { r.Error = "ya hay una exportación en curso."; return r; }
            corriendo = true;
            try
            {
                IntPtr hc = VentanaCorel();
                IWin32Window dueno = hc != IntPtr.Zero ? (IWin32Window)new VentanaAjena(hc) : null;
                AnalisisExportar a;
                try { a = HiloCorel.Hacer(delegate () { return ExportarCorel.Analizar(); }); }
                catch (Exception e) { r.Error = Motivo(e); MessageBox.Show(dueno, r.Error, "Exportar para TIZADA PRO", MessageBoxButtons.OK, MessageBoxIcon.Warning); return r; }
                if (a.Avisos.Count > 0)
                {
                    string txt = "Antes de exportar «" + a.Titulo + "», fijate:\n\n• " + string.Join("\n\n• ", a.Avisos.ToArray()) + "\n\n¿Exportar igual?";
                    if (MessageBox.Show(dueno, txt, "Exportar para TIZADA PRO", MessageBoxButtons.YesNo, MessageBoxIcon.Warning) != DialogResult.Yes)
                    { r.Cancelado = true; return r; }
                }
                string ruta;
                using (SaveFileDialog d = new SaveFileDialog())
                {
                    d.Title = "Guardar el PDF para TIZADA PRO";
                    d.Filter = "PDF para TIZADA PRO (*.pdf)|*.pdf";
                    d.DefaultExt = "pdf";
                    d.AddExtension = true;
                    d.OverwritePrompt = true;                   // si ya existe, Windows pregunta antes de reemplazar
                    string carpeta = Path.GetDirectoryName(a.Destino);
                    try { Directory.CreateDirectory(carpeta); } catch { }
                    d.InitialDirectory = carpeta;
                    d.FileName = Path.GetFileName(a.Destino);
                    if (d.ShowDialog(dueno) != DialogResult.OK) { r.Cancelado = true; return r; }
                    ruta = d.FileName;
                }
                try { HiloCorel.Hacer(delegate () { ExportarCorel.Exportar(ruta); return true; }); }
                catch (Exception e) { r.Error = Motivo(e); MessageBox.Show(dueno, r.Error, "No se pudo exportar", MessageBoxButtons.OK, MessageBoxIcon.Warning); return r; }
                r.Ok = true;
                r.Ruta = ruta;
                // la carpeta abierta con el PDF elegido: ése es el que se sube como arte
                try { Process.Start("explorer.exe", "/select,\"" + ruta + "\""); } catch { }
                if (hc != IntPtr.Zero) { try { SetForegroundWindow(hc); } catch { } }
                return r;
            }
            finally { corriendo = false; }
        }
    }
}
