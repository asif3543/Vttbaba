from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from database import db

user_states = {}

# ==============================
# 🔰 START POST
# ==============================
@Client.on_message(filters.command("post") & filters.private)
async def post_command(client: Client, message: Message):

    user_id = message.from_user.id

    if user_id != Config.OWNER_ID and user_id not in Config.ALLOWED_USERS:
        return await message.reply("❌ Not authorized")

    user_states[user_id] = {"step": "waiting_post"}

    await message.reply("📩 Send post (photo/video/document)")


# ==============================
# 🔰 RECEIVE POST MEDIA
# ==============================
@Client.on_message(
    (filters.photo | filters.video | filters.document) & filters.private
)
async def receive_post(client: Client, message: Message):

    user_id = message.from_user.id

    if user_id not in user_states:
        return

    if user_states[user_id]["step"] != "waiting_post":
        return

    user_states[user_id]["post_message_id"] = message.id
    user_states[user_id]["step"] = "choose_type"

    await message.reply(
        "✅ Post received\n\n"
        "Send:\n"
        "/link → Single Episode\n"
        "/batch → Batch Episodes"
    )


# ==============================
# 🔰 SINGLE LINK MODE
# ==============================
@Client.on_message(filters.command("link") & filters.private)
async def single_link(client: Client, message: Message):

    user_id = message.from_user.id

    if user_id not in user_states:
        return await message.reply("❌ Use /post first")

    user_states[user_id]["step"] = "waiting_episode"

    await message.reply("📥 Send episode (forward from storage channel)")


# ==============================
# 🔰 RECEIVE EPISODE
# ==============================
@Client.on_message(filters.private & filters.forwarded)
async def receive_episode(client: Client, message: Message):

    user_id = message.from_user.id

    if user_id not in user_states:
        return

    step = user_states[user_id].get("step")

    # 🔒 Must be forwarded
    if not message.forward_from_chat:
        return await message.reply("❌ Please forward from storage channel")

    # 🔒 Check storage channel
    if message.forward_from_chat.id != Config.STORAGE_CHANNEL:
        return await message.reply("❌ Wrong storage channel")

    # 🔹 SINGLE MODE
    if step == "waiting_episode":

        user_states[user_id]["episode_message_id"] = message.forward_from_message_id
        user_states[user_id]["step"] = "waiting_number"

        await message.reply("🔢 Enter episode number (e.g. 07)")

    # 🔹 BATCH MODE (next file use karega)
    elif step == "batch_collect":

        if "batch_list" not in user_states[user_id]:
            user_states[user_id]["batch_list"] = []

        user_states[user_id]["batch_list"].append(message.forward_from_message_id)

        await message.reply("➕ Send next episode or type /done")


# ==============================
# 🔰 ENTER EPISODE NUMBER
# ==============================
@Client.on_message(filters.text & filters.private)
async def episode_number(client: Client, message: Message):

    user_id = message.from_user.id

    if user_id not in user_states:
        return

    if user_states[user_id].get("step") != "waiting_number":
        return

    number = message.text.strip()

    if not number.isdigit():
        return await message.reply("❌ Send valid number (e.g. 07)")

    user_states[user_id]["episode_number"] = number
    user_states[user_id]["step"] = "confirm_post"

    await message.reply("✅ Type /confirm to finalize")


# ==============================
# 🔰 CONFIRM POST
# ==============================
@Client.on_message(filters.command("confirm") & filters.private)
async def confirm_post(client: Client, message: Message):

    user_id = message.from_user.id

    if user_id not in user_states:
        return

    data = user_states[user_id]

    if data.get("step") != "confirm_post":
        return

    post_id = await db.create_post(
        message_id=data["post_message_id"],
        episode_message_id=data["episode_message_id"],
        number=data["episode_number"]
    )

    bot_username = (await client.get_me()).username
    deep_link = f"https://t.me/{bot_username}?start=post_{post_id}"

    await message.reply(
        f"✅ Post Ready!\n\n"
        f"🔗 Link:\n{deep_link}\n\n"
        f"Use /send to publish"
    )

    user_states.pop(user_id)
