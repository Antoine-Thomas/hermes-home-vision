---
name: cout-ia-forensics
description: "Use when auditing LLM cost or explaining a bill gap."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [cout, billing, audit, state.db, monitoring]
    category: devops
    related_skills: [omniroute-suite, hermes-operations]
---

# Forensics du cout IA — ou part l'argent, et pourquoi l'estimation ment

Auditer la depense LLM reelle, la comparer a l'estimation d'Hermes, expliquer les ecarts, et concevoir une surveillance qui ne rate rien. Pour les combos/compression OmniRoute, voir `omniroute-suite`.

## When to Use

- « Pourquoi mon estimation de cout est-elle plus basse que ma facture ? »
- Ventiler la depense par session / modele / jour / provider de facturation.
- Verifier qu'une alerte de cout (job de surveillance des sessions payantes) ne rate rien.
- Choisir un indicateur de cout qui ne depend pas de l'estimation interne (solde du provider).

## Sources (a connaitre avant toute requete)

- `%LOCALAPPDATA%\hermes\state.db` + `profiles\<profil>\state.db` : table `sessions`. **Lister les bases reellement presentes avant de conclure « j'ai tout scanne »** — un profil sans `state.db` (ou dont le `.env` n'a pas la variable du provider) ne contribue pas, et le job de surveillance peut declarer un profil a 0 $ pour cette seule raison.
- Colonnes utiles de `sessions` : `id`, `source` (cli/telegram/cron/subagent/oneshot), `created_source`, `profile_name`, `model`, `model_config`, `started_at`, `last_activity_at`, `ended_at`, `api_call_count`, `billing_provider`, `billing_base_url`, `estimated_cost_usd`, `actual_cost_usd`, `cost_status`, `cost_source`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`.
- Table `session_model_usage` (meme `state.db`) : attribution par MODELE REEL — colonnes `session_id`, `model`, `billing_provider`, `billing_base_url`, `billing_mode`, `api_call_count`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `reasoning_tokens`, `estimated_cost_usd`, `actual_cost_usd`, `cost_status`, `cost_source`, `first_seen`, `last_seen`. C'est la source de verite pour « qui a coute quoi », la ou `sessions.model` n'est que le modele FINAL/principal.
- `logs\agent.log`, `agent.log.1`, `agent.log.2` : lignes `API call #N: model=… provider=… in=… out=… total=… latency=… cache=A/B (…%) id=…`, plus `agent.turn_context: conversation turn: session=… model=… provider=… platform=…` (le premier tour revele le provider de DEMARRAGE) et `agent_runtime_helpers: Model switched in-place: X (p) -> Y (q)`. **Rotation courte** : au-dela de quelques jours, la reponse est « introuvable », pas une deduction.
- `~/.omniroute/storage.sqlite` (lecture seule) : `usage_history` (provider, model, tokens_input/output/cache_read, timestamp), `call_logs` (timestamp, model, provider, tokens_*, combo_name), `provider_connections` (quelles routes payantes existent vraiment). C'est la seule source qui dit si un agregateur a atteint un provider payant.
- `.env` de chaque profil + `~/.omniroute/.env` + le `.env` du paquet npm : pour savoir QUI detient une cle (voir regle 6).
- `state-snapshots\<date>-pre-update\config.yaml` et `backups\pre_update_*\config.yaml` : **historique du modele par defaut du profil** — c'est la preuve qu'un modele payant etait choisi par configuration et non subi par un repli.

## Regles (les erreurs qui coutent un cycle)

