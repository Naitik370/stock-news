"""Tests for news_logger module."""

import sys
import os
import csv
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock_news import config
from stock_news.news_logger import log_articles


class TestNewsLogger:
    def setup_method(self):
        self._tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        self._tmp.close()
        self._original = config.NEWS_LOG_FILE
        config.NEWS_LOG_FILE = self._tmp.name
        # Start clean
        if os.path.exists(self._tmp.name):
            os.remove(self._tmp.name)

    def teardown_method(self):
        config.NEWS_LOG_FILE = self._original
        if os.path.exists(self._tmp.name):
            os.remove(self._tmp.name)

    def test_creates_file_with_headers(self):
        articles = {
            "RELIANCE": [{
                "title": "Test headline",
                "source": "Test Source",
                "url": "https://example.com",
                "priority": "urgent",
            }]
        }
        log_articles(articles)

        with open(config.NEWS_LOG_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert "timestamp_ist" in headers
            assert "stock" in headers
            assert "headline" in headers

    def test_appends_articles(self):
        articles = {
            "RELIANCE": [
                {"title": "Article 1", "source": "S1", "url": "https://a.com/1", "priority": "urgent"},
                {"title": "Article 2", "source": "S2", "url": "https://a.com/2", "priority": "normal"},
            ]
        }
        log_articles(articles)

        with open(config.NEWS_LOG_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
        # 1 header + 2 data rows
        assert len(rows) == 3

    def test_multiple_calls_append(self):
        a1 = {"RELIANCE": [{"title": "A1", "source": "S", "url": "https://a.com/1", "priority": "normal"}]}
        a2 = {"TCS": [{"title": "A2", "source": "S", "url": "https://a.com/2", "priority": "important"}]}

        log_articles(a1)
        log_articles(a2)

        with open(config.NEWS_LOG_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
        # 1 header + 2 data rows
        assert len(rows) == 3

    def test_empty_does_nothing(self):
        log_articles({})
        assert not os.path.exists(config.NEWS_LOG_FILE)
