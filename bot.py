import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

import cardtrader
import scryfall
import watchlist
from alerts import format_alert, format_price_report, format_watchlist, should_alert
from config import CHECK_INTERVAL_HOURS, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from price_checker import check_all_prices, check_card_price

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Command parsing helpers
# ---------------------------------------------------------------------------

def parse_add_args(text: str) -> tuple[str, float, bool]:
    """Parse `/add <card name> <threshold> [foil]`.

    Returns (card_name, threshold, is_foil).
    """
    parts = text.strip().split()
    if not parts:
        raise ValueError("Usage: /add <card name> <threshold> [foil]")

    # Remove the /add command itself if present
    if parts[0].lower().startswith("/add"):
        parts = parts[1:]

    if not parts:
        raise ValueError("Usage: /add <card name> <threshold> [foil]")

    foil = False
    if parts[-1].lower() == "foil":
        foil = True
        parts = parts[:-1]

    if not parts:
        raise ValueError("Usage: /add <card name> <threshold> [foil]")

    # Last token should be the numeric threshold
    try:
        threshold = float(parts[-1])
    except ValueError:
        raise ValueError(
            "Could not parse threshold. Usage: /add <card name> <threshold> [foil]"
        )

    name_parts = parts[:-1]
    if not name_parts:
        raise ValueError("Card name is missing. Usage: /add <card name> <threshold> [foil]")

    card_name = " ".join(name_parts)
    # Clean up trailing/leading commas from name
    card_name = card_name.strip().rstrip(",").strip()
    return card_name, threshold, foil


def parse_check_args(text: str) -> str | None:
    """Parse `/check [card name]`. Returns card name or None for all."""
    parts = text.strip().split()
    if parts and parts[0].lower().startswith("/check"):
        parts = parts[1:]
    if not parts:
        return None
    return " ".join(parts).strip()


def parse_remove_args(text: str) -> tuple[str, bool]:
    """Parse `/remove <card name> [foil]`. Returns (card_name, is_foil)."""
    parts = text.strip().split()
    if parts and parts[0].lower().startswith("/remove"):
        parts = parts[1:]

    if not parts:
        raise ValueError("Usage: /remove <card name> [foil]")

    foil = False
    if parts[-1].lower() == "foil":
        foil = True
        parts = parts[:-1]

    if not parts:
        raise ValueError("Card name is missing. Usage: /remove <card name> [foil]")

    card_name = " ".join(parts).strip().rstrip(",").strip()
    return card_name, foil


# ---------------------------------------------------------------------------
# Telegram command handlers
# ---------------------------------------------------------------------------

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "MTG Price Alert Bot \U0001f0cf\n"
        "\n"
        "/add <card name> <threshold> [foil] \u2014 Watch a card\n"
        "/remove <card name> [foil] \u2014 Remove from watchlist\n"
        "/list \u2014 Show watchlist\n"
        "/check \u2014 Check all prices now\n"
        "/check <card name> \u2014 Check a specific card\n"
        "/help \u2014 Show this message"
    )
    await update.message.reply_text(text)


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        card_name, threshold, foil = parse_add_args(update.message.text)
    except ValueError as e:
        await update.message.reply_text(str(e))
        return

    foil_label = " (foil)" if foil else ""
    await update.message.reply_text(
        f"Searching for \"{card_name}\"{foil_label}..."
    )

    # Resolve via Scryfall -> CardTrader
    try:
        printings = scryfall.search_card(card_name)
    except Exception:
        logger.exception("Scryfall search failed for '%s'", card_name)
        await update.message.reply_text(f"Error searching Scryfall for \"{card_name}\".")
        return

    if not printings:
        await update.message.reply_text(f"Card \"{card_name}\" not found on Scryfall.")
        return

    # Use the canonical name from Scryfall
    canonical_name = printings[0].get("name", card_name)

    try:
        blueprint_ids = cardtrader.resolve_blueprint_ids(canonical_name, printings)
    except Exception:
        logger.exception("Blueprint resolution failed for '%s'", canonical_name)
        await update.message.reply_text(
            f"Error resolving CardTrader blueprints for \"{canonical_name}\"."
        )
        return

    if not blueprint_ids:
        await update.message.reply_text(
            f"Warning: No CardTrader blueprints found for \"{canonical_name}\". "
            f"Adding to watchlist anyway \u2014 price checks will return no results."
        )

    added_by = None
    if update.message.from_user:
        added_by = update.message.from_user.username or update.message.from_user.first_name

    entry = watchlist.add_card(
        name=canonical_name,
        foil=foil,
        threshold_eur=threshold,
        blueprint_ids=blueprint_ids,
        added_by=added_by,
    )

    threshold_str = f"\u20ac{threshold:.2f}"
    bp_count = len(blueprint_ids)
    await update.message.reply_text(
        f"\u2705 Added \"{canonical_name}\"{foil_label} with threshold {threshold_str} "
        f"({bp_count} blueprint{'s' if bp_count != 1 else ''} found)"
    )


