import os
import time
import shutil
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from faster_whisper import WhisperModel
from flask import Flask
from threading import Thread

# ================= CONFIGURATION =================

# IMPORTANT: Ensure these ENV variables are set before running the script
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# Default Destination Channel agar set na ho
DEST_CHANNEL = int(os.environ.get("DEST_CHANNEL", "-10023456789")) 

OWNER_ID = 5344078567                    
ALLOWED_USERS = [5351848105]             
ALLOWED_GROUPS = [-1003899919015]        

# --- ENV CHECK ---
if not all([API_ID, API_HASH, BOT_TOKEN]):
    print("❌ ERROR: API_ID, API_HASH, or BOT_TOKEN environment variables are not set.")
    exit(1)

API_ID = int(API_ID) # Convert to int after checking existence

app = Client("SubGenBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ✅ PRE-LOADING MODEL: Isse transcription ke waqt delay nahi hoga
print("⏳ Loading AI Model (Tiny) on CPU... Please wait.")
# CPU performance ke liye int8 rakha hai. Yeh hi dheema chalega.
model = WhisperModel("tiny", device="cpu", compute_type="int8")
print("✅ AI Model Loaded Successfully!")

# ================= PORT BINDING (For Uptime Monitoring) =================

flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Bot is Running Live!"

def run_flask():
    # Ensure the port is available, default to 10000 if not set
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Flask Health Check Running on port {port}")
    # use threaded=True for better concurrency with Pyrogram's async loop management
    flask_app.run(host='0.0.0.0', port=port, threaded=True)

# ================= UTILS =================

def is_authorized(message: Message) -> bool:
    if not message.from_user: return False
    u_id = message.from_user.id    
    if u_id == OWNER_ID or u_id in ALLOWED_USERS or message.chat.id in ALLOWED_GROUPS:
        return True
    return False

def format_time(seconds, mode="srt"):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milis = int((seconds - int(seconds)) * 1000)
    if mode == "vtt":
        # VTT format needs milliseconds separated by a dot (.)
        return f"{hours:02}:{minutes:02}:{secs:02}.{milis:03}"
    # SRT format needs milliseconds separated by a comma (,)
    return f"{hours:02}:{minutes:02}:{secs:02},{milis:03}"

# ================= CORE LOGIC =================

async def process_transcription(client, message, mode):
    if not is_authorized(message): 
        return await message.reply("❌ Beta, tum authorized nahi ho!")
    
    replied = message.reply_to_message
    # Check if replied message exists and has a video/document (assuming audio is attached as document)
    if not replied or not (replied.video or (replied.document and 'audio' in replied.mime_type)):
        return await message.reply(f"❌ Video file par reply karke `/{mode}` likho! (Ya audio file attach ki ho)")

    status = await message.reply(f"⏳ **Processing {mode.upper()}...**\nTranscribing audio on CPU, lambi audio files mein zyada time lagega. Sabar rakhein.")
    
    start_time = time.time()
    v_path = None
    output_file = None
    
    try:
        # Download in root directory
        temp_name = f"video_{replied.id}.mp4" # Use a generic extension for download
        v_path = await client.download_media(replied, file_name=f"./{temp_name}")
        
        # Transcription (SLOWEST PART on CPU)
        # If you only have audio, faster-whisper extracts it automatically.
        segments, info = model.transcribe(v_path, beam_size=5)
        
        output_file = f"Sub_{replied.id}.{mode}"
        
        with open(output_file, "w", encoding="utf-8") as f:
            if mode == "vtt": f.write("WEBVTT\n\n")
            for i, segment in enumerate(segments, start=1):
                start = format_time(segment.start, mode)
                end = format_time(segment.end, mode)
                # Ensure text strip and proper formatting
                f.write(f"{i}\n{start} --> {end}\n{segment.text.strip()}\n\n")

        time_taken = f"{int(time.time() - start_time)}s"
        caption = (f"✅ **Subtitles Generated**\n\n"
                   f"🌐 **Language:** {info.language.upper()}\n"
                   f"⏱️ **Time Taken:** {time_taken}\n\n"
                   f"**Note:** Transcription was done on CPU, which is slow.")
        
        await client.send_document(chat_id=DEST_CHANNEL, document=output_file, caption=caption)
        await status.edit(f"✅ Kaam ho gaya! File channel (`{DEST_CHANNEL}`) pe bhej di hai. Total time: {time_taken}")

    except Exception as e:
        print(f"Transcription Error: {e}")
        await status.edit(f"❌ **Error:** Transcription mein problem aayi: {str(e)}")
    
    finally:
        # Cleanup downloaded file and generated subtitle file
        if v_path and os.path.exists(v_path): os.remove(v_path)
        if output_file and os.path.exists(output_file): os.remove(output_file)
        print(f"Cleanup complete for files related to message ID {replied.id if replied else 'N/A'}.")


# ================= HANDLERS =================

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply("🔥 **Subtitle Generator Online!**\n\nReply to a Video/Audio and use:\n`/srt` or ` /vtt`")

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
        # Added more extensions and kept your cleaning logic
        if file.endswith((".srt", ".vtt", ".mp4", ".mkv", ".temp")):
            try:
                os.remove(file)
                count += 1
            except Exception as e:
                print(f"Could not delete {file}: {e}")
    await message.reply(f"🧹 {count} junk files delete kar di hain!")

@app.on_message(filters.command("stats"))
async def get_stats(client, message: Message):
    if not is_authorized(message): return
    try:
        total, used, free = shutil.disk_usage("/")
        await message.reply(f"💾 **Disk Stats:**\nUsed: {used // (2**30)} GB | Free: {free // (2**30)} GB")
    except Exception as e:
        await message.reply(f"❌ Disk stats fetch failed: {e}")

if __name__ == "__main__":
    # Start Flask in a separate thread so Pyrogram can run its main loop
    Thread(target=run_flask, daemon=True).start()
    print("Bot is Starting...")
    # Pyrogram's run() handles the main asyncio loop
    app.run()
