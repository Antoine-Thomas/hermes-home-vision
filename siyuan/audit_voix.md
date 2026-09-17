# AUDIT_VOIX — corpus « ma voix 12 » (15/09/2026)

Corpus analysé : `C:\Users\searc\Desktop\ma voix 12` — **lecture seule**, aucun fichier déplacé,
copié ni modifié. Mesures produites par `audit_voix.py` (dans ce dossier) sur les 2 fichiers, en
flux par blocs de 30 s ; résultats bruts dans `audit_voix.json`.

## Étape 1 — Inventaire

| Fichier | Durée | Format | Fréquence | Canaux | Taille |
|---|---|---|---|---|---|
| ZOOM0004.WAV | 56 min 05 s | WAV PCM 24 bits | 48 000 Hz | 2 | 969,4 Mo |
| ZOOM0005.WAV | 47 min 18 s | WAV PCM 24 bits | 48 000 Hz | 2 | 817,4 Mo |

**Durée totale : 1 h 43 min (6 204 s) · Durée de voix utile (hors silence) : 1 h 36 min (5 784 s).**

## Étape 2 — Qualité, mesure par mesure

| Mesure | ZOOM0004 | ZOOM0005 | Lecture |
|---|---|---|---|
| Niveau médian | −25,2 dBFS | −25,7 dBFS | niveau d'enregistrement sain, tête de gain bien réglée |
| Crête | 0,0 dBFS | 0,0 dBFS | atteint le plein niveau (voir saturation) |
| Plancher de bruit | −36,0 dB | −47,5 dB | le 0004 est nettement plus bruyant |
| Niveau de parole | −22,1 dB | −21,7 dB | identique d'un fichier à l'autre |
| **Rapport signal/bruit estimé** | **13,9 dB** | **25,8 dB** | 0005 propre, 0004 acceptable mais à débruiter |
| Part de silence | 2,7 % | 11,6 % | aucune fichier au-dessus de 30 % (seuil d'alerte) |
| Échantillons saturés (≥ 0,99) | 253 (0,0002 %) | 360 (0,0003 %) | négligeable en proportion |
| Plus longue série saturée | 23 échantillons (~0,5 ms) | 63 échantillons (~1,3 ms) | quelques transitoires écrasés, pas de saturation continue |
| Aplatissement spectral | 0,0038 | 0,0029 | très tonal : **pas de fond musical ni de bruit large bande** |
| Centrinoïde spectral | 2 169 Hz | 2 028 Hz | centré voix parlée |
| F0 médiane | 164,6 Hz | 152,2 Hz | plage cohérente avec un seul locuteur |
| Étendue F0 | 132,5 – 196,5 Hz | 146,5 – 171,8 Hz | pas de voix étrangère détectée par cette mesure |

**Musique de fond** : aucune. L'aplatissement spectral très bas (0,003) sur les fenêtres analysées
correspond à un signal harmonique de parole ; un lit musical aurait fait monter cet indicateur et
abaissé le contraste signal/bruit.
**Autres locuteurs** : aucun indice. L'étendue de F0 reste étroite sur chaque fichier (64 Hz et
25 Hz d'amplitude). *Limite honnête* : ceci est un indice, pas une diarisation — une vérification
définitive demanderait un modèle de segmentation des locuteurs (non installé, non nécessaire ici).
**Silences anormaux** : aucun fichier ne dépasse 30 % de silence (2,7 % et 11,6 %).
**Clipping** : présent mais marginal — 613 échantillons sur ~297 millions. Les séries les plus
longues (23 et 63 échantillons) correspondent à des attaques de consonnes, pas à une saturation de
gain continue.

## Étape 3 — Verdict par rapport aux seuils XTTS

| Seuil communautaire | Modèle | Corpus |
|---|---|---|
| Minimum viable : 30 min propre, mono-source | — | **largement dépassé** |
| Bon : 1 à 3 h | ✔ | **1 h 36 min de voix utile** |
| Idéal : 5 h et plus | ✗ | non atteint (mais hors de portée sans nouvelles prises) |

### Verdict : **VIABLE — XTTS fine-tune redevient une cible sérieuse.**

Le corpus se situe dans la bande « bon » avec deux réserves exploitables, qui ne remettent pas le
verdict en cause mais dictent le prétraitement :

1. **ZOOM0004 est à débruiter** (SNR 13,9 dB contre 25,8 dB pour 0005). Un débruiteur léger avant
   l'extraction des embeddings suffit ; à défaut, entraîner d'abord sur 0005 et n'ajouter 0004
   qu'après nettoyage.
2. **Quelques transitoires saturés** (63 échantillons consécutifs au maximum). À repérer et atténuer
   avant l'entraînement : un fine-tune apprend aussi les clics.

## Étape 4 — Devis (aucun entraînement lancé)

**Ce qui est établi par la mesure** : 1 h 36 min utilisables, mono-source, sans musique, à 48 kHz
PCM 24 bits. Autrement dit, la donnée qui manquait à l'audit de la Phase 1 est là.

**Ce qui reste à vérifier par une écoute humaine** (je ne peux pas juger la variété d'intonation) :
le corpus contient-il des questions, des exclamations, des pauses variées — ou une lecture plate ?
Un corpus monotone produit une voix plus monotone encore après fine-tune.

| Poste | Estimation |
|---|---|
| Méthode | **LoRA sur XTTS v2** (le fine-tune complet ne tient pas dans 8 Go) |
| VRAM | **6 à 8 Go** — cela tient sur la RTX 3070 Ti, mais sans marge : lot 1-2, gradient checkpointing obligatoire. À confirmer par un essai à blanc de 10 minutes |
| Durée | Fourchette large : **8 à 30 heures** pour un résultat exploitable, selon le nombre d'époques, la longueur des segments (le standard est 6-12 s) et la vitesse de l'extraction des embeddings. Un essai court de 20 minutes par époque donnerait l'échelle réelle |
| Disque | ~2 à 3 Go : audio rééchantillonné à 22,05 kHz mono (~500 Mo), embeddings précalculés, checkpoints LoRA (100-300 Mo chacun) |
| Risques | 1) intonation uniforme (inconnu, à écouter) · 2) bruit du ZOOM0004 qui s'apprend · 3) attaques saturées qui deviennent des clics · 4) surapprentissage sur 1 h 36 : garder un jeu de validation de 10 % pour écouter le modèle à chaque époque · 5) le corpus est en stéréo : choisir un canal ou sommer, mais pas garder deux canaux traités différemment |

**Décision attendue de l'utilisateur** : accord (ou refus) pour cet essai. Rien ne démarre sans lui.

## Étape 5

La Phase 2 (chantiers 2 à 5) reprend après cet audit, quelle que soit la décision sur XTTS.

---

*Note : ce rapport est écrit dans `Desktop\hermes_install\voix\` et non dans le dossier du corpus,
qui est en lecture seule. Le corpus n'a pas été touché.*
