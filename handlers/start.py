from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_ID, ALLOWED_USERS, BOT_USERNAME, STORAGE_CHANNEL_ID
from database import db
from .shortner import make_shortlink

router = Router()

def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

# ------------------- NORMAL START -------------------
@router.message(Command("start"))
async def start_cmd(message: Message):
    # Check if it's a deep link (episode request)
    if " " in message.text:
        arg = message.text.split(" ", 1)[1]
        if arg.startswith("ep_"):
            await process_episode_request(message, arg[3:])  # remove "ep_"
            return

    # Normal welcome message
    text = (
        "🤖 Bot is alive!\n\n"
        "📌 **Admin Commands:**\n"
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
    await message.reply(text, parse_mode="Markdown")

# ------------------- DEEP LINK HANDLER -------------------
async def process_episode_request(message: Message, episode_param: str):
    uid = message.from_user.id

    # 1. Banned check
    if await db.is_banned(uid):
        await message.reply("❌ You are banned from using this bot.")
        return

    # 2. Premium check (direct send without shortner)
    if await db.is_premium(uid):
        await send_episode_direct(message, episode_param)
        return

    # 3. Force subscribe check (only for non-premium)
    fsubs = await db.get_fsub()
    not_joined = []
    for ch in fsubs:
        try:
            member = await message.bot.get_chat_member(ch["_id"], uid)
            if member.status not in ["member", "administrator", "creator"]:
                not_joined.append(ch)
        except:
            not_joined.append(ch)

    if not_joined:
        kb = []
        for ch in not_joined:
            kb.append([InlineKeyboardButton(text=f"📢 Join {ch['name']}", url=ch["link"])])
        kb.append([InlineKeyboardButton(text="✅ Try Again", callback_data=f"retry_{episode_param}")])
        await message.reply(
            "❌ **You must join the following channels first:**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
            parse_mode="Markdown"
        )
        return

    # 4. Normal user: generate shortner link
    shortners = await db.get_shortners()
    original_url = f"https://t.me/{BOT_USERNAME}?start=ep_{episode_param}"
    short_url = original_url

    if shortners:
        import random
        random.shuffle(shortners)
        for s in shortners:
            try:
                temp_url = await make_shortlink(s, original_url)
                if temp_url and temp_url != original_url:
                    short_url = temp_url
                    break
            except:
                continue

    await message.reply(
        f"🔗 **Solve this shortner to get your episode:**\n{short_url}\n\n"
        "After solving, you will automatically receive the file.",
        parse_mode="Markdown"
    )

# ------------------- DIRECT EPISODE SENDING (PREMIUM) -------------------
async def send_episode_direct(message: Message, episode_param: str):
    """Send episode(s) directly without shortner"""
    uid = message.from_user.id

    # Check if it's a range (e.g., "05-15")
    if "-" in episode_param:
        try:
            start_str, end_str = episode_param.split("-")
            start = int(start_str)
            end = int(end_str)
            # Retrieve batch episodes from database
            batch_data = await db.get_batch_range(start, end)
            if not batch_data:
                await message.reply("❌ No episodes found in this range.")
                return
            # Send each episode one by one
            for ep_num in range(start, end + 1):
                ep_msg_id = batch_data.get(str(ep_num))
                if ep_msg_id:
                    try:
                        await message.bot.copy_message(uid, STORAGE_CHANNEL_ID, ep_msg_id)
                    except Exception as e:
                        print(f"Failed to send episode {ep_num}: {e}")
                else:
                    await message.reply(f"⚠️ Episode {ep_num} not found.")
        except:
            await message.reply("❌ Invalid episode range format.")
    else:
        # Single episode
        post = await db.get_post_by_episode(episode_param)
        if not post:
            await message.reply("❌ Episode not found.")
            return

        # For single episode, post contains storage_msg_id
        try:
            await message.bot.copy_message(uid, STORAGE_CHANNEL_ID, post["storage_msg_id"])
        except Exception as e:
            await message.reply(f"❌ Failed to send episode: {e}")

# ------------------- RETRY CALLBACK (AFTER JOINING FORCE-SUB) -------------------
@router.callback_query(F.data.startswith("retry_"))
async def retry_callback(callback: CallbackQuery):
    episode_param = callback.data.split("_", 1)[1]
    await callback.message.delete()
    # Re-process the episode request
    await process_episode_request(callback.message, episode_param)
    await callback.answer()
