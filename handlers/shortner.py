import aiohttp
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from urllib.parse import quote
from bson import ObjectId
from config import OWNER_ID, ALLOWED_USERS
from database import db

router = Router()

class ShortnerState(StatesGroup):
    waiting_url = State()
    waiting_api = State()

def is_admin(uid): return uid == OWNER_ID or uid in ALLOWED_USERS

async def make_shortlink(shortner: dict, original_url: str) -> str:
    api_url = shortner.get("url")
    api_key = shortner.get("api")
    if not api_url or not api_key: return original_url

    encoded_url = quote(original_url, safe="")
    try:
        async with aiohttp.ClientSession() as session:
            # 99% of shortners use this GET method
            get_url = f"{api_url}?api={api_key}&url={encoded_url}"
            async with session.get(get_url, timeout=10) as resp:
                data = await resp.json(content_type=None)
                if data and data.get("status") == "success":
                    return data.get("shortenedUrl", original_url)
    except Exception as e:
        print(f"❌ Shortner Error: {e}")
    return original_url

# ... (rest of your add/remove shortner commands stay the same as original)
@router.message(Command("adshort"))
async def add_shortner_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.reply("🔗 Send API endpoint URL (e.g., https://shrinkme.io/api)")
    await state.set_state(ShortnerState.waiting_url)

@router.message(ShortnerState.waiting_url)
async def shortner_url(message: Message, state: FSMContext):
    url = message.text.strip()
    await state.update_data(url=url)
    await message.reply("🔑 Send API token/key")
    await state.set_state(ShortnerState.waiting_api)

@router.message(ShortnerState.waiting_api)
async def shortner_api(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.add_shortner(data["url"], message.text.strip())
    await message.reply("✅ Shortner added successfully!")
    await state.clear()

@router.message(Command("removeshot"))
async def remove_shortner_cmd(message: Message):
    if not is_admin(message.from_user.id): return
    shortners = await db.get_shortners()
    if not shortners:
        await message.reply("❌ No shortners found.")
        return
    kb = [[InlineKeyboardButton(text=s["url"], callback_data=f"rem_{s['_id']}")]] for s in shortners]
    await message.reply("Select shortner to remove:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("rem_"))
async def select_remove(callback: CallbackQuery, state: FSMContext):
    sid = callback.data.split("_")[1]
    await db.remove_shortner(ObjectId(sid))
    await callback.message.edit_text("✅ Shortner account deleted successfully.")
