"""Style-Bot — a general-purpose Discord server bot (moderation,
welcome messages, automod, custom commands, reaction roles, queue, support panel).

Run with: python discord-bot/bot.py
Requires the DISCORD_BOT_TOKEN environment variable / secret.
"""

import asyncio
import json
import logging
import os
import signal
import time

import aiohttp
from aiohttp import web
import discord
from dotenv import load_dotenv

import db

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("style-bot")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True  # required for on_presence_update to fire

bot = discord.Bot(intents=intents)

_start_time = time.monotonic()


async def health_handler(request: web.Request) -> web.Response:
    """Return bot health status as JSON."""
    uptime_seconds = time.monotonic() - _start_time
    payload = {
        "status": "ok",
        "uptime_seconds": round(uptime_seconds, 2),
        "guild_count": len(bot.guilds),
        "ready": not bot.is_closed(),
    }
    return web.Response(
        text=json.dumps(payload),
        content_type="application/json",
        status=200,
    )


async def run_health_server() -> None:
    """Run a lightweight HTTP server for Railway health checks.

    Uses the PORT env var (set automatically by Railway).  In local / Replit
    dev the env var may be absent or already taken by another service, so
    failures are logged as a warning rather than crashing the bot.
    """
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", health_handler)
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    try:
        await site.start()
        logger.info("Health server listening on port %d", port)
    except OSError as exc:
        logger.warning(
            "Health server could not bind to port %d (%s) — "
            "skipping health endpoint (OK in local/dev environments).",
            port, exc.strerror,
        )
        await runner.cleanup()

COGS = [
    "cogs.moderation",
    "cogs.automod",
    "cogs.welcome",
    "cogs.customcommands",
    "cogs.reactionroles",
    "cogs.queue",
    "cogs.supportpanel",
    "cogs.settings",
    "cogs.presence",
    "cogs.alerts",
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


async def _send_offline_alerts(reason: str = "บอทกำลังปิดตัว") -> None:
    """Send an offline embed to every guild that has alert_channel_id set."""
    from cogs.alerts import offline_embed
    try:
        rows = await db.get_all_alert_channels()
    except Exception:
        return
    for row in rows:
        channel = bot.get_channel(row["alert_channel_id"])
        if channel:
            try:
                await channel.send(embed=offline_embed(reason))
            except Exception:
                pass


def main() -> None:
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN is not set. Add it as a secret before starting the bot."
        )

    for cog in COGS:
        bot.load_extension(cog)

    async def _runner():
        loop = asyncio.get_running_loop()
        shutdown_event = asyncio.Event()

        def _on_signal():
            if not shutdown_event.is_set():
                shutdown_event.set()

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, _on_signal)
            except NotImplementedError:
                pass  # Windows dev environment

        async def _shutdown_watcher():
            await shutdown_event.wait()
            logger.info("Shutdown signal received — sending offline alerts…")
            await _send_offline_alerts()
            await bot.close()

        await db.init_pool()
        await db.run_migrations()
        await run_health_server()
        async with bot:
            watcher = asyncio.create_task(_shutdown_watcher())
            try:
                await bot.start(token)
            finally:
                watcher.cancel()

    asyncio.run(_runner())


if __name__ == "__main__":
    main()
