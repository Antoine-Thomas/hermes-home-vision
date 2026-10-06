# Gmail IMAP — spécificités utiles au classement de masse

Complète SKILL.md ; ne re-décrit pas la procédure.

## Labels : ce qui est écrivable et ce qui ne l'est pas

| Objet | Visible en `LIST` | Écrivable (COPY/STORE) |
|---|---|---|
| Label utilisateur affiché dans IMAP | oui | oui |
| Catégories Gmail (Promotions, Réseaux sociaux, Forums, Notifications) | non | non |
| Étiquettes miroir `[Imap]/Drafts`, `[Imap]/Sent`, `[Imap]/Trash` | non (visibles via `X-GM-LABELS`) | non |

Les catégories restent **cherchables** (`UID SEARCH X-GM-RAW '"category:promotions"'`,
`label:Promotions`) : utiles pour compter et pour expliquer à l'utilisateur, mais on
ne peut pas y ranger un mail par IMAP. Si elles sont la seule cible logique d'un
thème, le dire et demander l'accord pour créer un vrai label.

Sonde utile — distinguer « catégorie active » de « label inexistant » :

```python
for q in ("category:promotions", "category:forums", "label:Forums",
          "label:SiYuan", "label:Hermes"):
    typ, dat = M.uid("search", None, "X-GM-RAW", '"%s"' % q)
    print(q, len(dat[0].split()) if typ == "OK" else "ERR")
```

Chaque dossier/label a son propre espace UID : l'UID « 1 » du label ciblé n'a rien
à voir avec l'UID du même message dans `Tous les messages`. Toujours STORE avec un
UID obtenu dans le dossier sélectionné.

## Encodage des noms de labels (UTF-7 modifié)

Rappel de la table : `&AOk-` = é, `&AO0-` = à, `&AOc-` = ç.

- Décodage (Python 3.11 : `imaplib.utf7_decode` n'existe pas) : voir
  `scripts/gmail_imap_label_inventory.py`.
- Encodage, pour écrire `+X-GM-LABELS` sans se tromper :

```python
import base64

def utf7_encode(s):
    out, buf = [], ""
    def flush():
        nonlocal buf
        if buf:
            b64 = base64.b64encode(buf.encode("utf-16-be")).decode().rstrip("=")
            out.append("&" + b64 + "-")
            buf = ""
    for ch in s:
        if ch == "&":
            flush(); out.append("&-")
        elif 0x20 <= ord(ch) <= 0x7E:
            flush(); out.append(ch)
        else:
            buf += ch
    flush()
    return "".join(out)
```

Exemples : `Reçus` → `Re&AOc-us` ; `candidatures réponses` → `candidatures r&AOk-ponses`.

## Extraction des étiquettes d'une réponse FETCH

```python
def balanced(meta, key):
    """Contenu de la parenthese ouverte juste apres `key` (ex. b'X-GM-LABELS (')."""
    pos = meta.find(key)
    if pos == -1:
        return None
    start, depth, i = pos + len(key), 1, pos + len(key)
    while i < len(meta) and depth:
        if meta[i:i + 1] == b"(":
            depth += 1
        elif meta[i:i + 1] == b")":
            depth -= 1
        i += 1
    return meta[start:i - 1].decode("utf-8", "replace")
```

Puis découper les tokens en respectant guillemets et `\` (un label peut contenir un
guillemet échappé), et décoder chaque token en UTF-7.

Un item de réponse est un tuple `(méta, littéral)` **ou** des bytes : itérer et
accumuler la méta avant de parser, ne jamais supposer `item[1]`.

## Preuves à produire dans le rapport

- Total de la boîte (`SELECT` → EXISTS) identique avant/après : prouve l'absence de
  doublon (une copie IMAP mal ciblée créerait un second message dans
  `Tous les messages`).
- `SELECT "<nom brut du label>"` → EXISTS avant/après = +volume du mapping : prouve
  que l'étiquette a bien été posée, et pas seulement que la commande a répondu `OK`.
- Relecture du message test : `UID FETCH <uid> (UID FLAGS X-GM-LABELS)`.
