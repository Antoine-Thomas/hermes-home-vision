---
name: recherche-skills-officiels
description: "Use when rien en local : chercher dans le Skills Hub."
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [Hermes, Skills, Recherche, Auto-amelioration]
---

# Recherche de skills dans la documentation officielle

## When to Use

A declencher **systematiquement** quand une solution n'a pas ete trouvee dans les ressources
locales, dans cet ordre :

1. les skills locaux (`skills_list`, `/skills`) ;
2. le RAG local (documents SiYuan, skills, scripts v4, depot WordPress) ;
3. les venvs et les outils installes sur la machine.

Si les trois echouent, cette sequence se declenche **avant de dire « je ne sais pas »**. Une
competence manquante n'est jamais un mur : elle est un skill a trouver, a installer ou a creer.

## Quick Reference

```
# 1. chercher dans le Hub (tableau : nom, description, source, confiance, identifiant)
hermes skills search <mots-cles>
hermes skills search <mots-cles> --source official --limit 20
hermes skills search <mots-cles> --json

# 2. inspecter puis installer
hermes skills inspect <identifiant>
hermes skills install official/<categorie>/<nom>
hermes skills install https://exemple.com/SKILL.md --name mon-skill

# en session de chat
/skills search <mots-cles>      /skills browse      /skills install <identifiant>
```

| Source (`--source`) | Contenu |
|---|---|
| `official` | skills officiels optionnels livres avec Hermes |
| `skills-sh`, `well-known`, `github`, `clawhub`, `lobehub`, `browse-sh` | registres et depots |
| `nvidia`, `openai`, `anthropic`, `huggingface`, `voltagent`, `gstack`, `minimax` | editeurs |
| `all` | tout (defaut) |

## Procedure

1. **Chercher dans le Hub.** `hermes skills search "<mots-cles>"`. Lire l'identifiant, pas
   seulement le nom : l'identifiant dit d'ou vient le skill (`official/...` = confiance officielle).
   Plusieurs requetes valent mieux qu'une : un mot francais et son equivalent anglais technique
   ne donnent pas les memes resultats.
2. **Un skill pertinent existe** : `hermes skills inspect <identifiant>` pour lire avant
   d'installer, puis `hermes skills install <identifiant>`. Verifier ensuite qu'il apparait dans
   `hermes skills list`.
3. **Aucun skill n'existe** : le creer soi-meme, au format officiel ci-dessous.
4. **Referencer ce qu'on vient d'installer ou de creer.** Un skill hors index est un skill
   introuvable : relancer l'indexation du RAG (voir Verification).

## Creer un skill Hermes — format officiel

Pour repondre a « comment creer un skill Hermes » / « creer un nouveau skill », voici la forme
attendue, telle que la decrit le guide de creation.

Emplacement : `%LOCALAPPDATA%\hermes\skills\<categorie>\<nom-du-skill>\SKILL.md`
(+ `scripts/` si des scripts sont necessaires, un dossier optionnel).

```yaml
---
name: nom-du-skill            # minuscules et tirets
description: "Use when <declencheur>. <une phrase>."   # 60 caracteres maxi :
                              # c'est ce que voit la recherche de skills
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [Categorie, Sous-categorie, Mots-cles]
---
```

Sections du corps, dans cet ordre :

```markdown
## When to Use      # quand charger ce skill : les conditions de declenchement
## Quick Reference  # tableau des commandes ou appels courants
## Procedure        # les etapes, dans l'ordre que l'agent suit
## Pitfalls         # les modes d'echec connus et comment les traiter
## Verification     # comment l'agent confirme que ca a marche
```

Champs optionnels utiles : `platforms: [windows]` (le skill est masque sur les autres systemes) et
`metadata.hermes.blueprint` (avec `schedule`, `deliver`, `prompt`) pour faire d'un skill une
automatisation planifiee partageable.

## Pitfalls

- **`hermes skills search` interroge les registres distants, pas les skills locaux.** Un skill
  qu'on vient de creer ne sortira jamais de cette commande : il se verifie avec
  `hermes skills list` (colonne Source = `local`) et avec `skills_list`. Ne pas conclure « mon skill
  n'existe pas » parce que le Hub ne le trouve pas.
- Dans `hermes skills list`, les noms longs sont tronques dans le tableau (`recherche-skills-of…`) :
  chercher avec `grep -i` sur un fragment du nom, pas sur le nom entier.
- **Le Hub n'est pas dans le RAG.** Ce skill decrit le mecanisme ; le catalogue se consulte en
  ligne, a chaque fois. Ne jamais repondre de memoire sur le contenu du catalogue.
- `hermes skills install` refuse une installation si le scan de surete rend un verdict bloquant.
  `--force` passe outre : ne jamais l'utiliser sans avoir lu le SKILL.md, ligne par ligne.
- La confiance affichee (`Trust`) n'est pas un audit. Un skill tiers s'installe dans un dossier que
  l'agent execute : le lire avant de l'installer.
- **Un skill cree n'est pas indexe automatiquement.** Sans `indexer.py`, il ne sortira pas du RAG.
- Un skill qui ne vise pas la plateforme courante est masque de `skills_list` : si un skill
  officiel reste introuvable, verifier son champ `platforms` dans le guide de creation.
- Ne pas modifier `config.yaml` pour ce workflow : tout passe par le CLI et le dossier de skills.

## Verification

```
hermes skills search "<mots-cles>"        # le skill apparait avec son identifiant
hermes skills list | grep <nom>          # installation confirmee
hermes skills inspect <identifiant>      # contenu relu avant usage

# un skill cree est bien vu par Hermes et par le RAG
hermes skills list | grep <nom-du-skill>
%LOCALAPPDATA%\hermes\data\rag\venv\Scripts\python.exe \
    %LOCALAPPDATA%\hermes\data\rag\chercher.py "<sujet du skill>" -k 3
```

## Sources officielles

- Skills Hub (catalogue) : https://hermes-agent.nousresearch.com/docs/skills
- Creer un skill : https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills
- Utiliser les skills : https://hermes-agent.nousresearch.com/docs/guides/work-with-skills

Resume de ces trois sources dans SiYuan, notebook `veille`,
document « Sources officielles Hermes - skills ».
