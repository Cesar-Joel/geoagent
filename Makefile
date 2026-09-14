PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin
STAMP := $(VENV)/.installed

.DEFAULT_GOAL := help
.PHONY: help install lint format test test-unit test-integration

help:
	@echo "Objetivos: install lint format test test-unit test-integration"

install: $(STAMP)

$(STAMP): pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install --disable-pip-version-check -q -e ".[dev]"
	touch $(STAMP)

RUFF_PATHS := src tests

lint: $(STAMP)
	$(BIN)/ruff check $(RUFF_PATHS)
	$(BIN)/ruff format --check $(RUFF_PATHS)

format: $(STAMP)
	$(BIN)/ruff check --select I --fix $(RUFF_PATHS)
	$(BIN)/ruff format $(RUFF_PATHS)

test: test-unit test-integration

test-unit: $(STAMP)
	$(BIN)/python -m pytest tests/unit -q

# pytest devuelve 5 cuando no recoge ningún test; una suite vacía no es un fallo.
test-integration: $(STAMP)
	@$(BIN)/python -m pytest tests/integration -q; rc=$$?; \
	if [ $$rc -eq 5 ]; then \
		echo "tests/integration: sin tests todavía (pytest exit 5), se considera OK"; \
		exit 0; \
	fi; \
	exit $$rc
