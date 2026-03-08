"""Tests for bot module — command handlers."""

import sys
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from stock_news.bot import (
    start_cmd,
    help_cmd,
    portfolio_cmd,
    news_cmd,
    mute_cmd,
    unmute_cmd,
    muted_cmd,
    stocks_cmd,
    watch_cmd,
    unwatch_cmd,
    watchlist_cmd,
    _authorized,
    _runtime_muted,
)


# ── Helpers ───────────────────────────────────────────────────────────

def _make_update(chat_id="123456"):
    """Create a mock Update with an effective_chat and message."""
    update = MagicMock()
    update.effective_chat.id = int(chat_id)
    update.message.reply_text = AsyncMock()
    return update


def _make_context(bot_data=None, args=None):
    """Create a mock context."""
    ctx = MagicMock()
    ctx.bot_data = bot_data or {"use_mock": True, "kite_client": None}
    ctx.args = args or []
    return ctx


# ── Authorization ─────────────────────────────────────────────────────

class TestAuthorization:
    @patch("stock_news.bot.config")
    def test_authorized_chat(self, mock_config):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        update = _make_update("123456")
        assert _authorized(update) is True

    @patch("stock_news.bot.config")
    def test_unauthorized_chat(self, mock_config):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        update = _make_update("999999")
        assert _authorized(update) is False


# ── /start ────────────────────────────────────────────────────────────

class TestStartCmd:
    @pytest.mark.asyncio
    @patch("stock_news.bot.config")
    async def test_start_sends_welcome(self, mock_config):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        update = _make_update("123456")
        ctx = _make_context()
        await start_cmd(update, ctx)
        update.message.reply_text.assert_called_once()
        text = update.message.reply_text.call_args[0][0]
        assert "Stock News Bot" in text


# ── /help ─────────────────────────────────────────────────────────────

class TestHelpCmd:
    @pytest.mark.asyncio
    @patch("stock_news.bot.config")
    async def test_help_lists_commands(self, mock_config):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        update = _make_update("123456")
        ctx = _make_context()
        await help_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "/portfolio" in text
        assert "/news" in text
        assert "/mute" in text
        assert "/stocks" in text
        assert "/watch" in text
        assert "/watchlist" in text


# ── /portfolio ────────────────────────────────────────────────────────

class TestPortfolioCmd:
    @pytest.mark.asyncio
    @patch("stock_news.bot.config")
    async def test_portfolio_returns_summary(self, mock_config):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        update = _make_update("123456")
        ctx = _make_context()
        await portfolio_cmd(update, ctx)
        # Two calls: "Fetching…" + the actual summary
        assert update.message.reply_text.call_count == 2
        final_text = update.message.reply_text.call_args_list[-1][0][0]
        assert "Portfolio" in final_text or "₹" in final_text


# ── /stocks ───────────────────────────────────────────────────────────

class TestStocksCmd:
    @pytest.mark.asyncio
    @patch("stock_news.bot.config")
    async def test_stocks_lists_holdings(self, mock_config):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        update = _make_update("123456")
        ctx = _make_context()
        await stocks_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "RELIANCE" in text
        assert "TCS" in text


# ── /news ─────────────────────────────────────────────────────────────

class TestNewsCmd:
    @pytest.mark.asyncio
    @patch("stock_news.bot.config")
    async def test_news_no_args_shows_usage(self, mock_config):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        update = _make_update("123456")
        ctx = _make_context(args=[])
        await news_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "Usage" in text or "SYMBOL" in text

    @pytest.mark.asyncio
    @patch("stock_news.bot.fetch_news_for_stock", return_value=[])
    @patch("stock_news.bot.config")
    async def test_news_no_results(self, mock_config, mock_fetch):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        update = _make_update("123456")
        ctx = _make_context(args=["RELIANCE"])
        await news_cmd(update, ctx)
        mock_fetch.assert_called_once()
        # "Fetching…" + "No recent news"
        assert update.message.reply_text.call_count == 2

    @pytest.mark.asyncio
    @patch("stock_news.bot.fetch_news_for_stock")
    @patch("stock_news.bot.config")
    async def test_news_with_results(self, mock_config, mock_fetch):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        mock_fetch.return_value = [{
            "title": "Test headline",
            "source": "Test",
            "url": "https://example.com",
            "published_at_ist": "2026-03-08 12:00 IST",
            "priority_emoji": "⚪",
        }]
        update = _make_update("123456")
        ctx = _make_context(args=["TCS"])
        await news_cmd(update, ctx)
        final_text = update.message.reply_text.call_args_list[-1][0][0]
        assert "Test headline" in final_text


