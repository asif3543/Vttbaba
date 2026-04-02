from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import db, get_short_link
from config import Config
import uuid

# Memory for user states
STATE = {}

def is_admin(user_id):
    return user_id in Config.ALLOWED_USERS

@Client.on_message(filters.command("post") & filters.private)
async def start_post(client, message: Message):
    if not is_admin(message.from_user.id): return
    STATE[message.from_user.id] = {"step": "SEND_POST"}
    await message.reply_text("Send post\n(Forward media: document/photo/video with caption)")

@Client.on_message(filters.command(["link", "single link"]) & filters.private)
async def single_link_cmd(client, message: Message):
    user_id = message.from_user.id
    if user_id in STATE and STATE[user_id].get("step") == "LINK_TYPE":
        STATE[user_id]["type"] = "single"
        STATE[user_id]["step"] = "SEND_EPISODE"
        await message.reply_text("Send episode")

@Client.on_message(filters.command(["batch_link", "batch link"]) & filters.private)
async def batch_link_cmd(client, message: Message):
    user_id = message.from_user.id
    if user_id in STATE and STATE[user_id].get("step") == "LINK_TYPE":
        STATE[user_id]["type"] = "batch"
        STATE[user_id]["episodes"] = []
        STATE[user_id]["step"] = "SEND_BATCH_EPISODE"
        await message.reply_text("Send episode")

@Client.on_message(filters.command(["hmm", "confirm"]) & filters.private)
async def confirm_post(client, message: Message):
    user_id = message.from_user.id
    if user_id not in STATE or STATE[user_id].get("step") != "CONFIRM": return
    
    data = STATE[user_id]
    unique_id = str(uuid.uuid4())[:8]
    
    if data["type"] == "single":
        post_id = f"single_{unique_id}"
        db.table("posts").insert({"id": unique_id, "message_id": data["ep_msg_id"], "button_text": f"Watch episode {data['num']}", "type": "single"}).execute()
        btn_text = f"Watch episode {data['num']}"
    else:
        post_id = f"batch_{unique_id}"
        db.table("batch_posts").insert({"id": unique_id, "start_message_id": data["episodes"][0], "end_message_id": data["episodes"][-1], "range": data["num"]}).execute()
        btn_text = f"Watch episode {data['num']}"

    # Generate Short Link
    deep_link = f"https://t.me/{client.me.username}?start={post_id}"
    short_link = get_short_link(deep_link)
    markup = InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, url=short_link)]])
    
    # Send Final Poster Preview to Admin
    await client.copy_message(user_id, user_id, data["thumb_msg_id"], reply_markup=markup)
    
    STATE[user_id]["final_post"] = {"msg_id": data["thumb_msg_id"], "markup": markup}
    STATE[user_id]["step"] = "READY_TO_SEND"
    
    await message.reply_text("Post ready 👇\n\nUse commands:\n/send (For single channel)\n/send_more_channel (For multi channels)")

@Client.on_message(filters.private & ~filters.command(["start", "post", "link", "batch_link", "hmm", "confirm", "send", "send_more_channel", "yes", "delete", "hu_hu"]))
async def state_handler(client, message: Message):
    user_id = message.from_user.id
    if user_id not in STATE: return
    step = STATE[user_id].get("step")

    if step == "SEND_POST":
        if message.photo or message.video or message.document:
            STATE[user_id]["thumb_msg_id"] = message.id
            STATE[user_id]["step"] = "LINK_TYPE"
            await message.reply_text("Post successfully received\nPlease provide single link or batch link")
        else:
            await message.reply_text("Please forward media (Poster)!")

    elif step == "SEND_EPISODE":
        if message.video or message.document:
            fwd = await message.copy(Config.STORAGE_CHANNEL)
            STATE[user_id]["ep_msg_id"] = fwd.id
            STATE[user_id]["step"] = "WAIT_NUM"
            await message.reply_text("Enter number (e.g. 07)")

    elif step == "WAIT_NUM":
        STATE[user_id]["num"] = message.text
        STATE[user_id]["step"] = "CONFIRM"
        await message.reply_text("Type /confirm or /hmm")

    elif step == "SEND_BATCH_EPISODE":
        if message.video or message.document:
            fwd = await message.copy(Config.STORAGE_CHANNEL)
            STATE[user_id]["episodes"].append(fwd.id)
            if len(STATE[user_id]["episodes"]) == 1:
                await message.reply_text("Send next episode")
        elif message.text: # If text is received during batch, it's the range
            STATE[user_id]["num"] = message.text
            STATE[user_id]["step"] = "CONFIRM"
            await message.reply_text("Batch successfully adding\nType /confirm or /hmm")
