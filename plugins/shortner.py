from pyrogram import Client, filters
from pyrogram.types import Message
import database
import config

STATE = {}

@Client.on_message(filters.command("add shortner account") & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def add_shortner(client: Client, message: Message):
    STATE[message.from_user.id] = {"step": "wait_domain"}
    await message.reply("Bot reply - provide deskbord url\nGp link / any short")

@Client.on_message(filters.text & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def shortner_text_handler(client: Client, message: Message):
    uid = message.from_user.id
    state = STATE.get(uid, {})
    
    if message.text.startswith("/"):
        return

    if state.get("step") == "wait_domain":
        STATE[uid]['domain'] = message.text.replace("https://", "").replace("http://", "").split("/")[0]
        STATE[uid]['step'] = "wait_api"
        await message.reply("Bot reply - successfully send Your API Token")
        
    elif state.get("step") == "wait_api":
        api_token = message.text
        database.add_shortner(STATE[uid]['domain'], api_token)
        STATE.pop(uid, None)
        await message.reply("Bot reply - successfully add 🤗🤗🤗")

@Client.on_message(filters.command("remove shortner account") & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def remove_shortner(client: Client, message: Message):
    shortners = database.get_shortners()
    if not shortners:
        await message.reply("Koi shortner nahi mila.")
        return
        
    text = "Bot - select account\n\n"
    for s in shortners:
        text += f"ID: `{s['id']}` - {s['shortner_url'].split('|')[0]}\n"
    text += "\nSend ID to delete:"
    
    STATE[message.from_user.id] = {"step": "wait_delete_id"}
    await message.reply(text)

@Client.on_message(filters.text & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def shortner_delete_handler(client: Client, message: Message):
    uid = message.from_user.id
    if STATE.get(uid, {}).get("step") == "wait_delete_id":
        try:
            STATE[uid]['del_id'] = int(message.text)
            STATE[uid]['step'] = "wait_delete_confirm"
            await message.reply("Bot reply - kya aap hatana chahte hai\nToh delete (Type /delete)")
        except:
            pass

@Client.on_message(filters.command("delete") & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def confirm_delete(client: Client, message: Message):
    uid = message.from_user.id
    if STATE.get(uid, {}).get("step") == "wait_delete_confirm":
        database.remove_shortner(STATE[uid]['del_id'])
        STATE.pop(uid, None)
        await message.reply("Bot reply - successfully delete account for shortner")
