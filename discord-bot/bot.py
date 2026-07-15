"""Style-Bot — a general-purpose Discord server bot (moderation, leveling,
welcome messages, automod, custom commands, reaction roles), in the spirit
of MEE6.

Run with: python discord-bot/bot.py
Requires the DISCORD_BOT_TOKEN environment variable / secret.
"""

import logging
import os

import discord
from dotenv import load_dotenv

import db

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("style-bot")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = discord.Bot(intents=intents)

COGS = [
    "cogs.moderation",
    "cogs.automod",
    "cogs.leveling",
    "cogs.welcome",
    "cogs.customcommands",
    "cogs.reactionroles",
    "cogs.queue",
    "cogs.supportpanel",
    "cogs.settings",
]


@bot.event
async def on_ready():
    logger.info("Logged in as %s (id=%s)", bot.user, bot.user.id)
    logger.info("Connected to %d server(s).", len(bot.guilds))


@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error: discord.DiscordException):
    from discord.ext import commands as ext_commands

    if isinstance(error, ext_commands.MissingPermissions):
        await ctx.respond("You don't have permission to use this command.", ephemeral=True)
        return
    logger.exception("Command error in /%s", ctx.command.qualified_name if ctx.command else "?", exc_info=error)
    try:
        await ctx.respond("Something went wrong running that command.", ephemeral=True)
    except discord.InteractionResponded:
        pass


def main() -> None:
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN is not set. Add it as a secret before starting the bot."
        )

    async def _setup_db():
        await db.init_pool()

    for cog in COGS:
        bot.load_extension(cog)

    bot.loop.run_until_complete(_setup_db())
    bot.run(token)


if __name__ == "__main__":
    main()
