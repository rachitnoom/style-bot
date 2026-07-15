"""Per-server custom text commands, triggered with the server's prefix (default '!')."""

import discord
from discord.ext import commands

import db
from utils import is_staff, styled_embed, success_embed


class CustomCommands(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    cc_group = discord.SlashCommandGroup("customcommand", "Manage custom text commands")

    @cc_group.command(name="add", description="Add (or update) a custom command")
    @is_staff()
    async def add(self, ctx: discord.ApplicationContext, name: str, response: str):
        await db.add_custom_command(ctx.guild.id, name, response, ctx.author.id)
        prefix = (await db.get_guild_settings(ctx.guild.id))["command_prefix"]
        await ctx.respond(embed=success_embed(f"Custom command `{prefix}{name.lower()}` saved."))

    @cc_group.command(name="remove", description="Remove a custom command")
    @is_staff()
    async def remove(self, ctx: discord.ApplicationContext, name: str):
        await db.remove_custom_command(ctx.guild.id, name)
        await ctx.respond(embed=success_embed(f"Custom command `{name.lower()}` removed (if it existed)."))

    @cc_group.command(name="list", description="List all custom commands on this server")
    async def list_cmd(self, ctx: discord.ApplicationContext):
        rows = await db.list_custom_commands(ctx.guild.id)
        prefix = (await db.get_guild_settings(ctx.guild.id))["command_prefix"]
        if not rows:
            await ctx.respond(embed=styled_embed("Custom commands", "No custom commands yet."))
            return
        names = ", ".join(f"`{prefix}{r['name']}`" for r in rows)
        await ctx.respond(embed=styled_embed("Custom commands", names))

    @cc_group.command(name="prefix", description="Change the prefix used to trigger custom commands")
    @is_staff()
    async def prefix(self, ctx: discord.ApplicationContext, new_prefix: str):
        await db.update_guild_settings(ctx.guild.id, command_prefix=new_prefix)
        await ctx.respond(embed=success_embed(f"Custom command prefix set to `{new_prefix}`."))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        settings = await db.get_guild_settings(message.guild.id)
        prefix = settings["command_prefix"]
        if not message.content.startswith(prefix):
            return
        name = message.content[len(prefix):].split(" ")[0].lower()
        if not name:
            return
        row = await db.get_custom_command(message.guild.id, name)
        if row:
            await message.channel.send(row["response"])


def setup(bot: discord.Bot):
    bot.add_cog(CustomCommands(bot))
