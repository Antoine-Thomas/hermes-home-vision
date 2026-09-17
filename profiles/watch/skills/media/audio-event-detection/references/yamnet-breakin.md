# YAMNet break-in detection — class list & calibration

## Resolved target classes (after exclusions)

Class map from `yamnet_class_map.csv`; kept classes whose display name matches a
target keyword and does NOT match an exclusion keyword.

Keywords: `glass, shatter, break, smash, door, slam, bang, crash, knock, impact`
Exclusions: `doorbell, bell, cymbal, keyboard, mouse, typewriter, engine`

Resulting 10 target classes (index varies by class-map version — match by name, not index):

```
Door, Sliding door, Slam, Knock, Glass, Shatter, Bang, Smash, crash, Breaking
```

Note: "Engine knocking" would match `knock` but is excluded via `engine`.
"Doorbell" and "Crash cymbal" are excluded via `bell` / `cymbal`.

## Calibration (session-verified)

| Input | Best target class | Score | Verdict |
|---|---|---|---|
| Quiet room capture (audio.mp3) | Glass | 0.000 | no trigger ✓ |
| Real glass shatter (orangefreesounds `Glass-shattering-sound-effect.mp3`) | Shatter | 0.965 | trigger ✓ |

Threshold 0.5 cleanly separates the two. Tune: 0.3 = more sensitive (more false
positives), 0.7 = conservative.

## Download a glass-break test sample

Direct MP3 URLs that worked:
- `https://orangefreesounds.com/wp-content/uploads/2025/01/Glass-shattering-sound-effect.mp3` (real recording, recommended)

(Test files are one-off downloads; prefer a real recording over an AI-generated SFX
for calibration — YAMNet was trained on real foley.)