1. **Attribution : ne jamais comparer un total Hermes a un releve console sans verifier la date.** Hermes impute TOUT le cout d'une session a `started_at` ; la console facture le jour d'usage reel. Detecter les sessions longues par `last_activity_at` (une session ouverte des semaines est comptee sur un seul jour). Consequence : des journees « a zero » cote Hermes peuvent porter un gros montant reel, et un rapport « reel/estime » par jour est structurellement faux pour ces jours — le dire au lieu de conclure a une fuite. **Mesurer l'attribution par VARIANTES avant de citer un seul chiffre** : sur la meme periode, `started_at` dans la fenetre, `last_activity_at` dans la fenetre, l'union des deux, et « payantes seules » donnent des totaux qui n'ont rien a voir (mesure type : 17,4 / 34,5 / 34,5 / 22,1 $ pour la meme fenetre). Annoncer la variante employee, jamais « l'estimation » au singulier ; un ecart de 30 % entre deux variantes n'est pas un ecart de tarif, c'est un choix d'attribution.
10. **Un cumul de job n'est pas un montant de periode, et deux chiffres egaux ne sont pas le meme chiffre.** Le compteur d'un job de surveillance est un cumul sur TOUTE la base, sans filtre de date, filtre eventuellement par `billing_provider` : il ne peut pas etre compare tel quel a un releve de periode. Piege verifie : la facture console moins la cle etrangere (67,41 - 19,40 = 48,01) et le cumul du job (48,29) tombent a 0,3 $ l'un de l'autre SANS aucun rapport — la coincidence fait ecrire « l'estimation du job est ~48 $ » alors que le job n'a jamais produit ce nombre. Avant d'attribuer un chiffre a un composant, citer la requete exacte qui l'a produit (filtres compris) ; si le chiffre vient de l'utilisateur, le dire et le mesurer avant de le reprendre.
11. **Une explication fournie (par l'utilisateur, par une etape precedente) se MESURE avant d'entrer dans le log — et si elle ne se reproduit pas, suspecter D'ABORD sa propre formule de mesure.** Reproduire le phenomene annonce sur la population concernee ; en cas d'ecart, verifier la semantique des champs utilises avant de declarer l'explication fausse : un facteur ~0,5 annonce a ete « non reproduit » (agregat ~1,03) uniquement parce que la soustraction du cache faussait la mesure — la meme mesure, formule corrigee, a donne 0,499 sur la session citee et 0,60 en agregat, donc **confirme** la tendance. Une explication ecartee trop vite est aussi couteuse qu'une explication acceptee trop vite. Quand la mesure ne reproduit vraiment pas le phenomene, l'ecrire comme **hypothese non reproduite**, valeurs mesurees a cote (agregat, mediane, extremum) et `cause INCONNUE`. Ecrire une explication non verifiee comme une conclusion la propage a toutes les sessions suivantes ; la signaler comme telle ne coute qu'une ligne.
2. **Verifier `billing_provider` avant de ventiler par provider.** L'etiquette peut etre fausse : une session comptee `openrouter` dont les appels partent sur `api.deepseek.com` (le `model` porte un id de type `vendor/modele` mais `billing_base_url` et les lignes `API call … provider=` disent la verite). Croiser l'etiquette avec les providers reellement vus dans les logs de la session avant tout classement par provider.
3. **`actual_cost_usd` n'est jamais rempli** : le cout stocke est une ESTIMATION (`cost_status`/`cost_source` le disent), jamais reconciliee avec une facture. Le presenter comme tel, et dire « inconnu » la ou on ne peut pas savoir.
4. **Reconstituer appel par appel pour trancher un ecart de tarif** (voir `references/requetes-et-reconstitution.md`) : extraire `(ts, model, provider, in, out, cache)` des lignes `API call`, tarifer `in` au prix cache miss + `cache` au prix cache hit + `out`, appliquer les heures pleines, puis comparer **session par session** au `estimated_cost_usd` stocke. Un rapport proche de 1 valide l'estimateur ; un ecart concentre sur quelques sessions designe des compteurs incomplets, pas un tarif.
   **Avant de tarifer, etablir ce que chaque champ CONTIENT — ne jamais soustraire par reflexe.** Dans `state.db`, `input_tokens` n'inclut PAS le cache lu (champ separe) : une session dont `input_tokens` < `cache_read_tokens` le prouve, et l'entree du meme modele cote console (cache miss) doit tomber dans le meme ordre de grandeur que `input_tokens`. Soustaire le cache de l'entree (`max(0, in - cache)`) annule le miss des sessions tres cached et fabrique des ratios aberrants — mesure : ratio maximum 15,9 avant correction contre 2,5 apres, agregat 1,03 contre 0,60 sur la meme population. Regle : **un terme negatif ou un `max(0, ...)` dans une reconstitution de cout signale une semantique ou une unite fausse — corriger la formule, jamais clamper la valeur.**
5. **Ne jamais deduire un tarif unitaire d'un agregat.** Un « $/M effectif » calcule sur toute l'histoire melange des sessions aux compteurs incomplets et fabrique un tarif fantome (ex. un cache hit « a 0,007 $/M » alors que la grille dit 0,022). Le tarif se lit dans la grille, il ne se devine pas d'un total.
6. **Comparer les cles sans les exposer.** Pour savoir s'il y a une ou plusieurs cles d'un provider : lire les valeurs en memoire et n'imprimer qu'une matrice « identique / different » avec les fichiers concernes. Jamais la valeur, jamais un hash ; et un dossier dont l'activite s'arrete des mois plus tot n'est pas le consommateur recherche.
7. **Une session tres longue peut invalider sa propre estimation.** Comparer les jetons enregistres de la session au cout implique par ses propres jetons (grille, heures pleines) : un facteur 2 a 3 doit etre **signale comme une incoherence a expliquer**, pas lisse dans une moyenne.
8. **Etiqueter chaque conclusion** : etablie (preuve citee) / hypothese / inconnue — et « introuvable » quand les logs sont purges. L'utilisateur demande explicitement ce decoupage ; une conclusion ferme sur une zone sans logs se fera corriger. Corollaire : quand une conclusion d'une etape precedente est refutee par une mesure, la **RETRACTER explicitement** (le mot « retractee ») dans le rapport ET dans le log de chantier — ne pas la laisser en place comme si elle tenait, ni la reformuler en douce. Mecanique du log de chantier (elle-meme une piece a ne pas casser) :
  - backup date du log AVANT toute edition (`cp -p <log> <log>.bak.<AAAAMMJJ_HHMMSS>`) et son SHA en reference ;
  - un SHA tronque cite dans une entree de chantier identifie le fichier **a cette etape**, pas la
    version en service : pour verifier « le fichier est-il intact ? », hasher les `.bak.<horodatage>`
    voisins — l'attendu egale generalement le backup de l'etape citee, et le fichier en service a
    change depuis (etape validee ulterieurement). L'ecart n'est une regression qu'apres cette
    verification ;
  - ne JAMAIS reecrire l'entree fautive en place : ajouter un **marqueur court** en fin de la ligne concernee (renvoi vers la rectification) ET une **entree de rectification datee** en fin de fichier, qui nomme la conclusion retiree et les mesures qui la remplacent ;
  - preserver les fins de ligne : un fichier de log melange souvent CRLF (lignes ecrites par les scripts) et LF. **L'outil `patch` reecrit TOUT le fichier** dans ce cas (CRLF -> LF partout, diff integral alors que 2 lignes changent) — sur un log, editer par OCTETS (lire en binaire, remplacer la sequence exacte, ajouter les nouvelles lignes avec le terminator dominant) puis verifier : prefixe identique octet pour octet, compteurs CRLF/LF, delta = somme des blocs ajoutes ;
  - re-mesurer les valeurs citees AU MOMENT de l'ecriture : un chiffre mesure avant une edition ulterieure (taille d'un fichier qui a grossi depuis) devient un nouveau ecart a signaler dans le meme tour, pas a laisser passer ;
  - une rectification peut elle-meme etre fausse : la corriger par une NOUVELLE entree datee (« correction de ma propre rectification »), toujours en ajout seul — l'entree intermediaire reste en place pour que la chaine des corrections soit lisible ;
  - **ne jamais ecrire un horodatage de memoire ou « plausible »** : lire l'horloge au moment de l'append (`date '+%F %H:%M:%S'`). Un libelle 13:35-13:45 ecrit a 13:27:16 oblige a consommer une entree de plus pour rectifier l'heure ; l'heure est une mesure, pas une decoration.
