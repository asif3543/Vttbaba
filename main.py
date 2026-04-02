import logging
from pyrogram import Client
from config import Config
from flask import Flask
import threading
import os

logging.basicConfig(level=logging.INFO)

# 🌐 Flask app setup for Render Keep-Alive
app = Flask(__name__)

@app.route('/')
def hello():
    return "Bot is alive and running successfully! 🚀"

def run_flask():
    app.run(host="0.0.0.0", port=Config.PORT)

# 🤖 Pyrogram Bot Client setup
class AutoPostBot(Client):
    def __init__(self):
        super().__init__(
            "AutoPostBot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            plugins=dict(root="plugins") # Plugins folder ko auto-load karega
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        print(f"✅ Bot Started Successfully as {me.first_name} (@{me.username})")

    async def stop(self, *args):
        await super().stop()
        print("❌ Bot Stopped")

if __name__ == "__main__":
    # Flask server ko background thread me start karna
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Bot ko start karna
    print("Starting Telegram Bot...")
    AutoPostBot().run()
