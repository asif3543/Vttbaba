herefrom pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from database import db
import aiohttp

# ==============================
# 🔰 ADD SHORTNER ACCOUNT
# ==============================
@Client.on_message(filters.command("add") & filters.private)
async def add_shortner(client: Client, message: Message):

    user_id = message.from_user.id

    if user_id != Config.OWNER_ID:
        return await message.reply("❌ Only owner allowed")

    await message.reply("🔗 Send shortner API URL\nExample:\nhttps://example.com/api")

    Config.TEMP[user_id] = {"step": "shortner_url"}


@Client.on_message(filters.private & filters.text)
async def get_shortner_details(client: Client, message: Message):

    user_id = message.from_user.id

    if user_id not in Config.TEMP:
        return

    step = Config.TEMP[user_id].get("step")

    # 🔹 Step 1: URL
    if step == "shortner_url":
        Config.TEMP[user_id]["api_url"] = message.text.strip()
        Config.TEMP[user_id]["step"] = "shortner_key"
        return await message.reply("🔑 Send API Key")

    # 🔹 Step 2: API KEY
    elif step == "shortner_key":
        api_url = Config.TEMP[user_id]["api_url"]
        api_key = message.text.strip()

        await db.add_shortner(api_url=api_url, api_key=api_key)

        Config.TEMP.pop(user_id)

        await message.reply("✅ Shortner added successfully")


# ==============================
# 🔰 REMOVE SHORTNER
# ==============================
@Client.on_message(filters.command("remove shortner account") & filters.private)
async def remove_shortner(client: Client, message: Message):

    user_id = message.from_user.id

    if user_id != Config.OWNER_ID:
        return await message.reply("❌ Only owner allowed")

    accounts = await db.get_shortners()

    if not accounts:
        return await message.reply("❌ No accounts found")

    buttons = []
    for acc in accounts:
        buttons.append([
            InlineKeyboardButton(
                f"{acc['api_url']}",
                callback_data=f"del_{acc['id']}"
            )
        ])

    await message.reply(
        "🗑 Select account to remove:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@Client.on_callback_query()
async def delete_shortner(client: Client, query: CallbackQuery):

    data = query.data

    if data.startswith("del_"):
        shortner_id = data.split("_")[1]

        await db.delete_shortner(shortner_id)

        await query.message.reply("✅ Shortner removed")
        await query.answer()


# ==============================
# 🔰 SHORT LINK GENERATOR (ROTATION)
# ==============================
async def generate_short_link(original_url: str):

    accounts = await db.get_shortners()

    if not accounts:
        return original_url  # fallback

    for acc in accounts:
        try:
            api_url = acc["api_url"]
            api_key = acc["api_key"]

            url = f"{api_url}?api={api_key}&url={original_url}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as res:
                    data = await res.json()

                    # 🔹 Common API format
                    if data.get("status") == "success":
                        return data.get("shortenedUrl") or data.get("short")

        except Exception:
            continue  # try next account

    return original_url  # fallback if all fail
