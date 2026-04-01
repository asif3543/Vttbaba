from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import database
import config

USER_STATE = {}

# 1. Start Post
@Client.on_message(filters.command("post") & filters.user(config.ADMINS))
async def post_cmd(client: Client, message: Message):
    USER_STATE[message.from_user.id] = {"step": "wait_main_post"}
    await message.reply("Bot reply - send post")

# 2. Receive Main Post (Photo/Document/Video)
@Client.on_message((filters.document | filters.photo | filters.video) & filters.user(config.ADMINS))
async def receive_post(client: Client, message: Message):
    uid = message.from_user.id
    state = USER_STATE.get(uid, {})

    if state.get("step") == "wait_main_post":
        USER_STATE[uid]['main_msg'] = message
        USER_STATE[uid]['step'] = "ask_link_type"
        await message.reply("Bot reply - post successfully received \nPlease provide single ling batch link")
        
    elif state.get("step") == "wait_episode":
        if 'episodes' not in USER_STATE[uid]:
            USER_STATE[uid]['episodes'] = []
            
        # Extract file_id depending on media type
        if message.document: file_id = message.document.file_id
        elif message.video: file_id = message.video.file_id
        else: file_id = message.photo.file_id
            
        USER_STATE[uid]['episodes'].append(file_id)
        
        if state.get("type") == "single":
            USER_STATE[uid]['step'] = "ask_number"
            await message.reply("Bot Reply - Enter Number")
        else:
            USER_STATE[uid]['step'] = "wait_next_episode"
            await message.reply("Bot Reply - send next episode")

    elif state.get("step") == "wait_next_episode":
        if message.document: file_id = message.document.file_id
        elif message.video: file_id = message.video.file_id
        else: file_id = message.photo.file_id
            
        USER_STATE[uid]['episodes'].append(file_id)
        USER_STATE[uid]['step'] = "ask_number"
        await message.reply("Bot reply - batch successfully adding\nEnter number")

# 3. Handle Text Replies (single link, batch link, numbers, etc.)
@Client.on_message(filters.text & filters.user(config.ADMINS))
async def text_handler(client: Client, message: Message):
    uid = message.from_user.id
    state = USER_STATE.get(uid, {})
    text = message.text.lower().strip()
    
    # Agar command hai toh ignore karo, baaki commands handle karengi
    if text.startswith("/") and text not in ["/hmm", "/confirm", "/send", "/send more channel"]:
        return

    if state.get("step") == "ask_link_type":
        if text == "single link":
            USER_STATE[uid]['step'] = "wait_episode"
            USER_STATE[uid]['type'] = "single"
            await message.reply("Bot reply - send episode")
        elif text == "batch link":
            USER_STATE[uid]['step'] = "wait_episode"
            USER_STATE[uid]['type'] = "batch"
            await message.reply("Bot reply - send episode")
            
    elif state.get("step") == "ask_number":
        USER_STATE[uid]['number'] = message.text
        USER_STATE[uid]['step'] = "wait_confirm"
        await message.reply("Bot reply - /confirm")
        
    elif state.get("step") == "wait_hmm" and text == "/hmm":
        episodes_str = ",".join(state['episodes'])
        btn_text = f"Watch episode {state['number']}"
        post_id = database.save_post(episodes_str, btn_text)
        
        # Post ke niche button banaya
        btn = InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, url=f"https://t.me/{client.me.username}?start=post_{post_id}")]])
        USER_STATE[uid]['final_btn'] = btn
        
        # Wapas bheja owner ko
        await state['main_msg'].copy(message.chat.id, reply_markup=btn)
        
        # Options diye
        await message.reply("[ Send ]\n[ Send more channel ]")
        USER_STATE[uid]['step'] = "wait_send_command"

# 4. Commands Flow (/confirm, /hmm)
@Client.on_message(filters.command("confirm") & filters.user(config.ADMINS))
async def confirm_cmd(client: Client, message: Message):
    uid = message.from_user.id
    state = USER_STATE.get(uid, {})
    
    if state.get("step") == "wait_confirm":
        USER_STATE[uid]['step'] = "wait_hmm"
        await message.reply("My reply - /hmm")
        
    elif state.get("step") == "final_send_confirm":
        channels = state.get("target_channels", [])
        for ch in channels:
            await state['main_msg'].copy(ch, reply_markup=state['final_btn'])
        await message.reply("Bot un channel pe post daal dega ✅")
        USER_STATE.pop(uid, None)

# 5. Channel Send Logic
@Client.on_message(filters.command("send") & filters.user(config.ADMINS))
async def send_single(client: Client, message: Message):
    await send_channels_list(client, message, multi=False)

@Client.on_message(filters.command(["send more channel", "send_more_channel"]) & filters.user(config.ADMINS))
async def send_multi(client: Client, message: Message):
    await send_channels_list(client, message, multi=True)

async def send_channels_list(client, message, multi):
    uid = message.from_user.id
    if USER_STATE.get(uid, {}).get("step") == "wait_send_command":
        channels = database.get_target_channels()
        USER_STATE[uid]['is_multi'] = multi
        USER_STATE[uid]['selected_channels'] = []
        
        buttons = []
        for ch in channels:
            buttons.append([InlineKeyboardButton(ch['title'], callback_data=f"sel_{ch['channel_id']}")])
        
        if not buttons:
            await message.reply("Koi target channel nahi hai! Pehle add karein.")
            return
            
        await message.reply("Select Channel (Example ↓):", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r"^sel_"))
async def channel_select_callback(client: Client, query: CallbackQuery):
    ch_id = int(query.data.split("_")[1])
    uid = query.from_user.id
    state = USER_STATE.get(uid, {})
    
    if state.get("is_multi"):
        # Multi select
        if ch_id not in state['selected_channels']:
            USER_STATE[uid]['selected_channels'].append(ch_id)
        await query.answer(f"Channel Selected. Total: {len(USER_STATE[uid]['selected_channels'])}", show_alert=False)
        
        # User 2 select karne ke baad manually /confirm type karega as per your flow
        USER_STATE[uid]['target_channels'] = USER_STATE[uid]['selected_channels']
        USER_STATE[uid]['step'] = "final_send_confirm"
        await query.message.reply("Bot reply - confirm please\n(Type /confirm to send)")
    else:
        # Single select
        USER_STATE[uid]['target_channels'] = [ch_id]
        USER_STATE[uid]['step'] = "final_send_confirm"
        await query.message.edit_text("Bot reply - confirm please\n(Type /confirm to send)")
