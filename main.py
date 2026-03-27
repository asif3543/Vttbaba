

import os
import re
import gc
import time
import json
import asyncio
import threading
import subprocess
from collections import deque
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatType
from http.server import BaseHTTPRequestHandler, HTTPServer
from faster_whisper import WhisperModel
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from huggingface_hub import login

# ================= CONFIGURATION =================
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")
DEST_CHANNEL = int(os.getenv("DEST_CHANNEL", "0"))

OWNER_ID = 5344078567
ALLOWED_USERS = [5351848105]
ALLOWED_GROUPS = [-1003899919015]
PORT = int(os.getenv("PORT", 10000))

# ================= DUMMY SERVER =================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"SubGen Bot is Running!")

def run_http_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()

# ================= INIT =================
app = Client("SubGenBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Global Variables (Encoder Style)
users_waiting = {}  
task_queue = deque()
current_user = None
current_task = None
queue_lock = asyncio.Lock()
in_queue = set()
model = None

# ================= UTILS =================
def is_authorized(message: Message) -> bool:
    if not message.from_user: return False
    u_id = message.from_user.id
    if u_id == OWNER_ID or u_id in ALLOWED_USERS or message.chat.id in ALLOWED_GROUPS:
        return True
    return False

def format_timestamp(seconds: float, fmt: str):
    td = time.gmtime(seconds)
    ms = int((seconds % 1) * 1000)
    if fmt == "srt":
        return f"{time.strftime('%H:%M:%S', td)},{ms:03d}"
    return f"{time.strftime('%H:%M:%S', td)}.{ms:03d}"

async def get_model():
    global model
    if model is None:
        if HF_TOKEN:
            try: login(token=HF_TOKEN)
            except: pass
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return model

def run_transcription(model, audio_path, out_file, fmt):
    try:
        # SYNC SAFE: vad_filter=False
        segments, _ = model.transcribe(audio_path, beam_size=5, vad_filter=False)
        with open(out_file, "w", encoding="utf-8") as f:
            if fmt == "vtt": f.write("WEBVTT\n\n")
            for i, seg in enumerate(segments, 1):
                start, end = format_timestamp(seg.start, fmt), format_timestamp(seg.end, fmt)
                text = seg.text.strip()
                if not text: continue
                if fmt == "srt":
                    f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
                else:
                    f.write(f"{start} --> {end}\n{text}\n\n")
        return os.path.exists(out_file) and os.path.getsize(out_file) > 0
    except: return False

# ================= HANDLERS =================

@app.on_message(filters.command("start"))
async def start_cmd(_, message: Message):
    await message.reply("<b>🔥 AI Subtitle Generator Online!</b>\n\nSend me a video or reply to one to start.")

@app.on_message(filters.command("delete"))
async def delete_handler(_, message: Message):
    if not is_authorized(message): return
    global task_queue, in_queue, current_user
    task_queue.clear()
    in_queue.clear()
    current_user = None
    await message.reply("🗑️ **Queue and tasks cleared!**")

@app.on_message(filters.video | filters.document | filters.audio)
async def media_handler(client, message: Message):
    if not is_authorized(message): return
    
    media = message.video or message.document or message.audio
    if message.document and not message.document.mime_type.startswith(("video/", "audio/")):
        return # Ignore non-media docs
    
    user_id = message.from_user.id
    users_waiting[user_id] = {"media": media}
    
    # Encoder Style Buttons
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Generate SRT", callback_data="fmt_srt")],
        [InlineKeyboardButton("Generate VTT", callback_data="fmt_vtt")]
    ])
    await message.reply("🎯 **Select Subtitle Format:**", reply_markup=buttons)

@app.on_callback_query(filters.regex("^fmt_"))
async def callback_handler(client, query):
    user_id = query.from_user.id
    if user_id not in users_waiting:
        return await query.answer("❌ Error: Session expired. Send media again.", show_alert=True)
    
    fmt = query.data.split("_")[1]
    media = users_waiting[user_id]["media"]
    
    async with queue_lock:
        task_queue.append({'user_id': user_id, 'message': query.message, 'media': media, 'format': fmt})
        in_queue.add(user_id)
    
    await query.message.edit(f"✅ **Added to Queue.** Format: {fmt.upper()}\nPosition: {len(task_queue)}")
    del users_waiting[user_id]

# ================= CORE LOGIC =================

async def process_task(client, user_id, original_msg, media, fmt):
    status = await original_msg.reply("⚙️ **Starting Process...**")
    v_path = a_path = out_file = None
    uid = f"{user_id}_{int(time.time())}"

    try:
        await status.edit("📥 **Downloading Media...**")
        v_path = await client.download_media(media)
        
        await status.edit("🔊 **Extracting Audio...**")
        a_path = f"audio_{uid}.mp3"
        # Fast extraction settings
        cmd = ["ffmpeg", "-i", v_path, "-vn", "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1", a_path, "-y"]
        process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await process.wait()

        await status.edit(f"🤖 **AI Transcribing ({fmt.upper()})...**")
        mdl = await get_model()
        out_file = f"Sub_{uid}.{fmt}"
        
        loop = asyncio.get_running_loop()
        success = await loop.run_in_executor(None, run_transcription, mdl, a_path, out_file, fmt)

        if success:
            await status.edit("📤 **Uploading Result...**")
            dest = DEST_CHANNEL if DEST_CHANNEL != 0 else original_msg.chat.id
            await client.send_document(
                chat_id=dest,
                document=out_file,
                caption=f"✅ **{fmt.upper()} Generated**\n\n🆔 User: `{user_id}`"
            )
            await status.delete()
        else:
            await status.edit("❌ **Transcription Failed!**")
            
    except Exception as e:
        await status.edit(f"❌ **Error:** `{str(e)[:100]}`")
    finally:
        for f in [v_path, a_path, out_file]:
            if f and os.path.exists(f): os.remove(f)
        gc.collect()

async def queue_worker():
    global current_user, current_task
    while True:
        if not task_queue or current_user:
            await asyncio.sleep(5)
            continue
        
        async with queue_lock:
            task = task_queue.popleft()
            current_user = task['user_id']
            if current_user in in_queue: in_queue.remove(current_user)
        
        try:
            current_task = asyncio.create_task(
                process_task(app, current_user, task['message'], task['media'], task['format'])
            )
            await current_task
        except Exception as e:
            print(f"Worker Error: {e}")
        finally:
            current_user = None

# ================= START =================
async def main():
    threading.Thread(target=run_http_server, daemon=True).start()
    await app.start()
    print("🚀 Bot is Online!")
    asyncio.create_task(queue_worker())
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
