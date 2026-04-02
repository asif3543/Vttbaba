from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from plugins.post import STATE
from database import db
from config import Config

def get_channels():
    return db.table("channels").select("*").execute().data

@Client.on_message(filters.command(["send", "send_more_channel", "send more channel"]) & filters.private)
async def send_cmd(client, message: Message):
    user_id = message.from_user.id
    if user_id not in Config.ALLOWED_USERS: return
    
    channels = get_channels()
    if not channels:
        return await message.reply_text("No channels added in database!")

    buttons = [[InlineKeyboardButton(ch['channel_name'], callback_data=f"sendto_{ch['channel_id']}")] for ch in channels]
    
    STATE[user_id]["selected_channels"] = []
    STATE[user_id]["send_mode"] = "multi" if "more" in message.text else "single"
    
    await message.reply_text("Select channel(s):\n(Click /yes to confirm sending)", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r"^sendto_"))
async def select_channel(client, query: CallbackQuery):
    ch_id = int(query.data.split("_")[1])
    user_id = query.from_user.id
    
    if ch_id not in STATE[user_id].get("selected_channels", []):
        STATE[user_id]["selected_channels"].append(ch_id)
        
    await query.answer("Channel selected! Click /yes to send.", show_alert=False)

@Client.on_message(filters.command("yes") & filters.private)
async def confirm_send(client, message: Message):
    user_id = message.from_user.id
    if "final_post" not in STATE.get(user_id, {}): return
    
    channels = STATE[user_id].get("selected_channels", [])
    post = STATE[user_id]["final_post"]
    
    if not channels: return await message.reply_text("No channels selected!")
    
    for ch_id in channels:
        try:
            await client.copy_message(ch_id, user_id, post["msg_id"], reply_markup=post["markup"])
        except Exception as e:
            await message.reply_text(f"Error sending to {ch_id}: {e}")
            
    await message.reply_text("Post sent ✅")
    del STATE[user_id]
