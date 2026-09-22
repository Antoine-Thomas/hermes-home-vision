# Prompt d'archivage (cron « LLM Wiki archive », hebdomadaire)

Wiki : `C:\Users\searc\AppData\Local\hermes\wiki`. Lis d'abord `SCHEMA.md`
(section « Archivage (90 jours) »), `index.md`, `log.md`.

1. **CANDIDATES** : pages de `concepts/`, `entities/`, `comparisons/`, `queries/`,
   `syntheses/` dont la date `updated` du frontmatter dépasse **90 jours**.
   Calcule la liste en code (script Python ou commande), ne l'estime pas de tête.
2. **VÉRIFICATION AVANT ARCHIVAGE** : une page ancienne n'est archivée que si son
   contenu est **entièrement remplacé** ou si plus aucune source récente ne mentionne
   les mêmes entités. Dans le doute, laisse la page en place et signale-la.
3. **ARCHIVAGE** (méthode du SCHEMA) :
   - crée `_archive/<chemin d'origine>` si nécessaire et déplace la page (conserve le
     chemin relatif d'origine dans `_archive/`) ;
   - retire l'entrée de `index.md` et corrige `Total pages` ;
   - remplace les `[[wikilinks]]` qui pointaient vers elle par du texte simple suivi
     de « (archived) » dans toutes les pages qui la citaient ;
   - journalise dans `log.md` : `## [YYYY-MM-DD] archive | <page>` avec la raison.
4. **INTERDIT** : toucher à `raw/` et `scripts/`. Ne jamais supprimer un fichier :
   l'archivage est un déplacement, pas une suppression.
5. **SORTIE** : liste des pages archivées (ancien chemin → nouveau chemin), liste des
   pages laissées en place avec la raison, liste des fichiers modifiés.
