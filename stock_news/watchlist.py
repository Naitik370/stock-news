"""Self-managed alert watchlist — tracks stocks you want news for but don't own."""

import json
import os

from . import config
from .holdings import symbol_to_company


def _path() -> str:
    return os.path.join(config.BASE_DIR, "watchlist.json")


def load() -> list[str]:
    """Load watchlist symbols from disk."""
    path = _path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return [s.upper() for s in data if isinstance(s, str)]
    except (json.JSONDecodeError, IOError):
        return []


def _save(symbols: list[str]):
    """Persist watchlist to JSON."""
    path = _path()
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(sorted(set(s.upper() for s in symbols)), f, indent=2)
    os.replace(tmp, path)


def add(symbol: str) -> bool:
    """Add a symbol. Returns True if newly added, False if already present."""
    symbol = symbol.upper()
    current = load()
    if symbol in current:
        return False
    current.append(symbol)
    _save(current)
    return True


def remove(symbol: str) -> bool:
    """Remove a symbol. Returns True if removed, False if not found."""
    symbol = symbol.upper()
    current = load()
    if symbol not in current:
        return False
    current.remove(symbol)
    _save(current)
    return True


def get_as_holdings() -> list[dict]:
    """
    Convert watchlist into holding-like dicts (quantity=0) so they
    flow through the existing news pipeline seamlessly.
    """
    return [
        {
            "symbol": s,
            "company_name": symbol_to_company(s),
            "quantity": 0,
            "avg_price": 0,
            "last_price": 0,
            "close_price": 0,
            "pnl": 0,
            "day_change_pct": 0,
        }
        for s in load()
    ]
