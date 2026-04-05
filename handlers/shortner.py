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

# ✅ FIXED FUNCTION
async def make_shortlink(shortner, url):
    try:
        async with aiohttp.ClientSession() as s:

            # 👉 First try with form-data (most APIs support this)
            async with s.post(
                shortner["url"],
                data={"api": shortner["api"], "url": url},
                timeout=10
            ) as r:

                if r.status == 200:
                    data = await r.json()
                    print("Shortner Response:", data)

                    return (
                        data.get("short_url")
                        or data.get("shortened_url")
                        or data.get("link")
                        or data.get("result")
                        or data.get("short")
                        or url
                    )

            # 👉 Fallback: try JSON if above fails
            async with s.post(
                shortner["url"],
                json={"api": shortner["api"], "url": url},
                timeout=10
            ) as r:

                if r.status == 200:
                    data = await r.json()
                    print("Shortner JSON Response:", data)

                    return (
                        data.get("short_url")
                        or data.get("shortened_url")
                        or data.get("link")
                        or data.get("result")
                        or data.get("short")
                        or url
                    )

    except Exception as e:
        print("Shortner Error:", e)

    return url


@router.message(Command("adshort"))
async def add_shortner_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply("🔗 Send API endpoint URL (not dashboard)")
    await state.set_state(ShortnerState.waiting_url)


@router.message(ShortnerState.waiting_url)
async def shortner_url(message: Message, state: FSMContext):
    await state.update_data(url=message.text.strip())
    await message.reply("🔑 Send API token")
    await state.set_state(ShortnerState.waiting_api)


@router.message(ShortnerState.waiting_api)
async def shortner_api(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.add_shortner(data["url"], message.text.strip())
    await message.reply("✅ Shortner account added!")
    await state.clear()


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
        keyboard.append([
            InlineKeyboardButton(
                text=s["url"],
                callback_data=f"rem_{s['_id']}"
            )
        ])

    await message.reply(
        "Select account to remove:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


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
