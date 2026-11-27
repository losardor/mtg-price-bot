import os
from pathlib import Path

from dotenv import load_dotenv

BOT_NAME = "mtg-price-bot"


def _tgkit_env_file() -> Path | None:
    """The host's env file (~/.config/tgbots/mtg-price-bot.env), if this host has one."""
    try:
        from tgkit.config import env_path
    except ImportError:
        return None
    path = env_path(BOT_NAME)
    return path if path.is_file() else None


def _load_tgkit_env() -> bool:
    """Load the host env file through tgkit (refuses a group/world-readable file)."""
    path = _tgkit_env_file()
    if path is None:
        return False
    from tgkit import load_env
    load_env(BOT_NAME, env_file=path)
    return True


def load_config() -> dict:
    """Load configuration from environment variables.

    Returns a dict with all config values.
    Raises KeyError for missing required vars, ValueError for invalid TELEGRAM_CHAT_ID.
    """
    # On a host with ~/.config/tgbots/mtg-price-bot.env (the NUC) that file is
    # used; otherwise the repo's .env, as in local development.
    if not _load_tgkit_env():
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
        # Scryfall rejects default/missing User-Agents (HTTP 400, rule
        # generic_user_agent). Set MTG_BOT_USER_AGENT in the env file to add a
        # contact, e.g. "mtg-price-bot/1.0 (you@example.org)".
        "USER_AGENT": os.getenv("MTG_BOT_USER_AGENT") or "mtg-price-bot/1.0",
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
USER_AGENT = _config["USER_AGENT"]
