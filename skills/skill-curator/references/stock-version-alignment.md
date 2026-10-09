# Aligner le frontmatter d'un skill custom sur le stock bundled

Classe de tache : un skill bundled (`hermes skills list` -> Source `builtin`) a ete personnalise
(typiquement decoupe en `references/` par un split curator — ces modifications survivent a
`hermes update`) et on veut remettre UNIQUEMENT la ligne `version:` du frontmatter au niveau du stock
upstream, sans toucher au contenu.

## Ou vit le stock

Apres une install par git, les fichiers STOCK (bundled upstream) sont dans le depot d'installation :
`<HERMES_HOME>/hermes-agent/skills/<categorie>/<nom>/SKILL.md`
(ex. `.../hermes-agent/skills/research/llm-wiki/SKILL.md`).
Lecture seule : ne JAMAIS modifier la. La copie active a editer est `skills/<categorie>/<nom>/SKILL.md`
a la racine du profil.

## Obtenir la version stock (fiable)

Lire directement la ligne `version:` du fichier stock ci-dessus (`read_file`, ~ligne 4). C'est la
source d'autorite pour un skill bundled.

`hermes skills diff <nom>` est le chemin « officiel », mais deux comportements a connaitre :
- Le diff ne montre des hunks qu'a partir de la PREMIERE ligne changee. Consequence : si AUCUNE ligne
  `version:` n'apparait dans la sortie, la version locale EST identique a la stock (frontmatter =
  contexte non affiche, pas une perte d'info) => rien a aligner. Le verifier quand meme sur disque.
- Quand les versions different, le hunk du frontmatter montre la paire `-version: <STOCK>` /
  `+version: <LOCAL>`. Filtre sur : `hermes skills diff <nom> 2>&1 | grep -E "^[-+]version:"`.

## Piege Windows : `hermes skills diff` plante a l'AFFICHAGE

Sur ce terminal Windows, `hermes skills diff` peut lever `OSError: [Errno 22] Invalid argument` dans
rich `legacy_windows_render` / `_win32_console.write_text` en VIDANT le buffer — apres avoir deja
ecrit le diff. Le diff est donc complet sur stdout malgre la trace. Mais un `| head` / `| tail` masque
le vrai code de sortie (le pipe renvoie celui du dernier maillon) : ne pas conclure « commande
cassee ». Soit lire la version stock directement sur disque (prefere), soit filtrer par grep.

## `hermes skills inspect`

`hermes skills inspect <nom>` peut renvoyer PLUSIEURS resultats (registres skills.sh / clawhub).
Utiliser l'identifiant complet pour l'amont nousresearch : `skills-sh/nousresearch/hermes-agent/<nom>`.
La version du miroir registre correspond generalement au stock sur disque, mais pour un skill bundled
c'est le FICHIER sur disque qui tranche.

## Regles d'edition (aligner la version)

- Ne toucher QUE la ligne `version:` ; rien d'autre (ni contenu, ni autres champs du frontmatter, ni refs).
- Utiliser `patch` avec un `old_string` unique sur cette ligne (ex. `version: 2.3.0`), pas d'edition globale.
- Si les versions sont identiques : NE RIEN FAIRE et le rapporter — ne pas inventer une edition pour
  « coller » au plan annonce. Un plan qui presume N fichiers a aligner peut en avoir moins a la mesure.
- Un skill customise montre un diff structurel enorme vs stock (frontmatter + corps remplaces par un
  routeur) : c'est attendu. La preuve d'un alignement propre est `git diff --numstat` = `1 1` et
  `git diff` = 1 seule ligne changee par fichier touche.
- NE JAMAIS `hermes skills reset <nom> --restore` pour « reparer » une version : cela ecrase la
  personnalisation (le split). Aligner la ligne a la main.

## Fins de ligne (CRLF) — verrouiller avant/apres l'edition

Le depot a `.gitattributes` `* text=auto eol=lf` : la copie active d'un skill est CRLF en worktree, LF
dans l'index. `git ls-files --eol -- <fichier>` rend donc `i/lf  w/crlf  attr/text=auto eol=lf` —
c'est l'INDEX (`i/lf`) qui compte pour le commit, le `w/crlf` est du bruit normal.
Le `patch` de Hermes PRESERVE le CRLF (mesure : 2587 octets, CRLF 47/47, seule la ligne 4 change, pas
de BOM). Avant d'editer le fichier REEL, PROUVER ce comportement sur une copie byte-identique en
scratch : `cp <fichier> cache/scratch/<nom>`, patcher la copie, puis verifier taille inchangee +
`data.count(b'\r\n') == data.count(b'\n')` + une SEULE ligne differente. Si l'echantillon fabriquait
un LF isole, editer le vrai fichier par script OCTETS (`data.replace(old.encode(), new.encode())` avec
comptage d'occurrence = 1), pas par `patch`.

## Verification avant commit (depot bruyant)

- `git diff --numstat -- <fichier>` = `1 1` et `git diff` = 1 seule ligne : preuve que seul `version:`
  a bouge. Un skill deja decoupe ne doit PAS remontrer le decoupage `references/` (le split est committe).
- Scan secrets masque PAR FICHIER : le script du depot `docs/scripts/scan_secrets_history.py` scanne
  TOUT l'historique ; pour un seul fichier, importer son module (`importlib.util.spec_from_file_location`)
  et appliquer ses `COMPILED` + `PLACEHOLDER` aux octets du fichier — sortie = nb occ. + empreintes
  sha256[:16], jamais la valeur. Attendu : 0 reel.
- Commit ISOLE : `git add <fichier>` NOMME (jamais `-A`, jamais `git add skills/`), puis garde
  `git diff --cached --name-only | wc -l` doit valoir 1 ; si > 1, `git reset HEAD -- <extras>` et
  reverifier avant de committer. Ce depot porte en permanence du bruit runtime (`skills/.usage.json`,
  `skills/.curator_state`, `skills/.curator_suppressed`, `skills/.hub/index-cache/*`) et les fichiers
  frais d'une autre session : aucun ne doit entrer.
- Message de commit en LF PUR : ecrire les octets explicitement et verifier `CR == 0` avant
  `git commit -F <msgfile>`.
