"""Miscellaneous config commands: log channel + a help/overview command."""

import discord
from discord.ext import commands

from utils import is_staff, styled_embed, success_embed
import db


class Settings(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    settings_group = discord.SlashCommandGroup("settings", "Server configuration")

    @settings_group.command(name="logchannel", description="Set the channel used for moderation/automod logs")
    @is_staff()
    async def logchannel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        await db.update_guild_settings(ctx.guild.id, log_channel_id=channel.id)
        await ctx.respond(embed=success_embed(f"Logs will now be sent in {channel.mention}."))

    @discord.slash_command(name="help", description="Show everything Style-Bot can do")
    async def help_cmd(self, ctx: discord.ApplicationContext):
        embed = styled_embed(
            "Style-Bot commands",
            "Moderation: `/mod kick`, `/mod ban`, `/mod timeout`, `/mod warn`, `/mod clear`\n"
            "Leveling: `/level rank`, `/level leaderboard`, `/level setrole`\n"
            "Welcome: `/welcome channel`, `/welcome message`\n"
            "Automod: `/automod toggle`, `/automod addword`, `/automod anti_invite`\n"
            "Custom commands: `/customcommand add`, `/customcommand list`\n"
            "Reaction roles: `/reactionrole add`\n"
            "Queue: `/queue panel`, `/queue setdisplay`, `/queue reset`\n"
            "Settings: `/settings logchannel`",
        )
        await ctx.respond(embed=embed, ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(Settings(bot))
