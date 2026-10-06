# Verifier une narration avant le lip-sync (les mesures qui trompent)

Le controle « l'audio dit-il ce que dit le script ? » se fait AVANT tout rendu. Trois pieges
coutent des heures et faussent les conclusions ; les contournements sont ci-dessous.

## 1. Tracer le run : chemin, md5, date dans le JSON

Un script de verification prend en argument le chemin de l'audio ET les noms de sortie log/json,
et ecrit dans le JSON `audio`, `audio_md5`, `audio_taille`, `audio_mtime`, plus les arguments
recus. Sans ces champs, deux runs sur deux versions differentes du meme nom de wav se recouvrent :
meme nom de json, deux audios de durees differentes, et les mesures de l'un attribuees a l'autre.
Parametrer au lieu de figer les chemins dans le script, en gardant les valeurs par defaut =
comportement precedent, et nommer chaque run (`--log verif_v3.log --json verif_v3.json`) au lieu
d'ecraser le precedent.

Le consommateur de ce JSON (le script qui calcule la similarite canonique) doit accepter le meme
nom de fichier en argument : sinon il continue de mesurer un ancien run en silence, et le
parametrage du producteur ne sert a rien.

## 2. La presence d'un mot ne se juge pas sur le decodage du fichier entier

Les memes octets se transcrivent differemment selon la fenetre decodee : un mot physiquement
present ressort ABSENT du decodage global. Mesure : « prochain » absent des 294 s decodees,
present dans le decodage cible de [288,9 ; 294,1] s — les deux queues de fichier etaient pourtant
bit a bit identiques.

Methode qui tranche, dans cet ordre :

1. construire la liste des jetons normalises HORODATES — pour chaque mot de la transcription,
   ajouter ses jetons avec l'instant de debut du mot (un mot peut rendre 0, 1 ou 2 jetons :
   « 0,98 » en rend deux, la virgule devenant une espace). Verifier par une assertion que cette
   liste est identique a la normalisation du texte entier, sinon la correspondance
   jeton -> instant est cassee et toutes les fenetres seront fausses ;
2. localiser la phrase-ancres du segment dans cette timeline (appariement glissant,
   `difflib.SequenceMatcher`), et se rabattre sur le premier mot-cle si l'ancre n'est pas
   localisable ;
3. RE-DECODER seulement `[t0 - 2 s, t1 + 3 s]` — extraire les echantillons du WAV, ecrire un
   temporaire, transcrire avec le meme modele et les memes reglages ;
4. ne declarer ABSENT qu'apres cet echec, et dire dans le rapport laquelle des deux voies a
   tranche (« present (decodage global) » vs « PRESENT (decodage cible 288,9-294,1 s) »).

Le controle global seul produit un faux ABSENT ; le controle cible seul ne prouve pas l'absence
d'un mot ailleurs. Faire les deux, et garder un drapeau pour desactiver le cible et comparer
avant/apres.

## 3. La similarite brute n'est pas un verdict

difflib sur jetons normalises compte comme fautes les familles que le TTS et l'ASR ne rendent
jamais de la meme facon :

- sigles epeles : `L L M` -> « lme3 », « l l m » ;
- noms propres et marques : JEV (« j'aime », « jeune GEV »), Laya (« Laia », « j'aime laia »),
  SiYuan (« Si Youane », « du Yann »), GitHub (« Guite-Hub », « g tube »), Chatterbox
  (« Shatterbox »), KokoClone (« coco clone ») ;
- nombres en toutes lettres : « zero virgule quatre-vingt-dix-huit » -> « 0,98 » ;
- composes : Omni Route, protoagent, git clone, point M D, O N N X ;
- le `-s` muet : trier le `s` final des jetons de 4 lettres et plus avant de comparer.

Canonicaliser les DEUX cotes (sequences multi-jetons -> forme unique, puis jetons simples, puis
effondrement des suites de nombres) avant de mesurer. Mesure sur un meme audio : 0,8917 brut ->
0,8981 apres triage du `-s` -> 0,9560 canonique. Ne juger que ce qui reste apres canonicalisation,
et publier les trois chiffres ensemble : un brut sous le seuil annonce ne veut pas dire que
l'audio est mauvais.

Corollaire : la liste « phrases source absentes » par appariement < 0,80 sort la moitie des
phrases d'un texte technique et n'est pas utilisable. La rapporter uniquement avec son
avertissement, ou pas du tout.

## Ce qu'il faut rapporter

Les etendues de reference reellement non appariees (>= 3 mots), les passages ajoutes avec leur
instant, la repetition maximale d'un n-gramme (boucle TTS : un 6-gramme repete deux fois est
normal si le TEXTE source le repete — le verifier dans le texte, pas dans l'audio), la
similarite canonique, et la presence des segments inseres avec la voie de decision pour chacun.
