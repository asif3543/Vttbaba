import os
import time
import asyncio
import gc
import threading
import subprocess
from collections import deque
from http.server import BaseHTTPRequestHandler, HTTPServer
from faster_whisper import WhisperModel
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from huggingface_hub import login

# ================= CONFIGURATION =================
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")
DEST_CHANNEL = int(os.getenv("DEST_CHANNEL", "0"))

OWNER_ID = 5344078567
ALLOWED_USERS = [5351848105, 5344078567]
ALLOWED_GROUPS = [-1003810374456]

PORT = int(os.getenv("PORT", 10000))

# ================= DUMMY HTTP SERVER =================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"SubGen Bot is running!\n")

def run_http_server():
    try:
        server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
        server.serve_forever()
    except Exception as e:
        print(f"HTTP Server Error: {e}")

# ================= INIT =================
app = Client("SubGenBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

task_queue = deque()
queue_lock = asyncio.Lock()
is_processing = False
model = None
active_processes = {}

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
            try: login(token=HF_TOKEN, add_to_git_credential=False)
            except: pass
        # Render free tier ke liye 'tiny' best hai
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return model

def run_transcription(model, audio_path, out_file, fmt):
    try:
        # SYNC FIX: vad_filter=False taaki timing exact rahe
        segments, _ = model.transcribe(
            audio_path, 
            beam_size=5, 
            vad_filter=False, 
            word_timestamps=False
        )
        
        with open(out_file, "w", encoding="utf-8") as f:
            if fmt == "vtt": f.write("WEBVTT\n\n")
            for i, seg in enumerate(segments, 1):
                start = format_timestamp(seg.start, fmt)
                end = format_timestamp(seg.end, fmt)
                text = seg.text.strip()
                if not text: continue
                
                if fmt == "srt":
                    f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
                else:
                    f.write(f"{start} --> {end}\n{text}\n\n")
        return os.path.exists(out_file) and os.path.getsize(out_file) > 0
    except Exception as e:
        print(f"Transcription error: {e}")
        return False

# ================= HANDLERS =================
@app.on_message(filters.command("start"))
async def start_cmd(_, message: Message):
    await message.reply("<b>🔥 SubGen Bot Online!</b>\n\nReply to any video/audio with <code>/srt</code> or <code>/vtt</code>")

@app.on_message(filters.command(["srt", "vtt"]))
async def handle_request(_, message: Message):
    if not is_authorized(message): return
    
    replied = message.reply_to_message
    if not replied or not (replied.video or replied.document or replied.audio):
        return await message.reply("❌ Reply to a video/audio file.")

    fmt = message.command[0].lower()
    async with queue_lock:
        task_queue.append({"msg": message, "media": replied, "format": fmt})
    
    await message.reply(f"✅ Added to Queue. Position: {len(task_queue)}")

# ================= CORE PROCESSOR =================
async def process_task(task):
    global is_processing
    msg = task["msg"]
    media = task["media"]
    fmt = task["format"]
    
    status = await msg.reply("⏳ <b>Downloading...</b>")
    v_path = a_path = out_file = None
    uid = f"{msg.from_user.id}_{int(time.time())}"

    try:
        v_path = await app.download_media(media)
        
        await status.edit("🔊 <b>Extracting Audio...</b>")
        a_path = f"track_{uid}.mp3"
        cmd = ["ffmpeg", "-i", v_path, "-vn", "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1", a_path, "-y"]
        process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await process.wait()

        await status.edit(f"🤖 <b>AI Transcribing ({fmt.upper()})...</b>")
        mdl = await get_model()
        out_file = f"Sub_{uid}.{fmt}"
        
        loop = asyncio.get_running_loop()
        success = await loop.run_in_executor(None, run_transcription, mdl, a_path, out_file, fmt)

        if success:
            await status.edit("📤 <b>Uploading...</b>")
            dest = DEST_CHANNEL if DEST_CHANNEL != 0 else msg.chat.id
            await app.send_document(dest, out_file, caption=f"✅ {fmt.upper()} Subtitle Generated")
            await status.delete()
        else:
            await status.edit("❌ Transcription failed.")

    except Exception as e:
        await status.edit(f"❌ Error: {str(e)[:100]}")
    finally:
        for f in [v_path, a_path, out_file]:
            if f and os.path.exists(f): os.remove(f)
        is_processing = False
        gc.collect()

async def queue_worker():
    global is_processing
    while True:
        if not task_queue or is_processing:
            await asyncio.sleep(2)
            continue
        
        is_processing = True
        async with queue_lock:
            current_task_data = task_queue.popleft()
        await process_task(current_task_data)

async def main():
    threading.Thread(target=run_http_server, daemon=True).start()
    await app.start()
    asyncio.create_task(queue_worker())
    print("🚀 Bot Started!")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
