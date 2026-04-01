from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
import requests
import random
import database

async def check_force_sub(client, user_id):
    channels = database.get_force_subs()
    for ch in channels:
        try:
            await client.get_chat_member(ch, user_id)
        except UserNotParticipant:
            return False
        except Exception:
            pass
    return True

@Client.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, message: Message):
    text = message.text
    user_id = message.from_user.id
    
    if len(text.split()) > 1:
        param = text.split()[1]
        
        # 1. Force Sub Check
        is_joined = await check_force_sub(client, user_id)
        if not is_joined:
            channels = database.get_force_subs()
            buttons = []
            for i, ch in enumerate(channels):
                buttons.append([InlineKeyboardButton(f"Join Channel {i+1}", url=f"https://t.me/c/{str(ch).replace('-100', '')}/1")])
            buttons.append([InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{client.me.username}?start={param}")])
            await message.reply("❌ **Join First:** Aapko pehle channel join karna hoga fir try again pe click kare.", reply_markup=InlineKeyboardMarkup(buttons))
            return

        # 2. Link Clicked from Channel
        if param.startswith("post_"):
            post_id = param.replace("post_", "")
            
            # Premium Check
            if database.is_premium(user_id):
                await message.reply("👑 **Premium Member!** Direct episode sending...")
                await send_files(client, message.chat.id, post_id)
            else:
                # Free User - Send to Shortner
                shortners = database.get_shortners()
                if shortners:
                    selected = random.choice(shortners)
                    domain, api = selected['shortner_url'].split('|')
                    target_url = f"https://t.me/{client.me.username}?start=unlock_{post_id}"
                    
                    try:
                        api_url = f"https://{domain}/api?api={api}&url={target_url}"
                        res = requests.get(api_url).json()
                        short_url = res.get("shortenedUrl", res.get("shorturl"))
                        
                        btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔓 Open Short Link", url=short_url)]])
                        await message.reply("⚠️ **Shortner Solve Kare:** Har post ke saath new link hoga. Ise solve karke episode lijiye.", reply_markup=btn)
                    except Exception as e:
                        await message.reply("Shortner API Error. Please contact admin.")
                else:
                    await message.reply("No shortner account linked.")

        # 3. Unlock after Shortner
        elif param.startswith("unlock_"):
            post_id = param.replace("unlock_", "")
            await message.reply("✅ **Shortner Solved!** Ye raha aapka episode:")
            await send_files(client, message.chat.id, post_id)
    else:
        await message.reply("👋 Hello! Bot is working.")

async def send_files(client, chat_id, post_id):
    post = database.get_post(post_id)
    if not post:
        await client.send_message(chat_id, "Post not found!")
        return
    file_ids = post['link'].split(',')
    for fid in file_ids:
        await client.send_cached_media(chat_id, fid)
