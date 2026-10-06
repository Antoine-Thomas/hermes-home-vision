# Bounces, opt-out et delivrabilite : profondeur

Deux questions INDEPENDANTES, a traiter separement et a ne pas confondre dans le rapport :
(1) le domaine est-il authentifie et repute correct ? (2) la liste est-elle composee d'adresses
vivantes ? Rendre la repartition par categorie de code SMTP avant toute conclusion.

---

## 1. Trier la boite en lecture seule (IMAP)

```python
m = imaplib.IMAP4_SSL("mail.<domaine>", 993, timeout=60)
m.login(user, pwd)                      # identifiants SMTP du .env ; jamais de valeur au rapport
m.select("INBOX", readonly=True)
typ, data = m.search(None, '(SINCE "<JJ-Mmm-AAAA>")')
ids = data[0].split()
# en-tetes + date d'arrivee reelle, sans marquer comme lu :
m.fetch(i, "(BODY.PEEK[HEADER.FIELDS (DATE FROM SUBJECT)] INTERNALDATE)")
```

- **`BODY.PEEK` obligatoire**, y compris pour le corps (`BODY.PEEK[]`) : un `fetch` sans PEEK pose le
  drapeau `\Seen`, la boite est modifiee et la promesse « lecture seule » est rompue.
- **L'heure d'arrivee reelle est `INTERNALDATE`** (heure locale du serveur, ex. `+0200`), pas l'en-tete
  `Date:` — un `Date: 18:14:28 +0000` est 20:14 heure de Paris. Pour un opt-out (RGPD) c'est la date de
  la demande qui compte : citer l'heure locale, et donner l'en-tete en complement si les deux different.
- **La recherche pleine texte sur « stop » / « unsubscribe » / « desinscription » ramene TOUS les
  bounces** : le pied de page de la campagne contient ces mots et les DSN citent le message d'origine.
  Discriminer par l'EXPEDITEUR, pas par le corps : un humain n'est pas un MTA (`serveur-mail@…`,
  `mailer-daemon@…`, `postmaster@…`, `no-reply@…`, `bounce@…`), et un DSN a un objet du type
  « Mail delivery failed » / « Undelivered Mail Returned to Sender ».
- Chercher aussi Junk/spam/Archive/Trash (`select` dossier par dossier, `readonly=True`) et dire
  explicitement lequel est vide.
- **Quand l'utilisateur annonce N reponses et que la mesure en trouve moins, nommer l'ecart**
  (« le 3e a identifier est X ; il n'existe pas de 4e personne ») au lieu de presenter le N-ieme comme
  trouve.
- **Une reponse avec signature pro et sans clic sur le lien de confirmation est un opt-out par
  prudence RGPD** : motif `reponse_sans_clic`, meme si l'objet dit deja « stop ».

## 2. Reconnaitre les trois formats de bounce

Le meme envoi produit des DSN de MTA differents. Ne jamais supposer un format unique ; parser dans cet
ordre et garder le premier qui rend un destinataire :

| Source | Marqueur dans le corps | Champs fiables |
|---|---|---|
| Relais sortant Postfix (o2switch/Jabatus) | « Details de l'erreur ci-dessous » | `Final-Recipient: rfc822; <addr>`, `Diagnostic-Code:`, a defaut `said:` |
| Google (DSN) | `wasn't delivered to <addr> because` | `Final-Recipient`, `Diagnostic-Code`, `Status code:` |
| Microsoft 365 (NDR) | `couldn't be delivered` | `Final-Recipient`, `Diagnostic-Code`, `Status:` |

Regexes qui tiennent les trois :

```python
rec = re.search(r"Final-Recipient:\s*rfc822;\s*<?([^<>\s]+@[^<>\s]+?)>?\s*$", txt, re.M)
for pat in (r"<([^<>]+@[^<>]+)>:\s*(?:host|Host)",
            r"wasn't delivered to ([^ ]+@[^ ]+) because",
            r"message to ([^ ]+@[^ ]+) couldn't be delivered"):
    ...
status = re.search(r"^Status:\s*([0-9.]+)", txt, re.M)
diag   = re.search(r"^Diagnostic-Code:\s*(.*(?:\n\s+.*)*)", txt, re.M)   # sinon  said: ...
```

Categoriser sur le CODE SMTP, jamais sur le texte :

| Categorie | Codes / motifs |
|---|---|
| adresse inexistante | 5.1.1, 5.1.3, 5.1.6, 5.1.10, 5.0.0 (« does not exist », « no such user », « user no longer on system », « RecipientNotFound ») |
| domaine introuvable | 5.4.4 « host or domain name not found » |
| boite pleine | 5.2.2 « out of storage », « overquota » |
| relais refuse | 5.7.1 « Relay access denied » |
| acces refuse Exchange | 5.4.1 « Access denied » (aka.ms/EXOSmtpErrors) |
| connexion impossible | 4.4.1 (connection refused / timed out) — souvent temporaire, a requalifier |
| reputation / auth | 5.7.x « blocked », « spam », « policy » — **si et seulement si le texte le nomme** |

Un bounce = une ligne `email,date_demande,raison,source` dans `bounce_<AAAAMMJJ>.csv`, la raison portant
le code et le texte d'origine (tronque). Compter les adresses DISTINCTES et verifier qu'elles figurent
dans la liste d'envoi : un journal d'envoi peut afficher « N/N envoyes, 0 echec » parce qu'il ne trace
que le hand-off SMTP, le rejet arrivant apres.

## 3. Prouver l'authentification avec le verdict du DESTINATAIRE

Un DSN renvoye contient le message d'origine en piece jointe (`message/rfc822` ou
`text/rfc822-headers`) **avec les en-tetes ajoutes par le serveur qui a recu** :

