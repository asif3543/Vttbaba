from pyrogram import Client, filters

@Client.on_message(filters.command("help"))
async def help_handler(client, message):
    await message.reply_text(
        "/start\n/link\n/send\n/delete"
    )
