"""Regression tests for 2026-11-27 on makerfaire-nuc.

1. Scryfall answered 400 (rule generic_user_agent) because requests went out
   without User-Agent and Accept headers: every Scryfall and CardTrader call
   must carry both.
2. An edited /add was handled again, with update.message None: command
   handlers must ignore edited messages.
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
