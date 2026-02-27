from datetime import datetime, timedelta, timezone

import pytest
from alerts import format_alert, format_price_report, format_watchlist, should_alert


class TestFormatAlert:
    def test_basic_alert(self, watchlist_entry_basic, product_nm_en):
        result = format_alert(watchlist_entry_basic, product_nm_en)
        assert "Ragavan, Nimble Pilferer" in result
        assert "\u20ac12.00" in result  # price
        assert "\u20ac45.00" in result  # threshold
        assert "Near Mint" in result
        assert "seller_a" in result
        assert "Modern Horizons 2" in result

    def test_foil_alert(self, watchlist_entry_foil, product_foil):
        result = format_alert(watchlist_entry_foil, product_foil)
        assert "\u2b50 FOIL" in result
        assert "The One Ring" in result
        assert "\u20ac35.00" in result
        assert "The Lord of the Rings" in result


class TestFormatPriceReport:
    def test_basic_report(self, watchlist_entry_basic, product_nm_en):
        result = format_price_report(watchlist_entry_basic, product_nm_en)
        assert "Ragavan, Nimble Pilferer" in result
        assert "\u20ac12.00" in result
        assert "\u20ac45.00" in result
        assert "Near Mint" in result
        assert "seller_a" in result
        assert "Modern Horizons 2" in result

    def test_foil_report(self, watchlist_entry_foil, product_foil):
        result = format_price_report(watchlist_entry_foil, product_foil)
        assert "\u2b50 FOIL" in result


class TestFormatWatchlist:
    def test_empty_list(self):
        result = format_watchlist([])
        assert "empty" in result.lower()

    def test_multiple_entries(self, watchlist_entry_basic, watchlist_entry_foil):
        result = format_watchlist([watchlist_entry_basic, watchlist_entry_foil])
        assert "2 cards" in result
        assert "Ragavan, Nimble Pilferer" in result
        assert "The One Ring" in result

    def test_entry_without_last_price(self, watchlist_entry_basic):
        result = format_watchlist([watchlist_entry_basic])
        assert "1 card)" in result
        assert "last:" not in result

    def test_entry_with_last_price(self, watchlist_entry_foil):
        result = format_watchlist([watchlist_entry_foil])
        assert "last:" in result
        assert "\u20ac110.00" in result  # 11000 cents

    def test_entry_below_threshold_shows_checkmark(self):
        entry = {
            "name": "Test Card",
            "foil": False,
            "threshold_eur": 50.0,
            "last_price_cents": 4000,  # 40 EUR < 50 EUR threshold
        }
        result = format_watchlist([entry])
        assert "\u2705" in result


class TestShouldAlert:
    def test_price_above_threshold(self, watchlist_entry_basic):
        # threshold is 45 EUR = 4500 cents; price 5000 cents > threshold
        assert should_alert(watchlist_entry_basic, 5000) is False

    def test_price_below_threshold_never_alerted(self, watchlist_entry_basic):
        # last_alerted is None, price 3000 < 4500
        assert should_alert(watchlist_entry_basic, 3000) is True

    def test_price_below_threshold_alerted_long_ago(self):
        old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        entry = {
            "name": "Test",
            "foil": False,
            "threshold_eur": 50.0,
            "last_alerted": old_time,
            "last_price_cents": 4500,
        }
        assert should_alert(entry, 4000) is True

    def test_price_below_threshold_alerted_recently_same_price(self):
        recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        entry = {
            "name": "Test",
            "foil": False,
            "threshold_eur": 50.0,
            "last_alerted": recent,
            "last_price_cents": 4000,
        }
        # Same price as last_price_cents
        assert should_alert(entry, 4000) is False

    def test_price_below_threshold_alerted_recently_price_dropped(self):
        recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        entry = {
            "name": "Test",
            "foil": False,
            "threshold_eur": 50.0,
            "last_alerted": recent,
            "last_price_cents": 4000,
        }
        # Price dropped further: 3500 < 4000
        assert should_alert(entry, 3500) is True

    def test_last_alerted_none(self, watchlist_entry_basic):
        assert watchlist_entry_basic["last_alerted"] is None
        assert should_alert(watchlist_entry_basic, 3000) is True

    def test_last_alerted_malformed_string(self):
        entry = {
            "name": "Test",
            "foil": False,
            "threshold_eur": 50.0,
            "last_alerted": "not-a-date",
            "last_price_cents": None,
        }
        assert should_alert(entry, 4000) is True
