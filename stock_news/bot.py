"""Interactive Telegram bot — adds two-way commands on top of push alerts."""

import json
import logging
import os
from datetime import datetime, timezone, timedelta

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from . import config, watchlist
from .holdings import get_mock_holdings, fetch_holdings, symbol_to_company
from .news import fetch_news_for_stock
from .portfolio import compute_summary, format_summary
from .notifier import format_news_message, _escape_html
from .ai_summary import enrich_articles
from . import price_monitor

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))

# ── Runtime mute set (loaded from file + env on startup) ──────────────
_runtime_muted: set[str] = set()


def _muted_file() -> str:
    return os.path.join(config.BASE_DIR, "muted_stocks.json")


def _load_muted() -> set[str]:
    """Load muted stocks from env config + persistent JSON file."""
    muted = {s.upper() for s in config.MUTE_STOCKS}
    path = _muted_file()
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                muted |= {s.upper() for s in json.load(f)}
        except (json.JSONDecodeError, IOError):
            pass
    return muted


def _save_muted():
    """Persist runtime muted set to JSON file."""
    path = _muted_file()
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(sorted(_runtime_muted), f, indent=2)
    os.replace(tmp, path)


# ── Authorization ─────────────────────────────────────────────────────

def _authorized(update: Update) -> bool:
    """Check if the chat is the configured one."""
    chat_id = str(update.effective_chat.id)
    return chat_id == str(config.TELEGRAM_CHAT_ID)


# ── Command handlers ─────────────────────────────────────────────────

