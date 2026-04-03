from pyrogram import Client, filters
from pyrogram.types import Message
from config import OWNER_ID, USER_STATE
from database import add_premium, remove_premium, add_shortener, add_force_sub

# Space वाले Commands के लिए Filters.regex इस्तेमाल किया गया है
@Client.on_message(filters.regex(r"(?i)^/add premium") & filters.user(OWNER_ID) & filters.private)
async def cmd_add_prem(client: Client, message: Message):
    USER_STATE[message.from_user.id] = {"step": "premium_add"}
    await message.reply_text("Send user ID")

@Client.on_message(filters.regex(r"(?i)^/remove premium") & filters.user(OWNER_ID) & filters.private)
async def cmd_rem_prem(client: Client, message: Message):
    USER_STATE[message.from_user.id] = {"step": "premium_rem"}
    await message.reply_text("Send user ID")

@Client.on_message(filters.regex(r"(?i)^/add shortner account") & filters.user(OWNER_ID) & filters.private)
async def cmd_add_short(client: Client, message: Message):
    USER_STATE[message.from_user.id] = {"step": "shortner_url"}
    await message.reply_text("Provide dashboard URL")

@Client.on_message(filters.regex(r"(?i)^/force sub") & filters.user(OWNER_ID) & filters.private)
async def cmd_fsub(client: Client, message: Message):
    USER_STATE[message.from_user.id] = {"step": "fsub_msg"}
    await message.reply_text("Send channel message")

@Client.on_message(filters.user(OWNER_ID) & filters.private, group=3)
async def admin_flow(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in USER_STATE: return
    step = USER_STATE[user_id].get("step")

    if step == "premium_add" and message.text:
        USER_STATE[user_id]["target_id"] = int(message.text)
        USER_STATE[user_id]["step"] = "premium_confirm"
        await message.reply_text("Type /hu hu")
        
    elif step == "premium_confirm" and message.text.lower() == "/hu hu":
        await add_premium(USER_STATE[user_id]["target_id"])
        await message.reply_text("Premium added (28 days) ✅")
        del USER_STATE[user_id]
        
    elif step == "premium_rem" and message.text:
        await remove_premium(int(message.text))
        await message.reply_text("Premium removed ❌")
        del USER_STATE[user_id]
        
    elif step == "shortner_url" and message.text:
        USER_STATE[user_id]["url"] = message.text
        USER_STATE[user_id]["step"] = "shortner_api"
        await message.reply_text("Send API token")
        
    elif step == "shortner_api" and message.text:
        await add_shortener("Shortener", USER_STATE[user_id]["url"], message.text)
        await message.reply_text("Successfully added ✅")
        del USER_STATE[user_id]
        
    elif step == "fsub_msg" and message.forward_from_chat:
        chat = message.forward_from_chat
        await add_force_sub(chat.id, chat.title)
        await message.reply_text("Channel added for force join ✅")
        del USER_STATE[user_id]
