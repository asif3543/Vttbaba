from pyrogram import Client, filters
from pyrogram.types import Message
from database import db
from plugins.post import STATE
from config import Config

@Client.on_message(filters.command(["add_shortner_account", "add shortner account"]) & filters.private)
async def add_shortner(client, message: Message):
    if message.from_user.id != Config.OWNER_ID: return
    STATE[message.from_user.id] = {"step": "WAIT_SHORTNER_URL"}
    await message.reply_text("Provide dashboard URL")

@Client.on_message(filters.command(["add_premium", "add premium"]) & filters.private)
async def add_premium(client, message: Message):
    if message.from_user.id != Config.OWNER_ID: return
    STATE[message.from_user.id] = {"step": "WAIT_PREM_ID"}
    await message.reply_text("Send user ID")

@Client.on_message(filters.command("hu hu") & filters.private) # Prem confirm
async def hu_hu(client, message: Message):
    user_id = message.from_user.id
    if STATE.get(user_id, {}).get("step") == "WAIT_PREM_ID":
        target = STATE[user_id]["target_id"]
        db.table("premium_users").insert({"user_id": target, "expiry_date": "now() + interval '28 days'"}).execute()
        await message.reply_text("Premium added (28 days) ✅")

@Client.on_message(filters.command(["force_sub", "force sub"]) & filters.private)
async def force_sub(client, message: Message):
    if message.from_user.id != Config.OWNER_ID: return
    STATE[message.from_user.id] = {"step": "WAIT_FSUB"}
    await message.reply_text("Send channel message")

@Client.on_message(filters.private & ~filters.command(["start", "post", "link", "batch_link", "hmm", "confirm", "send", "send_more_channel", "yes", "hu_hu"]))
async def admin_text_handler(client, message: Message):
    user_id = message.from_user.id
    step = STATE.get(user_id, {}).get("step")
    
    if step == "WAIT_SHORTNER_URL":
        STATE[user_id]["shortner_url"] = message.text
        STATE[user_id]["step"] = "WAIT_SHORTNER_API"
        await message.reply_text("Send API token")
        
    elif step == "WAIT_SHORTNER_API":
        db.table("shortner_accounts").insert({"name": "Shortner", "api_url": STATE[user_id]["shortner_url"], "api_key": message.text}).execute()
        await message.reply_text("Successfully added ✅")
        
    elif step == "WAIT_PREM_ID":
        STATE[user_id]["target_id"] = int(message.text)
        await message.reply_text("Type /hu hu")

    elif step == "WAIT_FSUB":
        if message.forward_from_chat:
            ch_id = message.forward_from_chat.id
            ch_name = message.forward_from_chat.title
            db.table("force_sub_channels").insert({"channel_id": ch_id, "channel_name": ch_name}).execute()
            db.table("channels").insert({"channel_id": ch_id, "channel_name": ch_name}).execute()
            await message.reply_text("Channel added for force join ✅")