async def start_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    text = (
        "👋 <b>Stock News Bot</b>\n\n"
        "I track your portfolio and send news alerts.\n\n"
        "Use /help to see all commands."
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    text = (
        "📖 <b>Available Commands</b>\n\n"
        "<b>Portfolio</b>\n"
        "/portfolio — Live P&amp;L snapshot\n"
        "/stocks — List your portfolio symbols\n\n"
        "<b>News</b>\n"
        "/news &lt;SYMBOL&gt; — Latest news for a stock\n\n"
        "<b>Watchlist</b>\n"
        "/watch &lt;SYMBOL&gt; — Add stock to alert watchlist\n"
        "/unwatch &lt;SYMBOL&gt; — Remove from watchlist\n"
        "/watchlist — Show watchlisted stocks\n\n"
        "<b>Filters</b>\n"
        "/mute &lt;SYMBOL&gt; — Mute a stock from alerts\n"
        "/unmute &lt;SYMBOL&gt; — Unmute a stock\n"
        "/muted — Show muted stocks\n\n"
        "/help — This help message"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def portfolio_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    await update.message.reply_text("⏳ Fetching portfolio…")

    # Use Kite client if available, otherwise mock
    kite = ctx.bot_data.get("kite_client")
    if kite:
        try:
            from .kite_auth import is_token_valid
            if not is_token_valid(kite):
                await update.message.reply_text(
                    "⚠️ Kite session expired. Using last known data."
                )
                stock_holdings = get_mock_holdings()
            else:
                stock_holdings = fetch_holdings(kite)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {_escape_html(str(e))}", parse_mode="HTML")
            return
    else:
        stock_holdings = get_mock_holdings()

    summary = compute_summary(stock_holdings)
    text = format_summary(summary)

    if not text:
        text = "📊 No portfolio data available."

    await update.message.reply_text(text)


async def stocks_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    kite = ctx.bot_data.get("kite_client")
    use_mock = ctx.bot_data.get("use_mock", True)

    if use_mock or not kite:
        stock_holdings = get_mock_holdings()
    else:
        try:
            stock_holdings = fetch_holdings(kite)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {_escape_html(str(e))}", parse_mode="HTML")
            return

    # Merge watchlist stocks
    wl_holdings = watchlist.get_as_holdings()
    existing_symbols = {h["symbol"].upper() for h in stock_holdings}
    for wh in wl_holdings:
        if wh["symbol"].upper() not in existing_symbols:
            stock_holdings.append(wh)

    if not stock_holdings:
        await update.message.reply_text("📂 No holdings found.")
        return

    wl_symbols = {s.upper() for s in watchlist.load()}

    lines = ["📂 <b>Your Stocks</b>\n"]
    for h in stock_holdings:
        symbol = h["symbol"]
        company = h.get("company_name", symbol)
        qty = h.get("quantity", 0)
        if qty > 0:
            lines.append(f"  <code>{symbol}</code> — {_escape_html(company)} ({qty} shares)")
        elif symbol.upper() in wl_symbols:
            lines.append(f"  <code>{symbol}</code> — {_escape_html(company)} (👀 watchlist)")
        else:
            lines.append(f"  <code>{symbol}</code> — {_escape_html(company)} (extra)")

    lines.append("\n💡 Use <code>/news SYMBOL</code> to get news for any stock.")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def news_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    args = ctx.args
    if not args:
        await update.message.reply_text(
            "Usage: /news <b>&lt;SYMBOL&gt;</b>\n"
            "Example: <code>/news RELIANCE</code>",
            parse_mode="HTML",
        )
        return

    symbol = args[0].upper()
    company = symbol_to_company(symbol)

    await update.message.reply_text(f"🔍 Fetching news for <b>{symbol}</b>…", parse_mode="HTML")

    articles = fetch_news_for_stock(
        company_name=company,
        symbol=symbol,
        max_articles=5,
        max_age_hours=24,
    )

    if not articles:
        await update.message.reply_text(f"No recent news found for <b>{symbol}</b>.", parse_mode="HTML")
        return

    # Enrich with AI sentiment + summary
    enrich_articles({symbol: articles})

    lines = [f"📰 <b>News for {symbol}</b>\n"]
    for a in articles:
        emoji = a.get("ai_sentiment_emoji", a.get("priority_emoji", "⚪"))
        title = _escape_html(a.get("title", ""))
        source = _escape_html(a.get("source", ""))
        pub = a.get("published_at_ist", "")
        url = a.get("url", "")

        lines.append(f"{emoji} {title}")
        lines.append(f"    — {source} | {pub}")

        ai_summary = a.get("ai_summary", "")
        if ai_summary:
            lines.append(f"    💡 <i>{_escape_html(ai_summary)}</i>")

        if url:
            lines.append(f'    🔗 <a href="{url}">Read more</a>')
        lines.append("")

    await update.message.reply_text(
        "\n".join(lines).strip(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def mute_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    args = ctx.args
    if not args:
        await update.message.reply_text(
            "Usage: /mute <b>&lt;SYMBOL&gt;</b>\n"
            "Example: <code>/mute INFY</code>",
            parse_mode="HTML",
        )
        return

    symbol = args[0].upper()
    _runtime_muted.add(symbol)
    _save_muted()

    # Also sync to config so the news cycle picks it up immediately
    if symbol not in config.MUTE_STOCKS:
        config.MUTE_STOCKS.append(symbol)

    await update.message.reply_text(f"🔇 <b>{symbol}</b> muted. It won't appear in alerts.", parse_mode="HTML")


async def unmute_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    args = ctx.args
    if not args:
        await update.message.reply_text(
            "Usage: /unmute <b>&lt;SYMBOL&gt;</b>\n"
            "Example: <code>/unmute INFY</code>",
            parse_mode="HTML",
        )
        return

    symbol = args[0].upper()
    _runtime_muted.discard(symbol)
    _save_muted()

    if symbol in config.MUTE_STOCKS:
        config.MUTE_STOCKS.remove(symbol)

    await update.message.reply_text(f"🔊 <b>{symbol}</b> unmuted.", parse_mode="HTML")


async def muted_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    if _runtime_muted:
        symbols = ", ".join(sorted(_runtime_muted))
        text = f"🔇 <b>Muted stocks:</b> {symbols}"
    else:
        text = "🔊 No stocks are muted."

    await update.message.reply_text(text, parse_mode="HTML")


# ── Watchlist commands ────────────────────────────────────────────────

async def watch_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    args = ctx.args
    if not args:
        await update.message.reply_text(
            "Usage: /watch <b>&lt;SYMBOL&gt;</b>\n"
            "Example: <code>/watch ZOMATO</code>",
            parse_mode="HTML",
        )
        return

    symbol = args[0].upper()
    added = watchlist.add(symbol)
    company = symbol_to_company(symbol)

    if added:
        await update.message.reply_text(
            f"👀 <b>{symbol}</b> ({_escape_html(company)}) added to watchlist.\n"
            f"You'll now get news alerts for it.",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            f"<b>{symbol}</b> is already on your watchlist.",
            parse_mode="HTML",
        )


async def unwatch_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    args = ctx.args
    if not args:
        await update.message.reply_text(
            "Usage: /unwatch <b>&lt;SYMBOL&gt;</b>\n"
            "Example: <code>/unwatch ZOMATO</code>",
            parse_mode="HTML",
        )
        return

    symbol = args[0].upper()
    removed = watchlist.remove(symbol)

    if removed:
        await update.message.reply_text(
            f"✅ <b>{symbol}</b> removed from watchlist.",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            f"<b>{symbol}</b> was not on your watchlist.",
            parse_mode="HTML",
        )


async def watchlist_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    symbols = watchlist.load()
    if not symbols:
        await update.message.reply_text(
            "👀 Your watchlist is empty.\n"
            "Use <code>/watch SYMBOL</code> to add stocks.",
            parse_mode="HTML",
        )
        return

    lines = ["👀 <b>Alert Watchlist</b>\n"]
    for s in sorted(symbols):
        company = symbol_to_company(s)
        lines.append(f"  <code>{s}</code> — {_escape_html(company)}")
    lines.append(f"\n📊 {len(symbols)} stock(s) tracked")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ── Scheduled news push (runs inside the bot's event loop) ────────────

async def _scheduled_news_cycle(ctx: ContextTypes.DEFAULT_TYPE):
    """Job callback — runs one news-fetch cycle and pushes results."""
    from .dedup import filter_new, mark_sent
    from .news import fetch_news
    from .news_logger import log_articles

    chat_id = config.TELEGRAM_CHAT_ID
    if not chat_id:
        return

    # Determine holdings
    kite = ctx.bot_data.get("kite_client")
    use_mock = ctx.bot_data.get("use_mock", True)

    if use_mock or not kite:
        stock_holdings = get_mock_holdings()
    else:
        try:
            from .kite_auth import is_token_valid, get_kite_client
            if not is_token_valid(kite):
                kite = get_kite_client()
                if kite:
                    ctx.bot_data["kite_client"] = kite
                else:
                    logger.warning("Kite re-login failed during scheduled cycle.")
                    return
            stock_holdings = fetch_holdings(kite)
        except Exception as e:
            logger.error(f"Holdings fetch failed: {e}")
            return

    # Merge watchlist stocks
    existing_symbols = {h["symbol"].upper() for h in stock_holdings}
    for wh in watchlist.get_as_holdings():
        if wh["symbol"].upper() not in existing_symbols:
            stock_holdings.append(wh)

    # Check market hours
    now = datetime.now(IST)
    if config.MARKET_HOURS_ONLY and not use_mock:
        if now.weekday() >= 5 or not (9 <= now.hour < 16):
            return

    # Portfolio summary
    portfolio_text = ""
    summary = compute_summary([h for h in stock_holdings if h.get("quantity", 0) > 0])
    if summary["current_value"] > 0:
        portfolio_text = format_summary(summary)

    # Fetch & dedup news
    all_news = fetch_news(stock_holdings)
    if not all_news:
        return

    new_articles = filter_new(all_news)
    if not new_articles:
        return

    # Format and send
    enrich_articles(new_articles)
    message = format_news_message(new_articles, portfolio_text)
    try:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"Failed to send scheduled alert: {e}")

    mark_sent(new_articles)
    log_articles(new_articles)
    logger.info(
        f"Pushed {sum(len(v) for v in new_articles.values())} article(s) at "
        f"{now.strftime('%H:%M IST')}"
    )


async def _price_check_job(ctx: ContextTypes.DEFAULT_TYPE):
    """Job callback — checks for price spikes/drops every few minutes."""
    chat_id = config.TELEGRAM_CHAT_ID
    if not chat_id:
        return

    kite = ctx.bot_data.get("kite_client")
    use_mock = ctx.bot_data.get("use_mock", True)

    # Gather all symbols (holdings + watchlist)
    if use_mock or not kite:
        from .holdings import get_mock_holdings
        symbols = [h["symbol"] for h in get_mock_holdings()]
    else:
        try:
            from .kite_auth import is_token_valid, get_kite_client
            if not is_token_valid(kite):
                kite = get_kite_client()
                if kite:
                    ctx.bot_data["kite_client"] = kite
                else:
                    return
            symbols = [h["symbol"] for h in fetch_holdings(kite)]
        except Exception as e:
            logger.error(f"[PriceCheck] Holdings fetch failed: {e}")
            return

    # Add watchlist symbols
    wl_symbols = watchlist.load()
    existing = {s.upper() for s in symbols}
    for ws in wl_symbols:
        if ws.upper() not in existing:
            symbols.append(ws)

    if not symbols:
        return

    # Check market hours
    now = datetime.now(IST)
    if config.MARKET_HOURS_ONLY and not use_mock:
        if now.weekday() >= 5 or not (9 <= now.hour < 16):
            return

    # Run price check
    if use_mock or not kite:
        alerts = price_monitor.check_prices_mock(symbols)
    else:
        alerts = price_monitor.check_prices(kite, symbols)

    if not alerts:
        return

    message = price_monitor.format_price_alert(alerts)
    try:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"[PriceCheck] Failed to send alert: {e}")

    logger.info(f"[PriceCheck] Sent {len(alerts)} price alert(s) at {now.strftime('%H:%M IST')}")


# ── Bot launcher ──────────────────────────────────────────────────────

def run_bot(use_mock: bool = False, kite_client=None):
    """Start the interactive Telegram bot with scheduled news pushes."""
    global _runtime_muted
    _runtime_muted = _load_muted()

    if not config.TELEGRAM_BOT_TOKEN:
        print("[Bot] TELEGRAM_BOT_TOKEN not set. Cannot start bot.")
        return

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Store shared state
    app.bot_data["kite_client"] = kite_client
    app.bot_data["use_mock"] = use_mock

    # Register command handlers
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("portfolio", portfolio_cmd))
    app.add_handler(CommandHandler("news", news_cmd))
    app.add_handler(CommandHandler("stocks", stocks_cmd))
    app.add_handler(CommandHandler("watch", watch_cmd))
    app.add_handler(CommandHandler("unwatch", unwatch_cmd))
    app.add_handler(CommandHandler("watchlist", watchlist_cmd))
    app.add_handler(CommandHandler("mute", mute_cmd))
    app.add_handler(CommandHandler("unmute", unmute_cmd))
    app.add_handler(CommandHandler("muted", muted_cmd))

    # Schedule the periodic news cycle
    interval = config.SCHEDULE_INTERVAL_MINUTES * 60
    app.job_queue.run_repeating(
        _scheduled_news_cycle,
        interval=interval,
        first=10,  # first run 10s after bot starts
        name="news_cycle",
    )

    # Schedule the price check job
    price_interval = config.PRICE_CHECK_INTERVAL * 60
    app.job_queue.run_repeating(
        _price_check_job,
        interval=price_interval,
        first=5,  # first run 5s after bot starts
        name="price_check",
    )

    print(f"\n🤖 Bot started! Polling for commands…")
    print(f"   News push: every {config.SCHEDULE_INTERVAL_MINUTES} min")
    print(f"   Price check: every {config.PRICE_CHECK_INTERVAL} min (±{config.PRICE_ALERT_PCT}% threshold)")
    print(f"   Mode: {'Mock' if use_mock else 'Live (Kite)'}")
    print(f"   Press Ctrl+C to stop.\n")

    app.run_polling(allowed_updates=Update.ALL_TYPES)
