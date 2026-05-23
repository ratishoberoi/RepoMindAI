.PHONY: setup api test lint frontend

setup:
	uv venv
	uv pip install -e ".[dev,analysis]"

api:
	PYTHONPATH=backend uvicorn repomind.main:app --reload --host 0.0.0.0 --port 8000

test:
	PYTHONPATH=backend pytest

lint:
	PYTHONPATH=backend ruff check backend tests

frontend:
	cd frontend && npm install && npm run dev

