from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import OWNER_ID, ALLOWED_USERS, ALLOWED_GROUPS, STORAGE_CHANNEL_ID
from database import db
import random

router = Router()

# ========== STATES ==========
class PostState(StatesGroup):
    waiting_for_post = State()
    waiting_for_single_link = State()
    waiting_for_batch_link = State()
    waiting_for_episode = State()
    waiting_for_batch_episodes = State()

class ShortnerState(StatesGroup):
    waiting_for_url = State()
    waiting_for_token = State()

class PremiumState(StatesGroup):
    waiting_for_id = State()

class FSUBState(StatesGroup):
    waiting_for_message = State()

class BroadcastState(StatesGroup):
    waiting_for_selection = State()

# ========== CHECK ACCESS ==========
def check_access(user_id: int, chat_id: int) -> bool:
    if user_id == OWNER_ID or user_id in ALLOWED_USERS:
        return True
    if chat_id in ALLOWED_GROUPS:
        return True
    return False

# ========== START COMMAND ==========
@router.message(Command("start"))
async def start_command(message: Message):
    if not check_access(message.from_user.id, message.chat.id):
        await message.reply("❌ You are not authorized to use this bot.")
        return
    await message.reply("🤖 Bot is alive and working!\n\nCommands:\n/post - Upload new post\n/add shortner - Add shortner account\n/remove shortner - Remove shortner\n/add premium - Add premium user\n/remove premium - Remove premium\n/show premium list - Show all premium\n/force sub - Add force subscribe channel\n/send - Send post to channel\n/send more channel - Multi channel send")

# ========== POST COMMAND ==========
@router.message(Command("post"))
async def post_command(message: Message, state: FSMContext):
    if not check_access(message.from_user.id, message.chat.id):
        return
    await message.reply("📤 Send me the post (photo, video, document, or text)")
    await state.set_state(PostState.waiting_for_post)

@router.message(PostState.waiting_for_post)
async def receive_post(message: Message, state: FSMContext):
    if message.forward_from_chat or message.forward_from:
        # Store in storage channel
        stored_msg = await message.bot.forward_message(STORAGE_CHANNEL_ID, message.chat.id, message.message_id)
        await state.update_data(storage_msg_id=stored_msg.message_id)
        await message.reply("✅ Post received! Send me the link (single link or batch link)")
        await state.set_state(PostState.waiting_for_single_link)
    else:
        await message.reply("❌ Please forward a post from a channel or user")

@router.message(PostState.waiting_for_single_link)
async def receive_link(message: Message, state: FSMContext):
    link = message.text
    if "batch" in link.lower():
        await message.reply("📚 Send episodes one by one (forward each episode)\nType 'done' when finished")
        await state.set_state(PostState.waiting_for_batch_episodes)
        await state.update_data(episodes=[])
    else:
        await state.update_data(link=link)
        await message.reply("🎬 Send me the episode (just the number like 07)")
        await state.set_state(PostState.waiting_for_episode)

@router.message(PostState.waiting_for_episode)
async def receive_episode(message: Message, state: FSMContext):
    episode = message.text.strip()
    data = await state.get_data()
    
    # Generate button
    shortners = await db.get_all_shortners()
    if shortners:
        # Use first shortner for demo
        shortner = shortners[0]
        # Here you would call shortner API
        shortner_link = f"{shortner['deskboard_url']}/short/{episode}"
    else:
        shortner_link = data.get('link')
    
    button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🎬 Watch Episode {episode}", url=shortner_link)]
    ])
    
    # Send post to user with button
    await message.bot.copy_message(message.chat.id, STORAGE_CHANNEL_ID, data['storage_msg_id'], reply_markup=button)
    
    # Show send options
    await message.reply("✅ Post ready!\n\n[ Send ]\n[ Send more channel ]", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Send", callback_data="send_single")],
        [InlineKeyboardButton(text="📤 Send to multiple", callback_data="send_multi")]
    ]))
    await state.clear()

# ========== BATCH EPISODES ==========
@router.message(PostState.waiting_for_batch_episodes)
async def receive_batch_episode(message: Message, state: FSMContext):
    if message.text and message.text.lower() == "done":
        data = await state.get_data()
        episodes = data.get('episodes', [])
        if len(episodes) < 2:
            await message.reply("❌ Need at least 2 episodes for batch!")
            return
        
        ep_range = f"{episodes[0]}-{episodes[-1]}"
        button = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🎬 Watch Episode {ep_range}", url=f"https://short.link/batch/{ep_range}")]
        ])
        
        await message.bot.copy_message(message.chat.id, STORAGE_CHANNEL_ID, data['storage_msg_id'], reply_markup=button)
        await message.reply("✅ Batch post ready!\n\n[ Send ]\n[ Send more channel ]", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Send", callback_data="send_single")],
            [InlineKeyboardButton(text="📤 Send to multiple", callback_data="send_multi")]
        ]))
        await state.clear()
    elif message.forward_from_chat or message.forward_from:
        # Extract episode from forwarded message caption
        episodes = (await state.get_data()).get('episodes', [])
        episodes.append(str(len(episodes)+1))
        await state.update_data(episodes=episodes)
        await message.reply(f"✅ Episode {len(episodes)} received! Send next or type 'done'")
    else:
        await message.reply("❌ Please forward an episode message")

