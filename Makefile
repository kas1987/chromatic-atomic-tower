.PHONY: check validate go test tree harness mermaid confidence bundle harness-all

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

# --- MP-CAT-A006-4C01 Harness Engineering validation ---
harness:
	python scripts/cat_validate_harness_alignment.py --root .

mermaid:
	python scripts/cat_validate_mermaid.py --root .

confidence:
	python scripts/cat_score_confidence.py --root . --mission MP-CAT-A006-4C01 --dry-run

bundle:
	python scripts/cat_generate_evidence_bundle.py --root . --mission MP-CAT-A006-4C01 --dry-run

harness-all: check validate harness mermaid test
