import logging
import time

from cardtrader import get_marketplace_products

logger = logging.getLogger(__name__)


def is_acceptable(product: dict, want_foil: bool) -> bool:
    props = product.get("properties_hash", {})
    condition_ok = props.get("condition") in ("Near Mint", "Slightly Played")
    language_ok = props.get("mtg_language") in ("en", "it")
    foil_ok = props.get("mtg_foil", False) == want_foil
    available = not product.get("on_vacation", False)
    return condition_ok and language_ok and foil_ok and available


def check_card_price(card_entry: dict) -> dict | None:
    """Check marketplace prices for a single card entry.

    Returns the cheapest acceptable product, or None.
    """
    blueprint_ids = card_entry.get("blueprint_ids", [])
    want_foil = card_entry.get("foil", False)
    all_acceptable = []

    for bp_id in blueprint_ids:
        try:
            products = get_marketplace_products(bp_id)
        except Exception:
            logger.exception("Failed to fetch products for blueprint %d", bp_id)
            continue

        for p in products:
            if is_acceptable(p, want_foil):
                all_acceptable.append(p)

    if not all_acceptable:
        return None

    cheapest = min(all_acceptable, key=lambda p: p.get("price", {}).get("cents", float("inf")))
    return cheapest


def check_all_prices(entries: list[dict]) -> list[tuple[dict, dict | None]]:
    """Check prices for all watchlist entries.

    Returns list of (entry, cheapest_product) tuples.
    """
    results = []
    for entry in entries:
        logger.info("Checking price for '%s'%s", entry["name"], " (foil)" if entry["foil"] else "")
        cheapest = check_card_price(entry)
        results.append((entry, cheapest))
        time.sleep(0.15)
    return results
