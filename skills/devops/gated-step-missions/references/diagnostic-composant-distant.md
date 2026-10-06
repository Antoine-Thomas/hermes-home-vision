# Diagnostiquer un composant qui depend d'un service distant

Pour un composant dont la decision est prise par un service hors machine (API de decision typee,
modele distant, routeur a quota) et dont l'etat est affiche par un health check local. A lire avec
la section « Pieges » de la skill : ici le detail des mesures, la le jugement.

## 1. Etablir les niveaux de preuve, sans appel payant

Un health check honnete pour ce genre de composant distingue au moins :

| Niveau | Ce qu'il prouve | Comment le mesurer sans cout |
|---|---|---|
| service joignable | DNS + TLS + route reseau | handshake TLS sur `hote:443` (aucune requete applicative) |
| modele/endpoint accessible | le service a DEJA repondu un jour | presence d'une reponse valide dans l'HISTORIQUE de trace |
| appel fonctionnel | la derniere trace est fraiche | age de la derniere ligne contre une fenetre (ex. 7 j) |
| decision valide | la derniere trace porte une decision exploitable | champ de decision non nul dans la derniere ligne |
| repli | le consommateur a du se rabattre | champ de source/verdict de la derniere ligne |

Deux consequences a ecrire dans le rapport : un critere calcule sur la SEULE derniere ligne rend
l'etat instable (une abstention suffit a basculer le composant) ; et un critere ecrit en dur dans le
code rend toute mesure inoperante.

## 2. Lire la FORME d'une entree de trace avant son libelle

Beaucoup de consommateurs ecrivent `source: "regex"` / `state: "fallback"` aussi bien pour « reponse
sous le seuil » que pour « service injoignable ». Ce qui les distingue, ce sont les champs :

- chemin SUCCES : champs riches (probabilites par option, confiance, latence du service, identifiant
  de reponse) — presents uniquement si le client a recu un corps exploitable ;
- chemin ECHEC : cle d'erreur explicite (`raison: "<service>_down"`, `raison: "erreur"`, `erreur:`),
  et AUCUN champ riche.

Lire donc le code du consommateur pour savoir QUELS champs il ecrit sur chaque branche, puis classer
la ligne. Le libelle ne suffit pas, le code tranche.

Corollaire durable — **corriger le PRODUCTEUR, pas seulement le lecteur.** Tant que l'appelant ecrit le
meme libelle de repli pour les deux cas, aucun health check ne peut les distinguer. Le correctif est
d'ajouter un motif explicite a la ligne de trace : `raison: "sous_seuil"` (avec la confiance) quand le
service A REPONDU mais que le seuil local a rejete la decision, `raison: "<service>_down"` / `"erreur"`
quand il n'a pas repondu, et rien sur le chemin succes. C'est ce motif que le health check lit ensuite.

**Compatibilite avec l'historique** : les lignes ecrites AVANT le correctif n'ont pas de motif. Les
classer sur les champs riches (presence d'une confiance ou de probabilites = le service avait repondu,
absence des deux = panne) au lieu de les mettre en quarantaine : sinon l'etat du composant bascule
d'un coup a la mise a jour, sur des donnees qui ne disent rien de nouveau.

## 3. Sonder un quota distant en lecture seule

Avant d'ecrire « quota epuise », mesurer chez le fournisseur avec des GET de LECTURE (aucune
inference, aucun cout, aucun secret imprime) :

- `GET <base>/api/v1/auth/key` (OpenRouter) : `limit`, `usage`, `usage_daily/weekly/monthly`,
  `is_free_tier`, `free_model_daily_requests.{used,limit,remaining}`, `rate_limit` ;
- `GET <base>/api/v1/credits` : `total_credits`, `total_usage` ;
- `GET <base>/api/v1/models` : `pricing` du modele vise.

Lecture du resultat : un `usage` non nul avec `total_credits: 0` signifie que la regle d'acces n'est
PAS etablie — ecrire `inconnu` sur la continuite du service, jamais « gratuit donc garanti ». Un
compteur d'appels gratuits (du type `free_model_daily_requests`) est le premier a citer dans le
risque de re-panne : c'est la ressource qui s'epuise sans erreur de configuration.

La cle se lit dans `.env` par le script qui interroge l'API (variable d'environnement construite a la
volee) : le script ne l'imprime jamais, et le rapport ne cite que `presente` / `absente` par NOM de
variable.

