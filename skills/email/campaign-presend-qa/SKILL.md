---
name: campaign-presend-qa
description: "Use when QA-ing email campaign assets before send."
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [email, campaign, qa, rendering, palette, rgpd, brevo]
---

# Campaign pre-send QA

Passage entre « les fichiers sont construits » et « on envoie » : verifier qu'un mail
HTML est aux couleurs de la marque, qu'il rend correctement, qu'il ne contient aucune
information interne, et que les listes respectent la separation consentement.

Complement (ne le duplique pas) de la redaction et de l'envoi de campagnes, qui vivent
dans les skills email/prospection de l'utilisateur.

## When to Use

- Un mail HTML de campagne vient d'etre ecrit ou corrige et doit etre verifie avant livraison.
- L'utilisateur demande de « mettre le mail aux couleurs du site » ou de retirer les
  informations internes d'un texte destine a l'exterieur.
- Il faut produire des captures desktop/mobile d'un mail ou d'une page et prouver que rien
  n'est coupe ni faux dans la palette.
- Des listes de contacts doivent etre separees ou fusionnees selon le consentement avant
  import dans un outil d'envoi.

## Regles toujours actives

- **Aucun envoi sans GO explicite** de l'utilisateur, et un test ne part qu'a lui-meme.
  Un envoi de masse ne se deduit jamais d'un « on prepare ».
- **Jamais d'adresse email ni de code de verification en clair** dans la reponse, les
  journaux ou les fichiers de travail : masquer (`ab***@gm***.com`), compter, decrire.
- **Un secret colle dans le chat est une exposition, pas une autorisation d'ecrire** : ne
  jamais recopier dans `.env` (ni dans une commande, ni dans un appel d'outil qui le
  reaffiche) le mot de passe ou le jeton apparu dans la conversation. Le signaler comme
  expose, recommander la rotation, et laisser l'utilisateur saisir la valeur lui-meme.
  Controler l'etat sans lire la valeur : n'imprimer que sa longueur sous un libelle qui ne
  ressemble pas a un secret (`reeng_pwd_chars:0`) — la redaction d'Hermes mutile une ligne du
  type `REENG_SMTP_PASSWORD=[longueur 0]` et fait croire a une valeur presente. Une longueur
  **identique** d'un tour a l'autre ne prouve pas que la valeur a change : le dire tel quel, et
  retenir comme preuve le succes de l'authentification avec la valeur en place.
- **Portes d'envoi, toujours dans cet ordre** : `--dry-run` (aucune connexion : listes,
  dedoublonnage, liens, et deja « mot de passe defini : OUI/NON »), puis `--smtp-check` (TLS +
  authentification, 0 mail), puis `--test-email <adresse de l'utilisateur>` (1 seul mail, objet
  prefixe `[TEST]`) ; l'envoi reel attend le GO. Une etape bloquee se rapporte avec la sortie
  brute de la commande et sa cause exacte, jamais presentee comme faite — et jamais contournee
  en changeant d'expediteur (le repli Gmail `EMAIL_*` enverrait depuis la mauvaise boite).
