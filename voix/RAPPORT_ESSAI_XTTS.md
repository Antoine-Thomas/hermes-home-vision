# Essai XTTS — LoRA court sur 10 minutes de voix (15-09-2026)

> **Statut** : terminé — **gain marginal**, on en reste au lexique
> **Dernière mise à jour** : 15/09/2026

## Ce qui a été fait

| Étape | Résultat mesuré |
|---|---|
| A. Sous-corpus | 10 min d'entraînement (50 segments de 12 s) + 1 min de validation, extraits de **ZOOM0005** seul (SNR 25,8 dB), mono **22 050 Hz** (fréquence de XTTS v2 — 24 kHz aurait été rééchantillonné), transcrits par Whisper medium |
| B. Entraînement | XTTS v2, lot 1 + accumulation 16, **1 950 pas en 2 h 00** (40 époques), perte **4,3147 → 4,0121 (−7 %)**, meilleur modèle au pas **1568**, VRAM 7 928 / 8 192 Mo |
| C. Test A/B | 4 phrases générées avec la voix actuelle et avec le modèle affiné, transcrites par Whisper medium |
| D. Verdict | **gain marginal** — voir ci-dessous |

## Résultats du test A/B (transcriptions Whisper)

| Phrase | Voix actuelle | Modèle affiné | Termes reconnus |
|---|---|---|---|
| 1. WordPress en local avec Local by Flywheel | « Cours-presse en local, avec local, flywheel » | « Her Press en local, avec local, by Flywheel. **Ouais ouais.** » | 1/10 → 1/10 |
| 2. J'installe WooCommerce et je lance WP-CLI pour configurer nginx et MySQL | « au commerce », « WP Client », « un JANX MXQN » | « **WooCommerce** », « WPCM », « N-Junks » | **0/10 → 1/10** |
| 3. La sauvegarde s'exécute par cronne, puis Docker synchronise les fichiers | « sauvegarde s'exécute par crône… le fichier » | « **La** sauvegarde s'exécute par crône… **les fichiers** » | 2/10 → 2/10 |
| 4. Abonnez-vous pour ne pas rater le prochain volet | exact | exact | 1/10 → 1/10 |

**Total : 4 termes sur 40 reconnus → 5 sur 40.** Un seul gain net (« WooCommerce »), deux
rapprochements (« nginx » devient « N-Junks » au lieu de « JANX »), une phrase plus complète (p3), et
**aucun gain** sur les termes critiques : « WordPress », « WP-CLI », « MySQL », « cron » restent
méconnaissables.

## Stabilité et naturel

| Mesure | Voix actuelle | Modèle affiné |
|---|---|---|
| Durée pour le même texte | 4,50 – 7,66 s | 5,29 – 8,31 s (**+13 à +22 %**) |
| Crête | 0,77 – 0,88 | 0,57 – 0,76 |
| Silence interne maximal | 0,55 – 1,09 s | 0,50 – 0,90 s |
| Artefacts | — | « Ouais ouais » ajouté en fin de p1, « Et j'ense WPCM » (p2) |

Aucun clic, aucune saturation, aucun saut : **stable**. Mais le modèle affiné parle plus lentement pour
le même texte et ajoute parfois des mots — donc pas plus naturel.

## Verdict

**Gain marginal.** Décision appliquée : on documente, on archive le modèle, et **on en reste à la
diction par lexique** — qui règle déjà « WP-CLI », « nginx », « MySQL », « Docker » là où le fine-tune
échoue. Le lexique coûte quelques secondes, le fine-tune a coûté 2 h de GPU pour +1 terme sur 40.

## Ce que l'essai a appris (et qui reste acquis)

- **Le pipeline fonctionne** : un fine-tune XTTS v2 complet sur 8 Go est possible — 2 h pour 1 950 pas.
  Si le corpus atteint un jour 5 h, la cible redevient intéressante.
- **Piège 1** : le `max_wav_length` de la recette (255 995 ≈ 11,6 s) rejette des segments de 12 s et le
  chargeur part en `RecursionError` ; l'erreur affichée est un `PermissionError` sans rapport.
- **Piège 2** : les workers du DataLoader plantent sous Windows (`RecursionError`) → charger dans le
  processus principal (`num_loader_workers=0`).
- **Piège 3** : l'API TTS 0.27.5 n'accepte ni `model_path` ni `checkpoint_path` sur la façade ; il faut
  `Xtts.load_checkpoint(checkpoint_dir=…)` puis `Xtts.inference(text=…, language=…)` en paramètres nommés.
- **Piège 4** : 10 min de corpus (1 min de validation) ne déplacent pas un modèle de 518 M de
  paramètres. La perte baisse de 7 %, la diction ne bouge pas.

## Où sont les fichiers

- Corpus : `%LOCALAPPDATA%\hermes\data\xtts\corpus_test\` (wavs/, validation/, metadata_*.csv)
- Run complet : `entrainement\xtts_essai_20260915_223922-…\` — **16 Go** (3 checkpoints complets)
- Archive : `loRA_archive_best_model_1568.pth` — **5,6 Go**
- Échantillons A/B : `ab\` (8 WAV + `analyse_ab.txt`)
- `voix_reference.wav` : **intacte** (MD5 `2c786188c443…` identique avant et après)
