import os
import time
import shutil
import asyncio
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from faster_whisper import WhisperModel
from flask import Flask
from threading import Thread

# ================= CONFIGURATION =================

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DEST_CHANNEL = int(os.environ.get("DEST_CHANNEL", 0))

OWNER_ID = 5344078567                    
ALLOWED_USERS = [5351848105]             
ALLOWED_GROUPS = [-1003899919015]        

app = Client("SubGenBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ================= MODEL =================

print("⏳ Loading AI Model (Tiny)... Please wait.")
model = WhisperModel("tiny", device="cpu", compute_type="int8")
print("✅ AI Model Loaded Successfully!")

# ================= PORT =================

flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Bot is Running Live!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# ================= UTILS =================

def is_authorized(message: Message) -> bool:
    if not message.from_user:
        return False
    u_id = message.from_user.id    
    return u_id == OWNER_ID or u_id in ALLOWED_USERS or message.chat.id in ALLOWED_GROUPS

def format_time(seconds, mode="srt"):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    if mode == "vtt":
        return f"{h:02}:{m:02}:{s:02}.{ms:03}"
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

# ================= CORE =================

async def process_transcription(client, message, mode):
    if not is_authorized(message): 
        return await message.reply("❌ Authorized nahi ho")

    replied = message.reply_to_message

    # ✅ FIX: All formats + safe mime check
    if not replied or not (
        replied.video or 
        (replied.document and replied.document.mime_type and 
         ("video" in replied.document.mime_type or "audio" in replied.document.mime_type))
    ):
        return await message.reply(f"❌ Video ya Audio file par reply karke `/{mode}` likho!")

    status = await message.reply(f"⏳ Processing {mode.upper()}...")

    start_time = time.time()
    v_path = None
    audio_path = None
    output_file = None

    try:
        # ✅ ANY format download (no forced .mp4)
        v_path = await client.download_media(replied)

        # 🔥 IMPORTANT: audio extract (CRASH FIX)
        audio_path = f"audio_{replied.id}.mp3"

        cmd = [
            "ffmpeg",
            "-i", v_path,
            "-vn",
            "-acodec", "mp3",
            "-y",
            audio_path
        ]

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if not os.path.exists(audio_path):
            return await status.edit("❌ Audio extract failed")

        # ✅ Whisper on AUDIO (lightweight)
        segments, info = model.transcribe(audio_path, beam_size=5)

        output_file = f"Sub_{replied.id}.{mode}"

        with open(output_file, "w", encoding="utf-8") as f:
            if mode == "vtt":
                f.write("WEBVTT\n\n")

            for i, segment in enumerate(segments, start=1):
                start = format_time(segment.start, mode)
                end = format_time(segment.end, mode)
                f.write(f"{i}\n{start} --> {end}\n{segment.text.strip()}\n\n")

        time_taken = f"{int(time.time() - start_time)}s"

        caption = (
            f"✅ Subtitles Generated\n"
            f"🌐 {info.language.upper()}\n"
            f"⏱️ {time_taken}"
        )

        if DEST_CHANNEL == 0:
            await message.reply_document(output_file, caption=caption)
        else:
            await client.send_document(DEST_CHANNEL, output_file, caption=caption)

        await status.edit("✅ Kaam ho gaya!")

    except Exception as e:
        await status.edit(f"❌ Error: {str(e)}")

    finally:
        for f in [v_path, audio_path, output_file]:
            if f and os.path.exists(f):
                os.remove(f)

# ================= HANDLERS =================

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply("🔥 Subtitle Generator Online!\n/srt | /vtt")

@app.on_message(filters.command("srt") & filters.reply)
async def srt_handler(client, message: Message):
    await process_transcription(client, message, "srt")

@app.on_message(filters.command("vtt") & filters.reply)
async def vtt_handler(client, message: Message):
    await process_transcription(client, message, "vtt")

@app.on_message(filters.command("delete"))
async def delete_junk(client, message: Message):
    if not is_authorized(message): return
    count = 0
    for file in os.listdir("./"):
        if file.endswith((".srt", ".vtt", ".mp3", ".mp4", ".mkv", ".temp")):
            try:
                os.remove(file)
                count += 1
            except:
                pass
    await message.reply(f"🧹 {count} files delete ho gaye")

@app.on_message(filters.command("clearall"))
async def clear_all_junk(client, message: Message):
    if not is_authorized(message): return
    count = 0
    for file in os.listdir("./"):
        if file.endswith((".srt", ".vtt", ".mp3", ".mp4", ".mkv", ".temp")):
            try:
                os.remove(file)
                count += 1
            except:
                pass 
    await message.reply(f"🗑️ {count} files cleared!")

@app.on_message(filters.command("stats"))
async def get_stats(client, message: Message):
    if not is_authorized(message): return
    total, used, free = shutil.disk_usage("/")
    await message.reply(f"💾 Used: {used//(2**20)}MB\nFree: {free//(2**20)}MB")

# ================= RUN =================

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    print("Bot is Starting...")
    app.run()
