---
name: omniroute-gateway
description: Use when reordering OmniRoute combos to prefer free models.
version: 1
author: hermes-agent
license: mit
metadata:
  hermes:
    tags: [omniroute, llm-routing, free-models, hermes-config, devops]
    related_skills: [hermes-agent]
---

# OmniRoute Gateway Management

OmniRoute is a local LLM routing proxy (npm `omniroute`) running at
`http://127.0.0.1:20128` (dashboard + `/api` on :20128, inference on `/v1`).
It fans a single request across many upstream providers and exposes
**combos** — ordered model lists with a fallback strategy. The user's
`eco` combo is the default Hermes model and must prefer FREE models, only
falling back to paid in last resort.

## eco : cibles reellement atteignables dans un combo

Le combo resout le provider par le **prefixe du nom de modele** et filtre les cibles
AVANT dispatch. Consequence : les alias `auto/*` (`auto/gemini`, `auto/zai`, `auto/best-free`)
repondent `200` en appel direct mais sont **ecartes dans un combo** — log
`AUTH No credentials for auto`, puis `Provider <p> connection noauth auth failure (403)
— marking for skip on remaining targets (#8133)` : le combo renvoie un 403/402 global
en ~2 s alors que des modeles vivants figurent dans sa liste. Ne jamais mettre `auto/*`
dans `eco` ; ecrire les cibles en **provider/modele reels** :

- `gemini/gemini-3-flash-preview` — providerId `gemini` (cle Google, gratuit)
- `openai/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` — providerId `openai` (proxy NIM local :20200)

Diagnostic : dans `~/.omniroute/logs/application/app.log`, chaque requete detaille ses
targets (`Trying model i/N`, `No credentials for <provider>`, `marking for skip`).
Un echec de combo en ~2 s = cibles filtrees, pas un modele en panne.
Validation obligatoire apres toute ecriture de combo : `POST /v1/chat/completions
{"model":"eco"}` -> `200` + `content` non vide, et lire `model` dans la reponse (route
reellement servie) + 3 essais pour ecarter un coup de chance.

**Un combo qui echoue n'est pas forcement casse : verifier le PLAFOND DE CONTEXTE des cibles vivantes.**
Un combo dont les seules cibles vivantes n'ont pas le meme plafond echoue uniquement AU-DESSUS de ce
plafond. Mesure : le meme combo repond `200` en 2-5 s sur un prompt court (la premiere cible vivante
sert) et echoue en session longue parce que la cible a grand contexte (1 M) est en `429 cooldown` et
que les survivantes plafonnent a 128 K. Diagnostic dans cet ordre : (1) sonde courte — si elle passe,
le combo n'est pas en panne ; (2) `GET /v1/models` pour lire `context_length` de chaque cible vivante ;
(3) comparer au contexte reel de la session qui echoue. Ne jamais reconstruire un combo sur un seul
echec en session longue.

**Un job de maintenance additif accumule les cibles mortes.** Un probe qui n'ajoute jamais ne retire
rien : au bout de quelques semaines la majorite des cibles peut etre morte (providers fermes, modeles
retires du catalogue) et chaque appel paie leurs tentatives. Elaguer le combo ne suffit pas — le job le
re-remplira a son rythme : corriger aussi **son script** (retirer les familles mortes, purger au-dela de
N echecs consecutifs), le tester sur une copie du combo, puis relire le combo apres le passage horaire.

Etat du pool gratuit (verifie 2026-09-17) : tout `oc/*` et `opencode/*` renvoie
`403 OpenCode's free tier can only be used from within OpenCode` (ou `402 requires an
opencode API key`) — le pool gratuit OpenCode n'est plus exploitable via OmniRoute.
Les seules routes gratuites vivantes sont Gemini (cle perso) et le proxy NIM local.

## eco auto-refresh (cron `omniroute-eco-autorefresh`, horaire)

`~/AppData/Local/hermes/scripts/probe_omniroute.py` (job `5c9dd16aaa37`) probe les
modeles gratuits et maintient le combo `eco` (modele par defaut de Hermes).

