import asyncio
import random
import requests
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
import config
import db

# --- PYROGRAM CLIENT ---
app = Client(
    "anime_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# --- STATE MANAGEMENT ---
# Bot ko yaad rakhne ke liye ki admin abhi kis step par hai
USER_STATE = {}

# --- HELPER FUNCTIONS ---
def generate_short_link(long_url):
    shortners = db.get_shortners()
    if not shortners:
        return long_url # Agar shortner nahi hai, direct link de do
    
    # Ek ke baad ek (randomly) shortner choose karo
    shortner = random.choice(shortners)
    api_url = f"{shortner['shortner_url']}api?api={shortner['api_key']}&url={long_url}"
    try:
        res = requests.get(api_url).json()
        if res.get("status") == "success":
            return res.get("shortenedUrl")
    except Exception as e:
        print("Shortner Error:", e)
    return long_url

async checking_force_sub(client, user_id):
    channels = db.get_force_sub_channels()
    not_joined = []
    for ch in channels:
        try:
            await client.get_chat_member(ch, user_id)
        except UserNotParticipant:
            not_joined.append(ch)
        except Exception:
            pass # Bot admin nahi hai ya channel private hai
    return not_joined

# --- ADMIN COMMANDS ---

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    # Deep link check (jab user shortner solve karke aata hai)
    if len(message.command) > 1:
        post_id = message.command[1]
        
        # 1. Check Force Sub
        not_joined = await checking_force_sub(client, message.from_user.id)
        if not_joined:
            buttons = []
            for ch in not_joined:
                try:
                    chat = await client.get_chat(ch)
                    invite_link = chat.invite_link or f"https://t.me/{chat.username}"
                    buttons.append([InlineKeyboardButton(f"Join {chat.title}", url=invite_link)])
                except:
                    pass
            # Try again button wapas same link dega
            buttons.append([InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{client.me.username}?start={post_id}")])
            await message.reply("⚠️ Join First!\nAapko pehle niche diye gaye channels join karne honge:", reply_markup=InlineKeyboardMarkup(buttons))
            return

        # 2. Get Post & Send File
        post = db.get_post(post_id)
        if post:
            # post['link'] me humne file_id save ki hogi
            file_ids = post['link'].split(",")
            for fid in file_ids:
                await client.copy_message(chat_id=message.chat.id, from_chat_id=config.STORAGE_CHANNEL_ID, message_id=int(fid))
            await message.reply("🎉 Here is your episode!")
        return

    await message.reply("👋 Hello! Bot is working perfectly.\nCommands: /post, /batchlink, /add_premium, etc.")


# --- PREMIUM SYSTEM ---
@app.on_message(filters.command("add_premium") & filters.user(config.ADMINS))
async def add_premium_cmd(client, message: Message):
    USER_STATE[message.from_user.id] = {"step": "wait_premium_id"}
    await message.reply("Send User ID:")

@app.on_message(filters.command("remove_premium") & filters.user(config.ADMINS))
async def remove_premium_cmd(client, message: Message):
    USER_STATE[message.from_user.id] = {"step": "wait_remove_premium_id"}
    await message.reply("Send User ID to remove and ban from premium:")


# --- POSTING SYSTEM (TERA EXACT WORKFLOW) ---
@app.on_message(filters.command("post") & filters.user(config.ADMINS))
async def post_cmd(client, message: Message):
    USER_STATE[message.from_user.id] = {"step": "wait_post"}
    await message.reply("Send post (Document/Photo...)")

@app.on_message(filters.command("batchlink") & filters.user(config.ADMINS))
async def batchlink_cmd(client, message: Message):
    USER_STATE[message.from_user.id] = {"step": "wait_post", "is_batch": True}
    await message.reply("Send post (Document/Photo...)")

@app.on_message(filters.private & filters.user(config.ADMINS) & ~filters.command(["post", "batchlink", "confirm", "hmm", "send"]))
async def message_handler(client, message: Message):
    uid = message.from_user.id
    state = USER_STATE.get(uid)
    if not state:
        return

    step = state.get("step")

    # PREMIUM FLOW
    if step == "wait_premium_id":
        state['target_id'] = int(message.text)
        state['step'] = "wait_huhu"
        await message.reply("Please confirm type /hu_hu")
        return
    elif step == "wait_remove_premium_id":
        target_id = int(message.text)
        db.remove_premium_user(target_id)
        USER_STATE.pop(uid, None)
        await message.reply(f"Successfully deleted and banned ID {target_id}")
        return

    # POST FLOW
    if step == "wait_post":
        # Copy post to storage channel safely
        msg = await message.copy(config.STORAGE_CHANNEL_ID)
        state['post_msg_id'] = message.id
        state['step'] = "wait_link_type"
        if state.get("is_batch"):
            await message.reply("Post successfully received.\nPlease provide batch link reply (Type: batch link)")
        else:
            await message.reply("Post successfully received.\nPlease provide single link reply (Type: single link)")
        return
    
    elif step == "wait_link_type":
        if "single" in message.text.lower():
            state['step'] = "wait_episode"
            await message.reply("Send episode (Forward from database)")
        elif "batch" in message.text.lower():
            state['step'] = "wait_episode_batch_1"
            await message.reply("Send 1st episode")
        return

    elif step == "wait_episode":
        msg = await message.copy(config.STORAGE_CHANNEL_ID)
        state['file_id'] = str(msg.id)
        state['step'] = "wait_number"
        await message.reply("Enter Number (e.g. 07)")
        return
    
    elif step == "wait_episode_batch_1":
        msg = await message.copy(config.STORAGE_CHANNEL_ID)
        state['file_id_1'] = msg.id
        state['step'] = "wait_episode_batch_2"
        await message.reply("Send next episode (Last episode)")
        return
    
    elif step == "wait_episode_batch_2":
        msg = await message.copy(config.STORAGE_CHANNEL_ID)
        state['file_id_2'] = msg.id
        
        # Batch me sab episodes ek list me daal do (File 1 to File 2 range)
        f_ids = [str(i) for i in range(state['file_id_1'], state['file_id_2'] + 1)]
        state['file_id'] = ",".join(f_ids)
        
        state['step'] = "wait_number"
        await message.reply("Batch successfully adding\nEnter number (e.g. 05 - 15)")
        return

    elif step == "wait_number":
        state['episode_num'] = message.text
        state['step'] = "wait_confirm"
        await message.reply("/confirm")
        return

@app.on_message(filters.command("confirm") & filters.user(config.ADMINS))
async def confirm_cmd(client, message: Message):
    uid = message.from_user.id
    state = USER_STATE.get(uid)
    if state and state.get("step") == "wait_confirm":
        state['step'] = "wait_hmm"
        await message.reply("/hmm")

@app.on_message(filters.command("hmm") & filters.user(config.ADMINS))
async def hmm_cmd(client, message: Message):
    uid = message.from_user.id
    state = USER_STATE.get(uid)
    if state and state.get("step") == "wait_hmm":
        # Save to Database
        btn_text = f"Watch episode {state['episode_num']}"
        post_uuid = db.save_post(state['file_id'], btn_text)
        
        # Original long link
        bot_username = client.me.username
        long_link = f"https://t.me/{bot_username}?start={post_uuid}"
        
        state['final_url'] = long_link
        state['btn_text'] = btn_text
        state['step'] = "ready_to_send"
        
        # Post preview with button
        btn = InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, url=long_link)]])
        await client.copy_message(message.chat.id, message.chat.id, state['post_msg_id'], reply_markup=btn)
        
        await message.reply("Select Action:\n[ /send ] - 1 Channel\n[ /send_more ] - Multiple Channels")

