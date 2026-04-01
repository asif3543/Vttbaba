import asyncio
from aiohttp import web
from pyrogram import Client
import config

app = Client(
    "anime_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    plugins=dict(root="plugins")
)

async def health_check(request):
    return web.Response(text="🚀 Bot is Alive and Running on Render!")

async def start_web_server():
    server = web.Application()
    server.router.add_get('/', health_check)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', config.PORT)
    await site.start()
    print(f"🌐 Web Server Started on Port {config.PORT}")

async def main():
    await start_web_server()
    print("🤖 Starting Pyrogram Bot...")
    await app.start()
    print("✅ Bot is Online!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
