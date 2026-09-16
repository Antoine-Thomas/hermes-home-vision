## Environnement
- Windows 11, i7-8700, 64 Go, RTX 3070 Ti 8 Go (VRAM limitée)
- GPU bridé (30W/290W), perf IA limitées, diagnostic en cours
- Dev: WSL, tmux, MSYS_NO_PATHCONV=1, docker. Shell haute intégrité

## Hermes
Hermes v0.21.3 (2026.9.14), config v45. Gateway: default PID via schtasks Hermes_Gateway, watch PID via Hermes_Gateway_watch (tâche désactivée → relancer par hermes -p watch gateway start). multiplex_profiles=false explicite.
- Mémoire native: %LOCALAPPDATA%\hermes\memories\ (MEMORY.md + USER.md)
- Backend/gateway: 9119. Toolsets: hermes-cli, web, fichiers, terminal, browser
- Tâches: Reindex RAG 03h00, check memory 08h00, désaturer mémoire dim 04h00
- RAG reindexé post-update (2307 frag.) via data\rag\indexer.py
- Skills: %LOCALAPPDATA%\hermes\skills\. Archive: .archive/. hermes curator archive
- WP-CLI: C:\wp-cli\wp.bat (PHP Local). Local 10.1.2 (PHP 8.2.29/MySQL 8.4)

## Second cerveau
- SiYuan 3.8.2: 6806, workspace C:\Users\searc\SiYuan\hermes-projects, 6 notebooks
- RAG: %LOCALAPPDATA%\hermes\data\rag, e5-base, cache.db (TTL 24h), ~2284 frag.
- Routeur: router_memoire.py, hiérarchie 1→4, budget tokens, fraîcheur, contradictions

## Outils clés
- data\rag\: chercher, indexer, router_memoire, audit_rag, scan_secrets, serveur_rag (8200)
- scripts\: check_memory.ps1, desaturer_memoire.py
- OmniRoute 20128, NIM 20200, Vision OCR. DeepSeek: data/harness :3080 (Groq 8000 TPM)

## Préférences
- Réponses concises, français, expliquer changements. Documenter dans SiYuan pas MEMORY.md
- Vérifier avant d'affirmer, mesurer plutôt que supposer

## Règles transversales
- transformers < 5 obligatoire. Vérifier pviol + mclk au repos avant benchmark IA
- Jamais de téléchargement sans validation. Nouvelle info: SiYuan d'abord

## Vidéo
- Vidéo: fond bois/logo+CTA. Skill: talking-head-video-8gb (branche A=LatentSync, branche B=LivePortrait/SadTalker). VRAM 8Go: check avant rendu. Outils: data/video_youtube/. Projet: Desktop/hermes_tuto_v4/ → livrable "hermes tuto/". XTTS: data/xtts/venv.
