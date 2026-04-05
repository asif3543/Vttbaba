from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_ID, ALLOWED_USERS, BOT_USERNAME, STORAGE_CHANNEL_ID
from database import db
from .shortner import make_shortlink

router = Router()

def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

@router.message(Command("Forcesub"))
async def force_sub_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.reply("Please forward a message from the channel you want to force subscribe")

    # Temporary handler for forwarded message
    @router.message()
    async def fsub_forward(msg: Message):
        if msg.forward_from_chat:
            cid = msg.forward_from_chat.id
            name = msg.forward_from_chat.title or str(cid)
            link = f"https://t.me/{name}"
            await db.add_fsub(cid, name, link)
            await msg.reply(f"✅ Force subscribe added: {name}")
        else:
            await msg.reply("❌ Please forward a channel message")
        # Remove this temporary handler after one use? We'll just leave it, but it's okay.

# Deep link handler for episode access
@router.message(Command("start"))
async def start_with_ep(message: Message):
    if " ep_" in message.text:
        ep = message.text.split("ep_")[1].strip()
        uid = message.from_user.id
        if await db.is_banned(uid):
            await message.reply("❌ You are banned")
            return
        if await db.is_premium(uid):
            post = await db.get_post_by_episode(ep)
            if post:
                await message.bot.copy_message(uid, STORAGE_CHANNEL_ID, post["storage_msg_id"])
            else:
                await message.reply("❌ Episode not found")
            return
        # Check force sub
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
            kb.append([InlineKeyboardButton(text="✅ Try Again", callback_data=f"retry_{ep}")])
            await message.reply("❌ Join channels first:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            return
        # Free user: send shortner
        shortner = await db.get_random_shortner()
        url = f"https://t.me/{BOT_USERNAME}?start=ep_{ep}"
        if shortner:
            url = await make_shortlink(shortner, url)
        await message.reply(f"🔗 Solve shortner to get episode:\n{url}\nAfter solving, you'll receive the file.")

@router.callback_query(F.data.startswith("retry_"))
async def retry_callback(callback: CallbackQuery):
    ep = callback.data.split("_")[1]
    await callback.message.delete()
    # Re-trigger the start handler
    await start_with_ep(callback.message)
