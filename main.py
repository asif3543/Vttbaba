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
        self.end_headers()
        self.wfile.write(b"SubGen Bot is Live!")

def run_http_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()

# ================= INIT =================
app = Client("SubGenBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

task_queue = deque()
queue_lock = asyncio.Lock()
# Yeh event ensure karega ki ek time pe ek hi task chale bina race condition ke
processing_event = asyncio.Event() 
processing_event.set() 

model = None
model_lock = asyncio.Lock()

# ================= UTILS =================
def is_authorized(message: Message) -> bool:
    if not message.from_user: return False
    u_id = message.from_user.id
    return u_id == OWNER_ID or u_id in ALLOWED_USERS or message.chat.id in ALLOWED_GROUPS

def format_timestamp(seconds: float, fmt: str):
    td = time.gmtime(seconds)
    ms = int((seconds % 1) * 1000)
    if fmt == "srt":
        return f"{time.strftime('%H:%M:%S', td)},{ms:03d}"
    return f"{time.strftime('%H:%M:%S', td)}.{ms:03d}"

async def get_model():
    global model
    async with model_lock:
        if model is None:
            if HF_TOKEN:
                try: login(token=HF_TOKEN)
                except: pass
            model = WhisperModel("tiny", device="cpu", compute_type="int8")
        return model

def run_transcription(model, audio_path, out_file, fmt):
    try:
        # SYNC SAFE: No VAD filter to ensure perfect timing
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
@app.on_message(filters.command(["srt", "vtt"]))
async def handle_request(client, message: Message):
    if not is_authorized(message): return
    
    target = message.reply_to_message
    if not target or not (target.video or target.document or target.audio):
        return await message.reply("❌ Reply to a video/audio file.")

    fmt = message.command[0].lower()
    async with queue_lock:
        task_queue.append({"msg": message, "media": target, "format": fmt})
    
    await message.reply(f"✅ Added to Queue. Position: {len(task_queue)}")

# ================= CORE PROCESSOR =================
async def process_task(task):
    msg = task["msg"]
    media = task["media"]
    fmt = task["format"]
    
    status = await msg.reply("⏳ **Processing started...**")
    v_path = a_path = out_file = None
    uid = f"{msg.from_user.id}_{int(time.time())}"

    try:
        # 1. Download
        await status.edit("📥 **Downloading media...**")
        v_path = await app.download_media(media)
        
        # 2. Extract Audio
        await status.edit("🔊 **Extracting Audio (FFmpeg)...**")
        a_path = f"track_{uid}.mp3"
        cmd = ["ffmpeg", "-i", v_path, "-vn", "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1", a_path, "-y"]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await proc.wait()

        # 3. Transcribe
        await status.edit("🤖 **AI Transcribing (Linear Sync)...**")
        mdl = await get_model()
        out_file = f"Sub_{uid}.{fmt}"
        
        loop = asyncio.get_running_loop()
        success = await loop.run_in_executor(None, run_transcription, mdl, a_path, out_file, fmt)

        if success:
            await status.edit("📤 **Uploading...**")
            dest = DEST_CHANNEL if DEST_CHANNEL != 0 else msg.chat.id
            await app.send_document(dest, out_file, caption=f"✅ {fmt.upper()} Generated")
            await status.delete()
        else:
            await status.edit("❌ Transcription failed.")

    except Exception as e:
        await status.edit(f"❌ Error: `{str(e)[:100]}`")
    finally:
        for f in [v_path, a_path, out_file]:
            if f and os.path.exists(f): os.remove(f)
        gc.collect()

async def queue_worker():
    while True:
        await asyncio.sleep(1)
        if task_queue and processing_event.is_set():
            processing_event.clear() # Lock processing
            async with queue_lock:
                current_task = task_queue.popleft()
            
            try:
                await process_task(current_task)
            except Exception as e:
                print(f"Worker Error: {e}")
            finally:
                processing_event.set() # Release lock

# ================= MAIN =================
async def main():
    threading.Thread(target=run_http_server, daemon=True).start()
    await app.start()
    asyncio.create_task(queue_worker())
    print("🚀 Bot is Online with Processing Lock!")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
    
