import os
from pyrogram import Client
from server import keep_alive
import config

app = Client(
    "anime_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    plugins=dict(root="plugins") # Ye line automatically plugins folder ko load karegi
)

if __name__ == "__main__":
    print("🌐 Starting Web Server for Render on Port 10000...")
    keep_alive()
    print("🤖 Starting Pyrogram Anime Bot...")
    app.run()
