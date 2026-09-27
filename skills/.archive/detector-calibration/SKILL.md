---
name: detector-calibration
description: "Calibrer un detecteur : faux positifs et controle positif."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [calibration, faux-positifs, scanner, detection, qualite, tests]
    related_skills: [security-audit, code-review, systematic-debugging]
    created: "2026-08-25"
---

# Calibrer et valider un detecteur

Tout outil qui produit des *findings* — scanner de securite, revue de code
statique, monitor de logs, watcher de prix, linter maison — se juge sur deux
choses que « le script tourne sans planter » ne prouve pas :

1. **Le silence n'est pas une preuve.** Un module qui ne remonte rien peut etre
   juste... ou mort. Sans controle positif, on ne sait pas.
2. **Un finding n'est pas un defaut.** Tant que chaque alerte du premier run
   n'a pas ete ouverte une par une, le taux de faux positifs est inconnu.

Ce skill est la procedure pour passer d'un detecteur « qui s'execute » a un
detecteur « en qui on peut avoir confiance ».

## When to Use — quand l'utiliser

- On vient d'ecrire ou d'etendre un module qui emet des alertes / findings
- L'utilisateur dit « corrige les faux positifs », « trop de bruit »,
  « calibre-le », « je ne veux pas d'alertes inutiles »
