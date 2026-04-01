from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import database
import config

# State Management
USER_STATE = {}

@Client.on_message(filters.command("post") & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def post_cmd(client: Client, message: Message):
    USER_STATE[message.from_user.id] = {"step": "send_post"}
    await message.reply("Bot reply - send post")

@Client.on_message((filters.document | filters.photo | filters.video) & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def receive_post(client: Client, message: Message):
    uid = message.from_user.id
    state = USER_STATE.get(uid, {})

    if state.get("step") == "send_post":
        USER_STATE[uid]['main_msg'] = message
        USER_STATE[uid]['step'] = "ask_link_type"
        await message.reply("Bot reply - post successfully received \nPlease provide single ling batch link")
        
    elif state.get("step") == "send_episode":
        if 'episodes' not in USER_STATE[uid]:
            USER_STATE[uid]['episodes'] = []
            
        file_id = message.document.file_id if message.document else (message.video.file_id if message.video else message.photo.file_id)
        USER_STATE[uid]['episodes'].append(file_id)
        
        if state.get("type") == "single":
            USER_STATE[uid]['step'] = "ask_number"
            await message.reply("Bot Reply - Enter Number")
        else:
            USER_STATE[uid]['step'] = "send_next_episode"
            await message.reply("Bot Reply - send next episode (Send more or type 'done')")

    elif state.get("step") == "send_next_episode":
        file_id = message.document.file_id if message.document else (message.video.file_id if message.video else message.photo.file_id)
        USER_STATE[uid]['episodes'].append(file_id)
        await message.reply("Bot Reply - send next episode (Send more or type 'done')")

@Client.on_message(filters.text & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def text_handler(client: Client, message: Message):
    uid = message.from_user.id
    state = USER_STATE.get(uid, {})
    text = message.text.lower()
    
    if text.startswith("/"):
        return

    if state.get("step") == "ask_link_type":
        if "single" in text:
            USER_STATE[uid]['step'] = "send_episode"
            USER_STATE[uid]['type'] = "single"
            await message.reply("Bot reply - send episode")
        elif "batch" in text:
            USER_STATE[uid]['step'] = "send_episode"
            USER_STATE[uid]['type'] = "batch"
            await message.reply("Bot reply - send episode")
            
    elif state.get("step") == "send_next_episode" and text == "done":
        USER_STATE[uid]['step'] = "ask_number"
        await message.reply("Bot reply - batch successfully adding\nEnter number")
        
    elif state.get("step") == "ask_number":
        USER_STATE[uid]['number'] = message.text
        USER_STATE[uid]['step'] = "wait_confirm"
        await message.reply("Bot reply - /confirm")
        
    elif state.get("step") == "wait_hmm" and text == "/hmm":
        # Final Button Generation
        episodes_str = ",".join(state['episodes'])
        btn_text = f"Watch episode {state['number']}"
        post_id = database.save_post(episodes_str, btn_text)
        
        btn = InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, url=f"https://t.me/{client.me.username}?start=post_{post_id}")]])
        USER_STATE[uid]['final_btn'] = btn
        USER_STATE[uid]['final_post_id'] = post_id
        
        await state['main_msg'].copy(message.chat.id, reply_markup=btn)
        await message.reply("[ Send ]\n[ Send more channel ]\n\n(Type /send or /send more channel)")

@Client.on_message(filters.command("confirm") & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def confirm_cmd(client: Client, message: Message):
    uid = message.from_user.id
    if USER_STATE.get(uid, {}).get("step") == "wait_confirm":
        USER_STATE[uid]['step'] = "wait_hmm"
        await message.reply("My reply - /hmm (Type /hmm to generate post)")

@Client.on_message(filters.command(["send", "send more channel"]) & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def send_cmd(client: Client, message: Message):
    channels = database.get_target_channels()
    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(ch['title'], callback_data=f"sendto_{ch['channel_id']}")])
    
    if not buttons:
        await message.reply("No target channels found!")
        return
        
    await message.reply("Select Channel:", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r"^sendto_"))
async def send_callback(client: Client, query: CallbackQuery):
    channel_id = int(query.data.split("_")[1])
    uid = query.from_user.id
    state = USER_STATE.get(uid, {})
    
    # Ye /confirm mangega
    USER_STATE[uid]['target_send_channel'] = channel_id
    USER_STATE[uid]['step'] = "final_channel_confirm"
    await query.message.edit_text(f"Bot reply - confirm please\n(Type /confirm to send)")

@Client.on_message(filters.command("confirm") & (filters.user(config.ADMINS) | filters.chat(config.ALLOWED_GROUP)))
async def final_confirm_send(client: Client, message: Message):
    uid = message.from_user.id
    state = USER_STATE.get(uid, {})
    
    if state.get("step") == "final_channel_confirm":
        ch_id = state['target_send_channel']
        await state['main_msg'].copy(ch_id, reply_markup=state['final_btn'])
        await message.reply("Bot un channel pe post daal dega ✅")
        USER_STATE.pop(uid, None) # Clear state
