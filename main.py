from pyrogram import Client, idle
from pyrogram.errors import FloodWait
from config import Config
from aiohttp import web
import asyncio
import os

app = Client(
    "bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins={"root": "plugins"}
)

async def web_server():
    webapp = web.Application()
    webapp.router.add_get("/", lambda r: web.Response(text="Bot is ALIVE on Render!"))
    runner = web.AppRunner(webapp)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    print("🚀 Starting Web Server...")
    await web_server()
    
    print("🚀 Starting Telegram Bot...")
    while True:
        try:
            await app.start()
            print("✅ Bot Started 🥰 Successfully!")
            break
        except FloodWait as e:
            wait_time = e.value + 5
            print(f"⚠️ FloodWait Detected! Sleeping for {wait_time}s to prevent ban...")
            await asyncio.sleep(wait_time)
        except Exception as e:
            print(f"❌ Critical Error: {e}")
            break

    await idle()
    await app.stop()

if __name__ == "__main__":
    app.run(main())
