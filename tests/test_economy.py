"""Economy utility tests."""

from decimal import Decimal

from utils.currency import format_money, parse_bet, progress_bar


def test_format_money():
    assert format_money(Decimal("0.10")) == "$0.10"
    assert format_money(Decimal("1500")) == "$1.50K"
    assert format_money(Decimal("2500000")) == "$2.50M"


def test_parse_bet():
    assert parse_bet("1.50") == Decimal("1.50")
    assert parse_bet("2k") == Decimal("2000.00")
    assert parse_bet("1.5m") == Decimal("1500000.00")


def test_progress_bar():
    assert progress_bar(5, 10, 10) == "█████░░░░░"
    assert progress_bar(0, 10, 5) == "░░░░░"
