import aiohttp
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import OWNER_ID, ALLOWED_USERS
from database import db

router = Router()

class ShortnerState(StatesGroup):
    waiting_url = State()
    waiting_api = State()

def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

async def make_shortlink(shortner, url):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(shortner["url"], json={"api": shortner["api"], "url": url}, timeout=10) as r:
                if r.status == 200:
                    data = await r.json()
                    return data.get("short_url") or data.get("shortened_url") or url
    except:
        pass
    return url

# New command: /adshort
@router.message(Command("adshort"))
async def add_shortner_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply("🔗 Send deskboard URL")
    await state.set_state(ShortnerState.waiting_url)

@router.message(ShortnerState.waiting_url)
async def shortner_url(message: Message, state: FSMContext):
    await state.update_data(url=message.text)
    await message.reply("🔑 Send API token")
    await state.set_state(ShortnerState.waiting_api)

@router.message(ShortnerState.waiting_api)
async def shortner_api(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.add_shortner(data["url"], message.text)
    await message.reply("✅ Shortner account added!")
    await state.clear()

# New command: /removeshot
@router.message(Command("removeshot"))
async def remove_shortner_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    shortners = await db.get_shortners()
    if not shortners:
        await message.reply("❌ No shortner accounts")
        return
    keyboard = []
    for s in shortners:
        keyboard.append([InlineKeyboardButton(text=s["url"], callback_data=f"rem_{s['_id']}")])
    await message.reply("Select account to remove:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("rem_"))
async def select_remove(callback: CallbackQuery, state: FSMContext):
    sid = callback.data.split("_")[1]
    await state.update_data(shortner_id=sid)
    await callback.message.reply("Type /delete to confirm")

@router.message(Command("delete"))
async def delete_shortner(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("shortner_id"):
        await db.remove_shortner(data["shortner_id"])
        await message.reply("✅ Shortner deleted")
        await state.clear()
    else:
        await message.reply("❌ No shortner selected")
