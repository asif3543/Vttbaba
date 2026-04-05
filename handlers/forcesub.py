from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import OWNER_ID, ALLOWED_USERS
from database import db

router = Router()

# ---------- FSM States ----------
class FSubState(StatesGroup):
    waiting_forward = State()

def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

# ---------- /forcesub COMMAND ----------
@router.message(Command("forcesub"))
async def forcesub_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply("📢 Please forward any message from the channel you want to force subscribe.\n\nMake sure I am admin in that channel.")
    await state.set_state(FSubState.waiting_forward)

# ---------- RECEIVE FORWARDED MESSAGE ----------
@router.message(FSubState.waiting_forward)
async def fsub_forward_received(message: Message, state: FSMContext):
    if not message.forward_from_chat:
        await message.reply("❌ Please forward a message from a channel (not a user or group).")
        return

    chat = message.forward_from_chat
    channel_id = chat.id
    channel_name = chat.title or str(channel_id)
    # Try to get channel username or create invite link
    channel_link = f"https://t.me/{chat.username}" if chat.username else None

    if not channel_link:
        # Try to create an invite link (bot needs admin rights)
        try:
            invite_link = await message.bot.create_chat_invite_link(channel_id, member_limit=1)
            channel_link = invite_link.invite_link
        except:
            channel_link = f"https://t.me/c/{str(channel_id)[4:]}"  # fallback (may not work)

    # Optional: verify bot is admin
    try:
        bot_member = await message.bot.get_chat_member(channel_id, message.bot.id)
        if bot_member.status not in ["administrator", "creator"]:
            await message.reply("⚠️ I am not admin in that channel. Please make me admin and try again.")
            return
    except:
        await message.reply("❌ Cannot verify admin status. Make sure I am admin and the channel is public/accessible.")
        return

    # Save to database
    await db.add_fsub(channel_id, channel_name, channel_link)
    await message.reply(f"✅ Force-subscribe channel added successfully!\n\n📢 {channel_name}\n🔗 {channel_link}")
    await state.clear()

# ---------- OPTIONAL: LIST FORCE SUB CHANNELS ----------
@router.message(Command("fsub_list"))
async def list_fsub(message: Message):
    if not is_admin(message.from_user.id):
        return
    fsubs = await db.get_fsub()
    if not fsubs:
        await message.reply("📭 No force-subscribe channels configured.")
        return
    text = "📢 **Force Subscribe Channels:**\n\n"
    for idx, ch in enumerate(fsubs, 1):
        text += f"{idx}. {ch['name']}\n   {ch['link']}\n\n"
    await message.reply(text, parse_mode="Markdown")

# ---------- OPTIONAL: REMOVE FORCE SUB CHANNEL ----------
@router.message(Command("fsub_remove"))
async def remove_fsub_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    fsubs = await db.get_fsub()
    if not fsubs:
        await message.reply("No force-sub channels to remove.")
        return
    keyboard = []
    for ch in fsubs:
        keyboard.append([InlineKeyboardButton(text=ch['name'], callback_data=f"fsub_rem_{ch['_id']}")])
    await message.reply("Select channel to remove:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("fsub_rem_"))
async def confirm_remove_fsub(callback: CallbackQuery):
    ch_id = int(callback.data.split("_")[2])
    await db.fsub.delete_one({"_id": ch_id})
    await callback.message.reply("✅ Force-sub channel removed.")
    await callback.answer()
