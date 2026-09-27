RTX 3070 Ti 8 Go: SDXL LoRA non viable (spill WDDM); validé SD 1.5 512px: 1,8 s/pas, 3,5 Go VRAM, 0 spill, 1800 pas/53 min. Aucun reset GPU depuis 16/09.
§
Hermes v0.21.5+2729.gcdcd53c (config v46). Gateway = tâche Hermes_Gateway (+ HealthCheck), multiplex_profiles, 4 canaux en polling, 0 port. Backend 9119 et RAG 8200 définis, à l'arrêt. WP-CLI C:\wp-cli\wp.bat. Cron: reindex RAG 03h, check memory 08h, désaturation dim 04h. Chemins: mémoire/skills sous %LOCALAPPDATA%\hermes\ (+ skills\.archive\).
§
SiYuan 3.8.2 (6806), workspace C:\Users\searc\SiYuan\hermes-projects, 6 notebooks. RAG data\rag: chercher, indexer, router_memoire, audit_rag, scan_secrets, serveur_rag (8200); e5-base, cache TTL 24h, ~2300 frag. Routeur: hiérarchie 1→4, budget tokens, fraîcheur, contradictions.
§
Audit LoRA/vidéo: venv dédié data\video_youtube\LatentSync\venv; rapport data\sdxl_lora\docs\LORA_VISAGE_RUN_2026-09-17.md
§
Skills: 98 actifs (7 désactivés). Bots: default=@Hermes_assistante_2026_bot (chat 8956868107), veille=@Hermesveille1_veille_bot, watch=@Omaths2_watch_bot (désactivé).
§
hermes-agent\: venv = seul venv actif (PATH, lanceurs); .venv → .venv.retired-0.20.5. Détail docs\HERMES_VENVS.md
§
Git: dépôt canonique %LOCALAPPDATA%\hermes (remote Antoine-Thomas/hermes-home-vision, public, main); clone de lecture C:\Users\searc\Projets\hermes-home-vision, (rafraîchir après push). installs/ et tools/ (~2,5 Go) exclus via .git/info/exclude.
§
Règles: transformers < 5. Vérifier pviol + mclk au repos avant benchmark IA. Jamais de téléchargement sans validation; info nouvelle → SiYuan.
§
Préférences: français, concis, ciblé, expliquer chaque changement. Documenter dans SiYuan, pas MEMORY.md. Vérifier avant d'affirmer, mesurer plutôt que supposer.