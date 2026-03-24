import os
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from faster_whisper import WhisperModel

# ================= CONFIGURATION =================

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Yahan default value 0 rakhi hai taaki crash na ho agar var missing ho
DEST_CHANNEL = int(os.environ.get("DEST_CHANNEL", "-10023456789")) 

OWNER_ID = 5344078567                    
ALLOWED_USERS = [5351848105]             
ALLOWED_GROUPS = [-1003899919015]        

app = Client("SubGenBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ✅ RAM PROBLEM SOLVED: Using tiny model with int8 compute
# Isse Render ki 512MB RAM ful nahi hogi.
model = WhisperModel("tiny", device="cpu", compute_type="int8")

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
    if not replied or not (replied.video or replied.document):
        return await message.reply(f"❌ Video file par reply karke `/{mode}` likho!")

    status = await message.reply(f"⏳ **Processing {mode.upper()}...**\nAudio process ho raha hai, sabar rakho lala.")
    
    start_time = time.time()
    v_path = None
    output_file = None
    
    try:
        # File download (Temporary storage for processing)
        v_path = await client.download_media(replied)
        
        # AI Transcription logic
        segments, info = model.transcribe(v_path, beam_size=5)
        output_file = f"Sub_{replied.id}.{mode}"
        
        with open(output_file, "w", encoding="utf-8") as f:
            if mode == "vtt": f.write("WEBVTT\n\n")
            for i, segment in enumerate(segments, start=1):
                start = format_time(segment.start, mode)
                end = format_time(segment.end, mode)
                f.write(f"{i}\n{start} --> {end}\n{segment.text.strip()}\n\n")

        # Result channel pe bhej raha hai
        time_taken = f"{int(time.time() - start_time)}s"
        caption = (f"✅ **Subtitles Generated**\n\n"
                   f"🌐 **Language:** {info.language.upper()}\n"
                   f"⏱️ **Time:** {time_taken}")
        
        await client.send_document(
            chat_id=DEST_CHANNEL, 
            document=output_file, 
            caption=caption
        )
        
        await status.edit(f"✅ Kaam ho gaya! File channel pe bhej di hai.")

    except Exception as e:
        await status.edit(f"❌ **Error:** {str(e)}")
    
    finally:
        # ✅ STORAGE PROBLEM SOLVED: Kaam khatam hote hi delete
        if v_path and os.path.exists(v_path): os.remove(v_path)
        if output_file and os.path.exists(output_file): os.remove(output_file)

# ================= HANDLERS =================

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply("<b>🔥 Subtitle Generator is Online!</b>\n\nReply to a video with:\n/srt - Get SRT\n/vtt - Get VTT")

@app.on_message(filters.command("srt") & filters.reply)
async def srt_handler(client, message: Message):
    await process_transcription(client, message, "srt")

@app.on_message(filters.command("vtt") & filters.reply)
async def vtt_handler(client, message: Message):
    await process_transcription(client, message, "vtt")

if __name__ == "__main__":
    app.run()
  
