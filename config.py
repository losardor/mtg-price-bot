import os
from dotenv import load_dotenv


def load_config() -> dict:
    """Load configuration from environment variables.

    Returns a dict with all config values.
    Raises KeyError for missing required vars, ValueError for invalid TELEGRAM_CHAT_ID.
    """
    load_dotenv()

    # Required
    try:
        cardtrader_api_token = os.environ["CARDTRADER_API_TOKEN"]
    except KeyError:
        raise KeyError("CARDTRADER_API_TOKEN")

    try:
        telegram_bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    except KeyError:
        raise KeyError("TELEGRAM_BOT_TOKEN")

    try:
        raw_chat_id = os.environ["TELEGRAM_CHAT_ID"]
    except KeyError:
        raise KeyError("TELEGRAM_CHAT_ID")

    try:
        telegram_chat_id = int(raw_chat_id)
    except ValueError:
        raise ValueError(
            f"TELEGRAM_CHAT_ID must be a valid integer, got: {raw_chat_id!r}"
        )

    # Optional with defaults
    check_interval_hours = int(os.getenv("CHECK_INTERVAL_HOURS", "1"))
    alert_cooldown_hours = int(os.getenv("ALERT_COOLDOWN_HOURS", "24"))

    return {
        "CARDTRADER_API_TOKEN": cardtrader_api_token,
        "TELEGRAM_BOT_TOKEN": telegram_bot_token,
        "TELEGRAM_CHAT_ID": telegram_chat_id,
        "CHECK_INTERVAL_HOURS": check_interval_hours,
        "ALERT_COOLDOWN_HOURS": alert_cooldown_hours,
        "CARDTRADER_BASE_URL": "https://api.cardtrader.com/api/v2",
        "SCRYFALL_BASE_URL": "https://api.scryfall.com",
        "MTG_GAME_ID": 1,
    }


# Module-level constants — kept for backward compatibility
_config = load_config()

CARDTRADER_API_TOKEN = _config["CARDTRADER_API_TOKEN"]
TELEGRAM_BOT_TOKEN = _config["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = _config["TELEGRAM_CHAT_ID"]
CHECK_INTERVAL_HOURS = _config["CHECK_INTERVAL_HOURS"]
ALERT_COOLDOWN_HOURS = _config["ALERT_COOLDOWN_HOURS"]
CARDTRADER_BASE_URL = _config["CARDTRADER_BASE_URL"]
SCRYFALL_BASE_URL = _config["SCRYFALL_BASE_URL"]
MTG_GAME_ID = _config["MTG_GAME_ID"]
