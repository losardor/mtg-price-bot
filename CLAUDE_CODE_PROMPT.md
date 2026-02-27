# Claude Code Prompt — MTG CardTrader Price Alert Bot

Build a complete Python Telegram bot in this directory (`~/Developer/mtg-price-bot/`) that monitors Magic: The Gathering card prices on CardTrader.com and sends alerts when cards drop below user-defined thresholds. The bot runs as a long-lived process, checking prices hourly, and works in Telegram group chats.

## File Structure

```
mtg-price-bot/
├── bot.py                 # Main entry point: Telegram bot + scheduler
├── cardtrader.py          # CardTrader API client
├── scryfall.py            # Scryfall API client for card name → blueprint resolution
├── config.py              # Configuration loading (env vars)
├── watchlist.py           # Watchlist management (CRUD, persistence to data/watchlist.json)
├── price_checker.py       # Price checking logic + filtering
├── alerts.py              # Alert formatting and cooldown logic
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── data/                  # Mounted volume for persistent data
│   └── .gitkeep
└── README.md
```

## Dependencies (requirements.txt)

```
python-telegram-bot>=20.0
requests
apscheduler
python-dotenv
```

## Configuration (config.py)

Load from `.env` via python-dotenv:

```
CARDTRADER_API_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (int),
CHECK_INTERVAL_HOURS (default 1), ALERT_COOLDOWN_HOURS (default 24)
```

Also define constants:
- `CARDTRADER_BASE_URL = "https://api.cardtrader.com/api/v2"`
- `SCRYFALL_BASE_URL = "https://api.scryfall.com"`
- `MTG_GAME_ID = 1`

## CardTrader API Client (cardtrader.py)

Auth: `Authorization: Bearer <TOKEN>` header on every request.

### Methods needed:

1. **`get_expansions()`** → fetch `GET /expansions`, filter by `game_id=1`, return list. Cache in memory, refresh weekly.

2. **`get_blueprints(expansion_id)`** → `GET /blueprints/export?expansion_id=<id>`, returns all blueprints in an expansion. Each has `id`, `name`, `scryfall_id`.

3. **`get_marketplace_products(blueprint_id, language)`** → `GET /marketplace/products?blueprint_id=<id>&language=<lang>`. Returns cheapest 25 products. Call this twice per blueprint (once `language=en`, once `language=it`) and merge results.

Each product has:
- `price.cents`, `price.currency`
- `properties_hash.condition` ("Near Mint", "Slightly Played", etc.)
- `properties_hash.mtg_language` ("en", "it")
- `properties_hash.mtg_foil` (boolean)
- `user.username`, `user.country_code`
- `on_vacation` (skip these)
- `expansion.name_en`, `expansion.code`

**Error handling**: Retry with exponential backoff on 429/5xx (max 3 retries). Add ~150ms delay between calls.

## Scryfall Client (scryfall.py)

No auth needed. Rate limit: 10 req/sec (add ~100ms delay between calls).

### Methods:

1. **`search_card(name)`** → `GET /cards/search?q=!"<exact card name>"&unique=prints`
   Returns all printings. Each has `id` (= scryfall_id) and `set` code. Handle pagination if `has_more` is true.

## Card Resolution Strategy (used when `/add`ing a card)

1. Search Scryfall for all printings of the card name
2. Map Scryfall `set` codes → CardTrader `expansion_id` using the cached expansion list (match on `code` field)
3. For each matching expansion, fetch blueprints via `GET /blueprints/export?expansion_id=<id>`, match by `scryfall_id`
4. Collect all matching `blueprint_id`s and store them in the watchlist entry

## Watchlist (watchlist.py)

Persist to `data/watchlist.json`. Thread-safe read/write with file locking or similar.

### Data model per entry:

```python
{
    "name": str,                    # Card name
    "foil": bool,                   # False = non-foil
    "threshold_eur": float,         # e.g. 45.00
    "blueprint_ids": list[int],     # Resolved CardTrader blueprint IDs
    "last_price_cents": int | None,
    "last_price_currency": str | None,
    "last_condition": str | None,
    "last_language": str | None,
    "last_seller": str | None,
    "last_seller_country": str | None,
    "last_set": str | None,
    "last_checked": str | None,     # ISO datetime
    "last_alerted": str | None,     # ISO datetime
    "added_by": str | None          # Telegram username
}
```

### CRUD methods:
- `load()`, `save()`, `add_card(...)`, `remove_card(name, foil)`, `get_all()`, `find_card(name, foil)`, `update_card_price(...)`

## Price Checker (price_checker.py)

### Filtering logic:

