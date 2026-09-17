# Scripts SiYuan (second cerveau)

- `demarrer_siyuan.cmd` — démarre le noyau sur 6806 (ne fait rien s'il tourne déjà).
- `creer_tache.ps1` — crée la tâche planifiée utilisateur de démarrage à l'ouverture de session.
- `gather_sites.py` — relit l'état réel des sites Local (versions, extensions, sauvegardes).
- `construire_structure.py` — construit les 6 notebooks et leurs documents ; n'écrase rien.
- `import_notes.py` — importe des notes Markdown (option `--remplacer`).

Emplacement d'origine : `C:\Users\searc\SiYuan\`. Le jeton d'API est lu dans
`%LOCALAPPDATA%\hermes\.env` (variable `SIYUAN_TOKEN`) — aucun secret dans ces fichiers.
