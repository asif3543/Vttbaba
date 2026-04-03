from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from database import db
from datetime import datetime, timedelta, timezone

@Client.on_message(filters.command(["add shortner account"]) & filters.private)
async def add_sh(client: Client, message: Message):
    if message.from_user.id != Config.OWNER_ID: return
    Config.STATE[message.from_user.id] = {"step": "WAIT_SHORT_URL"}
    await message.reply("Provide dashboard URL")

@Client.on_message(filters.command(["remove shortner account"]) & filters.private)
async def rem_sh(client: Client, message: Message):
    if message.from_user.id != Config.OWNER_ID: return
    accounts = await db.get_shortners()
    btns = [[InlineKeyboardButton(f"{a['api_url']}", callback_data=f"delsh_{a['id']}")] for a in accounts]
    await message.reply("Select account", reply_markup=InlineKeyboardMarkup(btns))

@Client.on_callback_query(filters.regex(r"^delsh_"))
async def del_sh_cb(client: Client, query: CallbackQuery):
    Config.STATE[query.from_user.id] = {"step": "DEL_SHORT", "del_id": query.data.split("_")[1]}
    await query.message.reply("Confirm delete (type `/delete`)")

@Client.on_message(filters.command(["add premium"]) & filters.private)
async def add_pr(client: Client, message: Message):
    if message.from_user.id != Config.OWNER_ID: return
    Config.STATE[message.from_user.id] = {"step": "WAIT_PREM_ID"}
    await message.reply("Send I'd")

@Client.on_message(filters.command(["remove premium"]) & filters.private)
async def rem_pr(client: Client, message: Message):
    if message.from_user.id != Config.OWNER_ID: return
    Config.STATE[message.from_user.id] = {"step": "WAIT_REM_PREM_ID"}
    await message.reply("Send I'd")

@Client.on_message(filters.command(["show premium list"]) & filters.private)
async def show_pr(client: Client, message: Message):
    if message.from_user.id != Config.OWNER_ID: return
    users = await db.get_all_premium()
    txt = "💎 **Premium Users:**\n" + "\n".join([f"ID: `{u['user_id']}`" for u in users]) if users else "No premium users."
    await message.reply(txt)

@Client.on_message(filters.command(["force sub"]) & filters.private)
async def f_sub(client: Client, message: Message):
    if message.from_user.id != Config.OWNER_ID: return
    Config.STATE[message.from_user.id] = {"step": "WAIT_FSUB_MSG"}
    await message.reply("Send channel message")

@Client.on_message(filters.text & filters.private, group=1)
async def admin_text(client: Client, message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    step = Config.STATE.get(user_id, {}).get("step")

    if step == "WAIT_SHORT_URL":
        Config.STATE[user_id]["short_url"] = text
        Config.STATE[user_id]["step"] = "WAIT_SHORT_API"
        await message.reply("Send API token")
    elif step == "WAIT_SHORT_API":
        await db.add_shortner("Shortner", Config.STATE[user_id]["short_url"], text)
        await message.reply("Successfully added ✅")
        Config.STATE.pop(user_id, None)
    elif step == "DEL_SHORT" and text == "/delete":
        await db.delete_shortner(Config.STATE[user_id]["del_id"])
        await message.reply("Account removed ✅")
        Config.STATE.pop(user_id, None)
    elif step == "WAIT_PREM_ID":
        Config.STATE[user_id]["prem_id"] = int(text)
        await message.reply("Type /hu hu")
    elif step == "WAIT_PREM_ID" and text == "/hu hu":
        tid = Config.STATE[user_id]["prem_id"]
        exp = datetime.now(timezone.utc) + timedelta(days=28)
        await db.add_premium(tid, exp)
        await message.reply(f"Premium added (28 days) ✅")
        Config.STATE.pop(user_id, None)
    elif step == "WAIT_REM_PREM_ID":
        await db.remove_premium(int(text))
        await message.reply("Premium removed ❌")
        Config.STATE.pop(user_id, None)

@Client.on_message(filters.forwarded & filters.private, group=1)
async def admin_fwd(client: Client, message: Message):
    user_id = message.from_user.id
    if Config.STATE.get(user_id, {}).get("step") == "WAIT_FSUB_MSG":
        if message.forward_from_chat and message.forward_from_chat.type.value == "channel":
            await db.add_force_channel(message.forward_from_chat.id, message.forward_from_chat.title)
            await message.reply("Channel added for force join ✅")
            Config.STATE.pop(user_id, None)
