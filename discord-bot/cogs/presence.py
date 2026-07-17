"""Presence tracking cog — records member online/offline events to PostgreSQL."""

import logging

import discord
from discord.ext import commands

import db

logger = logging.getLogger("style-bot.presence")

# Map Discord status objects to the DB enum strings
_STATUS_MAP = {
    discord.Status.online: "online",
    discord.Status.idle: "idle",
    discord.Status.dnd: "dnd",
    discord.Status.do_not_disturb: "dnd",
    discord.Status.offline: "offline",
    discord.Status.invisible: "offline",
}


def _status_str(status: discord.Status) -> str:
    return _STATUS_MAP.get(status, "offline")


class Presence(commands.Cog):
    """Listens for presence changes and persists them to the database."""

    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_presence_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        if before.status == after.status:
            return  # no meaningful change

        status = _status_str(after.status)
        try:
            await db.record_presence_event(
                guild_id=after.guild.id,
                user_id=after.id,
                username=str(after),
                status=status,
            )
        except Exception:
            logger.exception(
                "Failed to record presence event for user %s (%s) in guild %s",
                after,
                after.id,
                after.guild.id,
            )

    @commands.Cog.listener()
    async def on_member_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        # Presence changes sometimes arrive via member_update when
        # on_presence_update is not triggered (e.g. mobile status).
        # We deduplicate by checking the status changed.
        pass  # handled entirely by on_presence_update

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """Mark a departing member as offline."""
        try:
            await db.record_presence_event(
                guild_id=member.guild.id,
                user_id=member.id,
                username=str(member),
                status="offline",
            )
        except Exception:
            logger.exception(
                "Failed to record offline event for leaving member %s (%s)",
                member,
                member.id,
            )


def setup(bot: discord.Bot) -> None:
    bot.add_cog(Presence(bot))
