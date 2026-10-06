<!-- Extrait de hermes-operations/SKILL.md, lignes 287-376 (compression A.3 du 2026-10-06) — contenu verbatim. -->

### Snapshot git de la config (`docs/`)

Le depot est **unique** : runtime a la racine de `%LOCALAPPDATA%\hermes`, documentation sous `docs/`.

**Le depot EST le home** (branche `main`, poussee sur son distant). Les skills vivent dans son arbre
(`skills/**`) : corriger un skill, le committer et le pousser se fait depuis cette racine — pas depuis
un autre depot, et **sans en chercher un ailleurs** : un balayage `.git` sur le disque remonte des
checkouts sans rapport (un clone `wazuh` sous le `Code\GitHub` de l'utilisateur) et fait perdre le
tour. **Le terminal s'ouvre dans `C:\WINDOWS\system32`** : faire `cd "$LOCALAPPDATA/hermes"` puis
`pwd` + `git status --short` AVANT tout `git` ou chemin relatif ; les chemins que l'utilisateur donne
(`skills/…`, `data/…`) sont relatifs a cette racine.

Apres un commit, rapporter le hash complet (`git rev-parse HEAD`) et la ligne de push
(`<ancien>..<nouveau>  main -> main`), et montrer le `git diff` des fichiers vises AVANT d'ajouter :
l'operateur veut voir ce qui part, pas seulement le fait que c'est parti. Ne jamais `git add -A`
depuis le home (l'arbre contient des dizaines de fichiers vivants, cf. `.gitignore` et l'audit).

**Un chantier de maintenance se committe en étapes logiques, chacune avec le préfixe de sa nature**
(`fix:` une correction de contenu ou de config, `docs:` la documentation et les fiches du wiki,
`chore:` le nettoyage de fichiers et de logs). Un commit fourre-tout rend le retour arrière
impossible quand une seule des modifications se révèle fausse. Committer **et pousser** à chaque
étape, puis donner le hash complet : l'opérateur suit l'avancement commit par commit.

**Un fichier introuvable se DIT ; il ne se cherche pas sur tout le disque.** Verifier le chemin exact
donne et, s'il n'y est pas, le rapporter tel quel plutot que de lancer une recherche large — elle
ramene des homonymes d'autres projets et fait conclure a tort a un livrable manquant ou deplace.
L'ancien depot externe a ete fusionne puis renomme en `*.archive` : ne plus y chercher la doc ni le
snapshot — tout est sous `docs/`.

La copie versionnée du config live est `docs\snapshot\config.yaml` — il n'y a
**pas** de `hermes_install\config.yaml` à la racine du dépôt. « Resynchroniser
docs/config.yaml » désigne donc ce fichier-là : le dire avant d'agir, plutôt que de
supposer que la racine contient la copie.

Procédure : `cp` live → snapshot, confirmer les deux `md5sum` identiques, `diff` vide, puis commit.
**S'attendre à un drift plus large que la dernière modification** : la copie versionnée retarde de
toute la migration de config, donc lire le `diff` en entier et rapporter chaque hunk au lieu de
supposer que seule l'édition du jour manque.

`config.yaml` ne contient aucun secret en clair (`api_key: ''` partout, les clés vivent dans
`.env`) : la copie brute est sûre. Mais le `.gitignore` déclare la politique « REDACTED uniquement »
et `snapshot/config.yaml.redacted` n'a **aucun régénérateur** (le scanner de secrets est un scanner
seul, sans mode export) — le rafraîchir signifierait inventer un format : le laisser tel quel et le
signaler.

**Une liste de décisions numérotée (D1…Dn) fournie par l'opérateur s'applique à la lettre, item par
item, et s'arrête à ses propres gates.** Un item conditionnel qui demande de « montrer le diff AVANT
écriture » se traite en **deux temps** : livrer le diff proposé dans le rapport, ne rien écrire, et
attendre le GO — écrire puis montrer le diff dans le compte rendu inverse la consigne, même quand
l'écriture est techniquement correcte. Un item marqué OPTIONNEL n'exempte pas de cette preuve préalable.

