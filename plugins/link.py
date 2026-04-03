from pyrogram import Client, filters
from pyrogram.types import Message
from plugins.post import user_states

# ==============================
# 🔰 SINGLE LINK MODE
# ==============================
@Client.on_message(filters.command("link") & filters.private)
async def single_link(client: Client, message: Message):

    user_id = message.from_user.id

    if user_id not in user_states:
        return await message.reply("❌ Use /post first")

    user_states[user_id]["step"] = "waiting_episode"

    await message.reply("📥 Send episode (forward from storage channel)")
