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
print("⏳ Loading AI Model (tiny)...")
# compute_type int8_float16 bhi try kar sakte ho, lekin int8 safe hai
model = WhisperModel("tiny", device="cpu", compute_type="int8")
print("✅ AI Model Loaded Successfully!")

# ================= FLASK HEALTH CHECK =================
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Bot is Running Live! ✅"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port, debug=False)

# ================= UTILS =================
def is_authorized(message: Message) -> bool:
    if not message.from_user:
        return False
    u_id = message.from_user.id
    return (u_id == OWNER_ID or 
            u_id in ALLOWED_USERS or 
            message.chat.id in ALLOWED_GROUPS)

def format_time(seconds: float, mode: str = "srt") -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    
    if mode == "vtt":
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

# ================= CORE TRANSCRIPTION (Fixed) =================
async def process_transcription(client, message: Message, mode: str, copy_mode: bool = False):
    if not is_authorized(message):
        return await message.reply("❌ Authorized nahi ho bhai!")

    replied = message.reply_to_message
    if not replied or not (replied.video or replied.audio or 
        (replied.document and replied.document.mime_type and 
         ("video" in replied.document.mime_type or "audio" in replied.document.mime_type))):
        return await message.reply(f"❌ Video ya Audio file par reply karke `/{mode}` likho!")

    status = await message.reply(f"⏳ Processing {mode.upper()}... (Tiny model slow hai, thoda wait karo)")

    start_time = time.time()
    v_path = None
    audio_path = None
    sub_path = None

    try:
        # Download media
        status = await status.edit("⬇️ Downloading file...")
        v_path = await client.download_media(replied)

        # Extract audio (better quality + error handling)
        status = await status.edit("🎵 Extracting audio...")
        audio_path = f"audio_{replied.id}_{int(time.time())}.wav"   # .wav better for whisper

        cmd = [
            "ffmpeg", "-i", v_path,
            "-vn", "-acodec", "pcm_s16le",   # better than mp3 for transcription
            "-ar", "16000", "-ac", "1",
            "-y", audio_path
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            return await status.edit(f"❌ Audio extraction failed:\n{stderr.decode()[:500]}")

        if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
            return await status.edit("❌ Audio file not created or too small")

        # Transcribe with better parameters
        status = await status.edit("🤖 Generating subtitles with AI...\n(Tiny model use ho raha hai, accuracy kam ho sakti hai)")

        segments, info = model.transcribe(
            audio_path,
            beam_size=5,
            word_timestamps=False,
            language=None,          # auto detect
            vad_filter=True,        # better silence removal
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        # Force list conversion (important fix!)
        segments = list(segments)   # <--- yeh line missing thi bahut cases mein

        if not segments:
            return await status.edit("❌ No speech detected in audio. Koi clear audio nahi mila.")

        # Generate subtitle file
        sub_path = f"Sub_{replied.id}.{mode}"
        with open(sub_path, "w", encoding="utf-8") as f:
            if mode == "vtt":
                f.write("WEBVTT\n\n")

            for i, segment in enumerate(segments, start=1):
                start = format_time(segment.start, mode)
                end = format_time(segment.end, mode)
                text = segment.text.strip()
                if text:  # empty lines avoid karo
                    f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

        time_taken = f"{int(time.time() - start_time)}s"

        caption = (
            f"✅ Subtitles Generated Successfully!\n"
            f"🌐 Language: {info.language.upper()} (prob: {info.language_probability:.2f})\n"
            f"⏱️ Time: {time_taken}\n"
            f"📄 Format: {mode.upper()}\n"
            f"🔢 Segments: {len(segments)}"
        )

        if copy_mode:
            await status.edit("📤 Sending video + subtitles...")
            await client.send_document(message.chat.id, sub_path, caption=caption, reply_to_message_id=replied.id)
            await client.send_video(
                message.chat.id, v_path,
                caption="🎥 Original Video (subtitles ke saath use kar sakte ho)",
                supports_streaming=True,
                reply_to_message_id=replied.id
            )
        else:
            if DEST_CHANNEL and DEST_CHANNEL != 0:
                await client.send_document(DEST_CHANNEL, sub_path, caption=caption)
            else:
                await client.send_document(
                    message.chat.id, 
                    sub_path, 
                    caption=caption,
                    reply_to_message_id=replied.id
                )

        await status.edit("✅ Done! Subtitles aa gaye.")

    except Exception as e:
        await status.edit(f"❌ Error: {str(e)[:400]}")
        print(f"Error: {e}")

    finally:
        # Cleanup
        for file in [v_path, audio_path, sub_path]:
            if file and os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    pass

# ================= HANDLERS =================
@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply(
        "🔥 **Subtitle Generator Bot** Online!\n\n"
        "Commands:\n"
        "`/srt`  → .srt subtitles\n"
        "`/vtt`  → .vtt subtitles\n"
        "`/copy` → Video + subtitles dono bhejo\n\n"
        "Kisi bhi video/audio par reply karke command use karo.\n"
        "Note: Tiny model hai → accuracy kam ho sakti hai Hindi mein."
    )

@app.on_message(filters.command("srt") & filters.reply)
async def srt_handler(client, message: Message):
    await process_transcription(client, message, "srt")

@app.on_message(filters.command("vtt") & filters.reply)
async def vtt_handler(client, message: Message):
    await process_transcription(client, message, "vtt")

@app.on_message(filters.command("copy") & filters.reply)
async def copy_handler(client, message: Message):
    await process_transcription(client, message, "srt", copy_mode=True)

# ================= UTILITY COMMANDS =================
@app.on_message(filters.command("delete"))
async def delete_junk(client, message: Message):
    if not is_authorized(message): 
        return
    count = 0
    for file in os.listdir("./"):
        if file.endswith((".srt", ".vtt", ".wav", ".mp3", ".mp4", ".mkv", ".temp")):
            try:
                os.remove(file)
                count += 1
            except:
                pass
    await message.reply(f"🧹 {count} temporary files deleted.")

@app.on_message(filters.command("stats"))
async def get_stats(client, message: Message):
    if not is_authorized(message): 
        return
    total, used, free = shutil.disk_usage("/")
    await message.reply(
        f"💾 **Disk Usage**\n"
        f"Used: {used//(1024*1024)} MB\n"
        f"Free: {free//(1024*1024)} MB"
    )

# ================= RUN BOT =================
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    print("🚀 Bot is Starting...")
    app.run()
