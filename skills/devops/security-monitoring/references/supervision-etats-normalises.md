# Supervision a etats normalises (etendre un heartbeat existant)

Objectif : qu'un rapport de sante represente l'etat REEL d'un parc de services (services locaux,
routeur LLM, base de connaissance, planificateur, repli), et non « tous les ports repondent ».
S'applique quand on herite d'un heartbeat existant et qu'on doit le porter sans casser ses lecteurs.

## 1. Modele d'etat

Quatre valeurs, une seule par composant :

| Etat | Sens | Exemple de preuve |
|---|---|---|
| `READY` | la sonde FONCTIONNELLE a conclu | le document attendu est dans le top-k ; une decision reelle est revenue ; aucun job actif en erreur |
| `DEGRADED` | le composant repond mais une mesure se degrade | taux de succes des appels recents sous le seuil ; budget memoire au-dessus du seuil ; repli active et dernier etage atteint |
| `FAILED` | aucune reponse, ou condition de panne dure | transport KO sur un port ferme ; tache desactivee ; index perime avec run planifie manque |
| `BLOCKED` | non evaluable | role decideur non demontre ; run en cours |

Regle d'agregation, a ecrire dans le rapport (champ `regle_overall`) :
`FAILED` d'un composant critique -> global `FAILED` ; sinon `DEGRADED`/`FAILED`/`BLOCKED` d'un
secondaire -> `DEGRADED` ; sinon `READY`. Declarer la liste des composants CRITIQUES et la liste des
SECONDAIRES dans le code, pas au fil du rapport.

Trois frontieres a tenir, chacune payee sur un composant reel :

- **Abstention n'est pas panne.** Un composant dont la decision a ete rejetee par un SEUIL LOCAL a bien
  fonctionne : il reste `READY`, et c'est le motif ecrit par SON producteur (`raison="sous_seuil"`) qui
  le dit. Ne le classent `BLOCKED` que les motifs TECHNIQUES (`<service>_down`, `erreur`). Un health
  check qui confond les deux declare en panne un service sain a chaque decision faible.
- **Quota epuise n'est pas panne.** Une ressource distante tarie (quota gratuit du fournisseur) rend la
  decision IMPOSSIBLE sans qu'aucun service soit tombe : `DEGRADED` avec le motif explicite et le
  compteur brut (`used` / `limit` / `remaining`) dans le rapport, jamais `BLOCKED` ni `FAILED`. Sans ce
  champ, une panne de quota se lit pendant des jours comme une panne de service.
- **Un critere code en dur interdit toute sortie d'etat.** Un drapeau `... = False`, ou un critere
  calcule sur la SEULE derniere ligne de trace, condamne le composant a vie : aucune mesure ne peut
  alors l'en faire sortir. Le critere doit etre la CONCLUSION des mesures (ex.
  `role_demontre = au moins une decision valide dans la FENETRE et aucun repli technique en cours`), et
  sa sortie d'etat se prouve par un test a entree controlee (section 4) PUIS par un run reel.

## 2. Sondes par type de composant

- **Service HTTP local** : un code de transport reussi ne suffit pas. Fixer le code ATTENDU par
  service (`200`, ou `401`/`404` quand le service repond volontairement ainsi) puis, quand c'est
  possible, une requete fonctionnelle : moteur de recherche -> position du document attendu dans le
  top-k ; moteur de decision local -> une decision reelle avec sa probabilite ; base de connaissance
  -> une requete SQL qui rend la derniere ecriture.
- **Service a TLS** : sonder en `https` avec un contexte non verifie et l'authentification attendue.
  Une sonde en clair sur un port TLS fait ecrire une **stack trace** dans le journal du service a
  CHAQUE tick (le plugin de securite refuse la connexion) : le journal devient illisible et la sonde
  conclut a tort a une panne.
- **Modele local (GPU)** : disponibilite via la liste des modeles (`/api/tags`) **et** test reel de
  generation **seulement si le modele est deja en VRAM** (`/api/ps`). Un modele configure mais absent
  de la liste = `DEGRADED`, pas `READY`.
- **Routeur LLM** : lire sa base d'appels en `mode=ro` et calculer le **taux de succes des N derniers
  appels** avec la repartition des codes. C'est la seule facon de distinguer « debout » de
  « fonctionnel » quand les upstreams renvoient `503`/`504`/`429`.