- **La commande attendue se valide contre les options REELLES du script avant le GO d'envoi.**
  Un plan fourni par l'utilisateur peut citer des options qui n'existent pas (`--rate`,
  `--exclude-optout`) : les passer fait echouer le script a l'`argparse` (exit 2, « unrecognized
  arguments ») et la campagne ne part jamais. Lire les `add_argument` du script, confronter chaque
  option du plan, et rapporter l'ecart avec la commande corrigee AVANT de continuer. Une garantie
  demandee mais absente du script (exclusion d'opt-out) ne se suppose jamais appliquee : mesurer
  l'exclusion reelle et la declarer. Prevoir aussi la porte de confirmation : un `--send` sans
  `--yes` en shell non interactif (`isatty()` faux) s'arrete avant le premier mail (exit 3) —
  l'annoncer avec la commande proposee, sinon le « lancement » ne fait rien et parait avoir echoue.
- **Un arret automatique demande se verifie dans le script, il ne se suppose pas.** Un plan
  d'envoi qui exige « STOP apres 3 erreurs SMTP consecutives » ou un plafond journalier ne
  s'appuie sur rien si le script se contente de journaliser chaque erreur et de continuer
  (docstring type « toute erreur est journalisee et n'interrompt pas la boucle »). Lire la boucle
  d'envoi AVANT de lancer : si le garde-fou manque, l'ajouter au script (backup horodate, compteur
  remis a 0 sur chaque succes, `break` + marqueur `log["aborted"]` dans le journal quand le seuil
  est atteint, cap `MAX_DAILY`, puis `py_compile` et re-`--dry-run`) plutot que d'externaliser la
  surveillance : un watchdog separe devrait tuer le process de l'exterieur, fragile en git-bash
  (PID du fils natif), donc plus couteux et moins sur. Rapporter le patch dans le rapport final
  (script sauvegarde, ce qui a ete ajoute, ce qui n'a pas bouge).
- **« Envoie-moi une copie du mail » = le mail RENDU, pas le journal.** Livrer le template avec
  ses balises de fusion resolues (+ partie `text/plain`), et l'envoyer a la seule adresse de
  l'utilisateur. Jamais le journal d'envoi ni la liste des destinataires (un journal dit qui a
  recu, pas ce que le mail raconte), et jamais un destinataire de la liste « pour montrer un
  exemple ».
- **Mesurer avant d'affirmer** : tout chiffre annonce (nombre de contacts, de skills, de
  notebooks, de liens) est mesure ; tout ecart avec le chiffre donne par l'utilisateur est
  signale dans le rapport, jamais corrige en silence.
- **Fichiers d'exclusion : charges par le script, avec fail-safe.** Les opt-out vivent dans
  `optout.csv` (`email,date_demande,motif,source`) a la racine du dossier de campagne, et le script
  d'envoi doit **refuser de demarrer** (exit 2, avant toute connexion SMTP) quand ce fichier manque :
  un fichier renomme par une sauvegarde ou une synchro fait repartir une campagne vers des opt-out,
  en silence. Les exclusions de qualite (placeholder, telephone, adresse scrapee) vont dans
  `exclusions_manuelles.csv`, les echecs d'acheminement dans `bounce_<date>.csv` — les trois sont
  charges et fondus en union dedupliquee. La separation est volontaire : un opt-out est une obligation
  legale, une exclusion manuelle une decision de qualite de liste. Procedures de blocklistage cote ESP :
  `references/brevo-consent-reengagement.md`.
- **« Exclues » n'est pas « retirees de la cible ».** Le compte de l'union des fichiers d'exclusion et
  le nombre de contacts reellement retires de la liste d'envoi ne coincident pas des qu'une adresse
  exclue ne figure dans aucune liste lue par le script. Rendre les DEUX chiffres avec l'ecart nomme,
  adresse par adresse ; un ecart non explique signale un fichier perdu ou un filtre inoperant.
- **Un nettoyage de liste ne supprime rien sans decision.** La sortie est un fichier nettoye PLUS un
  fichier `*_a_valider.csv` porte par une colonne `MOTIF` (motifs cumulables : `BOITE_GENERIQUE`,
  `DOMAINE_NON_RESOLVABLE`, `PLACEHOLDER_PROBABLE`, `TEL_COMME_ADRESSE`, `BOUNCE_*`, `OPT_OUT`).
  Les boites generiques (`contact@`, `hello@`, `info@`, `bonjour@`) se comptent et se presentent (par
  motif, par extension de domaine, avec des exemples de domaines d'accueil) avant tout retrait : sur
  une liste d'agences c'est souvent une adresse par domaine professionnel distinct, donc un
  destinataire reel, et l'utilisateur tranche — jamais de retrait d'office.
- **Joignabilite des destinataires avant d'ecrire.** Tester que le domaine de chaque adresse de la
  liste resout un MX **ou** un A (DNS-over-HTTPS, `ThreadPoolExecutor` sur les domaines uniques, pas
  sur les adresses). Un `Status 2` (SERVFAIL / zone cassee) est mort autant qu'un `Status 3`
  (NXDOMAIN) : n'ecarter que le NXDOMAIN laisse passer des zones cassees. Un domaine mort = un bounce
  garanti. Recette : `references/contact-list-hygiene.md`.
- Style attendu des mails produit : fond clair, noir/blanc + **un seul accent**, titres de
  section en petites capitales, largeur max 600 px, responsive, **aucune image sauf miniatures
  distantes demandees explicitement** (voir §2), liens explicites, personne physique en
  signature quand le texte dit « je ».
- **Un seul bouton plein** par mail : le CTA de l'action attendue. Les elements secondaires
  (video, depot de code) restent en lien ou bouton borde, jamais en second bouton plein.

## Procedure

### 1. Extraire la palette de la marque depuis le site

```bash
curl -s -A "Mozilla/5.0" -L https://<site>/ -o home.html     # lire les <link rel=stylesheet>
# telecharger les feuilles ; la feuille du theme ENFANT porte les tokens de marque :
grep -ohE "\-\-[a-z]+-[a-z0-9-]+\s*:\s*[^;}]+" theme.css | sort -u    # tokens (--sm-accent, ...)
grep -ohE "font-family:\s*[^;}]{0,80}" theme.css | sort -u             # typographies
```

- Compter la frequence des hex dans les feuilles : l'accent reel ressort, le bruit non.
- **Ne pas reprendre les couleurs par defaut du theme parent** (Astra : `#046bd2`,
  `#045cb4`, `#1e293b`, `#334155`) : presentes partout dans le CSS, ce ne sont pas des
  couleurs de marque.
- Typographies du site : garder les replis (`'Source Sans Pro', 'Segoe UI', Arial`) car la
  plupart des clients mail ne chargent pas Google Fonts.
- Tokens releves pour searching-murphy.com -> `references/searching-murphy-palette.md`.

### 2. Ecrire/corriger le HTML

**Modifier un template existant (annonce remplacee, nouveau projet, mise a jour de contenu) :**

- **Backup horodate avant toute ecriture** : `cp <f> <f>.bak_$(date +%Y%m%d_%H%M%S)`, puis `sha256sum`
  des deux fichiers — des hashes identiques prouvent que la copie est fidele, et c'est ce backup qui
  rend le `diff -u` et le rollback verifiables. Citer le nom du backup dans le rapport.
- **Editer par `patch` sur une ancre de contenu, jamais par numero de ligne.** L'utilisateur donne les
  numeros de lignes de l'etat INITIAL ; apres chaque hunk les suivants se decalent, donc une ancre de
  ligne est fausse des le deuxieme remplacement — et silencieusement. Ancrer sur un extrait unique
  (balise + libelle).
- **`write_file` refuse d'ecraser un fichier dont la derniere lecture etait paginee** (`offset`/`limit`) :
  sur un template existant, passer directement par `patch`. Repondre tout le fichier pour lever le refus
  coute un tour et reecrit des zones hors consigne.
- **Un template habille par `<style>` arrive en TEXTE BRUT sur Gmail** : Gmail supprime le bloc
  `<style>` du `<head>`, donc classes, boutons et bandeau disparaissent — un `--test-email` reussi ne
  prouve rien sur le rendu. Inliner les styles (premailer), elaguer le `<style>` residuel aux seules
  media queries / pseudo-classes, et **conserver le `!important` de la media query** (premailer le
  supprime : sans lui l'inline gagne et le responsive mobile ne s'applique plus). Recette :
  `references/css-inlining-gmail.md`.
- Ne toucher que les zones du cahier des charges et livrer le `diff -u <backup> <fichier>` brut dans le
  rapport : c'est la preuve que la video, la section depot, le pied RGPD et le lien de desabonnement
  n'ont pas bouge.
- **Consigne stylistique explicite contre « coller au style existant »** : si l'utilisateur demande un
  « lien bleu » alors que la charte du fichier colore tous les liens en teal (`#0c9f93`), ne pas trancher
  en silence — appliquer la charte du fichier (coherence) et SIGNALER l'ecart des deux consignes dans le
  rapport, en proposant le style inline cible si le bleu est vraiment voulu.

- Tables imbriquees, styles inline, `max-width: 600px`, meta viewport + `@media
  (max-width: 620px)`, aucun `<img>` — **sauf miniature distante explicitement demandee** :
  `<a href="<page cible>"><img src="https://<hote>/<miniature>.jpg" alt="..." width="504"
  style="width:100%; max-width:504px; height:auto; border:0; display:block;"></a>` avec un
  intitule au-dessus et une legende sous l'image.
- **Jamais d'`<iframe>`** (video, carte, formulaire) : les clients mail le suppriment. Une video
  se remplace par une miniature cliquable de la plateforme (`img.youtube.com/vi/<ID>/...`).
- Verifier que la miniature distante existe vraiment : un HTTP 200 ne suffit pas
  (`maxresdefault` sert un placeholder 120x90 quand la miniature HD n'existe pas). Le
  `Content-Length` d'un `curl -sI` tranche sans decoder (placeholder : ~1-2 Ko ; vraie
  `maxresdefault` : plusieurs centaines de Ko) ; les dimensions reelles restent la preuve si
  c'est ambigu. Verifier aussi que l'ID de la miniature est bien celui de la **1re video** de
  la cible annoncee (§6).
- Merge tags de l'ESP laisses en place (`{{ contact.FIRSTNAME | default:"" }}`,
  `{{ unsubscribe }}`) et **signales** : hors ESP ils ne sont pas resolus (lien de
  desabonnement inactif pendant un test manuel, c'est normal).
- Adresse postale de l'expediteur reprise des mentions legales du site, jamais inventee.

### 3. Valider la structure en statique (avant toute capture)

`HTMLParser` : aucune balise non fermee, meta viewport, max-width 600 px, media query,
presence des merge tags et de l'adresse postale, nombre de liens et de sections attendu,
nombre d'images attendu (0 par defaut, 1 miniature si demandee), 0 occurrence de `<iframe>`,
balises de fusion restantes comptees (0 sur un mail pret a partir). C'est plus fiable et plus rapide qu'un dump du DOM.

### 4. Rendre et verifier les captures (Windows, Chrome headless)

```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --no-sandbox \
  --disable-gpu --user-data-dir=".../prof1" --hide-scrollbars --window-size=680,1900 \
  --screenshot="C:/.../desktop.png" "file:///C:/.../mail.html"
```

- **Un seul lancement par appel terminal** et un `--user-data-dir` unique a chaque fois :
  deux executions consecutives avec le meme profil n'ecrivent aucun PNG.
- Le PNG peut apparaitre **quelques secondes apres** la sortie du process : `sleep 5-10`
  puis tester l'existence du fichier avant de le copier.
- La fenetre = la capture : prevoir large (`680,1900` desktop, `390,2600` mobile).
- Verifier ensuite objectivement les pixels avec `scripts/check_render_png.py` (tokens de
  marque presents, bandes sombres en haut et en bas, pixel du bas = fond de page donc rien
  n'est coupe).
- La lecture automatique d'une capture par un modele vision est peu fiable sur le detail
  (sections manquees, couleurs annoncees fausses) : livrer les PNG a l'utilisateur pour le
  jugement visuel, et s'appuyer sur le controle objectif pour le reste.

### 5. Porte « zero contenu interne » (obligatoire avant livraison)

Passer le HTML final au `grep -c` d'une **liste explicite de termes interdits** (codenames
internes, chemins de sauvegarde, prefixes d'hote, chantiers en cours, extensions des
fichiers de travail) et exiger **0 occurrence**. « Je n'en ai pas mis » n'est pas un controle.

### 6. Integrite des liens

Verifier que chaque cible existe avant de livrer (API du service ou requete HTTP) : un lien
mort dans le seul CTA rend la campagne inutilisable. Compter aussi les ancres et signaler
les repetitions volontaires (bouton qui repointe sur le meme depot).

- **Confronter le fichier a la consigne, ligne par ligne.** Une consigne « garder ce lien / ce
  libelle / cette miniature » est une specification, pas une description de l'existant :
  `grep -oE 'href="[^"]+"|src="[^"]+"'` sur le template, puis comparer chaque cible au texte
  demande. Quand le libelle dit « playlist » et que l'`href` pointe la video seule : corriger
  l'`href`, laisser libelle et miniature tels quels, et signaler l'ecart dans le rapport — ne
  jamais reecrire le libelle de l'utilisateur pour l'accorder a l'existant.
- **Cible YouTube : confirmer l'objet, pas la forme.** Un ID de playlist court n'est pas
  forcement tronque, ne pas le declarer invalide sur son apparence : lire la page (`curl -sL`
  puis `<title>`, `"playlistId"`, ou le parsing de `ytInitialData`) et comparer **titre,
  proprietaire et nombre de videos** au chiffre annonce par l'utilisateur, en verifiant l'ID de
  la 1re video. Signaler les liens de cible divergente laisses en place (ex. legende qui nomme
  une video et pointe cette video quand l'image pointe la playlist) et proposer l'alignement
  plutot que de trancher seul.
- Gabarits d'envoi : `--dry-run` puis `--smtp-check` avant tout `--test-email` (voir Regles).

### 7. Separation des listes par consentement

- Trois fichiers d'import distincts et jamais melanges : contacts confirmes (opt-in
  documente, seul importable), a verifier (adresses publiques), template si vide.
- Fichier de travail fusionne autorise **uniquement** avec une colonne de statut
  (`confirme` / `a_verifier` / `a_reconsentir`), nomme et documente comme non importable.
- Statut `a_reconsentir` = contact deja sollicite sans consentement marketing : le passage
  a `confirme` se fait par email de reengagement a double opt-in, un seul envoi, aucune
  relance des non-repondants, consentement journalise cote ESP (date/heure/IP).
- Dedoublonner casse-insensiblement entre sources, priorite confirme > a_verifier >
  a_reconsentir, et croiser avec les blacklists/opt-out avant d'ecrire.
- **Deux totaux differents dans la meme demande** (« les 393 » a qui l'on ecrit, « les 297 »
  importables) : les decomposer explicitement au lieu de repondre oui en bloc — cible d'envoi =
  toutes les listes lues par le script (y compris celles sans nom, non importables), sous-ensemble
  importable = les seules listes documentees avec consentement. Mesurer le recouvrement avec le
  fichier d'exclusion (attendu : 0) et signaler les documents-snapshots perimes qui citent un ancien
  total (« 109 exclusions » alors que le fichier en contient 13).
- Nettoyage des noms, fichier d'exclusion et invariants de split, joignabilite des domaines de
  la liste et traitement des boites generiques -> `references/contact-list-hygiene.md`.

### 8. Preflight de l'expediteur et verification de la remise

Le mail peut etre parfait et partir en spam : le domaine d'envoi se controle **avant**
l'envoi, pas apres. Recettes DNS/SMTP detaillees dans
`references/sender-domain-preflight.md`.

- Joignabilite : MX du domaine, puis TCP sur le port d'envoi (465 SSL / 587 STARTTLS ; le 25
  est souvent bloque depuis un reseau residentiel) et handshake TLS en verifiant que les SAN
  du certificat couvrent le host SMTP utilise.
- **SPF/DKIM/DMARC** : deux enregistrements TXT `v=spf1` sur le meme domaine = PermError chez
  le destinataire, donc spam, meme si l'un des deux contient le bon include. Fusionner en un
  seul, avec l'include du relais d'envoi. DKIM (selecteur) present + DMARC `p=none` = socle
  acceptable pour demarrer.
- **Confirmer une propagation annoncee, ne pas la croire** : interroger le resolveur que
  l'utilisateur cite ET le resolveur local (`nslookup -type=TXT <domaine> 8.8.8.8`), comparer la
  chaine entiere a celle qu'il a donnee, et verifier le selecteur DKIM au passage. « C'est
  propage » est une affirmation, pas une mesure.
- Verifier le formulaire cible sans cliquer : `curl -sL` sur l'URL, puis compter le `<title>`,
  le champ `id="EMAIL"`/`name="EMAIL"` et le libelle du bouton.
- Apres un envoi de test, **le code SMTP 250 ne prouve pas la remise** : relire en IMAP
  lecture seule et etablir le placement par les **labels du serveur**, pas par un balayage de
  dossiers. Sur Gmail : chercher le message dans `[Gmail]/Tous les messages`, puis
  `FETCH (X-GM-LABELS)` sur cette copie — `\Inbox` present = INBOX, `\Spam` present = spam.
  C'est la seule reponse fiable : un message archive/labelle n'apparait que dans « Tous les
  messages » et une recherche dossier par dossier rend alors un faux « pas recu » des qu'un
  `SELECT` echoue, `imaplib` laissant la connexion en etat `AUTH` (`command SEARCH illegal in
  state AUTH`). Controler `typ == "OK"` apres **chaque** `SELECT`, et n'utiliser que les noms
  de dossiers bruts renvoyes par `LIST` (`[Gmail]/Spam`, `[Gmail]/Tous les messages`, en UTF-7
  modifie — pas les libelles francais decodes). Un critere de recherche contenant un espace doit
  partir **cite** (`'SUBJECT', '"Un nouveau projet"'`) : `imaplib` n'echappe rien et le serveur
  refuse alors toute la recherche par `BAD Unknown argument <2e mot>`. Sur un serveur sans extension
  Gmail (`CAPABILITY` sans `X-GM-EXT-1`, cas cPanel/Dovecot d'un hebergeur), les labels n'existent
  pas : le placement se lit dans le **chemin du dossier** ou le message est trouve (`INBOX`,
  `INBOX.Junk`, `INBOX.Sent`...), et l'absence de labels ne doit etre rapportee ni comme
  « placement inconnu » ni comme un doute.
- Relever sur le message recu `Authentication-Results` (spf/dkim/dmarc pass), `Received-SPF` et
  `X-Spam-Status: No` : « recu » ne dit rien, ces trois en-tetes disent que la remise n'a pas
  ete penalisee — utile quand l'utilisateur signale une propagation DNS (cache SPF) en cours.
  Puis, sur le corps du message **recu** (pas le template) : texte du CTA, chaque `href`
  compare a l'URL **exacte** attendue (egalite de chaine — pas un prefixe : une URL tronquee
  passerait), lien de desabonnement + en-tete `List-Unsubscribe`, miniature en `src`, 0 balise
  de fusion restante, et presence d'une partie `text/plain` (multipart/alternative = signal
  anti-spam positif). Le repli du merge tag prenom (`Salut,` quand le prenom est vide) est
  attendu, ne pas le rapporter comme un bug.
- **Une cible corrigee se prouve par son ABSENCE** : apres avoir change un `href`, renvoyer un
  test et exiger que l'ancienne URL ne figure plus dans le corps recu. Un controle de presence
  seul passe encore quand le template portait deux occurrences de l'ancienne cible — cas type du
  bloc video (miniature + legende) corrige en deux temps.
  `scripts/check_delivery_imap.py` fait tout ce releve en une commande.
- **Un pic de bounces n'accuse pas l'authentification.** Prouver SPF/DKIM/DMARC par les en-tetes du
  DESTINATAIRE (`Authentication-Results` / `Received-SPF` embarques dans les rapports de non-remise),
  lire le code SMTP de chaque bounce avant de conclure, et ne pas croire un DNSBL interroge depuis un
  resolveur public (`127.255.255.254` = requete refusee, pas une inscription). Un lot d'echecs qui ne
  nomme ni SPF/DKIM/DMARC ni blocage de reputation accuse la LISTE des destinataires, pas le domaine :
  dire la cause mesuree meme si la demande partait d'une autre hypothese.
  Recette : `references/sender-domain-preflight.md` §5.
- **Apres l'envoi, trier la BOITE avant de conclure quoi que ce soit sur les listes.** Les vraies
  reponses se cherchent par OBJET et jamais par corps : un rapport de non-remise cite le texte de la
  campagne, donc une recherche par corps remonte tous les bounces et noie les opt-out. Rendre deux
  listes DISTINCTES — opt-out (jamais recontactes) et adresses en echec — et recouper ces dernieres
  avec la liste d'envoi : le journal a « 0 echec » et la boite a 11 % de rejets decrivent deux
  instants, pas une contradiction. Recette : `references/post-campaign-response-triage.md`.
- Un expediteur sur domaine propre (SMTP de l'hebergeur) est preferable a une boite webmail
  externe pour une campagne : SPF/DKIM/DMARC sont alignes. Compter les envois dans le journal
  du script avant d'affirmer ce qui est parti : lire `results[]` entree par entree et son champ
  `mode` (`test` = tests a soi-meme, `mass` = envois reels) ; le bloc `summary` ne decrit que la
  derniere execution et ne doit pas etre cite comme le total.
- **Le canal d'envoi se prouve, il ne s'annonce pas.** Quand l'utilisateur demande « qui envoie
  quoi », livrer les trois preuves ensemble : le script ne parle qu'a l'hote SMTP de l'hebergeur
  (aucun appel a l'API de l'ESP dans le code), le mail RECU porte `smtp.mailfrom` = l'adresse du
  domaine, une chaine `Received` de l'hebergeur et **aucun relais de l'ESP**, et le `pass`
  SPF/DKIM/DMARC est aligne sur ce domaine. Une URL de formulaire d'ESP dans le corps ne fait pas de
  l'ESP le canal d'envoi : elle ne sert qu'a recueillir le consentement.
- **Tracabilite des envois** : le journal local du script (destinataire, horodatage, statut, fichier
  source) est la trace sure, et il doit vivre dans le dossier de campagne, hors du cache purgeable.
  Une copie dans la boite « Envoyes » du serveur d'envoi n'est PAS automatique : mesure faite sur un
  hebergement cPanel/o2switch, `INBOX.Sent` existe mais contient 0 message apres plusieurs envois
  authentifies, car un serveur ne depose rien pour un envoi fait par un client SMTP externe (c'est le
  client qui copie, via un APPEND IMAP ; l'archivage cote hebergeur ou un filtre systeme Exim — acces
  root — sont les autres voies). Ne jamais promettre la copie webmail : la verifier en IMAP lecture
  seule sur ce dossier, puis proposer APPEND ou archivage si l'utilisateur la veut.

## Pieges

- Livrer une capture sans controle objectif : le modele vision peut decrire une mise en page
  inexistante ; garder le controle pixel comme verite.
- Renommer ou supprimer les merge tags de l'ESP « pour que ca marche en test » : ils doivent
  rester en place, c'est l'ESP qui les remplace a l'envoi.
- Reprendre une palette de memoire : les tokens du site sont mesurables, et une palette
  approximative se voit immediatement sur un mail produit.
- Confondre « relation existante » et « consentement » : un correspondant regulier n'est pas
  un opt-in.
- **Repli croise de mot de passe entre fournisseurs SMTP** : `pwd = NOUVEAU_SMTP_PASSWORD or
  ANCIEN_SMTP_PASSWORD` envoie le mot de passe de l'ancien compte au nouveau serveur, qui
  repond `535 Incorrect authentication data` et masque la vraie cause (mot de passe absent).
  Resoudre (hote, port, utilisateur, mot de passe) d'un bloc selon le seul hote.
- Taille de la capture comme preuve : un mail avec image distante passe de ~30 Ko a
  ~200-300 Ko quand la miniature est vraiment chargee. Un PNG qui reste petit = image non
  chargee, a diagnostiquer avant de livrer.
- Corriger en silence un libelle fourni par l'utilisateur (dire « cette video » quand il a
  ecrit « la playlist ») : garder ses mots et signaler l'ecart constate dans le rapport.
- Deux consignes contradictoires dans la meme demande (envoyer un test / n'envoyer aucun test) :
  appliquer la plus recente et le dire explicitement, jamais choisir en silence.
- Laisser le script d'envoi et son journal `*_sent.json` dans
  `%LOCALAPPDATA%\hermes\cache\scratch` : ce dossier est purge apres ~24 h d'inactivite, donc
  une campagne etalee sur plusieurs jours perd son outil et sa reprise. Copier script + journal
  dans le dossier de campagne, mettre le README a jour, et le proposer avant l'envoi reel.
  Tant que la reponse ne vient pas, rappeler ce point comme action ouverte a la fin de chaque
  rapport : un risque signale une fois puis oublie se realise a la purge.
- **Copier le script ne deplace pas son etat** : le journal (`*_sent.json`) est souvent un chemin
  en dur dans le script, donc deplacer le seul `.py` laisse la reprise dans le cache purgeable et
  rend le README faux. Procedure : copier le script, prouver que la copie est identique par
  empreinte (`sha256sum` des deux fichiers), relancer `--dry-run` **depuis le nouveau chemin**
  (les defauts doivent etre absolus pour que le script soit independant du dossier courant),
  mettre a jour dans le README le chemin du script ET la ligne `cd` des commandes, et declarer le
  chemin REEL du journal. Repointer le journal est une decision de l'utilisateur : le proposer,
  car changer ce chemin fait repartir la reprise de zero. Quand la reponse vient, le changement se
  fait en trois endroits (docstring de l'option, constante nommee a cote des autres chemins, defaut
  `add_argument`) et se prouve **au runtime**, pas par relecture : intercepter
  `ArgumentParser.add_argument` pour lire le defaut effectif pendant un `main()` en `--dry-run`,
  verifier que le fichier du journal existe a ce chemin, puis `py_compile`. Migrer l'etat existant
  par copie, avec preuve d'egalite (`sha256sum` des deux fichiers + comptage des entrees relues).
  L'ancienne copie du script reste alors en place avec l'ancien chemin : la **signaler comme
  divergence** — un doublon qui garde l'ancien chemin est un piege si on le relance par reflexe — et
  proposer de le supprimer ou de le synchroniser, sans le faire d'office.
- Rapporter une demande a moitie satisfaite sans le dire : quand une porte est bloquee
  (identifiant absent), livrer la sortie brute de la commande, ce qui a ete verifie autrement
  (liens, listes, dedoublonnage) et l'etat exact (0 mail parti) — laisser croire qu'un test a
  ete recu serait un rapport faux.
- **Reecrire un script d'envoi smtplib a la main alors qu'un script teste existe** : le script
  du dossier de campagne fait deja fusion/dedoublonnage des listes, resolution des balises, repli
  SMTP et journalisation ; le reecrire fait perdre des tours (echappement des chemins Windows) et
  laisse croire a un envoi different. L'appeler avec ses modes documentes (`--dry-run` /
  `--smtp-check` / `--test-email` / `--send`).

## Fichiers

- `scripts/check_html_static.py` — validation statique d'un template avant envoi : balises non
  fermees, meta viewport, `max-width`, media query, compte de liens / images / `<iframe>`, balises de
  fusion restantes, termes interdits (`--forbid`). Une commande au lieu d'un `HTMLParser` reecrit a
  chaque session.
- `scripts/check_render_png.py` — controle objectif d'une capture (palette, bandes, coupe).
- `scripts/check_delivery_imap.py` — releve d'un mail deja parti : placement reel par labels
  (`\Inbox` / `\Spam`), en-tetes d'authentification, liens/images attendus du corps recu,
  [`--from <adresse> --since <date> [--subject-contains "[TEST]"]
  [--expect <url> ...] [--expect-absent <url> ...] [--imap-host <hote> --user-env <VAR> --pwd-env
  <VAR> --any-folder]`. Les options d'hote/identifiants servent a verifier une boite d'hebergeur
  (cPanel/o2switch) et son dossier `INBOX.Sent` ; la-bas le placement est deduit du chemin du
  dossier, faute de labels Gmail.
  Les metadonnees du message sont relues **item par item** (`INTERNALDATE`, `X-GM-LABELS`,
  `FLAGS`) : un `FETCH` groupe peut revenir sans les items demandes, et conclure « ni INBOX ni
  Spam » sur des labels non relus transforme une erreur de lecture en faux diagnostic de spam.
  La commande affiche donc `INCONNU — labels non relus` et invite a relancer. `--expect-absent`
  sert a prouver la disparition d'une URL apres correction.
- `references/searching-murphy-palette.md` — tokens, typographies et style des mails produit.
- `references/sender-domain-preflight.md` — verifier un domaine expediteur (MX, SPF/DKIM/DMARC,
  SMTP/TLS, ou mettre les identifiants) avant une campagne envoyee depuis le domaine.
- `references/post-campaign-response-triage.md` — apres l'envoi : relever la boite IMAP en lecture
  seule, separer opt-out (par objet) et bounces (`message/delivery-status`), taxonomie des codes SMTP,
  motifs d'opt-out et regle RGPD de la reponse sans clic.
- `references/brevo-consent-reengagement.md` — reengagement a double opt-in : expediteur du
  domaine, modes du script, journal `mode` test/mass, pieges du mail de consentement.
- `references/css-inlining-gmail.md` — rendre un template habille par `<style>` compatible Gmail
  (inlining premailer, `<style>` residuel, `!important` responsive, effets de bord).
