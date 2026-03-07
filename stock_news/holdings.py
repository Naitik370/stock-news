"""Fetch and map Kite holdings to company names."""

import time
from datetime import datetime, timezone, timedelta
from kiteconnect import KiteConnect

from . import config

IST = timezone(timedelta(hours=5, minutes=30))

# ── NSE symbol → company name mapping ──
# This helps Google News find more relevant articles.
# Add more mappings as needed — unknown symbols use the tradingsymbol as-is.
SYMBOL_MAP = {
    "RELIANCE": "Reliance Industries",
    "TCS": "Tata Consultancy Services",
    "INFY": "Infosys",
    "HDFCBANK": "HDFC Bank",
    "ICICIBANK": "ICICI Bank",
    "HINDUNILVR": "Hindustan Unilever",
    "ITC": "ITC Limited",
    "SBIN": "State Bank of India",
    "BHARTIARTL": "Bharti Airtel",
    "KOTAKBANK": "Kotak Mahindra Bank",
    "LT": "Larsen and Toubro",
    "AXISBANK": "Axis Bank",
    "WIPRO": "Wipro",
    "HCLTECH": "HCL Technologies",
    "ADANIENT": "Adani Enterprises",
    "ADANIPORTS": "Adani Ports",
    "TATAMOTORS": "Tata Motors",
    "TATASTEEL": "Tata Steel",
    "MARUTI": "Maruti Suzuki",
    "SUNPHARMA": "Sun Pharma",
    "BAJFINANCE": "Bajaj Finance",
    "BAJFINSV": "Bajaj Finserv",
    "TITAN": "Titan Company",
    "ASIANPAINT": "Asian Paints",
    "NESTLEIND": "Nestle India",
    "ULTRACEMCO": "UltraTech Cement",
    "TECHM": "Tech Mahindra",
    "POWERGRID": "Power Grid Corporation",
    "NTPC": "NTPC Limited",
    "ONGC": "Oil and Natural Gas Corporation",
    "JSWSTEEL": "JSW Steel",
    "COALINDIA": "Coal India",
    "BPCL": "Bharat Petroleum",
    "IOC": "Indian Oil Corporation",
    "GRASIM": "Grasim Industries",
    "CIPLA": "Cipla",
    "DRREDDY": "Dr Reddys Laboratories",
    "DIVISLAB": "Divis Laboratories",
    "EICHERMOT": "Eicher Motors",
    "HEROMOTOCO": "Hero MotoCorp",
    "BAJAJ-AUTO": "Bajaj Auto",
    "M&M": "Mahindra and Mahindra",
    "BRITANNIA": "Britannia Industries",
    "TATACONSUM": "Tata Consumer Products",
    "APOLLOHOSP": "Apollo Hospitals",
    "INDUSINDBK": "IndusInd Bank",
    "SBILIFE": "SBI Life Insurance",
    "HDFCLIFE": "HDFC Life Insurance",
    "IRFC": "Indian Railway Finance Corporation",
    "IRCTC": "IRCTC",
    "ZOMATO": "Zomato",
    "PAYTM": "Paytm One97",
    "NYKAA": "Nykaa FSN E-Commerce",
    "DELHIVERY": "Delhivery",
    "POLICYBZR": "PB Fintech PolicyBazaar",
    "SAIL": "Steel Authority of India",
    "IDEA": "Vodafone Idea",
    "VEDL": "Vedanta Limited",
    "TATAPOWER": "Tata Power",
    "BANKBARODA": "Bank of Baroda",
    "PNB": "Punjab National Bank",
    "CANBK": "Canara Bank",
    "RECLTD": "REC Limited",
    "PFC": "Power Finance Corporation",
    "HAL": "Hindustan Aeronautics",
    "BEL": "Bharat Electronics",
    "NHPC": "NHPC Limited",
}

# ── Cache ──
_holdings_cache = {"data": None, "timestamp": None}
_CACHE_TTL_SECONDS = 3600  # 1 hour


def symbol_to_company(symbol: str) -> str:
    """Map NSE trading symbol to a human-readable company name."""
    return SYMBOL_MAP.get(symbol.upper(), symbol)


def fetch_holdings(kite: KiteConnect) -> list[dict]:
    """
    Fetch holdings from Kite Connect.
    Returns a list of dicts with symbol, company_name, quantity, avg_price,
    last_price, pnl, day_change_pct, close_price.
    Raw results are cached for 1 hour; MUTE/EXTRA applied on every call.
    """
    now = time.time()

    # Return cached raw holdings if fresh
    if (_holdings_cache["data"] is not None
            and _holdings_cache["timestamp"]
            and (now - _holdings_cache["timestamp"]) < _CACHE_TTL_SECONDS):
        raw_data = _holdings_cache["data"]
    else:
        raw_holdings = kite.holdings()

        raw_data = []
        for h in raw_holdings:
            symbol = h.get("tradingsymbol", "")
            last_price = h.get("last_price", 0)
            close_price = h.get("close_price", 0)

            # Day change percentage
            if close_price and close_price > 0:
                day_change_pct = ((last_price - close_price) / close_price) * 100
            else:
                day_change_pct = 0.0

            raw_data.append({
                "symbol": symbol,
                "company_name": symbol_to_company(symbol),
                "quantity": h.get("quantity", 0),
                "avg_price": h.get("average_price", 0),
                "last_price": last_price,
                "close_price": close_price,
                "pnl": h.get("pnl", 0),
                "day_change_pct": round(day_change_pct, 2),
            })

        # Update cache with unfiltered data
        _holdings_cache["data"] = raw_data
        _holdings_cache["timestamp"] = now

    # Apply MUTE/EXTRA on every call (not cached)
    holdings = list(raw_data)

    if config.MUTE_STOCKS:
        holdings = [h for h in holdings if h["symbol"].upper() not in config.MUTE_STOCKS]

    for extra in config.EXTRA_STOCKS:
        symbol = extra.strip().upper()
        if not any(h["symbol"].upper() == symbol for h in holdings):
            holdings.append({
                "symbol": symbol,
                "company_name": symbol_to_company(symbol),
                "quantity": 0,
                "avg_price": 0,
                "last_price": 0,
                "close_price": 0,
                "pnl": 0,
                "day_change_pct": 0,
            })

    return holdings


def get_mock_holdings() -> list[dict]:
    """Return sample holdings for testing without Kite credentials."""
    mock = [
        {"symbol": "RELIANCE", "quantity": 10, "avg_price": 2400, "last_price": 2550,
         "close_price": 2500, "pnl": 1500},
        {"symbol": "TCS", "quantity": 5, "avg_price": 3500, "last_price": 3650,
         "close_price": 3600, "pnl": 750},
        {"symbol": "INFY", "quantity": 20, "avg_price": 1400, "last_price": 1380,
         "close_price": 1410, "pnl": -400},
        {"symbol": "HDFCBANK", "quantity": 8, "avg_price": 1550, "last_price": 1620,
         "close_price": 1600, "pnl": 560},
        {"symbol": "TATAMOTORS", "quantity": 15, "avg_price": 650, "last_price": 680,
         "close_price": 670, "pnl": 450},
    ]
    for h in mock:
        h["company_name"] = symbol_to_company(h["symbol"])
        close = h["close_price"]
        last = h["last_price"]
        h["day_change_pct"] = round(((last - close) / close) * 100, 2) if close else 0

    return mock
