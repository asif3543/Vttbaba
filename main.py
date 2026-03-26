import os
import asyncio
import subprocess
from collections import deque
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from aiohttp import web

# ================= CONFIG =================

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEST_CHANNEL = int(os.getenv("DEST_CHANNEL")) # Ensure it's an integer

OWNER_ID = 6815990712
ALLOWED_GROUPS = [-1003810374456]

app = Client("EncoderBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ================= GLOBAL =================

users = {}
task_queue = deque()
in_queue = set()
queue_lock = asyncio.Lock()

# ================= WEB =================

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

# ================= AUTH =================

def is_authorized(message: Message):
    return message.chat.id in ALLOWED_GROUPS or message.from_user.id == OWNER_ID

# ================= START =================

@app.on_message(filters.command("start"))
async def start(_, message: Message):
    await message.reply("🔥 Bot Online!\nReply video with /hsub")

# ================= HSUB =================

@app.on_message(filters.command(["hsub"]))
async def hsub(_, message: Message):
    if not is_authorized(message):
        return await message.reply("❌ Not allowed")

    user_id = message.from_user.id
    if user_id in in_queue:
        return await message.reply("❌ Already in queue")

    replied = message.reply_to_message
    if not replied:
        return await message.reply("❌ Reply to video")

    media = replied.video or replied.document
    if not media:
        return await message.reply("❌ Invalid video")

    users[user_id] = {
        "video": media.file_id,
        "name": getattr(media, "file_name", "video.mp4")
    }
    await message.reply("📄 Send subtitle file (.srt/.ass/.vtt)")

# ================= SUBTITLE =================

@app.on_message(filters.document)
async def subtitle(_, message: Message):
    user_id = message.from_user.id
    if not is_authorized(message):
        return

    if not message.document.file_name.lower().endswith((".srt", ".ass", ".vtt")):
        return

    if user_id not in users:
        return await message.reply("❌ Use /hsub first")

    users[user_id]["sub"] = message.document.file_id
    await message.reply("✏️ Send name or /skip")

# ================= RENAME =================

@app.on_message(filters.text)
async def rename(_, message: Message):
    user_id = message.from_user.id
    if user_id not in users or "sub" not in users[user_id]:
        return

    name = message.text.strip()
    if name.lower() == "/skip":
        name = users[user_id]["name"]

    task_queue.append({
        "user": user_id,
        "video": users[user_id]["video"],
        "sub": users[user_id]["sub"],
        "name": name,
        "msg": message
    })

    in_queue.add(user_id)
    del users[user_id]
    await message.reply("✅ Added to queue")

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
    p = await asyncio.create_subprocess_exec(*cmd)
    await p.wait()
    # Check for parts specifically to avoid picking other files
    return sorted([f for f in os.listdir() if f.startswith("part_") and f.endswith(".mp4")])

async def encode(video, sub, out):
    # Added logs to see if FFmpeg is working
    cmd = [
        "ffmpeg", "-i", video,
        "-vf", f"subtitles={sub}",
        "-preset", "ultrafast",
        "-crf", "28",
        "-c:a", "copy",
        "-y", out
    ]
    p = await asyncio.create_subprocess_exec(*cmd)
    await p.wait()
    return os.path.exists(out)

async def process(task):
    msg = task["msg"]
    status = await msg.reply("⚙️ Processing...")

    try:
        v = await app.download_media(task["video"], "video.mp4")
        s = await app.download_media(task["sub"], "sub.srt")

        parts = await split_video(v)
        if not parts:
            return await status.edit("❌ Splitting failed")

        for i, part in enumerate(parts, 1):
            out = f"{task['name']}_{i}.mp4"
            ok = await encode(part, s, out)
            
            if not ok:
                await status.edit(f"❌ Encoding failed at Part {i}")
                break

            await app.send_video(DEST_CHANNEL, out, caption=f"{task['name']} Part {i}")
            os.remove(part)
            os.remove(out)

        # Cleanup original files
        if os.path.exists(v): os.remove(v)
        if os.path.exists(s): os.remove(s)
        
        await status.edit("✅ All parts uploaded successfully!")
    except Exception as e:
        await status.edit(f"❌ Error: {str(e)}")
    finally:
        if task["user"] in in_queue:
            in_queue.remove(task["user"])

# ================= WORKER =================

async def worker():
    print("Worker started...")
    while True:
        if not task_queue:
            await asyncio.sleep(5)
            continue

        async with queue_lock:
            task = task_queue.popleft()

        try:
            await process(task)
        except Exception as e:
            print(f"Worker Error: {e}")

# ================= MAIN =================

async def main():
    await app.start()
    await start_webserver()
    asyncio.create_task(worker())
    print("Bot is alive!")
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
