# PR #47 Review-Thread Disposition

Mission: `MP-CAT-A019-4C01`  
BEAD: `BEAD-CAT-A019-4C01-02`  
Captured: `2026-08-08T12:54:05.8260237Z`  
Source: GitHub GraphQL `reviewThreads` read-only query

All four threads are currently unresolved and not outdated. They are dispositioned below for a successor PR; no comments were resolved remotely.

| Thread | File | Finding | State | Disposition |
|---:|---|---|---|---|
| 3738648278 | `tests/test_cat_review_coverage.py:95` | Dry-run attestation assertion can vary when `CAT_OLLAMA_ATTESTATION_KEY` is set. | unresolved, not outdated | Make the test hermetic by clearing the attestation environment or assert the contract without depending on external signing state. |
| 3738648319 | `scripts/cat_review_coverage.py:14` | `sys`, `Path`, and `ROOT` are unused. | unresolved, not outdated | Remove unused imports and constant in the successor PR. |
| 3738648345 | `.github/workflows/claude.yml:15` | `github.ref` can be empty for issue events, collapsing concurrency to `claude-`. | unresolved, not outdated | Use an event-specific PR/issue identifier with a `run_id` fallback in the successor PR. |
| 3738648368 | `learnings/DECISION_LOG.md:36` | Adjacent entries conflict about whether Claude Code Review is retained or retired. | unresolved, not outdated | Consolidate the entries in a separately authorized governance change; this path is forbidden to A019-02. |

## Gate conclusion

The four findings are understood, but repairing them in PR #47 would require broadening the bounded A019-02 evidence-only BEAD and would include a forbidden `learnings/` path. The threads therefore remain unresolved pending a successor PR with its own mission/BEAD trace.
