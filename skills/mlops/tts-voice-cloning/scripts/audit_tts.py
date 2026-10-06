"""Audit de diction d'un moteur TTS : aller-retour Whisper sur un WAV genere.

Usage :
    python audit_tts.py <wav> <lang> ["texte attendu"]

A lancer avec le python de hermes-agent (faster-whisper CPU, modeles en cache) :
    "C:/Users/searc/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe" audit_tts.py out.wav fr "le texte"

Regles (voir SKILL.md) :
- Juger sur un paragraphe de >= 20-30 mots. Sur un clip isole de moins d'une seconde, Whisper
  invente des mots : la transcription ne prouve rien.
- Faire tourner un CONTROLE dans une autre langue sur le pipeline identique : si l'anglais est
  parfait et le francais casse, le defaut est la tete linguistique du moteur, pas l'installation.
- Les ecarts d'un seul mot homophone (demandez/demander) et les nombres normalises
  (« 91 » pour « quatre-vingt-onze ») sont la graphie de Whisper, PAS un defaut du TTS.
- faster-whisper sur CUDA echoue dans le venv hermes-agent (cublas64_12.dll) : rester en CPU int8.
"""
import os
import sys
import unicodedata

from faster_whisper import WhisperModel


def _norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    wav, lang = argv[1], argv[2]
    attendu = argv[3] if len(argv) > 3 else None
    if not os.path.exists(wav):
        print("FICHIER INTROUVABLE : %s" % wav)
        return 2

    model = os.environ.get("ASR_MODEL", "small")
    m = WhisperModel(model, device="cpu", compute_type="int8")
    segments, info = m.transcribe(wav, language=lang, beam_size=5)
    texte = " ".join(s.text.strip() for s in segments)

    print("FICHIER : %s" % wav)
    print("MODELE  : %s" % model)
    print("DUREE   : %.2f s   LANGUE : %s (p=%.3f)" % (info.duration, info.language, info.language_probability))
    if attendu:
        print("ATTENDU : %s" % attendu)
    print("ENTENDU : %s" % texte)

    if attendu:
        manquants = sorted(set(_norm(attendu).split()) - set(_norm(texte).split()))
        print("MOTS NON RETROUVES : %s" % (", ".join(manquants) if manquants else "aucun"))
        print("  (verifier chaque mot ci-dessus dans le contexte : Whisper reecrit les nombres et")
        print("   les homophones — un ecart d'un mot n'est pas forcement un defaut du TTS)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
