<!-- Extrait de hermes-operations/SKILL.md, lignes 914-1009 (compression A.3 du 2026-10-06) — contenu verbatim. -->

## Jetons et secrets : mesurer sans divulguer

- **Aucun secret ne sort dans un retour d'outil ni dans le chat.** Pour comparer deux jetons, publier
  une **empreinte** : `sha256("id:secret")[:10]`, jeton complet, `id:` inclus. Les deux côtés de la
  comparaison doivent utiliser le même schéma — une empreinte du *secret seul* face à une empreinte du
  *jeton complet* donne « ça ne correspond pas » alors que les jetons sont identiques.
- **Quand un livrable doit NOMMER une clé sans la révéler** (rapport d'audit, inventaire d'un parc),
  la forme attendue est le masque court : 4 premiers + 4 derniers caractères + longueur
  (`KdvEa3…Fbvy (len=32)`). Jamais la valeur entière, jamais un extrait plus long — et une table de
  secrets ne liste que les **noms** de variables, jamais leurs valeurs.
- **Un identifiant de bot n'est pas un secret.** Chercher le jeton complet
  (`\b[0-9]{8,12}:[A-Za-z0-9_-]{30,40}\b`). Un grep sur `8801969330:` remonte la doc, les dumps et
  les collages qui ne citent que l'id, et fait croire à des fuites inexistantes.
- **Trier une fuite par vivacité, pas par emplacement** : `getMe` sur chaque jeton trouvé — 200 =
  exploitable maintenant, 401 = révoqué. C'est ce tri qui hiérarchise le nettoyage.
- **Un nom de fichier ne prouve rien : scanner le CONTENU des fichiers suivis.** Un fichier baptisé
  `env.pre_update.redacted` a porté un jeton de bot **en clair et vivant** pendant des semaines ; le
  filtre par nom donne des faux positifs (docs de skills parlant de jetons) et laisse passer ce qu'on
  cherche. Le contrôle qui tranche : `git grep -I -n -E '<motifs>'` sur les fichiers suivis, hit trié
  par vivacité (200 = à révoquer tout de suite, 401 = inerte).
