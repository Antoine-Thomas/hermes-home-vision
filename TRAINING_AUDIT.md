# Audit des cibles entraînables — 15/09/2026

Machine : RTX 3070 Ti **8 Go de VRAM**, i7-8700 (6 cœurs), 64 Go de RAM, NVMe C: 1,1 To libre,
D: 2,3 To libre. GPU mesuré au repos : 1 053 Mo utilisés sur 8 192.

**Aucune formation lancée, aucun téléchargement, aucune installation dans le cadre de cet audit.**
Tout ce qui suit est mesuré sur la machine ou explicitement signalé comme estimation.

---

## 1. Ce qui existe déjà (vérifié, pas supposé)

**Environnements Python isolés — 7 au total, tous propres :**

| Environnement | Taille | torch | Paquets d'entraînement |
|---|---|---|---|
| LatentSync | 6 456 Mo | 2.5.1+cu121 | transformers, accelerate |
| liveportrait | 5 791 Mo | 2.5.1+cu121 | transformers |
| sadtalker | 5 632 Mo | 2.5.1+cu124 | aucun |
| wav2lip | 5 225 Mo | 2.5.1+cu121 | aucun |
| musetalk | 7 535 Mo | 2.0.1+cu118 | transformers, accelerate |
| echomimic_v2 | 5 962 Mo | 2.5.1+cu124 | transformers, accelerate |
| xtts | 5 082 Mo | — (TTS 0.27.5) | aucun |

Chacun a son propre `venv` : c'est propre, mais **aucun n'a `peft`, `bitsandbytes`, `datasets` ni
`trl`**. Aucune chaîne d'entraînement n'est installée : ni kohya_ss, ni sd-scripts, ni script
d'entraînement quel qu'il soit sur le disque.

**Corpus déjà présents :**

- `data/video_youtube` : 99 Go (sources 4K/720p, segments LatentSync, sorties).
- `data/xtts` : `voix_xtts_full.wav` (16 Mo) et v2/v3/v4 (15 Mo chacun), dossiers `segments/` et
  `segments_v4/` — **attention : ce sont des sorties XTTS, donc de la voix de synthèse, pas la voix
  réelle.**
- `data/vibevoice` 8,9 Go, `data/optimisation_tour` 3,1 Go, `data/surveillance` 1,6 Go.
- Scripts v4 : **78 fichiers** dans `Desktop\hermes_tuto_v4`, dont les métriques réutilisables —
  `diag_sauts.py`, `verif_v6.py`, `contour_levres.py`, `mesure_bouche.py`, `diag_cotes.py`,
  `fantomes.py`, `test_diction_v8*.py`, `whisper_v6.py`.
- Transcriptions : `volet4_transcript_v8_medium.txt` (63 lignes), v6 (62), small (140). Quelques
  centaines de mots chacune.
- Whisper : `faster_whisper` est installé dans le venv Hermes — la transcription fonctionne, mais
  il n'y a **pas** de jeu de données audio/transcription de qualité derrière.
- Skills : environ 80 `SKILL.md` (dont `talking-head-video-8gb`, 47,7 ko, le plus riche),
  `tts-voice-cloning`, `ai-video-pipeline`, `media-analysis`, `comfyui`, `productivity/siyuan`,
  les cinq WordPress, `omniroute-suite`, `hermes-operations`.
- Base de sessions Hermes (`state.db`, 419 Mo) : **37 868 messages**, 364 sessions. Détail :
  18 046 messages d'assistant (3,9 Mo de texte), 17 833 messages d'outil (**34 Mo**, essentiellement
  du bruit : sorties de commandes, journaux), le reste en messages utilisateur. Soit environ **6 Mo
  de prose exploitable**, non annotée, mêlant plusieurs langues et de nombreux échecs.

