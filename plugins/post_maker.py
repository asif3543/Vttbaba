from pyrogram import Client, filters
from pyrogram.types import Message
from plugins.helpers import USER_STATE, db, is_admin
import uuid

@Client.on_message(filters.private & filters.command("post"))
async def post_cmd(client, message: Message):
    if not is_admin(message.from_user.id): return
    USER_STATE[message.from_user.id] = {"step": "wait_post_file"}
    await message.reply_text("Send post (Forward media: document/photo/video from Storage Channel)")

@Client.on_message(filters.private & filters.command(["link", "single link"]))
async def single_link_cmd(client, message: Message):
    if not is_admin(message.from_user.id): return
    if USER_STATE.get(message.from_user.id, {}).get("step") == "wait_post_type":
        await message.reply_text("Enter number (e.g. 07):")
        USER_STATE[message.from_user.id]["step"] = "wait_single_num"

@Client.on_message(filters.private & filters.command("hmm"))
async def hmm_cmd(client, message: Message):
    user_id = message.from_user.id
    if user_id in USER_STATE and USER_STATE[user_id].get("step") == "wait_single_confirm":
        data = USER_STATE[user_id]
        post_id = str(uuid.uuid4())
        deep_link = f"https://t.me/{client.me.username}?start=single_{post_id}"
        
        # Save to DB
        db.table("posts").insert({
            "id": post_id,
            "message_id": data["msg_id"],
            "button_text": f"Watch episode {data['num']}",
            "type": "single"
        }).execute()
        
        USER_STATE[user_id]["last_post_id"] = post_id
        await message.reply_text(f"Post ready 👇\n[Watch episode {data['num']}]({deep_link})\n\nSend /send or /send_more_channel", disable_web_page_preview=True)

@Client.on_message(filters.private & filters.command(["batch_link", "batch link"]))
async def batch_link_cmd(client, message: Message):
    if not is_admin(message.from_user.id): return
    USER_STATE[message.from_user.id] = {"step": "wait_batch_start"}
    await message.reply_text("Send first episode (Forward from storage):")

@Client.on_message(filters.private & filters.command("confirm"))
async def confirm_cmd(client, message: Message):
    user_id = message.from_user.id
    if user_id in USER_STATE and USER_STATE[user_id].get("step") == "wait_batch_confirm":
        data = USER_STATE[user_id]
        batch_id = str(uuid.uuid4())
        deep_link = f"https://t.me/{client.me.username}?start=batch_{batch_id}"
        
        db.table("batch_posts").insert({
            "id": batch_id,
            "start_message_id": data["start_msg"],
            "end_message_id": data["end_msg"],
            "range": data["range"]
        }).execute()
        
        USER_STATE[user_id]["last_post_id"] = f"batch_{batch_id}"
        await message.reply_text(f"Post ready 👇\n[Watch episode {data['range']}]({deep_link})\n\nSend /send or /send_more_channel", disable_web_page_preview=True)

# Central Message Handler for all states
@Client.on_message(filters.private & ~filters.command(["start", "post", "link", "hmm", "batch_link", "confirm", "send", "hu_hu"]))
async def state_handler(client, message: Message):
    user_id = message.from_user.id
    if user_id not in USER_STATE: return
    state = USER_STATE[user_id].get("step")

    # POSTING
    if state == "wait_post_file":
        USER_STATE[user_id]["msg_id"] = message.forward_from_message_id or message.id
        USER_STATE[user_id]["step"] = "wait_post_type"
        await message.reply_text("Post successfully received.\nPlease provide /link or /batch_link")
    
    elif state == "wait_single_num":
        USER_STATE[user_id]["num"] = message.text
        USER_STATE[user_id]["step"] = "wait_single_confirm"
        await message.reply_text("Type /hmm to confirm")

    elif state == "wait_batch_start":
        USER_STATE[user_id]["start_msg"] = message.forward_from_message_id or message.id
        USER_STATE[user_id]["step"] = "wait_batch_end"
        await message.reply_text("Send next/last episode:")

    elif state == "wait_batch_end":
        USER_STATE[user_id]["end_msg"] = message.forward_from_message_id or message.id
        USER_STATE[user_id]["step"] = "wait_batch_range"
        await message.reply_text("Batch successfully adding.\nEnter range (e.g. 05-15):")

    elif state == "wait_batch_range":
        USER_STATE[user_id]["range"] = message.text
        USER_STATE[user_id]["step"] = "wait_batch_confirm"
        await message.reply_text("Type /confirm to finalize batch.")

    # PREMIUM & SHORTNER ADMIN
    elif state == "wait_prem_id":
        USER_STATE[user_id]["target_id"] = message.text
        USER_STATE[user_id]["step"] = "wait_prem_confirm"
        await message.reply_text("Type /hu hu to confirm.")
        
    elif state == "wait_rem_prem_id":
        remove_premium(int(message.text))
        await message.reply_text("Premium removed ❌")
        del USER_STATE[user_id]
