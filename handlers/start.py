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
    # Single ('10') aur Batch ('05-15') dono ke liye same hash kaam karega
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
    
    # 1. Ban Check
    if await db.is_banned(uid):
        await message.reply("❌ You are banned from using this bot.")
        return

    # 2. Deep Link Check (Jab user button ya shortner se aaye)
    if message.text and " " in message.text:
        arg = message.text.split(" ", 1)[1].strip()

        # STAGE 1: Naya link (Channel button se click kiya)
        if arg.startswith("ep_"):
            ep = arg.replace("ep_", "")
            await handle_new_request(message, ep)
            return
            
        # STAGE 2: Resolved link (Shortner solve karke wapas aaya)
        elif arg.startswith("res_"):
            # rsplit se batch (05-15) aur hash dono properly alag honge
            parts = arg.replace("res_", "").rsplit("_", 1)
            if len(parts) == 2:
                ep, received_hash = parts
                expected_hash = generate_hash(uid, ep)
                
                if received_hash == expected_hash:
                    await handle_resolved_request(message, ep)
                else:
                    await message.reply("❌ <b>Invalid or expired link!</b>\nPlease click the button from the channel again to generate a new link.", parse_mode="HTML")
            else:
                await message.reply("❌ <b>Broken Link!</b>", parse_mode="HTML")
            return  # Ye return pehle break ho raha tha isliye menu show ho raha tha

    # 3. Normal Start Command (Sirf tab chalega jab koi param na ho)
    text = (
        "🤖 <b>Bot is alive!</b>\n\n"
        "📌 <b>Admin Commands:</b>\n"
        "/post - Upload new post (single or batch)\n"
        "/send - Send to single channel\n"
        "/sendmorechannel - Send to multiple channels\n"
        "/confirm - Confirm send action\n"
        "/hmm - Confirm post creation\n"
        "/adshort - Add shortner account\n"
        "/removeshot - Remove shortner account\n"
        "/delete - Delete selected shortner\n"
        "/addpri - Add premium user (28 days)\n"
        "/removepri - Remove premium user\n"
        "/showpremiumlist - Show premium users\n"
        "/forcesub - Add force subscribe channel\n"
    )
    await message.reply(text, parse_mode="HTML")

# ================= NEW REQUEST (GENERATE SHORTLINK) =================
async def handle_new_request(message: Message, ep: str):
    uid = message.from_user.id
    
    # Premium user direct bypass
    if await db.is_premium(uid):
        await send_episode_direct(message, ep)
        return

    # Force sub check before link generation
    not_joined = await get_unjoined_channels(message.bot, uid)
    if not_joined:
        await ask_for_fsub(message, not_joined, f"ep_{ep}")
        return

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

    # Agar Shortner Fail Hua Toh Error Dega, Direct Episode Nahi!
    if short_url == original_url and shortners:
        await msg.edit_text(
            "❌ <b>Shortner API Error!</b>\n\n"
            "⚠️ Bot could not generate the link.\n"
            "👉 Admin: Please check your shortner URL and API token.",
            parse_mode="HTML"
        )
        return

    await msg.edit_text(
        f"🔗 <b>Solve this shortner to get the episode:</b>\n\n"
        f"👉 {short_url}\n\n"
        f"⚠️ <i>After solving, you will directly receive the file here.</i>",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

# ================= RESOLVED REQUEST (GIVE FILE) =================
async def handle_resolved_request(message: Message, ep: str):
    uid = message.from_user.id
    
    # Final force sub check (in case user left the channel while solving)
    not_joined = await get_unjoined_channels(message.bot, uid)
    if not_joined:
        hash_val = generate_hash(uid, ep)
        await ask_for_fsub(message, not_joined, f"res_{ep}_{hash_val}")
        return
        
    # Episode deliver karega
    await send_episode_direct(message, ep)

# ================= SEND EPISODE (SINGLE/BATCH) =================
async def send_episode_direct(message: Message, ep: str):
    uid = message.from_user.id
    
    if "-" in ep:
        # ======= BATCH LINK =======
        try:
            start_str, end_str = ep.split("-")
            start_ep, end_ep = int(start_str), int(end_str)
            batch_data = await db.get_batch_range(start_ep, end_ep)
            
            if not batch_data:
                await message.reply("❌ No episodes found in database.")
                return
                
            msg = await message.reply("📤 Sending your episodes in batch...")
            for ep_num in range(start_ep, end_ep + 1):
                msg_id = batch_data.get(ep_num)
                if msg_id:
                    try:
                        await message.bot.copy_message(uid, STORAGE_CHANNEL_ID, msg_id)
                        await asyncio.sleep(0.5)  # Telegram API flood limit block se bachne ke liye
                    except Exception as e:
                        print(f"❌ Failed to send episode {ep_num}: {e}")
                else:
                    await message.reply(f"⚠️ Episode {ep_num} is missing from database.")
            
            await msg.delete() # 'Sending your episodes' message delete kar dega
            
        except Exception as e:
            await message.reply("❌ Invalid batch range format.")
    else:
        # ======= SINGLE LINK =======
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
        "❌ <b>You must join our channels first to proceed!</b>\nJoin below and click Try Again.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
