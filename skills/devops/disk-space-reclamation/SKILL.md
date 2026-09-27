---
name: disk-space-reclamation
description: "Use when auditing disk space or reclaiming GB."
version: 1.0.0
author: hermes-curator
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [disk, cleanup, audit, deletion, storage, cache, windows]
    category: devops
---

# Disk Space Reclamation

## When to use

- L'utilisateur demande un audit disque, une liste de cibles "supprimables", ou la recuperation de N Go.
- Toute tache ou l'on propose de SUPPRIMER des donnees sur le disque de l'utilisateur : caches, sauvegardes,
snapshots, venvs retires, archives d'installation.

## Regle 0 — deux phases, jamais une seule

Phase A = lecture seule : mesures + verdict + rapport. Phase B = suppression, seulement apres validation
EXPLICITE de l'utilisateur, dans l'ordre de risque.

- Ne jamais supprimer dans la meme reponse que la mesure. Un audit qui se termine sans validation se
termine par "aucune suppression effectuee" — et c'est un resultat valide.
- Respecter les zones exclues nommees par l'utilisateur (pending/, memories/, une quarantaine deja
comptee ailleurs) et le redire dans le rapport, sinon l'utilisateur ne peut pas savoir si l'exclusion a
ete honoree.
- Ne jamais supprimer un artefact de rollback (sauvegarde de profil, snapshot pre-update, venv retire)
dans la meme phase que des caches : ce sont deux risques differents, ils se valident separement.

## Procedure

1. **Inventaire lecture seule.** Mesurer chaque cible : taille exacte, mtime, nature reelle (fichier /
dossier). Verifier l'existence AVANT de mesurer : un chemin d'audit peut ne pas exister, ou designer
autre chose que ce que son libelle annonce.
2. **Statuer par categorie, pas par nom de dossier.** Un dossier nomme `cache`, `backup` ou `tmp` n'est
ni jetable ni regenerable du seul fait de son nom. Grille de decision :
`references/target-verdicts.md`.
3. **Tableau de verdicts**, une ligne par cible : `chemin | taille mesuree | mtime | verdict`.
Verdicts : SUR / A VERIFIER / A GARDER. Annoncer la convention de taille utilisee
(taille logique = somme des octets des fichiers, 1 Go = 10^9).
4. **Liste "a supprimer" triee par taille decroissante**, puis total recuperable. Donner aussi le total
laisse en "a verifier" : c'est ce qui cadre la phase B.
5. **Signaler les ecarts.** Toute difference entre les chiffres/chemins annonces par l'audit d'origine et
la mesure est ecrite dans le rapport, jamais corrigee en silence : taille qui double, chemin qui n'est pas
le bon, "fichier" qui est un dossier, nom reel different. Mettre ces ecarts dans une section "anomalies"
separee, numerotee.
6. **Attendre la validation**, puis supprimer dans l'ordre decroissant de taille et remesurer
(`df -h`) pour rendre l'ecart entre annonce et gain reel.

## Mesurer une arborescence volumineuse

