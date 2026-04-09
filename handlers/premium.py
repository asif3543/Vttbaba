from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import OWNER_ID, ALLOWED_USERS
from database import db

router = Router()

class PremiumState(StatesGroup):
    waiting_id = State()
    waiting_confirm = State()

def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

@router.message(Command("addpri"))
async def add_premium_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.reply("💰 Send Telegram user ID to add premium (Valid for 28 Days).\nExample: `585447854`", parse_mode="Markdown")
    await state.set_state(PremiumState.waiting_id)

@router.message(PremiumState.waiting_id)
async def premium_id_received(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.reply("❌ Invalid ID. Please send a numeric user ID.")
        return
        
    await state.update_data(premium_uid=uid)
    await state.set_state(PremiumState.waiting_confirm)
    await message.reply(f"✅ User ID `{uid}` will get premium for **28 Days**.\nType `/huhu` to confirm.", parse_mode="Markdown")

@router.message(Command("huhu"))
async def confirm_premium(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    uid = data.get("premium_uid")
    
    if not uid:
        await message.reply("❌ No pending premium. Use `/addpri` first.")
        return
        
    expiry = await db.add_premium(uid)
    await message.reply(f"✅ Premium added to `{uid}` 🪄\n📅 Valid until `{expiry.strftime('%Y-%m-%d')} (UTC)`", parse_mode="Markdown")
    await state.clear()

@router.message(Command("removepri"))
async def remove_premium_cmd(message: Message):
    if not is_admin(message.from_user.id): return
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply("❌ Usage: `/removepri user_id`\nExample: `/removepri 585447854`", parse_mode="Markdown")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await message.reply("❌ Invalid user ID.")
        return
    await db.remove_premium(uid)
    await message.reply(f"✅ Removed premium and banned `{uid}`.", parse_mode="Markdown")

@router.message(Command("showpremiumlist"))
async def show_premium_list(message: Message):
    if not is_admin(message.from_user.id): return
    users = await db.get_premium_list()
    if not users:
        await message.reply("📭 No active premium users.")
        return
    text = "🌟 **Active Premium Users:**\n\n"
    for u in users:
        expiry_str = u['expiry'].strftime('%Y-%m-%d')
        text += f"• `{u['_id']}` – expires on {expiry_str}\n"
    await message.reply(text, parse_mode="Markdown")
