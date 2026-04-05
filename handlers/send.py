from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_ID, ALLOWED_USERS, STORAGE_CHANNEL_ID
from database import db

router = Router()

# Global temporary storage for multi‑channel selections (user_id -> list of channel _ids)
multi_selected = {}

def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS


# ------------------- /send (single channel) -------------------
@router.message(Command("send"))
async def send_command(message: Message):
    if not is_admin(message.from_user.id):
        return

    channels = await db.get_channels()
    if not channels:
        await message.reply("❌ No channels found. Add channels to database first.")
        return

    keyboard = [
        [InlineKeyboardButton(text=ch["name"], callback_data=f"single_{ch['_id']}")]
        for ch in channels
    ]
    await message.reply("📢 Select channel to send the post:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


# ------------------- /sendmorechannel (multiple channels) -------------------
@router.message(Command("sendmorechannel"))
async def send_more_command(message: Message):
    if not is_admin(message.from_user.id):
        return

    channels = await db.get_channels()
    if not channels:
        await message.reply("❌ No channels found.")
        return

    uid = message.from_user.id
    multi_selected[uid] = []  # reset selection for this user

    keyboard = []
    for ch in channels:
        keyboard.append([InlineKeyboardButton(text=f"☐ {ch['name']}", callback_data=f"multi_{ch['_id']}")])
    keyboard.append([InlineKeyboardButton(text="✅ Done", callback_data="multi_done")])

    await message.reply("Select channels (tap to select, tap again to remove):", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


# ------------------- CALLBACK: single channel selection (from /send or send_single) -------------------
@router.callback_query(F.data == "send_single")
async def send_single_callback(callback: CallbackQuery):
    channels = await db.get_channels()
    if not channels:
        await callback.message.reply("❌ No channels found.")
        return

    keyboard = [
        [InlineKeyboardButton(text=ch["name"], callback_data=f"single_{ch['_id']}")]
        for ch in channels
    ]
    await callback.message.reply("📢 Select channel:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()


@router.callback_query(F.data.startswith("single_"))
async def single_channel_selected(callback: CallbackQuery):
    channel_id = int(callback.data.split("_")[1])
    await db.save_temp(callback.from_user.id, {
        "send_channel": channel_id,
        "send_type": "single"
    })
    await callback.message.reply(f"✅ Channel selected.\nType `/confirm` to send the post.")
    await callback.answer()


# ------------------- CALLBACK: multi‑channel selection (toggle) -------------------
@router.callback_query(F.data.startswith("multi_") & (F.data != "multi_done"))
async def multi_select_toggle(callback: CallbackQuery):
    cid_str = callback.data.split("_")[1]  # channel _id as string
    uid = callback.from_user.id

    if uid not in multi_selected:
        multi_selected[uid] = []

    if cid_str in multi_selected[uid]:
        multi_selected[uid].remove(cid_str)
        await callback.answer("Removed")
    else:
        multi_selected[uid].append(cid_str)
        await callback.answer("Added")

    # Refresh the keyboard with updated checkmarks
    channels = await db.get_channels()
    keyboard = []
    for ch in channels:
        checked = "✅" if str(ch['_id']) in multi_selected[uid] else "☐"
        keyboard.append([InlineKeyboardButton(text=f"{checked} {ch['name']}", callback_data=f"multi_{ch['_id']}")])
    keyboard.append([InlineKeyboardButton(text="✅ Done", callback_data="multi_done")])

    await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@router.callback_query(F.data == "multi_done")
async def multi_done_callback(callback: CallbackQuery):
    uid = callback.from_user.id
    selected = multi_selected.get(uid, [])

    if not selected:
        await callback.message.reply("❌ No channels selected. Please select at least one.")
        return

    # Convert string _ids to integers (or keep as strings, but DB expects int? We'll store as int)
    selected_int = [int(x) for x in selected]
    await db.save_temp(uid, {
        "send_channels": selected_int,
        "send_type": "multi"
    })
    await callback.message.reply(f"✅ {len(selected)} channel(s) selected.\nType `/confirm` to send.")
    await callback.answer()


# ------------------- /confirm : actually send the post -------------------
@router.message(Command("confirm"))
async def confirm_send(message: Message):
    temp = await db.get_temp(message.from_user.id)
    latest_post = await db.get_latest_post()

    if not latest_post:
        await message.reply("❌ No post found. Create a post using `/post` first.")
        return

    if not temp:
        await message.reply("❌ No channel selected. Use `/send` or `/sendmorechannel` first.")
        return

    # Single channel send
    if temp.get("send_type") == "single" and temp.get("send_channel"):
        try:
            await message.bot.copy_message(
                chat_id=temp["send_channel"],
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=latest_post["storage_msg_id"],
                reply_markup=latest_post.get("reply_markup")  # preserves button if any
            )
            await message.reply("✅ Post delivered to the channel!")
        except Exception as e:
            await message.reply(f"❌ Failed to send: {e}")

    # Multi channel send
    elif temp.get("send_type") == "multi" and temp.get("send_channels"):
        success = 0
        for cid in temp["send_channels"]:
            try:
                await message.bot.copy_message(
                    chat_id=int(cid),
                    from_chat_id=STORAGE_CHANNEL_ID,
                    message_id=latest_post["storage_msg_id"],
                    reply_markup=latest_post.get("reply_markup")
                )
                success += 1
            except Exception as e:
                print(f"Failed to send to {cid}: {e}")
        await message.reply(f"✅ Post delivered to {success} out of {len(temp['send_channels'])} channel(s).")

    else:
        await message.reply("❌ Invalid selection. Use /send or /sendmorechannel again.")

    # Clean up temporary data and multi_selected
    await db.del_temp(message.from_user.id)
    if message.from_user.id in multi_selected:
        del multi_selected[message.from_user.id]
