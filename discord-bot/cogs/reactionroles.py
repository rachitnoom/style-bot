"""Reaction-role setup: react to a message with an emoji to receive/remove a role."""

import discord
from discord.ext import commands

import db
from utils import is_staff, success_embed


class ReactionRoles(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    rr_group = discord.SlashCommandGroup("reactionrole", "Set up reaction roles")

    @rr_group.command(name="add", description="Turn a reaction on a message into a role toggle")
    @is_staff()
    async def add(
        self,
        ctx: discord.ApplicationContext,
        message_id: str,
        emoji: str,
        role: discord.Role,
    ):
        try:
            message = await ctx.channel.fetch_message(int(message_id))
        except (discord.NotFound, ValueError):
            await ctx.respond("Couldn't find that message in this channel.", ephemeral=True)
            return

        await message.add_reaction(emoji)
        await db.add_reaction_role(message.id, ctx.guild.id, ctx.channel.id, emoji, role.id)
        await ctx.respond(
            embed=success_embed(f"Reacting with {emoji} on that message now grants {role.mention}."),
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.member is None or payload.member.bot:
            return
        row = await db.get_reaction_role(payload.message_id, str(payload.emoji))
        if not row:
            return
        guild = self.bot.get_guild(payload.guild_id)
        role = guild.get_role(row["role_id"]) if guild else None
        if role:
            try:
                await payload.member.add_roles(role, reason="Reaction role")
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        row = await db.get_reaction_role(payload.message_id, str(payload.emoji))
        if not row:
            return
        member = guild.get_member(payload.user_id)
        role = guild.get_role(row["role_id"])
        if member and role:
            try:
                await member.remove_roles(role, reason="Reaction role removed")
            except discord.Forbidden:
                pass


def setup(bot: discord.Bot):
    bot.add_cog(ReactionRoles(bot))
