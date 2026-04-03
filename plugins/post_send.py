from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from database import db

# ================= 🔰 POST WORKFLOW =================
@Client.on_message(filters.command("post") & filters.private)
async def post_command(client: Client, message: Message):
    if message.from_user.id not in Config.ALLOWED_USERS: return
    Config.STATE[message.from_user.id] = {"step": "WAIT_POST_MEDIA"}
    await message.reply("Send post")

@Client.on_message((filters.photo | filters.video | filters.document) & filters.private)
async def receive_post(client: Client, message: Message):
    user_id = message.from_user.id
    if Config.STATE.get(user_id, {}).get("step") == "WAIT_POST_MEDIA":
        Config.STATE[user_id]["post_msg_id"] = message.id
        Config.STATE[user_id]["step"] = "CHOOSE_TYPE"
        await message.reply("Post successfully received\nPlease provide `single link` or `batch link`")

@Client.on_message(filters.text & filters.private)
async def post_text_handler(client: Client, message: Message):
    user_id = message.from_user.id
    text = message.text.strip().lower()
    step = Config.STATE.get(user_id, {}).get("step")

    if step == "CHOOSE_TYPE":
        if text in ["single link", "/link"]:
            Config.STATE[user_id]["step"] = "WAIT_SINGLE_EP"
            await message.reply("Send episode")
        elif text in["batch link", "/batch link"]:
            Config.STATE[user_id]["step"] = "WAIT_BATCH_EP"
            Config.STATE[user_id]["batch_list"] =[]
            await message.reply("Send episode")

    elif step == "WAIT_SINGLE_NUM":
        Config.STATE[user_id]["number"] = text
        Config.STATE[user_id]["step"] = "WAIT_CONFIRM"
        await message.reply("Type /confirm")

    elif step == "WAIT_BATCH_RANGE":
        Config.STATE[user_id]["range"] = text
        Config.STATE[user_id]["step"] = "WAIT_CONFIRM"
        await message.reply("Type /confirm")

    elif step == "WAIT_CONFIRM" and text in["/hmm", "/confirm"]:
        data = Config.STATE[user_id]
        bot_user = (await client.get_me()).username
        
        if "number" in data:
            btn_text = f"Watch episode {data['number']}"
            post_id = await db.create_post(data["post_msg_id"], data["ep_id"], btn_text)
            Config.STATE[user_id]["deep_link"] = f"https://t.me/{bot_user}?start=reqS_{post_id.replace('-','')}"
        else:
            btn_text = f"Watch episode {data['range']}"
            sorted_eps = sorted(data["batch_list"])
            post_id = await db.create_batch_post(sorted_eps[0], sorted_eps[-1], data["range"])
            Config.STATE[user_id]["deep_link"] = f"https://t.me/{bot_user}?start=reqB_{post_id.replace('-','')}"

        Config.STATE[user_id]["btn_text"] = btn_text
        await message.reply(f"Post ready 👇\n[{btn_text}]\n\n[ /send ]\n[ /send more channel ]")
        Config.STATE[user_id]["step"] = "READY_TO_SEND"

@Client.on_message(filters.forwarded & filters.private)
async def forwarded_episodes(client: Client, message: Message):
    user_id = message.from_user.id
    step = Config.STATE.get(user_id, {}).get("step")

    if step == "WAIT_SINGLE_EP":
        Config.STATE[user_id]["ep_id"] = message.forward_from_message_id
        Config.STATE[user_id]["step"] = "WAIT_SINGLE_NUM"
        await message.reply("Enter number")
        
    elif step == "WAIT_BATCH_EP":
        if "batch_list" not in Config.STATE[user_id]:
            Config.STATE[user_id]["batch_list"] = []
        
        Config.STATE[user_id]["batch_list"].append(message.forward_from_message_id)
        
        # If it's the first forwarded message, prompt for the next one
        if len(Config.STATE[user_id]["batch_list"]) == 1:
            await message.reply("Send next episode (forward all, then type range e.g. 05-15)")
            Config.STATE[user_id]["step"] = "WAIT_BATCH_EP_DONE"

    elif step == "WAIT_BATCH_EP_DONE":
        Config.STATE[user_id]["batch_list"].append(message.forward_from_message_id)
        # We silently save subsequent forwards until they type the range.

# ================= 🔰 SEND SYSTEM =================
@Client.on_message(filters.command(["send", "send more channel"]) & filters.private)
async def send_system(client: Client, message: Message):
    user_id = message.from_user.id
    if Config.STATE.get(user_id, {}).get("step") != "READY_TO_SEND":
        return await message.reply("❌ No post ready.")

    channels = await db.get_channels()
    if not channels: return await message.reply("❌ No channels found.")

    mode = "multi" if "more" in message.text else "single"
    Config.STATE[user_id]["send_mode"] = mode
    Config.STATE[user_id]["selected_ch"] = []

    btns = [[InlineKeyboardButton(ch["channel_name"], callback_data=f"selch_{ch['channel_id']}")] for ch in channels]
    await message.reply("📢 Select channels:", reply_markup=InlineKeyboardMarkup(btns))

@Client.on_callback_query(filters.regex(r"^selch_"))
async def select_channel(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    ch_id = int(query.data.split("_")[1])
    
    if Config.STATE[user_id]["send_mode"] == "single":
        Config.STATE[user_id]["selected_ch"] = [ch_id]
        await query.message.reply("Confirm please (type `/confirm`)")
    else:
        selected = Config.STATE[user_id]["selected_ch"]
        if ch_id in selected: selected.remove(ch_id)
        else: selected.append(ch_id)
        await query.answer(f"✅ Selected", show_alert=False)
        await query.message.reply("Confirm please (type `/confirm`)")

@Client.on_message(filters.command("confirm") & filters.private)
async def final_send(client: Client, message: Message):
    user_id = message.from_user.id
    data = Config.STATE.get(user_id, {})
    if "selected_ch" not in data or not data["selected_ch"]: return
    
    btn = InlineKeyboardMarkup([[InlineKeyboardButton(data["btn_text"], url=data["deep_link"])]])
    for ch in data["selected_ch"]:
        await client.copy_message(chat_id=ch, from_chat_id=message.chat.id, message_id=data["post_msg_id"], reply_markup=btn)
    
    await message.reply("Post sent ✅")
    Config.STATE.pop(user_id, None)
