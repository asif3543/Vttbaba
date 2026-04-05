import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from aiogram.filters import Command
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, MEMBER, ADMINISTRATOR, IS_NOT_MEMBER
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import OWNER_ID, ALLOWED_USERS, STORAGE_CHANNEL_ID, BOT_USERNAME
from database import db
from datetime import datetime

router = Router()

# ==================== STATES ====================
class PostState(StatesGroup):
    waiting_post = State()
    waiting_link_type = State()
    waiting_episode = State()
    waiting_number = State()
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

# ==================== CHECK ACCESS ====================
def is_admin(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in ALLOWED_USERS

# ==================== AUTO ADMIN DETECT ====================
# Tracks channels where bot gets added/removed as admin to populate the list
@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER >> ADMINISTRATOR))
async def bot_added_as_admin(event: ChatMemberUpdated):
    if event.chat.type == "channel":
        await db.add_channel(event.chat.id, event.chat.title)

@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=ADMINISTRATOR >> IS_NOT_MEMBER))
async def bot_removed_as_admin(event: ChatMemberUpdated):
    if event.chat.type == "channel":
        await db.remove_channel(event.chat.id)

# ==================== SHORTNER API ====================
async def create_shortlink(shortner: dict, original_url: str) -> str:
    """Generate short link via API GET format"""
    api_url = f"{shortner['url']}/api?api={shortner['api']}&url={original_url}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("shortenedUrl") or data.get("short_url") or original_url
    except Exception as e:
        print(f"Shortner error: {e}")
    return original_url

# ==================== FILE DELIVERY SYSTEM ====================
async def send_files(bot, user_id: int, episode_label: str, message_to_reply=None):
    post = await db.get_post_by_episode(episode_label)
    if not post:
        if message_to_reply: await message_to_reply.reply("❌ Episode not found in Database.")
        return
        
    for file_msg_id in post.get("file_msg_ids", []):
        try:
            await bot.copy_message(user_id, STORAGE_CHANNEL_ID, file_msg_id)
        except Exception:
            pass

async def verify_and_send_episode(bot, user_id: int, episode_label: str, message: Message):
    # Check force subscribe
    fsub_channels = await db.get_fsub_channels()
    not_joined = []
    
    for channel in fsub_channels:
        try:
            member = await bot.get_chat_member(channel["_id"], user_id)
            if member.status not in ["member", "administrator", "creator"]:
                not_joined.append(channel)
        except:
            not_joined.append(channel)
    
    if not_joined:
        keyboard = []
        for ch in not_joined:
            keyboard.append([InlineKeyboardButton(text=f"📢 Join {ch['name']}", url=ch["link"])])
        keyboard.append([InlineKeyboardButton(text="✅ Try Again", callback_data=f"retry_{episode_label}")])
        
        await message.reply(
            "join first",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        return
        
    # Free users that have passed shortner and FSub
    await send_files(bot, user_id, episode_label, message)

# ==================== /start ====================
@router.message(Command("start"))
async def start_cmd(message: Message):
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) > 1:
        param = args[1]
        
        # When user clicks button on channel post
        if param.startswith("episode_"):
            episode_label = param.replace("episode_", "")
            
            if await db.is_banned(user_id):
                await message.reply("❌ You are banned.")
                return
                
            # If Premium -> bypass shortner & directly verify fsub/send files
            if await db.is_premium(user_id):
                await verify_and_send_episode(message.bot, user_id, episode_label, message)
                return
                
            # Free user -> generate shortlink
            shortner = await db.get_random_shortner()
            if shortner:
                verify_link = f"https://t.me/{BOT_USERNAME}?start=verify_{episode_label}"
                short_url = await create_shortlink(shortner, verify_link)
                await message.reply(f"🔗 Please solve the shortner to get episode:\n{short_url}\n\nAfter solving, you'll get the episode automatically.")
            else:
                # No shortner configured -> directly to verify
                await verify_and_send_episode(message.bot, user_id, episode_label, message)
            return
            
        # When user comes back after solving shortner
        elif param.startswith("verify_"):
            episode_label = param.replace("verify_", "")
            await verify_and_send_episode(message.bot, user_id, episode_label, message)
            return

    await message.reply("🤖 Bot is alive!")

@router.callback_query(F.data.startswith("retry_"))
async def retry_fsub(callback: CallbackQuery):
    episode_label = callback.data.replace("retry_", "")
    await callback.message.delete()
    await verify_and_send_episode(callback.bot, callback.from_user.id, episode_label, callback.message)

# ==================== POST SYSTEM ====================
@router.message(Command("post"))
async def post_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.reply("send post")
    await state.set_state(PostState.waiting_post)

