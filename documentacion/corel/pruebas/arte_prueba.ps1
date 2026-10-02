# Arma en CorelDRAW (por COM) un ARTE de prueba con la MISMA estructura que un arte de Illustrator
# para TIZADA PRO: una página por mesa, capas «diseño», «Editable escudo», «Nombre», «00» y «guias»
# (con el nombre de la mesa como texto vivo). Después lo publica en PDF para ver qué entiende el sistema.
# Es un documento NUEVO y descartable: no toca nada abierto del usuario.
param([string]$Salida = "$PSScriptRoot\arte_corel.pdf", [string]$Cdr = "$PSScriptRoot\arte_corel.cdr")
$ErrorActionPreference = 'Stop'
$app = New-Object -ComObject CorelDRAW.Application
$doc = $app.CreateDocument()
$doc.Unit = 3            # cdrMillimeter
$mesas = @('Frente#M', 'Espalda#M')
$doc.AddPages(1) | Out-Null
$info = @()
for ($i = 1; $i -le $mesas.Count; $i++) {
  $pg = $doc.Pages.Item($i)
  $pg.Name = $mesas[$i-1]
  $pg.SetSize(300, 400)
  $pg.Activate()
  # Capas de ABAJO hacia ARRIBA (en Corel la última creada queda arriba).
  $capas = @{}
  foreach ($n in @('diseño', 'Editable escudo', 'Nombre', '00', 'guias')) { $capas[$n] = $pg.CreateLayer($n) }
  # diseño: fondo rojo CMYK exacto + una franja con decimales (como Illustrator guarda 0.996)
  $r = $capas['diseño'].CreateRectangle2(0, 0, 300, 400); $r.Fill.UniformColor.CMYKAssign(0, 100, 100, 0); $r.Outline.SetNoOutline()
  $f = $capas['diseño'].CreateRectangle2(0, 150, 300, 60); $f.Fill.UniformColor.CMYKAssign(12, 34, 56, 7); $f.Outline.SetNoOutline()
  # Editable escudo: un círculo cian
  $e = $capas['Editable escudo'].CreateEllipse2(220, 330, 25); $e.Fill.UniformColor.CMYKAssign(100, 0, 0, 0); $e.Outline.SetNoOutline()
  # Nombre: texto vivo con borde DETRÁS del relleno (lo que en Illustrator es la pila de apariencias)
  $t = $capas['Nombre'].CreateArtisticText(60, 300, 'GARCIA', 1034, 0, 'Arial', 48, $true)
  $t.Fill.UniformColor.CMYKAssign(0, 0, 0, 0)
  $t.Outline.Type = 1; $t.Outline.Width = 1.5; $t.Outline.Color.CMYKAssign(0, 0, 0, 100); $t.Outline.BehindFill = $true
  # 00: número
  $n0 = $capas['00'].CreateArtisticText(90, 180, '10', 1034, 0, 'Arial', 140, $true)
  $n0.Fill.UniformColor.CMYKAssign(0, 0, 0, 100)
  # guias: el nombre de la mesa como texto vivo (con eso el sistema mapea cada mesa a su pieza)
  $g = $capas['guias'].CreateArtisticText(10, 10, $mesas[$i-1], 1034, 0, 'Arial', 12)
  $g.Fill.UniformColor.CMYKAssign(0, 0, 0, 100)
  $info += "pagina $i '$($pg.Name)': capas=" + (($pg.Layers | ForEach-Object { $_.Name }) -join ' | ')
}
$info
"capas maestras: " + (($doc.MasterPage.Layers | ForEach-Object { $_.Name }) -join ' | ')
$s = $doc.PDFSettings
"PDF por defecto: TextAsCurves=$($s.TextAsCurves) EmbedFonts=$($s.EmbedFonts) ColorMode=$($s.ColorMode) pdfVersion=$($s.pdfVersion) UseColorProfile=$($s.UseColorProfile) PublishRange=$($s.PublishRange) SpotColors=$($s.SpotColors) Overprints=$($s.Overprints) ComplexFillsAsBitmaps=$($s.ComplexFillsAsBitmaps) TextExportMode=$($s.TextExportMode) SubsetFonts=$($s.SubsetFonts)"
$doc.SaveAs($Cdr, $app.CreateStructSaveAsOptions())
$doc.PublishToPDF($Salida)
$doc.Close()
"OK -> $Salida"
