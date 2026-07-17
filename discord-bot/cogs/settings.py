"""Miscellaneous config commands: log channel + a paginated help command."""

import discord
from discord.ext import commands

from utils import is_staff, styled_embed, success_embed
import db

BRAND_COLOR = 0x5865F2

# ---------------------------------------------------------------------------
# Help data — category name, emoji, list of (command, description, usage)
# ---------------------------------------------------------------------------

HELP_CATEGORIES = {
    "moderation": {
        "label": "การจัดการเซิร์ฟเวอร์",
        "emoji": "🛡️",
        "description": "คำสั่งสำหรับดูแลและจัดการสมาชิก (ต้องมีสิทธิ์ที่เกี่ยวข้อง)",
        "commands": [
            ("/mod kick @สมาชิก [เหตุผล]",       "เตะสมาชิกออกจากเซิร์ฟเวอร์"),
            ("/mod ban @สมาชิก [เหตุผล]",        "แบนสมาชิกออกจากเซิร์ฟเวอร์"),
            ("/mod unban user_id:123...",         "ปลดแบนผู้ใช้ด้วย ID"),
            ("/mod timeout @สมาชิก นาที [เหตุผล]","ปิดปากสมาชิกชั่วคราว"),
            ("/mod untimeout @สมาชิก",            "ยกเลิกการปิดปากสมาชิก"),
            ("/mod warn @สมาชิก [เหตุผล]",       "ออกใบเตือนให้สมาชิก"),
            ("/mod warnings @สมาชิก",             "ดูประวัติใบเตือนของสมาชิก"),
            ("/mod clearwarnings @สมาชิก",        "ล้างใบเตือนทั้งหมดของสมาชิก"),
            ("/mod clear จำนวน",                  "ลบข้อความล่าสุด (สูงสุด 100 ข้อความ)"),
        ],
    },
    "welcome": {
        "label": "ข้อความต้อนรับ / อำลา",
        "emoji": "👋",
        "description": "ตั้งค่าข้อความต้อนรับสมาชิกใหม่และข้อความอำลา\n"
                       "**ตัวแปรที่ใช้ได้:** `{mention}` `{user}` `{name}` `{server}` `{count}`",
        "commands": [
            ("/welcome channel #ห้อง",            "กำหนดห้องสำหรับส่งข้อความต้อนรับ"),
            ("/welcome message ข้อความ",          "ตั้งข้อความต้อนรับ (ใช้ตัวแปรได้)"),
            ("/welcome leave_channel #ห้อง",      "กำหนดห้องสำหรับส่งข้อความอำลา"),
            ("/welcome leave_message ข้อความ",    "ตั้งข้อความอำลา (ใช้ตัวแปรได้)"),
            ("/welcome test",                     "ทดสอบข้อความต้อนรับกับบัญชีตัวเอง"),
        ],
    },
    "automod": {
        "label": "Automod",
        "emoji": "🤖",
        "description": "ระบบกรองอัตโนมัติ — บล็อกคำต้องห้าม ลิงก์เชิญ และ mention สแปม",
        "commands": [
            ("/automod toggle",                   "เปิด/ปิดตัวกรองคำต้องห้าม"),
            ("/automod anti_invite",              "เปิด/ปิดบล็อกลิงก์เชิญ Discord"),
            ("/automod anti_mention_spam",        "เปิด/ปิดบล็อกข้อความที่ mention สแปมจำนวนมาก"),
            ("/automod addword คำ",               "เพิ่มคำลงในรายการต้องห้าม"),
            ("/automod removeword คำ",            "ลบคำออกจากรายการต้องห้าม"),
            ("/automod listwords",                "ดูรายการคำต้องห้ามทั้งหมด"),
        ],
    },
    "customcommands": {
        "label": "คำสั่งกำหนดเอง",
        "emoji": "💬",
        "description": "สร้างคำสั่งข้อความสั้น ๆ ที่กำหนดเองสำหรับเซิร์ฟเวอร์",
        "commands": [
            ("/customcommand add ชื่อคำสั่ง ข้อความตอบกลับ", "เพิ่ม (หรืออัปเดต) คำสั่งกำหนดเอง"),
            ("/customcommand remove ชื่อคำสั่ง",              "ลบคำสั่งกำหนดเอง"),
            ("/customcommand list",                           "ดูคำสั่งกำหนดเองทั้งหมดของเซิร์ฟเวอร์"),
            ("/customcommand prefix ตัวอักษร",               "เปลี่ยน prefix สำหรับเรียกใช้คำสั่งกำหนดเอง"),
        ],
    },
    "reactionroles": {
        "label": "Reaction Roles",
        "emoji": "🎭",
        "description": "ผูก emoji บนข้อความ — กด emoji เพื่อรับ/ถอดบทบาทอัตโนมัติ",
        "commands": [
            ("/reactionrole add message_id:123 emoji:🎮 role:@บทบาท",
             "ผูก emoji บนข้อความนั้นให้กดรับ/ถอดบทบาทที่กำหนด\n"
             "*(ต้องรันคำสั่งในห้องเดียวกับข้อความนั้น)*"),
        ],
    },
    "queue": {
        "label": "ระบบคิว",
        "emoji": "🎫",
        "description": "ระบบคิวหมายเลข 1–100 สำหรับรับคิวและติดตามสถานะแบบเรียลไทม์",
        "commands": [
            ("/queue panel",             "โพสต์แผงปุ่ม **รับคิว** / **เสร็จสิ้น** ในช่องนี้"),
            ("/queue setdisplay #ห้อง", "กำหนดห้องแสดงรายชื่อคิวแบบเรียงลำดับ (อัปเดตอัตโนมัติ)"),
            ("/queue reset",             "ล้างคิวทั้งหมด — ใช้เมื่อต้องการเริ่มรอบใหม่"),
        ],
    },
    "supportpanel": {
        "label": "ศูนย์ช่วยเหลือ (ปุ่มซัพพอร์ต)",
        "emoji": "🛎️",
        "description": "แผงปุ่ม 3 ปุ่ม — เรียกแอดมิน / ขอความช่วยเหลือ / หาปาตี้ลงดัน\n"
                       "**ต้องตั้งค่าครบก่อนใช้ `/supportpanel panel`**",
        "commands": [
            ("/supportpanel setadmin user:@ผู้ใช้\nหรือ /supportpanel setadmin role:@บทบาท",
             "กำหนดว่าปุ่ม 🔔 **เรียกแอดมิน** จะแท็กใคร (เลือกได้ทั้ง user หรือ role)"),
            ("/supportpanel sethelper role:@บทบาท",
             "กำหนดบทบาทที่จะถูกแท็กเมื่อกดปุ่ม 🙋 **ขอความช่วยเหลือ**"),
            ("/supportpanel setrole role:@บทบาท",
             "กำหนดบทบาทที่จะได้รับ/ถูกถอดเมื่อกดปุ่ม ⚔️ **หาปาตี้ลงดัน**"),
            ("/supportpanel setchannel channel:#ห้อง",
             "กำหนดห้องที่รับการแจ้งเตือนจากปุ่มเรียกแอดมิน / ขอความช่วยเหลือ / หาปาตี้"),
            ("/supportpanel panel",
             "โพสต์แผงปุ่มทั้ง 3 ในห้องที่รันคำสั่ง (ต้องตั้งค่า 4 ขั้นตอนด้านบนให้ครบก่อน)"),
        ],
    },
    "settings": {
        "label": "ตั้งค่าทั่วไป",
        "emoji": "⚙️",
        "description": "การตั้งค่าระบบทั่วไปของบอทในเซิร์ฟเวอร์",
        "commands": [
            ("/settings logchannel #ห้อง", "กำหนดห้อง log สำหรับบันทึกการใช้คำสั่ง moderation และ automod"),
        ],
    },
}


