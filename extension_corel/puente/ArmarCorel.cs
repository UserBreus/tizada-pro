// USER PRO para CorelDRAW — ARMA LA PLANTILLA EN COREL por COM (el equivalente de `tizada.jsx`).
//
// El plan llega de TIZADA PRO (navegador de esta PC, `frontend/src/motor/molde/corel.js → planCorel`)
// y es el MISMO que se le manda a Illustrator, pasado a «una PÁGINA por mesa»: en Corel cada mesa de
// trabajo es una página (no hay un lienzo común con mesas acomodadas), así que no hay tope de lienzo
// (una página llega a 45 m) y todo entra en UN archivo a tamaño real.
//
// Qué arma (lo que el motor lee del arte, ver COREL_REFERENCIA.md):
//   · una PÁGINA por mesa, del tamaño de la caja del diseño, con el nombre de la mesa;
//   · en CADA página las capas, de abajo hacia arriba: diseño · Editable … · personalización · guias
//     (la «Capa 1» con que nace la página se renombra a la primera: si quedara vacía sería ruido);
//   · en «guias» el CONTORNO de la pieza y su NOMBRE como texto vivo (con ese texto el motor asigna
//     la mesa a su pieza). En Corel no hay «volver guía» un trazado: la capa queda BLOQUEADA y el
//     sistema descarta la capa «guias» al imprimir, como con Illustrator;
//   · en «diseño» el FONDO rojo clarito de la mesa.
// Guarda en Documentos › USER PRO › Plantillas como .cdr VERSIÓN 2022 (v24): abre de la 2022 en adelante.
//
// 🔴 COM EN UN SOLO HILO STA: Corel rechaza llamadas desde otros hilos. Todo pasa por `HiloCorel`,
// que además registra un filtro de mensajes: si Corel está ocupado (un diálogo abierto, guardando)
// contesta «reintentá» y se reintenta un rato en vez de fallar.
// C# 5 (el compilador de Windows): nada de `$"…"`, `?.` ni `=>` en propiedades.
using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

namespace UserPro
{
    // ── el plan ya validado (ver `Plan.Sanear`) ──────────────────────────────────────────────────
    class CapaPlan { public string Nombre; public bool Bloqueada; public int[] Color; }
    class SubCamino { public List<double[]> P = new List<double[]>(); public bool C; }
    // `Punteado` (MOLDE A MEDIDA, MAPA 623): el margen/dobladillo, una línea de rayas; null = contorno
    class CaminoPlan { public int Capa; public List<SubCamino> Sub = new List<SubCamino>(); public double Ancho; public double[] Color; public bool Punteado; }
    class TextoPlan { public int Capa; public string T; public double X, Y, Tam; public bool Vector; }
    class FondoPlan { public int Capa; public double[] Color; }
    class PaginaPlan
    {
        public string Nombre; public double W, H;
        public bool ConLugar; public double Cx, Cy;       // el CENTRO de la mesa en el lienzo del molde (pt, «y» hacia abajo)
        public FondoPlan Fondo;
        public List<CaminoPlan> Caminos = new List<CaminoPlan>();
        public List<TextoPlan> Textos = new List<TextoPlan>();
    }
    class Plan
    {
        public string Titulo, Archivo;
        public int Activa;
        public List<CapaPlan> Capas = new List<CapaPlan>();
        public List<PaginaPlan> Paginas = new List<PaginaPlan>();
        public string GuardarEn;

        // 1800" = el tamaño máximo de página de Corel (45,72 m), en puntos
        const double TOPE_PAGINA_PT = 1800 * 72;

