# Pacing / diction control + backup-before-regenerate

## Text chunking IS the pacing lever
The same voice + text can read fast-and-flowing OR slow-and-breathy, controlled
ONLY by how the .txt is structured — each `Speaker N:` turn boundary inserts a
pause/silence at that point.

- **Flowing / fast / natural** = ONE `Speaker 1:` line at the very top, then
  flowing paragraphs separated by blank lines. The whole episode is a single
  turn → no forced pauses.
  Measured: single turn ≈ 1936 generated tokens → 257 s for an ~1800-word episode.
- **Slower / breathes between sentences** = a `Speaker 1:` before EVERY sentence
  (one sentence per turn). Every boundary adds a pause.
  Measured: 67 one-sentence turns = 68 segments → 2595 tokens → 328 s.
  The extra ~86 s is pure inserted silence.

To fix "diction trop rapide, il faut respirer": add MORE turn boundaries — but
go INCREMENTAL (group 2-3 sentences per turn first). One-sentence-per-turn is
the extreme and reads choppy. Over-correcting straight to 67 one-sentence turns
is what made the user ask to revert to the flowing version.

## Backup before regenerating (user requirement)
`inference_from_file.py` writes to the SAME `--output_dir/<name>_generated.wav`
every run, OVERWRITING the previous audio. TTS is non-deterministic (no seed),
so the overwritten audio is unrecoverable byte-for-byte.

Rule: before regenerating a voice/audio the user has already approved, `cp` the
current output to a backup name first, e.g.
`outputs_episode2/episode2_fluent_backup.wav`.

To recover an ALREADY-overwritten version: the voice (e.g. `MaVoix`) and the
episode CONTENT both survive — only the text-file formatting is lost. Find the
original text via `session_search` (the user's prompt with the full text is in
history), reconstruct the flowing format (restore elision apostrophes:
`l'Anima`, `n'était`, `s'élevaient`), and regenerate.
