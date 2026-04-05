from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import OWNER_ID, ALLOWED_USERS, STORAGE_CHANNEL_ID, BOT_USERNAME
from database import db
from .shortner import make_shortlink

router = Router()

# ------------------- STATES -------------------
class PostState(StatesGroup):
    waiting_post = State()
    waiting_link_type = State()
    waiting_single_ep = State()
    waiting_batch_ep = State()
    waiting_batch_range = State()

# ------------------- ADMIN CHECK -------------------
def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

# ------------------- /post COMMAND -------------------
@router.message(Command("post"))
async def post_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply("📤 Send post (forward a photo/video/document or any media)")
    await state.set_state(PostState.waiting_post)

# ------------------- RECEIVE POST MEDIA -------------------
@router.message(PostState.waiting_post)
async def receive_post(message: Message, state: FSMContext):
    if message.forward_from_chat or message.forward_from or message.photo or message.video or message.document:
        # Forward to storage channel
        stored = await message.bot.forward_message(
            STORAGE_CHANNEL_ID, message.chat.id, message.message_id
        )
        await db.save_temp(message.from_user.id, {"storage_msg_id": stored.message_id})
        await message.reply("✅ Post received.\n\nNow send: `single link` or `batch link`", parse_mode="Markdown")
        await state.set_state(PostState.waiting_link_type)
    else:
        await message.reply("❌ Please forward a post (media) or send a photo/video/document.")

# ------------------- SINGLE OR BATCH -------------------
@router.message(PostState.waiting_link_type)
async def link_type(message: Message, state: FSMContext):
    text = message.text.lower()
    temp = await db.get_temp(message.from_user.id)

    if "batch" in text:
        await db.save_temp(message.from_user.id, {**temp, "type": "batch", "episodes": []})
        await message.reply("📚 Send episodes one by one (forward each episode).\nWhen done, type `done`")
        await state.set_state(PostState.waiting_batch_ep)
    else:  # single link
        await db.save_temp(message.from_user.id, {**temp, "type": "single"})
        await message.reply("🎬 Now forward the episode (media) for this single post.")
        await state.set_state(PostState.waiting_single_ep)

# ------------------- SINGLE EPISODE (FORWARD + NUMBER) -------------------
@router.message(PostState.waiting_single_ep)
async def single_ep(message: Message, state: FSMContext):
    temp = await db.get_temp(message.from_user.id)

    # Step 1: forward episode media
    if message.forward_from_chat or message.forward_from or message.photo or message.video or message.document:
        stored_ep = await message.bot.forward_message(
            STORAGE_CHANNEL_ID, message.chat.id, message.message_id
        )
        await db.save_temp(message.from_user.id, {**temp, "episode_msg_id": stored_ep.message_id})
        await message.reply("✅ Episode media saved. Now send the episode number (e.g., `07`)")
        return

    # Step 2: episode number
    if message.text:
        ep = message.text.strip()
        await db.save_temp(message.from_user.id, {**temp, "episode": ep})
        await message.reply(f"✅ Episode {ep}\nType `/hmm` to confirm post.")
        await state.clear()

# ------------------- BATCH EPISODES (COLLECT FORWARDS) -------------------
@router.message(PostState.waiting_batch_ep)
async def batch_ep(message: Message, state: FSMContext):
    temp = await db.get_temp(message.from_user.id)
    episodes = temp.get("episodes", [])

    # Forwarded episode media
    if message.forward_from_chat or message.forward_from or message.photo or message.video or message.document:
        stored_ep = await message.bot.forward_message(
            STORAGE_CHANNEL_ID, message.chat.id, message.message_id
        )
        episodes.append(stored_ep.message_id)
        await db.save_temp(message.from_user.id, {**temp, "episodes": episodes})
        await message.reply(f"✅ Episode {len(episodes)} received. Send next or type `done`")
        return

    # User types "done"
    if message.text and message.text.lower() == "done":
        if len(episodes) < 2:
            await message.reply("❌ Need at least 2 episodes for batch.")
            return
        await message.reply("✅ Now send the episode number range (e.g., `05-15`)")
        await state.set_state(PostState.waiting_batch_range)
        return

    await message.reply("❌ Please forward an episode media or type `done`.")

# ------------------- BATCH RANGE -------------------
@router.message(PostState.waiting_batch_range)
async def batch_range(message: Message, state: FSMContext):
    rng = message.text.strip()
    temp = await db.get_temp(message.from_user.id)

    # Save range and also map each episode number to its stored message id
    episodes_ids = temp.get("episodes", [])
    # Parse range: e.g., "05-15"
    try:
        start_str, end_str = rng.split("-")
        start = int(start_str)
        end = int(end_str)
        if end - start + 1 != len(episodes_ids):
            await message.reply(f"⚠️ You forwarded {len(episodes_ids)} episodes but range has {end-start+1} episodes.\nPlease match the count or use correct range.")
            return
        # Store mapping in database for future retrieval
        for i, ep_num in enumerate(range(start, end+1)):
            await db.add_batch_episode(ep_num, episodes_ids[i])
    except:
        await message.reply("❌ Invalid range format. Use like `05-15`")
        return

    await db.save_temp(message.from_user.id, {**temp, "batch_range": rng})
    await message.reply(f"✅ Batch range {rng}\nType `/hmm` to confirm post.")
    await state.clear()

# ------------------- CONFIRM POST (CREATE BUTTON) -------------------
@router.message(Command("hmm"))
async def confirm_post(message: Message, state: FSMContext):
    temp = await db.get_temp(message.from_user.id)
    if not temp:
        await message.reply("❌ No pending post. Use /post first.")
        return

    # Determine button text and episode param
    if temp.get("type") == "batch":
        episode_param = temp.get("batch_range", "1")   # e.g., "05-15"
        btn_text = f"🎬 Watch Episodes {episode_param}"
    else:
        episode_param = temp.get("episode", "1")
        btn_text = f"🎬 Watch Episode {episode_param}"

    # Deep link URL
    original_url = f"https://t.me/{BOT_USERNAME}?start=ep_{episode_param}"

    # Shortner failover
    shortners = await db.get_shortners()
    short_url = original_url
    if shortners:
        import random
        random.shuffle(shortners)
        for s in shortners:
            try:
                test_url = await make_shortlink(s, original_url)
                if test_url and test_url != original_url:
                    short_url = test_url
                    print(f"✅ Used shortner: {s['url']}")
                    break
            except Exception as e:
                print(f"Shortner error: {e}")

    # Create button
    button = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=btn_text, url=short_url)]]
    )

    # Send the post preview with button
    await message.bot.copy_message(
        message.chat.id,
        STORAGE_CHANNEL_ID,
        temp["storage_msg_id"],
        reply_markup=button
    )

    # Save post info in DB (for later reference)
    await db.save_post({
        "storage_msg_id": temp["storage_msg_id"],
        "type": temp.get("type"),
        "episode": temp.get("episode"),
        "batch_range": temp.get("batch_range"),
        "short_url": short_url,
        "created_at": temp.get("created_at")  # optional
    })

    # Show send options
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Send", callback_data="send_single")],
        [InlineKeyboardButton(text="📤 Send more channel", callback_data="send_multi")]
    ])
    await message.reply("Post ready!\nChoose an option:", reply_markup=keyboard)

    # Clean up temp data
    await db.del_temp(message.from_user.id)
