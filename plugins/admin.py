from pyrogram import Client, filters
from pyrogram.types import Message
from config import ADMINS

@Client.on_message(filters.command("delete") & filters.user(ADMINS))
async def delete_handler(client, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("Reply to message")

    await message.reply_to_message.delete()
    await message.reply_text("Deleted ✅")
