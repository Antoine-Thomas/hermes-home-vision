---
name: windows-app-install
description: "Use when installing a Windows app from a release."
version: "1.0.0"
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [windows, install, github-release, registry, shortcut]
    category: devops
---

# Installer une application Windows

Installer proprement une application de bureau sur ce parc — Windows 11, **shell de l'agent ELEVE**
(admin sans UAC), GPU parfois occupe par une autre session Hermes — puis PROUVER l'installation et
rapporter les ecarts.

## When to use

- Une mission dit « installer X, version legere, pret a l'emploi » : installeur `.exe`/NSIS, MSI,
  portable `.zip`.
- Telecharger des poids, modeles ou donnees depuis une release GitHub ou le site editeur.
- Verifier une installation existante (version, chemin, raccourci) ou preparer un dossier de travail.
- Session « installation seulement » : aucune inference, aucun calcul GPU a lancer (une autre session
  peut tenir le GPU).

## Procedure

1. **Etat des lieux AVANT tout.** Chercher l'application dans les deux emplacements usuels —
   `C:\Program Files\<App>` et `C:\Users\<user>\AppData\Local\Programs\<App>` — plus le dossier de
   travail annonce, puis `df -h /c` pour l'espace libre. Un dossier de travail absent n'est pas une
   erreur : il sera cree plus loin, le dire et continuer.

2. **Resoudre la release par l'API, jamais par une URL recopiee d'un brief.**
   `curl -sL https://api.github.com/repos/<org>/<repo>/releases/latest`, puis lire `tag_name`,
   `published_at` et **chaque** entree de `assets[]` (nom, `size`, `browser_download_url`).
   Lire la DATE : `latest` peut etre bien plus ancien que suppose — c'est une information a
   rapporter, pas un probleme a corriger. Recette et verification :
   `references/github-release-downloads.md`.

3. **Telecharger et PROUVER le fichier.** `curl -L --retry 3 -f -o <nom> <url>`, puis comparer la
   taille obtenue a `assets[].size` **a l'octet**, prendre le `sha256sum`, et lire les deux premiers
   octets (`head -c 2 <f> | xxd` -> `MZ` = PE, `PK` = archive zip/PyTorch). Une taille qui colle a
   l'octet est la seule preuve qu'on a le bon fichier.

4. **Lancer l'installeur GUI** :
   `powershell -NoProfile -Command "Start-Process -FilePath 'C:\...\<app>.exe'"`, faire cliquer
   l'utilisateur jusqu'au bout, puis verifier l'EFFET (jamais le code de retour).

5. **Fermer ce que l'installeur a lance** si la session doit rester sans calcul GPU :
   `cmd /c "taskkill /F /IM <App>.exe"` (sortie UTF-16 -> `| tr -d '\0'`), puis prouver le compte a
   0 (`Get-Process <App> | Measure-Object | Select -Expand Count`).

6. **Arborescence de travail** : creer les dossiers annonces (vides et prets), et un `README.md` qui
   documente l'arborescence, les ecarts vs la consigne et le mode d'emploi.

## Preuves et rapport

Ce que l'utilisateur attend a la fin, dans cet ordre :

- Version installee : cle `Uninstall` du registre, `HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*`
  **et** `...\WOW6432Node\...\Uninstall\*` -> `DisplayName` / `DisplayVersion`.
- Chemin exact de l'executable, et raccourci Bureau RELU (`TargetPath`).
- Appels `curl` : faire `cd` dans le dossier d'arrivee et passer un nom **relatif**. Un chemin MSYS
  `/c/...` donne a `curl` (binaire natif) echoue en `exit 23` sur une requete pourtant correcte —
  cf. `windows-path-handling`.
- Tailles des fichiers telecharges, arborescence finale (`find . -maxdepth 2`), espace disque
  **avant/apres**, et `nvidia-smi` en fin de session pour montrer que la session n'a rien ajoute.
