.PHONY: install dev test test-bdd test-unit lint typecheck clean run docs

install:
	uv tool install .

dev:
	uv pip install -e ".[dev]"

test:
	uv run pytest

test-unit:
	uv run pytest tests/unit/

test-bdd:
	uv run pytest tests/bdd/

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage dist build
	find . -type d -name __pycache__ -exec rm -rf {} +

run:
	uv run flow

docs:
	uv run python scripts/generate_prompts_doc.py
