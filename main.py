from pyrogram import Client
from config import Config

app = Client(
    "bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins={"root": "plugins"} #yaha se files lega 
)

print("🚀 Bot Started on PORT 10000")

app.run()