**Un appel d'inference reussi peut ne bouger NI le compteur d'appels gratuits, NI `usage`.** Mesurer le
delta des trois champs (`used`, `remaining`, `usage`) juste avant et juste apres l'appel, et consigner
ce delta mesure : une estimation du plan (« cet appel consomme +1 ») recopiee telle quelle devient dans
le rapport une consommation qui n'existe pas — et l'erreur inverse (une consommation reelle non vue) est
plus grave encore. Le meme controle vaut pour le cout en dollars.

## 4. Les seuils sont dans le CONSOMMATEUR, pas chez le fournisseur

Un meme service distant est appele par plusieurs consommateurs, chacun avec son propre seuil et son
propre repli. Les inventorier avant de conclure : module de routage (choix de couche), service
d'ecriture (categorisation/indexation), hook de plugin, helper manuel d'agent. Pour chacun, relever :
constante de seuil, timeout, forme du repli, et le fichier de trace. Un service peut avoir un bon
taux de succes et malgre tout ne plus jamais etre retenu, parce qu'un seuil mal cale le refuse.

**Avant de deplacer un seuil, verifier QUEL champ il compare, et calibrer par REPLAY.** Deux mesures a
cout nul, dans cet ordre :

- **L'identite du champ.** Un client de decision rend souvent PLUSIEURS nombres : une distribution
  (`probabilities`) et un scalaire par choix (`confidence`). Les citer cote a cote sur un cas connu
  tranche : mesure d'un cas ou `confidence` valait 0,38 alors que la dominante de `probabilities`
  valait 0,59. Si le seuil porte sur le scalaire, l'abaisser de 0,15 ne rattrape PAS un cas a dominante
  0,59 : le faux negatif survit au correctif, et l'etape suivante cherche une panne qui n'existe pas.
  Un correctif de seuil se valide sur la VALEUR COMPAREE, jamais sur la valeur qu'on croyait voir.
- **La calibration par rejeu.** Rejouer les decisions DEJA consignees (fichier de trace) sous l'ancienne
  et la nouvelle regle, et consigner la distribution avant/apres : acceptees, abstentions, et accords
  avec la decision de reference. Une constante abaissee achete des decisions ET des desaccords :
  compter les deux et nommer le cas gagne. Si la trace ne couvre pas le job vise (ex. 4 lignes pour un
  seuil), le dire — un seuil fige sur 4 decisions n'est pas un seuil calibre. Et ne pas melanger deux
  jobs : une distribution mesuree sur la CATEGORISATION ne calibre pas un seuil de CHOIX DE COUCHE, meme
  client et meme echelle de confiance.

## 5. Plugin active / handler inactif

Pour un composant fourni par un plugin : `plugins.enabled` (ou l'ancienne liste `plugins: [nom]`) dit
que le plugin est CHARGE, pas que son handler s'execute. Le mode d'un handler est une option de
configuration dont le defaut est souvent `off` : chercher la section de reglages du plugin dans le
fichier de config, et une section de reglages absente signifie « valeurs par defaut », donc handler
muet. Le client (bibliotheque) du plugin, lui, peut rester utilise par d'autres scripts : sa presence
ne prouve pas que le plugin tourne. La commande d'etat du plugin, quand elle existe, repond en
quelques lignes (`<plugin> status`) sans rien depenser : la preferer a une deduction.

## 6. Compter l'usage REEL avant de conclure « utilise » ou « inutile »

Un composant peut etre branche partout et ne servir nulle part ; l'inverse est vrai aussi. Croiser :
les fichiers de trace (`*.jsonl` de decisions, 20-50 lignes suffisent a un taux), le journal du
producteur (une ligne de creation qui porte une valeur EXPLICITE ne declenche aucun appel distant),
les resultats de harness, et la table d'historique du runtime en lecture seule (`sqlite` en
`mode=ro`). Puis reparler en clair : « N appels sur 7 jours, dont X par un harness de test, Y par la
production, Z par le handler ». Un appel servi par un cache (latence ~1 ms sur une entre identique)
n'est pas un appel reseau : le dire, sinon le compte est faux d'une unite.

## 7. Le breaker et le fail-open se decrivent en une phrase chacun

Pour un client qui gere la limite de debit : retry UNE fois si `Retry-After` tient dans une fenetre,
puis compteur de 429/529 consecutifs par endpoint, seuil d'ouverture (ex. 3), silence pendant une
periode (ex. 120 s), remise a zero sur tout succes, et fail-open (retour `None`) sur toute autre
defaillance. C'est ce bloc qui explique le comportement observe lors d'une panne de quota : le
rapport doit pouvoir predire la trace que produira un 429 avant de le rencontrer.
