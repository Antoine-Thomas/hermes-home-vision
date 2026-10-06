# Triage des reponses et des bounces apres une campagne (boite IMAP de l'hebergeur)

Le passage qui suit l'envoi : separer les VRAIES reponses humaines (opt-out) des rapports de
non-remise, classer les bounces, et rendre les deux listes. Complement de
`sender-domain-preflight.md` (qui traite le domaine expediteur) : ici on ne parle que du contenu de
la boite.

## 1. Relever la boite en lecture seule

`imaplib.IMAP4_SSL("mail.<domaine>", 993)` avec le compte d'envoi (`REENG_SMTP_USER` /
`REENG_SMTP_PASSWORD`), sans jamais ecrire (pas de `STORE`, pas de `\Seen` pose).

- `select(dossier, readonly=True)` et **verifier `typ == "OK"` apres CHAQUE select** : un select
  rate laisse la connexion en etat AUTH (`command SEARCH illegal in state AUTH`) et toutes les
  recherches suivantes echouent — ce qui se lit a tort comme « rien recu ».
- Balayer `INBOX` **et** `INBOX.Junk`, `INBOX.spam`, `INBOX.Archive`, `INBOX.Trash` (noms bruts de
  `LIST`, cf. skill `email-suite` pour les dossiers UTF-7).
- Critere de date en mois anglais abrege (`'(SINCE "29-Sep-2026")'`) ; tout critere contenant un
  espace part **cite** (`'(SUBJECT "stop")'`), sinon le serveur refuse la recherche entiere.
- Les bounces du relais de l'hebergeur (Postfix/o2switch : expediteur `serveur-mail@smtp-*.jabatus.fr`,
  objet generique du type « Impossible d'envoyer l'email ») ne ressemblent en rien a un bounce Gmail :
  filtrer sur l'expediteur du relais, jamais sur `mailer-daemon@`.

## 2. Identifier les opt-out : par OBJET, jamais par corps

