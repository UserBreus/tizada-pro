# Molde CON DISEÑO adentro hecho en Corel (camino B): una página por pieza, una capa por talle (S y M),
# y cada pieza = su contorno como contenedor de PowerClip con el diseño adentro (la «máscara de
# recorte» de Illustrator). También deja el nombre «00» como texto de muestra. Documento descartable.
param([string]$Salida = "$PSScriptRoot\molde_b_corel.pdf")
$ErrorActionPreference = 'Stop'
$app = New-Object -ComObject CorelDRAW.Application
$doc = $app.CreateDocument()
$doc.Unit = 3
$doc.AddPages(1) | Out-Null
$piezas = @('Frente', 'Espalda')
for ($i = 1; $i -le 2; $i++) {
  $pg = $doc.Pages.Item($i); $pg.Name = $piezas[$i-1]; $pg.SetSize(700, 400); $pg.Activate()
  $x = 20
  foreach ($talle in @('S', 'M')) {
    $capa = $pg.CreateLayer($talle)
    $esc = if ($talle -eq 'S') { 1.0 } else { 1.15 }
    # contorno de la pieza (un trapecio con escote curvo) = contenedor
    $w = 250 * $esc; $h = 330 * $esc
    $crv = $app.CreateCurve($doc)
    $sp = $crv.CreateSubPath($x, 20)
    $sp.AppendLineSegment($x + $w, 20) | Out-Null
    $sp.AppendLineSegment($x + $w - 20, 20 + $h) | Out-Null
    $sp.AppendCurveSegment2($x + 20, 20 + $h, $x + $w * 0.65, 20 + $h - 60, $x + $w * 0.35, 20 + $h - 60) | Out-Null
    $sp.Closed = $true
    $cont = $capa.CreateCurve($crv)
    $cont.Outline.SetNoOutline()
    # diseño que se mete adentro: franjas CMYK exactas más grandes que la pieza
    $a = $capa.CreateRectangle2($x - 30, 0, $w + 60, $h + 60); $a.Fill.UniformColor.CMYKAssign(0, 100, 100, 0); $a.Outline.SetNoOutline()
    $b = $capa.CreateRectangle2($x - 30, 150, $w + 60, 50); $b.Fill.UniformColor.CMYKAssign(12, 34, 56, 7); $b.Outline.SetNoOutline()
    $n = $capa.CreateArtisticText($x + 60, 60, '00', 1034, 0, 'Arial', 90, $true); $n.Fill.UniformColor.CMYKAssign(0, 0, 0, 100)
    foreach ($s in @($a, $b, $n)) { $s.AddToPowerClip($cont, 0) }
    $x += $w + 40
  }
}
"capas pag 1: " + (($doc.Pages.Item(1).Layers | ForEach-Object { $_.Name }) -join ' | ')
$doc.PublishToPDF($Salida)
$doc.Dirty = $false
$doc.Close()
"OK -> $Salida"
