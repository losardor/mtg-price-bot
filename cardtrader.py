import logging
import time
from datetime import datetime, timezone

import requests

from config import CARDTRADER_API_TOKEN, CARDTRADER_BASE_URL, MTG_GAME_ID

logger = logging.getLogger(__name__)

_last_request_time = 0.0
_expansion_cache: dict[str, int] = {}  # code -> expansion_id
_expansion_cache_time: datetime | None = None
_CACHE_TTL_SECONDS = 7 * 24 * 3600  # 1 week


def _rate_limit():
    """Ensure at least 150ms between CardTrader requests."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < 0.15:
        time.sleep(0.15 - elapsed)
    _last_request_time = time.time()


def _headers() -> dict:
    return {"Authorization": f"Bearer {CARDTRADER_API_TOKEN}"}


def _request_with_retry(method: str, url: str, **kwargs) -> requests.Response:
    """Make an HTTP request with exponential backoff on 429/5xx."""
    max_retries = 3
    for attempt in range(max_retries + 1):
        _rate_limit()
        resp = requests.request(method, url, headers=_headers(), timeout=30, **kwargs)
        if resp.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
            wait = 2 ** attempt
            logger.warning(
                "CardTrader %s %s returned %d, retrying in %ds (attempt %d/%d)",
                method, url, resp.status_code, wait, attempt + 1, max_retries,
            )
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp
    return resp  # unreachable but keeps type checkers happy


def get_expansions() -> dict[str, int]:
    """Fetch MTG expansions from CardTrader, cached for one week.

    Returns dict mapping expansion code (lowercase) -> expansion_id.
    """
    global _expansion_cache, _expansion_cache_time

    now = datetime.now(timezone.utc)
    if _expansion_cache and _expansion_cache_time:
        age = (now - _expansion_cache_time).total_seconds()
        if age < _CACHE_TTL_SECONDS:
            return _expansion_cache

    logger.info("Fetching CardTrader expansions (MTG game_id=%d)", MTG_GAME_ID)
    url = f"{CARDTRADER_BASE_URL}/expansions"
    resp = _request_with_retry("GET", url)
    expansions = resp.json()

    cache = {}
    for exp in expansions:
        if exp.get("game_id") == MTG_GAME_ID:
            code = exp.get("code", "").lower()
            if code:
                cache[code] = exp["id"]

    _expansion_cache = cache
    _expansion_cache_time = now
    logger.info("Cached %d MTG expansions", len(cache))
    return _expansion_cache


def get_blueprints(expansion_id: int) -> list[dict]:
    """Fetch all blueprints for an expansion."""
    url = f"{CARDTRADER_BASE_URL}/blueprints/export"
    resp = _request_with_retry("GET", url, params={"expansion_id": expansion_id})
    return resp.json()


def get_marketplace_products(blueprint_id: int) -> list[dict]:
    """Fetch marketplace products for a blueprint (EN + IT), merged."""
    products = []
    url = f"{CARDTRADER_BASE_URL}/marketplace/products"

    for lang in ("en", "it"):
        resp = _request_with_retry("GET", url, params={
            "blueprint_id": blueprint_id,
            "language": lang,
        })
        products.extend(resp.json())

    return products


def resolve_blueprint_ids(card_name: str, scryfall_printings: list[dict]) -> list[int]:
    """Given Scryfall printings, resolve CardTrader blueprint IDs.

    Maps scryfall set codes -> CardTrader expansion IDs, fetches blueprints,
    and matches by scryfall_id.
    """
    expansions = get_expansions()
    scryfall_ids = {p["id"] for p in scryfall_printings}
    set_codes = {p["set"].lower() for p in scryfall_printings}

    blueprint_ids = []
    seen_expansion_ids = set()

    for code in set_codes:
        exp_id = expansions.get(code)
        if exp_id is None or exp_id in seen_expansion_ids:
            continue
        seen_expansion_ids.add(exp_id)

        try:
            blueprints = get_blueprints(exp_id)
        except Exception:
            logger.exception("Failed to fetch blueprints for expansion %s (id=%d)", code, exp_id)
            continue

        for bp in blueprints:
            if bp.get("scryfall_id") in scryfall_ids:
                blueprint_ids.append(bp["id"])

    logger.info("Resolved %d blueprint IDs for '%s'", len(blueprint_ids), card_name)
    return blueprint_ids
