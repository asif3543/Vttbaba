import os
import time
import json
import asyncio
import subprocess
from collections import deque
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from aiohttp import web   # ✅ PORT FIX

# ================= CONFIG =================

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEST_CHANNEL = os.getenv("DEST_CHANNEL")

OWNER_ID = 6815990712
ALLOWED_USERS = [6815990712]
ALLOWED_GROUPS = [-1003810374456]

app = Client("EncoderBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ================= GLOBAL =================

users = {}
task_queue = deque()
current_user = None
queue_lock = asyncio.Lock()

# ================= WEB SERVER (PORT FIX) =================

async def handle(request):
    return web.Response(text="Bot Running")

async def start_webserver():
    app_web = web.Application()
    app_web.router.add_get("/", handle)
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# ================= UTILS =================

def is_authorized(message: Message):
    if not message.from_user:
        return False
    u_id = message.from_user.id
    if message.text and message.text.startswith("/start"):
        return True
    return u_id == OWNER_ID or u_id in ALLOWED_USERS or message.chat.id in ALLOWED_GROUPS

# ================= HANDLERS =================

@app.on_message(filters.command("start"))
async def start(_, message: Message):
    await message.reply("🔥 Bot Online!\n\nReply video with /hsub")

@app.on_message(filters.command("hsub"))
async def hsub(_, message: Message):
    if not is_authorized(message):
        return

    replied = message.reply_to_message
    if not replied or not (replied.video or replied.document):
        return await message.reply("❌ Reply to video")

    media = replied.video or replied.document
    users[message.from_user.id] = {"video": media.file_id}
    await message.reply("📄 Send subtitle (.srt/.ass/.vtt)")

@app.on_message(filters.document)
async def get_sub(_, message: Message):
    if not is_authorized(message):
        return

    user_id = message.from_user.id

    if not message.document.file_name.lower().endswith((".srt", ".ass", ".vtt")):
        return

    if user_id not in users:
        return await message.reply("❌ Send video first")

    task_queue.append({
        "user": user_id,
        "video": users[user_id]["video"],
        "sub": message.document.file_id,
        "msg": message
    })

    del users[user_id]
    await message.reply(f"✅ Added to queue: {len(task_queue)}")

# ================= CORE =================

async def split_video(input_path):
    cmd = [
        "ffmpeg", "-i", input_path,
        "-c", "copy",
        "-map", "0",
        "-segment_time", "600",
        "-f", "segment",
        "part_%03d.mp4"
    ]
    process = await asyncio.create_subprocess_exec(*cmd)
    await process.wait()

    parts = sorted([f for f in os.listdir() if f.startswith("part_")])
    return parts

async def encode_part(video, sub, output):
    cmd = [
        "ffmpeg", "-i", video,
        "-vf", f"subtitles={sub}",
        "-preset", "ultrafast",
        "-crf", "28",
        "-c:a", "copy",
        "-y", output
    ]
    process = await asyncio.create_subprocess_exec(*cmd)
    await process.wait()
    return os.path.exists(output)

async def process_task(task):
    msg = task["msg"]
    status = await msg.reply("⚙️ Downloading...")

    v_path = await app.download_media(task["video"], file_name="input.mp4")
    s_path = await app.download_media(task["sub"], file_name="sub.srt")

    try:
        await status.edit("✂️ Splitting video...")
        parts = await split_video(v_path)

        count = 1
        for part in parts:
            out = f"out_{count}.mp4"

            await status.edit(f"🔥 Encoding Part {count}/{len(parts)}")

            ok = await encode_part(part, s_path, out)
            if not ok:
                return await status.edit("❌ Encode failed")

            await status.edit(f"📤 Uploading Part {count}")

            await app.send_video(
                chat_id=DEST_CHANNEL,
                video=out,
                caption=f"✅ Part {count}"
            )

            os.remove(part)
            os.remove(out)
            count += 1

        await status.edit("✅ All parts uploaded!")

    except Exception as e:
        await status.edit(f"❌ Error: {e}")

    finally:
        for f in [v_path, s_path]:
            if f and os.path.exists(f):
                os.remove(f)

# ================= QUEUE =================

async def worker():
    global current_user
    while True:
        if not task_queue:
            await asyncio.sleep(3)
            continue

        async with queue_lock:
            task = task_queue.popleft()
            current_user = task["user"]

        try:
            await process_task(task)
        except:
            pass
        finally:
            current_user = None

# ================= MAIN =================

async def main():
    await app.start()
    await start_webserver()  # ✅ PORT FIX
    print("Bot Running...")
    asyncio.create_task(worker())
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
