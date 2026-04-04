from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait
from config import API_ID, API_HASH, BOT_TOKEN
from aiohttp import web
import asyncio, os, sys
import uvloop

# ⚡ Performance boost
uvloop.install()

# ✅ Proper event loop
loop = asyncio.get_event_loop()

# ✅ Correct Client (plugins properly load honge)
app = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins")  # 🔥 FIX
)

# ❌ REMOVE THIS LINE (ERROR)

# ✅ Test command (bot alive check)
@app.on_message(filters.command("ping"))
async def ping_test(client, message):
    await message.reply_text("✅ Pong! Bot is Alive!")

# 🌐 Web server (Render keep-alive)
async def web_server():
    webapp = web.Application()
    webapp.router.add_get("/", lambda r: web.Response(text="Bot Running ✅"))
    
    runner = web.AppRunner(webapp)
    await runner.setup()
    
    await web.TCPSite(
        runner,
        "0.0.0.0",
        int(os.environ.get("PORT", 10000))
    ).start()

# 🚀 Main function
async def main():
    await web_server()

    while True:
        try:
            await app.start()
            bot_info = await app.get_me()
            print(f"✅ Bot Started Successfully: @{bot_info.username}")
            break

        except FloodWait as e:
            print(f"FloodWait: Sleeping {e.value}s")
            await asyncio.sleep(e.value + 5)

        except Exception as e:
            print(f"Startup Error: {e}")
            sys.exit(1)

    await idle()
    await app.stop()

# ▶️ Run
if __name__ == "__main__":
    asyncio.run(main())
