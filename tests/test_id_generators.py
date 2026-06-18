"""Coverage for the ID parsing/derivation helpers and regexes in
scripts/cat_new_mission.py and scripts/cat_new_bead.py.

These modules are otherwise CLI-only (argparse + filesystem writes); the pure
helpers and the public ID-format regexes are unit-tested here.
"""
from __future__ import annotations

import pytest

from scripts import cat_new_bead as nb
from scripts import cat_new_mission as nm


# ---------------------------------------------------------------------------
# _legacy_mission_number (identical in both modules)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("module", [nm, nb])
def test_legacy_mission_number_parses(module):
    assert module._legacy_mission_number("MP-CAT-003") == 3
    assert module._legacy_mission_number("MP-CAT-A006-4C01") is None
    assert module._legacy_mission_number("nonsense") is None


# ---------------------------------------------------------------------------
# new/legacy mission id regexes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mission_id,ok", [
    ("MP-CAT-A006-4C01", True),
    ("MP-CAT-S001-1C99", True),
    ("MP-CAT-Z001-4C01", False),   # tier must be S/A/B/C
    ("MP-CAT-A006-5C01", False),   # digit 1-4 only
    ("MP-CAT-006", False),         # legacy form, not new
])
def test_new_mission_id_regex(mission_id, ok):
    assert bool(nm.NEW_MISSION_ID_RE.match(mission_id)) is ok


def test_example_mission_id_regex():
    assert nm.EXAMPLE_MISSION_ID_RE.match("MP-CAT-EXAMPLE-FOO-1")
    assert not nm.EXAMPLE_MISSION_ID_RE.match("MP-CAT-A006-4C01")


# ---------------------------------------------------------------------------
# bead id regexes + derivation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bead_id,ok", [
    ("BEAD-CAT-S001-4C01-01", True),
    ("BEAD-CAT-A006-1C99-12", True),
    ("BEAD-CAT-Z001-4C01-01", False),
    ("BEAD-CAT-001-002", False),   # legacy form, not new
])
def test_new_bead_id_regex(bead_id, ok):
    assert bool(nb.NEW_BEAD_ID_RE.match(bead_id)) is ok


def test_legacy_bead_id_regex():
    assert nb.LEGACY_BEAD_ID_RE.match("BEAD-CAT-001-002")
    assert not nb.LEGACY_BEAD_ID_RE.match("BEAD-CAT-S001-4C01-01")


def test_derive_bead_id_from_mission():
    assert (
        nb._derive_bead_id_from_mission("MP-CAT-S001-4C01", "02")
        == "BEAD-CAT-S001-4C01-02"
    )


def test_derived_bead_id_is_valid_new_format():
    derived = nb._derive_bead_id_from_mission("MP-CAT-A006-4C01", "07")
    assert nb.NEW_BEAD_ID_RE.match(derived)
