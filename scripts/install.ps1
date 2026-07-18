# Compass one-shot install (Windows PowerShell)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not (Test-Path (Join-Path $Root "packages"))) {
  $Root = Split-Path -Parent $Root
}
Set-Location $Root

Write-Host "== Compass install =="
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { throw "Need Python 3.10+ on PATH" }

Write-Host "-- pip editable packages"
python -m pip install -e "packages/compass-core[dev,studio]"
try { python -m pip install -e packages/compass-mcp } catch { Write-Host "(optional) compass-mcp skipped" }
try { python -m pip install "mcp>=1.0" } catch { Write-Host "(optional) mcp skipped" }
try { python -m pip install -r apps/studio/requirements.txt } catch { Write-Host "(optional) studio reqs partial" }

$SkillSrc = Join-Path $Root "skill"
$Dest = "d:\PycharmProjects\pythonProject\.cursor\skills\compass"
if (-not (Test-Path (Split-Path $Dest))) {
  $Dest = Join-Path $env:USERPROFILE ".cursor\skills\compass"
}
if (Test-Path $Dest) { Remove-Item -Recurse -Force $Dest }
Copy-Item -Recurse $SkillSrc $Dest
Write-Host "Skill installed -> $Dest"

Write-Host ""
Write-Host "Done. Try: python -m compass_core.cli --help"
Write-Host "Set COMPASS_ROOT=$Root\content"
