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


API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEST_CHANNEL = int(os.getenv("DEST_CHANNEL", 0))

OWNER_ID = 5344078567                    
ALLOWED_USERS = [5351848105]             
ALLOWED_GROUPS = [-1003899919015]        

app = Client("SubGenBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ✅ PRE-LOADING MODEL: Isse transcription ke waqt delay nahi hoga
print("⏳ Loading AI Model (Tiny)... Please wait.")
model = WhisperModel("tiny", device="cpu", compute_type="int8")
print("✅ AI Model Loaded Successfully!")

# ================= PORT BINDING =================

flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Bot is Running Live!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

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
        return f"{hours:02}:{minutes:02}:{secs:02}.{milis:03}"
    return f"{hours:02}:{minutes:02}:{secs:02},{milis:03}"

# ================= CORE LOGIC =================

async def process_transcription(client, message, mode):
    if not is_authorized(message): 
        return await message.reply("❌ Beta, tum authorized nahi ho!")
    
    replied = message.reply_to_message
    # FIX: MIME type access corrected to replied.document.mime_type
    if not replied or not (replied.video or (replied.document and 'audio' in replied.document.mime_type)):
        return await message.reply(f"❌ Video ya Audio file par reply karke `/{mode}` likho!")

    status = await message.reply(f"⏳ **Processing {mode.upper()}...**\nTranscribing audio, thoda sabar rakho.")
    
    start_time = time.time()
    v_path = None
    output_file = None
    
    try:
        # Download in root
        temp_name = f"video_{replied.id}.mp4"
        v_path = await client.download_media(replied, file_name=f"./{temp_name}")
        
        # Transcription (Using pre-loaded model)
        segments, info = model.transcribe(v_path, beam_size=5)
        output_file = f"Sub_{replied.id}.{mode}"
        
        with open(output_file, "w", encoding="utf-8") as f:
            if mode == "vtt": f.write("WEBVTT\n\n")
            for i, segment in enumerate(segments, start=1):
                start = format_time(segment.start, mode)
                end = format_time(segment.end, mode)
                f.write(f"{i}\n{start} --> {end}\n{segment.text.strip()}\n\n")

        time_taken = f"{int(time.time() - start_time)}s"
        caption = (f"✅ **Subtitles Generated**\n\n"
                   f"🌐 **Language:** {info.language.upper()}\n"
                   f"⏱️ **Time:** {time_taken}")
        
        await client.send_document(chat_id=DEST_CHANNEL, document=output_file, caption=caption)
        await status.edit(f"✅ Kaam ho gaya! File channel pe bhej di hai.")

    except Exception as e:
        await status.edit(f"❌ **Error:** {str(e)}")
    
    finally:
        if v_path and os.path.exists(v_path): os.remove(v_path)
        if output_file and os.path.exists(output_file): os.remove(output_file)

# ================= HANDLERS =================

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply("🔥 **Subtitle Generator Online!**\n/srt | /vtt | /delete | /stats | /close | /clearall")

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
        if file.endswith((".srt", ".vtt", ".mp4", ".mkv", ".temp")):
            try:
                os.remove(file)
                count += 1
            except Exception:
                pass # Ignore if file is locked or missing
    await message.reply(f"🧹 {count} local temporary files delete kar di hain!")

# --- NEW COMMAND: /clearall ---
@app.on_message(filters.command("clearall"))
async def clear_all_junk(client, message: Message):
    if not is_authorized(message): return
    count = 0
    for file in os.listdir("./"):
        if file.endswith((".srt", ".vtt", ".mp4", ".mkv", ".temp")):
            try:
                os.remove(file)
                count += 1
            except Exception:
                pass 
    await message.reply(f"🗑️ **All Junk Files Cleared!**\n{count} files successfully deleted.")

# --- NEW COMMAND: /close ---
# Note: Pyrogram bot ko 'close' karne ke liye Client ko stop karna padta hai.
# Iske liye process ko shutdown karna padega, jo bot ko offline kar dega.
@app.on_message(filters.command("close"))
async def close_bot(client, message: Message):
    if message.from_user.id != OWNER_ID: # Sirf owner ko permission
        return await message.reply("❌ Tum yeh command use nahi kar sakte.")
        
    await message.reply("🛑 **Shutting Down Bot...** Goodbye!")
    # Client ko stop karke bot ko off karta hai.
    await client.stop() 
    # NOTE: Is command ke baad bot band ho jayega aur restart karna padega.

@app.on_message(filters.command("stats"))
async def get_stats(client, message: Message):
    if not is_authorized(message): return
    total, used, free = shutil.disk_usage("/")
    await message.reply(f"💾 **Disk Stats:**\nUsed: {used // (2**20)} MB\nFree: {free // (2**20)} MB")

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    print("Bot is Starting...")
    app.run()
