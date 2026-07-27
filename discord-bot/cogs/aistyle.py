"""AI image-style cog — แต่งภาพด้วย AI (FLUX.1 Kontext via fal.ai)

คำสั่ง slash:
  /style      — เปลี่ยนสไตล์รูปภาพ (เลือกจากเมนู)
  /background — เปลี่ยนพื้นหลังรูปภาพ
  /beauty     — ปรับความสวย / ความคมชัด (1-10)
  /aihelp     — ดูคำสั่ง AI ทั้งหมด
"""

import asyncio
import io
import logging
import os

import aiohttp
import discord
from discord import option
from discord.ext import commands

import db

logger = logging.getLogger("style-bot.aistyle")

FAL_MODEL = "fal-ai/flux-pro/kontext"

# ---------------------------------------------------------------------------
# AI processing helper
# ---------------------------------------------------------------------------

async def _process_image(image_url: str, mode: str, prompt: str = "") -> bytes:
    """Send image_url + prompt to fal.ai and return the resulting PNG bytes."""
    if mode == "style":
        full_prompt = (
            f"Transform this photo into {prompt} style. "
            f"Strictly preserve the exact same face, facial features, identity, expression, pose, "
            f"body proportions, and clothing. "
            f"Only change the artistic style, lighting, and overall aesthetic. "
            f"Highly detailed, sharp focus, professional quality, no face distortion."
        )
    elif mode == "background":
        full_prompt = (
            f"Replace the background with {prompt}. "
            f"Keep the person completely unchanged — same face, hair, body, pose, clothing, and "
            f"lighting on the subject. "
            f"Clean edges, natural blending, realistic lighting and shadows. High quality."
        )
    elif mode == "beauty":
        full_prompt = (
            f"Subtly enhance the beauty and clarity of this portrait at level {prompt}/10. "
            f"Improve skin texture naturally, enhance lighting, increase sharpness and clarity. "
            f"Do not change the face structure, identity, or expression. "
            f"Keep it realistic and natural looking."
        )
    else:
        full_prompt = prompt

    import fal_client  # lazy import — only needed when this cog is active

    fal_key = os.environ.get("FAL_KEY")
    if fal_key:
        fal_client.api_key = fal_key

    result = await asyncio.to_thread(
        fal_client.subscribe,
        FAL_MODEL,
        arguments={
            "prompt": full_prompt,
            "image_url": image_url,
            "num_images": 1,
            "output_format": "png",
        },
        with_logs=False,
    )

    output_url = result["images"][0]["url"]

    async with aiohttp.ClientSession() as session:
        async with session.get(output_url) as resp:
            if resp.status == 200:
                return await resp.read()
            raise RuntimeError(f"Failed to download result image (status {resp.status})")


# ---------------------------------------------------------------------------
# Style-select UI
# ---------------------------------------------------------------------------

_STYLE_OPTIONS = [
    discord.SelectOption(label="Anime",       description="สไตล์อนิเมะญี่ปุ่น",          emoji="🌸"),
    discord.SelectOption(label="Cinematic",   description="ภาพยนตร์โทนภาพสวย",           emoji="🎬"),
    discord.SelectOption(label="Oil Painting",description="ภาพวาดสีน้ำมัน",              emoji="🎨"),
    discord.SelectOption(label="Cyberpunk",   description="นีออน + เมืองอนาคต",           emoji="🌃"),
    discord.SelectOption(label="Realistic",   description="สมจริงสูง",                    emoji="📷"),
    discord.SelectOption(label="Watercolor",  description="สีน้ำ",                        emoji="💧"),
    discord.SelectOption(label="3D Render",   description="เรนเดอร์ 3D",                  emoji="🧊"),
    discord.SelectOption(label="Sketch",      description="ภาพสเก็ตช์ดินสอ",              emoji="✏️"),
]


class StyleSelect(discord.ui.Select):
    def __init__(self, image_url: str, user_id: int):
        self.image_url = image_url
        self.user_id = user_id
        super().__init__(
            placeholder="เลือกสไตล์ที่ต้องการ...",
            min_values=1,
            max_values=1,
            options=_STYLE_OPTIONS,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ คุณไม่ใช่คนที่สั่งคำสั่งนี้", ephemeral=True
            )
            return

        style = self.values[0]
        await interaction.response.defer()

        try:
            result_bytes = await _process_image(self.image_url, mode="style", prompt=style)
            filename = f"styled_{style.lower().replace(' ', '_')}.png"
            file = discord.File(io.BytesIO(result_bytes), filename=filename)
            await interaction.followup.send(
                content=f"✨ เปลี่ยนสไตล์เป็น **{style}** เรียบร้อยแล้ว",
                file=file,
            )
        except Exception as exc:
            logger.exception("style select error")
            await interaction.followup.send(
                f"❌ เกิดข้อผิดพลาด: `{exc}`", ephemeral=True
            )


