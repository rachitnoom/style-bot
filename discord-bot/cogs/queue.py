"""Queue-ticket system: members claim a numbered ticket (1-100) with a button,
and release it with another button once served. A live sorted list is kept
up to date in a dedicated display channel.
"""

import discord
from discord.ext import commands

import db
from utils import error_embed, is_staff, styled_embed, success_embed

TAKE_CUSTOM_ID = "queue_take_ticket"
DONE_CUSTOM_ID = "queue_complete_ticket"


def _panel_embed() -> discord.Embed:
    embed = styled_embed(
        "🎫 ระบบคิว",
        f"กดปุ่ม **รับคิว** เพื่อรับหมายเลขคิว (1-{db.QUEUE_MAX})\n"
        "กดปุ่ม **เสร็จสิ้น** เมื่อใช้บริการเรียบร้อยแล้วเพื่อคืนคิวของคุณ",
    )
    return embed


def _display_embed(tickets: list) -> discord.Embed:
    if not tickets:
        description = "_ยังไม่มีคิว_"
    else:
        description = "\n".join(f"**{t['number']}** — {t['display_name']}" for t in tickets)
    embed = styled_embed(f"📋 คิวปัจจุบัน ({len(tickets)}/{db.QUEUE_MAX})", description)
    return embed


class QueuePanelView(discord.ui.View):
    """Persistent view attached to the queue control panel message."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="รับคิว", style=discord.ButtonStyle.green, custom_id=TAKE_CUSTOM_ID)
    async def take(self, button: discord.ui.Button, interaction: discord.Interaction):
        cog: "Queue" = interaction.client.get_cog("Queue")
        await cog.handle_take(interaction)

    @discord.ui.button(label="เสร็จสิ้น", style=discord.ButtonStyle.red, custom_id=DONE_CUSTOM_ID)
    async def done(self, button: discord.ui.Button, interaction: discord.Interaction):
        cog: "Queue" = interaction.client.get_cog("Queue")
        await cog.handle_done(interaction)


class Queue(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Re-register the persistent view so the buttons keep working after a restart.
        self.bot.add_view(QueuePanelView())

    queue_group = discord.SlashCommandGroup("queue", "Ticket-queue system")

    @queue_group.command(name="panel", description="โพสต์แผงปุ่มรับคิว/เสร็จสิ้นในช่องนี้")
    @is_staff()
    async def panel(self, ctx: discord.ApplicationContext):
        message = await ctx.channel.send(embed=_panel_embed(), view=QueuePanelView())
        await db.update_guild_settings(
            ctx.guild.id,
            queue_panel_channel_id=ctx.channel.id,
            queue_panel_message_id=message.id,
        )
        await ctx.respond(embed=success_embed("โพสต์แผงคิวเรียบร้อยแล้ว"), ephemeral=True)

    @queue_group.command(name="setdisplay", description="กำหนดช่องที่จะแสดงรายชื่อคิวแบบเรียงลำดับ")
    @is_staff()
    async def setdisplay(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        tickets = await db.list_active_tickets(ctx.guild.id)
        message = await channel.send(embed=_display_embed(tickets))
        await db.update_guild_settings(
            ctx.guild.id,
            queue_display_channel_id=channel.id,
            queue_display_message_id=message.id,
        )
        await ctx.respond(
            embed=success_embed(f"ตั้งค่าช่องแสดงคิวเป็น {channel.mention} แล้ว"),
            ephemeral=True,
        )

    @queue_group.command(name="reset", description="ล้างคิวทั้งหมด (สำหรับเริ่มรอบใหม่)")
    @is_staff()
    async def reset(self, ctx: discord.ApplicationContext):
        await db.clear_all_tickets(ctx.guild.id)
        await self._refresh_display(ctx.guild)
        await ctx.respond(embed=success_embed("ล้างคิวทั้งหมดแล้ว"), ephemeral=True)

    async def handle_take(self, interaction: discord.Interaction):
        guild = interaction.guild
        number = await db.claim_next_ticket(guild.id, interaction.user.id, str(interaction.user.display_name))
        if number is None:
            await interaction.response.send_message(
                embed=error_embed(f"คิวเต็มแล้ว (สูงสุด {db.QUEUE_MAX} คิว)"), ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=success_embed(f"คุณได้รับคิวหมายเลข **{number}**"), ephemeral=True
        )
        await self._refresh_display(guild)

    async def handle_done(self, interaction: discord.Interaction):
        guild = interaction.guild
        freed = await db.complete_ticket(guild.id, interaction.user.id)
        if freed is None:
            await interaction.response.send_message(
                embed=error_embed("คุณไม่มีคิวที่กำลังใช้งานอยู่"), ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=success_embed(f"คิวหมายเลข **{freed}** เสร็จสิ้นแล้ว ขอบคุณครับ/ค่ะ"), ephemeral=True
        )
        await self._refresh_display(guild)

    async def _refresh_display(self, guild: discord.Guild):
        settings = await db.get_guild_settings(guild.id)
        channel_id = settings["queue_display_channel_id"]
        message_id = settings["queue_display_message_id"]
        if not channel_id:
            return

        channel = guild.get_channel(channel_id)
        if channel is None:
            return

        tickets = await db.list_active_tickets(guild.id)
        embed = _display_embed(tickets)

        message = None
        if message_id:
            try:
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                message = None

        if message is not None:
            await message.edit(embed=embed)
        else:
            message = await channel.send(embed=embed)
            await db.update_guild_settings(guild.id, queue_display_message_id=message.id)


def setup(bot: discord.Bot):
    bot.add_cog(Queue(bot))
