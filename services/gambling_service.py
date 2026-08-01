"""Gambling game logic and payout calculations."""

from __future__ import annotations

import hashlib
import random
import secrets
from decimal import Decimal

import asyncpg

from models.enums import GameType, XP_PER_GAME, XP_PER_WIN
from repositories.game_repository import GameRepository
from services.economy_service import EconomyService
from services.house_edge_service import HouseEdgeService
from utils.logging import get_logger

logger = get_logger(__name__)

SLOT_SYMBOLS = ["🍒", "🍋", "🔔", "⭐", "💎", "7️⃣"]
CARD_VALUES = list(range(1, 14))


class GamblingService:
    """Central gambling engine with provably fair seeds for applicable games."""

    def __init__(self, db, economy: EconomyService, house_edge: HouseEdgeService) -> None:
        self.db = db
        self.economy = economy
        self.house_edge = house_edge
        self.games = GameRepository(db)

    def _user_context(self, user: asyncpg.Record) -> tuple[Decimal, int]:
        net = Decimal(str(user["wallet"])) + Decimal(str(user["bank"]))
        return net, int(user["level"])

    def provably_fair_seed(self) -> tuple[str, str]:
        server_seed = secrets.token_hex(16)
        client_seed = secrets.token_hex(8)
        combined = hashlib.sha256(f"{server_seed}:{client_seed}".encode()).hexdigest()
        return server_seed, combined

    def _hash_roll(self, seed: str, index: int, max_val: int) -> int:
        h = hashlib.sha256(f"{seed}:{index}".encode()).hexdigest()
        return int(h, 16) % max_val

    async def place_bet(self, user_id: int, guild_id: int, amount: Decimal) -> asyncpg.Record:
        user = await self.economy.get_user(user_id, guild_id)
        max_bet = self.economy.max_bet(user)
        if amount <= 0:
            raise ValueError("Bet must be positive")
        if amount > Decimal(str(user["wallet"])):
            raise ValueError("Insufficient wallet balance")
        if amount > max_bet and max_bet < Decimal(str(user["wallet"])):
            raise ValueError(f"Max bet is ${max_bet}")
        return await self.economy.deduct_bet(user_id, guild_id, amount)

    async def finalize_game(
        self,
        user_id: int,
        guild_id: int,
        game_type: GameType | str,
        bet: Decimal,
        payout: Decimal,
        won: bool,
        metadata: dict | None = None,
    ) -> None:
        if won and payout > 0:
            await self.economy.payout_win(user_id, guild_id, bet, payout, str(game_type))
        async with self.db.transaction() as conn:
            await self.games.record_history(
                conn,
                user_id=user_id,
                guild_id=guild_id,
                game_type=str(game_type),
                bet=bet,
                payout=payout if won else Decimal("0"),
                won=won,
                metadata=metadata,
            )
            xp = XP_PER_WIN if won else XP_PER_GAME
            await conn.execute(
                """
                UPDATE users SET
                    xp = xp + $2,
                    level = GREATEST(1, 1 + (xp + $2) / 100),
                    win_streak = CASE WHEN $3 THEN win_streak + 1 ELSE 0 END,
                    best_win_streak = CASE WHEN $3 AND win_streak + 1 > best_win_streak
                        THEN win_streak + 1 ELSE best_win_streak END,
                    updated_at = NOW()
                WHERE user_id = $1
                """,
                user_id,
                xp,
                won,
            )
        logger.info("game_complete", user_id=user_id, game=str(game_type), won=won, payout=str(payout))

    # --- Game implementations ---

    async def coinflip(self, user_id: int, guild_id: int, bet: Decimal, choice: str) -> dict:
        await self.place_bet(user_id, guild_id, bet)
        user = await self.economy.get_user(user_id, guild_id)
        net, level = self._user_context(user)
        result = random.choice(["heads", "tails"])
        won = result == choice.lower()
        if not won:
            win_chance = 0.48
            won = self.house_edge.roll_outcome(win_chance, net, level) and result == choice.lower()
        multiplier = Decimal("1.96")
        payout = (bet * multiplier).quantize(Decimal("0.01")) if won else Decimal("0")
        await self.finalize_game(user_id, guild_id, GameType.COINFLIP, bet, payout, won)
        return {"result": result, "won": won, "payout": payout}

    async def dice(self, user_id: int, guild_id: int, bet: Decimal, target: int) -> dict:
        await self.place_bet(user_id, guild_id, bet)
        user = await self.economy.get_user(user_id, guild_id)
        net, level = self._user_context(user)
        roll = random.randint(1, 6)
        win_chance = max(0.1, (7 - target) / 6 * 0.9)
        won = roll >= target
        if not won:
            won = self.house_edge.roll_outcome(win_chance, net, level) and roll >= target
        mult = Decimal(str(round(6 / max(1, 7 - target) * 0.95, 2)))
        payout = (bet * mult).quantize(Decimal("0.01")) if won else Decimal("0")
        await self.finalize_game(user_id, guild_id, GameType.DICE, bet, payout, won)
        return {"roll": roll, "won": won, "payout": payout}

    async def slots(self, user_id: int, guild_id: int, bet: Decimal) -> dict:
        await self.place_bet(user_id, guild_id, bet)
        reels = [random.choice(SLOT_SYMBOLS) for _ in range(3)]
        won = reels[0] == reels[1] == reels[2]
        mult = Decimal("10") if won else Decimal("0")
        if reels[0] == reels[1] and not won:
            mult = Decimal("2")
            won = True
        payout = (bet * mult).quantize(Decimal("0.01")) if won else Decimal("0")
        await self.finalize_game(user_id, guild_id, GameType.SLOTS, bet, payout, won, {"reels": reels})
        return {"reels": reels, "won": won, "payout": payout}

    async def roulette(self, user_id: int, guild_id: int, bet: Decimal, choice: str) -> dict:
        await self.place_bet(user_id, guild_id, bet)
        number = random.randint(0, 36)
        red = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
        color = "green" if number == 0 else ("red" if number in red else "black")
        won = False
        mult = Decimal("0")
        c = choice.lower()
        if c in ("red", "black", "green"):
            won = c == color
            mult = Decimal("2") if c != "green" else Decimal("14")
        elif c.isdigit():
            won = int(c) == number
            mult = Decimal("36")
        payout = (bet * mult).quantize(Decimal("0.01")) if won else Decimal("0")
        await self.finalize_game(user_id, guild_id, GameType.ROULETTE, bet, payout, won)
        return {"number": number, "color": color, "won": won, "payout": payout}

    async def limbo(self, user_id: int, guild_id: int, bet: Decimal, target: Decimal) -> dict:
        await self.place_bet(user_id, guild_id, bet)
        user = await self.economy.get_user(user_id, guild_id)
        net, level = self._user_context(user)
        edge = float(self.house_edge.effective_edge(net, level))
        result = round(random.uniform(1.0, max(float(target) * 1.5, 10.0)) * (1 - edge * 0.3), 2)
        won = result >= float(target)
        payout = (bet * target).quantize(Decimal("0.01")) if won else Decimal("0")
        await self.finalize_game(user_id, guild_id, GameType.LIMBO, bet, payout, won)
        return {"result": result, "target": float(target), "won": won, "payout": payout}

    async def crash_cashout(self, user_id: int, guild_id: int, bet: Decimal, cashout_at: float) -> dict:
        await self.place_bet(user_id, guild_id, bet)
        crash_point = round(random.uniform(1.01, 10.0), 2)
        won = cashout_at <= crash_point
        payout = (bet * Decimal(str(cashout_at))).quantize(Decimal("0.01")) if won else Decimal("0")
        await self.finalize_game(user_id, guild_id, GameType.CRASH, bet, payout, won)
        return {"crash_point": crash_point, "cashout_at": cashout_at, "won": won, "payout": payout}

    def generate_mines(self, mine_count: int = 5, seed: str | None = None) -> tuple[list[int], str]:
        server_seed, combined = self.provably_fair_seed()
        use_seed = seed or combined
        positions = set()
        idx = 0
        while len(positions) < mine_count:
            positions.add(self._hash_roll(use_seed, idx, 20))
            idx += 1
        return sorted(positions), server_seed

    def mines_multiplier(self, revealed: int, mine_count: int = 5) -> Decimal:
        safe = 20 - mine_count
        if revealed <= 0:
            return Decimal("1.00")
        mult = 1.0
        for i in range(revealed):
            mult *= (20 - i) / (safe - i)
        return Decimal(str(round(mult * 0.97, 2)))

    async def plinko(self, user_id: int, guild_id: int, bet: Decimal, risk: str) -> dict:
        await self.place_bet(user_id, guild_id, bet)
        multipliers = {
            "low": [0.5, 0.8, 1.0, 1.2, 1.5, 1.2, 1.0, 0.8, 0.5],
            "medium": [0.3, 0.5, 1.0, 2.0, 3.0, 2.0, 1.0, 0.5, 0.3],
            "high": [0.1, 0.3, 0.5, 2.0, 10.0, 2.0, 0.5, 0.3, 0.1],
        }
        slots = multipliers.get(risk, multipliers["medium"])
        slot = random.randint(0, len(slots) - 1)
        mult = Decimal(str(slots[slot]))
        payout = (bet * mult).quantize(Decimal("0.01"))
        won = payout >= bet
        await self.finalize_game(user_id, guild_id, GameType.PLINKO, bet, payout, won)
        return {"slot": slot, "multiplier": float(mult), "won": won, "payout": payout}

    def blackjack_hand_value(self, cards: list[int]) -> int:
        total = sum(min(c, 10) for c in cards)
        aces = sum(1 for c in cards if c == 1)
        while aces and total + 10 <= 21:
            total += 10
            aces -= 1
        return total

    def deal_card(self) -> int:
        return random.choice(CARD_VALUES)

    async def higher_lower(self, user_id: int, guild_id: int, bet: Decimal, guess: str) -> dict:
        await self.place_bet(user_id, guild_id, bet)
        current = random.randint(1, 13)
        next_card = random.randint(1, 13)
        won = (guess == "higher" and next_card > current) or (guess == "lower" and next_card < current)
        if next_card == current:
            payout = bet
            await self.finalize_game(user_id, guild_id, GameType.HIGHER_LOWER, bet, payout, True)
            return {"current": current, "next": next_card, "won": True, "payout": payout, "push": True}
        payout = (bet * Decimal("1.9")).quantize(Decimal("0.01")) if won else Decimal("0")
        await self.finalize_game(user_id, guild_id, GameType.HIGHER_LOWER, bet, payout, won)
        return {"current": current, "next": next_card, "won": won, "payout": payout, "push": False}

    async def baccarat(self, user_id: int, guild_id: int, bet: Decimal, bet_on: str) -> dict:
        await self.place_bet(user_id, guild_id, bet)
        player = [self.deal_card(), self.deal_card()]
        banker = [self.deal_card(), self.deal_card()]
        pv = sum(min(c, 10) for c in player) % 10
        bv = sum(min(c, 10) for c in banker) % 10
        if pv > bv:
            winner = "player"
        elif bv > pv:
            winner = "banker"
        else:
            winner = "tie"
        won = bet_on == winner
        mult = Decimal("2") if bet_on != "tie" else Decimal("8")
        payout = (bet * mult).quantize(Decimal("0.01")) if won else Decimal("0")
        await self.finalize_game(user_id, guild_id, GameType.BACCARAT, bet, payout, won)
        return {"player": pv, "banker": bv, "winner": winner, "won": won, "payout": payout}

    async def tower(self, user_id: int, guild_id: int, bet: Decimal, floors: int = 3) -> dict:
        await self.place_bet(user_id, guild_id, bet)
        climbed = 0
        for _ in range(floors):
            if random.random() < 0.7:
                climbed += 1
            else:
                break
        mult = Decimal(str(1 + climbed * 0.5))
        won = climbed > 0
        payout = (bet * mult).quantize(Decimal("0.01")) if won else Decimal("0")
        await self.finalize_game(user_id, guild_id, GameType.TOWER, bet, payout, won)
        return {"floors_climbed": climbed, "multiplier": float(mult), "won": won, "payout": payout}

    async def duel(self, user_id: int, guild_id: int, target_id: int, bet: Decimal) -> dict:
        if user_id == target_id:
            raise ValueError("Cannot duel yourself")
        await self.place_bet(user_id, guild_id, bet)
        roll_a = random.randint(1, 100)
        roll_b = random.randint(1, 100)
        won = roll_a > roll_b
        payout = (bet * Decimal("1.95")).quantize(Decimal("0.01")) if won else Decimal("0")
        await self.finalize_game(user_id, guild_id, GameType.DUEL, bet, payout, won, {"target": target_id, "rolls": [roll_a, roll_b]})
        return {"your_roll": roll_a, "their_roll": roll_b, "won": won, "payout": payout}
