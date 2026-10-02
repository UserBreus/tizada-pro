// USER PRO para CorelDRAW — «EXPORTAR PARA TIZADA PRO»: el PDF que sube el diseñador, con TODOS los
// ajustes que necesita el sistema, sin depender de que el usuario los elija bien (pedido del usuario
// 2026-09-30: «eso depende mucho del usuario; que la extensión ya me guarde el PDF con todo lo que se
// necesita, con un botón visual en Corel»). Ver COREL_REFERENCIA.md §4 (por qué cada ajuste).
//
// Dos pasos, los dos en el hilo de Corel (`HiloCorel`):
//   1. `Analizar`: qué documento está abierto, dónde va a quedar el PDF y qué conviene avisar antes
//      (texto del DISEÑO sin pasar a curvas, mesas sin su nombre en «guias»). NO toca el documento.
//   2. `Exportar`: publica el PDF con los ajustes fijos y deja los ajustes de PDF del documento como
//      estaban. Nunca guarda el .cdr ni cambia nada del dibujo.
// El PDF va AL LADO del .cdr como «<nombre> - para TIZADA.pdf» (un nombre propio: nunca pisa otro PDF
// del usuario); si el documento nunca se guardó, a Documentos › USER PRO › Para subir.
// C# 5 (el compilador de Windows): nada de `$"…"`, `?.` ni `=>` en propiedades.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;

namespace UserPro
{
    class AnalisisExportar
    {
        public string Titulo;          // el nombre del documento en Corel
        public string Destino;         // la ruta del PDF que se va a escribir
        public int Paginas;
        public List<string> Avisos = new List<string>();
    }

    static class ExportarCorel
    {
        const int CDR_TEXTO = 6;                  // cdrShapeType.cdrTextShape
        // pdfVersion17_Acrobat9: conserva las CAPAS (OCG) y la transparencia vectorial
        const int PDF_ACROBAT9 = 9;
        const int PDF_COLOR_NATIVO = 3;           // pdfNative: el CMYK sale tal cual (nada de pasar a RGB)
        const int PDF_TODO = 0;                   // pdfWholeDocument
        const int PDF_ZIP = 3;                    // imágenes SIN pérdida (la ley: nunca bajar la calidad)
        const int PDF_TINTA_COMO_TINTA = 0;       // pdfSpotAsSpot

        static string Normal(string s)
        {
            string d = (s ?? "").Trim().ToLowerInvariant().Normalize(NormalizationForm.FormD);
            StringBuilder sb = new StringBuilder();
            foreach (char c in d) if (CharUnicodeInfo.GetUnicodeCategory(c) != UnicodeCategory.NonSpacingMark) sb.Append(c);
            return sb.ToString();
        }

        static dynamic App()
        {
            Type t = Type.GetTypeFromProgID("CorelDRAW.Application");
            if (t == null) throw new Exception("no encontré CorelDRAW en esta computadora");
            return Activator.CreateInstance(t);
        }

        static string CarpetaParaSubir()
        {
            return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "USER PRO", "Para subir");
        }

        // Cuenta los textos de las formas (y de lo que haya adentro de grupos y PowerClips)
        static int ContarTextos(dynamic formas)
        {
            int n = 0;
            foreach (dynamic s in formas)
            {
                int tipo = (int)s.Type;
                if (tipo == CDR_TEXTO) n++;
                try { if ((int)s.Shapes.Count > 0) n += ContarTextos(s.Shapes); } catch { }
                try { if (s.PowerClip != null) n += ContarTextos(s.PowerClip.Shapes); } catch { }
            }
            return n;
        }

