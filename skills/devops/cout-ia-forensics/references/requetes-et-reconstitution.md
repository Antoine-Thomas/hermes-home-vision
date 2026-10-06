# Requetes et reconstitution — cout IA

Tout est en LECTURE SEULE (`sqlite3.connect("file:<chemin>?mode=ro", uri=True)`, chemin en `/`).

## 1. Bases a scanner

```python
BASES = [("default", HERMES / "state.db")] + [
    (p.parent.name, p) for p in (HERMES / "profiles").glob("*/state.db")]
```
Verifier l'existence de chaque base avant de conclure ; les autres `.db` du profil
(`cron/notepad.db`, `cron/executions.db`, `kanban.db`, `shared-state.db`) ne contiennent pas de sessions.

## 2. Ventilation des sessions payantes

```sql
-- par source / profil / etiquettes
select coalesce(source,'(null)'), count(*), round(sum(estimated_cost_usd),4)
from sessions where billing_provider in ('deepseek','openrouter') group by 1 order by 3 desc;

-- cron vs hors cron sans LIKE (le % casse le formatage Python)
select count(*), round(sum(estimated_cost_usd),4) from sessions
where billing_provider in ('deepseek','openrouter') and substr(id,1,5)='cron_';

-- top sessions : duree via last_activity_at (ended_at est souvent NULL)
select id, model, billing_provider, round(estimated_cost_usd,4),
       api_call_count, input_tokens, output_tokens, cache_read_tokens,
       started_at, last_activity_at
from sessions where billing_provider in ('deepseek','openrouter')
order by estimated_cost_usd desc limit 10;

-- fiabilite du chiffre
select cost_status, cost_source, count(*), round(sum(estimated_cost_usd),4)
from sessions where billing_provider in ('deepseek','openrouter') group by 1,2;
-- puis : select count(actual_cost_usd) ... (0 = jamais reconcilie)

-- cout par MODELE REEL sur une fenetre (attribution repli incluse).
-- GROUP BY sessions.model attribue au modele FINAL : une session servie par nvidia-stack
--   mais qui a brule un repli deepseek-flash en cours de route est comptee « nvidia-stack
--   0,63 $ » alors que la route gratuite n'est JAMAIS facturee. Attribuer chaque session
--   au modele qui a le plus coute, via session_model_usage (plusieurs lignes par session,
--   clivees par base_url/mode/fenetre) :
WITH u AS (
  SELECT session_id, model,
         ROW_NUMBER() OVER (PARTITION BY session_id
           ORDER BY COALESCE(estimated_cost_usd,0) DESC, last_seen DESC) rn
  FROM session_model_usage)
SELECT u.model, COUNT(*), SUM(COALESCE(s.estimated_cost_usd,0))
FROM sessions s JOIN u ON u.session_id = s.id AND u.rn = 1
WHERE s.started_at >= ? AND COALESCE(s.estimated_cost_usd,0) > 0
GROUP BY u.model ORDER BY 3 DESC LIMIT 8;
-- controle : ce total egale sum(estimated_cost_usd) des sessions payantes de la fenetre
--   (chaque session compte une fois) — verifier l'egalite, c'est la preuve que
--   l'attribution ne double-compte ni n'omet une session. Les routes gratuites
--   (nvidia-stack/eco/free-openrouter) y apparaissent a 0 $, le repli sous son vrai nom.
```

## 3. Attribution par jour (le piege structurel)

Comparer, pour chaque jour du releve console :

- sessions **demarrees** ce jour (`started_at` dans la journee) ;
- sessions **actives** ce jour (`started_at < fin` et `coalesce(last_activity_at, started_at) >= debut`).

L'ecart entre les deux colonnes mesure le biais d'attribution. Une difference de fuseau
(console en UTC) se teste en recalculant les deux decoupages (`time.localtime` vs `time.gmtime`) :
si les deux donnent le meme rapport, le fuseau n'est pas l'explication.

## 4. Reconstitution appel par appel (tranche les ecarts de tarif)

