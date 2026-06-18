.PHONY: check validate go test tree loghouse loghouse-gate

check:
	python scripts/cat_check_repo.py

validate:
	python scripts/cat_validate.py --all

go:
	python scripts/cat_resolve_go.py

test:
	pytest -q

tree:
	find . -maxdepth 3 -type f | sort

# LOGHOUSE: run all checks locally (mirrors cat-loghouse-ci.yml)
loghouse: loghouse-gate
	python scripts/cat_validate.py --all
	python scripts/cat_loghouse.py --input tests/fixtures/loghouse
	pytest -q tests/test_loghouse_schemas.py tests/test_loghouse_engine.py tests/test_loghouse_rules.py tests/test_loghouse_drift.py
	python scripts/cat_validate_loghouse.py --root .

# LOGHOUSE drift gate: fail if any P0/P1 forbidden edge is present
loghouse-gate:
	python scripts/loghouse/drift_gate.py \
		--rules reference/loghouse/architecture_rules.yaml \
		--edges tests/fixtures/loghouse/dependency_edges.json \
		--fail-on p0,p1
