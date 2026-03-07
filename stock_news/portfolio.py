"""Portfolio P&L summary calculator."""


def compute_summary(holdings: list[dict]) -> dict:
    """
    Compute portfolio-level summary from holdings data.

    Returns:
        {
            total_investment: float,
            current_value: float,
            total_pnl: float,
            total_pnl_pct: float,
            top_gainer: {symbol, day_change_pct},
            top_loser: {symbol, day_change_pct},
            day_pnl: float,
        }
    """
    if not holdings:
        return {
            "total_investment": 0,
            "current_value": 0,
            "total_pnl": 0,
            "total_pnl_pct": 0,
            "top_gainer": None,
            "top_loser": None,
            "day_pnl": 0,
        }

    # Filter to actual holdings (not extra stocks with 0 quantity)
    actual = [h for h in holdings if h.get("quantity", 0) > 0]

    if not actual:
        return {
            "total_investment": 0,
            "current_value": 0,
            "total_pnl": 0,
            "total_pnl_pct": 0,
            "top_gainer": None,
            "top_loser": None,
            "day_pnl": 0,
        }

    total_investment = sum(h["avg_price"] * h["quantity"] for h in actual)
    current_value = sum(h["last_price"] * h["quantity"] for h in actual)
    total_pnl = current_value - total_investment
    total_pnl_pct = (total_pnl / total_investment * 100) if total_investment else 0

    # Day P&L
    day_pnl = sum(
        (h["last_price"] - h.get("close_price", h["last_price"])) * h["quantity"]
        for h in actual
    )

    # Top gainer and loser by day change %
    sorted_by_change = sorted(actual, key=lambda h: h.get("day_change_pct", 0))
    top_loser = {
        "symbol": sorted_by_change[0]["symbol"],
        "day_change_pct": sorted_by_change[0].get("day_change_pct", 0),
    }
    top_gainer = {
        "symbol": sorted_by_change[-1]["symbol"],
        "day_change_pct": sorted_by_change[-1].get("day_change_pct", 0),
    }

    return {
        "total_investment": round(total_investment, 2),
        "current_value": round(current_value, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "top_gainer": top_gainer,
        "top_loser": top_loser,
        "day_pnl": round(day_pnl, 2),
    }


def format_summary(summary: dict) -> str:
    """Format portfolio summary as a compact string for Telegram."""
    if summary["current_value"] == 0:
        return "📊 Portfolio: No holdings data"

    pnl_sign = "+" if summary["total_pnl_pct"] >= 0 else ""
    day_sign = "+" if summary["day_pnl"] >= 0 else ""

    # Format values in Indian notation (lakhs/crores feel)
    current = f"₹{summary['current_value']:,.0f}"
    pnl_pct = f"{pnl_sign}{summary['total_pnl_pct']:.1f}%"
    day_pnl = f"{day_sign}₹{summary['day_pnl']:,.0f}"

    line = f"📊 Portfolio: {current} ({pnl_pct}) | Today: {day_pnl}"

    # Add top gainer/loser
    parts = []
    if summary["top_gainer"]:
        g = summary["top_gainer"]
        g_sign = "+" if g["day_change_pct"] >= 0 else ""
        parts.append(f"📈 {g['symbol']} {g_sign}{g['day_change_pct']:.1f}%")
    if summary["top_loser"] and summary["top_loser"]["symbol"] != summary.get("top_gainer", {}).get("symbol"):
        l = summary["top_loser"]
        l_sign = "+" if l["day_change_pct"] >= 0 else ""
        parts.append(f"📉 {l['symbol']} {l_sign}{l['day_change_pct']:.1f}%")

    if parts:
        line += "\n" + " | ".join(parts)

    return line
