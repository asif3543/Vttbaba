from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import OWNER_ID, ALLOWED_USERS, STORAGE_CHANNEL_ID, BOT_USERNAME
from database import db

router = Router()

# ================= STATES =================
class PostState(StatesGroup):
    waiting_post = State()
    waiting_link_type = State()
    waiting_single_ep = State()
    waiting_batch_ep = State()
    waiting_batch_range = State()

# ================= ADMIN CHECK =================
def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

# ================= /POST =================
@router.message(Command("post"))
async def post_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply("📤 Send post (poster/media)")
    await state.set_state(PostState.waiting_post)

# ================= RECEIVE POST =================
@router.message(PostState.waiting_post)
async def receive_post(message: Message, state: FSMContext):
    if (message.photo or message.video or message.document or message.forward_from_chat):
        stored = await message.bot.forward_message(
            STORAGE_CHANNEL_ID, message.chat.id, message.message_id
        )
        await db.save_temp(message.from_user.id, {"storage_msg_id": stored.message_id})
        await message.reply("✅ Post received.\n\nSend:\n`single link` or `batch link`", parse_mode="Markdown")
        await state.set_state(PostState.waiting_link_type)
    else:
        await message.reply("❌ Send valid media.")

# ================= LINK TYPE =================
@router.message(PostState.waiting_link_type)
async def link_type(message: Message, state: FSMContext):
    text = message.text.lower()
    temp = await db.get_temp(message.from_user.id)
    if "batch" in text:
        await db.save_temp(message.from_user.id, {**temp, "type": "batch", "episodes": []})
        await message.reply("📚 Forward episodes one by one.\nType `done` when finished.")
        await state.set_state(PostState.waiting_batch_ep)
    else:
        await db.save_temp(message.from_user.id, {**temp, "type": "single"})
        await message.reply("🎬 Forward episode media.")
        await state.set_state(PostState.waiting_single_ep)

# ================= SINGLE =================
@router.message(PostState.waiting_single_ep)
async def single_ep(message: Message, state: FSMContext):
    temp = await db.get_temp(message.from_user.id)

    # Step 1: forward episode
    if (message.photo or message.video or message.document or message.forward_from_chat):
        stored_ep = await message.bot.forward_message(
            STORAGE_CHANNEL_ID, message.chat.id, message.message_id
        )
        await db.save_temp(message.from_user.id, {**temp, "episode_msg_id": stored_ep.message_id})
        await message.reply("✅ Episode saved.\nSend episode number (example: `07`)")
        return

    # Step 2: episode number
    if message.text:
        ep = message.text.strip()
        await db.save_temp(message.from_user.id, {**temp, "episode": ep})
        await message.reply(f"✅ Episode {ep}\nType `/hmm`")
        await state.clear()

# ================= BATCH =================
@router.message(PostState.waiting_batch_ep)
async def batch_ep(message: Message, state: FSMContext):
    temp = await db.get_temp(message.from_user.id)
    episodes = temp.get("episodes", [])

    if (message.photo or message.video or message.document or message.forward_from_chat):
        stored = await message.bot.forward_message(
            STORAGE_CHANNEL_ID, message.chat.id, message.message_id
        )
        episodes.append(stored.message_id)
        await db.save_temp(message.from_user.id, {**temp, "episodes": episodes})
        await message.reply(f"✅ Episode {len(episodes)} saved")
        return

    if message.text == "done":
        if len(episodes) < 2:
            await message.reply("❌ Minimum 2 episodes required.")
            return
        await message.reply("Send range (example: `05-15`)")
        await state.set_state(PostState.waiting_batch_range)
        return

# ================= RANGE =================
@router.message(PostState.waiting_batch_range)
async def batch_range(message: Message, state: FSMContext):
    rng = message.text.strip()
    temp = await db.get_temp(message.from_user.id)
    episodes_ids = temp.get("episodes", [])

    try:
        s, e = rng.split("-")
        start = int(s)
        end = int(e)
        if end - start + 1 != len(episodes_ids):
            await message.reply("❌ Range count mismatch.")
            return
        for i, ep in enumerate(range(start, end + 1)):
            await db.add_batch_episode(ep, episodes_ids[i])
    except:
        await message.reply("❌ Invalid range.")
        return

    await db.save_temp(message.from_user.id, {**temp, "batch_range": rng})
    await message.reply(f"✅ Range {rng}\nType `/hmm`")
    await state.clear()

# ================= CONFIRM =================
@router.message(Command("hmm"))
async def confirm_post(message: Message):
    temp = await db.get_temp(message.from_user.id)
    if not temp:
        await message.reply("❌ No post.")
        return

    if temp.get("type") == "batch":
        episode_param = temp.get("batch_range")
        btn_text = f"🎬 Watch Episodes {episode_param}"
    else:
        episode_param = temp.get("episode")
        btn_text = f"🎬 Watch Episode {episode_param}"

    # IMPORTANT: Button always uses deep link, NOT shortner
    deep_link = f"https://t.me/{BOT_USERNAME}?start=ep_{episode_param}"
    button = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=btn_text, url=deep_link)]]
    )

    await message.bot.copy_message(
        message.chat.id,
        STORAGE_CHANNEL_ID,
        temp["storage_msg_id"],
        reply_markup=button
    )

    await db.save_post({
        "storage_msg_id": temp["storage_msg_id"],
        "type": temp.get("type"),
        "episode": temp.get("episode"),
        "batch_range": temp.get("batch_range"),
        "reply_markup": button.model_dump()
    })

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Send", callback_data="send_single")],
            [InlineKeyboardButton(text="📤 Send more channel", callback_data="send_multi")]
        ]
    )
    await message.reply("Post ready!", reply_markup=keyboard)
    await db.del_temp(message.from_user.id)
