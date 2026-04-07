from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, ADMINISTRATOR

from config import OWNER_ID, ALLOWED_USERS, STORAGE_CHANNEL_ID
from database import db

router = Router()
multi_selected = {}

def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

# ================= AUTO ADD CHANNEL WHEN BOT BECOMES ADMIN =================
@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=ADMINISTRATOR))
async def auto_add_channel(event: ChatMemberUpdated):
    if event.chat.type in ["channel", "supergroup"]:
        await db.add_channel(event.chat.id, event.chat.title)
        print(f"✅ Bot was made admin, Auto-Added Channel: {event.chat.title}")

# ================= MANUAL ADD CHANNEL =================
@router.message(Command("addchannel"))
async def manual_add(message: Message):
    if not is_admin(message.from_user.id): return
    await message.reply("📢 Forward any message from the channel. Make sure I am admin there.")

@router.message(F.forward_from_chat)
async def save_channel_forward(message: Message):
    if not is_admin(message.from_user.id): return
    chat = message.forward_from_chat
    try:
        bot_member = await message.bot.get_chat_member(chat.id, message.bot.id)
        if bot_member.status in ["administrator", "creator"]:
            await db.add_channel(chat.id, chat.title)
            await message.reply(f"✅ Channel added manually:\n{chat.title}")
        else:
            await message.reply("❌ I am not admin in that channel.")
    except:
        await message.reply("❌ Cannot access channel. Make me admin first.")

# ================= SEND COMMANDS =================
@router.message(Command("send"))
async def send_command(message: Message):
    if not is_admin(message.from_user.id): return
    await show_single_list(message)

@router.message(Command("sendmorechannel"))
async def send_more_command(message: Message):
    if not is_admin(message.from_user.id): return
    await show_multi_list(message)

@router.callback_query(F.data == "cmd_send")
async def cb_send(call: CallbackQuery):
    await show_single_list(call.message)
    await call.answer()

@router.callback_query(F.data == "cmd_sendmulti")
async def cb_sendmulti(call: CallbackQuery):
    await show_multi_list(call.message)
    await call.answer()

# ================= LIST LOGIC =================
async def show_single_list(message: Message):
    channels = await db.get_channels()
    if not channels:
        await message.reply("❌ No channels found. Add me as admin in your channel first.")
        return
    kb = []
    for ch in channels:
        kb.append([InlineKeyboardButton(text=ch["name"], callback_data=f"single_{ch['_id']}")])
    await message.reply("📢 Select 1 Channel to send post:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

async def show_multi_list(message: Message):
    channels = await db.get_channels()
    if not channels:
        await message.reply("❌ No channels found. Add me as admin in your channels first.")
        return
    uid = message.from_user.id if hasattr(message.from_user, "id") else message.chat.id
    multi_selected[uid] = []
    
    kb = []
    for ch in channels:
        kb.append([InlineKeyboardButton(text=f"☐ {ch['name']}", callback_data=f"multi_{ch['_id']}")])
    kb.append([InlineKeyboardButton(text="✅ Done", callback_data="multi_done")])
    await message.reply("📢 Select multiple channels:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

# ================= CALLBACKS =================
@router.callback_query(F.data.startswith("single_"))
async def single_selected(call: CallbackQuery):
    cid = int(call.data.split("_")[1])
    await db.save_temp(call.from_user.id, {"send_channel": cid, "send_type": "single"})
    await call.message.reply("✅ Channel selected.\nType `/confirm` to post.")
    await call.answer()

@router.callback_query(F.data.startswith("multi_") & (F.data != "multi_done"))
async def multi_select_toggle(call: CallbackQuery):
    cid = call.data.split("_")[1]
    uid = call.from_user.id
    
    if uid not in multi_selected:
        multi_selected[uid] = []
    if cid in multi_selected[uid]:
        multi_selected[uid].remove(cid)
    else:
        multi_selected[uid].append(cid)

    channels = await db.get_channels()
    kb = []
    for ch in channels:
        checked = "✅" if str(ch["_id"]) in multi_selected[uid] else "☐"
        kb.append([InlineKeyboardButton(text=f"{checked} {ch['name']}", callback_data=f"multi_{ch['_id']}")])
    kb.append([InlineKeyboardButton(text="✅ Done", callback_data="multi_done")])
    
    await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data == "multi_done")
async def multi_done_callback(call: CallbackQuery):
    uid = call.from_user.id
    selected = multi_selected.get(uid, [])
    if not selected:
        await call.message.reply("❌ No channels selected.")
        return
    await db.save_temp(uid, {"send_channels": [int(x) for x in selected], "send_type": "multi"})
    await call.message.reply(f"✅ {len(selected)} channels selected.\nType `/confirm` to post.")
    await call.answer()

# ================= CONFIRM SEND =================
@router.message(Command("confirm"))
async def confirm_send(message: Message):
    uid = message.from_user.id
    if not is_admin(uid): return

    temp = await db.get_temp(uid)
    latest_post = await db.get_latest_post()

    if not latest_post or not temp:
        await message.reply("❌ Missing data. Did you complete the post and select channels?")
        return

    # REBUILD REPLY MARKUP FROM DB SO IT APPEARS IN THE CHANNEL
    markup_dict = latest_post.get("reply_markup")
    markup = InlineKeyboardMarkup(**markup_dict) if markup_dict else None

    success = 0
    targets = []
    if temp.get("send_type") == "single":
        targets.append(temp["send_channel"])
    elif temp.get("send_type") == "multi":
        targets.extend(temp["send_channels"])

    for cid in targets:
        try:
            await message.bot.copy_message(
                chat_id=cid,
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=latest_post["storage_msg_id"],
                reply_markup=markup
            )
            success += 1
        except Exception as e:
            print(f"❌ Send failed for {cid}: {e}")

    await message.reply(f"✅ Successfully sent to {success}/{len(targets)} channels!")
    await db.del_temp(uid)
    if uid in multi_selected:
        del multi_selected[uid]
