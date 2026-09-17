# Historique qualite

> **Statut** : actif
> **Derniere mise a jour** : 15/09/2026

4 rapport(s) de controle qualite, du plus ancien au plus recent.

| Date | Video | Verdict | Sauts | Ratio fantomes | Ratio levres |
|---|---|---|---|---|---|
| 2026-09-15 19:01:57 | `youtube_volet4_hermes_FINAL.mp4` | **OK** | 0 | 0.392 | 1.488 |
| 2026-09-15 19:02:57 | `youtube_volet4_hermes_FINAL_v7.mp4` | **ALERTE** | 5 | 0.382 | 1.483 |
| 2026-09-15 19:04:50 | `youtube_volet4_hermes_FINAL_v7.mp4` | **ALERTE** | 5 | 0.382 | 1.483 |
| 2026-09-15 19:13:30 | `youtube_volet4_hermes_FINAL.mp4` | **OK** | 0 | 0.392 | 1.488 |

## Tendances

- Aucune tendance preoccupante sur les 3 derniers rendus.

## Comment lire

- **Sauts** : nombre d'images dont l'ecart avec la voisine depasse 4 fois la mediane.
- **Ratio fantomes** : cotes de gradient dans la zone des levres, rapportes a la source propre.
- **Ratio levres** : force du contour des levres, rapportee a la source (`1,0` = aussi net).
- Verdicts : `OK` (code 0) · `ATTENTION` (code 1) · `ALERTE` (code 2).

Regenerer ce fichier : `python historique_qualite.py --dossier "C:\Users\searc\Desktop\hermes tuto"`
