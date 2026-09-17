---
name: hermes-memory
description: Hermes memory routing, curation, and lifecycle management.
version: 1.0.0
---

# Hermes Memory Management

Procedures for managing the hierarchical memory of Hermes Agent, balancing native markdown memory, vector-based RAG, and structured SiYuan documentation.

## Hierarchical Routing Procedure
Before every query requiring external information, determine the necessary source level to avoid unnecessary RAG consumption:
1. **MEMORY.md + USER.md**: Always loaded.
2. **SiYuan (API 6806)**: For projects, decisions, and structured documentation.
3. **RAG (port 8200)**: For technical traps, thresholds, and measures.
4. **Skills Hub**: For domains not covered locally.

**Run the router before RAG:**
```bash
python "%LOCALAPPDATA%\hermes\data\rag\router_memoire.py" "question"
```

## Curation & Lifecycle
- **Anti-accumulation**: Run `audit_rag.py` monthly to detect never-cited, obsolete, or redundant fragments.
- **Secret Protection**: `indexer.py` automatically filters secrets (tokens, API keys) based on `SECRET_PATTERNS`.
- **Memory Limits**: `check_memory.ps1` alerts when `MEMORY.md` > **2100** chars or `USER.md` > **1300** (older notes say 1375 for USER — 1300 is current). MEMORY's hard injection cap is 2200; 2100 is the early-warning line, so aim under the alert threshold, not merely under the cap. The script measures raw CRLF, so a Python `len(open(f).read())` on universal newlines reads ~2 chars/line LOWER and is not authoritative for the alert.
- **Desaturation**: When MEMORY.md or USER.md approaches saturation, archive old entries to SiYuan and rewrite to regain margin. Since 2026-09-17 this is scripted: `%LOCALAPPDATA%\hermes\scripts\desaturer_memoire.py` (`--dry-run` default, `--auto` only above the alert thresholds) + scheduled task « Hermes - desaturer memoire », Sunday 04:00, log `scripts/desaturation.log`. It requires SiYuan up (otherwise it changes nothing, exit 1), archives the whole file into `journal / Archive <FICHIER> - <date>` before rewriting, keeps a `.bak`, rolls back if the size is still over the threshold, and refuses to touch protected sections. Full decision rules in `references/desaturation.md`.
- **Obsolescence**: Apply the `> À revérifier: YYYY-MM-DD` convention to SiYuan documents.

## Staged writes — the write-approval queue

Memory (and skill) writes can be *staged* instead of committed: `agent/background_review.py`, and any turn with `memory.write_approval: true`, writes a JSON proposal under `%LOCALAPPDATA%\hermes\pending\<subsystem>\<id>.json`. Each record carries `payload.target` (`memory` → MEMORY.md, `user` → USER.md) and `payload.operations[]` (`replace old_text → content`, or `add`). A proposal is inert until applied.

**There is no `hermes memory pending`** — `hermes memory` exposes only `setup|status|off|reset`. Review through the `/memory` slash command (`/memory pending`, `/memory approve <id>`, `/memory reject <id|all>`), or drive the same handler from the CLI:

```python
# Hermes venv python, HERMES_HOME set
from tools import write_approval as wa
from hermes_cli.write_approval_commands import handle_pending_subcommand
from tools.memory_tool import load_on_disk_store
print(handle_pending_subcommand(wa.MEMORY, ["pending"], memory_store=load_on_disk_store()))
```

Rules that matter:
- **Apply to the file named by `payload.target`, never the file the text seems to fit.** A `[MEMORY]` proposal written into USER.md saturates USER and forces unrelated lines to be truncated.
- **Discard the entry after applying it by hand** (`reject <id>`): operations are `replace old_text → content`, so a leftover proposal whose `old_text` still matches re-applies on the next sweep and duplicates the inserted line.
- **Read the operations and sum their size deltas against the real current size before writing.** A single "compact" memory line runs ~250 chars and a small two-op batch ~235 — on a file already near the alert threshold that is the whole remaining margin.
- **Verify the write landed before reporting it applied** — grep the target file for the new text and re-run `check_memory.ps1`. Reporting a proposal as applied without that read lets an unapplied proposal survive an entire session as a false fact.

## Pitfalls
- **`§` separators are structural, not cosmetic.** The store splits entries on `ENTRY_DELIMITER = "\n§\n"` (`tools/memory_tool_store.py`). A memory file rewritten as markdown `##` sections separated by blank lines is read as **one single entry** — so any `replace`/`remove` rewrites the whole file and silently destroys every other entry. Keep a line containing only `§` between entries, and check the format after any external edit: a restructured file is a loaded gun, not a styling choice.
- **Recovering an entry list wiped by a `replace`**: the memory tool keeps no history (`hermes memory` = `setup|status|off|reset` only) and `.bak` files may predate several rewrites. The most faithful copy of the start-of-session file is the memory block injected into the session prompt — rebuild from it, re-insert the `§` separators, then verify the entry count by splitting the file on `"\n§\n"` in a **fresh process**.
- **Never call the memory tool again in a session after editing MEMORY.md/USER.md outside it**: the session's store still holds the pre-edit entries and a later flush writes that stale view back over the file. A read-only probe (`replace` without `old_text`) returns `current_entries` from the stale store, so it confirms nothing about the disk.
- **File locations (real paths)**: MEMORY.md and USER.md live in the **`memories/` subdirectory** of `%LOCALAPPDATA%\hermes` (`...\hermes\memories\MEMORY.md`), NOT at the `%LOCALAPPDATA%\hermes\` root. Many prompts/doc refer to the root; always check the `memories\` subdir first.
- **SiYuan fragment checks**: SiYuan `hpath` (`/Title`) is a virtual path, not a disk path — `audit_rag.py` must only existence-check local sources (skill/script_v4/wordpress), never mark siyuan fragments obsolete for a missing path.
- **Cache invalidation**: cache.db (SQLite, TTL 24h) must be emptied after every `indexer.py` reindex — stale cached results otherwise serve an old index. Purge >7-day entries on server startup.
- **RAG HTTP server (8200)**: `serveur_rag.py` is manual-only — no scheduled task starts it. Launch it detached (`cmd //c "start /b …"`); `GET /sante` returns the fragment count and per-source breakdown (siyuan/skill/script_v4/wordpress). After a reindex the running server still holds the OLD index in memory — call `POST /recharger` (relit l'index sur disque) or restart it, or searches silently serve stale results.
- **Vector index vs Memory**: The vector index is a table of contents, not a brain. Always prefer structured markdown when available.
- **Secret Leaks**: Never hardcode tokens in skills or documents. Placeholders (e.g., `<token>`) are safe, real secrets are filtered but must be avoided.
- **Token Budget**: Respect token budgets per level to avoid cost runaway: Niv2 (500), Niv3 (1500), Niv4 (3000).
