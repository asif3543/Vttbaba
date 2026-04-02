import logging
import threading
from pyrogram import Client
from flask import Flask
from config import Config

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is 100% Working and Online!"

def run_flask():
    app.run(host="0.0.0.0", port=Config.PORT)

class AutoPostBot(Client):
    def __init__(self):
        super().__init__(
            "AutoPostBot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            plugins=dict(root="plugins")
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        print(f"✅ Bot Online: @{me.username}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    AutoPostBot().run()
