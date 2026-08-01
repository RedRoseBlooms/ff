"""Gambling logic tests."""

from decimal import Decimal

from services.gambling_service import GamblingService


class FakeEconomy:
    pass


def test_mines_multiplier():
    service = GamblingService(None, FakeEconomy(), None)  # type: ignore
    assert service.mines_multiplier(0) == Decimal("1.00")
    m1 = service.mines_multiplier(1)
    m3 = service.mines_multiplier(3)
    assert m3 > m1


def test_blackjack_hand_value():
    service = GamblingService(None, FakeEconomy(), None)  # type: ignore
    assert service.blackjack_hand_value([1, 10]) == 21
    assert service.blackjack_hand_value([10, 10, 1]) == 21


def test_generate_mines():
    service = GamblingService(None, FakeEconomy(), None)  # type: ignore
    positions, seed = service.generate_mines(5)
    assert len(positions) == 5
    assert len(set(positions)) == 5
    assert all(0 <= p < 20 for p in positions)
    assert len(seed) > 0
