.PHONY: install run dev dev-backend dev-frontend test test-gen lint build report clean

# Installation & Startup
install:
	bash install.sh

run:
	bash run.sh

# Development
dev-backend:
	cd backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

dev-frontend:
	cd frontend && npm run dev

dev:
	@echo "Run 'make dev-backend' and 'make dev-frontend' in separate terminals"

# Testing & Verification
test:
	cd backend && python -m pytest tests/ -v

test-gen:
	cd backend && python -m pytest tests/test_generator.py -v

# Evaluation & Benchmark Reporting
report:
	cd backend && python -m chainsentinel.cli report --db data/chainsentinel.duckdb --eval-ground-truth data/cli_test/ground_truth.json --output-dir ../docs

# Code Quality
lint:
	cd backend && python -m ruff check .
	cd backend && python -m mypy chainsentinel/ app/ --ignore-missing-imports

# Build Frontend
build:
	cd frontend && npm run build
	@echo "Frontend static bundle built successfully to frontend/out/"

# Clean Temporary Data & Caches
clean:
	rm -rf backend/.venv backend/__pycache__ backend/**/__pycache__ backend/.pytest_cache
	rm -rf frontend/out frontend/node_modules frontend/.vite
	rm -rf data/models/*.pkl data/test_output data/test_output_2
