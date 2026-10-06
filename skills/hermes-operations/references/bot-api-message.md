<!-- Extrait de hermes-operations/SKILL.md, lignes 381-410 (compression A.3 du 2026-10-06) — contenu verbatim. -->

## Envoyer un message ponctuel (récap de fin de chantier) par l'API Bot

Livrable récurrent demandé en fin de chantier de maintenance : un récap Telegram (décisions prises,
chemins finaux, ce qui reste). Le gateway n'est pas nécessaire — l'API Bot suffit, et ça évite
d'attendre un tick.

```bash
ENVF="$LOCALAPPDATA/hermes/.env"
TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' "$ENVF" | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d '\r')
curl -s -X POST "https://api.telegram.org/bot$TOKEN/sendMessage" \
  --data-urlencode "chat_id=8956868107" \
  --data-urlencode "text@$LOCALAPPDATA/Temp/recap.txt"
```

- Le corps se passe **par fichier** (`--data-urlencode "text@<fichier>"`), jamais inline : un récap
  multi-lignes avec accents, `§`, guillemets et antislashs de chemins Windows se fait déchiqueter par
  le quoting bash. Écrire le texte avec `write_file`, puis appeler `curl`.
- **Sans `parse_mode`** : en Markdown/HTML le moindre `_` ou `*` d'un chemin fait échouer l'envoi
  (`can't parse entities`) et rien ne part. Le récap part en texte brut.
- **Ne jamais exposer le jeton** : le lire dans une variable au moment de l'appel, jamais l'`echo`, ni
  dans la commande montrée au chat. La preuve d'envoi à rapporter est `message_id` + `chat` + longueur.
- Limite **4096 caractères** par message : au-delà, découper en envois numérotés (« 1/2 »).
  `{"ok":true,"result":{"message_id":…}}` en retour vaut accusé de réception.
- Un récap doit se lire **seul** : décisions prises, chemins finaux livrés, état des services, et ce
  qui reste à faire côté utilisateur. S'arrêter aux chemins sans dire ce qui reste oblige à relire la
  session.
- **Un second message court est préférable à un récap faux** : si une affirmation du premier envoi se
  révèle inexacte, envoyer la rectification (elle nomme l'erreur) plutôt que de laisser le fil sur une
  version fausse.

