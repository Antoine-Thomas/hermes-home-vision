<!-- Source: autonomous-ai-agents/quick-skill/SKILL.md (archived 2026-09-10) -->

---
name: quick-skill
description: "Creer un skill Hermes depuis une description en francais."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [skills, meta, generation, scaffold, validation, hermes]
    related_skills: [hermes-agent]
prerequisites:
  commands: [python, hermes]
---

# quick-skill : transformer une phrase en skill installe

L'utilisateur decrit ce qu'il veut ("je veux un skill qui verifie mes
certificats SSL et me previent 30 jours avant expiration"), et ressort avec
un skill valide, installe et immediatement utilisable. Aucun YAML ecrit a la main.

## When to Use — quand l'utiliser

Declencher des que l'utilisateur dit, dans n'importe quelle formulation :

- "cree-moi un skill qui...", "fais-en un skill", "retiens cette procedure"
- "je veux pouvoir refaire ca plus tard", "transforme ca en routine"
- "ajoute un skill pour..."
- ou apres une tache complexe reussie, quand on propose de la capitaliser

Ne PAS l'utiliser pour modifier un skill existant : la, c'est
`skill_manage(action='patch')` directement.

### Depuis une conversation : `--from-session`

Si la procedure vient d'etre executee dans la conversation en cours (ou si
l'utilisateur colle un resume), ne pas rediger le corps a la main : passer le
texte a `--from-session`, qui extrait declencheurs, etapes, commandes, pieges
et verification, puis valide.

```bash
python scripts/newskill.py --from-session "<resume ou chemin de fichier>" \
  --name mon-skill --category devops
```

`--description` devient optionnelle (deduite, <= 60 car.). L'extraction est
mecanique : **relire le corps genere**, les manques sont marques
`(a completer)`. Pour une procedure inedite qu'on maitrise deja, `--body`
reste plus precis.

## Le script

`scripts/newskill.py` fait tout le mecanique : frontmatter, validation,
chemin d'installation, verification post-installation.

Le recuperer avec `skill_view(name='quick-skill', file_path='scripts/newskill.py')`
ou l'appeler par son chemin :

```
~/AppData/Local/hermes/skills/autonomous-ai-agents/quick-skill/scripts/newskill.py
```

## Procedure

### 1. Extraire les 6 elements de la demande

Ne jamais inventer : si un element manque et qu'il change le contenu du skill,
poser UNE question groupee avec `clarify`. Sinon, choisir un defaut raisonnable.

| Element | Regle |
|---|---|
| `nom` | minuscules, tirets, <= 64 car. Deduit de la demande (`ssl-expiry-check`) |
| `description` | **60 caracteres MAXIMUM**, une phrase, se termine par un point |
| `categorie` | reutiliser une categorie existante (`devops`, `productivity`, ...) |
| declencheurs | les formulations exactes que l'utilisateur emploiera |
| etapes | numerotees, avec les COMMANDES exactes, pas des intentions |
| verification | comment savoir que ca a marche |

La contrainte des 60 caracteres est stricte : au-dela, Hermes tronque la
description a 57 car. + `...` dans l'index et le skill ne se declenche plus.
Le script refuse la creation dans ce cas.

### 2. Ecrire le corps dans un fichier temporaire

Markdown, sans frontmatter (le script l'ajoute). Structure attendue :

```markdown
# <Titre lisible>

<1-3 phrases : ce que ca fait, pour qui>

## Quand l'utiliser

- <declencheur 1, formule comme l'utilisateur le dirait>
- <declencheur 2>

## Procedure

### 1. <Etape>

```bash
<commande exacte>
```

### 2. <Etape>
...

## Pieges

1. **<Piege>** : <pourquoi ca casse et quoi faire>

## Verification

```bash
<commande qui prouve que ca a marche>
```
```

Ecrire ce fichier avec `write_file` dans `$LOCALAPPDATA/Temp/` (jamais sur le Bureau).

### 3. Generer et installer

```bash
python "<chemin>/scripts/newskill.py" \
  --name ssl-expiry-check \
  --description "Verifier l'expiration des certificats SSL." \
  --category devops \
  --tags ssl,certificats,monitoring \
  --body "$LOCALAPPDATA/Temp/corps.md"
```

Options utiles :

- `--dry-run` : affiche le SKILL.md final sans rien ecrire (a montrer a l'utilisateur avant validation)
- `--force` : ecrase un skill existant du meme nom
- `--check <nom>` : valide un skill deja installe sans le modifier

Le script sort en code `2` si la validation echoue, et dit precisement quoi corriger.

### 4. Rendre disponible immediatement

```bash
hermes skills list | grep -i ssl-expiry-check
```

Puis, dans la session en cours :

```
/reload-skills
```

Sans `/reload-skills`, le skill existe sur le disque mais n'est pas dans l'index
de la session courante. Il sera de toute facon charge aux sessions suivantes.

### 5. Verifier le contenu charge

```
skill_view(name='ssl-expiry-check')
```

Confirmer a l'utilisateur : le nom, le chemin, la description reelle, et la
phrase exacte a dire pour le declencher.

## Pieges

1. **Description > 60 caracteres** : cause d'echec la plus frequente. Compter
   avant d'appeler le script. `skill_manage(action='create')` rejette aussi.
2. **Ecrire le skill directement avec `skill_manage(action='create')`** marche,
   mais on perd le validateur : pas de controle du nom, pas de detection de
   section manquante, pas de verification post-installation. Passer par le script.
3. **Section "Quand l'utiliser" absente** : le linter de Hermes emet un
   avertissement et surtout le skill ne se declenche jamais au bon moment.
   Le script refuse un corps sans section de declencheurs.
4. **Nom en CamelCase ou avec des espaces** : rejete. Minuscules et tirets.
5. **Skill trop generique** ("aider avec le web") : il se declenche tout le
   temps ou jamais. Un skill = une tache reconnaissable.
6. **Ne pas mettre de secrets dans le corps du skill** : les skills sont des
   fichiers en clair et passent dans le prompt systeme.
7. **Categorie inventee** : verifier avec `ls ~/AppData/Local/hermes/skills/`
   avant d'en creer une nouvelle, sinon l'arborescence se fragmente.
8. **Toute date dans le frontmatter doit etre entre guillemets.** `created: 2026-08-25`
   est parse par YAML en objet `datetime.date`, et `skill_view` echoue alors avec
   `Object of type date is not JSON serializable` : le skill devient illisible.
   Ecrire `created: "2026-08-25"`. Le script le fait deja ; y penser si on edite
   un frontmatter a la main.
9. **Le linter de Hermes teste `^#+\s+When to Use` — ancre en DEBUT de titre.**
   `## Quand l'utiliser (When to Use)` echoue quand meme, parce que le titre
   commence par "Quand". Ecrire `## When to Use — quand l'utiliser`.
   (Source : `hermes-agent/tools/skill_linter.py`, `_EXPECTED_SECTIONS`.)

## Verification

```bash
# le skill est installe et valide
python "<chemin>/scripts/newskill.py" --check ssl-expiry-check

# il apparait dans l'index
hermes skills list | grep -i ssl-expiry-check
```
