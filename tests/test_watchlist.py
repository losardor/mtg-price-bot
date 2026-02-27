import json

import pytest
import watchlist


class TestAddCard:
    def test_add_card_creates_entry(self, tmp_watchlist):
        entry = watchlist.add_card("Ragavan, Nimble Pilferer", False, 45.0, [500, 501], "tester")
        assert entry["name"] == "Ragavan, Nimble Pilferer"
        assert entry["foil"] is False
        assert entry["threshold_eur"] == 45.0
        assert entry["blueprint_ids"] == [500, 501]
        assert entry["added_by"] == "tester"
        assert entry["last_price_cents"] is None
        assert entry["last_alerted"] is None

    def test_add_card_same_name_foil_updates(self, tmp_watchlist):
        watchlist.add_card("Ragavan, Nimble Pilferer", False, 45.0, [500], "tester")
        updated = watchlist.add_card("Ragavan, Nimble Pilferer", False, 60.0, [500, 501])
        assert updated["threshold_eur"] == 60.0
        assert updated["blueprint_ids"] == [500, 501]
        # Should not duplicate
        entries = watchlist.get_all()
        assert len(entries) == 1

    def test_add_card_foil_and_nonfoil_separate(self, tmp_watchlist):
        watchlist.add_card("Lightning Bolt", False, 5.0, [100])
        watchlist.add_card("Lightning Bolt", True, 10.0, [100])
        entries = watchlist.get_all()
        assert len(entries) == 2


class TestRemoveCard:
    def test_remove_existing(self, tmp_watchlist):
        watchlist.add_card("Ragavan, Nimble Pilferer", False, 45.0, [500])
        assert watchlist.remove_card("Ragavan, Nimble Pilferer", False) is True
        assert watchlist.get_all() == []

    def test_remove_nonexistent(self, tmp_watchlist):
        assert watchlist.remove_card("Nonexistent Card", False) is False


class TestGetAll:
    def test_empty_watchlist(self, tmp_watchlist):
        assert watchlist.get_all() == []

    def test_after_adds(self, tmp_watchlist):
        watchlist.add_card("Card A", False, 10.0, [1])
        watchlist.add_card("Card B", False, 20.0, [2])
        watchlist.add_card("Card C", True, 30.0, [3])
        entries = watchlist.get_all()
        assert len(entries) == 3


class TestCaseInsensitive:
    def test_find_case_insensitive(self, tmp_watchlist):
        watchlist.add_card("Ragavan, Nimble Pilferer", False, 45.0, [500])
        found = watchlist.find_card("ragavan, nimble pilferer", False)
        assert found is not None
        assert found["name"] == "Ragavan, Nimble Pilferer"

    def test_remove_case_insensitive(self, tmp_watchlist):
        watchlist.add_card("Ragavan, Nimble Pilferer", False, 45.0, [500])
        assert watchlist.remove_card("ragavan, nimble pilferer", False) is True
        assert watchlist.get_all() == []


class TestUpdateCardPrice:
    def test_updates_all_fields(self, tmp_watchlist):
        watchlist.add_card("Test Card", False, 10.0, [100])
        watchlist.update_card_price(
            name="Test Card",
            foil=False,
            price_cents=850,
            currency="EUR",
            condition="Near Mint",
            language="en",
            seller="seller_a",
            seller_country="IT",
            set_name="Modern Horizons 2",
        )
        entry = watchlist.find_card("Test Card", False)
        assert entry["last_price_cents"] == 850
        assert entry["last_price_currency"] == "EUR"
        assert entry["last_condition"] == "Near Mint"
        assert entry["last_language"] == "en"
        assert entry["last_seller"] == "seller_a"
        assert entry["last_seller_country"] == "IT"
        assert entry["last_set"] == "Modern Horizons 2"
        assert entry["last_checked"] is not None


class TestMarkAlerted:
    def test_sets_last_alerted(self, tmp_watchlist):
        watchlist.add_card("Test Card", False, 10.0, [100])
        watchlist.mark_alerted("Test Card", False)
        entry = watchlist.find_card("Test Card", False)
        assert entry["last_alerted"] is not None


class TestPersistence:
    def test_data_survives_save_load(self, tmp_watchlist):
        watchlist.add_card("Card A", False, 10.0, [1, 2])
        watchlist.add_card("Card B", True, 20.0, [3])

        # Verify by reading raw JSON
        with open(tmp_watchlist) as f:
            raw_data = json.load(f)
        assert len(raw_data) == 2

        # Re-load via watchlist module
        reloaded = watchlist.load()
        assert len(reloaded) == 2
        assert reloaded[0]["name"] == "Card A"
        assert reloaded[0]["blueprint_ids"] == [1, 2]
        assert reloaded[1]["name"] == "Card B"
        assert reloaded[1]["foil"] is True
