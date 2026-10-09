# Verifier un correctif sans executer ses effets de bord

Cas d'usage : le correctif porte sur un script a ETAT (sonde, moniteur, heartbeat) qui ecrit un
fichier d'etat ou une ligne de base a chaque passage, et la phase en cours interdit toute ecriture.
Il faut pourtant prouver que le correctif marche AVANT de lancer la sonde pour de vrai — sinon la
phase suivante decouvre l'erreur, ou pire, publie un "corrige" qui ne l'est pas.

## Recette

1. **Localiser l'ecrivain, pas le calcul.** Chercher la fonction qui persiste (`_etat_sauve`, `save`,
   `json.dump`, `os.replace`) et remonter a son site d'appel : c'est elle qu'il faut neutraliser.
   Rebind au niveau module : `mod._etat_sauve = lambda d: captures.append(d)`. Le compteur de
   captures est la preuve a rendre ("appele 4 fois, toutes interceptees").
2. **Alimenter avec le VRAI parseur du module**, pas un dict ecrit a la main. Un dict dont les cles
   sont plausibles mais fausses rend un verdict plausible et faux : mesure, un `etats` attendu au
   format `{nom: {"state": …}}` a ete alimente avec le fichier d'etat brut (qui porte `last_state`) —
   resultat, tous les composants "indisponibles" et un `DEGRADED` qui n'existait pas.
3. **Pour remplacer une lecture de base, patcher le module GLOBAL.** Une fonction qui fait
   `import sqlite3` EN LOCAL n'expose aucun `mod.sqlite3` (`AttributeError`) : ce qu'elle appelle est
   `sys.modules['sqlite3'].connect`. Capturer le vrai `connect` AVANT la substitution et le faire
   utiliser par le faux — un faux qui appelle le nom patche recurse a l'infini
   (`maximum recursion depth exceeded`), ce qui se lit comme un bug du code teste alors que c'est
   celui du harnais.
4. **Appeler la VRAIE fonction.** Re-implementer sa logique ne prouve que la lecture qu'on en a.
   Le harnais importe le module (`sys.path.insert(0, <dossier>)`) et appelle la fonction sonde.
5. **Construire un CONTRE-CAS.** Un correctif qui supprime un faux positif peut aussi eteindre une
   alerte reelle : simuler le cas ou le signal DOIT se declencher (les donnees que le controle est
   cense rattraper) et montrer qu'il echoue encore. Sans ce contre-cas, « le correctif marche » et
   « le controle est mort » sont indiscernables — et c'est la seule preuve qui distingue les deux.
6. **Prouver l'absence d'ecriture** par l'empreinte du fichier d'etat avant/apres (`sha256sum`), pas
   par l'intention. Un fichier d'etat rafraichi entre deux mesures par une tache planifiee n'est pas
   votre ecriture : relever l'intervalle de la tache et attribuer explicitement.
7. **Le record retourne peut APLATIR son detail.** Un helper du type `marquer()` fait
   `rec.update(detail)` : les champs se lisent `rec["repli_active"]`, pas `rec["detail"][…]`. Un
   `KeyError: 'detail'` est un bug de harnais, pas un bug du code teste.

## Verification du correctif lui-meme

Le harnais ne sert qu'a rendre la mesure possible ; la preuve est le tableau des scenarios. Enumere les
cas avec leur verdict ATTENDU avant de lancer, et confronte : config reelle, cas ou le faux positif
doit disparaitre, cas ou le signal legitime doit rester, cas ou le controle est cense echouer. Un
scenario qui rend autre chose que l'attendu est un ECART a rapporter tel quel — y compris quand il
accuse le harnais.

## Pieges

- **Un compteur impossible accuse la mesure, pas la cible.** Un `ACE(F)=0` sur un fichier qui en porte
  trois, un total a 1 sur une liste de vingt : suspecter d'abord la construction du chemin ou de la
  boucle du harnais, et refaire la mesure par une autre forme avant de conclure sur la cible.
- **Ne pas confondre "la sonde ecrit l'etat" et "la sonde est autorisee a ecrire l'etat"** : la phase
  de verification precede le GO de la phase qui, elle, ecrit. Le tableau de bord de la phase de test
  finale se lit sur l'etat REELLEMENT ecrit (`--resume`/`--once` de la phase autorisee), pas sur la
  simulation.
- **Un correctif de sonde se documente dans le changelog du sous-systeme concerne**, avec le motif
  exact que la sonde remontait avant (le libelle du faux positif), sinon la correction est
  indetectable dans l'historique du projet.
