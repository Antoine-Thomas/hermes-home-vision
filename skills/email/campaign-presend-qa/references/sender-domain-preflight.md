# Preflight d'un domaine expediteur (avant une campagne SMTP directe)

A passer **avant d'ecrire le mail**, pour la campagne envoyee depuis une boite du domaine de
l'utilisateur (l'ESP refuse l'import sans opt-in, donc la demande de consentement part par
SMTP direct). Ces controles sont independants du contenu du message.

## 1. Le domaine recoit et peut envoyer

```bash
nslookup -type=MX <domaine>          # le MX existe et pointe sur l'hebergeur mail
```

```python
import socket, ssl
for h, p in ((HOST_SMTP, 465), (HOST_SMTP, 587), (HOST_SMTP, 25)):
    try:
        socket.create_connection((h, p), timeout=8).close(); print(h, p, "TCP OK")
    except Exception as e:
        print(h, p, "ECHEC", e)
ctx = ssl.create_default_context()
with ctx.wrap_socket(socket.create_connection((HOST_SMTP, 465), timeout=10),
                     server_hostname=HOST_SMTP) as s:
    c = s.getpeercert()
    print(s.version(), [v for k, v in c.get('subjectAltName', ()) if k == 'DNS'],
          c['notBefore'], '->', c['notAfter'])
```

- 465 (SSL) et 587 (STARTTLS) repondent generalement ; le 25 est souvent bloque depuis un
  reseau residentiel — ce n'est pas un probleme du serveur, ne pas le rapporter comme tel.
- **Les SAN du certificat doivent couvrir le host utilise** (`server_hostname` passe, donc la
  verification de hostname est reelle). Un `mail.<domaine>` n'est acceptable que si le
  certificat le liste, sinon utiliser l'adresse brute du noeud de l'hebergeur.
- Lire ensuite `s.esmtp_features.get('auth')` (les hebergeurs mutualises offrent `PLAIN LOGIN`)
  et `size` : cela evite de conclure a tort qu'un login echoue.

## 2. Authentification du courrier

```bash
nslookup -type=TXT <domaine>                        # SPF (parmi d'autres TXT)
nslookup -type=TXT _dmarc.<domaine>                 # DMARC
nslookup -type=TXT default._domainkey.<domaine>     # DKIM (selecteur courant)
```

- **Un seul enregistrement SPF.** Deux TXT `v=spf1` sur le meme domaine = PermError (RFC 7208)
  cote destinataire, donc spam, meme si l'un des deux contient le bon include. Fusionner en un
  enregistrement unique listant tous les emetteurs reels :
  `v=spf1 +a +mx +include:<relais d'envoi de l'hebergeur> +include:<ESP eventuel> ~all`.
  Cas frequent : un SPF d'ESP laisse en place a cote de l'SPF de l'hebergeur.
- Chez o2switch, l'include du relais d'envoi est `+include:spf.jabatus.fr` et s'ajoute depuis
  l'outil **Authentification** du cPanel : editer le SPF dans l'editeur de zone DNS le fait
  ecraser a la mise a jour suivante de la zone.
- **Confirmer une propagation annoncee, jamais la croire** : `nslookup -type=TXT <domaine> 8.8.8.8`
  ET le resolveur local, puis comparer la chaine **entiere** a celle que l'utilisateur a donnee
  (et le selecteur DKIM au passage). Le cache du resolveur public peut servir l'ancienne zone
  plusieurs heures apres la fusion : c'est mesurable, pas a supposer.
- **Un `ip4:` seul ne suffit pas chez un mutualise** : o2switch relaie par des IP tournantes
  (mesure : 109.234.163.31, 109.234.163.39, 109.234.164.45 sur trois envois successifs), donc
  c'est l'`include:spf.jabatus.fr` qui couvre la rotation — l'IP explicite de la zone n'est pas
  celle utilisee a chaque envoi, et l'SPF passe quand meme. Ne pas diagnostiquer un probleme
  d'SPF depuis une seule IP, et ne pas « corriger » l'IP dans la zone.
- DKIM : un enregistrement present sur le selecteur utilise suffit pour demarrer.
- DMARC : `p=none` en surveillance (`rua=`) est un socle acceptable ; le durcissement vient
  apres plusieurs semaines de rapports.

## 3. Cadre d'envoi de l'hebergeur

- Les hebergeurs mutualises relaient les sortants via des IP tournantes et ne documentent pas
  toujours de quota horaire : ne pas annoncer un plafond qui n'est pas verifie.
- En revanche ils filtrent les messages sortants (entetes, format, sujet) et interdisent le
  courrier commercial non sollicite dans leurs CGV : presenter le message comme une **demande
  de consentement unique**, sans relance automatisee, et le dire si la liste compte plusieurs
  centaines d'adresses.

## 4. Identifiants : ou et comment

- Cles dediees dans `%LOCALAPPDATA%\hermes\.env` (sauvegarder le fichier avant) :
  `REENG_SMTP_HOST`, `REENG_SMTP_PORT`, `REENG_SMTP_USER`, `REENG_SMTP_PASSWORD`.
