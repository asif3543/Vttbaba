import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

# ================= CONFIG =================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEST_CHANNEL = int(os.getenv("DEST_CHANNEL", 0))
PORT = int(os.getenv("PORT", 8080))  # Render free-tier port

# ================= ACCESS CONTROL =================
OWNER_ID = 5344078567
ALLOWED_USERS = [5351848105]
ALLOWED_GROUPS = [-1003810374456]

def is_authorized(message: Message) -> bool:
    if not message.from_user: return False
    u_id = message.from_user.id
    if u_id == OWNER_ID or u_id in ALLOWED_USERS or message.chat.id in ALLOWED_GROUPS:
        return True
    return False

# ================= IN-MEMORY SETTINGS =================
user_settings = {}  # {user_id: {"thumb": file_id, "format": "video"}}
current_tasks = {}  # {user_id: asyncio.Task}

# ================= BOT INIT =================
app = Client("RenameBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ================= COMMAND HANDLERS =================
@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply_text(
        "<b>🔥 Rename Bot Online!</b>\n\n"
        "/tumb - Set Thumbnail\n"
        "/form - Choose Format\n"
        "/cancel - Cancel ongoing rename\n"
        "/refresh - Reset your settings\n"
        "Reply video/document with <code>/nn-li New Name</code> to rename and send to channel."
    )

# Set Thumbnail
@app.on_message(filters.command("tumb"))
async def set_tumb(client, message: Message):
    if not is_authorized(message): return
    await message.reply_text("📸 Send the image you want to set as thumbnail.")

@app.on_message(filters.photo)
async def save_tumb(client, message: Message):
    if not is_authorized(message): return
    user_id = message.from_user.id
    file_id = message.photo.file_id
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id]["thumb"] = file_id
    await message.reply_text("✅ Thumbnail saved!")

# Select Format
@app.on_message(filters.command("form"))
async def set_format(client, message: Message):
    if not is_authorized(message): return
    buttons = [
        [
            InlineKeyboardButton("Video (Media)", callback_data="set_vid"),
            InlineKeyboardButton("Document", callback_data="set_doc")
        ]
    ]
    await message.reply_text("Select format:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex("set_"))
async def update_format(client, query):
    user_id = query.from_user.id
    fmt = "video" if "vid" in query.data else "document"
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id]["format"] = fmt
    await query.answer()
    await query.message.edit(f"✅ Format set to: {fmt.capitalize()}")

# ================= CANCEL COMMAND =================
@app.on_message(filters.command("cancel"))
async def cancel_task(client, message: Message):
    user_id = message.from_user.id
    task = current_tasks.get(user_id)
    if task and not task.done():
        task.cancel()
        await message.reply("❌ Your current rename request has been cancelled.")
    else:
        await message.reply("⚠️ No active rename request found.")

# ================= REFRESH COMMAND =================
@app.on_message(filters.command("refresh"))
async def refresh_settings(client, message: Message):
    user_id = message.from_user.id
    if user_id in user_settings:
        user_settings[user_id] = {}
    await message.reply("🔄 Your settings have been reset. You can set new thumbnail and format now.")

# ================= MAIN RENAME LOGIC =================
@app.on_message(filters.command("nn-li") & filters.reply)
async def rename_handler(client, message: Message):
    if not is_authorized(message):
        return await message.reply("❌ You are not authorized.")

    if len(message.command) < 2:
        return await message.reply("❌ Usage: Reply with `/nn-li New Name`")

    replied = message.reply_to_message
    if not (replied.video or replied.document):
        return await message.reply("❌ Reply to a Video/Document.")

    new_name = message.text.split(None, 1)[1]
    user_id = message.from_user.id
    settings = user_settings.get(user_id, {})
    thumb_id = settings.get("thumb")
    fmt = settings.get("format", "video")

    status = await message.reply("⏳ Processing your request...")

    file_id = replied.video.file_id if replied.video else replied.document.file_id

    async def send_file():
        try:
            if fmt == "video":
                await client.send_video(
                    chat_id=DEST_CHANNEL,
                    video=file_id,
                    caption=f"**{new_name}**",
                    file_name=f"{new_name}.mp4",
                    thumb=thumb_id,
                    supports_streaming=True
                )
            else:
                await client.send_document(
                    chat_id=DEST_CHANNEL,
                    document=file_id,
                    caption=f"**{new_name}**",
                    file_name=f"{new_name}.mkv",
                    thumb=thumb_id
                )
            await status.edit(f"✅ Successfully sent '{new_name}' to channel.")
        except asyncio.CancelledError:
            await status.edit("❌ Rename request cancelled by user.")
        except Exception as e:
            await status.edit(f"❌ Error: {str(e)}")
        finally:
            current_tasks.pop(user_id, None)

    task = asyncio.create_task(send_file())
    current_tasks[user_id] = task

# ================= RUN BOT =================
async def main():
    await app.start()
    print("✅ Rename Bot is Online!")
    await app.idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
