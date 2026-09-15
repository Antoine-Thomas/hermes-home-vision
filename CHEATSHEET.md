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

## LTX-2.3 / ComfyUI — OPÉRATIONNEL (mesuré le 15/09/2026)

Génération texte -> vidéo validée de bout en bout : `640x384, 25 images, 24 i/s, 8 étapes, mode
distilled, offload=True`. Sortie H.264 **avec audio** (LTX-2.3 est un modèle audio-vidéo).

| | à froid | à chaud |
|---|---|---|
| total | 132,79 s | 205,11 s |
| par image | 5,31 s | 8,20 s |
| par étape | 16,60 s | 25,64 s |

Soit 127 a 197 fois le temps reel : compter 2 a 3,5 minutes par seconde de video generee.

Piege a connaitre (cout : une journee) : `load_sd` peut remettre **0 cle sur 4444** quand les
operations de renommage du noeud ne correspondent pas au GGUF. Symptome : 4186 parametres sur le
disque virtuel, puis `Cannot copy out of meta tensor`. Diagnostic express :
`grep "Uninitialized parameters" comfyui.log` (le constructeur nomme lui-meme les modules vides),
puis comparer le nombre de cles du dictionnaire au nombre de parametres du modele. Correctif
applique dans `LTX2/ltx_core/loader/single_gpu_model_builder.py` (fonction `load_sd`) : relire le
GGUF sans operations quand le dictionnaire revient vide.


Dossier : `C:\Users\searc\ComfyUI-LTX` · ComfyUI portable v0.35.0 · python embarqué 3.13
`C:\Users\searc\ComfyUI-LTX\ComfyUI_windows_portable\python_embeded\python.exe`

```
# lancer le serveur (port 8188)
cd /c/Users/searc/ComfyUI-LTX/ComfyUI_windows_portable
./python_embeded/python.exe -s ComfyUI/main.py --listen 127.0.0.1 --port 8188
# interface web
http://127.0.0.1:8188
# test texte -> video par l'API (petit format pour valider)
cd /c/Users/searc/ComfyUI-LTX
"$LOCALAPPDATA/hermes/hermes-agent/venv/Scripts/python.exe" ltx_test.py 640 384 25 8
```

Poids en place (27,7 Go au total) :
```
ComfyUI/models/gguf/ltx-2.3-22b-distilled-1.1-Q4_K_S.gguf   (12,96 Go, transformer)
ComfyUI/models/gguf/gemma-3-12b-it-qat-Q4_0.gguf            ( 8,70 Go, encodeur de texte)
ComfyUI/models/checkpoints/connector-11.safetensors        ( 6,34 Go, connecteurs, MIT)
ComfyUI/models/vae/ltx-2.3-22b-distilled_video_vae.safetensors (1,45 Go)
ComfyUI/models/vae/ltx-2.3-22b-distilled_audio_vae.safetensors (0,36 Go)
```

VRAM limitée (cas de cette machine, 8 Go, Ampere sans FP8 natif) :
- le nœud `LTX2_SM_Model` a un paramètre **`offload`** : le laisser à `True` (streaming des
  couches), c'est l'équivalent du `--offload cpu` de la version Python d'origine ;
- les quantifications GGUF remplacent la quantification fp8 : Q4_K_S tient en VRAM/streaming,
  Q8_0 non ;
- les poids doivent rester sur le NVMe (`C:`), pas sur les SSD externes.

Ne pas confondre les trois branches vidéo (`talking-head-video-8gb`) : A = source vidéo
tournée (LatentSync), B = source photo (LivePortrait/SadTalker/Wav2Lip), C = génération IA
(LTX-2.3 ici). La boucle ping-pong, le découpage et le recadrage des lèvres n'existent QU'en A.

