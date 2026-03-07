"""Tests for config module."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock_news import config


class TestConfig:
    def test_priority_keywords_are_lowercase(self):
        """All priority keywords should be lowercase for matching."""
        for kw in config.PRIORITY_URGENT:
            assert kw == kw.lower(), f"Urgent keyword '{kw}' should be lowercase"
        for kw in config.PRIORITY_IMPORTANT:
            assert kw == kw.lower(), f"Important keyword '{kw}' should be lowercase"

    def test_mute_stocks_are_uppercase(self):
        """Muted stocks should be uppercase for comparison."""
        for s in config.MUTE_STOCKS:
            assert s == s.upper(), f"Muted stock '{s}' should be uppercase"

    def test_paths_use_base_dir(self):
        assert config.KITE_SESSION_FILE.startswith(config.BASE_DIR)
        assert config.SEEN_NEWS_FILE.startswith(config.BASE_DIR)
        assert config.NEWS_LOG_FILE.startswith(config.BASE_DIR)

    def test_defaults(self):
        assert config.SCHEDULE_INTERVAL_MINUTES > 0
        assert config.NEWS_MAX_ARTICLES > 0
        assert config.NEWS_MAX_AGE_HOURS > 0
