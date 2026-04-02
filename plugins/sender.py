from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from plugins.helpers import USER_STATE, get_saved_channels, is_admin

@Client.on_message(filters.command(["send", "send_more_channel", "send more channel"]) & filters.private)
async def send_cmd(client, message: Message):
    if not is_admin(message.from_user.id): return
    channels = get_saved_channels()
    if not channels: return await message.reply_text("No channels saved!")
    
    buttons = [[InlineKeyboardButton(ch['channel_name'], callback_data=f"send_{ch['channel_id']}")] for ch in channels]
    await message.reply_text("Select channel:\n(Use /confirm after multi-select)", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r"^send_"))
async def handle_send(client, query: CallbackQuery):
    ch_id = query.data.split("_")[1]
    user_id = query.from_user.id
    if "send_channels" not in USER_STATE.get(user_id, {}):
        USER_STATE[user_id] = {"send_channels": []}
    USER_STATE[user_id]["send_channels"].append(ch_id)
    await query.answer("Channel selected! Type /confirm", show_alert=True)

@Client.on_message(filters.command("confirm") & filters.private)
async def confirm_send_action(client, message: Message):
    user_id = message.from_user.id
    if "send_channels" in USER_STATE.get(user_id, {}):
        post_data = USER_STATE[user_id].get("last_post_id")
        for ch_id in USER_STATE[user_id]["send_channels"]:
            await client.send_message(int(ch_id), f"🎥 New Episode Uploaded!\n\n👉 https://t.me/{client.me.username}?start={post_data}")
        await message.reply_text("Post sent to selected channels ✅")
        del USER_STATE[user_id]["send_channels"]
