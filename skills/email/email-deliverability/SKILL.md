---
name: email-deliverability
description: "Use when email bounces or SPF/DKIM/DMARC need auditing."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [email, bounce, opt-out, spf, dkim, dmarc, deliverability, suppression-list, imap]
    category: email
---

# Deliverabilite et bounces d'un envoi de masse

Diagnostiquer un envoi de masse qui a produit des bounces, isoler les desinscriptions, et brancher
une liste de suppression dans le script d'envoi. Profondeur (code IMAP, regex de parsing, table de
codes SMTP, gabarit de restitution) : `references/bounces-et-deliverabilite.md`.

## When to use

- Un envoi de masse a produit des bounces et l'utilisateur veut la cause.
- Une hypothese d'authentification circule (« cause probable : SPF/DKIM/DMARC mal configures ») :
  elle se confirme ou se refute a la mesure, pieces en main.
- Des destinataires ont repondu « stop » / « unsubscribe » et il faut les sortir definitivement.
- Il faut nettoyer la liste source (domaines morts, placeholders) et brancher un fail-safe
  d'exclusion dans le script d'envoi.

## Regles durables

- **Deux diagnostics INDEPENDANTS, jamais melanges dans le rapport** : la delivrabilite du domaine
  (SPF/DKIM/DMARC/reputation) et la qualite de la LISTE (adresses mortes). Une campagne peut afficher
  10-12 % de bounces avec une authentification impeccable : dans ce cas la cause est la liste, et le
  rapport le dit AVANT de proposer une modification DNS.
- **Le verdict d'authentification se lit chez le DESTINATAIRE, pas dans un avis.** Un DSN renvoye
  embarque le message d'origine avec les en-tetes du serveur qui a recu (`Authentication-Results`,
  `ARC-Authentication-Results`, `Received-SPF`). C'est la seule mesure qui vaut, elle coute zero
  envoi, et elle refute ou confirme l'hypothese en une lecture.
- **Categoriser sur le code SMTP, jamais sur le texte du bounce** (anglais, parfois localise).
- **Zero envoi pendant l'audit** : `--dry-run` cote script, `readonly=True` + `BODY.PEEK` cote IMAP.
  Un `fetch` sans PEEK marque les messages comme lus et rompt la promesse « lecture seule ».
- **L'heure d'arrivee reelle est `INTERNALDATE`, pas l'en-tete `Date:`** : les clients envoient
  souvent `+0000`, ce qui decale la date d'une desinscription de deux heures. Pour un opt-out
  (RGPD), c'est la date de la demande qui compte.
- **Un opt-out ne se requalifie jamais.** Reponse avec signature pro sans clic sur le lien de
  confirmation = opt-out par prudence (`reponse_sans_clic`). Une adresse sortie ne recoit plus rien.
- **Ne rien exclure en silence** : chaque retrait a sa ligne (fichier + motif) et le rapport donne les
  comptes avant/apres (`contacts N -> M`).
- **Un fail-safe non teste n'est pas un fail-safe** : supprimer temporairement le fichier obligatoire,
  relancer, constater le code de sortie et l'absence de connexion SMTP, restaurer.
- **Un ecart entre la demande et la mesure se signale** : si l'utilisateur annonce N reponses et que
  la boite en contient moins, nommer ce qu'elle contient et l'ecart, sans fabriquer le N-ieme.

## Procedure

1. **Trier la boite en lecture seule.** `imaplib.IMAP4_SSL(mail.<domaine>, 993)`, identifiants SMTP du
   `.env`, `select("INBOX", readonly=True)`, `search` par date. Discriminer les humains des MTA par
   l'EXPEDITEUR (`serveur-mail@…`, `mailer-daemon@…`, `postmaster@…`, `no-reply@…`), jamais par le
   corps : la recherche pleine texte sur « stop » / « unsubscribe » ramene tous les bounces, car le
   pied de page de la campagne contient ces mots. Verifier aussi Junk/spam/Archive/Trash et dire
   lequel est vide. Code : reference §1.
2. **Reconnaitre les trois formats de bounce** (Postfix du relais sortant, DSN Google, NDR Microsoft)
   et garder le premier qui rend un destinataire : `Final-Recipient:` puis `Diagnostic-Code:` /
   `said:` / `Status:`. Table de codes et regex : reference §2.
