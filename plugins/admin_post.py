from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import database
import config

STATE = {}

@Client.on_message(filters.command("post") & filters.user(config.ADMINS))
async def cmd_post(client: Client, message: Message):
    STATE[message.from_user.id] = {"step": "wait_post"}
    await message.reply("Bot reply - send post")

@Client.on_message((filters.document | filters.photo | filters.video) & filters.user(config.ADMINS))
async def receive_media(client: Client, message: Message):
    uid = message.from_user.id
    state = STATE.get(uid, {})

    if state.get("step") == "wait_post":
        STATE[uid]['main_post'] = message
        STATE[uid]['step'] = "wait_link_type"
        await message.reply("Bot reply - post successfully received\nPlease provide single ling batch link")
        
    elif state.get("step") == "wait_episode":
        if 'episodes' not in STATE[uid]: STATE[uid]['episodes'] = []
        file_id = message.document.file_id if message.document else (message.video.file_id if message.video else message.photo.file_id)
        STATE[uid]['episodes'].append(file_id)
        
        if state.get("link_type") == "single":
            STATE[uid]['step'] = "wait_number"
            await message.reply("Bot Reply - Enter Number")
        else:
            STATE[uid]['step'] = "wait_next_episode"
            await message.reply("Bot Reply - send next episode")

    elif state.get("step") == "wait_next_episode":
        file_id = message.document.file_id if message.document else (message.video.file_id if message.video else message.photo.file_id)
        STATE[uid]['episodes'].append(file_id)
        STATE[uid]['step'] = "wait_batch_number"
        await message.reply("Bot reply - batch successfully adding\nEnter number")

@Client.on_message(filters.text & filters.user(config.ADMINS))
async def handle_text(client: Client, message: Message):
    uid = message.from_user.id
    state = STATE.get(uid, {})
    text = message.text.lower().strip()

    if text.startswith("/") and text not in ["/hmm", "/confirm", "/send"]: return

    if state.get("step") == "wait_link_type":
        if text == "single link":
            STATE[uid]['link_type'] = "single"
            STATE[uid]['step'] = "wait_episode"
            await message.reply("Bot reply - send episode")
        elif text == "batch link":
            STATE[uid]['link_type'] = "batch"
            STATE[uid]['step'] = "wait_episode"
            await message.reply("Bot reply - send episode")

    elif state.get("step") in ["wait_number", "wait_batch_number"]:
        STATE[uid]['episode_number'] = message.text
        STATE[uid]['step'] = "wait_confirm"
        if state.get("step") == "wait_batch_number":
            await message.reply("Bot reply - confirm")
        else:
            await message.reply("Bot reply - /confirm")

    elif state.get("step") == "wait_hmm" and text == "/hmm":
        eps_str = ",".join(STATE[uid]['episodes'])
        btn_txt = f"Watch episode {STATE[uid]['episode_number']}"
        post_id = database.save_post(eps_str, btn_txt)
        
        btn = InlineKeyboardMarkup([[InlineKeyboardButton(btn_txt, url=f"https://t.me/{client.me.username}?start=post_{post_id}")]])
        STATE[uid]['final_btn'] = btn
        
        await STATE[uid]['main_post'].copy(message.chat.id, reply_markup=btn)
        await message.reply("[ Send ]\n[ Send more channel ]")
        STATE[uid]['step'] = "wait_send_command"

@Client.on_message(filters.command("confirm") & filters.user(config.ADMINS))
async def cmd_confirm(client: Client, message: Message):
    uid = message.from_user.id
    state = STATE.get(uid, {})
    
    if state.get("step") == "wait_confirm":
        STATE[uid]['step'] = "wait_hmm"
        await message.reply("My reply - /hmm")
        
    elif state.get("step") == "wait_final_confirm":
        for ch in STATE[uid]['selected_channels']:
            await STATE[uid]['main_post'].copy(ch, reply_markup=STATE[uid]['final_btn'])
        await message.reply("Bot un channel pe post daal dega ✅")
        STATE.pop(uid, None)

@Client.on_message(filters.command(["send", "send more channel", "send_more_channel"]) & filters.user(config.ADMINS))
async def cmd_send(client: Client, message: Message):
    uid = message.from_user.id
    if STATE.get(uid, {}).get("step") == "wait_send_command":
        channels = database.get_target_channels()
        STATE[uid]['selected_channels'] = []
        
        btns = []
        for ch in channels:
            btns.append([InlineKeyboardButton(ch['title'], callback_data=f"sel_{ch['channel_id']}")])
        
        if not btns:
            await message.reply("No target channels! Use /add_target_channel to add.")
            return
            
        await message.reply("Select Channel:", reply_markup=InlineKeyboardMarkup(btns))
        STATE[uid]['step'] = "wait_final_confirm"

@Client.on_callback_query(filters.regex(r"^sel_"))
async def callback_select(client: Client, query: CallbackQuery):
    ch_id = int(query.data.split("_")[1])
    uid = query.from_user.id
    if uid in STATE:
        if ch_id not in STATE[uid]['selected_channels']:
            STATE[uid]['selected_channels'].append(ch_id)
        await query.answer("Channel selected!", show_alert=False)
        await query.message.reply("Bot reply - confirm please\n(Type /confirm)")
