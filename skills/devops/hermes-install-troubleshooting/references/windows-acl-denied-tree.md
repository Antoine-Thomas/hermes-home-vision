# Arbre d'install refuse au non-eleve — forensique ACL

Classe de panne : une execution NON ELEVEE de `hermes` (update, venv, plugin, launcher) echoue avec
`WinError 5` sur un chemin de `tools\` ou `plugins\`, alors que la meme commande en admin passe.
Ce n'est pas un fichier manquant, ni une install corrompue : c'est une DACL par objet.

## 1. Signatures d'entree

- `[WinError 5] Acces refuse: '...\tools\python-<ver>-<arch>\python.exe'`
- `uv venv` : `Caused by: Could not find a suitable Python executable for the virtual environment
  based on the interpreter: ...\tools\python-<ver>-<arch>\python.exe`
- `python: install failed: [WinError 5] ... .previous-python-<ver>-<arch>\DLLs\<dll>`
- `Test-Path` / `Get-Item` / `takeown` / `icacls` qui rendent un refus ou « chemin introuvable » sur
  un dossier dont on vient de lister le contenu.

## 2. Anatomie de la DACL cassee

```
D:P(A;OICI;FA;;;OW)(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)
D:P  = DACL PROTEGEE : l'heritage du parent est coupe (AreAccessRulesProtected = True)
OW   = S-1-3-4 "DROITS DU PROPRIETAIRE"  -> FullControl pour le PROPRIETAIRE de l'objet
SY   = SYSTEM            -> FullControl
BA   = Administrateurs   -> FullControl
      -> AUCUNE ACE pour l'utilisateur : rien pour lui si le proprietaire est Administrateurs
