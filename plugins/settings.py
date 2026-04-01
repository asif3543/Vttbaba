from pyrogram import Client, filters
from pyrogram.types import Message
import config

@app.on_message(filters.command("Setting") & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def settings_cmd(client: Client, message: Message):
    text = """
⚙️ **Bot Commands & Settings** ⚙️

/post - Naya episode/batch post karne ke liye
/add shortner account - Naya shortner add karne ke liye
/remove shortner account - Shortner hatane ke liye
/add premium - Bina shortner direct link dene ke liye (28 days)
/remove premium - Premium hatane ke liye
/show premium list - Premium users dekhne ke liye
/Force sub - Force sub channel add karne ke liye
/send & /send more channel - Posts ko target channels me bhejne ke liye

*Bot is securely running on Render with Supabase DB!*
    """
    await message.reply(text)
