# Evidence Archival Policy

**Version:** 1.0.0  
**Effective:** 2026-06-21  
**Owner:** Human Owner  
**Review Cycle:** Every 5 sprints (e.g., after Sprint 020)

---

## Purpose

The Evidence Plane (`evidence/`) accumulates records from every mission and BEAD execution. Without an
archival policy, this directory grows unbounded, increasing clone time, search latency, and cognitive
overhead for operators.

This policy defines when and how evidence is archived, what data is retained indefinitely, and the
automation (Sprint A015) that executes archival procedures.

---

## Archival Rules

### Rule 1: Evidence Older Than 90 Days

Evidence artifacts older than 90 days move from `evidence/` to `evidence/archive/YYYY/MM/`.

**Examples of archival-eligible evidence:**
- CI reports: `evidence/ci/cat_ci_report_MISSION_ID.json` (timestamps tracked)
- BEAD execution logs: `evidence/logs/BEAD_ID_*.jsonl`
- Diffs and patches: `evidence/diffs/*.patch`
- Manually-generated test results and screenshots: `evidence/manual/*.json`

**Archive path structure:**
```
evidence/archive/
  2026/
    Q2/  (April–June)
      cat_ci_report_MP_CAT_A011_4C01.json
      BEAD_CAT_A011_4C01_01_execution.jsonl
    Q3/  (July–September)
      ...
```

**Exclusions — these evidence types are NOT archived:**
- `evidence/scorecard/` — agent scorecard records and reports (kept indefinitely; high-signal, low-volume)
- `evidence/bundles/` — evidence bundle contracts (required for audit trail; keep indefinitely)
- `evidence/gate_results/` — confidence gate, human gate, and promotion gate records (keep indefinitely)

### Rule 2: Scorecard Records Retained Indefinitely

`agents/scorecards/*.yaml` records are kept in the active directory forever. They are:
- Small (< 100 bytes each)
- High-signal (directly inform agent promotion/demotion decisions)
- Part of the audit trail for trust evolution

**No archival of scorecard records.**

### Rule 3: Learnings Retained Indefinitely

`learnings/` artifacts are kept in place. They include:
- `DECISION_LOG.md` — operator decisions and governance changes
- `INCIDENT_LOG.md` — incidents and remediation (when created)
- Post-sprint retros and lessons learned

**No archival of learnings.**

### Rule 4: Archive Is Tracked

The `evidence/archive/` directory and its contents are tracked in git, NOT gitignored.

**Rationale:** Archive provides audit trail continuity for compliance and forensics. It should be
part of the permanent repository history.

---

## Archival Procedure

### Manual Archival (until Sprint A015)

```bash
python scripts/cat_archive_evidence.py --dry-run
python scripts/cat_archive_evidence.py --run
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
```

### Automated Archival (Sprint A015+)

`scripts/cat_archive_evidence.py` implements:
- `--status` — report how many artifacts are eligible for archival
- `--dry-run` — show proposed moves without executing
- `--run` — execute archival; move artifacts to `evidence/archive/YYYY/QN/`
- `--older-than DAYS` — override the 90-day default

**Automation integration:**
- Cron job or post-sprint hook runs archival after sprint closeout
- Warnings logged to `evidence/logs/archival_*.jsonl` for each run
- `cat_check_repo.py` reports unarchived stale evidence as a warning (not blocking)

---

## Audit Trail

Archival operations are logged at:
```
evidence/logs/archival_2026_06_21.jsonl
evidence/logs/archival_2026_07_19.jsonl
...
```

Each entry includes:
- Timestamp
- Archived file path
- File size
- Destination path
- Git commit SHA (if committed immediately)

---

## Lifecycle Examples

### Example 1: CI Report from Sprint A011 (completed 2026-06-18)

**2026-06-18:** `evidence/ci/cat_ci_report_MP_CAT_A011_4C01.json` created.  
**2026-09-18:** Becomes eligible for archival (90 days old).  
**2026-09-20:** Archival runs; moves to `evidence/archive/2026/Q3/cat_ci_report_MP_CAT_A011_4C01.json`.  
**Forever:** Stays in git history; accessible via `git log --all` or blame.

### Example 2: Agent Scorecard Record (2026-06-18)

**2026-06-18:** `agents/scorecards/BEAD_CAT_A011_4C01_01_Builder_bead_completed.yaml` created.  
**Forever:** Retained in active directory, never archived.  
**Audit:** Supports any future inquiry into Builder's promotion to trusted on 2026-06-21.

### Example 3: DECISION_LOG Entry (2026-06-21)

**2026-06-21:** Human Owner records operator hygiene decision.  
**Forever:** Retained in `learnings/DECISION_LOG.md`.  
**Audit:** Foundation for future governance retrospectives.

---

## Review and Update

This policy is reviewed every 5 sprints (approximately every 6–8 weeks, depending on sprint duration).

**Next review:** Post-Sprint 020 (estimated Q2 2027).

Updates required if:
- Archive query time exceeds 5 seconds (scale to a sharded archive)
- Archive grows beyond 100 MB (tighten retention window to 60 days)
- New evidence plane types are added (update Rules 1–3 to classify them)

---

## Appendix: Integration with Sprint A015

**Sprint A015: Evidence Archival Automation** implements this policy via 4 BEADs:

| BEAD | Task |
|------|------|
| BEAD-CAT-A015-4C01-01 | Define `archive.schema.json` and archival eligibility rules |
| BEAD-CAT-A015-4C01-02 | Build `scripts/cat_archive_evidence.py` CLI |
| BEAD-CAT-A015-4C01-03 | Wire archival check into `cat_check_repo.py` |
| BEAD-CAT-A015-4C01-04 | Run pilot archive cycle + evidence + docs |

**Expected outcome:** Full automation ready for post-A015 deployment.
