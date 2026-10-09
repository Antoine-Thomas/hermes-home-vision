# Chatterbox — narration FR clonee (chatterbox-tts 0.1.7)

Moteur de narration longue en remplacement d'XTTS : sortie 24 kHz mono, clonage par
`audio_prompt_path`. Ce fichier porte l'API, la recette de sonde, les mesures et les pieges ; les
regles always-on sont dans SKILL.md.

## Environnement

- Venv dedie : `C:\Users\searc\AppData\Local\hermes\data\chatterbox\.venv` (torch 2.6.0+cu124, cuda 12.4).
- Voix de reference : `data\xtts\voix_reference.wav` (24 kHz mono).
- `ModuleNotFoundError: No module named 'pkg_resources'` au chargement de `perth` (watermarker) =
  setuptools >= 81. Correctif : `uv pip install --python <venv>/Scripts/python.exe "setuptools<81"`
  (84.0.0 -> 80.10.2, `Required-by: torch`). Sans lui l'import de perth laisse le watermarker a
  `None` et `from_pretrained` meurt sur `TypeError: 'NoneType' object is not callable`.
- Un `UserWarning: pkg_resources is deprecated` subsiste apres le correctif : benin.
- Mesures du chemin valide : LOAD_S 13-16, VRAM pic 3 881 Mo, ~9-12 s par phrase courte,
  `MODEL_VARIANT v2`.
- Variante **v3** (clone master) : `data\chatterbox_v3\.venv` (torch 2.6.0+cu124),
  `MULTILINGUAL_T3_MODELS` present et `from_pretrained(device="cuda", t3_model="v3")` accepte.
  Mesures : LOAD_S 11,6, SR 24 000, VRAM pic 4 461 Mo, **310 s de GPU pour 11 segments / 268,0 s
  d'audio** (268,0/420 -> `atempo` 0,638 pour une cible de 7 min).

## API minimale

```python
import torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
model = ChatterboxMultilingualTTS.from_pretrained(device="cuda")   # pas de t3_model dans 0.1.7
wav = model.generate(texte, language_id="fr", audio_prompt_path=REF)
ta.save(out, wav, model.sr, encoding="PCM_S", bits_per_sample=16)   # model.sr = 24000, mono
```

Verifier la variante plutot que la supposer :
`"t3_model" in inspect.signature(ChatterboxMultilingualTTS.from_pretrained).parameters`.

## Recette de sonde (avant toute narration longue)

