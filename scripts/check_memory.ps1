# check_memory.ps1 - Alerte saturation MEMORY.md / USER.md
# Lit la taille des fichiers memoire et alerte si proche de la limite.
# Seuils : MEMORY.md > 2100 chars, USER.md > 1300 chars.
# Suggestion : archiver les entrees > 90 jours vers SiYuan 'journal / Archive MEMORY'.
# Usage : powershell -NoProfile -ExecutionPolicy Bypass -File check_memory.ps1
# NB : texte en ASCII pur (les accents cassent PowerShell 5.1 sans BOM).

$hermesDir = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA + "\hermes" } else { Join-Path $env:USERPROFILE "AppData\Local\hermes" }
$memFile   = Join-Path $hermesDir "memories\MEMORY.md"
$userFile  = Join-Path $hermesDir "memories\USER.md"

$memChars = 0; $userChars = 0
if (Test-Path $memFile) { $memChars = (Get-Content $memFile -Raw -Encoding UTF8).Length }
if (Test-Path $userFile) { $userChars = (Get-Content $userFile -Raw -Encoding UTF8).Length }

# Limites (seuil d'alerte)
$memLimit  = 2100
$userLimit = 1300

Write-Host ("[check_memory] MEMORY.md : {0} / {1} chars" -f $memChars, $memLimit)
Write-Host ("[check_memory] USER.md   : {0} / {1} chars" -f $userChars, $userLimit)

$alert = $false

if ($memChars -gt $memLimit) {
  Write-Host ""
  Write-Host "[ALERTE] MEMORY.md sature : $memChars / $memLimit chars" -ForegroundColor Red
  Write-Host "  Une decision de plus risque d'etre tronquee silencieusement."
  Write-Host "  Suggestion : archiver les entrees > 90 jours vers SiYuan 'journal / Archive MEMORY'."
  $alert = $true
}

if ($userChars -gt $userLimit) {
  Write-Host ""
  Write-Host "[ALERTE] USER.md sature : $userChars / $userLimit chars" -ForegroundColor Red
  Write-Host "  Le profil est proche de la limite, consolider les entrees redondantes."
  $alert = $true
}

if (-not $alert) {
  Write-Host "[check_memory] OK - aucune memoire saturee."
}

# Code de sortie : 0 = OK, 1 = alerte (utile pour planification/notifications)
if ($alert) { exit 1 } else { exit 0 }