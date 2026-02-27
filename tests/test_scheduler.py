"""Tests to ensure the APScheduler is started inside the async event loop.

Regression: AsyncIOScheduler.start() requires a running event loop.
Calling it from synchronous code (e.g. directly in main()) raises
``RuntimeError: no running event loop``.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers to capture what main() does without starting a real Telegram bot
# ---------------------------------------------------------------------------

def _build_mock_app():
    """Return a mock Telegram Application that records post_init and skips polling."""
    mock_app = MagicMock()
    # run_polling should be a no-op
    mock_app.run_polling = MagicMock()
    return mock_app


@pytest.fixture
def mock_main_deps(monkeypatch):
    """Patch all external dependencies so we can import and call main()."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    monkeypatch.setenv("CARDTRADER_TOKEN", "fake-ct-token")
    monkeypatch.setenv("CHECK_INTERVAL_HOURS", "1")

    import config
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "123")
    monkeypatch.setattr(config, "CHECK_INTERVAL_HOURS", 1)

    import watchlist
    monkeypatch.setattr(watchlist, "get_all", lambda: [])

    import cardtrader
    monkeypatch.setattr(cardtrader, "get_expansions", lambda: [])

    mock_app = _build_mock_app()

    mock_builder = MagicMock()
    mock_builder.token.return_value = mock_builder
    mock_builder.build.return_value = mock_app

    with patch("bot.ApplicationBuilder", return_value=mock_builder):
        yield mock_app


class TestSchedulerStartsInEventLoop:
    """Ensure the scheduler is started inside the event loop, not synchronously."""

    def test_main_sets_post_init(self, mock_main_deps):
        """main() must assign an async callback to app.post_init instead of
        calling scheduler.start() synchronously."""
        import bot

        bot.main()
        mock_app = mock_main_deps

        # post_init must have been set to a callable
        assert mock_app.post_init is not None, (
            "main() must set app.post_init to start the scheduler inside the event loop"
        )
        assert callable(mock_app.post_init)

    def test_post_init_is_async(self, mock_main_deps):
        """The post_init callback must be a coroutine function so it runs
        inside the event loop."""
        import bot

        bot.main()
        mock_app = mock_main_deps

        assert asyncio.iscoroutinefunction(mock_app.post_init), (
            "post_init must be an async function so it runs inside the event loop"
        )

    def test_post_init_starts_scheduler(self, mock_main_deps):
        """Calling post_init inside a running event loop must successfully
        start the AsyncIOScheduler (the exact scenario that failed before)."""
        import bot

        bot.main()
        mock_app = mock_main_deps
        post_init = mock_app.post_init

        with patch("bot.AsyncIOScheduler") as MockScheduler:
            mock_sched_instance = MagicMock()
            MockScheduler.return_value = mock_sched_instance

            # Run the async callback inside an event loop
            asyncio.run(post_init(mock_app))

            mock_sched_instance.add_job.assert_called_once()
            mock_sched_instance.start.assert_called_once()

    def test_scheduler_start_not_called_synchronously(self, mock_main_deps):
        """scheduler.start() must NOT be called during main() itself
        (i.e. outside of an event loop)."""
        import bot

        with patch("bot.AsyncIOScheduler") as MockScheduler:
            mock_sched_instance = MagicMock()
            MockScheduler.return_value = mock_sched_instance

            bot.main()

            # The scheduler constructor may or may not be called during main(),
            # but .start() must NOT be called synchronously.
            mock_sched_instance.start.assert_not_called(), (
                "scheduler.start() must not be called synchronously in main(); "
                "it should only run inside the post_init async callback"
            )
