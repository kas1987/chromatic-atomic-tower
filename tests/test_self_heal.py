from scripts.cat_self_heal import build_plan, FORBIDDEN_MARKERS


def test_self_heal_plan_contains_only_safe_actions_when_needed():
    actions = build_plan()
    assert all(action['safe'] for action in actions)
    assert all(not any(marker in action['path'] for marker in FORBIDDEN_MARKERS) for action in actions)
