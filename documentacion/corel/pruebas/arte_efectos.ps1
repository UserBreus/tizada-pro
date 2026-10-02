# Arte de prueba en Corel con lo que un diseñador usa de verdad, para ver cómo lo guarda en el PDF
# y si TIZADA PRO lo entiende igual que lo de Illustrator. Cada cosa va en su try: si una falla,
# las demás siguen. Documento descartable.
$ErrorActionPreference = 'Stop'
$app = New-Object -ComObject CorelDRAW.Application
$doc = $app.CreateDocument(); $doc.Unit = 3
$pg = $doc.Pages.Item(1); $pg.Name = 'Espalda#M'; $pg.SetSize(400, 500)
$c = @{}
foreach ($n in @('diseño', 'Editable escudo', 'Editable logo', 'Nombre', '00', 'guias')) { $c[$n] = $pg.CreateLayer($n) }
$r = @()
function Probar($nombre, [scriptblock]$b) { try { & $b; $script:r += "OK    $nombre" } catch { $script:r += "FALLA $nombre : $($_.Exception.Message)" } }

Probar 'degradé (fuente lineal) en diseño' {
  $s = $c['diseño'].CreateRectangle2(0, 0, 400, 500)
  $s.Fill.ApplyFountainFill($app.CreateCMYKColor(0, 100, 100, 0), $app.CreateCMYKColor(100, 0, 0, 0), 1, 90, 256, 0, 50, 0, 0, 0) | Out-Null
  $s.Outline.SetNoOutline()
}
Probar 'transparencia uniforme 50% en diseño' {
  $s = $c['diseño'].CreateEllipse2(200, 250, 120); $s.Fill.UniformColor.CMYKAssign(0, 0, 100, 0); $s.Outline.SetNoOutline()
  $s.Transparency.ApplyUniformTransparency(50) | Out-Null
}
Probar 'texto del diseño en curvas' {
  $t = $c['diseño'].CreateArtisticText(20, 20, 'CLUB', 1034, 0, 'Arial', 60, $true); $t.Fill.UniformColor.CMYKAssign(0, 0, 0, 100); $t.ConvertToCurves() | Out-Null
}
Probar 'color Pantone (tinta plana) en diseño' {
  $s = $c['diseño'].CreateRectangle2(0, 440, 400, 30); $s.Outline.SetNoOutline()
  $s.Fill.UniformColor.SpotAssignByName('PANTONE 485 C')
}
Probar 'sombra paralela en diseño' {
  $s = $c['diseño'].CreateRectangle2(280, 60, 80, 80); $s.Fill.UniformColor.CMYKAssign(0, 60, 100, 0); $s.Outline.SetNoOutline()
  $s.CreateDropShadow(0, 50, 15, 3, -3, $app.CreateCMYKColor(0, 0, 0, 100)) | Out-Null
}
Probar 'escudo = GRUPO de 3 objetos' {
  $a = $c['Editable escudo'].CreateEllipse2(330, 440, 30); $a.Fill.UniformColor.CMYKAssign(100, 0, 0, 0)
  $b = $c['Editable escudo'].CreateRectangle2(315, 425, 30, 30); $b.Fill.UniformColor.CMYKAssign(0, 0, 0, 0)
  $e = $c['Editable escudo'].CreateEllipse2(330, 440, 8); $e.Fill.UniformColor.CMYKAssign(0, 100, 0, 0)
  $sr = $app.CreateShapeRange(); $sr.Add($a); $sr.Add($b); $sr.Add($e); $sr.Group() | Out-Null
}
Probar 'logo = IMAGEN (PNG) importada' {
  $c['Editable logo'].Activate()
  $c['Editable logo'].Import("$PSScriptRoot\logo_prueba.png", 0, $app.CreateStructImportOptions())
  $sel = $app.ActiveSelectionRange; $sel.SetSize(40, 40); $sel.SetPosition(30, 480)
}
Probar 'nombre sobre una CURVA (texto en trayecto)' {
  $arco = $c['Nombre'].CreateEllipse2(200, 250, 150, 150); $arco.Outline.SetNoOutline()
  $t = $c['Nombre'].CreateArtisticText(100, 380, 'GONZALEZ', 1034, 0, 'Arial', 40, $true); $t.Fill.UniformColor.CMYKAssign(0, 0, 0, 100)
  $t.Text.FitToPath($arco) | Out-Null
  $arco.Delete()
}
Probar 'número con PowerClip de franjas adentro' {
  $n = $c['00'].CreateArtisticText(140, 120, '7', 1034, 0, 'Arial', 200, $true); $n.Fill.UniformColor.CMYKAssign(0, 0, 0, 100)
  $n.ConvertToCurves() | Out-Null
  $f = $c['00'].CreateRectangle2(100, 150, 200, 20); $f.Fill.UniformColor.CMYKAssign(0, 100, 0, 0); $f.Outline.SetNoOutline()
  $f.AddToPowerClip($c['00'].Shapes.Item(2), 0) | Out-Null
}
$g = $c['guias'].CreateArtisticText(5, 5, 'Espalda#M', 1034, 0, 'Arial', 10); $g.Fill.UniformColor.CMYKAssign(0, 0, 0, 100)
$doc.PublishToPDF("$PSScriptRoot\arte_efectos.pdf")
$doc.Dirty = $false; $doc.Close()
$r
