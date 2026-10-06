# Espace gagne : logique vs reel

Une passe de suppressions se juge sur l'espace que le VOLUME rend, pas sur la somme des tailles
supprimees. Ce fichier donne les quatre sondes et la reconciliation.

## 1. Lire l'espace libre en octets exacts

```powershell
$d = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
'{0:N0} o libres ({1:N2} GiB)' -f $d.FreeSpace, ($d.FreeSpace/1GB)
```

`df -h` arrondit au GiB : un Go rendu peut ne pas bouger la colonne. Mesurer avant le premier lot et
apres le dernier — jamais lot par lot, les writers du systeme consomment en parallele.

## 2. Reconcilier

```
gain_mesure = somme(cibles autonomes) + part_reellement_liberee(caches partages)
              - octets_partis_en_corbeille
```

Exemple mesure sur une passe reelle : 7 cibles autonomes (6,22 GiB) + cache uv (6,54 GiB rendus sur
16,75 GiB supprimes) - 4,57 GiB partis en corbeille = **8,19 GiB** de gain, exactement ce que le volume
avait rendu. Un ecart qui ne se referme pas designe un consommateur a trouver (§5) ou un partage a
chiffrer (§3) : il se nomme dans les anomalies, il ne s'arrondit pas.

Prevoir l'ecart des l'audit : un profil dont la taille logique depasse nettement l'occupation reelle
ne rendra jamais ce delta, quel que soit le nombre de cibles supprimees.

## 3. Sonde hardlink (caches partages)

```powershell
fsutil hardlink list 'C:\chemin\vers\fichier.dll'
```

Chaque ligne rendue = un lien VIVANT. Deux chemins dans des dossiers differents = les blocs ne sont
comptes qu'une fois sur le volume. Mesure : `torch_cuda.dll` (1 176 Mo) portait trois liens — venv
`hermes-agent`, venv `liveportrait`, venv `wav2lip` — donc un cache qui le portait ne rend rien a la
suppression tant qu'un venv le reference. Les installateurs qui dedoublonnent (uv, pnpm, les clones de
venvs) produisent ce montage par construction.

Corollaire : `du` et l'enumeration .NET additionnent des tailles LOGIQUES. Sur un parc ou les venvs se
partagent les blocs, la somme d'un arbre surestime l'occupation reelle — le seul arbitre est `FreeSpace`.
Un fichier peut donc etre "de N Go" dans un tableau et valoir bien moins pour le volume.

Le partage traverse les ARBRES, pas seulement les venvs d'un meme parc : un pack d'inference qui
re-reference les poids d'un dossier d'entrainement, ou deux sous-dossiers d'un meme outil qui attendent le
meme modele sous deux noms (`models\gguf\<modele>` et `models\text_encoders\<modele>`), le fait souvent par
LIEN. Avant de sommer un tableau de tailles de packs :

1. lister les fichiers de meme nom et de meme taille presents dans deux packs differents (indice : meme
   taille ET meme mtime a la seconde) ;
2. passer les plus gros au `fsutil hardlink list` ;
3. retirer du total logique tout ce qui rend 2 liens ou plus.

Mesure : 3 paires (un modele de 8,70 Go et un de 12,96 Go sous deux noms dans le meme outil, un
checkpoint de 6,94 Go partage entre deux packs) = **28,60 Go comptes deux fois** sur 249,81 Go logiques.
Les annoncer comme "doublons a supprimer" aurait promis 28,60 Go que le volume n'aurait jamais rendus.

## 4. Sonde corbeille

```powershell
$rb = 'C:\' + [char]36 + 'Recycle.Bin\<SID>'
$s = 0; Get-ChildItem -LiteralPath $rb -Recurse -Force -File | ForEach-Object { $s += $_.Length }
'{0:N0} Mo en corbeille' -f ($s/1MB)
Get-ChildItem -LiteralPath $rb -Force -File |
  Where-Object { $_.Name -like ('*' + [char]36 + 'I*') } |
  Sort-Object CreationTime -Descending | Select-Object -First 8 Name, CreationTime
```

Le contenu est renomme `$R<code>.<ext>` ; le jumeau `$I<code>.<ext>` porte les metadonnees (chemin
d'origine dans son en-tete, plus l'horodatage de mise en corbeille, qui date l'evenement). **Une
recherche par le nom d'origine ne trouve rien** — la recherche par nom conclut « deja supprime » a tort
alors que les octets sont occupes. Pour les liberer il faut vider la corbeille : action de
l'utilisateur, a proposer et jamais a faire sans demande.

Pieges de shell : `$` doit etre protege cote bash (`[char]36` en PowerShell, ou passer par un `.ps1`
appele en `-File`) ; et une apostrophe francaise dans une chaine PowerShell mono-quote casse le parseur
(ecrire `du venv video`, pas `d'un venv video`).

## 5. Ecarter les consommateurs concurrents avant d'accuser les hardlinks

Un gain inferieur a la somme peut aussi venir d'une ecriture parallele pendant la passe. Chacun se
mesure :

- **Corbeille** (§4) — c'est le candidat le plus frequent, et il est invisible a une recherche par nom.
- **VHDX Docker / WSL** qui grandissent :
  `Get-ChildItem -Path <AppData\Local> -Filter '*.vhdx' -Recurse -File | Sort Length -Desc | Select -First 5`
  avec leur `LastWriteTime` (un vhdx modifie pendant la passe explique l'ecart).
- **Fichiers > 200 Mo ecrits depuis N minutes** dans les zones de travail :
  `Get-ChildItem -Recurse -File | Where-Object { $_.Length -gt 200MB -and $_.LastWriteTime -gt (Get-Date).AddMinutes(-N) }`
  (a borner aux zones plausibles : `data/`, `Downloads/`, `Videos/`, `.cache/`).
- **Processus vivants** : `Get-CimInstance Win32_Process` filtre sur `python|node|ffmpeg|comfy`. Une tache
de fond qui ecrit pendant la passe l'emporte sur le calcul.

## 6. Prouver un doublon avant d'annoncer le gain

Un contenu identique ne prouve pas deux allocations. TROIS verifications, dans cet ordre :

```bash
stat -c '%i %h' <copie1> <copie2>              # inodes differents ET h=1 = 2 allocations reelles
fsutil hardlink list "$(cygpath -w <copie1>)"   # ne doit rendre QUE le fichier lui-meme
md5sum <copie1> <copie2>                        # identite de contenu, si elle conditionne la decision
```

`cygpath -w` est requis : `fsutil` est un binaire natif et ne comprend pas un chemin `/c/...`.

- Mesure : deux blobs de 19,02 Go, md5 identiques, inodes distincts, `fsutil hardlink list` rendant une
  seule ligne chacun -> 2 allocations reelles, la suppression de l'une rend bien 19,02 Go. Le meme controle
  sur un cache outillage avait donne l'inverse (3 liens vivants = 0 Go rendu).
- **Lancer ce md5 en tache de fond** (`background=true` + `notify=true`) : ~38 Go lus sur un disque
  d'audit prennent une vingtaine de minutes, et pendant ce temps le disque est sature — les autres mesures
  ralentissent ou depassent leur timeout. Ne pas enchainer : relancer apres, ou mesurer d'abord.
- Verifier que chaque fichier rend bien une ligne avec un hash de 32 caracteres hexa : un fichier absent ou
  un chemin mal converti rend une ligne d'erreur, pas un hash.

Un ecart inexplique apres ces cinq sondes ne se presente pas comme un resultat : il se declare dans le
section anomalies, avec les chiffres bruts.
