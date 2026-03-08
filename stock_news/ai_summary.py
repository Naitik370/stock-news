"""AI-powered article enrichment — sentiment tags and TL;DR summaries via Google Gemini."""

import json
import logging

from google import genai
from google.genai import types

from . import config

logger = logging.getLogger(__name__)

_MODEL = "gemini-2.5-flash-lite"

_SYSTEM_PROMPT = (
    "You are a senior Indian stock market news analyst. "
    "Your job is to read news articles about publicly traded companies on NSE/BSE "
    "and provide concise, actionable analysis.\n\n"
    "For every article you are given:\n"
    "1. Determine the sentiment: 'bullish', 'bearish', or 'neutral'.\n"
    "2. Write a concise 1-2 sentence TL;DR covering what happened and its market implication.\n\n"
    "Use the provided URLs and your web search capability to read the full article content. "
    "If you cannot access an article, base your analysis on the headline and source.\n\n"
    "Respond ONLY with a raw JSON array (no markdown fences, no commentary). "
    "Each element must have exactly these keys:\n"
    '  {"index": <number>, "sentiment": "<bullish|bearish|neutral>", '
    '"summary": "<1-2 sentence TL;DR>"}'
)


def _build_prompt(articles_flat: list[dict]) -> str:
    """Build the user prompt listing articles to analyze."""
    lines = ["Analyze these articles:\n"]

    for i, article in enumerate(articles_flat):
        lines.append(f"[{i}] {article.get('title', '')} — {article.get('source', '')}")
        url = article.get("url", "")
        if url:
            lines.append(f"    URL: {url}")

    return "\n".join(lines)


def _parse_response(text: str, count: int) -> list[dict] | None:
    """Parse the Gemini JSON response. Returns list of {index, sentiment, summary} or None."""
    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Remove first and last lines (```json and ```)
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned

    try:
        data = json.loads(cleaned)
        if not isinstance(data, list):
            return None
        return data
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"[AI] Failed to parse Gemini response: {e}")
        return None


def _sentiment_emoji(sentiment: str) -> str:
    """Map sentiment to emoji."""
    return {
        "bullish": "🐂",
        "bearish": "🐻",
        "neutral": "😐",
    }.get(sentiment.lower(), "😐")


def _extract_text(response) -> str | None:
    """Robustly extract text from a Gemini response."""
    # Try .text first
    try:
        if response.text:
            return response.text
    except (AttributeError, ValueError):
        pass

    # Fall back to candidates
    try:
        if response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, "text") and part.text:
                            return part.text
    except (AttributeError, IndexError):
        pass

    return None


def _call_gemini(client, prompt: str, use_search: bool = True) -> str | None:
    """Call Gemini and return the response text, or None."""
    config_kwargs = {
        "temperature": 0.3,
        "system_instruction": _SYSTEM_PROMPT,
    }

    if use_search:
        search_tool = types.Tool(google_search=types.GoogleSearch())
        config_kwargs["tools"] = [search_tool]

    response = client.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )

    return _extract_text(response)


def enrich_articles(articles_by_symbol: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """
    Enrich articles with AI sentiment and summary via Gemini.

    Adds to each article dict:
      - ai_sentiment: 'bullish', 'bearish', or 'neutral'
      - ai_sentiment_emoji: 🐂, 🐻, or 😐
      - ai_summary: 1-2 sentence TL;DR

    If GEMINI_API_KEY is not set or if the API call fails,
    articles are returned unchanged (graceful degradation).
    """
    if not config.GEMINI_API_KEY:
        logger.debug("[AI] No GEMINI_API_KEY configured. Skipping AI enrichment.")
        return articles_by_symbol

    # Flatten all articles with their position info
    articles_flat = []
    position_map = []  # [(symbol, index_in_list)]

    for symbol, articles in articles_by_symbol.items():
        for i, article in enumerate(articles):
            articles_flat.append(article)
            position_map.append((symbol, i))

    if not articles_flat:
        return articles_by_symbol

    # Build and send prompt
    prompt = _build_prompt(articles_flat)

    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)

        # Try with Google Search grounding first
        text = _call_gemini(client, prompt, use_search=True)

        # Fall back to without search if empty (model may not support it)
        if not text:
            logger.info("[AI] Retrying without search grounding...")
            text = _call_gemini(client, prompt, use_search=False)

        if not text:
            logger.warning("[AI] Empty response from Gemini.")
            return articles_by_symbol

        results = _parse_response(text, len(articles_flat))
        if not results:
            logger.warning(f"[AI] Could not parse Gemini response: {text[:200]}")
            return articles_by_symbol

        # Apply results back to articles
        for item in results:
            idx = item.get("index")
            if idx is None or idx < 0 or idx >= len(articles_flat):
                continue

            sentiment = item.get("sentiment", "neutral").lower()
            if sentiment not in ("bullish", "bearish", "neutral"):
                sentiment = "neutral"

            articles_flat[idx]["ai_sentiment"] = sentiment
            articles_flat[idx]["ai_sentiment_emoji"] = _sentiment_emoji(sentiment)
            articles_flat[idx]["ai_summary"] = item.get("summary", "")

        logger.info(f"[AI] Enriched {len(results)} article(s) with sentiment + summary.")

    except Exception as e:
        logger.warning(f"[AI] Gemini API call failed: {e}")
        # Graceful degradation — articles remain unchanged

    return articles_by_symbol

