import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import OWNER_ID, ALLOWED_USERS, STORAGE_CHANNEL_ID, BOT_USERNAME
from database import db
from datetime import datetime

router = Router()

multi_selected = {}

# ==================== STATES ====================
class PostState(StatesGroup):
    waiting_post = State()
    waiting_link_type = State()
    waiting_single_episode = State()
    waiting_single_number = State()
    waiting_batch_episode = State()
    waiting_batch_range = State()
    waiting_hmm = State()

class ShortnerAddState(StatesGroup):
    waiting_url = State()
    waiting_token = State()

class PremiumAddState(StatesGroup):
    waiting_id = State()

class PremiumRemoveState(StatesGroup):
    waiting_id = State()

class FSUBState(StatesGroup):
    waiting_message = State()

def is_admin(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in ALLOWED_USERS

# ==================== SHORTNER API ====================
async def create_shortlink(shortner: dict, original_url: str) -> str:
    try:
        api_url = f"{shortner['url']}/api?api={shortner['api']}&url={original_url}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("shortenedUrl") or data.get("shortened_url") or data.get("short_url") or original_url
    except Exception as e:
        pass
    return original_url

# ==================== SEND EPISODE (FILES) TO USER ====================
async def send_episode_to_user(message: Message, user_id: int, episode: str, is_verify: bool = False):
    if await db.is_banned(user_id):
        await message.reply("❌ You are banned from using this bot.")
        return
    
    post = await db.get_post_by_episode(episode)
    if not post:
        await message.reply("❌ Episode not found.")
        return

    # Check premium
    is_prem = await db.is_premium(user_id)
    
    # FSUB Check
    fsub_channels = await db.get_fsub_channels()
    not_joined = []
    
    for channel in fsub_channels:
        try:
            member = await message.bot.get_chat_member(channel["_id"], user_id)
            if member.status not in ["member", "administrator", "creator"]:
                not_joined.append(channel)
        except:
            not_joined.append(channel)
    
    if not_joined:
        keyboard = [[InlineKeyboardButton(text=f"📢 Join {ch['name']}", url=ch["link"])] for ch in not_joined]
        keyboard.append([InlineKeyboardButton(text="✅ Try Again", callback_data=f"retry_{episode}_{1 if is_verify else 0}")])
        
        await message.reply("join first\nTry again", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        return
    
    # If Free user and Not Verified -> Send to shortner
    if not is_prem and not is_verify:
        shortner = await db.get_random_shortner()
        if shortner:
            original_url = f"https://t.me/{BOT_USERNAME}?start=verify_{episode}"
            short_url = await create_shortlink(shortner, original_url)
            
            await message.reply(
                f"🔗 Please solve the shortner to get episode:\n{short_url}\n\n"
                f"After solving, you'll get the episode automatically."
            )
            return

    # If Premium OR Verified -> Send actual files
    for file_msg_id in post.get("ep_msg_ids", []):
        try:
            await message.bot.copy_message(user_id, STORAGE_CHANNEL_ID, file_msg_id)
        except:
            pass

@router.callback_query(F.data.startswith("retry_"))
async def retry_episode(callback: CallbackQuery):
    data_parts = callback.data.split("_")
    episode = data_parts[1]
    is_verify = bool(int(data_parts[2]))
    await callback.message.delete()
    await send_episode_to_user(callback.message, callback.from_user.id, episode, is_verify)

# ==================== /start ====================
@router.message(Command("start"))
async def start_cmd(message: Message):
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) > 1:
        if args[1].startswith("episode_"):
            episode = args[1].replace("episode_", "")
            await send_episode_to_user(message, user_id, episode, is_verify=False)
            return
        elif args[1].startswith("verify_"):
            episode = args[1].replace("verify_", "")
            await send_episode_to_user(message, user_id, episode, is_verify=True)
            return
            
    await message.reply("🤖 Bot is alive!")

# ==================== /post SYSTEM ====================
@router.message(Command("post"))
async def post_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.reply("send post")
    await state.set_state(PostState.waiting_post)

@router.message(PostState.waiting_post)
async def receive_post(message: Message, state: FSMContext):
    stored = await message.bot.copy_message(STORAGE_CHANNEL_ID, message.chat.id, message.message_id)
    await db.save_temp_post(message.from_user.id, {"storage_msg_id": stored.message_id, "ep_msg_ids": []})
    
    await message.reply("post successfully received \n"
                        "Please provide single link batch link")
    await state.set_state(PostState.waiting_link_type)

@router.message(PostState.waiting_link_type)
async def receive_link_type(message: Message, state: FSMContext):
    text = message.text.lower()
    temp = await db.get_temp_post(message.from_user.id)
    
    if "batch" in text:
        await db.save_temp_post(message.from_user.id, {**temp, "link_type": "batch"})
        await message.reply("send episode")
        await state.set_state(PostState.waiting_batch_episode)
    else:
        await db.save_temp_post(message.from_user.id, {**temp, "link_type": "single"})
        await message.reply("send episode")
        await state.set_state(PostState.waiting_single_episode)

# Single Link Workflow
@router.message(PostState.waiting_single_episode)
async def receive_single_episode(message: Message, state: FSMContext):
    stored = await message.bot.copy_message(STORAGE_CHANNEL_ID, message.chat.id, message.message_id)
    temp = await db.get_temp_post(message.from_user.id)
    ep_ids = temp.get("ep_msg_ids", [])
    ep_ids.append(stored.message_id)
    await db.save_temp_post(message.from_user.id, {**temp, "ep_msg_ids": ep_ids})
    
    await message.reply("Enter Number")
    await state.set_state(PostState.waiting_single_number)

@router.message(PostState.waiting_single_number)
async def receive_single_number(message: Message, state: FSMContext):
    episode = message.text.strip()
    temp = await db.get_temp_post(message.from_user.id)
    await db.save_temp_post(message.from_user.id, {**temp, "episode": episode})
    await message.reply("/confirm")
    await state.set_state(PostState.waiting_hmm)

# Batch Link Workflow
@router.message(PostState.waiting_batch_episode)
async def receive_batch_episode(message: Message, state: FSMContext):
    if message.text and message.text.lower() == "done":
        await message.reply("batch successfully adding\n"
                            "Enter number")
        await state.set_state(PostState.waiting_batch_range)
    else:
        stored = await message.bot.copy_message(STORAGE_CHANNEL_ID, message.chat.id, message.message_id)
        temp = await db.get_temp_post(message.from_user.id)
        ep_ids = temp.get("ep_msg_ids", [])
        ep_ids.append(stored.message_id)
        await db.save_temp_post(message.from_user.id, {**temp, "ep_msg_ids": ep_ids})
        await message.reply("send next episode")

@router.message(PostState.waiting_batch_range)
async def receive_batch_range(message: Message, state: FSMContext):
    ep_range = message.text.strip()
    temp = await db.get_temp_post(message.from_user.id)
    await db.save_temp_post(message.from_user.id, {**temp, "batch_range": ep_range})
    await message.reply("confirm")
    await state.set_state(PostState.waiting_hmm)

# ==================== /hmm (Confirm Post) ====================
@router.message(F.text.lower() == "/hmm")
async def hmm_post(message: Message, state: FSMContext):
    temp = await db.get_temp_post(message.from_user.id)
    if not temp: return
    
    if temp.get("link_type") == "batch":
        episode_val = temp.get("batch_range")
        btn_text = f"Watch episode {episode_val}"
    else:
        episode_val = temp.get("episode")
        btn_text = f"Watch episode {episode_val}"
        
    deep_link = f"https://t.me/{BOT_USERNAME}?start=episode_{episode_val}"
    button = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=btn_text, url=deep_link)]])
    
    # Save post to database completely
    await db.save_post({
        "link_type": temp.get("link_type"),
        "episode": temp.get("episode"),
        "batch_range": temp.get("batch_range"),
        "storage_msg_id": temp["storage_msg_id"],
        "ep_msg_ids": temp.get("ep_msg_ids", []),
        "created_at": datetime.utcnow()
    })
    
    await message.bot.copy_message(message.chat.id, STORAGE_CHANNEL_ID, temp["storage_msg_id"], reply_markup=button)
    await message.reply("[ Send ]\n[ Send more channel]")
    await state.clear()

