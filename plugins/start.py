from pyrogram import Client, filters
from pyrogram.types import Message
from database import db
from plugins.premium import is_premium
from plugins.force_sub import check_force_sub, force_sub_buttons

# ==============================
# 🔰 START + DEEP LINK
# ==============================
@Client.on_message(filters.command("start") & filters.private)
async def start(client: Client, message: Message):

    user_id = message.from_user.id

    # 🔹 Deep link
    if len(message.command) > 1:

        data = message.command[1]

        if data.startswith("post_"):
            post_id = data.split("_")[1]

            post = await db.get_post(post_id)

            if not post:
                return await message.reply("❌ Post not found")

            # 🔹 Premium
            if await is_premium(user_id):
                return await send_episode(client, message, post)

            # 🔹 Force sub check
            not_joined = await check_force_sub(client, user_id)

            if not_joined:
                buttons = await force_sub_buttons(client, user_id)
                return await message.reply(
                    "🚫 Join all channels first",
                    reply_markup=buttons
                )

            # 🔹 Shortner
            short = await db.generate_short_link(user_id, post_id)

            return await message.reply(f"🔗 Link:\n{short}")

    await message.reply("👋 Welcome to Anime Bot")
