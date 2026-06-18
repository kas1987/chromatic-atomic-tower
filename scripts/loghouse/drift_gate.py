"""
LOGHOUSE Drift Gate.

CI enforcement: fails with exit code 1 when any architecture-rule violation at
severity P0 or P1 (or whatever --fail-on specifies) is present in the observed
dependency edges.

Usage:
    python scripts/loghouse/drift_gate.py \\
        --rules reference/loghouse/architecture_rules.yaml \\
        --edges tests/fixtures/loghouse/dependency_edges.json \\
        --fail-on p0,p1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure repo root is importable when invoked directly (not via -m)
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.common import load_yaml, validate_with_schema, ROOT

ARCH_RULE_SCHEMA = ROOT / "schemas" / "architecture_rule.schema.json"


def load_rules(rules_path: Path) -> list[dict]:
    data = load_yaml(rules_path)
    return data.get("rules", [])


def load_edges(edges_path: Path) -> list[dict]:
    return json.loads(edges_path.read_text(encoding="utf-8"))


def _rule_for_edge(edge: dict, rules: list[dict]) -> dict | None:
    """Return the first matching rule for an edge, or None."""
    for rule in rules:
        source_match = edge.get("source") == rule.get("source") or rule.get("source") == "*"
        target_match = edge.get("target") == rule.get("target") or rule.get("target") == "*"
        type_match = rule.get("edge_type") in (edge.get("edge_type"), "any")
        if source_match and target_match and type_match:
            return rule
    return None


def run_gate(
    rules_path: Path,
    edges_path: Path,
    fail_on_severities: set[str],
) -> int:
    """
    Check each dependency edge against the architecture rules.

    Returns 0 if no forbidden edge at the specified severity levels is found,
    1 otherwise.
    """
    rules = load_rules(rules_path)
    edges = load_edges(edges_path)

    violations: list[dict] = []

    for edge in edges:
        rule = _rule_for_edge(edge, rules)
        if rule is None:
            continue  # no rule — not a gated violation

        if rule.get("decision") == "forbidden":
            sev = rule.get("severity", "p3")
            if sev in fail_on_severities:
                violations.append(
                    {
                        "edge_id": edge.get("edge_id"),
                        "source": edge.get("source"),
                        "target": edge.get("target"),
                        "edge_type": edge.get("edge_type"),
                        "rule_id": rule.get("rule_id"),
                        "severity": sev,
                        "rationale": rule.get("rationale", ""),
                    }
                )

    if violations:
        print(
            f"[drift-gate] FAIL — {len(violations)} "
            f"forbidden edge(s) at severity {sorted(fail_on_severities)} detected:"
        )
        for v in violations:
            print(
                f"  BLOCKED [{v['severity']}] {v['source']} → {v['target']} "
                f"({v['edge_type']}) rule={v['rule_id']}"
            )
        print("[drift-gate] Build failed: critical architecture rule violation(s) present.")
        return 1

    print(
        f"[drift-gate] PASS — no forbidden edge at severity "
        f"{sorted(fail_on_severities)} found in {edges_path.name}"
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="LOGHOUSE Drift Gate CI enforcer")
    parser.add_argument(
        "--rules",
        type=Path,
        default=ROOT / "reference" / "loghouse" / "architecture_rules.yaml",
        help="Path to architecture_rules.yaml",
    )
    parser.add_argument(
        "--edges",
        type=Path,
        required=True,
        help="Path to dependency_edges.json fixture",
    )
    parser.add_argument(
        "--fail-on",
        dest="fail_on",
        default="p0,p1",
        help="Comma-separated severity levels that trigger a build failure (default: p0,p1)",
    )
    args = parser.parse_args()

    fail_severities = {s.strip().lower() for s in args.fail_on.split(",")}
    exit_code = run_gate(args.rules, args.edges, fail_severities)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
