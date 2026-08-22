# Atalhos do dia a dia. `make check` e o mesmo gate do CI.
BACKEND := code/backend
FRONTEND := code/frontend
PY := $(BACKEND)/.venv/Scripts/python

.PHONY: help setup check backend-check frontend-check test lint format api console clean

help:
	@echo "setup           instala backend (venv) e frontend"
	@echo "check           gate completo: backend + frontend"
	@echo "test            pytest"
	@echo "lint            ruff + mypy"
	@echo "format          aplica o formatter"
	@echo "api             sobe a API em :8000"
	@echo "console         sobe o Console em :5173"
	@echo "clean           remove workspaces gerados e caches"

setup:
	cd $(BACKEND) && python -m venv .venv && .venv/Scripts/python -m pip install -q -e ".[dev]"
	cd $(FRONTEND) && npm install

check: backend-check frontend-check

backend-check:
	cd $(BACKEND) && .venv/Scripts/python -m ruff check .
	cd $(BACKEND) && .venv/Scripts/python -m ruff format --check .
	cd $(BACKEND) && .venv/Scripts/python -m mypy .
	cd $(BACKEND) && .venv/Scripts/python -m pytest

frontend-check:
	cd $(FRONTEND) && npx tsc --noEmit
	cd $(FRONTEND) && npx vite build

test:
	cd $(BACKEND) && .venv/Scripts/python -m pytest

lint:
	cd $(BACKEND) && .venv/Scripts/python -m ruff check .
	cd $(BACKEND) && .venv/Scripts/python -m mypy .

format:
	cd $(BACKEND) && .venv/Scripts/python -m ruff check . --fix
	cd $(BACKEND) && .venv/Scripts/python -m ruff format .

api:
	cd $(BACKEND) && .venv/Scripts/uvicorn main:app --reload

console:
	cd $(FRONTEND) && npm run dev

clean:
	rm -rf .workspaces $(BACKEND)/.pytest_cache $(BACKEND)/.mypy_cache $(BACKEND)/.ruff_cache
	find $(BACKEND) -name __pycache__ -type d -prune -exec rm -rf {} +