# ── /mute & /unmute & /muted ─────────────────────────────────────────

class TestMuteCommands:
    @pytest.mark.asyncio
    @patch("stock_news.bot._save_muted")
    @patch("stock_news.bot.config")
    async def test_mute_adds_symbol(self, mock_config, mock_save):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        mock_config.MUTE_STOCKS = []
        update = _make_update("123456")
        ctx = _make_context(args=["INFY"])
        await mute_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "INFY" in text
        assert "muted" in text.lower()
        mock_save.assert_called_once()

    @pytest.mark.asyncio
    @patch("stock_news.bot._save_muted")
    @patch("stock_news.bot.config")
    async def test_unmute_removes_symbol(self, mock_config, mock_save):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        mock_config.MUTE_STOCKS = ["INFY"]
        _runtime_muted.add("INFY")
        update = _make_update("123456")
        ctx = _make_context(args=["INFY"])
        await unmute_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "INFY" in text
        assert "unmuted" in text.lower()

    @pytest.mark.asyncio
    @patch("stock_news.bot.config")
    async def test_muted_lists_stocks(self, mock_config):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        _runtime_muted.clear()
        _runtime_muted.add("SAIL")
        _runtime_muted.add("IDEA")
        update = _make_update("123456")
        ctx = _make_context()
        await muted_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "SAIL" in text
        assert "IDEA" in text

    @pytest.mark.asyncio
    @patch("stock_news.bot.config")
    async def test_muted_empty(self, mock_config):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        _runtime_muted.clear()
        update = _make_update("123456")
        ctx = _make_context()
        await muted_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "No stocks are muted" in text

    @pytest.mark.asyncio
    @patch("stock_news.bot.config")
    async def test_mute_no_args_shows_usage(self, mock_config):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        update = _make_update("123456")
        ctx = _make_context(args=[])
        await mute_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "Usage" in text or "SYMBOL" in text


# ── /watch & /unwatch & /watchlist ────────────────────────────────────

class TestWatchlistCommands:
    @pytest.mark.asyncio
    @patch("stock_news.bot.watchlist")
    @patch("stock_news.bot.config")
    async def test_watch_adds_symbol(self, mock_config, mock_wl):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        mock_wl.add.return_value = True
        update = _make_update("123456")
        ctx = _make_context(args=["ZOMATO"])
        await watch_cmd(update, ctx)
        mock_wl.add.assert_called_once_with("ZOMATO")
        text = update.message.reply_text.call_args[0][0]
        assert "ZOMATO" in text
        assert "watchlist" in text.lower()

    @pytest.mark.asyncio
    @patch("stock_news.bot.watchlist")
    @patch("stock_news.bot.config")
    async def test_watch_duplicate(self, mock_config, mock_wl):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        mock_wl.add.return_value = False
        update = _make_update("123456")
        ctx = _make_context(args=["ZOMATO"])
        await watch_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "already" in text.lower()

    @pytest.mark.asyncio
    @patch("stock_news.bot.watchlist")
    @patch("stock_news.bot.config")
    async def test_unwatch_removes_symbol(self, mock_config, mock_wl):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        mock_wl.remove.return_value = True
        update = _make_update("123456")
        ctx = _make_context(args=["ZOMATO"])
        await unwatch_cmd(update, ctx)
        mock_wl.remove.assert_called_once_with("ZOMATO")
        text = update.message.reply_text.call_args[0][0]
        assert "ZOMATO" in text

    @pytest.mark.asyncio
    @patch("stock_news.bot.watchlist")
    @patch("stock_news.bot.config")
    async def test_watchlist_shows_stocks(self, mock_config, mock_wl):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        mock_wl.load.return_value = ["ZOMATO", "PAYTM"]
        update = _make_update("123456")
        ctx = _make_context()
        await watchlist_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "ZOMATO" in text
        assert "PAYTM" in text

    @pytest.mark.asyncio
    @patch("stock_news.bot.watchlist")
    @patch("stock_news.bot.config")
    async def test_watchlist_empty(self, mock_config, mock_wl):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        mock_wl.load.return_value = []
        update = _make_update("123456")
        ctx = _make_context()
        await watchlist_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "empty" in text.lower()

    @pytest.mark.asyncio
    @patch("stock_news.bot.config")
    async def test_watch_no_args_shows_usage(self, mock_config):
        mock_config.TELEGRAM_CHAT_ID = "123456"
        update = _make_update("123456")
        ctx = _make_context(args=[])
        await watch_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "Usage" in text or "SYMBOL" in text
