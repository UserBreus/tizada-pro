# ¿Puede Corel hacer por COM lo mismo que hace tizada.jsx en Illustrator? Página por mesa con nombre,
# capas con nombre y bloqueo, importar un SVG de contornos en una capa y ubicarlo exacto, volverlo
# guía, textos, página MUY larga, y guardar .cdr en versión 2022 (v24). Documento descartable.
$ErrorActionPreference = 'Stop'
$dir = $PSScriptRoot
$app = New-Object -ComObject CorelDRAW.Application
$doc = $app.CreateDocument()
$doc.Unit = 3
$res = @()
# 1) página muy larga (mesa de 1,6 m × 30 m)
try { $doc.Pages.Item(1).SetSize(1600, 30000); $res += "pagina 1600x30000 mm: OK (" + $doc.Pages.Item(1).SizeWidth + " x " + $doc.Pages.Item(1).SizeHeight + ")" } catch { $res += "pagina larga: FALLA $_" }
try { $doc.Pages.Item(1).SetSize(1600, 100000); $res += "pagina 1600x100000 mm: " + $doc.Pages.Item(1).SizeHeight } catch { $res += "pagina 100 m: FALLA $($_.Exception.Message)" }
$doc.Pages.Item(1).SetSize(600, 800)
$pg = $doc.Pages.Item(1); $pg.Name = 'Frente#S'
# 2) capas como en tizada.jsx
$dis = $pg.CreateLayer('diseño'); $gu = $pg.CreateLayer('guias')
# 3) SVG de contornos importado en la capa guias, ubicado exacto
$svg = Join-Path $dir 'contorno.svg'
@'
<svg xmlns="http://www.w3.org/2000/svg" width="200mm" height="300mm" viewBox="0 0 200 300">
<rect id="tizada_ref" x="0" y="0" width="200" height="300" fill="none" stroke="none"/>
<path d="M20 20 L180 20 L170 280 Q100 240 30 280 Z" fill="none" stroke="#000" stroke-width="0.5"/>
</svg>
'@ | Set-Content -Encoding UTF8 $svg
$gu.Activate()
$gu.Import($svg, 0, $app.CreateStructImportOptions())
$imp = $app.ActiveSelectionRange
$res += "importado: $($imp.Count) forma(s), tamaño " + [math]::Round($imp.SizeWidth,1) + " x " + [math]::Round($imp.SizeHeight,1) + " mm"
$imp.SetPosition(50, 700)    # esquina sup-izq en mm (origen abajo-izq de la página)
$res += "posición tras SetPosition: x=" + [math]::Round($imp.PositionX,1) + " y=" + [math]::Round($imp.PositionY,1)
# 4) líneas guía (lo que en Illustrator es guides=true): una guía horizontal y una vertical
$g1 = $doc.MasterPage.GuidesLayer.CreateGuideAngle(0, 500, 0); $g2 = $doc.MasterPage.GuidesLayer.CreateGuideAngle(300, 0, 90)
$res += "guías creadas: " + $doc.MasterPage.GuidesLayer.Shapes.Count
# 5) texto con el nombre de la mesa en guias + convertir a curvas
$t = $gu.CreateArtisticText(50, 20, 'Frente#S', 1034, 0, 'Arial', 14); $t.Fill.UniformColor.CMYKAssign(0,0,0,100)
$t2 = $gu.CreateArtisticText(50, 40, 'TALLE S', 1034, 0, 'Arial', 30); $t2.ConvertToCurves()
# 6) bloquear capa guias, activar diseño
$gu.Editable = $false; $dis.Activate()
$res += "capas: " + (($pg.Layers | ForEach-Object { $_.Name + $(if (-not $_.Editable) {'(bloq)'} else {''}) }) -join ' | ')
# 7) guardar en versión 2022 (v24) y 2026
$o = $app.CreateStructSaveAsOptions(); $o.Version = 24
$doc.SaveAs((Join-Path $dir 'plantilla_v24.cdr'), $o); $res += "guardado .cdr v24 (2022): OK"
$doc.Dirty = $false; $doc.Close()
$res