```

| | dossier sain | dossier casse |
|---|---|---|
| DACL | heritee (`D:AI(...)`) | protegee (`D:P(...)`) |
| ACE utilisateur | `<user>:(OI)(CI)(F)` presente | absente |
| ACE Codex/sandbox | heritee du parent | heritee du parent (non determinante) |
| DENY | aucun | aucun (ne PAS chercher un DENY) |

## 3. Regle du proprietaire (le point decisif)

L'ACE `OW` (OWNER RIGHTS) accorde FullControl au **proprietaire enregistre de l'objet**, pas a
l'utilisateur qui interroge. Donc :

- proprietaire = `BUILTIN\Administrateurs` (objet cree par un processus ELEVE, comportement par
  defaut pour un membre du groupe Administrateurs) -> le jeton filtre n'a rien -> `WinError 5` ;
- proprietaire = l'utilisateur -> il conserve le controle total -> l'objet **fonctionne** malgre une
  DACL identique en apparence. C'est ce qui explique des voisins du meme dossier qui marchent
  (`node`, `npm`, `uv`, `ffmpeg`) et d'autres non (`python`, `git`, `cua-driver`).

Lire le proprietaire (`Get-Acl` -> `.Owner`, ou `dir /q`) **avant** de conclure quoi que ce soit sur
une DACL protegee.

## 4. SIDs utilisables par un jeton NON ELEVE

Utilisables : SID de l'utilisateur, Utilisateurs (S-1-5-32-545), Tout le monde (S-1-1-0),
Utilisateurs authentifies (S-1-5-11), INTERACTIF (S-1-5-4), OUVERTURE DE SESSION DE CONSOLE (S-1-2-1),
Groupe des invites (S-1-5-32-546).
A NE PAS compter : Administrateurs (S-1-5-32-544) — sous UAC il est monte en **refus uniquement**
dans le jeton filtre ; CREATOR OWNER (S-1-3-0) — ne s'applique qu'a la creation d'enfants.

## 5. Reproduire le refus sans toucher aux ACL

1. Ecrire un `.bat` dans le scratch qui enchaine les tests et redirige tout dans un fichier :
   `whoami /groups`, `dir /a "..."`, `type "...\fichier"`, `"...\python.exe" --version`, plus des
   temoins sains (dossier parent, un dossier herite normal). Un `.bat` construit ses chemins par
   `%LOCALAPPDATA%` : c'est la seule forme ou le chemin arrive intact (cf. `windows-path-handling`).
2. `runas /trustlevel:0x20000 "<scratch>\probe.bat"` — pas de mot de passe demande, et le jeton
   reproduit le refus.
3. Lire la sortie : elle est en UTF-16 -> `tr -d '\0' < sortie.txt > sortie.clean.txt` avant `grep`.
4. Verifier que le jeton est du bon type : `BUILTIN\Administrateurs` doit porter la mention
   `Groupe utilise pour les refus uniquement`.
5. Lecture attendue : `dir` sur l'objet casse -> `Fichier introuvable` (exit 1) ; `type` ->
   `Acces refuse` (exit 1) ; `python.exe --version` -> `Acces refuse` (**exit 5 = WinError 5**) ; les
   temoins sains -> exit 0.

## 6. Perimetre et faux positif

`scripts/find-denied-tree.ps1 -Root <home>` — le perimetre reel est souvent des centaines d'objets :
un `tools\<outil>` entier (git : >1200 entrees), un `plugins\<nom>`, parfois `telemetry\*` et des
profils. Ne reparer que la cible du message d'erreur laisse une install qui recassera au prochain
outil sollicite.
Faux positif a ignorer : un fichier nomme `nul` (artefact d'une redirection bash) rend
`ACL ILLISIBLE` ; il ne s'agit pas d'un objet a reparer.

## 7. Reparation

```
icacls "<dir>" /inheritance:e /grant "%USERNAME%:(OI)(CI)F" /T /C
```

- `/inheritance:e` reactive l'heritage : suffisant quand le parent (`tools\`, `plugins\`, la racine
  du home) porte encore `<utilisateur>:(OI)(CI)(F)` — le verifier avant (`icacls "<parent>"`).
- Un `takeown` explicite n'est PAS necessaire : rendre l'heritage redonne l'acces sans changer le
  proprietaire. Ne pas modifier le proprietaire « pour faire propre ».
- Ordre : perimetre mesure -> accord de l'utilisateur -> `icacls` -> re-scan (le `TOTAL_ANOMALIES`
  doit retomber a 0 ou ne garder que le faux positif `nul`) -> relancer `hermes update` ensuite.
- Ne rien reparer tant que l'ECRIVAIN de la DACL (voir 8) peut relancer son install : la DACL
  protegee est reappliquee au prochain outil installe.

## 8. Causes eliminees / ce que la mesure ne prouve pas

Mesure, sur ce type de dossier :

- **Aucune ACE DENY nulle part** — une chasse au `DENY` est une fausse piste ; tout le blocage vient
  de l'ABSENCE d'ACE utilisable.
- **`git clone`, `mkdir`, `cp` ne produisent PAS cette DACL** (test en scratch : DACL heritee saine).
  Donc ne pas accuser git ni l'extraction d'archive.
- **Le code Hermes ne contient pas cet ecrivain** : seul un texte d'aide `icacls ... /grant:r`
  (message d'erreur d'install de plugin) et un GRANT AppContainer (`S-1-15-2-2`) cote desktop. Ne pas
  partir « corriger le code » sur cette base.
- La forme `OWNER RIGHTS + SYSTEM + Administrateurs` est celle d'une **DACL par defaut de processus
  tournant dans un contexte sandboxe** ; sur un parc qui heberge un sandbox de ce type (utilisateurs
  et groupe dedies, ACE heritable posee sur `%LOCALAPPDATA%`), c'est le candidat a VERIFIER, pas un
  fait etabli. Le dire comme hypothese dans le rapport, avec la mesure qui la soutient.

## 9. Ce que le rapport doit contenir

Pour chaque dossier de la question : existe/absent, proprietaire, resume d'ACL, ecart avec un dossier
sain de reference ; plus le total du perimetre, le resultat du test a jeton restreint (exit codes), et
les ecarts entre la premisse de l'utilisateur et la mesure (par ex. un fichier annonce absent qui
existe, ou une date d'incident qui ne correspond a aucun objet casse).
