.PHONY: setup check format test smoke build run

setup:
	uv sync --frozen

check:
	uv run --frozen python scripts/check.py
	uv run --frozen ruff check .
	uv run --frozen ruff format --check .
	uv run --frozen pyright

format:
	uv run --frozen ruff check --fix .
	uv run --frozen ruff format .

test:
	uv run --frozen pytest -q

smoke:
	uv run --frozen pytest -q -m smoke

build:
	uv build

run:
	uv run --frozen uvicorn chatbot.main:app --host 127.0.0.1 --port 8000
