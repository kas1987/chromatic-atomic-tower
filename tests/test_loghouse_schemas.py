from scripts.common import ROOT, validate_with_schema


# ── telemetry_envelope ───────────────────────────────────────────────────────


def test_telemetry_envelope_schema_invalid_missing_required():
    """A telemetry envelope missing required fields must fail."""
    sample = {
        "event_id": "6d6942e2-36db-4ce7-84d8-b75a4ef3ce53",
        "ts": "2026-06-17T12:00:00Z",
        "signal_type": "log",
        # missing: service, env, severity, commit_sha, deploy_id, attrs
    }
    errors = validate_with_schema(sample, ROOT / "schemas/telemetry_envelope.schema.json")
    assert len(errors) > 0


def test_telemetry_envelope_schema_invalid_bad_signal_type():
    """A telemetry envelope with an invalid signal_type must fail."""
    sample = {
        "event_id": "6d6942e2-36db-4ce7-84d8-b75a4ef3ce53",
        "ts": "2026-06-17T12:00:00Z",
        "signal_type": "telemetry",  # invalid enum
        "service": "payments-api",
        "env": "prod",
        "severity": "info",
        "message": "ok",
        "commit_sha": "abc1234",
        "deploy_id": "deploy-20260617-1200",
        "attrs": {},
    }
    errors = validate_with_schema(sample, ROOT / "schemas/telemetry_envelope.schema.json")
    assert len(errors) > 0