# ==================== SEND POST SYSTEM ====================
@router.message(Command("send"))
async def send_cmd(message: Message):
    if not is_admin(message.from_user.id): return
    channels = await db.get_channels()
    keyboard = [[InlineKeyboardButton(text=ch["name"], callback_data=f"single_{ch['_id']}")] for ch in channels]
    await message.reply("Select option:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("single_"))
async def send_single(callback: CallbackQuery):
    channel_id = int(callback.data.split("_")[1])
    temp = await db.get_temp_post(callback.from_user.id) or {}
    await db.save_temp_post(callback.from_user.id, {**temp, "pending_channel": channel_id, "send_type": "single"})
    await callback.message.reply("confirm please")

@router.message(F.text.lower() == "/send more channel")
async def send_more_cmd(message: Message):
    if not is_admin(message.from_user.id): return
    channels = await db.get_channels()
    
    user_id = message.from_user.id
    multi_selected[user_id] = []
    
    keyboard = [[InlineKeyboardButton(text=f"☐ {ch['name']}", callback_data=f"multi_{ch['_id']}")] for ch in channels]
    keyboard.append([InlineKeyboardButton(text="✅ Done", callback_data="multi_done")])
    await message.reply("Select channel:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("multi_") & ~F.data.in_(["multi_done"]))
async def select_multi(callback: CallbackQuery):
    ch_id = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    if ch_id in multi_selected.get(user_id, []):
        multi_selected[user_id].remove(ch_id)
    else:
        multi_selected.setdefault(user_id, []).append(ch_id)
        
    channels = await db.get_channels()
    keyboard = [[InlineKeyboardButton(text=f"{'✅' if str(ch['_id']) in multi_selected[user_id] else '☐'} {ch['name']}", callback_data=f"multi_{ch['_id']}")] for ch in channels]
    keyboard.append([InlineKeyboardButton(text="✅ Done", callback_data="multi_done")])
    await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "multi_done")
async def multi_done(callback: CallbackQuery):
    user_id = callback.from_user.id
    temp = await db.get_temp_post(user_id) or {}
    await db.save_temp_post(user_id, {**temp, "pending_channels": multi_selected.get(user_id, []), "send_type": "multi"})
    await callback.message.reply("confirm please")

@router.message(Command("confirm"))
async def confirm_send(message: Message):
    temp = await db.get_temp_post(message.from_user.id)
    latest_post = await db.get_latest_post()
    if not temp or not latest_post: return
    
    if latest_post.get("link_type") == "batch":
        episode_val = latest_post.get("batch_range")
        btn_text = f"Watch episode {episode_val}"
    else:
        episode_val = latest_post.get("episode")
        btn_text = f"Watch episode {episode_val}"
        
    deep_link = f"https://t.me/{BOT_USERNAME}?start=episode_{episode_val}"
    button = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=btn_text, url=deep_link)]])
    
    if temp.get("send_type") == "single":
        try:
            await message.bot.copy_message(temp["pending_channel"], STORAGE_CHANNEL_ID, latest_post["storage_msg_id"], reply_markup=button)
        except: pass
    elif temp.get("send_type") == "multi":
        for ch_id in temp.get("pending_channels", []):
            try:
                await message.bot.copy_message(int(ch_id), STORAGE_CHANNEL_ID, latest_post["storage_msg_id"], reply_markup=button)
            except: pass
            
    await db.delete_temp_post(message.from_user.id)

