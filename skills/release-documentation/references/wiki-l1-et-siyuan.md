# Page wiki L1 + note SiYuan : recette locale

Mecanique des etapes 2 et 4 de la publication documentaire. Valable pour tout
depot cure dans le second cerveau, pas seulement pour une release.

## Page du wiki L1

- Chemin : `wiki/<section>/<slug>.md`, sections `concepts`, `entities`,
  `comparisons`, `queries`, `syntheses`. Le champ `type` du frontmatter doit
  correspondre au dossier (`concept` -> `concepts`, `summary` -> `syntheses`) :
  un `type` incoherent est un echec du verificateur.
- Frontmatter obligatoire : `title`, `created`, `updated`, `type`, `tags`,
  `sources` (plus `confidence`).
- **Tags issues de la taxonomie de `SCHEMA.md`** : un tag nouveau s'ajoute
  d'abord dans `SCHEMA.md`, sinon la page est refusee.
- **Minimum 2 wikiliens** dans le corps, chacun visant un slug qui existe
  (`[[fallback-chain]]`, pas `[[fallback chain]]`).
- `sources` ne cite que des fichiers presents dans `raw/`.
- Une page se lit en 30 s ; au-dela de ~200 lignes, decouper.

## Catalogue sans appel LLM

    cd <WIKI>/scripts && python -c "
    import importlib.util
    spec = importlib.util.spec_from_file_location('cw', 'compile_wiki.py')
    cw = importlib.util.module_from_spec(spec); spec.loader.exec_module(cw)
    cw.update_index([], dry=False)"

- L'import ne declenche aucun appel reseau : `main()` porte l'appel au modele.
  C'est ce qui rend l'ajout manuel gratuit en quota.
- `update_index([])` reconstruit le catalogue depuis TOUTES les pages du disque —
  la nouvelle prend le titre ou la premiere phrase du corps, les autres gardent
  leur ligne. Controler : `Last updated:` bouge, `Total pages:` +1, entree en
  ordre alphabetique dans la bonne section.
- `log.md` : append `## [YYYY-MM-DD] create | page <chemin relatif>` (actions
  admises : ingest, update, query, lint, create, archive, delete).
- Ne PAS lancer `compile_wiki.py` pour un ajout redige a la main : il n'ingere que
  les sources de `raw/` et coute un appel LLM.

## Verification

`python scripts/verify_wiki.py` (script du skill ; `WIKI_PATH`, sinon
`%LOCALAPPDATA%\hermes\wiki`). Il controle frontmatter, `type` vs dossier, tags,
`sources` de `raw/`, liens resolus, presence et unicite dans `index.md`, en-tete
`Total pages` egal au nombre de fichiers, au moins une entree de log, et signale
les pages plutot anglaises. **Lire son code de retour** : `EXIT=0` avec
« echecs (0) » est la seule preuve acceptable avant d'annoncer l'ajout.

## Note SiYuan

1. `POST /api/notebook/lsNotebooks` et **reprendre l'id** du notebook de domaine
   (un nom peut porter un tiret long : « Infrastructure — Providers LLM » — le
   nom se lit, il ne se devine pas).
2. Chercher un doublon avant de creer :
   `SELECT id, content, hpath FROM blocks WHERE type='d' AND content LIKE '%<mot-clef>%'`.
   Creer un doublon est l'echec silencieux de cette etape.
3. Ecrire le corps markdown dans un fichier JSON, puis
   `POST /api/filetree/createDocWithMd` (`notebook`, `path`, `markdown`).
   - `path` : `/Titre - JJ-MM-AAAA`. **Aucun autre `/`** : SiYuan mappe le chemin
     sur le disque et fabrique une arborescence parasite sans erreur.
   - **Pas de frontmatter YAML** dans `markdown` : SiYuan genere le sien et
     afficherait le notre comme du texte.
   - Corps : resume des nouveautes, liens (release, page wiki, CHANGELOG) et
     renvoi « detail dans `docs/<fichier>.md` ».
4. Prouver : `getHPathByID` (chemin humain) + `getBlockKramdown` (corps relu,
   longueur attendue). `code: 0` seul ne prouve pas que le corps est complet.

## Corriger un paragraphe d'une note existante

Corriger sur place, sans recreer la note (une note recreee perd son id, ses
liens entrants et son historique) :

1. Trouver le bloc a retoucher par le doc, pas par le texte :
   `SELECT id, type, content FROM blocks WHERE root_id='<id du doc>' AND type='p'`.
   Restreindre a `p`/`h`/`c` — **jamais `l` ni `i`** : `updateBlock` sur un item
   de liste remplace aussi ses enfants, donc une correspondance sur une
   sous-puce efface l'arborescence.
2. `getBlockKramdown` du bloc, **remplacement de chaine** sur la seule valeur
   fautive (garder le reste du paragraphe verbatim, y compris la ligne
   d'attributs `{: id="..." }` renvoyee par la lecture), puis
   `updateBlock {id, data, dataType: "markdown"}`.
3. Prouver la correction sur le document entier, pas sur le bloc :
   `exportMdContent` du doc et controler dans le meme passage (a) **tous les
   titres** releves avant l'edition sont encore la, (b) l'ancienne valeur est
   absente, (c) la nouvelle est presente le bon nombre de fois, (d) le nombre de
   blocs du doc (`SELECT COUNT(*) FROM blocks WHERE root_id=...`) n'a pas bouge.
   Un `code: 0` sur `updateBlock` ne prouve rien de tout cela.
4. Si la note a ete ecrite sans accents, garder ce parti pris dans le texte
   corrige : seul le mot fourni par la demande porte l'accent.
