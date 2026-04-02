from pyrogram import Client, filters
from pyrogram.types import Message
from plugins.helpers import USER_STATE, is_admin, add_premium, remove_premium, db

@Client.on_message(filters.command(["add_shortner_account", "add shortner account"]) & filters.private)
async def add_shortner(client, message: Message):
    if not is_admin(message.from_user.id): return
    USER_STATE[message.from_user.id] = {"step": "wait_shortner_url"}
    await message.reply_text("Provide Shortner API URL:")

@Client.on_message(filters.command(["add_premium", "add premium"]) & filters.private)
async def add_prem(client, message: Message):
    if not is_admin(message.from_user.id): return
    USER_STATE[message.from_user.id] = {"step": "wait_prem_id"}
    await message.reply_text("Send user ID for Premium:")

@Client.on_message(filters.command("hu hu") & filters.private)
async def huhu_confirm(client, message: Message):
    user_id = message.from_user.id
    if USER_STATE.get(user_id, {}).get("step") == "wait_prem_confirm":
        add_premium(int(USER_STATE[user_id]["target_id"]))
        await message.reply_text("Premium added (28 days) ✅")
        del USER_STATE[user_id]

@Client.on_message(filters.command(["remove_premium", "remove premium"]) & filters.private)
async def rem_prem(client, message: Message):
    if not is_admin(message.from_user.id): return
    USER_STATE[message.from_user.id] = {"step": "wait_rem_prem_id"}
    await message.reply_text("Send user ID to remove premium:")

@Client.on_message(filters.command(["show_premium_list", "show premium list"]) & filters.private)
async def show_prem(client, message: Message):
    if not is_admin(message.from_user.id): return
    res = db.table("premium_users").select("user_id").execute()
    if res.data:
        text = "🔰 Premium Users:\n" + "\n".join([f"👤 `{u['user_id']}`" for u in res.data])
        await message.reply_text(text)
    else:
        await message.reply_text("No premium users.")
