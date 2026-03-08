"""Tests for watchlist module."""

import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch
from stock_news import watchlist


class TestWatchlist:
    def _tmp_watchlist(self, tmp_path):
        """Patch the watchlist file to use a temp path."""
        return patch.object(watchlist, "_path", return_value=str(tmp_path / "watchlist.json"))

    def test_load_empty(self, tmp_path):
        with self._tmp_watchlist(tmp_path):
            assert watchlist.load() == []

    def test_add_and_load(self, tmp_path):
        with self._tmp_watchlist(tmp_path):
            assert watchlist.add("ZOMATO") is True
            assert "ZOMATO" in watchlist.load()

    def test_add_duplicate(self, tmp_path):
        with self._tmp_watchlist(tmp_path):
            watchlist.add("ZOMATO")
            assert watchlist.add("ZOMATO") is False
            assert watchlist.load().count("ZOMATO") == 1

    def test_add_case_insensitive(self, tmp_path):
        with self._tmp_watchlist(tmp_path):
            watchlist.add("zomato")
            assert "ZOMATO" in watchlist.load()

    def test_remove(self, tmp_path):
        with self._tmp_watchlist(tmp_path):
            watchlist.add("ZOMATO")
            assert watchlist.remove("ZOMATO") is True
            assert "ZOMATO" not in watchlist.load()

    def test_remove_not_found(self, tmp_path):
        with self._tmp_watchlist(tmp_path):
            assert watchlist.remove("ZOMATO") is False

    def test_get_as_holdings(self, tmp_path):
        with self._tmp_watchlist(tmp_path):
            watchlist.add("RELIANCE")
            watchlist.add("ZOMATO")
            holdings = watchlist.get_as_holdings()
            assert len(holdings) == 2
            for h in holdings:
                assert h["quantity"] == 0
                assert "symbol" in h
                assert "company_name" in h

    def test_get_as_holdings_has_company_names(self, tmp_path):
        with self._tmp_watchlist(tmp_path):
            watchlist.add("RELIANCE")
            holdings = watchlist.get_as_holdings()
            assert holdings[0]["company_name"] == "Reliance Industries"

    def test_persists_to_file(self, tmp_path):
        wl_file = tmp_path / "watchlist.json"
        with self._tmp_watchlist(tmp_path):
            watchlist.add("TCS")
            watchlist.add("INFY")
            with open(wl_file) as f:
                data = json.load(f)
            assert "INFY" in data
            assert "TCS" in data
