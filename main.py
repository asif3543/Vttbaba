from pyrogram import Client, idle
from config import Config
from aiohttp import web
import asyncio

app = Client(
    "bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins={"root": "plugins"}
)

async def web_server():
    """Dummy web server to keep Render Free Tier alive"""
    webapp = web.Application()
    webapp.router.add_get("/", lambda r: web.Response(text="Bot is running smoothly on Render!"))
    runner = web.AppRunner(webapp)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()

async def main():
    print("🚀 Starting Web Server for Render...")
    await web_server()
    print("🚀 Starting Telegram Bot...")
    await app.start()
    await idle()
    await app.stop()

if __name__ == "__main__":
    app.run(main())
