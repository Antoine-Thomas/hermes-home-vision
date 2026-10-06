<!-- Extrait de hermes-operations/SKILL.md, lignes 1010-1097 (compression A.3 du 2026-10-06) — contenu verbatim. -->

## Verification

```bash
hermes gateway status   # expect PID + Scheduled Task Hermes_Gateway
hermes gateway list     # all profiles at once (default + watch) -> ✓/✗ per profile
 hermes status          # model/provider sanity
cat "$LOCALAPPDATA/hermes/channel_directory.json"  # which telegram chats are authorized
```

**Rapport de vérification (passe en lecture seule)** : quand la demande est « colle-moi les sorties
de <commandes> », livrer les sorties brutes dans l'ordre demandé — pas de résumé, pas d'artefact de
contrôle, pas de commit pour cette partie. Commenter uniquement les écarts par rapport à l'attendu,
et requalifier ce qui est **préexistant** (vulnérabilités npm du doctor, tâche planifiée désactivée)
au lieu de le présenter comme une régression de la session. Quand la passe découvre un **service mort** (port muet, tâche sans prochaine exécution), ne pas se contenter de le signaler : trancher « encore utile ou vestige » en interrogeant le **consommateur** — jamais un grep de config — puis livrer des options numérotées avec une recommandation, et attendre la décision avant toute action. Recette : `references/local-service-triage.md`.

**Un audit d'installation** (confronter le parc au README de référence) se livre dans
`docs/RAPPORT_AUDIT_<AAAAMMJJ>.md` avec la structure attendue : résumé exécutif de 3-5 lignes,
tableaux « élément | attendu | réel | écart », versions et dérive, optimisations priorisées par
impact/effort, résultats des contrôles de sécurité, actions prioritaires, et une section finale
« points à trancher » (les questions à poser avant toute action). Le rapport se montre **section par
section** au fur et à mesure, et se termine par l'envoi en pièce jointe sur Telegram.

**Compter les taches attendues contre la REALITE du multiplexage avant d'annoncer des manquantes.**
Un README qui liste N taches (dont `Hermes_Gateway_watch` / `_veille`) decrit un parc a gateways
separes ; avec `multiplex_profiles: true` ces taches n'ont pas lieu d'etre et leur absence n'est PAS
un ecart. Le controle qui tranche est `hermes gateway list`, pas la liste du README. Et
`scripts/creer_tache_gateway.ps1` **refuse** de creer une tache inexistante sans `-TemplateTask` ET
`-VbsPath` — sous multiplexage il n'existe pas de VBS par profil, donc « recreer les taches
manquantes » n'est pas un correctif applicable : le correctif est de mettre a jour le README. Un
`-DryRun` sur une tache absente doit montrer cette erreur, pas un diff plausible.

**Cette liste de taches vit en TROIS endroits, et n'en corriger qu'un recree la derive.** Sous
multiplexage : `README.md` (§ Installation : « N taches », la variante manuelle, la table des scripts),
`docs/ARCHITECTURE_HERMES.md` (le tableau des taches planifiees, qui porte encore les taches par profil
et les vestiges) et `docs/scripts/bootstrap.ps1` (le generateur — ses listes `$generateurs` /
`$recreables` **creent encore** une tache gateway par profil, donc rejouent le conflit de pollers au
premier redeploiement). Decompte reel : **12 taches** (1 gateway multiplexe + healthcheck + 10
recreables), la ou un parc a gateways separes en comptait 14. Quand la demande ne porte que sur le
README, le dire et proposer l'alignement des deux autres — un README « honnete » que le bootstrap
contredit reste faux.

