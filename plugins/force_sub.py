from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from database import db

# ==============================
# 🔰 ADD FORCE SUB CHANNEL
# ==============================
@Client.on_message(filters.command("force sub") & filters.private)
async def add_force_sub(client: Client, message: Message):

    user_id = message.from_user.id

    if user_id != Config.OWNER_ID:
        return await message.reply("❌ Only owner allowed")

    await message.reply("📢 Forward a message from the channel")


# ==============================
# 🔰 SAVE CHANNEL
# ==============================
@Client.on_message(filters.forwarded & filters.private)
async def save_channel(client: Client, message: Message):

    user_id = message.from_user.id

    if user_id != Config.OWNER_ID:
        return

    if not message.forward_from_chat:
        return

    chat = message.forward_from_chat

    if chat.type != "channel":
        return await message.reply("❌ Not a channel")

    try:
        member = await client.get_chat_member(chat.id, "me")
        if member.status not in ["administrator", "creator"]:
            return await message.reply("❌ Bot is not admin")
    except:
        return await message.reply("❌ Error checking admin")

    await db.add_force_channel(chat.id, chat.title)

    await message.reply(f"✅ Added: {chat.title}")


# ==============================
# 🔰 CHECK JOIN
# ==============================
async def check_force_sub(client: Client, user_id: int):

    channels = await db.get_force_channels()
    not_joined = []

    for ch in channels:
        try:
            member = await client.get_chat_member(ch["channel_id"], user_id)

            if member.status in ["left", "kicked"]:
                not_joined.append(ch)

        except:
            not_joined.append(ch)

    return not_joined


# ==============================
# 🔰 BUTTONS
# ==============================
async def force_sub_buttons(client: Client, user_id: int):

    channels = await db.get_force_channels()
    buttons = []

    for ch in channels:
        # ✅ SAFE LINK (NO API CALL)
        link = f"https://t.me/{ch['channel_name'].replace(' ', '')}"

        buttons.append([InlineKeyboardButton(ch["channel_name"], url=link)])

    buttons.append([InlineKeyboardButton("🔄 Try Again", callback_data="check_join")])

    return InlineKeyboardMarkup(buttons)


# ==============================
# 🔰 TRY AGAIN
# ==============================
@Client.on_callback_query(filters.regex("check_join"))
async def recheck_join(client: Client, query: CallbackQuery):

    user_id = query.from_user.id

    not_joined = await check_force_sub(client, user_id)

    if not not_joined:
        await query.answer("✅ Done! Now click your link again", show_alert=True)
        return

    await query.answer("❌ Join all channels first", show_alert=True)