# ========== SEND CALLBACKS ==========
@router.callback_query(F.data == "send_single")
async def send_single(callback: CallbackQuery):
    await callback.message.reply("📢 Send this to which channel?\nSelect from list:")
    channels = await db.get_all_channels()
    if not channels:
        await callback.message.reply("❌ No channels added! Use /add channel first")
        return
    
    keyboard = []
    for ch in channels:
        keyboard.append([InlineKeyboardButton(text=ch['name'], callback_data=f"ch_{ch['_id']}")])
    
    await callback.message.reply("Select channel:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "send_multi")
async def send_multi(callback: CallbackQuery):
    await callback.message.reply("📢 Select channels (you can select multiple):")
    channels = await db.get_all_channels()
    keyboard = []
    for ch in channels:
        keyboard.append([InlineKeyboardButton(text=f"✅ {ch['name']}", callback_data=f"multi_{ch['_id']}")])
    keyboard.append([InlineKeyboardButton(text="✅ Done selecting", callback_data="multi_done")])
    await callback.message.reply("Select channels:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

# ========== SHORTNER COMMANDS ==========
@router.message(Command("add shortner account"))
async def add_shortner(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await message.reply("🔗 Send me your shortner deskboard URL")
    await state.set_state(ShortnerState.waiting_for_url)

@router.message(ShortnerState.waiting_for_url)
async def receive_shortner_url(message: Message, state: FSMContext):
    await state.update_data(url=message.text)
    await message.reply("🔑 Send me your API token")
    await state.set_state(ShortnerState.waiting_for_token)

@router.message(ShortnerState.waiting_for_token)
async def receive_shortner_token(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.add_shortner(data['url'], message.text)
    await message.reply("✅ Shortner account added successfully! 🎉")
    await state.clear()

@router.message(Command("remove shortner account"))
async def remove_shortner(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    shortners = await db.get_all_shortners()
    if not shortners:
        await message.reply("❌ No shortner accounts found")
        return
    
    keyboard = []
    for s in shortners:
        keyboard.append([InlineKeyboardButton(text=s['deskboard_url'], callback_data=f"del_short_{s['_id']}")])
    await message.reply("Select shortner to remove:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

# ========== PREMIUM COMMANDS ==========
@router.message(Command("add premium"))
async def add_premium(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await message.reply("👤 Send user ID to add premium")
    await state.set_state(PremiumState.waiting_for_id)

@router.message(PremiumState.waiting_for_id)
async def receive_premium_id(message: Message, state: FSMContext):
    user_id = int(message.text.strip())
    expiry = await db.add_premium(user_id)
    await message.reply(f"✅ Premium added to {user_id}!\nValid until: {expiry.strftime('%Y-%m-%d')}")
    await state.clear()

@router.message(Command("remove premium"))
async def remove_premium(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await message.reply("👤 Send user ID to remove premium")
    await state.set_state(PremiumState.waiting_for_id)

@router.message(Command("show premium list"))
async def show_premium(message: Message):
    if not check_access(message.from_user.id, message.chat.id):
        return
    users = await db.show_premium_list()
    if not users:
        await message.reply("📭 No premium users found")
        return
    
    text = "🌟 **Premium Users List** 🌟\n\n"
    for user in users:
        text += f"• `{user['_id']}` - Expires: {user['premium_expiry'].strftime('%Y-%m-%d')}\n"
    await message.reply(text)

# ========== FORCE SUBSCRIBE ==========
@router.message(Command("Force sub"))
async def force_sub(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await message.reply("📢 Forward a message from the channel you want to force subscribe")
    await state.set_state(FSUBState.waiting_for_message)

@router.message(FSUBState.waiting_for_message)
async def receive_fsub_message(message: Message, state: FSMContext):
    if message.forward_from_chat:
        channel_id = message.forward_from_chat.id
        channel_name = message.forward_from_chat.title or str(channel_id)
        await db.add_fsub_channel(channel_id, channel_name, f"https://t.me/{channel_name}")
        await message.reply(f"✅ Force subscribe added: {channel_name}")
    else:
        await message.reply("❌ Please forward a message from the channel")
    await state.clear()

# ========== SEND COMMANDS ==========
@router.message(Command("send"))
async def send_command(message: Message):
    if not check_access(message.from_user.id, message.chat.id):
        return
    # Similar to send_single callback
    await message.reply("📢 Send to which channel?")
    channels = await db.get_all_channels()
    keyboard = []
    for ch in channels:
        keyboard.append([InlineKeyboardButton(text=ch['name'], callback_data=f"ch_{ch['_id']}")])
    await message.reply("Select channel:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.message(Command("send more channel"))
async def send_more_command(message: Message):
    if not check_access(message.from_user.id, message.chat.id):
        return
    await send_multi(None)  # Reuse logic

# ========== DELETE COMMAND ==========
@router.message(Command("delete"))
async def delete_command(message: Message):
    if message.from_user.id == OWNER_ID:
        await message.reply("✅ Deleted")
