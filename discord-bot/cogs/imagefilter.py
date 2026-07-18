"""Image filter cog — แต่งภาพด้วยฟิลเตอร์สไตล์ต่างๆ

คำสั่ง (แนบรูปภาพมาพร้อมคำสั่ง หรือ reply ข้อความที่มีรูป):
  !grayscale  — ขาวดำ
  !sepia      — วินเทจเซเปีย
  !blur       — เบลอ
  !sharpen    — คมชัด
  !cartoon    — การ์ตูน (edge enhance + ลดสี)
  !whitebg    — โทนสว่าง / bright
  !resize W H — ปรับขนาด (default 800×600)
  !animate    — GIF ซูมเข้า 20 เฟรม
  !stylehelp  — แสดงคำสั่งทั้งหมด
"""

import io

import discord
from discord.ext import commands
from PIL import Image, ImageFilter, ImageEnhance, ImageOps

BRAND_COLOR = 0x5865F2
MAX_BYTES = 8 * 1024 * 1024   # 8 MB output limit
THUMBNAIL = (1280, 1280)       # ลดขนาดก่อนประมวลผล เพื่อประหยัด memory


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _get_image(ctx: commands.Context) -> Image.Image | None:
    """ดึง PIL Image จาก attachment ของข้อความปัจจุบัน หรือ referenced message."""
    attachment = None

    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]
    elif ctx.message.reference:
        ref = ctx.message.reference.resolved
        if ref and ref.attachments:
            attachment = ref.attachments[0]

    if attachment is None:
        await ctx.reply(
            "📎 กรุณาแนบรูปภาพมาพร้อมคำสั่ง หรือ reply ข้อความที่มีรูป",
            mention_author=False,
        )
        return None

    if not attachment.content_type or not attachment.content_type.startswith("image/"):
        await ctx.reply("❌ ไฟล์ที่แนบมาไม่ใช่รูปภาพ", mention_author=False)
        return None

    data = await attachment.read()
    img = Image.open(io.BytesIO(data)).convert("RGBA")
    img.thumbnail(THUMBNAIL, Image.LANCZOS)
    return img


def _to_file(img: Image.Image, filename: str = "result.png") -> discord.File:
    buf = io.BytesIO()
    fmt = "GIF" if filename.endswith(".gif") else "PNG"
    if fmt == "PNG":
        img = img.convert("RGBA")
    img.save(buf, format=fmt)
    buf.seek(0)
    return discord.File(buf, filename=filename)


def _to_gif_file(frames: list[Image.Image], duration: int = 60) -> discord.File:
    buf = io.BytesIO()
    frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=duration,
        optimize=True,
    )
    buf.seek(0)
    return discord.File(buf, filename="animated.gif")


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

def apply_grayscale(img: Image.Image) -> Image.Image:
    return ImageOps.grayscale(img).convert("RGBA")


def apply_sepia(img: Image.Image) -> Image.Image:
    gray = ImageOps.grayscale(img)
    sepia = Image.new("RGB", gray.size)
    pixels = list(gray.getdata())
    sepia_pixels = [
        (
            min(int(p * 1.08), 255),
            min(int(p * 0.85), 255),
            min(int(p * 0.66), 255),
        )
        for p in pixels
    ]
    sepia.putdata(sepia_pixels)
    return sepia.convert("RGBA")


def apply_blur(img: Image.Image) -> Image.Image:
    return img.filter(ImageFilter.GaussianBlur(radius=3))


def apply_sharpen(img: Image.Image) -> Image.Image:
    return img.filter(ImageFilter.SHARPEN).filter(ImageFilter.SHARPEN)


def apply_cartoon(img: Image.Image) -> Image.Image:
    rgb = img.convert("RGB")
    edges = rgb.filter(ImageFilter.FIND_EDGES).convert("L")
    # ลดจำนวนสีให้ดูเหมือนการ์ตูน
    quantized = rgb.quantize(colors=16).convert("RGB")
    # overlay edges เป็นสีดำ
    edge_rgba = edges.point(lambda x: 0 if x > 30 else 255)
    mask = edge_rgba.convert("L")
    result = quantized.copy()
    result.paste((0, 0, 0), mask=ImageOps.invert(mask))
    return result.convert("RGBA")


def apply_whitebg(img: Image.Image) -> Image.Image:
    rgb = img.convert("RGB")
    bright = ImageEnhance.Brightness(rgb).enhance(1.3)
    contrast = ImageEnhance.Contrast(bright).enhance(0.9)
    return contrast.convert("RGBA")


def apply_resize(img: Image.Image, w: int, h: int) -> Image.Image:
    return img.resize((w, h), Image.LANCZOS)


