# Modifier `config.yaml` (et livrer un script qui le modifie) sans casser l'install

`config.yaml` pilote gateways, toolsets et plateformes. Une édition ratée ne se voit pas tout de
suite : la config se recharge au prochain démarrage du gateway, et un bloc supprimé passe inaperçu
jusqu'à ce qu'une fonctionnalité manque. Procédure et garde-fous ci-dessous.

## 1. Choisir le bon outil d'écriture

| Type de clé | Outil | Remarque |
|---|---|---|
| Scalaire (`delegation.max_spawn_depth`, `platforms.a2a.enabled`, `model`) | `hermes config set <clé> <valeur>` | Sûr. Valider avec `hermes config check`. |
| Liste (`platform_toolsets.cli`, `known_plugin_toolsets.*`) | **Jamais `config set`** | La liste entière est remplacée par la valeur scalaire. |
| Suppression d'une clé | `hermes config unset <clé>` | Retour à l'état par défaut (clé absente), préférable à `false`. |

**`hermes config set` sur une clé liste clobbe la liste.** Vérifié :
`hermes config set platform_toolsets.cli a2a` remplace les 17 toolsets par la chaîne `a2a` — et
n'avertit (« not a recognized config key ») qu'**après** l'écriture. Pour une liste : édition
textuelle ciblée du bloc dans le fichier, puis relecture avec `hermes config get <clé>`.

Après tout `config set`, relire **et** vérifier l'emplacement : `grep -n "^<section>:" -A 14 config.yaml`.
Une clé pointée peut atterrir sous une section voisine (le `config get` réussit quand même, donc il
ne prouve pas le placement).

## 2. Ne jamais faire d'aller-retour YAML complet

`ruamel.yaml` (load → dump) **reformate tout le fichier** : réindentation des séquences, rewrapping
des blocs de prompts, normalisation des `|`/`>`. Sémantiquement identique, diff inexploitable, et
impossible à relire. Sur un fichier live : édition textuelle ciblée uniquement (lecture du texte,
remplacement du seul bloc visé, réécriture avec le même style de fin de ligne et sans BOM).

### Regex d'édition : une ancre consommée doit être restituée

Un motif ancré sur l'en-tête de section (`(?m)^platform_toolsets:...`) **consomme cette ligne** :
si le remplacement ne la réémet pas (groupe nommé restitué), c'est le bloc entier qui disparaît du
fichier, sans erreur. Comparer les hash après édition — c'est le seul contrôle qui l'attrape.

## 3. Vérifier l'édition sur une COPIE (jamais en direct)

Le harness minimal, à mettre dans le script livré sous forme de commutateur `-SelfTest` qui sort
**avant** les étapes à effet de bord :

1. `Copy-Item config.yaml $temp` ;
2. appliquer l'édition : `add` → 17 → 18 éléments ;
3. réappliquer : `add` doit être **idempotent** (`modifie=False`) ;
4. `remove` → retour à 17 ; réappliquer `remove` → idempotent ;
5. `Get-FileHash -Algorithm MD5` sur l'original et sur la copie après `add`+`remove` → **identiques**
   (comparaison octet à octet, pas seulement texte normalisé) ;
6. ne jamais écrire dans le fichier live dans ce mode (`-ConfigPath` en paramètre pour pointer la copie).

Un script destructeur se teste par ailleurs **sans l'exécuter** :

```powershell
$e = $null
[System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$null, [ref]$e)
if ($e.Count) { $e | ForEach-Object { $_.Message + ' @ ligne ' + $_.Extent.StartLineNumber } }
```

## 4. Isoler une commande CLI Hermes pour connaître son comportement réel

Pour savoir ce que fait vraiment `hermes config set/unset/get` sans risquer le fichier live :

```bash
T="$LOCALAPPDATA/Temp/hermes_home_test"; mkdir -p "$T"; cp "$LOCALAPPDATA/hermes/config.yaml" "$T/"
HERMES_HOME="$T" hermes config path          # confirme l'isolation : pointe vers la copie
HERMES_HOME="$T" hermes config set <clé> <valeur>
HERMES_HOME="$T" hermes config check
```

`HERMES_HOME` est respecté par `hermes config` : c'est la méthode pour reproduire un piège de config
(destruction de liste, mauvaise section, clé inconnue) et le documenter au lieu de le deviner.

## 5. Valider le chemin d'écriture d'un script Python destructeur

Ne pas se contenter du mode « simulation » : importer le module et rediriger sa cible vers un
dossier temporaire exécute le vrai code (backup, écriture, rollback, codes de sortie) sans toucher
la prod.

```python
spec = importlib.util.spec_from_file_location("mod", chemin_script)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
mod.DOSSIER_CIBLE = dossier_temporaire    # + mod.LOG si le script journalise
sys.argv = ["script.py", "--auto"]; code = mod.main()
```

Couvrir explicitement : cas nominal, rollback (l'écriture ne suffit pas à repasser sous le seuil),
garde-fou qui doit refuser d'écrire, et dépendance externe injoignable. Puis nettoyer l'état externe
créé par le test (doc créé dans SiYuan, fichier temporaire) et **le vérifier** par une relecture.

## 6. Après toute écriture vers un système externe, relire la cible

Un `code = 0` renvoyé par une API ne prouve pas le contenu. Relire (export/lecture du document,
`hermes config get`, `Get-ScheduledTaskInfo`, log du script) et affirmer sur la base de cette
relecture. Vaut pour SiYuan, la config, les tâches planifiées.

## 7. Versionner les scripts livrés

Les scripts créés dans `%LOCALAPPDATA%\hermes\scripts\` sont copiés dans `Desktop\hermes_install` :
`siyuan/` pour la mémoire et le RAG (`desaturer_memoire.py`, `creer_tache_*.ps1`), `hermes/` pour la
plateforme et le gateway (`activer_a2a.ps1`). Confirmer `md5sum` identique des deux côtés avant de
committer, et ne jamais committer le journal d'exécution.

## 8. PowerShell 5.1 : texte ASCII pur

Un `.ps1` écrit en UTF-8 **sans BOM** et contenant des accents s'affiche mutilé en PowerShell 5.1.
Écrire les messages en ASCII (accents retirés), et garder les accents dans les seuls fichiers
Python/Markdown (eux lus en UTF-8 explicite).
