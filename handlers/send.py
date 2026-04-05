from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from config import OWNER_ID, ALLOWED_USERS, STORAGE_CHANNEL_ID
from database import db

router = Router()
multi_selected = {}

def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

@router.message(Command("send"))
async def send_command(message: Message):
    if not is_admin(message.from_user.id):
        return
    channels = await db.get_channels()
    if not channels:
        await message.reply("❌ No channels found. Add channels to database first.")
        return
    keyboard = []
    for ch in channels:
        keyboard.append([InlineKeyboardButton(text=ch["name"], callback_data=f"single_{ch['_id']}")])
    await message.reply("📢 Select channel:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.message(Command("sendmorechannel"))
async def send_more_command(message: Message):
    if not is_admin(message.from_user.id):
        return
    channels = await db.get_channels()
    if not channels:
        await message.reply("❌ No channels found")
        return
    keyboard = []
    for ch in channels:
        keyboard.append([InlineKeyboardButton(text=f"☐ {ch['name']}", callback_data=f"multi_{ch['_id']}")])
    keyboard.append([InlineKeyboardButton(text="✅ Done", callback_data="multi_done")])
    await message.reply("Select channels:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "send_single")
async def send_single_callback(callback: CallbackQuery):
    channels = await db.get_channels()
    if not channels:
        await callback.message.reply("❌ No channels found")
        return
    keyboard = []
    for ch in channels:
        keyboard.append([InlineKeyboardButton(text=ch["name"], callback_data=f"single_{ch['_id']}")])
    await callback.message.reply("📢 Select channel:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("single_"))
async def single_channel(callback: CallbackQuery):
    channel_id = int(callback.data.split("_")[1])
    await db.save_temp(callback.from_user.id, {"send_channel": channel_id, "send_type": "single"})
    await callback.message.reply("confirm please")

@router.callback_query(F.data == "send_multi")
async def send_multi_callback(callback: CallbackQuery):
    channels = await db.get_channels()
    if not channels:
        await callback.message.reply("❌ No channels found")
        return
    keyboard = []
    for ch in channels:
        keyboard.append([InlineKeyboardButton(text=f"☐ {ch['name']}", callback_data=f"multi_{ch['_id']}")])
    keyboard.append([InlineKeyboardButton(text="✅ Done", callback_data="multi_done")])
    await callback.message.reply("Select channels (tap to select, then Done):", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("multi_") & ~F.data == "multi_done")
async def multi_select(callback: CallbackQuery):
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
        checked = "✅" if str(ch['_id']) in multi_selected[uid] else "☐"
        keyboard.append([InlineKeyboardButton(text=f"{checked} {ch['name']}", callback_data=f"multi_{ch['_id']}")])
    keyboard.append([InlineKeyboardButton(text="✅ Done", callback_data="multi_done")])
    await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "multi_done")
async def multi_done(callback: CallbackQuery):
    uid = callback.from_user.id
    selected = multi_selected.get(uid, [])
    if not selected:
        await callback.message.reply("❌ No channels selected")
        return
    await db.save_temp(uid, {"send_channels": selected, "send_type": "multi"})
    await callback.message.reply(f"✅ {len(selected)} channel(s) selected\nconfirm please")

@router.message(Command("confirm"))
async def confirm_send(message: Message):
    temp = await db.get_temp(message.from_user.id)
    latest = await db.get_latest_post()
    if not latest:
        await message.reply("❌ No post to send. Create a post first.")
        return
    if temp.get("send_type") == "single" and temp.get("send_channel"):
        try:
            await message.bot.copy_message(temp["send_channel"], STORAGE_CHANNEL_ID, latest["storage_msg_id"])
            await message.reply("✅ Post delivered!")
        except Exception as e:
            await message.reply(f"❌ Failed: {e}")
    elif temp.get("send_type") == "multi" and temp.get("send_channels"):
        success = 0
        for cid in temp["send_channels"]:
            try:
                await message.bot.copy_message(int(cid), STORAGE_CHANNEL_ID, latest["storage_msg_id"])
                success += 1
            except:
                pass
        await message.reply(f"✅ Delivered to {success} channels")
    else:
        await message.reply("❌ No channel selected")
    await db.del_temp(message.from_user.id)
    if message.from_user.id in multi_selected:
        del multi_selected[message.from_user.id]
