"""Price spike / drop monitor — alerts when a stock moves significantly in a short window."""

import logging
import random
from datetime import datetime, timezone, timedelta

from . import config

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))

# In-memory price cache: {symbol: last_price}
_price_cache: dict[str, float] = {}


def check_prices(
    kite,
    symbols: list[str],
    threshold_pct: float | None = None,
) -> list[dict]:
    """
    Fetch live prices via Kite LTP and compare with cached prices.

    Returns a list of alert dicts for symbols that moved beyond threshold:
      [{"symbol": ..., "prev_price": ..., "curr_price": ..., "change_pct": ..., "direction": "spike"|"drop"}]
    """
    if threshold_pct is None:
        threshold_pct = config.PRICE_ALERT_PCT

    if not symbols:
        return []

    # Build instrument keys (NSE:SYMBOL format)
    instruments = [f"NSE:{s}" for s in symbols]

    try:
        ltp_data = kite.ltp(instruments)
    except Exception as e:
        logger.error(f"[PriceMonitor] LTP fetch failed: {e}")
        return []

    alerts = []

    for symbol in symbols:
        key = f"NSE:{symbol}"
        if key not in ltp_data:
            continue

        curr_price = ltp_data[key].get("last_price", 0)
        if curr_price <= 0:
            continue

        prev_price = _price_cache.get(symbol)

        # Update cache
        _price_cache[symbol] = curr_price

        # Skip first reading (no previous price to compare)
        if prev_price is None or prev_price <= 0:
            continue

        change_pct = ((curr_price - prev_price) / prev_price) * 100

        if abs(change_pct) >= threshold_pct:
            direction = "spike" if change_pct > 0 else "drop"
            alerts.append({
                "symbol": symbol,
                "prev_price": prev_price,
                "curr_price": curr_price,
                "change_pct": round(change_pct, 2),
                "direction": direction,
            })

    return alerts


def check_prices_mock(
    symbols: list[str],
    threshold_pct: float | None = None,
) -> list[dict]:
    """
    Simulate price checks with random fluctuations for testing.
    ~20% chance of generating a significant move for at least one stock.
    """
    if threshold_pct is None:
        threshold_pct = config.PRICE_ALERT_PCT

    alerts = []

    for symbol in symbols:
        # Give each stock a base price if not cached
        if symbol not in _price_cache:
            _price_cache[symbol] = random.uniform(500, 5000)

        prev_price = _price_cache[symbol]

        # 20% chance of a big move, otherwise small noise
        if random.random() < 0.2:
            change_pct = random.choice([-1, 1]) * random.uniform(threshold_pct, threshold_pct + 3)
        else:
            change_pct = random.uniform(-1, 1)

        curr_price = prev_price * (1 + change_pct / 100)
        _price_cache[symbol] = curr_price

        if abs(change_pct) >= threshold_pct:
            direction = "spike" if change_pct > 0 else "drop"
            alerts.append({
                "symbol": symbol,
                "prev_price": round(prev_price, 2),
                "curr_price": round(curr_price, 2),
                "change_pct": round(change_pct, 2),
                "direction": direction,
            })

    return alerts


def format_price_alert(alerts: list[dict]) -> str:
    """Format price alerts into an HTML message for Telegram."""
    if not alerts:
        return ""

    now = datetime.now(IST).strftime("%H:%M IST")
    lines = [f"🚨 <b>Price Alert</b> ({now})\n"]

    for a in alerts:
        emoji = "🚀" if a["direction"] == "spike" else "📉"
        sign = "+" if a["change_pct"] > 0 else ""

        lines.append(
            f"{emoji} <b>{a['symbol']}</b>  "
            f"₹{a['prev_price']:,.2f} → ₹{a['curr_price']:,.2f}  "
            f"({sign}{a['change_pct']}%)"
        )

    return "\n".join(lines)


def reset_cache():
    """Clear the price cache (useful for testing)."""
    _price_cache.clear()
