from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from plugins.helpers import db, check_is_premium, get_short_link, get_force_sub_channels
from config import Config
import asyncio

async def delete_after(messages, delay=300):
    await asyncio.sleep(delay)
    for msg in messages:
        try:
            await msg.delete()
        except: pass

async def check_fsub(client, user_id):
    channels = get_force_sub_channels()
    not_joined = []
    for ch in channels:
        try:
            await client.get_chat_member(ch['channel_id'], user_id)
        except UserNotParticipant:
            not_joined.append(ch)
        except Exception: pass
    return not_joined

@Client.on_message(filters.command("start") & filters.private)
async def start_logic(client, message: Message):
    user_id = message.from_user.id
    text = message.text.split()

    if len(text) == 1:
        return await message.reply_text(f"Welcome {message.from_user.first_name}! I am an Auto-Post Bot.")

    param = text[1]

    # Force Sub Check Pura Karo Pehle
    not_joined = await check_fsub(client, user_id)
    if not_joined:
        buttons = []
        for ch in not_joined:
            invite = await client.export_chat_invite_link(ch['channel_id'])
            buttons.append([InlineKeyboardButton(f"Join {ch['channel_name']}", url=invite)])
        buttons.append([InlineKeyboardButton("Try Again", url=f"https://t.me/{client.me.username}?start={param}")])
        return await message.reply_text("⛔ You must join our channels to get the file!", reply_markup=InlineKeyboardMarkup(buttons))

    # Premium VS Free logic
    is_prem = check_is_premium(user_id)
    
    # Verification handling (Shortner return link)
    if param.startswith("verify_"):
        file_param = param.replace("verify_", "")
        await send_file(client, message, file_param)
        return

    # Agar free user direct start parameter me aaya, usko shortner link do
    if not is_prem:
        bot_link = f"https://t.me/{client.me.username}?start=verify_{param}"
        short_url = await get_short_link(bot_link)
        await message.reply_text(
            "⚠️ **You are a FREE user.**\nPlease verify to get the file:\n\n"
            f"👉 {short_url}\n\n*Or contact admin to buy premium!*",
            disable_web_page_preview=True
        )
        return

    # Premium user (Ya verify ho chuka free user) direct file do
    await send_file(client, message, param)

async def send_file(client, message, param):
    user_id = message.from_user.id
    sent_messages = []
    
    warn_msg = await message.reply_text("⏳ Sending your file... (It will be deleted in 5 minutes)")
    sent_messages.append(warn_msg)

    try:
        if param.startswith("single_"):
            p_id = param.split("_")[1]
            res = db.table("posts").select("message_id").eq("id", p_id).execute()
            msg_id = res.data[0]['message_id']
            msg = await client.copy_message(user_id, Config.STORAGE_CHANNEL, int(msg_id))
            sent_messages.append(msg)

        elif param.startswith("batch_"):
            b_id = param.split("_")[1]
            res = db.table("batch_posts").select("start_message_id", "end_message_id").eq("id", b_id).execute()
            start_id = res.data[0]['start_message_id']
            end_id = res.data[0]['end_message_id']
            
            for i in range(int(start_id), int(end_id) + 1):
                msg = await client.copy_message(user_id, Config.STORAGE_CHANNEL, i)
                sent_messages.append(msg)
                await asyncio.sleep(0.5) # Spam limit bachane ke liye
    except Exception as e:
        await message.reply_text("❌ Error getting file! Maybe it was deleted.")
        print(e)
    
    # Start Auto Delete task (5 mins = 300 seconds)
    asyncio.create_task(delete_after(sent_messages, 300))
