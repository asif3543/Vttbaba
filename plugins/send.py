from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from database import db
from plugins.post import user_states

# ==============================
# 🔰 SEND (SINGLE)
# ==============================
@Client.on_message(filters.command("send") & filters.private)
async def send_single(client: Client, message: Message):

    user_id = message.from_user.id

    # 🔒 Admin check
    if user_id != Config.OWNER_ID and user_id not in Config.ALLOWED_USERS:
        return await message.reply("❌ Not authorized")

    if user_id not in user_states:
        return await message.reply("❌ No post found. Use /post first")

    channels = await db.get_channels()

    if not channels:
        return await message.reply("❌ No channels found")

    buttons = []
    for ch in channels:
        buttons.append([
            InlineKeyboardButton(
                ch["channel_name"],
                callback_data=f"select_{ch['channel_id']}"
            )
        ])

    user_states[user_id]["mode"] = "single"
    user_states[user_id]["selected_channels"] = []

    await message.reply(
        "📢 Select a channel:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ==============================
# 🔰 SEND MULTIPLE
# ==============================
@Client.on_message(filters.command("send more channel") & filters.private)
async def send_multi(client: Client, message: Message):

    user_id = message.from_user.id

    # 🔒 Admin check
    if user_id != Config.OWNER_ID and user_id not in Config.ALLOWED_USERS:
        return await message.reply("❌ Not authorized")

    if user_id not in user_states:
        return await message.reply("❌ No post found")

    channels = await db.get_channels()

    if not channels:
        return await message.reply("❌ No channels found")

    buttons = []
    for ch in channels:
        buttons.append([
            InlineKeyboardButton(
                ch["channel_name"],
                callback_data=f"multi_{ch['channel_id']}"
            )
        ])

    user_states[user_id]["mode"] = "multi"
    user_states[user_id]["selected_channels"] = []

    await message.reply(
        "📢 Select multiple channels:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ==============================
# 🔰 CHANNEL SELECT
# ==============================
@Client.on_callback_query()
async def channel_select(client: Client, query: CallbackQuery):

    user_id = query.from_user.id

    if user_id not in user_states:
        return await query.answer("❌ Session expired", show_alert=True)

    data = query.data

    # 🔹 SINGLE SELECT
    if data.startswith("select_"):
        channel_id = int(data.split("_")[1])

        user_states[user_id]["selected_channels"] = [channel_id]

        await query.message.reply("✅ Selected\n\nType /confirm to send")
        await query.answer()

    # 🔹 MULTI SELECT
    elif data.startswith("multi_"):
        channel_id = int(data.split("_")[1])

        selected = user_states[user_id]["selected_channels"]

        if channel_id in selected:
            selected.remove(channel_id)
        else:
            selected.append(channel_id)

        await query.answer(f"✅ Selected: {len(selected)}")


# ==============================
# 🔰 CONFIRM SEND
# ==============================
@Client.on_message(filters.command("confirm") & filters.private)
async def confirm_send(client: Client, message: Message):

    user_id = message.from_user.id

    if user_id not in user_states:
        return

    data = user_states[user_id]

    # 🔒 Ensure this confirm is for SEND only
    if data.get("mode") not in ["single", "multi"]:
        return

    selected = data.get("selected_channels")

    if not selected:
        return await message.reply("❌ No channel selected")

    post_message_id = data.get("post_message_id")
    episode_message_id = data.get("episode_message_id")

    if not post_message_id:
        return await message.reply("❌ No post data")

    sent = 0

    for channel_id in selected:
        try:
            # 🔹 Send main post (thumbnail/text)
            await client.copy_message(
                chat_id=channel_id,
                from_chat_id=message.chat.id,
                message_id=post_message_id
            )

            # 🔹 Send episode (actual content from storage)
            if episode_message_id:
                await client.copy_message(
                    chat_id=channel_id,
                    from_chat_id=Config.STORAGE_CHANNEL,
                    message_id=episode_message_id
                )

            sent += 1

        except Exception as e:
            await message.reply(f"❌ Failed: {channel_id}\n{e}")

    await message.reply(f"✅ Sent to {sent} channel(s)")

    # Reset state
    user_states.pop(user_id, None)
