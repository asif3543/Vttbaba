import os

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

OWNER_ID = int(os.environ.get("OWNER_ID", 5351848105))
ALLOWED_USER = int(os.environ.get("ALLOWED_USER", 5344078567))
STORAGE_CHANNEL_ID = int(os.environ.get("STORAGE_CHANNEL_ID", -1003096528862))
PORT = int(os.environ.get("PORT", 10000))

# Jo log bot use kar sakte hain admin commands ke liye
ADMINS = [OWNER_ID, ALLOWED_USER]