9. **Separer « Hermes estime mal » de « trafic hors Hermes » par le NOMBRE DE REQUETES, pas par les jetons.** Un compte provider peut agreger PLUSIEURS cles : la console affiche alors plusieurs noms de cles, et Hermes n'en connait qu'une — son estimation est structurellement INCOMPLETE (pas fausse), et aucune correction de tarif ne la fera coller. Methode : comparer, sur la meme periode et le meme modele, le `sum(api_call_count)` d'Hermes au nombre de requetes de la console. Le nombre de requetes se trompe beaucoup moins que les jetons (il ne depend ni du cache ni du decoupage des tours) : un rapport de ~0,7 localise le manque du cote hors Hermes, et la fraction manquante doit correspondre aux jours sans session cote Hermes. Demander ensuite a l'utilisateur la **repartition par cle** de la console : elle nomme le consommateur (une autre cle, un autre outil) et clot l'enquete. Verdict a ecrire noir sur blanc : « le job ne voit que la cle X ; son estimation est un MINIMUM par construction » — et ne jamais presenter l'ecart comme une fuite avant cette verification. Corollaire : la reponse ne se trouve pas toujours sur la machine. Quand un fait decisif est dans une console externe (repartition par cle, solde, prix officiel), le dire et le demander au lieu de conclure a partir de ce qui est present.

