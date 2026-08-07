# PR Review Workflow

## Purpose

Define how CAT pull requests collect review signal without treating flaky or experimental bots as merge blockers.

## Review Chain

| Order | Reviewer | Source | Role |
|---|---|---|---|
| 1 | Codex | GitHub Actions (`codex-review.yml`) | Automated first pass on `pull_request` |
| 2 | Copilot | GitHub native Copilot review | Second automated pass |
| 3 | Human | Manual triage | Decide merge / fix / escalate |

Do not short-circuit the chain: wait for Codex and Copilot settle before declaring a PR thread-clean.

## Settle Windows

Automated reviewers often post (or update) comments after the push event that triggered them.

| Action | Guidance |
|---|---|
| After push / synchronize | Wait **90–180 seconds** before claiming "no review threads" |
| Before merge | Re-check Conversations and Checks after the settle window |
| Flaky bot noise | Classify under advisory signal; do not promote to required without a stability window |

## Check vs Review

| Class | Examples | Merge impact |
|---|---|---|
| Required CI | `validate`, `cat-ci` | Must pass |
| Advisory CI / review | `governance-ci`, `loghouse-ci`, `github-bridge`, `codex-review` | Informational |
| Native review | Copilot | Triage manually |

`codex-review` remains **advisory until a stability window** completes. Do not add it as a required status check prematurely.

## Branch Protection Notes

| Setting | Status |
|---|---|
| Required status checks (`validate`, `cat-ci`) | Expected for promotion |
| `required_conversation_resolution` | **Deferred to next PR** — do not enable in this hardening pass |

## Phase 2 — Ollama Cloud Artifact Seat (scaffold)

Advisory only. Not a required CI check. Scaffolds land in-repo; dual-LLM quorum
enforcement and Ollama CI wiring remain deferred (see Appendix).

| Script | Role |
|---|---|
| `scripts/cat_review_coverage.py` | Provider allowlist + `quorum_needed_for_level` / `evaluate_quorum` |
| `scripts/cat_ollama_pr_review.py` | Writes `evidence/reviews/pr-{N}.json` (`--dry-run` skips live Ollama) |

| Model tag | Role (planned) |
|---|---|
| `kimi-k2.7-code:cloud` | Optional artifact / correlation review |
| `minimax-m3:cloud` | Optional artifact / correlation review |

Providers recognized by the scaffold: `codex`, `copilot`, `ollama` (artifact seat).
Env: `OLLAMA_HOST` (default `http://127.0.0.1:11434`), optional
`CAT_OLLAMA_ATTESTATION_KEY` for HMAC attestation.

```powershell
python scripts/cat_review_coverage.py --help
python scripts/cat_review_coverage.py --check-quorum --level R2 --providers codex,ollama
python scripts/cat_ollama_pr_review.py --pr 1 --head-sha abc123 --model kimi-k2.7-code:cloud --dry-run
```

Phase 2 does not change required CI or the Codex → Copilot → human chain.

## Operator Checklist

1. Confirm required checks (`validate`, `cat-ci`) are green.
2. Wait 90–180s after the latest push for Codex / Copilot comments.
3. Triage advisory findings; fix load-bearing issues; ignore flake.
4. Do not treat missing conversation-resolution enforcement as a defect — it is deferred.
5. Merge only with Human Owner (or delegated) approval when mission/BEAD rules require it.

## Related Docs

- `docs/operations/CI_GOVERNANCE.md` — check tiers and cost guard
- `docs/operations/PR_GOVERNANCE.md` — Mission/BEAD PR identity rules
- `docs/operations/REVIEW_INTAKE.md` — mapping review feedback into missions/BEADs
- `docs/github_actions_guardrails.md` — workflow cost/security guardrails

## Appendix: DataAnn audit

**Audited path (newest):**  
`C:\.10_DataAnn\_PerGPT\DataAnn-doctor-post-pr27-wt\tools\`  
(`review_coverage.py` 17001 B, `ollama_pr_review.py` 5500 B; LastWriteTime 2026-08-06).

**Also checked:** `C:\Users\kas41\dataann\tools\` — present but **behind** (no
`review_coverage.py` / `ollama_pr_review.py`). Prefer `_PerGPT` worktrees.

| Topic | Finding |
|---|---|
| Provider allowlist | Exact logins: Codex=`chatgpt-codex-connector`; Copilot=`copilot-pull-request-reviewer`, `github-copilot[bot]`; Bugbot=`cursor[bot]`, `cursor-bugbot`. Humans never count. |
| Quorum model | R0/R1/R2 → **2** LLM seats; R3/R4 → **1** (or REVIEW_GAP with dual hard gates / Sol triple override for R0–R1). |
| Ollama seat | JSON under `artifacts/triage/reviews/pr-{N}-*.json`; must match `pr`, `head_sha`, `provider`∈{ollama,kimi,ollama_kimi}, `model`, plus `findings` or `summary`. |
| HMAC | `DATAANN_OLLAMA_ATTESTATION_KEY` required for trusted seat; attestation version `hmac-sha256-v1` (`payload_sha256` + `signature`). Optional `DATAANN_OLLAMA_ATTESTATION_KEY_ID`. |
| Host env | `OLLAMA_HOST` loopback-only by default; remote needs `DATAANN_OLLAMA_ALLOW_REMOTE=1` + `DATAANN_OLLAMA_ALLOWED_HOSTS`. |
| CLI | `ollama_pr_review.py --help` works (`--pr`, `--head-sha`, `--summary`, `--finding`, `--provider`, `--model`, `--prompt`). `review_coverage.py` is a **library** (no `__main__` / `--help`). |
| Gaps | Main `dataann` clone lacks these tools. No dry-run flag on DataAnn writer (attestation key required or write fails). CAT scaffold uses `evidence/reviews/pr-{N}.json` + `CAT_OLLAMA_ATTESTATION_KEY` and supports `--dry-run`. |

### Next PR checklist

1. `required_conversation_resolution` (branch protection)
2. `codex-review` as required check (after stability window)
3. Ollama seat wired into CI (advisory → optional gate; **not** required in this pass)
4. Dual-LLM quorum enforcement (integrate `cat_review_coverage` into merge/readiness path)
