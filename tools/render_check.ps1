# Adapted from hssling/india-tb-acf-campaign (MIT), tools/render_check.ps1 (itself adapted from hssling/india-state-tb-score); modified: default folder manuscript\submission
# Export the submission .docx files to PDF through Word (own instance) and report page and table counts.
# Usage: powershell -NoProfile -File tools\render_check.ps1 [<submission dir>]   (default: manuscript\submission)
# PDFs go to <submission dir>\_render, one line per file, then the pages each table spans.
param([string]$Sub = (Join-Path (Split-Path $PSScriptRoot -Parent) "manuscript\submission"))
$rd = Join-Path $Sub "_render"
New-Item -ItemType Directory -Force $rd | Out-Null
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  foreach ($f in (Get-ChildItem -Path $Sub -Filter "*.docx" | Sort-Object Name)) {
    $n = $f.BaseName
    $d = $word.Documents.Open($f.FullName, $false, $true)
    $d.Repaginate()
    $d.ExportAsFixedFormat("$rd\$n.pdf", 17)
    "$n pages=$($d.ComputeStatistics(2)) tables=$($d.Tables.Count)"
    $i = 0
    foreach ($t in $d.Tables) {
      $i++
      $first = $t.Range.Characters.First.Information(3)
      $last = $t.Range.Characters.Last.Information(3)
      "  table $i : rows $($t.Rows.Count), pages $first-$last"
    }
    $d.Close(0)
  }
} finally { $word.Quit() }
