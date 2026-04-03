from pyrogram import Client, filters
from pyrogram.types import Message
from config import OWNER_ID, ADMINS
from database import add_premium, remove_premium, add_shortener, add_force_sub

# --- PREMIUM COMMANDS ---
@Client.on_message(filters.command("add premium") & filters.user(OWNER_ID))
async def cmd_add_premium(client: Client, message: Message):
    await message.reply_text("Send User ID")
    user_state[message.from_user.id] = {"step": "premium_add"}

@Client.on_message(filters.command("remove premium") & filters.user(OWNER_ID))
async def cmd_remove_premium(client: Client, message: Message):
    try:
        user_id = int(message.text.split(" ")[1]) # Example: /remove premium 123456
        remove_premium(user_id)
        await message.reply_text("Successfully deleted and ban")
    except:
        await message.reply_text("Send ID with command: /remove premium [ID]")

@Client.on_message(filters.command("hu hu") & filters.user(OWNER_ID))
async def confirm_premium(client: Client, message: Message):
    if user_state.get(message.from_user.id, {}).get("step") == "premium_add_confirm":
        user_id = user_state[message.from_user.id]["user_id"]
        add_premium(user_id)
        await message.reply_text(f"Successfully add member {user_id} 🪄🪄🪄")
        del user_state[message.from_user.id]

# --- SHORTENER COMMANDS ---
@Client.on_message(filters.command("add shortner account") & filters.user(OWNER_ID))
async def cmd_add_shortner(client: Client, message: Message):
    user_state[message.from_user.id] = {"step": "shortner_url"}
    await message.reply_text("Provide dashboard URL (API URL)")

# --- FORCE SUB SYSTEM ---
@Client.on_message(filters.command("force sub") & filters.user(OWNER_ID))
async def cmd_force_sub(client: Client, message: Message):
    user_state[message.from_user.id] = {"step": "force_sub_fwd"}
    await message.reply_text("Please send message and check I'm admin in gc")

@Client.on_message(filters.user(OWNER_ID), group=2)
async def admin_workflow(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_state:
        return
    
    step = user_state[user_id].get("step")

    # Premium Logic
    if step == "premium_add":
        user_state[user_id]["user_id"] = int(message.text)
        user_state[user_id]["step"] = "premium_add_confirm"
        await message.reply_text("Successfully add member\nPlease confirm type /hu hu")

    # Shortener Logic
    elif step == "shortner_url":
        user_state[user_id]["url"] = message.text
        user_state[user_id]["step"] = "shortner_api"
        await message.reply_text("Successfully send. Your API Token?")
    elif step == "shortner_api":
        add_shortener("Shortener", user_state[user_id]["url"], message.text)
        await message.reply_text("Successfully add 🤗🤗🤗")
        del user_state[user_id]

    # Force Sub Logic
    elif step == "force_sub_fwd" and message.forward_from_chat:
        chat = message.forward_from_chat
        add_force_sub(chat.id, chat.title)
        await message.reply_text("😘 adding successfully 😲")
        del user_state[user_id]

# Note: Add `user_state = {}` variable at the top of this file or import it from a common utils file. 
# For simplicity, we can just define `user_state = {}` globally in this plugin too (Pyrogram loads them independently).
user_state = {}