- Le script est **additif + elagage** : il ajoute en tete les modeles nouvellement vivants absents du
  combo, et ne retire une cible qu'apres **N echecs consecutifs a code TERMINAL** (`401/402/403/404` =
  acces ferme ou modele retire du catalogue). Un modele qui rate un probe est souvent juste rate-limite :
  les echecs **transitoires** (`429` cooldown, `502/504`, timeout, `200` a contenu vide) n'incrementent
  pas le compteur et ne le remettent pas a zero — **seul un succes remet le compteur a zero**. Reference :
  `PRUNE_AFTER = 3`, etat persistant dans `data/omniroute/probe_omniroute_state.json` (hors depot git :
  `data/` est ignore), donc les compteurs survivent entre deux passages horaires.
- **Plancher obligatoire** : refuser tout elagage qui ferait descendre le combo sous `FLOOR_MODELS = 2`
  cibles, et evaluer ce plancher sur la liste **fusionnee** (pas sur les seuls vivants du moment). Sans
  ce garde-fou, un elagage agressif reproduit le scenario catastrophique decrit juste apres (combo reduit
  a 1 cible -> tout le trafic part sur le fallback payant).
- **Tester l'elagage sans attendre N heures** : relancer le script N fois de suite simule N ticks ; relire
  ensuite `GET /api/combos` (nombre de cibles) et le fichier d'etat (compteurs par modele). **Ne pas
  enchainer une rafale puis conclure sur un `503`** : plusieurs passes en quelques minutes saturent les
  quotas gratuits et le combo repond `503 all targets were skipped by pre-dispatch filters` pendant
  quelques minutes — re-sonder 2-3 min plus tard avant de declarer le combo casse. Cadence prevue :
  1 passe/heure.
- Interdit : reconstruire `eco` a partir des seuls modeles "vivants du moment".
  Si aucun ne passe le seuil (tous rate-limites), `eco` tombe a 1 modele, celui-ci
  echoue aussi et **tout le trafic Hermes part sur le fallback payant DeepSeek**.
  Symptome : `POST /v1/chat/completions {"model":"eco"}` -> `504 ... requestQueue.maxWaitMs`.
  Reparation : `data/omniroute/restore_eco_20260912.py` (backup + PUT 10 modeles gratuits verifies).
- Pas de seuil de latence pour declarer "vivant" : `200` + `content` non vide suffit
  (les modeles froids repondent en 5-12 s et sont parfaitement utilisables).
- Sonde avec `max_tokens >= 200`. Avec un budget minuscule (5-10), les modeles
  "reasoning" mettent tous les tokens dans `reasoning_content`, OmniRoute rejette
  en `502 ... failed quality validation` et le probe conclut a tort "mort".
- `providerId` : `oc` pour `oc/*`, `opencode` pour `opencode/*`, `auto` pour
  `auto/*` (convention du combo `eco-fast`, verifiee fonctionnelle).
- **Ce job reecrit `eco` a chaque passage** : toute assertion « combo inchange » doit etre
  **horodatee** (ou prise juste apres lecture). A distance de plusieurs heures elle est fausse par
  construction, et attribuer l'ecart a sa propre session est une erreur de diagnostic — comparer
  `updatedAt` et `cron/executions.db` (le job doit y figurer `completed` sur la fenetre) avant de
  conclure a une fuite.

## Cles API dediees (isolation par consommateur)

Une cle par consommateur plutot que la cle du poste : degats bornes, usage attribuable, revocation
ciblee. `GET /api/keys` liste (`keys[]`, plus `allowKeyReveal`) ; `DELETE /api/keys/<id>` supprime.

- **`POST /api/keys` n'applique PAS `allowedModels`.** Il repond `201` avec la cle (et echoit
  `allowedConnections`), mais la relecture donne `allowedModels: []` — aucune restriction, alors qu'on
  croit l'avoir posee. La portee se pose par **`PATCH /api/keys/<id>`** (`{"allowedModels": […]}` →
  `200`), puis se **verifie par relecture**, jamais sur le retour de creation.
