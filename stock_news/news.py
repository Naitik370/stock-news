"""Google News RSS parser with IST filtering and priority scoring."""

import time
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import feedparser
import requests as http_requests

from . import config

IST = timezone(timedelta(hours=5, minutes=30))


def _score_priority(headline: str) -> str:
    """
    Score a headline's priority based on keywords.
    Returns: 'urgent', 'important', or 'normal'
    """
    lower = headline.lower()

    for kw in config.PRIORITY_URGENT:
        if kw in lower:
            return "urgent"

    for kw in config.PRIORITY_IMPORTANT:
        if kw in lower:
            return "important"

    return "normal"


def _priority_emoji(priority: str) -> str:
    """Return emoji for priority level."""
    return {
        "urgent": "🔴",
        "important": "🟡",
        "normal": "⚪",
    }.get(priority, "⚪")


def _parse_title(raw_title: str) -> tuple[str, str]:
    """
    Split Google News RSS title into headline and source.
    Format: "Headline text - Source Name"
    """
    parts = raw_title.rsplit(" - ", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return raw_title.strip(), "Unknown"


def _parse_pubdate(entry) -> datetime | None:
    """Parse the pubDate from an RSS entry into a timezone-aware datetime."""
    pub_str = entry.get("published", "")
    if not pub_str:
        return None

    try:
        return parsedate_to_datetime(pub_str)
    except Exception:
        pass

    # Fallback: feedparser's parsed time
    try:
        struct = entry.get("published_parsed")
        if struct:
            from calendar import timegm
            ts = timegm(struct)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
    except Exception:
        pass

    return None


def fetch_news_for_stock(
    company_name: str,
    symbol: str,
    max_articles: int = None,
    max_age_hours: float = None,
) -> list[dict]:
    """
    Fetch news for a single stock from Google News RSS.

    Args:
        company_name: Human-readable name (e.g., "Reliance Industries")
        symbol: NSE trading symbol (e.g., "RELIANCE")
        max_articles: Max articles to return (default from config)
        max_age_hours: Only return articles newer than this (default from config)

    Returns:
        List of article dicts with keys:
        title, source, url, published_at_ist, priority, priority_emoji, symbol
    """
    if max_articles is None:
        max_articles = config.NEWS_MAX_ARTICLES
    if max_age_hours is None:
        max_age_hours = config.NEWS_MAX_AGE_HOURS

    # Build Google News RSS URL
    query = f"{company_name} stock"
    encoded_query = quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"

    articles = []
    now_ist = datetime.now(IST)
    cutoff = now_ist - timedelta(hours=max_age_hours)

    retries = 2
    feed = None
    for attempt in range(retries + 1):
        try:
            # Use requests with timeout, then parse the content
            resp = http_requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            break
        except Exception as e:
            if attempt < retries:
                print(f"  [News] Retry {attempt + 1} for {symbol}: {e}")
                time.sleep(3)
            else:
                print(f"  [News] Failed to fetch news for {symbol}: {e}")
                return []

    if feed is None:
        return []

    for entry in feed.entries:
        # Parse publication date
        pub_dt = _parse_pubdate(entry)
        if not pub_dt:
            continue

        # Convert to IST
        pub_ist = pub_dt.astimezone(IST)

        # Time filter: skip articles older than max_age_hours
        if pub_ist < cutoff:
            continue

        # Parse title
        headline, source_from_title = _parse_title(entry.get("title", ""))

        # Prefer <source> tag, fall back to title parsing
        source = entry.get("source", {}).get("title", source_from_title)

        # Get link
        link = entry.get("link", "")

        # Priority scoring
        priority = _score_priority(headline)

        articles.append({
            "symbol": symbol,
            "company_name": company_name,
            "title": headline,
            "source": source,
            "url": link,
            "published_at_ist": pub_ist.strftime("%Y-%m-%d %H:%M IST"),
            "published_dt": pub_ist,
            "priority": priority,
            "priority_emoji": _priority_emoji(priority),
        })

    # Sort by recency (latest first), then by priority as tiebreaker
    priority_order = {"urgent": 0, "important": 1, "normal": 2}
    articles.sort(key=lambda a: (-a["published_dt"].timestamp(), priority_order.get(a["priority"], 2)))

    return articles[:max_articles]


def fetch_news(holdings: list[dict], max_articles: int = None, max_age_hours: float = None) -> dict[str, list[dict]]:
    """
    Fetch news for all stocks in holdings.

    Args:
        holdings: List of holding dicts (must have 'symbol' and 'company_name')
        max_articles: Max articles per stock
        max_age_hours: Only articles newer than this

    Returns:
        Dict mapping symbol → list of article dicts.
        Only includes stocks that have at least one article.
    """
    all_news = {}

    for i, holding in enumerate(holdings):
        symbol = holding["symbol"]
        company = holding["company_name"]

        print(f"  [News] Fetching: {symbol} ({company})...")

        articles = fetch_news_for_stock(
            company_name=company,
            symbol=symbol,
            max_articles=max_articles,
            max_age_hours=max_age_hours,
        )

        if articles:
            all_news[symbol] = articles
            print(f"  [News]   → {len(articles)} article(s) found")
        else:
            print(f"  [News]   → No recent news")

        # Be polite to Google — small delay between requests
        if i < len(holdings) - 1:
            time.sleep(0.5)

    return all_news
