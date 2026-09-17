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
| Mémoire | MEMORY 2036/2100, USER 1193/1300 | MEMORY 2076/2100 (7 entrées), USER 1193/1300 — voir § 4 : fichier écrasé par l'outil mémoire puis restauré | ⚠ incident résolu |
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

## 4. Incident mémoire — survenu et résolu dans cette session

**Ce qui s'est passé.** La mise à jour de la ligne « Skills » via l'outil mémoire (`replace`) a
réécrit `MEMORY.md` en entier : les 7 sections sont devenues une seule ligne.

**Cause racine.** `tools/memory_tool_store.py` découpe les entrées sur `ENTRY_DELIMITER = "\n§\n"`.
La restructuration de la mémoire du 16/09 avait remplacé ces séparateurs `§` par des titres markdown
`##` : le store ne voyait donc plus qu'**une seule entrée** (tout le fichier), et remplacer cette
entrée unique efface le reste par construction. Aucun garde-fou n'a pu se déclencher : le fichier
« round-trip » parfaitement (1 entrée → 1 entrée), donc pas de détection de drift.

**Récupération.** Aucune sauvegarde postérieure au 16/09 (les `.bak` datent d'une génération
antérieure du format ; `hermes memory` n'expose ni historique ni sous-commande `pending`). Le
fichier a été reconstruit depuis la copie injectée dans la session — copie fidèle du contenu au
démarrage de session, et source la plus fiable disponible.

**Correction.** Contenu restauré (7 sections) **et** séparateurs `§` rétablis entre les sections :
le store voit de nouveau 7 entrées, `replace`/`remove` redeviennent chirurgicaux au lieu de
destructeurs.

**Vérification** (lecture depuis le disque, en répliquant la logique du store) : 7 entrées —
Environnement, Hermes, Second cerveau, Outils clés, Préférences, Règles transversales, Vidéo —
2076 chars ; `check_memory.ps1` → 2076/2100 et 1193/1300, « aucune mémoire saturée ».

**Écart résiduel, annoncé franchement** : 2076 chars contre 2036 avant l'incident. La mise à jour
volontaire de la ligne Skills/Profils explique +82 ; l'écart réel n'est que de +40. Une petite
différence de mise en forme (fins de ligne, lignes vides) ne peut pas être exclue : la
reconstruction est fidèle sur le fond (toutes les sections de la version courante sont présentes,
aucune entrée du fichier de démarrage ne manque) mais n'est pas certifiée identité octet à octet.

**À savoir pour la suite** : le store de la session en cours garde une vue périmée (1 entrée,
161 chars) et ne doit plus être appelé ici — un flush écraserait la restauration. Une session neuve
relit le disque. Leçon consignée dans le skill `hermes-memory` (3 puces de pièges).

## 5. Ce qui reste à faire (par l'opérateur, non fait)

1. Clés dédiées du profil `veille` (`veille setup` ou `profiles\veille\.env`) — **ne pas** recopier
   le `.env` du bureau. Attention : sans clé, le profil hérite des variables du shell.
2. Modèle du profil veille (`eco` par défaut aujourd'hui).
3. `SOUL.md` du profil veille (encore le texte par défaut).
4. Élaguer les 58 skills bundled du profil veille.
5. Décider de l'activation : `scripts\activer_a2a.ps1` (jetons + `a2a_agents`), uniquement quand le
   gateway `veille` est joignable. Retour arrière : `scripts\desactiver_a2a.ps1`.

## 6. Synthèse

1. A2A reste entièrement désactivé, conforme : plugin off, aucune clé, port 9900 muet.
2. Le document d'architecture sépare les rôles bureau/veille et fixe les règles d'isolation.
3. Le profil `veille` existe, isolé sans le moindre credential, gateway arrêté.
4. Les usages A2A réels (fédération, cross-framework, orchestration, service callable) sont
   documentés ; x402 et le cas « Claude Code en production » du brief sont écartés comme faux.
5. Aucune régression : 0.21.3, doctor stable, tâches planifiées intactes, SiYuan/RAG/backend/
   OmniRoute répondent ; la mémoire a été écrasée par l'outil mémoire puis restaurée et sécurisée,
   et le proxy NIM est à l'arrêt depuis le 13/09 (préexistant).
