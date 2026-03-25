import os
import time
import asyncio
import subprocess
import gc
from collections import deque
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from faster_whisper import WhisperModel
from flask import Flask
from threading import Thread

# ================= CONFIGURATION =================
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DEST_CHANNEL = int(os.environ.get("DEST_CHANNEL", "0"))

OWNER_ID = 5344078567
ALLOWED_USERS = [5351848105, OWNER_ID]
ALLOWED_GROUPS = [-1003899919015]

app = Client("SubGenEncoderBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Queue system
task_queue = deque()
is_processing = False
cancel_flag = {} # UserID-wise skip flag

# ================= FLASK (Keep-Alive) =================
flask_app = Flask(__name__)
@flask_app.route('/')
def health(): return "Bot is Online with Queue & AI! ✅"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# ================= UTILS =================
def is_authorized(message: Message) -> bool:
    u_id = message.from_user.id if message.from_user else 0
    return (u_id in ALLOWED_USERS or message.chat.id in ALLOWED_GROUPS)

def format_timestamp(seconds: float, mode: str = "srt") -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    if mode == "vtt": return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

async def cleanup(files):
    for f in files:
        if f and os.path.exists(f):
            try: os.remove(f)
            except: pass
    gc.collect()

# ================= CORE AI TRANSCRIPTION =================
async def transcribe_logic(client, message, mode, replied):
    user_id = message.from_user.id
    status = await message.reply(f"⏳ {mode.upper()} process start ho raha hai...")
    
    v_path = a_path = s_path = None
    try:
        # 1. Download & Extract Audio
        await status.edit("⬇️ Downloading & Extracting Audio...")
        v_path = await client.download_media(replied)
        a_path = f"audio_{user_id}.wav"
        
        # FFmpeg audio extract (16k mono is best for Whisper)
        cmd = ["ffmpeg", "-i", v_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-y", a_path]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(v_path): os.remove(v_path) # Delete video early

        if cancel_flag.get(user_id): return await status.edit("⏹️ Skipped!")

        # 2. AI Process
        await status.edit("🤖 AI Subtitles generate kar raha hai...")
        # Model loading (inside function to save RAM)
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, info = model.transcribe(a_path, beam_size=1)

        s_path = f"sub_{user_id}.{mode}"
        with open(s_path, "w", encoding="utf-8") as f:
            if mode == "vtt": f.write("WEBVTT\n\n")
            for i, segment in enumerate(segments, start=1):
                if cancel_flag.get(user_id): break
                f.write(f"{i}\n{format_timestamp(segment.start, mode)} --> {format_timestamp(segment.end, mode)}\n{segment.text.strip()}\n\n")

        # 3. Upload
        if not cancel_flag.get(user_id):
            caption = f"✅ Done!\n🌍 Lang: {info.language.upper()}\n📄 Format: {mode.upper()}"
            if DEST_CHANNEL:
                await client.send_document(DEST_CHANNEL, s_path, caption=caption)
            await client.send_document(message.chat.id, s_path, caption=caption, reply_to_message_id=replied.id)
            await status.delete()
        else:
            await status.edit("⏹️ Process Skipped.")

    except Exception as e:
        await status.edit(f"❌ Error: {str(e)}")
    finally:
        await cleanup([v_path, a_path, s_path])
        del model # Force RAM release

# ================= QUEUE WORKER =================
async def worker():
    global is_processing
    while True:
        if task_queue:
            is_processing = True
            task = task_queue.popleft()
            await transcribe_logic(task['client'], task['message'], task['mode'], task['replied'])
            is_processing = False
        await asyncio.sleep(2)

# ================= HANDLERS =================
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("🔥 **AI Subtitle & Encoder Bot**\n\nCommands:\n`/srt` - Video to SRT\n`/vtt` - Video to VTT\n`/skip` - Cancel Task\n`/refresh` - Clear RAM/Files")

@app.on_message(filters.command(["srt", "vtt"]) & filters.reply)
async def sub_handler(client, message):
    if not is_authorized(message): return
    replied = message.reply_to_message
    if not (replied.video or replied.document or replied.audio):
        return await message.reply("❌ Video ya audio par reply karein!")
    
    mode = message.command[0]
    user_id = message.from_user.id
    cancel_flag[user_id] = False
    
    task_queue.append({'client': client, 'message': message, 'mode': mode, 'replied': replied})
    await message.reply(f"✅ Queue me add ho gaya! Position: {len(task_queue)}")

@app.on_message(filters.command("skip"))
async def skip_handler(client, message):
    user_id = message.from_user.id
    cancel_flag[user_id] = True
    await message.reply("⏹️ Agli process ya current process skip ho jayegi.")

@app.on_message(filters.command("refresh"))
async def refresh_handler(client, message):
    if not is_authorized(message): return
    await cleanup(os.listdir("."))
    await message.reply("🧹 Junk files deleted and Memory Refreshed!")

# ================= MAIN RUN =================
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    asyncio.get_event_loop().create_task(worker())
    print("🚀 Bot is running...")
    app.run()
