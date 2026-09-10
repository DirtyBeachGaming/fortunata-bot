"""
Fortunata — the astrology bot for Trimalchio's Dinner Party.

Entry point. Run with `python bot.py`.
"""
from __future__ import annotations

import asyncio
import logging
import os

import discord
from discord.ext import commands

import config
from utils.db import Database

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("fortunata")

INTENTS = discord.Intents.default()
INTENTS.members = True  # required for on_member_join + accurate role management

EXTENSIONS = [
    "cogs.verification",
    "cogs.placements",
    "cogs.chinese_zodiac",
    "cogs.blood_type",
    "cogs.profile",
    "cogs.admin",
]


class Fortunata(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned, intents=INTENTS)
        self.db = Database(config.DB_PATH)

    async def setup_hook(self) -> None:
        os.makedirs(os.path.dirname(config.DB_PATH) or ".", exist_ok=True)
        await self.db.connect()
        log.info("Database ready at %s", config.DB_PATH)

        for ext in EXTENSIONS:
            try:
                await self.load_extension(ext)
                log.info("Loaded extension %s", ext)
            except Exception:
                log.exception("Failed to load extension %s", ext)

        if config.GUILD_ID:
            guild_obj = discord.Object(id=config.GUILD_ID)
            self.tree.copy_global_to(guild=guild_obj)
            synced = await self.tree.sync(guild=guild_obj)
            log.info("Synced %d command(s) to guild %s (instant)", len(synced), config.GUILD_ID)
        else:
            synced = await self.tree.sync()
            log.info("Synced %d command(s) globally (may take up to ~1h to appear)", len(synced))

    async def close(self) -> None:
        await self.db.close()
        await super().close()

    async def on_ready(self) -> None:
        log.info("Fortunata is online as %s (id=%s)", self.user, self.user.id if self.user else "?")
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name="the stars over the banquet")
        )


async def main() -> None:
    bot = Fortunata()
    async with bot:
        await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
