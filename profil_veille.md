# Profil Hermes `veille` — second agent (créé, non activé)

Créé le 2026-09-17 avec `hermes profile create veille --description "..."`.
**Non activé** : gateway arrêté, aucun credential, A2A toujours off.

---

## 1. Ce qui existe maintenant

| Élément | Valeur vérifiée |
|---|---|
| Répertoire | `%LOCALAPPDATA%\hermes\profiles\veille` |
| Description | « Agent veille techno continue (arXiv/HF/OpenRouter), synthèse, alertes A2A - non active » (`profile.yaml`, `description_auto: false`) |
| `.env` | **3 lignes, uniquement des commentaires** — aucune clé, aucun secret |
| `config.yaml` | frais ; **aucune** section `platform_toolsets`, **aucune** mention `a2a` |
| Skills | 58 skills bundled synchronisés (seed initial) |
| Modèle | `eco` par résolution par défaut ; le profil n'a pas de clé → repli sur l'environnement du shell (voir §3) |
| Alias | `C:\Users\searc\.local\bin\veille.bat` → `hermes -p veille ...` |
| Gateway | **stopped** (`hermes -p veille gateway status` → pas de PID) |
| Sous-dossiers | `audio_cache, backups, cron, home, hooks, image_cache, logs, memories, pairing, plans, sessions, skills, skins, SOUL.md, workspace` |

## 2. Pourquoi pas `--clone`

`hermes profile create veille --clone` aurait copié `config.yaml`, **`.env`**, `SOUL.md` et les
skills du profil `default` — c'est-à-dire les clés Telegram, DeepSeek, OmniRoute, SMTP et Vision du
bureau. Incompatible avec l'objectif d'isolation du second agent (clés de recherche dédiées).
Le profil a donc été créé **vide de credentials**, à dessein.

Variantes également écartées :

- `--clone-channels` : deux profils sur un même bot Telegram se neutralisent (un seul bot par token ;
  un gateway multiplexé met le doublon en attente). À ne pas utiliser.
- `--clone-all` : copie tout l'état, y compris ce qui n'a pas vocation à être partagé.

## 3. Étapes manuelles restantes (à faire par l'opérateur, interactif)

1. **Clés dédiées** : `veille setup` (interactif) ou édition directe de
   `profiles\veille\.env`. Ne pas recopier le `.env` du profil `default`.
   Sans clé dans ce `.env`, le profil **hérite des variables du shell** — comportement à connaître
   avant de lancer un gateway : une clé exportée globalement serait utilisée par la veille.
2. **Modèle** : viser un modèle recherche (par exemple DeepSeek pour la synthèse, un modèle
   gratuit en premier recours selon la règle « gratuits d'abord »).
3. **Personnalité** : `profiles\veille\SOUL.md` (encore le texte par défaut).
4. **Skills** : 58 bundled présents ; retirer ceux sans rapport avec la veille pour alléger le
   contexte de l'agent.
5. **Gateway** : `hermes -p veille gateway start` **uniquement** quand le rôle est décidé —
   c'est aussi le prérequis de l'activation A2A (voir `architecture_2_agents.md` §6).

## 4. Contrôles

```bash
hermes profile list            # default (stopped) / veille (stopped, alias veille) / watch (running)
hermes -p veille gateway status # attendu : pas de PID
hermes doctor                  # attendu : "2 profile(s) found"
grep -c "A2A_" "$LOCALAPPDATA/hermes/profiles/veille/.env"   # attendu : 0
netstat -ano | grep :9900      # attendu : rien
```

## 5. Non-régression observée après création

- Profil `default` : inchangé, `config.yaml` non touché.
- Profil `watch` : gateway toujours running (PID inchangé).
- 9900 : toujours muet, aucune clé `A2A_*` créée.
- `hermes doctor` : 2 profils détectés, aucun nouvel issue (les 4 issues restants sont préexistants).
- ⚠ Préexistant, non causé par cette création : `watch` partage son credential email avec
  `default` (message de `hermes profile list`).
