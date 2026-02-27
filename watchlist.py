import json
import logging
import os
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

WATCHLIST_PATH = os.path.join("data", "watchlist.json")
_lock = threading.Lock()


def _ensure_data_dir():
    os.makedirs("data", exist_ok=True)


def _new_entry(
    name: str,
    foil: bool,
    threshold_eur: float,
    blueprint_ids: list[int],
    added_by: str | None = None,
) -> dict:
    return {
        "name": name,
        "foil": foil,
        "threshold_eur": threshold_eur,
        "blueprint_ids": blueprint_ids,
        "last_price_cents": None,
        "last_price_currency": None,
        "last_condition": None,
        "last_language": None,
        "last_seller": None,
        "last_seller_country": None,
        "last_set": None,
        "last_checked": None,
        "last_alerted": None,
        "added_by": added_by,
    }


def load() -> list[dict]:
    with _lock:
        _ensure_data_dir()
        if not os.path.exists(WATCHLIST_PATH):
            return []
        try:
            with open(WATCHLIST_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.exception("Failed to load watchlist")
            return []


def save(entries: list[dict]) -> None:
    with _lock:
        _ensure_data_dir()
        with open(WATCHLIST_PATH, "w") as f:
            json.dump(entries, f, indent=2)
        logger.info("Saved watchlist with %d entries", len(entries))


def add_card(
    name: str,
    foil: bool,
    threshold_eur: float,
    blueprint_ids: list[int],
    added_by: str | None = None,
) -> dict:
    entries = load()
    existing = find_card_in(entries, name, foil)
    if existing is not None:
        existing["threshold_eur"] = threshold_eur
        existing["blueprint_ids"] = blueprint_ids
        save(entries)
        return existing

    entry = _new_entry(name, foil, threshold_eur, blueprint_ids, added_by)
    entries.append(entry)
    save(entries)
    return entry


def remove_card(name: str, foil: bool) -> bool:
    entries = load()
    lower_name = name.lower()
    new_entries = [
        e for e in entries
        if not (e["name"].lower() == lower_name and e["foil"] == foil)
    ]
    if len(new_entries) == len(entries):
        return False
    save(new_entries)
    return True


def get_all() -> list[dict]:
    return load()


def find_card(name: str, foil: bool) -> dict | None:
    return find_card_in(load(), name, foil)


def find_card_in(entries: list[dict], name: str, foil: bool) -> dict | None:
    lower_name = name.lower()
    for e in entries:
        if e["name"].lower() == lower_name and e["foil"] == foil:
            return e
    return None


def update_card_price(
    name: str,
    foil: bool,
    price_cents: int,
    currency: str,
    condition: str,
    language: str,
    seller: str,
    seller_country: str,
    set_name: str,
) -> None:
    entries = load()
    entry = find_card_in(entries, name, foil)
    if entry is None:
        return
    entry["last_price_cents"] = price_cents
    entry["last_price_currency"] = currency
    entry["last_condition"] = condition
    entry["last_language"] = language
    entry["last_seller"] = seller
    entry["last_seller_country"] = seller_country
    entry["last_set"] = set_name
    entry["last_checked"] = datetime.now(timezone.utc).isoformat()
    save(entries)


def mark_alerted(name: str, foil: bool) -> None:
    entries = load()
    entry = find_card_in(entries, name, foil)
    if entry is None:
        return
    entry["last_alerted"] = datetime.now(timezone.utc).isoformat()
    save(entries)
