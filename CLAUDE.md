# MTG Price Bot

## Running tests

Always run tests inside the Docker container, never in the host Python environment.
The project uses Python 3.12 in Docker while the host may have a different version.

```bash
docker compose run --rm test
```

This uses the `test` service defined in `docker-compose.yml` (under the `test` profile).
To run a specific test file:

```bash
docker compose run --rm test tests/test_scheduler.py -v
```

The tests are hermetic (placeholder env in `tests/conftest.py`), so a Python 3.12 venv works too: on makerfaire-nuc, `~/bots/mtg-price-bot/.venv/bin/pytest -q`.
