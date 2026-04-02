from pyrogram import Client, filters
from pyrogram.types import Message
from plugins.helpers import USER_STATE, is_admin, db
import uuid
from config import Config

@Client.on_message(filters.command("post") & filters.private)
async def post_cmd(client, message: Message):
    if not is_admin(message.from_user.id): return
    USER_STATE[message.from_user.id] = {"step": "wait_post_file"}
    await message.reply_text("Forward media from Storage Channel:")

@Client.on_message(filters.command(["link", "single link"]) & filters.private)
async def single_link_cmd(client, message: Message):
    if not is_admin(message.from_user.id): return
    USER_STATE[message.from_user.id]["step"] = "wait_single_num"
    await message.reply_text("Enter number (e.g. 07):")

@Client.on_message(filters.command("hmm") & filters.private)
async def hmm_cmd(client, message: Message):
    user_id = message.from_user.id
    if USER_STATE.get(user_id, {}).get("step") == "wait_single_confirm":
        data = USER_STATE[user_id]
        p_id = str(uuid.uuid4())
        link = f"https://t.me/{client.me.username}?start=single_{p_id}"
        
        db.table("posts").insert({"id": p_id, "message_id": data["msg_id"], "button_text": f"Watch episode {data['num']}", "type": "single"}).execute()
        USER_STATE[user_id]["last_post_id"] = f"single_{p_id}"
        await message.reply_text(f"Post ready 👇\n[Watch episode {data['num']}]({link})\n\nSend /send or /send_more_channel", disable_web_page_preview=True)

@Client.on_message(filters.command(["batch_link", "batch link"]) & filters.private)
async def batch_link_cmd(client, message: Message):
    if not is_admin(message.from_user.id): return
    USER_STATE[message.from_user.id] = {"step": "wait_batch_start"}
    await message.reply_text("Forward FIRST episode from storage:")

@Client.on_message(filters.command("confirm") & filters.private)
async def confirm_cmd(client, message: Message):
    user_id = message.from_user.id
    state = USER_STATE.get(user_id, {}).get("step")
    
    if state == "wait_batch_confirm":
        data = USER_STATE[user_id]
        b_id = str(uuid.uuid4())
        link = f"https://t.me/{client.me.username}?start=batch_{b_id}"
        
        db.table("batch_posts").insert({"id": b_id, "start_message_id": data["start_msg"], "end_message_id": data["end_msg"], "range": data["range"]}).execute()
        USER_STATE[user_id]["last_post_id"] = f"batch_{b_id}"
        await message.reply_text(f"Post ready 👇\n[Watch episode {data['range']}]({link})\n\nSend /send or /send_more_channel", disable_web_page_preview=True)

# Main input handler for Admin States
@Client.on_message(filters.private & ~filters.command(["start", "post", "link", "hmm", "batch_link", "confirm"]))
async def state_handler(client, message: Message):
    user_id = message.from_user.id
    if user_id not in USER_STATE: return
    state = USER_STATE[user_id].get("step")

    # Post Making Logic (Ensure it's forwarded from Storage Channel)
    if state == "wait_post_file":
        msg_id = message.forward_from_message_id or message.id
        USER_STATE[user_id].update({"msg_id": msg_id, "step": "wait_post_type"})
        await message.reply_text("Received! Provide /link or /batch_link")
    
    elif state == "wait_single_num":
        USER_STATE[user_id].update({"num": message.text, "step": "wait_single_confirm"})
        await message.reply_text("Type /hmm to confirm")

    elif state == "wait_batch_start":
        msg_id = message.forward_from_message_id or message.id
        USER_STATE[user_id].update({"start_msg": msg_id, "step": "wait_batch_end"})
        await message.reply_text("Forward LAST episode:")

    elif state == "wait_batch_end":
        msg_id = message.forward_from_message_id or message.id
        USER_STATE[user_id].update({"end_msg": msg_id, "step": "wait_batch_range"})
        await message.reply_text("Batch adding! Enter range (e.g. 05-15):")

    elif state == "wait_batch_range":
        USER_STATE[user_id].update({"range": message.text, "step": "wait_batch_confirm"})
        await message.reply_text("Type /confirm to finalize batch.")

    elif state == "wait_prem_id":
        USER_STATE[user_id].update({"target_id": message.text, "step": "wait_prem_confirm"})
        await message.reply_text("Type /hu hu to confirm.")
        
    elif state == "wait_rem_prem_id":
        remove_premium(int(message.text))
        await message.reply_text("Premium removed ❌")
        del USER_STATE[user_id]
