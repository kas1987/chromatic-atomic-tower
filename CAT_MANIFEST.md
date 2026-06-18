# CAT Manifest

`CAT_MANIFEST.md` is the canonical repo rulebook for Chromatic Atomic Tower.

If another file conflicts with this manifest, this manifest wins unless a human owner updates the manifest.

## 1. Repository purpose

CAT exists to control mission-based autonomous engineering.

It does not exist to store random notes, broad experiments, or ungoverned prompts.

## 2. Canonical hierarchy

```text
Human Goal
  -> Mission Pack
    -> BEAD
      -> Agent Dispatch
        -> Evidence
          -> Learning
            -> Next BEAD
```

## 3. Required root files

| File | Purpose |
|---|---|
| `README.md` | Human entrypoint |
| `START_HERE.md` | First-run instructions |
| `PDR_CAT_000_ESTABLISH_CORE_REPO.md` | Design record |
| `CAT_MANIFEST.md` | Canonical repo rules |
| `CAT_PRINCIPLES.md` | System principles |
| `CHROMATIC_TREES.md` | Tree governance and worktree map |
| `AGENTS.md` | Agent operating instructions |
| `requirements.txt` | Python script dependencies |
| `Makefile` | Common local commands |

### 3.1 Allowed optional root files

These standard project files may also live at the root. Nothing else may be
created at the root without a manifest update (see §10).

| File | Purpose |
|---|---|
| `CAT_ROADMAP.md` | Sprint roadmap |
| `CHANGELOG.md` | Version history |
| `GOVERNANCE.md` | Governance model |
| `CONTRIBUTING.md` | Contribution rules |
| `SECURITY.md` | Security policy |
| `QUICKSTART.md` | Fast-start guide |
| `VERSION` | Version marker |
| `CHROMATIC_TREES.worktree.json` | Worktree map data (pairs with `CHROMATIC_TREES.md`) |
| `pyproject.toml` | Python project / tooling config |
| `.editorconfig`, `.env.example`, `.gitignore` | Editor/env/VCS dotfiles |

Sprint plans are **not** root files — they live under `docs/operations/`
(e.g. `docs/operations/SPRINT_000_PLAN.md`).

### 3.2 Allowed tooling directories

Beyond the canonical directories in §4, these tooling directories are permitted:

| Directory | Purpose | Tracked? |
|---|---|---|
| `.github/` | CI workflows, issue/PR templates | yes |
| `.vscode/` | VS Code agent surface for the harness (MP-CAT-002) | yes |
| `.agent/` | Multi-model harness home (MP-CAT-002) | yes |
| `tests/` | Python test suite | yes |
| `ci/` | CI helper scripts | yes |
| `.claude/`, `.pytest_cache/`, `.venv/`, `__pycache__/` | Local tooling/cache | no (gitignored) |

### 3.3 Gitignored root entries

These transient/credential entries are expected at the root in local workflows.
They are gitignored, never committed, and never flagged as stray by
`scripts/cat_check_repo.py`. Keep this list in sync with `.gitignore` and the
checker's `IGNORED_ROOT_ENTRIES` / `IGNORED_ROOT_PATTERNS`.

| Entry | Purpose | Tracked? |
|---|---|---|
| `.env`, `.env.*` | Local secrets/config consumed by `scripts/gh_app_token.sh` (`.env.example` is the tracked template) | no (gitignored) |
| `*.pem` | GitHub App private keys | no (gitignored) |
| `.github_app_token_cache` | Cached GitHub App installation token written by `scripts/gh_app_token.sh` | no (gitignored) |


## 4. Canonical directories

| Directory | Owner | Allowed content |
|---|---|---|
| `missions/` | Mission Plane | Mission contracts, templates, registry |
| `beads/` | Execution Plane | Atomic work units |
| `agents/` | Execution Plane | Agent roles and scoring |
| `gates/` | Execution Plane | Confidence, review, human, promotion, tool budget |
| `evidence/` | Evidence Plane | Logs, diffs, reports, screenshots, test results |
| `schemas/` | Contract Plane | JSON schemas |
| `scripts/` | Automation Plane | Validators, resolvers, generators |
| `playbooks/` | Governance Plane | Operating procedures |
| `docs/` | Knowledge Plane | Architecture, operations, migration, reference |
| `state/` | State Plane | Sprint state, tower state, handoff queue, risks |
| `learnings/` | Learning Plane | Decisions, incidents, patterns, echo logs |
| `prompts/` | Agent Plane | Reusable GPT/agent prompts |
| `checklists/` | Review Plane | Human and agent checklists |
| `reference/` | Reference Plane | Source images and supporting artifacts |

## 5. No orphan work rule

No change may be made unless it can identify:

- Mission ID
- BEAD ID
- Agent or human owner
- Allowed path
- Validation method
- Evidence destination

## 6. Mutation rule

Agents may only write files listed in the active BEAD `allowed_paths` field.

Agents must halt if they need to touch a forbidden path or a path not explicitly allowed.

### 6.1 Operator-plane exemption

Human-invoked meta-work that governs the lifecycle itself — sprint closeouts,
retrospectives, sprint kickoffs, and repository hygiene/cleanup — is **operator-plane**
work, not agent execution of a BEAD. It is authorized directly by the Human Owner
(see §10), is recorded in `learnings/DECISION_LOG.md`, and is therefore **exempt from
the `allowed_paths` restriction** in §6. It must still respect `forbidden_paths`
(secrets, credentials, production). It must not be used for feature/mission deliverable
work — if the change implements a mission deliverable, it requires a BEAD.

## 7. Documentation rule

Markdown explains why and how.

YAML/JSON defines what is allowed.

If prose conflicts with YAML/JSON execution contract, the execution contract wins for agent action.

## 8. Validation rule

Before closeout, run:

```bash
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
```

## 9. GO-mode rule

`GO` means:

```text
Resolve the highest-priority approved unblocked BEAD and dispatch only that BEAD.
```

`GO` does not mean:

```text
Search broadly, invent work, change architecture, or continue without evidence.
```

## 10. Change rule

Changes to CAT governance require one of:

- a PDR update
- a mission contract
- a decision log entry
- a human owner approval
