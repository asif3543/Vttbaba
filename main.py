import os
import gc
import time
import asyncio
import threading
from collections import deque
from http.server import BaseHTTPRequestHandler, HTTPServer

from pyrogram import Client, filters, idle
from pyrogram.types import Message
from faster_whisper import WhisperModel

# ================= CONFIG =================

API_ID = int(os.getenv("API_ID", "0"))   # 👈 Render se lega
API_HASH = os.getenv("API_HASH", "")     # 👈 Render se lega

BOT_TOKEN = "8397073883:AAEUc_qW_dzmxBzrHZehoczWl3MFY0Z4WNM"  # 🔥 FIXED TOKEN (yaha daal de apna)

PORT = int(os.getenv("PORT", "10000"))

# ================= SAFETY CHECK =================

if API_ID == 0 or API_HASH == "":
    raise ValueError("❌ API_ID / API_HASH missing (Render me daal)")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN missing")

# ================= SERVER =================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Running")

def run_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()

# ================= BOT =================

app = Client(
    "SubGenBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

task_queue = deque()
queue_lock = asyncio.Lock()
model = None

# ================= MODEL =================

def load_model():
    global model
    if model is None:
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return model

# ================= TIME =================

def format_time(sec, fmt):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)

    if fmt == "srt":
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    return f"{h:02}:{m:02}:{s:02}.{ms:03}"

# ================= TRANSCRIBE =================

def generate_sub(model, audio, output, fmt):
    segments, _ = model.transcribe(audio, vad_filter=False)

    with open(output, "w", encoding="utf-8") as f:
        if fmt == "vtt":
            f.write("WEBVTT\n\n")

        for i, seg in enumerate(segments, 1):
            text = seg.text.strip()
            if not text:
                continue

            start = format_time(seg.start, fmt)
            end = format_time(seg.end, fmt)

            if fmt == "srt":
                f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
            else:
                f.write(f"{start} --> {end}\n{text}\n\n")

# ================= COMMANDS =================

@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply("🔥 Bot Online!\n\nReply video with /srt or /vtt")

@app.on_message(filters.command(["srt", "vtt"]))
async def add_queue(client, message):

    if not message.reply_to_message:
        return await message.reply("⚠️ Reply to a video")

    fmt = message.command[0]

    async with queue_lock:
        task_queue.append({
            "msg": message,
            "fmt": fmt
        })

    await message.reply(f"✅ Added to queue ({len(task_queue)})")

# ================= WORKER =================

async def worker():
    while True:

        if not task_queue:
            await asyncio.sleep(2)
            continue

        async with queue_lock:
            task = task_queue.popleft()

        msg = task["msg"]
        fmt = task["fmt"]

        status = await msg.reply("⏳ Processing...")

        video = f"v_{msg.id}.mp4"
        audio = f"a_{msg.id}.mp3"
        sub = f"sub_{msg.id}.{fmt}"

        try:
            await app.download_media(msg.reply_to_message, file_name=video)

            await status.edit("🎵 Extracting...")

            proc = await asyncio.create_subprocess_shell(
                f"ffmpeg -i {video} -vn -ar 16000 -ac 1 {audio} -y",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await proc.wait()

            await status.edit("🤖 Transcribing...")

            mdl = load_model()
            await asyncio.to_thread(generate_sub, mdl, audio, sub, fmt)

            await status.edit("⬆️ Uploading...")

            await msg.reply_document(sub)

            await status.delete()

        except Exception as e:
            await status.edit(f"❌ Error: {str(e)[:50]}")

        finally:
            for f in [video, audio, sub]:
                if os.path.exists(f):
                    os.remove(f)
            gc.collect()

# ================= MAIN =================

async def main():
    threading.Thread(target=run_server, daemon=True).start()

    await app.start()
    print("✅ BOT STARTED")

    asyncio.create_task(worker())

    await idle()

if __name__ == "__main__":
    asyncio.run(main())
