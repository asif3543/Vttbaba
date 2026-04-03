Enterfrom pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from database import db
from datetime import datetime, timedelta

# ==============================
# 🔰 ADD PREMIUM
# ==============================
@Client.on_message(filters.command("add premium") & filters.private)
async def add_premium(client: Client, message: Message):
    if message.from_user.id != Config.OWNER_ID:
        return await message.reply("❌ Only owner allowed")

    Config.TEMP[message.from_user.id] = {"step": "add_id"}
    await message.reply("👤 Send User ID")


# ==============================
# 🔰 REMOVE PREMIUM
# ==============================
@Client.on_message(filters.command("remove premium") & filters.private)
async def remove_premium(client: Client, message: Message):
    if message.from_user.id != Config.OWNER_ID:
        return await message.reply("❌ Only owner allowed")

    Config.TEMP[message.from_user.id] = {"step": "remove_id"}
    await message.reply("👤 Send User ID")


# ==============================
# 🔰 HANDLE TEXT
# ==============================
@Client.on_message(filters.private & filters.text)
async def premium_handler(client: Client, message: Message):

    user_id = message.from_user.id

    if user_id not in Config.TEMP:
        return

    step = Config.TEMP[user_id]["step"]
    text = message.text.strip()

    if step == "add_id":
        target = int(text)
        expiry = datetime.utcnow() + timedelta(days=28)

        await db.add_premium(target, expiry)
        Config.TEMP.pop(user_id)

        await message.reply(f"✅ Added Premium\n👤 {target}")

    elif step == "remove_id":
        target = int(text)

        await db.remove_premium(target)
        Config.TEMP.pop(user_id)

        await message.reply(f"❌ Removed Premium\n👤 {target}")


# ==============================
# 🔰 SHOW LIST
# ==============================
@Client.on_message(filters.command("show premium list") & filters.private)
async def show_premium(client: Client, message: Message):

    if message.from_user.id != Config.OWNER_ID:
        return

    users = await db.get_all_premium()

    if not users:
        return await message.reply("❌ No users")

    txt = "💎 Premium Users:\n\n"
    for u in users:
        txt += f"{u['user_id']} → {u['expiry_date']}\n"

    await message.reply(txt)


# ==============================
# 🔰 CHECK PREMIUM
# ==============================
async def is_premium(user_id: int):
    user = await db.get_premium(user_id)

    if not user:
        return False

    if datetime.utcnow() > user["expiry_date"]:
        await db.remove_premium(user_id)
        return False

    return True
