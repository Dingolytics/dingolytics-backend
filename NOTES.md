### Initialize fresh database

```bash
docker-compose run --rm server create_tables
```

### Run management shell in Docker container

```bash
docker-compose run --rm server bash
```

### Managing migrations

Create a new auto-migration:

```bash
flask --app redash db check
flask --app redash db migrate
```

### Run specific tests

```bash
docker compose -f docker-compose.tests.yml run --rm server-tests tests tests/handlers/test_streams.py
```