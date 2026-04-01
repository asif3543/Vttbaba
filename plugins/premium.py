from pyrogram import Client, filters
from pyrogram.types import Message
import database
import config

STATE = {}

@Client.on_message(filters.command("add premium") & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def add_prem(client: Client, message: Message):
    STATE[message.from_user.id] = {"step": "wait_prem_id"}
    await message.reply("Bot reply - send I'd")

@Client.on_message(filters.text & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def prem_id_handler(client: Client, message: Message):
    uid = message.from_user.id
    if STATE.get(uid, {}).get("step") == "wait_prem_id" and not message.text.startswith("/"):
        STATE[uid]['prem_id'] = int(message.text)
        STATE[uid]['step'] = "wait_huhu"
        await message.reply("Bot reply - successfully add member\nPleas confirm type /hu hu")

@Client.on_message(filters.command("hu hu") & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def huhu_handler(client: Client, message: Message):
    uid = message.from_user.id
    if STATE.get(uid, {}).get("step") == "wait_huhu":
        target_id = STATE[uid]['prem_id']
        database.add_premium(target_id)
        STATE.pop(uid, None)
        await message.reply(f"Bot - successfully add member {target_id} 🪄🪄🪄")

@Client.on_message(filters.command("remove premium") & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def rem_prem(client: Client, message: Message):
    STATE[message.from_user.id] = {"step": "wait_rem_id"}
    await message.reply("Bot reply - send I'd")

@Client.on_message(filters.text & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def rem_id_handler(client: Client, message: Message):
    uid = message.from_user.id
    if STATE.get(uid, {}).get("step") == "wait_rem_id" and not message.text.startswith("/"):
        target_id = int(message.text)
        database.remove_premium(target_id)
        STATE.pop(uid, None)
        await message.reply("Bot reply - successfully deleted and ban")

@Client.on_message(filters.command("show premium list") & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def show_prem(client: Client, message: Message):
    users = database.get_all_premium()
    if not users:
        await message.reply("No premium users found.")
        return
    text = "👑 **Premium Users List:**\n"
    for u in users:
        text += f"ID: `{u['user_id']}` (Valid till: {u['valid_until'][:10]})\n"
    await message.reply(text)
