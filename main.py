import asyncio
from pyrogram import Client, idle
from server import web_server
import config

app = Client(
    "anime_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    plugins=dict(root="plugins") # Ye line check karti hai plugins folder
)

async def main():
    # Pehle Render ka port 10000 start karo taaki deploy fail na ho
    await web_server()
    
    # Fir Bot start karo
    print("🤖 Starting Pyrogram Bot...")
    await app.start()
    print("✅ Bot Started Successfully! 🥰🥰.")
    
    # Bot ko zinda rakho
    await idle()
    await app.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
