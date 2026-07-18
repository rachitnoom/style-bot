"""Alerts cog — sends online/offline notifications to a configured channel.

On every `on_ready` the bot posts a 🟢 online embed.
The offline embed is sent by bot.py's SIGTERM handler before the bot closes.

Reconnect suppression
---------------------
Discord's Gateway can disconnect and reconnect automatically within seconds
during a network blip.  Each reconnect fires ``on_ready``, which would spam
the alert channel with false-alarm "bot is online" messages.

To prevent this the cog tracks the monotonic time of the last online embed it
sent.  If ``on_ready`` fires again within ``ONLINE_ALERT_COOLDOWN_SECONDS``
(default 60 s) the embed is suppressed and the event is logged at INFO level
so operators can see that a reconnect was detected but was intentionally
squelched.
"""

import logging
import time

import discord
from discord.ext import commands

import db
from utils import is_staff, success_embed

logger = logging.getLogger(__name__)

# Minimum seconds between consecutive "bot is online" embeds.
# Reconnects within this window are treated as transient blips and suppressed.
ONLINE_ALERT_COOLDOWN_SECONDS: int = 60


def online_embed(bot: discord.Bot) -> discord.Embed:
    latency_ms = round(bot.latency * 1000) if bot.latency else 0
    embed = discord.Embed(
        title="🟢 บอทออนไลน์แล้ว",
        description="Style-Bot เชื่อมต่อกับ Discord สำเร็จ",
        color=0x2ECC71,
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="Latency", value=f"{latency_ms} ms", inline=True)
    embed.add_field(name="เซิร์ฟเวอร์", value=str(len(bot.guilds)), inline=True)
    embed.set_footer(text="Style-Bot")
    return embed


def offline_embed(reason: str = "บอทกำลังปิดตัว") -> discord.Embed:
    embed = discord.Embed(
        title="🔴 บอทออฟไลน์",
        description=reason,
        color=0xE74C3C,
        timestamp=discord.utils.utcnow(),
    )
    embed.set_footer(text="Style-Bot")
    return embed


def recovery_embed(reason: str = "Uptime monitor reports recovery") -> discord.Embed:
    """Green embed posted when the uptime monitor reports the bot is back up."""
    embed = discord.Embed(
        title="🟢 บอทกลับมาออนไลน์",
        description=reason,
        color=0x2ECC71,
        timestamp=discord.utils.utcnow(),
    )
    embed.set_footer(text="Style-Bot")
    return embed


class Alerts(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        # Monotonic timestamp of the last "bot is online" embed we sent.
        # None means we haven't sent one yet this process lifetime.
        self._last_online_alert: float | None = None

    @commands.Cog.listener()
    async def on_ready(self):
        """Send an online alert to every guild that has alert_channel_id set.

        If ``on_ready`` fires again within ``ONLINE_ALERT_COOLDOWN_SECONDS``
        of the previous alert (e.g. a brief network blip caused an automatic
        reconnect) the embed is suppressed to avoid spamming the alert channel.
        """
        now = time.monotonic()

        if self._last_online_alert is not None:
            elapsed = now - self._last_online_alert
            if elapsed < ONLINE_ALERT_COOLDOWN_SECONDS:
                logger.info(
                    "on_ready fired %.1f s after the last online alert "
                    "(cooldown=%d s) — suppressing duplicate embed.",
                    elapsed,
                    ONLINE_ALERT_COOLDOWN_SECONDS,
                )
                return

        self._last_online_alert = now

        rows = await db.get_all_alert_channels()
        for row in rows:
            channel = self.bot.get_channel(row["alert_channel_id"])
            if channel:
                try:
                    await channel.send(embed=online_embed(self.bot))
                except discord.HTTPException:
                    pass

    # ------------------------------------------------------------------
    # /settings alertchannel  (registered here, shown in settings help)
    # ------------------------------------------------------------------

    alerts_group = discord.SlashCommandGroup(
        "alerts", "ตั้งค่าการแจ้งเตือนสถานะบอท"
    )

    @alerts_group.command(
        name="channel",
        description="กำหนดห้องที่บอทจะส่งข้อความแจ้งเตือนเมื่อออนไลน์/ออฟไลน์",
    )
    @is_staff()
    async def set_alert_channel(
        self, ctx: discord.ApplicationContext, channel: discord.TextChannel
    ):
        await db.update_guild_settings(ctx.guild.id, alert_channel_id=channel.id)
        await ctx.respond(
            embed=success_embed(
                f"จะส่งข้อความแจ้งเตือนสถานะบอทไปที่ {channel.mention}"
            ),
            ephemeral=True,
        )

    @alerts_group.command(
        name="disable",
        description="ปิดการแจ้งเตือนสถานะบอทสำหรับเซิร์ฟเวอร์นี้",
    )
    @is_staff()
    async def disable_alert_channel(self, ctx: discord.ApplicationContext):
        await db.update_guild_settings(ctx.guild.id, alert_channel_id=None)
        await ctx.respond(
            embed=success_embed("ปิดการแจ้งเตือนสถานะบอทแล้ว"),
            ephemeral=True,
        )

    @alerts_group.command(
        name="test",
        description="ทดสอบส่งข้อความแจ้งเตือนไปยังห้องที่ตั้งค่าไว้",
    )
    @is_staff()
    async def test_alert(self, ctx: discord.ApplicationContext):
        row = await db.get_guild_settings(ctx.guild.id)
        channel_id = row["alert_channel_id"]
        if not channel_id:
            await ctx.respond(
                "ยังไม่ได้ตั้งค่าห้องแจ้งเตือน ใช้ `/alerts channel` ก่อน",
                ephemeral=True,
            )
            return
        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            await ctx.respond("ไม่พบห้องที่ตั้งค่าไว้ กรุณาตั้งค่าใหม่", ephemeral=True)
            return
        await channel.send(embed=online_embed(self.bot))
        await channel.send(embed=offline_embed("นี่คือข้อความทดสอบ — บอทยังออนไลน์อยู่"))
        await ctx.respond("ส่งข้อความทดสอบเรียบร้อยแล้ว ✅", ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(Alerts(bot))
