"""
Stock News Notification System
Main orchestrator — fetches holdings, gets news, sends Telegram alerts.
Runs every 15 min during market hours.
"""

import argparse
import sys
from datetime import datetime, timezone, timedelta

from rich.console import Console
from rich.table import Table

from stock_news import config, dedup, holdings, news, news_logger, notifier, portfolio
from stock_news.kite_auth import get_kite_client, is_token_valid

console = Console()
IST = timezone(timedelta(hours=5, minutes=30))

# Track whether we've sent a portfolio summary today
_summary_sent_date = None

# Global kite client — so re-login propagates across cycles
_kite_client = None


def _is_market_hours(force_skip: bool = False) -> bool:
    """Check if current time is within market hours (Mon-Fri 9:00-16:00 IST)."""
    if force_skip or not config.MARKET_HOURS_ONLY:
        return True

    now = datetime.now(IST)

    # Monday=0, Sunday=6
    if now.weekday() >= 5:
        return False

    hour = now.hour
    return 9 <= hour < 16


def _print_news_table(articles_by_symbol: dict[str, list[dict]]):
    """Print a rich table of news articles to the console."""
    if not articles_by_symbol:
        console.print("[dim]No new articles to display.[/dim]")
        return

    table = Table(title="📰 Stock News", show_lines=True)
    table.add_column("Stock", style="cyan bold", width=12)
    table.add_column("Priority", width=4, justify="center")
    table.add_column("Headline", style="white")
    table.add_column("Source", style="dim")
    table.add_column("Time (IST)", style="dim", width=18)

    for symbol, articles in articles_by_symbol.items():
        for article in articles:
            table.add_row(
                symbol,
                article.get("priority_emoji", "⚪"),
                article.get("title", ""),
                article.get("source", ""),
                article.get("published_at_ist", ""),
            )

    console.print(table)


def run_cycle(use_mock: bool = False, force_summary: bool = False):
    """
    Execute one news-fetch cycle.

    Args:
        use_mock: Use mock holdings data
        force_summary: Force portfolio summary even if already sent today
    """
    global _summary_sent_date, _kite_client

    now = datetime.now(IST)
    console.print(f"\n[bold blue]{'='*50}[/bold blue]")
    console.print(f"[bold blue]  Cycle: {now.strftime('%Y-%m-%d %H:%M:%S IST')}[/bold blue]")
    console.print(f"[bold blue]{'='*50}[/bold blue]")

    # --- Step 1: Check market hours ---
    if not _is_market_hours(force_skip=use_mock):
        console.print("[dim]Outside market hours. Skipping.[/dim]")
        return

    # --- Step 2: Get holdings ---
    console.print("\n[bold]📂 Fetching holdings...[/bold]")
    if use_mock:
        stock_holdings = holdings.get_mock_holdings()
        console.print(f"  Using mock data: {len(stock_holdings)} stocks")
    else:
        if _kite_client is None:
            console.print("[red]  No Kite client. Cannot fetch holdings.[/red]")
            return

        # Check token validity
        if not is_token_valid(_kite_client):
            console.print("[yellow]  Token expired. Attempting re-login...[/yellow]")
            _kite_client = get_kite_client()
            if not _kite_client:
                console.print("[red]  Re-login failed![/red]")
                notifier.send_error_alert(
                    "Kite session expired and re-login failed. "
                    "Please check your credentials and restart the script."
                )
                return

        try:
            stock_holdings = holdings.fetch_holdings(_kite_client)
            console.print(f"  Found {len(stock_holdings)} stocks in portfolio")
        except Exception as e:
            console.print(f"[red]  Holdings fetch failed: {e}[/red]")
            notifier.send_error_alert(f"Holdings fetch failed: {e}")
            return

    # --- Step 3: Portfolio summary ---
    portfolio_text = ""
    today_str = now.strftime("%Y-%m-%d")
    should_send_summary = force_summary or _summary_sent_date != today_str

    if should_send_summary and any(h["quantity"] > 0 for h in stock_holdings):
        console.print("\n[bold]📊 Computing portfolio summary...[/bold]")
        summary = portfolio.compute_summary(stock_holdings)
        portfolio_text = portfolio.format_summary(summary)
        console.print(f"  {portfolio_text}")
        _summary_sent_date = today_str

    # --- Step 4: Fetch news ---
    console.print("\n[bold]📰 Fetching news...[/bold]")
    all_news = news.fetch_news(stock_holdings)

    if not all_news:
        console.print("[dim]  No recent news found for any stock.[/dim]")
        return

    total_articles = sum(len(v) for v in all_news.values())
    console.print(f"  Total articles found: {total_articles}")

    # --- Step 5: Dedup ---
    console.print("\n[bold]🔍 Checking for new articles...[/bold]")
    new_articles = dedup.filter_new(all_news)

    if not new_articles:
        console.print("[dim]  All articles already sent. Nothing new.[/dim]")
        return

    new_count = sum(len(v) for v in new_articles.values())
    console.print(f"  New articles: {new_count}")

    # --- Step 6: Display ---
    _print_news_table(new_articles)

    # --- Step 7: Send Telegram ---
    console.print("\n[bold]📤 Sending Telegram notification...[/bold]")
    sent = notifier.send_news_alert(new_articles, portfolio_text)

    if sent:
        console.print("[green]  ✅ Telegram message sent![/green]")
    else:
        console.print("[yellow]  ⚠️ Telegram send failed or not configured.[/yellow]")

    # --- Step 8: Mark as sent + log ---
    dedup.mark_sent(new_articles)
    news_logger.log_articles(new_articles)
    console.print("[dim]  Articles logged and marked as seen.[/dim]")


