# Makefile for nucmass development
#
# Usage:
#   make help        Show this help message
#   make install     Install package in development mode
#   make test        Run tests with pytest
#   make docs        Build Sphinx documentation
#   make jupyter     Launch Jupyter Lab
#
# Requirements:
#   - Python 3.12+
#   - uv (recommended) or pip

.PHONY: help install install-all test test-cov lint format docs docs-live docs-stop jupyter clean clean-all

# Default target
.DEFAULT_GOAL := help

# Colors for help output
BLUE := \033[36m
RESET := \033[0m

#-----------------------------------------------------------------------
# Help
#-----------------------------------------------------------------------

help: ## Show this help message
	@echo "nucmass development commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BLUE)%-15s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "Examples:"
	@echo "  make install      Install for development"
	@echo "  make test         Run all tests"
	@echo "  make docs         Build documentation"

#-----------------------------------------------------------------------
# Installation
#-----------------------------------------------------------------------

install: ## Install package in development mode
	@if command -v uv >/dev/null 2>&1; then \
		echo "Installing with uv..."; \
		uv pip install -e ".[dev]"; \
	else \
		echo "Installing with pip..."; \
		pip install -e ".[dev]"; \
	fi

install-all: ## Install with all optional dependencies
	@if command -v uv >/dev/null 2>&1; then \
		echo "Installing all dependencies with uv..."; \
		uv pip install -e ".[all]"; \
	else \
		echo "Installing all dependencies with pip..."; \
		pip install -e ".[all]"; \
	fi

#-----------------------------------------------------------------------
# Testing
#-----------------------------------------------------------------------

test: ## Run tests with pytest
	python -m pytest tests/ -v

test-cov: ## Run tests with coverage report
	python -m pytest tests/ -v --cov=src/nucmass --cov-report=term-missing --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

test-fast: ## Run tests without slow markers
	python -m pytest tests/ -v -m "not slow"

#-----------------------------------------------------------------------
# Code Quality
#-----------------------------------------------------------------------

lint: ## Run linters (ruff check + type hints)
	@echo "Running ruff..."
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check src/nucmass tests; \
	else \
		echo "ruff not installed. Install with: uv pip install ruff"; \
	fi
	@echo "Running mypy..."
	@if command -v mypy >/dev/null 2>&1; then \
		mypy src/nucmass --ignore-missing-imports; \
	else \
		echo "mypy not installed. Install with: uv pip install mypy"; \
	fi

format: ## Auto-format code with ruff
	@if command -v ruff >/dev/null 2>&1; then \
		ruff format src/nucmass tests; \
		ruff check --fix src/nucmass tests; \
	else \
		echo "ruff not installed. Install with: uv pip install ruff"; \
	fi

#-----------------------------------------------------------------------
# Documentation
#-----------------------------------------------------------------------

docs: ## Build Sphinx documentation
	@if [ ! -d "docs/_build" ]; then mkdir -p docs/_build; fi
	$(MAKE) -C docs html
	@echo "Documentation: docs/_build/html/index.html"

docs-live: ## Build docs with live reload (auto-refresh on changes)
	$(MAKE) -C docs livehtml

docs-stop: ## Stop the live docs server
	@pkill -f "sphinx-autobuild" 2>/dev/null && echo "Docs server stopped" || echo "No docs server running"

docs-clean: ## Clean documentation build
	$(MAKE) -C docs clean

#-----------------------------------------------------------------------
# Development Tools
#-----------------------------------------------------------------------

jupyter: ## Launch Jupyter Lab with notebooks
	@if command -v jupyter >/dev/null 2>&1; then \
		jupyter lab notebooks/; \
	else \
		echo "Jupyter not installed. Run: make install-all"; \
	fi

ipython: ## Launch IPython shell with nucmass imported
	@if command -v ipython >/dev/null 2>&1; then \
		ipython -i -c "from nucmass import NuclearDatabase; db = NuclearDatabase(); print('NuclearDatabase loaded as: db')"; \
	else \
		echo "IPython not installed. Run: make install"; \
	fi

#-----------------------------------------------------------------------
# Database Management
#-----------------------------------------------------------------------

db-init: ## Initialize/rebuild the nuclear database
	nucmass init --rebuild

db-summary: ## Show database summary
	nucmass summary

#-----------------------------------------------------------------------
# Cleanup
#-----------------------------------------------------------------------

clean: ## Remove Python cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage 2>/dev/null || true

clean-all: clean docs-clean ## Remove all generated files (cache + docs)
	rm -rf dist/ build/ 2>/dev/null || true

#-----------------------------------------------------------------------
# Release (for maintainers)
#-----------------------------------------------------------------------

build: clean ## Build distribution packages
	python -m build

check-release: ## Check package before release
	twine check dist/*