**Ce qui n'existe pas :** aucun modèle d'embeddings local (les 75 Go d'Ollama contiennent
`glm-4.7-flash`, `hermes3:8b`, `llama2.5`/`qwen2.5:7b`, mais **aucun modèle d'embedding**), aucune
base vectorielle (`faiss`, `chromadb`, `sentence_transformers` absents partout).

**Corpus de la voix réelle — le point critique :**
`data/video_youtube/p1002837/source.mp4` = **13,92 secondes** d'audio (aac 48 kHz stéréo). Les
versions `source_4k_25fps_clean.mp4` et `source_720p_25fps_clean.mp4` font 8 s et **n'ont pas de
piste audio**. La prise de vue originale (P1002837) n'est plus sur le disque : recherche faite sur
Bureau, Vidéos, Téléchargements, D:, F:, H: — introuvable. Aucun autre enregistrement de voix
(wav/mp3/m4a > 1 Mo) sur la machine. **Total disponible : moins de 15 secondes de voix réelle.**

**Contexte WordPress :** les cinq sites Local ont été supprimés le 15/09 (`sites.json` vide, dossier
`Local Sites` disparu). Il n'y a donc plus de contenu de site à indexer ni à utiliser comme données.

---

## 2. Inventaire des cibles

### Cible 1 — XTTS : fine-tune sur la voix de l'auteur

- **Données disponibles** : 13,92 s de voix réelle (`source.mp4`), mono-source, qualité correcte
  mais très courte ; les `voix_xtts_full*.wav` (16 Mo) et `segments/` sont des **sorties de
  synthèse**, inutilisables pour apprendre la voix.
- **Données manquantes** : tout. Il faut 30 minutes à plusieurs heures de parole propre, sans
  musique, une seule prise de parole, idéalement 200+ phrases couvrant les termes techniques visés.
- **VRAM / méthode** : fine-tune XTTS ≈ 6-8 Go en LoRA sur les couches GPT, mais la faisabilité
  VRAM n'est pas le facteur limitant — **la donnée l'est**.
- **Durée estimée** : 2 à 4 h par essai, pour un résultat dégradé — et non exploitable.
- **Disque** : quelques Go (checkpoints XTTS 1,8 Go + sauvegardes d'essais).
- **Utilité réelle : 2/5.** La diction des termes techniques (WP-CLI, nginx, MySQL, Docker) est
  **déjà réglée** par le labo de graphies : 44 phrases passées XTTS → Whisper ont validé
  « double-vé-pé cé-èle-i », « n-jin-x », « Maï-Ess-Cu-Elle », « Dockeur », « Hermesse ».
  **Ce travail a été transformé en lexique opérationnel le 15/09/2026** : `lexique_diction.json`
  (10 termes, 5 tournures), `preparer_script_tts.py` (avant synthèse) et
  `corriger_transcription.py` (après Whisper). Voir le document SiYuan « Lexique de diction et
  relecture ».
- **Risques** : sur-apprentissage garanti avec 14 s (le modèle apprend le bruit, la voix se
  dégrade), temps perdu, et le vrai problème — la diction — est traité ailleurs.

**Verdict : À ÉVITER** (tant que la donnée n'existe pas). Le levier utile est une couche de
correction lexicale appliquée au texte *avant* la synthèse, pas un entraînement.

### Cible 2 — Whisper : fine-tune français + jargon WordPress

- **Données disponibles** : environ 271 s d'audio (la voix de synthèse du volet 4) et 5
  transcriptions de 62 à 140 lignes, produites par Whisper lui-même.
- **Données manquantes** : des dizaines d'heures audio/transcription alignées de qualité humaine.
  On dispose de quelques minutes et d'un étiquetage circulaire (Whisper transcrit, Whisper
  s'entraîne sur sa propre sortie) — c'est le pire cas de figure.
- **VRAM / méthode** : LoRA sur Whisper small ou medium, 6-8 Go, faisable techniquement.
- **Durée estimée** : 2 à 4 h par époque ; sans données, l'exercice n'a pas de sens.
- **Disque** : 1 à 3 Go par essai.
- **Utilité réelle : 2/5.** La relecture est le vrai besoin, et il se règle **sans entraînement** :
  un lexique de correction (nginx, WP-CLI, MySQL, WooCommerce, Xdebug…) appliqué après
  transcription, plus un `initial_prompt` qui donne le vocabulaire à Whisper.
- **Risques** : boucle fermée sur ses propres erreurs, dégradation sur le français courant,
  des heures de GPU pour un gain inférieur à une table de correspondance de 40 lignes.

**Verdict : À ÉVITER.** Le lexique de post-correction est la bonne réponse, et il est déjà à moitié
écrit dans `test_diction_v8*.py`.

### Cible 3 — LoRA visuel : SDXL / Flux / LTX-2.3

- **Données disponibles** : quasi rien. Aucun dossier d'images de style constitué ; les seuls
  fichiers image sur le disque sont des captures de contrôle du volet 4
  (`apercu_v6_95s.png`, etc.). Le logo utilisé par l'assemblage existe dans les scripts.
- **Données manquantes** : 20 à 40 images propres du style visé (logo, palettes, cadrages types),
  légendées. À collecter.
- **VRAM / méthode** :
  - **SDXL LoRA** : ~8-10 Go en configuration basse VRAM (kohya `--lowvram`, batch 1, 768 px,
    gradient checkpointing, fp16) — **tient sur 8 Go, de justesse**, c'est le seul chemin réaliste.
  - **Flux LoRA** : le modèle fait 12 B ; même quantifié, l'entraînement réclame ~16-24 Go.
    **Non, pas sur cette machine.**
  - **LTX-2.3 LoRA** : modèle de 22 B, chaîne d'entraînement officielle conçue pour 40+ Go de VRAM.
    **Non.** Et nos poids sont en GGUF quantifié, ce qui n'est pas entraînable en l'état.
- **Durée estimée** : 2 à 4 h par passage SDXL (1 500-2 000 pas, ~2-4 s/pas), 2 à 4 passages pour
  converger → une journée par style.
- **Disque** : ~10 Go (modèle SDXL de base ~6,5 Go + kohya + sauvegardes de LoRA).
- **Utilité réelle : 3/5.** Utile pour des vignettes, des illustrations de fond, des planches de
  présentation — pas pour la vidéo, où la branche C génère déjà sans style imposé.
- **Risques** : avec 20 images, la qualité plafonne vite ; le style « logo + palette » s'obtient
  aussi très bien par composition classique (ce que fait déjà l'assemblage FFmpeg).

**Verdict : À ESSAYER** (SDXL uniquement, plus tard, après collecte d'images). Flux et LTX LoRA :
**à éviter**.

### Cible 4 — LLM local 7B : QLoRA WordPress + skills Hermes

- **Données disponibles** : ~6 Mo de prose issue de 364 sessions (3,9 Mo d'assistant, ~2 Mo
  d'utilisateur), non annotée ; les ~80 skills ; les 5 skills WordPress du dépôt. Aucun jeu
  instruction/réponse construit.
- **Données manquantes** : des milliers de paires instruction→réponse, relues par un humain. Ici il
  faudrait **fabriquer** le jeu de données avant même de songer à entraîner.
- **VRAM / méthode** : QLoRA 7B en 4 bits, batch 1, séquence 512-1024, gradient checkpointing,
  optimiseur paginé → **6-8 Go, ça passe, mais c'est serré** et la moindre séquence longue casse
  l'allocation.
- **Durée estimée** : 6 à 10 h par époque sur 1 000-2 000 exemples ; compter 2 à 3 jours avec la
  préparation et les essais.
- **Disque** : ~20 Go (modèle de base 4 bits, LoRA, checkpoints, jeu de données).
- **Utilité réelle : 1/5 — et il faut le dire franchement.** La machine a déjà accès à OmniRoute
  (10 modèles gratuits en priorité), à DeepSeek en repli, et à trois modèles dans Ollama
  (`glm-4.7-flash`, `hermes3:8b`, `qwen2.5:7b`). Un 7B affiné sur 6 Mo de conversations non triées
  sera **moins bon** que ces modèles sur le WordPress comme sur le reste, tout en coûtant des jours
  de GPU.
- **Risques** : dégrader un modèle correct, sur-apprendre le style des échanges (et leurs erreurs),
  y consacrer une semaine pour un résultat inférieur à ce qui tourne déjà.

**Verdict : À ÉVITER.** Le seul angle défendable serait un **classifieur** étroit (voir cible 6),
pas un modèle génératif.

### Cible 5 — Embeddings / RAG : base de connaissances interrogeable

- **Données disponibles — et c'est ici que tout se joue** : les ~80 skills (dont
  `talking-head-video-8gb` 47,7 ko), les 23 documents SiYuan, le dépôt des 5 skills WordPress,
  les 78 scripts v4 avec leurs commentaires, les métadonnées YouTube des volets, les journaux
  d'installation (`INSTALL_LOG.md`, `RAPPORT_INSTALLATION.md`, `CHEATSHEET.md`), la documentation
  Hermes. Soit **quelques mégaoctets de texte propre, déjà structuré et à jour** — l'inverse du cas
  Whisper et du cas 7B.
- **Données manquantes** : **un modèle d'embeddings**, c'est tout. Il n'y en a aucun sur la machine
  (pas de `sentence-transformers`, pas de modèle d'embedding dans Ollama, pas de base vectorielle).
  C'est un prérequis de quelques centaines de mégaoctets, à valider avant installation.
- **VRAM / méthode** : aucun entraînement. L'indexation se fait en quelques minutes, sur CPU ou GPU
  indifféremment ; l'interrogation ne consomme pas de VRAM (embeddings + recherche lexicale).
- **Durée estimée** : une demi-journée de mise en place, dont la moitié pour l'indexation et les
  essais de pertinence.
- **Disque** : moins de 1 Go pour 2 000 à 5 000 fragments et leurs vecteurs.
- **Utilité réelle : 5/5.** C'est la seule cible dont le produit est **immédiatement consommé par
  Hermes** au quotidien : retrouver la bonne procédure, le bon piège, le bon paramètre sans les
  remettre dans chaque prompt — c'est-à-dire moins de tokens, moins d'erreurs répétées, et une
  mémoire qui ne sature pas.
- **Risques** : faibles et tous maîtrisables — index qui vieillit si on ne le régénère pas (à
  scripter), fragmentation mal choisie (à calibrer : le paragraphe ou la section, pas la ligne),
  dépendance à un modèle d'embeddings à choisir.

**Verdict : À FAIRE.**

### Cible 6 — Classifieurs légers : anomalies vidéo

- **Données disponibles** : les métriques existent déjà — `diag_sauts.py` (MAD par image, détection
  des sauts aux raccords), `verif_v6.py`, `contour_levres.py` et `mesure_bouche.py` (netteté du
  contour des lèvres), `diag_cotes.py` (netteté latérale), `fantomes.py`. Les valeurs mesurées du
  volet 4 sont connues : MAD 0,96-1,22 aux raccords d'un montage sain contre 6,5 sur le montage
  défectueux ; netteté latérale ×6 après transfert passe-haut ; contour de lèvres 1,33/1,49 contre
  1,00 pour la source.
- **Données manquantes** : des **étiquettes**. On a quelques cas documentés (5 sauts sur le volet 4,
  des zones floues identifiées), pas de quoi entraîner sérieusement.
- **VRAM / méthode** : aucune. Un détecteur d'anomalies sur ces quelques variables
  (`IsolationForest`, `sklearn`) tourne sur CPU en secondes. Pas de deep learning.
- **Durée estimée** : une demi-journée, plus le temps de fabriquer des exemples défectueux
  volontairement (c'est faisable : on sait dégrader une image, créer un saut, flouter une bande).
- **Disque** : négligeable.
- **Utilité réelle : 3/5.** Utile pour automatiser le contrôle qualité des prochains volets, mais
  **un simple seuil fait déjà 90 % du travail** : « MAD > 4 × la médiane » a détecté les 5 sauts.
  L'apprentissage n'apporte quelque chose que si les défauts deviennent variés et nombreux.
- **Risques** : sur-ingénierie (entraîner un modèle pour remplacer trois lignes de seuil),
  étiquettes trop rares.

**Verdict : À ESSAYER** (version seuils d'abord, apprentissage seulement si les défauts se
diversifient).

---

## 3. Tableau comparatif priorisé (rapport utilité / coût)

| Cible | Données dispo | VRAM | Durée | Utilité | Verdict |
|---|---|---|---|---|---|
| **Embeddings / RAG** | Abondantes et propres (skills, SiYuan, scripts, docs) | 0 (aucun entraînement) | ½ journée | **5/5** | **FAIT** |
| Classifieurs d'anomalies vidéo | Métriques oui, étiquettes non | 0 (CPU) | ½ journée | 3/5 | À ESSAYER |
| SDXL LoRA (style visuel) | Quasi nulles, à collecter | 8-10 Go (serré) | 1 journée | 3/5 | À ESSAYER |
| XTTS fine-tune (voix) | **14 s** de voix réelle | 6-8 Go | 2-4 h/essai, résultat dégradé | 2/5 | À ÉVITER |
| Whisper fine-tune | Quelques minutes, étiquetage circulaire | 6-8 Go | 2-4 h/époque | 2/5 | À ÉVITER |
| LLM 7B QLoRA | 6 Mo de prose non annotée | 6-8 Go (tendu) | 2-3 jours | 1/5 | À ÉVITER |
| Flux LoRA | — | ≥16 Go | — | — | À ÉVITER |
| LTX-2.3 LoRA | — | ≥40 Go, poids GGUF non entraînables | — | — | À ÉVITER |

---

## 4. Trois recommandations

### 1. RAG sur la documentation et les skills — **maintenant**

**Pourquoi avant tout le reste** : c'est la seule cible dont les données existent déjà, dont le
produit sert tous les jours, et qui ne consomme ni VRAM ni temps de GPU. Tout le reste demande soit
une collecte de données (voix, images, paires instruction-réponse), soit des jours de calcul pour un
résultat inférieur à ce qui est déjà installé. Ici : une demi-journée, et Hermes s'en sert
immédiatement.

**À collecter avant de commencer** : rien de nouveau — il faut **choisir et installer un modèle
d'embeddings** (aucun n'est présent), décider du périmètre à indexer (proposition : les ~80 skills,
les 23 documents SiYuan, les 78 scripts v4, le dépôt des skills WordPress) et du découpage (par
section de document, pas par ligne).

**Première étape concrète (une seule)** : écrire le script d'indexation qui découpe ces quatre
sources en fragments et produit un index local — **sans encore installer de modèle**, en vérifiant
d'abord le volume exact de fragments et leur taille.

### 2. Le lexique de diction et de relecture — **FAIT le 15/09/2026** (sans entraînement)

**Pourquoi** : cela traite la demande réelle (NGINX, WP-CLI, MySQL, Docker s'écrivent mal) sans
entraîner quoi que ce soit. Le labo de graphies a déjà validé 44 phrases ; il manque la couche qui
applique ces correspondances automatiquement, avant la synthèse et après la transcription Whisper.

**À collecter** : la liste des termes à corriger, avec leurs graphies validées — déjà en partie
consignée dans `test_diction_v8*.py` et dans les transcriptions du volet 4.

**Première étape concrète (une seule)** : extraire de `test_diction_v8*.py` le tableau
« terme → graphie validée » dans un fichier unique réutilisable.

### 3. Contrôle qualité des vidéos par seuils, puis classifieur si nécessaire — **en dernier**

**Pourquoi** : les métriques existent déjà et le seuil MAD a fait le travail sur le volet 4. C'est
du temps bien investi, mais ce n'est pas ce qui débloque le plus de valeur aujourd'hui.

**À collecter** : constituer un petit jeu d'exemples étiquetés (sain / sauté / flou / fantôme) en
dégradant volontairement des extraits existants.

**Première étape concrète (une seule)** : regrouper dans un seul script les métriques dispersées
(`diag_sauts.py`, `contour_levres.py`, `diag_cotes.py`) avec des seuils explicites, et le faire
tourner sur le volet 4 livré pour vérifier qu'il retrouve les 5 sauts connus.

---

## 5. Ce qu'il ne faut pas faire sur cette machine

1. **Fine-tuner XTTS sur 14 secondes de voix.** Ça ne « améliorera » pas la diction, ça abîmera la
   voix. Le problème de diction se règle par les graphies et un lexique.
2. **Fine-tuner Whisper sur ses propres transcriptions.** Boucle fermée : le modèle apprend ses
   erreurs. Le lexique de post-correction est plus efficace et gratuit.
3. **Entraîner un LLM 7B local « pour WordPress ».** Trois modèles sont déjà installés et dix
   modèles gratuits sont accessibles ; un 7B affiné sur 6 Mo de conversations non triées sera
   inférieur à tous, pour deux à trois jours de GPU.
4. **Tenter Flux ou LTX-2.3 en LoRA.** 12 B et 22 B de paramètres : la VRAM nécessaire est hors de
   portée (16-24 Go et 40+ Go), et nos poids LTX sont quantifiés en GGUF, donc non entraînables.
5. **Confondre sorties XTTS et voix réelle.** Tout `data/xtts/voix_xtts_*.wav` est de la synthèse :
   s'en servir comme données de voix serait une faute de méthode.
6. **Lancer un entraînement sans avoir compté les données d'abord.** Le réflexe qui a évité 18 Go
   inutiles sur LTX-2.3 s'applique ici à l'identique : mesurer le volume, la qualité et les
   étiquettes avant d'installer quoi que ce soit.

---

## 6. Ce qu'il me faut valider avant d'engager la suite

1. **Le modèle d'embeddings** : aucun n'est présent. Accord pour en installer un (quelques centaines
   de mégaoctets) ou préférence pour passer par une API distante ?
2. **Le périmètre de l'index** : les quatre sources proposées (skills, SiYuan, scripts v4, dépôt
   WordPress) ou un sous-ensemble ?
3. **Le maintien à jour** : régénération manuelle après chaque modification, ou tâche planifiée
   quotidienne (comme celle du noyau SiYuan) ?

---

*Rapport produit sans entraînement, sans téléchargement et sans installation. Toutes les valeurs de
ce document proviennent de mesures faites sur la machine le 15/09/2026.*
