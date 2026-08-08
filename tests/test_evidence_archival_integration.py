"""Fixture-backed proof for the A015 archive move path."""

import json
import os
import time
from pathlib import Path

import cat_archive_evidence as cae


def test_aged_fixture_moves_and_logs(monkeypatch, tmp_path):
    evidence_root = tmp_path / 'evidence'
    source = evidence_root / 'ci' / 'aged-report.json'
    source.parent.mkdir(parents=True)
    source.write_text('{"fixture": true}\n', encoding='utf-8')
    old_time = time.time() - (120 * 86400)
    os.utime(source, (old_time, old_time))

    monkeypatch.setattr(cae, 'ROOT', tmp_path)
    monkeypatch.setattr(cae, 'EVIDENCE_ROOT', evidence_root)
    monkeypatch.setattr(cae, 'ARCHIVE_ROOT', evidence_root / 'archive')
    monkeypatch.setattr(cae, 'LOGS_DIR', evidence_root / 'logs')

    records = cae.cmd_run(older_than_days=90, batch_id='A015-fixture')

    archived = [record for record in records if record['event'] == 'archived']
    assert len(archived) == 1
    destination = tmp_path / archived[0]['destination_path']
    assert destination.exists()
    assert not source.exists()

    logs = sorted((evidence_root / 'logs').glob('archival_*.jsonl'))
    assert len(logs) == 1
    logged = json.loads(logs[0].read_text(encoding='utf-8').splitlines()[0])
    assert logged['archival_batch_id'] == 'A015-fixture'
    assert logged['destination_path'] == archived[0]['destination_path']
