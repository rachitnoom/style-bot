"""Welcome / leave messages, configurable per server with {placeholders}."""

import discord
from discord.ext import commands

import db
from utils import is_staff, render_template, styled_embed, success_embed

PLACEHOLDER_HELP = "Available placeholders: {mention}, {user}, {name}, {server}, {count}"


class Welcome(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    welcome_group = discord.SlashCommandGroup("welcome", "Configure welcome & leave messages")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        settings = await db.get_guild_settings(member.guild.id)
        if not settings["welcome_channel_id"]:
            return
        channel = member.guild.get_channel(settings["welcome_channel_id"])
        if not channel:
            return
        text = render_template(settings["welcome_message"], member, member.guild)
        embed = styled_embed("👋 New member!", text)
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        settings = await db.get_guild_settings(member.guild.id)
        if not settings["leave_channel_id"]:
            return
        channel = member.guild.get_channel(settings["leave_channel_id"])
        if not channel:
            return
        text = render_template(settings["leave_message"], member, member.guild)
        await channel.send(embed=styled_embed("👋 Member left", text))

    @welcome_group.command(name="channel", description="Set the channel for welcome messages")
    @is_staff()
    async def channel_cmd(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        await db.update_guild_settings(ctx.guild.id, welcome_channel_id=channel.id)
        await ctx.respond(embed=success_embed(f"Welcome messages will now be sent in {channel.mention}."))

    @welcome_group.command(name="message", description="Set the welcome message template")
    @is_staff()
    async def message_cmd(self, ctx: discord.ApplicationContext, template: str):
        await db.update_guild_settings(ctx.guild.id, welcome_message=template)
        await ctx.respond(embed=success_embed(f"Welcome message updated.\n{PLACEHOLDER_HELP}"))

    @welcome_group.command(name="leave_channel", description="Set the channel for leave messages")
    @is_staff()
    async def leave_channel_cmd(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        await db.update_guild_settings(ctx.guild.id, leave_channel_id=channel.id)
        await ctx.respond(embed=success_embed(f"Leave messages will now be sent in {channel.mention}."))

    @welcome_group.command(name="leave_message", description="Set the leave message template")
    @is_staff()
    async def leave_message_cmd(self, ctx: discord.ApplicationContext, template: str):
        await db.update_guild_settings(ctx.guild.id, leave_message=template)
        await ctx.respond(embed=success_embed(f"Leave message updated.\n{PLACEHOLDER_HELP}"))

    @welcome_group.command(name="test", description="Preview the welcome message using your own account")
    @is_staff()
    async def test(self, ctx: discord.ApplicationContext):
        settings = await db.get_guild_settings(ctx.guild.id)
        text = render_template(settings["welcome_message"], ctx.author, ctx.guild)
        await ctx.respond(embed=styled_embed("👋 New member! (preview)", text))


def setup(bot: discord.Bot):
    bot.add_cog(Welcome(bot))
