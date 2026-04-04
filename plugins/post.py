from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMINS, USER_STATE
from database import add_post, add_batch

@Client.on_message(filters.command(["post", "genlink", "batch"]) & filters.user(ADMINS) & filters.private)
async def start_post(client: Client, message: Message):
    USER_STATE[message.from_user.id] = {"step": "wait_post_media"}
    await message.reply_text("Send post (Forward media: document/photo/video)")

@Client.on_message(filters.user(ADMINS) & filters.private, group=1)
async def handle_workflow(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in USER_STATE: return
    state = USER_STATE[user_id]
    step = state.get("step")

    # STEP 1: Get Post Media
    if step == "wait_post_media" and message.media:
        state["post_msg_id"] = message.id
        state["step"] = "wait_link_type"
        await message.reply_text("Post successfully received.\nPlease provide `single link` or `batch link`")
        return

    # STEP 2: Link Type
    if step == "wait_link_type":
        text = message.text.lower().strip()
        if text in["/link", "single link", "single"]:
            state["type"] = "single"
            state["step"] = "wait_single_episode"
            await message.reply_text("Send episode (Forward from database)")
        elif text in["/batch link", "batch link", "batch"]:
            state["type"] = "batch"
            state["step"] = "wait_batch_episodes"
            state["batch_list"] =[]
            await message.reply_text("Send episode 1")
        return

    # STEP 3: Single Workflow
    if state.get("type") == "single":
        if step == "wait_single_episode" and message.media:
            state["file_id"] = message.forward_from_message_id if message.forward_from_chat else message.id
            state["step"] = "wait_single_number"
            await message.reply_text("Enter Number (e.g. 07)")
        elif step == "wait_single_number":
            state["number"] = message.text
            state["step"] = "wait_confirm"
            await message.reply_text("Type /confirm or /hmm")

    # STEP 4: Batch Workflow
    elif state.get("type") == "batch":
        if step == "wait_batch_episodes" and message.media:
            msg_id = message.forward_from_message_id if message.forward_from_chat else message.id
            state["batch_list"].append(msg_id)
            if len(state["batch_list"]) == 1:
                await message.reply_text("Send next episode (forward all, then type range e.g. 05-15)")
        elif step == "wait_batch_episodes" and message.text:
            state["range"] = message.text
            state["step"] = "wait_confirm"
            await message.reply_text("Batch successfully adding.\nType /confirm or /hmm")

    # STEP 5: Confirm & Generate Links
    if step == "wait_confirm" and message.text in ["/hmm", "/confirm"]:
        bot_info = await client.get_me()
        if state["type"] == "single":
            post_id = await add_post(state["file_id"], f"Watch episode {state['number']}", "single")
            link = f"https://t.me/{bot_info.username}?start=post_{post_id}"
            btn_text = f"Watch episode {state['number']}"
        else:
            sorted_eps = sorted(state["batch_list"])
            post_id = await add_batch(sorted_eps[0], sorted_eps[-1], state["range"])
            link = f"https://t.me/{bot_info.username}?start=batch_{post_id}"
            btn_text = f"Watch episode {state['range']}"
            
        btn = InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, url=link)]])
        state["ready_btn"] = btn
        state["ready_link"] = link
        state["step"] = "ready_to_send"
        
        await message.reply_text(f"Post ready 👇\n[{btn_text}]\n\n[ /send ]\n[ /send more channel ]")
