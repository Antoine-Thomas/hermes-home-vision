# Lecture seule de l'API SiYuan (recettes pour harness et garde-fous)

Toutes ces routes passent par `wiki_writer._api(route, payload)` → `(ok, body)`. Aucune n'écrit.
`ok=False` ⇒ `body` porte `erreur` ; ne JAMAIS conclure « absent » sur une lecture échouée.

## 1. Résoudre un nom de notebook en id — sans jamais créer

```python
ok, body = w._api("/api/notebook/lsNotebooks", {})
lister = {n["name"]: n["id"] for n in (body.get("data") or {}).get("notebooks", [])}
```

Nom absent de `lister` → message clair + code 1, aucune `createNotebook`.

## 2. Énumérer TOUS les titres d'un notebook (récursif, sans SQL)

`listDocsByPath` liste UN niveau :

- racine : `{"notebook": nid, "path": "/"}` ;
- enfants d'un doc hiérarchique : `{"notebook": nid, "path": <champ "path" du parent>}`.
  Ce champ vaut son chemin `.sy` (`/2026….sy`), **pas** son hpath : `path="/<nom>"` renvoie `[]` sans erreur.

Chaque item porte `name` (titre), `id`, `path` et `subFileCount` (0 = feuille). `subFileCount`
arrive tard dans l'objet : ne pas juger sur une sortie tronquée.

```python
def titres(nid, chemin="/", prof=0):
    if prof > 8:
        return None
    ok, body = w._api("/api/filetree/listDocsByPath", {"notebook": nid, "path": chemin})
    if not ok:
        return None
    out = []
    for f in (body.get("data") or {}).get("files") or []:
        if f.get("name"):
            out.append(f["name"])
        if (f.get("subFileCount") or 0) > 0 and f.get("path"):
            sous = titres(nid, f["path"], prof + 1)
            if sous is None:
                return None
            out += sous
    return out
```

`None` = lecture impossible ⇒ ne rien décider (surtout pas « absent »).

## 3. Garde anti-doublon complet

1. Existence au hpath visé : `create_doc(..., if_exists="skip")` (filetree, sous verrou, anti-TOCTOU).
2. Garde supplémentaire, lecture seule : si le titre visé figure dans `titres(nid)` mais **pas** à la racine,
   un doc identique vit ailleurs (sous-dossier) → ne rien créer, message clair, code 1.

## 4. Compter les documents d'un notebook

```python
ok, body = w._api("/api/query/sql",
                  {"stmt": "SELECT id FROM blocks WHERE type='d' AND box='%s'" % nid})
n = len(body.get("data") or [])
```

SQL récursif (compte les docs en sous-dossier) mais ~1 s de retard après une écriture :
à n'utiliser que pour un inventaire STABLE, jamais comme anti-doublon.

## 5. Lire le contenu d'un doc

- `POST /api/block/getBlockKramdown {"id": doc_id}` → contenu stocké brut, annotations
  `{: id="…" updated="…" }` intercalées à retirer.
- `POST /api/export/exportMdContent {"id": doc_id}` → Markdown « propre » MAIS décoré :
  frontmatter YAML + titre en H1 + deux espaces en fin de ligne. Comparer à une source après
  retrait du frontmatter, retrait de la ligne `# <titre>` et `rstrip()` par ligne.
- `POST /api/filetree/getHPathByID {"id": doc_id}` → hpath réel du doc.

## 6. Snapshot de stabilité (avant/après un harness)

Par notebook réel : `{doc_id: sha256(exportMdContent(doc_id))}` + compte SQL ; plus SHA256 de
`index.faiss` et `chunks.jsonl`, et l'état de la tâche de reindex (`.State`, `.LastTaskResult`,
`.LastRunTime`). Comparer une empreinte globale
(`sha256(repr(sorted((nom, sorted(docs.items())) for nom, docs in snap.items())))`) plutôt que de
relire à l'œil — et restaurer l'état trouvé (ne pas « forcer activé »).

## 7. Verrous

`acquire_lock` crée `data\siyuan\locks\<notebook_id>.lock` ; `release()` déverrouille et ferme mais
NE SUPPRIME PAS le fichier. Un harness qui supprime un notebook jetable doit supprimer aussi son
`.lock`, sinon la vérification « locks/ propres » échoue.
