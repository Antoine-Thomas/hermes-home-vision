# Topologie d'un combo et réordonnancement

## Un combo n'a pas autant de résilience que de cibles

OmniRoute élimine les cibles par **fournisseur**, pas par modèle. Dès qu'une cible rend un 503,
le routeur marque le provider épuisé et **saute toutes ses autres cibles dans la même requête** :

```
Provider openai connection <id> error (503) — marking for skip on remaining targets
Skipping openai/nvidia/nemotron-3.5-lightning-30b-a3b — provider openai marked exhausted this request
```

Conséquence : un combo dont plusieurs membres partagent le même `providerId` s'effondre d'un seul
coup. Mesure : un combo `eco` à 3 cibles dont 2 pointent `providerId: openai` (proxy NIM) vaut en
pratique **un seul fournisseur** — un 503 NIM retire les deux cibles NIM, et il ne reste que la
cible gemini, elle-même morte.

Règle de diagnostic : après lecture du combo, **grouper les cibles par `providerId`**, pas compter
les entrées. Un combo « à 3 cibles » dont les cibles vivantes partagent un provider n'a aucun
failover. Ne jamais présenter le nombre de membres comme un niveau de fiabilité.

## Le plancher de latence vient des cibles mortes en tête

Une cible qui pend ne rend pas une erreur rapide : elle consomme le délai du limiteur local
(`requestQueue.maxWaitMs`, 15 000 ms par défaut) puis rend un 504, **et seulement ensuite** le combo
passe à la suivante. Trace attendue :

```
Trying model 1/3: gemini/gemini-3-flash-preview
⏰ [RATE-LIMIT] gemini:<id>:<modele> — limiter-managed execution expired after 15s
[504]: Request exceeded OmniRoute's local rate-limit execution expiration ... for gemini/...
Model gemini/... failed, trying next
```

Donc la latence d'un combo ≈ (nombre de cibles mortes placées avant la première cible saine) × 15 s.
Un combo qui répond `200` mais en ~17 s à chaque appel a typiquement une cible morte en position 1.
**Réordonner corrige ce plancher de latence, pas la fiabilité** : si les cibles saines partagent un
provider qui sature, le combo échouera toujours. Ne pas annoncer une réparation complète après un
simple réordonnancement — mesurer les deux (latence ET taux de succès).

## Plafond de contexte : il suit la PREMIÈRE cible

Le log écrit `Combo context limit: <N> (source=target)` à chaque tentative. Réordonner un combo peut
donc changer son plafond effectif : mettre une cible 128 K en tête fait passer le combo de
1 048 576 à 128 000. À vérifier avant de réordonner un combo utilisé par des sessions longues.

## Recette de réordonnancement (vérifiée)

1. `GET /api/combos` (Bearer `OMNIROUTE_API_KEY` du `.env` du home) → isoler le combo par `name`.
2. **Backup** du JSON complet du combo dans `data/omniroute/backups/<combo>_avant_reordonnancement_<AAAAMMJJ>.json`.
   Vérifier qu'il contient bien `models` (ordre d'origine), `strategy` et `config` : c'est la
   restauration par simple `PUT` du fichier.
3. **Garde-fou AVANT écriture** : asserter que l'ordre courant des `models[].model` est exactement
   l'ordre attendu et que le nombre de cibles est celui prévu ; refuser d'écrire sinon. Un
   réordonnancement appliqué sur un combo déjà dérivé part du mauvais état.
4. `PUT /api/combos/<id>` avec le corps complet `{name, models, strategy, config}` — `config` repris
   à l'identique de la lecture (ne pas la régénérer).
5. **Renuméroter les `id` d'entrée sur la nouvelle position** (`<combo>-NN-<provider>-<modele>`,
   `/` remplacés par `-`). Un id dont le `NN` ne correspond plus à l'index peut être re-trié par
   `NN` ailleurs et **annuler silencieusement le réordonnancement**.
6. **Relire** (`GET /api/combos`) et prouver : `updatedAt` changé, nouvel ordre, `config` inchangée.

## Validation

- Appeler le combo **par son nom** (`{"model":"<combo>"}`), 3 fois **espacées de ~30 s**, et lire
  le champ `model` de la réponse = quelle cible a réellement servi (pas ce qu'on a demandé).
- Confirmer la tête de combo dans `app.log` : la trace `Trying model 1/N: <modele>` doit nommer la
  cible voulue.
- **Vos propres sondes fabriquent la saturation que vous diagnostiquez.** Un appel isolé sur une
  cible NIM peut rendre `200` en ~1 s alors que la même cible rend `503` en rafale juste après.
  Espacer les essais, et ne jamais conclure « combo cassé » ni « combo réparé » sur une rafale.
- Un résultat mitigé (2 succès sur 3, ou 3 sur 6) est un résultat à **rapporter tel quel** : il
  indique que le correctif a atteint son plafond, pas qu'il a échoué.
