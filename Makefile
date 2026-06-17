.PHONY: check validate go test tree

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
