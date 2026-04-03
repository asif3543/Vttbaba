from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait
from config import API_ID, API_HASH, BOT_TOKEN
from aiohttp import web
import asyncio, os, sys
import uvloop

uvloop.install()
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True, plugins={"root": "plugins"})

# 🔴 यह डायरेक्ट कमांड है, यह बताएगी कि बॉट मैसेज पढ़ रहा है या नहीं
@app.on_message(filters.command("ping"))
async def ping_test(client, message):
    await message.reply_text("✅ Pong! Bot is 100% Alive and reading messages!")

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
            await asyncio.sleep(e.value + 5)
        except Exception as e:
            sys.exit(1)
            
    await idle()
    await app.stop()

if __name__ == "__main__":
    loop.run_until_complete(main())
