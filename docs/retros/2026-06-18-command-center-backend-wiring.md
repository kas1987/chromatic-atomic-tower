# Session Retrospective — Command Center Backend Wiring

**Date:** 2026-06-18
**PRs merged:** none (reference/ assets, not in CI scope)
**Epics closed:** none (this was operator-plane work under CAT manifest §6.1)
**Files changed:**
- `reference/server.py` — new Python stdlib HTTP server (7 endpoints)
- `reference/dashboard.html` — added DOM IDs + replaced static JS with live-fetch polling

---

## What shipped

- **`reference/server.py`** — `ThreadingHTTPServer` (stdlib + PyYAML, no extra deps) serving:
  - `GET /` → dashboard.html
  - `GET /api/state` → `state/TOWER_STATE.yaml`
  - `GET /api/beads` → all BEADs from active/queued/completed/failed dirs, `_dir` field added
  - `GET /api/agents` → `AGENT_SCORECARD.yaml` merged with `AGENT_REGISTRY.yaml` (autonomy_level, can_dispatch)
  - `GET /api/gates` → computed from active BEAD confidence scores
  - `GET /api/events` → normalized transition_history entries, last 7 days, latest 25
  - `GET /api/all` → one-shot payload for dashboard polling
- **Live dashboard** at `http://localhost:8000` polling every 5 seconds:
  - Real sprint (SPRINT-012), 92 BEADs, 7 agent scores, 25 events
  - Green connection dot when backend live, amber when offline (static data fallback)
  - Kanban active column, scorecard bars, events feed, gates summary all dynamic

---

## Learnings

### 1. YAML→JSON serialization: always `default=str`
PyYAML parses YAML timestamps as Python `datetime` objects. `json.dumps(data)` throws on them.
Fix: `json.dumps(data, default=str)` everywhere. This is a mandatory rule for any Python server reading YAML.
**Action:** Add to CAT pattern library as a server bootstrap requirement.

### 2. Field-renaming normalization layer breaks downstream filters
Normalized transition_history entries from `from_status/to_status/timestamp/guard_ok` → `from/to/time/ok` for the JS.
The filter code immediately below still used the old field names (`event.get("timestamp")`), returning 0 events.
Caught only by live-testing `/api/events` after server start.
**Action:** When you rename fields in a normalization function, grep for old field names in the same function scope before shipping.

### 3. Multiple server instances cause stale-code testing
Restarted server twice but old PIDs (26488, 26052) were still bound to :8000. Fixed version never got traffic.
`netstat -ano | Select-String ":8000 "` revealed two LISTENING entries.
**Action:** Before restart, explicitly `Stop-Process` all PIDs on the target port, not just the last known PID.

### 4. Parallel subagent delegation (haiku + fork) worked cleanly here
Haiku agent wrote the mechanical server.py; fork agent added IDs and JS. Both completed without conflicts
because their file scopes were non-overlapping (server.py vs dashboard.html).
The fork needed full conversation context (knew the HTML structure) — justified the fork over a fresh agent.
**Action:** Parallelise on file-scope separation, not just task-type separation. Confirm non-overlapping paths before dispatch.

---

## KPI snapshot

| KPI | Value |
|---|---|
| Active BEADs in registry | 18 |
| Completed BEADs | 49 |
| Failed BEADs | 25 |
| Agent roles | 7 |
| Builder score | 100.0 |
| Avg confidence (active BEADs) | 83.6 (warn band) |
| Live events returned | 25 |
| Server startup time | <2s |

---

## Follow-up

- Gate confidence avg 83.6 is in `warn` band — worth checking active BEADs to see which are pulling it below 85
- The `failed/` BEAD directory has 25 entries — worth a quick sweep to see if any warrant incident log entries
- `reference/server.py` is not under CI scope; if CAT ever adds a server test suite, this file should move to a proper `src/` or `tools/` location
- No BEAD was claimed for this work — it was operator-plane. If the dashboard becomes a mission deliverable, open a BEAD under the next sprint.
