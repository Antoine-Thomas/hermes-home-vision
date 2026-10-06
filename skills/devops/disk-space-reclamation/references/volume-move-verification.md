# Deplacer des donnees vers un autre volume (copie verifiee)

Quand un audit disque conclut « DEPLACABLE VERS <volume> » : la copie est longue, traverse deux supports,
et la suppression de la source ne se valide qu'apres une verification qui ne depend pas du bon vouloir de
l'outil de copie. Recette complete, dans l'ordre.

## 1. Chiffrer la duree AVANT d'annoncer (sonde de debit)

Une estimation au feeling est fausse d'un facteur 5 selon le support. Copier un sous-arbre representatif
vers un dossier temporaire du volume CIBLE, chronometrer, supprimer la sonde :

```powershell
$t0 = Get-Date
robocopy.exe $sousArbre "D:\_probe" /E /R:1 /W:2 /NFL /NDL /NJH /NJS /NP | Out-Null
$t1 = Get-Date
# debit = octets copies / duree ; fichiers/s = nb fichiers copies / duree
```

En deduire DEUX bornes pour le lot complet et retenir la plus grande :

- borne debit    = octetsTotaux / (octets de la sonde par seconde)
- borne fichiers = nbFichiersTotal / (fichiers de la sonde par seconde)

Une sonde sur un sous-arbre a PETITS fichiers surestime le temps du lot complet : le lot reel a une taille
moyenne par fichier plus grande, donc moins de surcout par fichier. Annoncer la fourchette, pas un chiffre
unique, et rappeler la borne basse. Mesure de reference : 23 Mo/s et 458 fichiers/s sur un HDD USB 3
(dossier node_modules), bornes 168 min / 32 min, 62 min reellement obtenues sur 231,78 Go / 887 695 fichiers.

La sonde quantifie le support CIBLE (USB, reseau, mecanique), pas la machine : sur un volume cible lent,
c'est l'ecriture qui plafonne, jamais la lecture de la source NVMe.

## 2. Copier sans /MOVE, en arriere-plan

```bash
robocopy "C:\c" "D:\backup_x" /E /R:2 /W:5 /NP /TEE /LOG:D:\backup_x_robocopy.log
```

- Jamais `/MOVE` vers un support amovible : robocopy efface chaque source au fur et a mesure, une coupure
du support detruit la source et laisse une copie partielle. Copie d'abord, suppression ensuite, sur deux
validations explicites distinctes.
- Lancer en arriere-plan avec notification des que la duree estimee depasse ~10 min.
- Avant de rendre la main : verifier que la destination GROSSIT et que la queue du log avance. Un processus
  lance mais bloque se lit sinon comme un succes.
- Log : 995 000 lignes et 62 Mo pour 887 695 fichiers avec les noms de fichiers. Le garder dans un
  emplacement durable et HORS de l'arborescence deplacee.

## 3. Verifier par ensemble, pas par comptage

Ecrire deux listes avec la MEME enumeration .NET, cle `chemin relatif + taille`, puis les comparer :

```powershell
[System.IO.File]::ReadAllLines($srcList)   # "rel<TAB>length" par fichier
Compare-Object -ReferenceObject $sl -DifferenceObject $dl   # SideIndicator <= / =>
```

- Attendu : 0 uniquement en source, 0 uniquement en destination. C'est la seule preuve de completude qui
  couvre l'arbre ENTIER, la cle incluant la taille (un fichier tronque remonte comme ecart de taille).
- Comparer des comptages ne prouve rien : deux erreurs symetriques s'annulent, et un comptage different
  peut signifier un perimetre different (un dossier parent contient d'autres charges que le dossier
  mesure a l'audit) — chercher la cause avant de conclure a une perte.
- Croiser avec le log : `Select-String -LiteralPath $log -Pattern "ERREUR|ERROR|ECHEC" -SimpleMatch`
  (0 attendu) et les colonnes Ignore / Extras du resume, qui doivent etre a 0.
- Script pret a l'emploi : `scripts/verify-copy-tree.ps1`.

## 4. Echantillonner les hachages, en borne

- SHA256 COMPLET uniquement sur des fichiers <=100 Mo : un par sous-arbre distinct, tirer au hasard avec
  une graine fixe (`Get-Random -SetSeed`) pour que le tirage soit reproductible.
- Grouper APRES avoir retire le prefixe commun de la cible deplacee : une arborescence nestee sous un seul
  root (`C:\c\Users\<user>\Desktop\<backup>\`) fait sinon retomber tous les fichiers dans un seul groupe
  et l'echantillon ne couvre rien.
- Fichiers de plusieurs Go : controle PARTIEL (premiers + derniers 32 Mo par `Seek` sur un `FileStream`),
  annonce comme partiel. Presenter un hash partiel comme un SHA256 est une fausse preuve.
- Le hachage complet de quelques fichiers de 5-7 Go lus depuis un disque externe lent depasse le mur
  d'appel de l'outil (~420 s constate) : c'est ce qui rend le controle partiel necessaire, pas un confort.

## 5. Discipline de temps et de processus

- Mur d'appel constate en avant-plan : ~420 s. Au-dela, l'appel rend la main sans la sortie ; un
  `timeout` explicite plus grand est promu en processus de fond suivi.
- Apres un appel expire, chercher l'orphelin avant de relancer un autre travail lourd sur le meme disque :
  `Get-CimInstance Win32_Process -Filter "Name='powershell.exe'"` (CreationDate + CPU eleve = le job
  encore vivant), puis `Stop-Process -Id <pid> -Force`.
- Sous git-bash, `taskkill //PID <pid>` est refuse (« Argument ou option non valide ») : passer par
  `Stop-Process`. Eviter aussi `&` et `2>&1` dans les commandes envoyees a l'outil terminal : il les lit
  comme une mise en arriere-plan et refuse la commande entiere.

## 6. Supprimer la source (etape separee, sur validation)

Seulement apres un rapport de verification valide et un GO explicite. Ecrire un manifeste avant toute
deletion, remesurer l'espace libre **en octets** des deux volumes, et recontroler la satisfaction des
fichiers recuperes ailleurs (ceux qui n'existaient que dans la copie source, cf. « cibles mixtes » dans
`references/space-accounting.md`) AVANT d'effacer quoi que ce soit.