```python
RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ INFO \[([^\]]+)\] agent\.conversation_loop: "
    r"API call #(\d+): model=(\S+) provider=(\S+) in=(\d+) out=(\d+) total=(\d+)"
    r"(?: latency=\S+)?(?: cache=(\d+)/(\d+))?")

BAREME = {  # (entree cache miss, sortie, cache hit) par million, heures creuses
    "deepseek-v4-pro":   (0.66, 1.98, 0.022),
    "deepseek-flash":    (0.15, 0.60, 0.003),
    "deepseek-v4-flash": (0.15, 0.60, 0.003),
    "deepseek-chat":     (0.15, 0.60, 0.003),
}
PAYANT = {"deepseek", "openrouter"}   # a croiser avec billing_base_url de la session

def facteur(ts):                      # heures pleines : x2, 01-04 et 06-10 UTC, lun-ven
    u = time.gmtime(time.mktime(time.strptime(ts, "%Y-%m-%d %H:%M:%S")))
    return 2.0 if (u.tm_wday < 5 and (1 <= u.tm_hour < 4 or 6 <= u.tm_hour < 10)) else 1.0
# frais = ((in - cache)*r_in + cache*r_cr + out*r_out)/1e6 * facteur(ts)
```

Puis, par session : `off[sid]`, `plein[sid]`, et `estimated_cost_usd` — imprimer le rapport
`stocke / plein` et le detail des 12 sessions les plus cheres. Un rapport global ~1,0 valide
l'estimateur ; des ecarts concentres sur les sessions longues designent des compteurs incomplets.
Ecarter du calcul les sessions commencant AVANT le debut des logs : leur reconstitution est
partielle par construction et fausse le rapport (les lister a part).

## 5. Cles et consommateurs

Comparer les valeurs de la variable du provider entre les `.env` (racine, `profiles/*/.env`,
`~/.omniroute/.env`, paquet npm) **en memoire**, et n'imprimer qu'un regroupement « fichiers
identiques / fichiers differents » — jamais la valeur, jamais un hash.

## 6. OmniRoute : trafic reel

```sql
select provider, model, count(*), sum(tokens_input), sum(tokens_output), sum(tokens_cache_read)
from usage_history group by 1,2 order by 3 desc limit 15;
select provider, coalesce(name,''), is_active, (api_key is not null and api_key <> '')
from provider_connections order by provider;   -- aucune ligne 'deepseek' => aucune route payante
```
Verifier `min(timestamp)`/`max(timestamp)` avant de conclure : l'historique peut ne couvrir
que les derniers jours.

## 7. OmniRoute : ce que le canal a REELLEMENT tente

```sql
-- 1) les combos NOMMES : un canal 'auto/<x>' n'y figure pas, c'est un canal virtuel
select name from combos order by name;

-- 2) tentatives par cle/profil (api_key_name) sur une fenetre horaire
select timestamp, status, model, provider, combo_strategy, api_key_name, tokens_input, error_code
from usage_history
where model like '%best-%' and timestamp >= '<debut ISO>' and timestamp <= '<fin ISO>'
order by timestamp;

-- 3) la CIBLE reellement visee : combo_step_id porte l'etape virtuelle
select timestamp, status, model, requested_model, provider, combo_name, combo_step_id,
       substr(coalesce(error_summary,''),1,160)
from call_logs
where timestamp >= '<debut ISO>' and timestamp <= '<fin ISO>'
order by timestamp;
```

- `call_logs.combo_step_id` est la SEULE trace de la cible d'un canal virtuel
  (`virtual-auto-smart-3-gemini` = une seule cible tentee) : la liste des candidats d'un
  `auto/<canal>` est recalculee a chaque requete et **n'est pas persistee**. Repondre par les
  tentatives tracees, jamais par la liste d'un autre jour.
- Un modele de combo se lit en deux etages : `combo_name` + `combo_step_id` (ex. `nvidia-stack` /
  `n1`, `n2`) — c'est ce qui separe une reponse SERVIE d'une cible visee et echouee.
- Les appels unitaires existent aussi en JSON sous `~/.omniroute/call_logs/<AAAA-MM-JJ>/` :
  `grep -rl "<nom-du-modele>" <dossier>` date l'incident sans requete SQL.
- `error_summary` porte le message exact a citer, et `usage_history.status` le code par tentative.
  Classes a reconnaitre : `No target in combo <X> supports tool calling; request carried N tools`
  (filtre capacite ; `diagnostics.excluded` liste les cibles ecartees avec leur `reason`),
  `all targets were skipped by pre-dispatch filters`, `Request exceeded OmniRoute's local
  rate-limit execution expiration (legacy ... maxWaitMs=...)`, `[429] quota`, `[500]`/`[504]`.
- Le modele reellement servi pour une session cron ne se lit pas dans le combo demande : cote
  Hermes, `profiles/<p>/state.db` → `sessions.model` de la session `cron_<job_id>_<horodatage>`
  (un `model_snapshot` dans `jobs.json` est fige a la creation et peut ne plus rien dire).
