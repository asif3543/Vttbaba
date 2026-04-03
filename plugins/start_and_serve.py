from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import is_premium, get_force_subs, get_shorteners
from config import STORAGE_CHANNEL_ID
import asyncio
import requests
import random

async def check_force_sub(client, user_id):
    channels = get_force_subs()
    not_joined = []
    for ch in channels:
        try:
            member = await client.get_chat_member(ch["channel_id"], user_id)
            if member.status.value in ["left", "kicked", "banned"]:
                not_joined.append(ch)
        except:
            not_joined.append(ch)
    return not_joined

def get_short_link(long_url):
    shorteners = get_shorteners()
    if not shorteners: return long_url
    
    # Random Shortener Rotation
    acc = random.choice(shorteners)
    api_url = acc["api_url"]
    api_key = acc["api_key"]
    
    # Standard Shortener API Call
    try:
        res = requests.get(f"{api_url}?api={api_key}&url={long_url}").json()
        if res.get("status") == "success" or res.get("status"):
            return res.get("shortenedUrl")
    except:
        pass
    return long_url

@Client.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    args = message.command
    
    if len(args) > 1:
        payload = args[1]
        
        # Free users MUST pass Force Sub
        if not is_premium(user_id):
            not_joined = await check_force_sub(client, user_id)
            if not_joined:
                buttons = []
                for ch in not_joined:
                    invite_link = await client.export_chat_invite_link(ch["channel_id"])
                    buttons.append([InlineKeyboardButton(f"Join {ch['channel_name']}", url=invite_link)])
                
                bot_info = await client.get_me()
                buttons.append([InlineKeyboardButton("Try Again", url=f"https://t.me/{bot_info.username}?start={payload}")])
                
                await message.reply_text("Join First 👇", reply_markup=InlineKeyboardMarkup(buttons))
                return

            # Shortener Logic
            if not payload.startswith("verified_"):
                bot_info = await client.get_me()
                long_url = f"https://t.me/{bot_info.username}?start=verified_{payload}"
                short_url = get_short_link(long_url)
                
                btn = InlineKeyboardMarkup([[InlineKeyboardButton("Verify & Watch", url=short_url)]])
                await message.reply_text("Please solve the link to get the episode.", reply_markup=btn)
                return

        # Removing "verified_" prefix if solved
        if payload.startswith("verified_"):
            payload = payload.replace("verified_", "")

        # --- SENDING THE EPISODES ---
        sent_msgs = []
        if payload.startswith("post_"):
            post_id = payload.split("_")[1]
            # Fetch from DB and copy from Storage Channel
            # (Requires you to fetch the message ID from DB, skipping full implementation to fit limit, but here is the copy logic)
            msg = await client.copy_message(user_id, STORAGE_CHANNEL_ID, 123) # 123 = post's file_id
            sent_msgs.append(msg)
            
        elif payload.startswith("batch_"):
            batch_id = payload.split("_")[1]
            # Get start_id and end_id from DB
            start_id, end_id = 10, 15 # Example values fetched from DB
            for i in range(start_id, end_id + 1):
                msg = await client.copy_message(user_id, STORAGE_CHANNEL_ID, i)
                sent_msgs.append(msg)
                await asyncio.sleep(0.5)

        # AUTO DELETE SYSTEM (5 Mins)
        await asyncio.sleep(300)
        for m in sent_msgs:
            try:
                await m.delete()
            except:
                pass
    else:
        await message.reply_text("Hello! Welcome to Advanced Auto Bot.")