1. Choisir les JETONS RISQUES : nombres, ports, URL, noms composes, acronymes espaces.
2. Une phrase courte par graphie candidate, toutes dans UN SEUL processus (chargement du modele
   13-16 s contre ~9-12 s par generation). Ecrire un WAV par sonde et un JSON
   (tag, texte, duree, octets, sha256, forcages d'EOS) que le verificateur relit — le JSON evite de
   rejouer les generations pour re-lire les resultats.
3. Transcrire chaque WAV avec faster-whisper `medium`, `device="cpu", compute_type="int8"` (le venv
   `hermes-agent` n'a pas de cublas exploitable), `language="fr", beam_size=5`.
4. Juger sur quatre axes, pas sur la similarite seule :
   - similarite `difflib.SequenceMatcher` sur texte normalise ;
   - mots de CONTENU manquants (liste de mots vides a part) — c'est ce qui detecte la fin avalee ;
   - mots EN TROP (hallucination) ;
   - chaque jeton technique present sous AU MOINS une graphie acceptee
     (`8 200` | `8200` | `huit mille deux cents`).
5. Normalisation qui rend deux graphies comparables : NFD, suppression des diacritiques
   (categories Unicode `Mn`), minuscules, tout non `[a-z0-9]` -> espace, espaces multiples ecrases.
   C'est ce qui fait que `Yüan` et `yuan` se comparent.
6. Un ecart purement morphologique (`indexe` transcrit `index`) est un PASS : le compter comme echec
   fabrique un faux KO et fait reecrire un texte bon.

## Mesures (a citer, elles evitent de refaire les tirages)

| Sonde | Attendue | Transcription Whisper medium | Sim. | Verdict |
|---|---|---|---|---|
| RAG + port | `Le RAG, sur le port 8 200, indexe mes notes.` | `Le rag sur le port 8200, index mi-note.` | 0,923 | jeton OK, fin avalee |
| Si Yuan + port | `Si Yüan, sur le port 6 806, c'est mon Obsidian.` | `Si du Yen sur le porc si croisant 6, c'est mon obsidiant.` | 0,768 | KO, nombre perdu |
| URL | `GitHub point com slash Antoine Thomas slash hermes tiret home tiret vision.` | `Jtube.com slash Antoine Thomas slash erme-homme-vision` | 0,797 | KO |
| RAG sans port | `Le RAG local indexe mes notes, sans aucune clé d'API.` | `Le rag local index mes notes sans aucune clé d'api.` | 0,990 | OK |
| Si Yuan sans port | `Si Yüan, c'est mon Obsidian : une base Markdown, un second cerveau.` | `Si Yuan, c'est mon obsidian, une base Markdown, un second cerveau.` | 1,000 | OK |
| URL, 2e tirage | (meme texte) | `Jtube.com slash Antoine Thomas slash erme-homme-vision` | 0,797 | KO reproductible |

Ce qui s'en deduit :

- retirer le port a suffi a reparer « Si Yüan » (`Si du Yen` -> `Si Yuan`) sans toucher au trema :
  la phrase courte isolee et le nombre etaient les causes, pas la graphie ;
- l'URL echoue deux fois a l'identique — ce n'est pas un tirage malheureux, c'est le passage entier ;
- `point com` se reduit proprement a `.com` : ne pas le corriger ;
- « slash » et « Antoine Thomas » passent toujours.

## Forcage d'EOS et troncature

```python
import logging
class ForceCounter(logging.Handler):
    def __init__(self):
        super().__init__(); self.n = 0
    def emit(self, record):
        m = record.getMessage()
        if "forcing EOS" in m or "repetition of token" in m: self.n += 1
logging.getLogger().addHandler(ForceCounter()); logging.getLogger().setLevel(logging.WARNING)
```

Present sur 3/3 des sondes des deux series (1 a 2 fois chacune, meme jeton repete), y compris sur les
WAV qui transcrivent parfaitement : **signal de risque, pas preuve de defaut**. La preuve de
troncature est ailleurs — le DERNIER mot de contenu attendu disparait ou s'abime. Comparer
l'horodatage du dernier segment Whisper a la duree du WAV ne detecte PAS ce cas.

## Ralentissement (ffmpeg atempo)

```bash
ffmpeg -i ANIMA_narration_chatterbox.wav -filter:a "atempo=0.79" ANIMA_narration_chatterbox_7min.wav
```

**Calculer le facteur, ne jamais le fixer a priori** : `atempo = duree_mesuree / duree_cible`.
**Le debit des sondes courtes n'est pas celui de la narration** : 128 mots/min mesures sur des phrases
isolees (dispersion 85-151) contre **187 mots/min sur la narration complete** (921 mots -> 294,9 s).
L'extrapolation depuis les sondes annoncait 7 min 17 s de brut et un `atempo` quasi inutile ; la mesure
reelle a donne 4 min 55 s et un `atempo` de **0,702**. Toujours partir de la duree du WAV concatene.
Signaler l'ecart : -30 % de debit s'entend. Apres ralentissement, re-transcrire avec Whisper pour
verifier que la diction tient — un atempo agressif degrade la reconnaissance sans que ca s'entende a
l'oreille (mesure : similarite globale 0,823 avant, 0,809 apres).

## Narration complete — architecture qui tient et resultats mesures

Chaine executee sur 11 segments / 921 mots (`_work_2c/run_narration_chatterbox_v2.py`) :

1. Decoupage en amont, texte jamais modifie, integrite verifiee en re-concatenant les segments et en
   comparant au texte source. Cible 6-12 phrases / 75-80 mots.
2. UN SEUL processus pour toute la generation (le chargement du modele coute 13-16 s, non rejouable
   11 fois) : un WAV par segment, plus un JSON ecrit a chaque segment (duree, octets, sha256,
   forcages d'EOS, VRAM pic).
3. UNE SEULE transcription Whisper groupee pour tous les segments (`whisper_batch2.py <modele> <wav...>`
   -> JSON sur stdout) : un appel par segment recharge le modele CPU a chaque fois.
4. Regeneration des KO en un lot, puis UNE SEULE re-transcription groupee des reprises.
5. Assemblage avec le module `wave` (24 kHz mono 16 bits), `atempo` ffmpeg, puis 16 kHz mono pour
   SadTalker **a partir du master ralenti** — un 16 k derive de la base n'a plus la bonne duree.

**Le poste de cout est le CPU, pas le GPU** : Whisper `medium` CPU transcrit a ~1x la duree de
l'audio (294,9 s en ~290 s), quand la generation GPU tient 11 segments en 10 min. Deux passes de
transcription dans un seul appel terminal ont depasse le plafond de l'outil (~420 s) et le processus
a ete tue avant d'ecrire son rapport : lancer les passes longues en tache de fond (`notify=true`) et
faire ecrire chaque artefact sur disque des qu'il est pret.

### Resultats du tirage (a citer pour ne pas refaire les 30 min de GPU)

| Segment | Prise 1 | Prise 2 | Retenue | Jetons critiques absents |
|---|---|---|---|---|
| 01 (75 mots) | 0,954 | 0,940 | 0,954 | github |
| 02 (75) | 0,957 | 0,879 | 0,957 | laya |
| 03 (76) | 0,787 | 0,813 | 0,813 | jev, laya, siyuan, memory.md, user.md |
| 04 (78) | 0,559 | 0,710 | 0,710 | siyuan, skills hub |
| 05 (77) | 0,881 | 0,952 | 0,952 | aucun |
| 06 (80) | 0,805 | 0,781 | 0,805 | jev |
| 07 (81) | 0,848 | 0,789 | 0,848 | anima, laya, onnx, fail open, regex |
| 08 (77) | 0,852 | 0,917 | 0,917 | laya, xtts |
| 09 (79) | 0,955 | 0,929 | 0,955 | kokoclone, chatterbox |
| 10 (76) | 0,877 | 0,880 | 0,880 | siyuan, chatterbox |
| 11 (147) | 0,708 | 0,648 | 0,708 | omni route, github |

5 segments sur 11 atteignent 0,90 ; **1 seul passe le verdict complet** (similarite ET jetons).
Similarite globale 0,823 (base) / 0,809 (apres ralentissement). Moyennes : prise 1 = 0,835,
prise 2 = 0,840 — regenerer ne vaut rien en moyenne.

### Jetons que Chatterbox v2 casse systematiquement (sur les deux prises)

| Attendu | Transcrit |
|---|---|
| JEV | `Jeff`, `Jev`, `Gev`, `J.E.V.` |
| Laya | `Leia`, `Laïa`, `L.A.I.A.` |
| Si Yüan | `Siguant`, `C U A N`, `6 UAN` |
| le RAG | `l'oracle local`, `L.A.R.A.G.`, `ORAG`, `l'AuraG` |
| Chatterbox | `Shatterbox` |
| Kokoclone | `Coco clone` |
| GitHub | `Jtube` (et `Jclone` pour `git clone`) |
| Omni Route | `OmniRoot` |
| L L M | `LLME`, `LLMS`, `LLME3` |
| ONNX | `Onux` |
| Anima | `AnimAz`, `NIA`, `UNIA` |
| XTTS | `XT` |
| fail open / repli regex | `file open` / `re-pirogex` |
| MEMORY.md, USER.md | `mémoire point, monsieur d'usé point monsieur d'` |

Ces jetons ne se reglent ni par un tirage supplementaire, ni par le labo de graphies d'XTTS : mesure
faite, respeller en phonetique DEGRADE (voir la section suivante ; `references/french-diction-tricks.md`
decrit le labo XTTS, il ne s'applique PAS ici). Voies qui restent : reformuler la phrase, retirer le
jeton du texte parle, raccourcir le segment, ou changer de moteur.

### Reecriture phonetique ciblee — ce que Chatterbox en fait (mesure, ne pas refaire)

Tentative : respeller les termes techniques avant synthese (`JEV` -> `Ji-E-Vé`, `Si Yüan` ->
`Si You-an`, `Omni Route` -> `Omi-Raoute`, `Anima` -> `A-nima`, `L L M` -> `Èle-Èle-Ème`,
`GitHub` -> `Guit-Hub`, ...), les 11 segments regeneres en v3. Resultat : **moyenne des similarites
0,856 -> 0,839** et verdict complet **2/10 -> 1/11** (meme metrique recalculee sur les deux jeux de
transcriptions).

| Terme respelle | Rendus obtenus | Rendus AVANT la reecriture |
|---|---|---|
| `Ji-E-Vé` | `J V` (x3), `JLV`, `J.E.V` | `jev` (correct), `Gev` |
| `Si You-an` | `C-U-N` (x2) | `shiyuhan`, `6 UAN`, `siyuan` |
| `Omi-Raoute` | `au miraout` (x2), `Omira ou Turag` | `OmniRoute` (correct) |
| `La-ya` | `l'aia`, `layar` | `l'aya`, `Laïa`, `Leia` |
| `X-T-T-S` | `xts` | `xtets`, `XT` |
| `Obsidiane` | `obsidiane locale` (correct) | `obsidion`, `obsidiant` |
| `Èle-Èle-Ème` | `LLM` | `LML`, `LLME` |
| `règle expresse` (phrase reformulee) | `regle express`, `repli` -> `repis` | `fail open` -> `faille open` |

Ce qui s'en deduit :

- respeller un sigle avec des tirets fait **epeler** le modele : `Ji-E-Vé` -> `J V`, et `Si You-an` ->
  `C-U-N` (des lettres a la place des syllabes) ;
- les deux graphies qui aident portaient deja une forme prononcable d'un seul tenant (`Obsidiane`,
  `Èle-Èle-Ème`) : la regle n'est pas « respeller », c'est **une syllabe d'un seul mot ou rien** ;
- la reecriture change le tirage du segment ENTIER : `trois piliers, JEV` (juste au tirage precedent)
  est devenu `3 PIDs, JLV et`, une phrase a ete ajoutee en fin de deux segments, et le segment long a
  perdu ~35 mots (27,2 s pour 145 mots contre 40,0 s au tirage precedent) ;
- classer les KO par NATURE avant de conclure : sur 11 segments, 2 etaient des artefacts de metrique
  (0,970 avec un seul jeton absent ; 0,821 avec zero jeton absent — Whisper ecrit `1 / 2 / 4 / 5` en
  chiffres et fait chuter le score), et le seuil de 0,90 contre le texte d'origine est inatteignable
  pour un segment truffe de nombres et de sigles.

### Trois defauts qui ne sont pas de prononciation

- **Boucle de repetition** : un segment a invente `Niveau 5, le skill hub... Niveau 6, le skill hub...`
  absent du texte, et le segment long a repete quatre fois « a vraiment la chaine » avec les phrases
  reordonnees. Une reprise ne corrige pas une boucle : reduire la longueur du segment.
- **Perte silencieuse d'un item de liste** : le « Trois » du recapitulatif a disparu. Un controle par
  jetons critiques ne le voit pas — lire la transcription du segment fautif, pas seulement son score.
- **Contenu perdu ou ajoute, invisible au score de similarite** : mesurer le rapport mots/seconde de
  chaque segment (base : 2,6-3,6 mots/s). 5,33 mots/s avec un transcript plus court que la reference =
  des mots manquants ; un transcript plus long = une phrase inventee en fin de segment (observe :
  `Merci d'avoir regardé cette vidéo !`, `Le problème, il hallucinait sur le français.`).

## Narration Witcher 3 (96 segments / 2 703 mots) — mesures du 07/10/2026

Chaine : segments de 200-250 caracteres (moyenne 168, soit ~28 mots) issus du texte brut, un WAV
par segment dans UN seul processus, `ffmpeg -f concat -c copy`, puis
`loudnorm=I=-16:TP=-1.5:LRA=11 -ar 48000 -ac 1`.

| Mesure | Valeur |
|---|---|
| LOAD du modele | 11,9 s |
| VRAM pic (segments de 200-250 car) | 4 802 Mo / 8 192 |
| GPU total, 96 segments / 1 191,9 s d'audio | 2 433,4 s (40 min 33 s) |
| Debit mesure | 2,36 mots/s = **140,9 mots/min** |
| Durc totale | 1 150,88 s = 19,181 min a 48 kHz mono |
| Silence de tete / de queue (fichier assemble) | 0,106 s / 0,010 s |
| RMS / crete / echantillons ecretes | -15,87 dBFS / 0,8415 / 0 |

- **Chatterbox ne padde PAS la queue de ses segments, contrairement a XTTS.** Sur 96 segments :
  silence de queue median **15 ms**, max 0,531 s, total 7,5 s sur 1 191,9 s (**0,6 %**). Le concat
  `-c copy` est donc utilisable tel quel, **aucun trimming n'est necessaire** — ne pas transposer le
  piege XTTS des 575 ms par jointure a Chatterbox.
- **Planifier a ~140 mots/min, pas 150.** L'estimation a 150 mots/min annoncait 18,0 min ; la mesure
  reelle donne 19,2 min (2 703 mots). Un script cale sur 15 min a 150 mots/min sort a ~19 min. Verifier
  le nombre de mots AVANT de lancer 40 min de GPU, pas apres.
- **Le detecteur mots/s attrape les tirages qui trament, et il est gratuit.** Mediane 2,30 mots/s
  (dispersion 1,66-3,17) ; 2 segments sortis a 0,93 et 1,02 mots/s etaient des tirages qui trainaient,
  avec de la PAROLE CONTINUE (0 silence interne, RMS -15,8 dBFS) — donc ni un probleme de silence, ni
  un debit lent legitime.
- **Re-tirage d'abord, decoupage ensuite — dans cet ordre et mesure a chaque fois.** seg 026
  (1,02 -> 2,16 mots/s, 40,00 s -> 18,96 s, garde) ; seg 007 a re-traine (0,93 -> 0,82, tirage ecarte)
  et a ete **coupe a la frontiere de phrase** : 0,93 -> **2,13 mots/s**, 35,44 s -> 15,48 s.
  Un tirage qui traine DEUX fois de suite est le texte/le tirage, pas la chance.
- **Recoller les deux moities en UN SEUL fichier de segment** (module `wave`, memes parametres) quand
  l'indexation est deja figee : un segment insere en fin de plan se retrouverait a la fin de l'audio.
  Le nom de fichier et l'index restent ceux du plan, `concat.txt` reste valide.
- **74/96 segments ont force l'EOS au moins une fois** (87 forcages au total, max 2 par segment) — y
  compris des segments qui passent : confirme que c'est un signal de risque et non une preuve de
  defaut. 10 segments sont legerement sous la bande saine (1,66-1,99 mots/s) : c'est du rythme, pas
  un tirage a refaire, le decrochage net se joue sous 1,1 mots/s.

## Script TTS pre-traite (v3, 73 segments / 2 112 mots) — mesures du 07/10/2026

Script ou les acronymes sont ECRITS EN PHONETIQUE avant synthese (« R T X », « D L S S »,
« C D Projekt Red », « mille quatre cent quarante p », « vingt-quatre gigaoctets de memoire vive »),
segments de 200-250 car (moyenne 170,3), integration verifiee par re-concatenation ET par multiset de
caracteres (0 perdu, 0 ajoute). GPU 2 117 s pour 932,0 s d'audio, puis 15 segments retouches.

| Mesure | Valeur |
|---|---|
| Duree finale | 859,88 s = **14,331 min** (cible 13-17) |
| Debit mesure | 147,4 mots/min |
| Sortie | 48 kHz mono pcm_s16le, 82 548 558 o |
| RMS / crete | -15,99 dBFS / 0,8414 (-1,50 dBFS) / 0 ecretage |
| Silences internes >= 0,30 s | 85, soit 41,16 s (4,79 %) |
| Forcages d'EOS | 66/73 segments, 88 forcages |

### Ce que le moteur rend des graphies epellees (verifie par Whisper `medium` sur 26 segments)

| Graphie demandee | Rendu | Verdict |
|---|---|---|
| `R T X` | `RTX` (7 segments sur 8) ; `eart` sur 1 | rendu en lettres |
| `G T A O` | `GTA O` | rendu |
| `Direct X douze` | `direct X12` | rendu |
| `C D Projekt Red` | `cd projekt red` / `CD Projekt, Red` | rendu apres re-tirage ; 1 segment en `cd project rud` |
| `G O G` | `Geo, je` -> `gog` apres re-tirage | rendu apres re-tirage |
| `D L C` | `DLC` / `de lc` | rendu |
| `P S cinq` | `PS5` | rendu |
| `V R R` | `VTR Heure` -> `VRR` / `vr air` | partiel |
| `P S S R` | `PSS` / `PS1 R` / `ps1 air` | **partiel, le R se perd** |
| `D L S S` | `deux LSS` / `dls` / `2 lss` sur les 4 segments ou il apparait | **defaut systematique : le D sort en « deux »** |
| `trente-neuf dollars quatre-vingt-dix-neuf` | `39,99 $` | rendu (Whisper renormalise) |
| `vingt-quatre gigaoctets de memoire vive` | `24 Go de memoire vive` | rendu |
| `mille quatre cent quarante p` | `1440p` / `1440 pas` | rendu |
| `i sept treize mille sept cents K` | `i7 13700K` / `Ni7 13700K` | rendu |

- **Un echec repete sur TOUS les segments est la graphie, pas le tirage** : `D L S S` est sorti
  « deux LSS » sur les 4 segments ou il apparait, a chaque tirage. La regle « remplacer le mot » du
  SKILL.md s'applique — mais un brief qui interdit de retoucher la version TTS se contente de le
  SIGNALER.
- **La similarite s'effondre quand le script ecrit les nombres en toutes lettres, et ce n'est pas un
  defaut.** Mesure : un segment a 0,6407 de similarite ou Whisper a reecrit `mille quatre cent
  quarante p -> 1440 pas`, `R T X trois mille soixante-dix -> RTX 3070 DT`, `i sept treize mille sept
  cents K -> Ni7 13700K`, `24 gigaoctets de memoire vive -> 24 Go` : la diction etait JUSTE. Ne jamais
  re-tirer sur la seule similarite d'un segment dense en nombres ; classer d'abord par « lecteurs de
  nombres corrects », la similarite ensuite.
- **Chatterbox peut TRONQUER un segment au lieu de le lire** : une prise de 24 mots est sortie en
  **0,80 s** (30,00 mots/s, RMS -13,3 dBFS) — un souffle inintelligible, pas un debit rapide. C'est la
  borne HAUTE du detecteur mots/s qui l'attrape ; le re-tirage l'a ramene a 2,61 mots/s.
- **Le plafond ~40 s se repete** : un segment est sorti a **40,00 s pile** pour 34 mots (0,85 mots/s),
  comme dans le run v2 (39,16 s puis 40,00 s).
- **`transcribe()` de faster-whisper renvoie un GENERATEUR** : `len(segs)` leve `TypeError`. Faire
  `segs = list(segs)` des le retour, sinon le script de controle meurt apres la premiere transcription.
- **Un run de tirages en avant-plan est tue au plafond de l'outil (~420 s)** : il meurt au milieu du
  lot. Ecrire le JSON d'avancement APRES CHAQUE segment (pas a la fin) et relancer en tache de fond en
  FUSIONNANT les entiers deja calcules, sinon les tirages deja produits sont perdus.

## Chapitres YouTube cales sur la timeline REELLE (ne pas garder les estimations du brief)

L'estimation de structure fournie avec un brief (ici jusqu'a 16:15) est toujours fausse : le WAV fait
14:19. Recalculer depuis les durees des segments : `start[i] = somme des durees 0..i-1` est EXACT aux
frontieres (concat sans trou, loudnorm ne change pas la duree — verifier que `analyse.brut.duree_s ==
analyse.final.duree_s`).

- **Un titre de section peut etre colle a la FIN d'un segment** : le chunker fusionne tout reliquat de
  moins de 60 caracteres avec le segment precedent, donc un titre court (« Verdict », 7 car) n'ouvre
  pas son segment. Prendre le debut du segment pour un tel chapitre le place jusqu'a 18 s trop tot.
  Le resoudre en transcrivant CE SEUL segment avec `word_timestamps=True` et en cherchant, par
  fenetre glissante + `difflib`, la position du premier mot du titre (cout ~15 s de CPU par chapitre).
- **Detecter les titres comme « paragraphe court sans point final »** : les paragraphes narratifs
  finissent tous par `.`, donc `len(p) <= 90 and not p.endswith('.')`. Un filtre qui exclut aussi `?`
  rate les titres interrogatifs (« Le contexte : pourquoi un remaster, et pourquoi gratuit ? »).
- **Padder les minutes** (`%02d:%02d`) : `%d:%02d` sur 59,56 s ecrit `0:60`, qui n'est pas un format
  YouTube valide.
- **Ne pas laisser de ligne de texte juste apres le dernier timestamp** (un `FIN` se fait absorber
  dans l'intitule du dernier chapitre) : YouTube ne garde que des lignes `MM:SS intitule`.

## Narration Witcher 3 v2 (67 segments / 1 968 mots) — mesures du 07/10/2026

Article Markdown -> texte parle (balisage retire, titres H1/H2 conserves), segments de 200-250 car
(moyenne 173), integration verifiee par re-concatenation. Modele charge en 14,3 s, VRAM pic 4 802 Mo,
2 327 s de GPU pour 890,0 s d'audio, puis 14 segments hors bande retouches (232 s de GPU).

| Mesure | Valeur |
|---|---|
| Duree finale | 809,68 s = **13,495 min** (cible 13-17 min) |
| Debit mesure | 2,43 mots/s = **145,8 mots/min** |
| Sortie | 48 kHz mono pcm_s16le, 77 729 358 o |
| RMS / crete (apres loudnorm) | -15,96 dBFS / 0,8415 (-1,50 dBFS) / 0 ecretage |
| Silence de tete / de queue | 0,037 s / 0,032 s |
| Silences internes >= 0,30 s | 83, soit 39,38 s (4,86 %), max 1,08 s |
| Forcages d'EOS | 47/67 segments, 54 forcages |

- **Chatterbox plafonne autour de 40 s** : les deux tirages qui trainaient sont sortis a 39,16 s et
  **40,00 s exactement**. Un segment a ~40 s est un tirage borne par le decodeur, pas un debit lent
  legitime — le re-tirage ou le decoupage le regle (0,95 -> 2,39 mots/s apres recollage).
- **`wave.getparams()` inclut `nframes`** : comparer `(nchannels, sampwidth, framerate, comptype,
  compname)` pour recoller deux moities. Le test naif `pa == pb` echoue toujours et fait perdre le run
  au moment du recollage, apres les generations.
- **Un segment d'UNE seule phrase ne peut pas passer par le fallback decoupage** (titre de section,
  phrase courte) : il reste sous 2,0 mots/s. Le consigner comme reserve, pas boucler dessus — 5 des 14
  segments retouches sont restes entre 1,59 et 1,98 mots/s, tous mono-phrase ou a tirage moyen.
- **Deux venvs, deux etapes** : le venv chatterbox n'a pas faster-whisper. Generer les tirages dans
  l'un (`_draw`), scorer/transcrire dans l'autre (venv hermes-agent, faster-whisper CPU `small`) — ne
  rien installer dans le venv du moteur pour un controle ponctuel.
- Verdict de diction sur les 14 segments retouches : 12/14 contenu intact (similarite canonique >=
  0,97 apres triage des artefacts `-s` muet, `trois` -> `3`, `pre-requis` -> `pre requis`). Les deux
  vrais defauts sont des passages de NOMBRES : « 1440p a 60 FPS ... RTX 3070 Ti, i7-13700K » et
  « 39,99 a 49,99 dollars ». Le second a ete repare par un tirage choisi sur la diction ; le premier
  resiste a 3 tirages.

## Politique de texte

Aucun numero de port, aucune URL dans le texte PARLE : ils vont a l'ecran et dans la description
YouTube, ce qui rend en plus le script reutilisable par un autre utilisateur. Chercher les portees a
retirer AVANT la synthese : `grep -nE 'port|[0-9]{4}'` sur le fichier de narration — attention aux
faux positifs (`n'importe`, `importe` contiennent `port`).