Versions imposées dans le python portable (ne pas « mettre à jour » sans raison) :
transformers 4.57.6 (le nœud casse en 5.x), diffusers 0.36.0 (0.40 exige huggingface-hub>=1.23,
incompatible), opencv-python-headless 5.0.0.93, torch 2.13.0+cu130 (d'origine).

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

## SiYuan — second cerveau (installé le 15/09/2026)

Version 3.8.2 (winget `B3log.SiYuan`, installation par utilisateur, ~747 Mo). Porte la
correction de la CVE d'information disclosure des 3.8.1 et antérieures. La 3.8.3 existe mais
c'est une version de fonctionnalités (Electron, IA), pas un correctif de sécurité.

```
Noyau     : C:\Users\searc\AppData\Local\Programs\SiYuan\resources\kernel\SiYuan-Kernel.exe
Workspace : C:\Users\searc\SiYuan\hermes-projects
Conf      : C:\Users\searc\SiYuan\hermes-projects\conf\conf.json
Interface : http://127.0.0.1:6806   (protégée par accessAuthCode, port local uniquement)
Demarrer  : double-clic sur C:\Users\searc\SiYuan\demarrer_siyuan.cmd
```

ATTENTION, SiYuan a DEUX secrets distincts — c'est le piège de l'installation :
- `accessAuthCode` (conf.json) : ouvre l'interface web. À saisir dans le navigateur au premier accès.
- `api.token` (conf.json, section `api`) : c'est LUI que les API acceptent. C'est cette valeur qui
  va dans `SIYUAN_TOKEN`. Mettre l'accessAuthCode à la place donne `Auth failed [header: Authorization]`.

```
# .env de Hermes (%LOCALAPPDATA%\hermes\.env), deja en place
SIYUAN_TOKEN=<api.token de conf.json>
SIYUAN_URL=http://127.0.0.1:6806
```

```
# test de connexion
curl -s -X POST "${SIYUAN_URL:-http://127.0.0.1:6806}/api/notebook/lsNotebooks" \
  -H "Authorization: Token $SIYUAN_TOKEN" -H "Content-Type: application/json" -d '{}'
# attendu : {"code":0,"msg":"","data":{"notebooks":[...]}}
```

Skill : `productivity/siyuan` (dépôt officiel, `hermes skills install official/productivity/siyuan --yes`).
Prérequis installé : `jq` 1.8.2 (winget `jqlang.jq`) — sans lui toutes les commandes du skill échouent.
Toutes les routes sont en POST, même en lecture ; seules les requêtes SQL SELECT sont admises.

Piège de la première ouverture : l'application graphique écrit son journal dans
`%USERPROFILE%\.config\siyuan\` et plante en `ENOENT` si ce dossier n'existe pas (fenêtre blanche,
noyau jamais lancé). Créer le dossier avant le premier lancement. Le noyau en ligne de commande
(`serve`) est le chemin fiable et sert aussi l'interface web.

### Structure du second cerveau (15/09/2026)

```
hermes-projets        5 doc.   un par site Local (versions, extensions, sauvegardes, acces)
hermes-skills        12 doc.   2 notes d'origine + un par skill reellement utilise
video-ia              3 doc.   branche A LatentSync / B source photo / C LTX-2.3
apprentissage-continu 0 doc.   vide volontairement (Phase 1)
journal               1 doc.   panne LTX-2.3 du 15/09
veille                2 doc.   sources suivies, idees en attente
```

Convention de chaque document : en-tete `> **Statut**` + `> **Derniere mise a jour**`, puis
Fait / Reste a faire / Pieges / Commandes.

```
# reconstruire la structure (n'ecrase rien, ignore ce qui existe deja)
cd /c/Users/searc/SiYuan && python construire_structure.py --dry   # simulation
python construire_structure.py                                     # creation
python gather_sites.py > sites_data.json                           # relire l'etat des sites Local
```

Code d'acces de l'interface : celui choisi par l'utilisateur, dans `conf.json` (section
`accessAuthCode`). Pour le changer : arreter le noyau AVANT d'editer le fichier, sinon il le
reecrit en s'arretant.

Demarrage automatique : tache planifiee utilisateur « SiYuan - noyau second cerveau », a l'ouverture
de session, qui lance `demarrer_siyuan.cmd`.
```
schtasks /query /tn "SiYuan - noyau second cerveau"     # verifier
powershell -c "Start-ScheduledTask -TaskName 'SiYuan - noyau second cerveau'"   # declencher
```
