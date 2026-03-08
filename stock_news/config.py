"""Centralized configuration — loads all settings from .env"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Kite Connect ---
KITE_API_KEY = os.getenv("KITE_API_KEY", "")
KITE_API_SECRET = os.getenv("KITE_API_SECRET", "")
KITE_USER_ID = os.getenv("KITE_USER_ID", "")
KITE_PASSWORD = os.getenv("KITE_PASSWORD", "")
KITE_TOTP_SECRET = os.getenv("KITE_TOTP_SECRET", "")

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- Gemini AI ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# --- Scheduling ---
SCHEDULE_INTERVAL_MINUTES = int(os.getenv("SCHEDULE_INTERVAL_MINUTES", "15"))
MARKET_HOURS_ONLY = os.getenv("MARKET_HOURS_ONLY", "true").lower() == "true"

# --- Price Alerts ---
PRICE_ALERT_PCT = float(os.getenv("PRICE_ALERT_PCT", "3.0"))
PRICE_CHECK_INTERVAL = int(os.getenv("PRICE_CHECK_INTERVAL", "5"))  # minutes

# --- News ---
NEWS_MAX_ARTICLES = int(os.getenv("NEWS_MAX_ARTICLES", "3"))
NEWS_MAX_AGE_HOURS = float(os.getenv("NEWS_MAX_AGE_HOURS", "1"))

# --- Optional stock lists ---
_extra = os.getenv("EXTRA_STOCKS", "")
EXTRA_STOCKS = [s.strip() for s in _extra.split(",") if s.strip()]

_muted = os.getenv("MUTE_STOCKS", "")
MUTE_STOCKS = [s.strip().upper() for s in _muted.split(",") if s.strip()]

# --- Priority keywords ---
PRIORITY_URGENT = [
    "results", "earnings", "fraud", "sebi", "crash", "ban", "downgrade",
    "penalty", "scam", "default", "loss", "investigation", "suspend",
]
PRIORITY_IMPORTANT = [
    "acquisition", "merger", "buyback", "dividend", "upgrade", "target",
    "deal", "partnership", "ipo", "split", "bonus", "stake",
]

# --- Paths ---
# BASE_DIR points to project root (parent of stock_news/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KITE_SESSION_FILE = os.path.join(BASE_DIR, ".kite_session")
SEEN_NEWS_FILE = os.path.join(BASE_DIR, "seen_news.json")
NEWS_LOG_FILE = os.path.join(BASE_DIR, "news_log.csv")
MUTED_STOCKS_FILE = os.path.join(BASE_DIR, "muted_stocks.json")
WATCHLIST_FILE = os.path.join(BASE_DIR, "watchlist.json")
