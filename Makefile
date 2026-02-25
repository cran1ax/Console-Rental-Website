.PHONY: help install run migrate makemigrations createsuperuser shell test lint format docker-up docker-down celery celery-beat collectstatic flush seed prod-build prod-up prod-down prod-logs prod-restart prod-shell prod-migrate

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ════════════════════════════════════════════════════════════════
# Development
# ════════════════════════════════════════════════════════════════

install: ## Install dev dependencies
	pip install -r requirements/dev.txt

run: ## Run development server
	python manage.py runserver

migrate: ## Run migrations
	python manage.py migrate

makemigrations: ## Create migrations
	python manage.py makemigrations

createsuperuser: ## Create superuser
	python manage.py createsuperuser

shell: ## Django shell plus
	python manage.py shell_plus

test: ## Run tests
	pytest

lint: ## Run linting
	flake8 apps/
	mypy apps/

format: ## Format code
	black apps/ config/
	isort apps/ config/

docker-up: ## Start Docker services (dev)
	docker compose up -d

docker-down: ## Stop Docker services (dev)
	docker compose down

celery: ## Start Celery worker (dev)
	celery -A config worker -l info

celery-beat: ## Start Celery beat (dev)
	celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

collectstatic: ## Collect static files
	python manage.py collectstatic --noinput

flush: ## Reset database
	python manage.py flush --noinput

seed: ## Load seed data
	python manage.py loaddata fixtures/*.json

# ════════════════════════════════════════════════════════════════
# Production
# ════════════════════════════════════════════════════════════════

prod-build: ## Build production Docker images
	docker compose -f docker-compose.prod.yml build

prod-up: ## Start all production services
	docker compose -f docker-compose.prod.yml up -d

prod-down: ## Stop all production services
	docker compose -f docker-compose.prod.yml down

prod-logs: ## Tail production logs (all services)
	docker compose -f docker-compose.prod.yml logs -f

prod-logs-web: ## Tail web server logs only
	docker compose -f docker-compose.prod.yml logs -f web nginx

prod-restart: ## Restart production web + workers (zero-downtime)
	docker compose -f docker-compose.prod.yml restart web celery-worker celery-beat

prod-shell: ## Open Django shell in production container
	docker compose -f docker-compose.prod.yml exec web python manage.py shell_plus

prod-migrate: ## Run migrations in production
	docker compose -f docker-compose.prod.yml exec web python manage.py migrate --noinput

prod-createsuperuser: ## Create superuser in production
	docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

prod-status: ## Show status of all production services
	docker compose -f docker-compose.prod.yml ps

prod-backup-db: ## Backup production database
	docker compose -f docker-compose.prod.yml exec db pg_dump -U corner_console corner_console_db > backup_$$(date +%Y%m%d_%H%M%S).sql

