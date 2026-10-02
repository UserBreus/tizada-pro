// USER PRO para CorelDRAW — EL BOTÓN «Exportar para TIZADA PRO» DENTRO DE LA BARRA DE COREL.
//
// Se compila aparte como `TizadaPro.dll` (`construir.py`) y Corel lo carga en la barra «TIZADA PRO»
// como control propio (`type="wpfhost"` en `AppUI.xslt`). Así el botón muestra el ÍCONO de TIZADA PRO
// (en verde, el color de Corel) y el texto entero: un botón de Corel común sin DLL sólo puede usar
// los íconos internos de Corel, y quedaba una flechita sola (queja del usuario 2026-10-01).
//
// El botón NO exporta: le pide al conector (el programa junto al reloj, 127.0.0.1:47851) que lo
// haga con `POST /exportar-corel`. Hay UN solo flujo de exportar (`puente/FlujoExportar.cs`: revisa,
// pregunta la carpeta, publica con los ajustes fijos); el botón flotante y el menú del ícono usan
// el mismo. El pedido va en un hilo aparte: Corel no se congela mientras la persona elige carpeta.
//
// Corel 2022–2026 corre .NET Framework 4 (las interop de Corel son v4.0.30319): este control no usa
// nada de Corel, sólo WPF, así que sirve igual en todas. C# 5 (el compilador de Windows).
using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;

namespace UserPro.Corel
{
    public class BotonTizada : UserControl
    {
        const string URL = "http://127.0.0.1:47851/exportar-corel";
        const string TEXTO = "Exportar para TIZADA PRO";

        // el verde de Corel (los mismos tonos que el ícono del instalador y el botón de la web)
        static readonly Brush FONDO = Pintura(232, 246, 236), FONDO_ENCIMA = Pintura(211, 240, 219),
                              FONDO_APRETADO = Pintura(191, 232, 202), BORDE = Pintura(60, 185, 80),
                              LETRA = Pintura(18, 92, 40);

        readonly Border caja;
        readonly TextBlock texto;
        bool ocupado;

        public BotonTizada() : this(null) { }

        // Corel le pasa su objeto Application: no se usa (todo lo hace el conector)
        public BotonTizada(object app)
        {
            Focusable = false;
            Cursor = Cursors.Hand;
            ToolTip = "Exportar para TIZADA PRO: te pregunta en qué carpeta guardar y deja el PDF listo para subir, con todos los ajustes que necesita el sistema.";

            StackPanel fila = new StackPanel();
            fila.Orientation = Orientation.Horizontal;
            fila.VerticalAlignment = VerticalAlignment.Center;
            Image icono = new Image();
            icono.Source = Isotipo();
            icono.Width = 18;
            icono.Height = 18;
            icono.Margin = new Thickness(0, 0, 6, 0);
            RenderOptions.SetBitmapScalingMode(icono, BitmapScalingMode.HighQuality);
            fila.Children.Add(icono);
            texto = new TextBlock();
            texto.Text = TEXTO;
            texto.FontFamily = new FontFamily("Segoe UI");
            texto.FontSize = 12;
            texto.FontWeight = FontWeights.SemiBold;
            texto.Foreground = LETRA;
            texto.VerticalAlignment = VerticalAlignment.Center;
            fila.Children.Add(texto);

            caja = new Border();
            caja.Child = fila;
            caja.Background = FONDO;
            caja.BorderBrush = BORDE;
            caja.BorderThickness = new Thickness(1);
            caja.CornerRadius = new CornerRadius(5);
            caja.Padding = new Thickness(8, 2, 10, 2);
            caja.Margin = new Thickness(3, 2, 3, 2);
            caja.Height = 26;
            Content = caja;

            MouseEnter += delegate { if (!ocupado) caja.Background = FONDO_ENCIMA; };
            MouseLeave += delegate { if (!ocupado) caja.Background = FONDO; };
            MouseLeftButtonDown += delegate (object s, MouseButtonEventArgs e) { if (!ocupado) caja.Background = FONDO_APRETADO; e.Handled = true; };
            MouseLeftButtonUp += delegate (object s, MouseButtonEventArgs e) { e.Handled = true; Tocar(); };
        }

        static Brush Pintura(byte r, byte g, byte b)
        {
            SolidColorBrush p = new SolidColorBrush(Color.FromRgb(r, g, b));
            p.Freeze();
            return p;
        }

        static ImageSource Isotipo()
        {
            try
            {
                using (Stream s = Assembly.GetExecutingAssembly().GetManifestResourceStream("isotipo.png"))
                {
                    BitmapImage im = new BitmapImage();
                    im.BeginInit();
                    im.CacheOption = BitmapCacheOption.OnLoad;
                    im.StreamSource = s;
                    im.EndInit();
                    im.Freeze();
                    return im;
                }
            }
            catch { return null; }
        }

        void Tocar()
        {
            if (ocupado) return;
            ocupado = true;
            caja.Background = FONDO_APRETADO;
            caja.Opacity = 0.75;
            texto.Text = "Exportando…";
            ThreadPool.QueueUserWorkItem(delegate
            {
                string r = Pedir();
                if (r == null && ArrancarConector())
                {
                    Thread.Sleep(3000);                 // el conector tarda un poco en atender
                    r = Pedir();
                }
                Dispatcher.BeginInvoke(new Action(delegate { Terminar(r); }));
            });
        }

        // null = el conector no contestó (no está abierto)
        static string Pedir()
        {
            try
            {
                HttpWebRequest q = (HttpWebRequest)WebRequest.Create(URL);
                q.Method = "POST";
                q.Proxy = null;                          // es esta misma PC: nunca por un proxy
                q.ContentLength = 0;
                q.Timeout = 60 * 60 * 1000;              // la persona puede tardar en elegir la carpeta
                q.ReadWriteTimeout = 60 * 60 * 1000;
                using (WebResponse w = q.GetResponse())
                using (StreamReader sr = new StreamReader(w.GetResponseStream(), Encoding.UTF8))
                    return sr.ReadToEnd();
            }
            catch { return null; }
        }

        // Si el conector no está abierto (lo cerraron desde el ícono), se abre solo una vez.
        static bool ArrancarConector()
        {
            try
            {
                string exe = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                                          "USER PRO", "Corel", "USER-PRO-Corel.exe");
                if (!File.Exists(exe)) return false;
                Process.Start(exe, "/puente");
                return true;
            }
            catch { return false; }
        }

        void Terminar(string r)
        {
            ocupado = false;
            caja.Opacity = 1;
            caja.Background = IsMouseOver ? FONDO_ENCIMA : FONDO;
            texto.Text = TEXTO;
            if (r == null)
            {
                MessageBox.Show("No pude hablar con el programa USER PRO para CorelDRAW (el ícono verde junto al reloj).\n\n" +
                                "Abrilo desde el menú Inicio («USER PRO para CorelDRAW») y tocá el botón de nuevo. " +
                                "Si no está instalado, bajalo desde TIZADA PRO: «Conectores».",
                                "Exportar para TIZADA PRO", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }
            // los avisos y errores ya los mostró el conector; si salió bien, una confirmación corta
            if (r.Replace(" ", "").Contains("\"ok\":true"))
            {
                texto.Text = "✓ Listo para subir";
                DispatcherTimer t = new DispatcherTimer();
                t.Interval = TimeSpan.FromSeconds(4);
                t.Tick += delegate { t.Stop(); if (!ocupado) texto.Text = TEXTO; };
                t.Start();
            }
        }
    }
}
