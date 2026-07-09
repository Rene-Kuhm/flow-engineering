.PHONY: install dev test test-bdd test-unit lint security pip-audit typecheck clean run docs

install:
	uv tool install .

dev:
	uv sync --locked --all-extras --dev

test:
	uv run pytest

test-unit:
	uv run pytest tests/unit/

test-bdd:
	uv run pytest tests/bdd/

lint:
	uv run ruff check src tests

security:
	uv run ruff check --select S102,S105,S106,S107,S108,S301,S302,S303,S304,S305,S306,S307,S308,S310,S312,S313,S314,S315,S316,S317,S318,S319,S321,S323,S501,S502,S503,S504,S505,S506,S507,S508,S509,S601,S602,S604,S605,S606,S608,S609,S610,S611,S612 src scripts

pip-audit:
	pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/pip_audit.ps1

typecheck:
	uv run mypy src

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage dist build
	find . -type d -name __pycache__ -exec rm -rf {} +

run:
	uv run flow

docs:
	uv run python scripts/generate_prompts_doc.py
