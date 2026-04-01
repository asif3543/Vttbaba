from pyrogram import filters

def register(app):
    @app.on_message(filters.command("batchlink"))
    async def batchlink_cmd(client, message):
        await message.reply_text("Send the episode range for batch posting.")