- **Une consigne littérale qui n'atteint pas son but se SIGNALE, elle ne se corrige pas en silence.**
  Un motif `.gitignore` sans joker (`.bak_`) ne matche que le fichier nommé exactement `.bak_` : le
  prouver avec `git check-ignore --no-index -v <chemin réel>` sur les vrais fichiers ET une sonde
  (`probe.bak_2026`), puis proposer le motif qui couvre (`*.bak_*`) et attendre le GO. Un fichier déjà
  SUIVI n'est de toute façon jamais concerné par `.gitignore` : `git rm --cached` le fait réapparaître
  en non suivi si aucun motif ne le couvre — c'est le seul cas encore attrapable par un `git add -A`,
  donc celui à nommer dans le rapport.
- **Un item hors dépôt (sous `data/`, chemin ignoré) ou sans fichier se traite et se rapporte, mais ne
  se committe pas** : l'annoncer par item (« hors dépôt, non committable ») sans inventer de chemin de
  remplacement. Un item dont la cible a disparu change de NATURE, pas seulement de valeur —
  « réparer un fichier tronqué » devient « réassembler un livrable absent » — et se réécrit ainsi.
- **Un item de code se prouve par ses DEUX branches, exécutées sans réseau** (monkeypatch de la
  primitive externe) : branche nominale ET branche dégradée, en comparant clé par clé les valeurs
  exactes exigées par la décision, plus le code de sortie CLI dans les deux modes (`--json` et texte).
- **Les gates de l'opérateur s'exécutent dans l'ordre annoncé** : `git diff --cached` complet, puis le
  scan de secrets SUR LE DIFF indexé, motif par motif (`for m in sk- gh_ AKIA AIza xox hf_ nvapi- JWT;
  do git diff --cached | grep -cE "$m"; done`), puis le contrôle nommé (ACLs, config). **Un gate ROUGE
  arrête le commit** : nommer l'item fautif et sa commande de correction, laisser l'index prêt, et
  proposer des options numérotées (« GO tel quel » / « GO correction d'abord » / « GO motif corrigé »)
  plutôt que de committer presque ou de pousser pour finir.
- **Un fichier réécrit par un outil se mesure avant d'être accusé de reformatage** : un patch qui
  affiche tout le fichier en +/- peut n'avoir changé que 2 lignes. Trancher par `git diff --numstat`
  (2/0 attendu), `git diff --stat` et `grep -c $'\r' <fichier>` (0 CRLF attendu) — `.gitattributes`
  (`* text=auto eol=lf`) normalise à l'index, donc l'avertissement CRLF de git n'est pas un écart.
- **Corriger une ligne dans un bloc : ne matcher QUE cette ligne.** Un `old_string` qui inclut les
  lignes voisines les **supprime** (le remplacement ne restitue que ce qu'on écrit, pas le contexte
  au-delà) : mesuré sur un `.gitignore` à blocs, un simple passage de `hermes-agent/` à `/hermes-agent/`
  a effacé `data/`, puis `bin/` au correctif suivant. Après toute édition de ce genre, prouver la
  minimalité par `git diff --numstat <fichier>` (attendu `1 1`) **et** relire le bloc entier — sur un
  `.gitignore`, une ligne d'exclusion perdue (`data/`, `logs/`, `.env*`) ne salit pas le diff : elle rend
  le motif inopérant, et le `git add -A` suivant indexe ce qu'elle protégeait.
- **Le go push est une INSTRUCTION écrite, pas une humeur à deviner** : tant qu'aucune étape ne porte
  `git push`, on committe seulement et l'état de l'index se rapporte tel quel (prêt, rien perdu) entre
  deux tours. Quand la mission liste ELLE-MÊME le push parmi ses étapes (« `git push origin main` »,
  avec l'attendu `<ancien>..<nouveau> main -> main »), c'est le go : l'exécuter et **nommer la lecture**
  dans le rapport — s'arrêter pour redemander coûte un tour et laisse la mission à moitié livrée. Les
  deux formes coexistent dans un même message : la règle générale tient tant qu'aucune étape ne nomme
  le push ; dès qu'une étape le nomme, c'est elle qui tranche.

