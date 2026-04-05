from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import OWNER_ID, ALLOWED_USERS
from database import db

router = Router()

class PremiumState(StatesGroup):
    waiting_id = State()

def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

@router.message(Command("addpri"))
async def add_premium_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply("Send user ID")
    await state.set_state(PremiumState.waiting_id)

@router.message(PremiumState.waiting_id)
async def premium_id(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
        expiry = await db.add_premium(uid)
        await message.reply(f"✅ Premium added to {uid}\nValid until {expiry.strftime('%Y-%m-%d')}\nType /huhu to confirm")
        await state.update_data(premium_uid=uid)
    except:
        await message.reply("❌ Invalid user ID")

@router.message(Command("huhu"))
async def confirm_premium(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("premium_uid"):
        await message.reply(f"✅ Premium confirmed for {data['premium_uid']} 🪄")
        await state.clear()
    else:
        await message.reply("❌ No pending premium. Use /addpri first")

@router.message(Command("removepri"))
async def remove_premium_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int(message.text.split()[1])
        await db.remove_premium(uid)
        await message.reply(f"✅ Removed premium and banned {uid}")
    except:
        await message.reply("❌ Usage: /removepri user_id")

@router.message(Command("showpremiumlist"))
async def show_premium_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    users = await db.get_premium_list()
    if not users:
        await message.reply("📭 No premium users")
        return
    text = "🌟 Premium Users:\n"
    for u in users:
        text += f"• `{u['_id']}` - expires {u['expiry'].strftime('%Y-%m-%d')}\n"
    await message.reply(text)
