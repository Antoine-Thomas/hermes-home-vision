# Installer un plugin tiers dans Hermes : verifier avant d'executer

A ouvrir des qu'on envisage d'installer ou d'activer un plugin / paquet tiers annonce pour Hermes
(avatar, voix, interface, extension de toolset) — et avant de repeter une affirmation d'integration
venue d'ailleurs.

## Principe

Un paquet annonce par une recherche web, un forum ou un autre assistant est une HYPOTHESE, pas un fait.
Cas reel : une description annoncait un plugin d'avatar « reutilisant ta config TTS et fournissant une
commande `hermes vtuber status` ». Le paquet existait bel et bien, mais les trois affirmations
d'integration etaient fausses pour cette installation. Cinq mesures gratuites separent l'hypothese du
fait — les faire AVANT d'installer quoi que ce soit.

## Les 5 mesures

1. **Existence et metadonnees, sans installer** :
   `curl -s https://pypi.org/pypi/<nom>/json` → lire `info.name`, `info.version`, `info.summary`,
   `info.author`, `info.license`, `info.project_urls`, `info.requires_dist`, et le bloc `releases`.
   Un HTTP 200 prouve que le paquet EXISTE, jamais qu'il fait ce qu'on annonce.
   - `releases` avec plusieurs versions publiees le MEME jour = paquet tres jeune : lire le code avant
     d'executer.
   - `requires_dist` est la surface reelle du risque : micro (`sounddevice`, `webrtcvad`), serveur web
     (`uvicorn`, `starlette`), STT (`faster-whisper`), wake-word (`openwakeword`). C'est ce qui
     s'installerait dans le venv Hermes.
2. **Licence** (`info.license`) : MIT / Apache = usage libre, monetisation comprise. AGPL-3.0 =
   copyleft fort. L'utilisateur monetise son contenu : verifier la licence du CODE avant d'integrer,
   comme on verifie celle des poids d'un modele.
3. **La commande annoncee existe-t-elle ?** `hermes --help` (puis `hermes <cmd> --help`). Une
   sous-commande citee dans une description de plugin peut n'exister dans aucune version installee.
4. **L'integration annoncee est-elle vraie CHEZ CET utilisateur ?** `grep -i <provider>
   <HERMES_HOME>/config.yaml` : un plugin qui « reutilise ta config TTS » alors que le moteur annonce
   n'apparait pas dans le fichier n'integrera rien. Verifier aussi ce qui tourne deja : `plugins.enabled`
   dans `config.yaml` et le contenu de `<HERMES_HOME>/plugins/`. Annoncer « il faut installer X » sans
   avoir regarde l'existant est une faute de mesure, pas une simplification.
5. **Le paquet fait-il ce que l'utilisateur VEUT ?** Un avatar Live2D pour l'interface de l'agent n'est
   pas un asset a incruster dans un montage video, et un overlay video n'est pas un plugin d'agent.
   Nommer l'usage final, verifier qu'il correspond, sinon on installe un outil qui ne resout pas le
   probleme pose.

## Installation (si les 5 mesures passent)

- Ne pas installer un paquet tiers non relu dans le venv Hermes. Pour un essai : venv isole.
- Activation : `plugins.enabled` dans `config.yaml` ; les plugins vivent dans
  `<HERMES_HOME>/plugins/` (installation par pip pour un paquet publie, copie de dossier pour un plugin
  local).
- Un besoin de production video (avatar incruste, overlay) se resout par un RENDERER autonome
  (node + ffmpeg, fichier de sortie a importer au montage), pas par un plugin de l'agent : voir les
  skills video (overlay / talking-head).

## Rapport

Donner les mesures brutes (code HTTP, version, licence, date de publication, sortie de `grep`), nommer
ce qui est verifie et ce qui reste une hypothese, et proposer la decision. Ne pas installer en silence
quand la description d'origine contient des affirmations fausses.
