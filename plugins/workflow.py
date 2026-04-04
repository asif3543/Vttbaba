from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMINS, USER_STATE
from database import add_post, add_batch

@Client.on_message(filters.command("post") & filters.user(ADMINS) & filters.private)
async def start_post(client, message):
    USER_STATE[message.from_user.id] = {"step": "wait_post_media"}
    await message.reply_text("Send post media")

@Client.on_message(filters.user(ADMINS) & filters.private, group=1)
async def handle_workflow(client, message):
    user_id = message.from_user.id
    if user_id not in USER_STATE:
        return

    state = USER_STATE[user_id]
    step = state.get("step")

    if step == "wait_post_media" and message.media:
        state["post_msg_id"] = message.id
        state["step"] = "wait_type"
        await message.reply_text("Send /link or /batch")

    elif step == "wait_type":
        if message.text == "/link":
            state["type"] = "single"
            state["step"] = "wait_episode"
            await message.reply_text("Send episode file")

        elif message.text == "/batch":
            state["type"] = "batch"
            state["step"] = "wait_start"
            await message.reply_text("Send first episode")

    elif state.get("type") == "single":
        if step == "wait_episode" and message.media:
            state["file_id"] = message.id
            state["step"] = "wait_number"
            await message.reply_text("Send episode number")

        elif step == "wait_number":
            state["number"] = message.text
            post_id = await add_post(state["file_id"], f"Watch {state['number']}")
            
            bot = await client.get_me()
            link = f"https://t.me/{bot.username}?start=post_{post_id}"

            btn = InlineKeyboardMarkup([[InlineKeyboardButton("Watch", url=link)]])

            state["ready_btn"] = btn
            state["step"] = "ready_to_send"

            await message.reply_text("Post Ready ✅\nUse /send")

    elif state.get("type") == "batch":
        if step == "wait_start" and message.media:
            state["start"] = message.id
            state["step"] = "wait_end"
            await message.reply_text("Send last episode")

        elif step == "wait_end" and message.media:
            state["end"] = message.id
            batch_id = await add_batch(state["start"], state["end"], "Batch")
            
            bot = await client.get_me()
            link = f"https://t.me/{bot.username}?start=batch_{batch_id}"

            btn = InlineKeyboardMarkup([[InlineKeyboardButton("Watch Batch", url=link)]])

            state["ready_btn"] = btn
            state["step"] = "ready_to_send"

            await message.reply_text("Batch Ready ✅\nUse /send")
