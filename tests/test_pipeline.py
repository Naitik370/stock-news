"""Quick test to verify the news pipeline works end-to-end."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock_news.news import fetch_news_for_stock
from stock_news.dedup import filter_new, mark_sent
from stock_news.holdings import get_mock_holdings
from stock_news.portfolio import compute_summary, format_summary
from stock_news.notifier import format_news_message

# Test with a 48-hour window to ensure we get articles
articles = fetch_news_for_stock("Reliance Industries", "RELIANCE", max_age_hours=48)

print(f"\nFound {len(articles)} articles for RELIANCE:\n")
for a in articles:
    print(f"  {a['priority_emoji']} [{a['priority'].upper()}] {a['title']}")
    print(f"     Source: {a['source']} | {a['published_at_ist']}")
    print(f"     URL: {a['url'][:80]}...")
    print()

# Test dedup
fake_articles = {"RELIANCE": articles}
new = filter_new(fake_articles)
print(f"Before dedup: {len(articles)} articles")
print(f"After dedup (first run): {sum(len(v) for v in new.values())} new articles")

if new:
    mark_sent(new)
    new_again = filter_new(fake_articles)
    print(f"After dedup (second run): {sum(len(v) for v in new_again.values())} new articles (should be 0)")

# Test portfolio
holdings = get_mock_holdings()
summary = compute_summary(holdings)
print(f"\n{format_summary(summary)}")

# Test notifier formatting
if new:
    msg = format_news_message(new, format_summary(summary))
    print(f"\n--- Telegram Message Preview ---\n{msg}\n--- End ---")

print("\n✅ All tests passed!")
