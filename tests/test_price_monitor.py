"""Tests for price_monitor module."""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock_news import price_monitor, config

@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the price cache before each test."""
    price_monitor.reset_cache()
    yield
    price_monitor.reset_cache()


def test_check_prices_no_previous():
    kite = MagicMock()
    kite.ltp.return_value = {"NSE:RELIANCE": {"last_price": 2500.0}}

    # First check shouldn't alert, just caches
    alerts = price_monitor.check_prices(kite, ["RELIANCE"], threshold_pct=3.0)
    assert not alerts
    assert price_monitor._price_cache["RELIANCE"] == 2500.0


def test_check_prices_below_threshold():
    price_monitor._price_cache["RELIANCE"] = 2500.0
    kite = MagicMock()
    kite.ltp.return_value = {"NSE:RELIANCE": {"last_price": 2550.0}} # +2%

    alerts = price_monitor.check_prices(kite, ["RELIANCE"], threshold_pct=3.0)
    assert not alerts


def test_check_prices_spike():
    price_monitor._price_cache["RELIANCE"] = 2500.0
    kite = MagicMock()
    kite.ltp.return_value = {"NSE:RELIANCE": {"last_price": 2600.0}} # +4%

    alerts = price_monitor.check_prices(kite, ["RELIANCE"], threshold_pct=3.0)
    assert len(alerts) == 1
    assert alerts[0]["symbol"] == "RELIANCE"
    assert alerts[0]["direction"] == "spike"
    assert alerts[0]["change_pct"] == 4.0


def test_check_prices_drop():
    price_monitor._price_cache["TCS"] = 3000.0
    kite = MagicMock()
    kite.ltp.return_value = {"NSE:TCS": {"last_price": 2850.0}} # -5%

    alerts = price_monitor.check_prices(kite, ["TCS"], threshold_pct=3.0)
    assert len(alerts) == 1
    assert alerts[0]["symbol"] == "TCS"
    assert alerts[0]["direction"] == "drop"
    assert alerts[0]["change_pct"] == -5.0


def test_check_prices_api_error():
    kite = MagicMock()
    kite.ltp.side_effect = Exception("API down")

    alerts = price_monitor.check_prices(kite, ["RELIANCE"])
    assert not alerts


def test_format_price_alert():
    alerts = [
        {"symbol": "RELIANCE", "prev_price": 2500.0, "curr_price": 2600.0, "change_pct": 4.0, "direction": "spike"},
        {"symbol": "TCS", "prev_price": 3000.0, "curr_price": 2850.0, "change_pct": -5.0, "direction": "drop"},
    ]
    msg = price_monitor.format_price_alert(alerts)
    assert "🚀" in msg
    assert "📉" in msg
    assert "RELIANCE" in msg
    assert "+4.0%" in msg
    assert "-5.0%" in msg