@app.on_message(filters.command("send") & filters.user(config.ADMINS))
async def send_cmd(client, message: Message):
    uid = message.from_user.id
    state = USER_STATE.get(uid)
    if state and state.get("step") == "ready_to_send":
        # Note: Yaha channel list database ya config se fetch hogi
        state['step'] = "wait_channel_name"
        await message.reply("Channel name batao (Example: Gyani baba)")

@app.on_message(filters.command("hu_hu") & filters.user(config.ADMINS))
async def huhu_cmd(client, message: Message):
    uid = message.from_user.id
    state = USER_STATE.get(uid)
    if state and state.get("step") == "wait_huhu":
        target_id = state['target_id']
        db.add_premium_user(target_id)
        USER_STATE.pop(uid, None)
        await message.reply(f"Successfully add member {target_id} 🪄🪄🪄")

# --- RENDER PORT BINDING (WEB SERVER) ---
# Render free tier me bot sleep na ho aur deploy fail na ho isliye ye server zaroori hai
async def web_server():
    async def handle(request):
        return web.Response(text="Bot is running!")
    
    app_web = web.Application()
    app_web.router.add_get('/', handle)
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', config.PORT)
    await site.start()
    print(f"🌍 Web server started on port {config.PORT}")

async def main():
    await app.start()
    print("🤖 Anime Bot Started Successfully!")
    await web_server()
    await pyrogram.idle()

if __name__ == "__main__":
    import pyrogram
    app.run(main())
