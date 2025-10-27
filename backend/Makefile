.PHONY: up down psql migrate seed logs status clean help

help: ## Show this help message
	@echo "Reploom Backend - Docker Compose Management"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: ## Start all services (postgres, redis, qdrant)
	@echo "Starting all services..."
	docker compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 2
	docker compose ps

down: ## Stop all services
	@echo "Stopping all services..."
	docker compose down

psql: ## Connect to PostgreSQL database
	@echo "Connecting to PostgreSQL..."
	docker compose exec postgres psql -U postgres -d ai_documents_db

migrate: ## Run database migrations (initialize database)
	@echo "Running database migrations..."
	@if [ ! -d ".venv" ]; then \
		echo "Virtual environment not found. Run 'uv sync' first."; \
		exit 1; \
	fi
	@echo "Initializing database schema..."
	. .venv/bin/activate && python -c "from app.core.db import init_db; init_db(); print('Database initialized successfully!')"

seed: ## Seed database with demo data for 5-minute walkthrough
	@echo "Seeding database with demo data..."
	@if [ ! -d ".venv" ]; then \
		echo "Virtual environment not found. Run 'uv sync' first."; \
		exit 1; \
	fi
	. .venv/bin/activate && python seed_demo.py

logs: ## Show logs from all services
	docker compose logs -f

status: ## Show status of all services
	docker compose ps

clean: ## Stop services and remove volumes (WARNING: deletes all data)
	@echo "WARNING: This will delete all data in volumes!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose down -v; \
		echo "Services stopped and volumes removed."; \
	else \
		echo "Cancelled."; \
	fi

restart: ## Restart all services
	@echo "Restarting all services..."
	docker compose restart

dev: up ## Start services and run development server
	@echo "Services started. Now run:"
	@echo "  source .venv/bin/activate"
	@echo "  fastapi dev app/main.py"
