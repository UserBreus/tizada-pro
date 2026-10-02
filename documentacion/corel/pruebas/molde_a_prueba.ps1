# Molde BASE (camino A) hecho en Corel con la convención de TIZADA PRO (CONVENCION_PLANTILLA.md):
# una página por pieza, un talle por capa, y en cada capa el texto «TALLE-Pieza-#». Contornos sin
# relleno, como un molde de moldería. Documento descartable.
param([string]$Salida = "$PSScriptRoot\molde_a_corel.pdf")
$ErrorActionPreference = 'Stop'
$app = New-Object -ComObject CorelDRAW.Application
$doc = $app.CreateDocument(); $doc.Unit = 3
$doc.AddPages(1) | Out-Null
$piezas = @('Frente', 'Espalda')
for ($i = 1; $i -le 2; $i++) {
  $pg = $doc.Pages.Item($i); $pg.Name = $piezas[$i-1]; $pg.SetSize(600, 800); $pg.Activate()
  foreach ($talle in @('S', 'M', 'L')) {
    $capa = $pg.CreateLayer($talle)
    $k = @{ 'S' = 1.0; 'M' = 1.06; 'L' = 1.12 }[$talle]
    $w = 450 * $k; $h = 650 * $k; $x = (600 - $w) / 2; $y = (800 - $h) / 2
    $crv = $app.CreateCurve($doc)
    $sp = $crv.CreateSubPath($x, $y)
    $sp.AppendLineSegment($x + $w, $y) | Out-Null
    $sp.AppendLineSegment($x + $w - 40, $y + $h) | Out-Null
    $sp.AppendCurveSegment2($x + 40, $y + $h, $x + $w * 0.7, $y + $h - 90, $x + $w * 0.3, $y + $h - 90) | Out-Null
    $sp.Closed = $true
    $s = $capa.CreateCurve($crv); $s.Fill.ApplyNoFill(); $s.Outline.Type = 1; $s.Outline.Width = 0.3
    $s.Outline.Color.CMYKAssign(0, 0, 0, 100)
    $t = $capa.CreateArtisticText($x + 30, $y + 30, "$talle-$($piezas[$i-1])-#", 1034, 0, 'Arial', 14)
    $t.Fill.UniformColor.CMYKAssign(0, 0, 0, 100)
  }
}
$doc.PublishToPDF($Salida)
$doc.Dirty = $false; $doc.Close()
"OK -> $Salida"
