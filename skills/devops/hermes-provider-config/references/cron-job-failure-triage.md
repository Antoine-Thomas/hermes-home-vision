# Diagnostiquer un job cron Hermes en echec (lecture seule)

Un job qui echoue (`503`, `all targets skipped`, `RuntimeError: Service temporarily unavailable`)
laisse quatre artefacts. Aucun ne suffit seul : la definition dit ce qui etait demande, l'historique dit
ce qui s'est passe, `state.db` dit qui a reellement servi, le journal dit pourquoi ca a casse.

Regle de la phase : aucune ecriture. `.env` jamais lu (noms de variables seulement), valeurs de cles
jamais imprimees (longueur + `sha256(valeur)[:8]` pour comparer deux cles entre elles).

## 1. La definition : `<profil>/cron/jobs.json`

```python
import io, json
j = json.load(io.open('profiles/<p>/cron/jobs.json', encoding='utf-8'))['jobs'][0]
print({k: j.get(k) for k in ('id','schedule','enabled','state','model','provider','base_url',
        'model_snapshot','provider_snapshot','last_status','last_error','failure_streak',
        'next_run_at','deliver','skills','timeout_seconds')})
print('prompt_chars =', len(j.get('prompt','')))
```

Lecture :

- `model` / `provider` / `base_url` a `null` -> **aucun epinglage** : le job parcourt le `model.default`
  et la chaine du profil (donc les modifier change le job sans toucher `jobs.json`).
- `model_snapshot` / `provider_snapshot` -> traces ecrites a la creation, **inertes** : ne pas les
  confondre avec le modele servi.
- `failure_streak` + `last_error` -> la panne telle que le planificateur l'a enregistree.
- Un `prompt` court (< 2 000 caracteres) ne peut pas etre la cause d'un echec : mesurer le contexte
  ACCUMULE (voir §4) avant d'accuser la longueur du prompt.

## 2. L'historique des runs : `<profil>/cron/executions.db`

```python
import sqlite3
c = sqlite3.connect('file:profiles/<p>/cron/executions.db?mode=ro', uri=True); c.row_factory = sqlite3.Row
print([r[1] for r in c.execute('PRAGMA table_info(executions)')])
for r in c.execute('select * from executions order by rowid desc limit 12'):
    print(dict(r))
```

- Le suffixe URI `?mode=ro` est la garantie de lecture seule (un `sqlite3.connect` nu peut creer le
  fichier : jamais acceptable dans une phase de diagnostic).
- Duree = `finished_at - started_at`. `source` : `builtin` = planificateur en process (gateway),
  `direct` = run declenche a la main / par un process neuf.
- Statut `unknown` + `Scheduler restarted after this execution's owner exited` = **run perdu par
  redemarrage du planificateur**, ce n'est pas une panne du job : le dire separement.
- Le regroupement `group by source, status` donne le « dernier succes » : c'est la date a confronter a
  « qu'est-ce qui a change depuis ? ».

## 3. Le modele servi et le cout : `<profil>/state.db` et `cron/usage_audit.jsonl`

```python
for r in c.execute('select id, model, billing_provider, estimated_cost_usd, api_call_count'
                   ' from sessions order by rowid desc limit 8'):
    print(dict(r))
```

- Les ids de session de cron sont de la forme `cron_<jobid>_<AAAAMMJJ_HHMMSS>` : filtrer par
  `id like '%<jobid>%'` pour l'historique du job, sans tri par id (comparaison de chaines).
- `estimated_cost_usd = 0` + `billing_provider = custom` sur toutes les sessions du job = **aucune
  bascule payante** : repondre a « est-ce que ca a paye ? » par cette table, pas par la duree du tour.
- `cron/usage_audit.jsonl` (une ligne par appel) : `model`, `prompt_tokens`, `duration_ms`, `error`.
  `prompt_tokens` a `null` = l'appel a echoue AVANT generation (dispatch), pas en cours de generation.
  Comparer les durees des runs reussis pour fixer la duree cible du job.
- Une session de job absente de `state.db` = run mort avant la premiere completion.

## 4. Le deroule : `<profil>/logs/agent.log`

```bash
grep -a "cron_<jobid>_<AAAAMMJJ>" agent.log | grep -aoE "API call #[0-9]+: model=[^ ]+ summary=.{0,120}"
grep -a "cron_<jobid>_<AAAAMMJJ>" agent.log | grep -aoE "Fallback activated|\(429|\(502|\(503|\(504|all targets were skipped|No target in combo.{0,60}"
```

Codes : `429` = quota (nommer le quota, cf. §5) ; `502`/`504` = amont ou file d'attente locale du proxy ;
`503 all targets were skipped` = plus AUCUNE cible vivante. La ligne terminale porte l'etat du contexte
(`msgs=86 tokens=~12k`) : c'est le volume accumule, pas la taille du prompt.

