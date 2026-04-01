import os
import time
import json
import asyncio
import threading
import tempfile
import re
from collections import deque
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import MessageNotModified, MessageIdInvalid
from http.server import HTTPServer, BaseHTTPRequestHandler

# ================= CONFIGURATION =================

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEST_CHANNEL = "@Sub_and_hardsub"
PORT = 10000

OWNER_ID = 5351848105
ALLOWED_USERS = [5344078567]
ALLOWED_GROUPS = [-1003899919015]

app = Client("EncoderBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

users_data = {}
task_queue = deque()
in_queue = set()
processing_lock = asyncio.Lock()
main_loop = None
edit = "Maintanence by: @Sub_and_hardsub"

current_encoding = {}

# ================= UTILS =================

def is_authorized(message: Message) -> bool:
    if not message.from_user: return False
    u_id = message.from_user.id    
    if message.text and message.text.lower().startswith("/start"): return True    
    if u_id == OWNER_ID or u_id in ALLOWED_USERS or message.chat.id in ALLOWED_GROUPS:
        return True
    return False

def is_owner(message: Message) -> bool:
    return message.from_user and message.from_user.id == OWNER_ID

async def get_duration(file):
    try:
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", file]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE)
        stdout, _ = await proc.communicate()
        data = json.loads(stdout.decode())
        return float(data.get("format", {}).get("duration", 0))
    except:
        return 0

def format_progress_bar(percent, width=10):
    filled = int(percent * width / 100)
    return "█" * filled + "░" * (width - filled)

async def safe_edit(message: Message, text: str):
    try:
        await message.edit(text)
    except:
        pass

# ================= DOWNLOAD =================

async def download_with_verification(client, file_id, status_msg, phase="Downloading"):
    temp_dir = tempfile.gettempdir()
    base_name = f"temp_{int(time.time())}_{file_id}"
    
    for attempt in range(5):
        temp_file = os.path.join(temp_dir, f"{base_name}_{attempt}")
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
            path = await client.download_media(file_id, file_name=temp_file)
            if path and os.path.exists(path) and os.path.getsize(path) > 0:
                return path
        except:
            await asyncio.sleep(3)
    raise Exception("Download failed")

# ================= ENCODER =================

async def encode_with_progress(video_path, subtitle_path, output_path, total_duration, status_msg, user_id):
    escaped_sub = subtitle_path.replace("\\", "\\\\").replace("'", "'\\\\''")

    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"subtitles=filename='{escaped_sub}'",
        "-c:v", "libx264",
        "-preset", "superfast",   # FIX
        "-crf", "28",             # FIX
        "-threads", "1",          # FIX
        "-max_muxing_queue_size", "1024",
        "-c:a", "copy",
        "-progress", "pipe:1",
        "-y", output_path
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    current_encoding[user_id] = process
    last_update = 0
    progress_data = {}

    while True:
        line = await process.stdout.readline()
        if not line:
            break

        line = line.decode().strip()
        if "=" in line:
            key, val = line.split("=", 1)
            progress_data[key] = val

        if key == "out_time_ms":
            try:
                ms = int(progress_data.get("out_time_ms", 0))
                sec = ms / 1_000_000
                percent = (sec / total_duration) * 100 if total_duration else 0

                if time.time() - last_update > 10:  # FIX
                    bar = format_progress_bar(percent)
                    await safe_edit(status_msg, f"🔥 Encoding...\n`{bar}` {percent:.1f}%")
                    last_update = time.time()
            except:
                pass

    try:
        await asyncio.wait_for(process.wait(), timeout=900)  # FIX
    except:
        process.kill()
        raise Exception("Encoding timeout")

    current_encoding.pop(user_id, None)

    if not os.path.exists(output_path):
        raise Exception("Encoding failed")

    return True

# ================= HANDLERS =================

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply(f"🔥 Bot Online!\n\n{edit}")

@app.on_message(filters.command("hsub"))
async def hsub(client, message: Message):
    if not is_authorized(message): return
    r = message.reply_to_message
    if not r or not (r.video or r.document):
        return await message.reply("Reply video")

    users_data[message.from_user.id] = {
        "video": {"file_id": (r.video or r.document).file_id, "file_name": "video.mp4"},
        "chat_id": message.chat.id,
        "state": "WAIT_SUB"
    }
    await message.reply("Send subtitle")

@app.on_message(filters.document)
async def sub(client, message: Message):
    uid = message.from_user.id
    if uid not in users_data: return

    users_data[uid]["subtitle"] = {"file_id": message.document.file_id}
    task_queue.append(users_data.pop(uid))
    await message.reply("Added to queue")

# ================= WORKER =================

async def worker():
    while True:
        if not task_queue:
            await asyncio.sleep(5)
            continue

        task = task_queue.popleft()
        uid = task["chat_id"]

        status = await app.send_message(uid, "Processing...")

        try:
            v = await download_with_verification(app, task["video"]["file_id"], status)

            if os.path.getsize(v) > 300 * 1024 * 1024:  # FIX
                await status.edit("Too big")
                continue

            s = await download_with_verification(app, task["subtitle"]["file_id"], status)

            out = "output.mp4"
            dur = await get_duration(v)

            await encode_with_progress(v, s, out, dur, status, uid)

            await app.send_document(uid, out)

            await status.edit("Done")

        except Exception as e:
            await status.edit(str(e))

        finally:
            try:
                for f in os.listdir(tempfile.gettempdir()):
                    os.remove(os.path.join(tempfile.gettempdir(), f))
            except:
                pass

# ================= HEALTH =================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def do_HEAD(self):  # FIX
        self.send_response(200)
        self.end_headers()

def run_server():
    HTTPServer(("0.0.0.0", PORT), HealthHandler).serve_forever()

# ================= MAIN =================

async def main():
    if edit != "Maintanence by: @Sub_and_hardsub":
        return
    await app.start()
    print("Bot started")
    asyncio.create_task(worker())
    await idle()

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.get_event_loop().run_until_complete(main())
