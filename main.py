from pyrogram import Client
from keep_alive import keep_alive
from config import API_ID, API_HASH, BOT_TOKEN

bot = Client(
    "AdvancedAutoBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins")
)

if __name__ == "__main__":
    print("Starting Keep-Alive Server...")
    keep_alive()
    print("Starting Telegram Bot...")
    bot.run()
