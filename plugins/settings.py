from pyrogram import Client, filters
from pyrogram.types import Message
import config

@Client.on_message(~filters.command("start") & filters.private & ~filters.user(config.ADMINS))
async def any_text_user(client: Client, message: Message):
    await message.reply("I am an anime post bot. Only admins can use commands.")

@Client.on_message(filters.command("Setting") & filters.user(config.ADMINS))
async def cmd_settings(client: Client, message: Message):
    text = """
⚙️ **All Commands List**
/post - Create new post
/add shortner account - Connect GP Link etc.
/remove shortner account - Remove Shortener
/add premium - Add premium member (28 Days)
/remove premium - Ban premium member
/show premium list - View all premium users
/Force sub - Set Force Join Channel
/send | /send more channel - Send to channels

*Everything configured perfectly for Render!*
    """
    await message.reply(text)
