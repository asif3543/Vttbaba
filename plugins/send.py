from pyrogram import Client, filters
from pyrogram.types import Message

@Client.on_message(filters.command("send"))
async def send_handler(client, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("Reply to message")

    await message.reply_to_message.copy(message.chat.id)