async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        card_name, foil = parse_remove_args(update.message.text)
    except ValueError as e:
        await update.message.reply_text(str(e))
        return

    foil_label = " (foil)" if foil else ""
    removed = watchlist.remove_card(card_name, foil)
    if removed:
        await update.message.reply_text(f"\u2705 Removed \"{card_name}\"{foil_label} from watchlist.")
    else:
        await update.message.reply_text(f"\"{card_name}\"{foil_label} not found in watchlist.")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    entries = watchlist.get_all()
    text = format_watchlist(entries)
    await update.message.reply_text(text)


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    card_name = parse_check_args(update.message.text)

    if card_name:
        # Check specific card (both foil and non-foil if both exist)
        entries = watchlist.get_all()
        matches = [
            e for e in entries if e["name"].lower() == card_name.lower()
        ]
        if not matches:
            await update.message.reply_text(f"\"{card_name}\" not found in watchlist.")
            return

        await update.message.reply_text(f"Checking price for \"{card_name}\"...")
        for entry in matches:
            cheapest = check_card_price(entry)
            if cheapest:
                _update_entry_from_product(entry, cheapest)
                text = format_price_report(entry, cheapest)
            else:
                foil_label = " (foil)" if entry.get("foil") else ""
                text = f"{entry['name']}{foil_label}\n\nNo acceptable offers found."
            await update.message.reply_text(text)
    else:
        # Check all cards
        entries = watchlist.get_all()
        if not entries:
            await update.message.reply_text("Watchlist is empty.")
            return

        await update.message.reply_text(f"Checking prices for {len(entries)} card(s)...")
        results = check_all_prices(entries)
        for entry, cheapest in results:
            if cheapest:
                _update_entry_from_product(entry, cheapest)
                text = format_price_report(entry, cheapest)
            else:
                foil_label = " (foil)" if entry.get("foil") else ""
                text = f"{entry['name']}{foil_label}\n\nNo acceptable offers found."
            await update.message.reply_text(text)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _update_entry_from_product(entry: dict, product: dict) -> None:
    """Update watchlist entry with latest price info from a product."""
    props = product.get("properties_hash", {})
    price = product.get("price", {})
    user = product.get("user", {})
    expansion = product.get("expansion", {})

    watchlist.update_card_price(
        name=entry["name"],
        foil=entry["foil"],
        price_cents=price.get("cents", 0),
        currency=price.get("currency", "EUR"),
        condition=props.get("condition", ""),
        language=props.get("mtg_language", ""),
        seller=user.get("username", ""),
        seller_country=user.get("country_code", ""),
        set_name=expansion.get("name_en", ""),
    )


# ---------------------------------------------------------------------------
# Scheduled price check
# ---------------------------------------------------------------------------

async def scheduled_price_check(app) -> None:
    """Run by APScheduler every CHECK_INTERVAL_HOURS."""
    logger.info("Running scheduled price check...")
    try:
        entries = watchlist.get_all()
        if not entries:
            logger.info("Watchlist is empty, skipping scheduled check.")
            return

        results = check_all_prices(entries)
        for entry, cheapest in results:
            if cheapest is None:
                continue

            _update_entry_from_product(entry, cheapest)
            price_cents = cheapest.get("price", {}).get("cents", 0)

            if should_alert(entry, price_cents):
                text = format_alert(entry, cheapest)
                try:
                    await app.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)
                    watchlist.mark_alerted(entry["name"], entry["foil"])
                    logger.info("Sent alert for '%s'", entry["name"])
                except Exception:
                    logger.exception("Failed to send alert for '%s'", entry["name"])

    except Exception:
        logger.exception("Scheduled price check failed")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)

    # Load watchlist
    entries = watchlist.get_all()
    logger.info("Loaded watchlist with %d entries", len(entries))

    # Pre-cache CardTrader expansions
    try:
        expansions = cardtrader.get_expansions()
        logger.info("Cached %d CardTrader expansions", len(expansions))
    except Exception:
        logger.exception("Failed to fetch CardTrader expansions on startup")

    # Build Telegram application
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("start", cmd_help))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("remove", cmd_remove))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("check", cmd_check))

    # Start APScheduler inside the event loop via post_init
    async def start_scheduler(application):
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            scheduled_price_check,
            "interval",
            hours=CHECK_INTERVAL_HOURS,
            args=[application],
            id="price_check",
            name="Hourly price check",
        )
        scheduler.start()
        logger.info("Scheduler started (interval: %d hour(s))", CHECK_INTERVAL_HOURS)

    app.post_init = start_scheduler

    # Start polling
    logger.info("Starting Telegram bot polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