## Grille et heures pleines (DeepSeek, verifiee sur la page officielle)

- `agent/usage_pricing.py` porte la grille embarquee (source et version dans le tuple d'entree). Pour DeepSeek : v4-pro `0,66` entree (cache miss) / `0,022` cache hit / `1,98` sortie par M ; flash `0,15` / `0,003` / `0,60` — **en heures creuses**.
- Heures pleines = **01:00-04:00 et 06:00-10:00 UTC, lundi-vendredi** (hors jours feries chinois) → **tarif x2**. Toute reconstitution qui ignore ce fait surestime ou sous-estime selon l'heure : convertir l'horodatage LOCAL des logs en UTC avant de decider.
- **L'estimateur applique bien le x2** (reconstitution heure-pleine vs `estimated_cost_usd` : rapport ~1,0). Ne pas conclure « le facteur manque » en lisant le seul commentaire du code — le tester par reconciliation.
- Solde du provider : `GET https://api.deepseek.com/user/balance` (Bearer) → `{is_available, balance_infos:[{currency, total_balance, granted_balance, topped_up_balance}]}`. C'est le seul indicateur qui capte TOUT le trafic de la cle, y compris hors Hermes ; en echange il est au niveau du compte (pas de la cle) et sort du perimetre local.

## Concevoir la surveillance des sessions payantes

- **Critere** : increment du cumul `estimated_cost_usd` par profil, compare au scan precedent — **independant de `started_at`**. Un filtre `started_at > dernier scan` rate une bascule payante survenue au milieu d'une session deja ouverte (le seul cas qu'on veut attraper).
- **Premier scan** (aucun etat) : balayage des 24 dernieres heures avec un message dedie (« historique 24 h »), jamais un point de depart silencieux.
- **Un seul appel de lecture par profil et par scan** (cumul, reference avant fenetre, modeles) : deux lectures successives peuvent etre incoherentes.
- **Delta negatif** (cumul purge) : reset du repere, journalise, sans alerte.
- **Profil sans repere** : baseline initialisee explicitement et journalisee, pas de saut muet.
- **Anti-spam qui ne perd rien** : l'increment bloque par l'anti-spam est REPORTE (`hausse_en_attente`) ; a l'expiration, une alerte « hausse non signalee : +X $ » le consomme et le remet a zero ; le retour a la normale ne part qu'apres, et un reset/baseline ne purge jamais le report.
- **Toujours tester sur COPIES** : script copie avec ses chemins rediriges vers un dossier de test, base de test synthetique (une copie de `state.db` est inutilement lourde), et SHA256 des fichiers de production avant/apres pour prouver la non-interference.
- **Auditer APRES COUP ce que le job a fait** (« combien d'alertes sont parties depuis 24 h ? ») : la source est `cron/executions.db` — une ligne par run avec `delivery_outcome` (`delivered` = alerte remise, `suppressed` = anti-spam, `failed`). Le dossier `cron/output/<job_id>/` est rotationne (~50 fichiers, ~13 h) et le JSON d'etat de la sonde n'est qu'un instantane : aucun des deux ne repond a « depuis 24 h ». Filtrer en Python sur le `datetime` parse (piege du filtre texte SQL : voir `hermes-stack-audit`). Script pret a l'emploi : `scripts/audit_cron_24h.py`.

## Pieges de lecture

- **Grep de codes HTTP sur les logs = faux positifs massifs** : `503`/`504` matchent des compteurs de jetons (`total=166503`). Ancrer le motif (debut de ligne + niveau ERROR, ou parser les lignes `API call`).
- **Un `%` dans un `LIKE` SQLite casse le formatage Python de la requete**. Utiliser `substr(id,1,5)='cron_'`.
- **Le meme modele peut apparaitre sous plusieurs ids** (`vendor/modele` vs `modele`) : regrouper avant de comparer deux sources, sinon la ventilation par modele se scinde.
- **Un `ended_at` NULL est frequent**, meme pour des sessions terminees en apparence : ne pas construire de duree dessus, utiliser `last_activity_at - started_at` (et le dire).
- **`hourly_usage_summary` / `daily_usage_summary` d'OmniRoute peuvent etre vides** alors que `usage_history` et `call_logs` sont pleins : interroger les tables brutes, pas les agregats.
- **Sur une base OmniRoute VIVANTE, la PREMIERE lecture de `sqlite_master` peut ne rendre qu'une
  partie du schema** (une seule table vue sur une base de 145 Mo, puis le schema complet a la
  relecture) : recouper avec `PRAGMA table_list` et relire avant de conclure qu'une table est
  absente. Un « `usage_history` introuvable » est un artefact de lecture, pas une preuve.
- **`sessions.model` = modele FINAL, pas source du cout ; les routes gratuites sont a 0,0.** `nvidia-stack`, `eco`, `free-openrouter`, `auto/*` n'ont AUCUNE regle de prix : dans `session_model_usage` elles rendent `estimated_cost_usd = 0.0` et `cost_status = 'unknown'`. Une session dont `model` vaut une route gratuite mais `estimated_cost_usd > 0` a donc brule un repli PAYANT (deepseek-flash le plus souvent) : tout rapport qui groupe par `model` final (ex. « nvidia-stack 0,63 $ ») MIS-ATTRIBUE le cout du repli a la route gratuite — verifier via le breakdown `session_model_usage` avant de conclure « la route gratuite est facturee ». Attention : `session_model_usage` a PLUSIEURS lignes par (session, modele) (clivees par base_url/mode/fenetre) — les TOTAUX se lisent dans `sessions`, l'ATTRIBUTION par modele dans `session_model_usage`.

## References

- `references/requetes-et-reconstitution.md` — requetes SQL pretes a l'emploi (ventilation, attribution par modele reel, top sessions, couverture, trafic OmniRoute, et cibles REELLEMENT tentees par un canal `auto/*`) et squelette du script de reconstitution appel par appel.
- `references/audit-chaine-surveillance.md` — ou lire ce qu'un job de surveillance a FAIT : definitions de job, `cron/executions.db` (runs + `delivery_outcome`), rotation de `cron/output/`, fichiers d'etat des sondes, profils et pool de credentials, quotas OmniRoute, etat reel des bots Telegram d'un gateway.
- `scripts/audit_cron_24h.py` — audit lecture seule des jobs cron sur une fenetre glissante (runs, alertes livrees horodatees, anomalies) : `python scripts/audit_cron_24h.py [heures] [filtre_job ...]`.