        static double Num(object v)
        {
            double n;
            try { n = Convert.ToDouble(v, CultureInfo.InvariantCulture); }
            catch { throw new Exception("número inválido en el plan"); }
            if (double.IsNaN(n) || double.IsInfinity(n)) throw new Exception("número inválido en el plan");
            return n;
        }
        static string Txt(object v, int tope)
        {
            string s = v == null ? "" : Convert.ToString(v, CultureInfo.InvariantCulture);
            return s.Length > tope ? s.Substring(0, tope) : s;
        }
        static object[] Lista(object v, int tope, string que)
        {
            object[] a = v as object[];
            if (a == null)
            {
                System.Collections.ArrayList al = v as System.Collections.ArrayList;
                if (al != null) a = al.ToArray();
            }
            if (a == null) throw new Exception("falta " + que + " en el plan");
            if (a.Length > tope) throw new Exception("demasiados " + que + " (" + a.Length + ")");
            return a;
        }
        static Dictionary<string, object> Dic(object v, string que)
        {
            Dictionary<string, object> d = v as Dictionary<string, object>;
            if (d == null) throw new Exception(que + " no es un objeto");
            return d;
        }
        static object Get(Dictionary<string, object> d, string k) { object v; return d.TryGetValue(k, out v) ? v : null; }

        // Un nombre de archivo válido en Windows (sin \ / : * ? " < > | ni caracteres de control)
        public static string NombreArchivo(string v)
        {
            StringBuilder sb = new StringBuilder();
            foreach (char c in v ?? "") sb.Append("\\/:*?\"<>|".IndexOf(c) >= 0 || c < 32 ? ' ' : c);
            string n = System.Text.RegularExpressions.Regex.Replace(sb.ToString(), @"\s+", " ").Trim().TrimEnd('.', ' ');
            if (n.Length > 100) n = n.Substring(0, 100);
            return n.Length > 0 ? n : "Plantilla";
        }

