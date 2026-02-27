import os
import pytest


# ---------------------------------------------------------------------------
# Sample CardTrader product dicts
# ---------------------------------------------------------------------------

@pytest.fixture
def product_nm_en():
    """Near Mint, English, non-foil, not on vacation."""
    return {
        "id": 1001,
        "blueprint_id": 500,
        "price": {"cents": 1200, "currency": "EUR"},
        "properties_hash": {
            "condition": "Near Mint",
            "mtg_language": "en",
            "mtg_foil": False,
        },
        "on_vacation": False,
        "user": {"username": "seller_a", "country_code": "IT"},
        "expansion": {"name_en": "Modern Horizons 2"},
    }


@pytest.fixture
def product_sp_it():
    """Slightly Played, Italian, non-foil, not on vacation."""
    return {
        "id": 1002,
        "blueprint_id": 500,
        "price": {"cents": 900, "currency": "EUR"},
        "properties_hash": {
            "condition": "Slightly Played",
            "mtg_language": "it",
            "mtg_foil": False,
        },
        "on_vacation": False,
        "user": {"username": "seller_b", "country_code": "DE"},
        "expansion": {"name_en": "Modern Horizons 2"},
    }


@pytest.fixture
def product_foil():
    """Near Mint, English, foil, not on vacation."""
    return {
        "id": 1003,
        "blueprint_id": 500,
        "price": {"cents": 3500, "currency": "EUR"},
        "properties_hash": {
            "condition": "Near Mint",
            "mtg_language": "en",
            "mtg_foil": True,
        },
        "on_vacation": False,
        "user": {"username": "seller_c", "country_code": "US"},
        "expansion": {"name_en": "The Lord of the Rings"},
    }


@pytest.fixture
def product_played():
    """Played condition (unacceptable)."""
    return {
        "id": 1004,
        "blueprint_id": 500,
        "price": {"cents": 500, "currency": "EUR"},
        "properties_hash": {
            "condition": "Played",
            "mtg_language": "en",
            "mtg_foil": False,
        },
        "on_vacation": False,
        "user": {"username": "seller_d", "country_code": "FR"},
        "expansion": {"name_en": "Modern Horizons 2"},
    }


@pytest.fixture
def product_german():
    """German language (unacceptable)."""
    return {
        "id": 1005,
        "blueprint_id": 500,
        "price": {"cents": 700, "currency": "EUR"},
        "properties_hash": {
            "condition": "Near Mint",
            "mtg_language": "de",
            "mtg_foil": False,
        },
        "on_vacation": False,
        "user": {"username": "seller_e", "country_code": "DE"},
        "expansion": {"name_en": "Modern Horizons 2"},
    }


@pytest.fixture
def product_vacation():
    """Seller on vacation (unacceptable)."""
    return {
        "id": 1006,
        "blueprint_id": 500,
        "price": {"cents": 800, "currency": "EUR"},
        "properties_hash": {
            "condition": "Near Mint",
            "mtg_language": "en",
            "mtg_foil": False,
        },
        "on_vacation": True,
        "user": {"username": "seller_f", "country_code": "ES"},
        "expansion": {"name_en": "Modern Horizons 2"},
    }


# ---------------------------------------------------------------------------
# Sample watchlist entries
# ---------------------------------------------------------------------------

@pytest.fixture
def watchlist_entry_basic():
    """Basic non-foil watchlist entry, never alerted."""
    return {
        "name": "Ragavan, Nimble Pilferer",
        "foil": False,
        "threshold_eur": 45.0,
        "blueprint_ids": [500, 501],
        "last_price_cents": None,
        "last_price_currency": None,
        "last_condition": None,
        "last_language": None,
        "last_seller": None,
        "last_seller_country": None,
        "last_set": None,
        "last_checked": None,
        "last_alerted": None,
        "added_by": "testuser",
    }


@pytest.fixture
def watchlist_entry_foil():
    """Foil watchlist entry with last_alerted set."""
    return {
        "name": "The One Ring",
        "foil": True,
        "threshold_eur": 120.0,
        "blueprint_ids": [600],
        "last_price_cents": 11000,
        "last_price_currency": "EUR",
        "last_condition": "Near Mint",
        "last_language": "en",
        "last_seller": "seller_x",
        "last_seller_country": "IT",
        "last_set": "The Lord of the Rings",
        "last_checked": "2025-01-01T12:00:00+00:00",
        "last_alerted": "2025-01-01T10:00:00+00:00",
        "added_by": "testuser",
    }


# ---------------------------------------------------------------------------
# Tmp watchlist fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_watchlist(tmp_path, monkeypatch):
    """Monkeypatch watchlist.WATCHLIST_PATH to a temp directory."""
    import watchlist
    watchlist_file = str(tmp_path / "watchlist.json")
    monkeypatch.setattr(watchlist, "WATCHLIST_PATH", watchlist_file)
    # Also patch _ensure_data_dir to be a no-op since tmp_path already exists
    monkeypatch.setattr(watchlist, "_ensure_data_dir", lambda: None)
    return watchlist_file
