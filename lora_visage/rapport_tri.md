# Rapport de tri — corpus LoRA visage (16/09/2026)

Source : `C:\Users\searc\Desktop\40 tof de moi` — **lecture seule**, originaux jamais modifiés.
Sortie : `C:\Users\searc\Desktop\40 tof de moi\lora_visage\` (26 images 1024×1024, 34 Mo).

## 1. Filtre qualité (3b) — basé sur le VISAGE, pas sur l'image

| Étape | Résultat |
|---|---|
| Photos traitées | **55** (54 JPG + 1 PNG) |
| Visage détecté (InsightFace buffalo_l, GPU) | 54 sur 55 |
| **Retenues** | **26** |
| Éliminées | **29** |

Répartition des éliminations :

| Raison | Nombre |
|---|---|
| Netteté du visage sous la médiane du corpus (seuil 56,5 mesuré sur les visages détectés) | 27 |
| Aucun visage détecté | 1 |
| Petit côté du visage < 512 px | 1 |
| Plus de 2 % du visage écrasé (cramé) | 1 |

Les visages retenus vont de **601×842 px à 2155×3491 px** — tous au-dessus des seuils 512 / 700.

## 2. Variété (3c) — analyse visuelle des 26 retenues

Répartition **angles × expressions** telle que produite par le tri :

| Angle / expression | Nombre |
|---|---|
| face_neutre | 12 |
| face_serieux | 3 |
| face_sourire (léger) | 3 |
| face_sourirefranc | 1 |
| face_autre (moue, bouche ouverte) | 3 |
| 3-4g_neutre | 1 |
| 3-4g_serieux | 1 |
| plongee_neutre | 1 |
| contreplongee_neutre | 1 |
| **profil** | **0** |

Arrière-plans : 1 extérieur, le reste intérieur. **Aucun studio, aucun fond uni franc** (les fonds
« uni » annoncés en première lecture sont en fait des intérieurs flous).

## 3. Confrontation aux cibles que tu avais fixées

| Cible | Demandé | Obtenu | Écart |
|---|---|---|---|
| Total | 25-35 | **26** | ✔ |
| Face | ~35 % (9-12) | **20 (77 %)** | ✘ très au-dessus |
| Trois-quarts | ~30 % (8-11) | **2 (8 %)** | ✘ très en dessous |
| Profil | ~20 % (5-7) | **0** | ✘ absent |
| Plongée / contre-plongée | ~15 % (4-5) | **2 (8 %)** | ~ acceptable |
| Neutre | ~40 % | **16 (62 %)** | ✘ au-dessus |
| Sourire (léger + franc) | ~40 % | **4 (15 %)** | ✘ en dessous |

## 4. Verdict

**Le corpus est suffisant en QUANTITÉ (26 photos), insuffisant en VARIÉTÉ D'ANGLES.**

Concrètement : 20 des 26 photos sont de face. Un LoRA entraîné là-dessus apprendra très bien
l'identité de face et mal les profils et les trois-quarts — il aura tendance à ramener tout prompt
vers un visage frontal. Ce n'est pas rédhibitoire (un LoRA visage frontal reste utile pour des
portraits), mais c'est une limite à connaître avant de dépenser 8-15 h de GPU.

### Recommandation : **essai court d'abord**

| Option | Photos | Étapes visées | Durée GPU estimée |
|---|---|---|---|
| **Essai court (recommandé)** | 15 (les meilleures, en gardant les 2 trois-quarts et les 2 plongées) | ~1 500 | **2 à 3 h** |
| Run complet | 26 | ~4 000 | **6 à 10 h** |

Justification : la variété étant faible, l'essai court suffit à savoir si l'identité « prend » (c'est
la question à laquelle on peut répondre en 2 h) ; un run complet sur un corpus trop frontal
n'apportera pas la variété manquante, seulement une meilleure fidélité de face.

**Aucun entraînement n'a été lancé.** Prérequis non installé à ce jour : la chaîne SDXL LoRA
(kohya_ss ou les scripts diffusers) — à prévoir avant l'essai, avec un budget de téléchargement à
valider (le modèle de base SDXL ~6,9 Go).

### Pour gagner la variété manquante (si tu veux la viser)

15 à 20 photos de plus, uniquement en **profil** et **trois-quarts**, même avec une qualité moindre
(le 512 px minimum s'applique). Les profils sont l'angle qui manque le plus ; c'est aussi celui que
l'analyse visuelle a trouvé le plus difficile à juger sur le corpus actuel — preuve qu'il n'y en a
pas.

## 5. Photos à l'analyse douteuse (à ton arbitrage)

Quatorze photos ont été classées avec un doute explicite : le modèle de vision s'est contredit entre
deux passes, surtout sur l'angle (face vs trois-quarts) et sur l'expression (neutre vs léger
sourire). Les voici, avec la valeur retenue :

| Fichier | Angle retenu | Expression retenue | Doute |
|---|---|---|---|
| 20241116_094455.jpg | face | neutre | une seule oreille visible → léger 3-4 possible |
| 20250427_012301.jpg | face | neutre | léger 3-4 possible |
| 20250731_125207.jpg | face | sourire-léger | face ou profil-gauche selon la passe |
| 20250731_125901.jpg | 3-4-gauche | sérieux | légère contre-plongée possible |
| 492453107_…_n.jpg | plongée | neutre | plongée ou léger 3-4 |
| 493832895_…_n.jpg | face | neutre | face ou 3-4-droit (menton tourné) |
| P1002617.JPG | face | sérieux | plongée marquée selon une lecture |
| P1002885.JPG | contre-plongée | neutre | contredit par deux autres lectures |
| P1002908.JPG | face | sérieux | fond uni ou intérieur flou |
| P1002916.JPG | face | neutre | neutre ou léger sourire |
| P1002919.JPG | 3-4-gauche | neutre | face ou 3-4-gauche |
| P1002920.JPG | face | neutre | intérieur ou flou artistique |
| P1002921.JPG | face | neutre | fond flou : intérieur ou flou artistique |
| P1002923.JPG | face | neutre | neutre ou léger sourire |
| P1002924.JPG | face | autre | bouche ouverte en moue |
| P1002925.JPG | face | sourire-léger | cadrage et expression hésitants |
| P1002926.JPG | face | neutre | inclinaison caméra contradictoire |
| P1002934.JPG | face | autre | moue, fond uni ou pièce |

*(18 lignes : certaines portaient un doute sur plusieurs champs.)*

## 6. Fichiers produits

| Fichier | Contenu |
|---|---|
| `lora_visage/filtre_visage.json` | mesures complètes des 55 photos (visage px, netteté, exposition, verdict 3b) |
| `lora_visage/attributs.json` | angle / expression / arrière-plan / cadrage des 26 retenues, avec les doutes |
| `lora_visage/metadata.json` | **la fiche demandée en 3e** : fichier, source originale, angle, expression, arrière-plan, taille du visage en px, netteté |
| `lora_visage/*.png` | 26 images 1024×1024 recadrées (marge 1,5× la taille du visage) |
| `lora_visage/filtre_visage.py`, `preparer_lora.py` | les deux scripts, réutilisables |
| `filtre.log`, `recadrage.log` | journaux d'exécution |
