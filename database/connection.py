"""Async PostgreSQL connection pool management."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpg

from config import Config
from utils.logging import get_logger

logger = get_logger(__name__)


class Database:
    """Manages asyncpg connection pool with transaction helpers."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(
            dsn=self.config.database_url,
            min_size=self.config.pool_min_size,
            max_size=self.config.pool_max_size,
            command_timeout=30,
        )
        await self._ensure_extensions()
        logger.info("database_connected", min=self.config.pool_min_size, max=self.config.pool_max_size)

    async def _ensure_extensions(self) -> None:
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
            logger.info("database_closed")

    async def execute(self, query: str, *args: object) -> str:
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args: object) -> list[asyncpg.Record]:
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args: object) -> asyncpg.Record | None:
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args: object):
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[asyncpg.Connection]:
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn

    async def run_schema(self, schema_path: str = "schema.sql") -> None:
        with open(schema_path, encoding="utf-8") as f:
            sql = f.read()
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            await conn.execute(sql)
        logger.info("schema_applied")
