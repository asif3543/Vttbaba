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
# Ye variables aap Render ke "Environment Variables" me bhi daal sakte hain
API_ID = int(os.environ.get("API_ID", "0")) # Apna API ID yahan likhein ya Render me set karein
API_HASH = os.environ.get("API_HASH", "")   # Apna API HASH yahan likhein
BOT_TOKEN = os.environ.get("BOT_TOKEN", "") # Apna BOT TOKEN yahan likhein

OWNER_ID = 5344078567
ALLOWED_USERS = [5351848105, OWNER_ID]
ALLOWED_GROUPS = [-1003899919015]

app = Client("SubGenBotLocal", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Tiny model RAM bachane ke liye (int8 quantization)
# Ye 512MB RAM me aaram se chal jayega
print("Loading AI Model (Tiny)... Please wait.")
model = WhisperModel("tiny", device="cpu", compute_type="int8")

# ================= FLASK HEALTH CHECK =================
# Render ko active rakhne ke liye
flask_app = Flask(__name__)
@flask_app.route('/')
def health(): return "Bot is Running Live! ✅"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# ================= UTILS =================
def is_authorized(message: Message) -> bool:
    if not message.from_user:
        return False
    u_id = message.from_user.id
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
        return await message.reply("❌ Aap authorized nahi hain!")

    replied = message.reply_to_message
    if not replied or not (replied.video or replied.document or replied.audio):
        return await message.reply(f"❌ Kisi Video/Audio file par reply karke `/{mode}` likho!")

    status = await message.reply("⏳ Processing... (Video se audio nikala ja raha hai)")
    
    video_path = None
    audio_path = f"audio_{message.id}.wav"
    sub_path = f"sub_{message.id}.{mode}"

    try:
        # 1. Download Video (Telegram Storage se Bot storage me)
        await status.edit("⬇️ Downloading file...")
        video_path = await client.download_media(replied)
        
        # 2. Extract Audio using FFmpeg (RAM save karne ke liye)
        await status.edit("🎵 Audio extract ho raha hai...")
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            "-y", audio_path
        ]
        # subprocess.run audio extract karegi
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Turant video delete karo taaki disk aur RAM free ho jaye
        if video_path and os.path.exists(video_path):
            os.remove(video_path)

        # 3. Transcribe using Local Whisper AI
        await status.edit("🤖 AI Subtitles generate kar raha hai (Local)...")
        # beam_size=1 process ko fast banata hai low RAM par
        segments, info = model.transcribe(audio_path, beam_size=1)

        # 4. Save to Subtitle File
        with open(sub_path, "w", encoding="utf-8") as f:
            if mode == "vtt":
                f.write("WEBVTT\n\n")
            
            for i, segment in enumerate(segments, start=1):
                start = format_timestamp(segment.start, mode)
                end = format_timestamp(segment.end, mode)
                text = segment.text.strip()
                if text:
                    f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

        # 5. Send back to User
        await status.edit("📤 Uploading subtitles...")
        caption = (
            f"✅ **Subtitles Generated!**\n\n"
            f"🌐 **Language:** {info.language.upper()}\n"
            f"📄 **Format:** {mode.upper()}\n"
            f"🔢 **Confidence:** {int(info.language_probability * 100)}%"
        )
        await client.send_document(
            message.chat.id, 
            sub_path, 
            caption=caption, 
            reply_to_message_id=replied.id
        )
        await status.delete()

    except Exception as e:
        await status.edit(f"❌ Error: {str(e)}")
        print(f"Error detail: {e}")
    finally:
        # Final Cleanup
        for f in [video_path, audio_path, sub_path]:
            if f and os.path.exists(f):
                try: os.remove(f)
                except: pass

# ================= HANDLERS =================
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply(
        "🔥 **Subtitle Generator Bot**\n\n"
        "Commands:\n"
        "`/srt` - Reply to video for SRT file\n"
        "`/vtt` - Reply to video for VTT file\n\n"
        "Powered by Local Whisper AI (No API Required)"
    )

@app.on_message(filters.command("srt") & filters.reply)
async def srt_handler(client, message):
    await process_subtitles(client, message, "srt")

@app.on_message(filters.command("vtt") & filters.reply)
async def vtt_handler(client, message):
    await process_subtitles(client, message, "vtt")

@app.on_message(filters.command("clean"))
async def clean_storage(client, message):
    if message.from_user.id != OWNER_ID: return
    count = 0
    for file in os.listdir("."):
        if file.endswith((".wav", ".srt", ".vtt", ".mp4", ".mkv")):
            os.remove(file)
            count += 1
    await message.reply(f"🧹 Cleaned {count} temporary files.")

# ================= RUN BOT =================
if __name__ == "__main__":
    # Flask ko thread me start karein
    Thread(target=run_flask, daemon=True).start()
    print("🚀 Bot Started Successfully!")
    app.run()
