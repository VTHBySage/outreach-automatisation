.PHONY: install dev run test lint format migrate celery flower docker-up docker-down clean

# Install production dependencies
install:
	pip install -e .

# Install development dependencies
dev:
	pip install -e ".[dev]"

# Run the FastAPI application
run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
test:
	pytest tests/ -v --cov=app --cov-report=term-missing

# Run a single test file
test-file:
	pytest $(FILE) -v

# Lint code
lint:
	ruff check app/ tests/
	mypy app/

# Format code
format:
	black app/ tests/
	ruff check --fix app/ tests/

# Create a new migration
migrate-create:
	alembic revision --autogenerate -m "$(MSG)"

# Run migrations
migrate:
	alembic upgrade head

# Rollback last migration
migrate-rollback:
	alembic downgrade -1

# Start Celery worker
celery:
	celery -A app.workers.celery_app worker --loglevel=info

# Start Celery worker with specific queue
celery-queue:
	celery -A app.workers.celery_app worker --loglevel=info -Q $(QUEUE)

# Start Celery beat scheduler
celery-beat:
	celery -A app.workers.celery_app beat --loglevel=info

# Start Flower monitoring
flower:
	celery -A app.workers.celery_app flower --port=5555

# Start Docker services
docker-up:
	docker-compose up -d

# Stop Docker services
docker-down:
	docker-compose down

# Build Docker image
docker-build:
	docker build -t outreach-automation .

# Clean up
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov dist build *.egg-info

# Show help
help:
	@echo "Available commands:"
	@echo "  install        - Install production dependencies"
	@echo "  dev            - Install development dependencies"
	@echo "  run            - Run FastAPI application"
	@echo "  test           - Run all tests"
	@echo "  lint           - Run linters"
	@echo "  format         - Format code"
	@echo "  migrate        - Run database migrations"
	@echo "  migrate-create - Create new migration (MSG=description)"
	@echo "  celery         - Start Celery worker"
	@echo "  flower         - Start Flower monitoring"
	@echo "  docker-up      - Start Docker services"
	@echo "  docker-down    - Stop Docker services"
	@echo "  clean          - Clean up temporary files"
