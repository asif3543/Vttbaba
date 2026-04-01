from pyrogram import filters

def register(app):
    @app.on_message(filters.command("start"))
    async def start_cmd(client, message):
        await message.reply_text("Hello 🤗 Welcome to Anime Auto Post Bot!")
