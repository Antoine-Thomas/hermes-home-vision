# Surveillance d'un run d'inference de plusieurs heures (GPU 8 Go, Windows)

Un rendu de 5 minutes occupe le GPU plusieurs heures (~47x le temps reel, mesure sur 8 Go a 256 px).
La session qui l'a lance peut etre comprimee, rechargee ou fermee avant la fin : tout ce qui doit
survivre vit dans des FICHIERS et dans des notifications envoyees depuis le processus de
surveillance lui-meme.

## 1. La commande, avec des chemins ABSOLUS

```
venv/Scripts/python.exe -u -m scripts.inference \
  --unet_config_path configs/unet/stage2.yaml \
  --inference_ckpt_path checkpoints/latentsync_unet.pt \
  --inference_steps 20 --guidance_scale 1.5 --enable_deepcache \
  --video_path tests/.../source_loop_344.mp4 \
  --audio_path C:/Users/.../data/xtts/audio_v5.wav \
  --video_out_path tests/.../sortie_latentsync_v5.mp4 \
  --temp_dir temp_v5
```

- `-u` : sans lui la sortie est bufferisee et la progression reste invisible.
- **Le chemin de l'audio doit etre absolu.** Un chemin relatif se resout contre le dossier du depot
  du modele, pas contre le dossier d'ou l'on lance : un `../../data/xtts/...` par ailleurs correct
  echoue en `RuntimeError: Audio path not found`.
- **`--temp_dir` neuf a chaque tentative** : un run tue laisse un `temp/video.mp4` (la source
  pre-traitee) ; un dossier neuf evite de melanger les etats sans avoir a supprimer l'ancien.
- Le dossier de sortie doit exister avant le lancement.

### 1bis. Verifier que la RAM hote peut contenir la video ENTIERE

L'inference decode toute la video en memoire hote, a la resolution de la SOURCE, avant de commencer a
generer. Budget a calculer AVANT de lancer : `frames x largeur x hauteur x 3` octets.

Mesure du 20/09 sur 1080p : 8600 x 1920 x 1080 x 3 = 53 Go theoriques, 49,0 Go reellement tenus par
le processus. Sur une machine de 64 Go il restait 2,6 Go libres et le fichier d'echange etait a 39 Go
utilises sur 82 alloues : pagination continue. Consequence mesuree : 127 s par iteration au lieu des
~25-30 attendues (538 iterations, ~13 h 30 projetees contre 4 h 30 annoncees), et une cadence qui se
degrade au fil du run.

Si le budget depasse la RAM libre : SEGMENTER avant de lancer (segments multiples du cycle ping-pong,
audio decoupe sur des echantillons exacts). Un run de 5 minutes en 1080p lance d'un seul bloc ne tient
pas sur cette machine — decouvrir le mur a la 12e heure coute le run entier.

Verifier aussi la VRAM du bureau : sous Premiere Pro le pic est monte a 7877 / 8192 Mio, et un working
set qui deborde passe par le WDDM et coute le meme facteur.

## 2. Lancer depuis un MONITEUR, jamais l'inverse

Un script Python qui `Popen` l'inference (stdout+stderr fusionnes, `text=True`, `bufsize=1`) et lit
sa sortie dans un thread. C'est la seule facon d'obtenir une progression REELLE : le pipeline affiche
une barre tqdm sur sa boucle d'inference, entouree des phases de detection et de restauration des
visages.

```
# ancrer sur la DESCRIPTION de la barre, jamais sur « la derniere vue »
barre    = re.compile(r"Doing inference\.\.\.:\s+(\d+)%\|.*?\|\s*(\d+)/(\d+)")
echeance = re.compile(r"\[([^,\]]+),\s*([^,\]]+)\]")       # "1:02:03<1:23:45, 1.02it/s"
```