## 5. La cause cote routeur : `~/.omniroute/logs/application/app.log`

Compter par fenetre horaire plutot que lire :

```bash
grep -a "2026-09-29T1[89]:" app.log | grep -ac "16/16"                       # fenetres NIM saturees
grep -a "2026-09-29T1[89]:" app.log | grep -ac "rate-limit execution expiration"  # file locale 15 s
grep -ac "generate_content_free_tier_requests" app.log                        # plafond Gemini journalier
```

Puis verifier que les cibles du job sont bien autorisees par SA cle de routeur
(`GET http://127.0.0.1:20128/api/keys` -> `modelAccessMode`, `allowedModels`, `providerId` ; valeurs de
cles masquees). Une cible absente de `allowedModels` est une cause a part entiere ; une cible presente
mais sans quota est une panne de fenetre.

Contre-epreuve a chercher avant de conclure a une chaine morte : **le meme combo a-t-il servi un AUTRE
job/profil dans la journee ?** (sessions cron des autres profils, `state.db`). Si oui, la chaine est
vivante et l'echec est un epuisement de fenetre.

## 6. Tableau de preuve a rendre

| Artefact | Ce qu'il prouve | Ce qu'il ne prouve pas |
|---|---|---|
| `jobs.json` | epinglage ou non, dernier statut, texte du prompt | qui a servi, ni pourquoi ca a casse |
| `executions.db` | date/duree/statut/erreur par run, dernier succes | le modele servi, le cout |
| `state.db` + `usage_audit.jsonl` | modele servi, cout, volume de contexte | la cause de l'echec |
| `agent.log` du profil | l'ordre exact de la cascade et les codes | l'etat du routeur en amont |
| `app.log` du routeur | fenetres de quota, saturation, plafonds | la decision d'Hermes |

Chaque constat du rapport porte son etiquette (`etabli` / `hypothese` / `inconnu`) ET sa source. Un
constat « inconnu » utile vaut mieux qu'une explication plausible : nommer la piste (ex. contexte modele
fige d'un planificateur en process) et dire qu'elle n'est pas tranchee.

## Pieges

- **Ne pas sonder les etages pendant une fenetre saturee** : une sonde directe consomme le quota qu'elle
  veut mesurer et fabrique le 503 qu'on cherche a expliquer. Preferer la lecture des journaux du routeur.
- **Ne pas lire `.env`, ne pas imprimer une valeur de cle.** Comparer deux cles (racine contre profil) par
  longueur + `sha256(valeur)[:8]`, jamais par affichage.
- **Ne pas recopier un invariant de la demande comme un fait** (« le quota s'est reconstitue ? », « l'alias
  est casse ? ») : chacun se mesure, et un ecart avec la premisse se declare dans le rapport.
- **Le fichier `jobs.json` est reecrit par le planificateur** : ne jamais l'editer a la main, meme pour
  « juste » corriger un prompt (passer par le CLI cron du profil).

## 7. Taux de succes d'un combo sur ses N derniers appels (`call_logs`)

`~/.omniroute/call_logs/<AAAAMMJJ>/*.json` : un fichier par appel, `summary` = `timestamp`,
`comboName`, `model`, `status`, `provider`, `tokens`. Le champ qui nomme le COMBO est
`summary.comboName` : sur un echec OmniRoute y ecrit l'alias du combo, sur un succes le nom du modele
amont — compter par `model` fait apparaitre un combo a 0 % alors qu'il a servi. Les succes SONT
journalises : un combo sans aucun `status: 200` sur la fenetre est un fait mesure, pas un trou de log.

```python
import json, glob, os, collections
rows = []
for f in glob.glob(os.path.expanduser('~/.omniroute/call_logs/*/*.json')):
    s = (json.load(open(f, encoding='utf-8')) or {}).get('summary', {}) or {}
    rows.append((str(s.get('timestamp')), str(s.get('comboName')), s.get('status')))
rows.sort()
for n in ('eco', 'nvidia-stack', 'free-openrouter'):
    sub = [r for r in rows if r[1] == n][-20:]
    print(n, len(sub), dict(collections.Counter(r[2] for r in sub)))
```

C'est la recette a sortir quand la demande porte « taux de succes des 20 dernieres sondes » — question a
laquelle un fichier d'ETAT de monitoring (`sante_combos.json`) ne peut PAS repondre : il ne porte que le
dernier verdict par combo (`up`, `code`, `checked_at`) et seulement pour les combos listes dans le script
qui le remplit (un script reduit a une seule cible laisse les autres entrees figees a leur derniere
passe). Le dire et attribuer chaque pourcentage a sa fenetre ET a son artefact.
