# Default recipe to show available commands
default:
    @just --list

install:
    uv pip install -e .

install-dev:
    uv pip install -e ".[dev]"

format:
    uv run ruff format .

format-check:
    uv run ruff format --check .

lint:
    uv run ruff check .

lint-fix:
    uv run ruff check --fix .

test:
    uv run python tests/test.py