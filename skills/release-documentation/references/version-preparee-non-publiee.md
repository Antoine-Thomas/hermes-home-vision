# Documenter une version preparee, non publiee

Quand la version n'est PAS sortie (pas de tag, pas de release), le lot documentaire a la meme
structure que pour une version publiee, mais la page d'accueil doit rendre impossible de la croire
livree. Recette dediee, referencee depuis `SKILL.md`.

## Forme du README

1. **Bandeau** : la ligne de version courante porte la mention de statut entre parentheses
   (« preparee, non publiee ») ; la version stable reste nommee comme **stable precedente** (et garde
   ses anciennes lignes originale / precedente). Le lecteur doit savoir en une ligne ce qui est livre
   et ce qui ne l'est pas.
2. **Tableau `Version | Statut | Branche / Tag | Documentation`** : ligne supplementaire pour la
   version en preparation, colonne statut disant le bloqueur (« preparee, non publiee — bloqueurs B1/B2
   ouverts »), colonne tag annoncant **aucun tag**, colonne documentation pointant vers les fichiers
   nouveaux (architecture + changelog de la version).
3. **Branche par defaut** : elle porte la doc de la version preparee sans etre la version stable.
   L'ecrire en clair sous le tableau (`main` porte la doc de la X preparee ; la stable reste Y, tag
   `vY` ; aucun tag `vX` n'existe) — sinon la page d'accueil annonce comme livree une version qui ne
   l'est pas, et l'extrait d'installation `git checkout <tag>` envoie vers un tag inexistant.
4. **Section bloqueurs** : ce qui interdit la publication, avec l'etat **mesure** de chaque verrou
   (un artefact livrable absent, une tache planifiee `Disabled`, un job en pause, une dependance en
   attente d'amont), placee avant la licence, suivie de la checklist qui conditionne le tag et la
   release. Un bloqueur se date et se prouve, il ne se decrit pas de memoire.
5. **Aucun tag, aucune release, aucun `gh release edit` dans ce pass** : « preparee » et « publiee » sont
   deux etats distincts du depot, et c'est l'operateur qui fait passer de l'un a l'autre.

## Re-mesurer avant d'ecrire

**La valeur perimee vit aussi dans les COMMANDES du document.** Une version de reference change a deux
endroits : la ligne de prose **et** la sortie attendue de la commande `--version` que l'operateur
compare (« attendu : `vX+NNNN` »). Corriger la prose seule laisse une procedure de verification qui
valide la mauvaise version. Recenser les deux sites avant d'ecrire (`grep -in "<motif>" <fichier>` sur
le numero ancien) et corriger les deux.

**Les compteurs se re-mesurent a la source**, jamais en recopiant la ligne voisine :

| Affirmation du document | Mesure |
|---|---|
| nombre de notebooks du second cerveau | `lsNotebooks` sur l'API SiYuan (`http://127.0.0.1:6806/api/notebook/lsNotebooks`, en-tete `Authorization: Token <...>` lu dans `.env` sans l'afficher) |
| nombre de fragments d'index RAG | `GET /sante` du serveur RAG (8200) |
| nombre de profils | `ls -d profiles/*/` + la racine |
| service reellement en ecoute / port | `netstat -ano \| grep LISTENING \| grep ":<port>\b"` |
| version de l'agent | `hermes --version` |

**Un gabarit fourni par la demande qui contredit la mesure se corrige dans le detail ET se signale** :
un profil annonce « 1 bot Telegram + 1 cle routeur » qui ne porte qu'une cle d'API en dur, un compte de
notebooks faux, un service cite comme actif qui est a l'arret. Le schema demande est une intention, pas
une source : on ecrit la valeur mesuree, et le rapport dit quel element du gabarit a ete corrige et
pourquoi.

**Les chiffres du jour se documentent avec leur date et leur methode.** Un cout ou une latence repris
d'un fichier de mesures date de plusieurs jours se re-mesure si l'appel est bon marche, et les deux
valeurs (catalogue et mesure du jour) apparaissent dans le document — l'ecart est une information, pas
une erreur a masquer. Si la mesure implique un appel payant, le dire dans le rapport avec son cout
(regle de bascule : prevenir avant de depenser).

## Passer de « preparee » a « publiee » (second passage)

Deux formes, et c'est l'operateur qui tranche — **demander, ne pas choisir** :

- **Statut « publiee » dans le MEME commit que le tag (forme de ce depot quand la redaction et la
  publication se font dans la meme session).** Le document nait directement `> Statut : publiee.` avec
  sa phrase « tag annote `vX` sur `main` (pose dans le meme commit que ce changelog) », le commit du lot
  part, le tag suit immediatement, et il n'y a **AUCUN commit post-publication**. Rien n'est jamais
  publie en `preparee`.
- **Passage de statut dans un commit `docs:` separe, APRES la publication**, quand le lot a deja ete
  pousse en `preparee` (tag et push d'abord, sinon la page d'accueil annonce livree une version que le
  depot ne porte pas encore).

Dans les deux cas, meme discipline que le premier pass : recenser les sites, indexer les chemins un par
un, aucun `git add -A`.

Sites a reprendre — les **recenser par mesure**, jamais de memoire :
`grep -in "preparee\|apres validation" README.md docs/CHANGELOG-<v>.md`.

| Site | Avant | Apres |
|---|---|---|
| entete du CHANGELOG | `> Statut : preparee.` + la phrase annoncant commit et tag a venir | `> Statut : publiee.` + le tag et sa cible (`tag vX -> <sha>`) |
| bandeau du README | `<v> (preparee, non publiee)` | `<v> (publiee)` ; la version precedente passe en « stable publiee anterieure » |
| tableau des versions | statut « Preparee », colonne tag « tag `vX` (apres validation) » | statut « Publiee », colonne tag « tag `vX` » |
| phrase des N versions telechargeables | « la X sur `main` (tag `vX`, apres validation) » | « la X sur `main` (tag `vX`) » — et le COMPTE annonce avance de 1 |
| paragraphe « branche par defaut » | porte la X preparee et la Y publiee | porte la X publiee (tag `vX`) ; l'ordre s'inverse |
| tableau de documentation / « Voir aussi » | libelle « changelog de la X (preparee) » | « changelog de la X (publiee) » |

Controles de sortie : `grep -c` ne rend plus aucun `preparee` desormais faux, le **compte annonce egale
le nombre de lignes du tableau** de versions, et la preuve apres push se refait comme ci-dessous.

## Preuve apres push

Deux lectures, parce qu'elles ne prouvent pas la meme chose :

1. **Contenu servi brut** : `curl -s https://raw.githubusercontent.com/<o>/<r>/main/README.md | head -6`
   — c'est le fichier tel qu'il est publie.
2. **Page rendue** : `curl -sL https://github.com/<o>/<r> | grep -c "<libelle>"` sur les libelles cles
   (nom de version, mention de statut, liens vers les fichiers nouveaux, titre de la section bloqueurs).
   Un compteur a zero sur un libelle attendu est un vrai signal d'echec ; un grep vide sur une phrase
   **mise en gras** ne l'est pas (le balisage est dans la ligne) — chercher le libelle nu.
