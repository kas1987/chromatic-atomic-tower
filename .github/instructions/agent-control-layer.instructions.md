---
applyTo: ".agent/**"
description: 'Rules for editing the harness control layer.'
---
# Editing the `.agent/` control layer

This directory is the harness control plane. Treat it as governed state, not scratch space.

- **`queue.json`** must remain valid JSON. Every item carries an `id`, `status`, and `bead_id`
  linking it to a CAT BEAD. Do not invent statuses outside:
  `pending | in-progress | review | validating | blocked | done`. Only a human marks `done`.
- **`runs/`** is generated output. Do not hand-edit `review_packet.md`, `test_output.txt`, or
  `git_diff_*` — regenerate them via `scripts/harness_run.py` / the VS Code tasks.
- **`model_routes.yaml` / `harness_settings.yaml`** define routing and budget guardrails. Keep
  them valid YAML; changing a model tag must match an installed Ollama model.
- **`tickets/`** are authored from `.agent/templates/ticket_template.md`. A ticket must declare
  Allowed Files, Forbidden Files/Actions, Acceptance Criteria, Test Commands, and Stop Conditions.
- **`governance/`** is read-mostly policy. Changing a guardrail or escalation rule is itself an
  escalation-worthy change — flag it for human review.

When code reads these files, wrap every `json.loads()` / `yaml.safe_load()` in try/except — files
may be observed mid-write.
