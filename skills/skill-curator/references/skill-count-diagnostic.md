# Diagnostic ecart comptage skills (84 vs 143)

Cause frequente: dossiers vides `skills/_archive/` listes comme categorie alors que `_archive` n est jamais exclu du prompt (seul `.archive/` l est). `hermes curator archive` deplace vers `.archive/` + ecrit `.curator_suppressed` pour bloquer le re-seed bundled.

## Procedure diagnostic
```bash
# 1. Actifs reels (hors archives)
find "$LOCALAPPDATA/hermes/skills" -name "SKILL.md" -not -path "*/_archive/*" -not -path "*/.archive/*" | wc -l
# 2. Fantomes _archive
find "$LOCALAPPDATA/hermes/skills/_archive" -name "SKILL.md" | wc -l
find "$LOCALAPPDATA/hermes/skills/_archive" -type f | wc -l  # 0 = dossiers vides = categorie fantome
# 3. Archive reelle
find "$LOCALAPPDATA/hermes/skills/.archive" -name "SKILL.md" | wc -l
# 4. Snapshot bandeau
ls -la "$LOCALAPPDATA/hermes/.skills_prompt_snapshot.json"
python -c "import json,collections; d=json.load(open(r'C:\Users\searc\AppData\Local\hermes\.skills_prompt_snapshot.json',encoding='utf-8')); s=d.get('skills',d); print(len(s), collections.Counter(x.get('category','') for x in s))"
```

## Correction
- Si `_archive` ne contient aucun `SKILL.md` (uniquement dossiers vides): `rm -rf "$LOCALAPPDATA/hermes/skills/_archive"` — pas de migration vers `.archive` necessaire.
- Si `_archive` contient des `SKILL.md`: `hermes curator archive <nom>` par skill, ou `mv "$LOCALAPPDATA/hermes/skills/_archive"/* "$LOCALAPPDATA/hermes/skills/.archive/"` puis supprimer `_archive`.
- Snapshot stale (count != actifs ou categorie `_archive` presente): `rm "$LOCALAPPDATA/hermes/.skills_prompt_snapshot.json"` puis `hermes gateway restart` (+ `hermes -p watch gateway restart` si multi-profil). Le snapshot se regenere au prochain tick — verifier apres 5-10s.
- Verif finale: actifs=84, `_archive` inexistant, `.archive`=65, snapshot count=84 sans `_archive`.

## Pitfalls
- Compter `skills_list` brut (90 lignes) inclut header/lignes table — ne pas confondre avec `find SKILL.md` (84).
- Supprimer `_archive` vide n exige pas `hermes curator archive`; le re-seed ne revient que si `.curator_suppressed` manque.
- Ne pas editer `.skills_prompt_snapshot.json` a la main — le supprimer force un rebuild propre.
