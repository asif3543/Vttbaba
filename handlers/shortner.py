import aiohttp
import json
import re
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from urllib.parse import quote, urlparse
from bson import ObjectId
from config import OWNER_ID, ALLOWED_USERS
from database import db

router = Router()

class ShortnerState(StatesGroup):
    waiting_url = State()
    waiting_api = State()

def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

# ================= UNIVERSAL SHORTLINK MAKER =================
async def make_shortlink(shortner: dict, original_url: str) -> str:
    api_url = shortner.get("url")
    api_key = shortner.get("api")
    if not api_url or not api_key: return original_url

    encoded_url = quote(original_url, safe="")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            get_url = f"{api_url}?api={api_key}&url={encoded_url}"
            async with session.get(get_url, headers=headers, timeout=15) as resp:
                text = await resp.text()
                
                # Check for standard JSON response
                try:
                    data = json.loads(text)
                    short = data.get("shortenedUrl") or data.get("short_url") or data.get("link") or data.get("url")
                    if short and short.startswith("http"):
                        return short
                except json.JSONDecodeError:
                    pass

                # Fallback: Check if response is just a plain URL
                if text.strip().startswith("http"):
                    return text.strip()

                # Fallback 2: Regex to find any URL in response
                match = re.search(r'(https?://[^\s]+)', text)
                if match:
                    return match.group(1)
                    
    except Exception as e:
        print(f"❌ Shortner API Error for {api_url}: {e}")
        
    return original_url

# ================= ADD SHORTNER (WITH AUTO-FIX) =================
@router.message(Command("adshort"))
async def add_shortner_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.reply(
        "🔗 **Send Shortner Dashboard or Homepage URL**\n"
        "(Example: `https://gplinks.com/member/dashboard` or `https://shrinkme.io`)",
        parse_mode="Markdown"
    )
    await state.set_state(ShortnerState.waiting_url)

@router.message(ShortnerState.waiting_url)
async def shortner_url(message: Message, state: FSMContext):
    url = message.text.strip()
    if not url.startswith("http"):
        await message.reply("❌ URL must start with http:// or https://")
        return
        
    # URL AUTO-FIXER: Removes dashboard path, ensures it ends with /api
    parsed = urlparse(url)
    clean_domain = f"{parsed.scheme}://{parsed.netloc}"
    clean_api_url = f"{clean_domain}/api"
    
    await state.update_data(url=clean_api_url)
    await message.reply(
        f"✅ **Auto-Corrected API Endpoint:** `{clean_api_url}`\n\n"
        f"🔑 Now send your API token/key from the shortener tools.",
        parse_mode="Markdown"
    )
    await state.set_state(ShortnerState.waiting_api)

@router.message(ShortnerState.waiting_api)
async def shortner_api(message: Message, state: FSMContext):
    data = await state.get_data()
    api_key = message.text.strip()
    await db.add_shortner(data["url"], api_key)
    await message.reply("✅ Shortner account added successfully!")
    await state.clear()

# ================= REMOVE SHORTNER =================
@router.message(Command("removeshot"))
async def remove_shortner_cmd(message: Message):
    if not is_admin(message.from_user.id): return
    shortners = await db.get_shortners()
    if not shortners:
        await message.reply("❌ No shortner accounts found.")
        return
    
    keyboard = []
    for s in shortners:
        btn_text = s["url"][:40] + "..." if len(s["url"]) > 40 else s["url"]
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"rem_{s['_id']}")])
    
    await message.reply("Select shortner account to remove:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("rem_"))
async def select_remove(callback: CallbackQuery, state: FSMContext):
    sid = callback.data.split("_")[1]
    await state.update_data(shortner_id=sid)
    await callback.message.reply("Type `/delete` to confirm removal.")
    await callback.answer()

@router.message(Command("delete"))
async def delete_shortner(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    if not data.get("shortner_id"):
        await message.reply("❌ No shortner selected. Use /removeshot first.")
        return
    await db.remove_shortner(ObjectId(data["shortner_id"]))
    await message.reply("✅ Shortner account deleted successfully.")
    await state.clear()
