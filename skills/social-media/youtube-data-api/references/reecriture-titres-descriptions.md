# Reecriture des titres/descriptions/tags d'une chaine (SEO YouTube, lecture seule)

Suite de `tri-thematique-et-vagues.md` : une fois la population triee (garder / deplacer /
supprimer), produire la liste des videos a reecrire, avec titre, description et tags proposes.
Regle cardinale : **on reformule ce qui est mesure, on n'invente jamais le contenu**. Le sujet
et la localisation cites dans le titre propose doivent venir du titre ou de la description d'origine.

## 1. `desc_200c` est TRONQUEE : ne jamais reconstruire une description sans en tenir compte

L'inventaire ne stocke que les 200 premiers caracteres de la description. Deux consequences :
- le critere « description < 100 caracteres » ne peut PAS distinguer une description de 200 c
  d'une description de 4000 c : les deux valent 200 (saturer est un signe de richesse, pas de vide) ;
- une description proposee assemblee depuis ces 200 c termine sur une phrase coupee en plein mot
  (« ...Night an »). Si `len(desc) == 200`, jeter la derniere phrase avant de la reutiliser.
Le signaler comme limite du livrable : la description complete n'est pas dans l'inventaire.

## 2. Tout critere exprime « mot-cle de jeu » est vrai par construction hors jeux

« Titre <= 40 caracteres OU pas de mot-cle de jeu dans le titre » est satisfait par 100 % des
videos musique/IA, qui ne peuvent pas contenir de nom de jeu. Sur une population mixte (514 videos
ici), le comptage des priorites est donc sur-estime cote hors-jeux : publier le split
jeux / hors-jeux de chaque liste, et marquer les lignes hors-jeux d'une colonne
`pattern_applique = hors_pattern_jeux` (le pattern mesure sur les jeux ne leur est pas applicable).

## 3. « Au moins 2 criteres » se declenche sans aucun defaut reel

Quand la liste de criteres contient a la fois des criteres de qualite (vues dans la fourchette,
duree >= 30 s) et des indicateurs de mal-ecriture, une video **bien ecrite** atteint deja 2 criteres
par le seul cumul vues + duree. Mesure : 16 des 93 candidats « priorite 1 » de ce nettoyage
n'avaient aucun defaut reel. Compter les defauts separement (titre sans mot-cle/court, description
pauvre, tags <= 3) et les publier en colonne `nb_defauts` : le score editorial se calcule dessus.

## 4. Formule de score : nommer la lecture retenue

Un score du type `vues x (1 + manquants / 5)` est ambigu (manquants = criteres NON remplis, ou
= defauts constates ?). Ecrire la lecture appliquee : ici `score = vues x (1 + nb_defauts / 5)`,
le diviseur 5 restant celui de la consigne, et `nb_defauts` compte les indicateurs de mal-ecriture
verifies (0-3). Sans cette phrase, deux personnes obtiennent deux classements differents.

## 5. Ne pas appliquer un pattern mesure sur un theme a un autre theme

Un gabarit de titre valide sur les shorts de jeu (« Hidden / Secret / Missed + objet + jeu ») ne se
transpose pas a une video de clarinette ou a un clip de jazz : la proposition devient une invention
de ton. Pour les populations hors perimetre : nettoyage factuel uniquement (espaces doubles,
contexte deja present dans le titre ou la description) et tags construits sur le **genre detecte**
(clarinette / jazz / fanfare / ska / rock / dub / violon), jamais la base de tags du jeu.

## 6. Un nettoyage de titre qui normalise TOUS les tirets casse les noms propres

`re.sub(r'\s*[-\u2013\u2014]\s*', ' — ', t)` transforme `Jean-Paul Dub` en `Jean — Paul Dub`.
Ne restructurer que les tirets entoures d'espaces (`\s+[-\u2013\u2014]\s*` / `\s*[-\u2013\u2014]\s+`), et laisser
intacts les tirets intra-mot. Verifier le replace sur un echantillon de titres avant de livrer.

## 7. Langue du titre propose

Ne pas basculer systematiquement en anglais : mesurer d'abord la langue des titres qui performent.
Mesure de cette chaine : 8 titres anglais / 2 francais dans le top 10 jeux, mais le 2e meilleur
(19 713 vues) est francais. Regle retenue et ecrite dans le rapport : anglais si le titre actuel
est deja anglais ou si c'est un short AAA a hashtags internationaux, francais sinon ; colonne
`langue_proposee` pour rendre la decision verifiable.

## 8. Colonnes d'un CSV de reecriture

Les 5 colonnes demandees (id, titre actuel, vues, duree, jeu identifie / titre propose /
description proposee / tags proposes / raison) + les colonnes de controle :
`rang`, `score_potentiel`, `nb_criteres_remplis`, `nb_defauts`, `criteres_remplis`,
`defauts_mesures`, `langue_proposee`, `pattern_applique`, `chaine_cible`, `nb_tags_actuels`,
`longueur_titre_actuel`, `longueur_desc_actuelle`. Signaler au rapport les colonnes ajoutees.
Verifier la longueur des titres proposes contre la cible (ici 50-70 c : 49/52 titres de jeu dans
la cible, mediane 56) et le tri decroissant du score, par programme, pas a l'oeil.
