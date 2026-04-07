from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from config import OWNER_ID, ALLOWED_USERS, STORAGE_CHANNEL_ID
from database import db

router = Router()

multi_selected = {}

# ================= ADMIN CHECK =================
def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

# ================= ADD CHANNEL =================
@router.message(Command("addchannel"))
async def add_channel_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.reply(
        "📢 Forward any message from the channel.\n"
        "Make sure I am admin there."
    )

@router.message(F.forward_from_chat)
async def save_channel_forward(message: Message):
    if not is_admin(message.from_user.id):
        return
    chat = message.forward_from_chat
    try:
        bot_member = await message.bot.get_chat_member(chat.id, message.bot.id)
        if bot_member.status not in ["administrator", "creator"]:
            await message.reply("❌ I am not admin in that channel.")
            return
    except:
        await message.reply("❌ Cannot access that channel.")
        return

    await db.add_channel(chat.id, chat.title)
    await message.reply(f"✅ Channel added:\n{chat.title}")

# ================= SEND SINGLE =================
@router.message(Command("send"))
async def send_command(message: Message):
    if not is_admin(message.from_user.id):
        return
    channels = await db.get_channels()
    if not channels:
        await message.reply("❌ No channels found.\nUse /addchannel first.")
        return
    keyboard = []
    for ch in channels:
        keyboard.append([
            InlineKeyboardButton(text=ch["name"], callback_data=f"single_{ch['_id']}")
        ])
    await message.reply(
        "📢 Select channel:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

# ================= SEND MULTI =================
@router.message(Command("sendmorechannel"))
async def send_more_command(message: Message):
    if not is_admin(message.from_user.id):
        return
    channels = await db.get_channels()
    if not channels:
        await message.reply("❌ No channels found.\nUse /addchannel first.")
        return
    uid = message.from_user.id
    multi_selected[uid] = []
    keyboard = []
    for ch in channels:
        keyboard.append([
            InlineKeyboardButton(text=f"☐ {ch['name']}", callback_data=f"multi_{ch['_id']}")
        ])
    keyboard.append([
        InlineKeyboardButton(text="✅ Done", callback_data="multi_done")
    ])
    await message.reply(
        "Select channels:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

# ================= SINGLE SELECT =================
@router.callback_query(F.data.startswith("single_"))
async def single_channel_selected(callback: CallbackQuery):
    channel_id = int(callback.data.split("_")[1])
    await db.save_temp(callback.from_user.id, {
        "send_channel": channel_id,
        "send_type": "single"
    })
    await callback.message.reply("✅ Channel selected.\nType `/confirm`")
    await callback.answer()

# ================= MULTI SELECT =================
@router.callback_query(F.data.startswith("multi_") & (F.data != "multi_done"))
async def multi_select_toggle(callback: CallbackQuery):
    cid = callback.data.split("_")[1]
    uid = callback.from_user.id
    if uid not in multi_selected:
        multi_selected[uid] = []
    if cid in multi_selected[uid]:
        multi_selected[uid].remove(cid)
        await callback.answer("Removed")
    else:
        multi_selected[uid].append(cid)
        await callback.answer("Added")

    channels = await db.get_channels()
    keyboard = []
    for ch in channels:
        checked = "✅" if str(ch["_id"]) in multi_selected[uid] else "☐"
        keyboard.append([
            InlineKeyboardButton(text=f"{checked} {ch['name']}", callback_data=f"multi_{ch['_id']}")
        ])
    keyboard.append([
        InlineKeyboardButton(text="✅ Done", callback_data="multi_done")
    ])
    await callback.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data == "multi_done")
async def multi_done_callback(callback: CallbackQuery):
    uid = callback.from_user.id
    selected = multi_selected.get(uid)
    if not selected:
        await callback.message.reply("❌ No channels selected.")
        return
    selected_int = [int(x) for x in selected]
    await db.save_temp(uid, {
        "send_channels": selected_int,
        "send_type": "multi"
    })
    await callback.message.reply(f"✅ {len(selected)} channel(s) selected.\nType `/confirm`")
    await callback.answer()

# ================= CONFIRM SEND =================
@router.message(Command("confirm"))
async def confirm_send(message: Message):
    uid = message.from_user.id
    temp = await db.get_temp(uid)
    latest_post = await db.get_latest_post()

    if not latest_post:
        await message.reply("❌ No post found.")
        return
    if not temp:
        await message.reply("❌ No channel selected.")
        return

    # Restore reply_markup safely
    reply_markup = None
    if latest_post.get("reply_markup"):
        try:
            reply_markup = InlineKeyboardMarkup(**latest_post["reply_markup"])
        except Exception as e:
            print("Markup restore error:", e)

    # SINGLE SEND
    if temp.get("send_type") == "single":
        try:
            await message.bot.copy_message(
                chat_id=temp["send_channel"],
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=latest_post["storage_msg_id"],
                reply_markup=reply_markup
            )
            await message.reply("✅ Post sent successfully!")
        except Exception as e:
            await message.reply(f"❌ Failed:\n{e}")

    # MULTI SEND
    elif temp.get("send_type") == "multi":
        success = 0
        total = len(temp["send_channels"])
        for cid in temp["send_channels"]:
            try:
                await message.bot.copy_message(
                    chat_id=cid,
                    from_chat_id=STORAGE_CHANNEL_ID,
                    message_id=latest_post["storage_msg_id"],
                    reply_markup=reply_markup
                )
                success += 1
            except Exception as e:
                print(f"Send failed {cid}: {e}")
        await message.reply(f"✅ Sent to {success}/{total} channels")

    # Cleanup
    await db.del_temp(uid)
    if uid in multi_selected:
        del multi_selected[uid]
