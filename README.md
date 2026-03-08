# Stock News Notification System

Real-time stock news alerts for your Zerodha Kite portfolio, delivered to Telegram every 15 minutes.

## Features

- 📈 **Kite Holdings** — Fetches your live portfolio via Kite Connect API
- 📰 **Google News RSS** — Real-time news, no API key needed
- 🔴🟡⚪ **Priority Scoring** — Urgent/Important/Normal tags on headlines
- 📊 **Portfolio P&L** — Daily summary with top gainer/loser
- 🔔 **Telegram Notifications** — Rich formatted alerts with links
- 🤖 **Interactive Bot** — `/portfolio`, `/news`, `/stocks`, `/mute`, `/watch` commands
- 🧠 **AI Summaries** — Sentiment tags (🐂/🐻/😐) + TL;DR via Gemini
- 🚀 **Price Spike Alerts** — Auto-detects fast moves (±3%) every 5 mins
- 🔄 **Deduplication** — Only sends genuinely new articles
- 📝 **CSV Logging** — Local history in `news_log.csv`
- ⏰ **Scheduler** — Runs every 15 min during market hours (Mon–Fri 9–4 IST)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

You'll need:
- **Kite Connect**: API key + secret from [developers.kite.trade](https://developers.kite.trade)
- **Zerodha**: User ID, password, TOTP secret
- **Telegram**: Bot token from @BotFather + your chat_id

### 3. Get Your Telegram Chat ID

Send any message to your bot, then run:

```bash
python main.py --setup
```

Add the printed `chat_id` to your `.env` file.

### 4. Test with Mock Data

```bash
python main.py --mock --once
```

This runs a full cycle with sample holdings (RELIANCE, TCS, INFY, HDFCBANK, TATAMOTORS) — no Kite login needed.

### 5. Run Live

```bash
python main.py
```

This will:
1. Auto-login to Kite using TOTP
2. Fetch your holdings
3. Get news for each stock
4. Send Telegram alerts for new articles
5. Repeat every 15 minutes

## CLI Options

| Flag | Description |
|---|---|
| `--bot` | Start interactive Telegram bot mode |
| `--once` | Run one cycle and exit |
| `--mock` | Use sample holdings (no Kite needed) |
| `--setup` | Get your Telegram chat_id |
| `--reset-seen` | Clear dedup history |
| `--summary` | Force portfolio summary |

## Configuration (.env)

| Variable | Description | Default |
|---|---|---|
| `KITE_API_KEY` | Kite Connect API key | — |
| `KITE_API_SECRET` | Kite Connect API secret | — |
| `KITE_USER_ID` | Zerodha client ID | — |
| `KITE_PASSWORD` | Zerodha password | — |
| `KITE_TOTP_SECRET` | TOTP base32 secret | — |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | — |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID | — |
| `SCHEDULE_INTERVAL_MINUTES` | Run interval | `15` |
| `MARKET_HOURS_ONLY` | Only run 9AM–4PM Mon–Fri IST | `true` |
| `NEWS_MAX_ARTICLES` | Max articles per stock | `3` |
| `NEWS_MAX_AGE_HOURS` | Only news newer than X hours | `1` |
| `EXTRA_STOCKS` | Additional stocks (comma-separated) | — |
| `MUTE_STOCKS` | Stocks to ignore (comma-separated) | — |
| `GEMINI_API_KEY` | Google Gemini API key (optional, for AI summaries) | — |
| `PRICE_ALERT_PCT` | Threshold for price spike/drop alerts (%) | `3.0` |
| `PRICE_CHECK_INTERVAL`| How often to check for price spikes (mins) | `5` |

## Bot Mode (Interactive)

Start the interactive bot to send commands from Telegram:

```bash
python main.py --bot          # live Kite data
python main.py --bot --mock   # mock portfolio (no Kite needed)
```

| Command | Description |
|---|---|
| `/start` | Welcome message |
| `/help` | List all commands |
| `/portfolio` | Instant P&L snapshot |
| `/stocks` | List your portfolio symbols |
| `/news <SYMBOL>` | Latest news for a stock (e.g. `/news RELIANCE`) |
| `/mute <SYMBOL>` | Mute a stock from alerts |
| `/unmute <SYMBOL>` | Unmute a stock |
| `/muted` | Show muted stocks |
| `/watch <SYMBOL>` | Add stock to alert watchlist |
| `/unwatch <SYMBOL>` | Remove from watchlist |
| `/watchlist` | Show watchlisted stocks |

The bot also pushes scheduled news alerts automatically (same as push mode).

## Files Generated

| File | Purpose |
|---|---|
| `.kite_session` | Cached Kite access token (auto-managed) |
| `seen_news.json` | Dedup tracking (auto-pruned after 7 days) |
| `news_log.csv` | History of all sent articles |
| `muted_stocks.json` | Stocks muted via bot commands |
| `watchlist.json` | Alert watchlist stocks |

## Important Notes

- **Don't login to Kite Web/mobile** while the script is running — it invalidates the API session
- The TOTP secret is the base32 string from your 2FA setup (not the 6-digit code)
- Market hours are Mon–Fri 9:00–16:00 IST. Set `MARKET_HOURS_ONLY=false` to run anytime
