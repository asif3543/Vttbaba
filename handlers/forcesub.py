from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import OWNER_ID, ALLOWED_USERS
from database import db

router = Router()

class FSubState(StatesGroup):
    waiting_forward = State()

def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

@router.message(Command("forcesub"))
async def forcesub_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.reply("📢 Forward any message from the channel.\nMake sure bot is ADMIN there.")
    await state.set_state(FSubState.waiting_forward)

@router.message(FSubState.waiting_forward)
async def fsub_forward_received(message: Message, state: FSMContext):
    if not message.forward_from_chat:
        await message.reply("❌ Forward a message from a channel.")
        return

    chat = message.forward_from_chat
    channel_id = chat.id
    channel_name = chat.title or str(channel_id)

    try:
        bot_member = await message.bot.get_chat_member(channel_id, message.bot.id)
        if bot_member.status not in ["administrator", "creator"]:
            await message.reply("⚠️ Bot must be ADMIN first.")
            return
    except:
        await message.reply("❌ Cannot access channel.")
        return

    channel_link = None
    if chat.username:
        channel_link = f"https://t.me/{chat.username}"
    else:
        try:
            invite = await message.bot.create_chat_invite_link(channel_id)
            channel_link = invite.invite_link
        except:
            channel_link = None

    if not channel_link:
        await message.reply("❌ Failed to create invite link.")
        return

    await db.add_fsub(channel_id, channel_name, channel_link)
    await db.add_channel(channel_id, channel_name)

    await message.reply(f"✅ Channel added successfully!\n\n📢 {channel_name}\n🔗 {channel_link}")
    await state.clear()

@router.message(Command("fsub_list"))
async def list_fsub(message: Message):
    if not is_admin(message.from_user.id): return
    fsubs = await db.get_fsub()
    if not fsubs:
        await message.reply("📭 No force-sub channels.")
        return
    text = "📢 **Force Subscribe Channels:**\n\n"
    for idx, ch in enumerate(fsubs, 1):
        text += f"{idx}. {ch['name']}\n{ch['link']}\n\n"
    await message.reply(text, parse_mode="Markdown")

@router.message(Command("fsub_remove"))
async def remove_fsub_cmd(message: Message):
    if not is_admin(message.from_user.id): return
    fsubs = await db.get_fsub()
    if not fsubs:
        await message.reply("❌ No channels found.")
        return
    keyboard = []
    for ch in fsubs:
        keyboard.append([InlineKeyboardButton(text=ch["name"], callback_data=f"fsub_rem_{ch['_id']}")])
    await message.reply("Select channel to remove:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("fsub_rem_"))
async def confirm_remove_fsub(callback: CallbackQuery):
    ch_id = int(callback.data.split("_")[2])
    await db.fsub.delete_one({"_id": ch_id})
    await callback.message.edit_text("✅ Channel removed from Force Sub.")
