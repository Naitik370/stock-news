"""Telegram notification sender."""

import requests

from . import config


def _base_url():
    """Build API URL dynamically so it always uses the current token."""
    return f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


def _send_message(text: str, parse_mode: str = "HTML") -> bool:
    """
    Send a message via Telegram Bot API.
    Returns True on success, False on failure.
    """
    url = f"{_base_url()}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    retries = 2
    for attempt in range(retries + 1):
        try:
            resp = requests.post(url, json=payload, timeout=10)
            data = resp.json()

            if data.get("ok"):
                return True

            print(f"[Telegram] API error: {data.get('description', 'Unknown')}")

            # If message is too long, try splitting (with depth guard)
            if "too long" in data.get("description", "").lower():
                return _send_long_message(text, parse_mode, _depth=0)

            if attempt < retries:
                import time
                time.sleep(2)

        except Exception as e:
            print(f"[Telegram] Send failed (attempt {attempt + 1}): {e}")
            if attempt < retries:
                import time
                time.sleep(2)

    return False


def _send_long_message(text: str, parse_mode: str = "HTML", _depth: int = 0) -> bool:
    """Split a long message and send in chunks."""
    if _depth > 3:
        print("[Telegram] Message still too long after splitting. Giving up.")
        return False

    max_len = 4000  # Telegram max is 4096, leave margin
    chunks = []
    current = ""

    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_len:
            chunks.append(current)
            current = line
        else:
            current += ("\n" + line) if current else line

    if current:
        chunks.append(current)

    success = True
    for chunk in chunks:
        if not _send_message(chunk, parse_mode):
            success = False

    return success


def format_news_message(
    articles_by_symbol: dict[str, list[dict]],
    portfolio_summary: str = "",
) -> str:
    """
    Format a Telegram message with news articles and optional portfolio summary.

    Args:
        articles_by_symbol: {symbol: [article_dicts]}
        portfolio_summary: Optional portfolio summary line

    Returns:
        Formatted HTML string for Telegram
    """
    lines = []

    # Portfolio summary header (escape HTML to prevent parse errors)
    if portfolio_summary:
        lines.append(_escape_html(portfolio_summary))
        lines.append("")

    lines.append("📰 <b>Stock News Alert</b>")
    lines.append("")

    for symbol, articles in articles_by_symbol.items():
        lines.append(f"🔹 <b>{symbol}</b>")

        for article in articles:
            emoji = article.get("priority_emoji", "⚪")
            title = _escape_html(article.get("title", ""))
            source = _escape_html(article.get("source", ""))
            url = article.get("url", "")
            pub_time = article.get("published_at_ist", "")

            lines.append(f"{emoji} • {title}")
            lines.append(f"    — {source} | {pub_time}")
            if url:
                lines.append(f'    🔗 <a href="{url}">Read more</a>')
            lines.append("")

    return "\n".join(lines).strip()


def send_news_alert(
    articles_by_symbol: dict[str, list[dict]],
    portfolio_summary: str = "",
) -> bool:
    """
    Send a formatted news alert to Telegram.
    Returns True if sent, False if failed or nothing to send.
    """
    if not articles_by_symbol:
        return False

    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[Telegram] Bot token or chat ID not configured. Skipping.")
        return False

    message = format_news_message(articles_by_symbol, portfolio_summary)
    return _send_message(message)


def send_error_alert(error_msg: str) -> bool:
    """Send an error/warning alert to Telegram."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return False

    text = f"⚠️ <b>Stock News Alert — Error</b>\n\n{_escape_html(error_msg)}"
    return _send_message(text)


def send_portfolio_summary(summary_text: str) -> bool:
    """Send a standalone portfolio summary to Telegram."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return False

    return _send_message(summary_text)


def get_chat_id():
    """
    Helper to fetch your Telegram chat_id.
    Send any message to your bot first, then run this.
    """
    url = f"{_base_url()}/getUpdates"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()

        if not data.get("ok") or not data.get("result"):
            print("[Telegram] No messages found. Send a message to your bot first!")
            return

        for update in data["result"]:
            msg = update.get("message", {})
            chat = msg.get("chat", {})
            chat_id = chat.get("id")
            first_name = chat.get("first_name", "Unknown")

            if chat_id:
                print(f"\n✅ Found your chat!")
                print(f"   Name: {first_name}")
                print(f"   Chat ID: {chat_id}")
                print(f"\n   Add this to your .env file:")
                print(f"   TELEGRAM_CHAT_ID={chat_id}\n")
                return

        print("[Telegram] Could not find chat_id in updates.")

    except Exception as e:
        print(f"[Telegram] Error: {e}")


def _escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
