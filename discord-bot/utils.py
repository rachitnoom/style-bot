"""Shared helpers: permission checks, embed styling, message templating."""

import discord
from discord.ext import commands

BRAND_COLOR = 0x5865F2  # blurple-ish accent used across every embed
ERROR_COLOR = 0xE74C3C
SUCCESS_COLOR = 0x2ECC71


def styled_embed(title: str, description: str = "", color: int = BRAND_COLOR) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    return embed


def error_embed(description: str) -> discord.Embed:
    return discord.Embed(title="Something went wrong", description=description, color=ERROR_COLOR)


def success_embed(description: str) -> discord.Embed:
    return discord.Embed(description=description, color=SUCCESS_COLOR)


def render_template(template: str, member: discord.Member, guild: discord.Guild) -> str:
    return (
        template.replace("{mention}", member.mention)
        .replace("{user}", str(member))
        .replace("{name}", member.display_name)
        .replace("{server}", guild.name)
        .replace("{count}", str(guild.member_count))
    )


def is_staff():
    """Slash-command check: requires Manage Server (used for bot configuration commands)."""

    async def predicate(ctx: discord.ApplicationContext) -> bool:
        if ctx.author.guild_permissions.manage_guild:
            return True
        raise commands.MissingPermissions(["manage_guild"])

    return commands.check(predicate)


def xp_for_level(level: int) -> int:
    """Total XP required to reach `level`. Mirrors the classic MEE6-style curve."""
    return 5 * (level ** 2) + 50 * level + 100


def level_from_xp(xp: int) -> int:
    level = 0
    while xp >= xp_for_level(level + 1):
        level += 1
    return level
