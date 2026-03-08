"""Tests for ai_summary module."""

import sys
import os
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from stock_news.ai_summary import (
    enrich_articles,
    _build_prompt,
    _parse_response,
    _sentiment_emoji,
)


# ── Helpers ───────────────────────────────────────────────────────────

def _sample_articles():
    return {
        "RELIANCE": [
            {
                "title": "Reliance Q3 results beat estimates",
                "source": "Economic Times",
                "url": "https://example.com/article1",
                "published_at_ist": "2026-03-08 10:00 IST",
                "priority": "urgent",
                "priority_emoji": "🔴",
            },
        ],
        "TCS": [
            {
                "title": "TCS lays off 2000 employees",
                "source": "Moneycontrol",
                "url": "https://example.com/article2",
                "published_at_ist": "2026-03-08 11:00 IST",
                "priority": "normal",
                "priority_emoji": "⚪",
            },
        ],
    }


# ── Unit tests ────────────────────────────────────────────────────────

class TestSentimentEmoji:
    def test_bullish(self):
        assert _sentiment_emoji("bullish") == "🐂"

    def test_bearish(self):
        assert _sentiment_emoji("bearish") == "🐻"

    def test_neutral(self):
        assert _sentiment_emoji("neutral") == "😐"

    def test_unknown(self):
        assert _sentiment_emoji("unknown") == "😐"


class TestBuildPrompt:
    def test_contains_headlines(self):
        articles = _sample_articles()
        flat = []
        for arts in articles.values():
            flat.extend(arts)
        prompt = _build_prompt(flat)
        assert "Reliance Q3 results" in prompt
        assert "TCS lays off" in prompt

    def test_contains_urls(self):
        articles = _sample_articles()
        flat = []
        for arts in articles.values():
            flat.extend(arts)
        prompt = _build_prompt(flat)
        assert "https://example.com/article1" in prompt

    def test_indexed(self):
        articles = _sample_articles()
        flat = []
        for arts in articles.values():
            flat.extend(arts)
        prompt = _build_prompt(flat)
        assert "[0]" in prompt
        assert "[1]" in prompt


class TestParseResponse:
    def test_valid_json(self):
        text = json.dumps([
            {"index": 0, "sentiment": "bullish", "summary": "Great results"},
            {"index": 1, "sentiment": "bearish", "summary": "Layoffs announced"},
        ])
        result = _parse_response(text, 2)
        assert result is not None
        assert len(result) == 2

    def test_with_code_fences(self):
        text = '```json\n[{"index": 0, "sentiment": "neutral", "summary": "Test"}]\n```'
        result = _parse_response(text, 1)
        assert result is not None
        assert len(result) == 1

    def test_invalid_json(self):
        result = _parse_response("not json at all", 1)
        assert result is None

    def test_non_array(self):
        result = _parse_response('{"key": "value"}', 1)
        assert result is None


class TestEnrichArticles:
    @patch("stock_news.ai_summary.config")
    def test_skips_without_api_key(self, mock_config):
        mock_config.GEMINI_API_KEY = ""
        articles = _sample_articles()
        result = enrich_articles(articles)
        # Articles should be unchanged — no ai_summary key
        assert "ai_summary" not in result["RELIANCE"][0]

    @patch("stock_news.ai_summary.genai")
    @patch("stock_news.ai_summary.config")
    def test_enriches_with_valid_response(self, mock_config, mock_genai):
        mock_config.GEMINI_API_KEY = "test-key"

        # Mock Gemini response
        mock_response = MagicMock()
        mock_response.text = json.dumps([
            {"index": 0, "sentiment": "bullish", "summary": "Strong quarterly results."},
            {"index": 1, "sentiment": "bearish", "summary": "Major layoffs signal trouble."},
        ])
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        articles = _sample_articles()
        result = enrich_articles(articles)

        assert result["RELIANCE"][0]["ai_sentiment"] == "bullish"
        assert result["RELIANCE"][0]["ai_sentiment_emoji"] == "🐂"
        assert "Strong quarterly" in result["RELIANCE"][0]["ai_summary"]
        assert result["TCS"][0]["ai_sentiment"] == "bearish"

    @patch("stock_news.ai_summary.genai")
    @patch("stock_news.ai_summary.config")
    def test_graceful_on_api_error(self, mock_config, mock_genai):
        mock_config.GEMINI_API_KEY = "test-key"
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API rate limit")
        mock_genai.Client.return_value = mock_client

        articles = _sample_articles()
        result = enrich_articles(articles)
        # Articles should be unchanged
        assert "ai_summary" not in result["RELIANCE"][0]

    @patch("stock_news.ai_summary.genai")
    @patch("stock_news.ai_summary.config")
    def test_graceful_on_bad_json(self, mock_config, mock_genai):
        mock_config.GEMINI_API_KEY = "test-key"
        mock_response = MagicMock()
        mock_response.text = "This is not valid JSON"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        articles = _sample_articles()
        result = enrich_articles(articles)
        assert "ai_summary" not in result["RELIANCE"][0]
