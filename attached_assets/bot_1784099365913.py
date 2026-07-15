import discord
from discord import app_commands
import os
from dotenv import load_dotenv
import asyncio
from coingecko_sdk import CoinGeckoAPI
import datetime

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True  # ถ้าต้องการอ่านข้อความ

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    print(f'✅ บอท {client.user} ออนไลน์แล้ว!')
    await tree.sync()  # Sync slash commands
    client.loop.create_task(price_alert_task())  # เริ่ม task ตรวจราคา

@tree.command(name="hello", description="ทักทายบอท")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"สวัสดีครับ {interaction.user.mention}! 👋")

# --- Market Alert Feature ---
cg = CoinGeckoAPI()

# เก็บข้อมูลการแจ้งเตือน (สำหรับตัวอย่าง เก็บใน memory)
alerts = {}  # user_id: {"symbol": "bitcoin", "threshold": 60000, "channel": channel_id}

async def price_alert_task():
    while True:
        try:
            for user_id, data in list(alerts.items()):
                try:
                    price_data = cg.get_price(ids=data['symbol'], vs_currencies='usd')
                    current_price = price_data[data['symbol']]['usd']
                    
                    if current_price <= data['threshold']:
                        channel = client.get_channel(data['channel'])
                        if channel:
                            await channel.send(f"⚠️ **แจ้งเตือนตลาด!** {data['symbol'].upper()} ราคาตกเหลือ ${current_price:,} (ต่ำกว่า threshold ${data['threshold']:,})")
                        # ลบ alert หลังแจ้ง (หรือคอมเมนต์ออกถ้าอยากแจ้งซ้ำ)
                        # del alerts[user_id]
                except:
                    pass
        except:
            pass
        await asyncio.sleep(60)  # ตรวจทุก 60 วินาที

@tree.command(name="set_alert", description="ตั้งแจ้งเตือนราคาตก (เช่น bitcoin)")
@app_commands.describe(symbol="ชื่อเหรียญ เช่น bitcoin", threshold="ราคาต่ำสุดที่ต้องการแจ้ง (USD)")
async def set_alert(interaction: discord.Interaction, symbol: str, threshold: float):
    alerts[interaction.user.id] = {
        "symbol": symbol.lower(),
        "threshold": threshold,
        "channel": interaction.channel_id
    }
    await interaction.response.send_message(f"✅ ตั้งแจ้งเตือน {symbol.upper()} แล้ว! จะแจ้งเมื่อราคาตกต่ำกว่า ${threshold:,}")

@tree.command(name="list_alerts", description="ดูรายการแจ้งเตือนของคุณ")
async def list_alerts(interaction: discord.Interaction):
    user_alerts = [f"{data['symbol'].upper()}: ${data['threshold']:,}" for data in alerts.values() if True]  # ง่าย ๆ ก่อน
    if user_alerts:
        await interaction.response.send_message("📋 การแจ้งเตือนของคุณ:\n" + "\n".join(user_alerts))
    else:
        await interaction.response.send_message("ยังไม่มีแจ้งเตือน")

# ใส่คำสั่งอื่น ๆ ที่นี่ (เช่น /style)

client.run(TOKEN)