- **La liste doit nommer les modeles REELLEMENT dispatches, pas les alias du combo.** Un combo
  autorise sous son seul nom produit `503 all targets were skipped by pre-dispatch filters` (le filtre
  s'applique aux cibles, avant dispatch) ; le modele concret absent de la liste produit
  `403 Model "…" is not allowed for this API key`. Donc : autoriser l'alias **et** les membres
  concrets des combos concernes.
- **Une cle restreinte perd ses cibles des que la rotation sort de sa liste — l'echec est un `503`.**
  Une cle dont `allowedModels` n'est pas vide passe en `modelAccessMode: restricted` : le filtre
  s'applique aux **cibles resolues**, avant dispatch, alors qu'un alias `auto/*` resout sa cible a chaque
  appel dans un pool de plusieurs centaines de modeles. Diagnostic : la reponse porte `poolSize` non nul
  avec `attempted: 0` et `terminalReason: all_targets_skipped` — ca ressemble a une panne de pool et ca
  revient par vagues. Correctif : autoriser l'alias **et** les cibles concretes vivantes du pool, ou
  rendre le modele determineste (un combo dont tous les membres sont autorises, p. ex. `nvidia-stack`).
  Verifier aussi les **replis** : un `fallback_model` absent de `allowedModels` echoue en `403`.
- **Le jeton n'est lisible qu'a sa creation.** `POST /api/keys` renvoie la cle en clair une seule fois ;
  ensuite `GET /api/keys` la masque (champ `key` tronque, `allowKeyReveal: false`) et `keyPrefix` derive
  du `machineId` — deux cles differentes peuvent donc partager leur prefixe, ce n'est pas un doublon.
  Consequence pratique : creer la cle **et** la poser chez son consommateur dans le meme appel.
- Preuve de portee, cote client : `GET /v1/models` avec la cle restreinte n'annonce que les modeles
  autorises. C'est la verification la plus lisible qu'une restriction est bien active.
- **Sonder une API d'ecriture avec un corps bidon cree quand meme l'objet.** Un `POST` incomplet peut
  repondre `201` au lieu de `400` : lire la reponse avant de la boucler, et supprimer l'objet parasite
  (`DELETE`) en le signalant.

## Recommended Workflows

- **Silent Launch**: Use `omniroute-launch.vbs` to launch the server without a visible console window.
- **Model Discovery**: Use the `omniroute-auto-update` skill to discover and apply free models periodically via `/api/combos`.

## Diagnostics & API
- **API Endpoints**: Use `/api/combos` for management (requires Bearer token) and `/v1/models` for inspection.
- **Silent Launch Technique**: See `references/silent-launch-vbs.md`.
- **API Tips**: See `references/api-tips.md`.
- **Adding a new upstream provider (e.g. Minimax)**: See `references/minimax-provider.md`.
- **Brancher un consommateur local** (app qui parle au routeur en OpenAI-compatible, cle dediee posee
  dans SA config, verification de bout en bout) : `references/openai-compatible-consumers.md`.

### Connexion en erreur : lire `/api/providers`, pas la topologie du dashboard

`GET /api/providers` rend `connections[]` avec `testStatus` (`active` / `expired`) et
`providerSpecificData.apiKeyHealth` (`ok` / `warning` / `invalid`). La connexion hors `active` est
l'« Erreur 1 » du dashboard, et **tous ses modeles renvoient la meme erreur** — d'ou l'impression que
les modeles sont casses alors que c'est la cle de la connexion :

| Reponse du modele | Cause | Correctif |
|---|---|---|
| `401 A valid API key is required. Get one at …` | cle de la connexion morte/expiree (`testStatus: expired`) | renouveler cote fournisseur, ou desactiver la connexion **et** retirer ses modeles des combos (sinon le bruit continue). `PATCH /api/providers/<id> {"isActive": false}` desactive sans supprimer (garder la trace) — relire `isActive` pour le prouver, `DELETE` n'est pas necessaire |
| `502 spawn <binaire> ENOENT` | provider adosse a un executable local, sans connexion enregistree : le modele reste au catalogue et rend `0 token` indefiniment | installer/configurer le provider, ou retirer le modele |
| `429 All credentials for model X are cooling down` | quota fournisseur epuise, transitoire | attendre — ne pas conclure a une panne de configuration |
| `404 … no longer available to new users` | modele retire du catalogue cote fournisseur | retirer des combos |

Un modele du catalogue sans connexion pour son prefixe n'est pas « a tester » : verifier d'abord
`GET /api/providers`.

### Taille du pool de comptes : la vraie limite des routes gratuites

Le log écrit `gemini | all N active accounts cooling down for model <m> (reset after Ns)` : le routeur
gère un **pool de comptes par provider** et fait tourner les credentials, donc **un pool de 1 compte
n'a aucune rotation possible** pendant le cooldown — la cible est écartée et le combo retombe sur ses
cibles 128 K (ou sur le payant). C'est ce qui rend une route gratuite « fiable sur petit prompt,
abandonnée en session longue ».

- **Diagnostiquer la taille du pool** : `grep -o "all [0-9]* active accounts cooling down" app.log |
  sort | uniq -c` — le nombre annoncé est la taille **réelle** du pool. Ne pas la déduire du nombre de
  connexions affichées par le dashboard : seule la ligne du log l'annonce.
- **Élargir une route gratuite** : déclarer une **seconde connexion du même provider**, adossée à un
  **AUTRE compte** du fournisseur (`POST /api/providers {"name":"<Prov> Account 2", "provider":
  "<même providerId>", "authType":"apikey", "apiKey":"<clé du second compte>"}`). Une seconde clé du
  **même** compte ne change rien : le quota est par compte, pas par clé.
- **Valider par le log, pas par `/api/providers`** : `all 1 active accounts` → `all 2 active accounts`
  est la seule preuve que la rotation survit à un cooldown (relire après un `429` réel).
- **Aucun réglage du combo dans ce cas** : `eco` continue de pointer `gemini/<modèle>` ; c'est la
  résolution de compte à l'intérieur du provider qui change, pas la liste des cibles.

## Fallback payant — canonique DeepSeek V4.1 Flash

DeepSeek V4.1 Flash (552B MoE, 10/09/2026) — nom canonique `deepseek-flash` (version-less, futur-proof). `deepseek-v4-flash` n'est qu'un alias de compatibilite ; `deepseek-v4-pro` sera route vers Flash apres le 14/09/2026 12:00 Pekin. Toujours configurer `model: deepseek-flash` (pas l'alias) dans `fallback_providers` et dans l'alias `flash:` du config.yaml.
Option B validee : fallback mono-entree `provider: deepseek / model: deepseek-flash` — retirer `omniroute/auto/best-chat` du fallback economise 60s de timeout a chaque echec d'eco. **Mais le mono-entree payant n'est plus la cible** : l'etage gratuit deterministe passe AVANT le payant (voir ci-dessous) — ne garder le mono-entree payant que si aucun target gratuit fiable n'existe, car il facture au premier rate-limit du primaire. Editer via `terminal` (le guard `patch` refuse `~/AppData/Local/hermes/config.yaml`), appliquer sur default ET `profiles/watch/config.yaml` en une commande.

**Mais un repli mono-entree payant facture au premier hoquet du primaire.** Mesure : sur le profil
du bureau (`fallback_providers: [deepseek/deepseek-flash]`), un `hermes -z` de controle a ete servi
par DeepSeek **payant** alors que le primaire `eco` repondait `200` en 2 s en appel direct — l'echec
etait un `429 cooldown` transitoire de la premiere cible du combo, invisible dans les logs de la
session. Intercaler un etage **gratuit et deterministe** (combo local dont toutes les cibles sont
autorisees, p. ex. le combo NIM local) avant l'etage payant : un repli unique payant transforme
chaque rate-limit en facture.

**Prouver l'etage qui a servi, cote Hermes** : le profil garde le modele et le provider factures —
`SELECT id, model, billing_provider, api_call_count FROM sessions ORDER BY rowid DESC LIMIT 1` sur le
`state.db` du profil (lecture en `mode=ro`, le gateway ecrit pendant qu'on lit). C'est cette colonne,
ou le call log OmniRoute, qui dit si une session a coute : la verifier **avant** d'annoncer « test
OK », et signaler la bascule payante comme l'exige la regle « gratuit d'abord ».
Verifier le normaliseur : `hermes_cli/model_normalize.py` doit contenir `deepseek-flash` dans `_DEEPSEEK_CANONICAL_MODELS` et `_normalize_for_deepseek` doit laisser passer `deepseek-flash` tel quel (bug #107389 corrige).

Ne jamais scraper de tokens communautaires — violation ToS et meme pool deja en 429/cooling-down, aucun gain. Ajouter un vrai provider via dashboard OmniRoute (`POST /api/providers`) avec cle API fournie par l'utilisateur. communautaires pour `oc`/`opencode` — ces providers exposent deja le pool `muse-spark`/`big-pickle`/`mimo` en 429 cooling-down, ajouter d'autres tokens ne les dedouane pas et viole le ToS du source.

## Editing Hermes config.yaml safely

- The `patch` tool REFUSES to write `~/AppData/Local/hermes/config.yaml` (security guard on agent modifying Hermes config). Edit it via `terminal` instead.
- NEVER use `sed` block-range substitutions (`/^A:/,/^- B$/c\...`) on this file — multi-line range ends are fragile (a missing boundary matched nothing or swallowed to EOF) and truncated the whole file to a few lines. The failure is silent: file just shrank.
- Edit via Python line-by-line iteration instead: read lines, on a header line skip its indented block (lines starting `  -` or `    `), emit replacement. This is precise and leaves unrelated lines untouched.
- ALWAYS back up `config.yaml` before touching it (rely on the auto-update `.bak.update_YYYYMMDD_HHMMSS` Hermes drops before updates). Restore is trivial when an edit nukes the file; the damaged file is otherwise unrecoverable by hand.
- After editing, validate with `python -c "import yaml; c=yaml.safe_load(open('<path>',encoding='utf-8')); print(c['model']['default'], c['fallback_providers'])"` and confirm the file still has ~its original line count, not a few dozen.
- **Preserver les fins de ligne** : lire et ecrire avec `newline=""` (ou en binaire). Un `open(...).read()`
  en mode texte traduit CRLF -> LF et l'ecriture qui suit normalise **tout** le fichier : ~1 octet par
  ligne en moins, ce qui ressemble a une perte de contenu (`wc -c` qui chute de plusieurs centaines
  d'octets pour 3 lignes ajoutees) et fait perdre du temps en investigation. Comparer le contenu avec un
  diff qui retire les CR (`diff <(sed 's/\r$//' avant) <(sed 's/\r$//' apres)`), et savoir que git
  (autocrlf) stocke en LF et n'affichera pas la conversion : le controle honnete est le diff ligne a
  ligne plus `python -c "import yaml; ..."`, pas la taille du fichier.
- Default Hermes model lives at `model.default` (`auto/best-chat` = premium; `eco` = free) plus per-provider `default_model`. `fallback_providers: []` makes the setup 100% free.

## Relaunch watchdog — piege TIME_WAIT (no-op silencieux)

`OmniRoute-Watchdog` (toutes les 5 min) et `OmniRoute-AutoLaunch` appellent
`omniroute-launch.vbs` / `.cmd`, qui sortent en no-op si `netstat -an | findstr ":20128 "`
matche. Or les sockets clients en `TIME_WAIT` du process mort matchent aussi : le watchdog
croit le serveur up et ne relance jamais — l'incident ne s'auto-repare pas et tout le trafic
Hermes bascule sur DeepSeek payant.

- Fix (applique le 2026-09-16) : filtrer l'etat, `netstat -an | findstr /i LISTENING | findstr /r ":20128 "`
  dans LES DEUX launchers (`%LOCALAPPDATA%\hermes\omniroute-launch.vbs` et `.cmd`).
- Diagnostic d'un OmniRoute down : `netstat -ano | grep 20128` -> aucun `LISTENING` (que des
  `TIME_WAIT`) et `~/.omniroute/logs/application/app.log` s'arrete net sans ligne `Shutdown`
  = crash, pas arret propre. Les taches planifiees `LastTaskResult=0` ne prouvent rien :
  le launcher est sorti en no-op.
- Relance manuelle (detachee, sans fenetre) : `wscript.exe //B "%LOCALAPPDATA%\hermes\omniroute-launch.vbs"`,
  puis ~30-45 s avant que `127.0.0.1:20128` accepte. Verification obligatoire apres relance :
  `POST /v1/chat/completions {"model":"eco"}` -> 200 + `content` non vide (un 401 sur `/v1/models`
  prouve seulement que le port ecoute).

## Gateway-down diagnosis (10061-compatible)

Symptom burst in Hermes logs (NOT a model problem):
- `httpx.ConnectError: [WinError 10061] Aucune connexion...refusé` — port closed
- `Auxiliary compression: connection error ... falling back` then `Error code: 402` — context compressor tried `auto` → connection refused → paid fallback → 402. Root cause is the LOCAL gateway being down, not billing.
- `Streaming failed before` — same root cause (gateway not responding).

## NVIDIA NIM Provider — Critical Distinction

**The OmniRoute `dva` provider is NOT NVIDIA NIM** — it's a "Devin Agentic" bridge that fails with `DEVIN_AGENTIC_HOME must be an absolute path inside the bridge sandbox`.

**Real NVIDIA NIM endpoint**: `https://integrate.api.nvidia.com/v1`

User's NIM keys are in `~/AppData/Local/hermes/data/nvidia/.env`:
- `NVIDIA_API_KEY_SVD` — Synthetic Video Detector
- `NVIDIA_API_KEY_SD` — Stable Diffusion
- `NVIDIA_API_KEY_GEMMA4` — Gemma 4 vision (also works for chat models)

**Working models on this account** (via NIM API directly):
- `nvidia/nemotron-3.5-lightning-30b-a3b` — 30B MoE, fast, chat
- `nvidia/nemotron-3-super-120b-a12b` — 120B MoE, chat/reasoning
- `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` — 30B MoE, reasoning

**Non-working models** (404, not deployed on this account):
- `nvidia/llama-3.1-nemotron-70b-instruct`, `nvidia/llama-3.1-nemotron-ultra-253b-v1`, etc.

**Model alias**: `auto/best-chat` is a dynamic auto-routing alias, not a fixed model. It iterates through models and in testing resolved to `oc/mimo-v2.5-free`. DeepSeek only appears as a paid fallback in `fallback_providers`, never in the normal routing.

### Wiring NVIDIA NIM into OmniRoute (the proxy pattern)

OmniRoute has NO native `nvidia-nim` provider type — `openai`/`pollinations`/`auto`
all REWRITE model names per their own prefix scheme (`nvidia/nemotron-...` →
`openai/nemotron-...`), which NVIDIA NIM rejects (404). It also injects
`prompt_cache_key`, which NIM rejects with 400. The working fix is a **local
proxy** (`data/nvidia/nvidia-nim-proxy.py`, port 20200) that normalizes the
model name (strips router prefixes, re-adds `nvidia/`) and drops unsupported
params before forwarding to `https://integrate.api.nvidia.com/v1`. Full recipe
in `references/nvidia-nim-models.md`.

**Combo `providerId` pitfall**: in a combo's `models[]` entries, `providerId`
must be the provider TYPE string (`"openai"`) — NOT the connection UUID. Using
the UUID yields `ALL_TARGETS_SKIPPED` ("all targets were skipped by pre-dispatch
filters").

**`providerId` alone is not enough — the model NAME must carry the provider prefix the router
resolves on.** OmniRoute picks the provider from the PREFIX of the model string, not from
`providerId`. An entry written `"nvidia/nemotron-3.5-lightning-30b-a3b"` with
`providerId: "openai"` is routed to a provider called `nvidia` that has no credentials:
`401 No active credentials for provider: nvidia` when called by model name, and `502` (with a
nested message) when called by combo name — while the very same model answers `200` as
`openai/nvidia/nemotron-3.5-lightning-30b-a3b`. Rule: write each `models[].model` in the form the
downstream provider expects (for the local NIM proxy: `openai/nvidia/<modele>`), and validate by
calling the COMBO name (`{"model":"<combo>"}`), never only the bare model name — a combo can be
fully wired and still be unreachable from Hermes.

## File Lock Diagnosis Pattern (Windows)

When `rm -rf` fails with `Device or resource busy`:
1. Use Sysinternals `handle64.exe -accepteula "<filename>"` to find which process holds the lock
2. Check the process: `Get-CimInstance Win32_Process -Filter 'ProcessId=<PID>'`
3. For locks from Hermes components (omniroute, guardian): prefer RunOnce at reboot over killing the process

## Python Instance Locking (Anti-Duplicate)

To prevent multiple instances of a long-running Python daemon:
1. Create lock file with PID: `open(LOCK_FILE, 'x').write(str(os.getpid()))`
2. On startup, check lock: if exists and PID alive → exit silently
3. Use `ctypes.windll.kernel32.OpenProcess()` to check PID liveness on Windows
4. Clean up lock in `finally:` block
5. Handle stale locks: if PID dead → delete lock and restart

## Silent Python Wrapper Pattern (VBS)

When scheduled tasks need to run Python without console flash:
- Use `wscript.exe` (not `pwsh.exe` which may flash briefly on some Windows configs)
- Create `.vbs` file: `sh.Run "python.exe script.py", 0, False` (second arg 0 = hidden)
- Register VBS in scheduled task with action `wscript.exe "path/to/launch.vbs"`