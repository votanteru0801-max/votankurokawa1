.PHONY: up down logs test lint typecheck migrate seed rich-menu-image rich-menu-json

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f app

test:
	docker compose exec app pytest

lint:
	docker compose exec app ruff check .

typecheck:
	docker compose exec app mypy app

migrate:
	docker compose exec app alembic upgrade head

seed:
	docker compose exec app python scripts/seed_mock_data.py

rich-menu-image:
	docker compose exec app python scripts/generate_rich_menu_image.py

rich-menu-json:
	docker compose exec app python scripts/export_rich_menu_json.py
