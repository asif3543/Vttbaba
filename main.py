import os
import time
import asyncio
import gc
import threading
import tempfile
from collections import deque
from http.server import BaseHTTPRequestHandler, HTTPServer
from faster_whisper import WhisperModel
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from huggingface_hub import login

# ================= CONFIG =================
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")
DEST_CHANNEL = int(os.getenv("DEST_CHANNEL", "0"))  # ya username bhi de sakte ho
OWNER_ID = 5344078567
ALLOWED_USERS = [5344078567]
ALLOWED_GROUPS = [-1003899919015]

PORT = int(os.getenv("PORT", 10000))  # Render ke liye

# ================= DUMMY HTTP SERVER FOR RENDER =================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"SubGen Bot is running on Render!\n")

def run_http_server():
    try:
        server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
        print(f"✅ Dummy HTTP server started on port {PORT} for Render")
        server.serve_forever()
    except Exception as e:
        print(f"HTTP Server Error: {e}")

# ================= INIT =================
app = Client("SubGenBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

task_queue = deque()
queue_lock = asyncio.Lock()
is_processing = False
model = None
model_lock = asyncio.Lock()

# Per-user temporary storage for rename logic
users_data = {}
in_queue = set()
current_encoding = {}

# ================= UTILS =================
async def safe_reply(message: Message, text: str):
    try:
        return await message.reply_text(text)
    except Exception as e:
        print(f"Reply Error: {e}")
        return None

async def is_authorized(message: Message) -> bool:
    if not message or not message.from_user:
        return False
    uid = message.from_user.id
    if uid == OWNER_ID or uid in ALLOWED_USERS or message.chat.id in ALLOWED_GROUPS:
        return True
    await safe_reply(message, f"❌ Unauthorized ID: `{uid}`")
    return False

def format_timestamp(seconds: float, fmt: str):
    td = time.gmtime(seconds)
    ms = int((seconds % 1) * 1000)
    cs = int((seconds % 1) * 100)
    if fmt == "srt":
        return f"{time.strftime('%H:%M:%S', td)},{ms:03d}"
    elif fmt == "vtt":
        return f"{time.strftime('%H:%M:%S', td)}.{ms:03d}"
    else:  # ass
        ts = time.strftime('%H:%M:%S', td)
        return f"{ts[1:] if ts.startswith('0') else ts}.{cs:02d}"

async def download_with_verification(client, file_id, attempts=5):
    """Reliable download with retry and verification."""
    temp_dir = tempfile.gettempdir()
    base_name = f"temp_{int(time.time())}_{file_id}"
    for attempt in range(attempts):
        temp_file = os.path.join(temp_dir, f"{base_name}_{attempt}")
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            path = await client.download_media(file_id, file_name=temp_file)
            if path and os.path.exists(path) and os.path.getsize(path) > 0:
                return path
        except Exception as e:
            await asyncio.sleep(2*(attempt+1))
    raise Exception("Download failed after multiple attempts")

async def get_model():
    global model
    async with model_lock:
        if model is None:
            print("Loading Whisper Model (tiny)...")
            if HF_TOKEN:
                try:
                    login(token=HF_TOKEN)
                    print("✅ HF Login Successful")
                except Exception as e:
                    print(f"HF Login Error: {e}")
            try:
                model = WhisperModel(
                    "tiny",
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=max(2, os.cpu_count() or 4),
                    num_workers=1,
                    download_root="./model_cache"
                )
                print("✅ Model Loaded with int8!")
            except Exception as e:
                print(f"int8 failed: {e}. Trying float32 fallback...")
                model = WhisperModel(
                    "tiny",
                    device="cpu",
                    compute_type="float32",
                    cpu_threads=max(2, os.cpu_count() or 4),
                    num_workers=1,
                    download_root="./model_cache"
                )
                print("✅ Model Loaded with float32 fallback!")
        return model

def run_transcription(model, audio_path, out_file, fmt):
    try:
        segments, info = model.transcribe(
            audio_path,
            beam_size=5,
            vad_filter=True,
            word_timestamps=False
        )
        has_data = False
        with open(out_file, "w", encoding="utf-8") as f:
            if fmt == "vtt":
                f.write("WEBVTT\n\n")
            elif fmt == "ass":
                f.write("[Script Info]\nScriptType: v4.00+\n\n[Events]\nFormat: Layer, Start, End, Style, Text\n")
            for i, seg in enumerate(segments, 1):
                text = seg.text.strip()
                if not text:
                    continue
                has_data = True
                start = format_timestamp(seg.start, fmt)
                end = format_timestamp(seg.end, fmt)
                if fmt == "srt":
                    f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
                elif fmt == "vtt":
                    f.write(f"{start} --> {end}\n{text}\n\n")
                else:
                    f.write(f"Dialogue: 0,{start},{end},Default,{text}\n")
        return has_data
    except Exception as e:
        print(f"Transcription Error: {e}")
        return False

# ================= COMMANDS =================
@app.on_message(filters.command("start"))
async def start_cmd(_, message: Message):
    if await is_authorized(message):
        await safe_reply(message, "🔥 SubGen Bot Online!\nReply to video with /srt /vtt /ass")

@app.on_message(filters.command(["srt", "vtt", "ass"]))
async def handle_request(_, message: Message):
    if not await is_authorized(message):
        return
    reply = message.reply_to_message
    if not reply or not (reply.video or reply.document):
        return await safe_reply(message, "❌ Reply to a video or document file!")

    fmt = message.command[0].lower()
    users_data[message.from_user.id] = {
        "media": reply.video or reply.document,
        "format": fmt,
        "chat_id": message.chat.id
    }
    await safe_reply(message, f"✅ Added to queue (Position: {len(task_queue)+1})")

# ================= PROCESS TASK =================
async def process_task(task):
    global is_processing
    msg = task["msg"]
    media = task["media"]
    fmt = task["format"]
    uid = f"{msg.chat.id}_{msg.id}"
    v_path = f"v_{uid}.mp4"
    a_path = f"a_{uid}.mp3"
    out_file = f"sub_{uid}.{fmt}"

    try:
        status = await safe_reply(msg, "⏳ Downloading media...")
        await app.download_media(media.file_id, file_name=v_path)

        if status:
            await status.edit("🔊 Extracting audio...")
        cmd = ["ffmpeg", "-i", v_path, "-vn", "-ar", "16000", "-ac", "1", "-b:a", "32k", "-f", "mp3", a_path, "-y"]
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()
        os.remove(v_path)

        if status:
            await status.edit("🤖 Loading AI Model...")
        mdl = await get_model()
        if status:
            await status.edit(f"🤖 Transcribing ({fmt.upper()})...")
        loop = asyncio.get_event_loop()
        ok = await loop.run_in_executor(None, run_transcription, mdl, a_path, out_file, fmt)
        os.remove(a_path)

        if not ok:
            raise Exception("No speech detected")
        dest = DEST_CHANNEL if DEST_CHANNEL != 0 else msg.chat.id
        if status:
            await status.edit("📤 Uploading subtitle...")
        await app.send_document(dest, out_file, caption=f"✅ {fmt.upper()} Subtitles Generated")
        if status:
            await status.delete()
        os.remove(out_file)
    except Exception as e:
        print(f"Processing Error: {e}")
        if status:
            await status.edit(f"❌ Error: {str(e)[:80]}")
    finally:
        is_processing = False
        gc.collect()

# ================= QUEUE WORKER =================
async def worker():
    global is_processing
    while True:
        if users_data and not is_processing:
            is_processing = True
            user_id, task = next(iter(users_data.items()))
            try:
                await process_task({"msg": task["media"], "media": task["media"], "format": task["format"]})
                users_data.pop(user_id, None)
            except Exception as e:
                print(f"Worker Error: {e}")
                is_processing = False
        await asyncio.sleep(1)

# ================= MAIN =================
async def main():
    await app.start()
    try:
        await app.send_message(OWNER_ID, "✅ SubGen Bot Started Successfully on Render!")
    except:
        pass
    asyncio.create_task(worker())
    print("🚀 BOT RUNNING")
    await idle()

if __name__ == "__main__":
    threading.Thread(target=run_http_server, daemon=True).start()
    asyncio.run(main())
