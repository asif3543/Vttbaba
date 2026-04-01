import asyncio
import logging
from pyrogram import Client, idle
from server import web_server
import config

# Ye terminal me error aur files ka status dikhayega
logging.basicConfig(level=logging.INFO)

print("🔍 Loading files from 'plugins' directory...")

# Pyrogram ka auto-plugin system (Ye saari files ko khud access dega)
app = Client(
    "anime_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    plugins=dict(root="plugins") # ⚠️ DHYAN RAHE: Saari files 'plugins' folder me honi chahiye!
)

async def main():
    # 1. Render ko sone se bachane ke liye server start
    print("🌐 Starting Web Server for Render on port 10000...")
    await web_server()
    
    # 2. Bot start karna aur saari files ko zinda karna
    print("🤖 Starting Pyrogram Bot & Connecting Files...")
    await app.start()
    
    # Bot ka username print karega agar access mil gaya toh
    me = await app.get_me()
    print(f"✅ Bot Started Successfully as @{me.username}")
    print("📁 Saari commands aur files successfully connect ho gayi hain!")
    
    # 3. Bot ko 24/7 online rakhne ke liye idle()
    await idle()
    await app.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
