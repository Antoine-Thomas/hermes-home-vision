---
name: premiere-montage-comparatif
description: Use when creating comparative montages in Premiere via MCP.
---

# Premiere Montage Comparatif — v1

Workflow validé sur Premiere Pro Beta 26.x + premiere-pro-mcp (C:/Users/searc/premiere-pro-mcp).

## Séquence

- Preset: `HD 1080p/HD 1080p 60 fps.sqpreset` — PASSER LE CHEMIN AVEC BACKSLASHES (`C:\Program Files\...`) sinon `Failed to create sequence from preset` (forward-slash bug du bridge).
- Vérifier via `get_full_project_overview` : 1920x1080, ticks 254016000000/60, 3 pistes video / 4 audio.
- Utiliser `getSequenceTools().create_sequence` (gère l'échappement ExtendScript), pas un buildScript manuel.

## Insertion film entier (1102 segments)

- Sources: A `000f4244` CaenTravoriginal1080p60fps.mp4, B `000f4242` caentravelling2_4K60_stable.mp4, durée 2753.950s chacune.
- Formule: `nb = 2*ceil(max(durA,durB)/5)` = 1102. Segment n : source = A si pair sinon B, extrait `[(n//2)*5, (n//2)*5+5]` borné à durée source.
- Méthode: `projectItem.setInPoint(timeObj,4)` + `setOutPoint` SUR L'ELEMENT PROJET (pas clip timeline — buggé), puis `sequence.overwriteClip(projectItem, ticks)` avec `ticks = seconds * 254016000000`. Nommage `A-000`/`B-000`, étiquettes via `projectItem.setColorLabel(6=violet A, 7=bleu B)`.
- Audio: A sans piste (silence accepté), B audio sur A1. Ne pas forcer de silence artificiel.

## Analyse préalable

- Script: `C:/Users/searc/AppData/Local/Temp/analyse_pelerinage.py` (cv2 + ffmpeg scdet + Farneback 320x180 + Haar cascade /2s). Sortie `%TEMP%/evenements_pelerinage.json`. `junction_map.json` mappe chaque jonction vers transition + marqueurs RELIRE sur incertains.
- Lancer avec timeout >=1200s en arrière-plan. Si échec -> fallback dissolve partout.

## Limites connues v2 (Premiere 27.0 Beta — build actuelle)

- Catalogue QE entierement casse: `qe.project.getVideoEffectByName`/`getVideoTransitionByName` renvoient des stubs `name=""` ; `getVideoEffectList`/`getVideoTransitionList` renvoient des objets SANS `numItems` ; `qeClip.addTransition(...)` et `qeClip.addVideoEffect(...)` retournent `false` (no-op) ou jettent "Illegal Parameter type" (duree numerique). DOM legacy `Track.transitions` en lecture seule, pas d'ajout possible. Transitions + effets (Lumetri) IMPOSSIBLES via CEP/QE.
- UXP bridge (TransitionFactory.createVideoTransition, createAddVideoTransitionAction) = seule voie fonctionnelle, mais non installee (pas de PREMIERE_UXP_TOKEN, pas de plugin UXP, port 7777 ferme).
- OK sur 27.0: insertion, nommage, etiquettes, marqueurs (`seq.markers.createMarker(t)` + `deleteMarker` + `getNextMarker(m)` sur la collection), playhead (`seq.setPlayerPosition("0")`), sauvegarde (`app.project.save()`), duplication (`seq.clone()`), renommage (`seq.name = "..."`).
- `getPlayerPosition()` + `setPlayerPosition` prennent/rendent des ticks; `__ticksToSeconds`/`__secondsToTicks` dispo en helper.

## Creation sequence fiable (27.0)

- `create_sequence` avec preset HD 1080p 60fps echoue toujours ("Failed to create sequence from preset").
- Methode fiable: `duplicate_sequence` sur une sequence existante deja bonne (1102 clips) puis `seq.name = "NouveauNom"` via execute_extendscript. Herite clips + resolution + fps + duree. Verifier width/height/ticks apres.

## Limites connues v1 (Premiere 26.x Beta)

- `qeClip.addTransition()` et `addVideoEffect()` sont NO-OP sur cette build (MCP: "returned without adding"). Transitions, Lumetri, effets audio non posables via QE — à faire manuellement ou en ExtendScript pur.
- OK: insertion, nommage, marqueurs (`create_marker`), sauvegarde (`app.project.save()`), playhead (`setPlayerPosition("0")`), étiquettes.

## Finalisation

- Sauvegarder via `buildScript("app.project.save();")` + playhead à 0.
- Vérifier: `get_full_project_overview` + `get_full_sequence_info` (duration ~5507.9s, totalClips 1653).
- NE JAMAIS exporter ni écraser Séquence 01 / fichiers montage_alternance_5s.mp4.
