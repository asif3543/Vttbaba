import os
import re
import time
import json
import asyncio
import subprocess
import threading
from collections import deque
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ChatType
from http.server import HTTPServer, BaseHTTPRequestHandler

# ================= CONFIGURATION =================

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEST_CHANNEL = int(os.getenv("DEST_CHANNEL", 0)) 
PORT = int(os.getenv("PORT", 10000))

OWNER_ID = 5344078567                    
ALLOWED_USERS = [5351848105]             
ALLOWED_GROUPS = [-1003899919015] 

app = Client("EncoderBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Global Variables
users = {}
task_queue = deque()
current_task = None
queue_lock = asyncio.Lock()
in_queue = set()
processing = False

# ================= UTILS =================

def is_authorized(message: Message) -> bool:
    if not message.from_user: return False
    u_id = message.from_user.id    
    if message.text and message.text.lower().startswith("/start"): return True    
    if u_id == OWNER_ID or u_id in ALLOWED_USERS or message.chat.id in ALLOWED_GROUPS:
        return True
    return False

def progress_bar(percent):
    filled = int((percent / 100) * 12)
    return "█" * filled + "░" * (12 - filled)

def get_duration(file):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file],
            capture_output=True, text=True, check=True
        )
        data = json.loads(result.stdout)
        duration = data.get("format", {}).get("duration")
        if not duration:
            for stream in data.get("streams", []):
                duration = stream.get("duration")
                if duration: break
        return float(duration) if duration else 0.0
    except: return 0.0

# ================= HANDLERS =================

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply_text("<b>🔥 Furina Encoder is Online!</b>\n\nReply to a video with /hsub to start.")

@app.on_message(filters.command("hsub"))
async def hsub_handler(client, message: Message):
    if not is_authorized(message): return
    replied = message.reply_to_message
    if not replied or not (replied.video or replied.document):
        return await message.reply("❌ Reply to a video file.")
    
    media = replied.video or replied.document
    users[message.from_user.id] = {
        "video": {"file_id": media.file_id, "file_name": getattr(media, 'file_name', "video.mp4")},
        "step": "WAIT_SUB"
    }
    await message.reply("📄 Now send the Subtitle file (.srt / .ass).")

@app.on_message(filters.video | filters.document)
async def file_handler(client, message: Message):
    if not is_authorized(message): return
    user_id = message.from_user.id
    
    # Check if waiting for subtitle
    if user_id in users and users[user_id].get("step") == "WAIT_SUB":
        if message.document and message.document.file_name.lower().endswith((".srt", ".ass", ".vtt")):
            users[user_id]["subtitle"] = {"file_id": message.document.file_id, "file_name": message.document.file_name}
            users[user_id]["step"] = "WAIT_RENAME_CHOICE"
            
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Rename", callback_data="rename_yes"),
                 InlineKeyboardButton("⏭️ Skip", callback_data="rename_skip")]
            ])
            await message.reply("Do you want to rename the output file?", reply_markup=buttons)
        else:
            await message.reply("❌ Please send a valid subtitle file (.srt or .ass)")
        return

    # Check if waiting for rename text
    if user_id in users and users[user_id].get("step") == "WAIT_RENAME_TEXT":
        new_name = message.text
        if not new_name.lower().endswith((".mp4", ".mkv")):
            new_name += ".mp4"
        
        users[user_id]["video"]["file_name"] = new_name
        await add_to_queue(user_id, message)
        return

    # Default: Treat as new video
    media = message.video or message.document
    if media:
        users[user_id] = {
            "video": {"file_id": media.file_id, "file_name": getattr(media, 'file_name', "video.mp4")},
            "step": "WAIT_SUB"
        }
        await message.reply("📄 Now send the Subtitle file.")