3. **Prouver l'authentification** en extrayant `Authentication-Results` / `Received-SPF` /
   `DKIM-Signature` (`d=` et `s=`) du message d'origine joint au DSN. Verifier que le selecteur signe
   est celui publie en DNS, et que l'IP de sortie REELLE (le relais final de la chaine `Received:`,
   pas le serveur de connexion) est couverte par le SPF, `include:` de prestataire developpe par un
   TXT. Reference §3.
4. **Auditer le DNS** : SPF, DMARC, MX, A du serveur de connexion, et plusieurs selecteurs DKIM
   (`default`, `mail`, `o2switch`, `dkim`, `s1`). **Piege blacklists** : depuis un resolveur public,
   Spamhaus/CBL repondent `127.255.255.254` = « requete refusee », PAS une inscription (les codes
   d'inscription sont `127.0.0.2`-`127.0.0.11`). Sur un `127.255.255.x`, ecrire « non concluant
   depuis ce poste » et renvoyer vers un checker navigateur. Reference §4.
5. **Tester les domaines de la liste en masse** : `scripts/verif_domaines_doh.py --csv <contacts.csv>`
   (DNS-over-HTTPS Google, MX puis A, aucune dependance). **`Status=3` (NXDOMAIN) ET `Status=2`
   (SERVFAIL : NS morts, zone cassee, lame delegation) sont tous deux NON DELIVRABLES** : classer sur
   `not MX and not A`, jamais sur `status == 3` seul. Reference §5.
6. **Ecrire les fichiers de suppression et brancher le fail-safe** : `optout.csv`
   (`email,date_demande,motif,source`, **obligatoire**) et `bounce_<AAAAMMJJ>.csv`
   (`email,date_demande,raison,source`) a la racine du dossier de campagne ; le script d'envoi les
   charge au demarrage (`glob` sur `bounce_*.csv`), filtre apres le dedoublonnage, imprime le compte
   d'exclusions, refuse de demarrer si `optout.csv` manque, et refuse `--test-email` vers une adresse
   exclue. Backup horodate du script avant edition, nom cite au rapport. Reference §6.
7. **Restituer** la repartition des bounces par categorie, les verdicts d'authentification recus, les
   chiffres de la liste, et les desinscriptions (`email | date heure locale | motif | source`).
   Gabarit : reference §7.

## Pieges

- **Un journal d'envoi « N/N envoyes, 0 echec » ne dit rien des bounces** : le script ne trace que le
  hand-off SMTP, le rejet arrive apres. Croiser les adresses des bounces avec la liste d'envoi avant
  d'accuser le script.
- **Les boites generiques (`contact@`, `bonjour@`, `info@`, `hello@`) resolvent** : les garder dans la
  liste nettoyee avec une colonne `AVERTISSEMENT`, ne pas les exclure en silence — l'arbitrage revient
  a l'utilisateur.
- **Artefacts de scraping** : un nom de fichier image pris pour une adresse (`…@2x.<hash>.avif`), des
  adresses fabriquees par motif (`contact@<domaine>` en masse), des placeholders (`jean.dupont@…`). Les
  nommer : c'est la preuve que le probleme est la source, pas l'envoi.
- **SPF/DKIM/DMARC `pass` = hypothese REFUTEE.** Ne pas appliquer « quand meme » le plan de correction
  DNS ecrit d'avance dans la demande : nommer la cause reellement mesuree et proposer la suite dessus.
- **`p=none` avec un `rua=` chez un prestataire est une configuration normale** en surveillance : ne
  pas la presenter comme une erreur, dire qu'aucun rejet n'est demande.

## Files

- `references/bounces-et-deliverabilite.md` — code IMAP, regex des trois formats de bounce, table des
  codes SMTP, extraction des verdicts d'authentification, verifications DNS, gabarit de restitution.
- `scripts/verif_domaines_doh.py` — verifie en masse la resolvabilite des domaines d'un ou plusieurs
  CSV d'emails (MX + A via DNS-over-HTTPS), classe ok / nxdomain / zone_cassee / erreur et ecrit un JSON.
