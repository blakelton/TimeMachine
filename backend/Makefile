.PHONY: help install install-dev run test lint format type-check clean

help:
	@echo "TimeMachine Backend - Make Commands"
	@echo ""
	@echo "  install       Install production dependencies"
	@echo "  install-dev   Install development dependencies"
	@echo "  run           Run development server"
	@echo "  test          Run tests with coverage"
	@echo "  lint          Run ruff linter"
	@echo "  format        Format code with black and ruff"
	@echo "  type-check    Run mypy type checker"
	@echo "  clean         Remove cache and build files"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

run:
	uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

test:
	pytest

lint:
	ruff check app tests

format:
	black app tests
	ruff check --fix app tests

type-check:
	mypy app

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov .coverage
