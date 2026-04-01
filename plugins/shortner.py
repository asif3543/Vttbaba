from pyrogram import filters

def register(app):
    @app.on_message(filters.command("add_shortner"))
    async def add_shortner_cmd(client, message):
        await message.reply_text("Send your shortner dashboard link and API key.")
