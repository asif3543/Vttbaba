from pyrogram import Client, filters
from pyrogram.types import Message
import database
import config

STATE = {}

@Client.on_message(filters.command("add shortner account") & filters.user(config.ADMINS))
async def cmd_add_shortner(client: Client, message: Message):
    STATE[message.from_user.id] = {"step": "wait_url"}
    await message.reply("Bot reply - provide deskbord url\nGp link / any short")

@Client.on_message(filters.text & filters.user(config.ADMINS))
async def handle_shortner_text(client: Client, message: Message):
    uid = message.from_user.id
    state = STATE.get(uid, {})
    text = message.text

    if text.startswith("/") and text != "/delete": return

    if state.get("step") == "wait_url":
        domain = text.replace("https://", "").replace("http://", "").split("/")[0]
        STATE[uid]['domain'] = domain
        STATE[uid]['step'] = "wait_token"
        await message.reply("Bot reply - successfully send Your API Token")

    elif state.get("step") == "wait_token":
        database.add_shortner(STATE[uid]['domain'], text)
        STATE.pop(uid, None)
        await message.reply("Bot reply - successfully add 🤗🤗🤗")

    elif state.get("step") == "wait_del_id":
        try:
            STATE[uid]['del_id'] = int(text)
            STATE[uid]['step'] = "wait_del_confirm"
            await message.reply("Bot reply - kya aap hatana chahte hai\nToh delete (Type /delete)")
        except: pass

@Client.on_message(filters.command("remove shortner account") & filters.user(config.ADMINS))
async def cmd_rem_shortner(client: Client, message: Message):
    shortners = database.get_shortners()
    if not shortners:
        await message.reply("No shortners available.")
        return
    text = "Bot - select account\n\n"
    for s in shortners:
        text += f"ID: `{s['id']}` - {s['shortner_url']}\n"
    STATE[message.from_user.id] = {"step": "wait_del_id"}
    await message.reply(text + "\nSend ID to delete:")

@Client.on_message(filters.command("delete") & filters.user(config.ADMINS))
async def cmd_del_confirm(client: Client, message: Message):
    uid = message.from_user.id
    if STATE.get(uid, {}).get("step") == "wait_del_confirm":
        database.remove_shortner(STATE[uid]['del_id'])
        STATE.pop(uid, None)
        await message.reply("Bot reply - successfully delete account for shortner")
