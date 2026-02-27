# MTG CardTrader Price Alert Bot

A Telegram bot that monitors Magic: The Gathering card prices on CardTrader.com and sends alerts when cards drop below user-defined thresholds.

## Features

- Watch any MTG card with a price threshold (foil/non-foil)
- Automatic hourly price checks with Telegram alerts
- Searches across all printings via Scryfall
- Filters for Near Mint / Slightly Played, English / Italian listings
- Cooldown logic to avoid alert spam

## Setup

### 1. Get API tokens

- **CardTrader**: Sign up at [cardtrader.com](https://www.cardtrader.com), go to Account Settings > API, and generate a JWT token.
- **Telegram Bot**: Message [@BotFather](https://t.me/BotFather) on Telegram to create a bot and get the token.
- **Telegram Chat ID**: Add the bot to your group, send a message, then use the Telegram Bot API to get the chat ID (`https://api.telegram.org/bot<TOKEN>/getUpdates`).

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your actual tokens
```

### 3. Deploy with Docker

```bash
docker compose up -d --build
```

The bot will start polling for commands and checking prices every hour.

### Run without Docker

```bash
pip install -r requirements.txt
python bot.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/add <card name> <threshold> [foil]` | Add a card to the watchlist |
| `/remove <card name> [foil]` | Remove a card from the watchlist |
| `/list` | Show the current watchlist |
| `/check` | Check prices for all watched cards |
| `/check <card name>` | Check price for a specific card |

### Examples

```
/add Ragavan, Nimble Pilferer 45
/add The One Ring 60
/add Ragavan, Nimble Pilferer 120 foil
/remove The One Ring
/check Ragavan, Nimble Pilferer
```

## Data

Watchlist data is persisted to `data/watchlist.json`. When using Docker, this directory is mounted as a volume so data survives container restarts.
