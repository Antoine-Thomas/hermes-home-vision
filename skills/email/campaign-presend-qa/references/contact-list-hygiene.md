# Hygiene d'une liste de contacts avant import (Brevo ou autre ESP)

Ou placer quoi quand une liste brute est decoupee en fichiers d'import : ce qui est
reintegrable, ce qui est ecarte et pourquoi, et les invariants a verifier apres chaque
regeneration.

## Decoupage et invariants

- Un fichier d'import par niveau de consentement, plus un fichier d'exclusion
  (`EMAIL,RAISON`) qui porte **une raison par ligne**, regles evaluees dans l'ordre — la
  premiere qui matche gagne : adresse malformee (pas de `@`, encoded-word MIME dans EMAIL,
  regex invalide) > domaine = nom de fichier (`.avif/.png/.jpg/.svg`) > domaine placeholder
  (`entreprise.fr`, `domaine.com`, `structure.fr`, `example.*`, `test.com`) > domaine de
  revente (`domainmarket`, `brandbucket`, `defining`, `sedo`, `hugedomains`) > adresse
  technique (`dpo@`, `privacy@`, `privacypolicy*`, `noreply@`, `no-reply@`, `postmaster`,
  `abuse`) > liste de diffusion (`<liste>@lists.*`) > numero de telephone en part locale
  (`0607865319@orange.fr`, `121743945@qq.com`) > webmail sans nom.
- Les **listes de diffusion** arrivent en categorie professionnelle (domaine non webmail) et y
  restent invisibles jusqu'a l'envoi : les sortir des qu'elles sont reperees, avec leur raison.
- Le bucket **webmail sans nom** (gmail/yahoo/hotmail/free sans prenom ni nom) est numeriquement
  le plus gros et ne se jette pas : le sortir dans un fichier dedie avec FIRSTNAME/LASTNAME
  vides, ce qui rend l'exclusion lisible (elle ne garde que les vraies anomalies) et evite de
  perdre un quart des envois potentiels. Recuperer la colonne SOURCE depuis le fichier brut
  d'origine quand le fichier d'exclusion ne porte que EMAIL,RAISON.
- Invariants a verifier a chaque regeneration : somme des lignes des fichiers produits = lignes
  du fichier source ; 0 doublon inter-fichiers sur EMAIL en comparaison casse-insensible
  (y compris contre le fichier d'exclusion) ; 0 ligne vide ; nombre de colonnes constant ;
  dernier octet = LF ; pas de BOM.
- Controler les adresses interdites **fichier par fichier**, pas sur l'ensemble : le fichier
  d'exclusion contient par construction les cas ecartes, l'y compter est un faux positif.

## Noms exploitables

- Title Case applique **mot par mot**, particules (`de`, `la`, `van`, `von`) en minuscules sauf
  en tete, apostrophes conservees : la lecture litterale « premiere lettre majuscule, reste
  minuscule » produit des noms composes faux (`Rancier picard`). Annoncer la convention retenue.
- Decoder les encoded-words MIME des colonnes de nom avant toute autre operation ; un nom
  complet colle dans FIRSTNAME se decoupe en prenom/nom AVANT la detection d'inversion. Un nom
  illisible apres decodage reste vide plutot qu'approximatif (tester le resultat contre
  `^[Lettres ' -]{1,40}$`).
- Inverser FIRSTNAME/LASTNAME quand FIRSTNAME est en fait le nom de famille, detecte par la
  part locale : (1) le premier token de la part locale egale le LASTNAME -> inverser ; (2) la
  part locale commence par une abreviation (>= 2 caracteres) du prenom present dans LASTNAME
  (`ale.choplain@` pour Alexis Choplain) -> inverser. Exiger **au moins 2 tokens** dans la part
  locale : avec un seul token (`prenom@domaine`), la regle inverse des couples corrects.
- La normalisation doit etre **idempotente** : un second passage doit annoncer 0 modification.
  Une regle d'inversion non idempotente double-inverse au re-run.
- Un nom d'organisation ou de metier dans FIRSTNAME/LASTNAME (`Association`, `Coworking`,
  `Naturopathe`) n'est pas un nom de personne : lister les lignes concernees et proposer de
  vider les deux champs en gardant COMPANY. Jamais corriger en silence.

## Joignabilite des domaines (avant d'ecrire a la liste)

Un domaine mort est un bounce garanti : le tester AVANT l'envoi, pour la liste entiere.

```python
import csv, json, urllib.request, concurrent.futures as cf

def alive(dom):
    for rtype in ("MX", "A"):
        req = urllib.request.Request("https://dns.google/resolve?name=%s&type=%s" % (dom, rtype),
                                     headers={"User-Agent": "hermes-dns-check/1.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            j = json.loads(r.read().decode("utf-8", "replace"))
        if j.get("Status") == 0 and j.get("Answer"):
            return dom, True
    return dom, False

domaines = {l["EMAIL"].split("@")[-1].lower() for l in csv.DictReader(open(src, encoding="utf-8-sig"))}
with cf.ThreadPoolExecutor(max_workers=24) as ex:
    for dom, ok in ex.map(alive, sorted(domaines)):
        if not ok:
            print("MORT:", dom)
```

- L'appel se fait par **domaine dedoublonne minuscule** (centaines d'appels, pas milliers) :
  l'API publique repond en une requete par nom.
- **`Status 3` (NXDOMAIN) et `Status 2` (SERVFAIL / lame delegation) sont morts tous les deux** :
  tester `Status == 0 and Answer` couvre les deux ; un test qui ne rejette que le NXDOMAIN laisse
  passer des zones cassees (domaine existant, sous-domaine casse).
- Repli MX puis A : un domaine sans MX mais avec un A reste joignable, donc ne pas ecarter sur le
  seul MX vide.
- Resultat : ces adresses sortent de la liste propre et entrent dans le fichier a valider avec le
  motif `DOMAINE_NON_RESOLVABLE`, jamais supprimees du fichier source.

## Boites generiques : compter et presenter, ne pas trancher

- Motifs a compter : `contact@`, `hello@`, `info@`, `bonjour@`, `accueil@`, `recrutement@`, `jobs@`,
  `support@`.
- Rendre trois chiffres : par motif, par extension (`.fr`, `.com`, `.net`, `.org`... — deduire
  l'extension de tout ce qui suit le dernier point, pas les deux derniers labels), et une vingtaine
  de domaines d'accueil avec des exemples d'adresses.
- Sur une liste d'agences/societes, ces adresses sont presque une par domaine distinct et ~0 sur
  messagerie grand public : ce sont de vraies boites de contact, pas des doublons. Les supprimer
  coute des destinataires valides, les garder coute la personnalisation — donc chiffrer, montrer, et
  attendre la decision. Ne jamais retirer d'office sous pretexte que « contact@ » est generique.
- Reconnaitre aussi les adresses fabriquees : nom de personne sur une messagerie grand public
  (`jean.dupond@gmail.com`), domaine de personne sans site (`info@anniedupont.com`), et surtout les
  adresses issues d'un scraping de page — un nom de fichier en part locale ou en domaine
  (`shield-light-cta@2x.1786f34.avif`) est un artefact de gabarit, jamais une boite.

## Restitution

- Le rapport annonce : lignes par fichier, suppressions par raison, confirmations demandees
  (0 nom de fichier, 0 placeholder, 0 adresse technique dans les fichiers exploitables),
  nombre de noms normalises, et un echantillon anonymise (`ab***@gm***.com`).
- Les contacts importables restent sans consentement documente jusqu'a l'opt-in : le dire, et
  rappeler le nombre de jours d'envoi pour la limite de l'ESP.
