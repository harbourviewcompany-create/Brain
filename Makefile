.PHONY: test compile zip infra-up infra-down migrate health worker api neo4j-rebuild

test:
	pytest

compile:
	python -m compileall brain apps tests

zip:
	cd .. && zip -r brain-codebase.zip brain-codebase -x '*.pyc' -x '__pycache__/*'

infra-up:
	docker compose -f infra/docker-compose.yml up -d

infra-down:
	docker compose -f infra/docker-compose.yml down

migrate:
	python -m tools.apply_migrations

health:
	python scripts/infra_healthcheck.py

worker:
	python -m apps.worker.main

api:
	uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

neo4j-rebuild:
	python scripts/rebuild_neo4j_projection.py
