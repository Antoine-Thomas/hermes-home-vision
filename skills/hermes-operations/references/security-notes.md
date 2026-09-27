# Notes de sécurité — accès aux dossiers utilisateur

## CodexSandboxUsers — accès lecture aux dossiers utilisateur

Le groupe local `OMATHS\CodexSandboxUsers` (créé par l'outillage Codex, description « Codex
sandbox internal group (managed) ») a un accès LECTURE (RX) permanent sur :

  - `C:\Users\searc\Desktop`
  - `C:\Users\searc\Documents`
  - `C:\Users\searc\Downloads`

ACE héritée par TOUT ce qui est déposé dans ces 3 dossiers.
Le profil `C:\Users\searc` lui-même n'a PAS cette ACE.

**Règle : ne JAMAIS déposer de secret dans ces 3 dossiers.**
Les jetons, clés et credentials vont dans `%LOCALAPPDATA%\hermes\.env` ou tout chemin hors des
3 ci-dessus.

Mesure : 27/09/2026 — 2 comptes actifs (CodexSandboxOnline, CodexSandboxOffline), aucun processus
en cours, `~/.codex` modifié le 22/09 (donc Codex encore utilisé).
Décision : conserver les ACE et les comptes, documenter la règle.
