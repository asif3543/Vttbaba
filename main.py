from pyrogram import Client, filters
from config import API_ID, API_HASH, BOT_TOKEN
from plugins import start, post_system, batchlink, shortner, premium, force_sub, utils

app = Client("anime-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Load plugins
start.register(app)
post_system.register(app)
batchlink.register(app)
shortner.register(app)
premium.register(app)
force_sub.register(app)
utils.register(app)

print("Bot is starting...")
app.run()
