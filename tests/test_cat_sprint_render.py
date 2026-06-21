"""tests/test_cat_sprint_render.py

Comprehensive tests for:
  - scripts/cat_render_sprint_state.py  (render_sprint_state, render_handoff_queue, write_sprint_state)
  - scripts/cat_status.py               (main)

Strategy:
  - Write minimal YAML fixture files into tmp_path and pass tmp_path as `root`
    so every test is isolated from the live repo state.
  - Mock `beads_for_mission` via monkeypatch for the handoff-queue tests that
    would otherwise require real BEAD files on disk.
  - Mock `cat_status.ROOT` to point at tmp_path for cat_status.main() tests.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Modules under test (pythonpath = [".", "scripts"] handles the import path)
# ---------------------------------------------------------------------------
import cat_render_sprint_state as crs
import cat_status


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False), encoding="utf-8")


@pytest.fixture()
def minimal_root(tmp_path: Path) -> Path:
    """A tmp_path with minimal TOWER_STATE.yaml + MISSION_REGISTRY.yaml."""
    _write_yaml(
        tmp_path / "state" / "TOWER_STATE.yaml",
        {
            "active_sprint": "sprint-001",
            "status": "active",
            "active_mission_id": "MP-CAT-001",
            "active_bead_id": "BEAD-001",
            "go_mode": "auto",
            "sprint_goal": "Ship the harness",
            "next_command": None,
        },
    )
    _write_yaml(
        tmp_path / "missions" / "registry" / "MISSION_REGISTRY.yaml",
        {
            "active_mission_id": "MP-CAT-001",
            "missions": [
                {
                    "mission_id": "MP-CAT-001",
                    "title": "Test mission",
                    "status": "in_progress",
                }
            ],
        },
    )
    return tmp_path


@pytest.fixture()
def idle_root(tmp_path: Path) -> Path:
    """A tmp_path where no active mission is set anywhere."""
    _write_yaml(
        tmp_path / "state" / "TOWER_STATE.yaml",
        {
            "active_sprint": "",
            "status": "post_sprint_idle",
            "active_mission_id": None,
            "active_bead_id": None,
            "go_mode": "manual",
            "sprint_goal": "",
            "next_command": None,
        },
    )
    _write_yaml(
        tmp_path / "missions" / "registry" / "MISSION_REGISTRY.yaml",
        {
            "active_mission_id": None,
            "missions": [],
        },
    )
    return tmp_path


# ===========================================================================
# render_sprint_state
# ===========================================================================

class TestRenderSprintState:
    def test_banner_present(self, minimal_root: Path) -> None:
        out = crs.render_sprint_state(minimal_root)
        assert crs.BANNER in out

    def test_heading_present(self, minimal_root: Path) -> None:
        out = crs.render_sprint_state(minimal_root)
        assert "# CAT Sprint State" in out

    def test_active_sprint_in_table(self, minimal_root: Path) -> None:
        out = crs.render_sprint_state(minimal_root)
        assert "sprint-001" in out

    def test_active_mission_in_table(self, minimal_root: Path) -> None:
        out = crs.render_sprint_state(minimal_root)
        assert "MP-CAT-001" in out

    def test_active_bead_in_table(self, minimal_root: Path) -> None:
        out = crs.render_sprint_state(minimal_root)
        assert "BEAD-001" in out

    def test_mission_status_shown(self, minimal_root: Path) -> None:
        out = crs.render_sprint_state(minimal_root)
        assert "in_progress" in out

    def test_go_mode_shown(self, minimal_root: Path) -> None:
        out = crs.render_sprint_state(minimal_root)
        assert "auto" in out

    def test_no_active_mission_shows_dash(self, idle_root: Path) -> None:
        out = crs.render_sprint_state(idle_root)
        # When there is no active mission id the field should show em-dash
        assert "| Active Mission | — |" in out

    def test_canonical_sources_section_present(self, minimal_root: Path) -> None:
        out = crs.render_sprint_state(minimal_root)
        assert "## Canonical Sources" in out

    def test_returns_string(self, minimal_root: Path) -> None:
        out = crs.render_sprint_state(minimal_root)
        assert isinstance(out, str)

    def test_mission_id_from_registry_fallback(self, tmp_path: Path) -> None:
        """If tower has no active_mission_id, registry.active_mission_id is used."""
        _write_yaml(
            tmp_path / "state" / "TOWER_STATE.yaml",
            {"active_sprint": "sprint-002", "status": "active"},
        )
        _write_yaml(
            tmp_path / "missions" / "registry" / "MISSION_REGISTRY.yaml",
            {
                "active_mission_id": "MP-CAT-002",
                "missions": [{"mission_id": "MP-CAT-002", "title": "Fallback", "status": "approved"}],
            },
        )
        out = crs.render_sprint_state(tmp_path)
        assert "MP-CAT-002" in out


# ===========================================================================
# render_handoff_queue
# ===========================================================================

class TestRenderHandoffQueue:
    def test_no_active_mission_shows_idle_message(self, idle_root: Path) -> None:
        out = crs.render_handoff_queue(idle_root)
        assert "No active mission" in out

    def test_banner_in_handoff(self, idle_root: Path) -> None:
        out = crs.render_handoff_queue(idle_root)
        assert crs.BANNER in out

    def test_heading_in_handoff(self, idle_root: Path) -> None:
        out = crs.render_handoff_queue(idle_root)
        assert "# Agent Handoff Queue" in out

    def test_mission_no_beads_shows_empty_message(
        self, minimal_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mission active but no queued/active BEADs → empty-mission message."""
        monkeypatch.setattr(crs, "_queued_beads", lambda mission_id, root: [])
        out = crs.render_handoff_queue(minimal_root)
        assert "has no queued or active BEADs" in out

    def test_active_bead_appears_in_active_section(
        self, minimal_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_beads = [
            {"bead_id": "BEAD-001", "status": "active", "title": "Do the thing", "agent_role": "engineer"},
        ]
        monkeypatch.setattr(crs, "_queued_beads", lambda mission_id, root: fake_beads)
        out = crs.render_handoff_queue(minimal_root)
        assert "## Active" in out
        assert "BEAD-001" in out
        assert "Do the thing" in out
        assert "engineer" in out

    def test_queued_bead_appears_in_next_section(
        self, minimal_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_beads = [
            {"bead_id": "BEAD-002", "status": "queued", "title": "Next task", "agent_role": "reviewer"},
        ]
        monkeypatch.setattr(crs, "_queued_beads", lambda mission_id, root: fake_beads)
        out = crs.render_handoff_queue(minimal_root)
        assert "## Next" in out
        assert "BEAD-002" in out
        assert "Status: queued" in out

    def test_mixed_active_and_queued_beads(
        self, minimal_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_beads = [
            {"bead_id": "BEAD-001", "status": "active", "title": "Active task", "agent_role": "eng"},
            {"bead_id": "BEAD-002", "status": "queued", "title": "Queued task", "agent_role": "qa"},
        ]
        monkeypatch.setattr(crs, "_queued_beads", lambda mission_id, root: fake_beads)
        out = crs.render_handoff_queue(minimal_root)
        assert "## Active" in out
        assert "## Next" in out
        assert "BEAD-001" in out
        assert "BEAD-002" in out


# ===========================================================================
# write_sprint_state
# ===========================================================================

class TestWriteSprintState:
    def test_creates_sprint_state_md(
        self, minimal_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(crs, "_queued_beads", lambda mission_id, root: [])
        crs.write_sprint_state(minimal_root)
        sprint_path = minimal_root / "state" / "SPRINT_STATE.md"
        assert sprint_path.exists(), "SPRINT_STATE.md was not created"

    def test_creates_agent_handoff_queue_md(
        self, minimal_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(crs, "_queued_beads", lambda mission_id, root: [])
        crs.write_sprint_state(minimal_root)
        handoff_path = minimal_root / "state" / "AGENT_HANDOFF_QUEUE.md"
        assert handoff_path.exists(), "AGENT_HANDOFF_QUEUE.md was not created"

    def test_sprint_state_contains_banner(
        self, minimal_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(crs, "_queued_beads", lambda mission_id, root: [])
        crs.write_sprint_state(minimal_root)
        content = (minimal_root / "state" / "SPRINT_STATE.md").read_text(encoding="utf-8")
        assert crs.BANNER in content

    def test_handoff_contains_banner(
        self, minimal_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(crs, "_queued_beads", lambda mission_id, root: [])
        crs.write_sprint_state(minimal_root)
        content = (minimal_root / "state" / "AGENT_HANDOFF_QUEUE.md").read_text(encoding="utf-8")
        assert crs.BANNER in content

    def test_print_output_mentions_files(
        self, minimal_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(crs, "_queued_beads", lambda mission_id, root: [])
        crs.write_sprint_state(minimal_root)
        captured = capsys.readouterr()
        assert "SPRINT_STATE" in captured.out
        assert "AGENT_HANDOFF_QUEUE" in captured.out

    def test_files_end_with_newline(
        self, minimal_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(crs, "_queued_beads", lambda mission_id, root: [])
        crs.write_sprint_state(minimal_root)
        for filename in ("SPRINT_STATE.md", "AGENT_HANDOFF_QUEUE.md"):
            content = (minimal_root / "state" / filename).read_text(encoding="utf-8")
            assert content.endswith("\n"), f"{filename} does not end with newline"


# ===========================================================================
# cat_status.main
# ===========================================================================

class TestCatStatusMain:
    def _setup_root(self, root: Path, mission_id: str | None = "MP-CAT-001") -> None:
        _write_yaml(
            root / "state" / "TOWER_STATE.yaml",
            {
                "status": "active",
                "active_sprint": "sprint-001",
                "active_bead_id": "BEAD-001",
                "next_command": "run_tests",
            },
        )
        missions = []
        if mission_id:
            missions.append({"mission_id": mission_id, "title": "Test", "status": "in_progress"})
        _write_yaml(
            root / "missions" / "registry" / "MISSION_REGISTRY.yaml",
            {
                "active_mission_id": mission_id,
                "missions": missions,
            },
        )

    def test_main_returns_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        self._setup_root(tmp_path)
        monkeypatch.setattr(cat_status, "ROOT", tmp_path)
        rc = cat_status.main()
        assert rc == 0

    def test_main_outputs_valid_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        self._setup_root(tmp_path)
        monkeypatch.setattr(cat_status, "ROOT", tmp_path)
        cat_status.main()
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert isinstance(payload, dict)

    def test_main_required_keys_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        self._setup_root(tmp_path)
        monkeypatch.setattr(cat_status, "ROOT", tmp_path)
        cat_status.main()
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        required = {
            "tower_status",
            "active_sprint",
            "active_mission_id",
            "active_bead_id",
            "mission",
            "next_command",
        }
        assert required <= payload.keys()

    def test_main_active_mission_id_matches(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        self._setup_root(tmp_path, mission_id="MP-CAT-001")
        monkeypatch.setattr(cat_status, "ROOT", tmp_path)
        cat_status.main()
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["active_mission_id"] == "MP-CAT-001"

    def test_main_mission_dict_present_when_active(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        self._setup_root(tmp_path, mission_id="MP-CAT-001")
        monkeypatch.setattr(cat_status, "ROOT", tmp_path)
        cat_status.main()
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["mission"] is not None
        assert payload["mission"]["mission_id"] == "MP-CAT-001"

    def test_main_mission_none_when_no_active(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        self._setup_root(tmp_path, mission_id=None)
        monkeypatch.setattr(cat_status, "ROOT", tmp_path)
        cat_status.main()
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["mission"] is None
        assert payload["active_mission_id"] is None

    def test_main_tower_fields_correct(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        self._setup_root(tmp_path)
        monkeypatch.setattr(cat_status, "ROOT", tmp_path)
        cat_status.main()
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["tower_status"] == "active"
        assert payload["active_sprint"] == "sprint-001"
        assert payload["active_bead_id"] == "BEAD-001"
        assert payload["next_command"] == "run_tests"

    def test_main_output_is_sorted_keys(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        """json.dumps(sort_keys=True) means keys appear alphabetically in output."""
        self._setup_root(tmp_path)
        monkeypatch.setattr(cat_status, "ROOT", tmp_path)
        cat_status.main()
        captured = capsys.readouterr()
        lines = captured.out.strip().splitlines()
        # Find only top-level keys (lines that start with two-space indent + quoted key)
        key_lines = [l.strip().split(":")[0].strip('"') for l in lines if l.startswith('  "')]
        top_level_keys = [k for k in key_lines if k]
        assert top_level_keys == sorted(top_level_keys), "Output keys are not sorted"
