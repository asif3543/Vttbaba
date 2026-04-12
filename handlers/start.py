import asyncio
from bson import ObjectId
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import OWNER_ID, ALLOWED_USERS, BOT_USERNAME, STORAGE_CHANNEL_ID, EPISODE_CHANNEL_ID
from database import db
from .shortner import make_shortlink

router = Router()

def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

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

@router.message(Command("start"))
async def start_cmd(message: Message):
    try:
        uid = message.from_user.id
        
        if await db.is_banned(uid):
            await message.reply("❌ You are banned from using this bot.")
            return

        if message.text and " " in message.text:
            arg = message.text.split(" ", 1)[1].strip()

            if arg.startswith("ep_"):
                post_id = arg.replace("ep_", "")
                await handle_new_request(message, post_id)
                return
                
            elif arg.startswith("verify_"):
                token = arg.replace("verify_", "")
                post_id = await db.check_verify_token(uid, token)
                
                if post_id:
                    await handle_resolved_request(message, post_id)
                else:
                    await message.reply(
                        "❌ <b>Link is Expired or Already Used!</b>\n\n"
                        "⚠️ <i>For security reasons, shortner links can only be used ONCE. "
                        "You cannot reuse old links or share them to bypass.</i>\n\n"
                        "👉 Please go to the channel and click the button again to generate a new link.", 
                        parse_mode="HTML"
                    )
                return
                
            # FALLBACK FOR OLD LINKS CREATED YESTERDAY
            elif arg.startswith("res_"):
                parts = arg.replace("res_", "").rsplit("_", 1)
                if len(parts) == 2:
                    await handle_resolved_request(message, parts[0])
                else:
                    await message.reply("❌ <b>Broken Link!</b> Please generate a new one.", parse_mode="HTML")
                return

            else:
                await message.reply("⚠️ <b>Invalid Command!</b>", parse_mode="HTML")
                return

        if is_admin(uid):
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
        else:
            await message.reply("👋 <b>Welcome!</b>\nPlease use the buttons provided in our main channel to download episodes.", parse_mode="HTML")
            
    except Exception as e:
        print(f"Start Error: {e}")
        await message.reply("⚠️ Something went wrong! Please try again.")

async def handle_new_request(message: Message, post_id: str):
    uid = message.from_user.id
    
    if await db.is_premium(uid):
        await send_episode_direct(message, post_id)
        return

    not_joined = await get_unjoined_channels(message.bot, uid)
    if not_joined:
        await ask_for_fsub(message, not_joined, f"ep_{post_id}")
        return

    msg = await message.reply("⏳ Please wait, generating your secure link...")
    
    token = await db.create_verify_token(uid, post_id)
    
    clean_bot_username = BOT_USERNAME.replace("@", "") if BOT_USERNAME else "Hardsubsweety_bot"
    original_url = f"https://t.me/{clean_bot_username}?start=verify_{token}"
    
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

    if short_url == original_url and shortners:
        await msg.edit_text("❌ <b>Shortner API Error!</b>\nAdmin: Check API.", parse_mode="HTML")
        return

    await msg.edit_text(
        f"🔗 <b>Solve this shortner to get the episode:</b>\n\n"
        f"👉 {short_url}\n\n"
        f"⚠️ <i>After solving, you will directly receive the file here.</i>",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

async def handle_resolved_request(message: Message, post_id: str):
    uid = message.from_user.id
    not_joined = await get_unjoined_channels(message.bot, uid)
    if not_joined:
        token = await db.create_verify_token(uid, post_id)
        await ask_for_fsub(message, not_joined, f"verify_{token}")
        return
    await send_episode_direct(message, post_id)

async def send_episode_direct(message: Message, post_id: str):
    uid = message.from_user.id
    
    # Agar purani Batch Link hai ("05-15" format mein)
    if not ObjectId.is_valid(post_id) and "-" in post_id:
        try:
            start_str, end_str = post_id.split("-")
            batch_data = await db.get_batch_range(int(start_str), int(end_str))
            msg = await message.reply("📤 Sending your episodes in batch...")
            for ep_num in range(int(start_str), int(end_str) + 1):
                ep_info = batch_data.get(ep_num)
                if ep_info:
                    try:
                        await message.bot.copy_message(uid, ep_info["chat_id"] if ep_info["chat_id"] else STORAGE_CHANNEL_ID, ep_info["msg_id"])
                        await asyncio.sleep(0.5) 
                    except Exception: pass
            await msg.delete()
            return
        except Exception:
            pass

    # Nayi Unique ID wali Post
    post = await db.get_post_by_id(post_id)
    if not post:
        await message.reply("❌ Episode not found.")
        return
        
    if post.get("type") == "batch":
        episodes = post.get("episodes", [])
        msg = await message.reply("📤 Sending your episodes in batch...")
        for ep_info in episodes:
            try:
                await message.bot.copy_message(uid, ep_info.get("chat_id", STORAGE_CHANNEL_ID), ep_info.get("msg_id"))
                await asyncio.sleep(0.5) 
            except Exception as e:
                print(f"❌ Failed to send batch episode: {e}")
        await msg.delete()
    else:
        try:
            actual_video_id = post.get("episode_msg_id")
            old_storage_id = post.get("storage_msg_id")
            chat_id = post.get("episode_chat_id")
            
            if actual_video_id and chat_id:
                await message.bot.copy_message(uid, chat_id, actual_video_id)
            elif actual_video_id:
                await message.bot.copy_message(uid, EPISODE_CHANNEL_ID, actual_video_id)
            elif old_storage_id:
                await message.bot.copy_message(uid, STORAGE_CHANNEL_ID, old_storage_id)
            else:
                await message.reply("❌ Error: Video not found in database.")
        except Exception as e:
            await message.reply(f"❌ Failed to send episode: {e}")

async def ask_for_fsub(message: Message, not_joined: list, callback_payload: str):
    buttons = []
    for ch in not_joined:
        buttons.append([InlineKeyboardButton(text=f"📢 Join {ch['name']}", url=ch["link"])])
    
    clean_bot_username = BOT_USERNAME.replace("@", "") if BOT_USERNAME else "Hardsubsweety_bot"
    buttons.append([InlineKeyboardButton(text="✅ Try Again", url=f"https://t.me/{clean_bot_username}?start={callback_payload}")])
    
    await message.reply(
        "❌ <b>You must join our channels first to proceed!</b>\nJoin below and click Try Again.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
