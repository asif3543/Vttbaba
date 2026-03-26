import os
import time
import json
import asyncio
import subprocess
import threading
from collections import deque
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
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
users_data = {}
task_queue = deque()
current_task = None
in_queue = set()
processing_lock = asyncio.Lock()

# ================= UTILS =================

def is_authorized(message: Message) -> bool:
    if not message.from_user: return False
    u_id = message.from_user.id    
    if message.text and message.text.lower().startswith("/start"): return True    
    if u_id == OWNER_ID or u_id in ALLOWED_USERS or message.chat.id in ALLOWED_GROUPS:
        return True
    return False

def get_duration(file):
    try:
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    except: return 0

# ================= HANDLERS =================

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply("<b>🔥 Furina Encoder is Online!</b>\n\nReply to video with /hsub")

@app.on_message(filters.command("delete"))
async def delete_all(client, message: Message):
    if not is_authorized(message): return
    global task_queue, in_queue, users_data
    task_queue.clear()
    in_queue.clear()
    users_data.clear()
    await message.reply("🗑️ All data cleared.")

@app.on_message(filters.command("hsub"))
async def hsub_cmd(client, message: Message):
    if not is_authorized(message): return
    replied = message.reply_to_message
    if not replied or not (replied.video or replied.document):
        return await message.reply("❌ Reply to a video file with /hsub")
    
    media = replied.video or replied.document
    users_data[message.from_user.id] = {
        "video": {"file_id": media.file_id, "file_name": getattr(media, 'file_name', "video.mp4")},
        "state": "WAIT_SUB"
    }
    await message.reply("📄 Now send the Subtitle file (.srt / .ass)")

@app.on_message(filters.document | filters.video | filters.text)
async def handle_all_inputs(client, message: Message):
    if not is_authorized(message): return
    user_id = message.from_user.id
    
    if user_id not in users_data: return

    state = users_data[user_id].get("state")

    # Step 1: Receiving Subtitle
    if state == "WAIT_SUB" and message.document:
        if message.document.file_name.lower().endswith((".srt", ".ass")):
            users_data[user_id]["subtitle"] = {"file_id": message.document.file_id, "file_name": message.document.file_name}
            users_data[user_id]["state"] = "WAIT_RENAME_CHOICE"
            
            btn = InlineKeyboardMarkup([[
                InlineKeyboardButton("📝 Rename", callback_data="rn_yes"),
                InlineKeyboardButton("⏭️ Skip", callback_data="rn_skip")
            ]])
            await message.reply("Do you want to rename the output file?", reply_markup=btn)
        return

    # Step 2: Receiving Rename Text
    if state == "WAIT_RENAME_TEXT" and message.text:
        new_name = message.text.strip()
        if not new_name.lower().endswith((".mp4", ".mkv")):
            new_name += ".mp4"
        users_data[user_id]["video"]["file_name"] = new_name
        await add_to_queue(user_id, message)
        return

@app.on_callback_query(filters.regex("^rn_"))
async def callback_rename(client, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id not in users_data: return await query.answer("Session Expired", show_alert=True)

    if query.data == "rn_yes":
        users_data[user_id]["state"] = "WAIT_RENAME_TEXT"
        await query.message.edit("📝 Send new name for the video:")
    else:
        await query.message.edit("🚀 Processing with original name...")
        await add_to_queue(user_id, query.message)

async def add_to_queue(user_id, message):
    data = users_data.pop(user_id)
    task_queue.append({
        "user_id": user_id,
        "video": data["video"],
        "subtitle": data["subtitle"]
    })
    in_queue.add(user_id)
    await message.reply(f"✅ Added to Queue. Position: {len(task_queue)}")

# ================= CORE ENCODER =================

async def encode_process(video, subtitle, output, duration, status_msg):
    # Escape path for FFmpeg
    sub_path = subtitle.replace("'", "'\\''").replace(":", "\\:")
    
    # Render-friendly settings (Ultrafast preset to save CPU)
    cmd = [
        "ffmpeg", "-i", video,
        "-vf", f"subtitles='{sub_path}'",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26", 
        "-c:a", "copy", "-y", output
    ]
    
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    
    # Progress monitoring
    start_time = time.time()
    while True:
        line = await process.stdout.readline()
        if not line: break
        # Progress updates can be added here if needed, but keeping it light for Render
        await asyncio.sleep(1)

    await process.wait()
    return os.path.exists(output)

async def worker():
    while True:
        if not task_queue:
            await asyncio.sleep(5)
            continue
        
        task = task_queue.popleft()
        uid = task["user_id"]
        v_info = task["video"]
        s_info = task["subtitle"]
        
        status = await app.send_message(uid, "⏳ Starting Process...")
        channel_log = None
        v_path = s_path = out_path = None
        
        try:
            # Notify Channel
            if DEST_CHANNEL:
                channel_log = await app.send_message(DEST_CHANNEL, f"<b>🔄 Starting:</b> <code>{v_info['file_name']}</code>")

            # Download
            await status.edit("📥 Downloading files...")
            v_path = await app.download_media(v_info["file_id"])
            s_path = await app.download_media(s_info["file_id"])
            out_path = v_info["file_name"]
            
            dur = get_duration(v_path)
            
            # Encode
            await status.edit("🔥 Encoding started (Ultrafast Mode)...")
            success = await encode_process(v_path, s_path, out_path, dur, status)
            
            if success:
                await status.edit("📤 Uploading to channel...")
                await app.send_video(
                    chat_id=DEST_CHANNEL if DEST_CHANNEL else uid,
                    video=out_path,
                    caption=f"<b>✅ Hardsub Complete</b>\n<code>{out_path}</code>",
                    supports_streaming=True
                )
                await status.edit("✅ Successfully Completed!")
                if channel_log: await channel_log.delete()
            else:
                await status.edit("❌ Encoding Failed.")
                
        except Exception as e:
            await app.send_message(uid, f"❌ Error: {str(e)}")
        finally:
            in_queue.discard(uid)
            # Cleanup
            for f in [v_path, s_path, out_path]:
                if f and os.path.exists(f): os.remove(f)

# ================= RENDER KEEP ALIVE =================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running")

def run_health_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()

# ================= MAIN =================

async def main():
    await app.start()
    print("Bot is started!")
    asyncio.create_task(worker())
    await idle()

if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
