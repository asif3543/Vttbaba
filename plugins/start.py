from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from plugins.helpers import generate_short_link, send_and_delete
from config import Config
from datetime import datetime, timezone
import asyncio

async def is_premium(user_id: int):
    user = await db.get_premium(user_id)
    if not user: return False
    expiry = datetime.fromisoformat(user["expiry_date"])
    if datetime.now(timezone.utc) > expiry:
        await db.remove_premium(user_id)
        return False
    return True

async def check_force_sub(client, user_id):
    channels = await db.get_force_channels()
    not_joined =[]
    for ch in channels:
        try:
            member = await client.get_chat_member(ch["channel_id"], user_id)
            if member.status in["left", "kicked", "restricted"]:
                not_joined.append(ch)
        except:
            not_joined.append(ch)
    return not_joined

@Client.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, message: Message):
    user_id = message.from_user.id

    if len(message.command) > 1:
        data = message.command[1]

        # STEP 1: Clicked from Channel Button
        if data.startswith("reqS_") or data.startswith("reqB_"):
            mode = "single" if data.startswith("reqS_") else "batch"
            post_id = data.split("_")[1]
            
            # Premium Check
            if await is_premium(user_id):
                return await process_files(client, message, mode, post_id)
            
            # Free User Check -> Generate Shortener
            bot_user = (await client.get_me()).username
            verify_url = f"https://t.me/{bot_user}?start=ver_{mode}_{post_id}_{user_id}"
            short_link = await generate_short_link(verify_url)
            return await message.reply(f"🔗 **Solve shortner:**\n{short_link}")

        # STEP 2: Returned from Shortener
        elif data.startswith("ver_"):
            parts = data.split("_")
            mode, post_id, target_user = parts[1], parts[2], int(parts[3])

            if user_id != target_user:
                return await message.reply("❌ Invalid Link")

            # Force Sub Check
            not_joined = await check_force_sub(client, user_id)
            if not_joined:
                btns = [[InlineKeyboardButton(ch["channel_name"], url=f"https://t.me/{ch['channel_name'].replace(' ', '')}")] for ch in not_joined]
                btns.append([InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{(await client.get_me()).username}?start={data}")])
                return await message.reply("🚫 **Join first:**", reply_markup=InlineKeyboardMarkup(btns))

            # Send files
            return await process_files(client, message, mode, post_id)

    await message.reply("Welcome message / Bot intro")

async def process_files(client, message, mode, post_id):
    await message.reply("Sending episode... Auto delete after 5 min ⏳")
    
    # We fetch by ILIKE because Supabase UUID removes hyphens in deep links
    if mode == "single":
        res = await db._request("GET", f"posts?id=ilike.*{post_id}*")
        if res: asyncio.create_task(send_and_delete(client, message.chat.id, Config.STORAGE_CHANNEL, int(res[0]["file_id"])))
    elif mode == "batch":
        res = await db._request("GET", f"batch_posts?id=ilike.*{post_id}*")
        if res:
            for msg_id in range(int(res[0]["start_message_id"]), int(res[0]["end_message_id"]) + 1):
                asyncio.create_task(send_and_delete(client, message.chat.id, Config.STORAGE_CHANNEL, msg_id))
                await asyncio.sleep(0.5)
