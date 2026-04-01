from pyrogram import filters

def register(app):
    @app.on_message(filters.command("force_sub"))
    async def force_sub_cmd(client, message):
        await message.reply_text("Forward a channel message to set force subscribe.")
