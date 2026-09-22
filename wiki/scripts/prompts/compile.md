# Prompt de compilation du wiki L1 (cron « LLM Wiki compile »)

Exécuter ces instructions dans l'ordre. Wiki : `C:\Users\searc\AppData\Local\hermes\wiki`
(variable d'environnement `WIKI_PATH`). Le skill `llm-wiki` décrit les conventions.

1. **ORIENTATION** (obligatoire avant toute écriture) : lis `SCHEMA.md`, puis
   `index.md`, puis les 20 dernières lignes de `log.md`. Sans ça, tu crées des
   doublons et tu casses les cross-références.
2. **SOURCES À TRAITER** : liste les fichiers de `raw/notes/` (et `raw/articles/`,
   `raw/papers/`, `raw/transcripts/`) dont le chemin n'apparaît dans aucun champ
   `sources:` d'une page existante (`search_files` sur `raw/notes/<fichier>`).
   Traite ces sources uniquement.
3. **PAGES** : crée ou mets à jour les pages dans `concepts/` et `entities/`
   (et `comparisons/` si deux briques sont mises côte à côte). Contraintes strictes :
   - frontmatter YAML complet : `title`, `created`, `updated`, `type`
     (`entity|concept|comparison|query|summary`), `tags`, `sources` ;
   - noms de fichiers en kebab-case, minuscules, sans espaces ;
   - **minimum 2 liens `[[wikilinks]]` par page**, et vérifie que les pages
     existantes pointent en retour ;
   - tags **uniquement** pris dans la taxonomie de `SCHEMA.md` ;
   - seuil : créer une page si le sujet apparaît dans **2+ sources** ou s'il est
     **central à une seule** source ; ne pas créer de page pour une mention de passage ;
   - **synthétiser**, ne pas recopier la source ; une page se lit en 30 secondes ;
   - si une information contredit une page existante : suivre la « Politique de mise
     à jour » du SCHEMA (`contested: true`, `contradictions: [...]`) et ajouter une
     entrée dans `contradictions.md`.
4. **NAVIGATION** : ajoute chaque nouvelle page à `index.md` (bonne section, ordre
   alphabétique), mets à jour l'en-tête (`Last updated`, `Total pages`), puis ajoute
   une entrée dans `log.md` : `## [YYYY-MM-DD] ingest | <sujet>` avec la liste des
   fichiers créés ou modifiés.
5. **INTERDIT** : modifier, renommer ou supprimer quoi que ce soit dans `raw/`
   (sources immuables) et dans `scripts/`.
6. **SORTIE** : termine par la liste exacte des fichiers créés ou modifiés
   (chemins complets). Si aucune source nouvelle n'est à traiter, écris
   « rien à compiler » et ne touche à rien.

## Budget et méthode (important — modèle gratuit, budget d'outils limité)

- **Maximum 15 appels d'outils au total.** Ne lis pas les fichiers un par un :
  lis `SCHEMA.md` + `index.md` + la fin de `log.md` + les sources de `raw/notes/`
  en **un seul** appel `terminal` (par exemple `cat` de plusieurs fichiers).
- **N'utilise pas `search_files` en boucle.** Une seule passe sur `sources:` suffit
  pour savoir ce qui est déjà compilé.
- Écris ensuite **toutes** les pages en un seul passage (`write_file` par page),
  puis mets à jour `index.md` et `log.md` en un seul passage.
- **Ne relis jamais un fichier que tu viens d'écrire** et ne reformate rien :
  tu n'as pas les appels d'outils pour itérer.
- Vise **6 à 10 pages** au total sur ces 5 sources : c'est suffisant pour amorcer
  le wiki, les ticks suivants enrichiront.
