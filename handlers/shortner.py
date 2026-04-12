import aiohttp
import json
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

# ================= MAKE SHORTLINK =================
async def make_shortlink(shortner: dict, original_url: str) -> str:
    api_url = shortner.get("url")
    api_key = shortner.get("api")
    if not api_url or not api_key: return original_url

    # Proper URL encoding
    encoded_url = quote(original_url, safe="")
    
    # Adding User-Agent because some shortners block bots
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            get_url = f"{api_url}?api={api_key}&url={encoded_url}"
            async with session.get(get_url, headers=headers, timeout=15) as resp:
                text = await resp.text()
                
                try:
                    data = json.loads(text)
                    if data.get("status") == "success" or data.get("shortenedUrl"):
                        short = data.get("shortenedUrl") or data.get("short_url") or data.get("link")
                        if short and short.startswith("http"):
                            return short
                except json.JSONDecodeError:
                    if text.strip().startswith("http"):
                        return text.strip()
    except Exception as e:
        print(f"❌ Shortner API Request Failed: {e}")
        
    return original_url

# ================= ADD SHORTNER =================
@router.message(Command("adshort"))
async def add_shortner_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.reply(
        "🔗 Send Shortner URL\n\n"
        "*(You can send Dashboard URL or Homepage, I will auto-fix it)*\n"
        "Example: `https://gplinks.com/`",
        parse_mode="Markdown"
    )
    await state.set_state(ShortnerState.waiting_url)

@router.message(ShortnerState.waiting_url)
async def shortner_url(message: Message, state: FSMContext):
    url = message.text.strip()
    if not url.startswith("http"):
        await message.reply("❌ URL must start with http:// or https://")
        return
        
    # ====== AUTO URL FIXER ======
    # Ye user ke /member/dashboard ko automatically /api me badal dega
    parsed = urlparse(url)
    clean_url = f"{parsed.scheme}://{parsed.netloc}/api"
    # ============================
    
    await state.update_data(url=clean_url)
    await message.reply(
        f"✅ **URL Auto-Corrected to:** `{clean_url}`\n\n"
        f"🔑 Now send your API token/key",
        parse_mode="Markdown"
    )
    await state.set_state(ShortnerState.waiting_api)

@router.message(ShortnerState.waiting_api)
async def shortner_api(message: Message, state: FSMContext):
    data = await state.get_data()
    api_key = message.text.strip()
    await db.add_shortner(data["url"], api_key)
    await message.reply("✅ Shortner account added successfully!\nNow you can test your links.")
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
