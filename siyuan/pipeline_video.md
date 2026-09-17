# Pipeline vidéo — orchestrateur

> **Statut** : actif
> **Dernière mise à jour** : 15/09/2026

## Fait

`C:\Users\searc\Desktop\hermes_tuto_v4\pipeline_video.py` enchaîne toute la chaîne, un seul point
d'entrée :

```
python pipeline_video.py --script mon_script.txt --voix v9 --qualite --source p1002837
```

| Étape | Rôle | Appelé | Produit |
|---|---|---|---|
| 1 | préparation du script (lexique de diction) | `preparer_script_tts.py` | `scripts_tts/<script>_tts.txt` |
| 2 | synthèse vocale | `gen_voice_v<N>.py` détecté automatiquement | `volet4_voice_<voix>.wav` |
| 3 | plan de découpe | calcul interne (voir la limite ci-dessous) | — |
| 4 | lissage vidéo | `run_latentsync_v8b.py` | `latentsync_<source>_<voix>.mp4` |
| 5 | assemblage | `assemble_v6.py run` (variables d'environnement) | `youtube_volet4_hermes_FINAL_<voix>.mp4` |
| 6 | contrôle qualité | `controle_qualite.py` | `rapport_qualite_*.json` + verdict |

Rapport unique `pipeline_<horodatage>.txt` : durée totale, durée de chaque étape, verdict qualité,
chemin et taille de chaque fichier produit.

Options : `--dry-run` (liste tout, n'exécute rien) · `--sans-etape N` (reprend à l'étape N) ·
`--force` (autorise l'écrasement) · `--qualite` (ajoute l'étape 6).

### Garanties

- **Aucun script existant n'est modifié.** `assemble_v6.py` est paramétrable par variables
  d'environnement, il est appelé tel quel. `gen_voice_v8.py` et `run_latentsync_v8b.py` n'ont ni
  argument ni variable d'environnement : l'orchestrateur écrit dans le dossier temporaire une
  **copie** de leur source avec les constantes substituées, l'exécute, puis la supprime. L'empreinte
  des fichiers d'origine est relevée avant et après chaque étape et consignée dans le rapport : si
  elle change, l'orchestrateur s'arrête.
- **Rien n'est supprimé, jamais.** Un fichier de sortie déjà présent fait **arrêter** le pipeline
  avant toute exécution (code 2) : il faut `--force` pour l'autoriser.
- **Arrêt propre sur échec** : l'étape suivante ne démarre pas, le rapport est écrit quand même, et
  il indique la commande de reprise (`--sans-etape N`).

## Reste à faire

- L'étape 3 **ne découpe pas** l'audio : la découpe réelle (phase du ping-pong + coupe des silences
  de fin de segment) est faite par `run_latentsync_v8b.py`. L'orchestrateur vérifie le plan (durée,
  segments de 48 s = 3 cycles de 16 s, reste) et le consigne. Découper deux fois produirait des
  segments différents de ceux que LatentSync attend.
- Numérotation : l'étape 4 est LatentSync, l'**assemblage est l'étape 5**. Pour reprendre à
  l'assemblage : `--sans-etape 5`.
- Le vrai run de validation a porté sur un texte court (18 s d'audio). À confirmer sur un volet
  complet, où l'assemblage dure des dizaines de minutes.

## Pièges

- Deux pièges Python rencontrés en construisant le lanceur, à ne pas refaire :
  `re.sub` interprète les antislashs de la **chaîne de remplacement** comme des références de
  groupe (il faut passer une fonction) ; et passer par `exec()` d'une chaîne contenant un chemin
  Windows décode les antislashs **deux fois**, ce qui casse les chemins — écrire un fichier
  temporaire est la solution.
- Les dossiers de sortie doivent exister : `preparer_script_tts.py` ne crée pas son dossier
  `scripts_tts`. L'orchestrateur les crée.
- Le générateur de voix **reprend** les segments déjà présents : sans dossier de sortie neuf
  (`segments_<voix>`), il réutiliserait les segments d'une autre voix, et la nouvelle voix serait
  un mélange silencieux des deux.
- L'assemblage appelle lui-même le contrôle qualité depuis le 15/09. Pour éviter de décoder la vidéo
  deux fois, l'orchestrateur le désactive (`V4_SANS_QUALITE=1`) et lance l'étape 6 lui-même.

## Commandes

```
cd "C:\Users\searc\Desktop\hermes_tuto_v4"

python pipeline_video.py --script test_pipeline_court.txt --voix v9 --qualite --source p1002837
python pipeline_video.py --script mon_script.txt --voix v9 --qualite --dry-run
python pipeline_video.py --script mon_script.txt --voix v9 --qualite --sans-etape 5
python pipeline_video.py --script mon_script.txt --voix v9 --qualite --force
```

### Tests réalisés le 15/09/2026

| Test | Résultat |
|---|---|
| `--dry-run` sur le script du volet 4 | 6 étapes listées, 0 exécution, code 0 |
| `--dry-run --sans-etape 5` (fichiers du volet 4 déjà rendus) | étapes 1-4 « ignorée », 5-6 « à exécuter », code 0 |
| **Run complet réel** sur `test_pipeline_court.txt` (18,3 s d'audio) | **code 0, 285,3 s au total** : XTTS 38,5 s · plan 0,1 s · LatentSync 151,0 s · assemblage 82,2 s · qualité 13,6 s · **verdict OK** |
| Reprise `--sans-etape 6` sur la vidéo produite | seule l'étape 6 exécutée (13,2 s), verdict OK, code 0 |
| Écrasement sans `--force` | arrêté avant exécution, code 2, 4 sorties signalées |
| Intégrité des scripts appelés et de la vidéo livrée | empreintes inchangées, `FINAL` v8 = `0351c5ff3540…` |
