import hashlib
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import OWNER_ID, ALLOWED_USERS, BOT_USERNAME, STORAGE_CHANNEL_ID, SECRET_HASH
from database import db
from .shortner import make_shortlink

router = Router()

def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

# ================= HASH GENERATOR (BYPASS ROKNE KE LIYE) =================
def generate_hash(uid: int, episode: str) -> str:
    return hashlib.md5(f"{uid}_{episode}_{SECRET_HASH}".encode()).hexdigest()[:10]

# ================= FORCE SUB CHECK =================
async def get_unjoined_channels(bot, uid):
    fsubs = await db.get_fsub()
    not_joined = []
    for ch in fsubs:
        try:
            member = await bot.get_chat_member(ch["_id"], uid)
            if member.status not in ["member", "administrator", "creator"]:
                not_joined.append(ch)
        except:
            not_joined.append(ch)
    return not_joined

# ================= START COMMAND =================
@router.message(Command("start"))
async def start_cmd(message: Message):
    uid = message.from_user.id
    
    # Ban Check
    if await db.is_banned(uid):
        await message.reply("❌ You are banned from using this bot.")
        return

    # Deep Link Check
    if message.text and " " in message.text:
        arg = message.text.split(" ", 1)[1]

        # 1. First time click from Channel (ep_)
        if arg.startswith("ep_"):
            ep = arg.replace("ep_", "")
            await handle_new_request(message, ep)
            return
            
        # 2. After solving shortner (res_)
        elif arg.startswith("res_"):
            parts = arg.replace("res_", "").rsplit("_", 1)
            if len(parts) == 2:
                ep, received_hash = parts
                expected_hash = generate_hash(uid, ep)
                
                if received_hash == expected_hash:
                    await handle_resolved_request(message, ep)
                else:
                    await message.reply("❌ Invalid or expired link! Please click the button from the channel again.")
            return

    # Normal Start Command
    text = (
        "🤖 **Bot is alive!**\n\n"
        "📌 **Admin Commands:**\n"
        "/post - Upload new post\n"
        "/send - Send to single channel\n"
        "/sendmorechannel - Send to multiple channels\n"
        "/addchannel - Force add channel\n"
        "/adshort - Add shortner\n"
        "/removeshot - Remove shortner\n"
        "/addpri - Add premium\n"
        "/removepri - Remove premium & ban\n"
        "/forcesub - Add force subscribe channel\n"
    )
    await message.reply(text, parse_mode="Markdown")

# ================= NEW REQUEST (GIVE SHORTLINK) =================
async def handle_new_request(message: Message, ep: str):
    uid = message.from_user.id
    
    # Premium check
    if await db.is_premium(uid):
        print(f"⭐ Premium user {uid} accessing direct")
        await send_episode_direct(message, ep)
        return

    # Force sub check
    not_joined = await get_unjoined_channels(message.bot, uid)
    if not_joined:
        await ask_for_fsub(message, not_joined, f"ep_{ep}")
        return

    # Generate Shortner Flow
    msg = await message.reply("⏳ Please wait, generating your secure link...")
    hash_val = generate_hash(uid, ep)
    original_url = f"https://t.me/{BOT_USERNAME}?start=res_{ep}_{hash_val}"
    
    shortners = await db.get_shortners()
    short_url = original_url
    
    if shortners:
        import random
        random.shuffle(shortners)
        for s in shortners:
            temp = await make_shortlink(s, original_url)
            if temp and temp.startswith("http") and temp != original_url:
                short_url = temp
                break

    await msg.edit_text(
        f"🔗 **Solve this shortner to get the episode:**\n\n"
        f"👉 {short_url}\n\n"
        f"⚠️ *After solving, you will directly receive the file here.*",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

# ================= RESOLVED REQUEST (GIVE FILE) =================
async def handle_resolved_request(message: Message, ep: str):
    uid = message.from_user.id
    
    # Final check if user left channel while solving
    not_joined = await get_unjoined_channels(message.bot, uid)
    if not_joined:
        hash_val = generate_hash(uid, ep)
        await ask_for_fsub(message, not_joined, f"res_{ep}_{hash_val}")
        return
        
    await send_episode_direct(message, ep)

# ================= SEND EPISODE (SINGLE/BATCH) =================
async def send_episode_direct(message: Message, ep: str):
    uid = message.from_user.id
    
    if "-" in ep:
        # BATCH SEND
        try:
            start_str, end_str = ep.split("-")
            start_ep, end_ep = int(start_str), int(end_str)
            batch_data = await db.get_batch_range(start_ep, end_ep)
            
            if not batch_data:
                await message.reply("❌ No episodes found.")
                return
                
            await message.reply("📤 Sending your episodes...")
            for ep_num in range(start_ep, end_ep + 1):
                msg_id = batch_data.get(ep_num)
                if msg_id:
                    try:
                        await message.bot.copy_message(uid, STORAGE_CHANNEL_ID, msg_id)
                        await asyncio.sleep(0.5) # Flood wait rokne ke liye
                    except Exception as e:
                        print(f"❌ Failed to send {ep_num}: {e}")
                else:
                    await message.reply(f"⚠️ Episode {ep_num} missing.")
        except Exception as e:
            await message.reply("❌ Invalid batch range.")
    else:
        # SINGLE SEND
        post = await db.get_post_by_episode(ep)
        if not post:
            await message.reply("❌ Episode not found.")
            return
        try:
            await message.bot.copy_message(uid, STORAGE_CHANNEL_ID, post["storage_msg_id"])
        except Exception as e:
            await message.reply(f"❌ Failed to send episode: {e}")

# ================= FORCE SUB MENU =================
async def ask_for_fsub(message: Message, not_joined: list, callback_payload: str):
    buttons = []
    for ch in not_joined:
        buttons.append([InlineKeyboardButton(text=f"📢 Join {ch['name']}", url=ch["link"])])
    buttons.append([InlineKeyboardButton(text="✅ Try Again", url=f"https://t.me/{BOT_USERNAME}?start={callback_payload}")])
    
    await message.reply(
        "❌ **You must join our channels first!**\nJoin below and click Try Again.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown"
    )
