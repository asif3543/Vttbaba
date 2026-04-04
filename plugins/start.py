from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import is_premium, get_force_subs, get_shorteners, get_post, get_batch
from config import STORAGE_CHANNEL_ID
import asyncio, aiohttp, random

async def check_force_sub(client, user_id):
    not_joined =[]
    for ch in await get_force_subs():
        try:
            member = await client.get_chat_member(ch["channel_id"], user_id)
            if member.status.value in ["left", "kicked", "banned"]: not_joined.append(ch)
        except: not_joined.append(ch)
    return not_joined

async def get_short_link(long_url):
    shorteners = await get_shorteners()
    if not shorteners: return long_url
    acc = random.choice(shorteners)
    try:
        url = f"{acc['api_url']}?api={acc['api_key']}&url={long_url}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as res:
                data = await res.json()
                if "shortenedUrl" in data: return data["shortenedUrl"]
                if "short" in data: return data["short"]
    except: pass
    return long_url

@Client.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    args = message.command
    
    if len(args) > 1:
        payload = args[1]
        
        # 1. Force Sub Check
        if not await is_premium(user_id):
            not_joined = await check_force_sub(client, user_id)
            if not_joined:
                btns =[]
                for ch in not_joined:
                    link = f"https://t.me/{ch['channel_name'].replace(' ', '')}"
                    btns.append([InlineKeyboardButton(f"Join {ch['channel_name']}", url=link)])
                bot_info = await client.get_me()
                btns.append([InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{bot_info.username}?start={payload}")])
                return await message.reply_text("Join first", reply_markup=InlineKeyboardMarkup(btns))

            # 2. Shortener Check
            if not payload.startswith("ver_"):
                bot_info = await client.get_me()
                long_url = f"https://t.me/{bot_info.username}?start=ver_{payload}"
                short_url = await get_short_link(long_url)
                btn = InlineKeyboardMarkup([[InlineKeyboardButton("Verify & Watch", url=short_url)]])
                return await message.reply_text("Please solve the link to get the episode.", reply_markup=btn)

        if payload.startswith("ver_"): payload = payload.replace("ver_", "")

        # 3. SEND EPISODES
        sent_msgs =[]
        await message.reply_text("Sending episode... Auto delete after 5 min ⏳")
        
        if payload.startswith("post_"):
            post_id = payload.split("_")[1]
            post = await get_post(post_id)
            if post:
                msg = await client.copy_message(user_id, STORAGE_CHANNEL_ID, int(post["file_id"]))
                sent_msgs.append(msg)
                
        elif payload.startswith("batch_"):
            batch_id = payload.split("_")[1]
            batch = await get_batch(batch_id)
            if batch:
                for i in range(int(batch["start_message_id"]), int(batch["end_message_id"]) + 1):
                    msg = await client.copy_message(user_id, STORAGE_CHANNEL_ID, i)
                    sent_msgs.append(msg)
                    await asyncio.sleep(0.5)

        # 4. AUTO DELETE
        await asyncio.sleep(300)
        for m in sent_msgs:
            try: await m.delete()
            except: pass
    else:
        await message.reply_text("Welcome to Advanced File Store Bot!")