def apply_animate(img: Image.Image, steps: int = 20) -> list[Image.Image]:
    """สร้าง GIF ซูมเข้า 20 เฟรม"""
    rgb = img.convert("RGB")
    w, h = rgb.size
    frames: list[Image.Image] = []
    for i in range(steps):
        scale = 1.0 + (i / steps) * 0.5   # ซูม 100% → 150%
        nw, nh = int(w * scale), int(h * scale)
        zoomed = rgb.resize((nw, nh), Image.LANCZOS)
        # crop กลาง
        left = (nw - w) // 2
        top = (nh - h) // 2
        cropped = zoomed.crop((left, top, left + w, top + h))
        frames.append(cropped)
    return frames


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class ImageFilter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _process(self, ctx: commands.Context, label: str, result: Image.Image) -> None:
        file = _to_file(result)
        embed = discord.Embed(
            description=f"✅ ใช้ฟิลเตอร์ **{label}** เรียบร้อยแล้ว",
            color=BRAND_COLOR,
        )
        embed.set_image(url="attachment://result.png")
        await ctx.reply(embed=embed, file=file, mention_author=False)

    @commands.command(name="grayscale", aliases=["bw", "ขาวดำ"])
    async def grayscale(self, ctx: commands.Context):
        """แปลงภาพเป็นขาวดำ"""
        img = await _get_image(ctx)
        if img:
            async with ctx.typing():
                await self._process(ctx, "Grayscale", apply_grayscale(img))

    @commands.command(name="sepia", aliases=["วินเทจ"])
    async def sepia(self, ctx: commands.Context):
        """ฟิลเตอร์เซเปีย วินเทจ"""
        img = await _get_image(ctx)
        if img:
            async with ctx.typing():
                await self._process(ctx, "Sepia", apply_sepia(img))

    @commands.command(name="blur", aliases=["เบลอ"])
    async def blur(self, ctx: commands.Context):
        """เบลอภาพ"""
        img = await _get_image(ctx)
        if img:
            async with ctx.typing():
                await self._process(ctx, "Blur", apply_blur(img))

    @commands.command(name="sharpen", aliases=["คม"])
    async def sharpen(self, ctx: commands.Context):
        """เพิ่มความคมชัด"""
        img = await _get_image(ctx)
        if img:
            async with ctx.typing():
                await self._process(ctx, "Sharpen", apply_sharpen(img))

    @commands.command(name="cartoon", aliases=["การ์ตูน"])
    async def cartoon(self, ctx: commands.Context):
        """ฟิลเตอร์สไตล์การ์ตูน"""
        img = await _get_image(ctx)
        if img:
            async with ctx.typing():
                await self._process(ctx, "Cartoon", apply_cartoon(img))

    @commands.command(name="whitebg", aliases=["สว่าง"])
    async def whitebg(self, ctx: commands.Context):
        """ปรับโทนสว่าง"""
        img = await _get_image(ctx)
        if img:
            async with ctx.typing():
                await self._process(ctx, "White Bright", apply_whitebg(img))

    @commands.command(name="resize", aliases=["ปรับขนาด"])
    async def resize(self, ctx: commands.Context, width: int = 800, height: int = 600):
        """ปรับขนาดภาพ — ใช้: !resize 800 600"""
        if not (32 <= width <= 3000 and 32 <= height <= 3000):
            await ctx.reply("❌ ขนาดต้องอยู่ระหว่าง 32–3000 px", mention_author=False)
            return
        img = await _get_image(ctx)
        if img:
            async with ctx.typing():
                await self._process(ctx, f"Resize {width}×{height}", apply_resize(img, width, height))

    @commands.command(name="animate", aliases=["gif", "แอนิเมต"])
    async def animate(self, ctx: commands.Context):
        """สร้าง GIF ซูมเข้า"""
        img = await _get_image(ctx)
        if img:
            async with ctx.typing():
                frames = apply_animate(img)
                file = _to_gif_file(frames)
                embed = discord.Embed(
                    description="✅ สร้าง **GIF ซูมเข้า** เรียบร้อยแล้ว",
                    color=BRAND_COLOR,
                )
                embed.set_image(url="attachment://animated.gif")
                await ctx.reply(embed=embed, file=file, mention_author=False)

    @commands.command(name="stylehelp")
    async def stylehelp(self, ctx: commands.Context):
        """แสดงคำสั่งแต่งภาพทั้งหมด"""
        embed = discord.Embed(
            title="🎨 คำสั่งแต่งภาพ Style-Bot",
            description="แนบรูปภาพมาพร้อมคำสั่ง หรือ reply ข้อความที่มีรูป",
            color=BRAND_COLOR,
        )
        embed.add_field(
            name="ฟิลเตอร์พื้นฐาน",
            value=(
                "`!grayscale` — ขาวดำ\n"
                "`!sepia` — วินเทจเซเปีย\n"
                "`!blur` — เบลอ\n"
                "`!sharpen` — คมชัด\n"
                "`!cartoon` — สไตล์การ์ตูน\n"
                "`!whitebg` — โทนสว่าง"
            ),
            inline=False,
        )
        embed.add_field(
            name="เครื่องมืออื่น",
            value=(
                "`!resize W H` — ปรับขนาด (เช่น `!resize 800 600`)\n"
                "`!animate` — สร้าง GIF ซูมเข้า"
            ),
            inline=False,
        )
        embed.set_footer(text="รองรับ .png .jpg .jpeg .webp .gif")
        await ctx.reply(embed=embed, mention_author=False)


def setup(bot: commands.Bot):
    bot.add_cog(ImageFilter(bot))
