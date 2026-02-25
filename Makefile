.PHONY: help install run migrate makemigrations createsuperuser shell test lint format docker-up docker-down celery

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
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

docker-up: ## Start Docker services
	docker compose up -d

docker-down: ## Stop Docker services
	docker compose down

celery: ## Start Celery worker
	celery -A config worker -l info

celery-beat: ## Start Celery beat
	celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

collectstatic: ## Collect static files
	python manage.py collectstatic --noinput

flush: ## Reset database
	python manage.py flush --noinput

seed: ## Load seed data
	python manage.py loaddata fixtures/*.json