class StyleView(discord.ui.View):
    def __init__(self, image_url: str, user_id: int):
        super().__init__(timeout=120)
        self.add_item(StyleSelect(image_url, user_id))


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class AIStyle(commands.Cog):
    """AI-powered image editing commands (fal.ai FLUX.1 Kontext)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /style
    @discord.slash_command(name="style", description="เปลี่ยนสไตล์รูปภาพด้วย AI (เลือกจากเมนู)")
    @option("image", discord.Attachment, description="รูปที่ต้องการแก้ไข")
    async def style_command(self, ctx: discord.ApplicationContext, image: discord.Attachment):
        if not image.content_type or not image.content_type.startswith("image/"):
            await ctx.respond("❌ กรุณาแนบไฟล์รูปภาพเท่านั้น", ephemeral=True)
            return

        await ctx.respond(
            content="🎨 **เลือกสไตล์ที่ต้องการ** จากเมนูด้านล่างได้เลย",
            view=StyleView(image.url, ctx.author.id),
        )
        try:
            await db.log_ai_command(ctx.author.id, ctx.guild_id or 0, "style")
        except Exception:
            logger.warning("Failed to log style command", exc_info=True)

    # /background
    @discord.slash_command(name="background", description="เปลี่ยนพื้นหลังรูปภาพ")
    @option("image",      discord.Attachment, description="รูปที่ต้องการแก้ไข")
    @option("background", str,                description="พื้นหลังที่ต้องการ เช่น white studio, beach sunset, cyberpunk city")
    async def background_command(
        self,
        ctx: discord.ApplicationContext,
        image: discord.Attachment,
        background: str,
    ):
        if not image.content_type or not image.content_type.startswith("image/"):
            await ctx.respond("❌ กรุณาแนบไฟล์รูปภาพเท่านั้น", ephemeral=True)
            return

        await ctx.defer()
        try:
            await db.log_ai_command(ctx.author.id, ctx.guild_id or 0, "background")
        except Exception:
            logger.warning("Failed to log background command", exc_info=True)

        try:
            result_bytes = await _process_image(image.url, mode="background", prompt=background)
            file = discord.File(io.BytesIO(result_bytes), filename="background.png")
            await ctx.followup.send(
                content=f"🖼️ เปลี่ยนพื้นหลังเป็น **{background}** เรียบร้อยแล้ว",
                file=file,
            )
        except Exception as exc:
            logger.exception("background command error")
            await ctx.followup.send(f"❌ เกิดข้อผิดพลาด: `{exc}`", ephemeral=True)

    # /beauty
    @discord.slash_command(name="beauty", description="ปรับความสวย / ความคมชัดของรูป")
    @option("image", discord.Attachment, description="รูปที่ต้องการปรับ")
    @option(
        "level",
        int,
        description="ระดับการปรับ (1-10) แนะนำ 5-7",
        min_value=1,
        max_value=10,
        default=6,
    )
    async def beauty_command(
        self,
        ctx: discord.ApplicationContext,
        image: discord.Attachment,
        level: int,
    ):
        if not image.content_type or not image.content_type.startswith("image/"):
            await ctx.respond("❌ กรุณาแนบไฟล์รูปภาพเท่านั้น", ephemeral=True)
            return

        await ctx.defer()
        try:
            await db.log_ai_command(ctx.author.id, ctx.guild_id or 0, "beauty")
        except Exception:
            logger.warning("Failed to log beauty command", exc_info=True)

        try:
            result_bytes = await _process_image(image.url, mode="beauty", prompt=str(level))
            file = discord.File(io.BytesIO(result_bytes), filename="beauty.png")
            await ctx.followup.send(
                content=f"💎 ปรับความสวยระดับ **{level}** เรียบร้อยแล้ว",
                file=file,
            )
        except Exception as exc:
            logger.exception("beauty command error")
            await ctx.followup.send(f"❌ เกิดข้อผิดพลาด: `{exc}`", ephemeral=True)

    # /aihelp
    @discord.slash_command(name="aihelp", description="ดูคำสั่ง AI แต่งภาพทั้งหมด")
    async def aihelp_command(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            title="🤖 AI Image Commands",
            description="แต่งรูปภาพด้วย AI (FLUX.1 Kontext via fal.ai)",
            color=0x5865F2,
        )
        embed.add_field(name="/style",      value="เปลี่ยนสไตล์รูป (เลือกจากเมนู)", inline=False)
        embed.add_field(name="/background", value="เปลี่ยนพื้นหลังรูป",              inline=False)
        embed.add_field(name="/beauty",     value="ปรับความสวย + ความคมชัด (1-10)", inline=False)
        embed.set_footer(text="ส่งรูปมาพร้อมคำสั่งได้เลย")
        await ctx.respond(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(AIStyle(bot))
