from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from plugins.helpers import db, check_is_premium, get_short_link, get_force_sub_channels, check_group_access
from config import Config
import asyncio

async def auto_delete(messages):
    await asyncio.sleep(300) # 5 Minutes
    for msg in messages:
        try:
            await msg.delete()
        except: pass

@Client.on_message(filters.command("start") & filters.private)
async def start_logic(client, message: Message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) == 1:
        return await message.reply_text("👋 Welcome to Auto Post Bot!")

    param = args[1]
    
    # 🔰 FORCE SUB CHECK
    not_joined = []
    for ch in get_force_sub_channels():
        try:
            await client.get_chat_member(ch['channel_id'], user_id)
        except UserNotParticipant:
            not_joined.append(ch)
        except Exception: pass
        
    if not_joined:
        buttons = [[InlineKeyboardButton(f"Join {ch['channel_name']}", url=await client.export_chat_invite_link(ch['channel_id']))] for ch in not_joined]
        buttons.append([InlineKeyboardButton("Try Again", url=f"https://t.me/{client.me.username}?start={param}")])
        return await message.reply_text("⛔ You must join our channels!", reply_markup=InlineKeyboardMarkup(buttons))

    is_prem = check_is_premium(user_id)
    
    # 🔰 FREE USER SHORTNER LOGIC
    if not is_prem and not param.startswith("verify_"):
        short_url = await get_short_link(f"https://t.me/{client.me.username}?start=verify_{param}")
        return await message.reply_text(f"⚠️ **Free User Verification Required!**\n\n👉 {short_url}\n\n*Or Buy Premium.*", disable_web_page_preview=True)

    # Clean parameter if verified
    param = param.replace("verify_", "")

    # 🔰 SENDING FILE LOGIC
    warn = await message.reply_text("⏳ Sending file... (Will delete in 5 mins)")
    msgs_to_delete = [warn]

    try:
        if param.startswith("single_"):
            msg_id = db.table("posts").select("message_id").eq("id", param.split("_")[1]).execute().data[0]['message_id']
            msg = await client.copy_message(user_id, Config.STORAGE_CHANNEL, int(msg_id))
            msgs_to_delete.append(msg)

        elif param.startswith("batch_"):
            data = db.table("batch_posts").select("*").eq("id", param.split("_")[1]).execute().data[0]
            for i in range(int(data['start_message_id']), int(data['end_message_id']) + 1):
                msg = await client.copy_message(user_id, Config.STORAGE_CHANNEL, i)
                msgs_to_delete.append(msg)
                await asyncio.sleep(0.5)
                
    except Exception as e:
        await message.reply_text("❌ Error getting file!")
        print(e)
    
    # Start auto delete in background
    asyncio.create_task(auto_delete(msgs_to_delete))

# Ignore group messages unless it's the ALLOWED_GROUP
@Client.on_message(filters.group)
async def group_handler(client, message: Message):
    if not check_group_access(message.chat.id):
        return # Ignore msg from unauthorized groups
