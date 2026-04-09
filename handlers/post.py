from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import OWNER_ID, ALLOWED_USERS, STORAGE_CHANNEL_ID, EPISODE_CHANNEL_ID, BOT_USERNAME
from database import db

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
    if not is_admin(message.from_user.id): return
    await message.reply("📤 Send the Main Post Media (Poster) for the channel.")
    await state.set_state(PostState.waiting_post)

@router.message(PostState.waiting_post)
async def receive_post(message: Message, state: FSMContext):
    if message.photo or message.video or message.document or message.forward_from_chat:
        # POSTER hamesha Storage Channel me hi jayega
        stored = await message.bot.forward_message(STORAGE_CHANNEL_ID, message.chat.id, message.message_id)
        await db.save_temp(message.from_user.id, {"storage_msg_id": stored.message_id})
        await message.reply("✅ Poster received.\n\nNow, send:\n`single link` OR `batch link`", parse_mode="Markdown")
        await state.set_state(PostState.waiting_link_type)
    else:
        await message.reply("❌ Send valid media.")

@router.message(PostState.waiting_link_type)
async def link_type(message: Message, state: FSMContext):
    text = message.text.lower()
    if "batch" in text:
        await db.save_temp(message.from_user.id, {"type": "batch", "episodes": []})
        await message.reply("📚 Forward all episode files one by one.\nType `done` when finished.")
        await state.set_state(PostState.waiting_batch_ep)
    elif "single" in text:
        await db.save_temp(message.from_user.id, {"type": "single"})
        await message.reply("🎬 Forward the single episode file.")
        await state.set_state(PostState.waiting_single_ep)
    else:
        await message.reply("❌ Invalid choice. Type `single link` or `batch link`.")

@router.message(PostState.waiting_single_ep)
async def single_ep(message: Message, state: FSMContext):
    temp = await db.get_temp(message.from_user.id)
    if message.photo or message.video or message.document or message.forward_from_chat:
        
        # ====== ZERO-COPY MAGIC (Duplicate Upload Fixed) ======
        if message.forward_from_chat:
            # Agar forward kiya hai, toh upload mat karo, sirf original ID utha lo!
            ep_msg_id = message.forward_from_message_id
            ep_chat_id = message.forward_from_chat.id
        else:
            # Agar admin ne direct upload kar diya, toh usko Episode Base me copy kardo
            stored_ep = await message.bot.copy_message(EPISODE_CHANNEL_ID, message.chat.id, message.message_id)
            ep_msg_id = stored_ep.message_id
            ep_chat_id = EPISODE_CHANNEL_ID

        await db.save_temp(message.from_user.id, {
            "episode_msg_id": ep_msg_id,
            "episode_chat_id": ep_chat_id
        })
        
        await message.reply("✅ Episode Linked Perfectly! (No duplicate upload)\nSend episode number (example: `07`)")
        return
        
    if message.text:
        ep = message.text.strip()
        await db.save_temp(message.from_user.id, {"episode": ep})
        await message.reply(f"✅ Episode {ep} linked.\nType `/hmm` to confirm post.")
        await state.clear()

@router.message(PostState.waiting_batch_ep)
async def batch_ep(message: Message, state: FSMContext):
    temp = await db.get_temp(message.from_user.id)
    episodes = temp.get("episodes", [])
    if message.photo or message.video or message.document or message.forward_from_chat:
        
        # ====== ZERO-COPY MAGIC FOR BATCH ======
        if message.forward_from_chat:
            ep_msg_id = message.forward_from_message_id
            ep_chat_id = message.forward_from_chat.id
        else:
            stored = await message.bot.copy_message(EPISODE_CHANNEL_ID, message.chat.id, message.message_id)
            ep_msg_id = stored.message_id
            ep_chat_id = EPISODE_CHANNEL_ID

        # Store as dictionary
        episodes.append({"msg_id": ep_msg_id, "chat_id": ep_chat_id})
        await db.save_temp(message.from_user.id, {"episodes": episodes})
        await message.reply(f"✅ Episode {len(episodes)} Linked. Send next or type `done`.")
        return
        
    if message.text and message.text.lower() == "done":
        if len(episodes) < 2:
            await message.reply("❌ Minimum 2 episodes required.")
            return
        await message.reply("Send range (example: `05-15`)")
        await state.set_state(PostState.waiting_batch_range)

@router.message(PostState.waiting_batch_range)
async def batch_range(message: Message, state: FSMContext):
    rng = message.text.strip()
    temp = await db.get_temp(message.from_user.id)
    episodes_ids = temp.get("episodes", [])
    try:
        s, e = rng.split("-")
        start, end = int(s), int(e)
        if end - start + 1 != len(episodes_ids):
            await message.reply("❌ Range count mismatch!")
            return
        for i, ep in enumerate(range(start, end + 1)):
            # Passing msg_id and chat_id separately
            await db.add_batch_episode(ep, episodes_ids[i]["msg_id"], episodes_ids[i]["chat_id"])
    except Exception:
        await message.reply("❌ Invalid range format.")
        return

    await db.save_temp(message.from_user.id, {"batch_range": rng})
    await message.reply(f"✅ Batch Range {rng} linked.\nType `/hmm` to confirm post.")
    await state.clear()

@router.message(Command("hmm"))
async def confirm_post(message: Message):
    temp = await db.get_temp(message.from_user.id)
    if not temp:
        await message.reply("❌ No post data found.")
        return

    if temp.get("type") == "batch":
        ep_param = temp.get("batch_range")
        btn_text = f"🎬 Watch Episodes {ep_param}"
    else:
        ep_param = temp.get("episode")
        btn_text = f"🎬 Watch Episode {ep_param}"

    clean_bot_username = BOT_USERNAME.replace("@", "")
    deep_link = f"https://t.me/{clean_bot_username}?start=ep_{ep_param}"
    
    button = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=btn_text, url=deep_link)]])
    
    await db.save_post({
        "storage_msg_id": temp.get("storage_msg_id"),
        "episode_msg_id": temp.get("episode_msg_id"),
        "episode_chat_id": temp.get("episode_chat_id"),
        "type": temp.get("type"),
        "episode": temp.get("episode"),
        "batch_range": temp.get("batch_range"),
        "reply_markup": button.model_dump()
    })

    await message.bot.copy_message(message.chat.id, STORAGE_CHANNEL_ID, temp["storage_msg_id"], reply_markup=button)

    action_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Send (Single Channel)", callback_data="cmd_send")],
        [InlineKeyboardButton(text="📤 Send More Channel", callback_data="cmd_sendmulti")]
    ])
    await message.reply("✅ **Post Ready!** Select an action below:", reply_markup=action_kb)
    await db.del_temp(message.from_user.id)
