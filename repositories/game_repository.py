"""Game session and history repository."""

from __future__ import annotations

import json
from decimal import Decimal
from uuid import UUID

import asyncpg


class GameRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def create_session(
        self,
        user_id: int,
        guild_id: int,
        game_type: str,
        bet: Decimal,
        state: dict,
        seed: str | None = None,
    ) -> asyncpg.Record:
        return await self.db.fetchrow(
            """
            INSERT INTO game_sessions (user_id, guild_id, game_type, bet_amount, state, seed)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6)
            RETURNING *
            """,
            user_id,
            guild_id,
            game_type,
            bet,
            json.dumps(state),
            seed,
        )

    async def update_session(self, session_id: UUID, state: dict, active: bool = True) -> None:
        await self.db.execute(
            """
            UPDATE game_sessions SET state = $2::jsonb, active = $3, updated_at = NOW()
            WHERE session_id = $1
            """,
            session_id,
            json.dumps(state),
            active,
        )

    async def get_active_session(self, user_id: int, game_type: str) -> asyncpg.Record | None:
        return await self.db.fetchrow(
            """
            SELECT * FROM game_sessions
            WHERE user_id = $1 AND game_type = $2 AND active = TRUE
            ORDER BY created_at DESC LIMIT 1
            """,
            user_id,
            game_type,
        )

    async def close_session(self, session_id: UUID) -> None:
        await self.db.execute(
            "UPDATE game_sessions SET active = FALSE, updated_at = NOW() WHERE session_id = $1",
            session_id,
        )

    async def record_history(
        self,
        conn: asyncpg.Connection,
        *,
        user_id: int,
        guild_id: int,
        game_type: str,
        bet: Decimal,
        payout: Decimal,
        won: bool,
        metadata: dict | None = None,
    ) -> None:
        await conn.execute(
            """
            INSERT INTO game_history (user_id, guild_id, game_type, bet_amount, payout, won, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
            """,
            user_id,
            guild_id,
            game_type,
            bet,
            payout,
            won,
            json.dumps(metadata or {}),
        )

        await conn.execute(
            """
            INSERT INTO user_stats (user_id) VALUES ($1)
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id,
        )
        profit = payout - bet if won else bet
        await conn.execute(
            """
            UPDATE user_stats SET
                games_played = games_played + 1,
                games_won = games_won + $2,
                money_earned = money_earned + $3,
                money_lost = money_lost + $4,
                biggest_win = GREATEST(biggest_win, $5),
                biggest_loss = GREATEST(biggest_loss, $6),
                updated_at = NOW()
            WHERE user_id = $1
            """,
            user_id,
            1 if won else 0,
            payout if won else Decimal("0"),
            bet if not won else Decimal("0"),
            payout if won else Decimal("0"),
            bet if not won else Decimal("0"),
        )

    async def leaderboard(
        self,
        guild_id: int,
        metric: str,
        limit: int = 10,
        offset: int = 0,
    ) -> list[asyncpg.Record]:
        if metric == "biggest_win":
            return await self.db.fetch(
                """
                SELECT gh.user_id, MAX(gh.payout) AS value
                FROM game_history gh
                WHERE gh.guild_id = $1 AND gh.won = TRUE
                GROUP BY gh.user_id
                ORDER BY value DESC LIMIT $2 OFFSET $3
                """,
                guild_id,
                limit,
                offset,
            )
        if metric == "most_games":
            return await self.db.fetch(
                """
                SELECT us.user_id, us.games_played AS value
                FROM user_stats us
                JOIN users u ON u.user_id = us.user_id
                WHERE u.guild_id = $1
                ORDER BY value DESC LIMIT $2 OFFSET $3
                """,
                guild_id,
                limit,
                offset,
            )
        if metric == "net_profit":
            return await self.db.fetch(
                """
                SELECT us.user_id, (us.money_earned - us.money_lost) AS value
                FROM user_stats us
                JOIN users u ON u.user_id = us.user_id
                WHERE u.guild_id = $1
                ORDER BY value DESC LIMIT $2 OFFSET $3
                """,
                guild_id,
                limit,
                offset,
            )
        raise ValueError("Unknown metric")
