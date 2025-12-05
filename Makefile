# SpecMem Makefile
# Convenience commands for development

.PHONY: help install dev test lint format typecheck clean build docs serve

# Default target
help:
	@echo "SpecMem Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install     Install production dependencies"
	@echo "  make dev         Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test        Run all tests"
	@echo "  make test-unit   Run unit tests only"
	@echo "  make test-prop   Run property tests only"
	@echo "  make test-cov    Run tests with coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint        Run linter (ruff check)"
	@echo "  make format      Format code (ruff format)"
	@echo "  make typecheck   Run type checker (mypy)"
	@echo "  make check       Run all checks (lint + typecheck + test)"
	@echo ""
	@echo "Build:"
	@echo "  make build       Build package"
	@echo "  make clean       Clean build artifacts"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs        Build documentation"
	@echo "  make serve       Serve documentation locally"

# =============================================================================
# Setup
# =============================================================================

install:
	pip install -e .

install-uv:
	uv sync

dev:
	pip install -e ".[dev]"
	pre-commit install
	pre-commit install --hook-type commit-msg

dev-uv:
	uv sync --dev
	uv run pre-commit install
	uv run pre-commit install --hook-type commit-msg

# =============================================================================
# Testing
# =============================================================================

test:
	pytest tests/ -v

test-unit:
	pytest tests/unit -v

test-prop:
	pytest tests/property -v --hypothesis-seed=42

test-cov:
	pytest tests/ --cov=specmem --cov-report=html --cov-report=term-missing -v
	@echo "Coverage report: htmlcov/index.html"

test-fast:
	pytest tests/ -v -x --tb=short -q

# =============================================================================
# Code Quality
# =============================================================================

lint:
	ruff check .

lint-fix:
	ruff check --fix .

format:
	ruff format .

format-check:
	ruff format --check .

typecheck:
	mypy specmem --ignore-missing-imports

check: lint typecheck test
	@echo "All checks passed!"

# =============================================================================
# Build
# =============================================================================

build: clean
	python -m build
	twine check dist/*

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# =============================================================================
# Documentation
# =============================================================================

docs:
	mkdocs build

serve:
	mkdocs serve

# =============================================================================
# Development Utilities
# =============================================================================

# Run the CLI
run:
	python -m specmem.cli.main

# Start the web UI
ui:
	python -m specmem.ui.server

# Update pre-commit hooks
hooks-update:
	pre-commit autoupdate

# Run pre-commit on all files
hooks-run:
	pre-commit run --all-files
