.PHONY: up down logs migrate sh test seed site

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose exec backend python manage.py migrate

sh:
	docker compose exec backend bash

test:
	docker compose exec backend python manage.py test

seed:
	docker compose exec backend python manage.py seed_demo

exec:
	docker compose exec backend python manage.py shell

site:
	docker compose --profile site up --build site