Un bounce **cite le message d'origine**, dont le texte contient le vocabulaire d'opt-out de la
campagne : une recherche `BODY "stop"` / `BODY "unsubscribe"` remonte donc *tous* les bounces et noie
les vraies reponses. `SUBJECT "stop"` + filtrage des expediteurs automatiques donne la liste juste —
puis lire le corps de chaque candidat (un opt-out reel peut avoir l'objet « stop » et un corps vide).

Une ligne par retrait, format `email,date_demande,motif,source` :

| motif | ce qu'on a vu |
|---|---|
| `stop_explicite` | le corps demande l'arret (parfois un seul mot) |
| `unsubscribe` | demande explicite de desinscription |
| `reponse_sans_clic` | reponse a l'objet d'opt-out dont le corps ne porte que la signature de l'expediteur |

- **Une reponse sans clic « OUI » reste une demande de retrait** : traiter en opt-out, par prudence
  RGPD, tout ce qui manifeste une opposition, meme mal formulee (signature seule, corps vide, objet
  d'opt-out). Le silence ne vaut jamais consentement : ne jamais presenter une non-reponse comme un
  accord, ni dans le rapport ni dans un fichier.
- Ecrire ces adresses dans le fichier d'opt-out du **dossier de campagne** (jamais dans les listes de
  contacts), les ajouter au jeu d'exclusion du script d'envoi, et verifier que le script **refuse de
  demarrer** quand ce fichier manque.
- **Horodater l'arrivee par `INTERNALDATE`, pas par l'en-tete `Date:`.** L'en-tete `Date` est ecrit par
  le client de l'expediteur, souvent en UTC : un opt-out dont l'en-tete dit 18:23 est arrive a 20:23
  heure de Paris, et le fichier d'opt-out doit porter l'heure de la BOITE (le fuseau du serveur), pas
  celle du client. Relever `INTERNALDATE` avec le `FETCH`, en plus de l'adresse et de l'objet.
- Quand la boite contient moins (ou plus) d'arrets explicites que le nombre annonce dans la demande,
  rendre le compte MESURE et nommer l'adresse qui explique l'ecart — jamais s'aligner en silence sur
  le chiffre attendu.

## 4. Jeu d'exclusion du script d'envoi (opt-out, exclusions de qualite, bounces)

Trois fichiers au meme format (`email,date_demande,motif,source`), charges au demarrage et fondus en
union dedupliquee — la colonne lue est `email`, les trois autres sont documentaires et servent de
justification devant un client, un hebergeur ou la CNIL :

| fichier | contenu | obligatoire |
|---|---|---|
| `optout.csv` | stop explicite / unsubscribe / reponse sans clic | OUI (fail-safe) |
| `exclusions_manuelles.csv` | placeholders, telephones, adresses scrapees | non |
| `bounce_<date>.csv` | echecs d'acheminement (tous les `bounce_*.csv` du dossier) | non |

- Le fichier de bounces se genere depuis le parse des NDR, **dedoublonne par email** (une adresse peut
  porter plusieurs bounces), avec la raison = code SMTP d'origine, non retouche.
- Un chargeur robuste n'abandonne pas tout le fichier pour une ligne invalide : il ignore l'email en
  le signalant (`[!] <fichier> : email ignore (syntaxe invalide)`). Les trois sources sont lues
  separement, PUIS l'union est calculee — c'est ce qui permet d'afficher un decompte par fichier.
- **Tester le fail-safe pour de vrai, pas par relecture** : `mv optout.csv optout.csv.test`, lancer
  `--dry-run`, attendre le code de sortie 2 et le message d'arret, puis `mv` de retour. Le meme filet
  doit refuser un `--test-email` sur une adresse exclue.
- Apres chaque modification du chargeur, `py_compile` puis `--dry-run` : decompte par fichier (pour
  reperer un fichier non lu) et coherence entre total d'exclusions uniques et contacts retires.
- Backup horodate du script avant de toucher ce chargeur, cite dans le rapport — et si l'edition est
  faite en plusieurs passes, dire lequel des backups correspond a quel etat au lieu de laisser croire
  qu'il couvre la derniere modification.

## 3. Extraire les bounces par la partie `message/delivery-status`

Le texte libre n'est pas exploitable (chaque relais le redige differemment). Le destinataire et la
cause sont dans la partie `message/delivery-status` :

```
Final-Recipient: rfc822; <adresse>
Action: failed
Status: 5.4.4
Diagnostic-Code: X-Postfix; Host or domain name not found ...
```

Decoder le message entier (`raw.decode(errors="replace").replace("\r", "")`) et retenir
`Final-Recipient`, `Status` et `Diagnostic-Code`. Le bloc texte « Details de l'erreur ci-dessous » des
relais maison sert de secours, jamais de source.

| Code / libelle | Lecture | Action |
|---|---|---|
| `5.4.4 host/domain name not found` | le domaine du destinataire ne resout pas | adresse fabriquee, retirer |
| `5.1.1 / 5.1.10 / 5.0.0 / 5.1.6` adresse inconnue | boite inexistante | retirer |
| `5.2.2 out of storage` | boite pleine | transitoire, retenter ou flaguer |
| `5.7.1 relay access denied` | leur serveur refuse le relais | retirer |
| `5.4.1 access denied` (Exchange) | refus cote destinataire | retirer |
| `4.4.1 connection refused / timeout` | transitoire, l'adresse peut etre valide | NE PAS retirer, retenter |
| `spf=`/`dkim=`/`dmarc=fail`, blacklist citee | probleme d'expediteur | voir `sender-domain-preflight.md` §5 |

- **Le `sent` du journal n'est pas une remise.** Le script consigne le succes a la remise au relais ;
  les rejets arrivent ensuite, dans la boite. Un taux de bounce se MESURE dans la boite (nombre de NDR
  / nombre d'envois reels) et se recoupe avec la liste d'envoi, adresse par adresse — un journal a
  « 0 echec » et une boite a 11 % de rejets ne se contredisent pas, ils decrivent deux instants.
- **Un lot qui ne nomme ni SPF/DKIM/DMARC ni blocage de reputation accuse la LISTE, pas le domaine
  expediteur.** Dire la cause mesuree meme si la demande partait d'une autre hypothese, et regarder
  comment la liste a ete construite : des domaines entiers en `5.4.4` trahissent des adresses generees
  par motif (`contact@<domaine>.fr`) jamais verifiees.
- Garder les deux listes DISTINCTES dans le rapport (opt-out d'un cote, adresses en echec de l'autre) :
  les fusionner dans un seul fichier fait perdre la distinction entre « ne plus jamais ecrire » et
  « cette adresse n'existe pas ».
