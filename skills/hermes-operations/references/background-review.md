<!-- Extrait de hermes-operations/SKILL.md, lignes 43-80 (compression A.3 du 2026-10-06) — contenu verbatim. -->

### La revue d'arrière-plan écrit dans tes fichiers pendant ta session

Un fichier de skill, `skills/.usage.json` ou `memories/MEMORY.md` qui change **sans action de ta part**
vient presque toujours de la revue d'arrière-plan de la session en cours (fork du curateur), pas d'une
seconde instance. Avant de conclure à un agent concurrent, inventorier les **piles réelles** :
`Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|hermes' }` trié par
`CreationDate` — les PID vont par chaînes (lanceur `hermes.exe`/venv + python `.hermes-runtime` +
`tools/python-*`), donc un parc sain = **1 pile gateway + 1 pile chat**. Une écriture sans PID
supplémentaire est un fork interne.

Attribuer l'écriture à son auteur, dans cet ordre :

- `skills/.curator_ledger.jsonl` : chaque entrée porte `actor` (`"curator"` = revue d'arrière-plan,
  `"agent"` = tes propres `skill_manage`), `skill`, `before`/`after` en `sha256` et surtout
  `evidence.session_id` — c'est lui qui désigne le writer.
- `.curator_backups/blobs/<sha256>` : les états avant/après en clair, avec leur mtime (le `sha256` de
  l'entrée de ledger s'y retrouve, ce qui donne la chronologie exacte).
- `pending/memory/*.json` : `origin: "background_review"` = **propositions**, pas écritures — comparer
  au contenu réel du fichier avant de dire qu'une entrée a été appliquée.
- `logs/agent.log` : grepper l'id de session entre crochets (`[20260927_…]`). Les refus
  `Refusing background curator patch for skill <X>: … not curator-managed` prouvent à la fois le fork
  interne et sa borne (il ne touche jamais les skills bundled ni user-owned).

**Ne jamais committer un fichier dont le writer est encore actif** : `stat -c '%y %n' <fichiers>` +
`wc -l`, pause ~30 s, re-mesure — identiques = stable, on peut committer ; sinon on fige un état à
moitié écrit et le diff audité n'est plus celui qui part. Et **un diff qui porte des lignes qu'on n'a
pas écrites se NOMME** (message de commit, rapport) au lieu d'être absorbé en silence.

**Elle repasse toutes les ~15 min : ne pas courir après chaque passe.** Mesure : 4 passes en 1 h 04,
chacune pendant que la session travaillait, la dérive repassant de 1 à 10 entrées sans que la session
ait touché à une skill — et une passe réécrit des fichiers que la session vient de committer. Un arbre
propre est donc un **état de quelques minutes, pas un objectif** : geler à chaque passe revient à un
commit toutes les ~15 min, dont l'historique ne dit plus rien. Pratique retenue par l'opérateur :
**gel groupé** — laisser les passes s'accumuler, figer l'ENSEMBLE des entrées à un moment choisi (fin de
session, fin d'heure, avant un push important) avec la preuve de stabilité de 3 min, pousser, et
accepter la re-dérive. Une passe survenue pendant le gel se ramasse au gel suivant ; la voir réapparaître
n'est pas l'échec du commit précédent.

