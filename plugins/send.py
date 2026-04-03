from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import ADMINS, USER_STATE
from database import get_channels

@Client.on_message((filters.command("send") | filters.regex(r"(?i)^/send more channel")) & filters.user(ADMINS) & filters.private)
async def send_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if USER_STATE.get(user_id, {}).get("step") != "ready_to_send":
        return await message.reply_text("❌ Create a post first using /post")
    
    channels = await get_channels()
    if not channels: return await message.reply_text("No channels found.")

    mode = "multi" if "more" in message.text else "single"
    USER_STATE[user_id]["send_mode"] = mode
    USER_STATE[user_id]["selected"] =[]

    btns = [[InlineKeyboardButton(ch["channel_name"], callback_data=f"sel_{ch['channel_id']}")] for ch in channels]
    await message.reply_text("Show channel list:", reply_markup=InlineKeyboardMarkup(btns))

@Client.on_callback_query(filters.regex(r"^sel_"))
async def select_ch(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    ch_id = int(query.data.split("_")[1])
    
    if USER_STATE[user_id]["send_mode"] == "single":
        USER_STATE[user_id]["selected"] = [ch_id]
        await query.message.reply_text("Confirm please (/confirm)")
    else:
        if ch_id in USER_STATE[user_id]["selected"]: USER_STATE[user_id]["selected"].remove(ch_id)
        else: USER_STATE[user_id]["selected"].append(ch_id)
        await query.answer("Selected!")
        await query.message.reply_text("Confirm please (/confirm)")

@Client.on_message(filters.command("confirm") & filters.user(ADMINS) & filters.private, group=2)
async def do_send(client: Client, message: Message):
    user_id = message.from_user.id
    state = USER_STATE.get(user_id, {})
    
    if state.get("step") != "ready_to_send" or not state.get("selected"): 
        return
    
    for ch in state["selected"]:
        await client.copy_message(chat_id=ch, from_chat_id=user_id, message_id=state["post_msg_id"], reply_markup=state["ready_btn"])
    
    await message.reply_text("Post sent ✅")
    del USER_STATE[user_id]
