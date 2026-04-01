from pyrogram import filters

def register(app):
    @app.on_message(filters.command("add_premium"))
    async def add_premium_cmd(client, message):
        await message.reply_text("Send user ID to grant premium access.")
