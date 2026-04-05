from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import OWNER_ID, ALLOWED_USERS, STORAGE_CHANNEL_ID, BOT_USERNAME
from database import db
from .shortner import make_shortlink

router = Router()

class PostState(StatesGroup):
    waiting_post = State()
    waiting_link_type = State()
    waiting_single_ep = State()
    waiting_batch_ep = State()
    waiting_batch_range = State()

def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

@router.message(Command("post"))
async def post_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply("📤 Send post (forward from any channel or user)")
    await state.set_state(PostState.waiting_post)

@router.message(PostState.waiting_post)
async def receive_post(message: Message, state: FSMContext):
    if message.forward_from_chat or message.forward_from:
        stored = await message.bot.forward_message(STORAGE_CHANNEL_ID, message.chat.id, message.message_id)
        await db.save_temp(message.from_user.id, {"storage_msg_id": stored.message_id})
        await message.reply("✅ Post received. Send 'single link' or 'batch link'")
        await state.set_state(PostState.waiting_link_type)
    else:
        await message.reply("❌ Please forward a post")

@router.message(PostState.waiting_link_type)
async def link_type(message: Message, state: FSMContext):
    text = message.text.lower()
    temp = await db.get_temp(message.from_user.id)
    if "batch" in text:
        await db.save_temp(message.from_user.id, {**temp, "type": "batch", "episodes": []})
        await message.reply("📚 Send episode (forward) or type 'done'")
        await state.set_state(PostState.waiting_batch_ep)
    else:
        await db.save_temp(message.from_user.id, {**temp, "type": "single"})
        await message.reply("🎬 Send episode (just the number, e.g. 07)")
        await state.set_state(PostState.waiting_single_ep)

@router.message(PostState.waiting_single_ep)
async def single_ep(message: Message, state: FSMContext):
    ep = message.text.strip()
    temp = await db.get_temp(message.from_user.id)
    await db.save_temp(message.from_user.id, {**temp, "episode": ep})
    await message.reply(f"✅ Episode {ep}\n/confirm or /hmm")
    await state.clear()

@router.message(PostState.waiting_batch_ep)
async def batch_ep(message: Message, state: FSMContext):
    temp = await db.get_temp(message.from_user.id)
    episodes = temp.get("episodes", [])
    if message.forward_from_chat or message.forward_from:
        episodes.append(message.message_id)
        await db.save_temp(message.from_user.id, {**temp, "episodes": episodes})
        await message.reply(f"✅ Episode {len(episodes)} received. Send next or type 'done'")
    elif message.text and message.text.lower() == "done":
        if len(episodes) < 2:
            await message.reply("❌ Need at least 2 episodes")
            return
        await message.reply("✅ Enter number range (e.g. 05-15)")
        await state.set_state(PostState.waiting_batch_range)
    else:
        await message.reply("❌ Forward an episode or type 'done'")

@router.message(PostState.waiting_batch_range)
async def batch_range(message: Message, state: FSMContext):
    rng = message.text.strip()
    temp = await db.get_temp(message.from_user.id)
    await db.save_temp(message.from_user.id, {**temp, "batch_range": rng})
    await message.reply(f"✅ Range {rng}\n/confirm or /hmm")
    await state.clear()

@router.message(Command("confirm"))
@router.message(Command("hmm"))
async def confirm_post(message: Message, state: FSMContext):
    temp = await db.get_temp(message.from_user.id)
    if not temp:
        await message.reply("❌ No pending post. Use /post first.")
        return
    shortner = await db.get_random_shortner()
    if temp.get("type") == "batch":
        episode_val = temp.get("batch_range", "1")
        btn_text = f"🎬 Watch Episode {episode_val}"
    else:
        episode_val = temp.get("episode", "1")
        btn_text = f"🎬 Watch Episode {episode_val}"
    original_url = f"https://t.me/{BOT_USERNAME}?start=ep_{episode_val}"
    if shortner:
        short_url = await make_shortlink(shortner, original_url)
    else:
        short_url = original_url
    button = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=btn_text, url=short_url)]])
    await message.bot.copy_message(message.chat.id, STORAGE_CHANNEL_ID, temp["storage_msg_id"], reply_markup=button)
    await db.save_post({
        "storage_msg_id": temp["storage_msg_id"],
        "type": temp.get("type"),
        "episode": temp.get("episode"),
        "batch_range": temp.get("batch_range"),
        "short_url": short_url
    })
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Send", callback_data="send_single")],
        [InlineKeyboardButton(text="📤 Send more channel", callback_data="send_multi")]
    ])
    await message.reply("[ Send ]\n[ Send more channel ]", reply_markup=keyboard)
    await db.del_temp(message.from_user.id)
