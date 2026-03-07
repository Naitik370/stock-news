"""Tests for deduplication module."""

import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock_news import config
from stock_news.dedup import filter_new, mark_sent, reset, _url_hash


class TestUrlHash:
    def test_consistent(self):
        """Same URL always produces the same hash."""
        h1 = _url_hash("https://example.com/article-1")
        h2 = _url_hash("https://example.com/article-1")
        assert h1 == h2

    def test_different_urls_different_hashes(self):
        h1 = _url_hash("https://example.com/article-1")
        h2 = _url_hash("https://example.com/article-2")
        assert h1 != h2

    def test_hash_length(self):
        h = _url_hash("https://example.com")
        assert len(h) == 16


class TestDedup:
    def setup_method(self):
        """Use a temp file for each test."""
        self._tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self._tmp.close()
        self._original = config.SEEN_NEWS_FILE
        config.SEEN_NEWS_FILE = self._tmp.name
        # Start clean
        if os.path.exists(self._tmp.name):
            os.remove(self._tmp.name)

    def teardown_method(self):
        config.SEEN_NEWS_FILE = self._original
        if os.path.exists(self._tmp.name):
            os.remove(self._tmp.name)

    def _make_articles(self, urls):
        return {
            "TEST": [{"url": url, "title": f"Article {i}"} for i, url in enumerate(urls)]
        }

    def test_all_new_on_first_run(self):
        articles = self._make_articles(["https://a.com/1", "https://a.com/2"])
        result = filter_new(articles)
        assert len(result["TEST"]) == 2

    def test_none_new_after_mark_sent(self):
        articles = self._make_articles(["https://a.com/1"])
        mark_sent(articles)
        result = filter_new(articles)
        assert len(result) == 0

    def test_mixed_new_and_old(self):
        old = self._make_articles(["https://a.com/old"])
        mark_sent(old)

        mixed = self._make_articles(["https://a.com/old", "https://a.com/new"])
        result = filter_new(mixed)
        assert len(result["TEST"]) == 1
        assert result["TEST"][0]["url"] == "https://a.com/new"

    def test_reset_clears_history(self):
        articles = self._make_articles(["https://a.com/1"])
        mark_sent(articles)

        reset()

        result = filter_new(articles)
        assert len(result["TEST"]) == 1

    def test_seen_file_is_valid_json(self):
        articles = self._make_articles(["https://a.com/1"])
        mark_sent(articles)

        with open(config.SEEN_NEWS_FILE, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict)
        assert len(data) == 1
