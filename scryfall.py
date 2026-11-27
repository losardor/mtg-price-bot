import logging
import time

import requests

from config import SCRYFALL_BASE_URL, USER_AGENT

logger = logging.getLogger(__name__)

_last_request_time = 0.0

# Scryfall requires both on every request; without them it answers 400.
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}


def _rate_limit():
    """Ensure at least 100ms between Scryfall requests."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < 0.1:
        time.sleep(0.1 - elapsed)
    _last_request_time = time.time()


def search_card(name: str) -> list[dict]:
    """Search Scryfall for all printings of an exact card name.

    Returns a list of card objects, each with at least 'id' (scryfall_id) and 'set'.
    """
    results = []
    url = f"{SCRYFALL_BASE_URL}/cards/search"
    params = {"q": f'!"{name}"', "unique": "prints"}

    while True:
        _rate_limit()
        logger.info("Scryfall search: %s params=%s", url, params)
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)

        if resp.status_code == 404:
            logger.warning("Scryfall found no results for '%s'", name)
            return []

        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("data", []))

        if data.get("has_more") and data.get("next_page"):
            url = data["next_page"]
            params = {}
        else:
            break

    logger.info("Scryfall returned %d printings for '%s'", len(results), name)
    return results
