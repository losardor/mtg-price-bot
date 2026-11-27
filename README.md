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

## Production: makerfaire-nuc

Runs on **makerfaire-nuc** (Sony CSL Rome LAN, user `makerfaire`) as a systemd user service, in its own venv on uv-managed Python 3.12, without Docker.

| | |
|---|---|
| Code | `~/bots/mtg-price-bot` (git clone; nothing is edited on the NUC) |
| Venv | `~/bots/mtg-price-bot/.venv` (Python 3.12, `uv`) |
| Config | `~/.config/tgbots/mtg-price-bot.env`, mode 600: `TELEGRAM_BOT_TOKEN`, `CARDTRADER_API_TOKEN`, `TELEGRAM_CHAT_ID`, `CHECK_INTERVAL_HOURS`, `ALERT_COOLDOWN_HOURS` |
| Watchlist | `~/.local/share/tgbots/mtg-price-bot/data/watchlist.json` (the service's working directory) |
| Service | `deploy/mtg-price-bot.service` → `systemctl --user {status,restart} mtg-price-bot` |
| Logs | `journalctl --user -u mtg-price-bot` (tokens redacted by [tgkit](https://github.com/losardor/tgkit)) |
| Alerts | a crash reaches Ruggiero through the monitor bot (`tgsignal-wrap -p mtg`) |

Without `~/.config/tgbots/mtg-price-bot.env`, for example on the Mac, `config.py` reads the repo `.env` as before. The tests use placeholder values and never read a real `.env` or env file. Run them with Docker (`docker compose run --rm test`) or in a Python 3.12 venv (`.venv/bin/pytest -q`).

Deploy after pushing: `ssh makerfaire@192.168.0.227 '~/bots/mtg-price-bot/deploy/deploy-nuc.sh'`.
