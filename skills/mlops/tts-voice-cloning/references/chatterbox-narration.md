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

## Politique de texte

Aucun numero de port, aucune URL dans le texte PARLE : ils vont a l'ecran et dans la description
YouTube, ce qui rend en plus le script reutilisable par un autre utilisateur. Chercher les portees a
retirer AVANT la synthese : `grep -nE 'port|[0-9]{4}'` sur le fichier de narration — attention aux
faux positifs (`n'importe`, `importe` contiennent `port`).
