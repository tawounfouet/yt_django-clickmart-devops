.PHONY: up up-staging up-prod down logs ps clean

up:
	docker compose up -d --build

up-staging:
	docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d --build

up-prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=50

ps:
	docker compose ps

clean:
	docker compose down -v --remove-orphans
