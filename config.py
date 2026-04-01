import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

OWNER_ID = int(os.getenv("OWNER_ID", "5351848105"))
ALLOWED_USERS = [int(x) for x in os.getenv("ALLOWED_USERS", "5344078567").split(",")]

STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID", "-1003096528862"))
ALLOWED_GROUP_ID = int(os.getenv("ALLOWED_GROUP_ID", "-1003899919015"))
