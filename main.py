import os
import time
import asyncio
import gc
from collections import deque
from faster_whisper import WhisperModel
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from huggingface_hub import login

# ================= CONFIG =================
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")
DEST_CHANNEL = int(os.getenv("DEST_CHANNEL", "0"))

OWNER_ID = 5344078567
ALLOWED_USERS = [5344078567]
ALLOWED_GROUPS = [-1003899919015]

# ================= INIT =================
app = Client("SubGenBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

task_queue = deque()
queue_lock = asyncio.Lock()
is_processing = False

model = None
model_lock = asyncio.Lock()

# ================= UTILS =================
async def safe_reply(message: Message, text: str):
    try:
        return await message.reply_text(text)
    except Exception as e:
        print(f"Reply Error: {e}")
        return None

async def is_authorized(message: Message) -> bool:
    if not message or not message.from_user:
        return False
    uid = message.from_user.id
    if uid == OWNER_ID or uid in ALLOWED_USERS or message.chat.id in ALLOWED_GROUPS:
        return True
    await safe_reply(message, f"❌ Unauthorized ID: `{uid}`")
    return False

def format_timestamp(seconds: float, fmt: str):
    td = time.gmtime(seconds)
    ms = int((seconds % 1) * 1000)
    cs = int((seconds % 1) * 100)

    if fmt == "srt":
        return f"{time.strftime('%H:%M:%S', td)},{ms:03d}"
    elif fmt == "vtt":
        return f"{time.strftime('%H:%M:%S', td)}.{ms:03d}"
    else:  # ass
        ts = time.strftime('%H:%M:%S', td)
        return f"{ts[1:] if ts.startswith('0') else ts}.{cs:02d}"

# ================= MODEL =================
async def get_model():
    global model
    async with model_lock:
        if model is None:
            print("Loading Whisper Model (tiny)...")
            if HF_TOKEN:
                try:
                    login(token=HF_TOKEN)
                    print("✅ HF Login Successful")
                except Exception as e:
                    print(f"HF Login Error: {e}")

            try:
                model = WhisperModel(
                    "tiny",
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=max(2, os.cpu_count() or 4),   # better than 1
                    num_workers=1,
                    download_root="./model_cache"
                )
                print("✅ Model Loaded with int8!")
            except Exception as e:
                print(f"int8 failed: {e}. Trying float32 fallback...")
                model = WhisperModel(
                    "tiny",
                    device="cpu",
                    compute_type="float32",
                    cpu_threads=max(2, os.cpu_count() or 4),
                    num_workers=1,
                    download_root="./model_cache"
                )
                print("✅ Model Loaded with float32 fallback!")
        return model

# ================= TRANSCRIBE =================
def run_transcription(model, audio_path, out_file, fmt):
    try:
        segments, info = model.transcribe(
            audio_path,
            beam_size=5,           # better quality than 1
            vad_filter=True,       # removes silence better
            word_timestamps=False
        )
        print(f"Detected language: {info.language} (prob: {info.language_probability:.2f})")

        has_data = False
        with open(out_file, "w", encoding="utf-8") as f:
            if fmt == "vtt":
                f.write("WEBVTT\n\n")
            elif fmt == "ass":
                f.write("[Script Info]\nScriptType: v4.00+\n\n[Events]\nFormat: Layer, Start, End, Style, Text\n")

            for i, seg in enumerate(segments, 1):
                text = seg.text.strip()
                if not text:
                    continue
                has_data = True
                start = format_timestamp(seg.start, fmt)
                end = format_timestamp(seg.end, fmt)

                if fmt == "srt":
                    f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
                elif fmt == "vtt":
                    f.write(f"{start} --> {end}\n{text}\n\n")
                else:
                    f.write(f"Dialogue: 0,{start},{end},Default,{text}\n")

        return has_data
    except Exception as e:
        print(f"Transcription Error: {e}")
        return False

# ================= COMMANDS =================
@app.on_message(filters.command("start"))
async def start_cmd(_, message: Message):
    if await is_authorized(message):
        await safe_reply(message, "🔥 SubGen Bot Online!\nReply to video with /srt /vtt /ass")

@app.on_message(filters.command(["srt", "vtt", "ass"]))
async def handle_request(_, message: Message):
    if not await is_authorized(message):
        return

    reply = message.reply_to_message
    if not reply or not (reply.video or reply.document):
        return await safe_reply(message, "❌ Reply to a video or document file!")

    fmt = message.command[0].lower()

    async with queue_lock:
        task_queue.append({
            "msg": message,
            "media": reply.video or reply.document,
            "format": fmt
        })

    await safe_reply(message, f"✅ Added to queue (Position: {len(task_queue)})")

@app.on_message(filters.command("refresh"))
async def refresh(_, message: Message):
    if not await is_authorized(message):
        return

    global task_queue, is_processing
    task_queue.clear()
    is_processing = False

    for f in os.listdir("."):
        if f.startswith(("v_", "a_")) or f.endswith((".srt", ".vtt", ".ass")):
            try:
                os.remove(f)
            except:
                pass
    gc.collect()
    await safe_reply(message, "♻️ Queue & temp files cleaned!")

# ================= PROCESS TASK =================
async def process_task(task):
    global is_processing
    msg = task["msg"]
    media = task["media"]
    fmt = task["format"]

    status = await safe_reply(msg, "⏳ Starting...")
    uid = f"{msg.chat.id}_{msg.id}"
    v_path = f"v_{uid}.mp4"
    a_path = f"a_{uid}.mp3"
    out_file = f"sub_{uid}.{fmt}"

    try:
        if status:
            await status.edit("📥 Downloading media...")
        await app.download_media(media.file_id, file_name=v_path)

        if status:
            await status.edit("🔊 Extracting audio...")
        cmd = [
            "ffmpeg", "-i", v_path,
            "-vn", "-ar", "16000", "-ac", "1",
            "-b:a", "32k", "-f", "mp3",
            a_path, "-y"
        ]
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()

        if os.path.exists(v_path):
            os.remove(v_path)

        if status:
            await status.edit("🤖 Loading AI Model...")
        mdl = await get_model()

        if status:
            await status.edit("🤖 Transcribing... (tiny model on CPU)")

        loop = asyncio.get_event_loop()
        ok = await loop.run_in_executor(None, run_transcription, mdl, a_path, out_file, fmt)

        if not ok:
            raise Exception("No speech detected")

        dest = DEST_CHANNEL if DEST_CHANNEL != 0 else msg.chat.id
        if status:
            await status.edit("📤 Uploading subtitle file...")
        await app.send_document(dest, out_file, caption=f"✅ {fmt.upper()} Subtitles Generated")

        if status:
            await status.delete()

    except Exception as e:
        print(f"Processing Error: {e}")
        if status:
            await status.edit(f"❌ Error: {str(e)[:80]}")
    finally:
        for f in [v_path, a_path, out_file]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass
        gc.collect()
        is_processing = False

# ================= QUEUE WORKER =================
async def worker():
    global is_processing
    while True:
        if task_queue and not is_processing:
            is_processing = True
            try:
                task = task_queue.popleft()
                await process_task(task)
            except Exception as e:
                print(f"Worker Error: {e}")
                is_processing = False
        await asyncio.sleep(1)

# ================= MAIN =================
async def main():
    await app.start()
    try:
        await app.send_message(OWNER_ID, "✅ SubGen Bot Started Successfully on Render!")
    except:
        pass

    asyncio.create_task(worker())
    print("🚀 BOT RUNNING")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
