# Energy Normalization & Duration Compensation (reusable logic)

## 1. Energy rank-normalization (librosa)

Raw RMS energy on compressed/loud masters collapses into a narrow low band,
so fixed thresholds never fire. Normalize by rank instead.

```python
import numpy as np, librosa

y, sr = librosa.load(path, sr=None)
frames = librosa.onset.onset_strength(y=y, sr=sr)
energy = np.array([window_energy_i])            # raw, 0..~0.5
order = np.argsort(energy)
rank = np.empty_like(order, dtype=float)
rank[order] = np.linspace(0.0, 1.0, len(energy)) # NOW in 0..1
# use `rank` as the per-segment `energy` fed to source/transition selection
```

Thresholds `0.3 / 0.7` then split calm / mid / hot reliably on ANY track.

## 2. xfade duration compensation

Output video duration when chaining N clips with xfade durations T[1..N-1]:

```
total_video = sum(durations[0..N-1]) - sum(T[1..N-1])
```

Each xfade of length T overlaps T seconds between two clips.

To make the video cover the WHOLE audio (length `L_audio`), append a pad
segment (same source & energy as the last real segment):

```
P = sum(T[1..N-1]) + T_last      # T_last = transition of the appended pad
pad_duration = P
# now: total_video = sum(durations[0..N-1]) + P - (sum(T) + T_last)
#                    = sum(durations[0..N-1])  == L_audio (when segments span the track)
```

Then `atrim=0:total_video` on the audio so audio length matches exactly.

### xfade offset formula
For the i-th xfade (i from 1 to N-1):
```
offset_i = cumulative_sum(durations[0..i-1]) - cumulative_sum(T[1..i])
```
The first clip starts at 0; each subsequent xfade begins after the prior
clip minus the overlap already consumed.