```python
def is_acceptable(product, want_foil: bool) -> bool:
    props = product["properties_hash"]
    condition_ok = props.get("condition") in ("Near Mint", "Slightly Played")
    language_ok = props.get("mtg_language") in ("en", "it")
    foil_ok = props.get("mtg_foil", False) == want_foil
    available = not product.get("on_vacation", False)
    return condition_ok and language_ok and foil_ok and available
```

### `check_card_price(card_entry)`:
- For each `blueprint_id` in the entry, call marketplace for EN and IT
- Filter with `is_acceptable`, collect all acceptable products
- Return the one with lowest `price.cents`, or None

### `check_all_prices(watchlist)`:
- Iterate all entries, call `check_card_price` for each
- Add ~150ms delay between API calls to be polite
- Return list of (entry, cheapest_product) tuples

## Alerts (alerts.py)

### `format_alert(card_entry, product)` → str:

```
🚨 Price Alert: Ragavan, Nimble Pilferer

💰 €42.00 (threshold: €45.00)
📦 Near Mint · English
🏪 CardShopPro (IT)
🃏 Modern Horizons 2
```

If foil, append " ⭐ FOIL" to the card name line.

### `format_price_report(card_entry, product)` → str:
Similar but without the 🚨, used for `/check` responses.

### `format_watchlist(entries)` → str:
```
📋 Watchlist (3 cards)

1. Ragavan, Nimble Pilferer — threshold €45.00 — last: €42.00 ✅
2. Ragavan, Nimble Pilferer ⭐ FOIL — threshold €120.00 — last: €135.00
3. The One Ring — threshold €60.00 — last: €58.50 ✅

✅ = currently below threshold
```

### Cooldown logic:
`should_alert(card_entry, new_price_cents)` → bool
- True if never alerted before
- True if `last_alerted` is older than `ALERT_COOLDOWN_HOURS`
- True if `new_price_cents < last_price_cents` (price dropped further)
- False otherwise

## Bot (bot.py)

Use `python-telegram-bot` v20+ (async). Use `APScheduler` for the hourly job.

### Commands:

| Command | Handler |
|---------|---------|
| `/help` | Show command list |
| `/add <card name> <threshold> [foil]` | Resolve via Scryfall→CardTrader, add to watchlist. Reply with confirmation or error. |
| `/remove <card name> [foil]` | Remove from watchlist. Reply with confirmation. |
| `/list` | Show formatted watchlist |
| `/check` | Run price check for ALL cards, reply with report for each |
| `/check <card name>` | Check specific card (both foil/non-foil if both watched) |

### Parsing `/add`:
The card name can contain spaces and commas. The threshold is the last numeric token. If the very last token is "foil", it's a foil entry. Examples:
- `/add Ragavan, Nimble Pilferer 45` → name="Ragavan, Nimble Pilferer", threshold=45.0, foil=False
- `/add Ragavan, Nimble Pilferer 120 foil` → name="Ragavan, Nimble Pilferer", threshold=120.0, foil=True
- `/add The One Ring 60` → name="The One Ring", threshold=60.0, foil=False

### Scheduled job:
Every `CHECK_INTERVAL_HOURS`, run full price check. For any card below threshold where `should_alert()` is True, send alert to `TELEGRAM_CHAT_ID`. Update all entries with latest price info and save.

### Startup:
1. Load watchlist from disk
2. Fetch & cache CardTrader expansions
3. Register Telegram command handlers
4. Start APScheduler
5. Start Telegram polling

## Docker

### Dockerfile:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

### docker-compose.yml:
```yaml
version: "3.8"
services:
  mtg-bot:
    build: .
    container_name: mtg-price-bot
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./data:/app/data
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

### .env.example:
```
CARDTRADER_API_TOKEN=your_jwt_token_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_group_chat_id_here
CHECK_INTERVAL_HOURS=1
ALERT_COOLDOWN_HOURS=24
```

## Error Handling
- Retry API calls with exponential backoff on 429 or 5xx (max 3 retries)
- If CardTrader is down, log the error and skip the cycle — never crash
- If Scryfall can't find a card name, reply to the user immediately with an error
- If blueprint resolution finds zero matches, warn user but save the entry anyway
- Handle Telegram API errors gracefully
- All errors logged to stdout

## README.md
Write a brief README covering: what the bot does, how to set up tokens, how to deploy with Docker, and the available commands.

## Important implementation notes
- Use `async` throughout since python-telegram-bot v20 is async
- The APScheduler job that runs hourly should use `AsyncIOScheduler` and call an async function
- For the Scryfall search, handle the case where `has_more` is true and paginate
- The expansion cache should be a dict mapping `code` → `expansion_id` for fast lookups
- Make sure `data/` directory exists on startup (create if missing)
- Use `logging` module throughout, log to stdout
- All price display: convert cents to EUR with 2 decimal places (e.g., 4200 → €42.00)

Build all files now. Make sure the code is complete, correct, and ready to run.
