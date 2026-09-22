# Compilation non-agentique : tout le wiki en UN appel LLM

Un tick d'agent ne peut PAS compiler le wiki. Ne pas reessayer : c'est
structurel, pas un manque de patience.

## When to Use (Quand utiliser)

- Avant tout ingest/compile : c'est TOUJOURS ce script, jamais un tour d'agent.
- Quand un job « LLM Wiki compile » echoue en `429`/`504` ou part sur le modele
  payant (`billing_provider=deepseek`) alors qu'il est cense tourner en `eco`.
- Quand les pages produites sortent en anglais, avec des liens morts, ou quand un
  modele recopie le gabarit du prompt.
- Quand on branche un nouveau modele gratuit comme source de compilation.

## Pourquoi l'agent echoue (mesure)

- **Interrupt dur de 3 minutes sur tout run cron.** La compilation fait plusieurs
  tours (orientation -> sources -> ecriture -> index -> log) et se fait couper en
  route.
- **~16 K tokens de prompt systeme a CHAQUE tour** (index des skills, schemas
  d'outils) : les paliers gratuits sautent en debit/minute et la chaine part sur
  le payant.

Symptomes typiques : `OmniRoute 504 requestQueue.maxWaitMs`, `429 cooling down`,
`Fallback activated: deepseek` dans `agent.log`, et un `billing_provider=deepseek`
sur un job cense tourner en `eco`.

## Le script

`wiki/scripts/compile_wiki.py` — stdlib seule, process unique, AUCUN tour
d'agent : il lit `SCHEMA.md` + `index.md` + `log.md` + les sources de `raw/`,
envoie **un seul** POST, parse le JSON, ecrit les pages et met a jour
`index.md`/`log.md`.

    python compile_wiki.py                    # sources non encore citees
    python compile_wiki.py --all              # recompile tout (relit index.md)
    python compile_wiki.py --dry-run          # n'ecrit rien
    python compile_wiki.py --rounds 4 --gap 120 --timeout 900 --max-tokens 16000

Lanceur cron : `%LOCALAPPDATA%\hermes\scripts\wiki_compile.py`, job en
`script + no_agent` (zero appel LLM, timeout script 3600 s). Le champ `script`
d'un job cron est resolu sous `<HERMES_HOME>\scripts\` — un script hors de ce
dossier remonte `script resolves outside ...` dans le health check du job.

## Ce qui fait marcher ou casser le prompt

- **La langue s'obtient par l'EXEMPLE, pas par la regle.** Trois consignes
  « redige en francais » ont ete ignorees ; c'est la mise en francais du GABARIT
  de sortie (title/summary/body) qui a produit des pages francaises. Un modele
  imite l'exemple et survole les regles.
- **Les liens doivent etre des slugs kebab-case exacts.** Un modele rend
  `[[fallback chain]]` pour `concepts/fallback-chain.md` -> lien mort. L'ecrire
  noir sur blanc ET le verifier apres ecriture.
- **Les modeles de raisonnement brulent `max_tokens` avant d'ecrire le JSON**
  (mesure : 23 327 car. de raisonnement pour 2 305 car. de contenu, donc
  troncature). Budgeter 16 000, pas 8 000.
- **Prefill assistant `{`** : aide, mais un modele peut re-emettre sa propre
  accolade -> ne pas coller `{{` (JSON invalide). Tolerer les deux cas.
- **Un modele faible recopie le GABARIT** du prompt (slug `nom-du-concept`,
  corps d'exemple) et le tronque. Rejeter ces pages par marqueur, et refuser
  d'ecrire si aucune page ne survit — sinon le wiki se remplit de pages vides.

## Robustesse de lecture

- `json.loads(..., strict=False)` : un modele emet couramment des retours a la
  ligne bruts dans les chaines JSON, rejetes par `strict=True`.
- **Recuperer les objets complets d'un tableau `pages` tronque** en suivant la
  profondeur des accolades (celles des chaines ignorees) et en parsant page par
  page. Une reponse coupee par `finish_reason=length` n'est pas reparable
  autrement.
- Un flux SSE peut porter `{"error": ...}` avec un statut **HTTP 200** : le
  remonter tel quel, sinon l'echec se lit « reponse vide » et la cause est
  perdue.

## Controles avant de dire « compile »

- liens morts, tags hors taxonomie, moins de 2 `[[wikilink]]`, langue de la page ;
- **refuser d'ecrire si aucune page n'est exploitable** (exit non nul, `index.md`
  et `log.md` intacts) ;
- `index.md` se reconstruit a partir de TOUTES les pages du disque, pas du seul
  lot — sinon une page non retouchee disparait du catalogue. Dedoublonner les
  commentaires de section et ne jamais laisser un libelle qui repete le slug ;
- verifier avec un script INDEPENDANT du compilateur : frontmatter complet, `type`
  coherent avec le dossier, tags, sources reelles de `raw/`, liens resolus,
  en-tete `Total pages` egal au nombre de fichiers.
