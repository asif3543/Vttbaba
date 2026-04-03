from pyrogram import Client, idle
from pyrogram.errors import FloodWait
from config import API_ID, API_HASH, BOT_TOKEN
from aiohttp import web
import asyncio, os, sys
import uvloop

# Install Superfast uvloop implementation
uvloop.install()

if not BOT_TOKEN or API_ID == 0:
    print("❌ ERROR: Missing Environment Variables!")
    sys.exit(1)

# in_memory=True prevents SQLite lock issues on Render
app = Client(
    "bot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN, 
    in_memory=True,  
    plugins={"root": "plugins"}
)

async def web_server():
    webapp = web.Application()
    webapp.router.add_get("/", lambda r: web.Response(text="Advanced Production Bot is Running!"))
    runner = web.AppRunner(webapp)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000))).start()

async def main():
    await web_server()
    while True:
        try:
            await app.start()
            bot_info = await app.get_me()
            print(f"✅ Stable Production Bot Started: @{bot_info.username}")
            break
        except FloodWait as e:
            print(f"⚠️ FloodWait Detected! Sleeping for {e.value + 5}s...")
            await asyncio.sleep(e.value + 5)
        except Exception as e:
            print(f"❌ Core Crash: {e}")
            sys.exit(1)
            
    await idle()
    await app.stop()

if __name__ == "__main__":
    app.run(main())
