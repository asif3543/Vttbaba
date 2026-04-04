import asyncio
import uvloop
from pyrogram import Client, idle
from config import API_ID, API_HASH, BOT_TOKEN

uvloop.install()

app = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root=".")
)

async def main():
    await app.start()
    print("✅ Bot Started")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
