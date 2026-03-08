# 🚀 Stock News V2: Future Improvements

This document outlines potential high-value features for the next iteration of the Stock News Notification System.

## ✅ 1. Interactive Telegram Bot (2-Way Chat)
~~Convert the one-way notifier into an interactive bot.~~
**Implemented!** Use `python main.py --bot` to start. Commands:
* **`/portfolio`** — Instant live P&L snapshot on demand.
* **`/stocks`** — List all portfolio symbols.
* **`/news <SYMBOL>`** — Fetch the latest news for any stock (e.g., `/news INFY`).
* **`/mute <SYMBOL>`** / **`/unmute <SYMBOL>`** — Toggle noise filters from Telegram.
* **`/muted`** — See currently muted stocks.

## ✅ 2. AI Summaries & Sentiment Analysis
~~Integrate a free LLM API to analyze articles.~~
**Implemented!** Add `GEMINI_API_KEY` to `.env` to enable. Uses Gemini 2.5 Flash Lite with Google Search grounding.
* **Sentiment Tags:** Every article auto-tagged as 🐂 **Bullish**, 🐻 **Bearish**, or 😐 **Neutral**
* **TL;DR Summaries:** Concise 1-2 sentence summaries from Gemini with web search context
* Works in both `/news` command and scheduled push alerts. Degrades gracefully if no API key.

## ✅ 3. Price & Volume Alerts
~~Utilize the 15-minute Kite fetching cycle to track real-time prices.~~
**Implemented!** Built a dedicated 5-minute polling cycle that detects price spikes or drops.
* **Price Monitor:** Compares live LTP against cached prices from 5 mins ago.
* **Auto-Alerts:** Triggers if a stock moves more than `PRICE_ALERT_PCT` (default ±3%).
* Covers all portfolio holdings and `watchlist.json` symbols.

## ✅ 4. Watchlist Integration
~~Expand tracking beyond just owned stocks.~~
**Implemented!** Use `/watch ZOMATO` to track stocks you don't own. Watchlisted stocks appear in news alerts automatically.
* **`/watch <SYMBOL>`** — Add to alert watchlist
* **`/unwatch <SYMBOL>`** — Remove from watchlist
* **`/watchlist`** — See all watchlisted stocks

## 📅 5. Earnings Calendar Sync
Integrate with an upcoming earnings calendar to anticipate news.
* **Pre-Earnings Alerts:** Send reminders a day before: *"🔔 Reminder: TCS announces Q3 results tomorrow afternoon."*

## 📈 6. Simple Technical Indicators
Use historical data from Kite to identify technical flags.
* **Overbought/Oversold:** Alerts like *"⚠️ RELIANCE is currently Overbought (RSI > 75)"*.
* **Moving Averages:** Alerts like *"🚀 INFY just crossed its 50-day moving average"*.
