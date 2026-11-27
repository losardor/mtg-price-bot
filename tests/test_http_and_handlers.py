"""Regression tests for 2026-11-27 on makerfaire-nuc.

1. Scryfall answered 400 (rule generic_user_agent) because requests went out
   without User-Agent and Accept headers: every Scryfall and CardTrader call
   must carry both.
2. An edited /add was handled again, with update.message None: command
   handlers must ignore edited messages.
3. /marketplace/products returns {"<blueprint_id>": [products]}; the products
   were dropped, so /check and the hourly check never found an offer.
"""
from datetime import datetime, timezone

import responses
from telegram import Chat, Message, Update, User
from telegram.ext import ApplicationBuilder, CommandHandler

import bot
import cardtrader
import scryfall

SEARCH = "https://api.scryfall.com/cards/search"


@responses.activate
def test_scryfall_sends_user_agent_and_accept():
    responses.add(responses.GET, SEARCH, json={"data": [{"id": "x", "set": "c21"}], "has_more": False})
    scryfall.search_card("Sol Ring")
    sent = responses.calls[0].request.headers
    assert sent["Accept"] == "application/json"
    assert sent["User-Agent"].startswith("mtg-price-bot/")
    assert "python-requests" not in sent["User-Agent"]


@responses.activate
def test_scryfall_headers_on_every_page():
    responses.add(responses.GET, SEARCH,
                  json={"data": [{"id": "a"}], "has_more": True, "next_page": SEARCH + "?page=2"})
    responses.add(responses.GET, SEARCH + "?page=2", json={"data": [{"id": "b"}], "has_more": False})
    assert len(scryfall.search_card("Sol Ring")) == 2
    assert all(c.request.headers["Accept"] == "application/json" for c in responses.calls)


@responses.activate
def test_cardtrader_sends_user_agent_and_accept():
    url = "https://api.cardtrader.com/api/v2/expansions"
    responses.add(responses.GET, url, json=[])
    cardtrader._request_with_retry("GET", url)
    sent = responses.calls[0].request.headers
    assert sent["Accept"] == "application/json"
    assert sent["User-Agent"].startswith("mtg-price-bot/")
    assert sent["Authorization"].startswith("Bearer ")


def _update(edited: bool) -> Update:
    msg = Message(message_id=1, date=datetime.now(timezone.utc),
                  chat=Chat(id=1, type="private"), from_user=User(id=1, first_name="T", is_bot=False),
                  text="/add Sol Ring 1")
    return Update(update_id=1, edited_message=msg) if edited else Update(update_id=1, message=msg)


def test_command_handlers_ignore_edited_messages():
    app = ApplicationBuilder().token("123456:TEST").build()
    bot.register_handlers(app)
    handlers = [h for h in app.handlers[0] if isinstance(h, CommandHandler)]
    assert {c for h in handlers for c in h.commands} == set(bot.COMMANDS)
    for h in handlers:
        assert h.filters.check_update(_update(edited=False))
        assert not h.filters.check_update(_update(edited=True))


@responses.activate
def test_marketplace_products_keyed_by_blueprint():
    """Live shape: {"<blueprint_id>": [products]}; before the fix only the key was kept."""
    url = "https://api.cardtrader.com/api/v2/marketplace/products"
    responses.add(responses.GET, url, json={"4459": [{"id": 1, "price": {"cents": 131}},
                                                    {"id": 2, "price": {"cents": 150}}]})
    responses.add(responses.GET, url, json={"4459": [{"id": 3, "price": {"cents": 99}}]})
    products = cardtrader.get_marketplace_products(4459)
    assert [p["id"] for p in products] == [1, 2, 3]


def test_check_finds_offer_from_keyed_payload(monkeypatch):
    import price_checker
    payload = {"4459": [{"id": 7, "price": {"cents": 131, "currency": "EUR"},
                         "properties_hash": {"condition": "Near Mint", "mtg_language": "en",
                                             "mtg_foil": False}}]}
    monkeypatch.setattr(price_checker, "get_marketplace_products",
                        lambda bp: cardtrader._products_from_payload(payload))
    cheapest = price_checker.check_card_price({"blueprint_ids": [4459], "foil": False})
    assert cheapest["id"] == 7