**Un changement machine qui ne touche AUCUN fichier du depot se versionne dans le tableau des taches de
`docs/ARCHITECTURE_HERMES.md`.** Supprimer ou desactiver une tache planifiee ne produit par nature
aucun `git diff` : la seule trace durable est la ligne du tableau (avec la raison — vestige, doublon,
code de sortie — et son etat) mise a jour puis commitee. Sans ca, le depot reste faux et le prochain
audit re-signale une tache « manquante » volontairement retiree. Un commit par action
(`chore(tasks): supprime la tache vestige <nom>` / `chore(tasks): desactive la tache stale <nom>`),
avec la verification dans le meme tour (`Get-ScheduledTask -TaskName <nom>` -> 0 resultat, ou
`State = Disabled`) : la desactivation se fait par `Disable-ScheduledTask`, jamais `Unregister-`, quand
la tache est un doublon fonctionnel d'une autre.

**Une consigne de nettoyage qui melange des fichiers precis et une regle de retention (« supprime
agent.log.1 et process-results, garde les 7 derniers jours ») se tranche en LISTANT les candidats,
jamais en choisissant en silence une des deux regles.** Mesurer l'age reel
(`find <dir> -type f -mtime +N`) et presenter la liste AVANT de supprimer : si les fichiers nommes
sont DANS la fenetre de retention, le dire (« agent.log.1 a 4 jours ; tout process-results est < 7
jours ») et demander le perimetre. La suppression est irreversible et c'est l'operateur qui a demande
les deux regles a la fois.

**Un plan ou un brief fourni de l'extérieur se MESURE avant d'être exécuté.** Convertir chaque
affirmation factuelle du brief en contrôle d'assertion et l'exécuter d'abord : compteurs réels
(`git rev-list --count`, `du -sh`), listes de fichiers calculées (`comm` des `git ls-files`),
remplacement d'un état supposé par l'état mesuré (`git status`, `git tag -l`), existence réelle du
dépôt distant (`gh api repos/<owner>/<nom>` → 404 = à créer). Les chiffres du brief deviennent les
critères de vérification, et chaque écart se dit dans le même tour : un brief qui annonce « un seul
fichier contient le secret » ou « le dépôt existe » oriente vers une action partielle ou impossible.
Les gates explicites demandés par l'opérateur (« attends ma validation avant X ») se respectent à la
lettre : exécuter la phase préparatoire, s'arrêter à la phase nommée, et rapporter ce qui bloque.

**Une provenance annoncée se MESURE avant d'être reprise : « c'est un skill Hermes », « c'est une
instance externe », « c'est un service » sont des hypothèses, pas des prémisses.** Une correction de
l'opérateur qui nomme la nature d'un composant se vérifie comme n'importe quelle affirmation de brief :
chercher le handler de la commande citée (`grep -rn 'CommandDef("<nom>"' hermes-agent/hermes_cli/`,
`grep -rl '^name: <nom>$' --include=SKILL.md skills/ profiles/*/skills/`), puis chercher le script ou le
processus qui traite réellement l'entrée (`grep -rn '"/<nom>"'`, `Get-CimInstance Win32_Process`). Un nom
de commande cité dans une doc de skill ne prouve pas une implémentation : un skill de documentation peut
lister `/com` et `/video` sans les implémenter, `hermes_cli/commands.py` donne `/com` = alias de
`/commands`, et les vraies commandes de capture sont les skills `photo` et `record`. Construire une
mission sur la provenance annoncée coûte le tour entier (tester `/com` comme une prise de vue alors que
c'est un index de commandes) : mesurer d'abord, puis nommer la nature réelle du composant dans le même
tour que le résultat.

**Chantier explicitement reporté à une session dédiée** : ne pas le relancer depuis une session
multi-chantiers, ne pas en rejouer les tests. Relever seulement son état — `git status` sur
`hermes-agent` (propre, aucun diff = patch annulé, pas de patch à moitié appliqué), emplacement des
sauvegardes pré-patch — et l'écrire dans le plan du dépôt. Le contexte frais fait partie de la
procédure : une tentative de patch upstream échouée sur du code frais se rejoue à l'identique.