        // 🔴 SEGURIDAD: lo que llega por la red NUNCA se ejecuta; se lee campo por campo, sólo números y
        // textos, con topes (los mismos que el puente de Illustrator, `sanear` en puente.js).
        public static Plan Sanear(object crudo)
        {
            Dictionary<string, object> p = Dic(crudo, "el plan");
            Plan o = new Plan();
            o.Titulo = Txt(Get(p, "titulo"), 120);
            o.Archivo = NombreArchivo(Txt(Get(p, "archivo") ?? Get(p, "titulo"), 200));
            o.Activa = (int)Math.Max(0, Math.Floor(Num(Get(p, "activa") ?? 0)));
            foreach (object co in Lista(Get(p, "capas"), 60, "capas"))
            {
                Dictionary<string, object> c = Dic(co, "una capa");
                object[] col = Lista(Get(c, "color") ?? new object[] { 128, 128, 128 }, 3, "color");
                o.Capas.Add(new CapaPlan {
                    Nombre = Txt(Get(c, "nombre"), 120), Bloqueada = Convert.ToBoolean(Get(c, "bloqueada") ?? false),
                    Color = new int[] { (int)Num(col[0]), (int)Num(col[1]), (int)Num(col[2]) } });
            }
            if (o.Capas.Count == 0) throw new Exception("el plan no trae capas");
            int caminos = 0, puntos = 0, textos = 0;
            foreach (object po in Lista(Get(p, "paginas"), 5000, "páginas"))
            {
                Dictionary<string, object> pg = Dic(po, "una página");
                PaginaPlan pp = new PaginaPlan { Nombre = Txt(Get(pg, "nombre"), 120), W = Num(Get(pg, "w")), H = Num(Get(pg, "h")) };
                if (Get(pg, "cx") != null && Get(pg, "cy") != null) { pp.ConLugar = true; pp.Cx = Num(Get(pg, "cx")); pp.Cy = Num(Get(pg, "cy")); }
                if (pp.W <= 0 || pp.H <= 0 || pp.W > TOPE_PAGINA_PT || pp.H > TOPE_PAGINA_PT)
                    throw new Exception("la mesa «" + pp.Nombre + "» no entra en una página de Corel (máximo 45 m)");
                object fo = Get(pg, "fondo");
                if (fo != null)
                {
                    Dictionary<string, object> f = Dic(fo, "el fondo");
                    object[] col = Lista(Get(f, "color") ?? new object[] { 0, 0, 0, 10 }, 4, "color");
                    pp.Fondo = new FondoPlan { Capa = (int)Num(Get(f, "capa") ?? 0),
                        Color = new double[] { Num(col[0]), Num(col[1]), Num(col[2]), Num(col[3]) } };
                }
                foreach (object ko in Lista(Get(pg, "caminos") ?? new object[0], 20000, "caminos"))
                {
                    Dictionary<string, object> k = Dic(ko, "un camino");
                    object[] col = Lista(Get(k, "color") ?? new object[] { 0, 0, 0, 100 }, 4, "color");
                    CaminoPlan cp = new CaminoPlan { Capa = (int)Num(Get(k, "capa")), Ancho = Num(Get(k, "ancho") ?? 1),
                        Color = new double[] { Num(col[0]), Num(col[1]), Num(col[2]), Num(col[3]) },
                        Punteado = Get(k, "punteado") != null };
                    foreach (object so in Lista(Get(k, "sub"), 500, "sub-caminos"))
                    {
                        Dictionary<string, object> s = Dic(so, "un sub-camino");
                        SubCamino sc = new SubCamino { C = Convert.ToBoolean(Get(s, "c") ?? false) };
                        foreach (object qo in Lista(Get(s, "p"), 200000, "puntos"))
                        {
                            object[] q = Lista(qo, 6, "punto");
                            if (q.Length < 6) throw new Exception("punto incompleto en el plan");
                            sc.P.Add(new double[] { Num(q[0]), Num(q[1]), Num(q[2]), Num(q[3]), Num(q[4]), Num(q[5]) });
                        }
                        puntos += sc.P.Count;
                        if (sc.P.Count > 1) cp.Sub.Add(sc);
                    }
                    caminos++;
                    if (cp.Sub.Count > 0) pp.Caminos.Add(cp);
                }
                foreach (object to in Lista(Get(pg, "textos") ?? new object[0], 5000, "textos"))
                {
                    Dictionary<string, object> t = Dic(to, "un texto");
                    pp.Textos.Add(new TextoPlan { Capa = (int)Num(Get(t, "capa")), T = Txt(Get(t, "t"), 200),
                        X = Num(Get(t, "x")), Y = Num(Get(t, "y")), Tam = Num(Get(t, "tam") ?? 12),
                        Vector = Convert.ToBoolean(Get(t, "vector") ?? false) });
                    textos++;
                }
                o.Paginas.Add(pp);
            }
            if (o.Paginas.Count == 0) throw new Exception("el plan no trae mesas");
            if (caminos > 20000) throw new Exception("el plan trae demasiados caminos");
            if (puntos > 3000000) throw new Exception("el plan trae demasiados puntos");
            if (textos > 5000) throw new Exception("el plan trae demasiados textos");
            foreach (PaginaPlan pg in o.Paginas)
            {
                foreach (CaminoPlan k in pg.Caminos) if (k.Capa < 0 || k.Capa >= o.Capas.Count) throw new Exception("un camino apunta a una capa que no existe");
                foreach (TextoPlan t in pg.Textos) if (t.Capa < 0 || t.Capa >= o.Capas.Count) throw new Exception("un texto apunta a una capa que no existe");
                if (pg.Fondo != null && (pg.Fondo.Capa < 0 || pg.Fondo.Capa >= o.Capas.Count)) throw new Exception("un fondo apunta a una capa que no existe");
            }
            return o;
        }
    }