- Un scan remonte beaucoup d'alertes **de meme forme sur plusieurs cibles**
  (signature quasi certaine d'un artefact d'environnement, pas d'un vrai defaut)
- Un module ne remonte rien et on veut savoir s'il detecte vraiment quelque chose
- Avant de declarer un detecteur « teste », ou de le brancher sur un cron

Pour un bug fonctionnel classique sans notion de finding, utiliser plutot
`systematic-debugging`.

## Procedure

### 1. Ouvrir chaque finding du premier run

Ne jamais conclure sur le compteur (`ELEVE 5`). Extraire la liste complete avec
la preuve de chaque alerte — c'est la seule facon de voir un motif :

```bash
python -c "
import json,glob
d=json.load(open(sorted(glob.glob('reports/*.json'))[-1],encoding='utf-8'))
for x in d['findings']: print(x['severite'],'|',x['titre'],'|',(x['preuve'] or '')[:120])
"
```

**Signal fort** : la meme alerte sur *toutes* les cibles. Un fichier present sur
5 sites sur 5 n'est pas une intrusion, c'est l'environnement de dev.

### 2. Classer chaque alerte en trois seaux

| Seau | Exemple | Traitement |
|---|---|---|
| Signal reel | copie de configuration servie par le web | garder la severite |
| Artefact d'environnement | fichier genere par l'outil de dev local | filtrer par liste nommee |
| Contenu de l'utilisateur | ses propres scripts d'audit a la racine | **degrader**, pas supprimer |

### 3. Trois regles de filtrage qui tiennent dans le temps

1. **Filtrer par generateur, jamais par nom de fichier utilisateur.** Whitelister
   `local-xdebuginfo.php` (produit par l'outil de dev) est sain. Whitelister
   `pre-flight-check.php` parce que c'est « probablement a l'utilisateur »
   masquerait une backdoor portant le meme nom demain.
2. **Filtrer sur la capacite de nuire, pas sur l'inconnu.** Un fichier inconnu
   mais **inerte** (`.md`, `.txt`, `.json`, `.js` non servi comme code) n'est pas
   un risque : ignorer. Un fichier inconnu **executable** au meme endroit reste
   une alerte.
3. **Degrader plutot que supprimer** quand c'est ambigu : passer en MOYEN avec un
   libelle « a confirmer un par un ». Une alerte supprimee est une alerte qu'on
   ne reverra jamais ; une alerte degradee reste auditable.

Toujours **compter les elements filtres** dans le rapport
(`racine_fichiers_inertes_ignores: 5`) : un filtre silencieux devient invisible
et donc indebogable.

### 4. Controle positif — obligatoire

Prouver que le detecteur **se declenche**, pas seulement qu'il se taise.
Construire le controle **en ajout seul**, dans un dossier neuf horodate : rien
n'est supprime, rien de l'environnement reel n'est touche, et le controle est
rejouable a l'identique.

```bash
T="$LOCALAPPDATA/Temp/ctrl_$(date +%Y%m%d_%H%M%S)"   # neuf a chaque fois
mkdir -p "$T"
# 1. copier des entrees SAINES connues (elles ne doivent PAS etre signalees)
# 2. injecter une anomalie par chemin de detection, une seule a la fois
# 3. lancer le detecteur sur $T uniquement
```

Un controle positif reussi coche deux cases :

- **chaque** chemin de detection a produit son finding attendu ;
- les entrees saines laissees intactes **n'ont pas** ete signalees.

La seconde case est celle qu'on oublie : un detecteur qui alerte sur tout
« detecte » aussi les anomalies, sans valeur.

Voir `scripts/positive_control_wp_core.sh` pour un exemple complet et rejouable
(integrite d'un core WordPress, 4 chemins de detection).

### 5. Attribuer une regression de performance avant de l'imputer a son code

Quand un module ralentit, mesurer les sous-commandes **isolement** avant de
soupconner sa propre modification :

```bash
python -c "
import subprocess,time
def chrono(cmd):
    s=time.perf_counter(); subprocess.run(cmd,capture_output=True); return time.perf_counter()-s
print('cmd A : %.3fs'%chrono(['netstat','-ano','-p','TCP']))
print('cmd B : %.3fs'%chrono(['tasklist','/FO','CSV','/NH']))
"
```

`time.perf_counter` dans un sous-processus Python est portable et compare des
sous-commandes de facon fiable, sans dependre d'un utilitaire de chronometrage
present ou non sur l'hote.

Deux optimisations qui reviennent souvent une fois le coupable identifie :

- **import paresseux** : deplacer un import couteux (reseau, parsing) dans la
  fonction qui l'utilise, pour ne pas le payer sur les passes ciblees ;
- **sous-commande paresseuse** : n'appeler l'enumeration couteuse que s'il reste
  reellement un element a qualifier apres les filtres.

## Restitution attendue

L'utilisateur veut des chiffres mesures, pas une intention :

- annoncer le **avant / apres** du calibrage (« 20 alertes ELEVE dont 0 reelle
  -> 3 ELEVE toutes reelles ») ;
- donner les durees reellement mesurees, et **expliquer l'ecart** avec un
  objectif annonce plutot que de le passer sous silence ;
- signaler explicitement ce qui n'a **pas** pu etre prouve, plutot que de
  presenter un chemin non teste comme valide ;
- verifier l'etat existant **avant** de modifier : ne pas reconstruire ce qui
  est deja en place, le confirmer.

## Pieges

1. **Ne pas confondre « 0 finding » et « module valide ».** C'est l'erreur qui
   justifie ce skill : sans controle positif, un module vide passe pour un module
   sain.
2. **Ne pas whitelister pour faire baisser le compteur.** Chaque regle de filtre
   doit avoir une justification causale (« genere par tel outil ») ecrite en
   commentaire a cote de la liste.
3. **Ne pas filtrer une categorie entiere pour un cas.** Les fichiers d'une zone
   « utilisateur » (ex. contenu, plugins, themes) peuvent legitimement manquer ou
   differer : exclure cette zone du decompte, pas le controle entier.
4. **Ne jamais annoncer un finding comme une compromission prouvee.** Un
   detecteur produit des *signatures* : formuler « signature de X, a verifier ».
5. **Ne pas construire un controle positif par suppression/restauration** de
   donnees reelles. Un dossier neuf horodate en ajout seul est plus sur, plus
   rejouable, et ne risque pas d'abimer l'environnement de l'utilisateur.
6. **Verifier les imports reellement disponibles** avant d'utiliser un symbole :
   `from datetime import date` ne donne pas `datetime.now()`. Compiler le fichier
   (`python -m py_compile`) apres edition attrape ca immediatement.

## Verification

```bash
# 1. le detecteur compile
python -m py_compile chemin/vers/detecteur.py

# 2. controle NEGATIF : sur une cible saine, aucune alerte parasite
python detecteur.py --cible <cible_saine>

# 3. controle POSITIF : sur la cible fabriquee, chaque chemin se declenche
bash scripts/positive_control_wp_core.sh     # exemple fourni

# 4. non-regression : un module cible ne doit executer QUE lui-meme
python detecteur.py --modules <un_seul> && \
  python -c "import json,glob; print(json.load(open(sorted(glob.glob('reports/*.json'))[-1],encoding='utf-8'))['contexte']['perimetre']['modules'])"
```

## Fichiers lies

- `references/wp-integrity-case-study.md` — cas reel chiffre : 20 faux positifs
  ELEVE ramenes a 3 alertes reelles, avec les trois regles appliquees.
- `scripts/positive_control_wp_core.sh` — controle positif rejouable, non
  destructif, 4 chemins de detection.
