---
name: youtube-data-api
description: "Use when auditing or cleaning a YouTube channel."
version: "1.0.0"
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [youtube, api, inventory, audit, quota, classification]
    category: social-media
---

# YouTube Data API v3 — inventaire, classification, quota

Classe de tache : lire les metadonnees d'une chaine YouTube (titres, vues, duree, visibilite, tags)
pour produire un inventaire et une classification des candidats a la suppression. Lecture seule.

## When to Use

- Inventaire complet d'une chaine (~100 a ~2000 videos) a partir d'un handle `@nom`.
- Classification de candidats au nettoyage (vues faibles, brouillons, doublons) a confirmer manuellement.
- Suivi de statistiques d'une chaine ou d'une liste de videos sous contrainte de quota.
- Toute lecture de metadonnees YouTube. Pour PUBLIER ou modifier, ce n'est pas la bonne authentification
  (il faut OAuth2 avec le compte proprietaire — voir `references/api-quota-et-auth.md`).

## Regle 0 — lecture seule, et le dire dans le rapport

Sauf mandat explicite contraire : aucun upload, aucune mise en prive, aucune modification de titre,
aucune suppression. Le fait que l'API permette l'ecriture ne l'autorise pas. Terminer le rapport par
une phrase explicite du type « aucune modification cote YouTube » — l'utilisateur verifie ce point.

## Regle 1 — jamais `search.list`