- La meme boite se relit en IMAP (`mail.<domaine>:993`, meme mot de passe de compte) : c'est le
  moyen de verifier la remise cote expediteur, dossiers cPanel/Dovecot `INBOX`, `INBOX.Junk`,
  `INBOX.Sent`. A savoir : un envoi par client SMTP externe ne depose **rien** dans `INBOX.Sent`
  (mesure : dossier present, 0 message apres plusieurs envois authentifies). La trace sure reste le
  journal du script ; une copie dans « Envoyes » demande un APPEND IMAP cote client ou l'archivage
  cote hebergeur.
- Ne jamais ecraser les cles `EMAIL_*` : elles pilotent le pont mail de Hermes (polling, envoi
  depuis la boite habituelle).
- Laisser la ligne de mot de passe vide avec un commentaire : c'est l'utilisateur qui colle le
  mot de passe du compte email (cPanel > Comptes de messagerie). Ne jamais le demander ni
  l'afficher dans la reponse.
- Si l'utilisateur le colle malgre tout dans la conversation : ne pas l'ecrire dans `.env` (un
  appel d'ecriture le recopie dans la transcription), le signaler comme expose (historique de
  session et journaux Hermes), recommander la rotation dans le cPanel puis l'usage du **nouveau**
  mot de passe, et lui laisser la saisie. Verifier ensuite l'etat sans lire la valeur :
  `awk -F= '/^REENG_SMTP_PASSWORD/{print "reeng_pwd_chars:" length($2)}' .env` (libelle en
  minuscules pour ne pas declencher la redaction ; ligne vide -> 0).
- Repli d'hote : le script retombe sur le SMTP Gmail (`EMAIL_*`) des que `REENG_SMTP_HOST` est
  absent. Si l'identifiant o2switch manque, ne pas laisser ce repli envoyer depuis la mauvaise
  boite : completer l'identifiant, pas changer d'expediteur. `--smtp-check` doit afficher le
  fournisseur attendu, le compte masque et « mot de passe defini : OUI » avant tout envoi.
- Aucun repli croise entre fournisseurs dans le code : le quadruplet se resout selon le seul
  host retenu, sinon le mauvais mot de passe part au mauvais serveur (`535`) et le diagnostic
  part dans la mauvaise direction.

## 5. Apres l'envoi : prouver l'authentification par les en-tetes du destinataire

Un pic de bounces n'incrimine pas SPF/DKIM/DMARC : cela se mesure, et la preuve est deja dans la
boite d'envoi (les rapports de non-remise renvoient le message d'origine).

- **Les NDR embarquent le verdict du receveur.** Extraire des bounces `Authentication-Results`,
  `ARC-Authentication-Results` et `Received-SPF` : chez Google
  `dkim=pass header.i=@<domaine> header.s=<selecteur>; spf=pass; dmarc=pass`, chez Microsoft
  `spf=pass (sender IP is <ip>); dkim=pass (signature was verified) header.d=<domaine>; dmarc=pass`.
  Des `pass` sur les trois axes chez Gmail ET Outlook refutent « SPF/DKIM/DMARC mal configures » par
  une mesure, et reorientent le diagnostic vers la liste des destinataires.
- **Le selecteur reellement signe se lit dans le `DKIM-Signature` du message renvoye**
  (`d=<domaine>; s=<selecteur>`) : le comparer a l'enregistrement publie
  (`nslookup -type=TXT <selecteur>._domainkey.<domaine>`). Un selecteur signe mais non publie donne
  `dkim=fail` chez le destinataire meme si la zone « a bien un DKIM ».
- **Verifier l'alignement dans le meme releve** : `From` et `Return-Path` sur le domaine signe,
  `List-Unsubscribe` present, `Message-ID` du domaine. Un `From` hors du domaine signe casse DMARC
  meme avec une signature DKIM valide.
- **La chaine `Received` du message renvoye donne l'IP vue par le destinataire**
  (`<noeud>.o2switch.net [109.234.164.45]` -> `smtp.jabatus.fr [109.234.163.11]` -> relais
  `dans.` / `seigneur.` / `smtp-2.jabatus.fr`). Ce sont les IP des relais, couvertes par
  `include:spf.jabatus.fr`, qui sont evaluees — pas l'IP explicite de la zone.
- **Piege DNSBL : un resolveur public ne repond pas.** `nslookup <ip-inversee>.zen.spamhaus.org`
  rend `127.255.255.254` : c'est le code « requete refusee (resolveur public non declare) », **pas**
  une inscription (les codes d'inscription de zen vont de `127.0.0.2` a `127.0.0.11`). Ne jamais
  rapporter ce resultat comme « IP blacklistee » ni comme « IP propre » : le declarer NON CONCLUANT
  depuis ce poste et renvoyer a un verificateur web (mxtoolbox) si la reponse est voulue.
- **Un bounce decrit le destinataire, pas l'emetteur.** Lire le code SMTP avant d'accuser
  l'authentification : `5.4.4` domaine inexistant (adresse fabriquee), `5.1.x`/`5.1.10` adresse
  inconnue, `5.2.2` boite pleine, `5.4.1` refus Exchange, `5.7.1` relais refuse, `4.4.1` connexion
  refusee ou timeout (temporaire, l'adresse peut etre valide). Un lot d'echecs qui ne nomme ni
  SPF/DKIM/DMARC ni blocage de reputation est un probleme de qualite de LISTE — regarder comment
  elle a ete construite (des domaines entiers en `5.4.4` trahissent des adresses generees par motif
  `contact@<domaine>.fr`, jamais verifiees).
