RTX 3070 Ti 8 Go: SDXL LoRA non viable (spill WDDM, 207 s/pas @1024, 37 @512). Validé = SD 1.5 512px: 1,8 s/pas, 3,5 Go VRAM, 0 spill, 1800 pas/53 min sans reset. Plus de resets GPU depuis 16/09.
§
## Hermes
Hermes v0.21.3 (config v45). Gateway default+watch (schtasks), multiplex_profiles=false, backend 9119. Toolsets: hermes-cli, web, fichiers, terminal, browser. Mémoire native %LOCALAPPDATA%\hermes\memories\ (MEMORY.md+USER.md). Skills %LOCALAPPDATA%\hermes\skills\ (+.archive/). WP-CLI C:\wp-cli\wp.bat (PHP Local 10.1.2, 8.2.29/MySQL 8.4). Cron: reindex RAG 03h, check memory 08h, désaturer mémoire dim 04h.
§
## Second cerveau
SiYuan 3.8.2 (6806), workspace C:\Users\searc\SiYuan\hermes-projects, 6 notebooks. RAG data\rag: chercher, indexer, router_memoire, audit_rag, scan_secrets, serveur_rag (8200); e5-base, cache.db TTL 24h, ~2300 frag. Routeur: hiérarchie 1→4, budget tokens, fraîcheur, contradictions.
§
Audit LoRA/vidéo: venv dédié data\video_youtube\LatentSync\venv (insightface buffalo_l + cv2); rapport data\sdxl_lora\docs\LORA_VISAGE_RUN_2026-09-17.md
§
## Préférences
- Français, concis, ciblé; expliquer chaque changement. Documenter dans SiYuan, pas MEMORY.md
- Vérifier avant d'affirmer; mesurer plutôt que supposer
§
## Règles transversales
- transformers < 5 obligatoire. Vérifier pviol + mclk au repos avant benchmark IA
- Jamais de téléchargement sans validation. Nouvelle info: SiYuan d'abord
§
Skills: 90 actifs (7 désactivés). Bots Telegram: default=@Hermes_assistante_2026_bot (chat 8956868107), veille=@Hermesveille1_veille_bot, watch=@Omaths2_watch_bot (tâche désactivée, exclu du healthcheck)
§
Hermes dans hermes-agent\ : hermes-agent\venv = seul venv actif (PATH, tous lanceurs); .venv → .venv.retired-0.20.5 (rétention ~19/10). Détail docs\HERMES_VENVS.md