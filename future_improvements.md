# 🚀 Stock News V2: Future Improvements

This document outlines potential high-value features for the next iteration of the Stock News Notification System.

## 🤖 1. Interactive Telegram Bot (2-Way Chat)
Convert the one-way notifier into an interactive bot.
* **`/portfolio` command:** Get an instant live P&L snapshot on demand without waiting for the 15-minute cycle.
* **`/news <SYMBOL>` command:** Fetch the absolute latest news for any specific stock (e.g., `/news INFY`).
* **`/mute <SYMBOL>` command:** Toggle noise filters directly from the Telegram chat instead of modifying the `.env` file.

## 🧠 2. AI Summaries & Sentiment Analysis
Integrate a free LLM API (like Google Gemini or OpenAI) to analyze articles.
* **Sentiment Tags:** Auto-tag every article as 🐂 **Bullish**, 🐻 **Bearish**, or 😐 **Neutral**.
* **TL;DR Generation:** Instead of just sending URLs, scrape the article text and send a concise 2-sentence summary (e.g., *"Reliance acquired a new solar company; expected to boost green energy revenue."*).

## 🎯 3. Price & Volume Alerts
Utilize the 15-minute Kite fetching cycle to track real-time prices.
* **Custom Targets:** Add `PRICE_ALERTS={"RELIANCE": {"above": 2600, "below": 2400}}` to `.env`. Get instant Telegram alerts if a stock hits your target.
* **Percentage Triggers:** Auto-alert if any holding jumps or crashes by >5% in a single day.

## 👀 4. Watchlist Integration
Expand tracking beyond just owned stocks.
* **Track Unowned Stocks:** Create a mechanism in config to track news and prices for stocks you are watching but don't currently have in your portfolio (e.g., tracking Zomato for a buy signal).

## 📅 5. Earnings Calendar Sync
Integrate with an upcoming earnings calendar to anticipate news.
* **Pre-Earnings Alerts:** Send reminders a day before: *"🔔 Reminder: TCS announces Q3 results tomorrow afternoon."*

## 📈 6. Simple Technical Indicators
Use historical data from Kite to identify technical flags.
* **Overbought/Oversold:** Alerts like *"⚠️ RELIANCE is currently Overbought (RSI > 75)"*.
* **Moving Averages:** Alerts like *"🚀 INFY just crossed its 50-day moving average"*.
