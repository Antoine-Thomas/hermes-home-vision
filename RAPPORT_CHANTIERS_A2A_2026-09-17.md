# Rapport — préparation du 2ᵉ agent Hermes (veille) et des usages A2A

Date : 2026-09-17 · Hermes v0.21.3 (2026.9.14), upstream 97962358 · A2A **non activé**.

---

## 1. Livrables

| Chantier | Livrable | Emplacement | Commit |
|---|---|---|---|
| 1 | Architecture 2 agents | `Desktop\hermes_install\architecture_2_agents.md` | `50fc1ba` |
| 2 | Profil `veille` créé + documenté, non activé | `profiles\veille\` + `Desktop\hermes_install\profil_veille.md` | `f37a1f4` |
| 3 | Skill de veille | `skills\research\veille-2-agent\SKILL.md` (copie versionnée : `skills/veille-2-agent/`) | `c2041ab` |
| 4 | Cas d'usage A2A stratégiques | `skills\hermes-operations\SKILL.md` § « A2A — cas d'usage stratégiques » (copie versionnée : `skills/hermes-operations/`) | `e743382` |
| — | Rapport | ce fichier | — |

Copies versionnées vérifiées par `md5sum` identiques aux fichiers live.

## 2. Corrections apportées au brief transmis

Le brief venait d'une autre IA ; quatre affirmations ne résistent pas à la lecture du code du plugin.

| Affirmation | Réalité vérifiée |
|---|---|
| « La PR #14559 documente un adaptateur Bindu qui ajoute des micropaiements x402 » | **Faux.** `plugins/platforms/a2a/DESIGN.md` classe DID/Ed25519, scopes OAuth2 et x402 (#14559 bindu) sous « Deliberately out of scope (future, not this pass) ». Non implémenté, aucune mention dans le README ni le manifeste |
| « La PR #11025 documente le cas cross-framework Claude Code, working in production » | **Faux dans l'interprétation.** #11025 est une issue-source d'exigences, tracée sur 4 lignes du DESIGN.md : injection en session live, filtres de confidentialité + redaction sortante + audit, persistance hors compaction, auth localhost-default. Rien sur Claude Code |
| « `mode=best` : le meilleur score (qualité, latence) » | **Faux.** `best` = la réponse la plus longue. Le code se qualifie lui-même de « coarse » |
| « `hermes a2a` » (sous-entendu commande CLI) | N'existe pas dans 0.21.3 |

Écarté du périmètre en conséquence : tout plan de monétisation à la requête (x402) repose sur un
non-objectif assumé, pas sur un adaptateur existant.

Piège de lecture relevé et documenté : `config.yaml` contient `- a2a` ligne 717, mais sous
`known_plugin_toolsets.cli` (toolsets *connus*), pas sous `platform_toolsets.cli` (liste *active*).
Un `grep a2a` naïf laisse croire à tort que A2A est activé.

## 3. Non-régression

| Contrôle | Avant | Après | Verdict |
|---|---|---|---|
| Version | 0.21.3 · upstream 97962358 | idem | ✓ |
| `hermes doctor` | 4 issues (3× npm vulns, 1× `hermes setup`) | mêmes 4 issues, aucun nouveau | ✓ |
| Skills | 97 enabled / 7 disabled | **98** / 7 | ✓ delta intentionnel : +1 (`veille-2-agent`) |
| Mémoire | MEMORY 2036/2100, USER 1193/1300 | identique (non touchée) | ✓ |
| Tâches planifiées | check memory, desaturer memoire, Reindex RAG, serve backend, PurgeReports, HermesGateway, Hermes_Gateway, Hermes_Gateway_watch (Disabled), NVIDIA_NIM_Proxy — toutes Ready | identique | ✓ |
| Gateway | default arrêté, watch PID 22876 | identique (veille : non running, attendu) | ✓ |
| SiYuan 6806 | en écoute | 127.0.0.1:6806 LISTENING, API 200 | ✓ |
| RAG 8200 | en écoute | 127.0.0.1:8200 LISTENING, répond (404 JSON sur `/` : service vivant, pas de route racine) | ✓ |
| Backend 9119 | en écoute | 127.0.0.1:9119 LISTENING, HTTP 200 | ✓ |
| OmniRoute 20128 | en écoute | 127.0.0.1:20128 LISTENING, HTTP 307 | ✓ |
| A2A | plugin not enabled, 0 clé `A2A_*`, 9900 muet | identique | ✓ |
| `config.yaml` du profil `default` | — | non modifié | ✓ |
| ESTOP | absent | absent | ✓ |

Écarts **préexistants**, non causés par cette session :

- **Proxy NVIDIA NIM (20200) ne répond pas** : aucun listener, tâche `Hermes_NVIDIA_NIM_Proxy`
  dont le dernier run remonte au **13/09/2026 16:23** (résultat 0), sans prochaine exécution
  planifiée. Aucune action de cette session ne touche un service.
- `Hermes_Gateway_watch` est **Disabled** alors que le gateway `watch` tourne (PID 22876) : connu,
  signalé et non corrigé sans demande.
- Profil `watch` partage son credential email avec `default` (avertissement de `hermes profile list`).
- 3 rapports npm de vulnérabilités (browser tools, web workspace, WhatsApp bridge).

## 4. Ce qui reste à faire (par l'opérateur, non fait)

1. Clés dédiées du profil `veille` (`veille setup` ou `profiles\veille\.env`) — **ne pas** recopier
   le `.env` du bureau. Attention : sans clé, le profil hérite des variables du shell.
2. Modèle du profil veille (`eco` par défaut aujourd'hui).
3. `SOUL.md` du profil veille (encore le texte par défaut).
4. Élaguer les 58 skills bundled du profil veille.
5. Décider de l'activation : `scripts\activer_a2a.ps1` (jetons + `a2a_agents`), uniquement quand le
   gateway `veille` est joignable. Retour arrière : `scripts\desactiver_a2a.ps1`.

## 5. Synthèse

1. A2A reste entièrement désactivé, conforme : plugin off, aucune clé, port 9900 muet.
2. Le document d'architecture sépare les rôles bureau/veille et fixe les règles d'isolation.
3. Le profil `veille` existe, isolé sans le moindre credential, gateway arrêté.
4. Les usages A2A réels (fédération, cross-framework, orchestration, service callable) sont
   documentés ; x402 et le cas « Claude Code en production » du brief sont écartés comme faux.
5. Aucune régression : 0.21.3, doctor stable, mémoire intacte, tâches planifiées intactes,
   SiYuan/RAG/backend/OmniRoute répondent ; seul écart observé, le proxy NIM à l'arrêt depuis le 13/09.
