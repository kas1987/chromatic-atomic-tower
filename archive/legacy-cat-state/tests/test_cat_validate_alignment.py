"""tests/test_cat_validate_alignment.py

Unit and integration tests for scripts/cat_validate_harness_alignment.py.

The source module exposes two public helpers (_resolve_mission_path,
_find_bead_files) and two entry points (validate, main).  The spec asks for
coverage of logical groups named check_required_files, check_mission_exists,
check_beads, check_gates, check_mermaid_fenced, and check_complexity_routing;
those behaviours live inside validate() and are exercised here via targeted
tmp_path fixtures.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scripts.cat_validate_harness_alignment import (
    BEAD_SEARCH_DIRS,
    MISSION_CANDIDATES,
    REQUIRED_BEAD_KEYS,
    REQUIRED_BEADS,
    REQUIRED_FILES,
    _find_bead_files,
    _resolve_mission_path,
    main,
    validate,
)
from scripts.common import ROOT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MISSION_ARCHIVED = 'missions/archived/MP-CAT-A006-4C01_HARNESS_ENGINEERING_ALIGNMENT.yaml'


def _minimal_bead_yaml(bead_id: str) -> str:
    """Return a minimal YAML string that satisfies REQUIRED_BEAD_KEYS."""
    return (
        f"mission_id: MP-CAT-A006-4C01\n"
        f"bead_id: {bead_id}\n"
        f"allowed_paths: []\n"
        f"forbidden_paths: []\n"
        f"validation:\n"
        f"  checks: []\n"
        f"required_output: dummy_output.yaml\n"
        f"definition_of_done: done\n"
    )


def _minimal_mission_yaml(bead_ids: list[str]) -> str:
    lines = ["mission_id: MP-CAT-A006-4C01\nbeads:\n"]
    for bid in bead_ids:
        lines.append(f"  - bead_id: {bid}\n")
    return "".join(lines)


def _minimal_gates_yaml(gate_ids: list[str]) -> str:
    lines = ["gates:\n"]
    for gid in gate_ids:
        lines.append(f"  - gate_id: {gid}\n    description: placeholder\n")
    return "".join(lines)


def _minimal_routes_yaml() -> str:
    return (
        "complexity_routing:\n"
        "  default_routes:\n"
        "    - {level: C1, model: haiku}\n"
        "    - {level: C2, model: haiku}\n"
        "    - {level: C3, model: sonnet}\n"
        "    - {level: C4, model: opus}\n"
        "  fallback_rules:\n"
        "    - {condition: overload, action: degrade}\n"
        "  non_negotiables:\n"
        "    - no_pii\n"
    )


FULL_GATE_IDS = [
    'completeness_gate',
    'substantive_validation_gate',
    'control_validation_gate',
    'evidence_sufficiency_gate',
    'promotion_gate',
]


def _build_full_tmp_root(tmp_path: Path) -> Path:
    """Construct a tmp_path that satisfies every check in validate()."""
    # Required files
    for rel in REQUIRED_FILES:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith('.md'):
            p.write_text('# doc\n```mermaid\ngraph TD;\nA-->B;\n```\n', encoding='utf-8')
        elif rel.endswith('.yaml') or rel.endswith('.yml'):
            p.write_text('placeholder: true\n', encoding='utf-8')
        else:
            p.write_text('', encoding='utf-8')

    # Mission (archived candidate)
    mission_path = tmp_path / MISSION_ARCHIVED
    mission_path.parent.mkdir(parents=True, exist_ok=True)
    mission_path.write_text(_minimal_mission_yaml(REQUIRED_BEADS), encoding='utf-8')

    # Bead files (completed dir)
    bead_dir = tmp_path / 'beads' / 'completed'
    bead_dir.mkdir(parents=True, exist_ok=True)
    for bid in REQUIRED_BEADS:
        (bead_dir / f'{bid}.yaml').write_text(_minimal_bead_yaml(bid), encoding='utf-8')

    # Gates
    gates_path = tmp_path / 'gates' / 'assertion_gates.yaml'
    gates_path.parent.mkdir(parents=True, exist_ok=True)
    gates_path.write_text(_minimal_gates_yaml(FULL_GATE_IDS), encoding='utf-8')

    # Model routes
    routes_path = tmp_path / 'agents' / 'model_routes.yaml'
    routes_path.parent.mkdir(parents=True, exist_ok=True)
    routes_path.write_text(_minimal_routes_yaml(), encoding='utf-8')

    # Mermaid docs
    for rel in [
        'docs/architecture/HARNESS_ENGINEERING_AUDIT_ALIGNMENT.md',
        'docs/architecture/CAT_MISSION_PIPELINE_MERMAID.md',
    ]:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('# diagram\n```mermaid\ngraph TD;\nA-->B;\n```\n', encoding='utf-8')

    return tmp_path


# ===========================================================================
# _resolve_mission_path
# ===========================================================================

class TestResolveMissionPath:
    def test_real_root_returns_string(self):
        """Integration: real repo has the mission in missions/archived."""
        result = _resolve_mission_path(ROOT)
        assert result is not None
        assert isinstance(result, str)
        assert 'MP-CAT-A006-4C01' in result

    def test_empty_tmp_path_returns_none(self, tmp_path):
        result = _resolve_mission_path(tmp_path)
        assert result is None

    def test_active_candidate_is_preferred(self, tmp_path):
        active_rel = MISSION_CANDIDATES[0]
        active_path = tmp_path / active_rel
        active_path.parent.mkdir(parents=True, exist_ok=True)
        active_path.write_text('mission_id: test\n', encoding='utf-8')
        result = _resolve_mission_path(tmp_path)
        assert result == active_rel

    def test_archived_candidate_found_when_active_absent(self, tmp_path):
        archived_rel = MISSION_CANDIDATES[1]
        archived_path = tmp_path / archived_rel
        archived_path.parent.mkdir(parents=True, exist_ok=True)
        archived_path.write_text('mission_id: test\n', encoding='utf-8')
        result = _resolve_mission_path(tmp_path)
        assert result == archived_rel


# ===========================================================================
# _find_bead_files
# ===========================================================================

class TestFindBeadFiles:
    def test_real_root_finds_all_beads(self):
        """Integration: all 8 beads must be locatable in the real repo."""
        for bid in REQUIRED_BEADS:
            matches = _find_bead_files(ROOT, bid)
            assert matches, f"Expected bead file(s) for {bid}, found none"

    def test_empty_tmp_path_returns_empty_list(self, tmp_path):
        matches = _find_bead_files(tmp_path, 'BEAD-CAT-A006-4C01-01')
        assert matches == []

    def test_finds_bead_in_completed_dir(self, tmp_path):
        bead_id = 'BEAD-CAT-A006-4C01-01'
        bead_dir = tmp_path / 'beads' / 'completed'
        bead_dir.mkdir(parents=True, exist_ok=True)
        bead_file = bead_dir / f'{bead_id}.yaml'
        bead_file.write_text(_minimal_bead_yaml(bead_id), encoding='utf-8')
        matches = _find_bead_files(tmp_path, bead_id)
        assert any(p.name == f'{bead_id}.yaml' for p in matches)

    def test_finds_bead_in_active_dir(self, tmp_path):
        bead_id = 'BEAD-CAT-A006-4C01-02'
        bead_dir = tmp_path / 'beads' / 'active'
        bead_dir.mkdir(parents=True, exist_ok=True)
        bead_file = bead_dir / f'{bead_id}_draft.yaml'
        bead_file.write_text(_minimal_bead_yaml(bead_id), encoding='utf-8')
        matches = _find_bead_files(tmp_path, bead_id)
        assert any('active' in str(p) for p in matches)

    def test_no_duplicates_returned(self, tmp_path):
        bead_id = 'BEAD-CAT-A006-4C01-03'
        for sub in BEAD_SEARCH_DIRS:
            d = tmp_path / sub
            d.mkdir(parents=True, exist_ok=True)
            (d / f'{bead_id}.yaml').write_text(_minimal_bead_yaml(bead_id), encoding='utf-8')
        matches = _find_bead_files(tmp_path, bead_id)
        paths = [str(p) for p in matches]
        assert len(paths) == len(set(paths))


# ===========================================================================
# check_required_files  (exercised via validate())
# ===========================================================================

class TestCheckRequiredFiles:
    def test_real_root_passes(self):
        """Integration: all required files exist in the real repo."""
        code, errors = validate(ROOT)
        missing_required = [e for e in errors if e.startswith('missing required file:')]
        assert missing_required == [], f"Missing required files: {missing_required}"

    def test_empty_tmp_path_fails(self, tmp_path):
        code, errors = validate(tmp_path)
        assert code == 1
        assert any('missing required file:' in e for e in errors)

    def test_each_required_file_absence_detected(self, tmp_path):
        """Remove one required file at a time; each removal must produce an error."""
        root = _build_full_tmp_root(tmp_path)
        for rel in REQUIRED_FILES:
            target = root / rel
            if not target.exists():
                continue
            content = target.read_bytes()
            target.unlink()
            _, errors = validate(root)
            assert any(rel in e for e in errors), (
                f"Removing {rel} did not produce an error"
            )
            target.write_bytes(content)  # restore


# ===========================================================================
# check_mission_exists  (exercised via validate())
# ===========================================================================

class TestCheckMissionExists:
    def test_real_root_mission_found(self):
        """Integration: mission is present and parse-able."""
        code, errors = validate(ROOT)
        mission_errors = [e for e in errors if 'missing mission contract' in e]
        assert mission_errors == []

    def test_no_candidates_fails(self, tmp_path):
        code, errors = validate(tmp_path)
        assert any('missing mission contract' in e for e in errors)

    def test_mission_with_all_beads_passes(self, tmp_path):
        root = _build_full_tmp_root(tmp_path)
        code, errors = validate(root)
        bead_ref_errors = [e for e in errors if 'mission missing BEAD references' in e]
        assert bead_ref_errors == []

    def test_mission_missing_bead_reference_fails(self, tmp_path):
        root = _build_full_tmp_root(tmp_path)
        # Overwrite mission without all beads
        mission_path = root / MISSION_ARCHIVED
        mission_path.write_text(_minimal_mission_yaml(['BEAD-CAT-A006-4C01-01']), encoding='utf-8')
        _, errors = validate(root)
        assert any('mission missing BEAD references' in e for e in errors)


# ===========================================================================
# check_beads  (exercised via validate())
# ===========================================================================

class TestCheckBeads:
    def test_real_root_beads_pass(self):
        """Integration: all 8 required beads exist with required keys."""
        code, errors = validate(ROOT)
        bead_errors = [e for e in errors if 'missing BEAD file' in e or 'missing key:' in e]
        assert bead_errors == [], f"Bead errors on real root: {bead_errors}"

    def test_no_beads_fails(self, tmp_path):
        code, errors = validate(tmp_path)
        assert any('missing BEAD file' in e for e in errors)

    def test_bead_missing_required_key_fails(self, tmp_path):
        root = _build_full_tmp_root(tmp_path)
        # Overwrite one bead without a required key
        bead_path = root / 'beads' / 'completed' / 'BEAD-CAT-A006-4C01-01.yaml'
        bead_path.write_text(
            'mission_id: MP-CAT-A006-4C01\nbead_id: BEAD-CAT-A006-4C01-01\n',
            encoding='utf-8',
        )
        _, errors = validate(root)
        assert any('missing key:' in e for e in errors)

    def test_full_bead_set_no_missing_key_errors(self, tmp_path):
        root = _build_full_tmp_root(tmp_path)
        _, errors = validate(root)
        key_errors = [e for e in errors if 'missing key:' in e]
        assert key_errors == []


# ===========================================================================
# check_gates  (exercised via validate())
# ===========================================================================

class TestCheckGates:
    def test_real_root_gates_pass(self):
        """Integration: assertion_gates.yaml defines all required gates."""
        code, errors = validate(ROOT)
        gate_errors = [e for e in errors if 'assertion_gates.yaml missing gates' in e]
        assert gate_errors == []

    def test_no_gates_file_missing_required_file_error(self, tmp_path):
        code, errors = validate(tmp_path)
        assert any('gates/assertion_gates.yaml' in e for e in errors)

    def test_gates_file_missing_gate_id_fails(self, tmp_path):
        root = _build_full_tmp_root(tmp_path)
        gates_path = root / 'gates' / 'assertion_gates.yaml'
        # Only provide 2 of the 5 required gates
        gates_path.write_text(_minimal_gates_yaml(['completeness_gate', 'promotion_gate']), encoding='utf-8')
        _, errors = validate(root)
        assert any('assertion_gates.yaml missing gates' in e for e in errors)

    def test_all_required_gates_present_passes(self, tmp_path):
        root = _build_full_tmp_root(tmp_path)
        _, errors = validate(root)
        gate_errors = [e for e in errors if 'assertion_gates.yaml missing gates' in e]
        assert gate_errors == []


# ===========================================================================
# check_mermaid_fenced  (exercised via validate())
# ===========================================================================

class TestCheckMermaidFenced:
    def test_real_root_mermaid_docs_pass(self):
        """Integration: both architecture docs have mermaid fences."""
        code, errors = validate(ROOT)
        mermaid_errors = [e for e in errors if 'no Mermaid diagram' in e]
        assert mermaid_errors == []

    def test_doc_without_mermaid_fence_fails(self, tmp_path):
        root = _build_full_tmp_root(tmp_path)
        # Overwrite one doc without a mermaid fence
        doc = root / 'docs' / 'architecture' / 'CAT_MISSION_PIPELINE_MERMAID.md'
        doc.write_text('# No diagrams here\nJust text.\n', encoding='utf-8')
        _, errors = validate(root)
        assert any('no Mermaid diagram' in e for e in errors)

    def test_doc_with_mermaid_fence_passes(self, tmp_path):
        root = _build_full_tmp_root(tmp_path)
        _, errors = validate(root)
        mermaid_errors = [e for e in errors if 'no Mermaid diagram' in e]
        assert mermaid_errors == []


# ===========================================================================
# check_complexity_routing  (exercised via validate())
# ===========================================================================

class TestCheckComplexityRouting:
    def test_real_root_routing_passes(self):
        """Integration: model_routes.yaml has a valid complexity_routing block."""
        code, errors = validate(ROOT)
        routing_errors = [e for e in errors if 'complexity_routing' in e]
        assert routing_errors == []

    def test_no_routes_file_missing_required_file_error(self, tmp_path):
        code, errors = validate(tmp_path)
        assert any('agents/model_routes.yaml' in e for e in errors)

    def test_missing_complexity_routing_block_fails(self, tmp_path):
        root = _build_full_tmp_root(tmp_path)
        routes_path = root / 'agents' / 'model_routes.yaml'
        routes_path.write_text('other_key: value\n', encoding='utf-8')
        _, errors = validate(root)
        assert any('missing complexity_routing block' in e for e in errors)

    def test_fewer_than_four_routes_fails(self, tmp_path):
        root = _build_full_tmp_root(tmp_path)
        routes_path = root / 'agents' / 'model_routes.yaml'
        routes_path.write_text(
            'complexity_routing:\n'
            '  default_routes:\n'
            '    - {level: C1, model: haiku}\n'
            '    - {level: C2, model: haiku}\n'
            '  fallback_rules:\n'
            '    - {condition: overload, action: degrade}\n'
            '  non_negotiables: [no_pii]\n',
            encoding='utf-8',
        )
        _, errors = validate(root)
        assert any('at least four default routes' in e for e in errors)

    def test_missing_fallback_rules_fails(self, tmp_path):
        root = _build_full_tmp_root(tmp_path)
        routes_path = root / 'agents' / 'model_routes.yaml'
        routes_path.write_text(
            'complexity_routing:\n'
            '  default_routes:\n'
            '    - {level: C1, model: haiku}\n'
            '    - {level: C2, model: haiku}\n'
            '    - {level: C3, model: sonnet}\n'
            '    - {level: C4, model: opus}\n'
            '  non_negotiables: [no_pii]\n',
            encoding='utf-8',
        )
        _, errors = validate(root)
        assert any('missing fallback rules' in e for e in errors)

    def test_valid_routing_block_passes(self, tmp_path):
        root = _build_full_tmp_root(tmp_path)
        _, errors = validate(root)
        routing_errors = [e for e in errors if 'complexity_routing' in e]
        assert routing_errors == []


# ===========================================================================
# main()
# ===========================================================================

class TestMain:
    def test_main_real_root_exits_zero(self, monkeypatch):
        """Integration: main() returns 0 on the real, passing repository."""
        monkeypatch.setattr(
            sys, 'argv', ['cat_validate_harness_alignment.py', '--root', str(ROOT)]
        )
        result = main()
        assert result == 0

    def test_main_empty_dir_exits_one(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            sys, 'argv', ['cat_validate_harness_alignment.py', '--root', str(tmp_path)]
        )
        result = main()
        assert result == 1