`du -sb` / `du -sm` (busybox/MSYS) est trop lent des que les cibles se comptent en Go : une passe sur 18
cibles (dont une de 17,6 Go et une de 68 Go) n'a pas rendu la main en 420 s. Ne pas relancer avec un
timeout plus grand — changer de methode : une enumeration .NET boucle sur les fichiers au lieu de
parcourir les inodes cote shell, et rend la meme mesure en minutes.

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:/Users/<user>/.../scripts/measure-targets.ps1 -List C:/chemin/cibles.txt
```

Le script rend un TSV `kind | bytes | mtime | path` trie par taille decroissante (kind = FILE | DIR |
MISSING), ce qui donne directement le tableau du rapport. Garder `du -sh` pour un petit dossier et
`df -h` pour l'espace libre : eux restent rapides.

- **Mtime d'un dossier** = derniere modification de son repertoire (ajout/retrait d'entree), pas le max
des enfants. C'est un signal d'ACTIVITE, a confirmer en regardant le mtime des sous-dossiers avant d'en
conclure qu'une cible est morte.
- **Toujours sortir une ligne MISSING / retypee** pour une cible introuvable ou d'une autre nature, au
lieu de sauter la ligne : une cible absente du rapport passe pour inexistante.
- Ne pas lancer une lecture de contenu sur un fichier de nature inconnue : `read_file` sur un `.exe`
deverse des pages d'octets illisibles et pollue la session. Etablir d'abord le type (extension, `file`,
`stat -c %s`) et ne garder `read_file` que pour un fichier texte.
- "Les 5 premieres lignes" ne s'appliquent qu'a un fichier TEXTE. Quand aucune cible n'est un fichier
texte (archives ZIP/7z, dossiers), le dire explicitement plutot que d'omettre la demande.

## Ce qui rend une cible NON sure

Ces six controles, passes sur chaque cible "regenerable", ont chacun retourne une cible en "a verifier"
sur une meme session :

1. **Elle est encore ecrite.** Un mtime du jour sur le dossier ou sur un sous-dossier = magasin ACTIF,
pas un residu (un magasin de blobs de sauvegarde du curateur, 1556 fichiers, ecrit le jour meme).
Chercher la date avant de declarer "ancien".
2. **Un composant vivant la lit.** Chercher le nom du modele / le chemin du cache dans les scripts
actifs avant de conclure "regenerable" :
`grep -rn -i -E "<nom-modele>|SentenceTransformer|<chemin-cache>" <dossier-des-scripts-*.py>` et lire le
manifeste d'index. Un cache qui contient un modele charge par un service en marche n'est pas un cache,
c'est une DEPENDANCE (le cache de modeles portait le modele d'embedding du RAG local, sans lequel
l'index ne se recharge pas).
3. **Une doctrine de retention la protege.** Lire les docs du profil avant de toucher un artefact de
rollback : un venv retire peut avoir une date de suppression prevue (`grep -n -i -E "retention|retired"
docs/*.md`). Supprimer avant la date contredit une decision documentee.
4. **Son contenu n'est pas versionne.** `git check-ignore -v <cible>` puis `git ls-files <cible> | wc -l`.
Un dossier ignore ET non suivi (donnees metier, `.env`) rend une sauvegarde "redundante" la SEULE copie
existante hors du profil.
5. **Une sauvegarde n'est "remplacee" que si la plus recente est complete.** Verifier la presence des
sous-arbres attendus (memories/, skills/, data/, state.db) : une sauvegarde voisine plus recente peut
etre VIDE (0 Mo) — un echec de sauvegarde, pas un remplacement. Un dossier partiel contient une copie de
donnees gitignores : ce n'est pas un doublon.
6. **Le cout de regeneration n'est pas le prix du telechargement.** Un artefact produit par un run long
non reproductible en une commande (export/conversion de poids, index) se garde meme s'il est
techniquement regenerable.

Et un controle de propriete : avant de proposer la suppression du dossier de travail d'un skill, verifier
si ce skill est actif dans `config.yaml` (liste `skills.disabled`) — s'il est actif, la cible n'est pas
sure, quelle que soit sa taille.

## Suppression (phase B)

- Ordre : plus grosse cible d'abord. Le gain se mesure tot et une erreur coute moins cher sur un cache que
sur une sauvegarde.
- Supprimer les enfants d'une cible, pas le parent d'un cache outillage : `uv cache clean archive-v0`
nettoie une famille de cache, alors que supprimer `uv/cache/` entier emporte `git-v0`, `sdists-*`,
`simple-*` et `wheels-*` (mesure : 16,7 Go dans `archive-v0` sur 17,1 Go du parent).
- Apres chaque lot : `df -h /c` et comparer au total annonce. Un gain different de la somme mesuree est un
ecart a signaler, pas a arrondir.

## Rapport — pieges

- Ecrire la taille MESUREE, pas la taille annoncee : sur une meme session les chiffres d'audit differaient
des mesures d'un facteur 2,5 a 6. Un tableau qui recopie l'inventaire d'origine propage l'erreur.
- Une cible vide (0 Mo) et une sauvegarde partielle sont deux ANOMALIES a signaler, pas a taire.
- Un artefact durable range dans un dossier temporaire elague automatiquement (cache/scratch) est un
risque de perte silencieuse, pas un fichier a supprimer : le dire et proposer l'emplacement durable.
- Ne pas conclure "redundant" depuis un nom de dossier horodate : le dossier le plus recent peut etre le
plus vide.

## Fichiers

- `scripts/measure-targets.ps1` — mesure taille + mtime d'une liste de cibles (enumeration .NET, TSV trie).
- `references/target-verdicts.md` — grille par categorie (cache d'outillage, cache de modeles,
  node_modules, archive d'installation, sauvegarde, snapshot d'etat, venv retire, runtime navigateur,
  dossier de travail de skill) : quoi verifier, verdict par defaut.