def _overview_embed() -> discord.Embed:
    lines = []
    for key, cat in HELP_CATEGORIES.items():
        lines.append(f"{cat['emoji']} **{cat['label']}** — {len(cat['commands'])} คำสั่ง")
    embed = discord.Embed(
        title="📖 รายการคำสั่งทั้งหมด",
        description=(
            "เลือกหมวดจาก dropdown ด้านล่างเพื่อดูรายละเอียดและวิธีใช้งาน\n\n"
            + "\n".join(lines)
        ),
        color=BRAND_COLOR,
    )
    embed.set_footer(text="เฉพาะคำสั่งที่มีหัวข้อ [แอดมิน] ต้องใช้สิทธิ์ Manage Server หรือสูงกว่า")
    return embed


def _category_embed(key: str) -> discord.Embed:
    cat = HELP_CATEGORIES[key]
    lines = []
    for cmd, desc in cat["commands"]:
        lines.append(f"**`{cmd}`**\n{desc}\n")
    embed = discord.Embed(
        title=f"{cat['emoji']} {cat['label']}",
        description=cat["description"] + "\n\n" + "\n".join(lines),
        color=BRAND_COLOR,
    )
    embed.set_footer(text="พิมพ์ /help อีกครั้งเพื่อดูภาพรวมทั้งหมด")
    return embed


class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=cat["label"],
                value=key,
                emoji=cat["emoji"],
            )
            for key, cat in HELP_CATEGORIES.items()
        ]
        super().__init__(
            placeholder="เลือกหมวดคำสั่ง...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        embed = _category_embed(selected)
        await interaction.response.edit_message(embed=embed)


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(HelpSelect())

    @discord.ui.button(label="ภาพรวมทั้งหมด", style=discord.ButtonStyle.secondary, emoji="📖", row=1)
    async def overview(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=_overview_embed())


class Settings(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    settings_group = discord.SlashCommandGroup("settings", "การตั้งค่าเซิร์ฟเวอร์")

    @settings_group.command(name="logchannel", description="กำหนดห้อง log สำหรับ moderation และ automod")
    @is_staff()
    async def logchannel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        await db.update_guild_settings(ctx.guild.id, log_channel_id=channel.id)
        await ctx.respond(embed=success_embed(f"บันทึก log จะถูกส่งไปที่ {channel.mention} แล้ว"), ephemeral=True)

    @discord.slash_command(name="ping", description="ตรวจสอบว่าบอทออนไลน์และดู latency")
    async def ping_cmd(self, ctx: discord.ApplicationContext):
        latency = round(ctx.bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latency: **{latency} ms**",
            color=0x2ECC71 if latency < 200 else 0xE74C3C,
        )
        await ctx.respond(embed=embed)

    @discord.slash_command(name="help", description="ดูคำสั่งและวิธีการใช้งานทั้งหมดของบอท")
    async def help_cmd(self, ctx: discord.ApplicationContext):
        await ctx.respond(embed=_overview_embed(), view=HelpView(), ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(Settings(bot))
