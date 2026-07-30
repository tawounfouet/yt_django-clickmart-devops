.PHONY: up-dev up-staging up-prod down-dev down-staging down-prod logs logs-staging logs-prod ps clean
.PHONY: api-test api-lint api-shell api-migrate
.PHONY: web-dev web-test web-lint web-build
.PHONY: ci

# ─── Dev local (pas de -p, tests uniquement) ───
up-dev:
	docker compose up -d --build

down-dev:
	docker compose down

# ─── Staging (port 8080) ───
up-staging:
	docker compose -p clickmart-stg -f docker-compose.yml -f docker-compose.staging.yml up -d --build

down-staging:
	docker compose -p clickmart-stg -f docker-compose.yml -f docker-compose.staging.yml down

logs-staging:
	docker compose -p clickmart-stg -f docker-compose.yml -f docker-compose.staging.yml logs -f --tail=50

# ─── Production (ports 80/443, prod uniquement sur le serveur) ───
up-prod:
	docker compose -p clickmart -f docker-compose.yml -f docker-compose.prod.yml up -d --build

down-prod:
	docker compose -p clickmart -f docker-compose.yml -f docker-compose.prod.yml down

logs-prod:
	docker compose -p clickmart -f docker-compose.yml -f docker-compose.prod.yml logs -f --tail=50

# ─── Utilitaires ───
logs:
	docker compose logs -f --tail=50

ps:
	docker compose ps

clean:
	docker compose down -v --remove-orphans

# ─── API ───
api-test:
	cd backend && python -m pytest -q

api-lint:
	cd backend && ruff check . --ignore F401,E501,E402,B017,BLE001,I001,RUF012,RUF100,S110

api-shell:
	cd backend && python manage.py shell

api-migrate:
	cd backend && python manage.py migrate

# ─── Web ───
web-dev:
	cd frontend && npm run dev

web-test:
	cd frontend && npx vitest run

web-lint:
	cd frontend && npm run lint

web-build:
	cd frontend && npm run build

# ─── CI local ───
ci: api-lint api-test web-lint web-test
	@echo "✅ All CI checks passed"
