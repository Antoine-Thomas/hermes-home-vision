# Prompt de détection des contradictions (cron « LLM Wiki contradictions »)

Wiki : `C:\Users\searc\AppData\Local\hermes\wiki`. Lis d'abord `SCHEMA.md`
(section « Politique de mise à jour »), `index.md`, puis les 20 dernières lignes de `log.md`.

1. **PÉRIMÈTRE** : toutes les pages de `concepts/`, `entities/`, `comparisons/`,
   `queries/`, `syntheses/`.
2. **DÉTECTION** : repère les pages qui partagent des tags/entités mais affirment des
   faits incompatibles (valeurs, dates, PID, ports, versions, seuils, architectures).
   Compare en priorité les couples qui se citent mutuellement en `[[wikilinks]]` et
   ceux dont le frontmatter porte déjà `contested: true`.
3. **TRAITEMENT** de chaque contradiction réelle :
   - n'écrase **jamais** une affirmation : note les deux positions avec leur date et
     leur source dans la page concernée ;
   - pose dans le frontmatter de chaque page impliquée : `contested: true` et
     `contradictions: [slug-de-l-autre-page]` ; incrémente `updated` ;
   - mets à jour la section « Contradictions ouvertes » de `contradictions.md` au
     format décrit en tête de ce fichier ; si la contradiction se tranche par la date
     ou la source, déplace-la dans « Contradictions tranchées » avec la raison.
4. **JOURNAL** : ajoute `## [YYYY-MM-DD] lint | contradictions` dans `log.md` avec le
   nombre de contradictions trouvées et les pages touchées.
5. **INTERDIT** : modifier quoi que ce soit dans `raw/` ou `scripts/`.
6. **SORTIE** : liste des contradictions (page A vs page B, sujet, positions) et liste
   des fichiers modifiés. Si aucune contradiction : écris « aucune contradiction » et
   n'écris rien sur le disque.
