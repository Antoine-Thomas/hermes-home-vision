# Tri thematique d'une chaine et vagues de nettoyage successives

Approfondissement pour la passe N+1 : a partir d'un inventaire deja classe (rouge/jaune/vert),
separer une chaine multi-sujets en listes par theme (garder / deplacer / supprimer).

## 1. Classer sur TITRE + DESCRIPTION, jamais le titre seul

Un createur qui publie des shorts de jeu sous titre anglais omet souvent le nom du jeu dans le
titre : `These Blue Containers Give Different Loot Every Time`, `Epic Sword vs Gun Showdown!`,
`I Tried The Craziest Weapon In The Game!`. Mesure : 45 jaunes ne portaient le mot `cyberpunk`
que dans le titre, et 35 autres **uniquement** dans la description (`Found in Cyberpunk 2077.`,
`#Cyberpunk2077`). Concatenation a utiliser : `norm(titre) + ' | ' + norm(desc_200c)`.
Un inventaire qui ne stocke que `desc_200c` (200 premiers caracteres) suffit : les hashtags y sont.

## 2. Construire la liste des jeux depuis l'inventaire, pas depuis sa memoire

Le prompt cite 5-6 jeux ; la chaine en contient davantage. Balayer l'inventaire avec un jeu de
candidats (~90 noms) et sortir les titres qui matchent : les vignobles locaux (`DARKTIDE` = Warhammer
40k, `SLEEPING DOGS`, `CRONOS The New Dawn`, `RAID Shadow Legends`, `Path of Exile`, `Half-Life Alyx`,
`Judge Dredd`, `Enclave`) sortent de l'ombre et evitaient une erreur d'aiguillage. Supprimer ensuite
les candidats a faux positifs (`metro` -> Metro Bank$y, un groupe ; `dirt` -> un clip ; `control`,
`sonic`, `vr` -> mots ordinaires).

**Chaque motif doit tolerer le chiffre colle et le hashtag.** `\bwitcher\b` ne matche pas `witcher3`,
`\bcyberpunk\b` ne matche ni `cyberpunk2077` ni `#Cyberpunk2077`, et `#SleepingDogs` se normalise en un
seul jeton `sleepingdogs` : la frontiere de mot tombe au mauvais endroit des qu'un chiffre ou un `#`
suit le nom. Les deux parades s'appliquent ENSEMBLE — inserer un separateur avant normalisation
(`re.sub(r'(?<=[a-z])(?=\d)', ' ', t)`) et lister les deux formes (`cyberpunk2077|cyberpunk`,
`sleeping ?dogs`). Un motif partiel sous-compte en silence : sur la meme donnee, la proportion de
shorts « jeu » est passee de 91 a 99 apres correction, et `Dirt Rally 2.0` / `Tschart de Kaer Morhen`
retombaient dans « autre ».

## 3. `\bai\b` est un piege en francais

En texte minuscule, `j'ai` / `t'ai` / `n'ai` se normalisent en `j ai` / `t ai` et declenchent le
mot-cle `ai`. Mesure : 3 videos musicales et un clip de 2009 classes « IA » a tort. Utiliser `\bia\b`
(sigle francais, peu collisionnel) et les noms d'outils (hermes, latentsync, heygen, suno, firefly,
stable diffusion, `runway ml`). Attention aussi a `motion design` : c'est de l'animation, pas de l'IA.

## 4. Ordre des regles = arbitrage editorial, a ecrire dans le rapport

