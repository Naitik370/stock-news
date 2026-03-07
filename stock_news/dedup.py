"""Deduplication — tracks seen articles to avoid repeat Telegram notifications."""

import hashlib
import json
import os
import time
from datetime import datetime, timezone, timedelta

from . import config

IST = timezone(timedelta(hours=5, minutes=30))
_PRUNE_DAYS = 7


def _url_hash(url: str) -> str:
    """Create a short hash of a URL for dedup tracking."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _load_seen() -> dict:
    """Load seen articles from file. Returns {hash: timestamp}."""
    if not os.path.exists(config.SEEN_NEWS_FILE):
        return {}
    try:
        with open(config.SEEN_NEWS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_seen(seen: dict):
    """Atomic save of seen articles."""
    tmp_path = config.SEEN_NEWS_FILE + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(seen, f, indent=2)
    os.replace(tmp_path, config.SEEN_NEWS_FILE)


def _prune_old(seen: dict) -> dict:
    """Remove entries older than _PRUNE_DAYS."""
    cutoff = time.time() - (_PRUNE_DAYS * 86400)
    return {h: ts for h, ts in seen.items() if ts > cutoff}


def filter_new(articles_by_symbol: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """
    Filter out already-seen articles.

    Args:
        articles_by_symbol: {symbol: [article_dicts]}

    Returns:
        Same structure but with only unseen articles.
        Symbols with no new articles are omitted.
    """
    seen = _load_seen()
    new_articles = {}

    for symbol, articles in articles_by_symbol.items():
        unseen = []
        for article in articles:
            h = _url_hash(article["url"])
            if h not in seen:
                unseen.append(article)

        if unseen:
            new_articles[symbol] = unseen

    return new_articles


def mark_sent(articles_by_symbol: dict[str, list[dict]]):
    """
    Mark articles as sent so they won't be sent again.

    Args:
        articles_by_symbol: {symbol: [article_dicts]}
    """
    seen = _load_seen()
    now = time.time()

    for articles in articles_by_symbol.values():
        for article in articles:
            h = _url_hash(article["url"])
            seen[h] = now

    # Prune old entries
    seen = _prune_old(seen)

    _save_seen(seen)


def reset():
    """Clear all seen articles."""
    if os.path.exists(config.SEEN_NEWS_FILE):
        os.remove(config.SEEN_NEWS_FILE)
        print("[Dedup] Seen articles cleared.")
    else:
        print("[Dedup] No seen articles file to clear.")
