from pyrogram import filters

def register(app):
    @app.on_message(filters.command("post"))
    async def post_cmd(client, message):
        await message.reply_text("Please forward the post to publish.")
