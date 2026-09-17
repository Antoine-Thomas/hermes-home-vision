# French Diction Tricks — measured spellings for XTTS-v2

Settings these measurements come from: XTTS-v2, `language="fr"`, `temperature=0.87`,
`speed=0.95`, this user's reference voice. Re-validate on the actual reference voice —
the method below is what transfers, not the exact strings.

## Validation lab (do this before writing a full script)

1. Write one short sentence per candidate spelling of the term in doubt.
2. Generate each to its own WAV (XTTS venv, 3 s each).
3. Transcribe each with faster-whisper (`small`, `language="fr"`) — the Hermes venv has it.
4. Keep the spelling the transcription returns correctly. Do not arbitrate by ear, and do
   not trust a single run: re-generate the loser once before ruling it out.

## Spelling table (measured)

| term | spelling that works | transcribed as | spelling that fails |
|------|--------------------|----------------|---------------------|
| WP-CLI | `double-vé-pé cé-èle-i` | « WP-CLI » | `WP-C-L-I` -> « WBCL-I » |
| nginx | `n-jin-x` | « Nginx », « EngineX » | `ène-jine-ixe` -> « NGNIS » |
| MySQL | `Maï-Ess-Cu-Elle` | « MySQL » | bare `MySQL` -> « Miskillon » |
| rsync | `Ar-sink` | « Arsync » | `Ère-sinque` -> « R5 » |
| Docker | `Dockeur` | « Docker » | — |
| Hermes | `Hermesse` | « Hermès » | — |
| WooCommerce | `WooCommerce` | « ou-commerce » | `Wou-Commerce` -> « ou commerce » |

General shape: spell an acronym as French syllable names separated by spaces, and spell a
brand as the French pronunciation in one word. A hyphen inside an acronym makes XTTS read it
as a single English word; spaces make it read letter names.

## Sentences and structures XTTS mangles (rewrite, do not "fix")

| written | comes out as | rewrite as |
|---------|--------------|------------|
| « je vous montre comment monter un environnement » | « comment on t'envie mon environnement » | « on installe ensemble un environnement » |
| « le guide d'installation » | « le deal d'installation » | « la documentation » |
| « des modèles réutilisables » | « des mails réutilisables » | « des configurations réutilisables » |
| « WordPress Deployment » | « WordPress the program » | « le déploiement WordPress » |
| « Troisième skill : … » (ordinal alone) | « GameSkill … » | « Le troisième : le skill … » |
| « Cinquième : … » | ok | — |

Pattern: an ordinal or short label glued in front of an English-looking word gets swallowed;
an English job title inside a French sentence gets replaced by a similar-sounding English
phrase. Keep ordinals in a full French phrase (`Le troisième : …`) and rename English product
names to their French description.

## Do not read command lines aloud

Reciting a CLI invocation with its flags produces an unintelligible stretch (whisper shows a
multi-second hole in the transcript even though the RMS is full). Say what the command does,
and send the exact command to the video description instead.

## After generating the whole voice

Transcribe the assembled WAV end to end and diff it mentally against the script: any hole in
the transcript is an unintelligible passage (not a silence — verify with the RMS), and any
term that came back wrong goes into the spelling table above.