Premiere regle qui matche, gagne. Mettre `jeux` avant `musique` (un live « 07-Cyberpunk 2077 - Live
Immersif » n'est pas de la musique) mais `musique` avant `ia` quand la cible musique est la clarinette
(`Jazzmer - Clarinette & AI` part sur la chaine musique, pas sur la chaine IA). Un titre qui matche
deux themes se signale en colonne `conflit_avec_<autre>` — c'est la que se cachent les cas a trancher
(`EDGERUNNER 2 - La revolution IA : Stable Diffusion`, contenu Cyberpunk produit par IA).

## 5. Le critere « jaune sous X vues apres 6 mois » est souvent structurellement VIDE

Quand la passe precedente a classe rouge sur `vues<10 et age>6 mois`, aucun jaune ne peut avoir
moins de 10 vues et plus de 6 mois : le critere ne peut rien declencher. Mesure : 0 declenchement sur
494 jaunes. Le dire (critere nomme non testable) au lieu de laisser croire que le cas a ete evalue,
et reporter la suppression sur les criteres qui mordent reellement (0 vue, brouillon, doublon).

## 6. Regle « brouillon/test » : ne jamais la faire reposer sur un mot-cle seul

`demo` et `tuto` apparaissent dans des titres legitimes (`ENCLAVE ! TUTO COMMENT : je me fais
eclater en 75 sec`, `Resident Evil 7 demo`) : une regex par mot supprimerait des videos de jeu a
1 000 vues. Restreindre a : titre normalise de <= 3 caracteres, OU titre **entierement** compose du
mot technique (`^(test|essai|brouillon|1080p|runway|in3d|meta[a-z]*phose[s]?\d*|converted|tuto)( [a-z0-9]*){0,2}$`),
OU presence de `converted` (fichier jamais renomme). Et scoper la regle aux verdicts jaune/rouge :
lister a part les candidats verts non supprimes, pour que la restriction soit visible.

## 7. Comptages a publier dans le recap de vague

- une table `par_theme` : nb, vues cumulees, verdict propose ;
- la masse de vues des 5 listes doit egaler la somme des vues de la population restante
  (controle par soustraction, pas par confiance) ;
- `candidats_deplacer_avant_arbitrage` vs liste finale : l'ecart est le nombre de conflits arbitres ;
- `recouvrement_phase1_vague2` : doit etre vide, sinon une video serait comptee deux fois dans le
  cumule du nettoyage.

## 8. Controle croise anti-oubli

Apres construction, rebalayer les videos NON retenues avec le motif « jeu » : toute video portant un
mot-cle de jeu hors de la liste jeux est une erreur d'aiguillage. Mesure de la passe : 0 sur 758.

## 9. Verifier qu'une vague de suppression a bien ete appliquee

Le mandat « les N videos sont supprimees, verifie l'etat » se traite comme une mesure, pas comme une
confirmation.

**`videos.list` ne prouve pas qu'une video est morte.** Une video supprimee peut encore etre retournee
par l'API un moment (cache), et elle disparait de la playlist `uploads` AVANT de disparaitre de
`videos.list` : les deux signaux ne coincident pas. Controle independant et gratuit en quota, l'endpoint
public oEmbed :

```
https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=<id>&format=json
  -> HTTP 200 (+ titre) = la video est REELLEMENT en ligne
  -> HTTP 404            = la video n'est plus disponible
```

Presentation attendue : « encore retournee par l'API mais 404 en oEmbed = supprimee » (1 cas mesure),
« 200 en oEmbed = toujours en ligne » (2 cas mesures : le nettoyage est incomplet, le dire et nommer les
ids).

**Une suppression se propage en quelques heures : re-mesurer avant de conclure a l'echec.** Deux
controles a 8 h d'intervalle sur le meme lot : 2 videos encore en ligne au premier passage (oEmbed 200),
disparues au second. Un « nettoyage incomplet » annonce trop tot se retourne contre le rapport, et
l'utilisateur reprend une suppression deja faite. Horodater chaque mesure et refaire le controle oEmbed
avant de declarer qu'une video est encore la — le seul cas ou l'echec est reel est un 200 stable sur
deux mesures espacees.

**Repartir l'ecart d'inventaire en trois comptes, jamais un seul.** `set(inventaire N) -
set(inventaire N+1)` donne les videos disparues ; l'intersecter avec la liste planifiee separe les
suppressions executees du reste. Mesure d'une passe : 84 disparues = 76 planifiees executees + 2
planifiees encore en ligne + 8 disparitions HORS listes (1 254 vues cumulees).

**L'ecart NET entre deux inventaires n'est pas le nombre de suppressions : une video peut avoir ete
PUBLIEE entre les deux mesures.** Comparer dans les DEUX sens et nommer les nouvelles venues. Mesure :
733 -> 732 (soit -1) alors que 2 videos avaient disparu et 1 venait d'etre publiee ; l'ecart contre la
reference de la veille est 85 (86 disparues - 1 publiee), pas 86 et pas 78. Un rapport qui annonce
« 78 supprimees, ecart 78 » sur une chaine qui publie se contredit tout seul.

**Pour chaque disparition hors liste, dire dans quelle liste elle figurait** (a supprimer / a deplacer /
a garder) : 6 des 8 etaient dans « a deplacer » (donc a conserver pour migration) et 2 dans « a garder ».
C'est cette colonne qui declenche la question utile (« est-ce volontaire ? »), pas le compteur brut.
Un ecart non explique laisse l'utilisateur chercher la difference tout seul — et invalide la liste de
migration qui suit.

**Controles a imprimer** : `statistics.videoCount` == items de la playlist `uploads` == items retournes
par les lots de `videos.list`. Les trois egaux signifient qu'aucune video privee n'est cachee a la cle
API ; un ecart se presente comme une explication *deduite*, jamais comme une mesure.

**Cadence et dernieres publications** : compter les publications des 30 / 60 / 90 derniers jours, la date
du dernier short (`duree_s <= 60`) et les themes des 10 dernieres publications. C'est ce qui rend
visible une derive editoriale (chaine devenue majoritairement IA alors que l'objectif annonce est le
jeu) — mesure a remonter avant tout plan de relance.
