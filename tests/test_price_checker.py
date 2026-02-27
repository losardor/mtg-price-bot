import pytest
from price_checker import check_card_price, check_all_prices


def _make_product(pid, cents, condition="Near Mint", language="en", foil=False, vacation=False):
    return {
        "id": pid,
        "blueprint_id": 500,
        "price": {"cents": cents, "currency": "EUR"},
        "properties_hash": {
            "condition": condition,
            "mtg_language": language,
            "mtg_foil": foil,
        },
        "on_vacation": vacation,
        "user": {"username": f"seller_{pid}", "country_code": "IT"},
        "expansion": {"name_en": "Test Set"},
    }


class TestCheckCardPrice:
    def test_returns_cheapest_acceptable(self, monkeypatch):
        products = [
            _make_product(1, 2000),                          # acceptable, €20
            _make_product(2, 1500),                          # acceptable, €15 (cheapest)
            _make_product(3, 500, condition="Played"),        # unacceptable
            _make_product(4, 1000, vacation=True),            # unacceptable
            _make_product(5, 1800),                          # acceptable, €18
        ]
        monkeypatch.setattr(
            "price_checker.get_marketplace_products",
            lambda bp_id: products,
        )
        entry = {
            "name": "Test Card",
            "foil": False,
            "blueprint_ids": [500],
        }
        result = check_card_price(entry)
        assert result is not None
        assert result["id"] == 2
        assert result["price"]["cents"] == 1500

    def test_no_acceptable_products(self, monkeypatch):
        products = [
            _make_product(1, 500, condition="Played"),
            _make_product(2, 600, language="de"),
            _make_product(3, 700, vacation=True),
        ]
        monkeypatch.setattr(
            "price_checker.get_marketplace_products",
            lambda bp_id: products,
        )
        entry = {
            "name": "Test Card",
            "foil": False,
            "blueprint_ids": [500],
        }
        result = check_card_price(entry)
        assert result is None

    def test_multiple_blueprint_ids_picks_global_cheapest(self, monkeypatch):
        bp_products = {
            100: [_make_product(1, 2000)],   # €20
            200: [_make_product(2, 1200)],   # €12 (cheapest overall)
            300: [_make_product(3, 1800)],   # €18
        }
        monkeypatch.setattr(
            "price_checker.get_marketplace_products",
            lambda bp_id: bp_products[bp_id],
        )
        entry = {
            "name": "Test Card",
            "foil": False,
            "blueprint_ids": [100, 200, 300],
        }
        result = check_card_price(entry)
        assert result is not None
        assert result["id"] == 2

    def test_skips_non_dict_products(self, monkeypatch):
        """API may return strings instead of dicts; these should be skipped."""
        products = [
            "unexpected string",
            _make_product(1, 1500),
            42,
        ]
        monkeypatch.setattr(
            "price_checker.get_marketplace_products",
            lambda bp_id: products,
        )
        entry = {
            "name": "Test Card",
            "foil": False,
            "blueprint_ids": [500],
        }
        result = check_card_price(entry)
        assert result is not None
        assert result["id"] == 1
        assert result["price"]["cents"] == 1500

    def test_one_blueprint_fails_still_returns_others(self, monkeypatch):
        call_count = {"n": 0}

        def mock_get(bp_id):
            call_count["n"] += 1
            if bp_id == 100:
                raise ConnectionError("API down")
            return [_make_product(2, 1500)]

        monkeypatch.setattr(
            "price_checker.get_marketplace_products",
            mock_get,
        )
        entry = {
            "name": "Test Card",
            "foil": False,
            "blueprint_ids": [100, 200],
        }
        result = check_card_price(entry)
        assert result is not None
        assert result["id"] == 2


class TestCheckAllPrices:
    def test_returns_list_of_tuples(self, monkeypatch):
        monkeypatch.setattr(
            "price_checker.get_marketplace_products",
            lambda bp_id: [_make_product(1, 1000)],
        )
        # Disable sleep between checks
        import time
        monkeypatch.setattr(time, "sleep", lambda s: None)

        entries = [
            {"name": "Card A", "foil": False, "blueprint_ids": [100]},
            {"name": "Card B", "foil": False, "blueprint_ids": [200]},
        ]
        results = check_all_prices(entries)
        assert len(results) == 2
        assert results[0][0]["name"] == "Card A"
        assert results[0][1] is not None
        assert results[1][0]["name"] == "Card B"
