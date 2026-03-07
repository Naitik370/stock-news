"""Tests for the portfolio summary calculator."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock_news.portfolio import compute_summary, format_summary


class TestComputeSummary:
    def test_empty_holdings(self):
        result = compute_summary([])
        assert result["total_investment"] == 0
        assert result["current_value"] == 0
        assert result["top_gainer"] is None

    def test_skips_zero_quantity(self):
        """Extra stocks (quantity=0) should not affect portfolio."""
        holdings = [
            {"symbol": "RELIANCE", "quantity": 0, "avg_price": 2400,
             "last_price": 2500, "close_price": 2400, "pnl": 0, "day_change_pct": 0},
        ]
        result = compute_summary(holdings)
        assert result["total_investment"] == 0

    def test_correct_totals(self):
        holdings = [
            {"symbol": "RELIANCE", "quantity": 10, "avg_price": 2400, "last_price": 2550,
             "close_price": 2500, "pnl": 1500, "day_change_pct": 2.0},
            {"symbol": "INFY", "quantity": 20, "avg_price": 1400, "last_price": 1380,
             "close_price": 1410, "pnl": -400, "day_change_pct": -2.13},
        ]
        result = compute_summary(holdings)

        assert result["total_investment"] == 10 * 2400 + 20 * 1400  # 52000
        assert result["current_value"] == 10 * 2550 + 20 * 1380  # 53100
        assert result["total_pnl"] == 53100 - 52000  # 1100
        assert result["top_gainer"]["symbol"] == "RELIANCE"
        assert result["top_loser"]["symbol"] == "INFY"

    def test_day_pnl(self):
        holdings = [
            {"symbol": "TCS", "quantity": 5, "avg_price": 3500, "last_price": 3650,
             "close_price": 3600, "pnl": 750, "day_change_pct": 1.39},
        ]
        result = compute_summary(holdings)
        # day_pnl = (3650 - 3600) * 5 = 250
        assert result["day_pnl"] == 250

    def test_single_stock_gainer_loser_same(self):
        """With one stock, top gainer and loser are the same."""
        holdings = [
            {"symbol": "TCS", "quantity": 5, "avg_price": 3500, "last_price": 3650,
             "close_price": 3600, "pnl": 750, "day_change_pct": 1.39},
        ]
        result = compute_summary(holdings)
        assert result["top_gainer"]["symbol"] == "TCS"
        assert result["top_loser"]["symbol"] == "TCS"


class TestFormatSummary:
    def test_empty_portfolio(self):
        summary = compute_summary([])
        text = format_summary(summary)
        assert "No holdings data" in text

    def test_contains_currency(self):
        holdings = [
            {"symbol": "RELIANCE", "quantity": 10, "avg_price": 2400, "last_price": 2550,
             "close_price": 2500, "pnl": 1500, "day_change_pct": 2.0},
        ]
        summary = compute_summary(holdings)
        text = format_summary(summary)
        assert "₹" in text
        assert "📊" in text

    def test_negative_pnl_shows_minus(self):
        holdings = [
            {"symbol": "INFY", "quantity": 10, "avg_price": 1500, "last_price": 1400,
             "close_price": 1450, "pnl": -1000, "day_change_pct": -3.45},
        ]
        summary = compute_summary(holdings)
        text = format_summary(summary)
        assert "-" in text
