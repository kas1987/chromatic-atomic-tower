from scripts import cat_self_heal
from scripts.cat_self_heal import FORBIDDEN_MARKERS, apply_plan, build_plan


def test_self_heal_plan_contains_only_safe_actions_when_needed():
    actions = build_plan()
    assert all(action['safe'] for action in actions)
    assert all(not any(marker in action['path'] for marker in FORBIDDEN_MARKERS) for action in actions)


def test_build_plan_proposes_missing_dirs_and_gitkeeps(monkeypatch, tmp_path):
    monkeypatch.setattr(cat_self_heal, 'ROOT', tmp_path)
    actions = build_plan()
    classes = {a['repair_class'] for a in actions}
    assert 'create_missing_required_directory' in classes
    # every required dir should be proposed since tmp_path is empty
    dir_actions = [a for a in actions if a['repair_class'] == 'create_missing_required_directory']
    assert len(dir_actions) == len(cat_self_heal.REQUIRED_DIRS)


def test_apply_plan_creates_directories(monkeypatch, tmp_path):
    monkeypatch.setattr(cat_self_heal, 'ROOT', tmp_path)
    actions = build_plan()
    apply_plan(actions)
    for required in cat_self_heal.REQUIRED_DIRS:
        assert (tmp_path / required).is_dir()


def test_apply_plan_converges_to_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(cat_self_heal, 'ROOT', tmp_path)
    # First pass creates the directories; a second pass then adds the .gitkeep
    # placeholders that only become proposable once the dirs exist. After both,
    # the plan must be empty (the repair loop has converged).
    apply_plan(build_plan())
    apply_plan(build_plan())
    assert build_plan() == []


def test_apply_plan_skips_forbidden_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(cat_self_heal, 'ROOT', tmp_path)
    forbidden = [{
        'repair_class': 'create_missing_required_directory',
        'path': 'secrets/keys', 'safe': True, 'description': 'x',
    }]
    apply_plan(forbidden)
    assert not (tmp_path / 'secrets' / 'keys').exists()


def test_apply_plan_skips_unsafe_actions(monkeypatch, tmp_path):
    monkeypatch.setattr(cat_self_heal, 'ROOT', tmp_path)
    unsafe = [{
        'repair_class': 'create_missing_required_directory',
        'path': 'ci/reports', 'safe': False, 'description': 'x',
    }]
    apply_plan(unsafe)
    assert not (tmp_path / 'ci' / 'reports').exists()