- **Decideur distant a quota** (API de decision typee, LLM externe) : cinq niveaux de preuve sans appel
  payant — service joignable (handshake TLS, aucune requete applicative), endpoint ayant DEJA repondu
  (reponse valide dans l'historique), derniere trace fraiche (age contre une fenetre, ex. 7 j), decision
  valide DANS LA FENETRE (et non sur la derniere ligne), repli limite aux motifs TECHNIQUES — PLUS la
  mesure du quota fournisseur en lecture seule (`GET <base>/api/v1/auth/key` :
  `free_model_daily_requests.{used,limit,remaining}`, `usage_daily`, `is_free_tier` ;
  `GET <base>/api/v1/credits` : `total_credits`), exposee a cote de l'etat du composant. C'est ce champ
  qui empeche « quota epuise » de se lire comme « service en panne ». La cle se lit en memoire et
  s'ajoute a la liste de masquage ; le harnais verifie son ABSENCE du rapport serialise. Ces GET de
  lecture ne consomment pas le quota d'inference : le mesurer, pas le supposer.
- **Chaine de repli** : lire la chaine dans la config LIVE (primaire + etages), verifier chaque etage
  avec les sondes deja faites, puis chercher dans les sessions recentes le provider/modele REELLEMENT
  utilise : `repli_active` (le primaire n'apparait plus) et `dernier_etage_atteint` (le dernier etage
  a servi) sont des degradations a rapporter, pas des details.
- **Planificateur** : un enregistrement par job — `id`, `nom`, `enabled`, dernier run, DERNIER
  RESULTAT, `failure_streak`, prochain run — plus le battement du planificateur lui-meme. Un job en
  erreur se rapporte, il ne se repare pas.
- **Taches planifiees** : etat de la tache + historique (`LastRunTime`, `LastTaskResult`).
- **Memoire / budgets** : lire la limite dans la config (jamais la coder en dur), rapporter le
  pourcentage et marquer la lecture seule.
- **Couts** : cumul + fenetre 24 h, avec le seuil affiche et un drapeau « provisoire ».
- **Gateway / daemon** : battement (age), PID vivant (OpenProcess `PROCESS_QUERY_LIMITED_INFORMATION`,
  jamais `os.kill(pid, 0)` qui termine le process sous Windows), phase de cycle de vie, et l'etat par
  profil si le daemon est multiplexe.

## 3. Identifiants de sonde et secrets

Un service protege se sonde avec ses identifiants : les lire **en memoire** depuis la config de
deploiement, les enregistrer dans une liste de masquage utilisee par la fonction qui tronque les
messages, et n'ecrire dans le rapport que des CODES, des compteurs et des noms d'hote. Les variables
d'environnement ne se lisent que par leur NOM (jamais leur valeur). Controle final : chercher les
valeurs sensibles connues dans le rapport produit (plus les motifs generiques de jeton et les
en-tetes `Authorization`) — attendu : aucune occurrence.

## 4. Harnais de test des 4 etats (obligatoire)

Les etats doivent RESULTER des sondes : un test qui ecrit `state="FAILED"` a la main ne prouve rien.

1. Rendre les endpoints parametrables (un dictionnaire au niveau du module) pour que le test
   redirige une sonde vers un service local sans toucher au reste.
2. Cas `READY` : lancer un **vrai serveur HTTP local** sur un port attribue par l'OS qui repond
   correctement (200 + contenu attendu) et verifier que la sonde rend `READY` avec sa preuve.
3. Cas `DEGRADED` : le meme serveur repond **200** mais sans le contenu attendu -> `DEGRADED`. C'est
   la preuve que « 200 » n'est pas « READY ».
4. Cas `FAILED` : pointer une sonde sur un **port reellement ferme** -> transport KO -> `FAILED`.
5. Cas `BLOCKED` : un composant dont le role n'est pas demontre — force par une ENTREE CONTROLEE (un
   journal de trace ecrit dans le dossier temporaire du test), JAMAIS en lisant la trace de production :
   un cas `BLOCKED` branche sur le journal reel cesse de tester quoi que ce soit des que le composant
   change d'etat, et il interdit le correctif (l'assertion devient impossible a satisfaire, donc la
   suite de tests doit etre re-ecrite, pas contournee). Ajouter en regard un cas de NON-REGRESSION qui
   LIT la trace reelle — le test ne l'ecrit jamais — et verifie que l'abstention historique ne bloque
   plus. Meme methode pour une dependance reseau : un stub qui rend « quota epuise » prouve le passage
   en `DEGRADED` sans reseau, et un test a part execute la mesure reelle et controle la FORME du
   resultat (champs presents, aucun secret) sans exiger son succes.
6. Agregation : faire coexister les quatre dans UN rapport et verifier l'etat global ; verifier
   aussi que le composant retire de l'architecture n'apparait dans AUCUNE sonde et que chaque
   composant expose ses champs obligatoires.
7. Isoler l'ecriture d'etat : rediriger le fichier d'etat du module vers un dossier temporaire, sinon
   le test gonfle les series d'echecs de production. Relever les SHA avant/apres de la production.

## 5. Mise en service et preuve

- Executer l'entree REELLE de la supervision (la tache planifiee : `schtasks /run /tn "<tache>"`)
  et non seulement le module en direct : verifier `LastTaskResult` et le `timestamp` du rapport.
- **Verifier qu'un nouveau composant est seulement DANS le chemin d'alerte avant d'ecrire « aucune
  alerte parasite ».** Sur un heartbeat ou la notification Telegram est branchee sur les composants
  LEGACY (ports, taches planifiees, fraicheur d'index, orphelins), un composant des nouvelles sections
  ne declenche rien par construction. Le dire comme un fait mesure — fonction d'alerte citee et liste
  des composants qu'elle couvre — et non comme une absence d'anomalie.
- Confirmer la non-regression des lecteurs historiques : les cles d'origine sont toujours la, le
  heartbeat garde son temps d'execution, et l'anti-spam d'alertes n'a pas envoye de message parasite
  (aucune anomalie nouvelle pendant la mise en service).
- Documenter le schema (champ par champ, roles des fichiers d'etat) a cote du module : c'est ce qui
  permet aux lecteurs suivants de ne pas casser le rapport a leur tour.
- Limites a declarer explicitement : composants non supervises, seuils provisoires, sondes profondes
  conditionnelles, et alertes non branchees sur les nouveaux composants si elles ne le sont pas.
