"""
Role naming conventions + a get-or-create helper shared by every cog, so
"Sun in Aries" (created during quick verification) is the exact same role
used later by the full /placements chart, etc.
"""
from __future__ import annotations

import logging

import discord

from utils.astrology import ZodiacSign
from utils.chart import PLANETS, ASCENDANT_LABEL
from utils.chinese import ANIMAL_EMOJI, ELEMENT_EMOJI as CN_ELEMENT_EMOJI
from utils.blood import BloodType

log = logging.getLogger("fortunata.roles")


class RoleError(RuntimeError):
    pass


def sun_role_name(sign: ZodiacSign) -> str:
    return f"☀️ Sun in {sign.name}"


def planet_role_name(planet_key: str, sign: ZodiacSign) -> str:
    if planet_key == "sun":
        return sun_role_name(sign)
    if planet_key == "ascendant":
        label, emoji = ASCENDANT_LABEL
        return f"{emoji} {label} in {sign.name}"
    for attr, label, emoji in PLANETS:
        if attr == planet_key:
            return f"{emoji} {label} in {sign.name}"
    raise ValueError(f"Unknown planet key: {planet_key}")


def chinese_animal_role_name(animal: str) -> str:
    return f"{ANIMAL_EMOJI.get(animal, '')} Year of the {animal}".strip()


def chinese_element_role_name(element: str) -> str:
    return f"{CN_ELEMENT_EMOJI.get(element, '')} {element} Element".strip()


def blood_role_name(blood: BloodType) -> str:
    return f"{blood.emoji} Blood Type {blood.label.replace('Type ', '')}"


async def get_or_create_role(
    guild: discord.Guild,
    name: str,
    *,
    color: discord.Color | None = None,
    hoist: bool = False,
    mentionable: bool = False,
    reason: str = "Fortunata role",
) -> discord.Role:
    existing = discord.utils.get(guild.roles, name=name)
    if existing is not None:
        return existing
    try:
        return await guild.create_role(
            name=name,
            color=color or discord.Color.default(),
            hoist=hoist,
            mentionable=mentionable,
            reason=reason,
        )
    except discord.Forbidden as exc:
        raise RoleError(
            f"I don't have permission to create the role '{name}'. Make "
            f"sure my top role is above where new roles should go and I "
            f"have the Manage Roles permission."
        ) from exc
    except discord.HTTPException as exc:
        raise RoleError(f"Discord rejected creating the role '{name}': {exc}") from exc


async def assign_role(member: discord.Member, role: discord.Role, *, reason: str = "") -> None:
    try:
        await member.add_roles(role, reason=reason or "Fortunata role assignment")
    except discord.Forbidden as exc:
        raise RoleError(
            f"I don't have permission to give {member} the role '{role.name}'. "
            f"My top role needs to be above '{role.name}' in the role list."
        ) from exc
    except discord.HTTPException as exc:
        raise RoleError(f"Discord rejected assigning '{role.name}': {exc}") from exc


async def remove_role(member: discord.Member, role: discord.Role, *, reason: str = "") -> None:
    try:
        if role in member.roles:
            await member.remove_roles(role, reason=reason or "Fortunata role update")
    except discord.Forbidden as exc:
        raise RoleError(
            f"I don't have permission to remove '{role.name}' from {member}."
        ) from exc
    except discord.HTTPException as exc:
        raise RoleError(f"Discord rejected removing '{role.name}': {exc}") from exc


async def replace_category_role(
    member: discord.Member,
    guild: discord.Guild,
    old_role_name: str | None,
    new_role: discord.Role,
    *,
    reason: str = "",
) -> None:
    """Remove a member's previous role in a category (e.g. their old Sun
    sign role) before/while adding the new one, so members don't collect
    stale placement roles when they re-run a command with new data."""
    if old_role_name and old_role_name != new_role.name:
        old_role = discord.utils.get(guild.roles, name=old_role_name)
        if old_role is not None:
            await remove_role(member, old_role, reason=reason)
    await assign_role(member, new_role, reason=reason)
