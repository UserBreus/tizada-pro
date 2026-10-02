// USER PRO para CorelDRAW — instala / quita el COMPLEMENTO de Corel (la barra «TIZADA PRO» con el
// botón «Exportar para TIZADA PRO», ver `complemento/AppUI.xslt`).
//
// Corel carga los complementos SÓLO desde su carpeta de programas (<CorelDRAW>\Programs64\Addons), que
// es de Windows: escribir ahí pide permiso de administrador. Por eso este paso corre APARTE, elevado
// (el instalador se relanza con `/complemento` y Windows pregunta UNA vez); todo lo demás del
// conector sigue sin pedir permisos. Se instala en TODOS los CorelDRAW 2022+ de la PC.
// Si el usuario no da el permiso, el conector sigue funcionando y el botón aparece pegado a la
// ventana de Corel (`BotonCorel`) en vez de estar en la barra.
// C# 5 (el compilador de Windows): nada de `$"…"`, `?.` ni `=>` en propiedades.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using Microsoft.Win32;

namespace UserPro
{
    static class Complemento
    {
        const string CARPETA = "TizadaPro";
        static readonly string[] ARCHIVOS = { "AppUI.xslt", "UserUI.xslt", "CorelDrw.addon", "TizadaPro.dll" };

        /// Las carpetas Programs64 de cada CorelDRAW 2022+ instalado (según «Aplicaciones instaladas»).
        public static List<string> CarpetasCorel()
        {
            List<string> out_ = new List<string>();
            foreach (RegistryView vista in new[] { RegistryView.Registry64, RegistryView.Registry32 })
            {
                try
                {
                    using (RegistryKey baseK = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, vista))
                    using (RegistryKey u = baseK.OpenSubKey(@"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"))
                    {
                        if (u == null) continue;
                        foreach (string n in u.GetSubKeyNames())
                        {
                            using (RegistryKey k = u.OpenSubKey(n))
                            {
                                string nombre = k == null ? null : k.GetValue("DisplayName") as string;
                                string lugar = k == null ? null : k.GetValue("InstallLocation") as string;
                                if (nombre == null || lugar == null) continue;
                                if (!System.Text.RegularExpressions.Regex.IsMatch(nombre, @"^CorelDRAW Graphics Suite 20\d\d$")) continue;
                                string p64 = Path.Combine(lugar.Trim(), "Programs64");
                                string exe = Path.Combine(p64, "CorelDRW.exe");
                                if (!File.Exists(exe)) continue;
                                try { if (FileVersionInfo.GetVersionInfo(exe).FileMajorPart < 24) continue; } catch { continue; }
                                string full = Path.GetFullPath(p64).TrimEnd('\\');
                                bool ya = false;
                                foreach (string x in out_) if (string.Equals(x, full, StringComparison.OrdinalIgnoreCase)) ya = true;
                                if (!ya) out_.Add(full);
                            }
                        }
                    }
                }
                catch { }
            }
            return out_;
        }

        public static bool Instalado()
        {
            foreach (string p in CarpetasCorel())
                if (File.Exists(Path.Combine(p, "Addons", CARPETA, "CorelDrw.addon"))) return true;
            return false;
        }

        /// Modo `/complemento` (ya elevado): copia los archivos. Devuelve el código de salida (0 = bien).
        public static int InstalarAca()
        {
            int bien = 0, mal = 0;
            foreach (string p in CarpetasCorel())
            {
                try
                {
                    string dest = Path.Combine(p, "Addons", CARPETA);
                    Directory.CreateDirectory(dest);
                    // restos de instalaciones anteriores con Corel abierto (ver abajo)
                    foreach (string viejo in Directory.GetFiles(dest, "*.viejo-*"))
                    {
                        try { File.Delete(viejo); } catch { }
                    }
                    foreach (string a in ARCHIVOS)
                    {
                        string ruta = Path.Combine(dest, a);
                        // con Corel abierto, la DLL del botón está EN USO y no se puede pisar; Windows sí
                        // deja renombrarla: la nueva queda en su lugar y Corel la toma al reiniciarse
                        if (File.Exists(ruta))
                        {
                            try { File.Delete(ruta); }
                            catch { File.Move(ruta, ruta + ".viejo-" + DateTime.Now.Ticks); }
                        }
                        using (Stream s = Assembly.GetExecutingAssembly().GetManifestResourceStream("complemento." + a))
                        using (FileStream f = File.Create(ruta))
                        {
                            if (s != null) s.CopyTo(f);
                        }
                    }
                    bien++;
                }
                catch { mal++; }
            }
            return mal > 0 ? 2 : (bien > 0 ? 0 : 3);
        }

        /// Modo `/quitar-complemento` (ya elevado).
        public static int QuitarAca()
        {
            int mal = 0;
            foreach (string p in CarpetasCorel())
            {
                try { string d = Path.Combine(p, "Addons", CARPETA); if (Directory.Exists(d)) Directory.Delete(d, true); }
                catch { mal++; }
            }
            return mal > 0 ? 2 : 0;
        }

        /// Desde el instalador (sin permisos): relanza este programa elevado. null = bien; si no, el motivo.
        public static string PedirPermisoY(string modo)
        {
            if (CarpetasCorel().Count == 0) return "no encontré CorelDRAW 2022 o más nuevo en esta computadora";
            try
            {
                ProcessStartInfo i = new ProcessStartInfo(Assembly.GetExecutingAssembly().Location, modo);
                i.Verb = "runas";                  // Windows pregunta el permiso de administrador
                i.UseShellExecute = true;
                using (Process pr = Process.Start(i))
                {
                    pr.WaitForExit();
                    return pr.ExitCode == 0 ? null : "no se pudieron copiar los archivos del botón (código " + pr.ExitCode + ")";
                }
            }
            catch (Win32Exception e)
            {
                if (e.NativeErrorCode == 1223) return "no se dio el permiso";      // tocaron «No» en la pregunta de Windows
                return e.Message;
            }
        }
    }
}
