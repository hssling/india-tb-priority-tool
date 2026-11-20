# Adapted from hssling/india-tb-acf-campaign (MIT), tools/word_count_word.ps1 (itself adapted from hssling/india-state-tb-score); modified: Evaluation and Program Planning sections (numbered headings 1. Introduction to 7. Conclusions; subsection headings N.N. inside them) and the whole-text count for the 10,000-word limit
# Count the abstract, the main text and the whole text of the anonymised manuscript in Microsoft Word.
# Usage: powershell -NoProfile -File word_count_word.ps1 <docx> <out.json>
# Opens its own Word instance (read-only, hidden) and quits only that instance.
# Abstract: the paragraphs between the "Abstract" heading and the Keywords line (Keywords excluded).
# Main text: the text under the headings "1. Introduction" to "7. Conclusions" (subsection headings
# such as "2.1. ..." stay inside it), headings excluded; it ends at any other heading (Funding).
# Total: every paragraph from the title to the "References" heading, headings included, tables
# excluded (the journal's limit of 10,000 words excludes references, tables and figures).
param([string]$Docx, [string]$Out)
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  $d = $word.Documents.Open($Docx, $false, $true)
  $state = ""; $abs = 0; $main = 0; $total = 0; $done = $false; $sec = [ordered]@{}; $cur = ""
  foreach ($p in $d.Paragraphs) {
    $t = $p.Range.Text.Trim()
    if ($t -eq "References") { $done = $true }
    if ($p.Range.Information(12)) { continue }          # inside a table
    $n = $p.Range.ComputeStatistics(0)
    if (-not $done) { $total += $n }
    $isHeading = $p.OutlineLevel -lt 10
    if ($isHeading) {
      if ($t -eq "Abstract") { $state = "abs" }
      elseif ($t -match '^[1-7]\. (Introduction|Methods|Results|Discussion|Lessons learned|Limitations|Conclusions)$') {
        $state = "main"; $cur = $Matches[1]; $sec[$cur] = 0 }
      elseif ($t -match '^\d+\.\d+\. ' -and $state -eq "main") { }
      else { $state = "" }
      continue
    }
    if ($t -like "Keywords:*") { $state = ""; continue }
    if ($state -eq "abs") { $abs += $n }
    if ($state -eq "main") { $main += $n; $sec[$cur] += $n }
  }
  $pages = $d.ComputeStatistics(2)
  $d.Close(0)
  $parts = @()
  foreach ($k in $sec.Keys) { $parts += ('"' + $k + '": ' + $sec[$k]) }
  $json = '{"abstract": ' + $abs + ', "main_text": ' + $main + ', "total": ' + $total + ', "sections": {' + ($parts -join ', ') + '}, "pages": ' + $pages + '}'
  Set-Content -Path $Out -Value $json -Encoding ascii
} finally { $word.Quit() }
