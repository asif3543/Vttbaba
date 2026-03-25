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
DEST_CHANNEL = int(os.environ.get("DEST_CHANNEL", "0")) # Render Env me daalna (-100...)

OWNER_ID = 5344078567
ALLOWED_USERS = [5351848105, OWNER_ID]
ALLOWED_GROUPS = [-1003899919015]

app = Client("VttBabaBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Queue system for 512MB RAM
task_queue = deque()
is_processing = False
cancel_tasks = set()

# ================= FLASK HEALTH CHECK =================
flask_app = Flask(__name__)
@flask_app.route('/')
def health(): return "Bot is Running Live! ✅"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# ================= UTILS =================
def is_authorized(message: Message) -> bool:
    u_id = message.from_user.id if message.from_user else 0
    return (u_id in ALLOWED_USERS or message.chat.id in ALLOWED_GROUPS)

def format_time(seconds: float, mode: str = "srt") -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    if mode == "vtt": return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

# ================= CORE AI TRANSCRIPTION =================
async def run_transcription(client, message, mode, replied):
    user_id = message.from_user.id
    status = await message.reply(f"🚀 {mode.upper()} Process Started...")
    
    v_path = a_path = s_path = None
    try:
        # 1. Download & Extract Audio (Streaming logic to save RAM)
        await status.edit("⬇️ Downloading & Extracting Audio...")
        v_path = await client.download_media(replied)
        a_path = f"audio_{message.id}.wav"
        
        # Audio extraction (Whisper likes 16k mono)
        cmd = ["ffmpeg", "-i", v_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-y", a_path]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(v_path): os.remove(v_path) # Turant video delete karo

        if user_id in cancel_tasks: return await status.edit("⏹️ Skipped!")

        # 2. AI Transcribe (Load model only when needed)
        await status.edit("🤖 AI generating subtitles... (Wait)")
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, info = model.transcribe(a_path, beam_size=1)

        s_path = f"sub_{message.id}.{mode}"
        with open(s_path, "w", encoding="utf-8") as f:
            if mode == "vtt": f.write("WEBVTT\n\n")
            for i, segment in enumerate(segments, start=1):
                if user_id in cancel_tasks: break
                start = format_time(segment.start, mode)
                end = format_time(segment.end, mode)
                f.write(f"{i}\n{start} --> {end}\n{segment.text.strip()}\n\n")

        # 3. Sending results
        if user_id not in cancel_tasks:
            caption = f"✅ **Subtitles Done!**\n🌍 Lang: {info.language.upper()}\n📄 Format: {mode.upper()}"
            
            # Destination Channel me bhej raha hai
            if DEST_CHANNEL != 0:
                await client.send_document(DEST_CHANNEL, s_path, caption=caption + f"\n👤 User: {message.from_user.mention}")
            
            # User ko reply me bhej raha hai
            await client.send_document(message.chat.id, s_path, caption=caption, reply_to_message_id=replied.id)
            await status.delete()
        else:
            await status.edit("⏹️ Skipped mid-way.")

    except Exception as e:
        await status.edit(f"❌ Error: {str(e)}")
    finally:
        # Cleanup everything
        for f in [v_path, a_path, s_path]:
            if f and os.path.exists(f): os.remove(f)
        if user_id in cancel_tasks: cancel_tasks.remove(user_id)
        gc.collect()

# ================= QUEUE WORKER =================
async def worker():
    global is_processing
    while True:
        if task_queue:
            is_processing = True
            task = task_queue.popleft()
            await run_transcription(task['c'], task['m'], task['mode'], task['r'])
            is_processing = False
        await asyncio.sleep(2)

# ================= HANDLERS =================
@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply("🔥 **VttBaba SubGen Online!**\n\nReply to video with `/srt` or `/vtt`.\nUse `/skip` to stop, `/refresh` to clean.")

@app.on_message(filters.command(["srt", "vtt"]) & filters.reply)
async def sub_trigger(client, message):
    if not is_authorized(message): return
    replied = message.reply_to_message
    if not (replied.video or replied.document or replied.audio):
        return await message.reply("❌ Video/Audio file par reply karo!")
    
    mode = message.command[0]
    task_queue.append({'c': client, 'm': message, 'mode': mode, 'r': replied})
    await message.reply(f"⏳ Added to Queue. Position: {len(task_queue)}")

@app.on_message(filters.command("skip"))
async def skip_cmd(client, message):
    cancel_tasks.add(message.from_user.id)
    await message.reply("⏹️ Your current task will be skipped.")

@app.on_message(filters.command("refresh"))
async def refresh_cmd(client, message):
    if not is_authorized(message): return
    for f in os.listdir("."):
        if f.endswith((".wav", ".srt", ".vtt", ".mp4", ".mkv")):
            try: os.remove(f)
            except: pass
    gc.collect()
    await message.reply("🧹 Storage and RAM Refreshed!")

# ================= RUN BOT =================
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    asyncio.get_event_loop().create_task(worker())
    print("🚀 Bot is running...")
    app.run()