# ==================== SHORTNER SYSTEM ====================
@router.message(F.text.lower() == "/add shortner account")
async def add_shortner(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.reply("provide deskbord url")
    await state.set_state(ShortnerAddState.waiting_url)

@router.message(ShortnerAddState.waiting_url)
async def short_url(message: Message, state: FSMContext):
    await state.update_data(url=message.text.strip())
    await message.reply("send your API Token")
    await state.set_state(ShortnerAddState.waiting_token)

@router.message(ShortnerAddState.waiting_token)
async def short_token(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.add_shortner(data["url"], message.text.strip())
    await message.reply("successfully add 🤗🤗🤗")
    await state.clear()

@router.message(F.text.lower() == "/remove shortner account")
async def remove_shortner(message: Message):
    if not is_admin(message.from_user.id): return
    shortners = await db.get_shortners()
    keyboard = [[InlineKeyboardButton(text=f"{s['url']} - {s['api'][:4]}...", callback_data=f"rem_{s['_id']}")] for s in shortners]
    await message.reply("select account", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("rem_"))
async def sel_remove(callback: CallbackQuery, state: FSMContext):
    await state.update_data(short_id=callback.data.split("_")[1])
    await callback.message.reply("kya aap hatana chahte hai\ntype /delete")

@router.message(F.text.lower() == "/delete")
async def del_shortner(message: Message, state: FSMContext):
    data = await state.get_data()
    if "short_id" in data:
        await db.remove_shortner(data["short_id"])
        await message.reply("successfully delete account for shortner")
        await state.clear()

# ==================== PREMIUM SYSTEM ====================
@router.message(F.text.lower() == "/add premium")
async def add_prem(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.reply("send I'd")
    await state.set_state(PremiumAddState.waiting_id)

@router.message(PremiumAddState.waiting_id)
async def prem_id(message: Message, state: FSMContext):
    await state.update_data(pid=int(message.text.strip()))
    await message.reply("successfully add member\nPleas confirm type /hu hu")

@router.message(F.text.lower() == "/hu hu")
async def hu_hu(message: Message, state: FSMContext):
    data = await state.get_data()
    if "pid" in data:
        await db.add_premium(data["pid"])
        await message.reply(f"successfully add member {data['pid']} 🪄🪄🪄")
        await state.clear()

@router.message(F.text.lower() == "/remove premium")
async def remove_prem(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.reply("send I'd")
    await state.set_state(PremiumRemoveState.waiting_id)

@router.message(PremiumRemoveState.waiting_id)
async def rm_prem_id(message: Message, state: FSMContext):
    await db.remove_premium(int(message.text.strip()))
    await message.reply("successfully deleted and ban")
    await state.clear()

@router.message(F.text.lower() == "/show premium list")
async def show_prem(message: Message):
    if not is_admin(message.from_user.id): return
    users = await db.get_premium_list()
    if users:
        await message.reply("🌟 Premium Users:\n" + "\n".join([f"`{u['_id']}`" for u in users]))
    else:
        await message.reply("No premium users.")

# ==================== FORCE SUB ====================
@router.message(F.text.lower() == "/force sub")
async def force_sub_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.reply("please send massage and chack I'm admin gc")
    await state.set_state(FSUBState.waiting_message)

@router.message(FSUBState.waiting_message)
async def rec_fsub(message: Message, state: FSMContext):
    if message.forward_from_chat:
        ch = message.forward_from_chat
        await db.add_fsub_channel(ch.id, ch.title)
        await message.reply("😘 adding successfully 😲")
    else:
        await message.reply("Please forward from channel.")
    await state.clear()
