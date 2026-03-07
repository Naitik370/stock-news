"""Tests for notifier module."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock_news.notifier import format_news_message, _escape_html


class TestEscapeHtml:
    def test_ampersand(self):
        assert _escape_html("A&B") == "A&amp;B"

    def test_angle_brackets(self):
        assert _escape_html("<script>") == "&lt;script&gt;"

    def test_no_escape_needed(self):
        assert _escape_html("Hello World") == "Hello World"

    def test_mixed(self):
        assert _escape_html("A&B <C> D") == "A&amp;B &lt;C&gt; D"


class TestFormatNewsMessage:
    def _sample_articles(self):
        return {
            "RELIANCE": [
                {
                    "title": "Reliance Q3 results",
                    "source": "Economic Times",
                    "url": "https://example.com/article1",
                    "published_at_ist": "2026-03-08 10:00 IST",
                    "priority": "urgent",
                    "priority_emoji": "🔴",
                },
            ],
            "TCS": [
                {
                    "title": "TCS wins deal",
                    "source": "Moneycontrol",
                    "url": "https://example.com/article2",
                    "published_at_ist": "2026-03-08 11:00 IST",
                    "priority": "normal",
                    "priority_emoji": "⚪",
                },
            ],
        }

    def test_contains_stock_headers(self):
        msg = format_news_message(self._sample_articles())
        assert "RELIANCE" in msg
        assert "TCS" in msg

    def test_contains_headlines(self):
        msg = format_news_message(self._sample_articles())
        assert "Reliance Q3 results" in msg
        assert "TCS wins deal" in msg

    def test_contains_priority_emojis(self):
        msg = format_news_message(self._sample_articles())
        assert "🔴" in msg
        assert "⚪" in msg

    def test_contains_links(self):
        msg = format_news_message(self._sample_articles())
        assert "https://example.com/article1" in msg
        assert "Read more" in msg

    def test_with_portfolio_summary(self):
        msg = format_news_message(self._sample_articles(), "📊 Portfolio: ₹1,00,000")
        assert "Portfolio" in msg

    def test_without_portfolio_summary(self):
        msg = format_news_message(self._sample_articles(), "")
        assert "Stock News Alert" in msg

    def test_html_escapes_titles(self):
        """Titles with special chars should be HTML-safe."""
        articles = {
            "TEST": [{
                "title": "Revenue > $1B & growing",
                "source": "Test",
                "url": "https://example.com",
                "published_at_ist": "now",
                "priority": "normal",
                "priority_emoji": "⚪",
            }]
        }
        msg = format_news_message(articles)
        assert "&amp;" in msg
        assert "&gt;" in msg

    def test_empty_articles(self):
        msg = format_news_message({})
        assert "Stock News Alert" in msg


class TestFormatNewsMessagePortfolioEscaped:
    def test_portfolio_with_special_chars(self):
        """Portfolio summary containing & or < should be escaped."""
        articles = {
            "TEST": [{
                "title": "Test", "source": "Test", "url": "https://example.com",
                "published_at_ist": "now", "priority": "normal", "priority_emoji": "⚪",
            }]
        }
        msg = format_news_message(articles, "P&L <summary>")
        assert "P&amp;L" in msg
        assert "&lt;summary&gt;" in msg
