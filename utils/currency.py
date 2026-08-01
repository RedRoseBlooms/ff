"""Currency formatting utilities."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def format_money(amount: Decimal | float | int | str) -> str:
    """Format amount as human-readable currency."""
    value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if value >= 1_000_000:
        return f"${value / Decimal('1000000'):,.2f}M"
    if value >= 1_000:
        return f"${value / Decimal('1000'):,.2f}K"
    return f"${value:,.2f}"


def parse_bet(raw: str) -> Decimal:
    """Parse bet string supporting k/m suffixes."""
    text = raw.strip().lower().replace("$", "").replace(",", "")
    multiplier = Decimal("1")
    if text.endswith("k"):
        multiplier = Decimal("1000")
        text = text[:-1]
    elif text.endswith("m"):
        multiplier = Decimal("1000000")
        text = text[:-1]
    return (Decimal(text) * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def progress_bar(current: float, total: float, width: int = 10) -> str:
    """Create a unicode progress bar."""
    if total <= 0:
        return "░" * width
    ratio = max(0.0, min(1.0, current / total))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)