@app.on_callback_query()
async def callback_handler(client, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id not in users:
        return await query.answer("Session expired. Send video again.", show_alert=True)

    if query.data == "rename_yes":
        users[user_id]["step"] = "WAIT_RENAME_TEXT"
        await query.message.edit("Please send the new name for the video (Example: `Jujutsu_Kaisen_S01E01.mp4`)")
    
    elif query.data == "rename_skip":
        await query.message.edit("Processing with original name...")
        await add_to_queue(user_id, query.message)

async def add_to_queue(user_id, message):
    data = users.pop(user_id)
    task_queue.append({
        'user_id': user_id, 
        'video_info': data["video"], 
        'subtitle_info': data["subtitle"]
    })
    in_queue.add(user_id)
    await message.reply_text(f"✅ Added to Queue. Position: {len(task_queue)}")

# ================= CORE LOGIC =================

async def encode_video(video_path, sub_path, output_path, duration, msg):
    # Escaping for FFmpeg subtitle filter
    sub_path_es = sub_path.replace("'", "'\\''").replace(":", "\\:")
    
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"subtitles='{sub_path_es}'",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-c:a", "copy", "-movflags", "+faststart",
        "-progress", "pipe:1", "-nostats", "-y", output_path
    ]
    
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    last_update = time.time()

    while True:
        line = await process.stdout.readline()
        if not line: break
        line = line.decode(errors="ignore").strip()
        if "out_time_ms=" in line:
            try:
                val = line.split("=")[1]
                if val.isdigit() and duration > 0:
                    current_time = int(val) / 1000000
                    percent = min(int((current_time / duration) * 100), 100)
                    if time.time() - last_update >= 10:
                        bar = progress_bar(percent)
                        await msg.edit(f"<b>🔥 Hardsubbing:</b> {percent}%\n{bar}")
                        last_update = time.time()
            except: continue
    
    await process.wait()
    return os.path.exists(output_path) and os.path.getsize(output_path) > 0

async def process_task(task):
    user_id = task['user_id']
    v_info = task['video_info']
    s_info = task['subtitle_info']
    
    status = await app.send_message(user_id, "⚙️ Starting download...")
    channel_msg = None
    v_path = s_path = output = None

    try:
        # Download
        v_path = await app.download_media(v_info["file_id"])
        s_path = await app.download_media(s_info["file_id"])
        output = f"Encoded_{v_info['file_name']}"
        duration = get_duration(v_path)

        # Notification in Channel
        if DEST_CHANNEL != 0:
            channel_msg = await app.send_message(DEST_CHANNEL, f"<b>🔄 Starting Encoding:</b>\n<code>{v_info['file_name']}</code>")

        await status.edit("🔥 <b>Encoding started...</b>")
        
        # Encoding
        success = await encode_video(v_path, s_path, output, duration, status)
        
        if success:
            await status.edit("📤 <b>Uploading...</b>")
            await app.send_video(
                chat_id=DEST_CHANNEL,
                video=output,
                caption=f"<b>✅ Hardsub Complete</b>\n<code>{v_info['file_name']}</code>",
                supports_streaming=True
            )
            await status.edit("✅ <b>Success! Sent to channel.</b>")
            
            # Delete channel "Starting" message
            if channel_msg:
                try: await channel_msg.delete()
                except: pass
        else:
            await status.edit("❌ Encoding Failed. Check subtitle format.")
            if channel_msg: await channel_msg.edit("❌ Encoding Failed.")

    except Exception as e:
        await status.edit(f"❌ Error: {str(e)}")
    finally:
        for f in [v_path, s_path, output]:
            if f and os.path.exists(f): os.remove(f)

async def queue_worker():
    global processing
    while True:
        if not task_queue:
            await asyncio.sleep(5)
            continue
        
        processing = True
        task = task_queue.popleft()
        in_queue.remove(task['user_id'])
        await process_task(task)
        processing = False

# ================= SERVER =================

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()

# ================= MAIN =================

async def main():
    await app.start()
    print("Bot Started!")
    asyncio.create_task(queue_worker())
    await idle()

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.get_event_loop().run_until_complete(main())
