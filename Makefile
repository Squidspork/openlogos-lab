.PHONY: install dev test lint typecheck check doctor demo clean

install:
	python -m pip install -e .

dev:
	python -m pip install -e ".[dev]"

test:
	SALINAS_OFFLINE=true pytest

lint:
	ruff check .

typecheck:
	mypy salinas_lab

check: lint typecheck test

doctor:
	openlogos-lab doctor

demo:
	openlogos-lab --demo

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info
