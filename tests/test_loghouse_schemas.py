from scripts.common import ROOT, validate_with_schema


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


def test_dispatch_queue_item_schema_valid_sample():
    sample = {
        'id': '6d6942e2-36db-4ce7-84d8-b75a4ef3ce53',
        'finding_id': '44baafbf-fd7f-4f2d-9fc3-518e536d9281',
        'owner': 'team-payments',
        'agent_role': 'BUILDER',
        'evidence_ref': 'deploy-20260617-1200',
        'acceptance_criteria': 'Rollback deploy and verify error rate returns to baseline.',
        'stop_condition': 'Production error rate exceeds SLO for more than 15 minutes.',
        'priority': 'p1',
        'status': 'queued',
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/dispatch_queue_item.schema.json')
    assert errors == []


def test_dispatch_queue_item_schema_requires_agent_role():
    sample = {
        'id': '6d6942e2-36db-4ce7-84d8-b75a4ef3ce53',
        'finding_id': '44baafbf-fd7f-4f2d-9fc3-518e536d9281',
        'owner': 'team-payments',
        'evidence_ref': 'deploy-20260617-1200',
        'acceptance_criteria': 'Rollback deploy and verify error rate returns to baseline.',
        'stop_condition': 'Production error rate exceeds SLO for more than 15 minutes.',
        'priority': 'p1',
        'status': 'queued',
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/dispatch_queue_item.schema.json')
    assert any('agent_role' in err for err in errors)


def test_architecture_rule_schema_valid_sample():
    sample = {
        'rule_id': 'RULE-001',
        'source': 'frontend',
        'target': 'payments-api',
        'edge_type': 'runtime',
        'decision': 'allowed',
        'severity': 'p2',
        'rationale': 'Frontend calls payments API for checkout.',
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/architecture_rule.schema.json')
    assert errors == []


def test_architecture_rule_schema_requires_decision():
    sample = {
        'rule_id': 'RULE-001',
        'source': 'frontend',
        'target': 'payments-api',
        'edge_type': 'runtime',
        'severity': 'p2',
        'rationale': 'Frontend calls payments API for checkout.',
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/architecture_rule.schema.json')
    assert any('decision' in err for err in errors)


def test_drift_report_schema_valid_sample():
    sample = {
        'report_id': 'a1c7b3ae-2f7f-4ed6-ab58-829640d3d98e',
        'generated_at': '2026-06-18T01:15:00Z',
        'edges': [
            {
                'edge_id': 'b2d8c4bf-3f8a-5fe7-bc69-930751e4e09f',
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


def test_drift_report_schema_requires_summary():
    sample = {
        'report_id': 'a1c7b3ae-2f7f-4ed6-ab58-829640d3d98e',
        'generated_at': '2026-06-18T01:15:00Z',
        'edges': [],
    }
    errors = validate_with_schema(sample, ROOT / 'schemas/drift_report.schema.json')
    assert any('summary' in err for err in errors)
