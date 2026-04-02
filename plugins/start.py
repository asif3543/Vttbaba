from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from database import db, get_short_link
from config import Config
import asyncio

async def auto_delete(msgs):
    await asyncio.sleep(300) # 5 Min
    for m in msgs:
        try: await m.delete()
        except: pass

@Client.on_message(filters.command("start") & filters.private)
async def start_logic(client, message: Message):
    args = message.text.split()
    if len(args) == 1:
        return await message.reply_text("Welcome to File Store Bot!")

    param = args[1]
    user_id = message.from_user.id

    # 🔰 FORCE SUB CHECK
    f_subs = db.table("force_sub_channels").select("*").execute().data
    not_joined = []
    for ch in f_subs:
        try: await client.get_chat_member(ch['channel_id'], user_id)
        except UserNotParticipant: not_joined.append(ch)
        except Exception: pass
        
    if not_joined:
        btns = [[InlineKeyboardButton(f"Join {c['channel_name']}", url=await client.export_chat_invite_link(c['channel_id']))] for c in not_joined]
        btns.append([InlineKeyboardButton("Try Again", url=f"https://t.me/{client.me.username}?start={param}")])
        return await message.reply_text("⛔ Join channels first!", reply_markup=InlineKeyboardMarkup(btns))

    # 🔰 PREMIUM CHECK
    is_prem = bool(db.table("premium_users").select("*").eq("user_id", user_id).execute().data)

    # 🔰 SHORTNER CHECK (Free users ko pehle verify karwana)
    if not is_prem and not param.startswith("verify_"):
        bot_link = f"https://t.me/{client.me.username}?start=verify_{param}"
        short_url = get_short_link(bot_link)
        return await message.reply_text(f"⚠️ **Free User!** Please verify:\n👉 {short_url}\n\n*Or buy premium.*", disable_web_page_preview=True)

    param = param.replace("verify_", "")

    # 🔰 FILE DELIVERY
    warn = await message.reply_text("⏳ Sending episode(s)... (Will Auto-Delete in 5 minutes)")
    msgs_to_delete = [warn]

    try:
        if param.startswith("single_"):
            p_id = param.split("_")[1]
            data = db.table("posts").select("message_id").eq("id", p_id).execute().data[0]
            msg = await client.copy_message(user_id, Config.STORAGE_CHANNEL, int(data["message_id"]))
            msgs_to_delete.append(msg)

        elif param.startswith("batch_"):
            p_id = param.split("_")[1]
            data = db.table("batch_posts").select("*").eq("id", p_id).execute().data[0]
            start_id, end_id = int(data["start_message_id"]), int(data["end_message_id"])
            for i in range(start_id, end_id + 1):
                msg = await client.copy_message(user_id, Config.STORAGE_CHANNEL, i)
                msgs_to_delete.append(msg)
                await asyncio.sleep(0.5)

    except Exception as e:
        await message.reply_text("❌ File not found! Contact Admin.")
        
    asyncio.create_task(auto_delete(msgs_to_delete))

# Ignore messages in unauthorized groups
@Client.on_message(filters.group)
async def group_handler(client, message):
    if message.chat.id != Config.ALLOWED_GROUP: pass
