Enterfrom pyrogram import Client, filters
from pyrogram.types import Message
from plugins.helpers import USER_STATE, db, is_admin, add_premium, remove_premium

@Client.on_message(filters.private & filters.command(["add_shortner_account", "add shortner account"]))
async def add_shortner(client, message: Message):
    if not is_admin(message.from_user.id): return
    USER_STATE[message.from_user.id] = {"step": "wait_shortner_url"}
    await message.reply_text("Provide shortner dashboard API URL (e.g., https://shortner.com/api):")

@Client.on_message(filters.private & filters.command(["add_premium", "add premium"]))
async def add_prem_cmd(client, message: Message):
    if not is_admin(message.from_user.id): return
    USER_STATE[message.from_user.id] = {"step": "wait_prem_id"}
    await message.reply_text("Send user ID for Premium:")

@Client.on_message(filters.private & filters.command("hu hu"))
async def huhu_confirm(client, message: Message):
    user_id = message.from_user.id
    if user_id in USER_STATE and USER_STATE[user_id].get("step") == "wait_prem_confirm":
        target_id = USER_STATE[user_id]["target_id"]
        add_premium(int(target_id))
        await message.reply_text("Premium added (28 days) ✅")
        del USER_STATE[user_id]

@Client.on_message(filters.private & filters.command(["remove_premium", "remove premium"]))
async def rem_prem(client, message: Message):
    if not is_admin(message.from_user.id): return
    USER_STATE[message.from_user.id] = {"step": "wait_rem_prem_id"}
    await message.reply_text("Send user ID to remove premium:")

@Client.on_message(filters.private & filters.command(["show_premium_list", "show premium list"]))
async def show_prem(client, message: Message):
    if not is_admin(message.from_user.id): return
    res = db.table("premium_users").select("user_id").execute()
    if res.data:
        text = "🔰 **Premium Users List:**\n\n"
        for user in res.data:
            text += f"👤 `{user['user_id']}`\n"
        await message.reply_text(text)
    else:
        await message.reply_text("No premium users found.")

@Client.on_message(filters.private & filters.command(["force_sub", "force sub"]))
async def force_sub_cmd(client, message: Message):
    if not is_admin(message.from_user.id): return
    USER_STATE[message.from_user.id] = {"step": "wait_fsub_channel"}
    await message.reply_text("Send channel message (Forward from channel where bot is admin):")