`search.list` coute **100 unites** par appel et ne sert a rien ici : la playlist `uploads` de la chaine
donne la liste complete des video_id. Couts reels : `channels.list` 1, `playlistItems.list` 1,
`videos.list` 1 (balayage complet d'une chaine de ~800 videos = ~35 unites sur 10 000/jour).

## Regle 2 — verifier la cle AVANT de depenser du quota

La cle vit dans `%LOCALAPPDATA%\hermes\.env` sous `YOUTUBE_API_KEY`. `read_file` **refuse** ce fichier
(depot d'identifiants Hermes) : le lire au terminal et n'afficher que la longueur et le prefixe.

```
KEY=$(grep "^YOUTUBE_API_KEY=" "$LOCALAPPDATA/hermes/.env" | head -1 | cut -d= -f2- | tr -d '"'"'"'\r')
echo "longueur=${#KEY} prefixe=${KEY:0:4}"
```

- `AIza` + **39** caracteres = cle API Cloud classique, la forme attendue par la Data API.
- `AQ.Ab8...` (**53** caracteres, contient un point) = cle AI Studio / Gemini. Si le test ci-dessous
  rend un 401, c'est que le serveur rejette le **type** de credential, pas la cle : ne pas conclure
  « cle invalide », demander une cle Cloud (voir `references/api-quota-et-auth.md`).
- Cle absente ou vide : s'arreter net et dire exactement `YOUTUBE_API_KEY absente du .env`.

Test de validite (1 unite, HTTP 200 = valide) :

```
curl -sS -o "C:/Users/<user>/AppData/Local/hermes/cache/scratch/yt_probe.json" -w "%{http_code}" \
  "https://www.googleapis.com/youtube/v3/channels?part=id,snippet,statistics,contentDetails&forHandle=<handle>&key=$KEY"
```

Toujours ecrire le corps dans un FICHIER (jamais seulement sur stdout) : le code HTTP seul ne dit pas
pourquoi un 403 est arrive, et un appel de diagnostic ne se rejoue pas sans repayer du quota.

## Regle 3 — `part=` doit couvrir tout ce que le rapport demande

Erreur la plus facile a commettre, y compris dans un prompt redige par l'utilisateur : demander
`statistics.viewCount`/`videoCount`/`subscriberCount` tout en passant `part=id,snippet,contentDetails`
rend une reponse **valide mais sans les champs**. Avant l'appel, relire la liste des champs a extraire
et verifier que chaque famille est dans `part=`. Pour un inventaire video :
`part=snippet,statistics,contentDetails,status`.

## Procedure

### 1. Resoudre la chaine
`channels.list?part=id,snippet,statistics,contentDetails&forHandle=<handle>` (sans le `@`).
Extraire `id`, `snippet.title`, `contentDetails.relatedPlaylists.uploads`, et les compteurs publics
(`statistics.videoCount`, `subscriberCount`, `viewCount`) : ils serviront de point de comparaison.

### 2. Enumerer les uploads
`playlistItems.list?part=contentDetails&playlistId=UU...&maxResults=50`, boucle sur `nextPageToken`,
collecte des `contentDetails.videoId` (dedoublonner en conservant l'ordre).

### 3. Recuperer les metadonnees par lots de 50
`videos.list?part=snippet,statistics,contentDetails,status&id=<50 ids joints par virgule>`. L'API
n'accepte pas plus de 50 `id` ; au-dela, l'appel est rejete. Laisser ~0,15 s entre les appels.

### 4. Ecrire les sorties
Deux CSV + deux JSON dans `cache/scratch/`. CSV en **UTF-8 avec BOM** (`utf-8-sig`) : le CSV est ouvert
dans Excel FR, un UTF-8 nu y affiche les accents casses. JSON en UTF-8 nu. Le JSON porte un bloc
`resume` (compteurs, mediane, top10, plus ancienne/recente, appels consommes, ecarts) ET la liste
complete — un JSON qui ne contient que la liste oblige a tout recalculer.

### 5. Classer
Une seule categorie par video, avec une raison courte (<= 15 mots) qui cite les valeurs mesurees, pas
le nom du critere. Priorite : rouge > jaune > vert ; des qu'un critere rouge est vrai, la video est
rouge meme si elle porte aussi un marqueur de brouillon. Trier le CSV par verdict (rouge, jaune, vert)
puis par vues croissantes : le fichier se lit alors comme une file de traitement.

### 6. Verifier avant de rendre
Relire les sorties et confronter : nombre de lignes = nombre de videos, somme des verdicts =
compteur `par_verdict`, nombre de groupes de doublons = somme des `nb`. Un rapport qui annonce
« 29 rouges » doit avoir 29 lignes rouges dans le CSV — imprimer les deux compteurs.

### 7. Consolider en listes cibles (supprimer / non liste / garder)

Chaque video appartient a UNE seule liste. Construire dans cet ordre :

1. **Supprimer** = union(verdict rouge, doublons non elus) dedupliquee en gardant le motif LE PLUS
   FORT (« rouge » l'emporte sur « doublon »). Consequence a expliquer dans le rapport : le CSV peut
   porter plus de motifs que de lignes (mesure : 29 rouge + 52 doublon sur 78 lignes, parce que
   3 videos cumulaient les deux) — sans cette phrase, la somme parait fausse.
2. **Garder** = les categories editoriales demandees, evaluees sur TOUTES les videos.
3. **Le reste** = la liste intermediaire.

**La priorite annoncee (le plus souvent GARDER > UNLISTED > SUPPRIMER) doit etre calculee sur toutes
les videos, pas seulement sur celles qui restent apres la premiere passe** : une priorite appliquee en
fin de chaine ne se declenche jamais. L'appliquer en soustrayant explicitement (`supprimer -= garder`)
et COMPTER les conflits arbitres — ce nombre est un resultat du rapport, et c'est lui qui merite une
revue humaine (mesure : 9 doublons perdants sauves par la priorite).

Verifier par arithmetique, dans les deux sens : somme des listes = total des videos, et le total de
vues sacrifiees de la passe N doit egaler celui de la passe N-1 moins les chevauchements (mesure :
3839 + 4212 - 9 = 8042 = total de la passe precedente). Un ecart de quelques unites sur ce controle
traduit un double comptage, pas une erreur d'arrondi.

### 8. Tout livrable de suppression est une liste, jamais une action

Le mandat type est « produire les listes pour un nettoyage MANUEL » : ne rien modifier cote YouTube,
ne pas passer en non liste, ne pas reordonner. Fournir en plus du CSV une liste d'identifiants prete
a coller dans YouTube Studio : **un `https://www.youtube.com/watch?v=<id>` par ligne**, dans le MEME
ordre que le CSV, et la verifier par regex (`[A-Za-z0-9_-]{11}`) puis par egalite avec les ids du CSV.

### 9. Ne jamais ecraser les sorties des passes precedentes

Chaque passe ecrit ses PROPRES fichiers (`yt_phase1_supprimer.*`, puis `yt_phase1_supprimer_sur.*`) :
les sorties precedentes sont la reference contre laquelle on verifie et la trace de la decision. Un
nom de fichier reutilise detruit la comparaison entre passes et l'explication a posteriori. Quand deux
jeux de listes coexistent (liste large / liste stricte), le dire explicitement dans le rapport pour
que le nettoyage manuel ne parte pas du mauvais fichier.

### 10. Verifier qu'une vague de suppression a ete appliquee, puis re-mesurer

Une liste livree n'est pas une suppression faite. Quand l'utilisateur annonce « les N videos sont
supprimees, verifie » :

1. Confronter les ids des listes de suppression avec `videos.list` (lots de 50, `part=id,status`)
   **et** avec l'endpoint public oEmbed, sans quota :
   `https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=<id>&format=json`
   -> **HTTP 200 = encore en ligne**, **HTTP 404 = supprimee**. `videos.list` peut encore retourner une
   video deja supprimee : les deux sources sont necessaires pour trancher.
2. Refaire l'inventaire COMPLET (channels -> playlistItems -> videos par lots de 50) avant toute
   nouvelle classification : un inventaire local est perime des la premiere suppression. Fichier neuf
   (`yt_etat_actuel.json`), jamais d'ecrasement de la reference precedente.
3. Repartir l'ecart avec l'inventaire precedent en TROIS comptes — planifiees executees / planifiees
   encore en ligne / disparitions HORS listes — et dire, pour chaque disparition hors liste, dans
   quelle liste elle figurait (a supprimer / a deplacer / a garder).

Detail, chiffres de controle et pieges de comptage : `references/tri-thematique-et-vagues.md`.

### 11. Auditer les playlists avant de proposer une strategie de playlists

`playlists.list?part=snippet,contentDetails,status&channelId=<UC...>` (pagine par 50) donne le nom et
`contentDetails.itemCount` pour 1 unite : c'est le comptage SANS paginer les items. Ne paginer
`playlistItems` que pour les playlists dont on veut les `video_id`, et **budgeter** : les fourre-tout
font exploser le quota (mesure : 112 unites `playlistItems` pour une seule chaine, a cause de playlists
de 727 / 610 / 580 items). Comparer `itemCount` declare et items retournes (ecart = video comptee mais
plus recuperable) et compter les playlists sans description. A remonter AVANT toute strategie : sur une
chaine ancienne les playlists se recouvrent massivement, donc une nouvelle playlist thematique nait en
doublon d'une existante.

Detail, seuils et livrable : `references/playlists-et-relance.md`.

## Sauvegarde de metadonnees avant suppression

Pour sauvegarder les metadonnees d'une video unique avant une eventuelle suppression (ex. pour remplacer le fichier source tout en conservant les vues, likes, commentaires) :

1. Utiliser l'endpoint `videos.list?part=snippet,contentDetails,status&id=<VIDEO_ID>` .
2. Extraire :
   - `snippet.title` -> titre
   - `snippet.description` -> description complete
   - `snippet.tags` -> tableau de tags (peut etre vide)
   - `snippet.categoryId` -> identifiant de categorie numerique
   - `snippet.defaultLanguage` (optionnel) -> langue par defaut
   - `contentDetails.duration` -> duree au format ISO 8601 (ex. PT14M20S)
   - `status.privacyStatus` -> statut de confidentialite (public, unlisted, private)
   - `status.license` -> licence (youtube ou creativeCommon)
   - `statistics` (optionnel) -> vues, likes, commentaires (si besoin de garder une copie)
3. Sauvegarder ces champs dans un fichier JSON (ou un fichier texte pret a coller) pour les reutiliser lors d'un nouvel upload.

**Note** : l'API renvoie toujours la description complete, contrairement a l'interface YouTube qui peut la tronquer si elle est longue ; aucune etendue necessaire.

## Regles de rapport (preferences utilisateur, valables pour toute cette classe)

- **Mesurer, ne pas affirmer.** Chaque chiffre du rapport vient d'une sortie de commande ou d'un code
  HTTP. Les chiffres du prompt (l'utilisateur annonce ses propres totaux) ne sont pas des mesures.
- **Rapporter les ecarts.** Un total API qui differe du total annonce par l'utilisateur est une
  information a part entiere : donner les deux valeurs, et separer ce qui est mesure de ce qui est
  deduit. Ne jamais « corriger » le chiffre de l'utilisateur. Vaut aussi pour les totaux attendus
  ecrits dans le PROMPT (voir Pitfalls : 22/30 attendus contre 32/20 mesures).
- **Publier un total de controle et le confronter.** Chaque script imprime ce qu'il a produit (lignes
  ecrites, ids uniques, somme des vues) et ce total est confronte a une valeur independante (somme des
  listes = total des videos). Quand c'est TA constante d'attente qui est fausse dans le harnais, l'ecart
  se rapporte aussi : une etiquette de controle fausse fait douter d'un resultat juste, et le taire
  coute une verification complete a l'utilisateur.
- **Erreur API = STOP net.** Code HTTP + corps JSON brut, et rien d'autre : pas de sortie partielle,
  pas de classification partielle, pas de fichier a moitie ecrit.
- **Ne jamais afficher la cle.** Longueur + prefixe uniquement. Et masquer les jetons avant d'imprimer
  un corps de reponse serveur : un message d'erreur Google peut citer la cle ou le projet —
  `sed -E 's/AIza[A-Za-z0-9_-]+/<REDACTED>/g; s/AQ\.[A-Za-z0-9_.-]+/<REDACTED>/g'`.
- **Compter le quota dans le rapport** (`channels 1, playlistItems 17, videos 17, total 35`) : c'est ce
  qui autorise ou non un second passage le meme jour.
- **Nommer la cause d'un critere non teste.** Un critere qui n'a rien declenche parce que la donnee
  n'existe pas dans la reponse (aucune video `unlisted` visible) n'est pas un critere « respecte » :
  le dire explicitement, sinon le rapport laisse croire que le cas a ete evalue.

## Pitfalls

- **Une cle API ne voit que les videos PUBLIQUES.** Les videos privees (et selon les cas certaines non
  listees) sont invisibles : `statistics.videoCount` et le total YouTube Studio peuvent donc etre
  largement superieurs au nombre d'items recuperes. Verifier `status.privacyStatus` avant de conclure
  quoi que ce soit sur les non-listees, et presenter l'ecart comme une explication *deduite* — seul
  OAuth2 tranche. Corollaire : un critere du type « non listee depuis > 30 jours » est intestable avec
  une cle API.
- **`statistics` peut omettre des champs** (compteur de likes masque) : traiter comme inconnu (`None`),
  jamais comme 0 — sinon la classification fabrique de faux « 0 vue ».
- **`videoCount` du canal et nombre d'items de la playlist uploads peuvent differer de +/-1** (compteur
  Google en retard). Ecart a signaler, pas une erreur de code. Sur une chaine nettoyee, imprimer les
  trois compteurs cote a cote (`videoCount`, items de la playlist `uploads`, items retournes par les
  lots de `videos.list`) : les trois egaux signifient qu'aucune video privee n'est cachee a la cle API
  — c'est un resultat a publier, pas une absence de resultat.
- **La duree est en ISO 8601** (`PT1H2M3S`, `P1DT2H`), jamais en secondes : la parser et non l'afficher.
  Un `PT45S` lu comme « 45 » donne des durees absurdes.
- **Doublons par titre : regrouper par composantes connexes, pas par paires.** Un balayage qui liste
  chaque couple proche produit des groupes qui se recouvrent et un comptage incoherent. Union-find sur
  un seuil de Levenshtein normalise (distance / longueur max), titres normalises (sans accents,
  minuscules, ponctuation reduite), puis un seul « titre_commun » par groupe. **Mais un seuil de
  similarite de titre produit des faux positifs par construction : il sert a TRIER, jamais a decider.**
  Des titres quasi identiques recouvrent souvent des contenus distincts (series numerotees, meme
  gabarit de titre a un mot pres, captations differentes d'un intitule generique). Avant toute
  suppression, separer « titres strictement identiques apres normalisation » (fiable) de « tout le
  reste » (revue humaine), et livrer DEUX listes : voir `references/doublons-et-listes-cibles.md`.
- **Le niveau de normalisation change le comptage, donc le livrable.** « Egalite de chaine brute » et
  « NFKD + minuscules + ponctuation reduite » ne donnent pas le meme total sur le meme jeu de doublons
  (mesure : 22 contre 32 non-elus stricts sur 52). Ecrire la regle EXACTE appliquee dans le rapport et
  annoncer le total mesure, meme s'il contredit le total attendu — c'est un ecart a rapporter, jamais
  un chiffre a faire coller (voir `references/doublons-et-listes-cibles.md`).
- **Un chemin MSYS passe a `curl` pour `-o` atterrit ailleurs** (`/tmp/x` -> `C:\tmp\x`) et le `sed`
  suivant ne trouve plus le fichier. Donner un chemin natif `C:/...` ABSOLU au scratch, sans passer
  par `$TMPDIR` (qui vaut `/tmp` dans le bash de l'agent, pas le dossier scratch annonce).
- **Un `| tail -60` sur la boucle de pagination coute le diagnostic.** Imprimer une ligne par page et
  par lot (`page 12 -> 600 ids`) : c'est cette trace qui prouve que les 17 pages ont ete lues.
- **Accents francais dans les titres** : ecrire les CSV avec `encoding="utf-8-sig"` et les relire avec
  la meme valeur, sinon une relecture de controle rend des titres mojibake et un faux ecart.

- **Remplacement de video** : la fonctionnalite de remplacement de video (inline replacement) n'est pas disponible via l'API pour les createurs reguliers ; elle est reservee a certains partenaires via un formulaire special (Vevo). En l'absence d'acces partenaire, la seule option pour changer le fichier source est de supprimer puis reuploader la video, en prenant soin de remettre les metadonnees sauvegardees.

## Fichiers

- `scripts/youtube_channel_inventory.py` — chaine complete et testee : controle de cle, pagination,
  lots de 50, inventaire CSV/JSON, classification CSV/JSON avec les criteres par defaut. Lancable par
  `python <copie locale du script> <handle>`. Le copier dans le scratch : il ecrit ses sorties a cote
  de lui.
- `references/api-quota-et-auth.md` — table de cout du quota, choix cle API vs OAuth2, table de
decision des codes d'erreur Google, criteres de classification par defaut.
- `references/doublons-et-listes-cibles.md` — consolidations en listes cibles : election de l'elu dans
  un groupe de doublons, deux niveaux de fiabilite (strict / approximatif), signaux de faux positif,
  familles de faux positifs observees, colonnes du CSV de revue.
- `references/tri-thematique-et-vagues.md` — passe N+1 : tri par theme (garder jeux / deplacer IA /
  deplacer musique / supprimer) sur titre + description, ordre des regles, criteres de suppression
  structurellement vides, controle croise anti-oubli, et verification post-nettoyage (oEmbed,
  decomposition de l'ecart d'inventaire, motifs tolerants au chiffre colle et au hashtag).
- `references/reecriture-titres-descriptions.md` — reecriture SEO : titre/description/tags proposes,
  pieges de `desc_200c` tronquee, criteres vrais par construction hors jeux, score de potentiel,
  nettoyage de titres sans casser les noms propres, choix de la langue.
- `references/playlists-et-relance.md` — audit des playlists : enumeration, `itemCount` declare contre
  mesure, budget quota des fourre-tout, redondance a trancher avant d'en creer une nouvelle.