def main():
    parser = argparse.ArgumentParser(
        description="Stock News Notification System — Kite + Google News + Telegram"
    )
    parser.add_argument("--once", action="store_true", help="Run once and exit (no scheduling)")
    parser.add_argument("--mock", action="store_true", help="Use mock holdings data (no Kite needed)")
    parser.add_argument("--setup", action="store_true", help="Get your Telegram chat_id")
    parser.add_argument("--reset-seen", action="store_true", help="Clear dedup history")
    parser.add_argument("--summary", action="store_true", help="Force portfolio summary")
    args = parser.parse_args()

    # --- Setup mode ---
    if args.setup:
        console.print("\n[bold]🔧 Telegram Setup[/bold]")
        console.print("Make sure you've sent a message to your bot first.\n")
        notifier.get_chat_id()
        return

    # --- Reset dedup ---
    if args.reset_seen:
        dedup.reset()
        return

    # --- Authenticate with Kite (unless mock) ---
    global _kite_client
    if not args.mock:
        console.print("\n[bold]🔐 Authenticating with Kite...[/bold]")
        _kite_client = get_kite_client()
        if not _kite_client:
            console.print("[red]Authentication failed. Use --mock to test without Kite.[/red]")
            sys.exit(1)

    # --- Single run ---
    if args.once:
        run_cycle(use_mock=args.mock, force_summary=args.summary)
        return

    # --- Scheduled run ---
    import signal
    import time as time_mod

    interval = config.SCHEDULE_INTERVAL_MINUTES
    _running = True

    def _handle_stop(signum, frame):
        nonlocal _running
        _running = False
        console.print("\n[bold yellow]Shutting down...[/bold yellow]")

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    console.print(f"\n[bold green]🚀 Stock News System Started![/bold green]")
    console.print(f"  Schedule: every {interval} minutes")
    console.print(f"  Market hours only: {config.MARKET_HOURS_ONLY}")
    console.print(f"  Mode: {'Mock' if args.mock else 'Live (Kite)'}")
    console.print(f"  Press Ctrl+C to stop.\n")

    # Run immediately on start
    run_cycle(use_mock=args.mock, force_summary=True)

    # Loop with sleep
    while _running:
        # Sleep in small increments so Ctrl+C is responsive
        wait_seconds = interval * 60
        for _ in range(wait_seconds):
            if not _running:
                break
            time_mod.sleep(1)

        if _running:
            run_cycle(use_mock=args.mock)

    console.print("[bold yellow]Stopped.[/bold yellow]")


if __name__ == "__main__":
    main()