        /// Paso 1: qué hay abierto y qué avisar. Corre en el hilo de Corel.
        public static AnalisisExportar Analizar()
        {
            dynamic app = App();
            dynamic doc = null;
            try { doc = app.ActiveDocument; } catch { }
            if (doc == null) throw new Exception("no hay ningún diseño abierto en CorelDRAW.");
            AnalisisExportar a = new AnalisisExportar();
            a.Titulo = (string)doc.Title;
            a.Paginas = (int)doc.Pages.Count;
            string nombre = Path.GetFileNameWithoutExtension(a.Titulo);
            string carpeta = null;
            try { carpeta = (string)doc.FilePath; } catch { }
            if (string.IsNullOrEmpty(carpeta) || !Directory.Exists(carpeta)) carpeta = CarpetaParaSubir();
            a.Destino = Path.Combine(carpeta, Plan.NombreArchivo(nombre) + " - para TIZADA.pdf");

            int textosDiseno = 0, sinNombre = 0;
            for (int i = 1; i <= a.Paginas; i++)
            {
                dynamic pg = doc.Pages[i];
                bool conNombre = false;
                foreach (dynamic l in pg.Layers)
                {
                    string n = Normal((string)l.Name);
                    if (n == "diseno") textosDiseno += ContarTextos(l.Shapes);
                    else if (n == "guias" || n == "guia" || n == "guides") { if (ContarTextos(l.Shapes) > 0) conNombre = true; }
                }
                if (!conNombre) sinNombre++;
            }
            if (textosDiseno > 0)
                a.Avisos.Add(textosDiseno + " texto" + (textosDiseno == 1 ? "" : "s") + " en la capa «diseño» todavía no está" + (textosDiseno == 1 ? "" : "n") +
                             " en curvas. Se imprime tal cual, pero conviene pasarlo a curvas: seleccionalo y tocá Ctrl+Q (Objeto → Convertir en curvas).");
            if (sinNombre > 0)
                a.Avisos.Add(sinNombre + " página" + (sinNombre == 1 ? "" : "s") + " no tiene" + (sinNombre == 1 ? "" : "n") +
                             " el nombre de la mesa escrito en la capa «guias». Sin ese nombre, el sistema no sabe de qué pieza es esa mesa.");
            return a;
        }

        /// Paso 2: publica el PDF con los ajustes de TIZADA PRO. Corre en el hilo de Corel.
        public static void Exportar(string destino)
        {
            dynamic app = App();
            dynamic doc = app.ActiveDocument;
            if (doc == null) throw new Exception("no hay ningún diseño abierto en CorelDRAW.");
            Directory.CreateDirectory(Path.GetDirectoryName(destino));
            dynamic s = doc.PDFSettings;
            // lo que tenía el documento, para dejarlo igual después (el botón no cambia sus ajustes)
            Dictionary<string, object> antes = new Dictionary<string, object>();
            string[] campos = { "pdfVersion", "ColorMode", "PublishRange", "TextAsCurves", "ComplexFillsAsBitmaps", "EmbedFonts",
                                "EmbedBaseFonts", "SubsetFonts", "BitmapCompression", "DownsampleColor", "DownsampleGray",
                                "DownsampleMono", "SpotColors", "ConvertSpotColors", "OutputSpotColorsAs", "Overprints",
                                "IncludeBleed", "CropMarks", "RegistrationMarks", "DensitometerScales", "FileInformation",
                                "Thumbnails", "TextExportMode" };
            foreach (string c in campos) { try { antes[c] = s.GetType().InvokeMember(c, System.Reflection.BindingFlags.GetProperty, null, s, null); } catch { } }
            try
            {
                s.pdfVersion = PDF_ACROBAT9;          // con las capas (Acrobat 6+)
                s.ColorMode = PDF_COLOR_NATIVO;       // CMYK exacto
                s.PublishRange = PDF_TODO;            // todas las mesas
                s.TextAsCurves = false;               // los nombres de las mesas y la personalización, como TEXTO
                s.ComplexFillsAsBitmaps = false;      // el degradé sigue siendo vector
                s.EmbedFonts = true;
                s.EmbedBaseFonts = true;
                s.SubsetFonts = true;
                s.BitmapCompression = PDF_ZIP;        // sin pérdida
                s.DownsampleColor = false;            // las imágenes a su resolución
                s.DownsampleGray = false;
                s.DownsampleMono = false;
                s.SpotColors = true;                  // las tintas planas, como tintas planas
                s.ConvertSpotColors = false;
                s.OutputSpotColorsAs = PDF_TINTA_COMO_TINTA;
                s.Overprints = true;
                s.IncludeBleed = false;               // nada fuera de la mesa
                s.CropMarks = false;
                s.RegistrationMarks = false;
                s.DensitometerScales = false;
                s.FileInformation = false;
                s.Thumbnails = false;
                s.TextExportMode = 0;                 // texto en Unicode
                doc.PublishToPDF(destino);
            }
            finally
            {
                foreach (KeyValuePair<string, object> kv in antes)
                {
                    try { s.GetType().InvokeMember(kv.Key, System.Reflection.BindingFlags.SetProperty, null, s, new object[] { kv.Value }); } catch { }
                }
            }
            if (!File.Exists(destino)) throw new Exception("CorelDRAW no dejó el PDF (¿la carpeta es de sólo lectura?).");
        }
    }
}
