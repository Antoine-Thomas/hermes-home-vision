# Modele de script ENFANT ELEVE (a copier et adapter) - voir Regle 8 de SKILL.md
#
# Pourquoi ce squelette : chaque RunAs coute une validation UAC, donc on regroupe dans UNE seule
# fenetre elevee l'inventaire (lecture seule) PUIS l'action, et le script ecrit un rapport que la
# session NON elevee relit et re-verifie. Trois pieges y sont deja neutralises :
#   - ASCII pur (PowerShell 5.1 relit l'UTF-8 sans BOM en ANSI : les accents cassent le parsing) ;
#   - variables nommees explicitement ($out / $item / $ligne) car PowerShell est insensible a la
#     casse : $l et $L sont la MEME variable et un foreach ($l ...) ecrase le tableau de rapport ;
#   - jamais $args (variable automatique) pour construire une ligne de commande.
#
# Appel depuis la session non elevee :
#   powershell -NoProfile -Command "Start-Process -Verb RunAs -Wait -PassThru -FilePath 'powershell' `
#     -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','<ce script>'"
# NB : -Verb RunAs interdit -RedirectStandardOutput/-RedirectStandardError -> d'ou Start-Transcript.

$ErrorActionPreference = 'Continue'
$scr = 'C:\Users\<utilisateur>\AppData\Local\hermes\cache\scratch\<tache>'
New-Item -ItemType Directory -Path $scr -Force | Out-Null
Start-Transcript -Path (Join-Path $scr 'child_transcript.txt') -Force | Out-Null

$out = New-Object System.Collections.ArrayList
[void]$out.Add("ENFANT ELEVE - " + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
[void]$out.Add("utilisateur = " + ([Security.Principal.WindowsIdentity]::GetCurrent()).Name + " | eleve = " +
    ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator))

# --- 1. INVENTAIRE AVANT (lecture seule) : a faire TOUJOURS avant l'action ---
# ex : hashes, tailles, mtimes, etat du service. Donner a chaque copie son sha256 pour que la
# session non elevee puisse re-verifier elle-meme (une sauvegarde non re-verifiee n'est pas opposable).

# --- 2. ACTION ------------------------------------------------------------
# Chemin COMPLET des binaires natifs : un nom nu (ex. 'msiexec.exe') peut ne rien lancer dans
# l'enfant sans rendre ni objet ni code de sortie.
$exe = 'C:\Windows\System32\msiexec.exe'
$cmdArgs = @('/i', '<chemin msi>', '/qn', 'WAZUH_MANAGER=127.0.0.1', '/l*v', (Join-Path $scr 'msi.log'))
# JAMAIS $args ci-dessus : variable automatique, l'assignation serait ignoree.

$proc = $null; $code = 'NON RETOURNE'
try { $proc = Start-Process -FilePath $exe -ArgumentList $cmdArgs -Wait -PassThru -ErrorAction Stop; $code = $proc.ExitCode }
catch { [void]$out.Add('EXCEPTION Start-Process : ' + $_.Exception.Message) }
[void]$out.Add('objet retourne : ' + $(if ($proc) { 'oui (Id=' + $proc.Id + ')' } else { 'AUCUN' }) + ' | code = ' + $code)

# --- 3. DISCRIMINANT : l'action a-t-elle REELLEMENT eu lieu ? ----------------
# Ne jamais conclure depuis un code de sortie seul. Pour MSI : journal present ET non vide, sinon
# repli par operateur d'appel, seul moyen fiable d'obtenir le code.
if (-not (Test-Path -LiteralPath (Join-Path $scr 'msi.log'))) {
    [void]$out.Add('journal MSI ABSENT -> l action n a pas eu lieu, repli par operateur d appel')
    & $exe @cmdArgs
    [void]$out.Add('code (\$LASTEXITCODE) = ' + $LASTEXITCODE)
}

# --- 4. ET PUIS SEULEMENT l'arret / l'etat, avec attente BORNEE de l'effet ----
# ex : Stop-Service -Name <svc> -Force ; Set-Service -StartupType Manual ; boucle de 12 x 5 s qui
# sort des que l'effet est la. Un demarrage automatique laisse en place annule le travail de l'etape 1.

$out | Out-File -FilePath (Join-Path $scr 'report.txt') -Encoding ascii
Stop-Transcript | Out-Null
exit 0
