# Audit de fuite de jetons (install Hermes)

Un secret a fuité (historique, export de session, collage dans le chat). Objectif : produire la **carte
des fuites** — quel jeton, où, et surtout **lesquels sont encore exploitables** — puis nettoyer sans
casser et faire tourner ce qui doit l'être.

## 1. Motif : le jeton complet, jamais l'id seul

```python
pat = re.compile(rb"\b([0-9]{8,12}):([A-Za-z0-9_-]{30,40})\b")
```

Un id de bot seul (`8801969330:`) n'est pas un secret : doc, dumps de requêtes et collages le citent
légalement. Chercher le motif complet évite des faux positifs qui noient le vrai problème.

## 2. Shortlister, puis empreinter

Ne **pas** parcourir `%LOCALAPPDATA%/hermes` récursivement en Python : `data/*/venv`,
`site-packages`, `node_modules`, `models_dev_cache.json` font expirer la cellule (> 5 min). Deux temps :

1. `search_files` / ripgrep avec `output_mode=files_only` sur le motif complet → liste courte.
   Attendu comme bruit, à ignorer : un fichier `nul` du home (`os error 1`) et les `gateway.lock`
   verrouillés par un gateway vivant (`os error 33`).
2. Python lit **ces fichiers seulement** et rend une ligne par jeton :
   `sha10(jeton complet) | id du bot | getMe | fichiers où il apparaît`.

```python
import hashlib, json, urllib.request, urllib.error
def s10(tok: bytes) -> str:            # tok = b"<id>:<secret>"
    return hashlib.sha256(tok).hexdigest()[:10]
# triage de vivacité, une requête par jeton, aucun secret imprimé
try:
    with urllib.request.urlopen("https://api.telegram.org/bot%s/getMe" % tok.decode(), timeout=15) as r:
        vivant = json.load(r)["result"]["username"]      # 200 -> exploitable
    # 401/404 -> révoqué : hors priorité de nettoyage
```

## 3. Où les fuites vivent dans une install Hermes

| Chemin | Ce qu'on y trouve |
|---|---|
| `%LOCALAPPDATA%/hermes/.hermes_history` | l'historique CLI — **y compris tout ce que l'utilisateur colle dans le chat**, avec ses numéros de ligne |
| `%LOCALAPPDATA%/hermes/pastes/*.txt` | les collages longs reçus par le chat, en clair |
| `%LOCALAPPDATA%/hermes/.env` (défaut) et `profiles/<profil>/.env` | les valeurs vivantes — c'est là qu'on découvre un jeton partagé entre deux profils |
| `data/surveillance/token.sec`, `data/*/.env` | secrets de sidecars |
| `sessions/request_dump_*.json` | dumps de requêtes : souvent l'id seul, sans le secret |
| `logs/agent.log*`, `logs/process-results/*.json` | traces d'outils |
| skills de documentation (`telegram-bot-polling/references/…`) | l'id du bot cité volontairement — faux positif attendu |

Un `.env.avant_token.<stamp>` ne contient pas forcément l'ancien jeton (c'est la config qui est
sauvegardée, pas toujours le secret) : le vérifier avant d'annoncer qu'une copie subsiste.

## 4. Nettoyer sans casser

- **Supprimer par correspondance de contenu, jamais par numéro de ligne** : `.hermes_history` grossit
  pendant la session, donc un numéro relevé dix minutes plus tôt est déjà faux.
- **Préserver les CRLF** : lire en binaire, filtrer les lignes, réécrire en binaire. `grep -v` sur un
  fichier CRLF le réécrit en LF et produit un diff de tout le fichier ; `Set-Content` PowerShell peut
  réenregistrer en UTF-16 selon la version.
- Copie horodatée avant, puis contrôle après : **zéro** occurrence du motif complet dans le fichier
  nettoyé, et l'occurrence légitime toujours présente dans le `.env` visé.
- **Nettoyer après la rotation, pas avant** : effacer l'historique pendant qu'un jeton reste valide ne
  change rien au risque.
- **Un fichier vivant se nettoie à longueur constante, jamais par suppression.** Retirer des octets décale
  tout ce qui suit, et un writer en append peut alors réécrire au mauvais offset. Dans `state.db`, les
  logs et les snapshots de cache : remplacer la valeur par un marqueur **de même longueur**. La
  suppression de lignes reste la bonne méthode pour `.hermes_history`.
