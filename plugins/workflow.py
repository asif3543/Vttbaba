from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import MessageMediaType
from config import ADMINS, BOT_TOKEN
from database import add_post, add_batch
import requests

# Temporary memory to store workflow state
user_state = {}

@Client.on_message(filters.command("post") & filters.user(ADMINS) & filters.private)
async def start_post(client: Client, message: Message):
    user_state[message.from_user.id] = {"step": "wait_post_media"}
    await message.reply_text("Send post (Forward media: document/photo/video)")

@Client.on_message(filters.user(ADMINS) & filters.private, group=1)
async def handle_workflow(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_state:
        return

    state = user_state[user_id]
    step = state.get("step")

    # STEP 1: Receiving the display post media
    if step == "wait_post_media" and message.media:
        state["post_msg_id"] = message.id
        state["step"] = "wait_link_type"
        await message.reply_text("Post successfully received.\nPlease provide `single link` or `batch link` (/link or /batch link)")
        return

    # STEP 2: Asking type
    if step == "wait_link_type":
        if message.text in ["/link", "single link"]:
            state["type"] = "single"
            state["step"] = "wait_single_episode"
            await message.reply_text("Send episode (Forward from database)")
        elif message.text in ["/batch link", "batch link"]:
            state["type"] = "batch"
            state["step"] = "wait_batch_first"
            await message.reply_text("Send first episode")
        return

    # STEP 3: Single Workflow
    if state.get("type") == "single":
        if step == "wait_single_episode" and message.media:
            state["file_id"] = message.id # We store the message ID of the forwarded episode
            state["step"] = "wait_single_number"
            await message.reply_text("Enter Number (e.g. 07)")
        
        elif step == "wait_single_number":
            state["number"] = message.text
            state["step"] = "wait_single_confirm"
            await message.reply_text("Type /hmm to confirm")

        elif step == "wait_single_confirm" and message.text == "/hmm":
            post_id = add_post(state["file_id"], f"Watch episode {state['number']}", "single")
            bot_info = await client.get_me()
            link = f"https://t.me/{bot_info.username}?start=post_{post_id}"
            
            btn = InlineKeyboardMarkup([[InlineKeyboardButton(f"Watch episode {state['number']}", url=link)]])
            await client.copy_message(user_id, user_id, state["post_msg_id"], reply_markup=btn)
            await message.reply_text("Post ready 👇\n\n[ Send ]\n[ Send more channel ]")
            del user_state[user_id]

    # STEP 4: Batch Workflow
    elif state.get("type") == "batch":
        if step == "wait_batch_first" and message.media:
            state["start_id"] = message.id
            state["step"] = "wait_batch_last"
            await message.reply_text("Send next episode (Last Episode)")
            
        elif step == "wait_batch_last" and message.media:
            state["end_id"] = message.id
            state["step"] = "wait_batch_range"
            await message.reply_text("Batch successfully adding.\nEnter range (e.g. 05-15)")
            
        elif step == "wait_batch_range":
            state["range"] = message.text
            state["step"] = "wait_batch_confirm"
            await message.reply_text("Type /hmm to confirm")
            
        elif step == "wait_batch_confirm" and message.text == "/hmm":
            batch_id = add_batch(state["start_id"], state["end_id"], state["range"])
            bot_info = await client.get_me()
            link = f"https://t.me/{bot_info.username}?start=batch_{batch_id}"
            
            btn = InlineKeyboardMarkup([[InlineKeyboardButton(f"Watch episode {state['range']}", url=link)]])
            await client.copy_message(user_id, user_id, state["post_msg_id"], reply_markup=btn)
            await message.reply_text("Post ready 👇\n\n/send\n/send more channel")
            del user_state[user_id]
