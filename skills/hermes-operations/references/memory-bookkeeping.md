<!-- Extrait de hermes-operations/SKILL.md, lignes 1098-1108 (compression A.3 du 2026-10-06) — contenu verbatim. -->

## Memory & runbook bookkeeping

- `memories/MEMORY.md` has a hard ~2200 char budget (injected every turn). When near limit, compress existing entries in place before appending — shorten verbose lines, merge related bullets, keep `§` separators. Target ≤2170 to leave headroom.
- **Verify memory usage in CHARACTERS, never with `wc -c`.** `wc -c` counts bytes and accented characters cost 2 bytes in UTF-8, so it overstates usage (2071 "chars" measured for 2036 real). The budget is characters. Authoritative reader: `scripts/check_memory.ps1`, which uses `(Get-Content -Raw).Length`; Python equivalent `len(open(f, encoding='utf-8').read())`.
- **Les deux lecteurs ci-dessus divergent sur un fichier en CRLF** : `Get-Content -Raw` conserve les fins de ligne et compte chaque `\r\n` pour 2 caractères, une lecture Python en mode texte universel les ramène à 1. L'écart est exactement le nombre de fins de ligne (22 chars sur un fichier de 22 lignes) et **n'est pas un écart de contenu** : citer la valeur du script, nommer le lecteur, et ne pas partir chasser un drift de contenu inexistant. `MEMORY.md` est en LF (les deux lecteurs concordent), `USER.md` peut être en CRLF — vérifier avant de comparer.
- `check_memory.ps1` alert thresholds (MEMORY 2100 / USER 1300) differ from the `config.yaml` limits (2200 / 1375). Name the reader you are quoting — otherwise "under the threshold" and "above the target" coexist and nobody can tell which applies.
- `check_memory.ps1` is **read-only**: it writes no file and creates no `.bak`. Do not attribute sanitising backups to it.
- `memories/USER.md` (~1000 chars) holds stable preferences; `MEMORY.md` holds environment facts and standing ops rules.
- `recovery_runbook.md` is the durable ops reference — record ESTOP semantics, channel/bot mapping, and verification commands there with tags `[telegram pause resume bots surveillance assistance]` so future sessions can `search_files` it.
- Tag new ops facts with all relevant keywords in the same line so keyword search finds them without scanning full history.

