from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from plugins.helpers import generate_short_link, send_and_delete
from config import Config
from datetime import datetime, timezone
import asyncio

async def is_premium(user_id: int):
    user = await db.get_premium(user_id)
    if not user:
        return False
    expiry = datetime.fromisoformat(user["expiry_date"])
    if datetime.now(timezone.utc) > expiry:
        await db.remove_premium(user_id)
        return False
    return True

async def check_force_sub(client, user_id):
    channels = await db.get_force_channels()
    not_joined = []
    for ch in channels:
        try:
            member = await client.get_chat_member(ch["channel_id"], user_id)
            if member.status in ["left", "kicked", "restricted"]:
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)
    return not_joined

@Client.on_message(filters.command("start") & filters.private)
async def start(client: Client, message: Message):
    user_id = message.from_user.id

    if len(message.command) > 1:
        data = message.command[1]

        # 🔰 Request Flow (Clicking from Channel) -> ?start=req_single_{id}
        if data.startswith("req_"):
            mode, post_id = data.split("_")[1], data.split("_")[2]
            
            if await is_premium(user_id):
                return await process_files(client, message, mode, post_id)
            
            # Free User -> Generate Shortner Link to Verify
            bot_username = (await client.get_me()).username
            verify_url = f"https://t.me/{bot_username}?start=ver_{mode}_{post_id}_{user_id}"
            short_link = await generate_short_link(verify_url)
            
            return await message.reply(f"🔗 **Solve this link to get episode:**\n{short_link}\n\n⏳ _Link expires quickly, solve it to watch!_")

        # 🔰 Verify Flow (After Solving Shortner) -> ?start=ver_single_{id}_{user_id}
        elif data.startswith("ver_"):
            parts = data.split("_")
            mode, post_id, target_user = parts[1], parts[2], int(parts[3])

            if user_id != target_user:
                return await message.reply("❌ This link is tied to another user! Generate your own.")

            # Check Force Sub after Shortener
            not_joined = await check_force_sub(client, user_id)
            if not_joined:
                buttons = [[InlineKeyboardButton(ch["channel_name"], url=f"https://t.me/{ch['channel_name'].replace(' ', '')}")] for ch in not_joined]
                buttons.append([InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{(await client.get_me()).username}?start={data}")])
                return await message.reply("🚫 **Join all channels first to receive the episode!**", reply_markup=InlineKeyboardMarkup(buttons))

            # Send Files
            return await process_files(client, message, mode, post_id)

    await message.reply("👋 Welcome to the Bot! I manage links securely.")

async def process_files(client, message, mode, post_id):
    await message.reply("✅ Processing! Your files will auto-delete in 5 minutes. ⏳")
    if mode == "single":
        post = await db.get_post(post_id)
        if post:
            asyncio.create_task(send_and_delete(client, message.chat.id, Config.STORAGE_CHANNEL, int(post["file_id"])))
    elif mode == "batch":
        post = await db.get_batch(post_id)
        if post:
            start_id, end_id = int(post["start_message_id"]), int(post["end_message_id"])
            for msg_id in range(start_id, end_id + 1):
                asyncio.create_task(send_and_delete(client, message.chat.id, Config.STORAGE_CHANNEL, msg_id))
                await asyncio.sleep(0.5)
