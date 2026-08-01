"""House edge service tests."""

from decimal import Decimal

from config import Config
from services.house_edge_service import HouseEdgeService


def test_new_player_favored(sample_config):
    service = HouseEdgeService(sample_config)
    new_edge = service.effective_edge(Decimal("0.10"), level=1)
    rich_edge = service.effective_edge(Decimal("10000"), level=50)
    assert new_edge < rich_edge


def test_payout_adjustment(sample_config):
    service = HouseEdgeService(sample_config)
    base = Decimal("2.00")
    adjusted = service.apply_payout_multiplier(base, Decimal("100"), 20)
    assert adjusted < base


def test_probability_bounds(sample_config):
    service = HouseEdgeService(sample_config)
    for _ in range(100):
        prob = service.adjust_win_probability(0.5, Decimal("100"), 10)
        assert 0.05 <= prob <= 0.95
