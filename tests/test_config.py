import pytest
import config as config_module
from config import load_config


REQUIRED_ENVS = {
    "CARDTRADER_API_TOKEN": "test-ct-token",
    "TELEGRAM_BOT_TOKEN": "test-tg-token",
    "TELEGRAM_CHAT_ID": "123456789",
}


@pytest.fixture(autouse=True)
def no_dotenv(monkeypatch):
    """Prevent load_dotenv from reading .env files during tests."""
    monkeypatch.setattr(config_module, "load_dotenv", lambda: None)
    monkeypatch.setattr(config_module, "_load_tgkit_env", lambda: False)


@pytest.fixture
def full_env(monkeypatch):
    """Set all required env vars."""
    for key, val in REQUIRED_ENVS.items():
        monkeypatch.setenv(key, val)
    # Clear optional vars to ensure defaults
    monkeypatch.delenv("CHECK_INTERVAL_HOURS", raising=False)
    monkeypatch.delenv("ALERT_COOLDOWN_HOURS", raising=False)


def test_all_required_vars_present(monkeypatch, full_env):
    cfg = load_config()
    assert cfg["CARDTRADER_API_TOKEN"] == "test-ct-token"
    assert cfg["TELEGRAM_BOT_TOKEN"] == "test-tg-token"
    assert cfg["TELEGRAM_CHAT_ID"] == 123456789
    assert cfg["CHECK_INTERVAL_HOURS"] == 1
    assert cfg["ALERT_COOLDOWN_HOURS"] == 24
    assert cfg["CARDTRADER_BASE_URL"] == "https://api.cardtrader.com/api/v2"
    assert cfg["SCRYFALL_BASE_URL"] == "https://api.scryfall.com"
    assert cfg["MTG_GAME_ID"] == 1


def test_missing_cardtrader_api_token(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    monkeypatch.delenv("CARDTRADER_API_TOKEN", raising=False)
    with pytest.raises(KeyError, match="CARDTRADER_API_TOKEN"):
        load_config()


def test_missing_telegram_bot_token(monkeypatch):
    monkeypatch.setenv("CARDTRADER_API_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(KeyError, match="TELEGRAM_BOT_TOKEN"):
        load_config()


def test_missing_telegram_chat_id(monkeypatch):
    monkeypatch.setenv("CARDTRADER_API_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with pytest.raises(KeyError, match="TELEGRAM_CHAT_ID"):
        load_config()


def test_negative_chat_id(monkeypatch, full_env):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-5158009038")
    cfg = load_config()
    assert cfg["TELEGRAM_CHAT_ID"] == -5158009038


def test_non_numeric_chat_id(monkeypatch, full_env):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "not-a-number")
    with pytest.raises(ValueError, match="TELEGRAM_CHAT_ID must be a valid integer"):
        load_config()


def test_optional_defaults(monkeypatch, full_env):
    monkeypatch.delenv("CHECK_INTERVAL_HOURS", raising=False)
    monkeypatch.delenv("ALERT_COOLDOWN_HOURS", raising=False)
    cfg = load_config()
    assert cfg["CHECK_INTERVAL_HOURS"] == 1
    assert cfg["ALERT_COOLDOWN_HOURS"] == 24


def test_custom_optional_values(monkeypatch, full_env):
    monkeypatch.setenv("CHECK_INTERVAL_HOURS", "6")
    monkeypatch.setenv("ALERT_COOLDOWN_HOURS", "48")
    cfg = load_config()
    assert cfg["CHECK_INTERVAL_HOURS"] == 6
    assert cfg["ALERT_COOLDOWN_HOURS"] == 48
