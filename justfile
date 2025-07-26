# Default recipe to show available commands
default:
    @just --list

install:
    uv pip install -e .

test:
    uv run python test.py