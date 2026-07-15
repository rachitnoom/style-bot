"""XP-per-message leveling system with level roles and a leaderboard, MEE6-style."""

import datetime
import random

import discord
from discord.ext import commands

import db
from utils import is_staff, level_from_xp, styled_embed, success_embed, xp_for_level


class Leveling(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    level_group = discord.SlashCommandGroup("level", "Leveling & XP commands")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        settings = await db.get_guild_settings(message.guild.id)
        row = await db.get_level_row(message.guild.id, message.author.id)

        now = datetime.datetime.now(datetime.timezone.utc)
        last = row["last_message_at"]
        cooldown = settings["xp_cooldown_seconds"]
        if last is not None and (now - last).total_seconds() < cooldown:
            return

        gained = random.randint(settings["xp_per_message"], settings["xp_per_message"] + 10)
        new_xp = row["xp"] + gained
        old_level = row["level"]
        new_level = level_from_xp(new_xp)

        await db.add_xp(message.guild.id, message.author.id, gained, new_level, now)

        if new_level > old_level:
            await self._handle_level_up(message, new_level, settings)

    async def _handle_level_up(self, message: discord.Message, new_level: int, settings) -> None:
        channel = message.channel
        if settings["level_up_channel_id"]:
            target = message.guild.get_channel(settings["level_up_channel_id"])
            if target:
                channel = target
        try:
            await channel.send(
                embed=success_embed(f"🎉 {message.author.mention} just reached **level {new_level}**!")
            )
        except discord.Forbidden:
            pass

        for role_row in await db.get_level_roles(message.guild.id):
            if role_row["level"] == new_level:
                role = message.guild.get_role(role_row["role_id"])
                if role:
                    try:
                        await message.author.add_roles(role, reason=f"Reached level {new_level}")
                    except discord.Forbidden:
                        pass

    @level_group.command(name="rank", description="Show your (or someone else's) level and XP")
    async def rank(self, ctx: discord.ApplicationContext, member: discord.Member = None):
        member = member or ctx.author
        row = await db.get_level_row(ctx.guild.id, member.id)
        rank = await db.get_rank(ctx.guild.id, member.id)
        next_level_xp = xp_for_level(row["level"] + 1)
        embed = styled_embed(
            f"Rank — {member.display_name}",
            f"**Level:** {row['level']}\n**XP:** {row['xp']} / {next_level_xp}\n**Server rank:** #{rank}",
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.respond(embed=embed)

    @level_group.command(name="leaderboard", description="Show the server's top members by XP")
    async def leaderboard(self, ctx: discord.ApplicationContext):
        rows = await db.get_leaderboard(ctx.guild.id, limit=10)
        if not rows:
            await ctx.respond(embed=styled_embed("Leaderboard", "No one has earned XP yet."))
            return
        lines = []
        for i, row in enumerate(rows, start=1):
            member = ctx.guild.get_member(row["user_id"])
            name = member.display_name if member else f"User {row['user_id']}"
            lines.append(f"**{i}.** {name} — Level {row['level']} ({row['xp']} XP)")
        await ctx.respond(embed=styled_embed("🏆 Leaderboard", "\n".join(lines)))

    @level_group.command(name="setrole", description="Assign a role to be granted at a given level")
    @is_staff()
    async def setrole(self, ctx: discord.ApplicationContext, level: int, role: discord.Role):
        await db.set_level_role(ctx.guild.id, level, role.id)
        await ctx.respond(embed=success_embed(f"Members reaching level {level} will now receive {role.mention}."))

    @level_group.command(name="removerole", description="Remove a level-role reward")
    @is_staff()
    async def removerole(self, ctx: discord.ApplicationContext, level: int):
        await db.remove_level_role(ctx.guild.id, level)
        await ctx.respond(embed=success_embed(f"Removed the level-role reward for level {level}."))

    @level_group.command(name="setchannel", description="Set the channel used for level-up announcements")
    @is_staff()
    async def setchannel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        await db.update_guild_settings(ctx.guild.id, level_up_channel_id=channel.id)
        await ctx.respond(embed=success_embed(f"Level-up announcements will now be sent in {channel.mention}."))


def setup(bot: discord.Bot):
    bot.add_cog(Leveling(bot))