- **`.hermes_history` est un fichier de BLOCS** : une ligne `# <horodatage>` puis une ligne `+<texte>`
  par ligne saisie. Supprimer le bloc entier (l'en-tête `# …` **et** ses `+…`), jamais la seule ligne
  porteuse — sinon un en-tête orphelin subsiste. L'écriture se fait par `appendFileSync` à chaque entrée :
  une réécriture du fichier est sans risque, les ajouts suivants partent au nouveau EOF.
- **Un `UPDATE` sur `messages` ne suffit pas** : l'index plein-texte garde sa propre copie. Reconstruire
  après nettoyage — `INSERT INTO messages_fts(messages_fts) VALUES('rebuild')` et idem pour
  `messages_fts_trigram` — sinon le secret reste lisible dans l'index pendant qu'un `LIKE` sur `messages`
  annonce à tort « 0 occurrence ».
- **`cache/terminal/hermes-snap-*.sh` contient les `.env` du profil en clair** : le sandbox y déverse
  l'environnement (`declare -x SIYUAN_TOKEN="…"`) avant chaque commande. Toute passe de nettoyage doit
  inclure ce répertoire, sinon la fuite survit dans un cache que personne ne pense à regarder.
- **Un message qui RECITE l'ancien secret le remet dans `.hermes_history` et dans `state.db`.** Après un
  tel collage, refaire la passe (mesurer, neutraliser, revérifier) : c'est une boucle, pas un nettoyage
  ponctuel.
- **Ne jamais dumper la section secrets d'un fichier de config** (`conf.json` → `api.token`, un `.env` →
  ses clés) : un « aperçu » en sortie d'outil atterrit dans `state.db` et recrée la fuite qu'on vient de
  fermer. Masquer par nom de champ (`apikey|token|secret|password`) et n'imprimer que longueur +
  empreinte.
- **Vérifier sans la valeur** : quand l'ancien secret n'existe plus sur disque, extraire les candidats par
  motif et comparer le **sha256 de chaque candidat** à l'empreinte relevée avant suppression. Le contrôle
  final est « aucun candidat dont l'empreinte correspond », pas « le grep ne trouve rien ».

## 5. Risque par type de jeton

| Jeton | Exploitable depuis | Contrôle |
|---|---|---|
| Telegram bot | n'importe où (API publique) | `getMe` |
| API locale (SiYuan 6806, RAG 8200, OmniRoute 20128) | la machine — ou le LAN si le bind a été élargi | `netstat -ano | findstr :6806` → `127.0.0.1:6806` = local seulement |

Même fuite, deux urgences : les jetons distants d'abord, les jetons liés à `127.0.0.1` ensuite —
mais les deux se notent dans le rapport.

## 6. Rotation d'un jeton Telegram (le secret ne passe pas par le chat)

1. L'utilisateur fait `/revoke` dans BotFather et pose le nouveau jeton dans `profiles/<profil>/.env`
   (même bot, même id, même `@username`).
2. Vérifier par **empreinte** : le nouveau `sha10` ≠ l'ancien.
3. `getMe` → 200 et le `@username` attendu.
4. Redémarrer le gateway du profil, puis lire `logs/gateway.log` (`✓ telegram connected`) et
   `gateway_state.json` (`"telegram":{"state":"connected"}`).
5. Dernier contrôle : envoyer un message au bot et le voir traité — `getMe` seul ne prouve pas que le
   polling est sain.
6. Alors seulement, nettoyer l'ancien jeton (§4).

Tant que la rotation n'est pas confirmée par l'utilisateur, ne rien nettoyer et ne pas redémarrer :
un jeton révoqué et non reposé fait échouer la livraison des jobs `deliver=telegram` du profil.

## 7. Deux profils sur un même bot

`hermes profile list` l'annonce lui-même : « Profile '<x>' shares its email credential with default:
the bot can only belong to one profile. » Un jeton de bot dupliqué dans deux `.env` fait parker le
doublon par le gateway multiplexé. Corriger en donnant son propre bot au profil, ou en retirant le
jeton de son `.env` — jamais en laissant les deux.

## 8. Un secret partagé : la rotation casse l'autre consommateur

Un même jeton peut vivre dans plusieurs endroits — `.env` du bureau **et** d'un profil, `conf.json`
d'une application locale, `token.sec` d'un sidecar. Le reposer dans un seul casse les autres
**silencieusement** : le consommateur oublié continue de démarrer, puis échoue à l'usage.

- Après la vérification `401` de l'ancien et `200` du nouveau, **contrôler chaque autre fichier qui
  portait la valeur** et nommer la casse (« le profil bureau ne peut plus écrire dans SiYuan »).
- Réparer est une **action distincte du nettoyage** et demande l'accord de l'utilisateur : un `.env` du
  bureau est hors périmètre par défaut.
- Les sauvegardes prises avant la rotation (`*.env.bak`, `conf.json.bak`, `.env.avant_token.<stamp>`)
  contiennent les anciens secrets : elles font partie de la carte des fuites et se suppriment — leur
  valeur de restauration est nulle une fois les jetons révoqués.
- Un jeton d'application locale se rotte côté application (l'app réécrit son `conf.json`), puis se
  répercute sur les `.env` qui le portaient : vérifier les deux sens avant d'annoncer la rotation finie.
