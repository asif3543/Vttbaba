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

def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

# ---------- MAIN SHORTNER FUNCTION (FIXED) ----------
async def make_shortlink(shortner: dict, original_url: str) -> str:
    """
    Tries to create a short link using the given shortner account.
    Returns short URL if successful, else returns original_url.
    """
    api_url = shortner.get("url")
    api_key = shortner.get("api")
    
    if not api_url or not api_key:
        return original_url

    print(f"🔗 Trying Shortner: {api_url}")
    print(f"🔗 Original URL: {original_url}")

    # URL encode the original URL
    encoded_url = quote(original_url, safe="")
    timeout_obj = aiohttp.ClientTimeout(total=15)

    try:
        async with aiohttp.ClientSession() as session:
            # Method 1: GET request (Adlinkfly & most common)
            get_url = f"{api_url}?api={api_key}&url={encoded_url}"
            async with session.get(get_url, timeout=timeout_obj) as resp:
                if resp.status == 200:
                    try:
                        data = await resp.json()
                    except:
                        text = await resp.text()
                        if text.startswith("http"):
                            print(f"✅ Short URL Generated: {text}")
                            return text.strip()
                    else:
                        short = (
                            data.get("shortenedUrl") or
                            data.get("short_url") or
                            data.get("link") or
                            data.get("result") or
                            data.get("short") or
                            None
                        )
                        if short and short.startswith("http"):
                            print(f"✅ Short URL Generated: {short}")
                            return short

            # Method 2: POST with form data
            async with session.post(api_url, data={"api": api_key, "url": encoded_url}, timeout=timeout_obj) as resp:
                if resp.status == 200:
                    try:
                        data = await resp.json()
                    except:
                        text = await resp.text()
                        if text.startswith("http"):
                            print(f"✅ Short URL Generated: {text}")
                            return text.strip()
                    else:
                        short = (
                            data.get("shortenedUrl") or
                            data.get("short_url") or
                            data.get("link") or
                            data.get("result") or
                            data.get("short") or
                            None
                        )
                        if short and short.startswith("http"):
                            print(f"✅ Short URL Generated: {short}")
                            return short

            # Method 3: POST with JSON
            async with session.post(api_url, json={"api": api_key, "url": encoded_url}, timeout=timeout_obj) as resp:
                if resp.status == 200:
                    try:
                        data = await resp.json()
                    except:
                        text = await resp.text()
                        if text.startswith("http"):
                            print(f"✅ Short URL Generated: {text}")
                            return text.strip()
                    else:
                        short = (
                            data.get("shortenedUrl") or
                            data.get("short_url") or
                            data.get("link") or
                            data.get("result") or
                            data.get("short") or
                            None
                        )
                        if short and short.startswith("http"):
                            print(f"✅ Short URL Generated: {short}")
                            return short
    except Exception as e:
        print(f"Shortner error: {e}")

    # If all methods fail, return original URL
    print("⚠️ All shortner methods failed, using original URL")
    return original_url


# ---------- ADD SHORTNER ----------
@router.message(Command("adshort"))
async def add_shortner_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply("🔗 Send API endpoint URL (e.g., https://your-shortener.com/api)")
    await state.set_state(ShortnerState.waiting_url)

@router.message(ShortnerState.waiting_url)
async def shortner_url(message: Message, state: FSMContext):
    url = message.text.strip()
    if not url.startswith("http"):
        await message.reply("❌ URL must start with http:// or https://")
        return
    await state.update_data(url=url)
    await message.reply("🔑 Send API token/key")
    await state.set_state(ShortnerState.waiting_api)

@router.message(ShortnerState.waiting_api)
async def shortner_api(message: Message, state: FSMContext):
    data = await state.get_data()
    api_key = message.text.strip()
    await db.add_shortner(data["url"], api_key)
    await message.reply("✅ Shortner account added successfully!")
    await state.clear()


# ---------- REMOVE SHORTNER (ObjectId fix) ----------
@router.message(Command("removeshot"))
async def remove_shortner_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    shortners = await db.get_shortners()
    if not shortners:
        await message.reply("❌ No shortner accounts found.")
        return
    
    keyboard = []
    for s in shortners:
        btn_text = s["url"][:40] + "..." if len(s["url"]) > 40 else s["url"]
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"rem_{s['_id']}")])
    
    await message.reply(
        "Select shortner account to remove:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data.startswith("rem_"))
async def select_remove(callback: CallbackQuery, state: FSMContext):
    sid = callback.data.split("_")[1]
    await state.update_data(shortner_id=sid)
    await callback.message.reply("Type /delete to confirm removal.")
    await callback.answer()

@router.message(Command("delete"))
async def delete_shortner(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("shortner_id"):
        await message.reply("❌ No shortner selected. Use /removeshot first.")
        return
    # Convert string ID to ObjectId
    await db.remove_shortner(ObjectId(data["shortner_id"]))
    await message.reply("✅ Shortner account deleted successfully.")
    await state.clear()
