"""Tests for holdings module."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock_news.holdings import symbol_to_company, get_mock_holdings


class TestSymbolToCompany:
    def test_known_symbol(self):
        assert symbol_to_company("RELIANCE") == "Reliance Industries"
        assert symbol_to_company("TCS") == "Tata Consultancy Services"
        assert symbol_to_company("INFY") == "Infosys"

    def test_case_insensitive(self):
        assert symbol_to_company("reliance") == "Reliance Industries"
        assert symbol_to_company("Tcs") == "Tata Consultancy Services"

    def test_unknown_symbol_returns_itself(self):
        assert symbol_to_company("XYZUNKNOWN") == "XYZUNKNOWN"

    def test_special_symbols(self):
        assert symbol_to_company("M&M") == "Mahindra and Mahindra"
        assert symbol_to_company("BAJAJ-AUTO") == "Bajaj Auto"


class TestMockHoldings:
    def test_returns_list(self):
        holdings = get_mock_holdings()
        assert isinstance(holdings, list)
        assert len(holdings) == 5

    def test_has_required_fields(self):
        holdings = get_mock_holdings()
        required = ["symbol", "company_name", "quantity", "avg_price",
                     "last_price", "close_price", "pnl", "day_change_pct"]
        for h in holdings:
            for field in required:
                assert field in h, f"Missing field: {field} in {h['symbol']}"

    def test_day_change_pct_calculated(self):
        holdings = get_mock_holdings()
        for h in holdings:
            if h["close_price"] > 0:
                expected = round(((h["last_price"] - h["close_price"]) / h["close_price"]) * 100, 2)
                assert h["day_change_pct"] == expected, f"Wrong day_change_pct for {h['symbol']}"

    def test_company_names_mapped(self):
        holdings = get_mock_holdings()
        for h in holdings:
            assert h["company_name"] != h["symbol"], f"{h['symbol']} should be mapped to a company name"
