# Cheatsheet — Hermes, WordPress local, vidéo IA (15/09/2026)

Chemins réels sur cette machine :
- Hermes : `C:\Users\searc\AppData\Local\hermes` (config : `config.yaml`, skills : `skills\`)
- Local (ex-by Flywheel) : `C:\Users\searc\AppData\Local\Programs\Local`
- Sites Local : `C:\Users\searc\Local Sites\<site>`
- PHP de Local : `%LOCALAPPDATA%\Programs\Local\resources\extraResources\lightning-services\php-8.2.29+0\bin\win64\php.exe`
- WP-CLI : `C:\wp-cli\wp.bat` (appelle le PHP de Local) — la commande nue `wp` tombe sur un fichier vide de System32
- Scripts vidéo volet 4 : `C:\Users\searc\Desktop\hermes_tuto_v4`
- Dépôt des skills WP : `C:\Users\searc\Code\hermes-wordpress-skills`

## Hermes

```
hermes --version                       # v0.21.2 (2026.9.11)
hermes tools                           # toolsets disponibles / actifs
hermes memory                          # mémoire persistante
hermes skill run <skill> -- <args>     # exécuter un skill
/skills                                # (en session) lister les skills chargés
skill_view(name='<skill>')             # (outil) charger un skill
```
Skills WordPress installés : `local-flywheel-setup`, `wordpress-site-management`,
`wp-cli-automation`, `wordpress-backup-restore`, `wordpress-deployment` (catégorie `wordpress`).

## WP-CLI (WordPress local)

```
"C:\wp-cli\wp.bat" --info                                    # dans un dossier de site
"C:\wp-cli\wp.bat" plugin list --status=active
"C:\wp-cli\wp.bat" plugin install woocommerce --activate
"C:\wp-cli\wp.bat" language core install fr_FR --activate
"C:\wp-cli\wp.bat" post create --post_type=product --post_title="Produit test" --post_status=publish
"C:\wp-cli\wp.bat" db export backup.sql
"C:\wp-cli\wp.bat" search-replace 'monsite.local' 'prod.monsite.fr' --all-tables
```
Sans le .bat : `"<php de Local>" "C:\wp-cli\wp-cli.phar" <commande>`

## Sauvegarde et déploiement (skills Hermes)

```
hermes skill run wordpress-backup-restore -- backup --site=monsite.local
hermes skill run wordpress-deployment     -- deploy --site=monsite.local \
      --target=prod.monsite.fr --ssh-user=deploy --ssh-host=monserveur.fr
```

## Local by Flywheel

```
# version installee (rien a mettre a jour : 10.1.2.0)
powershell "(Get-Item \"$env:LOCALAPPDATA\Programs\Local\Local.exe\").VersionInfo.ProductVersion"
# sites
ls "$USERPROFILE/Local Sites"
# certificats SSL locaux
ls "$APPDATA/Local/run/router/nginx/certs"
```
Mise à jour (si un jour disponible) : menu de l'application > Check for Updates.
Les sites vivent dans `%USERPROFILE%\Local Sites`, ils ne sont pas touchés par une mise à jour.

## Vidéo IA locale (déjà installée)

```
# venvs existants
ls "$LOCALAPPDATA/hermes/data/video_youtube"     # LatentSync, liveportrait, sadtalker, wav2lip, musetalk, echomimic_v2
ls "$LOCALAPPDATA/hermes/data/xtts/venv"         # clonage vocal XTTS

# volet 4 : chaine complete (source video 4K -> avatar parlant)
cd "$HOME/Desktop/hermes_tuto_v4"
python boucle_p1002837.py                        # choix de la fenetre de boucle
python prep_p1002837.py 55 254 --no-fade --suffix=_clean
python run_latentsync_v8b.py                     # segments de 48 s (multiple du cycle ping-pong)
V4_KEEP=1.00 V4_LIPALIGN=1 python assemble_v6.py run
python verifier_v6.py ; python diag_sauts.py <video> <wav> 1200 2400 3600 4800 6000
```
Skill de référence : `talking-head-video-8gb` (v1.8) — deux branches à ne pas confondre,
source vidéo (LatentSync) et source photo (LivePortrait/SadTalker/Wav2Lip).

## LTX-2 / ComfyUI — NON INSTALLÉS

Rien à documenter tant que l'installation n'est pas faite. Éléments vérifiés avant de lancer :
1 094 Go libres sur C:, VRAM 8 Go, RAM 63,9 Go. Installer sur C: (NVMe) et non sur F:/H:.

## AirLLM — NON INSTALLÉ

Non recommandé sur cette machine (inférence par streaming disque). Pour un modèle local,
utiliser Ollama, déjà installé : `ollama serve` puis provider Hermes
`http://127.0.0.1:11434/v1` (déjà déclaré dans config.yaml).

## Liens

- Hermes Agent : https://hermes-agent.nousresearch.com/docs
- Hermes (dépôt) : https://github.com/NousResearch/hermes-agent
- Skills WordPress : https://github.com/Antoine-Thomas/hermes-wordpress-skills
- Local : https://localwp.com/ — téléchargements : https://localwp.com/releases/
- WP-CLI : https://make.wordpress.org/cli/handbook/
- AirLLM : https://github.com/lyogavin/airllm

## Surveillance système

```
nvidia-smi --query-gpu=utilization.gpu,memory.used,power.draw --format=csv,noheader
powershell "Get-CimInstance Win32_OperatingSystem | Select FreePhysicalMemory,TotalVisibleMemorySize"
netstat -ano | grep LISTENING | awk '{print $2}' | sed 's/.*://' | sort -n -u
```
