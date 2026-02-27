import responses
from scryfall import search_card


SCRYFALL_SEARCH_URL = "https://api.scryfall.com/cards/search"


class TestSearchCard:
    @responses.activate
    def test_successful_search_multiple_printings(self):
        responses.add(
            responses.GET,
            SCRYFALL_SEARCH_URL,
            json={
                "data": [
                    {"id": "aaa", "set": "mh2", "name": "Ragavan, Nimble Pilferer"},
                    {"id": "bbb", "set": "2x2", "name": "Ragavan, Nimble Pilferer"},
                    {"id": "ccc", "set": "mul", "name": "Ragavan, Nimble Pilferer"},
                ],
                "has_more": False,
            },
            status=200,
        )
        results = search_card("Ragavan, Nimble Pilferer")
        assert len(results) == 3
        assert results[0]["id"] == "aaa"
        assert results[1]["set"] == "2x2"
        assert results[2]["id"] == "ccc"

    @responses.activate
    def test_paginated_response(self):
        page2_url = "https://api.scryfall.com/cards/search?page=2"
        responses.add(
            responses.GET,
            SCRYFALL_SEARCH_URL,
            json={
                "data": [
                    {"id": "aaa", "set": "mh2", "name": "Lightning Bolt"},
                    {"id": "bbb", "set": "m21", "name": "Lightning Bolt"},
                ],
                "has_more": True,
                "next_page": page2_url,
            },
            status=200,
        )
        responses.add(
            responses.GET,
            page2_url,
            json={
                "data": [
                    {"id": "ccc", "set": "sta", "name": "Lightning Bolt"},
                ],
                "has_more": False,
            },
            status=200,
        )
        results = search_card("Lightning Bolt")
        assert len(results) == 3
        assert [r["id"] for r in results] == ["aaa", "bbb", "ccc"]

    @responses.activate
    def test_404_returns_empty(self):
        responses.add(
            responses.GET,
            SCRYFALL_SEARCH_URL,
            json={"object": "error", "code": "not_found"},
            status=404,
        )
        results = search_card("Nonexistent Card XYZZY")
        assert results == []

    @responses.activate
    def test_successful_call_works(self):
        """Verify that a normal call succeeds (rate limiting doesn't break things)."""
        responses.add(
            responses.GET,
            SCRYFALL_SEARCH_URL,
            json={
                "data": [{"id": "aaa", "set": "mh2", "name": "Sol Ring"}],
                "has_more": False,
            },
            status=200,
        )
        results = search_card("Sol Ring")
        assert len(results) == 1
