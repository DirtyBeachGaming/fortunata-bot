"""
Persistence layer for Fortunata. A single SQLite database (via aiosqlite)
holds per-guild configuration (roles/channels the bot manages) and
per-member astrology data (sun sign, full natal chart, Chinese zodiac,
blood type).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS guild_config (
    guild_id INTEGER PRIMARY KEY,
    verified_role_id INTEGER,
    unverified_role_id INTEGER,
    verification_channel_id INTEGER,
    verification_message_id INTEGER
);

CREATE TABLE IF NOT EXISTS users (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    verified INTEGER NOT NULL DEFAULT 0,

    sun_sign TEXT,

    birth_year INTEGER,
    birth_month INTEGER,
    birth_day INTEGER,
    birth_hour INTEGER,
    birth_minute INTEGER,
    birth_location TEXT,
    birth_lat REAL,
    birth_lon REAL,
    birth_tz TEXT,

    moon_sign TEXT,
    ascendant_sign TEXT,
    mercury_sign TEXT,
    venus_sign TEXT,
    mars_sign TEXT,
    jupiter_sign TEXT,
    saturn_sign TEXT,
    uranus_sign TEXT,
    neptune_sign TEXT,
    pluto_sign TEXT,

    chinese_animal TEXT,
    chinese_element TEXT,
    chinese_lunar_year INTEGER,

    blood_type TEXT,

    updated_at TEXT,

    PRIMARY KEY (guild_id, user_id)
);
"""

# Columns a caller may set via upsert_user's **fields
_USER_COLUMNS = {
    "verified", "sun_sign",
    "birth_year", "birth_month", "birth_day", "birth_hour", "birth_minute",
    "birth_location", "birth_lat", "birth_lon", "birth_tz",
    "moon_sign", "ascendant_sign", "mercury_sign", "venus_sign", "mars_sign",
    "jupiter_sign", "saturn_sign", "uranus_sign", "neptune_sign", "pluto_sign",
    "chinese_animal", "chinese_element", "chinese_lunar_year",
    "blood_type",
}

_GUILD_COLUMNS = {
    "verified_role_id", "unverified_role_id",
    "verification_channel_id", "verification_message_id",
}


class Database:
    def __init__(self, path: str):
        self.path = path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database not connected — call connect() first")
        return self._conn

    # ---------------------------------------------------------------- guild

    async def get_guild_config(self, guild_id: int) -> Optional[dict]:
        cur = await self.conn.execute(
            "SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def set_guild_config(self, guild_id: int, **fields: Any) -> None:
        bad = set(fields) - _GUILD_COLUMNS
        if bad:
            raise ValueError(f"Unknown guild_config column(s): {bad}")
        existing = await self.get_guild_config(guild_id)
        if existing is None:
            cols = ", ".join(["guild_id"] + list(fields.keys()))
            placeholders = ", ".join(["?"] * (len(fields) + 1))
            await self.conn.execute(
                f"INSERT INTO guild_config ({cols}) VALUES ({placeholders})",
                (guild_id, *fields.values()),
            )
        else:
            set_clause = ", ".join(f"{k} = ?" for k in fields)
            await self.conn.execute(
                f"UPDATE guild_config SET {set_clause} WHERE guild_id = ?",
                (*fields.values(), guild_id),
            )
        await self.conn.commit()

    # ----------------------------------------------------------------- user

    async def get_user(self, guild_id: int, user_id: int) -> Optional[dict]:
        cur = await self.conn.execute(
            "SELECT * FROM users WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def upsert_user(self, guild_id: int, user_id: int, **fields: Any) -> None:
        bad = set(fields) - _USER_COLUMNS
        if bad:
            raise ValueError(f"Unknown users column(s): {bad}")
        fields = dict(fields)
        fields["updated_at"] = datetime.now(timezone.utc).isoformat()

        existing = await self.get_user(guild_id, user_id)
        if existing is None:
            cols = ", ".join(["guild_id", "user_id"] + list(fields.keys()))
            placeholders = ", ".join(["?"] * (len(fields) + 2))
            await self.conn.execute(
                f"INSERT INTO users ({cols}) VALUES ({placeholders})",
                (guild_id, user_id, *fields.values()),
            )
        else:
            set_clause = ", ".join(f"{k} = ?" for k in fields)
            await self.conn.execute(
                f"UPDATE users SET {set_clause} WHERE guild_id = ? AND user_id = ?",
                (*fields.values(), guild_id, user_id),
            )
        await self.conn.commit()

    async def delete_user(self, guild_id: int, user_id: int) -> None:
        await self.conn.execute(
            "DELETE FROM users WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await self.conn.commit()
