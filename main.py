import os
import time
import asyncio
import subprocess
import shutil
from pyrogram import Client, filters
from pyrogram.types import Message
from faster_whisper import WhisperModel
from flask import Flask
from threading import Thread

# ================= CONFIGURATION =================
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Jjis channel pe subtitles bhejne hain uski ID (e.g., -100123456789)
# Agar 0 rakhoge toh sirf usi chat me aayega jahan command di hai
DEST_CHANNEL = int(os.environ.get("DEST_CHANNEL", "0")) 

OWNER_ID = 5344078567
ALLOWED_USERS = [5351848105, OWNER_ID]
ALLOWED_GROUPS = [-1003899919015]

app = Client("SubGenBotLocal", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Tiny model for 512MB RAM
print("Loading AI Model (Tiny)...")
model = WhisperModel("tiny", device="cpu", compute_type="int8")

# ================= FLASK (Keep-Alive) =================
flask_app = Flask(__name__)
@flask_app.route('/')
def health(): return "Bot is Running! ✅"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# ================= UTILS =================
def is_authorized(message: Message) -> bool:
    u_id = message.from_user.id if message.from_user else 0
    return (u_id in ALLOWED_USERS or message.chat.id in ALLOWED_GROUPS)

def format_timestamp(seconds: float, mode: str = "srt") -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    if mode == "vtt":
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

# ================= CORE PROCESS =================
async def process_subtitles(client, message: Message, mode: str):
    if not is_authorized(message):
        return await message.reply("❌ Unauthorized!")

    replied = message.reply_to_message
    if not replied or not (replied.video or replied.document or replied.audio):
        return await message.reply(f"❌ Video/Audio par reply karke `/{mode}` likho!")

    status = await message.reply("⏳ Starting process...")
    
    video_path = None
    audio_path = f"audio_{message.id}.wav"
    sub_path = f"sub_{message.id}.{mode}"

    try:
        # 1. Download Video
        await status.edit("⬇️ Downloading video from Telegram...")
        video_path = await client.download_media(replied)
        
        # 2. Extract Audio (RAM optimize karne ke liye)
        await status.edit("🎵 Extracting audio stream...")
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            "-y", audio_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Video delete kar do turant RAM/Disk bachane ke liye
        if os.path.exists(video_path): os.remove(video_path)

        # 3. Transcribe AI
        await status.edit("🤖 AI generating subtitles... (Wait)")
        segments, info = model.transcribe(audio_path, beam_size=1)

        # 4. Save to File
        with open(sub_path, "w", encoding="utf-8") as f:
            if mode == "vtt": f.write("WEBVTT\n\n")
            for i, segment in enumerate(segments, start=1):
                start = format_timestamp(segment.start, mode)
                end = format_timestamp(segment.end, mode)
                f.write(f"{i}\n{start} --> {end}\n{segment.text.strip()}\n\n")

        # 5. Sending File (Current Chat + Destination Channel)
        caption = f"✅ **Subtitles Done!**\n🌍 Lang: {info.language.upper()}\n📄 Format: {mode.upper()}"
        
        # Agar Channel ID di hai toh wahan bhejo
        if DEST_CHANNEL != 0:
            await client.send_document(
                chat_id=DEST_CHANNEL,
                document=sub_path,
                caption=caption + f"\n🆔 Request by: {message.from_user.mention}"
            )
            await status.edit(f"✅ Subtitles sent to Destination Channel!")
        
        # User ko bhi file bhej do
        await client.send_document(
            chat_id=message.chat.id,
            document=sub_path,
            caption=caption,
            reply_to_message_id=replied.id
        )
        
        if DEST_CHANNEL == 0:
            await status.delete()

    except Exception as e:
        await status.edit(f"❌ Error: {str(e)}")
    finally:
        # Cleanup everything
        for f in [video_path, audio_path, sub_path]:
            if f and os.path.exists(f):
                try: os.remove(f)
                except: pass

# ================= HANDLERS =================
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("Bot Ready! Video par reply karke `/srt` ya `/vtt` likhein.")

@app.on_message(filters.command("srt") & filters.reply)
async def srt_handler(client, message):
    await process_subtitles(client, message, "srt")

@app.on_message(filters.command("vtt") & filters.reply)
async def vtt_handler(client, message):
    await process_subtitles(client, message, "vtt")

# ================= RUN =================
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    print("🚀 Bot is LIVE!")
    app.run()
