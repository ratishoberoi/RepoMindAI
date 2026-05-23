.PHONY: setup api test lint frontend

setup:
	uv venv
	uv pip install -e ".[analysis,dev]"

api:
	PYTHONPATH=backend uvicorn repomind.main:app --reload --host 0.0.0.0 --port 8000

test:
	PYTHONPATH=backend .venv/bin/pytest

lint:
	PYTHONPATH=backend .venv/bin/ruff check backend tests scripts

frontend:
	cd frontend && npm install && npm run dev