@router.message(PostState.waiting_post)
async def receive_post(message: Message, state: FSMContext):
    stored = await message.bot.copy_message(STORAGE_CHANNEL_ID, message.chat.id, message.message_id)
    await state.update_data(main_msg_id=stored.message_id)
    await message.reply("post successfully received \nPlease provide single link or batch link")
    await state.set_state(PostState.waiting_link_type)

@router.message(PostState.waiting_link_type, F.text.lower().in_(["single link", "batch link"]))
async def receive_link_type(message: Message, state: FSMContext):
    is_batch = "batch" in message.text.lower()
    await state.update_data(link_type="batch" if is_batch else "single", file_msg_ids=[])
    await message.reply("send episode")
    await state.set_state(PostState.waiting_episode)

@router.message(PostState.waiting_episode)
async def receive_episode(message: Message, state: FSMContext):
    data = await state.get_data()
    
    if data["link_type"] == "batch" and message.text and message.text.lower() == "done":
        await message.reply("batch successfully adding\nEnter number (example: 05-15)")
        await state.set_state(PostState.waiting_number)
        return
        
    stored = await message.bot.copy_message(STORAGE_CHANNEL_ID, message.chat.id, message.message_id)
    file_msg_ids = data.get("file_msg_ids", [])
    file_msg_ids.append(stored.message_id)
    await state.update_data(file_msg_ids=file_msg_ids)
    
    if data["link_type"] == "single":
        await message.reply("Enter Number")
        await state.set_state(PostState.waiting_number)
    else:
        await message.reply("send next episode\n(Or type 'done')")

@router.message(PostState.waiting_number)
async def receive_number(message: Message, state: FSMContext):
    await state.update_data(episode_label=message.text.strip())
    await message.reply("/confirm")
    await state.set_state(PostState.waiting_hmm)

@router.message(PostState.waiting_hmm, F.text.lower() == "/hmm")
async def confirm_hmm(message: Message, state: FSMContext):
    data = await state.get_data()
    episode_label = data["episode_label"]
    main_msg_id = data["main_msg_id"]
    
    btn_text = f"Watch Episode {episode_label}"
    deep_link = f"https://t.me/{BOT_USERNAME}?start=episode_{episode_label}"
    button = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=btn_text, url=deep_link)]])
    
    # Add markup to storage message
    await message.bot.edit_message_reply_markup(chat_id=STORAGE_CHANNEL_ID, message_id=main_msg_id, reply_markup=button)
    
    # Save post
    await db.save_post({
        "episode_label": episode_label,
        "main_msg_id": main_msg_id,
        "file_msg_ids": data["file_msg_ids"],
        "created_at": datetime.utcnow()
    })
    
    # Send preview and options
    await message.bot.copy_message(message.chat.id, STORAGE_CHANNEL_ID, main_msg_id, reply_markup=button)
    await message.reply("[ Send ]\n[ Send more channel]")
    await state.clear()

# ==================== SEND CHANNELS ====================
@router.message(F.text.lower() == "/send")
async def send_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    channels = await db.get_channels()
    if not channels:
        await message.reply("❌ Bot is not admin in any channel!")
        return
        
    keyboard = [[InlineKeyboardButton(text=ch["name"], callback_data=f"single_{ch['_id']}")] for ch in channels]
    await message.reply("Select channel:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("single_"))
async def select_single(callback: CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.split("_")[1])
    await state.update_data(send_type="single", pending_channel=channel_id)
    await callback.message.reply("confirm please")

@router.message(F.text.lower() == "/send more channel")
async def send_more_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    channels = await db.get_channels()
    if not channels: return
    
    await state.update_data(multi_channels=[])
    keyboard = [[InlineKeyboardButton(text=f"☐ {ch['name']}", callback_data=f"multi_{ch['_id']}")] for ch in channels]
    keyboard.append([InlineKeyboardButton(text="✅ Done", callback_data="multi_done")])
    await message.reply("Select channels:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("multi_") & ~F.data.in_(["multi_done"]))
async def toggle_multi(callback: CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    selected = data.get("multi_channels", [])
    
    if channel_id in selected: selected.remove(channel_id)
    else: selected.append(channel_id)
    await state.update_data(multi_channels=selected)
    
    channels = await db.get_channels()
    keyboard = [[InlineKeyboardButton(text=f"{'✅' if ch['_id'] in selected else '☐'} {ch['name']}", callback_data=f"multi_{ch['_id']}")] for ch in channels]
    keyboard.append([InlineKeyboardButton(text="✅ Done", callback_data="multi_done")])
    await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "multi_done")
async def multi_done(callback: CallbackQuery, state: FSMContext):
    await state.update_data(send_type="multi")
    await callback.message.reply("confirm please")

@router.message(F.text.lower() == "/confirm")
async def confirm_send(message: Message, state: FSMContext):
    data = await state.get_data()
    send_type = data.get("send_type")
    if not send_type: return
    
    latest_post = await db.get_latest_post()
    if not latest_post: return
    
    btn_text = f"Watch Episode {latest_post['episode_label']}"
    deep_link = f"https://t.me/{BOT_USERNAME}?start=episode_{latest_post['episode_label']}"
    button = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=btn_text, url=deep_link)]])
    
    if send_type == "single":
        await message.bot.copy_message(data["pending_channel"], STORAGE_CHANNEL_ID, latest_post["main_msg_id"], reply_markup=button)
    elif send_type == "multi":
        for ch_id in data.get("multi_channels", []):
            try: await message.bot.copy_message(ch_id, STORAGE_CHANNEL_ID, latest_post["main_msg_id"], reply_markup=button)
            except: pass
            
    await message.reply("✅ Post successfully delivered!")
    await state.clear()

