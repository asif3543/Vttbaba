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

# Store multi-selected channels temporarily
multi_selected = {}

# ==================== STATES ====================
class PostState(StatesGroup):
    waiting_post = State()
    waiting_link_type = State()
    waiting_single_episode = State()
    waiting_batch_episode = State()
    waiting_batch_range = State()

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

# ==================== SHORTNER API CALL ====================
async def create_shortlink(shortner: dict, original_url: str) -> str:
    """Generate short link using shortner API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                shortner["url"],
                json={"api": shortner["api"], "url": original_url},
                timeout=10
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Common response formats
                    return data.get("short_url") or data.get("shortened_url") or data.get("shortlink") or original_url
    except Exception as e:
        print(f"Shortner failed: {e}")
    return original_url

# ==================== SEND EPISODE TO USER ====================
async def send_episode_to_user(message: Message, user_id: int, episode: str):
    # Check if banned
    if await db.is_banned(user_id):
        await message.reply("❌ You are banned from using this bot.")
        return
    
    # Check premium
    if await db.is_premium(user_id):
        post = await db.get_post_by_episode(episode)
        if post:
            await message.bot.copy_message(
                user_id,
                STORAGE_CHANNEL_ID,
                post["storage_msg_id"]
            )
        else:
            await message.reply("❌ Episode not found.")
        return
    
    # Check force subscribe for free users
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
        keyboard = []
        for ch in not_joined:
            keyboard.append([InlineKeyboardButton(text=f"📢 Join {ch['name']}", url=ch["link"])])
        keyboard.append([InlineKeyboardButton(text="✅ Try Again", callback_data=f"retry_{episode}")])
        
        await message.reply(
            "❌ Join channels first to access episodes:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        return
    
    # Free user - send shortner link
    shortner = await db.get_random_shortner()
    if shortner:
        original_url = f"https://t.me/{BOT_USERNAME}?start=episode_{episode}"
        short_url = await create_shortlink(shortner, original_url)
        
        await message.reply(
            f"🔗 Please solve the shortner to get episode:\n{short_url}\n\n"
            f"After solving, you'll get the episode automatically."
        )
    else:
        # No shortner account - direct link
        await message.reply(
            f"🎬 Click below to get episode:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Get Episode", url=f"https://t.me/{BOT_USERNAME}?start=episode_{episode}")]
            ])
        )

# ==================== /start ====================
@router.message(Command("start"))
async def start_cmd(message: Message):
    user_id = message.from_user.id
    args = message.text.split()
    
    # Deep link - user clicked on button
    if len(args) > 1 and args[1].startswith("episode_"):
        episode = args[1].replace("episode_", "")
        await send_episode_to_user(message, user_id, episode)
        return
    
    # Normal start
    await message.reply(
        "🤖 Bot is alive!\n\n"
        "📌 **Admin Commands:**\n"
        "/post - Upload new post\n"
        "/add shortner account - Add shortner account\n"
        "/remove shortner account - Remove shortner\n"
        "/add premium - Add premium user (28 days)\n"
        "/remove premium - Remove premium user\n"
        "/show premium list - Show all premium users\n"
        "/Force sub - Add force subscribe channel\n"
        "/send - Send post to single channel\n"
        "/send more channel - Send post to multiple channels\n\n"
        "📌 **Premium Users:** Direct episode access without shortner\n"
        "📌 **Free Users:** Solve shortner → Join channels → Get episode"
    )

# ==================== /post ====================
@router.message(Command("post"))
async def post_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("❌ Only admin can use this command.")
        return
    await message.reply("📤 Send post")
    await state.set_state(PostState.waiting_post)

@router.message(PostState.waiting_post)
async def receive_post(message: Message, state: FSMContext):
    if message.forward_from_chat or message.forward_from:
        stored = await message.bot.forward_message(STORAGE_CHANNEL_ID, message.chat.id, message.message_id)
        await db.save_temp_post(message.from_user.id, {
            "storage_msg_id": stored.message_id,
            "step": "post_received"
        })
        await message.reply("✅ Post successfully received\nPlease provide single link or batch link")
        await state.set_state(PostState.waiting_link_type)
    else:
        await message.reply("❌ Please forward a post from a channel or user")

@router.message(PostState.waiting_link_type)
async def receive_link_type(message: Message, state: FSMContext):
    text = message.text.lower()
    temp = await db.get_temp_post(message.from_user.id)
    
    if "batch" in text:
        await db.save_temp_post(message.from_user.id, {**temp, "link_type": "batch"})
        await message.reply("📚 Send episode")
        await state.set_state(PostState.waiting_batch_episode)
    else:
        await db.save_temp_post(message.from_user.id, {**temp, "link_type": "single"})
        await message.reply("🎬 Send episode")
        await state.set_state(PostState.waiting_single_episode)

@router.message(PostState.waiting_single_episode)
async def receive_single_episode(message: Message, state: FSMContext):
    episode = message.text.strip()
    temp = await db.get_temp_post(message.from_user.id)
    await db.save_temp_post(message.from_user.id, {**temp, "episode": episode})
    await message.reply(f"✅ Episode {episode}\n/confirm")
    await state.clear()

@router.message(PostState.waiting_batch_episode)
async def receive_batch_episode(message: Message, state: FSMContext):
    temp = await db.get_temp_post(message.from_user.id)
    episodes = temp.get("batch_episodes", [])
    
    if message.forward_from_chat or message.forward_from:
        episodes.append(message.message_id)
        await db.save_temp_post(message.from_user.id, {**temp, "batch_episodes": episodes})
        await message.reply(f"✅ Episode {len(episodes)} received\nSend next episode or type 'done'")
    elif message.text and message.text.lower() == "done":
        if len(episodes) < 2:
            await message.reply("❌ Need at least 2 episodes! Send more.")
            return
        await message.reply("✅ Batch successfully adding\nEnter number range (example: 05-15)")
        await state.set_state(PostState.waiting_batch_range)
    else:
        await message.reply("❌ Please forward an episode message")

@router.message(PostState.waiting_batch_range)
async def receive_batch_range(message: Message, state: FSMContext):
    ep_range = message.text.strip()
    temp = await db.get_temp_post(message.from_user.id)
    await db.save_temp_post(message.from_user.id, {**temp, "batch_range": ep_range})
    await message.reply(f"✅ Range: {ep_range}\n/confirm")
    await state.clear()

# ==================== /confirm & /hmm ====================
@router.message(Command("confirm"))
@router.message(Command("hmm"))
async def confirm_post(message: Message, state: FSMContext):
    temp = await db.get_temp_post(message.from_user.id)
    if not temp:
        await message.reply("❌ No pending post. Use /post first.")
        return
    
    # Generate shortner link for button
    shortner = await db.get_random_shortner()
    shortner_link = None
    
    if temp.get("link_type") == "batch":
        episode_value = temp.get("batch_range", "1")
        btn_text = f"🎬 Watch Episode {episode_value}"
    else:
        episode_value = temp.get("episode", "1")
        btn_text = f"🎬 Watch Episode {episode_value}"
    
    original_url = f"https://t.me/{BOT_USERNAME}?start=episode_{episode_value}"
    
    if shortner:
        shortner_link = await create_shortlink(shortner, original_url)
    else:
        shortner_link = original_url
    
    # Create button
    button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_text, url=shortner_link)]
    ])
    
    # Send post with button
    await message.bot.copy_message(
        message.chat.id,
        STORAGE_CHANNEL_ID,
        temp["storage_msg_id"],
        reply_markup=button
    )
    
    # Save post to database
    await db.save_post({
        "user_id": message.from_user.id,
        "storage_msg_id": temp["storage_msg_id"],
        "link_type": temp.get("link_type"),
        "episode": temp.get("episode"),
        "batch_range": temp.get("batch_range"),
        "shortner_link": shortner_link,
        "created_at": datetime.utcnow()
    })
    
    # Show send options
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Send", callback_data="send_single")],
        [InlineKeyboardButton(text="📤 Send more channel", callback_data="send_multi")]
    ])
    await message.reply("[ Send ]\n[ Send more channel]", reply_markup=keyboard)
    await db.delete_temp_post(message.from_user.id)

# ==================== SEND TO SINGLE CHANNEL ====================
@router.callback_query(F.data == "send_single")
async def send_single_option(callback: CallbackQuery):
    channels = await db.get_channels()
    
    if not channels:
        await callback.message.reply("❌ Bot is not admin in any channel! Add channels to database first.")
        return
    
    keyboard = []
    for ch in channels:
        keyboard.append([InlineKeyboardButton(text=ch["name"], callback_data=f"single_{ch['_id']}")])
    
    await callback.message.reply(
        "📢 Select channel to send:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data.startswith("single_"))
async def send_to_single_channel(callback: CallbackQuery):
    channel_id = int(callback.data.split("_")[1])
    await db.save_temp_post(callback.from_user.id, {"pending_channel": channel_id, "send_type": "single"})
    await callback.message.reply("confirm please")

# ==================== SEND TO MULTIPLE CHANNELS ====================
@router.callback_query(F.data == "send_multi")
async def send_multi_option(callback: CallbackQuery):
    channels = await db.get_channels()
    
    if not channels:
        await callback.message.reply("❌ Bot is not admin in any channel! Add channels to database first.")
        return
    
    keyboard = []
    for ch in channels:
        keyboard.append([InlineKeyboardButton(text=f"☐ {ch['name']}", callback_data=f"multi_{ch['_id']}")])
    keyboard.append([InlineKeyboardButton(text="✅ Done", callback_data="multi_done")])
    
    await callback.message.reply(
        "📢 Select channels (tap to select, then Done):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data.startswith("multi_") & ~F.data == "multi_done")
async def multi_select_channel(callback: CallbackQuery):
    channel_id = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    if user_id not in multi_selected:
        multi_selected[user_id] = []
    
    if channel_id in multi_selected[user_id]:
        multi_selected[user_id].remove(channel_id)
        await callback.answer("Removed")
    else:
        multi_selected[user_id].append(channel_id)
        await callback.answer("Added")
    
    # Refresh keyboard
    channels = await db.get_channels()
    keyboard = []
    for ch in channels:
        checked = "✅" if str(ch['_id']) in multi_selected[user_id] else "☐"
        keyboard.append([InlineKeyboardButton(text=f"{checked} {ch['name']}", callback_data=f"multi_{ch['_id']}")])
    keyboard.append([InlineKeyboardButton(text="✅ Done", callback_data="multi_done")])
    
    await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "multi_done")
async def multi_done_selection(callback: CallbackQuery):
    user_id = callback.from_user.id
    selected = multi_selected.get(user_id, [])
    
    if not selected:
        await callback.message.reply("❌ No channels selected!")
        return
    
    await db.save_temp_post(user_id, {"pending_channels": selected, "send_type": "multi"})
    await callback.message.reply(f"✅ {len(selected)} channel(s) selected\nconfirm please")

# ==================== FINAL CONFIRM FOR SEND ====================
@router.message(Command("confirm"))
async def confirm_send(message: Message):
    temp = await db.get_temp_post(message.from_user.id)
    latest_post = await db.get_latest_post()
    
    if not latest_post:
        await message.reply("❌ No post found to send. Create a post first with /post")
        return
    
    # Single channel send
    if temp.get("send_type") == "single" and temp.get("pending_channel"):
        try:
            await message.bot.copy_message(
                chat_id=temp["pending_channel"],
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=latest_post["storage_msg_id"],
                reply_markup=latest_post.get("reply_markup")
            )
            await message.reply("✅ Post delivered to channel!")
        except Exception as e:
            await message.reply(f"❌ Failed: {e}")
    
    # Multiple channels send
    elif temp.get("send_type") == "multi" and temp.get("pending_channels"):
        success = 0
        failed = 0
        
        for ch_id in temp["pending_channels"]:
            try:
                await message.bot.copy_message(
                    chat_id=int(ch_id),
                    from_chat_id=STORAGE_CHANNEL_ID,
                    message_id=latest_post["storage_msg_id"],
                    reply_markup=latest_post.get("reply_markup")
                )
                success += 1
            except Exception as e:
                failed += 1
                print(f"Failed to send to {ch_id}: {e}")
        
        await message.reply(f"✅ Delivered to {success} channels.\n❌ Failed: {failed}")
    else:
        await message.reply("❌ No channel selected. Use /send or /send more channel first.")
    
    # Clean up
    await db.delete_temp_post(message.from_user.id)
    if message.from_user.id in multi_selected:
        del multi_selected[message.from_user.id]

# ==================== /send COMMAND ====================
@router.message(Command("send"))
async def send_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    await send_single_option(message)  # Reuse same logic

# ==================== /send more channel COMMAND ====================
@router.message(Command("send more channel"))
async def send_more_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    await send_multi_option(message)  # Reuse same logic

# ==================== SHORTNER ACCOUNT ====================
@router.message(Command("add shortner account"))
async def add_shortner_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply("🔗 Provide deskboard URL")
    await state.set_state(ShortnerAddState.waiting_url)

@router.message(ShortnerAddState.waiting_url)
async def shortner_url(message: Message, state: FSMContext):
    await state.update_data(url=message.text)
    await message.reply("🔑 Send your API Token")
    await state.set_state(ShortnerAddState.waiting_token)

@router.message(ShortnerAddState.waiting_token)
async def shortner_token(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.add_shortner(data["url"], message.text)
    await message.reply("✅ Shortner account successfully added! 🤗🤗🤗")
    await state.clear()

@router.message(Command("remove shortner account"))
async def remove_shortner_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    shortners = await db.get_shortners()
    if not shortners:
        await message.reply("❌ No shortner accounts found.")
        return
    
    keyboard = []
    for s in shortners:
        keyboard.append([InlineKeyboardButton(text=s["url"], callback_data=f"rem_{s['_id']}")])
    
    await message.reply("Select account to remove:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("rem_"))
async def select_remove(callback: CallbackQuery, state: FSMContext):
    shortner_id = callback.data.split("_")[1]
    await state.update_data(shortner_id=shortner_id)
    await callback.message.reply("क्या आप हटाना चाहते हैं?\nType /delete")

@router.message(Command("delete"))
async def delete_shortner(message: Message, state: FSMContext):
    data = await state.get_data()
    shortner_id = data.get("shortner_id")
    if shortner_id:
        await db.remove_shortner(shortner_id)
        await message.reply("✅ Successfully deleted shortner account!")
    else:
        await message.reply("❌ No shortner selected.")
    await state.clear()

# ==================== PREMIUM SYSTEM ====================
@router.message(Command("add premium"))
async def add_premium_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply("Send user ID")
    await state.set_state(PremiumAddState.waiting_id)

@router.message(PremiumAddState.waiting_id)
async def premium_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        await state.update_data(premium_user=user_id)
        await message.reply("✅ Successfully add member\nPlease confirm type /hu hu")
    except:
        await message.reply("❌ Invalid user ID. Send a number.")

@router.message(Command("hu hu"))
async def confirm_premium(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("premium_user")
    if user_id:
        expiry = await db.add_premium(user_id)
        await message.reply(f"✅ Successfully add member {user_id} 🪄🪄🪄\nValid until: {expiry.strftime('%Y-%m-%d')}")
    else:
        await message.reply("❌ No user ID found. Use /add premium first.")
    await state.clear()

@router.message(Command("remove premium"))
async def remove_premium_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply("Send user ID")
    await state.set_state(PremiumRemoveState.waiting_id)

@router.message(PremiumRemoveState.waiting_id)
async def remove_premium_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        await db.remove_premium(user_id)
        await message.reply(f"✅ Successfully deleted and banned\nUser {user_id} cannot use bot anymore.")
    except:
        await message.reply("❌ Invalid user ID.")
    await state.clear()

@router.message(Command("show premium list"))
async def show_premium(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    users = await db.get_premium_list()
    if not users:
        await message.reply("📭 No premium users.")
        return
    
    text = "🌟 Premium Users:\n\n"
    for user in users:
        text += f"• `{user['_id']}` - Expires: {user['premium_expiry'].strftime('%Y-%m-%d')}\n"
    await message.reply(text)

# ==================== FORCE SUBSCRIBE ====================
@router.message(Command("Force sub"))
async def force_sub_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply("Please send message and check I'm admin in channel")
    await state.set_state(FSUBState.waiting_message)

@router.message(FSUBState.waiting_message)
async def receive_fsub(message: Message, state: FSMContext):
    if message.forward_from_chat:
        channel_id = message.forward_from_chat.id
        channel_name = message.forward_from_chat.title or str(channel_id)
        await db.add_fsub_channel(channel_id, channel_name)
        await message.reply(f"😘 Adding successfully 😲\n{channel_name}")
    else:
        await message.reply("❌ Please forward a message from the channel.")
    await state.clear()

# ==================== RETRY CALLBACK ====================
@router.callback_query(F.data.startswith("retry_"))
async def retry_episode(callback: CallbackQuery):
    episode = callback.data.split("_")[1]
    await send_episode_to_user(callback.message, callback.from_user.id, episode)
    await callback.answer()
