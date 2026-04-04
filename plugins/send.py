from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import ADMINS, USER_STATE
from database import get_channels

@Client.on_message(filters.command("send") & filters.user(ADMINS) & filters.private)
async def send_cmd(client, message):
    user_id = message.from_user.id
    state = USER_STATE.get(user_id)

    if not state or state.get("step") != "ready_to_send":
        return await message.reply_text("Create post first")

    channels = await get_channels()
    if not channels:
        return await message.reply_text("No channels")

    for ch in channels:
        await client.copy_message(
            chat_id=ch["channel_id"],
            from_chat_id=user_id,
            message_id=state["post_msg_id"],
            reply_markup=state["ready_btn"]
        )

    await message.reply_text("Sent ✅")
    del USER_STATE[user_id]
