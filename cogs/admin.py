"""
Admin/setup commands, grouped under /fortunata. Requires Manage Server.
"""
from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils import roles as role_utils
from utils.astrology import ZODIAC_SIGNS, SIGN_ORDER
from utils.chart import PLANETS
from utils.chinese import ANIMALS, ELEMENTS
from utils.blood import BLOOD_TYPES
from cogs.verification import VerificationPanelView, WELCOME_TITLE

log = logging.getLogger("fortunata.admin")


class Admin(commands.Cog):
    fortunata = app_commands.Group(
        name="fortunata",
        description="Fortunata setup & admin commands",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db  # type: ignore[attr-defined]

    # ------------------------------------------------------------- setup

    @fortunata.command(name="setup", description="Set up (or move) the verification panel.")
    @app_commands.describe(
        channel="Channel to post the verification panel in",
        verified_role="Role given once someone verifies (created if omitted)",
        unverified_role="Role new members hold until they verify (created if omitted)",
    )
    async def setup_cmd(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        verified_role: discord.Role | None = None,
        unverified_role: discord.Role | None = None,
    ) -> None:
        guild = interaction.guild
        assert guild is not None
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            if verified_role is None:
                verified_role = await role_utils.get_or_create_role(
                    guild, "🍷 Verified", color=discord.Color.gold(),
                    reason="Fortunata setup",
                )
            if unverified_role is None:
                unverified_role = await role_utils.get_or_create_role(
                    guild, "🔒 Unverified", color=discord.Color.dark_grey(),
                    reason="Fortunata setup",
                )
        except role_utils.RoleError as exc:
            await interaction.followup.send(f"⚠️ {exc}", ephemeral=True)
            return

        embed = discord.Embed(
            title=WELCOME_TITLE,
            description=(
                "*The wine is poured, the couches are draped in Tyrian purple, and "
                "Trimalchio wants to know your stars before you take your seat.*\n\n"
                "**Click your Sun sign below** if you already know it, or hit "
                "**Find My Sign** and pick the date range your birthday falls in.\n\n"
                "Once you're in, explore more with:\n"
                "`/placements` — your full birth chart (Sun through Pluto + Rising)\n"
                "`/chinesezodiac` — your Chinese zodiac animal & element\n"
                "`/bloodtype` — blood type astrology\n"
                "`/profile` — see everything Fortunata knows about you"
            ),
            color=0x8E44AD,
        )
        embed.set_footer(text="🍇 Trimalchio's Dinner Party")

        verification_cog = self.bot.get_cog("Verification")
        if verification_cog is None:
            await interaction.followup.send(
                "⚠️ The Verification module isn't loaded — check the bot's startup logs.",
                ephemeral=True,
            )
            return
        view = VerificationPanelView(verification_cog)
        message = await channel.send(embed=embed, view=view)

        await self.db.set_guild_config(
            guild.id,
            verified_role_id=verified_role.id,
            unverified_role_id=unverified_role.id,
            verification_channel_id=channel.id,
            verification_message_id=message.id,
        )

        await interaction.followup.send(
            f"✅ Verification panel posted in {channel.mention}.\n"
            f"Verified role: {verified_role.mention}\n"
            f"Unverified role: {unverified_role.mention}\n\n"
            f"Run `/fortunata lockdown` if you'd like me to automatically hide "
            f"the rest of the server from unverified members.",
            ephemeral=True,
        )

    # ---------------------------------------------------------- lockdown

    @fortunata.command(
        name="lockdown",
        description="Hide every other channel from unverified members (verification channel stays visible to everyone).",
    )
    async def lockdown_cmd(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        assert guild is not None
        config = await self.db.get_guild_config(guild.id)
        if not config or not config.get("unverified_role_id") or not config.get("verified_role_id"):
            await interaction.response.send_message(
                "Run `/fortunata setup` first.", ephemeral=True
            )
            return

        unverified_role = guild.get_role(config["unverified_role_id"])
        verified_role = guild.get_role(config["verified_role_id"])
        verification_channel_id = config.get("verification_channel_id")
        if unverified_role is None or verified_role is None:
            await interaction.response.send_message(
                "Couldn't find the configured roles — re-run `/fortunata setup`.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        updated, failed = 0, 0
        for chan in guild.channels:
            is_verification_chan = chan.id == verification_channel_id
            try:
                if is_verification_chan:
                    await chan.set_permissions(
                        guild.default_role, view_channel=False, reason="Fortunata lockdown"
                    )
                    await chan.set_permissions(
                        unverified_role, view_channel=True, reason="Fortunata lockdown"
                    )
                    await chan.set_permissions(
                        verified_role, view_channel=True, reason="Fortunata lockdown"
                    )
                else:
                    await chan.set_permissions(
                        guild.default_role, view_channel=False, reason="Fortunata lockdown"
                    )
                    await chan.set_permissions(
                        unverified_role, view_channel=False, reason="Fortunata lockdown"
                    )
                    await chan.set_permissions(
                        verified_role, view_channel=True, reason="Fortunata lockdown"
                    )
                updated += 1
            except discord.HTTPException:
                failed += 1
                log.warning("Couldn't set permissions on channel %s", chan)

        await interaction.followup.send(
            f"🔒 Lockdown applied to {updated} channel(s)"
            + (f" ({failed} failed — check my role position/permissions)" if failed else "")
            + ".",
            ephemeral=True,
        )

    # ------------------------------------------------------ backfill-unverified

    @fortunata.command(
        name="backfill-unverified",
        description="Give the Unverified role to every existing member who isn't Verified yet (for members who joined before setup).",
    )
    async def backfill_unverified_cmd(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        assert guild is not None
        config = await self.db.get_guild_config(guild.id)
        if not config or not config.get("unverified_role_id") or not config.get("verified_role_id"):
            await interaction.response.send_message(
                "Run `/fortunata setup` first.", ephemeral=True
            )
            return

        unverified_role = guild.get_role(config["unverified_role_id"])
        verified_role = guild.get_role(config["verified_role_id"])
        if unverified_role is None or verified_role is None:
            await interaction.response.send_message(
                "Couldn't find the configured roles — re-run `/fortunata setup`.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        updated, skipped, failed = 0, 0, 0
        async for member in guild.fetch_members(limit=None):
            if member.bot:
                continue
            if verified_role in member.roles or unverified_role in member.roles:
                skipped += 1
                continue
            try:
                await member.add_roles(
                    unverified_role, reason="Fortunata backfill: existing member pending verification"
                )
                updated += 1
            except discord.HTTPException:
                failed += 1

        await interaction.followup.send(
            f"✅ Gave Unverified to {updated} existing member(s). "
            f"Skipped {skipped} (already Verified/Unverified)"
            + (f", {failed} failed" if failed else "")
            + ".",
            ephemeral=True,
        )

    # ------------------------------------------------------ create-roles

    @fortunata.command(
        name="create-roles",
        description="Pre-create every Fortunata role (so you can reorder/recolor them before people use the bot).",
    )
    async def create_roles_cmd(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        assert guild is not None
        await interaction.response.defer(ephemeral=True, thinking=True)

        created, existed, failed = 0, 0, 0

        async def ensure(name: str, color: int) -> None:
            nonlocal created, existed, failed
            before = discord.utils.get(guild.roles, name=name)
            try:
                await role_utils.get_or_create_role(
                    guild, name, color=discord.Color(color), reason="Fortunata bulk role creation"
                )
                if before is None:
                    created += 1
                else:
                    existed += 1
            except role_utils.RoleError:
                failed += 1

        for key in SIGN_ORDER:
            sign = ZODIAC_SIGNS[key]
            for attr, _label, _emoji in PLANETS:
                await ensure(role_utils.planet_role_name(attr, sign), sign.color)
            await ensure(role_utils.planet_role_name("ascendant", sign), sign.color)

        for animal in ANIMALS:
            await ensure(role_utils.chinese_animal_role_name(animal), 0xC0392B)
        for element in ELEMENTS:
            await ensure(role_utils.chinese_element_role_name(element), 0x99AAB5)

        for blood in BLOOD_TYPES.values():
            await ensure(role_utils.blood_role_name(blood), blood.color)

        await interaction.followup.send(
            f"✅ Done. Created {created} new role(s), {existed} already existed"
            + (f", {failed} failed" if failed else "") + ".",
            ephemeral=True,
        )

    # --------------------------------------------------------------- misc

    @fortunata.command(name="config", description="Show Fortunata's current configuration for this server.")
    async def config_cmd(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        assert guild is not None
        config = await self.db.get_guild_config(guild.id)
        if not config:
            await interaction.response.send_message("Not configured yet — run `/fortunata setup`.", ephemeral=True)
            return

        def fmt_role(rid):
            role = guild.get_role(rid) if rid else None
            return role.mention if role else "*not set*"

        def fmt_channel(cid):
            chan = guild.get_channel(cid) if cid else None
            return chan.mention if chan else "*not set*"

        embed = discord.Embed(title="⚙️ Fortunata Configuration", color=0x8E44AD)
        embed.add_field(name="Verified role", value=fmt_role(config.get("verified_role_id")))
        embed.add_field(name="Unverified role", value=fmt_role(config.get("unverified_role_id")))
        embed.add_field(name="Verification channel", value=fmt_channel(config.get("verification_channel_id")))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @fortunata.command(name="reset", description="Clear a member's stored astrology data.")
    @app_commands.describe(member="Member to reset", remove_roles="Also strip their Fortunata roles")
    async def reset_cmd(
        self, interaction: discord.Interaction, member: discord.Member, remove_roles: bool = True
    ) -> None:
        guild = interaction.guild
        assert guild is not None
        data = await self.db.get_user(guild.id, member.id)
        if not data:
            await interaction.response.send_message("No data on file for that member.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        if remove_roles:
            names = []
            from utils.astrology import get_sign
            for attr, _label, _emoji in PLANETS:
                sign = get_sign(data.get(f"{attr}_sign")) if data.get(f"{attr}_sign") else None
                if sign:
                    names.append(role_utils.planet_role_name(attr, sign))
            asc = get_sign(data.get("ascendant_sign")) if data.get("ascendant_sign") else None
            if asc:
                names.append(role_utils.planet_role_name("ascendant", asc))
            if data.get("chinese_animal"):
                names.append(role_utils.chinese_animal_role_name(data["chinese_animal"]))
            if data.get("chinese_element"):
                names.append(role_utils.chinese_element_role_name(data["chinese_element"]))
            if data.get("blood_type") in BLOOD_TYPES:
                names.append(role_utils.blood_role_name(BLOOD_TYPES[data["blood_type"]]))

            for name in names:
                role = discord.utils.get(guild.roles, name=name)
                if role:
                    try:
                        await member.remove_roles(role, reason="Fortunata reset")
                    except discord.HTTPException:
                        pass

        await self.db.delete_user(guild.id, member.id)
        await interaction.followup.send(f"✅ Cleared Fortunata data for {member.mention}.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