```
ARC-Authentication-Results: i=1; mx.google.com; dkim=pass header.i=@<domaine> header.s=default;
  spf=pass (google.com: domain of <from> designates <ip> as permitted sender) smtp.mailfrom=<from>;
  dmarc=pass (p=NONE sp=NONE dis=NONE) header.from=<domaine>
Authentication-Results: mx.microsoft.com 1; spf=pass (sender IP is <ip>) smtp.mailfrom=<domaine>;
  dkim=pass (signature was verified) header.d=<domaine>; dmarc=pass action=none header.from=<domaine>
```

- Extraire `DKIM-Signature` (`d=`, `s=`) du message d'origine et verifier que le selecteur signe est
  celui publie en DNS : un `s=` absent de la zone explique des echecs DKIM.
- SPF/DKIM/DMARC `pass` chez les deux plus gros fournisseurs = **hypothese d'authentification REFUTEE**.
  Le rapport dit ce qui est refute, nomme la cause mesuree (ici : la liste), et ne propose aucune
  modification DNS « quand meme ».
- Verifier l'IP de sortie REELLE, pas celle du serveur de connexion : la chaine `Received:` du DSN
  montre le relais final (`from smtp.<hebergeur> … by smtp-2.<hebergeur>`) et
  `Received-SPF: Pass … client-ip=<ip>`. Un SPF reposant sur un `include:` prestataire se developpe par
  un TXT (`nslookup -type=TXT spf.<hebergeur>`) pour confirmer que ce /24 est couvert.

## 4. DNS : les 4 verifications, et le piege des blacklists

```bash
nslookup -type=TXT <domaine>          # SPF
nslookup -type=TXT _dmarc.<domaine>   # DMARC
nslookup -type=MX <domaine>           # MX
nslookup -type=A mail.<domaine>       # serveur de connexion
for s in default mail o2switch dkim s1 selector1; do nslookup -type=TXT $s._domainkey.<domaine>; done
```

- Enumerer plusieurs selecteurs DKIM : beaucoup de domaines n'utilisent pas `mail`. Si plusieurs
  repondent, c'est celui du `DKIM-Signature` observe qui fait foi.
- `p=none` avec `rua=mailto:rua@dmarc.<prestataire>` (Brevo, Mailgun) est une configuration normale en
  surveillance : ne pas la presenter comme une erreur, mais dire qu'aucun rejet n'est demande.
