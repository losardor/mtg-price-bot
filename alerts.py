import logging
from datetime import datetime, timedelta, timezone

from config import ALERT_COOLDOWN_HOURS

logger = logging.getLogger(__name__)


def _cents_to_eur(cents: int) -> str:
    return f"\u20ac{cents / 100:.2f}"


def _language_display(lang_code: str) -> str:
    mapping = {"en": "English", "it": "Italian"}
    return mapping.get(lang_code, lang_code)


def format_alert(card_entry: dict, product: dict) -> str:
    props = product.get("properties_hash", {})
    price = product.get("price", {})
    user = product.get("user", {})
    expansion = product.get("expansion", {})

    name = card_entry["name"]
    if card_entry.get("foil"):
        name += " \u2b50 FOIL"

    price_str = _cents_to_eur(price.get("cents", 0))
    threshold_str = _cents_to_eur(int(card_entry["threshold_eur"] * 100))
    condition = props.get("condition", "Unknown")
    language = _language_display(props.get("mtg_language", ""))
    seller = user.get("username", "Unknown")
    country = user.get("country_code", "")
    set_name = expansion.get("name_en", "Unknown")

    return (
        f"\U0001f6a8 Price Alert: {name}\n"
        f"\n"
        f"\U0001f4b0 {price_str} (threshold: {threshold_str})\n"
        f"\U0001f4e6 {condition} \u00b7 {language}\n"
        f"\U0001f3ea {seller} ({country})\n"
        f"\U0001f0cf {set_name}"
    )


def format_price_report(card_entry: dict, product: dict) -> str:
    props = product.get("properties_hash", {})
    price = product.get("price", {})
    user = product.get("user", {})
    expansion = product.get("expansion", {})

    name = card_entry["name"]
    if card_entry.get("foil"):
        name += " \u2b50 FOIL"

    price_str = _cents_to_eur(price.get("cents", 0))
    threshold_str = _cents_to_eur(int(card_entry["threshold_eur"] * 100))
    condition = props.get("condition", "Unknown")
    language = _language_display(props.get("mtg_language", ""))
    seller = user.get("username", "Unknown")
    country = user.get("country_code", "")
    set_name = expansion.get("name_en", "Unknown")

    return (
        f"{name}\n"
        f"\n"
        f"\U0001f4b0 {price_str} (threshold: {threshold_str})\n"
        f"\U0001f4e6 {condition} \u00b7 {language}\n"
        f"\U0001f3ea {seller} ({country})\n"
        f"\U0001f0cf {set_name}"
    )


def format_watchlist(entries: list[dict]) -> str:
    if not entries:
        return "\U0001f4cb Watchlist is empty."

    lines = [f"\U0001f4cb Watchlist ({len(entries)} card{'s' if len(entries) != 1 else ''})"]
    lines.append("")

    for i, entry in enumerate(entries, 1):
        name = entry["name"]
        if entry.get("foil"):
            name += " \u2b50 FOIL"

        threshold_str = _cents_to_eur(int(entry["threshold_eur"] * 100))
        last_price = entry.get("last_price_cents")

        line = f"{i}. {name} \u2014 threshold {threshold_str}"
        if last_price is not None:
            last_str = _cents_to_eur(last_price)
            line += f" \u2014 last: {last_str}"
            if last_price <= int(entry["threshold_eur"] * 100):
                line += " \u2705"
        lines.append(line)

    lines.append("")
    lines.append("\u2705 = currently below threshold")
    return "\n".join(lines)


def should_alert(card_entry: dict, new_price_cents: int) -> bool:
    threshold_cents = int(card_entry["threshold_eur"] * 100)
    if new_price_cents > threshold_cents:
        return False

    last_alerted = card_entry.get("last_alerted")
    if last_alerted is None:
        return True

    try:
        alerted_dt = datetime.fromisoformat(last_alerted)
    except (ValueError, TypeError):
        return True

    now = datetime.now(timezone.utc)
    if now - alerted_dt > timedelta(hours=ALERT_COOLDOWN_HOURS):
        return True

    last_price = card_entry.get("last_price_cents")
    if last_price is not None and new_price_cents < last_price:
        return True

    return False
