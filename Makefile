.RECIPEPREFIX = >
.PHONY: up down logs migrate sh test seed

up:
> docker compose up --build

down:
> docker compose down

logs:
> docker compose logs -f

migrate:
> docker compose exec backend python manage.py migrate

sh:
> docker compose exec backend bash

test:
> docker compose exec backend python manage.py test

# placeholder until Phase 1 adds the seed command
seed:
> docker compose exec backend python manage.py seed_demo
