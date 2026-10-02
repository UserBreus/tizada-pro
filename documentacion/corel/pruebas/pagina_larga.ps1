# ¿Corel publica bien a PDF una mesa de 1,6 m × 30 m? (en 2017 las de más de 5,08 m salían en blanco
# por no usar /UserUnit). Documento descartable: un rectángulo arriba, otro abajo y un texto.
$ErrorActionPreference = 'Stop'
$app = New-Object -ComObject CorelDRAW.Application
$doc = $app.CreateDocument(); $doc.Unit = 3
$pg = $doc.Pages.Item(1); $pg.SetSize(1600, 30000); $pg.Name = 'Mesa larga'
$l = $pg.CreateLayer('diseño')
$a = $l.CreateRectangle2(100, 29500, 400, 400); $a.Fill.UniformColor.CMYKAssign(0, 100, 100, 0)
$b = $l.CreateRectangle2(100, 100, 400, 400); $b.Fill.UniformColor.CMYKAssign(100, 0, 0, 0)
$t = $l.CreateArtisticText(700, 15000, 'MITAD', 1034, 0, 'Arial', 200); $t.Fill.UniformColor.CMYKAssign(0, 0, 0, 100)
$doc.PublishToPDF("$PSScriptRoot\mesa_larga.pdf")
$doc.Dirty = $false; $doc.Close()
"OK"
