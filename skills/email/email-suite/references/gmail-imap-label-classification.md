# Classer une boîte Gmail par labels, en IMAP pur (sans API OAuth)

Gmail expose les labels comme des dossiers IMAP et permet de les appliquer avec
`X-GM-EXT-1` (dispo si `X-GM-EXT-1` figure dans `M.capabilities`).

## 1. Inventaire honnête des cibles possibles

- `M.list()` ne renvoie QUE les labels dont « Afficher dans IMAP » est coché.
  Un label absent de `LIST` n'est pas écrivable : ni `COPY` ni `STORE` ne peuvent
  le cibler.
- Les onglets-catégories Gmail (Promotions, Réseaux sociaux, Notifications,
  Forums) sont **searchables** (`X-GM-RAW "label:Promotions"`) mais n'ont pas de
  dossier IMAP : ils ne peuvent PAS recevoir de mail via IMAP. Ne pas les
  présenter comme cibles.
- Vérifier le compte réel de chaque label via `X-GM-LABELS` sur les messages
  (fiable), pas via `label:` seul.
- Sondes `X-GM-RAW` : à lancer **après** `SELECT` (sinon
  `SEARCH illegal in state AUTH`). Les noms non ASCII doivent être passés en
  UTF-8/bytes, sinon `'ascii' codec can't encode character`.

## 2. PIÈGE MAJEUR : UID vs numéro de séquence

Dans une réponse `FETCH`, le **premier nombre est le numéro de séquence**, pas
l'UID. Un scan qui stocke ce nombre croit manipuler des UID et fabrique un
index inutilisable :

- `UID STORE <seq> ...` répond `OK` avec **zéro donnée** (UID inexistant) : le
  script croit avoir agi, rien n'a été fait. Aucune erreur n'est levée.
- Symptôme : `res` de `M.uid(...)` vaut `[None]`.
- Diagnostic : `M.uid('search', None, 'UID', '<n>')` renvoie `b''` = n'existe pas,
  alors que `M.fetch('<n>', '(UID)')` renvoie par ex. `b'384 (UID 4517)'`.

**Règle** : toujours demander `UID` explicitement dans le FETCH
(`"(UID FLAGS X-GM-LABELS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])"`) et
relire `UID (\d+)` dans la métadonnée.

## 3. Appliquer un label : `STORE +X-GM-LABELS`, jamais `COPY`

```python
M.select('"[Gmail]/Tous les messages"', readonly=False)   # UID de All Mail
M.uid('store', b'4514', '+X-GM-LABELS', '("Re&AOc-us")')  # "Reçus"
```

- `+` = ajout seul : les labels existants (`\Inbox`, `\Seen`, `\Important`) et
  les labels utilisateur déjà posés restent intacts. Pas de `-`/`FLAGS` sur
  autre chose.
- Le nom du label s'écrit en **UTF-7 modifié**, exactement comme le dossier
  (`Reçus` → `Re&AOc-us`, `réponses` → `r&AOk-ponses`). Récupérer la forme brute
  via `LIST` plutôt que la ré-encoder.
- Le label est appliqué au message ; **aucun doublon** n'est créé dans
  « Tous les messages » (vérifié : total inchangé). `COPY` vers un dossier-label
  n'est pas nécessaire pour étiqueter.
- Idempotent : rejouer le `STORE` sur un message déjà étiqueté ne change rien
  (donc le comptage d'un lot peut sembler inférieur de 1 si un test a déjà
  étiqueté un des mails).

## 4. Lots et vérification

- 250 UID par commande, `time.sleep(0.2)` entre les commandes.
- Garde-fou avant lancement : refuser tout UID qui porte déjà un label
  utilisateur, pour ne jamais écraser/dupliquer un classement existant.
- Vérification = **re-scan complet** puis comparaison UID par UID avec l'état
  d'avant : aucun UID disparu, aucun label retiré (`avant ⊆ après`), aucun
  `\Seen` ajouté, aucun `\Inbox` retiré, et chaque UID cible porte bien son
  label. Compter aussi les mails marqués `\Inbox` et les non-lus : un écart de
  ±1 est souvent un **mail arrivé pendant l'opération**, pas une perte.
- `SIZE`/`EXISTS` d'un dossier-label = nombre de mails portant ce label :
  contrôle indépendant du comptage par UID.

## 5. Pièges d'affichage (Windows/console)

- `d[0]` renvoyé par `SELECT` est une **str**, pas un int (`SELECT`/`LIST`
  renvoient des bytes mais imaplib les décode) : `int(d[0])` avant tout `%d`.
- Les noms d'expéditeurs sans adresse (From = nom affiché seul, fréquent avant
  2012 : MSN, Windows Live, newsletters) doivent être comptés à part ;
  `parseaddr` renvoie alors une adresse vide.
- Un `From` multi-lignes (pliage d'en-tête) casse un parsing ligne par ligne :
  préférer `email.message_from_bytes` sur le bloc d'en-têtes.
