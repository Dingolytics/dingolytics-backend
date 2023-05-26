.PHONY: build up initdb migrate redis-cli shell test test-clean

COMPOSE_CMD := docker compose

TEST_COMPOSE_CMD := docker compose -f docker-compose.tests.yml

build:
	$(COMPOSE_CMD) build

initdb:
	$(COMPOSE_CMD) run --rm server manage database create-tables

up: initdb
	$(COMPOSE_CMD) up

migrate:
	$(COMPOSE_CMD) run --rm server manage db migrate

redis-cli:
	$(COMPOSE_CMD) run --rm redis redis-cli -h redis

shell:
	$(COMPOSE_CMD) run --rm server bash

test:
	$(TEST_COMPOSE_CMD) build
	$(TEST_COMPOSE_CMD) run --rm server-tests

test-clean:
	$(TEST_COMPOSE_CMD) stop
	$(TEST_COMPOSE_CMD) down --volumes