    // ── el filtro de mensajes COM: reintentar mientras Corel está ocupado ─────────────────────────
    [ComImport, Guid("00000016-0000-0000-C000-000000000046"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IOleMessageFilter
    {
        [PreserveSig] int HandleInComingCall(int dwCallType, IntPtr hTaskCaller, int dwTickCount, IntPtr lpInterfaceInfo);
        [PreserveSig] int RetryRejectedCall(IntPtr hTaskCallee, int dwTickCount, int dwRejectType);
        [PreserveSig] int MessagePending(IntPtr hTaskCallee, int dwTickCount, int dwPendingType);
    }

    class FiltroMensajes : IOleMessageFilter
    {
        [DllImport("Ole32.dll")]
        static extern int CoRegisterMessageFilter(IOleMessageFilter nuevo, out IOleMessageFilter viejo);

        public static void Registrar() { IOleMessageFilter v; CoRegisterMessageFilter(new FiltroMensajes(), out v); }

        public int HandleInComingCall(int dwCallType, IntPtr hTaskCaller, int dwTickCount, IntPtr lpInterfaceInfo) { return 0; }
        // SERVERCALL_RETRYLATER (2): Corel está ocupado → reintentar a los 250 ms, durante 2 minutos
        public int RetryRejectedCall(IntPtr hTaskCallee, int dwTickCount, int dwRejectType)
        {
            if (dwRejectType == 2 && dwTickCount < 120000) return 250;
            return -1;
        }
        public int MessagePending(IntPtr hTaskCallee, int dwTickCount, int dwPendingType) { return 2; }
    }

    // ── el único hilo que habla con Corel ─────────────────────────────────────────────────────────
    static class HiloCorel
    {
        static readonly BlockingCollection<Action> cola = new BlockingCollection<Action>();
        static Thread hilo;

        public static void Iniciar()
        {
            hilo = new Thread(delegate ()
            {
                FiltroMensajes.Registrar();
                foreach (Action a in cola.GetConsumingEnumerable()) { try { a(); } catch { } }
            });
            hilo.IsBackground = true;
            hilo.SetApartmentState(ApartmentState.STA);
            hilo.Start();
        }

        /// Corre `f` en el hilo de Corel y espera su resultado (o su error).
        public static T Hacer<T>(Func<T> f)
        {
            T res = default(T);
            Exception err = null;
            using (ManualResetEventSlim listo = new ManualResetEventSlim(false))
            {
                cola.Add(delegate () { try { res = f(); } catch (Exception e) { err = e; } finally { listo.Set(); } });
                listo.Wait();
            }
            if (err != null) throw err;
            return res;
        }
    }

    // ── el armado ─────────────────────────────────────────────────────────────────────────────────
    class ResultadoArmado { public int Mesas; public string Metodo; public bool Guardado; public int TextosFallidos; public bool EspacioUnico; }

    static class ArmarCorel
    {
        const double MM = 25.4 / 72.0;            // un punto en milímetros (el documento se arma en mm)
        const int CDR_MM = 3;                     // cdrMillimeter
        const int CDR_CM = 4;                     // cdrCentimeter (las reglas que ve la persona)
        const int CDR_TOP_LEFT = 3;               // cdrReferencePoint.cdrTopLeft
        const int CDR_FALSO = 0, CDR_IZQ = 1;      // cdrTriState.cdrFalse · cdrAlignment.cdrLeftAlignment
        const int CDR_ESPANOL = 1034;             // cdrTextLanguage (el idioma del texto; no cambia el dibujo)
        const int CDR_VERSION_2022 = 24;          // cdrFileVersion: abre de la 2022 en adelante

        /// ¿Está instalado Corel 2022+? → «CorelDRAW 2026 (27)» o null. No abre Corel.
        public static string Instalado(out int mayor)
        {
            mayor = 0;
            try
            {
                using (Microsoft.Win32.RegistryKey k = Microsoft.Win32.Registry.ClassesRoot.OpenSubKey(@"CorelDRAW.Application\CurVer"))
                {
                    string cur = k == null ? null : k.GetValue("") as string;          // «CorelDRAW.Application.27»
                    if (cur == null) return null;
                    int.TryParse(cur.Substring(cur.LastIndexOf('.') + 1), out mayor);
                }
            }
            catch { return null; }
            // 24 = 2022 y 2023 (la 2023 es 24.3+), 25 = 2024, 26 = 2025, 27 = 2026
            string anio = mayor == 24 ? "2022/2023" : mayor >= 25 ? (mayor + 1999).ToString() : null;
            if (mayor < 24) return "CorelDRAW (versión " + mayor + ", anterior a 2022)";
            return "CorelDRAW " + anio + " (" + mayor + ")";
        }

        static dynamic App()
        {
            Type t = Type.GetTypeFromProgID("CorelDRAW.Application");
            if (t == null) throw new Exception("no encontré CorelDRAW en esta computadora");
            // se engancha con el Corel que ya está abierto (Corel es de una sola instancia); si no hay
            // ninguno, lo abre
            dynamic app = Activator.CreateInstance(t);
            if ((int)app.VersionMajor < 24) throw new Exception("esta computadora tiene CorelDRAW " + app.VersionMajor + ": hace falta la 2022 o más nueva");
            app.Visible = true;
            return app;
        }

        static string Fmt(double v) { return v.ToString("0.###", CultureInfo.InvariantCulture); }

        // Los contornos de UNA página como un SVG en puntos, con `tizada_ref` = un rectángulo SIN
        // relleno ni trazo del tamaño exacto de la página: al importar, el grupo mide lo que la página
        // y se ubica en su esquina (la caja de una curva no es la de sus puntos).
        static string SvgPagina(PaginaPlan pg)
        {
            StringBuilder sb = new StringBuilder();
            sb.Append("<?xml version=\"1.0\" encoding=\"UTF-8\"?><svg xmlns=\"http://www.w3.org/2000/svg\" width=\"")
              .Append(Fmt(pg.W)).Append("pt\" height=\"").Append(Fmt(pg.H)).Append("pt\" viewBox=\"0 0 ")
              .Append(Fmt(pg.W)).Append(' ').Append(Fmt(pg.H)).Append("\">")
              .Append("<rect id=\"tizada_ref\" x=\"0\" y=\"0\" width=\"").Append(Fmt(pg.W)).Append("\" height=\"").Append(Fmt(pg.H))
              .Append("\" fill=\"none\" stroke=\"none\"/><g fill=\"none\" stroke=\"#000000\" stroke-width=\"1\">");
            foreach (CaminoPlan k in pg.Caminos)
            {
                if (k.Punteado) continue;          // el dobladillo va aparte, con rayas (ver `DibujarCamino`)
                foreach (SubCamino sp in k.Sub)
                {
                    sb.Append("<path d=\"M").Append(Fmt(sp.P[0][0])).Append(' ').Append(Fmt(sp.P[0][1]));
                    int n = sp.C ? sp.P.Count + 1 : sp.P.Count;
                    for (int i = 1; i < n; i++)
                    {
                        double[] a = sp.P[i - 1], b = sp.P[i % sp.P.Count];
                        bool recta = a[4] == a[0] && a[5] == a[1] && b[2] == b[0] && b[3] == b[1];
                        if (recta) sb.Append('L').Append(Fmt(b[0])).Append(' ').Append(Fmt(b[1]));
                        else sb.Append('C').Append(Fmt(a[4])).Append(' ').Append(Fmt(a[5])).Append(' ')
                               .Append(Fmt(b[2])).Append(' ').Append(Fmt(b[3])).Append(' ')
                               .Append(Fmt(b[0])).Append(' ').Append(Fmt(b[1]));
                    }
                    if (sp.C) sb.Append('Z');
                    sb.Append("\"/>");
                }
            }
            sb.Append("</g></svg>");
            return sb.ToString();
        }

        // Cada contorno como trazo negro sin relleno (lo mismo que `tizadaTrazo` en Illustrator)
        static void Trazo(dynamic s, double anchoPt, double[] cmyk)
        {
            try { s.Fill.ApplyNoFill(); } catch { }
            s.Outline.Type = 1;                                   // cdrOutline
            s.Outline.Width = Math.Max(0.05, anchoPt * MM);
            s.Outline.Color.CMYKAssign((int)cmyk[0], (int)cmyk[1], (int)cmyk[2], (int)cmyk[3]);
        }

        // Importar el SVG de la página en la capa y ubicarlo en la esquina. false = no se pudo (se
        // borra lo que haya entrado y se dibuja punto por punto).
        static bool ImportarSvg(dynamic app, dynamic doc, dynamic capa, PaginaPlan pg, double[] cmyk, double ancho)
        {
            string ruta = Path.Combine(Path.GetTempPath(), "tizada_corel_" + Guid.NewGuid().ToString("N") + ".svg");
            File.WriteAllText(ruta, SvgPagina(pg), new UTF8Encoding(false));
            dynamic sel = null;
            try
            {
                capa.Activate();
                capa.Import(ruta, 0, app.CreateStructImportOptions());      // 0 = cdrAutoSense
                sel = doc.SelectionRange;
                if (sel == null || (int)sel.Count == 0) return false;
                double w = pg.W * MM, h = pg.H * MM;
                // el grupo tiene que medir lo que la página (lo asegura `tizada_ref`); si no, no se adivina
                if (Math.Abs((double)sel.SizeWidth - w) > 0.5 || Math.Abs((double)sel.SizeHeight - h) > 0.5) { sel.Delete(); return false; }
                sel.SetPositionEx(CDR_TOP_LEFT, 0.0, h);
                dynamic sueltos = sel.UngroupAllEx();
                int n = (int)sueltos.Count;
                for (int i = n; i >= 1; i--)
                {
                    dynamic s = sueltos[i];
                    bool sinRelleno = (int)s.Fill.Type == 0;              // cdrNoFill
                    bool sinTrazo = (int)s.Outline.Type == 0;             // cdrNoOutline
                    // `tizada_ref`: sin relleno ni trazo y del tamaño de la página → se borra
                    if (sinRelleno && sinTrazo && Math.Abs((double)s.SizeWidth - w) < 0.5 && Math.Abs((double)s.SizeHeight - h) < 0.5) { s.Delete(); continue; }
                    Trazo(s, ancho, cmyk);
                }
                return true;
            }
            catch
            {
                try { if (sel != null) sel.Delete(); } catch { }
                return false;
            }
            finally { try { File.Delete(ruta); } catch { } }
        }

        // Un contorno punto por punto (si el SVG no entró). Cada punto: [x, y, entrada x, y, salida x, y]
        // en puntos, origen arriba a la izquierda de la PÁGINA, «y» hacia abajo.
        static void DibujarCamino(dynamic app, dynamic doc, dynamic capa, CaminoPlan k, double altoPag)
        {
            Func<double, double> X = delegate (double x) { return x * MM; };
            Func<double, double> Y = delegate (double y) { return (altoPag - y) * MM; };
            foreach (SubCamino sp in k.Sub)
            {
                dynamic crv = app.CreateCurve(doc);
                dynamic sub = crv.CreateSubPath(X(sp.P[0][0]), Y(sp.P[0][1]));
                int n = sp.C ? sp.P.Count + 1 : sp.P.Count;
                for (int i = 1; i < n; i++)
                {
                    double[] a = sp.P[i - 1], b = sp.P[i % sp.P.Count];
                    bool recta = a[4] == a[0] && a[5] == a[1] && b[2] == b[0] && b[3] == b[1];
                    if (i == sp.P.Count && sp.C && recta) break;            // el cierre lo hace `Closed`
                    if (recta) sub.AppendLineSegment(X(b[0]), Y(b[1]), false);
                    else sub.AppendCurveSegment2(X(b[0]), Y(b[1]), X(a[4]), Y(a[5]), X(b[2]), Y(b[3]), false);
                }
                sub.Closed = sp.C;
                dynamic forma = capa.CreateCurve(crv);
                Trazo(forma, k.Ancho, k.Color);
                if (k.Punteado)
                {
                    // un estilo de rayas de los que trae Corel (el 1 es la línea llena). Si esta versión
                    // no lo deja, queda llena: igual se ve dónde termina el margen.
                    try { forma.Outline.Style = app.OutlineStyles[4]; } catch { }
                    try { forma.Name = "dobladillo"; } catch { }
                }
            }
        }

        const int CDR_ACOMODO_LIBRE = 1;           // cdrMultipageLayout.cdrMultipageLayoutFreeform

        static bool AcomodarEnUnEspacio(dynamic app, dynamic doc, Plan plan)
        {
            try
            {
                dynamic vista = app.ActiveWindow.ActiveView;
                vista.UseMultipageView = true;
                doc.MultipageLayout = CDR_ACOMODO_LIBRE;
                bool alguna = false;
                for (int ip = 0; ip < plan.Paginas.Count; ip++)
                {
                    PaginaPlan pg = plan.Paginas[ip];
                    if (!pg.ConLugar) continue;
                    vista.SetPageOrigin(doc.Pages[ip + 1], pg.Cx * MM, -pg.Cy * MM);
                    alguna = true;
                }
                try { vista.ToFitAllPages(); } catch { }
                return alguna;
            }
            catch { return false; }
        }

        /// Arma el documento entero. Corre en el hilo de Corel (`HiloCorel`).
        public static ResultadoArmado Armar(Plan plan)
        {
            dynamic app = App();
            dynamic doc = app.CreateDocument();
            doc.Unit = CDR_MM;                     // las cuentas de este archivo van en mm (no tocar)
            // LO QUE VE LA PERSONA, EN CENTÍMETROS (2026-10-07, pedido del usuario: «debe ser en
            // centímetros», igual que Illustrator): las reglas del documento. Si esta versión no lo deja,
            // quedan como vengan; el dibujo no cambia.
            try { doc.Rulers.HUnits = CDR_CM; doc.Rulers.VUnits = CDR_CM; } catch { }
            ResultadoArmado r = new ResultadoArmado { Mesas = plan.Paginas.Count, Metodo = "ninguno" };
            bool alguno = false, todosSvg = true;
            // más rápido: Corel no redibuja mientras se arma (se restaura SIEMPRE al final)
            try { app.Optimization = true; app.EventsEnabled = false; } catch { }
            try
            {
                doc.BeginCommandGroup("USER PRO: plantilla");
                if (plan.Paginas.Count > 1) doc.AddPages(plan.Paginas.Count - 1);
                for (int ip = 0; ip < plan.Paginas.Count; ip++)
                {
                    PaginaPlan pg = plan.Paginas[ip];
                    dynamic page = doc.Pages[ip + 1];
                    page.SetSize(pg.W * MM, pg.H * MM);
                    try { page.Name = pg.Nombre; } catch { }
                    page.Activate();

                    // ── las capas de ESTA página, de abajo hacia arriba (la «Capa 1» con que nace la
                    //    página pasa a ser la primera; las nuevas se crean arriba de la anterior) ──
                    List<dynamic> capas = new List<dynamic>();
                    dynamic base0 = null;
                    foreach (dynamic l in page.Layers)
                    {
                        if (!(bool)l.IsGuidesLayer && !(bool)l.Master && !(bool)l.IsDesktopLayer && !(bool)l.IsGridLayer) { base0 = l; break; }
                    }
                    for (int i = 0; i < plan.Capas.Count; i++)
                    {
                        dynamic lay = (i == 0 && base0 != null) ? base0 : page.CreateLayer(plan.Capas[i].Nombre);
                        lay.Name = plan.Capas[i].Nombre;
                        try { lay.Color.RGBAssign(plan.Capas[i].Color[0], plan.Capas[i].Color[1], plan.Capas[i].Color[2]); } catch { }
                        capas.Add(lay);
                    }

                    // ── el fondo de la mesa (rojo clarito, el color viene en el plan) ──
                    if (pg.Fondo != null)
                    {
                        dynamic f = capas[pg.Fondo.Capa].CreateRectangle2(0.0, 0.0, pg.W * MM, pg.H * MM, 0.0, 0.0, 0.0, 0.0);
                        f.Fill.UniformColor.CMYKAssign((int)pg.Fondo.Color[0], (int)pg.Fondo.Color[1], (int)pg.Fondo.Color[2], (int)pg.Fondo.Color[3]);
                        f.Outline.SetNoOutline();
                        try { f.Name = "fondo"; } catch { }
                    }

                    // ── los contornos: de una vez con el SVG; si no entra, punto por punto ──
                    CaminoPlan c0 = pg.Caminos.Find(delegate (CaminoPlan x) { return !x.Punteado; });
                    if (c0 != null)
                    {
                        alguno = true;
                        if (!ImportarSvg(app, doc, capas[c0.Capa], pg, c0.Color, c0.Ancho))
                        {
                            todosSvg = false;
                            foreach (CaminoPlan k in pg.Caminos) if (!k.Punteado) DibujarCamino(app, doc, capas[k.Capa], k, pg.H);
                        }
                    }
                    // MOLDE A MEDIDA (MAPA 623): el margen (dobladillo), punteado, siempre punto por punto
                    foreach (CaminoPlan k in pg.Caminos) if (k.Punteado) DibujarCamino(app, doc, capas[k.Capa], k, pg.H);

                    // ── el nombre de la mesa como TEXTO VIVO (lo que lee el motor); el título del talle
                    //    va en curvas. Un texto que Corel no acepta no corta el armado: se cuenta. ──
                    foreach (TextoPlan t in pg.Textos)
                    {
                        try
                        {
                            float tam = (float)Math.Max(1, Math.Min(1000, t.Tam));
                            dynamic tx = capas[t.Capa].CreateArtisticText(t.X * MM, (pg.H - t.Y) * MM, string.IsNullOrEmpty(t.T) ? "Pieza" : t.T,
                                                                          CDR_ESPANOL, 0, "Arial", tam, CDR_FALSO, CDR_FALSO, 0, CDR_IZQ);
                            tx.Fill.UniformColor.CMYKAssign(0, 0, 0, 100);
                            if (t.Vector) { try { tx.ConvertToCurves(); } catch { } }
                        }
                        catch { r.TextosFallidos++; }
                    }

                    // ── bloquear lo que va bloqueado ──
                    for (int i = 0; i < capas.Count; i++) { try { capas[i].Editable = !plan.Capas[i].Bloqueada; } catch { } }
                }
                r.Metodo = !alguno ? "ninguno" : (todosSvg ? "svg" : "puntos");
                doc.EndCommandGroup();
                // 🔴 TODAS LAS MESAS EN UN ESPACIO DE TRABAJO (pedido del usuario 2026-09-30: «una página
                // por base no es para nada cómodo»). Cada mesa SIGUE siendo una página (así la lee el
                // motor: mesa = página del PDF), pero se prende la VISTA DE VARIAS PÁGINAS con acomodo
                // LIBRE y cada página va al lugar de su pieza en el molde, como las mesas de Illustrator.
                // `SetPageOrigin` ubica el CENTRO de la página, con la «y» hacia arriba. Se guarda con el
                // archivo. Si esta versión no lo tiene, queda como estaba (una página detrás de otra).
                r.EspacioUnico = AcomodarEnUnEspacio(app, doc, plan);
            }
            finally
            {
                try { app.Optimization = false; app.EventsEnabled = true; app.Refresh(); } catch { }
            }
            // se termina parado en la primera mesa, en la capa activa del plan («diseño»)
            try
            {
                dynamic p1 = doc.Pages[1];
                p1.Activate();
                int ia = Math.Min(plan.Activa, plan.Capas.Count - 1);
                foreach (dynamic l in p1.Layers) if ((string)l.Name == plan.Capas[ia].Nombre) { l.Activate(); break; }
            }
            catch { }
            if (!string.IsNullOrEmpty(plan.GuardarEn))
            {
                try
                {
                    dynamic op = app.CreateStructSaveAsOptions();
                    op.Version = CDR_VERSION_2022;
                    doc.SaveAs(plan.GuardarEn, op);
                    r.Guardado = true;
                }
                catch { r.Guardado = false; }
            }
            try { app.AppWindow.Activate(); } catch { }
            return r;
        }

        /// Documentos › USER PRO › Plantillas › «<nombre>.cdr»; si ya existe NO se pisa: «… (2).cdr».
        public static string RutaParaGuardar(string nombre)
        {
            string carpeta = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "USER PRO", "Plantillas");
            Directory.CreateDirectory(carpeta);
            string ruta = Path.Combine(carpeta, nombre + ".cdr");
            for (int i = 2; File.Exists(ruta) && i < 1000; i++) ruta = Path.Combine(carpeta, nombre + " (" + i + ").cdr");
            return ruta;
        }
    }
}
