"""Local CSV logger for sent news articles — survives Telegram chat clears."""

import csv
import os
from datetime import datetime, timezone, timedelta

from . import config

IST = timezone(timedelta(hours=5, minutes=30))

_HEADERS = ["timestamp_ist", "stock", "headline", "source", "url", "priority"]


def _ensure_file():
    """Create the CSV file with headers if it doesn't exist."""
    if not os.path.exists(config.NEWS_LOG_FILE):
        with open(config.NEWS_LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(_HEADERS)


def log_articles(articles_by_symbol: dict[str, list[dict]]):
    """
    Append sent articles to the CSV log.

    Args:
        articles_by_symbol: {symbol: [article_dicts]}
    """
    if not articles_by_symbol:
        return

    _ensure_file()
    now_ist = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

    with open(config.NEWS_LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for symbol, articles in articles_by_symbol.items():
            for article in articles:
                writer.writerow([
                    now_ist,
                    symbol,
                    article.get("title", ""),
                    article.get("source", ""),
                    article.get("url", ""),
                    article.get("priority", "normal"),
                ])
