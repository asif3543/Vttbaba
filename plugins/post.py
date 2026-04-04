from pyrogram import Client, filters
from pyrogram.types import Message

@Client.on_message(filters.command("link"))
async def link_handler(client, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("Reply to a message")

    msg = message.reply_to_message

    chat_id = str(msg.chat.id)
    if chat_id.startswith("-100"):
        chat_id = chat_id[4:]

    link = f"https://t.me/c/{chat_id}/{msg.id}"

    await message.reply_text(link)
