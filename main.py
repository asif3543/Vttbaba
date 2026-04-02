import logging
import threading
from pyrogram import Client
from flask import Flask
from config import Config

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.route('/')
def home():
    return "File Store Bot is Live and Running!"

def run_flask():
    app.run(host="0.0.0.0", port=Config.PORT)

class FileStoreBot(Client):
    def __init__(self):
        super().__init__(
            "FileStoreBot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            plugins=dict(root="plugins")
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        print(f"✅ Bot Started Successfully: @{me.username}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    FileStoreBot().run()