- **Auditer l'HISTORIQUE, pas seulement HEAD.** `git ls-files` et `git grep` ne voient que l'arbre
  courant : un jeton encore vivant peut être dans trois blobs anciens (copie `.env` dé-suivie,
  `state.db` de 192 Mo, `.env.avant_*`) qui partent quand même au push. Scanner **tous** les blobs avec
  `scripts/scan_history_secrets.py <dépôt> --purge-cmds`, planifier la purge en **UNE** passe
  (`git filter-repo --force --invert-paths --path …` : une passe oubliée = une réécriture de SHA de
  plus), puis **re-vérifier avec le même scanner** — `git log -p | grep` ne prouve rien sur un blob de
  192 Mo. La liste des blobs décide, pas le fichier cité par un brief. Détail :
  `references/hermes-home-git-baseline.md` §3 ter (audit d'historique) et §6 (fusion de deux dépôts).
- **Tout secret collé dans le chat est déjà une fuite** : il est écrit en clair dans `.hermes_history`
  et dans `pastes/`. Le signaler dans le même tour avec son empreinte et sa ligne, et proposer la
  rotation — nettoyer ne suffit pas tant que le secret est valide. L'inventaire se fait **par motif,
  jamais par valeur**, et il est plus large qu'il n'y parait : dans `state.db` la valeur vit aussi dans
  `reasoning`, `reasoning_content`, `tool_calls`, `api_content` et dans les index FTS (`messages_fts`,
  `messages_fts_trigram`) — un `UPDATE` sur `content` seul la laisse dans l'index — et `state.db-wal`
  compte aussi. Le chiffrer (n lignes, n colonnes) et donner la seule preuve qui rassure l'operateur :
  `git grep -lE '<motif>'` sur les fichiers **suivis** = 0, donc le push ne l'emporte pas.
- **Un fichier vivant (`state.db`, `logs/`, `cache/terminal/hermes-snap-*.sh`) se nettoie à longueur
  constante**, pas par suppression : retirer des octets décale la suite du fichier pour un writer en
  append. Un `UPDATE` sur `messages` ne suffit pas — reconstruire `messages_fts` **et**
  `messages_fts_trigram` (`INSERT INTO … VALUES('rebuild')`), sinon le secret survit dans l'index.
- **Compter les OCCURRENCES, jamais les lignes, et jamais avec un `LIKE` sur le motif litteral.**
  `where content like '%github_pat_%'` compte aussi les lignes qui CITENT le motif — les commandes de
  l'agent, la doc du scanner, le present skill — donc le chiffre annonce est faux et surestime
  (observe : « 72 lignes concernees » pour 13 occurrences reelles, correction a faire dans le meme
  tour quand on s'en apercoit). Compter les occurrences avec une fonction SQL :
  `con.create_function('nb_occ', 1, lambda s: len(pat.findall(s)) if isinstance(s, str) else 0)` puis
  `select coalesce(sum(nb_occ(col)),0) from tbl`. Le `LIKE` ne sert que de pre-filtre de candidats.
- **Apres le masquage : `PRAGMA wal_checkpoint(TRUNCATE)`, pas `PASSIVE`.** Un checkpoint PASSIVE rend
  `(0, n, n)` — succes, toutes les pages checkpointees — et **laisse le `-wal` a sa taille** ; c'est le
  fichier de plusieurs dizaines de Mo, et `hermes doctor` le compte comme un **nouveau** probleme
  (« Large WAL file » : 5 issues au lieu des 4 preexistantes). C'est une regression auto-infligee qui
  invalide le controle de non-regression : `TRUNCATE` ramene le `-wal` a 0 et le doctor a 4.
- **Le script existe, ne pas reecrire un one-shot** :
  `python scripts/nettoyer_traces_secret.py --motif '<regex>' [--apply]` — DryRun par defaut, recherche
  par motif (jamais la valeur), sauvegarde `state.db` + `-wal` + `-shm`, masque a longueur constante,
  rebuild des deux index FTS, checkpoint TRUNCATE, vacuum, puis verification du compte exact.
- **Prouver la sante apres l'operation, pas seulement l'absence du secret** : `pragma integrity_check`
  = `ok` **et** une requete `MATCH` sur les deux index FTS (un `rebuild` qui rend « succes » ne prouve
  pas que l'index repond encore). Le test bout-en-bout le moins cher est un `session_search`, qui
  traverse l'index et rend des resultats reels.
- **Le cache du sandbox terminal recopie les `.env` du profil** en `declare -x` dans
  `cache/terminal/hermes-snap-*.sh` : à inclure dans toute passe de nettoyage.
- **Un message qui recite un ancien secret le remet dans `.hermes_history` et `state.db`** : refaire la
  passe après un tel collage. Et ne jamais dumper la section secrets d'un fichier de config
  (`conf.json` → `api.token`) : l'aperçu en sortie d'outil recrée la fuite.
- **Un secret partagé entre plusieurs fichiers casse les autres consommateurs à la rotation — et un
  consommateur n'est pas forcément un `.env`.** Après une rotation de jeton de bot, re-chercher TOUS les
  porteurs du même bot id (`.env` de profils, sidecars de scripts non-Hermes type `token.sec`, copies
  `.env.avant_rotation_*`, snapshots) et les trier par `getMe` : 200 = vivant, 401 = révoqué. Un sidecar
  resté sur le secret révoqué laisse son process **vivant mais sourd** (401 en boucle) et sa tâche
  planifiée le relance indéfiniment : le symptôme se lit à tort « le bot est connecté mais /X ne répond
  plus ». Nommer chaque casse dans le même tour ; la réparer est une action distincte, soumise à
  l'accord de l'utilisateur.
- **Un dépôt git du home est une surface de fuite de plus, pas un rangement.** Il se crée avec un
  scan pré-commit par empreinte et une liste d'exclusion explicite (jetons tiers, sessions, binaires) :
  recette et motifs dans `references/hermes-home-git-baseline.md`. Un motif oublié se rattrape
  (`git rm --cached`) tant que le commit n'est pas poussé — après, la rotation est la seule sortie.
- **Les permissions du système de fichiers font partie de la surface de fuite : un `.env` qui hérite
  d'un groupe sandbox/outil reste lisible par lui.** Cible : Système(F), Administrateurs(F), utilisateur
  courant(F), héritage coupé. Geste insensible à la locale (Windows FR affiche « Système »,
  « Administrateurs »), donc par SID : `icacls <fichier> /inheritance:r /grant:r '*S-1-5-18:(F)'
  '*S-1-5-32-544:(F)' '*S-1-5-21-<…>-1001:(F)'` ; vérifier ensuite fichier par fichier :
  `(Get-Acl <f>).Access | % { $_.IdentityReference + '|' + $_.FileSystemRights + '|' + $_.IsInherited }`.
  Sur un DOSSIER, `/T` étend l'opération aux enfants, et un déplacement INTRA-VOLUME **conserve** les
  ACEs d'origine du fichier : (re)poser l'ACL APRÈS le déplacement, jamais avant. Contrôler aussi les
  fichiers que la liste d'audit ne nommait pas : un `.env` créé APRÈS l'audit garde l'héritage et fait
  échouer le contrôle « les N .env sont propres » — c'est un gate rouge, donc pas de commit.
- **Une sauvegarde de secret (`.env.bak_*`) se DÉPLACE hors du home, elle ne se supprime pas.**
  Destination dédiée hors du dépôt (`%USERPROFILE%\<dossier>`), avec **structure miroir par profil** :
  trois `.env.bak_<horodatage>` homonymes de profils différents s'écraseraient dans un dossier plat.
  Preuve à rapporter : `sha256` avant/après sur chacun + absence de la source, puis ACL restreinte
  (point précédent).
- Carte des fuites, nettoyage (CRLF, blocs de `.hermes_history`, longueur constante, reconstruction FTS),
  vérification par empreinte quand la valeur n'existe plus, risque selon le type de jeton, séquence de
  rotation : `references/token-leak-audit.md`.