- **Un motif generique (`(\d+)%\|.*?\|\s*(\d+)/(\d+)`) lit la MAUVAISE barre.** Le pipeline en
affiche plusieurs : la boucle d'inference une fois par iteration, et des barres secondaires (ici
`Sample frames: 16`, 20 elements) environ 21 fois par iteration. Un motif sans description attrape
donc presque toujours une barre secondaire et annonce 100 % (20/20) alors que le vrai travail est a
88 % (474/538). Ancrer sur le texte de la barre ET **valider le denominateur** : un total de 20 pour
une video de 8600 frames signifie qu'on lit la mauvaise barre, pas que le run est fini. Un statut qui
affiche 100 % se recoupe avec le log avant d'etre cru ou notifie.
- Le fichier de sortie n'apparait qu'a la fin : ne pas en deduire la progression.
- Le dossier temporaire ne contient que la source pre-traitee, aucune frame generee.
- La phase de detection des visages tourne plusieurs minutes sur toute la video SANS pourcentage (sa
  barre n'a pas de description) : afficher la phase, pas seulement le pourcentage, sinon on croit a
  un blocage (voir la regle « ne pas conclure bloque sur un log fige » du skill 8 Go).

## 3. Echantillonnage, seuils, arret d'urgence

```
nvidia-smi --query-gpu=memory.used,temperature.gpu --format=csv,noheader,nounits
```

- **Toutes les 30 s**, pas toutes les 2 s : sur 4 h 30 un echantillonnage serre ne sert a rien et
  pese sur les I/O.
- Mesure de reference sur cette machine : 6141 Mio de VRAM pic en phase de detection, 54 degC, avec
  2,9 Go deja pris par le bureau.
- **Arret d'urgence** : VRAM pic > 8050 Mio, 3 events `nvlddmkm` ID 153 consecutifs, `Kernel-Power` 41.
- **`Kernel-Power` 41 est un reboot** : le moniteur ne peut pas agir dessus (il est mort avec la
  machine). Ce controle sert a qualifier l'echec apres coup, pas a arreter quelque chose.
- Verifier les events **toutes les 5 min**, pas a chaque echantillon (requete couteuse).

## 4. Le journal d'evenements Windows

`wevtutil` sort en **UTF-16** : `grep` repond `Binary file matches` et un decodage naif est illisible.
Decoder explicitement (`utf-16-le` cote Python, `tr -d '\0'` en shell).

```
wevtutil qe System /q:"*[System[EventID=41]]" /c:5 /rd:true /f:text
wevtutil qe System /q:"*[System[(EventID=153) and (Provider[@Name='nvlddmkm'])]]" /c:5 /rd:true /f:text
```

**Compter les events presents au demarrage et les soustraire** (la reference se lit AVANT le Popen).
Un moniteur qui part de zero compte un event historique comme nouveau et fait monter son propre
compteur d'arret d'urgence.

## 5. Ce qui survit a la session

1. **Un JSON de statut reecrit a chaque echantillon** : phase, pourcentage, avance/total, ETA, VRAM
   pic, temp max, compteurs d'events, debut, fin, arret, erreur. Une session ulterieure reprend le
   suivi en le relisant, sans rien deviner.
2. **Le moniteur notifie lui-meme**, par HTTP simple depuis son propre processus : au lancement
   (heure de debut + estimation), toutes les 30 min (progression), a la fin (duree, VRAM pic, temp
   max, events, chemin et taille de sortie), et sur arret d'urgence (cause + derniere frame).
3. **Un cron watchdog independant** (`no_agent=True`, `deliver='telegram:<chat>'`, toutes les
   15 min) qui ne parle QUE si quelque chose va mal : statut fige depuis plus de ~12 min, arret
   d'urgence enregistre, VRAM au-dessus du seuil, `nvidia-smi` injoignable, ou run termine. En
   `no_agent`, une sortie **vide n'envoie rien** : c'est le motif watchdog, et c'est ce qui evite de
   doubler les notifications du moniteur. Attention a la mise en garde du SKILL.md sur
   `deliver='telegram'` pour les taches non surveillees : garder le watchdog muet-par-defaut pour que
   la passerelle ne delivre que sur une vraie alerte.

   **Variante « rapporteur de progres » (run de ~1 h 20, mesuree le 22/09)** : quand l'utilisateur veut
   des points d'avancement reguliers, le meme script cron peut rapporter au lieu de se taire — a
   condition de **dedoublonner par un fichier d'etat** (derniere ligne envoyee). Sans ce fichier, un
   tick toutes les 20 min renvoie la meme phrase et le watchdog devient du bruit. Le progres se lit de
   facon fiable en **comptant les fichiers de sortie de l'etage courant** (`ls sortie | wc -l`) plutot
   qu'en analysant le log : le script d'etage n'imprime sa ligne de progres que tous les 10 elements, et
   rien du tout avant le dixieme, donc un log sans nouvelle ligne n'est pas un blocage. Trois regles qui ont rendu le script utile : rapporter seulement si la ligne a change ; alerter si aucun
   nouveau fichier depuis ~20 min ; annoncer la fin UNE fois (etat « deja annonce »), puis rester muet.
   Le meme etat sert a limiter la tache (`repeat=6` pour 1 h 20) pour qu'elle ne survive pas au run.

## 6. Pieges payes

- **Ne jamais redemarrer le moniteur en cours de run** : tuer le moniteur peut laisser l'inference
  orpheline (elle continue d'ecrire sa sortie), et un second moniteur lance une SECONDE inference —
  deux modeles dans 8 Go, c'est le reset GPU. Si le moniteur est mal configure, le laisser finir.
- **Verifier que les fichiers de suivi sont bien la ou on les attend avant de rendre la main.** Une
  accolade parasite dans un argument cree silencieusement un dossier au nom decale (`..._v5}`) : le run
  lui-meme utilise ses propres arguments et se passe bien, mais le journal et le statut atterrissent
  ailleurs. S'ils ne sont pas la, les chercher (`find . -name ...`) au lieu de conclure que le
  moniteur n'ecrit pas.
- **Ordre des operations** : lire la reference des events et envoyer la notification de lancement
  AVANT d'entrer dans la boucle — une requete `wevtutil` peut prendre une minute, et une notification
  qui arrive deux minutes apres le lancement n'indique plus la meme heure de debut.
- **Tuer un seul processus** : jamais `taskkill /IM python.exe` (regle du skill 8 Go) ; viser le PID.

## 7. Le canal de notification doit etre VERIFIE, pas suppose

Un moniteur peut tourner parfaitement pendant 12 h sans avoir jamais rien envoye : c'est arrive, et
c'est ce qui fait conclure a tort que le run est mort.

- **Jamais de HTML pour du texte machine.** `parse_mode=HTML` + une chaine produite par le programme
  (ETA de tqdm `01:55<00:00`, message d'erreur, extrait de log) = un `<` brut pris pour une balise et
  un **HTTP 400 sur CHAQUE envoi**. Soit echapper `<`, `>`, `&`, soit ne pas mettre de parse_mode du
  tout — du texte simple suffit pour un suivi.
- **Le message de lancement qui passe ne prouve rien.** Son contenu differe de celui des rappels :
  c'est le rappel qui porte l'ETA, donc le `<`. Valider le texte RECURRENT, pas seulement le premier.
- **Journaliser le resultat de chaque envoi** (succes ou echec, avec le code HTTP). Un moniteur qui ne
  peut pas prouver qu'il a notifie est un moniteur aveugle.
- **Un watchdog « muet sauf probleme » ne voit PAS un canal mort.** Ici il verifiait la fraicheur du
  statut — donc la liveness du moniteur — et restait muet pendant que 100 % des envois echouaient.
  Correctif : le notifieur ecrit un battement de coeur (horodatage du dernier envoi REUSSI) et le
  watchdog alerte si ce dernier succes date de plus de ~2x l'intervalle de rappel. Surveiller le
  moniteur ne suffit pas, il faut surveiller la LIVRAISON.
- **Le chemin de livraison du watchdog lui-meme n'est pas teste tant qu'il n'a pas parle** : un
  watchdog muet depuis sa creation n'a jamais exerce `deliver`. Le faire parler une fois avant de
  s'y fier pour une nuit entiere.

## 8. Diagnostiquer « le run s'est arrete sans notification »

Dans cet ordre, sans rien relancer :

1. **Le log grossit-il ?** `stat -c %s` a 20 s d'intervalle : +300 octets en 20 s = le run est vivant.
   C'est la preuve de vie ; l'absence de notification n'en est pas une.
2. **Le fichier de sortie n'existe pas ?** Normal : il n'apparait qu'a la toute fin. Son absence ne
   prouve rien, ni dans un sens ni dans l'autre.
3. **Le statut JSON peut mentir** (§2) : lire la progression dans le log
   (`tr '\r' '\n' < log | grep "Doing inference" | tail -1`).
4. **Le processus est-il la ?** `nvidia-smi --query-compute-apps` et `tasklist` affichent
   l'INTERPRETEUR DE BASE : un python de venv apparait comme `Python310`, pas comme le venv. Un
   `grep venv` sur la liste des processus ne trouve rien et fait croire a un arret. Passer par le PID
   et la ligne de commande.
5. **Outils Windows** : `wmic` n'existe plus (Windows 11). Utiliser PowerShell —
   `Get-CimInstance Win32_Process -Filter "name='python.exe'" | Select ProcessId,CommandLine`,
   `Get-CimInstance Win32_OperatingSystem` (RAM totale/libre),
   `Get-CimInstance Win32_PageFileUsage` (echange), `Get-CimInstance Win32_Processor` (charge CPU).
6. **Events** : comparer au compteur de reference pris avant le lancement, en decodant l'UTF-16 (§4).
   Deux `nvlddmkm` 153 anterieurs au lancement ne sont pas des events du run.
7. **Qui consomme ?** `Get-CimInstance Win32_Process` trie par WorkingSetSize : c'est ce qui attribue
   le ralentissement (ici 49 Go pour l'inference, 2,6 Go libres sur 64).

Rapport a produire : cause probable (crash GPU / traceback / session fermee / arret propre / canal de
notification), ressources mesurees, recommandation. Quand le run est a 88 % avec ~2 h restantes,
laisser finir bat toujours un redemarrage a zero.
