import os
import time
import json
import asyncio
import threading
import tempfile
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
current_encoding = {}

edit = "Maintanence by: @Sub_and_hardsub"

# ================= UTILS =================

def is_authorized(message: Message):
    if not message.from_user:
        return False
    if message.text and message.text.lower().startswith("/start"):
        return True
    return (
        message.from_user.id == OWNER_ID
        or message.from_user.id in ALLOWED_USERS
        or message.chat.id in ALLOWED_GROUPS
    )

def is_owner(message: Message):
    return message.from_user and message.from_user.id == OWNER_ID

async def safe_edit(message: Message, text: str):
    try:
        await message.edit(text)
    except:
        pass

def progress_bar(p):
    filled = int(p / 10)
    return "█" * filled + "░" * (10 - filled)

# ================= DOWNLOAD =================

async def download_file(client, file_id):
    path = await client.download_media(file_id)
    if not path or not os.path.exists(path):
        raise Exception("Download failed")
    return path

# ================= ENCODER =================

async def encode(video, sub, out, duration, msg, uid):
    cmd = [
        "ffmpeg", "-i", video,
        "-vf", f"subtitles='{sub}'",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "26",
        "-threads", "2",
        "-c:a", "copy",
        "-progress", "pipe:1",
        "-y", out
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    current_encoding[uid] = process
    last = 0

    while True:
        line = await process.stdout.readline()
        if not line:
            break

        if b"out_time_ms" in line:
            try:
                ms = int(line.decode().split("=")[1])
                sec = ms / 1_000_000
                percent = (sec / duration) * 100 if duration else 0

                if time.time() - last > 8:
                    await safe_edit(msg, f"🔥 Encoding\n{progress_bar(percent)} {percent:.1f}%")
                    last = time.time()
            except:
                pass

    await process.wait()
    current_encoding.pop(uid, None)

    if not os.path.exists(out):
        raise Exception("Encoding failed")

# ================= COMMANDS =================

@app.on_message(filters.command("start"))
async def start(client, m):
    await m.reply("🔥 Bot Online!\nUse /hsub")

@app.on_message(filters.command("delete"))
async def delete(client, m):
    if not is_owner(m):
        return await m.reply("❌ Owner only")
    task_queue.clear()
    users_data.clear()
    await m.reply("🗑 Cleared")

@app.on_message(filters.command("cancel"))
async def cancel(client, m):
    uid = m.from_user.id

    if uid in current_encoding:
        proc = current_encoding[uid]
        proc.kill()
        current_encoding.pop(uid, None)
        return await m.reply("🛑 Cancelled")

    await m.reply("❌ No task")

@app.on_message(filters.command("hsub"))
async def hsub(client, m):
    if not is_authorized(m):
        return

    r = m.reply_to_message
    if not r or not (r.video or r.document):
        return await m.reply("Reply to video")

    users_data[m.from_user.id] = {
        "video": r.video.file_id if r.video else r.document.file_id,
        "chat": m.chat.id,
        "state": "sub"
    }
    await m.reply("Send subtitle")

@app.on_message(filters.document)
async def sub(client, m):
    uid = m.from_user.id
    if uid not in users_data:
        return

    if users_data[uid]["state"] == "sub":
        users_data[uid]["sub"] = m.document.file_id
        task_queue.append(users_data.pop(uid))
        await m.reply(f"✅ Added to queue {len(task_queue)}")

# ================= WORKER =================

async def worker():
    while True:
        if not task_queue:
            await asyncio.sleep(5)
            continue

        task = task_queue.popleft()
        uid = uid = task["chat"]

        msg = await app.send_message(task["chat"], "⏳ Processing")

        try:
            v = await download_file(app, task["video"])
            s = await download_file(app, task["sub"])

            if os.path.getsize(v) > 500 * 1024 * 1024:
                await msg.edit("❌ Too big")
                continue

            out = "output.mp4"

            await encode(v, s, out, 0, msg, uid)

            await app.send_document(task["chat"], out)

            await msg.edit("✅ Done")

        except Exception as e:
            await msg.edit(f"❌ {e}")

        finally:
            for f in os.listdir(tempfile.gettempdir()):
                try:
                    os.remove(os.path.join(tempfile.gettempdir(), f))
                except:
                    pass

# ================= HEALTH =================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_server():
    HTTPServer(("0.0.0.0", PORT), HealthHandler).serve_forever()

# ================= MAIN =================

async def main():
    await app.start()
    print("Bot Started")
    asyncio.create_task(worker())
    await idle()

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.get_event_loop().run_until_complete(main())