# ==================== SHORTNER ====================
@router.message(F.text.lower() == "/add shortner account")
async def add_shortner_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.reply("provide deskbord url")
    await state.set_state(ShortnerAddState.waiting_url)

@router.message(ShortnerAddState.waiting_url)
async def shortner_url(message: Message, state: FSMContext):
    await state.update_data(url=message.text.strip())
    await message.reply("send your API Token")
    await state.set_state(ShortnerAddState.waiting_token)

@router.message(ShortnerAddState.waiting_token)
async def shortner_token(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.add_shortner(data["url"], message.text.strip())
    await message.reply("successfully add 🤗🤗🤗")
    await state.clear()

@router.message(F.text.lower() == "/remove shortner account")
async def remove_shortner_cmd(message: Message):
    if not is_admin(message.from_user.id): return
    shortners = await db.get_shortners()
    keyboard = [[InlineKeyboardButton(text=f"{s['url'].replace('https://','')} - {s['api'][:4]}...", callback_data=f"rem_short_{s['_id']}")] for s in shortners]
    await message.reply("select account", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("rem_short_"))
async def select_remove_short(callback: CallbackQuery, state: FSMContext):
    await state.update_data(del_shortner_id=callback.data.split("_")[2])
    await callback.message.reply("kya aap hatana chahte hai\ntype /delete")

@router.message(F.text.lower() == "/delete")
async def delete_cmd(message: Message, state: FSMContext):
    data = await state.get_data()
    if "del_shortner_id" in data:
        await db.remove_shortner(data["del_shortner_id"])
        await message.reply("successfully delete account for shortner")
        await state.clear()

# ==================== PREMIUM ====================
@router.message(F.text.lower() == "/add premium")
async def add_prem(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.reply("send I'd")
    await state.set_state(PremiumAddState.waiting_id)

@router.message(PremiumAddState.waiting_id)
async def prem_id(message: Message, state: FSMContext):
    await state.update_data(prem_id=int(message.text.strip()))
    await message.reply("successfully add member\nPleas confirm type /hu hu")

@router.message(F.text.lower() == "/hu hu")
async def confirm_prem(message: Message, state: FSMContext):
    data = await state.get_data()
    if "prem_id" in data:
        await db.add_premium(data["prem_id"])
        await message.reply(f"successfully add member {data['prem_id']} 🪄🪄🪄")
        await state.clear()

@router.message(F.text.lower() == "/remove premium")
async def remove_prem(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.reply("send I'd")
    await state.set_state(PremiumRemoveState.waiting_id)

@router.message(PremiumRemoveState.waiting_id)
async def del_prem(message: Message, state: FSMContext):
    await db.remove_premium(int(message.text.strip()))
    await message.reply("successfully deleted and ban")
    await state.clear()

@router.message(F.text.lower() == "/show premium list")
async def show_premium(message: Message):
    if not is_admin(message.from_user.id): return
    users = await db.get_premium_list()
    text = "🌟 Premium Users:\n\n" + "\n".join([f"• `{u['_id']}` - Exp: {u['premium_expiry'].strftime('%Y-%m-%d')}" for u in users]) if users else "📭 No premium users."
    await message.reply(text)

# ==================== FSUB ====================
@router.message(F.text.lower() == "/force sub")
async def fsub_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.reply("please send massage and chack I'm admin gc")
    await state.set_state(FSUBState.waiting_message)

@router.message(FSUBState.waiting_message)
async def receive_fsub(message: Message, state: FSMContext):
    if message.forward_origin and message.forward_origin.type == "chat":
        chat = message.forward_origin.chat
        await db.add_fsub_channel(chat.id, chat.title)
        await message.reply("😘 adding successfully 😲")
    else:
        await message.reply("Please forward directly from the channel.")
    await state.clear()