- **Chaque ecart vs la consigne, liste explicitement**, meme quand le resultat final est
  fonctionnel : chemin d'installation, plage de taille annoncee, noms de fichiers, format des
  donnees. Un ecart non signale se lit plus tard comme un mensonge.

## Pitfalls

### `curl -s -o` sort en `exit 0` sur un corps 404

`curl -sL -o fichier <url>` **reussit** quand le serveur repond `404` avec un corps texte : le
fichier contient la page d'erreur (`Not Found`, 9 octets) et le code est 0. Deux fichiers differents
ont ainsi rendu le **meme sha256**, celui de la chaine `Not Found`. Parades : `-f` (`--fail`, sort non
nul sur code >= 400) **et** comparaison de la taille a `assets[].size` de l'API. Un `du -m` qui
annonce 1 Mo la ou l'API annonce 64 Mo est le seul signal.

### Le shell eleve fait basculer l'installation en per-machine

Un installeur electron-builder `perMachine=false` vise `%LOCALAPPDATA%\Programs\<App>` ; lance depuis
un shell **eleve**, il installe dans `C:\Program Files\<App>`. Le dossier attendu par la consigne est
alors vide et une recherche a cet emplacement conclut a tort a un echec. **Chercher l'application par
le processus** (`Get-Process <App> | Select -ExpandProperty Path -Unique`), puis rapporter le chemin
reel comme ecart. Corollaires : le raccourci du menu Demarrer part en `ProgramData` (per-machine) et
un raccourci Bureau n'est alors **pas** cree automatiquement.

### Un tag peut exister sans porter l'asset annonce

Ne jamais telecharger une URL sans l'avoir confrontee a `assets[]` de l'API de la release : un tag
reel peut ne contenir que d'autres fichiers. Si l'asset annonce n'existe nulle part, choisir la
release qui le porte et rapporter la substitution avec les deux URL.

### Raccourci Bureau : guillemets SIMPLES obligatoires

```
powershell -NoProfile -Command '$s=(New-Object -ComObject WScript.Shell).CreateShortcut("C:\Users\<user>\Desktop\<App>.lnk"); $s.TargetPath="C:\Program Files\<App>\<App>.exe"; $s.WorkingDirectory="C:\Program Files\<App>"; $s.IconLocation="C:\Program Files\<App>\<App>.exe,0"; $s.Save()'
```

En guillemets doubles cote bash, `$s` est mange par le shell et la commande part avec `.TargetPath`
nu (`Vous devez indiquer une expression de valeur apres l'operateur +`). Relire ensuite `TargetPath`
dans une commande elle aussi en guillemets simples : c'est la preuve que le raccourci vise le bon exe.

### Les donnees demandees peuvent etre au mauvais format pour l'outil

Un brief peut demander des fichiers que l'application ne lit pas. Cas mesure — **Upscayl** : il
charge des modeles **NCNN** (paire `.bin` + `.param`, via Settings -> "Add Custom Models" -> dossier
`models`), **pas** les `.pth` PyTorch, qui exigent une conversion prealable par chaiNNer. Regle :
lire le dossier `resources\models\` de l'application et sa documentation avant de telecharger des
poids, puis livrer a la fois **ce qui a ete demande** et **ce qui est reellement chargeable**, en
disant clairement lequel sert a quoi. Details et sources :
`references/github-release-downloads.md`.

### Une appli non signee n'est pas un blocage

`Get-AuthenticodeSignature` qui rend `NotSigned` est un **constat**, pas une raison d'arreter :
le consigner et verifier la provenance autrement (taille + sha256 confrontes a l'API de la release).
Un stub NSIS electron-builder est en outre un binaire **i386** meme pour une application x64
(`machine: 0x014c`) : ce n'est pas le signe d'un mauvais asset.

## Voir aussi

- `windows-path-handling` — formes de chemins et d'arguments a donner aux binaires natifs
  (`curl`, `icacls`, PowerShell), UTF-16 des sorties, echappement des commandes PowerShell.
- `windows-ops` — operations Windows (GPU Docker/WSL2, taches planifiees, fenetres console).
