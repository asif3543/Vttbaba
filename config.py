import os

# Telegram API
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Storage & permissions
OWNER_ID = int(os.getenv("OWNER_ID", "5351848105"))
ALLOWED_USERS = [int(uid) for uid in os.getenv("ALLOWED_USERS", "5344078567").split(",")]
ALLOWED_GROUPS = [int(gid) for gid in os.getenv("ALLOWED_GROUPS", "-1003899919015").split(",")]
STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID", "-1003096528862"))
