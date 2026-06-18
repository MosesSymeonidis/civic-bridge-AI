COMPOSE_LOCAL = docker compose -f compose.yaml -f compose.local.yaml

.PHONY: up down logs build backend-migrate backend-seed backend-test frontend-check check

up:
	$(COMPOSE_LOCAL) up --build

down:
	$(COMPOSE_LOCAL) down

logs:
	$(COMPOSE_LOCAL) logs --follow

build:
	$(COMPOSE_LOCAL) build

backend-migrate:
	cd backend && alembic upgrade head

backend-seed:
	cd backend && SEED_DEMO_DATA=true python -m app.scripts.seed_demo_data

backend-test:
	cd backend && pytest

frontend-check:
	cd frontend && npm run check

check: backend-test frontend-check
