from pyrogram import Client, filters
from pyrogram.types import Message
import database
import config

STATE = {}

@Client.on_message(filters.command(["add premium", "add_premium"]) & filters.user(config.ADMINS))
async def cmd_add_prem(client: Client, message: Message):
    STATE[message.from_user.id] = {"step": "wait_prem_id"}
    await message.reply("Bot reply - send I'd")

@Client.on_message(filters.text & filters.user(config.ADMINS))
async def handle_prem_text(client: Client, message: Message):
    uid = message.from_user.id
    state = STATE.get(uid, {})
    text = message.text

    if text.startswith("/") and text != "/hu hu": return

    if state.get("step") == "wait_prem_id":
        STATE[uid]['prem_id'] = int(text)
        STATE[uid]['step'] = "wait_huhu"
        await message.reply("Bot reply - successfully add member\nPleas confirm type /hu hu")

    elif state.get("step") == "wait_rem_id":
        database.remove_premium(int(text))
        STATE.pop(uid, None)
        await message.reply("Bot reply - successfully deleted and ban")

@Client.on_message(filters.command("hu hu") & filters.user(config.ADMINS))
async def cmd_huhu(client: Client, message: Message):
    uid = message.from_user.id
    if STATE.get(uid, {}).get("step") == "wait_huhu":
        user_id = STATE[uid]['prem_id']
        database.add_premium(user_id)
        STATE.pop(uid, None)
        await message.reply(f"Bot - successfully add member {user_id} 🪄🪄🪄")

@Client.on_message(filters.command(["remove premium", "remove_premium"]) & filters.user(config.ADMINS))
async def cmd_rem_prem(client: Client, message: Message):
    STATE[message.from_user.id] = {"step": "wait_rem_id"}
    await message.reply("Bot reply - send I'd")

@Client.on_message(filters.command("show premium list") & filters.user(config.ADMINS))
async def cmd_show_prem(client: Client, message: Message):
    users = database.get_all_premium()
    text = "👑 **Premium Users:**\n"
    for u in users: text += f"ID: `{u['user_id']}` (Exp: {u['valid_until'][:10]})\n"
    await message.reply(text if users else "No premium users.")
