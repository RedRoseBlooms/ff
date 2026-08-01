"""Dynamic house edge calculation - internal only."""

from __future__ import annotations

import random
from decimal import Decimal

from config import Config


class HouseEdgeService:
    """
    Gradual, non-obvious house edge adjustments based on wealth tiers.
    New players receive favorable odds; wealthy players see slight reductions.
    """

    TIERS = [
        (Decimal("0"), Decimal("0.01")),
        (Decimal("1"), Decimal("0.02")),
        (Decimal("10"), Decimal("0.03")),
        (Decimal("100"), Decimal("0.04")),
        (Decimal("1000"), Decimal("0.05")),
        (Decimal("10000"), Decimal("0.06")),
    ]

    def __init__(self, config: Config) -> None:
        self.base = config.house_edge_base

    def effective_edge(self, net_worth: Decimal, level: int = 1) -> Decimal:
        edge = self.base
        for threshold, bonus in self.TIERS:
            if net_worth >= threshold:
                edge = self.base + bonus
        # New player favor: reduce edge for low levels
        if level <= 5:
            edge *= Decimal("0.7")
        elif level <= 15:
            edge *= Decimal("0.85")
        return min(edge, Decimal("0.12"))

    def adjust_win_probability(self, base_prob: float, net_worth: Decimal, level: int) -> float:
        edge = float(self.effective_edge(net_worth, level))
        adjusted = base_prob * (1.0 - edge * 0.5)
        return max(0.05, min(0.95, adjusted))

    def apply_payout_multiplier(self, multiplier: Decimal, net_worth: Decimal, level: int) -> Decimal:
        edge = self.effective_edge(net_worth, level)
        reduction = Decimal("1") - edge
        return (multiplier * reduction).quantize(Decimal("0.01"))

    def roll_outcome(self, win_chance: float, net_worth: Decimal, level: int) -> bool:
        prob = self.adjust_win_probability(win_chance, net_worth, level)
        # Small random variance so patterns aren't obvious
        prob += random.uniform(-0.02, 0.02)
        prob = max(0.05, min(0.95, prob))
        return random.random() < prob
