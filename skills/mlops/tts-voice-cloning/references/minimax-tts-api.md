# MiniMax T2A v2 (API cloud) — notes verifiees

Endpoint synchrone HTTP : `POST https://api.minimax.io/v1/t2a_v2`
(headers `Authorization: Bearer <cle sk-...>` + `Content-Type: application/json`).

- **Hosts** : une cle `sk-` emise sur `platform.minimax.io` n'est valable QUE sur
  `api.minimax.io/v1`. Les hotes CN/anciens (`api.minimaxi.com/v1`, `api.minimax.chat/v1`)
  repondent `base_resp.status_code=2049 'invalid api key'` — ce n'est pas un probleme de cle.
  Ne pas conclure « cle invalide » sans tester `api.minimax.io` en premier.
- **Modeles** : `speech-02-hd` (defaut), `speech-02-turbo`, `speech-2.6-*`, `speech-2.8-*`.
- **Corps** : `{model, text, stream:false, language_boost:"French",
  voice_setting:{voice_id, speed:1.0, vol:1.0, pitch:0},
  audio_setting:{sample_rate, bitrate, format, channel}, output_format:"hex"}`.
  Formats non-streaming : `mp3`, `wav`, `flac` (`pcm` refusé hors streaming).
- **Reponse** : l'audio arrive en HEX dans `data.audio` (`bytes.fromhex(...)`), la duree en ms
  dans `extra_info.audio_length`. Toujours verifier `base_resp.status_code == 0`.
- **Taille** : `text` < 10 000 caracteres ; au-dela de 3 000, la doc recommande le streaming.

## Voix systeme francaises (a passer en `voice_id`)

| voice_id | nom | usage |
|---|---|---|
| `French_Male_Speech_New` | Level-Headed Man | narration / pro (defaut masculin) |
| `French_MaleNarrator` | Male Narrator | narration |
| `French_CasualMan` | Casual Man | ton decontracte |
| `French_FemaleAnchor` | Female Anchor | info |
| `French_Female_News Anchor` | Patient Female Presenter | info |

Liste complete : `https://platform.minimax.io/docs/faq/system-voice-id` (ou API Get Voice).

## Codes d'erreur qui changent la decision

- `1008 insufficient balance` : **la cle est valide**, c'est le COMPTE qui n'a plus de credit.
  Erreur au niveau compte : tous les modeles et toutes les voix echouent pareil. Inutile de
  re-essayer un autre modele ou un autre hote — il faut recharger le compte. A signaler tel quel,
  sans fabriquer d'audio.
- `2049 / 1004` : cle refusee par cet hote (mauvais domaine) ou cle invalide.

## Pieges d'environnement

- **Un `.env` peut coller un caractere U+FFFD (`EF BF BD`) en fin de cle**, avant le CR.
  Un en-tete HTTP est encode en latin-1 : `urllib` leve alors
  `UnicodeEncodeError('latin-1', 'Bearer ...', 133, 134, ...)`. Filtrer la cle sur
  `ord(c) < 128` avant de l'envoyer, et le signaler (le `.env` est a corriger).
- **Python 3.14 nu n'a ni `requests` ni `numpy`** : faire l'appel en `urllib.request` + `json`,
  et la concatenation WAV avec le module stdlib `wave` (16 bits PCM ; `audioop` a disparu en 3.13).
- **Concatenation multi-chunks** : normaliser CHAQUE chunk en 16 kHz mono s16le avec ffmpeg
  (`-ar 16000 -ac 1 -c:a pcm_s16le`) avant de joindre les frames — les en-tetes WAV renvoyes
  par l'API ne sont pas concatenables en l'etat.
