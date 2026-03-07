"""Tests for news module."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock_news.news import _score_priority, _priority_emoji, _parse_title


class TestScorePriority:
    def test_urgent_keywords(self):
        assert _score_priority("Reliance Q3 results beat estimates") == "urgent"
        assert _score_priority("SEBI investigation into company") == "urgent"
        assert _score_priority("Company hit with fraud charges") == "urgent"
        assert _score_priority("Stock market crash today") == "urgent"
        assert _score_priority("Company earnings report released") == "urgent"

    def test_important_keywords(self):
        assert _score_priority("Company announces acquisition deal") == "important"
        assert _score_priority("Dividend declared for shareholders") == "important"
        assert _score_priority("Board approves buyback plan") == "important"
        assert _score_priority("Stock target price raised") == "important"
        assert _score_priority("Merger talks underway") == "important"

    def test_normal(self):
        assert _score_priority("Reliance Industries shares trade flat") == "normal"
        assert _score_priority("Stock market update today") == "normal"

    def test_case_insensitive(self):
        assert _score_priority("RELIANCE RESULTS") == "urgent"
        assert _score_priority("Acquisition News") == "important"

    def test_urgent_beats_important(self):
        """If both urgent and important keywords present, urgent wins."""
        assert _score_priority("Fraud investigation leads to acquisition freeze") == "urgent"


class TestPriorityEmoji:
    def test_emojis(self):
        assert _priority_emoji("urgent") == "🔴"
        assert _priority_emoji("important") == "🟡"
        assert _priority_emoji("normal") == "⚪"
        assert _priority_emoji("unknown") == "⚪"


class TestParseTitle:
    def test_standard_format(self):
        headline, source = _parse_title("Reliance shares rise 2% - Economic Times")
        assert headline == "Reliance shares rise 2%"
        assert source == "Economic Times"

    def test_multiple_dashes(self):
        """Should split on the LAST dash only."""
        headline, source = _parse_title("Q3 results - strong growth - Moneycontrol")
        assert headline == "Q3 results - strong growth"
        assert source == "Moneycontrol"

    def test_no_dash(self):
        headline, source = _parse_title("Just a headline without source")
        assert headline == "Just a headline without source"
        assert source == "Unknown"

    def test_empty_string(self):
        headline, source = _parse_title("")
        assert headline == ""
        assert source == "Unknown"
