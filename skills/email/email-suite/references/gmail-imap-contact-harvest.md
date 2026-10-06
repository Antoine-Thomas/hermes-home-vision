# Extraction des correspondants Gmail (lecture seule, sans API)

Objectif : constituer une liste de contacts depuis une boite Gmail quand l'API
OAuth n'est plus valide. Tout se fait en lecture seule, jamais d'email envoye.

## 1. Verifier quel acces existe reellement

| Indice | Chemin | Signification |
|---|---|---|
| OAuth | `%LOCALAPPDATA%\hermes\google_token.json` + `google_client_secret.json` | API People/Gmail si le refresh marche |
| IMAP/SMTP | `.env` du profil : `EMAIL_ADDRESS`, `EMAIL_IMAP_HOST`, `EMAIL_PASSWORD` | mot de passe d'application Gmail (19 car. avec espaces) |
| Carnet local | `%USERPROFILE%\Contacts\`, `*.vcf`, `abook.sqlite` | souvent vide sur Windows |

Test OAuth : POST sur `token_uri` avec `grant_type=refresh_token`. Un
`400 invalid_grant` = jeton revoque/expire (le mode Testing expire ~7 jours) ->
l'API est inutilisable, l'IMAP reste la voie. Ne pas confondre : le champ
`expiry` du fichier ne concerne que l'access token.

## 2. Scan IMAP des destinataires (To/Cc/Bcc) — stdlib seulement

```python
M = imaplib.IMAP4_SSL(host, 993, timeout=90)
M.login(user, app_password)
M.select('"INBOX"', readonly=True)   # readonly = rien n'est marque comme lu
M.uid('search', None, 'SINCE', '28-Sep-2025')
M.uid('fetch', b"1,2,3,...", '(BODY.PEEK[HEADER.FIELDS (TO CC BCC DATE)])')
```

- `BODY.PEEK[...]` indispensable : sans PEEK, Gmail marque les messages comme lus.
- Lots de 200-250 UID par fetch ; 10 000 messages = ~3 min.
- **Nom du dossier Envoyes** : selon la langue du compte, `Sent` peut etre vide.
  Utiliser le nom EXACT renvoye par `M.list()` : `"[Gmail]/Messages envoy&AOk-s"`
  en francais (UTF-7 modifie), `"[Gmail]/Sent Mail"` en anglais. Un `Sent` vide
  est le signe d'une boite mal choisie, pas d'une absence de mail.
- Les dossiers d'etiquettes (labels) dupliquent INBOX/Envoyes : ne scanner que
  `INBOX` + le vrai dossier Envoyes pour eviter le double comptage.
- Bcc n'existe que dans les messages envoyes (Gmail le retire a la reception).

## 3. Filtrage indispensable

Exclure, sinon la liste est polluee :
- adresses propres et alias (mot de passe du compte, `searching...`, variantes `@googlemail.com`) ;
- domaines/locaux automatiques : `noreply`, `no-reply`, `donotreply`, `mailer-daemon`,
  `postmaster`, `bounce`, `notification*`, `alert*`, `lists*`, `group*`,
  `*plusgoogle.com`, `*noreply.github.com` ;
- adresses vues une seule fois (bruit/spam) — regle metier : garder >= 2 occurrences.

Enrichissements derives (a signaler a l'utilisateur, pas a presenter comme officiels) :
- FIRSTNAME/LASTNAME depuis le nom d'affichage du header, sinon depuis la forme
  `prenom.nom@` ;
- COMPANY depuis le domaine quand ce n'est pas un webmail connu (laisser vide sinon).

## 4. Controle de rendu du HTML d'email (Windows)

Chrome headless en une commande, sans dependance :

```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --no-sandbox \
  --disable-gpu --user-data-dir=".../prof1" --hide-scrollbars --window-size=680,1500 \
  --screenshot="C:/.../mail_render.png" "file:///C:/.../mail_essai.html"
```

- Un `--user-data-dir` unique par lancement : deux executions consecutives avec le
  meme profil echouent silencieusement (aucun PNG ecrit).
- `--dump-dom` peut renvoyer 0 octet dans cet environnement : ne pas s'y fier, valider
  la structure en statique (HTMLParser : balises non fermees, presence des liens,
  merge tags `{{ contact.FIRSTNAME }}` / `{{ unsubscribe }}`, viewport + media query,
  absence d'images lourdes).
- La lecture automatique d'une capture (modele vision auxiliaire) est peu fiable sur
  le detail : livrer le PNG a l'utilisateur et lui demander de valider le rendu final.