- **Piege DNSBL : depuis un resolveur public, Spamhaus/CBL repondent `127.255.255.254`**
  (« query refused », resolveur non enregistre) — ce n'est PAS une inscription. Les codes d'inscription
  sont `127.0.0.2` a `127.0.0.11`. Ne jamais ecrire « IP blacklistee » sur un `127.255.255.x` : dire
  « non concluant depuis ce poste » et renvoyer vers un checker navigateur (mxtoolbox) si l'utilisateur
  veut la confirmation.

## 5. Qualite de la liste : tester les domaines en masse

`scripts/verif_domaines_doh.py --csv <contacts.csv>` (DNS-over-HTTPS Google, MX puis A, 24 workers,
aucune dependance) : quelques centaines de domaines en quelques secondes.

- **`Status=3` (NXDOMAIN) ET `Status=2` (SERVFAIL : NS morts, zone cassee, lame delegation) rendent
  tous les deux le domaine non delivrable.** Un filtre `status == 3` seul rate les zones cassees :
  classer sur `not MX and not A`, et conserver le status pour le rapport.
- **Signal d'adresses fabriquees par motif** : masse de `contact@<domaine>` (souvent plus de la moitie
  de la liste), domaines qui ne resolvent pas, placeholders (`jean.dupont@…`, `info@anniedupont.com`),
  artefacts de scraping (nom de fichier image pris pour une adresse, ex. `…@2x.<hash>.avif`). Le
  rapport les nomme : c'est la preuve que le probleme est la source.
- **Les boites generiques (`contact@`, `bonjour@`, `info@`, `hello@`) resolvent** : les garder dans la
  liste nettoyee en les signalant dans une colonne `AVERTISSEMENT`, jamais les exclure en silence
  (pour une relance au ton personnel, l'arbitrage appartient a l'utilisateur).
- Livrer deux fichiers : `contacts_..._nettoye.csv` (retenues + colonne `AVERTISSEMENT`) et
  `contacts_..._a_valider.csv` (exclues + colonne `MOTIF`, une cause par jeton, concatenees par `|`).
  Controler l'integrite du nettoye avant de l'annoncer : 0 doublon, 0 domaine non resolvable, 0 adresse
  deja en opt-out/bounce.

## 6. Fichiers de suppression et fail-safe du script d'envoi

```
optout.csv              email,date_demande,motif,source
bounce_<AAAAMMJJ>.csv   email,date_demande,raison,source
```

- Le script d'envoi charge `optout.csv` (**obligatoire**) puis TOUS les `bounce_*.csv` (`glob`), filtre
  apres la fusion/dedoublonnage, imprime le compte (optout / bounce / total uniques / contacts
  retires) et **refuse de demarrer si `optout.csv` manque** — code de sortie non nul AVANT toute
  connexion SMTP.
- Refuser aussi `--test-email` vers une adresse exclue : un test vers un opt-out est deja un echec de
  conformite.
- **Verifier le fail-safe pour de vrai** : renommer `optout.csv`, lancer `--dry-run`, constater le code
  de sortie et l'absence de connexion SMTP, restaurer le fichier.
- Le `--dry-run` doit afficher le compte d'exclusions : c'est la preuve que le filtre est branche, et
  l'ecart `N -> M` se lit immediatement.
- Lire les CSV d'exclusion en `utf-8-sig` (un export tableur porte un BOM qui casse l'en-tete `email`),
  valider la syntaxe, et normaliser en minuscules avant comparaison.
- Backup horodate du script avant edition, nom cite au rapport.

## 7. Format de restitution

```
Bounces ................ N  (x % de l'envoi) — N adresses distinctes, toutes presentes dans la liste
                              d'envoi (le journal d'envoi ne trace que le hand-off)
  domaine introuvable .. n1      relais refuse ........ n2
  adresse inexistante .. n2      acces refuse 5.4.1 ... n4
  boite pleine ......... n3      SPF/DKIM/DMARC ....... 0
Authentification ....... verdicts recus (dkim= / spf= / dmarc=) par fournisseur
Liste .................. domaines non resolvables, placeholders, tel-comme-adresse
desinscriptions ........ email | date (heure locale) | motif | source
exclusions actives ..... optout n + bounce n -> contacts N -> M
```
