"""
Environment configuration for Fortunata.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str) -> int | None:
    val = os.getenv(name)
    if not val:
        return None
    try:
        return int(val)
    except ValueError:
        return None


DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
GUILD_ID: int | None = _get_int("GUILD_ID")  # optional: instant slash-command sync to one guild
DB_PATH: str = os.getenv("DB_PATH", "data/fortunata.sqlite3")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

if not DISCORD_TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is not set. Copy .env.example to .env and fill it in, "
        "or set the DISCORD_TOKEN environment variable in your hosting platform."
    )
