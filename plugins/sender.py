from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from plugins.helpers import USER_STATE, db, get_saved_channels

@Client.on_message(filters.private & filters.command(["send", "send_more_channel", "send more channel"]))
async def send_cmd(client, message: Message):
    channels = get_saved_channels()
    if not channels:
        return await message.reply_text("No channels saved! Add them via /force_sub first.")
    
    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(ch['channel_name'], callback_data=f"sendto_{ch['channel_id']}")])
    
    await message.reply_text("Select channel to send post:\n(Press /confirm after selecting for multi-channels)", 
                             reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r"^sendto_"))
async def handle_sendto(client, query: CallbackQuery):
    ch_id = query.data.split("_")[1]
    user_id = query.from_user.id
    
    if "selected_channels" not in USER_STATE.get(user_id, {}):
        USER_STATE[user_id] = {"selected_channels": []}
    
    USER_STATE[user_id]["selected_channels"].append(ch_id)
    await query.answer("Channel selected! Select more or type /confirm", show_alert=True)

@Client.on_message(filters.private & filters.command("confirm"))
async def confirm_send(client, message: Message):
    user_id = message.from_user.id
    
    # Agar multi-channel sending confirm ho raha hai
    if "selected_channels" in USER_STATE.get(user_id, {}):
        post_data = USER_STATE[user_id].get("last_post_id")
        if not post_data: return await message.reply_text("No recent post found to send!")
        
        for ch_id in USER_STATE[user_id]["selected_channels"]:
            # Yaha bot Storage channel se user channel me post bhejeka
            # Placeholder for exact post formatting
            await client.send_message(int(ch_id), f"New Episode Here!\nhttps://t.me/{client.me.username}?start={post_data}")
            
        await message.reply_text("Post sent to all selected channels ✅")
        del USER_STATE[user_id]["selected_channels"]
