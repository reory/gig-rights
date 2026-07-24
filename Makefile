.PHONY: help up down restart build logs test test-docker cli-classify clean

# Default command when running just 'make'
.DEFAULT_GOAL := help

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: ## Start Docker containers in the background
	docker compose up -d

down: ## Stop all Docker containers
	docker compose down

restart: ## Restart Docker services
	docker compose restart

build: ## Rebuild and start Docker containers
	docker compose up -d --build

logs: ## Stream live logs from the API container
	docker compose logs -f

test: ## Run unit tests locally with pytest
	pytest -v

test-docker: ## Run unit tests inside the active Docker container
	docker compose exec api pytest -v

cli-batch: ## Run CSV batch calculation inside Docker container
	docker compose exec api gig-rights batch-csv data/test_pay_periods.csv

clean: ## Remove Python bytecode and test cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .coverage