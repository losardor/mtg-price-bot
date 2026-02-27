import responses
import requests
import pytest

import cardtrader

BASE_URL = "https://api.cardtrader.com/api/v2"


@pytest.fixture(autouse=True)
def reset_cache(monkeypatch):
    """Reset the expansion cache before each test."""
    monkeypatch.setattr(cardtrader, "_expansion_cache", {})
    monkeypatch.setattr(cardtrader, "_expansion_cache_time", None)
    # Disable rate limiting for tests
    monkeypatch.setattr(cardtrader, "_rate_limit", lambda: None)


class TestGetExpansions:
    @responses.activate
    def test_returns_mtg_expansions(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/expansions",
            json=[
                {"id": 100, "game_id": 1, "code": "MH2"},
                {"id": 200, "game_id": 1, "code": "LTR"},
                {"id": 300, "game_id": 2, "code": "FAB01"},  # Not MTG
                {"id": 400, "game_id": 1, "code": ""},  # Empty code, should skip
            ],
            status=200,
        )
        result = cardtrader.get_expansions()
        assert "mh2" in result
        assert "ltr" in result
        assert "fab01" not in result  # Different game
        assert result["mh2"] == 100
        assert result["ltr"] == 200

    @responses.activate
    def test_caching_only_one_request(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/expansions",
            json=[{"id": 100, "game_id": 1, "code": "MH2"}],
            status=200,
        )
        result1 = cardtrader.get_expansions()
        result2 = cardtrader.get_expansions()
        assert result1 == result2
        assert len(responses.calls) == 1  # Only one HTTP request


class TestGetBlueprints:
    @responses.activate
    def test_returns_blueprints(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/blueprints/export",
            json=[
                {"id": 1, "scryfall_id": "aaa", "name": "Card A"},
                {"id": 2, "scryfall_id": "bbb", "name": "Card B"},
            ],
            status=200,
        )
        result = cardtrader.get_blueprints(100)
        assert len(result) == 2
        assert result[0]["id"] == 1


class TestGetMarketplaceProducts:
    @responses.activate
    def test_merges_en_and_it(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/marketplace/products",
            json=[{"id": 1, "language": "en"}],
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/marketplace/products",
            json=[{"id": 2, "language": "it"}],
            status=200,
        )
        result = cardtrader.get_marketplace_products(500)
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2


class TestResolveBlueprintIds:
    @responses.activate
    def test_maps_scryfall_ids(self):
        # Mock expansions
        responses.add(
            responses.GET,
            f"{BASE_URL}/expansions",
            json=[
                {"id": 100, "game_id": 1, "code": "MH2"},
                {"id": 200, "game_id": 1, "code": "2X2"},
            ],
            status=200,
        )
        # Mock blueprints for MH2
        responses.add(
            responses.GET,
            f"{BASE_URL}/blueprints/export",
            json=[
                {"id": 1001, "scryfall_id": "aaa", "name": "Ragavan"},
                {"id": 1002, "scryfall_id": "zzz", "name": "Other"},
            ],
            status=200,
        )
        # Mock blueprints for 2X2
        responses.add(
            responses.GET,
            f"{BASE_URL}/blueprints/export",
            json=[
                {"id": 2001, "scryfall_id": "bbb", "name": "Ragavan"},
            ],
            status=200,
        )

        printings = [
            {"id": "aaa", "set": "mh2"},
            {"id": "bbb", "set": "2x2"},
        ]
        result = cardtrader.resolve_blueprint_ids("Ragavan", printings)
        assert 1001 in result
        assert 2001 in result
        assert 1002 not in result

    @responses.activate
    def test_skips_unknown_set_codes(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/expansions",
            json=[{"id": 100, "game_id": 1, "code": "MH2"}],
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/blueprints/export",
            json=[{"id": 1001, "scryfall_id": "aaa", "name": "Card"}],
            status=200,
        )

        printings = [
            {"id": "aaa", "set": "mh2"},
            {"id": "bbb", "set": "xyz_unknown"},  # Not in CardTrader
        ]
        result = cardtrader.resolve_blueprint_ids("Card", printings)
        assert 1001 in result
        # Should not error, just skip unknown


class TestRetryLogic:
    @responses.activate
    def test_retries_on_429_then_succeeds(self, monkeypatch):
        # Disable sleep during retry
        import time
        monkeypatch.setattr(time, "sleep", lambda s: None)

        responses.add(
            responses.GET,
            f"{BASE_URL}/expansions",
            json={"error": "rate limited"},
            status=429,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/expansions",
            json=[{"id": 100, "game_id": 1, "code": "MH2"}],
            status=200,
        )
        result = cardtrader.get_expansions()
        assert "mh2" in result
        assert len(responses.calls) == 2

    @responses.activate
    def test_fails_after_max_retries(self, monkeypatch):
        import time
        monkeypatch.setattr(time, "sleep", lambda s: None)

        for _ in range(4):  # max_retries=3, so 4 total attempts
            responses.add(
                responses.GET,
                f"{BASE_URL}/expansions",
                json={"error": "server error"},
                status=500,
            )
        # 4th attempt also returns 500, should raise
        with pytest.raises(requests.exceptions.HTTPError):
            cardtrader.get_expansions()
