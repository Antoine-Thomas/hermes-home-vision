# Wiki Index

> Catalogue du contenu. Chaque page wiki est listée sous son type avec un
> résumé d'une ligne. **Lire ce fichier en premier** pour trouver les pages
> pertinentes d'une question.
> Last updated: 2026-09-22 | Total pages: 17

## Concepts
- [[auto-best-free]] — Le modèle `auto/best-free` était configuré comme primary, mais il ne répond jamais (400/502).
- [[auto-best-reasoning]] — Alias payant (Anthropic via OpenRouter), ecarte de la chaine le 22/09/2026.
- [[deepseek-flash]] — `deepseek-flash` est utilisé comme dernier étage payant de la chaîne de repli.
- [[eco]] — Eco est un modele de palier gratuit servi via OmniRoute, utilise comme premier etage de la chaine de repli.
- [[fallback-chain]] — La chaine de repli est la liste ordonnee des modeles que Hermes sollicite lorsque le modele principal devient indisponible.
- [[fallback-providers]] — La configuration `fallback_providers` spécifie les couples provider/modèle utilisés en cas d'échec du primaire.
- [[free-openrouter]] — Le combo free-openrouter a été ajouté à OmniRoute le 22‑09‑2026.
- [[hermes-config]] — La configuration d'Hermes définit le modèle par défaut (`eco`), le provider (`omniroute`), la chaîne de repli via `fallback_providers`, et le nombre maximal de tentatives (`agent.api_max_retries`).
- [[jev]] — Jev est le skill TypeSafe intégré à Hermes pour trancher les choix rapides.
- [[nvidia-stack]] — Le `nvidia-stack` constitue un étage de repli gratuit basé sur les modèles NVIDIA.
- [[primary-model]] — Le modele principal est le premier a repondre a une requete.
- [[provider-connection]] — Dans OmniRoute, une connexion fournisseur definit la facon dont un service d'IA externe est atteint.
- [[state-db]] — La base d'etat (`state.db`) conserve l'historique d'usage des modeles par session : quel modele a servi chaque requete, a quel moment, et les details de facturation associes.
## Entities
- [[hermes-agent]] — Hermes Agent (v0.21.4) est l'agent IA local central : il achemine les requetes via une chaine de repli configurable, s'integre a OmniRoute et a SiYuan, et tourne sur un GPU local RTX 3070 Ti.
- [[nvidia-nim-proxy]] — Le proxy NIM expose les modèles NVIDIA via l'URL 127.0.0.1:20200 et assure la traduction entre les appels Hermes et les endpoints NVIDIA.
- [[omniroute]] — OmniRoute (port 20128) est le routeur de modeles qui selectionne les fournisseurs et les combos pour Hermes.
- [[openrouter]] — OpenRouter est un provider de modèles accessible via une clé API stockée dans `.env`.
## Comparisons
<!-- ordre alphabetique -->
## Queries
<!-- ordre alphabetique -->
## Syntheses
<!-- ordre alphabetique -->
