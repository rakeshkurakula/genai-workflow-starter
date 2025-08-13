# GenAI Workflow Starter - Makefile
# Development targets for the monorepo

.PHONY: help dev setup clean build test evals ingest

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Initial setup - install dependencies
	@echo "Setting up development environment..."
	pnpm install
	docker compose pull
	@echo "Setup complete!"

dev: ## Start development environment
	@echo "Starting development environment..."
	docker compose up -d vectordb mcp-server
	@echo "Development services started!"
	@echo "Vector DB: http://localhost:6333"
	@echo "MCP Server: http://localhost:3000"
	@echo "Run 'make dev-api' to start the API server"

dev-api: ## Start API server in development mode
	@echo "Starting API server..."
	cd apps/api && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

stop: ## Stop all services
	@echo "Stopping services..."
	docker compose down
	@echo "Services stopped!"

build: ## Build all services
	@echo "Building services..."
	docker compose build
	pnpm build
	@echo "Build complete!"

test: ## Run all tests
	@echo "Running tests..."
	pnpm test
	@echo "Tests complete!"

test-agents: ## Run agent tests
	@echo "Running agent tests..."
	cd agents && python -m pytest tests/ -v

test-api: ## Run API tests
	@echo "Running API tests..."
	cd apps/api && python -m pytest tests/ -v

evals: ## Run evaluation suite
	@echo "Running evaluations..."
	@if [ -d "evals" ]; then \
		cd evals && python -m pytest tests/ -v --tb=short; \
	else \
		echo "No evals directory found. Create evals/ with your evaluation tests."; \
	fi

ingest: ## Ingest seed data into vector database
	@echo "Ingesting seed data..."
	@if [ -f "data/seed/ingest.py" ]; then \
		cd data/seed && python ingest.py; \
	else \
		echo "Creating sample ingest script..."; \
		mkdir -p data/seed; \
		echo "# Seed data ingestion script" > data/seed/ingest.py; \
		echo "print('Add your data ingestion logic here')" >> data/seed/ingest.py; \
		echo "Sample ingest script created at data/seed/ingest.py"; \
	fi

clean: ## Clean up containers and volumes
	@echo "Cleaning up..."
	docker compose down -v
	docker system prune -f
	@echo "Cleanup complete!"

logs: ## Show logs from all services
	docker compose logs -f

logs-api: ## Show API logs
	docker compose logs -f api

logs-vectordb: ## Show vector DB logs  
	docker compose logs -f vectordb

logs-mcp: ## Show MCP server logs
	docker compose logs -f mcp-server

shell-api: ## Open shell in API container
	docker compose exec api bash

shell-vectordb: ## Open shell in vector DB container
	docker compose exec vectordb bash

format: ## Format code
	@echo "Formatting code..."
	pnpm format
	@if command -v black >/dev/null 2>&1; then \
		black agents/ apps/; \
	fi
	@if command -v isort >/dev/null 2>&1; then \
		isort agents/ apps/; \
	fi

lint: ## Lint code
	@echo "Linting code..."
	pnpm lint
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 agents/ apps/; \
	fi

type-check: ## Run type checking
	@echo "Running type checks..."
	@if command -v mypy >/dev/null 2>&1; then \
		mypy agents/ apps/; \
	fi
