"""Kick, ban, timeout, warn, and message-purge commands."""

import discord
from discord.ext import commands

import db
from utils import error_embed, styled_embed, success_embed


async def _log_action(guild: discord.Guild, description: str) -> None:
    settings = await db.get_guild_settings(guild.id)
    log_channel_id = settings["log_channel_id"]
    if not log_channel_id:
        return
    channel = guild.get_channel(log_channel_id)
    if channel:
        await channel.send(embed=styled_embed("Moderation Log", description))


class Moderation(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    moderation = discord.SlashCommandGroup("mod", "Moderation commands")

    @moderation.command(name="kick", description="Kick a member from the server")
    @discord.default_permissions(kick_members=True)
    async def kick(self, ctx: discord.ApplicationContext, member: discord.Member, reason: str = "No reason provided"):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            await ctx.respond(embed=error_embed("You can't kick someone with an equal or higher role."), ephemeral=True)
            return
        await member.kick(reason=f"{ctx.author}: {reason}")
        await ctx.respond(embed=success_embed(f"👢 {member.mention} was kicked. Reason: {reason}"))
        await _log_action(ctx.guild, f"**Kick** — {member} by {ctx.author} — {reason}")

    @moderation.command(name="ban", description="Ban a member from the server")
    @discord.default_permissions(ban_members=True)
    async def ban(self, ctx: discord.ApplicationContext, member: discord.Member, reason: str = "No reason provided"):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            await ctx.respond(embed=error_embed("You can't ban someone with an equal or higher role."), ephemeral=True)
            return
        await member.ban(reason=f"{ctx.author}: {reason}")
        await ctx.respond(embed=success_embed(f"🔨 {member.mention} was banned. Reason: {reason}"))
        await _log_action(ctx.guild, f"**Ban** — {member} by {ctx.author} — {reason}")

    @moderation.command(name="unban", description="Unban a user by ID")
    @discord.default_permissions(ban_members=True)
    async def unban(self, ctx: discord.ApplicationContext, user_id: str):
        user = discord.Object(id=int(user_id))
        await ctx.guild.unban(user)
        await ctx.respond(embed=success_embed(f"✅ Unbanned user ID {user_id}."))
        await _log_action(ctx.guild, f"**Unban** — {user_id} by {ctx.author}")

    @moderation.command(name="timeout", description="Timeout (mute) a member for N minutes")
    @discord.default_permissions(moderate_members=True)
    async def timeout(self, ctx: discord.ApplicationContext, member: discord.Member, minutes: int, reason: str = "No reason provided"):
        import datetime

        duration = datetime.timedelta(minutes=minutes)
        await member.timeout_for(duration, reason=f"{ctx.author}: {reason}")
        await ctx.respond(embed=success_embed(f"🔇 {member.mention} was timed out for {minutes} minute(s). Reason: {reason}"))
        await _log_action(ctx.guild, f"**Timeout** — {member} for {minutes}m by {ctx.author} — {reason}")

    @moderation.command(name="untimeout", description="Remove an active timeout from a member")
    @discord.default_permissions(moderate_members=True)
    async def untimeout(self, ctx: discord.ApplicationContext, member: discord.Member):
        await member.remove_timeout()
        await ctx.respond(embed=success_embed(f"🔊 Timeout removed for {member.mention}."))

    @moderation.command(name="warn", description="Issue a warning to a member")
    @discord.default_permissions(moderate_members=True)
    async def warn(self, ctx: discord.ApplicationContext, member: discord.Member, reason: str = "No reason provided"):
        warn_id = await db.add_warning(ctx.guild.id, member.id, ctx.author.id, reason)
        await ctx.respond(embed=success_embed(f"⚠️ {member.mention} was warned (#{warn_id}). Reason: {reason}"))
        await _log_action(ctx.guild, f"**Warn** — {member} by {ctx.author} — {reason}")
        try:
            await member.send(embed=styled_embed("You received a warning", f"Server: {ctx.guild.name}\nReason: {reason}"))
        except discord.Forbidden:
            pass

    @moderation.command(name="warnings", description="List a member's warnings")
    @discord.default_permissions(moderate_members=True)
    async def warnings(self, ctx: discord.ApplicationContext, member: discord.Member):
        rows = await db.get_warnings(ctx.guild.id, member.id)
        if not rows:
            await ctx.respond(embed=styled_embed("Warnings", f"{member.mention} has no warnings."))
            return
        lines = [f"**#{r['id']}** — {r['reason']} ({r['created_at'].strftime('%Y-%m-%d')})" for r in rows]
        await ctx.respond(embed=styled_embed(f"Warnings for {member.display_name}", "\n".join(lines)))

    @moderation.command(name="clearwarnings", description="Clear all warnings for a member")
    @discord.default_permissions(moderate_members=True)
    async def clearwarnings(self, ctx: discord.ApplicationContext, member: discord.Member):
        await db.clear_warnings(ctx.guild.id, member.id)
        await ctx.respond(embed=success_embed(f"🧹 Cleared all warnings for {member.mention}."))

    @moderation.command(name="clear", description="Delete a number of recent messages in this channel")
    @discord.default_permissions(manage_messages=True)
    async def clear(self, ctx: discord.ApplicationContext, amount: discord.Option(int, min_value=1, max_value=100)):
        await ctx.defer(ephemeral=True)
        deleted = await ctx.channel.purge(limit=amount)
        await ctx.respond(embed=success_embed(f"🧹 Deleted {len(deleted)} message(s)."), ephemeral=True)
        await _log_action(ctx.guild, f"**Purge** — {len(deleted)} messages in #{ctx.channel.name} by {ctx.author}")


def setup(bot: discord.Bot):
    bot.add_cog(Moderation(bot))
