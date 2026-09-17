# rollback_update.ps1 — Restaure la config, l'environnement, la mémoire et l'état
# depuis le snapshot pris AVANT hermes update (desktop\hermes_install\snapshot).
#
# Usage :  powershell -NoProfile -ExecutionPolicy Bypass -File rollback_update.ps1
# Usage secours : -Source <chemin> -Target <chemin hermes>
#
# Restaure : config.yaml, .env, memories/, state.db (si présent dans le snapshot).

param(
  [string]$Source = "C:\Users\searc\Desktop\hermes_install\snapshot",
  [string]$Target = "$env:LOCALAPPDATA\hermes"
)

Write-Host "=== ROLLBACK UPDATE HERMES ===" -ForegroundColor Cyan
Write-Host "Source : $Source"
Write-Host "Target : $Target"
Write-Host ""

if (-not (Test-Path $Target)) {
  Write-Host "ERREUR : dossier cible absent ($Target)" -ForegroundColor Red
  exit 2
}
if (-not (Test-Path $Source)) {
  Write-Host "ERREUR : snapshot absent ($Source). Rien a restaurer." -ForegroundColor Red
  exit 2
}

# 1. config.yaml
$cfg = Join-Path $Source "config.yaml.pre_update"
if (Test-Path $cfg) {
  Copy-Item $cfg (Join-Path $Target "config.yaml") -Force
  Write-Host "[OK] config.yaml restaure"
} else { Write-Host "[MANQUE] config.yaml.pre_update absent" -ForegroundColor Yellow }

# 2. .env
$envf = Join-Path $Source "env.pre_update"
if (Test-Path $envf) {
  Copy-Item $envf (Join-Path $Target ".env") -Force
  Write-Host "[OK] .env restaure"
} else { Write-Host "[MANQUE] env.pre_update absent" -ForegroundColor Yellow }

# 3. memories/
$mem = Join-Path $Source "memories.pre_update"
if (Test-Path $mem) {
  $memTgt = Join-Path $Target "memories"
  if (Test-Path $memTgt) { Remove-Item $memTgt -Recurse -Force }
  Copy-Item $mem $memTgt -Recurse -Force
  Write-Host "[OK] memories/ restaure"
} else { Write-Host "[MANQUE] memories.pre_update absent" -ForegroundColor Yellow }

# 4. state.db
$db = Join-Path $Source "state.db.pre_update"
if (Test-Path $db) {
  Copy-Item $db (Join-Path $Target "state.db") -Force
  Write-Host "[OK] state.db restaure"
} else { Write-Host "[MANQUE] state.db.pre_update absent (peut etre volumineux / non copie)" -ForegroundColor Yellow }

Write-Host ""
Write-Host "=== ROLLBACK TERMINE ===" -ForegroundColor Green
Write-Host "Il reste a :"
Write-Host "  1. Restaurer le code :  cd '\$env:LOCALAPPDATA\hermes\hermes-agent' ; git reset --hard <commit-precedent>  (ou git stash apply)"
Write-Host "  2. Redemarrer les services : hermes gateway restart ; relancer 'serve' manuellement avec la commande recordee."
Write-Host ""
Write-Host "ATTENTION : ce script restaure data/cache depuis le snapshot du MOMENT du backup. Toute session creee entre backup et rollback est perdue."

exit 0