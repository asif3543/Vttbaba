from pyrogram import Client, idle
from pyrogram.errors import FloodWait
from config import API_ID, API_HASH, BOT_TOKEN
from aiohttp import web
import asyncio, os, sys

# 🚨 Security Check: अगर Token नहीं है तो Render को बता दो
if not BOT_TOKEN or API_ID == 0:
    print("❌ ERROR: BOT_TOKEN or API_ID is missing in Environment Variables!")
    sys.exit(1)

# 🔥 in_memory=True डाला है ताकि Render पर Session File Lock न हो
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
    webapp.router.add_get("/", lambda r: web.Response(text="Bot is Running Successfully!"))
    runner = web.AppRunner(webapp)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000))).start()

async def main():
    await web_server()
    while True:
        try:
            await app.start()
            bot_info = await app.get_me()
            print(f"✅ Bot Started Successfully: @{bot_info.username}")
            break
        except FloodWait as e:
            print(f"⚠️ FloodWait! Sleeping for {e.value + 5} sec...")
            await asyncio.sleep(e.value + 5)
        except Exception as e:
            print(f"❌ Critical Error in Bot Start: {e}")
            sys.exit(1)
            
    await idle()
    await app.stop()

if __name__ == "__main__":
    app.run(main())