def test_telemetry_envelope_schema_valid_sample():
    sample = {
        'event_id': '6d6942e2-36db-4ce7-84d8-b75a4ef3ce53',
        'ts': '2026-06-17T12:00:00Z',
        'signal_type': 'log',
        'service': 'payments-api',
        'env': 'prod',
        'severity': 'error',
        'message': 'timeout from upstream',
        'trace_id': 'abc123',
        'span_id': 'def456',
        'commit_sha': 'abc1234',
        'deploy_id': 'deploy-20260617-1200',
        'attrs': {'http.status_code': 504},
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/telemetry_envelope.schema.json')
    assert errors == []


def test_finding_schema_valid_sample():
    sample = {
        'finding_id': '44baafbf-fd7f-4f2d-9fc3-518e536d9281',
        'title': 'Error spike after deploy',
        'category': 'reliability',
        'severity': 'p1',
        'confidence': 0.82,
        'status': 'open',
        'services': ['payments-api'],
        'first_seen': '2026-06-17T12:05:00Z',
        'last_seen': '2026-06-17T12:10:00Z',
        'owner': 'team-payments',
        'hypothesis': 'Deploy introduced retry bug.',
        'suggested_fix': 'Rollback deployment and inspect retry middleware change.',
        'blast_radius': 'service',
        'sla_impact': True,
        'evidence': [
            {
                'source_type': 'deploy',
                'source_ref': 'deploy-20260617-1200',
                'observed_at': '2026-06-17T12:06:00Z',
                'summary': 'Error rate increased 3x within 10 minutes of deploy.',
            }
        ],
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/finding.schema.json')
    assert errors == []


def test_finding_schema_invalid_bad_category():
    """A finding with an invalid category enum must fail."""
    sample = {
        'finding_id': '44baafbf-fd7f-4f2d-9fc3-518e536d9281',
        'title': 'Bad finding',
        'category': 'mystery',  # invalid enum
        'severity': 'p1',
        'confidence': 0.82,
        'status': 'open',
        'services': ['payments-api'],
        'first_seen': '2026-06-17T12:05:00Z',
        'last_seen': '2026-06-17T12:10:00Z',
        'owner': 'team-payments',
        'hypothesis': 'Something happened.',
        'suggested_fix': 'Fix it.',
        'blast_radius': 'service',
        'sla_impact': True,
        'evidence': [
            {
                'source_type': 'deploy',
                'source_ref': 'deploy-20260617-1200',
                'observed_at': '2026-06-17T12:06:00Z',
                'summary': 'Error rate increased.',
            }
        ],
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/finding.schema.json')
    assert len(errors) > 0


def test_finding_schema_invalid_empty_evidence():
    """A finding with an empty evidence array must fail."""
    sample = {
        'finding_id': '44baafbf-fd7f-4f2d-9fc3-518e536d9281',
        'title': 'No evidence finding',
        'category': 'reliability',
        'severity': 'p1',
        'confidence': 0.82,
        'status': 'open',
        'services': ['payments-api'],
        'first_seen': '2026-06-17T12:05:00Z',
        'last_seen': '2026-06-17T12:10:00Z',
        'owner': 'team-payments',
        'hypothesis': 'Something happened.',
        'suggested_fix': 'Fix it.',
        'blast_radius': 'service',
        'sla_impact': True,
        'evidence': [],  # minItems: 1 violation
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/finding.schema.json')
    assert len(errors) > 0


def test_dependency_edge_schema_requires_allowed_flag():
    sample = {
        'edge_id': 'a1c7b3ae-2f7f-4ed6-ab58-829640d3d98e',
        'source': 'frontend',
        'target': 'payments-api',
        'edge_type': 'runtime',
        'observed_at': '2026-06-17T12:11:00Z',
        'confidence': 0.7,
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/dependency_edge.schema.json')
    assert any('allowed' in err for err in errors)


def test_deploy_event_schema_valid_sample():
    sample = {
        'deploy_id': 'deploy-20260617-1200',
        'service': 'payments-api',
        'commit_sha': 'abc1234',
        'actor': 'github-actions',
        'started_at': '2026-06-17T11:59:00Z',
        'completed_at': '2026-06-17T12:01:00Z',
        'status': 'succeeded',
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/deploy_event.schema.json')
    assert errors == []


def test_deploy_event_schema_invalid_bad_status():
    """A deploy event with an invalid status enum must fail."""
    sample = {
        'deploy_id': 'deploy-20260617-1200',
        'service': 'payments-api',
        'commit_sha': 'abc1234',
        'actor': 'github-actions',
        'started_at': '2026-06-17T11:59:00Z',
        'completed_at': '2026-06-17T12:01:00Z',
        'status': 'running',  # invalid enum
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/deploy_event.schema.json')
    assert len(errors) > 0


def test_deploy_event_schema_invalid_missing_actor():
    """A deploy event missing the actor field must fail."""
    sample = {
        'deploy_id': 'deploy-20260617-1200',
        'service': 'payments-api',
        'commit_sha': 'abc1234',
        'started_at': '2026-06-17T11:59:00Z',
        'completed_at': '2026-06-17T12:01:00Z',
        'status': 'succeeded',
        # missing: actor
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/deploy_event.schema.json')
    assert len(errors) > 0


def test_dependency_edge_schema_valid_sample():
    """A fully valid dependency_edge record must pass."""
    sample = {
        'edge_id': 'a1c7b3ae-2f7f-4ed6-ab58-829640d3d98e',
        'source': 'frontend',
        'target': 'payments-api',
        'edge_type': 'runtime',
        'observed_at': '2026-06-17T12:11:00Z',
        'confidence': 0.7,
        'allowed': True,
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/dependency_edge.schema.json')
    assert errors == []


# --- New schema tests (BEAD-01): dispatch_queue_item, architecture_rule, drift_report ---


def test_dispatch_queue_item_schema_valid_sample():
    sample = {
        'id': '11111111-1111-1111-1111-111111111111',
        'finding_id': '22222222-2222-2222-2222-222222222222',
        'owner': 'team-payments',
        'agent_role': 'BUILDER',
        'evidence_ref': 'deploy-20260617-1200',
        'acceptance_criteria': 'Error rate returns below 1% within 30 minutes of rollback.',
        'stop_condition': 'If root cause requires schema migration, escalate to ORCHESTRATOR.',
        'priority': 'p1',
        'status': 'queued',
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/dispatch_queue_item.schema.json')
    assert errors == []


def test_dispatch_queue_item_schema_invalid_missing_required():
    sample = {
        'id': '11111111-1111-1111-1111-111111111111',
        'finding_id': '22222222-2222-2222-2222-222222222222',
        # missing owner, agent_role, evidence_ref, acceptance_criteria, stop_condition, priority, status
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/dispatch_queue_item.schema.json')
    assert len(errors) > 0


def test_architecture_rule_schema_valid_sample():
    sample = {
        'rule_id': 'RULE-001',
        'source': 'frontend',
        'target': 'payments-api',
        'edge_type': 'runtime',
        'decision': 'allowed',
        'severity': 'p2',
        'rationale': 'Frontend is permitted to call the payments API.',
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/architecture_rule.schema.json')
    assert errors == []


def test_architecture_rule_schema_invalid_bad_decision():
    sample = {
        'rule_id': 'RULE-002',
        'source': 'frontend',
        'target': 'database',
        'edge_type': 'runtime',
        'decision': 'maybe',  # invalid enum
        'severity': 'p0',
        'rationale': 'Direct DB access is not allowed.',
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/architecture_rule.schema.json')
    assert len(errors) > 0


def test_drift_report_schema_valid_sample():
    sample = {
        'report_id': '33333333-3333-3333-3333-333333333333',
        'generated_at': '2026-06-17T13:00:00Z',
        'edges': [
            {
                'edge_id': '44444444-4444-4444-4444-444444444444',
                'source': 'frontend',
                'target': 'payments-api',
                'edge_type': 'runtime',
                'classification': 'intentional',
                'rule_id': 'RULE-001',
            }
        ],
        'summary': {
            'intentional': 1,
            'accidental': 0,
            'blocked': 0,
            'unknown': 0,
            'total': 1,
        },
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/drift_report.schema.json')
    assert errors == []


def test_drift_report_schema_invalid_bad_classification():
    sample = {
        'report_id': '55555555-5555-5555-5555-555555555555',
        'generated_at': '2026-06-17T13:00:00Z',
        'edges': [
            {
                'edge_id': '66666666-6666-6666-6666-666666666666',
                'source': 'frontend',
                'target': 'database',
                'edge_type': 'runtime',
                'classification': 'suspicious',  # invalid enum
            }
        ],
        'summary': {
            'intentional': 0,
            'accidental': 0,
            'blocked': 0,
            'unknown': 0,
            'total': 1,
        },
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/drift_report.schema.json')
    assert len(errors) > 0
