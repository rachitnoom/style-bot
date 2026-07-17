"""Support panel: two buttons — call an admin and request help.
Clicking either button posts an alert into a configured channel.
"""

import discord
from discord.ext import commands

import db
from utils import error_embed, is_staff, styled_embed, success_embed

CALL_ADMIN_ID = "supportpanel_call_admin"
CALL_HELP_ID = "supportpanel_call_help"


def _panel_embed() -> discord.Embed:
    return styled_embed(
        "🛎️ ศูนย์ช่วยเหลือ",
        "🔔 **เรียกแอดมิน** — แจ้งเตือนแอดมินให้มาดูแล\n"
        "🙋 **ขอความช่วยเหลือ** — แจ้งเตือนทีมช่วยเหลือ",
    )


def _mention_target(settings) -> str:
    target_id = settings["admin_target_id"]
    target_type = settings["admin_target_type"]
    if not target_id:
        return ""
    return f"<@&{target_id}>" if target_type == "role" else f"<@{target_id}>"


class SupportPanelView(discord.ui.View):
    """Persistent view attached to the support panel message."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="เรียกแอดมิน", emoji="🔔", style=discord.ButtonStyle.red, custom_id=CALL_ADMIN_ID)
    async def call_admin(self, button: discord.ui.Button, interaction: discord.Interaction):
        cog: "SupportPanel" = interaction.client.get_cog("SupportPanel")
        await cog.handle_call_admin(interaction)

    @discord.ui.button(label="ขอความช่วยเหลือ", emoji="🙋", style=discord.ButtonStyle.primary, custom_id=CALL_HELP_ID)
    async def call_help(self, button: discord.ui.Button, interaction: discord.Interaction):
        cog: "SupportPanel" = interaction.client.get_cog("SupportPanel")
        await cog.handle_call_help(interaction)



class SupportPanel(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Re-register the persistent view so the buttons keep working after a restart.
        self.bot.add_view(SupportPanelView())

    panel_group = discord.SlashCommandGroup("supportpanel", "Support-panel (call admin / help / self-role) setup")

    @panel_group.command(name="setadmin", description="กำหนดผู้ใช้หรือบทบาทที่จะถูกเรียกด้วยปุ่ม 'เรียกแอดมิน'")
    @is_staff()
    async def setadmin(
        self,
        ctx: discord.ApplicationContext,
        user: discord.Option(discord.Member, "ผู้ใช้ที่จะแจ้งเตือน", required=False, default=None),
        role: discord.Option(discord.Role, "บทบาทที่จะแจ้งเตือน", required=False, default=None),
    ):
        if not user and not role:
            await ctx.respond(embed=error_embed("ระบุ user หรือ role อย่างใดอย่างหนึ่ง"), ephemeral=True)
            return
        if user and role:
            await ctx.respond(embed=error_embed("ระบุได้แค่ user หรือ role อย่างเดียว ไม่ใช่ทั้งสอง"), ephemeral=True)
            return
        target = user or role
        target_type = "user" if user else "role"
        await db.update_support_panel_settings(
            ctx.guild.id, admin_target_id=target.id, admin_target_type=target_type
        )
        await ctx.respond(embed=success_embed(f"ปุ่ม 'เรียกแอดมิน' จะแจ้งเตือน {target.mention} แล้ว"), ephemeral=True)

    @panel_group.command(name="sethelper", description="กำหนดบทบาทที่จะถูกเรียกด้วยปุ่ม 'ขอความช่วยเหลือ'")
    @is_staff()
    async def sethelper(self, ctx: discord.ApplicationContext, role: discord.Role):
        await db.update_support_panel_settings(ctx.guild.id, helper_role_id=role.id)
        await ctx.respond(embed=success_embed(f"ปุ่ม 'ขอความช่วยเหลือ' จะแจ้งเตือน {role.mention} แล้ว"), ephemeral=True)

    @panel_group.command(name="setchannel", description="กำหนดห้องที่จะรับการแจ้งเตือนจากปุ่มเรียกแอดมิน/ขอความช่วยเหลือ")
    @is_staff()
    async def setchannel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        await db.update_support_panel_settings(ctx.guild.id, notify_channel_id=channel.id)
        await ctx.respond(embed=success_embed(f"การแจ้งเตือนจะถูกส่งไปที่ {channel.mention} แล้ว"), ephemeral=True)

    @panel_group.command(name="panel", description="โพสต์แผงปุ่มเรียกแอดมิน/ขอความช่วยเหลือ/รับบทบาทในช่องนี้")
    @is_staff()
    async def panel(self, ctx: discord.ApplicationContext):
        settings = await db.get_support_panel_settings(ctx.guild.id)
        missing = []
        if not settings["admin_target_id"]:
            missing.append("`/supportpanel setadmin`")
        if not settings["helper_role_id"]:
            missing.append("`/supportpanel sethelper`")
        if not settings["notify_channel_id"]:
            missing.append("`/supportpanel setchannel`")
        if missing:
            await ctx.respond(
                embed=error_embed("ยังไม่ได้ตั้งค่าครบ กรุณาใช้คำสั่งต่อไปนี้ก่อน: " + ", ".join(missing)),
                ephemeral=True,
            )
            return

        message = await ctx.channel.send(embed=_panel_embed(), view=SupportPanelView())
        await db.update_support_panel_settings(
            ctx.guild.id, panel_channel_id=ctx.channel.id, panel_message_id=message.id
        )
        await ctx.respond(embed=success_embed("โพสต์แผงศูนย์ช่วยเหลือเรียบร้อยแล้ว"), ephemeral=True)

    async def _notify_channel(self, guild: discord.Guild, settings) -> discord.TextChannel | None:
        channel_id = settings["notify_channel_id"]
        return guild.get_channel(channel_id) if channel_id else None

    async def handle_call_admin(self, interaction: discord.Interaction):
        settings = await db.get_support_panel_settings(interaction.guild.id)
        channel = await self._notify_channel(interaction.guild, settings)
        mention = _mention_target(settings)
        if not channel or not mention:
            await interaction.response.send_message(
                embed=error_embed("ยังไม่ได้ตั้งค่าปุ่มนี้ กรุณาติดต่อทีมงานให้ตั้งค่าก่อน"), ephemeral=True
            )
            return
        await channel.send(
            embed=styled_embed(
                "🔔 มีการเรียกแอดมิน",
                f"{interaction.user.mention} เรียกแอดมิน {mention} จากห้อง {interaction.channel.mention}",
            )
        )
        await interaction.response.send_message(embed=success_embed("แจ้งแอดมินแล้ว โปรดรอสักครู่"), ephemeral=True)

    async def handle_call_help(self, interaction: discord.Interaction):
        settings = await db.get_support_panel_settings(interaction.guild.id)
        channel = await self._notify_channel(interaction.guild, settings)
        role_id = settings["helper_role_id"]
        if not channel or not role_id:
            await interaction.response.send_message(
                embed=error_embed("ยังไม่ได้ตั้งค่าปุ่มนี้ กรุณาติดต่อทีมงานให้ตั้งค่าก่อน"), ephemeral=True
            )
            return
        await channel.send(
            embed=styled_embed(
                "🙋 มีการขอความช่วยเหลือ",
                f"{interaction.user.mention} ขอความช่วยเหลือจากทีม <@&{role_id}> ที่ห้อง {interaction.channel.mention}",
            )
        )
        await interaction.response.send_message(embed=success_embed("ส่งคำขอความช่วยเหลือแล้ว โปรดรอสักครู่"), ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(SupportPanel(bot))
