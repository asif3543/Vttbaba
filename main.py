from pyrogram import Client, idle
from pyrogram.errors import FloodWait
from config import API_ID, API_HASH, BOT_TOKEN
from aiohttp import web
import asyncio, os

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, plugins={"root": "plugins"})

async def web_server():
    webapp = web.Application()
    webapp.router.add_get("/", lambda r: web.Response(text="Clone Manager & File Store Running!"))
    runner = web.AppRunner(webapp)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000))).start()

async def main():
    await web_server()
    while True:
        try:
            await app.start()
            print("✅ Bot Started")
            break
        except FloodWait as e:
            await asyncio.sleep(e.value + 5)
        except Exception as e:
            break
    await idle()
    await app.stop()

if __name__ == "__main__":
    app.run(main())
