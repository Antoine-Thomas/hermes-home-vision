# Doublons de titre et listes cibles de nettoyage

Approfondissement des etapes 7 a 9 de la procedure : passer d'un inventaire classe a des listes
« supprimer / passer en non liste / garder » utilisables telles quelles.

## 1. Le seuil de similarite TRIE, il ne DECIDE pas

Un regroupement de titres vides par distance de Levenshtein est un **outil de tri**. Sur un jeu reel il
produit des faux positifs par construction : la mesure du nettoyage d'une chaine a montre qu'a peine
la moitie des « doublons non elus » etaient de vrais doublons, et que le plus gros sacrifice portait
sur une video a plusieurs milliers de vues parfaitement legitime.

Consequence pratique : ne jamais livrer une seule liste de suppression construite sur ce seuil.
Livrer **une liste fiable** et **une liste de revue**, et dire dans le rapport que le fichier fiable
ne contient que ce qui est demontre.

## 2. Election deterministe dans un groupe

Un groupe de doublons garde UNE version, choisie par cle de tri stable et rejouable :

1. vues decroissantes ;
2. a egalite de vues, `publishedAt` decroissante (la plus recente) ;
3. a egalite de vues ET de date, `video_id` croissant (lexicographique).

Sans le 3e critere l'election depend de l'ordre de parcours et deux executions donnent deux listes.
Les autres membres sont « non elus ». Ecrire le motif avec les deux valeurs :
`doublon — garde <id_elu> (<vues_elu> vues vs <vues_non_elu>)` — c'est ce qui rend la decision
verifiable sans relire les donnees.

**Aucun groupe ne part entierement** : apres election, verifier qu'il reste toujours au moins un
membre hors de la liste de suppression. Un groupe entierement supprime signale une erreur de logique.

## 3. Deux niveaux de fiabilite

| Niveau | Definition | Usage |
|---|---|---|
| **strict** | titres egaux apres normalisation | suppression possible |
| **approximatif** | tout le reste | revue humaine uniquement |

Normalisation a appliquer et a ECRIRE dans le rapport : NFKD, suppression des diacritiques,
minuscules, tout caractere hors `[a-z0-9]` remplace par une espace, espaces multiples collapses, trim.

Effet mesure du niveau choisi sur le meme jeu de 52 non-elus : **22 stricts** en egalite de chaine
brute, **32 stricts** avec la normalisation ci-dessus. Les 10 ecarts sont des paires qui ne differaient
que par la casse, l'accent ou la ponctuation finale (`Le Bocal` / `Le bocal`, `cafe sauvage` /
`café sauvage`, `Keep my heart` / `Keep my heart.`) : ce sont de vrais doublons, donc la normalisation
est plus JUSTE que l'egalite brute. Le seul point a signaler est le remplacement d'un separateur
(`Helelyos - ... -` contre `Helelyos , ... .`) : a confirmer visuellement quand la ponctuation porte du
sens.

Presentation attendue dans le rapport : « ton attendu 22/30 ; mesure 32/20, voici la regle appliquee
et les 10 paires qui font l'ecart ». Ne jamais ajuster un seuil pour retomber sur le chiffre attendu.

## 4. Signaux de faux positif

Chacun suffit a renvoyer la paire en revue plutot qu'en suppression :

| Signal | Regle | Pourquoi |
|---|---|---|
| numerotation d'episode | regex `^\s*\d{1,2}\s*[-'\u2019]` sur l'un des deux titres | deux episodes d'une meme serie ont un titre quasi identique et un contenu different |
| mots distinctifs | apres retrait des mots courants, les deux titres ont chacun un jeton alphabetique de 4+ caracteres absent de l'autre | un seul mot porteur change (objet, arme, lieu, morceau) = contenu different |
| ecart de duree | `abs(duree_a - duree_b) > 30 s` | un re-upload garde sa duree ; deux captations diffèrent |

Un tokenizer qui casse un nom propre en deux jetons fabrique un faux signal
de « mots distinctifs » (`Blackminou` contre `Black Minou`) : lire les titres avant de faire confiance au
signal, et ne pas compter ce cas comme une divergence.

## 5. Familles de faux positifs, par mecanisme

- **Meme gabarit, un mot porteur change** : `<phrase identique> <OBJET A>` contre `<phrase identique>
  <OBJET B>`. Le piege est maximal quand les durees sont quasi egales (un short de 15 s contre un autre
  de 16 s) : c'est ce qui a coute le plus gros sacrifice. C'est precisement le contenu a conserver.
- **Series numerotees** : `06-...` / `07-...`, `04 – ...` / `05 – ...`, `1-...` / `02-...`,
  `LIVE #14` / `LIVE #15`. Le tri par vues designera un episode comme « l'original » des autres.
- **Intitule generique repete** : plusieurs videos portant exactement le nom d'un artiste ou d'un lieu
  sont des captations differentes, pas des copies.
- **Edition annuelle** : quand l'un des deux titres porte une annee (`... à la demeurée 2024`), les
  dates confirment des editions distinctes.
- **Homonyme court** : un titre d'un seul mot (`Sauvage`, `VISION`) matche par accident avec un pluriel
  ou un autre clip. Ces paires ont souvent peu de vues, mais elles sont indistinguables du vrai doublon
  sans lire les dates et les durees.

## 6. Vrais doublons malgre des titres non identiques

A l'inverse, trois signatures rendent le doublon tres probable meme hors du niveau « strict » :

- une **faute de frappe corrigee** (`... Ophiri Axii ...` contre `... Ophirie Axii ...`) ;
- un **espace manquant dans un nom propre** (`Blackminou` contre `Black Minou`) ;
- **meme titre, meme date de publication, duree a moins de 1 % pres** (deux parties de 6 h 49 a 128 s
  d'ecart) — la date identique plus la duree identique valent mieux que le titre.

C'est cette liste-la qu'il faut remonter a l'utilisateur comme « ceux que je crois etre de vrais
doublons » quand la regle mecanique rend zero cas fiable : un `vrai_probables = 0` calcule par seuil est
un artefact de seuil, pas un resultat editorial. Le dire.

## 7. Colonnes du CSV de revue

Un fichier de revue n'est utile que s'il porte la comparaison, pas seulement l'identifiant :

```
video_id, titre_non_elu, vues_non_elu, titre_elu, vues_elu,
date_non_elu, date_elu, duree_non_elu, duree_elu,
categorie_probable, piste, signaux
```

`piste` = `faux_doublon_probable` / `vrai_doublon_probable` ; `signaux` = la liste des signaux
declenches avec leurs valeurs. Signaler au rapport toute colonne ajoutee hors de la liste demandee :
c'est une deviation de format, l'utilisateur decide si elle reste.

## 8. Chevauchement entre listes : le calculer et le dire

Deux listes definies par des regles differentes se recouvrent mecaniquement. Cas typique : une liste
« sure » definie comme `rouges + doublons stricts` et une liste « a verifier » definie comme
`doublons approximatifs` ; une video rouge qui est aussi un doublon approximatif appartient aux deux.

- Calculer l'intersection, l'ecrire dans le recap (`overlap_...`) et annoncer le **perimetre distinct**
  reel (mesure : 20 lignes ecrites, 19 videos reellement a verifier).
- Rester conforme au format demande (garder les 20 lignes) et signaler le defaut de conception de la
  regle plutot que de corriger les fichiers en silence : c'est la regle qui est ambigue, pas la donnee.
- Le meme controle vaut pour la somme des vues : une video comptee dans deux listes fait depasser la
  somme du total de reference — l'ecart exact identifie la ligne en cause.
